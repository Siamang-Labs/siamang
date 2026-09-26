"""The methods added to the flow nodes in one series — ordinal regression, key
drivers, the perceptual map and price sensitivity: checked, generated, run on a
SurveyData, and reported."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from siamang.flow import FlowRunner, check_flow, default_registry, generate_flow
from siamang.model import from_document, loads

DOCUMENTS = Path(__file__).resolve().parent / "documents"


@pytest.fixture(scope="module")
def questionnaire_doc():
    return loads((DOCUMENTS / "brand_awareness.questionnaire.json").read_text("utf-8"))


@pytest.fixture(scope="module")
def survey(questionnaire_doc):
    return from_document(questionnaire_doc).survey


def _flow(nodes, edges, name="methods"):
    return {
        "schema_version": "1.0",
        "name": name,
        "nodes": [{"id": i, "type": t, "params": p} for i, t, p in nodes],
        "edges": [
            {"from": {"node": a, "port": ap}, "to": {"node": b, "port": bp}}
            for a, ap, b, bp in edges
        ],
    }


def _weighted_source():
    """Simulated responses, weighted to an even gender split."""
    nodes = [
        ("sim", "source.simulated", {"n": 400, "seed": 21}),
        ("cell", "prepare.cell_weights", {"variable": "gender", "targets": {"1": 0.5, "2": 0.5}}),
        ("apply", "prepare.apply_weight", {}),
    ]
    edges = [("sim", "data", "cell", "data"), ("cell", "data", "apply", "data")]
    return nodes, edges


# ─── ordinal regression ──────────────────────────────────────────────────────


def test_regression_offers_the_ordinal_model_and_runs_it_weighted(
    questionnaire_doc, survey, tmp_path
):
    spec = default_registry().get("analyze.regression")
    assert spec.params["kind"].values == ("auto", "ols", "logit", "ordinal")
    assert spec.params["kind"].default == "auto"
    nodes, edges = _weighted_source()
    predictors = ["trust_acme", "region", "age"]
    nodes += [
        ("ord", "analyze.regression", {"y": "satisfaction", "predictors": predictors,
                                       "kind": "ordinal"}),
        ("sec", "output.report_section", {"heading": "Satisfaction"}),
        ("save", "output.save_report", {"title": "Ordinal", "path": "outputs/ord.md"}),
    ]  # fmt: skip
    edges += [
        ("apply", "data", "ord", "data"),
        ("ord", "table", "sec", "items"),
        ("ord", "stat", "sec", "items"),
        ("sec", "report", "save", "sections"),
    ]
    flow = _flow(nodes, edges)
    assert check_flow(flow, questionnaire=questionnaire_doc) == []
    code = generate_flow(flow, questionnaire_doc)
    assert (
        "_model = n_apply.analysis.regression(\n"
        '    "satisfaction", ["trust_acme", "region", "age"], kind="ordinal"\n)'
    ) in code
    result = FlowRunner(flow, questionnaire=survey, questionnaire_document=questionnaire_doc).run(
        cwd=tmp_path
    )
    assert result.ok
    stat = result.output("ord", "stat")
    assert stat["model"] == "ordinal logit (proportional odds)" and stat["weight"] == "weight"
    assert stat["order"] == (
        "Very dissatisfied < Dissatisfied < Neutral < Satisfied < Very satisfied"
    )
    # trust_acme's Refused (9) is not a level of trust.
    assert "Trust: Acme" in stat["missing_codes"] and "9 = Refused" in stat["missing_codes"]
    table = result.output("ord", "table")
    assert list(table["type"]).count("threshold") == 4
    # The questionnaire asks the South no trust question: two regions remain.
    assert list(table["term"][:3]) == ["trust_acme", "region = North", "age"]
    report = (tmp_path / "outputs" / "ord.md").read_text("utf-8")
    assert "Very dissatisfied|Dissatisfied" in report and "odds_ratio_lower" in report
    assert "| nan" not in report  # the thresholds' odds ratio is blank
    assert json.dumps(stat)


# ─── key drivers ─────────────────────────────────────────────────────────────


def test_key_drivers_node_checked_generated_and_run_weighted(questionnaire_doc, survey, tmp_path):
    spec = default_registry().get("analyze.drivers")
    assert spec.title == "Key drivers" and list(spec.outputs) == ["table", "stat"]
    assert spec.params["method"].values == ("relative_weights", "shapley")
    nodes, edges = _weighted_source()
    drivers_params = {"y": "satisfaction", "predictors": ["trust_acme", "trust_globex", "age"]}
    nodes += [
        ("kd", "analyze.drivers", drivers_params),
        ("sh", "analyze.drivers", {**drivers_params, "method": "shapley"}),
        ("sec", "output.report_section", {"heading": "Drivers"}),
        ("save", "output.save_report", {"title": "Drivers", "path": "outputs/kd.md"}),
    ]
    edges += [
        ("apply", "data", "kd", "data"),
        ("apply", "data", "sh", "data"),
        ("kd", "table", "sec", "items"),
        ("sh", "table", "sec", "items"),
        ("sec", "report", "save", "sections"),
    ]
    flow = _flow(nodes, edges)
    assert check_flow(flow, questionnaire=questionnaire_doc) == []
    code = generate_flow(flow, questionnaire_doc)
    assert "from siamang.data import drivers" in code
    assert 'method="relative_weights"' in code and 'method="shapley"' in code
    result = FlowRunner(flow, questionnaire=survey, questionnaire_document=questionnaire_doc).run(
        cwd=tmp_path
    )
    assert result.ok
    stat = result.output("kd", "stat")
    assert stat["Method"] == "Johnson's relative weights" and stat["Weight"] == "weight"
    assert stat["Outcome"] == "Overall satisfaction" and "9 = Refused" in stat["Missing codes"]
    table = result.output("kd", "table")
    assert table.analysis.weight == "weight"
    assert table.to_frame()["% of R²"].sum() == pytest.approx(100, abs=0.2)
    from siamang.data import drivers

    direct = drivers.analyze(result.output("apply", "data"), **drivers_params)
    assert direct.stats == stat
    assert result.output("sh", "stat")["Method"] == "Shapley value decomposition of R² (LMG)"
    report = (tmp_path / "outputs" / "kd.md").read_text("utf-8")
    assert "Relative weight" in report and "Shapley value" in report
    assert json.dumps(stat)
    # One driver is not a split; a nominal with three answers is refused by the run.
    flow["nodes"][3]["params"]["predictors"] = ["age"]
    issues = check_flow(flow, questionnaire=questionnaire_doc)
    assert [(i.severity, i.code) for i in issues] == [("error", "PARAM_CONFLICT")]
    assert issues[0].message.startswith(
        "kd: Key drivers splits R² between two or more predictors; 1 was given."
    )
    flow["nodes"][3]["params"]["predictors"] = ["age", "gender"]
    assert check_flow(flow, questionnaire=questionnaire_doc) == []
    runner = FlowRunner(flow, questionnaire=survey, questionnaire_document=questionnaire_doc)
    failed = runner.run(cwd=tmp_path, raise_on_error=False)
    error = next(run for run in failed.runs if run.state == "error")
    assert error.node == "kd" and "Gender is nominal with 3 answers" in error.error
    assert "Explode multiple choice" in error.error
