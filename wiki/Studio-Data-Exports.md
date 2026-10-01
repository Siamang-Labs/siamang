# Data Exports

**Export** on the Data tab downloads a whole table as CSV, Excel, SPSS, Stata,
Parquet or SQLite. This page describes exactly what each file contains, what
every export includes and leaves out, how multiple answers are written, the
size limit, and the other ways to get data out of Studio.

---

## Exporting a table

1. Open **Data** and pick the table in the rail (`responses`, a table a flow
   wrote, `quota_counters`, …).
2. Click **Export ▾** at the bottom right of the grid.
3. Choose **CSV**, **Excel**, **SPSS**, **Stata**, **Parquet** or **SQLite**.

A toast says **Preparing responses.csv…**, then **Exported responses.csv**. The
file is named after the table (`responses.sav`, `responses.dta`,
`clean_responses.xlsx`, …).

The export always contains the **whole table** — not just the 100 rows the
grid shows, and regardless of the grid's search, sort or quick filters.

If an export fails, the reason stays under the grid with a **Retry** button
(e.g. **Retry CSV**) until you dismiss it. A file the format cannot hold is
refused with a reason rather than a server error, for example "The table
cannot be written as .dta: …" or "The table cannot be written as Parquet: …".

Every member of the organization can export; exports are not limited by plan.
Each export is recorded in the project's activity log (**Settings →
Activity**) as `data.export`, with the table, the format and the number of
rows — never the data.

---

## What every export contains

For the `responses` table, in this order:

| Included | Notes |
|---|---|
| one column per variable, in the questionnaire's order | the answers as codes, each column named after its variable (not the question's Id), in the order the current Save asks them. A matrix gives one column per row (the chosen column's code); a Multiple choice in the wide layout one column per choice (`1` chosen, `0` offered and not chosen, empty when not answered or when the option was hidden from the respondent). "Other (please specify)" is the Other code (`-66` unless the question names another) in the question's column and the typed text in `<variable>_other`, right after it; "None of the above" is `-77`; "Not applicable" the declared not-applicable code (`-1` from the Builder). See [Codes for Other, None of the above and N/A](Studio-Question-Types#codes-for-other-none-of-the-above-and-na) |
| codebook-only variables | variables no question asks — hidden, computed or assigned ones, such as an experimental arm — right after the questions |
| other answer keys | `__status` (`completed`, `screened_out` or `redirect` for interviews that ended on a special page; empty otherwise), a column left under an old Id, a flag a custom script wrote |
| `url_<name>` | each URL parameter the link carried: a source tag, a panel id (`url_prolific_pid`), the invitation token (`url_inv`) |
| `duration_s`, `started_at` | seconds from opening the page to the last save, and when the page was opened |
| `captcha` | `pass` or `unavailable`, when the captcha is on |
| `tab_switches`, `hidden_seconds`, `pastes` | the behavioral counts (see [[Data Quality\|Studio-Data-Quality]]) |
| `id` | the row number (the respondent's **Response ID**) |
| `survey_id` | the environment that collected the row |
| `respondent_id` | the random id of the interview |
| `partial` | `true` for unfinished interviews |
| `created_at`, `updated_at` | first and last write |

- **All rows**: completed **and partial** interviews, from **all
  environments** (`pilot` and `main` together). Filter before you analyze:
  `partial` = `false` for submitted interviews, `survey_id` for one
  environment (it is the 12-character id in that environment's link),
  `__status` ≠ `screened_out` to drop screen-outs.
- **Fieldwork columns.** The metadata columns carry the names a flow gives
  them, so a downloaded file and a flow's data agree. A column appears when
  at least one row has the value (a survey without the captcha has no
  `captcha` column). If one of your variables has the same name as one of
  them (say, a variable `duration_s`), the answer wins in the rows that hold
  one, and the other rows keep the metadata value. `last_page` is not
  exported: it belongs to the drop-off funnel.
- **Personal data.** The `url_*` columns include panel ids and invitation
  tokens, which tie a response to a person. Treat a Data export accordingly. A
  [research bundle](Studio-Reproducibility#the-research-bundle) leaves out the
  parameters no flow reads, and never carries the invitation token.
- If a variable is named like a table column (`id`, `partial`, …), the
  variable keeps the name and the table column becomes `_id`, `_partial`, ….
- **Responses collected by an older survey build** are written in the same
  layout as new ones: a matrix stored as one object becomes one column per row
  with the column's code (a 0–10 scale stored as 1–11 is written 0–10), a wide
  Multiple choice stored as one list becomes 0/1 per choice, Other stored as
  `__other__` becomes the Other code plus `<variable>_other`, `__none__` the
  None code, `na` the declared not-applicable code (still `na` without one),
  and script flags stored under `__flags__` become columns (`speeder`). The
  survey page's internal columns (`__options__`, `__pages__`, `__errors__`,
  `__timers__`) no longer appear. An export you make now can therefore differ
  from one you downloaded earlier for the same responses. See
  [Older surveys and responses](Studio-Question-Types#older-surveys-and-responses).
- Answers collected by earlier versions of Studio under a question's Id have
  been moved to the variable's column; the few that could not be moved safely
  stay in a column named after the Id (see
  [The responses table](Studio-Responses-and-Data#the-responses-table)).

Other tables — `quota_counters`, `survey_meta`, the tables your flows write —
are exported as they are, column for column.

### Multiple answers

| Answer | CSV, Excel, SPSS, Stata, SQLite | Parquet |
|---|---|---|
| multiple choice (several codes) | codes joined with `;` — `1;3` | a real list — `[1, 3]` |
| unanswered | empty cell | missing |
| other structured answers | JSON text | JSON text |

The `1;3` form is the same one the engine and a flow's **Export file** node
write, so every file of a project spells multiple answers the same way. (A
Multiple choice in the wide layout has no list to write: it is one 0/1 column
per choice.)

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
- **value labels** (including the labels you give missing codes in the
  Codebook, e.g. `-9 Refused`),
- **declared missing values**,
- the **measurement level** (nominal, ordinal, scale).

The labels come from the **current Save** of the questionnaire — not from the
version that collected the data. If you renamed a variable or changed codes
mid-field, older responses are labeled with today's codebook (see
[Data from more than one version](Studio-Responses-and-Data#data-from-more-than-one-version)).
The codes Studio adds for Other, None of the above and N/A carry their labels
("Other", "None of the above", "Not applicable" as a declared missing code),
and a `<variable>_other` column has its own variable label. Columns that are
not questionnaire variables (`id`, `survey_id`, the `url_*` and other
fieldwork columns, …) are written without labels. If the questionnaire cannot
be read, the file is still produced, unlabeled.

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
- A Parquet column holds one type. When a column does not — text next to
  numbers (for example `na` next to codes, where the codebook declares no N/A
  code), or lists next to single values — the whole file is written the way
  the other formats write it: multiple answers as `1;3`, and each column that
  mixes text with numbers as text. A column that mixes `true`/`false` with
  numbers — a script flag such as `speeder`, stored as `true` by an older
  survey build and as `1` by a current one — is written as `1`/`0`.

Good for: Python and R pipelines, large tables, type-faithful archiving.

### SQLite

- One `.sqlite` file with a single table named **`data`**.
- Timestamps as text (`2026-06-04 14:41:07+0000`).

Good for: one file with the whole table, queryable offline with any SQLite
tool.

### Stata (.dta)

- Labeled like the SPSS file: variable labels, value labels, declared missing
  values, from the **current Save**.
- Names follow the SPSS rules above, cut at **32** characters (Stata's limit);
  names that clash after the cut get `_1`, `_2`, ….
- Timestamps are written without time zone.
- A missing text answer is written as an empty string, which is how Stata
  stores a missing string anyway. Long open answers (2,045 characters and more)
  are written as Stata long strings, next to skipped ones.

Good for: Stata, with labels ready. A flow's **Export file** node with
**Format** **Stata (.dta)** writes a labeled Stata file of the data at that
point of the flow. (The **Simulate** mode of **Builder → Test** downloads *simulated*
responses as CSV, Excel, SPSS, Stata or Parquet — useful for preparing your
analysis before fieldwork, but it is not your data.)

### From a flow: R and the codebook

The Data tab exports the table as it is stored. A flow's **Export file** node
writes the data as it is at that point of the flow — after cleaning,
recoding and weighting, with the variables the flow made. You type the
file's name in its **File name** field, such as `clean` (the field keeps
`outputs/` and the ending fixed), and choose what it writes in **Format**:

| Format | Files written for the name `clean` (under **Files**, `outputs/<flow>/`) |
|---|---|
| **CSV (.csv)**, **Excel (.xlsx)**, **Parquet (.parquet)** | the data and `clean.dictionary.json` |
| **SPSS (.sav)**, **Stata (.dta)** | labeled SPSS or Stata data and `clean.dictionary.json` |
| **R bundle (.R)** | `clean.csv`, `clean.dictionary.json` and the script `clean.R` |
| **Codebook only (.json)** | the codebook alone, no data |

A node added from the palette writes `<flow>_data.csv`. There is no `.xls`:
a name typed with it is answered "Choose Excel (.xlsx): an .xls name would
hold an .xlsx workbook, and Excel warns about that.", with a one-click fix. A
single run of the flow keeps these files under **Files**; **Run all** keeps
them only when the flow lists them among its outputs, as the example study's
flows do, and the line under **File name** says which (see
[What Run all keeps](Studio-Flows#what-run-all-keeps)).

`clean.R` reads `clean.csv` (UTF-8) and its dictionary with the `jsonlite`
package into a data frame `survey_data`: the codebook's missing codes become
`NA`, labeled codes become factors (a code without a label keeps a level of
its own), each column's `label` attribute is the variable's label from the
codebook (not the question's text), and
multiple-choice columns (`1;3`) stay text. Put the three files in one folder
and run `Rscript clean.R`, or `source("clean.R")` from R — the script finds
its files beside itself. See
[Export the cleaned data for R](Studio-Recipes#export-the-cleaned-data-for-r).
The [example study](Studio-Projects#the-example-study)'s flow `cleaning`
writes one: `outputs/cleaning/clean_responses.R`, `clean_responses.csv` and
`clean_responses.dictionary.json` in **Files**, the cleaned responses with
their weight — kept by a run of the flow and by **Run all** alike, since that
flow lists them among its outputs.

An `.xlsx` a flow writes keeps text as text: an open answer such as
`=HYPERLINK(…)` stays the string it is, never a formula Excel would run —
as in the Data tab's Excel export.

### From a flow: a report's tables in Excel

Where the data exports above give the answers, a report's tables give the
results. Check **Also save tables to Excel** on a flow's **Save report** node
(**Also Excel** in the Report view) and each run writes, beside the report,
`outputs/<flow>/<report>.xlsx`:

- a **Contents** sheet with the report's title and one linked row per table
  (**Sheet**, **Section**, **Table**);
- one sheet per table of the report — frequencies, crosstabs, banners with
  their significance letters, group means (their post-hoc pairs on a sheet of
  their own), test and model tables — named by the table's caption, each with
  its statistics under it; numbers are numbers, text is text;
- no charts, and no statistics wired into a section as a line of their own.

Download it from **Reports** (**Excel**), from **Files** or from the run's
card; a **Run all** keeps it too. See
[Tables in Excel](Studio-Reports#tables-in-excel).

### From a flow: a tab book

A **Tab book (Excel)** node writes every question of the study crossed by a
banner of segments into one workbook — the file a client asks for after
fieldwork. With **Banner** `gender, region` and **Questions** left empty, a
run writes the workbook named in its **File name** — `<flow>_tabbook` for a
node added from the palette, so `outputs/<flow>/<flow>_tabbook.xlsx` under
**Files**:

- a **Contents** sheet: one linked row per question (**#**, **Question**,
  **Variable**, **Base**, **Sheet**) and the questions it did not tabulate,
  with why (an open answer, a ranking, a question nobody answered);
- one sheet per question, named after its variable: **Total**, then a column
  per answer of each banner variable, lettered (`Male (A)`, `Female (B)`, …,
  `Capital (D)`, …); the **Base** of each column; each answer's count and
  column percentage with its significance letters in the cell beside it; the
  mean and standard deviation of a number you named; footnotes;
- a **Notes** sheet on the weight, the test, the level, the correction, the
  minimum base, the missing codes left out and the date.

The codebook's missing codes are left out and counted, a weighted run shows
both bases, numbers are numbers and text stays text (an answer that begins
with `=` is never a formula). Download it from **Reports** (the **Tab book**
entry), from **Files** or from the run's card; **Run all** keeps it too. See
[Tab book (Excel)](Studio-Node-Reference#tab-book-excel) and
[Tab books](Studio-Reports#tab-books).

---

## Size limit

A Data-tab export produces at most **100,000 rows**. A larger table is
refused with: "This table exceeds the synchronous export limit of 100,000
rows. No file was generated; use a database export for the complete dataset."
No partial file is produced.

For larger tables, use a flow: **Responses** (or **Project table**) →
**Export file** writes the file during a run of that flow; it appears in the
run's outputs and under [[Files|Studio-Files]]. Connectors and a research bundle that
includes the responses are limited to 100,000 rows as well.

---

## Other routes out

| Route | What you get | Page |
|---|---|---|
| Flow **Export file** node | `.csv`, `.xlsx`, `.sav`, `.dta` or `.parquet` of the data at that point of the flow — cleaned, weighted, with `url_*` and timing columns — plus its data dictionary; or an R bundle (`.R`), or the codebook alone (`.json`) — see [From a flow: R and the codebook](#from-a-flow-r-and-the-codebook) | [[Analysis Flows\|Studio-Flows]], [[Node Reference\|Studio-Node-Reference]] |
| Flow **Write table** node | a new project table, which you can export from Data | [[Analysis Flows\|Studio-Flows]] |
| Flow **Save report** node, **Also save tables to Excel** | every table of the report in one `.xlsx` beside it, a sheet per table with its statistics, and a Contents sheet — see [From a flow: a report's tables in Excel](#from-a-flow-a-reports-tables-in-excel) | [[Reports\|Studio-Reports]] |
| Flow **Tab book (Excel)** node | every question by a banner of segments in one `.xlsx` — a sheet per question with bases, counts, percentages and significance letters, a Contents and a Notes sheet — see [From a flow: a tab book](#from-a-flow-a-tab-book) | [[Reports\|Studio-Reports]] |
| Connectors *(Plus; some targets Pro)* | a table pushed to Google Sheets, Excel 365, Supabase, Airtable, Dropbox, HubSpot *(Plus)*, or S3, GCS, Azure, BigQuery, Snowflake, your own database, SFTP, REDCap, Salesforce, HTTP *(Pro)* | [[Connectors\|Studio-Connectors]] |
| Research bundle | data, questionnaire, code, codebook and a provenance file in one zip — the export for a co-author or a paper. Its data files keep the fieldwork columns but only the `url_*` parameters a flow reads, and never the invitation token | [[Reproducibility\|Studio-Reproducibility]] |
| API | the same exports for a script, with an API key | [[API and API Keys\|Studio-API-and-API-Keys]] |

## See also

- [[Responses and the Data Tab|Studio-Responses-and-Data]]
- [[Codebook and Variables|Studio-Codebook-and-Variables]]
- [[Cleaning and Weighting Data|Studio-Cleaning-and-Weighting]]
- [[Reproducibility: Code, Bundles and Citation|Studio-Reproducibility]]

<!-- studio-nav -->
---

← [[Responses and the Data Tab|Studio-Responses-and-Data]] · [Studio contents](Studio-Overview#all-pages) · [[Data Quality|Studio-Data-Quality]] →
