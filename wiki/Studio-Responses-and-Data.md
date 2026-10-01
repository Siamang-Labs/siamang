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
┌ Tables ─────────┬ responses  1,284 rows  [All][Completed][Partial] Filter loaded rows… [Search all rows] [Data|Schema|Insights] ┐
│ ▦ clean_        │ Showing the newest 100 of 1,284 rows. Filtering and sorting work on what is loaded; press Enter or   │
│   responses 1,190│ “Search all rows” to search the whole table — exports always use the whole table.                  │
│ ▦ quota_        │ q1_age  q2_region  q3_aware  …  id    survey_id     meta             partial  created_at     │
│   counters   6  │ 34      2          1         …  1284  3f9a1c07b2de  {"started_at"…}  false    2026-06-04 …   │
│ ▦ responses 1,284│ …                                                                          [Delete]        │
│ ▦ survey_meta 2 │ [Prev]  Showing 1–25 of 100 rows  [Next]                                  [Export ▾]      │
└─────────────────┴───────────────────────────────────────────────────────────────────────────────────────────────┘
```

- The rail on the left, **Tables**, lists every table of the project with its
  row count (for large tables the count is an estimate; `—` while it is not
  known).
- The bar shows the table's name and row count (**N rows loaded** when the
  count is not known), the quick filters, the search field (with **Search all
  rows** once you type) and the three views: **Data**, **Schema**,
  **Insights**.

Every member of the organization can open Data and export. Deleting a response
is for owners and admins (see [Deleting a response](#deleting-a-response)).

---

## The tables

| Table | What it holds |
|---|---|
| `responses` | one row per interview: the answers plus fieldwork metadata |
| `quota_counters` | one row per quota cell and environment: `survey_id`, `variable`, `value`, `target`, `current` |
| `survey_meta` | one row per environment: the title and codebook of its latest build (`survey_id`, `title`, `schema_json`, `variables_json`, `max_responses`, `schema_hash`, `created_at`) |
| *your own* | anything a flow's **Write table** node produced (`clean_responses`, `weighted`, …) |

Data collected elsewhere — a panel file, an earlier wave, a Qualtrics
export — never goes into `responses`. It is uploaded under
[[Files|Studio-Files]] and read by a flow's **Data file** node; a **Write
table** node below it can keep it here as a table of your own, with the
file's column names as they are (`StartDate`, a Russian header). A name
longer than 63 bytes (a Cyrillic letter takes two) cannot be a table column:
the node stops before writing anything, and you rename that column first. See
[Analyzing a dataset collected elsewhere](Studio-Files#analyzing-a-dataset-collected-elsewhere).

In `quota_counters`, `value` is stored in JSON form — a text answer appears
with quotes (`"north"`), a code without (`2`).

### The responses table

In the grid, the answers are spread into **one column per variable**, followed
by the table's own columns:

| Column | Meaning |
|---|---|
| *one per variable* | the answers (`q1_age`, `q2_region`, …), as codes. A matrix contributes one column per row, holding the chosen column's code (a 0–10 scale stores 0–10); a MaxDiff one column per pick and a conjoint one per task, each plus its design version; a Multiple choice in the wide layout one column per choice (`1` chosen, `0` offered and not chosen, empty when the question was not answered or the option was hidden from the respondent) |
| `<variable>_other` | the text typed for "Other (please specify)", next to its question's column, which holds the Other code (`-66` unless the question names another). "None of the above" is a code too (`-77`), and "Not applicable" the variable's declared not-applicable code (`-1` when set up in the Builder) — see [Codes for Other, None of the above and N/A](Studio-Question-Types#codes-for-other-none-of-the-above-and-na) |
| `__status` | how the interview ended, when it ended on a special page: `completed`, `screened_out` or `redirect` |
| `id` | the response's row number — the **Response ID** the respondent saw on the thank-you page |
| `survey_id` | the environment that collected it (the 12-character id in the survey link) |
| `meta` | fieldwork metadata, as JSON (below) |
| `respondent_id` | a random id that ties an interview's progress saves to its final submission |
| `partial` | `true` while the interview is unfinished |
| `created_at` / `updated_at` | first and last write |

If one of your variables is called like a table column (`id`, `partial`, …),
the variable keeps the name and the table column gets an underscore (`_id`).

Answers are stored under their **variable name** — the name in the Codebook —
not under the question's **Id**, so a column is called after the variable
even when the two names differ (a preset's Id `q5` and variable `nps_5` give
the column `nps_5`). See
[Question Id and variable name](Studio-Builder-Overview#question-id-and-variable-name).

> **Note — responses collected before this rule.** Earlier versions of Studio
> stored a single-answer question's answer under its Id. Studio has moved the
> answers already collected that way to the variable's column, once, and
> recounted the quota cells involved. Where the move could have mixed two
> questions' answers (for example, an Id that is also another question's
> variable), the answers stayed under the Id, so you may still see such a
> column next to the variable's. Surveys published before the change keep
> sending answers under the Id; Studio files each of them under the variable
> as it arrives, so no new rows land in the old column. (Their conditions,
> branching and piping on such questions work only once you
> [republish](Studio-Publishing-and-Environments#republishing).)

Answer columns follow the **questionnaire's order** — that of the current
Save: each question's variables page by page, a `<variable>_other` column right
after its variable, then the codebook's variables no question asks (hidden,
computed or assigned ones, such as an experimental arm), then any other keys
the rows hold (`__status`, a column left under an old Id, a flag a custom
script wrote) in the order they first appear. Exports use the same order.

**Responses collected by an older survey build** are shown in this same
layout, so old and new rows share their columns: a matrix stored as one object
becomes one column per row with the column's code (a 0–10 scale stored as
1–11 reads 0–10), a wide Multiple choice stored as a list becomes 0/1 per
choice, Other stored as `__other__` becomes the Other code plus the
`<variable>_other` text, `__none__` becomes the None code, `na` becomes the
declared not-applicable code (it stays `na` while the codebook declares none),
and flags a custom script wrote under `__flags__` (for example `speeder`) are
columns of their own. The survey page's internal bookkeeping that older builds
stored with every response (`__options__`, `__pages__`, `__errors__`,
`__timers__`) is not shown. The stored rows are not rewritten: the grid,
exports, flows and the research bundle all read them this way. See
[Older surveys and responses](Studio-Question-Types#older-surveys-and-responses).

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

The grid shows `meta` as it is stored, as JSON. In **exports** from the Data
tab and in **Flows**, these keys arrive as ordinary columns: `url_*`,
`duration_s` (from `duration_seconds`), `started_at`, `captcha`,
`tab_switches`, `hidden_seconds`, `pastes`. `last_page` stays in `meta`: it
feeds the drop-off funnel. See [[Data Exports|Studio-Data-Exports]].

### Partial responses

A **partial** row is an interview that has started and not been submitted.
The survey sends the answers so far each time the respondent changes page or
leaves the tab; the final submission turns the same row into a complete one
(`partial` = `false`). Partials:

- appear in the table, and in every export — filter them out on `partial`;
- do not count toward response caps or quotas;
- feed the drop-off funnel on Distribute and an invitation's `started` status;
- have a rate limit of their own, apart from final submissions (60 a minute
  per survey and network address each, and the same again for quota checks),
  so a class or an office answering from one network address does not use up
  what its submissions need (see
  [[Limits and Quotas at a Glance|Studio-Limits-Reference]]);
- include respondents whom a full quota cell stopped, with the answers the
  survey had sent before they were stopped (someone stopped on leaving the
  first page has usually sent nothing yet, and leaves no row).

Partial rows come only from a survey built with the current runtime. An
environment published before it sends none — its table holds submitted
responses only — until you
[republish](Studio-Publishing-and-Environments#republishing) it.

In a flow, **Only completed responses** on the **Responses** node leaves them
out (see [[Cleaning and Weighting Data|Studio-Cleaning-and-Weighting]]).

---

## The Data view

The grid loads **100 rows** of the selected table, **newest first**, and shows
them 25 per page. In `responses` that means the most recently started
interviews (by `created_at`) come first, so new interviews appear at the top.
A table a flow wrote is ordered the same way when it has a `created_at` or
`id` column; otherwise its rows come in the order the database returns them. A
note above the grid says what is loaded:

- "Showing the newest 100 of 1,284 rows. Filtering and sorting work on what is
  loaded; press Enter or “Search all rows” to search the whole table — exports
  always use the whole table."
- "All 87 rows loaded. Exports use the whole table." — for a small table.
- "87 rows loaded. Filtering and sorting search only what is loaded — exports
  always use the whole table." — when the table's row count is not known.

### Searching the whole table

Type in **Filter loaded rows…** and press `Enter`, or click **Search all
rows** (tooltip "Search every row of the table on the server, not only the
rows loaded here"). Studio searches **every row** of the table and loads the
newest 100 that match. A row matches when any of its values contains the text,
upper or lower case alike — an answer, the response `id`, the `respondent_id`,
or a value inside `meta` such as a panel id or an invitation token. The
survey's own texts that older builds stored with each response (option labels,
page titles) are not searched, so a word from the questionnaire finds only the
rows whose answers contain it.

The note above the grid then reads "12 rows of the whole table match “8f2a”."
— with "— showing the newest 100" when more match than are loaded — and
**Clear search** goes back to the newest rows.

> **Limitation.** The grid cannot page beyond the 100 rows it loads. To go
> through older responses in a large table, narrow the search, export the
> table, or filter it in a flow.

What you can do with the loaded rows:

- **Sort** — click a column header (again to reverse: ▲ / ▼). Until you do,
  the rows keep the newest-first order.
- **Filter** — typing in **Filter loaded rows…** narrows the loaded rows as
  you type (any cell, including the JSON of `meta`); press `Enter` to search
  the whole table instead.
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

1. A stat row: **responses** (every row — completed, screened-out and partial
   interviews), **completed** (submitted interviews that did not end on a
   Screen-out page — what quota cells and response caps count; the tooltip adds
   how many were screened out), **partial** (with its share), **last
   response**. Each interview counts on its own: Studio cannot tell whether
   two responses came from the same person.
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
| Frequencies | the 50 most frequent values; percentages are of all responses. When every answer is a number or a code, the bars come in code order (`0`, `1`, `2` … `10`, no answer last); answers in words come largest first |
| Crosstabs | up to 2,500 cells; totals always cover all responses. Rows and columns that are numbers or codes sort by value, then words, then no answer |
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

> **Note.** Insights counts the answers as they are stored. Responses collected
> by an older survey build keep their older shapes there — a matrix kept as
> one object under the question (its rows then count as unanswered), Other
> kept as `__other__` with its text, `__none__`, `na` — which the Data grid,
> exports and flows translate but Insights does not. For a dataset that spans
> the switch, read those questions in a flow (see
> [Data from more than one version](#data-from-more-than-one-version)).

### Pinned widgets

Pinned widgets appear for everyone on the project, under **Pinned from
studio/settings.json · every response in the table, partial ones included,
unweighted** — a flow's report of the same question reads the cleaned,
weighted data and gives other numbers. They are declared in the `insights`
list of `studio/settings.json` (there is no editor for this list in the
beta):

```json
"insights": [
  { "type": "frequency", "variable": "q2_region", "title": "Region" },
  { "type": "crosstab",  "rows": "q2_region", "cols": "q3_aware", "title": "Awareness by region" }
]
```

Only `frequency` and `crosstab` widgets are drawn.

A project started from the [example study](Studio-Projects#the-example-study)
pins five: *Overall life satisfaction*, *Life satisfaction by age group (1 =
16-29, 2 = 30-44, 3 = 45+)*, *Hours a day on screens*, *Would recommend the
app (0 = not at all likely, 10 = extremely likely)* and *Interest in the app
by message (1 = sleep, 2 = time)*. They count every sample response; the
reports of the example's flows give the same questions for the respondents
who pass its cleaning, weighted.

---

## Deleting a response

Owners and admins can erase a single response — the path for a GDPR erasure
or withdrawal request.

1. Find the row in the `responses` table (see below).
2. Click **Delete** at the end of the row (tooltip "Delete response (GDPR)").
3. Confirm:

   > **Delete response** — "Erase response #4817 from responses, including its
   > answers and its metadata." — "Permanent, and the intent: this is the GDPR
   > erasure path, so there is no trash and no recovery window. The response
   > counts and any quota cell it filled go down with it." → **Delete**

The row is removed at once (toast **Response deleted**) and the deletion is
recorded in the project's activity log — as `response.delete` with the row
number, without the content.

- The **Delete** button appears only in the `responses` table, and only for
  **owners and admins**. Members do not see it; ask an owner or admin to erase
  a response.
- The response counts go down, and the quota cells of that environment are
  recounted from the responses that remain, so a cell that was full because of
  this respondent opens again. Invitation statuses are **not** rolled back.
- Copies you already exported, or tables a flow wrote from the responses, are
  not touched: delete the respondent there too, and re-run the flows.

### Finding a respondent

- **By Response ID.** The thank-you page shows the respondent a **Response
  ID** — the `id` column. Type it in **Filter loaded rows…** and press `Enter`.
- **By a panel id or an invitation token.** Search the whole table the same
  way ([Searching the whole table](#searching-the-whole-table)): the search
  reads the values inside `meta` too, so `url_prolific_pid` or `url_inv`
  values are found in any row, not only the 100 newest.
- **By answers the respondent can describe.** Search for a distinctive open
  answer, or use a flow to find the row's `id`.
- **Invitations.** Invited respondents carry their token in `meta` as
  `url_inv`. The recipients list on Distribute shows names and statuses, not
  tokens, so identify invited respondents by what they tell you (their Response
  ID) or through the API.

---

## Response caps

A response cap stops an environment from taking responses once it has that
many **completed interviews** — submitted and not screened out; partials and
screen-outs do not count. New projects start with `pilot` capped at 50 and
`main` at 1,200; on the Free plan the project as a whole also stops at 1,000,
all environments together. Once a cap is full, new respondents see "Thank you
for your interest" as the page opens, and someone already answering meets it
at submit. Details:
[Response caps](Studio-Publishing-and-Environments#response-caps).

---

## Data from more than one version

A dataset can contain answers collected under different Saves: every
republish keeps the environment's link and `survey_id`, and responses do not
record which Save collected them. To see which version was in the field when,
compare `created_at` with the publish times in **Settings → Activity** (its
**Export CSV** includes each publish's Save number). Watch for:

- a variable renamed mid-field — two columns where you expect one (renaming
  only the **Id** of a single-answer question does not split its column,
  since the answer is stored under the variable name);
- an option code that changed meaning;
- a question added later — empty for earlier respondents.

Harmonize in a flow with **Recode** / **Select columns** rather than by
editing the raw table, so the fix is documented and reproducible. SPSS and
Stata exports take their labels from the **current** Save, and the grid and
exports read older answers with the current Save's questionnaire.

### When an environment switches to the current runtime

Republishing an environment that was built before the latest Studio update
also changes the survey page itself (see
[Republishing](Studio-Publishing-and-Environments#republishing)). In the data:

- **Same columns, same codes.** Responses from before and after the switch are
  read in one layout — matrix codes, Other, None and N/A codes, wide Multiple
  choice as 0/1 per choice (see [The responses table](#the-responses-table)).
  An export you make now can therefore differ from one you downloaded earlier
  for the same responses (`0`–`10` where it said `1`–`11`, `-66` where it said
  `__other__`).
- **Hidden options.** In a wide Multiple choice, an option hidden from the
  respondent by its own condition is empty in new responses but `0` in older
  ones, which cannot tell "hidden" from "not chosen".
- **Partial rows** start to arrive only after the switch, so partial counts
  and the drop-off funnel cover the later period only.
- **Quota cells** count completed interviews only; a cell on a matrix row or
  on one choice of a wide Multiple choice counts only responses collected
  after the switch (see
  [How cells are counted](Studio-Quotas-and-Randomization#how-cells-are-counted)).
- **Seeded randomization.** In an older build, **Assign to a condition** with
  a **Seed** sent every respondent to the same arm, and every respondent of a
  MaxDiff or conjoint saw the same design version. After the switch,
  respondents are spread over the arms by their weights and get different
  design versions, each kept after a reload. Compare arms and design versions
  on the responses collected after the switch.
- **Insights** reads the stored shapes as they are (see the note under
  [Insights](#insights)).

---

## Retention

Responses are kept until you delete them — one by one, as above, or with the
whole project (**Settings → Danger Zone**, owners and admins), which removes
its database immediately and replaces its published surveys with the closed
page. There is no automatic deletion after a period.

---

## Getting data out

- **Export** at the bottom right of the grid — CSV, Excel, SPSS, Stata,
  Parquet, SQLite: [[Data Exports|Studio-Data-Exports]].
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

<!-- studio-nav -->
---

← [[Live Monitoring|Studio-Live-Monitoring]] · [Studio contents](Studio-Overview#all-pages) · [[Data Exports|Studio-Data-Exports]] →
