"""Trend: a measure over waves or dates, its points checked against arithmetic
done by hand, and the node checked, run and generated.

A tracking study's reader looks at the line; the numbers under it have to be
the ones Proportion CI and a weighted mean give for the same respondents, or
the chart and the table beside it tell two stories.
"""

from __future__ import annotations

import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import stats as scipy_stats

from siamang.core.variable import MissingValue, Variable, VariableMap
from siamang.data.survey_data import SurveyData
from siamang.reporting import trend as trend_module
from siamang.reporting.trend import TrendChart, trend

Z95 = 1.959963984540054


def _wilson(p: float, n: float) -> tuple[float, float]:
    """Wilson's score interval of the share p of n, in percent, by hand."""
    centre = (p + Z95**2 / (2 * n)) / (1 + Z95**2 / n)
    half = Z95 * math.sqrt(p * (1 - p) / n + Z95**2 / (4 * n**2)) / (1 + Z95**2 / n)
    return (centre - half) * 100, (centre + half) * 100


DOCUMENTS = Path(__file__).resolve().parent / "documents"
ROOT = Path(__file__).resolve().parents[1]


def _data(frame: pd.DataFrame, *variables: Variable) -> SurveyData:
    codebook = VariableMap()
    codebook.add_many(list(variables))
    return SurveyData(frame=frame, variables=codebook)


SAT = Variable(
    "sat",
    "ordinal",
    label="Satisfaction",
    labels={1: "Poor", 2: "Fair", 3: "Good", 4: "Very good", 5: "Excellent", 9: "Don't know"},
    missing=(MissingValue(9, "Don't know", kind="dont_know"),),
)
WAVE = Variable("wave", "ordinal", label="Wave", labels={1: "Spring", 2: "Summer", 10: "Winter"})
SEG = Variable(
    "seg",
    "nominal",
    label="Segment",
    labels={1: "New", 2: "Loyal", 99: "Refused"},
    missing=(MissingValue(99, "Refused", kind="refusal"),),
)


def _waves() -> SurveyData:
    frame = pd.DataFrame(
        {
            # Codes out of order in the data; waves are ordered by code.
            "wave": [10, 10, 10, 1, 1, 1, 1, 1, 2, 2, 2, 2],
            "sat": [5, 4, 1, 4, 5, 2, 9, 3, 1, 2, 4, 5],
            "seg": [1, 2, 2, 1, 1, 2, 2, 99, 1, 2, 2, 2],
            "w": [1.0, 2.0, 1.0, 1.0, 3.0, 1.0, 5.0, 2.0, 1.0, 1.0, 2.0, 0.0],
        }
    )
    return _data(frame, WAVE, SAT, SEG, Variable("w", "ratio"))


def _row(points, period, group=None):
    rows = points.points[points.points["period"] == period]
    if group is not None:
        rows = rows[rows["group_label"] == group]
    assert len(rows) == 1
    return rows.iloc[0]


# ── waves ──────────────────────────────────────────────────────────────────


def test_percent_over_waves_by_hand():
    points = trend(_waves(), "wave", measure="percent", variable="sat", codes=[4, 5])
    # Ordered by code, labeled by the codebook.
    assert points.periods == ["Spring", "Summer", "Winter"]
    # Spring: answers 4, 5, 2, 3 (the 9 is "Don't know", out of the base): 2 of 4.
    spring = _row(points, "Spring")
    assert spring["base"] == 4 and spring["value"] == pytest.approx(50.0)
    # Wilson's interval: 15.0 to 85.0 for 2 of 4.
    assert (spring["lower"], spring["upper"]) == pytest.approx(_wilson(0.5, 4))
    assert spring["lower"] == pytest.approx(15.0039, abs=1e-4)
    # Summer: 1, 2, 4, 5 -> 2 of 4; Winter: 5, 4, 1 -> 2 of 3.
    assert _row(points, "Summer")["value"] == pytest.approx(50.0)
    winter = _row(points, "Winter")
    assert winter["base"] == 3 and winter["value"] == pytest.approx(200 / 3)
    assert winter["upper"] == pytest.approx(_wilson(2 / 3, 3)[1])
    # Every point is under the minimum base of 30, and says so.
    assert points.points["low"].all()
    assert set(points.table["Note"]) == {"base below 30"}
    assert points.stats["Missing codes left out"] == "Satisfaction: 1 (9 = Don't know)"
    assert points.stats["Measure"] == "% choosing 4 = Very good, 5 = Excellent — Satisfaction"


def test_the_percent_is_proportion_ci_s_and_its_interval_the_bar_chart_s():
    """One code, one wave: the point is Proportion CI's, and its interval the
    one the Bar chart draws for the same share (share_interval: Wilson's, on
    Kish's effective base when weighted)."""
    from siamang.data.intervals import share_interval

    data = _waves()
    for weighted in (False, True):
        source = data.with_weight("w") if weighted else data
        points = trend(source, "wave", variable="sat", codes=4)
        spring = source.with_frame(
            source.frame[(source.frame["wave"] == 1) & (source.frame["sat"] != 9)]
        )
        expected = spring.analysis.proportion_ci("sat", 4, weighted=weighted)
        drawn = share_interval(spring.frame["sat"] == 4, spring.frame["w"] if weighted else None)
        point = _row(points, "Spring")
        assert point["value"] == pytest.approx(expected["p"] * 100)
        assert point["lower"] == pytest.approx(drawn.lower * 100)
        assert point["upper"] == pytest.approx(drawn.upper * 100)


def test_a_percent_of_0_or_100_keeps_a_band():
    """The normal approximation gave none of 40 the interval [0, 0] — certainty
    — and 1 of 40 [0, 7.3]; the Bar chart's Wilson interval, drawn beside it in
    a report, gave [0, 8.8]. They are one interval now."""
    frame = pd.DataFrame(
        {"wave": np.repeat([1, 2, 3], 40), "aware": [2] * 40 + [1] + [2] * 39 + [1, 2] * 20}
    )
    data = _data(
        frame,
        Variable("wave", "ordinal", label="Wave", labels={1: "W1", 2: "W2", 3: "W3"}),
        Variable("aware", "nominal", label="Aware", labels={1: "Yes", 2: "No"}),
    )
    points = trend(data, "wave", variable="aware", codes=1)
    none, one = _row(points, "W1"), _row(points, "W2")
    assert (none["value"], none["lower"]) == (0.0, 0.0)
    assert none["upper"] == pytest.approx(8.7622, abs=1e-4) == _wilson(0.0, 40)[1]
    assert (one["lower"], one["upper"]) == pytest.approx(_wilson(1 / 40, 40))
    assert one["lower"] > 0
    assert points.stats["Interval"] == "95% Wilson score interval, as the Bar chart draws a share's"
    # A point at 0 % sits on the frame and is drawn whole.
    ax = data.plot.trend("wave", variable="aware", codes=1).plot()
    assert ax.get_ylim()[0] == 0 and all(not c.get_clip_on() for c in ax.collections[:2])


def test_a_hollow_point_s_interval_is_in_the_table_not_on_the_axis():
    """A mean of two respondents has a t interval from -46 to 56 on a 0-10
    scale: drawn, it set the axis and flattened every line to a strip. The band
    stops at the points that have their base, and the axis fits what is drawn."""
    rng = np.random.default_rng(0)
    frame = pd.DataFrame(
        {
            "wave": np.r_[np.repeat([1, 2, 3, 4], 120), [5, 5]],
            "score": np.r_[rng.integers(4, 10, 480), [1, 9]],
        }
    )
    data = _data(
        frame,
        Variable("wave", "ordinal", label="Wave", labels={i: f"W{i}" for i in range(1, 6)}),
        Variable("score", "interval", label="Likelihood to recommend (0-10)"),
    )
    chart = data.plot.trend("wave", measure="mean", variable="score")
    last = _row(chart.points, "W5")
    assert last["low"] and last["lower"] == pytest.approx(-45.8246, abs=1e-3)  # in the table
    ax = chart.plot()
    low, high = ax.get_ylim()
    assert 4 < low < 5 < 7 < high < 8  # the points and the solid points' bands
    from matplotlib.collections import PolyCollection

    [band] = [c for c in ax.collections if isinstance(c, PolyCollection)]
    vertices = band.get_paths()[0].vertices
    assert vertices[:, 0].max() == 3  # W4: no band at the hollow W5
    assert (
        "Hollow points: fewer than 30 respondents, drawn without a band (the table gives their "
        "intervals)." in _notes_of(chart)
    )


def test_weighted_percent_and_bases_by_hand():
    points = trend(_waves().with_weight("w"), "wave", variable="sat", codes=[4, 5])
    spring = _row(points, "Spring")
    # Spring's answers 4, 5, 2, 3 weigh 1, 3, 1, 2: (1 + 3) / 7 chose 4 or 5.
    assert spring["value"] == pytest.approx(400 / 7)
    assert spring["base"] == 4 and spring["weighted_base"] == pytest.approx(7.0)
    effective = 7.0**2 / (1 + 9 + 1 + 4)  # Kish: 49 / 15
    assert spring["effective_base"] == pytest.approx(effective)
    assert (spring["lower"], spring["upper"]) == pytest.approx(_wilson(4 / 7, effective))
    # Summer: 1, 2, 4, 5 weighing 1, 1, 2, 0 -> 2 / 4; a weight of 0 is a respondent still.
    summer = _row(points, "Summer")
    assert summer["value"] == pytest.approx(50.0) and summer["base"] == 4
    table = points.table
    assert list(table.columns) == [
        "Period",
        "Percent",
        "Lower 95%",
        "Upper 95%",
        "Base",
        "Weighted base",
        "Effective base",
        "Note",
    ]
    assert table.loc[0, "Percent"] == 57.1 and table.loc[0, "Weighted base"] == 7.0
    assert points.stats["Weight"] == "w"
    assert "Kish's effective base" in points.stats["Interval"]


def test_one_line_per_group_and_a_missing_code_in_no_line():
    points = trend(_waves(), "wave", variable="sat", codes=[4, 5], by="seg")
    assert [label for _code, label in points.groups] == ["New", "Loyal"]
    # Spring, New: 4, 5 -> 100 %; Spring, Loyal: 2 (the 9 is out) -> 0 %.
    assert _row(points, "Spring", "New")["value"] == pytest.approx(100.0)
    loyal = _row(points, "Spring", "Loyal")
    assert loyal["value"] == 0.0 and loyal["base"] == 1
    # The respondent whose segment is 99 "Refused" is in no line, and counted.
    assert points.points["base"].sum() == 10
    assert "Segment: 1 (99 = Refused)" in points.stats["Missing codes left out"]
    assert list(points.table.columns[:2]) == ["Period", "Segment"]


def test_a_wave_the_codebook_declares_between_two_is_a_gap():
    frame = pd.DataFrame({"wave": [1, 1, 3, 3], "sat": [4, 1, 5, 5]})
    wave = Variable("wave", "ordinal", labels={1: "W1", 2: "W2", 3: "W3", 4: "W4"})
    points = trend(_data(frame, wave, SAT), "wave", variable="sat", codes=[4, 5])
    # W2 has no data yet but lies between; W4 lies after the last wave.
    assert points.periods == ["W1", "W2", "W3"]
    gap = _row(points, "W2")
    assert gap["base"] == 0 and np.isnan(gap["value"])
    assert points.table.loc[1, "Note"] == "no respondents"


# ── dates ──────────────────────────────────────────────────────────────────


def _dated() -> SurveyData:
    frame = pd.DataFrame(
        {
            # As a platform snapshot writes them: the responses' created_at from
            # a CSV, a runtime's started_at, a date question — and one that is not.
            "created_at": [
                "2026-01-05 09:00:00+00:00",
                "2026-01-31T23:30:00-02:00",  # 01:30 on 1 February in UTC
                "2026-01-20T10:00:00.000Z",
                "2026-04-02",
                "2026-04-30 23:59:59.123456+00:00",
                "n/a",
                None,
            ],
            "sat": [4, 5, 1, 2, 5, 5, 4],
            "score": [3.0, 5.0, 1.0, 2.0, 4.0, 5.0, 4.0],
        }
    )
    return _data(frame, SAT, Variable("score", "interval", label="Score"))


def test_months_of_iso_text_in_utc_with_the_empty_months_as_gaps():
    points = trend(_dated(), "created_at", period="month", variable="sat", codes=[4, 5])
    assert points.periods == ["Jan 2026", "Feb 2026", "Mar 2026", "Apr 2026"]
    # January: 4, 1 (the 23:30 at -02:00 is February in UTC) -> 1 of 2.
    assert _row(points, "Jan 2026")["base"] == 2
    assert _row(points, "Jan 2026")["value"] == pytest.approx(50.0)
    assert _row(points, "Feb 2026")["value"] == pytest.approx(100.0)
    assert _row(points, "Mar 2026")["base"] == 0
    assert _row(points, "Apr 2026")["value"] == pytest.approx(50.0)
    assert points.stats["Left out"] == (
        "1 without created_at; 1 whose created_at is not a date (for example 'n/a')"
    )
    assert points.stats["Time"] == "created_at, by month"


def test_iso_weeks_run_monday_to_sunday_under_their_iso_year():
    frame = pd.DataFrame(
        {
            "day": pd.to_datetime(
                ["2025-12-29", "2026-01-04", "2026-01-05", "2026-01-11", "2026-01-12"]
            ),
            "sat": [4, 1, 5, 5, 2],
        }
    )
    points = trend(_data(frame, SAT), "day", period="week", variable="sat", codes=[4, 5])
    # Monday 29 December 2025 is in ISO week 1 of 2026, as is Sunday 4 January.
    assert points.periods == ["2026-W01", "2026-W02", "2026-W03"]
    assert [_row(points, week)["base"] for week in points.periods] == [2, 2, 1]
    assert [_row(points, week)["value"] for week in points.periods] == [50.0, 100.0, 0.0]
    assert "ISO weeks, Monday to Sunday" in points.stats["Time"]


def test_a_datetime_column_with_a_zone_and_the_other_periods():
    stamps = pd.to_datetime(
        ["2025-03-31 23:00", "2025-04-01 01:00", "2025-07-15 12:00", "2026-02-01 00:00"]
    ).tz_localize("Europe/Paris")
    frame = pd.DataFrame({"at": stamps, "sat": [4, 4, 1, 5]})
    data = _data(frame, SAT)
    # 23:00 in Paris on 31 March is 21:00 UTC, and 01:00 on 1 April is 23:00 UTC on
    # 31 March: both are that day in UTC.
    days = trend(data, "at", period="day", measure="count")
    assert days.periods[:2] == ["2025-03-31", "2025-04-01"]
    assert _row(days, "2025-03-31")["value"] == 2.0
    quarters = trend(data, "at", period="quarter", measure="count")
    assert quarters.periods == ["2025 Q1", "2025 Q2", "2025 Q3", "2025 Q4", "2026 Q1"]
    assert [_row(quarters, q)["value"] for q in quarters.periods] == [2.0, 0.0, 1.0, 0.0, 1.0]
    years = trend(data, "at", period="year", measure="count")
    assert years.periods == ["2025", "2026"]


def test_the_mean_by_hand_weighted_and_not():
    data = _dated()
    points = trend(data, "created_at", period="month", measure="mean", variable="score")
    april = _row(points, "Apr 2026")  # 2.0 and 4.0
    assert april["value"] == pytest.approx(3.0)
    sd = math.sqrt(2.0)  # sample SD of 2 and 4
    margin = scipy_stats.t.ppf(0.975, 1) * sd / math.sqrt(2)
    assert april["lower"] == pytest.approx(3.0 - margin)
    frame = data.frame.assign(w=[1.0, 2.0, 3.0, 1.0, 3.0, 1.0, 1.0])
    weighted = data.with_frame(frame).with_weight("w")
    points = trend(weighted, "created_at", period="month", measure="mean", variable="score")
    # January: 3.0 and 1.0 weighing 1 and 3.
    january = _row(points, "Jan 2026")
    assert january["value"] == pytest.approx((3.0 * 1 + 1.0 * 3) / 4)  # 1.5
    variance = (1 * (3.0 - 1.5) ** 2 + 3 * (1.0 - 1.5) ** 2) / 4 * 2 / (2 - 1)
    effective = 16 / 10
    margin = scipy_stats.t.ppf(0.975, effective - 1) * math.sqrt(variance) / math.sqrt(effective)
    assert january["upper"] == pytest.approx(1.5 + margin)
    assert january["weighted_base"] == 4.0 and january["base"] == 2


def test_the_count_weighted_and_not():
    data = _waves()
    counts = trend(data, "wave", measure="count")
    assert [_row(counts, p)["value"] for p in counts.periods] == [5.0, 4.0, 3.0]
    assert list(counts.table["Count"]) == [5, 4, 3]
    weighted = trend(data.with_weight("w"), "wave", measure="count")
    assert [_row(weighted, p)["value"] for p in weighted.periods] == [12.0, 4.0, 4.0]
    assert "Lower 95%" not in weighted.table.columns
    # A count is its own base: no point of it is "low", and nothing needs a note.
    assert not counts.points["low"].any() and "Low base" not in counts.stats
    assert "Note" not in counts.table.columns


def test_a_multiple_choice_question_counts_who_chose_any_of_the_codes():
    frame = pd.DataFrame({"wave": [1, 1, 1, 2, 2], "aware": [[1, 3], [2], [], [3], [1, 2]]})
    aware = Variable("aware", "nominal", label="Aware", labels={1: "A", 2: "B", 3: "C"})
    points = trend(_data(frame, WAVE, aware), "wave", variable="aware", codes=[1, 3])
    # Wave 1: [1, 3] yes, [2] no, [] did not answer -> 1 of 2.
    assert _row(points, "Spring")["base"] == 2
    assert _row(points, "Spring")["value"] == pytest.approx(50.0)
    assert _row(points, "Summer")["value"] == pytest.approx(100.0)


def test_codes_are_found_by_their_text_and_wrong_ones_are_named():
    frame = pd.DataFrame({"wave": [1, 1], "sat": [4.0, 2.0]})  # a CSV's floats
    data = _data(frame, WAVE, SAT)
    assert _row(trend(data, "wave", variable="sat", codes="4"), "Spring")["value"] == 50.0
    with pytest.raises(ValueError, match=r"9 \(Don't know\) is a missing code of Satisfaction"):
        trend(data, "wave", variable="sat", codes=[4, 9])
    with pytest.raises(ValueError, match="Satisfaction has no answer 7; its answers are 1 = Poor"):
        trend(data, "wave", variable="sat", codes=7)
    with pytest.raises(ValueError, match="Name the answer code"):
        trend(data, "wave", variable="sat")
    with pytest.raises(ValueError, match="no column 'when'"):
        trend(data, "when", measure="count")


def test_a_mean_of_a_nominal_variable_is_refused():
    frame = pd.DataFrame({"wave": [1, 2], "seg": [1, 2]})
    with pytest.raises(ValueError, match="Segment is nominal: its codes are names"):
        trend(_data(frame, WAVE, SEG), "wave", measure="mean", variable="seg")


def test_a_multiple_choice_time_or_split_is_refused_in_a_sentence():
    frame = pd.DataFrame({"wave": [1, 2], "sat": [4, 5], "aware": [[1, 2], [2]]})
    aware = Variable("aware", "nominal", label="Aware", labels={1: "A", 2: "B"})
    data = _data(frame, WAVE, SAT, aware)
    with pytest.raises(ValueError, match="Split by needs one answer per respondent, and Aware"):
        trend(data, "wave", variable="sat", codes=[4, 5], by="aware")
    with pytest.raises(ValueError, match="Aware holds multiple-choice answers .* and Time is one"):
        trend(data, "aware", measure="count")


def test_a_point_whose_weights_sum_to_0_says_so():
    frame = pd.DataFrame({"wave": [1, 1, 2, 2], "sat": [4, 1, 5, 2], "w": [1.0, 1.0, 0.0, 0.0]})
    data = _data(frame, WAVE, SAT, Variable("w", "ratio")).with_weight("w")
    points = trend(data, "wave", variable="sat", codes=[4, 5], min_base=1)
    assert np.isnan(_row(points, "Summer")["value"])
    assert list(points.table["Note"]) == ["", "their weights sum to 0"]
    chart = data.plot.trend("wave", variable="sat", codes=[4, 5], min_base=1)
    assert "Not drawn: 1 point whose respondents' weights sum to 0." in _notes_of(chart)


def test_too_many_days_are_refused_with_the_way_out():
    frame = pd.DataFrame({"at": pd.to_datetime(["2020-01-01", "2026-01-01"]), "sat": [1, 2]})
    with pytest.raises(ValueError, match="spans 2,193 days: too many points"):
        trend(_data(frame, SAT), "at", period="day", measure="count")


# ── the chart ──────────────────────────────────────────────────────────────


def test_the_chart_draws_hollow_points_and_hands_over_its_table(tmp_path):
    pytest.importorskip("matplotlib")
    data = _waves().with_weight("w")
    chart = data.plot.trend("wave", variable="sat", codes=[4, 5], by="seg", min_base=2)
    assert isinstance(chart, TrendChart)
    table = chart.table
    assert table.to_frame().equals(chart.points.table)
    assert table.stats["Weight"] == "w"
    path = chart.save(tmp_path / "trend.png")
    assert path.stat().st_size > 5000
    assert chart.weight_note == "weighted by 'w'"
    ax = chart.plot()
    assert [text.get_text() for text in ax.get_xticklabels()] == ["Spring", "Summer", "Winter"]
    assert ax.get_legend().get_title().get_text() == "Segment"
    # New in Spring has 2 respondents, filled; Loyal in Spring has 1, hollow.
    low = chart.points.points
    assert low[(low["period"] == "Spring") & (low["group_label"] == "Loyal")]["low"].all()
    hollow = [
        collection
        for collection in ax.collections
        if len(collection.get_offsets()) and (collection.get_facecolors()[:, :3] == 1).all()
    ]
    assert hollow, "a low base is drawn hollow"
    # Under the plot, what a table says under itself: the base, the hollow
    # points, the bands, the weight and the missing codes left out.
    assert _notes_of(chart) == [
        "Base: 10 respondents who answered (weighted: 13.0); 1 to 3 per point.",
        "Hollow points: fewer than 2 respondents, drawn without a band (the table gives their "
        "intervals).",
        "Bands: 95% confidence intervals.",
        "Weighted by 'w'; the bases count respondents.",
        "Left out as missing: Satisfaction: 1 (9 = Don't know); Segment: 1 (99 = Refused).",
    ]


def _notes_of(chart) -> list[str]:
    """The notes written under a chart, one per line (short enough not to wrap)."""
    chart.plot()
    return [line for text in chart._fig.texts for line in text.get_text().split("\n")]


def _tracking(groups: int, waves: int = 4, n: int = 2400, seed: int = 2) -> SurveyData:
    """Waves of a question split by ``groups`` segments with long names."""
    rng = np.random.default_rng(seed)
    labels = {code: f"Segment number {code} of the panel, as recruited" for code in range(1, 99)}
    segment = Variable("seg", "nominal", label="Segment of the panel", labels=labels)
    wave = Variable(
        "wave",
        "ordinal",
        label="Wave",
        labels={code: f"Wave {code}: the fieldwork of month {code}" for code in range(1, 99)},
    )
    frame = pd.DataFrame(
        {
            "wave": rng.integers(1, waves + 1, n),
            "seg": rng.integers(1, groups + 1, n),
            "sat": rng.choice([1, 2, 3, 4, 5], n, p=[0.3, 0.3, 0.3, 0.06, 0.04]),
            "w": rng.choice([500.0, 1000.0, 1500.0], n),
        }
    )
    return _data(frame, wave, SAT, segment, Variable("w", "ratio"))


def _inside(figure, texts) -> bool:
    """Whether every text is drawn within the figure's width and height."""
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    box = figure.bbox
    return all(
        box.x0 - 1 <= extent.x0 and extent.x1 <= box.x1 + 1 and box.y0 - 1 <= extent.y0
        for text in texts
        if text.get_text()
        for extent in [text.get_window_extent(renderer)]
    )


def test_many_lines_never_share_a_colour_and_leave_their_bands_to_the_table():
    pytest.importorskip("matplotlib")
    from matplotlib.collections import PolyCollection

    many = _tracking(13).plot.trend("wave", variable="sat", codes=[4, 5], by="seg")
    ax = many.plot()
    colours = {tuple(np.round(line.get_color(), 3)) for line in ax.get_lines()}
    assert len(ax.get_lines()) == 13 and len(colours) == 13
    # Thirteen bands would be a fog over the lines: the table keeps the intervals.
    assert not [c for c in ax.collections if isinstance(c, PolyCollection)]
    assert (
        "No bands: the 95% intervals of 13 lines would hide one another; the table gives each "
        "point's." in " ".join(" ".join(_notes_of(many)).split())
    )
    assert {"Lower 95%", "Upper 95%"} <= set(many.table.to_frame().columns)
    few = _tracking(4).plot.trend("wave", variable="sat", codes=[4, 5], by="seg")
    bands = [c for c in few.plot().collections if isinstance(c, PolyCollection)]
    assert len(bands) == 4 and "Bands: 95% confidence intervals." in _notes_of(few)


def test_the_value_axis_ticks_whole_percents_and_separates_thousands():
    pytest.importorskip("matplotlib")
    data = _tracking(1)
    ax = data.plot.trend("wave", variable="sat", codes=5).plot()
    # About 4 %: the axis runs to 10 %, its ticks on whole percents.
    assert ax.get_ylim() == (0.0, 10.0)
    ticks = [tick for tick in ax.yaxis.get_major_locator()() if 0 <= tick <= 10]
    assert ticks and all(float(tick).is_integer() for tick in ticks)
    assert ax.yaxis.get_major_formatter()(4, 0) == "4%"
    weighted = data.with_weight("w").plot.trend("wave", measure="count")
    axis = weighted.plot().yaxis
    assert axis.get_major_formatter()(600000, 0) == "600,000"
    assert "Base: 2,400 respondents (weighted: " in _notes_of(weighted)[0]


def test_a_narrow_figure_grows_and_keeps_its_labels_inside():
    pytest.importorskip("matplotlib")
    from siamang.reporting.chart_parts import axes_points

    chart = _tracking(3, waves=7).plot.trend(
        "wave", variable="sat", codes=[4, 5], by="seg", figsize=(5, 3.5)
    )
    ax = chart.plot()
    figure = chart._fig
    # Too narrow for a legend beside the plot: under it, the figure grown
    # taller so the plot keeps a readable height.
    assert ax.get_legend() is None and len(figure.legends) == 1
    assert figure.get_figheight() > 3.5 and axes_points(ax)[1] >= 109
    # Every wave is named, and nothing runs past the figure.
    assert len([label for label in ax.get_xticklabels() if label.get_text()]) == 7
    texts = [ax.title, ax.xaxis.label, ax.yaxis.label, *ax.get_xticklabels(), *figure.texts]
    assert _inside(figure, texts)
    legend = figure.legends[0]
    assert _inside(figure, [legend.get_title(), *legend.get_texts()])


def test_a_legend_taller_than_the_plot_goes_under_it():
    pytest.importorskip("matplotlib")
    chart = _tracking(13).plot.trend("wave", variable="sat", codes=[4, 5], by="seg")
    ax = chart.plot()
    assert ax.get_legend() is None and len(chart._fig.legends) == 1
    names = [text.get_text() for text in chart._fig.legends[0].get_texts()]
    assert names[0] == "Segment number 1\nof the panel, as\nrecruited"  # wrapped
    assert _inside(chart._fig, [*chart._fig.legends[0].get_texts(), ax.title])


def test_period_labels_are_level_where_they_fit_and_slanted_where_not():
    pytest.importorskip("matplotlib")
    stamps = pd.date_range("2026-01-01", "2026-12-31", freq="D", tz="UTC")
    frame = pd.DataFrame({"at": stamps.astype(str), "sat": np.resize([1, 4, 5], len(stamps))})
    data = _data(frame, SAT)
    wide = data.plot.trend("at", variable="sat", codes=[4, 5], figsize=(12, 5)).plot()
    labels = wide.get_xticklabels()
    assert len(labels) == 12 and {label.get_rotation() for label in labels} == {0.0}
    assert labels[0].get_text() in ("Jan 2026", "Jan\n2026")
    narrow = data.plot.trend("at", variable="sat", codes=[4, 5], figsize=(3.5, 3)).plot()
    turned = narrow.get_xticklabels()
    assert {label.get_rotation() for label in turned} == {40.0}
    # By day, a label on every day would be a smear: every n-th day is named.
    days = data.plot.trend("at", period="day", measure="count").plot()
    shown = [label.get_text() for label in days.get_xticklabels()]
    assert shown[0] == "2026-01-01" and 10 < len(shown) < 60


# ── the node ───────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def questionnaire_doc():
    from siamang.model import loads

    return loads((DOCUMENTS / "brand_awareness.questionnaire.json").read_text("utf-8"))


@pytest.fixture(scope="module")
def survey(questionnaire_doc):
    from siamang.model import from_document

    return from_document(questionnaire_doc).survey


def _responses(survey) -> SurveyData:
    data = survey.simulate(n=360, seed=5)
    rng = np.random.default_rng(5)
    days = pd.Timestamp("2026-01-01", tz="UTC") + pd.to_timedelta(
        rng.integers(0, 180, len(data.frame)), unit="D"
    )
    # The platform's column as a CSV snapshot carries it.
    frame = data.frame.assign(created_at=[str(day) for day in days])
    return data.with_frame(frame)


def _trend_flow(params: dict | None = None) -> dict:
    trend_params = {
        "time": "created_at",
        "variable": "satisfaction",
        "codes": [4, 5],
        "by": "region",
        **(params or {}),
    }
    nodes = [
        ("src", "source.responses", {}),
        ("trend", "visualize.trend", trend_params),
        ("section", "output.report_section", {"heading": "Tracking"}),
        ("save", "output.save_report", {"title": "Tracking", "path": "outputs/tracking.md"}),
    ]
    edges = [
        ("src", "data", "trend", "data"),
        ("trend", "chart", "section", "items"),
        ("trend", "table", "section", "items"),
        ("section", "report", "save", "sections"),
    ]
    return {
        "schema_version": "1.0",
        "name": "tracking",
        "nodes": [{"id": i, "type": t, "params": p} for i, t, p in nodes],
        "edges": [
            {"from": {"node": a, "port": ap}, "to": {"node": b, "port": bp}}
            for a, ap, b, bp in edges
        ],
    }


def test_the_node_is_registered_with_its_parameters():
    from siamang.flow import default_registry

    spec = default_registry().get("visualize.trend")
    assert spec.outputs == {"chart": "Chart", "table": "Table"}
    assert spec.params["period"].values == ("day", "week", "month", "quarter", "year")
    assert spec.params["measure"].values == ("percent", "mean", "count")
    assert spec.params["codes"].kind == "json" and spec.params["min_base"].default == 30
    # Answer codes are asked for only with the percent, Measure variable not with the count.
    assert spec.reads("codes", {"measure": "percent"})
    assert not spec.reads("codes", {"measure": "mean"})
    assert not spec.reads("variable", {"measure": "count"})
    assert not spec.reads("band", {"measure": "count"})
    # A count is its own base: Minimum base is not read with it.
    assert spec.reads("min_base", {"measure": "mean"})
    assert not spec.reads("min_base", {"measure": "count"})
    help_text = default_registry().get("prepare.apply_weight").params["column"].help
    weighted, _unweighted = help_text.split("Unweighted, and saying so:")
    assert "Trend" in weighted


def test_check_flow_knows_the_response_timestamps_and_the_rules(questionnaire_doc):
    from siamang.flow import check_flow

    assert check_flow(_trend_flow(), questionnaire=questionnaire_doc) == []
    issues = check_flow(_trend_flow({"codes": None}), questionnaire=questionnaire_doc)
    assert [(i.code, i.message) for i in issues] == [
        (
            "PARAM_CONFLICT",
            "trend: Name the Answer codes whose percent is tracked — one code, or a list "
            "such as [4, 5].",
        )
    ]
    # With the count, the variable and its codes are not read, so not checked.
    flow = _trend_flow({"measure": "count", "variable": "nope", "codes": None})
    assert check_flow(flow, questionnaire=questionnaire_doc) == []
    flow = _trend_flow({"measure": "mean", "variable": None, "codes": None})
    assert [i.code for i in check_flow(flow, questionnaire=questionnaire_doc)] == ["PARAM_CONFLICT"]
    flow = _trend_flow({"time": "created_when"})
    assert [i.code for i in check_flow(flow, questionnaire=questionnaire_doc)] == [
        "UNKNOWN_VARIABLE"
    ]


def test_a_platform_names_the_response_timestamps_its_data_carries(questionnaire_doc):
    """RESPONSE_TIMES lists the timestamps any platform's frame may carry; a
    platform whose responses carry fewer (Studio's have no submitted_at) names
    them, so that Time = submitted_at is an unknown variable at the check
    rather than "The data has no column 'submitted_at'" at the run."""
    from siamang.flow import check_flow
    from siamang.flow.document import RESPONSE_TIMES

    carried = ("created_at", "updated_at", "started_at")
    for name in RESPONSE_TIMES:
        flow = _trend_flow({"time": name})
        assert check_flow(flow, questionnaire=questionnaire_doc) == []
        issues = check_flow(flow, questionnaire=questionnaire_doc, response_times=carried)
        if name in carried:
            assert issues == []
        else:
            assert [(i.severity, i.code, i.message) for i in issues] == [
                (
                    "error",
                    "UNKNOWN_VARIABLE",
                    f"Parameter 'time' of trend names unknown variable {name!r}.",
                )
            ]
    # None of them: data that carries none (a file, simulated answers).
    issues = check_flow(_trend_flow(), questionnaire=questionnaire_doc, response_times=())
    assert [i.code for i in issues] == ["UNKNOWN_VARIABLE"]
    issues = check_flow(
        _trend_flow({"time": "updated_at"}),
        questionnaire=questionnaire_doc,
        response_times="updated_at",
    )
    assert issues == []


@pytest.mark.parametrize(
    ("params", "message"),
    [
        (
            {"measure": "mean", "variable": "region", "codes": None},
            "trend: Region is nominal: its codes are names, not amounts, so their mean says "
            "nothing. Track the percent choosing an answer instead (Measure = percent).",
        ),
        (
            {"measure": "mean", "variable": "aware", "codes": None},
            "trend: Brands heard of (unaided) holds multiple-choice answers (lists of codes), "
            "which have no mean. Track the percent choosing an answer instead (Measure = "
            "percent).",
        ),
        (
            {"by": "aware"},
            "trend: Split by needs one answer per respondent, and Brands heard of (unaided) "
            "allows several: split by one of its options after Explode multiple choice, or "
            "choose another variable.",
        ),
        (
            {"time": "aware", "measure": "count", "variable": None, "codes": None},
            "trend: Brands heard of (unaided) holds multiple-choice answers (lists of codes), "
            "and Time is one wave or one date per respondent: choose the wave's variable or a "
            "date.",
        ),
        (
            {"variable": "trust_acme", "codes": [4, 9]},
            "trend: 9 (Refused) is a missing code of Trust: Acme, not an answer: missing codes "
            "are left out of the base. Name an answer.",
        ),
    ],
)
def test_check_flow_names_what_the_run_refuses(questionnaire_doc, survey, params, message):
    """The run's refusals, said on the canvas before it — in the run's words."""
    from siamang.flow import check_flow

    flow = _trend_flow(params)
    issues = check_flow(flow, questionnaire=questionnaire_doc)
    assert [(issue.severity, issue.code, issue.message) for issue in issues] == [
        ("error", "PARAM_CONFLICT", message)
    ]
    given = flow["nodes"][1]["params"]
    with pytest.raises(ValueError) as refused:
        trend(
            _responses(survey),
            given["time"],
            measure=given.get("measure", "percent"),
            variable=given["variable"],
            codes=given["codes"],
            by=given["by"],
        )
    assert str(refused.value) == message.removeprefix("trend: ")


def test_a_result_chart_does_not_redraw_the_trends_table(questionnaire_doc):
    """The Trend draws its own chart; its table is the chart's numbers, not a
    result for the Result chart to draw again."""
    from siamang.flow import check_flow

    flow = _trend_flow()
    flow["nodes"].append({"id": "again", "type": "visualize.result_chart", "params": {}})
    flow["edges"].append(
        {"from": {"node": "trend", "port": "table"}, "to": {"node": "again", "port": "result"}}
    )
    codes = [issue.code for issue in check_flow(flow, questionnaire=questionnaire_doc)]
    assert codes == ["RESULT_NOT_DRAWABLE"]


def test_the_node_runs_and_its_script_reproduces_it(questionnaire_doc, survey, tmp_path):
    from siamang.codegen import generate_questionnaire
    from siamang.flow import FlowRunner, generate_flow
    from siamang.io import write_snapshot
    from siamang.reporting.result_table import ResultTable

    responses = _responses(survey)
    flow = _trend_flow()
    runner_dir, script_dir = tmp_path / "runner", tmp_path / "script"
    result = FlowRunner(flow, questionnaire=survey, questionnaire_document=questionnaire_doc).run(
        sources={"src": responses}, cwd=runner_dir
    )
    assert result.ok
    table = result.output("trend", "table")
    assert isinstance(table, ResultTable)
    frame = table.to_frame()
    assert list(frame.columns[:3]) == ["Period", "Region", "Percent"]
    assert frame["Period"].iloc[0] == "Jan 2026" and len(frame) == 6 * 3
    assert table.stats["Time"] == "created_at, by month"

    code = generate_flow(flow, questionnaire_doc)
    assert code == generate_flow(flow, questionnaire_doc)
    assert ".plot.trend(" in code and 'measure="percent"' in code
    assert "band=" in code and "codes=[4, 5]" in code
    (script_dir / "survey").mkdir(parents=True)
    (script_dir / "survey" / "__init__.py").write_text("", encoding="utf-8")
    (script_dir / "survey" / "questionnaire.py").write_text(
        generate_questionnaire(questionnaire_doc), encoding="utf-8"
    )
    (script_dir / "scripts").mkdir()
    script = script_dir / "scripts" / "tracking.py"
    script.write_text(code, encoding="utf-8")
    snapshot = write_snapshot(responses, script_dir / "data" / "responses.csv")
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join([str(script_dir), str(ROOT)]),
        "MPLBACKEND": "Agg",
    }
    completed = subprocess.run(
        [sys.executable, str(script), "--data", str(snapshot)],
        cwd=script_dir,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    ours = (runner_dir / "outputs" / "tracking.md").read_text("utf-8")
    theirs = (script_dir / "outputs" / "tracking.md").read_text("utf-8")
    assert ours == theirs
    assert (
        "| Jan 2026 | Capital |" in ours
        and (script_dir / "outputs" / "tracking_fig_1.png").exists()
    )


@pytest.mark.parametrize(
    ("params", "column"),
    [
        ({"measure": "mean", "codes": None, "period": "week"}, "Mean"),
        ({"measure": "count", "variable": None, "codes": None, "by": None}, "Count"),
    ],
)
def test_every_measure_runs_weighted(questionnaire_doc, survey, params, column, tmp_path):
    from siamang.flow import FlowRunner, check_flow

    flow = _trend_flow(params)
    flow["nodes"].insert(1, {"id": "w", "type": "prepare.apply_weight", "params": {"column": "w"}})
    flow["edges"][0]["from"]["node"] = "w"
    flow["edges"].insert(
        0, {"from": {"node": "src", "port": "data"}, "to": {"node": "w", "port": "data"}}
    )
    assert check_flow(flow, questionnaire=questionnaire_doc) == []
    responses = _responses(survey)
    responses = responses.with_frame(responses.frame.assign(w=1.5))
    result = FlowRunner(flow, questionnaire=survey, questionnaire_document=questionnaire_doc).run(
        sources={"src": responses}, cwd=tmp_path
    )
    frame = result.output("trend", "table").to_frame()
    assert column in frame.columns and "Weighted base" in frame.columns
    assert result.output("trend", "chart").weight_note == "weighted by 'w'"


def test_past_four_lines_each_line_s_points_take_a_shape_of_their_own():
    """Color alone does not keep six or more lines apart for every reader,
    and past the palette two lines are two shades of one hue: past four lines
    (where the bands stop) each line's points, and its legend entry, take a
    shape of their own. Up to four, circles as before."""
    rng = np.random.default_rng(3)
    frame = pd.DataFrame(
        {
            "wave": np.tile([1, 2, 3], 300),
            "seg": np.repeat(np.arange(1, 7), 150),
            "aware": rng.integers(1, 3, 900),
        }
    )
    data = _data(
        frame,
        Variable("wave", "ordinal", label="Wave", labels={1: "W1", 2: "W2", 3: "W3"}),
        Variable("seg", "nominal", label="Segment", labels={i: f"S{i}" for i in range(1, 7)}),
        Variable("aware", "nominal", label="Aware", labels={1: "Yes", 2: "No"}),
    )

    from matplotlib.collections import PathCollection

    def shapes(ax):  # the points' marker paths, line by line
        return [
            collection.get_paths()[0].vertices.round(3).tobytes()
            for collection in ax.collections
            if isinstance(collection, PathCollection) and len(collection.get_offsets())
        ]

    six = data.plot.trend("wave", variable="aware", codes=1, by="seg").plot()
    drawn = shapes(six)
    assert len(drawn) == 6 and len(set(drawn)) == 6
    assert [line.get_marker() for line in six.get_legend().get_lines()] == list(
        trend_module.MARKERS[:6]
    )
    four = data.with_frame(frame[frame["seg"] <= 4])
    ax = four.plot.trend("wave", variable="aware", codes=1, by="seg").plot()
    assert len(set(shapes(ax))) == 1


def test_a_response_timestamp_is_offered_as_time_and_named_on_the_axis():
    """check_flow accepted the responses' created_at as Time, but a builder
    offering only the codebook's variables could not choose it, and the axis
    read "created_at (day)": Time's parameter names the timestamps a picker
    should offer, with labels, and the axis calls them by their names."""
    from siamang.flow import default_registry

    time = default_registry().get("visualize.trend").params["time"]
    assert time.to_json()["extra"][0] == {
        "name": "created_at",
        "label": "Response date (created_at)",
    }
    assert {item["name"] for item in time.to_json()["extra"]} == {
        "created_at",
        "updated_at",
        "started_at",
        "submitted_at",
    }
    frame = pd.DataFrame(
        {
            "created_at": ["2026-05-25 09:00:00+00:00", "2026-06-02 10:00:00+00:00"] * 20,
            "aware": [1, 2] * 20,
        }
    )
    data = _data(frame, Variable("aware", "nominal", label="Aware", labels={1: "Yes", 2: "No"}))
    points = trend(data, "created_at", period="month", variable="aware", codes=1)
    assert points.xlabel == "Response date (month)"
    labelled = _data(
        frame,
        Variable("aware", "nominal", label="Aware", labels={1: "Yes", 2: "No"}),
        Variable("created_at", "nominal", label="Interview time"),
    )
    assert trend(labelled, "created_at", variable="aware", codes=1).xlabel == (
        "Interview time (month)"
    )
