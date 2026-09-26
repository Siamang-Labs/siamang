# Reporting Tables

siamang's declarative tables turn a [[Working with Data|Working-with-Data]]
`SurveyData` into publication-ready output. Each table reads variable labels,
value labels, and measurement scales from the attached metadata, computes the
right statistics, and exports to a DataFrame, Markdown, HTML, or Excel. The three
table types are `FreqTable`, `CrossTable`, and `GroupMeanTable`, each also
reachable through the fluent `data.report` accessor.

```python
from siamang.reporting import FreqTable, CrossTable, GroupMeanTable
```

The examples below assume `data` is the simulated `SurveyData` built in
[[Simulation]] / [[Analysis]] (variables `it_role`, `remote_freq`, `autonomy`).

---

## Common interface

All tables subclass `SurveyTable` and share these methods (the table is built
lazily on first use):

| Method | Returns | Notes |
| :--- | :--- | :--- |
| `to_frame()` | `pd.DataFrame` | Raw result table. |
| `to_markdown()` | `str` | GitHub-flavored pipe table; appends a stats footer. |
| `to_html()` | `str` | HTML table tagged with the `siamang-table` CSS class (rendered as `class="dataframe siamang-table"`); renders inline in Jupyter. |
| `export_xlsx(path)` | `Path` | Writes an `.xlsx` sheet named `"Table"`. |

The statistics footer (Chi-square, Cramér's V, the chosen mean-comparison test,
etc.) is rendered automatically beneath `to_markdown()`/`to_html()` output.

---

## `FreqTable` — univariate frequencies

```python
FreqTable(data, column="", exclude_missing=True, sort="value")
```

A frequency distribution with absolute counts, percentages, and cumulative
percentages, plus a `Total` row. Value labels are resolved automatically.

**Parameters**

- **`column`** — variable to tabulate.
- **`exclude_missing`** — drop `NaN` from the base (default `True`).
- **`sort`** — `"value"` (by code, default), `"freq"` (count descending), or
  `"label"` (alphabetical by label). Any other value is silently ignored and
  code order is kept.

```python
print(data.report.freq("it_role").to_markdown())
```

```text
| Value | Label | N | % | Cumulative % |
|---|---|---|---|---|
| 1 | Engineer | 58 | 29.0 | 29.0 |
| 2 | Data Scientist | 47 | 23.5 | 52.5 |
| 3 | DevOps | 43 | 21.5 | 74.0 |
| 4 | PM | 52 | 26.0 | 100.0 |
|  | Total | 200 | 100.0 | 100.0 |

Variable = IT Role; N valid = 200
```

---

## `CrossTable` — bivariate cross-tabulation

```python
CrossTable(data, row="", col="", pct="none", test=True, method="chi2")
```

A two-way contingency table with row/column totals and, by default, a
Chi-square test of independence reported in the footer alongside its degrees of
freedom, p-value, Cramér's V, and N.

**Parameters**

- **`row`** — row variable (usually the independent variable).
- **`col`** — column variable (usually the dependent variable).
- **`pct`** — percentage direction: `"none"` (counts), `"row"`, `"col"`, or
  `"total"`. The `Total` row/column always shows raw counts.
- **`test`** — run the Chi-square test and append the footer (default `True`).
  Requires `scipy`; without it the footer reports that scipy is missing.
- **`method`** — `"chi2"` (default) or `"fisher"`: Fisher's exact test, for
  small counts. A 2 × 2 table gets p, the odds ratio and its exact 95 % CI; a
  larger one the Fisher–Freeman–Halton p (exact, or from 20,000 random tables
  with a fixed seed when there are too many to sum). It counts respondents and
  leaves the codebook's missing codes out of the table; see
  [[Analysis|Analysis#fishers-exact-test-reportcrosstab-methodfisher]].

```python
print(data.report.crosstab("it_role", "remote_freq", pct="row").to_markdown())
```

```text
| IT Role | Never | Occasionally | Hybrid | Mostly remote | Fully remote | Total |
|---|---|---|---|---|---|---|
| Engineer | 17.2 | 19.0 | 27.6 | 20.7 | 15.5 | 58 |
| Data Scientist | 19.1 | 10.6 | 17.0 | 21.3 | 31.9 | 47 |
| DevOps | 27.9 | 32.6 | 20.9 | 7.0 | 11.6 | 43 |
| PM | 26.9 | 17.3 | 30.8 | 11.5 | 13.5 | 52 |
| Total | 45.0 | 39.0 | 49.0 | 31.0 | 36.0 | 200 |

χ² = 21.485; df = 12; p = 0.0437; Cramér's V = 0.189; N = 200
```

---

## `GroupMeanTable` — grouped means with automatic test

```python
GroupMeanTable(data, column="", by="", test=True, method="auto", posthoc="none", adjust="holm")
```

Compares the mean of a continuous variable across categories of a grouping
variable, reporting per-group `Mean`, `SD`, `Median`, and `N`. With `test=True`
it **selects the significance test automatically** based on the dependent
variable's scale and the number of groups:

| Dependent scale | 2 groups | 3+ groups |
| :--- | :--- | :--- |
| `ordinal` (or scale unknown) | Mann–Whitney U | Kruskal–Wallis H |
| `interval` / `ratio` | Independent t-test | One-way ANOVA |

**Parameters**

- **`column`** — continuous dependent variable.
- **`by`** — categorical grouping variable.
- **`test`** — run and report the chosen test (default `True`; requires `scipy`).
- **`method`** — `"auto"` (default: the choice above) or a test named by hand:
  `"student"`, `"welch"`, `"anova"`, `"welch_anova"`, `"mannwhitney"`,
  `"kruskal"`, reported with df and an effect size.
- **`posthoc`** — `"none"` (default), `"tukey"` (after `anova`),
  `"games_howell"` (after `welch_anova`) or `"dunn"` (after `kruskal`, p
  adjusted by **`adjust`**: `"holm"` or `"bonferroni"`). The pairs render under
  the table as a `PostHocTable` (`table.posthoc_table`) and go to a second sheet
  of `export_xlsx`.

A test named by hand leaves the codebook's missing codes out of the table and
the test and says how many (`Missing codes left out`); `"auto"` reads the data
as it always has. See [[Analysis|Analysis#several-groups-and-post-hoc-tests-reportmeans]].

```python
print(data.report.means("autonomy", by="remote_freq").to_markdown())
```

```text
| Remote Frequency | Mean | SD | Median | N |
|---|---|---|---|---|
| Never | 3.222 | 1.38 | 4.0 | 45 |
| Occasionally | 2.923 | 1.458 | 3.0 | 39 |
| Hybrid | 2.898 | 1.447 | 3.0 | 49 |
| Mostly remote | 3.0 | 1.653 | 2.0 | 31 |
| Fully remote | 3.278 | 1.386 | 4.0 | 36 |

Kruskal-Wallis H = 2.133; p = 0.7113; N = 200; Variable = Autonomy
```

Here `autonomy` is ordinal and `remote_freq` has five categories, so
Kruskal–Wallis H is chosen automatically.

---

## `TTestTable` and `CorrelationMatrixTable`

```python
TTestTable(data, column="", kind="independent", by=None, groups=None, other=None,
           mu=0.0, variances="welch", confidence=0.95)
CorrelationMatrixTable(data, columns=[], method="spearman", missing="pairwise",
                       adjust="none", layout="matrix")
```

Both live in `siamang.reporting.stat_tables` and are what `data.report.ttest`
and `data.report.correlation_matrix` return. `TTestTable` has one row per group
(N, mean, SD, SE) and t, df, p, the mean difference with its CI and Cohen's d in
the footer; `CorrelationMatrixTable` prints the lower triangle with significance
marks, or one row per pair with `layout="pairs"`. Both are explained, with
output, in [[Analysis|Analysis#choosing-the-test-yourself]].

---

## Weighted data

After `SurveyData.with_weight(...)` (the flow's **Apply weight**) every table
reads the weight and says in its footer what it did with it: `FreqTable` sums
weights for N and % and adds an `Unweighted N` column; `CrossTable` sums
weights in the cells and runs χ² on Kish's effective base (Fisher's exact test
counts respondents and says so); `GroupMeanTable` weights means, SDs and
medians while N, the test and the post-hoc pairs stay unweighted.
`CorrelationMatrixTable` weights Pearson's coefficient (p on Kish's effective
base); `TTestTable` and the rank correlations say the weight is not applied. The
banner, NPS, MaxDiff and conjoint tables are weighted throughout and name the
`Weight`. The descriptives table weights means, SDs, medians and quartiles
beside a `Weighted N` column and gives Kish's effective N. The quality, theme
and data-check tables count responses and say
`Weight: unweighted (the weight 'w' is not applied)`. See
[[what the weight reaches|Working-with-Data#what-the-weight-reaches]].

---

## The `data.report` accessor

Instead of importing the classes, use the fluent accessor — it returns the same
table objects, so you can chain an exporter directly:

```python
def freq(column, *, exclude_missing=True, sort="value") -> FreqTable
def crosstab(row, col, *, pct="none", test=True, method="chi2") -> CrossTable
def means(column, *, by, test=True, method="auto", posthoc="none", adjust="holm") -> GroupMeanTable
def ttest(column, *, kind="independent", by=None, groups=None, other=None, mu=0.0,
          variances="welch", confidence=0.95) -> TTestTable
def correlation_matrix(columns, *, method="spearman", missing="pairwise", adjust="none",
                       layout="matrix") -> CorrelationMatrixTable
def descriptives(columns, *, by=None, detail=False) -> DescriptivesTable
def data_check(variables=None) -> DataCheckTable
def themes(codeframe, *, sentiment=False) -> ThemeTable
```

`descriptives` and `data_check` are described in [[Analysis|Analysis#descriptive-statistics-datareportdescriptives]];
both print an undefined cell (the SD of one answer) as a blank, never `nan`.
`themes` gives one row per theme as a share of the coded answers, then `Coded`
and `Uncoded` as shares of everyone who answered, with `Coverage` and
`Distinct uncoded answers` in its stats; with `sentiment=True` and a codeframe
built with sentiment, each row adds `Negative %`, `Neutral %` and `Positive %`
and the stats the overall `Sentiment` and the `Net sentiment`.

```python
data.report.freq("it_role", sort="freq").to_frame()
data.report.crosstab("it_role", "remote_freq", pct="col").to_html()
data.report.means("autonomy", by="remote_freq").export_xlsx("autonomy_means.xlsx")
```

---

## Exporting

Every table supports the four exporters from the common interface:

```python
table = data.report.crosstab("it_role", "remote_freq", pct="row")

frame = table.to_frame()            # pandas DataFrame
md    = table.to_markdown()         # str (with stats footer)
html  = table.to_html()            # str
path  = table.export_xlsx("crosstab.xlsx")   # Path (the directory must already exist)
```

To assemble several tables and charts into one narrative document, drop them
into a [[Report Document|Report-Document]]. For multi-variable cross-break
tables, see [[Banner Tables|Banner-Tables]].

---

## Tab book (Excel)

A tab book is every question of the study crossed by the same banner, one
sheet each — the workbook a client opens after fieldwork.
`siamang.reporting.tabbook.write_tabbook` writes it; the flow node is
**Tab book (Excel)** (`output.tabbook`), whose `stat` output says how many
sheets were written and which questions were skipped, and why.

```python
from siamang.reporting.tabbook import write_tabbook

stat = write_tabbook(
    data.with_weight("weight"),
    "outputs/tabbook.xlsx",
    banner=["region", "age_band"],   # the columns: Total, then every code of each
    questions=None,                  # every nominal, ordinal and multiple-choice question
                                     # but open answers and rankings (name them to include them)
    percentages="column",            # or "row", or "none" (counts only)
    counts=True,
    letters=True, level=0.05, correction="none",   # or "bonferroni"
    means=True,                      # mean and SD of an interval or ratio question
)
# {'Workbook': 'outputs/tabbook.xlsx', 'Sheets written': 23, 'Questions skipped': 1,
#  'Skipped': 'comment: 187 different answers and no answer labels — …', …}
```

- **Contents** lists every question with a link to its sheet, and what was not
  tabulated with the reason.
- **One sheet per question**, named after its variable (at most 31
  characters, unique as Excel compares names): the label, the banner across
  (the banner variable over its codes, each with its letter), the base —
  unweighted, and weighted when a weight applies — then per answer its count
  and its percentage (`0.0%`), the letters in their own cells beside the
  column percentage (they compare column percentages, so a book of row
  percentages or counts only has none), and for an interval or ratio
  question its mean and standard deviation per column. The header and the
  bases are frozen.
- **Notes**: the weight, the percentages, the base, the test, alpha,
  Bonferroni, the minimum base, the missing codes left out and the date.

The numbers are the [[Banner table's|Banner-Tables]]: its counts, and its
two-sided z-test of column proportions within each banner variable (a column
under thirty — effective — respondents is not tested; Total never is). Two
things differ, on purpose: the codebook's missing codes are left out (a
question's from its base; a banner variable's respondent is in Total and in
none of its columns), and a column's base — for its percentages and its test —
is those in it who answered the question. A multiple-choice question is one
table of every option on the base of those who chose at least one, so its
percentages add up to more than 100. `siamang.reporting.tabbook.tabulate`
returns the numbers without writing the workbook.

On weighted data a cell holds the sum of weights as it is, and a percentage is
of those sums — as the Frequencies and Crosstab tables compute it, never of
sums rounded for show: weights of 0.04, 0.04, 0.04 and 0.34 give 8.7, 17.4 and
73.9 %. The weighted counts and the weighted base are shown to one decimal
(`#,##0.0`), as those tables show them; the unweighted base is a whole number.
The workbook keeps text as text as Save report's does: a label, an answer or a
banner name that begins with `=` is written as a string, never as a formula
Excel would run, and a link names its sheet quoted (`'q''x'!A1` for a sheet
`q'x`).

---

See also: [[Reporting Charts|Reporting-Charts]] · [[Report Document|Report-Document]] · [[Banner Tables|Banner-Tables]] · [[Analysis]] · [[Working with Data|Working-with-Data]]
