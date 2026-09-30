"""Read a table someone else made: a CSV or an Excel workbook as it comes.

A data file uploaded by a researcher is rarely the comma-separated UTF-8 file
``pandas.read_csv`` expects. Excel in Russian and most European locales saves
"CSV" with ``;`` between fields and a comma as the decimal mark, often with a
byte-order mark, or in the Windows code page (Windows-1251 for Cyrillic);
"Unicode text" is UTF-16 with tabs; a sheet may start with a title, and a
Qualtrics export has a row of question texts under the names (and, as CSV, a
row of ``{"ImportId": ...}`` under that). Read with pandas' defaults, such a
file collapses into one column, fails with ``UnicodeDecodeError`` or makes a
respondent of the question texts.

:func:`read_text_table` and :func:`read_workbook` find out how the file is
written — each choice can be given instead of detected — and say what they
found (:class:`TableRead.options`), so a host can show it and a run reads the
file the same way. Every option a caller passes to pandas (``sep=``,
``encoding=``, ``decimal=``, ``header=``, ``sheet_name=`` …) still wins.
"""

from __future__ import annotations

import codecs
import contextlib
import csv
import datetime as _dt
import io
import math
import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd

#: Delimiters a text file is tried with, in the order a tie is settled.
DELIMITERS = (",", ";", "\t", "|")
#: How a builder names them (``tab`` for the tab character).
DELIMITER_NAMES = {",": ",", ";": ";", "\t": "tab", "|": "|"}
#: The legacy code pages a file that is not UTF-8 is recognised in: the
#: Windows code pages of Cyrillic, Western and Central European Excel, and the
#: two older Cyrillic ones.
LEGACY_ENCODINGS = ("cp1251", "cp1252", "cp1250", "koi8_r", "cp866")
#: Plain names of the encodings (by Python's codec name), for messages.
ENCODING_NAMES = {
    "utf-8": "UTF-8",
    "utf-8-sig": "UTF-8 (with a byte-order mark)",
    "utf-16": 'UTF-16 (Excel\'s "Unicode text")',
    "utf-16-le": "UTF-16",
    "utf-16-be": "UTF-16",
    "utf-32": "UTF-32",
    "cp1251": "Windows-1251 (Cyrillic)",
    "cp1252": "Windows-1252 (Western European)",
    "cp1250": "Windows-1250 (Central European)",
    "koi8-r": "KOI8-R (Cyrillic)",
    "cp866": "CP866 (Cyrillic, DOS)",
    "iso8859-1": "ISO-8859-1 (Latin-1)",
}
#: The fixed columns of every Qualtrics response export.
QUALTRICS_COLUMNS = frozenset(
    {
        "StartDate",
        "EndDate",
        "Status",
        "IPAddress",
        "Progress",
        "Duration (in seconds)",
        "Finished",
        "RecordedDate",
        "ResponseId",
        "RecipientLastName",
        "RecipientFirstName",
        "RecipientEmail",
        "ExternalReference",
        "ExternalDataReference",
        "LocationLatitude",
        "LocationLongitude",
        "DistributionChannel",
        "UserLanguage",
    }
)
#: Cells that mean "no value" in a column that otherwise holds numbers, dates
#: or true/false (in a text column they stay what the respondent wrote).
NA_TOKENS = frozenset(
    {
        "-",
        "--",
        "\u2014",
        "\u2013",
        ".",
        "na",
        "n/a",
        "#n/a",
        "null",
        "none",
        "nan",
        "#null!",
        "#div/0!",
        "#value!",
        "#ref!",
        "#num!",
    }
)

_SAMPLE_BYTES = 262_144
#: How much of a file's non-ASCII lines its encoding is judged by.
_SCORE_BYTES = 65_536
_SAMPLE_ROWS = 200
_HEAD_ROWS = 30
_IMPORT_ID = re.compile(r'^\{\s*"ImportId"\s*:')
_SPACES = "\u00a0\u202f\u2009 "
_DIGITS_ONLY = re.compile(r"^[+-]?\d+$")
_BOOLS = {"true": True, "false": False}
_ISO_DATE = re.compile(
    r"^\d{4}-\d{2}-\d{2}(?:[ T]\d{1,2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?$"
)
_DOT_DATE = re.compile(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})(?: (\d{1,2}):(\d{2})(?::(\d{2}))?)?$")
_SLASH_DATE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})(?: (\d{1,2}):(\d{2})(?::(\d{2}))?)?$")


def normal_name(name: Any) -> str:
    """A column name as names are compared: case folded, runs of anything but
    letters and digits one underscore (``Q1`` and ``q1``, ``Duration (in
    seconds)`` and ``duration_in_seconds``) — the rule by which the Qualtrics
    importer names variables after a question's export tag."""

    return re.sub(r"[\W_]+", "_", str(name).casefold()).strip("_")


class SnapshotReadError(ValueError):
    """A data file that cannot be read, said in words: what was found, and
    which option (or which way of saving the file) reads it."""


@dataclass(slots=True)
class TableRead:
    """A table read from a file: the frame, the labels a label row gave its
    columns, and how the file was read."""

    frame: pd.DataFrame
    #: Column -> the text of a label row under the names (a Qualtrics export's
    #: question texts), when the file has one.
    labels: dict[str, str] = field(default_factory=dict)
    #: How the file was read, each choice as detected or given: ``encoding``,
    #: ``delimiter``, ``decimal`` (text); ``sheet`` and ``sheets`` (Excel);
    #: ``skip_rows`` (rows above the header), ``header_rows`` (1 the names, 2
    #: with a label row, 3 with a row skipped after it), ``qualtrics``.
    options: dict[str, Any] = field(default_factory=dict)
    #: What a reader should know: columns renamed or dropped, and why.
    notes: list[str] = field(default_factory=list)


# ─── text files ──────────────────────────────────────────────────────────────


def detect_encoding(source: str | Path) -> str:
    """The encoding a text file is written in.

    A byte-order mark settles it (UTF-8, UTF-16, UTF-32); a file that decodes
    as UTF-8 throughout is UTF-8; otherwise the legacy code page among
    :data:`LEGACY_ENCODINGS` in which the file's non-ASCII letters make words
    (:func:`legacy_encoding`): Windows-1251 for Cyrillic text Excel saved,
    Windows-1252 for Western European text, and so on.
    """

    return _detect_encoding(Path(source))[0]


def _detect_encoding(path: Path) -> tuple[str, bool]:
    """The encoding, and whether it is a guess (a legacy code page chosen by
    how its letters read, rather than a mark or valid UTF-8)."""

    with path.open("rb") as handle:
        head = handle.read(_SAMPLE_BYTES)
    if head.startswith(codecs.BOM_UTF8):
        return "utf-8-sig", False
    if head.startswith((codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE)):
        return "utf-32", False
    if head.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return "utf-16", False
    unmarked = _utf16_without_mark(head)
    if unmarked:
        return unmarked, False
    utf8, sample = _scan_non_ascii(path)
    if utf8:
        return "utf-8", False
    return legacy_encoding(sample), True


def _utf16_without_mark(head: bytes) -> str | None:
    """UTF-16 saved without a mark: every other byte of ASCII text is zero."""

    sample = head[:4096]
    if len(sample) < 4:
        return None
    even, odd = sample[0::2], sample[1::2]
    if odd.count(0) > 0.4 * len(odd) and even.count(0) < 0.05 * len(even):
        return "utf-16-le"
    if even.count(0) > 0.4 * len(even) and odd.count(0) < 0.05 * len(odd):
        return "utf-16-be"
    return None


_HIGH_LINE = re.compile(rb"[^\n]*[\x80-\xff][^\n]*")


def _scan_non_ascii(path: Path) -> tuple[bool, bytes]:
    """Whether the whole file is UTF-8, and its lines that hold bytes beyond
    ASCII (up to :data:`_SAMPLE_BYTES` of them), wherever in the file they
    are: the letters an encoding is told by. A file whose first 256 KB are
    ASCII (codes, numbers) and whose Cyrillic answers come later is judged
    by those answers, not by its ASCII head."""

    decoder = codecs.getincrementaldecoder("utf-8")()
    utf8 = True
    sample: list[bytes] = []
    size = 0
    with path.open("rb") as handle:
        while chunk := handle.read(1 << 20):
            if utf8:
                try:
                    decoder.decode(chunk)
                except UnicodeDecodeError:
                    utf8 = False
            if size < _SAMPLE_BYTES:
                for found in _HIGH_LINE.finditer(chunk):
                    line = found.group()
                    sample.append(line)
                    size += len(line) + 1
                    if size >= _SAMPLE_BYTES:
                        break
            if not utf8 and size >= _SAMPLE_BYTES:
                break
    if utf8:
        try:
            decoder.decode(b"", final=True)
        except UnicodeDecodeError:
            utf8 = False
    return utf8, b"\n".join(sample)


#: How often each letter comes in Russian text (per cent; Ukrainian's own
#: letters as they come in Ukrainian): what tells Windows-1251 from KOI8-R
#: and CP866 when each of them decodes a file into Cyrillic words — "ответ"
#: rather than "ПФЧЕФ".
_CYRILLIC_FREQUENCY = {
    "о": 10.97, "е": 8.45, "а": 8.01, "и": 7.35, "н": 6.70, "т": 6.26, "с": 5.47,
    "р": 4.73, "в": 4.54, "л": 4.40, "к": 3.49, "м": 3.21, "д": 2.98, "п": 2.81,
    "у": 2.62, "я": 2.01, "ы": 1.90, "ь": 1.74, "г": 1.70, "з": 1.65, "б": 1.59,
    "ч": 1.44, "й": 1.21, "х": 0.97, "ж": 0.94, "ш": 0.73, "ю": 0.64, "ц": 0.48,
    "щ": 0.36, "э": 0.32, "ф": 0.26, "ъ": 0.04, "ё": 0.04,
    "і": 1.5, "ї": 0.5, "є": 0.4, "ґ": 0.1, "ў": 0.1,
}  # fmt: skip
_RARE_CYRILLIC = 0.02
#: Signs a survey's text holds beside its words — quotes, dashes, currency,
#: "№", degrees: they read in any code page that has them.
_TEXT_SIGNS = frozenset("\u00a0¡¢£¤¥¦§©«¬\u00ad®°±²³µ¶·¹º»¼½¾¿×÷–—‘’‚“”„†‡•…‰‹›€№™₽")
#: A word: letters, with an apostrophe inside ("l'été", "п'ять").
_WORDS = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)*")
_NEAR_BEST = 0.15
_CLEARLY_MORE_COMMON = 0.15
_NO_WORDS = -10.0
_SMALL_LETTERS = 0.5
_SIGN_IN_WORD = re.compile(r"(?<=[^\W\d_])[^\w\s\x00-\x7f](?=[^\W\d_])")


def legacy_encoding(sample: bytes) -> str:
    """The code page among :data:`LEGACY_ENCODINGS` in which ``sample`` (the
    lines of a file that hold bytes beyond ASCII) reads as text.

    Each code page decodes the sample. A character beyond ASCII reads when it
    is a sign text holds (quotes, dashes, currency, "№") or a letter of a word
    of one script: Cyrillic letters with no Latin letter in the word, or
    accented Latin letters in a word with plain ones ("très", "Łódź"). It
    does not read in a word that mixes scripts, turns case mid-word ("мОСКВА",
    KOI8-R read as Windows-1251) or is all accented letters ("îòâåò",
    Cyrillic read as Western), and a box-drawing or control character counts
    twice against. Windows-1251 is chosen unless KOI8-R or CP866 reads
    clearly better, or as well with letters Russian uses clearly more
    ("ответ", not "ПФЧЕФ"); the Cyrillic choice wins over the better of
    Windows-1252 and Windows-1250 (a tie going to Windows-1252) when it reads
    at least as well. A sample so short that both read — a lone "м" — is
    taken for Cyrillic, what a Russian Excel file is. ``charset_normalizer`` decides only a sample without a
    letter or sign to tell by.
    """

    if len(sample) > _SCORE_BYTES:
        cut = sample.rfind(b"\n", 0, _SCORE_BYTES)
        sample = sample[: cut if cut > 0 else _SCORE_BYTES]
    readings: dict[str, _Reading] = {}
    for encoding in LEGACY_ENCODINGS:
        try:
            text = sample.decode(encoding)
        except UnicodeDecodeError:
            continue  # a byte this code page has no character for
        reads, in_cyrillic, frequency = _how_it_reads(text)
        if reads is not None:
            readings[encoding] = _Reading(encoding, reads, in_cyrillic, frequency)
    if not readings:
        return codecs.lookup(_charset_normalizer(sample) or LEGACY_ENCODINGS[0]).name
    # Windows-1251 unless an older Cyrillic code page reads clearly better, or
    # as well with letters Russian uses clearly more ("ответ", not "ПФЧЕФ").
    cyrillic: _Reading | None = readings.get("cp1251")
    for older in ("koi8_r", "cp866"):
        other = readings.get(older)
        if other is None or not other.cyrillic:
            continue
        if (
            cyrillic is None
            or other.reads > cyrillic.reads + _NEAR_BEST
            or (
                other.reads >= cyrillic.reads - _NEAR_BEST
                and cyrillic.cyrillic
                and other.frequency != _NO_WORDS
                and (
                    cyrillic.frequency == _NO_WORDS
                    or other.frequency >= cyrillic.frequency + _CLEARLY_MORE_COMMON
                )
            )
        ):
            cyrillic = other
    latin: _Reading | None = None
    for encoding in ("cp1252", "cp1250"):  # a tie goes to Windows-1252
        other = readings.get(encoding)
        if other is not None and (latin is None or other.reads > latin.reads):
            latin = other
    if cyrillic is not None and (latin is None or cyrillic.reads >= latin.reads):
        chosen = cyrillic
    else:
        chosen = latin if latin is not None else next(iter(readings.values()))
    return codecs.lookup(chosen.encoding).name


@dataclass(frozen=True, slots=True)
class _Reading:
    encoding: str
    reads: float
    cyrillic: bool
    frequency: float


def _how_it_reads(text: str) -> tuple[float | None, bool, float]:
    """The share of ``text``'s characters beyond ASCII that read (as a sign or
    in a word; less the unreadable, box drawing twice), None without any;
    whether its words are mostly Cyrillic; and the mean log-frequency in
    Russian of the letters of its Cyrillic words (each word once)."""

    high = [char for char in text if ord(char) > 0x7F]
    if not high:
        return None, False, 0.0
    good = bad = 0
    for char in high:
        if char in _TEXT_SIGNS:
            good += 1
        elif (
            "\u2500" <= char <= "\u25ff" or "\u0080" <= char <= "\u009f" or char in "∙√≈≤≥⌠⌡\ufffd"
        ):
            bad += 2
    # A sign between two letters ("M№ller", Western read as CP866) is no
    # sign text holds there (an apostrophe aside).
    bad += 2 * sum(1 for sign in _SIGN_IN_WORD.findall(text) if sign != "’")
    cyrillic_words = latin_words = lower = 0
    logs: list[float] = []
    seen: set[str] = set()
    for word in _WORDS.findall(text):
        count = sum(1 for char in word if ord(char) > 0x7F and char.isalpha())
        if not count:
            continue  # no letter beyond ASCII ("¹" is a sign, counted above)
        verdict = _word_reads(word)
        if verdict is None:
            bad += count
            continue
        good += count
        if verdict == "cyrillic":
            cyrillic_words += 1
            # Each word once (fifty answers "м" say no more than one does), and
            # words of two letters or more: a lone letter tells nothing.
            if word not in seen and len(word) > 1:
                seen.add(word)
                logs.extend(
                    math.log(_CYRILLIC_FREQUENCY.get(char, _RARE_CYRILLIC)) for char in word.lower()
                )
                lower += sum(1 for char in word if char.islower())
        else:
            latin_words += 1
    # Russian is written mostly in small letters: KOI8-R read as Windows-1251
    # (and back) swaps the case of every letter.
    frequency = (sum(logs) + _SMALL_LETTERS * lower) / len(logs) if logs else _NO_WORDS
    return (good - bad) / len(high), cyrillic_words > latin_words, frequency


def _word_reads(word: str) -> str | None:
    """``"cyrillic"`` or ``"latin"`` when ``word`` reads as a word of that
    script, None when it does not."""

    letters = [char for char in word if char.isalpha()]
    if not letters:
        return None
    if any(
        char.islower() and following.isupper()
        for char, following in zip(letters, letters[1:], strict=False)
    ):
        return None  # "мОСКВА": KOI8-R read as Windows-1251
    cyrillic = sum(1 for char in letters if "\u0400" <= char <= "\u04ff")
    plain = sum(1 for char in letters if char.isascii())
    accented = sum(1 for char in letters if "\u00c0" <= char <= "\u024f")
    if cyrillic == len(letters):
        return "cyrillic"
    if (
        accented
        and not cyrillic
        and accented + plain == len(letters)
        and (plain or len(letters) == 1)
    ):
        return "latin"  # "très", "été", "Łódź", "à"; not "îòâåò"
    return None


def _charset_normalizer(sample: bytes) -> str | None:
    try:
        from charset_normalizer import from_bytes
    except ImportError:  # pragma: no cover - a dependency of the engine
        return None
    found = from_bytes(sample, cp_isolation=list(LEGACY_ENCODINGS)).best()
    return found.encoding if found is not None and found.encoding else None


def _encoding_name(encoding: str) -> str:
    try:
        return ENCODING_NAMES.get(codecs.lookup(encoding).name, encoding)
    except LookupError:
        return encoding


def _canonical_encoding(encoding: str) -> str:
    try:
        name = codecs.lookup(encoding).name
    except LookupError as exc:
        raise SnapshotReadError(
            f"Unknown encoding {encoding!r}: use utf-8, utf-16, cp1251, cp1252, koi8-r "
            "or another Python codec name, or leave Encoding on auto."
        ) from exc
    # Python names UTF-16/32 without a byte order as "utf-16"; keep the rest.
    return name


def _sample_text(path: Path, encoding: str) -> tuple[str, bool]:
    """The start of the file as text, and whether the file goes on after it."""

    with path.open("rb") as handle:
        head = handle.read(_SAMPLE_BYTES)
        more = bool(handle.read(1))
    decoder = codecs.getincrementaldecoder(encoding)(errors="strict")
    try:
        text = decoder.decode(head, final=not more)
    except UnicodeDecodeError as exc:
        raise _decode_error(path, encoding, exc) from exc
    return text, more


def _decode_error(path: Path, encoding: str, exc: UnicodeDecodeError) -> SnapshotReadError:
    guess = None
    with contextlib.suppress(OSError):
        guess = detect_encoding(path)
    hint = (
        f" It looks like {_encoding_name(guess)}: set Encoding to {guess}, or leave it on auto."
        if guess and codecs.lookup(guess).name != codecs.lookup(encoding).name
        else " Leave Encoding on auto, or save the file as CSV UTF-8."
    )
    return SnapshotReadError(
        f"The file is not {_encoding_name(encoding)}: byte {exc.object[exc.start:exc.start + 1]!r} "
        f"at position {exc.start} cannot be read in it.{hint}"
    )


def _rows(text: str, delimiter: str, *, complete: bool) -> tuple[list[list[str]], list[int]]:
    """The rows of a sample as the csv module parses them (quotes respected,
    blank lines as empty rows); without the last when the sample is cut."""

    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter, quotechar='"')
    rows: list[list[str]] = []
    lines: list[int] = []
    try:
        for row in reader:
            rows.append(row)
            lines.append(reader.line_num)
            if len(rows) >= _SAMPLE_ROWS * 5:
                break
    except csv.Error:
        pass
    if not complete and rows:
        rows.pop()
        lines.pop()
    return rows, lines


def sniff_delimiter(text: str, *, complete: bool = True) -> str:
    """The delimiter of a text table: of ``,`` ``;`` tab and ``|``, the one
    that splits the rows of the sample into the same number of fields most
    consistently (quoted fields respected), the names row first among them.

    When ``,`` and ``;`` split every row alike — Russian Excel's "Рост, см;Вес,
    кг" over "175,5;70,2" — ``;`` is taken unless the fields it makes hold
    commas of text rather than decimal commas more often than the fields
    ``,`` makes hold a ``;``. A table of one column is read whole: its
    numbers may be written "4,5".
    """

    found: dict[str, tuple[tuple[Any, ...], list[list[str]]]] = {}
    for delimiter in DELIMITERS:
        rows, _lines = _rows(text, delimiter, complete=complete)
        filled = [row for row in rows if any(cell.strip() for cell in row)][:_SAMPLE_ROWS]
        counts = [len(row) for row in filled]
        if not counts:
            continue
        width, seen = Counter(counts).most_common(1)[0]
        if width < 2:
            continue
        share = seen / len(counts)
        # The names row splits as the answers do; a title above it may not.
        named = next((count for count in counts if count >= 2), 0) == width
        found[delimiter] = ((share >= 0.9, named, round(share, 2), width), filled)
    if not found:
        return ","
    rank = {delimiter: index for index, delimiter in enumerate(DELIMITERS)}
    chosen = max(found, key=lambda delimiter: (found[delimiter][0], -rank[delimiter]))
    if chosen == "," and ";" in found and found[";"][0] == found[","][0]:
        in_comma = sum(1 for row in found[","][1][1:] for cell in row if ";" in cell)
        in_semicolon = sum(
            1
            for row in found[";"][1][1:]
            for cell in row
            if "," in cell and not _DECIMAL_COMMA.match(cell.strip())
        )
        if in_comma >= in_semicolon:
            chosen = ";"
    if chosen == "," and _one_decimal_column(found[","][1]):
        # One column of decimal commas: read with a delimiter it does not hold.
        return next((mark for mark in (";", "\t", "|") if mark not in text), ",")
    return chosen


def _one_decimal_column(rows: list[list[str]]) -> bool:
    """Rows (split at ``,``) of a one-column table whose numbers are written
    with a decimal comma: "score" over "4,5", "3,2" — or a name with a comma
    and a space in it ("Доход, руб.") over such numbers."""

    if len(rows) < 2:
        return False
    names = rows[0]
    if len(names) > 2 or (len(names) == 2 and not names[1].startswith(" ")):
        return False
    values = [",".join(row).strip() for row in rows[1:]]
    return any(len(row) == 2 for row in rows[1:]) and all(
        _DECIMAL_COMMA.match(value) or _DIGITS_ONLY.match(value) for value in values
    )


_DECIMAL_COMMA = re.compile(r"^[+-]?\d{1,3}(?:[ .\u00a0\u202f]?\d{3})*,\d+%?$|^[+-]?\d+,\d+%?$")
_DECIMAL_POINT = re.compile(r"^[+-]?\d{1,3}(?:[ ,\u00a0\u202f]?\d{3})*\.\d+%?$|^[+-]?\d+\.\d+%?$")


def detect_decimal(rows: list[list[str]], delimiter: str) -> str:
    """``,`` when the table's numbers are written with a decimal comma (as
    Excel writes them where ``;`` separates the fields), else ``.``."""

    if delimiter == ",":
        return "."
    comma = point = 0
    for row in rows:
        for cell in row:
            value = cell.strip()
            if _DECIMAL_COMMA.match(value):
                comma += 1
            elif _DECIMAL_POINT.match(value):
                point += 1
    return "," if comma > point else "."


def read_text_table(
    source: str | Path,
    *,
    encoding: str | None = "auto",
    delimiter: str | None = "auto",
    decimal: str | None = "auto",
    header_rows: int | str | None = "auto",
    skip_rows: int | None = None,
    nrows: int | None = None,
    keep_text: Iterable[str] = (),
    **read_kwargs: Any,
) -> TableRead:
    """Read a delimited text file (``.csv``, ``.tsv``, ``.txt``).

    ``encoding``, ``delimiter`` (``,`` ``;`` ``tab`` ``|``), ``decimal``
    (``.`` or ``,``) and ``header_rows`` (1, 2 or 3; see
    :func:`detect_header`) are detected when ``"auto"`` (or None);
    ``skip_rows`` counts the rows above the names (a title), None to detect.
    ``read_kwargs`` go to :func:`pandas.read_csv` and win over what is
    detected: ``sep=``, ``header=``, ``skiprows=`` … as pandas reads them.
    ``keep_text`` names columns (compared by :func:`normal_name`) whose
    answers stay the text they are, as a questionnaire's multiple-answer
    columns ("1,3") must.
    """

    path = Path(source)
    options: dict[str, Any] = {"format": path.suffix.lower().lstrip(".")}
    kwargs = dict(read_kwargs)
    if "sep" in kwargs and _is_auto(delimiter):
        delimiter = kwargs.pop("sep")
    kwargs.pop("sep", None)

    notes: list[str] = []
    if _is_auto(encoding):
        chosen_encoding, guessed = _detect_encoding(path)
        options["encoding_detected"] = True
        if guessed:
            options["encoding_guessed"] = True
            notes.append(
                f"The file is not UTF-8: it is read as {_encoding_name(chosen_encoding)}, "
                "the code page its letters read best in. If names or answers look garbled, "
                "set Encoding (or save the file as CSV UTF-8)."
            )
    else:
        chosen_encoding = _canonical_encoding(str(encoding))
    if chosen_encoding == "utf-8" and _starts_with_bom(path):
        chosen_encoding = "utf-8-sig"
    options["encoding"] = chosen_encoding
    text, more = _sample_text(path, chosen_encoding)
    if not text.strip():
        raise SnapshotReadError("The file is empty: there is no table to read.")

    if _is_auto(delimiter):
        sep = sniff_delimiter(text, complete=not more)
        options["delimiter_detected"] = True
    else:
        sep = _delimiter(str(delimiter))
    options["delimiter"] = sep

    rows, _lines = _rows(text, sep, complete=not more)
    explicit_header = "header" in kwargs or "skiprows" in kwargs or "names" in kwargs
    if explicit_header:
        layout = _Layout(skip=0, label_row=None, skipped=(), qualtrics=False)
    else:
        layout = detect_header(rows, header_rows=header_rows, skip_rows=skip_rows, fields=True)
    options.update(layout.options())

    body = rows[layout.skip + 1 + layout.extra :][:_SAMPLE_ROWS]
    mark = detect_decimal(body, sep) if _is_auto(decimal) else _decimal(str(decimal))
    options["decimal"] = mark
    # Told by the first rows: a column whose decimals come later ("1" for
    # three hundred rows, then "0,85") is read with the other mark too. A
    # comma-separated file's commas are no decimals ("1,3" is a list).
    marks = (mark,) if sep == "," or not _is_auto(decimal) else (mark, "," if mark == "." else ".")

    names = rows[layout.skip] if layout.skip < len(rows) else []
    as_text = _identifier_columns(names, body)
    pandas_kwargs: dict[str, Any] = {
        "sep": sep,
        "encoding": chosen_encoding,
        "decimal": mark,
        "index_col": False,
        # Only an empty cell is missing here: "NA" (Namibia), "None" and
        # "null" written by a respondent stay answers; in a column of numbers
        # they are blanks (tidy_frame).
        "keep_default_na": False,
        "na_values": [""],
    }
    if not explicit_header:
        pandas_kwargs["skiprows"] = layout.skip
        pandas_kwargs["header"] = 0
    if as_text:
        pandas_kwargs["dtype"] = {name: str for name in as_text}
    if nrows is not None:
        pandas_kwargs["nrows"] = nrows + layout.extra
    pandas_kwargs.update(kwargs)
    try:
        frame = pd.read_csv(path, **pandas_kwargs)
    except UnicodeDecodeError as exc:
        raise _decode_error(path, chosen_encoding, exc) from exc
    except pd.errors.EmptyDataError as exc:
        raise SnapshotReadError("The file is empty: there is no table to read.") from exc
    except pd.errors.ParserError as exc:
        raise SnapshotReadError(_parser_message(exc, sep, chosen_encoding)) from exc

    labels, frame = _label_rows(frame, layout)
    frame = _tidy_names(frame, notes, labels)
    _total_row(frame, notes)
    if not explicit_header:
        keep = [name.strip() for name in as_text] + _named(frame, keep_text)
        tidy_frame(frame, decimal=marks, keep_text=keep)
    return TableRead(frame=frame, labels=labels, options=options, notes=notes)


def _named(frame: pd.DataFrame, names: Iterable[str]) -> list[str]:
    wanted = {normal_name(name) for name in names}
    return [column for column in frame.columns if wanted and normal_name(column) in wanted]


def _starts_with_bom(path: Path) -> bool:
    with path.open("rb") as handle:
        return handle.read(3) == codecs.BOM_UTF8


def _is_auto(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip().lower() in {"", "auto"})


def _delimiter(value: str) -> str:
    named = {"tab": "\t", "\\t": "\t", "comma": ",", "semicolon": ";", "pipe": "|"}
    chosen = named.get(value.strip().lower(), value)
    if len(chosen) != 1:
        raise SnapshotReadError(
            f"Delimiter {value!r} is not one character: use ',', ';', tab or '|', or auto."
        )
    return chosen


def _decimal(value: str) -> str:
    named = {"point": ".", "dot": ".", "comma": ","}
    chosen = named.get(value.strip().lower(), value.strip())
    if chosen not in {".", ","}:
        raise SnapshotReadError(f"Decimal mark {value!r} is neither '.' nor ',' (or auto).")
    return chosen


def _parser_message(exc: Exception, sep: str, encoding: str) -> str:
    text = str(exc)
    found = re.search(r"Expected (\d+) fields in line (\d+), saw (\d+)", text)
    how = f"(read with delimiter {DELIMITER_NAMES.get(sep, sep)!r} and {_encoding_name(encoding)})"
    if found:
        expected, line, saw = found.groups()
        return (
            f"Line {line} has {saw} fields where the table has {expected} {how}. A value "
            "that holds the delimiter must be in double quotes; or pick another Delimiter."
        )
    return f"The file cannot be read as a table {how}: {text}"


def _identifier_columns(names: list[str], body: list[list[str]]) -> list[str]:
    """Columns of digits with a leading zero (``00123``) or too long for a
    number to hold exactly (16 digits and more): identifiers and phone
    numbers, kept as text rather than read as numbers."""

    keep: list[str] = []
    for index, name in enumerate(names):
        values = [row[index].strip() for row in body if index < len(row) and row[index].strip()]
        if not values or not all(_DIGITS_ONLY.match(value) for value in values):
            continue
        if any(
            (len(value.lstrip("+-")) > 1 and value.lstrip("+-").startswith("0"))
            or len(value.lstrip("+-")) >= 16
            for value in values
        ):
            keep.append(name)
    return [name for name in keep if name]


# ─── header rows ─────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class _Layout:
    skip: int  # rows above the names
    label_row: int | None  # offset below the names of the label row (1), or None
    skipped: tuple[int, ...]  # offsets below the names of rows to drop (ImportId)
    qualtrics: bool
    detected: bool = False

    @property
    def extra(self) -> int:
        """Rows under the names that are not answers."""
        return max([0, *(self.label_row or 0,), *self.skipped])

    def options(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"skip_rows": self.skip, "header_rows": 1 + self.extra}
        if self.qualtrics:
            payload["qualtrics"] = True
        return payload


def detect_header(
    rows: list[list[Any]],
    *,
    header_rows: int | str | None = "auto",
    skip_rows: int | None = None,
    fields: bool = False,
) -> _Layout:
    """Where a table's names are, and what lies under them.

    The names are on the first row that fills at least half the table's width
    (and two cells), unless ``skip_rows`` says how many rows lie above them: a
    title, a note or an empty row above the names is not read as them. With
    ``fields`` (a text file's rows, as split), a row split into another number
    of fields than the table's rows are is not the names unless it fills most
    of the width: a title "Survey, March 2026" above three columns.
    ``header_rows`` counts the rows from the names down that are not answers:
    1 the names alone; 2 the names and a row of labels (question texts), which
    label the columns; 3 names, labels and a row that is dropped (the
    ``{"ImportId": ...}`` row of a Qualtrics CSV). ``"auto"`` finds a Qualtrics
    export — an ImportId row, or StartDate and ResponseId among the names
    with a text under StartDate and a date under that — and reads one row of
    names otherwise.
    """

    cells = [[_cell_text(cell) for cell in row] for row in rows[:_HEAD_ROWS]]
    if skip_rows is not None and not _is_auto(skip_rows):
        skip = int(skip_rows)
        if skip < 0:
            raise SnapshotReadError("Skip rows cannot be negative.")
    else:
        skip = _names_row(cells, fields)
    names = cells[skip] if skip < len(cells) else []

    def import_row(offset: int) -> bool:
        index = skip + offset
        if index >= len(cells):
            return False
        filled = [cell for cell in cells[index] if cell]
        return bool(filled) and all(_IMPORT_ID.match(cell) for cell in filled)

    qualtrics = _qualtrics_names(names)
    if _is_auto(header_rows):
        if import_row(2):
            return _Layout(skip, 1, (2,), True, detected=True)
        if import_row(1):
            return _Layout(skip, None, (1,), True, detected=True)
        if qualtrics and _label_like(cells, skip):
            return _Layout(skip, 1, (), True, detected=True)
        return _Layout(skip, None, (), False, detected=skip_rows is None)
    try:
        count = int(header_rows)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise SnapshotReadError(f"Header rows {header_rows!r} is not 1, 2 or 3 (or auto).") from exc
    if count not in (1, 2, 3):
        raise SnapshotReadError(f"Header rows {count} is not 1, 2 or 3 (or auto).")
    if count == 1:
        return _Layout(skip, None, (), qualtrics)
    return _Layout(skip, 1, (2,) if count == 3 else (), qualtrics or import_row(2))


def _cell_text(cell: Any) -> str:
    if cell is None or (isinstance(cell, float) and math.isnan(cell)):
        return ""
    if cell is pd.NaT:
        return ""
    return str(cell).strip()


def _names_row(cells: list[list[str]], fields: bool = False) -> int:
    widths = [sum(1 for cell in row if cell) for row in cells]
    if not widths:
        return 0
    width = max(widths)
    if width <= 1:
        return next((index for index, filled in enumerate(widths) if filled), 0)
    least = max(2, math.ceil(width / 2))
    lengths = Counter(len(row) for row, filled in zip(cells, widths, strict=True) if filled >= 2)
    usual = lengths.most_common(1)[0][0] if lengths else 0
    for index, filled in enumerate(widths[:20]):
        if filled < least:
            if not fields and _names_of_fewer(cells, index, width):
                return index
            continue
        if fields and len(cells[index]) != usual and filled < 0.8 * width:
            continue
        return index
    return 0


def _names_of_fewer(cells: list[list[str]], index: int, width: int) -> bool:
    """A sheet's names row that names fewer columns than the answers fill
    (columns beyond it have no header): three or more texts side by side,
    at least a quarter of the width, over a row of answers that spans them."""

    row = cells[index]
    filled = [position for position, cell in enumerate(row) if cell]
    if len(filled) < 3 or len(filled) * 4 < width or index + 1 >= len(cells):
        return False
    if len(filled) < 0.8 * (filled[-1] - filled[0] + 1):
        return False  # a group header over merged cells, not the names
    if any(
        _DIGITS_ONLY.match(row[position]) or _NUMBERISH.match(row[position]) for position in filled
    ):
        return False
    below = cells[index + 1]
    return (
        sum(1 for position in filled if position < len(below) and below[position])
        >= len(filled) * 0.8
    )


_NUMBERISH = re.compile(r"^[+-]?[\d\s.,]+%?$")


def _qualtrics_names(names: list[str]) -> bool:
    """Names a Qualtrics export starts with: StartDate and ResponseId among
    its fixed columns (Status, Progress or Finished alone are names any
    table may have)."""

    present = set(names)
    return "StartDate" in present and bool({"ResponseId", "ResponseID"} & present)


_DATE_LIKE = re.compile(r"^(?=.*\d)[\d/.:\- TtZ+]+$")


def _label_like(cells: list[list[str]], skip: int) -> bool:
    """The row under a Qualtrics export's names holds texts, not answers: its
    StartDate cell reads "Start Date" where the first answer's (the row after
    it) is a date."""

    if skip + 1 >= len(cells):
        return False
    names = cells[skip]
    column = names.index("StartDate")

    def cell(row: int) -> str:
        return cells[row][column] if row < len(cells) and column < len(cells[row]) else ""

    label = cell(skip + 1)
    if not label or _DATE_LIKE.match(label):
        return False
    return skip + 2 >= len(cells) or bool(_DATE_LIKE.match(cell(skip + 2)))


def _label_rows(frame: pd.DataFrame, layout: _Layout) -> tuple[dict[str, str], pd.DataFrame]:
    """The labels the label row gives, and the frame without the rows under
    the names that are not answers."""

    if not layout.extra or frame.empty:
        return {}, frame
    labels: dict[str, str] = {}
    if layout.label_row is not None and len(frame) >= layout.label_row:
        row = frame.iloc[layout.label_row - 1]
        for column, value in row.items():
            text = _cell_text(value)
            if text and not _IMPORT_ID.match(text):
                labels[str(column)] = " ".join(text.split())
    return labels, frame.iloc[layout.extra :].reset_index(drop=True)


def _tidy_names(frame: pd.DataFrame, notes: list[str], labels: dict[str, str]) -> pd.DataFrame:
    """Names without surrounding spaces; unnamed columns with nothing in them
    (a trailing delimiter, cells Excel formatted beyond the table) dropped."""

    renamed = {}
    for column in frame.columns:
        if isinstance(column, str) and column != column.strip() and column.strip():
            renamed[column] = column.strip()
    if renamed:
        clash = set(renamed.values()) & (set(frame.columns) - set(renamed))
        renamed = {old: new for old, new in renamed.items() if new not in clash}
        frame = frame.rename(columns=renamed)
        for old, new in renamed.items():
            if old in labels:
                labels[new] = labels.pop(old)
    empty = [
        column
        for column in frame.columns
        if (not isinstance(column, str) or column.startswith("Unnamed: ") or not column.strip())
        and frame[column].isna().all()
    ]
    if empty:
        frame = frame.drop(columns=empty)
    mangled = [
        str(column)
        for column in frame.columns
        if isinstance(column, str)
        and re.search(r"\.\d+$", column)
        and column.rsplit(".", 1)[0] in frame.columns
    ]
    if mangled:
        notes.append("Columns with the same name were renamed: " + ", ".join(mangled) + ".")
    unnamed = [
        str(column)
        for column in frame.columns
        if isinstance(column, str) and column.startswith("Unnamed: ")
    ]
    if unnamed:
        notes.append("Columns without a name were named " + ", ".join(unnamed) + ".")
    return frame


_TOTALS = frozenset(
    {
        "итого",
        "всего",
        "сумма",
        "total",
        "totals",
        "grand total",
        "sum",
        "summe",
        "gesamt",
        "total général",
    }
)


def _total_row(frame: pd.DataFrame, notes: list[str]) -> None:
    """Say so when the last row reads like a total a spreadsheet adds under
    its table ("Итого", "Total"): it is read as a respondent otherwise."""

    if frame.empty:
        return
    for value in frame.iloc[-1].tolist():
        if isinstance(value, str) and value.strip().rstrip(":").casefold() in _TOTALS:
            notes.append(
                f"The last row reads {value.strip()!r}, like a total under the table: it is "
                "read as a respondent. Delete it from the file, or filter it out."
            )
            return


# ─── workbooks ───────────────────────────────────────────────────────────────


def read_workbook(
    source: str | Path,
    *,
    sheet: str | int | None = "auto",
    header_rows: int | str | None = "auto",
    skip_rows: int | None = None,
    nrows: int | None = None,
    decimal: str | None = "auto",
    keep_text: Iterable[str] = (),
    **read_kwargs: Any,
) -> TableRead:
    """Read a sheet of an Excel workbook (``.xlsx``, ``.xlsm``, ``.xls``).

    ``sheet`` is a sheet's name or its number counting from 1; ``"auto"`` is
    the first sheet that holds a table (not a one-column note or an empty
    sheet), the first sheet when none does. The names row and the rows under
    it are found as in a text file (:func:`detect_header`). ``read_kwargs`` go
    to :func:`pandas.read_excel`; ``sheet_name=``, ``header=`` or ``skiprows=``
    among them are read as pandas reads them.

    Numbers a workbook keeps as text are read with ``decimal``; ``"auto"``
    takes the mark the sheet's text numbers show (``0,5`` or ``0.5``), ``.``
    in a Qualtrics export, and leaves a column of nothing but ``1,500``-like
    values as text (with a note) when nothing tells. ``keep_text`` as in
    :func:`read_text_table`.
    """

    path = Path(source)
    engine = _excel_engine(path)
    kwargs = dict(read_kwargs)
    kwargs.pop("engine", None)
    try:
        book = pd.ExcelFile(path, engine=engine)
    except ImportError as exc:
        raise SnapshotReadError(
            "Reading an .xls workbook (Excel 97–2003) needs the xlrd package "
            "(pip install 'xlrd>=2.0.1'); or save the workbook as .xlsx or CSV."
        ) from exc
    except Exception as exc:  # noqa: BLE001 - zip, XML and OLE errors alike
        raise SnapshotReadError(
            f"The file cannot be opened as an Excel workbook ({type(exc).__name__}: {exc}). "
            "Open it in Excel and save it as .xlsx or CSV UTF-8."
        ) from exc
    with book:
        sheets = [str(name) for name in book.sheet_names]
        options: dict[str, Any] = {"format": path.suffix.lower().lstrip("."), "sheets": sheets}
        if "sheet_name" in kwargs:
            chosen: Any = kwargs.pop("sheet_name")
            if isinstance(chosen, list) or chosen is None:
                raise SnapshotReadError("Read one sheet at a time: name it with sheet=.")
        elif _is_auto(sheet):
            chosen = _table_sheet(book, sheets)
            options["sheet_detected"] = True
        else:
            chosen = _sheet_named(sheet, sheets)
        options["sheet"] = chosen if isinstance(chosen, str) else sheets[int(chosen)]

        explicit = {"header", "skiprows", "names", "usecols"} & set(kwargs)
        if explicit:
            frame = book.parse(chosen, **kwargs)
            notes: list[str] = []
            frame = _tidy_names(frame, notes, {})
            return TableRead(frame=frame, labels={}, options=options, notes=notes)

        limit = None if nrows is None else nrows + _HEAD_ROWS
        raw = book.parse(
            chosen,
            header=None,
            dtype=object,
            keep_default_na=False,
            na_values=[""],
            nrows=limit,
            **kwargs,
        )
    if raw.empty:
        raise SnapshotReadError(f"Sheet {options['sheet']!r} is empty: there is no table to read.")
    head = raw.head(_HEAD_ROWS).to_numpy().tolist()
    layout = detect_header(head, header_rows=header_rows, skip_rows=skip_rows)
    options.update(layout.options())
    names = _unique_names([_cell_text(cell) for cell in raw.iloc[layout.skip].tolist()])
    labels: dict[str, str] = {}
    if layout.label_row is not None and layout.skip + 1 < len(raw):
        for name, value in zip(names, raw.iloc[layout.skip + 1].tolist(), strict=False):
            text = _cell_text(value)
            if text and not _IMPORT_ID.match(text):
                labels[name] = " ".join(text.split())
    data = raw.iloc[layout.skip + 1 + layout.extra :].reset_index(drop=True)
    data.columns = names
    if nrows is not None:
        data = data.head(nrows)
    # An empty row is no respondent (a CSV's empty line is skipped too).
    blank = data.isna().all(axis=1)
    if bool(blank.any()):
        data = data.loc[~blank].reset_index(drop=True)
    frame = data.infer_objects()
    notes = []
    frame = _tidy_names(frame, notes, labels)
    _total_row(frame, notes)
    # A workbook's numbers kept as text are written the way the locale of
    # whoever typed them writes numbers: 1 200,50 or 1,200.50.
    marks: tuple[str, ...] | None
    if not _is_auto(decimal):
        marks = (_decimal(str(decimal)),)
        options["decimal"] = marks[0]
    elif layout.qualtrics:
        marks = (".",)  # Qualtrics writes 4.5, and "1,3" for several answers
    else:
        found = decimal_evidence(frame)
        marks = None if found is None else (found, "," if found == "." else ".")
        if found is not None:
            options["decimal"] = found
            options["decimal_detected"] = True
    tidy_frame(frame, decimal=marks, keep_text=_named(frame, keep_text), notes=notes)
    return TableRead(frame=frame, labels=labels, options=options, notes=notes)


def _excel_engine(path: Path) -> Literal["openpyxl", "xlrd"]:
    """The reader a workbook needs, from its first bytes rather than its name:
    an ``.xls`` that is really an ``.xlsx`` (a zip) opens with openpyxl, and a
    web page saved as ``.xls`` is named for what it is."""

    with path.open("rb") as handle:
        magic = handle.read(512)
    if magic.startswith(b"PK"):
        return "openpyxl"
    if magic.startswith(b"\xd0\xcf\x11\xe0"):
        return "xlrd"
    text = magic.lstrip().lower()
    if text.startswith((b"<html", b"<!doctype", b"<table", b"<meta")) or b"<html" in text:
        raise SnapshotReadError(
            "This file is a web page (HTML) named like a workbook, as some systems export "
            '"Excel" files: open it in Excel and save it as .xlsx or CSV UTF-8.'
        )
    if text.startswith(b"<?xml"):
        raise SnapshotReadError(
            "This file is an XML spreadsheet (Excel 2003 XML), which cannot be read here: "
            "open it in Excel and save it as .xlsx or CSV UTF-8."
        )
    if not magic:
        raise SnapshotReadError("The file is empty: there is no table to read.")
    raise SnapshotReadError(
        "The file is not an Excel workbook: open it in Excel and save it as .xlsx or CSV UTF-8."
    )


def _sheet_named(sheet: Any, sheets: list[str]) -> Any:
    text = str(sheet).strip()
    if text in sheets:
        return text
    lowered = {name.lower(): name for name in sheets}
    if text.lower() in lowered:
        return lowered[text.lower()]
    if re.fullmatch(r"\d+", text):
        number = int(text)
        if 1 <= number <= len(sheets):
            return number - 1
        raise SnapshotReadError(
            f"There is no sheet {number}: this workbook has {len(sheets)} "
            f"({', '.join(sheets)})."
        )
    raise SnapshotReadError(f"No sheet named {text!r}; this workbook has: {', '.join(sheets)}.")


#: Sheet names of the documentation a workbook carries beside its data.
_DOCUMENT_SHEETS = re.compile(
    r"codebook|code ?book|variables?|dictionary|readme|read me|info|notes?|labels?|legend|"
    r"description|metadata|about|instructions?|кодиров|кодбук|переменн|описани|словар|"
    r"справк|инструкц|метаданн|легенд",
    re.IGNORECASE,
)


def _table_sheet(book: pd.ExcelFile, sheets: list[str]) -> Any:
    """The first sheet whose top holds a table (two columns and two rows)
    and that does not document another: one named like a codebook or a
    README, or one that lists another sheet's names (a "Variables" sheet
    before "Data"), is passed over when another table is there."""

    tables: list[tuple[int, str, list[list[str]]]] = []
    for index, name in enumerate(sheets):
        try:
            head = book.parse(index, header=None, dtype=object, nrows=_HEAD_ROWS)
        except Exception:  # noqa: BLE001 - a chart sheet, a broken one
            continue
        cells = [[_cell_text(cell) for cell in row] for row in head.to_numpy().tolist()]
        widths = [sum(1 for cell in row if cell) for row in cells]
        if max(widths, default=0) >= 2 and sum(1 for width in widths if width) >= 2:
            tables.append((index, name, cells))
    if not tables:
        return 0
    names = {
        index: {cell for cell in cells[_names_row(cells)] if cell} if cells else set()
        for index, _name, cells in tables
    }

    def documents(index: int, name: str, cells: list[list[str]]) -> bool:
        if _DOCUMENT_SHEETS.search(name):
            return True
        values = {cell for row in cells for cell in row if cell}
        return any(
            len(names[other] & values) >= max(2, min(len(names[other]), _HEAD_ROWS) // 2)
            for other, _other_name, _cells in tables
            if other != index
        )

    return next(
        (index for index, name, cells in tables if not documents(index, name, cells)),
        tables[0][0],
    )


def _unique_names(names: list[str]) -> list[str]:
    """Names as pandas makes them: ``Unnamed: 3`` for an empty one, ``q1.1``
    for a second ``q1``."""

    seen: Counter[str] = Counter()
    out: list[str] = []
    for index, name in enumerate(names):
        base = name or f"Unnamed: {index}"
        candidate = base
        while candidate in seen:
            seen[base] += 1
            candidate = f"{base}.{seen[base]}"
        seen[candidate] += 1
        out.append(candidate)
    return out


# ─── types ───────────────────────────────────────────────────────────────────


def tidy_frame(
    frame: pd.DataFrame,
    *,
    decimal: str | tuple[str, ...] | None = ".",
    columns: list[Any] | None = None,
    keep_text: list[str] | None = None,
    notes: list[str] | None = None,
) -> pd.DataFrame:
    """Give text columns the type their values have, in place.

    A column read as text because its cells are text — an Excel export's
    ``"100.0"``, ``"True"``, a Qualtrics date, a number with a thousands
    space or a decimal comma, a number column with one blank or a ``-`` —
    becomes numbers, true/false or dates when every value it holds reads so;
    cells of spaces, and ``-``, ``NA``, ``#N/A`` … in such a column, are
    blanks. Anything else stays the text it is (a cell of spaces blank).
    ``decimal`` is the file's decimal mark, or the marks to try in turn
    (``(",", ".")``: a column whose decimals come only past the rows the mark
    was told by still reads). None reads a column written with either
    (``1 200,50`` or ``1,200.50``, as a workbook's text cells may be), but
    leaves as text a column whose every value is as ambiguous as ``1,500``
    (one and a half, or fifteen hundred), saying so in ``notes``.
    ``columns`` limits it to some columns; ``keep_text`` columns (codes with
    a leading zero, answers the questionnaire says are lists) are left as
    text.
    """

    keep = set(keep_text or ())
    for column in list(frame.columns if columns is None else columns):
        if column not in frame.columns or column in keep:
            continue
        series = frame[column]
        if series.dtype != object:
            continue
        if decimal is None and _ambiguous_commas(series):
            if notes is not None:
                notes.append(
                    f"{column}: its values are written like 1,500, which may be a decimal "
                    "comma (1.5) or a thousands comma (1500), so they are kept as text: set "
                    "Decimal mark."
                )
            blanked = _blanks(series)
            if blanked is not None:
                frame[column] = blanked
            continue
        typed = typed_column(series, decimal=decimal)
        if typed is not None:
            frame[column] = typed
    return frame


_AMBIGUOUS_COMMA = re.compile(r"^[+-]?\d{1,3}(?:,\d{3})+$")
_COMMA_EVIDENCE = re.compile(
    r"^[+-]?\d+,(?:\d{1,2}|\d{4,})%?$|^[+-]?\d{1,3}(?:[ .\u00a0\u202f]\d{3})+,\d+%?$"
)
_POINT_EVIDENCE = re.compile(
    r"^[+-]?\d+\.(?:\d{1,2}|\d{4,})%?$|^[+-]?\d{1,3}(?:[ ,\u00a0\u202f]\d{3})+\.\d+%?$"
)


def _ambiguous_commas(series: pd.Series) -> bool:
    """Every value a number like ``1,500`` or ``12,250``: one and a half with
    a decimal comma, fifteen hundred with a thousands comma."""

    values = []
    for value in series.dropna():
        if not isinstance(value, str):
            return False
        text = value.strip()
        if text and text.lower() not in NA_TOKENS:
            values.append(text)
    return bool(values) and all(_AMBIGUOUS_COMMA.match(text) for text in values)


def decimal_evidence(frame: pd.DataFrame) -> str | None:
    """The decimal mark a workbook's numbers kept as text are written with —
    ``,`` when more of them read unmistakably so (``0,5``, ``12,25``,
    ``1 234,5``) than with ``.``, ``.`` when fewer — or None when none tell."""

    comma = point = 0
    for column in frame.columns:
        series = frame[column]
        if series.dtype != object:
            continue
        for value in series.dropna().head(_TYPE_SAMPLE):
            if not isinstance(value, str):
                continue
            text = value.strip()
            if _COMMA_EVIDENCE.match(text):
                comma += 1
            elif _POINT_EVIDENCE.match(text):
                point += 1
    if comma > point:
        return ","
    if point > comma:
        return "."
    return None


def _marks(decimal: str | tuple[str, ...] | None) -> tuple[str, ...]:
    if decimal is None:
        return (".", ",")
    if isinstance(decimal, str):
        return (decimal,)
    return tuple(decimal)


def typed_column(
    series: pd.Series, *, decimal: str | tuple[str, ...] | None = "."
) -> pd.Series | None:
    """``series`` (text) with the type its values have, or None to keep it."""

    values = series.dropna()
    if values.empty:
        return None
    # A column of text shows it in its first answers: only one whose sample
    # reads as numbers, dates or true/false is read in full, so a large file's
    # open answers are not gone through cell by cell.
    if len(values) > _TYPE_SAMPLE and _typed(values.iloc[:_TYPE_SAMPLE], decimal) is None:
        return _blanks(series)
    typed = _typed(values, decimal)
    if typed is None:
        return _blanks(series)
    kind, result = typed
    if kind == "boolean":
        out = pd.Series(np.nan, index=series.index, dtype=object)
        out.loc[result.index] = result
        return out.astype("boolean") if out.isna().any() else out.astype(bool)
    if kind in {"integer", "number"}:
        out = pd.Series(np.nan, index=series.index, dtype=float)
        out.loc[result.index] = result.astype(float)
        if kind == "integer" and not out.isna().any():
            return out.astype("int64")
        return out
    out = pd.Series(pd.NaT, index=series.index, dtype=result.dtype)
    out.loc[result.index] = result
    return out


_TYPE_SAMPLE = 500


def _typed(
    values: pd.Series, decimal: str | tuple[str, ...] | None
) -> tuple[str, pd.Series] | None:
    """What non-missing ``values`` read as — ``boolean``, ``integer``,
    ``number`` or ``date`` with the values so read (blanks and NA tokens left
    out) — or None when some are text."""

    texts = values.map(lambda value: value.strip() if isinstance(value, str) else value)
    empty = texts.map(
        lambda value: isinstance(value, str) and (value == "" or value.lower() in NA_TOKENS)
    )
    filled = texts[~empty]
    if filled.empty:
        return None
    booleans = _as_booleans(filled)
    if booleans is not None:
        return "boolean", booleans
    for mark in _marks(decimal):
        numbers = _as_numbers(filled, mark)
        if numbers is not None:
            whole = bool((numbers % 1 == 0).all()) and _all_integers(filled)
            return ("integer" if whole else "number"), numbers
    dates = _as_dates(filled)
    if dates is not None:
        return "date", dates
    return None


def _blanks(series: pd.Series) -> pd.Series | None:
    """``series`` with its cells of spaces blank, or None when it has none."""

    try:
        blank = series.str.strip().eq("")
    except AttributeError:  # no text in it
        return None
    if not bool(blank.any()):
        return None
    return series.mask(blank, np.nan)


def _all_integers(values: pd.Series) -> bool:
    return all(
        (isinstance(value, int | np.integer) and not isinstance(value, bool))
        or (isinstance(value, str) and _DIGITS_ONLY.match(value.replace(" ", "")))
        for value in values
    )


def _as_booleans(values: pd.Series) -> pd.Series | None:
    out = []
    for value in values:
        if isinstance(value, bool | np.bool_):
            out.append(bool(value))
        elif isinstance(value, str) and value.lower() in _BOOLS:
            out.append(_BOOLS[value.lower()])
        else:
            return None
    return pd.Series(out, index=values.index, dtype=object)


def _as_numbers(values: pd.Series, decimal: str) -> pd.Series | None:
    thousands = "." if decimal == "," else ","
    pattern = re.compile(
        rf"^[+-]?(?:\d{{1,3}}(?:[{re.escape(thousands)}{_SPACES}]\d{{3}})+|\d+)"
        rf"(?:{re.escape(decimal)}\d+)?(?:[eE][+-]?\d+)?%?$"
        rf"|^[+-]?{re.escape(decimal)}\d+$"
    )
    out = []
    for value in values:
        if isinstance(value, bool | np.bool_):
            return None
        if isinstance(value, int | float | np.integer | np.floating):
            out.append(float(value))
            continue
        if not isinstance(value, str):
            return None
        text = value.replace("\u2212", "-")
        if not pattern.match(text):
            return None
        digits = text.rstrip("%")
        for mark in _SPACES:
            digits = digits.replace(mark, "")
        if re.search(rf"\d{re.escape(thousands)}\d{{3}}", digits):
            digits = digits.replace(thousands, "")
        if decimal == ",":
            digits = digits.replace(",", ".")
        if (
            _DIGITS_ONLY.match(digits)
            and len(digits.lstrip("+-")) > 1
            and digits.lstrip("+-").startswith("0")
        ):
            return None  # 00123: a code, not the number 123
        try:
            out.append(float(digits))
        except ValueError:
            return None
    return pd.Series(out, index=values.index, dtype=float)


def _as_dates(values: pd.Series) -> pd.Series | None:
    stamps = (_dt.datetime, _dt.date, pd.Timestamp)
    if all(isinstance(value, stamps) for value in values):
        try:
            return pd.to_datetime(values)
        except (ValueError, TypeError):
            return None
    # A workbook may hold some dates as dates and the rest as text.
    texts = [
        value.isoformat(sep=" ") if isinstance(value, _dt.datetime) else value for value in values
    ]
    if not all(isinstance(text, str) for text in texts):
        return None
    series = pd.Series(texts, index=values.index, dtype=object)
    try:
        if all(_ISO_DATE.match(text) for text in texts):
            return pd.to_datetime(series, format="ISO8601")
        if all(_DOT_DATE.match(text) for text in texts):
            return pd.to_datetime(series, dayfirst=True, format="mixed")
        slash = [_SLASH_DATE.match(text) for text in texts]
        if all(slash):
            dayfirst = any(int(match.group(1)) > 12 for match in slash if match)
            return pd.to_datetime(series, dayfirst=dayfirst, format="mixed")
    except (ValueError, TypeError, OverflowError):
        return None
    return None


__all__ = [
    "DELIMITERS",
    "LEGACY_ENCODINGS",
    "QUALTRICS_COLUMNS",
    "SnapshotReadError",
    "TableRead",
    "detect_decimal",
    "detect_encoding",
    "detect_header",
    "decimal_evidence",
    "legacy_encoding",
    "normal_name",
    "read_text_table",
    "read_workbook",
    "sniff_delimiter",
    "tidy_frame",
    "typed_column",
]
