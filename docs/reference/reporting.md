# `siamang.reporting` — Declarative Reporting & Visualization Reference

The `reporting` subpackage provides a high-level, declarative API for generating publication-ready statistical tables and data visualizations. Designed for quantitative social scientists and sociologists, the system automatically leverages variable metadata (such as variable labels, value labels, and measurement scales) to choose appropriate statistics, perform significance tests, and format charts [1] [2] [3].

To make this reporting API extremely convenient, it is attached directly to the `SurveyData` class via the `report` and `plot` accessors [2].

```python
from siamang.reporting import (
    FreqTable, CrossTable, GroupMeanTable,
    BarChart, BoxPlot, HeatMap, ScatterPlot
)
```

---

## 1. Table Components

All table components are subclasses of the base `SurveyTable` class. They are bound to a `SurveyData` container.

### Base Class: `SurveyTable`

Every table component supports the following common interface:

#### Methods

* **`to_frame() -> pd.DataFrame`**:
  Returns the raw pandas DataFrame representation.
* **`to_markdown() -> str`**:
  Returns a clean, pipe-formatted GitHub-flavored Markdown table.
* **`to_html() -> str`**:
  Returns a clean HTML `<table>` string with basic class styling.
* **`export_xlsx(path: str | Path) -> Path`**:
  Exports the table directly to an Excel sheet named `"Table"`. The destination directory must already exist.

The statistics a table reports (`stats`) print under it as `key = value`,
joined by `; ` — and a statistics mapping given to `Report.add` prints the
same way. A float keeps up to four decimals without padding (`df = 124.98`; a
whole one keeps its `.0`), and one below 0.0001 keeps four significant digits
with its exponent (`p = 5.8e-07`, `p = 7.988e-32`), so nothing that is not 0
reads `0.0000`; one below 1 that four significant digits already hold is
printed as it is (`p = 0.002343`). A p-value in the `stats` or a table cell of
these tables keeps four decimals, or below 0.0001 four significant digits
(`1.134e-24`), so its footer prints the same p; Paired tests and factor
analysis keep four significant digits throughout — statistics, cells and
footer alike (`p = 0.002343`, `Bartlett p = 0.00227`). The
HTML writes each number of a table as the Markdown does, so the `.html` and the
`.md` of a report show the same values: a table component's cells as they are
kept, and a bare DataFrame given to `Report.add` — not rounded — as tabulate
prints it, a float with six significant digits (`62.263`, `6.15462e-38`).

#### Weighted data

Every table reads `SurveyData.weight` (set by `with_weight()`, the flow's Apply weight node) and says in `stats` what it did with it. `FreqTable` sums weights for N and the percentages and adds an `Unweighted N` column; `CrossTable` sums weights in its cells and runs χ² on the counts scaled to Kish's effective base (with `test=False` its stats still give `Weighted N` and `Weight`); `GroupMeanTable` weights means, SDs and medians while N, the test and any post-hoc pairs stay unweighted, and says so in `Note`. Fisher's exact test in `CrossTable` counts respondents and says so in `Base`; `CorrelationMatrixTable` weights Pearson's coefficient (p on Kish's effective base) and `TTestTable` states `Weight: unweighted (the weight '<column>' is not applied)`. The banner, NPS, MaxDiff and conjoint tables are weighted throughout and name the `Weight`. The quality and theme tables count responses and state `Weight: unweighted (the weight '<column>' is not applied)`. The full list, including the analysis methods, is in the data reference under *What the weight reaches*.

---

### Univariate Frequencies: `FreqTable`

Generates frequency distributions with absolute counts, percentages, and cumulative percentages.

#### Properties

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `data` | `SurveyData` | *Required* | The `SurveyData` container. |
| `column` | `str` | `""` | Name of the variable to analyze. |
| `exclude_missing` | `bool` | `True` | If `True`, filters out missing values from the base. |
| `sort` | `str` | `"value"` | Sort order: `"value"` (sort by code value, default), `"freq"` (descending count), or `"label"` (alphabetical by value label). Any other value is silently ignored and the table keeps code order — a typo will not raise an error. |

#### Example

```python
from siamang.reporting import FreqTable

table = FreqTable(data, column="remote_freq", sort="value")
print(table.to_markdown())
```

---

### Bivariate Cross-tabulations: `CrossTable`

Generates two-way contingency tables with optional statistical tests (Chi-square, Cramer's V, Phi) and automatic percentages [1] [2].

#### Properties

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `data` | `SurveyData` | *Required* | The `SurveyData` container. |
| `row` | `str` | `""` | Row variable name (usually the independent variable). |
| `col` | `str` | `""` | Column variable name (usually the dependent variable). |
| `pct` | `str` | `"none"` | Percentage direction: `"row"`, `"col"`, `"total"`, or `"none"`. |
| `test` | `bool` | `True` | If `True`, runs the test `method` names and appends it to the footer. |
| `method` | `str` | `"chi2"` | `"chi2"`: a Chi-square test of independence with $\chi^2$, $df$, $p$-value, and Cramér's V [1] [3]. `"fisher"`: Fisher's exact test — for a 2 × 2 table p, the conditional odds ratio (`Odds ratio`, `OR 95% CI`, `Odds ratio of` naming the cells), for a larger one the Fisher-Freeman-Halton p (`p method`: exact, or Monte Carlo from 20,000 tables with a fixed seed). It counts respondents, leaves the codebook's missing codes out of the table and test, and names them in `Missing codes left out`. |

#### Example

```python
from siamang.reporting import CrossTable

table = CrossTable(data, row="it_role", col="remote_freq", pct="row", test=True)
print(table.to_markdown())
```

---

### Grouped Means: `GroupMeanTable`

Compares means of an interval/ratio variable across categories of a nominal/ordinal grouping variable [1].

#### Properties

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `data` | `SurveyData` | *Required* | The `SurveyData` container. |
| `column` | `str` | `""` | Continuous dependent variable (interval/ratio). |
| `by` | `str` | `""` | Categorical independent variable (nominal/ordinal). |
| `test` | `bool` | `True` | If `True`, runs a significance test: ANOVA, t-test, Kruskal-Wallis, or Mann-Whitney U [1] [3]. |
| `method` | `str` | `"auto"` | `"auto"` chooses as below. Or by hand: `"student"`, `"welch"`, `"anova"`, `"welch_anova"`, `"mannwhitney"`, `"kruskal"`; the footer then gives `Test`, the statistic, `df` (none for Mann-Whitney's U), `p` and an effect size (Cohen's d, η², rank-biserial r, ε²), and the codebook's missing codes are left out of the table and the test (`Missing codes left out`). A two-group test of more groups reports `Test = not run: …`. |
| `posthoc` | `str` | `"none"` | `"tukey"` after `"anova"`, `"games_howell"` after `"welch_anova"`, `"dunn"` after `"kruskal"`; any other pairing is a `ValueError`. The pairs are a `PostHocTable` (`posthoc_table`), rendered under the means table by `to_markdown` / `to_html` and written to a second sheet by `export_xlsx`; the footer's `Post-hoc` counts the pairs that differ at p < 0.05. |
| `adjust` | `str` | `"holm"` | Dunn's p adjustment: `"holm"` or `"bonferroni"`. Tukey and Games-Howell control the family-wise error themselves. |

#### Test Selection Logic

Siamang automatically chooses the appropriate significance test based on the data structure:
* **Dependent variable is `ordinal`**: Non-parametric tests are chosen.
  * Grouping variable has **2 categories**: **Mann-Whitney U** test.
  * Grouping variable has **3+ categories**: **Kruskal-Wallis H** test.
* **Dependent variable is `interval` or `ratio`**: Parametric tests are chosen.
  * Grouping variable has **2 categories**: **Independent t-test**.
  * Grouping variable has **3+ categories**: **One-way ANOVA**.

#### Example

```python
from siamang.reporting import GroupMeanTable

table = GroupMeanTable(data, column="autonomy", by="remote_freq", test=True)
print(table.to_markdown())

chosen = GroupMeanTable(data, column="age", by="it_role", method="anova", posthoc="tukey")
chosen.posthoc_table.to_frame()   # Pair, Difference, 95% CI low / high, q, p
```

---

### Tests chosen by hand: `TTestTable`, `CorrelationMatrixTable`, `PostHocTable`

In `siamang.reporting.stat_tables`, built on `siamang.data.inference`. Each leaves the codebook's missing codes out and says so. A cell the data leaves undefined — the SD and SE of a group with one answer or none, a post-hoc pair that could not be compared, a correlation with a constant variable — is NaN in `to_frame()` and blank in `to_markdown()` / `to_html()` (and so in a Studio preview), never `nan` or `None`; the correlation matrix's `matrix` layout writes `n/a` in the cell of a pair it could not compute. The stats say why (`Not computed`).

* **`TTestTable(data, column, kind="independent", by=None, groups=None, other=None, mu=0.0, variances="welch", confidence=0.95)`** — one row per group (independent: the two groups of `by`, or the two codes in `groups` when `by` has more — without them such a `by` is a `ValueError` listing its groups, and two codes naming the same group, or a multiple-choice `by` or `column`, are a `ValueError` too), per measurement (paired: `column` and `other` over the complete pairs, plus their difference) or for the variable (one-sample against `mu`): `N`, `Mean`, `SD`, `SE`. Stats: `Test` (Welch's or Student's t-test, Paired t-test, One-sample t-test), `t`, `df`, `p`, `Mean difference` and `Difference` (which minus which), `95% CI`, `Cohen's d` (`Cohen's d (d_z)` for paired data), `Hedges' g` (two groups), `N`, and `Test value`, `Incomplete pairs left out` where they apply.
* **`CorrelationMatrixTable(data, columns, method="spearman", missing="pairwise", adjust="none", layout="matrix")`** — `layout="matrix"`: a `Variable` column and one column per variable, the lower triangle holding coefficients with `*` (p < .05), `**` (p < .01), `***` (p < .001) on the adjusted p when `adjust` is set, `—` on the diagonal. `layout="pairs"`: `Variable 1`, `Variable 2`, the coefficient (`r`, `rho`, `tau`), `p`, `p (Holm)` (or the adjustment chosen) and `N`. Stats: `Method`, `Missing`, `N` (a range when pairwise N differs), `p adjustment` (the method and the pairs it adjusted over — `over the 1 pair computed (of 3)` when some could not be computed), `Marks`, `Not computed`. `result` holds the square frames.
* **`PostHocTable`** — what `GroupMeanTable.posthoc_table` returns: Tukey and Games-Howell give `Pair`, `Difference`, `95% CI low`, `95% CI high`, `q` (Games-Howell also `df`) and `p` (`< 1e-07` below what SciPy computes the studentized range to, with the footer's `p` saying so); Dunn gives `Pair`, `Mean rank difference`, `z`, `p (unadjusted)` and `p (Holm)` / `p (Bonferroni)`.

---

## 1b. The look of a report: `ReportTheme`

`Report.to_html()` returns a fragment by default — the report's Markdown put
through `markdown`, for splicing into a page of your own. `to_html(standalone=True)`
(and `save("report.html")`) returns a whole document instead: a `<head>`, a
stylesheet compiled from a `ReportTheme`, tables rendered by the table components
themselves, and figures in a `<figure>` with their caption.

```python
from siamang.reporting import Report, ReportTheme

theme = ReportTheme(font_preset="academic", page="a4", number_tables=True)
Report(title="Satisfaction 2026", theme=theme).text("…").save("report.html")
```

The theme is the same shape as the questionnaire's `UIConfig`: **one named preset
plus tokens you may override**, stored sparsely (`to_dict()` writes only what
differs from the defaults). `academic`, `modern` and `humanist` name the same
typefaces as the survey presets, so a report and the questionnaire it came from
can be set in the same type.

| Field | Values | What it does |
| :--- | :--- | :--- |
| `font_preset` | `academic` · `modern` · `humanist` | body and heading stacks |
| `density` | `compact` · `comfortable` · `spacious` | type size, leading, block gap, cell padding |
| `table_style` | `rules` · `grid` · `zebra` | `rules` is the research-paper table: horizontal only |
| `page` | `screen` · `a4` · `letter` | adds an `@page` rule with the paper's margins |
| `width` | a CSS length | the measure on screen (720px); ignored on paper |
| `font_size`, `line_height`, `table_font_size` | CSS length / number | override the density |
| `font_family`, `heading_font_family`, `mono_font_family` | a CSS font stack | override the preset |
| `text_color`, `muted_text_color`, `border_color`, `accent_color`, `background_color` | a color | |
| `table_width` | `auto` · `full` | |
| `align_numeric` | bool | numbers right, on tabular figures |
| `figure_width`, `figure_align` | CSS length, `left`/`center`/`right` | the default for a figure |
| `figure_dpi` | 72–600 | what figures are written at |
| `caption_position` | `below` · `above` | |
| `number_tables`, `number_figures`, `table_label`, `figure_label` | bool, str | `Table 1.` prefixes; off by default |
| `chart_palette` | 2–12 hex colours | the series of a chart of `palette="theme"`, in order |
| `chart_sequential` | a hex colour | magnitude (a heatmap of means) and the steps of an ordered scale |
| `chart_diverging` | two hex colours | a scale's low end and high end (Likert, NPS, sentiment, correlations) |
| `chart_text_color`, `chart_grid_color` | a hex colour | the charts' text (at least 4.5:1 on white) and grid lines |
| `chart_font` | a font stack | the charts' face: the first of the stack installed where they are drawn |
| `custom_css` | CSS | appended last, so it wins — and checked by nothing |

**Chart colours.** The `chart_*` fields colour every chart whose palette is
`"theme"` (a heatmap's `cmap="theme"`) — and no other, so a chart that names a
palette of its own draws the picture it always drew. Their defaults
(`siamang.reporting.chart_theme`) are chosen for readers with colour-vision
deficiencies: eight colours, `#2a78d6 #eb6834 #335c00 #e08fff #29c2a3 #8f0a5c
#cc4799 #5233a3`, any two of which are at least 9.5 apart in OKLab (×100) with
protanopia and deuteranopia simulated (Machado, Oliveira & Fernandes 2009) and
17 with full colour vision, each at least 2:1 on white — so a chart of up to
eight series can put any two side by side — ordered so the first three are
14.6 apart; a Trend of more than four lines gives each line's points a shape
of its own too (and its legend entry);
blue `#2a78d6` for magnitude; red `#e34948` to blue for a scale that diverges;
text `#1a1a1a` and grid `#e0e0e0`. Colours are hex only (`#rgb` or `#rrggbb`):
they are drawn by matplotlib, not a browser. A list may be given as one string
(`"#2a78d6, #eb6834"`); a palette or sequential colour under 1.3:1 on white
(`#ffe8b2`) is refused, as a bar or a line in it all but disappears. Past the
palette a chart takes its colours darker, then lighter as far as they keep 2:1
on white (a colour already under that, a little darker instead), then hues
spaced round the wheel, never one twice. An ordered scale's steps run from a
tint of the sequential colour still 2:1 on white to the colour at half its
lightness — from the colour darkened to 2:1 when it is lighter than that (a
yellow, a light blue), and from its tint straight to its half when it is near
black — each step its own colour; a diverging scale's arms from each end to a
tint of it 45 % of the way to white, the neutral answer grey (`#bdbdbd`). A
value written on a bar, a segment or a cell is white or the text colour,
whichever reads better — black where neither reaches 4.5:1, which one of white
and black always does. Secondary text (the notes under a chart) is the text
colour as light as still reads 4.5:1 on white. In the theme's colours a
`BoxPlot`'s boxes take the palette in the order they are drawn, undimmed, and a
`ScatterPlot`'s groups in the codebook's order, its legend titled by the
variable's label. A `BarChart`'s Other (`top`, a donut's small slices) is the
neutral grey, none of the palette's; its error bars and significance letters,
and a donut's base and the percentages beside its ring, are the text colour,
the lines to those percentages the secondary text colour; a histogram's bars,
in every panel, are the palette's first colour.

A chart is drawn when it is made (a flow draws it at its node, so what it
cannot draw fails that node), and the report's theme is known only when the
report is rendered. So a chart of palette `"theme"` is drawn at first in the
theme `SIAMANG_REPORT_THEME` names, else the defaults; and `to_markdown`,
`to_html` and `save` draw it again, from its parameters, in the chart colours of
the theme they render with whenever those differ
(`siamang.reporting.chart_theme.in_report`) — a copy, kept for the next
rendering; the chart itself keeps its picture. The Markdown's figures take the
document's theme too, so `.md` and `.html` show the same charts.

`ReportTheme.from_env()` reads the JSON file named by `SIAMANG_REPORT_THEME`,
the way `output.save_report` reads `SIAMANG_PROVENANCE`: whatever runs a flow can
say how its reports should look without editing the flow. A missing or malformed
file falls back to the defaults rather than failing the run.

`stylesheet()` is a pure function of the theme — no clock, no locale, no network,
no `@import` — so the same theme gives the same bytes on every machine.

**Markdown and HTML carry different things, on purpose.** The `.md` is the
report's content: text, order, captions, notes, the provenance footer. It stays
plain Markdown that diffs and travels, and a theme never changes a byte of it.
The `.html` is the document as it is meant to be read. Both are written from the
same blocks, so neither can drift from the other.

**Rendering it elsewhere.** There is no PDF writer here; `save("r.pdf")` says so
and names the two things that work: print the HTML from a browser, or
`pandoc report.html -o report.pdf` (`-o report.docx` for Word). Both honor the
theme's `@page` rule.

**Tables to Excel.** `Report.save_tables(path)` (`siamang.reporting.workbook.save_tables`)
writes every table of the report to one `.xlsx` workbook — any other suffix is a
`ValueError`. Each table gets the sheets its own `export_xlsx` writes (Group means
with a post-hoc test: `<name>` and `<name> – Post-hoc`; a Banner with its letters),
a bare DataFrame is written without its index (a two-row header joined with ` / `),
and the table's `stats` go under it after an empty row (the post-hoc table's own
under the pairs). Text is written as text: a cell, caption or heading beginning
with `=` is a string, never a formula (`siamang.io.excel_text`, which the tables'
`export_xlsx` and the data's Excel export use too). Sheets are named by
caption, else section heading, else `stats["Variable"]`, else `Table <n>`: at most
31 characters, without `[ ] : * ? / \` or an apostrophe at either end, unique
regardless of case (`(2)`, `(3)`…), never `History`. A `Contents` sheet comes first:
the report's title, a line saying charts are not included, and one linked row per
sheet (the link quoting the sheet's name with an apostrophe inside doubled,
`#'Brand''s image'!A1`: `siamang.io.excel_text.sheet_link`) with its section and
caption (`Frequencies: Region` for a table without one; `Perceptual map: Brand ×
Region — rows (Brand)`, `Price sensitivity: Gabor-Granger — curves`, `Key drivers:
Liking`, `Paired tests: Cochran's Q` for the later analyses). Charts, text and statistics mappings are not tables and are skipped.

`Report.add()` and `Report.image()` take a **`width`** (a CSS length), an
**`align`** and a **`break_before`**, checked where they are written rather than
where they are rendered. Two items at `width="48%"` with `align="left"` sit side
by side. Like the theme, they reach the HTML only.

`sample_report(theme)` builds a short report using every kind of block, from
literals rather than from data, so a theme can be previewed without a run.

---

## 2. Visualization Components

All chart components are subclasses of the base `SurveyChart` class.

### Base Class: `SurveyChart`

Every chart component supports the following common interface:

#### Properties

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `data` | `SurveyData` | *Required* | The `SurveyData` container. |
| `figsize` | `tuple[float, float]` | `(10, 6)` | Figure dimensions in inches `(width, height)`. |
| `palette` | `str` | `"muted"` | Seaborn color palette name (e.g., `"muted"`, `"deep"`, `"pastel"`, `"colorblind"`), or `"theme"`: the chart colours, text colour, grid and face of the report theme (§1b, *Chart colours*). |
| `title` | `str \| None` | `None` | Optional chart title. If `None`, automatically generated from variable labels. |
| `weight_note` | `str \| None` | — | Read-only. `None` on unweighted data; otherwise `"weighted by '<column>'"` for a chart that draws weighted numbers, or `"unweighted (the weight '<column>' is not applied)"` for one that cannot. |

#### Weighted data

A chart on weighted data (`SurveyData.with_weight`) never disagrees in silence with the weighted tables beside it. `BarChart` draws sums of weights (axis "Weighted count") or weighted means (axis "Weighted mean …"), and `HeatMap` with `by` draws weighted means (colour bar "Weighted mean"). `BoxPlot`, `ScatterPlot` and the correlation `HeatMap` have no standard weighted form: they draw the respondents as they are, and the title gets a second line, `unweighted (the weight '<column>' is not applied)` — kept under a title you set yourself too.

#### Methods

* **`plot() -> plt.Axes`**:
  Builds and returns the matplotlib Axes object.
* **`show() -> None`**:
  Displays the plot inline (ideal for Jupyter notebooks).
* **`save(path: str | Path, dpi: int = 150) -> Path`**:
  Saves the plot to a file (`bbox_inches="tight"`). The destination directory must already exist.
* **`png(dpi: int | None = None) -> bytes`**:
  The chart as PNG bytes at `dpi` (default: the chart's `dpi`), the bytes `save` writes to a `.png`.
* **`release() -> None`**:
  Closes the figure and lets go of it, keeping the PNGs rendered so far. A figure holds its drawing (megabytes at 150 dpi) for as long as the chart refers to it, closed or not. After `release`, `png` and `save` to a `.png` at a resolution rendered before write those bytes without drawing; `plot`, `show`, another resolution or format draw the chart again from its parameters. A `Report` releases each chart once it has written it (but one whose figure was asked for with `plot()` or `show()`), and `FlowRunner` each chart once its node has rendered it.

---

### Categorical Distribution: `BarChart`

Plots the counts or percentages of a categorical variable, its answers within each group of a second variable (`split`: the chart of a crosstab), or mean values of a continuous variable across groups (`by`) — or, as `layout="histogram"`, the distribution of a number, and as `layout="donut"`, one variable's answers as the parts of a whole. On weighted data the counts are sums of weights, the percentages weighted and the means weighted means.

While `show`, `split` and `sort` keep their defaults, and none of `top`, `other`, `intervals`, `letters` or a histogram or donut layout is asked for, the chart is the one `BarChart` has always drawn. The other forms (`siamang.reporting.bars`) leave the codebook's missing codes out of the bars and say how many, and write under the plot the base (respondents who answered, and the weighted base), the weight, and for a multiple-choice question that its percentages are of respondents and add up to more than 100 %. They also draw a multiple-choice question, which the older chart could not (it raised `unhashable type: 'list'`); a multiple-choice question is drawn by them whatever the parameters. One series has one colour; the steps of an ordered scale (ordinal and up) are one hue light to dark; a colour belongs to its answer — its place among all the answers given — whatever `sort` does to the order and whatever Top N or a donut's Other leaves out, so one answer has one colour in every chart of a report. A number (interval or ratio, without value labels) with more than `MAX_VALUES` (30) values given is not drawn a bar, a slice, a series or a group each: `Age is a number with 84 different values given, and this chart draws a bar for each: layout='histogram' draws its distribution (or band it first with Bands).` (`… a slice for each …` for a donut; `Split by Age is a number with 84 different values given, a group for each: band it first (Bands) to compare its ranges.`); `by` draws its mean per group as before. A chart of a variable nobody answered says `No respondent answered X.` Long labels wrap, a word is never broken — one longer than its bar's room makes the labels smaller (to 8 pt) or, below that, turns them 45° in as many lines as two turned neighbours leave room for (at most 40 characters a line); vertical bars whose labels cannot be placed even so are drawn horizontally. Labels under vertical bars are fitted again to the plot as it is laid out (the value axis's title and ticks take their room from the figure's width): level ones keep an em apart and are made smaller or turned when they come closer, turned ones take as many lines as their measured spacing holds, and when neither can be read the bars are drawn across. A group's `(n = 1,613)` is never broken over two lines. A count axis (and a mean's of thousands, whose values read `41,646.65`) is thinned until its labels keep half an em apart, and the ticks found are kept for the save. Beside horizontal bars each label gets a row: the labels are tried at 11 pt in 28 % of the width, then smaller (to 8 pt) and wider (to 45 %), and when they still overlap the figure grows to a row per label's height. The axis titles wrap to the plot's length, and a split's value axis reads `% within each group` when `% within <Split by label>` would not fit on one line. The legend goes under the plot when the figure is narrower than 7.5 in or the legend is taller than the plot; and a figure grows taller when its labels, legend and notes would leave the plot less than 110 pt (or 40 % of the height asked) — it keeps its width.

#### Properties

In addition to base properties:

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `column` | `str` | `""` | Variable to plot on the X-axis (or Y-axis if horizontal). |
| `by` | `str \| None` | `None` | If specified, plots grouped means of `column` across categories of `by`. |
| `horizontal` | `bool` | `False` | If `True`, draws horizontal bars. |
| `show_values` | `bool` | `True` | If `True`, annotates bars with their numeric values (percentages as `45.2%`). A value is written where it fits — beside a bar's end, or inside its segment of a stack — and left to the axis where it would not. |
| `show` | `str` | `"count"` | `"count"` or `"percent"` of the respondents who answered (of respondents for a multiple-choice question: the bars add up to more than 100 %). With `by` the bars are means; `show="percent"` with `by` is a `ValueError`. |
| `split` | `str \| None` | `None` | A variable with one answer per respondent: the distribution of `column` within each of its groups — percentages of each group with `show="percent"`, as `CrossTable(pct="col")` gives them. Each group's `n` is written under its name. Not with `by` (a `ValueError`); not a multiple-choice variable. |
| `layout` | `str` | `"grouped"` | With `split`: `"grouped"`, `"stacked"` (each group's total above its bar) or `"stacked_100"` (percentages, each group at 100 %). A multiple-choice `column` is drawn `"grouped"` only. `"histogram"` and `"donut"` are forms of their own (below). |
| `sort` | `str` | `"code"` | `"code"` (codebook order) or `"value"` (largest first: the answer given most overall with `split`, the highest mean with `by`). |
| `top` | `int \| None` | `None` | Only the `top` answers given most (with `split`, overall; the options named most for a multiple-choice question); of two given as often the first in code order. The note: `The 5 answers given most of 24 are drawn; the other 19 are left out.` (`… Other combines the other 19.`). Not with `by`, nor a histogram; a `ValueError` below 1. |
| `other` | `bool` | `False` | With `top`: the rest as one grey bar (series), last — `Other`, or `Other (combined)` when an answer drawn is called Other; for a multiple-choice question the respondents who named any of the rest (`… Other is the respondents who named any of the other 3.`). A `ValueError` without `top`. |
| `intervals` | `bool` | `False` | Error bars (whiskers with caps, dark grey) on bars side by side: a percentage's Wilson interval (`siamang.data.intervals.share_interval`: on Kish's effective base when weighted; each group's own base with `split`), a mean's `mean_interval` (Student's t; weighted, the linearization interval — the Group means chart's). The value is written past the whisker. Note: `Error bars: 95 % confidence intervals (Wilson score[, on Kish's effective base]).` / `… of the mean (Student's t).` / `(weighted: the linearization interval, as the Group means chart draws it).`, and `No interval for a group of one answer: …`. On counts: `Confidence intervals are drawn for percentages and for means by group; counts have none.` A stacked layout, a histogram or a donut is a `ValueError`. |
| `confidence` | `float` | `0.95` | The intervals' level, between 0 and 1. |
| `letters` | `bool` | `False` | With `split`, `show="percent"` and `layout="grouped"` (else a `ValueError`): each group labelled with the Banner table's letter for its column (`North (A)`: letters in `tables.banner_values` order — the codebook's — over the split variable's values in the data, `tables.column_letter`), and in bold after each bar's value the letters of the groups whose share of that answer is significantly lower: `tables.proportion_letters`, the Banner table's two-sided z-test of column proportions with the pooled variance, on each group's respondents who answered (Kish's effective base when weighted); a group below 30 is not tested. The Tab book's letters for the same question and banner. Notes: `A letter over a bar names a group (its letter is under its name) whose share of that answer is significantly lower (two-sided z-test of column proportions, p < 0.05[, Bonferroni-corrected][, on Kish's effective base]) — the Banner table's and the Tab book's letters.`, `Not tested, fewer than 30 respondents who answered: West (D).`, `No letters: fewer than two groups have 30 respondents who answered, the least a group is tested on.`, `No group's share of any answer is significantly higher than another's.`, and when the bars are too narrow for their letters `The bars are too narrow to carry their significance letters: the Banner table and the Tab book show them.` |
| `level` | `float` | `0.05` | The letters' significance level, between 0 and 1. |
| `correction` | `str` | `"none"` | `"none"` or `"bonferroni"` (the level divided by the number of pairs of tested groups). |
| `bins` | `str \| int \| list` | `"auto"` | `layout="histogram"`: `"auto"`/`None`/`""` — Freedman–Diaconis (`numpy.histogram_bin_edges(x, "fd")`; Sturges' when the IQR is 0; whole-number answers a whole width, at least 1, edges at half-numbers from the lowest); a whole number 1–100 (text or int) — equal bins over the range; two numbers or more (list, or text separated by commas, semicolons or spaces) — increasing edges, the last bin closed. Else a `ValueError` naming what Bins takes (`siamang.reporting.bars.parse_bins`). At most 100 bins (an automatic width that gives more is widened). |
| `min_slice` | `float` | `3.0` | `layout="donut"`: slices below this percentage are combined as Other when two or more are (0–100). |

**Histogram** (`layout="histogram"`, `siamang.reporting.bars.render_histogram`): the bars span their bins (white edges), counts (`Count` / `Weighted count`) or with `show="percent"` percent of the respondents who answered (`% of respondents[ (weighted)]`), the x axis thousands-separated and, for edges given, ticked at them (up to 25). With `split` (at most `MAX_PANELS` = 12 groups): one panel per group, sharing the bins (x) and the scale (y), in one column up to four groups and two past, each titled `North (n = 97)` at its left, the value axis `Count` / `Weighted count` / `% of the group` on the first column, the title over them all; the figure grows until every panel, as laid out under its wrapped title, is at least 72 pt tall; the shared x axis is thinned until its labels keep half an em apart (a histogram's edges keep every second, third … one). Notes: `Bins: 18 of width 4 (Freedman–Diaconis), each holding 4 whole numbers.` (`… 33 of width 7,090 (Freedman–Diaconis)`, `… 12 of equal width`, `… the edges given; each bin holds its left edge, the last its right edge too`, `; the width is of the answers as they are, the heights weighted`), `The bins differ in width: a bar's height is its count, not its density.`, `12 answers outside the bins (below 18 or above 65) not drawn[, but in the base].` Refused: a nominal or ordinal variable (`A histogram draws the distribution of a number, and Region is nominal: draw its answers as bars (layout='grouped').`), a multiple-choice one, an answer that is not a number, `by`, `top`, intervals or letters, more than 12 groups.

**Donut** (`layout="donut"`, `render_donut`): a ring 0.38 of the radius wide, slices clockwise from 12 o'clock in `sort` order with Other (grey) last, white edges; each percentage (9 pt, `45.2%`) on its slice when its box fits inside the slice's ring both ways, else in a column beside the ring on the slice's side, joined to it by a line that leaves the ring outwards first, the labels of a side a line apart (`show_values=False`: none). In the hole: the respondents who answered (bold, sized to the hole), `respondents`, and on weighted data `weighted 1,498`. The legend names the slices beside the donut (a figure at least 7.5 in wide whose legend is no taller than the plot can be) or under it. A donut's plot is at least 55 % of the height asked. Notes: `The 6 answers given most of 24 have slices of their own; Other combines the other 18 — a donut's slices make a whole.`, `Other [also ]combines 4 answers under 3 % each: A, B, C and D.`, `Nobody answered Poor.` Refused: `split` (`… layout='stacked_100' shows the answers within each group.`), `by`, a multiple-choice question (`… its shares add up to more than 100 % and are not the parts of a whole: draw them as bars (layout='grouped').`), intervals or letters, and a donut every answer of which is under `min_slice` (`Each of the 40 answers to Forty drawn is under 3 % of the respondents who answered, so Other would fill the whole ring: draw them as bars (layout='grouped'), or lower min_slice.`).

#### Example

```python
from siamang.reporting import BarChart

# 1. Simple frequency bar chart
chart = BarChart(data, column="it_role")
chart.show()

# 2. Grouped mean bar chart
chart = BarChart(data, column="autonomy", by="remote_freq", palette="pastel")
chart.save("autonomy_means.png")

# 3. Percentages, largest first
BarChart(data, column="it_role", show="percent", sort="value", horizontal=True)

# 4. The chart of a crosstab: satisfaction within each region, stacked to 100 %
BarChart(data, column="satisfaction", split="region", layout="stacked_100")

# 5. The ten answers given most, the rest as Other, with their intervals
BarChart(data, column="it_role", show="percent", top=10, other=True, intervals=True)

# 6. The Banner table's significance letters over the bars
BarChart(data, column="satisfaction", split="region", show="percent", letters=True)

# 7. A histogram per region, and a donut
BarChart(data, column="age", layout="histogram", bins="18, 25, 35, 50, 65", split="region")
BarChart(data, column="it_role", layout="donut", min_slice=5)
```

---

### Distribution Comparison: `BoxPlot`

Compares the distribution of an interval/ratio variable across groups [1]. Unweighted; on weighted data the title says so.

#### Properties

In addition to base properties:

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `column` | `str` | `""` | Continuous dependent variable (Y-axis). |
| `by` | `str` | `""` | Categorical grouping variable (X-axis). |
| `show_points` | `bool` | `False` | If `True`, overlays individual data points (jittered strip plot) on top of boxes. |

#### Example

```python
from siamang.reporting import BoxPlot

chart = BoxPlot(data, column="satisfaction", by="remote_freq", show_points=True)
chart.show()
```

---

### Matrix / Correlation: `HeatMap`

Plots a correlation matrix of continuous variables or a mean matrix of a set of Likert items grouped by a category [1] [3]. On weighted data the means are weighted, and so is the Pearson correlation matrix; the Spearman and Kendall matrices are not, and their title says so.

#### Properties

In addition to base properties:

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `columns` | `list[str]` | `[]` | List of variables to include in the matrix. |
| `by` | `str \| None` | `None` | If specified, plots grouped means of `columns` across categories of `by`. If `None`, plots a correlation matrix of `columns` by `method`, over the respondents who answered every one of them. |
| `annot` | `bool` | `True` | If `True`, writes the data value in each cell. |
| `cmap` | `str` | `"YlOrRd"` | Matplotlib colormap name (grouped-means mode only), or `"theme"`: the report theme's sequential colour for means and its diverging pair for a correlation matrix, with its text colour, grid and face (§1b). |
| `vmin` | `float \| None` | `None` | Minimum value anchor for the colormap (grouped-means mode only). |
| `vmax` | `float \| None` | `None` | Maximum value anchor for the colormap (grouped-means mode only). |
| `method` | `str` | `"spearman"` | The correlation without `by`. `"spearman"` is drawn as it always was: unweighted, the answers read as they are (a missing code counts as an answer). `"pearson"` and `"kendall"` (tau-b) are drawn by `siamang.reporting.correlation_chart` from `inference.correlation_matrix(..., missing="listwise")` — the Correlation matrix table's numbers: the codebook's missing codes are left out, and the note under the plot gives N, the weight and the missing codes left out. Pearson is weighted on weighted data (colour bar `Weighted Pearson r`, `weight_note` `"weighted by 'w'"`); Kendall adds the unweighted line to its title. A pair that cannot be computed is a blank cell, named under the plot as the chart names its items (`Not computed (a blank cell): Trust × Constant: …`, or `1 × 3` when numbered); an item with the same answer from everyone has a blank diagonal too. Labels longer than 14 characters are numbered: rows `1. label`, columns `1`, `2`, …; the rows' labels are tried at 10 pt in a third of the width down to 8 pt in a half, the first whose rows fit the height grown by at most 60 %, and the plot is made tall enough for every row's wrapped label. The coefficients are written at the size their cells hold (at most 10 pt, "-0.03" in a cell); below 6 pt they are left out and the note says `The cells are too small to hold their coefficients: see the table.`; no gridlines cross the cells. Any other value is a `ValueError`. |

> **Note:** In correlation mode (`by=None`) the matrix is always drawn on a diverging `RdBu_r` scale centered at 0 over the range `[-1, 1]` (the theme's diverging pair with `cmap="theme"`); otherwise the `cmap`, `vmin`, and `vmax` properties are ignored. To restyle a correlation heatmap, work with the `matplotlib` Axes returned by `plot()`.

#### Example

```python
from siamang.reporting import HeatMap

# 1. Plot mean agreement for a set of matrix variables across remote frequency
chart = HeatMap(
    data,
    columns=["surv_keystroke", "surv_camera", "surv_git"],
    by="remote_freq",
    cmap="Blues"
)
chart.show()

# 2. Correlation matrix of all numerical variables
#    (always rendered on a fixed RdBu_r scale over [-1, 1], centered at 0)
corr_chart = HeatMap(
    data,
    columns=["age", "experience", "satisfaction", "autonomy"],
    by=None,
)
corr_chart.show()
```

---

### Battery of Items: `LikertChart`

Diverging stacked bars of items that share one ordered scale (`siamang.reporting.likert`): each item's answers below the middle of the scale stack left of a centre line, those above it right; the top-2 and bottom-2 shares (one answer each on a scale of two or three: "Top box") are written at the ends of every bar, under the headers `Bottom-2` and `Top-2`. On weighted data the shares are sums of weights (`weight_note` `"weighted by 'w'"`), `n` counts respondents.

#### Properties

In addition to base properties:

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `columns` | `list[str]` | `[]` | The items. Their scale is the codebook's: the value labels without the missing codes, the same for every item (compared by code and by label, case and spaces aside), else a `ValueError` naming two of them and their scales. An item without labels may give a `valid_range` of 2–11 whole numbers, or be asked by a `LikertScale` question of the data's questionnaire (its points, the ends named by its left and right labels). A multiple-choice item is refused. |
| `neutral` | `str` | `"split"` | `"split"`: an odd scale's middle answer half on either side of the centre. `"side"`: drawn apart, in a panel at the right titled by its label. An even scale has none; its centre falls between the middle two answers. |
| `sort` | `str` | `"top2"` | `"top2"`: the largest top-2 share first (ties: the smaller bottom-2, then the order given). `"listed"`: the order of `columns`. |
| `show_values` | `bool` | `True` | Each answer's share (`23%`) inside its segment where it fits. |
| `palette` | `str` | `"RdBu"` | A diverging palette; the neutral answer is grey (`#bdbdbd`). An even scale of four or more answers samples it two wider and drops the two middle (palest) colours. `"theme"`: the report theme's diverging pair, the low answers in its first colour. |
| `table` | `pd.DataFrame` | — | Read-only: the numbers drawn, in chart order — `Item`, one column per answer (%), `Top-2`, `Bottom-2` (or `Top box`, `Bottom box`), `N`, and `Weighted N` on weighted data. |

The title, when not given, is the words every item label starts with up to a separator (`: `, ` - `, ` – `, ` — `, `? `), and the rest of each label names its bar; without such a stem it is `"<n> items from <lowest label> to <highest label>"`, and one item's title is its label (its bar's row then reads `(n = …)`). The items' labels are tried at 11 pt in 0.3 of the width down to 8 pt in 0.45, the first whose rows fit the height grown by at most 60 %; a row is at most 60 pt tall, so few items make a shorter figure. The centre line runs behind the values, and the neutral answer's value has a grey box it hides behind. The note under the chart gives the base, the answers in the top-2 and bottom-2, the neutral answer's handling (`The neutral answer (3 = Neither) is split around the centre.` / `… is drawn apart, at the right.` / `No neutral answer: the centre falls between 2 = Fair and 3 = Good.`), the weight, `Left out as missing: …` for the codebook's missing codes, `Not on the scale, left out: …` for other values, and `No answer on the scale, not drawn: …` for an item nobody answered.

#### Example

```python
from siamang.reporting import LikertChart

chart = LikertChart(data, columns=["trust_acme", "trust_globex"], neutral="side")
chart.save("trust.png")
chart.table
```

---

### Bivariate Relationship: `ScatterPlot`

Plots the relationship between two continuous variables, with optional grouping (color) and a linear trendline. Unweighted — every respondent is one point and the trendline is an unweighted fit; on weighted data the title says so.

#### Properties

In addition to base properties:

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `x` | `str` | `""` | Independent variable (X-axis). |
| `y` | `str` | `""` | Dependent variable (Y-axis). |
| `hue` | `str \| None` | `None` | Optional categorical variable to group points by color. |
| `trendline` | `bool` | `True` | If `True`, adds a linear regression trendline. |

#### Example

```python
from siamang.reporting import ScatterPlot

chart = ScatterPlot(data, x="autonomy", y="satisfaction", hue="remote_freq")
chart.show()
```

---

## 3. Integration with `SurveyData` Accessors

To make this reporting API extremely convenient, two accessors are attached directly to the `SurveyData` class:

* **`data.report`**: Accessor for generating tables (`ReportAccessor`).
* **`data.plot`**: Accessor for generating charts (`PlotAccessor`).

### `data.report` Accessor Methods

* **`freq(column: str, *, exclude_missing: bool = True, sort: str = "value") -> FreqTable`**:
  Creates a `FreqTable` instance.
* **`crosstab(row: str, col: str, *, pct: str = "none", test: bool = True, method: str = "chi2") -> CrossTable`**:
  Creates a `CrossTable` instance.
* **`means(column: str, *, by: str, test: bool = True, method: str = "auto", posthoc: str = "none", adjust: str = "holm") -> GroupMeanTable`**:
  Creates a `GroupMeanTable` instance.
* **`ttest(column: str, *, kind: str = "independent", by: str | None = None, groups: list | None = None, other: str | None = None, mu: float = 0.0, variances: str = "welch", confidence: float = 0.95) -> TTestTable`**:
  Creates a `TTestTable` instance.
* **`correlation_matrix(columns: list[str], *, method: str = "spearman", missing: str = "pairwise", adjust: str = "none", layout: str = "matrix") -> CorrelationMatrixTable`**:
  Creates a `CorrelationMatrixTable` instance.
* **`maxdiff(question, *, method: str = "both") -> MaxDiffTable`**, **`conjoint(question) -> ConjointTable`**:
  One row per item (counting score, utility, share) or per level (part-worth, importance). On weighted data every column is weighted — the utilities and part-worths come from a conditional logit on the weighted choices — and `stats` carries `Weight` and a base of `N respondents (W weighted)`.
* **`conjoint_shares(question, products, *, include_none: bool = False) -> ShareTable`**:
  What the part-worths predict a market of `products` would do: the rows of `siamang.data.conjoint.shares` (`product`, `utility`, `share`), with the base, the model, a note that these are shares of the listed products, and on weighted data the `Weight`, in `stats`.
* **`quality(column: str = "quality_flags")`**, **`themes(codeframe, *, sentiment: bool = False)`**:
  Count responses and coded answers; on weighted data `stats["Weight"]` reads `unweighted (the weight '<column>' is not applied)`. The theme table's rows are shares of the coded answers, then `Coded` and `Uncoded` as shares of all answers; its stats add `Coverage` and `Distinct uncoded answers`, and with `sentiment` (and a codeframe that has it) `Negative %` / `Neutral %` / `Positive %` columns and the `Sentiment` and `Net sentiment` stats — `Sentiment: not in this codeframe` otherwise.
* **`descriptives(columns: list[str], *, by: str | None = None, detail: bool = False) -> DescriptivesTable`**:
  N, Missing, Mean, SD, Min, Median, Max per variable (and group), with Q1, Q3, skewness and kurtosis under `detail`. Missing codes are not answers; on weighted data the mean, SD, median and quartiles are weighted beside a `Weighted N` column and `stats` gives `Effective N` and `Design effect`. Undefined cells print blank (`siamang.reporting.summaries`).
* **`data_check(variables: list[str] | None = None) -> DataCheckTable`**:
  `validate()` as a table with the rows and example values of each problem (`siamang.data.checks.check`).
* **`banner(rows: list[str], columns: list[str], *, weight: str | None = None, test: bool = True, level: float = 0.05, correction: str = "none") -> BannerTable`**:
  The cross-break: the questions in `rows` down the page, a block of columns per
  variable in `columns`, and a base row. Each cell is a column percentage with
  its count and, unless `test` is off, the letters of the columns it is
  significantly higher than.

  Columns are compared **only within a banner variable** — its values are
  mutually exclusive groups of the same people, which is what a z-test of two
  proportions assumes; columns belonging to different banner variables overlap,
  so the table does not compare them. On weighted data the test uses Kish's
  effective base, because weights make a sample behave like a smaller one, and a
  column with fewer than thirty respondents takes no part at all. The test, its
  level, the correction (`"none"` or `"bonferroni"`), any untested columns and
  the kind of base are all reported in `stats`.

  `data.tables.banner(...)` returns the same numbers in tidy form — one row per
  pair of values — for feeding to something else.

  The test is `siamang.reporting.tables.proportion_letters(shares, bases,
  letters, *, level=0.05, correction="none", min_base=30)` — each column's
  share (0–1) and the base the test uses, keyed alike, and each column's letter;
  it returns the letters each column beats — with the columns' order
  `banner_values(series, labels)` (the codebook's labelled values present, then
  the others by their text) and `column_letter(index)` (A–Z, then `#27` …). The
  Tab book and the Bar chart's significance letters (`letters=True`) call the
  same functions.

### `data.plot` Accessor Methods

* **`bar(column: str, *, by: str | None = None, horizontal: bool = False, show_values: bool = True, figsize: tuple[float, float] = (10, 6), palette: str = "muted", title: str | None = None, show: str = "count", split: str | None = None, layout: str = "grouped", sort: str = "code", top: int | None = None, other: bool = False, intervals: bool = False, confidence: float = 0.95, letters: bool = False, level: float = 0.05, correction: str = "none", bins: str | int | list[float] = "auto", min_slice: float = 3.0) -> BarChart`**:
  Creates a `BarChart` instance.
* **`boxplot(column: str, *, by: str, show_points: bool = False, figsize: tuple[float, float] = (10, 6), palette: str = "muted", title: str | None = None) -> BoxPlot`**:
  Creates a `BoxPlot` instance.
* **`heatmap(columns: list[str], *, by: str | None = None, annot: bool = True, cmap: str = "YlOrRd", vmin: float | None = None, vmax: float | None = None, figsize: tuple[float, float] = (10, 6), title: str | None = None, method: str = "spearman") -> HeatMap`**:
  Creates a `HeatMap` instance.
* **`scatter(x: str, y: str, *, hue: str | None = None, trendline: bool = True, figsize: tuple[float, float] = (10, 6), palette: str = "muted", title: str | None = None) -> ScatterPlot`**:
  Creates a `ScatterPlot` instance.
* **`likert(columns: list[str], *, neutral: str = "split", sort: str = "top2", show_values: bool = True, figsize: tuple[float, float] = (10, 6), palette: str = "RdBu", title: str | None = None) -> LikertChart`**:
  Creates a `LikertChart` instance.

### Example

```python
# Create a CrossTable and print as markdown
print(data.report.crosstab("it_role", "remote_freq", pct="row").to_markdown())

# Plot and save a boxplot comparing autonomy by remote frequency
data.plot.boxplot("autonomy", by="remote_freq", show_points=True).save("autonomy_by_remote.png")
```

---

## 4. Charts of results: `result_charts`

`siamang.reporting.result_charts` draws what an analysis already computed —
the `visualize.result_chart` node (Result chart) of a flow. `data.plot` draws
from the data; a result chart draws the result's own numbers, so the picture
beside a table shows that table.

```python
from siamang.reporting import result_charts

result_charts.chart(data.report.means("satisfaction", by="region", method="anova", posthoc="tukey"))
result_charts.chart([pca.variance, pca.stats], kind="scree", title="Scree plot").save("scree.png")
```

**`chart(results, kind="auto", *, title=None, figsize=(10, 6), palette="muted", dpi=150) -> ResultChart`**
takes one result or a list of them (what a flow connects to the node's many
input: a table, and its stat beside it). The first result a renderer draws is
drawn — with `kind`, the first that can be drawn as it — and the others lend it
what they say: the weight, a regression's base. A bare DataFrame's weight is read
from `frame.attrs["weight"]`, which a regression's, a PCA's, a cluster's and
TURF's tables carry. The chart is built at once, so a
result it cannot draw raises `ResultChartError` (a `ValueError`) with what it
draws instead: `A Result chart cannot draw a FreqTable (Value, Label, N, %, …).
It draws the results of Group means, Descriptive statistics, t-test, Paired
tests, Proportion CI, Net Promoter Score, TURF, MaxDiff, Conjoint, Share of
preference, Principal components, Factor analysis, Cluster (k-means),
Regression, Correlation matrix, Code open answers, Key drivers, Perceptual map,
Price sensitivity — connect the table of one of them.`, `Kind 'scree' does not suit this result: Group means draws 'means' or
'means_sd'.`, `Unknown kind 'pie'; the kinds are auto, means, …`. `ResultChart`
is a `SurveyChart`: `save()`, `plot()`, `show()`, `weight_note`, and a `Report`
takes it like any chart; `chart.drawn` is the kind `auto` resolved to.

| Result | Kinds (the first is `auto`) | What is drawn |
| :--- | :--- | :--- |
| `GroupMeanTable` (Group means) | `means`, `means_sd` | each group's mean with its 95 % confidence interval (or ± 1 SD), each row labelled with its base (`North (n = 97)`); with a post-hoc test, the compact letter display — means sharing a letter do not differ at p < .05 (Piepho's insert-and-absorb, as R's `multcompView`; `letters(groups, different)`) |
| `DescriptivesTable` | `means`, `means_sd` | each variable's mean with its base (`(n = …)`), one coloured series per group with `by`, the legend giving each group's base (`n = 90–97` when the variables' differ); variables whose means reach more than `SCALE_RATIO` (5) times one another's (an income and an age) take a panel each, on a scale of their own, a row per group named with its base, titled `Means by Region, each variable on its own scale` |
| `TTestTable` (t-test) | `means`, `means_sd` | each group's or measurement's mean with its interval at the test's confidence, its row labelled with its base; a one-sample test draws its test value as a line; the test's difference and CI in a note |
| Paired tests' `table` (Wilcoxon, Friedman) | `means`, `means_sd` | each measurement's mean (the row of differences is the test's) |
| McNemar's and Cochran's Q's `table` | `shares` | the share saying yes to each, with Wilson's interval; the test's p in a note |
| Proportion CI's stat | `interval` | the share as a number over its interval on a 0–100 % track, with the base (the effective base when weighted) |
| `NpsTable` | `stacked` | detractors, passives and promoters in one 100 % bar, the score and its 95 % CI above it |
| `TurfTable` of a search | `reach` | reach by portfolio size, each point labelled with its gain, and under it the option that size adds (`+ label`, by the table's `labels`); a best portfolio that is not the one before plus an option reads `a new set` and is listed in full in a note |
| `TurfTable` of a fixed portfolio | `items` | each option's reach and what it reaches alone, the portfolio's reach as a line |
| `MaxDiffTable` | `utilities`, `scores`, `shares` (a counting table: `scores`) | utilities with their 95 % Wald intervals against the reference item (the standard errors are the fit's: `maxdiff.utilities`), the counting scores, or the shares; the base in a note |
| `ConjointTable` | `importance`, `partworths` | each attribute's importance; every level's part-worth, coloured by attribute, each attribute's levels in the design's order (the table sorts them by worth); the base in a note |
| `ShareTable` (Share of preference) | `shares` | each product's share |
| PCA `variance` / `loadings`, `PcaResult` | `scree` / `loadings` | eigenvalues with the Kaiser line at 1 (the components kept filled, when the stat says how many); a diverging heatmap of the loadings |
| Factor analysis `variance` / `loadings`, `FactorAnalysis` | `scree` / `loadings` | the same, with parallel analysis's random 95th percentile when it chose the number; loadings hidden in the table are blank |
| Cluster centroids, `ClusterAssignment`, `ClusterResult` | `profile` | a snake plot: each cluster's means down the items (by label: the centroids carry `attrs["labels"]`, as a PCA's loadings do), sized in the legend |
| Regression `table`, `RegressionResult` | `coefficients` | a forest of the coefficients with 95 % intervals, the intercept left out, the terms and the outcome by label (`table.attrs["labels"]`) — t with n − k df when the stat gives n (normal otherwise, and it says so); a note gives N and each nominal predictor's reference level (`compared with Region = North`, from `table.attrs["reference"]`); a logit's odds ratios on a log scale; the ordinal logit's odds ratios with the table's Wald intervals, its thresholds left out and a note saying which way the answers run |
| `CorrelationMatrixTable` | `heatmap` | the lower triangle with the table's significance marks (on the adjusted p when adjusted), N in a note |
| `ThemeTable` (Code open answers) | `shares`, `sentiment` | each theme's share of the coded answers and the coverage; the negative / neutral / positive split; titled by the question's label |
| `DriverTable`, `KeyDrivers` (Key drivers) | `importance` | `drivers.plot`: each driver's share of R², largest first, a negative beta in the second colour |
| `MapTable` (any of a Perceptual map's tables), `PerceptualMap` | `map` | `correspondence.plot`: the symmetric map of the first two dimensions; a map whose labels would overlap on the figure asked for is drawn taller (a fifth at a time, up to 1.2 × its width), and one still crowded numbers its points and lists their names under it (`numbered=True`) |
| `PriceTable` (`table` or `curves`), `PriceSensitivity` | `curves` | `pricing.plot`: Van Westendorp's four curves, points and acceptable range (with the NMS trial curve below), or Gabor-Granger's demand over revenue; a chart of two panels is at least 6 inches tall |

**Weight.** A chart follows the weight of the result it draws: the note the
result (or a stat beside it) carries is the second line of the title and
`weight_note` — `weighted by 'w'` for a weight column, or the result's own
`unweighted (the weight 'w' is not applied)`. The intervals of weighted means
are the linearization ones (`siamang.data.intervals`).

**Legibility.** Categories are rows, the first at the top: labels are wrapped at
a third of the width, whole, and many rows get a smaller font (10 pt down to 7,
three lines, four at 8 pt); a chart whose rows its height cannot hold so grows
taller at 9 or 8 pt rather than cut a label. Only a label longer than four lines
of 8 pt is cut, with an ellipsis, and never so that two labels read alike. A
chart of few rows is shorter than the height it was given. The title (from the
plot's left edge), the axis titles and the notes under the plot are wrapped to
the plot as it is laid out, so nothing runs past the figure and the PNG is the
width asked for. Value labels sit beside their bar or whisker and the axis widens until
they fit; legends sit between the title and the plot. NPS and sentiment keep a
red–grey–blue of their own and the heatmaps a diverging scale centred on 0; the
palette colours everything else. With `palette="theme"` every colour is the
report theme's (§1b): the series, the diverging pair for the red–grey–blue and
the heatmaps, the text, the grid and the face — Key drivers, the Perceptual map
and Price sensitivity included, in its first two colours.

**Registry.** A later analysis adds its result with
`register(result_type, kinds, fn, *, accepts=None, name=None)` — `fn(result,
chart)` draws on the figure it asks `chart` for (`chart.figure()`, or
`chart.rows(labels)` for one row per category, `chart.colors(n)`,
`chart.legend(ax)`, `chart.make_room(ax, labels)`), reads `chart.drawn` and
`chart.stats`, and returns the title; `accepts(result)` tells apart results of
one class (a regression's coefficients and a PCA's loadings are both
DataFrames); the last registration that accepts a result wins — and with
`register_output(node_type, port, kinds)` (kinds a tuple, or a function of the
node's parameters) tells `check_flow` what its output draws. A new kind is also
a value of the node's `kind` enum. An analysis with a chart of its own draws it
whole and hands the figure over with `chart.adopt(fig)`: its title (the Title
given replaces its first line), weight line, colours and labels are kept as
drawn, and the chart does not lay it out again. The later analyses' renderers
are in `siamang.reporting.method_charts`: Key drivers, the Perceptual map and
Price sensitivity through their modules' `plot`, Cochran's Q and the ordinal
logit as above.

---

## 5. Trend and tab book

### `data.plot.trend(...)` → `TrendChart` (`siamang.reporting.trend`)

* **`trend(time: str, *, period: str = "month", measure: str = "percent", variable: str | None = None, codes=None, by: str | None = None, band: bool = True, min_base: int = 30, figsize=(10, 6), palette: str = "muted", title: str | None = None) -> TrendChart`**:
  A measure over waves or dates, one line per group of `by`. `time` is a wave
  code (one point per code, ordered by code, value labels on the axis) or a
  date — `datetime64`, or ISO 8601 text such as a platform snapshot's
  `created_at` — read in UTC and grouped by `period` (`day`, ISO `week`
  Monday to Sunday labelled `2026-W22`, `month`, `quarter`, `year`), every
  period between the first and the last on the axis. `measure` is
  `"percent"` choosing `codes` of `variable` (any of them for a
  multiple-choice question), its `"mean"`, or the `"count"` of respondents.
  Weighted data gives weighted points; the band is the 95 % interval
  (a percent's Wilson score interval, as `intervals.share_interval` gives the
  Bar chart's, or the t interval of the mean, on Kish's effective base when
  weighted), drawn for up to `MAX_BANDS` (4) lines — past that the notes say
  the table gives each point's interval. A percent or a mean with fewer than
  `min_base` respondents is drawn hollow and without its band (the table gives
  it), and the value axis fits the points and the bands drawn; a point at 0 %
  or 100 % is drawn whole on the frame. A count is its own base. A multiple-choice question as `time` or `by` is refused
  (`ValueError`, in a sentence), as are a mean of a nominal or multiple-choice
  variable and a missing code among `codes`.

  The chart follows `siamang.reporting.chart_parts` as the Bar chart's newer
  forms do: `series_colours` (no two lines alike), `percent_axis` (whole
  percents) or `thousands_axis` (a count or a mean), period labels level —
  wrapped to the measured room between two ticks — or slanted at 40° in as
  many lines as fit (every n-th period named only when they must be thinned),
  the title and axis titles wrapped to the plot, the legend beside the plot
  or under it (`legend_below`) on a figure narrower than 7.5 inches or when it
  is taller than the plot, and a `Footnote` under it: `Base: … respondents who
  answered (weighted: …); … to … per point.`, `Gaps: …`, `Hollow points: fewer
  than 30 respondents, drawn without a band (the table gives their
  intervals).`, `Band(s): 95% confidence interval(s).` or `No bands:
  …`, `Not drawn: … whose respondents' weights sum to 0.`, `Weighted by 'w';
  the bases count respondents.`, `Left out as missing: …`, `Left out: …`. A
  figure too small for its labels grows taller.
* **`TrendChart.table`** — a `ResultTable` of period × group: the measure,
  `Lower 95%`, `Upper 95%`, `Base`, and on weighted data `Weighted base` and
  `Effective base`, and — for a percent or a mean — `Note` (`base below 30`,
  `no respondents`, `their weights sum to 0`). Its
  `stats`: `Measure`, `Base`, `Time`, `Interval`, `Weight`, `Low base`,
  `Missing codes left out`, `Left out` (rows without a time, or whose text is
  not a date, or without a group). **`TrendChart.points`** is the same,
  unrounded (`trend(data, time, …)` computes it without a chart).

### `write_tabbook(...)` (`siamang.reporting.tabbook`)

* **`write_tabbook(data, path, *, banner: list[str], questions: list[str] | None = None, percentages: str = "column", counts: bool = True, letters: bool = True, level: float = 0.05, correction: str = "none", means: bool = True, min_base: int = 30, created: datetime | None = None) -> dict`**:
  An `.xlsx` workbook: `Contents` (a link per question, and what was not
  tabulated, with why), one sheet per question — Total and every code of each
  banner variable across; the base (unweighted, and weighted); counts and
  column (`"column"`) or row (`"row"`) percentages; the Banner table's letters
  in their own cells beside the column percentages (with `"row"` or `"none"`
  there are none: they compare column percentages); the mean and SD of an
  interval or ratio question — and
  `Notes` (weight, test, alpha, Bonferroni, minimum base, missing codes left
  out, `created`). Counts come from `siamang.data.tables._banner_pair` and
  the letters from `BannerTable`'s test; the codebook's missing codes are left
  out, and a column's base is those in it who answered. On weighted data a
  cell holds the sum of weights and a percentage is of those sums, as
  `FreqTable` and `CrossTable` compute it; weighted counts and bases are
  formatted `#,##0.0` (`WEIGHTED_FORMAT`), the unweighted base `#,##0`. Text
  that begins with `=` stays text (`siamang.io.excel_text.as_text`) and the
  links quote their sheet (`siamang.io.excel_text.sheet_link`). Returns the
  stat (`Sheets written`, `Questions skipped`, `Skipped`, …).
* **`tabulate(data, *, banner, …) -> TabBook`** — the same numbers without the
  workbook: a `QuestionTab` per question (`answers`, `columns`, `base`,
  `weighted_base`, `effective_base`, `counts`, `column_percent`,
  `row_percent`, `letters`, `means`, `left_out`) and `skipped`.

---

## References

1. Agresti, Alan. *An Introduction to Categorical Data Analysis*. Wiley, 3rd edition, 2018.
2. McKinney, Wes. *Python for Data Analysis: Data Wrangling with pandas, NumPy, and Jupyter*. O'Reilly Media, 3rd edition, 2022.
3. Wickham, Hadley. *ggplot2: Elegant Graphics for Data Analysis*. Springer, 2nd edition, 2016.
