"""The bar chart's newer forms: percentages, a split into groups, an order by size.

:class:`~siamang.reporting.charts.BarChart` draws what it has always drawn while
``show``, ``split`` and ``sort`` are left at their defaults — a stored flow
renders the same picture — and hands everything else to :func:`draw`:

- ``show="percent"``: each bar is a share of the respondents who answered. For
  a multiple-choice question that is the share who named the option, so the
  bars add up to more than 100 % and the chart says so, as the Frequencies
  table does.
- ``split``: the chart of a crosstab — the answers within each group of a
  second variable, drawn ``grouped`` side by side, ``stacked``, or
  ``stacked_100`` with every group's bar at 100 %. Percentages are of each
  group, as a Crosstab's column percentages are, and sums of weights when the
  data is weighted.
- ``sort="value"``: the largest bar first; ``"code"`` keeps the codebook's order.
- ``top``: only the N answers given most (overall, with a split), the rest
  left out or — ``other=True`` — combined as Other: for a multiple-choice
  question, the respondents who named any of the rest.
- ``intervals``: an error bar on each percentage — Wilson's interval
  (:func:`siamang.data.intervals.share_interval`, on Kish's effective base
  when weighted) — and on each mean by group, the interval the Group means
  chart draws (:func:`~siamang.data.intervals.mean_interval`). Only on bars
  side by side: on a stack an interval has no end of its own to sit on.
- ``letters``: with a split, grouped, in percent: above each bar the letters
  of the groups whose share of that answer it is significantly higher than —
  the Banner table's two-sided z-test of column proportions
  (:func:`siamang.reporting.tables.proportion_letters`), on the base of the
  group's respondents who answered (Kish's effective base weighted), groups
  lettered A, B, … over the split variable's groups in the Banner table's
  order: the comparisons the Tab book prints for the same cells, under the
  letters its banner gives these columns (the same letters only when the
  split variable is the banner's first).
- ``layout="histogram"``: an interval or ratio variable in ``bins`` — Freedman
  and Diaconis's width (``"auto"``), a number of bins, or their edges — as
  counts or percent, weighted; with a split, one panel per group.
- ``layout="donut"``: one variable's answers as the parts of a whole, the
  slices smaller than ``min_slice`` percent combined as Other and the base in
  the middle.

Everything this module draws says under the plot what a table says under
itself: the base, the weight, and the codebook's missing codes, which it leaves
out of the bars — a 99 "Don't know" is not an answer — and counts. A
multiple-choice question, which the older chart could not draw at all, is
drawn here whatever the parameters.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

from siamang.reporting import chart_theme
from siamang.reporting.chart_parts import (
    CHAR_WIDTH,
    FOOTNOTE_SIZE,
    VALUE_SIZE,
    Footnote,
    axes_points,
    chars_in,
    code_order,
    code_text,
    count_text,
    fit_ticks,
    font_size,
    ink_on,
    left_out_note,
    legend_below,
    percent_axis,
    series_colours,
    text_width,
    thousands_axis,
    wrap,
)

if TYPE_CHECKING:
    from siamang.data.survey_data import SurveyData
    from siamang.reporting.charts import BarChart

SHOWS = ("count", "percent")
LAYOUTS = ("grouped", "stacked", "stacked_100", "histogram", "donut")
SORTS = ("code", "value")
CORRECTIONS = ("none", "bonferroni")

#: A group with fewer (effective) respondents than this takes no part in the
#: significance letters: the Banner table's and the Tab book's minimum.
MIN_TESTED = 30
#: The most bins a histogram draws: Freedman and Diaconis's width on a long
#: tail gives hundreds, and a number or edges asked for more are a mistake.
MAX_BINS = 100
#: The most groups a histogram draws, one panel each.
MAX_PANELS = 12
#: The most values of a number (interval or ratio, without value labels)
#: drawn as bars or as the series or groups of a split: past it each value is
#: a bar or a legend entry nobody reads (84 ages made a legend wider than the
#: figure), and a histogram is what draws the distribution.
MAX_VALUES = 30
#: The colour of the answers combined as Other: none of the answers' own.
OTHER_COLOUR = (0.72, 0.72, 0.72)
#: The colour of error bars and of the letters over the bars.
INK = "0.2"
#: The text beside a donut — its base, the percentages of its thin slices —
#: and the lines that join those percentages to their slices.
DONUT_INK = "0.15"
LEADER = "0.55"


# The colours above, or — while a chart of palette "theme" is drawn — the
# report theme's (chart_theme): Other in its neutral grey, as the Likert
# chart's neutral answer and the NPS's passives are; the whiskers, the letters
# and the text beside a donut in its text colour; a leader line in its
# secondary text colour.
def _other() -> Any:
    return chart_theme.neutral(OTHER_COLOUR)


def _ink(default: Any = INK) -> Any:
    return chart_theme.text(default)


@dataclass
class Bars:
    """What a bar chart draws: ``values[position, series]`` and how to read it."""

    values: np.ndarray
    positions: list[str]
    series: list[str]
    kind: str  # count | percent | mean
    value_label: str
    position_label: str
    title: str
    legend_title: str = ""
    stacked: bool = False
    #: Every bar reaches 100 (stacked_100): the value axis is 0–100.
    full: bool = False
    #: The series are the steps of a scale (ordinal and up), not categories.
    ordered: bool = False
    #: Each series' place in code order among all ``palette_size`` answers
    #: drawn from (Top N's left out included): its colour follows the answer,
    #: not the rank a sort or Top N gave it, so an answer has one colour in
    #: every chart of a report.
    colour_index: list[int] = field(default_factory=list)
    palette_size: int = 0
    notes: list[str] = field(default_factory=list)
    #: The value axis's title when ``value_label`` would not fit on one line
    #: along it (a split by a question: its notes name the variable).
    short_value_label: str = ""
    #: Each bar's confidence interval, shaped as ``values`` (NaN where there
    #: is none), or None when no interval is drawn.
    lower: np.ndarray | None = None
    upper: np.ndarray | None = None
    #: The significance letters above each bar, ``marks[position][series]``.
    marks: list[list[str]] | None = None
    #: The bar (one series) or the series that combines the answers as Other,
    #: drawn grey.
    other_position: int | None = None
    other_series: int | None = None


def is_classic(chart: BarChart) -> bool:
    """Whether ``chart`` is the one BarChart has always drawn: the newer
    parameters at their defaults, and no multiple-choice column (which that
    chart could not draw — it raised ``unhashable type: 'list'``)."""

    from siamang.data import multi

    if chart.show != "count" or chart.split is not None or chart.sort != "code":
        return False
    if chart.layout not in LAYOUTS[:3] or chart.top is not None:
        return False  # a histogram, a donut — or a layout it would refuse
    if chart.other or chart.intervals or chart.letters:
        return False
    frame = chart.data.frame
    for name in (chart.column, chart.by):
        if name is not None and name in frame.columns and multi.is_multi(frame[name]):
            return False
    return True


def draw(chart: BarChart) -> None:
    """Build ``chart`` in its newer form (see the module's docstring)."""

    from siamang.data.inference import without_missing_codes

    _check(chart)
    data = chart.data
    names = [chart.column, *(name for name in (chart.split, chart.by) if name)]
    frame, left_out = without_missing_codes(data.frame, names, data.variables)
    frame = frame.reset_index(drop=True)
    _few_values(chart, frame)
    weights = _weights(data)
    figure: Bars | Histogram | Donut
    if chart.layout == "histogram":
        figure = _histogram(chart, frame, weights)
    elif chart.layout == "donut":
        figure = _donut(chart, frame, weights)
    elif chart.by:
        figure = _means(chart, frame, weights)
    elif chart.split:
        figure = _split(chart, frame, weights)
    else:
        figure = _distribution(chart, frame, weights)
    if weights is not None:
        chart._weighted()
        figure.notes.append(f"Weighted by '{data.weight}'; n counts respondents.")
    note = left_out_note(left_out, data.variables)
    if note:
        figure.notes.append(note)
    if isinstance(figure, Histogram):
        render_histogram(chart, figure)
    elif isinstance(figure, Donut):
        render_donut(chart, figure)
    else:
        render(chart, figure)


# ─── what the bars are ───────────────────────────────────────────────────────


def _check(chart: BarChart) -> None:
    if chart.show not in SHOWS:
        raise ValueError(f"show must be one of {', '.join(SHOWS)}; got {chart.show!r}.")
    if chart.layout not in LAYOUTS:
        raise ValueError(f"layout must be one of {', '.join(LAYOUTS)}; got {chart.layout!r}.")
    if chart.sort not in SORTS:
        raise ValueError(f"sort must be one of {', '.join(SORTS)}; got {chart.sort!r}.")
    if chart.by and chart.split:
        raise ValueError(
            "by draws the mean of the variable in each group and split its answers in "
            "each group — give one of them."
        )
    if chart.by and chart.show == "percent":
        raise ValueError(
            "A mean in each group is not a percentage: to show the answers in each "
            "group as percentages, use split= instead of by=."
        )
    for name in (chart.column, chart.by, chart.split):
        if name and name not in chart.data.frame.columns:
            raise ValueError(f"No variable {name!r} in the data.")
    if chart.correction not in CORRECTIONS:
        raise ValueError(
            f"correction must be one of {', '.join(CORRECTIONS)}; got {chart.correction!r}."
        )
    for name, value in (("confidence", chart.confidence), ("level", chart.level)):
        if isinstance(value, bool) or not isinstance(value, int | float) or not 0 < value < 1:
            raise ValueError(f"{name} must be between 0 and 1; got {value!r}.")
    if (
        isinstance(chart.min_slice, bool)
        or not isinstance(chart.min_slice, int | float)
        or not 0 <= chart.min_slice < 100
    ):
        raise ValueError(f"min_slice must be a percentage from 0 to 100; got {chart.min_slice!r}.")
    if chart.top is not None:
        if isinstance(chart.top, bool) or not isinstance(chart.top, int | np.integer):
            raise ValueError(f"top must be a whole number of answers; got {chart.top!r}.")
        if chart.top < 1:
            raise ValueError(f"top must be 1 or more; got {chart.top!r}.")
        if chart.by:
            raise ValueError(
                "top keeps the answers given most, and with by the bars are means of "
                "groups — give one of them."
            )
    if chart.other and chart.top is None:
        raise ValueError("other combines the answers after the top N: give top= as well.")
    side_by_side = "on bars side by side (layout='grouped')"
    if chart.layout == "histogram":
        if chart.by:
            raise ValueError(
                "A histogram draws the distribution of the variable, and by its mean in "
                "each group: give split= for a histogram of each group."
            )
        if chart.top is not None:
            raise ValueError(
                "top keeps the answers given most; a histogram draws bins of a number."
            )
        if chart.intervals or chart.letters:
            raise ValueError(
                "Confidence intervals and significance letters are drawn "
                f"{side_by_side}, not on a histogram."
            )
        parse_bins(chart.bins)
    if chart.layout == "donut":
        if chart.split:
            raise ValueError(
                "A donut shows one variable's answers as the parts of a whole: split "
                "cannot be drawn in it — layout='stacked_100' shows the answers within "
                "each group."
            )
        if chart.by:
            raise ValueError(
                "A donut shows the shares of the answers, and by draws means — give one of them."
            )
        if chart.intervals or chart.letters:
            raise ValueError(
                "Confidence intervals and significance letters are drawn "
                f"{side_by_side}, not on a donut."
            )
    if chart.intervals and chart.split and chart.layout != "grouped":
        raise ValueError(
            f"Confidence intervals are drawn {side_by_side}: a stacked bar has no end of "
            "its own for each answer."
        )
    if chart.letters:
        if not chart.split:
            raise ValueError("Significance letters compare the groups of split: give split=.")
        if chart.layout != "grouped":
            raise ValueError(f"Significance letters are drawn {side_by_side}, not on stacks.")
        if chart.show != "percent":
            raise ValueError(
                "Significance letters compare percentages, as the Banner table's do: "
                "give show='percent'."
            )


def _few_values(chart: BarChart, frame: pd.DataFrame) -> None:
    """Refuse a number (interval or ratio, no value labels) with more than
    :data:`MAX_VALUES` values drawn a bar, a slice, a series or a group per
    value — the answer the histogram gives, or Bands does for a group. With
    ``top`` only the N values given most are drawn, so N is what counts."""

    data = chart.data
    # A histogram draws the number's distribution, and By its mean per group.
    roles = [] if chart.layout == "histogram" or chart.by else [(chart.column, None)]
    roles += [(name, role) for name, role in ((chart.split, "Split by"), (chart.by, "By")) if name]
    for name, role in roles:
        variable = _variable(data, name)
        if variable is None or variable.scale not in ("interval", "ratio"):
            continue
        if _answer_labels(data, name):
            continue
        count = len(pd.unique(frame[name].dropna()))
        top = chart.top if role is None else None
        if min(count, top or count) <= MAX_VALUES:
            continue
        label = _label(data, name)
        if role is None:
            what = "a slice" if chart.layout == "donut" else "a bar"
            if top is not None:
                raise ValueError(
                    f"{label} is a number with {count:,} different values given, and top={top} "
                    f"draws {what} for each of the {top} given most: give top={MAX_VALUES} or "
                    "fewer, or layout='histogram' draws its distribution (or band it first with "
                    "Bands)."
                )
            raise ValueError(
                f"{label} is a number with {count:,} different values given, and this chart "
                f"draws {what} for each: layout='histogram' draws its distribution (or band "
                "it first with Bands)."
            )
        raise ValueError(
            f"{role} {label} is a number with {count:,} different values given, a group for "
            "each: band it first (Bands) to compare its ranges."
        )


def _palette_places(drawn: list[int], answers: int, ordered: bool) -> dict[str, Any]:
    """``colour_index`` and ``palette_size`` of answers ``drawn`` (their places
    in code order among all ``answers`` given): an answer's colour is its place
    among all of them, so that it keeps its colour whatever Top N or a donut's
    Other leaves out. A number of more than :data:`MAX_VALUES` values, drawn
    with Top N, is the exception: its steps light to dark would be too close
    to tell apart (five ages among 74 read as one blue), so the answers drawn
    take the steps among themselves, in code order."""

    if not ordered or answers <= MAX_VALUES:
        return {"colour_index": list(drawn), "palette_size": answers}
    place = {index: step for step, index in enumerate(sorted(set(drawn)))}
    return {"colour_index": [place[index] for index in drawn], "palette_size": len(place)}


def _weights(data: SurveyData) -> np.ndarray | None:
    """The weight of each row, by position; missing or not a number counts 0."""

    if data.weight is None:
        return None
    if data.weight not in data.frame.columns:
        raise ValueError(f"Weight column '{data.weight}' not found in frame.")
    column = pd.to_numeric(data.frame[data.weight], errors="coerce")
    return column.fillna(0.0).to_numpy(dtype=float)


def _variable(data: SurveyData, name: str) -> Any:
    return data.variables[name] if data.variables and name in data.variables else None


def _label(data: SurveyData, name: str) -> str:
    variable = _variable(data, name)
    return (variable.label if variable is not None else None) or name


def _answer_labels(data: SurveyData, name: str) -> dict[Any, str]:
    """The codebook's labelled answers of ``name``, its missing codes left out."""

    variable = _variable(data, name)
    if variable is None:
        return {}
    missing = set(variable.missing_values)
    return {code: label for code, label in (variable.labels or {}).items() if code not in missing}


def _is_scale(data: SurveyData, name: str) -> bool:
    variable = _variable(data, name)
    return variable is not None and variable.scale in ("ordinal", "interval", "ratio")


def _single_codes(data: SurveyData, name: str, answers: pd.Series) -> list[Any]:
    """The answers a bar is drawn for: those given, and on a scale (ordinal and
    up) every labelled step too — an answer nobody gave is a finding there."""

    codes: list[Any] = []
    labelled = list(_answer_labels(data, name)) if _is_scale(data, name) else []
    for code in [*labelled, *pd.unique(answers)]:
        if not any(code == known for known in codes):
            codes.append(code)
    return sorted(codes, key=code_order)


def _multi_codes(data: SurveyData, name: str, series: pd.Series) -> list[Any]:
    """A multiple-choice question's options: the labelled ones, as the
    Frequencies table lists them, else those named."""

    from siamang.data import multi

    labelled = list(_answer_labels(data, name))
    return labelled or multi.codes_in(series)


def _name_of(data: SurveyData, name: str, code: Any) -> str:
    labels = _variable(data, name).labels if _variable(data, name) is not None else {}
    return str((labels or {}).get(code, code_text(code)))


def _chose(series: pd.Series, code: Any, is_multi: bool) -> np.ndarray:
    from siamang.data import multi

    hits = multi.reach(series, code) if is_multi else series == code
    return hits.fillna(False).to_numpy(dtype=bool)


def _answered(series: pd.Series, is_multi: bool) -> np.ndarray:
    from siamang.data import multi

    return (multi.responded(series) if is_multi else series.notna()).to_numpy(dtype=bool)


def _base(n: int, weighted: float | None, whom: str) -> str:
    text = f"Base: {n:,} {'respondent' if n == 1 else 'respondents'} {whom}"
    return text + (f" (weighted: {weighted:,.1f})." if weighted is not None else ".")


def _order(values: np.ndarray, sort: str) -> list[int]:
    """Positions in code order, or largest first (ties keep their code order)."""

    indices = list(range(len(values)))
    if sort == "value":
        indices.sort(key=lambda i: -values[i] if values[i] == values[i] else np.inf)
    return indices


def _top(totals: np.ndarray, top: int | None) -> tuple[list[int], list[int]]:
    """The positions of the ``top`` largest ``totals``, in code order, and of
    the rest. Of two answers given as often the first in code order is kept."""

    indices = list(range(len(totals)))
    if top is None or top >= len(indices):
        return indices, []
    ranked = sorted(indices, key=lambda i: (-totals[i] if totals[i] == totals[i] else np.inf, i))
    return sorted(ranked[:top]), sorted(ranked[top:])


def _any_of(hits: list[np.ndarray]) -> np.ndarray:
    """Who chose any of these answers: Other, for a multiple-choice question
    the respondents who named at least one of the rest (not their sum)."""

    return np.logical_or.reduce(hits)


def _other_name(names: list[str]) -> str:
    """``Other`` — or, when an answer drawn is called that already, ``Other (combined)``."""

    return "Other (combined)" if any(n.strip().casefold() == "other" for n in names) else "Other"


def _top_note(
    kept: int, rest: int, other: str | None, is_multi: bool, overall: bool = False
) -> str:
    what, most = ("options", "named most") if is_multi else ("answers", "given most")
    head = f"The {kept} {what} {most}{' overall' if overall else ''} of {kept + rest} are drawn"
    if other is None:
        return f"{head}; the other {rest} are left out."
    if is_multi:
        return f"{head}; {other} is the respondents who named any of the other {rest}."
    return f"{head}; {other} combines the other {rest}."


def _share_bounds(
    hits: list[np.ndarray], base: np.ndarray, weights: np.ndarray | None, confidence: float
) -> tuple[np.ndarray, np.ndarray]:
    """Each share's interval in percent: Wilson's, on Kish's effective base
    when weighted (:func:`siamang.data.intervals.share_interval`)."""

    from siamang.data.intervals import share_interval

    lower, upper = np.full(len(hits), np.nan), np.full(len(hits), np.nan)
    for index, chose in enumerate(hits):
        interval = share_interval(
            chose[base], None if weights is None else weights[base], confidence=confidence
        )
        if interval.defined:
            lower[index], upper[index] = interval.lower * 100.0, interval.upper * 100.0
    return lower, upper


def _level(confidence: float) -> str:
    return f"{confidence * 100:g} %"


def _share_interval_note(chart: BarChart, weighted: bool) -> str:
    return f"Error bars: {_level(chart.confidence)} confidence intervals (Wilson score" + (
        ", on Kish's effective base)." if weighted else ")."
    )


#: Said when intervals are asked of bars that are counts.
_NO_COUNT_INTERVALS = (
    "Confidence intervals are drawn for percentages and for means by group; counts have none."
)


def _distribution(chart: BarChart, frame: pd.DataFrame, weights: np.ndarray | None) -> Bars:
    from siamang.data import multi

    data, name = chart.data, chart.column
    series = frame[name]
    weight = weights if weights is not None else np.ones(len(series))
    label = _label(data, name)
    is_multi = multi.is_multi(series)
    answered = _answered(series, is_multi)
    if not answered.any():
        # Every answer a missing code (or none at all): an empty axis ticked
        # "−0 %" said nothing; the split and the donut say this.
        raise ValueError(f"No respondent answered {label}.")
    codes = (
        _multi_codes(data, name, series)
        if is_multi
        else _single_codes(data, name, series[answered])
    )
    hits = [_chose(series, code, is_multi) & answered for code in codes]
    counts = np.array([weight[chose].sum() for chose in hits], dtype=float)
    base = float(weight[answered].sum())
    percent = chart.show == "percent"

    def scaled(raw: np.ndarray) -> np.ndarray:
        if not percent:
            return raw
        return raw / base * 100.0 if base > 0 else np.zeros(len(raw))

    kept, rest = _top(counts, chart.top)
    order = [kept[i] for i in _order(scaled(counts[kept]), chart.sort)]
    names = [_name_of(data, name, codes[i]) for i in order]
    drawn = [hits[i] for i in order]
    other = _other_name(names) if chart.other and rest else None
    if other is not None:
        drawn.append(_any_of([hits[i] for i in rest]))
        names.append(other)
    values = scaled(np.array([weight[chose].sum() for chose in drawn], dtype=float))
    weighted = weights is not None
    if percent:
        axis = "% of respondents" + (" (weighted)" if weighted else "")
    else:
        axis = "Weighted count" if weighted else "Count"
    notes = [_base(int(answered.sum()), base if weighted else None, "who answered")]
    if is_multi:
        notes.append(
            "Several answers allowed: each bar is the share of respondents who named "
            "the option, so the bars add up to more than 100 %."
            if percent
            else "Several answers allowed: each bar counts the respondents who named the option."
        )
    if rest:
        notes.append(_top_note(len(kept), len(rest), other, is_multi))
    lower = upper = None
    if chart.intervals and percent:
        lower, upper = _share_bounds(drawn, answered, weights, chart.confidence)
        notes.append(_share_interval_note(chart, weighted))
    elif chart.intervals:
        notes.append(_NO_COUNT_INTERVALS)
    return Bars(
        values=values.reshape(-1, 1),
        positions=names,
        series=[label],
        kind="percent" if percent else "count",
        value_label=axis,
        position_label="",  # the title names the variable
        title=chart.title or label,
        notes=notes,
        lower=None if lower is None else lower.reshape(-1, 1),
        upper=None if upper is None else upper.reshape(-1, 1),
        other_position=len(names) - 1 if other is not None else None,
    )


def _split(chart: BarChart, frame: pd.DataFrame, weights: np.ndarray | None) -> Bars:
    from siamang.data import multi

    data, name, by = chart.data, chart.column, str(chart.split)
    label, by_label = _label(data, name), _label(data, by)
    if by == name:
        raise ValueError("split must name another variable than the one drawn.")
    groups = frame[by]
    if multi.is_multi(groups):
        raise ValueError(
            f"split needs one answer per respondent, and {by_label} allows several: "
            "use it as the variable drawn, or split by one of its options after "
            "Explode multiple choice."
        )
    series = frame[name]
    is_multi = multi.is_multi(series)
    if is_multi and chart.layout != "grouped":
        raise ValueError(
            f"{label} allows several answers, so its options overlap and cannot be "
            "stacked: draw them side by side (layout='grouped')."
        )
    weight = weights if weights is not None else np.ones(len(series))
    answered = _answered(series, is_multi) & groups.notna().to_numpy(dtype=bool)
    if not answered.any():
        raise ValueError(f"No respondent answered both {label} and {by_label}.")
    group_codes = sorted(pd.unique(groups[answered]), key=code_order)
    codes = (
        _multi_codes(data, name, series)
        if is_multi
        else _single_codes(data, name, series[answered])
    )
    chose = [_chose(series, code, is_multi) for code in codes]
    # Top N overall: the answers given most by everyone drawn, in code order.
    kept, rest = _top(np.array([weight[answered & hits].sum() for hits in chose]), chart.top)
    kept_names = [_name_of(data, name, codes[i]) for i in kept]
    other = _other_name(kept_names) if chart.other and rest else None
    columns = [chose[i] for i in kept]
    if other is not None:
        columns.append(_any_of([chose[i] for i in rest]))
    shown = len(kept)  # the answers themselves; Other, when drawn, after them
    counts = np.zeros((len(group_codes), len(columns)))
    sizes, bases = [], np.zeros(len(group_codes))
    members = []
    for row, group in enumerate(group_codes):
        member = answered & (groups == group).to_numpy(dtype=bool)
        members.append(member)
        sizes.append(int(member.sum()))
        bases[row] = weight[member].sum()
        for column, hits in enumerate(columns):
            counts[row, column] = weight[member & hits].sum()
    percent = chart.show == "percent" or chart.layout == "stacked_100"
    values = counts
    if percent:
        with np.errstate(divide="ignore", invalid="ignore"):
            values = np.where(bases[:, None] > 0, counts / bases[:, None] * 100.0, 0.0)
    ordered = _is_scale(data, name) and not is_multi
    groups_order = list(range(len(group_codes)))
    if ordered and chart.sort == "value":
        # The steps of a scale stay in their order — sorted by frequency, a
        # stack's colour ramp and its top box scramble — and the groups go
        # largest first instead: by the top answer's share, or a stack's height.
        order = list(range(shown))
        key = values[:, shown - 1] if percent else counts.sum(axis=1)
        groups_order = _order(key, "value")
    else:
        order = _order(counts[:, :shown].sum(axis=0), chart.sort)
    series_order = order + ([shown] if other is not None else [])
    weighted = weights is not None
    if percent:
        axis = f"% within {by_label}" + (" (weighted)" if weighted else "")
    else:
        axis = "Weighted count" if weighted else "Count"
    short = "% within each group" + (" (weighted)" if weighted else "") if percent else ""
    total = float(weight[answered].sum())
    notes = [
        _base(int(answered.sum()), total if weighted else None, "who answered both")
        + " Each group's n is under its name."
    ]
    if is_multi:
        notes.append(
            "Several answers allowed: each bar is the share of the group's respondents "
            "who named the option, so a group's bars add up to more than 100 %."
            if percent
            else "Several answers allowed: each bar counts the respondents who named the option."
        )
    elif percent:
        notes.append(f"Percentages are of each group of {by_label}.")
    if ordered and chart.sort == "value":
        top = kept_names[shown - 1]
        notes.append(
            f"Groups in order of their share of {top}; the answers keep the scale's order."
            if percent
            else "Groups largest first; the answers keep the scale's order."
        )
    if rest:
        notes.append(_top_note(len(kept), len(rest), other, is_multi, overall=True))

    lower = upper = None
    if chart.intervals and percent:
        lower, upper = np.full(values.shape, np.nan), np.full(values.shape, np.nan)
        for row, member in enumerate(members):
            lower[row], upper[row] = _share_bounds(columns, member, weights, chart.confidence)
        notes.append(_share_interval_note(chart, weighted))
    elif chart.intervals:
        notes.append(_NO_COUNT_INTERVALS)

    letters: dict[Any, str] = {}
    marks = None
    if chart.letters:
        letters, found, letter_notes = _significance(
            chart, frame, group_codes, members, counts, bases, weights
        )
        marks = [
            [found[column].get(group_codes[row], "") for column in series_order]
            for row in groups_order
        ]
        notes.extend(letter_notes)

    def position(index: int) -> str:
        group = group_codes[index]
        letter = f" ({letters[group]})" if group in letters else ""
        return f"{_name_of(data, by, group)}{letter}\n(n = {sizes[index]:,})"

    return Bars(
        values=values[groups_order][:, series_order],
        positions=[position(index) for index in groups_order],
        series=[kept_names[i] for i in order] + ([other] if other is not None else []),
        kind="percent" if percent else "count",
        value_label=axis,
        position_label=by_label,
        title=chart.title or f"{label} by {by_label}",
        legend_title=label,
        stacked=chart.layout != "grouped",
        full=chart.layout == "stacked_100",
        ordered=_is_scale(data, name),
        **_palette_places([kept[i] for i in order], len(codes), _is_scale(data, name)),
        notes=notes,
        short_value_label=short,
        lower=None if lower is None else lower[groups_order][:, series_order],
        upper=None if upper is None else upper[groups_order][:, series_order],
        marks=marks,
        other_series=shown if other is not None else None,
    )


def _significance(
    chart: BarChart,
    frame: pd.DataFrame,
    group_codes: list[Any],
    members: list[np.ndarray],
    counts: np.ndarray,
    bases: np.ndarray,
    weights: np.ndarray | None,
) -> tuple[dict[Any, str], list[dict[Any, str]], list[str]]:
    """The groups' letters, each answer's letters by group, and the notes.

    The Banner table's test as the Tab book runs it on the same data: groups
    lettered in the Banner table's column order (the codebook's, of the split
    variable as the data holds it), each group's base its respondents who
    answered the question — Kish's effective base weighted — and a group below
    :data:`MIN_TESTED` left out of the test.
    """

    from siamang.reporting.tables import banner_values, column_letter, proportion_letters

    data, by = chart.data, str(chart.split)
    variable = _variable(data, by)
    order = banner_values(frame[by], (variable.labels or {}) if variable is not None else {})
    letters = {code: column_letter(index) for index, code in enumerate(order)}
    tested: dict[Any, float] = {}
    for row, member in enumerate(members):
        if weights is None:
            tested[group_codes[row]] = float(member.sum())
        else:
            chosen = weights[member]
            squared = float((chosen**2).sum())
            tested[group_codes[row]] = float(chosen.sum()) ** 2 / squared if squared > 0 else 0.0
    group_letters = {code: letters[code] for code in group_codes}
    found = []
    for column in range(counts.shape[1]):
        shares = {
            code: counts[row, column] / bases[row] if bases[row] > 0 else 0.0
            for row, code in enumerate(group_codes)
        }
        found.append(
            proportion_letters(
                shares,
                tested,
                group_letters,
                level=chart.level,
                correction=chart.correction,
                min_base=MIN_TESTED,
            )
        )
    weighted = weights is not None
    how = (
        f"two-sided z-test of column proportions, p < {chart.level:g}"
        + (", Bonferroni-corrected" if chart.correction == "bonferroni" else "")
        + (", on Kish's effective base" if weighted else "")
    )
    notes = [
        "A letter over a bar names a group (its letter is under its name) whose share of "
        f"that answer is significantly lower ({how}) — the Banner table's and the Tab book's "
        "letters."
    ]
    thin = [
        f"{_name_of(data, by, code)} ({group_letters[code]})"
        for code in group_codes
        if tested[code] < MIN_TESTED
    ]
    if len(group_codes) - len(thin) >= 2 and not any(found):
        notes.append("No group's share of any answer is significantly higher than another's.")
    if thin and len(thin) >= len(group_codes) - 1:
        notes.append(
            f"No letters: fewer than two groups have {MIN_TESTED} respondents who answered, "
            "the least a group is tested on."
        )
    elif thin:
        notes.append(
            f"Not tested, fewer than {MIN_TESTED} respondents who answered: "
            + ", ".join(thin)
            + "."
        )
    return group_letters, found, notes


def _means(chart: BarChart, frame: pd.DataFrame, weights: np.ndarray | None) -> Bars:
    from siamang.data import multi

    data, name, by = chart.data, chart.column, str(chart.by)
    label, by_label = _label(data, name), _label(data, by)
    series = frame[name]
    if multi.is_multi(series):
        raise ValueError(
            f"{label} allows several answers, so it has no mean: draw its answers "
            "(without by), or split them by a group with split=."
        )
    values = pd.to_numeric(series, errors="coerce").to_numpy(dtype=float)
    weight = weights if weights is not None else np.ones(len(values))
    groups = frame[by]
    is_multi = multi.is_multi(groups)
    answered = _answered(groups, is_multi) & ~np.isnan(values)
    codes = (
        _multi_codes(data, by, groups)
        if is_multi
        else sorted(pd.unique(groups[answered]), key=code_order)
    )
    means, names, bounds, single = [], [], [], []
    for code in codes:
        member = _chose(groups, code, is_multi) & answered
        if not member.any():
            continue  # a group nobody is in has no mean
        total = float(weight[member].sum())
        means.append(
            float((weight[member] * values[member]).sum() / total) if total > 0 else np.nan
        )
        names.append(f"{_name_of(data, by, code)}\n(n = {int(member.sum()):,})")
        if chart.intervals:
            from siamang.data.intervals import mean_interval

            interval = mean_interval(
                values[member],
                None if weights is None else weights[member],
                confidence=chart.confidence,
            )
            bounds.append(
                (interval.lower, interval.upper) if interval.defined else (np.nan, np.nan)
            )
            if interval.note == "one answer has no interval":
                single.append(_name_of(data, by, code))
    if not names:
        raise ValueError(f"No respondent has both {label} and {by_label}.")
    means_array = np.array(means)
    order = _order(means_array, chart.sort)
    weighted = weights is not None
    notes = [
        _base(
            int(answered.sum()),
            float(weight[answered].sum()) if weighted else None,
            "who answered both",
        )
        + " Each group's n is under its name."
    ]
    if is_multi:
        notes.append(
            f"Several answers allowed in {by_label}: the groups overlap, and a "
            "respondent counts in every group they named."
        )
    lower = upper = None
    if chart.intervals:
        array = np.array(bounds, dtype=float)[order]
        lower, upper = array[:, :1], array[:, 1:]
        notes.append(
            f"Error bars: {_level(chart.confidence)} confidence intervals of the mean ("
            + ("weighted: the linearization interval)." if weighted else "Student's t).")
        )
        if single:
            notes.append("No interval for a group of one answer: " + ", ".join(single) + ".")
    return Bars(
        values=means_array[order].reshape(-1, 1),
        positions=[names[i] for i in order],
        series=[label],
        kind="mean",
        value_label=("Weighted mean " if weighted else "Mean ") + label,
        position_label=by_label,
        title=chart.title or f"Mean {label} by {by_label}",
        notes=notes,
        lower=lower,
        upper=upper,
    )


# ─── drawing ─────────────────────────────────────────────────────────────────


def value_text(value: float, kind: str) -> str:
    """A bar's value as it is written on the chart."""

    if kind == "percent":
        return f"{value:.1f}%"
    if kind == "mean":
        return f"{value:,.2f}"  # 41,646.65, as a count's thousands are
    return count_text(value)


#: A label turned under a vertical bar is at most this many characters a line:
#: longer ones would take the figure's height, and the bars are drawn across.
TURNED_WIDTH = 40


def _wrap_whole(text: str, width: int) -> str:
    """``text`` wrapped to ``width``, its "(n = 1,613)" kept on one line: it
    broke into "(n =" and "1,613)"."""

    held = re.sub(r"\(n = ([^)]*)\)", lambda match: f"(n\u00a0=\u00a0{match.group(1)})", text)
    return wrap(held, width).replace("\u00a0", " ")


def _group_label(text: str, width: int) -> str:
    """``text`` wrapped to ``width``, a group's "(n = …)" on a line of its own."""

    head, _, tail = text.partition("\n(n = ")
    return wrap(head, width) + (f"\n(n = {tail}" if tail else "")


def _tick_labels(labels: list[str], slot_pt: float) -> tuple[list[str], int, float] | None:
    """Labels under vertical bars ``slot_pt`` apart: wrapped to the room each
    has (smaller, to 8 pt, when a word is longer than it — a word is never
    broken), else turned 45° in as many lines as the slot holds between two
    turned labels. None when neither can be read: the bars are then drawn
    across, their labels beside them (:func:`_fit_across`)."""

    size = font_size("xtick.labelsize")
    room = slot_pt * 0.95
    longest = max((len(word) for text in labels for word in text.split()), default=1)
    upright = max(8.0, min(size, room / (longest * CHAR_WIDTH)))
    width = chars_in(room, upright)
    if width >= 5 and longest * upright * CHAR_WIDTH <= room:
        return [_group_label(text, width) for text in labels], 0, upright
    # Turned 45°, two neighbouring labels are slot · sin 45° apart across
    # their lines: that many lines fit, each of at most TURNED_WIDTH characters.
    lines = int(slot_pt * 0.7071 / (size * 1.2))
    if lines < 1:
        return None
    flat = [" ".join(text.split("\n")) for text in labels]
    for width in range(16, TURNED_WIDTH + 1):
        turned = [_wrap_whole(text, width) for text in flat]
        if all(text.count("\n") < lines for text in turned):
            return turned, 45, size
    return None


def _crowded(labels: list[Any], renderer: Any, horizontal: bool, gap_pt: float = 0.0) -> bool:
    """Whether two neighbouring tick labels overlap, or are closer than
    ``gap_pt`` points (words of two labels side by side read as one)."""

    boxes = [label.get_window_extent(renderer) for label in labels if label.get_text()]
    gap = gap_pt / 72.0 * labels[0].figure.dpi if boxes else 0.0
    if horizontal:
        boxes.sort(key=lambda box: box.y0)
        return any(
            low.y1 + gap > high.y0 + 0.5 for low, high in zip(boxes, boxes[1:], strict=False)
        )
    boxes.sort(key=lambda box: box.x0)
    return any(
        left.x1 + gap > right.x0 + 0.5 for left, right in zip(boxes, boxes[1:], strict=False)
    )


#: The least room between two labels side by side under the bars, in ems of
#: their size: closer, "metropolitan" and its neighbour's "(n = 4,249)" on one
#: line read as one phrase.
LABEL_GAP = 1.0


def _place_under(ax: Any, placed: tuple[list[str], int, float]) -> None:
    labels, rotation, size = placed
    ax.set_xticklabels(
        labels,
        fontsize=size,
        rotation=rotation,
        ha="right" if rotation else "center",
        rotation_mode="anchor" if rotation else "default",
    )


def _fit_under(
    ax: Any, footnote: Footnote, labels: list[str], placed: tuple[list[str], int, float]
) -> bool:
    """The labels under vertical bars fitted again to the plot as laid out.

    They were fitted to a share of the figure's width; the value axis's title
    and ticks take their room first, so on a narrow figure the plot is much
    narrower (229 of 360 pt at 5 in) and turned labels were drawn over one
    another. Level labels closer than :data:`LABEL_GAP` are made smaller or
    turned; turned ones get as many lines as their measured spacing holds.
    False when no placement can be read: the bars are then drawn across."""

    renderer = ax.figure.canvas.get_renderer()
    shrink = 1.0
    for _ in range(4):
        slot = axes_points(ax)[0] / max(len(labels), 1)
        _, rotation, size = placed
        if rotation:
            lines = max(label.get_text().count("\n") + 1 for label in ax.get_xticklabels())
            fits = lines <= int(slot * 0.7071 / (font_size("xtick.labelsize") * 1.2))
        else:
            fits = not _crowded(ax.get_xticklabels(), renderer, False, LABEL_GAP * size)
        if fits:
            return True
        if not rotation:
            shrink *= 0.85  # the estimate was generous: the words are wider
        again = _tick_labels(labels, slot * shrink)
        if again is None:
            return False
        placed = again
        _place_under(ax, placed)
        footnote.apply()
    return False


def _fit_across(ax: Any, footnote: Footnote, labels: list[str], figure_pt: float) -> None:
    """The labels beside horizontal bars: the largest size and the narrowest
    column (a share of the figure's width) at which no two of them overlap,
    else the smallest, with the figure grown to a row per label's height."""

    base = font_size("ytick.labelsize")
    tries = ((base, 0.28), (base - 1, 0.28), (base - 1, 0.36), (8.0, 0.36), (8.0, 0.45))
    renderer = ax.figure.canvas.get_renderer()
    for size, share in tries:
        width = chars_in(share * figure_pt, size)
        ax.set_yticklabels([_group_label(text, width) for text in labels], fontsize=size)
        footnote.apply()
        if not _crowded(ax.get_yticklabels(), renderer, True):
            return
    scale = 72.0 / ax.figure.dpi
    tallest = max(label.get_window_extent(renderer).height for label in ax.get_yticklabels())
    footnote.least = max(footnote.least, len(labels) * (tallest * scale + 5.0))
    footnote.apply()


def _axis_titles(ax: Any, bars: Bars, horizontal: bool, title: str) -> None:
    """The axis titles and the title wrapped to the plot they label: a
    question as a Split by label is longer than a plot is tall."""

    width, height = axes_points(ax)
    size = font_size("axes.labelsize")
    across = bars.value_label
    if bars.short_value_label and len(across) > chars_in(width if horizontal else height, size):
        across = bars.short_value_label
    along = bars.position_label
    x_text, y_text = (across, along) if horizontal else (along, across)
    ax.set_xlabel(wrap(x_text, chars_in(width, size)) if x_text else "")
    ax.set_ylabel(wrap(y_text, chars_in(height, size)) if y_text else "")
    # Centred over the plot, the title may reach as far to either side of its
    # centre as the figure goes on the nearer one.
    box = ax.get_position()
    centre = (box.x0 + box.x1) / 2.0
    room = 2.0 * min(centre, 1.0 - centre) * ax.figure.get_figwidth() * 72.0 - 8.0
    ax.set_title(wrap(title, chars_in(max(room, width), font_size("axes.titlesize"))))


def render(chart: BarChart, bars: Bars, *, across: bool = False) -> None:
    """Draw ``bars`` on a new figure of ``chart`` (``across``: horizontally,
    whatever the chart asks — its labels could not be read under the bars)."""

    import matplotlib.pyplot as plt

    chart_theme.set_theme(style="whitegrid", palette=chart.palette)
    values = bars.values
    positions, count = values.shape
    figure_pt = chart.figsize[0] * 72.0
    # Beside the plot when the figure is wide enough, else under it.
    legend_beside = count > 1 and figure_pt >= 7.5 * 72.0
    legend_pt = min(0.3 * figure_pt, 11.0 * 0.6 * 24 + 40.0) if legend_beside else 0.0
    horizontal = chart.horizontal or across
    placed = None
    if not horizontal:
        placed = _tick_labels(bars.positions, (0.85 * figure_pt - legend_pt) / max(positions, 1))
        # Labels that cannot be read under the bars go beside them.
        horizontal = placed is None

    fig, ax = plt.subplots(figsize=chart.figsize)
    chart._fig, chart._ax = fig, ax
    # Other is grey, and the answers' colours are the palette's without it.
    plain = count - (bars.other_series is not None)
    palette = series_colours(chart.palette, max(plain, bars.palette_size), ordered=bars.ordered)
    colours = [palette[index] for index in (bars.colour_index or range(plain))]
    other = _other()
    if bars.other_series is not None:
        colours.insert(bars.other_series, other)
    at = np.arange(positions, dtype=float)
    if bars.stacked or count == 1:
        thickness, offsets = 0.7, [0.0] * count
    else:
        thickness = 0.8 / count
        offsets = [-0.4 + thickness * (index + 0.5) for index in range(count)]
    base = np.zeros(positions)
    for index in range(count):
        heights = values[:, index]
        colour: Any = colours[index]
        if count == 1 and bars.other_position is not None:
            colour = [
                other if position == bars.other_position else colour
                for position in range(positions)
            ]
        style = {
            "color": colour,
            "label": bars.series[index],
            "edgecolor": "white",
            "linewidth": 0.8 if count > 1 else 0.0,
        }
        where = at + offsets[index]
        if horizontal:
            ax.barh(where, heights, height=thickness, left=base if bars.stacked else None, **style)
        else:
            ax.bar(where, heights, width=thickness, bottom=base if bars.stacked else None, **style)
        if bars.stacked:
            base = base + np.nan_to_num(heights)
    if bars.lower is not None and bars.upper is not None and not bars.stacked:
        slot_pt = (0.8 * figure_pt if not horizontal else 0.75 * chart.figsize[1] * 72.0) / max(
            positions, 1
        )
        _error_bars(ax, bars, offsets, horizontal, cap=min(4.0, thickness * slot_pt * 0.25))

    value_axis, position_axis = (ax.xaxis, ax.yaxis) if horizontal else (ax.yaxis, ax.xaxis)
    if bars.kind == "percent":
        percent_axis(value_axis)
    elif bars.kind == "count":
        thousands_axis(value_axis)
    elif bars.kind == "mean" and np.nanmax(np.abs(values), initial=0.0) >= 1000:
        thousands_axis(value_axis)  # a mean of thousands reads as a count's
    if bars.full:
        (ax.set_xlim if horizontal else ax.set_ylim)(0, 100)
    ax.grid(False)
    ax.grid(True, axis="x" if horizontal else "y", color=chart_theme.grid("0.88"), linewidth=0.8)
    ax.set_axisbelow(True)
    position_axis.set_ticks(at)
    if horizontal:
        ax.set_yticklabels(
            [_group_label(text, chars_in(0.28 * figure_pt, 11.0)) for text in bars.positions]
        )
        ax.set_ylim(positions - 0.5, -0.5)  # the first answer on top
    else:
        _place_under(ax, placed)  # type: ignore[arg-type]
        ax.set_xlim(-0.5, positions - 0.5)
    title = bars.title
    _axis_titles(ax, bars, horizontal, title)

    below = None
    if count > 1:
        handles, names = ax.get_legend_handles_labels()
        if legend_beside:
            if bars.stacked and not horizontal:  # the top segment first, as drawn
                handles, names = handles[::-1], names[::-1]
            ax.legend(
                handles,
                [wrap(name, 24) for name in names],
                title=wrap(bars.legend_title, 24),
                loc="upper left",
                bbox_to_anchor=(1.01, 1.0),
                frameon=False,
                fontsize=10,
                title_fontsize=10,
            )
        else:
            below = legend_below(fig, handles, names, bars.legend_title, figure_pt)

    footnote = Footnote(fig, bars.notes, legend=below, axes=ax)
    footnote.apply()
    side = ax.get_legend()
    if side is not None:
        renderer = fig.canvas.get_renderer()
        if side.get_window_extent(renderer).height > ax.get_window_extent(renderer).height + 1:
            # Taller than the plot, it would run over the notes: under the plot.
            handles, names = ax.get_legend_handles_labels()
            side.remove()
            footnote.legend = legend_below(fig, handles, names, bars.legend_title, figure_pt)
            footnote.apply()
    if horizontal:
        _fit_across(ax, footnote, bars.positions, figure_pt)
    for _ in range(2):  # wrapped to the plot as it is laid out
        _axis_titles(ax, bars, horizontal, title)
        footnote.apply()
    if not horizontal and not _fit_under(ax, footnote, bars.positions, placed):  # type: ignore[arg-type]
        # Under the plot as it is laid out (narrower than the figure the
        # labels were first fitted to), they cannot be read: across.
        plt.close(fig)
        chart._fig = chart._ax = None
        render(chart, bars, across=True)
        return
    marked = bars.marks is not None and any(mark for row in bars.marks for mark in row)
    if chart.show_values or marked:
        written = _write_values(
            ax, bars, colours, thickness, offsets, horizontal, show_values=chart.show_values
        )
        if marked and written is None:
            footnote.add(
                "The bars are too narrow to carry their significance letters: the Banner "
                "table and the Tab book show them."
            )
        footnote.apply()
        if marked and written:
            _keep_inside(ax, written, horizontal)
            footnote.apply()
    if horizontal and bars.kind != "percent":
        # Counts and means of thousands on a narrow plot, once the value axis
        # has its final length.
        fit_ticks(ax, "x")


def _keep_inside(ax: Any, texts: list[Any], horizontal: bool) -> None:
    """Widen the value axis until every text past a bar's end is inside the
    plot: a value with its letters, measured as drawn rather than estimated."""

    renderer = ax.figure.canvas.get_renderer()
    margin = 4.0 * ax.figure.dpi / 72.0  # clear of the plot's edge
    for _ in range(3):
        box = ax.get_window_extent(renderer)
        low, high = ax.get_xlim() if horizontal else ax.get_ylim()
        ends = [text.get_window_extent(renderer) for text in texts]
        over = max((end.x1 - box.x1) if horizontal else (end.y1 - box.y1) for end in ends)
        over += margin
        if over <= 0.5:
            return
        along = box.width if horizontal else box.height
        (ax.set_xlim if horizontal else ax.set_ylim)(
            low, high + over / max(along - over, 1.0) * (high - low)
        )


def _error_bars(ax: Any, bars: Bars, offsets: list[float], horizontal: bool, *, cap: float) -> None:
    """Each bar's confidence interval as a whisker over its end; a bar
    without one (a single answer) has none."""

    assert bars.lower is not None and bars.upper is not None
    positions, count = bars.values.shape
    for index in range(count):
        middle, low, high = (array[:, index] for array in (bars.values, bars.lower, bars.upper))
        keep = ~(np.isnan(low) | np.isnan(high) | np.isnan(middle))
        if not keep.any():
            continue
        where = (np.arange(positions, dtype=float) + offsets[index])[keep]
        spread = np.vstack([middle[keep] - low[keep], high[keep] - middle[keep]]).clip(min=0.0)
        style = {
            "fmt": "none",
            "ecolor": _ink(),
            "elinewidth": 1.0,
            "capsize": cap,
            "capthick": 1.0,
            "zorder": 3,
            "label": "_nolegend_",
        }
        if horizontal:
            ax.errorbar(middle[keep], where, xerr=spread, **style)
        else:
            ax.errorbar(where, middle[keep], yerr=spread, **style)


def _write_values(
    ax: Any,
    bars: Bars,
    colours: list[Any],
    thickness: float,
    offsets: list[float],
    horizontal: bool,
    *,
    show_values: bool = True,
) -> list[Any] | None:
    """Each bar's value where it fits: beside its end, or inside its segment of a
    stack. A value that would not fit is left to the axis, never cut off.

    Beside a bar with an error bar the value goes past the whisker, and a
    bar's significance letters (bold) after its value. Returns the texts
    written past the bars' ends — or None when bars side by side are too
    narrow to carry them, and nothing was written."""

    values = bars.values
    positions, count = values.shape
    width_pt, height_pt = axes_points(ax)
    along_pt = width_pt if horizontal else height_pt
    across_pt = height_pt if horizontal else width_pt
    low, high = ax.get_xlim() if horizontal else ax.get_ylim()
    span = max(high - low, 1e-12)
    band_pt = thickness / max(positions, 1) * across_pt  # a bar's thickness
    size = VALUE_SIZE

    if bars.stacked:
        base = np.zeros(positions)
        for index in range(count):
            for position in range(positions):
                value = values[position, index]
                if not value or value != value:
                    continue
                text = value_text(value, bars.kind)
                length = value / span * along_pt
                fits = (
                    length >= text_width(text, size) + 6 and band_pt >= size + 3
                    if horizontal
                    else length >= size + 4 and band_pt >= text_width(text, size) + 4
                )
                if fits:
                    middle = base[position] + value / 2.0
                    xy = (middle, position) if horizontal else (position, middle)
                    ax.text(
                        *xy,
                        text,
                        ha="center",
                        va="center",
                        fontsize=size,
                        color=ink_on(colours[index]),
                    )
            base = base + np.nan_to_num(values[:, index])
        if bars.full or bars.kind != "count" or not show_values:
            return []
        tips = [(position, 0.0, base[position], base[position]) for position in range(positions)]
        kind_values = [value_text(total, bars.kind) for total in base]
        marks = [""] * len(tips)
    else:
        tips, kind_values, marks = [], [], []
        for index in range(count):
            for position in range(positions):
                value = values[position, index]
                if value != value:
                    continue
                end = value  # past the whisker, when there is one
                if bars.upper is not None and bars.lower is not None:
                    reach = (
                        bars.upper[position, index] if value >= 0 else bars.lower[position, index]
                    )
                    if reach == reach:
                        end = max(value, reach) if value >= 0 else min(value, reach)
                mark = bars.marks[position][index] if bars.marks is not None else ""
                if not show_values and not mark:
                    continue
                tips.append((position, offsets[index], value, end))
                kind_values.append(value_text(value, bars.kind) if show_values else "")
                marks.append(mark)
    if not tips:
        return []
    gap = 4.0  # between a value and its letters
    widths = [
        text_width(text, size) + (text_width(mark, size) + (gap if text else 0.0) if mark else 0.0)
        for text, mark in zip(kind_values, marks, strict=True)
    ]
    widest = max(widths)
    rotation = 0
    if horizontal:
        if band_pt < size * 0.9:
            return None
    elif band_pt < widest + 2:
        if band_pt < size * 1.15:  # turned values of neighbouring bars would touch
            return None
        rotation = 90
    written: list[Any] = []
    renderer = ax.figure.canvas.get_renderer()
    stacked_marks = not horizontal and not rotation and any(marks) and any(kind_values)
    extent_pt = (
        widest if horizontal or rotation else size * (2.25 if stacked_marks else 1.0)
    ) + 6.0
    for (position, offset, value, end), text, mark in zip(tips, kind_values, marks, strict=True):
        sign = 1.0 if value >= 0 else -1.0
        # The letters follow the value: beside it across, over it upright,
        # further along it turned.
        after = text_width(text, size) + gap if text else 0.0
        if horizontal:
            anchor = (end, position + offset)
            shifts = [(3 * sign, 0), (3 * sign + after * sign, 0)]
            common = {"ha": "left" if sign > 0 else "right", "va": "center"}
        else:
            anchor = (position + offset, end)
            above = after if rotation else (size * 1.25 if text else 0.0)
            shifts = [(0, 3 * sign), (0, 3 * sign + above * sign)]
            common = {
                "ha": "center",
                "va": "bottom" if sign > 0 else "top",
                "rotation": rotation,
            }
        if text:
            written.append(
                ax.annotate(
                    text,
                    anchor,
                    xytext=shifts[0],
                    textcoords="offset points",
                    fontsize=size,
                    **common,
                )
            )
            if mark and (horizontal or rotation):
                # After the value as drawn, not as estimated: a theme's face
                # is narrower or wider than the estimate, and the letters keep
                # their gap in any.
                box = written[-1].get_window_extent(renderer)
                drawn = (box.width if horizontal else box.height) * 72.0 / ax.figure.dpi
                push = (3 + drawn + gap) * sign
                shifts[1] = (push, 0) if horizontal else (0, push)
        if mark:
            written.append(
                ax.annotate(
                    mark,
                    anchor,
                    xytext=shifts[1],
                    textcoords="offset points",
                    fontsize=size,
                    fontweight="bold",
                    color=_ink(),
                    **common,
                )
            )
    # Room beyond the longest bar (or whisker) for its value.
    room = extent_pt / along_pt * span * 1.15
    tops = [end for _, _, _, end in tips]
    new_high = max(high, max(tops) + room)
    new_low = min(low, min(tops) - room) if min(tops) < 0 else low
    (ax.set_xlim if horizontal else ax.set_ylim)(new_low, new_high)
    return written


# ─── histogram ───────────────────────────────────────────────────────────────


@dataclass
class Histogram:
    """What a histogram draws: counts (or percent) per bin, a panel per group."""

    edges: np.ndarray
    #: One array of heights per panel, and the panel's title ("" for one panel).
    heights: list[np.ndarray]
    panels: list[str]
    kind: str  # count | percent
    value_label: str
    title: str
    #: The edges were given: the axis is ticked at them.
    explicit: bool = False
    notes: list[str] = field(default_factory=list)


_BINS_HELP = (
    "Bins is auto (Freedman and Diaconis's width), a number of bins, or the bins' edges "
    "in increasing order, separated by commas (0, 18, 35, 65)"
)


def parse_bins(bins: Any) -> str | int | list[float]:
    """What ``bins`` asks for: ``"auto"``, a number of bins, or their edges.

    ``None``, ``""`` and ``"auto"`` are auto; a whole number (or its text) is
    the number of equal bins, 1 to :data:`MAX_BINS`; two numbers or more (a
    list, or text separated by commas, semicolons or spaces) are the edges,
    each greater than the one before. Anything else is a ``ValueError`` that
    says what Bins takes.
    """

    if bins is None or (isinstance(bins, str) and bins.strip().casefold() in ("", "auto")):
        return "auto"
    numbers: list[float]
    if isinstance(bins, bool):
        raise ValueError(f"{_BINS_HELP}; got {bins!r}.")
    if isinstance(bins, int | float | np.integer | np.floating):
        numbers = [float(bins)]
    elif isinstance(bins, str):
        parts = [part for part in re.split(r"[,;\s]+", bins.strip()) if part]
        try:
            numbers = [float(part) for part in parts]
        except ValueError:
            raise ValueError(f"{_BINS_HELP}; got {bins!r}.") from None
    elif isinstance(bins, list | tuple | np.ndarray):
        try:
            numbers = [float(edge) for edge in bins]
        except (TypeError, ValueError):
            raise ValueError(f"{_BINS_HELP}; got {bins!r}.") from None
    else:
        raise ValueError(f"{_BINS_HELP}; got {bins!r}.")
    if not numbers or not all(math.isfinite(number) for number in numbers):
        raise ValueError(f"{_BINS_HELP}; got {bins!r}.")
    if len(numbers) == 1:
        if not numbers[0].is_integer() or not 1 <= numbers[0] <= MAX_BINS:
            raise ValueError(
                f"A number of bins is a whole number from 1 to {MAX_BINS}; got {bins!r}."
            )
        return int(numbers[0])
    if len(numbers) - 1 > MAX_BINS:
        raise ValueError(f"At most {MAX_BINS} bins: {len(numbers)} edges give {len(numbers) - 1}.")
    for left, right in zip(numbers, numbers[1:], strict=False):
        if not right > left:
            raise ValueError(
                f"The bins' edges must increase from one to the next, and {left:g} is followed "
                f"by {right:g}."
            )
    return numbers


def histogram_edges(values: np.ndarray, bins: Any) -> tuple[np.ndarray, str]:
    """The bins' edges for ``values`` and a sentence saying how they were chosen.

    Auto is Freedman and Diaconis's width, 2 · IQR / n^(1/3), as
    ``numpy.histogram_bin_edges(values, "fd")`` gives it — Sturges' number of
    bins when the middle half of the answers is one value. Answers that are
    all whole numbers take a whole width (at least 1), the edges halfway
    between two numbers, so no bin holds more possible answers than another
    and none falls on an edge. More than :data:`MAX_BINS` bins are drawn as
    that many.
    """

    chosen = parse_bins(bins)
    if isinstance(chosen, list):
        return np.array(chosen, dtype=float), "the edges given"
    if isinstance(chosen, int):
        edges = np.histogram_bin_edges(values, bins=chosen)
        return edges, f"{chosen} of equal width"
    n = values.size
    low, high = float(values.min()), float(values.max())
    q75, q25 = np.percentile(values, [75, 25])
    spread = float(q75 - q25)
    rule = "Freedman–Diaconis" if spread > 0 else "Sturges"
    if bool(np.all(values == np.round(values))):
        if spread > 0:
            width = 2.0 * spread / n ** (1.0 / 3.0)
        else:
            width = (high - low) / (math.ceil(math.log2(n)) + 1)
        width = float(max(1, math.ceil(width - 1e-9)))
        count = math.ceil((high - low + 1.0) / width)
        if count > MAX_BINS:
            width = float(math.ceil((high - low + 1.0) / MAX_BINS))
            count = math.ceil((high - low + 1.0) / width)
            rule += f", widened to {MAX_BINS} bins at most"
        edges = low - 0.5 + width * np.arange(count + 1)
        each = "one whole number" if width == 1 else f"{_number(width)} whole numbers"
        return edges, f"{count} of width {_number(width)} ({rule}), each holding {each}"
    edges = np.histogram_bin_edges(values, bins="fd" if spread > 0 else "sturges")
    if len(edges) - 1 > MAX_BINS:
        edges = np.histogram_bin_edges(values, bins=MAX_BINS)
        rule += f", {MAX_BINS} bins at most"
    return edges, f"{len(edges) - 1} of width {_number(float(edges[1] - edges[0]))} ({rule})"


def _number(value: float) -> str:
    """A bin's width or edge: three figures, thousands separated (7,090, 2.46)."""

    if abs(value) >= 1000:
        return f"{value:,.0f}"
    return f"{value:.3g}"


def _histogram(chart: BarChart, frame: pd.DataFrame, weights: np.ndarray | None) -> Histogram:
    from siamang.data import multi

    data, name = chart.data, chart.column
    label = _label(data, name)
    series = frame[name]
    variable = _variable(data, name)
    if multi.is_multi(series):
        raise ValueError(
            f"{label} allows several answers; a histogram draws one number per respondent."
        )
    if variable is not None and variable.scale in ("nominal", "ordinal"):
        raise ValueError(
            f"A histogram draws the distribution of a number, and {label} is "
            f"{variable.scale}: draw its answers as bars (layout='grouped')."
        )
    numbers = pd.to_numeric(series, errors="coerce").to_numpy(dtype=float)
    answered = _answered(series, False)
    text = answered & ~np.isfinite(numbers)
    if text.any():
        raise ValueError(
            f"A histogram draws numbers, and {label} holds an answer that is not one "
            f"(for example {series[text].iloc[0]!r})."
        )
    weight = weights if weights is not None else np.ones(len(series))
    groups, group_codes, by_label = None, [], ""
    if chart.split:
        by = str(chart.split)
        by_label = _label(data, by)
        if by == name:
            raise ValueError("split must name another variable than the one drawn.")
        groups = frame[by]
        if multi.is_multi(groups):
            raise ValueError(
                f"split needs one answer per respondent, and {by_label} allows several: "
                "use it as the variable drawn, or split by one of its options after "
                "Explode multiple choice."
            )
        answered = answered & groups.notna().to_numpy(dtype=bool)
        group_codes = sorted(pd.unique(groups[answered]), key=code_order)
        if len(group_codes) > MAX_PANELS:
            raise ValueError(
                f"{by_label} has {len(group_codes)} groups, and a histogram draws a panel for "
                f"each: at most {MAX_PANELS}. Band it (Bands) or split by a variable of "
                "fewer groups."
            )
    if not answered.any():
        raise ValueError(
            f"No respondent answered {label}" + (f" and {by_label}." if chart.split else ".")
        )
    edges, how = histogram_edges(numbers[answered], chart.bins)
    percent = chart.show == "percent"

    def tally(mask: np.ndarray) -> np.ndarray:
        counts, _ = np.histogram(
            numbers[mask], bins=edges, weights=None if weights is None else weights[mask]
        )
        counts = counts.astype(float)
        base = float(weight[mask].sum())
        if percent:
            return counts / base * 100.0 if base > 0 else np.zeros(len(counts))
        return counts

    heights, panels = [], []
    if groups is None:
        heights.append(tally(answered))
        panels.append("")
    else:
        for code in group_codes:
            member = answered & (groups == code).to_numpy(dtype=bool)
            heights.append(tally(member))
            panels.append(f"{_name_of(data, str(chart.split), code)} (n = {int(member.sum()):,})")
    weighted = weights is not None
    if percent:
        axis = ("% of respondents" if groups is None else "% within each group") + (
            " (weighted)" if weighted else ""
        )
    else:
        axis = "Weighted count" if weighted else "Count"
    notes = [
        _base(
            int(answered.sum()),
            float(weight[answered].sum()) if weighted else None,
            "who answered both" if groups is not None else "who answered",
        )
        + (" Each group's n is over its panel." if groups is not None else "")
    ]
    if groups is not None and percent:
        notes.append(f"Percentages are of each group of {by_label}.")
    explicit = isinstance(parse_bins(chart.bins), list)
    bin_note = f"Bins: {how}"
    if explicit:
        bin_note += "; each bin holds its left edge, the last its right edge too"
    if weighted and parse_bins(chart.bins) == "auto":
        bin_note += "; the width is of the answers as they are, the heights weighted"
    notes.append(bin_note + ".")
    widths = np.diff(edges)
    if not np.allclose(widths, widths[0]):
        notes.append(
            "The bins differ in width: a bar's height is its "
            + ("percentage" if percent else "count")
            + ", not its density."
        )
    values = numbers[answered]
    outside = int(((values < edges[0]) | (values > edges[-1])).sum())
    if outside:
        notes.append(
            f"{outside:,} {'answer' if outside == 1 else 'answers'} outside the bins (below "
            f"{_number(edges[0])} or above {_number(edges[-1])}) not drawn"
            + (", but in the base." if percent else ".")
        )
    return Histogram(
        edges=edges,
        heights=heights,
        panels=panels,
        kind="percent" if percent else "count",
        value_label=axis,
        title=chart.title or (f"{label} by {by_label}" if groups is not None else label),
        explicit=explicit,
        notes=notes,
    )


#: A panel of a histogram split into groups is at least this tall, in points.
PANEL_PT = 72.0


def render_histogram(chart: BarChart, histogram: Histogram) -> None:
    """Draw ``histogram`` on a new figure of ``chart``: one plot, or a panel
    per group, sharing their bins and their value axis, one above the other
    (two columns past four groups)."""

    import matplotlib.pyplot as plt

    chart_theme.set_theme(style="whitegrid", palette=chart.palette)
    panels = len(histogram.heights)
    colour = series_colours(chart.palette, 1)[0]
    edges = histogram.edges
    widths = np.diff(edges)
    if panels == 1:
        fig, ax = plt.subplots(figsize=chart.figsize)
        axes = [ax]
    else:
        columns = 1 if panels <= 4 else 2
        rows = -(-panels // columns)
        # Each panel at least PANEL_PT tall, with its title and ticks.
        height = max(chart.figsize[1], (rows * (PANEL_PT + 30.0) + 120.0) / 72.0)
        fig, grid = plt.subplots(
            rows,
            columns,
            figsize=(chart.figsize[0], height),
            sharex=True,
            sharey=True,
            squeeze=False,
        )
        axes = list(grid.flat)
        for index, ax in enumerate(axes):
            if index >= panels:
                ax.set_visible(False)
            elif index + columns >= panels:  # the lowest of its column: its ticks
                ax.xaxis.set_tick_params(labelbottom=True)
    chart._fig, chart._ax = fig, axes[0]
    figure_pt = chart.figsize[0] * 72.0
    panel_pt = figure_pt / (1 if panels <= 4 else 2)
    short = {"count": "Count", "percent": "% of the group"}[histogram.kind]
    if histogram.kind == "count" and histogram.value_label.startswith("Weighted"):
        short = "Weighted count"
    for index, (heights, title) in enumerate(zip(histogram.heights, histogram.panels, strict=True)):
        ax = axes[index]
        ax.bar(
            edges[:-1],
            heights,
            width=widths,
            align="edge",
            color=colour,
            edgecolor="white",
            linewidth=0.6 if len(widths) <= 60 else 0.0,
        )
        ax.grid(False)
        ax.grid(True, axis="y", color=chart_theme.grid("0.88"), linewidth=0.8)
        ax.set_axisbelow(True)
        if histogram.kind == "percent":
            percent_axis(ax.yaxis)
        else:
            thousands_axis(ax.yaxis)
        thousands_axis(ax.xaxis)
        if histogram.explicit and len(edges) <= 25:
            ax.set_xticks(edges)
        margin = (edges[-1] - edges[0]) * 0.01
        ax.set_xlim(edges[0] - margin, edges[-1] + margin)
        if title:
            ax.set_title(
                _wrap_whole(title, chars_in(panel_pt - 40.0, 10.0)), loc="left", fontsize=10
            )
    title_size = font_size("axes.titlesize")
    label_size = font_size("axes.labelsize")
    if panels == 1:
        ax = axes[0]
        ax.set_ylabel(wrap(histogram.value_label, chars_in(axes_points(ax)[1], label_size)))
        ax.set_title(wrap(histogram.title, chars_in(figure_pt - 60.0, title_size)))
        Footnote(fig, histogram.notes, axes=ax).apply()
        fit_ticks(ax, "x")
        return
    fig.suptitle(wrap(histogram.title, chars_in(figure_pt - 40.0, title_size)), fontsize=title_size)
    footnote = Footnote(fig, histogram.notes)
    labelled = axes[: panels : 1 if panels <= 4 else 2]  # the first column's
    for ax in labelled:
        ax.set_ylabel(short)
    footnote.apply()
    # Each panel at least PANEL_PT tall as laid out: its title wraps to as
    # many lines as a long group name needs, which a fixed allowance per
    # panel did not foresee (8 groups at 5 × 4 in left panels 24 pt tall).
    shown = [ax for ax in axes if ax.get_visible()]
    for _ in range(3):
        short_pt = PANEL_PT - min(axes_points(ax)[1] for ax in shown)
        if short_pt <= 0.5:
            break
        fig.set_figheight(fig.get_figheight() + short_pt * rows / 72.0)
        footnote.apply()
    # The value axis's title in as many lines as each panel's height needs.
    for ax in labelled:
        ax.set_ylabel(wrap(short, chars_in(axes_points(ax)[1], label_size)))
    footnote.apply()
    fit_ticks(shown[-1], "x")  # shared: every panel's


# ─── donut ───────────────────────────────────────────────────────────────────


#: The ring's width, as a share of the donut's radius.
RING = 0.38


@dataclass
class Donut:
    """What a donut draws: each slice's share of the respondents who answered."""

    shares: np.ndarray
    names: list[str]
    title: str
    legend_title: str
    ordered: bool
    #: Each slice's answer's place among the ``palette_size`` answers, as a
    #: split of the same question colours it (Top N's and the small ones
    #: combined as Other included).
    colour_index: list[int]
    palette_size: int
    #: The slice that combines answers as Other, drawn grey.
    other: int | None
    respondents: int
    weighted_base: float | None
    notes: list[str] = field(default_factory=list)


def _names_list(names: list[str]) -> str:
    if len(names) > 6:
        return ", ".join(names[:5]) + f" and {len(names) - 5} more"
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def _donut(chart: BarChart, frame: pd.DataFrame, weights: np.ndarray | None) -> Donut:
    from siamang.data import multi

    data, name = chart.data, chart.column
    series = frame[name]
    label = _label(data, name)
    if multi.is_multi(series):
        raise ValueError(
            f"{label} allows several answers, so its shares add up to more than 100 % and "
            "are not the parts of a whole: draw them as bars (layout='grouped')."
        )
    weight = weights if weights is not None else np.ones(len(series))
    answered = _answered(series, False)
    if not answered.any():
        raise ValueError(f"No respondent answered {label}.")
    base = float(weight[answered].sum())
    if base <= 0:
        raise ValueError(f"No answer to {label} carries weight.")
    codes = _single_codes(data, name, series[answered])
    hits = [_chose(series, code, False) & answered for code in codes]
    counts = np.array([weight[chose].sum() for chose in hits], dtype=float)
    shares = counts / base * 100.0
    top, rest = _top(counts, chart.top)
    nobody = sorted(i for i in top + rest if counts[i] <= 0)  # no slice to draw
    given = [i for i in top if counts[i] > 0]
    rest = [i for i in rest if counts[i] > 0]
    small = [i for i in given if shares[i] < chart.min_slice]
    # One small slice alone is not combined: Other would only rename it.
    if not rest and len(small) < 2:
        small = []
    kept = [i for i in given if i not in small]
    if not kept:
        # Every answer under min_slice: Other would be the whole ring.
        raise ValueError(
            f"Each of the {len(given)} answers to {label} drawn is under {chart.min_slice:g} % "
            "of the respondents who answered, so Other would fill the whole ring: draw them "
            "as bars (layout='grouped'), or lower min_slice."
        )
    order = [kept[i] for i in _order(shares[kept], chart.sort)]
    names = [_name_of(data, name, codes[i]) for i in order]
    values = [shares[i] for i in order]
    other = None
    notes = [_base(int(answered.sum()), base if weights is not None else None, "who answered")]
    if rest or small:
        other_name = _other_name(names)
        names.append(other_name)
        values.append(float(shares[rest + small].sum()))
        other = len(names) - 1
        if rest:
            notes.append(
                f"The {len(top)} answers given most of {len(counts)} are drawn; {other_name} "
                f"combines the other {len(rest)} — a donut's slices make a whole."
            )
        if small:
            smaller = [_name_of(data, name, codes[i]) for i in small]
            notes.append(
                f"{other_name} {'also ' if rest else ''}combines {len(small)} answers under "
                f"{chart.min_slice:g} % each: {_names_list(smaller)}."
            )
    if nobody:
        notes.append(
            "Nobody answered " + _names_list([_name_of(data, name, codes[i]) for i in nobody]) + "."
        )
    return Donut(
        shares=np.array(values, dtype=float),
        names=names,
        title=chart.title or label,
        legend_title=label,
        ordered=_is_scale(data, name),
        **_palette_places(order, len(codes), _is_scale(data, name)),
        other=other,
        respondents=int(answered.sum()),
        weighted_base=base if weights is not None else None,
        notes=notes,
    )


def render_donut(chart: BarChart, donut: Donut) -> None:
    """Draw ``donut`` on a new figure of ``chart``: the slices clockwise from
    the top, each one's percentage on it — beside it when it is too thin —
    the base in the middle, the answers in a legend."""

    import matplotlib.pyplot as plt

    chart_theme.set_theme(style="white", palette=chart.palette)
    fig, ax = plt.subplots(figsize=chart.figsize)
    chart._fig, chart._ax = fig, ax
    count = len(donut.shares)
    plain = count - (donut.other is not None)
    palette = series_colours(chart.palette, max(plain, donut.palette_size), ordered=donut.ordered)
    colours = [palette[index] for index in donut.colour_index]
    if donut.other is not None:
        colours.insert(donut.other, _other())
    wedges, _ = ax.pie(
        donut.shares,
        colors=colours,
        startangle=90,
        counterclock=False,
        radius=1.0,
        wedgeprops={"width": RING, "edgecolor": "white", "linewidth": 1.5},
    )
    for wedge, name in zip(wedges, donut.names, strict=True):
        wedge.set_label(name)
    # Round whatever the plot's shape: the limits give way, not the plot's box,
    # so a legend beside it stays where the layout put it.
    # (pie() fixes both limits, which the aspect could then not move.)
    ax.set_aspect("equal", adjustable="datalim")
    ax.set_autoscale_on(True)
    ax.update_datalim([(-DONUT_REACH[0], -DONUT_REACH[1]), DONUT_REACH])
    ax.margins(0.0)
    ax.autoscale_view()
    figure_pt = chart.figsize[0] * 72.0
    ax.set_title(wrap(donut.title, chars_in(figure_pt - 60.0, font_size("axes.titlesize"))))
    names = [wrap(name, 24) for name in donut.names]
    title = wrap(donut.legend_title, 24)
    # Beside the donut when the figure is wide enough and the legend no
    # taller than the plot can be (its lines at 10 pt, the title's and the
    # notes' room taken off the figure's height); under it otherwise.
    lines = sum(name.count("\n") + 1 for name in [*names, title])
    legend_pt = lines * 12.0 + len(names) * 5.0 + 10.0
    width = chars_in(figure_pt - 14.0, FOOTNOTE_SIZE)
    notes_pt = sum(wrap(note, width).count("\n") + 1 for note in donut.notes) * FOOTNOTE_SIZE * 1.3
    room_pt = chart.figsize[1] * 72.0 - 50.0 - notes_pt
    below = None
    if figure_pt >= 7.5 * 72.0 and legend_pt <= room_pt:
        ax.legend(
            wedges,
            names,
            title=title,
            loc="center left",
            bbox_to_anchor=(1.0, 0.5),
            frameon=False,
            fontsize=10,
            title_fontsize=10,
        )
    else:
        below = legend_below(fig, list(wedges), donut.names, donut.legend_title, figure_pt)
    # A donut is read by its slices: more than a bar chart's least plot.
    footnote = Footnote(
        fig, donut.notes, legend=below, axes=ax, least=0.55 * chart.figsize[1] * 72.0
    )
    footnote.apply()
    scale = _place_donut(ax)
    _centre(ax, donut, scale)
    if chart.show_values:
        _slice_labels(ax, wedges, donut.shares, colours, scale)


def _place_donut(ax: Any) -> float:
    """Fix the limits of the laid-out plot so the donut is round and, with a
    legend beside it, the donut and the legend sit together in the middle of
    their room rather than a wide figure's width apart. Returns the points
    per unit of the radius."""

    fig = ax.figure
    renderer = fig.canvas.get_renderer()
    points = 72.0 / fig.dpi
    box = ax.get_window_extent(renderer)
    width_pt, height_pt = box.width * points, box.height * points
    # The reach asked for fits the plot's tighter side.
    scale = min(width_pt / (2 * DONUT_REACH[0]), height_pt / (2 * DONUT_REACH[1]))
    donut_pt = 2 * DONUT_REACH[0] * scale
    left = (width_pt - donut_pt) / 2.0  # the donut's left edge, from the plot's
    side = ax.get_legend()
    if side is not None:  # beside the plot, where the layout made room for it
        legend_pt = side.get_window_extent(renderer).width * points
        left = max(0.0, (width_pt + legend_pt - donut_pt - legend_pt) / 2.0)
        side.set_bbox_to_anchor((min(1.0, (left + donut_pt) / width_pt), 0.5), ax.transAxes)
    low = -(left / scale + DONUT_REACH[0])
    ax.set_autoscale_on(False)
    ax.set_xlim(low, low + width_pt / scale)
    ax.set_ylim(-height_pt / scale / 2.0, height_pt / scale / 2.0)
    return scale


#: How far the plot reaches from the centre, across and up, in radii: room
#: beside the ring for the percentages of thin slices.
DONUT_REACH = (1.5, 1.25)


def _centre(ax: Any, donut: Donut, scale: float) -> None:
    """The base in the hole: the respondents, and the sum of their weights."""

    hole_pt = 2.0 * (1.0 - RING) * scale * 0.75  # the widest line's room
    number = f"{donut.respondents:,}"
    size = max(8.0, min(22.0, hole_pt / max(len(number), 3) / (CHAR_WIDTH * 1.1)))
    small = max(7.0, min(10.0, hole_pt / len("respondents") / CHAR_WIDTH))
    lines = [(number, size, "bold"), ("respondents", small, "normal")]
    if donut.weighted_base is not None:
        weighted = f"weighted {count_text(donut.weighted_base)}"
        lines.append(
            (weighted, max(6.5, min(small, hole_pt / len(weighted) / CHAR_WIDTH)), "normal")
        )
    total = sum(line_size * 1.2 for _, line_size, _ in lines)
    y = total / 2.0
    for text, line_size, weight in lines:
        y -= line_size * 1.2 / 2.0
        ax.text(
            0.0,
            y / scale,
            text,
            ha="center",
            va="center",
            fontsize=line_size,
            fontweight=weight,
            color=_ink(DONUT_INK),
        )
        y -= line_size * 1.2 / 2.0


def _slice_labels(
    ax: Any, wedges: list[Any], shares: np.ndarray, colours: list[Any], scale: float
) -> None:
    """Each slice's percentage on the ring where it fits; else in a column
    beside the ring, on the slice's side, joined to it by a line that leaves
    the ring outwards first — the labels of a side a line apart, so none
    covers another."""

    size = VALUE_SIZE
    middle = 1.0 - RING / 2.0
    ring_pt = RING * scale
    outside: list[tuple[float, str]] = []  # the slice's middle angle, its text
    for wedge, share, colour in zip(wedges, shares, colours, strict=True):
        text = f"{share:.1f}%"
        angle = math.radians((wedge.theta1 + wedge.theta2) / 2.0)
        arc_pt = math.radians(wedge.theta2 - wedge.theta1) * middle * scale
        # The text's box, level, measured along the ring's radius and across
        # it where it would sit: it must fit inside the slice both ways.
        across, along = abs(math.cos(angle)), abs(math.sin(angle))
        width, height = text_width(text, size), size * 1.2
        radial = across * width + along * height
        tangential = along * width + across * height
        if radial + 4.0 <= ring_pt and tangential + 4.0 <= arc_pt:
            ax.text(
                middle * math.cos(angle),
                middle * math.sin(angle),
                text,
                ha="center",
                va="center",
                fontsize=size,
                color=ink_on(colour),
            )
        else:
            outside.append((angle, text))
    step = size * 1.35 / scale  # a line apart, in radii
    elbow, column = 1.08, 1.2
    top = DONUT_REACH[1] - step / 2.0
    for right in (True, False):
        labels = sorted(
            (label for label in outside if (math.cos(label[0]) >= 0) == right),
            key=lambda label: -math.sin(label[0]),
        )
        ys = [min(top, elbow * math.sin(angle)) for angle, _ in labels]
        for index in range(1, len(ys)):  # downwards, a line apart
            ys[index] = min(ys[index], ys[index - 1] - step)
        if ys and ys[-1] < -top:  # past the bottom: the side up again
            ys[-1] = -top
            for index in range(len(ys) - 2, -1, -1):
                ys[index] = max(ys[index], ys[index + 1] + step)
        x = column if right else -column
        for (angle, text), y in zip(labels, ys, strict=True):
            out = (math.cos(angle), math.sin(angle))
            bend = (elbow * out[0], elbow * out[1])
            ax.plot(
                [out[0], bend[0], x],
                [out[1], bend[1], y],
                color=chart_theme.muted(LEADER),
                linewidth=0.7,
                solid_capstyle="round",
            )
            ax.text(
                x + (0.03 if right else -0.03),
                y,
                text,
                ha="left" if right else "right",
                va="center",
                fontsize=size,
                color=_ink(DONUT_INK),
            )


__all__ = [
    "CORRECTIONS",
    "LAYOUTS",
    "SHOWS",
    "SORTS",
    "Bars",
    "Donut",
    "Histogram",
    "draw",
    "histogram_edges",
    "is_classic",
    "parse_bins",
    "render",
    "render_donut",
    "render_histogram",
    "value_text",
]
