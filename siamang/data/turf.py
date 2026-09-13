"""TURF: how many different people a shortlist of options reaches together.

The question a frequency table cannot answer. "Which three flavors should we
stock?" is not "the three most popular flavors": the top three often appeal to
the same people, and a slightly less popular fourth may be the only one some
respondents chose at all. TURF — Total Unduplicated Reach and Frequency —
counts the people a *combination* reaches, each person once however many of the
options they named.

Three things are said out loud here because they are what makes such a table
trustworthy:

    **Reach is respondents.** A portfolio reaches somebody who chose at least
    one of its items. Nobody is counted twice, which is the whole point of the
    "unduplicated" in the name.

    **The base is the respondents who answered**, not everyone in the file. A
    reach of 60 % means 60 % of the people who answered the question; every
    result here carries that base so it cannot be quoted without it.

    **The search is named.** ``best`` examines every combination and is the
    real answer; ``greedy`` adds the item with the largest gain at each step,
    which is fast and can miss the best portfolio outright. Tools that call
    both "TURF" without saying which they ran are the reason TURF has a
    reputation for producing numbers nobody can reproduce.

Input is one 0/1 column per option — what :func:`siamang.data.multi.explode`
and the ``prepare.explode`` node produce from a multiple-choice question.
"""

from __future__ import annotations

from collections.abc import Sequence
from itertools import combinations

import pandas as pd

__all__ = ["TurfTable", "item_reach", "portfolio_reach", "turf"]

#: Refuse an exhaustive search bigger than this rather than appearing to hang.
_MAX_COMBINATIONS = 200_000


def _chosen(frame: pd.DataFrame, items: Sequence[str]) -> pd.DataFrame:
    missing = [name for name in items if name not in frame.columns]
    if missing:
        raise KeyError(f"columns not found: {', '.join(map(repr, missing))}")
    numeric = frame[list(items)].apply(pd.to_numeric, errors="coerce")
    if numeric.isna().all().all() and len(items):
        raise TypeError(
            "TURF needs one 0/1 column per option. These columns hold no numbers "
            "— a multiple-choice column of code lists is not one of them. Run "
            "prepare.explode first."
        )
    return numeric


def _base_mask(chosen: pd.DataFrame) -> pd.Series:
    """Who answered the question: anybody with a value in any of the items.

    After ``explode`` a respondent who never saw the question is missing in
    every indicator, and a respondent who chose nothing is missing too — both
    are "no answer" and neither belongs in the denominator.
    """

    return chosen.notna().any(axis=1)


def _weights(frame: pd.DataFrame, weight: str | None) -> pd.Series | None:
    if weight is None:
        return None
    if weight not in frame.columns:
        raise KeyError(f"column not found: {weight!r}")
    return pd.to_numeric(frame[weight], errors="coerce").fillna(0.0)


def _total(mask: pd.Series, weights: pd.Series | None) -> float:
    return float(weights[mask].sum()) if weights is not None else float(mask.sum())


def item_reach(
    frame: pd.DataFrame, items: Sequence[str], *, weight: str | None = None
) -> pd.Series:
    """Each item's own reach, as a share of the respondents who answered."""

    chosen = _chosen(frame, items)
    base_mask = _base_mask(chosen)
    weights = _weights(frame, weight)
    base = _total(base_mask, weights)
    reached = {
        name: _total((chosen[name] > 0) & base_mask, weights) / base if base else 0.0
        for name in items
    }
    return pd.Series(reached, dtype=float)


def portfolio_reach(
    frame: pd.DataFrame, items: Sequence[str], *, weight: str | None = None
) -> float:
    """The share of respondents who chose at least one of ``items``."""

    chosen = _chosen(frame, items)
    base_mask = _base_mask(chosen)
    weights = _weights(frame, weight)
    base = _total(base_mask, weights)
    if not base:
        return 0.0
    hit = (chosen > 0).any(axis=1) & base_mask
    return _total(hit, weights) / base


class TurfTable(pd.DataFrame):
    """A TURF table that carries its base and which search produced it.

    A subclass rather than a tuple so it still prints, plots and exports as a
    frame, while `base` and `method` travel with it — a reach percentage
    without its denominator, or without knowing whether the portfolio is the
    best one or merely a good one, is not a finding.
    """

    _metadata = ["base", "method"]

    @property
    def _constructor(self) -> type[TurfTable]:
        return TurfTable


def turf(
    frame: pd.DataFrame,
    items: Sequence[str],
    *,
    max_size: int = 3,
    method: str = "best",
    weight: str | None = None,
    include: Sequence[str] | None = None,
) -> TurfTable:
    """The best portfolio of each size from 1 to ``max_size``.

    ``method="best"`` tries every combination; ``method="greedy"`` extends the
    previous portfolio with whichever item adds most, which is what most tools
    do and can miss the best answer. ``include`` fixes items that are in the
    portfolio whatever they add — the shelf space already committed.

    Columns: the portfolio's ``items``, its ``reach`` and ``reach_percent``,
    the ``incremental`` gain over the row above, and ``frequency`` — the mean
    number of the portfolio's items a reached respondent chose, the F in TURF
    that most tables quietly drop.
    """

    if method not in {"best", "greedy"}:
        raise ValueError("method must be 'best' or 'greedy'.")
    if max_size < 1:
        raise ValueError("max_size must be at least 1.")
    items = list(dict.fromkeys(items))
    if not items:
        raise ValueError("turf needs at least one item.")
    fixed = list(include or [])
    unknown = [name for name in fixed if name not in items]
    if unknown:
        raise ValueError(f"include names items that are not in the list: {', '.join(unknown)}")

    chosen = _chosen(frame, items)
    base_mask = _base_mask(chosen)
    weights = _weights(frame, weight)
    base = _total(base_mask, weights)
    hits = {name: (chosen[name] > 0) & base_mask for name in items}
    max_size = min(max_size, len(items))

    if method == "best":
        free = [name for name in items if name not in fixed]
        total = sum(
            _n_choose_k(len(free), size - len(fixed))
            for size in range(max(1, len(fixed)), max_size + 1)
            if size >= len(fixed)
        )
        if total > _MAX_COMBINATIONS:
            raise ValueError(
                f"An exhaustive search over {len(items)} items up to size {max_size} "
                f"is {total:,} combinations. Lower max_size, shorten the item list, "
                "or pass method='greedy' — and say in the report which was used."
            )

    rows: list[dict[str, object]] = []
    previous = 0.0
    best_so_far: list[str] = list(fixed)
    for size in range(max(1, len(fixed)), max_size + 1):
        if method == "best":
            free = [name for name in items if name not in fixed]
            candidates = ([*fixed, *extra] for extra in combinations(free, size - len(fixed)))
        else:
            remaining = [name for name in items if name not in best_so_far]
            candidates = ([*best_so_far, name] for name in remaining)
        winner, reached = _best(candidates, hits, weights)
        if winner is None:
            break
        best_so_far = winner
        chosen_count = chosen[winner].fillna(0).gt(0).sum(axis=1)
        hit_mask = chosen_count.gt(0) & base_mask
        rows.append(
            {
                "size": size,
                "items": ", ".join(winner),
                "reach": round(reached, 4),
                "reach_percent": round(reached / base * 100, 1) if base else 0.0,
                "incremental": round(reached - previous, 4),
                "incremental_percent": round((reached - previous) / base * 100, 1) if base else 0.0,
                "frequency": round(float(chosen_count[hit_mask].mean()), 2)
                if hit_mask.any()
                else 0.0,
            }
        )
        previous = reached

    out = TurfTable(
        rows,
        columns=[
            "size",
            "items",
            "reach",
            "reach_percent",
            "incremental",
            "incremental_percent",
            "frequency",
        ],
    )
    out.base = int(round(base))
    out.method = method
    return out


def _best(
    candidates, hits: dict[str, pd.Series], weights: pd.Series | None
) -> tuple[list[str] | None, float]:
    """The candidate portfolio with the largest reach; ties go to the first seen.

    Deterministic on purpose: two portfolios reaching the same people is common
    with overlapping options, and a table that reorders between runs cannot be
    checked against the one in the report.
    """

    winner: list[str] | None = None
    best = -1.0
    for candidate in candidates:
        mask = hits[candidate[0]].copy()
        for name in candidate[1:]:
            mask |= hits[name]
        reached = float(weights[mask].sum()) if weights is not None else float(mask.sum())
        if reached > best:
            winner, best = list(candidate), reached
    return winner, max(best, 0.0)


def _n_choose_k(n: int, k: int) -> int:
    from math import comb

    return comb(n, k) if 0 <= k <= n else 0
