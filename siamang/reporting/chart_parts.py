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
    """Text colour that reads on a fill of ``colour``: white on dark, ink on light."""

    from matplotlib.colors import to_rgb

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
    would start over, so more categories than that take hues spaced around the
    wheel instead of two answers sharing one.
    """

    import seaborn as sns
    from matplotlib.colors import to_rgb

    base = list(sns.color_palette(palette))
    if ordered and count > 1:
        first = to_rgb(base[0])
        light = tuple(1.0 - (1.0 - channel) * 0.35 for channel in first)
        dark = tuple(channel * 0.4 for channel in first)
        return list(sns.blend_palette([light, first, dark], count))
    if count <= len(base):
        return base[:count]
    return list(sns.color_palette("husl", count))


def percent_axis(axis: Any) -> None:
    """Label a value axis of percentages 0 %, 20 %, …"""

    from matplotlib.ticker import PercentFormatter

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

    def __init__(self, fig: Any, notes: list[str], legend: Any = None, axes: Any = None) -> None:
        self.fig = fig
        self.notes = [note for note in notes if note]
        self.legend = legend
        self.axes = axes
        self._text: Any = None
        self._asked = fig.get_figheight() * 72.0
        width = chars_in(fig.get_figwidth() * 72.0 - 14.0, FOOTNOTE_SIZE)
        self.lines = [line for note in self.notes for line in wrap(note, width).split("\n")]

    @property
    def text(self) -> str:
        return "\n".join(self.lines)

    def apply(self) -> None:
        if self.axes is not None:
            self._make_room()
        self._layout()
        if self.axes is not None:
            # The labels measured before the layout may take a little more
            # after it: a second, exact step.
            least = max(self.MIN_PLOT[0], self.MIN_PLOT[1] * self._asked)
            short = least - axes_points(self.axes)[1]
            if short > 0.5:
                self.fig.set_figheight(self.fig.get_figheight() + short / 72.0)
                self._layout()
        height = self.fig.get_figheight() * 72.0
        if self.lines and self._text is None:
            self._text = self.fig.text(
                0.012, 0.0, self.text, ha="left", va="bottom", fontsize=FOOTNOTE_SIZE, color="0.3"
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
        least = max(self.MIN_PLOT[0], self.MIN_PLOT[1] * self._asked)
        required = self._below() + (tight - plot) + least + 16.0
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
    """A count: whole numbers as integers, weighted ones to one decimal."""

    return str(int(round(value))) if abs(value - round(value)) < 1e-9 else f"{value:.1f}"


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
    "font_size",
    "ink_on",
    "left_out_note",
    "percent_axis",
    "row_major",
    "series_colours",
    "text_width",
    "wrap",
]
