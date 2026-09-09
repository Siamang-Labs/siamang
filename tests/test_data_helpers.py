"""siamang.data.respondents / weights / stats — frame-level pipeline helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from siamang.data import respondents, stats, weights

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
