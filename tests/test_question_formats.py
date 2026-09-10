"""OpenText formats, LikertScale start/display and the NPS table: the
question model, the runtime payload, the simulator, SurveyJS round-trip and
`data.report.nps()`."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import siamang as sg
from siamang.core.serialization import question_to_dict
from siamang.core.variable import Variable, VariableMap
from siamang.data import SurveyData
from siamang.frontend.compiler.react import _compile_question
from siamang.model import from_document, to_document, validate_document


def _survey() -> sg.Questionnaire:
    email = sg.Variable("email", scale="nominal", label="Email")
    born = sg.Variable("born", scale="nominal", label="Date of birth")
    nps = sg.Variable("nps", scale="ordinal", label="Recommend")
    stars = sg.Variable("stars", scale="ordinal", label="Rating")
    return sg.Questionnaire(
        title="Formats",
        pages=[
            sg.Page(
                name="p1",
                items=[
                    sg.OpenText("Your email?", var=email, id="q_email", format="email"),
                    sg.OpenText("Born?", var=born, id="q_born", format="date"),
                    sg.LikertScale("Recommend?", var=nps, id="q_nps", points=11, start=0),
                    sg.LikertScale("Rate it", var=stars, id="q_stars", display="stars"),
                ],
            )
        ],
    )


def test_question_model_validates_the_new_fields():
    v = sg.Variable("x", scale="nominal", label="x")
    with pytest.raises(ValueError, match="format must be one of"):
        sg.OpenText("?", var=v, format="zip")
    with pytest.raises(ValueError, match="multiline"):
        sg.OpenText("?", var=v, multiline=True, format="email")
    with pytest.raises(ValueError, match="start must be 0 or 1"):
        sg.LikertScale("?", var=v, start=2)
    with pytest.raises(ValueError, match="display must be one of"):
        sg.LikertScale("?", var=v, display="hearts")
    assert sg.LikertScale("?", var=v, points=11, start=0).values == list(range(0, 11))
    assert sg.LikertScale("?", var=v).values == [1, 2, 3, 4, 5]


def test_runtime_payload_carries_format_start_and_display():
    survey = _survey()
    by_id = {q.id: q for q in survey.pages[0].flatten_questions()}
    email = _compile_question(by_id["q_email"])
    assert email["kind"] == "text" and email["format"] == "email"
    nps = _compile_question(by_id["q_nps"])
    assert nps["kind"] == "likert" and nps["points"] == 11 and nps["start"] == 0
    assert nps["display"] == "scale"
    assert _compile_question(by_id["q_stars"])["display"] == "stars"


def test_document_round_trip_and_schema_keep_the_fields():
    document = to_document(_survey())
    validate_document(document)
    items = {item["id"]: item for item in document["pages"][0]["items"]}
    assert items["q_email"]["format"] == "email" and items["q_born"]["format"] == "date"
    assert items["q_nps"]["start"] == 0 and items["q_stars"]["display"] == "stars"
    assert "format" not in items.get("q_stars", {})  # defaults are not written
    loaded = from_document(document).survey
    back = {q.id: q for q in loaded.pages[0].flatten_questions()}
    assert back["q_nps"].start == 0 and back["q_stars"].display == "stars"
    assert back["q_born"].format == "date"


def test_simulate_produces_values_of_the_right_shape():
    frame = _survey().simulate(n=50, seed=1).frame
    assert frame["email"].str.contains("@example.com").all()
    assert pd.to_datetime(frame["born"], errors="coerce").notna().all()
    assert frame["nps"].between(0, 10).all() and (frame["nps"] == 0).any()
    assert frame["stars"].between(1, 5).all()


def test_surveyjs_export_maps_formats_and_scale_start():
    survey = _survey()
    by_id = {q.id: q for q in survey.pages[0].flatten_questions()}
    assert question_to_dict(by_id["q_email"])["inputType"] == "email"
    nps = question_to_dict(by_id["q_nps"])
    assert nps["rateMin"] == 0 and nps["rateMax"] == 10
    assert question_to_dict(by_id["q_stars"])["rateType"] == "stars"


def _nps_data(weight: bool = False) -> SurveyData:
    scores = [10, 9, 9, 8, 7, 6, 3, 0, 10, 9] + [np.nan]
    frame = pd.DataFrame({"nps": scores})
    if weight:
        frame["w"] = [2.0] * 5 + [1.0] * 6
    variables = VariableMap()
    variables.add(Variable("nps", "ordinal", label="Recommend us"))
    data = SurveyData(frame=frame, variables=variables)
    return data.with_weight("w") if weight else data


def test_nps_table_groups_scores_and_reports_the_score_with_a_ci():
    table = _nps_data().report.nps("nps")
    frame = table.to_frame().set_index("Group")
    assert frame.loc["Promoters", "N"] == 5 and frame.loc["Detractors", "N"] == 3
    assert frame.loc["Passives", "N"] == 2 and frame.loc["Total", "N"] == 10
    assert table.stats["NPS"] == 20.0 and table.stats["N valid"] == 10
    assert table.stats["CI95 low"] < 20 < table.stats["CI95 high"]
    assert "Promoters" in table.to_markdown() and "NPS = 20.0" in table.to_markdown()
    # Weights move the shares: the first five rows (all 7+) count double.
    weighted = _nps_data(weight=True).report.nps("nps")
    assert weighted.stats["NPS"] > 20.0
    bad = SurveyData(frame=pd.DataFrame({"x": [1, 11]}))
    with pytest.raises(ValueError, match="outside 0–10"):
        bad.report.nps("x").to_frame()


def test_nps_node_runs_in_a_flow():
    from siamang.flow import FlowRunner

    survey = _survey()
    document = {
        "schema_version": "1.0",
        "name": "nps",
        "nodes": [
            {"id": "src", "type": "source.simulated", "params": {"n": 80, "seed": 3}},
            {"id": "nps", "type": "analyze.nps", "params": {"variable": "nps"}},
        ],
        "edges": [{"from": {"node": "src", "port": "data"}, "to": {"node": "nps", "port": "data"}}],
    }
    result = FlowRunner(document, questionnaire=survey).run()
    outputs = result.outputs["nps"]
    assert "NPS" in outputs["stat"] and outputs["table"].to_frame()["N"].iloc[-1] == 80
