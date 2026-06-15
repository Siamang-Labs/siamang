# Cloud Analysis SDK

Write analysis scripts that run against your collected responses. The `siamang_cloud`
package is available in your project's run environment: you import it from a Python file,
read your project's tables, compute results, and build a report — without managing any
connection details yourself.

A script becomes an **analysis task** the moment you declare it in
[[Project Config (siamang.yaml)|Cloud-siamang-yaml]]. You then run it from the
**Analysis** screen (or on a schedule), and any report it saves shows up under
[[Analysis & Reports|Cloud-Analysis-and-Reporting]].

## The import surface

Everything you need comes from one package:

```python
from siamang_cloud import db, analysis, respondents, Report
```

| Import | What you use it for |
| :--- | :--- |
| `db` | List, inspect, read and write your project's tables |
| `analysis` | Weighting, frequencies, crosstabs, chi-square, Cramér's V |
| `respondents` | Dedup resumed submissions, completion time, partial flags |
| `Report` | Build a Markdown / HTML report document |

Your scripts run in an **isolated environment** with read access to your project's data.
Reading a table loads it as a pandas `DataFrame`, so anything you already know about
pandas, numpy and scipy works here too.

## `db` — your project data

`db` is your handle on the project's tables. Your collected answers live in a table
called **`responses`**; analysis steps you write add more tables (for example
`clean_responses`, `weighted_responses`).

| Call | Returns | Notes |
| :--- | :--- | :--- |
| `db.list_tables()` | `list[str]` | Names of every table in your project |
| `db.schema("responses")` | `list[dict]` | Each column's `name`, `type`, `nullable`, `default` |
| `db.table("responses").to_pandas()` | `DataFrame` | Load a whole table. The `responses` table is flattened so each answer is its own column |
| `db.write_table("clean", df, if_exists="replace")` | — | Save a DataFrame as a table. `if_exists` is `"fail"` (default), `"replace"` or `"append"` |
| `db.as_survey_data("responses")` | survey-data object | Load a table wrapped for label-aware analysis |
| `db.export_table("responses", "out.csv")` | written path | Write a table to a file — format from the extension |

There is **no free-form SQL** here: you read tables and work with them in pandas. When
you need a custom slice, load the table and filter it in Python.

When you read the `responses` table, each answer variable (for example `gender`,
`age_group`, `satisfaction`) comes back as its own column, alongside identifiers such as
`respondent_id` and the submission timestamps.

`export_table` infers the format from the file extension. Supported formats: `csv`,
`parquet`, `xlsx`, `sav` (SPSS) and `sqlite`.

```python
from siamang_cloud import db

print(db.list_tables())                       # e.g. ['responses', 'survey_meta']
print(db.schema("responses"))                 # column names and types

df = db.table("responses").to_pandas()        # one column per answer
db.export_table("responses", "outputs/responses.sav")   # SPSS for a colleague
```

## `analysis` — weights, tables, significance

These helpers take and return plain pandas objects, so a result drops straight into a
`Report`.

| Function | What it does |
| :--- | :--- |
| `frequencies(df, "col", weight=None)` | Frequency table with `value`, `count`, `percent` |
| `crosstab(df, "row", "col", weight=None, normalize=None)` | Two-way contingency table; `normalize="index"` / `"columns"` / `"all"` for percentages |
| `chi2(df, "a", "b")` | Pearson chi-square: returns `chi2`, `dof`, `p`, `cramers_v`, `n` |
| `cell_weights(df, "col", targets)` | Post-stratification weights so one variable matches target proportions |
| `rake_weights(df, targets)` | Raking (iterative proportional fitting) to several marginal targets |

`targets` is a mapping of category to share — proportions or counts, normalized for you.
The weight functions return a `Series` scaled to mean 1.0, ready to pass as the
`weight=` argument to `frequencies` or `crosstab`.

```python
from siamang_cloud import analysis, db

df = db.table("responses").to_pandas()
freq = analysis.frequencies(df, "satisfaction")
table = analysis.crosstab(df, "work_mode", "satisfaction", normalize="index")
test = analysis.chi2(df, "work_mode", "satisfaction")
print(test["p"], test["cramers_v"])
```

## `respondents` — response hygiene

Helpers that work over the loaded `responses` DataFrame.

| Function | What it does |
| :--- | :--- |
| `dedup_responses(df, id_col="respondent_id")` | Collapse repeated submissions (a resume updates, not duplicates); keeps the most recent |
| `completion_time(df)` | Per-response duration in seconds (prefers a `duration_s` column, else timestamps) |
| `partial_flag(df, required=[...])` | Boolean `Series`: `True` where any required field is blank |

## A complete script

This is a full analysis step you can commit. It cleans the raw responses, rakes the
sample to census margins, builds two tables with a significance note, and saves a report.
Declare it as a `type: analysis` task and it runs from the Analysis screen.

```python
"""Key tables (type: analysis) — frequencies, a weighted crosstab, chi-square."""

from siamang_cloud import Report, analysis, db, respondents

# 1. Read collected responses (one column per answer).
raw = db.table("responses").to_pandas()

# 2. One row per respondent; drop partials and speeders (under 2 minutes).
df = respondents.dedup_responses(raw, id_col="respondent_id")
df["duration_s"] = respondents.completion_time(df)
df["is_partial"] = respondents.partial_flag(df, required=["gender", "age_group", "satisfaction"])
df = df[~df["is_partial"]]
df = df[df["duration_s"].isna() | (df["duration_s"] >= 120)]

# 3. The achieved sample skews young/male; rake it to census margins.
CENSUS = {
    "gender": {1: 0.49, 2: 0.48, 3: 0.03},
    "age_group": {1: 0.32, 2: 0.36, 3: 0.32},
}
df["w"] = analysis.rake_weights(df, CENSUS)

# 4. Weighted estimates.
sat = analysis.frequencies(df, "satisfaction", weight="w")
ct = analysis.crosstab(df, "work_mode", "satisfaction", weight="w", normalize="index")
test = analysis.chi2(df, "work_mode", "satisfaction")

# 5. Save a report — it appears under Analysis & Reports.
(
    Report(
        title="Digital Life & Wellbeing — key tables",
        description="Weighted estimates (raked to census gender x age margins).",
    )
    .heading("Job satisfaction")
    .add(sat, caption="Table 1. Satisfaction, weighted %")
    .heading("Satisfaction by work mode")
    .add(ct, caption="Table 2. Row % within work mode")
    .note(f"chi2={test['chi2']:.1f}, dof={test['dof']}, p={test['p']:.4f}, "
          f"Cramér's V={test['cramers_v']:.2f}")
    .save("outputs/key_tables.md")
)
print("report written to outputs/key_tables.md")
```

You can also persist an intermediate result for a later step to pick up:

```python
db.write_table("weighted_responses", df, if_exists="replace")
```

Then declare the script in your project config so the platform can run it:

```yaml
tasks:
  key_tables:
    type: analysis
    entry: scripts/key_tables.py
    description: "Weighted frequencies, crosstab + chi-square"
    report: outputs/key_tables.md
```

## Building the report

`Report` is the composable document you assemble in your script. Every builder method
returns the report, so you chain them and finish with `save()`:

- **Narrative** — `.heading(text)`, `.markdown(md)`, `.note(md)`, `.value(label, v)`,
  `.divider()`.
- **Inserts** — `.add(component, caption=...)` accepts a pandas `DataFrame` or a library
  table / chart; `.image(path, caption=...)` embeds a figure.
- **Save** — `.save("outputs/report.md")` writes Markdown; `.save("outputs/report.html")`
  writes HTML. (PDF output is planned.)

See [[Report Document|Report-Document]] for the full builder reference.

## See also

- [[Project Config (siamang.yaml)|Cloud-siamang-yaml]] — declare your script as an analysis task
- [[Analysis & Reports|Cloud-Analysis-and-Reporting]] — run scripts and view reports
- [[Report Document|Report-Document]] — the `Report` builder in depth
- [[Working with Data|Working-with-Data]] — survey data and label-aware analysis
