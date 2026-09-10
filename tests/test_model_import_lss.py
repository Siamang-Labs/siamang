"""siamang.model.import_lss — a LimeSurvey structure export as a document."""

from __future__ import annotations

from pathlib import Path

import pytest

from siamang.model import DocumentError, from_document, validate_document
from siamang.model.import_lss import import_lss, import_lss_file

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "wellbeing_check.lss"


@pytest.fixture(scope="module")
def result():
    return import_lss_file(FIXTURE)


def _page(document, name):
    return next(p for p in document["pages"] if p["name"] == name)


def _item(document, item_id):
    for page in document["pages"]:
        for item in page.get("items") or []:
            if item.get("id") == item_id:
                return item
    raise KeyError(item_id)


def test_document_is_valid_and_runs_through_the_engine(result):
    validate_document(result.document)
    loaded = from_document(result.document)
    loaded.survey.validate()
    assert result.document["title"] == "Wellbeing Check 2026"
    assert result.document["options"] == {
        "language": "en",
        "allow_back": True,
        "show_progress": True,
    }
    assert result.document["ui"] == {"redirect_url": "https://example.org/thanks"}


def test_groups_welcome_and_end_texts_become_pages(result):
    names = [p["name"] for p in result.document["pages"]]
    assert names == ["welcome", "screener", "digital_habits", "wrap_up", "end"]
    welcome = _page(result.document, "welcome")
    assert welcome["kind"] == "content" and "five minutes" in welcome["body"]
    screener = _page(result.document, "screener")
    assert [i["id"] for i in screener["items"]] == ["consent", "age", "region"]
    assert "A few questions about you" in screener["body"]  # the group description
    end = _page(result.document, "end")
    assert end["kind"] == "final" and "Thanks" in end["body"]


def test_question_types_map(result):
    consent = _item(result.document, "consent")
    assert consent["type"] == "SingleChoice" and consent["required"] is True
    assert [c["code"] for c in consent["choices"]] == ["Y", "N"]
    age = _item(result.document, "age")
    assert age["type"] == "NumericInput" and age["step"] == 1 and "help" not in age
    assert any(s.where == "age" and s.what == "Help text" for s in result.skipped)
    assert result.document["variables"]["age"]["valid_range"] == [16, 99]
    region = _item(result.document, "region")
    assert region["type"] == "SingleChoice" and region["display"] == "dropdown"
    assert [c["label"] for c in region["choices"]] == ["North", "South", "Capital"]
    screen = _item(result.document, "screen_time")
    assert (
        screen["type"] == "NumericInput" and screen["display"] == "slider" and screen["step"] == 0.5
    )
    assert result.document["variables"]["screen_time"]["valid_range"] == [0, 12]
    apps = _item(result.document, "apps")
    assert apps["type"] == "Matrix" and apps["subquestions"] == ["Social media", "News"]
    assert apps["column_labels"] == ["Never", "Sometimes", "Daily"]
    assert apps["var"] == ["apps_sq001", "apps_sq002"]
    assert result.document["variables"]["apps_sq001"]["labels"][2] == {"code": 3, "label": "Daily"}
    satisfaction = _item(result.document, "satisfaction")
    assert satisfaction["display"] == "buttons" and satisfaction["required"] is True
    assert result.document["variables"]["satisfaction"]["scale"] == "ordinal"
    priorities = _item(result.document, "priorities")
    assert priorities["type"] == "Ranking" and priorities["randomize"] is True
    assert [c["label"] for c in priorities["choices"]] == ["Sleep", "Exercise", "Friends & family"]
    comment = _item(result.document, "comment")
    assert (
        comment["type"] == "OpenText"
        and comment["multiline"] is True
        and comment["max_chars"] == 500
    )
    mood = _item(result.document, "mood")
    assert mood["type"] == "Matrix" and mood["column_labels"] == ["1", "2", "3", "4", "5"]
    contact_email = _item(result.document, "contact_sq001")
    assert (
        contact_email["type"] == "OpenText"
        and contact_email["text"] == "How can we reach you? — Email"
    )
    birthday = _item(result.document, "birthday")
    assert birthday["type"] == "OpenText"
    assert any("date question became free text" in w for w in result.warnings)


def test_text_display_lands_in_the_page_body(result):
    habits = _page(result.document, "digital_habits")
    assert "digital habits" in habits["body"]
    assert "intro" not in [i["id"] for i in habits["items"]]


def test_multi_choice_tested_by_relevance_is_stored_wide(result):
    devices = _item(result.document, "devices")
    assert devices["type"] == "MultiChoice" and devices["mode"] == "wide"
    assert devices["var"] == ["devices_sq001", "devices_sq002", "devices_sq003"]
    assert devices["other_specify"] is True
    assert result.document["variables"]["devices_sq001"]["label"] == "Phone"
    screen = _item(result.document, "screen_time")
    assert screen["show_if"] == {
        "type": "expression",
        "op": "=",
        "left": {"type": "var", "name": "devices_sq001"},
        "right": 1,
    }
    assert any(s.what == "Exclusive answer" for s in result.skipped)


def test_relevance_equations_become_show_if(result):
    apps = _item(result.document, "apps")
    cond = apps["show_if"]
    assert cond["op"] == "or"
    assert cond["left"] == {
        "type": "expression",
        "op": "=",
        "left": {"type": "var", "name": "region"},
        "right": "A1",
    }
    assert cond["right"]["right"] == "A3"
    # a group relevance becomes the page's show_if
    habits = _page(result.document, "digital_habits")
    assert habits["show_if"] == {
        "type": "expression",
        "op": "=",
        "left": {"type": "var", "name": "consent"},
        "right": "Y",
    }
    # a function in the expression: the question is shown always and reported
    low = _item(result.document, "low_reason")
    assert "show_if" not in low
    assert any(
        s.where == "low_reason" and s.what == "Relevance" and "is_empty" in s.why
        for s in result.skipped
    )


def test_legacy_conditions_apply_when_there_is_no_relevance_equation(result):
    legacy = _item(result.document, "legacy")
    assert legacy["show_if"] == {
        "type": "expression",
        "op": "=",
        "left": {"type": "var", "name": "consent"},
        "right": "Y",
    }


def test_the_rest_is_reported(result):
    reported = {(s.where, s.what) for s in result.skipped}
    assert ("calc", "Equation") in reported
    assert ("upload", "File upload") in reported
    assert ("survey", "Quotas") in reported
    assert ("legacy", "Validation regex") in reported
    assert ("Wrap up", "Group randomization") in reported
    assert "calc" not in result.document["variables"]
    assert not any(
        i["id"] in {"calc", "upload"}
        for p in result.document["pages"]
        for i in p.get("items") or []
    )


def test_a_lime_survey_3_export_with_inline_texts_reads_too():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<document>
 <LimeSurveyDocType>Survey</LimeSurveyDocType>
 <languages><language>de</language></languages>
 <answers><rows>
  <row><qid>2</qid><code><![CDATA[1]]></code><answer><![CDATA[Ja]]></answer><sortorder>1</sortorder><language><![CDATA[de]]></language><scale_id>0</scale_id></row>
  <row><qid>2</qid><code><![CDATA[2]]></code><answer><![CDATA[Nein]]></answer><sortorder>2</sortorder><language><![CDATA[de]]></language><scale_id>0</scale_id></row>
 </rows></answers>
 <groups><rows>
  <row><gid>1</gid><sid>9</sid><group_name><![CDATA[Fragen]]></group_name><group_order>0</group_order><description/><language><![CDATA[de]]></language><grelevance/></row>
 </rows></groups>
 <questions><rows>
  <row><qid>2</qid><parent_qid>0</parent_qid><sid>9</sid><gid>1</gid><type><![CDATA[L]]></type><title><![CDATA[q1]]></title><question><![CDATA[Alles klar?]]></question><other><![CDATA[N]]></other><mandatory><![CDATA[N]]></mandatory><question_order>1</question_order><language><![CDATA[de]]></language><scale_id>0</scale_id><relevance><![CDATA[1]]></relevance></row>
 </rows></questions>
 <surveys><rows><row><sid>9</sid><language><![CDATA[de]]></language><format><![CDATA[S]]></format><allowprev><![CDATA[N]]></allowprev><showprogress><![CDATA[N]]></showprogress></row></rows></surveys>
 <surveys_languagesettings><rows><row><surveyls_survey_id>9</surveyls_survey_id><surveyls_language><![CDATA[de]]></surveyls_language><surveyls_title><![CDATA[Kurz]]></surveyls_title></row></rows></surveys_languagesettings>
</document>"""
    result = import_lss(xml)
    validate_document(result.document)
    assert result.document["title"] == "Kurz"
    assert result.document["options"] == {
        "language": "de",
        "allow_back": False,
        "show_progress": False,
    }
    q1 = _item(result.document, "q1")
    assert q1["choices"] == [{"code": 1, "label": "Ja"}, {"code": 2, "label": "Nein"}]
    assert [p["name"] for p in result.document["pages"]] == ["fragen"]


def test_not_a_lime_survey_file_is_refused():
    with pytest.raises(DocumentError):
        import_lss("<document><LimeSurveyDocType>Responses</LimeSurveyDocType></document>")
    with pytest.raises(DocumentError):
        import_lss("not xml at all")
    with pytest.raises(DocumentError):
        import_lss('{"SurveyEntry": {}}')
