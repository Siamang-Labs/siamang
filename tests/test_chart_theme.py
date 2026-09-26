"""Charts in the report theme's colours: ``palette="theme"``.

The colour arithmetic is checked against reference values (WCAG's contrast of
known pairs, Machado 2009's matrices, the OKLab distances the data-viz palette
validator reports for the default palette); the default palette against the
colour-vision rules it is chosen for; a theme's chart fields against the
messages that name a bad one. Then every chart form is drawn in the theme's
colours and read back from the figure — its bars, segments, lines, cells, text,
grid and face — and a chart that names a palette of its own is drawn byte for
byte as it was, whatever theme is about. A report draws a chart of palette
"theme" in its own theme's colours, and a flow does so through its Save
report's Look, run and generated.
"""

from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
import pytest

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import to_hex  # noqa: E402

from siamang.core.variable import Variable, VariableMap  # noqa: E402
from siamang.data import SurveyData  # noqa: E402
from siamang.reporting import Report, ReportTheme, ReportThemeError  # noqa: E402
from siamang.reporting import chart_theme as ct  # noqa: E402
from siamang.reporting import result_charts as rc  # noqa: E402

DOCUMENTS = Path(__file__).resolve().parent / "documents"
ROOT = Path(__file__).resolve().parents[1]

CUSTOM = ReportTheme(
    chart_palette=["#7b3294", "#008837", "#e66101", "#0571b0"],
    chart_sequential="#008837",
    chart_diverging=["#e66101", "#5e3c99"],
    chart_text_color="#203040",
    chart_grid_color="#dde3ea",
    chart_font="Liberation Serif, DejaVu Serif, serif",
)


@pytest.fixture(autouse=True)
def _close_figures(monkeypatch):
    monkeypatch.delenv("SIAMANG_REPORT_THEME", raising=False)
    yield
    plt.close("all")


def _hex(colour) -> str:
    return to_hex(colour, keep_alpha=False)


# ─── colour arithmetic ───────────────────────────────────────────────────────


def test_contrast_and_luminance_are_wcag_s():
    """WCAG 2.x: black on white 21:1; #777777 on white 4.48:1 (the classic
    just-fails-AA grey); a colour against itself 1:1."""

    assert ct.contrast("#000000", "#ffffff") == pytest.approx(21.0)
    assert ct.contrast("#777777", "#ffffff") == pytest.approx(4.478, abs=0.001)
    assert ct.contrast("#2a78d6", "#2a78d6") == pytest.approx(1.0)
    assert ct.luminance("#ffffff") == pytest.approx(1.0)
    assert ct.luminance("#808080") == pytest.approx(0.21586, abs=1e-5)
    # #rgb is #rrggbb.
    assert ct.hex_colour("#ABC") == "#aabbcc"
    assert ct.mix("#000000", "#ffffff", 0.5) == "#808080"


def test_the_simulation_is_machado_2009_in_oklab():
    """Pure red seen with protanopia is Machado's first column on linear RGB,
    clamped to 0–1 (0.152286, 0.114503, 0); OKLab's white is L = 1, a = b = 0."""

    assert ct.seen("#ffffff") == pytest.approx((1.0, 0.0, 0.0), abs=1e-4)
    expected = ct._oklab([0.152286, 0.114503, 0.0])
    assert ct.seen("#ff0000", "protan") == pytest.approx(expected)
    # The distances the data-viz palette validator reports for the default
    # palette (validate_palette.js, OKLab ΔE × 100): the closest neighbours
    # under protanopia and with full colour vision, and of the first three
    # under deuteranopia.
    assert ct.distance("#eda100", "#1baf7a", "protan") == pytest.approx(9.1, abs=0.05)
    assert ct.distance("#e87ba4", "#eda100") == pytest.approx(19.6, abs=0.05)
    assert ct.distance("#1baf7a", "#eb6834", "deutan") == pytest.approx(9.2, abs=0.05)
    assert ct.distance("#2a78d6", "#e34948", "protan") == pytest.approx(21.6, abs=0.05)


# ─── the default colours ─────────────────────────────────────────────────────

#: OKLab ΔE × 100 below which two colours are hard to tell apart (the
#: validator's target is 8, its floor with other cues 6), and the least between
#: neighbours with full colour vision.
CVD_TARGET, NORMAL_FLOOR = 8.0, 15.0


def test_the_default_palette_is_safe_for_colour_blind_readers():
    """Series take the palette in order, so bars, stacks and lines side by side
    take neighbours: every pair of neighbours stays apart under protanopia and
    deuteranopia (and with full colour vision), and so do any two of the first
    three — a chart of up to three series can put any two side by side."""

    palette = ReportTheme().chart_palette
    assert palette == ct.PALETTE and len(palette) == 8
    for vision in ct.VISIONS:
        for first, second in zip(palette, palette[1:], strict=False):
            assert ct.distance(first, second, vision) >= CVD_TARGET, (first, second, vision)
        for i in range(3):
            for j in range(i + 1, 3):
                assert ct.distance(palette[i], palette[j], vision) >= CVD_TARGET
    for first, second in zip(palette, palette[1:], strict=False):
        assert ct.distance(first, second) >= NORMAL_FLOOR
    worst = min(
        ct.distance(a, b, vision)
        for vision in ct.VISIONS
        for a, b in zip(palette, palette[1:], strict=False)
    )
    assert worst == pytest.approx(9.1, abs=0.05)
    # The diverging pair: the two sides of a scale read as two sides.
    low, high = ct.DIVERGING
    for vision in (None, *ct.VISIONS):
        assert ct.distance(low, high, vision) >= 20


def test_the_steps_of_a_scale_read_in_order():
    """An ordered scale's steps are one hue, light to dark: the lightness
    falls step by step (by at least 0.06 in OKLab up to seven steps), the
    lightest still 2:1 on white. A diverging scale's two arms stay apart for
    colour-blind readers at every step."""

    colours = ct.ChartColours()
    for count in range(2, 10):
        steps = colours.ordinal(count)
        lightness = [ct.lightness(step) for step in steps]
        assert lightness == sorted(lightness, reverse=True)
        assert ct.contrast(steps[0], ct.BACKGROUND) >= ct.MIN_STEP_CONTRAST
        if count <= 7:
            assert min(a - b for a, b in zip(lightness, lightness[1:], strict=False)) >= 0.06
    assert colours.ordinal(1) == [ct.SEQUENTIAL]
    for count in range(2, 10):
        steps = colours.diverging_steps(count)
        assert len(steps) == count
        assert steps[0] == ct.DIVERGING[0] and steps[-1] == ct.DIVERGING[1]
        half = count // 2
        low, high = steps[:half], steps[count - half :][::-1]
        for arm in (low, high):
            lightness = [ct.lightness(step) for step in arm]
            assert lightness == sorted(lightness)  # lighter toward the middle
            assert ct.contrast(arm[-1], ct.BACKGROUND) >= ct.MIN_STEP_CONTRAST
            assert ct.distance(arm[-1], ct.NEUTRAL) >= CVD_TARGET  # not the neutral grey
        for vision in ct.VISIONS:
            for left, right in zip(low, high, strict=True):
                assert ct.distance(left, right, vision) >= 10, (count, left, right)
        if count % 2:
            assert steps[half] == ct.MIDPOINT


def test_text_on_any_fill_reads():
    """The value written on a bar, a segment or a cell is in white or the
    theme's text, whichever reads better, black when neither reaches 4.5:1 —
    and one of white and black always does. Checked on every colour a theme
    chart fills with, and on colours drawn at random."""

    for colours in (ct.ChartColours(), ct.ChartColours.of(CUSTOM)):
        fills = [
            *colours.palette,
            *colours.series(24),
            *colours.ordinal(7),
            *colours.diverging_steps(7),
            ct.NEUTRAL,
            ct.MIDPOINT,
        ]
        fills += [to_hex(colours.colormap("diverging")(x)) for x in np.linspace(0, 1, 21)]
        fills += [to_hex(colours.colormap("sequential")(x)) for x in np.linspace(0, 1, 21)]
        rng = np.random.default_rng(0)
        fills += [to_hex(rgb) for rgb in rng.uniform(size=(300, 3))]
        for fill in fills:
            ink = colours.ink_on(fill)
            assert ct.contrast(ink, fill) >= ct.MIN_TEXT_CONTRAST, (fill, ink)
    # White on the dark end, the theme's text on the light one.
    colours = ct.ChartColours()
    assert colours.ink_on("#104281") == "#ffffff"
    assert colours.ink_on("#cde2fb") == ct.TEXT
    # #e34948 reaches 4.2:1 with white and 4.1:1 with the text: black, 5.0:1.
    assert colours.ink_on("#e34948") == "#000000"
    # Secondary text is as light as still reads on white.
    assert ct.contrast(colours.muted, ct.BACKGROUND) == pytest.approx(4.5, abs=0.05)


def test_more_series_than_the_palette_never_repeat_a_colour():
    colours = ct.ChartColours.of(ReportTheme(chart_palette=["#2a78d6", "#eb6834"]))
    for count in (1, 2, 5, 6, 7, 30):
        series = colours.series(count)
        assert len(series) == count and len(set(series)) == count
    assert colours.series(2) == ["#2a78d6", "#eb6834"]
    assert colours.series(0) == []


# ─── the theme's chart fields ────────────────────────────────────────────────


def test_chart_colours_are_stored_sparsely_and_read_back():
    """A theme stores only what was chosen; a list of colours comes from JSON
    as a list, or from a text box as one string, and is a tuple in the theme."""

    assert ReportTheme().to_dict() == {}
    theme = ReportTheme(chart_palette="#111111, #222222 #333", chart_font="Inter, sans-serif")
    assert theme.chart_palette == ("#111111", "#222222", "#333")
    assert theme.to_dict() == {
        "chart_palette": ["#111111", "#222222", "#333"],
        "chart_font": "Inter, sans-serif",
    }
    assert ReportTheme.from_dict(json.loads(json.dumps(theme.to_dict()))) == theme
    assert hash(theme) == hash(ReportTheme.from_dict(theme.to_dict()))
    assert ReportTheme(chart_palette=list(ct.PALETTE)).to_dict() == {}


@pytest.mark.parametrize(
    ("kwargs", "says"),
    [
        ({"chart_palette": ["blue", "#eb6834"]}, "chart_palette: 'blue' is not a hex colour"),
        ({"chart_palette": ["#2a78d6"]}, "give between 2 and 12 colours, .* got 1"),
        ({"chart_palette": ["#2a78d6"] * 13}, "give between 2 and 12"),
        ({"chart_palette": ["#fff", "#FFFFFF"]}, "'#FFFFFF' is given twice"),
        ({"chart_palette": 5}, "chart_palette: expected a list of hex colours"),
        ({"chart_sequential": "rgb(0,0,0)"}, "chart_sequential: 'rgb"),
        ({"chart_diverging": ["#e34948"]}, "chart_diverging: give two colours, the low end first"),
        ({"chart_diverging": ["#e34948", "#E34948"]}, "the two ends are the same colour"),
        ({"chart_diverging": ["#e34948", "navy"]}, "chart_diverging: 'navy' is not a hex"),
        ({"chart_text_color": "#cccccc"}, r"contrast of 1\.6:1; text needs at least 4\.5:1"),
        ({"chart_text_color": "#20304"}, "chart_text_color: '#20304' is not a hex"),
        ({"chart_grid_color": "grey"}, "chart_grid_color"),
        ({"chart_font": "Inter; color: red"}, "chart_font: a list of font names"),
        ({"chart_font": " , "}, "chart_font: expected font names"),
    ],
)
def test_a_bad_chart_colour_names_its_field(kwargs, says):
    with pytest.raises(ReportThemeError, match=says):
        ReportTheme(**kwargs)


def test_the_face_is_the_first_one_installed():
    """A font stack as CSS writes one: the first face installed where the
    chart is drawn, a generic family resolved to matplotlib's face for it;
    none installed is the default."""

    assert ct.resolve_font("'Liberation Serif', serif") == "Liberation Serif"
    assert ct.resolve_font("No Such Face, monospace") == "DejaVu Sans Mono"
    assert ct.resolve_font("No Such Face") is None
    assert ct.resolve_font(None) is None


# ─── the charts ──────────────────────────────────────────────────────────────

AGREE = {1: "Strongly disagree", 2: "Disagree", 3: "Neither", 4: "Agree", 5: "Strongly agree"}


def _data() -> SurveyData:
    rng = np.random.default_rng(4)
    n = 240
    frame = pd.DataFrame(
        {
            "region": rng.integers(1, 6, n),
            "sat": rng.integers(1, 6, n),
            "age": rng.integers(1, 4, n),
            "score": rng.normal(50, 10, n),
            "income": rng.normal(3000, 500, n),
            "t1": rng.integers(1, 6, n),
            "t2": rng.integers(1, 6, n),
            "t3": rng.integers(1, 6, n),
            "wave": rng.integers(1, 5, n),
            "w": rng.uniform(0.5, 2.0, n),
        }
    )
    variables = VariableMap()
    variables.add_many(
        [
            Variable(
                "region",
                "nominal",
                label="Region",
                labels={1: "North", 2: "South", 3: "East", 4: "West", 5: "Capital"},
            ),
            Variable("sat", "ordinal", label="Satisfaction", labels=AGREE),
            Variable("age", "ordinal", label="Age", labels={1: "18–34", 2: "35–54", 3: "55+"}),
            Variable("score", "interval", label="Score"),
            Variable("income", "ratio", label="Income"),
            *[
                Variable(name, "ordinal", label=f"Trust: {brand}", labels=AGREE)
                for name, brand in (("t1", "Acme"), ("t2", "Globex"), ("t3", "Initech"))
            ],
            Variable("wave", "ordinal", label="Wave", labels={i: f"W{i}" for i in range(1, 5)}),
            Variable("w", "ratio", label="Weight"),
        ]
    )
    return SurveyData(frame=frame, variables=variables)


def _forms(data: SurveyData, palette: str) -> dict:
    """Every chart form, drawn with ``palette`` (a Likert chart's own default
    for "muted", a heatmap's colour map for the heatmaps)."""
    likert = "RdBu" if palette == "muted" else palette
    cmap = "YlOrRd" if palette == "muted" else palette
    weighted = data.with_weight("w")
    return {
        "bar": lambda: data.plot.bar("region", palette=palette),
        "bar_means": lambda: data.plot.bar("score", by="age", palette=palette),
        "bar_percent": lambda: weighted.plot.bar("region", show="percent", palette=palette),
        "bar_split": lambda: data.plot.bar("region", split="age", palette=palette),
        "bar_scale": lambda: data.plot.bar(
            "sat", split="age", layout="stacked_100", palette=palette
        ),
        "bar_top": lambda: data.plot.bar(
            "region", show="percent", top=3, other=True, palette=palette
        ),
        "bar_intervals": lambda: weighted.plot.bar(
            "region", split="age", show="percent", intervals=True, palette=palette
        ),
        "bar_letters": lambda: data.plot.bar(
            "sat", split="region", show="percent", letters=True, palette=palette
        ),
        "histogram": lambda: weighted.plot.bar("income", layout="histogram", palette=palette),
        "histogram_split": lambda: data.plot.bar(
            "score", layout="histogram", split="age", show="percent", palette=palette
        ),
        "donut": lambda: data.plot.bar("region", layout="donut", top=3, palette=palette),
        "boxplot": lambda: data.plot.boxplot("score", by="region", palette=palette),
        "scatter": lambda: data.plot.scatter(
            "score", "income", hue="age", trendline=False, palette=palette
        ),
        "heatmap_means": lambda: data.plot.heatmap(["t1", "t2"], by="age", cmap=cmap),
        "heatmap_spearman": lambda: data.plot.heatmap(["t1", "t2", "t3"], cmap=cmap),
        "heatmap_pearson": lambda: weighted.plot.heatmap(
            ["t1", "t2", "t3"], method="pearson", cmap=cmap
        ),
        "likert": lambda: data.plot.likert(["t1", "t2", "t3"], palette=likert),
        "trend": lambda: data.plot.trend(
            "wave", measure="percent", variable="sat", codes=[4, 5], by="age", palette=palette
        ),
        "result_means": lambda: rc.chart(data.report.means("score", by="region"), palette=palette),
        "result_nps": lambda: rc.chart(
            SurveyData(frame=pd.DataFrame({"n": [0, 5, 7, 8, 9, 10, 10, 3]})).report.nps("n"),
            palette=palette,
        ),
    }


def _png(chart) -> bytes:
    out = io.BytesIO()
    chart._ensure_built()
    chart._fig.savefig(out, format="png", dpi=40)
    return out.getvalue()


def test_a_chart_with_its_own_palette_is_drawn_as_it_was_whatever_the_theme(tmp_path, monkeypatch):
    """The theme is an opt-in: a chart that names a palette of its own —
    every stored flow's — is drawn byte for byte the same with a house style
    about (SIAMANG_REPORT_THEME) and in a report of a theme with other chart
    colours, and leaves matplotlib's settings as a chart always did."""

    data = _data()
    plain = {name: _png(make()) for name, make in _forms(data, "muted").items()}
    plt.close("all")
    path = tmp_path / "theme.json"
    path.write_text(json.dumps(CUSTOM.to_dict()), encoding="utf-8")
    monkeypatch.setenv("SIAMANG_REPORT_THEME", str(path))
    for name, make in _forms(data, "muted").items():
        chart = make()
        assert not ct.reads_theme(chart), name
        assert _png(chart) == plain[name], name
        assert ct.in_report(chart, CUSTOM) is chart, name


def _facecolours(ax) -> list[str]:
    return [_hex(patch.get_facecolor()) for patch in ax.patches if patch.get_height() > 0]


def test_every_form_takes_the_theme_s_colours_text_grid_and_face():
    """Drawn with palette "theme" — here a report theme's other colours — each
    form fills with the theme's colours and writes in its text colour and
    face, its grid in the grid colour."""

    data = _data()
    colours = ct.ChartColours.of(CUSTOM)
    forms = _forms(data, "theme")
    for name, make in forms.items():
        chart = ct.in_report(make(), CUSTOM)  # as a report of CUSTOM draws it
        assert chart._drawn_with == colours, name
        fig = chart._fig
        texts = [text for text in fig.findobj(matplotlib.text.Text) if text.get_text().strip()]
        faces = {text.get_fontname() for text in texts}
        assert faces == {"Liberation Serif"}, (name, faces)
        inks = {_hex(text.get_color()) for text in texts}
        allowed = {colours.text, colours.muted, "#ffffff", "#000000"}
        assert inks <= allowed, (name, inks - allowed)
        for ax in fig.axes:
            for line in ax.get_xgridlines() + ax.get_ygridlines():
                if line.get_visible():
                    assert _hex(line.get_color()) == colours.grid, name

    ax = forms["bar"]().plot()  # the classic chart: the palette in turn
    assert _facecolours(ax)[:5] == list(ct.PALETTE[:5])


def test_the_bars_likert_heatmaps_and_results_take_each_their_kind_of_colour():
    data = _data()
    colours = ct.ChartColours.of(CUSTOM)
    forms = _forms(data, "theme")

    def drawn(name):
        return ct.in_report(forms[name](), CUSTOM)

    # A split by a nominal variable: the palette; a scale: the sequential steps.
    ax = drawn("bar_split")._ax
    assert [_hex(c.patches[0].get_facecolor()) for c in ax.containers] == list(colours.series(5))
    ax = drawn("bar_scale")._ax
    assert [_hex(c.patches[0].get_facecolor()) for c in ax.containers] == colours.ordinal(5)
    # Likert: the diverging pair, the neutral answer grey.
    ax = drawn("likert")._ax
    fills = [_hex(c.patches[0].get_facecolor()) for c in ax.containers]
    steps = colours.diverging_steps(5)
    assert fills == [steps[0], steps[1], ct.NEUTRAL, steps[3], steps[4]]
    assert fills[0] == "#e66101" and fills[-1] == "#5e3c99"
    # Heatmaps: the sequential map for means, the diverging one for correlations.
    assert drawn("heatmap_means")._ax.collections[0].cmap.name.startswith("theme_sequential")
    for name in ("heatmap_spearman", "heatmap_pearson"):
        mesh = drawn(name)._ax.collections[0]
        assert ct.distance(mesh.cmap(mesh.norm(0.0)), ct.MIDPOINT) < 1, name
    # The values written in a heatmap's cells read on them.
    ax = drawn("heatmap_means")._ax
    mesh = ax.collections[0]
    for text in ax.texts:
        x, y = text.get_position()
        fill = mesh.cmap(mesh.norm(mesh.get_array()[int(y), int(x)]))
        assert ct.contrast(text.get_color(), fill) >= ct.MIN_TEXT_CONTRAST
    # Trend: a line per group in the palette's order.
    ax = drawn("trend")._ax
    assert [_hex(line.get_color()) for line in ax.lines[:3]] == list(colours.palette[:3])
    # Result charts: the series; the NPS in the diverging pair around grey.
    ax = drawn("result_means")._ax
    assert {_hex(line.get_color()) for line in ax.lines if line.get_marker() == "o"} == {"#7b3294"}
    ax = drawn("result_nps")._ax
    assert _facecolours(ax)[:3] == ["#e66101", ct.NEUTRAL, "#5e3c99"]


def test_the_bar_chart_s_newer_options_take_the_theme_s_colours():
    """Top N's Other is the theme's neutral grey — the grey of the Likert
    chart's neutral answer and the NPS's passives — and none of the palette's;
    error bars and significance letters are in its text colour; a histogram's
    bars, in every panel, are its first colour over its grid; a donut's slices
    take the palette and Other the grey, its base and the percentages beside
    the ring its text colour, the lines to them its secondary text colour.
    With a palette of their own they keep their grey and their ink."""

    from matplotlib.container import BarContainer, ErrorbarContainer
    from matplotlib.patches import Wedge

    from siamang.reporting import bars
    from tests.test_bar_extras import _channels, _letters

    colours = ct.ChartColours.of(CUSTOM)
    data = _data()

    def drawn(chart):
        return ct.in_report(chart, CUSTOM)

    def series(ax) -> list[str]:
        return [
            _hex(c.patches[0].get_facecolor()) for c in ax.containers if isinstance(c, BarContainer)
        ]

    # Top N: the answers in the first colour, Other grey; with Split by, Other
    # is a series of its own, grey after the answers' colours.
    top = drawn(data.plot.bar("region", show="percent", top=3, other=True, palette="theme"))
    assert _facecolours(top._ax) == [colours.palette[0]] * 3 + [ct.NEUTRAL]
    split = drawn(
        data.plot.bar("region", split="age", show="percent", top=2, other=True, palette="theme")
    )
    assert series(split._ax) == [*colours.palette[:2], ct.NEUTRAL]
    assert ct.NEUTRAL not in colours.series(12)
    plain = data.plot.bar("region", show="percent", top=3, other=True)
    assert plain.plot().patches[3].get_facecolor()[:3] == pytest.approx(bars.OTHER_COLOUR)

    # Error bars: whiskers and caps in the text colour.
    ci = drawn(
        data.plot.bar("region", split="age", show="percent", intervals=True, palette="theme")
    )
    containers = [c for c in ci._ax.containers if isinstance(c, ErrorbarContainer)]
    assert len(containers) == 5
    for container in containers:
        (whiskers,) = container.lines[2]
        assert {_hex(colour) for colour in whiskers.get_colors()} == {colours.text}
        assert {_hex(cap.get_markeredgecolor()) for cap in container.lines[1]} == {colours.text}
    means = drawn(data.plot.bar("score", by="age", intervals=True, palette="theme"))
    containers = [c for c in means._ax.containers if isinstance(c, ErrorbarContainer)]
    assert len(containers) == 1
    assert {_hex(colour) for colour in containers[0].lines[2][0].get_colors()} == {colours.text}
    plain = data.plot.bar("region", split="age", show="percent", intervals=True)
    (whiskers,) = next(
        c for c in plain.plot().containers if isinstance(c, ErrorbarContainer)
    ).lines[2]
    assert {_hex(colour) for colour in whiskers.get_colors()} == {_hex(bars.INK)}

    # Significance letters: bold, in the text colour (Left's 60 % yes is
    # higher than Right's 40 %, z = 2.83).
    frame = pd.DataFrame(
        {"q": [1] * 60 + [2] * 40 + [1] * 40 + [2] * 60, "g": [1] * 100 + [2] * 100}
    )
    variables = VariableMap()
    variables.add_many(
        [
            Variable("q", "nominal", label="Answer", labels={1: "Yes", 2: "No"}),
            Variable("g", "nominal", label="Group", labels={1: "Left", 2: "Right"}),
        ]
    )
    yes_no = SurveyData(frame=frame, variables=variables)
    lettered = drawn(yes_no.plot.bar("q", split="g", show="percent", letters=True, palette="theme"))
    assert _letters(lettered._ax) == {("Left (A)", "Yes"): "B", ("Right (B)", "No"): "A"}
    bold = [text for text in lettered._ax.texts if text.get_fontweight() in ("bold", 700)]
    assert len(bold) == 2 and {_hex(text.get_color()) for text in bold} == {colours.text}
    # Beside a value the letters keep a 4 pt gap in the theme's face as in
    # the default one: placed after the value as drawn, not as estimated.
    for palette in ("theme", "muted"):
        chart = yes_no.plot.bar(
            "q", split="g", show="percent", letters=True, horizontal=True, palette=palette
        )
        ax = ct.in_report(chart, CUSTOM).plot()
        renderer = ax.figure.canvas.get_renderer()
        points = 72.0 / ax.figure.dpi
        for letter in (text for text in ax.texts if text.get_fontweight() in ("bold", 700)):
            value = next(
                text for text in ax.texts if text.get_text().endswith("%") and text.xy == letter.xy
            )
            gap = letter.get_window_extent(renderer).x0 - value.get_window_extent(renderer).x1
            assert gap * points == pytest.approx(4.0, abs=0.75), palette
            assert letter.get_fontname() == value.get_fontname()

    # A histogram: its first colour, in one plot or a panel per group.
    for chart in (
        data.plot.bar("income", layout="histogram", palette="theme"),
        data.plot.bar("score", layout="histogram", split="region", palette="theme"),
    ):
        fig = drawn(chart)._fig
        panels = [ax for ax in fig.axes if ax.get_visible()]
        assert len(panels) in (1, 5)
        for ax in panels:
            assert set(_facecolours(ax)) == {colours.palette[0]}
            grid = [line for line in ax.get_ygridlines() if line.get_visible()]
            assert grid and {_hex(line.get_color()) for line in grid} == {colours.grid}
        assert _hex(fig.texts[-1].get_color()) == colours.muted  # the notes

    # A donut: the answers kept in the palette in code order (the fifth past
    # CUSTOM's four a lighter first), Other grey; thin slices' percentages
    # beside the ring, in the text colour, joined by lines in the secondary one.
    donut = drawn(
        _channels((30, 20, 1, 1, 1, 1, 1, 1)).plot.bar(
            "c", layout="donut", top=5, min_slice=0, figsize=(6, 4), palette="theme"
        )
    )
    ax = donut._ax
    wedges = [patch for patch in ax.patches if isinstance(patch, Wedge)]
    assert [wedge.get_label() for wedge in wedges][-1] == "Other"
    assert [_hex(wedge.get_facecolor()) for wedge in wedges] == [
        *colours.series(5),
        ct.NEUTRAL,
    ]
    assert ax.lines and {_hex(line.get_color()) for line in ax.lines} == {colours.muted}
    centre = [text for text in ax.texts if text.get_text() in ("56", "respondents")]
    assert len(centre) == 2 and {_hex(text.get_color()) for text in centre} == {colours.text}
    beside = [
        text
        for text in ax.texts
        if text.get_text().endswith("%") and abs(text.get_position()[0]) > 1
    ]
    on_ring = [text for text in ax.texts if text.get_text().endswith("%") and text not in beside]
    assert beside and {_hex(text.get_color()) for text in beside} == {colours.text}
    for text in on_ring:  # on its slice, in the ink that reads on it
        x, y = text.get_position()
        angle = np.degrees(np.arctan2(y, x)) % 360
        wedge = next(w for w in wedges if (angle - w.theta1) % 360 <= (w.theta2 - w.theta1) % 360)
        assert ct.contrast(text.get_color(), wedge.get_facecolor()) >= ct.MIN_TEXT_CONTRAST
    plain = _channels().plot.bar("c", layout="donut", min_slice=6).plot()
    assert plain.patches[-1].get_facecolor()[:3] == pytest.approx(bars.OTHER_COLOUR)


def test_box_and_scatter_groups_take_the_palette_in_their_order():
    """A box plot's groups take the palette in the order they are drawn, at
    full strength (seaborn dims a box's colour otherwise); a scatter plot's in
    the codebook's order, its legend titled by the variable, not "_hue"."""

    data = _data()
    box = ct.in_report(data.plot.boxplot("score", by="region", palette="theme"), CUSTOM)
    fills = [_hex(patch.get_facecolor()) for patch in box._ax.patches]
    assert fills == list(ct.ChartColours.of(CUSTOM).series(5))
    scatter = ct.in_report(
        data.plot.scatter("score", "income", hue="age", trendline=False, palette="theme"),
        CUSTOM,
    )
    legend = scatter._ax.get_legend()
    assert legend.get_title().get_text() == "Age"
    assert [text.get_text() for text in legend.get_texts()] == ["18–34", "35–54", "55+"]
    points = {
        _hex(colour)
        for collection in scatter._ax.collections
        for colour in collection.get_facecolor()
    }
    assert points == {"#7b3294", "#008837", "#e66101"}


def test_the_method_charts_take_the_theme_s_first_two_colours():
    from siamang.data import drivers
    from tests.test_result_charts_methods import _drivers_data

    result = drivers.analyze(_drivers_data(), "overall", ["price", "staff", "queue", "parking"])
    plain = rc.chart(result.table)
    assert set(_facecolours(plain._ax)) <= {drivers.POSITIVE, drivers.NEGATIVE}
    themed = rc.chart(result.table, palette="theme")
    assert set(_facecolours(themed._ax)) <= set(ct.PALETTE[:2])
    other = ct.in_report(themed, CUSTOM)
    assert set(_facecolours(other._ax)) <= {"#7b3294", "#008837"}
    assert {_hex(label.get_color()) for label in other._ax.get_yticklabels()} == {"#203040"}


def test_a_theme_chart_leaves_matplotlib_s_settings_as_they_were():
    """Its text, grid and face are set while it is drawn and restored after,
    so the next chart is not drawn in them; its own ticks keep them when it is
    saved later, whatever the settings are then."""

    keys = ("text.color", "axes.labelcolor", "xtick.color", "grid.color", "font.family")
    before = {key: matplotlib.rcParams[key] for key in keys}
    chart = _data().plot.bar("region", show="percent", palette="theme")
    chart._colours = ct.ChartColours.of(CUSTOM)
    chart._ensure_built()
    assert {key: matplotlib.rcParams[key] for key in keys} == before
    with matplotlib.rc_context({"xtick.color": "red", "font.family": ["DejaVu Sans"]}):
        chart._fig.savefig(io.BytesIO(), format="png", dpi=40)
    for label in chart._ax.get_xticklabels() + chart._ax.get_yticklabels():
        if label.get_text():
            assert _hex(label.get_color()) == "#203040"
            assert label.get_fontname() == "Liberation Serif"


# ─── in a report ─────────────────────────────────────────────────────────────


def test_a_report_draws_its_theme_charts_in_its_colours_and_leaves_the_chart_as_drawn(
    tmp_path,
):
    """Drawn at its node before the theme is known, a chart of palette "theme"
    is drawn again from its parameters in the report's colours — once for the
    report's Markdown and HTML both — and the chart itself keeps its picture.
    A report whose theme names the same chart colours uses the chart as it is."""

    data = _data()
    chart = data.plot.bar("region", split="age", palette="theme")
    chart._ensure_built()
    at_node = _png(chart)
    assert _hex(chart._ax.containers[0].patches[0].get_facecolor()) == ct.PALETTE[0]

    report = Report(title="R", theme=CUSTOM).add(chart, caption="Age")
    open_before = set(plt.get_fignums())
    report.save(tmp_path / "r.md")
    report.save(tmp_path / "r.html")
    copy = chart._redrawn
    assert copy is not None and copy is not chart
    # Rendered once and let go: its picture is kept, not an open figure.
    assert copy._fig is None and set(plt.get_fignums()) == open_before
    assert ct.in_report(chart, CUSTOM) is copy  # drawn once, kept
    assert _png(chart) == at_node
    assert _hex(copy.plot().containers[0].patches[0].get_facecolor()) == "#7b3294"

    # The PNG the Markdown refers to is the report's colours: its first series'
    # colour fills pixels, the default palette's does not.
    pixels = (plt.imread(tmp_path / "r_fig_0.png")[..., :3] * 255).round().astype(int)
    found = {tuple(p) for p in pixels.reshape(-1, 3)}
    assert (0x7B, 0x32, 0x94) in found and (0x2A, 0x78, 0xD6) not in found
    assert "data:image/png;base64," in (tmp_path / "r.html").read_text("utf-8")

    # The same chart colours: no second drawing.
    same = Report(title="R", theme=ReportTheme(font_preset="modern")).add(chart)
    same.to_markdown(tmp_path / "same")
    assert ct.in_report(chart, ReportTheme(font_preset="modern")) is chart

    # A chart never drawn is drawn in the report's colours in the first place.
    fresh = data.plot.bar("region", palette="theme")
    assert ct.in_report(fresh, CUSTOM) is fresh
    assert _facecolours(fresh._ax)[0] == "#7b3294"


def test_at_its_node_a_theme_chart_takes_the_house_style(tmp_path, monkeypatch):
    """Outside a report the theme is the one SIAMANG_REPORT_THEME names — a
    platform's preview sets it to the flow's Save report look — else the default."""

    chart = _data().plot.bar("region", palette="theme")
    assert _facecolours(chart.plot())[0] == ct.PALETTE[0]
    path = tmp_path / "theme.json"
    path.write_text(json.dumps(CUSTOM.to_dict()), encoding="utf-8")
    monkeypatch.setenv("SIAMANG_REPORT_THEME", str(path))
    chart = _data().plot.bar("region", palette="theme")
    assert _facecolours(chart.plot())[0] == "#7b3294"
    assert ct.in_report(chart, CUSTOM) is chart


# ─── in a flow ───────────────────────────────────────────────────────────────


def _flow(theme: dict) -> dict:
    nodes = [
        ("sim", "source.simulated", {"n": 160, "seed": 2}),
        ("bar", "visualize.bar", {"variable": "region", "split": "gender", "palette": "theme"}),
        (
            "donut",
            "visualize.bar",
            {"variable": "region", "layout": "donut", "top": 2, "palette": "theme"},
        ),
        (
            "hist",
            "visualize.bar",
            {"variable": "age", "layout": "histogram", "split": "gender", "palette": "theme"},
        ),
        (
            "lik",
            "visualize.likert",
            {"items": ["trust_acme", "trust_globex"], "palette": "theme"},
        ),
        ("heat", "visualize.heatmap", {"items": ["age", "satisfaction"], "cmap": "theme"}),
        ("box", "visualize.boxplot", {"y": "age", "by": "region", "palette": "theme"}),
        ("means", "analyze.means", {"y": "satisfaction", "by": "region"}),
        ("rc", "visualize.result_chart", {"palette": "theme"}),
        ("sec", "output.report_section", {"heading": "Charts"}),
        ("save", "output.save_report", {"title": "T", "path": "outputs/t.md", "theme": theme}),
    ]
    edges = [
        ("sim", "data", "bar", "data"),
        ("sim", "data", "donut", "data"),
        ("sim", "data", "hist", "data"),
        ("sim", "data", "lik", "data"),
        ("sim", "data", "heat", "data"),
        ("sim", "data", "box", "data"),
        ("sim", "data", "means", "data"),
        ("means", "table", "rc", "result"),
        *[
            (node, "chart", "sec", "items")
            for node in ("bar", "donut", "hist", "lik", "heat", "box", "rc")
        ],
        ("sec", "report", "save", "sections"),
    ]
    return {
        "schema_version": "1.0",
        "name": "colours",
        "nodes": [{"id": i, "type": t, "params": p} for i, t, p in nodes],
        "edges": [
            {"from": {"node": a, "port": ap}, "to": {"node": b, "port": bp}}
            for a, ap, b, bp in edges
        ],
    }


def test_a_flow_s_charts_take_its_save_report_look(tmp_path):
    """Checked, run and generated: every chart node offers "theme", the Save
    report's Look carries the chart colours, the run's report draws its charts
    in them, and the generated script writes the same report."""

    from siamang.codegen import generate_questionnaire
    from siamang.flow import FlowRunner, check_flow, default_registry, generate_flow
    from siamang.model import from_document, loads

    registry = default_registry()
    for node in (
        "visualize.bar",
        "visualize.boxplot",
        "visualize.scatter",
        "visualize.likert",
        "visualize.trend",
        "visualize.result_chart",
    ):
        assert "theme" in registry.get(node).params["palette"].values, node

    document = loads((DOCUMENTS / "brand_awareness.questionnaire.json").read_text("utf-8"))
    survey = from_document(document).survey
    theme = {"font_preset": "modern", **CUSTOM.to_dict()}
    flow = _flow(theme)
    assert check_flow(flow, questionnaire=document) == []
    bad = _flow({"chart_palette": ["#7b3294", "purple"]})
    [issue] = check_flow(bad, questionnaire=document)
    assert issue.severity == "error" and issue.node == "save"
    assert "chart_palette: 'purple' is not a hex colour such as '#2a78d6'." in issue.message

    runner_dir, script_dir = tmp_path / "runner", tmp_path / "script"
    result = FlowRunner(flow, questionnaire=survey, questionnaire_document=document).run(
        cwd=runner_dir
    )
    assert result.ok
    # At the node, before the Save report: the default theme's colours.
    bar = result.output("bar")
    assert bar._fig is None  # the run renders each chart and releases its figure
    assert _hex(bar.plot().containers[0].patches[0].get_facecolor()) == ct.PALETTE[0]
    for node in ("bar", "donut", "hist", "lik", "heat", "box", "rc"):
        chart = result.output(node)
        assert chart._redrawn is not None and chart._redrawn._drawn_with.palette == tuple(
            CUSTOM.chart_palette
        ), node
    # The donut's Other slice is the theme's grey, the histogram's bars its first colour.
    fills = [_hex(p.get_facecolor()) for p in result.output("donut")._redrawn.plot().patches]
    assert fills == ["#7b3294", "#008837", ct.NEUTRAL]
    hist = result.output("hist")._redrawn.plot().figure
    assert {c for ax in hist.axes if ax.get_visible() for c in _facecolours(ax)} == {"#7b3294"}
    ours = (runner_dir / "outputs" / "t.md").read_text("utf-8")
    first = re.search(r"\((t_fig_\d+\.png)\)", ours).group(1)  # the Bar chart's
    pixels = (plt.imread(runner_dir / "outputs" / first)[..., :3] * 255).round()
    found = {tuple(p) for p in pixels.astype(int).reshape(-1, 3)}
    assert (0x7B, 0x32, 0x94) in found and (0x2A, 0x78, 0xD6) not in found

    code = generate_flow(flow, document)
    assert 'palette="theme"' in code and 'cmap="theme"' in code
    assert '"chart_palette": ["#7b3294", "#008837", "#e66101", "#0571b0"]' in code
    (script_dir / "survey").mkdir(parents=True)
    (script_dir / "survey" / "__init__.py").write_text("", encoding="utf-8")
    (script_dir / "survey" / "questionnaire.py").write_text(
        generate_questionnaire(document), encoding="utf-8"
    )
    (script_dir / "scripts").mkdir()
    script = script_dir / "scripts" / "colours.py"
    script.write_text(code, encoding="utf-8")
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join([str(script_dir), str(ROOT)]),
        "MPLBACKEND": "Agg",
    }
    env.pop("SIAMANG_REPORT_THEME", None)
    completed = subprocess.run(
        [sys.executable, str(script)],
        cwd=script_dir,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert (script_dir / "outputs" / "t.md").read_text("utf-8") == ours
    theirs = (plt.imread(script_dir / "outputs" / first)[..., :3] * 255).round()
    assert (0x7B, 0x32, 0x94) in {tuple(p) for p in theirs.astype(int).reshape(-1, 3)}
