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
| `test` | `bool` | `True` | If `True`, automatically runs a Chi-square test of independence and appends a footer with $\chi^2$, $df$, $p$-value, and Cramér's V [1] [3]. |

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
| `test` | `bool` | `True` | If `True`, automatically runs a significance test: ANOVA, t-test, Kruskal-Wallis, or Mann-Whitney U [1] [3]. |

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
```

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
| `custom_css` | CSS | appended last, so it wins — and checked by nothing |

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
| `palette` | `str` | `"muted"` | Seaborn color palette name (e.g., `"muted"`, `"deep"`, `"pastel"`, `"colorblind"`). |
| `title` | `str \| None` | `None` | Optional chart title. If `None`, automatically generated from variable labels. |

#### Methods

* **`plot() -> plt.Axes`**:
  Builds and returns the matplotlib Axes object.
* **`show() -> None`**:
  Displays the plot inline (ideal for Jupyter notebooks).
* **`save(path: str | Path, dpi: int = 150) -> Path`**:
  Saves the plot to a file (`bbox_inches="tight"`). The destination directory must already exist.

---

### Categorical Distribution: `BarChart`

Plots frequencies or percentages of categorical variables, or mean values of continuous variables across groups.

#### Properties

In addition to base properties:

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `column` | `str` | `""` | Variable to plot on the X-axis (or Y-axis if horizontal). |
| `by` | `str \| None` | `None` | If specified, plots grouped means of `column` across categories of `by`. |
| `horizontal` | `bool` | `False` | If `True`, draws horizontal bars. |
| `show_values` | `bool` | `True` | If `True`, annotates bars with their numeric values. |

#### Example

```python
from siamang.reporting import BarChart

# 1. Simple frequency bar chart
chart = BarChart(data, column="it_role")
chart.show()

# 2. Grouped mean bar chart
chart = BarChart(data, column="autonomy", by="remote_freq", palette="pastel")
chart.save("autonomy_means.png")
```

---

### Distribution Comparison: `BoxPlot`

Compares the distribution of an interval/ratio variable across groups [1].

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

Plots a correlation matrix of continuous variables or a mean matrix of a set of Likert items grouped by a category [1] [3].

#### Properties

In addition to base properties:

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `columns` | `list[str]` | `[]` | List of variables to include in the matrix. |
| `by` | `str \| None` | `None` | If specified, plots grouped means of `columns` across categories of `by`. If `None`, plots a Spearman rank correlation matrix of `columns`. |
| `annot` | `bool` | `True` | If `True`, writes the data value in each cell. |
| `cmap` | `str` | `"YlOrRd"` | Matplotlib colormap name (grouped-means mode only). |
| `vmin` | `float \| None` | `None` | Minimum value anchor for the colormap (grouped-means mode only). |
| `vmax` | `float \| None` | `None` | Maximum value anchor for the colormap (grouped-means mode only). |

> **Note:** In correlation mode (`by=None`) the matrix is always drawn on a diverging `RdBu_r` scale centered at 0 over the range `[-1, 1]`; the `cmap`, `vmin`, and `vmax` properties are ignored. To restyle a correlation heatmap, work with the `matplotlib` Axes returned by `plot()`.

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

### Bivariate Relationship: `ScatterPlot`

Plots the relationship between two continuous variables, with optional grouping (color) and a linear trendline.

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
* **`crosstab(row: str, col: str, *, pct: str = "none", test: bool = True) -> CrossTable`**:
  Creates a `CrossTable` instance.
* **`means(column: str, *, by: str, test: bool = True) -> GroupMeanTable`**:
  Creates a `GroupMeanTable` instance.
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

### `data.plot` Accessor Methods

* **`bar(column: str, *, by: str | None = None, horizontal: bool = False, show_values: bool = True, figsize: tuple[float, float] = (10, 6), palette: str = "muted", title: str | None = None) -> BarChart`**:
  Creates a `BarChart` instance.
* **`boxplot(column: str, *, by: str, show_points: bool = False, figsize: tuple[float, float] = (10, 6), palette: str = "muted", title: str | None = None) -> BoxPlot`**:
  Creates a `BoxPlot` instance.
* **`heatmap(columns: list[str], *, by: str | None = None, annot: bool = True, cmap: str = "YlOrRd", vmin: float | None = None, vmax: float | None = None, figsize: tuple[float, float] = (10, 6), title: str | None = None) -> HeatMap`**:
  Creates a `HeatMap` instance.
* **`scatter(x: str, y: str, *, hue: str | None = None, trendline: bool = True, figsize: tuple[float, float] = (10, 6), palette: str = "muted", title: str | None = None) -> ScatterPlot`**:
  Creates a `ScatterPlot` instance.

### Example

```python
# Create a CrossTable and print as markdown
print(data.report.crosstab("it_role", "remote_freq", pct="row").to_markdown())

# Plot and save a boxplot comparing autonomy by remote frequency
data.plot.boxplot("autonomy", by="remote_freq", show_points=True).save("autonomy_by_remote.png")
```

---

## References

1. Agresti, Alan. *An Introduction to Categorical Data Analysis*. Wiley, 3rd edition, 2018.
2. McKinney, Wes. *Python for Data Analysis: Data Wrangling with pandas, NumPy, and Jupyter*. O'Reilly Media, 3rd edition, 2022.
3. Wickham, Hadley. *ggplot2: Elegant Graphics for Data Analysis*. Springer, 2nd edition, 2016.
