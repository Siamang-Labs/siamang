"""Each chart's Vega-Lite spec, from the numbers its picture was drawn from.

A chart records what it drew while it draws (``SurveyChart._drawn``): the
numbers, the labels, the notes and the colors, as the drawing code computed
them. The records here turn that into a spec (:mod:`siamang.reporting.vega`
has what the specs share), so the interactive chart and the picture are drawn
from one set of numbers and cannot disagree. Nothing here reads the data
again.
"""

from __future__ import annotations

import functools
import math
import warnings
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from siamang.reporting import vega

# ─── shared ──────────────────────────────────────────────────────────────────


def recording(record: Callable[..., None]) -> Callable[..., None]:
    """A recording never costs a chart its picture: one that fails leaves the
    chart without an interactive form (``vega_lite()`` is None), and a
    warning says why."""

    @functools.wraps(record)
    def run(chart: Any, *args: Any, **kwargs: Any) -> None:
        try:
            record(chart, *args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - the picture is drawn regardless
            chart._drawn = None
            warnings.warn(
                f"{type(chart).__name__}: no interactive chart ({type(exc).__name__}: {exc}); "
                "its picture is drawn.",
                RuntimeWarning,
                stacklevel=3,
            )

    return run


def group_bases(groups: Any, weights: Any, codes: list[Any], *, text: bool = False) -> list[Any]:
    """Each group's base, in ``codes``' order: the respondents in it and — a
    Series of ``weights`` aligned with ``groups``, or None — their weight;
    as a tooltip writes it with ``text``."""

    sizes = groups.groupby(groups).size()
    totals = None if weights is None else weights.groupby(groups).sum()
    bases = [(int(sizes[code]), None if totals is None else float(totals[code])) for code in codes]
    return [vega.base_text(n, weighted) for n, weighted in bases] if text else bases


#: The size of a value written on or beside a mark, in pixels.
VALUE_SIZE = 10.5


def _text_px(text: str) -> float:
    """The width of ``text`` at :data:`VALUE_SIZE`, estimated (the face is
    the browser's; a little wide rather than narrow)."""

    return len(str(text)) * VALUE_SIZE * 0.6


#: The name of the view a chart is drawn in, which names its scales
#: (``chart_x``) wherever the spec puts it: an expression reads them by name.
VIEW = "chart"


def _scale(channel: str) -> str:
    """The name of the scale of ``channel`` in a chart's view, for an
    expression: ``chart_x`` — but ``xOffset``, which Vega-Lite keeps in the
    group of each position, under its own name."""

    return channel if channel.endswith("Offset") else f"{VIEW}_{channel}"


def _turned(channel: str, least: float) -> str:
    """The expression that says a bar of the band scale of ``channel`` is too
    narrow for a value ``least`` pixels wide: the value is turned."""

    return f"(bandwidth('{_scale(channel)}') < {least:.0f})"


def _fits(along: str, length: str, across: str, thickness: str) -> str:
    """The expression that says a segment (a row's ``start`` to ``end`` on the
    scale of ``along``) is, as drawn, at least ``length`` pixels long and its
    band at least ``thickness`` thick: its value can be written in it."""

    scale = f"'{VIEW}_{along}'"
    return (
        f"(abs(scale({scale}, datum.end) - scale({scale}, datum.start)) >= {length}"
        f" && bandwidth('{VIEW}_{across}') >= {thickness})"
    )


def _ink_encoding(rows: list[dict[str, Any]], text: str) -> dict[str, Any]:
    """The color of a value written on its segment or slice: each row's
    ``ink`` (white, black or the text color) as a condition, so it takes no
    scale and no legend of its own."""

    inks = sorted({row["ink"] for row in rows if row.get("ink")} - {text})
    return {
        "condition": [{"test": f"datum.ink === '{ink}'", "value": ink} for ink in inks],
        "value": text,
    }


def _amount(value: float) -> str:
    """A number read off an axis (a quartile, a point): thousands separated,
    two decimals when it has any."""

    value = float(value)
    if abs(value) >= 1000 or value.is_integer():
        return f"{value:,.0f}"
    return f"{value:,.2f}"


#: What an interactive chart that zooms says under its notes.
ZOOM_HINT = "Drag to move the view; hold Shift and scroll to zoom; double-click to reset."


def _zoom(encodings: str = "x,y") -> dict[str, Any]:
    """Zoom and pan bound to the scales: the wheel zooms only with Shift held,
    so a page scrolled past the chart is not caught by it."""

    return {
        "name": "zoom",
        "select": {
            "type": "interval",
            "encodings": encodings.split(","),
            "zoom": "wheel![event.shiftKey]",
        },
        "bind": "scales",
    }


def _ink(chart: Any, fill: str) -> str:
    """Text that reads on ``fill``, as the picture writes it there."""

    from siamang.reporting import chart_theme

    colours = getattr(chart, "_drawn_with", None)
    if isinstance(colours, chart_theme.ChartColours):
        return colours.ink_on(fill)
    return "#ffffff" if chart_theme.luminance(fill) < 0.36 else "#262626"


def _figure_px(chart: Any) -> tuple[float, float]:
    """The chart's figure size in CSS pixels (:data:`vega.PX_PER_INCH`)."""

    width, height = chart.figsize
    return float(width) * vega.PX_PER_INCH, float(height) * vega.PX_PER_INCH


def _label_lines(text: str, width: int) -> str:
    """A position's label wrapped to ``width`` characters, a group's
    "(n = …)" on a line of its own."""

    head, _, tail = str(text).partition("\n(n = ")
    lines = vega.wrap(" ".join(head.split("\n")), width)
    if tail:
        lines.append(f"(n = {tail}")
    return "\n".join(lines)


def _legend(title: str | None, labels: list[str], orient: str = "top") -> dict[str, Any]:
    """A legend over the plot (or under it), its entries in as many columns
    as the width the chart is drawn at holds: a legend beside the plot left a
    chart in a narrow column (a dashboard's tile) no room for its bars."""

    longest = max((len(str(label)) for label in labels), default=8)
    entry = min(220.0, longest * 6.4) + 30.0
    return {
        "title": title or None,
        "orient": orient,
        "direction": "horizontal",
        "columns": {"expr": f"max(1, min({len(labels)}, floor(width / {entry:.0f})))"},
        "labelLimit": 220,
    }


def _height(chart: Any, least: float = 220.0, most: float = 420.0) -> float:
    """A plot's height for a figure of the chart's size."""

    return float(min(most, max(least, _figure_px(chart)[1] * 0.7)))


# ─── bars ────────────────────────────────────────────────────────────────────


@dataclass
class DrawnBars:
    """What a bar chart drew (:class:`siamang.reporting.bars.Bars`), in the
    colors and the direction it was drawn in."""

    bars: Any
    colours: list[str]
    horizontal: bool
    show_values: bool
    #: The color of the bar that combines answers as Other (one series).
    other: str | None = None
    #: One series whose bars are each in a color of their own (the chart
    #: BarChart has always drawn colors a count's bars through its palette).
    position_colours: list[str] | None = None
    #: The chart BarChart has always drawn: its values written as it writes
    #: them (1234, not 1,234; a mean to two decimals).
    classic: bool = False

    def spec(self, chart: Any) -> dict[str, Any]:
        return bar_spec(chart, self)


def _value_text(value: float, kind: str, classic: bool = False) -> str:
    """A value as the picture writes it on its bar."""

    if classic:
        from siamang.reporting.charts import _format_value

        return f"{value:.2f}" if kind == "mean" else _format_value(float(value))
    from siamang.reporting.bars import value_text

    return value_text(value, kind)


def bar_spec(chart: Any, drawn: DrawnBars) -> dict[str, Any]:
    bars = drawn.bars
    values = np.asarray(bars.values, dtype=float)
    positions, count = values.shape
    horizontal = drawn.horizontal
    width_px, _ = _figure_px(chart)
    if horizontal:
        chars = 20  # a narrow chart keeps room for its bars
    else:
        slot = 0.8 * width_px / max(positions, 1)
        chars = int(max(8, min(24, slot / 6.5)))
    labels = vega.unique([_label_lines(text, chars) for text in bars.positions])
    series = [str(name) for name in bars.series]
    bases = list(getattr(bars, "base_texts", []) or [])
    kind = bars.kind
    intervals = bars.lower is not None and bars.upper is not None
    confidence = getattr(chart, "confidence", None)
    level = f"{confidence * 100:g}%" if isinstance(confidence, float | int) else ""
    rows: list[dict[str, Any]] = []
    stacked = bool(bars.stacked)
    totals = np.zeros(positions)
    ends = []
    for index in range(positions):
        running = 0.0
        for column in range(count):
            value = values[index, column]
            finite = value == value
            row: dict[str, Any] = {
                "label": labels[index],
                "position": vega.plain(bars.positions[index]),
                "series": series[column],
                "value": vega.number(value),
                "text": _value_text(value, kind, drawn.classic) if finite else "no value",
                "order": column,
            }
            if bases:
                row["base"] = bases[index] if index < len(bases) else bases[-1]
            colour = drawn.colours[column] if column < len(drawn.colours) else "#888888"
            if count == 1 and drawn.position_colours is not None:
                colour = drawn.position_colours[index]
            if count == 1 and bars.other_position is not None and index == bars.other_position:
                colour = drawn.other or colour
            row["colour"] = colour
            if stacked:
                size = float(value) if finite else 0.0
                row["start"], row["end"] = running, running + size
                row["mid"] = running + size / 2.0
                row["ink"] = _ink(chart, colour)
                running += size
            if intervals:
                low, high = bars.lower[index, column], bars.upper[index, column]
                if low == low and high == high:
                    row["lower"], row["upper"] = vega.number(low), vega.number(high)
                    row["interval"] = f"{_value_text(low, kind)} to {_value_text(high, kind)}"
                else:
                    row["interval"] = "none"
            end = value if finite else 0.0
            if intervals and row.get("upper") is not None and finite:
                end = max(value, row["upper"]) if value >= 0 else min(value, row["lower"])
            row["tip"] = vega.number(end)
            ends.append(end)
            if bars.marks is not None:
                row["letters"] = bars.marks[index][column]
                row["higher"] = _higher_than(row["letters"], bars.positions)
            rows.append(row)
        totals[index] = running
    along, across = ("x", "y") if horizontal else ("y", "x")
    offset = "yOffset" if horizontal else "xOffset"
    value_axis: dict[str, Any] = {"title": bars.value_label, "grid": True}
    if kind == "percent":
        value_axis.update(vega.percent_axis())
    else:
        value_axis.update(vega.thousands_axis())
    scale: dict[str, Any] = {}
    if bars.full:
        scale["domain"] = [0, 100]
    else:
        finite_ends = [end for end in ends if end == end]
        high = max([*finite_ends, *(totals if stacked else [])], default=0.0)
        low = min(finite_ends, default=0.0)
        room = 1.14 if drawn.show_values or bars.marks is not None else 1.02
        if high > 0:
            scale["domainMax"] = float(high * room)
        if low < 0:
            scale["domainMin"] = float(low * room)
    position_axis: dict[str, Any] = {
        "title": bars.position_label or None,
        "labelExpr": vega.multiline_labels(),
        "labelAngle": 0,
        "grid": False,
        "ticks": False,
        "labelPadding": 6,
    }
    if horizontal:
        position_axis["labelAlign"] = "right"
        position_axis["labelLimit"] = 170
    else:
        # A label no wider than its band: in a narrow chart neighbors' labels
        # are cut short (the tooltip names each bar) rather than run together.
        position_axis["labelLimit"] = {"expr": f"max(bandwidth('{VIEW}_{across}') + 8, 36)"}
    encoding: dict[str, Any] = {
        across: {
            "field": "label",
            "type": "nominal",
            "sort": labels,
            "axis": position_axis,
            "scale": {"paddingInner": 0.25 if count == 1 or stacked else 0.18},
        }
    }
    if count > 1 and not stacked:
        encoding[offset] = {"field": "series", "type": "nominal", "sort": series}
    tooltip = [("position", bars.position_label or "Answer")]
    if count > 1:
        tooltip.append(("series", bars.legend_title or "Series"))
    tooltip.append(("text", bars.value_label))
    if intervals:
        tooltip.append(("interval", f"{level} confidence interval".strip()))
    if bars.marks is not None:
        tooltip.append(("higher", "Significantly higher than"))
    if bases:
        tooltip.append(("base", "Base"))
    bar_encoding: dict[str, Any] = {
        "tooltip": vega.tooltip(*tooltip),
        "description": {"field": "description"},
    }
    if stacked:
        bar_encoding[along] = {
            "field": "start",
            "type": "quantitative",
            "axis": value_axis,
            "scale": scale,
        }
        bar_encoding[f"{along}2"] = {"field": "end"}
    else:
        bar_encoding[along] = {
            "field": "value",
            "type": "quantitative",
            "axis": value_axis,
            "scale": scale,
        }
    if count > 1:
        domain, range_ = list(series), list(drawn.colours[:count])
        bar_encoding["color"] = {
            "field": "series",
            "type": "nominal",
            "scale": {"domain": domain, "range": range_},
            "legend": _legend(bars.legend_title, domain),
        }
        bar_encoding["opacity"] = vega.shown()
    else:
        bar_encoding["color"] = {
            "field": "colour",
            "type": "nominal",
            "scale": None,
            "legend": None,
        }
    for row in rows:
        parts = [row["position"]]
        if count > 1:
            parts.append(row["series"])
        parts.append(row["text"])
        row["description"] = ": ".join(parts[:-1]) + f", {parts[-1]}"
    bar_layer: dict[str, Any] = {
        "mark": {
            "type": "bar",
            "stroke": "#ffffff" if count > 1 else None,
            "strokeWidth": 0.8 if count > 1 else 0,
        },
        "encoding": bar_encoding,
    }
    if count > 1:
        bar_layer["params"] = [vega.toggle("series")]
    layers = [bar_layer]
    look = vega.look_of(chart)
    if intervals and not stacked:
        layers.append(
            {
                "transform": [{"filter": "isValid(datum.lower)"}],
                "mark": {"type": "rule", "strokeWidth": 1.2, "color": look.text},
                "encoding": {
                    along: {"field": "lower", "type": "quantitative"},
                    f"{along}2": {"field": "upper"},
                    **({"opacity": vega.shown(1, 0)} if count > 1 else {}),
                },
            }
        )
    marked = bars.marks is not None and any(mark for row in bars.marks for mark in row)
    fade = {"opacity": vega.shown(1, 0)} if count > 1 else {}
    if (drawn.show_values or marked) and not stacked:
        # What is written past each bar's end: its value (and, across, its
        # letters after it), or its letters alone when values are off.
        for row in rows:
            letters = row.get("letters", "") if marked else ""
            if row["value"] is None:
                row["label_text"] = ""
            elif drawn.show_values:
                row["label_text"] = row["text"] + (f"  {letters}" if horizontal and letters else "")
            else:
                row["label_text"] = letters
            row["text_px"] = _text_px(row["text"]) if drawn.show_values else 0.0
        band = offset if count > 1 else across
        # A value is not written on a bar thinner than its text is tall: the
        # values of neighbors would run together (the picture leaves them off
        # too), and the tooltip gives each.
        hidden = f"(bandwidth('{_scale(band)}') < {9 if horizontal else 11})"
        mark: dict[str, Any] = {
            "type": "text",
            "fontSize": VALUE_SIZE,
            "color": look.text,
            "text": {"expr": f"{hidden} ? '' : datum.label_text"},
        }
        widest = max((_text_px(row["label_text"]) for row in rows), default=0.0)
        if horizontal:
            mark.update(align="left", baseline="middle", dx=4)
        else:
            # Upright over its bar when the bar is as wide as the value, else
            # turned to read upward — as the picture turns its values.
            turned = _turned(band, widest + 4)
            mark.update(
                angle={"expr": f"{turned} ? 270 : 0"},
                align={"expr": f"{turned} ? 'left' : 'center'"},
                baseline={"expr": f"{turned} ? 'middle' : 'bottom'"},
                dx={"expr": f"{turned} ? 4 : 0"},
                dy={"expr": f"{turned} ? 0 : -4"},
            )
        layers.append(
            {
                "transform": [{"filter": "isValid(datum.value)"}],
                "mark": mark,
                "encoding": {along: {"field": "tip", "type": "quantitative"}, **fade},
            }
        )
        if marked and not horizontal and drawn.show_values:
            # The letters after the value: over it upright, further along it turned.
            layers.append(
                {
                    "transform": [{"filter": "isValid(datum.value) && datum.letters"}],
                    "mark": {
                        "type": "text",
                        "fontSize": VALUE_SIZE,
                        "fontWeight": "bold",
                        "color": look.text,
                        "text": {"expr": f"{hidden} ? '' : datum.letters"},
                        "angle": {"expr": f"{turned} ? 270 : 0"},
                        "align": {"expr": f"{turned} ? 'left' : 'center'"},
                        "baseline": {"expr": f"{turned} ? 'middle' : 'bottom'"},
                        "dx": {"expr": f"{turned} ? datum.text_px + 10 : 0"},
                        "dy": {"expr": f"{turned} ? 0 : -{VALUE_SIZE + 6:g}"},
                    },
                    "encoding": {along: {"field": "tip", "type": "quantitative"}, **fade},
                }
            )
    if stacked and drawn.show_values:
        # A segment's value inside it where the segment, as drawn, holds it.
        for row in rows:
            row["text_px"] = _text_px(row["text"])
        fits = (
            _fits(along, "datum.text_px + 6", across, "13")
            if horizontal
            else _fits(along, "14", across, "datum.text_px + 4")
        )
        layers.append(
            {
                "transform": [{"filter": "datum.value > 0"}],
                "mark": {
                    "type": "text",
                    "fontSize": VALUE_SIZE,
                    "align": "center",
                    "baseline": "middle",
                    "text": {"expr": f"{fits} ? datum.text : ''"},
                },
                "encoding": {
                    along: {"field": "mid", "type": "quantitative"},
                    "color": _ink_encoding(rows, look.text),
                    **fade,
                },
            }
        )
        if kind == "count" and not bars.full:
            total_rows = [
                {"label": labels[index], "total": float(totals[index])}
                for index in range(positions)
            ]
            for row in total_rows:
                row["text"] = _value_text(row["total"], kind, drawn.classic)
                row["text_px"] = _text_px(row["text"])
            # Each stack's total past its end, where the stack is as wide.
            room = "9" if horizontal else "datum.text_px"
            mark = {
                "type": "text",
                "fontSize": VALUE_SIZE,
                "color": look.text,
                "text": {"expr": f"bandwidth('{VIEW}_{across}') < {room} ? '' : datum.text"},
            }
            if horizontal:
                mark.update(align="left", baseline="middle", dx=4)
            else:
                mark.update(align="center", baseline="bottom", dy=-4)
            layers.append(
                {
                    "data": {"values": total_rows},
                    "mark": mark,
                    "encoding": {along: {"field": "total", "type": "quantitative"}},
                }
            )
    main: dict[str, Any] = {
        "name": VIEW,
        "width": "container",
        "height": _bars_height(chart, positions, count if not stacked else 1)
        if horizontal
        else _height(chart),
        "data": {"values": rows},
        "encoding": encoding,
        "layer": layers,
    }
    what = "Stacked bar chart" if stacked else "Bar chart"
    if count > 1:
        items = [
            (f"{row['position']}, {row['series']}", row["text"])
            for row in rows
            if row["value"] is not None
        ]
    else:
        items = [(row["position"], row["text"]) for row in rows if row["value"] is not None]
    description = f"{what}: {vega.plain(bars.title)}. {vega.listing(items, 24)}."
    return vega.finish(
        chart,
        main,
        heading=bars.title,
        notes=list(bars.notes),
        description=description,
        kind="bar",
    )


def _higher_than(letters: str, positions: list[str]) -> str:
    """A bar's significance letters as the groups they name — "North (A),
    East (C)" — from the groups' labels, which carry their letters; "none"
    without letters."""

    import re

    if not letters:
        return "none"
    named = {}
    for position in positions:
        found = re.match(r"^(.*) \(([A-Z]|#\d+)\)$", vega.plain(position))
        if found:
            named[found.group(2)] = found.group(0)
    marks = re.findall(r"#\d+|[A-Z]", letters)
    return ", ".join(named.get(mark, mark) for mark in marks)


def _bars_height(chart: Any, positions: int, count: int) -> float:
    """Horizontal bars: a row per position, as tall as its bars need."""

    row = max(26.0, count * 14.0 + 12.0)
    return float(max(_height(chart, 160.0, 300.0), positions * row))


# ─── histogram ───────────────────────────────────────────────────────────────


@dataclass
class DrawnHistogram:
    histogram: Any
    colour: str
    bases: list[str] = field(default_factory=list)

    def spec(self, chart: Any) -> dict[str, Any]:
        return histogram_spec(chart, self)


def histogram_spec(chart: Any, drawn: DrawnHistogram) -> dict[str, Any]:
    from siamang.reporting.bars import _number

    histogram = drawn.histogram
    edges = [float(edge) for edge in histogram.edges]
    kind = histogram.kind
    panels = list(histogram.panels)
    top = max((float(np.nanmax(heights, initial=0.0)) for heights in histogram.heights), default=0)
    value_axis: dict[str, Any] = {"title": histogram.value_label, "grid": True}
    value_axis.update(vega.percent_axis() if kind == "percent" else vega.thousands_axis())
    x_axis: dict[str, Any] = {"title": None, "grid": False}
    x_axis.update(vega.thousands_axis())
    if histogram.explicit and len(edges) <= 25:
        x_axis["values"] = edges
    views = []
    many = len(panels) > 1
    for index, (heights, panel) in enumerate(zip(histogram.heights, panels, strict=True)):
        base = drawn.bases[index] if index < len(drawn.bases) else ""
        rows = []
        for left, right, height in zip(edges[:-1], edges[1:], heights, strict=True):
            rows.append(
                {
                    "start": left,
                    "end": right,
                    "value": vega.number(height),
                    "text": _value_text(float(height), kind),
                    "bin": f"{_number(left)} to {_number(right)}",
                    "base": base,
                    "description": f"{_number(left)} to {_number(right)}: "
                    f"{_value_text(float(height), kind)}",
                }
            )
        tooltip = [("bin", "Bin"), ("text", histogram.value_label)]
        if base:
            tooltip.append(("base", "Base"))
        view: dict[str, Any] = {
            "name": f"{VIEW}_{index}" if many else VIEW,
            "width": "container",
            "height": 110.0 if many else _height(chart),
            "data": {"values": rows},
            "mark": {"type": "bar", "color": drawn.colour, "stroke": "#ffffff", "strokeWidth": 0.6},
            "encoding": {
                "x": {
                    "field": "start",
                    "type": "quantitative",
                    "scale": {"domain": [edges[0], edges[-1]], "nice": False, "zero": False},
                    "axis": x_axis,
                },
                "x2": {"field": "end"},
                "y": {
                    "field": "value",
                    "type": "quantitative",
                    "scale": {"domain": [0, top * 1.05 if top > 0 else 1]},
                    # A panel's axis says it shortly: its group is over it.
                    "axis": {**value_axis, "title": _short_value(histogram)}
                    if many
                    else value_axis,
                },
                "y2": {"datum": 0},
                "tooltip": vega.tooltip(*tooltip),
                "description": {"field": "description"},
            },
        }
        if many:
            view["title"] = {"text": panel, "fontSize": 12, "fontWeight": "normal", "offset": 4}
        views.append(view)
    main = {"vconcat": views, "spacing": 18} if many else views[0]
    description = f"Histogram: {vega.plain(histogram.title)}, {len(edges) - 1} bins" + (
        f", one panel for each of {len(panels)} groups." if many else "."
    )
    return vega.finish(
        chart,
        main,
        heading=histogram.title,
        notes=list(histogram.notes),
        description=description,
        kind="histogram",
    )


def _short_value(histogram: Any) -> str:
    short = {"count": "Count", "percent": "% of the group"}[histogram.kind]
    if histogram.kind == "count" and histogram.value_label.startswith("Weighted"):
        short = "Weighted count"
    return short


# ─── donut ───────────────────────────────────────────────────────────────────


@dataclass
class DrawnDonut:
    donut: Any
    colours: list[str]
    show_values: bool

    def spec(self, chart: Any) -> dict[str, Any]:
        return donut_spec(chart, self)


def donut_spec(chart: Any, drawn: DrawnDonut) -> dict[str, Any]:
    from siamang.reporting.bars import RING
    from siamang.reporting.chart_parts import count_text

    donut = drawn.donut
    names = [str(name) for name in donut.names]
    base = vega.base_text(donut.respondents, donut.weighted_base)
    rows = []
    for index, (name, share) in enumerate(zip(names, donut.shares, strict=True)):
        colour = drawn.colours[index]
        rows.append(
            {
                "answer": name,
                "share": vega.number(share),
                "text": f"{float(share):.1f}%",
                "order": index,
                "base": base,
                "ink": _ink(chart, colour),
                # The slice's value on it where the slice is wide enough.
                "inside": bool(float(share) >= 6.0),
                "description": f"{name}: {float(share):.1f}%",
            }
        )
    height = _height(chart, 260.0, 380.0)
    outer = height / 2.0 - 26.0
    inner = outer * (1.0 - RING)
    look = vega.look_of(chart)
    theta = {"field": "share", "type": "quantitative", "stack": True}
    order = {"field": "order", "type": "quantitative", "sort": "ascending"}
    slices: dict[str, Any] = {
        "mark": {
            "type": "arc",
            "outerRadius": outer,
            "innerRadius": inner,
            "stroke": "#ffffff",
            "strokeWidth": 1.5,
        },
        "params": [vega.toggle("answer")],
        "encoding": {
            "theta": theta,
            "order": order,
            "color": {
                "field": "answer",
                "type": "nominal",
                "scale": {"domain": names, "range": drawn.colours},
                "legend": _legend(donut.legend_title, names),
            },
            "opacity": vega.shown(),
            "tooltip": vega.tooltip(("answer", "Answer"), ("text", "Share"), ("base", "Base")),
            "description": {"field": "description"},
        },
    }
    layers: list[dict[str, Any]] = [slices]
    if drawn.show_values:
        # Each slice's percentage on it where it is wide enough, else just
        # outside the ring — the picture joins those to their slices by a line.
        layers.append(
            {
                "transform": [{"filter": "datum.inside"}],
                "mark": {
                    "type": "text",
                    "radius": (outer + inner) / 2.0,
                    "fontSize": VALUE_SIZE,
                    "align": "center",
                    "baseline": "middle",
                },
                "encoding": {
                    "theta": theta,
                    "order": order,
                    "text": {"field": "text"},
                    "color": _ink_encoding(rows, look.text),
                    "opacity": vega.shown(1, 0),
                },
            }
        )
        layers.append(
            {
                "transform": [{"filter": "!datum.inside"}],
                "mark": {
                    "type": "text",
                    "radius": outer + 14.0,
                    "fontSize": VALUE_SIZE,
                    "align": "center",
                    "baseline": "middle",
                    "color": look.text,
                },
                "encoding": {
                    "theta": theta,
                    "order": order,
                    "text": {"field": "text"},
                    "opacity": vega.shown(1, 0),
                },
            }
        )
    centre = [f"{donut.respondents:,}", "respondents"]
    if donut.weighted_base is not None:
        centre.append(f"weighted {count_text(donut.weighted_base)}")
    # The base in the hole: at the center, where a radius of 0 puts a mark.
    layers.append(
        {
            "data": {"values": [{"lines": centre}]},
            "mark": {
                "type": "text",
                "radius": 0,
                "align": "center",
                "baseline": "middle",
                "fontSize": 12,
                "lineHeight": 16,
                "color": look.text,
                "aria": False,
            },
            "encoding": {
                "text": {"field": "lines"},
                "theta": {"datum": 0, "type": "quantitative"},
            },
        }
    )
    main = {
        "name": VIEW,
        "width": "container",
        "height": height,
        "data": {"values": rows},
        "layer": layers,
    }
    items = [(row["answer"], row["text"]) for row in rows]
    description = f"Donut chart: {vega.plain(donut.title)}. {vega.listing(items)}. {base}."
    return vega.finish(
        chart,
        main,
        heading=donut.title,
        notes=list(donut.notes),
        description=description,
        kind="donut",
    )


# ─── Likert ──────────────────────────────────────────────────────────────────


@dataclass
class DrawnLikert:
    """What a Likert chart drew: its items' shares in chart order, the scale,
    the colors of its answers, and the half-width of its axis."""

    rows: list[dict[str, Any]]
    items: list[str]
    scale: Any
    colours: dict[Any, str]
    limit: float
    side: bool
    title: str
    notes: list[str]
    axis: str
    show_values: bool

    def spec(self, chart: Any) -> dict[str, Any]:
        return likert_spec(chart, self)


#: The least plot width (pixels) at which a Likert chart writes its top-2 and
#: bottom-2 columns.
NARROW_LIKERT = 420


def likert_spec(chart: Any, drawn: DrawnLikert) -> dict[str, Any]:
    scale = drawn.scale
    limit = float(drawn.limit)
    pad = 0.3 * limit  # room at either end for the bottom-2 and top-2 shares
    edge = limit + pad
    look = vega.look_of(chart)
    width_px, _ = _figure_px(chart)
    items = vega.unique(
        [
            _label_lines(f"{name}\n(n = {row['n']:,})" if name else f"(n = {row['n']:,})", 20)
            for name, row in zip(drawn.items, drawn.rows, strict=True)
        ]
    )
    labels = [str(scale.labels[code]) for code in scale.codes]
    side = drawn.side
    neutral = scale.neutral
    # The neutral answer apart: a panel of its own right of the top-2 shares,
    # a fifth of the width, on its own scale (as the picture's).
    x0 = edge + 0.1 * limit
    room = 2.0 * edge / 5.0
    top_neutral = max((row["shares"][neutral] for row in drawn.rows), default=0.0) if side else 0
    side_max = max(10.0, math.ceil(top_neutral * 1.35 / 10.0) * 10.0) if side else 1.0
    per = room / side_max
    rows = []
    for item, row in zip(items, drawn.rows, strict=True):
        half = row["shares"][neutral] / 2.0 if neutral is not None and not side else 0.0
        starts: dict[Any, float] = {}
        running = -half
        for code in reversed(scale.negative):
            running -= row["shares"][code]
            starts[code] = running
        running = half
        for code in scale.positive:
            starts[code] = running
            running += row["shares"][code]
        if neutral is not None:
            starts[neutral] = x0 if side else -half
        base = vega.base_text(row["n"], row["weighted"] if chart.data.weight is not None else None)
        boxes = f"{row['top']:.0f}% / {row['bottom']:.0f}%"
        for order, code in enumerate(scale.codes):
            share = float(row["shares"][code])
            colour = drawn.colours[code]
            apart = side and code == neutral
            start = starts[code]
            end = start + (share * per if apart else share)
            text = f"{share:.0f}%"
            rows.append(
                {
                    "item": item,
                    "name": vega.plain(item) if drawn.items[0] else "",
                    "answer": str(scale.labels[code]),
                    "share": vega.number(share),
                    "text": text,
                    "start": start,
                    "end": end,
                    "mid": (start + end) / 2.0,
                    "order": order,
                    "base": base,
                    "boxes": boxes,
                    "ink": _ink(chart, colour),
                    "text_px": _text_px(text),
                    "description": f"{vega.plain(item) or drawn.title}: {scale.labels[code]} {text}",
                }
            )
    ends = [
        {
            "item": item,
            "top": f"{row['top']:.0f}%",
            "bottom": f"{row['bottom']:.0f}%",
        }
        for item, row in zip(items, drawn.rows, strict=True)
    ]
    step = next(
        (
            step
            for step in (10.0, 20.0, 25.0, 50.0)
            if (2 * (limit // step) + 1) * 44.0 <= width_px * 0.6
        ),
        50.0,
    )
    ticks = [float(value * step) for value in range(-int(limit // step), int(limit // step) + 1)]
    far = x0 + room if side else edge
    if side:
        ticks += [x0, x0 + room]
    label_expr = "format(abs(datum.value), '.0f') + '%'"
    if side:
        label_expr = (
            f"datum.value >= {x0 - 1e-6!r} ? format((datum.value - {x0!r}) / {per!r}, '.0f') + '%'"
            f" : {label_expr}"
        )
    y = {
        "field": "item",
        "type": "nominal",
        "sort": items,
        "axis": {
            "title": None,
            "labelExpr": vega.multiline_labels(),
            "labelLimit": 170,
            "ticks": False,
            "grid": False,
            "domain": False,
        },
        "scale": {"paddingInner": 0.34},
    }
    box = "Top-2" if scale.box == 2 else "Top box"
    low_box = "Bottom-2" if scale.box == 2 else "Bottom box"
    tooltip = vega.tooltip(
        ("answer", "Answer"),
        ("text", "Share"),
        ("boxes", f"{box} / {low_box.lower()}"),
        ("base", "Base"),
    )
    if drawn.items[0]:
        tooltip.insert(0, {"field": "name", "type": "nominal", "title": "Item"})
    segments: dict[str, Any] = {
        "mark": {"type": "bar", "stroke": "#ffffff", "strokeWidth": 0.8},
        "params": [vega.toggle("answer")],
        "encoding": {
            "y": y,
            "x": {
                "field": "start",
                "type": "quantitative",
                "scale": {"domain": [-edge, far], "nice": False, "zero": False},
                "axis": {
                    "title": drawn.axis,
                    "values": ticks,
                    "labelExpr": label_expr,
                    "grid": True,
                },
            },
            "x2": {"field": "end"},
            "color": {
                "field": "answer",
                "type": "nominal",
                "scale": {"domain": labels, "range": [drawn.colours[code] for code in scale.codes]},
                "legend": _legend(None, labels),
            },
            "order": {"field": "order", "type": "quantitative"},
            "opacity": vega.shown(),
            "tooltip": tooltip,
            "description": {"field": "description"},
        },
    }
    layers: list[dict[str, Any]] = [
        segments,
        {
            "data": {"values": [{}]},
            "mark": {"type": "rule", "color": look.text, "strokeWidth": 1},
            "encoding": {"x": {"datum": 0, "type": "quantitative"}},
        },
    ]
    if drawn.show_values:
        # Each answer's share in its segment where the segment, as drawn, holds it.
        fits = _fits("x", "datum.text_px + 5", "y", "13")
        layers.append(
            {
                "transform": [{"filter": "datum.share > 0"}],
                "mark": {
                    "type": "text",
                    "fontSize": VALUE_SIZE,
                    "baseline": "middle",
                    "text": {"expr": f"{fits} ? datum.text : ''"},
                },
                "encoding": {
                    "y": {"field": "item", "type": "nominal", "sort": items},
                    "x": {"field": "mid", "type": "quantitative"},
                    "color": _ink_encoding(rows, look.text),
                    "opacity": vega.shown(1, 0),
                },
            }
        )
    # The top-2 and bottom-2 shares in columns at the two ends — left out of a
    # chart drawn too narrow to hold them beside its bars (the tooltip gives
    # them).
    narrow = f"width < {NARROW_LIKERT}"
    for value, field_name, align in ((-edge, "bottom", "left"), (edge, "top", "right")):
        layers.append(
            {
                "data": {"values": ends},
                "mark": {
                    "type": "text",
                    "fontSize": VALUE_SIZE,
                    "align": align,
                    "baseline": "middle",
                    "color": look.text,
                    "dx": 6 if align == "left" else -6,
                    "text": {"expr": f"{narrow} ? '' : datum.{field_name}"},
                },
                "encoding": {
                    "y": {"field": "item", "type": "nominal", "sort": items},
                    "x": {"datum": value, "type": "quantitative"},
                },
            }
        )
    headers = [(-edge, low_box, "left", True), (edge, box, "right", True)]
    if side:
        headers.append((x0 + room / 2.0, str(scale.labels[neutral]), "center", False))
    for value, text, align, column in headers:
        layers.append(
            {
                "data": {"values": [{"text": text}]},
                "mark": {
                    "type": "text",
                    "fontSize": VALUE_SIZE,
                    "align": align,
                    "baseline": "bottom",
                    "color": look.muted,
                    "dy": -6,
                    "dx": 6 if align == "left" else (-6 if align == "right" else 0),
                    "text": {"expr": f"{narrow} ? '' : datum.text" if column else "datum.text"},
                },
                "encoding": {
                    "x": {"datum": value, "type": "quantitative"},
                    "y": {"value": 0},
                },
            }
        )
    count = len(drawn.rows)
    lines = max(item.count("\n") + 1 for item in items)
    main = {
        "name": VIEW,
        "width": "container",
        "height": float(count * max(34.0, min(60.0, lines * 15.0 + 12.0))),
        "data": {"values": rows},
        "layer": layers,
    }
    items_text = [
        (
            vega.plain(item) or "the item",
            f"{box.lower()} {row['top']:.0f}%, " f"{low_box.lower()} {row['bottom']:.0f}%",
        )
        for item, row in zip(items, drawn.rows, strict=True)
    ]
    description = (
        f"Likert chart: {vega.plain(drawn.title)}, {len(drawn.rows)} "
        f"{'item' if count == 1 else 'items'} on a scale from {labels[0]} to {labels[-1]}. "
        f"{vega.listing(items_text)}."
    )
    return vega.finish(
        chart,
        main,
        heading=drawn.title,
        notes=list(drawn.notes),
        description=description,
        kind="likert",
    )


# ─── heatmap ─────────────────────────────────────────────────────────────────


@dataclass
class DrawnMatrix:
    """What a heatmap drew: a value per row and column, its color map and the
    text written in each cell."""

    values: np.ndarray
    rows: list[str]
    columns: list[str]
    row_names: list[str]
    column_names: list[str]
    texts: list[list[str]]
    #: The color map sampled at even steps, and the values the steps stand for.
    stops: list[str]
    domain: list[float]
    annotate: bool
    title: str
    notes: list[str]
    legend_title: str | None
    x_title: str | None
    value_title: str
    #: Each column's base as a tooltip gives it, or one for every cell.
    bases: list[str]
    subtitle: list[str] | None = None
    kind: str = "heatmap"
    #: Each cell's fill as the picture drew it (for the ink written on it).
    fills: list[list[str]] = field(default_factory=list)

    def spec(self, chart: Any) -> dict[str, Any]:
        return matrix_spec(chart, self)


@recording
def record_matrix(
    chart: Any,
    ax: Any,
    values: Any,
    *,
    rows: list[str],
    columns: list[str],
    row_names: list[str] | None = None,
    column_names: list[str] | None = None,
    text: Any,
    title: str,
    notes: list[str] | None = None,
    legend_title: str | None = None,
    x_title: str | None = None,
    value_title: str,
    bases: list[str] | Callable[[], list[str]],
    annotate: bool,
    subtitle: list[str] | None = None,
    kind: str = "heatmap",
) -> None:
    """Record the heatmap just drawn on ``ax`` (a seaborn heatmap: its first
    collection is the mesh, whose color map and norm are the picture's)."""

    mesh = ax.collections[0]
    cmap, norm = mesh.cmap, mesh.norm
    low, high = float(norm.vmin), float(norm.vmax)
    steps = 11
    domain = [low + (high - low) * index / (steps - 1) for index in range(steps)]
    stops = [vega.hex_colour(cmap(norm(value))) for value in domain]
    array = np.asarray(values, dtype=float)
    texts = [[text(value) if value == value else "" for value in line] for line in array.tolist()]
    fills = [
        [vega.hex_colour(cmap(norm(value))) if value == value else "#ffffff" for value in line]
        for line in array.tolist()
    ]
    chart._drawn = DrawnMatrix(
        values=array,
        rows=[str(row) for row in rows],
        columns=[str(column) for column in columns],
        row_names=[vega.plain(name) for name in (row_names or rows)],
        column_names=[vega.plain(name) for name in (column_names or columns)],
        texts=texts,
        stops=stops,
        domain=domain,
        annotate=annotate,
        title=title,
        notes=[note for note in (notes or []) if note],
        legend_title=legend_title,
        x_title=x_title,
        value_title=value_title,
        bases=bases() if callable(bases) else list(bases),
        subtitle=subtitle,
        kind=kind,
        fills=fills,
    )


def matrix_spec(chart: Any, drawn: DrawnMatrix) -> dict[str, Any]:
    look = vega.look_of(chart)
    rows_axis = vega.unique([_label_lines(row, 22) for row in drawn.rows])
    width_px, _ = _figure_px(chart)
    chars = int(max(6, min(18, 0.6 * width_px / max(len(drawn.columns), 1) / 6.5)))
    columns_axis = vega.unique([_label_lines(column, chars) for column in drawn.columns])
    data = []
    for i, row in enumerate(rows_axis):
        for j, column in enumerate(columns_axis):
            value = drawn.values[i, j]
            fill = drawn.fills[i][j]
            base = (
                drawn.bases[j] if len(drawn.bases) > 1 else (drawn.bases[0] if drawn.bases else "")
            )
            data.append(
                {
                    "row": row,
                    "column": column,
                    "row_name": drawn.row_names[i],
                    "column_name": drawn.column_names[j],
                    "value": vega.number(value),
                    "text": drawn.texts[i][j] or "not computed",
                    "cell": drawn.texts[i][j],
                    "ink": _ink(chart, fill),
                    "base": base,
                    "description": f"{drawn.row_names[i]}, {drawn.column_names[j]}: "
                    f"{drawn.texts[i][j] or 'not computed'}",
                }
            )
    tooltip = [
        ("row_name", "Row"),
        ("column_name", drawn.x_title or "Column"),
        ("text", drawn.value_title),
    ]
    if drawn.bases:
        tooltip.append(("base", "Base"))
    cells: dict[str, Any] = {
        "transform": [{"filter": "isValid(datum.value)"}],
        "mark": {"type": "rect", "stroke": "#ffffff", "strokeWidth": 0.5},
        "encoding": {
            "color": {
                "field": "value",
                "type": "quantitative",
                "scale": {"domain": drawn.domain, "range": drawn.stops, "clamp": True},
                # Over the cells, across: beside them it left a narrow chart no
                # room for its cells.
                "legend": {
                    "title": drawn.legend_title,
                    "orient": "top",
                    "direction": "horizontal",
                    "gradientLength": {"expr": "max(80, min(220, width - 20))"},
                    "format": ",.2~f",
                    "titleLimit": 260,
                },
            },
            "tooltip": vega.tooltip(*tooltip),
            "description": {"field": "description"},
        },
    }
    layers: list[dict[str, Any]] = [cells]
    if drawn.annotate:
        layers.append(
            {
                "transform": [{"filter": "isValid(datum.value)"}],
                "mark": {"type": "text", "fontSize": VALUE_SIZE, "baseline": "middle"},
                "encoding": {
                    "text": {"field": "cell"},
                    "color": _ink_encoding(data, look.text),
                },
            }
        )
    lines = max(row.count("\n") + 1 for row in rows_axis)
    main = {
        "name": VIEW,
        "width": "container",
        "height": float(max(160.0, len(rows_axis) * max(30.0, lines * 14.0 + 10.0))),
        "data": {"values": data},
        "encoding": {
            "x": {
                "field": "column",
                "type": "nominal",
                "sort": columns_axis,
                "axis": {
                    "title": drawn.x_title,
                    "labelAngle": 0,
                    "labelExpr": vega.multiline_labels(),
                    "orient": "bottom",
                    "ticks": False,
                    "domain": False,
                    # No wider than its column: a narrow chart cuts a label
                    # short (the tooltip names the cell) rather than lose
                    # its cells to it.
                    "labelLimit": {"expr": f"max(bandwidth('{VIEW}_x') + 4, 24)"},
                },
            },
            "y": {
                "field": "row",
                "type": "nominal",
                "sort": rows_axis,
                "axis": {
                    "title": None,
                    "labelExpr": vega.multiline_labels(),
                    "ticks": False,
                    "domain": False,
                },
            },
        },
        "layer": layers,
    }
    cells_text = [(f"{row['row_name']} × {row['column_name']}", row["text"]) for row in data]
    description = (
        f"Heatmap: {vega.plain(drawn.title)}, {len(drawn.rows)} rows by {len(drawn.columns)} "
        f"columns. {vega.listing(cells_text, 30)}."
    )
    return vega.finish(
        chart,
        main,
        heading=drawn.title,
        subtitle=drawn.subtitle,
        notes=drawn.notes,
        description=description,
        kind=drawn.kind,
    )


# ─── box plot ────────────────────────────────────────────────────────────────


@dataclass
class DrawnBoxes:
    """What a box plot drew: each group's five numbers and outliers, and —
    with Show points — the values it plotted, in the colors drawn."""

    groups: list[str]
    stats: list[dict[str, Any] | None]
    points: list[tuple[str, float]]
    title: str
    subtitle: list[str] | None
    x_title: str
    y_title: str

    def spec(self, chart: Any) -> dict[str, Any]:
        return boxes_spec(chart, self)


@recording
def record_boxes(chart: Any, ax: Any, frame: Any, column: str, title: str) -> None:
    """Record the box plot just drawn on ``ax`` from ``frame`` (``_group`` the
    group's label): Tukey's boxes as seaborn draws them —
    ``matplotlib.cbook.boxplot_stats`` with whiskers at 1.5 IQR."""

    from matplotlib import cbook

    groups = [label.get_text() for label in ax.get_xticklabels()]
    if not any(groups):
        groups = [str(value) for value in dict.fromkeys(frame["_group"])]
    # Each box's color by where it stands: seaborn adds the boxes in the order
    # of its hue levels, not of the axis.
    colours: dict[int, str] = {}
    for patch in ax.patches:
        extent = patch.get_path().get_extents()
        colours[int(round((extent.x0 + extent.x1) / 2.0))] = vega.hex_colour(patch.get_facecolor())
    stats: list[dict[str, Any] | None] = []
    for index, group in enumerate(groups):
        values = frame.loc[frame["_group"] == group, column].to_numpy(dtype=float)
        if not len(values):
            stats.append(None)
            continue
        found = cbook.boxplot_stats(values, whis=1.5)[0]
        stats.append(
            {
                "n": int(len(values)),
                "whislo": float(found["whislo"]),
                "q1": float(found["q1"]),
                "med": float(found["med"]),
                "q3": float(found["q3"]),
                "whishi": float(found["whishi"]),
                "fliers": [float(value) for value in found["fliers"]],
                "colour": colours.get(index, "#4c72b0"),
            }
        )
    points = []
    if getattr(chart, "show_points", False):
        points = [
            (str(group), float(value))
            for group, value in zip(frame["_group"], frame[column], strict=True)
        ]
    chart._drawn = DrawnBoxes(
        groups=groups,
        stats=stats,
        points=points,
        title=title,
        subtitle=[chart._weight_note] if chart._weight_note else None,
        x_title=ax.get_xlabel(),
        y_title=" ".join(ax.get_ylabel().split()),
    )


def boxes_spec(chart: Any, drawn: DrawnBoxes) -> dict[str, Any]:
    look = vega.look_of(chart)
    width_px, _ = _figure_px(chart)
    chars = int(max(8, min(22, 0.7 * width_px / max(len(drawn.groups), 1) / 6.5)))
    axis_groups = vega.unique([_label_lines(group, chars) for group in drawn.groups])
    boxes, outliers = [], []
    for group, axis_group, stat in zip(drawn.groups, axis_groups, drawn.stats, strict=True):
        if stat is None:
            continue
        boxes.append(
            {
                "group": axis_group,
                "name": vega.plain(group),
                "lower": stat["whislo"],
                "q1": stat["q1"],
                "median": stat["med"],
                "q3": stat["q3"],
                "upper": stat["whishi"],
                "median_text": _amount(stat["med"]),
                "quartiles": f"{_amount(stat['q1'])} to {_amount(stat['q3'])}",
                "whiskers": f"{_amount(stat['whislo'])} to {_amount(stat['whishi'])}",
                "outliers": f"{len(stat['fliers']):,}",
                "base": vega.base_text(stat["n"]),
                "colour": stat["colour"],
                "ink": _ink(chart, stat["colour"]),
                "description": f"{vega.plain(group)}: median {_amount(stat['med'])}, "
                f"quartiles {_amount(stat['q1'])} to {_amount(stat['q3'])}",
            }
        )
        outliers += [
            {"group": axis_group, "name": vega.plain(group), "value": value, "text": _amount(value)}
            for value in stat["fliers"]
        ]
    names = {group: axis for group, axis in zip(drawn.groups, axis_groups, strict=True)}
    points = [
        {"group": names.get(group, group), "value": vega.number(value)}
        for group, value in drawn.points
    ]
    tooltip = vega.tooltip(
        ("name", drawn.x_title or "Group"),
        ("median_text", "Median"),
        ("quartiles", "Middle half (quartiles)"),
        ("whiskers", "Whiskers (1.5 IQR)"),
        ("outliers", "Outliers"),
        ("base", "Base"),
    )
    y = {"type": "quantitative", "axis": {"title": drawn.y_title, **vega.thousands_axis()}}
    layers: list[dict[str, Any]] = [
        {
            "data": {"values": boxes},
            "mark": {"type": "rule", "color": look.text, "strokeWidth": 1.1},
            "encoding": {
                "y": {"field": "lower", **y},
                "y2": {"field": "upper"},
                "tooltip": tooltip,
            },
        },
        {
            "data": {"values": boxes},
            "mark": {
                "type": "bar",
                "width": {"band": 0.8},
                "stroke": look.text,
                "strokeWidth": 0.8,
            },
            "encoding": {
                "y": {"field": "q1", **y},
                "y2": {"field": "q3"},
                "color": {"field": "colour", "type": "nominal", "scale": None, "legend": None},
                "tooltip": tooltip,
                "description": {"field": "description"},
            },
        },
        {
            "data": {"values": boxes},
            "mark": {
                "type": "bar",
                "width": {"band": 0.8},
                "strokeWidth": 2,
                "fillOpacity": 0,
            },
            "encoding": {
                "y": {"field": "median", **y},
                "y2": {"field": "median"},
                "stroke": _ink_encoding(boxes, look.text),
                "tooltip": tooltip,
            },
        },
    ]
    if outliers:
        layers.append(
            {
                "data": {"values": outliers},
                "mark": {
                    "type": "point",
                    "shape": "diamond",
                    "filled": True,
                    "size": 28,
                    "color": look.muted,
                },
                "encoding": {
                    "y": {"field": "value", **y},
                    "tooltip": vega.tooltip(
                        ("name", drawn.x_title or "Group"), ("text", "Outlier")
                    ),
                },
            }
        )
    if points:
        layers.append(
            {
                "data": {"values": points},
                "transform": [{"calculate": "random() - 0.5", "as": "jitter"}],
                "mark": {
                    "type": "circle",
                    "size": 10,
                    "opacity": 0.4,
                    "color": look.text,
                    "aria": False,
                },
                "encoding": {
                    "y": {"field": "value", **y},
                    "xOffset": {
                        "field": "jitter",
                        "type": "quantitative",
                        "scale": {"domain": [-1.6, 1.6]},
                    },
                },
            }
        )
    main = {
        "name": VIEW,
        "width": "container",
        "height": _height(chart),
        # The jitter's offsets are the points' own: the boxes keep the band.
        "resolve": {"scale": {"xOffset": "independent"}},
        "encoding": {
            "x": {
                "field": "group",
                "type": "nominal",
                "sort": axis_groups,
                "scale": {"domain": axis_groups, "paddingInner": 0.3},
                "axis": {
                    "title": drawn.x_title,
                    "labelAngle": 0,
                    "labelExpr": vega.multiline_labels(),
                    "ticks": False,
                },
            }
        },
        "layer": layers,
    }
    items = [(row["name"], f"median {row['median_text']}") for row in boxes]
    description = f"Box plot: {vega.plain(drawn.title)}. {vega.listing(items)}."
    notes = []
    if points:
        notes.append(
            "Each point is a respondent's answer, placed at random across its box's width."
        )
    return vega.finish(
        chart,
        main,
        heading=drawn.title,
        subtitle=drawn.subtitle,
        notes=notes,
        description=description,
        kind="boxplot",
    )


# ─── scatter plot ────────────────────────────────────────────────────────────


@dataclass
class DrawnPoints:
    """What a scatter plot drew: each respondent's two values (and group),
    the colors, and the fitted line's ends."""

    x: list[float]
    y: list[float]
    groups: list[str] | None
    levels: list[str]
    colours: list[str]
    line: list[tuple[float, float]] | None
    line_colour: str | None
    title: str
    subtitle: list[str] | None
    x_title: str
    y_title: str
    hue_title: str | None

    def spec(self, chart: Any) -> dict[str, Any]:
        return points_spec(chart, self)


@recording
def record_points(
    chart: Any,
    ax: Any,
    frame: Any,
    hue_col: str | None,
    title: str,
    hue_title: str | None,
) -> None:
    """Record the scatter plot just drawn on ``ax`` from ``frame``: the
    points in the colors seaborn gave them, the fitted line as drawn."""

    points = ax.collections[0]
    faces = points.get_facecolors()
    x = [float(value) for value in frame[chart.x]]
    y = [float(value) for value in frame[chart.y]]
    groups = None
    levels: list[str] = []
    colours: list[str] = []
    if hue_col is not None:
        groups = [str(value) for value in frame[hue_col]]
        legend = ax.get_legend()
        levels = (
            [text.get_text() for text in legend.get_texts()]
            if legend is not None
            else list(dict.fromkeys(groups))
        )
        levels = [level for level in levels if level in set(groups)] or list(dict.fromkeys(groups))
        for level in levels:
            index = groups.index(level)
            colours.append(vega.hex_colour(faces[min(index, len(faces) - 1)]))
    else:
        colours = [vega.hex_colour(faces[0])] if len(faces) else ["#4c72b0"]
    line = None
    line_colour = None
    if ax.lines:
        drawn = ax.lines[-1]
        xs, ys = drawn.get_xdata(), drawn.get_ydata()
        if len(xs) >= 2:
            line = [(float(xs[0]), float(ys[0])), (float(xs[-1]), float(ys[-1]))]
            line_colour = vega.hex_colour(drawn.get_color())
    chart._drawn = DrawnPoints(
        x=x,
        y=y,
        groups=groups,
        levels=levels,
        colours=colours,
        line=line,
        line_colour=line_colour,
        title=title,
        subtitle=[chart._weight_note] if chart._weight_note else None,
        x_title=ax.get_xlabel(),
        y_title=ax.get_ylabel(),
        hue_title=hue_title,
    )


def points_spec(chart: Any, drawn: DrawnPoints) -> dict[str, Any]:
    rows = []
    for index, (x, y) in enumerate(zip(drawn.x, drawn.y, strict=True)):
        row: dict[str, Any] = {"x": vega.number(x), "y": vega.number(y)}
        if drawn.groups is not None:
            row["group"] = drawn.groups[index]
        rows.append(row)
    for row in rows:
        row["x_text"] = _amount(row["x"]) if row["x"] is not None else ""
        row["y_text"] = _amount(row["y"]) if row["y"] is not None else ""
    tooltip = [("x_text", drawn.x_title), ("y_text", drawn.y_title)]
    if drawn.groups is not None:
        tooltip.append(("group", drawn.hue_title or "Group"))
    encoding: dict[str, Any] = {
        "x": {
            "field": "x",
            "type": "quantitative",
            "scale": {"zero": False},
            "axis": {"title": drawn.x_title, **vega.thousands_axis()},
        },
        "y": {
            "field": "y",
            "type": "quantitative",
            "scale": {"zero": False},
            "axis": {"title": drawn.y_title, **vega.thousands_axis()},
        },
        "tooltip": vega.tooltip(*tooltip),
    }
    params = [_zoom()]
    if drawn.groups is not None:
        encoding["color"] = {
            "field": "group",
            "type": "nominal",
            "scale": {"domain": drawn.levels, "range": drawn.colours},
            "legend": _legend(drawn.hue_title, drawn.levels),
        }
        encoding["opacity"] = vega.shown(0.7, 0.04)
        params.append(vega.toggle("group"))
    layers: list[dict[str, Any]] = [
        {
            "data": {"values": rows},
            "mark": {
                "type": "circle",
                "size": 34,
                "opacity": 0.7,
                **({"color": drawn.colours[0]} if drawn.groups is None else {}),
            },
            "params": params,
            "encoding": encoding,
        }
    ]
    if drawn.line is not None:
        (x0, y0), (x1, y1) = drawn.line
        layers.append(
            {
                "data": {
                    "values": [
                        {"x": x0, "y": y0, "fit": "Linear fit"},
                        {"x": x1, "y": y1, "fit": "Linear fit"},
                    ]
                },
                "mark": {
                    "type": "line",
                    "color": drawn.line_colour or "#c44e52",
                    "strokeWidth": 1.8,
                    "clip": True,
                },
                "encoding": {
                    "x": {"field": "x", "type": "quantitative"},
                    "y": {"field": "y", "type": "quantitative"},
                },
            }
        )
    main = {
        "name": VIEW,
        "width": "container",
        "height": _height(chart, 260.0, 440.0),
        "layer": layers,
    }
    description = (
        f"Scatter plot: {vega.plain(drawn.title)}, {len(rows):,} respondents, "
        f"{drawn.x_title} across and {drawn.y_title} up"
        + (f", colored by {drawn.hue_title}" if drawn.groups is not None else "")
        + (", with a linear fit" if drawn.line is not None else "")
        + "."
    )
    notes = [ZOOM_HINT]
    if drawn.line is not None:
        notes.insert(0, "Line: least-squares linear fit, unweighted.")
    return vega.finish(
        chart,
        main,
        heading=drawn.title,
        subtitle=drawn.subtitle,
        notes=notes,
        description=description,
        kind="scatter",
    )


# ─── trend ───────────────────────────────────────────────────────────────────

#: The shapes a Trend's points take past its fourth line (trend.MARKERS), as
#: Vega-Lite names them.
SHAPES = {
    "o": "circle",
    "s": "square",
    "^": "triangle-up",
    "D": "diamond",
    "v": "triangle-down",
    "P": "cross",
    "X": "cross",
    "*": "triangle",
    "p": "wedge",
    "h": "circle",
    "<": "triangle-left",
    ">": "triangle-right",
}


@dataclass
class DrawnTrend:
    """What a Trend drew: its points (``trend.TrendPoints``) in the colors of
    its lines, whether the bands were drawn, and its value axis."""

    points: Any
    colours: list[str]
    banded: bool
    shapes: bool
    title: str
    notes: list[str]
    ylabel: str
    domain: tuple[float, ...]

    def spec(self, chart: Any) -> dict[str, Any]:
        return trend_spec(chart, self)


def trend_spec(chart: Any, drawn: DrawnTrend) -> dict[str, Any]:
    from siamang.reporting.chart_parts import count_text
    from siamang.reporting.trend import MARKERS, _code_text

    points = drawn.points
    measure = points.measure
    periods = list(points.periods)
    groups = [label or vega.plain(drawn.title) for _, label in points.groups]
    split = points.group_title is not None
    level = f"{points.confidence * 100:g}%"

    def text(value: float) -> str:
        if value != value:
            return "no respondents"
        if measure == "percent":
            return f"{value:.1f}%"
        if measure == "mean":
            return f"{value:,.2f}"
        return count_text(value)

    rows = []
    for index, (code, _label) in enumerate(points.groups):
        frame = points.points
        mine = frame[
            frame["group"].map(_code_text) == _code_text(code)
            if code is not None
            else frame["group"].isna()
        ].sort_values("position")
        for record in mine.to_dict("records"):
            value = float(record["value"])
            low = bool(record["low"])
            row: dict[str, Any] = {
                "position": int(record["position"]),
                "period": str(record["period"]),
                "group": groups[index],
                "value": vega.number(value),
                "text": text(value),
                "low": low,
                "base": vega.base_text(
                    int(record["base"]),
                    float(record["weighted_base"]) if points.weight is not None else None,
                ),
            }
            lower, upper = float(record["lower"]), float(record["upper"])
            if measure != "count":
                row["interval"] = (
                    f"{text(lower)} to {text(upper)}"
                    if lower == lower and upper == upper
                    else "none"
                )
            if drawn.banded and not low and lower == lower and upper == upper:
                row["lower"], row["upper"] = lower, upper
            if low and value == value:
                row["note"] = f"fewer than {points.min_base} respondents"
            row["description"] = (
                f"{row['group'] + ', ' if split else ''}{row['period']}: {row['text']}"
            )
            rows.append(row)
    dense = len(periods) > 40
    size = 34 if not dense else max(8.0, 34 * 40 / len(periods))
    count = len(groups)
    labels_expr = vega.script_json(periods)
    step = 1 if len(periods) <= 16 else math.ceil(len(periods) / 16)
    x = {
        "field": "position",
        "type": "quantitative",
        "scale": {"domain": [-0.5, len(periods) - 0.5], "nice": False, "zero": False},
        "axis": {
            "title": points.xlabel,
            "values": list(range(0, len(periods), step)),
            "labelExpr": f"{labels_expr}[datum.value] || ''",
            "labelAngle": 0 if len(periods) <= 8 else -40,
            "labelAlign": "center" if len(periods) <= 8 else "right",
            "grid": True,
            "labelOverlap": "greedy",
        },
    }
    value_axis: dict[str, Any] = {"title": drawn.ylabel, "grid": True}
    value_axis.update(vega.percent_axis() if measure == "percent" else vega.thousands_axis())
    low_limit, high_limit = drawn.domain[0], drawn.domain[-1]
    # A count's axis from 0, its top chosen here; a percent's and a mean's
    # the picture's.
    scale: dict[str, Any] = (
        {"domainMin": 0, "nice": True}
        if measure == "count"
        else {"domain": [low_limit, high_limit], "nice": False, "zero": False}
    )
    y = {"field": "value", "type": "quantitative", "scale": scale, "axis": value_axis}
    legend = None
    if split:
        # The legend shows the lines, not the pale bands.
        legend = {
            **_legend(points.group_title, groups),
            "symbolType": "stroke" if not drawn.shapes else "circle",
            "symbolStrokeWidth": 2.5,
            "symbolOpacity": 1,
        }
    colour: dict[str, Any] = {
        "field": "group",
        "type": "nominal",
        "scale": {"domain": groups, "range": drawn.colours[:count]},
        "legend": legend,
    }
    fade = {"opacity": vega.shown()} if split else {}
    tooltip = [("period", "Period")]
    if split:
        tooltip.insert(0, ("group", points.group_title or "Group"))
    tooltip.append(("text", {"percent": "Percent", "mean": "Mean", "count": "Count"}[measure]))
    if measure != "count":
        tooltip.append(("interval", f"{level} confidence interval"))
    tooltip.append(("base", "Base"))
    tooltip.append(("note", "Note"))
    shape: dict[str, Any] = {}
    if drawn.shapes:
        shape = {
            "shape": {
                "field": "group",
                "type": "nominal",
                "scale": {
                    "domain": groups,
                    "range": [
                        SHAPES.get(MARKERS[i % len(MARKERS)], "circle") for i in range(count)
                    ],
                },
                "legend": legend,
            }
        }
    line_params = [vega.toggle("group")] if split else []
    if len(periods) > 24:
        line_params.append(_zoom("x"))
    layers: list[dict[str, Any]] = []
    if drawn.banded and any("lower" in row for row in rows):
        layers.append(
            {
                "mark": {"type": "area", "opacity": 0.18 if count == 1 else 0.08, "aria": False},
                "encoding": {
                    "y": {"field": "lower", "type": "quantitative"},
                    "y2": {"field": "upper"},
                    "color": colour,
                    **({"opacity": vega.shown(0.18 if count == 1 else 0.08, 0)} if split else {}),
                },
            }
        )
    line = {
        "mark": {"type": "line", "strokeWidth": 1.4 if dense else 2.0},
        "encoding": {"y": y, "color": colour, **fade},
    }
    if line_params:
        line["params"] = line_params
    layers.append(line)
    point_encoding = {
        "y": {"field": "value", "type": "quantitative"},
        "color": colour,
        "tooltip": vega.tooltip(*tooltip),
        "description": {"field": "description"},
        **shape,
        **fade,
    }
    # The points that have their base filled, the others hollow (a layer of
    # no points at all would leave its scale nothing to span).
    solid = [row for row in rows if row["value"] is not None and not row["low"]]
    hollow = [row for row in rows if row["value"] is not None and row["low"]]
    if solid:
        layers.append(
            {
                "transform": [{"filter": "isValid(datum.value) && !datum.low"}],
                "mark": {"type": "point", "filled": True, "size": size, "opacity": 1},
                "encoding": point_encoding,
            }
        )
    if hollow:
        layers.append(
            {
                "transform": [{"filter": "isValid(datum.value) && datum.low"}],
                "mark": {
                    "type": "point",
                    "filled": False,
                    "fill": "#ffffff",
                    "fillOpacity": 1,
                    "strokeWidth": 1.0 if dense else 1.6,
                    "size": size,
                    "opacity": 1,
                },
                "encoding": point_encoding,
            }
        )
    main = {
        "name": VIEW,
        "width": "container",
        "height": _height(chart),
        "data": {"values": rows},
        "encoding": {"x": x},
        "layer": layers,
    }
    notes = list(drawn.notes)
    if len(periods) > 24:
        notes.append(ZOOM_HINT)
    items = [
        (f"{row['group']}, {row['period']}" if split else row["period"], row["text"])
        for row in rows
        if row["value"] is not None
    ]
    description = (
        f"Trend: {vega.plain(drawn.title)}, {len(periods)} periods"
        + (f", {count} lines by {points.group_title}" if split else "")
        + f". {vega.listing(items, 24)}."
    )
    return vega.finish(
        chart,
        main,
        heading=drawn.title,
        notes=notes,
        description=description,
        kind="trend",
    )


# ─── recording what was drawn ────────────────────────────────────────────────


@recording
def record_bars(chart: Any, bars: Any, colours: list[Any], other: Any, across: bool) -> None:
    """What a bar chart drew (``bars.render``): its bars in their colors and
    the direction they were drawn in."""

    chart._drawn = DrawnBars(
        bars=bars,
        colours=[vega.hex_colour(colour) for colour in colours],
        horizontal=across,
        show_values=chart.show_values,
        other=vega.hex_colour(other),
    )


@recording
def record_classic(
    chart: Any,
    values: Any,
    labels: list[str],
    position_label: str,
    axis: str,
    kind: str,
    bases: Callable[[], list[tuple[int, float | None]]],
    series: str | None = None,
) -> None:
    """What the chart BarChart has always drawn drew: its bars in the colors
    drawn (read off them), its labels and values as it writes them."""

    from siamang.reporting.bars import Bars

    colours = [vega.hex_colour(patch.get_facecolor()) for patch in chart._ax.patches]
    counted = bases()
    bars = Bars(
        values=np.asarray(values, dtype=float).reshape(-1, 1),
        positions=[str(label) for label in labels],
        series=[series or position_label],
        kind=kind,
        value_label=axis,
        position_label=position_label,
        title=chart._ax.get_title(),
        base_texts=[vega.base_text(n, weighted) for n, weighted in counted]
        * (len(labels) if len(counted) == 1 else 1),
    )
    chart._drawn = DrawnBars(
        bars=bars,
        colours=colours[:1] or ["#4c72b0"],
        horizontal=chart.horizontal,
        show_values=chart.show_values,
        position_colours=colours if len(colours) == len(labels) else None,
        classic=True,
    )


@recording
def record_histogram(chart: Any, histogram: Any, colour: Any) -> None:
    chart._drawn = DrawnHistogram(histogram, vega.hex_colour(colour), list(histogram.base_texts))


@recording
def record_donut(chart: Any, donut: Any, colours: list[Any]) -> None:
    chart._drawn = DrawnDonut(
        donut, [vega.hex_colour(colour) for colour in colours], chart.show_values
    )


@recording
def record_likert(
    chart: Any,
    *,
    rows: list[dict[str, Any]],
    items: list[str],
    scale: Any,
    colours: dict[Any, Any],
    limit: float,
    side: bool,
    title: str,
    notes: list[str],
    axis: str,
) -> None:
    chart._drawn = DrawnLikert(
        rows=rows,
        items=items,
        scale=scale,
        colours={code: vega.hex_colour(colours[code]) for code in scale.codes},
        limit=limit,
        side=side,
        title=title,
        notes=list(notes),
        axis=axis,
        show_values=chart.show_values,
    )


@recording
def record_trend(
    chart: Any,
    *,
    points: Any,
    colours: list[Any],
    banded: bool,
    shapes: bool,
    title: str,
    notes: list[str],
    ylabel: str,
    ax: Any,
) -> None:
    chart._drawn = DrawnTrend(
        points=points,
        colours=[vega.hex_colour(colour) for colour in colours],
        banded=banded,
        shapes=shapes,
        title=title,
        notes=list(notes),
        ylabel=ylabel,
        domain=tuple(float(limit) for limit in ax.get_ylim()),
    )


__all__ = [
    "DrawnBars",
    "DrawnBoxes",
    "DrawnDonut",
    "DrawnHistogram",
    "DrawnLikert",
    "DrawnMatrix",
    "DrawnPoints",
    "DrawnTrend",
    "group_bases",
    "record_bars",
    "record_boxes",
    "record_classic",
    "record_donut",
    "record_histogram",
    "record_likert",
    "record_matrix",
    "record_points",
    "record_trend",
    "recording",
]
