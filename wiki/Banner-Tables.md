# Banner Tables

A **banner table** (also called a cross-break) is the workhorse of survey
reporting: it stacks one or more *row* variables against one or more *column*
(banner) variables in a single wide table, so you can read every subgroup
breakdown at a glance. siamang builds these through the `data.tables` accessor
(`SurveyTables`), which returns an export-ready `BannerTable`.

```python
from siamang.data import SurveyTables, BannerTable
```

In practice you reach `SurveyTables` via the `tables` property of a
[[Working with Data|Working-with-Data]] `SurveyData`:

```python
data.tables   # -> SurveyTables(frame, variables, weight_column)
```

---

## `SurveyTables.banner`

```python
def banner(self, rows: list[str], columns: list[str],
           weight: str | None = None, labels: bool = True) -> BannerTable: ...
```

Cross-tabulates **every** `rows` variable against **every** `columns` variable
and concatenates the results into one long, tidy frame. For each row/column
pair it computes the cell count `n` and the percentage **within each column
category** (i.e. column percentages).

**Parameters**

- **`rows`** — list of row variable names (the categories being profiled). Must
  be non-empty.
- **`columns`** — list of banner/column variable names (the cross-break groups).
  Must be non-empty.
- **`weight`** — optional weight column; cells become summed weights instead of
  raw counts. Defaults to the `SurveyData` weight (set via `with_weight`). Raises
  `ValueError` if the column is not in the frame.
- **`labels`** — resolve variable and value labels into `row_label`/`column_label`
  columns (default `True`).

The result is a `BannerTable` wrapping a DataFrame with one row per
(row variable, row value, column variable, column value) combination and the
columns:

```text
row_variable | row_value | row_label | column_variable | column_value | column_label | n | percent
```

`percent` is a proportion within the column category (multiply by 100 for a
percentage).

---

## Example

Using the simulated `data` from [[Simulation]] / [[Analysis]] (variables
`it_role`, `remote_freq`):

```python
banner = data.tables.banner(rows=["it_role"], columns=["remote_freq"])
print(banner.frame.head(6).to_string())
```

```text
  row_variable  row_value       row_label column_variable  column_value   column_label     n   percent
0      it_role          1        Engineer     remote_freq             1          Never  10.0  0.222222
1      it_role          1        Engineer     remote_freq             2   Occasionally  11.0  0.282051
2      it_role          1        Engineer     remote_freq             3         Hybrid  16.0  0.326531
3      it_role          1        Engineer     remote_freq             4  Mostly remote  12.0  0.387097
4      it_role          1        Engineer     remote_freq             5   Fully remote   9.0  0.250000
5      it_role          2  Data Scientist     remote_freq             1          Never   9.0  0.200000
```

Read row 0 as: among respondents whose `remote_freq` is *Never*, 22.2% are
Engineers. Pass multiple variables to profile several breakdowns at once:

```python
# Several row variables against several banner variables
banner = data.tables.banner(rows=["it_role", "autonomy"],
                            columns=["remote_freq"])
```

### Weighted banner

```python
weighted = data.with_weight("design_weight")
banner = weighted.tables.banner(rows=["it_role"], columns=["remote_freq"])
# or override per call:
banner = data.tables.banner(rows=["it_role"], columns=["remote_freq"],
                            weight="design_weight")
```

---

## `BannerTable` and export

```python
@dataclass(frozen=True, slots=True)
class BannerTable:
    frame: pd.DataFrame
```

`BannerTable` is an immutable container around the compiled `frame`. Access the
DataFrame directly, or export it:

| Method | Returns | Notes |
| :--- | :--- | :--- |
| `export_csv(path, **kwargs)` | `Path` | Writes CSV (`index=False`); creates parent dirs. |
| `export_xlsx(path, **kwargs)` | `Path` | Writes Excel (`index=False`); creates parent dirs. |

```python
banner = data.tables.banner(rows=["it_role"], columns=["remote_freq"])

df = banner.frame                      # work with it in pandas
banner.export_xlsx("out/banner.xlsx")  # publication export
banner.export_csv("out/banner.csv")
```

---

## The one that is meant to be read: `data.report.banner`

`data.tables.banner` gives you the numbers in tidy form — one row per pair of
values — which is what a spreadsheet or another program wants. The version a
person reads is `data.report.banner`, which lays the same numbers out the way an
agency table is laid out:

```python
table = data.report.banner(["satisfaction", "recommend"], ["region", "age_band"])
print(table.to_markdown())
```

| Question | Answer | Region: North (A) | Region: South (B) | Age: Under 35 (C) | Age: 35+ (D) |
|---|---|---|---|---|---|
| Base | respondents | 162 | 127 | 206 | 194 |
| Satisfied? | Yes | 72.8% (118) B | 40.2% (51) | 55.8% (115) | 49.5% (96) |

A letter says the column is **significantly higher** than the column that letter
names. Three things decide whether that claim is honest, and all three are
reported in `stats` rather than assumed:

- **Only within a banner variable.** The values of `region` are mutually
  exclusive groups of the same people, which is what a z-test of two proportions
  assumes. Columns from *different* banner variables overlap — a northerner is
  also under 35 — so the table never compares them.
- **The effective base on weighted data.** Weights make a sample behave like a
  smaller one; testing on the raw count would manufacture significance. The test
  uses Kish's effective sample size, and `stats` says so.
- **A floor under the base.** A column with fewer than thirty respondents is not
  tested at all. A headline difference computed off seven people is noise with a
  letter beside it.

`correction="bonferroni"` is available; the default is `"none"`, as the industry
does it, and either way the choice is named in `stats` beside the level.

## When to use which table

- **`data.report.banner`** — the cross-break to read or put in a report: blocks
  of columns, a base row, significance letters.
- **`data.tables.banner`** — the same numbers in tidy long format, ideal for
  spreadsheets and for feeding to something else.
- **`CrossTable`** ([[Reporting Tables|Reporting-Tables]]) — a single, labeled
  two-way table with Chi-square/Cramér's V and row/column percentages, ideal for
  inline Markdown/HTML and [[Report Document|Report-Document]] narratives.

---

See also: [[Reporting Tables|Reporting-Tables]] · [[Working with Data|Working-with-Data]] · [[Analysis]] · [[Report Document|Report-Document]] · [[Data Import and Export|Data-Import-and-Export]]
