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


# ─── coverage and sentiment ──────────────────────────────────────────────────


def test_the_table_says_how_much_the_codeframe_covers():
    """Four answers, three coded: coverage 75 %, and the one uncoded answer is
    a quarter of the answers — not a third of the coded ones, as it read."""

    cf = text_coding.parse(_codeframe())
    table = text_coding.apply(_data(), cf).report.themes(cf)
    rows = table.to_frame().set_index("Theme")
    assert rows.loc["Charging", "%"] == round(2 / 3 * 100, 1)  # of the coded answers
    assert rows.loc["Coded", "%"] == 75.0 and rows.loc["Uncoded", "%"] == 25.0
    assert table.stats["Coverage"] == "75.0 % of the answers have a theme"
    assert table.stats["Distinct uncoded answers"] == 1
    assert "Sentiment" not in table.stats and "Positive %" not in rows.columns


def test_uncoded_answers_are_the_texts_and_count_once_each_when_repeated():
    cf = text_coding.parse(_codeframe())
    frame = pd.DataFrame({"why": ["Nothing at all", "  nothing AT all", "New one", "", None]})
    uncoded = text_coding.uncoded_answers(frame, cf)
    assert list(uncoded) == ["Nothing at all", "  nothing AT all", "New one"]
    data = SurveyData(frame=frame)
    stats = data.report.themes(cf).stats
    assert stats["Distinct uncoded answers"] == 2 and stats["Answered"] == 3
    assert text_coding.uncoded_answers(pd.DataFrame({"other": ["x"]}), cf).empty


def test_sentiment_splits_each_theme_when_the_codeframe_has_it():
    cf = text_coding.parse(
        _codeframe(
            sentiment={
                text_coding.fingerprint("Charging is too slow"): -1,
                text_coding.fingerprint("The price"): 1,
            }
        )
    )
    table = _data().report.themes(cf, sentiment=True)
    rows = table.to_frame().set_index("Theme")
    assert list(rows.columns) == ["N", "%", "Negative %", "Neutral %", "Positive %"]
    # Both charging answers are negative, the price answer positive.
    assert list(rows.loc["Charging", ["Negative %", "Neutral %", "Positive %"]]) == [
        100.0,
        0.0,
        0.0,
    ]
    assert rows.loc["Price", "Positive %"] == 100.0
    assert rows.loc["Coded", "Negative %"] == round(2 / 3 * 100, 1)
    # Nobody scored the uncoded answer: a blank, not a zero.
    assert pd.isna(rows.loc["Uncoded", "Negative %"])
    assert "nan" not in table.to_markdown().lower()
    assert table.stats["Sentiment"] == (
        "negative 66.7 %, neutral 0.0 %, positive 33.3 % of 3 answers"
    )
    assert table.stats["Net sentiment"] == -33.3


def test_asking_for_sentiment_a_codeframe_lacks_is_said_not_ignored():
    cf = text_coding.parse(_codeframe())
    table = _data().report.themes(cf, sentiment=True)
    assert table.stats["Sentiment"] == "not in this codeframe"
    assert list(table.to_frame().columns) == ["Theme", "N", "%"]


def test_the_node_hands_on_the_coverage_as_a_stat(tmp_path):
    from siamang.flow import FlowRunner, check_flow

    path = tmp_path / "why.codeframe.json"
    payload = _codeframe(sentiment={text_coding.fingerprint("The price"): 0})
    path.write_text(json.dumps(payload), encoding="utf-8")
    flow = {
        "schema_version": "1.0",
        "name": "t",
        "nodes": [
            {"id": "src", "type": "source.responses", "params": {}},
            {
                "id": "code",
                "type": "prepare.text_code",
                "params": {"codeframe": str(path), "sentiment": True},
            },
        ],
        "edges": [
            {"from": {"node": "src", "port": "data"}, "to": {"node": "code", "port": "data"}}
        ],
    }
    assert check_flow(flow) == []
    result = FlowRunner(flow).run(sources={"src": _data()}, cwd=tmp_path)
    assert result.ok, [r.error for r in result.runs if r.error]
    stat = result.output("code", "stat")
    assert stat["Coverage"] == "75.0 % of the answers have a theme"
    assert stat["Sentiment"] == "negative 0.0 %, neutral 100.0 %, positive 0.0 % of 1 answer"
    assert "why_theme_sentiment" in result.output("code", "data").frame
    assert "Neutral %" in result.output("code", "table").to_frame().columns


# ─── version 1, as it was ────────────────────────────────────────────────────


def test_a_version_1_codeframe_reads_and_applies_exactly_as_before(tmp_path):
    """Pinned at the revision before version 2: the file written back, the
    codes, the coverage, the table (sentiment, a weight) and the generated
    code of a version 1 codeframe are the same, byte for byte."""

    from siamang.flow import generate_flow

    fp = text_coding.fingerprint
    answers = [
        "Charging is too slow",
        "  charging  IS   too   slow ",
        "The price",
        "Nothing at all",
        "",
        None,
        "=SUM(A1)",
        "Цена высокая",
        "charging is too slow\nreally",
    ]
    payload = {
        "schema_version": "1.0",
        "variable": "why",
        "themes": [
            {"code": 1, "label": "Charging", "definition": "Speed."},
            {"code": 2, "label": "Price", "examples": ["The price"]},
            {"code": 3, "label": "=Other"},
        ],
        "assignments": {
            fp("Charging is too slow"): 1,
            fp("The price"): 2,
            fp("Цена высокая"): 2,
            fp("=SUM(A1)"): 3,
        },
        "sentiment": {fp("Charging is too slow"): -1, fp("The price"): 1},
        "model": "m",
        "built_at": "2026-09-13",
        "source_rows": 4,
    }
    cf = text_coding.parse(payload)
    assert cf.version == 1 and not cf.multiple
    assert json.dumps(cf.to_dict(), ensure_ascii=False) == (
        '{"schema_version": "1.0", "variable": "why", "into": "why_theme", "themes": '
        '[{"code": 1, "label": "Charging", "definition": "Speed."}, {"code": 2, "label": '
        '"Price", "examples": ["The price"]}, {"code": 3, "label": "=Other"}], "assignments": '
        '{"f887f32929175cfa": 1, "60f4a731ffcd8b85": 2, "ac5ef1d6fc5c9c89": 2, '
        '"2bfc65fae6ef8c6f": 3}, "sentiment": {"f887f32929175cfa": -1, "60f4a731ffcd8b85": 1}, '
        '"model": "m", "built_at": "2026-09-13", "source_rows": 4}'
    )
    variables = VariableMap()
    variables.add(Variable("why", "nominal", label="Why?", dtype="str"))
    frame = pd.DataFrame({"why": answers, "w": [float(i) for i in range(1, 10)]})
    data = SurveyData(frame=frame, variables=variables)
    assert repr(text_coding.codes(frame["why"], cf).tolist()) == (
        "[1, 1, 2, <NA>, <NA>, <NA>, 3, 2, <NA>]"
    )
    assert text_coding.coverage(frame, cf) == {"answered": 7, "coded": 5, "uncoded": 2}
    assert list(text_coding.uncoded_answers(frame, cf)) == [
        "Nothing at all",
        "charging is too slow\nreally",
    ]
    applied = text_coding.apply(data, cf, sentiment=True)
    assert applied.report.themes(cf, sentiment=True).to_markdown() == (
        "| Theme | N | % | Negative % | Neutral % | Positive % |\n|---|---|---|---|---|---|\n"
        "| Charging | 2 | 40.0 | 100.0 | 0.0 | 0.0 |\n| Price | 2 | 40.0 | 0.0 | 0.0 | 100.0 |\n"
        "| =Other | 1 | 20.0 |  |  |  |\n| Coded | 5 | 71.4 | 66.7 | 0.0 | 33.3 |\n"
        "| Uncoded | 2 | 28.6 |  |  |  |\n\nVariable = why; Answered = 7; Themes = 3; "
        "Coverage = 71.4 % of the answers have a theme; Distinct uncoded answers = 2; "
        "Percentages = a theme: of the coded answers; Coded and Uncoded: of all answers; "
        "Sentiment = negative 66.7 %, neutral 0.0 %, positive 33.3 % of 3 answers; "
        "Net sentiment = -33.3; Codeframe = m, 2026-09-13"
    )
    assert applied.with_weight("w").report.themes(cf).to_markdown() == (
        "| Theme | N | % |\n|---|---|---|\n| Charging | 2 | 40.0 |\n| Price | 2 | 40.0 |\n"
        "| =Other | 1 | 20.0 |\n| Coded | 5 | 71.4 |\n| Uncoded | 2 | 28.6 |\n\n"
        "Variable = why; Answered = 7; Themes = 3; Coverage = 71.4 % of the answers have a "
        "theme; Distinct uncoded answers = 2; Percentages = a theme: of the coded answers; "
        "Coded and Uncoded: of all answers; Codeframe = m, 2026-09-13; "
        "Weight = unweighted (the weight 'w' is not applied)"
    )
    flow = {
        "schema_version": "1.0",
        "name": "t",
        "nodes": [
            {"id": "src", "type": "source.responses", "params": {}},
            {
                "id": "code",
                "type": "prepare.text_code",
                "params": {"codeframe": "why.codeframe.json", "sentiment": True},
            },
        ],
        "edges": [
            {"from": {"node": "src", "port": "data"}, "to": {"node": "code", "port": "data"}}
        ],
    }
    code = generate_flow(flow)
    assert code[code.index("# ── Code open answers") :] == (
        "# ── Code open answers: why.codeframe.json ───────────────────────────────────────\n"
        "# studio: code\n"
        '_codeframe = text_coding.load("why.codeframe.json")\n'
        "n_code_data = text_coding.apply(n_src, _codeframe, into=None, sentiment=True)\n"
        "# Coverage travels with the themes: a theme share is of the coded answers,\n"
        "# and how many answers the codeframe had never seen is the other half of it.\n"
        "n_code_table = n_code_data.report.themes(_codeframe, sentiment=True)\n"
        "n_code_stat = n_code_table.stats\n"
    )
