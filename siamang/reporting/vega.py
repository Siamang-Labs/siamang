"""Interactive charts: a chart as a Vega-Lite spec, and the libraries that draw it.

Every chart the reporting package draws with matplotlib — a picture, which
Markdown, Excel, print and every earlier output keep — can also say what it
draws as a **Vega-Lite 6** spec (:meth:`SurveyChart.vega_lite()
<siamang.reporting.charts.SurveyChart.vega_lite>`), which a browser draws with
tooltips, a legend that hides and shows its series, and zoom where it helps. A
report saved with ``interactive=True`` shows its charts so in its HTML and
writes each figure's spec beside its picture in its Markdown (``fig_3.png``,
``fig_3.vl.json``); a Live tile of a chart publishes its spec with it.

A spec says what the picture says and nothing more:

- its data is **inline** and holds only what the chart draws — the counts,
  percentages, means, intervals and bins, computed in Python by the same code
  that draws the picture, so the two cannot disagree. Never a respondent's row:
  a chart that plots respondents themselves (a scatter plot's points, a box
  plot's outliers and, with *Show points*, its points) carries the values it
  plots and nothing else — no id, no other answer;
- its title, axis titles, legend and notes are the picture's — the base, the
  weight and the missing codes left out at the chart's foot, wrapped (as its
  title is) to the width the chart is drawn at;
- its colors are those the picture was drawn in, with the report Look's text,
  grid and font (:mod:`siamang.reporting.chart_theme`);
- a tooltip on every mark gives its label, its value written as the picture
  writes it, and its base;
- where there are series, a click on the legend hides one (and a second click
  shows it again; a double click shows them all);
- a ``description`` says in words what the chart shows, for a screen reader.

This module holds what the specs share (the look, the notes, the formats, the
toggle) and the libraries: Vega 6.4.0, Vega-Lite 6.4.3 and Vega-Embed 7.3.0,
vendored in ``siamang/reporting/assets/vega`` with their licenses. A report
copies them into its HTML once, inline — a report is read offline and mailed,
so nothing is loaded from a CDN.
"""

from __future__ import annotations

import functools
import json
import math
import textwrap
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

#: The Vega-Lite major version every spec is written for, and its schema.
VEGA_LITE_MAJOR = 6
SCHEMA = "https://vega.github.io/schema/vega-lite/v6.json"
#: The vendored libraries' versions (assets/vega/README.md).
VERSIONS = {"vega": "6.4.0", "vega-lite": "6.4.3", "vega-embed": "7.3.0"}
#: The builds, in the order a page loads them: Vega-Lite needs Vega, and
#: Vega-Embed both.
LIBRARIES = ("vega.min.js", "vega-lite.min.js", "vega-embed.min.js")

#: The face of a chart that does not read the theme: the pictures' own
#: (matplotlib's DejaVu Sans) where it is installed, else a sans-serif.
DEFAULT_FONT = '"DejaVu Sans", Verdana, "Helvetica Neue", Arial, sans-serif'
#: The width a chart's picture is laid out for, in CSS pixels per inch of its
#: ``figsize``: a 10-inch figure is a 720-pixel column, a report's measure.
PX_PER_INCH = 72.0
#: The notes' size and line height, in pixels.
NOTE_SIZE = 10.5
NOTE_LINE = 14.0
#: The name of the selection a legend click toggles.
HIDDEN = "hidden"
#: How opaque a hidden series is: all but gone, still where it was.
HIDDEN_OPACITY = 0.07

# ─── the look ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Look:
    """The text, grid and font a spec is drawn in."""

    text: str
    muted: str
    grid: str
    font: str
    background: str = "#ffffff"


def look_of(chart: Any) -> Look:
    """The look of ``chart``: the colors it was drawn in when it reads the
    report theme (``palette="theme"``), else the default theme's text and grid
    — what a report's page is set in — with the pictures' own face."""

    from siamang.reporting import chart_theme

    colours = getattr(chart, "_drawn_with", None)
    drawn = colours if isinstance(colours, chart_theme.ChartColours) else None
    theme = drawn or chart_theme.ChartColours()
    font = (drawn.font_stack if drawn is not None else None) or DEFAULT_FONT
    return Look(text=theme.text, muted=theme.muted, grid=theme.grid, font=font)


def config(look: Look) -> dict[str, Any]:
    """The spec's ``config``: the look, and sizes a report's page reads at."""

    return {
        "background": look.background,
        "font": look.font,
        # Room past the drawing: a browser's face measures a little otherwise
        # than it draws, and the last line of the notes or a legend's title
        # was cut by a few pixels.
        "padding": {"left": 8, "top": 8, "right": 16, "bottom": 16},
        "view": {"stroke": None},
        "title": {
            "color": look.text,
            "subtitleColor": look.muted,
            "anchor": "start",
            "fontSize": 15,
            "fontWeight": 600,
            "subtitleFontSize": 12,
            "offset": 12,
        },
        "axis": {
            "labelColor": look.text,
            "titleColor": look.text,
            "gridColor": look.grid,
            "domainColor": look.muted,
            "tickColor": look.muted,
            "labelFontSize": 11,
            "titleFontSize": 12,
            "titleFontWeight": "normal",
            "labelLimit": 260,
        },
        "legend": {
            "labelColor": look.text,
            "titleColor": look.text,
            "labelFontSize": 11,
            "titleFontSize": 11,
            "titleFontWeight": 600,
            "labelLimit": 220,
            "titleLimit": 220,
            "symbolType": "square",
        },
        "header": {"labelColor": look.text, "titleColor": look.text, "labelFontSize": 11},
        "text": {"color": look.text, "fontSize": 11},
        "concat": {"spacing": 14},
    }


# ─── what the chart says ─────────────────────────────────────────────────────


def wrap(text: str, width: int) -> list[str]:
    """``text`` in lines of at most ``width`` characters, its own lines kept."""

    lines: list[str] = []
    for paragraph in str(text).split("\n"):
        lines.extend(textwrap.wrap(paragraph, max(8, width), break_long_words=False) or [""])
    return lines


#: The widths (characters) the notes are wrapped to, and the least width of
#: the chart's container (pixels) at which each is used — 6.2 pixels a
#: character at :data:`NOTE_SIZE` in the pictures' wide face, and the
#: padding: the lines follow the width the chart is drawn at, which only the
#: browser knows (``containerSize()``).
NOTE_WIDTHS = (
    (150, 960.0),
    (120, 780.0),
    (100, 650.0),
    (80, 530.0),
    (64, 430.0),
    (52, 350.0),
    (44, 300.0),
    (36, 0.0),
)
#: The same for the title, in its bold face at 15 pixels (about 9 a character).
TITLE_WIDTHS = ((90, 850.0), (72, 690.0), (60, 580.0), (48, 470.0), (38, 380.0), (30, 0.0))


def _by_width(text: str, widths: tuple[tuple[int, float], ...]) -> dict[str, str] | str:
    """``text``'s lines for the width the chart is drawn at: an expression
    that picks, by the container's width, ``text`` wrapped to the widest
    width of ``widths`` that fits — or the text itself, when it is one line
    at every width."""

    variants = [(width, least, wrap(text, width)) for width, least in widths]
    if all(len(lines) == 1 for _, _, lines in variants):
        return str(text)
    choice = json.dumps(variants[-1][2], ensure_ascii=False)
    for _, least, lines in reversed(variants[:-1]):
        choice = (
            f"containerSize()[0] >= {least:g} ? {json.dumps(lines, ensure_ascii=False)}"
            f" : ({choice})"
        )
    return {"expr": choice}


def notes_title(notes: list[str], look: Look) -> dict[str, Any] | None:
    """The notes under the chart — the base, the weight, what was left out —
    as the chart view's title at its foot, from its left edge, in the muted
    text and wrapped to the width the chart is drawn at. None without notes."""

    notes = [note for note in notes if note and note.strip()]
    if not notes:
        return None
    return {
        "text": _by_width("\n".join(notes), NOTE_WIDTHS),
        "orient": "bottom",
        "anchor": "start",
        "frame": "bounds",
        "fontSize": NOTE_SIZE,
        "fontWeight": "normal",
        "lineHeight": NOTE_LINE,
        "color": look.muted,
        "offset": 14,
    }


def title(text: str, subtitle: list[str] | None = None) -> dict[str, Any]:
    """A spec's ``title``, wrapped to the width the chart is drawn at, with
    its subtitle (the weight a chart does not apply)."""

    heading = " ".join(str(text).split())
    out: dict[str, Any] = {"text": _by_width(heading, TITLE_WIDTHS), "frame": "bounds"}
    if subtitle:
        out["subtitle"] = subtitle
    return out


def finish(
    chart: Any,
    main: dict[str, Any],
    *,
    heading: str,
    notes: list[str],
    description: str,
    subtitle: list[str] | None = None,
    kind: str,
) -> dict[str, Any]:
    """The whole spec: ``main`` (a view, a layer or a concatenation) under its
    title, the notes at its foot, the look, and what it is for a screen reader.

    With notes, ``main`` is the one view of a ``vconcat`` and the notes are
    its title at the foot: the chart's own title stays over its legend, and
    the notes start at the chart's left edge, not its plot's.

    ``kind`` names the chart in ``usermeta`` (``{"siamang": {"chart": …}}``),
    with the notes as a list — what a host that shows the chart needs besides
    the drawing."""

    look = look_of(chart)
    below = notes_title(notes, look)
    spec: dict[str, Any] = {"$schema": SCHEMA}
    spec["title"] = title(heading, subtitle)
    spec["description"] = description
    if below is not None:
        spec["vconcat"] = [{**main, "title": below}]
    else:
        spec.update(main)
    spec["autosize"] = {"type": "fit-x", "contains": "padding"}
    spec["config"] = config(look)
    spec["usermeta"] = {
        "siamang": {
            "chart": kind,
            "notes": [note for note in notes if note],
            "vega-lite": VERSIONS["vega-lite"],
        }
    }
    return spec


# ─── numbers ─────────────────────────────────────────────────────────────────


def number(value: Any) -> float | None:
    """A value for the spec's data: a float, or None for NaN and infinity
    (JSON has neither, and a gap is what they are on a chart)."""

    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def percent_axis() -> dict[str, Any]:
    """A value axis of percentages written as the pictures write them: 20%."""

    return {"format": ",.0f", "labelExpr": "datum.label + '%'"}


def thousands_axis() -> dict[str, Any]:
    """A count axis with its thousands separated (20,000), as the pictures'."""

    return {"format": ",~f"}


def base_text(n: int, weighted: float | None = None) -> str:
    """A tooltip's base: ``1,234 respondents`` (``, weighted 1,201.5``)."""

    text = f"{n:,} {'respondent' if n == 1 else 'respondents'}"
    return text + (f" (weighted {weighted:,.1f})" if weighted is not None else "")


def hex_colour(colour: Any) -> str:
    """A matplotlib color (a name, a gray level as text, an RGB tuple) as hex."""

    from matplotlib.colors import to_hex

    return str(to_hex(colour, keep_alpha=False))


def unique(labels: list[str]) -> list[str]:
    """``labels`` made unique for an axis — a second answer of the same label
    followed by an invisible mark — so two bars are never drawn as one."""

    seen: dict[str, int] = {}
    out = []
    for label in labels:
        count = seen.get(label, 0)
        seen[label] = count + 1
        out.append(label + "​" * count)
    return out


def multiline_labels() -> str:
    """An axis's ``labelExpr`` that writes a label's lines one under another."""

    return "split(datum.label, '\\n')"


def toggle(field: str) -> dict[str, Any]:
    """The selection a click on the legend toggles: each click on an entry
    hides its series or shows it again; a double click shows them all."""

    return {
        "name": HIDDEN,
        "select": {"type": "point", "fields": [field], "toggle": "true"},
        "bind": "legend",
    }


def shown(value: Any = 1, hidden: Any = HIDDEN_OPACITY) -> dict[str, Any]:
    """An ``opacity`` encoding: ``value``, or ``hidden`` for a series hidden
    by a click on the legend (:func:`toggle`)."""

    return {"condition": {"param": HIDDEN, "empty": False, "value": hidden}, "value": value}


def tooltip(*fields: tuple[str, str]) -> list[dict[str, Any]]:
    """A tooltip of ``(field, title)`` pairs, written as the data holds them."""

    return [{"field": field, "type": "nominal", "title": name} for field, name in fields]


def listing(pairs: list[tuple[str, str]], limit: int = 12) -> str:
    """``"North 41.2%, South 30.1% and 3 more"`` for a description."""

    items = [f"{name} {value}" for name, value in pairs]
    if len(items) > limit:
        return ", ".join(items[:limit]) + f" and {len(items) - limit} more"
    return ", ".join(items)


def plain(label: str) -> str:
    """A label as one line: its lines joined, a group's "(n = …)" left out."""

    head = str(label).split("\n(n = ", 1)[0]
    return " ".join(head.replace("​", "").split())


# ─── the libraries ───────────────────────────────────────────────────────────


@functools.cache
def library(name: str) -> str:
    """The text of one vendored build (:data:`LIBRARIES`), without its
    ``sourceMappingURL`` comment, checked to be safe inside a ``<script>``."""

    if name not in LIBRARIES:
        raise ValueError(f"No vendored library {name!r}; the libraries are {', '.join(LIBRARIES)}.")
    text = (resources.files("siamang.reporting.assets.vega") / name).read_text("utf-8")
    lines = text.rstrip("\n").split("\n")
    if lines and lines[-1].startswith("//# sourceMappingURL="):
        lines = lines[:-1]
    text = "\n".join(lines)
    lowered = text.lower()
    if "</script" in lowered or "<!--" in text:
        raise ValueError(f"{name} cannot be written inside a <script> element as it is.")
    return text


def libraries_size() -> int:
    """The bytes the three libraries add to a document."""

    return sum(len(library(name).encode("utf-8")) for name in LIBRARIES)


def script_json(value: Any) -> str:
    """``value`` as JSON that is safe inside ``<script type="application/json">``:
    ``<``, ``>`` and ``&`` escaped, so no label can end the element."""

    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


# ─── beside a picture ────────────────────────────────────────────────────────


def spec_path(picture: str | Path) -> Path:
    """Where the spec of the chart pictured in ``picture`` goes: beside it,
    ``fig_3.png`` → ``fig_3.vl.json``."""

    path = Path(picture)
    return path.with_name(path.stem + ".vl.json")


def write_spec(chart: Any, path: str | Path) -> Path | None:
    """Write ``chart``'s Vega-Lite spec to ``path`` (a ``.vl.json``) and return
    it — or None, writing nothing, when the chart has no interactive form."""

    make = getattr(chart, "vega_lite", None)
    spec = make() if callable(make) else None
    if spec is None:
        return None
    path = Path(path)
    path.write_text(
        json.dumps(spec, ensure_ascii=False, indent=1, allow_nan=False) + "\n", encoding="utf-8"
    )
    return path


__all__ = [
    "DEFAULT_FONT",
    "LIBRARIES",
    "SCHEMA",
    "VEGA_LITE_MAJOR",
    "VERSIONS",
    "Look",
    "config",
    "finish",
    "notes_title",
    "libraries_size",
    "library",
    "look_of",
    "script_json",
    "spec_path",
    "write_spec",
]
