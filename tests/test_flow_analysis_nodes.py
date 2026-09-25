"""The Paired tests node in a flow: checked, run, generated."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from siamang.codegen import generate_questionnaire
from siamang.flow import FlowRunner, check_flow, default_registry, generate_flow
from siamang.io import write_snapshot
from siamang.model import from_document, loads
from siamang.reporting.result_table import ResultTable

DOCUMENTS = Path(__file__).resolve().parent / "documents"
ROOT = Path(__file__).resolve().parents[1]  # this checkout, which the script must import
TRUST = ["trust_acme", "trust_globex"]


@pytest.fixture(scope="module")
def questionnaire_doc():
    return loads((DOCUMENTS / "brand_awareness.questionnaire.json").read_text("utf-8"))


@pytest.fixture(scope="module")
def survey(questionnaire_doc):
    return from_document(questionnaire_doc).survey


def _flow(nodes, edges, name="stats"):
    return {
        "schema_version": "1.0",
        "name": name,
        "nodes": [{"id": i, "type": t, "params": p} for i, t, p in nodes],
        "edges": [
            {"from": {"node": a, "port": ap}, "to": {"node": b, "port": bp}}
            for a, ap, b, bp in edges
        ],
    }


def _stats_flow(source=("src", "source.responses", {})):
    nodes = [
        source,
        ("wil", "analyze.paired", {"variables": TRUST}),
        ("mcn", "analyze.paired", {"variables": TRUST, "test": "mcnemar", "yes_codes": [4, 5]}),
        ("fri", "analyze.paired", {"variables": [*TRUST, "satisfaction"], "posthoc": "bonferroni"}),
        ("sec", "output.report_section", {"heading": "Related samples"}),
        ("save", "output.save_report", {"title": "Stats", "path": "outputs/stats.md"}),
    ]
    edges = [(source[0], "data", n, "data") for n in ("wil", "mcn", "fri")]
    edges += [
        ("wil", "table", "sec", "items"),
        ("mcn", "table", "sec", "items"),
        ("fri", "table", "sec", "items"),
        ("fri", "pairs", "sec", "items"),
        ("sec", "report", "save", "sections"),
    ]
    return _flow(nodes, edges)


def test_the_nodes_are_registered_and_listed_as_unweighted():
    registry = default_registry()
    paired = registry.get("analyze.paired")
    assert paired.outputs == {"table": "Table", "pairs": "Table", "stat": "Stat"}
    assert paired.params["test"].values == ("auto", "wilcoxon", "mcnemar", "friedman")
    assert paired.params["yes_codes"].kind == "json"
    help_text = registry.get("prepare.apply_weight").params["column"].help
    _, unweighted = help_text.split("Unweighted, and saying so:")
    assert "Paired tests" in unweighted


def test_check_flow_accepts_the_paired_tests(questionnaire_doc):
    assert check_flow(_stats_flow(), questionnaire=questionnaire_doc) == []
    flow = _stats_flow()
    flow["nodes"][1]["params"]["variables"] = ["trust_acme", "trust_nope"]
    issues = check_flow(flow, questionnaire=questionnaire_doc)
    assert [issue.code for issue in issues] == ["UNKNOWN_VARIABLE"]


def test_the_nodes_run_on_weighted_survey_data(questionnaire_doc, survey, tmp_path):
    nodes = [
        ("sim", "source.simulated", {"n": 250, "seed": 11}),
        ("cell", "prepare.cell_weights", {"variable": "gender", "targets": {"1": 0.5, "2": 0.5}}),
    ]
    flow = _stats_flow(source=("apply", "prepare.apply_weight", {}))
    flow["nodes"] = [{"id": i, "type": t, "params": p} for i, t, p in nodes] + flow["nodes"]
    flow["edges"] = [
        {"from": {"node": "sim", "port": "data"}, "to": {"node": "cell", "port": "data"}},
        {"from": {"node": "cell", "port": "data"}, "to": {"node": "apply", "port": "data"}},
        *flow["edges"],
    ]
    assert check_flow(flow, questionnaire=questionnaire_doc) == []
    result = FlowRunner(flow, questionnaire=survey, questionnaire_document=questionnaire_doc).run(
        cwd=tmp_path
    )
    assert result.ok
    unweighted = "unweighted (the weight 'weight' is not applied)"
    for node in ("wil", "mcn", "fri"):
        table, stat = result.output(node, "table"), result.output(node, "stat")
        assert isinstance(table, ResultTable) and table.stats == stat
        assert stat["Weight"] == unweighted
        # trust_* carry a "Refused" missing code, which never counts as an answer.
        assert "(9 = Refused) left out" in stat["Missing codes"]
    assert result.output("wil", "stat")["Test"] == "Wilcoxon signed-rank"
    assert result.output("mcn", "stat")["Counts as yes"] == "4 = High, 5 = Full"
    assert result.output("fri", "stat")["Test"] == "Friedman"
    assert len(result.output("fri", "pairs").to_frame()) == 3
    assert "Bonferroni" in result.output("fri", "pairs").stats["Adjustment"]
    report = (tmp_path / "outputs" / "stats.md").read_text("utf-8")
    assert "Kendall's W" in report and "Rank-biserial r" in report and "nan" not in report


def test_the_generated_script_reproduces_the_runner(questionnaire_doc, survey, tmp_path):
    responses = survey.simulate(n=220, seed=9)
    flow = _stats_flow()
    runner_dir, script_dir = tmp_path / "runner", tmp_path / "script"
    result = FlowRunner(flow, questionnaire=survey, questionnaire_document=questionnaire_doc).run(
        sources={"src": responses}, cwd=runner_dir
    )
    assert result.ok

    code = generate_flow(flow, questionnaire_doc)
    assert code == generate_flow(flow, questionnaire_doc)
    assert "from siamang.data import paired" in code and "paired.compare(" in code
    (script_dir / "survey").mkdir(parents=True)
    (script_dir / "survey" / "__init__.py").write_text("", encoding="utf-8")
    (script_dir / "survey" / "questionnaire.py").write_text(
        generate_questionnaire(questionnaire_doc), encoding="utf-8"
    )
    (script_dir / "scripts").mkdir()
    script = script_dir / "scripts" / "stats.py"
    script.write_text(code, encoding="utf-8")
    snapshot = write_snapshot(responses, script_dir / "data" / "responses.csv")
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(script_dir), str(ROOT)])}
    completed = subprocess.run(
        [sys.executable, str(script), "--data", str(snapshot)],
        cwd=script_dir,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    ours = (runner_dir / "outputs" / "stats.md").read_text("utf-8")
    theirs = (script_dir / "outputs" / "stats.md").read_text("utf-8")
    assert ours == theirs
    assert "Wilcoxon signed-rank" in ours and "McNemar" in ours
    assert json.dumps(result.output("fri", "stat"))  # a stat is plain JSON for a tile
