"""Applying a codeframe to open answers — no model, no network.

A coding scheme has to run the same way twice. So it lives in a file — a
**codeframe** — that is data like any other, and this module applies it: a
lookup, a column, a codebook entry. An analysis that reads a codeframe file can
be re-run by anyone holding the file, gives the same numbers, and the scheme
itself is there to disagree with — which is what a coding scheme is for.

Answers are matched by a fingerprint of their normalized text rather than by
row position, so the same answer is coded the same way wherever it appears, and
a frame rebuilt in a different order still codes identically. The file keeps
fingerprints, never the answers' texts.

**Version 1** (``schema_version`` ``"1.0"``) is a list of themes and a verdict
per fingerprint, one theme each. An answer the codeframe has never seen —
collected after it was built, or simply new — stays uncoded rather than being
guessed at, and :func:`coverage` says how many those are.

**Version 2** (``"2.0"``) adds what a researcher coding by hand needs to keep
up with answers that keep arriving:

* **several themes an answer** (``multiple``; the theme variable is then a
  multiple-choice variable, lists of codes) with an optional cap
  (``max_codes``);
* **rules** per theme — ``include``, ``require`` and ``exclude`` terms, read
  within a clause or over the whole answer (``scope``) — which code the answers
  nobody decided, at every run, including the ones collected after the rules
  were written (:mod:`siamang.data.text_rules` says what a term may say);
* **nets** (a theme's ``group``: a row counting each respondent once),
  **exclusive** themes (*Nothing / Don't know*: kept only when nothing else
  matches) and a **priority** that decides which theme a single-theme answer
  keeps and where ``max_codes`` cuts;
* **replacements** (``replace``: synonyms, typos) made before the rules read;
* a coder's decision may be several themes, or none (``[]``: read, and
  belongs to no theme).

Each answer is coded by the first of: a coder's decision for its fingerprint,
the rules, nothing. :func:`validate`, :func:`preview`, :func:`explain` and
:func:`suggest` are what an editor of the codeframe calls: pure functions of
the codeframe and the answers it is shown.

A version 1 file is read and applied exactly as before.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from itertools import repeat
from pathlib import Path
from typing import Any, cast

import pandas as pd

from siamang.data import text_rules

__all__ = [
    "Codeframe",
    "CodeframeError",
    "CodeframeIssue",
    "Coding",
    "Rules",
    "Theme",
    "Validation",
    "apply",
    "codes",
    "coding",
    "coverage",
    "explain",
    "fingerprint",
    "load",
    "normalise",
    "parse",
    "preview",
    "sentiment_scores",
    "sources",
    "suggest",
    "tally",
    "uncoded_answers",
    "validate",
]

#: The format this module reads. Bumped only for a change that an older reader
#: could not handle; new optional keys do not need it.
SCHEMA_VERSION = "1.0"
#: The version with rules, several themes an answer, nets and exclusive themes.
SCHEMA_VERSION_2 = "2.0"

#: Sentiment, when a codeframe carries it: one column of -1 / 0 / 1 beside the
#: theme. Deliberately three values — a model's "0.62 positive" is a number
#: without a unit, and a report that quotes it is quoting nothing.
SENTIMENT_LABELS = {-1: "Negative", 0: "Neutral", 1: "Positive"}

_SPACE_RE = re.compile(r"\s+")
_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")
_FINGERPRINT_RE = re.compile(r"^[0-9a-f]{16}$")
MAX_THEMES = 64
#: Version 2's limits: themes, terms in one list, replacements.
MAX_THEMES_V2 = 200
MAX_TERMS = 500
MAX_REPLACEMENTS = 2000
SOURCES = ("hand", "rule", "uncoded")


class CodeframeError(ValueError):
    """A codeframe file that cannot be applied."""


@dataclass(frozen=True, slots=True)
class Rules:
    """A theme's rules (version 2): it matches in a scope — a clause, or the
    whole answer — where one ``include`` term matches, each ``require`` group
    has a term that matches and no ``exclude`` term matches. ``scope`` empty
    takes the codeframe's."""

    include: tuple[str, ...] = ()
    require: tuple[tuple[str, ...], ...] = ()
    exclude: tuple[str, ...] = ()
    scope: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"include": list(self.include)}
        if len(self.require) == 1:
            payload["require"] = list(self.require[0])
        elif self.require:
            payload["require"] = [list(group) for group in self.require]
        if self.exclude:
            payload["exclude"] = list(self.exclude)
        if self.scope:
            payload["scope"] = self.scope
        return payload


@dataclass(frozen=True, slots=True)
class Theme:
    """One theme: the code it writes, what it means, and — in version 2 — the
    net it belongs to, whether it stands alone, its priority and its rules."""

    code: int
    label: str
    definition: str = ""
    examples: tuple[str, ...] = ()
    group: str = ""
    exclusive: bool = False
    priority: float = 0
    rules: Rules | None = None


@dataclass(frozen=True, slots=True)
class Codeframe:
    """A coding scheme and its verdicts, as read from a file."""

    variable: str
    into: str
    themes: tuple[Theme, ...]
    #: fingerprint -> theme code (version 1), or -> the codes, maybe none
    #: (version 2). The verdicts, frozen.
    assignments: Mapping[str, Any] = field(default_factory=dict)
    #: fingerprint -> -1 / 0 / 1, when the codeframe was built with sentiment.
    sentiment: Mapping[str, int] = field(default_factory=dict)
    model: str = ""
    built_at: str = ""
    #: How many answers the scheme was built from, for the methods section.
    source_rows: int = 0
    version: int = 1
    language: str = "en"
    #: Several themes an answer (a multiple-choice theme variable), or one.
    multiple: bool = False
    #: The most themes the rules give an answer; 0 for no cap.
    max_codes: int = 0
    #: Where a theme's rules are read unless it says otherwise.
    scope: str = text_rules.CLAUSE
    #: (from, to): words or phrases replaced before the rules read an answer.
    replace: tuple[tuple[str, str], ...] = ()
    _compiled: Any = field(default=None, init=False, repr=False, compare=False)

    @property
    def labels(self) -> dict[int, str]:
        return {theme.code: theme.label for theme in self.themes}

    @property
    def nets(self) -> dict[str, tuple[int, ...]]:
        """The nets: each group of two or more themes, with their codes, in the
        order the groups first appear."""
        groups: dict[str, list[int]] = {}
        for theme in self.themes:
            if theme.group:
                groups.setdefault(theme.group, []).append(theme.code)
        return {name: tuple(codes) for name, codes in groups.items() if len(codes) >= 2}

    @property
    def rule_set(self) -> text_rules.RuleSet:
        """The rules, compiled once for this codeframe."""
        if self._compiled is None:
            themes = [
                text_rules.RuleTheme(
                    code=theme.code,
                    label=theme.label,
                    order=order,
                    exclusive=theme.exclusive,
                    priority=float(theme.priority),
                    scope=(theme.rules.scope if theme.rules else "") or self.scope,
                    include=theme.rules.include if theme.rules else (),
                    require=theme.rules.require if theme.rules else (),
                    exclude=theme.rules.exclude if theme.rules else (),
                )
                for order, theme in enumerate(self.themes)
            ]
            object.__setattr__(self, "_compiled", text_rules.RuleSet(themes, self.replace))
        return cast(text_rules.RuleSet, self._compiled)

    def to_dict(self) -> dict[str, Any]:
        if self.version >= 2:
            return self._to_dict_v2()
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

    def _to_dict_v2(self) -> dict[str, Any]:
        themes = []
        for t in self.themes:
            entry: dict[str, Any] = {"code": t.code, "label": t.label}
            if t.definition:
                entry["definition"] = t.definition
            if t.group:
                entry["group"] = t.group
            if t.exclusive:
                entry["exclusive"] = True
            if t.priority:
                entry["priority"] = t.priority
            if t.rules is not None:
                entry["rules"] = t.rules.to_dict()
            themes.append(entry)
        payload: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION_2,
            "variable": self.variable,
            "into": self.into,
            "language": self.language,
            "multiple": self.multiple,
            "max_codes": self.max_codes,
            "scope": self.scope,
            "replace": [{"from": a, "to": b} for a, b in self.replace],
            "themes": themes,
            "assignments": {
                key: (codes[0] if len(codes) == 1 else list(codes))
                for key, codes in self.assignments.items()
            },
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
    an answer, and the file carries fingerprints, not answers.
    """

    return _fingerprint_of(normalise(text))


def _fingerprint_of(normalised: str) -> str:
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()[:16]


def parse(payload: Mapping[str, Any]) -> Codeframe:
    """Read a codeframe from its JSON shape, refusing anything unusable."""

    if not isinstance(payload, Mapping):
        raise CodeframeError("a codeframe must be a JSON object")
    version = _version(payload)
    if version == 2:
        codeframe, issues = _read_v2(payload)
        errors = [issue for issue in issues if issue.level == "error"]
        if errors or codeframe is None:
            raise CodeframeError(f"codeframe: {errors[0].message}")
        return codeframe
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


# ─── Version 2: reading and validating ────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class CodeframeIssue:
    """One problem of a codeframe: ``error`` (it cannot be applied) or
    ``warning`` (it can, but part of it does nothing), the reason, and where —
    a path of keys into the JSON (``("themes", 2, "rules", "include", 0)``)."""

    level: str
    message: str
    path: tuple[str | int, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {"level": self.level, "message": self.message, "path": list(self.path)}


@dataclass(frozen=True, slots=True)
class Validation:
    """What :func:`validate` found."""

    errors: tuple[CodeframeIssue, ...] = ()
    warnings: tuple[CodeframeIssue, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "errors": [issue.to_dict() for issue in self.errors],
            "warnings": [issue.to_dict() for issue in self.warnings],
        }


def validate(codeframe: Mapping[str, Any] | Codeframe) -> Validation:
    """Every problem of a codeframe, errors and warnings, each with its place.

    A version 1 file is checked as :func:`parse` checks it (the first problem);
    a version 2 file is checked in full: unknown codes and fingerprints,
    duplicate codes and replacements, empty or unreadable terms, terms that
    can never match an answer once it is normalised, keys that mean nothing.
    """

    payload = codeframe.to_dict() if isinstance(codeframe, Codeframe) else codeframe
    if not isinstance(payload, Mapping):
        return Validation(errors=(CodeframeIssue("error", "a codeframe must be a JSON object"),))
    try:
        version = _version(payload)
    except CodeframeError as exc:
        return Validation(errors=(CodeframeIssue("error", str(exc), ("schema_version",)),))
    if version == 1:
        try:
            parse(payload)
        except CodeframeError as exc:
            return Validation(errors=(CodeframeIssue("error", str(exc)),))
        return Validation(warnings=tuple(_version_2_fields(payload)))
    _, issues = _read_v2(payload)
    return Validation(
        errors=tuple(i for i in issues if i.level == "error"),
        warnings=tuple(i for i in issues if i.level == "warning"),
    )


def _version_2_fields(payload: Mapping[str, Any]) -> list[CodeframeIssue]:
    """Fields of version 2 in a version 1 file, which reads them as nothing."""
    found = [
        CodeframeIssue(
            "warning",
            f"'{key}' is a field of version 2, and this codeframe is version 1: it is "
            "ignored unless schema_version is 2.0",
            (key,),
        )
        for key in ("multiple", "max_codes", "scope", "replace", "language")
        if key in payload
    ]
    for index, theme in enumerate(payload.get("themes") or []):
        for key in ("group", "exclusive", "priority", "rules"):
            if isinstance(theme, Mapping) and key in theme:
                found.append(
                    CodeframeIssue(
                        "warning",
                        f"theme {theme.get('code')}: '{key}' is a field of version 2, and this "
                        "codeframe is version 1: it is ignored unless schema_version is 2.0",
                        ("themes", index, key),
                    )
                )
    return found


def _version(payload: Mapping[str, Any]) -> int:
    raw = payload.get("schema_version")
    if raw is None or isinstance(raw, bool):
        return 1
    major = str(raw).strip().split(".", 1)[0]
    if major == "2":
        return 2
    if major.isdigit() and int(major) > 2:
        raise CodeframeError(
            f"codeframe: schema_version {raw!r} is newer than this siamang reads (1.0 or 2.0)"
        )
    return 1  # 1.0, or what a version 1 reader took for it


_TOP_KEYS = frozenset(
    {
        "schema_version",
        "variable",
        "into",
        "language",
        "multiple",
        "max_codes",
        "scope",
        "replace",
        "themes",
        "assignments",
        "sentiment",
        "model",
        "built_at",
        "source_rows",
    }
)
_THEME_KEYS = frozenset({"code", "label", "definition", "group", "exclusive", "priority", "rules"})
_RULE_KEYS = frozenset({"include", "require", "exclude", "scope"})


def _as_code(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and re.fullmatch(r"-?\d{1,9}", value.strip()):
        return int(value)
    return None


def _read_v2(payload: Mapping[str, Any]) -> tuple[Codeframe | None, list[CodeframeIssue]]:
    """Read a version 2 codeframe and every problem it has, in one pass, so
    :func:`parse` and :func:`validate` never disagree."""

    issues: list[CodeframeIssue] = []

    def error(message: str, *path: str | int) -> None:
        issues.append(CodeframeIssue("error", message, path))

    def warn(message: str, *path: str | int) -> None:
        issues.append(CodeframeIssue("warning", message, path))

    for key in payload:
        if key not in _TOP_KEYS:
            warn(f"'{key}' is not a codeframe field and is ignored", str(key))

    variable = str(payload.get("variable") or "").strip()
    if not _NAME_RE.match(variable):
        error(f"{variable!r} is not a variable name", "variable")
    into = str(payload.get("into") or f"{variable}_theme").strip()
    if not _NAME_RE.match(into):
        error(f"{into!r} is not a variable name", "into")

    def given(key: str, default: Any) -> Any:
        value = payload.get(key)
        return default if value is None else value

    language = given("language", "en")
    if language != "en":
        error(
            f"language {language!r} is not supported: the words the rules know — negations, "
            "clause breaks, stop words — are English ('en')",
            "language",
        )
    multiple = given("multiple", False)
    if not isinstance(multiple, bool):
        error("multiple is true or false", "multiple")
        multiple = False
    max_codes = given("max_codes", 0)
    if isinstance(max_codes, bool) or not isinstance(max_codes, int) or max_codes < 0:
        error("max_codes is a whole number, 0 for no cap", "max_codes")
        max_codes = 0
    elif max_codes and not multiple:
        warn(
            "max_codes does nothing in a codeframe that gives one theme an answer "
            "(multiple is false)",
            "max_codes",
        )
    scope = given("scope", text_rules.CLAUSE)
    if scope not in text_rules.SCOPES:
        error(f"scope is 'clause' or 'answer', not {scope!r}", "scope")
        scope = text_rules.CLAUSE

    replace = _read_replacements(payload.get("replace"), error, warn)
    replaced_words = {
        text_rules.normalise_replacement(a): text_rules.normalise_replacement(b) for a, b in replace
    }

    raw_themes = payload.get("themes")
    themes: list[Theme] = []
    if not isinstance(raw_themes, Sequence) or isinstance(raw_themes, str) or not raw_themes:
        error("the codeframe has no themes", "themes")
        raw_themes = []
    elif len(raw_themes) > MAX_THEMES_V2:
        error(f"more than {MAX_THEMES_V2} themes", "themes")
        raw_themes = []
    codes: dict[int, Theme] = {}
    labels: dict[str, int] = {}
    for index, entry in enumerate(raw_themes):
        theme = _read_theme(entry, index, scope, replaced_words, error, warn)
        if theme is None:
            continue
        if theme.code in codes:
            error(f"theme code {theme.code} appears twice", "themes", index, "code")
            continue
        folded = theme.label.casefold()
        if folded in labels:
            warn(
                f"themes {labels[folded]} and {theme.code} are both labelled {theme.label!r}",
                "themes",
                index,
                "label",
            )
        labels.setdefault(folded, theme.code)
        codes[theme.code] = theme
        themes.append(theme)
    groups: dict[str, list[int]] = {}
    for theme in themes:
        if theme.group:
            groups.setdefault(theme.group, []).append(theme.code)
    for name, members in groups.items():
        if len(members) == 1:
            index = next(i for i, t in enumerate(themes) if t.code == members[0])
            warn(
                f"the net {name!r} has one theme ({members[0]}), so no net row is shown for it",
                "themes",
                index,
                "group",
            )

    assignments = _read_assignments(payload.get("assignments"), codes, multiple, error, warn)
    sentiment: dict[str, int] = {}
    raw_sentiment = payload.get("sentiment") or {}
    if not isinstance(raw_sentiment, Mapping):
        error("sentiment maps fingerprints to -1, 0 or 1", "sentiment")
        raw_sentiment = {}
    for key, value in raw_sentiment.items():
        if not _FINGERPRINT_RE.match(str(key)):
            error(f"sentiment {key!r} is not an answer's fingerprint", "sentiment", str(key))
            continue
        score = _as_code(value)
        if score not in SENTIMENT_LABELS:
            error(f"sentiment {key!r} is not -1, 0 or 1", "sentiment", str(key))
            continue
        sentiment[str(key)] = score
    source_rows = payload.get("source_rows") or 0
    if isinstance(source_rows, bool) or not isinstance(source_rows, int) or source_rows < 0:
        error("source_rows is a whole number", "source_rows")
        source_rows = 0

    if any(issue.level == "error" for issue in issues):
        return None, issues
    return (
        Codeframe(
            variable=variable,
            into=into,
            themes=tuple(themes),
            assignments=assignments,
            sentiment=sentiment,
            model=str(payload.get("model") or ""),
            built_at=str(payload.get("built_at") or ""),
            source_rows=source_rows,
            version=2,
            language="en",
            multiple=multiple,
            max_codes=max_codes,
            scope=scope,
            replace=replace,
        ),
        issues,
    )


def _read_replacements(raw: Any, error: Any, warn: Any) -> tuple[tuple[str, str], ...]:
    if raw is None:
        return ()
    if not isinstance(raw, Sequence) or isinstance(raw, str):
        error("replace is a list of {from, to}", "replace")
        return ()
    if len(raw) > MAX_REPLACEMENTS:
        error(f"more than {MAX_REPLACEMENTS} replacements", "replace")
        return ()
    pairs: list[tuple[str, str]] = []
    seen: dict[str, int] = {}
    for index, entry in enumerate(raw):
        if not isinstance(entry, Mapping):
            error("a replacement is an object with from and to", "replace", index)
            continue
        before, after = entry.get("from"), entry.get("to", "")
        if not isinstance(before, str) or not text_rules.normalise_replacement(before):
            error("a replacement needs the words it replaces (from)", "replace", index, "from")
            continue
        if not isinstance(after, str):
            error("a replacement's to is text (empty to drop the words)", "replace", index, "to")
            continue
        key = text_rules.normalise_replacement(before)
        if len(key) > text_rules.MAX_TERM_LENGTH or len(after) > text_rules.MAX_TERM_LENGTH:
            error(
                f"a replacement is longer than {text_rules.MAX_TERM_LENGTH} characters",
                "replace",
                index,
            )
            continue
        if key in seen:
            error(f"{before.strip()!r} is replaced twice", "replace", index, "from")
            continue
        seen[key] = index
        if key == text_rules.normalise_replacement(after):
            warn(f"{before.strip()!r} is replaced by itself", "replace", index)
        pairs.append((before.strip(), after.strip()))
    return tuple(pairs)


def _read_theme(
    entry: Any,
    index: int,
    scope: str,
    replaced: dict[str, str],
    error: Any,
    warn: Any,
) -> Theme | None:
    where = ("themes", index)
    if not isinstance(entry, Mapping):
        error("a theme is an object", *where)
        return None
    code = _as_code(entry.get("code"))
    if code is None:
        error("a theme needs a whole-number code", *where, "code")
        return None
    label = entry.get("label")
    label = label.strip() if isinstance(label, str) else ""
    if not label:
        error(f"theme {code} has no label", *where, "label")
        return None
    name = f"theme {code} ({label})"
    for key in entry:
        if key == "examples":
            error(
                f"{name}: a version 2 codeframe keeps no answers' texts, only their "
                "fingerprints — remove its examples",
                *where,
                "examples",
            )
        elif key not in _THEME_KEYS:
            warn(f"{name}: '{key}' is not a theme field and is ignored", *where, str(key))
    definition = entry.get("definition") or ""
    group = entry.get("group") or ""
    if not isinstance(definition, str):
        error(f"{name}: the definition is text", *where, "definition")
        definition = ""
    if not isinstance(group, str):
        error(f"{name}: the group (net) is text", *where, "group")
        group = ""
    exclusive = entry.get("exclusive", False)
    if not isinstance(exclusive, bool):
        error(f"{name}: exclusive is true or false", *where, "exclusive")
        exclusive = False
    priority = entry.get("priority", 0)
    if (
        isinstance(priority, bool)
        or not isinstance(priority, int | float)
        or not math.isfinite(priority)
    ):
        error(f"{name}: priority is a number", *where, "priority")
        priority = 0
    rules = _read_rules(entry.get("rules"), name, where, scope, replaced, error, warn)
    return Theme(
        code=code,
        label=label,
        definition=definition.strip(),
        group=group.strip(),
        exclusive=exclusive,
        priority=priority,
        rules=rules,
    )


def _read_rules(
    raw: Any,
    name: str,
    where: tuple[str | int, ...],
    scope: str,
    replaced: dict[str, str],
    error: Any,
    warn: Any,
) -> Rules | None:
    if raw is None:
        return None
    where = (*where, "rules")
    if not isinstance(raw, Mapping):
        error(f"{name}: rules is an object of include, require and exclude", *where)
        return None
    for key in raw:
        if key not in _RULE_KEYS:
            warn(f"{name}: '{key}' is not a rule field and is ignored", *where, str(key))
    own_scope = raw.get("scope") or ""
    if own_scope and own_scope not in text_rules.SCOPES:
        error(f"{name}: scope is 'clause' or 'answer', not {own_scope!r}", *where, "scope")
        own_scope = ""
    reads = own_scope or scope

    def terms(key: str, value: Any, path: tuple[str | int, ...]) -> tuple[str, ...]:
        if value is None:
            return ()
        if not isinstance(value, Sequence) or isinstance(value, str):
            error(f"{name}: {key} is a list of terms", *path)
            return ()
        if len(value) > MAX_TERMS:
            error(f"{name}: more than {MAX_TERMS} {key} terms", *path)
            return ()
        kept: list[str] = []
        seen: set[str] = set()
        for position, term in enumerate(value):
            spot = (*path, position)
            if not isinstance(term, str):
                error(f"{name}: {key} term {position + 1} is not text", *spot)
                continue
            try:
                parsed, notes = text_rules.parse_term(term)
            except text_rules.TermError as exc:
                error(f"{name}: {key} term {term.strip()!r}: {exc}", *spot)
                continue
            for note in notes:
                warn(f"{name}: {key} term {term.strip()!r} {note}", *spot)
            for note in _term_notes(parsed, reads, replaced):
                warn(f"{name}: {key} term {term.strip()!r} {note}", *spot)
            normal = text_rules.normalise_term(term)
            if normal in seen:
                warn(f"{name}: {key} term {term.strip()!r} is given twice", *spot)
                continue
            seen.add(normal)
            kept.append(term.strip())
        return tuple(kept)

    include = terms("include", raw.get("include"), (*where, "include"))
    exclude = terms("exclude", raw.get("exclude"), (*where, "exclude"))
    raw_require = raw.get("require")
    require: list[tuple[str, ...]] = []
    if raw_require is not None:
        if not isinstance(raw_require, Sequence) or isinstance(raw_require, str):
            error(f"{name}: require is a list of terms, or a list of lists", *where, "require")
        elif raw_require and all(
            isinstance(g, Sequence) and not isinstance(g, str) for g in raw_require
        ):
            for position, group in enumerate(raw_require):
                found = terms("require", group, (*where, "require", position))
                if found:
                    require.append(found)
                elif not group:
                    warn(f"{name}: require group {position + 1} is empty", *where, "require")
        elif any(isinstance(g, Sequence) and not isinstance(g, str) for g in raw_require):
            error(
                f"{name}: require is either a list of terms (one of them) or a list of "
                "lists (one of each), not both",
                *where,
                "require",
            )
        else:
            found = terms("require", raw_require, (*where, "require"))
            if found:
                require.append(found)
    if (require or exclude) and not include:
        warn(
            f"{name}: its rules have no include term, so its require and exclude terms do nothing",
            *where,
        )
    both = {text_rules.normalise_term(t) for t in include} & {
        text_rules.normalise_term(t) for t in exclude
    }
    for term in sorted(both):
        warn(
            f"{name}: {term!r} is both included and excluded, so it never codes the theme",
            *where,
        )
    return Rules(include=include, require=tuple(require), exclude=exclude, scope=own_scope)


def _term_notes(term: text_rules.Term, scope: str, replaced: dict[str, str]) -> list[str]:
    """Why a readable term still can never match: a word the answers never
    hold as the term asks — one that splits clauses (in a clause), one the
    replacements take away, or a negation asked to be negated."""

    notes: list[str] = []
    for atoms in term.words:
        cores = [atom for atom in atoms if "*" not in atom.core]
        if not cores or len(cores) < len(atoms):
            continue
        if scope == text_rules.CLAUSE and all(
            atom.core in text_rules.CLAUSE_WORDS for atom in atoms
        ):
            notes.append(
                f"can never match within a clause: '{atoms[0].core}' ends a clause "
                "(give the theme the scope 'answer')"
            )
        gone = [a.core for a in atoms if a.core in replaced and replaced[a.core] != a.core]
        if len(gone) == len(atoms):
            notes.append(
                f"can never match: '{gone[0]}' is replaced by '{replaced[gone[0]]}' "
                "before the rules read an answer"
            )
        never = [
            a.core
            for a in atoms
            if a.negated and (text_rules.is_negator(a.core) or a.core in text_rules.NEGATION_STOPS)
        ]
        if len(never) == len(atoms):
            notes.append(f"can never match: '{never[0]}' is never negated itself")
    whole = text_rules.normalise_term(term.text)
    if whole in replaced and " " in whole and replaced[whole] != whole:
        notes.append(
            f"can never match: '{whole}' is replaced by '{replaced[whole]}' "
            "before the rules read an answer"
        )
    return notes


def _read_assignments(
    raw: Any, codes: dict[int, Theme], multiple: bool, error: Any, warn: Any
) -> dict[str, tuple[int, ...]]:
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        error("assignments maps answers' fingerprints to theme codes", "assignments")
        return {}
    assignments: dict[str, tuple[int, ...]] = {}
    for key, value in raw.items():
        spot = ("assignments", str(key))
        if not _FINGERPRINT_RE.match(str(key)):
            error(
                f"assignment {str(key)[:40]!r} is not an answer's fingerprint (16 hexadecimal "
                "characters): a codeframe keeps fingerprints, never the answers' texts",
                *spot,
            )
            continue
        values = value if isinstance(value, list) else [value]
        found: list[int] = []
        for item in values:
            code = _as_code(item)
            if code is None:
                error(f"assignment {key!r}: {item!r} is not a theme code", *spot)
            elif codes and code not in codes:
                error(f"assignment {key!r} names unknown theme {code}", *spot)
            elif code in found:
                warn(f"assignment {key!r} names theme {code} twice", *spot)
            else:
                found.append(code)
        if len(found) > 1 and not multiple:
            warn(
                f"assignment {key!r} names {len(found)} themes, and the codeframe gives one "
                "an answer (multiple is false): the one ranked highest is kept",
                *spot,
            )
        assignments[str(key)] = tuple(found)
    return assignments


# ─── Coding ───────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Coding:
    """How one answer was coded: its codes (``None`` when it has none because
    nobody decided and no rule matched, or it is blank), where they came from —
    ``hand`` (a coder's decision, maybe ``()``: no theme), ``rule``, ``uncoded``
    or ``blank`` — and, for ``rule``, the rules that gave them."""

    codes: tuple[int, ...] | None
    source: str
    fired: tuple[text_rules.Fired, ...] = ()


_BLANK = Coding(None, "blank")
_UNCODED = Coding(None, "uncoded")


def _code_text(codeframe: Codeframe, normalised: str) -> Coding:
    if not normalised:
        return _BLANK
    manual = codeframe.assignments.get(_fingerprint_of(normalised))
    if codeframe.version < 2:
        return _UNCODED if manual is None else Coding((int(manual),), "hand")
    if manual is not None:
        if not codeframe.multiple and len(manual) > 1:
            order = {t.code: (-float(t.priority), i) for i, t in enumerate(codeframe.themes)}
            manual = (min(manual, key=order.__getitem__),)
        return Coding(tuple(manual), "hand")
    rules = codeframe.rule_set
    if not rules.rules:
        return _UNCODED
    fired = rules.fire(rules.prepare(normalised))
    kept, _ = text_rules.resolve(fired, multiple=codeframe.multiple, max_codes=codeframe.max_codes)
    if not kept:
        return _UNCODED
    return Coding(tuple(f.theme.code for f in kept), "rule", tuple(kept))


def coding(series: Iterable[Any], codeframe: Codeframe) -> list[Coding]:
    """How each answer of ``series`` is coded, in order — each distinct answer
    coded once."""

    by_value: dict[str, Coding] = {}
    by_text: dict[str, Coding] = {}
    out: list[Coding] = []
    for value in series:
        known = by_value.get(value) if isinstance(value, str) else None
        if known is None:
            text = normalise(value)
            known = by_text.get(text)
            if known is None:
                known = by_text[text] = _code_text(codeframe, text)
            if isinstance(value, str):
                by_value[value] = known
        out.append(known)
    return out


def codes(series: pd.Series, codeframe: Codeframe) -> pd.Series:
    """The theme code for every answer, ``NA`` where the codeframe has none.

    A version 2 codeframe with ``multiple`` gives each answer its list of
    codes (``[]`` where a coder decided it has no theme), a multiple-choice
    column; ``None`` where it is uncoded or blank."""

    if codeframe.version < 2:
        assignments = codeframe.assignments
        return pd.Series(
            [assignments.get(fingerprint(value), pd.NA) for value in series],
            index=series.index,
            dtype="Int64",
        )
    coded = coding(series, codeframe)
    if codeframe.multiple:
        return pd.Series(
            [None if c.codes is None else list(c.codes) for c in coded],
            index=series.index,
            dtype="object",
        )
    return pd.Series(
        [c.codes[0] if c.codes else pd.NA for c in coded], index=series.index, dtype="Int64"
    )


def sources(series: pd.Series, codeframe: Codeframe) -> pd.Series:
    """Where each answer's codes came from: ``hand``, ``rule`` or ``uncoded``;
    ``NA`` for a blank answer."""

    return pd.Series(
        [pd.NA if c.source == "blank" else c.source for c in coding(series, codeframe)],
        index=series.index,
        dtype="object",
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
    answers are missing values, which is what they are. A codeframe with
    ``multiple`` makes a multiple-choice variable: each answer's list of codes.
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

    For a version 2 codeframe ``coded`` counts every answer decided — by a
    coder (``by_hand``, ``no_theme`` of them decided to have none) or by the
    rules (``by_rules``) — and ``uncoded`` the answers neither reached.
    """

    if codeframe.version >= 2:
        empty = {"answered": 0, "coded": 0, "uncoded": 0}
        if codeframe.variable not in frame.columns:
            return {**empty, "by_hand": 0, "by_rules": 0, "no_theme": 0}
        return tally(coding(frame[codeframe.variable], codeframe))
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


def tally(coded: Iterable[Coding], weights: Iterable[int] | None = None) -> dict[str, int]:
    """:func:`coverage`'s counts of a list of :class:`Coding` — each counted
    ``weights`` times (one by default): how many answered, were coded (by hand,
    by the rules, as no theme) and were not."""
    by_source = {"hand": 0, "rule": 0, "uncoded": 0, "blank": 0, "none": 0}
    for item, weight in zip(coded, repeat(1) if weights is None else weights, strict=False):
        by_source[item.source] += weight
        if item.source == "hand" and not item.codes:
            by_source["none"] += weight
    return {
        "answered": by_source["hand"] + by_source["rule"] + by_source["uncoded"],
        "coded": by_source["hand"] + by_source["rule"],
        "uncoded": by_source["uncoded"],
        "by_hand": by_source["hand"],
        "by_rules": by_source["rule"],
        "no_theme": by_source["none"],
    }


def uncoded_answers(frame: pd.DataFrame, codeframe: Codeframe) -> pd.Series:
    """The answers the codeframe has no theme for, as written, in frame order.

    The ``uncoded`` of :func:`coverage` as the texts themselves: what a
    researcher reads to decide whether the scheme needs a new theme or only a
    rebuild, and — counted by :func:`fingerprint` — how many *different*
    answers a re-coding would have to look at. For a version 2 codeframe,
    the answers no coder decided and no rule matched.
    """

    if codeframe.variable not in frame.columns:
        return pd.Series(dtype="object")
    series = frame[codeframe.variable]
    if codeframe.version >= 2:
        mask = [c.source == "uncoded" for c in coding(series, codeframe)]
        return series[pd.Series(mask, index=series.index, dtype=bool)]
    answered = series.map(lambda v: normalise(v) != "").astype(bool)
    return series[answered & codes(series, codeframe).isna()]


# ─── What an editor of the codeframe calls ────────────────────────────────────


def _as_codeframe(codeframe: Mapping[str, Any] | Codeframe) -> Codeframe:
    return codeframe if isinstance(codeframe, Codeframe) else parse(codeframe)


def _distinct(answers: Any) -> list[tuple[str, str, int]]:
    """``answers`` — a mapping of answer to count, pairs of the two, answers
    alone, or a Series of them — as (text, normalised text, count), one per
    fingerprint (the first text seen, the counts summed), blanks left out."""

    if isinstance(answers, pd.Series):
        items: Iterable[Any] = ((value, 1) for value in answers)
    elif isinstance(answers, Mapping):
        items = answers.items()
    else:
        items = answers
    merged: dict[str, list[Any]] = {}
    for item in items:
        if isinstance(item, tuple | list) and len(item) == 2:
            text, count = item
        else:
            text, count = item, 1
        normalised = normalise(text)
        if not normalised:
            continue
        try:
            count = int(count)
        except (TypeError, ValueError):
            count = 1
        if normalised in merged:
            merged[normalised][2] += count
        else:
            merged[normalised] = [str(text), normalised, count]
    return [(text, normalised, count) for text, normalised, count in merged.values()]


def _percent(part: int, whole: int) -> float:
    return round(part / whole * 100, 1) if whole else 0.0


def preview(
    answers: Mapping[Any, int] | Iterable[Any] | pd.Series,
    codeframe: Mapping[str, Any] | Codeframe,
) -> dict[str, Any]:
    """How ``codeframe`` codes ``answers`` — each distinct answer with how many
    gave it — as JSON-ready data for an editor to show:

    * ``answers``: one entry per distinct answer (by fingerprint, in the order
      given): ``text``, ``count``, ``fingerprint``, ``codes``, ``source``
      (``hand`` | ``rule`` | ``uncoded``) and, for ``rule``, ``hits`` — each
      theme's ``code``, ``label``, the include ``term`` that matched, the
      ``fragment`` it matched and the ``clause`` it was in;
    * ``themes``: per theme its ``count`` of respondents (answers × counts),
      ``percent`` of those who answered, and how many of them by hand and by
      rules;
    * ``nets``: per net (a group of two or more themes) its ``count`` —
      a respondent once, however many of its themes they have — and percent;
    * ``coverage``: :func:`coverage`'s counts, of respondents, and ``distinct``
      the same of distinct answers.

    A codeframe given as JSON is read with :func:`parse` (and raises
    :class:`CodeframeError` as it does).
    """

    cf = _as_codeframe(codeframe)
    distinct = _distinct(answers)
    coded = [_code_text(cf, normalised) for _, normalised, _ in distinct]
    weights = [count for _, _, count in distinct]
    counts = tally(coded, weights)
    answered = counts["answered"]
    per_theme = {theme.code: {"count": 0, "by_hand": 0, "by_rules": 0} for theme in cf.themes}
    nets = cf.nets
    per_net = dict.fromkeys(nets, 0)
    rows = []
    for (text, normalised, count), result in zip(distinct, coded, strict=True):
        got = result.codes or ()
        for code in got:
            if code in per_theme:
                per_theme[code]["count"] += count
                per_theme[code]["by_hand" if result.source == "hand" else "by_rules"] += count
        for name, members in nets.items():
            if any(code in members for code in got):
                per_net[name] += count
        rows.append(
            {
                "text": text,
                "count": count,
                "fingerprint": _fingerprint_of(normalised),
                "codes": list(got),
                "source": result.source,
                "hits": [
                    {
                        "code": fired.theme.code,
                        "label": fired.theme.label,
                        "term": fired.term,
                        "fragment": fired.fragment,
                        "clause": fired.where,
                    }
                    for fired in result.fired
                ],
            }
        )
    return {
        "answers": rows,
        "themes": [
            {
                "code": theme.code,
                "label": theme.label,
                "group": theme.group,
                **per_theme[theme.code],
                "percent": _percent(per_theme[theme.code]["count"], answered),
            }
            for theme in cf.themes
        ],
        "nets": [
            {
                "group": name,
                "codes": list(members),
                "count": per_net[name],
                "percent": _percent(per_net[name], answered),
            }
            for name, members in nets.items()
        ],
        "coverage": {**counts, "percent_coded": _percent(counts["coded"], answered)},
        "distinct": tally(coded),
    }


def explain(text: Any, codeframe: Mapping[str, Any] | Codeframe) -> dict[str, Any]:
    """Why ``text`` is coded as it is, step by step, as JSON-ready data:

    ``normalised`` (the text the rules read: normalised, one apostrophe, the
    replacements made), ``fingerprint``, ``tokens`` (each ``word``, whether it
    is ``negated`` and by which word, its ``clause``), ``clauses``, ``manual``
    (a coder's decision for this answer, or None — it overrides the rules),
    ``rules`` (every rule whose include term matched, or would have but for a
    negation: ``status`` ``fired`` | ``vetoed`` | ``negated``, the ``term``, the
    ``fragment``, the ``clause`` and the ``reason``), ``dropped`` (themes that
    fired and were set aside, and why) and the result: ``codes`` and ``source``.
    """

    cf = _as_codeframe(codeframe)
    normalised = normalise(text)
    result = _code_text(cf, normalised)
    rules = cf.rule_set
    analysis = rules.prepare(normalised)
    clause_of = {c: i for i, c in enumerate(sorted({c for c in analysis.clause if c >= 0}))}
    manual = cf.assignments.get(_fingerprint_of(normalised)) if normalised else None
    if manual is not None and cf.version < 2:
        manual = (int(manual),)
    fired = rules.fire(analysis)
    _, dropped = text_rules.resolve(fired, multiple=cf.multiple, max_codes=cf.max_codes)
    return {
        "text": "" if text is None else str(text),
        "normalised": analysis.text,
        "fingerprint": _fingerprint_of(normalised),
        "tokens": [
            {
                "word": word,
                "negated": analysis.negated_by[i] >= 0,
                "negated_by": analysis.words[analysis.negated_by[i]]
                if analysis.negated_by[i] >= 0
                else None,
                "clause": clause_of.get(analysis.clause[i]),
            }
            for i, word in enumerate(analysis.words)
        ],
        "clauses": analysis.clause_texts(),
        "manual": None if manual is None else list(manual),
        "rules": rules.explain(analysis),
        "dropped": [
            {"code": f.theme.code, "label": f.theme.label, "reason": why}
            for f, why in ([] if manual is not None else dropped)
        ],
        "codes": list(result.codes or ()),
        "source": result.source,
    }


def suggest(
    answers: Mapping[Any, int] | Iterable[Any] | pd.Series,
    n: int = 30,
    *,
    codeframe: Mapping[str, Any] | Codeframe | None = None,
    min_count: int = 2,
) -> dict[str, list[dict[str, Any]]]:
    """Words and two-word phrases that come up most among ``answers`` (the
    uncoded ones, with their counts): ``words`` and ``phrases``, the ``n``
    commonest of each held by at least ``min_count`` respondents, each with its
    ``count`` and one ``example`` answer. English stop words are left out; a
    word mostly met negated comes as ``not_word``, a term that finds it. With
    a ``codeframe`` its replacements are made first, and the answers it codes
    left out."""

    cf = None if codeframe is None else _as_codeframe(codeframe)
    rules = cf.rule_set if cf is not None and cf.version >= 2 else None
    items = []
    for text, normalised, count in _distinct(answers):
        if cf is not None and _code_text(cf, normalised).source != "uncoded":
            continue
        read = rules.replaced(normalised) if rules is not None else text_rules.rule_text(normalised)
        items.append((text, read, count))
    return text_rules.suggest_terms(items, n=max(0, int(n)), min_count=min_count)
