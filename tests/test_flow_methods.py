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


# ─── perceptual map ──────────────────────────────────────────────────────────


def test_perceptual_map_node_crosstab_and_attributes(questionnaire_doc, survey, tmp_path):
    spec = default_registry().get("analyze.correspondence")
    assert spec.title == "Perceptual map"
    assert list(spec.outputs) == ["table", "rows", "columns", "stat"]
    assert not spec.reads("attributes", {"layout": "crosstab"})
    assert spec.reads("yes_codes", {"layout": "attributes"})
    nodes = [
        ("sim", "source.simulated", {"n": 400, "seed": 21}),
        ("expl", "prepare.explode", {"variable": "aware"}),
        ("cell", "prepare.cell_weights", {"variable": "gender", "targets": {"1": 0.5, "2": 0.5}}),
        ("apply", "prepare.apply_weight", {}),
        ("xt", "analyze.correspondence", {"row": "region", "column": "gender"}),
        (
            "at",
            "analyze.correspondence",
            {"layout": "attributes", "row": "region", "attributes": ["aware_1", "aware_2",
                                                                     "aware_3"]},
        ),
        ("sec", "output.report_section", {"heading": "Maps"}),
        ("save", "output.save_report", {"title": "Maps", "path": "outputs/maps.md"}),
    ]  # fmt: skip
    edges = [
        ("sim", "data", "expl", "data"),
        ("expl", "data", "cell", "data"),
        ("cell", "data", "apply", "data"),
        ("apply", "data", "xt", "data"),
        ("apply", "data", "at", "data"),
        ("xt", "table", "sec", "items"),
        ("xt", "rows", "sec", "items"),
        ("at", "columns", "sec", "items"),
        ("at", "stat", "sec", "items"),
        ("sec", "report", "save", "sections"),
    ]
    flow = _flow(nodes, edges)
    assert check_flow(flow, questionnaire=questionnaire_doc) == []
    code = generate_flow(flow, questionnaire_doc)
    assert "from siamang.data import correspondence" in code
    assert 'column="gender"' in code and "yes=None" in code and "dimensions=2" in code
    assert "# ── Perceptual map: region × aware_1, aware_2, aware_3 " in code
    result = FlowRunner(flow, questionnaire=survey, questionnaire_document=questionnaire_doc).run(
        cwd=tmp_path
    )
    assert result.ok
    stat = result.output("xt", "stat")
    assert stat["Map"] == "Region × Gender" and stat["Weight"] == "weight"
    assert stat["Chi-square counts"].startswith("respondents (unweighted)")
    attributes = result.output("at", "stat")
    assert attributes["Map"] == "Region × Attributes" and attributes["Counts as yes"] == "1 = Yes"
    assert list(result.output("at", "columns").to_frame()["Attributes"]) == [
        "Brands heard of (unaided): Acme",
        "Brands heard of (unaided): Globex",
        "Brands heard of (unaided): Initech",
    ]
    report = (tmp_path / "outputs" / "maps.md").read_text("utf-8")
    assert "Principal inertia" in report and "Contribution 1 %" in report
    assert json.dumps(stat) and json.dumps(attributes)
    # The check: a crosstab needs Columns, attributes two of them; yes codes
    # are read with attributes only.
    flow["nodes"][4]["params"].pop("column")
    flow["nodes"][5]["params"]["attributes"] = ["aware_1"]
    flow["nodes"][4]["params"]["yes_codes"] = 1
    issues = sorted(
        (i.severity, i.message) for i in check_flow(flow, questionnaire=questionnaire_doc)
    )
    assert issues == [
        (
            "error",
            "at: A perceptual map of attributes needs two or more attribute variables; 1 was"
            " given.",
        ),
        ("error", "xt: A crosstab map crosses Rows with Columns — choose the Columns variable."),
        (
            "warning",
            "xt: Counts as yes is read only with Table = attributes — set it, or clear Counts as"
            " yes.",
        ),
    ]


# ─── price sensitivity ───────────────────────────────────────────────────────


def _price_data():
    import numpy as np
    import pandas as pd

    from siamang.core.variable import Variable, VariableMap
    from siamang.data import SurveyData

    rng = np.random.default_rng(3)
    n = 240
    base = rng.lognormal(np.log(10), 0.25, n)
    frame = pd.DataFrame(
        {
            "tc": np.round(base * 0.5, 1),
            "ch": np.round(base * 0.8, 1),
            "ex": np.round(base * 1.2, 1),
            "te": np.round(base * 1.7, 1),
            "lc": rng.integers(1, 6, n),
            "le": rng.integers(1, 6, n),
            "wt": rng.uniform(0.5, 1.5, n),
        }
    )
    wtp = base * rng.uniform(0.8, 1.2, n)
    for price in (6, 8, 10, 12):
        frame[f"gg{price}"] = (wtp >= price).astype(int)
    variables = VariableMap()
    variables.add_many(
        [Variable(name, "ratio", label=label) for name, label in
         (("tc", "Too cheap"), ("ch", "A bargain"), ("ex", "Getting expensive"),
          ("te", "Too expensive"))]
        + [Variable(name, "ordinal") for name in ("lc", "le")]
        + [Variable(f"gg{p}", "nominal", label=f"Buy at {p}", labels={0: "No", 1: "Yes"})
           for p in (6, 8, 10, 12)]
    )  # fmt: skip
    questionnaire = {
        "variables": {
            name: {"scale": variables[name].scale, "label": variables[name].label}
            for name in variables
        }
    }
    return SurveyData(frame=frame, variables=variables), questionnaire


def test_price_sensitivity_node_runs_both_methods_weighted(tmp_path):
    spec = default_registry().get("analyze.price")
    assert spec.title == "Price sensitivity" and list(spec.outputs) == ["table", "curves", "stat"]
    assert spec.reads("likelihood_expensive", {"method": "van_westendorp"})
    assert not spec.reads("intent", {"method": "van_westendorp"})
    assert not spec.reads("too_cheap", {"method": "gabor_granger"})
    data, questionnaire = _price_data()
    vw = {"too_cheap": "tc", "cheap": "ch", "expensive": "ex", "too_expensive": "te"}
    gg = {
        "method": "gabor_granger",
        "intent": ["gg6", "gg8", "gg10", "gg12"],
        "price_points": [6, 8, 10, 12],
    }
    flow = _flow(
        [
            ("src", "source.responses", {}),
            ("apply", "prepare.apply_weight", {"column": "wt"}),
            ("vw", "analyze.price", vw),
            (
                "nms",
                "analyze.price",
                {**vw, "likelihood_cheap": "lc", "likelihood_expensive": "le"},
            ),
            ("gg", "analyze.price", gg),
            ("sec", "output.report_section", {"heading": "Prices"}),
            ("save", "output.save_report", {"title": "Prices", "path": "outputs/prices.md"}),
        ],
        [
            ("src", "data", "apply", "data"),
            ("apply", "data", "vw", "data"),
            ("apply", "data", "nms", "data"),
            ("apply", "data", "gg", "data"),
            ("vw", "table", "sec", "items"),
            ("nms", "curves", "sec", "items"),
            ("gg", "table", "sec", "items"),
            ("sec", "report", "save", "sections"),
        ],
    )
    assert check_flow(flow, questionnaire=questionnaire) == []
    code = generate_flow(flow, questionnaire)
    assert "from siamang.data import pricing" in code
    assert "# ── Price sensitivity: Van Westendorp: tc, ch, ex, te " in code
    assert "# ── Price sensitivity: Gabor-Granger: gg6, gg8, gg10, gg12 " in code
    assert 'likelihood_cheap="lc"' in code and "calibration=None" in code
    assert "prices=[6, 8, 10, 12], yes=None" in code
    result = FlowRunner(flow).run(sources={"src": data}, cwd=tmp_path)
    assert result.ok
    from siamang.data import pricing

    weighted = data.with_weight("wt")
    assert result.output("vw", "stat") == pricing.van_westendorp(weighted, **vw).stats
    assert result.output("vw", "stat")["Weight"] == "wt"
    assert "Highest revenue (NMS)" in result.output("nms", "stat")
    stat = result.output("gg", "stat")
    assert stat["Method"] == "Gabor-Granger" and stat["Prices"] == 4
    report = (tmp_path / "outputs" / "prices.md").read_text("utf-8")
    assert "Optimal price point (OPP)" in report and "Revenue-maximising price" in report
    assert "nan" not in report and json.dumps(stat)
    # The check: prices against questions, all four questions, and a
    # calibration without the questions it calibrates.
    flow["nodes"][4]["params"]["price_points"] = [6, 8, 10]
    flow["nodes"][2]["params"].pop("too_expensive")
    flow["nodes"][2]["params"]["calibration"] = {"5": 0.8}
    issues = sorted((i.severity, i.message) for i in check_flow(flow, questionnaire=questionnaire))
    assert issues == [
        (
            "error",
            "gg: Prices lists 3 prices for 4 purchase-intent questions; give one price per "
            "question, in the same order.",
        ),
        (
            "error",
            "vw: Van Westendorp needs the too-expensive price — choose it in Too expensive.",
        ),
        (
            "warning",
            "vw: Calibration is read only with the two likelihood questions — choose them, or "
            "clear Calibration.",
        ),
    ]
