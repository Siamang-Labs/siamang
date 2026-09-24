"""What the survey runtime stores, as the compiled payload fixes it.

Every key of the answers object that reaches a backend is a codebook variable
and every value one of its codes: these tests pin the payload fields the
runtime reads to get there. The runtime itself is driven in
``test_runtime_browser.py``.
"""

from __future__ import annotations

import pytest

import siamang as sg
from siamang.core.question import (
    DEFAULT_NONE_CODE,
    DEFAULT_OTHER_CODE,
    na_code,
    other_text_key,
)
from siamang.core.variable import MissingValue
from siamang.frontend.compiler.react import compile_react_payload


def _only_item(survey):
    (page,) = (p for p in compile_react_payload(survey)["PAGES"] if p.get("items"))
    (item,) = page["items"]
    return item


def _matrix(column_labels=None, labels=None, **kwargs):
    rows = [
        sg.Variable("r1", scale="ordinal", labels=dict(labels or {})),
        sg.Variable("r2", scale="ordinal", labels=dict(labels or {})),
    ]
    return sg.Matrix("Rate", var=rows, column_labels=column_labels, **kwargs)


def _survey(*items):
    return sg.Questionnaire(title="T", pages=[sg.Page(name="p", items=list(items))])


# ── Matrix: a column stores its code ─────────────────────────────────────────


class TestMatrixColumnCodes:
    def test_headers_that_name_the_labels_take_their_codes(self):
        """The codebook may list the scale in any order; a header names its code."""

        labels = {5: "Agree", 1: "Disagree", 3: "Neutral"}
        matrix = _matrix(["Disagree", "Neutral", "Agree"], labels)
        assert matrix.columns() == [(1, "Disagree"), (3, "Neutral"), (5, "Agree")]
        item = _only_item(_survey(matrix))
        assert item["columns"] == ["Disagree", "Neutral", "Agree"]
        assert item["columnCodes"] == [1, 3, 5]

    def test_a_zero_to_ten_scale_is_coded_zero_to_ten(self):
        """The ESS trust block: headers "0" … "10" over labels coded 0 … 10."""

        labels = {0: "No trust at all", **{n: str(n) for n in range(1, 10)}, 10: "Complete"}
        matrix = _matrix([str(n) for n in range(11)], labels)
        assert [code for code, _ in matrix.columns()] == list(range(11))

    def test_headers_match_by_position_when_the_texts_differ(self):
        labels = {10: "low", 20: "mid", 30: "high"}
        matrix = _matrix(["L", "M", "H"], labels)
        assert matrix.columns() == [(10, "L"), (20, "M"), (30, "H")]

    def test_without_headers_the_columns_are_the_codebook_in_code_order(self):
        labels = {9: "Refused", 2: "Low", 1: "None"}
        matrix = _matrix(None, labels)
        assert matrix.columns() == [(1, "None"), (2, "Low"), (9, "Refused")]
        item = _only_item(_survey(matrix))
        assert item["columns"] == ["None", "Low", "Refused"]
        assert item["columnCodes"] == [1, 2, 9]

    def test_headers_the_codebook_cannot_place_count_from_one(self):
        """No codebook, or one that neither names nor lines up with the headers:
        1, 2, 3 … as before — the only coding there is to go on."""

        assert _matrix(["A", "B"]).columns() == [(1, "A"), (2, "B")]
        assert _matrix(["A", "B"], {1: "x", 2: "y", 3: "z"}).columns() == [(1, "A"), (2, "B")]

    def test_a_header_named_twice_in_the_codebook_is_placed_by_position(self):
        matrix = _matrix(["Same", "Other"], {7: "Same", 8: "Same"})
        assert matrix.columns() == [(7, "Same"), (8, "Other")]


# ── Wide MultiChoice: one 0/1 variable per choice ────────────────────────────


def _wide(choices=True, **kwargs):
    variables = [
        sg.Variable(name, scale="nominal", label=label, labels={0: "No", 1: "Yes"})
        for name, label in (("b_1", "Acme"), ("b_2", "Globex"), ("b_99", "None"))
    ]
    options = (
        [sg.Option(1, "Acme"), sg.Option(2, "Globex"), sg.Option(99, "None of these")]
        if choices
        else None
    )
    return sg.MultiChoice("Brands?", vars=variables, choices=options, id="b", **kwargs)


class TestWideMultiChoice:
    def test_each_option_is_its_choice_on_its_variable(self):
        item = _only_item(_survey(_wide(exclusive=[99])))
        assert item["id"] == "b"
        assert item["wide"] is True
        assert item["options"] == [
            {"code": 1, "label": "Acme", "var": "b_1"},
            {"code": 2, "label": "Globex", "var": "b_2"},
            {"code": 99, "label": "None of these", "var": "b_99"},
        ]
        # `exclusive` names choice codes, which are now the options' codes.
        assert item["exclusive"] == [99]

    def test_without_choices_an_option_is_its_variable(self):
        item = _only_item(_survey(_wide(choices=False)))
        assert item["options"][0] == {"code": "b_1", "label": "Acme", "var": "b_1"}

    def test_an_array_multichoice_is_not_wide(self):
        var = sg.Variable("m", scale="nominal", labels={1: "A", 2: "B"})
        item = _only_item(_survey(sg.MultiChoice("M?", var=var)))
        assert "wide" not in item
        assert all("var" not in option for option in item["options"])


# ── Other (please specify), None of the above, Not applicable ────────────────

_FRUIT = {1: "Apple", 2: "Pear"}


def _fruit(**kwargs):
    var = sg.Variable("fruit", scale="nominal", labels=kwargs.pop("labels", _FRUIT))
    return sg.SingleChoice("Fruit?", var=var, id="q_fruit", **kwargs)


class TestOtherNoneAndNa:
    def test_other_stores_a_code_and_names_the_key_of_its_text(self):
        item = _only_item(_survey(_fruit(other_specify=True)))
        assert item["otherSpecify"] is True
        assert item["otherCode"] == DEFAULT_OTHER_CODE
        assert item["otherKey"] == "fruit_other"

    def test_metadata_sets_the_other_code(self):
        item = _only_item(_survey(_fruit(other_specify=True, metadata={"other_code": 96})))
        assert item["otherCode"] == 96

    def test_a_multichoice_other_is_keyed_by_its_variable(self):
        var = sg.Variable("snacks", scale="nominal", labels={1: "Chips"})
        item = _only_item(_survey(sg.MultiChoice("S?", var=var, other_specify=True)))
        assert (item["otherCode"], item["otherKey"]) == (DEFAULT_OTHER_CODE, "snacks_other")

    def test_a_wide_multichoice_other_is_keyed_by_the_question(self):
        item = _only_item(_survey(_wide(other_specify=True)))
        assert item["otherKey"] == "b_other" == other_text_key(_wide(other_specify=True))

    def test_none_of_the_above_is_a_code(self):
        item = _only_item(_survey(_fruit(none_of_above=True)))
        assert item["options"][-1] == {
            "code": DEFAULT_NONE_CODE,
            "label": "None of the above",
            "noneOfAbove": True,
        }
        item = _only_item(_survey(_fruit(none_of_above=True, metadata={"none_code": 97})))
        assert item["options"][-1]["code"] == 97

    def test_not_applicable_is_the_codebooks_not_applicable_code(self):
        declared = sg.Variable(
            "sat",
            scale="ordinal",
            labels={1: "1", 2: "2", 3: "3", -1: "Not applicable"},
            missing=(MissingValue(-1, "Not applicable", "not_applicable"),),
        )
        assert na_code(declared) == -1
        item = _only_item(_survey(sg.LikertScale("Sat?", var=declared, points=3, na_option=True)))
        assert item["naCode"] == -1
        # Without a declared code nothing is emitted, and the runtime keeps "na".
        plain = sg.Variable("sat", scale="ordinal")
        item = _only_item(_survey(sg.LikertScale("Sat?", var=plain, points=3, na_option=True)))
        assert "naCode" not in item

    def test_a_matrix_row_takes_its_own_variables_not_applicable_code(self):
        rows = [
            sg.Variable(
                "r1",
                scale="ordinal",
                labels={1: "A", 9: "N/A"},
                missing=(MissingValue(9, "N/A", "not_applicable"),),
            ),
            sg.Variable("r2", scale="ordinal", labels={1: "A"}),
        ]
        item = _only_item(_survey(sg.Matrix("M?", var=rows, column_labels=["A"], na_option=True)))
        assert item["rows"][0]["naCode"] == 9
        assert "naCode" not in item["rows"][1]


class TestAddedCodesValidation:
    def test_the_default_other_code_may_not_be_a_choice_already(self):
        clash = {1: "Apple", DEFAULT_OTHER_CODE: "Kiwi"}
        survey = _survey(_fruit(other_specify=True, labels=clash))
        with pytest.raises(ValueError, match="Set metadata other_code"):
            survey.validate()

    def test_an_explicit_other_code_may_name_the_choice_that_is_other(self):
        labels = {1: "Apple", 2: "Pear", 3: "Something else"}
        survey = _survey(_fruit(other_specify=True, labels=labels, metadata={"other_code": 3}))
        survey.validate()
        item = _only_item(survey)
        assert item["otherCode"] == 3
        assert [o["code"] for o in item["options"]] == [1, 2, 3]

    def test_none_of_the_above_needs_a_code_of_its_own(self):
        survey = _survey(_fruit(none_of_above=True, metadata={"none_code": 2}))
        with pytest.raises(ValueError, match="None of the above"):
            survey.validate()
        survey = _survey(
            _fruit(
                none_of_above=True,
                other_specify=True,
                metadata={"none_code": 5, "other_code": 5},
            )
        )
        with pytest.raises(ValueError, match="None of the above"):
            survey.validate()

    def test_a_code_must_be_a_number_or_a_string(self):
        survey = _survey(_fruit(other_specify=True, metadata={"other_code": [1]}))
        with pytest.raises(ValueError, match="number or a string"):
            survey.validate()

    def test_the_other_text_may_not_land_on_another_answer(self):
        clash = sg.OpenText("Say", var=sg.Variable("fruit_other", scale="nominal"))
        survey = _survey(_fruit(other_specify=True), clash)
        with pytest.raises(ValueError, match="fruit_other"):
            survey.validate()

    def test_the_other_text_is_a_variable_a_condition_may_read(self):
        follow_up = sg.OpenText(
            "Why that?",
            var=sg.Variable("why", scale="nominal"),
            show_if=sg.Expression("!=", sg.VarRef("fruit_other"), ""),
        )
        _survey(_fruit(other_specify=True), follow_up).validate()


class TestAddedCodesLint:
    def _codes(self, survey):
        return {w.code for w in survey.lint()}

    def test_an_unlabelled_other_or_none_code_is_reported(self):
        survey = _survey(_fruit(other_specify=True, none_of_above=True))
        warnings = [w for w in survey.lint() if w.code == "ADDED_CODE_WITHOUT_LABEL"]
        assert len(warnings) == 2
        labelled = {**_FRUIT, DEFAULT_OTHER_CODE: "Other", DEFAULT_NONE_CODE: "None"}
        survey = _survey(_fruit(other_specify=True, none_of_above=True, labels=labelled))
        assert "ADDED_CODE_WITHOUT_LABEL" not in self._codes(survey)

    def test_na_without_a_declared_code_is_reported_by_strict_lint(self):
        plain = sg.Variable("sat", scale="ordinal")
        survey = _survey(sg.LikertScale("Sat?", var=plain, points=3, na_option=True))
        assert "NA_STORED_AS_TEXT" not in self._codes(survey)
        assert "NA_STORED_AS_TEXT" in {w.code for w in survey.lint(level="strict")}
