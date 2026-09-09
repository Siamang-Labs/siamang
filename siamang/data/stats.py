"""Tidy-frame descriptives: frequencies, crosstabs and a chi-square test.

These are the plain-``DataFrame`` counterparts of :class:`~siamang.data.analysis.DataAnalysis`
for scripts that work on a frame without a :class:`~siamang.data.SurveyData`
wrapper. Results are ``pandas`` objects that drop straight into
``Report.add(...)``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def frequencies(
    df: pd.DataFrame, column: str, *, weight: str | None = None, dropna: bool = True
) -> pd.DataFrame:
    """Frequency distribution of ``column`` as ``value`` / ``count`` / ``percent`` rows.

    Sorted by value. With ``weight`` the counts are summed weights, rounded
    to whole responses.
    """

    if column not in df.columns:
        raise KeyError(f"column not found: {column!r}")
    if weight is not None:
        if weight not in df.columns:
            raise KeyError(f"column not found: {weight!r}")
        grouped = df.groupby(column, dropna=dropna)[weight].sum()
    else:
        grouped = df.groupby(column, dropna=dropna).size()
    total = float(grouped.sum()) or 1.0
    out = grouped.reset_index()
    out.columns = ["value", "count"]
    out["percent"] = (out["count"] / total * 100).round(1)
    out["count"] = out["count"].round().astype(int)
    return out.sort_values("value").reset_index(drop=True)


def crosstab(
    df: pd.DataFrame,
    row: str,
    col: str,
    *,
    weight: str | None = None,
    normalize: bool | str | None = None,
) -> pd.DataFrame:
    """Two-way table of ``row`` × ``col``.

    ``weight`` sums a weight column instead of counting rows. ``normalize``
    is passed to :func:`pandas.crosstab` (``"index"``, ``"columns"``,
    ``"all"`` or ``True``); when set, cells are percentages rounded to one
    decimal.
    """

    for name in (row, col):
        if name not in df.columns:
            raise KeyError(f"column not found: {name!r}")
    if weight is not None and weight not in df.columns:
        raise KeyError(f"column not found: {weight!r}")
    values = df[weight] if weight is not None else None
    aggfunc = "sum" if weight is not None else None
    table = pd.crosstab(
        df[row], df[col], values=values, aggfunc=aggfunc, normalize=normalize or False
    )
    if normalize:
        table = (table * 100).round(1)
    return table


def chi2(df: pd.DataFrame, a: str, b: str) -> dict[str, float | int]:
    """Pearson chi-square test of independence between two categorical columns.

    Returns ``chi2``, ``dof``, ``p``, Cramér's V (``cramers_v``) and ``n``.
    """

    try:
        from scipy.stats import chi2_contingency
    except ImportError as exc:
        raise ImportError("chi2() requires scipy to be installed.") from exc

    for name in (a, b):
        if name not in df.columns:
            raise KeyError(f"column not found: {name!r}")
    table = pd.crosstab(df[a], df[b])
    chi2_stat, p, dof, _expected = chi2_contingency(table)
    n = int(table.to_numpy().sum())
    k = min(table.shape) - 1
    cramers_v = float(np.sqrt(chi2_stat / (n * k))) if n > 0 and k > 0 else 0.0
    return {
        "chi2": float(chi2_stat),
        "dof": int(dof),
        "p": float(p),
        "cramers_v": round(cramers_v, 4),
        "n": n,
    }


__all__ = ["chi2", "crosstab", "frequencies"]
