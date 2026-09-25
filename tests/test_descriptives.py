"""siamang.data.descriptives and data.report.descriptives — the first table of a report.

The numbers are worked out by hand from the textbook formulas (the sample SD,
R's type-7 quartiles, SPSS's bias-corrected skewness G1 and kurtosis G2) rather
than taken from the library that computes them, and the weighted ones from the
same definitions the Group means table uses, so the two tables cannot disagree.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from siamang.core import Variable, VariableMap
from siamang.data import SurveyData
from siamang.data.descriptives import describe, weighted_quantile


def _data(weight: bool = False) -> SurveyData:
    variables = VariableMap()
    variables.add(
        Variable(
            "sat",
            "ordinal",
            label="Satisfaction",
            labels={1: "Low", 2: "Mid", 3: "High", 99: "Don't know"},
            missing_values=(99,),
        )
    )
    variables.add(Variable("age", "ratio", label="Age"))
    variables.add(
        Variable(
            "region",
            "nominal",
            label="Region",
            labels={2: "South", 1: "North", 9: "Refused"},
            missing_values=(9,),
        )
    )
    frame = pd.DataFrame(
        {
            "sat": pd.array([1, 2, 99, None, 3, 7], dtype="Int64"),
            "age": [30, 41.5, None, 22, 60, "n/a"],
            "region": [1, 2, 1, 2, 9, None],
            "w": [1.0, 2.0, 1.0, 1.0, 2.0, 1.0],
        }
    )
    data = SurveyData(frame=frame, variables=variables)
    return data.with_weight("w") if weight else data


def _row(table: pd.DataFrame, variable: str, **where) -> pd.Series:
    mask = table["Variable"] == variable
    for column, value in where.items():
        mask &= table[column] == value
    assert mask.sum() == 1
    return table[mask].iloc[0]


# ─── unweighted ──────────────────────────────────────────────────────────────


def test_the_basic_statistics_are_the_textbook_ones():
    table = describe(_data().frame, ["sat"], variables=_data().variables).table
    row = _row(table, "sat")
    # 99 is "Don't know" and the fourth row is blank: four answers, 1 2 3 7.
    assert row["N"] == 4 and row["Missing"] == 2
    assert row["Mean"] == 3.25
    assert row["SD"] == round(math.sqrt(20.75 / 3), 3)  # Σ(x − 3.25)² = 20.75
    assert (row["Min"], row["Median"], row["Max"]) == (1.0, 2.5, 7.0)
    assert row["Label"] == "Satisfaction"
    assert list(table.columns) == [
        "Variable",
        "Label",
        "N",
        "Missing",
        "Mean",
        "SD",
        "Min",
        "Median",
        "Max",
    ]


def test_detail_adds_quartiles_skewness_and_kurtosis_by_hand():
    table = describe(_data().frame, ["sat"], variables=_data().variables, detail=True).table
    row = _row(table, "sat")
    values = np.array([1.0, 2.0, 3.0, 7.0])
    n = len(values)
    deviations = values - values.mean()
    m2, m3, m4 = ((deviations**k).mean() for k in (2, 3, 4))
    g1 = m3 / m2**1.5
    g2 = m4 / m2**2 - 3
    skew = g1 * math.sqrt(n * (n - 1)) / (n - 2)  # G1, as SPSS and Excel report it
    kurt = ((n + 1) * g2 + 6) * (n - 1) / ((n - 2) * (n - 3))  # G2, excess
    # Type 7: Q1 at position 0.75 between 1 and 2, Q3 at 2.25 between 3 and 7.
    assert (row["Q1"], row["Q3"]) == (1.75, 4.0)
    assert row["Skewness"] == round(skew, 3) == 1.443
    assert row["Kurtosis"] == round(kurt, 3) == 2.235
    assert list(table.columns)[-7:] == ["Min", "Q1", "Median", "Q3", "Max", "Skewness", "Kurtosis"]


def test_missing_codes_and_text_are_set_aside_and_named():
    result = describe(_data().frame, ["sat", "age"], variables=_data().variables)
    age = _row(result.table, "age")
    assert age["N"] == 4 and age["Missing"] == 2  # a blank and "n/a"
    assert age["Mean"] == round((30 + 41.5 + 22 + 60) / 4, 3)
    assert result.stats["Missing codes"] == "sat: 99"
    assert result.stats["Not numbers"] == "age: 1"
    assert "Weight" not in result.stats


def test_by_splits_into_labelled_groups_in_codebook_order():
    result = describe(_data().frame, ["sat"], variables=_data().variables, by="region")
    table = result.table
    # The codebook lists South first; "Refused" (a missing code) is no group,
    # and neither is the blank.
    assert list(table["Region"]) == ["South", "North"]
    south = _row(table, "sat", Region="South")
    north = _row(table, "sat", Region="North")
    assert (south["N"], south["Missing"], south["Mean"]) == (1, 1, 2.0)
    assert (north["N"], north["Missing"], north["Mean"]) == (1, 1, 1.0)
    assert result.stats["By"] == "Region" and result.stats["Not in a group"] == 2


def test_an_unlabelled_group_reads_as_its_code():
    frame = pd.DataFrame({"x": [1.0, 2.0, 3.0], "g": [1.0, 3.0, None]})
    table = describe(frame, ["x"], by="g").table
    assert list(table["g"]) == ["1", "3"]


# ─── weighted ────────────────────────────────────────────────────────────────


def test_weighted_mean_sd_and_quartiles_by_hand():
    data = _data(weight=True)
    result = describe(data.frame, ["sat"], variables=data.variables, weight="w", detail=True)
    row = _row(result.table, "sat")
    # Answers 1, 2, 3, 7 with weights 1, 2, 2, 1.
    assert row["N"] == 4 and row["Weighted N"] == 6.0 and row["Missing"] == 2
    assert row["Mean"] == 3.0  # (1 + 4 + 6 + 7) / 6
    # Σw(x − 3)² = 4 + 2 + 0 + 16 = 22; / 6, times n / (n − 1) = 4 / 3.
    assert row["SD"] == round(math.sqrt(22 / 6 * 4 / 3), 3)
    # Cumulative weights 1, 3, 5, 6 of 6: 25 % → 2, 50 % → 2, 75 % → 3.
    assert (row["Q1"], row["Median"], row["Q3"]) == (2.0, 2.0, 3.0)
    assert (row["Min"], row["Max"]) == (1.0, 7.0)
    # Skewness and kurtosis stay the unweighted ones — and say so.
    assert row["Skewness"] == 1.443
    stats = result.stats
    assert stats["Weight"] == "w" and stats["Weighted N"] == 8.0
    assert stats["Effective N"] == round(64 / 12, 1)  # (Σw)² / Σw² over every row
    assert stats["Design effect"] == round(6 / (64 / 12), 3)
    assert "skewness and kurtosis are unweighted" in stats["Note"]


def test_weighted_statistics_match_the_group_means_table():
    """Same formulas, same numbers: a reader comparing the two tables must not
    find two weighted SDs for one group."""

    frame = pd.DataFrame(
        {
            "x": [1.0, 2.0, 4.0, 7.0, 3.0, 3.0, 5.0],
            "g": [1, 1, 1, 1, 2, 2, 2],
            "w": [0.5, 2.0, 1.0, 1.5, 1.0, 3.0, 0.2],
        }
    )
    data = SurveyData(frame=frame).with_weight("w")
    ours = data.report.descriptives(["x"], by="g").to_frame()
    means = data.report.means("x", by="g", test=False).to_frame()
    for group in (1, 2):
        row = _row(ours, "x", g=str(group))
        theirs = means[means["g"] == group].iloc[0]
        assert (row["Mean"], row["SD"], row["Median"], row["N"]) == (
            theirs["Mean"],
            theirs["SD"],
            theirs["Median"],
            theirs["N"],
        )


def test_equal_weights_give_the_unweighted_mean_and_sd():
    data = _data()
    frame = data.frame.assign(w=3.0)
    weighted = describe(frame, ["sat", "age"], variables=data.variables, weight="w").table
    plain = describe(frame, ["sat", "age"], variables=data.variables).table
    for column in ("N", "Mean", "SD", "Min", "Max"):
        assert list(weighted[column]) == list(plain[column])


def test_an_answer_weighted_zero_is_set_aside_from_the_weighted_statistics():
    """A weight of 0 — or none, which counts 0 — is an answer the weighting set
    aside: the SD's n / (n − 1) counts only the answers that carry weight, and
    one answer that does has no SD (Min and Max stay those of every answer). Equal weights plus a zero give the sample SD
    of the rest: 1, 2, 3 → mean 2, SD 1 (0.943 when the zero counted in n)."""

    zero = describe(
        pd.DataFrame({"x": [1.0, 2.0, 3.0, 100.0], "w": [1.0, 1.0, 1.0, 0.0]}), ["x"], weight="w"
    )
    row = _row(zero.table, "x")
    assert (row["N"], row["Missing"], row["Mean"], row["SD"]) == (4, 0, 2.0, 1.0)
    assert row["Median"] == 2.0 and (row["Min"], row["Max"]) == (1.0, 100.0)  # every answer
    assert "rows weighted 0 are left out" in zero.stats["Note"]
    blank = describe(pd.DataFrame({"x": [1.0, 5.0], "w": [1.0, np.nan]}), ["x"], weight="w")
    row = _row(blank.table, "x")
    assert row["N"] == 2 and row["Mean"] == 1.0 and math.isnan(row["SD"])
    nothing = describe(pd.DataFrame({"x": [1.0, 5.0], "w": [0.0, 0.0]}), ["x"], weight="w")
    row = _row(nothing.table, "x")
    assert row["N"] == 2 and all(math.isnan(row[k]) for k in ("Mean", "SD", "Median"))
    # Group means' weighted SD is the same one.
    frame = pd.DataFrame(
        {"x": [1.0, 2, 3, 100, 4, 9], "g": [1, 1, 1, 1, 2, 2], "w": [1.0, 1, 1, 0, 1, 0]}
    )
    means = SurveyData(frame=frame).with_weight("w").report.means("x", by="g", test=False)
    table = means.to_frame()
    assert table["SD"].iloc[0] == 1.0 and math.isnan(table["SD"].iloc[1])
    assert table["N"].tolist() == [4, 2]  # N stays the respondents counted
    assert "| 2 | 4.0 |  | 4.0 | 2 |" in means.to_markdown()  # blank, not nan or 0.0


def test_the_accessor_and_the_table_carry_the_weight():
    table = _data(weight=True).report.descriptives(["sat", "age"])
    frame = table.to_frame()
    assert "Weighted N" in frame.columns
    assert table.stats["Weight"] == "w"
    assert "N and Missing count respondents" in table.stats["Note"]


def test_weighted_quantile_is_the_first_value_reaching_the_share():
    values = np.array([4.0, 1.0, 3.0, 2.0])
    weights = np.array([1.0, 1.0, 1.0, 1.0])
    assert weighted_quantile(values, weights, 0.5) == 2.0
    assert weighted_quantile(values, np.array([0.0, 0.0, 0.0, 5.0]), 0.5) == 2.0
    assert math.isnan(weighted_quantile(values, np.zeros(4), 0.5))


# ─── degenerate cases ────────────────────────────────────────────────────────


def test_what_is_undefined_is_blank_not_a_number():
    frame = pd.DataFrame(
        {
            "one": [5.0, None, None, None],
            "none": [None, None, None, None],
            "flat": [2.0, 2.0, 2.0, 2.0],
            "three": [1.0, 2.0, 4.0, None],
        }
    )
    table = describe(frame, ["one", "none", "flat", "three"], detail=True).table
    one, none, flat, three = (_row(table, name) for name in ("one", "none", "flat", "three"))
    assert one["N"] == 1 and one["Mean"] == 5.0 and math.isnan(one["SD"])
    assert none["N"] == 0 and none["Missing"] == 4 and math.isnan(none["Mean"])
    assert flat["SD"] == 0.0 and math.isnan(flat["Skewness"]) and math.isnan(flat["Kurtosis"])
    assert not math.isnan(three["Skewness"]) and math.isnan(three["Kurtosis"])  # n = 3


def test_a_printed_table_shows_blanks_where_to_frame_has_nan():
    frame = pd.DataFrame({"one": [5.0, None]})
    table = SurveyData(frame=frame).report.descriptives(["one"])
    assert math.isnan(table.to_frame()["SD"].iloc[0])
    assert "nan" not in table.to_markdown().lower()
    assert "nan" not in table.to_html().lower()


def test_the_design_effect_counts_the_rows_the_weighting_kept():
    frame = pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0], "w": [1.0, 3.0, 0.0, None]})
    stats = describe(frame, ["x"], weight="w").stats
    # Two rows kept, weights 1 and 3: Kish's n is 16 / 10, the deff 2 / 1.6.
    assert (stats["Weighted N"], stats["Effective N"], stats["Design effect"]) == (4.0, 1.6, 1.25)


def test_weights_that_sum_to_nothing_give_no_weighted_mean():
    frame = pd.DataFrame({"x": [1.0, 2.0], "w": [0.0, None]})
    row = _row(describe(frame, ["x"], weight="w").table, "x")
    assert row["N"] == 2 and row["Weighted N"] == 0.0 and math.isnan(row["Mean"])
    assert (row["Min"], row["Max"]) == (1.0, 2.0)


def test_what_cannot_be_described_is_refused_with_a_reason():
    frame = pd.DataFrame({"x": [1.0, 2.0], "w": [1.0, -1.0], "m": [[1, 2], [3]]})
    with pytest.raises(ValueError, match="negative"):
        describe(frame, ["x"], weight="w")
    with pytest.raises(TypeError, match="prepare.explode"):
        describe(frame, ["m"])
    with pytest.raises(KeyError, match="nope"):
        describe(frame, ["nope"])
    with pytest.raises(ValueError, match="at least one"):
        describe(frame, [])


def test_a_multiple_choice_group_gives_one_overlapping_group_per_option():
    """Grouped by a question with several answers, each option is a group of
    everyone who chose it — as Group means does — and the stats say that the
    groups overlap. It raised "unhashable type: 'list'" before."""

    variables = VariableMap()
    variables.add(
        Variable(
            "aware",
            "nominal",
            label="Aware of",
            labels={1: "Acme", 2: "Globex", 99: "Don't know"},
            missing_values=(99,),
        )
    )
    frame = pd.DataFrame(
        {
            "x": [10.0, 20.0, 30.0, 40.0, 50.0],
            "aware": [[1], [1, 2], [2], [99], []],
        }
    )
    result = describe(frame, ["x"], variables=variables, by="aware")
    table = result.table
    assert list(table["Aware of"]) == ["Acme", "Globex"]  # the missing code is no group
    # Acme: 10 and 20; Globex: 20 and 30 — the respondent who chose both is in both.
    assert (_row(table, "x", **{"Aware of": "Acme"})["Mean"]) == 15.0
    assert (_row(table, "x", **{"Aware of": "Globex"})["Mean"]) == 25.0
    assert list(table["N"]) == [2, 2]
    # Three respondents are in a group; the Don't know and the empty answer are not.
    assert result.stats["Not in a group"] == 2
    assert result.stats["Groups"].startswith("overlap: Aware of allows several answers")
    data = SurveyData(frame=frame, variables=variables)
    assert data.report.descriptives(["x"], by="aware").to_frame().equals(table)
