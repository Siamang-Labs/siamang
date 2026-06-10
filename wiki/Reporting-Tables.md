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
| `to_html()` | `str` | `<table class="siamang-table">`; renders inline in Jupyter. |
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
  `"label"` (alphabetical by label).

```python
print(data.report.freq("it_role").to_markdown())
```

```text
| Value | Label | N | % | Cumulative % |
|---|---|---|---|---|
| 1.0 | Engineer | 37 | 33.9 | 33.9 |
| 2.0 | Data Scientist | 27 | 24.8 | 58.7 |
| 3.0 | DevOps | 23 | 21.1 | 79.8 |
| 4.0 | PM | 22 | 20.2 | 100.0 |
|  | Total | 109 | 100.0 | 100.0 |

Variable = IT Role; N valid = 109
```

---

## `CrossTable` — bivariate cross-tabulation

```python
CrossTable(data, row="", col="", pct="none", test=True)
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

```python
print(data.report.crosstab("it_role", "remote_freq", pct="row").to_markdown())
```

```text
| IT Role | Never | Occasionally | Hybrid | Mostly remote | Fully remote | Total |
|---|---|---|---|---|---|---|
| Engineer | 14.3 | 28.6 | 25.0 | 21.4 | 10.7 | 28 |
| Data Scientist | 25.0 | 15.0 | 15.0 | 20.0 | 25.0 | 20 |
| DevOps | 23.1 | 11.5 | 19.2 | 15.4 | 30.8 | 26 |
| PM | 35.7 | 14.3 | 14.3 | 10.7 | 25.0 | 28 |
| Total | 25.0 | 18.0 | 19.0 | 17.0 | 23.0 | 102 |

χ² = 10.1760; df = 12; p = 0.6006; Cramér's V = 0.1820; N = 102
```

---

## `GroupMeanTable` — grouped means with automatic test

```python
GroupMeanTable(data, column="", by="", test=True)
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

```python
print(data.report.means("autonomy", by="remote_freq").to_markdown())
```

```text
| Remote Frequency | Mean | SD | Median | N |
|---|---|---|---|---|
| Never | 3.696 | 1.329 | 4.0 | 23 |
| Occasionally | 2.167 | 1.467 | 2.0 | 12 |
| Hybrid | 2.9 | 1.296 | 3.0 | 30 |
| Mostly remote | 2.677 | 1.492 | 3.0 | 31 |
| Fully remote | 3.0 | 1.581 | 3.0 | 13 |

Kruskal-Wallis H = 10.5250; p = 0.0324; N = 109; Variable = Autonomy
```

Here `autonomy` is ordinal and `remote_freq` has five categories, so
Kruskal–Wallis H is chosen automatically.

---

## The `data.report` accessor

Instead of importing the classes, use the fluent accessor — it returns the same
table objects, so you can chain an exporter directly:

```python
def freq(column, *, exclude_missing=True, sort="value") -> FreqTable
def crosstab(row, col, *, pct="none", test=True) -> CrossTable
def means(column, *, by, test=True) -> GroupMeanTable
```

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
path  = table.export_xlsx("out/crosstab.xlsx")   # Path; creates parent dirs
```

To assemble several tables and charts into one narrative document, drop them
into a [[Report Document|Report-Document]]. For multi-variable cross-break
tables, see [[Banner Tables|Banner-Tables]].

---

See also: [[Reporting Charts|Reporting-Charts]] · [[Report Document|Report-Document]] · [[Banner Tables|Banner-Tables]] · [[Analysis]] · [[Working with Data|Working-with-Data]]
