"""The Vega-Lite specs of the Result charts, from the numbers their pictures
were drawn from.

A Result chart (:mod:`siamang.reporting.result_charts`) draws an analysis's
result with a few shared forms — rows of estimates with their intervals
(``_dots``), rows of bars (``_bars``), a scree plot, a heatmap of loadings —
and a handful of its own (a proportion's interval, TURF's reach curve, the
stacks of the Net Promoter Score and of sentiment). Each form records what it
drew while it draws (``SurveyChart._drawn``, as the charts of the data do in
:mod:`siamang.reporting.chart_specs`); once the renderer is done,
:func:`finish` adds what the chart as a whole says — its title, the weight
line, the axis titles and the notes under the plot — read off the figure
before it is laid out. The analyses that draw their own figure (Key drivers,
the Perceptual map, Price sensitivity; :mod:`siamang.reporting.method_charts`)
record their result's numbers as that figure draws them.

What a spec holds is what the picture shows: estimates, intervals, shares,
eigenvalues, loadings, coefficients, curves and the base of each — never a
respondent's row (no Result chart plots respondents).
"""

from __future__ import annotations

import dataclasses
import math
import re
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from siamang.reporting import vega
from siamang.reporting.chart_specs import (
    VALUE_SIZE,
    VIEW,
    ZOOM_HINT,
    DrawnMatrix,
    _figure_px,
    _height,
    _ink_encoding,
    _legend,
    _text_px,
    _zoom,
    matrix_spec,
    recording,
)

# ─── what every Result chart says ────────────────────────────────────────────


@dataclass(kw_only=True)
class DrawnResult:
    """What a Result chart drew, the chart's own part: :func:`finish` fills it
    in from the figure once the renderer is done."""

    heading: str = ""
    subtitle: list[str] | None = None
    notes: list[str] = field(default_factory=list)
    x_title: str | None = None
    y_title: str | None = None
    #: The base of the whole chart, as a tooltip writes it (a row that says
    #: its own, "North (n = 97)", gives that).
    base: str | None = None
    #: The value axis's limits as drawn, before room was made for the labels.
    limits: tuple[float, float] | None = None
    #: The value axis: ``x`` (rows across) or ``y`` (a curve up).
    along: str = "x"
    #: The axes whose titles and limits are the chart's; let go once read.
    axes: Any = field(default=None, repr=False)
    #: A figure an analysis drew whole: its title lines are its own.
    adopted: bool = False

    def spec(self, chart: Any) -> dict[str, Any]:  # pragma: no cover - each form has its own
        raise NotImplementedError

    def _finish(
        self,
        chart: Any,
        main: dict[str, Any],
        description: str,
        notes: list[str] | None = None,
    ) -> dict[str, Any]:
        return vega.finish(
            chart,
            main,
            heading=self.heading,
            subtitle=_subtitle(self.subtitle),
            notes=list(self.notes) if notes is None else notes,
            description=description,
            kind=getattr(chart, "drawn", "") or "result",
        )


#: The characters of a subtitle's line: a phone's width holds it.
SUBTITLE_CHARS = 44


def _subtitle(lines: list[str] | None) -> list[str] | None:
    """The subtitle's lines (the weight, what an analysis's figure says under
    its title) in lines a narrow chart holds: a subtitle is not wrapped to
    the width drawn at, and a longer line took the plot's room."""

    if not lines:
        return None
    out: list[str] = []
    for line in lines:
        # Parted where the line is (after a dash or a comma), else between words.
        chunks = re.split(r"(?<=,) |(?<= —) ", _one_line(line))
        current = ""
        for chunk in chunks:
            joined = f"{current} {chunk}" if current else chunk
            if len(joined) <= SUBTITLE_CHARS:
                current = joined
                continue
            if current:
                out.append(current)
            parts = vega.wrap(chunk, SUBTITLE_CHARS)
            out += parts[:-1]
            current = parts[-1]
        if current:
            out.append(current)
    return out


def _one_line(text: Any) -> str:
    return " ".join(str(text or "").split())


def count_base(value: Any) -> str | None:
    """A base given as a count — of respondents, or their weight — as a
    tooltip writes it."""

    number = vega.number(value)
    if number is None:
        return None
    if float(number).is_integer():
        return vega.base_text(int(number))
    return f"{number:,.1f} (weighted)"


def _base_of(stats: dict[str, Any]) -> str | None:
    """The chart's base from its result's statistics: the respondents
    counted (N), or the base a choice model states ("160 respondents")."""

    for key in ("N", "n", "N valid"):
        value = stats.get(key)
        if isinstance(value, int | np.integer) and not isinstance(value, bool):
            return vega.base_text(int(value))
    base = stats.get("Base")
    if isinstance(base, str) and "respondent" in base:
        return base
    return None


@recording
def finish(chart: Any, title: str) -> None:
    """Complete the record of the Result chart just drawn (``chart._drawn``):
    its title (the one given, else the renderer's) with the weight line under
    it, its axis titles, the value axis's limits and the notes under its plot,
    read off the figure before the chart lays it out and wraps them."""

    drawn = chart._drawn
    if not isinstance(drawn, DrawnResult):
        return
    if not drawn.adopted:
        drawn.heading = _one_line(chart.title or title)
        drawn.subtitle = [chart._weight_note] if chart._weight_note else None
        ax = drawn.axes if drawn.axes is not None else chart._ax
        drawn.x_title = drawn.x_title or _one_line(ax.get_xlabel()) or None
        drawn.y_title = drawn.y_title or _one_line(ax.get_ylabel()) or None
        if drawn.limits is None:
            limits = ax.get_xlim() if drawn.along == "x" else ax.get_ylim()
            drawn.limits = (float(min(limits)), float(max(limits)))
        drawn.notes = drawn.notes or [
            _one_line(note._siamang_note)
            for axes in chart._fig.axes
            for note in axes.texts
            if getattr(note, "_siamang_note", None)
        ]
    if drawn.base is None:
        drawn.base = _base_of(chart.stats)
    drawn.axes = None


@recording
def note(chart: Any, **fields: Any) -> None:
    """Add ``fields`` to the record of the chart being drawn — what a renderer
    draws after a shared form (a log scale, the lines of a profile)."""

    drawn = chart._drawn
    if isinstance(drawn, DrawnResult):
        for name, value in fields.items():
            setattr(drawn, name, value)


# ─── labels and numbers ──────────────────────────────────────────────────────

_WITH_BASE = re.compile(r"^(.*?)\s*\(n = ([^)]*)\)$", re.DOTALL)
_NUMBER = re.compile(r"^\s*([−-]?[\d,]*\.?\d+)")


def _row_label(label: str, width: int = 26) -> str:
    """A row's label in lines of ``width`` characters, its "(n = 97)" on a
    line of its own."""

    text = _one_line(label)
    found = _WITH_BASE.match(text)
    head, tail = (found.group(1), f"(n = {found.group(2)})") if found else (text, "")
    lines = vega.wrap(head, width) if head else []
    if tail:
        lines.append(tail)
    return "\n".join(lines or [""])


def _plain(label: str) -> str:
    """A row's name without its base: "North (n = 97)" is "North"."""

    text = _one_line(label)
    found = _WITH_BASE.match(text)
    return found.group(1) if found else text


def _base_in(*labels: Any) -> str | None:
    """The base a label states — "North (n = 97)" is 97 respondents."""

    for label in labels:
        text = _one_line(label or "")
        # "North (n = 97)", or a panel's row that is its base alone, "n = 300".
        found = _WITH_BASE.match(text) or re.fullmatch(r"()n = ([\d,–]+)", text)
        if found:
            count = found.group(2)
            return f"{count} {'respondent' if count == '1' else 'respondents'}"
    return None


def _decimals(texts: list[str], default: int = 2) -> int:
    """The decimals the picture writes its values with, read off its labels."""

    for text in texts:
        found = _NUMBER.match(str(text or ""))
        if found:
            number = found.group(1)
            return len(number.split(".")[1]) if "." in number else 0
    return default


def _percent_texts(texts: list[str]) -> bool:
    return any(re.match(r"^\s*[−-]?[\d,.]+ %", str(text or "")) for text in texts)


def _amount(value: float | None, digits: int, percent: bool = False) -> str:
    if value is None:
        return ""
    text = f"{value:,.{digits}f}"
    if text.startswith("-") and float(text.replace(",", "")) == 0:
        text = text[1:]
    return text + (" %" if percent else "")


def _value_title(axis: str | None, default: str = "Value") -> str:
    """What a value is called in a tooltip, from the axis's title: "Mean with
    its 95 % confidence interval" is a Mean."""

    if not axis:
        return default
    return re.split(r" with its |, ± 1 SD|, against ", axis)[0].strip() or default


def _interval_title(axis: str | None) -> str:
    """What an interval is called in a tooltip, from the axis's title."""

    axis = axis or ""
    if "± 1 SD" in axis:
        return "± 1 SD"
    found = re.search(r"(\d+(?:\.\d+)?) ?% confidence interval", axis)
    return f"{found.group(1)}% confidence interval" if found else "Interval"


def _note_in(text: str, letters: str = "") -> str:
    """What a value's label says besides the value — "(reference)", "(one
    answer: no SD)" — or nothing."""

    rest = _NUMBER.sub("", str(text or ""), count=1).strip()
    if letters and rest.endswith(letters):
        rest = rest[: -len(letters)].strip()
    rest = rest.removeprefix("%").strip()
    return rest.strip("()") if re.search(r"[A-Za-z]", rest) else ""


def _log_ticks(low: float, high: float) -> list[float]:
    """Ticks of a log axis as numbers are read: 0.5, 1, 2, 5 — or, on a
    narrow range, 0.8, 0.9, 1, 1.2."""

    inside: list[float] = []
    for mantissas in (
        (1.0, 2.0, 5.0),
        (1.0, 1.5, 2.0, 3.0, 5.0, 7.0),
        (1.0, 1.2, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0),
        tuple(1.0 + step / 10.0 for step in range(90)),
    ):
        ticks = sorted(
            {round(m * 10.0**exponent, 6) for exponent in range(-4, 5) for m in mantissas}
        )
        inside = [tick for tick in ticks if low <= tick <= high]
        if len(inside) >= 3:
            break
    if len(inside) > 9:
        inside = inside[:: math.ceil(len(inside) / 9)]
    return inside


def _room(limits: tuple[float, float], texts: list[str], chart: Any, *, log: bool = False) -> float:
    """The high end of a value axis with room for the widest label past it,
    at the width a report draws the chart; a narrower chart is laid out to
    hold its labels all the same (the drawing is fitted to its marks)."""

    low, high = limits
    widest = max((_text_px(text) for text in texts if text), default=0.0)
    if widest <= 0:
        return high
    plot = max(240.0, _figure_px(chart)[0] * 0.62)
    share = min(0.6, (widest + 8.0) / plot)
    if log and low > 0 and high > 0:
        span = math.log10(high) - math.log10(low)
        return float(10 ** (math.log10(high) + span * share / (1 - share)))
    return float(high + (high - low) * share / (1 - share))


#: The width of a chart's container (pixels) below which its row labels are
#: written in narrower lines, leaving the plot room (a phone, a dashboard tile).
NARROW = 520
#: The characters of a row label's line, wide and narrow.
ROW_CHARS, NARROW_ROW_CHARS = 26, 14
#: The characters of an axis title's line: one under a narrow plot fits it.
AXIS_CHARS = 40


def _row_axis(axis_labels: list[str], labels: list[str]) -> dict[str, Any]:
    """The axis of a chart's rows: each label in lines of
    :data:`ROW_CHARS`, or of :data:`NARROW_ROW_CHARS` in a narrow container."""

    narrow = {
        axis: _row_label(label, NARROW_ROW_CHARS).split("\n")
        for axis, label in zip(axis_labels, labels, strict=True)
    }
    return {
        "title": None,
        "labelExpr": f"containerSize()[0] < {NARROW} ? {vega.script_json(narrow)}[datum.label]"
        " : split(datum.label, '\\n')",
        "labelLimit": {"expr": f"containerSize()[0] < {NARROW} ? 110 : 200"},
        "labelAlign": "right",
        "ticks": False,
        "grid": False,
        "domain": False,
        "labelPadding": 6,
    }


def _row_height(
    chart: Any, labels: list[str], per_row: int = 1, *, least: float | None = None
) -> float:
    """The plot's height for a row per label, as tall as a row's label in its
    narrow lines and as its series need."""

    lines = max(
        (
            max(_row_label(label).count("\n"), _row_label(label, NARROW_ROW_CHARS).count("\n")) + 1
            for label in labels
        ),
        default=1,
    )
    pitch = max(28.0, lines * 13.0 + 10.0, per_row * 13.0 + 10.0)
    low = _height(chart, 120.0, 240.0) if least is None else least
    return float(max(low, len(labels) * pitch))


def _axis_title(text: str | None) -> str | list[str] | None:
    """An axis title in lines a narrow plot holds, as even as they can be
    (a list of them); a number and its unit ("95 %") are not parted."""

    if not text:
        return None
    text = re.sub(r"(\d) %", "\\1\u00a0%", _one_line(text))
    if len(text) <= AXIS_CHARS:
        return text
    count = math.ceil(len(text) / AXIS_CHARS)
    width = math.ceil(len(text) / count) + 2
    lines = vega.wrap(text, width)
    while len(lines) > count and width < AXIS_CHARS:
        width += 2
        lines = vega.wrap(text, width)
    return lines


def _legend_of(title: str | None, labels: list[str]) -> dict[str, Any]:
    """A legend over the plot whose entries may be long ("Random data, 95th
    percentile (parallel analysis)"): each as wide as the chart holds."""

    legend = _legend(title, labels)
    longest = max((len(str(label)) for label in labels), default=8)
    entry = min(360.0, longest * 6.4) + 30.0
    legend["columns"] = {"expr": f"max(1, min({len(labels)}, floor(width / {entry:.0f})))"}
    legend["labelLimit"] = {"expr": "max(80, min(360, width - 40))"}
    return legend


def _ticks() -> dict[str, Any]:
    """As many ticks on a value axis as its width reads easily."""

    return {"tickCount": {"expr": "max(3, ceil(width / 80))"}}


# ─── rows of estimates with their intervals (``_dots``) ─────────────────────


@dataclass(kw_only=True)
class DrawnDots(DrawnResult):
    """Rows of estimates with their intervals: a series per group, each a
    point, a line from its lower to its upper end and its value beside."""

    labels: list[str]
    #: Each: ``label`` (None for one series), ``colour``, ``estimate``,
    #: ``lower``, ``upper`` and ``text`` (the label drawn beside each point).
    series: list[dict[str, Any]]
    reference: float | None = None
    legend_title: str | None = None
    dodge: bool = True
    #: A profile: each series a line down the rows (a cluster's snake plot).
    lines: bool = False
    log: bool = False
    #: Each row's significance letters (Group means with a post-hoc test).
    letters: list[str] | None = None
    #: A panel per variable, each on a scale of its own (Descriptive
    #: statistics of an income and an age): (title, labels, series, limits).
    panels: list[tuple[str, list[str], list[dict[str, Any]], tuple[float, float]]] | None = None

    def spec(self, chart: Any) -> dict[str, Any]:
        return dots_spec(chart, self)


@recording
def record_dots(
    chart: Any,
    ax: Any,
    labels: list[Any],
    series: list[dict[str, Any]],
    *,
    reference: float | None,
    legend_title: str | None,
    dodge: bool,
) -> None:
    chart._drawn = DrawnDots(
        labels=[str(label) for label in labels],
        series=[_series(item) for item in series],
        reference=None if reference is None else float(reference),
        legend_title=legend_title,
        dodge=dodge,
        axes=ax,
    )


def _series(item: dict[str, Any]) -> dict[str, Any]:
    def numbers(values: Any) -> list[float | None]:
        return [vega.number(value) for value in np.asarray(values, dtype=float).tolist()]

    return {
        "label": None if item.get("label") is None else str(item["label"]),
        "colour": vega.hex_colour(item["color"]),
        "estimate": numbers(item["estimate"]),
        "lower": numbers(item["lower"]),
        "upper": numbers(item["upper"]),
        "text": [str(text) for text in item["text"]],
    }


@recording
def record_panels(
    chart: Any,
    axes: Any,
    panels: list[tuple[str, list[str], list[dict[str, Any]], Any]],
    legend_title: str | None,
) -> None:
    """Descriptive statistics drawn a panel per variable: each panel's title,
    rows, series and limits as drawn."""

    chart._drawn = DrawnDots(
        labels=[],
        series=[],
        legend_title=legend_title,
        axes=axes,
        panels=[
            (
                str(title),
                [str(label) for label in labels],
                [_series(item) for item in series],
                (float(min(ax.get_xlim())), float(max(ax.get_xlim()))),
            )
            for title, labels, series, ax in panels
        ],
    )


def _dot_rows(
    drawn: DrawnDots, labels: list[str], series: list[dict[str, Any]], axis_labels: list[str]
) -> list[dict[str, Any]]:
    texts = [text for item in series for text in item["text"]]
    digits = _decimals(texts)
    percent = _percent_texts(texts)
    rows = []
    for item in series:
        for index, label in enumerate(labels):
            estimate = item["estimate"][index]
            lower, upper = item["lower"][index], item["upper"][index]
            letters = drawn.letters[index] if drawn.letters and index < len(drawn.letters) else ""
            text = item["text"][index] if index < len(item["text"]) else ""
            name = _plain(label)
            row: dict[str, Any] = {
                "row": axis_labels[index],
                "name": name,
                "series": _plain(item["label"]) if item["label"] else "",
                "entry": item["label"] or "",
                # The same, for the lines' stroke: a field of its own keeps the
                # lines' colors out of the points' legend (the one a click
                # toggles), which one legend of both could not be.
                "stroke_entry": item["label"] or "",
                "index": index,
                "estimate": estimate,
                "lower": lower,
                "upper": upper,
                "value": _amount(estimate, digits, percent) if estimate is not None else "none",
                "interval": (
                    f"{_amount(lower, digits, percent)} to {_amount(upper, digits, percent)}"
                    if lower is not None and upper is not None
                    else "none"
                ),
                "label_text": text,
                "tip": upper if upper is not None else estimate,
                "base": _base_in(label, item["label"]) or drawn.base or "",
                "note": _note_in(text, letters),
                "letters": letters,
                "colour": item["colour"],
            }
            where = f"{name}, {row['series']}" if row["series"] else name
            row["description"] = f"{where}: {row['value']}" + (
                f" ({row['interval']})" if row["interval"] != "none" else ""
            )
            rows.append(row)
    return rows


def _dot_view(
    chart: Any,
    drawn: DrawnDots,
    labels: list[str],
    series: list[dict[str, Any]],
    limits: tuple[float, float],
    *,
    name: str = VIEW,
    title: str | None = None,
    x_title: str | None = None,
    least: float | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    look = vega.look_of(chart)
    axis_labels = vega.unique([_row_label(label) for label in labels])
    rows = _dot_rows(drawn, labels, series, axis_labels)
    many = len(series) > 1
    legend = [item["label"] or "" for item in series]
    low, high = limits
    domain_high = _room(limits, [row["label_text"] for row in rows], chart, log=drawn.log)
    scale: dict[str, Any] = {"domain": [low, domain_high], "nice": False}
    axis: dict[str, Any] = {"title": _axis_title(x_title), "grid": True}
    if drawn.log:
        scale["type"] = "log"
        axis.update({"values": _log_ticks(low, domain_high), "format": "~g"})
    else:
        scale["zero"] = False
        axis.update({**vega.thousands_axis(), **_ticks()})
    y: dict[str, Any] = {
        "field": "row",
        "type": "nominal",
        "sort": axis_labels,
        "axis": _row_axis(axis_labels, labels),
        # A band a row: the points of several series are set apart in it.
        "scale": {"type": "band", "paddingInner": 0.2},
    }
    offset = {}
    if many and drawn.dodge:
        offset = {"yOffset": {"field": "entry", "type": "nominal", "sort": legend}}
    if many:
        # The points' fill has the legend, which a click toggles; the lines'
        # stroke none.
        palette = {"domain": legend, "range": [item["colour"] for item in series]}
        fill: dict[str, Any] = {
            "field": "entry",
            "type": "nominal",
            "scale": palette,
            "legend": _legend_of(drawn.legend_title, legend),
        }
        stroke: dict[str, Any] = {
            "field": "stroke_entry",
            "type": "nominal",
            "scale": palette,
            "legend": None,
        }
    else:
        fill = stroke = {"value": series[0]["colour"] if series else look.text}
    fade = {"opacity": vega.shown()} if many else {}
    intervals = any(row["interval"] != "none" for row in rows)
    value_title = _value_title(x_title or drawn.x_title)
    tooltip = [("name", "Row")]
    if many:
        tooltip.append(("series", drawn.legend_title or "Series"))
    tooltip.append(("value", value_title))
    if intervals:
        tooltip.append(("interval", _interval_title(x_title or drawn.x_title)))
    if drawn.letters and any(drawn.letters):
        tooltip.append(("letters", "Letters (sharing one: no difference)"))
    if any(row["note"] for row in rows):
        tooltip.append(("note", "Note"))
    if any(row["base"] for row in rows):
        tooltip.append(("base", "Base"))
    tip = vega.tooltip(*tooltip)
    layers: list[dict[str, Any]] = []
    if drawn.reference is not None:
        layers.append(
            {
                "data": {"values": [{}]},
                "mark": {"type": "rule", "color": look.muted, "strokeWidth": 1},
                "encoding": {"x": {"datum": drawn.reference, "type": "quantitative"}},
            }
        )
    if drawn.lines:
        layers.append(
            {
                "transform": [{"filter": "isValid(datum.estimate)"}],
                "mark": {"type": "line", "strokeWidth": 1.6},
                "encoding": {
                    "x": {"field": "estimate", "type": "quantitative"},
                    "y": y,
                    "order": {"field": "index", "type": "quantitative"},
                    "detail": {"field": "entry", "type": "nominal"},
                    "stroke": stroke,
                    **fade,
                },
            }
        )
    if intervals:
        layers.append(
            {
                "transform": [{"filter": "isValid(datum.lower) && isValid(datum.upper)"}],
                "mark": {"type": "rule", "strokeWidth": 2},
                "encoding": {
                    "x": {"field": "lower", "type": "quantitative"},
                    "x2": {"field": "upper"},
                    "y": y,
                    **offset,
                    "stroke": stroke,
                    "tooltip": tip,
                    **fade,
                },
            }
        )
    points: dict[str, Any] = {
        "transform": [{"filter": "isValid(datum.estimate)"}],
        "mark": {
            "type": "point",
            "filled": True,
            "size": 80 if not many else 64,
            "stroke": "#ffffff",
            "strokeWidth": 1,
            "opacity": 1,
        },
        "encoding": {
            "x": {"field": "estimate", "type": "quantitative", "scale": scale, "axis": axis},
            "y": y,
            **offset,
            "fill": fill,
            "tooltip": tip,
            "description": {"field": "description"},
            **fade,
        },
    }
    if many:
        points["params"] = [vega.toggle("entry")]
    layers.append(points)
    if any(row["label_text"] for row in rows):
        layers.append(
            {
                "transform": [{"filter": "isValid(datum.tip) && datum.label_text"}],
                "mark": {
                    "type": "text",
                    "align": "left",
                    "baseline": "middle",
                    "dx": 5,
                    "fontSize": VALUE_SIZE if not many else VALUE_SIZE - 1,
                    "color": look.text,
                },
                "encoding": {
                    "x": {"field": "tip", "type": "quantitative"},
                    "y": y,
                    **offset,
                    "text": {"field": "label_text"},
                    **({"opacity": vega.shown(1, 0)} if many else {}),
                },
            }
        )
    view: dict[str, Any] = {
        "name": name,
        "width": "container",
        "height": _row_height(chart, labels, len(series) if drawn.dodge else 1, least=least),
        "data": {"values": rows},
        "layer": layers,
    }
    if title:
        view["title"] = {"text": title, "fontSize": 12, "fontWeight": "normal", "offset": 4}
    return view, rows


def dots_spec(chart: Any, drawn: DrawnDots) -> dict[str, Any]:
    if drawn.panels:
        views, rows = [], []
        for index, (title, labels, series, limits) in enumerate(drawn.panels):
            view, part = _dot_view(
                chart,
                drawn,
                labels,
                series,
                limits,
                name=f"{VIEW}_{index}",
                title=title,
                x_title=drawn.x_title if index == len(drawn.panels) - 1 else None,
                least=40.0,
            )
            views.append(view)
            rows += [{**row, "name": f"{title}, {row['name']}"} for row in part]
        main: dict[str, Any] = {"vconcat": views, "spacing": 16}
    else:
        main, rows = _dot_view(
            chart,
            drawn,
            drawn.labels,
            drawn.series,
            drawn.limits or (0.0, 1.0),
            x_title=drawn.x_title,
        )
    items = [
        (f"{row['name']}, {row['series']}" if row["series"] else row["name"], row["value"])
        for row in rows
        if row["estimate"] is not None
    ]
    what = "Profile chart" if drawn.lines else "Dot chart of estimates and their intervals"
    description = f"{what}: {vega.plain(drawn.heading)}. {vega.listing(items, 24)}."
    return drawn._finish(chart, main, description)


# ─── rows of bars (``_bars``, part-worths, Key drivers) ──────────────────────


@dataclass(kw_only=True)
class DrawnRowBars(DrawnResult):
    """A bar per row, from 0, its value beside it (left of a negative bar)."""

    labels: list[str]
    values: list[float | None]
    texts: list[str]
    colours: list[str]
    reference: float | None = 0.0
    #: Each row's group, which its color stands for (a conjoint attribute, the
    #: sign of a driver's beta), and the legend's title: a click hides a group.
    groups: list[str] | None = None
    legend_title: str | None = None
    #: More of a row for its tooltip: (title, a text per row).
    details: list[tuple[str, list[str]]] = field(default_factory=list)
    value_title: str | None = None

    def spec(self, chart: Any) -> dict[str, Any]:
        return row_bars_spec(chart, self)


@recording
def record_bars(
    chart: Any,
    ax: Any,
    labels: list[Any],
    values: Any,
    texts: list[str],
    colours: Any,
    *,
    reference: float | None,
    groups: list[str] | None = None,
) -> None:
    count = len(labels)
    # A color per row (a list of them), or one for every row (a name, or an
    # RGB tuple the palette gave).
    listed = colours if isinstance(colours, list) and len(colours) == count else None
    chart._drawn = DrawnRowBars(
        labels=[str(label) for label in labels],
        values=[vega.number(value) for value in np.asarray(values, dtype=float).tolist()],
        texts=[str(text) for text in texts],
        colours=[vega.hex_colour(colour) for colour in listed]
        if listed is not None
        else [vega.hex_colour(colours)] * count,
        reference=None if reference is None else float(reference),
        groups=groups,
        axes=ax,
    )


@recording
def record_drivers(chart: Any, analysis: Any, *, heading: str) -> None:
    """Record the Key drivers chart ``drivers.plot`` drew of ``analysis``: each
    driver's share of R², largest first, in the color of its beta's sign."""

    from siamang.data import drivers
    from siamang.reporting import chart_theme

    up = vega.hex_colour(chart_theme.series(drivers.POSITIVE, 0))
    down = vega.hex_colour(chart_theme.series(drivers.NEGATIVE, 1))
    order = np.argsort(-analysis.importance, kind="stable")
    percent = analysis.percent[order]
    negative = analysis.betas[order] < 0
    both = bool(negative.any() and not negative.all())
    detail = (
        f"{drivers.METHOD_NAMES[analysis.method]}, R² = {analysis.r_squared:.3f}, "
        f"N = {analysis.n}"
    )
    chart._drawn = DrawnRowBars(
        adopted=True,
        heading=_one_line(heading),
        subtitle=[detail] + ([f"weighted by '{analysis.weight}'"] if analysis.weight else []),
        x_title="Share of R² (%)",
        base=vega.base_text(int(analysis.n)),
        limits=(0.0, max(float(percent.max()) * 1.18 if len(percent) else 1.0, 1.0)),
        labels=[str(analysis.labels[index]) for index in order],
        values=[vega.number(value) for value in percent],
        texts=[f"{value:.1f} %" for value in percent],
        colours=[down if flag else up for flag in negative],
        reference=None,
        groups=["negative beta" if flag else "positive beta" for flag in negative]
        if both
        else None,
        details=[("Beta (standardized)", [f"{analysis.betas[index]:.3f}" for index in order])],
        value_title="Share of R²",
    )


def row_bars_spec(chart: Any, drawn: DrawnRowBars) -> dict[str, Any]:
    look = vega.look_of(chart)
    axis_labels = vega.unique([_row_label(label) for label in drawn.labels])
    rows = []
    for index, label in enumerate(drawn.labels):
        value = drawn.values[index]
        text = drawn.texts[index] if index < len(drawn.texts) else ""
        row: dict[str, Any] = {
            "row": axis_labels[index],
            "name": _plain(label),
            "value": value,
            "text": text if value is not None else "none",
            "label_text": text if value is not None else "",
            "colour": drawn.colours[index],
            "group": drawn.groups[index] if drawn.groups else "",
            "base": _base_in(label) or drawn.base or "",
            "description": f"{_plain(label)}: {text}",
        }
        for number, (_, values) in enumerate(drawn.details):
            row[f"detail_{number}"] = values[index]
        rows.append(row)
    low, high = drawn.limits or (
        min([0.0, *[v for v in drawn.values if v is not None]]),
        max([0.0, *[v for v in drawn.values if v is not None]]),
    )
    positive = [row["label_text"] for row in rows if (row["value"] or 0) >= 0]
    negative = [row["label_text"] for row in rows if (row["value"] or 0) < 0]
    domain_high = _room((low, high), positive, chart)
    domain_low = low
    if negative:
        domain_low = -_room((-high, -low), negative, chart)
    groups = list(dict.fromkeys(drawn.groups)) if drawn.groups else []
    if len(groups) > 1:
        colours = {
            group: colour for group, colour in zip(drawn.groups or [], drawn.colours, strict=True)
        }
        colour: dict[str, Any] = {
            "field": "group",
            "type": "nominal",
            "scale": {"domain": groups, "range": [colours[group] for group in groups]},
            "legend": _legend_of(drawn.legend_title, groups),
        }
    else:
        colour = {"field": "colour", "type": "nominal", "scale": None, "legend": None}
    fade = {"opacity": vega.shown()} if len(groups) > 1 else {}
    tooltip = [("name", "Row")]
    if len(groups) > 1:
        tooltip.append(("group", drawn.legend_title or "Group"))
    tooltip.append(("text", drawn.value_title or _value_title(drawn.x_title)))
    tooltip += [(f"detail_{number}", title) for number, (title, _) in enumerate(drawn.details)]
    if any(row["base"] for row in rows):
        tooltip.append(("base", "Base"))
    y = {
        "field": "row",
        "type": "nominal",
        "sort": axis_labels,
        "axis": _row_axis(axis_labels, drawn.labels),
        "scale": {"paddingInner": 0.3},
    }
    bars: dict[str, Any] = {
        "mark": {"type": "bar"},
        "encoding": {
            "x": {
                "field": "value",
                "type": "quantitative",
                "scale": {"domain": [domain_low, domain_high], "nice": False},
                "axis": {
                    "title": _axis_title(drawn.x_title),
                    "grid": True,
                    **vega.thousands_axis(),
                    **_ticks(),
                },
            },
            "y": y,
            "color": colour,
            "tooltip": vega.tooltip(*tooltip),
            "description": {"field": "description"},
            **fade,
        },
    }
    if len(groups) > 1:
        bars["params"] = [vega.toggle("group")]
    layers: list[dict[str, Any]] = [bars]
    if drawn.reference is not None:
        layers.append(
            {
                "data": {"values": [{}]},
                "mark": {"type": "rule", "color": look.muted, "strokeWidth": 1},
                "encoding": {"x": {"datum": drawn.reference, "type": "quantitative"}},
            }
        )
    layers.append(
        {
            "transform": [{"filter": "isValid(datum.value)"}],
            "mark": {
                "type": "text",
                "baseline": "middle",
                "fontSize": VALUE_SIZE,
                "color": look.text,
                "align": {"expr": "datum.value < 0 ? 'right' : 'left'"},
                "dx": {"expr": "datum.value < 0 ? -4 : 4"},
            },
            "encoding": {
                "x": {"field": "value", "type": "quantitative"},
                "y": y,
                "text": {"field": "label_text"},
                **({"opacity": vega.shown(1, 0)} if fade else {}),
            },
        }
    )
    main = {
        "name": VIEW,
        "width": "container",
        "height": _row_height(chart, drawn.labels),
        "data": {"values": rows},
        "layer": layers,
    }
    items = [(row["name"], row["text"]) for row in rows if row["value"] is not None]
    description = f"Bar chart: {vega.plain(drawn.heading)}. {vega.listing(items, 24)}."
    return drawn._finish(chart, main, description)


# ─── stacks of shares (the Net Promoter Score, sentiment by theme) ──────────


@dataclass(kw_only=True)
class DrawnStack(DrawnResult):
    """Rows of shares stacked from 0 to 100 %: each part in its color, its
    share written in it where the picture writes it."""

    #: The rows' labels; None for one bar of its own (the NPS).
    labels: list[str] | None
    parts: list[str]
    #: The legend's entries, a part each ("Detractors (0–6): 40.0 %").
    legend: list[str]
    colours: list[str]
    #: The color of a share written in each part, as the picture writes it.
    inks: list[str]
    shares: list[list[float | None]]
    texts: list[list[str]]
    #: The least share the picture writes in its part.
    least: float
    #: A line over the bar (the score) and what an empty row says.
    headline: str | None = None
    empty: str | None = None

    def spec(self, chart: Any) -> dict[str, Any]:
        return stack_spec(chart, self)


@recording
def record_stack(chart: Any, ax: Any, **fields: Any) -> None:
    fields["colours"] = [vega.hex_colour(colour) for colour in fields["colours"]]
    fields["inks"] = [vega.hex_colour(colour) for colour in fields["inks"]]
    fields["shares"] = [[vega.number(value) for value in row] for row in fields["shares"]]
    chart._drawn = DrawnStack(axes=ax, **fields)


def stack_spec(chart: Any, drawn: DrawnStack) -> dict[str, Any]:
    look = vega.look_of(chart)
    one = drawn.labels is None
    labels = [""] if one else drawn.labels or []
    axis_labels = vega.unique([_row_label(label) for label in labels]) if not one else ["bar"]
    rows = []
    for index, (label, shares, texts) in enumerate(
        zip(labels, drawn.shares, drawn.texts, strict=True)
    ):
        start = 0.0
        for part, (name, entry, share, text, ink) in enumerate(
            zip(drawn.parts, drawn.legend, shares, texts, drawn.inks, strict=True)
        ):
            size = share or 0.0
            rows.append(
                {
                    "row": axis_labels[index],
                    "name": _plain(label),
                    "part": name,
                    "entry": entry,
                    "share": share,
                    "text": text if share is not None else "none",
                    "start": start,
                    "end": start + size,
                    "mid": start + size / 2.0,
                    "order": part,
                    "ink": ink,
                    "inside": bool(share is not None and share >= drawn.least),
                    "text_px": _text_px(text),
                    "base": _base_in(label) or drawn.base or "",
                    "description": (f"{_plain(label)}: " if label else "") + f"{name} {text}",
                }
            )
            start += size
    y = {
        "field": "row",
        "type": "nominal",
        "sort": ["headline", *axis_labels] if one else axis_labels,
        "axis": None if one else _row_axis(axis_labels, labels),
        "scale": {"paddingInner": 0.3},
    }
    tooltip = [] if one else [("name", "Row")]
    tooltip += [("part", "Group" if one else "Part"), ("text", "Share")]
    if any(row["base"] for row in rows):
        tooltip.append(("base", "Base"))
    segments = {
        "mark": {"type": "bar", "stroke": "#ffffff", "strokeWidth": 1.5},
        "params": [vega.toggle("entry")],
        "encoding": {
            "x": {
                "field": "start",
                "type": "quantitative",
                "scale": {"domain": [0, 100], "nice": False},
                "axis": {
                    "title": _axis_title(drawn.x_title),
                    "grid": not one,
                    "values": list(range(0, 101, 20 if one else 10)),
                    "labelExpr": "datum.label + ' %'",
                    "labelFlush": False,
                    "labelOverlap": "greedy",
                },
            },
            "x2": {"field": "end"},
            "y": y,
            "color": {
                "field": "entry",
                "type": "nominal",
                "scale": {"domain": drawn.legend, "range": drawn.colours},
                "legend": _legend_of(None, drawn.legend),
            },
            "order": {"field": "order", "type": "quantitative"},
            "opacity": vega.shown(),
            "tooltip": vega.tooltip(*tooltip),
            "description": {"field": "description"},
        },
    }
    fits = "(abs(scale('chart_x', datum.end) - scale('chart_x', datum.start)) >= datum.text_px + 6)"
    layers: list[dict[str, Any]] = [
        segments,
        {
            "transform": [{"filter": "datum.inside"}],
            "mark": {
                "type": "text",
                "fontSize": VALUE_SIZE if not one else 12,
                "align": "center",
                "baseline": "middle",
                "text": {"expr": f"{fits} ? datum.text : ''"},
            },
            "encoding": {
                "x": {"field": "mid", "type": "quantitative"},
                "y": y,
                "color": _ink_encoding(rows, look.text),
                "opacity": vega.shown(1, 0),
            },
        },
    ]
    if drawn.headline:
        layers.append(
            {
                "data": {"values": [{"row": "headline", "text": drawn.headline}]},
                "mark": {
                    "type": "text",
                    # As large as the width drawn at holds it on one line.
                    "fontSize": {
                        "expr": f"max(11, min(20, width / {0.62 * len(drawn.headline):.1f}))"
                    },
                    "baseline": "middle",
                    "align": "center",
                    "color": look.text,
                },
                "encoding": {
                    "x": {"datum": 50, "type": "quantitative"},
                    "y": y,
                    "text": {"field": "text"},
                },
            }
        )
    if drawn.empty:
        empty = [
            {"row": axis_labels[index], "text": drawn.empty}
            for index, shares in enumerate(drawn.shares)
            if not any(share for share in shares)
        ]
        if empty:
            layers.append(
                {
                    "data": {"values": empty},
                    "mark": {
                        "type": "text",
                        "align": "left",
                        "baseline": "middle",
                        "dx": 4,
                        "fontSize": VALUE_SIZE,
                        "color": look.muted,
                    },
                    "encoding": {
                        "x": {"datum": 0, "type": "quantitative"},
                        "y": y,
                        "text": {"field": "text"},
                    },
                }
            )
    main = {
        "name": VIEW,
        "width": "container",
        "height": 120.0 if one else _row_height(chart, labels),
        "data": {"values": rows},
        "layer": layers,
    }
    items = [
        ((f"{row['name']}, " if row["name"] else "") + row["part"], row["text"])
        for row in rows
        if row["share"] is not None
    ]
    headline = f" {drawn.headline}." if drawn.headline else ""
    description = (
        f"Stacked bar chart: {vega.plain(drawn.heading)}.{headline} {vega.listing(items, 30)}."
    )
    return drawn._finish(chart, main, description)


# ─── TURF: each option's reach, and what it alone reaches ────────────────────


@dataclass(kw_only=True)
class DrawnOverlay(DrawnResult):
    """TURF's options: each one's reach, and over it the share only it
    reaches; a line where the portfolio as a whole reaches."""

    labels: list[str]
    reach: list[float | None]
    unique: list[float | None]
    texts: list[str]
    #: The legend's names of the two bars and the line, and their colors.
    names: list[str]
    colours: list[str]
    total: float | None = None

    def spec(self, chart: Any) -> dict[str, Any]:
        return overlay_spec(chart, self)


@recording
def record_overlay(chart: Any, ax: Any, **fields: Any) -> None:
    fields["colours"] = [vega.hex_colour(colour) for colour in fields["colours"]]
    for key in ("reach", "unique"):
        fields[key] = [vega.number(value) for value in fields[key]]
    chart._drawn = DrawnOverlay(axes=ax, **fields)


def overlay_spec(chart: Any, drawn: DrawnOverlay) -> dict[str, Any]:
    look = vega.look_of(chart)
    axis_labels = vega.unique([_row_label(label) for label in drawn.labels])
    reach_name, unique_name = drawn.names[:2]
    rows = []
    for index, label in enumerate(drawn.labels):
        reach, unique = drawn.reach[index], drawn.unique[index]
        common = {
            "row": axis_labels[index],
            "name": _plain(label),
            "reach_text": _amount(reach, 1, True),
            "unique_text": _amount(unique, 1, True),
            "base": drawn.base or "",
        }
        rows.append(
            {
                **common,
                "series": reach_name,
                "value": reach,
                "order": 0,
                "label_text": drawn.texts[index],
                "description": f"{_plain(label)}: reach {_amount(reach, 1, True)}, "
                f"{_amount(unique, 1, True)} only by this option",
            }
        )
        rows.append({**common, "series": unique_name, "value": unique, "order": 1})
    series = list(drawn.names)
    colour = {
        "field": "series",
        "type": "nominal",
        "scale": {"domain": series, "range": drawn.colours},
        "legend": _legend_of(None, series),
    }
    y = {
        "field": "row",
        "type": "nominal",
        "sort": axis_labels,
        "axis": _row_axis(axis_labels, drawn.labels),
        "scale": {"paddingInner": 0.3},
    }
    tooltip = vega.tooltip(
        ("name", "Option"),
        ("reach_text", reach_name),
        ("unique_text", unique_name),
        ("base", "Base"),
    )
    texts = [row.get("label_text", "") for row in rows]
    high = _room((0.0, 100.0), texts, chart)
    layers: list[dict[str, Any]] = [
        {
            "mark": {"type": "bar"},
            "params": [vega.toggle("series")],
            "encoding": {
                # The share only an option reaches over its reach, not after it.
                "x": {
                    "field": "value",
                    "type": "quantitative",
                    "stack": None,
                    "scale": {"domain": [0, high], "nice": False},
                    "axis": {
                        "title": _axis_title(drawn.x_title),
                        "grid": True,
                        "values": list(range(0, 101, 20)),
                    },
                },
                "y": y,
                "color": colour,
                "order": {"field": "order", "type": "quantitative"},
                "opacity": vega.shown(),
                "tooltip": tooltip,
                "description": {"field": "description"},
            },
        },
        {
            "transform": [{"filter": "datum.label_text"}],
            "mark": {
                "type": "text",
                "align": "left",
                "baseline": "middle",
                "dx": 4,
                "fontSize": VALUE_SIZE,
                "color": look.text,
            },
            "encoding": {
                "x": {"field": "value", "type": "quantitative"},
                "y": y,
                "text": {"field": "label_text"},
            },
        },
    ]
    if drawn.total is not None and len(drawn.names) > 2:
        layers.append(
            {
                "data": {
                    "values": [
                        {
                            "series": drawn.names[2],
                            "value": drawn.total,
                            "text": _amount(drawn.total, 1, True),
                            "base": drawn.base or "",
                        }
                    ]
                },
                "mark": {"type": "rule", "strokeWidth": 1.4},
                "encoding": {
                    "x": {"field": "value", "type": "quantitative"},
                    "color": colour,
                    "opacity": vega.shown(),
                    "tooltip": vega.tooltip(
                        ("series", "Portfolio"), ("text", reach_name), ("base", "Base")
                    ),
                },
            }
        )
    main = {
        "name": VIEW,
        "width": "container",
        "height": _row_height(chart, drawn.labels),
        "data": {"values": rows},
        "layer": layers,
    }
    items = [(row["name"], row["label_text"]) for row in rows if row.get("label_text")]
    description = f"Bar chart: {vega.plain(drawn.heading)}. {vega.listing(items, 24)}."
    return drawn._finish(chart, main, description)


# ─── a proportion and its interval ───────────────────────────────────────────


@dataclass(kw_only=True)
class DrawnProportion(DrawnResult):
    share: float
    low: float
    high: float
    colour: str
    track: str
    #: The line under the number: the interval, its level and the base.
    line: str

    def spec(self, chart: Any) -> dict[str, Any]:
        return proportion_spec(chart, self)


@recording
def record_proportion(chart: Any, ax: Any, **fields: Any) -> None:
    fields["colour"] = vega.hex_colour(fields["colour"])
    fields["track"] = vega.hex_colour(fields["track"])
    chart._drawn = DrawnProportion(axes=ax, limits=(0.0, 100.0), **fields)


def proportion_spec(chart: Any, drawn: DrawnProportion) -> dict[str, Any]:
    look = vega.look_of(chart)
    text = _amount(drawn.share, 1, True)
    interval = f"{_amount(drawn.low, 1, True)} to {_amount(drawn.high, 1, True)}"
    row = {
        "share": drawn.share,
        "low": drawn.low,
        "high": drawn.high,
        "text": text,
        "interval": interval,
        "note": drawn.line,
        "description": f"{text}, {drawn.line}",
    }
    x = {
        "type": "quantitative",
        "scale": {"domain": [-2, 102], "nice": False},
        "axis": {
            "title": None,
            "values": list(range(0, 101, 10)),
            "labelExpr": "datum.label + ' %'",
            "grid": False,
        },
    }
    tooltip = vega.tooltip(("text", "Share"), ("interval", "Interval"), ("note", "Base"))
    layers: list[dict[str, Any]] = [
        {
            "data": {"values": [{"from": 0, "to": 100}]},
            "mark": {"type": "rule", "strokeWidth": 14, "color": drawn.track, "strokeCap": "butt"},
            "encoding": {
                "x": {"field": "from", **x},
                "x2": {"field": "to"},
                "y": {"value": 96},
            },
        },
        {
            "mark": {
                "type": "rule",
                "strokeWidth": 14,
                "color": drawn.colour,
                "opacity": 0.45,
                "strokeCap": "butt",
            },
            "encoding": {
                "x": {"field": "low", "type": "quantitative"},
                "x2": {"field": "high"},
                "y": {"value": 96},
                "tooltip": tooltip,
            },
        },
        {
            "mark": {
                "type": "point",
                "filled": True,
                "size": 320,
                "color": drawn.colour,
                "stroke": "#ffffff",
                "strokeWidth": 1.5,
                "opacity": 1,
            },
            "encoding": {
                "x": {"field": "share", "type": "quantitative"},
                "y": {"value": 96},
                "tooltip": tooltip,
                "description": {"field": "description"},
            },
        },
        {
            "mark": {
                "type": "text",
                "fontSize": 34,
                "align": "center",
                "baseline": "middle",
                "color": look.text,
            },
            "encoding": {
                "x": {"datum": 50, "type": "quantitative"},
                "y": {"value": 36},
                "text": {"field": "text"},
            },
        },
    ]
    main = {
        "name": VIEW,
        "width": "container",
        "height": 124,
        "data": {"values": [row]},
        "layer": layers,
    }
    notes = [drawn.line, *drawn.notes]
    description = f"Proportion: {vega.plain(drawn.heading)}, {text}; {drawn.line}."
    spec = vega.finish(
        chart,
        main,
        heading=drawn.heading,
        subtitle=_subtitle(drawn.subtitle),
        notes=notes,
        description=description,
        kind=getattr(chart, "drawn", "") or "interval",
    )
    return spec


# ─── TURF's reach curve ──────────────────────────────────────────────────────


@dataclass(kw_only=True)
class DrawnReach(DrawnResult):
    """TURF's reach by portfolio size: each size's tick names what it adds."""

    ticks: list[str]
    portfolios: list[str]
    reach: list[float | None]
    added: list[float | None]
    colour: str
    ink: str

    def spec(self, chart: Any) -> dict[str, Any]:
        return reach_spec(chart, self)


@recording
def record_reach(chart: Any, ax: Any, **fields: Any) -> None:
    fields["colour"] = vega.hex_colour(fields["colour"])
    fields["ink"] = vega.hex_colour(fields["ink"])
    for key in ("reach", "added"):
        fields[key] = [vega.number(value) for value in fields[key]]
    chart._drawn = DrawnReach(axes=ax, along="y", **fields)


def _tick_lines(tick: str, width: int) -> list[str]:
    return [line for part in tick.split("\n") for line in vega.wrap(part, width)]


def reach_spec(chart: Any, drawn: DrawnReach) -> dict[str, Any]:
    ticks = vega.unique(["\n".join(_tick_lines(tick, 18)) for tick in drawn.ticks])
    narrow = {tick: _tick_lines(raw, 9) for tick, raw in zip(ticks, drawn.ticks, strict=True)}
    count = max(len(ticks), 1)
    rows = []
    for index, tick in enumerate(ticks):
        reach, added = drawn.reach[index], drawn.added[index]
        size = drawn.ticks[index].split("\n")[0]
        lines = [_amount(reach, 1, True)]
        if index:
            lines.append(f"(+{added:.1f})" if added is not None else "")
        rows.append(
            {
                "tick": tick,
                "size": size,
                "portfolio": drawn.portfolios[index],
                "reach": reach,
                "text": _amount(reach, 1, True),
                "added": f"+{_amount(added, 1, True)}" if index and added is not None else "—",
                "lines": lines,
                "base": drawn.base or "",
                "description": f"{size}: {drawn.portfolios[index]}, reach "
                f"{_amount(reach, 1, True)}",
            }
        )
    x = {
        "field": "tick",
        "type": "nominal",
        "sort": ticks,
        "axis": {
            "title": _axis_title(drawn.x_title),
            "labelAngle": 0,
            "labelExpr": f"containerSize()[0] < {NARROW} ? {vega.script_json(narrow)}"
            "[datum.label] : split(datum.label, '\\n')",
            # No wider than its slot: the tooltip names the whole portfolio.
            "labelLimit": {"expr": f"max(width / {count} - 6, 40)"},
            "grid": False,
            "ticks": False,
        },
    }
    y = {
        "field": "reach",
        "type": "quantitative",
        "scale": {"domain": [0, 100], "nice": False},
        "axis": {
            "title": _axis_title(drawn.y_title),
            "values": list(range(0, 101, 20)),
            "labelExpr": "datum.label + ' %'",
        },
    }
    tooltip = vega.tooltip(
        ("size", "Portfolio size"),
        ("portfolio", "Portfolio"),
        ("text", "Reach"),
        ("added", "Added by the last option"),
        ("base", "Base"),
    )
    layers = [
        {
            "mark": {"type": "line", "strokeWidth": 2, "color": drawn.colour},
            "encoding": {"x": x, "y": y},
        },
        {
            "mark": {
                "type": "point",
                "filled": True,
                "size": 90,
                "color": drawn.colour,
                "stroke": "#ffffff",
                "strokeWidth": 1,
                "opacity": 1,
            },
            "encoding": {
                "x": x,
                "y": {"field": "reach", "type": "quantitative"},
                "tooltip": tooltip,
                "description": {"field": "description"},
            },
        },
        {
            "mark": {
                "type": "text",
                "align": "center",
                "baseline": "bottom",
                # The reach, and what the size added under it: both over the point.
                "dy": {"expr": "-8 - 13 * (length(datum.lines) - 1)"},
                "fontSize": VALUE_SIZE,
                "lineHeight": 13,
                "color": drawn.ink,
            },
            "encoding": {
                "x": x,
                "y": {"field": "reach", "type": "quantitative"},
                "text": {"field": "lines"},
            },
        },
    ]
    main = {
        "name": VIEW,
        "width": "container",
        "height": _height(chart, 240.0, 380.0),
        "data": {"values": rows},
        "layer": layers,
    }
    items = [(row["size"], row["text"]) for row in rows]
    description = (
        f"Line chart: {vega.plain(drawn.heading)}, reach by portfolio size. "
        f"{vega.listing(items)}."
    )
    return drawn._finish(chart, main, description)


# ─── a scree plot ────────────────────────────────────────────────────────────


@dataclass(kw_only=True)
class DrawnScree(DrawnResult):
    """Eigenvalues by component, those kept filled; Kaiser's line at 1 and,
    from a parallel analysis, random data's."""

    eigenvalues: list[float | None]
    kept: int | None
    random: list[float | None] | None
    shown: list[int]
    name: str
    #: The legend's names: the eigenvalues, Kaiser's line, random data's.
    names: list[str]
    colour: str
    ink: str
    muted: str

    def spec(self, chart: Any) -> dict[str, Any]:
        return scree_spec(chart, self)


@recording
def record_scree(chart: Any, ax: Any, **fields: Any) -> None:
    for key in ("colour", "ink", "muted"):
        fields[key] = vega.hex_colour(fields[key])
    fields["eigenvalues"] = [vega.number(value) for value in fields["eigenvalues"]]
    if fields.get("random") is not None:
        fields["random"] = [vega.number(value) for value in fields["random"]]
    chart._drawn = DrawnScree(axes=ax, along="y", **fields)


def scree_spec(chart: Any, drawn: DrawnScree) -> dict[str, Any]:
    count = len(drawn.eigenvalues)
    eigen, kaiser = drawn.names[0], drawn.names[1]
    names = [eigen, kaiser] + ([drawn.names[2]] if drawn.random is not None else [])
    colours = [drawn.colour, drawn.ink] + ([drawn.muted] if drawn.random is not None else [])
    points = []
    for index, value in enumerate(drawn.eigenvalues, start=1):
        kept = drawn.kept is not None and index <= drawn.kept
        points.append(
            {
                "x": index,
                "value": value,
                "series": eigen,
                "text": _amount(value, 2),
                "kept": kept,
                "state": "kept" if kept else ("not kept" if drawn.kept is not None else ""),
                "label_text": _amount(value, 2) if index in drawn.shown else "",
                "random": _amount(drawn.random[index - 1], 2) if drawn.random is not None else "",
                "description": f"{drawn.name} {index}: eigenvalue {_amount(value, 2)}",
            }
        )
    lines = [{"x": row["x"], "value": row["value"], "series": eigen} for row in points]
    lines += [{"x": x, "value": 1.0, "series": kaiser} for x in (0.5, count + 0.5)]
    if drawn.random is not None:
        lines += [
            {"x": index, "value": value, "series": names[2]}
            for index, value in enumerate(drawn.random, start=1)
        ]
    top = max([1.0, *[value for value in drawn.eigenvalues if value is not None]]) * 1.12
    colour = {
        "field": "series",
        "type": "nominal",
        "scale": {"domain": names, "range": colours},
        "legend": {**_legend_of(None, names), "symbolType": "stroke", "symbolStrokeWidth": 2},
    }
    x = {
        "field": "x",
        "type": "quantitative",
        "scale": {"domain": [0.5, count + 0.5], "nice": False, "zero": False},
        "axis": {
            "title": _axis_title(drawn.x_title),
            "grid": False,
            "format": "d",
            **({"values": list(range(1, count + 1))} if count <= 25 else {"tickMinStep": 1}),
        },
    }
    y = {
        "field": "value",
        "type": "quantitative",
        "scale": {"domain": [0, top], "nice": False},
        "axis": {"title": _axis_title(drawn.y_title), "grid": True},
    }
    tooltip = [("x", drawn.name), ("text", "Eigenvalue")]
    if drawn.kept is not None:
        tooltip.append(("state", "Kept"))
    if drawn.random is not None:
        tooltip.append(("random", "Random data, 95th percentile"))
    if drawn.base:
        tooltip.append(("base", "Base"))
        for row in points:
            row["base"] = drawn.base
    layers: list[dict[str, Any]] = [
        {
            "data": {"values": lines},
            "mark": {"type": "line", "strokeWidth": 1.8},
            "params": [vega.toggle("series")],
            "encoding": {
                "x": x,
                "y": y,
                "color": colour,
                # Kaiser's line dashed, in the legend too.
                "strokeDash": {
                    "field": "series",
                    "type": "nominal",
                    "scale": {
                        "domain": names,
                        "range": [[1, 0], [4, 3]] + ([[1, 0]] if len(names) > 2 else []),
                    },
                },
                "opacity": vega.shown(),
            },
        },
        {
            "data": {"values": points},
            "mark": {"type": "point", "size": 70, "strokeWidth": 1.8, "opacity": 1},
            "encoding": {
                "x": {"field": "x", "type": "quantitative"},
                "y": {"field": "value", "type": "quantitative"},
                "fill": {
                    "condition": {"test": "datum.kept", "value": drawn.colour},
                    "value": "#ffffff",
                },
                "stroke": {
                    "condition": {"test": "datum.kept", "value": "#ffffff"},
                    "value": drawn.colour,
                },
                "tooltip": vega.tooltip(*tooltip),
                "description": {"field": "description"},
                "opacity": vega.shown(),
            },
        },
        {
            "data": {"values": points},
            "transform": [{"filter": "datum.label_text"}],
            "mark": {
                "type": "text",
                "align": "left",
                "baseline": "bottom",
                "dx": 6,
                "dy": -4,
                "fontSize": VALUE_SIZE,
                "color": drawn.ink,
            },
            "encoding": {
                "x": {"field": "x", "type": "quantitative"},
                "y": {"field": "value", "type": "quantitative"},
                "text": {"field": "label_text"},
            },
        },
    ]
    main = {
        "name": VIEW,
        "width": "container",
        "height": _height(chart, 240.0, 380.0),
        "layer": layers,
    }
    items = [(f"{drawn.name} {row['x']}", row["text"]) for row in points]
    kept = f", {drawn.kept} kept" if drawn.kept is not None else ""
    description = (
        f"Scree plot: {vega.plain(drawn.heading)}, eigenvalues of {count} "
        f"{drawn.name.lower()}s{kept}. {vega.listing(items)}."
    )
    return drawn._finish(chart, main, description)


# ─── heatmaps (loadings, a correlation matrix) ───────────────────────────────


@dataclass(kw_only=True)
class DrawnImage(DrawnResult):
    """A heatmap an ``imshow`` drew: its cells, the color map and norm it was
    drawn with (sampled), and what each cell writes."""

    matrix: DrawnMatrix

    def spec(self, chart: Any) -> dict[str, Any]:
        matrix = dataclasses.replace(
            self.matrix,
            title=self.heading,
            subtitle=_subtitle(self.subtitle),
            notes=[*self.matrix.notes, *self.notes],
            bases=self.matrix.bases or ([self.base] if self.base else []),
        )
        spec = matrix_spec(chart, matrix)
        spec["usermeta"]["siamang"]["chart"] = getattr(chart, "drawn", "") or matrix.kind
        return spec


@recording
def record_image(
    chart: Any,
    ax: Any,
    values: Any,
    *,
    cmap: Any,
    norm: Any,
    rows: list[str],
    columns: list[str],
    texts: list[list[str]],
    annotate: bool,
    row_names: list[str] | None = None,
    column_names: list[str] | None = None,
    legend_title: str,
    value_title: str,
    column_title: str | None = None,
    notes: list[str] | None = None,
    blank: str | None = None,
    blank_text: str = "not computed",
    details: dict[str, list[list[str]]] | None = None,
) -> None:
    array = np.asarray(values, dtype=float)
    low, high = float(norm.vmin), float(norm.vmax)
    steps = 11
    domain = [low + (high - low) * index / (steps - 1) for index in range(steps)]
    stops = [vega.hex_colour(cmap(norm(value))) for value in domain]
    fills = [
        [vega.hex_colour(cmap(norm(value))) if value == value else "#ffffff" for value in line]
        for line in array.tolist()
    ]
    chart._drawn = DrawnImage(
        axes=ax,
        matrix=DrawnMatrix(
            values=array,
            rows=[str(row) for row in rows],
            columns=[str(column) for column in columns],
            row_names=[_one_line(row) for row in (row_names or rows)],
            column_names=[_one_line(column) for column in (column_names or columns)],
            texts=texts,
            stops=stops,
            domain=domain,
            annotate=annotate,
            title="",
            notes=[note for note in (notes or []) if note],
            legend_title=legend_title,
            x_title=column_title,
            value_title=value_title,
            bases=[],
            kind="heatmap",
            fills=fills,
            blank=None if blank is None else vega.hex_colour(blank),
            blank_text=blank_text,
            details=dict(details or {}),
        ),
    )


# ─── the Perceptual map ──────────────────────────────────────────────────────


@dataclass(kw_only=True)
class DrawnMap(DrawnResult):
    """A correspondence analysis's symmetric map: the rows' and the columns'
    points on two dimensions, one scale on both axes, each point named."""

    points: list[dict[str, Any]]
    sets: list[str]
    colours: list[str]
    #: Whether the names are written by the points at first: the picture
    #: numbered the points of a map too crowded to name them.
    named: bool
    rule: str

    def spec(self, chart: Any) -> dict[str, Any]:
        return map_spec(chart, self)


@recording
def record_map(chart: Any, analysis: Any, *, numbered: bool, heading: str) -> None:
    """Record the Perceptual map ``correspondence.plot`` drew of ``analysis``
    (its first two dimensions, as the Result chart draws it)."""

    from siamang.data import correspondence

    solution = analysis.solution
    top = solution.dimensions
    points = []
    sets = [str(analysis.row_title), str(analysis.column_title)]
    tables = [analysis.rows, analysis.columns]
    for part, (labels, principal, masses, table) in enumerate(
        (
            (analysis.row_labels, solution.row_principal, solution.row_masses, tables[0]),
            (analysis.column_labels, solution.column_principal, solution.column_masses, tables[1]),
        )
    ):
        frame = table.to_frame() if hasattr(table, "to_frame") else None
        quality = (
            list(frame["Quality"])
            if frame is not None and "Quality" in frame
            else [None] * len(labels)
        )
        for index, label in enumerate(labels):
            x = float(principal[index, 0]) if top >= 1 else 0.0
            y = float(principal[index, 1]) if top >= 2 else 0.0
            points.append(
                {
                    "set": sets[part],
                    "name": str(label),
                    "label": correspondence._lines(str(label), 30).split("\n"),
                    "x": x,
                    "y": y,
                    "x_text": f"{x:.3f}",
                    "y_text": f"{y:.3f}",
                    "mass": f"{float(masses[index]):.3f}",
                    "quality": "" if quality[index] is None else f"{float(quality[index]):.3f}",
                    "description": f"{sets[part]}: {label} at {x:.2f}, {y:.2f}",
                }
            )
    # Where the picture placed each name — beside its point, or further out
    # with a line back to it — in points from the point, which at the width a
    # report draws the map are its pixels.
    placed = _placed_names(chart._fig.axes[0]) if not numbered else []
    if len(placed) == len(points):
        for point, (dx, dy, far) in zip(points, placed, strict=True):
            lines = len(point["label"])
            point.update(dx=dx, dy=-dy - lines * MAP_LINE, far=far, lx=dx, ly=-dy, align="left")
    shown = solution.explained[[k for k in (0, 1) if k < top]].sum()
    detail = f"Correspondence analysis, symmetric map — {shown:.1f} % of the inertia shown" + (
        f", N = {analysis.stats['N']}" if analysis.stats.get("N") else ""
    )

    def axis_title(k: int) -> str:
        if k > top:
            return f"Dimension {k} (none: the table has {top})"
        return f"Dimension {k} ({solution.explained[k - 1]:.1f} % of inertia)"

    chart._drawn = DrawnMap(
        adopted=True,
        heading=_one_line(heading),
        subtitle=[detail] + ([f"weighted by '{analysis.weight}'"] if analysis.weight else []),
        x_title=axis_title(1),
        y_title=axis_title(2),
        points=points,
        sets=sets,
        colours=[
            vega.hex_colour(correspondence._rows()),
            vega.hex_colour(correspondence._columns()),
        ],
        named=not numbered,
        rule=vega.hex_colour(correspondence._rule()),
        base=vega.base_text(int(analysis.stats["N"]))
        if isinstance(analysis.stats.get("N"), int | np.integer)
        else None,
    )


#: What a map's container holds besides its plot, across: the y axis, its
#: title and the padding (pixels).
MAP_CHROME = 92.0


#: The height of a line of a name on the map (pixels).
MAP_LINE = 13.0


def _placed_names(ax: Any) -> list[tuple[float, float, bool]]:
    """Each name the map's picture wrote beside its point: its bottom-left
    corner from the point, in points (up is positive), and whether it is
    far out, with a line back to its point."""

    placed = []
    for text in ax.texts:
        offset = getattr(text, "xyann", None)
        if offset is None or getattr(text, "anncoords", None) != "offset points":
            continue
        placed.append(
            (float(offset[0]), float(offset[1]), getattr(text, "arrow_patch", None) is not None)
        )
    return placed


def map_spec(chart: Any, drawn: DrawnMap) -> dict[str, Any]:
    look = vega.look_of(chart)
    xs = [point["x"] for point in drawn.points]
    ys = [point["y"] for point in drawn.points]
    height = _height(chart, 300.0, 480.0)
    # The points with a margin (as the picture's), both axes on one scale: a
    # unit is as long across as up at whatever width the map is drawn.
    x_low, x_high = min([0.0, *xs]), max([0.0, *xs])
    y_low, y_high = min([0.0, *ys]), max([0.0, *ys])
    x_span = max(x_high - x_low, 1e-9) * 1.3
    y_span = max(y_high - y_low, 1e-9) * 1.3
    cx, cy = (x_low + x_high) / 2.0, (y_low + y_high) / 2.0
    # The plot's width is the container's but for the axis and the padding:
    # the plot's own width would make its domain follow its layout, which
    # follows its domain.
    plot = f"max(containerSize()[0] - {MAP_CHROME:g}, 120)"
    per = f"max({x_span!r} / {plot}, {y_span!r} / {height!r})"
    x_domain = [
        {"expr": f"{cx!r} - {per} * {plot} / 2"},
        {"expr": f"{cx!r} + {per} * {plot} / 2"},
    ]
    y_domain = [
        {"expr": f"{cy!r} - {per} * {height!r} / 2"},
        {"expr": f"{cy!r} + {per} * {height!r} / 2"},
    ]
    points = []
    for point in drawn.points:
        right = point["x"] > cx + (x_high - x_low) / 6.0
        # Beside its point: right of it, or left of it in the map's right
        # third, where it would run past the edge.
        beside = {
            "ndx": -7.0 if right else 7.0,
            "ndy": -len(point["label"]) * MAP_LINE / 2.0,
            "nalign": "right" if right else "left",
        }
        points.append(
            {
                # Where the picture put the name, at a report's width; beside
                # its point in a narrower chart, whose points lie closer.
                "dx": beside["ndx"],
                "dy": beside["ndy"],
                "align": beside["nalign"],
                **beside,
                **point,
                "base": drawn.base or "",
            }
        )
    narrow = f"containerSize()[0] < {NARROW}"
    colour = {
        "field": "set",
        "type": "nominal",
        "scale": {"domain": drawn.sets, "range": drawn.colours},
        "legend": _legend_of(None, drawn.sets),
    }
    # The rows as circles, the columns as triangles — in the legend too.
    shape = {
        "field": "set",
        "type": "nominal",
        "scale": {"domain": drawn.sets, "range": ["circle", "triangle-up"]},
    }
    x = {
        "field": "x",
        "type": "quantitative",
        "scale": {"domain": x_domain, "nice": False, "zero": False},
        "axis": {"title": drawn.x_title, "grid": False, "tickCount": 6},
    }
    y = {
        "field": "y",
        "type": "quantitative",
        "scale": {"domain": y_domain, "nice": False, "zero": False},
        "axis": {"title": drawn.y_title, "grid": False, "tickCount": 6},
    }
    tooltip = vega.tooltip(
        ("set", "Of"),
        ("name", "Name"),
        ("x_text", "Dimension 1"),
        ("y_text", "Dimension 2"),
        ("mass", "Mass"),
        ("quality", "Quality"),
        ("base", "Base"),
    )
    layers: list[dict[str, Any]] = [
        {
            # A name placed far out: a line back to its point.
            "transform": [{"filter": "datum.far"}],
            "mark": {
                "type": "rule",
                "color": look.muted,
                "strokeWidth": 0.6,
                "clip": True,
                "x2Offset": {"expr": "datum.lx"},
                "y2Offset": {"expr": "datum.ly"},
                "opacity": {"expr": f"names && !({narrow}) ? 1 : 0"},
            },
            "encoding": {
                "x": {"field": "x", "type": "quantitative"},
                "y": {"field": "y", "type": "quantitative"},
                "x2": {"field": "x"},
                "y2": {"field": "y"},
            },
        },
        {
            "data": {"values": [{}]},
            "mark": {"type": "rule", "color": drawn.rule, "strokeWidth": 0.8},
            "encoding": {"x": {"datum": 0, "type": "quantitative"}},
        },
        {
            "data": {"values": [{}]},
            "mark": {"type": "rule", "color": drawn.rule, "strokeWidth": 0.8},
            "encoding": {"y": {"datum": 0, "type": "quantitative"}},
        },
        {
            "mark": {
                "type": "point",
                "filled": True,
                "size": 70,
                "stroke": "#ffffff",
                "strokeWidth": 1.2,
                "opacity": 1,
                "clip": True,
            },
            "params": [vega.toggle("set"), _zoom()],
            "encoding": {
                "x": x,
                "y": y,
                "color": colour,
                "shape": shape,
                "opacity": vega.shown(),
                "tooltip": tooltip,
                "description": {"field": "description"},
            },
        },
        {
            "mark": {
                "type": "text",
                "align": {"expr": f"{narrow} ? datum.nalign : datum.align"},
                "dx": {"expr": f"{narrow} ? datum.ndx : datum.dx"},
                "dy": {"expr": f"{narrow} ? datum.ndy : datum.dy"},
                "baseline": "top",
                "fontSize": VALUE_SIZE,
                "lineHeight": MAP_LINE,
                "color": look.text,
                "clip": True,
                "text": {"expr": "names ? datum.label : ''"},
            },
            "encoding": {
                "x": {"field": "x", "type": "quantitative"},
                "y": {"field": "y", "type": "quantitative"},
                "opacity": vega.shown(1, 0),
            },
        },
    ]
    main = {
        "name": VIEW,
        "width": "container",
        "height": height,
        "data": {"values": points},
        "layer": layers,
    }
    notes = list(drawn.notes)
    if not drawn.named:
        notes.append("The map is crowded: point at a point for its name, or tick Names on the map.")
    notes.append(ZOOM_HINT)
    items = [(f"{point['name']} ({point['set']})", "") for point in drawn.points]
    description = (
        f"Perceptual map: {vega.plain(drawn.heading)}. {drawn.x_title} across, "
        f"{drawn.y_title} up; {len(drawn.points)} points: "
        + ", ".join(name for name, _ in items[:30])
        + (f" and {len(items) - 30} more" if len(items) > 30 else "")
        + "."
    )
    spec = drawn._finish(chart, main, description, notes)
    # A box under the map that writes the names by the points, or leaves them
    # to the tooltips.
    spec["params"] = [
        {
            "name": "names",
            "value": drawn.named,
            "bind": {"input": "checkbox", "name": "Names on the map "},
        }
    ]
    return spec


# ─── Price sensitivity ───────────────────────────────────────────────────────


@dataclass(kw_only=True)
class DrawnPrices(DrawnResult):
    """Price sensitivity as the analysis draws it: Van Westendorp's four
    curves, its points and its range (with the NMS trial curve under them),
    or Gabor-Granger's demand over its revenue."""

    method: str
    prices: list[float]
    price_texts: list[str]
    #: Each: key, name, values (per price), color and whether it is dashed.
    curves: list[dict[str, Any]]
    #: Each: name ("IPP"), price, the share where it is marked, its panel.
    points: list[dict[str, Any]]
    band: tuple[float, float] | None
    band_colour: str | None
    ink: str
    muted: str
    #: The NMS trial curve (a share per price), or None.
    trial: list[float | None] | None = None
    #: Gabor-Granger: demand (%) and revenue per price, the best price, and
    #: the colors of the curve, the best bar and the others.
    demand: list[float | None] | None = None
    revenue: list[float | None] | None = None
    best: float | None = None
    colours: list[str] = field(default_factory=list)
    unit: str = ""

    def spec(self, chart: Any) -> dict[str, Any]:
        if self.method == "gabor_granger":
            return gabor_granger_spec(chart, self)
        return van_westendorp_spec(chart, self)


@recording
def record_prices(chart: Any, analysis: Any, *, heading: str) -> None:
    """Record the Price sensitivity chart ``pricing.plot`` drew of ``analysis``."""

    from siamang.data import pricing

    prices = [float(price) for price in analysis.prices]
    subtitle = f"N = {analysis.n}" + (
        f", weighted by '{analysis.weight}'" if analysis.weight else ""
    )
    common: dict[str, Any] = {
        "adopted": True,
        "heading": _one_line(heading),
        "subtitle": [subtitle],
        "x_title": pricing._price_axis(analysis),
        "base": vega.base_text(int(analysis.n)),
        "method": analysis.method,
        "prices": prices,
        "price_texts": [pricing._price(price) for price in prices],
        "ink": vega.hex_colour(pricing._ink()),
        "muted": vega.hex_colour(pricing._muted()),
        "unit": str(analysis.unit or ""),
    }
    if analysis.method == "gabor_granger":
        best = float(analysis.points["revenue"])
        lighter = pricing.chart_theme.tint("#f5b48f", pricing._expensive(), 0.5)
        chart._drawn = DrawnPrices(
            **common,
            curves=[],
            points=[],
            band=None,
            band_colour=None,
            demand=[vega.number(value) for value in analysis.shares["demand"]],
            revenue=[vega.number(value) for value in analysis.shares["revenue"]],
            best=best,
            colours=[
                vega.hex_colour(pricing._cheap()),
                vega.hex_colour(pricing._expensive()),
                vega.hex_colour(lighter),
            ],
            y_title="Would buy (%)",
        )
        return
    colours = {
        pricing.CHEAP_COLOUR: vega.hex_colour(pricing._cheap()),
        pricing.EXPENSIVE_COLOUR: vega.hex_colour(pricing._expensive()),
    }
    curves = [
        {
            "key": key,
            "name": pricing.CURVE_NAMES[key],
            "values": [vega.number(value) for value in analysis.shares[key]],
            "colour": colours[colour],
            "dashed": style == "--",
        }
        for key, colour, style in pricing._LINES
    ]
    points = []
    for key, _, _ in pricing.POINTS:
        price = analysis.points.get(key)
        if price is None:
            continue
        falling = pricing._CURVES_OF[key][0]
        value = float(np.interp(price, analysis.prices, analysis.shares[falling]))
        points.append(
            {
                "key": key,
                "name": f"{key} {pricing._price(price)}",
                "price": float(price),
                "value": value,
                "panel": 0,
            }
        )
    trial = None
    if "trial" in analysis.shares:
        trial = [vega.number(value) for value in analysis.shares["trial"]]
        for key, name in (("trial", "highest trial"), ("revenue", "highest revenue")):
            price = analysis.points.get(key)
            if price is None:
                continue
            value = float(np.interp(price, analysis.prices, analysis.shares["trial"]))
            points.append(
                {
                    "key": key,
                    "name": f"{name} {pricing._price(price)}",
                    "price": float(price),
                    "value": value,
                    "panel": 1,
                }
            )
    low, high = analysis.points.get("PMC"), analysis.points.get("PME")
    band = (float(low), float(high)) if low is not None and high is not None else None
    chart._drawn = DrawnPrices(
        **common,
        curves=curves,
        points=points,
        band=band,
        band_colour=vega.hex_colour(
            pricing.chart_theme.tint(pricing._BAND, pricing.chart_theme.grid(pricing._BAND), 0.5)
        ),
        trial=trial,
        y_title="% of respondents",
    )


def _price_axis(drawn: DrawnPrices, title: str | None, margin: float = 0.02) -> dict[str, Any]:
    """The price axis: the prices asked about, ``margin`` of their span (or,
    over 1, of the least step between them) past either end."""

    span = (max(drawn.prices) - min(drawn.prices)) or 1.0
    if margin > 1 and len(drawn.prices) > 1:
        pad = float(min(np.diff(sorted(drawn.prices)))) * (margin - 1)
    else:
        pad = span * margin
    return {
        "field": "price",
        "type": "quantitative",
        "scale": {
            "domain": [min(drawn.prices) - pad, max(drawn.prices) + pad],
            "nice": False,
            "zero": False,
        },
        "axis": {
            "title": _axis_title(title),
            "grid": False,
            **vega.thousands_axis(),
            **_ticks(),
        },
    }


def _staggered(points: list[dict[str, Any]], span: float) -> None:
    """Each name a level lower than a name it would otherwise touch — names
    of points at close prices stand one over another, as the picture's."""

    placed: list[tuple[float, int]] = []
    for point in sorted(points, key=lambda item: item["price"]):
        level = 0
        while any(
            abs(point["price"] - price) < span * 0.16 and taken == level for price, taken in placed
        ):
            level += 1
        point["level"] = level
        placed.append((point["price"], level))


def van_westendorp_spec(chart: Any, drawn: DrawnPrices) -> dict[str, Any]:
    names = [curve["name"] for curve in drawn.curves]
    span = (max(drawn.prices) - min(drawn.prices)) or 1.0
    lines = []
    for curve in drawn.curves:
        for price, text, value in zip(
            drawn.prices, drawn.price_texts, curve["values"], strict=True
        ):
            lines.append(
                {
                    "price": price,
                    "price_text": text,
                    "curve": curve["name"],
                    "value": value,
                    "text": _amount(value, 1, True),
                }
            )
    wide = []
    for index, (price, text) in enumerate(zip(drawn.prices, drawn.price_texts, strict=True)):
        row: dict[str, Any] = {"price": price, "price_text": text, "base": drawn.base or ""}
        for number, curve in enumerate(drawn.curves):
            row[f"c{number}"] = _amount(curve["values"][index], 1, True)
        if drawn.trial is not None:
            row["trial"] = _amount(drawn.trial[index], 1, True)
        wide.append(row)
    marked = [dict(point) for point in drawn.points]
    first = [point for point in marked if point["panel"] == 0]
    second = [point for point in marked if point["panel"] == 1]
    _staggered(first, span)
    _staggered(second, span)
    for point in marked:
        point["text"] = _amount(point["value"], 1, True)
        point["price_text"] = next(
            (
                text
                for price, text in zip(drawn.prices, drawn.price_texts, strict=True)
                if price == point["price"]
            ),
            f"{point['price']:g}",
        )
    x = _price_axis(drawn, drawn.x_title)
    if drawn.trial is not None:
        # The prices are written under the trial curve's panel, which shares them.
        x["axis"] = {**x["axis"], "title": None, "labels": False}
    colour = {
        "field": "curve",
        "type": "nominal",
        "scale": {"domain": names, "range": [curve["colour"] for curve in drawn.curves]},
        "legend": {**_legend_of(None, names), "symbolType": "stroke", "symbolStrokeWidth": 2},
    }
    # "Not" dashed, in the legend too.
    dash = {
        "field": "curve",
        "type": "nominal",
        "scale": {
            "domain": names,
            "range": [[6, 4] if curve["dashed"] else [1, 0] for curve in drawn.curves],
        },
    }
    hover_tooltip = [("price_text", "Price")]
    hover_tooltip += [(f"c{number}", curve["name"]) for number, curve in enumerate(drawn.curves)]
    hover_tooltip.append(("base", "Base"))
    # The names of the points over the curves, a level higher for a name
    # that would touch another.
    top = 112.0 + 8.0 * max((point.get("level", 0) for point in first), default=0)
    y = {
        "field": "value",
        "type": "quantitative",
        "scale": {"domain": [0, top], "nice": False},
        "axis": {
            "title": _axis_title(drawn.y_title),
            "values": list(range(0, 101, 20)),
            "grid": True,
        },
    }
    layers: list[dict[str, Any]] = []
    if drawn.band is not None:
        layers.append(
            {
                "data": {
                    "values": [
                        {
                            "from": drawn.band[0],
                            "to": drawn.band[1],
                            "text": "Range of acceptable prices: "
                            f"{_price_text(drawn, drawn.band[0])} to "
                            f"{_price_text(drawn, drawn.band[1])}",
                        }
                    ]
                },
                "mark": {"type": "rect", "color": drawn.band_colour or "#efefef"},
                "encoding": {
                    "x": {"field": "from", "type": "quantitative"},
                    "x2": {"field": "to"},
                    "tooltip": vega.tooltip(("text", "PMC to PME")),
                },
            }
        )
    layers += [
        {
            "data": {"values": lines},
            "mark": {"type": "line", "strokeWidth": 2},
            "params": [vega.toggle("curve")],
            "encoding": {
                "x": x,
                "y": y,
                "color": colour,
                "strokeDash": dash,
                "opacity": vega.shown(),
            },
        },
        *_hover(wide, hover_tooltip, drawn.muted, "hover"),
        *_price_points(first, drawn, 105.0, 8.0),
    ]
    view: dict[str, Any] = {
        "name": VIEW,
        "width": "container",
        "height": _height(chart, 260.0, 400.0),
        "layer": layers,
    }
    main: dict[str, Any] = view
    if drawn.trial is not None:
        trial = [
            {"price": price, "value": value, "text": _amount(value, 1, True)}
            for price, value in zip(drawn.prices, drawn.trial, strict=True)
        ]
        high = max([1.0, *[value for value in drawn.trial if value is not None]])
        levels = max((point.get("level", 0) for point in second), default=0)
        panel_top = high * 1.45 + high * 0.14 * levels
        trial_view = {
            "name": f"{VIEW}_trial",
            "width": "container",
            "height": 170,
            "layer": [
                {
                    "data": {"values": trial},
                    "mark": {"type": "line", "strokeWidth": 2, "color": drawn.ink},
                    "encoding": {
                        "x": _price_axis(drawn, drawn.x_title),
                        "y": {
                            "field": "value",
                            "type": "quantitative",
                            "scale": {"domain": [0, panel_top], "nice": False},
                            "axis": {"title": "Trial (% would buy)", "grid": True},
                        },
                    },
                },
                *_hover(
                    wide,
                    [("price_text", "Price"), ("trial", "Trial (NMS)"), ("base", "Base")],
                    drawn.muted,
                    "hover_trial",
                ),
                *_price_points(second, drawn, high * 1.3, high * 0.14, up=True),
            ],
        }
        main = {"vconcat": [view, trial_view], "spacing": 10, "resolve": {"scale": {"x": "shared"}}}
    items = [(point["name"].split(" ")[0], point["price_text"]) for point in first]
    description = (
        f"Price sensitivity (Van Westendorp): {vega.plain(drawn.heading)}. Four curves over "
        f"{len(drawn.prices)} prices; " + ", ".join(f"{a} at {b}" for a, b in items) + "."
    )
    return drawn._finish(chart, main, description)


def _price_text(drawn: DrawnPrices, price: float) -> str:
    from siamang.data import pricing

    return pricing._price(price)


def _hover(
    rows: list[dict[str, Any]], fields: list[tuple[str, str]], colour: str, name: str
) -> list[dict[str, Any]]:
    """A line at the price nearest the pointer, and every curve's share
    there in its tooltip."""

    return [
        {
            "data": {"values": rows},
            "mark": {"type": "rule", "color": colour, "strokeWidth": 1},
            "params": [
                {
                    "name": name,
                    "select": {
                        "type": "point",
                        "fields": ["price"],
                        "nearest": True,
                        "on": "pointerover",
                        "clear": "pointerout",
                    },
                }
            ],
            "encoding": {
                "x": {"field": "price", "type": "quantitative"},
                "opacity": {"condition": {"param": name, "empty": False, "value": 1}, "value": 0},
                "tooltip": vega.tooltip(*fields),
            },
        }
    ]


def _price_points(
    points: list[dict[str, Any]], drawn: DrawnPrices, y: float, step: float, *, up: bool = False
) -> list[dict[str, Any]]:
    """The points marked on a panel — a line from the axis (or, ``up``, to
    the name), a dot, and the name over the curves at its price, ``step``
    higher for each name it would otherwise touch."""

    if not points:
        return []
    for point in points:
        point["name_y"] = y + step * point.get("level", 0)
        point["rule_end"] = point["name_y"] - step * 0.45
        point["shape"] = (
            "diamond" if point["key"] == "revenue" and point["panel"] == 1 else "circle"
        )
        point["base"] = drawn.base or ""
    tooltip = vega.tooltip(("name", "Point"), ("text", "Share there"), ("base", "Base"))
    return [
        {
            "data": {"values": points},
            "mark": {"type": "rule", "color": drawn.muted, "strokeWidth": 0.8},
            "encoding": {
                "x": {"field": "price", "type": "quantitative"},
                "y": {"field": "value", "type": "quantitative"},
                "y2": {"field": "rule_end"} if up else {"datum": 0},
            },
        },
        {
            "data": {"values": points},
            "mark": {
                "type": "point",
                "filled": True,
                "size": 50,
                "color": drawn.ink,
                "stroke": "#ffffff",
                "strokeWidth": 1,
                "opacity": 1,
            },
            "encoding": {
                "x": {"field": "price", "type": "quantitative"},
                "y": {"field": "value", "type": "quantitative"},
                "shape": {"field": "shape", "type": "nominal", "scale": None},
                "tooltip": tooltip,
            },
        },
        {
            "data": {"values": points},
            "mark": {
                "type": "text",
                "fontSize": VALUE_SIZE,
                "align": "center",
                "baseline": "middle",
                "color": drawn.ink,
            },
            "encoding": {
                "x": {"field": "price", "type": "quantitative"},
                "y": {"field": "name_y", "type": "quantitative"},
                "text": {"field": "name"},
                "tooltip": tooltip,
            },
        },
    ]


def gabor_granger_spec(chart: Any, drawn: DrawnPrices) -> dict[str, Any]:
    demand, revenue = drawn.demand or [], drawn.revenue or []
    step = min(np.diff(drawn.prices)) if len(drawn.prices) > 1 else 1.0
    line, best_colour, lighter = (drawn.colours + ["#2a78d6", "#eb6834", "#f5b48f"])[:3]
    rows = []
    for price, text, share, money in zip(
        drawn.prices, drawn.price_texts, demand, revenue, strict=True
    ):
        best = drawn.best is not None and price == drawn.best
        rows.append(
            {
                "price": price,
                "from": price - step * 0.3,
                "to": price + step * 0.3,
                "price_text": text,
                "demand": share,
                "revenue": money,
                "demand_text": _amount(share, 0, True),
                "revenue_text": _amount(money, 2),
                "best": best,
                "colour": best_colour if best else lighter,
                "base": drawn.base or "",
                "description": f"{text}: {_amount(share, 0, True)} would buy, revenue "
                f"{_amount(money, 2)} per respondent",
            }
        )
    count = max(len(rows), 1)
    tooltip = vega.tooltip(
        ("price_text", "Price"),
        ("demand_text", "Would buy"),
        ("revenue_text", "Revenue per respondent"),
        ("base", "Base"),
    )
    # A tick at each price asked about, written as the picture writes it.
    x_values = {"values": drawn.prices, **vega.thousands_axis()}
    # Half a step past the first and the last price: their bars are whole.
    x_top = _price_axis(drawn, None, 1.5)
    x_top["axis"] = {"title": None, "grid": False, "labels": False, "ticks": False, **x_values}
    x_bottom = _price_axis(drawn, drawn.x_title, 1.5)
    x_bottom["axis"] = {"title": _axis_title(drawn.x_title), "grid": False, **x_values}
    top = max([10.0, *[value * 1.2 for value in demand if value is not None]])
    money_top = max([1e-9, *[value * 1.25 for value in revenue if value is not None]])
    # A value is written over each point only while the prices lie apart
    # enough for their labels, the best price's always.
    room = f"width / {count} >= 40 || datum.best"
    upper = {
        "name": VIEW,
        "width": "container",
        "height": 190,
        "data": {"values": rows},
        "layer": [
            {
                "data": {
                    "values": [
                        {
                            "price": drawn.best,
                            "text": f"highest revenue at {_price_text(drawn, drawn.best or 0)}",
                        }
                    ]
                },
                "mark": {"type": "rule", "color": drawn.muted, "strokeWidth": 0.8},
                "encoding": {"x": {"field": "price", "type": "quantitative"}},
            },
            {
                "data": {
                    "values": [
                        {
                            "price": drawn.best,
                            "text": f"highest revenue at {_price_text(drawn, drawn.best or 0)}",
                        }
                    ]
                },
                "mark": {
                    "type": "text",
                    "align": "left",
                    "baseline": "bottom",
                    "dx": 4,
                    "dy": -4,
                    "fontSize": VALUE_SIZE,
                    "color": drawn.ink,
                },
                "encoding": {
                    "x": {"field": "price", "type": "quantitative"},
                    "y": {"datum": 0, "type": "quantitative"},
                    "text": {"field": "text"},
                },
            },
            {
                "mark": {"type": "line", "strokeWidth": 2, "color": line},
                "encoding": {
                    "x": x_top,
                    "y": {
                        "field": "demand",
                        "type": "quantitative",
                        "scale": {"domain": [0, top], "nice": False},
                        "axis": {"title": _axis_title(drawn.y_title), "grid": True},
                    },
                },
            },
            {
                "mark": {
                    "type": "point",
                    "filled": True,
                    "size": 60,
                    "color": line,
                    "stroke": "#ffffff",
                    "strokeWidth": 1,
                    "opacity": 1,
                },
                "encoding": {
                    "x": {"field": "price", "type": "quantitative"},
                    "y": {"field": "demand", "type": "quantitative"},
                    "tooltip": tooltip,
                    "description": {"field": "description"},
                },
            },
            {
                "mark": {
                    "type": "text",
                    "align": "center",
                    "baseline": "bottom",
                    "dy": -7,
                    "fontSize": VALUE_SIZE,
                    "color": drawn.ink,
                    "text": {"expr": f"{room} ? datum.demand_text : ''"},
                },
                "encoding": {
                    "x": {"field": "price", "type": "quantitative"},
                    "y": {"field": "demand", "type": "quantitative"},
                },
            },
        ],
    }
    lower = {
        "name": f"{VIEW}_revenue",
        "width": "container",
        "height": 150,
        "data": {"values": rows},
        "layer": [
            {
                "mark": {"type": "rect", "stroke": "#ffffff"},
                "encoding": {
                    "x": {**x_bottom, "field": "from"},
                    "x2": {"field": "to"},
                    "y": {
                        "field": "revenue",
                        "type": "quantitative",
                        "scale": {"domain": [0, money_top], "nice": False},
                        "axis": {"title": ["Revenue per", "respondent"], "grid": True},
                    },
                    "y2": {"datum": 0},
                    "color": {"field": "colour", "type": "nominal", "scale": None, "legend": None},
                    "tooltip": tooltip,
                    "description": {"field": "description"},
                },
            },
            {
                "mark": {
                    "type": "text",
                    "align": "center",
                    "baseline": "bottom",
                    "dy": -4,
                    "fontSize": VALUE_SIZE,
                    "color": drawn.ink,
                    "text": {"expr": f"{room} ? datum.revenue_text : ''"},
                },
                "encoding": {
                    "x": {"field": "price", "type": "quantitative"},
                    "y": {"field": "revenue", "type": "quantitative"},
                },
            },
        ],
    }
    main = {"vconcat": [upper, lower], "spacing": 8, "resolve": {"scale": {"x": "shared"}}}
    items = [(row["price_text"], row["demand_text"]) for row in rows]
    description = (
        f"Price sensitivity (Gabor-Granger): {vega.plain(drawn.heading)}. Would buy at each price: "
        f"{vega.listing(items)}; highest revenue at {_price_text(drawn, drawn.best or 0)}."
    )
    return drawn._finish(chart, main, description)


__all__ = [
    "DrawnDots",
    "DrawnImage",
    "DrawnMap",
    "DrawnOverlay",
    "DrawnPrices",
    "DrawnProportion",
    "DrawnReach",
    "DrawnResult",
    "DrawnRowBars",
    "DrawnScree",
    "DrawnStack",
    "count_base",
    "finish",
    "note",
    "record_bars",
    "record_dots",
    "record_drivers",
    "record_image",
    "record_map",
    "record_overlay",
    "record_panels",
    "record_prices",
    "record_proportion",
    "record_reach",
    "record_scree",
    "record_stack",
]
