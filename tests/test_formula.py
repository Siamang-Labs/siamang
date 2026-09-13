"""The formula language: what it computes, and what it refuses.

Two things are being tested, and the second matters as much as the first. A
formula has to produce the right number — but it also has to fail out loud, at
the character, before anybody runs anything, because the alternative is a
column of NaN that looks exactly like a question nobody answered.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from siamang.data import formula as F
from siamang.data.survey_data import SurveyData

FRAME = pd.DataFrame(
    {
        "a": [1.0, 2.0, None, 4.0],
        "b": [10.0, 0.0, 5.0, 2.0],
        "words": ["yes", "no", "maybe", "yes"],
    }
)


def values(text: str) -> list[float]:
    return [round(v, 6) if v == v else v for v in F.evaluate(text, FRAME)]


# ── what it computes ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("a + b", [11.0, 2.0, None, 6.0]),
        ("b - a", [9.0, -2.0, None, -2.0]),
        ("a * 2", [2.0, 4.0, None, 8.0]),
        ("b / 2", [5.0, 0.0, 2.5, 1.0]),
        ("-a", [-1.0, -2.0, None, -4.0]),
        # Precedence and parentheses, the thing a hand-written parser gets wrong.
        ("1 + 2 * 3", [7.0] * 4),
        ("(1 + 2) * 3", [9.0] * 4),
        ("2 * 3 + 1", [7.0] * 4),
        ("12 / 2 / 3", [2.0] * 4),
        ("1 - 2 - 3", [-4.0] * 4),
    ],
)
def test_arithmetic(text, expected):
    got = values(text)
    assert len(got) == len(expected)
    for actual, want in zip(got, expected, strict=True):
        assert (actual != actual) if want is None else actual == want


def test_functions_work_row_by_row():
    assert values("mean(a, b)") == [5.5, 1.0, 5.0, 3.0]
    assert values("sum(a, b)") == [11.0, 2.0, 5.0, 6.0]
    assert values("min(a, b)") == [1.0, 0.0, 5.0, 2.0]
    assert values("max(a, b)") == [10.0, 2.0, 5.0, 4.0]
    assert values("abs(0 - b)") == [10.0, 0.0, 5.0, 2.0]
    assert values("round(b / 3, 2)") == [3.33, 0.0, 1.67, 0.67]
    assert values("log(b, 10)")[0] == 1.0
    assert values("log(b)")[0] == round(math.log(10), 6)


def test_coalesce_is_how_you_say_treat_blank_as_zero():
    """Deliberately explicit: the default is that missing stays missing, and a
    researcher who wants otherwise says so in one visible place."""
    assert values("coalesce(a, 0)") == [1.0, 2.0, 0.0, 4.0]
    assert values("coalesce(a, b)") == [1.0, 2.0, 5.0, 4.0]


def test_if_then_else_chooses_per_row():
    assert values("if a > 1 then 100 else 0") == [0.0, 100.0, 0.0, 100.0]
    assert values("if a >= 2 and b > 1 then a else -1") == [-1.0, -1.0, -1.0, 4.0]
    assert values("if not (a > 1) then 1 else 0") == [1.0, 0.0, 1.0, 0.0]
    assert values("if a = 1 or b = 5 then 1 else 0") == [1.0, 0.0, 1.0, 0.0]


def test_a_bare_condition_is_a_zero_one_indicator():
    """The old `derive` produced exactly this, so the new one has to as well —
    otherwise the cheap case would need the other node."""
    assert values("a >= 2") == [0.0, 1.0, 0.0, 1.0]


# ── what it refuses, and where ──────────────────────────────────────────────


def test_missing_stays_missing_rather_than_becoming_zero():
    """A respondent who skipped a question has no value. Arithmetic on it must
    not invent one — a zero would drag every mean downstream."""
    assert values("a + 1")[2] != values("a + 1")[2]  # NaN
    assert values("mean(a, b)")[2] == 5.0  # ... but an aggregate skips it


def test_dividing_by_zero_gives_missing_not_infinity():
    """An infinity reads as a number all the way into the report."""
    got = F.evaluate("a / b", FRAME)
    assert not np.isinf(got).any()
    assert got[1] != got[1]  # 2 / 0 is missing


def test_a_literal_zero_divisor_is_refused_before_anything_runs():
    with pytest.raises(F.FormulaError) as caught:
        F.parse("a / 0")
    assert "dividing by zero" in str(caught.value)


def test_log_of_a_non_positive_number_is_missing():
    got = F.evaluate("log(b)", FRAME)
    assert got[1] != got[1]  # log(0)


@pytest.mark.parametrize(
    ("text", "fragment"),
    [
        ("", "empty"),
        ("a +", "ends in the middle"),
        ("a $ b", "does not belong"),
        ("((a)", "closing ')'"),
        ("a) + 1", "left over"),
        ("foo(a)", "no function called 'foo'"),
        ("if a > 1 then 2", "needs an 'else'"),
        ("if a > 1 else 2", "needs a 'then'"),
        ("round(a, b)", "has to be a plain number"),
        ("round()", "takes 1"),
        ("abs(a, b)", "takes 1"),
        ("then + 1", "cannot start a value"),
    ],
)
def test_what_it_cannot_read_it_reports(text, fragment):
    with pytest.raises(F.FormulaError) as caught:
        F.parse(text)
    assert fragment in str(caught.value)


def test_every_error_points_at_a_character():
    """The position is what lets an editor underline rather than repeat."""
    with pytest.raises(F.FormulaError) as caught:
        F.parse("a + b $ c")
    assert caught.value.position == 6
    assert "character 7" in caught.value.at()


def test_an_unknown_variable_is_named_at_evaluation():
    with pytest.raises(F.FormulaError, match="no variable named 'nope'"):
        F.evaluate("nope + 1", FRAME)


def test_a_column_of_words_is_refused_rather_than_silently_emptied():
    """pd.to_numeric(errors="coerce") would give a column of NaN that looks
    exactly like a question nobody answered."""
    with pytest.raises(F.FormulaError, match="holds no numbers"):
        F.evaluate("words + 1", FRAME)


def test_nesting_is_bounded():
    with pytest.raises(F.FormulaError, match="too deeply"):
        F.parse("(" * 64 + "a" + ")" * 64)


def test_length_is_bounded():
    with pytest.raises(F.FormulaError, match="too long"):
        F.parse("a + " * 1000 + "a")


def test_nothing_is_executed():
    """The parser knows names and numbers. It does not know Python."""
    for attack in ("__import__('os')", "a.__class__", "open('x')", "a if a else b"):
        with pytest.raises(F.FormulaError):
            F.parse(attack)


# ── the codebook side ───────────────────────────────────────────────────────


def test_variables_are_reported_for_checking_against_a_codebook():
    assert F.parse("if age < 30 then round(spend / 12, 2) else 0").variables() == {
        "age",
        "spend",
    }
    assert F.check("a + missing_one", known=["a"]) == ["missing_one"]


def test_derive_formula_registers_the_variable_it_writes():
    """A column added without a Variable is invisible to describe(), to the
    dictionary beside an export, and to any node that names it later."""
    data = SurveyData(frame=pd.DataFrame({"spend_year": [1200.0, 600.0, None]}))
    out = data.derive_formula("spend_month", "round(spend_year / 12, 2)")

    assert list(out.frame["spend_month"])[:2] == [100.0, 50.0]
    assert out.variables is not None
    variable = out.variables["spend_month"]
    assert variable.role == "derived"
    assert variable.scale == "ratio"
    # The label defaults to the formula: it says exactly how the number was made
    # and travels with the codebook into every export.
    assert variable.label == "round(spend_year / 12, 2)"


def test_derive_formula_keeps_an_explicit_label_and_scale():
    data = SurveyData(frame=pd.DataFrame({"age": [25, 40, 62]}))
    out = data.derive_formula(
        "band",
        "if age < 30 then 1 else 2",
        label="Age band",
        scale="ordinal",
        labels={1: "Under 30", 2: "30+"},
    )
    assert list(out.frame["band"]) == [1.0, 2.0, 2.0]
    assert out.variables is not None
    assert out.variables["band"].label == "Age band"
    assert out.variables["band"].scale == "ordinal"
    assert out.variables["band"].labels == {1: "Under 30", 2: "30+"}
