# Responses and the Data Tab

**Data** is your project's database: the answers as they arrive, the quota
counters, and every table your flows write. This page covers the tables and
their columns, browsing and filtering, instant insights, deleting a response
for an erasure request, and what to watch when a dataset spans several
versions. Downloads are covered in [[Data Exports|Studio-Data-Exports]];
quality checks in [[Data Quality|Studio-Data-Quality]].

---

## The Data screen

```
┌ Tables ─────────┬ responses  1,284 rows   [All][Completed][Partial] Filter loaded rows…     [Data|Schema|Insights] ┐
│ ▦ clean_        │ Showing the first 100 of 1,284 rows. Filtering and sorting search only what is loaded —      │
│   responses 1,190│ exports always use the whole table.                                                          │
│ ▦ quota_        │ q1_age  q2_region  q3_aware  …  id    survey_id     meta             partial  created_at     │
│   counters   6  │ 34      2          1         …  1     3f9a1c07b2de  {"started_at"…}  false    2026-06-04 …   │
│ ▦ responses 1,284│ …                                                                          [Delete]        │
│ ▦ survey_meta 2 │ [Prev]  Showing 1–25 of 100 rows  [Next]                                  [Export ▾]      │
└─────────────────┴───────────────────────────────────────────────────────────────────────────────────────────────┘
```

- The rail on the left, **Tables**, lists every table of the project with its
  row count (for large tables the count is an estimate).
- The bar shows the table's name and row count, the quick filters, the search
  field and the three views: **Data**, **Schema**, **Insights**.

Every member of the organization can open Data and export.

---

## The tables

| Table | What it holds |
|---|---|
| `responses` | one row per interview: the answers plus fieldwork metadata |
| `quota_counters` | one row per quota cell and environment: `survey_id`, `variable`, `value`, `target`, `current` |
| `survey_meta` | one row per environment: the title and codebook of its latest build (`survey_id`, `title`, `schema_json`, `variables_json`, `max_responses`, `schema_hash`, `created_at`) |
| *your own* | anything a flow's **Write table** node produced (`clean_responses`, `weighted`, …) |

In `quota_counters`, `value` is stored in JSON form — a text answer appears
with quotes (`"north"`), a code without (`2`).

### The responses table

In the grid, the answers are spread into **one column per variable**, followed
by the table's own columns:

| Column | Meaning |
|---|---|
| *one per variable* | the answers (`q1_age`, `q2_region`, …); a matrix contributes one column per row |
| `__status` | how the interview ended, when it ended on a special page: `completed`, `screened_out` or `redirect` |
| `id` | the response's row number — the **Response ID** the respondent saw on the thank-you page |
| `survey_id` | the environment that collected it (the 12-character id in the survey link) |
| `meta` | fieldwork metadata, as JSON (below) |
| `respondent_id` | a random id that ties an interview's progress saves to its final submission |
| `partial` | `true` while the interview is unfinished |
| `created_at` / `updated_at` | first and last write |

If one of your variables is called like a table column (`id`, `partial`, …),
the variable keeps the name and the table column gets an underscore (`_id`).

Answer columns appear in the order the database returns them — shorter names
first — not in questionnaire order. Flows and exports can reorder them.

### Fieldwork metadata

The `meta` column holds what the survey page recorded about the interview —
never a variable of the questionnaire:

| Key | Meaning |
|---|---|
| `started_at` | when the page was opened |
| `duration_seconds` | seconds from opening to this save |
| `last_page` | the page the respondent was on |
| `url_<name>` | each URL parameter of the link, up to 8 (`url_source`, `url_inv` for an invitation, `url_prolific_pid` for a Prolific id) |
| `tab_switches`, `hidden_seconds`, `pastes` | how often the respondent left the tab, for how long in total, how many times they pasted |
| `captcha` | `pass` or `unavailable`, written by Studio when the captcha is on |

In **Flows**, these arrive as ordinary columns: `url_*`, `duration_s`,
`started_at`, `captcha`, `tab_switches`, `hidden_seconds`, `pastes`. Exports
from the Data tab leave `meta` out.

### Partial responses

A **partial** row is an interview that has started and not been submitted.
The survey sends the answers so far each time the respondent changes page or
leaves the tab; the final submission turns the same row into a complete one
(`partial` = `false`). Partials:

- appear in the table, and in every export — filter them out on `partial`;
- do not count toward response caps or quotas;
- feed the drop-off funnel on Distribute.

In a flow, the **Speeders & partials** node drops them (see
[[Cleaning and Weighting Data|Studio-Cleaning-and-Weighting]]).

---

## The Data view

The grid shows **the first 100 rows** of the selected table, 25 per page. A
note above it says so:

- "Showing the first 100 of 1,284 rows. Filtering and sorting search only what
  is loaded — exports always use the whole table."
- "All 87 rows loaded. Exports use the whole table." — for a small table.

> **Current limitation.** The grid cannot page beyond those first 100 rows,
> which are usually the oldest. To look at newer or specific responses in a
> large table, export it, or filter it in a flow.

What you can do with the loaded rows:

- **Sort** — click a column header (again to reverse: ▲ / ▼).
- **Search** — type in **Filter loaded rows…**; it matches any cell, including
  the JSON of `meta`.
- **Quick filters** — chips that appear only when the loaded rows support
  them:

  | Chip | Keeps |
  |---|---|
  | **All** | everything |
  | **Completed** | rows that are not partial (screen-outs included) |
  | **Partial** | unfinished interviews |
  | **Captcha unavailable** | responses stored without a captcha token |
  | **Quality flags** | rows with a non-empty `quality_flags` — in tables written by a flow with the **Response quality** node |

- **Page** — **Prev** / **Next**, "Showing 1–25 of 100 rows" (or "… of 12
  filtered rows").

Empty cells show `—`; numeric columns are right-aligned. With no match: "No
loaded rows match this filter." and **Clear filter**. An empty table: "No data
yet — This table has no rows. Deploy a survey and collect responses to
populate it." with **Open Distribute →**.

The grid loads when you open Data or pick a table; switch tables or reopen the
tab to see new responses.

---

## The Schema view

**Schema** lists the table's columns as stored — **column**, **type**,
**nullable** (yes/no). For `responses` that is the storage layout (`id`,
`survey_id`, `data`, `meta`, `respondent_id`, `partial`, `created_at`,
`updated_at`, with the answers inside `data`), which is what you need when you
wire a connector or query the table elsewhere.

---

## Insights

**Insights** summarizes the responses without building a flow. The numbers are
computed by the server over the **whole** `responses` table — no sandbox run,
no waiting.

What you see, top to bottom:

1. A stat row: **responses**, **respondents**, **partial** (with its share),
   **last response**.
2. **Responses per day · last 14 days** (hidden while all days are zero).
3. **Pinned** widgets, if the project defines any.
4. **Explore frequencies** — pick a variable; you get the distribution as bars
   with percentages.
5. **Explore crosstab** — pick a row and a column variable; you get counts with
   row and column totals (**Σ**), shaded by size. Picking the same variable
   twice: "Pick two different variables."

| Rule | Detail |
|---|---|
| Which responses | **all** rows of all environments (`pilot` and `main` together), **including partial interviews**. For completed-only, weighted or filtered results, use [[Flows\|Studio-Flows]] |
| Frequencies | the 50 most frequent values; percentages are of all responses |
| Crosstabs | up to 2,500 cells; totals always cover all responses |
| Unanswered | shown as `—` |
| Variables offered | those of your published questionnaire |

For a question with several answers per respondent (multiple choice), the
tables count each option once per respondent and say so:

- frequencies: "Multiple answers allowed · base N respondents who answered ·
  percentages are of respondents, so they sum above 100%"
- crosstabs: "Multiple answers allowed · Σ counts respondents, not cells, so
  the cells sum above it · each column Σ is that column's own base"

With no responses at all: "No responses yet — Deploy the survey and collected
answers are charted here." with **Open Distribute →**. A chart that fails to
load says "Could not load this chart." with **Retry**.

### Pinned widgets

Pinned widgets appear for everyone on the project, under **Pinned from
studio/settings.json**. They are declared in the `insights` list of
`studio/settings.json` (there is no editor for this list in the beta):

```json
"insights": [
  { "type": "frequency", "variable": "q2_region", "title": "Region" },
  { "type": "crosstab",  "rows": "q2_region", "cols": "q3_aware", "title": "Awareness by region" }
]
```

Only `frequency` and `crosstab` widgets are drawn.

---

## Deleting a response

Owners and admins can erase a single response — the path for a GDPR erasure
or withdrawal request.

1. Find the row in the `responses` table (see below).
2. Click **Delete** at the end of the row (tooltip "Delete response (GDPR)").
3. Confirm:

   > **Delete response** — "Erase response #4817 from responses, including its
   > answers and its metadata." — "Permanent, and the intent: this is the GDPR
   > erasure path, so there is no trash and no recovery window. Your response
   > counts and any quota it filled do not go back." → **Delete**

The row is removed at once (toast **Response deleted**) and the deletion is
recorded in the project's activity log — as `response.delete` with the row
number, without the content.

- The **Delete** button appears only in the `responses` table. Members see it
  too, but only **owners and admins** can delete; for a member the attempt
  fails.
- Quota counters and invitation statuses are **not** rolled back. Adjust a
  quota target if it matters.
- Copies you already exported, or tables a flow wrote from the responses, are
  not touched: delete the respondent there too, and re-run the flows.

### Finding a respondent

- **By Response ID.** The thank-you page shows the respondent a **Response
  ID** — the `id` column. Asking for it is the simplest route.
- **In the grid.** Search **Filter loaded rows…** for the id, a panel id or an
  invitation token — this works when the row is among the first 100 loaded.
- **In a large table.** Export the table (CSV) or use a flow to find the row's
  `id` — by `url_<name>` for a panel id, or by answers the respondent can
  describe — then locate it for deletion.
- **Invitations.** Invited respondents carry their token in `meta` as
  `url_inv`. The recipients list on Distribute shows names and statuses, not
  tokens, so identify invited respondents by what they tell you (their Response
  ID) or through the API.

---

## Response caps

A response cap refuses submissions once an environment has that many
completed responses (screen-outs included). New projects start with `pilot`
capped at 50 and `main` at 1,200; the Free plan adds 1,000 per environment. The
refusal happens when the respondent submits. Details:
[Response caps](Studio-Publishing-and-Environments#response-caps).

---

## Data from more than one version

A dataset can contain answers collected under different Saves: every
republish keeps the environment's link and `survey_id`, and responses do not
record which Save collected them. To see which version was in the field when,
compare `created_at` with the publish times in **Settings → Activity** (its
**Export CSV** includes each publish's Save number). Watch for:

- a variable renamed mid-field — two columns where you expect one;
- an option code that changed meaning;
- a question added later — empty for earlier respondents.

Harmonize in a flow with **Recode** / **Select columns** rather than by
editing the raw table, so the fix is documented and reproducible. SPSS and
Stata exports take their labels from the **current** Save.

---

## Retention

Responses are kept until you delete them — one by one, as above, or with the
whole project (**Settings → Danger Zone**, owners and admins), which removes
its database immediately and replaces its published surveys with the closed
page. There is no automatic deletion after a period.

---

## Getting data out

- **Export** at the bottom right of the grid — CSV, Excel, SPSS, Parquet,
  SQLite: [[Data Exports|Studio-Data-Exports]].
- **Connectors** push a table to Sheets, Excel 365, warehouses and more:
  [[Connectors|Studio-Connectors]].
- The **research bundle** packages data, code and codebook:
  [[Reproducibility|Studio-Reproducibility]].
- The **API** lets a script pull exports: [[API and API Keys|Studio-API-and-API-Keys]].

## See also

- [[Data Exports|Studio-Data-Exports]]
- [[Data Quality|Studio-Data-Quality]]
- [[What Respondents See|Studio-Respondent-Experience]]
- [[Analysis Flows|Studio-Flows]]
- [[Security and Privacy|Studio-Security-and-Privacy]]
