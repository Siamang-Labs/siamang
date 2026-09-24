"""siamang.model.import_qsf — a Qualtrics export as a questionnaire document."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from siamang.codegen.questionnaire import generate_questionnaire
from siamang.model import DocumentError, from_document, validate_document
from siamang.model.import_qsf import import_qsf, import_qsf_file
from siamang.model.parse_python import parse_source

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "brand_pulse.qsf"


@pytest.fixture(scope="module")
def result():
    return import_qsf_file(FIXTURE)


def _items(document, page_name):
    page = next(p for p in document["pages"] if p["name"] == page_name)
    items = page.get("items") or []
    # a randomized block wraps the page's questions
    if len(items) == 1 and items[0].get("type") == "Block":
        return items[0]["items"]
    return items


def test_document_is_valid_and_runs_through_the_engine(result):
    validate_document(result.document)
    loaded = from_document(result.document)
    loaded.survey.validate()
    assert result.document["title"] == "Brand Pulse 2026"
    assert result.document["options"] == {
        "language": "en",
        "allow_back": True,
        "show_progress": True,
    }


def test_blocks_page_breaks_and_flow_order_become_pages(result):
    names = [p["name"] for p in result.document["pages"]]
    assert names == ["screener", "screener_2", "screen_out", "brand_usage", "attitudes", "wrap_up"]
    screener = result.document["pages"][0]
    assert [i["id"] for i in screener["items"]] == ["consent", "age"]
    assert [i["id"] for i in result.document["pages"][1]["items"]] == ["region"]
    # the trash block and the block outside the flow are not pages
    assert not any("old" in n or "trash" in n for n in names)
    assert any(s.what == "Block" and "unused" in s.why for s in result.skipped)


def test_branch_to_end_of_survey_is_a_disqualification_page(result):
    page = result.document["pages"][2]
    assert page["kind"] == "disqualification"
    cond = page["show_if"]
    assert cond["op"] == "or"
    assert cond["left"] == {
        "type": "expression",
        "op": "=",
        "left": {"type": "var", "name": "consent"},
        "right": 2,
    }
    assert cond["right"] == {
        "type": "expression",
        "op": "<",
        "left": {"type": "var", "name": "age"},
        "right": 18,
    }


def test_question_types_map_with_recodes_other_and_exclusive(result):
    doc = result.document
    consent, age = _items(doc, "screener")
    assert consent["type"] == "SingleChoice" and consent["required"] is True
    assert consent["choices"] == [{"code": 1, "label": "Yes, I agree"}, {"code": 2, "label": "No"}]
    assert consent["text"] == "Do you agree to take part in this short study?"
    assert age["type"] == "NumericInput" and doc["variables"]["age"]["valid_range"] == [16, 99]

    (region,) = _items(doc, "screener_2")
    assert region["display"] == "dropdown" and region["other_specify"] is True
    assert [c["code"] for c in region["choices"]] == [1, 2, 3, 99]
    # The text-entry choice (recode 99) is the Other option, not a second one.
    assert region["metadata"] == {"other_code": 99}

    brand = _items(doc, "brand_usage")
    by_id = {i["id"]: i for i in brand}
    # its choices are tested by logic, so it is stored wide (one yes/no per choice)
    assert by_id["aware"]["type"] == "MultiChoice" and by_id["aware"]["mode"] == "wide"
    assert by_id["aware"]["var"] == ["aware_1", "aware_2", "aware_3", "aware_9"]
    assert doc["variables"]["aware_9"] == {
        "scale": "nominal",
        "label": "None of these",
        "labels": [{"code": 0, "label": "No"}, {"code": 1, "label": "Yes"}],
    }
    # the choices stay beside the variables (choice i on variable i), so the
    # exclusive "None of these" is kept
    assert by_id["aware"]["randomize"] is True and by_id["aware"]["exclusive"] == [9]
    assert [c["code"] for c in by_id["aware"]["choices"]] == [1, 2, 3, 9]
    assert not any(s.what == "Exclusive answer" for s in result.skipped)
    assert by_id["trust"]["type"] == "Matrix"
    assert by_id["trust"]["var"] == ["trust_acme", "trust_globex"]
    assert by_id["trust"]["column_labels"] == ["Not at all", "A little", "Somewhat", "A lot"]
    assert doc["variables"]["trust_acme"]["labels"][3] == {"code": 4, "label": "A lot"}
    assert "points" not in by_id  # constant sum is reported, not invented
    # descriptive text went to the page body; the block's randomization wraps the questions
    page = next(p for p in doc["pages"] if p["name"] == "brand_usage")
    assert "About the brands" in page["body"]
    assert page["items"][0]["type"] == "Block" and page["items"][0]["randomize"] is True

    attitudes = {i["id"]: i for i in _items(doc, "attitudes")}
    assert attitudes["nps"]["display"] == "buttons" and len(attitudes["nps"]["choices"]) == 11
    assert attitudes["happy_price"]["display"] == "slider" and attitudes["happy_price"]["step"] == 1
    assert doc["variables"]["happy_service"]["valid_range"] == [0, 10]
    assert attitudes["rank"]["type"] == "Ranking"
    assert attitudes["contact_first_name"]["type"] == "OpenText"
    assert attitudes["contact_email"]["var"] == "contact_email"

    wrap = {i["id"]: i for i in _items(doc, "wrap_up")}
    assert wrap["comments"]["multiline"] is True and wrap["comments"]["max_chars"] == 500


def test_display_logic_becomes_show_if(result):
    doc = result.document
    trust = {i["id"]: i for i in _items(doc, "brand_usage")}["trust"]
    selected = {
        "type": "expression",
        "op": "=",
        "left": {"type": "var", "name": "aware_1"},
        "right": 1,
    }
    none = {"type": "expression", "op": "=", "left": {"type": "var", "name": "aware_9"}, "right": 1}
    assert trust["show_if"] == {
        "type": "expression",
        "op": "and",
        "left": selected,
        "right": {"type": "expression", "op": "not", "left": none},
    }
    nps = {i["id"]: i for i in _items(doc, "attitudes")}["nps"]
    assert nps["show_if"]["op"] == "or"
    assert nps["show_if"]["left"] == {
        "type": "expression",
        "op": "=",
        "left": {"type": "var", "name": "trust_acme"},
        "right": 4,
    }
    assert nps["show_if"]["right"]["op"] == ">=" and nps["show_if"]["right"]["right"] == 65
    # logic on embedded data cannot be expressed: the question is shown, the loss is listed
    recontact = {i["id"]: i for i in _items(doc, "wrap_up")}["recontact"]
    assert "show_if" not in recontact
    assert any("EmbeddedField" in s.what for s in result.skipped)


def test_everything_lost_is_listed(result):
    text = "\n".join(str(s) for s in result.skipped)
    assert "points: Constant sum" in text
    assert "timing: Timing" in text
    assert "Embedded data (source, panel_id)" in text
    assert "Quota element" in text
    assert "Old block: Block" in text
    assert any("Block randomizer" in w for w in result.warnings)


def test_imported_document_survives_codegen_and_static_read(result):
    code = generate_questionnaire(result.document, format=False)
    again = parse_source(code)
    assert again.dropped == []
    # the static reader fills in engine defaults; the surveys are the same
    assert from_document(again.document).survey == from_document(result.document).survey


def test_rejects_what_is_not_a_qsf():
    with pytest.raises(DocumentError, match="Not valid JSON"):
        import_qsf("{")
    with pytest.raises(DocumentError, match="no SurveyElements"):
        import_qsf({"SurveyEntry": {}})
    with pytest.raises(DocumentError, match="no questions or blocks"):
        import_qsf(json.dumps({"SurveyEntry": {}, "SurveyElements": []}))


def test_terminal_pages_have_a_body_and_unasked_variables_are_pruned(result):
    screen_out = result.document["pages"][2]
    assert screen_out["body"].startswith("<p>Thank you")
    assert "old" not in result.document["variables"]
    assert "trashed" not in result.document["variables"]
    survey = from_document(result.document).survey
    assert [w.code for w in survey.lint(level="strict")] == []


def test_an_imported_wide_question_runs_with_its_choice_codes(result):
    """The runtime pairs choice i with variable i, so "None of these" is
    exclusive by its code and the region's text-entry choice is its Other."""

    from siamang.frontend.compiler.react import compile_react_payload
    from siamang.model import from_document

    loaded = from_document(result.document)
    items = {
        item.get("qid"): item
        for page in compile_react_payload(loaded.survey)["PAGES"]
        for block in [page, *page.get("blocks", [])]
        for item in block.get("items", [])
    }
    aware = items["aware"]
    assert aware["wide"] is True and aware["exclusive"] == [9]
    assert [(o["code"], o["var"]) for o in aware["options"]][-1] == (9, "aware_9")
    region = next(item for item in items.values() if item.get("otherSpecify"))
    assert region["otherCode"] == 99 and region["options"][-1]["code"] == 99
