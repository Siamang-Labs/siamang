"""siamang.flow — registry, documents, runner and code generation."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from siamang.codegen import generate_questionnaire
from siamang.data import SurveyData
from siamang.flow import (
    FlowError,
    FlowRunner,
    check_flow,
    default_registry,
    generate_flow,
    live,
    node_order,
    render_condition,
    resolve_flow,
    validate_flow,
)
from siamang.flow.document import Edge
from siamang.flow.registry import Registry, RegistryError, spec_from_dict
from siamang.flow.template import render_node
from siamang.io import write_snapshot
from siamang.model import from_document, loads

ROOT = Path(__file__).resolve().parent
DOCUMENTS = ROOT / "documents"
HAS_MPL = importlib.util.find_spec("matplotlib") is not None
HAS_PARQUET = importlib.util.find_spec("pyarrow") is not None


@pytest.fixture(scope="module")
def questionnaire_doc():
    return loads((DOCUMENTS / "brand_awareness.questionnaire.json").read_text("utf-8"))


@pytest.fixture(scope="module")
def survey(questionnaire_doc):
    return from_document(questionnaire_doc).survey


@pytest.fixture(scope="module")
def responses(survey) -> SurveyData:
    """Simulated responses with the collector's columns (respondent_id, duration_s)."""

    simulated = survey.simulate(n=300, seed=7)
    rng = np.random.default_rng(1)
    frame = simulated.frame.copy()
    frame["respondent_id"] = [f"r{i % 280}" for i in range(len(frame))]  # a few resumes
    frame["submitted_at"] = range(len(frame))
    frame["duration_s"] = rng.integers(30, 400, len(frame))
    return SurveyData(frame=frame, variables=simulated.variables, questionnaire=survey)


@pytest.fixture(scope="module")
def flow_doc():
    return json.loads((DOCUMENTS / "satisfaction.flow.json").read_text("utf-8"))


# ─── registry ────────────────────────────────────────────────────────────────


def test_registry_loads_every_node_and_serializes():
    registry = default_registry()
    assert len(registry) >= 25
    categories = registry.by_category()
    assert all(categories[c] for c in ("source", "prepare", "analyze", "visualize", "output"))
    payload = json.loads(registry.dumps())
    assert {item["type"] for item in payload} == set(registry.types())
    crosstab = registry.get("analyze.crosstab")
    assert crosstab.outputs == {"table": "Table", "stat": "Stat"}
    assert crosstab.params["pct"].values == ("none", "row", "col", "total")
    assert crosstab.to_json()["params"]["row"] == {
        "kind": "variable",
        "required": True,
        "scales": ["nominal", "ordinal"],
        "label": "Rows",
    }
    with pytest.raises(RegistryError, match="Unknown node type"):
        registry.get("analyze.nope")


def test_every_template_placeholder_is_declared():
    """A template may only name its own ports and parameters."""

    import re

    pattern = re.compile(r"\{(in|out)\.([a-z_]+)\}|\{([a-z_]+)!r\}")
    for spec in default_registry():
        for fragment in spec.template:
            for kind, port, param in pattern.findall(fragment.code):
                if kind == "in":
                    assert port in spec.inputs, (spec.type, port)
                elif kind == "out":
                    assert port in spec.outputs, (spec.type, port)
                else:
                    assert param in spec.params or param == "node", (spec.type, param)


def test_spec_validation_rejects_bad_specifications():
    base = {
        "type": "analyze.x",
        "category": "analyze",
        "title": "X",
        "inputs": {"data": "SurveyData"},
        "outputs": {"table": "Table"},
        "template": "{out.table} = {in.data}",
    }
    assert spec_from_dict(base).type == "analyze.x"
    with pytest.raises(RegistryError, match="must start with its category"):
        spec_from_dict({**base, "type": "prepare.x"})
    with pytest.raises(RegistryError, match="unknown type"):
        spec_from_dict({**base, "outputs": {"table": "Blob"}})
    with pytest.raises(RegistryError, match="unknown kind"):
        spec_from_dict({**base, "params": {"p": {"kind": "weird"}}})
    with pytest.raises(RegistryError, match="needs 'values'"):
        spec_from_dict({**base, "params": {"p": {"kind": "enum"}}})
    with pytest.raises(RegistryError, match="unknown param"):
        spec_from_dict({**base, "template": [{"when": "nope", "code": "x"}]})
    with pytest.raises(RegistryError, match="Duplicate"):
        Registry([spec_from_dict(base), spec_from_dict(base)])


# ─── documents ───────────────────────────────────────────────────────────────


def test_example_flow_is_valid(flow_doc, questionnaire_doc):
    validate_flow(flow_doc)
    assert check_flow(flow_doc, questionnaire=questionnaire_doc) == []
    graph = resolve_flow(flow_doc, questionnaire=questionnaire_doc)
    assert graph.order[0] == "src" and graph.order[-1] == "save"
    assert graph.order.index("section") > graph.order.index("means")
    assert graph.params("dedup") == {
        "key": "respondent_id",
        "order_by": "submitted_at",
        "keep": "last",
    }
    assert graph.inputs["section"]["items"] == [
        ("xtab", "table"),
        ("bar", "chart"),
        ("means", "table"),
    ]


def test_node_order_is_stable_by_depth_position_and_id():
    nodes = {
        "b": {"type": "x", "position": [0, 1]},
        "a": {"type": "x", "position": [0, 2]},
        "c": {"type": "x", "position": [1, 0]},
        "d": {"type": "x", "position": [1, 0]},
    }
    edges = [Edge("a", "o", "c", "i"), Edge("b", "o", "d", "i"), Edge("a", "o", "d", "i")]
    assert node_order(nodes, edges) == ["b", "a", "c", "d"]
    with pytest.raises(FlowError, match="cycle"):
        node_order(nodes, edges + [Edge("d", "o", "a", "i")])


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


def test_check_flow_reports_graph_problems(questionnaire_doc):
    def codes(document):
        return sorted(
            {issue.code for issue in check_flow(document, questionnaire=questionnaire_doc)}
        )

    sim = ("sim", "source.simulated", {})
    assert (
        codes(
            _flow(
                [sim, ("f", "analyze.freq", {"variable": "region"})], [("sim", "data", "f", "data")]
            )
        )
        == []
    )
    assert codes(_flow([("x", "analyze.nope", {})], [])) == ["UNKNOWN_NODE_TYPE"]
    assert "PARAM_REQUIRED" in codes(
        _flow([sim, ("f", "analyze.freq", {})], [("sim", "data", "f", "data")])
    )
    assert "UNKNOWN_PARAM" in codes(
        _flow(
            [sim, ("f", "analyze.freq", {"variable": "region", "zzz": 1})],
            [("sim", "data", "f", "data")],
        )
    )
    assert "UNKNOWN_VARIABLE" in codes(
        _flow([sim, ("f", "analyze.freq", {"variable": "nope"})], [("sim", "data", "f", "data")])
    )
    assert "VARIABLE_SCALE" in codes(
        _flow(
            [sim, ("x", "analyze.crosstab", {"row": "age", "col": "region"})],
            [("sim", "data", "x", "data")],
        )
    )
    assert "PARAM_INVALID" in codes(
        _flow(
            [sim, ("f", "analyze.freq", {"variable": "region", "sort": "up"})],
            [("sim", "data", "f", "data")],
        )
    )
    assert "INPUT_NOT_CONNECTED" in codes(
        _flow([("f", "analyze.freq", {"variable": "region"})], [])
    )
    assert "PORT_TYPE_MISMATCH" in codes(
        _flow(
            [
                sim,
                ("f", "analyze.freq", {"variable": "region"}),
                ("g", "analyze.freq", {"variable": "region"}),
            ],
            [("sim", "data", "f", "data"), ("f", "table", "g", "data")],
        )
    )
    assert "UNKNOWN_PORT" in codes(
        _flow([sim, ("f", "analyze.freq", {"variable": "region"})], [("sim", "rows", "f", "data")])
    )
    assert "INPUT_CONNECTED_TWICE" in codes(
        _flow(
            [sim, ("s2", "source.simulated", {}), ("f", "analyze.freq", {"variable": "region"})],
            [("sim", "data", "f", "data"), ("s2", "data", "f", "data")],
        )
    )
    assert "CYCLE" in codes(
        _flow(
            [sim, ("a", "prepare.apply_weight", {}), ("b", "prepare.apply_weight", {})],
            [("a", "data", "b", "data"), ("b", "data", "a", "data")],
        )
    )
    # Variables created upstream are known downstream; raw conditions are refused.
    created = _flow(
        [
            sim,
            ("i", "prepare.index", {"name": "trust_idx", "items": ["trust_acme", "trust_globex"]}),
            ("m", "analyze.means", {"y": "trust_idx", "by": "region"}),
        ],
        [("sim", "data", "i", "data"), ("i", "data", "m", "data")],
    )
    assert codes(created) == []
    raw = _flow(
        [sim, ("f", "prepare.filter", {"condition": {"type": "raw", "text": "{age} > 1"}})],
        [("sim", "data", "f", "data")],
    )
    assert "PARAM_INVALID" in codes(raw)
    with pytest.raises(FlowError, match="schema_version"):
        validate_flow({"name": "x", "nodes": []})
    with pytest.raises(FlowError, match="nodes/0/id"):
        validate_flow(
            {
                "schema_version": "1.0",
                "name": "x",
                "nodes": [{"id": "Bad Id", "type": "source.simulated"}],
            }
        )


def test_render_condition():
    cond = {
        "type": "expression", "op": "and",
        "left": {"type": "expression", "op": ">=", "left": {"type": "var", "name": "age"}, "right": 18},
        "right": {"type": "expression", "op": "not",
                  "left": {"type": "expression", "op": "in", "left": {"type": "var", "name": "region"}, "right": [1, 2]}},
    }  # fmt: skip
    assert (
        render_condition(cond)
        == "sg.AND(sg.compare('age', '>=', 18), sg.NOT(sg.compare('region', 'in', [1, 2])))"
    )
    import siamang as sg

    expression = eval(render_condition(cond), {"sg": sg})  # noqa: S307 - our own rendering
    assert expression.evaluate({"age": 30, "region": 3}) is True
    assert expression.evaluate({"age": 30, "region": 1}) is False
    with pytest.raises(FlowError, match="raw"):
        render_condition({"type": "raw", "text": "x"})


# ─── runner ──────────────────────────────────────────────────────────────────


@pytest.mark.skipif(not HAS_MPL, reason="matplotlib")
def test_runner_executes_the_example_flow(flow_doc, questionnaire_doc, survey, responses, tmp_path):
    runner = FlowRunner(flow_doc, questionnaire=survey, questionnaire_document=questionnaire_doc)
    result = runner.run(sources={"src": responses}, cwd=tmp_path)
    assert result.ok and [run.state for run in result.runs] == ["ok"] * len(result.order)
    table = result.output("xtab", "table").to_frame()
    assert "Total" in table.columns and len(table) > 2
    assert set(result.output("xtab", "stat")) >= {"χ²", "p", "N"}
    assert result.output("apply").weight == "weight"
    assert (tmp_path / "outputs" / "satisfaction_by_region.md").is_file()
    assert (tmp_path / "outputs" / "satisfaction_by_region.html").is_file()
    tiles = {tile.node: tile for tile in result.tiles}
    assert tiles["tile_n"].kind == "number" and tiles["tile_n"].value == len(
        result.output("speed").frame
    )
    assert tiles["tile_x"].value is result.output("xtab", "table")
    # Dedup collapsed the resumed respondents.
    assert len(result.output("dedup").frame) == 280
    # A run up to a node executes only its ancestors.
    partial = runner.run(sources={"src": responses}, cwd=tmp_path, upto="rake")
    assert partial.order == ["src", "dedup", "speed", "rake"]


def test_runner_needs_data_for_platform_sources_and_reports_errors(flow_doc, survey, tmp_path):
    runner = FlowRunner(flow_doc, questionnaire=survey)
    with pytest.raises(FlowError, match="needs data"):
        runner.run(cwd=tmp_path)


def test_runner_with_a_snapshot_path_and_a_fake_db(questionnaire_doc, survey, responses, tmp_path):
    snapshot = write_snapshot(responses, tmp_path / "responses.csv")
    flow = _flow(
        [
            ("src", "source.table", {"table": "clean"}),
            ("f", "analyze.freq", {"variable": "region"}),
            ("w", "output.write_table", {"name": "freq_out"}),
        ],
        [("src", "data", "f", "data"), ("src", "data", "w", "data")],
    )
    runner = FlowRunner(flow, questionnaire=survey, questionnaire_document=questionnaire_doc)
    result = runner.run(sources={"src": snapshot}, cwd=tmp_path)
    assert result.output("f").to_frame()["N"].iloc[-1] == len(responses.frame)
    assert [run.state for run in result.runs] == ["ok", "ok", "skipped"]

    written = {}

    class FakeDb:
        def as_survey_data(self, table, **kwargs):
            return responses

        def write_table(self, name, frame, if_exists):
            written[name] = (len(frame), if_exists)

    result = runner.run(db=FakeDb(), cwd=tmp_path)
    assert result.ok and written == {"freq_out": (len(responses.frame), "replace")}

    bad = _flow(
        [("sim", "source.simulated", {}), ("m", "analyze.correlation", {"x": "nope", "y": "age"})],
        [("sim", "data", "m", "data")],
    )
    outcome = FlowRunner(bad, questionnaire=survey).run(cwd=tmp_path, raise_on_error=False)
    assert not outcome.ok and outcome.runs[-1].state == "error"


@pytest.mark.skipif(not HAS_MPL, reason="matplotlib")
def test_every_prepare_analyze_visualize_node_runs(questionnaire_doc, survey, responses, tmp_path):
    """One flow through most of the registry, so each template is executed at least once."""

    nodes = [
        ("sim", "source.simulated", {"n": 120, "seed": 3}),
        (
            "filt",
            "prepare.filter",
            {
                "condition": {
                    "type": "expression",
                    "op": ">=",
                    "left": {"type": "var", "name": "age"},
                    "right": 18,
                }
            },
        ),
        ("miss", "prepare.missing", {"action": "drop_rows", "variables": ["trust_acme"]}),
        (
            "rec",
            "prepare.recode",
            {
                "variable": "region",
                "mapping": {"1": 1, "2": 2, "3": 2},
                "into": "region2",
                "scale": "nominal",
            },
        ),
        (
            "cell",
            "prepare.cell_weights",
            {"variable": "gender", "targets": {"1": 0.5, "2": 0.5}, "cap": 3},
        ),
        ("apply", "prepare.apply_weight", {}),
        ("idx", "prepare.index", {"name": "trust_idx", "items": ["trust_acme", "trust_globex"]}),
        (
            "qual",
            "prepare.quality",
            {
                "items": ["trust_acme", "trust_globex"],
                "expected": {"gender": 1},
                "mode": "flag",
            },
        ),
        ("expl", "prepare.explode", {"variable": "aware"}),
        (
            "sel",
            "prepare.select",
            {
                "columns": [
                    "age",
                    "region",
                    "gender",
                    "satisfaction",
                    "trust_idx",
                    "region2",
                    "weight",
                    "quality_flags",
                    "quality_score",
                    "aware_1",
                    "aware_2",
                    "aware_3",
                    "aware_99",
                ]
            },
        ),
        ("freq", "analyze.freq", {"variable": "region2", "sort": "freq"}),
        ("corr", "analyze.correlation", {"x": "age", "y": "satisfaction"}),
        ("ci", "analyze.proportion_ci", {"variable": "gender", "value": 1, "weighted": True}),
        ("cmp", "analyze.compare_groups", {"y": "satisfaction", "group": "region2"}),
        (
            "cmp3",
            "analyze.compare_groups",
            {"y": "satisfaction", "group": "region", "test": "kruskal"},
        ),
        ("desc", "analyze.describe", {"mode": "codebook"}),
        ("reg", "analyze.regression", {"y": "satisfaction", "predictors": ["age", "region2"]}),
        ("pca", "analyze.pca", {"items": ["age", "satisfaction", "trust_idx"], "n_components": 2}),
        ("clu", "analyze.cluster", {"items": ["age", "satisfaction"], "k": 2, "into": "segment"}),
        ("rel", "analyze.reliability", {"items": ["age", "satisfaction", "trust_idx"]}),
        ("box", "visualize.boxplot", {"y": "trust_idx", "by": "region2"}),
        ("heat", "visualize.heatmap", {"items": ["age", "satisfaction", "trust_idx"]}),
        ("scat", "visualize.scatter", {"x": "age", "y": "satisfaction", "hue": "gender"}),
        (
            "sec",
            "output.report_section",
            {"heading": "Everything", "captions": {"freq": "T1"}, "note": "n."},
        ),
        (
            "save",
            "output.save_report",
            {"title": "All nodes", "path": "outputs/all.md", "toc": True},
        ),
        ("exp", "output.export_file", {"path": "outputs/clean.csv"}),
        ("tile", "output.live_tile", {"kind": "stat", "label": "corr"}),
    ]
    chain = ["sim", "filt", "miss", "rec", "cell", "apply", "idx", "qual", "expl", "sel"]
    edges = [(a, "data", b, "data") for a, b in zip(chain, chain[1:], strict=False)]
    edges += [
        ("sel", "data", n, "data")
        for n in (
            "freq",
            "corr",
            "ci",
            "cmp",
            "cmp3",
            "desc",
            "reg",
            "pca",
            "clu",
            "rel",
            "box",
            "heat",
            "scat",
            "exp",
        )
    ]
    edges += [
        ("freq", "table", "sec", "items"),
        ("corr", "stat", "sec", "items"),
        ("box", "chart", "sec", "items"),
        ("desc", "table", "sec", "items"),
        ("reg", "table", "sec", "items"),
        ("pca", "loadings", "sec", "items"),
        ("clu", "table", "sec", "items"),
        ("rel", "stat", "sec", "items"),
        ("sec", "report", "save", "sections"),
        ("corr", "stat", "tile", "input"),
    ]
    flow = _flow(nodes, edges)
    assert check_flow(flow, questionnaire=questionnaire_doc) == []
    result = FlowRunner(flow, questionnaire=survey, questionnaire_document=questionnaire_doc).run(
        cwd=tmp_path
    )
    assert result.ok
    assert result.output("filt").frame["age"].min() >= 18
    assert "region2" in result.output("rec").frame.columns
    assert result.output("apply").weight == "weight"
    exploded = result.output("expl")
    # The indicators reproduce the list column exactly, and a respondent who
    # answered nothing is missing rather than a row of noes.
    assert [
        sorted(code for code in (1, 2, 3, 99) if row[f"aware_{code}"] == 1)
        for _, row in exploded.frame.head(20).iterrows()
    ] == [sorted(value) for value in exploded.frame["aware"].head(20)]
    assert exploded.variables["aware_1"].label == "Brands heard of (unaided): Acme"
    assert "rho" in result.output("corr")
    assert set(result.output("cmp")) >= {"statistic", "p_value"}
    assert list(result.output("reg", "table")["term"])[:2] == ["(intercept)", "age"]
    assert result.output("reg", "stat")["model"] == "WLS"  # the flow applied a weight
    assert list(result.output("pca", "loadings").columns) == ["item", "PC1", "PC2"]
    assert "segment" in result.output("clu", "data").frame.columns
    assert result.output("clu", "table")["size"].sum() == len(
        result.output("sel").frame.dropna(subset=["age", "satisfaction"])
    )
    assert "alpha" in result.output("rel", "stat")
    assert (tmp_path / "outputs" / "all.md").read_text("utf-8").startswith("# All nodes")
    assert (tmp_path / "outputs" / "clean.csv").is_file()
    assert (tmp_path / "outputs" / "clean.dictionary.json").is_file()
    assert result.tiles[0].kind == "stat" and "rho" in result.tiles[0].value


# ─── code generation ─────────────────────────────────────────────────────────


def _ruff(*args: str, code: str) -> subprocess.CompletedProcess:
    from siamang.codegen.format import ruff_command

    command = ruff_command()
    assert command
    return subprocess.run(
        [*command, *args, "-"], input=code, capture_output=True, text=True, check=False
    )


def test_generated_flow_script_is_clean_deterministic_and_golden(flow_doc, questionnaire_doc):
    code = generate_flow(flow_doc, questionnaire_doc)
    assert code == generate_flow(flow_doc, questionnaire_doc)
    golden = DOCUMENTS / "satisfaction.flow.generated.py"
    assert (
        golden.exists()
    ), "run: siamang codegen tests/documents/satisfaction.flow.json --questionnaire …"
    assert code == golden.read_text("utf-8")
    assert _ruff("format", "--isolated", "--line-length", "100", code=code).stdout == code
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
        "--config",
        'lint.isort.known-first-party = ["survey"]',
        "--config",
        'lint.isort.known-third-party = ["siamang", "siamang_studio"]',
        code=code,
    )
    assert lint.returncode == 0, lint.stdout + lint.stderr
    # Every node is marked, and the platform source has the --data branch.
    for node in flow_doc["nodes"]:
        assert f"# studio: {node['id']}" in code
    assert "if args.data:  # research bundle" in code and "from siamang_studio import db" in code
    assert "from survey.questionnaire import survey" in code
    assert (
        'live.publish("tile_n", kind="number", label="Clean respondents", value=n_speed, metric="rows")'
        in code
    )


@pytest.mark.skipif(not HAS_MPL or not HAS_PARQUET, reason="matplotlib and pyarrow")
def test_generated_script_reproduces_the_runner(
    flow_doc, questionnaire_doc, survey, responses, tmp_path
):
    """The script run from a snapshot writes the same report the runner writes."""

    runner_dir, script_dir = tmp_path / "runner", tmp_path / "script"
    result = FlowRunner(
        flow_doc, questionnaire=survey, questionnaire_document=questionnaire_doc
    ).run(sources={"src": responses}, cwd=runner_dir)
    assert result.ok

    (script_dir / "survey").mkdir(parents=True)
    (script_dir / "survey" / "__init__.py").write_text("", encoding="utf-8")
    (script_dir / "survey" / "questionnaire.py").write_text(
        generate_questionnaire(questionnaire_doc), encoding="utf-8"
    )
    (script_dir / "scripts").mkdir()
    script = script_dir / "scripts" / "satisfaction_by_region.py"
    script.write_text(generate_flow(flow_doc, questionnaire_doc), encoding="utf-8")
    snapshot = write_snapshot(responses, script_dir / "data" / "responses.parquet")
    env = {**os.environ, "PYTHONPATH": str(script_dir), "MPLBACKEND": "Agg"}
    completed = subprocess.run(
        [sys.executable, str(script), "--data", str(snapshot)],
        cwd=script_dir,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    ours = (runner_dir / "outputs" / "satisfaction_by_region.md").read_text("utf-8")
    theirs = (script_dir / "outputs" / "satisfaction_by_region.md").read_text("utf-8")
    assert ours == theirs
    assert "χ²" in ours and "Table 1. Satisfaction × region (%)" in ours


def test_save_report_footer_comes_from_the_environment(
    flow_doc, questionnaire_doc, survey, responses, tmp_path, monkeypatch
):
    """The platform (or a bundle's run.sh) sets SIAMANG_PROVENANCE; the saved
    report ends with that text. Unset, the report is unchanged."""

    monkeypatch.delenv("SIAMANG_PROVENANCE", raising=False)
    plain = FlowRunner(flow_doc, questionnaire=survey, questionnaire_document=questionnaire_doc)
    assert plain.run(sources={"src": responses}, cwd=tmp_path / "plain").ok
    text = (tmp_path / "plain" / "outputs" / "satisfaction_by_region.md").read_text("utf-8")
    assert "Provenance" not in text

    monkeypatch.setenv("SIAMANG_PROVENANCE", "Project `acme/brand`\nSave #17 · siamang 1.4.0")
    stamped = FlowRunner(flow_doc, questionnaire=survey, questionnaire_document=questionnaire_doc)
    assert stamped.run(sources={"src": responses}, cwd=tmp_path / "stamped").ok
    text = (tmp_path / "stamped" / "outputs" / "satisfaction_by_region.md").read_text("utf-8")
    assert text.rstrip().endswith("Save #17 · siamang 1.4.0")
    assert "**Provenance**" in text and "Project `acme/brand`" in text


def test_generate_flow_variants(questionnaire_doc):
    two_sources = _flow(
        [
            ("a", "source.responses", {}),
            ("b", "source.table", {"table": "clean"}),
            ("fa", "analyze.freq", {"variable": "region"}),
            ("fb", "analyze.freq", {"variable": "region"}),
        ],
        [("a", "data", "fa", "data"), ("b", "data", "fb", "data")],
    )
    code = generate_flow(
        two_sources,
        questionnaire_doc,
        header="Studio made this ({schema}).",
        platform_module="siamang_cloud",
    )
    assert "Studio made this (1.0)." in code
    assert '"--data-a"' in code and '"--data-b"' in code
    assert "if args.a_data:" in code and "if args.b_data:" in code
    assert "from siamang_cloud import db" in code
    local_only = _flow(
        [("sim", "source.simulated", {}), ("f", "analyze.freq", {"variable": "region"})],
        [("sim", "data", "f", "data")],
    )
    code = generate_flow(local_only, questionnaire_doc)
    assert "argparse" not in code and "from survey.questionnaire import survey" in code
    with pytest.raises(FlowError, match="Unknown node type"):
        generate_flow(_flow([("x", "analyze.nope", {})], []))


def test_render_node_and_live_capture(flow_doc, questionnaire_doc):
    graph = resolve_flow(flow_doc, questionnaire=questionnaire_doc)
    assert render_node(graph, "apply") == "n_apply = n_rake.with_weight('weight')\n"
    assert render_node(graph, "tile_x").startswith("live.publish('tile_x', kind='table'")
    with live.capture() as tiles:
        live.publish(
            "t",
            kind="number",
            label="n",
            value=SurveyData(frame=__import__("pandas").DataFrame({"a": [1, 2]})),
            metric="rows",
        )
    assert tiles == [live.Tile("t", "number", "n", 2)]
    with pytest.raises(ValueError, match="tile kind"):
        live.publish("t", kind="gauge", label="n", value=1)


def test_cli_flow_commands(flow_doc, questionnaire_doc, responses, tmp_path):
    flow_path = DOCUMENTS / "satisfaction.flow.json"
    q_path = DOCUMENTS / "brand_awareness.questionnaire.json"
    check = subprocess.run(
        [
            sys.executable,
            "-m",
            "siamang",
            "flow",
            "check",
            str(flow_path),
            "--questionnaire",
            str(q_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert check.returncode == 0 and "OK" in check.stdout
    nodes = subprocess.run(
        [sys.executable, "-m", "siamang", "flow", "nodes", "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert nodes.returncode == 0 and json.loads(nodes.stdout)[0]["type"].startswith("analyze.")
    if HAS_MPL:
        snapshot = write_snapshot(responses, tmp_path / "r.csv")
        run = subprocess.run(
            [
                sys.executable,
                "-m",
                "siamang",
                "flow",
                "run",
                str(flow_path),
                "--data",
                str(snapshot),
                "--questionnaire",
                str(q_path),
                "--cwd",
                str(tmp_path / "out"),
            ],
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "MPLBACKEND": "Agg"},
        )
        assert run.returncode == 0, run.stderr
        assert "tile     tile_n [number] Clean respondents:" in run.stdout
        assert (tmp_path / "out" / "outputs" / "satisfaction_by_region.md").is_file()
