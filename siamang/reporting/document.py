"""Composable research report: narrative + tables + charts -> Markdown/HTML.

Builds on the rest of :mod:`siamang.reporting`: tables (FreqTable/CrossTable/...)
already expose ``to_markdown()``/``to_html()`` and charts (BarChart/...) expose
``save()`` — ``Report`` only orchestrates them into one document.

Every builder method returns ``self`` for fluent chaining; ``save()`` is the
terminal call.
"""

from __future__ import annotations

import base64
import mimetypes
import re
import tempfile
from pathlib import Path

import pandas as pd

from siamang.reporting.charts import SurveyChart
from siamang.reporting.tables import SurveyTable

# (kind, payload) blocks. payload depends on kind:
#   "md"    -> str
#   "table" -> (SurveyTable | pd.DataFrame, caption|None)
#   "chart" -> (SurveyChart, caption|None)
#   "image" -> (path: str, caption|None)
_Block = tuple[str, object]


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _data_uri(data: bytes, path: str) -> str:
    mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


class Report:
    def __init__(self, title: str | None = None, description: str | None = None) -> None:
        self.title = title
        self.description = description
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

    # ── inserts ───────────────────────────────────────────────────
    def add(self, component: object, *, caption: str | None = None) -> Report:
        if isinstance(component, SurveyTable):
            self._blocks.append(("table", (component, caption)))
        elif isinstance(component, SurveyChart):
            self._blocks.append(("chart", (component, caption)))
        elif isinstance(component, pd.DataFrame):
            self._blocks.append(("table", (component, caption)))
        else:
            raise TypeError(
                "Report.add() accepts a SurveyTable, SurveyChart, or pandas.DataFrame; "
                f"got {type(component).__name__}"
            )
        return self

    def image(self, path: str | Path, *, caption: str | None = None) -> Report:
        self._blocks.append(("image", (str(path), caption)))
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
                comp, caption = payload
                if caption:
                    lines.append(f"*{caption}*")
                if isinstance(comp, SurveyTable):
                    lines.append(comp.to_markdown())
                else:
                    assert isinstance(comp, pd.DataFrame)
                    lines.append(comp.to_markdown(index=False))
            elif kind == "chart":
                assert isinstance(payload, tuple)
                comp, caption = payload
                assert isinstance(comp, SurveyChart)
                ref = self._chart_ref(comp, i, asset_dir, embed_images)
                lines.append(f"![{caption or ''}]({ref})")
                if caption:
                    lines.append(f"*{caption}*")
            elif kind == "image":
                assert isinstance(payload, tuple)
                path, caption = payload
                ref = self._image_ref(str(path), embed_images)
                lines.append(f"![{caption or ''}]({ref})")
                if caption:
                    lines.append(f"*{caption}*")

        return "\n\n".join(lines) + "\n"

    def _chart_ref(self, chart: SurveyChart, index: int, asset_dir: Path, embed: bool) -> str:
        if embed:
            with tempfile.TemporaryDirectory() as tmp:
                png = Path(tmp) / f"fig_{index}.png"
                chart.save(png)
                return _data_uri(png.read_bytes(), str(png))
        asset_dir.mkdir(parents=True, exist_ok=True)
        png = asset_dir / f"fig_{index}.png"
        chart.save(png)
        return png.name

    def _image_ref(self, path: str, embed: bool) -> str:
        p = Path(path)
        if embed and p.exists():
            return _data_uri(p.read_bytes(), path)
        return path

    def to_html(self) -> str:
        import markdown as md_lib

        md = self.to_markdown(embed_images=True)
        return md_lib.markdown(md, extensions=["tables"])

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        suffix = path.suffix.lower()
        path.parent.mkdir(parents=True, exist_ok=True)
        if suffix in (".md", ".markdown", ""):
            path.write_text(self.to_markdown(asset_dir=path.parent), encoding="utf-8")
        elif suffix in (".html", ".htm"):
            path.write_text(self.to_html(), encoding="utf-8")
        elif suffix == ".pdf":
            raise NotImplementedError("PDF rendering is added in the Stage 4 worker (HTML->PDF).")
        else:
            raise ValueError(f"unsupported report format: {suffix!r}")
        return path

    # ── combine (Run all) ─────────────────────────────────────────
    @classmethod
    def combine(cls, reports: list[Report], *, title: str, toc: bool = True) -> Report:
        """Merge several reports into one document with an optional table of contents."""
        merged = cls(title=title)
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
