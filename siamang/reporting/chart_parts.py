"""What the newer charts share: a footnote under the plot, text that wraps
instead of running into its neighbours, and the colours of several series.

A survey chart is read away from the table it came from — pasted into a slide,
mailed as a PNG — so what a table says under itself (the base, the weight, the
missing codes left out) goes under the chart too. :class:`Footnote` reserves
the room for it at the bottom of the figure, so the plot, its tick labels and
its legend never run into it, and a figure keeps the size it was asked for.

Only the charts added with it use this module; the older ones draw exactly
what they always drew.
"""

from __future__ import annotations

import textwrap
from typing import Any

#: The size of the footnote's text, in points.
FOOTNOTE_SIZE = 9.0
#: The size of a value written on or beside a bar, in points.
VALUE_SIZE = 9.0
#: The width of an average character of the sans-serif face, as a share of
#: its size: what a label may hold is estimated from it before it is drawn.
CHAR_WIDTH = 0.6


def wrap(text: Any, width: int) -> str:
    """``text`` broken into lines of at most ``width`` characters, words kept whole."""

    text = str(text)
    lines: list[str] = []
    for paragraph in text.split("\n"):
        lines.extend(textwrap.wrap(paragraph, max(4, width), break_long_words=False) or [""])
    return "\n".join(lines)


def in_sentence(label: Any) -> str:
    """A codebook label as it reads inside a sentence: "Weighted mean overall
    life satisfaction", not "… mean Overall life …". Only a capital that starts
    an ordinary word is lowered — "MaxDiff score", "NPS", "I scroll" and a
    one-letter word keep theirs."""

    text = str(label)
    word = text.split(" ", 1)[0]
    letters = word.rstrip(":,;.)")
    if len(letters) > 1 and letters[0].isupper() and letters[1:].islower():
        return text[0].lower() + text[1:]
    return text


def common_prefix(labels: list[Any]) -> tuple[str, list[str]]:
    """The "Question: " every one of ``labels`` starts with, and the labels
    without it — ("MaxDiff score", ["Focus sessions", …]) — or ("", the labels)
    when there is none. An exploded question's or a score's options all carry
    it, and a chart that repeats it on every row has room for little else."""

    texts = [str(label) for label in labels]
    if len(texts) < 2 or not all(": " in text for text in texts):
        return "", texts
    heads = {text.split(": ", 1)[0] for text in texts}
    if len(heads) != 1:
        return "", texts
    rests = [text.split(": ", 1)[1].strip() for text in texts]
    if not all(rests) or len(set(rests)) != len(rests):
        return "", texts
    return heads.pop(), rests


def chars_in(width_pt: float, size: float) -> int:
    """How many characters of ``size`` points fit in ``width_pt`` points."""

    return max(4, int(width_pt / (size * CHAR_WIDTH)))


def text_width(text: str, size: float) -> float:
    """The width of ``text`` in points, estimated: its longest line."""

    return max((len(line) for line in str(text).split("\n")), default=0) * size * CHAR_WIDTH


def font_size(key: str) -> float:
    """The size in points an rcParams entry gives (``"large"`` resolved)."""

    import matplotlib
    from matplotlib.font_manager import FontProperties

    return float(FontProperties(size=matplotlib.rcParams[key]).get_size_in_points())


def axes_points(ax: Any) -> tuple[float, float]:
    """The drawn width and height of ``ax``, in points."""

    box = ax.get_window_extent()
    dpi = ax.figure.dpi
    return box.width * 72.0 / dpi, box.height * 72.0 / dpi


def ink_on(colour: Any) -> str:
    """Text colour that reads on a fill of ``colour``: white on dark, ink on light
    (in a chart of the theme's colours, whichever of white and its text reads
    better — :meth:`~siamang.reporting.chart_theme.ChartColours.ink_on`)."""

    from matplotlib.colors import to_rgb

    from siamang.reporting import chart_theme

    themed = chart_theme.themed()
    if themed is not None:
        return themed.ink_on(colour)

    def linear(channel: float) -> float:
        return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4

    red, green, blue = (linear(channel) for channel in to_rgb(colour))
    luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
    return "white" if luminance < 0.36 else "0.15"


def series_colours(palette: str, count: int, *, ordered: bool = False) -> list[Any]:
    """One colour per series from ``palette``, none of them repeated.

    The steps of an ordered scale (ordinal and up) are one hue, the palette's
    first, light to dark: the order is in the colour, and neighbouring answers
    look like neighbours. Categories that have no order take the palette's
    colours in turn; a qualitative palette has eight or ten, and past them it
    would start over. More categories than that take the palette's colours
    again, lighter, then darker — each unlike its neighbours, as a hue wheel's
    near neighbours (and its first and last colour) are not — and past three
    times the palette, hues spaced over the wheel without closing it, their
    lightness alternating.

    ``palette="theme"`` takes the report theme's colours
    (:meth:`~siamang.reporting.chart_theme.ChartColours.series`): its palette,
    and for the steps of a scale its sequential colour.
    """

    import seaborn as sns
    from matplotlib.colors import to_rgb

    from siamang.reporting import chart_theme

    if palette == chart_theme.THEME:
        return [to_rgb(colour) for colour in chart_theme.current().series(count, ordered=ordered)]
    base = list(sns.color_palette(palette))
    if ordered and count > 1:
        first = to_rgb(base[0])
        light = tuple(1.0 - (1.0 - channel) * 0.35 for channel in first)
        dark = tuple(channel * 0.4 for channel in first)
        return list(sns.blend_palette([light, first, dark], count))
    if count <= len(base):
        return base[:count]
    if count <= 3 * len(base):
        white, black = (1.0, 1.0, 1.0), (0.0, 0.0, 0.0)
        lighter = [_mix(colour, white, 0.5) for colour in base]
        darker = [_mix(colour, black, 0.4) for colour in base]
        return [to_rgb(colour) for colour in base] + (lighter + darker)[: count - len(base)]
    hues = list(sns.color_palette("husl", count + 1))[:count]  # not back to the first
    return [
        _mix(colour, (0.0, 0.0, 0.0), 0.3) if index % 2 else colour
        for index, colour in enumerate(hues)
    ]


def _mix(colour: Any, other: tuple[float, float, float], share: float) -> tuple[float, ...]:
    """``colour`` moved ``share`` of the way to ``other``."""

    from matplotlib.colors import to_rgb

    return tuple(a + (b - a) * share for a, b in zip(to_rgb(colour), other, strict=True))


def percent_axis(axis: Any) -> None:
    """Label a value axis of percentages 0 %, 20 %, …

    The ticks fall on whole percents (steps of 1, 2, 5 or 10 and their tens):
    labels without decimals on the 2.5-point steps matplotlib would choose
    otherwise read 0, 2, 5, 8, 10 % under evenly spaced gridlines."""

    from matplotlib.ticker import MaxNLocator, PercentFormatter

    axis.set_major_locator(MaxNLocator(nbins="auto", steps=[1, 2, 5, 10], integer=True))
    axis.set_major_formatter(PercentFormatter(xmax=100, decimals=0))


class Footnote:
    """Notes under a chart, and a layout that leaves the room for them.

    ``apply`` lays the figure out (``tight_layout``) above the notes — and above
    ``legend``, a figure legend placed between the plot and the notes when the
    figure is too narrow to hold it beside the plot — and may be called again
    after something was added. The notes are written at the bottom left, in a
    small grey type.

    When what must be written around the plot leaves ``axes`` less than a
    readable height (long labels on a small figure), the figure grows taller
    by what is missing rather than drawing a plot nobody can read.
    """

    #: The least height of the plot, in points, and as a share of the figure.
    MIN_PLOT = (110.0, 0.4)

    def __init__(
        self,
        fig: Any,
        notes: list[str],
        legend: Any = None,
        axes: Any = None,
        least: float | None = None,
    ) -> None:
        self.fig = fig
        self.notes = [note for note in notes if note]
        self.legend = legend
        self.axes = axes
        self._text: Any = None
        self._asked = fig.get_figheight() * 72.0
        #: The plot's least height in points: MIN_PLOT, or more when its rows
        #: need it (a heatmap's wrapped labels, a Likert chart's items).
        self.least = max(self.MIN_PLOT[0], self.MIN_PLOT[1] * self._asked, least or 0.0)
        width = chars_in(fig.get_figwidth() * 72.0 - 14.0, FOOTNOTE_SIZE)
        self.lines = [line for note in self.notes for line in wrap(note, width).split("\n")]

    @property
    def text(self) -> str:
        return "\n".join(self.lines)

    def add(self, note: str) -> None:
        """Write ``note`` after the others; the next ``apply`` makes room."""
        self.notes.append(note)
        width = chars_in(self.fig.get_figwidth() * 72.0 - 14.0, FOOTNOTE_SIZE)
        self.lines += wrap(note, width).split("\n")
        if self._text is not None:
            self._text.set_text(self.text)

    def apply(self) -> None:
        if self.axes is not None:
            self._make_room()
        self._layout()
        if self.axes is not None:
            # The labels measured before the layout may take a little more
            # after it: a second, exact step.
            short = self.least - axes_points(self.axes)[1]
            if short > 0.5:
                self.fig.set_figheight(self.fig.get_figheight() + short / 72.0)
                self._layout()
        height = self.fig.get_figheight() * 72.0
        if self.lines and self._text is None:
            from siamang.reporting import chart_theme

            self._text = self.fig.text(
                0.012,
                0.0,
                self.text,
                ha="left",
                va="bottom",
                fontsize=FOOTNOTE_SIZE,
                color=chart_theme.muted("0.3"),
            )
        if self._text is not None:
            self._text.set_y(5.0 / height)

    def _below(self) -> float:
        """The points the notes and a legend under the plot take."""

        needed = len(self.lines) * FOOTNOTE_SIZE * 1.3 + 10.0 if self.lines else 4.0
        if self.legend is not None:
            height = self.fig.get_figheight() * 72.0
            self.legend.set_bbox_to_anchor((0.5, needed / height), transform=self.fig.transFigure)
            box = self.legend.get_window_extent(self.fig.canvas.get_renderer())
            needed += box.height * 72.0 / self.fig.dpi + 6.0
        return needed

    def _make_room(self) -> None:
        """Grow the figure when the plot, its title and tick labels, the legend
        and the notes do not fit with the plot at a readable height."""

        renderer = self.fig.canvas.get_renderer()
        scale = 72.0 / self.fig.dpi
        tight = self.axes.get_tightbbox(renderer).height * scale
        plot = self.axes.get_window_extent(renderer).height * scale
        required = self._below() + (tight - plot) + self.least + 16.0
        if required > self.fig.get_figheight() * 72.0:
            self.fig.set_figheight(required / 72.0)

    def _layout(self) -> None:
        import warnings

        height = self.fig.get_figheight() * 72.0
        with warnings.catch_warnings():
            # A label too big for a small figure: the layout does what it can.
            warnings.simplefilter("ignore", UserWarning)
            self.fig.tight_layout(rect=(0.0, min(0.9, self._below() / height), 1.0, 1.0))


def row_major(items: list[Any], columns: int) -> list[Any]:
    """``items`` reordered so a legend of ``columns`` columns, which matplotlib
    fills column by column, reads row by row in the order given."""

    rows = -(-len(items) // max(columns, 1))
    order = [row * columns + column for column in range(columns) for row in range(rows)]
    return [items[index] for index in order if index < len(items)]


def legend_below(
    fig: Any, handles: list[Any], names: list[str], title: str, figure_pt: float
) -> Any:
    """A figure legend between the plot and the notes, in as many columns as
    the figure's width holds, read row by row (:class:`Footnote` makes room
    for it when it is given as ``legend``)."""

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


def left_out_note(left_out: dict[str, list[tuple[Any, int]]], variables: Any) -> str | None:
    """``"Left out as missing: Trust: Acme: 12 (9 = Refused)"``, or None."""

    from siamang.data.inference import missing_codes_note

    note = missing_codes_note(left_out, variables)
    return f"Left out as missing: {note}." if note else None


def code_order(code: Any) -> tuple[int, Any]:
    """Numbers first, in order, then anything else by its text."""

    if isinstance(code, bool):
        return (1, str(code))
    if isinstance(code, int | float):
        return (0, float(code))
    try:
        return (0, float(code))
    except (TypeError, ValueError):
        return (1, str(code))


def code_text(code: Any) -> str:
    """A code as the codebook writes it: 3, not the 3.0 a float column holds."""

    if isinstance(code, float) and code.is_integer():
        return str(int(code))
    return str(code)


def count_text(value: float) -> str:
    """A count: whole numbers as integers, weighted ones to one decimal — or,
    from 100 on, whole too, as ``18,848`` reads and ``18848.4`` does not; the
    thousands separated."""

    if abs(value - round(value)) < 1e-9 or abs(value) >= 100:
        return f"{int(round(value)):,}"
    return f"{value:.1f}"


def thousands_axis(axis: Any) -> None:
    """Label a count axis with its thousands separated: 20,000, not 20000."""

    from matplotlib.ticker import FuncFormatter

    axis.set_major_formatter(
        FuncFormatter(
            lambda value, _: f"{value:,.0f}" if float(value).is_integer() else f"{value:,g}"
        )
    )


def fit_ticks(ax: Any, which: str = "x", gap: float = 0.5) -> None:
    """Thin the ticks of ``ax``'s x (or y) axis until no two neighbouring
    labels come closer than ``gap`` ems: the locator counts ticks, not the
    width of their labels, so on a narrow plot '0 50,000 100,000150,000'
    ran together. Ticks set one by one (a histogram's edges) keep every
    second, third … one; others are asked of matplotlib in fewer bins. The
    ticks found are then fixed: matplotlib would choose them again when the
    figure is saved, by the settings in force then — a chart in the theme's
    colours is saved outside them, and took twice the ticks it was fitted
    with. Axes that share the axis share the result."""

    from matplotlib.ticker import FixedLocator, MaxNLocator

    axis = ax.xaxis if which == "x" else ax.yaxis
    fig = ax.figure
    fixed = axis.get_major_locator()
    fixed_ticks = list(fixed.locs) if isinstance(fixed, FixedLocator) else None
    bins = 0
    for step in range(1, 12):
        fig.draw_without_rendering()
        renderer = fig.canvas.get_renderer()
        low, high = sorted(ax.get_xlim() if which == "x" else ax.get_ylim())
        labels = [
            label
            for tick, label in zip(
                axis.get_majorticklocs(), axis.get_majorticklabels(), strict=False
            )
            if low <= tick <= high and label.get_visible() and label.get_text()
        ]
        boxes = sorted(
            (label.get_window_extent(renderer) for label in labels),
            key=lambda box: box.x0 if which == "x" else box.y0,
        )
        room = gap * labels[0].get_fontsize() / 72.0 * fig.dpi if labels else 0.0
        if which == "x":
            crowded = any(a.x1 + room > b.x0 for a, b in zip(boxes, boxes[1:], strict=False))
        else:
            crowded = any(a.y1 + room > b.y0 for a, b in zip(boxes, boxes[1:], strict=False))
        if not crowded or len(labels) < 3:
            axis.set_major_locator(FixedLocator(list(axis.get_majorticklocs())))
            return
        if fixed_ticks is not None:
            axis.set_major_locator(FixedLocator(fixed_ticks[:: step + 1]))
        else:
            # A bin fewer each time: 0 20,000 40,000 60,000 becomes 0 25,000
            # 50,000 before it becomes 0 50,000.
            bins = (bins or len(labels)) - 1
            axis.set_major_locator(MaxNLocator(nbins=max(bins, 1), steps=[1, 2, 2.5, 5, 10]))
    axis.set_major_locator(FixedLocator(list(axis.get_majorticklocs())))


__all__ = [
    "CHAR_WIDTH",
    "FOOTNOTE_SIZE",
    "VALUE_SIZE",
    "Footnote",
    "axes_points",
    "chars_in",
    "code_order",
    "code_text",
    "count_text",
    "fit_ticks",
    "thousands_axis",
    "font_size",
    "ink_on",
    "left_out_note",
    "legend_below",
    "percent_axis",
    "row_major",
    "series_colours",
    "text_width",
    "wrap",
]
