"""siamang.data.paired — Wilcoxon signed-rank, McNemar and Friedman on related samples.

The reference values are computed by hand where the arithmetic is short, and
otherwise by SciPy 1.17 (``wilcoxon``, ``friedmanchisquare``) and statsmodels
(``mcnemar``), whose conventions the module follows.
"""

from __future__ import annotations

from itertools import product

import numpy as np
import pandas as pd
import pytest

from siamang.core.variable import MissingValue, Variable, VariableMap
from siamang.data import SurveyData, paired
from siamang.reporting.result_table import ResultTable

# ─── the array-level tests ───────────────────────────────────────────────────


def test_signed_rank_exact_without_ties_by_hand():
    """d = 3, −1, 4, 2, −5, 6, 7: the ranks of |d| are the values themselves.
    W+ = 3 + 4 + 2 + 6 + 7 = 22, W− = 1 + 5 = 6. Of the 2⁷ = 128 sign
    patterns, 14 give W+ ≥ 22 (the subsets of 1..7 summing to 6 or less), so
    the two-sided exact p is 2 · 14 / 128."""

    result = paired.signed_rank([3, -1, 4, 2, -5, 6, 7])
    assert (result.w_plus, result.w_minus) == (22.0, 6.0)
    assert result.method == "exact"
    assert result.p == pytest.approx(28 / 128)
    # Z from the normal approximation: (22 − 7·8/4) / √(7·8·15/24) = 8 / √35.
    assert result.z == pytest.approx(8 / 35**0.5)
    assert result.r == pytest.approx(8 / 35**0.5 / 7**0.5)
    assert result.rank_biserial == pytest.approx((22 - 6) / 28)
    assert (result.positive, result.negative, result.zeros) == (5, 2, 0)
    approximate = paired.signed_rank([3, -1, 4, 2, -5, 6, 7], p_value="approximate")
    assert approximate.method == "normal approximation"
    assert approximate.p == pytest.approx(0.17629637444051116)  # 2 · Φ(−8 / √35)


def test_signed_rank_with_ties_and_zeros_matches_scipy():
    """16 pairs with zeros and tied |d|: more than 13, so the normal
    approximation with the tie correction. Without the zeros the 14 ranks are
    1.5 ×2, 4 ×3, 7 ×3, 9, 10, 11.5 ×2, 13, 14; the negative differences hold
    1.5 + 4 + 11.5 = 17 of the 105. SciPy 1.17: p = 0.025478168 (wilcox),
    0.024015126 (pratt)."""

    d = [0, 0, 1, -1, 2, 2, -2, 3, 3, 3, 4, 5, 6, -6, 7, 8]
    wilcox = paired.signed_rank(d)
    assert wilcox.method == "normal approximation"
    assert (wilcox.w_plus, wilcox.w_minus) == (88.0, 17.0)
    assert wilcox.p == pytest.approx(0.025478168040325017)
    assert wilcox.ranked == 14 and wilcox.zeros == 2 and wilcox.ties
    pratt = paired.signed_rank(d, zeros="pratt")
    assert pratt.ranked == 16
    assert pratt.w_minus == 23.0  # ranked with the zeros: 3.5 + 6.5 + 13
    assert pratt.p == pytest.approx(0.024015125859125658)


def _permutation_p(d, zeros):
    """The two-sided p by enumerating every sign pattern — the definition."""
    from scipy.stats import rankdata

    d = np.asarray(d, dtype=float)
    kept = d[d != 0] if zeros == "wilcox" else d
    ranks = rankdata(np.abs(kept))[kept != 0]
    observed = ranks[kept[kept != 0] > 0].sum()
    sums = np.array([np.dot(signs, ranks) for signs in product((0, 1), repeat=len(ranks))])
    return min(1.0, 2 * min((sums <= observed).mean(), (sums >= observed).mean()))


def test_small_samples_with_ties_get_the_exact_permutation_p():
    """At most 13 pairs with ties or zeros: every sign pattern is counted, as
    SciPy 1.17 does (0.2539063 wilcox, 0.2304688 pratt for this sample)."""

    d = [1, 2, -1, 0, 3, 1, -2, 2, 0, 1, 1, -1]
    for zeros, expected in (("wilcox", 0.2539063), ("pratt", 0.2304688)):
        result = paired.signed_rank(d, zeros=zeros)
        assert result.method == "exact"
        assert result.p == pytest.approx(expected, abs=1e-7)
        assert result.p == pytest.approx(_permutation_p(d, zeros))
    # Asked for, the exact p is available beyond 13 pairs, ties or not.
    d = [0, 0, 1, -1, 2, 2, -2, 3, 3, 3, 4, 5, 6, -6, 7, 8]
    exact = paired.signed_rank(d, p_value="exact")
    assert exact.method == "exact"
    assert exact.p == pytest.approx(_permutation_p(d, "wilcox"))


def test_signed_rank_degenerate_cases_explain_instead_of_crashing():
    same = paired.signed_rank([0, 0, 0])
    assert same.p is None and same.z is None and same.method == "none"
    assert "same answer" in same.note
    empty = paired.signed_rank([np.nan, np.nan])
    assert empty.n == 0 and empty.p is None and empty.note == "no complete pairs"
    one = paired.signed_rank([2])
    assert one.method == "exact" and one.p == 1.0
    with pytest.raises(ValueError, match="zeros must be one of"):
        paired.signed_rank([1, 2], zeros="zsplit")


def test_mcnemar_exact_and_chi_square_match_statsmodels():
    # b + c = 12 < 25: exact, 2 · P(X ≤ 3 | 12, ½) = 2 · 299 / 4096.
    small = paired.mcnemar_test(3, 9)
    assert small.method == "exact binomial" and small.statistic is None
    assert small.p == pytest.approx(598 / 4096)
    assert small.cohens_g == pytest.approx(9 / 12 - 0.5)
    assert small.odds_ratio == pytest.approx(3 / 9)
    # b + c = 35: (|10 − 25| − 1)² / 35 = 5.6 on 1 df.
    large = paired.mcnemar_test(10, 25)
    assert large.method == "chi-square with continuity correction"
    assert large.statistic == pytest.approx(5.6) and large.df == 1
    assert large.p == pytest.approx(0.01796047752607879)
    # b = c: Edwards' correction as R and statsmodels apply it, 1 / (b + c).
    even = paired.mcnemar_test(20, 20)
    assert even.statistic == pytest.approx(0.025)
    assert even.p == pytest.approx(0.8743670611628918)
    # Forced either way.
    assert paired.mcnemar_test(10, 25, p_value="exact").p == pytest.approx(0.016673847800120715)
    assert paired.mcnemar_test(3, 9, p_value="approximate").statistic == pytest.approx(25 / 12)
    # Nobody changed: nothing to test; one side empty: no odds ratio.
    assert paired.mcnemar_test(0, 0).p is None
    assert paired.mcnemar_test(0, 7).odds_ratio is None
    assert paired.mcnemar_test(0, 7).p == pytest.approx(2 / 128)


def test_friedman_by_hand_and_with_ties_as_scipy():
    """Rank sums 5, 8, 11 over four respondents and three variables:
    χ² = 12 / (4·3·4) · (25 + 64 + 121) − 3·4·4 = 4.5 on 2 df, p = e^−2.25,
    Kendall's W = 4.5 / (4 · 2)."""

    matrix = [[1, 2, 3], [2, 5, 4], [1, 3, 5], [3, 2, 4]]
    result = paired.friedman_test(matrix)
    assert result.statistic == pytest.approx(4.5)
    assert result.df == 2
    assert result.p == pytest.approx(np.exp(-2.25))
    assert result.kendalls_w == pytest.approx(0.5625)
    assert list(result.mean_ranks) == pytest.approx([1.25, 2.0, 2.75])
    tied = [[1, 1, 2], [2, 3, 3], [1, 2, 3], [4, 4, 4], [2, 1, 1], [3, 4, 5]]
    with_ties = paired.friedman_test(tied)
    # scipy.stats.friedmanchisquare: 3.6470588235294055, p = 0.16145490331307955
    assert with_ties.statistic == pytest.approx(3.6470588235294055)
    assert with_ties.p == pytest.approx(0.16145490331307955)
    all_tied = paired.friedman_test([[2, 2, 2], [3, 3, 3]])
    assert all_tied.statistic is None and all_tied.p is None
    with pytest.raises(ValueError, match="three or more"):
        paired.friedman_test([[1, 2], [2, 1]])


def test_holm_and_bonferroni_by_hand():
    """Holm: sorted 0.01·3, 0.03·2, then 0.04·1 held up to 0.06."""

    assert list(paired.adjust([0.01, 0.04, 0.03], "holm")) == pytest.approx([0.03, 0.06, 0.06])
    assert list(paired.adjust([0.01, 0.04, 0.03], "bonferroni")) == pytest.approx(
        [0.03, 0.12, 0.09]
    )
    assert list(paired.adjust([0.5, 0.9], "holm")) == pytest.approx([1.0, 1.0])
    # A comparison that could not be tested is not counted (R's p.adjust).
    adjusted = paired.adjust([0.02, np.nan, 0.04], "bonferroni")
    assert adjusted[0] == pytest.approx(0.04) and np.isnan(adjusted[1])


# ─── on survey data ──────────────────────────────────────────────────────────

LABELS = {1: "Poor", 2: "Fair", 3: "Good", 4: "Very good", 5: "Excellent", 9: "Refused"}


def _survey(weighted: bool = False) -> SurveyData:
    before = [1, 2, 3, 2, 4, 1, 3, 2, 9, 5, np.nan, 3]
    after = [3, 1, 5, 4, 5, 5, 3, 4, 2, 5, 4, 9]
    later = [2, 3, 4, 4, 5, 6, 4, 3, 3, 5, 5, 4]
    frame = pd.DataFrame(
        {
            "before": before,
            "after": after,
            "later": later,
            "aware_a": [1, 1, 0, 1, 0, 0, 1, 1, 0, 1, 1, np.nan],
            "aware_b": [1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1],
            "region": [1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2],
            "w": [1.0] * 12,
        }
    )
    refused = (MissingValue(9, "Refused"),)
    variables = VariableMap()
    variables.add_many(
        [
            Variable("before", "ordinal", label="Rating before", labels=LABELS, missing=refused),
            Variable("after", "ordinal", label="Rating after", labels=LABELS, missing=refused),
            Variable("later", "ordinal", label="Rating later"),
            Variable("aware_a", "nominal", label="Knows A", labels={0: "No", 1: "Yes"}),
            Variable("aware_b", "nominal", label="Knows B", labels={0: "No", 1: "Yes"}),
            Variable("region", "nominal", label="Region", labels={1: "North", 2: "South"}),
        ]
    )
    data = SurveyData(frame=frame, variables=variables)
    return data.with_weight("w") if weighted else data


def test_wilcoxon_on_survey_data_drops_missing_codes_and_says_so():
    """Rows 9 (before = Refused), 11 (before blank) and 12 (after = Refused)
    are left out; the nine complete pairs give d = before − after = −2, 1, −2,
    −2, −1, −4, 0, −2, 0 — first minus second, as R's wilcox.test(x, y,
    paired = TRUE), SciPy's wilcoxon(x, y) and the paired t-test take it.
    Without the zeros the ranks are 1.5 (the two 1s), 4.5 (the four 2s) and 7,
    so W+ = 1.5 and W− = 4 · 4.5 + 1.5 + 7 = 26.5; nine pairs with ties and
    zeros get the exact permutation p, 0.046875 (SciPy 1.17)."""

    result = paired.wilcoxon(_survey(), "before", "after")
    stats = result.stats
    assert stats["N"] == 9 and stats["Excluded"] == 3
    assert "a missing value in either variable" in stats["Excluded because"]
    assert stats["Missing codes"] == "2 answers with a missing code (9 = Refused) left out"
    assert (stats["Positive differences"], stats["Negative differences"]) == (1, 6)
    assert stats["Zero differences"] == 2
    assert (stats["W+"], stats["W-"]) == (1.5, 26.5)
    # Z and the rank-biserial r are negative: the first rating is the lower.
    assert stats["Z"] < 0 and stats["Rank-biserial r"] == pytest.approx((1.5 - 26.5) / 28, abs=1e-3)
    assert stats["p"] == pytest.approx(0.046875, rel=1e-3)  # four significant digits
    assert stats["p-value"] == "exact"  # 9 pairs, ties and zeros: the permutation p
    assert stats["Difference"] == "Rating before − Rating after"
    assert "Weight" not in stats
    table = result.table.to_frame()
    assert list(table["Variable"]) == [
        "Rating before",
        "Rating after",
        "Difference (Rating before − Rating after)",
    ]
    assert list(table["N"]) == [9, 9, 9]
    assert table.loc[2, "Median"] == -2.0
    assert table.loc[0, "Mean"] == pytest.approx(23 / 9, abs=1e-3)
    assert "nan" not in result.table.to_markdown()
    assert result.pairs.to_frame().empty and "no pairwise" in result.pairs.stats["Note"]


def test_mcnemar_on_survey_data_with_yes_inferred_from_0_1():
    """Eleven complete pairs (the last has no answer on A): 5 yes on both, 2
    yes on A only, 4 on B only, 0 neither."""

    result = paired.mcnemar(_survey(), "aware_a", "aware_b")
    stats = result.stats
    assert stats["Counts as yes"] == "1 = Yes"
    assert stats["N"] == 11 and stats["Excluded"] == 1
    assert (stats["Yes only: aware_a"], stats["Yes only: aware_b"]) == (2, 4)
    assert stats["p"] == pytest.approx(paired.mcnemar_test(2, 4).p, rel=1e-3)
    assert stats["p-value"] == "exact binomial (6 discordant pairs)"
    assert stats["% yes: aware_a"] == pytest.approx(63.6)
    assert stats["% yes: aware_b"] == pytest.approx(81.8)
    # First minus second, as the Wilcoxon and t-test differences: 7/11 − 9/11.
    assert stats["Difference"] == "Knows A − Knows B"
    assert stats["Difference (points)"] == pytest.approx(-18.2)
    table = result.table.to_frame()
    assert list(table.columns) == ["Knows A", "Knows B: yes", "Knows B: no", "Total"]
    assert table.iloc[0, 1:].tolist() == [5, 2, 7]
    assert table.iloc[1, 1:].tolist() == [4, 0, 4]
    assert table.iloc[2, 1:].tolist() == [9, 2, 11]


def test_mcnemar_needs_to_be_told_what_yes_is_on_other_codes():
    data = _survey()
    with pytest.raises(ValueError, match="which answer counts as yes.*1 = Poor"):
        paired.mcnemar(data, "before", "later")
    # Top-two box: Very good or Excellent count as yes.
    result = paired.mcnemar(data, "before", "after", yes=[4, 5])
    assert result.stats["Counts as yes"] == "4 = Very good, 5 = Excellent"
    nobody = paired.mcnemar(data, "before", "after", yes=8)
    assert "no respondent gave 8" in nobody.stats["Warning"]
    assert "nothing to test" in nobody.stats["Note"] and "p" not in nobody.stats


def test_friedman_on_survey_data_with_holm_adjusted_pairs():
    result = paired.friedman(_survey(), ["before", "after", "later"])
    stats = result.stats
    assert stats["Test"] == "Friedman" and stats["N"] == 9 and stats["df"] == 2
    rows = result.table.to_frame()
    assert list(rows.columns) == ["Variable", "N", "Mean", "SD", "Median", "Mean rank"]
    assert rows["Mean rank"].sum() == pytest.approx(6.0)  # 1 + 2 + 3 per respondent
    frame = _survey().frame.drop(index=[8, 10, 11])
    expected = paired.friedman_test(frame[["before", "after", "later"]].to_numpy())
    assert stats["Chi-square"] == pytest.approx(expected.statistic, abs=1e-3)
    assert stats["Kendall's W"] == pytest.approx(expected.kendalls_w, abs=1e-3)
    pairs = result.pairs.to_frame()
    assert list(zip(pairs["Variable A"], pairs["Variable B"], strict=True)) == [
        ("Rating before", "Rating after"),
        ("Rating before", "Rating later"),
        ("Rating after", "Rating later"),
    ]
    raw = [
        paired.signed_rank(frame[a].to_numpy() - frame[b].to_numpy()).p
        for a, b in (("before", "after"), ("before", "later"), ("after", "later"))
    ]
    assert list(pairs["p"]) == pytest.approx(raw, rel=1e-3)
    assert list(pairs["p adjusted"]) == pytest.approx(paired.adjust(raw, "holm"), rel=1e-3)
    assert result.pairs.stats["Adjustment"] == "Holm (3 comparisons)"
    assert result.pairs.stats["Difference"] == "A − B"
    # N is the nine respondents compared, as in the footer; those who gave the
    # same answer twice are counted beside it — two for before − after, one for
    # before − later, three for after − later. N used to count only the ranked
    # pairs, 7 / 8 / 6 under a footer of N = 9.
    assert list(pairs.columns[:4]) == ["Variable A", "Variable B", "N", "Zero differences"]
    assert list(pairs["N"]) == [9, 9, 9] and result.pairs.stats["N"] == 9
    assert list(pairs["Zero differences"]) == [2, 1, 3]
    first = paired.signed_rank(frame["before"].to_numpy() - frame["after"].to_numpy())
    assert (pairs["W+"][0], pairs["W-"][0]) == (first.w_plus, first.w_minus) == (1.5, 26.5)
    bonferroni = paired.friedman(_survey(), ["before", "after", "later"], posthoc="bonferroni")
    assert list(bonferroni.pairs.to_frame()["p adjusted"]) == pytest.approx(
        paired.adjust(raw, "bonferroni"), rel=1e-3
    )
    skipped = paired.friedman(_survey(), ["before", "after", "later"], posthoc="none")
    assert skipped.pairs.to_frame().empty and skipped.stats["Pairwise"] == "none"


def test_compare_picks_the_test_and_explains_what_it_cannot_do():
    data = _survey()
    assert paired.compare(data, ["before", "after"]).stats["Test"] == "Wilcoxon signed-rank"
    assert paired.compare(data, ["before", "after", "later"]).stats["Test"] == "Friedman"
    assert paired.compare(data, ["aware_a", "aware_b"], test="mcnemar").stats["Test"] == "McNemar"
    with pytest.raises(ValueError, match="exactly two variables; 3 were given"):
        paired.compare(data, ["before", "after", "later"], test="wilcoxon")
    # Auto chose no test for one variable: the message is about paired tests,
    # not about Friedman's, which nobody asked for.
    with pytest.raises(ValueError, match=r"^Paired tests compare two or more variables .*1 was"):
        paired.compare(data, ["before"])
    with pytest.raises(ValueError, match="Friedman's test compares three or more variables; 1 was"):
        paired.compare(data, ["before"], test="friedman")
    with pytest.raises(ValueError, match="needs ordered values; region is nominal"):
        paired.compare(data, ["before", "region"])
    with pytest.raises(ValueError, match="before is listed twice"):
        paired.compare(data, ["before", "before"])
    with pytest.raises(KeyError, match="nope"):
        paired.compare(data, ["before", "nope"])
    text = data.with_frame(data.frame.assign(later=["x"] * 12))
    with pytest.raises(TypeError, match="text that is not a number"):
        paired.compare(text, ["before", "after", "later"])
    listed = data.with_frame(data.frame.assign(later=[[1, 2]] * 12))
    with pytest.raises(TypeError, match="prepare.explode"):
        paired.compare(listed, ["before", "later"])


def test_everyone_answering_the_same_is_a_result_not_an_error():
    data = _survey()
    same = data.with_frame(data.frame.assign(after=data.frame["before"]))
    result = paired.wilcoxon(same, "before", "after")
    assert "p" not in result.stats and "same answer" in result.stats["Note"]
    assert result.stats["Zero differences"] == 10
    blank = data.with_frame(data.frame.assign(after=np.nan))
    nobody = paired.wilcoxon(blank, "before", "after")
    assert nobody.stats["N"] == 0 and nobody.stats["Note"] == "no complete pairs"


def test_weighted_data_says_the_weight_is_not_applied():
    data = _survey(weighted=True)
    note = "unweighted (the weight 'w' is not applied)"
    assert paired.wilcoxon(data, "before", "after").stats["Weight"] == note
    assert paired.mcnemar(data, "aware_a", "aware_b").stats["Weight"] == note
    friedman = paired.friedman(data, ["before", "after", "later"])
    assert friedman.stats["Weight"] == friedman.pairs.stats["Weight"] == note


def test_result_tables_render_blank_cells_and_their_statistics():
    table = ResultTable(
        data=_survey(),
        frame=pd.DataFrame({"A": ["x", "y"], "B": [1.5, np.nan]}),
        footer={"Test": "t", "p": 0.01234},
    )
    markdown = table.to_markdown()
    assert "| y |  |" in markdown and "nan" not in markdown.lower()
    # A p kept to four significant digits prints as kept (stat_text).
    assert markdown.endswith("Test = t; p = 0.01234")
    html = table.to_html()
    assert "NaN" not in html and "siamang-stats" in html
    assert np.isnan(table.to_frame().loc[1, "B"])  # the number stays missing


def test_a_footer_prints_the_p_the_statistics_keep():
    """Paired tests keep a p to four significant digits (p_rounded), and their
    footers went through stat_text's four decimals: stats["p"] = 0.002343 under
    a footer of "p = 0.0023", 0.008144 under "p = 0.0081". Each footer now
    prints its statistics' p as kept, as the pairwise table's cells do."""
    rng = np.random.default_rng(0)
    x = rng.integers(1, 6, 40).astype(float)
    y = np.clip(x + rng.integers(-1, 3, 40), 1, 5)
    z = np.clip(y + rng.integers(-1, 2, 40), 1, 5)
    data = SurveyData(frame=pd.DataFrame({"x": x, "y": y, "z": z}))
    wilcoxon = paired.wilcoxon(data, "x", "y")
    friedman = paired.friedman(data, ["x", "y", "z"])
    assert (wilcoxon.stats["p"], friedman.stats["p"]) == (0.002343, 0.008144)
    for result in (wilcoxon, friedman):
        assert f"; p = {result.stats['p']};" in result.table.to_markdown()
        assert f"; p = {result.stats['p']};" in result.table.to_html()
    assert "| 0.002343 | 0.007029 |" in friedman.pairs.to_markdown()


def test_wilcoxon_mcnemar_and_the_paired_t_test_take_the_difference_one_way():
    """The paired t-test reported before − after and Wilcoxon after − before,
    so a robustness check of one by the other showed opposite signs and W+ and
    W− swapped. All take first − second now, as R and SciPy do."""

    from scipy import stats as sp

    data = _survey()
    wilcoxon = paired.wilcoxon(data, "before", "after").stats
    t_test = data.report.ttest("before", kind="paired", other="after").stats
    assert wilcoxon["Difference"] == t_test["Difference"] == "Rating before − Rating after"
    assert t_test["Mean difference"] < 0 and wilcoxon["Z"] < 0
    frame = data.frame.drop(index=[8, 10, 11])
    x, y = frame["before"].to_numpy(), frame["after"].to_numpy()
    # SciPy's wilcoxon(x, y) tests x − y: "less" is the side the data lean to.
    assert sp.wilcoxon(x, y, alternative="less").pvalue < 0.05
    assert sp.wilcoxon(x, y, alternative="greater").pvalue > 0.5
    assert paired.wilcoxon(data, "before", "after").test.w_plus == 1.5


def test_mcnemar_names_the_field_and_one_list_column_reads_as_one():
    data = _survey()
    with pytest.raises(ValueError, match="in Counts as yes — `yes` outside a flow"):
        paired.mcnemar(data, "before", "later")
    listed = data.with_frame(data.frame.assign(aware_a=[[1, 2]] * 12))
    # "aware_a hold multiple-choice answers" before.
    with pytest.raises(TypeError, match="^aware_a holds multiple-choice answers"):
        paired.mcnemar(listed, "aware_a", "aware_b")


# ─── Cochran's Q ─────────────────────────────────────────────────────────────

#: Eighteen respondents × three yes/no questions.
COCHRAN = np.array(
    [
        [1, 1, 0],
        [1, 1, 1],
        [0, 1, 0],
        [0, 0, 0],
        [1, 1, 0],
        [1, 1, 1],
        [0, 1, 1],
        [1, 1, 0],
        [0, 0, 1],
        [1, 1, 0],
        [1, 0, 0],
        [1, 1, 0],
        [0, 1, 0],
        [1, 1, 1],
        [0, 1, 0],
        [1, 1, 0],
        [0, 0, 0],
        [1, 1, 0],
    ]
)


def test_cochran_q_by_hand_and_as_statsmodels_and_r():
    """Yes per question C = 11, 14, 5 (N = 30 yeses); the respondents' yeses
    squared sum to ΣR² = 64. Q = (k − 1)(k ΣC² − N²) / (k N − ΣR²) =
    2 · (3 · 342 − 900) / (90 − 64) = 252 / 26 on 2 df. statsmodels 0.15
    ``cochrans_q``: Q = 9.692307692307692, p = 0.007858544670151704; R's
    ``DescTools::CochranQTest``: Q = 9.6923, df = 2, p-value = 0.007859."""

    result = paired.cochran_test(COCHRAN)
    assert result.statistic == pytest.approx(252 / 26)
    assert result.statistic == pytest.approx(9.692307692307692)
    assert result.df == 2 and (result.n, result.k) == (18, 3)
    assert result.p == pytest.approx(0.007858544670151704)
    assert list(result.yes) == [11, 14, 5]
    # A respondent saying yes to all, or to none, adds as much to the numerator
    # as to the denominator: Q does not move.
    more = np.vstack([COCHRAN, [[1, 1, 1], [0, 0, 0], [1, 1, 1]]])
    assert paired.cochran_test(more).statistic == pytest.approx(252 / 26)
    assert paired.cochran_test(more).n == 21
    # Nobody differs between the questions: nothing to test, not a division by 0.
    same = paired.cochran_test([[1, 1, 1], [0, 0, 0]])
    assert same.statistic is None and same.p is None
    assert paired.cochran_test(np.zeros((0, 3))).statistic is None
    with pytest.raises(ValueError, match="three or more"):
        paired.cochran_test([[1, 0], [0, 1]])
    with pytest.raises(ValueError, match="yes \\(1\\) and no \\(0\\)"):
        paired.cochran_test([[1, 2, 0]])


def _cochran_survey(weighted: bool = False) -> SurveyData:
    frame = pd.DataFrame(COCHRAN, columns=["ad_tv", "ad_web", "ad_radio"]).astype(float)
    # Two more respondents: one with a blank, one who refused the radio question.
    extra = pd.DataFrame({"ad_tv": [1.0, 0.0], "ad_web": [np.nan, 1.0], "ad_radio": [1.0, 9.0]})
    frame = pd.concat([frame, extra], ignore_index=True)
    frame["w"] = np.linspace(0.5, 1.5, len(frame))
    yes_no = {0: "No", 1: "Yes", 9: "Refused"}
    refused = (MissingValue(9, "Refused"),)
    variables = VariableMap()
    variables.add_many(
        [
            Variable("ad_tv", "nominal", label="Saw it on TV", labels=yes_no, missing=refused),
            Variable("ad_web", "nominal", label="Saw it online", labels=yes_no, missing=refused),
            Variable(
                "ad_radio", "nominal", label="Heard it on the radio", labels=yes_no, missing=refused
            ),
        ]
    )
    data = SurveyData(frame=frame, variables=variables)
    return data.with_weight("w") if weighted else data


def test_cochran_on_survey_data_with_pairwise_mcnemar_holm():
    """The eighteen complete respondents; the pairs are McNemar tests on them:
    TV − online b = 1, c = 4 (exact p = 0.375), TV − radio 8 and 2 (0.109375),
    online − radio 10 and 1 (0.01171875) — the exact binomial p statsmodels'
    ``mcnemar(exact=True)`` gives. Holm: 0.01171875 · 3 = 0.03515625,
    0.109375 · 2 = 0.21875, 0.375."""

    variables = ["ad_tv", "ad_web", "ad_radio"]
    result = paired.cochran(_cochran_survey(), variables)
    stats = result.stats
    assert stats["Test"] == "Cochran's Q" and stats["Counts as yes"] == "1 = Yes"
    assert stats["N"] == 18 and stats["Variables"] == 3 and stats["Excluded"] == 2
    assert stats["Missing codes"] == "1 answer with a missing code (9 = Refused) left out"
    assert stats["Q"] == pytest.approx(9.692) and stats["df"] == 2
    assert stats["p"] == 0.007859  # four significant digits
    assert stats["Pairwise"] == "McNemar, Holm-adjusted p"
    table = result.table.to_frame()
    assert list(table.columns) == ["Variable", "N", "Yes", "% yes"]
    assert list(table["Variable"]) == ["Saw it on TV", "Saw it online", "Heard it on the radio"]
    assert list(table["Yes"]) == [11, 14, 5]
    assert list(table["% yes"]) == [61.1, 77.8, 27.8]
    pairs = result.pairs.to_frame()
    assert list(zip(pairs["Yes only A"], pairs["Yes only B"], strict=True)) == [
        (1, 4),
        (8, 2),
        (10, 1),
    ]
    assert list(pairs["p"]) == [0.375, 0.1094, 0.01172]
    assert list(pairs["p adjusted"]) == [0.375, 0.2188, 0.03516]
    assert list(pairs["Difference (points)"]) == [-16.7, 33.3, 50.0]
    assert pairs["Chi-square"].isna().all()  # exact below 25 discordant pairs
    footer = result.pairs.stats
    assert footer["Adjustment"] == "Holm (3 comparisons)" and footer["p-value"] == "exact binomial"
    assert footer["Difference"] == "A − B" and footer["N"] == 18
    assert "nan" not in result.pairs.to_markdown()
    bonferroni = paired.cochran(_cochran_survey(), variables, posthoc="bonferroni")
    assert list(bonferroni.pairs.to_frame()["p adjusted"]) == [1.0, 0.3281, 0.03516]
    approximate = paired.cochran(_cochran_survey(), variables, p_value="approximate")
    # (|1 − 4| − 1)² / 5 = 0.8, as statsmodels' mcnemar(exact=False).
    assert approximate.pairs.to_frame()["Chi-square"][0] == 0.8
    skipped = paired.cochran(_cochran_survey(), variables, posthoc="none")
    assert skipped.pairs.to_frame().empty and skipped.stats["Pairwise"] == "none"
    assert "not asked for" in skipped.pairs.stats["Note"]


def test_cochran_reads_yes_codes_explains_and_says_it_is_unweighted():
    data = _cochran_survey(weighted=True)
    variables = ["ad_tv", "ad_web", "ad_radio"]
    note = "unweighted (the weight 'w' is not applied)"
    result = paired.compare(data, variables, test="cochran")
    assert result.stats["Weight"] == result.pairs.stats["Weight"] == note
    assert result.stats["Test"] == "Cochran's Q"
    # "No" as yes gives the mirror image, and the same Q.
    mirrored = paired.cochran(data, variables, yes=0)
    assert mirrored.stats["Counts as yes"] == "0 = No"
    assert mirrored.stats["Q"] == result.stats["Q"]
    nobody = paired.cochran(data, variables, yes=7)
    assert "no respondent gave 7 to any of the variables" in nobody.stats["Warning"]
    assert "nothing to compare" in nobody.stats["Note"] and "p" not in nobody.stats
    rated = SurveyData(frame=pd.DataFrame({"a": [1, 2, 3], "b": [2, 3, 1], "c": [3, 1, 2]}))
    with pytest.raises(ValueError, match="^Cochran's Q needs to know which answer counts as yes"):
        paired.cochran(rated, ["a", "b", "c"])
    assert paired.cochran(rated, ["a", "b", "c"], yes=[2, 3]).stats["Q"] == 0.0
    with pytest.raises(ValueError, match="Cochran's Q compares three or more yes/no variables; 2"):
        paired.compare(data, variables[:2], test="cochran")
    with pytest.raises(ValueError, match="For three or more yes/no variables, use Cochran's Q"):
        paired.compare(data, variables, test="mcnemar")
    with pytest.raises(ValueError, match="ad_tv is listed twice"):
        paired.cochran(data, ["ad_tv", "ad_tv", "ad_web"])
