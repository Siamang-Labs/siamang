# Reporting Charts

siamang's declarative charts mirror the [[Reporting Tables|Reporting-Tables]]
API: each chart reads variable labels, value labels, and scales from the
attached metadata and produces a publication-ready figure with minimal
configuration. The five chart types are `BarChart`, `BoxPlot`, `HeatMap`,
`LikertChart` and `ScatterPlot`, each also reachable through the fluent
`data.plot` accessor.

```python
from siamang.reporting import BarChart, BoxPlot, HeatMap, LikertChart, ScatterPlot
```

> **Requires the `charts` extra.** Charts depend on matplotlib (and seaborn for
> `HeatMap`/`ScatterPlot`). Install with `pip install "siamang[charts]"`. If
> matplotlib is missing, building any chart raises a friendly
> `ImportError: matplotlib is required for chart generation. Install it with:
> pip install matplotlib`. See [[Installation]].

The examples below assume `data` is the simulated `SurveyData` from
[[Simulation]] / [[Analysis]].

---

## Common interface

All charts subclass `SurveyChart` and share these parameters and methods. The
figure is built lazily on first use.

**Shared parameters**

- **`figsize`** — `(width, height)` in inches, default `(10, 6)`.
- **`palette`** — seaborn palette name, default `"muted"` (e.g. `"deep"`,
  `"pastel"`, `"colorblind"`).
- **`title`** — override the auto-generated title (default `None` → derived from
  variable labels).

**Methods**

| Method | Returns | Notes |
| :--- | :--- | :--- |
| `plot()` | `matplotlib.axes.Axes` | Build and return the Axes for further tweaking. |
| `show()` | `None` | Display inline (Jupyter) or in a window. |
| `save(path, dpi=150)` | `Path` | Write to file (the directory must already exist); `bbox_inches="tight"`. |

**Weighted data.** After `with_weight(...)` a chart never disagrees in silence
with the weighted tables beside it. `BarChart` draws sums of weights (axis
"Weighted count"), weighted percentages ("% of respondents (weighted)") or
weighted means ("Weighted mean …"), and `HeatMap` with `by`
draws weighted means (colour bar "Weighted mean"). `HeatMap` with `method="pearson"` draws weighted
coefficients (colour bar "Weighted Pearson r"), and `LikertChart` weighted
shares ("% of respondents (weighted)"). `BoxPlot`, `ScatterPlot` and
the Spearman or Kendall correlation `HeatMap` have no standard weighted form, so they draw the
respondents as they are and add a second title line, `unweighted (the weight
'w' is not applied)` — under a title you set yourself too. `chart.weight_note`
returns that line (or `"weighted by 'w'"`, or `None` on unweighted data).

---

## `BarChart`

```python
BarChart(data, column="", by=None, horizontal=False, show_values=True,
         show="count", split=None, layout="grouped", sort="code",
         figsize=(10, 6), palette="muted", title=None)
```

With only `column`, plots the **distribution** of a categorical variable. With
`by` set, plots the **mean** of `column` within each category of `by`. With
`split` set, plots the **answers within each group** of a second variable — the
chart of a crosstab.

**Extra parameters**

- **`column`** — variable on the category axis (or whose mean is plotted).
- **`by`** — optional grouping variable; switches to grouped-mean mode.
- **`horizontal`** — draw horizontal bars (default `False`).
- **`show_values`** — annotate each bar with its value (default `True`).
- **`show`** — `"count"` (default) or `"percent"`: the share of the respondents
  who answered. For a multiple-choice question that is the share who named each
  option, so the bars add up to more than 100 %, and the chart says so under
  the plot.
- **`split`** — a second variable (one answer per respondent). Each of its
  groups gets the distribution of `column`, as percentages of the group when
  `show="percent"` — a Crosstab's column percentages — and sums of weights on
  weighted data, like the Crosstab.
- **`layout`** — with `split`: `"grouped"` (bars side by side, the default),
  `"stacked"`, or `"stacked_100"` (each group's bar at 100 %, percentages
  whatever `show` says). A multiple-choice question's options overlap, so they
  are drawn side by side only; stacking them is refused.
- **`sort`** — `"code"` (the codebook's order, the default) or `"value"` (the
  largest bar first; with `split`, the answer given most overall; with `by`,
  the highest mean). A colour belongs to its answer, not to its place, so a
  sorted chart and an unsorted one colour the same answer alike.

At the defaults (`show="count"`, no `split`, `sort="code"`) the chart is the one
it has always been, picture for picture. The newer forms also:

- leave the codebook's missing codes out of the bars (a 99 "Don't know" is not
  an answer) and say how many under the plot;
- write under the plot the base (`Base: 571 respondents who answered
  (weighted: 742.7).`), the weight, and for a split each group's `n` under its
  name;
- draw one colour for a single series, and the steps of an ordered scale
  (ordinal and up) in one hue, light to dark;
- wrap long labels, put the legend under the plot when the figure is too narrow
  for it beside, and let a small figure grow taller rather than squash the
  plot to nothing.

A multiple-choice question is drawn by these forms whatever the parameters (the
older chart could not draw one).

```python
# Frequency of IT roles
data.plot.bar("it_role").show()

# Percent of respondents, largest first, horizontal
data.plot.bar("it_role", show="percent", sort="value", horizontal=True)

# Satisfaction within each region, stacked to 100 %
data.plot.bar("satisfaction", split="region", layout="stacked_100")

# Mean autonomy by remote frequency, saved to disk
data.plot.bar("autonomy", by="remote_freq", palette="pastel").save("autonomy_means.png")
```

`by` and `split` do different things — a mean in each group, the answers in
each group — and cannot both be given; nor can `by` with `show="percent"`.

---

## `BoxPlot`

```python
BoxPlot(data, column="", by="", show_points=False,
        figsize=(10, 6), palette="muted", title=None)
```

Compares the distribution of a continuous variable across categories.

**Extra parameters**

- **`column`** — continuous dependent variable (Y-axis).
- **`by`** — categorical grouping variable (X-axis).
- **`show_points`** — overlay a jittered strip plot of the raw points
  (default `False`).

```python
data.plot.boxplot("autonomy", by="remote_freq", show_points=True).show()
```

---

## `HeatMap`

```python
HeatMap(data, columns=[], by=None, annot=True, cmap="YlOrRd",
        vmin=None, vmax=None, method="spearman", figsize=(10, 6), title=None)
```

With `by` set, plots a matrix of **group means** (each of `columns` averaged
within categories of `by`). With `by=None`, plots a **correlation matrix** of
`columns` over the respondents who answered every one of them (using a
diverging `RdBu_r` scale centered at 0) — Spearman's by default.

**Extra parameters**

- **`columns`** — list of variables in the matrix.
- **`by`** — grouping variable for means; `None` for a correlation matrix.
- **`annot`** — write the numeric value in each cell (default `True`).
- **`cmap`** — colormap name (default `"YlOrRd"`; ignored for the correlation
  matrix).
- **`vmin`/`vmax`** — color-scale anchors.
- **`method`** — the correlation drawn without `by`: `"spearman"` (the default,
  drawn as it always was — the answers read as they are, so a missing code
  such as 9 = Refused counts as an answer), `"pearson"` or `"kendall"` (tau-b).
  Pearson and Kendall are the Correlation matrix table's numbers with
  `missing="listwise"`: the codebook's missing codes are left out and counted
  under the plot with N, Pearson's r is weighted on weighted data (colour bar
  "Weighted Pearson r"), and Kendall says under its title that the weight is
  not applied. A pair that cannot be computed is a blank cell, and the note
  says why. Long labels are numbered — the rows read `1. label`, the columns
  `1`, `2`, … — and the plot is made tall enough for every row's label.

> `HeatMap` requires **seaborn** specifically; it raises
> `ImportError: seaborn is required for HeatMap` if seaborn is unavailable.

```python
# Mean autonomy and age across remote-frequency groups
data.plot.heatmap(["autonomy", "age"], by="remote_freq", cmap="Blues").show()

# Spearman correlation matrix of continuous measures
data.plot.heatmap(["age", "autonomy"]).show()

# Pearson, weighted like the Correlation matrix table, missing codes left out
data.with_weight("w").plot.heatmap(["autonomy", "satisfaction", "age"], method="pearson")
```

---

## `LikertChart`

```python
LikertChart(data, columns=[], neutral="split", sort="top2", show_values=True,
            figsize=(10, 6), palette="RdBu", title=None)
```

A battery of items on one ordered scale — agree–disagree statements, ratings —
as **diverging stacked bars**: each item is a bar whose answers below the
middle of the scale stack to the left of a centre line and those above it to
the right, so a battery's lean reads at a glance. The shares of the two
answers at either end (**top-2** and **bottom-2**; the top and bottom answer
alone on a scale of two or three) are written at the ends of every bar.

**Extra parameters**

- **`columns`** — the items: one answer per respondent each, all with the same
  value labels in the codebook (their missing codes aside). Items on different
  scales are refused, naming both: *The items of a Likert chart must share one
  scale, and these do not: Trust: Acme has 1 = No trust, …; Overall satisfaction
  has 1 = Very dissatisfied, …. Draw them in separate charts, or recode them onto
  one scale first.* Items without labels may give a valid range of whole
  numbers instead.
- **`neutral`** — `"split"` (the middle answer of an odd scale half on either
  side of the centre, the default) or `"side"` (apart, in a panel at the right).
  An even scale has no neutral answer; its centre falls between the middle two.
- **`sort`** — `"top2"` (the largest top-2 share first, the default) or
  `"listed"`.
- **`show_values`** — each answer's share in its segment where it fits.
- **`palette`** — a diverging palette (`"RdBu"`, `"BrBG"`, `"PuOr"`, `"RdYlBu"`,
  `"PiYG"`, `"coolwarm"`); the low answers take its first colour, the neutral
  answer is grey.

Codes run low to high, left to right: recode a scale written the other way
(1 = Strongly agree) first. The codebook's missing codes and any value not on
the scale are left out of the bars and counted under the chart, with each
item's base beside its name (`n = 552`); on weighted data the shares are sums
of weights and `n` still counts respondents. When the item labels start with
the same words up to a separator (`Trust: Acme`, `Trust: Globex`), those words
are the title and the rest names each bar. `chart.table` holds the numbers
drawn: each answer's %, top-2, bottom-2, N (and the weighted N).

```python
data.plot.likert(["trust_acme", "trust_globex", "trust_initech"]).save("trust.png")

# Neutral apart, in questionnaire order
data.plot.likert(items, neutral="side", sort="listed")
```

---

## `ScatterPlot`

```python
ScatterPlot(data, x="", y="", hue=None, trendline=True,
            figsize=(10, 6), palette="muted", title=None)
```

Plots two continuous variables against each other, with an optional color
grouping and a linear regression trendline.

**Extra parameters**

- **`x`** — X-axis variable.
- **`y`** — Y-axis variable.
- **`hue`** — optional categorical variable to color points by.
- **`trendline`** — add a linear regression line (default `True`). The
  trendline is drawn only when `hue` is `None`.

```python
data.plot.scatter("age", "autonomy", hue="remote_freq").show()
```

---

## The `data.plot` accessor

The accessor returns the same chart objects, so you can chain `show()`/`save()`:

```python
def bar(column, *, by=None, horizontal=False, show_values=True,
        figsize=(10, 6), palette="muted", title=None,
        show="count", split=None, layout="grouped", sort="code") -> BarChart
def boxplot(column, *, by, show_points=False,
            figsize=(10, 6), palette="muted", title=None) -> BoxPlot
def heatmap(columns, *, by=None, annot=True, cmap="YlOrRd",
            vmin=None, vmax=None, figsize=(10, 6), title=None,
            method="spearman") -> HeatMap
def scatter(x, y, *, hue=None, trendline=True,
            figsize=(10, 6), palette="muted", title=None) -> ScatterPlot
def likert(columns, *, neutral="split", sort="top2", show_values=True,
           figsize=(10, 6), palette="RdBu", title=None) -> LikertChart
```

```python
ax = data.plot.bar("it_role", horizontal=True).plot()   # get Axes to customize
ax.set_xlabel("Respondents")
```

To embed charts in a narrative document alongside tables and prose, add them to
a [[Report Document|Report-Document]] — it calls `save()` for you and links the
generated PNGs.

---

## Charts of results: `result_charts`

The charts above draw from the data. `result_charts.chart()` draws what an
analysis already computed — the table or statistics it returned — so the
picture beside a table shows that table's own numbers. It is also the flow's
**Result chart** node (`visualize.result_chart`).

```python
from siamang.reporting import result_charts

means = data.report.means("autonomy", by="remote_freq", method="anova", posthoc="tukey")
result_charts.chart(means).save("autonomy_means.png")          # means with 95 % CIs and letters

pca = data.analysis.pca(["autonomy", "satisfaction", "age"])
result_charts.chart([pca.variance, pca.stats])                 # scree plot, components kept filled
result_charts.chart(pca, kind="loadings", title="What the components are")
```

What each result draws (the first kind is what `kind="auto"` draws):

| Result | Kinds |
| :--- | :--- |
| Group means, Descriptive statistics, t-test, Paired tests (Wilcoxon, Friedman) | `means` (95 % confidence interval), `means_sd` (± 1 SD) |
| Paired tests with McNemar | `shares` — the share saying yes to each, with Wilson's interval |
| Proportion CI | `interval` — the share and its interval on a 0–100 % track |
| Net Promoter Score | `stacked` — detractors / passives / promoters, the score and its CI |
| TURF | `reach` (a search: reach by portfolio size), `items` (a fixed portfolio: each option's reach and what only it reaches) |
| MaxDiff | `utilities` (with 95 % intervals), `scores`, `shares` |
| Conjoint | `importance`, `partworths` |
| Share of preference | `shares` |
| Principal components, Factor analysis | `scree` (from the variance output: Kaiser line, parallel analysis), `loadings` (a heatmap) |
| Cluster (k-means) | `profile` — each cluster's means down the items |
| Regression | `coefficients` — a forest without the intercept; odds ratios on a log scale for a logit |
| Correlation matrix | `heatmap` — the lower triangle with the table's significance marks |
| Code open answers | `shares`, `sentiment` |

With a post-hoc test, Group means puts the **compact letter display** beside
each mean: means that share a letter do not differ at p < .05 (Tukey,
Games-Howell or Dunn, whichever ran). Intervals are Student's t for unweighted
means, the linearization (survey-package) interval for weighted ones, and
Wilson's for a share — see `siamang.data.intervals` in the
[[API Reference|API-Reference-Index]].

**Weight.** A result chart says what its result says: `weighted by 'w'`, or
`unweighted (the weight 'w' is not applied)`, as the second line of the title
and in `chart.weight_note`. A regression's, a PCA's, a cluster's or TURF's
table does not carry the weight itself — pass its statistics beside it
(`[model.table, model.stats]`), which also gives a regression's interval its
t distribution.

**Long labels, many categories.** Categories are rows, first at the top; labels
wrap (three lines, then an ellipsis), the font shrinks from 10 to 7 pt as rows
multiply, and a chart that still cannot hold them grows taller. Value labels
never leave the plot.

**In a flow**, connect an analysis's table (and its stat) to a Result chart;
choose a Kind where the result has several. The flow check says before the run
when the chart cannot draw what is connected (`RESULT_NOT_DRAWABLE`) or when the
Kind does not suit it (`RESULT_KIND`), and warns when results of two analyses
are connected (`RESULT_SOURCES`).

**Your own result.** `result_charts.register(MyResult, ["mykind"], draw)`
teaches the chart a new result: `draw(result, chart)` draws on
`chart.rows(labels)` or `chart.figure()` and returns its title.

---

See also: [[Reporting Tables|Reporting-Tables]] · [[Report Document|Report-Document]] · [[Analysis]] · [[Working with Data|Working-with-Data]] · [[Installation]]
