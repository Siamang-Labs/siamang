"""The heatmap's correlation method: Spearman as it always was, Pearson
(weighted on weighted data) and Kendall with the missing codes left out.

The five complete respondents below make every coefficient arithmetic by hand:
x = 1..5, y = 2 1 4 3 5, z = 5 3 4 1 2.
"""

from __future__ import annotations

import math
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
            # Row 5's x is 9 = Refused, row 6 has no y: five complete rows.
            "x": [1, 2, 3, 4, 5, 9, 2],
            "y": [2, 1, 4, 3, 5, 3, np.nan],
            "z": [5, 3, 4, 1, 2, 2, 4],
            "c": [3, 3, 3, 3, 3, 3, 3],
            "w": [1.0, 2.0, 1.0, 1.0, 3.0, 1.0, 1.0],
        }
    )
    variables = VariableMap()
    variables.add_many(
        [
            Variable(
                "x",
                "ordinal",
                label="Trust",
                labels={1: "None", 5: "Full", 9: "Refused"},
                missing_values=(9,),
                missing_labels={9: "Refused"},
            ),
            Variable("y", "ordinal", label="Liking"),
            Variable("z", "ordinal", label="Price"),
            Variable("c", "ordinal", label="Constant"),
            Variable("w", "ratio", label="Weight"),
        ]
    )
    return SurveyData(frame=frame, variables=variables)


def _cells(chart) -> np.ndarray:
    mesh = chart.plot().collections[0]
    size = int(math.isqrt(mesh.get_array().size))
    return np.ma.filled(mesh.get_array().astype(float), np.nan).reshape(size, size)


def _footnote(chart) -> str:
    return " ".join(text.get_text() for text in chart.plot().figure.texts).replace("\n", " ")


def test_pearson_leaves_the_missing_code_out_and_says_so(tmp_path):
    # Deviations from the means (3, 3, 3): x -2 -1 0 1 2, y -1 -2 1 0 2, z 2 0 1 -2 -1;
    # every sum of squares is 10, so r = Σ products / 10: xy 8, xz -8, yz -3.
    chart = _data().plot.heatmap(["x", "y", "z"], method="pearson")
    chart.save(tmp_path / "pearson.png")
    assert np.round(_cells(chart), 6).tolist() == [
        [1.0, 0.8, -0.8],
        [0.8, 1.0, -0.3],
        [-0.8, -0.3, 1.0],
    ]
    ax = chart.plot()
    assert ax.get_title() == "Pearson Correlation Matrix"
    assert [t.get_text() for t in ax.get_yticklabels()] == ["Trust", "Liking", "Price"]
    assert [t.get_text() for t in ax.get_xticklabels()] == ["Trust", "Liking", "Price"]
    assert [t.get_text() for t in ax.texts][:3] == ["1.00", "0.80", "-0.80"]
    assert ax.figure.axes[-1].get_ylabel() == "Pearson r"  # the colour bar
    note = _footnote(chart)
    assert "N = 5 respondents who answered every item (listwise)." in note
    assert "Left out as missing: Trust: 1 (9 = Refused)." in note
    assert chart.weight_note is None


def test_kendall_is_tau_b_and_says_the_weight_is_not_applied(tmp_path):
    # Discordant pairs of 10: xy 2 → tau 0.6; xz 8 → -0.6; yz 6 → -0.2.
    chart = _data().with_weight("w").plot.heatmap(["x", "y", "z"], method="kendall")
    chart.save(tmp_path / "kendall.png")
    assert np.round(_cells(chart), 6).tolist() == [
        [1.0, 0.6, -0.6],
        [0.6, 1.0, -0.2],
        [-0.6, -0.2, 1.0],
    ]
    note = "unweighted (the weight 'w' is not applied)"
    assert chart.weight_note == note
    assert chart.plot().get_title() == f"Kendall tau-b Correlation Matrix\n{note}"


def test_weighted_pearson_is_the_correlation_matrix_table_s(tmp_path):
    # Weights 1 2 1 1 3 (total 8): means x 27/8, y 26/8; Σw·dx·dy = 17.25,
    # Σw·dx² = 17.875, Σw·dy² = 21.5.
    weighted = _data().with_weight("w")
    chart = weighted.plot.heatmap(["x", "y", "z"], method="pearson")
    chart.save(tmp_path / "weighted.png")
    assert _cells(chart)[0, 1] == pytest.approx(17.25 / math.sqrt(17.875 * 21.5), abs=1e-12)
    table = weighted.report.correlation_matrix(
        ["x", "y", "z"], method="pearson", missing="listwise"
    )
    np.testing.assert_allclose(_cells(chart), table.result.coefficients.to_numpy(), atol=1e-12)
    assert chart.weight_note == "weighted by 'w'"
    assert chart.plot().figure.axes[-1].get_ylabel() == "Weighted Pearson r"
    assert "Weighted by 'w': the coefficients are weighted; N counts respondents." in _footnote(
        chart
    )


def test_a_pair_that_cannot_be_computed_is_a_blank_cell_said_under_the_plot():
    chart = _data().plot.heatmap(["x", "c"], method="pearson")
    cells = _cells(chart)
    assert cells[0, 0] == 1.0 and np.isnan(cells[0, 1])
    # The constant item correlates with nothing, itself included: no "1.00"
    # in a blank row, and the pair is named as the chart names its items.
    assert np.isnan(cells[1, 1])
    assert [t.get_text() for t in chart.plot().texts] == ["1.00"]
    assert (
        "Not computed (a blank cell): Trust × Constant: a variable has the same value for "
        "everyone, so it correlates with nothing." in _footnote(chart)
    )
    assert not any(line.get_visible() for line in chart.plot().get_xgridlines())
    assert not any(line.get_visible() for line in chart.plot().get_ygridlines())


def _items(count: int) -> SurveyData:
    rng = np.random.default_rng(4)
    base = rng.normal(size=300)
    frame = pd.DataFrame(
        {f"s{i}": np.clip(np.round(3 + base * (i % 3) / 2 + rng.normal(size=300)), 1, 5)
         for i in range(1, count + 1)}
    )  # fmt: skip
    variables = VariableMap()
    variables.add_many(
        [
            Variable(
                f"s{i}", "ordinal",
                label=f"Agreement: statement number {i} about the service in the store",
            )
            for i in range(1, count + 1)
        ]
    )  # fmt: skip
    return SurveyData(frame=frame, variables=variables)


def test_the_coefficients_fit_their_cells_or_are_left_to_the_table(tmp_path):
    """14 items at 10 × 6 in wrote 12-pt coefficients into 48-pt cells, 13 of
    13 neighbours running together; the size now follows the cell."""
    chart = _items(14).plot.heatmap([f"s{i}" for i in range(1, 15)], method="pearson")
    chart.save(tmp_path / "fourteen.png")
    ax = chart.plot()
    renderer = ax.figure.canvas.get_renderer()
    texts = list(ax.texts)
    assert len(texts) == 14 * 14 and 6 <= texts[0].get_fontsize() < 12
    boxes = [text.get_window_extent(renderer) for text in texts]
    for row in range(14):
        line = sorted(boxes[row * 14 : (row + 1) * 14], key=lambda box: box.x0)
        assert all(a.x1 <= b.x0 for a, b in zip(line, line[1:], strict=False)), row
    # Too small a cell: no numbers, and the note says where they are.
    small = _items(14).plot.heatmap(
        [f"s{i}" for i in range(1, 15)], method="pearson", figsize=(4, 3)
    )
    small.save(tmp_path / "small.png")
    assert len(small.plot().texts) == 0
    assert "too small to hold their coefficients: see the table" in _footnote(small)


def test_a_small_figure_is_not_stretched_into_a_strip(tmp_path):
    """figsize=(6, 4) with 14 long labels grew to 6 × 17 inches: the rows'
    labels get smaller and wider first."""
    chart = _items(14).plot.heatmap(
        [f"s{i}" for i in range(1, 15)], method="kendall", figsize=(6, 4)
    )
    chart.save(tmp_path / "strip.png")
    ax = chart.plot()
    assert chart._fig.get_figwidth() == 6 and chart._fig.get_figheight() <= 8
    renderer = ax.figure.canvas.get_renderer()
    boxes = sorted(
        (t.get_window_extent(renderer) for t in ax.get_yticklabels()), key=lambda b: b.y0
    )
    assert all(low.y1 <= high.y0 + 0.5 for low, high in zip(boxes, boxes[1:], strict=False))


def test_long_labels_are_numbered_and_every_row_holds_its_label(tmp_path):
    data = _data()
    variables = VariableMap()
    long = {
        "x": "I trust the company to handle my personal data responsibly",
        "y": "I like the look and feel of the new website and the app",
        "z": "The prices are fair for the quality of what you get",
    }
    variables.add_many([Variable(name, "ordinal", label=label) for name, label in long.items()])
    chart = SurveyData(frame=data.frame, variables=variables).plot.heatmap(
        ["x", "y", "z"], method="kendall", figsize=(6, 3)
    )
    chart.save(tmp_path / "long.png")
    ax = chart.plot()
    assert [t.get_text() for t in ax.get_xticklabels()] == ["1", "2", "3"]
    rows = [t.get_text() for t in ax.get_yticklabels()]
    assert rows[0].startswith("1. I trust the company") and "\n" in rows[0]
    renderer = ax.figure.canvas.get_renderer()
    boxes = [t.get_window_extent(renderer) for t in ax.get_yticklabels()]
    assert all(upper.y0 >= lower.y1 - 0.5 for upper, lower in zip(boxes, boxes[1:], strict=False))


def test_spearman_draws_what_it_always_drew():
    """The default: every complete row, the 9 read as an answer, no footnote."""
    data = _data()
    chart = data.plot.heatmap(["x", "y", "z"])
    expected = data.frame[["x", "y", "z"]].dropna().corr(method="spearman").to_numpy()
    np.testing.assert_allclose(_cells(chart), expected)
    assert chart.plot().get_title() == "Spearman Correlation Matrix"
    assert chart.plot().figure.texts == []
    assert data.plot.heatmap(["x", "y"], method="spearman").plot().figure.texts == []
    with pytest.raises(ValueError, match="method must be one of pearson, spearman, kendall"):
        data.plot.heatmap(["x", "y"], method="phi").plot()


# ─── the node ────────────────────────────────────────────────────────────────


def _flow(params):
    return {
        "schema_version": "1.0",
        "name": "t",
        "nodes": [
            {"id": "src", "type": "source.responses", "params": {}},
            {"id": "w", "type": "prepare.apply_weight", "params": {"column": "w"}},
            {"id": "n", "type": "visualize.heatmap", "params": params},
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


def test_a_stored_heatmap_renders_the_code_it_always_did(questionnaire_doc):
    from siamang.flow.document import resolve_flow
    from siamang.flow.template import render_node

    graph = resolve_flow(
        _flow({"items": ["trust_acme", "trust_globex"]}), questionnaire=questionnaire_doc
    )
    assert render_node(graph, "n") == (
        "n_n = n_w.plot.heatmap(['trust_acme', 'trust_globex'], by=None, title=None, "
        "figsize=(10.0, 6.0), cmap='YlOrRd')\n"
    )


def test_the_heatmap_node_checks_generates_and_runs(questionnaire_doc, tmp_path):
    from siamang.flow import FlowRunner, check_flow, generate_flow
    from siamang.model import from_document

    survey = from_document(questionnaire_doc).survey
    flow = _flow({"items": ["trust_acme", "trust_globex", "satisfaction"], "method": "pearson"})
    assert check_flow(flow, questionnaire=questionnaire_doc) == []
    code = generate_flow(flow, questionnaire_doc)
    assert 'method="pearson"' in code
    simulated = survey.simulate(n=150, seed=8)
    frame = simulated.frame.assign(w=np.random.default_rng(3).uniform(0.5, 2.0, 150))
    data = SurveyData(frame=frame, variables=simulated.variables, questionnaire=survey)
    chart = FlowRunner(flow, questionnaire=survey).run(sources={"src": data}).output("n")
    chart.save(tmp_path / "flow.png")
    assert chart.weight_note == "weighted by 'w'"
    assert "(9 = Refused)" in _footnote(chart)

    warned = check_flow(
        _flow({"items": ["trust_acme", "trust_globex"], "by": "region", "method": "kendall"}),
        questionnaire=questionnaire_doc,
    )
    assert [(i.severity, i.message) for i in warned] == [
        (
            "warning",
            "n: Method applies to the correlation matrix drawn without By; with By the "
            "heatmap shows means.",
        )
    ]


# ─── means by group in the theme's colours ───────────────────────────────────

AGREEMENT = {1: "Strongly disagree", 2: "Disagree", 3: "Neutral", 4: "Agree", 5: "Strongly agree"}


def _rated(weighted: bool = False) -> SurveyData:
    frame = pd.DataFrame(
        {
            "q1": [1, 2, 3, 4, 5, 99, 4, 5, 3, 99],
            "q2": [5, 4, 4, 99, 5, 3, 2, 1, 2, 3],
            "g": [1, 1, 1, 1, 1, 2, 2, 2, 2, 2],
            "w": [1.0, 2.0, 1.0, 1.0, 1.0, 1.0, 3.0, 1.0, 1.0, 1.0],
        }
    )
    labels = {**AGREEMENT, 99: "Not applicable"}
    variables = VariableMap()
    variables.add_many(
        [
            Variable(
                "q1", "ordinal", label="Staff were helpful", labels=labels, missing_values=[99]
            ),
            Variable("q2", "ordinal", label="Prices are fair", labels=labels, missing_values=[99]),
            Variable("g", "nominal", label="Group", labels={1: "A", 2: "B"}),
        ]
    )
    data = SurveyData(frame=frame, variables=variables)
    return data.with_weight("w") if weighted else data


def _mean_cells(ax) -> dict[tuple[str, str], str]:
    rows = [label.get_text() for label in ax.get_yticklabels()]
    columns = [label.get_text().split("\n")[0] for label in ax.get_xticklabels()]
    return {
        (rows[int(text.get_position()[1])], columns[int(text.get_position()[0])]): text.get_text()
        for text in ax.texts
    }


def test_means_by_group_in_the_theme_s_colours_leave_the_missing_codes_out():
    """The classic form averaged 99 = Not applicable into a 1–5 item's mean
    (42.00, 23.40); in the theme's colours each cell is the mean of the
    group's respondents who answered the item — Group means' numbers."""
    data = _rated()
    ax = data.plot.heatmap(["q1", "q2"], by="g", cmap="theme").plot()
    assert _mean_cells(ax) == {
        ("1. Staff were helpful", "A"): "3.00",  # 1..5
        ("1. Staff were helpful", "B"): "4.00",  # 4, 5, 3
        ("2. Prices are fair", "A"): "4.50",  # 5, 4, 4, 5
        ("2. Prices are fair", "B"): "2.20",  # 3, 2, 1, 2, 3
    }
    for column, group in (("q1", 2), ("q2", 1)):
        own = data.with_frame(data.frame[data.frame[column] != 99])
        mean = own.report.means(column, by="g", method="welch_anova").to_frame()["Mean"]
        assert f"{mean.iloc[group - 1]:.2f}" in _mean_cells(ax).values()
    notes = " ".join(text.get_text() for text in ax.figure.texts).replace("\n", " ")
    assert "Left out as missing: Staff were helpful: 2 (99); Prices are fair: 1 (99)." in notes
    assert [label.get_text() for label in ax.get_xticklabels()] == ["A\n(n = 5)", "B\n(n = 5)"]
    # Weighted: each item's weighted mean (q1 in A: (1 + 4 + 3 + 4 + 5) / 6).
    weighted = data.with_weight("w").plot.heatmap(["q1"], by="g", cmap="theme").plot()
    assert _mean_cells(weighted)[("1. Staff were helpful", "A")] == f"{(1 + 4 + 3 + 4 + 5) / 6:.2f}"
    # A named colour map draws what it always drew: 99 counted.
    classic = data.plot.heatmap(["q1", "q2"], by="g").plot()
    assert "42.00" in {text.get_text() for text in classic.texts}


def test_many_long_items_by_many_groups_keep_their_mean_cells():
    """Twelve items of about 60 characters by eight groups made tight_layout
    give up and the heatmap a strip whose values lay on top of one another:
    the items are numbered and wrapped, and the cells keep their values apart."""
    rng = np.random.default_rng(2)
    items = [f"q{i}" for i in range(1, 13)]
    frame = pd.DataFrame({name: rng.integers(1, 6, 400) for name in items})
    frame["g"] = rng.integers(1, 9, 400)
    variables = VariableMap()
    variables.add_many(
        [
            Variable(
                name,
                "ordinal",
                label=f"Statement {i}: the service was good in way {i} of many",
                labels=AGREEMENT,
            )
            for i, name in enumerate(items, 1)
        ]
        + [
            Variable(
                "g",
                "nominal",
                label="Region",
                labels={i: f"Region number {i} of the country" for i in range(1, 9)},
            )
        ]
    )
    data = SurveyData(frame=frame, variables=variables)
    ax = data.plot.heatmap(items, by="g", cmap="theme").plot()
    fig = ax.figure
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    assert ax.get_yticklabels()[0].get_text().startswith("1. Statement 1")
    height = ax.get_window_extent(renderer).height * 72 / fig.dpi
    assert height >= 12 * 14  # a row of at least 14 pt an item
    boxes = [text.get_window_extent(renderer) for text in ax.texts]
    assert len(boxes) == 96
    assert not any(a.overlaps(b) for i, a in enumerate(boxes) for b in boxes[i + 1 :])
