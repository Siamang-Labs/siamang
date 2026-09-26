"""The Likert chart: diverging stacked bars of items on one scale.

Two items on a five-point agree scale (9 = Don't know is a missing code);
every share below is counted by hand:

    a: 1 2 3 3 4 5 5 9 · 4  → 8 answers: 12.5 12.5 25 25 25; top-2 50, bottom-2 25
    b: 5 5 4 4 4 3 2 1 1 0  → 0 is not on the scale; 9 answers:
       22.2 11.1 11.1 33.3 22.2; top-2 55.6, bottom-2 33.3
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
import pytest

from siamang.core.variable import Variable, VariableMap
from siamang.data import SurveyData

matplotlib.use("Agg")

DOCUMENTS = Path(__file__).resolve().parent / "documents"
AGREE = {
    1: "Strongly disagree",
    2: "Disagree",
    3: "Neither",
    4: "Agree",
    5: "Strongly agree",
    9: "Don't know",
}


@pytest.fixture(autouse=True)
def _close_figures():
    import matplotlib.pyplot as plt

    yield
    plt.close("all")


def _data(**extra) -> SurveyData:
    frame = pd.DataFrame(
        {
            "a": [1, 2, 3, 3, 4, 5, 5, 9, np.nan, 4],
            "b": [5, 5, 4, 4, 4, 3, 2, 1, 1, 0],
            "w": [1, 1, 1, 1, 1, 1, 1, 1, 1, 3.0],
            **extra,
        }
    )
    variables = VariableMap()
    for name, label in (("a", "Service: the staff were friendly"), ("b", "Service: fair prices")):
        variables.add(
            Variable(
                name,
                "ordinal",
                label=label,
                labels=AGREE,
                missing_values=(9,),
                missing_labels={9: "Don't know"},
            )
        )
    variables.add(Variable("w", "ratio", label="Weight"))
    return SurveyData(frame=frame, variables=variables)


def _segments(chart, code_index: int) -> list[tuple[float, float]]:
    """(left, width) of one answer's segment on every bar, top bar first."""
    container = chart.plot().containers[code_index]
    return [(round(p.get_x(), 3), round(p.get_width(), 3)) for p in container]


def _footnote(chart) -> str:
    return " ".join(text.get_text() for text in chart.plot().figure.texts).replace("\n", " ")


def test_shares_top_and_bottom_two_and_the_order_by_top_two(tmp_path):
    chart = _data().plot.likert(["a", "b"])
    chart.save(tmp_path / "likert.png")
    table = chart.table
    assert table["Item"].tolist() == ["fair prices", "the staff were friendly"]  # b first
    assert table.loc[
        1, ["Strongly disagree", "Disagree", "Neither", "Agree", "Strongly agree"]
    ].tolist() == [
        12.5,
        12.5,
        25.0,
        25.0,
        25.0,
    ]
    assert table["Top-2"].tolist() == [55.6, 50.0]
    assert table["Bottom-2"].tolist() == [33.3, 25.0]
    assert table["N"].tolist() == [9, 8]
    ax = chart.plot()
    assert [t.get_text() for t in ax.get_yticklabels()] == [
        "fair prices (n = 9)",
        "the staff were friendly (n = 8)",
    ]
    assert ax.get_title() == "Service"  # the words both labels start with
    texts = [t.get_text() for t in ax.texts]
    assert texts[:2] == ["Bottom-2", "Top-2"]
    assert texts[2:6] == ["33%", "56%", "25%", "50%"]  # bottom, top of each bar
    note = _footnote(chart)
    assert (
        "Top-2: 4 = Agree, 5 = Strongly agree; bottom-2: 1 = Strongly disagree, 2 = Disagree."
        in note
    )
    assert "The neutral answer (3 = Neither) is split around the centre." in note
    assert "Left out as missing: Service: the staff were friendly: 1 (9 = Don't know)." in note
    assert "Not on the scale, left out: Service: fair prices: 1 (0)." in note
    assert "Items in order of their top-2 share." in note


def test_the_bars_diverge_from_the_neutral_answer_split_around_the_centre():
    chart = _data().plot.likert(["a", "b"], sort="listed")
    # a (the top bar now): neutral 25 → 12.5 each side; Disagree 12.5 to its
    # left, Strongly disagree beyond; Agree and Strongly agree to the right.
    assert _segments(chart, 0)[0] == (-37.5, 12.5)
    assert _segments(chart, 1)[0] == (-25.0, 12.5)
    assert _segments(chart, 2)[0] == (-12.5, 25.0)
    assert _segments(chart, 3)[0] == (12.5, 25.0)
    assert _segments(chart, 4)[0] == (37.5, 25.0)
    assert chart.table["Item"].tolist() == ["the staff were friendly", "fair prices"]
    # Diverging colours with a grey middle: five of them, red below, blue above.
    from matplotlib.colors import to_hex, to_rgb

    fills = [to_rgb(c.patches[0].get_facecolor()) for c in chart.plot().containers]
    assert len({to_hex(fill) for fill in fills}) == 5
    assert to_hex(fills[2]) == "#bdbdbd"
    assert fills[0][0] > fills[0][2] and fills[4][2] > fills[4][0]
    # The legend in the scale's order.
    legend = chart.plot().figure.legends[0]
    assert sorted(t.get_text() for t in legend.get_texts()) == sorted(
        ["Strongly disagree", "Disagree", "Neither", "Agree", "Strongly agree"]
    )


def test_the_neutral_answer_apart_is_drawn_in_a_panel_at_the_right(tmp_path):
    chart = _data().plot.likert(["a", "b"], neutral="side", sort="listed")
    chart.save(tmp_path / "side.png")
    main, aside = chart.plot().figure.axes[:2]
    assert len(main.containers) == 4  # the neutral answer is not on the main axes
    assert _segments(chart, 1)[0] == (-12.5, 12.5)  # Disagree from the centre
    assert _segments(chart, 2)[0] == (0.0, 25.0)  # Agree from the centre
    neutral = [round(p.get_width(), 3) for p in aside.patches]
    assert neutral == [25.0, 11.111]
    assert aside.get_title() == "Neither"
    assert "is drawn apart, at the right" in _footnote(chart)


def test_an_even_scale_centres_between_its_middle_answers():
    four = {1: "Poor", 2: "Fair", 3: "Good", 4: "Excellent"}
    variables = VariableMap()
    variables.add_many([Variable(n, "ordinal", label=n.upper(), labels=four) for n in ("x", "y")])
    data = SurveyData(
        frame=pd.DataFrame({"x": [1, 2, 3, 4, 4], "y": [1, 1, 2, 3, 4]}), variables=variables
    )
    chart = data.plot.likert(["x", "y"], sort="listed", neutral="side")
    assert len(chart.plot().figure.axes) == 1  # no neutral answer to put aside
    assert _segments(chart, 1)[0] == (-20.0, 20.0)  # Fair: 1 of 5, left of 0
    assert _segments(chart, 2)[0] == (0.0, 20.0)  # Good: right of 0
    assert chart.table["Top-2"].tolist() == [60.0, 40.0]
    assert "No neutral answer: the centre falls between 2 = Fair and 3 = Good." in _footnote(chart)


def test_a_three_point_scale_has_a_top_and_bottom_box_of_one_answer():
    three = {1: "Worse", 2: "Same", 3: "Better"}
    variables = VariableMap()
    variables.add(Variable("x", "ordinal", label="Change", labels=three))
    data = SurveyData(frame=pd.DataFrame({"x": [1, 2, 2, 3]}), variables=variables)
    chart = data.plot.likert(["x"])
    assert chart.table["Top box"].tolist() == [25.0] and chart.table["Bottom box"].tolist() == [
        25.0
    ]
    assert [t.get_text() for t in chart.plot().texts][:2] == ["Bottom box", "Top box"]


def test_weighted_shares_are_sums_of_weights():
    # a's answers weigh 1 each except the last 4, which weighs 3: total 10.
    chart = _data().with_weight("w").plot.likert(["a"])
    assert chart.table.loc[
        0, ["Strongly disagree", "Disagree", "Neither", "Agree", "Strongly agree"]
    ].tolist() == [
        10.0,
        10.0,
        20.0,
        40.0,
        20.0,
    ]
    assert chart.table.loc[0, ["Top-2", "N", "Weighted N"]].tolist() == [60.0, 8, 10.0]
    assert chart.weight_note == "weighted by 'w'"
    assert chart.plot().get_xlabel() == "% of respondents (weighted)"
    assert "Weighted by 'w'; n counts respondents." in _footnote(chart)


def test_items_on_different_scales_are_refused_by_name():
    data = _data()
    variables = VariableMap()
    variables.add_many(list(data.variables.values()))
    variables.add(
        Variable("s", "ordinal", label="Satisfaction", labels={1: "Low", 2: "Mid", 3: "High"})
    )
    other = SurveyData(frame=data.frame.assign(s=1), variables=variables)
    with pytest.raises(ValueError) as refused:
        other.plot.likert(["a", "s"]).plot()
    assert str(refused.value) == (
        "The items of a Likert chart must share one scale, and these do not: Service: the "
        "staff were friendly has 1 = Strongly disagree, 2 = Disagree, 3 = Neither, 4 = Agree, "
        "5 = Strongly agree; Satisfaction has 1 = Low, 2 = Mid, 3 = High. Draw them in "
        "separate charts, or recode them onto one scale first."
    )
    # The same labels written differently (case, spaces) are one scale.
    shouting = {code: label.upper() + "  " for code, label in AGREE.items()}
    variables.add(Variable("c", "ordinal", label="C", labels=shouting, missing_values=(9,)))
    same = SurveyData(frame=data.frame.assign(c=data.frame["a"]), variables=variables)
    assert same.plot.likert(["a", "c"]).table["N"].tolist() == [8, 8]


@pytest.mark.parametrize(
    ("items", "kwargs", "message"),
    [
        (["m"], {}, "allows several answers"),
        (["plain"], {}, "none of the items has value labels"),
        (["a"], {"neutral": "left"}, "neutral must be one of split, side"),
        (["a"], {"sort": "bottom2"}, "sort must be one of top2, listed"),
        (["nope"], {}, "No variable 'nope' in the data."),
    ],
)
def test_what_cannot_be_drawn_is_said(items, kwargs, message):
    data = _data(m=[[1, 2]] * 10, plain=[1] * 10)
    variables = VariableMap()
    variables.add_many(list(data.variables.values()))
    variables.add(Variable("m", "nominal", label="M", labels=AGREE))
    variables.add(Variable("plain", "ordinal", label="Plain"))
    with pytest.raises(ValueError, match=message):
        SurveyData(frame=data.frame, variables=variables).plot.likert(items, **kwargs).plot()


def test_a_valid_range_stands_in_for_labels():
    variables = VariableMap()
    variables.add(Variable("r", "interval", label="Rating", valid_range=(1, 5)))
    data = SurveyData(frame=pd.DataFrame({"r": [1, 5, 5, 4]}), variables=variables)
    assert data.plot.likert(["r"]).table.columns.tolist()[1:6] == ["1", "2", "3", "4", "5"]


def test_a_long_battery_on_a_small_figure_keeps_every_bar_readable(tmp_path):
    statements = [
        "The staff were friendly and helpful when I needed assistance in the shop",
        "Prices are fair for the quality of what you get, compared with other shops",
        "The website is easy to navigate and to find the products I was looking for on",
        "Delivery arrived on time and in good condition, and I was told when to expect it",
    ]
    rng = np.random.default_rng(0)
    variables = VariableMap()
    frame = {}
    for index, text in enumerate(statements):
        variables.add(
            Variable(f"s{index}", "ordinal", label=text, labels=AGREE, missing_values=(9,))
        )
        frame[f"s{index}"] = rng.integers(1, 6, 80)
    chart = SurveyData(frame=pd.DataFrame(frame), variables=variables).plot.likert(
        list(frame), figsize=(6, 3)
    )
    chart.save(tmp_path / "small.png")
    ax = chart.plot()
    renderer = ax.figure.canvas.get_renderer()
    boxes = [t.get_window_extent(renderer) for t in ax.get_yticklabels()]
    assert all(upper.y0 >= lower.y1 - 0.5 for upper, lower in zip(boxes, boxes[1:], strict=False))
    legend = ax.figure.legends[0].get_window_extent(renderer)
    note = ax.figure.texts[0].get_window_extent(renderer)
    assert legend.y0 >= note.y1 - 1 and ax.get_window_extent(renderer).y0 > legend.y1
    assert ax.figure.get_figwidth() == 6


# ─── the node ────────────────────────────────────────────────────────────────


def _flow(params, weight=True):
    nodes = [{"id": "src", "type": "source.responses", "params": {}}]
    edges = []
    source = "src"
    if weight:
        nodes.append({"id": "w", "type": "prepare.apply_weight", "params": {"column": "w"}})
        edges.append({"from": {"node": "src", "port": "data"}, "to": {"node": "w", "port": "data"}})
        source = "w"
    nodes.append({"id": "n", "type": "visualize.likert", "params": params})
    edges.append({"from": {"node": source, "port": "data"}, "to": {"node": "n", "port": "data"}})
    return {"schema_version": "1.0", "name": "t", "nodes": nodes, "edges": edges}


@pytest.fixture(scope="module")
def questionnaire_doc():
    from siamang.model import loads

    return loads((DOCUMENTS / "brand_awareness.questionnaire.json").read_text("utf-8"))


def test_the_check_names_items_on_different_scales(questionnaire_doc):
    from siamang.flow import check_flow

    assert (
        check_flow(
            _flow({"items": ["trust_acme", "trust_globex"]}), questionnaire=questionnaire_doc
        )
        == []
    )
    issues = check_flow(
        _flow({"items": ["trust_acme", "satisfaction"]}), questionnaire=questionnaire_doc
    )
    assert [(i.severity, i.code, i.message) for i in issues] == [
        (
            "error",
            "PARAM_CONFLICT",
            "n: The items of a Likert chart must share one scale, and these do not: Trust: "
            "Acme has 1 = No trust, 2 = Low, 3 = Medium, 4 = High, 5 = Full; Overall "
            "satisfaction has 1 = Very dissatisfied, 2 = Dissatisfied, 3 = Neutral, "
            "4 = Satisfied, 5 = Very satisfied. Draw them in separate charts, or recode "
            "them onto one scale first.",
        )
    ]
    # A nominal variable is not a scale.
    wrong = check_flow(_flow({"items": ["region"]}), questionnaire=questionnaire_doc)
    assert [i.code for i in wrong] == ["VARIABLE_SCALE"]


def test_the_likert_node_checks_generates_and_runs(questionnaire_doc, tmp_path):
    from siamang.flow import FlowRunner, check_flow, default_registry, generate_flow
    from siamang.model import from_document

    spec = default_registry().get("visualize.likert")
    assert spec.to_json()["params"]["neutral"]["values"] == ["split", "side"]
    flow = _flow({"items": ["trust_acme", "trust_globex"], "neutral": "side"})
    assert check_flow(flow, questionnaire=questionnaire_doc) == []
    code = generate_flow(flow, questionnaire_doc)
    assert "n_w.plot.likert(" in code and 'neutral="side"' in code
    compile(code, "likert.py", "exec")
    survey = from_document(questionnaire_doc).survey
    simulated = survey.simulate(n=150, seed=9)
    frame = simulated.frame.assign(w=np.random.default_rng(4).uniform(0.5, 2.0, 150))
    data = SurveyData(frame=frame, variables=simulated.variables, questionnaire=survey)
    chart = FlowRunner(flow, questionnaire=survey).run(sources={"src": data}).output("n")
    chart.save(tmp_path / "flow.png")
    assert chart.weight_note == "weighted by 'w'"
    assert chart.plot().get_title() == "Trust"
    assert chart.table["Item"].tolist() in (["Acme", "Globex"], ["Globex", "Acme"])
    assert "(9 = Refused)" in _footnote(chart)
