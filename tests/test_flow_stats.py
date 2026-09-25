"""The statistics nodes in a flow: Correlation's method, Correlation matrix,
t-test, the tests chosen by hand in Group means, Compare groups and Crosstab,
and the checks that keep a post-hoc test after the test it follows."""

from __future__ import annotations

import itertools
import json
import subprocess
from pathlib import Path

import numpy as np
import pytest

from siamang.data import SurveyData
from siamang.flow import FlowError, FlowRunner, check_flow, default_registry, generate_flow
from siamang.flow.document import resolve_flow, resolved_params
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
    # A subtitle may vary with the parameters: the first variant that holds wins.
    from siamang.flow.template import subtitle

    varied = spec_from_dict({**base, "subtitle": [{"when": "a=q", "text": "q: {b}"}, "{a}, {b}"]})
    assert varied.subtitle == "{a}, {b}" and len(varied.subtitles) == 2
    assert subtitle(varied, {"a": "q", "b": "s"}) == "q: s"
    assert subtitle(varied, {"a": "p", "b": "s"}) == "p, s"
    with pytest.raises(RegistryError, match="subtitle 'when' names unknown param 'c'"):
        spec_from_dict({**base, "subtitle": [{"when": "c=1", "text": "x"}]})
    with pytest.raises(RegistryError, match="subtitles must be strings or"):
        spec_from_dict({**base, "subtitle": [{"text": "no condition"}]})


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


def _reads(node_type, name, params):
    spec = default_registry().get(node_type)
    return spec.reads(name, resolved_params(spec, params))


def test_a_node_reads_a_parameter_only_under_the_choices_that_write_it():
    # The t-test's designs: Groups and its codes for two groups of respondents,
    # Second measurement for a paired one, Test value for one sample.
    for name in ("group", "group_a", "group_b", "variances"):
        assert _reads("analyze.ttest", name, {})  # independent is the default
        assert not _reads("analyze.ttest", name, {"kind": "paired"})
        assert not _reads("analyze.ttest", name, {"kind": "one_sample"})
    assert _reads("analyze.ttest", "y2", {"kind": "paired"})
    assert not _reads("analyze.ttest", "y2", {})
    # Group B is read whether or not Group A is filled in: that is not a choice.
    assert _reads("analyze.ttest", "group_b", {"group_a": None})
    assert _reads("analyze.ttest", "y", {"kind": "paired"})  # required: always
    # Dunn's adjustment only with Dunn; Tukey and Games-Howell allow for the pairs.
    assert _reads("analyze.means", "adjust", {"method": "kruskal", "posthoc": "dunn"})
    assert not _reads("analyze.means", "adjust", {"method": "anova", "posthoc": "tukey"})
    assert not _reads("analyze.means", "adjust", {"method": "welch"})
    assert not _reads("analyze.means", "adjust", {})
    # Paired tests: each test is given what it reads.
    assert _reads("analyze.paired", "yes_codes", {"test": "mcnemar"})
    assert not _reads("analyze.paired", "yes_codes", {"test": "wilcoxon"})
    assert not _reads("analyze.paired", "zeros", {"test": "mcnemar"})
    for test in ("auto", "wilcoxon", "friedman"):
        assert _reads("analyze.paired", "zeros", {"test": test})
    assert _reads("analyze.paired", "posthoc", {"test": "friedman"})
    assert _reads("analyze.paired", "posthoc", {})  # auto is Friedman for three or more
    assert not _reads("analyze.paired", "posthoc", {"test": "mcnemar"})
    assert not _reads("analyze.paired", "posthoc", {"test": "wilcoxon"})
    for test in ("auto", "wilcoxon", "mcnemar", "friedman"):
        assert _reads("analyze.paired", "p_value", {"test": test})
    # Factor analysis: the score prefix with scores, the seed with parallel analysis.
    assert _reads("analyze.factor", "into", {"scores": True})
    assert not _reads("analyze.factor", "into", {})
    assert _reads("analyze.factor", "seed", {"criterion": "parallel"})
    assert not _reads("analyze.factor", "seed", {})
    assert _reads("analyze.factor", "criterion", {"n_factors": 2})


def _sentinel(param):
    return {
        "variable": "zz_other",
        "variables": ["zz_other"],
        "json": 12345,
        "float": 0.123,
        "int": 7,
        "bool": not bool(param.default),
        "string": "zz",
        "path": "zz.csv",
        "mapping": {"1": 2},
    }.get(param.kind, "zz")


def test_a_parameter_the_node_does_not_read_never_changes_its_code():
    """What makes leaving a value unchecked safe: with the choices under which
    the node does not read a parameter, no value of it changes the code."""
    from siamang.flow.document import Edge, FlowGraph

    registry = default_registry()
    source = registry.get("source.simulated")
    checked = 0
    for spec in registry:
        choices = sorted(
            {
                term.replace("!=", "=").split("=", 1)[0].strip()
                for fragment in spec.template
                if fragment.when
                for term in fragment.when.split("&")
                if "=" in term
                and spec.params[term.replace("!=", "=").split("=", 1)[0].strip()].kind
                in ("enum", "bool")
            }
        )
        if not choices:
            continue
        values = [
            list(spec.params[c].values) if spec.params[c].kind == "enum" else [True, False]
            for c in choices
        ]
        required = {n: _sentinel(p) for n, p in spec.params.items() if p.required}

        def render(params, spec=spec):
            nodes = {
                "src": {"id": "src", "type": "source.simulated"},
                "n": {"id": "n", "type": spec.type, "params": params},
            }
            graph = FlowGraph(
                document={"schema_version": "1.0", "name": "t", "nodes": list(nodes.values())},
                registry=registry,
                nodes=nodes,
                specs={"src": source, "n": spec},
                edges=[Edge("src", "data", "n", port) for port in spec.inputs],
                order=["src", "n"],
                inputs={"src": {}, "n": {port: [("src", "data")] for port in spec.inputs}},
            )
            return render_node(graph, "n")

        for combination in itertools.product(*values):
            base = {**required, **dict(zip(choices, combination, strict=True))}
            resolved = resolved_params(spec, base)
            for name, param in spec.params.items():
                if name in choices or spec.reads(name, resolved):
                    continue
                assert render({**base, name: _sentinel(param)}) == render(base), (
                    spec.type,
                    name,
                    combination,
                )
                checked += 1
    assert checked > 40  # the t-test's designs, Dunn's adjustment, the paired tests, TURF…


def test_a_value_the_node_does_not_read_is_not_checked(questionnaire_doc, survey, tmp_path):
    """A paired t-test that still holds a Group A, or a Groups naming a variable
    that has since gone, is not an error: the run ignores those values, and a
    builder that hides the fields would report an error nobody can see."""

    def errors(node_type, params):
        found = _one(node_type, params, questionnaire_doc)[1]
        return [(i.code, i.message) for i in found if i.severity == "error"]

    paired = {"kind": "paired", "y": "trust_acme", "y2": "trust_globex"}
    assert errors("analyze.ttest", {**paired, "group": "gender", "group_a": 1}) == []
    assert errors("analyze.ttest", {**paired, "group": "age_band", "variances": "pooled"}) == []
    assert errors("analyze.ttest", {"kind": "one_sample", "y": "satisfaction", "group_b": 2}) == []
    # Read, they are checked as before.
    assert errors("analyze.ttest", {"y": "age", "group": "age_band"}) == [
        ("UNKNOWN_VARIABLE", "Parameter 'group' of n names unknown variable 'age_band'.")
    ]
    assert errors("analyze.ttest", {"y": "age", "group": "gender", "group_b": 2})[0][0] == (
        "PARAM_CONFLICT"
    )
    assert errors("analyze.means", {"y": "age", "by": "region", "adjust": "sidak"}) == []
    assert (
        errors(
            "analyze.means",
            {"y": "age", "by": "region", "method": "kruskal", "posthoc": "dunn", "adjust": "sidak"},
        )[0][0]
        == "PARAM_INVALID"
    )
    # A warning that a value is ignored is still given: that is what it is for.
    warnings = [
        i.message
        for i in _one(
            "analyze.paired",
            {"variables": ["trust_acme", "trust_globex"], "test": "wilcoxon", "yes_codes": 5},
            questionnaire_doc,
        )[1]
    ]
    assert warnings == [
        "n: Counts as yes is read only by McNemar — set Test to mcnemar, or clear it."
    ]
    # And the flow runs, the stale values left out of the code.
    flow = _flow(
        [
            ("src", "source.responses", {}),
            ("n", "analyze.ttest", {**paired, "group": "age_band", "group_a": 1}),
        ],
        [("src", "data", "n", "data")],
    )
    code = generate_flow(flow, questionnaire=questionnaire_doc)
    assert "age_band" not in code and 'kind="paired"' in code
    result = FlowRunner(flow, questionnaire=survey).run(
        sources={"src": survey.simulate(n=80, seed=3)}, cwd=tmp_path, raise_on_error=True
    )
    assert result.outputs["n"]["stat"]["Test"].startswith("Paired")


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
    assert 'method="anova", posthoc="tukey")\n' in code  # Dunn's adjustment only with Dunn

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
    # Three genders and no groups named: the check warns before the run refuses.
    warned = ["PARAM_CONFLICT"] if node_type == "analyze.ttest" else []
    assert [i.code for i in issues if i.severity == "warning"] == warned
    assert [i for i in issues if i.severity == "error"] == []
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


def test_a_section_captions_each_output_of_a_node_on_its_own(questionnaire_doc):
    """A factor analysis's loadings, variance and statistics in one section each
    take their own caption and size (`fa.loadings`), and the node's own key still
    answers for an output without one — so a stored section renders as before."""
    items = ["age", "trust_acme", "trust_globex", "satisfaction"]
    flow = _flow(
        [
            ("src", "source.responses", {}),
            ("fa", "analyze.factor", {"items": items, "n_factors": 1}),
            (
                "sec",
                "output.report_section",
                {
                    "captions": {"fa.loadings": "Table 5. Loadings", "fa": "Factor analysis"},
                    "layout": {"fa.variance": {"width": "60%"}},
                },
            ),
        ],
        [
            ("src", "data", "fa", "data"),
            ("fa", "loadings", "sec", "items"),
            ("fa", "variance", "sec", "items"),
            ("fa", "stat", "sec", "items"),
        ],
    )
    assert check_flow(flow, questionnaire=questionnaire_doc) == []
    code = render_node(resolve_flow(flow, questionnaire=questionnaire_doc), "sec")
    assert "['Table 5. Loadings', 'Factor analysis', 'Factor analysis']" in code
    assert "[{}, {'width': '60%'}, {}]" in code


def test_what_the_parameters_settle_is_checked_before_the_run(questionnaire_doc):
    """How many variables a paired test compares is in the flow, so a McNemar of
    three or a Friedman of two is an error of the check — in the words the run
    would refuse it with — not a surprise in the sandbox. A t-test of two groups
    whose Groups has three answers and none named is a warning: a filter
    upstream may leave only two in the data."""

    def issues(node_type, params):
        return [(i.severity, i.message) for i in _one(node_type, params, questionnaire_doc)[1]]

    three = ["trust_acme", "trust_globex", "satisfaction"]
    assert issues("analyze.paired", {"variables": three, "test": "mcnemar"}) == [
        ("error", "n: McNemar compares exactly two variables; 3 were given.")
    ]
    assert issues("analyze.paired", {"variables": three, "test": "wilcoxon"}) == [
        (
            "error",
            "n: Wilcoxon signed-rank compares exactly two variables; 3 were given. For three"
            " or more, use Friedman.",
        )
    ]
    assert issues("analyze.paired", {"variables": three[:2], "test": "friedman"}) == [
        (
            "error",
            "n: Friedman's test compares three or more variables; 2 were given. For two, use"
            " Wilcoxon signed-rank (or McNemar for yes/no).",
        )
    ]
    assert issues("analyze.paired", {"variables": three[:1]})[0][1].startswith(
        "n: Paired tests compare two or more variables"
    )
    assert issues("analyze.paired", {"variables": three}) == []  # auto: Friedman
    assert issues("analyze.paired", {"variables": three[:2], "test": "mcnemar"}) == []

    assert issues("analyze.ttest", {"y": "age", "group": "gender"}) == [
        (
            "warning",
            "n: Gender has 3 answers (1 = Male, 2 = Female, 3 = Other); a t-test compares two"
            " — name them in Group A and Group B, unless the data this node reads holds only"
            " two of them.",
        )
    ]
    assert (
        issues("analyze.ttest", {"y": "age", "group": "gender", "group_a": 1, "group_b": 2}) == []
    )
    # The codebook's missing codes are not answers: No trust … Full, not Refused.
    assert (
        "has 5 answers (1 = No trust"
        in issues("analyze.ttest", {"y": "age", "group": "trust_acme"})[0][1]
    )
    assert (
        issues(
            "analyze.ttest", {"kind": "paired", "y": "age", "y2": "trust_acme", "group": "gender"}
        )
        == []
    )


def test_a_made_variable_of_the_wrong_scale_is_warned(questionnaire_doc):
    """A Crosstab of a factor score (interval) ran with one row per distinct
    float and nothing said so: made variables' scales were not checked, only the
    codebook's. They are now — as a warning, so a flow saved before runs on."""

    def issues(nodes):
        flow = _flow(
            [("src", "source.responses", {}), *nodes],
            [("src", "data", nodes[0][0], "data")]
            + [(a[0], "data", b[0], "data") for a, b in zip(nodes, nodes[1:], strict=False)],
        )
        return [
            (i.severity, i.code, i.message)
            for i in check_flow(flow, questionnaire=questionnaire_doc)
        ]

    items = ["trust_acme", "trust_globex", "satisfaction", "age"]
    factor_then = [("fa", "analyze.factor", {"items": items, "n_factors": 1, "scores": True})]
    assert issues(
        [*factor_then, ("xt", "analyze.crosstab", {"row": "factor_1", "col": "gender"})]
    ) == [
        (
            "warning",
            "VARIABLE_SCALE",
            "Parameter 'row' of xt: 'factor_1' is interval (as the node that makes it gives it),"
            " expected nominal | ordinal.",
        )
    ]
    assert issues([*factor_then, ("m", "analyze.means", {"y": "factor_1", "by": "gender"})]) == []
    derive = {"name": "young", "formula": "if age < 30 then 1 else 2"}
    assert issues(
        [
            ("d", "prepare.derive", derive),
            ("xt", "analyze.crosstab", {"row": "young", "col": "gender"}),
        ]
    )[0][:2] == ("warning", "VARIABLE_SCALE")  # a Derive is ratio unless told otherwise
    assert (
        issues(
            [
                ("d", "prepare.derive", {**derive, "scale": "nominal"}),
                ("xt", "analyze.crosstab", {"row": "young", "col": "gender"}),
            ]
        )
        == []
    )
    bands = {"variable": "age", "bins": [18, 30, 65], "into": "age_band"}
    assert (
        issues(
            [
                ("b", "prepare.bands", bands),
                ("t", "analyze.ttest", {"y": "age", "group": "age_band"}),
            ]
        )
        == []
    )
    # A codebook variable of the wrong scale is still an error.
    assert issues([("xt", "analyze.crosstab", {"row": "age", "col": "gender"})])[0][:2] == (
        "error",
        "VARIABLE_SCALE",
    )
