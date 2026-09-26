"""The respondents who answered every one of a set of variables.

A paired test compares answers that come in sets from one person, and a factor
analysis correlates items over the same people; either way a respondent with a
blank in one of the variables has nothing to contribute to the others, and is
left out of all of them. :func:`listwise` makes that one decision in one place
and keeps the count, so every result can say how many people it left out and
why.

The codebook's missing codes are missing here, not answers: a "Refused" coded
9 on a 1–5 scale would otherwise rank above "Full trust" and correlate like a
very high rating. They are turned into blanks first, as ``prepare.missing``
does, and counted apart so the result can name them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

from siamang.data import multi

if TYPE_CHECKING:
    from siamang.data.survey_data import SurveyData
    from siamang.reporting.result_table import ResultTable


@dataclass(frozen=True, slots=True)
class Listwise:
    """The complete rows of some variables, and what it took to get them."""

    #: The complete rows, codebook missing codes already blank; the original index.
    frame: pd.DataFrame
    #: Rows left out for a blank (or a missing code) in any of the variables.
    excluded: int
    #: Answers that were a codebook missing code, and so counted as blanks.
    coded: int
    #: ``code = label`` of each missing code that was met, in first-met order.
    codes: tuple[str, ...] = ()
    #: Which rows of the data are complete, by position: what puts a result back
    #: on its rows when the index repeats a label (waves concatenated without
    #: ``ignore_index``), where selecting by label would pull in every row that
    #: shares it.
    mask: np.ndarray | None = None

    @property
    def n(self) -> int:
        return int(len(self.frame))

    def note(self) -> str | None:
        """What the missing codes were, for a result's statistics; None if none."""
        if not self.coded:
            return None
        answers = "answer" if self.coded == 1 else "answers"
        return f"{self.coded} {answers} with a missing code ({', '.join(self.codes)}) left out"

    def report(self, stats: dict[str, Any], where: str) -> None:
        """Say in ``stats`` how many respondents were left out, and why."""
        stats["Excluded"] = self.excluded
        if self.excluded:
            stats["Excluded because"] = f"a missing value in {where} (listwise)"
        note = self.note()
        if note:
            stats["Missing codes"] = note


def listwise(data: SurveyData, columns: list[str], *, numeric: bool = True) -> Listwise:
    """The rows of ``data`` with a value in every one of ``columns``.

    ``numeric`` converts the columns to numbers and refuses a column holding
    text that is not one — dropping those answers as blanks would change the
    sample without saying so. Multiple-choice columns (lists of codes) are
    refused with the way out: explode them first.
    """

    frame = data.frame
    unknown = [column for column in columns if column not in frame.columns]
    if unknown:
        raise KeyError(f"column not found: {', '.join(map(repr, unknown))}")
    listed = [column for column in columns if multi.is_multi(frame[column])]
    if listed:
        raise TypeError(
            f"{', '.join(listed)} {'holds' if len(listed) == 1 else 'hold'} multiple-choice "
            "answers (lists of codes), which have no single value to compare. Run "
            "prepare.explode first: it turns each option into its own 0/1 column."
        )
    values = frame[columns].copy()
    coded = 0
    met: list[str] = []
    variables = data.variables
    for column in columns:
        if variables is None or column not in variables:
            continue
        missing = variables[column].structured_missing_values()
        if not missing:
            continue
        hit = values[column].isin([item.code for item in missing])
        if not hit.any():
            continue
        coded += int(hit.sum())
        present = set(values.loc[hit, column].tolist())
        for item in missing:
            text = f"{item.code} = {item.label}"
            if item.code in present and text not in met:
                met.append(text)
        values[column] = values[column].mask(hit)
    if numeric:
        values = _numbers(values)
    mask = values.notna().all(axis=1).to_numpy()
    complete = values[mask]
    return Listwise(
        frame=complete,
        excluded=int(len(values) - len(complete)),
        coded=coded,
        codes=tuple(met),
        mask=mask,
    )


def _numbers(values: pd.DataFrame) -> pd.DataFrame:
    converted = values.apply(pd.to_numeric, errors="coerce")
    for column in values.columns:
        lost = values[column].notna() & converted[column].isna()
        if lost.any():
            sample: Any = values.loc[lost, column].iloc[0]
            raise TypeError(
                f"{column} holds text that is not a number (for example {sample!r}), so "
                "it has no value to compare. Recode it to numeric codes first."
            )
    return converted.astype(float)


# ── what the results built on these rows share ───────────────────────────────


def distinct(variables: list[str]) -> None:
    """Refuse a variable listed twice: compared or correlated with itself it
    says nothing, and a factor analysis could not even invert the matrix."""
    twice = [name for name in dict.fromkeys(variables) if variables.count(name) > 1]
    if twice:
        raise ValueError(
            f"{', '.join(twice)} {'is' if len(twice) == 1 else 'are'} listed twice; "
            "each variable can be used once."
        )


def label_of(data: SurveyData, name: str) -> str:
    """The variable's label from the codebook, or its name."""
    if data.variables is not None and name in data.variables:
        return data.variables[name].label or name
    return name


def unweighted(stats: dict[str, Any], data: SurveyData) -> None:
    """Say in ``stats`` that the data's weight is not applied, when it has one."""
    if data.weight is not None:
        from siamang.data.analysis import unweighted_note

        stats["Weight"] = unweighted_note(data.weight)


def result_table(data: SurveyData, frame: pd.DataFrame, footer: dict[str, Any]) -> ResultTable:
    """``frame`` as a report table with ``footer`` as its statistics."""
    from siamang.reporting.result_table import ResultTable

    return ResultTable(data=data, frame=frame, footer=dict(footer))


def rounded(value: float | None, digits: int) -> float | None:
    """``value`` rounded, or None when there is none (or it is not finite)."""
    if value is None or not np.isfinite(value):
        return None
    return round(float(value), digits)


def p_rounded(value: float | None) -> float | None:
    """A p-value to four significant digits, so a tiny one is not rounded to 0."""
    if value is None or not np.isfinite(value):
        return None
    return float(f"{value:.4g}")


def round_p(value: float) -> float:
    """A p-value to four decimals, as the tables have always printed one — or,
    below 0.0001, to four significant digits (``1.134e-24``, ``5e-05``): a test
    that found something never reports p = 0. The line is where
    :func:`~siamang.reporting.tables.stat_text` starts writing an exponent, so a
    footer prints the p the statistics keep.

    NaN stays NaN, as ``round`` leaves it.
    """
    value = float(value)
    if not np.isfinite(value):
        return value
    if value != 0 and abs(value) < 1e-4:
        return float(f"{value:.4g}")
    return round(value, 4)


__all__ = [
    "Listwise",
    "distinct",
    "label_of",
    "listwise",
    "p_rounded",
    "result_table",
    "round_p",
    "rounded",
    "unweighted",
]
