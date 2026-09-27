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
        "likert": LikertChart(d, columns=["t1", "t2", "t3"]),
        "likert_side": LikertChart(w, columns=["t1", "t2", "t3"], neutral="side", palette="theme"),
        "heatmap_spearman": HeatMap(w, columns=["t1", "t2", "t3", "age"]),
        "heatmap_pearson": HeatMap(w, columns=["t1", "t2", "t3", "age"], method="pearson"),
        "heatmap_means": HeatMap(d, columns=["t1", "t2", "t3"], by="region"),
        "heatmap_means_theme": HeatMap(w, columns=["t1", "t2", "t3"], by="region", cmap="theme"),
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


def test_every_chart_form_has_a_spec_and_a_result_chart_has_none(charts, specs):
    assert all(spec is not None for spec in specs.values()), [
        name for name, spec in specs.items() if spec is None
    ]
    # A result's chart has no interactive form yet: None, and its report
    # shows its picture.
    result = rc.chart(_survey().report.means("age", by="region"))
    assert result.vega_lite() is None


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
        assert [(row["x"], row["y"]) for row in rows] == pytest.approx(
            [tuple(point) for point in offsets.tolist()]
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


def test_charts_that_plot_respondents_carry_only_the_plotted_values(specs):
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
    outside = html
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
    for name in ("LICENSE-vega", "LICENSE-vega-lite", "LICENSE-vega-embed", "README.md"):
        assert (folder / name).is_file()
    assert vega.libraries_size() < 1_000_000


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
    result = rc.chart(_survey().report.means("age", by="region"))
    assert vega.write_spec(result, tmp_path / "none.vl.json") is None
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
        live.publish(
            "c",
            kind="chart",
            label="Result",
            value=rc.chart(_survey().report.means("age", by="region")),
        )
    assert tiles[0].spec == charts["bar_classic"].vega_lite()
    assert tiles[1].spec is None and tiles[2].spec is None


# ─── in a browser ────────────────────────────────────────────────────────────

_HARNESS = r"""
const fs = require("fs");
const [pageFile, outFile, shots] = process.argv.slice(2);
let chromium;
try { ({ chromium } = require("playwright")); }
catch (e) { console.log(JSON.stringify({ skip: "playwright is not installed" })); process.exit(0); }
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
    await page.waitForFunction(() => {
      const all = document.querySelectorAll(".siamang-chart").length;
      const done = document.querySelectorAll(".siamang-chart-live, .siamang-chart-failed").length;
      return all > 0 && all === done;
    }, null, { timeout: 60000 });
    const charts = await page.evaluate(() => Array.from(document.querySelectorAll(".siamang-chart")).map((box) => {
      const marks = {};
      box.querySelectorAll(".siamang-chart-view svg g.role-mark").forEach((group) => {
        const cls = group.getAttribute("class");
        if (/(^| )notes_/.test(cls)) return;
        const type = cls.split(" ")[0].replace("mark-", "");
        marks[type] = (marks[type] || 0) + group.children.length;
      });
      const svg = box.querySelector(".siamang-chart-view svg");
      // How far the drawing reaches past the picture's edges: nothing is cut.
      let over = 0;
      if (svg) {
        const edge = svg.getBoundingClientRect();
        svg.querySelectorAll("text").forEach((text) => {
          const r = text.getBoundingClientRect();
          if (r.width === 0 || r.height === 0) return;
          over = Math.max(over, r.bottom - edge.bottom, r.right - edge.right, edge.left - r.left);
        });
      }
      const texts = [];
      box.querySelectorAll(".siamang-chart-view svg g.mark-text.role-mark text").forEach((text) => {
        if (text.textContent.trim()) texts.push(text.textContent.trim());
      });
      return {
        name: box.getAttribute("data-name"),
        live: box.classList.contains("siamang-chart-live"),
        marks,
        texts,
        over,
        label: svg ? (svg.getAttribute("aria-label") || "") : "",
        width: box.getBoundingClientRect().width,
      };
    }));
    // A tooltip: over the first bar of the first chart.
    let tooltip = "";
    const bar = await page.$(".siamang-chart .siamang-chart-view svg g.mark-rect.role-mark path");
    if (bar) {
      const box = await bar.boundingBox();
      await page.mouse.move(box.x + box.width / 2, box.y + Math.min(box.height / 2, 10));
      await page.waitForTimeout(300);
      tooltip = await page.evaluate(() => {
        const el = document.getElementById("vg-tooltip-element");
        return el ? el.innerText : "";
      });
    }
    // The legend: a click hides a series, a second click shows it again.
    let legend = null;
    const split = '.siamang-chart[data-name="bar_split_letters"] .siamang-chart-view svg';
    const entry = await page.$(split + " g.role-legend-symbol path");
    if (entry) {
      await entry.scrollIntoViewIfNeeded();
      const first = () => page.evaluate((root) => {
        const group = document.querySelector(root + " g.mark-rect.role-mark");
        return Array.from(group.children).map((p) => p.getAttribute("opacity") || "1");
      }, split);
      const before = await first();
      await entry.click();
      await page.waitForTimeout(200);
      const hidden = await first();
      await entry.click();
      await page.waitForTimeout(200);
      const shown = await first();
      legend = { before, hidden, shown };
    }
    if (shots) {
      const boxes = await page.$$(".siamang-chart");
      for (let i = 0; i < boxes.length; i++) {
        const name = await boxes[i].getAttribute("data-name");
        await boxes[i].screenshot({ path: shots + "/" + name + ".png" });
      }
    }
    await page.emulateMedia({ media: "print" });
    const printed = await page.evaluate(() => Array.from(document.querySelectorAll(".siamang-chart")).map((box) => [
      getComputedStyle(box.querySelector(".siamang-chart-view")).display,
      getComputedStyle(box.querySelector(".siamang-chart-picture")).display,
    ]));
    // A phone's width: every chart laid out again, nothing cut.
    await page.emulateMedia({ media: "screen" });
    await page.setViewportSize({ width: 400, height: 900 });
    await page.reload();
    await page.waitForFunction(() => {
      const all = document.querySelectorAll(".siamang-chart").length;
      return all > 0 && all === document.querySelectorAll(".siamang-chart-live, .siamang-chart-failed").length;
    }, null, { timeout: 60000 });
    const narrow = await page.evaluate(() => Array.from(document.querySelectorAll(".siamang-chart")).map((box) => {
      const svg = box.querySelector(".siamang-chart-view svg");
      const edge = svg.getBoundingClientRect();
      let over = 0;
      svg.querySelectorAll("text").forEach((text) => {
        const r = text.getBoundingClientRect();
        if (r.width === 0 || r.height === 0) return;
        over = Math.max(over, r.bottom - edge.bottom, r.right - edge.right, edge.left - r.left);
      });
      const texts = [];
      box.querySelectorAll(".siamang-chart-view svg g.mark-text.role-mark text").forEach((text) => {
        if (text.textContent.trim()) texts.push(text.textContent.trim());
      });
      return { name: box.getAttribute("data-name"), over, width: edge.width, texts };
    }));
    fs.writeFileSync(outFile, JSON.stringify({ charts, logs, requests, tooltip, legend, printed, narrow }));
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
    assert drawn["logs"] == []
    assert drawn["requests"] == []
    assert [chart["name"] for chart in drawn["charts"]] == list(charts)
    assert all(chart["live"] for chart in drawn["charts"]), [
        chart["name"] for chart in drawn["charts"] if not chart["live"]
    ]
    # Printed, each chart is its picture.
    assert all(state == ["none", "block"] for state in drawn["printed"])
    # No text runs past the drawing's edges (the notes' last line, a legend),
    # in a report's column or at a phone's width.
    assert [(c["name"], c["over"]) for c in drawn["charts"] if c["over"] > 1] == []
    narrow = [(c["name"], round(c["over"])) for c in drawn["narrow"] if c["over"] > 1]
    assert narrow == [], narrow
    assert all(c["width"] <= 400 for c in drawn["narrow"])


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
    if name == "donut":
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
    narrow = {chart["name"]: chart["texts"] for chart in drawn["narrow"]}
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


def test_a_chart_reads_aloud_and_its_tooltip_gives_the_value_and_the_base(drawn):
    for chart in drawn["charts"]:
        assert chart["label"].startswith(
            ("Bar", "Stacked", "Histogram", "Donut", "Likert", "Heatmap", "Box", "Scatter", "Trend")
        ), chart
    assert "Base" in drawn["tooltip"] and "respondents" in drawn["tooltip"]


def test_a_click_on_the_legend_hides_a_series_and_a_second_shows_it(drawn):
    legend = drawn["legend"]
    assert legend is not None
    assert set(legend["before"]) == {"1"}
    assert set(legend["hidden"]) != {"1"} and any(float(value) < 0.2 for value in legend["hidden"])
    assert legend["shown"] == legend["before"]
