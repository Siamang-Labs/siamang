"""Tests for related samples: the same respondents answering two or more questions.

:meth:`~siamang.data.analysis.DataAnalysis.mannwhitney` and
:meth:`~siamang.data.analysis.DataAnalysis.kruskal` compare *different*
people. These compare answers that come in sets from *one* person — the same
scale asked about two brands, a rating before and after a message, three
concepts each rated by everyone — where the question is whether the answers
shift, and the respondent is their own control.

- :func:`wilcoxon` — Wilcoxon signed-rank, two ordered variables;
- :func:`mcnemar` — McNemar, two yes/no variables;
- :func:`friedman` — Friedman, three or more ordered variables, with pairwise
  Wilcoxon comparisons adjusted by Holm or Bonferroni;
- :func:`compare` — what the ``analyze.paired`` flow node calls: Wilcoxon for
  two variables and Friedman for more, or the test it is told to run.

A respondent with a blank in any of the compared variables is left out of all
of them (:func:`siamang.data.listwise.listwise`): a pair with half its answers
is not a pair. The codebook's missing codes count as blanks, not answers. Every
result says how many respondents that left out.

The statistics, and the conventions behind them:

**Wilcoxon signed-rank.** The differences are *first minus second* — as R's
``wilcox.test(x, y, paired = TRUE)`` and SciPy's ``wilcoxon(x, y)`` take them,
and as the paired t-test reports its mean difference. Pairs that
gave the same answer twice (zero differences) are dropped before ranking —
Wilcoxon's own method, and what R's ``wilcox.test`` and SPSS do — or, with
``zeros="pratt"``, ranked with the others and left out of the sums (Pratt
1959). Tied absolute differences get their average rank. ``W+`` and ``W-`` are
the sums of the ranks of the positive and negative differences. The p-value is
two-sided and follows SciPy's ``wilcoxon`` (1.13 and later): exact when there
are at most 50 pairs and no ties or zeros, exact over the permutations of the
signs when there are at most 13 pairs with ties or zeros, and otherwise the
normal approximation with the tie correction and without a continuity
correction (R's default applies one; SPSS does not). ``p_value="exact"``
computes the exact permutation distribution of the (average) ranks for any
sample up to :data:`EXACT_LIMIT` pairs; ``"approximate"`` always uses the
normal approximation. ``Z = (W+ − E[W+]) / SD[W+]`` from the same
approximation is reported either way, signed so that a positive Z means the
first variable tends to be higher. Effect sizes: ``r = Z / √n`` with ``n`` the
pairs in the ranking (Rosenthal 1991), and the matched-pairs rank-biserial
correlation ``(W+ − W-) / (W+ + W-)`` (Kerby 2014), which runs from −1 (every
difference negative) to 1.

**McNemar.** Each variable becomes yes (the codes in ``yes``) or no (any other
answer). Only the respondents who differ between the two carry information:
``b`` said yes to the first and no to the second, ``c`` the other way round.
With fewer than 25 of them the p-value is the exact two-sided binomial test of
``b`` against ``b + c`` at ½; otherwise it is the chi-square with Edwards'
continuity correction, ``(|b − c| − 1)² / (b + c)`` on 1 df, as R's
``mcnemar.test`` and statsmodels compute it. Reported beside it: the share
saying yes to each, their difference, Cohen's ``g = max(b, c) / (b + c) − ½``
and the odds ratio ``b / c``.

**Friedman.** Each respondent's answers are ranked among themselves (ties get
their average rank); ``χ² = [12 / (n k (k+1)) Σ Rⱼ² − 3 n (k+1)] / C`` on
``k − 1`` df, with the tie correction ``C = 1 − Σ(t³ − t) / (n k (k² − 1))``, as
SciPy's ``friedmanchisquare`` and R's ``friedman.test``. Kendall's ``W = χ² /
(n (k − 1))``. The pairwise comparisons are Wilcoxon signed-rank tests of every
pair on the same respondents, with the p-values adjusted by Holm's step-down
method (default) or Bonferroni. Tests on the mean ranks (Nemenyi, Dunn) are not
offered: the mean rank of two variables depends on which *other* variables are
in the set, so adding a third concept could change whether the first two
differ (Benavoli, Corani & Mangili 2016).

None of these tests has a standard weighted form, so they run on the
respondents as they are and, on weighted data, their statistics carry
``Weight: unweighted (the weight 'w' is not applied)``.

The array-level functions — :func:`signed_rank`, :func:`mcnemar_test`,
:func:`friedman_test` and :func:`adjust` — take plain numbers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

from siamang.data.listwise import (
    Listwise,
    distinct,
    label_of,
    listwise,
    p_rounded,
    result_table,
    rounded,
    unweighted,
)

if TYPE_CHECKING:
    from siamang.data.survey_data import SurveyData
    from siamang.reporting.result_table import ResultTable

TESTS = ("auto", "wilcoxon", "mcnemar", "friedman")
ZERO_METHODS = ("wilcox", "pratt")
P_VALUES = ("auto", "exact", "approximate")
POSTHOC = ("holm", "bonferroni", "none")

#: Pairs up to which an exact Wilcoxon p-value is computed when asked for.
EXACT_LIMIT = 1000
#: Discordant pairs below which McNemar's p-value is the exact binomial test.
MCNEMAR_EXACT_BELOW = 25


# ── results ──────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class SignedRank:
    """A Wilcoxon signed-rank test on one set of differences."""

    n: int  # differences given (zeros included)
    ranked: int  # differences in the ranking: non-zero (wilcox) or all (pratt)
    positive: int
    negative: int
    zeros: int
    w_plus: float
    w_minus: float
    z: float | None  # None when nothing is left to rank
    p: float | None
    method: str  # "exact" | "normal approximation" | "none"
    r: float | None
    rank_biserial: float | None
    ties: bool
    note: str | None = None


@dataclass(frozen=True, slots=True)
class McNemarTest:
    """McNemar's test from the two discordant counts."""

    b: int  # yes on the first, no on the second
    c: int  # no on the first, yes on the second
    statistic: float | None  # chi-square, None for the exact test
    df: int | None
    p: float | None
    method: str  # "exact binomial" | "chi-square with continuity correction" | "none"
    cohens_g: float | None
    odds_ratio: float | None


@dataclass(frozen=True, slots=True)
class FriedmanTest:
    n: int
    k: int
    statistic: float | None
    df: int
    p: float | None
    kendalls_w: float | None
    mean_ranks: np.ndarray


@dataclass(frozen=True, slots=True)
class PairedResult:
    """What a paired test found: a table, the pairwise comparisons, the statistics.

    ``table`` and ``pairs`` are tables for a report (the statistics as their
    footer); ``stats`` is the same statistics as a dict; ``test`` holds the
    unrounded numbers.
    """

    table: ResultTable
    pairs: ResultTable
    stats: dict[str, Any] = field(default_factory=dict)
    test: SignedRank | McNemarTest | FriedmanTest | None = None


# ── array level ──────────────────────────────────────────────────────────────


def signed_rank(differences: Any, *, zeros: str = "wilcox", p_value: str = "auto") -> SignedRank:
    """Wilcoxon signed-rank test of ``differences`` against 0, two-sided.

    Missing values (NaN) are ignored. See the module docstring for how zeros,
    ties and the p-value are handled.
    """

    from scipy.stats import norm, rankdata

    if zeros not in ZERO_METHODS:
        raise ValueError(f"zeros must be one of {', '.join(ZERO_METHODS)}.")
    if p_value not in P_VALUES:
        raise ValueError(f"p_value must be one of {', '.join(P_VALUES)}.")
    d = np.asarray(differences, dtype=float).ravel()
    d = d[~np.isnan(d)]
    n = int(len(d))
    is_zero = d == 0
    n_zero = int(is_zero.sum())
    positive, negative = int((d > 0).sum()), int((d < 0).sum())
    if zeros == "wilcox":
        kept = d[~is_zero]
        ranks = rankdata(np.abs(kept)) if len(kept) else np.zeros(0)
        signs = np.sign(kept)
        count = len(kept)
        mean = count * (count + 1) / 4
        variance = count * (count + 1) * (2 * count + 1) / 24
    else:
        all_ranks = rankdata(np.abs(d)) if n else np.zeros(0)
        ranks = all_ranks[~is_zero]
        signs = np.sign(d[~is_zero])
        count = n
        # Cureton (1967): the zeros' ranks are not in either sum.
        mean = (count * (count + 1) - n_zero * (n_zero + 1)) / 4
        variance = (
            count * (count + 1) * (2 * count + 1) - n_zero * (n_zero + 1) * (2 * n_zero + 1)
        ) / 24
    ties_t = _tie_sizes(ranks)
    variance -= float((ties_t**3 - ties_t).sum()) / 48
    w_plus = float(ranks[signs > 0].sum())
    w_minus = float(ranks[signs < 0].sum())
    has_ties = bool((ties_t > 1).any())
    if len(ranks) == 0 or variance <= 0:
        note = (
            "every respondent gave the same answer to both, so there is no difference to test"
            if n
            else "no complete pairs"
        )
        return SignedRank(
            n=n,
            ranked=int(count),
            positive=positive,
            negative=negative,
            zeros=n_zero,
            w_plus=w_plus,
            w_minus=w_minus,
            z=None,
            p=None,
            method="none",
            r=None,
            rank_biserial=None,
            ties=has_ties,
            note=note,
        )
    z = (w_plus - mean) / variance**0.5
    note = None
    if p_value == "approximate":
        exact = False
    elif p_value == "exact":
        exact = len(ranks) <= EXACT_LIMIT
        if not exact:
            note = (
                f"an exact p-value is computed for at most {EXACT_LIMIT} pairs; with "
                f"{len(ranks)} the normal approximation is used"
            )
    else:  # SciPy's rule, 1.13 and later
        exact = n <= 50 and (not (has_ties or n_zero) or n <= 13)
    if exact:
        p = _exact_signed_rank_p(ranks, w_plus)
        method = "exact"
    else:
        p = float(min(1.0, 2 * norm.sf(abs(z))))
        method = "normal approximation"
    total = w_plus + w_minus
    return SignedRank(
        n=n,
        ranked=int(count),
        positive=positive,
        negative=negative,
        zeros=n_zero,
        w_plus=w_plus,
        w_minus=w_minus,
        z=float(z),
        p=float(p),
        method=method,
        r=float(z / count**0.5),
        rank_biserial=float((w_plus - w_minus) / total) if total > 0 else None,
        ties=has_ties,
        note=note,
    )


def _tie_sizes(ranks: np.ndarray) -> np.ndarray:
    if len(ranks) == 0:
        return np.zeros(0)
    _, counts = np.unique(ranks, return_counts=True)
    return counts.astype(float)


def _exact_signed_rank_p(ranks: np.ndarray, w_plus: float) -> float:
    """Two-sided p of ``W+`` over the 2ⁿ equally likely sign patterns.

    Average ranks are multiples of ½, so twice the ranks are integers and the
    distribution of twice ``W+`` is built by convolution, one rank at a time.
    Without ties this is the classical exact distribution; with ties it is the
    exact permutation distribution of the ranks observed.
    """

    doubled = np.rint(2 * np.asarray(ranks, dtype=float)).astype(np.int64)
    total = int(doubled.sum())
    dist = np.zeros(total + 1)
    dist[0] = 1.0
    top = 0
    for step in doubled:
        step = int(step)
        new = dist[: top + step + 1].copy()
        new[step : top + step + 1] += dist[: top + 1]
        dist[: top + step + 1] = new * 0.5
        top += step
    observed = int(round(2 * w_plus))
    lower = float(dist[: observed + 1].sum())
    upper = float(dist[observed:].sum())
    return float(min(1.0, 2 * min(lower, upper)))


def mcnemar_test(b: int, c: int, *, p_value: str = "auto") -> McNemarTest:
    """McNemar's test from the discordant counts ``b`` (yes, no) and ``c`` (no, yes)."""

    from scipy.stats import binom, chi2

    if p_value not in P_VALUES:
        raise ValueError(f"p_value must be one of {', '.join(P_VALUES)}.")
    b, c = int(b), int(c)
    n = b + c
    if n == 0:
        return McNemarTest(b, c, None, None, None, "none", None, None)
    g = max(b, c) / n - 0.5
    odds = b / c if c > 0 and b > 0 else None
    if p_value == "exact" or (p_value == "auto" and n < MCNEMAR_EXACT_BELOW):
        p = float(min(1.0, 2 * binom.cdf(min(b, c), n, 0.5)))
        return McNemarTest(b, c, None, None, p, "exact binomial", g, odds)
    statistic = (abs(b - c) - 1) ** 2 / n
    return McNemarTest(
        b,
        c,
        float(statistic),
        1,
        float(chi2.sf(statistic, 1)),
        "chi-square with continuity correction",
        g,
        odds,
    )


def friedman_test(matrix: Any) -> FriedmanTest:
    """Friedman's test on ``matrix`` (respondents × variables), tie-corrected."""

    from scipy.stats import chi2, rankdata

    x = np.asarray(matrix, dtype=float)
    if x.ndim != 2 or x.shape[1] < 3:
        raise ValueError("Friedman's test needs three or more variables.")
    n, k = x.shape
    if n == 0:
        return FriedmanTest(0, k, None, k - 1, None, None, np.full(k, np.nan))
    ranks = rankdata(x, axis=1)
    rank_sums = ranks.sum(axis=0)
    ties = 0.0
    for row in x:
        _, counts = np.unique(row, return_counts=True)
        ties += float((counts**3 - counts).sum())
    correction = 1 - ties / (n * k * (k * k - 1))
    mean_ranks = rank_sums / n
    if correction <= 1e-12:
        return FriedmanTest(n, k, None, k - 1, None, None, mean_ranks)
    statistic = (12.0 / (n * k * (k + 1)) * float((rank_sums**2).sum()) - 3 * n * (k + 1)) / (
        correction
    )
    statistic = max(statistic, 0.0)
    return FriedmanTest(
        n=n,
        k=k,
        statistic=float(statistic),
        df=k - 1,
        p=float(chi2.sf(statistic, k - 1)),
        kendalls_w=float(statistic / (n * (k - 1))),
        mean_ranks=mean_ranks,
    )


def adjust(pvalues: Any, method: str = "holm") -> np.ndarray:
    """p-values adjusted for multiple comparisons (``holm``, ``bonferroni`` or
    ``none``); NaN stays NaN and is not counted, as R's ``p.adjust`` does."""

    p = np.asarray(pvalues, dtype=float)
    out = np.full(p.shape, np.nan)
    present = ~np.isnan(p)
    values = p[present]
    m = len(values)
    if method == "none" or m == 0:
        out[present] = values
        return out
    if method == "bonferroni":
        out[present] = np.minimum(1.0, values * m)
        return out
    if method != "holm":
        raise ValueError("method must be 'holm', 'bonferroni' or 'none'.")
    order = np.argsort(values, kind="stable")
    adjusted = np.empty(m)
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, min(1.0, (m - rank) * values[index]))
        adjusted[index] = running
    out[present] = adjusted
    return out


# ── on survey data ───────────────────────────────────────────────────────────


def count_problem(test: str, count: int) -> str | None:
    """Why ``test`` cannot compare ``count`` variables, or None when it can.

    The message :func:`compare` raises, and the one ``check_flow`` gives for
    the node before a run: the number of variables is known from the flow.
    """

    given = f"{count} {'was' if count == 1 else 'were'} given"
    if test == "auto" and count < 2:
        return (
            "Paired tests compare two or more variables answered by the same "
            "respondents — two for Wilcoxon signed-rank (or McNemar), three or more "
            f"for Friedman; {given}."
        )
    if test in {"wilcoxon", "mcnemar"} and count != 2:
        name = "Wilcoxon signed-rank" if test == "wilcoxon" else "McNemar"
        more = " For three or more, use Friedman." if test == "wilcoxon" else ""
        return f"{name} compares exactly two variables; {given}.{more}"
    if test == "friedman" and count < 3:
        return (
            f"Friedman's test compares three or more variables; {given}. For two, use "
            "Wilcoxon signed-rank (or McNemar for yes/no)."
        )
    return None


def compare(
    data: SurveyData,
    variables: list[str],
    *,
    test: str = "auto",
    yes: Any = None,
    zeros: str = "wilcox",
    p_value: str = "auto",
    posthoc: str = "holm",
) -> PairedResult:
    """Run the paired test ``test`` on ``variables`` — the ``analyze.paired`` node.

    ``auto`` is Wilcoxon for two variables and Friedman for three or more;
    McNemar, for two yes/no variables, is run when asked for.
    """

    if test not in TESTS:
        raise ValueError(f"test must be one of {', '.join(TESTS)}.")
    variables = list(variables or [])
    problem = count_problem(test, len(variables))
    if problem:
        raise ValueError(problem)
    if test == "auto":
        test = "wilcoxon" if len(variables) == 2 else "friedman"
    if test in {"wilcoxon", "mcnemar"}:
        if test == "wilcoxon":
            return wilcoxon(data, variables[0], variables[1], zeros=zeros, p_value=p_value)
        return mcnemar(data, variables[0], variables[1], yes=yes, p_value=p_value)
    return friedman(data, variables, posthoc=posthoc, zeros=zeros, p_value=p_value)


def wilcoxon(
    data: SurveyData,
    x: str,
    y: str,
    *,
    zeros: str = "wilcox",
    p_value: str = "auto",
) -> PairedResult:
    """Wilcoxon signed-rank test of ``x − y`` for the respondents who answered both."""

    distinct([x, y])
    _ordered(data, [x, y], "Wilcoxon signed-rank")
    rows = listwise(data, [x, y])
    first, second = rows.frame[x].to_numpy(), rows.frame[y].to_numpy()
    result = signed_rank(first - second, zeros=zeros, p_value=p_value)
    label_x, label_y = label_of(data, x), label_of(data, y)
    table = _describe(
        data, rows, [x, y], extra=[(f"Difference ({label_x} − {label_y})", first - second)]
    )
    stats: dict[str, Any] = {
        "Test": "Wilcoxon signed-rank",
        "Difference": f"{label_x} − {label_y}",
        "N": rows.n,
        "Positive differences": result.positive,
        "Negative differences": result.negative,
        "Zero differences": result.zeros,
    }
    stats.update(_signed_rank_stats(result))
    stats["Zeros"] = (
        "dropped before ranking (Wilcoxon)"
        if zeros == "wilcox"
        else "ranked, then left out of the sums (Pratt)"
    )
    rows.report(stats, "either variable")
    unweighted(stats, data)
    return PairedResult(
        table=result_table(data, table, stats),
        pairs=_no_pairs(data, "two variables are one comparison; see the table's statistics"),
        stats=stats,
        test=result,
    )


def mcnemar(
    data: SurveyData,
    x: str,
    y: str,
    *,
    yes: Any = None,
    p_value: str = "auto",
) -> PairedResult:
    """McNemar's test: does the share saying yes differ between ``x`` and ``y``?

    ``yes`` is the answer code, or a list of codes, that counts as yes; every
    other answer is no. Left empty, it is 1 when both variables hold only 0
    and 1 — the shape ``prepare.explode`` and ``prepare.derive`` produce.
    """

    distinct([x, y])
    rows = listwise(data, [x, y], numeric=False)
    codes, warning = _yes_codes(data, rows, [x, y], yes)
    said_x = rows.frame[x].isin(codes).to_numpy()
    said_y = rows.frame[y].isin(codes).to_numpy()
    a = int((said_x & said_y).sum())
    b = int((said_x & ~said_y).sum())
    c = int((~said_x & said_y).sum())
    d = int((~said_x & ~said_y).sum())
    result = mcnemar_test(b, c, p_value=p_value)
    label_x, label_y = label_of(data, x), label_of(data, y)
    table = pd.DataFrame(
        {
            label_x: ["Yes", "No", "Total"],
            f"{label_y}: yes": [a, c, a + c],
            f"{label_y}: no": [b, d, b + d],
            "Total": [a + b, c + d, rows.n],
        }
    )
    n = rows.n
    stats: dict[str, Any] = {
        "Test": "McNemar",
        "Counts as yes": _codes_text(data, [x, y], codes),
        "N": n,
    }
    if n:
        share_x, share_y = (a + b) / n * 100, (a + c) / n * 100
        stats[f"% yes: {x}"] = rounded(share_x, 1)
        stats[f"% yes: {y}"] = rounded(share_y, 1)
        stats["Difference"] = f"{label_x} − {label_y}"
        stats["Difference (points)"] = rounded(share_x - share_y, 1)
    stats[f"Yes only: {x}"] = b
    stats[f"Yes only: {y}"] = c
    if warning:
        stats["Warning"] = warning
    if result.method == "none":
        stats["Note"] = (
            "no respondent answered the two differently, so there is nothing to test"
            if n
            else "no respondent answered both"
        )
    else:
        if result.statistic is not None:
            stats["Chi-square"] = rounded(result.statistic, 3)
            stats["df"] = result.df
        stats["p"] = p_rounded(result.p)
        stats["p-value"] = (
            f"exact binomial ({b + c} discordant pairs)"
            if result.method == "exact binomial"
            else "chi-square with continuity correction"
        )
        stats["Cohen's g"] = rounded(result.cohens_g, 3)
        if result.odds_ratio is not None:
            stats["Odds ratio"] = rounded(result.odds_ratio, 3)
    rows.report(stats, "either variable")
    unweighted(stats, data)
    return PairedResult(
        table=result_table(data, table, stats),
        pairs=_no_pairs(data, "two variables are one comparison; see the table's statistics"),
        stats=stats,
        test=result,
    )


def friedman(
    data: SurveyData,
    variables: list[str],
    *,
    posthoc: str = "holm",
    zeros: str = "wilcox",
    p_value: str = "auto",
) -> PairedResult:
    """Friedman's test on three or more ``variables``, with pairwise comparisons.

    ``posthoc`` adjusts the pairwise Wilcoxon p-values by ``holm`` or
    ``bonferroni``; ``none`` skips the comparisons. ``zeros`` and ``p_value``
    are those of the pairwise Wilcoxon tests.
    """

    if posthoc not in POSTHOC:
        raise ValueError(f"posthoc must be one of {', '.join(POSTHOC)}.")
    variables = list(variables)
    problem = count_problem("friedman", len(variables))
    if problem:
        raise ValueError(problem)
    distinct(variables)
    _ordered(data, variables, "Friedman's test")
    rows = listwise(data, variables)
    matrix = rows.frame[variables].to_numpy()
    result = friedman_test(matrix)
    table = _describe(data, rows, variables)
    table["Mean rank"] = [rounded(value, 3) for value in result.mean_ranks]
    stats: dict[str, Any] = {"Test": "Friedman", "Variables": len(variables), "N": rows.n}
    if result.statistic is None:
        stats["Note"] = (
            "every respondent gave the same answer to all the variables, so there is "
            "nothing to rank"
            if rows.n
            else "no respondent answered all the variables"
        )
    else:
        stats["Chi-square"] = rounded(result.statistic, 3)
        stats["df"] = result.df
        stats["p"] = p_rounded(result.p)
        stats["Kendall's W"] = rounded(result.kendalls_w, 3)
    stats["Pairwise"] = (
        "none"
        if posthoc == "none"
        else f"Wilcoxon signed-rank, {'Holm' if posthoc == 'holm' else 'Bonferroni'}-adjusted p"
    )
    rows.report(stats, "any of the variables")
    unweighted(stats, data)
    if posthoc == "none":
        pairs = _no_pairs(data, "pairwise comparisons were not asked for")
    else:
        pairs = _pairwise(data, rows, variables, posthoc=posthoc, zeros=zeros, p_value=p_value)
    return PairedResult(
        table=result_table(data, table, stats), pairs=pairs, stats=stats, test=result
    )


def _pairwise(
    data: SurveyData,
    rows: Listwise,
    variables: list[str],
    *,
    posthoc: str,
    zeros: str,
    p_value: str,
) -> ResultTable:
    results = []
    for first, second in combinations(variables, 2):
        difference = rows.frame[first].to_numpy() - rows.frame[second].to_numpy()
        results.append((first, second, signed_rank(difference, zeros=zeros, p_value=p_value)))
    raw = [np.nan if result.p is None else result.p for _, _, result in results]
    adjusted = adjust(raw, posthoc)
    frame = pd.DataFrame(
        [
            {
                "Variable A": label_of(data, first),
                "Variable B": label_of(data, second),
                # N is everyone compared, as in the footer and the two-variable
                # table; the pairs that answered the same are counted beside it.
                "N": result.n,
                "Zero differences": result.zeros,
                "W+": result.w_plus,
                "W-": result.w_minus,
                "Z": rounded(result.z, 3),
                "p": p_rounded(result.p),
                "p adjusted": p_rounded(None if np.isnan(value) else float(value)),
                "r": rounded(result.r, 3),
                "Rank-biserial r": rounded(result.rank_biserial, 3),
            }
            for (first, second, result), value in zip(results, adjusted, strict=True)
        ]
    )
    tested = int((~np.isnan(np.asarray(raw))).sum())
    footer: dict[str, Any] = {
        "Test": "Wilcoxon signed-rank for each pair",
        "Difference": "A − B",
        "Adjustment": f"{'Holm' if posthoc == 'holm' else 'Bonferroni'} ({tested} comparisons)",
        "N": rows.n,
    }
    methods = sorted({result.method for _, _, result in results if result.method != "none"})
    if methods:
        footer["p-value"] = " / ".join(methods)
    untested = [
        f"{label_of(data, a)} – {label_of(data, b)}" for a, b, result in results if result.p is None
    ]
    if untested:
        footer["Note"] = f"no differences to test for {', '.join(untested)}"
    unweighted(footer, data)
    return result_table(data, frame, footer)


# ── helpers ──────────────────────────────────────────────────────────────────


def _signed_rank_stats(result: SignedRank) -> dict[str, Any]:
    stats: dict[str, Any] = {"W+": result.w_plus, "W-": result.w_minus}
    if result.p is None:
        stats["Note"] = result.note
        return stats
    stats["Z"] = rounded(result.z, 3)
    stats["p"] = p_rounded(result.p)
    stats["p-value"] = (
        "exact" if result.method == "exact" else "normal approximation, tie-corrected"
    )
    if result.note:
        stats["Note"] = result.note
    stats["r"] = rounded(result.r, 3)
    stats["Rank-biserial r"] = rounded(result.rank_biserial, 3)
    return stats


def _describe(
    data: SurveyData,
    rows: Listwise,
    variables: list[str],
    extra: list[tuple[str, np.ndarray]] | None = None,
) -> pd.DataFrame:
    """N, mean, SD and median of each variable over the complete rows (and of
    any ``extra`` (label, values) series, such as the differences)."""
    series = [(label_of(data, name), rows.frame[name].to_numpy()) for name in variables]
    return pd.DataFrame(
        [
            {"Variable": label, "N": rows.n, **_summary(values)}
            for label, values in [*series, *(extra or [])]
        ],
        columns=["Variable", "N", "Mean", "SD", "Median"],
    )


def _summary(values: np.ndarray) -> dict[str, float | None]:
    n = len(values)
    return {
        "Mean": rounded(float(np.mean(values)), 3) if n else None,
        "SD": rounded(float(np.std(values, ddof=1)), 3) if n > 1 else None,
        "Median": rounded(float(np.median(values)), 3) if n else None,
    }


def _no_pairs(data: SurveyData, why: str) -> ResultTable:
    columns = [
        "Variable A",
        "Variable B",
        "N",
        "Zero differences",
        "W+",
        "W-",
        "Z",
        "p",
        "p adjusted",
        "r",
        "Rank-biserial r",
    ]
    return result_table(
        data, pd.DataFrame(columns=columns), {"Note": f"no pairwise comparisons: {why}"}
    )


def _ordered(data: SurveyData, variables: list[str], test: str) -> None:
    """Refuse a nominal variable: ranking its codes would rank region 3 above 1."""
    if data.variables is None:
        return
    nominal = [
        name
        for name in variables
        if name in data.variables and data.variables[name].scale == "nominal"
    ]
    if nominal:
        raise ValueError(
            f"{test} ranks the answers, so it needs ordered values; "
            f"{', '.join(nominal)} {'is' if len(nominal) == 1 else 'are'} nominal. "
            "For two yes/no questions use McNemar."
        )


def _yes_codes(
    data: SurveyData, rows: Listwise, variables: list[str], yes: Any
) -> tuple[list[Any], str | None]:
    """The codes that count as yes, and a warning when no respondent gave any."""
    values: set[Any] = set()
    for name in variables:
        values.update(rows.frame[name].tolist())
    if yes is not None and yes != [] and yes != "":
        codes = list(yes) if isinstance(yes, list | tuple | set) else [yes]
        if rows.n and not pd.Series(list(values), dtype=object).isin(codes).any():
            shown = ", ".join(map(str, codes))
            return codes, (
                f"no respondent gave {shown} to either variable, so every answer counts "
                "as no; check the code"
            )
        return codes, None
    if values <= {0, 1}:
        return [1], None
    shown = ", ".join(_code_text(data, variables, value) for value in _sorted(values))
    raise ValueError(
        f"McNemar needs to know which answer counts as yes: the variables hold {shown}. "
        "Name that code (or a list of codes) in Counts as yes — `yes` outside a flow; "
        "every other answer counts as no."
    )


def _sorted(values: set[Any]) -> list[Any]:
    return sorted(values, key=lambda value: (str(type(value)), value))


def _code_text(data: SurveyData, variables: list[str], code: Any) -> str:
    if isinstance(code, float) and code.is_integer():
        code = int(code)  # a column with a blank in it is float: 1.0 is the code 1
    for name in variables:
        if data.variables is not None and name in data.variables:
            label = (data.variables[name].labels or {}).get(code)
            if label:
                return f"{code} = {label}"
    return str(code)


def _codes_text(data: SurveyData, variables: list[str], codes: list[Any]) -> str:
    return ", ".join(_code_text(data, variables, code) for code in codes)


__all__ = [
    "EXACT_LIMIT",
    "MCNEMAR_EXACT_BELOW",
    "FriedmanTest",
    "McNemarTest",
    "PairedResult",
    "SignedRank",
    "adjust",
    "compare",
    "count_problem",
    "friedman",
    "friedman_test",
    "mcnemar",
    "mcnemar_test",
    "signed_rank",
    "wilcoxon",
]
