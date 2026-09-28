"""Interactive charts: every chart's Vega-Lite spec, and a report that draws them.

Each chart says what it draws as a Vega-Lite 6 spec (``SurveyChart.vega_lite()``,
:mod:`siamang.reporting.vega`). These tests hold the specs to what the owner
asked of them: valid against the Vega-Lite 6.4.3 JSON Schema (vendored in
``tests/fixtures``), drawn from the same numbers as the picture, carrying only
what the chart draws (no respondent's row where the chart aggregates; only the
plotted values where it plots respondents), and drawn by the vendored
libraries in headless Chromium without an error, a warning or a request to
anywhere. A report saved with ``interactive=True`` carries the libraries once
and names no address; saved without it, a report is what it always was.

The browser tests need Node, the ``playwright`` package and a Chromium it can
launch, and are skipped without them (``NODE_PATH`` and ``PLAYWRIGHT_CHROMIUM``
as ``tests/test_runtime_browser.py`` says).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np
import pandas as pd
import pytest

matplotlib.use("Agg")

from jsonschema import Draft7Validator  # noqa: E402
from jsonschema.exceptions import best_match  # noqa: E402

from siamang.core.variable import Variable, VariableMap  # noqa: E402
from siamang.data import SurveyData  # noqa: E402
from siamang.flow import FlowRunner, check_flow, live  # noqa: E402
from siamang.flow.template import render_node  # noqa: E402
from siamang.reporting import Report, vega  # noqa: E402
from siamang.reporting import result_charts as rc  # noqa: E402
from siamang.reporting.bars import value_text  # noqa: E402
from siamang.reporting.charts import BarChart, BoxPlot, HeatMap, ScatterPlot  # noqa: E402
from siamang.reporting.likert import LikertChart  # noqa: E402
from siamang.reporting.trend import TrendChart  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SCHEMA = FIXTURES / "vega-lite-v6.4.3.schema.json"
N = 400


# ─── the data ────────────────────────────────────────────────────────────────


def _survey(weighted: bool = False) -> SurveyData:
    """400 respondents: a satisfaction scale with a missing code, a region, an
    age, an income, a multiple-choice question, three items on one scale, an
    interview date and a wave — and an id no spec may carry."""

    rng = np.random.default_rng(7)
    region = rng.choice([1, 2, 3, 4], size=N, p=[0.35, 0.3, 0.2, 0.15])
    satisfaction = np.clip(np.round(rng.normal(3.4 + 0.2 * (region == 2), 1.1, N)), 1, 5)
    satisfaction[rng.random(N) < 0.05] = 9
    items = {f"t{i}": np.clip(np.round(rng.normal(3 + 0.4 * i, 1.0, N)), 1, 5) for i in range(1, 4)}
    frame = pd.DataFrame(
        {
            "respondent_id": [f"RID-{index:05d}-SECRET" for index in range(N)],
            "region": region,
            "sat": satisfaction,
            "age": np.round(rng.normal(44, 14, N)).clip(18, 90),
            "income": np.round(rng.lognormal(10.5, 0.5, N), -2),
            "brands": [
                list(rng.choice([1, 2, 3, 4], size=rng.integers(0, 3), replace=False).tolist())
                for _ in range(N)
            ],
            "date": (
                pd.Timestamp("2026-01-01") + pd.to_timedelta(rng.integers(0, 180, N), unit="D")
            ).strftime("%Y-%m-%d"),
            "wave": rng.choice([1, 2, 3], size=N),
            "w": rng.uniform(0.5, 1.8, N).round(3),
            **items,
        }
    )
    scale = {
        1: "Very dissatisfied",
        2: "Dissatisfied",
        3: "Neither",
        4: "Satisfied",
        5: "Very satisfied",
    }
    variables = VariableMap()
    variables.add_many(
        [
            Variable("respondent_id", "nominal", label="Respondent"),
            Variable(
                "region",
                "nominal",
                label="Region",
                labels={1: "North", 2: "South", 3: "East", 4: "Capital metropolitan area"},
            ),
            Variable(
                "sat",
                "ordinal",
                label="Overall satisfaction",
                labels={**scale, 9: "Don't know"},
                missing_values=(9,),
                missing_labels={9: "Don't know"},
            ),
            Variable("age", "ratio", label="Age"),
            Variable("income", "ratio", label="Household income"),
            Variable(
                "brands",
                "nominal",
                label="Brands used",
                labels={1: "Acme", 2: "Globex", 3: "Initech", 4: "Umbrella"},
            ),
            Variable("date", "nominal", label="Interview date"),
            Variable(
                "wave", "ordinal", label="Wave", labels={1: "Spring", 2: "Summer", 3: "Autumn"}
            ),
            Variable("w", "ratio", label="Weight"),
            *[
                Variable(f"t{i}", "ordinal", label=f"Trust: {name}", labels=scale)
                for i, name in zip(range(1, 4), ["Acme", "Globex", "Initech"], strict=True)
            ],
        ]
    )
    data = SurveyData(frame=frame, variables=variables)
    return data.with_weight("w") if weighted else data


def _with_gaps() -> SurveyData:
    """The weighted survey with a quarter of the second item unanswered: a
    means heatmap's cell then counts fewer respondents than its group."""

    data = _survey(weighted=True)
    frame = data.frame.copy()
    gaps = np.random.default_rng(11).random(len(frame)) < 0.25
    frame.loc[gaps, "t2"] = np.nan
    return SurveyData(frame=frame, variables=data.variables).with_weight("w")


def _charts() -> dict[str, Any]:
    """Every chart form with an interactive one, by name."""

    d, w = _survey(), _survey(weighted=True)
    return {
        "bar_classic": BarChart(d, column="sat"),
        "bar_classic_means": BarChart(d, column="age", by="region", horizontal=True),
        "bar_percent": BarChart(w, column="sat", show="percent", intervals=True, palette="theme"),
        "bar_split_letters": BarChart(
            d, column="sat", split="region", show="percent", letters=True
        ),
        "bar_stacked": BarChart(d, column="sat", split="region", layout="stacked"),
        "bar_stacked_100": BarChart(
            w, column="sat", split="region", layout="stacked_100", horizontal=True, palette="theme"
        ),
        "bar_top_other": BarChart(
            d, column="brands", show="percent", top=2, other=True, sort="value"
        ),
        "bar_means_intervals": BarChart(d, column="age", by="region", intervals=True, sort="value"),
        "histogram": BarChart(d, column="age", layout="histogram"),
        "histogram_split": BarChart(
            w, column="age", layout="histogram", split="region", show="percent"
        ),
        "donut": BarChart(w, column="sat", layout="donut", palette="theme"),
        # Every slice holds its own value: no value is written outside the ring.
        "donut_inside": BarChart(d, column="region", layout="donut"),
        "likert": LikertChart(d, columns=["t1", "t2", "t3"]),
        "likert_side": LikertChart(w, columns=["t1", "t2", "t3"], neutral="side", palette="theme"),
        "heatmap_spearman": HeatMap(w, columns=["t1", "t2", "t3", "age"]),
        "heatmap_pearson": HeatMap(w, columns=["t1", "t2", "t3", "age"], method="pearson"),
        "heatmap_means": HeatMap(d, columns=["t1", "t2", "t3"], by="region"),
        "heatmap_means_theme": HeatMap(w, columns=["t1", "t2", "t3"], by="region", cmap="theme"),
        "heatmap_means_gaps": HeatMap(
            _with_gaps(), columns=["t1", "t2", "t3"], by="region", cmap="theme"
        ),
        "boxplot": BoxPlot(d, column="income", by="region"),
        "boxplot_points": BoxPlot(w, column="age", by="region", show_points=True, palette="theme"),
        "scatter": ScatterPlot(d, x="age", y="income"),
        "scatter_hue": ScatterPlot(d, x="age", y="income", hue="region", palette="theme"),
        "trend": TrendChart(
            d, time="date", period="month", measure="percent", variable="sat", codes=[4, 5]
        ),
        "trend_by": TrendChart(
            w, time="date", period="month", measure="mean", variable="age", by="region"
        ),
        "trend_waves": TrendChart(d, time="wave", measure="count"),
        "trend_daily": TrendChart(d, time="date", period="day", measure="count"),
    }


@pytest.fixture(scope="module")
def charts() -> dict[str, Any]:
    import matplotlib.pyplot as plt

    matplotlib.rcParams["figure.max_open_warning"] = 0  # every chart is kept to be read
    made = _charts()
    yield made
    plt.close("all")


@pytest.fixture(scope="module")
def specs(charts) -> dict[str, dict[str, Any]]:
    return {name: chart.vega_lite() for name, chart in charts.items()}


@pytest.fixture(scope="module")
def validator() -> Draft7Validator:
    return Draft7Validator(json.loads(SCHEMA.read_text("utf-8")))


def _main(spec: dict[str, Any]) -> dict[str, Any]:
    """The chart's own view: the first of a spec with notes under it."""

    return spec["vconcat"][0] if len(spec.get("vconcat", [])) == 1 else spec


def _datasets(spec: Any) -> list[list[dict[str, Any]]]:
    """Every inline dataset of ``spec``, wherever it is."""

    found = []
    if isinstance(spec, dict):
        data = spec.get("data")
        if isinstance(data, dict) and isinstance(data.get("values"), list):
            found.append(data["values"])
        for key, value in spec.items():
            if key != "data":
                found += _datasets(value)
    elif isinstance(spec, list):
        for item in spec:
            found += _datasets(item)
    return found


def _rows(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """The chart's own rows: the main view's (first) dataset."""

    return _datasets(_main(spec))[0]


# ─── the specs ───────────────────────────────────────────────────────────────


class _Funnel:
    """A result a later node registers a renderer of its own for."""

    def __init__(self, steps: dict[str, float]) -> None:
        self.steps = steps
        self.stats: dict[str, Any] = {}


def _own_figure() -> Any:
    """A Result chart whose renderer draws a figure of its own, with none of
    the shared forms: it has no interactive form."""

    def draw(result: _Funnel, chart: Any) -> str:
        _, ax = chart.figure()
        ax.plot(list(result.steps), list(result.steps.values()))
        return "Funnel"

    renderer = rc.register(_Funnel, ["funnel"], draw, name="Funnel")
    try:
        return rc.chart(_Funnel({"Saw it": 100, "Clicked": 40, "Bought": 5}))
    finally:
        rc._RENDERERS.remove(renderer)


def test_every_chart_form_has_a_spec_and_a_chart_without_one_says_none(charts, specs):
    assert all(spec is not None for spec in specs.values()), [
        name for name, spec in specs.items() if spec is None
    ]
    # A Result chart has its spec (tests/test_interactive_result_charts.py);
    # a later node's renderer that draws a figure of its own has none, and
    # its report shows its picture.
    assert rc.chart(_survey().report.means("age", by="region")).vega_lite() is not None
    assert _own_figure().vega_lite() is None


def test_every_spec_is_valid_vega_lite_6(specs, validator):
    for name, spec in specs.items():
        assert spec["$schema"] == vega.SCHEMA == "https://vega.github.io/schema/vega-lite/v6.json"
        errors = list(validator.iter_errors(spec))
        assert not errors, f"{name}: {best_match(errors).message[:400]}"
        # JSON as JSON is: no NaN, no infinity.
        json.dumps(spec, allow_nan=False)


def test_every_spec_says_what_the_picture_says(charts, specs):
    """The title, the notes under the plot, the look, a description, a
    tooltip with the base on the chart's marks."""

    for name, spec in specs.items():
        chart = charts[name]
        assert spec["description"] and len(spec["description"]) > 20, name
        assert spec["config"]["font"], name
        assert spec["usermeta"]["siamang"]["vega-lite"] == "6.4.3"
        title = spec["title"]["text"]
        # One line, or the lines for the width drawn at, chosen in the browser.
        assert (
            (title["expr"].startswith("containerSize()[0] >="))
            if isinstance(title, dict)
            else title.strip()
        ), name
        notes = spec["usermeta"]["siamang"]["notes"]
        if notes:
            foot = _main(spec)["title"]
            assert foot["orient"] == "bottom" and foot["anchor"] == "start", name
            written = json.dumps(foot["text"], ensure_ascii=False)
            assert all(word in written for word in notes[0].split()[:3]), name
        text = json.dumps(spec)
        if "base" in json.dumps(_rows(spec)[:1]):
            assert '"title": "Base"' in text, name
        weight_note = chart.weight_note
        if weight_note and weight_note.startswith("unweighted"):
            # The picture's second title line: the spec's subtitle.
            assert spec["title"].get("subtitle") == [weight_note], name


def test_the_theme_colors_and_the_look(charts, specs):
    from siamang.reporting import chart_theme

    spec = specs["bar_split_letters"]
    colour = _main(spec)["layer"][0]["encoding"]["color"]
    # The picture's colors, in its series' order, and the default look.
    assert colour["scale"]["domain"] == list(charts["bar_split_letters"]._drawn.bars.series)
    assert colour["scale"]["range"] == charts["bar_split_letters"]._drawn.colours
    assert spec["config"]["axis"]["labelColor"] == chart_theme.TEXT
    assert spec["config"]["axis"]["gridColor"] == chart_theme.GRID
    # A chart of palette "theme" takes the theme's palette.
    donut = _main(specs["donut"])["layer"][0]["encoding"]["color"]["scale"]["range"]
    assert set(donut) <= set(chart_theme.ChartColours().series(5, ordered=True)) | {
        chart_theme.NEUTRAL
    }


def test_a_report_theme_s_colors_and_font_reach_the_spec():
    from siamang.reporting import ReportTheme, chart_theme

    theme = ReportTheme(
        chart_palette=("#123456", "#abcdef", "#ff8800"),
        chart_text_color="#222244",
        chart_grid_color="#dddddd",
        chart_font="Georgia, serif",
    )
    chart = BarChart(_survey(), column="sat", split="region", show="percent", palette="theme")
    shown = chart_theme.in_report(chart, theme)
    spec = shown.vega_lite()
    assert spec["config"]["font"] == "Georgia, serif"
    assert spec["config"]["axis"]["labelColor"] == "#222244"
    assert spec["config"]["axis"]["gridColor"] == "#dddddd"
    colours = _main(spec)["layer"][0]["encoding"]["color"]["scale"]["range"]
    assert colours == shown._drawn.colours


# ─── the numbers are the picture's ───────────────────────────────────────────


def _bar_lengths(ax: Any, horizontal: bool) -> list[list[float]]:
    return [
        [float(p.get_width() if horizontal else p.get_height()) for p in container]
        for container in ax.containers
        if hasattr(container, "patches")
    ]


@pytest.mark.parametrize(
    "name",
    [
        "bar_percent",
        "bar_split_letters",
        "bar_stacked",
        "bar_stacked_100",
        "bar_top_other",
        "bar_means_intervals",
    ],
)
def test_bar_values_are_the_bars_drawn(charts, specs, name):
    chart = charts[name]
    drawn = chart._drawn
    rows = _rows(specs[name])
    positions, count = drawn.bars.values.shape
    lengths = _bar_lengths(chart.plot(), drawn.horizontal)
    assert len(lengths) == count
    for row in rows:
        index = drawn.bars.series.index(row["series"]) if count > 1 else 0
        where = [vega.plain(p) for p in drawn.bars.positions].index(row["position"])
        drawn_length = lengths[index][where]
        if row["value"] is None:
            assert drawn_length != drawn_length or drawn_length == 0
            continue
        assert row["value"] == pytest.approx(drawn_length, abs=1e-9)
        assert row["value"] == pytest.approx(drawn.bars.values[where, index], abs=1e-12)
        # The value as the picture writes it on its bar.
        assert row["text"] == value_text(row["value"], drawn.bars.kind)
        if "lower" in row:
            assert row["lower"] == pytest.approx(drawn.bars.lower[where, index])
            assert row["upper"] == pytest.approx(drawn.bars.upper[where, index])


def test_the_classic_bar_chart_keeps_its_numbers_and_its_labels(charts, specs):
    chart = charts["bar_classic"]
    ax = chart.plot()
    heights = [p.get_height() for p in ax.patches]
    rows = _rows(specs["bar_classic"])
    assert [row["value"] for row in rows] == pytest.approx(heights)
    # Written as the picture writes them (1234, not 1,234), which are its texts.
    texts = {text.get_text() for text in ax.texts}
    assert {row["text"] for row in rows} <= texts
    # Every bar in the color it was drawn in.
    from matplotlib.colors import to_hex

    assert [row["colour"] for row in rows] == [to_hex(p.get_facecolor()) for p in ax.patches]
    means = _rows(specs["bar_classic_means"])
    drawn = [p.get_width() for p in charts["bar_classic_means"].plot().patches]
    assert [row["value"] for row in means] == pytest.approx(drawn)
    assert all(re.fullmatch(r"\d+\.\d\d", row["text"]) for row in means)


def test_a_significance_letter_names_its_groups_in_the_tooltip(specs):
    rows = _rows(specs["bar_split_letters"])
    marked = [row for row in rows if row["letters"]]
    assert marked, "the data should give at least one letter"
    for row in marked:
        for letter in row["letters"]:
            assert f"({letter})" in row["higher"]
    assert {row["higher"] for row in rows if not row["letters"]} == {"none"}


def test_histogram_and_donut_values_are_drawn_ones(charts, specs):
    chart = charts["histogram"]
    ax = chart.plot()
    rows = _rows(specs["histogram"])
    assert [row["value"] for row in rows] == pytest.approx([p.get_height() for p in ax.patches])
    assert [row["start"] for row in rows] == pytest.approx([p.get_x() for p in ax.patches])
    split = specs["histogram_split"]
    panels = _main(split)["vconcat"]
    assert len(panels) == 4
    drawn = charts["histogram_split"]._drawn.histogram
    for panel, heights in zip(panels, drawn.heights, strict=True):
        assert [row["value"] for row in panel["data"]["values"]] == pytest.approx(list(heights))
    donut = charts["donut"]
    wedges = [p for p in donut.plot().patches if hasattr(p, "theta1")]
    shares = [(w.theta2 - w.theta1) / 360.0 * 100.0 for w in wedges]
    assert [row["share"] for row in _rows(specs["donut"])] == pytest.approx(shares, abs=1e-6)


def test_likert_shares_are_the_table_s(charts, specs):
    for name in ("likert", "likert_side"):
        table = charts[name].table
        rows = _rows(specs[name])
        answers = [column for column in table.columns if column not in ("Item",)]
        for _, line in table.iterrows():
            mine = [row for row in rows if row["name"] == line["Item"]]
            for row in mine:
                assert round(row["share"], 1) == pytest.approx(line[row["answer"]])
            assert {row["answer"] for row in mine} <= set(answers)
        # A diverging stack: the negative answers left of 0, the positive right.
        acme = [row for row in rows if row["name"] == "Acme"]
        assert all(row["end"] <= 1e-9 for row in acme if row["answer"] in ("Dissatisfied",))
        assert all(row["start"] >= -1e-9 for row in acme if row["answer"] == "Very satisfied")


def test_heatmap_cells_are_the_mesh_s(charts, specs):
    for name in ("heatmap_spearman", "heatmap_pearson", "heatmap_means", "heatmap_means_theme"):
        ax = charts[name].plot()
        mesh = np.ma.filled(np.ma.asarray(ax.collections[0].get_array(), dtype=float), np.nan)
        values = [row["value"] for row in _rows(specs[name])]
        expected = [None if v != v else v for v in mesh.ravel().tolist()]
        assert len(values) == len(expected), name
        for got, want in zip(values, expected, strict=True):
            assert (got is None) == (want is None), name
            if got is not None:
                assert got == pytest.approx(want), name


def test_box_plot_numbers_are_seaborn_s_boxes(charts, specs):
    chart = charts["boxplot"]
    ax = chart.plot()
    boxes = _main(specs["boxplot"])["layer"][1]["data"]["values"]
    # seaborn adds its boxes in the order of its hue levels: by where they stand.
    patches = sorted(ax.patches, key=lambda patch: patch.get_path().get_extents().x0)
    assert len(boxes) == len(patches) == 4
    from matplotlib.colors import to_hex

    for box, patch in zip(boxes, patches, strict=True):
        extent = patch.get_path().get_extents()
        assert (box["q1"], box["q3"]) == pytest.approx((extent.y0, extent.y1))
        assert box["colour"] == to_hex(patch.get_facecolor())
    medians = sorted(
        float(line.get_ydata()[0]) for line in ax.lines if len(set(line.get_ydata())) == 1
    )
    assert sorted(box["median"] for box in boxes) == pytest.approx(
        [m for m in medians if any(abs(m - b["median"]) < 1e-9 for b in boxes)]
    )


def test_scatter_points_are_the_points_drawn(charts, specs):
    for name in ("scatter", "scatter_hue"):
        ax = charts[name].plot()
        offsets = ax.collections[0].get_offsets()
        rows = _main(specs[name])["layer"][0]["data"]["values"]
        # The same points, each once (in an order of their own: see
        # test_charts_that_plot_respondents_carry_only_the_plotted_values).
        assert sorted((row["x"], row["y"]) for row in rows) == pytest.approx(
            sorted(tuple(point) for point in offsets.tolist())
        )
    line = _main(specs["scatter"])["layer"][1]["data"]["values"]
    fitted = charts["scatter"].plot().lines[-1]
    assert (line[0]["x"], line[0]["y"]) == pytest.approx(
        (fitted.get_xdata()[0], fitted.get_ydata()[0])
    )
    assert (line[-1]["x"], line[-1]["y"]) == pytest.approx(
        (fitted.get_xdata()[-1], fitted.get_ydata()[-1])
    )


def test_trend_points_are_the_table_s_and_gaps_stay_gaps(charts, specs):
    for name in ("trend", "trend_by", "trend_waves"):
        points = charts[name].points.points
        rows = _rows(specs[name])
        assert len(rows) == len(points)
        for row, (_, point) in zip(rows, points.iterrows(), strict=True):
            if point["value"] != point["value"]:
                assert row["value"] is None
            else:
                assert row["value"] == pytest.approx(point["value"])
            assert row["low"] == bool(point["low"])
    # A low base is drawn hollow, as the picture draws it.
    layers = _main(specs["trend_by"])["layer"]
    hollow = [layer for layer in layers if layer["mark"].get("filled") is False]
    assert hollow and hollow[0]["mark"]["fill"] == "#ffffff"


def _found(spec: Any, key: str) -> list[Any]:
    """Every value of ``key`` anywhere in ``spec``."""

    found = []
    if isinstance(spec, dict):
        for name, value in spec.items():
            if name == key:
                found.append(value)
            found += _found(value, key)
    elif isinstance(spec, list):
        for item in spec:
            found += _found(item, key)
    return found


def _units(spec: Any) -> list[dict[str, Any]]:
    """Every view or layer of ``spec`` that has params."""

    units = []
    if isinstance(spec, dict):
        if isinstance(spec.get("params"), list):
            units.append(spec)
        for value in spec.values():
            units += _units(value)
    elif isinstance(spec, list):
        for item in spec:
            units += _units(item)
    return units


def test_a_legend_toggles_the_series_shown_and_fades_the_hidden_ones(specs):
    """A legend's selection holds the series shown — every entry at first — so
    Vega-Lite's legend fades the entries out of it, those of the series
    hidden (a selection of the hidden series faded the ones still shown).
    Only a click on an entry toggles (a click on a mark toggled the entry
    clicked last once more)."""

    toggled = set()
    for name, spec in specs.items():
        for unit in _units(spec):
            for param in unit["params"]:
                if param.get("name") != vega.SHOWN:
                    continue
                toggled.add(name)
                field = param["select"]["fields"][0]
                assert param["bind"] == {"legend": vega.LEGEND_CLICK}, name
                # No clear (a double click) in the spec: it cost the legend its
                # first click. The report's page shows every series on one.
                assert set(param["select"]) == {"type", "fields", "toggle"}, name
                legends = [
                    channel
                    for channel in unit["encoding"].values()
                    if isinstance(channel, dict)
                    and channel.get("field") == field
                    and channel.get("legend") is not None
                ]
                domain = legends[0]["scale"]["domain"]
                assert [entry[field] for entry in param["value"]] == domain, name
        # A series is drawn while it is in the selection, or when none is
        # (the double click empties it).
        for condition in _found(spec, "condition"):
            if isinstance(condition, dict) and condition.get("param") == vega.SHOWN:
                assert condition["empty"] is True, name
    assert {"bar_split_letters", "donut", "likert", "scatter_hue", "trend_by"} <= toggled
    assert "hidden" not in json.dumps(specs)


def test_a_trend_point_s_note_is_in_its_own_tooltip_alone(specs):
    """Only a point of a low base has a note: a tooltip that asks every point
    for one says "Note: undefined" over the others."""

    hollow_seen = False
    for name in ("trend", "trend_by", "trend_waves", "trend_daily"):
        for layer in _main(specs[name])["layer"]:
            tooltip = layer.get("encoding", {}).get("tooltip")
            if not tooltip:
                continue
            titles = [entry["title"] for entry in tooltip]
            hollow = layer["mark"].get("filled") is False
            hollow_seen |= hollow
            assert ("Note" in titles) == hollow, (name, titles)
            if hollow:
                rows = [
                    row for row in _rows(specs[name]) if row["low"] and row["value"] is not None
                ]
                assert rows and all(row.get("note") for row in rows), name
    assert hollow_seen


def test_a_means_heatmap_cell_gives_the_base_of_its_own_mean(specs):
    """A cell's mean is of the group's respondents who answered its item: its
    base is theirs, not the group's (which the picture writes under the
    group's name)."""

    frame = _with_gaps().frame
    groups = {"North": 1, "South": 2, "East": 3, "Capital metropolitan area": 4}
    items = {"Acme": "t1", "Globex": "t2", "Initech": "t3"}
    rows = _rows(specs["heatmap_means_gaps"])
    assert len(rows) == 12
    for row in rows:
        item, code = items[row["row_name"]], groups[row["column_name"]]
        part = frame[[item, "region", "w"]].dropna()
        mine = part[part["region"] == code]
        assert row["base"] == vega.base_text(len(mine), float(mine["w"].sum())), row
    bases = {(row["row_name"], row["column_name"]): row["base"] for row in rows}
    assert bases[("Globex", "North")] != bases[("Acme", "North")]
    # The tooltip names what a row and a column are.
    titles = [
        entry["title"]
        for entry in _main(specs["heatmap_means_gaps"])["layer"][0]["encoding"]["tooltip"]
    ]
    assert titles[:2] == ["Item", "Region"] and titles[-1] == "Base"
    spearman = _main(specs["heatmap_spearman"])["layer"][0]["encoding"]["tooltip"]
    assert [entry["title"] for entry in spearman][:2] == ["Variable", "With"]


def test_a_heatmap_s_printed_value_has_its_cell_s_tooltip(specs):
    """The value written in a cell is where the pointer goes: it has the
    cell's tooltip (a text without one took the pointer from the cell)."""

    for name in ("heatmap_spearman", "heatmap_pearson", "heatmap_means", "heatmap_means_theme"):
        layers = _main(specs[name])["layer"]
        cells = layers[0]["encoding"]["tooltip"]
        texts = [layer for layer in layers if layer["mark"]["type"] == "text"]
        valued = [layer for layer in texts if "!isValid" not in json.dumps(layer["transform"])]
        assert valued and all(layer["encoding"]["tooltip"] == cells for layer in valued), name


def test_a_donut_writes_a_value_layer_only_for_slices_it_holds(specs):
    """A layer of values with no slice to write stacks an empty angle, which
    Vega warns of: a donut whose slices all hold their values has no layer
    for the values outside the ring."""

    def filters(name: str) -> list[str]:
        return [
            layer.get("transform", [{}])[0].get("filter", "")
            for layer in _main(specs[name])["layer"]
        ]

    assert "datum.inside" in filters("donut_inside")
    assert "!datum.inside" not in filters("donut_inside")
    assert {"datum.inside", "!datum.inside"} <= set(filters("donut"))


def test_zoom_takes_the_wheel_with_ctrl_or_cmd_held(specs):
    """Vega-Lite zooms by the wheel's vertical delta, which Shift turns
    sideways on Windows and macOS: the wheel zooms with Ctrl or Cmd (and a
    trackpad's pinch), and the hint says so."""

    zoomed = 0
    for name, spec in specs.items():
        for unit in _units(spec):
            for param in unit["params"]:
                if param.get("name") == "zoom":
                    zoomed += 1
                    zoom = param["select"]["zoom"]
                    assert zoom == "wheel![event.ctrlKey || event.metaKey]", name
                    notes = " ".join(spec["usermeta"]["siamang"]["notes"])
                    assert "hold Ctrl (Cmd on a Mac) and scroll, or pinch, to zoom" in notes
                    assert "Shift" not in notes, name
    assert zoomed >= 3  # the scatter plots and the daily Trend


# ─── nothing but what the chart draws ────────────────────────────────────────

#: The charts that plot respondents themselves, and the fields their points carry.
PLOTTED = {
    "scatter": {"x", "y", "x_text", "y_text"},
    "scatter_hue": {"x", "y", "x_text", "y_text", "group"},
}


def test_no_respondent_row_reaches_a_spec(specs):
    for name, spec in specs.items():
        text = json.dumps(spec)
        assert "RID-" not in text and "SECRET" not in text, name
        rows = sum(len(values) for values in _datasets(spec))
        if name in PLOTTED or name == "boxplot_points":
            continue
        # An aggregated chart holds a row per bar, cell, point of a line or
        # box — never one per respondent.
        assert rows < N / 2, (name, rows)


def test_charts_that_plot_respondents_carry_only_the_plotted_values(charts, specs):
    for name, fields in PLOTTED.items():
        rows = _main(specs[name])["layer"][0]["data"]["values"]
        assert len(rows) == N
        assert all(set(row) <= fields for row in rows), name
    points = [
        values
        for values in _datasets(specs["boxplot_points"])
        if values and set(values[0]) == {"group", "value"}
    ]
    assert len(points) == 1 and len(points[0]) == N
    outliers = _main(specs["boxplot"])["layer"][3]["data"]["values"]
    assert outliers and all(set(row) == {"group", "name", "value", "text"} for row in outliers)
    # A point's place in the list is no key to a respondent: the points are
    # in the order of their values (by group), not of the data — else two
    # charts of the data joined by place would rebuild each respondent's
    # answers (age, income and region from one, age and satisfaction from
    # another).
    frame = _survey().frame
    scatter = _main(specs["scatter_hue"])["layer"][0]["data"]["values"]
    levels = charts["scatter_hue"]._drawn.levels
    key = [(levels.index(row["group"]), row["x"], row["y"]) for row in scatter]
    assert key == sorted(key)
    in_frame = list(zip(frame["age"], frame["income"], strict=True))
    assert [(row["x"], row["y"]) for row in scatter] != in_frame
    boxes = points[0]
    groups = charts["boxplot_points"]._drawn.groups
    axis = _box_axis(specs["boxplot_points"])
    names = {group: label for group, label in zip(groups, axis, strict=True)}
    order = [(list(names.values()).index(row["group"]), row["value"]) for row in boxes]
    assert order == sorted(order)
    # A host that shows charts to the public can tell these charts apart.
    flagged = {
        name for name, spec in specs.items() if spec["usermeta"]["siamang"].get("respondents")
    }
    assert flagged == {"scatter", "scatter_hue", "boxplot", "boxplot_points"}


def test_a_box_plot_is_flagged_when_it_plots_a_respondents_answer():
    """An outlier is one respondent's answer as much as a point is: a box plot
    with outliers is flagged for a public page, one without is not, and its
    outliers are listed by value, not in the data's order."""
    import matplotlib.pyplot as plt

    data = _survey()
    try:
        with_outliers = BoxPlot(data, column="income", by="region")
        spec = with_outliers.vega_lite()
        assert spec["usermeta"]["siamang"].get("respondents") is True
        outliers = _main(spec)["layer"][3]["data"]["values"]
        by_group: dict[str, list[float]] = {}
        for row in outliers:
            by_group.setdefault(row["group"], []).append(row["value"])
        assert outliers and all(values == sorted(values) for values in by_group.values())
        plain = BoxPlot(data, column="wave", by="region")
        plain_spec = plain.vega_lite()
        assert not any(stat and len(stat["fliers"]) for stat in plain._drawn.stats)
        assert "respondents" not in plain_spec["usermeta"]["siamang"]
    finally:
        plt.close("all")


def _box_axis(spec: dict[str, Any]) -> list[str]:
    return _main(spec)["encoding"]["x"]["sort"]


# ─── the report ──────────────────────────────────────────────────────────────


def _report(charts: dict[str, Any], names: list[str]) -> Report:
    report = Report(title="Interactive", description="Charts a client can explore.")
    for name in names:
        report.heading(name, 3).add(charts[name], caption=f"Chart {name}")
    return report


#: The only addresses in an interactive report: literal strings inside the
#: vendored libraries — XML namespaces, a link in an error message, the
#: editor a page without the editor action never opens, the Vega schema's
#: name. None is ever requested (the browser test counts the requests).
LIBRARY_STRINGS = {
    "http://www.w3.org/2000/svg",
    "http://www.w3.org/2000/xmlns/",
    "http://www.w3.org/1999/xlink",
    "https://vega.github.io/editor/",
    "https://vega.github.io/schema/vega/v6.json",
    "https://github.com/vega/vega-lite/issues/2415",
    "https://github.com/Starcounter-Jack/JSON-Patch",
}
#: The addresses in the libraries' notices: words of two licenses' texts.
NOTICE_STRINGS = {
    "https://github.com/scijs/integrate-adaptive-simpson",
    "http://www.apache.org/licenses/LICENSE-2.0",
    "http://unlicense.org",
}


def test_an_interactive_report_carries_the_libraries_once_and_no_address(charts, tmp_path):
    names = ["bar_split_letters", "donut", "likert", "scatter_hue", "trend_by", "bar_classic"]
    html = _report(charts, names).to_html(standalone=True, interactive=True)
    # Once per document, however many charts.
    assert html.count('<script data-library="vega">') == 1
    assert html.count('<script data-library="vega-lite">') == 1
    assert html.count('<script data-library="vega-embed">') == 1
    assert html.count(vega.library("vega.min.js")[:200]) == 1
    assert html.count('class="siamang-chart"') == len(names)
    assert html.count('<script type="application/json" class="siamang-chart-spec">') == len(names)
    # Each chart's picture: for a reader without scripts, and for print.
    assert html.count('<noscript><img src="data:image/png;base64,') == len(names)
    assert "@media print" in html and ".siamang-chart-picture" in html
    # No address: nothing loaded from anywhere, none in the page's own markup.
    assert not re.search(r"""(src|href)\s*=\s*["']?(https?:)?//""", html, re.IGNORECASE)
    assert not re.search(r"url\(\s*['\"]?(https?:)?//", html, re.IGNORECASE)
    libraries = "".join(vega.library(name) for name in vega.LIBRARIES)
    # The libraries' notices, once, before them: every license of the builds
    # and of what they bundle, as their licenses ask of a copy given away.
    notices = vega.notices()
    assert html.count(f"<!--\n{notices}\n-->") == 1
    assert html.index(notices) < html.index('<script data-library="vega">')
    for line in (
        "Copyright (c) 2015-2023, University of Washington Interactive Data Lab",
        "Copyright (c) 2015, University of Washington Interactive Data Lab.",
        "Copyright 2010-2023 Mike Bostock",
        "Copyright (c) 2013, 2014, 2020 Joachim Wester",
        "Copyright (c) Isaac Z. Schlueter and Contributors",
        "vega 6.4.0",
        "vega-lite 6.4.3",
        "vega-embed 7.3.0",
    ):
        assert line in notices, line
    assert set(re.findall(r"https?://[^\s\"'<>)]+", notices)) <= NOTICE_STRINGS
    outside = html.replace(notices, "")
    for name in vega.LIBRARIES:
        outside = outside.replace(vega.library(name), "")
    assert not re.search(r"https?://", outside), re.findall(r"https?://\S{0,60}", outside)[:3]
    found = set(re.findall(r"https?://[^\s\"'`<>)\\]+", libraries))
    assert found <= LIBRARY_STRINGS, found - LIBRARY_STRINGS
    # The spec's own $schema is left out of the page; the page says the mode.
    assert '"$schema"' not in outside and 'mode: "vega-lite"' in html
    # The chart menu saves pictures, and offers no editor and no source.
    assert "editor: false" in html and "source: false" in html
    # The libraries' licenses ship beside them.
    folder = Path(vega.__file__).parent / "assets" / "vega"
    for name in (
        "LICENSE-vega",
        "LICENSE-vega-lite",
        "LICENSE-vega-embed",
        "README.md",
        "THIRD-PARTY-NOTICES.txt",
    ):
        assert (folder / name).is_file()
    assert vega.libraries_size() < 1_000_000
    # A chart's menu saves its picture by the report's name and its title.
    files = re.findall(r'data-file="([^"]+)"', html)
    assert files[0] == "interactive-overall-satisfaction-by-region" and len(set(files)) == len(
        files
    )


def test_a_saved_report_names_its_charts_pictures_by_its_file(charts, tmp_path):
    report = _report(charts, ["bar_classic", "likert"])
    report.save(tmp_path / "key_tables.html", interactive=True)
    html = (tmp_path / "key_tables.html").read_text("utf-8")
    assert re.findall(r'data-file="([^"]+)"', html) == [
        "key_tables-overall-satisfaction",
        "key_tables-trust",
    ]
    assert 'getAttribute("data-file")' in html


def test_defaults_are_unchanged(charts, tmp_path):
    report = _report(charts, ["bar_classic", "donut"])
    # The HTML: no script, the figures as images.
    html = report.to_html(standalone=True)
    assert "<script" not in html and "siamang-chart" not in html
    assert html == report.to_html(standalone=True, interactive=False)
    fragment = report.to_html()
    assert "<script" not in fragment
    # The Markdown writes its figures and nothing else.
    report.save(tmp_path / "plain" / "r.md")
    report.save(tmp_path / "plain" / "r.html")
    assert sorted(p.name for p in (tmp_path / "plain").iterdir()) == [
        "r.html",
        "r.md",
        "r_fig_1.png",
        "r_fig_3.png",
    ]
    # Asked for, the Markdown has each figure's spec beside it, the same
    # Markdown, and the HTML draws the charts.
    report.save(tmp_path / "live" / "r.md", interactive=True)
    report.save(tmp_path / "live" / "r.html", interactive=True)
    assert sorted(p.name for p in (tmp_path / "live").iterdir()) == [
        "r.html",
        "r.md",
        "r_fig_1.png",
        "r_fig_1.vl.json",
        "r_fig_3.png",
        "r_fig_3.vl.json",
    ]
    assert (tmp_path / "live" / "r.md").read_text("utf-8") == (
        tmp_path / "plain" / "r.md"
    ).read_text("utf-8")
    spec = json.loads((tmp_path / "live" / "r_fig_1.vl.json").read_text("utf-8"))
    assert spec["$schema"] == vega.SCHEMA and spec == charts["bar_classic"].vega_lite()
    assert 'class="siamang-chart"' in (tmp_path / "live" / "r.html").read_text("utf-8")
    with pytest.raises(ValueError, match="standalone=True"):
        report.to_html(interactive=True)


def test_a_document_of_pictures_draws_those_with_a_spec_beside_them(charts, tmp_path):
    """A report combined from Markdown (Studio's Run all) has its charts as
    pictures; with each figure's spec written beside it, the pictures that
    have one are drawn interactively — the libraries once, each picture kept."""

    report = _report(charts, ["bar_classic", "likert"])
    report.save(tmp_path / "flow" / "r.md", interactive=True)
    markdown = (tmp_path / "flow" / "r.md").read_text("utf-8")
    combined = Report.combine(
        [Report(title="First flow").markdown(markdown), Report(title="Second").text("No chart.")],
        title="Study",
    )
    html = combined.to_html(standalone=True)
    pictures = re.findall(r'src="(r_fig_\d+\.png)"', html)
    assert pictures == ["r_fig_1.png", "r_fig_3.png"]
    specs = {"r_fig_1.png": json.loads((tmp_path / "flow" / "r_fig_1.vl.json").read_text("utf-8"))}
    drawn = Report.interactive_figures(html, specs, name="report")
    assert drawn.count('class="siamang-chart"') == 1
    assert drawn.count('<script data-library="vega-embed">') == 1
    assert drawn.count(vega.notices()) == 1 and ".siamang-chart-picture" in drawn
    # The picture with a spec is in its chart's container (not in a <p>), kept
    # for print and a reader without scripts; the other stays a picture.
    assert '<noscript><img alt="Chart bar_classic" src="r_fig_1.png" /></noscript>' in drawn
    assert '<p><img alt="Chart likert" src="r_fig_3.png" /></p>' in drawn
    assert re.search(r'data-file="report-overall-satisfaction"', drawn)
    # Nothing to draw: the document as it was.
    assert Report.interactive_figures(html, {}) == html
    assert Report.interactive_figures(html, {"elsewhere.png": specs["r_fig_1.png"]}) == html


def test_a_chart_whose_spec_fails_keeps_its_picture(charts, monkeypatch):
    chart = charts["bar_classic"]

    def broken() -> None:
        raise RuntimeError("no spec today")

    monkeypatch.setattr(chart, "vega_lite", broken)
    report = Report(title="R").add(chart, caption="Kept")
    with pytest.warns(RuntimeWarning, match="its picture is kept"):
        html = report.to_html(standalone=True, interactive=True)
    assert '<img src="data:image/png;base64,' in html and "siamang-chart" not in html
    assert "<script" not in html


def test_write_spec_and_spec_path(charts, tmp_path):
    assert vega.spec_path(tmp_path / "preview" / "bar.png") == tmp_path / "preview" / "bar.vl.json"
    written = vega.write_spec(charts["likert"], tmp_path / "likert.vl.json")
    assert (
        written is not None
        and json.loads(written.read_text("utf-8"))["usermeta"]["siamang"]["chart"] == "likert"
    )
    assert vega.write_spec(_own_figure(), tmp_path / "none.vl.json") is None
    assert not (tmp_path / "none.vl.json").exists()


# ─── the flow ────────────────────────────────────────────────────────────────


def _flow(save: dict[str, Any]) -> dict[str, Any]:
    nodes = [
        ("src", "source.responses", {"table": "responses"}),
        ("bar", "visualize.bar", {"variable": "sat", "show": "percent", "split": "region"}),
        ("tile", "output.live_tile", {"kind": "chart", "label": "Satisfaction"}),
        ("section", "output.report_section", {"heading": "Satisfaction"}),
        ("save", "output.save_report", {"title": "T", "path": "outputs/r.md", **save}),
    ]
    edges = [
        ("src", "data", "bar", "data"),
        ("bar", "chart", "tile", "input"),
        ("bar", "chart", "section", "items"),
        ("section", "report", "save", "sections"),
    ]
    return {
        "schema_version": "1.0",
        "name": "t",
        "nodes": [{"id": i, "type": t, "params": p} for i, t, p in nodes],
        "edges": [
            {"from": {"node": a, "port": ap}, "to": {"node": b, "port": bp}}
            for a, ap, b, bp in edges
        ],
    }


def test_save_report_writes_interactive_only_where_it_is_read():
    from siamang.flow import resolve_flow

    plain = render_node(resolve_flow(_flow({})), "save")
    assert "interactive" not in plain
    assert ".save('outputs/r.md')\n" in plain and '.with_suffix(".html"))\n' in plain
    on = render_node(resolve_flow(_flow({"interactive": True})), "save")
    assert ".save('outputs/r.md', interactive=True)" in on
    assert """.save(Path('outputs/r.md').with_suffix(".html"), interactive=True)""" in on
    # Without the HTML it has nothing to draw in: the code is as without it,
    # and the check says so.
    off = render_node(resolve_flow(_flow({"html": False, "interactive": True})), "save")
    assert off == render_node(resolve_flow(_flow({"html": False})), "save")
    issues = [issue for issue in check_flow(_flow({"html": False, "interactive": True}))]
    warned = [issue for issue in issues if issue.code == "PARAM_CONFLICT"]
    assert [issue.severity for issue in warned] == ["warning"]
    assert "Also save HTML" in warned[0].message
    assert not [i for i in check_flow(_flow({"interactive": True})) if i.code == "PARAM_CONFLICT"]


def test_a_flow_run_writes_the_interactive_report_and_publishes_the_tile_s_spec(tmp_path):
    result = FlowRunner(_flow({"interactive": True})).run(sources={"src": _survey()}, cwd=tmp_path)
    assert result.ok
    outputs = tmp_path / "outputs"
    assert sorted(p.name for p in outputs.iterdir()) == [
        "r.html",
        "r.md",
        "r_fig_1.png",
        "r_fig_1.vl.json",
    ]
    html = (outputs / "r.html").read_text("utf-8")
    assert html.count('class="siamang-chart"') == 1 and 'data-library="vega-embed"' in html
    tile = next(tile for tile in result.tiles if tile.node == "tile")
    assert tile.kind == "chart" and tile.spec is not None
    assert tile.spec["$schema"] == vega.SCHEMA
    assert json.loads((outputs / "r_fig_1.vl.json").read_text("utf-8")) == tile.spec
    # A stored flow, the option unset: the outputs it always wrote.
    again = tmp_path / "plain"
    FlowRunner(_flow({})).run(sources={"src": _survey()}, cwd=again)
    assert sorted(p.name for p in (again / "outputs").iterdir()) == [
        "r.html",
        "r.md",
        "r_fig_1.png",
    ]


def test_a_tile_carries_a_spec_only_for_a_chart_that_has_one(charts):
    with live.capture() as tiles:
        live.publish("a", kind="chart", label="Bars", value=charts["bar_classic"])
        live.publish("b", kind="number", label="N", value=3)
        live.publish("c", kind="chart", label="Funnel", value=_own_figure())
        result = rc.chart(_survey().report.means("age", by="region"))
        live.publish("d", kind="chart", label="Result", value=result)
    assert tiles[0].spec == charts["bar_classic"].vega_lite()
    assert tiles[1].spec is None and tiles[2].spec is None
    assert tiles[3].spec == result.vega_lite() and tiles[3].spec is not None


# ─── in a browser ────────────────────────────────────────────────────────────

_HARNESS = r"""
const fs = require("fs");
const [pageFile, outFile, shots] = process.argv.slice(2);
let chromium;
try { ({ chromium } = require("playwright")); }
catch (e) { console.log(JSON.stringify({ skip: "playwright is not installed" })); process.exit(0); }
const drawn = () => {
  const all = document.querySelectorAll(".siamang-chart").length;
  return all > 0 && all === document.querySelectorAll(".siamang-chart-live, .siamang-chart-failed").length;
};
// Each chart as drawn: its marks by type, its written values, how far any
// text reaches past the drawing's edges (on every side), its name.
const read = () => Array.from(document.querySelectorAll(".siamang-chart")).map((box) => {
  const marks = {}, texts = [];
  const svg = box.querySelector(".siamang-chart-view svg");
  let over = 0;
  if (svg) {
    svg.querySelectorAll("g.role-mark").forEach((group) => {
      const cls = group.getAttribute("class");
      if (/(^| )notes_/.test(cls)) return;
      const type = cls.split(" ")[0].replace("mark-", "");
      marks[type] = (marks[type] || 0) + group.children.length;
    });
    const edge = svg.getBoundingClientRect();
    svg.querySelectorAll("text").forEach((text) => {
      const r = text.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) return;
      over = Math.max(over, r.bottom - edge.bottom, r.right - edge.right, edge.left - r.left, edge.top - r.top);
    });
    svg.querySelectorAll("g.mark-text.role-mark text").forEach((text) => {
      if (text.textContent.trim()) texts.push(text.textContent.trim());
    });
  }
  return {
    name: box.getAttribute("data-name"),
    live: box.classList.contains("siamang-chart-live"),
    marks, texts, over,
    label: svg ? (svg.getAttribute("aria-label") || "") : "",
    width: svg ? svg.getBoundingClientRect().width : 0,
  };
});
// Every tooltip a chart's marks carry, as Vega encoded it on each item: a
// value that reads "undefined", "NaN", "null" or nothing is a field the row
// does not have.
const tooltips = () => Array.from(document.querySelectorAll(".siamang-chart")).map((box) => {
  const seen = new Set(), bad = [], keys = [];
  box.querySelectorAll(".siamang-chart-view svg *").forEach((el) => {
    const item = el.__data__;
    if (!item || item.tooltip == null || typeof item.tooltip !== "object") return;
    const text = JSON.stringify(item.tooltip);
    if (seen.has(text)) return;
    seen.add(text);
    keys.push(Object.keys(item.tooltip).join("|"));
    for (const [key, value] of Object.entries(item.tooltip)) {
      if (["undefined", "NaN", "null", ""].includes(String(value).trim())) bad.push(key + ": " + String(value));
    }
  });
  return { name: box.getAttribute("data-name"), bad, keys: Array.from(new Set(keys)) };
});
// A value written on a mark must not take the pointer from the mark under
// it: where the pointer is over a written value, the element it finds has a
// tooltip whenever an element under it has one.
const covered = (name) => {
  const box = document.querySelector('.siamang-chart[data-name="' + name + '"]');
  const out = [];
  box.querySelectorAll(".siamang-chart-view svg g.mark-text.role-mark text").forEach((text) => {
    if (!text.textContent.trim() || text.getAttribute("opacity") === "0") return;
    const r = text.getBoundingClientRect();
    if (!r.width || r.top < 0 || r.bottom > innerHeight) return;
    const stack = document.elementsFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    const tip = (el) => el && el.__data__ && el.__data__.tooltip != null;
    const top = stack.find((el) => el.__data__ !== undefined);
    if (top && !tip(top) && stack.some((el) => el !== top && tip(el))) out.push(text.textContent.trim());
  });
  return out;
};
const tipText = () => {
  const el = document.getElementById("vg-tooltip-element");
  return el && el.classList.contains("visible") ? el.innerText : "";
};
(async () => {
  let browser;
  try {
    const exe = process.env.PLAYWRIGHT_CHROMIUM;
    browser = await chromium.launch(exe ? { executablePath: exe } : {});
  } catch (e) {
    console.log(JSON.stringify({ skip: "no Chromium: " + String(e.message).split("\n")[0] }));
    process.exit(0);
  }
  const logs = [], requests = [];
  try {
    const page = await browser.newPage({ viewport: { width: 900, height: 1000 } });
    page.on("console", (m) => { if (m.type() !== "log") logs.push(m.type() + ": " + m.text()); });
    page.on("pageerror", (e) => logs.push("pageerror: " + e.message));
    page.on("request", (r) => {
      const url = r.url();
      if (!url.startsWith("file:") && !url.startsWith("data:")) requests.push(url);
    });
    await page.goto("file://" + pageFile);
    await page.waitForFunction(drawn, null, { timeout: 60000 });
    const charts = await page.evaluate(read);
    const tips = await page.evaluate(tooltips);
    const view = (name) => '.siamang-chart[data-name="' + name + '"] .siamang-chart-view svg';
    const boxes = await page.$$(".siamang-chart");
    const hidden = {};
    for (const box of boxes) {
      const name = await box.getAttribute("data-name");
      await box.scrollIntoViewIfNeeded();
      const found = await page.evaluate(covered, name);
      if (found.length) hidden[name] = found;
    }
    // A tooltip: over the first bar of the first chart, and over a value
    // written in a heatmap's cell.
    const hover = async (selector) => {
      const target = await page.$(selector);
      if (!target) return "";
      await target.scrollIntoViewIfNeeded();
      const box = await target.boundingBox();
      await page.mouse.move(0, 0);
      await page.waitForTimeout(100);
      await page.mouse.move(box.x + box.width / 2, box.y + Math.min(box.height / 2, 10));
      await page.waitForTimeout(300);
      return page.evaluate(tipText);
    };
    const tooltip = await hover(".siamang-chart .siamang-chart-view svg g.mark-rect.role-mark path");
    const cellValue = await hover(view("heatmap_means_gaps") + " g.mark-text.role-mark text");
    // The legend: a click hides a series and fades its entry, a second click
    // shows it again; a click on a bar changes nothing; a double click shows
    // every series.
    let legend = null;
    const split = view("bar_split_letters");
    const entry = await page.$(split + " g.role-legend-symbol path");
    if (entry) {
      await entry.scrollIntoViewIfNeeded();
      const state = () => page.evaluate((root) => ({
        bars: Array.from(document.querySelector(root + " g.mark-rect.role-mark").children).map((p) => p.getAttribute("opacity") || "1"),
        entries: Array.from(document.querySelectorAll(root + " g.role-legend-symbol path")).map((p) => p.getAttribute("opacity") || "1"),
      }), split);
      // A click straight at the entry, the page's first: no hover before it.
      const click = async (el) => { const b = await el.boundingBox(); await page.mouse.click(b.x + b.width / 2, b.y + b.height / 2); await page.waitForTimeout(250); };
      const before = await state();
      await click(entry);
      const hiddenOne = await state();
      const bar = (await page.$$(split + " g.mark-rect.role-mark path"))[hiddenOne.bars.findIndex((o) => o === "1")];
      await click(bar);
      const afterBar = await state();
      await click(entry);
      const shown = await state();
      const entries = await page.$$(split + " g.role-legend-symbol path");
      await click(entries[0]);
      await click(entries[1]);
      const twoHidden = await state();
      const plot = await bar.boundingBox();
      await page.mouse.dblclick(plot.x + plot.width / 2, plot.y + plot.height / 2);
      await page.waitForTimeout(250);
      legend = { before, hidden: hiddenOne, afterBar, shown, twoHidden, reset: await state() };
    }
    // Zoom: a wheel with Ctrl held zooms the scatter plot, a plain wheel
    // does not (the page scrolls on); a double click resets it.
    let zoom = null;
    const scatter = await page.$(view("scatter"));
    if (scatter) {
      await scatter.scrollIntoViewIfNeeded();
      const axis = () => page.evaluate((root) => Array.from(document.querySelectorAll(root + " g.role-axis-label text")).map((t) => t.textContent).sort().join(","), view("scatter"));
      const frame = await page.evaluate((root) => {
        let best = null, area = 0;
        document.querySelectorAll(root + " path.background").forEach((p) => { const r = p.getBoundingClientRect(); if (r.width * r.height > area) { area = r.width * r.height; best = { x: r.x, y: r.y, width: r.width, height: r.height }; } });
        return best;
      }, view("scatter"));
      const cx = frame.x + frame.width / 2, cy = frame.y + frame.height / 2;
      const wheel = (init) => page.evaluate(([x, y, init]) => {
        const el = document.elementFromPoint(x, y);
        el.dispatchEvent(new WheelEvent("wheel", { bubbles: true, cancelable: true, clientX: x, clientY: y, ...init }));
      }, [cx, cy, init]);
      const before = await axis();
      await wheel({ deltaY: -240 }); await page.waitForTimeout(250);
      const plain = await axis();
      await wheel({ deltaY: -240, shiftKey: true, deltaX: 0 }); await page.waitForTimeout(250);
      const shift = await axis();
      await wheel({ deltaY: -240, ctrlKey: true }); await page.waitForTimeout(250);
      const ctrl = await axis();
      await page.mouse.dblclick(cx, cy); await page.waitForTimeout(250);
      await wheel({ deltaY: -240, metaKey: true }); await page.waitForTimeout(250);
      const meta = await axis();
      await page.mouse.dblclick(cx, cy); await page.waitForTimeout(250);
      zoom = { before, plain, shift, ctrl, meta, reset: await axis() };
    }
    if (shots) {
      for (const box of boxes) {
        const name = await box.getAttribute("data-name");
        await box.screenshot({ path: shots + "/" + name + ".png" });
      }
    }
    await page.emulateMedia({ media: "print" });
    const printed = await page.evaluate(() => Array.from(document.querySelectorAll(".siamang-chart")).map((box) => [
      getComputedStyle(box.querySelector(".siamang-chart-view")).display,
      getComputedStyle(box.querySelector(".siamang-chart-picture")).display,
    ]));
    // A phone's widths: every chart laid out again, nothing cut.
    await page.emulateMedia({ media: "screen" });
    const narrow = {};
    for (const width of [400, 360, 320]) {
      await page.setViewportSize({ width, height: 900 });
      await page.reload();
      await page.waitForFunction(drawn, null, { timeout: 60000 });
      narrow[width] = await page.evaluate(read);
    }
    fs.writeFileSync(outFile, JSON.stringify({ charts, tips, hidden, logs, requests, tooltip, cellValue, legend, zoom, printed, narrow }));
    console.log(JSON.stringify({ ok: true }));
  } finally {
    await browser.close();
  }
})().catch((e) => { console.log(JSON.stringify({ error: String((e && e.stack) || e) })); });
"""


@pytest.fixture(scope="module")
def drawn(charts, tmp_path_factory) -> dict[str, Any]:
    """Every chart drawn in one interactive report, in headless Chromium."""

    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    folder = tmp_path_factory.mktemp("interactive")
    names = list(charts)
    report = Report(title="Every chart")
    for name in names:
        report.add(charts[name], caption=name)
    html = report.to_html(standalone=True, interactive=True)
    # Named by chart, for the harness and for a reader of the screenshots.
    for index, name in enumerate(names, start=1):
        html = html.replace(f'data-name="figure-{index}"', f'data-name="{name}"', 1)
    page = folder / "report.html"
    page.write_text(html, encoding="utf-8")
    harness = folder / "harness.js"
    harness.write_text(_HARNESS, encoding="utf-8")
    out = folder / "out.json"
    shots = os.environ.get("SIAMANG_CHART_SHOTS", "")
    run = subprocess.run(
        [node, str(harness), str(page), str(out), shots],
        capture_output=True,
        text=True,
        timeout=240,
        env={**os.environ},
    )
    lines = [line for line in run.stdout.splitlines() if line.startswith("{")]
    status = json.loads(lines[-1]) if lines else {"error": run.stderr[-2000:]}
    if "skip" in status:
        pytest.skip(status["skip"])
    assert status.get("ok"), status
    return json.loads(out.read_text("utf-8"))


def test_every_chart_is_drawn_without_an_error_or_a_request(drawn, charts):
    # No error and no warning — a donut whose values all sit in its slices
    # warned of an empty layer's infinite extent.
    assert drawn["logs"] == []
    assert drawn["requests"] == []
    assert [chart["name"] for chart in drawn["charts"]] == list(charts)
    assert all(chart["live"] for chart in drawn["charts"]), [
        chart["name"] for chart in drawn["charts"] if not chart["live"]
    ]
    # Printed, each chart is its picture.
    assert all(state == ["none", "block"] for state in drawn["printed"])
    # No text runs past the drawing's edges (the notes' last line, a legend,
    # the title's first line above it), in a report's column or at a phone's
    # widths, down to 320 pixels.
    assert [(c["name"], c["over"]) for c in drawn["charts"] if c["over"] > 1] == []
    for width, laid in drawn["narrow"].items():
        narrow = [(c["name"], round(c["over"])) for c in laid if c["over"] > 1]
        assert narrow == [], (width, narrow)
        assert all(c["width"] <= int(width) for c in laid), width


def _expected_marks(name: str, chart: Any, spec: dict[str, Any]) -> dict[str, int]:
    """The marks a chart's spec should draw, by type: a bar per value, a slice
    per answer, a cell per coefficient, a symbol per point."""

    rows = _rows(spec)
    valued = sum(1 for row in rows if row.get("value") is not None)
    if name.startswith("bar_"):
        return {"rect": valued}
    if name == "histogram":
        return {"rect": len(rows)}
    if name == "histogram_split":
        return {"rect": sum(len(panel["data"]["values"]) for panel in _main(spec)["vconcat"])}
    if name.startswith("donut"):
        return {"arc": len(rows)}
    if name.startswith("likert"):
        return {"rect": len(rows), "rule": 1}
    if name.startswith("heatmap"):
        return {"rect": valued}
    if name.startswith("boxplot"):
        boxes = len(rows)
        outliers = sum(len(stat["fliers"]) for stat in chart._drawn.stats if stat)
        points = N if name == "boxplot_points" else 0
        return {"rule": boxes, "rect": 2 * boxes, "symbol": outliers + points}
    if name.startswith("scatter"):
        return {"symbol": N, "line": 1 if name == "scatter" else 0}
    if name.startswith("trend"):
        lines = len({row["group"] for row in rows if row["value"] is not None})
        return {"symbol": valued, "line": lines}
    raise AssertionError(name)


def test_every_chart_draws_the_marks_its_numbers_call_for(drawn, charts, specs):
    by_name = {chart["name"]: chart for chart in drawn["charts"]}
    for name, spec in specs.items():
        marks = by_name[name]["marks"]
        expected = _expected_marks(name, charts[name], spec)
        assert {mark: marks.get(mark, 0) for mark in expected} == expected, (name, marks)


def test_values_are_written_where_the_bars_hold_them(drawn, specs):
    wide = {chart["name"]: chart["texts"] for chart in drawn["charts"]}
    narrow = {chart["name"]: chart["texts"] for chart in drawn["narrow"]["400"]}
    for name in ("bar_percent", "bar_split_letters", "bar_classic", "bar_means_intervals"):
        values = [row["text"] for row in _rows(specs[name]) if row["value"] is not None]
        assert sorted(text for text in wide[name] if text in values) == sorted(values), name
    # The letters, bold, after their values.
    letters = [row["letters"] for row in _rows(specs["bar_split_letters"]) if row["letters"]]
    assert sorted(text for text in wide["bar_split_letters"] if text in letters) == sorted(letters)
    # At a phone's width a grouped bar is thinner than its value is tall:
    # no value is written, none runs into its neighbor.
    values = {row["text"] for row in _rows(specs["bar_split_letters"])}
    assert not [text for text in narrow["bar_split_letters"] if text in values]
    # A stack's segment holds its value where it is wide enough, as drawn.
    assert "41.3%" in wide["bar_stacked_100"] and len(narrow["bar_stacked_100"]) < len(
        wide["bar_stacked_100"]
    )


def test_a_chart_reads_aloud_and_its_tooltips_give_the_value_and_the_base(drawn):
    for chart in drawn["charts"]:
        assert chart["label"].startswith(
            ("Bar", "Stacked", "Histogram", "Donut", "Likert", "Heatmap", "Box", "Scatter", "Trend")
        ), chart
    assert "Base" in drawn["tooltip"] and "respondents" in drawn["tooltip"]
    # Every tooltip of every mark: no field a row lacks ("Note: undefined"
    # over every point of a Trend but those of a low base), and a base on
    # every mark but a respondent's own point and an outlier.
    assert {tip["name"]: tip["bad"] for tip in drawn["tips"] if tip["bad"]} == {}
    for tip in drawn["tips"]:
        assert tip["keys"], tip["name"]
        for keys in tip["keys"]:
            if tip["name"].startswith("scatter") or keys.endswith("|Outlier"):
                continue
            assert "Base" in keys.split("|"), (tip["name"], keys)
    trend = next(tip for tip in drawn["tips"] if tip["name"] == "trend_by")
    assert any("Note" in keys.split("|") for keys in trend["keys"])
    assert any("Note" not in keys.split("|") for keys in trend["keys"])


def test_a_value_written_on_a_mark_leaves_the_mark_its_tooltip(drawn):
    """The pointer over a cell's printed value, a segment's share or a
    slice's percentage finds the mark's tooltip (a heatmap's value took the
    pointer and showed none)."""

    assert drawn["hidden"] == {}
    tip = drawn["cellValue"]
    assert "Item" in tip and "Base" in tip and "respondents" in tip, tip


def test_a_click_on_the_legend_hides_a_series_and_fades_its_entry(drawn):
    legend = drawn["legend"]
    assert legend is not None
    before, hidden = legend["before"], legend["hidden"]
    assert set(before["bars"]) == {"1"} and set(before["entries"]) == {"1"}
    # Hidden: its bars all but gone, its legend entry faded — the others' not.
    assert any(float(value) < 0.2 for value in hidden["bars"])
    assert [float(value) < 1 for value in hidden["entries"]] == [True] + [False] * (
        len(before["entries"]) - 1
    )
    # A click on a bar is no click on the legend.
    assert legend["afterBar"] == hidden
    assert legend["shown"] == before
    faded = [float(value) < 1 for value in legend["twoHidden"]["entries"]]
    assert faded[:2] == [True, True] and not any(faded[2:])
    # A double click shows every series.
    assert legend["reset"] == before


def test_the_wheel_zooms_with_ctrl_or_cmd_held(drawn):
    zoom = drawn["zoom"]
    assert zoom is not None
    # A plain wheel scrolls the page past the chart; Shift, which Windows and
    # macOS turn into a scroll across, is not asked for.
    assert zoom["plain"] == zoom["before"] and zoom["shift"] == zoom["before"]
    assert zoom["ctrl"] != zoom["before"] and zoom["meta"] != zoom["before"]
    assert zoom["reset"] == zoom["before"]
