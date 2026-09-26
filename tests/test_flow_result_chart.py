"""The Result chart node in a flow: registered, checked, run, generated.

The check reads what is connected — the node types and parameters upstream —
and names an output the chart cannot draw, or a Kind that does not suit it,
before the run; the run draws each result as the result is weighted; the
generated script draws the same figures.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import matplotlib
import pytest

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402

from siamang.codegen import generate_questionnaire  # noqa: E402
from siamang.data import text_coding  # noqa: E402
from siamang.flow import FlowRunner, check_flow, default_registry, generate_flow  # noqa: E402
from siamang.flow.document import FlowError  # noqa: E402
from siamang.io import write_snapshot  # noqa: E402
from siamang.model import from_document, loads, to_document  # noqa: E402
from siamang.reporting import result_charts as rc  # noqa: E402

DOCUMENTS = Path(__file__).resolve().parent / "documents"
ROOT = Path(__file__).resolve().parents[1]
TRUST = ["trust_acme", "trust_globex"]


@pytest.fixture(autouse=True)
def _close_figures():
    yield
    plt.close("all")


@pytest.fixture(scope="module")
def questionnaire_doc():
    return loads((DOCUMENTS / "brand_awareness.questionnaire.json").read_text("utf-8"))


@pytest.fixture(scope="module")
def survey(questionnaire_doc):
    return from_document(questionnaire_doc).survey


def _flow(nodes, edges, name="charts"):
    return {
        "schema_version": "1.0",
        "name": name,
        "nodes": [{"id": i, "type": t, "params": p} for i, t, p in nodes],
        "edges": [
            {"from": {"node": a, "port": ap}, "to": {"node": b, "port": bp}}
            for a, ap, b, bp in edges
        ],
    }


# Each analysis, and the chart of it: (analysis id, type, params, [ports], chart params).
ANALYSES = [
    ("means", "analyze.means", {"y": "satisfaction", "by": "region", "method": "anova", "posthoc": "tukey"}, ["table"], {}),
    ("desc", "analyze.descriptives", {"variables": ["age", "satisfaction"], "by": "gender"}, ["table"], {"kind": "means_sd"}),
    ("tt", "analyze.ttest", {"y": "age", "kind": "paired", "y2": "satisfaction"}, ["table"], {}),
    ("wil", "analyze.paired", {"variables": TRUST}, ["table"], {}),
    ("mcn", "analyze.paired", {"variables": TRUST, "test": "mcnemar", "yes_codes": [4, 5]}, ["table"], {}),
    ("ci", "analyze.proportion_ci", {"variable": "gender", "value": 2, "weighted": True}, ["stat"], {}),
    ("nps", "analyze.nps", {"variable": "satisfaction"}, ["table"], {}),
    ("turf", "analyze.turf", {"items": ["aware_1", "aware_2", "aware_3"], "max_size": 2}, ["table", "stat"], {}),
    ("pca", "analyze.pca", {"items": ["age", "satisfaction", *TRUST]}, ["variance", "stat"], {}),
    ("fac", "analyze.factor", {"items": ["age", "satisfaction", *TRUST], "n_factors": 2}, ["loadings"], {}),
    ("clu", "analyze.cluster", {"items": ["age", "satisfaction"], "k": 3}, ["table", "stat"], {}),
    ("reg", "analyze.regression", {"y": "satisfaction", "predictors": ["age", "region"]}, ["table", "stat"], {"title": "What goes with satisfaction"}),
    ("cor", "analyze.correlation_matrix", {"items": ["age", "satisfaction", *TRUST], "method": "pearson"}, ["table"], {}),
]  # fmt: skip


def _charts_flow(weighted: bool = True, source=("src", "source.responses", {})):
    nodes = [source, ("expl", "prepare.explode", {"variable": "aware"})]
    edges = [(source[0], "data", "expl", "data")]
    upstream = "expl"
    if weighted:
        nodes += [
            (
                "cell",
                "prepare.cell_weights",
                {"variable": "gender", "targets": {"1": 0.5, "2": 0.5}},
            ),
            ("w", "prepare.apply_weight", {}),
        ]
        edges += [("expl", "data", "cell", "data"), ("cell", "data", "w", "data")]
        upstream = "w"
    for node, kind, params, ports, chart in ANALYSES:
        if kind == "analyze.proportion_ci" and not weighted:
            params = {**params, "weighted": False}
        nodes += [(node, kind, params), (f"c_{node}", "visualize.result_chart", chart)]
        edges.append((upstream, "data", node, "data"))
        edges += [(node, port, f"c_{node}", "result") for port in ports]
        edges.append((f"c_{node}", "chart", "sec", "items"))
    nodes += [
        ("sec", "output.report_section", {"heading": "Results, drawn"}),
        ("save", "output.save_report", {"title": "Charts", "path": "outputs/charts.md"}),
    ]
    edges.append(("sec", "report", "save", "sections"))
    return _flow(nodes, edges)


def _issues(flow, questionnaire_doc):
    return [
        (issue.severity, issue.code, issue.message)
        for issue in check_flow(flow, questionnaire=questionnaire_doc)
    ]


# ─── the node ────────────────────────────────────────────────────────────────


def test_the_node_is_registered_with_every_kind():
    spec = default_registry().get("visualize.result_chart")
    assert spec.category == "visualize" and spec.outputs == {"chart": "Chart"}
    port = spec.inputs["result"]
    assert port.types == ("Table", "Stat") and port.many and not port.optional
    assert spec.params["kind"].values == ("auto", *rc.KINDS)
    assert spec.params["kind"].default == "auto"
    assert list(spec.params) == ["kind", "title", "width", "height", "palette"]
    # Every parameter is written into the code, so every one is read.
    assert all(spec.reads(name, {"kind": "auto"}) for name in spec.params)
    help_text = default_registry().get("prepare.apply_weight").params["column"].help
    assert "Result chart (as the result it draws)" in help_text


# ─── the check ───────────────────────────────────────────────────────────────


def test_check_flow_accepts_every_analysis_the_chart_draws(questionnaire_doc):
    assert _issues(_charts_flow(), questionnaire_doc) == []


def _one_chart(analysis, ports, chart=None, extra=()):
    node, kind, params = analysis
    nodes = [
        ("src", "source.responses", {}),
        (node, kind, params),
        ("c", "visualize.result_chart", chart or {}),
    ]
    edges = [("src", "data", node, "data"), *((node, port, "c", "result") for port in ports)]
    for other in extra:
        nodes.append(other[:3])
        edges.append(("src", "data", other[0], "data"))
        edges.append((other[0], other[3], "c", "result"))
    return _flow(nodes, edges)


def test_check_flow_names_an_output_the_chart_cannot_draw(questionnaire_doc):
    freq = ("fr", "analyze.freq", {"variable": "region"})
    [(severity, code, message)] = _issues(_one_chart(freq, ["table"]), questionnaire_doc)
    assert (severity, code) == ("error", "RESULT_NOT_DRAWABLE")
    assert message.startswith(
        "c: A Result chart cannot draw the table output of Frequencies (fr); it draws the "
        "results of Group means, Descriptive statistics, t-test, Paired tests,"
    )
    # A stat alone lends a chart its weight and base, and draws nothing.
    reg = ("reg", "analyze.regression", {"y": "satisfaction", "predictors": ["age"]})
    assert _issues(_one_chart(reg, ["stat"]), questionnaire_doc) == [
        (
            "error",
            "RESULT_NOT_DRAWABLE",
            "c: The stat output of Regression (reg) only tells a chart its weight and base; "
            "connect the output it draws, table, too.",
        )
    ]
    # Friedman's pairs are a table of tests, not something to draw.
    pairs = ("fri", "analyze.paired", {"variables": [*TRUST, "satisfaction"]})
    [(_, code, message)] = _issues(_one_chart(pairs, ["table", "pairs"]), questionnaire_doc)
    assert code == "RESULT_NOT_DRAWABLE" and "the pairs output of Paired tests (fri)" in message


def test_check_flow_names_a_kind_that_does_not_suit(questionnaire_doc):
    pca = ("pca", "analyze.pca", {"items": ["age", "satisfaction"]})
    assert _issues(_one_chart(pca, ["loadings"], {"kind": "scree"}), questionnaire_doc) == [
        (
            "error",
            "RESULT_KIND",
            "c: Kind 'scree' does not suit the loadings output of Principal components (pca), "
            "which draws 'loadings'; its variance output draws 'scree'.",
        )
    ]
    assert (
        _issues(_one_chart(pca, ["variance", "loadings"], {"kind": "scree"}), questionnaire_doc)
        == []
    )
    means = ("m", "analyze.means", {"y": "satisfaction", "by": "region"})
    [(_, code, message)] = _issues(
        _one_chart(means, ["table"], {"kind": "heatmap"}), questionnaire_doc
    )
    assert message == (
        "c: Kind 'heatmap' does not suit the table output of Group means (m), which draws "
        "'means' or 'means_sd'."
    )


def test_what_an_output_draws_follows_the_parameters_upstream(questionnaire_doc):
    fixed = ("t", "analyze.turf", {"items": ["age"], "method": "fixed", "portfolio": ["age"]})
    [(_, code, message)] = _issues(
        _one_chart(fixed, ["table"], {"kind": "reach"}), questionnaire_doc
    )
    assert code == "RESULT_KIND" and message.endswith("which draws 'items'.")
    search = ("t", "analyze.turf", {"items": ["age"]})
    assert _issues(_one_chart(search, ["table"], {"kind": "reach"}), questionnaire_doc) == []
    mcnemar = ("p", "analyze.paired", {"variables": TRUST, "test": "mcnemar"})
    [(_, code, message)] = _issues(
        _one_chart(mcnemar, ["table"], {"kind": "means"}), questionnaire_doc
    )
    assert code == "RESULT_KIND" and message.endswith("which draws 'shares'.")


def test_results_of_two_analyses_are_warned(questionnaire_doc):
    means = ("m", "analyze.means", {"y": "satisfaction", "by": "region"})
    nps = ("n", "analyze.nps", {"variable": "satisfaction"}, "table")
    assert _issues(_one_chart(means, ["table"], extra=[nps]), questionnaire_doc) == [
        (
            "warning",
            "RESULT_SOURCES",
            "c: The results connected come from m, n; a Result chart draws one of them — the "
            "table output of Group means (m).",
        )
    ]
    # With a kind, the one that draws it.
    [(_, _, message)] = _issues(
        _one_chart(means, ["table"], {"kind": "stacked"}, extra=[nps]), questionnaire_doc
    )
    assert message.endswith("the table output of Net Promoter Score (n).")


# ─── the run ─────────────────────────────────────────────────────────────────


EXPECTED = {
    # chart: (kind drawn, weight note, the result's class)
    "c_means": ("means", "weighted by 'weight'", "GroupMeanTable"),
    "c_desc": ("means_sd", "weighted by 'weight'", "DescriptivesTable"),
    "c_tt": ("means", "unweighted (the weight 'weight' is not applied)", "TTestTable"),
    "c_wil": ("means", "unweighted (the weight 'weight' is not applied)", "ResultTable"),
    "c_mcn": ("shares", "unweighted (the weight 'weight' is not applied)", "ResultTable"),
    "c_ci": ("interval", "weighted by 'weight'", "Proportion"),
    "c_nps": ("stacked", "weighted by 'weight'", "NpsTable"),
    "c_turf": ("reach", "weighted by 'weight'", "TurfTable"),
    "c_pca": ("scree", "weighted by 'weight'", "DataFrame"),
    "c_fac": ("loadings", "unweighted (the weight 'weight' is not applied)", "ResultTable"),
    "c_clu": ("profile", "unweighted (the weight 'weight' is not applied)", "DataFrame"),
    "c_reg": ("coefficients", "weighted by 'weight'", "DataFrame"),
    "c_cor": ("heatmap", "weighted by 'weight'", "CorrelationMatrixTable"),
}


def test_each_chart_draws_its_result_as_the_result_is_weighted(questionnaire_doc, survey, tmp_path):
    flow = _charts_flow(source=("sim", "source.simulated", {"n": 240, "seed": 5}))
    result = FlowRunner(flow, questionnaire=survey, questionnaire_document=questionnaire_doc).run(
        cwd=tmp_path
    )
    assert result.ok
    for node, (kind, note, cls) in EXPECTED.items():
        chart = result.output(node)
        assert isinstance(chart, rc.ResultChart), node
        assert (chart.drawn, chart.weight_note, type(chart.result).__name__) == (
            kind,
            note,
            cls,
        ), node
        # A run releases each figure once rendered; plot() draws it again.
        # (Panels — Descriptives of an age and a 1–5 scale — carry the title
        # over them all.)
        figure = chart.plot().figure
        title = figure._suptitle.get_text() if figure._suptitle else chart.plot().get_title("left")
        assert title.endswith(f"\n{note}"), node
    assert (
        result.output("c_reg")
        .plot()
        .get_title(loc="left")
        .startswith("What goes with satisfaction")
    )
    # TURF's reach curve names its options by their labels, as the fixed one.
    first = result.output("c_turf").plot().get_xticklabels()[0].get_text().replace("\n", " ")
    assert first.startswith("1 Brands heard of")
    # What each output draws, as the check reads it, is what the run draws.
    for node, kind, params, ports, _ in ANALYSES:
        spec = default_registry().get(kind)
        resolved = {**{k: p.default for k, p in spec.params.items()}, **params}
        for port in ports:
            expected = rc.output_kinds(kind, port, resolved)
            if expected is not None:
                assert rc.kinds_of(result.output(node, port)) == expected, (node, port)
    report = (tmp_path / "outputs" / "charts.md").read_text("utf-8")
    assert report.count("![](charts_fig_") == len(EXPECTED)
    assert len(list((tmp_path / "outputs").glob("charts_fig_*.png"))) == len(EXPECTED)


def test_the_generated_script_draws_the_same_charts(questionnaire_doc, survey, tmp_path):
    responses = survey.simulate(n=200, seed=3)
    flow = _charts_flow(weighted=False)
    runner_dir, script_dir = tmp_path / "runner", tmp_path / "script"
    result = FlowRunner(flow, questionnaire=survey, questionnaire_document=questionnaire_doc).run(
        sources={"src": responses}, cwd=runner_dir
    )
    assert result.ok
    code = generate_flow(flow, questionnaire_doc)
    assert "from siamang.reporting import Report, result_charts" in code
    assert (
        'n_c_pca = result_charts.chart(\n    [n_pca_variance, n_pca_stat],\n    kind="auto",'
        in code
    )
    (script_dir / "survey").mkdir(parents=True)
    (script_dir / "survey" / "__init__.py").write_text("", encoding="utf-8")
    (script_dir / "survey" / "questionnaire.py").write_text(
        generate_questionnaire(questionnaire_doc), encoding="utf-8"
    )
    (script_dir / "scripts").mkdir()
    script = script_dir / "scripts" / "charts.py"
    script.write_text(code, encoding="utf-8")
    snapshot = write_snapshot(responses, script_dir / "data" / "responses.csv")
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join([str(script_dir), str(ROOT)]),
        "MPLBACKEND": "Agg",
    }
    completed = subprocess.run(
        [sys.executable, str(script), "--data", str(snapshot)],
        cwd=script_dir,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    ours = (runner_dir / "outputs" / "charts.md").read_text("utf-8")
    theirs = (script_dir / "outputs" / "charts.md").read_text("utf-8")
    assert ours == theirs
    for name in sorted(path.name for path in (runner_dir / "outputs").glob("charts_fig_*.png")):
        assert (script_dir / "outputs" / name).stat().st_size > 1000


# ─── the choice models and the open answers ──────────────────────────────────


def _choice_survey():
    import siamang as sg

    items = {
        1: "Price",
        2: "Quality of the materials",
        3: "Speed of delivery",
        4: "Friendly support",
        5: "Range",
    }
    variables = [
        sg.Variable(f"md_t{task}_{side}", "nominal", label=f"t{task} {side}", labels=items)
        for task in (1, 2, 3)
        for side in ("best", "worst")
    ]
    variables.append(sg.Variable("md_version", "nominal", label="Design version"))
    maxdiff = sg.MaxDiff(
        "Which matters most?", variables, per_task=3, tasks=3, versions=4, seed=2, id="q_md"
    )
    attributes = [
        sg.Attribute(
            "brand", [sg.Option(1, "Acme"), sg.Option(2, "Globex"), sg.Option(3, "Initech")]
        ),
        sg.Attribute("price", [sg.Option(10, "10"), sg.Option(15, "15"), sg.Option(20, "20")]),
    ]
    tasks = [
        sg.Variable(f"cbc_t{t}", "nominal", label=f"Task {t}", labels={1: "1", 2: "2", 3: "3"})
        for t in (1, 2, 3, 4)
    ]
    tasks.append(sg.Variable("cbc_version", "nominal", label="Design version"))
    conjoint = sg.Conjoint(
        "Which would you buy?",
        tasks,
        attributes=attributes,
        alternatives=3,
        tasks=4,
        versions=6,
        seed=7,
        id="q_cbc",
    )
    return sg.Questionnaire(title="Choices", pages=[sg.Page(name="p", items=[maxdiff, conjoint])])


def test_maxdiff_conjoint_and_shares_are_drawn_from_their_tables(tmp_path):
    survey = _choice_survey()
    document = to_document(survey)
    products = {"Cheap Acme": {"brand": 1, "price": 10}, "Dear Globex": {"brand": 2, "price": 20}}
    flow = _flow(
        [
            ("sim", "source.simulated", {"n": 160, "seed": 4}),
            ("md", "analyze.maxdiff", {"question": "q_md"}),
            ("counts", "analyze.maxdiff", {"question": "q_md", "method": "counts"}),
            ("cbc", "analyze.conjoint", {"question": "q_cbc"}),
            ("sh", "analyze.conjoint_shares", {"question": "q_cbc", "products": products}),
            ("c_md", "visualize.result_chart", {}),
            ("c_scores", "visualize.result_chart", {"kind": "scores"}),
            ("c_counts", "visualize.result_chart", {}),
            ("c_imp", "visualize.result_chart", {}),
            ("c_pw", "visualize.result_chart", {"kind": "partworths"}),
            ("c_sh", "visualize.result_chart", {}),
        ],
        [
            *(("sim", "data", node, "data") for node in ("md", "counts", "cbc", "sh")),
            ("md", "table", "c_md", "result"),
            ("md", "table", "c_scores", "result"),
            ("counts", "table", "c_counts", "result"),
            ("cbc", "table", "c_imp", "result"),
            ("cbc", "table", "c_pw", "result"),
            ("sh", "table", "c_sh", "result"),
        ],
    )
    assert check_flow(flow, questionnaire=document) == []
    result = FlowRunner(flow, questionnaire=survey, questionnaire_document=document).run(
        cwd=tmp_path
    )
    assert result.ok
    table = result.output("md", "table").to_frame()
    utilities = result.output("c_md")
    assert utilities.drawn == "utilities"
    ticks = [label.get_text() for label in utilities.plot().get_yticklabels()]
    assert ticks == list(table["Item"])  # best first, as the table orders them
    points = sorted(
        (float(y), float(x))
        for line in utilities._ax.lines
        if line.get_marker() == "o"
        for x, y in zip(line.get_xdata(), line.get_ydata(), strict=True)
    )
    assert [x for _, x in points] == pytest.approx(list(table["Utility"]))
    # Every item but the reference has an interval: its standard error is the fit's.
    reference = result.output("md", "stat")["Reference"]
    whiskers = [c for c in utilities._ax.collections][0].get_segments()
    assert len(whiskers) == len(table) - 1
    assert any(text.get_text().endswith("(reference)") for text in utilities._ax.texts)
    assert reference in list(table["Item"])
    scores = result.output("c_scores")
    widths = [bar.get_width() for bar in scores.plot().patches]
    assert widths == pytest.approx(list(table["Score"]))
    assert result.output("c_counts").drawn == "scores"
    # The counting table has no utilities to draw: said before the run.
    flow["nodes"][7]["params"]["kind"] = "utilities"
    [issue] = check_flow(flow, questionnaire=document)
    assert issue.code == "RESULT_KIND" and "which draws 'scores'" in issue.message

    importance = result.output("c_imp")
    parts = result.output("cbc", "table").to_frame()
    assert importance.drawn == "importance"
    assert [label.get_text() for label in importance.plot().get_yticklabels()] == list(
        dict.fromkeys(parts["Attribute"])
    )
    worths = result.output("c_pw")
    assert len(worths.plot().patches) == len(parts)  # one bar per level
    # Each attribute's levels in the design's order, whatever their worth.
    ticks = [label.get_text() for label in worths._ax.get_yticklabels()]
    prices = [tick.split(": ")[1] for tick in ticks if tick.startswith("price")]
    brands = [tick.split(": ")[1] for tick in ticks if tick.startswith("brand")]
    assert prices == ["10", "15", "20"] and brands == ["Acme", "Globex", "Initech"]
    # Each chart says its base.
    for chart in (utilities, scores, importance, worths):
        assert any(text.get_text().startswith("Base: 160 respondents") for text in chart._ax.texts)
    assert len({bar.get_facecolor() for bar in worths._ax.patches}) == 2  # one colour per attribute
    shares = result.output("c_sh")
    frame = result.output("sh", "table").to_frame()
    assert [bar.get_width() for bar in shares.plot().patches] == list(frame["share"])
    assert [label.get_text() for label in shares._ax.get_yticklabels()] == list(frame["product"])


def _codeframe(path: Path, sentiment: bool) -> str:
    payload = {
        "schema_version": "1.0",
        "variable": "comment",
        "themes": [{"code": 1, "label": "Service"}, {"code": 2, "label": "Price"}],
        "assignments": {
            text_coding.fingerprint("good service"): 1,
            text_coding.fingerprint("too dear"): 2,
        },
    }
    if sentiment:
        payload["sentiment"] = {text_coding.fingerprint("good service"): 1}
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def test_themes_are_drawn_and_a_missing_sentiment_is_explained_by_the_run(tmp_path):
    from siamang.core import Variable, VariableMap
    from siamang.data import SurveyData

    variables = VariableMap()
    variables.add(Variable("comment", "nominal", label="Comment", dtype="str"))
    data = SurveyData(
        frame=__import__("pandas").DataFrame(
            {"comment": ["good service", "good service", "too dear", "meh", None]}
        ),
        variables=variables,
    )
    with_sentiment = _codeframe(tmp_path / "with.codeframe.json", True)
    without = _codeframe(tmp_path / "without.codeframe.json", False)

    def flow(codeframe, sentiment, kind):
        return _flow(
            [
                ("src", "source.responses", {}),
                ("code", "prepare.text_code", {"codeframe": codeframe, "sentiment": sentiment}),
                ("c", "visualize.result_chart", {"kind": kind}),
            ],
            [("src", "data", "code", "data"), ("code", "table", "c", "result")],
        )

    run = FlowRunner(flow(with_sentiment, True, "sentiment")).run(
        sources={"src": data}, cwd=tmp_path
    )
    assert run.ok and run.output("c").drawn == "sentiment"
    shares = FlowRunner(flow(with_sentiment, False, "auto")).run(
        sources={"src": data}, cwd=tmp_path
    )
    assert [bar.get_width() for bar in shares.output("c").plot().patches] == [66.7, 33.3]
    # Asked for sentiment without ticking it: the check says so.
    [issue] = check_flow(flow(with_sentiment, False, "sentiment"))
    assert issue.code == "RESULT_KIND" and issue.message.endswith("which draws 'shares'.")
    # Ticked, but the codeframe has none — only the run can know, and says why.
    failed = FlowRunner(flow(without, True, "sentiment")).run(
        sources={"src": data}, cwd=tmp_path, raise_on_error=False
    )
    [error] = [run.error for run in failed.runs if run.state == "error"]
    assert error == (
        "ResultChartError: There is no sentiment to draw: this codeframe was built without "
        "sentiment."
    )
    with pytest.raises(FlowError, match="Node c \\(visualize.result_chart\\) failed"):
        FlowRunner(flow(without, True, "sentiment")).run(sources={"src": data}, cwd=tmp_path)


def test_a_table_connected_alone_still_says_how_the_weight_was_used(
    questionnaire_doc, survey, tmp_path
):
    """Regression, PCA, Cluster and TURF told the chart their weight only in
    their stat: with the table alone the chart had no weight line at all —
    and Cluster, whose k-means ignores the weight, did not say so."""
    nodes = [
        ("sim", "source.simulated", {"n": 240, "seed": 5}),
        ("expl", "prepare.explode", {"variable": "aware"}),
        ("cell", "prepare.cell_weights", {"variable": "gender", "targets": {"1": 0.5, "2": 0.5}}),
        ("w", "prepare.apply_weight", {}),
        ("clu", "analyze.cluster", {"items": ["age", "satisfaction"], "k": 3}),
        ("reg", "analyze.regression", {"y": "satisfaction", "predictors": ["age", "region"]}),
        ("ord", "analyze.regression",
         {"y": "satisfaction", "predictors": ["age"], "kind": "ordinal"}),
        ("pca", "analyze.pca", {"items": ["age", "satisfaction", *TRUST]}),
        ("turf", "analyze.turf", {"items": ["aware_1", "aware_2", "aware_3"], "max_size": 2}),
    ]  # fmt: skip
    edges = [("sim", "data", "expl", "data"), ("expl", "data", "cell", "data")]
    edges.append(("cell", "data", "w", "data"))
    ports = {"clu": "table", "reg": "table", "ord": "table", "pca": "loadings", "turf": "table"}
    for node, port in ports.items():
        nodes.append((f"c_{node}", "visualize.result_chart", {}))
        edges += [("w", "data", node, "data"), (node, port, f"c_{node}", "result")]
    flow = _flow(nodes, edges)
    assert _issues(flow, questionnaire_doc) == []
    result = FlowRunner(flow, questionnaire=survey, questionnaire_document=questionnaire_doc).run(
        cwd=tmp_path
    )
    assert result.ok
    notes = {node: result.output(f"c_{node}").weight_note for node in ports}
    assert notes == {
        "clu": "unweighted (the weight 'weight' is not applied)",
        "reg": "weighted by 'weight'",
        "ord": "weighted by 'weight'",
        "pca": "weighted by 'weight'",
        "turf": "weighted by 'weight'",
    }
    # Unweighted data: no weight line, as before.
    unweighted = _flow(
        [nodes[0], nodes[5], ("c_reg", "visualize.result_chart", {})],
        [("sim", "data", "reg", "data"), ("reg", "table", "c_reg", "result")],
    )
    plain = FlowRunner(
        unweighted, questionnaire=survey, questionnaire_document=questionnaire_doc
    ).run(cwd=tmp_path)
    assert plain.output("c_reg").weight_note is None
