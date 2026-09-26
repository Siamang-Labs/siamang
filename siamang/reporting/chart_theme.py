"""A chart in the report theme's colours: ``palette="theme"``.

A chart names its colours by a palette of seaborn's (``"muted"``, ``"RdBu"``,
a matplotlib colour map) — or by :data:`THEME`, which means *the colours of the
report it is in*: the ``chart_*`` fields of
:class:`~siamang.reporting.theme.ReportTheme` (a categorical palette, a
sequential colour, a diverging pair, the text and grid colours and the font),
whose defaults are a set that stays legible under protanopia and deuteranopia
(:data:`PALETTE`). Everything a chart asks of the theme is answered here, so a
chart module names a role — the text, the grid, the first series, the low end
of a diverging scale — and gets the theme's colour while a chart that reads the
theme is drawn (:func:`drawing`), and the colour it has always used otherwise.
A chart that names a palette of its own therefore draws the picture it always
drew, byte for byte, and a stored flow keeps its pictures: the theme is an
opt-in, never a new default.

When is the theme known? A chart is drawn at its node — a flow's run builds it
there, so what it cannot draw fails its own node — and the report's theme is a
parameter of the Save report downstream. So the theme a chart is drawn with at
its node is the one ``SIAMANG_REPORT_THEME`` names (a platform's preview sets
it to the flow's Save report look), else the default; and a report renders
each chart that reads the theme in its own theme's colours: when those differ
from the ones the chart was drawn with, it draws a copy of the chart from its
parameters — a chart is a dataclass of them and its data — in the report's
colours (:func:`in_report`). The chart at its node is left as it was drawn.

The colour arithmetic the rules need is here too: hex colours, the WCAG
contrast of text on a fill (:func:`contrast`, :meth:`ChartColours.ink_on`), and
a simulation of the two common colour-vision deficiencies (Machado, Oliveira
and Fernandes 2009) with distances in OKLab (:func:`distance`), which is what
the default palette is held to.
"""

from __future__ import annotations

import contextlib
import contextvars
import dataclasses
import functools
import math
import re
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from siamang.reporting.theme import ReportTheme

#: The palette that means "the report theme's colours".
THEME = "theme"

# ─── the default colours ─────────────────────────────────────────────────────

#: Eight hues in an order whose neighbours stay apart for a reader with
#: protanopia or deuteranopia (OKLab ΔE ≥ 9 between each pair of neighbours, and
#: between any two of the first three, simulated as :func:`distance` does) and
#: with full colour vision (ΔE ≥ 19): series are assigned in this order, so
#: bars, stacks and lines side by side take neighbours. Blue and orange are the
#: pair the engine's own analyses already draw with (Key drivers, the
#: Perceptual map, Price sensitivity).
PALETTE = (
    "#2a78d6",  # blue
    "#eb6834",  # orange
    "#1baf7a",  # aqua
    "#eda100",  # yellow
    "#e87ba4",  # magenta
    "#008300",  # green
    "#4a3aa7",  # violet
    "#e34948",  # red
)
#: One hue for magnitude and for the steps of an ordered scale, light to dark.
SEQUENTIAL = "#2a78d6"
#: The two ends of a diverging scale, low (negative, disagree, detractors)
#: first: red and blue, which no common colour-vision deficiency confuses.
DIVERGING = ("#e34948", "#2a78d6")
#: The charts' text: the report's own text colour (``ReportTheme.text_color``).
TEXT = "#1a1a1a"
#: Grid lines: light enough to stay behind the data.
GRID = "#e0e0e0"
#: The middle answer of a scale — a Likert chart's neutral answer, the Net
#: Promoter Score's passives, neutral sentiment: a grey, neither side.
NEUTRAL = "#bdbdbd"
#: The centre of a continuous diverging scale (a correlation of 0).
MIDPOINT = "#f2f2f2"
#: What the charts are drawn on.
BACKGROUND = "#ffffff"

#: How far toward white the innermost step of a diverging scale's arm goes.
INNER_TINT = 0.45
#: The least WCAG contrast of text against what it is written on (AA, normal text).
MIN_TEXT_CONTRAST = 4.5
#: The least contrast of the lightest step of an ordered scale against the background.
MIN_STEP_CONTRAST = 2.0
#: The most colours a categorical palette may name: past a dozen, no two can
#: be told apart reliably, and a chart past its palette makes lighter and
#: darker ones of its own.
MAX_PALETTE = 12

_HEX = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
#: What a font stack may not hold: it is a list of names, not CSS.
_FONT_FORBIDDEN = re.compile(r"[;{}<>]")
_GENERIC_FONTS = {
    "serif": "serif",
    "sans-serif": "sans-serif",
    "monospace": "monospace",
    "cursive": "cursive",
    "fantasy": "fantasy",
    "system-ui": "sans-serif",
    "ui-sans-serif": "sans-serif",
    "ui-serif": "serif",
    "ui-monospace": "monospace",
}


# ─── colour arithmetic ───────────────────────────────────────────────────────


def is_hex(value: Any) -> bool:
    """Whether ``value`` is a colour as ``#rgb`` or ``#rrggbb``."""

    return isinstance(value, str) and bool(_HEX.match(value.strip()))


def hex_colour(value: str) -> str:
    """``value`` as ``#rrggbb`` in lower case (``#abc`` → ``#aabbcc``)."""

    text = value.strip().lower()
    if len(text) == 4:
        text = "#" + "".join(char * 2 for char in text[1:])
    return text


def rgb(colour: Any) -> tuple[float, float, float]:
    """``colour`` — a hex string, or an RGB(A) tuple of floats in 0–1 — as RGB."""

    if isinstance(colour, str) and is_hex(colour):
        text = hex_colour(colour)
        return tuple(int(text[i : i + 2], 16) / 255.0 for i in (1, 3, 5))  # type: ignore[return-value]
    if isinstance(colour, str):
        from matplotlib.colors import to_rgb

        return tuple(float(channel) for channel in to_rgb(colour))  # type: ignore[return-value]
    red, green, blue = (float(channel) for channel in tuple(colour)[:3])
    return red, green, blue


def to_hex(colour: Any) -> str:
    return "#" + "".join(f"{round(max(0.0, min(1.0, c)) * 255):02x}" for c in rgb(colour))


def mix(colour: Any, other: Any, share: float) -> str:
    """``colour`` moved ``share`` of the way to ``other``, as hex."""

    return to_hex(tuple(a + (b - a) * share for a, b in zip(rgb(colour), rgb(other), strict=True)))


def _linear(channel: float) -> float:
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def luminance(colour: Any) -> float:
    """WCAG relative luminance."""

    red, green, blue = (_linear(channel) for channel in rgb(colour))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast(first: Any, second: Any) -> float:
    """The WCAG contrast ratio of two colours, 1 to 21."""

    high, low = sorted((luminance(first), luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


# Machado, Oliveira & Fernandes (2009), severity 1.0, on linear RGB.
_MACHADO = {
    "protan": (
        (0.152286, 1.052583, -0.204868),
        (0.114503, 0.786281, 0.099216),
        (-0.003882, -0.048116, 1.051998),
    ),
    "deutan": (
        (0.367322, 0.860646, -0.227968),
        (0.280085, 0.672501, 0.047413),
        (-0.011820, 0.042940, 0.968881),
    ),
}
VISIONS = ("protan", "deutan")


def _oklab(linear: Sequence[float]) -> tuple[float, float, float]:
    red, green, blue = linear  # 0–1, so the cone responses are not negative
    lo = (0.4122214708 * red + 0.5363325363 * green + 0.0514459929 * blue) ** (1 / 3)
    mid = (0.2119034982 * red + 0.6806995451 * green + 0.1073969566 * blue) ** (1 / 3)
    short = (0.0883024619 * red + 0.2817188376 * green + 0.6299787005 * blue) ** (1 / 3)
    return (
        0.2104542553 * lo + 0.7936177850 * mid - 0.0040720468 * short,
        1.9779984951 * lo - 2.4285922050 * mid + 0.4505937099 * short,
        0.0259040371 * lo + 0.7827717662 * mid - 0.8086757660 * short,
    )


def seen(colour: Any, vision: str | None = None) -> tuple[float, float, float]:
    """``colour`` in OKLab as a reader with ``vision`` (``"protan"``,
    ``"deutan"``, or None for full colour vision) sees it."""

    linear = [_linear(channel) for channel in rgb(colour)]
    if vision is not None:
        matrix = _MACHADO[vision]
        linear = [
            max(
                0.0,
                min(1.0, sum(weight * value for weight, value in zip(row, linear, strict=True))),
            )
            for row in matrix
        ]
    return _oklab(linear)


def distance(first: Any, second: Any, vision: str | None = None) -> float:
    """How far apart two colours look: Euclidean distance in OKLab × 100, as a
    reader with ``vision`` sees them (None: full colour vision). Under 6 two
    colours are hard to tell apart; 8 and more is comfortable."""

    return 100.0 * math.dist(seen(first, vision), seen(second, vision))


def lightness(colour: Any) -> float:
    """OKLab lightness, 0 (black) to 1 (white)."""

    return seen(colour)[0]


# ─── what a theme may say ────────────────────────────────────────────────────


def colours_of(value: Any) -> tuple[str, ...] | Any:
    """A list of colours as a theme stores it — a list, or one string of them
    separated by commas or spaces (what a form's text box holds) — as a tuple;
    anything else is returned as it is, for :func:`problem` to name."""

    if isinstance(value, str):
        return tuple(part for part in re.split(r"[\s,]+", value.strip()) if part)
    if isinstance(value, list | tuple):
        return tuple(value)
    return value


def problem(
    *,
    palette: Any,
    sequential: Any,
    diverging: Any,
    text: Any,
    grid: Any,
    font: Any,
) -> str | None:
    """Why the chart fields of a theme cannot be used, or None."""

    def not_hex(name: str, value: Any) -> str:
        return f"{name}: {value!r} is not a hex colour such as '#2a78d6'."

    if not isinstance(palette, tuple) or not all(isinstance(item, str) for item in palette):
        return "chart_palette: expected a list of hex colours, e.g. ['#2a78d6', '#eb6834']."
    for item in palette:
        if not is_hex(item):
            return not_hex("chart_palette", item)
    if not 2 <= len(palette) <= MAX_PALETTE:
        return (
            f"chart_palette: give between 2 and {MAX_PALETTE} colours, in the order the "
            f"series take them; got {len(palette)}."
        )
    normal = [hex_colour(item) for item in palette]
    for index, item in enumerate(normal):
        if item in normal[:index]:
            return f"chart_palette: {palette[index]!r} is given twice; two series would look alike."
    if not is_hex(sequential):
        return not_hex("chart_sequential", sequential)
    if (
        not isinstance(diverging, tuple)
        or len(diverging) != 2
        or not all(isinstance(item, str) for item in diverging)
    ):
        return (
            "chart_diverging: give two colours, the low end first and the high end "
            "second, e.g. ['#e34948', '#2a78d6']."
        )
    for item in diverging:
        if not is_hex(item):
            return not_hex("chart_diverging", item)
    if hex_colour(diverging[0]) == hex_colour(diverging[1]):
        return "chart_diverging: the two ends are the same colour, so the scale would not diverge."
    if not is_hex(text):
        return not_hex("chart_text_color", text)
    ratio = contrast(text, BACKGROUND)
    if ratio < MIN_TEXT_CONTRAST:
        return (
            f"chart_text_color: {text!r} on the charts' white background has a contrast of "
            f"{ratio:.1f}:1; text needs at least {MIN_TEXT_CONTRAST}:1."
        )
    if not is_hex(grid):
        return not_hex("chart_grid_color", grid)
    if font is not None:
        if not isinstance(font, str) or not font_names(font):
            return "chart_font: expected font names separated by commas, e.g. 'Inter, sans-serif'."
        if _FONT_FORBIDDEN.search(font) or len(font) > 200:
            return "chart_font: a list of font names separated by commas, without ; { } < >."
    return None


def font_names(stack: str) -> list[str]:
    """The names of a font stack as CSS writes one, quotes stripped."""

    return [name.strip().strip("'\"").strip() for name in stack.split(",") if name.strip("'\" ")]


def resolve_font(stack: str | None) -> str | None:
    """The first face of ``stack`` installed where the chart is drawn — a
    generic family (``serif``, ``sans-serif``, ``system-ui``…) resolved to the
    face matplotlib uses for it — or None when none is (the charts' default)."""

    if not stack:
        return None
    from matplotlib import font_manager

    installed = {entry.name.lower(): entry.name for entry in font_manager.fontManager.ttflist}
    for name in font_names(stack):
        key = name.lower()
        if key in installed:
            return installed[key]
        if key in _GENERIC_FONTS:
            properties = font_manager.FontProperties(family=_GENERIC_FONTS[key])
            path = font_manager.findfont(properties, fallback_to_default=True)
            return font_manager.FontProperties(fname=path).get_name()
    return None


# ─── the colours a chart is drawn in ─────────────────────────────────────────


@dataclass(frozen=True)
class ChartColours:
    """A theme's chart colours, resolved: what :func:`drawing` hands a chart."""

    palette: tuple[str, ...] = PALETTE
    sequential: str = SEQUENTIAL
    diverging: tuple[str, str] = DIVERGING
    text: str = TEXT
    grid: str = GRID
    #: The face the charts' text is set in; None is matplotlib's default.
    font: str | None = None

    @classmethod
    def of(cls, theme: ReportTheme | None) -> ChartColours:
        """The chart colours of ``theme`` (None: the default theme's)."""

        if theme is None:
            return cls()
        return cls(
            palette=tuple(hex_colour(colour) for colour in theme.chart_palette),
            sequential=hex_colour(theme.chart_sequential),
            diverging=(hex_colour(theme.chart_diverging[0]), hex_colour(theme.chart_diverging[1])),
            text=hex_colour(theme.chart_text_color),
            grid=hex_colour(theme.chart_grid_color),
            font=resolve_font(theme.chart_font),
        )

    @functools.cached_property
    def muted(self) -> str:
        """Secondary text (notes, headers): the text colour lightened as far
        as it still reads on the background (:data:`MIN_TEXT_CONTRAST`)."""

        low, high = 0.0, 1.0
        for _ in range(24):
            middle = (low + high) / 2.0
            if contrast(mix(self.text, BACKGROUND, middle), BACKGROUND) >= MIN_TEXT_CONTRAST:
                low = middle
            else:
                high = middle
        return mix(self.text, BACKGROUND, low)

    @property
    def neutral(self) -> str:
        return NEUTRAL

    def rc(self) -> dict[str, Any]:
        """matplotlib settings for the text, the ticks, the grid and the font."""

        settings: dict[str, Any] = {
            "text.color": self.text,
            "axes.labelcolor": self.text,
            "xtick.color": self.text,
            "ytick.color": self.text,
            "grid.color": self.grid,
            "axes.edgecolor": self.grid,
        }
        if self.font:
            settings["font.family"] = [self.font]
        return settings

    def ink_on(self, fill: Any) -> str:
        """The colour of text written on ``fill``: white or the theme's text,
        whichever reads better — black when neither reaches
        :data:`MIN_TEXT_CONTRAST`, which one of white and black always does."""

        best = max(("#ffffff", self.text), key=lambda ink: contrast(ink, fill))
        if contrast(best, fill) < MIN_TEXT_CONTRAST and contrast("#000000", fill) > contrast(
            best, fill
        ):
            return "#000000"
        return best

    def ordinal(self, count: int) -> list[str]:
        """``count`` steps of the sequential colour, light to dark: the
        lightest still :data:`MIN_STEP_CONTRAST` against the background, the
        darkest the colour at half its lightness."""

        light = self.sequential
        for share in (step / 100.0 for step in range(95, -1, -1)):
            candidate = mix(self.sequential, BACKGROUND, share)
            if contrast(candidate, BACKGROUND) >= MIN_STEP_CONTRAST:
                light = candidate
                break
        dark = mix(self.sequential, "#000000", 0.5)
        if count == 1:
            return [self.sequential]
        return _blend([light, self.sequential, dark], count)

    def series(self, count: int, *, ordered: bool = False) -> list[str]:
        """``count`` colours, one per series, none repeated — the palette in
        its order; the steps of an ordered scale from :meth:`ordinal`. Past
        the palette, its colours lighter, then darker, then hues spaced round
        the wheel (as :func:`~siamang.reporting.chart_parts.series_colours`)."""

        if ordered and count > 1:
            return self.ordinal(count)
        base = list(self.palette)
        if count <= len(base):
            return base[:count]
        if count <= 3 * len(base):
            lighter = [mix(colour, "#ffffff", 0.5) for colour in base]
            darker = [mix(colour, "#000000", 0.4) for colour in base]
            return base + (lighter + darker)[: count - len(base)]
        import seaborn as sns

        hues = [to_hex(colour) for colour in sns.color_palette("husl", count + 1)[:count]]
        return [
            mix(colour, "#000000", 0.3) if index % 2 else colour
            for index, colour in enumerate(hues)
        ]

    def diverging_steps(self, count: int) -> list[str]:
        """``count`` colours from the low end to the high end: each arm from
        its end to a tint of it :data:`INNER_TINT` of the way to white — the
        inner tints of the two arms still apart for a colour-blind reader, and
        2:1 on white — and the middle of an odd count :data:`MIDPOINT` (a
        Likert chart's neutral answer takes :data:`NEUTRAL` there)."""

        arm = count // 2
        shares = [INNER_TINT * index / max(arm - 1, 1) for index in range(arm)]
        low = [mix(self.diverging[0], BACKGROUND, share) for share in shares]
        high = [mix(self.diverging[1], BACKGROUND, share) for share in shares]
        return low + ([MIDPOINT] if count % 2 else []) + high[::-1]

    def colormap(self, kind: str) -> Any:
        """A continuous colour map: ``"sequential"`` from near white to dark,
        or ``"diverging"`` from the low end through :data:`MIDPOINT` to the
        high end (each end darkened a little, so the extremes stand out)."""

        from matplotlib.colors import LinearSegmentedColormap

        if kind == "sequential":
            stops = [
                mix(self.sequential, BACKGROUND, 0.92),
                self.sequential,
                mix(self.sequential, "#000000", 0.5),
            ]
        else:
            low, high = self.diverging
            stops = [
                mix(low, "#000000", 0.35),
                low,
                MIDPOINT,
                high,
                mix(high, "#000000", 0.35),
            ]
        return LinearSegmentedColormap.from_list(f"theme_{kind}", stops)


def _blend(stops: list[str], count: int) -> list[str]:
    """``count`` colours evenly along the lines between ``stops`` (in sRGB)."""

    if count <= 0:
        return []
    if count == 1:
        return [stops[len(stops) // 2]]
    out = []
    for index in range(count):
        position = index / (count - 1) * (len(stops) - 1)
        segment = min(int(position), len(stops) - 2)
        out.append(mix(stops[segment], stops[segment + 1], position - segment))
    return out


def theme_colours(theme: ReportTheme | None) -> ChartColours:
    """:meth:`ChartColours.of`, kept for the last theme asked: a report asks
    once per chart, and a font is looked up among the installed ones."""

    global _LAST
    if _LAST is not None and _LAST[0] == theme:
        return _LAST[1]
    colours = ChartColours.of(theme)
    _LAST = (theme, colours)
    return colours


_LAST: tuple[Any, ChartColours] | None = None


def from_env() -> ChartColours:
    """The chart colours of the theme ``SIAMANG_REPORT_THEME`` names, else the
    default theme's: what a chart that reads the theme is drawn in outside a
    report (at its node)."""

    from siamang.reporting.theme import ReportTheme

    return theme_colours(ReportTheme.from_env())


# ─── drawing ─────────────────────────────────────────────────────────────────

_ACTIVE: contextvars.ContextVar[ChartColours | None] = contextvars.ContextVar(
    "siamang_chart_colours", default=None
)


def reads_theme(chart: Any) -> bool:
    """Whether ``chart`` takes its colours from the theme: its palette, or a
    heatmap's colour map, is :data:`THEME`."""

    return any(getattr(chart, name, None) == THEME for name in ("palette", "cmap"))


def themed() -> ChartColours | None:
    """The colours of the chart being drawn, when it reads the theme."""

    return _ACTIVE.get()


def current() -> ChartColours:
    """The colours a palette of :data:`THEME` names just now: the chart's
    being drawn, else those of the theme ``SIAMANG_REPORT_THEME`` names."""

    return _ACTIVE.get() or from_env()


@contextlib.contextmanager
def drawing(chart: Any) -> Iterator[ChartColours | None]:
    """While ``chart`` is built: its colours, when it reads the theme — those
    a report asked for (``chart._colours``), else :func:`from_env` — with the
    theme's text, grid and font as matplotlib's settings. Those are restored
    afterwards, so a chart that reads the theme leaves nothing behind for the
    next chart. A chart that does not read the theme is built as it always
    was, and the role functions below answer it with its own colours."""

    colours = (getattr(chart, "_colours", None) or from_env()) if reads_theme(chart) else None
    token = _ACTIVE.set(colours)
    try:
        if colours is None:
            yield None
        else:
            import matplotlib

            with matplotlib.rc_context(colours.rc()):
                yield colours
                figure = getattr(chart, "_fig", None)
                if figure is not None:
                    # Drawn once here: a tick matplotlib makes at the save
                    # copies this one's colour and face, not the settings of
                    # whatever is drawn after.
                    figure.draw_without_rendering()
    finally:
        _ACTIVE.reset(token)
    if hasattr(chart, "_drawn_with"):
        chart._drawn_with = colours


def set_theme(**kwargs: Any) -> None:
    """``seaborn.set_theme(**kwargs)`` — with the theme's palette, text, grid
    and font when the chart being drawn reads the theme."""

    import seaborn as sns

    colours = themed()
    if colours is None:
        sns.set_theme(**kwargs)
        return
    if kwargs.get("palette") == THEME:
        kwargs["palette"] = list(colours.palette)
    sns.set_theme(**kwargs, rc=colours.rc())


# The roles a chart module asks for. Each takes the colour the chart has always
# used and returns it unless the chart being drawn reads the theme.


def text(default: Any) -> Any:
    colours = themed()
    return default if colours is None else colours.text


def muted(default: Any) -> Any:
    colours = themed()
    return default if colours is None else colours.muted


def grid(default: Any) -> Any:
    colours = themed()
    return default if colours is None else colours.grid


def series(default: Any, index: int = 0) -> Any:
    """The palette's ``index``-th colour (the first two: blue and orange)."""

    colours = themed()
    return default if colours is None else colours.palette[index % len(colours.palette)]


def low(default: Any) -> Any:
    colours = themed()
    return default if colours is None else colours.diverging[0]


def high(default: Any) -> Any:
    colours = themed()
    return default if colours is None else colours.diverging[1]


def neutral(default: Any) -> Any:
    colours = themed()
    return default if colours is None else colours.neutral


def tint(default: Any, colour: Any, share: float) -> Any:
    """``colour`` moved ``share`` of the way to white (a lighter shade of a
    theme's colour), or ``default``."""

    return default if themed() is None else mix(colour, BACKGROUND, share)


def cmap(default: Any, kind: str = "diverging") -> Any:
    """``default`` (a colour map or its name), or the theme's ``kind`` of map."""

    colours = themed()
    return default if colours is None else colours.colormap(kind)


def ink_on(fill: Any, default: Any) -> Any:
    colours = themed()
    return default if colours is None else colours.ink_on(fill)


def label_cells(ax: Any) -> None:
    """In a chart of the theme's colours, each value seaborn wrote in a
    heatmap's cell in the ink that reads on that cell (:meth:`ChartColours.ink_on`)."""

    colours = themed()
    if colours is None or not ax.collections:
        return
    import numpy as np

    mesh = ax.collections[0]
    values = np.ma.asarray(mesh.get_array())
    if values.ndim != 2:
        return
    for label in ax.texts:
        x, y = label.get_position()
        row, column = int(y), int(x)
        if 0 <= row < values.shape[0] and 0 <= column < values.shape[1]:
            label.set_color(colours.ink_on(mesh.cmap(mesh.norm(values[row, column]))))


def color_palette(name: Any, count: int | None = None) -> Any:
    """``seaborn.color_palette(name, count)``, or the theme's categorical colours."""

    import seaborn as sns

    if name == THEME:
        colours = current()
        return sns.color_palette(list(colours.series(count) if count else colours.palette))
    return sns.color_palette(name) if count is None else sns.color_palette(name, count)


def diverging_palette(name: Any, count: int) -> list[Any]:
    """``count`` colours of the diverging palette ``name``, or of the theme's pair."""

    import seaborn as sns

    if name == THEME:
        return [rgb(colour) for colour in current().diverging_steps(count)]
    return list(sns.color_palette(name, count))


def palette_for(name: Any, levels: Sequence[Any]) -> Any:
    """What a seaborn plot's ``palette=`` takes: ``name``, or the theme's
    colours for ``levels`` in their order."""

    if name == THEME:
        return dict(zip(levels, current().series(max(len(levels), 1)), strict=False))
    return name


# ─── in a report ─────────────────────────────────────────────────────────────


def in_report(chart: Any, theme: ReportTheme | None) -> Any:
    """``chart`` as a report in ``theme`` shows it.

    A chart that does not read the theme is itself. One that does is drawn in
    the report theme's colours: built in them when it has not been drawn yet,
    else — drawn at its node in other colours — a copy drawn from its
    parameters, which is kept on the chart for the report's next rendering
    (its Markdown, then its HTML). The report renders the copy and releases
    its figure (``SurveyChart.release``), so what is kept is its picture, not
    an open figure: closing a figure does not free it while something still
    refers to it.
    """

    if not reads_theme(chart):
        return chart
    wanted = theme_colours(theme)
    if getattr(chart, "_fig", None) is None and getattr(chart, "_drawn_with", None) is None:
        chart._colours = wanted
        chart._ensure_built()
        return chart
    if getattr(chart, "_drawn_with", None) == wanted:
        return chart
    kept = getattr(chart, "_redrawn", None)
    if kept is not None and kept._drawn_with == wanted:
        return kept
    copy = dataclasses.replace(chart)
    copy._colours = wanted
    copy._ensure_built()
    chart._redrawn = copy
    return copy


__all__ = [
    "BACKGROUND",
    "DIVERGING",
    "GRID",
    "MIDPOINT",
    "MIN_STEP_CONTRAST",
    "MIN_TEXT_CONTRAST",
    "NEUTRAL",
    "PALETTE",
    "SEQUENTIAL",
    "TEXT",
    "THEME",
    "VISIONS",
    "ChartColours",
    "contrast",
    "current",
    "distance",
    "drawing",
    "from_env",
    "in_report",
    "reads_theme",
    "themed",
]
