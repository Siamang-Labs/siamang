"""Multiple-choice answers: lists of codes, and everything that reads them.

The rule under test throughout is that the base is respondents, not answers:
shares are of the people who answered the question, so they sum above 100 %,
and somebody who answered nothing is out of the base rather than counted as a
respondent who rejected every option.
"""

from __future__ import annotations

import pandas as pd
import pytest

import siamang as sg
from siamang.codegen.questionnaire import generate_questionnaire
from siamang.core import Variable, VariableMap
from siamang.core.expression import Expression, VarRef
from siamang.data import SurveyData, multi, weights
from siamang.frontend.compiler.react import compile_react_payload
from siamang.model.parse_python import parse_source

# ─── fixtures ────────────────────────────────────────────────────────────────


def _frame() -> pd.DataFrame:
    """Six respondents; two answered nothing, in the two ways that happens."""

    return pd.DataFrame(
        {
            "reasons": [[1, 3], [2], [1, 2, 3], [3], [], None],
            "region": [1, 1, 2, 2, 1, 2],
            "spend": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0],
            "w": [1.0, 1.0, 2.0, 2.0, 1.0, 1.0],
        }
    )


def _data() -> SurveyData:
    variables = VariableMap()
    variables.add(
        Variable(
            "reasons",
            "nominal",
            label="Reasons to buy",
            labels={1: "Price", 2: "Quality", 3: "Habit"},
        )
    )
    variables.add(Variable("region", "nominal", label="Region", labels={1: "North", 2: "South"}))
    variables.add(Variable("spend", "ratio", label="Monthly spend"))
    return SurveyData(frame=_frame(), variables=variables)


# ─── primitives ──────────────────────────────────────────────────────────────


def test_is_multi_reads_the_data_not_the_codebook():
    frame = _frame()
    assert multi.is_multi(frame["reasons"])
    assert not multi.is_multi(frame["region"])
    # After exploding, the same question is no longer multi — which is the point:
    # an analysis should not have to be told which shape it is looking at.
    assert not multi.is_multi(multi.explode(frame["reasons"])["1"])


def test_an_empty_answer_is_not_a_respondent():
    series = _frame()["reasons"]
    assert list(multi.responded(series)) == [True, True, True, True, False, False]
    assert multi.base_size(series) == 4
    assert multi.base_size(series, weight=_frame()["w"]) == 6.0  # 1 + 1 + 2 + 2


def test_reach_finds_people_who_chose_a_code_among_others():
    series = _frame()["reasons"]
    # The comparison a plain frame gets wrong: [1, 3] == 1 is False.
    assert list(series == 1) == [False] * 6
    assert list(multi.reach(series, 1)) == [True, False, True, False, False, False]


def test_codes_in_is_sorted_and_stable():
    assert multi.codes_in(_frame()["reasons"]) == [1, 2, 3]
    assert multi.codes_in(pd.Series([["b"], ["a", "b"]])) == ["a", "b"]


# ─── frequencies and crosstab ────────────────────────────────────────────────


def test_frequencies_are_of_respondents_and_may_sum_above_100():
    out = multi.frequencies(_frame(), "reasons", labels={1: "Price", 2: "Quality", 3: "Habit"})
    assert out.base == 4 and out.answers == 7
    assert list(out["count"]) == [2, 2, 3]
    assert list(out["percent"]) == [50.0, 50.0, 75.0]
    assert sum(out["percent"]) > 100  # the property of the question, not a bug
    assert sum(out["percent_answers"]) == pytest.approx(100.0, abs=0.2)
    assert list(out["label"]) == ["Price", "Quality", "Habit"]


def test_frequencies_can_be_weighted_and_can_name_codes_nobody_chose():
    out = multi.frequencies(_frame(), "reasons", weight="w", codes=[1, 2, 3, 9])
    assert out.base == 6  # weighted respondents
    assert list(out["count"]) == [3, 3, 5, 0]
    assert list(out["percent"]) == [50.0, 50.0, 83.3, 0.0]


def test_frequencies_rejects_unknown_columns():
    with pytest.raises(KeyError, match="nope"):
        multi.frequencies(_frame(), "nope")


def test_crosstab_percentages_are_of_each_groups_own_base():
    out = multi.crosstab(_frame(), "reasons", "region")
    # North: respondents 0 and 1 answered (2 is blank); South: 2 and 3.
    assert out.base == {1: 2, 2: 2}
    habit = out[out["value"] == 3].iloc[0]
    assert habit["1"] == 50.0 and habit["2"] == 100.0


# ─── explode ─────────────────────────────────────────────────────────────────


def test_explode_gives_missing_not_zero_to_non_respondents():
    out = multi.explode(_frame()["reasons"], prefix="r_")
    assert list(out.columns) == ["r_1", "r_2", "r_3"]
    assert list(out["r_1"].fillna(-1)) == [1, 0, 1, 0, -1, -1]
    # Column sums match the reach counts exactly, so a base computed downstream
    # is the same base the frequency table reported.
    assert out.sum().tolist() == [2, 2, 3]


def test_explode_multi_registers_labeled_variables_in_codebook_order():
    out = _data().explode_multi("reasons")
    assert [c for c in out.frame.columns if c.startswith("reasons_")] == [
        "reasons_1",
        "reasons_2",
        "reasons_3",
    ]
    assert out.variables["reasons_2"].label == "Reasons to buy: Quality"
    assert out.variables["reasons_2"].role == "derived"
    assert out.variables["reasons_2"].labels == {0: "No", 1: "Yes"}
    assert "reasons" in out.frame.columns  # the list column stays by default
    assert out.variables["region"].label == "Region"  # and so does everything else


def test_explode_multi_can_drop_the_source_and_take_a_prefix():
    out = _data().explode_multi("reasons", prefix="why_", drop=True)
    assert "reasons" not in out.frame.columns and "reasons" not in out.variables
    assert out.variables["why_1"].label == "Reasons to buy: Price"


def test_explode_multi_keeps_codes_the_codebook_never_heard_of():
    data = _data()
    frame = data.frame.copy()
    # An "other, specify" code that arrived in the field after the codebook froze.
    frame["reasons"] = [[1, 77], *list(frame["reasons"])[1:]]
    out = data.with_frame(frame).explode_multi("reasons")
    assert "reasons_77" in out.frame.columns
    assert out.variables["reasons_77"].label == "Reasons to buy: 77"


def test_explode_multi_refuses_a_column_it_cannot_find():
    with pytest.raises(ValueError, match="not found"):
        _data().explode_multi("nope")


# ─── guards: the places that used to fail silently or obscurely ──────────────


def test_an_index_over_a_multi_column_says_what_to_do_instead():
    with pytest.raises(TypeError, match="prepare.explode"):
        _data().create_index("n", items=["reasons", "spend"])
    with pytest.raises(TypeError, match="prepare.explode"):
        _data().scale_alpha(["reasons", "spend"])


def test_weighting_a_multi_column_says_what_to_do_instead():
    frame = _frame()
    with pytest.raises(TypeError, match="prepare.explode"):
        weights.cell_weights(frame, "reasons", {1: 0.5, 2: 0.5})
    with pytest.raises(TypeError, match="prepare.explode"):
        weights.rake_weights(frame, {"reasons": {1: 0.5, 2: 0.5}})


def test_the_indicators_are_what_the_guards_promise():
    """The advice in the error message has to actually work."""

    exploded = _data().explode_multi("reasons")
    weighted = weights.cell_weights(exploded.frame, "reasons_1", {0: 0.5, 1: 0.5})
    assert float(weighted.mean()) == pytest.approx(1.0)
    index = exploded.create_index(
        "n_reasons", items=["reasons_1", "reasons_2", "reasons_3"], method="sum"
    )
    assert list(index.frame["n_reasons"].fillna(-1)) == [2, 1, 3, 1, -1, -1]


# ─── the `contains` operator ─────────────────────────────────────────────────


def test_contains_matches_a_code_inside_a_list_answer():
    chose = Expression("contains", VarRef("reasons"), 3)
    assert chose.evaluate({"reasons": [1, 3]}) is True
    assert chose.evaluate({"reasons": [2]}) is False
    # A single-answer variable still compares as equality, so the same condition
    # keeps working if the question is later stored one code per row.
    assert chose.evaluate({"reasons": 3}) is True
    missed = Expression("not contains", VarRef("reasons"), 3)
    assert missed.evaluate({"reasons": [1, 2]}) is True


def test_contains_survives_the_document_round_trip():
    variable = Variable("reasons", "nominal", labels={1: "Price", 2: "Quality", 3: "Habit"})
    condition = sg.Variable.contains(variable, 3)
    assert condition.to_dict()["op"] == "contains"
    assert Expression.from_dict(condition.to_dict()).evaluate({"reasons": [3]}) is True


def test_contains_survives_generated_python_read_back_without_execution():
    """The operator has to make the whole round trip, not just the document.

    A condition that serializes but does not regenerate is worse than one that
    never existed: it silently disappears from a downloaded questionnaire.
    """

    source = """
import siamang as sg
reasons = sg.Variable("reasons", scale="nominal", labels={1: "Price", 2: "Habit"})
more = sg.Variable("more", scale="nominal", label="More")
q_reasons = sg.MultiChoice("Why?", var=reasons, id="q_reasons", mode="array")
q_more = sg.OpenText("Tell us more", var=more, id="q_more",
                     show_if=reasons.contains(1), hide_if=reasons.notcontains(2))
p1 = sg.Page(name="p1", items=[q_reasons])
p2 = sg.Page(name="p2", items=[q_more])
survey = sg.Questionnaire(title="Multi", pages=[p1, p2])
"""
    document = parse_source(source).document
    question = document["pages"][1]["items"][0]
    assert question["show_if"]["op"] == "contains"
    assert question["hide_if"]["op"] == "not contains"

    regenerated = parse_source(generate_questionnaire(document, format=False))
    assert regenerated.dropped == []
    assert regenerated.document == document


def test_contains_compiles_to_javascript_rather_than_the_legacy_evaluator():
    """The browser has to agree with pandas about who sees the follow-up.

    An operator the compiler does not know falls back to the pre-compiled AST
    payload, whose evaluator returns null for anything it has not heard of — so
    an uncompiled `contains` would hide the question from everyone, quietly.
    """

    reasons = sg.Variable("reasons", scale="nominal", labels={1: "Price", 2: "Habit"})
    more = sg.Variable("more", scale="nominal", label="More")
    survey = sg.Questionnaire(
        title="Multi",
        pages=[
            sg.Page(name="p", items=[sg.MultiChoice("Why?", var=reasons, mode="array")]),
            sg.Page(name="q", items=[sg.OpenText("More?", var=more, show_if=reasons.contains(1))]),
        ],
    )
    show_if = compile_react_payload(survey)["PAGES"][1]["items"][0]["showIf"]
    assert set(show_if) == {"deps", "fn"}  # compiled, not the legacy AST
    assert show_if["deps"] == ["reasons"]
    assert show_if["fn"] == (
        '(Array.isArray(a["reasons"])?a["reasons"].includes(1):a["reasons"]===1)'
    )


def test_a_stale_code_in_a_contains_condition_is_linted():
    """The classic authoring mistake, and the one place it hides best.

    An option list is reworked and the rule pointing at it is not, so the
    branch is taken by nobody for the whole of fieldwork. `=` has been linted
    for this all along; a screener on a multiple-choice question is exactly
    where the silence costs most.
    """

    reasons = sg.Variable("reasons", scale="nominal", labels={1: "Price", 2: "Habit"})
    more = sg.Variable("more", scale="nominal", label="More")

    def survey(code: int) -> sg.Questionnaire:
        return sg.Questionnaire(
            title="M",
            pages=[
                sg.Page(name="p", items=[sg.MultiChoice("Why?", var=reasons, mode="array")]),
                sg.Page(
                    name="q",
                    items=[sg.OpenText("More?", var=more, show_if=reasons.contains(code))],
                ),
            ],
        )

    assert survey(1).lint() == []
    [warning] = survey(9).lint()
    assert warning.code == "UNKNOWN_CONDITION_VALUE" and "9" in warning.message


def test_filtering_a_flow_on_contains_keeps_the_right_people():
    condition = Expression("contains", VarRef("reasons"), 1)
    kept = _data().filter(condition)
    assert len(kept.frame) == 2


# ─── tables ──────────────────────────────────────────────────────────────────


def test_freq_table_shows_the_base_and_no_cumulative_column():
    table = _data().report.freq("reasons").to_frame()
    assert list(table.columns) == ["Value", "Label", "N", "%"]
    assert list(table["Label"]) == [
        "Price",
        "Quality",
        "Habit",
        "Base (respondents answering)",
    ]
    assert list(table["%"])[:3] == [50.0, 50.0, 75.0]
    stats = _data().report.freq("reasons").stats
    assert stats["Base"] == "4 respondents" and "multiple answers" in stats["Note"]


def test_freq_table_of_a_single_answer_question_is_unchanged():
    table = _data().report.freq("region").to_frame()
    assert "Cumulative %" in table.columns
    assert list(table["Label"])[-1] == "Total"


def test_crosstab_of_a_multi_row_reports_bases_and_no_chi_square():
    table = _data().report.crosstab("reasons", "region")
    frame = table.to_frame()
    assert list(frame["Reasons to buy"])[-1] == "Base (respondents answering)"
    assert "χ²" not in table.stats and "p" not in table.stats
    assert "overlap" in table.stats["Note"]


def test_means_by_a_multi_group_overlap_on_purpose():
    table = _data().report.means("spend", by="reasons")
    frame = table.to_frame()
    assert list(frame["N"]) == [2, 2, 3]  # 7 memberships from 4 respondents
    assert frame.loc[0, "Mean"] == pytest.approx(20.0)  # rows 0 and 2: 10 and 30
    assert "no significance test" in table.stats["Note"]


def test_proportion_ci_counts_people_who_chose_among_others():
    out = _data().analysis.proportion_ci("reasons", 3)
    assert out["n"] == 4.0
    assert out["p"] == pytest.approx(0.75)
