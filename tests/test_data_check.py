"""siamang.data.checks and data.report.data_check — the data against its codebook.

``validate()`` says a variable has a problem; the check says how many rows and
which values, because a 999 in an age column and a 17 in it need different
fixes. Every count here can be read off the frame by eye.
"""

from __future__ import annotations

import pandas as pd

from siamang.core import Variable, VariableMap
from siamang.data import SurveyData
from siamang.data.checks import COLUMNS, check


def _data() -> SurveyData:
    variables = VariableMap()
    variables.add(
        Variable(
            "sat",
            "ordinal",
            label="Satisfaction",
            labels={1: "Low", 2: "Mid", 3: "High"},
            missing_values=(99,),
            missing_labels={99: "Don't know"},
            valid_range=(1, 3),
        )
    )
    variables.add(Variable("age", "ratio", label="Age", valid_range=(18, 75)))
    variables.add(Variable("brands", "nominal", label="Brands", labels={1: "Acme", 2: "Globex"}))
    variables.add(Variable("id", "nominal", label="ID", role="id"))
    variables.add(Variable("gone", "nominal", label="Gone"))
    variables.add(Variable("also_gone", "nominal", label="Also gone"))
    frame = pd.DataFrame(
        {
            "sat": [1, 2, 99, None, 3, 7],
            "age": [30, 41.5, None, 22, 999, 17],
            "brands": [[1, 2], [9], [], None, [2, 9, 8], [1]],
            "id": [1, 2, 3, 3, 4, 5],
            "extra": [1, 2, 3, 4, 5, 6],
            "w": [1, 2, 1, 1, 2, 1],
        }
    )
    return SurveyData(frame=frame, variables=variables)


def _by(table: pd.DataFrame, variable: str, code: str) -> pd.Series:
    rows = table[(table["Variable"] == variable) & (table["Code"] == code)]
    assert len(rows) == 1, (variable, code, table)
    return rows.iloc[0]


def test_each_problem_says_how_many_rows_and_which_values():
    table = check(_data()).table
    assert list(table.columns) == COLUMNS
    # 99 is a declared missing code, so only the 7 is out of range.
    sat = _by(table, "sat", "OUT_OF_RANGE")
    assert (sat["Rows"], sat["Examples"]) == (1, "7 (1)")
    assert sat["Problem"] == "outside the valid range 1–3"
    age = _by(table, "age", "OUT_OF_RANGE")
    assert (age["Rows"], age["Examples"]) == (2, "17 (1), 999 (1)")
    unlabelled = _by(table, "sat", "INVALID_LABEL_VALUE")
    assert (unlabelled["Rows"], unlabelled["Examples"]) == (1, "7 (1)")
    # A multiple-choice answer is read code by code: two respondents named 9,
    # one of them 8 too.
    brands = _by(table, "brands", "INVALID_LABEL_VALUE")
    assert (brands["Rows"], brands["Examples"]) == (2, "9 (2), 8 (1)")
    duplicate = _by(table, "id", "DUPLICATE_ID")
    assert (duplicate["Rows"], duplicate["Examples"]) == (2, "3 (2)")


def test_problems_of_the_files_shape_are_one_row_each():
    table = check(_data()).table
    absent = table[table["Code"] == "MISSING_COLUMN"].iloc[0]
    assert absent["Variable"] == "2 columns" and absent["Examples"] == "also_gone, gone"
    assert pd.isna(absent["Rows"])
    extra = table[table["Code"] == "EXTRA_COLUMN"].iloc[0]
    assert extra["Examples"] == "extra, w" and extra["Severity"] == "warning"


def test_errors_come_first_and_the_stats_count_them():
    result = check(_data())
    severities = list(result.table["Severity"])
    assert severities == sorted(severities, key=lambda s: s != "error")
    assert result.stats["Errors"] == severities.count("error") == 6
    assert result.stats["Warnings"] == 1
    assert result.stats["Checked"] == "8 variables, 6 rows"
    assert "Result" not in result.stats


def test_a_list_of_variables_limits_the_check():
    result = check(_data(), ["age"])
    assert list(result.table["Code"]) == ["OUT_OF_RANGE"]
    assert result.stats["Checked"] == "1 variable, 6 rows"


def test_clean_data_says_so():
    variables = VariableMap()
    variables.add(Variable("x", "ordinal", labels={1: "a", 2: "b"}))
    result = check(SurveyData(frame=pd.DataFrame({"x": [1, 2, None]}), variables=variables))
    assert result.table.empty and list(result.table.columns) == COLUMNS
    assert result.stats["Result"] == "no problems found"
    assert result.stats["Errors"] == result.stats["Warnings"] == 0


def test_data_without_a_codebook_is_a_warning_not_a_crash():
    result = check(SurveyData(frame=pd.DataFrame({"x": [1]})))
    assert list(result.table["Code"]) == ["MISSING_METADATA"]
    assert result.table["Severity"].iloc[0] == "warning"


def test_a_value_of_the_wrong_type_and_a_text_weight_are_counted():
    variables = VariableMap()
    variables.add(Variable("n", "ratio", dtype="int"))
    variables.add(Variable("w", "ratio", role="weight"))
    frame = pd.DataFrame({"n": [1, 2.5, 3.5], "w": [1.0, "heavy", None]})
    table = check(SurveyData(frame=frame, variables=variables)).table
    wrong = _by(table, "n", "INVALID_DTYPE")
    assert (wrong["Rows"], wrong["Examples"]) == (2, "2.5 (1), 3.5 (1)")
    weight = _by(table, "w", "INVALID_WEIGHT")
    assert (weight["Rows"], weight["Examples"]) == (1, "heavy (1)")


def test_the_table_counts_rows_and_says_the_weight_is_not_used():
    table = _data().with_weight("w").report.data_check()
    assert table.stats["Weight"] == "unweighted (the weight 'w' is not applied)"
    printed = table.to_markdown()
    assert "| error | sat | outside the valid range 1–3 | 1 | 7 (1) | OUT_OF_RANGE |" in printed
    assert "nan" not in printed.lower() and "<NA>" not in printed


def test_the_weight_and_the_response_metadata_are_expected_not_extra():
    """A Cell or Rake weights node writes the weight, the platform and the
    runtime keep respondent_id, the timing and the link's url_* beside the
    answers: none is in a codebook, and a check that listed them as problems
    could never say "no problems found" on weighted or platform data."""

    variables = VariableMap()
    variables.add(Variable("x", "ordinal", labels={1: "a", 2: "b"}))
    frame = pd.DataFrame(
        {
            "x": [1, 2, 1],
            "weight": [0.5, 1.5, 1.0],
            "respondent_id": ["r1", "r2", "r3"],
            "duration_s": [300, 280, 410],
            "partial": [False, False, True],
            "url_panel": ["p1", "p2", None],
        }
    )
    data = SurveyData(frame=frame, variables=variables).with_weight("weight")
    result = check(data)
    assert result.table.empty and result.stats["Result"] == "no problems found"
    assert result.stats["Not in the codebook, as expected"] == (
        "weight (the weight); duration_s, partial, respondent_id, url_panel (response metadata)"
    )
    # A column nobody declared is still reported, and an unweighted weight
    # column is just a column.
    extra = check(data.with_frame(frame.assign(stray=1)))
    assert list(extra.table["Code"]) == ["EXTRA_COLUMN"]
    assert extra.table["Examples"].iloc[0] == "stray"
    plain = check(SurveyData(frame=frame, variables=variables))
    assert plain.table["Examples"].iloc[0] == "weight"
    assert "the weight" not in plain.stats["Not in the codebook, as expected"]
