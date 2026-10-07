"""A base with no answers in it — a survey just opened, a filter that left no
one — prints no result: no Total of 100 %, no NPS of 0, and a chart says in
plain words that no one answered instead of failing.

Weighted counts that are equal print alike, whatever order their weights were
summed in (:func:`siamang.data.listwise.round_weighted`).
"""

from __future__ import annotations

import warnings

import pandas as pd
import pytest

from siamang.core.variable import Variable, VariableMap
from siamang.data import SurveyData, paired
from siamang.data.listwise import round_weighted
from siamang.reporting import NoAnswersError, Report


def _empty() -> SurveyData:
    """The columns of a café's survey, and not one response."""

    variables = VariableMap()
    variables.add(Variable("brand", "nominal", label="Brand", labels={1: "Brand A", 2: "Brand B"}))
    variables.add(Variable("nps", "ordinal", label="Likely to recommend", valid_range=(0, 10)))
    variables.add(
        Variable("taste", "ordinal", label="Taste", labels={1: "Bad", 2: "OK", 3: "Good"})
    )
    variables.add(
        Variable("price", "ordinal", label="Price", labels={1: "Bad", 2: "OK", 3: "Good"})
    )
    variables.add(Variable("cups", "ratio", label="Cups a week"))
    columns = ["brand", "nps", "taste", "price", "cups"]
    frame = pd.DataFrame({name: pd.Series([], dtype=float) for name in columns})
    frame["visited"] = pd.Series([], dtype="datetime64[ns]")
    return SurveyData(frame=frame, variables=variables)


def test_an_empty_base_prints_no_percentage_and_no_score():
    """With no answers the Frequencies' Total read 100.0 % (and its
    Cumulative % 100.0) beside N 0, and the NPS read 0 with every group at
    0.0 %: on an empty dashboard, results. There are none: each is None,
    written "—" in the Markdown, the HTML and the footer."""

    data = _empty()
    freq = data.report.freq("brand")
    assert freq.to_frame().to_dict("records") == [
        {"Value": "", "Label": "Total", "N": 0, "%": None, "Cumulative %": None}
    ]
    assert "|  | Total | 0 | — | — |" in freq.to_markdown()
    assert "<td>—</td>" in freq.to_html() and "None" not in freq.to_html()

    nps = data.report.nps("nps")
    assert nps.stats["NPS"] is None and nps.stats["N valid"] == 0
    assert nps.to_frame()["%"].tolist() == [None, None, None, None]
    assert "NPS = —; SE = —" in nps.to_markdown()
    assert "None" not in nps.to_markdown() and "None" not in nps.to_html()

    # With answers, the same tables read as they did.
    answered = SurveyData(
        frame=pd.DataFrame({"brand": [1, 1, 2], "nps": [10, 9, 3]}), variables=data.variables
    )
    assert answered.report.freq("brand").to_frame()["%"].tolist() == [66.7, 33.3, 100.0]
    nps = answered.report.nps("nps")
    assert nps.stats["NPS"] == pytest.approx(33.3)
    assert nps.to_frame()["%"].tolist() == [33.3, 0.0, 66.7, 100.0]


@pytest.mark.parametrize(
    ("draw", "said"),
    [
        (lambda d: d.plot.bar("brand"), "No respondent answered Brand."),
        (lambda d: d.plot.bar("brand", show="percent"), "No respondent answered Brand."),
        (lambda d: d.plot.bar("brand", layout="donut"), "No respondent answered Brand."),
        (lambda d: d.plot.bar("cups", by="brand"), "No respondent answered both Cups a week and Brand."),
        (lambda d: d.plot.boxplot("cups", by="brand"), "No respondent answered both Cups a week and Brand."),
        (lambda d: d.plot.scatter("cups", "nps"), "No respondent answered both Cups a week and Likely to recommend."),
        (lambda d: d.plot.heatmap(["taste", "price"]), "No respondent answered every item: there is no correlation to draw."),
        (lambda d: d.plot.likert(["taste", "price"]), "No respondent answered any of the 2 items."),
        (lambda d: d.plot.trend("visited", period="week", measure="count"), "No respondent answered visited."),
    ],
)  # fmt: skip
def test_a_chart_of_no_answers_says_who_did_not_answer(draw, said):
    """A chart of a base with no answers drew an empty axis, a matrix of
    blanks or failed with a message of its own, each a little differently.
    Each raises NoAnswersError now (a ValueError, as before), with a plain
    message a report or a dashboard shows as it is."""

    chart = draw(_empty())
    with pytest.raises(NoAnswersError) as raised:
        chart.png()
    assert str(raised.value) == said
    assert isinstance(raised.value, ValueError)


def test_a_label_that_asks_is_not_followed_by_a_full_stop():
    """A label that asks ends the message: no "?." and no "?:" after it."""

    from siamang.reporting import result_charts

    variables = VariableMap()
    variables.add(Variable("brand", "nominal", label="Which brands have you heard of?"))
    variables.add(Variable("nps", "ordinal", label="Would you recommend us?", valid_range=(0, 10)))
    variables.add(Variable("region", "nominal", label="Where do you live?"))
    variables.add(Variable("taste", "ordinal", label="Taste"))
    frame = pd.DataFrame(
        {name: pd.Series([], dtype=float) for name in ("brand", "nps", "region", "taste")}
    )
    data = SurveyData(frame=frame, variables=variables)
    said = []
    for draw in (
        lambda: data.plot.bar("brand").png(),
        lambda: result_charts.chart(data.report.nps("nps")).png(),
        lambda: data.plot.heatmap(["taste", "nps"], by="region").png(),
        lambda: data.plot.heatmap(["taste", "nps"], by="region", cmap="theme").png(),
    ):
        with pytest.raises(NoAnswersError) as raised:
            draw()
        said.append(str(raised.value))
    assert said == [
        "No respondent answered Which brands have you heard of?",
        "There is no score: no respondent answered Would you recommend us?",
        "There is no mean to draw: no respondent answered every item and Where do you live?",
        "There is no mean to draw: no respondent answered an item and Where do you live?",
    ]


def test_a_chart_says_what_its_listwise_base_needs():
    """A scatter plot colored by a group needs the group too, and said only
    "both X and Y" when everyone had answered both."""

    variables = VariableMap()
    variables.add(Variable("cups", "ratio", label="Cups"))
    variables.add(Variable("spend", "ratio", label="Spend"))
    variables.add(Variable("g", "nominal", label="Group"))
    frame = pd.DataFrame({"cups": [1, 2, 3, 4], "spend": [2, 3, 1, 5], "g": [None] * 4})
    data = SurveyData(frame=frame, variables=variables)
    with pytest.raises(NoAnswersError, match="^No respondent answered Cups, Spend and Group.$"):
        data.plot.scatter("cups", "spend", hue="g").png()


def test_a_result_chart_of_an_nps_with_no_answers_says_so():
    from siamang.reporting import result_charts

    with pytest.raises(
        NoAnswersError, match="^There is no score: no respondent answered Likely to recommend.$"
    ):
        result_charts.chart(_empty().report.nps("nps")).png()


def test_a_report_writes_what_a_chart_of_no_answers_says_and_goes_on(tmp_path):
    """A report with such a chart in it failed as a whole; it writes the
    chart's message where the figure would be, keeps its caption, and the
    rest of the report is there."""

    data = _empty()
    report = Report(title="Week 1")
    report.add(data.report.freq("brand"))
    report.add(data.plot.bar("brand", show="percent"), caption="Brand shares")
    report.text("The end.")
    markdown = report.to_markdown()
    assert "*No respondent answered Brand.*\n\n*Brand shares*" in markdown
    assert markdown.rstrip().endswith("The end.")
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # no "no interactive chart" warning either
        html = report.save(tmp_path / "week1.html", interactive=True).read_text(encoding="utf-8")
    assert '<p class="siamang-figcaption">No respondent answered Brand.</p>' in html
    assert "Brand shares" in html and "The end." in html


def test_a_flow_with_no_answers_runs_through_and_says_so_where_charts_are_drawn(tmp_path):
    """A preview built each chart at its node and failed it with
    "ValueError: …", and the eager Result chart failed even the generated
    script's run. A chart of nothing is not a failed node: the flow runs
    through, and the report it saves writes each chart's message where its
    figure would be."""

    from siamang.flow import FlowRunner

    def node(node_id, kind, **params):
        return {"id": node_id, "type": kind, "params": params}

    def edge(a, ap, b, bp):
        return {"from": {"node": a, "port": ap}, "to": {"node": b, "port": bp}}

    flow = {
        "schema_version": "1.0",
        "name": "week1",
        "nodes": [
            node("src", "source.responses"),
            node("bar", "visualize.bar", variable="brand", show="percent"),
            node("nps", "analyze.nps", variable="nps"),
            node("rc", "visualize.result_chart"),
            node("sec", "output.report_section", heading="Week 1"),
            node("save", "output.save_report", title="Week 1", path="week1.md", html=False),
        ],
        "edges": [
            edge("src", "data", "bar", "data"),
            edge("src", "data", "nps", "data"),
            edge("nps", "table", "rc", "result"),
            edge("bar", "chart", "sec", "items"),
            edge("rc", "chart", "sec", "items"),
            edge("sec", "report", "save", "sections"),
        ],
    }
    run = FlowRunner(flow).run(sources={"src": _empty()}, cwd=tmp_path, raise_on_error=False)
    assert [(node.node, node.state) for node in run.runs] == [
        (name, "ok") for name in ("src", "bar", "nps", "rc", "sec", "save")
    ]
    for name in ("bar", "rc"):
        with pytest.raises(NoAnswersError):
            run.output(name).png()
    report = (tmp_path / "week1.md").read_text(encoding="utf-8")
    assert "*No respondent answered Brand.*" in report
    assert "*There is no score: no respondent answered Likely to recommend.*" in report


def test_a_live_chart_of_no_answers_has_no_spec_and_no_warning():
    from siamang.flow import live

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        with live.capture() as tiles:
            live.publish("t", kind="chart", label="Brand", value=_empty().plot.bar("brand"))
    assert tiles[0].spec is None


# ── Weighted counts ──────────────────────────────────────────────────────────


def test_equal_weighted_counts_print_alike():
    """Code 1's weights (0.15 + 0.65 + 0.65) and code 2's (0.45 + 1.0) both
    come to 1.45, but summed as floats the first is 1.4500000000000002 and
    read 1.5 beside the second's 1.4 — in a frequency table, a crosstab's
    bases and its weighted counts. Rounded by one helper that puts the float's
    noise aside first, every weighted count of 1.45 reads 1.4, as 1.45 does."""

    variables = VariableMap()
    variables.add(Variable("q", "nominal", label="Q", labels={1: "Tea", 2: "Coffee"}))
    variables.add(Variable("g", "nominal", label="G", labels={1: "In", 2: "Out"}))
    frame = pd.DataFrame(
        {"q": [1, 1, 1, 2, 2], "g": [1, 2, 1, 1, 2], "w": [0.15, 0.65, 0.65, 0.45, 1.0]}
    )
    data = SurveyData(frame=frame, variables=variables, weight="w")
    assert data.report.freq("q").to_frame()["N"].tolist() == [1.4, 1.4, 2.9]
    counts = data.report.crosstab("g", "q", pct="none").to_frame()
    assert counts.iloc[-1].tolist()[1:] == [1.4, 1.4, 2.9]
    # 0.65 and 0.45 as the freq table rounds them: up, as the floats are a hair above.
    assert counts["Tea"].tolist()[:2] == [0.8, 0.7] and counts["Coffee"].tolist()[:2] == [0.5, 1.0]
    bases = data.report.crosstab("g", "q", pct="col").to_frame()
    assert bases.iloc[-1].tolist()[1:] == [1.4, 1.4, 2.9]


def test_round_weighted_puts_the_float_noise_aside():
    assert [round_weighted(x) for x in (1.4500000000000002, 1.45, 4.550000000000001, 4.549999999999999)] == [1.4, 1.4, 4.5, 4.5]  # fmt: skip
    assert round_weighted(None) is None
    assert round_weighted(pd.Series([1.4500000000000002, None])).tolist()[0] == 1.4
    assert round_weighted(2.25, 2) == 2.25


# ── A Trend before the first response ───────────────────────────────────────


def _trend_flow(after: list[dict], edges: list[dict]) -> dict:
    """A flow that reads a Trend's table as its node does (the template's
    `.table`), then goes on to ``after``."""

    def edge(a, ap, b, bp):
        return {"from": {"node": a, "port": ap}, "to": {"node": b, "port": bp}}

    return {
        "schema_version": "1.0",
        "name": "trend",
        "nodes": [
            {"id": "src", "type": "source.file", "params": {"path": "d.csv"}},
            {"id": "tr", "type": "visualize.trend", "params": {"time": "when", "measure": "count"}},
            *after,
        ],
        "edges": [edge("src", "data", "tr", "data"), *[edge(*e) for e in edges]],
    }


def test_a_trend_before_the_first_response_lets_the_flow_and_its_script_go_on(
    tmp_path, monkeypatch
):
    """A Trend's node reads its table as it makes the chart, and the table
    raised NoAnswersError there: the node failed, the flow stopped at it, and
    a generated script — a Live run — published nothing after it. With no
    respondent to count, the table is one of no rows (Base 0), the node is
    done and the tiles after it are published."""

    from siamang.flow import FlowRunner, generate_flow, live

    monkeypatch.chdir(tmp_path)
    (tmp_path / "d.csv").write_text("when,brand\n", encoding="utf-8")
    flow = _trend_flow(
        [
            {"id": "t", "type": "output.live_tile", "params": {"kind": "chart", "label": "Trend"}},
            {"id": "f", "type": "analyze.freq", "params": {"variable": "brand"}},
            {"id": "tf", "type": "output.live_tile", "params": {"kind": "table", "label": "Brand"}},
        ],
        [
            ("tr", "chart", "t", "input"),
            ("src", "data", "f", "data"),
            ("f", "table", "tf", "input"),
        ],
    )
    run = FlowRunner(flow).run(cwd=tmp_path, raise_on_error=False)
    assert {node.node: node.state for node in run.runs} == {
        name: "ok" for name in ("src", "tr", "t", "f", "tf")
    }
    table = run.output("tr", "table")
    assert table.to_frame().empty and table.stats == {"Base": 0}

    # The script as a Live run has it, with no questionnaire module to import.
    code = generate_flow(flow).replace("from survey.questionnaire import survey", "survey = None")
    with live.capture() as tiles:
        exec(compile(code, "trend.py", "exec"), {"__name__": "__main__"})  # noqa: S102
    assert [tile.label for tile in tiles] == ["Trend", "Brand"]


def test_a_trend_whose_time_column_is_empty_beside_answers_is_a_set_up_mistake():
    """No time at all for respondents who answered is not a survey with no
    answers yet (a wave parameter never passed): it says so as a ValueError,
    not as an empty tile."""

    variables = VariableMap()
    variables.add(Variable("sat", "ordinal", label="Satisfaction"))
    variables.add(Variable("wave", "nominal", label="Wave"))
    frame = pd.DataFrame({"sat": [1, 2, 3], "wave": [None, None, None]})
    data = SurveyData(frame=frame, variables=variables)
    with pytest.raises(ValueError) as raised:
        data.plot.trend("wave", measure="count").png()
    assert not isinstance(raised.value, NoAnswersError)
    assert str(raised.value) == "Wave holds no values to draw a trend over."


# ── Result charts and analyses of no one ────────────────────────────────────


@pytest.mark.parametrize(
    ("result", "said"),
    [
        (lambda d: d.report.means("cups", by="brand"), "No respondent answered both Cups a week and Brand."),
        (lambda d: d.report.descriptives(["cups"]), "No respondent answered Cups a week."),
        (lambda d: d.report.descriptives(["cups", "nps"], by="brand"), "No respondent answered any of the 2 variables and Brand."),
        (lambda d: d.report.ttest("cups", by="brand"), "No respondent answered both Cups a week and Brand."),
        (lambda d: d.analysis.proportion_ci("brand", 2), "No respondent answered Brand."),
        (lambda d: paired.compare(d, ["taste", "price"], test="wilcoxon").table, "No respondent answered both Taste and Price."),
        (lambda d: paired.compare(d, ["taste", "price", "cups"], test="friedman").table, "No respondent answered Taste, Price and Cups a week."),
        (lambda d: paired.compare(d, ["taste", "price"], test="mcnemar", yes=[3]).table, "No respondent answered both Taste and Price."),
        (lambda d: paired.compare(d, ["taste", "price", "nps"], test="cochran", yes=[3]).table, "No respondent answered Taste, Price and Likely to recommend."),
        (lambda d: d.report.correlation_matrix(["taste", "price", "cups"]), "No respondent answered any two of the items: there is no correlation to draw."),
        (lambda d: d.report.correlation_matrix(["taste", "price", "cups"], missing="listwise"), "No respondent answered every item: there is no correlation to draw."),
    ],
)  # fmt: skip
def test_a_result_chart_of_no_one_says_who_did_not_answer(result, said):
    """A Result chart of Descriptives failed ("zip() argument 2 is longer
    than argument 1"), one of Group means, a t-test or a paired test drew an
    empty axis, one of a proportion drew a large 0.0 % on base 0, and one of
    a correlation matrix a matrix of "n/a"."""

    from siamang.reporting import result_charts

    with pytest.raises(NoAnswersError) as raised:
        result_charts.chart(result(_empty())).png()
    assert str(raised.value) == said


def test_an_analysis_of_no_one_prints_no_result():
    """A Spearman correlation of no pairs read rho 0.0 and p 1.0, a
    proportion 0.0 % (0.0 – 0.0), the quality and coding tables 0.0 % of no
    one; the chi-square stopped the flow in SciPy and, of one respondent,
    printed χ² = 0 on df 0; compare groups stopped it too. None, "—", and the
    tests not run, saying why."""

    data = _empty()
    analysis = data.analysis
    assert analysis.spearman("cups", "nps") == {"rho": None, "p_value": None, "n": 0.0}
    assert dict(analysis.proportion_ci("brand", 2)) == {
        "p": None,
        "lower": None,
        "upper": None,
        "n": 0.0,
    }
    not_run = "fewer than two groups have answers (0)"
    assert analysis.kruskal("cups", "brand")["note"] == not_run
    assert analysis.mannwhitney("cups", "brand")["p_value"] is None
    groups = analysis.compare_groups("cups", "brand", posthoc="dunn")
    assert (groups["p_value"], groups["note"], groups["posthoc"]) == (
        None,
        not_run,
        f"not run: {not_run}",
    )

    untestable = "Chi-square test: not run — the table has fewer than two rows or columns with answers in them"
    assert data.report.crosstab("taste", "brand").stats["Test"] == untestable
    one = SurveyData(frame=pd.DataFrame({"taste": [2], "brand": [1]}), variables=data.variables)
    stats = one.report.crosstab("taste", "brand").stats
    assert stats["Test"] == untestable and "χ²" not in stats
    assert data.report.crosstab("taste", "brand", pct="total").to_frame().iloc[-1].tolist()[1:] == [
        None
    ]

    quality = SurveyData(frame=pd.DataFrame({"quality_flags": pd.Series([], dtype=object)}))
    assert quality.report.quality().to_frame()["%"].tolist() == [None, None]


def test_an_analysis_with_nothing_to_work_on_says_no_one_answered():
    """TURF said "Run prepare.explode first" of a survey with no answers, and
    a cluster analysis, principal components and a reliability "fewer than
    three complete rows". They still stop at their node (what follows needs
    their result), in plain words."""

    from siamang.data import models, turf

    frame = pd.DataFrame({name: pd.Series([], dtype=float) for name in ("a", "b", "c")})
    for run in (
        lambda: models.pca(frame, ["a", "b", "c"]),
        lambda: models.kmeans(frame, ["a", "b", "c"], k=2),
        lambda: models.reliability(frame, ["a", "b", "c"]),
    ):
        with pytest.raises(NoAnswersError, match="^No respondent answered all 3 items.$"):
            run()
    with pytest.raises(NoAnswersError, match="^No respondent answered any of the 3 options.$"):
        turf.turf(frame, ["a", "b", "c"], max_size=2)


def test_an_nps_of_one_respondent_has_no_interval():
    """One promoter read NPS 100 with SE 0.0 and a 95 % interval from 100 to
    100: certainty from one answer. The score stands; its SE and interval
    need two respondents."""

    one = SurveyData(frame=pd.DataFrame({"nps": [10]}), variables=_empty().variables)
    stats = one.report.nps("nps").stats
    assert (stats["NPS"], stats["SE"], stats["CI95 low"], stats["CI95 high"]) == (
        100.0,
        None,
        None,
        None,
    )
    two = SurveyData(frame=pd.DataFrame({"nps": [10, 3]}), variables=_empty().variables)
    assert two.report.nps("nps").stats["SE"] is not None


def test_describe_counts_a_multiple_choice_column():
    """Describe raised "unhashable type: 'list'" on any survey with a
    multiple-choice question and stopped its flow; each set of codes chosen
    is one answer."""

    variables = VariableMap()
    variables.add(Variable("aware", "nominal", label="Aware", labels={1: "A", 2: "B"}))
    data = SurveyData(
        frame=pd.DataFrame({"aware": [[1, 2], [1], [1, 2], None]}), variables=variables
    )
    row = data.describe_variables().iloc[0]
    assert (row["n"], row["n_missing"], row["n_unique"]) == (4, 1, 2)


# ── Weighted counts on a chart ──────────────────────────────────────────────


def test_a_chart_writes_a_weighted_count_as_its_table_does():
    """A bar's label, its tooltip, the chart's description and a donut's
    center printed 1.5 for weights summed to 1.4500000000000002 and 1.4 for
    1.45, beside a table and a footer that read 1.4 for both; one donut read
    "weighted 1.5" in its center and "(weighted: 1.4)" under it."""

    from siamang.data import multi

    variables = VariableMap()
    variables.add(Variable("q", "nominal", label="Q", labels={1: "Tea", 2: "Coffee"}))
    frame = pd.DataFrame({"q": [1, 1, 1, 2, 2], "w": [0.15, 0.65, 0.65, 0.45, 1.0]})
    data = SurveyData(frame=frame, variables=variables, weight="w")
    bar = data.plot.bar("q", show="count")
    spec = bar.vega_lite()
    rows = [row for layer in [spec] for row in _rows(layer)]
    assert {(row["value"], row["text"]) for row in rows} == {(1.45, "1.4")}
    assert spec["description"] == "Bar chart: Q. Tea 1.4, Coffee 1.4."
    bar.png()
    assert sorted(text.get_text() for text in bar._ax.texts) == ["1.4", "1.4"]

    donut = SurveyData(frame=frame.iloc[:3], variables=variables, weight="w").plot.bar(
        "q", layout="donut"
    )
    donut.png()
    texts = [text.get_text() for text in donut._fig.findobj(lambda a: hasattr(a, "get_text"))]
    assert "weighted 1.4" in texts and any("(weighted: 1.4)" in text for text in texts)

    # A multiple choice's weighted counts, whole, alike whatever the order.
    picked = pd.DataFrame({"q": [[1], [1], [1], [2], [2]], "w": [0.15, 0.65, 0.7, 0.5, 1.0]})
    counts = multi.frequencies(picked, "q", weight="w", codes=[1, 2])
    assert counts["count"].tolist() == [2, 2]


def _rows(spec):
    """The rows of a Vega-Lite spec's data that carry a value's text."""

    if isinstance(spec, dict):
        values = spec.get("values")
        if isinstance(values, list):
            yield from (row for row in values if isinstance(row, dict) and "text" in row)
        for value in spec.values():
            yield from _rows(value)
    elif isinstance(spec, list):
        for value in spec:
            yield from _rows(value)
