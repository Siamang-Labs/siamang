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
  Exports the table directly to an Excel sheet. Creates parent directories if they do not exist.

---

### Univariate Frequencies: `FreqTable`

Generates frequency distributions with absolute counts, percentages, and cumulative percentages.

#### Properties

| Property | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `data` | `SurveyData` | *Required* | The `SurveyData` container. |
| `column` | `str` | `""` | Name of the variable to analyze. |
| `exclude_missing` | `bool` | `True` | If `True`, filters out missing values from the base. |
| `sort` | `str` | `"value"` | Sort order: `"value"` (sort by code value), `"frequency"` (descending count), or `"index"` (sort by value labels). |

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
  Saves the plot to a file. Creates parent directories if needed.

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
| `cmap` | `str` | `"YlOrRd"` | Matplotlib colormap name. |
| `vmin` | `float \| None` | `None` | Minimum value anchor for the colormap. |
| `vmax` | `float \| None` | `None` | Maximum value anchor for the colormap. |

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
corr_chart = HeatMap(
    data,
    columns=["age", "experience", "satisfaction", "autonomy"],
    by=None,
    cmap="coolwarm",
    vmin=-1.0,
    vmax=1.0
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
