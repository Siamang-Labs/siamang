# Data Exports

**Export** on the Data tab downloads a whole table as CSV, Excel, SPSS,
Parquet or SQLite. This page describes exactly what each file contains, what
every export includes and leaves out, how multiple answers are written, the
size limit, and the other ways to get data out of Studio.

---

## Exporting a table

1. Open **Data** and pick the table in the rail (`responses`, a table a flow
   wrote, `quota_counters`, …).
2. Click **Export ▾** at the bottom right of the grid.
3. Choose **CSV**, **Excel**, **SPSS**, **Parquet** or **SQLite**.

A toast says **Preparing responses.csv…**, then **Exported responses.csv**. The
file is named after the table (`responses.sav`, `clean_responses.xlsx`, …).

The export always contains the **whole table** — not just the 100 rows the
grid shows, and regardless of the grid's search, sort or quick filters.

If an export fails, the reason stays under the grid with a **Retry** button
(e.g. **Retry CSV**) until you dismiss it.

Every member of the organization can export; exports are not limited by plan.

---

## What every export contains

For the `responses` table:

| Included | Notes |
|---|---|
| one column per variable | the answers; a matrix gives one column per row |
| `__status` | `completed`, `screened_out` or `redirect` for interviews that ended on a special page; empty otherwise |
| `id` | the row number (the respondent's **Response ID**) |
| `survey_id` | the environment that collected the row |
| `respondent_id` | the random id of the interview |
| `partial` | `true` for unfinished interviews |
| `created_at`, `updated_at` | first and last write |

- **All rows**: completed **and partial** interviews, from **all
  environments** (`pilot` and `main` together). Filter before you analyze:
  `partial` = `false` for completed interviews, `survey_id` for one
  environment (it is the 12-character id in that environment's link),
  `__status` ≠ `screened_out` to drop screen-outs.
- **Left out: `meta`.** Timing, the last page, URL parameters (`url_source`,
  panel ids, invitation tokens), behavioral counts and the captcha verdict are
  not in Data exports. They are available in flows as columns (`duration_s`,
  `url_*`, `captcha`, …); use a flow with an **Export file** node to write
  them to a file (see [Other routes out](#other-routes-out)).
- If a variable is named like a table column (`id`, `partial`, …), the
  variable keeps the name and the table column becomes `_id`, `_partial`, ….

### Multiple answers

| Answer | CSV, Excel, SPSS, Stata, SQLite | Parquet |
|---|---|---|
| multiple choice (several codes) | codes joined with `;` — `1;3` | a real list — `[1, 3]` |
| unanswered | empty cell | missing |
| other structured answers | JSON text | JSON text |

The `1;3` form is the same one the engine and a flow's **Export file** node
write, so every file of a project spells multiple answers the same way.

---

## Formats

### CSV

- UTF-8, comma-separated, one header row.
- Timestamps include their time-zone offset.
- **Formula protection.** A text cell (or header) that starts with `=`, `+`,
  `-`, `@`, a tab or a carriage return is written with a leading apostrophe
  (`'=SUM(…)`), so a spreadsheet opens it as text instead of running it.
  Numbers stay numbers; a `-5` that a respondent *typed as text* is also
  prefixed.

Good for: anything, anywhere.

### Excel (.xlsx)

- One sheet, `Sheet1`, with a header row.
- Timestamps without time zone (the stored time, UTC).
- Text that looks like a formula is kept as text, never as a formula.

Good for: colleagues, quick pivots.

### SPSS (.sav)

The file carries the codebook of your questionnaire:

- **variable labels**,
- **value labels** (including labels of missing codes),
- **declared missing values**,
- the **measurement level** (nominal, ordinal, scale).

The labels come from the **current Save** of the questionnaire — not from the
version that collected the data. If you renamed a variable or changed codes
mid-field, older responses are labeled with today's codebook (see
[Data from more than one version](Studio-Responses-and-Data#data-from-more-than-one-version)).
Columns that are not questionnaire variables (`id`, `survey_id`, …) are written
without labels. If the questionnaire cannot be read, the file is still
produced, unlabeled.

Variable names are adjusted to SPSS rules — the same names in every export:

| Rule | Example |
|---|---|
| characters other than letters, digits and `_` become `_` | `q1.a` → `q1_a` |
| a name must start with a letter; otherwise `v_` is prefixed | `1st` → `v_1st`, `__status` → `v___status` |
| SPSS keywords get `v_` (`ALL`, `AND`, `BY`, `EQ`, `GE`, `GT`, `LE`, `LT`, `NE`, `NOT`, `OR`, `TO`, `WITH`) | `by` → `v_by` |
| at most 64 characters | longer names are cut |
| names that clash (SPSS ignores case) get `_1`, `_2`, … | `Q1`, `q1` → `Q1`, `q1_1` |

Timestamps are written without time zone. Good for: SPSS, with labels ready
for tables.

### Parquet

- Column types are kept: numbers, booleans, timestamps with time zone.
- Multiple answers stay lists.

Good for: Python and R pipelines, large tables, type-faithful archiving.

### SQLite

- One `.sqlite` file with a single table named **`data`**.
- Timestamps as text (`2026-06-04 14:41:07+0000`).

Good for: one file with the whole table, queryable offline with any SQLite
tool.

### Stata (.dta)

Stata is not in the Data tab's menu. For your responses:

- a flow with an **Export file** node and a path ending in `.dta` — labeled
  like the SPSS file; or
- the [[API|Studio-API-and-API-Keys]], which offers the same export as the
  Data tab in Stata format too.

Stata names follow the SPSS rules above, cut at 32 characters. (The
**Simulate** mode of **Builder → Test** downloads *simulated* responses as
CSV, Excel, SPSS, Stata or Parquet — useful for preparing your analysis before
fieldwork, but it is not your data.)

---

## Size limit

A Data-tab export produces at most **100,000 rows**. A larger table is
refused with: "This table exceeds the synchronous export limit of 100,000
rows. No file was generated; use a database export for the complete dataset."
No partial file is produced.

For larger tables, use a flow: **Responses** (or **Project table**) →
**Export file** writes the file during a run; it appears in the run's outputs
and under [[Files|Studio-Files]]. Connectors and a research bundle that
includes the responses are limited to 100,000 rows as well.

---

## Other routes out

| Route | What you get | Page |
|---|---|---|
| Flow **Export file** node | `.csv`, `.xlsx`, `.sav`, `.dta` or `.parquet` of the data at that point of the flow — cleaned, weighted, with `url_*` and timing columns — plus its data dictionary | [[Analysis Flows\|Studio-Flows]], [[Node Reference\|Studio-Node-Reference]] |
| Flow **Write table** node | a new project table, which you can export from Data | [[Analysis Flows\|Studio-Flows]] |
| Connectors *(Plus; some targets Pro)* | a table pushed to Google Sheets, Excel 365, Supabase, Airtable, Dropbox, HubSpot *(Plus)*, or S3, GCS, Azure, BigQuery, Snowflake, your own database, SFTP, REDCap, Salesforce, HTTP *(Pro)* | [[Connectors\|Studio-Connectors]] |
| Research bundle | data, questionnaire, code, codebook and a provenance file in one zip — the export for a co-author or a paper | [[Reproducibility\|Studio-Reproducibility]] |
| API | the same exports for a script, with an API key | [[API and API Keys\|Studio-API-and-API-Keys]] |

## See also

- [[Responses and the Data Tab|Studio-Responses-and-Data]]
- [[Codebook and Variables|Studio-Codebook-and-Variables]]
- [[Cleaning and Weighting Data|Studio-Cleaning-and-Weighting]]
- [[Reproducibility: Code, Bundles and Citation|Studio-Reproducibility]]
