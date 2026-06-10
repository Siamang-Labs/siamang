# Cloud Analysis SDK

`siamang_cloud` is the small SDK that analysis scripts import. It is available
inside the analysis sandbox (see [[Cloud Analysis and Reporting|Cloud-Analysis-and-Reporting]])
and gives a script three modules plus a re-exported report builder:

```python
from siamang_cloud import db, analysis, respondents, Report
```

- `db` — read the project's response tables (and write derived tables back).
- `analysis` — weighting, frequencies, crosstabs, and significance tests.
- `respondents` — respondent-level helpers (dedup/resume, completion time,
  partial flags).
- `Report` — the composable report document, re-exported from
  `siamang_cloud_engine` (full reference: [[Report Document|Report-Document]]).

The SDK is configured entirely from environment variables the run worker injects
into the sandbox — `SIAMANG_CLOUD_PG_DSN`, `SIAMANG_CLOUD_PROJECT_SCHEMA`,
`SIAMANG_CLOUD_PROJECT_ID` — so a script never sees a connection string or
credentials. The DSN is a Postgres role scoped to the project's own schema; a
script can only touch its own data. (See [[Cloud Sandbox and Security|Cloud-Sandbox-and-Security]].)

## `db` — project data access

```python
db.table(name)                         # -> _Table; .to_pandas() loads it as a DataFrame
db.list_tables()                       # -> list[str] of tables in the project schema
db.schema(name)                        # -> list of {name, type, nullable, default}
db.write_table(name, df, if_exists="fail")   # "fail" | "replace" | "append"
db.as_survey_data(name="responses", questionnaire=None)  # SurveyData wrapper for analysis
db.export_table(name, path, fmt=None)  # csv | parquet | xlsx | sav (SPSS) | sqlite
```

The raw `responses` table stores each submission's answers in a `data` JSONB
column. `db.table("responses").to_pandas()` **flattens** that JSONB so each
answer variable becomes a top-level column (alongside `id`, `survey_id`,
`respondent_id`, and the timestamps):

```python
raw = db.table("responses").to_pandas()
# real table columns: id, survey_id, respondent_id, partial, created_at, updated_at
# plus one column per answer variable lifted out of `data` (gender, age_group, …)
```

Any timing fields a respondent's payload carries (for example `duration_s`) come
through `data` as columns too; the `respondents` helpers below default to the
conventional `submitted_at` / `started_at` / `duration_s` names and simply skip
whatever a given dataset does not have.

Derived tables you write back live in the same project schema and show up under
**Database → Tables** in the web app:

```python
clean = raw.dropna(subset=["satisfaction"])
db.write_table("clean_responses", clean, if_exists="replace")
```

Table and column names are validated before use, and only the project's own
`project_<id>` schema is addressable, so the data boundary holds even for
untrusted scripts.

## `analysis` — weights, tables, significance

All functions take and return plain `pandas` objects, so results drop straight
into `Report.add(...)`.

```python
analysis.frequencies(df, column, *, weight=None, dropna=True)
    # -> DataFrame[value, count, percent]; weighted counts sum the weight column

analysis.crosstab(df, row, col, *, weight=None, normalize=None)
    # -> two-way contingency table; normalize ("index"|"columns"|"all") -> percentages

analysis.chi2(df, a, b)
    # -> {chi2, dof, p, cramers_v, n}  (Pearson chi-square + Cramér's V effect size)

analysis.cell_weights(df, column, targets)
    # -> Series; single-variable post-stratification weights (scaled to mean 1.0)

analysis.rake_weights(df, targets, *, max_iter=50, tol=1e-6)
    # -> Series; iterative proportional fitting (raking) to multiple margins
```

`targets` maps a category to a target proportion or count (counts are
normalized). Categories missing from the targets keep a weight of 1.0.

## `respondents` — respondent-level helpers

```python
respondents.dedup_responses(df, *, id_col="respondent_id",
                            order_by="submitted_at", keep="last")
    # collapse resumed submissions to one row per respondent

respondents.completion_time(df, *, start_col="started_at",
                            end_col="submitted_at", duration_col="duration_s")
    # -> Series of seconds; prefers an existing duration column, else end - start

respondents.partial_flag(df, required)
    # -> boolean Series: True when any `required` field is null/blank
```

## A complete example script

This is a self-contained `type: analysis` script — clean → weight → tabulate →
report — of the kind you commit to a project and wire up in
[[Project Config (siamang.yaml)|Cloud-siamang-yaml]]:

```python
"""scripts/key_tables.py — clean, weight, and tabulate in one script."""

from siamang_cloud import Report, analysis, db, respondents

# 1. Load raw responses (the `data` JSONB is flattened to columns).
raw = db.table("responses").to_pandas()

# 2. One row per respondent; drop partials and speeders (< 2 minutes).
df = respondents.dedup_responses(raw, id_col="respondent_id")
df["duration_s"] = respondents.completion_time(df)
df["is_partial"] = respondents.partial_flag(
    df, required=["gender", "age_group", "satisfaction"]
)
df = df[~df["is_partial"]]
df = df[df["duration_s"].isna() | (df["duration_s"] >= 120)]
db.write_table("clean_responses", df.drop(columns=["is_partial"]), if_exists="replace")

# 3. Rake the sample to census margins so estimates generalise.
CENSUS = {
    "gender":    {1: 0.49, 2: 0.48, 3: 0.03},
    "age_group": {1: 0.32, 2: 0.36, 3: 0.32},
}
df["w"] = analysis.rake_weights(df, CENSUS)

# 4. Weighted frequencies, a crosstab, and a chi-square test.
sat  = analysis.frequencies(df, "satisfaction", weight="w")
ct   = analysis.crosstab(df, "work_mode", "satisfaction", weight="w", normalize="index")
test = analysis.chi2(df, "work_mode", "satisfaction")

# 5. Assemble a report artifact (rendered in the Repository, combined by Run all).
(Report(title="Work & Wellbeing — key tables",
        description="Weighted estimates (raked to census gender × age margins).")
    .heading("Job satisfaction")
    .add(sat, caption="Table 1. Satisfaction, weighted %")
    .heading("Satisfaction by work mode")
    .add(ct, caption="Table 2. Row % within work mode")
    .note(
        f"chi²={test['chi2']:.1f}, dof={test['dof']}, "
        f"p={test['p']:.4f}, Cramér's V={test['cramers_v']:.2f}"
    )
    .save("outputs/key_tables.md"))

print(f"clean_responses: {len(df)} rows; report written to outputs/key_tables.md")
```

Declare it in `siamang.yaml` so the platform can run it and pick up its report:

```yaml
tasks:
  key_tables:
    type: analysis
    entry: scripts/key_tables.py
    description: "Weighted frequencies, crosstab + chi-square"
    report: outputs/key_tables.md
```

## See also

[[Cloud Analysis and Reporting|Cloud-Analysis-and-Reporting]] · [[Report Document|Report-Document]] · [[Cloud Engine Plugin|Cloud-Engine-Plugin]] · [[Project Config (siamang.yaml)|Cloud-siamang-yaml]] · [[Cloud Sandbox and Security|Cloud-Sandbox-and-Security]] · [[Analysis]]
