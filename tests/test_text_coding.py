"""siamang.data.text_coding — a coding scheme a model built, applied without one.

The split is the point: a model reads the answers once, somewhere else, and
writes a codeframe; the analysis reads that file. So these tests are about the
properties that make the file worth having — the same answer always gets the
same theme, an answer the scheme never saw stays uncoded rather than guessed
at, and the result is a variable with labels rather than a bare column.
"""

from __future__ import annotations

import json

import pandas as pd
import pytest

from siamang.core import Variable, VariableMap
from siamang.data import SurveyData, text_coding

ANSWERS = [
    "Charging is too slow",
    "  charging  IS   too   slow ",  # the same answer, typed differently
    "The price",
    "Nothing at all",
    "",
]


def _codeframe(**overrides) -> dict:
    payload = {
        "schema_version": "1.0",
        "variable": "why",
        "themes": [
            {"code": 1, "label": "Charging", "definition": "Speed or availability of charging."},
            {"code": 2, "label": "Price", "examples": ["The price"]},
        ],
        "assignments": {
            text_coding.fingerprint("Charging is too slow"): 1,
            text_coding.fingerprint("The price"): 2,
        },
        "model": "deepseek-flash",
        "built_at": "2026-09-13",
        "source_rows": 4,
    }
    payload.update(overrides)
    return payload


def _data() -> SurveyData:
    variables = VariableMap()
    variables.add(Variable("why", "nominal", label="Why?", dtype="str"))
    return SurveyData(frame=pd.DataFrame({"why": ANSWERS}), variables=variables)


# ─── matching ────────────────────────────────────────────────────────────────


def test_the_same_answer_typed_differently_gets_the_same_theme():
    cf = text_coding.parse(_codeframe())
    out = text_coding.codes(pd.Series(ANSWERS), cf)
    assert out.tolist()[:2] == [1, 1]
    assert text_coding.fingerprint("Charging is too slow") == text_coding.fingerprint(
        "  charging  IS   too   slow "
    )


def test_an_answer_the_codeframe_never_saw_stays_uncoded():
    """Collected after the scheme was built, or simply new. Guessing here would
    be the one thing a frozen codeframe exists to prevent."""
    cf = text_coding.parse(_codeframe())
    out = text_coding.codes(pd.Series(ANSWERS), cf)
    assert pd.isna(out.iloc[3]) and pd.isna(out.iloc[4])
    assert text_coding.coverage(_data().frame, cf) == {"answered": 4, "coded": 3, "uncoded": 1}


def test_a_frame_in_another_order_codes_identically():
    cf = text_coding.parse(_codeframe())
    shuffled = list(reversed(ANSWERS))
    assert text_coding.codes(pd.Series(shuffled), cf).tolist() == list(
        reversed(text_coding.codes(pd.Series(ANSWERS), cf).tolist())
    )


# ─── the file ────────────────────────────────────────────────────────────────


def test_a_codeframe_round_trips_through_its_file(tmp_path):
    path = tmp_path / "why.codeframe.json"
    path.write_text(json.dumps(_codeframe()), encoding="utf-8")
    cf = text_coding.load(path)
    assert cf.variable == "why" and cf.into == "why_theme"
    assert cf.labels == {1: "Charging", 2: "Price"}
    assert cf.themes[0].definition.startswith("Speed")
    assert cf.model == "deepseek-flash" and cf.source_rows == 4
    assert text_coding.parse(cf.to_dict()) == cf


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"themes": []}, "no themes"),
        ({"variable": "select *"}, "variable name"),
        ({"themes": [{"code": 1, "label": "A"}, {"code": 1, "label": "B"}]}, "twice"),
        ({"assignments": {"abc": 9}}, "unknown theme"),
        ({"themes": [{"code": 1, "label": " "}]}, "no label"),
        ({"sentiment": {"abc": 7}}, "sentiment"),
    ],
)
def test_an_unusable_codeframe_is_refused_with_a_reason(payload, message):
    with pytest.raises(text_coding.CodeframeError, match=message):
        text_coding.parse(_codeframe(**payload))


def test_a_missing_file_says_so(tmp_path):
    with pytest.raises(text_coding.CodeframeError, match="not found"):
        text_coding.load(tmp_path / "nope.json")


# ─── applying ────────────────────────────────────────────────────────────────


def test_the_theme_arrives_as_a_labeled_variable():
    cf = text_coding.parse(_codeframe())
    out = text_coding.apply(_data(), cf)
    assert out.frame["why_theme"].tolist()[:2] == [1, 1]
    book = out.codebook()
    assert "why_theme" in set(book["name"])
    assert out.variables["why_theme"].labels == {1: "Charging", 2: "Price"}
    assert out.variables["why_theme"].role == "derived"
    # The original is untouched.
    assert "why_theme" not in _data().frame.columns


def test_sentiment_is_only_added_when_the_codeframe_carries_it():
    plain = text_coding.parse(_codeframe())
    assert "why_theme_sentiment" not in text_coding.apply(_data(), plain, sentiment=True).frame
    with_sentiment = text_coding.parse(
        _codeframe(sentiment={text_coding.fingerprint("The price"): -1})
    )
    out = text_coding.apply(_data(), with_sentiment, sentiment=True)
    assert out.frame["why_theme_sentiment"].tolist()[2] == -1
    assert out.variables["why_theme_sentiment"].labels[-1] == "Negative"


def test_the_variable_name_can_be_overridden_but_not_invented():
    cf = text_coding.parse(_codeframe())
    assert "reason" in text_coding.apply(_data(), cf, into="reason").frame.columns
    with pytest.raises(text_coding.CodeframeError, match="variable name"):
        text_coding.apply(_data(), cf, into="drop table")


def test_coding_data_that_lacks_the_column_says_which_one():
    cf = text_coding.parse(_codeframe())
    with pytest.raises(text_coding.CodeframeError, match="why"):
        text_coding.apply(SurveyData(frame=pd.DataFrame({"other": ["x"]})), cf)


# ─── the report table ────────────────────────────────────────────────────────


def test_the_theme_table_shows_shares_of_what_was_coded_and_what_was_not():
    cf = text_coding.parse(_codeframe())
    table = text_coding.apply(_data(), cf).report.themes(cf)
    rows = dict(zip(table.to_frame()["Theme"], table.to_frame()["N"], strict=True))
    assert rows["Charging"] == 2 and rows["Price"] == 1
    assert rows["Coded"] == 3 and rows["Uncoded"] == 1
    assert table.stats["Answered"] == 4 and table.stats["Themes"] == 2
    assert "deepseek-flash" in table.stats["Codeframe"]
    assert "| Theme " in table.to_markdown()
    assert "Weight" not in table.stats
    # Themes count answers; on weighted data the table says the weight is not used.
    weighted = _data().with_frame(_data().frame.assign(w=[1.0, 2.0, 3.0, 4.0, 5.0]))
    table = text_coding.apply(weighted.with_weight("w"), cf).report.themes(cf)
    assert table.to_frame()["N"].tolist()[:2] == [2, 1]
    assert table.stats["Weight"] == "unweighted (the weight 'w' is not applied)"


# ─── the node ────────────────────────────────────────────────────────────────


def test_the_flow_node_codes_a_column_from_a_file(tmp_path):
    """End to end: a codeframe file on disk, a flow, a labeled variable out —
    the path a research bundle takes when someone re-runs it a year later."""
    from siamang.flow import FlowRunner, check_flow

    path = tmp_path / "why.codeframe.json"
    path.write_text(json.dumps(_codeframe()), encoding="utf-8")
    flow = {
        "schema_version": "1.0",
        "name": "t",
        "nodes": [
            {"id": "src", "type": "source.responses", "params": {}},
            {
                "id": "code",
                "type": "prepare.text_code",
                "params": {"codeframe": str(path), "into": "reason"},
            },
        ],
        "edges": [
            {"from": {"node": "src", "port": "data"}, "to": {"node": "code", "port": "data"}}
        ],
    }
    assert [i for i in check_flow(flow) if i.level == "error"] == []
    result = FlowRunner(flow).run(sources={"src": _data()}, cwd=tmp_path)
    assert result.ok, [r.error for r in result.runs if r.error]
    out = result.output("code", "data")
    assert out.frame["reason"].tolist()[:2] == [1, 1]
    assert out.variables["reason"].labels == {1: "Charging", 2: "Price"}
    table = result.output("code", "table")
    assert dict(zip(table.to_frame()["Theme"], table.to_frame()["N"], strict=True))["Uncoded"] == 1
