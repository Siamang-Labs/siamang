"""siamang.model.import_surveyjs — a SurveyJS definition as a document."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from siamang.model import DocumentError, from_document, validate_document
from siamang.model.import_surveyjs import import_surveyjs, import_surveyjs_file, looks_like_surveyjs

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "customer_pulse.surveyjs.json"


@pytest.fixture(scope="module")
def result():
    return import_surveyjs_file(FIXTURE)


def _page(document, name):
    return next(p for p in document["pages"] if p["name"] == name)


def _item(document, item_id):
    def walk(items):
        for item in items:
            if item.get("id") == item_id:
                return item
            if isinstance(item.get("items"), list):
                found = walk(item["items"])
                if found:
                    return found
        return None

    for page in document["pages"]:
        found = walk(page.get("items") or [])
        if found:
            return found
    raise KeyError(item_id)


def test_document_is_valid_and_runs_through_the_engine(result):
    validate_document(result.document)
    loaded = from_document(result.document)
    loaded.survey.validate()
    assert result.document["title"] == "Customer Pulse"
    assert result.document["options"] == {
        "language": "en",
        "allow_back": False,
        "show_progress": True,
    }
    assert result.document["ui"] == {"redirect_url": "https://example.org/done"}


def test_pages_bodies_and_the_end_page(result):
    assert [p["name"] for p in result.document["pages"]] == ["intro", "habits", "wrap", "end"]
    intro = _page(result.document, "intro")
    assert intro["title"] == "About you" and "Two quick questions" in intro["body"]
    assert [i["id"] for i in intro["items"]] == ["consent", "age", "region"]
    habits = _page(result.document, "habits")
    assert "<b>habits</b>" in habits["body"]
    assert habits["show_if"] == {
        "type": "expression",
        "op": "=",
        "left": {"type": "var", "name": "consent"},
        "right": 1,
    }
    end = _page(result.document, "end")
    assert end["kind"] == "final" and "Thank you" in end["body"]


def test_question_types_map(result):
    consent = _item(result.document, "consent")
    assert consent["type"] == "SingleChoice" and consent["required"] is True
    assert consent["choices"] == [{"code": 1, "label": "Yes"}, {"code": 0, "label": "No"}]
    age = _item(result.document, "age")
    assert age["type"] == "NumericInput"
    assert result.document["variables"]["age"]["valid_range"] == [16, 99]
    region = _item(result.document, "region")
    assert region["display"] == "dropdown" and region["other_specify"] is True
    assert [c["code"] for c in region["choices"]] == ["North", "South", "cap"]
    screen = _item(result.document, "screen_time")
    assert screen["display"] == "slider" and screen["step"] == 0.5
    assert result.document["variables"]["screen_time"]["valid_range"] == [0, 12]
    satisfaction = _item(result.document, "satisfaction")
    assert satisfaction["display"] == "buttons" and satisfaction["required"] is True
    labels = result.document["variables"]["satisfaction"]["labels"]
    assert labels[0] == {"code": 1, "label": "1 — Not at all"} and labels[-1]["code"] == 5
    apps = _item(result.document, "apps")
    assert apps["type"] == "Matrix" and apps["subquestions"] == ["Social media", "News"]
    assert apps["column_labels"] == ["Never", "Sometimes", "Daily"]
    assert apps["var"] == ["apps_social", "apps_news"]
    comment = _item(result.document, "comment")
    assert comment["multiline"] is True and comment["max_chars"] == 500
    contact = _item(result.document, "contact_email")
    assert contact["type"] == "OpenText" and contact["text"] == "How can we reach you? — Email"
    assert contact["format"] == "email"
    mood = _item(result.document, "mood")
    assert mood["type"] == "Matrix" and mood["column_labels"] == ["1", "2", "3"]
    assert mood["subquestions"] == ["morning", "evening"]
    birthday = _item(result.document, "birthday")
    assert birthday["type"] == "OpenText" and birthday["format"] == "date"
    assert not any("became free text" in w for w in result.warnings)


def test_panels_become_blocks_when_randomized(result):
    habits = _page(result.document, "habits")
    block = next(i for i in habits["items"] if i.get("type") == "Block")
    assert block["randomize"] is True and "id" not in block  # blocks carry no id
    assert [i["id"] for i in block["items"]] == ["priorities", "plan"]
    plan = _item(result.document, "plan")
    assert plan["randomize"] is True and plan["choices"][0] == {"code": 1, "label": "Free"}


def test_checkbox_tested_by_visible_if_is_stored_wide(result):
    devices = _item(result.document, "devices")
    assert devices["mode"] == "wide"
    assert devices["var"] == ["devices_phone", "devices_laptop", "devices_tablet", "devices_none"]
    screen = _item(result.document, "screen_time")
    assert screen["show_if"] == {
        "type": "expression",
        "op": "=",
        "left": {"type": "var", "name": "devices_phone"},
        "right": 1,
    }
    assert any(s.where == "devices" and s.what == "Exclusive answer" for s in result.skipped)


def test_visible_if_expressions_become_show_if(result):
    apps = _item(result.document, "apps")
    cond = apps["show_if"]
    assert (
        cond["op"] == "or" and cond["left"]["right"] == "North" and cond["right"]["right"] == "cap"
    )
    topics = _item(result.document, "topics")
    assert topics["show_if"]["op"] == "or"
    assert topics["show_if"]["left"] == {
        "type": "expression",
        "op": "=",
        "left": {"type": "var", "name": "plan"},
        "right": 1,
    }
    low = _item(result.document, "low_reason")
    assert "show_if" not in low
    assert any(
        s.where == "low_reason" and s.what == "visibleIf" and "notempty" in s.why
        for s in result.skipped
    )


def test_the_rest_is_reported(result):
    reported = {(s.where, s.what) for s in result.skipped}
    assert ("upload", "File upload") in reported
    assert ("sig", "Signature pad") in reported
    assert ("survey", "triggers") in reported and ("survey", "calculatedValues") in reported
    assert "upload" not in result.document["variables"]


def test_bare_elements_and_detection():
    survey = {
        "elements": [
            {"type": "radiogroup", "name": "q1", "title": "Pick", "choices": ["a", "b"]},
        ]
    }
    result = import_surveyjs(json.dumps(survey))
    validate_document(result.document)
    assert [p["name"] for p in result.document["pages"]] == ["page1"]
    assert looks_like_surveyjs(survey)
    assert looks_like_surveyjs({"pages": [{"name": "p", "elements": []}]})
    assert not looks_like_surveyjs({"pages": [{"name": "p", "items": []}]})
    assert not looks_like_surveyjs({"SurveyElements": [], "pages": []})
    with pytest.raises(DocumentError):
        import_surveyjs('{"title": "no pages"}')
    with pytest.raises(DocumentError):
        import_surveyjs("[]")
