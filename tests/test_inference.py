"""siamang.data.inference and the tables built on it: correlations, t-tests,
tests of several groups, post-hoc comparisons, Fisher's exact test and the
p-value adjustments.

Every reference value is worked by hand in a comment, or is what SciPy, R or
pingouin / scikit-posthocs (quoted, not imported) give for the same numbers.
"""

from __future__ import annotations

import itertools
import math

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from siamang.core.variable import Variable, VariableMap
from siamang.data import SurveyData, inference
from siamang.data.inference import NotTestable

# Three small groups used throughout: means 34/7, 44/6 and 53/8.
A = [3, 4, 5, 4, 6, 7, 5]
B = [6, 7, 8, 6, 9, 8]
C = [5, 5, 6, 7, 6, 8, 9, 7]


# ─── p adjustment ────────────────────────────────────────────────────────────


def test_p_adjustments_match_r_p_adjust():
    p = [0.01, 0.04, 0.03, 0.2]
    # Holm: sorted 0.01, 0.03, 0.04, 0.2 times 4, 3, 2, 1 = 0.04, 0.09, 0.08, 0.2,
    # made non-decreasing: 0.04, 0.09, 0.09, 0.2.
    assert inference.adjust_p(p, "holm") == pytest.approx([0.04, 0.09, 0.09, 0.2])
    # Benjamini-Hochberg: times 4/1, 4/2, 4/3, 4/4 = 0.04, 0.06, 0.0533, 0.2, then
    # the running minimum from the largest: 0.04, 0.0533, 0.0533, 0.2.
    assert inference.adjust_p(p, "fdr_bh") == pytest.approx([0.04, 0.16 / 3, 0.16 / 3, 0.2])
    assert inference.adjust_p(p, "bonferroni") == pytest.approx([0.04, 0.16, 0.12, 0.8])
    assert inference.adjust_p(p, "none") == pytest.approx(p)
    # Capped at 1; a missing p stays missing and does not count towards m.
    assert inference.adjust_p([0.4, 0.6], "bonferroni") == pytest.approx([0.8, 1.0])
    adjusted = inference.adjust_p([0.01, np.nan, 0.03], "bonferroni")
    assert adjusted[0] == pytest.approx(0.02) and math.isnan(adjusted[1])
    with pytest.raises(ValueError, match="adjust must be one of"):
        inference.adjust_p(p, "sidak")


# ─── correlation ─────────────────────────────────────────────────────────────


def test_pearson_by_hand_with_its_fisher_interval():
    # x deviations -2 -1 0 1 2, y deviations -2 0 1 0 1: Σxy = 6, Σx² = 10,
    # Σy² = 6, so r = 6 / √60 = √0.6 and t = r √(3 / 0.4) = 3 / √2 on 3 df.
    result = inference.correlate([1, 2, 3, 4, 5], [2, 4, 5, 4, 5], method="pearson")
    assert result["method"] == "Pearson" and result["n"] == 5
    assert result["r"] == pytest.approx(math.sqrt(0.6))
    assert result["p_value"] == pytest.approx(2 * stats.t.sf(3 / math.sqrt(2), 3))
    z, half = math.atanh(math.sqrt(0.6)), 1.959963984540054 / math.sqrt(2)
    assert result["lower"] == pytest.approx(math.tanh(z - half))
    assert result["upper"] == pytest.approx(math.tanh(z + half))
    reference = stats.pearsonr([1, 2, 3, 4, 5], [2, 4, 5, 4, 5]).confidence_interval()
    assert (result["lower"], result["upper"]) == pytest.approx((reference.low, reference.high))


def test_weighted_pearson_by_hand_and_on_the_effective_base():
    # Weights 1, 1, 2 → shares ¼, ¼, ½; means 2.25 and 2; covariance ¼·1.25·1 −
    # ¼·0.25·1 = 0.25; variances 0.6875 and 0.5: r = 0.25 / √0.34375.
    result = inference.correlate([1, 2, 3], [1, 3, 2], weights=[1, 1, 2])
    assert result["r"] == pytest.approx(0.25 / math.sqrt(0.6875 * 0.5))
    # Kish: (1 + 1 + 2)² / (1 + 1 + 4) = 8/3 effective pairs — too few for an
    # interval, and p on 8/3 − 2 df.
    assert result["n_effective"] == pytest.approx(8 / 3) and result["n"] == 3
    assert result["lower"] is None and result["upper"] is None
    r = result["r"]
    t = r * math.sqrt((8 / 3 - 2) / (1 - r * r))
    assert result["p_value"] == pytest.approx(2 * stats.t.sf(t, 8 / 3 - 2))
    # statsmodels' DescrStatsW(…, weights=w).corrcoef gives 0.8086274 here.
    x, y, w = [3, 4, 5, 4, 6, 7], B, [1, 2, 1, 3, 1, 2]
    assert inference.correlate(x, y, weights=w)["r"] == pytest.approx(0.8086273751610707)
    # Equal weights are no weights at all; a missing weight weighs 0.
    plain = inference.correlate(A[:6], B)
    equal = inference.correlate(A[:6], B, weights=[2.0] * 6)
    for key in ("r", "p_value", "lower", "upper"):
        assert equal[key] == pytest.approx(plain[key])
    assert inference.correlate([1, 2, 3, 9], [1, 3, 2, 0], weights=[1, 1, 2, None])["r"] == (
        pytest.approx(result["r"])
    )
    with pytest.raises(ValueError, match="negative"):
        inference.correlate([1, 2, 3], [1, 3, 2], weights=[1, -1, 2])


def test_rank_correlations():
    # Of the ten pairs of 1..5 against 3 1 2 5 4, seven are concordant and three
    # discordant: tau = (7 − 3) / 10.
    kendall = inference.correlate([1, 2, 3, 4, 5], [3, 1, 2, 5, 4], method="kendall")
    assert kendall["method"] == "Kendall tau-b" and kendall["tau"] == pytest.approx(0.4)
    assert kendall["p_value"] == pytest.approx(
        stats.kendalltau([1, 2, 3, 4, 5], [3, 1, 2, 5, 4]).pvalue
    )
    # Spearman: d = 2 −1 −1 1 −1, Σd² = 8, rho = 1 − 6·8 / (5·24) = 0.6.
    spearman = inference.correlate([1, 2, 3, 4, 5], [3, 1, 2, 5, 4], method="spearman")
    assert spearman["rho"] == pytest.approx(0.6) and "lower" not in spearman


def test_a_correlation_that_cannot_be_computed_says_why():
    with pytest.raises(NotTestable, match="at least three complete pairs; there are 2"):
        inference.correlate([1, 2, np.nan], [1, 2, 3])
    with pytest.raises(NotTestable, match="same value for everyone"):
        inference.correlate([1, 1, 1, 1], [1, 2, 3, 4], method="kendall")
    with pytest.raises(ValueError, match="method must be one of"):
        inference.correlate([1, 2, 3], [1, 2, 3], method="distance")


def test_correlation_matrix_pairwise_listwise_and_adjusted():
    frame = pd.DataFrame(
        {
            "a": [1, 2, 3, 4, 5, 6, np.nan],
            "b": [2, 1, 4, 3, 6, 5, 7],
            "c": [6, 5, 4, 3, 2, 2, 1],
        }
    )
    pairwise = inference.correlation_matrix(frame, ["a", "b", "c"], method="pearson")
    assert pairwise.n.loc["a", "b"] == 6 and pairwise.n.loc["b", "c"] == 7
    assert pairwise.coefficients.loc["b", "c"] == pytest.approx(
        stats.pearsonr(frame["b"], frame["c"]).statistic
    )
    assert pairwise.coefficients.loc["a", "a"] == 1.0
    listwise = inference.correlation_matrix(frame, ["a", "b", "c"], missing="listwise")
    assert set(listwise.n.to_numpy().ravel()) == {6}
    holm = inference.correlation_matrix(frame, ["a", "b", "c"], adjust="holm")
    upper = [("a", "b"), ("a", "c"), ("b", "c")]
    raw = [holm.p_values.loc[pair] for pair in upper]
    assert [holm.p_adjusted.loc[pair] for pair in upper] == pytest.approx(
        list(inference.adjust_p(raw, "holm"))
    )
    assert holm.p_adjusted.loc["b", "a"] == holm.p_adjusted.loc["a", "b"]
    assert list(holm.pairs()["x"]) == ["a", "a", "b"]
    with pytest.raises(ValueError, match="at least two variables"):
        inference.correlation_matrix(frame, ["a", "a"])
    # A pair that cannot be computed is a missing cell and a note, not a crash.
    flat = frame.assign(d=1.0)
    found = inference.correlation_matrix(flat, ["a", "d"], method="pearson")
    assert math.isnan(found.coefficients.loc["a", "d"])
    assert found.notes and "same value for everyone" in found.notes[0]


# ─── t-tests ─────────────────────────────────────────────────────────────────


def test_independent_t_tests_agree_with_scipy_and_pingouin():
    welch = inference.ttest_independent(A, B)
    reference = stats.ttest_ind(A, B, equal_var=False)
    assert welch.t == pytest.approx(reference.statistic)
    assert welch.p_value == pytest.approx(reference.pvalue)
    assert welch.df == pytest.approx(10.95621366505663)  # pingouin's dof
    interval = reference.confidence_interval()
    assert (welch.lower, welch.upper) == pytest.approx((interval.low, interval.high))
    assert welch.difference == pytest.approx(34 / 7 - 44 / 6)
    # Pooled SD √(((6·1.476) + (5·1.467)) / 11); pingouin: d −1.925566, g −1.791224.
    assert welch.cohens_d == pytest.approx(-1.925565771471926)
    assert welch.hedges_g == pytest.approx(-1.925565771471926 * (1 - 3 / (4 * 13 - 9)))
    assert welch.hedges_g == pytest.approx(-1.791224, abs=1e-6)
    student = inference.ttest_independent(A, B, equal_var=True)
    reference = stats.ttest_ind(A, B)
    assert (student.t, student.p_value, student.df) == pytest.approx(
        (reference.statistic, reference.pvalue, 11)
    )
    interval = reference.confidence_interval()
    assert (student.lower, student.upper) == pytest.approx((interval.low, interval.high))
    assert student.method == "Student's t-test (equal variances)"


def test_paired_and_one_sample_t_tests():
    paired = inference.ttest_paired(A[:6], B)
    reference = stats.ttest_rel(A[:6], B)
    assert (paired.t, paired.p_value, paired.df) == pytest.approx(
        (reference.statistic, reference.pvalue, 5)
    )
    # Differences −3 −3 −3 −2 −3 −1: mean −2.5, SD √0.7, d_z = −2.5 / √0.7.
    assert paired.difference == pytest.approx(-2.5)
    assert paired.cohens_d == pytest.approx(-2.5 / math.sqrt(0.7))
    interval = reference.confidence_interval()
    assert (paired.lower, paired.upper) == pytest.approx((interval.low, interval.high))
    # Only complete pairs count.
    assert inference.ttest_paired([*A[:6], 5], [*B, np.nan]).t == pytest.approx(paired.t)
    one = inference.ttest_one_sample(A, 4)
    reference = stats.ttest_1samp(A, 4)
    assert (one.t, one.p_value, one.df) == pytest.approx((reference.statistic, reference.pvalue, 6))
    assert one.difference == pytest.approx(34 / 7 - 4)
    assert one.cohens_d == pytest.approx((34 / 7 - 4) / np.std(A, ddof=1))
    # CI of the difference: the CI of the mean, shifted by the test value.
    interval = reference.confidence_interval()
    assert (one.lower + 4, one.upper + 4) == pytest.approx((interval.low, interval.high))


def test_t_tests_explain_what_they_cannot_test():
    with pytest.raises(NotTestable, match="at least two values in each group; East has 1"):
        inference.ttest_independent([1, 2, 3], [4], names=("West", "East"))
    with pytest.raises(NotTestable, match="neither group varies"):
        inference.ttest_independent([2, 2, 2], [5, 5])
    with pytest.raises(NotTestable, match="differ by the same amount"):
        inference.ttest_paired([1, 2, 3], [2, 3, 4])
    with pytest.raises(NotTestable, match="every value is the same"):
        inference.ttest_one_sample([3, 3, 3], 1)
    with pytest.raises(NotTestable, match="at least two values; there are 1"):
        inference.ttest_one_sample([3, np.nan], 1)


def test_decimal_values_that_do_not_vary_are_refused_as_whole_numbers_are():
    """Three answers of 1.4 have a variance of 7e-32, not 0 — their mean is
    1.4000000000000001 — and 1.1 − 1.0 and 4.1 − 4.0 differ by 4e-16. Read as
    spread, that rounding gave t = −2.25e15 and p = 2e-61 for [1.4]*3 against
    [1.9]*3. It is no spread: each test refuses as it does for [2, 2, 2]."""

    assert np.var([1.4] * 3, ddof=1) > 0  # the rounding the tests must see through
    with pytest.raises(NotTestable, match="neither group varies"):
        inference.ttest_independent([1.4] * 3, [1.9] * 3)
    with pytest.raises(NotTestable, match="neither group varies"):
        inference.ttest_independent([1.4] * 3, [1.9] * 3, equal_var=True)
    with pytest.raises(NotTestable, match="differ by the same amount"):
        inference.ttest_paired([1.0, 2.0, 3.0, 4.0, 5.0], [1.1, 2.1, 3.1, 4.1, 5.1])
    with pytest.raises(NotTestable, match="every value is the same"):
        inference.ttest_one_sample([0.7] * 3, 0)
    with pytest.raises(NotTestable, match="no group varies"):
        inference.anova([[1.4] * 3, [1.9] * 3])
    with pytest.raises(NotTestable, match="every value in group 1 is the same"):
        inference.welch_anova([[1.4] * 3, [2.0, 3.1, 2.6, 3.3], [2.2, 3.0, 2.8]])
    with pytest.raises(NotTestable, match="no group varies"):
        inference.posthoc([[1.4] * 3, [1.9] * 3], ["a", "b"], "tukey")
    howell = inference.posthoc([[1.4] * 3, [1.9] * 3, [2.0, 2.5, 3.0]], list("abc"), "games_howell")
    assert howell.notes == ["a vs b: neither group varies"]
    assert howell.table["p_value"].isna().tolist() == [True, False, False]
    # 0.1 + 0.2 + 0.3 is 0.6000000000000001: the same index summed in another order.
    with pytest.raises(NotTestable, match="same value for everyone"):
        inference.correlate([0.6, 0.1 + 0.2 + 0.3, 0.6, 0.6], [1, 2, 3, 4])
    with pytest.raises(NotTestable, match="same value for all the weight"):
        inference.correlate([0.6, 0.1 + 0.2 + 0.3, 0.6, 5.0], [1, 2, 3, 4], weights=[1, 1, 1, 0])
    # A real spread, however small beside the values, is still a spread.
    found = inference.ttest_one_sample([1e6, 1e6 + 1e-3, 1e6 + 2e-3], 1e6)
    assert found.t == pytest.approx(math.sqrt(3), rel=1e-6)  # mean 1e-3 over SE 1e-3/√3
    assert inference.no_spread([1e-12, 2e-12, 3e-12]) is False
    assert inference.no_spread([]) and inference.no_spread([0.0, 0.0])


def test_a_flat_decimal_group_in_the_tables_is_explained_not_tested():
    rng = np.random.default_rng(4)
    frame = pd.DataFrame(
        {
            "score": np.round(rng.normal(3, 1, 37), 1).tolist() + [1.4] * 3,
            "region": [1] * 19 + [2] * 18 + [3] * 3,
        }
    )
    variables = VariableMap()
    variables.add_many(
        [
            Variable("score", "interval", label="Score"),
            Variable("region", "nominal", label="Region", labels={1: "N", 2: "S", 3: "E"}),
        ]
    )
    data = SurveyData(frame=frame, variables=variables)
    table = data.report.means("score", by="region", method="welch_anova", posthoc="games_howell")
    assert table.stats["Test"] == (
        "not run: Welch's ANOVA weighs each group by its variance, and every value in E is the same"
    )
    # A pair with one flat group is Welch's test against a group of SD 0: on
    # the other group's n − 1 df, exactly as for a group of whole numbers.
    pairs = table.posthoc_table.to_frame()
    assert pairs["df"].tolist()[1:] == [18.0, 17.0]
    flat = data.with_frame(
        pd.DataFrame({"score": [1.4] * 3 + [1.9] * 3, "region": [1] * 3 + [2] * 3})
    )
    assert flat.report.ttest("score", by="region").stats["Test"] == (
        "not run: neither group varies, so there is no spread to test the difference against"
    )


# ─── several groups ──────────────────────────────────────────────────────────


def test_anova_and_welch_anova():
    found = inference.anova([A, B, C])
    reference = stats.f_oneway(A, B, C)
    assert (found.statistic, found.p_value) == pytest.approx(
        (reference.statistic, reference.pvalue)
    )
    assert (found.df, found.df2) == (2, 18)
    # SS between 21.744048, SS within 32.065476 (pingouin's detailed table).
    assert found.effect == pytest.approx(21.744048 / (21.744048 + 32.065476), abs=1e-7)
    welch = inference.welch_anova([A, B, C])
    # pingouin.welch_anova: F 6.079988 on 2 and 11.786643 df, p 0.015336.
    assert welch.statistic == pytest.approx(6.079988, abs=1e-6)
    assert welch.df2 == pytest.approx(11.786643, abs=1e-6)
    assert welch.p_value == pytest.approx(0.015336, abs=1e-6)
    with pytest.raises(NotTestable, match="East has 1"):
        inference.welch_anova([A, B, [4]], ["North", "South", "East"])
    with pytest.raises(NotTestable, match="every value in East is the same"):
        inference.welch_anova([A, B, [4, 4]], ["North", "South", "East"])
    with pytest.raises(NotTestable, match="no group varies"):
        inference.anova([[1, 1], [2, 2]])


def test_rank_tests_of_several_groups():
    found = inference.kruskal([A, B, C])
    reference = stats.kruskal(A, B, C)
    assert found.statistic == pytest.approx(reference.statistic)
    assert found.effect == pytest.approx(reference.statistic / 20)  # ε² = H / (N − 1)
    two = inference.mannwhitney(A, B)
    u = stats.mannwhitneyu(A, B, alternative="two-sided").statistic
    assert two.statistic == u and two.effect == pytest.approx(2 * u / 42 - 1)
    with pytest.raises(NotTestable, match="every value is the same"):
        inference.kruskal([[1, 1], [1, 1, 1]])


def test_tukey_matches_scipy_and_pingouin():
    found = inference.posthoc([A, B, C], ["A", "B", "C"], "tukey")
    reference = stats.tukey_hsd(A, B, C)
    for row, (i, j) in zip(found.table.itertuples(), [(0, 1), (0, 2), (1, 2)], strict=True):
        assert row.p_value == pytest.approx(reference.pvalue[i, j], abs=1e-6)
        assert row.difference == pytest.approx(reference.statistic[i, j])
        interval = reference.confidence_interval()
        assert row.lower == pytest.approx(interval.low[i, j], abs=1e-5)
        assert row.upper == pytest.approx(interval.high[i, j], abs=1e-5)
    # pingouin.pairwise_tukey: p 0.009810, 0.049302, 0.596795.
    assert list(found.table["p_adjusted"]) == pytest.approx(
        [0.009810, 0.049302, 0.596795], abs=1e-6
    )
    assert found.name == "Tukey HSD" and found.significant() == 2


def test_games_howell_matches_pingouin():
    found = inference.posthoc([A, B, C], ["A", "B", "C"], "games_howell")
    # pingouin.pairwise_gameshowell: df and p per pair.
    assert list(found.table["df"]) == pytest.approx([10.956214, 12.875284, 11.692449], abs=1e-6)
    assert list(found.table["p_value"]) == pytest.approx([0.012931, 0.066431, 0.585413], abs=1e-6)
    # q = √2 |t| with t the Welch statistic of the pair.
    assert found.table["statistic"][0] == pytest.approx(
        math.sqrt(2) * abs(stats.ttest_ind(A, B, equal_var=False).statistic)
    )
    single = inference.posthoc([A, B, [4]], ["A", "B", "C"], "games_howell")
    assert single.notes == ["A vs C: C has one value", "B vs C: C has one value"]
    assert single.table["p_value"].isna().tolist() == [False, True, True]


def test_dunn_matches_scikit_posthocs():
    holm = inference.posthoc([A, B, C], ["A", "B", "C"], "dunn", adjust="holm")
    # scikit_posthocs.posthoc_dunn: unadjusted and Holm-adjusted p.
    assert list(holm.table["p_value"]) == pytest.approx([0.006588, 0.043557, 0.387176], abs=1e-6)
    assert list(holm.table["p_adjusted"]) == pytest.approx([0.019763, 0.087115, 0.387176], abs=1e-6)
    bonferroni = inference.posthoc([A, B, C], ["A", "B", "C"], "dunn", adjust="bonferroni")
    assert list(bonferroni.table["p_adjusted"]) == pytest.approx(
        list(np.minimum(1, 3 * holm.table["p_value"]))
    )
    assert holm.name == "Dunn's test (Holm)" and holm.symbol == "z"
    with pytest.raises(ValueError, match="holm' or 'bonferroni"):
        inference.posthoc([A, B], ["A", "B"], "dunn", adjust="fdr_bh")
    with pytest.raises(NotTestable, match="at least two groups"):
        inference.posthoc([A, []], ["A", "B"], "tukey")


# ─── Fisher's exact test ─────────────────────────────────────────────────────


def test_fisher_two_by_two_is_the_lady_tasting_tea():
    found = inference.fisher_exact([[3, 1], [1, 3]])
    # The hypergeometric probabilities of a = 0..4 are 1, 16, 36, 16, 1 over 70;
    # those no more likely than the observed 16/70 sum to 34/70.
    assert found["p_value"] == pytest.approx(34 / 70)
    # R's fisher.test: odds ratio (conditional MLE) 6.408309.
    assert found["odds_ratio"] == pytest.approx(6.408309, rel=1e-5)
    # The exact interval: at each end the observed a = 3 is in the 2.5 % tail of
    # Fisher's noncentral hypergeometric distribution.
    tail = stats.nchypergeom_fisher
    assert tail.sf(2, 8, 4, 4, found["lower"]) == pytest.approx(0.025, abs=1e-6)
    assert tail.cdf(3, 8, 4, 4, found["upper"]) == pytest.approx(0.025, abs=1e-6)
    assert inference.fisher_exact([[5, 0], [0, 5]])["odds_ratio"] == float("inf")
    with pytest.raises(NotTestable, match="fewer than two rows or columns"):
        inference.fisher_exact([[3, 0], [0, 0]])
    with pytest.raises(ValueError, match="whole, non-negative counts"):
        inference.fisher_exact([[1.5, 2], [3, 4]])


def _ffh_brute_force(table: list[list[int]]) -> float:
    """Every table with these margins, by brute force over the free cells."""
    counts = np.array(table)
    rows, cols = counts.sum(axis=1), counts.sum(axis=0)
    total = counts.sum()

    def probability(t: np.ndarray) -> float:
        top = sum(math.lgamma(v + 1) for v in [*rows, *cols])
        bottom = math.lgamma(total + 1) + sum(math.lgamma(v + 1) for v in t.ravel())
        return math.exp(top - bottom)

    observed = probability(counts)
    mass = 0.0
    r, c = counts.shape
    ranges = [range(min(rows[i], cols[j]) + 1) for i in range(r - 1) for j in range(c - 1)]
    for free in itertools.product(*ranges):
        t = np.zeros((r, c), dtype=int)
        t[: r - 1, : c - 1] = np.array(free).reshape(r - 1, c - 1)
        t[: r - 1, c - 1] = rows[: r - 1] - t[: r - 1, : c - 1].sum(axis=1)
        t[r - 1, :] = cols - t[: r - 1, :].sum(axis=0)
        if (t < 0).any():
            continue
        if probability(t) <= observed * (1 + 1e-7):
            mass += probability(t)
    return mass


def test_fisher_freeman_halton_is_exact_when_it_can_be_and_seeded_when_not(monkeypatch):
    table = [[3, 1, 0], [1, 3, 2], [0, 2, 4]]
    exact = inference.fisher_exact(table)
    assert exact["exact"] and exact["method"] == "Fisher-Freeman-Halton exact test"
    assert exact["p_value"] == pytest.approx(_ffh_brute_force(table))
    # For a 2 × 2 the enumeration is Fisher's own p.
    assert inference.fisher_exact([[3, 1, 0], [1, 3, 0]])["p_value"] == pytest.approx(34 / 70)
    # Past the limit the p is sampled — from a fixed seed, so it is the same p
    # every time, and within a few standard errors of the exact one.
    monkeypatch.setattr(inference, "FISHER_EXACT_LIMIT", 10)
    sampled = inference.fisher_exact(table)
    assert not sampled["exact"] and sampled["samples"] == 20_000
    assert sampled == inference.fisher_exact(table)
    assert abs(sampled["p_value"] - exact["p_value"]) < 4 * sampled["p_error"]


# ─── missing codes ───────────────────────────────────────────────────────────


def _coded() -> SurveyData:
    """Ten respondents: a 99 (Don't know) in sat, a 9 (Refused) in grp, a weight."""
    frame = pd.DataFrame(
        {
            "grp": [1, 1, 1, 2, 2, 2, 3, 3, 3, 9],
            "sat": [1, 2, 3, 4, 5, 99, 2, 3, 4, 3],
            "sat2": [2, 2, 4, 4, 4, 5, 3, 3, 5, 99],
            "ans": [1, 2, 1, 2, 2, 2, 1, 1, 2, 1],
            "w": [1, 2, 1, 1, 3, 1, 1, 1, 2, 1.0],
        }
    )
    variables = VariableMap()
    variables.add_many(
        [
            Variable(
                "grp",
                "nominal",
                label="Group",
                labels={1: "North", 2: "South", 3: "East"},
                missing_values=(9,),
                missing_labels={9: "Refused"},
            ),
            Variable(
                "sat",
                "interval",
                label="Satisfaction",
                missing_values=(99,),
                missing_labels={99: "Don't know"},
            ),
            Variable("sat2", "interval", label="Satisfaction later", missing_values=(99,)),
            Variable("ans", "nominal", label="Answer", labels={1: "Yes", 2: "No"}),
            Variable("w", "ratio", label="Weight"),
        ]
    )
    return SurveyData(frame=frame, variables=variables)


def test_missing_codes_are_left_out_and_counted():
    data = _coded()
    frame, left_out = inference.without_missing_codes(
        data.frame, ["grp", "sat", "ans"], data.variables
    )
    assert left_out == {"grp": [(9, 1)], "sat": [(99, 1)]}
    assert frame["sat"].isna().sum() == 1 and frame["grp"].isna().sum() == 1
    assert frame["ans"].equals(data.frame["ans"]) and data.frame["sat"].max() == 99
    assert (
        inference.missing_codes_note(left_out, data.variables)
        == "Group: 1 (9 = Refused); Satisfaction: 1 (99 = Don't know)"
    )
    assert inference.without_missing_codes(data.frame, ["sat"], None)[1] == {}


# ─── the tables ──────────────────────────────────────────────────────────────


def test_group_means_by_default_are_exactly_what_they_were():
    """The automatic test reads the data as it always has — the 99 included."""
    data = _coded()
    table = data.report.means("sat", by="grp")
    assert table.to_frame()["N"].tolist() == [3, 3, 3, 1]
    groups = [data.frame.loc[data.frame["grp"] == g, "sat"].to_numpy() for g in (1, 2, 3, 9)]
    f = stats.f_oneway(*groups)
    # The numbers are what they were; the 99 and the 9 counted in them are now named.
    counted = (
        "Satisfaction: 1 (99 = Don't know); Group: 1 (9 = Refused); "
        "run Missing values first to leave them out"
    )
    assert table.stats == {"F": round(f.statistic, 3), "p": round(f.pvalue, 4), "N": 10} | {
        "Variable": "Satisfaction",
        "Missing codes counted as answers": counted,
    }
    assert table.posthoc_table is None
    assert data.report.means("sat", by="grp", method="auto").stats == table.stats
    # With the test off a chosen method changes nothing (the flow warns it is ignored).
    off = data.report.means("sat", by="grp", test=False, method="anova").to_frame()
    assert off.equals(data.report.means("sat", by="grp", test=False).to_frame())


def test_group_means_with_a_test_and_post_hoc_chosen_by_hand():
    data = _coded()
    table = data.report.means("sat", by="grp", method="anova", posthoc="tukey")
    frame = table.to_frame()
    # The 99 and the Refused group are left out of the table and the test.
    assert frame["Group"].tolist() == ["North", "South", "East"]
    assert frame["N"].tolist() == [3, 2, 3] and frame["Mean"].tolist() == [2.0, 4.5, 3.0]
    stats_ = table.stats
    f = stats.f_oneway([1, 2, 3], [4, 5], [2, 3, 4])
    assert stats_["Test"] == "One-way ANOVA" and stats_["F"] == round(f.statistic, 3)
    assert stats_["df"] == "2, 5" and stats_["p"] == round(f.pvalue, 4)
    assert stats_["Post-hoc"] == "Tukey HSD: 0 of 3 pairs differ at p < 0.05"
    assert stats_["Missing codes left out"] == (
        "Satisfaction: 1 (99 = Don't know); Group: 1 (9 = Refused)"
    )
    pairs = table.posthoc_table.to_frame()
    assert pairs["Pair"].tolist() == ["North vs South", "North vs East", "South vs East"]
    reference = stats.tukey_hsd([1, 2, 3], [4, 5], [2, 3, 4])
    assert pairs["p"].tolist() == [
        round(reference.pvalue[0, 1], 4),
        round(reference.pvalue[0, 2], 4),
    ] + [round(reference.pvalue[1, 2], 4)]
    markdown = table.to_markdown()
    assert "**Post-hoc: Tukey HSD**" in markdown and markdown.index(
        "| North vs South"
    ) > markdown.index("Missing codes left out")
    assert "<caption>Post-hoc: Tukey HSD</caption>" in table.to_html()


def test_group_means_tests_that_do_not_fit_say_so():
    data = _coded()
    three = data.report.means("sat", by="grp", method="welch").stats
    assert three["Test"] == (
        "not run: Welch's t-test (unequal variances) compares two groups and Group has 3 "
        "— choose anova or welch_anova"
    )
    two = data.with_frame(data.frame[data.frame["grp"].isin([1, 2])])
    welch = two.report.means("sat", by="grp", method="welch").stats
    reference = stats.ttest_ind([1, 2, 3], [4, 5], equal_var=False)
    assert welch["t"] == round(reference.statistic, 3) and welch["p"] == round(reference.pvalue, 4)
    dunn = data.report.means("sat", by="grp", method="kruskal", posthoc="dunn", adjust="bonferroni")
    assert dunn.stats["Post-hoc"].startswith("Dunn's test (Bonferroni): ")
    assert list(dunn.posthoc_table.to_frame().columns) == [
        "Pair",
        "Mean rank difference",
        "z",
        "p (unadjusted)",
        "p (Bonferroni)",
    ]
    with pytest.raises(ValueError, match="Tukey HSD follows One-way ANOVA: method='anova'"):
        data.report.means("sat", by="grp", method="kruskal", posthoc="tukey").to_frame()
    with pytest.raises(ValueError, match="method must be one of"):
        data.report.means("sat", by="grp", method="ttest").to_frame()
    # Weighted: means weighted, the test is not — as the automatic one.
    weighted = data.with_weight("w").report.means("sat", by="grp", method="anova").stats
    assert weighted["Note"] == "means, SD and medians are weighted; N and the test are not"


def test_group_means_export_puts_the_pairs_on_a_second_sheet(tmp_path):
    table = _coded().report.means("sat", by="grp", method="welch_anova", posthoc="games_howell")
    path = table.export_xlsx(tmp_path / "means.xlsx")
    sheets = pd.read_excel(path, sheet_name=None)
    assert list(sheets) == ["Table", "Post-hoc"] and len(sheets["Post-hoc"]) == 3


def test_crosstab_fisher_on_a_two_by_two():
    data = _coded()
    two = data.with_frame(data.frame[data.frame["grp"].isin([1, 2])])
    table = two.report.crosstab("grp", "ans", method="fisher")
    stats_ = table.stats
    # North: Yes 2, No 1; South: Yes 0, No 3.
    reference = stats.fisher_exact([[2, 1], [0, 3]])
    assert stats_["Test"] == "Fisher's exact test" and stats_["p"] == round(reference.pvalue, 4)
    assert stats_["Odds ratio"] == "∞" and stats_["N"] == 6
    assert stats_["Odds ratio of"] == "Yes (vs No) for North over South"
    assert stats_["OR 95% CI"].endswith("– ∞")
    # The chi-square default is untouched.
    assert "χ²" in two.report.crosstab("grp", "ans").stats


def test_crosstab_fisher_counts_people_and_leaves_missing_codes_out():
    data = _coded().with_weight("w")
    table = data.report.crosstab("grp", "ans", method="fisher")
    stats_ = table.stats
    # Without the Refused respondent: 2 1 / 0 3 / 2 1 — exact over every table.
    assert stats_["p"] == round(inference.fisher_exact([[2, 1], [0, 3], [2, 1]])["p_value"], 4)
    assert stats_["p method"] == "exact, over every table with these margins"
    assert stats_["N"] == 9 and stats_["Weighted N"] == 13.0 and stats_["Weight"] == "w"
    assert "counts respondents" in stats_["Base"]
    assert stats_["Missing codes left out"] == "Group: 1 (9 = Refused)"
    assert "Refused" not in table.to_frame().iloc[:, 0].tolist()
    # Turned off, nothing changes: the table is the chi-square one, codes and all.
    off = data.report.crosstab("grp", "ans", method="fisher", test=False)
    assert off.to_frame().equals(data.report.crosstab("grp", "ans", test=False).to_frame())


def test_t_test_table_for_each_design():
    data = _coded()
    independent = data.report.ttest("sat", by="grp", groups=[1, "2"])
    frame = independent.to_frame()
    assert list(frame.columns) == ["Group", "N", "Mean", "SD", "SE"]
    assert frame["Group"].tolist() == ["North", "South"] and frame["N"].tolist() == [3, 2]
    reference = stats.ttest_ind([1, 2, 3], [4, 5], equal_var=False)
    found = independent.stats
    assert found["Test"] == "Welch's t-test (unequal variances)"
    assert found["t"] == round(reference.statistic, 3) and found["p"] == round(reference.pvalue, 4)
    assert found["Difference"] == "North − South" and found["Mean difference"] == -2.5
    assert found["N"] == 5 and "Hedges' g" in found
    assert found["Missing codes left out"] == (
        "Satisfaction: 1 (99 = Don't know); Group: 1 (9 = Refused)"
    )
    student = data.report.ttest("sat", by="grp", groups=[1, 2], variances="student").stats
    assert student["df"] == 3

    paired = data.report.ttest("sat", kind="paired", other="sat2")
    assert paired.to_frame()["Variable"].tolist() == [
        "Satisfaction",
        "Satisfaction later",
        "Difference",
    ]
    keep = (data.frame["sat"] != 99) & (data.frame["sat2"] != 99)
    reference = stats.ttest_rel(data.frame.loc[keep, "sat"], data.frame.loc[keep, "sat2"])
    assert paired.stats["t"] == round(reference.statistic, 3) and paired.stats["N"] == 8
    assert paired.stats["Incomplete pairs left out"] == 2

    one = data.with_weight("w").report.ttest("sat", kind="one_sample", mu=3)
    reference = stats.ttest_1samp([1, 2, 3, 4, 5, 2, 3, 4, 3], 3)
    assert list(one.stats)[:3] == ["Test", "Test value", "t"]
    assert one.stats["t"] == round(reference.statistic, 3) and one.stats["N"] == 9
    assert one.stats["Weight"] == "unweighted (the weight 'w' is not applied)"


def test_t_test_refuses_clearly_and_explains_degenerate_groups():
    data = _coded()
    with pytest.raises(ValueError, match=r"Group has 3 groups \(1 = North, 2 = South, 3 = East\)"):
        data.report.ttest("sat", by="grp").to_frame()
    with pytest.raises(ValueError, match="'grp' has no group 7; its groups are 1 = North"):
        data.report.ttest("sat", by="grp", groups=[1, 7]).to_frame()
    with pytest.raises(ValueError, match=r"9 \(Refused\) is a missing code of Group, not a group"):
        data.report.ttest("sat", by="grp", groups=[1, 9]).to_frame()
    # The same group twice was a t of 0 on its respondents counted twice.
    for same in ([1, 1], [1, "1"], [2.0, 2]):
        with pytest.raises(ValueError, match="Group A and Group B are both"):
            data.report.ttest("sat", by="grp", groups=same).to_frame()
    with pytest.raises(ValueError, match="both 1 = North; a t-test compares two different"):
        data.report.ttest("sat", by="grp", groups=[1, 1]).to_frame()
    # A group of the codebook without anyone in it is explained, not refused.
    lonely = data.with_frame(data.frame[data.frame["grp"] != 3])
    empty = lonely.report.ttest("sat", by="grp", groups=[1, 3]).stats
    assert empty["Test"] == "not run: a t-test needs at least two values in each group; East has 0"
    with pytest.raises(ValueError, match="needs `other`"):
        data.report.ttest("sat", kind="paired").to_frame()


def test_correlation_matrix_table_matrix_and_pairs():
    data = _coded()
    table = data.report.correlation_matrix(["sat", "sat2", "ans"], method="pearson")
    frame = table.to_frame()
    assert list(frame.columns) == ["Variable", "Satisfaction", "Satisfaction later", "Answer"]
    r = table.result.coefficients.loc["sat2", "sat"]
    p = table.result.p_values.loc["sat2", "sat"]
    marks = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
    assert frame.iloc[1, 1] == f"{r:.3f}{marks}" and frame.iloc[0, 1] == "—"
    assert frame.iloc[0, 2] == ""
    stats_ = table.stats
    assert stats_["Method"] == "Pearson correlation" and stats_["N"] == "8–9"
    assert stats_["p adjustment"] == "none"
    pairs = data.report.correlation_matrix(
        ["sat", "sat2", "ans"], layout="pairs", adjust="fdr_bh", missing="listwise"
    )
    frame = pairs.to_frame()
    assert list(frame.columns) == [
        "Variable 1",
        "Variable 2",
        "rho",
        "p",
        "p (Benjamini-Hochberg)",
        "N",
    ]
    assert frame["N"].tolist() == [8, 8, 8]
    assert pairs.stats["p adjustment"] == "Benjamini-Hochberg (false discovery rate), over 3 pairs"
    assert pairs.stats["Missing"].startswith("listwise")


def test_correlation_matrix_weights_pearson_and_says_the_ranks_are_not():
    data = _coded().with_weight("w")
    pearson = data.report.correlation_matrix(["sat", "sat2"], method="pearson")
    keep = (data.frame["sat"] != 99) & (data.frame["sat2"] != 99)
    expected = inference.correlate(
        data.frame.loc[keep, "sat"], data.frame.loc[keep, "sat2"], weights=data.frame.loc[keep, "w"]
    )
    assert pearson.result.coefficients.loc["sat", "sat2"] == pytest.approx(expected["r"])
    assert pearson.stats["Weight"] == "w" and "Kish" in pearson.stats["Base"]
    spearman = data.report.correlation_matrix(["sat", "sat2"]).stats
    assert spearman["Weight"] == "unweighted (the weight 'w' is not applied)"


def test_analysis_correlation_and_compare_groups():
    data = _coded()
    keep = (data.frame["sat"] != 99) & (data.frame["sat2"] != 99)
    found = data.analysis.correlation("sat", "sat2")
    assert found["r"] == pytest.approx(
        stats.pearsonr(data.frame.loc[keep, "sat"], data.frame.loc[keep, "sat2"]).statistic
    )
    assert found["n"] == 8 and "missing_codes" in found and "weight" not in found
    weighted = data.with_weight("w").analysis.correlation("sat", "sat2")
    assert weighted["weight"] == "w" and weighted["n_effective"] < 8
    kendall = data.with_weight("w").analysis.correlation("sat", "sat2", method="kendall")
    assert kendall["weight"] == "unweighted (the weight 'w' is not applied)"
    flat = data.with_frame(data.frame.assign(sat2=3))
    assert flat.analysis.correlation("sat", "sat2")["note"].startswith("a variable has the same")

    groups = data.analysis.compare_groups("sat", "grp", posthoc="dunn")
    reference = stats.kruskal([1, 2, 3], [4, 5], [2, 3, 4])
    assert groups["statistic"] == pytest.approx(reference.statistic) and groups["groups"] == 3.0
    assert groups["posthoc"] == "Dunn's test (Holm)"
    dunn = inference.posthoc([[1, 2, 3], [4, 5], [2, 3, 4]], ["North", "South", "East"], "dunn")
    first = dunn.table.iloc[0]
    assert groups["North vs South"] == f"z = {first.statistic:.3f}, p = {first.p_adjusted:.4f}"
    pair = data.with_frame(data.frame[data.frame["grp"].isin([1, 2])])
    assert pair.analysis.compare_groups("sat", "grp", posthoc="dunn")["posthoc"].startswith(
        "not needed"
    )
    with pytest.raises(ValueError, match="Dunn's test follows Kruskal-Wallis"):
        data.analysis.compare_groups("sat", "grp", test="mannwhitney", posthoc="dunn")


def test_undefined_cells_print_blank_in_every_stat_table():
    """A pair that could not be compared, a correlation with a constant and the
    SD of one answer are NaN in to_frame() and blank when printed — never
    "nan", "NaN" or "None" in a report or a Studio preview."""

    variables = VariableMap()
    variables.add_many(
        [
            Variable("y", "interval", label="Y"),
            Variable("y2", "interval", label="Y2"),
            Variable("y3", "interval", label="Y3"),
            Variable("g", "nominal", label="G", labels={1: "One", 2: "Two", 3: "Three"}),
        ]
    )
    frame = pd.DataFrame(
        {
            "y": [1, 2, 3, 4, 5, 6, 7],
            "y2": [2, 1, 4, 3, 6, 5, 7],
            "y3": [1.0] * 7,
            "g": [1, 1, 1, 2, 2, 2, 3],
        }
    )
    data = SurveyData(frame=frame, variables=variables)
    means = data.report.means("y", by="g", method="welch_anova", posthoc="games_howell")
    pairs = data.report.correlation_matrix(["y", "y2", "y3"], layout="pairs")
    lonely = data.with_frame(frame[frame["g"] != 1])
    tables = [
        means.posthoc_table,
        pairs,
        data.report.ttest("y", by="g", groups=[1, 3]),
        lonely.report.ttest("y", by="g", groups=[1, 2]),
        data.with_frame(frame.iloc[:1]).report.ttest("y", kind="one_sample"),
    ]
    for table in tables:
        for text in (table.to_markdown(), table.to_html()):
            assert "nan" not in text.lower() and "None" not in text
    assert "nan" not in means.to_markdown().split("**Post-hoc")[1].lower()
    assert "| One vs Three | -5.0 |  |  |  |  |  |" in means.posthoc_table.to_markdown()
    assert "| Y | Y3 |  |  | 7 |" in pairs.to_markdown()
    assert "<caption>Post-hoc: Games-Howell</caption>" in means.posthoc_table.to_html()
    # The frame keeps the numbers a program reads: missing, not an empty string.
    assert means.posthoc_table.to_frame()["q"].isna().tolist() == [False, True, True]
    assert pairs.to_frame()["rho"].isna().tolist() == [False, True, True]
    assert lonely.report.ttest("y", by="g", groups=[1, 2]).to_frame()["Mean"].isna()[0]


def test_a_t_test_refuses_multiple_choice_groups_and_answers_with_the_way_out():
    variables = VariableMap()
    variables.add_many(
        [
            Variable("aware", "nominal", label="Aware of", labels={1: "Acme", 2: "Globex"}),
            Variable("age", "ratio", label="Age"),
        ]
    )
    frame = pd.DataFrame({"age": [20, 30, 40, 50], "aware": [[1], [1, 2], [2], [2]]})
    data = SurveyData(frame=frame, variables=variables)
    # It raised TypeError "unhashable type: 'list'" before.
    with pytest.raises(ValueError, match=r"Aware of \('aware'\) holds several answers per "):
        data.report.ttest("age", by="aware", groups=[1, 2]).to_frame()
    with pytest.raises(ValueError, match="its groups overlap .* Run Explode multiple choice"):
        data.report.ttest("age", by="aware").to_frame()
    with pytest.raises(ValueError, match="which have no mean"):
        data.report.ttest("aware", kind="one_sample").to_frame()


def test_the_defaults_say_when_they_count_missing_codes_as_answers():
    """The defaults read a 99 "Don't know" as an answer so that a stored flow
    keeps its numbers, and a test chosen by hand leaves it out — so the same
    Kruskal-Wallis gave two results with nothing saying why. The defaults now
    name the codes they counted; after Missing values there are none to name."""

    data = _coded()
    remedy = "; run Missing values first to leave them out"
    both = "Satisfaction: 1 (99 = Don't know); Group: 1 (9 = Refused)" + remedy
    kruskal = data.analysis.kruskal("sat", "grp")
    groups = [data.frame.loc[data.frame["grp"] == g, "sat"] for g in (1, 2, 3, 9)]
    assert kruskal["statistic"] == pytest.approx(stats.kruskal(*groups).statistic)
    assert kruskal["missing_codes_counted"] == both
    two = data.with_frame(data.frame[data.frame["grp"].isin([1, 2])])
    assert two.analysis.mannwhitney("sat", "grp")["missing_codes_counted"] == (
        "Satisfaction: 1 (99 = Don't know)" + remedy
    )
    # sat is 99 beside a sat2 of 5 once, and sat2 is 99 beside a sat of 3 once.
    assert data.analysis.spearman("sat", "sat2")["missing_codes_counted"] == (
        "Satisfaction: 1 (99 = Don't know); Satisfaction later: 1 (99)" + remedy
    )
    crosstab = data.report.crosstab("grp", "ans")
    assert "9" in crosstab.to_frame().iloc[:, 0].tolist()  # a row of its own, unlabelled
    assert crosstab.stats["Missing codes counted as answers"] == "Group: 1 (9 = Refused)" + remedy
    assert (
        "Missing codes counted as answers" in data.report.crosstab("grp", "ans", test=False).stats
    )
    fisher = data.report.crosstab("grp", "ans", method="fisher").stats
    assert "Missing codes counted as answers" not in fisher and "Missing codes left out" in fisher
    chosen = data.report.means("sat", by="grp", method="kruskal").stats
    assert "Missing codes counted as answers" not in chosen
    # Missing values first: nothing is counted, and nothing is said.
    clean = data.apply_missing_values()
    assert "missing_codes_counted" not in clean.analysis.kruskal("sat", "grp")
    assert "Missing codes counted as answers" not in clean.report.means("sat", by="grp").stats
    assert "Missing codes counted as answers" not in clean.report.crosstab("grp", "ans").stats


def test_a_tiny_p_is_never_printed_as_zero():
    """A test that found something reads p = 1.13e-24, not 0: the statistics keep
    four decimals, or four significant digits where four decimals would give 0,
    and a footer, a report line and an HTML cell print what the Markdown does.
    The references are SciPy's."""
    from siamang.data.listwise import round_p
    from siamang.reporting import Report
    from siamang.reporting.tables import stat_text

    rng = np.random.default_rng(0)
    low, high = rng.normal(0, 1, 200), rng.normal(2, 1, 200)
    variables = VariableMap()
    variables.add_many(
        [
            Variable("y", "interval", label="Y"),
            Variable("g", "nominal", label="G", labels={1: "One", 2: "Two", 3: "Three"}),
            Variable("a", "nominal", label="A", labels={1: "Yes", 2: "No"}),
        ]
    )
    frame = pd.DataFrame(
        {
            "y": np.r_[low, high, rng.normal(4, 1, 200)],
            "g": [1] * 200 + [2] * 200 + [3] * 200,
            "a": [1] * 190 + [2] * 10 + [2] * 190 + [1] * 10 + [1] * 200,
        }
    )
    data = SurveyData(frame=frame, variables=variables)
    two = data.with_frame(frame[frame["g"] != 3])

    welch = stats.ttest_ind(low, high, equal_var=False).pvalue  # 7.68e-58
    ttest = two.report.ttest("y", by="g")
    assert ttest.stats["p"] == pytest.approx(welch, rel=1e-3) and ttest.stats["p"] > 0
    assert f"p = {welch:.4g};" in ttest.to_markdown()
    assert two.report.means("y", by="g", method="welch").stats["p"] == ttest.stats["p"]
    # The default test, chosen for you, too.
    student = stats.ttest_ind(low, high).pvalue
    assert two.report.means("y", by="g").stats["p"] == pytest.approx(student, rel=1e-3)

    means = data.report.means("y", by="g", method="anova", posthoc="tukey")
    anova = stats.f_oneway(*[frame.loc[frame["g"] == k, "y"] for k in (1, 2, 3)]).pvalue
    assert means.stats["p"] == pytest.approx(anova, rel=1e-3) and anova < 1e-100
    # Tukey's p for groups 2 SD apart is below what SciPy computes the studentized
    # range to: printed as that bound, "< 1e-07", in the Markdown and the HTML.
    pairs = means.posthoc_table.to_frame()["p"].tolist()
    assert all(p is not None for p in pairs) and "< 1e-07" in pairs
    markdown, html = means.posthoc_table.to_markdown(), means.posthoc_table.to_html()
    for p in pairs:
        assert f"| {p} |" in markdown and f"<td>{str(p).replace('<', '&lt;')}</td>" in html

    crosstab = data.report.crosstab("a", "g")
    chi2 = stats.chi2_contingency(pd.crosstab(frame["a"], frame["g"]).to_numpy()).pvalue
    assert crosstab.stats["p"] == pytest.approx(chi2, rel=1e-3) and chi2 < 1e-4
    fisher = two.report.crosstab("a", "g", method="fisher")
    exact = stats.fisher_exact(pd.crosstab(two.frame["a"], two.frame["g"]).to_numpy()).pvalue
    assert fisher.stats["p"] == pytest.approx(exact, rel=1e-3) and exact < 1e-60
    assert f"p = {exact:.4g};" in fisher.to_markdown()

    matrix = data.with_frame(frame.assign(y2=frame["y"] + rng.normal(0, 6.5, 600)))
    matrix.variables.add(Variable("y2", "interval", label="Y2"))
    table = matrix.report.correlation_matrix(["y", "y2"], method="pearson", layout="pairs")
    assert 0 < table.to_frame()["p"][0] < 1e-4

    dunn = data.analysis.compare_groups("y", "g", posthoc="dunn")
    assert "p = 0.0000" not in str(dunn) and "e-" in dunn["One vs Three"]

    # Four decimals as before wherever they keep a p above 0.
    assert round_p(0.041563) == 0.0416 and round_p(0.0) == 0.0 and math.isnan(round_p(np.nan))
    assert round_p(1.13155862e-24) == 1.132e-24
    # A footer and a report line print the same, without padding.
    assert stat_text(124.98) == "124.98" and stat_text(64.4) == "64.4" and stat_text(2.0) == "2.0"
    assert stat_text(5.8e-07) == "5.8e-07" and stat_text(0.0123) == "0.0123"
    report = Report().add({"p_value": 2.17e-30, "df": 124.98}).to_markdown()
    assert "p_value = 2.17e-30; df = 124.98" in report


def test_a_studentized_range_p_below_what_scipy_computes_is_printed_as_a_bound():
    """SciPy's studentized_range.sf is 1 − cdf, the cdf integrated to an absolute
    error of 1e-11: past q ≈ 12 it gives the integration's noise, not a p. Every
    strong pair of three groups at 297 df read 1.144e-14, and in Games-Howell a
    larger q got a larger p (19.386 → 0.0, 37.479 → 2.776e-14). Below 1e-07 the
    p is 0.0 and printed "< 1e-07"; above it Tukey's p for two groups is the
    Student t-test's, as it must be (q = √2·|t| on the pooled variance)."""
    from siamang.data import inference

    rng = np.random.default_rng(0)
    frame = pd.DataFrame(
        {
            "y": np.r_[rng.normal(0, 1, 100), rng.normal(2, 1, 100), rng.normal(6, 1, 100)],
            "g": [1] * 100 + [2] * 100 + [3] * 100,
        }
    )
    variables = VariableMap()
    variables.add_many(
        [
            Variable("y", "interval", label="Y"),
            Variable("g", "nominal", label="G", labels={1: "One", 2: "Two", 3: "Three"}),
        ]
    )
    data = SurveyData(frame=frame, variables=variables)
    for method, posthoc in (("anova", "tukey"), ("welch_anova", "games_howell")):
        table = data.report.means("y", by="g", method=method, posthoc=posthoc).posthoc_table
        assert table.to_frame()["p"].tolist() == ["< 1e-07"] * 3, posthoc
        assert "| < 1e-07 |" in table.to_markdown() and "e-14" not in table.to_markdown()
        assert "< 1e-07 where it is smaller than SciPy computes" in table.stats["p"]
        assert (
            "3 of 3 pairs differ"
            in data.report.means("y", by="g", method=method, posthoc=posthoc).stats["Post-hoc"]
        )
    # q past 15 at 297 df and at 1998 df alike.
    strong = [rng.normal(mean, 1, 667) for mean in (0, 1, 2)]
    result = inference.posthoc(strong, ["a", "b", "c"], "tukey")
    assert (result.table["statistic"] > 15).all() and (result.table["p_adjusted"] == 0).all()

    # Two groups: Tukey's p is Student's, to the digits printed, above the floor.
    rng = np.random.default_rng(3)
    for shift, reference in ((0.5, 0.11535866027415248), (1.3, 5.361739564669448e-07)):
        a, b = rng.normal(0, 1, 40), rng.normal(shift, 1, 40)
        assert stats.ttest_ind(a, b).pvalue == pytest.approx(reference, rel=1e-12)
        p = inference.posthoc([a, b], ["A", "B"], "tukey").table["p_adjusted"][0]
        assert p == pytest.approx(reference, rel=1e-6)
    # The first pair of a table has no bound where its p is above the floor.
    moderate = data.with_frame(
        frame.assign(y=np.r_[rng.normal(0, 1, 200), rng.normal(0.4, 1, 100)])
    )
    pairs = moderate.report.means("y", by="g", method="anova", posthoc="tukey").posthoc_table
    assert all(isinstance(p, float) for p in pairs.to_frame()["p"])
    assert "< 1e-07" not in pairs.stats["p"]


def test_a_footer_prints_the_p_the_statistics_keep():
    """round_p and stat_text switch to the exponent at the same line (0.0001) and
    keep the same four significant digits, so a footer never says another p
    than the Stat output: round_p(4.99996e-05) kept 5e-05 while the footer said
    "p = 0.0001", and a t-test's p of 7.988e-32 read "p = 7.99e-32"."""
    from siamang.data.listwise import round_p
    from siamang.reporting.tables import stat_text

    assert round_p(4.99996e-05) == 5e-05 and stat_text(round_p(4.99996e-05)) == "5e-05"
    assert round_p(9.99e-05) == 9.99e-05 and stat_text(9.99e-05) == "9.99e-05"
    assert round_p(0.00012) == 0.0001 and stat_text(0.00012) == "0.0001"
    assert stat_text(7.988e-32) == "7.988e-32"
    for p in (0.5, 0.04999, 0.00015, 0.0001, 9.9996e-05, 5e-05, 4.99996e-05, 1.2345e-09, 7.988e-32):
        kept = round_p(p)
        assert stat_text(kept) == str(kept), p

    rng = np.random.default_rng(0)
    frame = pd.DataFrame(
        {"y": np.r_[rng.normal(0, 1, 60), rng.normal(3, 1, 60)], "g": [1] * 60 + [2] * 60}
    )
    variables = VariableMap()
    variables.add_many(
        [
            Variable("y", "interval", label="Y"),
            Variable("g", "nominal", label="G", labels={1: "One", 2: "Two"}),
        ]
    )
    ttest = SurveyData(frame=frame, variables=variables).report.ttest("y", by="g")
    assert ttest.stats["p"] < 1e-4 and f"p = {ttest.stats['p']};" in ttest.to_markdown()


def test_a_matrix_adjustment_counts_only_the_pairs_it_adjusted():
    """A pair with a constant variable has no p, so it is not one of the
    comparisons the adjustment divides among: with a × c and b × c not computed,
    Bonferroni over a × b alone leaves its p as it was (pearsonr: 0.04156)."""
    variables = VariableMap()
    variables.add_many([Variable(name, "interval", label=name.upper()) for name in "abc"])
    frame = pd.DataFrame({"a": [1.0, 2, 3, 4, 5, 6], "b": [2.0, 1, 4, 3, 6, 5], "c": [1.0] * 6})
    data = SurveyData(frame=frame, variables=variables)
    table = data.report.correlation_matrix(
        ["a", "b", "c"], method="pearson", adjust="bonferroni", layout="pairs"
    )
    row = table.to_frame().iloc[0]
    raw = stats.pearsonr(frame["a"], frame["b"]).pvalue
    assert row["p"] == row["p (Bonferroni)"] == round(raw, 4) == 0.0416
    assert table.stats["p adjustment"] == "Bonferroni, over the 1 pair computed (of 3)"
    assert table.stats["Not computed"].startswith("a × c: a variable has the same value")
    # Every pair computed: the count is all of them, as before.
    full = data.with_frame(frame.assign(c=[3.0, 1, 2, 6, 4, 5]))
    assert (
        full.report.correlation_matrix(
            ["a", "b", "c"], method="pearson", adjust="bonferroni"
        ).stats["p adjustment"]
        == "Bonferroni, over 3 pairs"
    )
    # The matrix layout writes n/a where the pair could not be computed.
    matrix = data.report.correlation_matrix(["a", "b", "c"], method="pearson").to_markdown()
    assert "| C | n/a | n/a | — |" in matrix
