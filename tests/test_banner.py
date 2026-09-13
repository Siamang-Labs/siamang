"""The banner table: the cross-break, and the letters that make it a claim.

A percentage is arithmetic. A letter beside it is a *statement* — "this group is
higher than that one" — and the ways to print a confident letter that is not
true are the point of most of this file: comparing columns that are not
mutually exclusive, testing on a weighted sample as though it were unweighted,
and finding significance in a column of seven people.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from siamang.core.variable import Variable, VariableMap
from siamang.data.survey_data import SurveyData
from siamang.reporting.tables import BannerTable


def _survey(frame: pd.DataFrame, **labels: dict) -> SurveyData:
    variables = VariableMap()
    for name in frame.columns:
        if name.startswith("w"):
            variables[name] = Variable(name, "ratio", label=name)
            continue
        variables[name] = Variable(
            name, "nominal", label=name.title(), labels=labels.get(name, {})
        )
    return SurveyData(frame=frame, variables=variables)


def _two_columns(p1: float, n1: int, p2: float, n2: int) -> SurveyData:
    """A banner with exactly two columns and exactly these proportions."""
    rows = []
    for group, share, size in ((1, p1, n1), (2, p2, n2)):
        hits = round(share * size)
        rows += [{"grp": group, "ans": 1}] * hits
        rows += [{"grp": group, "ans": 2}] * (size - hits)
    return _survey(
        pd.DataFrame(rows),
        grp={1: "Left", 2: "Right"},
        ans={1: "Yes", 2: "No"},
    )


def _cell(table: BannerTable, answer: str, column: int) -> str:
    frame = table.to_frame()
    row = frame[frame["Answer"] == answer].iloc[0]
    return str(row.iloc[2 + column])


# ── the shape ───────────────────────────────────────────────────────────────


def test_the_table_is_blocks_of_columns_with_a_base_row():
    data = _survey(
        pd.DataFrame(
            {
                "sat": [1, 1, 2, 2, 1, 2],
                "region": [1, 1, 1, 2, 2, 2],
                "age": [1, 2, 1, 2, 1, 2],
            }
        ),
        sat={1: "Yes", 2: "No"},
        region={1: "North", 2: "South"},
        age={1: "Under 35", 2: "35+"},
    )
    frame = BannerTable(data=data, rows=["sat"], columns=["region", "age"]).to_frame()

    assert list(frame.columns) == [
        "Question",
        "Answer",
        "Region: North (A)",
        "Region: South (B)",
        "Age: Under 35 (C)",
        "Age: 35+ (D)",
    ]
    # Letters run across the whole banner, so a letter names a column uniquely.
    assert list(frame["Answer"]) == ["respondents", "Yes", "No"]
    assert list(frame.iloc[0][2:]) == [3, 3, 3, 3]
    assert frame.iloc[1]["Region: North (A)"].startswith("66.7% (2)")


def test_the_numbers_are_the_same_ones_the_tidy_accessor_gives():
    """Two accessors, one computation: a reader comparing them must not find a
    different percentage."""
    frame = pd.DataFrame(
        {"sat": [1, 1, 2, 2, 1, 2, 1, 1], "region": [1, 1, 1, 2, 2, 2, 2, 1]}
    )
    data = _survey(frame, sat={1: "Yes", 2: "No"}, region={1: "North", 2: "South"})

    tidy = data.tables.banner(rows=["sat"], columns=["region"]).frame
    wide = BannerTable(data=data, rows=["sat"], columns=["region"]).to_frame()

    north_yes = tidy[(tidy["row_value"] == 1) & (tidy["column_value"] == 1)]["percent"].iloc[0]
    assert wide.iloc[1]["Region: North (A)"].startswith(f"{north_yes * 100:.1f}%")


def test_it_refuses_a_banner_with_nothing_in_it():
    data = _survey(pd.DataFrame({"a": [1, 2]}), a={1: "x", 2: "y"})
    with pytest.raises(ValueError, match="row variable"):
        BannerTable(data=data, rows=[], columns=["a"]).to_frame()
    with pytest.raises(ValueError, match="banner variable"):
        BannerTable(data=data, rows=["a"], columns=[]).to_frame()


# ── the letters ─────────────────────────────────────────────────────────────


def test_a_difference_that_is_significant_gets_a_letter():
    """60% of 100 against 40% of 100: z = 2.83, p = 0.005."""
    table = BannerTable(data=_two_columns(0.6, 100, 0.4, 100), rows=["ans"], columns=["grp"])
    assert _cell(table, "Yes", 0).endswith("B")
    assert not _cell(table, "Yes", 1).endswith("A")
    # ... and the other way round on the complementary row.
    assert _cell(table, "No", 1).endswith("A")


def test_a_difference_that_is_not_significant_gets_none():
    """55% against 45% on the same bases: z = 1.41, p = 0.16."""
    table = BannerTable(data=_two_columns(0.55, 100, 0.45, 100), rows=["ans"], columns=["grp"])
    assert "A" not in _cell(table, "Yes", 1)
    assert "B" not in _cell(table, "Yes", 0)


def test_the_letter_marks_the_higher_column_not_merely_a_difference():
    table = BannerTable(data=_two_columns(0.3, 200, 0.6, 200), rows=["ans"], columns=["grp"])
    assert "A" in _cell(table, "Yes", 1)  # the right-hand column is the higher one
    assert "B" not in _cell(table, "Yes", 0)


def test_columns_from_different_banner_variables_are_never_compared():
    """They overlap — a northerner is also under 35 — so a z-test between them
    assumes something that is not true. The table does not offer it."""
    rng = np.random.default_rng(3)
    n = 400
    region = rng.choice([1, 2], n)
    data = _survey(
        pd.DataFrame(
            {
                # Answer depends on region only; age is noise.
                "ans": np.where(region == 1, 1, 2),
                "region": region,
                "age": rng.choice([1, 2], n),
            }
        ),
        ans={1: "Yes", 2: "No"},
        region={1: "North", 2: "South"},
        age={1: "Under 35", 2: "35+"},
    )
    table = BannerTable(data=data, rows=["ans"], columns=["region", "age"])
    yes = table.to_frame().iloc[1]
    # A beats B inside the region block...
    assert "B" in str(yes["Region: North (A)"])
    # ... and no cell ever carries a letter from the other block.
    assert "C" not in str(yes["Region: North (A)"])
    assert "D" not in str(yes["Region: North (A)"])
    assert "within each banner variable only" in table.stats["Test"]


def test_bonferroni_is_available_and_named():
    data = _two_columns(0.6, 100, 0.4, 100)
    plain = BannerTable(data=data, rows=["ans"], columns=["grp"])
    assert "none" in plain.stats["Correction"]
    corrected = BannerTable(
        data=data, rows=["ans"], columns=["grp"], correction="bonferroni"
    )
    assert "Bonferroni" in corrected.stats["Correction"]
    with pytest.raises(ValueError, match="correction"):
        BannerTable(data=data, rows=["ans"], columns=["grp"], correction="holm").to_frame()


def test_a_column_too_small_to_test_is_left_out_and_said_so():
    """A headline difference computed off seven people is noise with a letter
    beside it."""
    rows = [{"grp": 1, "ans": 1}] * 6 + [{"grp": 1, "ans": 2}] * 1
    rows += [{"grp": 2, "ans": 1}] * 20 + [{"grp": 2, "ans": 2}] * 80
    data = _survey(pd.DataFrame(rows), grp={1: "Tiny", 2: "Big"}, ans={1: "Yes", 2: "No"})
    table = BannerTable(data=data, rows=["ans"], columns=["grp"])

    assert "A" not in _cell(table, "Yes", 1)
    assert "B" not in _cell(table, "Yes", 0)
    assert "fewer than 30" in table.stats["Not tested"]


def test_switching_the_test_off_leaves_bare_percentages():
    table = BannerTable(data=_two_columns(0.6, 100, 0.4, 100), rows=["ans"], columns=["grp"], test=False)
    assert _cell(table, "Yes", 0) == "60.0% (60)"
    assert table.stats["Test"] == "not run"


# ── weights ─────────────────────────────────────────────────────────────────


def test_weighting_tests_on_the_effective_base_not_the_raw_count():
    """Weights make a sample behave like a smaller one. Testing on the raw n
    would manufacture significance that the data does not support — the most
    plausible way this table could lie."""

    rng = np.random.default_rng(11)
    n = 200
    group = np.repeat([1, 2], n // 2)
    answer = np.where(rng.random(n) < np.where(group == 1, 0.60, 0.42), 1, 2)
    # Wildly unequal weights: a handful of respondents carry the sample.
    weights = np.where(rng.random(n) < 0.1, 20.0, 0.5)
    frame = pd.DataFrame({"ans": answer, "grp": group, "w": weights})
    data = _survey(frame, ans={1: "Yes", 2: "No"}, grp={1: "Left", 2: "Right"})

    unweighted = BannerTable(data=data, rows=["ans"], columns=["grp"])
    weighted = BannerTable(data=data, rows=["ans"], columns=["grp"], weight="w")

    raw = unweighted.to_frame()
    raw_base = raw.iloc[0][raw.columns[2]]
    assert "effective (Kish)" in weighted.stats["Base"]
    assert weighted.stats["Weight"] == "w"
    # The effective base is far below the raw one, so a letter is harder to earn.
    assert int(raw_base) == 100
    letters_unweighted = _cell(unweighted, "Yes", 0)
    letters_weighted = _cell(weighted, "Yes", 0)
    assert "B" in letters_unweighted
    assert "B" not in letters_weighted


def test_a_missing_weight_column_is_refused_by_name():
    data = _two_columns(0.5, 50, 0.5, 50)
    with pytest.raises(ValueError, match="nope"):
        BannerTable(data=data, rows=["ans"], columns=["grp"], weight="nope").to_frame()


# ── the report surface ──────────────────────────────────────────────────────


def test_it_renders_as_markdown_with_its_stats_underneath():
    """Without to_markdown it cannot go into a report section or a live tile,
    which is most of the point of a table in this engine."""
    table = BannerTable(data=_two_columns(0.6, 100, 0.4, 100), rows=["ans"], columns=["grp"])
    markdown = table.to_markdown()
    assert "| Question | Answer |" in markdown
    assert "z-test of column proportions" in markdown
    assert table.to_html().startswith("<table")


def test_the_accessor_hands_it_the_survey():
    data = _two_columns(0.6, 100, 0.4, 100)
    table = data.report.banner(rows=["ans"], columns=["grp"])
    assert isinstance(table, BannerTable)
    assert "Answer" in table.to_frame().columns
