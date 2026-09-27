# Report Document

`Report` composes narrative prose, [[Reporting Tables|Reporting-Tables]], and
[[Reporting Charts|Reporting-Charts]] into a single document you can export to
Markdown or HTML. It is a thin orchestrator: tables already know how to render
themselves (`to_markdown()`), and charts already know how to save themselves
(`save()`) — `Report` stitches them together in order and links the generated
assets.

```python
from siamang.reporting import Report   # also: from siamang import Report
```

Every builder method returns `self`, so calls chain fluently; `save()` (or
`to_markdown`/`to_html`) is the terminal step.

---

## Constructor

```python
Report(title: str | None = None, description: str | None = None)
```

`title` becomes a top-level `# H1`; `description` is rendered in italics beneath
it. Both are optional.

---

## Narrative methods

Each appends a block and returns `self`.

| Method | Renders as |
| :--- | :--- |
| `heading(text, level=2)` | `## text` (level controls the `#` count). |
| `markdown(md)` | Raw Markdown, verbatim. |
| `text(md)` | Alias for `markdown`. |
| `note(md)` | `> **Note:** md` (a blockquote callout). |
| `value(label, value)` | `**label:** value` (an inline key figure). |
| `divider()` | `---` (horizontal rule). |

---

## Inserts

### `add`

```python
def add(self, component: object, *, caption: str | None = None) -> Report: ...
```

Inserts a `SurveyTable` (any [[Reporting Tables|Reporting-Tables]] type), a
`SurveyChart` (any [[Reporting Charts|Reporting-Charts]] type), or a raw
`pandas.DataFrame`. The optional `caption` is rendered in italics above tables
and as both the image alt-text and an italic caption beneath charts. Any other
type raises `TypeError`.

### `image`

```python
def image(self, path: str | Path, *, caption: str | None = None) -> Report: ...
```

Inserts an existing image file by path (useful for figures produced outside
siamang).

---

## Exporting

### `to_markdown`

```python
def to_markdown(
    self, asset_dir: str | Path = ".", *, embed_images: bool = False, prefix: str = ""
) -> str: ...
```

Renders the whole document to a Markdown string. Charts are materialized to PNG
files named `<prefix>fig_<index>.png`, where `<index>` is the chart block's
position in the whole document (narrative blocks count too) — so the numbers
are ordered but not consecutive:

- with `embed_images=False` (default), each chart is written into `asset_dir`
  and linked by relative filename;
- with `embed_images=True`, each chart is encoded inline as a `data:` URI (no
  files written).

### `to_html`

```python
def to_html(
    self,
    *,
    theme=None,
    standalone: bool = False,
    embed_images: bool = True,
    asset_dir=".",
    interactive: bool = False,
) -> str: ...
```

Renders to HTML. By default a fragment (the Markdown through the `markdown`
library with the `tables` extension, images embedded inline); with
`standalone=True` a whole document with the theme's stylesheet.

With `interactive=True` (a document only) each chart that has an interactive
form (`SurveyChart.vega_lite()`, see [[Reporting Charts|Reporting-Charts]]) is
drawn in the reader's browser: a tooltip on every bar, point and cell with its
value and base, a legend whose entries hide and show their series, zoom where it
helps. The document carries the libraries that draw them — Vega, Vega-Lite and
Vega-Embed, vendored with the engine, about 0.8 MB, written in once however many
charts there are and never loaded from anywhere — so it opens offline and can be
mailed as it is. Each chart's picture stays in it: shown to a reader without
scripts, printed, and shown if a chart cannot be drawn. The charts' menu saves a
chart as PNG or SVG (no editor, no source view).

### `save`

```python
def save(self, path: str | Path, *, theme=None, interactive: bool = False) -> Path: ...
```

Writes the document, choosing the format from the file suffix: `.md`/`.markdown`
(or no suffix) → Markdown with `asset_dir` set to the file's parent and its
figures named by the file: `report.md` writes `report_fig_3.png`, so two
reports saved in one folder keep their own figures (characters other than
letters, digits, `.`, `_` and `-` in the name become `-`: `Q3 results.md`
writes `Q3-results_fig_3.png`); `.html`/`.htm` → HTML, its figures embedded. A
`.pdf` suffix raises `NotImplementedError`; any other suffix raises
`ValueError`. Parent directories are created automatically.

`interactive=True` asks for the charts' interactive form: the HTML draws them in
the browser (see `to_html`); the Markdown is the same and each figure has its
Vega-Lite spec written beside it (`report_fig_3.png`, `report_fig_3.vl.json`).
Without it a report writes exactly what it always wrote.

Each chart is drawn once for a report and written as the same PNG to its
Markdown and its HTML; its figure is then closed and let go
(`SurveyChart.release`), so a report of many charts never holds their figures
all at once. A chart whose figure you asked for (`plot()`, `show()`) is left
open, as you may still be changing it.

A chart of `palette="theme"` is written in the chart colors of the report's
`ReportTheme` (`chart_palette`, `chart_diverging`, … — see
[[Reporting Charts|Reporting-Charts]]), in the Markdown's figures and the
HTML's alike: drawn again from its parameters when it was drawn in other
colors. Any other chart is written as it was drawn.

### `save_tables`

```python
def save_tables(self, path: str | Path) -> Path: ...
```

Writes every table of the report to one Excel workbook (`path` must end in
`.xlsx`): one sheet per table, exactly as the table's own `export_xlsx` writes
it — a Banner keeps its significance letters, Group means with a post-hoc test
gets a second sheet (`<name> – Post-hoc`) — and a bare DataFrame as the report
prints it, without its index. The statistics a table prints under itself are
written under it after an empty row, numbers as numbers — and the post-hoc
pairs' own (the method, which way a difference runs, that p is adjusted) under
the pairs. Text stays text: an open answer, a label or a caption that begins
with `=` is written as a string, never as a formula Excel would run. A sheet is named by the
table's caption, else by the heading of its section, else by the variable it
describes, else `Table <n>`; the name is cut to Excel's 31 characters, loses
`[ ] : * ? / \`, and is made unique (`Age`, `Age (2)`). The first sheet,
`Contents`, lists every sheet with its section and full caption (or the kind of
table: `Group means: Age`; `Perceptual map: Brand × Region — rows (Brand)` for
one of a map's three tables), each a link — to a sheet named `Brand's image`
as Excel names it in a reference, `'Brand''s image'!A1`, the apostrophe
doubled. Charts, text and statistics lines are left out; a report without
tables gets a Contents sheet that says so.

```python
report.save("out/report.md")
report.save_tables("out/report.xlsx")
```

---

## Fluent example: narrative + table + chart

The example assumes the simulated `data` from [[Analysis]] (n=200, seed=123).

```python
from siamang.reporting import Report

report = (
    Report(title="Remote Work & Autonomy", description="Pilot wave, Q2 2026")
    .heading("Overview")
    .text("Perceived autonomy was measured on a 5-point scale.")
    .value("Respondents", len(data.frame))
    .add(data.report.means("autonomy", by="remote_freq"), caption="Table 1. Mean autonomy by remote frequency")
    .add(data.plot.bar("autonomy", by="remote_freq"), caption="Figure 1. Mean autonomy by remote frequency")
    .note("Non-consenting respondents were excluded from the base.")
    .divider()
)

# Write autonomy_report.md plus autonomy_report_fig_*.png into ./out/
report.save("out/autonomy_report.md")
```

The Markdown begins:

```text
# Remote Work & Autonomy

*Pilot wave, Q2 2026*

## Overview

Perceived autonomy was measured on a 5-point scale.

**Respondents:** 200

*Table 1. Mean autonomy by remote frequency*

| Remote Frequency | Mean | SD | Median | N |
|---|---|---|---|---|
| Never | 3.222 | 1.38 | 4.0 | 45 |
...

> **Note:** Non-consenting respondents were excluded from the base.
```

---

## Combining reports: `Report.combine`

```python
@classmethod
def combine(cls, reports: list[Report], *, title: str, toc: bool = True) -> Report: ...
```

Merges several `Report` objects into one document. Each source report's `title`
becomes a `## H2` section heading (its `description` rendered in italics below),
and its blocks are appended in order. With `toc=True` (default), a **Contents**
list of anchor links to each section is inserted at the top. This is ideal for a
"run-all" report that concatenates per-analysis sections.

```python
cleaning = Report(title="Data Cleaning", description="prep").text("49 cases dropped.")
tables   = Report(title="Final Tables").add(data.report.freq("it_role"))

full = Report.combine([cleaning, tables], title="Full Report")
md = full.to_markdown()
# "# Full Report"
# "## Contents"  ->  "- [Data Cleaning](#data-cleaning)" / "- [Final Tables](#final-tables)"
# "## Data Cleaning" ... "## Final Tables" ...
```

Section anchors are slugified from the title (lowercased, non-alphanumerics → `-`),
so `"Data Cleaning"` links to `#data-cleaning`.

---

See also: [[Reporting Tables|Reporting-Tables]] · [[Reporting Charts|Reporting-Charts]] · [[Working with Data|Working-with-Data]] · [[Tutorial Full Pipeline|Tutorial-Full-Pipeline]]
