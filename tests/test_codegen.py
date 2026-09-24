"""siamang.codegen — questionnaire documents to Python source."""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from siamang.cli.loader import load_survey_module
from siamang.codegen import generate_questionnaire
from siamang.codegen.emit import Call, Dict, List, Raw, literal, render
from siamang.codegen.format import ruff_command
from siamang.core import validate_options
from siamang.model import (
    DocumentError,
    dumps,
    from_document,
    import_module,
    loads,
    to_document,
)

ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures"
DOCUMENTS = ROOT / "documents"
FIXTURE_MODULES = [
    "brand_awareness_questionnaire.py",
    "digital_life_questionnaire.py",
    "kitchen_sink_questionnaire.py",
]


def _exec(code: str, tmp_path: Path, name: str = "generated"):
    path = tmp_path / f"{name}.py"
    path.write_text(code, encoding="utf-8")
    module = load_survey_module(path)
    sys.modules.pop(f"_siamang_user_{path.stem}", None)
    return module


def _ruff(*args: str, code: str) -> subprocess.CompletedProcess:
    command = ruff_command()
    assert command, "ruff is a dev dependency"
    return subprocess.run(
        [*command, *args, "-"], input=code, capture_output=True, text=True, check=False
    )


def _assert_generated_is_faithful(document: dict, tmp_path: Path) -> str:
    """doc -> py -> exec -> doc' with doc' == doc, and the code is clean and stable."""

    code = generate_questionnaire(document)
    assert code == generate_questionnaire(document), "generation must be deterministic"
    module = _exec(code, tmp_path)
    module.survey.validate()
    options = getattr(module, "options", None)
    validate_options(module.survey, options)
    assert to_document(module.survey, options) == document
    # ruff: formatting is a fixed point and the linter has nothing to say.
    formatted = _ruff("format", "--isolated", "--line-length", "100", code=code)
    assert formatted.returncode == 0, formatted.stderr
    assert formatted.stdout == code
    lint = _ruff(
        "check",
        "--isolated",
        "--line-length",
        "100",
        "--select",
        "E,F,W,I,UP,B,SIM",
        "--ignore",
        "E501",
        "--no-cache",
        code=code,
    )
    assert lint.returncode == 0, lint.stdout + lint.stderr
    return code


@pytest.mark.parametrize("fixture", FIXTURE_MODULES)
def test_generated_code_round_trips_fixture_modules(fixture, tmp_path):
    document = import_module(FIXTURES / fixture).document
    code = _assert_generated_is_faithful(document, tmp_path)
    # A second generation from the executed generated code is byte-identical.
    module = _exec(code, tmp_path, "second")
    again = to_document(module.survey, getattr(module, "options", None))
    assert generate_questionnaire(again) == code


@pytest.mark.parametrize("path", sorted(DOCUMENTS.glob("*.questionnaire.json")))
def test_committed_documents_have_committed_code(path, tmp_path):
    """tests/documents/<name>.generated.py is the golden output for <name>.questionnaire.json."""

    document = loads(path.read_text(encoding="utf-8"))
    code = _assert_generated_is_faithful(document, tmp_path)
    golden = path.with_name(path.name.replace(".questionnaire.json", ".generated.py"))
    assert golden.exists(), f"run: siamang codegen {path} -o {golden}"
    assert code == golden.read_text(encoding="utf-8")


def test_kitchen_sink_code_shape(tmp_path):
    document = import_module(FIXTURES / "kitchen_sink_questionnaire.py").document
    code = generate_questionnaire(document)
    assert "from datetime import datetime" in code
    assert "from siamang import Attribute, Media, MissingValue, Option, Quota" in code
    assert (
        "from siamang.core import ContentPage, DisqualificationPage, FinalPage, RedirectPage"
        in code
    )
    assert "from siamang.frontend import UIConfig" in code
    # Wide MultiChoice is written with vars=, missing values with MissingValue when typed.
    assert 'sg.MultiChoice("Own?", vars=[owns_a, owns_b], max_answers=2, id="q_own")' in code
    assert 'missing=(MissingValue(99, "Refused", kind="refusal"),)' in code
    assert "missing_values=[9]," in code and 'missing_labels={9: "Don\'t know"}' in code
    # Conditions: operators at depth <= 2, functions deeper, raw strings verbatim.
    assert 'show_if=age.ge(18) & ~region.eq("south")' in code
    assert 'show_if=consent.eq(1) & ~region.isin(["99", "south"])' in code
    assert "sg.AND(age.ge(18), sg.OR(region.eq(1), region.eq(2)))" in generate_questionnaire(
        import_module(FIXTURES / "brand_awareness_questionnaire.py").document
    )
    assert 'hide_if="{consent} == 2"' in code
    assert 'deadline=datetime.fromisoformat("2026-12-31T23:59:00")' in code
    # The registry-only variable survives through an explicit codebook.
    assert "codebook = sg.VariableMap()" in code
    assert "variables=codebook" in code
    # Custom scripts keep their code and settings.
    assert 'context={"level": "debug"}' in code and "sandbox=False" in code
    module = _exec(code, tmp_path)
    assert module.survey.variables["unused"].label == "Registered but not asked"


def test_assign_condition_generates_a_readable_call_and_survives_the_round_trip(tmp_path):
    document = {
        "schema_version": "1.0",
        "title": "Split ballot",
        "variables": {
            "q1": {"scale": "nominal"},
            "condition": {
                "scale": "nominal",
                "role": "grouping",
                "labels": [
                    {"code": 1, "label": "Control"},
                    {"code": 2, "label": "Treatment"},
                ],
            },
        },
        "pages": [
            {"name": "p1", "items": [{"type": "OpenText", "id": "q1", "var": "q1", "text": "Why?"}]}
        ],
        "scripts": [
            {
                "type": "assign_condition",
                "variable": "condition",
                "arms": [
                    {"code": 1, "label": "Control", "weight": 2},
                    {"code": 2, "label": "Treatment"},
                ],
                "seed": "study26",
            }
        ],
        # A quota on the assigned variable is how an arm is kept balanced.
        "quotas": [{"variable": "condition", "target_value": 1, "limit": 200}],
    }
    source = generate_questionnaire(document, header="Test.")
    assert "sg.Script.assign_condition(" in source
    assert '[(1, "Control", 2), (2, "Treatment")]' in source
    assert 'seed="study26"' in source
    assert 'Quota("condition", 1, 200)' in source

    module = _exec(source, tmp_path)
    assert to_document(module.survey)["scripts"] == document["scripts"]


def test_balanced_assignment_survives_the_round_trip(tmp_path):
    # balance=True has to reach the generated .py, or re-opening a fielded
    # study would quietly go back to an unbalanced draw.
    document = {
        "schema_version": "1.0",
        "title": "Split ballot",
        "variables": {
            "q1": {"scale": "nominal"},
            "condition": {
                "scale": "nominal",
                "role": "grouping",
                "labels": [
                    {"code": 1, "label": "Control"},
                    {"code": 2, "label": "Treatment"},
                ],
            },
        },
        "pages": [
            {"name": "p1", "items": [{"type": "OpenText", "id": "q1", "var": "q1", "text": "Why?"}]}
        ],
        "scripts": [
            {
                "type": "assign_condition",
                "variable": "condition",
                "arms": [{"code": 1, "label": "Control"}, {"code": 2, "label": "Treatment"}],
                "balance": True,
            }
        ],
        "quotas": [
            {"variable": "condition", "target_value": 1, "limit": 250},
            {"variable": "condition", "target_value": 2, "limit": 250},
        ],
    }
    source = generate_questionnaire(document, header="Test.")
    assert "balance=True" in source
    module = _exec(source, tmp_path)
    assert to_document(module.survey)["scripts"] == document["scripts"]


def test_multiline_custom_script_and_identifier_clashes(tmp_path):
    document = {
        "schema_version": "1.0",
        "title": 'Odd "names"',
        "variables": {
            "class": {"scale": "nominal", "labels": [{"code": "a", "label": "A"}]},
            "1st": {"scale": "ratio"},
            "sg": {"scale": "ratio"},
            "age": {"scale": "ratio"},
        },
        "pages": [
            {
                "name": "p-1",
                "items": [
                    {"type": "SingleChoice", "id": "class", "text": "Class?", "var": "class"},
                    {"type": "NumericInput", "id": "age", "text": "Age?", "var": "age"},
                    {"type": "NumericInput", "id": "first", "text": "First?", "var": "1st"},
                    {"type": "NumericInput", "id": "survey", "text": "sg?", "var": "sg"},
                ],
                "show_if": {
                    "type": "expression",
                    "op": ">",
                    "left": 3,
                    "right": {"type": "var", "name": "age"},
                },
            }
        ],
        "scripts": [
            {
                "type": "custom",
                "trigger": "onInit",
                "code": 'const s = """x""";\nif (a) {\n  b = "\\\\n";\n}\n',
            }
        ],
    }
    # Hand-written documents are not canonical (defaults left implicit); the
    # faithfulness check compares against the canonical form.
    loaded = from_document(document)
    document = to_document(loaded.survey, loaded.options)
    code = _assert_generated_is_faithful(document, tmp_path)
    assert "class_var = sg.Variable" in code
    assert "v_1st = sg.Variable" in code
    assert "sg_var = sg.Variable" in code
    assert "q_age = sg.NumericInput" in code and "q_class = sg.SingleChoice" in code
    assert "q_survey = sg.NumericInput" in code
    assert "page_p_1 = sg.Page" in code
    assert 'sg.Expression(">", 3, sg.VarRef("age"))' in code


def test_a_name_with_a_line_break_stays_on_its_comment_line(tmp_path):
    """Each definition is marked ``# studio: <question id>`` (a variable's
    name, a page's name). An id with a line break ended the comment there and
    the rest ran when the module was imported — as a research bundle's flow
    scripts import it."""

    import ast

    marker = tmp_path / "PLANTED"
    planted = f"import os; os.system('touch {marker}')"
    document = {
        "schema_version": "1.0",
        "title": "T",
        "variables": {
            f"v1\r{planted} #": {"scale": "nominal", "labels": [{"code": 1, "label": "A"}]},
        },
        "pages": [
            {
                "name": f"p1\n{planted} #",
                "items": [
                    {
                        "type": "SingleChoice",
                        "id": f"q1\n{planted} #",
                        "var": f"v1\r{planted} #",
                        "text": "?",
                    }
                ],
            }
        ],
    }
    code = generate_questionnaire(document)
    tree = ast.parse(code)
    imported = [
        a.name for node in ast.walk(tree) if isinstance(node, ast.Import) for a in node.names
    ]
    assert "os" not in imported
    markers = [line.rstrip() for line in code.split("\n") if line.startswith("# studio:")]
    assert markers == [
        f"# studio: var v1 {planted} #",
        f"# studio: q1 {planted} #",
        f"# studio: page p1 {planted} #",
    ]
    module = _exec(code, tmp_path)
    assert not marker.exists()
    assert module.survey.pages[0].name == f"p1\n{planted} #"


def test_generation_without_ruff_is_still_valid(tmp_path, monkeypatch):
    document = import_module(FIXTURES / "digital_life_questionnaire.py").document
    monkeypatch.setattr("siamang.codegen.questionnaire.format_source", _raise_unavailable)
    code = generate_questionnaire(document)
    module = _exec(code, tmp_path)
    assert to_document(module.survey, module.options) == document
    assert generate_questionnaire(document, format=False) == code


def _raise_unavailable(code, **kwargs):
    from siamang.codegen import FormatterUnavailable

    raise FormatterUnavailable("no ruff")


def test_invalid_document_is_rejected_before_generation():
    with pytest.raises(DocumentError, match="schema_version"):
        generate_questionnaire({"title": "x", "pages": []})


def test_custom_header():
    document = import_module(FIXTURES / "brand_awareness_questionnaire.py").document
    code = generate_questionnaire(document, header="Made by Studio (schema {schema}).")
    assert "Made by Studio (schema 1.0)." in code
    assert "siamang codegen" not in code


def test_emit_layout():
    call = Call("f", (literal("a"),), (("k", List((literal(1), literal(2)))),))
    assert render(call) == 'f("a", k=[1, 2])'
    long_items = tuple(literal(f"item number {i}") for i in range(8))
    expanded = render(Call("g", (List(long_items),)), 0)
    assert expanded.startswith('g(\n    [\n        "item number 0",')
    assert expanded.endswith("    ],\n)")
    assert render(Dict(((literal(1), Raw("x")),))) == "{1: x}"
    assert render(literal({"a": [None, True, 1.5]})) == '{"a": [None, True, 1.5]}'
    assert literal('say "hi"').text == "'say \"hi\"'"
    assert literal("it's").text == '"it\'s"'


def test_cli_codegen_matches_library(tmp_path):
    source = DOCUMENTS / "brand_awareness.questionnaire.json"
    out = tmp_path / "q.py"
    result = subprocess.run(
        [sys.executable, "-m", "siamang", "codegen", str(source), "-o", str(out)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert out.read_text(encoding="utf-8") == generate_questionnaire(loads(source.read_text()))
    check = subprocess.run(
        [sys.executable, "-m", "siamang", "validate", str(out)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert check.returncode == 0 and "OK" in check.stdout


def test_generated_document_text_is_stable_through_code(tmp_path):
    """doc -> py -> doc' as text: what a version history would store."""

    for fixture in FIXTURE_MODULES:
        document = import_module(FIXTURES / fixture).document
        module = _exec(generate_questionnaire(document), tmp_path, Path(fixture).stem)
        assert dumps(to_document(module.survey, getattr(module, "options", None))) == dumps(
            document
        )
        # from_document on the regenerated document is equal to the executed module's survey
        assert from_document(document).survey.title == module.survey.title


@pytest.mark.skipif(
    shutil.which("ruff") is None and importlib.util.find_spec("ruff") is None, reason="ruff"
)
def test_ruff_is_available_for_the_suite():
    assert ruff_command() is not None
