"""The flow nodes that expose what the engine could already do.

Descriptive statistics, Data check, MaxDiff scores, Bands, a fixed TURF
portfolio, the codeframe's coverage, Derive's value labels and the R bundle and
dictionary of Export file: each one is checked against the questionnaire,
generated into a script that lints clean, and run — and the script, run on its
own, writes what the runner writes.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

import siamang as sg
from siamang.codegen import generate_questionnaire
from siamang.flow import FlowRunner, check_flow, default_registry, generate_flow
from siamang.model import from_document, loads, to_document

DOCUMENTS = Path(__file__).resolve().parent / "documents"


def _flow(nodes, edges, name="t"):
    return {
        "schema_version": "1.0",
        "name": name,
        "nodes": [{"id": i, "type": t, "params": p} for i, t, p in nodes],
        "edges": [
            {"from": {"node": a, "port": ap}, "to": {"node": b, "port": bp}}
            for a, ap, b, bp in edges
        ],
    }


@pytest.fixture(scope="module")
def questionnaire_doc():
    return loads((DOCUMENTS / "brand_awareness.questionnaire.json").read_text("utf-8"))


@pytest.fixture(scope="module")
def survey(questionnaire_doc):
    return from_document(questionnaire_doc).survey


def _brand_flow():
    nodes = [
        ("sim", "source.simulated", {"n": 150, "seed": 5}),
        (
            "band",
            "prepare.bands",
            {"variable": "age", "bins": [16, 30, 45, 65, 100], "into": "age_band"},
        ),
        (
            "der",
            "prepare.derive",
            {
                "name": "older",
                "formula": "if age >= 50 then 2 else 1",
                "scale": "ordinal",
                "labels": {"1": "Under 50", "2": "50 or over"},
            },
        ),
        ("expl", "prepare.explode", {"variable": "aware"}),
        ("cell", "prepare.cell_weights", {"variable": "gender", "targets": {"1": 0.5, "2": 0.5}}),
        ("apply", "prepare.apply_weight", {}),
        ("check", "analyze.data_check", {}),
        (
            "desc",
            "analyze.descriptives",
            {"variables": ["age", "satisfaction"], "by": "age_band", "detail": True},
        ),
        ("desc2", "analyze.descriptives", {"variables": ["satisfaction"], "by": "older"}),
        (
            "reach",
            "analyze.turf",
            {
                "items": ["aware_1", "aware_2", "aware_3", "aware_99"],
                "method": "fixed",
                "portfolio": ["aware_1", "aware_3"],
            },
        ),
        ("r", "output.export_file", {"path": "outputs/clean.R"}),
        ("dict", "output.export_file", {"path": "outputs/codebook.json"}),
        ("sec", "output.report_section", {"heading": "Checks"}),
        ("save", "output.save_report", {"title": "Exposed", "path": "outputs/exposed.md"}),
    ]
    chain = ["sim", "band", "der", "expl", "cell", "apply"]
    edges = [(a, "data", b, "data") for a, b in zip(chain, chain[1:], strict=False)]
    edges += [
        ("apply", "data", n, "data") for n in ("check", "desc", "desc2", "reach", "r", "dict")
    ]
    edges += [
        ("check", "table", "sec", "items"),
        ("desc", "table", "sec", "items"),
        ("desc2", "stat", "sec", "items"),
        ("reach", "table", "sec", "items"),
        ("sec", "report", "save", "sections"),
    ]
    return _flow(nodes, edges, name="exposed")


def test_the_new_nodes_are_in_the_registry_with_their_ports():
    registry = default_registry()
    assert registry.get("analyze.descriptives").outputs == {"table": "Table", "stat": "Stat"}
    assert registry.get("analyze.data_check").outputs == {"table": "Table", "stat": "Stat"}
    assert registry.get("prepare.maxdiff_scores").outputs == {"data": "SurveyData", "stat": "Stat"}
    assert registry.get("prepare.bands").outputs == {"data": "SurveyData", "stat": "Stat"}
    assert registry.get("prepare.text_code").outputs == {
        "data": "SurveyData",
        "table": "Table",
        "stat": "Stat",
    }
    assert registry.get("analyze.turf").params["method"].values == ("best", "greedy", "fixed")
    assert ".R" in registry.get("output.export_file").description


def test_a_flow_of_the_new_nodes_checks_runs_and_says_what_it_did(
    questionnaire_doc, survey, tmp_path
):
    flow = _brand_flow()
    assert check_flow(flow, questionnaire=questionnaire_doc) == []
    result = FlowRunner(flow, questionnaire=survey, questionnaire_document=questionnaire_doc).run(
        cwd=tmp_path
    )
    assert result.ok, [run.error for run in result.runs if run.error]

    banded = result.output("band", "data")
    assert banded.variables["age_band"].labels[1] == "16 to under 30"
    assert result.output("band", "stat")["Outside the bands"] == 0
    assert result.output("der").variables["older"].labels == {1: "Under 50", 2: "50 or over"}

    # The weight column is the one thing the codebook does not know, and it is
    # expected there: the check finds nothing wrong.
    check = result.output("check", "table").to_frame()
    assert check.empty
    stat = result.output("check", "stat")
    assert stat["Result"] == "no problems found"
    assert stat["Not in the codebook, as expected"] == "weight (the weight)"
    assert stat["Weight"].startswith("unweighted")

    desc = result.output("desc", "table").to_frame()
    assert set(desc["Variable"]) == {"age", "satisfaction"}
    assert list(desc["Age (bands)"].unique())[:1] == ["16 to under 30"]
    assert {"Weighted N", "Q1", "Kurtosis"} <= set(desc.columns)
    stat = result.output("desc", "stat")
    assert stat["Weight"] == "weight" and stat["Effective N"] <= 150
    # Derive's labels name the groups; its label defaults to the formula.
    assert list(result.output("desc2", "table").to_frame()["if age >= 50 then 2 else 1"]) == [
        "Under 50",
        "50 or over",
    ]

    reach = result.output("reach", "table")
    assert reach.method == "fixed" and list(reach["option"]) == [
        "aware_1",
        "aware_3",
        "(portfolio)",
    ]
    assert reach["label"].iloc[0] == "Brands heard of (unaided): Acme"
    reach_stat = result.output("reach", "stat")
    assert reach_stat["Search"] == "none: a fixed portfolio"
    assert reach_stat["Reach"] == f"{reach['reach_percent'].iloc[-1]} %"
    assert reach_stat["Weight"] == "weight"

    outputs = tmp_path / "outputs"
    assert {"clean.R", "clean.csv", "clean.dictionary.json", "codebook.json"} <= {
        path.name for path in outputs.iterdir()
    }
    report = (outputs / "exposed.md").read_text("utf-8")
    assert "| Variable | Label | Age (bands) | N | Weighted N |" in report
    assert "nan" not in report.lower()


def _lint(code: str) -> subprocess.CompletedProcess:
    from siamang.codegen.format import ruff_command

    command = ruff_command()
    assert command
    return subprocess.run(
        [
            *command,
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
            "-",
        ],
        input=code,
        capture_output=True,
        text=True,
        check=False,
    )


def test_the_generated_script_lints_clean_and_writes_what_the_runner_writes(
    questionnaire_doc, survey, tmp_path
):
    flow = _brand_flow()
    code = generate_flow(flow, questionnaire_doc)
    lint = _lint(code)
    assert lint.returncode == 0, lint.stdout + lint.stderr
    assert "turf.evaluate(" in code and "export_file(n_apply" in code
    assert "report.descriptives(" in code and "report.data_check(" in code

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
    script = script_dir / "scripts" / "exposed.py"
    script.write_text(code, encoding="utf-8")
    # This checkout's engine, not whichever one is installed.
    engine = Path(sg.__file__).resolve().parent.parent
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
    for name in ("exposed.md", "clean.csv", "codebook.json"):
        ours = (runner_dir / "outputs" / name).read_text("utf-8")
        assert ours == (script_dir / "outputs" / name).read_text("utf-8"), name


# ─── MaxDiff scores ──────────────────────────────────────────────────────────


def _maxdiff_survey() -> sg.Questionnaire:
    items = {1: "Price", 2: "Quality", 3: "Speed", 4: "Support", 5: "Range"}
    first = [
        sg.Variable(f"md_t{task}_{side}", "nominal", label=f"t{task} {side}", labels=items)
        for task in (1, 2, 3)
        for side in ("best", "worst")
    ]
    first.append(sg.Variable("md_version", "nominal", label="Design version"))
    second = [
        sg.Variable(f"mx_t{task}_{side}", "nominal", label=f"t{task} {side}")
        for task in (1, 2)
        for side in ("best", "worst")
    ]
    second.append(sg.Variable("mx_version", "nominal", label="Design version"))
    return sg.Questionnaire(
        title="MD",
        pages=[
            sg.Page(
                name="p",
                items=[
                    sg.MaxDiff(
                        "Which matters most?",
                        first,
                        per_task=3,
                        tasks=3,
                        versions=4,
                        seed=2,
                        id="q_md",
                    ),
                    sg.MaxDiff(
                        "Which flavour?",
                        second,
                        choices=[
                            sg.Option(10, "Lime"),
                            sg.Option(20, "Mint"),
                            sg.Option(30, "Fig"),
                        ],
                        per_task=2,
                        tasks=2,
                        versions=3,
                        seed=4,
                    ),
                ],
            )
        ],
    )


def test_the_score_variables_are_known_to_the_check_before_a_run():
    survey = _maxdiff_survey()
    document = to_document(survey)
    flow = _flow(
        [
            ("sim", "source.simulated", {"n": 80, "seed": 4}),
            ("sc", "prepare.maxdiff_scores", {"question": "q_md"}),
            # The second question has no id: it is named as the runtime names it,
            # and its items are its choices.
            ("sc2", "prepare.maxdiff_scores", {"question": "maxdiff_mx_t1_best", "prefix": "f_"}),
            ("desc", "analyze.descriptives", {"variables": ["q_md_score_1", "f_30"]}),
            ("clu", "analyze.cluster", {"items": ["q_md_score_1", "q_md_score_2"], "k": 2}),
        ],
        [
            ("sim", "data", "sc", "data"),
            ("sc", "data", "sc2", "data"),
            ("sc2", "data", "desc", "data"),
            ("sc2", "data", "clu", "data"),
        ],
    )
    assert check_flow(flow, questionnaire=document) == []
    result = FlowRunner(flow, questionnaire=survey, questionnaire_document=document).run()
    assert result.ok, [run.error for run in result.runs if run.error]
    stat = result.output("sc", "stat")
    assert stat["Respondents scored"] == 80 and stat["Items"] == 5
    assert stat["Variables"] == "q_md_score_1 … q_md_score_5"
    data = result.output("sc2", "data")
    assert data.variables["f_10"].label == "MaxDiff score: Lime"
    assert data.frame["q_md_score_1"].between(-1, 1).all()
    desc = result.output("desc", "table").to_frame()
    assert list(desc["Label"]) == ["MaxDiff score: Price", "MaxDiff score: Fig"]
    assert "cluster" in result.output("clu", "data").frame

    # A score the question cannot have is named before anything runs.
    wrong = _flow(
        [
            ("sim", "source.simulated", {}),
            ("sc", "prepare.maxdiff_scores", {"question": "q_md"}),
            ("desc", "analyze.descriptives", {"variables": ["q_md_score_9"]}),
        ],
        [("sim", "data", "sc", "data"), ("sc", "data", "desc", "data")],
    )
    issues = check_flow(wrong, questionnaire=document)
    assert [issue.code for issue in issues] == ["UNKNOWN_VARIABLE"]
    assert "q_md_score_9" in issues[0].message
    code = generate_flow(flow, document)
    assert _lint(code).returncode == 0
    assert 'maxdiff.with_scores(n_sim, "q_md", prefix=None)' in code


def test_a_maxdiff_question_the_questionnaire_lacks_is_named_before_the_run():
    """A typo in the question passed the check and failed in the run; the check
    now names it with the questions there are, as the run's error does."""

    document = to_document(_maxdiff_survey())
    flow = _flow(
        [
            ("sim", "source.simulated", {"n": 20}),
            ("sc", "prepare.maxdiff_scores", {"question": "q_mdx"}),
        ],
        [("sim", "data", "sc", "data")],
    )
    issues = check_flow(flow, questionnaire=document)
    assert [(issue.code, issue.node) for issue in issues] == [("PARAM_INVALID", "sc")]
    assert issues[0].message == (
        "Parameter 'question' of sc: no MaxDiff question named 'q_mdx'; this questionnaire "
        "has: q_md, maxdiff_mx_t1_best."
    )
    # A questionnaire without a MaxDiff question says it has none.
    brand = loads((DOCUMENTS / "brand_awareness.questionnaire.json").read_text("utf-8"))
    issues = check_flow(flow, questionnaire=brand)
    assert issues[0].message.endswith("no MaxDiff question named 'q_mdx'; it has none.")
    # Without a questionnaire there is nothing to check against.
    assert check_flow(flow) == []
