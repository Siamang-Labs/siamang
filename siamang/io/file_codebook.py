"""The codebook a data file brings with it, and whether a questionnaire's fits it.

A file uploaded for analysis is not always the survey's own data: a client's
spreadsheet, a national survey, a Qualtrics export.
Such a file keeps its own names and gets a codebook of its own — the labels a
label row gives its columns, scales guessed from the values
(:func:`infer_scale`), the missing codes declared for it — rather than the
labels and scales of whatever questionnaire variable happens to share a
column's name. :func:`questionnaire_match` decides whether the questionnaire
describes the file: at least half of the file's columns (response metadata
left out) are its variables and they are at least half of its variables, or
the file's own dictionary labels them as the questionnaire does; and their
answers fit them.

The same module flags what a researcher should look at before analysing:
numbers that look like missing codes (``-7``, ``-9``, ``99`` …), and columns
that hold personal data (e-mail and IP addresses, locations, names, phone
numbers, panel IDs), which are best dropped before anything else.
"""

from __future__ import annotations

import csv
import html
import math
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from typing import Any

import numpy as np
import pandas as pd

from siamang.core.variable import MissingValue, Variable, VariableMap
from siamang.io.tabular import QUALTRICS_COLUMNS, normal_name

#: Columns a survey's data carries beside its answers (ids, timestamps, a
#: platform's flags, Qualtrics' fixed columns): not counted when deciding
#: whether a file is a questionnaire's data.
METADATA_COLUMNS = frozenset(
    {
        "id",
        "_id",
        "uuid",
        "respondent_id",
        "respondent",
        "response_id",
        "responseid",
        "survey_id",
        "session_id",
        "partial",
        "environment",
        "created_at",
        "updated_at",
        "started_at",
        "submitted_at",
        "duration",
        "duration_s",
        "weight",
        # Studio's Data export (meta): fieldwork signals beside the answers.
        "captcha",
        "tab_switches",
        "hidden_seconds",
        "pastes",
        "last_page",
        *(name.lower() for name in QUALTRICS_COLUMNS),
    }
)
#: Metadata by the shape of its name: a survey link's parameters (``url_…``),
#: a platform's own state (``__status``), Qualtrics' ``Q_`` metadata
#: (``Q_RecaptchaScore``, ``Q_TotalDuration``) and display-order columns
#: (``Q1_DO``, ``FL_6_DO``).
_METADATA_SHAPES = re.compile(r"^url_|^__|^Q_[A-Z][A-Za-z]+$|(?:^|_)DO(?:_\d+)?$")
#: A companion of a variable: its "Other (please specify)" text (``q5_other``,
#: Qualtrics' ``Q5_4_TEXT``).
_COMPANION = re.compile(r"^(?P<base>.+?)(?:_\d+)?_(?:other|TEXT|text)$")
#: Negative codes surveys use for "does not apply", "don't know", "refused".
MISSING_LIKE_NEGATIVE = frozenset(
    {-1, -2, -3, -4, -5, -6, -7, -8, -9, -97, -98, -99, -997, -998, -999}
)
#: High codes used the same way, when the answers' codes are far below them.
MISSING_LIKE_HIGH = frozenset({97, 98, 99, 997, 998, 999, 9997, 9998, 9999})

_PERSONAL_NAMES: dict[str, frozenset[str]] = {
    "e-mail": frozenset(
        {
            "email",
            "e_mail",
            "mail",
            "emailaddress",
            "email_address",
            "recipientemail",
            "почта",
            "электронная_почта",
            "эл_почта",
        }
    ),
    "IP address": frozenset({"ipaddress", "ip", "ip_address", "ipaddr", "ip_adres"}),
    "location": frozenset(
        {
            "locationlatitude",
            "locationlongitude",
            "latitude",
            "longitude",
            "lat",
            "lon",
            "lng",
            "geolocation",
            "geo",
            "coordinates",
            "gps",
        }
    ),
    "name": frozenset(
        {
            "recipientfirstname",
            "recipientlastname",
            "firstname",
            "first_name",
            "lastname",
            "last_name",
            "surname",
            "fullname",
            "full_name",
            "name",
            "фио",
            "имя",
            "фамилия",
            "отчество",
        }
    ),
    "phone": frozenset(
        {"phone", "phone_number", "phonenumber", "telephone", "tel", "mobile", "телефон"}
    ),
    "participant ID": frozenset(
        {
            "prolific_id",
            "prolificid",
            "prolific_pid",
            "pid",
            "workerid",
            "worker_id",
            "mturk_id",
            "mturkid",
            "externalreference",
            "externaldatareference",
            "panel_id",
            "panelist_id",
        }
    ),
    "address": frozenset(
        {"address", "street", "postcode", "zip", "zipcode", "zip_code", "postal_code", "адрес"}
    ),
}
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_IPV4 = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")
_IPV6 = re.compile(r"^[0-9a-fA-F]{0,4}(?::[0-9a-fA-F]{0,4}){2,7}$")
_TAGS = re.compile(r"<[^>]+>")
_NUMBER = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")


# ─── names ───────────────────────────────────────────────────────────────────


def personal_data(name: Any, series: pd.Series | None = None) -> str | None:
    """What personal data a column looks like it holds — ``"e-mail"``, ``"IP
    address"``, ``"location"``, ``"name"``, ``"phone"``, ``"participant ID"``,
    ``"address"`` — by its name, or by its values (e-mail and IP addresses),
    else None. A hint to drop the column early, never a verdict."""

    normal = normal_name(name)
    squeezed = normal.replace("_", "")
    for kind, names in _PERSONAL_NAMES.items():
        if normal in names or squeezed in names:
            return kind
    if series is None or series.dtype != object:
        return None
    texts = [value.strip() for value in series.dropna().head(200) if isinstance(value, str)]
    if len(texts) < 1:
        return None
    for kind, pattern in (("e-mail", _EMAIL), ("IP address", _IPV4), ("IP address", _IPV6)):
        hits = sum(1 for text in texts if pattern.match(text))
        if hits and hits >= 0.5 * len(texts):
            return kind
    return None


# ─── missing codes ───────────────────────────────────────────────────────────


#: The key of :func:`parse_missing`'s mapping for codes of every column.
EVERY_COLUMN = "*"


def parse_missing(value: Any) -> list[Any] | dict[str, list[Any]]:
    """Missing codes as a node or a caller gives them: ``"-7, -8, -9"`` (commas
    or spaces between them) for every column that holds them, a list, or
    ``{column: codes}`` — also as text, ``"sought_advice: -9; source_1: -7,
    -8"`` (a ``;`` between columns; a name holding ``;`` or ``:`` in double
    quotes). Codes given without a column in such a text are every column's
    (under :data:`EVERY_COLUMN`)."""

    if value is None or (isinstance(value, str) and not value.strip()):
        return []
    if isinstance(value, Mapping):
        return {str(column): _codes(codes) for column, codes in value.items()}
    if isinstance(value, str) and ":" in value:
        return _per_column(value)
    return _codes(value)


def _per_column(text: str) -> dict[str, list[Any]]:
    found: dict[str, list[Any]] = {}
    segments = next(csv.reader([text.replace("\n", ";")], delimiter=";", skipinitialspace=True))
    for segment in segments:
        if not segment.strip():
            continue
        name, colon, codes = segment.rpartition(":")
        column = name.strip() if colon else EVERY_COLUMN
        if colon and not column:
            raise ValueError(f"Missing codes {segment.strip()!r} name no column before the colon.")
        for code in _codes(codes if colon else segment):
            if code not in found.setdefault(column, []):
                found[column].append(code)
    return found


def missing_text(codes: Mapping[str, Iterable[Any]]) -> str:
    """``{column: codes}`` as the Missing codes text :func:`parse_missing`
    reads back: ``"sought_advice: -9; source_1: -7"``."""

    parts = []
    for column, values in codes.items():
        quoted = re.search(r'[;:"]', column) or column != column.strip()
        name = '"' + column.replace('"', '""') + '"' if quoted else column
        parts.append(f"{name}: {', '.join(str(_code(value)) for value in values)}")
    return "; ".join(parts)


def _codes(value: Any) -> list[Any]:
    if isinstance(value, str):
        items: Iterable[Any] = [
            part for part in re.split(r"[,;\s]+", value.replace("\u2212", "-")) if part
        ]
    elif isinstance(value, Iterable):
        items = value
    else:
        items = [value]
    codes: list[Any] = []
    for item in items:
        code = _code(item)
        if code is None:
            raise ValueError(f"Missing code {item!r} is not a number or a code.")
        if code not in codes:
            codes.append(code)
    return codes


def _code(item: Any) -> Any:
    if isinstance(item, bool):
        return None
    if isinstance(item, int | np.integer):
        return int(item)
    if isinstance(item, float | np.floating):
        return int(item) if float(item).is_integer() else float(item)
    if isinstance(item, str):
        text = item.strip()
        if not text:
            return None
        try:
            number = float(text)
        except ValueError:
            return text
        return int(number) if number.is_integer() else number
    return None


def suspected_missing(series: pd.Series, declared: Iterable[Any] = ()) -> list[Any]:
    """Codes in a numeric column that look like missing codes: negative codes
    such as -7, -8, -9 or -99 in a column whose other values (if any) are not
    negative;
    97, 98, 99, 999 … in a column of whole numbers far below them. Codes
    already declared missing are not suspected again. A guess to confirm
    (the Data file's Missing codes), never applied by itself: a column of
    changes (-3 … 3) or of years (1999) is left alone."""

    if not pd.api.types.is_numeric_dtype(series) or pd.api.types.is_bool_dtype(series):
        return []
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return []
    known = {float(code) for code in declared if isinstance(code, int | float)}
    distinct = sorted(float(value) for value in values.unique() if float(value) not in known)
    whole = [value for value in distinct if value.is_integer()]
    found: list[Any] = []
    negative = [value for value in whole if int(value) in MISSING_LIKE_NEGATIVE]
    rest = [value for value in distinct if value not in negative]
    if rest and not all(value.is_integer() for value in rest):
        # Among amounts, -1 or -2 may be amounts; -7, -8, -9 and -99 hardly are.
        negative = [value for value in negative if value <= -7]
    if negative and (not rest or min(rest) >= 0):
        # A column of nothing but -7 is one nobody was asked.
        found.extend(int(value) for value in negative)
    high = [value for value in whole if int(value) in MISSING_LIKE_HIGH]
    rest = [value for value in distinct if value not in high and value not in negative]
    if (
        high
        and rest
        and all(value.is_integer() for value in rest)
        and len(rest) <= 20
        and max(rest) < min(high) / 2
    ):
        found.extend(int(value) for value in high)
    return sorted(found)


# ─── scales ──────────────────────────────────────────────────────────────────


def column_type(series: pd.Series) -> str:
    """What a column holds, in words a builder shows: ``boolean``, ``date``,
    ``integer``, ``number``, ``list`` (several answers in a cell), ``text``, or
    ``empty`` when no cell holds a value (a Qualtrics export's recipient
    columns of an anonymous link)."""

    if series.isna().all():
        return "empty"
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "date"
    if pd.api.types.is_numeric_dtype(series):
        values = series.dropna()
        if values.empty or bool((values % 1 == 0).all()):
            return "integer"
        return "number"
    if series.dropna().map(lambda value: isinstance(value, list | tuple)).any():
        return "list"
    values = series.dropna()
    if not values.empty and values.map(lambda value: isinstance(value, bool | np.bool_)).all():
        return "boolean"
    return "text"


def infer_scale(series: pd.Series, missing: Iterable[Any] = ()) -> str:
    """The measurement level a column's values suggest — a guess, marked so
    wherever it is shown: true/false and text nominal; dates interval; whole
    numbers with two values nominal, with three to ten consecutive values
    between 0 and 10 ordinal (a rating), with up to twelve others below 100
    that repeat nominal (codes); any other numbers ratio, interval when some
    are negative. Missing codes, declared or suspected
    (:func:`suspected_missing`), are left out first."""

    kind = column_type(series)
    if kind in {"boolean", "text", "list", "empty"}:
        return "nominal"
    if kind == "date":
        return "interval"
    missing = list(missing)
    missing += suspected_missing(series, missing)
    left_out = {float(code) for code in missing if isinstance(code, int | float)}
    values = pd.to_numeric(series, errors="coerce").dropna()
    values = values[~values.astype(float).isin(left_out)]
    if values.empty:
        return "nominal"
    distinct = sorted(float(value) for value in values.unique())
    integral = all(value.is_integer() for value in distinct)
    low, high = distinct[0], distinct[-1]
    if integral and len(distinct) <= 2:
        return "nominal"
    consecutive = high - low + 1 == len(distinct)
    if integral and len(distinct) <= 10 and consecutive and low >= 0 and high <= 10:
        return "ordinal"
    # Codes repeat; a handful of ages in a small file do not.
    repeated = len(values) >= 2 * len(distinct)
    if integral and len(distinct) <= 12 and low >= 0 and high < 100 and repeated:
        return "nominal"
    return "ratio" if low >= 0 else "interval"


def file_variables(
    frame: pd.DataFrame,
    labels: Mapping[str, str] | None = None,
    missing: list[Any] | Mapping[str, list[Any]] | None = None,
) -> VariableMap:
    """A codebook for a file from the file alone: a variable per column, its
    label from the file's label row (a Qualtrics export's question texts),
    its scale guessed from its values (:func:`infer_scale`), and the missing
    codes declared for it (every numeric column holding one, or ``{column:
    codes}``). Categorical whole-number columns come back as ``Int64``, as a
    codebook's integer codes do (in ``frame`` itself)."""

    labels = labels or {}
    variables = VariableMap()
    for column in frame.columns:
        name = str(column)
        series = frame[column]
        declared = _declared_for(name, series, missing)
        scale = infer_scale(series, declared)
        label = labels.get(name)
        variables.add(
            Variable(
                name=name,
                scale=scale,
                label=label if label and label != name else None,
                missing=tuple(MissingValue(code, str(code)) for code in declared),
            )
        )
        if (
            scale in {"nominal", "ordinal"}
            and pd.api.types.is_float_dtype(series)
            and bool((series.dropna() % 1 == 0).all())
        ):
            frame[column] = series.round().astype("Int64")
    return variables


def _declared_for(
    name: str, series: pd.Series, missing: list[Any] | Mapping[str, list[Any]] | None
) -> list[Any]:
    """The declared codes that are missing codes of column ``name``: its own,
    and those given for every column that it holds — but not a negative code
    in a column of other negative values (a balance of -7.0 among -2 300 and
    -120.75 is an amount, not "does not apply")."""

    if not missing:
        return []
    if isinstance(missing, Mapping):
        own = list(missing.get(name, ()))
        every = [code for code in missing.get(EVERY_COLUMN, ()) if code not in own]
    else:
        own, every = [], list(missing)
    if (not own and not every) or pd.api.types.is_bool_dtype(series):
        return []
    present = _present_codes(series)
    codes = [code for code in own if _code_text(code) in present]
    if every:
        negatives = _other_negatives(series, every)
        codes += [
            code
            for code in every
            if _code_text(code) in present
            and not (isinstance(code, int | float) and code < 0 and negatives)
        ]
    return codes


def _other_negatives(series: pd.Series, codes: Iterable[Any]) -> bool:
    """Whether a numeric column holds negative values besides ``codes``."""

    if not pd.api.types.is_numeric_dtype(series) or pd.api.types.is_bool_dtype(series):
        return False
    known = {float(code) for code in codes if isinstance(code, int | float)}
    values = pd.to_numeric(series, errors="coerce").dropna()
    return bool(((values < 0) & ~values.astype(float).isin(known)).any())


def _present_codes(series: pd.Series) -> set[str]:
    values = series.dropna()
    if values.empty:
        return set()
    return {_code_text(value) for value in values.unique()[:5000]}


def _code_text(value: Any) -> str:
    if isinstance(value, float | np.floating) and float(value).is_integer():
        return str(int(value))
    if isinstance(value, np.integer):
        return str(int(value))
    return str(value).strip()


def with_missing(
    variables: VariableMap, frame: pd.DataFrame, missing: list[Any] | Mapping[str, list[Any]]
) -> VariableMap:
    """``variables`` with the declared ``missing`` codes added to every
    variable whose column holds one (a copy; the questionnaire's own
    variables are not changed)."""

    out = VariableMap()
    for name, variable in variables.items():
        declared = _declared_for(name, frame[name], missing) if name in frame.columns else []
        extra = [code for code in declared if code not in variable.missing_values]
        if extra:
            variable = replace(
                variable,
                missing=variable.missing + tuple(MissingValue(code, str(code)) for code in extra),
                missing_values=(),
                missing_labels={},
            )
        out.add(variable)
    return out


# ─── the questionnaire ───────────────────────────────────────────────────────


@dataclass(slots=True)
class QuestionnaireMatch:
    """How a file's columns meet a questionnaire's codebook."""

    #: The file's columns that could be answers (response metadata left out).
    columns: int
    #: The questionnaire's variables.
    variables: int = 0
    #: Those of the file's columns that are its variables (by name as renamed).
    shared: list[str] = field(default_factory=list)
    #: File column -> the variable it is, where only case or punctuation differ
    #: (``Q1`` -> ``q1``).
    renamed: dict[str, str] = field(default_factory=dict)
    #: Variable -> why the column's values do not fit it.
    conflicts: dict[str, str] = field(default_factory=dict)
    #: The file's own codebook (a dictionary, SPSS or Stata metadata) labels
    #: the variables it shares with the questionnaire as the questionnaire
    #: does: a table a flow of this project wrote.
    agrees: bool = False

    @property
    def matches(self) -> bool:
        """The file is the questionnaire's data: no more than a quarter of the
        shared columns hold values that do not fit their variables, and
        either at least half of the file's answer columns are the
        questionnaire's variables and they are at least half of its variables
        — the survey's responses, whole or nearly (a small file whose
        ``gender``, ``age`` and ``comment`` share names with a survey's is not
        its data) — or the file's own codebook labels them as the
        questionnaire does (``agrees``: a table a flow of the project wrote,
        with the variables it made beside a few of the survey's)."""

        if not self.shared or not self.columns:
            return False
        shared = len(self.shared)
        if len(self.conflicts) * 4 > shared:
            return False
        return self.agrees or (
            shared >= math.ceil(self.columns / 2) and shared >= math.ceil(self.variables / 2)
        )

    def fits(self, name: str) -> bool:
        """Whether column ``name`` is the questionnaire's variable, answers
        and all."""
        return name in self.shared and name not in self.conflicts

    def to_json(self) -> dict[str, Any]:
        return {
            "matches": self.matches,
            "columns": self.columns,
            "variables": self.variables,
            "shared": list(self.shared),
            "renamed": dict(self.renamed),
            "conflicts": dict(self.conflicts),
            "agrees": self.agrees,
        }


def questionnaire_match(
    frame: pd.DataFrame,
    variables: VariableMap,
    several: Iterable[str] = (),
    own: VariableMap | None = None,
) -> QuestionnaireMatch:
    """Whether ``variables`` (a questionnaire's codebook) describe ``frame``.

    A column is the questionnaire's variable by name — as it is, or with case
    and punctuation aside when that names exactly one (``Q1`` for ``q1``, as
    the Qualtrics importer names a question's export tag). Its values fit
    when each is one of the variable's codes, missing codes or value labels
    (a choice-text export), or a number for a numeric variable; ``several``
    columns hold several answers in a cell (``1;3``). ``own`` is the codebook
    the file brings (a dictionary, embedded metadata), compared with the
    questionnaire's on the variables both label.
    """

    several = set(several)
    by_normal: dict[str, list[str]] = {}
    for name in variables:
        by_normal.setdefault(normal_name(name), []).append(name)
    columns = [str(column) for column in frame.columns]
    present = set(columns)
    candidates = [
        column
        for column in columns
        if column in variables
        or not (is_metadata(column) or _companion(column, variables, by_normal))
    ]
    match = QuestionnaireMatch(columns=len(candidates), variables=len(variables))
    for column in candidates:
        name = column
        if column not in variables:
            options = by_normal.get(normal_name(column), [])
            if len(options) != 1 or options[0] in present:
                continue
            name = options[0]
            match.renamed[column] = name
        match.shared.append(name)
        problem = _misfit(frame[column], variables[name], several=name in several)
        if problem:
            match.conflicts[name] = problem
    if own is not None:
        labelled = [
            name
            for name in match.shared
            if name in own and (variables[name].labels or own[name].labels)
        ]
        match.agrees = bool(labelled) and all(
            _labels_of(own[name]) == _labels_of(variables[name]) for name in labelled
        )
    return match


def is_metadata(name: Any) -> bool:
    """Whether a column is response metadata rather than an answer: an id, a
    timestamp, a platform's fieldwork signal (Studio's export: ``captcha``,
    ``tab_switches``, ``url_…``; a copy of such a column renamed ``_id`` where
    an answer took its name), Qualtrics' fixed columns, ``Q_`` metadata and
    display orders."""

    text = str(name)
    bare = text.lstrip("_") or text
    if text.startswith("__") or _METADATA_SHAPES.search(text):
        return True
    return (
        bare.lower() in METADATA_COLUMNS
        or normal_name(bare) in METADATA_COLUMNS
        or bool(_METADATA_SHAPES.search(bare))
    )


def _companion(column: str, variables: VariableMap, by_normal: Mapping[str, list[str]]) -> bool:
    """A column that goes with a questionnaire variable rather than being an
    answer of its own: its "Other" text (``q5_other``, ``Q5_4_TEXT``)."""

    found = _COMPANION.match(column)
    if found is None:
        return False
    base = found.group("base")
    return base in variables or normal_name(base) in by_normal


def _labels_of(variable: Variable) -> dict[str, str]:
    """A variable's value labels, its labelled missing codes among them: SPSS
    keeps "9 refused" apart from the answers' labels, a questionnaire among
    them, and both say the same."""

    labelled = {**variable.labels, **variable.missing_labels}
    return {_code_text(code): label_text(label) for code, label in labelled.items()}


def _misfit(series: pd.Series, variable: Variable, *, several: bool) -> str | None:
    values = series.dropna()
    if values.empty:
        return None
    if several:
        flat: list[Any] = []
        for value in values:
            if isinstance(value, list | tuple):
                flat.extend(value)
            elif isinstance(value, str):
                answers = several_answers(value, variable)
                flat.extend([value] if answers is None else answers)
            else:
                flat.append(value)
        values = pd.Series(flat, dtype=object)
    distinct = list(pd.unique(values.astype(object)))[:5000]
    if variable.labels:
        codes = {_code_text(code) for code in variable.labels} | {
            _code_text(code) for code in variable.missing_values
        }
        texts = {label_text(label) for label in variable.labels.values()} | {
            label_text(label) for label in variable.missing_labels.values()
        }
        odd = [
            value
            for value in distinct
            if _code_text(value) not in codes
            and not (isinstance(value, str) and label_text(value) in texts)
        ]
        if odd:
            return (
                f"{len(odd)} of its values are neither its codes nor its labels"
                if len(odd) > 1
                else "a value is neither one of its codes nor one of its labels"
            )
        return None
    if variable.scale in {"interval", "ratio"} and not pd.api.types.is_numeric_dtype(series):
        missing = {_code_text(code) for code in variable.missing_values}
        words = [
            value
            for value in distinct
            if isinstance(value, str)
            and not _NUMBER.match(value.strip())
            and _code_text(value) not in missing
            and not re.match(r"^\d{4}-\d{2}-\d{2}", value.strip())
        ]
        if words:
            return f"it holds text where the questionnaire has numbers ({variable.scale})"
    return None


def several_answers(text: str, variable: Variable) -> list[Any] | None:
    """The answers a cell of a several-answers column holds: its codes
    ``1;3`` (as Siamang writes them) or ``1,3`` (as Qualtrics does), or its
    value labels joined with ``;`` or ``,`` ("Acme,Initech"; a label holding a
    comma, "Yes, often", is matched whole). Codes come back as they are
    written, labels as their codes; none for a blank cell. None when the cell
    is neither."""

    if not text.strip():
        return []
    codes = {_code_text(code): code for code in variable.labels} | {
        _code_text(code): code for code in variable.missing_values
    }
    parts = [part.strip() for part in re.split(r"[;,]", text)]
    parts = [part for part in parts if part]
    if parts and all(part in codes for part in parts):
        return [codes[part] for part in parts]
    lookup = _label_lookup(variable)
    if not lookup:
        return None
    found: list[Any] = []
    for chunk in text.split(";"):
        tokens = chunk.split(",")
        start = 0
        while start < len(tokens):
            if not tokens[start].strip():
                start += 1
                continue
            for end in range(len(tokens), start, -1):
                key = label_text(",".join(tokens[start:end]))
                if key in lookup:
                    found.append(lookup[key])
                    start = end
                    break
                if _code_text(key) in codes and end == start + 1:
                    found.append(codes[_code_text(key)])
                    start = end
                    break
            else:
                return None
    return found or None


def _label_lookup(variable: Variable) -> dict[str, Any]:
    """Label text -> code, labels two codes share left out."""

    lookup: dict[str, Any] = {}
    ambiguous: set[str] = set()
    for code, label in list(variable.labels.items()) + list(variable.missing_labels.items()):
        key = label_text(label)
        if key in lookup and lookup[key] != code:
            ambiguous.add(key)
        lookup[key] = code
    for key in ambiguous:
        lookup.pop(key, None)
    return lookup


def lists_from_labels(
    frame: pd.DataFrame, variables: VariableMap, columns: Iterable[str]
) -> list[str]:
    """Turn several-answers columns written as their value labels
    ("Acme,Initech", a Qualtrics choice-text export) into lists of codes, in
    ``frame``, where every cell reads so. Returns the columns converted."""

    converted: list[str] = []
    for name in columns:
        if name not in frame.columns or name not in variables or not variables[name].labels:
            continue
        series = frame[name]
        values = series.dropna()
        if series.dtype != object or values.empty:
            continue
        if not all(isinstance(value, str) for value in values):
            continue
        codes = {_code_text(code) for code in variables[name].labels}
        if all(
            all(part.strip() in codes for part in re.split(r"[;,]", text) if part.strip())
            for text in pd.unique(values)
        ):
            continue  # codes already ("1,3"): list_frame splits them
        parsed: dict[str, list[Any] | None] = {}
        for text in pd.unique(values):
            answers = several_answers(text, variables[name])
            if answers is None:
                break
            parsed[text] = answers or None  # a blank cell: no answer
        else:
            frame[name] = series.map(
                lambda value, table=parsed: table.get(value, value)
                if isinstance(value, str)
                else value
            )
            converted.append(name)
    return converted


def comma_answers(series: pd.Series, variable: Variable) -> bool:
    """Whether a several-answers column writes its codes joined with commas
    (``1,3``) — every comma-joined cell made of the variable's codes."""

    codes = {_code_text(code) for code in variable.labels} | {
        _code_text(code) for code in variable.missing_values
    }
    joined = [value for value in series.dropna() if isinstance(value, str) and "," in value]
    return bool(joined) and all(
        all(part.strip() in codes for part in value.split(",") if part.strip()) for value in joined
    )


def label_text(value: Any) -> str:
    """A label or an answer as they are compared: HTML tags and entities gone,
    spaces collapsed, case folded."""

    text = html.unescape(_TAGS.sub(" ", str(value)))
    return " ".join(text.split()).casefold()


def codes_from_labels(
    frame: pd.DataFrame, variables: VariableMap, skip: Iterable[str] = ()
) -> tuple[list[str], dict[str, int]]:
    """Turn a choice-text export's answers into their codes, in ``frame``.

    A column of text whose every value is one of its variable's value labels
    (or already one of its codes) becomes the codes: "Moderately" becomes 3
    where the questionnaire labels 3 "Moderately". A column with answers that
    are not among the labels keeps its text. Returns the columns converted,
    and for each column left as text the number of its values that are not
    labels (only columns that held some labels)."""

    skip = set(skip)
    converted: list[str] = []
    kept: dict[str, int] = {}
    for name, variable in variables.items():
        if name not in frame.columns or name in skip or not variable.labels:
            continue
        series = frame[name]
        if series.dtype != object:
            continue
        lookup: dict[str, Any] = {}
        ambiguous: set[str] = set()
        for code, label in list(variable.labels.items()) + list(variable.missing_labels.items()):
            key = label_text(label)
            if key in lookup and lookup[key] != code:
                ambiguous.add(key)
            lookup[key] = code
        for key in ambiguous:
            lookup.pop(key, None)
        codes = {_code_text(code): code for code in variable.labels} | {
            _code_text(code): code for code in variable.missing_values
        }
        values = series.dropna()
        if values.empty or not values.map(lambda value: isinstance(value, str)).any():
            continue
        mapped: dict[Any, Any] = {}
        unknown = 0
        labelled = 0
        for value in pd.unique(values.astype(object)):
            if isinstance(value, str) and label_text(value) in lookup:
                mapped[value] = lookup[label_text(value)]
                labelled += 1
            elif _code_text(value) in codes:
                mapped[value] = codes[_code_text(value)]
            else:
                unknown += 1
        if not labelled:
            continue
        if unknown:
            kept[name] = unknown
            continue
        codes_of = series.map(lambda value, table=mapped: table.get(value, value))
        frame[name] = (
            pd.to_numeric(codes_of) if _all_numeric(mapped.values()) else codes_of
        ).where(series.notna(), np.nan)
        converted.append(name)
    return converted, kept


def _all_numeric(values: Iterable[Any]) -> bool:
    return all(
        isinstance(value, int | float | np.integer | np.floating) and not isinstance(value, bool)
        for value in values
    )


__all__ = [
    "EVERY_COLUMN",
    "METADATA_COLUMNS",
    "QuestionnaireMatch",
    "codes_from_labels",
    "column_type",
    "comma_answers",
    "is_metadata",
    "file_variables",
    "infer_scale",
    "label_text",
    "lists_from_labels",
    "missing_text",
    "normal_name",
    "parse_missing",
    "personal_data",
    "questionnaire_match",
    "several_answers",
    "suspected_missing",
    "with_missing",
]
