"""siamang.model.parse_python — questionnaire files read without execution."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from siamang.codegen.questionnaire import generate_questionnaire
from siamang.model import DocumentError, import_module
from siamang.model.parse_python import parse_file, parse_source

ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures"
DOCUMENTS = ROOT / "documents"


@pytest.mark.parametrize(
    "fixture",
    ["brand_awareness_questionnaire.py", "digital_life_questionnaire.py"],
)
def test_static_read_matches_execution_for_fixtures(fixture):
    """The hand-written fixtures stay in the declarative subset: reading them
    without running them gives the same document as running them."""
    executed = import_module(FIXTURES / fixture)
    static = parse_file(FIXTURES / fixture)
    assert static.document == executed.document
    assert static.dropped == []


def test_programmatic_fixture_is_refused_with_the_reason():
    """kitchen_sink builds its survey inside a function: that is exactly what
    the static reader will not run, and the error says where."""
    with pytest.raises(DocumentError, match="functiondef statement") as exc:
        parse_file(FIXTURES / "kitchen_sink_questionnaire.py")
    assert "line 33" in str(exc.value)


@pytest.mark.parametrize("path", sorted(DOCUMENTS.glob("*.questionnaire.json")))
def test_generated_code_round_trips_without_execution(path):
    """codegen(document) → static read → the same document, nothing dropped."""
    document = json.loads(path.read_text(encoding="utf-8"))
    code = generate_questionnaire(document, format=False)
    result = parse_source(code)
    assert result.dropped == []
    assert result.document == document


def test_kitchen_sink_generated_code_round_trips():
    document = import_module(FIXTURES / "kitchen_sink_questionnaire.py").document
    result = parse_source(generate_questionnaire(document, format=False))
    assert result.dropped == []
    assert result.document == document


def test_unsupported_constructs_are_reported_with_lines_not_run():
    source = """
import os
import siamang as sg

age = sg.Variable("age", scale="ratio", label="Age")
q_age = sg.NumericInput("Age?", var=age, id="q_age")
os.system("echo pwned")          # line 7: never executed

def helper(n):                  # line 9
    return n * 2

pages = []
for i in range(3):              # line 13: not read
    pages.append(sg.Page(name=f"loop{i}", items=[]))

page_a = sg.Page(name="a", items=[q_age])
page_b = sg.Page(name="b", items=[__import__("os").getcwd()])   # bad item dropped
survey = sg.Questionnaire(title="Partial", pages=[page_a, page_b])
"""
    result = parse_source(source)
    assert [p["name"] for p in result.document["pages"]] == ["a", "b"]
    lines = {d.line for d in result.dropped}
    assert {2, 7, 9, 13} <= lines
    texts = "\n".join(str(d) for d in result.dropped)
    assert "import os" in texts and "for statement" in texts and "functiondef statement" in texts
    assert "__import__" in texts
    # page_b lost its unreadable item but kept its place.
    assert result.document["pages"][1]["items"] == []


def test_string_conditions_and_operators_are_read():
    source = """
import siamang as sg
from siamang import Option

age = sg.Variable("age", scale="ratio", label="Age")
region = sg.Variable("region", scale="nominal", label="Region", labels={1: "N", 2: "S"})
q_age = sg.NumericInput("Age?", var=age, id="q_age")
q_region = sg.SingleChoice("Region?", var=region, id="q_region",
                           choices=[Option(1, "N"), Option(2, "S", hide_if=age.lt(18))])
p1 = sg.Page(name="p1", items=[q_age])
p2 = sg.Page(name="p2", items=[q_region], show_if=age.ge(18) & ~region.isin([2]),
             next_if=[("{age} > 60", "p3")], default_next="p3")
p3 = sg.Page(name="p3", items=[])
survey = sg.Questionnaire(title="Ops", pages=[p1, p2, p3])
"""
    result = parse_source(source)
    assert result.dropped == []
    p2 = result.document["pages"][1]
    assert p2["show_if"]["op"] == "and"
    assert p2["next_if"][0]["target"] == "p3"


def test_syntax_error_and_missing_survey_are_document_errors():
    with pytest.raises(DocumentError, match="Not valid Python"):
        parse_source("survey = sg.Questionnaire(")
    with pytest.raises(DocumentError, match="does not define"):
        parse_source("import siamang as sg\nx = 1\n")
    with pytest.raises(DocumentError, match="does not define"):
        # Defined, but only by code the reader will not run.
        parse_source(
            "import siamang as sg\ndef build():\n    return sg.Questionnaire(title='x', pages=[])\nsurvey = build()\n"
        )


def test_only_engine_callables_are_invoked():
    # A name shadowing the engine vocabulary does not open a door: `sg.Page`
    # resolves to the real class only through the whitelisted module object.
    source = """
import siamang as sg
Page = print
survey = sg.Questionnaire(title="x", pages=[Page("not executed")])
"""
    result = parse_source(source)
    assert result.document["pages"] == []
    assert any("Page" in d.what for d in result.dropped)
