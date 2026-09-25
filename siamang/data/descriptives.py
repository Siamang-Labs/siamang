"""Descriptive statistics of numeric variables — the first table of most reports.

One row per variable (per group, with ``by``): how many answered, how many did
not, and the mean, SD, median, minimum and maximum of the answers — optionally
the quartiles, skewness and kurtosis too. What a researcher checks before any
test, and what a methods section quotes.

Three things are decided here rather than left to whoever reads the numbers:

    **A missing code is not an answer.** A 99 "Don't know" on a 1–5 scale is a
    fact about the respondent, not a very high rating, so every code the
    codebook declares missing counts as missing — as ``prepare.missing`` and
    the index, scale and cluster steps already treat it — and the table's stats
    name the codes it set aside. A value that is not a number at all is set
    aside and counted the same way.

    **The weight reaches what it has a standard form for.** On weighted data
    the mean, SD, median and quartiles are weighted — with the same formulas
    the Group means table uses, so the two never disagree — while N and Missing
    stay counts of people, with the weighted base in a column of its own. The
    stats give the weighted total, Kish's effective sample size and the design
    effect. Skewness and kurtosis have no one agreed weighted form, so they stay
    unweighted and the stats say so.

    **Nothing undefined is printed as a number.** An SD needs two answers,
    skewness three and kurtosis four (and all three some spread); below that the
    cell is blank rather than a zero somebody might quote.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from siamang.core.variable import VariableMap

__all__ = ["Descriptives", "describe", "weighted_quantile"]

#: The columns of the table, in order; the optional ones are dropped when unused.
_BASE = ["N", "Missing", "Mean", "SD", "Min", "Median", "Max"]
_DETAIL = ["Q1", "Q3", "Skewness", "Kurtosis"]


@dataclass(frozen=True, slots=True)
class Descriptives:
    """The table and the statistics printed under it."""

    table: pd.DataFrame
    stats: dict[str, Any] = field(default_factory=dict)


def weighted_quantile(values: np.ndarray, weights: np.ndarray, q: float) -> float:
    """The smallest value whose cumulative weight reaches ``q`` of the total.

    No interpolation: with weights there is no agreed way to interpolate, and
    this is the definition the Group means table already uses for its weighted
    median, so a median here and there is the same number.
    """

    total = float(weights.sum())
    if len(values) == 0 or total <= 0:
        return float("nan")
    order = np.argsort(values, kind="stable")
    cumulative = np.cumsum(weights[order])
    at = min(int(np.searchsorted(cumulative, q * total)), len(values) - 1)
    return float(values[order][at])


def describe(
    frame: pd.DataFrame,
    columns: Sequence[str],
    *,
    variables: VariableMap | None = None,
    weight: str | None = None,
    by: str | None = None,
    detail: bool = False,
) -> Descriptives:
    """N, missing, mean, SD, median, minimum and maximum of each of ``columns``.

    ``by`` splits every variable by the groups of another (labelled from the
    codebook, in its order; its own missing codes are no group). A
    multiple-choice ``by`` gives one group per option, of everyone who chose
    it: the groups overlap, and the stats say so. ``detail``
    adds Q1 and Q3 (NumPy's default linear interpolation, R's type 7 — the
    weighted ones by :func:`weighted_quantile`), skewness and excess kurtosis
    (the bias-corrected G1 and G2 SPSS and Excel report). ``weight`` names a
    weight column; a missing weight counts 0, a negative one is refused.
    """

    names = list(dict.fromkeys(columns))
    if not names:
        raise ValueError("Descriptive statistics need at least one variable.")
    absent = [name for name in [*names, *([by] if by else [])] if name not in frame.columns]
    if absent:
        raise KeyError(f"column not found: {', '.join(map(repr, absent))}")
    from siamang.data import multi

    listed = [name for name in names if multi.is_multi(frame[name])]
    if listed:
        raise TypeError(
            f"{', '.join(listed)} {'holds' if len(listed) == 1 else 'hold'} multiple-choice "
            "answers (lists of codes), which have no mean. Describe them with Frequencies, "
            "or run prepare.explode first and describe the 0/1 columns it makes."
        )

    weights = _weights(frame, weight)
    groups = _groups(frame, by, variables) if by else [(None, None, frame.index)]

    rows: list[dict[str, Any]] = []
    set_aside: dict[str, list[str]] = {}
    not_numbers: dict[str, int] = {}
    for name in names:
        values, is_code, is_text = _numeric(frame[name], _variable(variables, name))
        if int(is_code.sum()):
            codes = _variable(variables, name).missing_values  # type: ignore[union-attr]
            set_aside[name] = [str(code) for code in codes]
        if int(is_text.sum()):
            not_numbers[name] = int(is_text.sum())
        for _value, group_label, index in groups:
            usable = values.loc[index].dropna()
            row: dict[str, Any] = {"Variable": name, "Label": _label(variables, name)}
            if by:
                row[_label(variables, by)] = group_label
            row.update(
                _summary(
                    usable.to_numpy(dtype=float),
                    None if weights is None else weights.loc[usable.index].to_numpy(dtype=float),
                    missing=int(len(index) - len(usable)),
                    detail=detail,
                )
            )
            rows.append(row)

    leading = ["Variable", "Label", *([_label(variables, by)] if by else [])]
    counts = ["N", *(["Weighted N"] if weights is not None else []), "Missing"]
    spread = ["Mean", "SD", "Min", *(["Q1"] if detail else [])]
    spread += ["Median", *(["Q3"] if detail else []), "Max"]
    spread += ["Skewness", "Kurtosis"] if detail else []
    table = pd.DataFrame(rows, columns=[*leading, *counts, *spread])

    stats: dict[str, Any] = {"Variables": len(names), "Rows": int(len(frame))}
    if by:
        stats["By"] = _label(variables, by)
        grouped = len(set().union(*(index for _v, _l, index in groups)))
        if grouped < len(frame):
            stats["Not in a group"] = int(len(frame) - grouped)
        if multi.is_multi(frame[by]):
            stats["Groups"] = (
                f"overlap: {_label(variables, by)} allows several answers, so a respondent "
                "is in the group of every option they chose"
            )
    if set_aside:
        stats["Missing codes"] = "; ".join(
            f"{name}: {', '.join(codes)}" for name, codes in set_aside.items()
        )
    if not_numbers:
        stats["Not numbers"] = "; ".join(f"{name}: {n}" for name, n in not_numbers.items())
    if weights is not None:
        total = float(weights.sum())
        squares = float((weights**2).sum())
        effective = total**2 / squares if squares > 0 else 0.0
        stats["Weight"] = weight
        stats["Weighted N"] = round(total, 1)
        stats["Effective N"] = round(effective, 1)
        if effective > 0:
            # Kish's deff over the rows the weighting kept (a weight of 0 is a
            # row it set aside, not a respondent who makes the sample smaller).
            stats["Design effect"] = round(int((weights > 0).sum()) / effective, 3)
        stats["Note"] = (
            ("mean, SD, median and quartiles" if detail else "mean, SD and median")
            + " are weighted; N and Missing count respondents"
            + (
                "; rows weighted 0 are left out of the weighted statistics"
                if bool((weights == 0).any())
                else ""
            )
            + ("; skewness and kurtosis are unweighted" if detail else "")
        )
    return Descriptives(table=table, stats=stats)


# ─── helpers ─────────────────────────────────────────────────────────────────


def _variable(variables: VariableMap | None, name: str):
    return variables.get(name) if variables is not None else None


def _label(variables: VariableMap | None, name: str) -> str:
    variable = _variable(variables, name)
    return (variable.label if variable is not None else None) or name


def _weights(frame: pd.DataFrame, weight: str | None) -> pd.Series | None:
    if weight is None:
        return None
    if weight not in frame.columns:
        raise KeyError(f"column not found: {weight!r}")
    values = pd.to_numeric(frame[weight], errors="coerce").fillna(0.0).astype(float)
    if bool((values < 0).any()):
        raise ValueError(f"The weight column {weight!r} has negative values.")
    return values


def _numeric(series: pd.Series, variable: Any) -> tuple[pd.Series, pd.Series, pd.Series]:
    """The answers as numbers, with the codebook's missing codes and anything that
    is not a finite number set to NaN — and masks of which was which."""

    numeric = pd.to_numeric(series, errors="coerce").astype(float)
    is_code = pd.Series(False, index=series.index)
    codes = list(variable.missing_values) if variable is not None else []
    if codes:
        numeric_codes = [float(code) for code in pd.to_numeric(pd.Series(codes), errors="coerce")]
        is_code = series.isin(codes) | numeric.isin([c for c in numeric_codes if c == c])
        is_code = is_code.fillna(False).astype(bool)
    finite = numeric.notna() & np.isfinite(numeric.fillna(0.0))
    is_text = series.notna() & ~finite & ~is_code
    return numeric.where(finite & ~is_code), is_code, is_text


def _groups(
    frame: pd.DataFrame, by: str, variables: VariableMap | None
) -> list[tuple[Any, str, pd.Index]]:
    """``(value, label, rows)`` per group, codebook order first, then the rest.

    A blank and a declared missing code of ``by`` are no group: a mean for
    "Don't know which region" is not a regional mean. A multiple-choice ``by``
    has a group per option chosen, and they overlap.
    """

    from siamang.data import multi

    series = frame[by]
    variable = _variable(variables, by)
    missing = set(variable.missing_values) if variable is not None else set()
    labels = dict(variable.labels) if variable is not None else {}
    listed = multi.is_multi(series)
    found = multi.codes_in(series) if listed else series.dropna().unique().tolist()
    present = [value for value in found if value not in missing]
    ordered = [value for value in labels if value in present]
    ordered += [value for value in sorted(present, key=str) if value not in ordered]

    def rows(value: Any) -> pd.Index:
        chose = multi.reach(series, value) if listed else series.eq(value)
        return series.index[chose.fillna(False).to_numpy(dtype=bool)]

    return [(value, str(labels.get(value, _display(value))), rows(value)) for value in ordered]


def _summary(
    values: np.ndarray, weights: np.ndarray | None, *, missing: int, detail: bool
) -> dict[str, Any]:
    n = int(len(values))
    nan = float("nan")
    row: dict[str, Any] = {"N": n, "Missing": missing}
    if weights is not None:
        row["Weighted N"] = round(float(weights.sum()), 1)
    if n == 0:
        row.update(dict.fromkeys(_BASE[2:] + _DETAIL, nan))
        return row
    row["Min"] = _round(float(values.min()))
    row["Max"] = _round(float(values.max()))
    spread = float(values.max() - values.min())
    if weights is None:
        row["Mean"] = _round(float(values.mean()))
        row["SD"] = _round(float(values.std(ddof=1))) if n > 1 else nan
        q1, median, q3 = np.percentile(values, [25, 50, 75])
        row.update({"Median": _round(median), "Q1": _round(q1), "Q3": _round(q3)})
    else:
        # An answer weighted 0 (or with no weight, which counts 0) is one the
        # weighting set aside, as the design effect counts it: it takes no part
        # in the mean, the SD — not even in its n / (n − 1) — or the quartiles.
        # N and Missing still count it, and Min and Max are of every answer.
        carried = weights > 0
        if not carried.any():
            # Every answer weighs nothing: there is no weighted mean to give.
            row.update({"Mean": nan, "SD": nan, "Median": nan, "Q1": nan, "Q3": nan})
        else:
            values_w, weights_w = values[carried], weights[carried]
            kept = int(len(values_w))
            mean = float(np.average(values_w, weights=weights_w))
            row["Mean"] = _round(mean)
            if kept > 1:
                # The Group means table's weighted SD: the weighted variance scaled
                # by n / (n − 1) over the answers that carry weight, so equal
                # weights give exactly the sample SD of those answers.
                variance = float(np.average((values_w - mean) ** 2, weights=weights_w))
                row["SD"] = _round((variance * kept / (kept - 1)) ** 0.5)
            else:
                row["SD"] = nan  # an SD needs two answers
            row["Median"] = _round(weighted_quantile(values_w, weights_w, 0.5))
            row["Q1"] = _round(weighted_quantile(values_w, weights_w, 0.25))
            row["Q3"] = _round(weighted_quantile(values_w, weights_w, 0.75))
    if detail:
        from scipy import stats as sp_stats

        # Undefined without spread, and scipy's small-sample corrections need
        # three and four answers: below that the cell is blank, not a number.
        row["Skewness"] = (
            _round(float(sp_stats.skew(values, bias=False))) if n >= 3 and spread > 0 else nan
        )
        row["Kurtosis"] = (
            _round(float(sp_stats.kurtosis(values, fisher=True, bias=False)))
            if n >= 4 and spread > 0
            else nan
        )
    else:
        row.pop("Q1", None)
        row.pop("Q3", None)
    return row


def _display(value: Any) -> Any:
    """An unlabelled group's code as it was entered: 3, not the 3.0 a column
    with a blank in it turns every code into."""

    return int(value) if isinstance(value, float) and value.is_integer() else value


def _round(value: float) -> float:
    return round(float(value), 3) if value == value else float("nan")
