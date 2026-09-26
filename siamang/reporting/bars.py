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

Everything this module draws says under the plot what a table says under
itself: the base, the weight, and the codebook's missing codes, which it leaves
out of the bars — a 99 "Don't know" is not an answer — and counts. A
multiple-choice question, which the older chart could not draw at all, is
drawn here whatever the parameters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

from siamang.reporting.chart_parts import (
    CHAR_WIDTH,
    VALUE_SIZE,
    Footnote,
    axes_points,
    chars_in,
    code_order,
    code_text,
    count_text,
    font_size,
    ink_on,
    left_out_note,
    percent_axis,
    row_major,
    series_colours,
    text_width,
    thousands_axis,
    wrap,
)

if TYPE_CHECKING:
    from siamang.data.survey_data import SurveyData
    from siamang.reporting.charts import BarChart

SHOWS = ("count", "percent")
LAYOUTS = ("grouped", "stacked", "stacked_100")
SORTS = ("code", "value")


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
    #: Each series' place in code order: its colour follows the answer, not the
    #: rank a sort gave it.
    colour_index: list[int] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    #: The value axis's title when ``value_label`` would not fit on one line
    #: along it (a split by a question: its notes name the variable).
    short_value_label: str = ""


def is_classic(chart: BarChart) -> bool:
    """Whether ``chart`` is the one BarChart has always drawn: the newer
    parameters at their defaults, and no multiple-choice column (which that
    chart could not draw — it raised ``unhashable type: 'list'``)."""

    from siamang.data import multi

    if chart.show != "count" or chart.split is not None or chart.sort != "code":
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
    weights = _weights(data)
    if chart.by:
        bars = _means(chart, frame, weights)
    elif chart.split:
        bars = _split(chart, frame, weights)
    else:
        bars = _distribution(chart, frame, weights)
    if weights is not None:
        chart._weighted()
        bars.notes.append(f"Weighted by '{data.weight}'; n counts respondents.")
    note = left_out_note(left_out, data.variables)
    if note:
        bars.notes.append(note)
    render(chart, bars)


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


def _distribution(chart: BarChart, frame: pd.DataFrame, weights: np.ndarray | None) -> Bars:
    from siamang.data import multi

    data, name = chart.data, chart.column
    series = frame[name]
    weight = weights if weights is not None else np.ones(len(series))
    label = _label(data, name)
    is_multi = multi.is_multi(series)
    answered = _answered(series, is_multi)
    codes = (
        _multi_codes(data, name, series)
        if is_multi
        else _single_codes(data, name, series[answered])
    )
    counts = np.array([weight[_chose(series, code, is_multi) & answered].sum() for code in codes])
    base = float(weight[answered].sum())
    percent = chart.show == "percent"
    values = counts / base * 100.0 if percent and base > 0 else counts
    if percent and base <= 0:
        values = np.zeros(len(codes))
    order = _order(values, chart.sort)
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
    return Bars(
        values=values[order].reshape(-1, 1),
        positions=[_name_of(data, name, codes[i]) for i in order],
        series=[label],
        kind="percent" if percent else "count",
        value_label=axis,
        position_label="",  # the title names the variable
        title=chart.title or label,
        notes=notes,
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
    counts = np.zeros((len(group_codes), len(codes)))
    sizes, bases = [], np.zeros(len(group_codes))
    for row, group in enumerate(group_codes):
        member = answered & (groups == group).to_numpy(dtype=bool)
        sizes.append(int(member.sum()))
        bases[row] = weight[member].sum()
        for column, hits in enumerate(chose):
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
        order = list(range(len(codes)))
        key = values[:, -1] if percent else counts.sum(axis=1)
        groups_order = _order(key, "value")
    else:
        order = _order(counts.sum(axis=0), chart.sort)
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
        top = _name_of(data, name, codes[-1])
        notes.append(
            f"Groups in order of their share of {top}; the answers keep the scale's order."
            if percent
            else "Groups largest first; the answers keep the scale's order."
        )
    return Bars(
        values=values[groups_order][:, order],
        positions=[
            f"{_name_of(data, by, group_codes[index])}\n(n = {sizes[index]:,})"
            for index in groups_order
        ],
        series=[_name_of(data, name, codes[i]) for i in order],
        kind="percent" if percent else "count",
        value_label=axis,
        position_label=by_label,
        title=chart.title or f"{label} by {by_label}",
        legend_title=label,
        stacked=chart.layout != "grouped",
        full=chart.layout == "stacked_100",
        ordered=_is_scale(data, name),
        colour_index=order,
        notes=notes,
        short_value_label=short,
    )


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
    means, names = [], []
    for code in codes:
        member = _chose(groups, code, is_multi) & answered
        if not member.any():
            continue  # a group nobody is in has no mean
        total = float(weight[member].sum())
        means.append(
            float((weight[member] * values[member]).sum() / total) if total > 0 else np.nan
        )
        names.append(f"{_name_of(data, by, code)}\n(n = {int(member.sum()):,})")
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
    return Bars(
        values=means_array[order].reshape(-1, 1),
        positions=[names[i] for i in order],
        series=[label],
        kind="mean",
        value_label=("Weighted mean " if weighted else "Mean ") + label,
        position_label=by_label,
        title=chart.title or f"Mean {label} by {by_label}",
        notes=notes,
    )


# ─── drawing ─────────────────────────────────────────────────────────────────


def value_text(value: float, kind: str) -> str:
    """A bar's value as it is written on the chart."""

    if kind == "percent":
        return f"{value:.1f}%"
    if kind == "mean":
        return f"{value:.2f}"
    return count_text(value)


#: A label turned under a vertical bar is at most this many characters a line:
#: longer ones would take the figure's height, and the bars are drawn across.
TURNED_WIDTH = 40


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
        turned = [wrap(text, width) for text in flat]
        if all(text.count("\n") < lines for text in turned):
            return turned, 45, size
    return None


def _crowded(labels: list[Any], renderer: Any, horizontal: bool) -> bool:
    """Whether two neighbouring tick labels overlap."""

    boxes = [label.get_window_extent(renderer) for label in labels if label.get_text()]
    if horizontal:
        boxes.sort(key=lambda box: box.y0)
        return any(low.y1 > high.y0 + 0.5 for low, high in zip(boxes, boxes[1:], strict=False))
    boxes.sort(key=lambda box: box.x0)
    return any(left.x1 > right.x0 + 0.5 for left, right in zip(boxes, boxes[1:], strict=False))


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


def render(chart: BarChart, bars: Bars) -> None:
    """Draw ``bars`` on a new figure of ``chart``."""

    import matplotlib.pyplot as plt
    import seaborn as sns

    sns.set_theme(style="whitegrid", palette=chart.palette)
    values = bars.values
    positions, count = values.shape
    figure_pt = chart.figsize[0] * 72.0
    # Beside the plot when the figure is wide enough, else under it.
    legend_beside = count > 1 and figure_pt >= 7.5 * 72.0
    legend_pt = min(0.3 * figure_pt, 11.0 * 0.6 * 24 + 40.0) if legend_beside else 0.0
    horizontal = chart.horizontal
    placed = None
    if not horizontal:
        placed = _tick_labels(bars.positions, (0.85 * figure_pt - legend_pt) / max(positions, 1))
        # Labels that cannot be read under the bars go beside them.
        horizontal = placed is None

    fig, ax = plt.subplots(figsize=chart.figsize)
    chart._fig, chart._ax = fig, ax
    palette = series_colours(chart.palette, count, ordered=bars.ordered)
    colours = [palette[index] for index in (bars.colour_index or range(count))]
    at = np.arange(positions, dtype=float)
    if bars.stacked or count == 1:
        thickness, offsets = 0.7, [0.0] * count
    else:
        thickness = 0.8 / count
        offsets = [-0.4 + thickness * (index + 0.5) for index in range(count)]
    base = np.zeros(positions)
    for index in range(count):
        heights = values[:, index]
        style = {
            "color": colours[index],
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

    value_axis, position_axis = (ax.xaxis, ax.yaxis) if horizontal else (ax.yaxis, ax.xaxis)
    if bars.kind == "percent":
        percent_axis(value_axis)
    elif bars.kind == "count":
        thousands_axis(value_axis)
    if bars.full:
        (ax.set_xlim if horizontal else ax.set_ylim)(0, 100)
    ax.grid(False)
    ax.grid(True, axis="x" if horizontal else "y", color="0.88", linewidth=0.8)
    ax.set_axisbelow(True)
    position_axis.set_ticks(at)
    if horizontal:
        ax.set_yticklabels(
            [_group_label(text, chars_in(0.28 * figure_pt, 11.0)) for text in bars.positions]
        )
        ax.set_ylim(positions - 0.5, -0.5)  # the first answer on top
    else:
        labels, rotation, size = placed  # type: ignore[misc]
        ax.set_xticklabels(
            labels,
            fontsize=size,
            rotation=rotation,
            ha="right" if rotation else "center",
            rotation_mode="anchor" if rotation else "default",
        )
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
            below = _legend_below(fig, handles, names, bars.legend_title, figure_pt)

    footnote = Footnote(fig, bars.notes, legend=below, axes=ax)
    footnote.apply()
    side = ax.get_legend()
    if side is not None:
        renderer = fig.canvas.get_renderer()
        if side.get_window_extent(renderer).height > ax.get_window_extent(renderer).height + 1:
            # Taller than the plot, it would run over the notes: under the plot.
            handles, names = ax.get_legend_handles_labels()
            side.remove()
            footnote.legend = _legend_below(fig, handles, names, bars.legend_title, figure_pt)
            footnote.apply()
    if horizontal:
        _fit_across(ax, footnote, bars.positions, figure_pt)
    for _ in range(2):  # wrapped to the plot as it is laid out
        _axis_titles(ax, bars, horizontal, title)
        footnote.apply()
    if chart.show_values:
        _write_values(ax, bars, colours, thickness, offsets, horizontal)
        footnote.apply()


def _legend_below(
    fig: Any, handles: list[Any], names: list[str], title: str, figure_pt: float
) -> Any:
    """A figure legend between the plot and the notes, in as many columns as
    the figure's width holds, read row by row."""

    names = [wrap(name, 18) for name in names]
    entry_pt = max(text_width(name, 9.0) for name in names) + 30.0
    columns = max(1, min(len(names), int((figure_pt - 20.0) // entry_pt)))
    return fig.legend(
        row_major(handles, columns),
        row_major(names, columns),
        title=wrap(title, chars_in(figure_pt - 20.0, 9.0)),
        loc="lower center",
        ncol=columns,
        frameon=False,
        fontsize=9,
        title_fontsize=9,
    )


def _write_values(
    ax: Any,
    bars: Bars,
    colours: list[Any],
    thickness: float,
    offsets: list[float],
    horizontal: bool,
) -> None:
    """Each bar's value where it fits: beside its end, or inside its segment of a
    stack. A value that would not fit is left to the axis, never cut off."""

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
        if bars.full or bars.kind != "count":
            return
        tips = [(position, 0.0, base[position]) for position in range(positions)]
        kind_values = [value_text(total, bars.kind) for total in base]
    else:
        tips, kind_values = [], []
        for index in range(count):
            for position in range(positions):
                value = values[position, index]
                if value != value:
                    continue
                tips.append((position, offsets[index], value))
                kind_values.append(value_text(value, bars.kind))
    if not tips:
        return
    widest = max(text_width(text, size) for text in kind_values)
    rotation = 0
    if horizontal:
        if band_pt < size * 0.9:
            return
    elif band_pt < widest + 2:
        if band_pt < size * 1.15:  # turned values of neighbouring bars would touch
            return
        rotation = 90
    extent_pt = (widest if horizontal or rotation else size) + 6.0
    for (position, offset, value), text in zip(tips, kind_values, strict=True):
        sign = 1.0 if value >= 0 else -1.0
        if horizontal:
            ax.annotate(
                text,
                (value, position + offset),
                xytext=(3 * sign, 0),
                textcoords="offset points",
                ha="left" if sign > 0 else "right",
                va="center",
                fontsize=size,
            )
        else:
            ax.annotate(
                text,
                (position + offset, value),
                xytext=(0, 3 * sign),
                textcoords="offset points",
                ha="center",
                va="bottom" if sign > 0 else "top",
                rotation=rotation,
                fontsize=size,
            )
    # Room beyond the longest bar for its value.
    room = extent_pt / along_pt * span * 1.15
    tops = [value for _, _, value in tips]
    new_high = max(high, max(tops) + room)
    new_low = min(low, min(tops) - room) if min(tops) < 0 else low
    (ax.set_xlim if horizontal else ax.set_ylim)(new_low, new_high)


__all__ = ["LAYOUTS", "SHOWS", "SORTS", "Bars", "draw", "is_classic", "render", "value_text"]
