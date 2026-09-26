# Reports

A report is a document produced by a flow: headings, text you wrote, tables
and charts with captions, and notes. This page covers how a report is built
from nodes, writing it in the flow's **Report** view, styling it in the
**Look** tab and with the project's house style, the **Reports** screen, PDF
and Word copies, the provenance footer and the combined report of **Run all**.

---

## How a report is made

Two node types ([[Node Reference|Studio-Node-Reference]]):

- **Report section** — the tables, charts and statistics that belong
  together, with a heading, introductory Markdown, a caption per item and a
  closing note. Without a heading it is a plain block of text between two
  sections.
- **Save report** — the sections, in the order you connect them, combined
  into one document with a title and saved to a **Path** (default
  `outputs/report.md`), optionally with a table of contents.

**Run** the flow, and the document appears on the **Reports** screen and in
**Files**.

Two files come out of one report, and they divide the work:

- the **`.md`** carries the **content** — the same words and numbers, no
  styling, so it diffs cleanly and reads in any repository; each chart is a
  `fig_N.png` file beside it;
- the **`.html`** (on by default: **Also save HTML**) carries the **look** —
  the report's stylesheet, page size, typefaces and every chart embedded in
  the one file. Widths, alignment and page breaks exist only here. Its tables
  print the same numbers as the `.md`: a statistics table as it rounds them,
  and a table such as a **Regression**'s coefficients, a **Principal
  components** loading or a **Cluster** centroid with six significant digits
  (`62.263`, `6.15462e-38`).

Three rules make sure a report arrives:

1. The **Path** must start with `outputs/`. Only files written under
   `outputs/` are kept after a run; a report saved elsewhere is lost.
2. Set the same file as the flow's **Report path** (Flow settings, click the
   empty canvas) if you want it in the [combined report](#the-combined-report)
   of **Run all**. The Report view does this for you, and changing the
   **Save report** node's **Path** afterwards moves the **Report path** with
   it. A **Report path** that names a file the flow does not write makes the
   flow fail in **Run all**; **Check** and the Save warn about it first.
3. There is no PDF writer: a **Path** ending in `.pdf` fails. Print or convert
   the HTML instead ([below](#pdf-and-word)).

A run keeps at most 50 files (and 200 MB) under `outputs/`. When a flow
writes more — a report with dozens of charts — the report's `.md` and `.html`
are kept before the figures, so the report still arrives; the charts past the
cap are missing next to the `.md`, while the `.html` carries its charts
inside. See [What a run keeps](Studio-Flows#running-a-flow).

A report produced by a run on the platform ends with a
[provenance footer](#the-provenance-footer) unless you turn it off in
**Settings → Reports**.

---

## Writing the report in the Report view

The **Canvas | List | Report** switch in the flow editor shows the report as
a document over the same nodes. Everything you change here is a change to the
flow — visible on the canvas at once, saved with **Save changes**.

```
┌ Report title ───────────────────────────── outputs/satisfaction.md  [ ] Contents  [x] Also HTML ┐
│ 1  Section heading (optional)                             2 outputs   ok   v  ⋮           │
│    Introductory text (Markdown) — what the reader should take from this section            │
│    Outputs                                                                                  │
│    :: [Table]  Banner table  [Table caption………………]   [Full v]  ⋮                          │
│    :: [Chart]  Bar chart     [Figure caption……………]   [½ v]     ⋮                          │
│    [+ Add output ▾]                                                                         │
│    Section note: Caveats, base sizes, weighting                                             │
│ [+ Add section]                                                                             │
└──────────────────────────────────────────────────── │ [Preview | Look]   ▶ Preview report ──┘
```

### The title row

When the flow has a **Save report** node: **Report title**, the file path,
**Contents** (a table of contents), **Also HTML**, and an icon that shows the
**Save report** node on the canvas. Without one: "This flow saves no report
yet. Add a section: it creates the **Save report** node and wires the section
into it."

### Sections

**+ Add section** ("A heading, a paragraph of Markdown, and any tables or
charts you add to it — all three optional") adds a **Report section** node
wired into **Save report**. The first one also creates **Save report** — title
= the flow's title, **Path** `outputs/<flow>.md`, **Also save HTML** on, the
project's house style (when it has one) as its look — and sets the flow's
**Report path** to the same file. Renaming or duplicating the flow moves that
default path to the new name (`outputs/<new>.md`); a path you chose stays.

Each section card:

| Part | What it is |
|---|---|
| number | its place in the report |
| **Section heading (optional)** | the heading; leave empty for a block of plain text |
| count | "3 outputs" while the section is folded |
| state | the last preview's state (ok, error, stale, running…) |
| chevron | fold / unfold the section (**Collapse** / **Expand**) |
| **⋮** | the node id, **Move section up**, **Move section down**, **Show on the canvas**, **Delete section** |
| text box | "Introductory text (Markdown) — what the reader should take from this section" |
| **Outputs** | the section's tables, charts and statistics, one per row ("No tables or charts yet." when empty) |
| **+ Add output** | a dropdown of every table, chart and statistic in the flow not yet in this section, as `node · Title (Type)`; a node with several tables names each by its output — `fa · Factor analysis · variance (Table)`, `fri · Paired tests · pairs (Table)`. "Every table and chart of the flow is already in this section." when there are none left |
| **Section note** | "Caveats, base sizes, weighting" |

Sections that exist on the canvas but are not wired into **Save report** are
listed under **Not in the report** ("sections on the canvas that no Save
report node collects"), each with **Add to report**. The Report view works
with the first **Save report** node of a flow.

### Output rows

Each output is one row:

| Part | What it is |
|---|---|
| grip (left) | drag to reorder ("Drag to reorder") |
| type | **Table**, **Chart** or **Stat** |
| name | the node's kind (**Banner table**); the node id is added when two rows are the same kind, and the output's name (`variance`, `pairs`) when the node has several tables — both (`pca_2.loadings`) when two rows are the same kind and the same output |
| caption | "Table caption", "Figure caption", or for a statistic "Label before the values" |
| size | the width it is set to — see [Size and placement](#size-and-placement); a statistic shows "one line" instead |
| **⋮** | the node id (with the output, `fa.variance`, for a node with several tables, and whenever two rows of the section would otherwise read the same — a Crosstab's table and its statistic are `xtab.table` and `xtab.stat`; the row's caption, size and **⋮** controls are named the same way for screen readers), **Move up**, **Move down**, **Show on the canvas**, **Remove from section** |

A node's tables are separate rows: a factor analysis's loadings, variance
and factor correlations, a paired test's main table and its pairs. **Remove
from section** takes out that one and leaves the others. Each output has its
own caption and size: they are stored under `fa.variance` rather than `fa`
once a section holds more than one output of the node, and adding the second
output — here or by wiring it into the section on the canvas — moves the first
one's caption and size to its own key, so the new one starts empty. Taking one
of two out (here or by deleting its wire) moves the other's back under the
node's key; clearing a caption or a size leaves that output without one, even
where the node still has one; and deleting a node takes its captions and
sizes with it, so a node added later under the same id starts without them.
A section saved before, with one caption for the node, shows it on each of
the node's outputs until you give one its own — as the report prints it. The post-hoc pairs of a **Group means** are
not a separate output: they print under its means table.

After a preview, each row also shows a small preview of that output. A
statistic (**Stat**) is printed in the report as one line, `Caption: key =
value; …` — the caption is the label before the values. It has no size or
placement: its row reads "one line", with the tooltip "A statistic is one
line of the report: size and placement apply to tables and charts only".

### Size and placement

The size control on a row reads the width it is set to — **Full**, **¾**,
**⅔**, **½**, **⅓** — and opens the rest below the row:

| Control | Choices |
|---|---|
| width | **Full width**, **Three quarters**, **Two thirds**, **Half — two fit side by side**, **A third** |
| alignment | **left**, **center**, **right** — shown only when the item is narrower than the page; default center |
| **New page** | "Start this item on a new page when the report is printed" |

Two outputs at **Half** sit side by side; that is the whole layout model, and
it is enough for almost every report. A row that has been sized says so while
folded. The same control is in the **Report section** node's inspector, under
**Size and placement** (where a statistic, again, reads "one line"). Size
and placement reach the `.html` only.

### Preview report

The right pane has two tabs, **Preview** and **Look**. **▶ Preview report**
("Run the draft up to the Save report node in the sandbox") builds the report
from your unsaved draft on the current data and shows the engine's own HTML
document — the same renderer and look a run uses. **Rendered | Markdown**
switches to the Markdown source.

- The preview has **no provenance footer**; runs add it (while the setting in
  **Settings → Reports** is on).
- The preview renders in the look of the flow's **Save report** node, as a
  run does — the engine's defaults when the node has none.
- The Markdown view shows the first 4,000 characters; the rendered view shows
  the whole document.
- Changing anything upstream marks it "changed since — run again".
- Before the first preview: "No preview yet. Preview report runs the draft up
  to the Save report node and renders the document the engine builds — the
  same file Run saves under Files and Reports."

Previews count toward your plan's preview limits; see
[Run to here](Studio-Flows#run-to-here-and-preview-all).

That is the practical way to write: build the analysis on the canvas, then
switch to **Report** and write the words around the outputs.

---

## The Look tab

**Look** sets the look of the whole report. It is a parameter of the **Save
report** node, so — as the tab says — "it is in this flow, in
`scripts/<flow>.py` and in the research bundle. Whoever re-runs the study on
their own laptop gets this document, not a default one. **Preview report**
shows it." Everything here reaches the `.html` only. A **Save report** node
whose look is empty renders with the engine's defaults — in Studio as in the
downloaded script.

The four main choices:

| Control | Choices | Default |
|---|---|---|
| **Typeface** | **academic** (Source Serif 4, the questionnaire's own preset), **humanist** (Nunito), **modern** (Inter) | academic |
| **Density** | **compact** (14 px text, tight), **comfortable** (15.5 px), **spacious** (16.5 px) — type size, leading and the air between blocks | comfortable |
| **Tables** | **rules** (horizontal lines, the journal default), **grid**, **zebra** | rules |
| **Page** | **screen** (no page box, a measure of 720 px), **a4** (A4 with 22 mm margins), **letter** (Letter with 0.9 in margins) — "a4 and letter add page size and margins for printing" | screen |

Typefaces are named font stacks, never a downloaded web font: a report is
read offline and printed, and a stylesheet that fetches a font renders
differently depending on whether the reader had a network. Where a face is
not installed, the next one in the stack is used.

Under the disclosures (open ones stay open in this browser):

| Section | Controls |
|---|---|
| **Measurements and typefaces** | **Measure** (default `720px`, "ignored on paper"), **Font size**, **Line height** (a plain number such as `1.6`), **Table font size** (default `0.87em`), **Body typeface** ("a CSS font stack; overrides the preset"), **Heading typeface**, **Monospace typeface** |
| **Tables and figures** | **Table width** (**auto** / **full**), **Numbers right, on tabular figures** (on), **Default figure width** (`100%`), **Figure resolution** ("dpi — raise it for print"; 72–600, default 150), **Figure alignment** (**left** / **center** / **right**), **Caption** (**below** / **above**) |
| **Numbering** | **Number the tables**, **Number the figures** (both off) — "Table 1.", "Figure 2." before the caption; **Word for a table** / **Word for a figure** ("for a report in another language", defaults `Table`, `Figure`) |
| **Colors** | **Text** (`#1a1a1a`), **Muted text** (`#5a5a5a`), **Rules and borders** (`#d9d9de`), **Links** (`#2c5f8a`), **Background** (`#ffffff`), each a color picker plus a text box |
| **Custom CSS** | "Appended after the generated stylesheet, so it wins. Unlike everything above it is not checked by anything — a bad rule reaches the reader. It travels with the flow, so whoever runs the bundle gets it too." (placeholder `.siamang-report h2 { text-transform: uppercase }`) |

Lengths are a number and a unit (`720px`, `60%`, `2cm`); anything else is
reported by **Check** and on the node, e.g. "width: 'wide' is not a CSS length
(a number and a unit, e.g. '720px', '60%')." The one rule custom CSS must obey:
it cannot contain `</` ("custom_css: '</' would close the stylesheet").
An empty field means "whatever the preset says" and is not stored.

At the bottom: **Use the house style** (only when the project has one —
"Copy the house style from Settings → Reports over this flow's look") and
**Reset** ("Drop every choice and render with the engine's defaults"). Without
a **Save report** node the tab says "Add a section first — it creates the Save
report node the look belongs to."

---

## The project's house style

**Settings → Reports** holds the project's report settings, part of
`studio/settings.json` and versioned with every Save:

- **End every report with the provenance footer** ("— the Save, the engine
  version and the data snapshot it was built from"), on by default. It
  decides whether reports end with the
  [provenance footer](#the-provenance-footer): with it off, reports from
  platform runs — single runs, **Run all**, schedules, Live — and from a
  research bundle's `run.sh` have no footer.
- **Combined report** — where **Run all** writes the combined report
  (placeholder `reports/report.md`, "where Run all writes the merged report;
  Markdown, inside the project"). A path outside the project or not ending in
  `.md` is refused: "A combined report must be a Markdown path inside the
  project, like reports/report.md." The **combined** badge on the Reports
  screen follows this path.
- **House style** — the same form as the **Look** tab.

The house style is a **stamp**, never a setting a run reads: a flow's report
always renders in the look of its own **Save report** node — the same look
its downloaded script and a research bundle use. It is used in three ways:

1. It is **stamped** into a new **Save report** node — when the Report view
   creates one, and when you add one from the palette. From then on the node
   carries its own copy; changing the house style later does not change it.
2. It renders the **combined report** of **Run all**, which has no node of its
   own.
3. **Apply to every flow** ("Write this style into the Save report node of
   every flow, so each flow — and each bundle — carries it") copies it into
   every **Save report** node (or clears their looks when the house style is
   empty). If nothing changes: "Every flow already uses the house style".

A **Save report** node with no look of its own renders with the engine's
defaults, on the platform as in its script. Earlier, such a node silently
took the house style when Studio ran it, but not when its downloaded script
ran; a flow saved that way now renders plain everywhere until you stamp the
style in — **Apply to every flow**, or **Use the house style** in its
**Look** tab.

**Save report settings** and **Apply to every flow** each create a new Save
at once ("Update report settings", "Apply the report house style to 3 flows")
— an ordinary edit you can see in the diff and undo by restoring the Save.

---

## The Reports screen

```
┌ Reports ─────────────────────┐┌ outputs/tables/tables.md   [Markdown] [HTML] [Print / PDF] ┐
│ Tables                        ││                                                                 │
│ tables · tables.md · 23/09    ││   Digital Life – key tables                                     │
│ Report  combined              ││   …                                                             │
│ report.md · 23/09             ││                                                                 │
└──────────────────────────────┘└─────────────────────────────────────────────────────────────────┘
```

- **The left rail** lists every report the project's runs have produced: every
  `.md` (or `.html`) under `outputs/` and `reports/`, and the combined report
  wherever **Settings → Reports** puts it. The title comes from the file name
  ("satisfaction_by_region.md" → "Satisfaction by region", `report.md` →
  "Report"); the line under it reads "`flow · file · date`" (without the flow
  for a file outside `outputs/`). When two reports share a file name — a
  combined report moved to `deliverables/report.md` next to an older
  `reports/report.md`, say — the line shows each one's path instead of the
  file name, and clicking either opens its own file. The combined report —
  at the path **Settings → Reports** names, `reports/report.md` by default —
  carries a **combined** badge.
- **The document** renders in the middle: the HTML twin when there is one
  (exactly as the flow styled it), otherwise the Markdown with a plain
  stylesheet. It is shown as a document only — scripts in a report never run.
- **The bar** offers **Markdown**, **HTML** (only when the report has an HTML
  twin) and **Print / PDF**.

**Markdown** ("The .md — with its figures in a .zip when it has any, since it
refers to them by file name") downloads a report with charts as
`<name>.zip`: a folder `<name>/` holding the `.md` and the figures it names,
so the images show wherever you unpack it. A report without figures
downloads as the plain `.md`. The toast names the file ("Downloaded
tables.zip"); a failure reads "Could not download tables.md. *reason*".
**HTML** downloads the one self-contained `.html`.

Each run of a flow replaces its report on this screen — so does a **Run all**
in which the flow succeeded; earlier versions stay downloadable from their
run cards in the flow's **Run history**. A renamed flow's earlier reports keep
the old name (`outputs/<old>/…`).

With no reports: "No reports yet — Run a flow with a Report node (or Run all)
and its report shows up here." with **Open Flows**. If a stored file cannot be
read: "The stored file could not be read — download it instead." with a
download button.

> **Tip.** To share a report, send the **HTML**: one file, charts inside. The
> **Markdown** zip is for a repository or an editor. Reports have no share
> link of their own; for a live, read-only link use Live tiles
> ([[Live Monitoring|Studio-Live-Monitoring]]).

### PDF and Word

**Print / PDF** ("Open the print dialog — choose “Save as PDF” for a PDF
copy") opens your browser's print dialog on the report's own HTML, page box
and all. If you set **Page** to `a4` or `letter`, choose the same paper size
in the dialog and set its margins to none — the document already carries
them. A report without an HTML twin prints with Studio's own print margins
(18 mm top and bottom, 16 mm at the sides).

**For Word**, convert the HTML with [pandoc](https://pandoc.org):

```bash
pandoc report.html -o report.docx
```

The same command is in every research bundle's README. Studio does not render
Word or PDF on the server: a converter you run yourself is one you can pin,
and the HTML is the honest input to it.

---

## The provenance footer

While **Settings → Reports → End every report with the provenance footer**
is on (the default), every report produced by a run on the platform ends with
a rule and a **Provenance** table:

| Row | Content |
|---|---|
| **Project** | `organization/project` |
| **Questionnaire** | `Save #17 — <message> (2026-06-04 14:32 UTC, sha256 a3f2…)`, and the environments |
| **Data** | `project database at <time of the run, UTC>` |
| **Flow** | one row per flow in the Save: `flows/<name>.flow.json @ Save #17 (sha256 …)` |
| **Engine** | `siamang <version>` |
| **Generated by** | `Siamang Studio` |

When you email a PDF to a client, the document itself says which version of
the questionnaire produced those numbers and when the data was read. A report
produced from a research bundle carries the bundle's `PROVENANCE.md` instead,
which adds the data files' row counts and hashes (see
[[Reproducibility|Studio-Reproducibility]]). Previews have no footer.

Untick the box, and the next runs — on the platform and from a research
bundle made from that Save — write their reports without the footer. Reports
already written keep theirs.

---

## The combined report

**Run all** (Flows → **More ▾ → Run all flows**) runs every flow and then
writes one combined document, "Combined report":

- a **Contents** list, then one section per flow, in the order the flows ran
  — a flow after the flows whose tables it reads, alphabetical where that
  leaves a choice (see [Run all](Studio-Flows#run-all)) — titled with the
  flow's title and containing that flow's report;
- only flows whose **Report path** (Flow settings) names their report are
  included;
- written to `reports/report.md` (or the path in **Settings → Reports**) with
  an `.html` twin in the house style; charts are copied beside it as
  `<flow>__fig_N.png` (an `_` in the flow name becomes `-`), taken from each
  flow as soon as it finishes, so two flows' `fig_1.png` never mix.

Because it is assembled from each flow's Markdown, the combined HTML has the
house style's typefaces, measure and page box but plainer tables than a single
flow's own HTML.

**When a flow fails**, **Run all** still runs the flows that do not depend on
it and ends as failed — and still writes the combined report from the flows
that succeeded, titled **Combined report (incomplete)**. Its first section,
**Missing from this report**, reads: "This Run all did not finish every flow,
so this report has only the sections of the flows that did. Not in it:",
then one line per flow — "**tables** — failed: *reason*" or "**charts** —
skipped: needs tables, which failed" — and "Fix them and run all flows again
for the complete report." It replaces the previous combined report on this
screen. Only when none of the flows that succeeded has a report is no
combined report written, and the last one stays.

A flow whose **Report path** names a file it did not write counts as failed
("report outputs/tables.md was not written: the flow's Report path names a
file none of its nodes saves — set it to the Path of its Save report node");
the other flows, including those that read its tables, go on. Keep **Report
path** equal to the **Save report** node's **Path** — the Report view sets
both, changing the node's **Path** (or clearing it back to
`outputs/report.md`) moves the **Report path** along, and deleting that node
clears the **Report path** it set; a **Report path** you pointed elsewhere
yourself stays. A **Report path** that no **Save report** node writes is
caught before **Run all**: **Check** and the Save warn "The flow's Report path
is “outputs/tables.md”, but no Save report step saves there: Run all will fail
this flow. Set it to the Path of a Save report step, or clear it."

**Run all** also stores each successful flow's own report (its `.md`, `.html`
and figures) under `outputs/<flow>/`, where a single run of the flow puts
it, so this screen shows the flows' reports from that Run all too. See
[Run all](Studio-Flows#run-all).

---

## Tips

- **Write captions.** A caption per table is what turns a run output into a
  readable document, and it costs one line.
- **Put the base in the note**: "Base: all respondents, weighted by region and
  gender (n = 1,247)". Say which tables are weighted — see
  [Apply weight](Studio-Node-Reference#apply-weight).
- **One flow per deliverable** keeps reports focused; use **Run all** for the
  combined document.
- **Re-run before sending.** A report is a snapshot of the data at run time;
  the time is in the footer.
- **Set the page before you print**, not after. `a4` with numbering on is the
  closest thing here to a journal submission.
- **Reach for custom CSS last.** Everything above it is checked and travels
  with the bundle; a CSS rule is checked by nobody.

## See also

- [[Analysis Flows|Studio-Flows]]
- [[Node Reference|Studio-Node-Reference]]
- [[Project Settings|Studio-Project-Settings]]
- [[Reproducibility: Code, Bundles and Citation|Studio-Reproducibility]]
- [[Live Monitoring|Studio-Live-Monitoring]]

<!-- studio-nav -->
---

← [[Coding Open Answers|Studio-Open-Answer-Coding]] · [Studio contents](Studio-Overview#all-pages) · [[History and Versions|Studio-History-and-Versions]] →
