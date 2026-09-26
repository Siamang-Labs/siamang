"""Confidence intervals of a mean and of a share — what a chart's error bars show.

The tables print a mean with its SD and N; a chart of them draws each mean with
the interval a reader can compare by eye. Three forms, each the textbook one:

    **An unweighted mean** takes Student's t interval, mean ± t(n − 1) · SD / √n
    — R's ``t.test(x)$conf.int``, SPSS's Explore.

    **A weighted mean** takes the linearization (Taylor series) standard error
    of a ratio mean under with-replacement sampling of the respondents,
    SE² = n / (n − 1) · Σ wᵢ² (yᵢ − ȳ)² / (Σ wᵢ)² — what R's
    ``survey::svymean`` reports for ``svydesign(ids = ~1, weights = ~w)`` —
    with t(n − 1) as ``confint(…, df = degf(design))`` has it. An answer
    weighted 0 (a missing weight counts 0) takes no part: n is the answers
    that carry weight, as in the weighted SD of the tables. Equal weights give
    exactly the unweighted interval.

    **A share** takes Wilson's score interval — R's
    ``prop.test(x, n, correct = FALSE)$conf.int`` — which stays inside 0–1
    and does not collapse to a point at 0 % or 100 %.

When there is no interval to give — no answers, one answer, nothing weighted —
:class:`Interval` carries the estimate (when there is one) and a sentence
saying why, and a chart draws the point without whiskers and says so.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

__all__ = ["Interval", "mean_interval", "proportion_interval", "t_interval"]


@dataclass(frozen=True, slots=True)
class Interval:
    """An estimate and its confidence interval.

    ``lower`` and ``upper`` are None when there is no interval, and ``note``
    then says why; ``n`` is the answers the interval rests on (for a weighted
    mean, those that carry weight).
    """

    estimate: float
    lower: float | None
    upper: float | None
    n: int
    confidence: float
    method: str
    se: float | None = None
    note: str | None = None

    @property
    def defined(self) -> bool:
        return self.lower is not None and self.upper is not None


def _check(confidence: float) -> None:
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1.")


def _t(confidence: float, df: float) -> float:
    from scipy.stats import t as t_dist

    return float(t_dist.ppf((1 + confidence) / 2, df))


def t_interval(mean: Any, sd: Any, n: Any, *, confidence: float = 0.95) -> Interval:
    """Student's interval from a table's numbers: mean ± t(n − 1) · SD / √n.

    What a chart of a t-test's or a paired test's descriptives draws: those
    tables are unweighted, and their mean, SD and N are all it needs.
    """

    _check(confidence)
    method = "Student's t"
    count = 0 if n is None or n != n else int(n)
    if mean is None or mean != mean:
        return Interval(float("nan"), None, None, count, confidence, method, note="no answers")
    mean = float(mean)
    if count < 2 or sd is None or sd != sd:
        return Interval(mean, None, None, count, confidence, method, note=_one(count))
    se = float(sd) / math.sqrt(count)
    half = _t(confidence, count - 1) * se
    return Interval(mean, mean - half, mean + half, count, confidence, method, se=se)


def mean_interval(values: Any, weights: Any = None, *, confidence: float = 0.95) -> Interval:
    """The mean of ``values`` with its confidence interval, weighted by ``weights``.

    Missing values are left out, with their weights. See the module for the
    formulas; equal weights give exactly the unweighted interval.
    """

    _check(confidence)
    array = np.asarray(values, dtype=float)
    keep = ~np.isnan(array)
    if weights is None:
        array = array[keep]
        n = int(array.size)
        method = "Student's t"
        if n == 0:
            return Interval(float("nan"), None, None, 0, confidence, method, note="no answers")
        mean = float(array.mean())
        if n < 2:
            return Interval(mean, None, None, n, confidence, method, note=_one(n))
        se = float(array.std(ddof=1)) / math.sqrt(n)
    else:
        w = np.nan_to_num(np.asarray(weights, dtype=float), nan=0.0)
        if w.shape != array.shape:
            raise ValueError("values and weights must have the same length.")
        if np.any(w < 0):
            raise ValueError("weights must not be negative.")
        carried = keep & (w > 0)
        array, w = array[carried], w[carried]
        n = int(array.size)
        method = "linearization (Taylor series), weighted"
        if n == 0:
            note = "no answers" if not keep.any() else "no answer carries weight"
            return Interval(float("nan"), None, None, 0, confidence, method, note=note)
        total = float(w.sum())
        mean = float((w * array).sum() / total)
        if n < 2:
            return Interval(mean, None, None, n, confidence, method, note=_one(n))
        residual = w * (array - mean)
        se = math.sqrt(n / (n - 1) * float((residual**2).sum())) / total
    half = _t(confidence, n - 1) * se
    return Interval(mean, mean - half, mean + half, n, confidence, method, se=se)


def proportion_interval(successes: Any, n: Any, *, confidence: float = 0.95) -> Interval:
    """The share ``successes / n`` with Wilson's score interval (both as 0–1)."""

    _check(confidence)
    method = "Wilson score"
    total = 0 if n is None or n != n else int(n)
    if total <= 0:
        return Interval(float("nan"), None, None, 0, confidence, method, note="no answers")
    hits = float(successes)
    if hits < 0 or hits > total:
        raise ValueError("successes must be between 0 and n.")
    from scipy.stats import norm

    p = hits / total
    z = float(norm.ppf((1 + confidence) / 2))
    denominator = 1 + z**2 / total
    centre = (p + z**2 / (2 * total)) / denominator
    half = z * math.sqrt(p * (1 - p) / total + z**2 / (4 * total**2)) / denominator
    # At 0 % and 100 % one end is the share itself, not a rounding away from it.
    return Interval(
        p,
        0.0 if hits == 0 else max(0.0, centre - half),
        1.0 if hits == total else min(1.0, centre + half),
        total,
        confidence,
        method,
        se=math.sqrt(p * (1 - p) / total),
    )


def _one(n: int) -> str:
    return "no answers" if n == 0 else "one answer has no interval"
