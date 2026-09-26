"""The bar chart's newer forms: percentages, Split by (grouped, stacked, 100 %),
largest first, and the base and missing codes said under the plot.

Every expected number is arithmetic by hand on the small frame below; the
weighted split is also checked against the Crosstab table of the same data.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
import pytest

from siamang.core.variable import Variable, VariableMap
from siamang.data import SurveyData

matplotlib.use("Agg")

DOCUMENTS = Path(__file__).resolve().parent / "documents"


@pytest.fixture(autouse=True)
def _close_figures():
    import matplotlib.pyplot as plt

    yield
    plt.close("all")


def _data() -> SurveyData:
    frame = pd.DataFrame(
        {
            "q": [1, 1, 2, 3, 9, np.nan, 1, 2],
            "g": [1, 1, 1, 2, 2, 2, 1, 2],
            "score": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 30.0, 80.0],
            "m": [[1, 2], [1], [2, 3], [], None, [1, 3], None, None],
            "w": [1.0, 3.0, 1.0, 2.0, 1.0, 1.0, 2.0, 2.0],
        }
    )
    variables = VariableMap()
    variables.add_many(
        [
            Variable(
                "q",
                "nominal",
                label="Answer",
                labels={1: "Yes", 2: "No", 3: "Maybe", 9: "Refused"},
                missing_values=(9,),
                missing_labels={9: "Refused"},
            ),
            Variable("g", "nominal", label="Group", labels={1: "Left", 2: "Right"}),
            Variable("score", "interval", label="Score"),
            Variable("m", "nominal", label="Brands", labels={1: "Acme", 2: "Globex", 3: "Initech"}),
            Variable("w", "ratio", label="Weight"),
        ]
    )
    return SurveyData(frame=frame, variables=variables)


def _heights(chart) -> list[list[float]]:
    """Each series' bar lengths, in drawing order (one list per legend entry)."""

    ax = chart.plot()
    horizontal = chart.horizontal
    return [
        [round(p.get_width() if horizontal else p.get_height(), 3) for p in container]
        for container in ax.containers
    ]


def _ticks(chart) -> list[str]:
    ax = chart.plot()
    labels = ax.get_yticklabels() if chart.horizontal else ax.get_xticklabels()
    return [label.get_text() for label in labels]


def _footnote(chart) -> str:
    return " ".join(text.get_text() for text in chart.plot().figure.texts).replace("\n", " ")


def _values(chart) -> list[str]:
    return [text.get_text() for text in chart.plot().texts]


def _rendered(chart, tmp_path) -> None:
    path = chart.save(tmp_path / "chart.png")
    assert path.stat().st_size > 5000  # a real picture, not an empty canvas


# ─── percent of the respondents who answered ─────────────────────────────────


def test_percent_is_of_the_answers_with_the_missing_code_left_out_and_said(tmp_path):
    # Valid: 1, 1, 2, 3, 1, 2 (the 9 is Refused, one blank) → Yes 3/6, No 2/6, Maybe 1/6.
    chart = _data().plot.bar("q", show="percent")
    _rendered(chart, tmp_path)
    assert _heights(chart) == [[50.0, 33.333, 16.667]]
    assert _ticks(chart) == ["Yes", "No", "Maybe"]
    assert _values(chart) == ["50.0%", "33.3%", "16.7%"]
    ax = chart.plot()
    assert ax.get_ylabel() == "% of respondents" and ax.get_title() == "Answer"
    assert ax.yaxis.get_major_formatter()(20, 0) == "20%"
    note = _footnote(chart)
    assert "Base: 6 respondents who answered." in note
    assert "Left out as missing: Answer: 1 (9 = Refused)." in note
    # One series: one colour for every bar.
    assert len({tuple(p.get_facecolor()) for p in ax.patches}) == 1
    assert chart.weight_note is None


def test_weighted_percent_and_largest_first(tmp_path):
    # Weights of the valid rows: Yes 1 + 3 + 2 = 6, No 1 + 2 = 3, Maybe 2; total 11.
    chart = _data().with_weight("w").plot.bar("q", show="percent", sort="value", horizontal=True)
    _rendered(chart, tmp_path)
    assert _heights(chart) == [[54.545, 27.273, 18.182]]
    assert _ticks(chart) == ["Yes", "No", "Maybe"]
    ax = chart.plot()
    assert ax.get_ylim()[0] > ax.get_ylim()[1]  # the first bar on top
    assert ax.get_xlabel() == "% of respondents (weighted)"
    assert "Base: 6 respondents who answered (weighted: 11.0)." in _footnote(chart)
    assert "Weighted by 'w'" in _footnote(chart) and chart.weight_note == "weighted by 'w'"
    # Largest first on counts too: Maybe 1, No 2, Yes 3 reversed.
    counts = _data().plot.bar("q", sort="value")
    assert _heights(counts) == [[3.0, 2.0, 1.0]] and _values(counts) == ["3", "2", "1"]


def test_a_multiple_choice_question_is_a_share_of_respondents_summing_above_100(tmp_path):
    # Answered: rows 0, 1, 2 and 5 ([] and None are no answer). Acme: 0, 1, 5;
    # Globex: 0, 2; Initech: 2, 5 → 75 %, 50 %, 50 %: 175 % in all.
    chart = _data().plot.bar("m", show="percent")
    _rendered(chart, tmp_path)
    assert _heights(chart) == [[75.0, 50.0, 50.0]]
    assert _ticks(chart) == ["Acme", "Globex", "Initech"]
    note = _footnote(chart)
    assert "Base: 4 respondents who answered." in note
    assert "so the bars add up to more than 100 %" in note
    # At the defaults the older chart raised "unhashable type: 'list'"; it counts now.
    plain = _data().plot.bar("m")
    assert _heights(plain) == [[3.0, 2.0, 2.0]] and plain.plot().get_ylabel() == "Count"


# ─── Split by: the chart of a crosstab ───────────────────────────────────────


def test_split_grouped_gives_percentages_within_each_group(tmp_path):
    # Answered both: Left (g = 1) rows 0, 1, 2, 6 → Yes 3, No 1; Right rows 3, 7
    # → Maybe 1, No 1. Within each group: Left 75/25/0, Right 0/50/50.
    chart = _data().plot.bar("q", split="g", show="percent")
    _rendered(chart, tmp_path)
    assert _heights(chart) == [[75.0, 0.0], [25.0, 50.0], [0.0, 50.0]]
    assert _ticks(chart) == ["Left\n(n = 4)", "Right\n(n = 2)"]
    ax = chart.plot()
    legend = ax.get_legend()
    assert [t.get_text() for t in legend.get_texts()] == ["Yes", "No", "Maybe"]
    assert legend.get_title().get_text() == "Answer"
    colours = {tuple(container.patches[0].get_facecolor()) for container in ax.containers}
    assert len(colours) == 3
    assert ax.get_title() == "Answer by Group" and ax.get_ylabel() == "% within Group"
    note = _footnote(chart)
    assert "Base: 6 respondents who answered both." in note
    assert "Percentages are of each group of Group." in note
    assert "Left out as missing: Answer: 1 (9 = Refused)." in note


def test_a_weighted_split_matches_the_crosstab_of_the_same_data(tmp_path):
    data = _data()
    clean = data.with_frame(data.frame[data.frame["q"] != 9]).with_weight("w")
    table = clean.report.crosstab("q", "g", pct="col", test=False).to_frame()
    chart = clean.plot.bar("q", split="g", show="percent")
    _rendered(chart, tmp_path)
    expected = [
        [round(float(v), 1) for v in table.iloc[row, 1:3]] for row in range(3)
    ]  # rows Yes, No, Maybe; columns Left, Right
    drawn = [[round(v, 1) for v in series] for series in _heights(chart)]
    assert drawn == expected
    # By hand: Left weighs 1 + 3 + 1 + 2 = 7 (Yes 6, No 1); Right 2 + 2 = 4.
    assert _heights(chart)[0] == [85.714, 0.0]
    assert "(weighted: 11.0)" in _footnote(chart)


def test_stacked_and_stacked_to_100(tmp_path):
    data = _data()
    stacked = data.plot.bar("q", split="g", layout="stacked")
    _rendered(stacked, tmp_path)
    assert _heights(stacked) == [[3.0, 0.0], [1.0, 1.0], [0.0, 1.0]]
    # Segments start where the one below ends.
    no_left = stacked.plot().containers[1].patches[0]
    assert no_left.get_y() == 3.0
    # Each group's total written above its bar.
    assert "4" in _values(stacked) and "2" in _values(stacked)

    full = data.plot.bar("q", split="g", layout="stacked_100", horizontal=True)
    _rendered(full, tmp_path)
    heights = np.array(_heights(full))
    assert heights.sum(axis=0).round(6).tolist() == [100.0, 100.0]
    assert full.plot().get_xlim() == (0.0, 100.0)
    assert full.plot().get_xlabel() == "% within Group"
    # The legend of a vertical stack lists the top segment first, as drawn.
    upright = data.plot.bar("q", split="g", layout="stacked_100")
    texts = [t.get_text() for t in upright.plot().get_legend().get_texts()]
    assert texts == ["Maybe", "No", "Yes"]


def test_sorting_keeps_each_answer_its_colour(tmp_path):
    data = _data()
    by_code = data.plot.bar("q", split="g")
    by_value = data.plot.bar("q", split="g", sort="value")
    _rendered(by_value, tmp_path)

    def colours(chart):
        ax = chart.plot()
        return {
            text.get_text(): tuple(container.patches[0].get_facecolor())
            for text, container in zip(ax.get_legend().get_texts(), ax.containers, strict=True)
        }

    # Overall Yes 3, No 2, Maybe 1: already largest first here, so sort by the
    # answer given least instead by making Maybe the most common.
    frame = data.frame.assign(q=[3, 3, 3, 3, 9, np.nan, 1, 2])
    resorted = data.with_frame(frame).plot.bar("q", split="g", sort="value")
    assert [t.get_text() for t in resorted.plot().get_legend().get_texts()] == [
        "Maybe",
        "Yes",
        "No",
    ]
    assert colours(resorted) == colours(data.with_frame(frame).plot.bar("q", split="g"))
    assert colours(by_code) == colours(by_value)


def test_an_ordered_scale_is_one_hue_light_to_dark(tmp_path):
    from matplotlib.colors import to_rgb

    data = _data()
    variables = VariableMap()
    variables.add_many(list(data.variables.values()))
    variables.add(
        Variable(
            "rating",
            "ordinal",
            label="Rating",
            labels={1: "Poor", 2: "Fair", 3: "Good", 4: "Very good", 5: "Excellent"},
        )
    )
    rated = SurveyData(
        frame=data.frame.assign(rating=[1, 2, 2, 3, 3, 4, 5, 5]), variables=variables
    )
    chart = rated.plot.bar("rating", split="g", layout="stacked_100")
    _rendered(chart, tmp_path)
    fills = [to_rgb(container.patches[0].get_facecolor()) for container in chart.plot().containers]
    lightness = [sum(colour) for colour in fills]
    assert len(set(fills)) == 5 and lightness == sorted(lightness, reverse=True)
    # A labelled step nobody gave is drawn too (a scale's empty step is a finding):
    # nobody in Left said Excellent, nobody in Right said Poor.
    assert [len(container.patches) for container in chart.plot().containers] == [2] * 5


# ─── means by group, largest first ───────────────────────────────────────────


def test_means_by_group_largest_first_say_their_base():
    # Left: 10, 20, 30, 30 → 22.5 (n 4); Right: 40, 50, 60, 80 → 57.5 (n 4).
    chart = _data().plot.bar("score", by="g", sort="value")
    assert _heights(chart) == [[57.5, 22.5]]
    assert _ticks(chart) == ["Right\n(n = 4)", "Left\n(n = 4)"]
    assert _values(chart) == ["57.50", "22.50"]
    assert "Base: 8 respondents who answered both." in _footnote(chart)
    # Weighted: Left (10·1 + 20·3 + 30·1 + 30·2) / 7 = 22.857; Right (40·2 + 50 + 60 + 80·2) / 6.
    weighted = _data().with_weight("w").plot.bar("score", by="g", sort="value")
    assert _heights(weighted) == [[58.333, 22.857]]
    assert weighted.plot().get_ylabel() == "Weighted mean Score"
    # Grouped by a multiple-choice question: the groups overlap, and it says so.
    overlap = _data().plot.bar("score", by="m")
    # Acme rows 0, 1, 5 (10, 20, 60); Globex 0, 2 (10, 30); Initech 2, 5 (30, 60).
    assert _heights(overlap) == [[30.0, 20.0, 45.0]]
    assert "the groups overlap" in _footnote(overlap)


# ─── the chart it always was, and what it refuses ────────────────────────────


def test_the_defaults_draw_the_chart_they_always_drew():
    """The older chart: a bar per value found, the missing code among them, a
    colour per bar, no footnote."""

    chart = _data().plot.bar("q")
    ax = chart.plot()
    assert [p.get_height() for p in ax.patches] == [3, 2, 1, 1]
    assert [t.get_text() for t in ax.get_xticklabels()] == ["Yes", "No", "Maybe", "Refused"]
    assert len({tuple(p.get_facecolor()) for p in ax.patches}) == 4
    assert ax.get_xlabel() == "Answer" and ax.figure.texts == []


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"by": "g", "split": "g"}, "give one of them"),
        ({"by": "g", "show": "percent"}, "use split= instead of by="),
        ({"show": "share"}, "show must be one of count, percent"),
        ({"split": "g", "layout": "pie"}, "layout must be one of grouped, stacked, stacked_100"),
        ({"sort": "label"}, "sort must be one of code, value"),
        ({"split": "q"}, "split must name another variable"),
        ({"split": "nope"}, "No variable 'nope' in the data."),
    ],
)
def test_what_cannot_be_drawn_is_said(kwargs, message):
    with pytest.raises(ValueError, match=message):
        _data().plot.bar("q", **kwargs).plot()


def test_a_multiple_choice_question_is_not_stacked_nor_a_split():
    with pytest.raises(ValueError, match="options overlap and cannot be stacked"):
        _data().plot.bar("m", split="g", layout="stacked").plot()
    with pytest.raises(ValueError, match="split needs one answer per respondent"):
        _data().plot.bar("q", split="m").plot()
    with pytest.raises(ValueError, match="so it has no mean"):
        _data().plot.bar("m", by="g").plot()
    # Side by side is fine: each group's share who named the option.
    grouped = _data().plot.bar("m", split="g", show="percent")
    # Left answered: rows 0, 1, 2 → Acme 2/3, Globex 2/3, Initech 1/3; Right: row 5 only.
    assert _heights(grouped) == [[66.667, 100.0], [66.667, 0.0], [33.333, 100.0]]


def test_long_labels_on_a_small_figure_keep_a_readable_plot(tmp_path):
    data = _data()
    labels = {
        1: "Recommendation from a friend or a member of the family",
        2: "Search engine results page, paid or organic",
        3: "Television, radio or cinema advertising campaign",
    }
    variables = VariableMap()
    variables.add_many([v for v in data.variables.values() if v.name != "q"])
    variables.add(Variable("q", "nominal", label="How did you first hear about us?", labels=labels))
    long = SurveyData(frame=data.frame.assign(q=[1, 1, 2, 3, 3, 2, 1, 2]), variables=variables)
    chart = long.plot.bar("q", split="g", layout="stacked_100", figsize=(4, 3))
    _rendered(chart, tmp_path)
    ax = chart.plot()
    fig = ax.figure
    height = ax.get_window_extent().height * 72 / fig.dpi
    assert height >= 109.5  # points: the figure grew rather than squash the plot
    assert fig.get_figheight() > 3
    assert fig.get_figwidth() == 4  # and kept its width
    # Too narrow for a legend beside the plot: it sits under it, above the notes.
    assert ax.get_legend() is None and len(fig.legends) == 1
    renderer = fig.canvas.get_renderer()
    legend_box = fig.legends[0].get_window_extent(renderer)
    note_box = fig.texts[0].get_window_extent(renderer)
    assert legend_box.y0 >= note_box.y1 - 1
    assert ax.get_window_extent(renderer).y0 > legend_box.y1


# ─── the node ────────────────────────────────────────────────────────────────


def _flow(params):
    return {
        "schema_version": "1.0",
        "name": "t",
        "nodes": [
            {"id": "src", "type": "source.responses", "params": {}},
            {"id": "w", "type": "prepare.apply_weight", "params": {"column": "w"}},
            {"id": "n", "type": "visualize.bar", "params": params},
        ],
        "edges": [
            {"from": {"node": "src", "port": "data"}, "to": {"node": "w", "port": "data"}},
            {"from": {"node": "w", "port": "data"}, "to": {"node": "n", "port": "data"}},
        ],
    }


@pytest.fixture(scope="module")
def questionnaire_doc():
    from siamang.model import loads

    return loads((DOCUMENTS / "brand_awareness.questionnaire.json").read_text("utf-8"))


@pytest.fixture(scope="module")
def survey(questionnaire_doc):
    from siamang.model import from_document

    return from_document(questionnaire_doc).survey


def test_a_stored_bar_chart_renders_the_code_it_always_did(questionnaire_doc):
    from siamang.flow.document import resolve_flow
    from siamang.flow.template import render_node

    for params, by in (
        ({"variable": "region"}, "None"),
        ({"variable": "age", "by": "region"}, "'region'"),
    ):
        graph = resolve_flow(_flow(params), questionnaire=questionnaire_doc)
        assert render_node(graph, "n") == (
            f"n_n = n_w.plot.bar('{params['variable']}', by={by}, horizontal=False, "
            "show_values=True, title=None, figsize=(10.0, 6.0), palette='muted')\n"
        )


def test_the_bar_node_checks_its_combinations(questionnaire_doc):
    from siamang.flow import check_flow

    def issues(params):
        found = check_flow(
            _flow({"variable": "satisfaction", **params}), questionnaire=questionnaire_doc
        )
        return [(i.severity, i.message) for i in found]

    assert issues({"split": "region", "layout": "stacked_100"}) == []
    assert issues({"by": "region", "split": "gender"}) == [
        (
            "error",
            "n: By draws the mean of Variable in each group and Split by its answers in "
            "each group — clear one of them.",
        )
    ]
    assert issues({"by": "region", "show": "percent"}) == [
        (
            "warning",
            "n: By (the mean in each group) is not drawn when Show is percent; to show "
            "the answers in each group, use Split by.",
        )
    ]
    assert issues({"layout": "stacked"}) == [
        ("warning", "n: Layout applies only when Split by is set.")
    ]
    assert issues({"split": "age"})[0][0] == "error"  # a ratio variable is no group


@pytest.mark.parametrize(
    "params",
    [
        {"variable": "satisfaction", "show": "percent", "sort": "value"},
        {"variable": "trust_acme", "split": "region", "layout": "stacked_100", "horizontal": True},
        {"variable": "aware", "split": "gender", "show": "percent"},
        {"variable": "age", "by": "region", "sort": "value"},
    ],
)
def test_the_bar_node_checks_generates_and_runs(params, questionnaire_doc, survey, tmp_path):
    from siamang.flow import FlowRunner, check_flow, generate_flow

    flow = _flow(params)
    assert check_flow(flow, questionnaire=questionnaire_doc) == []
    code = generate_flow(flow, questionnaire_doc)
    compile(code, "bar.py", "exec")
    simulated = survey.simulate(n=150, seed=5)
    frame = simulated.frame.assign(w=np.random.default_rng(1).uniform(0.5, 2.0, 150))
    data = SurveyData(frame=frame, variables=simulated.variables, questionnaire=survey)
    result = FlowRunner(flow, questionnaire=survey).run(sources={"src": data}, cwd=tmp_path)
    chart = result.output("n")
    _rendered(chart, tmp_path)
    assert chart.weight_note == "weighted by 'w'"
    assert "Weighted by 'w'" in _footnote(chart)
    if params["variable"] == "trust_acme":  # its 9 = Refused is left out and said
        assert "Left out as missing: Trust: Acme:" in _footnote(chart)
        assert "(9 = Refused)" in _footnote(chart)


def test_the_bar_node_says_what_its_new_fields_do():
    from siamang.flow import default_registry

    spec = default_registry().get("visualize.bar")
    payload = json.loads(json.dumps(spec.to_json()))
    assert payload["params"]["show"]["values"] == ["count", "percent"]
    assert payload["params"]["layout"]["values"] == ["grouped", "stacked", "stacked_100"]
    assert payload["params"]["sort"]["values"] == ["code", "value"]
    assert payload["params"]["split"]["label"] == "Split by"
    # By is not read when Show is percent, so a builder hides it.
    assert (
        spec.reads("by", {**{n: p.default for n, p in spec.params.items()}, "show": "percent"})
        is False
    )
    assert spec.reads("by", {n: p.default for n, p in spec.params.items()}) is True


def test_tick_labels_never_run_into_each_other(tmp_path):
    """Nine answers, one of them a word longer than its bar's slot: the labels
    wrap, shrink or turn, and no two of them overlap."""

    labels = {
        1: "Recommendation from a friend or family member",
        2: "Search engine (Google, Bing and similar)",
        3: "Social media advertising",
        4: "Television or radio advertising",
        5: "Newspaper or magazine",
        6: "Walked past the shop",
        7: "Comparison website",
        8: "Email newsletter",
        9: "Other",
    }
    variables = VariableMap()
    variables.add(Variable("c", "nominal", label="How did you first hear about us?", labels=labels))
    frame = pd.DataFrame({"c": [code for code in labels for _ in range(code)]})
    for size in ((10, 6), (7, 5)):
        chart = SurveyData(frame=frame, variables=variables).plot.bar(
            "c", sort="value", figsize=size
        )
        chart.save(tmp_path / "ticks.png")
        ax = chart.plot()
        renderer = ax.figure.canvas.get_renderer()
        boxes = sorted(
            (t.get_window_extent(renderer) for t in ax.get_xticklabels()), key=lambda b: b.x0
        )
        rotated = ax.get_xticklabels()[0].get_rotation() != 0
        if not rotated:
            assert all(
                left.x1 <= right.x0 + 0.5 for left, right in zip(boxes, boxes[1:], strict=False)
            )
        else:  # turned: each label's anchor is further right than the last one's
            assert all(left.x1 < right.x1 for left, right in zip(boxes, boxes[1:], strict=False))


def _tick_values(axis) -> list[tuple[float, str]]:
    """Each major tick shown on ``axis``, with its label."""
    low, high = sorted(axis.get_view_interval())
    return [
        (float(tick), label.get_text())
        for tick, label in zip(axis.get_majorticklocs(), axis.get_ticklabels(), strict=True)
        if low - 1e-9 <= tick <= high + 1e-9
    ]


def test_a_percent_axis_labels_every_tick_with_its_own_value():
    """matplotlib's 2.5-point steps printed without decimals read 0, 2, 5, 8,
    10 %: the ticks fall on whole percents, and each says its own value."""

    codes = list(range(1, 7))
    frame = pd.DataFrame({"q": np.repeat(codes, [18, 17, 17, 16, 16, 16])})
    variables = VariableMap()
    variables.add(Variable("q", "nominal", label="Brand", labels={c: f"Brand {c}" for c in codes}))
    data = SurveyData(frame=frame, variables=variables)
    for horizontal in (False, True):
        chart = data.plot.bar("q", show="percent", horizontal=horizontal)
        ax = chart.plot()
        ax.figure.canvas.draw()
        ticks = _tick_values(ax.xaxis if horizontal else ax.yaxis)
        assert len(ticks) >= 3
        for value, text in ticks:
            assert text == f"{value:.0f}%" and value == int(value), ticks


# ─── long labels, many categories ────────────────────────────────────────────

LONG = [
    f"Brand number {i:02d} with a rather long descriptive product name (family size)"
    for i in range(1, 25)
]


def _brands(weighted: bool = False) -> SurveyData:
    rng = np.random.default_rng(0)
    frame = pd.DataFrame(
        {
            "b": rng.integers(1, 25, 1200).astype(float),
            "g": rng.integers(1, 4, 1200).astype(float),
            "m": [
                sorted(rng.choice(np.arange(1, 21), 3, replace=False).tolist()) for _ in range(1200)
            ],
            "y": rng.normal(50, 10, 1200),
            "h": rng.integers(1, 5, 1200).astype(float),
            "w": rng.uniform(0.5, 2.0, 1200),
        }
    )
    variables = VariableMap()
    variables.add_many(
        [
            Variable(
                "b", "nominal", label="Brand bought", labels={i + 1: t for i, t in enumerate(LONG)}
            ),
            Variable(
                "g",
                "nominal",
                label="Overall satisfaction with the service received during the last visit "
                "to the store",
                labels={1: "Low", 2: "Middle", 3: "High"},
            ),
            Variable(
                "m",
                "nominal",
                label="Services used",
                labels={i: f"Service option number {i}: {LONG[i][13:60]}" for i in range(1, 21)},
            ),
            Variable("y", "interval", label="Score"),
            Variable("h", "ordinal", label="Grade", labels={1: "A", 2: "B", 3: "C", 4: "D"}),
        ]
    )
    data = SurveyData(frame=frame, variables=variables)
    return data.with_weight("w") if weighted else data


def _boxes(chart, axis: str):
    ax = chart.plot()
    ax.figure.canvas.draw()
    renderer = ax.figure.canvas.get_renderer()
    labels = ax.get_yticklabels() if axis == "y" else ax.get_xticklabels()
    return [label.get_window_extent(renderer) for label in labels if label.get_text()]


def _overlaps(boxes) -> int:
    return sum(
        1
        for i, a in enumerate(boxes)
        for b in boxes[i + 1 :]
        if min(a.x1, b.x1) - max(a.x0, b.x0) > 0.5 and min(a.y1, b.y1) - max(a.y0, b.y0) > 0.5
    )


@pytest.mark.parametrize(
    ("column", "kwargs"),
    [
        ("b", {"show": "percent"}),
        ("b", {"show": "percent", "sort": "value"}),
        ("b", {"show": "percent", "figsize": (4, 3)}),
        ("g", {"show": "count", "split": "b", "layout": "stacked"}),
    ],
)
def test_many_long_labels_never_print_over_each_other(column, kwargs, tmp_path):
    """24 brands of 73 characters: across, the labels get the room of a row
    each (smaller, wider, else a taller figure); under vertical bars they
    cannot be read even turned, so the bars are drawn across."""

    data = _brands()
    for horizontal in (True, False):
        chart = data.plot.bar(column, horizontal=horizontal, **kwargs)
        chart.save(tmp_path / "brands.png")
        boxes = _boxes(chart, "y")
        assert len(boxes) == 24  # beside the bars, one per brand
        assert _overlaps(boxes) == 0, (kwargs, horizontal)
        ax = chart.plot()
        figure = ax.figure.bbox
        title = ax.title.get_window_extent(ax.figure.canvas.get_renderer())
        assert title.x0 >= -1 and title.x1 <= figure.x1 + 1
        assert title.y0 >= max(box.y1 for box in boxes) - 1  # over the first label, not on it


def test_means_by_many_long_groups_give_each_label_its_row(tmp_path):
    data = _brands(weighted=True)
    chart = data.plot.bar("y", by="b", sort="value")
    chart.save(tmp_path / "means.png")
    boxes = _boxes(chart, "y")
    assert len(boxes) == 24 and _overlaps(boxes) == 0
    assert all("(n = " in label.get_text() for label in chart.plot().get_yticklabels())


def test_a_long_axis_title_is_wrapped_inside_the_figure_and_clear_of_the_notes(tmp_path):
    """The value axis read "% within <a whole question> (weighted)", taller
    than the figure and over the Base note: the plot's own length holds it,
    in short when the question will not fit."""

    data = _brands(weighted=True)
    for horizontal in (False, True):
        chart = data.plot.bar(
            "h", split="g", show="percent", layout="stacked_100", horizontal=horizontal
        )
        chart.save(tmp_path / "axis.png")
        ax = chart.plot()
        fig = ax.figure
        renderer = fig.canvas.get_renderer()
        for label in (ax.xaxis.label, ax.yaxis.label):
            if not label.get_text():
                continue
            box = label.get_window_extent(renderer)
            assert box.x0 >= -1 and box.y0 >= -1, label.get_text()
            assert box.x1 <= fig.bbox.x1 + 1 and box.y1 <= fig.bbox.y1 + 1, label.get_text()
            for note in fig.texts:
                assert not box.overlaps(note.get_window_extent(renderer)), label.get_text()


def test_the_value_axis_says_within_each_group_when_the_question_is_too_long():
    chart = _brands(weighted=True).plot.bar("b", split="g", show="percent", horizontal=True)
    assert chart.plot().get_xlabel() == "% within each group (weighted)"
    assert "Percentages are of each group of Overall satisfaction" in _footnote(chart)
    short = _data().plot.bar("q", split="g", show="percent")
    assert short.plot().get_ylabel() == "% within Group"


def test_a_legend_taller_than_the_plot_goes_under_it(tmp_path):
    """Twenty options of three lines each beside the plot ran off the figure
    and over the notes: such a legend is placed under the plot, above them."""

    chart = _brands().plot.bar("m", show="percent", split="g")
    chart.save(tmp_path / "legend.png")
    ax = chart.plot()
    fig = ax.figure
    renderer = fig.canvas.get_renderer()
    assert ax.get_legend() is None and len(fig.legends) == 1
    legend = fig.legends[0].get_window_extent(renderer)
    assert legend.y0 >= -1 and legend.x0 >= -1 and legend.x1 <= fig.bbox.x1 + 1
    for note in fig.texts:
        assert not legend.overlaps(note.get_window_extent(renderer))
    assert ax.get_window_extent(renderer).y0 > legend.y1
    # A legend that fits beside the plot stays there.
    beside = _data().plot.bar("q", split="g", show="percent")
    assert beside.plot().get_legend() is not None


def test_series_past_the_palette_are_all_different_and_the_wheel_does_not_close():
    """Past 'muted''s ten colours, husl's wheel gave 13 series whose first and
    last (#f77189, #f668be) and neighbours (#35ae97, #36abb0) looked alike."""
    from matplotlib.colors import to_hex, to_rgb

    from siamang.reporting.chart_parts import series_colours

    def distance(a, b) -> float:
        return sum((x - y) ** 2 for x, y in zip(to_rgb(a), to_rgb(b), strict=True)) ** 0.5

    for count in (13, 24, 30, 31, 45):
        colours = series_colours("muted", count)
        assert len({to_hex(colour) for colour in colours}) == count
        closest = min(distance(a, b) for a, b in zip(colours, colours[1:], strict=False))
        assert closest > 0.12, count
        assert distance(colours[0], colours[-1]) > 0.12, count
    chart = _brands().plot.bar("b", split="g", show="percent", layout="stacked_100")
    ax = chart.plot()
    faces = {to_hex(container.patches[0].get_facecolor()) for container in ax.containers}
    assert len(faces) == 24


def test_the_check_names_a_split_or_stack_of_several_answers(questionnaire_doc):
    """Split by a multiple-choice question, and a stack of one's options, were
    refused only when the Save report built the chart; the questionnaire says
    it before the run."""
    from siamang.flow import check_flow

    def issues(params):
        return [
            (issue.severity, issue.message)
            for issue in check_flow(_flow(params), questionnaire=questionnaire_doc)
        ]

    split = issues({"variable": "region", "split": "aware", "show": "percent"})
    assert split == [
        (
            "error",
            "n: Split by needs one answer per respondent, and Brands heard of (unaided) allows "
            "several: draw it as the Variable, or split by one of its options after Explode "
            "multiple choice.",
        )
    ]
    stacked = issues({"variable": "aware", "split": "region", "layout": "stacked"})
    assert stacked == [
        (
            "error",
            "n: Brands heard of (unaided) allows several answers, so its options overlap and "
            "cannot be stacked: draw them side by side (Layout = grouped).",
        )
    ]
    assert issues({"variable": "aware", "split": "region", "show": "percent"}) == []
