"""Reading a choice-based conjoint: part-worths, importance, shares."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import siamang as sg
from siamang.data import SurveyData
from siamang.data import conjoint as cj

ATTRIBUTES = [
    sg.Attribute(
        "brand",
        [sg.Option(1, "Acme"), sg.Option(2, "Globex"), sg.Option(3, "Initech")],
        label="Brand",
    ),
    sg.Attribute(
        "price", [sg.Option(10, "10"), sg.Option(15, "15"), sg.Option(20, "20")], label="Price"
    ),
    sg.Attribute("warranty", [sg.Option(1, "1 year"), sg.Option(2, "2 years")], label="Warranty"),
]
# The first level of each attribute is the reference and sits at zero.
TRUE = {
    (0, 1): 0.0, (0, 2): 0.6, (0, 3): -0.3,
    (1, 10): 0.0, (1, 15): -0.8, (1, 20): -1.9,
    (2, 1): 0.0, (2, 2): 0.5,
}  # fmt: skip


def _question(tasks: int = 10, alternatives: int = 3, versions: int = 12, **kwargs) -> sg.Conjoint:
    variables = [
        sg.Variable(f"cbc_t{t}", "nominal", label=f"Task {t}", labels={1: "1", 2: "2", 3: "3"})
        for t in range(1, tasks + 1)
    ]
    variables.append(sg.Variable("cbc_version", "nominal", label="Design version"))
    return sg.Conjoint(
        "Which would you buy?",
        variables,
        attributes=ATTRIBUTES,
        alternatives=alternatives,
        tasks=tasks,
        versions=versions,
        seed=4,
        id="q_cbc",
        **kwargs,
    )


def _survey(question: sg.Conjoint) -> sg.Questionnaire:
    return sg.Questionnaire(title="C", pages=[sg.Page(name="p", items=[question])])


def _fieldwork(question: sg.Conjoint, n: int = 400, seed: int = 3) -> SurveyData:
    """Respondents who really do prefer what TRUE says they prefer.

    Choices are drawn from the part-worths plus Gumbel noise — the model the
    conditional logit assumes — so recovering TRUE tests the estimator rather
    than a trick in the data.
    """

    survey = _survey(question)
    design = question.resolved_design()
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(n):
        version = int(rng.integers(len(design.versions)))
        row: dict[str, object] = {"cbc_version": version}
        for task in range(question.tasks):
            profiles = design.task(version, task)
            utility = np.array([sum(TRUE[(i, code)] for i, code in enumerate(p)) for p in profiles])
            row[question.task_variable(task).name] = (
                int(np.argmax(utility + rng.gumbel(size=len(utility)))) + 1
            )
        rows.append(row)
    return SurveyData(frame=pd.DataFrame(rows), variables=survey.variables, questionnaire=survey)


def test_part_worths_recover_what_the_estimator_was_never_told():
    """The test the rest of the module stands on."""

    question = _question()
    data = _fieldwork(question)
    result = cj.part_worths(data, "q_cbc")
    assert result.stats["converged"]
    estimate = dict(zip(result.table["term"], result.table["estimate"], strict=True))
    fitted, truth = [], []
    for index, attribute in enumerate(ATTRIBUTES):
        for level in attribute.levels[1:]:
            fitted.append(estimate[f"{attribute.label}: {level.label}"])
            truth.append(TRUE[(index, level.code)])
    assert np.corrcoef(truth, fitted)[0, 1] > 0.99
    assert np.abs(np.array(truth) - np.array(fitted)).max() < 0.25
    # A level is not an alternative, so no share column: it would be read as one.
    assert "share" not in result.table.columns
    assert result.stats["reference"].count("+") == len(ATTRIBUTES) - 1


def test_importance_is_of_the_levels_that_were_shown():
    """Price tested over a wide range dominates one tested over a narrow one.
    That is a fact about the design, and the table has to carry the range so it
    is checkable rather than implied."""

    question = _question()
    data = _fieldwork(question)
    weights = cj.importance(data, "q_cbc")
    assert list(weights.columns) == [
        "attribute", "levels", "best", "worst", "range", "importance"
    ]  # fmt: skip
    assert weights["importance"].sum() == pytest.approx(100.0, abs=0.5)
    # Price spans 1.9 of utility, brand 0.9, warranty 0.5 — so price leads.
    assert weights.iloc[0]["attribute"] == "Price"
    assert weights.iloc[0]["best"] == "10" and weights.iloc[0]["worst"] == "20"
    assert (weights["range"] >= 0).all()


def test_shares_answer_what_if_we_changed_the_price():
    question = _question()
    data = _fieldwork(question)
    cheap = {"brand": 1, "price": 10, "warranty": 1}
    dear = {"brand": 1, "price": 20, "warranty": 1}
    table = cj.shares(data, "q_cbc", {"Cheap": cheap, "Dear": dear})
    assert list(table["product"]) == ["Cheap", "Dear"]
    assert table["share"].sum() == pytest.approx(100.0, abs=0.2)
    assert table.iloc[0]["share"] > table.iloc[1]["share"]
    # The same products in a list get generated names rather than being refused.
    assert set(cj.shares(data, "q_cbc", [cheap, dear])["product"]) == {"Product 1", "Product 2"}


def test_a_half_specified_product_is_refused_rather_than_guessed():
    """Filling in a missing attribute silently would be inventing the answer."""

    question = _question()
    data = _fieldwork(question, n=40)
    with pytest.raises(KeyError, match="no level for"):
        cj.shares(data, "q_cbc", {"Ours": {"brand": 1, "price": 10}})
    with pytest.raises(KeyError, match="not an attribute"):
        cj.shares(data, "q_cbc", {"Ours": {"brand": 1, "price": 10, "warranty": 1, "color": 2}})
    with pytest.raises(KeyError, match="is not a level"):
        cj.shares(data, "q_cbc", {"Ours": {"brand": 1, "price": 99, "warranty": 1}})
    with pytest.raises(ValueError, match="no 'none of these'"):
        cj.shares(
            data, "q_cbc", {"Ours": {"brand": 1, "price": 10, "warranty": 1}}, include_none=True
        )


def test_none_of_these_is_an_alternative_not_a_missing_answer():
    """Without a utility of its own, refusing to buy would be modeled as
    indifference between the products on offer."""

    question = _question(tasks=8, versions=8, none_label="I would buy none of these")
    data = _fieldwork(question, n=200)
    # Make a quarter of the answers "none" — alternative 4 of 3 products.
    frame = data.frame.copy()
    for task in range(question.tasks):
        name = question.task_variable(task).name
        frame.loc[frame.index[::4], name] = question.alternatives + 1
    data = data.with_frame(frame)

    result = cj.part_worths(data, "q_cbc")
    assert cj.NONE in set(result.table["term"])
    table = cj.shares(
        data,
        "q_cbc",
        {"Ours": {"brand": 1, "price": 10, "warranty": 1}},
        include_none=True,
    )
    assert set(table["product"]) == {"Ours", "I would buy none of these"}
    assert table["share"].sum() == pytest.approx(100.0, abs=0.2)


def test_answers_that_contradict_the_design_are_counted_not_used():
    question = _question(tasks=4, versions=4)
    data = _fieldwork(question, n=20)
    frame = data.frame.copy()
    frame.loc[frame.index[0], question.task_variable(0).name] = 9  # never offered
    frame.loc[frame.index[1], question.task_variable(1).name] = None
    frame.loc[frame.index[2], "cbc_version"] = None
    read = cj.answers(data.with_frame(frame), "q_cbc")
    assert read.reasons["not an alternative shown"] == 1
    assert read.reasons["not answered"] == 1
    assert read.reasons["no version"] == question.tasks
    assert read.respondents == 19


def test_the_table_carries_its_base_and_names_what_importance_means():
    question = _question(tasks=8, versions=8)
    data = _fieldwork(question, n=120)
    table = data.report.conjoint("q_cbc")
    frame = table.to_frame()
    assert list(frame.columns) == ["Attribute", "Level", "Part-worth", "Importance %"]
    # Every level appears, including each attribute's reference at zero.
    assert len(frame) == sum(len(a.levels) for a in ATTRIBUTES)
    assert (frame.groupby("Attribute")["Part-worth"].min() <= 0).all()
    assert table.stats["Base"] == "120 respondents"
    assert "conditional logit" in table.stats["Method"]
    assert "levels tested" in table.stats["Note"]


def test_the_question_is_found_by_name_or_told_what_exists():
    question = _question(tasks=3, versions=3)
    data = _fieldwork(question, n=5)
    assert cj.question_of(data, "q_cbc") is question
    with pytest.raises(KeyError, match="q_cbc"):
        cj.question_of(data, "nope")
    with pytest.raises(ValueError, match="no questionnaire attached"):
        cj.question_of(SurveyData(frame=data.frame), "q_cbc")
    with pytest.raises(KeyError, match="cbc_version"):
        cj.answers(data.with_frame(data.frame.drop(columns=["cbc_version"])), "q_cbc")


def test_the_exported_file_says_the_same_thing_the_engine_does(tmp_path):
    """As for MaxDiff: fit the same model on the written file, as an outside
    tool would, and check it finds the same part-worths."""

    from siamang.data.choice import ChoiceSets, mnl
    from siamang.io.choice import write_conjoint_choices

    question = _question()
    data = _fieldwork(question, n=200)
    path = write_conjoint_choices(data, "q_cbc", tmp_path / "cbc")
    frame = pd.read_csv(path)

    columns = [c for c in frame.columns if c.startswith("x")]
    chosen = np.zeros(len(frame), dtype=bool)
    for _, block in frame.groupby("ques"):
        chosen[block.index[int(block.iloc[0]["y"]) - 1]] = True
    from_file = mnl(
        ChoiceSets(
            design=frame[columns].to_numpy(float),
            chosen=chosen,
            group=frame["ques"].to_numpy(),
            names=columns,
        ),
        shares=False,
    )
    ours = cj.part_worths(data, "q_cbc").coefficients
    assert np.allclose(ours, from_file.coefficients, atol=1e-4)

    # Every task the same width, and y on the first row of each.
    assert list(frame.groupby("ques").size().unique()) == [question.alternatives]
    assert (frame.groupby("ques")["y"].apply(lambda s: (s != 0).sum()) == 1).all()


def test_the_dictionary_names_the_level_behind_every_column(tmp_path):
    import json

    from siamang.io.choice import write_conjoint_choices

    question = _question(tasks=4, versions=4)
    data = _fieldwork(question, n=20)
    path = write_conjoint_choices(data, "q_cbc", tmp_path / "cbc")
    frame = pd.read_csv(path)
    dictionary = json.loads(path.with_name("cbc.dictionary.json").read_text(encoding="utf-8"))

    assert set(dictionary["columns"]) == set(frame.columns)
    assert dictionary["columns"]["x1"] == "Brand: Globex"
    assert [a["name"] for a in dictionary["attributes"]] == ["brand", "price", "warranty"]
    assert dictionary["attributes"][0]["reference"] == "Acme"
    assert path.with_name("cbc.hb.R").is_file()
