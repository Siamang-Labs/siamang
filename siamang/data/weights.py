"""Post-stratification weights: cell weighting and raking.

Both functions return a weight :class:`pandas.Series` aligned with the frame's
index and scaled to mean 1.0 (so the weighted N equals the number of rows).
Store it as a column and tell ``SurveyData`` about it::

    frame = data.frame.assign(weight=weights.rake_weights(data.frame, targets))
    weighted = data.with_frame(frame).with_weight("weight")

Targets are given per category as proportions or counts; they are normalized
to proportions, so ``{1: 45, 2: 30, 3: 25}`` and ``{1: 0.45, 2: 0.30, 3: 0.25}``
mean the same thing. Categories absent from the targets keep their current
share.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np
import pandas as pd


def _target_proportions(targets: Mapping[Any, float]) -> dict[Any, float]:
    if not targets:
        raise ValueError("targets must not be empty.")
    if any(float(value) < 0 for value in targets.values()):
        raise ValueError("targets must be non-negative proportions or counts.")
    total = float(sum(targets.values())) or 1.0
    return {category: float(value) / total for category, value in targets.items()}


def _normalize(weights: pd.Series, cap: float | None) -> pd.Series:
    mean = float(weights.mean()) or 1.0
    weights = weights / mean
    if cap is not None:
        if cap <= 1:
            raise ValueError("cap must be greater than 1 (it bounds weights of mean 1).")
        # Clipping lowers the mean and rescaling lifts the clipped rows above
        # the cap again; alternating the two converges in a few passes.
        for _ in range(20):
            if float(weights.max()) <= float(cap) + 1e-9:
                break
            weights = weights.clip(upper=float(cap))
            mean = float(weights.mean()) or 1.0
            weights = weights / mean
        weights = weights.clip(upper=float(cap))
    return weights


def cell_weights(
    df: pd.DataFrame,
    column: str,
    targets: Mapping[Any, float],
    *,
    cap: float | None = None,
) -> pd.Series:
    """Single-variable post-stratification weights.

    After weighting, the distribution of ``column`` matches ``targets``.
    Categories absent from ``targets`` keep a weight of 1.0 before scaling.
    ``cap`` bounds the weights (of mean 1) from above; the capped rows are
    then under-represented, so the match to the targets is approximate.
    """

    if column not in df.columns:
        raise KeyError(f"column not found: {column!r}")
    props = _target_proportions(targets)
    observed = df[column].value_counts(normalize=True)
    factors = {
        category: (share / observed[category]) if observed.get(category, 0) else 0.0
        for category, share in props.items()
    }
    weights = df[column].map(lambda category: factors.get(category, 1.0)).astype(float)
    return _normalize(weights, cap)


def rake_weights(
    df: pd.DataFrame,
    targets: Mapping[str, Mapping[Any, float]],
    *,
    max_iter: int = 50,
    tol: float = 1e-6,
    cap: float | None = None,
) -> pd.Series:
    """Iterative proportional fitting (raking) to several marginal distributions.

    ``targets`` maps each margin column to its target distribution. The
    weights are adjusted margin by margin until the largest single-step
    change drops below ``tol`` or ``max_iter`` passes have run. Categories
    missing from a margin's targets are left unadjusted on that pass; rows
    whose category has no target on any margin keep a weight of 1.0 before
    scaling. ``cap`` behaves as in :func:`cell_weights`.
    """

    if not targets:
        raise ValueError("targets must name at least one margin.")
    for column in targets:
        if column not in df.columns:
            raise KeyError(f"column not found: {column!r}")
    n = len(df)
    weights = pd.Series(np.ones(n), index=df.index, dtype=float)
    norm = {column: _target_proportions(margin) for column, margin in targets.items()}
    for _ in range(max_iter):
        max_change = 0.0
        for column, props in norm.items():
            weighted = weights.groupby(df[column]).sum()
            total = float(weighted.sum()) or 1.0
            for category, target_share in props.items():
                current = float(weighted.get(category, 0.0))
                if current <= 0:
                    continue
                factor = (target_share * total) / current
                max_change = max(max_change, abs(factor - 1.0))
                weights.loc[df[column] == category] *= factor
        if max_change < tol:
            break
    return _normalize(weights, cap)


def effective_sample_size(weights: pd.Series) -> float:
    """Kish's effective sample size, ``(Σw)² / Σw²``, of a weight series."""

    values = pd.to_numeric(weights, errors="coerce").dropna().astype(float)
    sum_w = float(values.sum())
    sum_w2 = float((values**2).sum())
    if sum_w <= 0 or sum_w2 <= 0:
        return 0.0
    return (sum_w**2) / sum_w2


__all__ = ["cell_weights", "effective_sample_size", "rake_weights"]
