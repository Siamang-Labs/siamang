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
