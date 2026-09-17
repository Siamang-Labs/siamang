"""Composable research report: narrative + tables + charts -> Markdown/HTML.

Builds on the rest of :mod:`siamang.reporting`: tables (FreqTable/CrossTable/...)
already expose ``to_markdown()``/``to_html()`` and charts (BarChart/...) expose
``save()`` — ``Report`` only orchestrates them into one document.

Every builder method returns ``self`` for fluent chaining; ``save()`` is the
terminal call.

Markdown and HTML carry different things on purpose. The Markdown is the
document's *content* — its text, its order, its captions, its notes, its
provenance footer — and stays plain text that diffs and travels. The HTML is the
document as it is meant to be *read*: a :class:`~siamang.reporting.theme.ReportTheme`
compiled into a stylesheet, tables rendered by the table components themselves
rather than flattened through Markdown, and figures in a ``<figure>`` that can be
sized. Both are written from the same blocks, so neither can drift from the other.
"""

from __future__ import annotations

import base64
import mimetypes
import re
import tempfile
from collections.abc import Mapping
from pathlib import Path

import pandas as pd

from siamang.reporting.charts import SurveyChart
from siamang.reporting.tables import SurveyTable, frame_to_html
from siamang.reporting.theme import _LENGTH, ReportTheme

# (kind, payload) blocks. payload depends on kind:
#   "md"    -> str
#   "table" -> (SurveyTable | pd.DataFrame, caption|None, placement)
#   "chart" -> (SurveyChart, caption|None, placement)
#   "image" -> (path: str, caption|None, placement)
# `placement` is {width?, align?, break_before?} and reaches the HTML only —
# see Report.add.
_Block = tuple[str, object]

_HTML_ESCAPES = {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}


def _esc(text: object) -> str:
    out = str(text)
    for char, entity in _HTML_ESCAPES.items():
        out = out.replace(char, entity)
    return out


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


_ALIGN = ("left", "center", "right")


def layout_problem(placement: object) -> str | None:
    """Why ``{width, align, break_before}`` cannot be used, or None.

    Lives here rather than in the flow package so that the rule a report obeys
    and the rule ``check_flow`` enforces are one rule: a width the document
    would reject must be a Check issue on the canvas, not a TypeError in a run.
    """

    if not isinstance(placement, dict):
        return "expected an object with width, align or break_before."
    for key in placement:
        if key not in ("width", "align", "break_before"):
            return f"unknown key {key!r} (width, align, break_before)."
    width = placement.get("width")
    if width is not None and not _LENGTH.match(str(width)):
        return f"width: {width!r} is not a CSS length (a number and a unit, e.g. '60%', '320px')."
    align = placement.get("align")
    if align is not None and align not in _ALIGN:
        return f"align: {align!r} is not one of {', '.join(_ALIGN)}."
    if not isinstance(placement.get("break_before", False), bool):
        return "break_before: expected true or false."
    return None


def _as_theme(theme: ReportTheme | Mapping[str, object] | None) -> ReportTheme | None:
    """A theme, a plain object holding one, or nothing.

    Generated flow scripts pass the chosen fields as a dict — it needs no import
    and every other parameter in such a script is data too — so every entry
    point that takes a theme takes both.
    """

    if theme is None or isinstance(theme, ReportTheme):
        return theme
    return ReportTheme.from_dict(dict(theme))


def _placement(width: str | None, align: str | None, break_before: bool) -> dict[str, object]:
    """Validate and pack a block's placement, dropping what was not asked for."""

    placement: dict[str, object] = {}
    if width is not None:
        placement["width"] = width
    if align is not None:
        placement["align"] = align
    if break_before:
        placement["break_before"] = True
    problem = layout_problem(placement)
    if problem:
        raise ValueError(problem)
    return placement


def _frame_markdown(frame: pd.DataFrame) -> str:
    return frame.to_markdown(index=False)


def _number(theme: ReportTheme, kind: str, n: int) -> str | None:
    """ "Table 1." / "Figure 2." when the theme numbers them, else nothing."""

    if kind == "table" and theme.number_tables:
        return f"{theme.table_label} {n}."
    if kind == "figure" and theme.number_figures:
        return f"{theme.figure_label} {n}."
    return None


def _figure(
    inner: str,
    caption: str | None,
    number: str | None,
    layout: Mapping[str, object],
    theme: ReportTheme,
) -> str:
    """A table or an image with its caption, in a sized <figure>.

    `width` and `align` come from the block (Report.add), falling back to the
    theme; the width is an inline custom property rather than an inline rule, so
    a stylesheet can still override it and nothing here writes CSS syntax the
    theme does not own.
    """

    align = str(layout.get("align") or theme.figure_align)
    width = layout.get("width")
    style = f' style="--fig-w:{_esc(width)}"' if width else ""
    classes = "siamang-figure" + (" siamang-break" if layout.get("break_before") else "")
    parts = [f'<figure class="{classes}" data-align="{_esc(align)}"{style}>', inner]
    if caption or number:
        label = f'<span class="siamang-number">{_esc(number)}</span> ' if number else ""
        parts.append(
            f'<figcaption class="siamang-figcaption">{label}{_esc(caption or "")}</figcaption>'
        )
    parts.append("</figure>")
    return "\n".join(parts)


def _data_uri(data: bytes, path: str) -> str:
    mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


class Report:
    def __init__(
        self,
        title: str | None = None,
        description: str | None = None,
        theme: ReportTheme | Mapping[str, object] | None = None,
    ) -> None:
        self.title = title
        self.description = description
        # The theme rides on the document, so whatever renders it later — a
        # save, a host asking for HTML, a combine — gets the intended look
        # without being told about it separately.
        self.theme = _as_theme(theme)
        self._blocks: list[_Block] = []

    # ── narrative (free text) ─────────────────────────────────────
    def heading(self, text: str, level: int = 2) -> Report:
        self._blocks.append(("md", f"{'#' * level} {text}"))
        return self

    def markdown(self, md: str) -> Report:
        self._blocks.append(("md", md))
        return self

    # alias
    def text(self, md: str) -> Report:
        return self.markdown(md)

    def note(self, md: str) -> Report:
        self._blocks.append(("md", f"> **Note:** {md}"))
        return self

    def value(self, label: str, value: object) -> Report:
        self._blocks.append(("md", f"**{label}:** {value}"))
        return self

    def divider(self) -> Report:
        self._blocks.append(("md", "---"))
        return self

    def provenance(self, text: str | None) -> Report:
        """A footer saying what the report was made from.

        ``text`` is Markdown (typically the ``PROVENANCE.md`` of a research
        bundle: questionnaire version, data snapshot, engine); it goes after a
        divider so a report mailed to a client still tells where it came from.
        Nothing is added when ``text`` is empty, so callers can pass an
        environment variable straight through.
        """
        if text and text.strip():
            self._blocks.append(("md", "---"))
            self._blocks.append(("md", "**Provenance**\n\n" + text.strip()))
        return self

    # ── inserts ───────────────────────────────────────────────────
    def add(
        self,
        component: object,
        *,
        caption: str | None = None,
        width: str | None = None,
        align: str | None = None,
        break_before: bool = False,
    ) -> Report:
        """Put a table, a chart or a statistic in the report.

        ``width`` (a CSS length: ``"60%"``, ``"320px"``) and ``align`` place it
        on the page; ``break_before`` starts it on a new one when printed. All
        three are checked here, when the report is built, so a typo fails where
        it was written rather than in the renderer. **They apply to the HTML
        only.** The Markdown is the report's content and does not carry layout:
        an attribute like ``{width=50%}`` is stripped by GitHub and by most
        pipelines, so it would vanish exactly where a `.md` is most likely to be
        read, and supporting it would mean a Markdown dialect with two parsers.
        """
        placement = _placement(width, align, break_before)
        if isinstance(component, SurveyTable):
            self._blocks.append(("table", (component, caption, placement)))
        elif isinstance(component, SurveyChart):
            self._blocks.append(("chart", (component, caption, placement)))
        elif isinstance(component, pd.DataFrame):
            self._blocks.append(("table", (component, caption, placement)))
        elif isinstance(component, Mapping):
            # A statistics dict (a table's .stats, an analysis result): one line.
            parts = [
                f"{key} = {value:.4f}" if isinstance(value, float) else f"{key} = {value}"
                for key, value in component.items()
            ]
            text = "; ".join(parts) if parts else "—"
            self._blocks.append(("md", f"*{caption}*: {text}" if caption else text))
        else:
            raise TypeError(
                "Report.add() accepts a SurveyTable, SurveyChart, pandas.DataFrame or a "
                f"statistics mapping; got {type(component).__name__}"
            )
        return self

    def image(
        self,
        path: str | Path,
        *,
        caption: str | None = None,
        width: str | None = None,
        align: str | None = None,
        break_before: bool = False,
    ) -> Report:
        self._blocks.append(("image", (str(path), caption, _placement(width, align, break_before))))
        return self

    # ── serialization ─────────────────────────────────────────────
    def to_markdown(self, asset_dir: str | Path = ".", *, embed_images: bool = False) -> str:
        asset_dir = Path(asset_dir)
        lines: list[str] = []
        if self.title:
            lines.append(f"# {self.title}")
        if self.description:
            lines.append(f"*{self.description}*")

        for i, (kind, payload) in enumerate(self._blocks):
            if kind == "md":
                assert isinstance(payload, str)
                lines.append(payload)
            elif kind == "table":
                assert isinstance(payload, tuple)
                comp, caption = payload[0], payload[1]
                if caption:
                    lines.append(f"*{caption}*")
                if isinstance(comp, SurveyTable):
                    lines.append(comp.to_markdown())
                else:
                    assert isinstance(comp, pd.DataFrame)
                    lines.append(_frame_markdown(comp))
            elif kind == "chart":
                assert isinstance(payload, tuple)
                comp, caption = payload[0], payload[1]
                assert isinstance(comp, SurveyChart)
                ref = self._chart_ref(comp, i, asset_dir, embed_images)
                lines.append(f"![{caption or ''}]({ref})")
                if caption:
                    lines.append(f"*{caption}*")
            elif kind == "image":
                assert isinstance(payload, tuple)
                path, caption = payload[0], payload[1]
                ref = self._image_ref(str(path), embed_images)
                lines.append(f"![{caption or ''}]({ref})")
                if caption:
                    lines.append(f"*{caption}*")

        return "\n\n".join(lines) + "\n"

    def _chart_ref(
        self,
        chart: SurveyChart,
        index: int,
        asset_dir: Path,
        embed: bool,
        theme: ReportTheme | None = None,
    ) -> str:
        # The figure is written at the theme's resolution when one is rendering
        # it; without a theme the chart's own `dpi` applies, as before.
        dpi = theme.figure_dpi if theme is not None else None
        if embed:
            with tempfile.TemporaryDirectory() as tmp:
                png = Path(tmp) / f"fig_{index}.png"
                chart.save(png, dpi=dpi)
                return _data_uri(png.read_bytes(), str(png))
        asset_dir.mkdir(parents=True, exist_ok=True)
        png = asset_dir / f"fig_{index}.png"
        chart.save(png, dpi=dpi)
        return png.name

    def _image_ref(self, path: str, embed: bool) -> str:
        p = Path(path)
        if embed and p.exists():
            return _data_uri(p.read_bytes(), path)
        return path

    def to_html(
        self,
        *,
        theme: ReportTheme | Mapping[str, object] | None = None,
        standalone: bool = False,
        embed_images: bool = True,
        asset_dir: str | Path = ".",
    ) -> str:
        """The report as HTML.

        ``standalone`` is the difference between a fragment and a document. A
        fragment is the Markdown put through ``markdown`` and nothing else —
        what this method has always returned, kept byte for byte so a caller
        that splices it into a page of its own is unaffected. A document has a
        ``<head>``, the theme's stylesheet, its tables rendered by the table
        components (which know which columns are numbers) and its figures in a
        ``<figure>`` with their caption, so it can be opened, printed and mailed
        as it is.
        """

        import markdown as md_lib

        if not standalone:
            md = self.to_markdown(asset_dir=asset_dir, embed_images=embed_images)
            return md_lib.markdown(md, extensions=["tables"])

        # Nothing named one, so whatever runs this may have: SIAMANG_REPORT_THEME
        # is how a platform and a research bundle hand a flow the project's
        # house style without editing the flow (as SIAMANG_PROVENANCE does for
        # the footer). Unset, that is the defaults.
        theme = _as_theme(theme) or self.theme or ReportTheme.from_env()
        body = "\n".join(self._html_blocks(theme, Path(asset_dir), embed_images))
        title = _esc(self.title or "Report")
        return (
            "<!doctype html>\n"
            '<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f'<meta name="siamang-report-theme" content="{_esc(theme.font_preset)}">\n'
            f"<title>{title}</title>\n"
            f"<style>\n{theme.stylesheet()}</style>\n</head>\n"
            f'<body>\n<main class="siamang-report">\n{body}\n</main>\n</body>\n</html>\n'
        )

    def _html_blocks(self, theme: ReportTheme, asset_dir: Path, embed: bool) -> list[str]:
        import markdown as md_lib

        def md(text: str) -> str:
            # `attr_list` lets a report's own Markdown carry an id or a class;
            # `toc` gives headings the ids `Report.combine`'s contents links
            # point at, which they have never resolved to before.
            return md_lib.markdown(text, extensions=["tables", "attr_list", "toc"])

        out: list[str] = []
        if self.title:
            out.append(f"<h1>{_esc(self.title)}</h1>")
        if self.description:
            out.append(f'<p class="siamang-figcaption">{_esc(self.description)}</p>')

        tables = figures = 0
        for i, (kind, payload) in enumerate(self._blocks):
            if kind == "md":
                assert isinstance(payload, str)
                out.append(md(payload))
                continue
            assert isinstance(payload, tuple)
            component, caption = payload[0], payload[1]
            layout = payload[2] if len(payload) > 2 else {}
            if kind == "table":
                tables += 1
                label = _number(theme, "table", tables)
                # Both paths go through the table layer, so every table in the
                # document carries `siamang-table` and none of them arrives with
                # the inline `text-align` python-markdown writes into a pipe
                # table — which would override the theme's own alignment.
                inner = (
                    component.to_html()
                    if isinstance(component, SurveyTable)
                    else frame_to_html(component)
                )
                out.append(_figure(inner, caption, label, layout, theme))
            elif kind == "chart":
                figures += 1
                ref = self._chart_ref(component, i, asset_dir, embed, theme)
                alt = _esc(caption or "")
                out.append(
                    _figure(
                        f'<img src="{ref}" alt="{alt}">',
                        caption,
                        _number(theme, "figure", figures),
                        layout,
                        theme,
                    )
                )
            elif kind == "image":
                figures += 1
                ref = self._image_ref(str(component), embed)
                alt = _esc(caption or "")
                out.append(
                    _figure(
                        f'<img src="{ref}" alt="{alt}">',
                        caption,
                        _number(theme, "figure", figures),
                        layout,
                        theme,
                    )
                )
        return out

    def save(
        self, path: str | Path, *, theme: ReportTheme | Mapping[str, object] | None = None
    ) -> Path:
        path = Path(path)
        suffix = path.suffix.lower()
        path.parent.mkdir(parents=True, exist_ok=True)
        if suffix in (".md", ".markdown", ""):
            path.write_text(self.to_markdown(asset_dir=path.parent), encoding="utf-8")
        elif suffix in (".html", ".htm"):
            # Written as a document, not a fragment: a saved `.html` is opened
            # by a person, so it carries its own stylesheet and its own images.
            path.write_text(
                self.to_html(theme=theme, standalone=True, embed_images=True), encoding="utf-8"
            )
        elif suffix == ".pdf":
            raise NotImplementedError(
                "Reports are written as Markdown and HTML; there is no PDF renderer here. "
                "Save the HTML and convert it — `pandoc report.html -o report.pdf`, or print "
                "it from a browser, both of which honor the theme's @page rule."
            )
        else:
            raise ValueError(f"unsupported report format: {suffix!r}")
        return path

    # ── combine (Run all) ─────────────────────────────────────────
    @classmethod
    def combine(
        cls,
        reports: list[Report],
        *,
        title: str,
        toc: bool = True,
        theme: ReportTheme | Mapping[str, object] | None = None,
    ) -> Report:
        """Merge several reports into one document with an optional table of contents."""
        merged = cls(
            title=title,
            theme=_as_theme(theme) or next((r.theme for r in reports if r.theme), None),
        )
        sections = [r for r in reports if r.title or r._blocks]

        if toc:
            toc_lines = ["## Contents"]
            for r in sections:
                name = r.title or "Section"
                toc_lines.append(f"- [{name}](#{_slugify(name)})")
            merged._blocks.append(("md", "\n".join(toc_lines)))

        for r in sections:
            if r.title:
                merged._blocks.append(("md", f"## {r.title}"))
            if r.description:
                merged._blocks.append(("md", f"*{r.description}*"))
            merged._blocks.extend(r._blocks)
        return merged
