"""The data against its codebook, as a table a flow can show before analysis.

:meth:`SurveyData.validate` says *that* a variable has values outside its
valid range or codes nobody labeled. Before anything is analyzed a researcher
also needs *how many* rows and *which* values — 99 in an age column is a
missing code somebody forgot to declare, 7 on a five-point scale is a recode
that went wrong, and the two need different fixes. :func:`check` runs the same
validation and adds both, one row per problem, errors first.

Problems about the shape of the file rather than its values — columns the
codebook does not know, variables the data does not have — are gathered into
one row each, because a prepared frame (after Select, say) legitimately lacks
many codebook variables and fifty rows of that would bury the one row that
matters. Two kinds of undeclared column are expected rather than problems and
are named in the stats instead: the weight column the data is weighted by, and
the response metadata the runtime and the platform keep beside the answers
(:data:`METADATA_COLUMNS`, and the survey link's ``url_*`` parameters).

It counts rows, not people in the population, so on weighted data the result
says the weight is not applied.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pandas as pd

if TYPE_CHECKING:
    from siamang.core.variable import ValidationIssue, Variable
    from siamang.data.survey_data import SurveyData

__all__ = ["COLUMNS", "METADATA_COLUMNS", "DataCheck", "check"]

COLUMNS = ["Severity", "Variable", "Problem", "Rows", "Examples", "Code"]

#: How many offending values a row lists before it says "…".
_EXAMPLES = 5

_PROBLEMS = {
    "INVALID_LABEL_VALUE": "codes the codebook has no label for",
    "DUPLICATE_ID": "the same ID on more than one row",
    "INVALID_WEIGHT": "weight values that are not numbers",
    "MISSING_VALUE_WITHOUT_LABEL": "missing codes without a label",
    "MISSING_METADATA": "no codebook, so no values could be checked",
    "MISSING_WEIGHT_COLUMN": "the weight column is not in the data",
    "MISSING_COLUMN": "in the codebook but not in the data",
    "QUESTIONNAIRE_COLUMN_MISSING": "in the codebook but not in the data",
    "EXTRA_COLUMN": "in the data but not in the codebook",
}
#: Problems of the file's shape, gathered into one row per code.
_GATHERED = ("MISSING_COLUMN", "EXTRA_COLUMN")

#: Columns a response table carries beside the answers, which no codebook
#: declares: the store's own (``id``, ``survey_id``, ``created_at``, …), the
#: runtime's (``respondent_id``, ``__status``, the timing) and the platform's
#: behavioral signals, and the ``duration_s`` and ``partial`` that Speeders adds.
#: With the ``url_*`` link parameters they are not reported as extra columns.
#: The response timestamps a platform's frame carries beside the answers, and
#: what a chart calls them: no codebook declares them, so no label is found
#: there (a Trend's axis read "created_at (day)").
RESPONSE_TIME_LABELS = {
    "created_at": "Response date",
    "updated_at": "Last change",
    "started_at": "Start time",
    "submitted_at": "Submission time",
}

METADATA_COLUMNS = frozenset(
    {
        "id",
        "survey_id",
        "respondent_id",
        "created_at",
        "updated_at",
        "started_at",
        "submitted_at",
        "duration_s",
        "partial",
        "__status",
        "captcha",
        "tab_switches",
        "hidden_seconds",
        "pastes",
    }
)


@dataclass(frozen=True, slots=True)
class DataCheck:
    """The problems found, and the counts printed under them."""

    table: pd.DataFrame
    stats: dict[str, Any] = field(default_factory=dict)


def check(data: SurveyData, variables: Sequence[str] | None = None) -> DataCheck:
    """Every problem :meth:`SurveyData.validate` finds, with rows and examples.

    ``variables`` limits the check to those variables (the file-level problems
    included); by default every column and every codebook variable is checked.
    """

    from siamang.data.analysis import unweighted_note

    wanted = set(variables) if variables else None
    issues = [issue for issue in data.validate() if wanted is None or _subject(issue) in wanted]
    # The questionnaire's copy of "not in the data" says the same thing again.
    absent = {issue.variable for issue in issues if issue.code == "MISSING_COLUMN"}
    issues = [
        issue
        for issue in issues
        if not (issue.code == "QUESTIONNAIRE_COLUMN_MISSING" and issue.variable in absent)
    ]
    # The weight and the response metadata are expected beside the codebook.
    weight = [i.column for i in issues if i.code == "EXTRA_COLUMN" and i.column == data.weight]
    metadata = [
        str(issue.column)
        for issue in issues
        if issue.code == "EXTRA_COLUMN" and issue.column != data.weight and _metadata(issue.column)
    ]
    issues = [
        issue
        for issue in issues
        if not (
            issue.code == "EXTRA_COLUMN" and (issue.column in weight or issue.column in metadata)
        )
    ]

    rows: list[dict[str, Any]] = []
    gathered: dict[str, list[ValidationIssue]] = {}
    for issue in issues:
        code = "MISSING_COLUMN" if issue.code == "QUESTIONNAIRE_COLUMN_MISSING" else issue.code
        if code in _GATHERED:
            gathered.setdefault(code, []).append(issue)
            continue
        rows.append(_row(data, issue))
    for code, members in gathered.items():
        names = [str(_subject(issue)) for issue in members]
        rows.append(
            {
                "Severity": members[0].severity,
                "Variable": names[0] if len(names) == 1 else f"{len(names)} columns",
                "Problem": _PROBLEMS[code],
                "Rows": None,
                "Examples": _join(names, limit=8),
                "Code": code,
            }
        )
    rows.sort(key=lambda row: 0 if row["Severity"] == "error" else 1)
    table = pd.DataFrame(rows, columns=COLUMNS)
    # A count, or nothing where a problem is about a column rather than rows.
    table["Rows"] = pd.array([row["Rows"] for row in rows], dtype="Int64")

    checked = (
        len(wanted)
        if wanted is not None
        else len(set(data.frame.columns) | set(data.variables or {}))
    )
    errors = sum(1 for row in rows if row["Severity"] == "error")
    stats: dict[str, Any] = {
        "Checked": f"{checked} variable{'' if checked == 1 else 's'}, {len(data.frame)} rows",
        "Errors": errors,
        "Warnings": len(rows) - errors,
    }
    if not rows:
        stats["Result"] = "no problems found"
    expected = [f"{name} (the weight)" for name in weight]
    if metadata:
        expected.append(f"{_join(sorted(metadata), limit=8)} (response metadata)")
    if expected:
        stats["Not in the codebook, as expected"] = "; ".join(expected)
    if data.weight is not None:
        stats["Weight"] = unweighted_note(data.weight)
    return DataCheck(table=table, stats=stats)


def _metadata(column: Any) -> bool:
    return isinstance(column, str) and (column in METADATA_COLUMNS or column.startswith("url_"))


def _subject(issue: ValidationIssue) -> str | None:
    return issue.variable or issue.column


def _row(data: SurveyData, issue: ValidationIssue) -> dict[str, Any]:
    name = _subject(issue)
    variable = data.variables.get(name) if data.variables is not None and name else None
    series = data.frame[name] if name in data.frame.columns else None
    rows: int | None = None
    examples = ""
    problem = _PROBLEMS.get(issue.code, issue.message)
    if series is not None and variable is not None:
        answers = _answers(series, variable)
        if issue.code == "OUT_OF_RANGE":
            low, high = variable.valid_range  # type: ignore[misc]
            problem = f"outside the valid range {_bound(low)}–{_bound(high)}"
            bad = _out_of_range(answers, low, high)
            rows, examples = int(bad.sum()), _tally(answers[bad])
        elif issue.code == "INVALID_LABEL_VALUE":
            known = set(variable.labels)
            unlabelled = answers.map(lambda value: [v for v in _flat(value) if v not in known])
            rows = int(unlabelled.map(bool).sum())
            examples = _tally(pd.Series([v for values in unlabelled for v in values]))
        elif issue.code == "INVALID_DTYPE":
            problem = f"values that are not of type {variable.dtype}"
            bad = _wrong_type(answers, variable.dtype)
            if bad is not None:
                rows, examples = int(bad.sum()), _tally(answers[bad])
        elif issue.code == "DUPLICATE_ID":
            present = series.dropna()
            repeated = present[present.duplicated(keep=False)]
            rows, examples = int(len(repeated)), _tally(repeated)
        elif issue.code == "MISSING_VALUE_WITHOUT_LABEL":
            unlabelled = [c for c in variable.missing_values if c not in variable.missing_labels]
            examples = _join([str(code) for code in unlabelled])
    if issue.code == "INVALID_WEIGHT" and series is not None:
        present = series.dropna()
        bad = pd.to_numeric(present, errors="coerce").isna()
        rows, examples = int(bad.sum()), _tally(present[bad])
    return {
        "Severity": issue.severity,
        "Variable": name or "",
        "Problem": problem,
        "Rows": rows,
        "Examples": examples,
        "Code": issue.code,
    }


def _answers(series: pd.Series, variable: Variable) -> pd.Series:
    """The values the checks look at: no blanks and no declared missing codes —
    the same values ``validate`` judged."""

    present = series.dropna()
    codes = set(variable.missing_values)
    if not codes:
        return present
    keep = present.map(lambda v: isinstance(v, list | tuple | set) or v not in codes)
    return present[keep.astype(bool)]


def _out_of_range(answers: pd.Series, low: Any, high: Any) -> pd.Series:
    numeric = pd.to_numeric(answers, errors="coerce")
    bad = numeric.isna()
    if low is not None:
        bad |= numeric < low
    if high is not None:
        bad |= numeric > high
    return bad.fillna(True).astype(bool)


def _wrong_type(answers: pd.Series, dtype: str | None) -> pd.Series | None:
    if dtype not in {"int", "float"}:
        return None  # the other types are judged column-wide, not value by value
    numeric = pd.to_numeric(answers, errors="coerce")
    bad = numeric.isna()
    if dtype == "int":
        bad |= (numeric % 1 != 0).fillna(False)
    return bad.astype(bool)


def _flat(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list | tuple | set) else [value]


def _tally(values: pd.Series) -> str:
    """``7 (12), 8 (1)``: the offending values, most frequent first."""

    counts = Counter(_display(value) for value in values)
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return _join([f"{value} ({n})" for value, n in ordered])


def _join(items: list[str], limit: int = _EXAMPLES) -> str:
    shown = ", ".join(items[:limit])
    return shown + (f", … ({len(items) - limit} more)" if len(items) > limit else "")


def _display(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _bound(value: Any) -> str:
    return "…" if value is None else _display(value)
