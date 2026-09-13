"""Multiple-choice answers: one respondent, several codes, one honest base.

A ``MultiChoice`` question in its default mode stores an answer as a list of
codes — ``[1, 3]`` — because that is what it is. Every ordinary frame operation
then does the wrong thing with it: ``groupby`` cannot hash a list, a comparison
against a single code is false for a respondent who chose it among others, and
a frequency table of the raw column counts *combinations* ("1, 3" as its own
category) rather than options.

This module holds the rules that make such a column analyzable, and one rule
matters more than the mechanics:

    **The base is respondents, not answers.**

The share of an option is the people who named it over the people who answered
the question at all. The shares therefore sum above 100 %, which is a property
of the question and not a mistake — so everything here reports the base
alongside the numbers, and the tables built on it say so in words. A multiple
response table without its base is unreadable in exactly the way that looks
readable.

Not answering is not "chose nothing": an empty list and a missing value are
both "no answer", and they stay out of the base rather than counting as a
respondent who rejected every option.
"""

from __future__ import annotations

import contextlib
from collections.abc import Hashable, Mapping, Sequence
from typing import Any

import pandas as pd

__all__ = [
    "MultiCounts",
    "base_size",
    "codes_in",
    "crosstab",
    "explode",
    "frequencies",
    "is_multi",
    "reach",
    "responded",
]


def _is_list(value: Any) -> bool:
    return isinstance(value, list | tuple | set)


def is_multi(series: pd.Series) -> bool:
    """True when this column holds multiple-choice answers (lists of codes).

    Decided from the data rather than from the codebook on purpose: the same
    question is a list here and a set of 0/1 columns after :func:`explode`, and
    an analysis should not have to be told which it is looking at.
    """

    return bool(series.map(_is_list).any())


def responded(series: pd.Series) -> pd.Series:
    """True where the respondent answered the question at all.

    An empty list is not an answer — nobody chose "none of these" by leaving a
    question blank — so it stays out of every base computed here.
    """

    if is_multi(series):
        return series.map(lambda v: bool(_is_list(v) and len(v) > 0))
    return series.notna() & (series.astype(str).str.strip() != "")


def base_size(series: pd.Series, *, weight: pd.Series | None = None) -> float:
    """How many respondents the percentages are of."""

    answered = responded(series)
    return float(weight[answered].sum()) if weight is not None else float(answered.sum())


def codes_in(series: pd.Series) -> list[Hashable]:
    """Every code that appears, in first-seen order then sorted where possible.

    The codebook's own order is better when there is one; this is what a frame
    on its own can say, and it is stable for the same data.
    """

    seen: list[Hashable] = []
    for value in series:
        for code in value if _is_list(value) else ([value] if pd.notna(value) else []):
            if isinstance(code, Hashable) and code not in seen:
                seen.append(code)
    try:
        return sorted(seen)  # type: ignore[type-var]
    except TypeError:
        return seen  # mixed types: keep them in the order they appeared


def reach(series: pd.Series, code: Hashable) -> pd.Series:
    """True for every respondent who chose ``code`` — among others or alone.

    The operation a comparison against the raw column gets wrong: ``[1, 3] == 1``
    is false, so a filter on "chose option 1" silently keeps nobody.
    """

    return series.map(lambda v: code in v if _is_list(v) else v == code)


def explode(
    series: pd.Series,
    *,
    codes: Sequence[Hashable] | None = None,
    prefix: str = "",
) -> pd.DataFrame:
    """The answers as one 0/1 indicator column per code.

    What weights, regression and TURF all need, and what makes a question's
    storage mode an analysis decision rather than one taken before fieldwork.
    A respondent who did not answer gets missing values, not zeros: "did not
    say" and "said no to everything" are different findings.
    """

    wanted = list(codes) if codes is not None else codes_in(series)
    answered = responded(series)
    data = {
        f"{prefix}{code}": reach(series, code).where(answered).astype("boolean").astype("Int64")
        for code in wanted
    }
    return pd.DataFrame(data, index=series.index)


class MultiCounts(pd.DataFrame):
    """A multiple-response table that carries its own base.

    A subclass rather than a tuple so it still *is* a frame — it prints, plots
    and exports like one — while `base` and `answers` travel with it, because a
    reader who does not know the base cannot read the percentages.
    """

    _metadata = ["base", "answers"]

    @property
    def _constructor(self) -> type[MultiCounts]:
        return MultiCounts


def frequencies(
    df: pd.DataFrame,
    column: str,
    *,
    weight: str | None = None,
    codes: Sequence[Hashable] | None = None,
    labels: Mapping[Any, str] | None = None,
) -> MultiCounts:
    """Who chose each option, as counts and as a share of the respondents.

    ``percent`` is of the base — the respondents who answered — so the column
    sums above 100 % when people chose more than one thing. ``percent_answers``
    is of the answers given, which is the other number people ask for; both are
    here so neither has to be recomputed by hand from the wrong denominator.
    """

    if column not in df.columns:
        raise KeyError(f"column not found: {column!r}")
    series = df[column]
    weights = df[weight] if weight is not None else None
    if weight is not None and weight not in df.columns:
        raise KeyError(f"column not found: {weight!r}")
    base = base_size(series, weight=weights)
    wanted = list(codes) if codes is not None else codes_in(series)
    rows = []
    for code in wanted:
        chosen = reach(series, code) & responded(series)
        count = float(weights[chosen].sum()) if weights is not None else float(chosen.sum())
        rows.append(
            {
                "value": code,
                "label": (labels or {}).get(code, str(code)),
                "count": int(round(count)),
                "percent": round(count / base * 100, 1) if base else 0.0,
            }
        )
    answers = float(sum(row["count"] for row in rows))
    for row in rows:
        row["percent_answers"] = round(row["count"] / answers * 100, 1) if answers else 0.0
    out = MultiCounts(rows, columns=["value", "label", "count", "percent", "percent_answers"])
    out.base = int(round(base))
    out.answers = int(round(answers))
    return out


def crosstab(
    df: pd.DataFrame,
    column: str,
    by: str,
    *,
    weight: str | None = None,
    codes: Sequence[Hashable] | None = None,
    labels: Mapping[Any, str] | None = None,
) -> MultiCounts:
    """Each option's reach within each group of ``by``.

    Percentages are of the group's own base — the respondents in that column who
    answered the question — because that is the number a reader compares across
    columns. `base` carries the per-group bases so the table can print them.
    """

    for name in (column, by):
        if name not in df.columns:
            raise KeyError(f"column not found: {name!r}")
    series = df[column]
    weights = df[weight] if weight is not None else None
    answered = responded(series)
    wanted = list(codes) if codes is not None else codes_in(series)
    groups = list(df[by].dropna().unique())
    with contextlib.suppress(TypeError):  # mixed types: keep the order seen
        groups = sorted(groups)

    bases: dict[Any, int] = {}
    for group in groups:
        in_group = (df[by] == group) & answered
        total = float(weights[in_group].sum()) if weights is not None else float(in_group.sum())
        bases[group] = int(round(total))

    rows = []
    for code in wanted:
        row: dict[str, Any] = {"value": code, "label": (labels or {}).get(code, str(code))}
        chosen = reach(series, code) & answered
        for group in groups:
            in_group = chosen & (df[by] == group)
            count = float(weights[in_group].sum()) if weights is not None else float(in_group.sum())
            row[str(group)] = round(count / bases[group] * 100, 1) if bases[group] else 0.0
        rows.append(row)
    out = MultiCounts(rows, columns=["value", "label", *(str(g) for g in groups)])
    out.base = bases
    out.answers = int(round(sum(bases.values())))
    return out
