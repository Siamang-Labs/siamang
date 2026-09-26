"""The Paired tests and Factor analysis nodes in a flow: checked, run, generated."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from siamang.codegen import generate_questionnaire
from siamang.flow import FlowRunner, check_flow, default_registry, generate_flow
from siamang.flow.document import resolved_params
from siamang.io import write_snapshot
from siamang.model import from_document, loads
from siamang.reporting.result_table import ResultTable

DOCUMENTS = Path(__file__).resolve().parent / "documents"
ROOT = Path(__file__).resolve().parents[1]  # this checkout, which the script must import
TRUST = ["trust_acme", "trust_globex"]
ITEMS = ["trust_acme", "trust_globex", "satisfaction", "age"]


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
        (
            "fac",
            "analyze.factor",
            {"items": ITEMS, "n_factors": 2, "rotation": "oblimin", "scores": True},
        ),
        ("means", "analyze.means", {"y": "factor_1", "by": "region"}),
        ("sec", "output.report_section", {"heading": "Related samples and factors"}),
        ("save", "output.save_report", {"title": "Stats", "path": "outputs/stats.md"}),
    ]
    edges = [(source[0], "data", n, "data") for n in ("wil", "mcn", "fri", "fac")]
    edges += [
        ("fac", "data", "means", "data"),
        ("wil", "table", "sec", "items"),
        ("mcn", "table", "sec", "items"),
        ("fri", "table", "sec", "items"),
        ("fri", "pairs", "sec", "items"),
        ("fac", "loadings", "sec", "items"),
        ("fac", "variance", "sec", "items"),
        ("fac", "correlations", "sec", "items"),
        ("fac", "stat", "sec", "items"),
        ("means", "table", "sec", "items"),
        ("sec", "report", "save", "sections"),
    ]
    return _flow(nodes, edges)


def test_the_nodes_are_registered_and_listed_as_unweighted():
    registry = default_registry()
    paired = registry.get("analyze.paired")
    assert paired.outputs == {"table": "Table", "pairs": "Table", "stat": "Stat"}
    assert paired.params["test"].values == ("auto", "wilcoxon", "mcnemar", "friedman", "cochran")
    assert paired.params["yes_codes"].kind == "json"
    factor = registry.get("analyze.factor")
    assert list(factor.outputs) == ["data", "loadings", "variance", "correlations", "stat"]
    assert factor.params["method"].values == ("minres", "principal", "ml")
    assert factor.params["rotation"].default == "varimax"
    # A prefix, not a variable: the flow check names the scores themselves.
    assert factor.params["into"].creates is None
    help_text = registry.get("prepare.apply_weight").params["column"].help
    _, unweighted = help_text.split("Unweighted, and saying so:")
    assert "Paired tests" in unweighted and "Factor analysis" in unweighted


def test_check_flow_knows_the_factor_scores_a_later_node_names(questionnaire_doc):
    assert check_flow(_stats_flow(), questionnaire=questionnaire_doc) == []
    # Two fixed factors make factor_1 and factor_2, not factor_3.
    flow = _stats_flow()
    flow["nodes"][5]["params"]["y"] = "factor_3"
    issues = check_flow(flow, questionnaire=questionnaire_doc)
    assert [issue.code for issue in issues] == ["UNKNOWN_VARIABLE"]
    # Chosen by a rule, any number up to one fewer than the items may appear.
    flow["nodes"][4]["params"].pop("n_factors")
    assert check_flow(flow, questionnaire=questionnaire_doc) == []
    # Without scores there are none to name.
    flow["nodes"][4]["params"]["scores"] = False
    issues = check_flow(flow, questionnaire=questionnaire_doc)
    assert [issue.code for issue in issues] == ["UNKNOWN_VARIABLE"]
    # The prefix is not a variable, with scores or without: naming it was
    # accepted and failed at run time with a KeyError.
    for scores, into in ((False, None), (True, None), (True, "f")):
        flow = _stats_flow()
        flow["nodes"][4]["params"].update(scores=scores)
        if into:
            flow["nodes"][4]["params"]["into"] = into
        flow["nodes"][5]["params"]["y"] = into or "factor_"
        issues = check_flow(flow, questionnaire=questionnaire_doc)
        assert [issue.code for issue in issues] == ["UNKNOWN_VARIABLE"], (scores, into)
    flow["nodes"][5]["params"]["y"] = "f2"
    assert check_flow(flow, questionnaire=questionnaire_doc) == []
    # The items take ordered scales; a nominal one is named before the run.
    flow = _stats_flow()
    flow["nodes"][4]["params"]["items"] = [*ITEMS, "region"]
    issues = check_flow(flow, questionnaire=questionnaire_doc)
    assert [issue.code for issue in issues] == ["VARIABLE_SCALE"]


def test_the_nodes_run_on_weighted_survey_data(questionnaire_doc, survey, tmp_path):
    nodes = [
        ("sim", "source.simulated", {"n": 250, "seed": 11}),
        ("cell", "prepare.cell_weights", {"variable": "gender", "targets": {"1": 0.5, "2": 0.5}}),
        ("apply", "prepare.apply_weight", {}),
    ]
    flow = _stats_flow(source=("apply", "prepare.apply_weight", {}))
    flow["nodes"] = [{"id": i, "type": t, "params": p} for i, t, p in nodes[:2]] + flow["nodes"]
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
    stat = result.output("fac", "stat")
    assert stat["Weight"] == unweighted and stat["Factors"] == 2
    assert stat["Rotation"] == "oblimin (direct quartimin, gamma 0)"
    scored = result.output("fac", "data")
    assert {"factor_1", "factor_2"} <= set(scored.frame.columns)
    assert scored.weight == "weight"  # the weight travels on with the data
    assert "Factor 1 score" in result.output("means", "stat")["Variable"]
    report = (tmp_path / "outputs" / "stats.md").read_text("utf-8")
    assert "Kendall's W" in report and "Communality" in report and "nan" not in report


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
    assert "from siamang.data import factor, paired" in code
    assert "paired.compare(" in code and "factor.analyze(" in code
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
    assert json.dumps(result.output("fac", "stat"))  # a stat is plain JSON for a tile


def test_cochrans_q_in_a_flow_on_exploded_awareness(questionnaire_doc, survey, tmp_path):
    """Awareness of three brands, asked as one multiple-choice question and
    exploded into 0/1 columns: Cochran's Q asks whether the brands are known
    equally, and the pairs which of them differ. The check knows the count
    (two are McNemar's), the code passes yes codes and pairwise comparisons
    and nothing the test ignores, and the run matches the module."""

    brands = ["aware_1", "aware_2", "aware_3"]
    flow = _flow(
        [
            ("sim", "source.simulated", {"n": 300, "seed": 5}),
            ("expl", "prepare.explode", {"variable": "aware"}),
            ("q", "analyze.paired", {"variables": brands, "test": "cochran"}),
            ("sec", "output.report_section", {"heading": "Awareness"}),
            ("save", "output.save_report", {"title": "Awareness", "path": "outputs/q.md"}),
        ],
        [
            ("sim", "data", "expl", "data"),
            ("expl", "data", "q", "data"),
            ("q", "table", "sec", "items"),
            ("q", "pairs", "sec", "items"),
            ("sec", "report", "save", "sections"),
        ],
        name="awareness",
    )
    assert check_flow(flow, questionnaire=questionnaire_doc) == []
    # The inspector asks for what the test reads: yes codes, pairs, their p.
    spec = default_registry().get("analyze.paired")
    params = resolved_params(spec, {"variables": brands, "test": "cochran"})
    assert all(spec.reads(name, params) for name in ("yes_codes", "posthoc", "p_value"))
    assert not spec.reads("zeros", params)
    code = generate_flow(flow, questionnaire_doc)
    assert 'test="cochran"' in code and "yes=None" in code and 'posthoc="holm"' in code
    assert "zeros=" not in code
    result = FlowRunner(flow, questionnaire=survey, questionnaire_document=questionnaire_doc).run(
        cwd=tmp_path
    )
    assert result.ok
    stat = result.output("q", "stat")
    assert stat["Test"] == "Cochran's Q" and stat["Variables"] == 3
    assert stat["Counts as yes"] == "1 = Yes"  # Explode labels its 0/1 columns
    data = result.output("expl", "data")
    from siamang.data import paired

    direct = paired.cochran(data, brands)
    assert stat == direct.stats
    assert len(result.output("q", "pairs").to_frame()) == 3
    report = (tmp_path / "outputs" / "q.md").read_text("utf-8")
    assert "Cochran's Q" in report and "McNemar for each pair" in report
    assert json.dumps(stat)
    # Two brands are McNemar's; a Counts as yes kept for Wilcoxon is warned of.
    flow["nodes"][2]["params"]["variables"] = brands[:2]
    issues = check_flow(flow, questionnaire=questionnaire_doc)
    assert [(i.severity, i.message) for i in issues] == [
        (
            "error",
            "q: Cochran's Q compares three or more yes/no variables; 2 were given. For two,"
            " use McNemar.",
        )
    ]
    flow["nodes"][2]["params"].update(variables=brands, test="friedman", yes_codes=1)
    issues = check_flow(flow, questionnaire=questionnaire_doc)
    assert [i.severity for i in issues] == ["warning"]
    flow["nodes"][2]["params"].update(test="cochran")
    assert check_flow(flow, questionnaire=questionnaire_doc) == []
