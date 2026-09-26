"""Trend: a measure over waves or dates, one line per group.

A tracking study asks the same question wave after wave, or keeps its survey
open and reads it by the month. What its reader wants is one picture — did it
go up — and beside it the numbers the picture is drawn from, with the base of
every point, because a monthly point of 14 respondents moves by chance alone.

:func:`trend` computes the points once; :class:`TrendChart` draws them and
hands the same numbers over as a table (``chart.table``), so a report, the
Live screen and the chart can never disagree.

**Time** is either a wave code or a date:

* a variable of codes (``wave`` 1, 2, 3 …) gives one point per code, ordered
  by code, with the codebook's value labels on the axis; a code the codebook
  declares between the first and the last wave found is kept as a gap;
* a date or datetime column — a ``datetime64`` column, or text in ISO 8601 as a
  platform snapshot writes it (``2026-05-25 09:00:00+00:00``, a runtime's
  ``2026-05-25T09:00:00.000Z``, a date question's ``2026-05-25``) — is grouped
  by ``period``: ``day``, ``week`` (ISO weeks, Monday to Sunday, labelled by
  ISO year and week number: ``2026-W22``), ``month``, ``quarter`` or ``year``.
  Times with a time zone are read in UTC. Every period between the first and
  the last is on the axis, an empty one as a gap.

**Measure** is the percent choosing one or several answer codes (a top-2 box
is ``[4, 5]``; for a multiple-choice question, choosing any of them), the mean
of a numeric variable, or the count of respondents. Weighted data gives
weighted points and a weighted base per point; the confidence band is a
share's Wilson score interval (the Bar chart's, which keeps a width at 0 % and
100 %), or the mean's t interval, on Kish's effective base when weighted. A
point below ``min_base`` is drawn without its band, which the table gives.

The codebook's missing codes of Time, the measure and Split by are left out
and counted, and so are rows without a time or whose text is not a date. A
percent or a mean whose base (respondents) is below ``min_base`` is drawn
hollow and noted in the table; a count is its own base. A multiple-choice
question as Time or Split by — several groups for one respondent — is refused
in a sentence.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

from siamang.reporting.chart_parts import (
    Footnote,
    axes_points,
    chars_in,
    font_size,
    legend_below,
    percent_axis,
    series_colours,
    thousands_axis,
    wrap,
)
from siamang.reporting.charts import SurveyChart, _get_label, _get_value_labels, _require_matplotlib

if TYPE_CHECKING:
    from siamang.data.survey_data import SurveyData
    from siamang.reporting.result_table import ResultTable

__all__ = [
    "MEASURES",
    "PERIODS",
    "TrendChart",
    "TrendPoints",
    "trend",
]

#: How a date is grouped into points.
PERIODS = ("day", "week", "month", "quarter", "year")
#: What each point is.
MEASURES = ("percent", "mean", "count")

#: More points than this is a period chosen too short for the span, not a chart.
MAX_POINTS = 500
#: The most lines drawn with their confidence bands: more bands hide one
#: another and the lines, and the table gives each point's interval.
MAX_BANDS = 4
#: Past ``MAX_BANDS`` lines each line's points also take a shape of their own
#: (in the legend too): colour alone does not keep six or more lines apart for
#: every reader, and past the palette two lines are two shades of one hue.
MARKERS = ("o", "s", "^", "D", "v", "P", "X", "*", "p", "h", "<", ">")

_FREQUENCIES = {"day": "D", "week": "W-SUN", "month": "M", "quarter": "Q", "year": "Y"}
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


@dataclass(frozen=True)
class TrendPoints:
    """The points of a trend, and what a reader needs to know about them."""

    #: One row per period and group, as the table shows it (rounded).
    table: pd.DataFrame
    #: The same rows unrounded: ``position`` (on the time axis), ``period``,
    #: ``group`` (the code, None without Split by), ``group_label``, ``value``,
    #: ``lower``, ``upper``, ``base``, ``weighted_base``, ``effective_base``,
    #: ``low``.
    points: pd.DataFrame
    #: The time axis, in order: one label per period (or wave).
    periods: list[str]
    #: ``(code, label)`` per line; one ``(None, "")`` without Split by.
    groups: list[tuple[Any, str]]
    stats: dict[str, Any]
    measure: str
    title: str
    ylabel: str
    xlabel: str
    group_title: str | None
    weight: str | None
    min_base: int
    confidence: float
    #: The codebook's answer codes of a mean's variable (its axis), if any.
    scale_codes: tuple[float, ...] = ()


def trend(
    data: SurveyData,
    time: str,
    *,
    period: str = "month",
    measure: str = "percent",
    variable: str | None = None,
    codes: Any = None,
    by: str | None = None,
    min_base: int = 30,
    confidence: float = 0.95,
) -> TrendPoints:
    """The points of ``measure`` over ``time``, one line per group of ``by``.

    See the module's documentation for what each argument accepts. Raises
    ``ValueError`` with a sentence for the reader when the data cannot give a
    trend (no such column, a code that is not an answer, a mean of names).
    """

    if measure not in MEASURES:
        raise ValueError(f"measure must be one of {', '.join(MEASURES)}; got {measure!r}.")
    if period not in PERIODS:
        raise ValueError(f"period must be one of {', '.join(PERIODS)}; got {period!r}.")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1.")
    frame = data.frame
    if not frame.index.is_unique:
        frame = frame.reset_index(drop=True)
    for role, name in (("Time", time), ("Measure variable", variable), ("Split by", by)):
        if name is not None and name not in frame.columns:
            raise ValueError(f"The data has no column {name!r} to read {role} from.")
    if measure != "count" and not variable:
        raise ValueError(f"A trend of the {measure} needs a Measure variable.")
    wanted = _codes_list(codes) if measure == "percent" else []
    if measure == "percent" and not wanted:
        raise ValueError(
            "Name the answer code(s) whose percent is tracked: one code, or a list such as "
            "[4, 5] (a top-2 box)."
        )
    weights = _weights_of(data, frame)

    from siamang.data import multi
    from siamang.data.inference import missing_codes_note, without_missing_codes

    if multi.is_multi(frame[time]):
        raise ValueError(
            f"{_get_label(data, time)} holds multiple-choice answers (lists of codes), and Time "
            "is one wave or one date per respondent: choose the wave's variable or a date."
        )
    if by and multi.is_multi(frame[by]):
        raise ValueError(
            f"Split by needs one answer per respondent, and {_get_label(data, by)} allows "
            "several: split by one of its options after Explode multiple choice, or choose "
            "another variable."
        )

    columns = [name for name in (time, variable, by) if name]
    cleaned, left_out = without_missing_codes(frame, columns, data.variables)

    # ── time ──
    keys, periods, time_note, dates, not_dates = _time_axis(data, cleaned[time], time, period)
    has_time = keys >= 0
    stats: dict[str, Any] = {}

    # ── groups ──
    if by:
        group_values = _ordered_values(data, cleaned[by], by)
        position = {_code_text(code): index for index, code in enumerate(group_values)}
        group_of = np.array(
            [
                position.get(_code_text(value), -1) if pd.notna(value) else -1
                for value in cleaned[by]
            ],
            dtype=int,
        )
        by_labels = _get_value_labels(data, by)
        groups = [(code, str(by_labels.get(code, _code_text(code)))) for code in group_values]
    else:
        group_of = np.zeros(len(cleaned), dtype=int)
        groups = [(None, "")]

    # ── the measure ──
    values = np.ones(len(cleaned), dtype=float)
    answered = np.ones(len(cleaned), dtype=bool)
    scale_codes: tuple[float, ...] = ()
    var_label = _get_label(data, variable) if variable else ""
    if measure == "percent":
        assert variable is not None
        series = cleaned[variable]
        chosen_codes = _answer_codes(data, series, variable, wanted)
        labels = _get_value_labels(data, variable)
        named = list(
            dict.fromkeys(
                f"{_code_text(code)} = {labels[code]}" if code in labels else _code_text(code)
                for code in chosen_codes
            )
        )
        if multi.is_multi(series):
            answered = multi.responded(series).to_numpy(dtype=bool)
            picked = np.zeros(len(series), dtype=bool)
            for code in chosen_codes:
                picked |= multi.reach(series, code).fillna(False).to_numpy(dtype=bool)
        else:
            answered = series.notna().to_numpy(dtype=bool)
            picked = series.isin(chosen_codes).to_numpy(dtype=bool)
        values = picked.astype(float)
        texts = [str(labels.get(code, _code_text(code))) for code in chosen_codes]
        title = f"{var_label}: % {_joined(texts)}"
        ylabel = "%"
        stats["Measure"] = f"% choosing {', '.join(named)} — {var_label}"
        stats["Base"] = f"respondents who answered {var_label}, per point"
    elif measure == "mean":
        assert variable is not None
        series = cleaned[variable]
        variable_spec = data.variables.get(variable) if data.variables is not None else None
        if multi.is_multi(series):
            raise ValueError(
                f"{var_label} holds multiple-choice answers (lists of codes), which have no mean. "
                "Track the percent choosing an answer instead (Measure = percent)."
            )
        if variable_spec is not None and variable_spec.scale == "nominal":
            raise ValueError(
                f"{var_label} is nominal: its codes are names, not amounts, so their mean says "
                "nothing. Track the percent choosing an answer instead (Measure = percent)."
            )
        numbers = pd.to_numeric(series, errors="coerce")
        lost = series.notna() & numbers.isna()
        if lost.any():
            sample = series[lost].iloc[0]
            raise ValueError(
                f"{var_label} holds text that is not a number (for example {sample!r}), so it "
                "has no mean. Recode it to numeric codes first."
            )
        answered = numbers.notna().to_numpy(dtype=bool)
        values = numbers.fillna(0.0).to_numpy(dtype=float)
        if variable_spec is not None:
            declared = [
                float(code)
                for code in variable_spec.labels
                if code not in variable_spec.missing_values
                and isinstance(code, int | float)
                and not isinstance(code, bool)
            ]
            scale_codes = tuple(sorted(declared))
        title = f"Mean {var_label}"
        ylabel = "Mean"
        stats["Measure"] = f"mean of {var_label}"
        stats["Base"] = f"respondents who answered {var_label}, per point"
    else:
        title = "Respondents"
        ylabel = "Respondents"
        stats["Measure"] = "count of respondents" + (
            " (sum of weights)" if weights is not None else ""
        )
        stats["Base"] = "respondents per point"

    kept = has_time & (group_of >= 0)
    rows = np.flatnonzero(kept & answered)
    cells: dict[tuple[int, int], np.ndarray] = {}
    if len(rows):
        order = pd.DataFrame({"t": keys[rows], "g": group_of[rows], "row": rows})
        for (t, g), part in order.groupby(["t", "g"], sort=False)["row"]:
            cells[(int(t), int(g))] = part.to_numpy()

    records: list[dict[str, Any]] = []
    for g, (code, label) in enumerate(groups):
        for t, period_label in enumerate(periods):
            index = cells.get((t, g), np.array([], dtype=int))
            point = _point(
                measure, values[index], None if weights is None else weights[index], confidence
            )
            base = int(len(index))
            records.append(
                {
                    "position": t,
                    "period": period_label,
                    "group": code,
                    "group_label": label,
                    **point,
                    "base": base,
                    # A count is its own base: only a percent or a mean
                    # moves by chance on a few respondents.
                    "low": measure != "count" and base < min_base,
                }
            )
    points = pd.DataFrame(
        records,
        columns=[
            "position",
            "period",
            "group",
            "group_label",
            "value",
            "lower",
            "upper",
            "base",
            "weighted_base",
            "effective_base",
            "low",
        ],
    )

    by_label = _get_label(data, by) if by else None
    table = _table(points, measure, by_label, weights is not None, min_base, confidence)

    stats["Time"] = time_note
    if measure != "count":
        method = (
            "Wilson score interval, as the Bar chart draws a share's"
            if measure == "percent"
            else "t interval of the mean"
        )
        stats["Interval"] = f"{confidence:.0%} {method}" + (
            ", on Kish's effective base" if weights is not None else ""
        )
    if weights is not None:
        stats["Weight"] = data.weight
    low = points[points["low"]]
    if not low.empty:
        stats["Low base"] = (
            f"{len(low)} of {len(points)} points have fewer than {min_base} respondents "
            "(drawn hollow)"
        )
    note = missing_codes_note(left_out, data.variables)
    if note:
        stats["Missing codes left out"] = note
    dropped = _left_out(data, time, by, frame, has_time, dates, not_dates)
    if dropped:
        stats["Left out"] = dropped

    return TrendPoints(
        table=table,
        points=points,
        periods=periods,
        groups=groups,
        stats=stats,
        measure=measure,
        title=title,
        ylabel=ylabel,
        xlabel=_get_label(data, time) + (f" ({period})" if dates else ""),
        group_title=by_label,
        weight=data.weight if weights is not None else None,
        min_base=min_base,
        confidence=confidence,
        scale_codes=scale_codes,
    )


# ─── the parts ───────────────────────────────────────────────────────────────


def _weights_of(data: SurveyData, frame: pd.DataFrame) -> np.ndarray | None:
    """The weight of every row (a missing weight counts 0), or None unweighted."""
    if data.weight is None:
        return None
    if data.weight not in frame.columns:
        raise ValueError(f"Weight column '{data.weight}' not found in frame.")
    weights = pd.to_numeric(frame[data.weight], errors="coerce").fillna(0.0).to_numpy(dtype=float)
    if np.any(weights < 0):
        raise ValueError(f"The weight column '{data.weight}' has negative values.")
    return weights


def _codes_list(codes: Any) -> list[Any]:
    if codes is None or codes == "" or codes == []:
        return []
    return list(codes) if isinstance(codes, list | tuple) else [codes]


def _code_text(code: Any) -> str:
    """A code as the codebook writes it: 1, not the 1.0 a column with a blank holds."""
    if isinstance(code, float) and code.is_integer():
        return str(int(code))
    return str(code)


def _sort_key(code: Any) -> tuple[int, float, str]:
    """Numbers by value, then text by text: waves are ordered by code."""
    if isinstance(code, bool):
        return (0, float(code), "")
    if isinstance(code, int | float | np.integer | np.floating):
        return (0, float(code), "")
    try:
        return (0, float(str(code)), "")
    except ValueError:
        return (1, 0.0, str(code))


def _ordered_values(data: SurveyData, series: pd.Series, name: str) -> list[Any]:
    """A grouping variable's values: the codebook's answers in its order, then
    the values it does not label, by code. Missing codes are out already."""
    present = series.dropna().unique().tolist()
    variable = data.variables.get(name) if data.variables is not None else None
    missing = (
        {_code_text(code) for code in variable.missing_values} if variable is not None else set()
    )
    seen = {_code_text(value) for value in present}
    declared = [
        code
        for code in _get_value_labels(data, name)
        if _code_text(code) in seen and _code_text(code) not in missing
    ]
    known = {_code_text(code) for code in declared}
    extra = sorted((value for value in present if _code_text(value) not in known), key=_sort_key)
    return declared + extra


def _answer_codes(data: SurveyData, series: pd.Series, name: str, wanted: list[Any]) -> list[Any]:
    """The codes of ``series`` that ``wanted`` names, as the data holds them: a
    JSON 4 finds 4.0, "4" finds 4. A missing code, or a code that is neither an
    answer of the codebook nor in the data, is refused with the answers there are."""
    from siamang.data import multi

    variable = data.variables.get(name) if data.variables is not None else None
    labels = _get_value_labels(data, name)
    missing = list(variable.missing_values) if variable is not None else []
    present = (
        multi.codes_in(series) if multi.is_multi(series) else series.dropna().unique().tolist()
    )
    known = list(labels) + [
        value for value in present if _code_text(value) not in {_code_text(c) for c in labels}
    ]
    label = _get_label(data, name)
    found: list[Any] = []
    for code in wanted:
        for code_missing in missing:
            if _code_text(code_missing) == _code_text(code):
                text = variable.missing_labels.get(code_missing) if variable is not None else None
                raise ValueError(
                    f"{_code_text(code_missing)}{f' ({text})' if text else ''} is a missing code of "
                    f"{label}, not an answer: missing codes are left out of the base. Name an "
                    "answer."
                )
        match = [value for value in known if value == code or _code_text(value) == _code_text(code)]
        if not match:
            answers = [
                value
                for value in known
                if _code_text(value) not in {_code_text(m) for m in missing}
            ]
            listed = ", ".join(
                f"{_code_text(value)} = {labels[value]}" if value in labels else _code_text(value)
                for value in answers
            )
            raise ValueError(f"{label} has no answer {code!r}; its answers are {listed or 'none'}.")
        # The data's own code, and the codebook's when the data differs in type.
        for value in match:
            if value not in found:
                found.append(value)
        as_held = [value for value in present if _code_text(value) == _code_text(code)]
        for value in as_held:
            if value not in found:
                found.append(value)
    return found


def _joined(texts: list[str]) -> str:
    unique = list(dict.fromkeys(texts))
    if len(unique) <= 1:
        return "".join(unique)
    return ", ".join(unique[:-1]) + " or " + unique[-1]


def _time_axis(
    data: SurveyData, series: pd.Series, name: str, period: str
) -> tuple[np.ndarray, list[str], str, bool, int]:
    """Each row's position on the time axis (-1: none), the axis labels, what
    the stats say about time, whether it holds dates, and how many values
    were text that is not a date."""

    label = _get_label(data, name)
    parsed, not_dates = _as_dates(data, series, name)
    if parsed is None:
        waves = _ordered_waves(data, series, name)
        if len(waves) > MAX_POINTS:
            raise ValueError(
                f"{label} has {len(waves):,} different values: not wave codes. Time is a wave "
                "code or a date; for dates, the column must hold dates (ISO 8601 text such as "
                "2026-05-25 is read as one)."
            )
        position = {_code_text(code): index for index, code in enumerate(waves)}
        keys = np.array(
            [position.get(_code_text(value), -1) if pd.notna(value) else -1 for value in series],
            dtype=int,
        )
        labels = _get_value_labels(data, name)
        axis = [str(labels.get(code, _code_text(code))) for code in waves]
        named = f"{label} ({name})" if label != name else name
        return keys, axis, f"{named}: one point per code, ordered by code", False, 0

    frequency = _FREQUENCIES[period]
    stamps = parsed.dropna()
    if stamps.empty:
        raise ValueError(f"{label} holds no dates to draw a trend over.")
    periods = stamps.dt.to_period(frequency)
    axis_periods = pd.period_range(periods.min(), periods.max(), freq=frequency)
    if len(axis_periods) > MAX_POINTS:
        raise ValueError(
            f"{label} spans {len(axis_periods):,} {period}s: too many points for one chart. "
            "Choose a longer Period."
        )
    position = {value: index for index, value in enumerate(axis_periods)}
    keys = np.full(len(series), -1, dtype=int)
    as_period = parsed.dt.to_period(frequency)
    present = as_period.notna().to_numpy()
    keys[present] = [position[value] for value in as_period[present]]
    axis = [_period_label(value, period) for value in axis_periods]
    named = f"{label} ({name})" if label != name else name
    note = f"{named}, by {period}"
    if period == "week":
        note += " — ISO weeks, Monday to Sunday, labelled by ISO year and week number"
    return keys, axis, note, True, not_dates


def _as_dates(data: SurveyData, series: pd.Series, name: str) -> tuple[pd.Series | None, int]:
    """The column as naive UTC timestamps when it holds dates, else None; and
    how many of its values are text that is not a date.

    A column of codes the codebook labels is waves, whatever they look like. A
    ``datetime64`` column is dates, and so is text of which most values read as
    ISO 8601 (the rest are counted and left out); numbers are codes.
    """

    if _get_value_labels(data, name):
        return None, 0
    variable = data.variables.get(name) if data.variables is not None else None
    declared = variable is not None and variable.dtype == "datetime"
    if pd.api.types.is_datetime64_any_dtype(series):
        return _naive(pd.to_datetime(series, utc=True)), 0
    if pd.api.types.is_numeric_dtype(series) or pd.api.types.is_bool_dtype(series):
        return None, 0
    parsed = _parsed(series)
    given = ~_blank(series)
    read = int((parsed.notna() & given).sum())
    if not declared and read * 2 <= int(given.sum()):
        return None, 0
    return _naive(parsed), int(given.sum()) - read


def _parsed(series: pd.Series) -> pd.Series:
    """Text (and date objects) read as ISO 8601 timestamps in UTC; NaT where not."""
    text = series.map(lambda value: value.isoformat() if hasattr(value, "isoformat") else value)
    return pd.to_datetime(text, utc=True, format="ISO8601", errors="coerce")


def _blank(series: pd.Series) -> pd.Series:
    """No value at all: missing, or text of nothing but spaces."""
    return series.isna() | (series.astype(str).str.strip() == "")


def _naive(stamps: pd.Series) -> pd.Series:
    """UTC timestamps without their zone: a period is a calendar period in UTC."""
    return stamps.dt.tz_convert("UTC").dt.tz_localize(None)


def _ordered_waves(data: SurveyData, series: pd.Series, name: str) -> list[Any]:
    """The waves present, by code, and a wave the codebook declares between the
    first and the last of them (a wave with no data yet is a gap, not a jump)."""
    present = sorted(series.dropna().unique().tolist(), key=_sort_key)
    if not present:
        raise ValueError(f"{_get_label(data, name)} holds no values to draw a trend over.")
    variable = data.variables.get(name) if data.variables is not None else None
    missing = (
        {_code_text(code) for code in variable.missing_values} if variable is not None else set()
    )
    first, last = _sort_key(present[0]), _sort_key(present[-1])
    seen = {_code_text(value) for value in present}
    between = [
        code
        for code in _get_value_labels(data, name)
        if _code_text(code) not in seen
        and _code_text(code) not in missing
        and first <= _sort_key(code) <= last
    ]
    return sorted(present + between, key=_sort_key)


def _period_label(value: pd.Period, period: str) -> str:
    start = value.start_time
    if period == "day":
        return start.strftime("%Y-%m-%d")
    if period == "week":
        iso = start.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"
    if period == "month":
        return f"{_MONTHS[start.month - 1]} {start.year}"
    if period == "quarter":
        return f"{start.year} Q{value.quarter}"
    return str(start.year)


def _point(
    measure: str, values: np.ndarray, weights: np.ndarray | None, confidence: float
) -> dict[str, float]:
    """One point: its value, interval and bases (NaN where there is nothing)."""
    nan = float("nan")
    n = len(values)
    point = {
        "value": nan,
        "lower": nan,
        "upper": nan,
        "weighted_base": nan,
        "effective_base": nan,
    }
    if weights is not None:
        total = float(weights.sum())
        squared = float((weights**2).sum())
        effective = total**2 / squared if squared > 0 else 0.0
        point["weighted_base"] = total
        point["effective_base"] = effective
    if measure == "count":
        point["value"] = float(n) if weights is None else point["weighted_base"]
        return point
    if n == 0:
        return point
    if weights is None:
        base = float(n)
        mean = float(values.mean())
    else:
        total = point["weighted_base"]
        base = point["effective_base"]
        if total <= 0:
            return point
        mean = float((values * weights).sum() / total)
    if measure == "percent":
        # Wilson's interval, on Kish's effective base when weighted — the Bar
        # chart's. The normal approximation has no width at 0 % or 100 %
        # (none of 40 read as certain) and runs below 0 near them.
        from siamang.data.intervals import share_interval

        share = share_interval(values > 0.5, weights, confidence=confidence)
        point["value"] = mean * 100
        if share.lower is not None and share.upper is not None:
            point.update(lower=share.lower * 100, upper=share.upper * 100)
        return point
    point["value"] = mean
    if weights is None:
        sd = float(values.std(ddof=1)) if n > 1 else nan
    else:
        kept = int((weights > 0).sum())
        variance = float(np.average((values - mean) ** 2, weights=weights))
        sd = math.sqrt(variance * kept / (kept - 1)) if kept > 1 else nan
    if base > 1 and np.isfinite(sd):
        from scipy import stats as scipy_stats

        margin = float(scipy_stats.t.ppf((1 + confidence) / 2, base - 1)) * sd / math.sqrt(base)
        point.update(lower=mean - margin, upper=mean + margin)
    return point


def _table(
    points: pd.DataFrame,
    measure: str,
    by_label: str | None,
    weighted: bool,
    min_base: int,
    confidence: float,
) -> pd.DataFrame:
    """The points as a reader's table: period × group, the measure, its
    interval and the bases, a low base noted."""
    digits = 1 if measure == "percent" else 2
    name = {"percent": "Percent", "mean": "Mean", "count": "Count"}[measure]
    level = f"{confidence * 100:g}%"
    columns: dict[str, Any] = {"Period": points["period"]}
    if by_label is not None:
        columns[by_label if by_label != "Period" else "Group"] = points["group_label"]
    if measure == "count":
        columns[name] = (
            points["value"].round(1) if weighted else points["value"].round().astype("Int64")
        )
    else:
        columns[name] = points["value"].round(digits)
        columns[f"Lower {level}"] = points["lower"].round(digits)
        columns[f"Upper {level}"] = points["upper"].round(digits)
    columns["Base"] = points["base"].astype(int)
    if weighted:
        columns["Weighted base"] = points["weighted_base"].round(1)
        if measure != "count":
            columns["Effective base"] = points["effective_base"].round(1)

    def note(base: int, low: bool, total: float) -> str:
        if base == 0:
            return "no respondents"
        parts = [f"base below {min_base}"] if low else []
        if weighted and not total > 0:
            # Respondents whose weights are all 0 give no weighted point.
            parts.append("their weights sum to 0")
        return "; ".join(parts)

    if measure != "count":  # a count of 0 is a point, not a gap
        columns["Note"] = [
            note(base, low, total)
            for base, low, total in zip(
                points["base"], points["low"], points["weighted_base"], strict=True
            )
        ]
    return pd.DataFrame(columns)


def _left_out(
    data: SurveyData,
    time: str,
    by: str | None,
    frame: pd.DataFrame,
    has_time: np.ndarray,
    dates: bool,
    not_dates: int,
) -> str | None:
    """Rows no point counts, beyond the missing codes (said apart): no time,
    a time that is not a date, no group."""
    parts = []
    label = _get_label(data, time)
    blank = int(_blank(frame[time]).sum())
    if blank:
        parts.append(f"{blank} without {label}")
    if dates and not_dates:
        text = frame[time]
        bad = text[~_blank(text) & _parsed(text).isna()]
        example = f" (for example {bad.iloc[0]!r})" if not bad.empty else ""
        parts.append(f"{not_dates} whose {label} is not a date{example}")
    if by:
        ungrouped = int((_blank(frame[by]).to_numpy() & has_time).sum())
        if ungrouped:
            parts.append(f"{ungrouped} without {_get_label(data, by)}")
    return "; ".join(parts) or None


# ─── the chart ───────────────────────────────────────────────────────────────


@dataclass
class TrendChart(SurveyChart):
    """A measure over waves or dates, one line per group (:func:`trend`).

    ``table`` is the same points as a table — period × group with the measure,
    its interval and the bases — for a report or the Live screen. A percent or
    a mean of fewer than ``min_base`` respondents is drawn hollow, and the band
    is the ``confidence`` interval of each point (``band=False`` leaves it out;
    past ``MAX_BANDS`` lines the table gives the intervals instead).

    The chart is drawn as the newer charts are (:mod:`siamang.reporting.chart_parts`):
    a colour per line however many there are, whole percents or thousands
    separated on the value axis, the period labels level or slanted as they fit
    the plot, the title, axis titles and legend wrapped (the legend under the
    plot on a narrow figure or when it is taller than the plot), and the base,
    the weight and what was left out written under it — the figure growing
    taller rather than squeezing the plot.
    """

    time: str = ""
    period: str = "month"
    measure: str = "percent"
    variable: str | None = None
    codes: Any = None
    by: str | None = None
    band: bool = True
    min_base: int = 30
    confidence: float = 0.95

    _points: TrendPoints | None = field(init=False, repr=False, default=None)

    @property
    def points(self) -> TrendPoints:
        """The points, computed once."""
        if self._points is None:
            self._points = trend(
                self.data,
                self.time,
                period=self.period,
                measure=self.measure,
                variable=self.variable,
                codes=self.codes,
                by=self.by,
                min_base=self.min_base,
                confidence=self.confidence,
            )
        return self._points

    @property
    def table(self) -> ResultTable:
        """The points as a table, with what they are in its statistics."""
        from siamang.reporting.result_table import ResultTable

        points = self.points
        return ResultTable(data=self.data, frame=points.table, footer=points.stats)

    @property
    def stats(self) -> dict[str, Any]:
        return dict(self.points.stats)

    def _build(self) -> None:
        _require_matplotlib()
        import matplotlib.pyplot as plt

        from siamang.reporting import chart_theme

        points = self.points
        chart_theme.set_theme(style="whitegrid", palette=self.palette)
        fig, ax = plt.subplots(figsize=self.figsize)
        self._fig, self._ax = fig, ax
        figure_pt = self.figsize[0] * 72.0

        count = len(points.groups)
        # One colour per line, none repeated however many lines there are.
        colours = series_colours(self.palette, max(count, 1))
        positions = np.arange(len(points.periods))
        # Many periods (a year by day) are a line; its markers shrink with them.
        dense = len(positions) > 40
        size = 34 if not dense else max(6.0, 34 * 40 / len(positions))
        # The bands of many lines hide one another and the lines: past a few
        # lines the table gives each point's interval instead.
        banded = self.band and points.measure != "count" and count <= MAX_BANDS
        drawn_band = False
        for index, (code, label) in enumerate(points.groups):
            rows = points.points[
                points.points["group"].map(_code_text) == _code_text(code)
                if code is not None
                else points.points["group"].isna()
            ].sort_values("position")
            value = rows["value"].to_numpy(dtype=float)
            color = colours[index]
            shape = MARKERS[index % len(MARKERS)] if count > MAX_BANDS else "o"
            ax.plot(
                positions,
                value,
                color=color,
                linewidth=1.4 if dense else 2,
                label=label or None,
                zorder=2,
                # The shape is shown in the legend only: the points draw it.
                **(
                    {"marker": shape, "markevery": [], "markersize": 6} if count > MAX_BANDS else {}
                ),
            )
            shown = np.isfinite(value)
            low = rows["low"].to_numpy(dtype=bool)
            full, thin = shown & ~low, shown & low
            # A point at 0 % or 100 % sits on the frame: drawn whole.
            ax.scatter(
                positions[full],
                value[full],
                color=color,
                s=size,
                marker=shape,
                zorder=3,
                clip_on=False,
            )
            ax.scatter(
                positions[thin],
                value[thin],
                facecolors="white",
                edgecolors=[color],
                linewidths=1.0 if dense else 1.6,
                s=size,
                marker=shape,
                zorder=3,
                clip_on=False,
            )
            if banded:
                # A hollow point's interval is too wide to draw — a mean of two
                # respondents' t interval spans -46 to 56 on a 0-10 scale and
                # flattens every line — so the band stops at the points that
                # have their base; the table gives the hollow ones'.
                lower = np.where(low, np.nan, rows["lower"].to_numpy(dtype=float))
                upper = np.where(low, np.nan, rows["upper"].to_numpy(dtype=float))
                if np.isfinite(lower).any():
                    # Several bands overlap: each is lighter, so the lines stay the story.
                    alpha = 0.18 if count == 1 else 0.08
                    ax.fill_between(
                        positions, lower, upper, color=color, alpha=alpha, linewidth=0, zorder=1
                    )
                    drawn_band = True

        ax.grid(False)
        ax.grid(True, color=chart_theme.grid("0.9"), linewidth=0.8)
        ax.set_axisbelow(True)
        ax.set_xticks(positions)
        ax.set_xlim(-0.5, len(positions) - 0.5)
        self._value_axis(ax, points, banded)

        ylabel = {"percent": "% of respondents", "mean": "Mean", "count": "Respondents"}[
            points.measure
        ]
        if points.weight is not None:
            ylabel += " (weighted)"
            self._weighted()
        title = self._auto_title(*(part for part in (points.title, points.group_title) if part))

        below = None
        if points.group_title is not None:
            handles, names = ax.get_legend_handles_labels()
            if figure_pt >= 7.5 * 72.0:  # beside the plot, else under it
                ax.legend(
                    handles,
                    [wrap(name, 24) for name in names],
                    title=wrap(points.group_title, 24),
                    loc="upper left",
                    bbox_to_anchor=(1.01, 1.0),
                    frameon=False,
                    fontsize=10,
                    title_fontsize=10,
                )
            else:
                below = legend_below(fig, handles, names, points.group_title, figure_pt)

        footnote = Footnote(
            fig, _notes(points, count, drawn_band, self.band), legend=below, axes=ax
        )
        _fit_titles(ax, title, points.xlabel, ylabel)
        _fit_ticks(fig, ax, points.periods)
        footnote.apply()
        side = ax.get_legend()
        if side is not None:
            renderer = fig.canvas.get_renderer()
            if side.get_window_extent(renderer).height > ax.get_window_extent(renderer).height + 1:
                # Taller than the plot, it would run over the notes: under the plot.
                handles, names = ax.get_legend_handles_labels()
                side.remove()
                footnote.legend = legend_below(fig, handles, names, points.group_title, figure_pt)
                footnote.apply()
        for _ in range(2):  # fitted to the plot as it is laid out
            _fit_ticks(fig, ax, points.periods)
            _fit_titles(ax, title, points.xlabel, ylabel)
            footnote.apply()

    def _value_axis(self, ax: Any, points: TrendPoints, banded: bool) -> None:
        """The value axis: whole percents from 0, a count from 0 with its
        thousands separated, a mean on its scale's codes when it keeps to them,
        else on its points and bands. Fitted to what is drawn: the points, and
        the bands of the points that have their base."""
        from matplotlib.ticker import MaxNLocator

        frame = points.points
        solid = ~frame["low"].to_numpy(dtype=bool)
        parts = [frame["value"].to_numpy(float)]
        if banded:
            parts += [frame.loc[solid, column].to_numpy(float) for column in ("lower", "upper")]
        values = np.concatenate(parts)
        finite = values[np.isfinite(values)]
        if points.measure == "percent":
            top = 100.0 if not finite.size else min(100.0, max(10.0, finite.max() * 1.12))
            ax.set_ylim(0, top)
            percent_axis(ax.yaxis)
            return
        thousands_axis(ax.yaxis)
        if points.measure == "count":
            ax.set_ylim(bottom=0)
            if points.weight is None:
                # As many ticks as the axis holds, on whole respondents.
                ax.yaxis.set_major_locator(MaxNLocator(nbins="auto", integer=True))
            return
        if not finite.size:
            return
        if points.scale_codes:
            low_code, high_code = points.scale_codes[0], points.scale_codes[-1]
            if finite.min() >= low_code and finite.max() <= high_code:
                pad = (high_code - low_code) * 0.04
                ax.set_ylim(low_code - pad, high_code + pad)
                return
        low, high = float(finite.min()), float(finite.max())
        pad = (high - low) * 0.08 or max(abs(high) * 0.1, 1.0)
        ax.set_ylim(low - pad, high + pad)


def _notes(points: TrendPoints, count: int, drawn_band: bool, band: bool) -> list[str]:
    """What the chart says under itself: the base, the hollow points, the
    band, the weight and what was left out — as a table says under itself."""

    frame = points.points
    respondents = int(frame["base"].sum())
    whom = "respondents" if points.measure == "count" else "respondents who answered"
    base = f"Base: {respondents:,} {'respondent' if respondents == 1 else whom}"
    if points.weight is not None:
        base += f" (weighted: {float(np.nansum(frame['weighted_base'])):,.1f})"
    sizes = frame.loc[frame["base"] > 0, "base"]
    if points.measure != "count" and len(sizes) > 1:
        low, high = int(sizes.min()), int(sizes.max())
        base += f"; {low:,} per point" if low == high else f"; {low:,} to {high:,} per point"
    notes = [base + "."]
    empty = int((frame["base"] == 0).sum()) if points.measure != "count" else 0
    if empty:
        notes.append(f"Gaps: no respondents in {empty} of {len(frame)} points.")
    if points.weight is not None and points.measure != "count":
        weightless = int(((frame["base"] > 0) & ~(frame["weighted_base"] > 0)).sum())
        if weightless:
            notes.append(
                f"Not drawn: {weightless} {'point' if weightless == 1 else 'points'} whose "
                "respondents' weights sum to 0."
            )
    drawn = frame["low"] & frame["value"].notna()
    if drawn.any():
        hollow = f"Hollow points: fewer than {points.min_base} respondents"
        if band and points.measure != "count" and count <= MAX_BANDS:
            hollow += ", drawn without a band (the table gives their intervals)"
        notes.append(hollow + ".")
    level = f"{points.confidence:.0%}"
    if drawn_band:
        notes.append(
            f"Band: {level} confidence interval."
            if count == 1
            else f"Bands: {level} confidence intervals."
        )
    elif band and points.measure != "count" and count > MAX_BANDS:
        notes.append(
            f"No bands: the {level} intervals of {count} lines would hide one another; the "
            "table gives each point's."
        )
    if points.weight is not None:
        notes.append(f"Weighted by '{points.weight}'; the bases count respondents.")
    if points.stats.get("Missing codes left out"):
        notes.append(f"Left out as missing: {points.stats['Missing codes left out']}.")
    if points.stats.get("Left out"):
        notes.append(f"Left out: {points.stats['Left out']}.")
    return notes


def _fit_titles(ax: Any, title: str, xlabel: str, ylabel: str) -> None:
    """The title and the axis titles wrapped to the plot as it is laid out: a
    question's label is longer than a plot is wide."""

    width, height = axes_points(ax)
    size = font_size("axes.labelsize")
    ax.set_xlabel(wrap(xlabel, chars_in(width, size)))
    ax.set_ylabel(wrap(ylabel, chars_in(height, size)))
    # Centred over the plot, the title may reach as far to either side of its
    # centre as the figure goes on the nearer one.
    box = ax.get_position()
    centre = (box.x0 + box.x1) / 2.0
    room = 2.0 * min(centre, 1.0 - centre) * ax.figure.get_figwidth() * 72.0 - 8.0
    ax.set_title(wrap(title, chars_in(max(room, width), font_size("axes.titlesize"))))


#: A period label under the axis is at most this many lines, level; longer
#: ones are slanted.
LEVEL_LINES = 4
#: A slanted period label is at most this many characters a line.
SLANTED_WIDTH = 40
#: The angle of a slanted period label, in degrees.
SLANT = 40


def _fit_ticks(fig: Any, ax: Any, periods: list[str]) -> None:
    """The period labels as they fit the axis drawn: level, each on as few
    lines as the room between two ticks allows (measured, not guessed), when
    every word fits it; slanted otherwise, in as many lines as fit between two
    slanted neighbours — every label while they fit, else every second,
    third … label."""

    from matplotlib.font_manager import FontProperties

    count = len(periods)
    if count == 0:
        return
    size = font_size("xtick.labelsize")
    renderer = fig.canvas.get_renderer()
    font = FontProperties(size=size)

    def widest(text: str) -> float:
        """The widest line of ``text`` as drawn, in points."""
        return max(
            renderer.get_text_width_height_descent(line, font, ismath=False)[0]
            for line in text.split("\n")
        ) * (72.0 / fig.dpi)

    slot = axes_points(ax)[0] / count
    room = slot - 6.0  # a gap between neighbours
    ax.set_xticks(np.arange(count))
    words = [word for label in periods for word in label.split()] or [""]
    if max(widest(word) for word in dict.fromkeys(words)) <= room:
        longest = max(len(label) for label in periods)
        shortest = max(len(word) for word in words)
        for width in range(longest, shortest - 1, -1):
            level = [wrap(label, width) for label in periods]
            if any(label.count("\n") >= LEVEL_LINES for label in level):
                break  # narrower only adds lines
            if all(widest(label) <= room for label in level):
                ax.set_xticklabels(level, rotation=0, ha="center")
                return
    # Slanted, two labels ``step`` periods apart are step · slot · sin(angle)
    # apart across their lines: that many lines fit, each of at most
    # SLANTED_WIDTH characters.
    across = math.sin(math.radians(SLANT))
    step, slanted = count, [wrap(label, SLANTED_WIDTH) for label in periods]
    for tried in range(1, count + 1):
        lines = int(tried * slot * across / (size * 1.25))
        fitted = _slanted(periods, lines) if lines >= 1 else None
        if fitted is not None:
            step, slanted = tried, fitted
            break
    # Only the labelled periods keep a tick (and a grid line): a line per day
    # of a year is a grey wash, not a grid.
    shown = list(range(0, count, step))
    ax.set_xticks(shown)
    ax.set_xticklabels(
        [slanted[index] for index in shown], rotation=SLANT, ha="right", rotation_mode="anchor"
    )


def _slanted(periods: list[str], lines: int) -> list[str] | None:
    """The labels wrapped as narrowly (from 16 characters) as keeps each
    within ``lines`` lines, or None when even SLANTED_WIDTH does not."""

    for width in range(16, SLANTED_WIDTH + 1):
        wrapped = [wrap(label, width) for label in periods]
        if all(label.count("\n") < lines for label in wrapped):
            return wrapped
    return None
