# Reports

A report is a document produced by a flow: headings, text you wrote, tables
and charts with captions, and notes. This page covers how a report is built
from nodes, putting a result's chart beside its table, writing it in the
flow's **Report** view, styling it — its charts' colors too — in the **Look**
tab and with the project's house style, charts the reader can hover and
toggle in the HTML, the **Reports** screen, the report's tables in Excel and
the tab books beside the reports, PDF and Word copies, the provenance footer
and the combined report of **Run all**.

---

## How a report is made

Two node types ([[Node Reference|Studio-Node-Reference]]):

- **Report section** — the tables, charts and statistics that belong
  together, with a heading, introductory Markdown, a caption per item and a
  closing note. Without a heading it is a plain block of text between two
  sections.
- **Save report** — the sections, in the order you connect them, combined
  into one document with a title and saved under its **File name** in
  `outputs/` — `outputs/<flow>.md` when the Report view or the palette adds
  the node — optionally with a table of contents, with
  [interactive charts](#interactive-charts) in its HTML and with its tables
  in Excel.

**Run** the flow, and the document appears on the **Reports** screen and in
**Files**.

Two files come out of one report, and they divide the work (a third, the
[Excel workbook](#tables-in-excel) of its tables, when you ask for it):

- the **`.md`** carries the **content** — the same words and numbers, no
  styling, so it diffs cleanly and reads in any repository; each chart is a
  PNG file beside it, named by the report (`satisfaction_fig_1.png`,
  `satisfaction_fig_2.png` for `outputs/satisfaction.md`), so two reports in
  one folder never overwrite each other's figures;
- the **`.html`** (on by default: **Also save HTML**) carries the **look** —
  the report's stylesheet, page size, typefaces and every chart embedded in
  the one file. Widths, alignment and page breaks exist only here. Its tables
  print the same numbers as the `.md`: a statistics table as it rounds them,
  and a table such as a **Regression**'s coefficients, a **Principal
  components** loading or a **Cluster** centroid with six significant digits
  (`62.263`, `6.15462e-38`). With **Interactive charts in HTML** its charts
  answer the reader's pointer — see [Interactive charts](#interactive-charts).

Three rules make sure a report arrives:

1. A report is kept only under `outputs/`. The **File name** field keeps
   `outputs/` and `.md` fixed, so you type only the name, and the line under
   it says where a run leaves the report: "After a run: Files →
   outputs/*flow*/*name*.md". A path saved earlier outside `outputs/` is shown
   under "Other location, kept as it was written", with the reason ("This file
   isn't in outputs/, so a run doesn't keep it under Files.") and **Save it as
   … instead**.
2. Make it the flow's **Report path** (Flow settings, click the empty canvas;
   the Report view sets it for you) if you want **Run all** to keep it and put
   it in the [combined report](#the-combined-report). A **Save report** that
   is not the Report path is kept by a run of the flow but not by **Run all**,
   and its field says so. How the **Report path** follows its node, and the
   warning for one that names no node's file, are in
   [The combined report](Studio-Flows#the-combined-report).
3. There is no PDF writer. A name typed with `.pdf` is answered under the
   field — "Reports are saved as Markdown and HTML — for a PDF, open the HTML
   and print it." — with a fix that drops it. Print or convert the HTML
   instead ([below](#pdf-and-word)).

A run keeps at most 50 files (and 200 MB) under `outputs/`. When a flow
writes more — a report with dozens of charts — the report's `.md` and `.html`
are kept before the figures, so the report still arrives; the charts past the
cap are missing next to the `.md`, while the `.html` carries its charts
inside. With **Interactive charts in HTML** each chart also writes its
`.vl.json` beside its picture, which counts like a figure. See
[What a run keeps](Studio-Flows#running-a-flow).

A report produced by a run on the platform ends with a
[provenance footer](#the-provenance-footer) unless you turn it off in
**Settings → Reports**.

---

## Charts of results

A table of group means, a factor analysis's variance or a key-driver table
reads better with its picture beside it. A **Result chart** node draws that
picture from the analysis's own numbers, so chart and table never disagree:

1. On the canvas, add **Result chart** (Visualize) and connect the analysis's
   `table` to its **result** input — `variance` for a scree plot of a
   **Factor analysis** or **Principal components**, the `stat` of a
   **Proportion CI**. Connect the analysis's `stat` too if you like: the chart
   learns its base from it.
2. Leave **Kind** at `auto`, or pick another kind the result suits: the field
   lists them ("Group means (means.table) suits means — means with 95 %
   intervals; means_sd — means ± 1 SD. Auto draws means.").
3. Add both the table and the chart to the same section, for example the
   table at **Full** and the chart under it, or both at **Half** side by side.

What it draws for each analysis — means with their intervals and post-hoc
letters, the yes shares of McNemar and Cochran's Q, a TURF reach curve,
MaxDiff utilities, a scree plot, a forest of coefficients or odds ratios, key
drivers, a perceptual map, price curves — is listed under
[Result chart](Studio-Node-Reference#result-chart). The chart's title says
whether the result was weighted, so a reader never has to guess. For the
answers to a question — a distribution, a crosstab as bars (with
significance letters), a histogram, a donut, a battery of statements, a
measure month by month — draw from the data instead: **Bar chart** (with
**Split by** for a crosstab), **Likert chart** and **Trend**. To draw every
chart of a report in your brand's colors, see [Chart colors](#chart-colors).

---

## Writing the report in the Report view

The **Canvas | List | Report** switch in the flow editor shows the report as
a document over the same nodes. Everything you change here is a change to the
flow — visible on the canvas at once, saved with **Save changes**.

```
┌ Report title ──── satisfaction.md  [ ] Contents  [x] Also HTML  [ ] Interactive charts in HTML  [ ] Also Excel ┐
│ After a run: Files → outputs/satisfaction/satisfaction.md                                   │
│ Beside it: satisfaction.html, satisfaction_fig_1.png (a picture per chart)                  │
│ Change the file name                                                                        │
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

When the flow has a **Save report** node: **Report title**, the report's file
name (hover it for the whole path, "Saved as outputs/…"), **Contents** (a
table of contents), **Also HTML**, **Interactive charts in
HTML** ("Hover for a value and its base, click a legend entry to show or
hide a series. The HTML then carries the chart libraries (about 0.8 MB, once)
and the numbers each chart draws; the Markdown, the Excel and print keep the
pictures" — the node's parameter of the same name, off by default; with
**Also HTML** unchecked the box is grayed out and reads "Only the HTML has
interactive charts — tick Also HTML first"; see
[Interactive charts](#interactive-charts)), **Also Excel** ("Every
table of the report in one workbook beside it, named as the report with
.xlsx: a sheet per table with its statistics under it, and a Contents sheet
first; charts are left out" — the node's **Also save tables to Excel**, off
by default; see [Tables in Excel](#tables-in-excel)), and an icon that shows
the **Save report** node on the canvas. Without one: "This flow saves no report
yet. Add a section: it creates the **Save report** node and wires the section
into it."

Under the row, the report's file is spelled out as the node's **File name**
field spells it: "After a run: Files → outputs/*flow*/*name*.md", "Beside it:
…" (the `.html` with **Also HTML**, the `.xlsx` with **Also Excel**, and
"*name*_fig_1.png (a picture per chart)") and, when the node is not the flow's
**Report path**, "Run all keeps a report only when it is the flow's Report
path (in the Flow panel, with no node selected): run this flow on its own to
get this one." with **Make it the flow's report**. **Change the file name**
selects the **Save report** node on the canvas and puts the cursor in its
**File name**.

**Show on the canvas** — the title row's canvas icon, and the item of the
same name in each section's and each output's **⋮** menu — switches to the
**Canvas** view with the node selected in the inspector, and moves the
keyboard focus onto the node. With [focus mode](Studio-Flows#focus-mode) on,
the topbar and the project tabs step aside again as the canvas comes back.

### Sections

**+ Add section** ("A heading, a paragraph of Markdown, and any tables or
charts you add to it — all three optional") adds a **Report section** node
wired into **Save report**. The first one also creates **Save report** — title
= the flow's title, **File name** `outputs/<flow>.md`, **Also save HTML** on,
the project's house style (when it has one) as its look — and sets the flow's
**Report path** to the same file. Renaming or duplicating the flow moves that
default name to the new name (`outputs/<new>.md`), with the other file names
its nodes got from the flow's name (see
[Rename](Studio-Flows#rename)); a name you chose stays.

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
| **+ Add output** | a dropdown of every table, chart and statistic in the flow not yet in this section, as `node · Title (Type)`; a node with several tables names each by its output — `fa · Factor analysis · variance (Table)`, `fri · Paired tests · pairs (Table)`, `map · Perceptual map · rows (Table)`. "Every table and chart of the flow is already in this section." when there are none left |
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
and factor correlations, a paired test's main table and its pairs, a
perceptual map's dimensions, rows and columns, Van Westendorp's price points
and curves. **Remove
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

After a preview, each row also shows a small preview of that output, written
as the node's preview is (a p-value as the house style's **P values** says;
see [The project's house style](#the-projects-house-style)). A statistic
(**Stat**) is printed in the report as one line, `Caption: key = value; …` —
the caption is the label before the values; with the look's
[P values](#p-values) at **< 0.01**, a p below it reads `p < 0.01` there. It
has no size or placement: its row reads "one line", with the tooltip "A
statistic is one line of the report: size and placement apply to tables and
charts only".

### Size and placement

The size control on a row reads the width it is set to — **Full**, **¾**,
**⅔**, **½**, **⅓** — and opens the rest below the row:

| Control | Choices |
|---|---|
| width | **Full width**, **Three quarters**, **Two thirds**, **Half — two fit side by side**, **A third** |
| alignment | **left**, **center**, **right** — shown only when the item is narrower than the page; default center |
| space above | **Usual space above**, **No space above**, **More space above**, **Much more space above** — "The space between this item and the one before it in the HTML" |
| **New page** | "Start this item on a new page when the report is printed" |

Outputs narrower than the page that follow one another share a line — two at
**Half**, **Two thirds** and **A third**, three at **A third** — with the usual
gap between them; what does not fit wraps under them, and so does a table that
needs more room than its share. Text, a full-width output, **New page** or a
space above of its own starts a new line. That is the whole layout model, and
it is enough for almost every report. On a phone, and anywhere the report is
narrower than 480px, each takes the whole width; the preview pane is that
narrow by default, and when it stacks outputs you set side by side it says so
above the preview ("Items set side by side are shown one under another here,
as on a phone…") — widen it to see them together. Every table and chart keeps the look's
usual gap from the block before it (**Density** sets how much): **More** is
for two results that belong apart, **No space** for a chart that belongs right
under its table. A row that has been sized, or given a space of its own, says
so while folded: its control is drawn darker and names the choices on hover. The same control is in the **Report section** node's inspector, under
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
- With **Interactive charts in HTML** on (and **Also HTML**), the preview
  draws the charts as the run's HTML will. A preview opened straight from
  the file storage cannot be given the isolated frame those charts need, so
  there it shows each chart's picture, as print does; the report on the
  **Reports** screen is interactive either way.
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
shows it." Everything here reaches the `.html` only — except the **Chart
colors**, which also color the charts in the `.md`'s figures, and **P
values**, which sets how every p-value of the report is written, in the `.md`
too (see [P values](#p-values)). A **Save report** node whose look is empty
renders with the engine's defaults — in Studio as in the downloaded script.

The main choices — the four presets and **P values**:

| Control | Choices | Default |
|---|---|---|
| **Typeface** | **academic** (Source Serif 4, the questionnaire's own preset), **humanist** (Nunito), **modern** (Inter) | academic |
| **Density** | **compact** (14 px text, tight), **comfortable** (15.5 px), **spacious** (16.5 px) — type size, leading and the air between blocks | comfortable |
| **Tables** | **rules** (horizontal lines, the journal default), **grid**, **zebra** | rules |
| **Page** | **screen** (no page box, a measure of 720 px), **a4** (A4 with 22 mm margins), **letter** (Letter with 0.9 in margins) — "a4 and letter add page size and margins for printing" | screen |
| **P values** | **Exact** (every p as it was computed, such as `0.0123` or `3.2e-05`), **< 0.01** (a p below 0.01 reads `< 0.01`; any other as it was computed), **< 0.001** (the same below 0.001) — "how tables and statistics write a small p; results and exports keep the exact value" | Exact |

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
| **Chart colors** | **Series**, **Magnitude**, **Chart text**, **Diverging: low end**, **Diverging: high end**, **Grid lines**, **Chart typeface** — the colors of the report's charts whose **Palette** is `theme`; see [Chart colors](#chart-colors) |
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

### P values

**P values** decides how the report writes a p-value. **Exact**, the default,
writes every p as it was computed, as reports always have; **< 0.01** and
**< 0.001** write a p below that threshold as the bound and any other p as it
was computed (a p of exactly 0.01 is not below 0.01). The choice reaches every
p the report writes, in the `.md` and the `.html` alike:

- **Table cells** — every column of p-values: **Group means**' and its
  post-hoc pairs', a t-test's, a correlation's pairs', a regression's
  coefficients', **Paired tests**' and **Key drivers**'. A Tukey or
  Games-Howell p below 1e-07, otherwise written `< 1e-07`, reads as the bound
  too. Columns named after your answers, such as a crosstab's, are never
  changed, even when an answer is labeled "p".
- **Statistics lines** — the line under a table (a crosstab's chi-square p
  among them) and a statistics line of its own (a **Stat** output in a
  section) read `p < 0.01`, never `p = < 0.01`;
  so do a `Bartlett p` and the p of each pair that a comparison of groups
  names in a sentence. A **Proportion CI**'s `p` is the proportion, not a
  test's p, and is never changed.
- **The Excel workbook** ([Tables in Excel](#tables-in-excel)) — the cell
  keeps its number and shows the bound through its number format, so it still
  sorts, filters and calculates as the p it is.
- **Chart notes** — a **Result chart**'s note, such as a t-test's difference,
  reads `p < 0.01`; the tooltips of an interactive correlation heatmap
  follow it in their own style, `< .01`.

Only the writing changes: every result, the tables a node passes on, exported
files and a table's own Excel export keep the exact p. A tab book prints
significance letters, not p-values, so it is unchanged. The choice is stored
in the **Save report** node like the rest of the look (`"p_values": "0.01"`),
so the downloaded script and the research bundle write p the same way. Any
other value is refused on the node: "theme: p_values: '0.05' is not one of
exact, 0.01, 0.001."

The house style's **P values** does one thing more: it sets how Studio itself
writes a p-value in node previews and Live tiles; see
[The project's house style](#the-projects-house-style).

### Chart colors

The **Chart colors** disclosure puts your colors — a brand palette, a house
typeface — into the report's charts. It colors the charts whose **Palette**
is `theme` ("the report's chart colors (Save report's Look)") (a **Heatmap**'s
**Color map** `theme`); a chart that names a palette of its own keeps it. The
section says: "For the charts whose Palette is theme (a Heatmap's Color map
theme), in this report and in their previews. A chart that names a palette of
its own keeps it. Hex colors only: the charts are drawn by matplotlib, not by
a browser. Empty is the engine's default, a set readers with protanopia or
deuteranopia can tell apart."

| Control | What it colors | Empty means |
|---|---|---|
| **Series** ("2 to 12 colors, in the order the series take them") | bars, lines, slices and points, one color per series or answer, in order — a swatch per color to pick it, and a text box to paste the whole list (`#003f5c, #ffa600, #bc5090, #58508d`) | `#2a78d6, #eb6834, #335c00, #e08fff, #29c2a3, #8f0a5c, #cc4799, #5233a3` |
| **Magnitude** | one hue, light to dark: the answers of an ordered scale, the means of a heatmap | `#2a78d6` |
| **Diverging: low end**, **Diverging: high end** | the two ends of a diverging scale, low first: a Likert chart's disagree and agree sides, a correlation heatmap's negative and positive, the red, gray and blue of NPS and sentiment | `#e34948`, `#2a78d6` |
| **Chart text** | the charts' titles, labels, ticks and notes | `#1a1a1a` |
| **Grid lines** | the charts' grid | `#e0e0e0` |
| **Chart typeface** ("a font stack; the first face installed where the chart is drawn") | the charts' font, e.g. `Inter, sans-serif` | matplotlib's sans-serif |

Each color is a picker plus a text box, like **Colors** above; the text box
shows the default as its placeholder. Setting one end of the diverging pair
keeps the other end's default.

**Where the colors apply.** In the report — the `.md`'s figures and the
`.html` alike — every `theme` chart is drawn in its report's colors. Its node
preview, the **Preview report** pane and a **Live tile** after a run draw it
in the same look, the flow's **Save report**'s. (A flow whose **Save
report** nodes do not all name the same look — one that names none counts as
another, the engine's defaults — previews such a chart and draws its Live tile
in the default chart colors; each report still draws it in its own, and a
report that names no look keeps the engine's defaults, as from the research
bundle.) The chart colors travel with
the node like the rest of the look: in `scripts/<flow>.py` and in the
research bundle. The house style's **Chart colors** reach a flow when the
house style is stamped into its **Save report** node, like the rest of it.

**What the engine refuses**, named on the **Save report** node as you edit
and by **Check** — so a palette nobody could read never reaches a client:

- a color that is not hex: "theme: chart_palette: 'purple' is not a hex color
  such as '#2a78d6'.";
- fewer than 2 or more than 12 **Series** colors, or one given twice: "theme:
  chart_palette: give between 2 and 12 colors, in the order the series take
  them; got 1.", "theme: chart_palette: '#2a78d6' is given twice; two series
  would look alike.";
- a series or **Magnitude** color all but invisible on white: "theme:
  chart_palette: '#ffe8b2' on the charts' white background has a contrast of
  1.2:1; a bar or a line in it needs at least 1.3:1 to be seen.";
- **Chart text** that does not read: "theme: chart_text_color: '#cccccc' on
  the charts' white background has a contrast of 1.6:1; text needs at least
  4.5:1.";
- two equal diverging ends: "theme: chart_diverging: the two ends are the same
  color, so the scale would not diverge.";
- a typeface with CSS in it: "theme: chart_font: a list of font names
  separated by commas, without ; { } < >."

A light brand color passes as long as it reaches 1.3:1. The steps of an
ordered scale drawn from **Magnitude**, and the shades a chart makes for
series past the **Series** colors, are kept at 2:1 or darker on white, so a
pale gold still gives five steps a reader can tell apart. The default eight
colors stay apart for readers with protanopia or deuteranopia in any pair,
and a **Trend** of more than four lines also gives each line a marker shape
of its own. A palette you choose is yours to check.

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
- **Combined report** — where **Run all** writes the combined report: a path
  typed before a fixed `.md` (`reports/report.md` when left empty), with an
  `.html` copy beside it; the **combined** badge on the Reports screen
  follows it. The field's rules and messages are under
  [Settings → Reports](Studio-Project-Settings#reports).
- **House style** — the same form as the **Look** tab. A project started
  from the example study begins with one: the Look its six flows' reports
  use (**Typeface** **modern**, **Tables** **zebra**, teal **Links** and six
  **Chart colors** that readers with protanopia or deuteranopia can tell
  apart).

The house style is a **stamp**, never a setting a flow's report reads: a
flow's report always renders in the look of its own **Save report** node —
the same look its downloaded script and a research bundle use. It is used in
four ways:

1. It is **stamped** into a new **Save report** node — when the Report view
   creates one, and when you add one from the palette. From then on the node
   carries its own copy; changing the house style later does not change it.
2. It renders the **combined report** of **Run all**, which has no node of its
   own.
3. **Apply to every flow** ("Write this style into the Save report node of
   every flow, so each flow — and each bundle — carries it") copies it into
   every **Save report** node (or clears their looks when the house style is
   empty). If nothing changes: "Every flow already uses the house style".
4. Its **P values** sets how Studio writes a p-value where no report is
   involved: in a node's **Preview** pane, in the report composer's rows and
   in **Live** tiles, in Studio and on a public link. The form says so under
   **House style**: "Its P values also sets how Studio writes a p-value in
   node previews and Live tiles, so the study reads the same here as in its
   reports. They follow a change from their next run." A preview or a tile is
   written when it runs, so it shows a change from the next **Run to here**
   or recompute. A flow's own report still writes p as its **Save report**
   node's look says, and the combined report of **Run all** puts the flows'
   reports together as each wrote them.

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
┌ Reports ───────────────────────────┐┌ outputs/tables/key_tables.md   [Markdown] [HTML] [Excel] [Print / PDF] ┐
│ Data quality                       ││                                                                        │
│ cleaning · data_quality.md · 23/09 ││   Key tables                                                           │
│ Key tables                         ││   Life satisfaction                                                    │
│ tables · key_tables.md · 23/09     ││   How life satisfaction is distributed and how it varies by age, …     │
│ Screen use                         ││   …                                                                    │
│ usage · screen_use.md · 23/09      ││                                                                        │
│ …                                  ││                                                                        │
│ Report  combined                   ││                                                                        │
│ report.md · 23/09                  ││                                                                        │
│ Tab book  Excel                    ││                                                                        │
│ tables · tabbook.xlsx · 23/09      ││                                                                        │
└────────────────────────────────────┘└────────────────────────────────────────────────────────────────────────┘
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
  carries a **combined** badge. A flow's **Tab book (Excel)** workbooks are
  listed here too, with a table icon and an **Excel** badge: "Tab book" for
  a workbook named `tabbook.xlsx`, "Tab book: Client q3" for one of another
  name (`outputs/client_q3.xlsx`; a node added from the palette to the flow
  `tables` writes `tables_tabbook.xlsx`, "Tab book: Tables tabbook") — see
  [Tab books](#tab-books).
- **The document** renders in the middle: the HTML twin when there is one
  (exactly as the flow styled it), otherwise the Markdown with a plain
  stylesheet. It is shown as a document — scripts in a report do not run —
  except a report saved with **Interactive charts in HTML**: its charts work
  here, in a frame cut off from Studio, and the bar shows an **interactive**
  pill (see [On the Reports screen](#on-the-reports-screen)).
- **The bar** offers **Markdown**, **HTML** (only when the report has an HTML
  twin), **Excel** (only when a workbook of its tables is stored beside it —
  see [Tables in Excel](#tables-in-excel)) and **Print / PDF**.

**Markdown** ("The .md — with its figures in a .zip when it has any, since it
refers to them by file name") downloads a report with charts as
`<name>.zip`: a folder `<name>/` holding the `.md` and the figures it names,
so the images show wherever you unpack it. A report without figures
downloads as the plain `.md`. The toast names the file ("Downloaded
tables.zip"); a failure reads "Could not download tables.md. *reason*".
**HTML** downloads the one self-contained `.html`. **Excel** ("Every table of
the report in one workbook: a sheet per table, with its statistics under it,
and a Contents sheet") downloads `<name>.xlsx` ("Downloaded tables.xlsx").
Before you pick a report the pane reads "Reports render here as documents;
download them as Markdown or HTML — and their tables in Excel when the flow
saved them, and a flow's tab books — for your deliverables."

Each run of a flow replaces its report on this screen — so does a **Run all**
in which the flow succeeded; earlier versions stay downloadable from their
run cards in the flow's **Run history**. A renamed flow's earlier reports keep
the old name (`outputs/<old>/…`).

With no reports: "No reports yet — Run a flow with a Report node (or Run all)
and its report shows up here." with **Open Flows**. If a stored file cannot be
read: "The stored file could not be read — download it instead." with a
download button.

> **Tip.** To share a report, send the **HTML**: one file, charts inside —
> charts the client can hover and toggle when the flow has **Interactive
> charts in HTML** on ([send an interactive report](Studio-Recipes#send-an-interactive-report-to-a-client)). The
> **Markdown** zip is for a repository or an editor, the **Excel** workbook
> for a colleague who wants the numbers in a spreadsheet, a tab book for a
> client who wants every question by every segment. Reports have no
> share link of their own; for a live, read-only link use Live tiles
> ([[Live Monitoring|Studio-Live-Monitoring]]).

### Tables in Excel

Check **Also Excel** in the Report view's title row — on the canvas, **Also
save tables to Excel** on the **Save report** node — and run the flow. Beside
the report, under its name with `.xlsx` (`outputs/satisfaction.xlsx`), the
run writes every table of the report into one workbook. It is listed on the
run's card and under **Files** as `outputs/<flow>/<name>.xlsx`, and the
**Excel** button on this screen downloads it.

What the workbook holds:

| Sheet | Content |
|---|---|
| **Contents** (first) | the report's title, the line "One sheet per table of the report, its statistics under it; charts are not included.", then one row per table — **Sheet**, **Section**, **Table** (its caption, or what it is: "Group means: Age", "Perceptual map: Region × Overall satisfaction — rows (Region)") — each a link to its sheet |
| one per table | the table as the report prints it, its statistics under it after an empty row — numbers as numbers |
| `<name> – Post-hoc` | the post-hoc pairs of a **Group means**, with their method and notes under them |

- **Sheet names** come from the table's caption, else its section's heading,
  else the variable it describes, else `Table <n>` — cut to Excel's 31
  characters, without `[ ] : * ? / \`, and made unique ("Satisfaction",
  "Satisfaction (2)"). Write captions and the sheets are named after them.
- A **Banner table** keeps its significance letters in its cells
  (`21.2% (21) F`) and its notes under it.
- **Text stays text.** An open answer, label or caption that begins with `=`
  is written as a string, never as a formula Excel would run.
- **P values.** With the look's [P values](#p-values) at **< 0.01** or
  **< 0.001**, a p below the threshold keeps its number and reads as the
  bound (`< 0.01`) through the cell's number format, in the tables and in the
  statistics under them.
- **Not in it:** charts, the sections' text and notes, and statistics wired
  in as their own line (a **Stat** output). A report without tables gets a
  Contents sheet that says so.
- The workbook is written by every run of the flow — on its own, on a
  schedule, or in **Run all**, which stores it beside the flow's report as a
  single run does. A run with the box unchecked does not remove an older one:
  the **Excel** button then offers the workbook of the flow's last run that
  wrote it, which may be older than the report. The combined report has no
  workbook.
- A run keeps at most 50 files: the workbook counts like a chart. See
  [What a run keeps](Studio-Flows#running-a-flow).

### Tab books

A report's tables are the tables you chose for it. A **tab book** is the
other deliverable an agency hands over: every question of the study crossed
by a banner of segments — Total, then each gender, each region, … — one
sheet per question with its bases, counts, percentages and significance
letters. A flow writes one with a **Tab book (Excel)** node (Output):

1. Add **Tab book (Excel)** after your cleaning and weighting steps and
   connect the data to it.
2. Check the **Banner** variables (`gender`, `region`, `age_band`); leave
   **Questions** empty for every nominal, ordinal and multiple-choice
   question, or check the ones you want.
3. **Run** the flow. The workbook is written under the node's **File name**
   (`outputs/<flow>_tabbook.xlsx` for a node added from the palette) and
   kept as `outputs/<flow>/<name>.xlsx`, as the line under the field says.

On this screen it sits in the left rail beside the reports, as **Tab book**
with an **Excel** badge. Selecting it shows its path, an **Excel** button and
a note in place of a document — "A tab book from `tables`: every question it
tabulates crossed by the banner, a sheet each with its bases, counts and
percentages and the significance letters, a Contents sheet that links to them
and a Notes sheet on the weight, the test and what was left out. It opens in
Excel, LibreOffice or Google Sheets." — with **Download tabbook.xlsx**. It is
also on the run's card and in **Files**. A flow may hold several tab books,
each under a **File name** of its own; a second one added from the palette is
numbered (`<flow>_tabbook_2.xlsx`), and two nodes given one name are pointed
out with a fix. A path saved earlier outside `outputs/` is not kept, and the
node warns about it.

Each run of the flow, and each **Run all** in which it succeeded, replaces
the workbook here. A preview runs the node but keeps no file. What the sheets
hold, the test behind the letters and what is left out are under
[Tab book (Excel)](Studio-Node-Reference#tab-book-excel).

### PDF and Word

**Print / PDF** ("Open the print dialog — choose “Save as PDF” for a PDF
copy") opens your browser's print dialog on the report's own HTML, page box
and all. If you set **Page** to `a4` or `letter`, choose the same paper size
in the dialog and set its margins to none — the document already carries
them. A report without an HTML twin prints with Studio's own print margins
(18 mm top and bottom, 16 mm at the sides). A report with interactive charts
prints each chart's picture.

**For Word**, convert the HTML with [pandoc](https://pandoc.org):

```bash
pandoc report.html -o report.docx
```

The same command is in every research bundle's README. Studio does not render
Word or PDF on the server: a converter you run yourself is one you can pin,
and the HTML is the honest input to it.

---

## Interactive charts

A report's HTML can draw its charts in the reader's browser instead of as
fixed pictures: the reader points at a bar to read its exact value and base,
hides a series to compare the others, and zooms into a crowded scatter plot.
It is one checkbox, and it changes the HTML only.

### Turning them on

1. In the flow's **Report** view, check **Interactive charts in HTML** in the
   title row — on the canvas, the **Save report** node's **Interactive charts
   in HTML**. **Also HTML** must be checked too.
2. **Preview report** to see them, then **Run** the flow.

The box is off by default: a flow that does not check it writes exactly the
files it always did. With **Also HTML** unchecked it has nothing to act on —
the Report view grays it out, and a node that has it on anyway gets the
warning "Interactive charts in HTML draws the charts of the HTML — turn on
Also save HTML; the Markdown and the Excel workbook keep their pictures."

### What the reader can do

| Action | What happens |
|---|---|
| Point at a bar, point, segment or cell | a tooltip gives its label, its value — written as the picture writes it — and its base (`400 respondents`) |
| Click a legend entry | hides that series (its entry fades); click again to show it |
| Double-click the chart | shows every series again |
| Hold `Ctrl` (`Cmd` on a Mac) and scroll, or pinch | zooms a **Scatter plot**, a **Trend** of more than 24 periods or a **Perceptual map**; drag to move, double-click to reset — the note under the chart says so |
| **Names on the map** (a Perceptual map) | writes or hides the points' names; every name is in its point's tooltip either way. It starts unchecked for a map too crowded to name its points |
| Point at a **Van Westendorp** chart | draws a line at that price and gives every curve's share there |
| The chart's **…** menu | **Save as PNG** or **Save as SVG**, named after the report and the chart (`key_tables-life-satisfaction-by-age-group.png`) — nothing else: no "open in editor", which would send the chart's numbers to a web site |

Every chart node has this form — each **Bar chart** form (histogram and
donut included), the **Likert chart**, the **Heatmap**, the **Box plot**, the
**Scatter plot**, the **Trend** and every kind of **Result chart** — drawn
from the same numbers as its picture, in the same colors (the Look's
[Chart colors](#chart-colors) for a chart of **Palette** `theme`), with the
same title and the same notes under it (base, weighting, missing codes left
out). On a phone the chart narrows with the page and its menu button sits
over its corner.

### What the file carries

The `.html` is still one file that opens in any browser, offline, and
fetches nothing from anywhere — which is what makes it something you can
email to a client as it is. For that it carries:

- **The chart libraries** — Vega, Vega-Lite and Vega-Embed, open-source code
  under the BSD 3-Clause license, with their license notices — about 0.8 MB,
  once, however many charts the report has. A report whose HTML was 0.8 MB
  with six charts is about 1.7 MB with them interactive.
- **Each chart's numbers**, as a Vega-Lite spec: what the chart draws —
  counts, percentages, means, intervals, bins, a heatmap's cells, a result's
  estimates — never a respondent's own answers, **except** in the two charts
  that plot respondents one by one. A **Scatter plot** carries each point's
  **X**, **Y** and **Color by** group; a **Box plot** carries its outliers
  and, with **Show points**, every point — each a value and its group. No
  respondent id, no other answer, and the points are listed in sorted order,
  so a point's place in one chart does not match it to a point in another.
  Anyone who has the file can read these numbers, not only see them — see
  [Security and Privacy](Studio-Security-and-Privacy#interactive-charts-and-your-data).
- **Each chart's picture**, as before: it is what prints, what a reader
  whose browser runs no scripts sees, and what shows if a chart cannot be
  drawn.

Beside the Markdown, each figure's spec is written next to its picture
(`satisfaction_fig_3.png`, `satisfaction_fig_3.vl.json`). The run's card and
**Files** list them with a chart icon and the hint "Interactive chart: a
Vega-Lite 6 spec with the numbers the chart draws — the report's HTML draws
it"; the **Markdown** download keeps them beside the figures in its `.zip`.
The `.md` itself and the [Excel workbook](#tables-in-excel) are unchanged —
they keep the pictures.

### On the Reports screen

An interactive report has an **interactive** pill in the bar ("Its charts
answer the pointer: hover for a value and its base, click a legend entry to
show or hide a series. The report's scripts run in a frame of their own, cut
off from Studio."), and its **HTML** button says "One file that opens in any
browser, offline, with its interactive charts: it carries the chart
libraries and the numbers each chart draws".

Its charts work here as in the file, but in a frame of their own: the
report's scripts cannot read your Studio session, Studio's pages or storage,
call Studio's API, fetch anything, open windows, submit forms or start
downloads. The charts' **…** menu is hidden here for that reason — download
the **HTML** to use it, or take a figure's PNG from the run's card. Only a
report that carries the engine's chart libraries and interactive charts runs
scripts at all; any other report, including one whose text contains a
`<script>` of its own, is shown with none. **Print / PDF** prints each
chart's picture.

### In the combined report

In the [combined report](#the-combined-report) of **Run all**, the figures of
each flow whose **Save report** has **Interactive charts in HTML** checked
are interactive too, and the other flows' figures stay pictures. The research
bundle's `README.md` lists the reports with interactive charts, and the
Methods draft says that the report had "its charts interactive in its HTML
version".

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

Uncheck the box, and the next runs — on the platform and from a research
bundle made from that Save — write their reports without the footer. Reports
already written keep theirs.

---

## The combined report

**Run all** (Flows → **More ▾ → Run all flows**) runs every flow and then
writes one combined document, titled with the questionnaire's title — the
example study's is *Digital Life & Wellbeing 2026* — or "Combined report"
when the questionnaire has none:

- a **Contents** list, then one chapter per flow, in the order the flows ran
  — a flow after the flows whose tables it reads, alphabetical where that
  leaves a choice (see [Run all](Studio-Flows#run-all)). Each chapter is
  headed with its report's own title (*Data quality*, *Key tables*, …), the
  flow's title stands under the heading (*1. Clean raw responses*), and the
  report's sections follow one heading level down;
- only flows whose **Report path** (Flow settings) names their report are
  included;
- the [provenance footer](#the-provenance-footer), when it is on, once at the
  end rather than after every chapter;
- written to `reports/report.md` (or the path in **Settings → Reports**) with
  an `.html` twin in the house style; charts are copied beside it as
  `<flow>__<report>_fig_N.png` (an `_` in the flow name becomes `-`), taken
  from each flow as soon as it finishes, so two flows' figures never mix. The
  `.html` twin carries its figures inside it, so it shows them on this screen
  and wherever you open the downloaded file. A figure whose flow drew it
  interactively has its `.vl.json` copied beside it the same way, and is
  interactive in the `.html` twin (see
  [In the combined report](#in-the-combined-report)).

Because it is assembled from each flow's Markdown, the combined HTML has the
house style's typefaces, measure and page box but plainer tables than a single
flow's own HTML.

**When a flow fails**, **Run all** still runs the flows that do not depend on
it and ends as failed — and still writes the combined report from the flows
that succeeded, its title marked incomplete: *Digital Life & Wellbeing 2026
(incomplete)*, or **Combined report (incomplete)** for a questionnaire without
a title. Its first section,
**Missing from this report**, reads: "This Run all did not finish every flow,
so this report has only the sections of the flows that did. Not in it:",
then one line per flow — "**tables** — failed: *reason*" or "**charts** —
skipped: needs tables, which failed" — and "Fix them and run all flows again
for the complete report." It replaces the previous combined report on this
screen. Only when none of the flows that succeeded has a report is no
combined report written, and the last one stays.

A flow whose **Report path** names a file it did not write counts as failed
("report outputs/tables.md was not written: the flow's Report path names a
file none of its nodes saves — choose one of its Save report nodes in Report
path"); the other flows, including those that read its tables, go on. The
**Report path** is chosen from the flow's **Save report** nodes and follows
its node, so this happens only to one saved earlier or set through the API,
which **Check** and the Save warn about first — see
[The combined report](Studio-Flows#the-combined-report).

**Run all** also stores each successful flow's own report (its `.md`, `.html`,
figures and the workbook of its tables) and its tab books under
`outputs/<flow>/`, where a single run of the flow puts them, so this screen
shows the flows' reports and tab books from that Run all too. See
[Run all](Studio-Flows#run-all).

---

## Tips

- **Write captions.** A caption per table is what turns a run output into a
  readable document, and it costs one line — and it names the table's sheet
  in the Excel workbook.
- **Put the chart beside its table.** A **Result chart** draws the table's
  own numbers, weighted or not as the table is; two outputs at **Half** sit
  side by side.
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
- **Brand the charts in the Look, not chart by chart.** Set **Chart colors**
  once and give the charts **Palette** `theme`; changing the brand later is
  one edit.
- **Send a tab book with the report.** The report tells the story; the tab
  book lets the client look up any question by any segment.
- **Send the interactive HTML to a client** who wants exact values: check
  **Interactive charts in HTML**, and one file lets them read every value and
  base and switch series on and off, offline. Look at its scatter plots and
  box plots first — they carry each plotted respondent's values.

## See also

- [[Analysis Flows|Studio-Flows]]
- [[Node Reference|Studio-Node-Reference]]
- [[Project Settings|Studio-Project-Settings]]
- [[Reproducibility: Code, Bundles and Citation|Studio-Reproducibility]]
- [[Live Monitoring|Studio-Live-Monitoring]]

<!-- studio-nav -->
---

← [[Coding Open Answers|Studio-Open-Answer-Coding]] · [Studio contents](Studio-Overview#all-pages) · [[History and Versions|Studio-History-and-Versions]] →
