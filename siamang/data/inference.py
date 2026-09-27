"""Significance tests, post-hoc comparisons and correlations — numpy and SciPy only.

What the tables and flow nodes offer beyond their default tests: Pearson,
Spearman and Kendall correlations and a matrix of them, the three t-tests,
Student's and Welch's comparisons of two groups, one-way and Welch's ANOVA,
Tukey's HSD, Games-Howell and Dunn's test after a comparison of several groups,
Fisher's exact test, and the adjustments of p-values for multiple comparisons.

The functions take plain arrays and return plain numbers, so a result is the
same whoever asks for it. When the data cannot carry a test — one respondent in
a group, no variance anywhere — they raise :class:`NotTestable` with a sentence
saying why, and the tables print that sentence where the number would have
been. A wrong argument (an unknown method) is a ``ValueError`` as usual.

Missing codes: :func:`without_missing_codes` turns the codebook's declared
missing codes (a "Don't know" coded 99) into missing values and counts what it
left out, so a mean or a correlation never reads 99 as an answer. Every result
built on these tests uses it and says what it left out.
"""

from __future__ import annotations

import functools
import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from siamang.core.variable import VariableMap


class NotTestable(ValueError):
    """The data cannot carry the test; the message says why, for the reader."""


#: Values whose range is at most this share of their size differ by
#: floating-point rounding alone. Three answers of 1.4 have a variance of 7e-32,
#: not 0 (their mean is 1.4000000000000001), and 1.1 − 1.0 and 4.1 − 4.0 differ
#: by 4e-16; read as spread, that noise gave t-values of 10^15.
SPREAD_TOLERANCE = 1e-12


def no_spread(values: Any, *, scale: float | None = None) -> bool:
    """Whether ``values`` are all the same but for floating-point rounding.

    They are when their range is at most :data:`SPREAD_TOLERANCE` times
    ``scale`` — by default the largest of them in absolute value. For
    differences, pass the size of the numbers they were taken from: the
    rounding of 4.1 − 4.0 is a share of 4.1, not of 0.1.
    """

    array = np.asarray(values, dtype=float)
    if array.size == 0:
        return True
    size = float(np.abs(array).max()) if scale is None else float(scale)
    return float(np.ptp(array)) <= SPREAD_TOLERANCE * size


def _variance(values: np.ndarray) -> float:
    """The sample variance (n − 1): exactly 0 for values with no spread."""

    return 0.0 if no_spread(values) else float(values.var(ddof=1))


# ─── multiple comparisons ────────────────────────────────────────────────────

ADJUSTMENTS = ("none", "holm", "bonferroni", "fdr_bh")
ADJUSTMENT_NAMES = {
    "none": "none",
    "holm": "Holm",
    "bonferroni": "Bonferroni",
    "fdr_bh": "Benjamini-Hochberg",
}


def adjust_p(pvalues: Sequence[float] | np.ndarray, method: str = "holm") -> np.ndarray:
    """p-values adjusted for the number of comparisons, as R's ``p.adjust``.

    ``bonferroni`` multiplies by the number of tests m; ``holm`` multiplies the
    i-th smallest by m − i + 1 and keeps the order (step-down); ``fdr_bh``
    multiplies it by m / i and takes the running minimum from the largest
    (Benjamini-Hochberg). Adjusted values are capped at 1. A missing p (a pair
    that could not be tested) stays missing and does not count toward m.
    """

    if method not in ADJUSTMENTS:
        raise ValueError(f"adjust must be one of {', '.join(ADJUSTMENTS)}; got {method!r}.")
    p = np.asarray(pvalues, dtype=float)
    out = p.copy()
    present = ~np.isnan(p)
    m = int(present.sum())
    if method == "none" or m == 0:
        return out
    values = p[present]
    if method == "bonferroni":
        out[present] = np.minimum(1.0, values * m)
        return out
    order = np.argsort(values, kind="stable")
    ranked = values[order]
    if method == "holm":
        stepped = np.maximum.accumulate((m - np.arange(m)) * ranked)
    else:
        stepped = np.minimum.accumulate((m / np.arange(1, m + 1) * ranked)[::-1])[::-1]
    adjusted = np.empty(m)
    adjusted[order] = np.minimum(1.0, stepped)
    out[present] = adjusted
    return out


# ─── missing codes ───────────────────────────────────────────────────────────


def without_missing_codes(
    frame: pd.DataFrame, columns: Sequence[str], variables: VariableMap | None
) -> tuple[pd.DataFrame, dict[str, list[tuple[Any, int]]]]:
    """``frame`` with the declared missing codes of ``columns`` set missing.

    Returns the new frame (a copy; other columns untouched) and, per column,
    the codes found and how often — the input to :func:`missing_codes_note`.
    A multiple-choice column (lists of codes) is left as it is.
    """

    from siamang.data import multi

    cleaned = frame.copy()
    left_out: dict[str, list[tuple[Any, int]]] = {}
    for column in dict.fromkeys(columns):
        if variables is None or column not in variables or column not in frame.columns:
            continue
        codes = variables[column].missing_values
        series = frame[column]
        if not codes or multi.is_multi(series):
            continue
        mask = pd.Series(False, index=series.index)
        found: list[tuple[Any, int]] = []
        for code in codes:
            hit = (series == code).fillna(False).astype(bool)
            if hit.any():
                found.append((code, int(hit.sum())))
                mask |= hit
        if found:
            cleaned[column] = series.mask(mask)
            left_out[column] = found
    return cleaned, left_out


def missing_codes_note(
    left_out: dict[str, list[tuple[Any, int]]], variables: VariableMap | None
) -> str | None:
    """``"Satisfaction: 12 (99 = Don't know)"`` for what was left out, or None."""

    parts = []
    for column, found in left_out.items():
        variable = variables[column] if variables is not None and column in variables else None
        name = (variable.label if variable is not None else None) or column
        labels = variable.missing_labels if variable is not None else {}
        codes = ", ".join(
            f"{code} = {labels[code]}" if labels.get(code) else str(code) for code, _ in found
        )
        parts.append(f"{name}: {sum(count for _, count in found)} ({codes})")
    return "; ".join(parts) or None


def missing_codes_counted(
    frame: pd.DataFrame, columns: Sequence[str], variables: VariableMap | None
) -> str | None:
    """What a result that reads the declared missing codes as answers says.

    The defaults that predate this module — the automatic test of Group means,
    Crosstab's chi-square, ``kruskal``, ``mannwhitney`` and ``spearman`` —
    keep reading a 9 "Refused" as an answer, so that a stored flow keeps its
    numbers. Where ``frame`` holds such codes in ``columns`` they say so with
    this sentence (``"Trust: Acme: 38 (9 = Refused); run Missing values first
    to leave them out"``), which explains why a test chosen by hand on the same
    data gives another result. None when there are none.
    """

    note = missing_codes_note(without_missing_codes(frame, columns, variables)[1], variables)
    return f"{note}; run Missing values first to leave them out" if note else None


# ─── correlation ─────────────────────────────────────────────────────────────

CORRELATIONS = ("pearson", "spearman", "kendall")
CORRELATION_NAMES = {"pearson": "Pearson", "spearman": "Spearman", "kendall": "Kendall tau-b"}
#: The coefficient's usual symbol, and its key in a result.
CORRELATION_SYMBOLS = {"pearson": "r", "spearman": "rho", "kendall": "tau"}


def _weights(weights: Any, keep: np.ndarray) -> np.ndarray:
    """The weights of the kept rows; a missing weight weighs 0, a negative one is refused."""

    values = pd.to_numeric(pd.Series(np.asarray(weights)), errors="coerce").fillna(0.0)
    values = values.to_numpy(dtype=float)[keep]
    if np.any(values < 0):
        raise ValueError("The weight column has negative values.")
    return values


def correlate(
    x: Any,
    y: Any,
    *,
    method: str = "pearson",
    weights: Any = None,
    confidence: float = 0.95,
) -> dict[str, Any]:
    """The correlation of ``x`` and ``y`` over their complete pairs.

    Returns ``method``, the coefficient under its symbol (``r``, ``rho`` or
    ``tau``), ``p_value`` (two-sided) and ``n``, the pairs used. Pearson also
    gives a ``confidence`` interval, ``lower`` – ``upper``, by Fisher's z
    transformation. With ``weights`` (Pearson only — the rank correlations
    have no standard weighted form) the coefficient is the weighted one and its
    p-value and interval are taken on Kish's effective base, ``n_effective``,
    so weighting never makes a correlation look more certain than the
    respondents behind it; equal weights give the unweighted result. Kendall's
    is tau-b, which corrects for ties.
    """

    if method not in CORRELATIONS:
        raise ValueError(f"method must be one of {', '.join(CORRELATIONS)}; got {method!r}.")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1.")
    xs = pd.to_numeric(pd.Series(np.asarray(x)), errors="coerce").to_numpy(dtype=float)
    ys = pd.to_numeric(pd.Series(np.asarray(y)), errors="coerce").to_numpy(dtype=float)
    keep = ~(np.isnan(xs) | np.isnan(ys))
    xs, ys = xs[keep], ys[keep]
    n = int(len(xs))
    if n < 3:
        raise NotTestable(f"a correlation needs at least three complete pairs; there are {n}")
    if no_spread(xs) or no_spread(ys):
        raise NotTestable(
            "a variable has the same value for everyone, so it correlates with nothing"
        )

    from scipy import stats

    symbol = CORRELATION_SYMBOLS[method]
    result: dict[str, Any] = {"method": CORRELATION_NAMES[method]}
    if method == "spearman":
        found = stats.spearmanr(xs, ys)
        result.update({symbol: float(found.statistic), "p_value": float(found.pvalue), "n": n})
        return result
    if method == "kendall":
        found = stats.kendalltau(xs, ys)
        result.update({symbol: float(found.statistic), "p_value": float(found.pvalue), "n": n})
        return result

    if weights is None:
        found = stats.pearsonr(xs, ys)
        r, p_value, base = float(found.statistic), float(found.pvalue), float(n)
    else:
        w = _weights(weights, keep)
        total = float(w.sum())
        if total <= 0:
            raise NotTestable("the weights of the complete pairs sum to zero")
        weighed = w > 0
        if no_spread(xs[weighed]) or no_spread(ys[weighed]):
            raise NotTestable("a variable has the same value for all the weight")
        share = w / total
        dx, dy = xs - share @ xs, ys - share @ ys
        sxx, syy = float(share @ (dx * dx)), float(share @ (dy * dy))
        r = float(np.clip(share @ (dx * dy) / math.sqrt(sxx * syy), -1.0, 1.0))
        base = total**2 / float((w * w).sum())
        p_value = _p_of_r(r, base)
    result.update({symbol: r, "p_value": p_value, "n": n})
    if weights is not None:
        result["n_effective"] = base
    lower, upper = _fisher_interval(r, base, confidence)
    result.update({"lower": lower, "upper": upper, "confidence": confidence})
    return result


def _p_of_r(r: float, base: float) -> float | None:
    """Two-sided p of a Pearson r on ``base`` pairs: t = r √((n − 2) / (1 − r²))."""

    from scipy.stats import t as t_dist

    df = base - 2
    if df <= 0:
        return None
    if abs(r) >= 1:
        return 0.0
    t = r * math.sqrt(df / (1 - r * r))
    return float(2 * t_dist.sf(abs(t), df))


def _fisher_interval(r: float, base: float, confidence: float) -> tuple[float | None, float | None]:
    """Fisher's z interval: tanh(atanh r ± z / √(n − 3)); none below four pairs."""

    from scipy.stats import norm

    if base <= 3:
        return None, None
    if abs(r) >= 1:
        return r, r
    z = math.atanh(r)
    half = float(norm.ppf((1 + confidence) / 2)) / math.sqrt(base - 3)
    return math.tanh(z - half), math.tanh(z + half)


@dataclass(frozen=True, slots=True)
class CorrelationMatrix:
    """Every pair of ``columns``: coefficient, p (raw and adjusted) and N, as
    square frames indexed by column name. ``notes`` names each pair that could
    not be computed, and why."""

    method: str
    columns: list[str]
    coefficients: pd.DataFrame
    p_values: pd.DataFrame
    p_adjusted: pd.DataFrame
    n: pd.DataFrame
    missing: str
    adjust: str
    weighted: bool = False
    notes: list[str] = field(default_factory=list)

    def pairs(self) -> pd.DataFrame:
        """One row per pair (upper triangle): x, y, coefficient, p, p_adjusted, n."""

        rows = []
        for i, a in enumerate(self.columns):
            for b in self.columns[i + 1 :]:
                rows.append(
                    {
                        "x": a,
                        "y": b,
                        "coefficient": self.coefficients.loc[a, b],
                        "p_value": self.p_values.loc[a, b],
                        "p_adjusted": self.p_adjusted.loc[a, b],
                        "n": int(self.n.loc[a, b]),
                    }
                )
        return pd.DataFrame(rows, columns=["x", "y", "coefficient", "p_value", "p_adjusted", "n"])


def correlation_matrix(
    frame: pd.DataFrame,
    columns: Sequence[str],
    *,
    method: str = "spearman",
    missing: str = "pairwise",
    adjust: str = "none",
    weights: Any = None,
) -> CorrelationMatrix:
    """Correlations between every pair of ``columns``.

    ``missing="pairwise"`` uses, for each pair, every respondent who answered
    both — so N can differ from pair to pair; ``"listwise"`` first keeps only
    the respondents who answered all of them. ``adjust`` corrects the p-values
    for the number of pairs (:func:`adjust_p`). ``weights`` weights Pearson's
    coefficient as :func:`correlate` does and is ignored by the rank methods.
    """

    columns = list(dict.fromkeys(columns))
    if len(columns) < 2:
        raise ValueError("A correlation matrix needs at least two variables.")
    if missing not in ("pairwise", "listwise"):
        raise ValueError("missing must be 'pairwise' or 'listwise'.")
    if adjust not in ADJUSTMENTS:
        raise ValueError(f"adjust must be one of {', '.join(ADJUSTMENTS)}; got {adjust!r}.")
    if method not in CORRELATIONS:
        raise ValueError(f"method must be one of {', '.join(CORRELATIONS)}; got {method!r}.")
    data = frame[columns].apply(pd.to_numeric, errors="coerce")
    w = None
    if weights is not None and method == "pearson":
        w = pd.Series(np.asarray(weights), index=frame.index)
    if missing == "listwise":
        data = data.dropna()
        w = w.loc[data.index] if w is not None else None

    k = len(columns)
    coefficient = np.full((k, k), np.nan)
    p_value = np.full((k, k), np.nan)
    counts = np.zeros((k, k), dtype=int)
    notes: list[str] = []
    symbol = CORRELATION_SYMBOLS[method]
    for i, a in enumerate(columns):
        counts[i, i] = int(data[a].notna().sum())
        coefficient[i, i] = 1.0
        for j in range(i + 1, k):
            b = columns[j]
            pair = data[[a, b]].dropna()
            counts[i, j] = counts[j, i] = len(pair)
            try:
                found = correlate(
                    pair[a],
                    pair[b],
                    method=method,
                    weights=w.loc[pair.index] if w is not None else None,
                )
            except NotTestable as exc:
                notes.append(f"{a} × {b}: {exc}")
                continue
            coefficient[i, j] = coefficient[j, i] = found[symbol]
            if found["p_value"] is not None:
                p_value[i, j] = p_value[j, i] = found["p_value"]

    upper = np.triu_indices(k, 1)
    adjusted = np.full((k, k), np.nan)
    adjusted[upper] = adjust_p(p_value[upper], adjust)
    adjusted.T[upper] = adjusted[upper]
    square = lambda values: pd.DataFrame(values, index=columns, columns=columns)  # noqa: E731
    return CorrelationMatrix(
        method=method,
        columns=columns,
        coefficients=square(coefficient),
        p_values=square(p_value),
        p_adjusted=square(adjusted),
        n=square(counts),
        missing=missing,
        adjust=adjust,
        weighted=w is not None,
        notes=notes,
    )


# ─── t-tests ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class TTest:
    """One t-test: the statistic, its degrees of freedom and two-sided p, the
    mean difference with its confidence interval, and Cohen's d (Hedges' g for
    two independent groups)."""

    kind: str  # independent | paired | one_sample
    method: str
    t: float
    df: float
    p_value: float
    difference: float
    lower: float
    upper: float
    confidence: float
    cohens_d: float | None
    hedges_g: float | None = None


def _clean(values: Any) -> np.ndarray:
    array = pd.to_numeric(pd.Series(np.asarray(values)), errors="coerce").to_numpy(dtype=float)
    return array[~np.isnan(array)]


def _t_result(
    kind: str,
    method: str,
    difference: float,
    se: float,
    df: float,
    confidence: float,
    d: float | None,
    g: float | None = None,
) -> TTest:
    from scipy.stats import t as t_dist

    t = difference / se
    half = float(t_dist.ppf((1 + confidence) / 2, df)) * se
    return TTest(
        kind=kind,
        method=method,
        t=float(t),
        df=float(df),
        p_value=float(2 * t_dist.sf(abs(t), df)),
        difference=float(difference),
        lower=float(difference - half),
        upper=float(difference + half),
        confidence=confidence,
        cohens_d=d,
        hedges_g=g,
    )


def ttest_independent(
    a: Any,
    b: Any,
    *,
    equal_var: bool = False,
    confidence: float = 0.95,
    names: tuple[str, str] = ("the first group", "the second group"),
) -> TTest:
    """Two independent groups: Welch's t-test, or Student's with ``equal_var``.

    The difference is mean(a) − mean(b). Welch's standard error is
    √(s₁²/n₁ + s₂²/n₂) on the Welch–Satterthwaite df; Student's pools the
    variances on n₁ + n₂ − 2. Cohen's d is the difference over the pooled SD
    either way, and Hedges' g is d × (1 − 3 / (4(n₁ + n₂) − 9)).
    """

    a, b = _clean(a), _clean(b)
    for values, name in ((a, names[0]), (b, names[1])):
        if len(values) < 2:
            raise NotTestable(
                f"a t-test needs at least two values in each group; {name} has {len(values)}"
            )
    n1, n2 = len(a), len(b)
    v1, v2 = _variance(a), _variance(b)
    difference = float(a.mean() - b.mean())
    pooled = ((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2)
    if equal_var:
        se, df = math.sqrt(pooled * (1 / n1 + 1 / n2)), float(n1 + n2 - 2)
        method = "Student's t-test (equal variances)"
    else:
        s1, s2 = v1 / n1, v2 / n2
        se = math.sqrt(s1 + s2)
        df = (s1 + s2) ** 2 / (s1**2 / (n1 - 1) + s2**2 / (n2 - 1)) if se > 0 else float("nan")
        method = "Welch's t-test (unequal variances)"
    if se <= 0:
        raise NotTestable(
            "neither group varies, so there is no spread to test the difference against"
        )
    d = difference / math.sqrt(pooled) if pooled > 0 else None
    g = d * (1 - 3 / (4 * (n1 + n2) - 9)) if d is not None else None
    return _t_result("independent", method, difference, se, df, confidence, d, g)


def ttest_paired(x: Any, y: Any, *, confidence: float = 0.95) -> TTest:
    """Two measurements of the same respondents: a one-sample test of x − y.

    Only complete pairs count. Cohen's d is d_z, the mean difference over the
    SD of the differences.
    """

    xs = pd.to_numeric(pd.Series(np.asarray(x)), errors="coerce").to_numpy(dtype=float)
    ys = pd.to_numeric(pd.Series(np.asarray(y)), errors="coerce").to_numpy(dtype=float)
    keep = ~(np.isnan(xs) | np.isnan(ys))
    diff = xs[keep] - ys[keep]
    n = len(diff)
    if n < 2:
        raise NotTestable(f"a paired t-test needs at least two complete pairs; there are {n}")
    size = float(max(np.abs(xs[keep]).max(), np.abs(ys[keep]).max()))
    if no_spread(diff, scale=size):
        raise NotTestable(
            "every respondent's two answers differ by the same amount, so there is no spread "
            "to test the difference against"
        )
    sd = float(diff.std(ddof=1))
    difference = float(diff.mean())
    return _t_result(
        "paired", "Paired t-test", difference, sd / math.sqrt(n), n - 1, confidence, difference / sd
    )


def ttest_one_sample(x: Any, mu: float = 0.0, *, confidence: float = 0.95) -> TTest:
    """The mean of ``x`` against ``mu``; the difference is mean − mu and
    Cohen's d is that difference over the SD."""

    xs = _clean(x)
    n = len(xs)
    if n < 2:
        raise NotTestable(f"a one-sample t-test needs at least two values; there are {n}")
    if no_spread(xs):
        raise NotTestable("every value is the same, so there is no spread to test the mean against")
    sd = float(xs.std(ddof=1))
    difference = float(xs.mean() - mu)
    return _t_result(
        "one_sample",
        "One-sample t-test",
        difference,
        sd / math.sqrt(n),
        n - 1,
        confidence,
        difference / sd,
    )


# ─── several groups ──────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class GroupTest:
    """A test of k groups: its name, statistic (``symbol``), degrees of freedom,
    two-sided p and a standard effect size."""

    method: str
    symbol: str
    statistic: float
    p_value: float
    df: float | None = None
    df2: float | None = None
    effect_name: str | None = None
    effect: float | None = None


def _samples(samples: Sequence[Any]) -> list[np.ndarray]:
    return [_clean(values) for values in samples]


def anova(samples: Sequence[Any]) -> GroupTest:
    """One-way ANOVA: F = (SS between / (k − 1)) / (SS within / (N − k)), with
    η² = SS between / SS total."""

    groups = [g for g in _samples(samples) if len(g)]
    k, total = len(groups), sum(len(g) for g in groups)
    if k < 2:
        raise NotTestable("an ANOVA needs at least two groups with values")
    if total - k < 1:
        raise NotTestable("an ANOVA needs more respondents than groups")
    grand = np.concatenate(groups).mean()
    between = float(sum(len(g) * (g.mean() - grand) ** 2 for g in groups))
    within = float(sum((len(g) - 1) * _variance(g) for g in groups if len(g) > 1))
    if within <= 0:
        raise NotTestable("no group varies, so there is no spread to test the means against")
    from scipy.stats import f as f_dist

    df1, df2 = k - 1, total - k
    f = (between / df1) / (within / df2)
    return GroupTest(
        "One-way ANOVA",
        "F",
        float(f),
        float(f_dist.sf(f, df1, df2)),
        float(df1),
        float(df2),
        "η²",
        between / (between + within),
    )


def welch_anova(samples: Sequence[Any], names: Sequence[str] | None = None) -> GroupTest:
    """Welch's ANOVA, which does not assume equal variances (Welch 1951).

    With wᵢ = nᵢ / sᵢ² and m* = Σwᵢmᵢ / Σwᵢ: F = [Σwᵢ(mᵢ − m*)² / (k − 1)] /
    [1 + 2(k − 2)Λ / 3], Λ = 3Σ[(1 − wᵢ/Σw)² / (nᵢ − 1)] / (k² − 1), on k − 1
    and 1/Λ degrees of freedom. η² is the ordinary SS between / SS total.
    """

    groups = _samples(samples)
    names = list(names or [f"group {i + 1}" for i in range(len(groups))])
    for values, name in zip(groups, names, strict=True):
        if len(values) < 2:
            raise NotTestable(
                f"Welch's ANOVA needs at least two values in every group; {name} has {len(values)}"
            )
        if no_spread(values):
            raise NotTestable(
                f"Welch's ANOVA weighs each group by its variance, and every value in {name} "
                "is the same"
            )
    k = len(groups)
    if k < 2:
        raise NotTestable("an ANOVA needs at least two groups with values")
    n = np.array([len(g) for g in groups], dtype=float)
    means = np.array([g.mean() for g in groups])
    variances = np.array([g.var(ddof=1) for g in groups])
    w = n / variances
    centre = float((w * means).sum() / w.sum())
    lam = 3 * float(((1 - w / w.sum()) ** 2 / (n - 1)).sum()) / (k**2 - 1)
    f = (float((w * (means - centre) ** 2).sum()) / (k - 1)) / (1 + 2 * lam * (k - 2) / 3)
    from scipy.stats import f as f_dist

    grand = np.concatenate(groups).mean()
    between = float((n * (means - grand) ** 2).sum())
    within = float(((n - 1) * variances).sum())
    return GroupTest(
        "Welch's ANOVA",
        "F",
        float(f),
        float(f_dist.sf(f, k - 1, 1 / lam)),
        float(k - 1),
        float(1 / lam),
        "η²",
        between / (between + within),
    )


def kruskal(samples: Sequence[Any]) -> GroupTest:
    """Kruskal-Wallis H (tie-corrected, as SciPy computes it) with ε² = H / (N − 1)."""

    groups = [g for g in _samples(samples) if len(g)]
    if len(groups) < 2:
        raise NotTestable("Kruskal-Wallis needs at least two groups with values")
    values = np.concatenate(groups)
    if np.ptp(values) == 0:
        raise NotTestable("every value is the same, so there is nothing to rank")
    from scipy import stats

    found = stats.kruskal(*groups)
    h = float(found.statistic)
    return GroupTest(
        "Kruskal-Wallis H",
        "H",
        h,
        float(found.pvalue),
        float(len(groups) - 1),
        effect_name="ε²",
        effect=h / (len(values) - 1),
    )


def mannwhitney(a: Any, b: Any) -> GroupTest:
    """Mann-Whitney U of the first group (two-sided, as SciPy chooses exact or
    asymptotic), with the rank-biserial correlation 2U / (n₁n₂) − 1 — positive
    when the first group tends to be higher."""

    a, b = _clean(a), _clean(b)
    if not len(a) or not len(b):
        raise NotTestable("Mann-Whitney needs values in both groups")
    from scipy import stats

    found = stats.mannwhitneyu(a, b, alternative="two-sided")
    u = float(found.statistic)
    return GroupTest(
        "Mann-Whitney U",
        "U",
        u,
        float(found.pvalue),
        effect_name="rank-biserial r",
        effect=2 * u / (len(a) * len(b)) - 1,
    )


# ─── post-hoc comparisons ────────────────────────────────────────────────────

POSTHOCS = ("tukey", "games_howell", "dunn")
POSTHOC_NAMES = {
    "tukey": "Tukey HSD",
    "games_howell": "Games-Howell",
    "dunn": "Dunn's test",
}
#: The test each post-hoc comparison follows.
POSTHOC_FOLLOWS = {"tukey": "anova", "games_howell": "welch_anova", "dunn": "kruskal"}


@dataclass(frozen=True, slots=True)
class PostHoc:
    """Every pair of groups after a test of several.

    ``table`` has one row per pair: ``group_1``, ``group_2``, ``difference``
    (of means; of mean ranks for Dunn), ``statistic`` (q, or z for Dunn),
    ``df`` (Games-Howell), ``p_value`` (Tukey and Games-Howell already hold
    the family-wise error at the level asked; for Dunn the unadjusted p),
    ``p_adjusted`` and, for Tukey and Games-Howell, the simultaneous interval
    ``lower`` – ``upper``.
    """

    method: str
    table: pd.DataFrame
    adjust: str = "none"
    confidence: float = 0.95
    notes: list[str] = field(default_factory=list)

    @property
    def name(self) -> str:
        if self.method == "dunn":
            return f"{POSTHOC_NAMES['dunn']} ({ADJUSTMENT_NAMES[self.adjust]})"
        return POSTHOC_NAMES[self.method]

    @property
    def symbol(self) -> str:
        return "z" if self.method == "dunn" else "q"

    def significant(self, alpha: float = 0.05) -> int:
        return int((self.table["p_adjusted"] < alpha).sum())


_POSTHOC_COLUMNS = [
    "group_1",
    "group_2",
    "difference",
    "statistic",
    "df",
    "p_value",
    "p_adjusted",
    "lower",
    "upper",
]


def posthoc(
    samples: Sequence[Any],
    names: Sequence[str],
    method: str,
    *,
    adjust: str = "holm",
    confidence: float = 0.95,
) -> PostHoc:
    """Pairwise comparisons of the groups, in their order (1 vs 2, 1 vs 3, …).

    ``tukey`` — Tukey's HSD on the ANOVA's pooled variance (Tukey-Kramer for
    unequal groups): q = |mᵢ − mⱼ| / √(MSE/2 · (1/nᵢ + 1/nⱼ)) against the
    studentized range for k groups and N − k df. ``games_howell`` — each
    pair's own variances and Welch df: q = √2 |t|. ``dunn`` — Dunn's z on the
    mean ranks of all N values, corrected for ties, with p adjusted by
    ``adjust`` (``holm`` or ``bonferroni``). A pair that cannot be compared
    keeps its row with missing numbers and a note.
    """

    if method not in POSTHOCS:
        raise ValueError(f"posthoc must be one of {', '.join(POSTHOCS)}; got {method!r}.")
    if method == "dunn" and adjust not in ("holm", "bonferroni"):
        raise ValueError("Dunn's test takes adjust='holm' or 'bonferroni'.")
    groups = _samples(samples)
    names = list(names)
    kept = [(g, name) for g, name in zip(groups, names, strict=True) if len(g)]
    groups, names = [g for g, _ in kept], [name for _, name in kept]
    if len(groups) < 2:
        raise NotTestable("a post-hoc comparison needs at least two groups with values")
    if method == "tukey":
        table, notes = _tukey(groups, names, confidence)
    elif method == "games_howell":
        table, notes = _games_howell(groups, names, confidence)
    else:
        table, notes = _dunn(groups, names, adjust)
    return PostHoc(
        method=method,
        table=table,
        adjust=adjust if method == "dunn" else "none",
        confidence=confidence,
        notes=notes,
    )


def _pairs(k: int) -> list[tuple[int, int]]:
    return [(i, j) for i in range(k) for j in range(i + 1, k)]


#: The smallest p Tukey's HSD and Games-Howell give as a number. SciPy's
#: ``studentized_range.sf`` is 1 − cdf, the cdf integrated to an absolute error
#: of 1e-11, so a smaller p has fewer than four significant digits right, and
#: past q ≈ 12 it is the integration's noise rather than a probability: every
#: pair of three groups at 297 df reads 1.144e-14 whatever its q, 597 df gives 0,
#: and in Games-Howell a larger q could get a larger p. Below the floor the p is
#: 0.0 here, and the post-hoc table prints ``< 1e-07``.
STUDENTIZED_P_FLOOR = 1e-7


def _studentized_p(q: float, k: int, df: float) -> float:
    """The studentized range's upper tail at ``q``: SciPy's, or 0.0 below
    :data:`STUDENTIZED_P_FLOOR`, which SciPy does not compute to."""
    from scipy.stats import studentized_range

    p = float(studentized_range.sf(q, k, df))
    return 0.0 if p < STUDENTIZED_P_FLOOR else p


@functools.lru_cache(maxsize=4096)
def _studentized_quantile(confidence: float, k: int, df: float) -> float:
    """The studentized range's ``confidence`` quantile for ``k`` groups and
    ``df`` degrees of freedom, as ``studentized_range.ppf`` gives it (to a
    relative 1e-11) in about a third of the time.

    SciPy's ppf root-finds from the interval (0, 10) to 1e-14, a double
    integral (the cdf) at each of about 13 steps: 0.2 s a quantile, and
    Games-Howell needs one a pair — 66 pairs of 12 groups took 14 s, 435 of 30
    took 114 s. Here Newton's method starts from the quantile at infinite df
    (a single integral) moved by its first-order term in 1/df,
    ``q (1 − q f′(q)/f(q)) / (4 df)`` with ``f`` that limit's density, which
    is within 1e-6 at a few hundred df, and stops once a step is below 1e-8
    of the value. When it does not settle (it always has), SciPy's ppf is used.
    """
    from scipy.stats import studentized_range

    limit = float(studentized_range.ppf(confidence, k, np.inf))
    if not math.isfinite(df) or df >= 100_000:  # SciPy's own limit form there
        return float(studentized_range.ppf(confidence, k, df))
    step = 1e-4
    density = float(studentized_range.pdf(limit, k, np.inf))
    slope = (
        float(studentized_range.pdf(limit + step, k, np.inf))
        - float(studentized_range.pdf(limit - step, k, np.inf))
    ) / (2 * step)
    q = limit + limit * (1 - limit * slope / density) / (4 * df)
    for _ in range(10):
        change = (float(studentized_range.cdf(q, k, df)) - confidence) / float(
            studentized_range.pdf(q, k, df)
        )
        q -= change
        if not math.isfinite(q) or q <= 0:
            break
        if abs(change) < 1e-8 * q:
            return q
    return float(studentized_range.ppf(confidence, k, df))


def _studentized_quantiles(confidence: float, k: int, dfs: Sequence[float]) -> list[float]:
    """:func:`_studentized_quantile` at each of ``dfs``.

    Games-Howell's Welch df differ from pair to pair, and past a few distinct
    ones the quantile is interpolated rather than solved for each: it is a
    smooth function of 1/df, and a polynomial through its values at the 17
    Chebyshev–Lobatto points of the range is taken when the one through every
    other point (9) agrees with it to 1e-7 of the value wherever it is read.
    Such an interpolation's error falls geometrically with its points, so the
    17-point one is then within about 1e-12 — below SciPy's own ppf's. Where
    they disagree (a range reaching down to one or two df), each is solved.
    """

    distinct = sorted(set(dfs))
    if len(distinct) <= 17 or not all(math.isfinite(df) and df < 100_000 for df in distinct):
        solved = {df: _studentized_quantile(confidence, k, df) for df in distinct}
        return [solved[df] for df in dfs]
    low, high = 1 / distinct[-1], 1 / distinct[0]
    nodes = (low + high) / 2 + (high - low) / 2 * np.cos(np.pi * np.arange(17) / 16)
    values = np.array([_studentized_quantile(confidence, k, 1 / x) for x in nodes])
    points = 1 / np.asarray(dfs, dtype=float)
    fine = np.polynomial.Chebyshev.fit(nodes, values, 16, domain=[low, high])(points)
    coarse = np.polynomial.Chebyshev.fit(nodes[::2], values[::2], 8, domain=[low, high])(points)
    if np.all(np.abs(fine - coarse) <= 1e-7 * np.abs(fine)):
        return [float(value) for value in fine]
    solved = {df: _studentized_quantile(confidence, k, df) for df in distinct}
    return [solved[df] for df in dfs]


def _tukey(
    groups: list[np.ndarray], names: list[str], confidence: float
) -> tuple[pd.DataFrame, list[str]]:
    from scipy.stats import studentized_range

    k = len(groups)
    total = sum(len(g) for g in groups)
    df = total - k
    if df < 1:
        raise NotTestable("Tukey's HSD needs more respondents than groups")
    mse = sum((len(g) - 1) * _variance(g) for g in groups if len(g) > 1) / df
    if mse <= 0:
        raise NotTestable("no group varies, so there is no spread to compare the means against")
    critical = float(studentized_range.ppf(confidence, k, df))
    rows = []
    for i, j in _pairs(k):
        difference = float(groups[i].mean() - groups[j].mean())
        se = math.sqrt(mse / 2 * (1 / len(groups[i]) + 1 / len(groups[j])))
        q = abs(difference) / se
        p = _studentized_p(q, k, df)
        rows.append(
            [names[i], names[j], difference, q, float(df), p, p, difference - critical * se]
            + [difference + critical * se]
        )
    return pd.DataFrame(rows, columns=_POSTHOC_COLUMNS), []


def _games_howell(
    groups: list[np.ndarray], names: list[str], confidence: float
) -> tuple[pd.DataFrame, list[str]]:
    k = len(groups)
    rows, notes, tested = [], [], []
    for i, j in _pairs(k):
        a, b = groups[i], groups[j]
        difference = float(a.mean() - b.mean())
        if len(a) < 2 or len(b) < 2:
            small = names[i] if len(a) < 2 else names[j]
            notes.append(f"{names[i]} vs {names[j]}: {small} has one value")
            rows.append([names[i], names[j], difference] + [np.nan] * 6)
            continue
        s1, s2 = _variance(a) / len(a), _variance(b) / len(b)
        if s1 + s2 <= 0:
            notes.append(f"{names[i]} vs {names[j]}: neither group varies")
            rows.append([names[i], names[j], difference] + [np.nan] * 6)
            continue
        se = math.sqrt(s1 + s2)
        df = (s1 + s2) ** 2 / (s1**2 / (len(a) - 1) + s2**2 / (len(b) - 1))
        q = abs(difference) / se * math.sqrt(2)
        p = _studentized_p(q, k, df)
        rows.append([names[i], names[j], difference, q, df, p, p, np.nan, np.nan])
        tested.append((len(rows) - 1, se))
    # Each pair's interval is the quantile at its own Welch df: found for all
    # of them at once, which is where the time went.
    quantiles = _studentized_quantiles(confidence, k, [rows[row][4] for row, _ in tested])
    for (row, se), quantile in zip(tested, quantiles, strict=True):
        half = quantile / math.sqrt(2) * se
        rows[row][7:] = [rows[row][2] - half, rows[row][2] + half]
    return pd.DataFrame(rows, columns=_POSTHOC_COLUMNS), notes


def _dunn(
    groups: list[np.ndarray], names: list[str], adjust: str
) -> tuple[pd.DataFrame, list[str]]:
    from scipy.stats import norm, rankdata

    values = np.concatenate(groups)
    total = len(values)
    ranks = rankdata(values)
    _, ties = np.unique(values, return_counts=True)
    tie_term = float((ties**3 - ties).sum()) / (12 * (total - 1)) if total > 1 else 0.0
    spread = total * (total + 1) / 12 - tie_term
    if spread <= 0:
        raise NotTestable("every value is the same, so there is nothing to rank")
    bounds = np.cumsum([0] + [len(g) for g in groups])
    mean_ranks = [float(ranks[bounds[i] : bounds[i + 1]].mean()) for i in range(len(groups))]
    rows = []
    for i, j in _pairs(len(groups)):
        difference = mean_ranks[i] - mean_ranks[j]
        z = difference / math.sqrt(spread * (1 / len(groups[i]) + 1 / len(groups[j])))
        rows.append([names[i], names[j], difference, z, np.nan, float(2 * norm.sf(abs(z)))])
    table = pd.DataFrame(rows, columns=_POSTHOC_COLUMNS[:6])
    table["p_adjusted"] = adjust_p(table["p_value"].to_numpy(), adjust)
    table["lower"] = table["upper"] = np.nan
    return table, []


# ─── Fisher's exact test ─────────────────────────────────────────────────────

#: Tables of more than 2 × 2 are enumerated exactly up to this many tables with
#: the observed margins, and sampled beyond it.
FISHER_EXACT_LIMIT = 200_000
#: Monte Carlo tables drawn when enumeration would take too long, and the seed
#: they are drawn from — fixed, so a rerun gives the same p.
FISHER_SAMPLES = 20_000
FISHER_SEED = 20_260_925


def fisher_exact(table: Any, *, confidence: float = 0.95) -> dict[str, Any]:
    """Fisher's exact test of independence on a table of counts.

    2 × 2: SciPy's two-sided p and the conditional maximum-likelihood odds
    ratio with its exact interval — the estimate and interval R's
    ``fisher.test`` defines, oriented as (a·d)/(b·c) for [[a, b], [c, d]], and
    solved to full precision: R's ``uniroot`` stops at a tolerance of eps^0.25,
    so on a sparse table R prints limits that differ slightly ([[8, 1], [2, 20]]:
    upper limit 3712.06 here, 3592.50 in R; the p agrees to 1e-12).
    Larger: the Fisher–Freeman–Halton test, whose p is the probability of the
    tables with these margins that are no more likely than the one observed.
    It is summed exactly over every such table when there are at most
    ``FISHER_EXACT_LIMIT`` of them, and otherwise estimated from
    ``FISHER_SAMPLES`` random tables drawn with a fixed seed (Patefield's
    algorithm), so the same data always gives the same p; ``exact`` says which,
    and a sampled p comes with ``p_error``, its standard error.

    Rows or columns without any count are dropped first; fewer than two of
    either leaves nothing to test.
    """

    counts = np.asarray(table, dtype=float)
    if counts.ndim != 2:
        raise ValueError("Fisher's exact test takes a two-way table.")
    if np.any(counts < 0) or not np.allclose(counts, np.round(counts)):
        raise ValueError("Fisher's exact test needs whole, non-negative counts.")
    counts = counts.astype(np.int64)
    counts = counts[counts.sum(axis=1) > 0][:, counts.sum(axis=0) > 0]
    if counts.shape[0] < 2 or counts.shape[1] < 2:
        raise NotTestable("the table has fewer than two rows or columns with answers in them")

    from scipy import stats

    if counts.shape == (2, 2):
        from scipy.stats.contingency import odds_ratio

        found = stats.fisher_exact(counts, alternative="two-sided")
        conditional = odds_ratio(counts, kind="conditional")
        interval = conditional.confidence_interval(confidence_level=confidence)
        return {
            "method": "Fisher's exact test",
            "p_value": float(found.pvalue),
            "exact": True,
            "odds_ratio": float(conditional.statistic),
            "lower": float(interval.low),
            "upper": float(interval.high),
            "confidence": confidence,
        }

    from scipy.special import gammaln

    rows, cols = counts.sum(axis=1), counts.sum(axis=0)
    total = int(counts.sum())
    log_factorial = gammaln(np.arange(total + 1) + 1.0)
    # A table's probability is Π rᵢ! Π cⱼ! / (N! Π nᵢⱼ!): with the margins fixed,
    # "no more likely" is a sum of log nᵢⱼ! at least the observed one.
    observed = float(log_factorial[counts].sum())
    constant = float(log_factorial[rows].sum() + log_factorial[cols].sum() - log_factorial[total])
    exact = _ffh_exact(rows, cols, observed, constant, log_factorial)
    method = "Fisher-Freeman-Halton exact test"
    if exact is not None:
        return {"method": method, "p_value": exact, "exact": True}
    sampled = stats.random_table(rows, cols).rvs(
        FISHER_SAMPLES, method="patefield", random_state=np.random.default_rng(FISHER_SEED)
    )
    statistic = log_factorial[sampled].sum(axis=(1, 2))
    extreme = int((statistic >= observed - 1e-7).sum())
    p = (extreme + 1) / (FISHER_SAMPLES + 1)
    return {
        "method": method,
        "p_value": float(p),
        "exact": False,
        "samples": FISHER_SAMPLES,
        "seed": FISHER_SEED,
        "p_error": float(math.sqrt(p * (1 - p) / FISHER_SAMPLES)),
    }


def _ffh_exact(
    rows: np.ndarray,
    cols: np.ndarray,
    observed: float,
    constant: float,
    log_factorial: np.ndarray,
) -> float | None:
    """The exact Fisher–Freeman–Halton p, or None past ``FISHER_EXACT_LIMIT`` tables.

    Walks every table with these margins row by row: each row is a split of its
    total over the columns' remaining capacity, and the last row is what is
    left. Tables no more likely than the observed one add their probability.
    """

    row_totals = [int(r) for r in rows]
    capacity = [int(c) for c in cols]
    width = len(capacity)
    seen = 0
    mass = 0.0

    def splits(total: int, room: list[int], start: int) -> Any:
        if start == width - 1:
            if total <= room[start]:
                yield [total]
            return
        rest = sum(room[start + 1 :])
        for value in range(max(0, total - rest), min(room[start], total) + 1):
            for tail in splits(total - value, room, start + 1):
                yield [value, *tail]

    def walk(index: int, room: list[int], partial: float) -> bool:
        nonlocal seen, mass
        if index == len(row_totals) - 1:
            seen += 1
            if seen > FISHER_EXACT_LIMIT:
                return False
            statistic = partial + float(log_factorial[room].sum())
            if statistic >= observed - 1e-7:
                mass += math.exp(constant - statistic)
            return True
        for split in splits(row_totals[index], room, 0):
            left = [r - s for r, s in zip(room, split, strict=True)]
            if not walk(index + 1, left, partial + float(log_factorial[split].sum())):
                return False
        return True

    if not walk(0, capacity, 0.0):
        return None
    return float(min(1.0, mass))


__all__ = [
    "ADJUSTMENTS",
    "ADJUSTMENT_NAMES",
    "CORRELATIONS",
    "CORRELATION_NAMES",
    "CORRELATION_SYMBOLS",
    "POSTHOCS",
    "POSTHOC_FOLLOWS",
    "POSTHOC_NAMES",
    "SPREAD_TOLERANCE",
    "STUDENTIZED_P_FLOOR",
    "CorrelationMatrix",
    "GroupTest",
    "NotTestable",
    "PostHoc",
    "TTest",
    "adjust_p",
    "anova",
    "correlate",
    "correlation_matrix",
    "fisher_exact",
    "kruskal",
    "mannwhitney",
    "missing_codes_counted",
    "missing_codes_note",
    "no_spread",
    "posthoc",
    "ttest_independent",
    "ttest_one_sample",
    "ttest_paired",
    "welch_anova",
    "without_missing_codes",
]
