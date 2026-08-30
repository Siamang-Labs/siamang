"""Documentation-parity features: routing, randomization, choice behaviors,
matrix options, and create_index — the compiler/runtime payload side.

The interactive behavior itself is exercised in the browser; these tests pin
the compiled React payload (what the runtime consumes) and the data-layer API.
"""

from __future__ import annotations

import pandas as pd
import pytest

import siamang as sg
from siamang.core.page import DisqualificationPage
from siamang.frontend.compiler.react import compile_react_payload


def _page_by_name(payload, name):
    return next(p for p in payload["PAGES"] if p["name"] == name)


def _survey_with_routing():
    age = sg.Variable("age", scale="ratio", label="Age")
    ok = sg.Variable("ok", scale="nominal", label="OK", labels={1: "Yes", 2: "No"})
    return sg.Questionnaire(
        title="Routing",
        pages=[
            sg.Page(
                name="screen",
                items=[sg.NumericInput("Age?", var=age, skip_to="dq")],
                next_if=[(age.lt(18), "dq"), ("{age} >= 65", "senior")],
                default_next="main",
            ),
            sg.Page(name="main", items=[sg.SingleChoice("OK?", var=ok)]),
            sg.Page(name="senior", items=[]),
            DisqualificationPage(name="dq", body="Sorry"),
        ],
    )


class TestRoutingPayload:
    def test_next_if_rules_serialized_in_order(self):
        payload = compile_react_payload(_survey_with_routing())
        screen = _page_by_name(payload, "screen")
        rules = screen["nextIf"]
        assert len(rules) == 2
        # Typed expression compiles to {deps, fn}
        assert rules[0]["target"] == "dq"
        assert rules[0]["if"]["deps"] == ["age"]
        assert "18" in rules[0]["if"]["fn"]
        # String condition passes through verbatim for the runtime parser
        assert rules[1] == {"if": "{age} >= 65", "target": "senior"}

    def test_default_next_serialized(self):
        payload = compile_react_payload(_survey_with_routing())
        assert _page_by_name(payload, "screen")["defaultNext"] == "main"

    def test_skip_to_serialized_on_question(self):
        payload = compile_react_payload(_survey_with_routing())
        screen = _page_by_name(payload, "screen")
        assert screen["items"][0]["skipTo"] == "dq"

    def test_pages_without_routing_omit_keys(self):
        payload = compile_react_payload(_survey_with_routing())
        main = _page_by_name(payload, "main")
        assert "nextIf" not in main
        assert "defaultNext" not in main


class TestRandomizationPayload:
    def test_question_randomize_flag(self):
        v = sg.Variable("v", scale="nominal", labels={1: "A", 2: "B"})
        survey = sg.Questionnaire(
            title="R",
            pages=[sg.Page(name="p", items=[sg.SingleChoice("Q?", var=v, randomize=True)])],
        )
        payload = compile_react_payload(survey)
        assert _page_by_name(payload, "p")["items"][0]["randomize"] is True

    def test_block_randomize_and_page_randomize_blocks(self):
        v1 = sg.Variable("v1", scale="nominal", labels={1: "A"})
        v2 = sg.Variable("v2", scale="nominal", labels={1: "A"})
        survey = sg.Questionnaire(
            title="R",
            pages=[
                sg.Page(
                    name="p",
                    items=[
                        sg.Block(title="B1", items=[sg.SingleChoice("Q1?", var=v1)], randomize=True),
                        sg.Block(title="B2", items=[sg.SingleChoice("Q2?", var=v2)]),
                    ],
                    randomize_blocks=True,
                )
            ],
        )
        payload = compile_react_payload(survey)
        page = _page_by_name(payload, "p")
        assert page["randomizeBlocks"] is True
        assert page["blocks"][0]["randomize"] is True
        assert page["blocks"][0]["isBlock"] is True
        assert "randomize" not in page["blocks"][1]


class TestChoicePayload:
    def test_multichoice_exclusive_codes(self):
        v = sg.Variable("v", scale="nominal", labels={1: "A", 2: "B", 99: "None"})
        survey = sg.Questionnaire(
            title="M",
            pages=[sg.Page(name="p", items=[sg.MultiChoice("Q?", var=v, exclusive=[99])])],
        )
        payload = compile_react_payload(survey)
        assert _page_by_name(payload, "p")["items"][0]["exclusive"] == [99]

    def test_singlechoice_none_of_above_appends_option(self):
        v = sg.Variable("v", scale="nominal", labels={1: "A", 2: "B"})
        survey = sg.Questionnaire(
            title="S",
            pages=[sg.Page(name="p", items=[sg.SingleChoice("Q?", var=v, none_of_above=True)])],
        )
        payload = compile_react_payload(survey)
        options = _page_by_name(payload, "p")["items"][0]["options"]
        assert options[-1]["code"] == "__none__"
        assert options[-1]["noneOfAbove"] is True
        assert len(options) == 3


class TestMatrixPayload:
    def _survey(self, **kwargs):
        m1 = sg.Variable("m1", scale="ordinal", label="Var label one")
        m2 = sg.Variable("m2", scale="ordinal", label="Var label two")
        return sg.Questionnaire(
            title="M",
            pages=[
                sg.Page(
                    name="p",
                    items=[
                        sg.Matrix(
                            "Rate", var=[m1, m2], column_labels=["C1", "C2"], **kwargs
                        )
                    ],
                )
            ],
        )

    def test_subquestions_override_row_labels(self):
        payload = compile_react_payload(self._survey(subquestions=["Row A", "Row B"]))
        rows = _page_by_name(payload, "p")["items"][0]["rows"]
        assert [r["label"] for r in rows] == ["Row A", "Row B"]
        assert [r["id"] for r in rows] == ["m1", "m2"]

    def test_variable_labels_used_without_subquestions(self):
        payload = compile_react_payload(self._survey())
        rows = _page_by_name(payload, "p")["items"][0]["rows"]
        assert [r["label"] for r in rows] == ["Var label one", "Var label two"]

    def test_na_option_serialized(self):
        payload = compile_react_payload(self._survey(na_option="N/A"))
        assert _page_by_name(payload, "p")["items"][0]["naOption"] == "N/A"
        payload = compile_react_payload(self._survey(na_option=True))
        assert _page_by_name(payload, "p")["items"][0]["naOption"] == "Not applicable"
        payload = compile_react_payload(self._survey())
        assert "naOption" not in _page_by_name(payload, "p")["items"][0]


class TestCreateIndexSum:
    def _data(self):
        frame = pd.DataFrame({"a": [1, 2, None], "b": [3, 4, 5]})
        variables = sg.VariableMap()
        variables.add(sg.Variable("a", "interval", label="A"))
        variables.add(sg.Variable("b", "interval", label="B"))
        return sg.SurveyData(frame=frame, variables=variables)

    def test_sum_index(self):
        data = self._data().create_index("idx", items=["a", "b"], method="sum")
        assert list(data.frame["idx"]) == [4.0, 6.0, 5.0]
        assert data.variables["idx"].role == "derived"

    def test_mean_still_default(self):
        data = self._data().create_index("idx", items=["a", "b"])
        assert list(data.frame["idx"]) == [2.0, 3.0, 5.0]

    def test_unknown_method_rejected(self):
        with pytest.raises(ValueError, match="mean.*sum|sum.*mean"):
            self._data().create_index("idx", items=["a", "b"], method="median")


class TestRuntimeBundleMarkers:
    """The built bundle must carry the runtime halves of the new features."""

    def test_bundle_contains_feature_code(self):
        from importlib import resources

        bundle = (
            resources.files("siamang.frontend.templates.react")
            .joinpath("dist/bundle.js")
            .read_text(encoding="utf-8")
        )
        for marker in ("nextIf", "defaultNext", "skipTo", "__errors__", "__pages__",
                       "onPageExit", "onQuestionShow", "onRandomize", "siamangNext"):
            assert marker in bundle, f"bundle is stale: missing {marker}"
