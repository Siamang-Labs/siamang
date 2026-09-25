"""The statistics nodes in a flow: Correlation's method, Correlation matrix,
t-test, the tests chosen by hand in Group means, Compare groups and Crosstab,
and the checks that keep a post-hoc test after the test it follows."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
import pytest

from siamang.data import SurveyData
from siamang.flow import FlowError, FlowRunner, check_flow, default_registry, generate_flow
from siamang.flow.document import resolve_flow
from siamang.flow.registry import RegistryError, condition_holds, spec_from_dict
from siamang.flow.template import render_node
from siamang.model import from_document, loads

DOCUMENTS = Path(__file__).resolve().parent / "documents"


@pytest.fixture(scope="module")
def questionnaire_doc():
    return loads((DOCUMENTS / "brand_awareness.questionnaire.json").read_text("utf-8"))


@pytest.fixture(scope="module")
def survey(questionnaire_doc):
    return from_document(questionnaire_doc).survey


def _flow(nodes, edges):
    return {
        "schema_version": "1.0",
        "name": "t",
        "nodes": [{"id": i, "type": t, "params": p} for i, t, p in nodes],
        "edges": [
            {"from": {"node": a, "port": ap}, "to": {"node": b, "port": bp}}
            for a, ap, b, bp in edges
        ],
    }


def _one(node_type, params, questionnaire_doc):
    flow = _flow(
        [("src", "source.responses", {}), ("n", node_type, params)],
        [("src", "data", "n", "data")],
    )
    return flow, check_flow(flow, questionnaire=questionnaire_doc)


# ─── conditions and checks ───────────────────────────────────────────────────


def test_a_condition_reads_equal_unequal_set_and_all_of():
    params = {"method": "anova", "posthoc": "none", "test": False, "code": 0, "empty": ""}
    assert condition_holds("method=anova", params)
    assert condition_holds("method!=auto", params)
    assert not condition_holds("method!=anova", params)
    assert condition_holds("method=anova & posthoc=none", params)
    assert not condition_holds("method=anova & posthoc!=none", params)
    assert condition_holds("test=False", params)
    # Set: a code of 0 is set, false and empty are not.
    assert condition_holds("code", params)
    assert not condition_holds("test", params) and not condition_holds("empty", params)
    assert not condition_holds("missing", params)


def test_a_spec_checks_its_checks():
    base = {
        "type": "analyze.x",
        "category": "analyze",
        "title": "X",
        "inputs": {"data": "SurveyData"},
        "outputs": {"stat": "Stat"},
        "params": {
            "a": {"kind": "enum", "values": ["p", "q"], "default": "p"},
            "b": {"kind": "enum", "values": ["r", "s"], "default": "r"},
        },
        "template": [{"when": "a=p & b!=s", "code": "{out.stat} = 1"}],
    }
    spec = spec_from_dict(
        {**base, "checks": [{"when": "a=q", "require": ["b=s"], "message": "q needs s."}]}
    )
    assert spec.checks[0].violated({"a": "q", "b": "r"})
    assert not spec.checks[0].violated({"a": "q", "b": "s"})
    assert not spec.checks[0].violated({"a": "p", "b": "r"})
    assert "checks" not in spec.to_json()  # the palette's schema is unchanged
    with pytest.raises(RegistryError, match="check names unknown param 'c'"):
        spec_from_dict({**base, "checks": [{"when": "c=1", "message": "m"}]})
    with pytest.raises(RegistryError, match="a check needs a 'message'"):
        spec_from_dict({**base, "checks": [{"when": "a=q"}]})
    with pytest.raises(RegistryError, match="error or warning"):
        spec_from_dict({**base, "checks": [{"when": "a=q", "message": "m", "severity": "info"}]})
    with pytest.raises(RegistryError, match="template 'when' names unknown param 'c'"):
        spec_from_dict({**base, "template": [{"when": "a=p & c=1", "code": "x"}]})


def test_a_post_hoc_test_must_follow_the_test_it_belongs_to(questionnaire_doc):
    def issues(node_type, params):
        return [
            (i.severity, i.code, i.message) for i in _one(node_type, params, questionnaire_doc)[1]
        ]

    means = {"y": "age", "by": "region"}
    assert issues("analyze.means", {**means, "method": "anova", "posthoc": "tukey"}) == []
    assert issues("analyze.means", {**means, "posthoc": "tukey"}) == [
        (
            "error",
            "PARAM_CONFLICT",
            "n: Tukey's HSD follows a one-way ANOVA — set Test to anova, or Post-hoc to none.",
        )
    ]
    assert issues("analyze.means", {**means, "method": "anova", "posthoc": "games_howell"})[0][
        2
    ].startswith("n: Games-Howell follows Welch's ANOVA")
    assert issues("analyze.means", {**means, "method": "welch", "posthoc": "dunn"})[0][
        2
    ].startswith("n: Dunn's test follows Kruskal-Wallis")
    assert issues("analyze.means", {**means, "test": False, "method": "welch"}) == [
        ("warning", "PARAM_CONFLICT", "n: Test is not run while Significance test is off.")
    ]
    groups = {"y": "satisfaction", "group": "region"}
    assert issues("analyze.compare_groups", {**groups, "posthoc": "dunn"}) == []
    assert issues("analyze.compare_groups", {**groups, "test": "kruskal", "posthoc": "dunn"}) == []
    assert issues("analyze.compare_groups", {**groups, "test": "mannwhitney", "posthoc": "dunn"})[
        0
    ][:2] == ("error", "PARAM_CONFLICT")
    table = {"row": "gender", "col": "region"}
    assert issues("analyze.crosstab", {**table, "method": "fisher"}) == []
    assert issues("analyze.crosstab", {**table, "method": "fisher", "test": False})[0][0] == (
        "warning"
    )
    # A t-test needs what its design compares.
    assert issues("analyze.ttest", {"y": "age"})[0][2].startswith(
        "n: An independent-samples t-test compares two groups"
    )
    assert issues("analyze.ttest", {"y": "age", "kind": "paired"})[0][2].startswith(
        "n: A paired t-test compares two measurements"
    )
    assert issues("analyze.ttest", {"y": "age", "group": "gender", "group_a": 0})[0][2].startswith(
        "n: Name both groups"
    )
    assert issues("analyze.ttest", {"y": "age", "kind": "one_sample", "test_value": 40}) == []
    # A conflict is an error: the flow cannot run.
    flow, _ = _one("analyze.means", {**means, "posthoc": "tukey"}, questionnaire_doc)
    with pytest.raises(FlowError, match="Tukey's HSD follows a one-way ANOVA"):
        resolve_flow(flow, questionnaire=questionnaire_doc)


# ─── existing documents ──────────────────────────────────────────────────────

#: What each node's template rendered before it had a method to choose. A
#: stored flow that never set the new parameters must get exactly this code.
BEFORE = {
    ("analyze.correlation", '{"x": "age", "y": "satisfaction"}'): (
        "n_n = n_src.analysis.spearman('age', 'satisfaction')\n"
    ),
    ("analyze.means", '{"y": "age", "by": "region", "test": false}'): (
        "n_n_table = n_src.report.means('age', by='region', test=False)\n"
        "n_n_stat = n_n_table.stats\n"
    ),
    ("analyze.crosstab", '{"row": "gender", "col": "region", "pct": "row"}'): (
        "n_n_table = n_src.report.crosstab('gender', 'region', pct='row', test=True)\n"
        "n_n_stat = n_n_table.stats\n"
    ),
    ("analyze.compare_groups", '{"y": "satisfaction", "group": "region", "test": "kruskal"}'): (
        "n_n = n_src.analysis.kruskal('satisfaction', 'region')\n"
    ),
    ("analyze.compare_groups", '{"y": "satisfaction", "group": "region"}'): (
        "_groups = n_src.frame['region'].dropna().nunique()\n"
        "n_n = (\n"
        "    n_src.analysis.mannwhitney('satisfaction', 'region')\n"
        "    if _groups == 2\n"
        "    else n_src.analysis.kruskal('satisfaction', 'region')\n"
        ")\n"
    ),
}


@pytest.mark.parametrize(("node_type", "params"), list(BEFORE))
def test_a_stored_flow_renders_the_code_it_always_did(node_type, params, questionnaire_doc):
    flow, issues = _one(node_type, json.loads(params), questionnaire_doc)
    assert issues == []
    graph = resolve_flow(flow, questionnaire=questionnaire_doc)
    assert render_node(graph, "n") == BEFORE[(node_type, params)]


# ─── a flow with every new option ────────────────────────────────────────────

NODES = [
    ("src", "source.responses", {}),
    ("apply", "prepare.apply_weight", {"column": "w"}),
    ("pearson", "analyze.correlation", {"x": "age", "y": "trust_acme", "method": "pearson"}),
    ("kendall", "analyze.correlation", {"x": "age", "y": "trust_acme", "method": "kendall"}),
    (
        "matrix",
        "analyze.correlation_matrix",
        {"items": ["age", "trust_acme", "trust_globex", "satisfaction"], "adjust": "holm"},
    ),
    ("tt", "analyze.ttest", {"y": "age", "group": "gender", "group_a": 1, "group_b": 2}),
    ("paired", "analyze.ttest", {"kind": "paired", "y": "trust_acme", "y2": "trust_globex"}),
    ("one", "analyze.ttest", {"kind": "one_sample", "y": "satisfaction", "test_value": 3}),
    ("anova", "analyze.means", {"y": "age", "by": "region", "method": "anova", "posthoc": "tukey"}),
    ("dunn", "analyze.compare_groups", {"y": "age", "group": "region", "posthoc": "dunn"}),
    ("fisher", "analyze.crosstab", {"row": "gender", "col": "region", "method": "fisher"}),
    ("section", "output.report_section", {"heading": "Tests"}),
]


def _responses(survey) -> SurveyData:
    simulated = survey.simulate(n=160, seed=11)
    frame = simulated.frame.assign(w=np.random.default_rng(2).uniform(0.5, 2.0, 160))
    return SurveyData(frame=frame, variables=simulated.variables, questionnaire=survey)


def _stats_flow():
    edges = [("src", "data", "apply", "data")]
    edges += [("apply", "data", node, "data") for node, _, _ in NODES[2:-1]]
    edges += [(node, "table", "section", "items") for node in ("matrix", "tt", "anova", "fisher")]
    return _flow(NODES, edges)


def test_the_statistics_nodes_check_generate_and_run(questionnaire_doc, survey, tmp_path):
    flow = _stats_flow()
    assert check_flow(flow, questionnaire=questionnaire_doc) == []

    code = generate_flow(flow, questionnaire_doc)
    compile(code, "stats.py", "exec")
    from siamang.codegen.format import ruff_command

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
    assert 'n_pearson = n_apply.analysis.correlation("age", "trust_acme", method="pearson")' in code
    assert 'method="anova", posthoc="tukey", adjust="holm"' in code

    data = _responses(survey)
    result = FlowRunner(flow, questionnaire=survey, questionnaire_document=questionnaire_doc).run(
        sources={"src": data}, cwd=tmp_path
    )
    assert result.ok
    unweighted = "unweighted (the weight 'w' is not applied)"
    pearson = result.output("pearson")
    assert pearson["method"] == "Pearson" and pearson["weight"] == "w"
    assert pearson["n_effective"] < pearson["n"]
    assert "Refused" in pearson["missing_codes"]  # trust_acme's 9s are not answers
    assert result.output("kendall")["weight"] == unweighted and "tau" in result.output("kendall")
    matrix = result.output("matrix", "stat")
    assert matrix["p adjustment"] == "Holm, over 6 pairs" and matrix["Weight"] == unweighted
    assert result.output("tt", "stat")["Test"] == "Welch's t-test (unequal variances)"
    assert result.output("tt", "stat")["Weight"] == unweighted
    assert result.output("paired", "stat")["Test"] == "Paired t-test"
    assert result.output("one", "stat")["Test value"] == 3.0
    anova = result.output("anova", "stat")
    assert anova["Test"] == "One-way ANOVA" and anova["Post-hoc"].startswith("Tukey HSD: ")
    assert result.output("anova", "table").posthoc_table is not None
    dunn = result.output("dunn")
    assert dunn["weight"] == unweighted
    assert dunn["test"] == "Kruskal-Wallis H" and dunn["posthoc"] == "Dunn's test (Holm)"
    assert set(dunn) >= {"Capital vs North", "Capital vs South", "North vs South"}
    assert result.output("fisher", "stat")["Test"] == "Fisher-Freeman-Halton exact test"
    report = result.output("section").to_markdown()
    assert "**Post-hoc: Tukey HSD**" in report and "Welch's t-test" in report


def test_the_new_nodes_are_in_the_palette_and_say_what_the_weight_does():
    registry = default_registry()
    for node_type in ("analyze.correlation_matrix", "analyze.ttest"):
        spec = registry.get(node_type)
        assert spec.outputs == {"table": "Table", "stat": "Stat"}
        assert spec.to_json()["params"]
    help_text = registry.get("prepare.apply_weight").params["column"].help
    weighted, unweighted = help_text.split("Unweighted, and saying so:")
    assert "Correlation and Correlation matrix with Pearson" in weighted
    assert (
        "t-test" in unweighted and "Correlation and Correlation matrix with Spearman" in unweighted
    )


UNSET = [
    # A field cleared in Studio is stored as [] or ""; another client may store null.
    ("analyze.ttest", {"y": "age", "group": "gender", "group_a": [], "group_b": []}, "table"),
    ("analyze.ttest", {"y": "age", "group": "gender", "group_a": "", "group_b": None}, "table"),
    ("analyze.means", {"y": "age", "by": "region", "posthoc": None}, "table"),
    ("analyze.means", {"y": "age", "by": "region", "method": "", "posthoc": ""}, "table"),
    ("analyze.crosstab", {"row": "region", "col": "gender", "method": None}, "table"),
    ("analyze.compare_groups", {"y": "age", "group": "region", "posthoc": None}, "stat"),
    ("analyze.correlation", {"x": "age", "y": "satisfaction", "method": ""}, "stat"),
]


@pytest.mark.parametrize(("node_type", "params", "port"), UNSET)
def test_a_parameter_stored_empty_is_its_default_in_the_check_and_the_run(
    node_type, params, port, questionnaire_doc, survey
):
    """check_flow read null, "" and [] as "not set", the template conditions did
    not: the check passed and the run failed with a NameError from a fragment
    no condition chose, or produced no output at all."""

    flow, issues = _one(node_type, params, questionnaire_doc)
    assert issues == []
    graph = resolve_flow(flow, questionnaire=questionnaire_doc)
    stored = {name: value for name, value in params.items() if value not in (None, "", [])}
    clean, _ = _one(node_type, stored, questionnaire_doc)
    assert render_node(graph, "n") == render_node(
        resolve_flow(clean, questionnaire=questionnaire_doc), "n"
    )
    runner = FlowRunner(flow, questionnaire=survey, questionnaire_document=questionnaire_doc)
    data = _responses(survey)
    if node_type == "analyze.ttest":  # three genders and no groups named: said, not a NameError
        with pytest.raises(FlowError, match="Gender has 3 groups"):
            runner.run(sources={"src": data})
        return
    assert runner.run(sources={"src": data}).output("n", port) is not None


def test_the_rules_between_parameters_read_an_empty_value_as_the_default(questionnaire_doc):
    # posthoc "" is none and method null is auto: with the test off, nothing is
    # ignored (null read as a method gave "Test is not run while …" before).
    _, issues = _one(
        "analyze.means",
        {"y": "age", "by": "region", "test": False, "method": None, "posthoc": ""},
        questionnaire_doc,
    )
    assert issues == []
    _, issues = _one(
        "analyze.means",
        {"y": "age", "by": "region", "method": "", "posthoc": "tukey"},
        questionnaire_doc,
    )
    assert [issue.code for issue in issues] == ["PARAM_CONFLICT"]
