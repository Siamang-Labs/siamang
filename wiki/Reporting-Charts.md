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
         top=None, other=False, intervals=False, confidence=0.95,
         letters=False, level=0.05, correction="none",
         bins="auto", min_slice=3.0,
         figsize=(10, 6), palette="muted", title=None)
```

With only `column`, plots the **distribution** of a categorical variable. With
`by` set, plots the **mean** of `column` within each category of `by`. With
`split` set, plots the **answers within each group** of a second variable — the
chart of a crosstab. `layout="histogram"` draws a **histogram** of a number,
`layout="donut"` one variable's answers as a **donut**.

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
  are drawn side by side only; stacking them is refused. `"histogram"` and
  `"donut"` are forms of their own, below.
- **`top`** — only the N answers given most (with `split`, given most overall;
  for a multiple-choice question, the options named most). Two answers given
  as often: the first in code order is kept. The note under the chart says how
  many of how many are drawn. Not with `by`.
- **`other`** — with `top`: one more bar, grey and last whatever the sort, for
  the rest — for a multiple-choice question the share of respondents who named
  **any** of them, not the sum of their shares. Off (the default), the rest are
  left out.
- **`intervals`**, **`confidence`** — error bars at `confidence` (0.95): on a
  percentage, Wilson's score interval of the share (weighted: of the weighted
  share, on Kish's effective base — the share and base Proportion CI gives); on
  a mean by group, the interval the Group means chart draws (Student's t;
  weighted, the linearization interval). With `split` each group's own base.
  The value is written past the whisker. On bars side by side only: stacked
  layouts refuse them; counts have none (the note says so).
- **`letters`**, **`level`**, **`correction`** — with `split`,
  `show="percent"` and `layout="grouped"`: each group gets the letter the Banner
  table gives its column (A, B, … in the codebook's order, under its name), and
  each bar carries, in bold after its value, the letters of the groups whose
  share of that answer is significantly **lower** — the Banner table's
  two-sided z-test of column proportions at `level` (0.05), `correction`
  `"none"` or `"bonferroni"`, on the base of each group's respondents who
  answered (Kish's effective base when weighted). A group with fewer than 30 is
  not tested, and the note names it. These are the letters the Tab book prints
  for the same cells (and the Banner table's, when everyone answered).
- **`sort`** — `"code"` (the codebook's order, the default) or `"value"` (the
  largest bar first; with `split`, the answer given most overall; with `by`,
  the highest mean). A colour belongs to its answer, not to its place, so a
  sorted chart and an unsorted one colour the same answer alike. When the
  answers split into groups are a scale (ordinal and up), they keep its order
  and the groups go largest first instead: by their share of the top answer
  (by their total, for counts), as the note under the chart says. Any value
  but the defaults of `show`, `split` and `sort` draws the newer chart below,
  so changing only `sort` also changes the look (colours, labels, notes).

At the defaults (`show="count"`, no `split`, `sort="code"`, and none of `top`,
`other`, `intervals`, `letters`, a histogram or a donut) the chart is the one
it has always been, picture for picture. The newer forms also:

- leave the codebook's missing codes out of the bars (a 99 "Don't know" is not
  an answer) and say how many under the plot;
- write under the plot the base (`Base: 571 respondents who answered
  (weighted: 742.7).`), the weight, and for a split each group's `n` under its
  name;
- draw one colour for a single series, and the steps of an ordered scale
  (ordinal and up) in one hue, light to dark;
- wrap long labels, put the legend under the plot when the figure is too narrow
  for it beside (or it is taller than the plot), and let a small figure grow
  taller rather than squash the plot to nothing;
- give every label beside horizontal bars a row of its own: smaller (to 8 pt)
  and wider first, else the figure grows taller, so no two labels print over
  each other; vertical bars whose labels cannot be read under them, even
  wrapped or turned 45°, are drawn horizontally instead;
- wrap the axis titles to the plot's own length, and write `% within each
  group` on the value axis when `% within <the Split by question>` would not
  fit (the note under the plot names the variable).

A multiple-choice question is drawn by these forms whatever the parameters (the
older chart could not draw one).

**Histogram** (`layout="histogram"`) — an interval or ratio variable (a nominal
or ordinal one is refused, as is text that is not a number) in **`bins`**:
`"auto"` (Freedman and Diaconis's width, 2 · IQR / ∛n, as
`numpy.histogram_bin_edges(x, "fd")`; Sturges' number when the middle half of
the answers is one value; answers that are all whole numbers get a whole width,
the edges halfway between two numbers, so no bin holds more possible answers
than another), a number of bins of equal width, or the edges (`"0, 18, 25, 35,
50, 65"` or a list) — at most 100 bins. The bars are counts or, with
`show="percent"`, percent of the respondents who answered; weighted when a
weight is applied (the automatic width comes from the answers as they are). The
note gives the bins' rule, the answers outside given edges (left out of the
bars, kept in a percentage's base) and bins of unequal width (a bar's height is
its count, not its density). With `split`, one panel per group (at most 12),
sharing the bins and the value scale, one above another — two columns past four
groups — each titled by its group and `n`; the figure grows so each panel is
readable. Small multiples rather than outlines over one another: groups of
different shapes and sizes stay apart, and more than three stay legible.

**Donut** (`layout="donut"`) — one variable's answers as the parts of a whole,
clockwise from the top in the order `sort` gives, each slice's percentage on it
or, when the slice is too thin to hold it, beside the ring in a column joined to
its slice by a line (the labels of a side a line apart), the base in the middle
("1,200 respondents", and the weighted base). Slices under **`min_slice`** %
(3) are combined as a grey Other when there are two or more of them (0 keeps
every slice); with `top`, the answers after the top N are always combined as
Other — a donut's slices make a whole. The answers are named in a legend beside
the donut, or under it on a narrow figure or when it is taller than the plot. A
donut with `split` or `by`, of a multiple-choice question (its shares add up to
more than 100 %), or with intervals or letters, is refused.

```python
# Frequency of IT roles
data.plot.bar("it_role").show()

# Percent of respondents, largest first, horizontal
data.plot.bar("it_role", show="percent", sort="value", horizontal=True)

# Satisfaction within each region, stacked to 100 %
data.plot.bar("satisfaction", split="region", layout="stacked_100")

# Mean autonomy by remote frequency, saved to disk
data.plot.bar("autonomy", by="remote_freq", palette="pastel").save("autonomy_means.png")

# The ten roles named most, the rest as Other, with 95 % intervals
data.plot.bar("it_role", show="percent", top=10, other=True, intervals=True)

# Satisfaction by region with the Banner table's letters
data.plot.bar("satisfaction", split="region", show="percent", letters=True)

# A histogram of age per region, and a donut of the roles
data.plot.bar("age", layout="histogram", bins="18, 25, 35, 50, 65, 100", split="region")
data.plot.bar("it_role", layout="donut")
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
  not applied. A pair that cannot be computed is a blank cell (an item with the
  same answer from everyone, its own diagonal too), and the note says why,
  naming the pair as the chart names its items. Long labels are numbered — the
  rows read `1. label`, the columns `1`, `2`, … — and the rows' labels get
  smaller and wider before the plot grows taller for them. The coefficients are
  written at a size their cells hold (at most 10 pt); below 6 pt they are left
  to the table, and the note says so.

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
  numbers instead, or be asked by a Likert scale question (its points, the
  ends named by its end labels).
- **`neutral`** — `"split"` (the middle answer of an odd scale half on either
  side of the centre, the default) or `"side"` (apart, in a panel at the right).
  An even scale has no neutral answer; its centre falls between the middle two.
- **`sort`** — `"top2"` (the largest top-2 share first, the default) or
  `"listed"`.
- **`show_values`** — each answer's share in its segment where it fits.
- **`palette`** — a diverging palette (`"RdBu"`, `"BrBG"`, `"PuOr"`, `"RdYlBu"`,
  `"PiYG"`, `"coolwarm"`); the low answers take its first colour, the neutral
  answer is grey, and an even scale's two middle answers keep a colour (the
  palette is sampled two wider and its two palest dropped).

The item labels are fitted to the figure — smaller and wider on a narrow one —
before the chart grows taller, and a row is no taller than its label (at most
60 pt): one item draws one bar, titled by its label, its row showing its base.
The centre line runs behind the neutral answer's value.

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
        show="count", split=None, layout="grouped", sort="code",
        top=None, other=False, intervals=False, confidence=0.95,
        letters=False, level=0.05, correction="none",
        bins="auto", min_slice=3.0) -> BarChart
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
| Paired tests with McNemar or Cochran's Q | `shares` — the share saying yes to each, with Wilson's interval |
| Proportion CI | `interval` — the share and its interval on a 0–100 % track |
| Net Promoter Score | `stacked` — detractors / passives / promoters, the score and its CI |
| TURF | `reach` (a search: reach by portfolio size), `items` (a fixed portfolio: each option's reach and what only it reaches) |
| MaxDiff | `utilities` (with 95 % intervals), `scores`, `shares` |
| Conjoint | `importance`, `partworths` |
| Share of preference | `shares` |
| Principal components, Factor analysis | `scree` (from the variance output: Kaiser line, parallel analysis), `loadings` (a heatmap) |
| Cluster (k-means) | `profile` — each cluster's means down the items |
| Regression | `coefficients` — a forest without the intercept; odds ratios on a log scale for a logit and an ordinal logit (its thresholds left out) |
| Correlation matrix | `heatmap` — the lower triangle with the table's significance marks |
| Code open answers | `shares`, `sentiment` |
| Key drivers | `importance` — each driver's share of R² (`drivers.plot`) |
| Perceptual map | `map` — the map, from any of its tables (`correspondence.plot`); drawn taller when its labels would overlap, and with numbered points and a list of their names under it when even that is too crowded |
| Price sensitivity | `curves` — Van Westendorp's curves and points (and the NMS trial curve), or Gabor-Granger's demand and revenue (`pricing.plot`) |

With a post-hoc test, Group means puts the **compact letter display** beside
each mean: means that share a letter do not differ at p < .05 (Tukey,
Games-Howell or Dunn, whichever ran). Intervals are Student's t for unweighted
means, the linearization (survey-package) interval for weighted ones, and
Wilson's for a share — see `siamang.data.intervals` in the
[[API Reference|API-Reference-Index]].

**Weight.** A result chart says what its result says: `weighted by 'w'`, or
`unweighted (the weight 'w' is not applied)`, as the second line of the title
and in `chart.weight_note`. A regression's, a PCA's, a cluster's or TURF's
table carries it in `table.attrs["weight"]` (a cluster's: that k-means does not
apply it), so the table alone is enough; pass its statistics beside it
(`[model.table, model.stats]`) to give a regression's interval its t
distribution.

**Long labels, many categories.** Categories are rows, first at the top; labels
wrap and stay whole, the font shrinks from 10 to 7 pt as rows multiply, and a
chart that still cannot hold them grows taller rather than cut them — only a
label past four lines is cut, and never so that two read alike. The title, the
axis titles and the notes wrap to the plot, inside the figure. Value labels
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

## `TrendChart` — a measure over waves or dates

A tracking study asks the same question wave after wave, or reads an open
survey by the month. `data.plot.trend` draws one line per group and hands the
same points over as a table, each with its base:

```python
def trend(time, *, period="month", measure="percent", variable=None, codes=None,
          by=None, band=True, min_base=30, figsize=(10, 6), palette="muted",
          title=None) -> TrendChart
```

- **`time`** — a wave code (one point per code, ordered by code, the value
  labels on the axis; a wave the codebook declares between two that were
  found is a gap) or a date: a `datetime64` column, or ISO 8601 text as a
  platform's snapshot writes the responses' `created_at`
  (`2026-05-25 09:00:00+00:00`, `2026-05-25T09:00:00.000Z`, `2026-05-25`).
  Times with a zone are read in UTC; text that is not a date is left out and
  counted.
- **`period`** — for dates: `day`, `week`, `month`, `quarter` or `year`. A
  week is an ISO week, Monday to Sunday, labelled by its ISO year and number
  (`2026-W01` runs from Monday 29 December 2025). Every period between the
  first and the last is on the axis; an empty one is a gap.
- **`measure`** — `"percent"` of those who answered `variable` who gave one of
  `codes` (`[4, 5]` is a top-2 box; for a multiple-choice question, any of
  them), `"mean"` of `variable`, or `"count"` of respondents.
- **`by`** — one line per group; a respondent with a missing code is in none.
  A multiple-choice question cannot split (a respondent would be in several
  lines), nor be the time.
- **`band`** — the 95 % interval: Proportion CI's normal approximation, or the
  mean's t interval, on Kish's effective base when the data is weighted. The
  bands of up to four lines are drawn; more would hide one another and the
  lines, so the chart says "No bands: the 95% intervals of 13 lines would hide
  one another; the table gives each point's."
- **`min_base`** — a percent or a mean of fewer respondents is drawn hollow,
  noted under the chart and in the table's `Note` column. A count is its own
  base: its points are never hollow, and its table has no `Note`.

On weighted data the points, the band and the count are weighted and the table
gains `Weighted base` and `Effective base`; the codebook's missing codes are
left out of every base and named in the table's statistics.

**Long labels, many lines, small figures.** The Trend is drawn as the Bar
chart's newer forms are: every line has a colour of its own (past the
palette's ten, lighter and darker ones); the value axis ticks whole percents,
or separates thousands of a count or a mean (`20,000`); a period's label is
level, wrapped to the room between two ticks, when every word fits it, and
otherwise slanted in as many lines as fit — only then, and only as far as it
must, is every second or third period named; the title and axis titles wrap to
the plot; the legend sits beside the plot, or under it on a figure narrower
than 7.5 inches or when it is taller than the plot; and a figure too small for
its labels grows taller rather than squeeze the plot. Under the plot the chart
says what its table says under itself:

```
Base: 3,790 respondents who answered (weighted: 4,646.0); 157 to 201 per point.
Gaps: no respondents in 3 of 39 points.
Hollow points: fewer than 30 respondents.
Bands: 95% confidence intervals.
Weighted by 'w'; the bases count respondents.
Left out as missing: Satisfaction: 210 (9 = Don't know).
Left out: 1 without created_at; 1 whose created_at is not a date (for example 'n/a').
```

The Trend draws its own chart, and its table is that chart's numbers: it is
not a result for the Result chart (connecting it says `RESULT_NOT_DRAWABLE`).

```python
chart = data.plot.trend("wave", variable="satisfaction", codes=[4, 5], by="segment")
chart.save("satisfaction_trend.png")
chart.table.to_frame()     # Period, Segment, Percent, Lower 95%, Upper 95%, Base, Note
chart.table.stats          # Measure, Base, Time, Interval, Missing codes left out, …

data.plot.trend("created_at", period="week", measure="count").show()
```

In a flow it is the **Trend** node (`visualize.trend`), with a `chart` and a
`table` output — the table goes into a report section or a Live tile. The flow
check says before the run what the questionnaire already settles and the run
would refuse: the mean of a nominal or a multiple-choice question, a
multiple-choice question as Time or Split by, and a missing code named among
the Answer codes (`PARAM_CONFLICT`, in the run's words).

---

See also: [[Reporting Tables|Reporting-Tables]] · [[Report Document|Report-Document]] · [[Analysis]] · [[Working with Data|Working-with-Data]] · [[Installation]]
