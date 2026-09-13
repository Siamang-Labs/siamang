"""siamang.data.respondents / quality / weights / stats — frame-level helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from siamang.core import Variable, VariableMap
from siamang.data import SurveyData, quality, respondents, stats, weights

# ─── respondents ─────────────────────────────────────────────────────────────


def _responses() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "respondent_id": ["a", "b", "a", None, "c"],
            "submitted_at": ["10:00", "10:05", "10:09", "10:10", "10:12"],
            "duration_s": [120, 200, 90, 30, 180],
            "consider_ev": [1, 5, 3, None, 4],
        }
    )


def test_dedup_keeps_last_per_respondent_and_anonymous():
    out = respondents.dedup_responses(_responses(), order_by="submitted_at", keep="last")
    assert len(out) == 4
    a_rows = out[out["respondent_id"] == "a"]
    assert len(a_rows) == 1
    assert int(a_rows.iloc[0]["duration_s"]) == 90


def test_dedup_keep_first():
    out = respondents.dedup_responses(_responses(), keep="first")
    assert int(out[out["respondent_id"] == "a"].iloc[0]["duration_s"]) == 120
    with pytest.raises(ValueError, match="keep"):
        respondents.dedup_responses(_responses(), keep="middle")


def test_dedup_missing_id_column_returns_copy():
    df = pd.DataFrame({"x": [1, 2]})
    out = respondents.dedup_responses(df)
    assert out.equals(df) and out is not df


def test_completion_time_prefers_duration_column():
    assert list(respondents.completion_time(_responses())) == [120, 200, 90, 30, 180]


def test_completion_time_from_timestamps_when_no_duration():
    df = pd.DataFrame(
        {"started_at": ["2026-01-01T10:00:00"], "submitted_at": ["2026-01-01T10:02:30"]}
    )
    assert respondents.completion_time(df).iloc[0] == 150.0
    assert respondents.completion_time(pd.DataFrame({"x": [1, 2]})).isna().all()


def test_partial_flag_marks_missing_required():
    out = respondents.partial_flag(_responses(), ["consider_ev"])
    assert list(out) == [False, False, False, True, False]
    assert respondents.partial_flag(_responses(), ["nonexistent"]).all()


def test_speeders_flag():
    out = respondents.speeders(_responses(), min_seconds=100)
    assert list(out) == [False, False, True, True, False]
    df = pd.DataFrame({"duration_s": [None, 10]})
    assert list(respondents.speeders(df, min_seconds=60)) == [False, True]


# ─── quality ─────────────────────────────────────────────────────────────────

BATTERY = ["q1", "q2", "q3", "q4", "q5"]


def _battery() -> pd.DataFrame:
    """Five respondents: honest, flatliner, flatliner's twin, near-flat, partial."""

    return pd.DataFrame(
        {
            "q1": [1, 4, 4, 4, 3],
            "q2": [5, 4, 4, 4, None],
            "q3": [2, 4, 4, 5, 1],
            "q4": [4, 4, 4, 4, 2],
            "q5": [3, 4, 4, 4, 5],
        }
    )


def test_straightlining_catches_flat_rows_and_ignores_incomplete_ones():
    out = quality.straightlining(_battery(), BATTERY)
    assert list(out) == [False, True, True, False, False]
    # The near-flat row (4,4,5,4,4) needs a tolerance to count.
    loose = quality.straightlining(_battery(), BATTERY, max_sd=0.5)
    assert list(loose) == [False, True, True, True, False]


def test_straightlining_needs_a_battery_worth_measuring():
    frame = _battery()
    assert not quality.straightlining(frame, ["q1", "q2"]).any()
    assert not quality.straightlining(frame, ["nope", "gone", "missing"]).any()
    assert not quality.straightlining(frame, None).any()


def test_inconsistency_skips_pairs_it_cannot_compare():
    frame = pd.DataFrame({"age": [30, 40], "age_again": [30, 41], "only_once": [1, 2]})
    assert list(quality.inconsistency(frame, {"age": "age_again"})) == [False, True]
    # A pair naming a column the frame does not have is skipped, not counted.
    assert not quality.inconsistency(frame, {"only_once": "never_asked"}).any()
    assert not quality.inconsistency(frame, None).any()


def test_duplicate_pattern_flags_every_member_of_a_colliding_group():
    out = quality.duplicate_pattern(_battery(), BATTERY)
    assert list(out) == [False, True, True, False, False]
    assert not quality.duplicate_pattern(_battery(), BATTERY, min_items=9).any()


def test_attention_failed_only_judges_answered_checks():
    frame = pd.DataFrame({"trap": [3, 1, None]})
    assert list(quality.attention_failed(frame, {"trap": 3})) == [False, True, False]
    assert not quality.attention_failed(frame, None).any()


def test_checks_compare_numbers_as_numbers_not_as_text():
    """One missing answer makes the column float — 3 arrives as 3.0.

    Comparing those as strings flagged every honest respondent, which is worse
    than not checking at all: the fraud screen would condemn the whole sample.
    """

    frame = pd.DataFrame({"trap": [3, 1, None], "a": [30, 40, None], "b": [30, 41, 40]})
    assert list(quality.attention_failed(frame, {"trap": 3})) == [False, True, False]
    assert list(quality.inconsistency(frame, {"a": "b"})) == [False, True, False]
    # Text answers still compare as text.
    words = pd.DataFrame({"trap": ["blue", "red"]})
    assert list(quality.attention_failed(words, {"trap": "blue"})) == [False, True]


def test_quality_flags_name_every_failed_check_in_order():
    frame = _battery()
    frame["trap"] = [3, 3, 1, 3, 3]
    frame["age"] = [30, 40, 40, 30, 30]
    frame["age_again"] = [30, 41, 40, 30, 30]
    flags = quality.quality_flags(
        frame,
        items=BATTERY,
        pairs={"age": "age_again"},
        expected={"trap": 3},
    )
    assert flags.tolist() == [
        "",
        "straightlining; inconsistency; duplicate",
        "straightlining; duplicate; attention",
        "",
        "",
    ]
    assert quality.quality_score(flags).tolist() == [0, 3, 3, 0, 0]


def test_quality_flags_with_nothing_configured_flags_nobody():
    # The flow renders an unset mapping parameter as the literal None, so this
    # is what the generated script passes for a check the author left blank.
    flags = quality.quality_flags(_battery(), items=None, pairs=None, expected=None)
    assert flags.tolist() == [""] * 5
    assert quality.quality_score(flags).tolist() == [0] * 5


def test_flags_reach_the_codebook_through_with_derived():
    """What ``prepare.quality`` relies on: with_frame would lose the metadata."""

    variables = VariableMap()
    for name in BATTERY:
        variables.add(Variable(name, "ordinal", label=name.upper()))
    data = SurveyData(frame=_battery(), variables=variables)
    flags = quality.quality_flags(data.frame, items=BATTERY)
    scored = data.with_derived(
        "quality_flags", flags, label="Quality flags", scale="nominal"
    ).with_derived(
        "quality_score", quality.quality_score(flags), label="Checks failed", scale="ratio"
    )

    assert "quality_flags" in scored.frame.columns
    book = scored.codebook()
    assert set(book["name"]) == set(BATTERY) | {"quality_flags", "quality_score"}
    assert scored.variables["quality_score"].role == "derived"
    # The original is untouched: every helper here returns a new SurveyData.
    assert "quality_flags" not in data.frame.columns


# ─── weights ─────────────────────────────────────────────────────────────────


def test_cell_weights_match_targets_mean_one():
    df = pd.DataFrame({"g": ["a", "a", "a", "b"]})
    w = weights.cell_weights(df, "g", {"a": 0.5, "b": 0.5})
    assert w.mean() == pytest.approx(1.0)
    assert w[df["g"] == "b"].sum() / w.sum() == pytest.approx(0.5, abs=0.01)
    # Counts are normalized like proportions.
    assert weights.cell_weights(df, "g", {"a": 50, "b": 50}).equals(w)


def test_cell_weights_errors():
    df = pd.DataFrame({"g": ["a", "b"]})
    with pytest.raises(KeyError):
        weights.cell_weights(df, "nope", {"a": 1})
    with pytest.raises(ValueError, match="empty"):
        weights.cell_weights(df, "g", {})
    with pytest.raises(ValueError, match="non-negative"):
        weights.cell_weights(df, "g", {"a": -1, "b": 2})


def test_rake_weights_converge_to_margins():
    rng = np.random.default_rng(0)
    df = pd.DataFrame(
        {
            "region": rng.choice(["N", "S"], size=200, p=[0.7, 0.3]),
            "age": rng.choice(["y", "o"], size=200, p=[0.6, 0.4]),
        }
    )
    w = weights.rake_weights(df, {"region": {"N": 0.5, "S": 0.5}, "age": {"y": 0.5, "o": 0.5}})
    assert w.mean() == pytest.approx(1.0)
    assert w[df["region"] == "N"].sum() / w.sum() == pytest.approx(0.5, abs=0.02)
    assert w[df["age"] == "y"].sum() / w.sum() == pytest.approx(0.5, abs=0.02)
    with pytest.raises(KeyError):
        weights.rake_weights(df, {"nope": {"x": 1.0}})
    with pytest.raises(ValueError, match="margin"):
        weights.rake_weights(df, {})


def test_weight_cap_bounds_and_renormalizes():
    df = pd.DataFrame({"g": ["a"] * 19 + ["b"]})  # b is 5 % of the sample, target 50 %
    uncapped = weights.cell_weights(df, "g", {"a": 0.5, "b": 0.5})
    assert uncapped.max() > 3
    capped = weights.cell_weights(df, "g", {"a": 0.5, "b": 0.5}, cap=3)
    assert capped.max() <= 3 + 1e-9
    assert capped.mean() == pytest.approx(1.0)
    with pytest.raises(ValueError, match="cap"):
        weights.cell_weights(df, "g", {"a": 0.5, "b": 0.5}, cap=1)


def test_effective_sample_size():
    assert weights.effective_sample_size(pd.Series([1.0, 1.0, 1.0, 1.0])) == 4.0
    uneven = weights.effective_sample_size(pd.Series([0.5, 1.5, 0.5, 1.5]))
    assert 0 < uneven < 4
    assert weights.effective_sample_size(pd.Series([], dtype=float)) == 0.0


# ─── stats ───────────────────────────────────────────────────────────────────


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "region": ["N", "S", "N", "S", "N", "S", "N", "S"],
            "consider_ev": [1, 5, 2, 4, 1, 5, 3, 4],
            "w": [1.0, 1.0, 1.0, 1.0, 2.0, 2.0, 2.0, 2.0],
        }
    )


def test_frequencies_counts_and_percent():
    out = stats.frequencies(_frame(), "region")
    assert list(out["value"]) == ["N", "S"]
    assert list(out["count"]) == [4, 4]
    assert list(out["percent"]) == [50.0, 50.0]
    weighted = stats.frequencies(_frame(), "region", weight="w")
    assert dict(zip(weighted["value"], weighted["count"], strict=True)) == {"N": 6, "S": 6}
    with pytest.raises(KeyError):
        stats.frequencies(_frame(), "nope")
    with pytest.raises(KeyError):
        stats.frequencies(_frame(), "region", weight="nope")


def test_crosstab_counts_and_percentages():
    ct = stats.crosstab(_frame(), "region", "consider_ev")
    assert ct.loc["N", 1] == 2 and ct.loc["S", 5] == 2
    pct = stats.crosstab(_frame(), "region", "consider_ev", normalize="index")
    assert pct.loc["N"].sum() == pytest.approx(100.0, abs=0.1)
    weighted = stats.crosstab(_frame(), "region", "consider_ev", weight="w")
    assert weighted.loc["N", 1] == 3.0


def test_chi2_returns_stats_and_cramers_v():
    res = stats.chi2(_frame(), "region", "consider_ev")
    assert set(res) == {"chi2", "dof", "p", "cramers_v", "n"}
    assert res["n"] == 8
    assert 0.0 <= res["cramers_v"] <= 1.0
    assert 0.0 <= res["p"] <= 1.0
