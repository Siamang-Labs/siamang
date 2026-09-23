"""Tests for the declarative reporting module."""

from siamang import (
    LikertScale,
    NumericInput,
    Page,
    Questionnaire,
    SingleChoice,
    Variable,
    VariableMap,
)


def build_test_data():
    """Create a test SurveyData with known values."""
    consent = Variable("consent", scale="nominal", label="Consent", labels={1: "Yes", 0: "No"})
    age = Variable("age", scale="ratio", label="Age", valid_range=(18, 75))
    gender = Variable(
        "gender",
        scale="nominal",
        label="Gender",
        labels={1: "Male", 2: "Female", 3: "Non-binary"},
    )
    it_role = Variable(
        "it_role",
        scale="nominal",
        label="IT Role",
        labels={1: "Engineer", 2: "Data Scientist", 3: "DevOps", 4: "PM"},
    )
    remote_freq = Variable(
        "remote_freq",
        scale="ordinal",
        label="Remote Frequency",
        labels={1: "Never", 2: "Occasionally", 3: "Hybrid", 4: "Mostly remote", 5: "Fully remote"},
    )
    satisfaction = Variable(
        "satisfaction",
        scale="ordinal",
        label="Job Satisfaction",
        labels={1: "Very low", 2: "Low", 3: "Neutral", 4: "High", 5: "Very high"},
    )
    autonomy = Variable(
        "autonomy",
        scale="ordinal",
        label="Autonomy",
        labels={1: "Very low", 2: "Low", 3: "Moderate", 4: "High", 5: "Very high"},
    )

    variables = VariableMap()
    variables.add_many([consent, age, gender, it_role, remote_freq, satisfaction, autonomy])

    q_consent = SingleChoice("Consent?", var=consent, required=True)
    q_age = NumericInput("Age?", var=age)
    q_gender = SingleChoice("Gender?", var=gender)
    q_role = SingleChoice("Role?", var=it_role)
    q_remote = SingleChoice("Remote?", var=remote_freq)
    q_sat = LikertScale("Satisfaction?", var=satisfaction, points=5)
    q_aut = LikertScale("Autonomy?", var=autonomy, points=5)

    page1 = Page(name="consent", title="Consent", items=[q_consent])
    page2 = Page(
        name="demo",
        title="Demographics",
        items=[q_age, q_gender, q_role, q_remote, q_sat, q_aut],
        show_if=consent.eq(1),
    )

    survey = Questionnaire(
        title="Test Survey",
        pages=[page1, page2],
        variables=variables,
    )

    data = survey.simulate(n=200, seed=123)
    return data


def test_freq_table():
    data = build_test_data()
    table = data.report.freq("it_role")
    frame = table.to_frame()

    # Should have columns: Value, Label, N, %, Cumulative %
    assert "Label" in frame.columns
    assert "N" in frame.columns
    assert "%" in frame.columns
    assert "Cumulative %" in frame.columns

    # Labels should be resolved
    labels_in_table = frame["Label"].tolist()
    assert "Total" in labels_in_table

    # Markdown output
    md = table.to_markdown()
    assert "|" in md
    assert "Label" in md

    print("FreqTable OK")
    print(md[:500])
    print()


def test_quality_table_counts_by_reason_over_everyone_screened():
    """The table prepare.quality feeds into a report section.

    A respondent who failed two checks is in both reason rows, so the reasons
    do not add up — "Any check" is the number a methods section quotes, and
    every percentage is of everyone screened rather than of the survivors.
    """
    import pandas as pd

    from siamang.data import SurveyData

    frame = pd.DataFrame(
        {
            "id": [1, 2, 3, 4],
            "quality_flags": ["", "straightlining; duplicate", "attention", ""],
        }
    )
    table = SurveyData(frame=frame).report.quality("quality_flags")
    rows = dict(zip(table.to_frame()["Check"], table.to_frame()["N"], strict=True))
    assert rows["Straightlining"] == 1 and rows["Duplicate"] == 1 and rows["Attention"] == 1
    assert rows["Any check"] == 2 and rows["Clean"] == 2
    percent = dict(zip(table.to_frame()["Check"], table.to_frame()["%"], strict=True))
    assert percent["Any check"] == 50.0
    assert table.stats == {"Screened": 4, "Flagged": 2}
    # A check nobody failed is not a row of zeros: only what happened is shown.
    assert "Inconsistency" not in rows
    assert "| Check " in table.to_markdown()


def test_quality_table_without_a_flags_column_reports_everyone_clean():
    import pandas as pd

    from siamang.data import SurveyData

    table = SurveyData(frame=pd.DataFrame({"id": [1, 2]})).report.quality()
    rows = dict(zip(table.to_frame()["Check"], table.to_frame()["N"], strict=True))
    assert rows == {"Any check": 0, "Clean": 2}


def test_cross_table():
    data = build_test_data()
    table = data.report.crosstab("it_role", "remote_freq")
    table.to_frame()

    # Should have chi2 stats
    md = table.to_markdown()
    assert "χ²" in md or "chi" in md.lower() or "p =" in md

    print("CrossTable OK")
    print(md[:800])
    print()


def test_group_mean_table():
    data = build_test_data()
    table = data.report.means("autonomy", by="remote_freq")
    frame = table.to_frame()

    assert "Mean" in frame.columns
    assert "SD" in frame.columns
    assert "N" in frame.columns

    md = table.to_markdown()
    assert "Kruskal-Wallis" in md or "p =" in md

    print("GroupMeanTable OK")
    print(md[:500])
    print()


def test_bar_chart():
    data = build_test_data()
    chart = data.plot.bar("it_role")
    chart.save("/tmp/test_bar.png")
    print("BarChart saved to /tmp/test_bar.png")


def test_boxplot():
    data = build_test_data()
    chart = data.plot.boxplot("autonomy", by="remote_freq")
    chart.save("/tmp/test_boxplot.png")
    print("BoxPlot saved to /tmp/test_boxplot.png")


def test_heatmap():
    data = build_test_data()
    chart = data.plot.heatmap(["satisfaction", "autonomy"])
    chart.save("/tmp/test_heatmap.png")
    print("HeatMap saved to /tmp/test_heatmap.png")


def test_scatter():
    data = build_test_data()
    chart = data.plot.scatter("satisfaction", "autonomy", hue="remote_freq")
    chart.save("/tmp/test_scatter.png")
    print("ScatterPlot saved to /tmp/test_scatter.png")


if __name__ == "__main__":
    import matplotlib

    matplotlib.use("Agg")

    print("=" * 60)
    print("Testing siamang.reporting module")
    print("=" * 60)
    print()

    test_freq_table()
    test_cross_table()
    test_group_mean_table()
    test_bar_chart()
    test_boxplot()
    test_heatmap()
    test_scatter()

    print()
    print("=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)


# ── Weights reach the three basic tables ──────────────────────────────────────
#
# Two groups; the second respondent of each carries three times the weight of
# the first. Every expected number below is arithmetic by hand.


def _weighted_pair():
    import pandas as pd

    from siamang.core.variable import Variable, VariableMap
    from siamang.data import SurveyData

    frame = pd.DataFrame(
        {
            "grp": [1, 1, 2, 2],
            "ans": [1, 2, 1, 2],
            "score": [10.0, 20.0, 30.0, 40.0],
            "w": [1.0, 3.0, 1.0, 3.0],
        }
    )
    variables = VariableMap()
    variables.add_many(
        [
            Variable("grp", "nominal", label="Group", labels={1: "Left", 2: "Right"}),
            Variable("ans", "nominal", label="Answer", labels={1: "Yes", 2: "No"}),
            Variable("score", "interval", label="Score"),
            Variable("w", "ratio", label="Weight"),
        ]
    )
    return SurveyData(frame=frame, variables=variables)


def test_freq_table_counts_weights_and_keeps_the_people_beside_them():
    data = _weighted_pair()
    plain = data.report.freq("ans").to_frame()
    weighted = data.with_weight("w").report.freq("ans")
    frame = weighted.to_frame()

    # Unweighted: two of each, the table exactly as before.
    assert list(plain.columns) == ["Value", "Label", "N", "%", "Cumulative %"]
    assert plain["N"].tolist() == [2, 2, 4] and plain["%"].tolist() == [50.0, 50.0, 100.0]
    # Weighted: Yes = 1 + 1, No = 3 + 3, of 8 — and the raw counts still shown.
    assert list(frame.columns) == ["Value", "Label", "N", "Unweighted N", "%", "Cumulative %"]
    assert frame["N"].tolist() == [2.0, 6.0, 8.0]
    assert frame["Unweighted N"].tolist() == [2, 2, 4]
    assert frame["%"].tolist() == [25.0, 75.0, 100.0]
    assert frame["Cumulative %"].tolist() == [25.0, 100.0, 100.0]
    assert weighted.stats == {"Variable": "Answer", "N valid": 4, "Weighted N": 8.0, "Weight": "w"}


def test_cross_table_percentages_are_of_weights():
    data = _weighted_pair()
    plain = data.report.crosstab("grp", "ans", pct="row", test=False).to_frame()
    weighted = data.with_weight("w").report.crosstab("grp", "ans", pct="row")
    frame = weighted.to_frame()

    assert plain["Yes"].tolist() == [50.0, 50.0, 2] and plain["Total"].tolist() == [2, 2, 4]
    # Each group: Yes carries weight 1, No weight 3 — 25 / 75 — and the totals
    # are sums of weights.
    assert frame["Yes"].tolist() == [25.0, 25.0, 2.0]
    assert frame["No"].tolist() == [75.0, 75.0, 6.0]
    assert frame["Total"].tolist() == [4.0, 4.0, 8.0]
    stats = weighted.stats
    assert stats["N"] == 4 and stats["Weighted N"] == 8.0 and stats["Weight"] == "w"
    # Kish: (1+3+1+3)² / (1+9+1+9) = 64 / 20 = 3.2 effective respondents.
    assert stats["Effective N"] == 3.2
    assert "effective (Kish)" in stats["Base"]


def test_cross_table_tests_on_the_effective_base_not_the_weighted_count():
    """Weights make a sample behave like a smaller one; a χ² on the weighted
    counts as if they were people manufactures significance."""
    import numpy as np
    import pandas as pd

    from siamang.core.variable import Variable, VariableMap
    from siamang.data import SurveyData

    rng = np.random.default_rng(3)
    n = 400
    grp = np.repeat([1, 2], n // 2)
    ans = np.where(rng.random(n) < np.where(grp == 1, 0.55, 0.45), 1, 2)
    frame = pd.DataFrame({"grp": grp, "ans": ans, "w": np.where(rng.random(n) < 0.1, 25.0, 0.5)})
    variables = VariableMap()
    variables.add_many(
        [Variable("grp", "nominal"), Variable("ans", "nominal"), Variable("w", "ratio")]
    )
    data = SurveyData(frame=frame, variables=variables).with_weight("w")
    stats = data.report.crosstab("grp", "ans").stats
    assert stats["Effective N"] < stats["N"] < stats["Weighted N"]
    # The same table tested on the weighted counts as people would be far more "significant".
    from scipy.stats import chi2_contingency

    weighted_counts = pd.crosstab(frame["grp"], frame["ans"], values=frame["w"], aggfunc="sum")
    naive_p = chi2_contingency(weighted_counts.values)[1]
    assert naive_p < stats["p"]


def test_group_means_are_weighted_and_n_is_not():
    data = _weighted_pair()
    plain = data.report.means("score", by="grp", test=False).to_frame()
    weighted = data.with_weight("w").report.means("score", by="grp", test=False)
    frame = weighted.to_frame()

    assert plain["Mean"].tolist() == [15.0, 35.0] and plain["N"].tolist() == [2, 2]
    assert plain["SD"].tolist() == [7.071, 7.071] and plain["Median"].tolist() == [15.0, 35.0]
    # Left: (10·1 + 20·3) / 4 = 17.5; Right: (30·1 + 40·3) / 4 = 37.5.
    assert list(frame.columns) == ["Group", "Mean", "SD", "Median", "N"]
    assert frame["Group"].tolist() == ["Left", "Right"]
    assert frame["Mean"].tolist() == [17.5, 37.5]
    # Weighted variance (1·7.5² + 3·2.5²) / 4 = 18.75, times n/(n-1) = 2 → SD √37.5.
    assert frame["SD"].tolist() == [6.124, 6.124]
    # Half the weight (2 of 4) is reached at the heavier value.
    assert frame["Median"].tolist() == [20.0, 40.0]
    assert frame["N"].tolist() == [2, 2]
    assert weighted.stats["Weight"] == "w" and "weighted" in weighted.stats["Note"]


def test_equal_weights_reproduce_the_unweighted_tables():
    import pandas as pd

    data = build_test_data()
    weighted = pd.DataFrame(data.frame).assign(w=1.0)
    from siamang.data import SurveyData

    same = SurveyData(frame=weighted, variables=data.variables).with_weight("w")
    for column in ("it_role", "remote_freq"):
        a = data.report.freq(column).to_frame()
        b = same.report.freq(column).to_frame().drop(columns=["Unweighted N"])
        assert a["%"].tolist() == b["%"].tolist() and a["N"].tolist() == b["N"].tolist()
    a = data.report.crosstab("it_role", "remote_freq", pct="col").to_frame()
    b = same.report.crosstab("it_role", "remote_freq", pct="col").to_frame()
    assert a.round(1).values.tolist() == b.round(1).values.tolist()
    a = data.report.means("autonomy", by="remote_freq").to_frame()
    b = same.report.means("autonomy", by="remote_freq").to_frame()
    assert a["Mean"].tolist() == b["Mean"].tolist() and a["SD"].tolist() == b["SD"].tolist()
    assert a["N"].tolist() == b["N"].tolist()


def test_a_weighted_multiple_choice_frequency_shows_both_bases():
    import pandas as pd

    from siamang.core.variable import Variable, VariableMap
    from siamang.data import SurveyData

    frame = pd.DataFrame({"pick": [[1, 2], [1], [2], None], "w": [1.0, 3.0, 1.0, 5.0]})
    variables = VariableMap()
    variables.add_many(
        [Variable("pick", "nominal", labels={1: "A", 2: "B"}), Variable("w", "ratio")]
    )
    table = SurveyData(frame=frame, variables=variables).with_weight("w").report.freq("pick")
    rows = table.to_frame()
    # A: weights 1 + 3 of a weighted base 5 (the non-answer weighs nothing); B: 1 + 1.
    assert rows["N"].tolist() == [4, 2, 5] and rows["Unweighted N"].tolist() == [2, 2, 3]
    assert rows["%"].tolist() == [80.0, 40.0, 100.0]
    assert table.stats["Base"] == "3 respondents (5 weighted)"
