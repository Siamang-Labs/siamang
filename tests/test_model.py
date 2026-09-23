"""siamang.model — the questionnaire as a JSON document."""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

import siamang as sg
from siamang.core import (
    Block,
    LikertScale,
    MissingValue,
    MultiChoice,
    NumericInput,
    Page,
    Questionnaire,
    Script,
    Variable,
    validate_options,
)
from siamang.frontend.compiler import compile_questionnaire
from siamang.model import (
    SCHEMA_VERSION,
    DocumentError,
    dumps,
    from_document,
    import_module,
    loads,
    to_document,
    validate_document,
)
from siamang.model.scripts import script_from_document, script_to_document

ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures"
DOCUMENTS = ROOT / "documents"


# ─── helpers ─────────────────────────────────────────────────────────────────


def _load_fixture(name: str):
    path = FIXTURES / name
    spec = importlib.util.spec_from_file_location(f"_fixture_{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _kitchen_sink():
    module = _load_fixture("kitchen_sink_questionnaire.py")
    return module.survey, module.options


def _compiled(survey, options):
    opts = {k: v for k, v in (options or {}).items() if k != "ui"}
    return compile_questionnaire(survey, options=opts).to_dict()


def _assert_round_trip(survey, options=None):
    """py -> doc -> py' -> doc' with doc == doc' and compile(py) == compile(py')."""

    document = to_document(survey, options)
    validate_document(document)
    loaded = from_document(document)
    loaded.survey.validate()
    validate_options(loaded.survey, loaded.options)
    assert to_document(loaded.survey, loaded.options) == document
    assert _compiled(loaded.survey, loaded.options) == _compiled(survey, options)
    # The text form is canonical and survives a JSON round trip unchanged.
    text = dumps(document)
    assert loads(text) == document
    assert dumps(to_document(loaded.survey, loaded.options)) == text
    return document, loaded


# ─── round trips ─────────────────────────────────────────────────────────────


def test_kitchen_sink_round_trip():
    survey, options = _kitchen_sink()
    survey.validate()
    document, loaded = _assert_round_trip(survey, options)

    assert document["schema_version"] == SCHEMA_VERSION
    assert document["deadline"] == "2026-12-31T23:59:00"
    assert loaded.survey.deadline == survey.deadline
    # Variables: order of first use, registry-only ones last; string codes kept.
    assert list(document["variables"]) == [
        "consent", "age", "region", "gender", "owns_a", "owns_b", "trust",
        "m1", "m2", "rank",
        # A MaxDiff's variables in the order it fills them: best and worst for
        # each task, then the version of the design the respondent was shown.
        "md_t1_best", "md_t1_worst", "md_t2_best", "md_t2_worst", "md_version",
        # A conjoint's are lighter: the answer is which alternative was chosen,
        # so one per task, and the version says which products those were.
        "cbc_t1", "cbc_t2", "cbc_version",
        "score", "comment", "unused",
    ]  # fmt: skip
    assert [item["code"] for item in document["variables"]["region"]["labels"]] == [
        "north", "south", "99",
    ]  # fmt: skip
    assert loaded.survey.variables["region"].labels == {
        "north": "North",
        "south": "South",
        "99": "Elsewhere",
    }
    assert document["variables"]["age"]["valid_range"] == [16, None]
    # Missing values are stored in their structured form only.
    assert document["variables"]["gender"]["missing"] == [
        {"code": 99, "label": "Refused", "kind": "refusal"}
    ]
    assert "missing_values" not in document["variables"]["trust"]
    assert loaded.survey.variables["trust"].missing_values == (9,)
    assert loaded.survey.variables["trust"].missing_labels == {9: "Don't know"}
    # Options, quotas and UI travel in their own sections.
    assert document["options"] == {
        "language": "de",
        "description": "Everything at once",
        "completion_text": "Danke",
        "show_progress": False,
        "allow_back": False,
        "one_question_per_page": True,
        "max_responses": 500,
        "metadata": {"wave": 1, "tags": ["a", "b"], "nested": {"k": None}},
    }
    assert document["quotas"] == [
        {"variable": "gender", "target_value": 1, "limit": 100},
        {"variable": "region", "target_value": "north", "limit": 50},
    ]
    assert document["ui"] == {
        "primary_color": "#123456",
        "font_pair": "mixed",
        "show_title": False,
        "institution_name": "Lab",
        "estimated_minutes": 7,
        "custom_css": ".x{}",
        "access_codes": ["a1", "b2"],
    }
    assert loaded.ui == options["ui"]
    assert loaded.quotas == options["quota"]
    # Scripts: factories are recognized, everything else is verbatim.
    assert document["scripts"] == [
        {"type": "randomize_options", "question": "q_region", "seed": "abc"},
        {"type": "randomize_pages"},
        {"type": "timed_question", "question": "q_trust", "seconds": 45},
        {
            "type": "validate_fields_match",
            "field_a": "q_score",
            "field_b": "q_score",
            "message": "Must match.",
        },
        {"type": "validate_fields_match", "field_a": "q_score", "field_b": "q_score"},
        {
            "type": "custom",
            "name": "log_it",
            "trigger": "onAnswer",
            "target": "q_age",
            "code": "console.log(answers);",
            "context": {"level": "debug"},
            "sandbox": False,
        },
        {
            "type": "custom",
            "trigger": "onPageEnter",
            "code": "answers.__ready__ = true;",
            "sandbox": True,
        },
    ]
    assert loaded.survey.scripts == survey.scripts
    # A set in an `in` condition is stored in the order the compiler renders it.
    devices = next(page for page in document["pages"] if page["name"] == "devices")
    ownership = devices["items"][0]
    assert ownership["show_if"]["right"]["left"]["right"] == ["99", "south"]
    # Raw string conditions keep their text.
    about = next(page for page in document["pages"] if page["name"] == "about")
    gender_q = about["items"][2]
    assert gender_q["hide_if"] == {"type": "raw", "text": "{consent} == 2"}
    assert gender_q["name"] == "gender" and gender_q["skip_to"] == "wrap"
    assert about["items"][0]["tag"] == ["screener", "demo"]
    assert about["items"][0]["metadata"] == {"group": "demo", "weight": 1.5}
    assert about["items"][1]["choices"][2]["show_if"] == {"type": "raw", "text": "{age} >= 18"}
    # Every engine object comes back equal, not just the compiled output — the
    # one normalization is that a set operand comes back as a list.
    for original, rebuilt in zip(survey.pages, loaded.survey.pages, strict=True):
        if original.name != "devices":
            assert rebuilt == original
    rebuilt_block = loaded.survey.pages[4].items[0]
    assert rebuilt_block.show_if.right.left.right == ["99", "south"]


@pytest.mark.parametrize(
    "fixture",
    [
        "brand_awareness_questionnaire.py",
        "digital_life_questionnaire.py",
        "kitchen_sink_questionnaire.py",
    ],
)
def test_fixture_modules_round_trip(fixture):
    module = _load_fixture(fixture)
    module.survey.validate()
    document, loaded = _assert_round_trip(module.survey, getattr(module, "options", None))
    assert not [w for w in loaded.survey.lint() if w.severity == "error"]
    result = import_module(FIXTURES / fixture)
    assert result.document == document
    assert result.warnings == []


def test_digital_life_document_details():
    module = _load_fixture("digital_life_questionnaire.py")
    document = to_document(module.survey, module.options)
    assert document["scripts"] == [{"type": "randomize_options", "question": "news_source"}]
    devices = next(page for page in document["pages"] if page["name"] == "devices")
    wide = devices["items"][0]["items"][0]
    assert wide["type"] == "MultiChoice" and wide["mode"] == "wide"
    assert wide["var"] == ["owns_smartphone", "owns_laptop", "owns_tablet", "owns_smartwatch"]
    assert wide["id"] == "multi_owns_smartphone"
    assert devices["randomize_blocks"] is True
    loaded = from_document(document)
    rebuilt = next(
        question
        for question in loaded.survey.all_questions()
        if isinstance(question, MultiChoice) and question.mode == "wide"
    )
    assert [variable.name for variable in rebuilt.var] == wide["var"]


@pytest.mark.parametrize("path", sorted(DOCUMENTS.glob("*.questionnaire.json")))
def test_committed_documents_are_canonical(path):
    text = path.read_text(encoding="utf-8")
    document = loads(text)
    validate_document(document)
    loaded = from_document(document)
    loaded.survey.validate()
    validate_options(loaded.survey, loaded.options)
    assert not [w for w in loaded.survey.lint() if w.severity == "error"]
    assert dumps(to_document(loaded.survey, loaded.options)) == text


def test_layout_is_carried_but_not_interpreted():
    survey, options = _kitchen_sink()
    layout = {"collapsed_pages": ["about"], "logic_map": {"positions": {"intro": [0, 0]}}}
    document = to_document(survey, options, layout=layout)
    validate_document(document)
    assert document["layout"] == layout
    loaded = from_document(document)
    assert loaded.layout == layout
    assert "layout" not in to_document(loaded.survey, loaded.options)


def test_blocks_questionnaire_becomes_pages():
    age = Variable("age", "ratio", label="Age")
    mood = Variable("mood", "ordinal", label="Mood", labels={1: "Low", 2: "High"})
    survey = Questionnaire(
        title="Blocks",
        blocks=[
            Block(title="About you", items=[NumericInput("Age?", age)]),
            Block(title="How you feel", items=[LikertScale("Mood?", mood, points=2)]),
        ],
    )
    warnings: list[str] = []
    document = to_document(survey, on_warning=warnings.append)
    assert warnings == ["Questionnaire uses blocks=; each top-level block became a page."]
    assert [page["name"] for page in document["pages"]] == ["about_you", "how_you_feel"]
    validate_document(document)
    loaded = from_document(document)
    assert _compiled(loaded.survey, {}) == _compiled(survey, {})


def test_unknown_option_keys_are_reported_not_stored():
    survey, _ = _kitchen_sink()
    warnings: list[str] = []
    document = to_document(
        survey, {"runtime": object(), "language": "en"}, on_warning=warnings.append
    )
    assert warnings == ["options['runtime'] is not part of the document format and was dropped."]
    assert document["options"] == {"language": "en"}


# ─── scripts ─────────────────────────────────────────────────────────────────


def test_hand_edited_factory_script_is_custom():
    script = Script.timed_question("q1", seconds=30)
    edited = Script(
        code=script.code + "\n// tweaked",
        trigger=script.trigger,
        name=script.name,
        target=script.target,
    )
    payload = script_to_document(edited)
    assert payload["type"] == "custom" and payload["name"] == "timed_q1"
    assert script_from_document(payload) == edited
    assert script_from_document(script_to_document(script)) == script


def test_assign_condition_round_trips_and_rejects_bad_arms():
    payload = {
        "type": "assign_condition",
        "variable": "condition",
        "arms": [
            {"code": 1, "label": "Control", "weight": 2},
            {"code": 2, "label": "Treatment"},
            {"code": 3, "label": "Treatment B"},
        ],
        "seed": "study26",
    }
    script = script_from_document(payload)
    assert script.trigger == "onInit" and script.name == "assign_condition"
    # Weight 1 is the default and is not written back, so the document a
    # builder saves is the document it reads.
    assert script_to_document(script) == payload

    # An edited factory script degrades to custom rather than claiming to be
    # an assignment it no longer matches.
    edited = Script(
        code=script.code + "\n// tweaked",
        trigger=script.trigger,
        name=script.name,
        context=script.context,
    )
    assert script_to_document(edited)["type"] == "custom"

    for arms, why in [
        ([(1, "Only")], "one arm"),
        ([(1, "A"), (1, "B")], "duplicate codes"),
        ([(1, ""), (2, "B")], "empty label"),
        ([(1, "A", 0), (2, "B")], "zero weight"),
    ]:
        with pytest.raises(ValueError):
            Script.assign_condition("condition", arms), why
    with pytest.raises(ValueError):
        Script.assign_condition("1bad", [(1, "A"), (2, "B")])


def test_assign_condition_draws_the_declared_shares():
    # The arm is drawn in the browser, so the behavior that matters lives in
    # the emitted JavaScript. Check the shape the runtime relies on: the
    # parameters are recoverable from context, and the code only touches
    # `answers[variable]` when it is still unset (a resumed respondent keeps
    # the arm they were already given).
    script = Script.assign_condition("arm", [(1, "A", 3), (2, "B")], seed="s")
    assert script.context == {"variable": "arm", "arms": [[1, "A", 3], [2, "B", 1]], "seed": "s"}
    assert "answers[variable] === undefined" in script.code
    assert "[3, 1]" in script.code and "[1, 2]" in script.code


def test_balanced_assignment_round_trips_and_refuses_a_seed():
    # Balance is what stops one arm completing while another starves: the
    # respondent is sent to the arm furthest behind its quota instead of being
    # drawn independently. It is a different script from the unbalanced one,
    # so the round trip has to carry the flag or the builder would silently
    # turn balancing off on the next save.
    payload = {
        "type": "assign_condition",
        "variable": "condition",
        "arms": [{"code": 1, "label": "Control"}, {"code": 2, "label": "Treatment"}],
        "balance": True,
    }
    script = script_from_document(payload)
    assert script_to_document(script) == payload
    assert script.context["balance"] is True
    # The local draw stays as the fallback and the backend call is awaited
    # after it, so a respondent always has an arm even offline.
    assert "answers[variable] = chosen;" in script.code
    assert "await api.pickQuota(variable, values)" in script.code

    plain = script_from_document({k: v for k, v in payload.items() if k != "balance"})
    assert "await" not in plain.code
    assert script_to_document(plain).get("balance") is None
    assert plain != script

    # A balanced arm depends on who answered first, so it cannot also be
    # reproducible from a seed — saying both would be a lie about one of them.
    with pytest.raises(ValueError, match="seed"):
        Script.assign_condition("condition", [(1, "A"), (2, "B")], seed="s", balance=True)


def test_shorthand_codebook_forms_are_accepted():
    document = {
        "schema_version": SCHEMA_VERSION,
        "title": "Shorthand",
        "variables": {
            "v": {
                "scale": "nominal",
                "labels": {"1": "One", "2": "Two", "9": "Refused"},
                "missing_values": [9],
                "missing_labels": {"9": "Refused"},
            }
        },
        "pages": [
            {
                "name": "p",
                "items": [{"type": "SingleChoice", "id": "q", "text": "Q?", "var": "v"}],
            }
        ],
    }
    validate_document(document)
    loaded = from_document(document)
    variable = loaded.survey.variables["v"]
    assert variable.labels == {1: "One", 2: "Two", 9: "Refused"}
    assert variable.missing == (MissingValue(9, "Refused"),)
    canonical = to_document(loaded.survey, loaded.options)
    assert canonical["variables"]["v"]["labels"][0] == {"code": 1, "label": "One"}
    assert canonical["variables"]["v"]["missing"] == [
        {"code": 9, "label": "Refused", "kind": "system_missing"}
    ]
    # Minimal question objects get the engine defaults.
    question = loaded.survey.all_questions()[0]
    assert question.display == "radio" and question.required is False


# ─── errors ──────────────────────────────────────────────────────────────────


def _minimal(**question):
    return {
        "schema_version": SCHEMA_VERSION,
        "title": "T",
        "variables": {"v": {"scale": "ratio"}},
        "pages": [
            {
                "name": "p",
                "items": [
                    {"type": "NumericInput", "id": "q", "text": "Q?", "var": "v", **question}
                ],
            }
        ],
    }


def test_schema_reports_location():
    with pytest.raises(DocumentError, match=r"pages/0/items/0/step"):
        validate_document(_minimal(step=0))
    with pytest.raises(DocumentError, match=r"pages/0/items/0"):
        validate_document(_minimal(points=5))
    with pytest.raises(DocumentError, match="schema_version"):
        validate_document({**_minimal(), "schema_version": "0.9"})
    with pytest.raises(DocumentError, match="schema_version"):
        from_document({**_minimal(), "schema_version": "0.9"})


def test_from_document_structural_errors():
    with pytest.raises(DocumentError, match="unknown variable 'nope'"):
        from_document(_minimal(var="nope"))
    with pytest.raises(DocumentError, match="NumericInput has no field 'points'"):
        from_document(_minimal(points=5))
    with pytest.raises(DocumentError, match="question 'q'.*step"):
        from_document(_minimal(step=-1))
    broken = _minimal()
    broken["pages"][0]["show_if"] = {"type": "expression", "op": "="}
    with pytest.raises(DocumentError, match="page 'p' show_if"):
        from_document({**broken, "pages": [{**broken["pages"][0], "show_if": {"type": "what"}}]})
    with pytest.raises(DocumentError, match="deadline"):
        from_document({**_minimal(), "deadline": "yesterday"})


def test_to_document_rejects_what_the_format_cannot_hold():
    age = Variable("age", "ratio")
    survey = Questionnaire(
        title="T",
        pages=[Page("p", items=[NumericInput("Age?", age, show_if=lambda answers: True)])],
    )
    with pytest.raises(DocumentError, match="show_if is a function"):
        to_document(survey)
    survey = Questionnaire(
        title="T",
        pages=[
            Page("p", items=[NumericInput("Age?", age, metadata={"when": datetime(2026, 1, 1)})])
        ],
    )
    with pytest.raises(DocumentError, match="metadata.*datetime"):
        to_document(survey)
    with pytest.raises(DocumentError, match="Quota objects"):
        to_document(
            Questionnaire(title="T", pages=[Page("p", items=[NumericInput("Age?", age)])]),
            {"quota": ["x"]},
        )


def test_generated_schema_is_committed():
    """The JSON Schema file must match what scripts/gen_document_schema.py renders."""

    spec = importlib.util.spec_from_file_location(
        "gen_document_schema", ROOT.parent / "scripts" / "gen_document_schema.py"
    )
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    assert generator.OUT.read_text(encoding="utf-8") == generator.render()
    # And it is what the package loads.
    from siamang.model import load_schema

    assert load_schema() == json.loads(generator.render())


def test_public_api_smoke():
    survey, options = _kitchen_sink()
    document = to_document(survey, options)
    assert isinstance(sg.__version__, str)
    loaded = from_document(document)
    schema = loaded.survey.compile(**{k: v for k, v in loaded.options.items() if k != "ui"})
    assert schema.title == "Kitchen sink"


def test_every_question_type_is_named_in_all_three_dispatch_chains():
    """A type forgotten downstream degrades silently instead of raising.

    ``question_to_dict`` falls through to a text box, ``_compile_question`` to
    ``kind="text"`` — which the runtime's dispatcher then renders as *nothing*
    — and ``_simulate_value`` returns None, so ``simulate()`` yields a column of
    nulls. The output cannot tell the three apart from a legitimate answer (a
    single-line ``OpenText`` serializes to exactly the fall-through), so this
    asks the dispatch chains themselves whether they have heard of the type.
    """

    import inspect

    from siamang.core.serialization import question_to_dict
    from siamang.frontend.compiler.react import _compile_question
    from siamang.local_simulator import _simulate_value
    from siamang.model.document import QUESTION_TYPES

    chains = {
        "siamang/core/serialization.py": question_to_dict,
        "siamang/frontend/compiler/react.py": _compile_question,
        "siamang/local_simulator.py": _simulate_value,
    }
    for where, function in chains.items():
        source = inspect.getsource(function)
        forgotten = sorted(name for name in QUESTION_TYPES if name not in source)
        assert not forgotten, f"{where} never mentions {', '.join(forgotten)}"

    # And the fixture carries one of each, so the round-trip, codegen, schema
    # and payload tests all cover every type rather than most of them.
    survey, _options = _kitchen_sink()
    present = {type(question).__name__ for question in survey.all_questions()}
    missing = sorted(set(QUESTION_TYPES) - present)
    assert not missing, f"kitchen_sink_questionnaire.py has no {', '.join(missing)}"


def test_the_kitchen_sink_actually_collects_answers():
    """The fixture has to produce data, not just parse.

    It did not: three defects hid behind a simulation nobody looked at. The
    disqualification page is next in document order after the screener and an
    implicit next does not step over a terminal page, so *everyone* was screened
    out; `age` is declared `(16, None)` and `int(None)` took the run down; and a
    `hide_if` written as a string counted as "condition met", hiding that
    question from every respondent. All three produced columns of nulls, which
    look exactly like a question nobody reached.
    """

    from siamang.local_simulator import simulate_dataframe

    survey, _options = _kitchen_sink()

    # Ignoring routing, every question must yield a value — this is where a type
    # that falls through _simulate_value shows up as a column of nulls.
    everything = simulate_dataframe(survey.all_questions(), n=50, seed=5)
    empty = sorted(c for c in everything.columns if everything[c].isna().all())
    assert not empty, f"questions that simulate as null: {', '.join(empty)}"

    # With routing, the screener splits the sample and the consenters go on.
    frame = survey.simulate(n=300, seed=5).frame
    consented = frame[frame["consent"] == 1]
    assert 0 < len(consented) < len(frame)  # the screener does screen
    assert consented["age"].notna().all()
    assert consented["region"].notna().any()
    # `gender` carries a string hide_if; unreadable here, it must not hide it.
    assert frame["gender"].notna().any()
