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
                        sg.Block(
                            title="B1", items=[sg.SingleChoice("Q1?", var=v1)], randomize=True
                        ),
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


def _texts(*names):
    return [
        sg.OpenText(name.upper(), var=sg.Variable(name, scale="nominal", dtype="str"))
        for name in names
    ]


class TestNestedBlockPayload:
    """A nested block's conditions and shuffle reach the runtime: they used to
    be flattened away, while the model and the simulator honour them."""

    def _page(self, *items):
        route = sg.Variable("route", scale="nominal", labels={1: "A", 2: "B"})
        survey = sg.Questionnaire(
            title="N",
            pages=[
                sg.Page(name="p0", items=[sg.SingleChoice("Route?", var=route)]),
                sg.Page(name="p", items=list(items)),
            ],
        )
        return _page_by_name(compile_react_payload(survey), "p")

    def test_questions_in_nested_blocks_carry_their_conditions(self):
        a, b, c, d = _texts("a", "b", "c", "d")
        route = sg.Variable("route", scale="nominal", labels={1: "A", 2: "B"})
        deep = sg.Block(title="Deep", items=[c], hide_if=route.eq(2))
        inner = sg.Block(title="Inner", items=[b, deep], show_if=route.eq(1))
        (block,) = self._page(sg.Block(title="Outer", items=[a, inner, d]))["blocks"]
        items = {item["id"]: item for item in block["items"]}
        assert list(items) == ["a", "b", "c", "d"]  # every question, in document order
        assert "gates" not in items["a"] and "gates" not in items["d"]
        (inner_gate,) = items["b"]["gates"]
        assert inner_gate["title"] == "Inner" and inner_gate["showIf"]["deps"] == ["route"]
        assert [gate["title"] for gate in items["c"]["gates"]] == ["Inner", "Deep"]
        assert "hideIf" in items["c"]["gates"][1]
        # Nothing shuffles, so there is no layout to deal.
        assert "layout" not in block

    def test_a_shuffle_with_nested_blocks_is_sent_as_a_layout(self):
        a, b, c, d, e = _texts("a", "b", "c", "d", "e")
        inner = sg.Block(items=[b, c], randomize=True)
        kept, mixed = self._page(
            sg.Block(items=[a, inner]),
            sg.Block(items=[d, sg.Block(items=[e])], randomize=True),
        )["blocks"]
        assert kept["layout"] == [0, {"randomize": True, "items": [1, 2]}]
        assert "randomize" not in kept
        assert mixed["randomize"] is True
        assert mixed["layout"] == [0, {"randomize": False, "items": [1]}]
        # A nested block without a condition gates nothing.
        assert all("gates" not in item for item in [*kept["items"], *mixed["items"]])

    def test_a_block_without_nested_blocks_compiles_as_before(self):
        a, b = _texts("a", "b")
        (block,) = self._page(sg.Block(title="B", items=[a, b], randomize=True))["blocks"]
        assert set(block) == {"title", "items", "isBlock", "randomize"}

    def test_a_questionnaire_of_blocks_keeps_each_blocks_condition_and_shuffle(self):
        a, b, c = _texts("a", "b", "c")
        route = sg.Variable("route", scale="nominal", labels={1: "A", 2: "B"})
        survey = sg.Questionnaire(
            title="Blocks",
            blocks=[
                sg.Block(title="One", items=[sg.SingleChoice("Route?", var=route)]),
                sg.Block(title="Two", items=[a, b], show_if=route.eq(1), randomize=True),
                sg.Block(title="Three", items=[c], hide_if=route.eq(2)),
            ],
        )
        one, two, three = compile_react_payload(survey)["PAGES"]
        assert "showIf" not in one and "hideIf" not in one
        assert two["showIf"]["deps"] == ["route"]
        (block,) = two["blocks"]
        assert block["randomize"] is True and [q["id"] for q in block["items"]] == ["a", "b"]
        assert three["hideIf"]["deps"] == ["route"] and "blocks" not in three


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
        # A code of the variable (DEFAULT_NONE_CODE), not a sentinel string.
        assert options[-1]["code"] == sg.core.question.DEFAULT_NONE_CODE
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
                    items=[sg.Matrix("Rate", var=[m1, m2], column_labels=["C1", "C2"], **kwargs)],
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
        for marker in (
            "nextIf",
            "defaultNext",
            "skipTo",
            "__errors__",
            "__pages__",
            "onPageExit",
            "onQuestionShow",
            "onRandomize",
            "siamangNext",
            # Balanced condition assignment: the async script path, the
            # transport call it awaits, and the guard that keeps the late
            # write-back from re-applying keys the script never touched.
            "AsyncFunction",
            "pickQuota",
            "_differs",
            # The optional page hook a host transport can implement.
            "onPage",
            # MaxDiff: the component, the completeness rule that stops one
            # answered task counting as an answered question, and the version
            # draw that ties a respondent to one block of the design.
            "maxdiff",
            "maxDiffRemaining",
            "versionVar",
            # Conjoint: the component and the grid it renders.
            "conjoint",
            "taskVars",
        ):
            assert marker in bundle, f"bundle is stale: missing {marker}"


def test_question_qid_serialized_for_design_mode():
    """Design mode addresses questions by the author-facing id, not the variable."""
    payload = compile_react_payload(_survey_with_routing())
    items = [item for page in payload["PAGES"] for item in page.get("items", [])]
    items += [
        item
        for page in payload["PAGES"]
        for block in page.get("blocks", [])
        for item in block.get("items", [])
    ]
    assert items, "the routing fixture has questions"
    for item in items:
        assert "id" in item
        # qid is present whenever the author gave the question an id.
        if "qid" in item:
            assert isinstance(item["qid"], str) and item["qid"]


class TestMaxDiffPayload:
    """What the runtime is handed for a best–worst question."""

    def _survey(self, **kwargs):
        items = {1: "Price", 2: "Quality", 3: "Speed", 4: "Support", 5: "Range"}
        tasks = kwargs.pop("tasks", 3)
        variables = [
            sg.Variable(f"md_t{t}_{side}", scale="nominal", label=f"t{t} {side}", labels=items)
            for t in range(1, tasks + 1)
            for side in ("best", "worst")
        ]
        variables.append(sg.Variable("md_version", scale="nominal", label="Version"))
        question = sg.MaxDiff(
            "Which matters most?", variables, tasks=tasks, id="q_md", seed=3, **kwargs
        )
        return sg.Questionnaire(title="M", pages=[sg.Page(name="p", items=[question])])

    def test_the_whole_design_travels_with_the_payload(self):
        """The runtime picks a version from the respondent id rather than asking
        the server which one to show — one fewer thing between a respondent and
        their first question, and it works offline in a preview."""

        payload = compile_react_payload(self._survey(per_task=3, versions=4))
        item = _page_by_name(payload, "p")["items"][0]
        assert item["kind"] == "maxdiff"
        assert len(item["versions"]) == 4
        assert all(len(version) == 3 for version in item["versions"])
        assert all(len(task) == 3 for version in item["versions"] for task in version)
        assert all(
            len(set(task)) == 3 for version in item["versions"] for task in version
        ), "an item shown twice in one task has nothing to beat"

    def test_variable_names_travel_so_the_answer_is_one_key_per_variable(self):
        """Without these the component would have to invent names, and the
        answers would arrive under keys the codebook never heard of."""

        payload = compile_react_payload(self._survey(per_task=3, versions=2))
        item = _page_by_name(payload, "p")["items"][0]
        assert item["taskVars"] == [
            ["md_t1_best", "md_t1_worst"],
            ["md_t2_best", "md_t2_worst"],
            ["md_t3_best", "md_t3_worst"],
        ]
        assert item["versionVar"] == "md_version"
        assert [option["label"] for option in item["options"]][:2] == ["Price", "Quality"]
        assert item["bestLabel"] and item["worstLabel"]

    def test_the_same_seed_compiles_the_same_design(self):
        first = compile_react_payload(self._survey(per_task=3, versions=3))
        second = compile_react_payload(self._survey(per_task=3, versions=3))
        assert (
            _page_by_name(first, "p")["items"][0]["versions"]
            == (_page_by_name(second, "p")["items"][0]["versions"])
        )


class TestConjointPayload:
    """What the runtime is handed for a choice task."""

    def _survey(self, **kwargs):
        attributes = [
            sg.Attribute(
                "brand",
                [sg.Option(1, "Acme"), sg.Option(2, "Globex"), sg.Option(3, "Initech")],
                label="Brand",
            ),
            sg.Attribute(
                "price", [sg.Option(10, "£10"), sg.Option(15, "£15")], label="Price per month"
            ),
        ]
        tasks = kwargs.pop("tasks", 4)
        variables = [
            sg.Variable(f"cbc_t{t}", scale="nominal", label=f"Task {t}", labels={1: "1", 2: "2"})
            for t in range(1, tasks + 1)
        ]
        variables.append(sg.Variable("cbc_version", scale="nominal", label="Version"))
        question = sg.Conjoint(
            "Which would you buy?",
            variables,
            attributes=attributes,
            tasks=tasks,
            seed=2,
            id="q_cbc",
            **kwargs,
        )
        return sg.Questionnaire(title="C", pages=[sg.Page(name="p", items=[question])])

    def test_levels_travel_once_and_profiles_reference_them(self):
        """A profile is level codes; the labels ship once per attribute rather
        than once per task, which is the difference between a payload a phone
        downloads and one it does not."""

        payload = compile_react_payload(self._survey(alternatives=3, versions=5))
        item = _page_by_name(payload, "p")["items"][0]
        assert item["kind"] == "conjoint"
        assert [a["label"] for a in item["attributes"]] == ["Brand", "Price per month"]
        assert item["attributes"][0]["levels"] == {"1": "Acme", "2": "Globex", "3": "Initech"}
        assert len(item["versions"]) == 5
        for version in item["versions"]:
            assert len(version) == 4
            for task in version:
                assert len(task) == 3  # alternatives
                assert all(len(profile) == 2 for profile in task)  # one code per attribute

    def test_variable_names_and_the_none_option_travel(self):
        payload = compile_react_payload(self._survey(alternatives=2))
        item = _page_by_name(payload, "p")["items"][0]
        assert item["taskVars"] == ["cbc_t1", "cbc_t2", "cbc_t3", "cbc_t4"]
        assert item["versionVar"] == "cbc_version"
        assert item["noneLabel"] is None
        with_none = compile_react_payload(self._survey(alternatives=2, none_label="Neither"))
        assert _page_by_name(with_none, "p")["items"][0]["noneLabel"] == "Neither"

    def test_the_same_seed_compiles_the_same_design(self):
        first = compile_react_payload(self._survey(alternatives=3))
        second = compile_react_payload(self._survey(alternatives=3))
        assert (
            _page_by_name(first, "p")["items"][0]["versions"]
            == _page_by_name(second, "p")["items"][0]["versions"]
        )
