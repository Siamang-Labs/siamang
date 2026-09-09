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
        "m1", "m2", "rank", "score", "comment", "unused",
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
    assert gender_q["name"] == "gender_q" and gender_q["skip_to"] == "wrap"
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


@pytest.mark.parametrize("path", sorted(DOCUMENTS.glob("*.json")))
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
