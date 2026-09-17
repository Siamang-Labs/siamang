"""How a report looks: a small declarative theme and the stylesheet it compiles to.

:class:`Report` has always been able to write HTML, but only as
``markdown.markdown(...)`` — a bare fragment with no document around it and no
stylesheet in it. Every caller therefore had to invent its own look, which is
another way of saying the report had none of its own: the same document read
differently in a browser, in a saved file and on paper.

:class:`ReportTheme` is the missing piece, and it is deliberately the same shape
as :class:`~siamang.frontend.theme.ui_config.UIConfig`, which does this job for
the questionnaire: **one named preset plus individually overridable tokens**,
stored sparsely, compiled to CSS custom properties. A report and the survey it
came from can then be set in the same type without either knowing about the
other.

The stylesheet is a pure function of the theme — no clock, no locale, no
network, no ``@import`` — so the same theme gives the same bytes on every
machine, which is what lets a golden file pin it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, fields
from typing import Any

# ─── presets ─────────────────────────────────────────────────────────────────
# The stacks are the questionnaire's own (frontend.theme.ui_config.FONT_PRESETS),
# repeated here rather than imported: `siamang.reporting` is used headless, and
# `siamang.frontend` is the survey builder with everything that implies. A test
# imports both and fails if the two drift, which is the part that actually
# matters — a report and its questionnaire should not disagree about what
# "academic" means.
#
# Named stacks only, never a webfont link: a report is read offline, printed,
# and mailed as a file, and a stylesheet that fetches a font renders differently
# depending on whether the reader had a network. Where the face is not
# installed the next name in the stack is a deliberate choice, not a fallback.
PRESETS: dict[str, dict[str, str]] = {
    "academic": {
        "body": '"Source Serif 4", "Charter", Georgia, "Times New Roman", serif',
        "heading": '"Source Serif 4", "Charter", Georgia, serif',
    },
    "modern": {
        "body": '"Inter", "Helvetica Neue", system-ui, -apple-system, sans-serif',
        "heading": '"Inter", "Helvetica Neue", system-ui, sans-serif',
    },
    "humanist": {
        "body": '"Nunito", "Segoe UI", system-ui, sans-serif',
        "heading": '"Nunito", "Segoe UI", system-ui, sans-serif',
    },
}
MONO_STACK = '"JetBrains Mono", "Menlo", "Consolas", monospace'

# font-size · line-height · gap between blocks · table cell padding
_DENSITY: dict[str, tuple[str, str, str, str]] = {
    "compact": ("14px", "1.45", "14px", "3px 8px"),
    "comfortable": ("15.5px", "1.6", "20px", "5px 10px"),
    "spacious": ("16.5px", "1.75", "28px", "7px 12px"),
}

# `screen` has no page box at all: the measure is the theme's width, as on any
# other web document. The other two are paper, so the text block is the page
# minus its margins and the width token stops applying.
_PAGE: dict[str, str] = {
    "screen": "",
    "a4": "A4",
    "letter": "Letter",
}
_PAGE_MARGIN: dict[str, str] = {"screen": "", "a4": "22mm", "letter": "0.9in"}

_TABLE_STYLES = ("rules", "grid", "zebra")
_ALIGNMENTS = ("left", "center", "right")
_CAPTION_POSITIONS = ("below", "above")
_TABLE_WIDTHS = ("auto", "full")

# A CSS length as this theme accepts one: a number and a unit, or a percentage.
# Deliberately narrow — the point of validating is to catch "wide" and "60"
# before a run, not to reimplement the CSS grammar.
_LENGTH = re.compile(r"^-?\d+(\.\d+)?(px|pt|pc|em|rem|ch|ex|%|cm|mm|in|vw|vh)$")
_COLOR = re.compile(r"^(#[0-9a-fA-F]{3,8}|[a-zA-Z]+|(rgb|hsl)a?\([^;{}<>]*\))$")


class ReportThemeError(ValueError):
    """A theme field was given a value the stylesheet could not use."""


@dataclass(frozen=True, slots=True)
class ReportTheme:
    """The look of a rendered report.

    Every field is optional and ``None`` means "whatever the preset says", so a
    theme stored in a document carries only what was actually chosen.
    """

    # ── presets ──────────────────────────────────────────────────────
    font_preset: str = "academic"  # academic | humanist | modern
    density: str = "comfortable"  # compact | comfortable | spacious
    table_style: str = "rules"  # rules | grid | zebra
    page: str = "screen"  # screen | a4 | letter

    # ── measure and type ─────────────────────────────────────────────
    width: str | None = None  # the measure on screen; ignored on paper
    font_size: str | None = None
    line_height: str | None = None
    table_font_size: str | None = None
    font_family: str | None = None
    heading_font_family: str | None = None
    mono_font_family: str | None = None

    # ── color ────────────────────────────────────────────────────────
    text_color: str = "#1a1a1a"
    muted_text_color: str = "#5a5a5a"
    border_color: str = "#d9d9de"
    accent_color: str = "#2c5f8a"
    background_color: str = "#ffffff"

    # ── tables ───────────────────────────────────────────────────────
    table_width: str = "auto"  # auto | full
    align_numeric: bool = True

    # ── figures ──────────────────────────────────────────────────────
    figure_width: str | None = None  # default width of a figure
    figure_align: str = "center"  # left | center | right
    figure_dpi: int = 150  # what the figures are written at
    caption_position: str = "below"  # below | above

    # ── numbering ────────────────────────────────────────────────────
    number_tables: bool = False
    number_figures: bool = False
    table_label: str = "Table"
    figure_label: str = "Figure"

    # ── escape hatch ─────────────────────────────────────────────────
    # Appended after the generated stylesheet, so it wins. Unlike everything
    # above it is checked by nothing: a bad rule reaches the reader.
    custom_css: str | None = None

    # ── derived ──────────────────────────────────────────────────────
    def __post_init__(self) -> None:
        _validate(self)

    @property
    def effective_body_font(self) -> str:
        return self.font_family or PRESETS[self.font_preset]["body"]

    @property
    def effective_heading_font(self) -> str:
        return self.heading_font_family or PRESETS[self.font_preset]["heading"]

    @property
    def effective_mono_font(self) -> str:
        return self.mono_font_family or MONO_STACK

    def tokens(self) -> dict[str, str]:
        """The CSS custom properties, resolved. Handy for tests and for a host
        that wants to style something of its own to match."""

        size, line, gap, pad = _DENSITY[self.density]
        return {
            "--report-width": self.width or "720px",
            "--report-font-size": self.font_size or size,
            "--report-line-height": self.line_height or line,
            "--report-body-font": self.effective_body_font,
            "--report-heading-font": self.effective_heading_font,
            "--report-mono-font": self.effective_mono_font,
            "--report-text": self.text_color,
            "--report-muted": self.muted_text_color,
            "--report-border": self.border_color,
            "--report-accent": self.accent_color,
            "--report-bg": self.background_color,
            "--report-block-gap": gap,
            "--report-cell-pad": pad,
            "--report-table-font-size": self.table_font_size or "0.87em",
            "--report-figure-width": self.figure_width or "100%",
        }

    def stylesheet(self) -> str:
        """The whole stylesheet for a report rendered with this theme."""

        root = "\n".join(f"  {name}: {value};" for name, value in self.tokens().items())
        parts = [_ROOT.format(tokens=root), _RULES, _TABLE_RULES[self.table_style]]
        if self.table_width == "full":
            parts.append(".siamang-report table { width: 100%; }")
        if self.align_numeric:
            parts.append(_NUMERIC)
        parts.append(_FIGURE.format(align=_FIGURE_ALIGN[self.figure_align]))
        if self.caption_position == "above":
            parts.append(_CAPTION_ABOVE)
        parts.append(_PRINT)
        if _PAGE[self.page]:
            parts.append(
                f"@page {{ size: {_PAGE[self.page]}; margin: {_PAGE_MARGIN[self.page]}; }}\n"
                ".siamang-report { max-width: none; padding: 0; }"
            )
        if self.custom_css:
            parts.append("/* custom_css */\n" + self.custom_css.strip())
        return "\n\n".join(part.strip() for part in parts if part.strip()) + "\n"

    # ── serialization ────────────────────────────────────────────────
    def to_dict(self) -> dict[str, Any]:
        """Only what differs from the defaults, in field order."""

        default = ReportTheme()
        return {
            f.name: getattr(self, f.name)
            for f in fields(self)
            if getattr(self, f.name) != getattr(default, f.name)
        }

    @classmethod
    def from_dict(cls, data: Any) -> ReportTheme:
        """Build a theme from a plain object, naming the first bad key."""

        if data is None:
            return cls()
        if not isinstance(data, dict):
            raise ReportThemeError(f"a report theme is an object, got {type(data).__name__}.")
        known = {f.name for f in fields(cls)}
        for key in data:
            if key not in known:
                raise ReportThemeError(f"unknown theme field {key!r}.")
        return cls(**data)

    @classmethod
    def from_env(cls) -> ReportTheme:
        """The theme named by ``SIAMANG_REPORT_THEME`` (a path to JSON), or the
        defaults. Mirrors ``SIAMANG_PROVENANCE``: whatever runs a flow — a
        platform, a research bundle's ``run.sh`` — can say how its reports
        should look without editing the flow."""

        import json
        import os
        from pathlib import Path

        path = os.environ.get("SIAMANG_REPORT_THEME", "").strip()
        if not path:
            return cls()
        try:
            return cls.from_dict(json.loads(Path(path).read_text("utf-8")))
        except (OSError, ValueError):
            # A missing or malformed file must not fail a run that would
            # otherwise have produced the report. The default look is correct,
            # just not the one that was asked for.
            return cls()


# ─── validation ──────────────────────────────────────────────────────────────

_ENUMS: dict[str, tuple[str, ...]] = {
    "font_preset": tuple(PRESETS),
    "density": tuple(_DENSITY),
    "table_style": _TABLE_STYLES,
    "page": tuple(_PAGE),
    "table_width": _TABLE_WIDTHS,
    "figure_align": _ALIGNMENTS,
    "caption_position": _CAPTION_POSITIONS,
}
_LENGTHS = (
    "width",
    "font_size",
    "table_font_size",
    "figure_width",
)
_COLORS = (
    "text_color",
    "muted_text_color",
    "border_color",
    "accent_color",
    "background_color",
)


def _validate(theme: ReportTheme) -> None:
    for name, allowed in _ENUMS.items():
        value = getattr(theme, name)
        if value not in allowed:
            raise ReportThemeError(f"{name}: {value!r} is not one of {', '.join(allowed)}.")
    for name in _LENGTHS:
        value = getattr(theme, name)
        if value is not None and not _LENGTH.match(str(value)):
            raise ReportThemeError(
                f"{name}: {value!r} is not a CSS length (a number and a unit, e.g. '720px', '60%')."
            )
    for name in _COLORS:
        value = getattr(theme, name)
        if value is not None and not _COLOR.match(str(value)):
            raise ReportThemeError(f"{name}: {value!r} is not a color.")
    if theme.line_height is not None:
        try:
            float(theme.line_height)
        except (TypeError, ValueError):
            raise ReportThemeError(
                f"line_height: {theme.line_height!r} is a number without a unit, e.g. '1.6'."
            ) from None
    if not isinstance(theme.figure_dpi, int) or isinstance(theme.figure_dpi, bool):
        raise ReportThemeError(f"figure_dpi: expected an integer, got {theme.figure_dpi!r}.")
    if not 72 <= theme.figure_dpi <= 600:
        raise ReportThemeError("figure_dpi: must be between 72 and 600.")
    for name in ("align_numeric", "number_tables", "number_figures"):
        if not isinstance(getattr(theme, name), bool):
            raise ReportThemeError(f"{name}: expected true or false.")
    # `custom_css` is not checked — that is what it is for — except that it must
    # not be able to close the <style> element it is written into and start
    # something else.
    if theme.custom_css and "</" in theme.custom_css:
        raise ReportThemeError("custom_css: '</' would close the stylesheet; it cannot be used.")


# ─── the stylesheet ──────────────────────────────────────────────────────────

_ROOT = """\
/* ── siamang report ─────────────────────────────────────────────────── */
:root {{
{tokens}
}}"""

_RULES = """\
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--report-bg);
  color: var(--report-text);
  font-family: var(--report-body-font);
  font-size: var(--report-font-size);
  line-height: var(--report-line-height);
  -webkit-text-size-adjust: 100%;
}
.siamang-report {
  max-width: var(--report-width);
  margin: 0 auto;
  padding: 40px 24px 72px;
}
.siamang-report > * + * { margin-top: var(--report-block-gap); }
h1, h2, h3, h4 {
  font-family: var(--report-heading-font);
  font-weight: 600;
  line-height: 1.25;
  margin: 0;
  text-wrap: balance;
}
h1 { font-size: 1.8em; }
h2 { font-size: 1.35em; }
h3 { font-size: 1.12em; }
h4 { font-size: 1em; }
.siamang-report > h2 { margin-top: calc(var(--report-block-gap) * 1.8); }
p { margin: 0; text-wrap: pretty; }
a { color: var(--report-accent); }
code, pre, .siamang-stats { font-family: var(--report-mono-font); font-size: 0.9em; }
blockquote {
  margin: 0;
  padding-left: 16px;
  border-left: 2px solid var(--report-border);
  color: var(--report-muted);
}
hr { border: 0; border-top: 1px solid var(--report-border); }
ul, ol { margin: 0; padding-left: 1.4em; }
li + li { margin-top: 4px; }
/* The table of contents `Report.combine` writes, and the provenance footer. */
.siamang-report h2#contents + ul { list-style: none; padding-left: 0; }"""

_TABLE_RULES = {
    # The research-paper table: rules above and below the head and under the
    # last row, nothing vertical. Numbers are read down a column, and a grid
    # makes that harder rather than easier.
    "rules": """\
table { border-collapse: collapse; font-size: var(--report-table-font-size); }
th, td { padding: var(--report-cell-pad); border: 0; }
thead th { border-bottom: 1.5px solid var(--report-text); font-weight: 600; text-align: left; }
thead tr:first-child th { border-top: 1.5px solid var(--report-text); }
tbody tr:last-child td { border-bottom: 1.5px solid var(--report-text); }""",
    "grid": """\
table { border-collapse: collapse; font-size: var(--report-table-font-size); }
th, td { padding: var(--report-cell-pad); border: 1px solid var(--report-border); }
thead th { background: color-mix(in srgb, var(--report-text) 5%, transparent); font-weight: 600; text-align: left; }""",
    "zebra": """\
table { border-collapse: collapse; font-size: var(--report-table-font-size); }
th, td { padding: var(--report-cell-pad); border: 0; }
thead th { border-bottom: 1px solid var(--report-border); font-weight: 600; text-align: left; }
tbody tr:nth-child(even) { background: color-mix(in srgb, var(--report-text) 4%, transparent); }""",
}

# Numbers are compared right to left, so they share a right edge; the first
# column is the row label and stays left. `tabular-nums` keeps the digits in
# their columns when the face has proportional figures (every serif does).
_NUMERIC = """\
tbody td:not(:first-child), thead th:not(:first-child) {
  text-align: right;
  font-variant-numeric: tabular-nums;
}"""

_FIGURE_ALIGN = {"left": "0", "center": "0 auto", "right": "0 0 0 auto"}

_FIGURE = """\
.siamang-figure {{
  margin: {align};
  width: var(--fig-w, var(--report-figure-width));
  max-width: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
}}
.siamang-figure img {{ width: 100%; height: auto; }}
.siamang-figure[data-align="left"] {{ margin-right: auto; margin-left: 0; }}
.siamang-figure[data-align="center"] {{ margin-left: auto; margin-right: auto; }}
.siamang-figure[data-align="right"] {{ margin-left: auto; margin-right: 0; }}
.siamang-figcaption, .siamang-stats {{
  margin: 0;
  color: var(--report-muted);
  font-size: 0.87em;
  line-height: 1.45;
}}
.siamang-number {{ color: var(--report-text); font-weight: 600; }}
/* Two half-width figures set side by side rather than stacked. */
.siamang-figure + .siamang-figure[data-align="left"] {{ margin-top: 0; }}"""

_CAPTION_ABOVE = ".siamang-figure { flex-direction: column-reverse; }"

_PRINT = """\
@media print {
  body { background: #fff; }
  .siamang-report { max-width: none; padding: 0; }
  table, figure, img, blockquote, pre { break-inside: avoid; }
  h1, h2, h3, h4 { break-after: avoid; }
  pre { overflow: visible; white-space: pre-wrap; word-break: break-word; }
  .siamang-break { break-before: page; }
  a { color: inherit; text-decoration: none; }
}"""


# ─── a document to look at ───────────────────────────────────────────────────


def sample_report(theme: ReportTheme | None = None) -> Any:
    """A short report using every block kind, for previewing a theme.

    Pure — it builds its table from literals rather than from data — so a host
    can render it for a theme picker without a run, a database or a sandbox.
    """

    import pandas as pd

    from siamang.reporting.document import Report

    report = Report(
        title="Satisfaction with the service",
        description="A sample report — every kind of block, so a theme can be judged.",
        theme=theme,
    )
    report.heading("Overall satisfaction")
    report.text(
        "Column percentages, weighted to the census margins for region and gender. "
        "The base after cleaning is reported under the table."
    )
    report.add(
        pd.DataFrame(
            {
                "Region": ["North", "South", "Capital"],
                "Low": [12.1, 9.8, 7.4],
                "Mid": [41.0, 44.2, 38.8],
                "High": [46.9, 46.0, 53.8],
            }
        ),
        caption="Satisfaction by region (%)",
    )
    report.note("Base: n = 1 204 respondents who answered both questions.")
    report.heading("Method")
    report.text(
        "Fieldwork ran online between 2 and 19 June. Speeders under 90 seconds and "
        "duplicate respondents were removed before weighting."
    )
    report.value("Fieldwork", "2–19 June")
    return report
