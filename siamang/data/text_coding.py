"""Applying a frozen codeframe to open answers — no model, no network.

A language model can read a thousand open answers and propose a coding scheme;
it cannot be part of an analysis that has to run the same way twice. So the two
jobs are split. Somewhere else — a platform's worker, a researcher's notebook —
a model builds a **codeframe**: the themes, and which answer belongs to which.
That file is then data like any other, and this module applies it: a lookup, a
column, a codebook entry.

The consequence is the point. An analysis that codes text through an API cannot
be re-run (the model moves), cannot be checked (the prompt is gone) and cannot
be attached to a paper. One that reads a codeframe file can be re-run by anyone
holding the file, gives the same numbers, and the scheme itself is there to
disagree with — which is what a coding scheme is for.

Answers are matched by a fingerprint of their normalized text rather than by
row position, so the same answer is coded the same way wherever it appears, and
a frame rebuilt in a different order still codes identically. An answer the
codeframe has never seen — collected after it was built, or simply new — stays
uncoded rather than being guessed at, and :func:`coverage` says how many those
are.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

__all__ = [
    "Codeframe",
    "CodeframeError",
    "Theme",
    "apply",
    "codes",
    "coverage",
    "fingerprint",
    "load",
    "normalise",
    "parse",
    "sentiment_scores",
]

#: The format this module reads. Bumped only for a change that an older reader
#: could not handle; new optional keys do not need it.
SCHEMA_VERSION = "1.0"

#: Sentiment, when a codeframe carries it: one column of -1 / 0 / 1 beside the
#: theme. Deliberately three values — a model's "0.62 positive" is a number
#: without a unit, and a report that quotes it is quoting nothing.
SENTIMENT_LABELS = {-1: "Negative", 0: "Neutral", 1: "Positive"}

_SPACE_RE = re.compile(r"\s+")
_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")
MAX_THEMES = 64


class CodeframeError(ValueError):
    """A codeframe file that cannot be applied."""


@dataclass(frozen=True, slots=True)
class Theme:
    """One theme: the code it writes, what it means, and answers that show it."""

    code: int
    label: str
    definition: str = ""
    examples: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Codeframe:
    """A coding scheme and its verdicts, as read from a file."""

    variable: str
    into: str
    themes: tuple[Theme, ...]
    #: fingerprint -> theme code. The verdicts, frozen.
    assignments: Mapping[str, int] = field(default_factory=dict)
    #: fingerprint -> -1 / 0 / 1, when the codeframe was built with sentiment.
    sentiment: Mapping[str, int] = field(default_factory=dict)
    model: str = ""
    built_at: str = ""
    #: How many answers the scheme was built from, for the methods section.
    source_rows: int = 0

    @property
    def labels(self) -> dict[int, str]:
        return {theme.code: theme.label for theme in self.themes}

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "variable": self.variable,
            "into": self.into,
            "themes": [
                {
                    "code": t.code,
                    "label": t.label,
                    **({"definition": t.definition} if t.definition else {}),
                    **({"examples": list(t.examples)} if t.examples else {}),
                }
                for t in self.themes
            ],
            "assignments": dict(self.assignments),
        }
        if self.sentiment:
            payload["sentiment"] = dict(self.sentiment)
        for key in ("model", "built_at"):
            if value := getattr(self, key):
                payload[key] = value
        if self.source_rows:
            payload["source_rows"] = self.source_rows
        return payload


def normalise(text: Any) -> str:
    """The text as it is matched: unicode-normalized, case-folded, despaced.

    Not stemmed and not stripped of punctuation: two answers that differ by a
    word are different answers, and deciding they are not is the coding scheme's
    job, not the lookup's.
    """

    if text is None or (isinstance(text, float) and pd.isna(text)):
        return ""
    return _SPACE_RE.sub(" ", unicodedata.normalize("NFKC", str(text)).strip()).casefold()


def fingerprint(text: Any) -> str:
    """A short stable key for an answer's normalized text.

    Sixteen hex characters of SHA-256: short enough that a codeframe stays
    readable, long enough that a collision inside one survey is not a thing that
    happens. It is a lookup key, never an identifier — the text it came from is
    an answer, and the file carries examples, not every answer.
    """

    return hashlib.sha256(normalise(text).encode("utf-8")).hexdigest()[:16]


def parse(payload: Mapping[str, Any]) -> Codeframe:
    """Read a codeframe from its JSON shape, refusing anything unusable."""

    if not isinstance(payload, Mapping):
        raise CodeframeError("a codeframe must be a JSON object")
    variable = str(payload.get("variable") or "").strip()
    if not _NAME_RE.match(variable):
        raise CodeframeError(f"codeframe: {variable!r} is not a variable name")
    into = str(payload.get("into") or f"{variable}_theme").strip()
    if not _NAME_RE.match(into):
        raise CodeframeError(f"codeframe: {into!r} is not a variable name")

    raw_themes = payload.get("themes")
    if not isinstance(raw_themes, Sequence) or not raw_themes:
        raise CodeframeError("codeframe: no themes")
    if len(raw_themes) > MAX_THEMES:
        raise CodeframeError(f"codeframe: more than {MAX_THEMES} themes")
    themes: list[Theme] = []
    seen: set[int] = set()
    for entry in raw_themes:
        if not isinstance(entry, Mapping):
            raise CodeframeError("codeframe: a theme must be an object")
        try:
            code = int(entry["code"])
        except (KeyError, TypeError, ValueError) as exc:
            raise CodeframeError("codeframe: a theme needs an integer code") from exc
        label = str(entry.get("label") or "").strip()
        if not label:
            raise CodeframeError(f"codeframe: theme {code} has no label")
        if code in seen:
            raise CodeframeError(f"codeframe: theme code {code} appears twice")
        seen.add(code)
        examples = entry.get("examples") or []
        themes.append(
            Theme(
                code=code,
                label=label,
                definition=str(entry.get("definition") or "").strip(),
                examples=tuple(str(x) for x in examples if str(x).strip())[:5],
            )
        )

    assignments: dict[str, int] = {}
    for key, value in (payload.get("assignments") or {}).items():
        try:
            code = int(value)
        except (TypeError, ValueError) as exc:
            raise CodeframeError(f"codeframe: assignment {key!r} is not a theme code") from exc
        if code not in seen:
            raise CodeframeError(f"codeframe: assignment {key!r} names unknown theme {code}")
        assignments[str(key)] = code

    sentiment: dict[str, int] = {}
    for key, value in (payload.get("sentiment") or {}).items():
        try:
            score = int(value)
        except (TypeError, ValueError) as exc:
            raise CodeframeError(f"codeframe: sentiment {key!r} is not -1, 0 or 1") from exc
        if score not in SENTIMENT_LABELS:
            raise CodeframeError(f"codeframe: sentiment {key!r} is not -1, 0 or 1")
        sentiment[str(key)] = score

    return Codeframe(
        variable=variable,
        into=into,
        themes=tuple(themes),
        assignments=assignments,
        sentiment=sentiment,
        model=str(payload.get("model") or ""),
        built_at=str(payload.get("built_at") or ""),
        source_rows=int(payload.get("source_rows") or 0),
    )


def load(path: str | Path) -> Codeframe:
    """Read and validate a codeframe file."""

    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CodeframeError(f"codeframe file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CodeframeError(f"codeframe {path}: {exc}") from exc
    return parse(payload)


def codes(series: pd.Series, codeframe: Codeframe) -> pd.Series:
    """The theme code for every answer, ``NA`` where the codeframe has none."""

    assignments = codeframe.assignments
    return pd.Series(
        [assignments.get(fingerprint(value), pd.NA) for value in series],
        index=series.index,
        dtype="Int64",
    )


def sentiment_scores(series: pd.Series, codeframe: Codeframe) -> pd.Series:
    """The sentiment for every answer, ``NA`` where the codeframe has none."""

    scores = codeframe.sentiment
    return pd.Series(
        [scores.get(fingerprint(value), pd.NA) for value in series],
        index=series.index,
        dtype="Int64",
    )


def apply(
    data: Any, codeframe: Codeframe, *, into: str | None = None, sentiment: bool = False
) -> Any:
    """Attach the coded theme (and optionally the sentiment) to ``data``.

    Both arrive as proper variables — with the codeframe's own labels — so the
    theme is in the codebook, in a crosstab and in the SPSS export the moment it
    exists, rather than being a bare column an analysis has to explain. Uncoded
    answers are missing values, which is what they are.
    """

    if codeframe.variable not in data.frame.columns:
        raise CodeframeError(
            f"codeframe codes {codeframe.variable!r}, which this data does not have"
        )
    name = (into or codeframe.into).strip()
    if not _NAME_RE.match(name):
        raise CodeframeError(f"codeframe: {name!r} is not a variable name")
    series = data.frame[codeframe.variable]
    out = data.with_derived(
        name,
        codes(series, codeframe),
        label=f"Theme: {codeframe.variable}",
        scale="nominal",
        labels=codeframe.labels,
    )
    if sentiment and codeframe.sentiment:
        out = out.with_derived(
            f"{name}_sentiment",
            sentiment_scores(series, codeframe),
            label=f"Sentiment: {codeframe.variable}",
            scale="ordinal",
            labels=dict(SENTIMENT_LABELS),
        )
    return out


def coverage(frame: pd.DataFrame, codeframe: Codeframe) -> dict[str, int]:
    """How much of the column the codeframe actually covers.

    ``answered`` is how many respondents wrote something, ``coded`` how many of
    those the codeframe has a theme for, and ``uncoded`` the difference — the
    answers collected since it was built, or simply never seen. A report quoting
    theme shares should quote this next to them.
    """

    if codeframe.variable not in frame.columns:
        return {"answered": 0, "coded": 0, "uncoded": 0}
    series = frame[codeframe.variable]
    answered = series.map(lambda v: normalise(v) != "")
    coded = codes(series, codeframe).notna() & answered
    return {
        "answered": int(answered.sum()),
        "coded": int(coded.sum()),
        "uncoded": int(answered.sum() - coded.sum()),
    }
