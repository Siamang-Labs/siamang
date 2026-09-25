"""The statistics nodes, the paired tests and factor analysis, and the nodes that
expose the engine, in one flow: a variable one of them makes is read by the
others, the check knows it before the run, and the generated script writes
what the runner writes."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

import siamang as sg
from siamang.codegen import generate_questionnaire
from siamang.codegen.format import ruff_command
from siamang.flow import FlowRunner, check_flow, generate_flow
from siamang.model import from_document, loads

DOCUMENTS = Path(__file__).resolve().parent / "documents"
UNWEIGHTED = "unweighted (the weight 'weight' is not applied)"


@pytest.fixture(scope="module")
def questionnaire_doc():
    return loads((DOCUMENTS / "brand_awareness.questionnaire.json").read_text("utf-8"))


@pytest.fixture(scope="module")
def survey(questionnaire_doc):
    return from_document(questionnaire_doc).survey


def _combined_flow():
    items = ["trust_acme", "trust_globex", "satisfaction", "age"]
    scores = ["factor_1", "factor_2"]
    nodes = [
        ("sim", "source.simulated", {"n": 240, "seed": 7}),
        (
            "band",
            "prepare.bands",
            {"variable": "age", "bins": [16, 30, 45, 65, 100], "into": "age_band"},
        ),
        ("cell", "prepare.cell_weights", {"variable": "gender", "targets": {"1": 0.5, "2": 0.5}}),
        ("apply", "prepare.apply_weight", {}),
        ("fac", "analyze.factor", {"items": items, "n_factors": 2, "scores": True}),
        (
            "means",
            "analyze.means",
            {"y": "factor_1", "by": "age_band", "method": "anova", "posthoc": "tukey"},
        ),
        ("tt", "analyze.ttest", {"y": "factor_1", "group": "gender", "group_a": 1, "group_b": 2}),
        ("desc", "analyze.descriptives", {"variables": scores, "by": "age_band"}),
        (
            "matrix",
            "analyze.correlation_matrix",
            {"items": [*scores, "satisfaction"], "method": "pearson", "adjust": "holm"},
        ),
        ("fri", "analyze.paired", {"variables": items[:3]}),
        ("fisher", "analyze.crosstab", {"row": "age_band", "col": "gender", "method": "fisher"}),
        ("r", "output.export_file", {"path": "outputs/combined.R"}),
        ("sec", "output.report_section", {"heading": "Combined"}),
        ("save", "output.save_report", {"title": "Combined", "path": "outputs/combined.md"}),
    ]
    chain = ["sim", "band", "cell", "apply", "fac"]
    edges = [(a, "data", b, "data") for a, b in zip(chain, chain[1:], strict=False)]
    edges += [("fac", "data", n, "data") for n in ("means", "tt", "desc", "matrix", "r")]
    edges += [("apply", "data", n, "data") for n in ("fri", "fisher")]
    edges += [(n, "table", "sec", "items") for n in ("means", "tt", "desc", "matrix", "fri")]
    edges += [("fisher", "table", "sec", "items"), ("sec", "report", "save", "sections")]
    return {
        "schema_version": "1.0",
        "name": "combined",
        "nodes": [{"id": i, "type": t, "params": p} for i, t, p in nodes],
        "edges": [
            {"from": {"node": a, "port": ap}, "to": {"node": b, "port": bp}}
            for a, ap, b, bp in edges
        ],
    }


def test_the_nodes_of_the_three_series_check_and_run_together(questionnaire_doc, survey, tmp_path):
    flow = _combined_flow()
    # factor_1 (Factor analysis) and age_band (Bands) are known before the run.
    assert check_flow(flow, questionnaire=questionnaire_doc) == []
    flow["nodes"][5]["params"]["y"] = "factor_3"
    issues = check_flow(flow, questionnaire=questionnaire_doc)
    assert [issue.code for issue in issues] == ["UNKNOWN_VARIABLE"]
    flow["nodes"][5]["params"].update(y="factor_1", method="kruskal")
    issues = check_flow(flow, questionnaire=questionnaire_doc)
    assert [issue.code for issue in issues] == ["PARAM_CONFLICT"]

    result = FlowRunner(
        _combined_flow(), questionnaire=survey, questionnaire_document=questionnaire_doc
    ).run(cwd=tmp_path)
    assert result.ok
    assert result.output("fac", "data").weight == "weight"
    assert result.output("fac", "stat")["Weight"] == UNWEIGHTED
    means = result.output("means", "stat")
    assert means["Test"] == "One-way ANOVA" and means["Post-hoc"].startswith("Tukey HSD: ")
    assert result.output("tt", "stat")["Weight"] == UNWEIGHTED
    assert "Weighted N" in result.output("desc", "table").to_frame().columns
    matrix = result.output("matrix", "stat")
    assert matrix["p adjustment"] == "Holm, over 3 pairs" and matrix["Weight"] != UNWEIGHTED
    assert result.output("fri", "stat")["Test"] == "Friedman"
    assert result.output("fisher", "stat")["Test"] == "Fisher-Freeman-Halton exact test"
    report = (tmp_path / "outputs" / "combined.md").read_text("utf-8")
    assert "**Post-hoc: Tukey HSD**" in report and "Kendall's W" in report
    assert "30 to under 45" in report and "nan" not in report


def test_the_generated_script_of_the_combined_flow_writes_what_the_runner_writes(
    questionnaire_doc, survey, tmp_path
):
    flow = _combined_flow()
    code = generate_flow(flow, questionnaire_doc)
    assert code == generate_flow(flow, questionnaire_doc)
    lint = subprocess.run(
        [
            *ruff_command(),
            "check",
            "--isolated",
            "--select",
            "E,F,W,B,SIM",
            "--ignore",
            "E501",
            "-",
        ],
        input=code,
        capture_output=True,
        text=True,
        check=False,
    )
    assert lint.returncode == 0, lint.stdout
    for call in ("bands.bands(", "factor.analyze(", "paired.compare(", "report.ttest("):
        assert call in code

    runner_dir, script_dir = tmp_path / "runner", tmp_path / "script"
    ran = FlowRunner(flow, questionnaire=survey, questionnaire_document=questionnaire_doc).run(
        cwd=runner_dir
    )
    assert ran.ok
    (script_dir / "survey").mkdir(parents=True)
    (script_dir / "survey" / "__init__.py").write_text("", encoding="utf-8")
    (script_dir / "survey" / "questionnaire.py").write_text(
        generate_questionnaire(questionnaire_doc), encoding="utf-8"
    )
    (script_dir / "scripts").mkdir()
    script = script_dir / "scripts" / "combined.py"
    script.write_text(code, encoding="utf-8")
    engine = Path(sg.__file__).resolve().parent.parent  # this checkout's engine
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join([str(script_dir), str(engine)]),
        "MPLBACKEND": "Agg",
    }
    completed = subprocess.run(
        [sys.executable, str(script)],
        cwd=script_dir,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    for name in ("combined.md", "combined.csv", "combined.dictionary.json"):
        ours = (runner_dir / "outputs" / name).read_text("utf-8")
        assert ours == (script_dir / "outputs" / name).read_text("utf-8"), name
