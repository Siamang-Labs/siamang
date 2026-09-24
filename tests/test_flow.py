"""siamang.flow — registry, documents, runner and code generation."""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
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


def test_apply_weight_lists_what_it_weights_and_what_it_does_not():
    """The palette promised "every table and statistic downstream" while the
    rank tests, k-means and three of the charts ignored the weight. What the
    node says has to be what the nodes do — the flow test above checks the
    other half."""

    spec = default_registry().get("prepare.apply_weight")
    assert "every table and statistic" not in spec.description
    assert "unweighted" in spec.description
    listed = spec.params["column"].help
    weighted, unweighted = listed.split("Unweighted, and saying so:")
    for title in ("MaxDiff", "Conjoint", "Share of preference", "Principal components"):
        assert title in weighted
    for title in ("Compare groups", "Correlation", "Cluster", "Box plot", "Scatter plot"):
        assert title in unweighted and title not in weighted


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


def test_report_section_without_a_heading_is_a_plain_markdown_block(questionnaire_doc):
    """A section is the report's paragraph as well as its chapter: with no
    heading it contributes only its Markdown, so prose can sit between two
    sections without inventing a heading to carry it."""

    document = _flow(
        [
            ("prose", "output.report_section", {"text": "Everything below is weighted."}),
            ("titled", "output.report_section", {"heading": "Results"}),
            ("save", "output.save_report", {"title": "T", "path": "outputs/r.md"}),
        ],
        [
            ("prose", "report", "save", "sections"),
            ("titled", "report", "save", "sections"),
        ],
    )
    # A missing heading is no longer a document error.
    issues = check_flow(document, questionnaire=questionnaire_doc)
    assert [i for i in issues if i.severity == "error"] == []

    code = generate_flow(document, questionnaire_doc)
    prose, titled = code.index("n_prose = Report()"), code.index("n_titled = Report()")
    assert 'n_prose.text("Everything below is weighted.")' in code
    # Only the titled section emits a heading call.
    assert code.count(".heading(") == 1
    assert 'n_titled.heading("Results")' in code
    assert ".heading(" not in code[prose:titled]


def test_a_report_carries_its_look_and_the_placement_of_each_item(questionnaire_doc):
    """Both are node parameters, so both are in the flow document, in the
    generated script and in a research bundle — the look of a report is part of
    the program you take with you, the way the questionnaire's theme is."""

    document = _flow(
        [
            ("src", "source.responses", {"table": "responses"}),
            ("xtab", "analyze.crosstab", {"row": "satisfaction", "col": "region"}),
            ("bar", "visualize.bar", {"variable": "satisfaction"}),
            (
                "section",
                "output.report_section",
                {
                    "heading": "Results",
                    "captions": {"xtab": "Satisfaction by region"},
                    "layout": {
                        "xtab": {"width": "75%"},
                        "bar": {"width": "48%", "align": "left", "break_before": True},
                    },
                },
            ),
            (
                "save",
                "output.save_report",
                {
                    "title": "T",
                    "path": "outputs/r.md",
                    "theme": {"font_preset": "modern", "page": "a4", "number_tables": True},
                },
            ),
        ],
        [
            ("src", "data", "xtab", "data"),
            ("src", "data", "bar", "data"),
            ("xtab", "table", "section", "items"),
            ("bar", "chart", "section", "items"),
            ("section", "report", "save", "sections"),
        ],
    )
    issues = check_flow(document, questionnaire=questionnaire_doc)
    assert [i for i in issues if i.severity == "error"] == []

    code = generate_flow(document, questionnaire_doc)
    # Keyed by node in the document (so a rename carries it), positional in the
    # code (so it lines up with the port the template zips over).
    assert '[{"width": "75%"}, {"width": "48%", "align": "left", "break_before": True}]' in code
    assert "n_section.add(_item, caption=_caption, **_layout)" in code
    # The theme travels as data — no import to add, like every other parameter.
    assert 'theme={"font_preset": "modern", "page": "a4", "number_tables": True}' in code
    assert "ReportTheme" not in code


def test_a_look_or_a_placement_that_cannot_work_is_named_before_the_run(questionnaire_doc):
    def errors(section_params, save_params):
        document = _flow(
            [
                ("src", "source.responses", {"table": "responses"}),
                ("xtab", "analyze.crosstab", {"row": "satisfaction", "col": "region"}),
                ("section", "output.report_section", {"heading": "R", **section_params}),
                ("save", "output.save_report", {"title": "T", **save_params}),
            ],
            [
                ("src", "data", "xtab", "data"),
                ("xtab", "table", "section", "items"),
                ("section", "report", "save", "sections"),
            ],
        )
        return {
            i.message
            for i in check_flow(document, questionnaire=questionnaire_doc)
            if i.severity == "error"
        }

    assert errors({}, {}) == set()
    assert any("font_prest" in m for m in errors({}, {"theme": {"font_prest": "modern"}}))
    assert any("not one of" in m for m in errors({}, {"theme": {"page": "a3"}}))
    assert any("CSS length" in m for m in errors({}, {"theme": {"width": "wide"}}))
    assert any("xtab: align" in m for m in errors({"layout": {"xtab": {"align": "middle"}}}, {}))
    assert any("unknown key" in m for m in errors({"layout": {"xtab": {"size": "big"}}}, {}))


@pytest.mark.skipif(not HAS_MPL, reason="matplotlib")
def test_a_run_renders_the_report_in_the_look_the_flow_chose(
    questionnaire_doc, survey, responses, tmp_path
):
    document = _flow(
        [
            ("src", "source.responses", {"table": "responses"}),
            ("xtab", "analyze.crosstab", {"row": "satisfaction", "col": "region"}),
            (
                "section",
                "output.report_section",
                {"heading": "R", "layout": {"xtab": {"width": "60%"}}},
            ),
            (
                "save",
                "output.save_report",
                {
                    "title": "T",
                    "path": "outputs/r.md",
                    "html": True,
                    "theme": {"font_preset": "modern", "page": "a4", "number_tables": True},
                },
            ),
        ],
        [
            ("src", "data", "xtab", "data"),
            ("xtab", "table", "section", "items"),
            ("section", "report", "save", "sections"),
        ],
    )
    result = FlowRunner(document, questionnaire=survey).run(
        sources={"src": responses}, cwd=tmp_path
    )
    assert result.ok
    html = (tmp_path / "outputs" / "r.html").read_text("utf-8")
    assert '<meta name="siamang-report-theme" content="modern">' in html
    assert "@page { size: A4" in html
    assert "--fig-w:60%" in html
    assert "Table 1." in html
    # The Markdown is the content and says nothing about any of it.
    markdown = (tmp_path / "outputs" / "r.md").read_text("utf-8")
    assert "60%" not in markdown and "Table 1." not in markdown


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
def test_a_chart_node_sizes_the_figure_it_draws(questionnaire_doc, survey, responses, tmp_path):
    """The figure is the thing that is resized, not the picture of it: a chart
    asked for 6×4 inches writes 6×4 inches of pixels at its own dpi, so the axis
    labels keep their proportion instead of being scaled with the image."""

    document = _flow(
        [
            ("src", "source.responses", {"table": "responses"}),
            ("chart", "visualize.bar", {"variable": "satisfaction", "width": 6, "height": 4}),
        ],
        [("src", "data", "chart", "data")],
    )
    result = FlowRunner(document, questionnaire=survey).run(
        sources={"src": responses}, cwd=tmp_path
    )
    assert result.ok
    chart = result.output("chart", "chart")
    assert chart.figsize == (6.0, 4.0) and chart.palette == "muted"

    png = chart.save(tmp_path / "fig.png")
    from PIL import Image

    with Image.open(png) as image:
        width, height = image.size
    # bbox_inches="tight" trims the margins, so the written file is at most the
    # figure box and clearly smaller than the 10x6 default would have been.
    assert width <= 6 * chart.dpi and height <= 4 * chart.dpi
    assert width > 4 * chart.dpi and height > 2 * chart.dpi

    # dpi is a field now, so a caller holding only the chart can raise it.
    chart.dpi = 300
    with Image.open(chart.save(tmp_path / "fig300.png")) as image:
        assert image.size[0] > width * 1.5
    # An explicit argument still wins over the field.
    with Image.open(chart.save(tmp_path / "fig150.png", dpi=150)) as image:
        assert image.size[0] == width


def test_chart_geometry_is_checked_before_a_run(questionnaire_doc):
    """A figure of forty inches is a typo, and check_flow names the bound
    rather than letting matplotlib decide what to do with it."""

    def codes(params):
        document = _flow(
            [
                ("src", "source.responses", {"table": "responses"}),
                ("chart", "visualize.bar", {"variable": "satisfaction", **params}),
            ],
            [("src", "data", "chart", "data")],
        )
        return {
            i.message
            for i in check_flow(document, questionnaire=questionnaire_doc)
            if i.severity == "error"
        }

    assert codes({"width": 12}) == set()
    assert any("at most 30" in m for m in codes({"width": 40}))
    assert any("at least 2" in m for m in codes({"height": 0.5}))
    assert any("chartreuse" in m for m in codes({"palette": "chartreuse"}))


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
        (
            "turf",
            "analyze.turf",
            {"items": ["aware_1", "aware_2", "aware_3", "aware_99"], "max_size": 2},
        ),
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
            "turf",
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
    # After Apply weight every result either uses the weight or says it does not.
    unweighted = "unweighted (the weight 'weight' is not applied)"
    assert result.output("corr")["weight"] == unweighted
    assert result.output("cmp")["weight"] == result.output("cmp3")["weight"] == unweighted
    assert result.output("clu", "stat")["weight"] == unweighted
    assert result.output("box").weight_note == result.output("scat").weight_note == unweighted
    assert result.output("heat").weight_note == unweighted  # a correlation matrix
    assert result.output("ci")["weight"] == "weight"
    assert result.output("reg", "stat")["weight"] == "weight"
    assert result.output("pca", "stat")["weight"] == result.output("rel", "stat")["weight"]
    assert result.output("rel", "stat")["weight"] == "weight"
    assert result.output("turf", "stat")["Weight"] == "weight"
    # Reach never exceeds the base and never shrinks as the portfolio grows.
    reach = result.output("turf", "table")
    assert list(reach["size"]) == [1, 2]
    assert reach["reach"].is_monotonic_increasing
    assert reach["reach"].max() <= result.output("turf", "stat")["Base"]
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
    # A platform-only step in a flow with several sources is skipped when any
    # snapshot is given; it used to test `args.data`, which that script lacks.
    writes = _flow(
        [
            ("a", "source.responses", {}),
            ("b", "source.table", {"table": "clean"}),
            ("keep", "output.write_table", {"name": "out"}),
        ],
        [("a", "data", "keep", "data")],
    )
    code = generate_flow(writes, questionnaire_doc)
    assert "args.data:" not in code
    assert "if not (args.a_data or args.b_data):  # platform only" in code
    compile(code, "two.py", "exec")
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


def test_the_maxdiff_node_runs_on_a_maxdiff_questionnaire(tmp_path):
    """The node reads the design from the questionnaire rather than a parameter,
    so the only thing a researcher has to name is the question."""

    import siamang as sg
    from siamang.model import to_document

    items = {1: "Price", 2: "Quality", 3: "Speed", 4: "Support", 5: "Range"}
    variables = [
        sg.Variable(f"md_t{task}_{side}", "nominal", label=f"t{task} {side}", labels=items)
        for task in (1, 2, 3)
        for side in ("best", "worst")
    ]
    variables.append(sg.Variable("md_version", "nominal", label="Design version"))
    question = sg.MaxDiff(
        "Which matters most?", variables, per_task=3, tasks=3, versions=4, seed=2, id="q_md"
    )
    survey = sg.Questionnaire(title="MD", pages=[sg.Page(name="p", items=[question])])
    document = to_document(survey)

    flow = _flow(
        [
            ("sim", "source.simulated", {"n": 120, "seed": 4}),
            ("md", "analyze.maxdiff", {"question": "q_md", "method": "both"}),
        ],
        [("sim", "data", "md", "data")],
    )
    assert check_flow(flow, questionnaire=document) == []
    result = FlowRunner(flow, questionnaire=survey, questionnaire_document=document).run(
        cwd=tmp_path
    )
    assert result.ok
    table = result.output("md", "table").to_frame()
    assert list(table["Item"]) and set(table["Item"]) <= set(items.values())
    assert table["Score"].between(-1, 1).all()
    stats = result.output("md", "stat")
    assert "respondents" in stats["Base"]
    assert "conditional logit" in stats["Method"]


def test_the_choice_data_node_writes_what_an_hb_package_reads(tmp_path):
    """Individual utilities come from hierarchical Bayes, which lives in R and
    takes minutes; the node hands over the data instead of running a cut-down
    version of it here."""

    import siamang as sg
    from siamang.model import to_document

    items = {1: "Price", 2: "Quality", 3: "Speed", 4: "Support"}
    variables = [
        sg.Variable(f"md_t{task}_{side}", "nominal", label=f"t{task} {side}", labels=items)
        for task in (1, 2)
        for side in ("best", "worst")
    ]
    variables.append(sg.Variable("md_version", "nominal", label="Design version"))
    question = sg.MaxDiff("Which?", variables, per_task=3, tasks=2, versions=3, seed=6, id="q_md")
    survey = sg.Questionnaire(title="MD", pages=[sg.Page(name="p", items=[question])])
    document = to_document(survey)

    flow = _flow(
        [
            ("sim", "source.simulated", {"n": 60, "seed": 2}),
            ("out", "output.choice_data", {"question": "q_md", "path": "outputs/md.csv"}),
        ],
        [("sim", "data", "out", "data")],
    )
    assert check_flow(flow, questionnaire=document) == []
    result = FlowRunner(flow, questionnaire=survey, questionnaire_document=document).run(
        cwd=tmp_path
    )
    assert result.ok
    assert (tmp_path / "outputs" / "md.csv").is_file()
    assert (tmp_path / "outputs" / "md.dictionary.json").is_file()
    assert (tmp_path / "outputs" / "md.hb.R").is_file()


def _conjoint_survey():
    import siamang as sg

    attributes = [
        sg.Attribute(
            "brand", [sg.Option(1, "Acme"), sg.Option(2, "Globex"), sg.Option(3, "Initech")]
        ),
        sg.Attribute("price", [sg.Option(10, "10"), sg.Option(15, "15"), sg.Option(20, "20")]),
    ]
    variables = [
        sg.Variable(f"cbc_t{t}", "nominal", label=f"Task {t}", labels={1: "1", 2: "2", 3: "3"})
        for t in (1, 2, 3, 4)
    ]
    variables.append(sg.Variable("cbc_version", "nominal", label="Design version"))
    question = sg.Conjoint(
        "Which would you buy?",
        variables,
        attributes=attributes,
        alternatives=3,
        tasks=4,
        versions=6,
        seed=7,
        id="q_cbc",
    )
    return sg.Questionnaire(title="C", pages=[sg.Page(name="p", items=[question])])


def test_the_conjoint_nodes_run_on_a_conjoint_questionnaire(tmp_path):
    """The attributes and the design come from the questionnaire, so the only
    thing a researcher names is the question — and, for a simulation, the
    products they are thinking of launching."""

    from siamang.model import to_document

    survey = _conjoint_survey()
    document = to_document(survey)
    products = {
        "Cheap Acme": {"brand": 1, "price": 10},
        "Dear Globex": {"brand": 2, "price": 20},
    }
    flow = _flow(
        [
            ("sim", "source.simulated", {"n": 150, "seed": 9}),
            ("cbc", "analyze.conjoint", {"question": "q_cbc"}),
            ("sim_shares", "analyze.conjoint_shares", {"question": "q_cbc", "products": products}),
            ("out", "output.conjoint_data", {"question": "q_cbc", "path": "outputs/cbc.csv"}),
        ],
        [
            ("sim", "data", "cbc", "data"),
            ("sim", "data", "sim_shares", "data"),
            ("sim", "data", "out", "data"),
        ],
    )
    assert check_flow(flow, questionnaire=document) == []
    result = FlowRunner(flow, questionnaire=survey, questionnaire_document=document).run(
        cwd=tmp_path
    )
    assert result.ok

    table = result.output("cbc", "table").to_frame()
    assert list(table.columns) == ["Attribute", "Level", "Part-worth", "Importance %"]
    assert set(table["Attribute"]) == {"brand", "price"}
    stats = result.output("cbc", "stat")
    assert "respondents" in stats["Base"]

    shares = result.output("sim_shares", "table").to_frame()
    assert list(shares["product"]) and abs(shares["share"].sum() - 100.0) < 0.2
    shares_stats = result.output("sim_shares", "stat")
    assert shares_stats["Base"] == "150 respondents" and "Weight" not in shares_stats

    assert (tmp_path / "outputs" / "cbc.csv").is_file()
    assert (tmp_path / "outputs" / "cbc.dictionary.json").is_file()
    assert (tmp_path / "outputs" / "cbc.hb.R").is_file()


def test_the_derive_node_computes_a_variable_and_registers_it(tmp_path):
    """A formula reaches the run as text and comes back as a column with a
    Variable beside it — a column without one is invisible to describe(), to an
    export's dictionary, and to any node that names it later."""

    import siamang as sg
    from siamang.model import to_document

    survey = sg.Questionnaire(
        title="Spend",
        pages=[
            sg.Page(
                name="p",
                items=[
                    sg.NumericInput(
                        "Yearly spend",
                        sg.Variable("spend_year", "ratio", label="Spend", valid_range=(0, 1200)),
                        id="q_spend",
                    )
                ],
            )
        ],
    )
    document = to_document(survey)

    flow = _flow(
        [
            ("sim", "source.simulated", {"n": 40, "seed": 3}),
            (
                "der",
                "prepare.derive",
                {
                    "name": "spend_month",
                    "formula": "round(spend_year / 12, 2)",
                    "scale": "ratio",
                },
            ),
            ("desc", "analyze.describe", {}),
        ],
        [("sim", "data", "der", "data"), ("der", "data", "desc", "data")],
    )
    assert check_flow(flow, questionnaire=document) == []
    result = FlowRunner(flow, questionnaire=survey, questionnaire_document=document).run(
        cwd=tmp_path
    )
    assert result.ok
    described = result.output("desc", "table")
    described = described if isinstance(described, pd.DataFrame) else described.to_frame()
    assert "spend_month" in set(described["name"])
    # The label defaults to the formula, so the codebook says how the number
    # was made — and that travels into the dictionary beside any export.
    label = described.loc[described["name"] == "spend_month", "label"].iloc[0]
    assert label == "round(spend_year / 12, 2)"


def test_the_derive_node_reports_a_bad_formula_before_anything_runs(questionnaire_doc):
    """Both halves: a formula that cannot be read, and one that reads fine but
    names a variable the codebook has not got. Neither should wait for a run."""

    broken = _flow(
        [
            ("sim", "source.simulated", {}),
            ("der", "prepare.derive", {"name": "x", "formula": "age / "}),
        ],
        [("sim", "data", "der", "data")],
    )
    issues = check_flow(broken, questionnaire=questionnaire_doc)
    assert [i.code for i in issues] == ["PARAM_INVALID"]
    assert "character" in issues[0].message

    typo = _flow(
        [
            ("sim", "source.simulated", {}),
            ("der", "prepare.derive", {"name": "x", "formula": "agee + 1"}),
        ],
        [("sim", "data", "der", "data")],
    )
    issues = check_flow(typo, questionnaire=questionnaire_doc)
    assert [i.code for i in issues] == ["UNKNOWN_VARIABLE"]
    assert "agee" in issues[0].message


def test_the_banner_node_runs_and_only_compares_within_a_block(questionnaire_doc, survey, tmp_path):
    """The letters are the reason this node exists, and the way to get them
    wrong is to compare columns that are not mutually exclusive."""

    flow = _flow(
        [
            ("sim", "source.simulated", {"n": 300, "seed": 5}),
            (
                "ban",
                "analyze.banner",
                {"rows": ["gender"], "columns": ["region", "gender"]},
            ),
        ],
        [("sim", "data", "ban", "data")],
    )
    assert check_flow(flow, questionnaire=questionnaire_doc) == []
    result = FlowRunner(flow, questionnaire=survey, questionnaire_document=questionnaire_doc).run(
        cwd=tmp_path
    )
    assert result.ok

    # to_frame(), not a duck test: BannerTable has a `columns` field of its own
    # (the banner variables), so "has .columns" does not mean "is a frame".
    frame = result.output("ban", "table").to_frame()
    assert list(frame.columns[:2]) == ["Question", "Answer"]
    assert frame.iloc[0]["Answer"] == "respondents"

    stats = result.output("ban", "stat")
    assert "within each banner variable only" in stats["Test"]
    assert "none" in stats["Correction"]


def test_simulated_data_draws_the_arm_an_assignment_script_writes():
    """The Simulated data node ran `survey.simulate()`, which never sees the
    questionnaire's scripts, so an assigned arm was a column that did not
    exist and every page gated on it was empty."""

    import siamang as sg

    yes_no = sg.Variable("seen", "nominal", label="Seen", labels={1: "Yes", 0: "No"})
    survey = sg.Questionnaire(
        title="A",
        pages=[
            sg.Page(
                name="treated",
                show_if=sg.compare("condition", "=", 2),
                items=[sg.SingleChoice("Seen the ad?", var=yes_no, id="q_seen")],
            )
        ],
        scripts=[sg.Script.assign_condition("condition", [(1, "Control"), (2, "Treatment")])],
    )
    flow = _flow([("sim", "source.simulated", {"n": 200, "seed": 3})], [])
    data = FlowRunner(flow, questionnaire=survey).run().output("sim")
    assert set(data.frame["condition"]) == {1, 2}
    assert data.frame.loc[data.frame["condition"] == 2, "seen"].notna().all()
    assert data.frame.loc[data.frame["condition"] == 1, "seen"].isna().all()
    assert data.variables["condition"].labels == {1: "Control", 2: "Treatment"}
    code = generate_flow(flow)
    assert "from siamang.local_simulator import simulate_survey" in code
    assert "n_sim = simulate_survey(survey, n=200, seed=3)" in code


def test_a_node_may_name_the_arm_an_assignment_script_writes(questionnaire_doc):
    """No question collects an assigned arm and the document need not declare
    it, yet real responses and Simulated data carry it as a column: check_flow
    flagged a crosstab by it as UNKNOWN_VARIABLE, which validate() stopped
    doing for conditions long ago."""

    document = copy.deepcopy(questionnaire_doc)
    document["scripts"] = [
        *document.get("scripts", []),
        {
            "type": "assign_condition",
            "variable": "condition",
            "arms": [{"code": 1, "label": "Control"}, {"code": 2, "label": "Treatment"}],
        },
        {"type": "custom", "trigger": "onInit", "code": "answers.noted = 1;"},
    ]
    assert "condition" not in document["variables"]

    def issues(node_type, params):
        flow = _flow(
            [("sim", "source.simulated", {}), ("x", node_type, params)],
            [("sim", "data", "x", "data")],
        )
        return [issue.code for issue in check_flow(flow, questionnaire=document)]

    assert issues("analyze.crosstab", {"row": "condition", "col": "region"}) == []
    # Only what a script says it assigns counts: a custom script's key does not.
    assert issues("analyze.crosstab", {"row": "noted", "col": "region"}) == ["UNKNOWN_VARIABLE"]
    # The arm is nominal, as Simulated data enters it in the codebook.
    assert issues("visualize.scatter", {"x": "condition", "y": "age"}) == ["VARIABLE_SCALE"]
