"""The Result chart of the later analyses — siamang.reporting.method_charts.

Key drivers, the Perceptual map and Price sensitivity are drawn by their own
modules' plot functions, so each chart is checked against the numbers of its
result, worked out by hand where the data is small enough, and read back from
the figure: bars, points, lines and their labels. Cochran's Q draws Wilson's
interval of each share (quoted from R), the ordinal logit the table's own odds
ratios and Wald intervals without its thresholds. The flow tests check, generate
and run each one on weighted data, with a report.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
import pytest

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import LineCollection, PathCollection  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

from siamang.core.variable import MissingValue, Variable, VariableMap  # noqa: E402
from siamang.data import SurveyData, correspondence, drivers, paired, pricing  # noqa: E402
from siamang.flow import FlowRunner, check_flow, default_registry, generate_flow  # noqa: E402
from siamang.model import from_document, loads  # noqa: E402
from siamang.reporting import result_charts as rc  # noqa: E402
from siamang.reporting.method_charts import labels_overlap  # noqa: E402
from siamang.reporting.tables import stat_text  # noqa: E402

DOCUMENTS = Path(__file__).resolve().parent / "documents"


@pytest.fixture(autouse=True)
def _close_figures():
    yield
    plt.close("all")


def _ticks(ax) -> list[str]:
    return [label.get_text() for label in ax.get_yticklabels()]


def _title(chart) -> str:
    return chart.plot().get_title(loc="left")  # drawn again when a run released it


# ─── Key drivers ─────────────────────────────────────────────────────────────


def _drivers_data() -> SurveyData:
    rng = np.random.default_rng(11)
    n = 240
    x = rng.normal(size=(n, 4))
    y = x @ np.array([0.8, 0.4, -0.3, 0.1]) + rng.normal(size=n)
    frame = pd.DataFrame(x, columns=["price", "staff", "queue", "parking"])
    frame["overall"] = y
    frame["w"] = rng.uniform(0.5, 1.5, n)
    variables = VariableMap()
    variables.add_many(
        [
            Variable("price", "interval", label="Price compared with other shops in the area"),
            Variable("staff", "interval", label="Friendliness of the staff"),
            Variable("queue", "interval", label="Waiting time at the tills"),
            Variable("parking", "interval", label="Parking"),
            Variable("overall", "interval", label="Overall satisfaction"),
        ]
    )
    return SurveyData(frame=frame, variables=variables).with_weight("w")


def test_key_drivers_draw_the_chart_their_module_draws():
    result = drivers.analyze(_drivers_data(), "overall", ["price", "staff", "queue", "parking"])
    table = result.table.to_frame()
    chart = rc.chart([result.table, result.stats])
    assert chart.drawn == "importance" and rc.kinds_of(result.table) == ("importance",)
    assert rc.kinds_of(result) == ("importance",)
    ax = chart._ax
    # Largest share on top, each bar its % of R², the labels the drivers'.
    assert _ticks(ax) == list(table["Driver"])
    widths = [bar.get_width() for bar in ax.patches]
    assert widths == pytest.approx(sorted(result.percent, reverse=True))
    assert sum(widths) == pytest.approx(100.0)
    assert [text.get_text() for text in ax.texts] == [f"{value:.1f} %" for value in widths]
    # The waiting time's beta is negative: its bar is the second colour.
    colours = {
        label: bar.get_facecolor() for label, bar in zip(_ticks(ax), ax.patches, strict=True)
    }
    assert colours["Waiting time at the tills"] == matplotlib.colors.to_rgba(drivers.NEGATIVE)
    assert colours["Parking"] == matplotlib.colors.to_rgba(drivers.POSITIVE)
    # The module's own chart, bar for bar, with its title lines and the weight.
    own = drivers.plot(result, figsize=chart.figsize).axes[0]
    assert widths == [bar.get_width() for bar in own.patches]
    assert _title(chart) == own.get_title(loc="left")
    assert _title(chart).splitlines() == [
        "Key drivers of Overall satisfaction",
        f"Johnson's relative weights, R² = {result.r_squared:.3f}, N = {result.n}",
        "weighted by 'w'",
    ]
    assert chart.weight_note == "weighted by 'w'"
    titled = rc.chart(result, title="What drives satisfaction")
    assert _title(titled).splitlines()[0] == "What drives satisfaction"
    # A table that has lost its result is not a Key drivers result.
    assert rc.kinds_of(dataclasses.replace(result.table, analysis=None)) == ()


# ─── Perceptual map ──────────────────────────────────────────────────────────


def _crosstab_data() -> SurveyData:
    """R's smoke table (ca::smoke) as respondents: staff group by smoking."""
    smoke = [[4, 2, 3, 2], [4, 3, 7, 4], [25, 10, 12, 4], [18, 24, 33, 13], [10, 6, 7, 2]]
    rows, columns = [], []
    for i, counts in enumerate(smoke, start=1):
        for j, count in enumerate(counts, start=1):
            rows += [i] * count
            columns += [j] * count
    variables = VariableMap()
    variables.add_many(
        [
            Variable("staff", "nominal", label="Staff group", labels={
                1: "Senior managers", 2: "Junior managers", 3: "Senior employees",
                4: "Junior employees", 5: "Secretaries"}),
            Variable("smoking", "ordinal", label="Smoking", labels={
                1: "None", 2: "Light", 3: "Medium", 4: "Heavy"}),
        ]
    )  # fmt: skip
    return SurveyData(frame=pd.DataFrame({"staff": rows, "smoking": columns}), variables=variables)


def test_a_perceptual_map_is_drawn_from_any_of_its_tables():
    result = correspondence.analyze(_crosstab_data(), "staff", column="smoking")
    for table in (result.table, result.rows, result.columns, result):
        assert rc.kinds_of(table) == ("map",)
    chart = rc.chart(result.rows)
    assert chart.drawn == "map"
    ax = chart._ax
    rows, columns = (c for c in ax.collections if isinstance(c, PathCollection))
    solution = result.solution
    assert np.asarray(rows.get_offsets()) == pytest.approx(solution.row_principal[:, :2])
    assert np.asarray(columns.get_offsets()) == pytest.approx(solution.column_principal[:, :2])
    # ca::ca(smoke): the first two dimensions carry 87.8 % and 11.8 % of the inertia.
    assert ax.get_xlabel() == "Dimension 1 (87.8 % of inertia)"
    assert ax.get_ylabel() == "Dimension 2 (11.8 % of inertia)"
    labels = sorted(text.get_text() for text in ax.texts)
    assert labels == sorted([*result.row_labels, *result.column_labels])
    assert _title(chart).splitlines()[0] == "Perceptual map: Staff group × Smoking"
    assert not labels_overlap(ax)


def _brand_grid(brands: int = 12, attributes: int = 20) -> correspondence.PerceptualMap:
    """A brand-image grid with long labels: 32 points to label on one map."""
    rng = np.random.default_rng(3)
    names = [f"Brand {chr(65 + i)} Supermarkets and Groceries" for i in range(brands)]
    ticks = [f"Attribute number {j + 1} of the image grid" for j in range(attributes)]
    where_b, where_a = rng.normal(size=(brands, 2)), rng.normal(size=(attributes, 2))
    rows = []
    for b in range(brands):
        chance = 1 / (1 + np.exp(-(0.9 * where_b[b] @ where_a.T - 0.8)))
        for _ in range(60):
            rows.append([b + 1, *(rng.random(attributes) < chance).astype(int)])
    frame = pd.DataFrame(rows, columns=["brand"] + [f"a{j}" for j in range(attributes)])
    variables = VariableMap()
    variables.add(
        Variable("brand", "nominal", label="Brand", labels=dict(enumerate(names, start=1)))
    )
    for j, label in enumerate(ticks):
        variables.add(Variable(f"a{j}", "nominal", label=label, labels={0: "No", 1: "Yes"}))
    data = SurveyData(frame=frame, variables=variables)
    return correspondence.analyze(data, "brand", attributes=[f"a{j}" for j in range(attributes)])


def test_a_crowded_map_grows_taller_rather_than_overlap_its_labels():
    grid = _brand_grid()
    # On a small figure the 32 labels cannot all be placed apart even when the
    # map grows a fifth at a time up to 1.2 times its width: its points are
    # numbered instead, their names listed under it, and it keeps its width.
    small = rc.chart(grid.table, figsize=(4, 3))
    assert small._fig.get_figwidth() == 4
    assert [text.get_text() for text in small._ax.texts] == [str(i) for i in range(1, 33)]
    key = " ".join(text.get_text() for text in small._fig.texts).replace("\n    ", " ")
    assert "1  Brand A Supermarkets and Groceries" in key
    assert "13  Attribute number 1 of the image grid" in key
    # On the node's default figure it grows until no two labels overlap.
    chart = rc.chart(grid.table)
    width, height = chart._fig.get_size_inches()
    assert width == 10 and 6 <= height <= 12
    assert not labels_overlap(chart._ax)
    assert len(chart._ax.texts) == 32


def test_labels_overlap_reads_the_texts_not_their_leader_lines():
    fig = Figure(figsize=(4, 3))
    ax = fig.add_subplot(1, 1, 1)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.text(1, 1, "a label", fontsize=10)
    ax.annotate("far away", (1.2, 1.2), xytext=(8, 8), arrowprops={"arrowstyle": "-"})
    assert not labels_overlap(ax)  # the line crosses the first label's box; the texts do not
    ax.text(1.3, 1.1, "on top", fontsize=10)
    assert labels_overlap(ax)


# ─── Price sensitivity ───────────────────────────────────────────────────────


def _prices() -> SurveyData:
    """A: 10, 20, 30, 40; B: 20, 30, 40, 50; C answered out of order; D refused one."""
    frame = pd.DataFrame(
        {
            "tc": [10, 20, 30, 10],
            "ch": [20, 30, 20, 20],
            "ex": [30, 40, 40, 99],
            "te": [40, 50, 50, 40],
            "lc": [5, 4, 3, 5],
            "le": [3, 2, 1, 3],
            "w": [1.0, 1.0, 1.0, 1.0],
        }
    )
    variables = VariableMap()
    variables.add_many(
        [
            Variable("tc", "ratio", label="Too cheap"),
            Variable("ch", "ratio", label="A bargain"),
            Variable("ex", "ratio", label="Getting expensive",
                     missing=(MissingValue(99, "Refused"),)),
            Variable("te", "ratio", label="Too expensive"),
        ]
    )  # fmt: skip
    return SurveyData(frame=frame, variables=variables).with_weight("w")


QUESTIONS = {"too_cheap": "tc", "cheap": "ch", "expensive": "ex", "too_expensive": "te"}


def test_van_westendorp_draws_its_curves_and_points():
    result = pricing.van_westendorp(_prices(), **QUESTIONS)
    for table in (result.table, result.curves, result):
        assert rc.kinds_of(table) == ("curves",)
    chart = rc.chart(result.curves)
    assert chart.drawn == "curves" and len(chart._fig.axes) == 1
    ax = chart._ax
    # By hand, on the grid 10 … 50 (A and B answered in order).
    curves = {
        line.get_label(): list(line.get_ydata()) for line in ax.lines if line.get_label()[0] != "_"
    }
    assert curves == {
        "Too cheap": [100.0, 50.0, 0.0, 0.0, 0.0],
        "Not cheap": [0.0, 0.0, 50.0, 100.0, 100.0],
        "Not expensive": [100.0, 100.0, 50.0, 0.0, 0.0],
        "Too expensive": [0.0, 0.0, 0.0, 50.0, 100.0],
    }
    names = sorted(text.get_text() for text in ax.texts)
    assert names == ["IPP 30", "OPP 30", "PMC 25", "PME 35"]
    assert _title(chart).splitlines() == [
        "Price sensitivity (Van Westendorp)",
        "N = 2, weighted by 'w'",
    ]
    assert chart.weight_note == "weighted by 'w'"


def test_two_price_panels_are_drawn_tall_enough():
    nms = pricing.van_westendorp(
        _prices(), **QUESTIONS, likelihood_cheap="lc", likelihood_expensive="le"
    )
    chart = rc.chart(nms.table, figsize=(8, 4))
    assert len(chart._fig.axes) == 2
    assert tuple(chart._fig.get_size_inches()) == (8.0, 6.0)
    assert chart._fig.axes[1].get_ylabel() == "Trial (% would buy)"
    assert tuple(rc.chart(nms, figsize=(8, 9))._fig.get_size_inches()) == (8.0, 9.0)
    one = pricing.van_westendorp(_prices(), **QUESTIONS)
    assert tuple(rc.chart(one, figsize=(8, 4))._fig.get_size_inches()) == (8.0, 4.0)


def test_gabor_granger_draws_demand_over_revenue():
    # Three of four would buy at 5 and one at 10: demand 75 % and 25 %,
    # revenue per respondent 5 × 0.75 = 3.75 and 10 × 0.25 = 2.50.
    frame = pd.DataFrame({"p5": [1, 1, 1, 0], "p10": [1, 0, 0, 0]})
    result = pricing.gabor_granger(SurveyData(frame=frame), ["p5", "p10"], prices=[5, 10])
    chart = rc.chart(result.table)
    demand_ax, revenue_ax = chart._fig.axes
    [line] = [line for line in demand_ax.lines if line.get_marker() == "o"]
    assert list(line.get_xdata()) == [5, 10] and list(line.get_ydata()) == [75.0, 25.0]
    bars = revenue_ax.patches
    assert [bar.get_height() for bar in bars] == pytest.approx([3.75, 2.5])
    # The best price in the full colour, the other lighter.
    assert bars[0].get_facecolor() == matplotlib.colors.to_rgba(pricing.EXPENSIVE_COLOUR)
    assert bars[1].get_facecolor() != bars[0].get_facecolor()
    assert "highest revenue at 5" in [text.get_text() for text in demand_ax.texts]
    assert chart.weight_note is None


# ─── Cochran's Q ─────────────────────────────────────────────────────────────


def _yes_no() -> SurveyData:
    """20 respondents; 12, 8 and 4 of them say yes to a, b and c."""
    frame = pd.DataFrame(
        {
            "a": [1] * 12 + [0] * 8,
            "b": [1] * 8 + [0] * 12,
            "c": [1] * 4 + [0] * 16,
            "w": np.linspace(0.5, 1.5, 20),
        }
    )
    variables = VariableMap()
    for name, label in (
        ("a", "Aware of Acme"),
        ("b", "Aware of Globex"),
        ("c", "Aware of Initech"),
    ):
        variables.add(Variable(name, "nominal", label=label, labels={0: "No", 1: "Yes"}))
    return SurveyData(frame=frame, variables=variables).with_weight("w")


def test_cochrans_q_draws_each_share_with_wilsons_interval():
    result = paired.cochran(_yes_no(), ["a", "b", "c"])
    assert rc.kinds_of(result.table) == ("shares",) and rc.kinds_of(result) == ("shares",)
    chart = rc.chart(result.table)
    ax = chart._ax
    assert _ticks(ax) == ["Aware of Acme", "Aware of Globex", "Aware of Initech"]
    points = sorted(
        (float(y), float(x))
        for line in ax.lines
        if isinstance(line, Line2D) and line.get_marker() == "o"
        for x, y in zip(line.get_xdata(), line.get_ydata(), strict=True)
    )
    assert [x for _, x in points] == pytest.approx([60.0, 40.0, 20.0])
    # R: prop.test(12, 20, correct = FALSE)$conf.int -> 0.3865815 0.7811935;
    # prop.test(8, 20, ...) -> 0.2188065 0.6134185; prop.test(4, 20, ...) ->
    # 0.08065766 0.41601743.
    [whiskers] = [c for c in ax.collections if isinstance(c, LineCollection)]
    segments = sorted(
        (float(y0), float(x0), float(x1)) for (x0, y0), (x1, _) in whiskers.get_segments()
    )
    assert [x for segment in segments for x in segment[1:]] == pytest.approx(
        [38.65815, 78.11935, 21.88065, 61.34185, 8.065766, 41.601743], abs=1e-5
    )
    assert ax.get_xlim() == (0, 100)
    notes = " ".join(text.get_text() for text in ax.texts)
    assert f"Cochran's Q, p = {stat_text(result.stats['p'])}" in " ".join(notes.split())
    assert _title(chart).splitlines() == [
        "Cochran's Q: the share saying yes to each",
        "unweighted (the weight 'w' is not applied)",
    ]
    assert rc.chart(result).drawn == "shares"  # the result itself is drawable too


# ─── The ordinal logit ───────────────────────────────────────────────────────


def _ordinal() -> SurveyData:
    rng = np.random.default_rng(5)
    n = 300
    x1, x2 = rng.normal(size=n), rng.normal(size=n)
    answer = np.digitize(0.9 * x1 - 0.6 * x2 + rng.logistic(size=n), [-1.2, 0.0, 1.2]) + 1
    frame = pd.DataFrame({"y": answer, "x1": x1, "x2": x2})
    variables = VariableMap()
    variables.add(
        Variable("y", "ordinal", label="Satisfaction",
                 labels={1: "Low", 2: "Medium", 3: "High", 4: "Top"})
    )  # fmt: skip
    return SurveyData(frame=frame, variables=variables)


def test_an_ordinal_logit_draws_its_odds_ratios_without_the_thresholds():
    model = _ordinal().analysis.regression("y", ["x1", "x2"], kind="ordinal")
    table = model.table
    assert list(table["type"]) == ["coefficient"] * 2 + ["threshold"] * 3
    for chart in (rc.chart([table, model.stats]), rc.chart(model)):
        ax = chart._ax
        assert chart.drawn == "coefficients" and ax.get_xscale() == "log"
        assert _ticks(ax) == ["x1", "x2"]  # not Low / Medium, Medium / High, High / Top
        points = sorted(
            (float(y), float(x))
            for line in ax.lines
            if line.get_marker() == "o"
            for x, y in zip(line.get_xdata(), line.get_ydata(), strict=True)
        )
        assert [x for _, x in points] == pytest.approx(list(table["odds_ratio"][:2]))
        # The table's own Wald interval (R's exp(confint.default(fit))).
        [whiskers] = [c for c in ax.collections if isinstance(c, LineCollection)]
        segments = sorted((y0, x0, x1) for (x0, y0), (x1, _) in whiskers.get_segments())
        assert [s[1] for s in segments] == pytest.approx(list(table["odds_ratio_lower"][:2]))
        assert [s[2] for s in segments] == pytest.approx(list(table["odds_ratio_upper"][:2]))
        assert _title(chart) == "Ordinal logit: odds ratios — Satisfaction"  # the label
        note = " ".join(" ".join(text.get_text() for text in ax.texts).split())
        assert (
            "An odds ratio above 1 makes the higher answers more likely "
            "(Low < Medium < High < Top)" in note
        )
    # An ordinary regression keeps its forest and title.
    ols = _ordinal().analysis.regression("y", ["x1", "x2"], kind="ols")
    assert _title(rc.chart(ols)).startswith("Regression coefficients")


def test_the_new_results_are_listed_when_nothing_can_be_drawn():
    with pytest.raises(rc.ResultChartError) as error:
        rc.chart(pd.DataFrame({"x": [1]}))
    assert str(error.value).endswith(
        "Code open answers, Key drivers, Perceptual map, Price sensitivity — connect the "
        "table of one of them."
    )
    assert set(rc.KINDS) >= {"map", "curves"}
    spec = default_registry().get("visualize.result_chart")
    assert spec.params["kind"].values[-2:] == ("map", "curves")


# ─── In a flow ───────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def questionnaire_doc():
    return loads((DOCUMENTS / "brand_awareness.questionnaire.json").read_text("utf-8"))


@pytest.fixture(scope="module")
def survey(questionnaire_doc):
    return from_document(questionnaire_doc).survey


def _flow(nodes, edges, name="method_charts"):
    return {
        "schema_version": "1.0",
        "name": name,
        "nodes": [{"id": i, "type": t, "params": p} for i, t, p in nodes],
        "edges": [
            {"from": {"node": a, "port": ap}, "to": {"node": b, "port": bp}}
            for a, ap, b, bp in edges
        ],
    }


AWARE = ["aware_1", "aware_2", "aware_3"]
# (analysis id, type, params, ports connected to its chart, chart params)
ANALYSES = [
    ("kd", "analyze.drivers", {"y": "satisfaction", "predictors": ["trust_acme", "trust_globex", "age"]}, ["table"], {}),
    ("xt", "analyze.correspondence", {"row": "region", "column": "gender"}, ["rows"], {}),
    ("at", "analyze.correspondence", {"layout": "attributes", "row": "region", "attributes": AWARE}, ["table", "stat"], {"kind": "map", "title": "Awareness by region"}),
    ("coch", "analyze.paired", {"variables": AWARE, "test": "cochran"}, ["table"], {}),
    ("ord", "analyze.regression", {"y": "satisfaction", "predictors": ["trust_acme", "age"], "kind": "ordinal"}, ["table", "stat"], {}),
]  # fmt: skip
EXPECTED = {
    "c_kd": ("importance", "weighted by 'weight'", "DriverTable"),
    "c_xt": ("map", "weighted by 'weight'", "MapTable"),
    "c_at": ("map", "weighted by 'weight'", "MapTable"),
    "c_coch": ("shares", "unweighted (the weight 'weight' is not applied)", "ResultTable"),
    "c_ord": ("coefficients", "weighted by 'weight'", "DataFrame"),
}


def _methods_flow():
    nodes = [
        ("sim", "source.simulated", {"n": 400, "seed": 21}),
        ("expl", "prepare.explode", {"variable": "aware"}),
        ("cell", "prepare.cell_weights", {"variable": "gender", "targets": {"1": 0.5, "2": 0.5}}),
        ("w", "prepare.apply_weight", {}),
    ]
    edges = [("sim", "data", "expl", "data"), ("expl", "data", "cell", "data")]
    edges.append(("cell", "data", "w", "data"))
    for node, kind, params, ports, chart in ANALYSES:
        nodes += [(node, kind, params), (f"c_{node}", "visualize.result_chart", chart)]
        edges.append(("w", "data", node, "data"))
        edges += [(node, port, f"c_{node}", "result") for port in ports]
        edges.append((f"c_{node}", "chart", "sec", "items"))
    nodes += [
        ("sec", "output.report_section", {"heading": "The methods, drawn"}),
        ("save", "output.save_report", {"title": "Methods", "path": "outputs/methods.md"}),
    ]
    edges.append(("sec", "report", "save", "sections"))
    return _flow(nodes, edges)


def test_the_new_results_are_checked_generated_and_drawn_weighted(
    questionnaire_doc, survey, tmp_path
):
    flow = _methods_flow()
    assert check_flow(flow, questionnaire=questionnaire_doc) == []
    code = generate_flow(flow, questionnaire_doc)
    assert (
        'n_c_ord = result_charts.chart(\n    [n_ord_table, n_ord_stat],\n    kind="auto",' in code
    )
    assert 'n_c_at = result_charts.chart(\n    [n_at_table, n_at_stat],\n    kind="map",' in code
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
        assert _title(chart).endswith(note), node
    assert _title(result.output("c_at")).startswith("Awareness by region\n")
    assert _ticks(result.output("c_ord").plot()) == ["Trust: Acme", "Age"]  # by label
    # What each output draws, as the check reads it, is what the run draws.
    for node, kind, params, ports, _ in ANALYSES:
        spec = default_registry().get(kind)
        resolved = {**{k: p.default for k, p in spec.params.items()}, **params}
        for port in ports:
            expected = rc.output_kinds(kind, port, resolved)
            if expected is not None:
                assert rc.kinds_of(result.output(node, port)) == expected, (node, port)
    report = (tmp_path / "outputs" / "methods.md").read_text("utf-8")
    assert report.count("![](methods_fig_") == len(EXPECTED)
    assert len(list((tmp_path / "outputs").glob("methods_fig_*.png"))) == len(EXPECTED)


def test_the_check_says_what_the_new_outputs_draw(questionnaire_doc):
    flow = _methods_flow()
    params = {node["id"]: node["params"] for node in flow["nodes"]}
    params["c_kd"]["kind"] = "map"
    params["c_coch"]["kind"] = "means"
    params["c_xt"]["kind"] = "curves"
    issues = sorted(
        (issue.code, issue.message) for issue in check_flow(flow, questionnaire=questionnaire_doc)
    )
    assert issues == [
        (
            "RESULT_KIND",
            "c_coch: Kind 'means' does not suit the table output of Paired tests (coch), "
            "which draws 'shares'.",
        ),
        (
            "RESULT_KIND",
            "c_kd: Kind 'map' does not suit the table output of Key drivers (kd), which draws "
            "'importance'.",
        ),
        (
            "RESULT_KIND",
            "c_xt: Kind 'curves' does not suit the rows output of Perceptual map (xt), which "
            "draws 'map'.",
        ),
    ]
    # A stat alone lends the weight and draws nothing: the output that draws is named.
    stat_only = _flow(
        [
            ("src", "source.responses", {}),
            ("kd", "analyze.drivers", {"y": "satisfaction", "predictors": ["age", "trust_acme"]}),
            ("c", "visualize.result_chart", {}),
        ],
        [("src", "data", "kd", "data"), ("kd", "stat", "c", "result")],
    )
    [issue] = check_flow(stat_only, questionnaire=questionnaire_doc)
    assert issue.message == (
        "c: The stat output of Key drivers (kd) only tells a chart its weight and base; "
        "connect the output it draws, table, too."
    )


def _price_source():
    rng = np.random.default_rng(3)
    n = 240
    base = rng.lognormal(np.log(10), 0.25, n)
    frame = pd.DataFrame(
        {
            "tc": np.round(base * 0.5, 1),
            "ch": np.round(base * 0.8, 1),
            "ex": np.round(base * 1.2, 1),
            "te": np.round(base * 1.7, 1),
            "lc": rng.integers(1, 6, n),
            "le": rng.integers(1, 6, n),
            "wt": rng.uniform(0.5, 1.5, n),
        }
    )
    wtp = base * rng.uniform(0.8, 1.2, n)
    for price in (6, 8, 10, 12):
        frame[f"gg{price}"] = (wtp >= price).astype(int)
    variables = VariableMap()
    variables.add_many(
        [Variable(name, "ratio", label=name) for name in ("tc", "ch", "ex", "te")]
        + [Variable(name, "ordinal") for name in ("lc", "le")]
        + [Variable(f"gg{p}", "nominal", labels={0: "No", 1: "Yes"}) for p in (6, 8, 10, 12)]
    )
    questionnaire = {
        "variables": {
            name: {"scale": variables[name].scale, "label": variables[name].label}
            for name in variables
        }
    }
    return SurveyData(frame=frame, variables=variables), questionnaire


def test_price_sensitivity_is_drawn_in_a_flow(tmp_path):
    data, questionnaire = _price_source()
    vw = {"too_cheap": "tc", "cheap": "ch", "expensive": "ex", "too_expensive": "te"}
    gg = {"method": "gabor_granger", "intent": ["gg6", "gg8", "gg10", "gg12"],
          "price_points": [6, 8, 10, 12]}  # fmt: skip
    flow = _flow(
        [
            ("src", "source.responses", {}),
            ("apply", "prepare.apply_weight", {"column": "wt"}),
            (
                "nms",
                "analyze.price",
                {**vw, "likelihood_cheap": "lc", "likelihood_expensive": "le"},
            ),
            ("gg", "analyze.price", gg),
            ("c_nms", "visualize.result_chart", {"kind": "curves"}),
            ("c_gg", "visualize.result_chart", {"width": 6, "height": 4}),
        ],
        [
            ("src", "data", "apply", "data"),
            ("apply", "data", "nms", "data"),
            ("apply", "data", "gg", "data"),
            ("nms", "curves", "c_nms", "result"),
            ("gg", "table", "c_gg", "result"),
            ("gg", "stat", "c_gg", "result"),
        ],
    )
    assert check_flow(flow, questionnaire=questionnaire) == []
    result = FlowRunner(flow).run(sources={"src": data}, cwd=tmp_path)
    assert result.ok
    nms, gabor = result.output("c_nms"), result.output("c_gg")
    nms.plot(), gabor.plot()  # a run releases each figure once rendered
    assert (nms.drawn, gabor.drawn) == ("curves", "curves")
    assert [len(chart._fig.axes) for chart in (nms, gabor)] == [2, 2]
    assert tuple(gabor._fig.get_size_inches()) == (6.0, 6.0)
    assert nms.weight_note == gabor.weight_note == "weighted by 'wt'"
    analysis = result.output("nms", "table").analysis
    [trial] = [line for line in nms._fig.axes[1].lines if line.get_label() == "Trial (NMS)"]
    assert list(trial.get_ydata()) == pytest.approx(list(analysis.shares["trial"]))
    flow["nodes"][4]["params"]["kind"] = "importance"
    [issue] = check_flow(flow, questionnaire=questionnaire)
    assert issue.message == (
        "c_nms: Kind 'importance' does not suit the curves output of Price sensitivity "
        "(nms), which draws 'curves'."
    )


def test_the_key_drivers_chart_has_no_row_lines_whatever_was_drawn_before():
    """The Result chart sets seaborn's whitegrid theme, whose row lines struck
    through every bar and its "57.8 %"; drivers.plot alone drew them too once
    any chart had set the theme."""
    import seaborn as sns

    result = drivers.analyze(_drivers_data(), "overall", ["price", "staff", "queue", "parking"])
    flow_chart = rc.chart(result.table)
    assert not any(line.get_visible() for line in flow_chart._ax.yaxis.get_gridlines())
    assert any(line.get_visible() for line in flow_chart._ax.xaxis.get_gridlines())
    sns.set_theme(style="whitegrid")
    try:
        own = drivers.plot(result).axes[0]
    finally:
        sns.reset_orig()
    assert not any(line.get_visible() for line in own.yaxis.get_gridlines())
    title = flow_chart._ax.get_title(loc="left").splitlines()
    assert title[1].endswith(f", N = {result.n}")


def test_a_map_too_crowded_to_name_its_points_numbers_them_and_lists_the_names():
    """24 brands of long names by 13 regions: at its tallest the map still
    printed names over names ('Umbrella Pharmaceuticals Over-Scotland'), cut
    others with '…', and its legend's variable title too."""

    rng = np.random.default_rng(3)
    brands = [f"Brand {i:02d} with a rather long descriptive product name" for i in range(1, 25)]
    regions = [f"Region number {i} of the country" for i in range(1, 14)]
    frame = pd.DataFrame(
        {
            "brand": rng.choice(np.arange(1, 25), 1200, p=rng.dirichlet(np.ones(24))).astype(float),
            "region": rng.integers(1, 14, 1200).astype(float),
        }
    )
    variables = VariableMap()
    title = "Brand bought most often in the last three months"
    variables.add(Variable("brand", "nominal", label=title, labels=dict(enumerate(brands, 1))))
    variables.add(Variable("region", "nominal", label="Region", labels=dict(enumerate(regions, 1))))
    result = correspondence.analyze(
        SurveyData(frame=frame, variables=variables), "brand", column="region"
    )
    chart = rc.chart(result.table)
    fig, ax = chart._fig, chart._ax
    names = [*result.row_labels, *result.column_labels]
    assert len(names) > 30
    assert [text.get_text() for text in ax.texts] == [str(i) for i in range(1, len(names) + 1)]
    assert not labels_overlap(ax)
    renderer = fig.canvas.get_renderer()
    key = [text for text in fig.texts if text.get_text()]
    listed = " ".join(text.get_text() for text in key).replace("\n    ", " ")
    assert all(f"{i}  {name}" in listed for i, name in enumerate(names, 1))
    assert set(result.column_labels) == set(regions)
    legend = ax.get_legend()
    assert [text.get_text().replace("\n", " ") for text in legend.get_texts()] == [title, "Region"]
    below = legend.get_window_extent(renderer)
    assert below.y1 <= ax.xaxis.label.get_window_extent(renderer).y0
    for text in key:
        box = text.get_window_extent(renderer)
        assert box.y0 >= -1 and box.x1 <= fig.bbox.x1 + 1 and box.y1 <= below.y0
    # Asked for names, the map names its points, crowded or not.
    named = correspondence.plot(result, numbered=False)
    assert named.axes[0].texts[0].get_text().startswith("Brand 01")
