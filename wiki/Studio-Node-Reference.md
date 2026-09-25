# Node Reference

Every node in the Flows palette: what it does, what it takes and gives, and
every parameter with its exact label, default and allowed values. Use it
alongside [[Analysis Flows|Studio-Flows]], which explains the canvas, and
[[Cleaning and Weighting Data|Studio-Cleaning-and-Weighting]], which puts the
preparation nodes in order.

The palette is served by the engine, so this list is the engine's own: 46
nodes in five groups — **Sources** (4), **Prepare** (14), **Analyze** (17),
**Visualize** (4) and **Output** (7). Within each group the nodes appear here in
the palette's order. Each palette item shows the node's title and a short
name (the part after the dot below, e.g. `crosstab`); nodes that need the
project database also say `· platform`.

---

## Reading this page

**Ports.** Every node lists what it takes in and what it gives out, with the
port's name and type:

| Type | What flows through |
|---|---|
| **SurveyData** | the dataset *plus* its codebook and questionnaire — which is why tables come out labeled |
| **Table** | a frequency table, crosstab, group-means table, banner, coefficient table… |
| **Chart** | a bar chart, box plot, heatmap or scatter plot |
| **Stat** | a test result or a set of statistics (χ², p-values, CIs, model fit) |
| **Report** | a report section or a whole report |
| **Any** | anything — only the **Live tile** input accepts every type |

Weights, recodes, flags and derived variables are *columns inside*
SurveyData, not separate wires.

**Parameters.** "required" in the Default column means the node reports an
error until you fill it in. The inspector marks every other parameter
*optional*. Types:

| Type | How you set it in the inspector |
|---|---|
| variable | a dropdown of the variables available at this node (`name — label`), filtered to the scales the node accepts |
| variables (several) | a checklist of the same variables, filtered the same way |
| choice | a dropdown of the allowed values (**— default —** leaves the default) |
| whole number, number | a number box; the placeholder shows the default |
| checkbox | ticked = on |
| text | a text box; where the text names a new variable or column, the hint says "names a new variable" |
| JSON object, JSON | a text box that must contain valid JSON; it is read when you leave the box, and a parse error is shown under it |
| condition | the Builder's condition editor, over the variables available at this node |
| formula | a monospaced box, with the variables available at this node listed under it |
| file path | a text box; paths are relative to the project, e.g. `outputs/clean.csv`. For a **Data file** the hint reads "assets/<name> — a file uploaded under Files", for an output node "outputs/… under Files" |

**The variables available at a node** are the questionnaire's codebook
variables, then those that nodes upstream of it make — a **Recode**,
**Derive**, **Index / scale**, **Explode multiple choice**, **Cluster
(k-means)**, **Response quality**, **Speeders & partials**, a weighting node,
or a **Code open answers** whose **Theme variable** is filled in — labeled
"*label* · made by *node*" (or "made by *node*"), then those a table the flow
reads brings, labeled "from table *table* · made by *flow*". A variable made
further down the flow is not offered: it does not exist yet when this node
runs. See
[Parameters and variable pickers](Studio-Flows#parameters-and-variable-pickers).

**One-line texts.** The texts a node's card summarizes — a **Report
section**'s **Heading**, a **Derive** formula, a **Live tile**'s **Label**, a
path, a table or variable name — are written into a comment line of the
generated script, so they must be one line. A line break (or another control
character; a tab is fine) fails the engine check at **Check** and at Save,
on that node: "“heading” holds a line break or another control character: it
must be one line of text." The flow then has no script until you fix it.

**Where files go.** On the platform, only files a node writes **under
`outputs/`** are kept after a run and appear in **Files** (as
`outputs/<flow>/<file>`) and on the run's card. Give every path parameter of an
output node a value that starts with `outputs/`. A file a flow *reads* on the
platform is an upload under **Files**, named by its path `assets/<name>` (see
[Data file](#data-file)).

---

## Sources

Nodes with no input that produce **SurveyData**. A flow needs at least one.

### Data file

`source.file` — reads a data file with its codebook: Parquet, CSV, Excel,
SPSS (`.sav`) or Stata (`.dta`). The palette describes it as "A data file from
Files: Parquet, CSV, Excel, SPSS or Stata, with its dictionary when present."
With a dictionary (a `<name>.dictionary.json` beside the file, or the one you
name) the columns arrive labeled; otherwise the questionnaire's codebook
labels the columns it knows.

**In:** none → **Out:** `data` (SurveyData)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **File** | file path | required | — | Path of the data file, relative to the project. On the platform: an upload's path, `assets/<name>` (the hint reads "assets/<name> — a file uploaded under Files"). |
| **Dictionary (JSON)** | file path | — | — | Optional `<name>.dictionary.json`; found automatically when next to the file. |

- **On the platform** the node reads a file you uploaded under
  [[Files|Studio-Files]], by the path shown under the file's name there (the
  copy icon beside it copies "the path a flow reads it by"), for example
  `assets/ev_q2_labeled.sav`. Runs, **Run all** and **Run to here** all get
  it.
- Only the uploads a flow names are copied into its run. An uploaded
  dictionary is therefore not found "next to the file" on the platform: name
  it in **Dictionary (JSON)** as well (`assets/ev_q2.dictionary.json`).
- An upload that is missing shows in the run's log before the node fails:
  "note: assets/panel.csv is not among this project's Files" (or "… is listed
  under Files but its content is gone").
- In a research bundle made **with the responses so far**, the uploads the
  flows name are included at the same path; in a bundle without data, put
  the file there yourself (see [[Reproducibility|Studio-Reproducibility]]).

### Responses

`source.responses` · platform — the answers collected by your survey,
from the project's `responses` table, as SurveyData labeled by the
questionnaire's codebook. New flows start with one of these already placed
(id `src`).

**In:** none → **Out:** `data` (SurveyData)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Table** | text | `responses` | — | Which project table to read. `responses` is the table your survey writes. A table name has lowercase letters, digits and `_`, starts with a letter or `_`, and has at most 63 characters. |
| **Environment** | text | `main` | — | Keep the responses collected by this environment's deployments (plus rows no deployment collected, such as imported or sample data). Typed as text, e.g. `main` or `pilot`: lowercase letters, digits and `-`, starting with a letter, at most 63 characters. |
| **Only completed responses** | checkbox | off | — | Drop interviews that were started but not submitted. |

What comes in besides the answers: `duration_s` (interview length in
seconds), `started_at`, `captcha`, `tab_switches`, `hidden_seconds`, `pastes`
and every URL parameter of the survey link (`url_…`).

**How the answers arrive.** One column per variable, whichever survey runtime
collected the response — responses stored before the current runtime are read
into the same layout:

- A question that writes several variables — a matrix, a MaxDiff, a conjoint,
  a Multiple choice with **Data layout** `wide` — arrives as one column per
  variable. A wide choice is 1 when chosen and 0 when offered and not chosen;
  with the current survey runtime, an option the respondent never saw
  (hidden by its own condition) is left empty rather than 0.
- A matrix answer is the column's codebook code: a 0–10 scale is 0–10.
  Responses collected by an earlier runtime, which stored the column's
  position (1–11 for a 0–10 scale), are read as the code too — so a matrix
  whose codes are not 1, 2, 3, … gives different numbers than it did before
  this was fixed. Check **Recode** mappings, **Filter rows** values and
  weighting targets written against the old values.
- "Other (please specify)" arrives as the question's Other code (`-66` unless
  the question sets another) in the question's variable, and the typed text
  in its own column, `<variable>_other`. "None of the above" is the
  question's None code (`-77` unless set), and "Not applicable" the
  variable's declared not-applicable code — or the text `na` when the
  codebook declares none. See
  [[Codebook and Variables|Studio-Codebook-and-Variables]].
- A variable a custom script writes arrives as its own column; flags an
  earlier runtime stored together (`__flags__`) arrive one column each (for
  example `speeder`).

Notes:

- **Environment** keeps the responses of that environment's deployments plus
  the rows no deployment collected (imported data, a template's sample data).
- **Only completed responses** has no effect on a table without a `partial`
  column. Partial interviews reach the `responses` table only from surveys
  published with the current survey runtime: a survey published before
  partial saves were fixed sends only submitted interviews until you publish
  it again, and from then on a flow that does not tick this box sees its
  partial interviews too.
- A **Table** or **Environment** that no project can have (see the rules
  above) fails the engine check at Save: "“x y” is not a table name: …" or
  "“Main” is not an environment name: …".
- In a research bundle this node reads a data file instead of the database.
  A bundle made with data carries one already filtered the way this node
  filters (`data/responses.main.csv`, `data/responses.main.completed.csv`, or
  `data/responses.csv` when the filter keeps every row); with a file you
  supply yourself, the file is read as is. See
  [[Reproducibility|Studio-Reproducibility]].

### Simulated data

`source.simulated` — "Synthetic responses generated from the questionnaire's
logic — conditions, routing, assigned arms — for building a flow before
fieldwork." The same seed gives the same data, including in a research
bundle.

**In:** none → **Out:** `data` (SurveyData)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Respondents** | whole number | `200` | at least 1 | How many synthetic respondents to generate. |
| **Seed** | whole number | `42` | — | Random seed: the same seed gives the same data every time. |

Each simulated respondent walks the questionnaire as the survey would move
them, its scripts included:

- a Scripts → **Assign to a condition** arm is drawn by the arms' weights and
  arrives as a column (a nominal variable labeled with the arms), and the
  pages shown only to one arm are filled for that arm;
- a page shuffle is dealt to each respondent;
- questions hidden by their own, their block's or their page's condition stay
  empty, and so do answer options hidden by their own condition.

Quotas belong to publishing, not to the questionnaire, so no quota closes
here (Test → Simulate in the Builder does apply them). The generated line is
`n_<id> = simulate_survey(survey, n=…, seed=…)`. In a research bundle whose
engine pin lags behind Studio (the README says so), this node stops with an
error — see [[Reproducibility|Studio-Reproducibility]].

### Project table

`source.table` · platform — a table in the project database, typically one
another flow wrote with **Write table** (for example a cleaned copy of the
responses), as SurveyData labeled by the questionnaire's codebook.

**In:** none → **Out:** `data` (SurveyData)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Table** | text | required | — | Name of a project table written by a **Write table** node (or another table in **Data**): lowercase letters, digits and `_`, starting with a letter or `_`, at most 63 characters. |

- **Run all** runs this flow after the flow whose **Write table** writes the
  table named here, whatever the flows are called, and skips it (marked
  failed) when that flow fails. Running this flow on its own does not run the
  writer first: it reads the table as it is. See
  [Run all](Studio-Flows#run-all).
- The table brings the variables its writer stored with it — labels, scales
  and value labels of a recode, a derived variable, an index, a cluster, the
  quality flags — merged with the questionnaire's codebook (the
  questionnaire's entry wins a name both have). They can be picked in this
  flow's nodes ("from table *table* · made by *flow*"), and naming one passes
  the engine check. A table last written before tables kept their variables
  arrives without those labels until its writer runs again. See
  [Cleaning and Weighting Data](Studio-Cleaning-and-Weighting#writing-the-cleaned-data-to-a-table).
- In a research bundle made with data this node reads `data/tables/<table>.csv`
  — the table as it was in the project database when the bundle was made,
  with its variables in `data/tables/<table>.dictionary.json` — not a table
  the writing flow produces there.

---

## Prepare

SurveyData in, SurveyData out: the steps a methods section calls "data
preparation". The recommended order is described in
[[Cleaning and Weighting Data|Studio-Cleaning-and-Weighting]].

### Apply weight

`prepare.apply_weight` — "Weight the results downstream by a column. Weighted
results say so, and a result with no weighted form says it is unweighted."
Use it after **Cell weights** or **Rake weights** created the column (or when
the data already carries one).

**In:** `data` (SurveyData) → **Out:** `data` (SurveyData)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Weight column** | text | `weight` | — | The column holding the weights. The hint under it lists which results are weighted and which are not (the two tables below). |

These nodes use the applied weight, and their output names it (`Weight` or
`weight` among the statistics). In the weighted tables and charts a weight
that is missing or not a number counts as 0.

| Node | Weighted |
|---|---|
| **Frequencies** | N is the sum of the weights and the percentages follow it, with an **Unweighted N** column beside it (see [Frequencies](#frequencies)) |
| **Crosstab** | cells and totals are sums of weights and the percentages are taken from them; the chi-square test uses Kish's effective base (see [Crosstab](#crosstab)) |
| **Group means** | means, SDs and medians; N and the significance test stay unweighted (see [Group means](#group-means)) |
| **Banner table** | percentages and counts; tests on Kish's effective base |
| **Net Promoter Score** | the shares and the score (its standard error on Kish's effective base); N counts respondents |
| **Regression** | linear models become weighted least squares; logistic models are weighted too |
| **TURF** | the base and each portfolio's reach |
| **MaxDiff** | every column: **Shown**, **Best**, **Worst**, **Score**, **Utility** and **Share %** (see [MaxDiff](#maxdiff)) |
| **Conjoint** | the part-worths and **Importance %** (see [Conjoint](#conjoint)) |
| **Share of preference** | the shares, from weighted part-worths |
| **Principal components** | loadings, eigenvalues and explained variance, from the weighted covariance (or correlation) matrix |
| **Scale reliability** | alpha, item means, item–total correlations and alpha-if-deleted |
| **Bar chart** | bars are sums of weights, or weighted means with **By** (see [Bar chart](#bar-chart)) |
| **Heatmap** with **By** | weighted means by group |
| **Proportion CI** | only when its **Weighted** box is ticked (see [Proportion CI](#proportion-ci)) |

These have no weighted form. After Apply weight they run on the respondents
as they are and **say so**: "unweighted (the weight 'weight' is not applied)"
— as a `weight` statistic, a `Weight` line under the table, or a second line
of the chart's title (also under a title you set):

| Node | Where it says so |
|---|---|
| **Compare groups**, **Correlation** | statistic `weight` |
| **Cluster (k-means)** | statistic `weight` |
| **Proportion CI** with **Weighted** unticked | statistic `weight` |
| **Box plot**, **Scatter plot**, **Heatmap** without **By** | second title line |
| **Response quality**, **Code open answers** | `Weight` under their table: they count responses and answers |

**Describe** counts rows and, on weighted data, adds a `weighted_n_valid`
column: the weighted base a table of each variable would report. The data
files of **Choice data for HB** and **Conjoint data for HB** have no weight
column. The Methods draft describes the step as "estimates that support
weights were weighted by `weight` (rank tests, k-means clustering, box and
scatter plots and correlation heatmaps stay unweighted)".

> **Note.** The MaxDiff **Utility** and **Share %**, Conjoint, Share of
> preference, Principal components, Scale reliability, the Bar chart and the
> Heatmap of means were computed unweighted after Apply weight before this was
> fixed, and a weighted **Proportion CI** counted non-respondents in its base.
> Run a weighted flow again and these numbers change; reports and tiles from
> earlier runs keep the old ones.

### Cell weights

`prepare.cell_weights` — post-stratification on one variable: after
weighting, that variable's distribution matches your targets. It adds the
weight column but does not apply it — follow it with **Apply weight**.

**In:** `data` (SurveyData) → **Out:** `data` (SurveyData)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Variable** | variable | required | nominal / ordinal variables | The single-answer variable to weight on. |
| **Targets (code → share)** | JSON object | required | — | Target share per code, e.g. `{"1": 0.45, "2": 0.55}`. Shares or counts both work; they are normalized. |
| **Weight column** | text | `weight` | — | Name of the new weight column. |
| **Cap** | number | — | at least 1 | Upper bound for weights of mean 1 (must be greater than 1). Capping makes the match to the targets approximate. |

- Targets may be shares or counts; they are normalized, so
  `{"1": 45, "2": 55}` and `{"1": 0.45, "2": 0.55}` mean the same.
- A category you leave out of the targets keeps its current share.
- Weights are scaled to a mean of 1, so the weighted N equals the number of
  rows. **Cap** must be greater than 1.
- A multiple-answer variable is refused: a respondent in two categories has no
  single cell. Weight on a single-answer variable, or on the 0/1 columns
  **Explode multiple choice** creates.

### Dedup respondents

`prepare.dedup` — one row per respondent. A respondent who resumed the survey
or submitted twice is kept once: the latest submission by default.

**In:** `data` (SurveyData) → **Out:** `data` (SurveyData)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Respondent id column** | text | `respondent_id` | — | Column that identifies a respondent. |
| **Order by** | text | `submitted_at` | — | Column that orders a respondent's submissions. If it is missing, Studio falls back to `submitted_at`, `started_at`, `updated_at` or `created_at`, whichever exists. |
| **Keep** | choice | `last` | `first`, `last` | `last` keeps the most recent submission, `first` the earliest. |

Rows with a blank respondent id are always kept, each as its own respondent.
Data without the id column passes through unchanged.

### Derive

`prepare.derive` — a new variable computed from others with a small formula
language: arithmetic, functions and `if … then … else`. The formula is stored
as text and parsed, never executed as code, so what you write is exactly what
a reviewer reads in the generated script.

**In:** `data` (SurveyData) → **Out:** `data` (SurveyData)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **New variable** | text | required | — | Name of the new variable. |
| **Formula** | formula | required | — | e.g. round(spend_year / 12, 2), or: if age < 30 then 1 else 2. Functions: mean, sum, min, max, abs, round, log, coalesce. A missing answer stays missing; dividing by zero gives missing, not infinity. |
| **Label** | text | — | — | Defaults to the formula itself — the most honest description of the number. |
| **Scale** | choice | `ratio` | `ratio`, `interval`, `ordinal`, `nominal` | Measurement scale of the new variable. Choose `nominal` or `ordinal` when the result is a code rather than an amount. |

**The formula language.**

| Element | Syntax |
|---|---|
| Numbers | `12`, `0.5`, `.5` |
| Variables | codebook names, e.g. `spend_year`, `q1` |
| Arithmetic | `+`, `-`, `*`, `/`, unary `-`, parentheses |
| Comparisons | `=`, `!=`, `>`, `>=`, `<`, `<=` |
| Logic | `and`, `or`, `not` |
| Conditional | `if <condition> then <value> else <value>` |
| Functions | `mean(…)`, `sum(…)`, `min(…)`, `max(…)` — across their arguments, row by row; `abs(x)`, `round(x, digits)`, `log(x)`, `coalesce(x, y, …)` |

Examples: `round(spend_year / 12, 2)` · `(q1 + q2 + q3) / 3` ·
`mean(q1, q2, q3)` · `if age < 30 then 1 else 2` ·
`if income > 0 then round(income / 12, 2) else 0` · `coalesce(children, 0)`.

Precedence, loosest first: `if … then … else`, `or`, `and`, `not`,
comparisons, `+ -`, `* /`, unary minus. The comparison and logic words mean
exactly what they mean in a skip-logic condition. `contains` (chose) is not
available: a formula works on numbers — run **Explode multiple choice** first
and use the 0/1 column.

Two behaviors to know before you read a result:

- **A blank stays blank.** A respondent who skipped a question has no value,
  and arithmetic on it has none either. Dividing by zero also gives a blank
  rather than infinity — an infinity looks like a number all the way into the
  report. Write `coalesce(x, 0)` where you mean "treat a blank as zero".
- **A text variable is refused by name**, rather than turning into a column of
  blanks. Recode it first.

A formula is checked when you press **Check** and when you Save: an unreadable
one says where reading stopped ("… (at character 14)"), and a variable that is
neither in the codebook nor made earlier in the flow is named. Write it on one
line: the box wraps long formulas, but a line break in it fails the check (see
[One-line texts](#reading-this-page)).

### Explode multiple choice

`prepare.explode` — one 0/1 column per option of a multiple-answer question
(`brand_1`, `brand_2`, …), so that weights, regression, clustering and TURF can
read it.

**In:** `data` (SurveyData) → **Out:** `data` (SurveyData)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Multiple-choice variable** | variable | required | nominal variables | A question whose answers are lists of codes. |
| **Column prefix** | text | — | — | Defaults to the variable's own name and an underscore, so option 1 becomes brand_1. |
| **Drop the original column** | checkbox | off | — | Off by default — the list column still answers questions the indicators cannot, such as how many options each respondent picked. |

Someone who did not answer the question gets a **blank** in every indicator,
not a row of zeroes — "chose nothing" and "was never asked" are different
facts, and only the first belongs in a base. The indicator names follow the
codebook's codes (`<prefix><code>`), and later nodes offer them in their
variable lists ("made by *node*") — for example as a **TURF**'s **Options**.
A Multiple choice question with **Data layout** `wide` already has one 0/1
variable per choice and needs no Explode.

### Filter rows

`prepare.filter` — keeps only the respondents who satisfy a condition, built
with the same visual editor as the questionnaire's logic.

**In:** `data` (SurveyData) → **Out:** `data` (SurveyData)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Condition** | condition | required | — | Rows that satisfy the condition are kept; the others are removed. |

The editor offers **ALL of the following** / **ANY of the following**, the
operators = ≠ > ≥ < ≤ **in**, **not in**, **chose**, **did not choose**, and
value pickers that show value labels (`Capital region (1)`). Its variables
are those available at this node — the codebook's, and those made upstream,
such as `quality_score` or a recode — so you can, for example, keep only
`quality_score` = `0`. A condition that nests groups opens as JSON.
Conditions typed as raw text are refused ("raw string conditions cannot be
evaluated on data").

### Index / scale

`prepare.index` — combines several items into one index variable, the mean
or the sum of the items. Check the items' internal consistency with **Scale
reliability** first.

**In:** `data` (SurveyData) → **Out:** `data` (SurveyData)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Index name** | text | required | — | Name of the new index variable. |
| **Items** | variables (several) | required | — | The component variables. |
| **Method** | choice | `mean` | `mean`, `sum` | `mean` or `sum` of the items. |
| **Label** | text | — | — | Codebook label of the index. |

### Missing values

`prepare.missing` — applies the codebook's declared missing codes ("Don't
know", "Refused" with their codes): they become blanks, so they stop counting
as real values in means and tests. Optionally drops the rows that are blank in
chosen variables.

**In:** `data` (SurveyData) → **Out:** `data` (SurveyData)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Action** | choice | `to_nan` | `to_nan`, `drop_rows` | `to_nan` turns the codebook's declared missing codes into blanks; `drop_rows` does that and then drops rows blank in the variables listed below. |
| **Drop rows missing in** | variables (several) | empty | — | For drop_rows: rows with a blank in any of these variables are dropped. |

### Response quality

`prepare.quality` — flags straightlining, contradictions, duplicate answer
patterns and failed attention checks. By default it **marks** responses rather
than dropping them, so you decide what to exclude and say so in your
write-up.

**In:** `data` (SurveyData) → **Out:** `data` (SurveyData), `table` (Table)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Battery to check** | variables (several) | empty | — | A matrix or a battery of same-scale items. Straightlining and duplicate patterns are measured across these. |
| **Answers that must agree** | JSON object | empty | — | left variable: right variable. A respondent answering them differently is flagged as contradictory. |
| **Attention checks** | JSON object | empty | — | variable: the answer a reading respondent gives. |
| **Straightlining tolerance** | number | `0.0` | at least 0.0 | Standard deviation across the battery at or below which a response counts as flat. 0 means literally identical answers. |
| **Mode** | choice | `flag` | `flag`, `drop` | Flag adds the columns and keeps everyone; drop also removes the flagged responses. |
| **Flags column** | text | `quality_flags` | — | New variable holding the names of the failed checks (empty when clean). |
| **Score column** | text | `quality_score` | — | New variable counting the failed checks (0 when clean). |

The four checks:

| Check (name in the flags) | Flagged when |
|---|---|
| `straightlining` | the standard deviation of a response across **Battery to check** is at or below **Straightlining tolerance** |
| `inconsistency` | a pair in **Answers that must agree** was answered differently |
| `duplicate` | the response's complete answer pattern across the battery is identical to another response's — every member of such a group is flagged |
| `attention` | an attention-check variable was answered with anything but the expected answer |

- **Flags column** (`quality_flags`) holds the failed checks joined with
  `; `, e.g. `straightlining; duplicate`, and is empty for a clean response;
  **Score column** (`quality_score`) counts them. Both enter the codebook
  (labels "Quality flags" and "Checks failed") and travel into exports and the
  generated script.
- **Second output — `table`:** one row per check with N and %, then **Any
  check** and **Clean**, as shares of everyone screened, counted *before*
  anything is dropped. Wire it into a **Report section** to put your exclusion
  numbers in the report. The counts are of responses whatever the weight; on
  weighted data the table says "Weight: unweighted (the weight 'weight' is not
  applied)".
- Later nodes offer `quality_flags` and `quality_score` in their variable
  lists, so a **Filter rows** can keep the clean responses (`quality_score` =
  `0`) instead of **Mode** `drop`.
- For **Attention checks**, the inspector offers **Fill from the questionnaire
  (N marked)** when questions are marked as attention checks in the Builder;
  otherwise it says "Mark a question as an attention check in Builder to fill
  this in."

### Rake weights

`prepare.rake_weights` — iterative proportional fitting: adjusts weights until
several margins (region, gender, age group…) match their targets at once. It
adds the weight column but does not apply it — follow it with **Apply
weight**.

**In:** `data` (SurveyData) → **Out:** `data` (SurveyData)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Targets (variable → code → share)** | JSON object | required | — | One block per margin, e.g. `{"region": {"1": 0.45, "2": 0.30, "3": 0.25}, "gender": {"1": 0.48, "2": 0.52}}`. |
| **Weight column** | text | `weight` | — | Name of the new weight column. |
| **Max iterations** | whole number | `50` | at least 1 | Maximum raking passes. |
| **Tolerance** | number | `1e-06` | — | Stop when no margin changes by more than this in a pass. |
| **Cap** | number | — | at least 1 | Upper bound for weights of mean 1 (must be greater than 1). |

Targets are normalized per margin (shares or counts). A category missing from
a margin's targets is left unadjusted on that margin. Weights are scaled to a
mean of 1. Multiple-answer variables are refused, as for **Cell weights**.

### Recode

`prepare.recode` — maps the codes of a variable onto new codes, into a new
variable with its own codebook entry: collapsing a 5-point scale to 3 points,
merging small categories, harmonizing codes between waves.

**In:** `data` (SurveyData) → **Out:** `data` (SurveyData)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Variable** | variable | required | — | The variable to recode. |
| **Old code → new code** | JSON object | required | — | Old code → new code, e.g. `{"1": 1, "2": 1, "3": 2}`. Codes not listed are left blank in the new variable. |
| **New variable** | text | — | — | Defaults to `<variable>_recoded`. |
| **Label** | text | — | — | Codebook label of the new variable. |
| **Scale** | choice | — | `nominal`, `ordinal`, `interval`, `ratio` | Measurement scale of the new variable. |

- Codes you do not list in the mapping become blank in the new variable, so
  list every code you want to keep (`{"1": 1, "2": 2, "3": 3, "4": 3, "5": 3}`).
- The new variable's value labels are its codes themselves (`1`, `2`, …):
  there is no field for value labels, so tables of a recoded variable show
  codes. Say what the codes mean in the **Label** or in a caption.
- **Scale** defaults to the source variable's scale; **Label** defaults to the
  new variable's name.
- Later nodes offer the new variable in their variable lists, as
  "*label* · made by *node*".

### Select columns

`prepare.select` — keeps only the listed variables.

**In:** `data` (SurveyData) → **Out:** `data` (SurveyData)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Variables** | variables (several) | required | — | The variables to keep. |

Everything else is dropped, including columns later nodes may need — the
weight, `respondent_id`, timestamps. Select late, or include them.

### Speeders & partials

`prepare.speeders` — quality screening on interview length and completeness.
It adds two columns, `duration_s` and `partial`, and drops speeders and
(optionally) partial interviews. Later nodes offer both in their variable
lists ("completion time · made by *node*", "partial response · made by
*node*").

**In:** `data` (SurveyData) → **Out:** `data` (SurveyData)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Minimum seconds** | whole number | `60` | at least 0 | Interviews completed faster than this are dropped. |
| **Required answers** | variables (several) | empty | — | An interview is *partial* when any of these is blank. |
| **Drop partials** | checkbox | on | — | Also drop partial interviews. |

The rules, precisely:

- A **speeder** is a response whose duration is known and shorter than
  **Minimum seconds**. Duration is the platform's interview length, or
  `submitted_at` − `started_at` when that is all the data has. A response
  whose duration is unknown is never treated as a speeder.
- A response is **partial** when *any* variable in **Required answers** is
  blank. With no required answers listed, nobody is partial, so **Drop
  partials** removes nothing. A required name that does not exist in the data
  marks *every* response partial — check the names.

### Code open answers

`prepare.text_code` — applies a **frozen codeframe** (themes and which answer
belongs to which) to an open-text variable. The model ran once, earlier, when
the codeframe was built; this node only looks answers up in the saved file, so
the same answers get the same themes on every run, and no network call happens
inside your flow. See [[Coding Open Answers|Studio-Open-Answer-Coding]].

**In:** `data` (SurveyData) → **Out:** `data` (SurveyData), `table` (Table)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Codeframe** | file path | required | — | The codeframe file (`analysis/<name>.codeframe.json`) built from these answers. |
| **Theme variable** | text | — | — | Defaults to the name the codeframe carries. |
| **Also add sentiment** | checkbox | off | — | Only when the codeframe was built with it. |

- **Codeframe** is a dropdown of the project's saved codeframes (**— choose a
  codeframe —**). The button beside it — **Code open answers…**, or **Code
  more answers…** once one exists — opens the assistant that builds one. With
  none yet: "No codeframe in this project yet. The assistant builds one from
  the answers you have collected; you read it and save it before anything is
  coded."
- **Output `data`:** adds the theme variable (label `Theme: <variable>`, value
  labels = your theme labels) and, with **Also add sentiment**, a
  `<theme variable>_sentiment` variable coded −1 / 0 / 1 (Negative / Neutral /
  Positive).
- **Output `table`:** one row per theme with N and % of coded answers, then
  **Coded** and **Uncoded** rows. It counts answers, not weights; on weighted
  data it says "Weight: unweighted (the weight 'weight' is not applied)".
- Answers are matched by their normalized text. An answer the codeframe has
  never seen — collected after it was built — stays blank (uncoded) rather
  than being guessed.
- Later nodes offer the theme variable in their variable lists when you type
  its name in **Theme variable** (for example `feedback_theme`); left empty,
  the node still creates it under the codeframe's name, but the pickers do
  not list it. The sentiment variable is not offered.

---

## Analyze

SurveyData in; a **Table**, a **Stat**, or both (**Cluster (k-means)** also
passes the data on). Frequencies and Crosstab wired straight to a
**Responses** node also show instant counts in the inspector — see
[Instant counts](Studio-Flows#instant-counts). How each node treats an
applied weight is summed up under [Apply weight](#apply-weight).

### Banner table

`analyze.banner` — the cross-break: several questions down the page, several
breakdowns across it, each cell a column percentage with its count, and
letters marking significant differences.

**In:** `data` (SurveyData) → **Out:** `table` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Questions (down)** | variables (several) | required | nominal / ordinal variables | One block of rows per question. |
| **Breakdowns (across)** | variables (several) | required | nominal / ordinal variables | Each becomes a block of columns. Letters run across the whole table, but columns are only compared inside their own block. |
| **Significance letters** | checkbox | on | — | Mark significant differences with column letters. |
| **Level** | number | `0.05` | 0.001–0.2 | Significance level for the letters. |
| **Multiple comparisons** | choice | `none` | `none`, `bonferroni` | `bonferroni` corrects for the number of comparisons; `none` is the industry default. |

A letter says this column is significantly higher than the column that letter
names — and three rules keep that claim honest, all restated under the table:

- Columns are compared **only inside their own block**. The values of one
  breakdown are mutually exclusive, which is what the test assumes; columns
  from two different breakdowns overlap (a northerner is also under 35), so
  they are never compared.
- On weighted data the test uses the **effective base** (Kish), because
  weights make a sample behave like a smaller one. The banner uses the
  applied weight.
- A column with **fewer than 30 respondents is not tested**, and the table
  says which ones those were.

### Cluster (k-means)

`analyze.cluster` — segments respondents on a set of items with k-means
(k-means++ start, deterministic for a given seed). It adds a labeled nominal
cluster variable to the data and returns the centroids. Wire its `data` output
on to use the segments: later nodes offer the cluster variable in their
variable lists (a **Crosstab** by segment, say), and **Export file** or
**Write table** take it further.

The segmentation is drawn on the respondents as they are, never on the
weight: on weighted data its statistics carry `weight` = "unweighted (the
weight 'weight' is not applied)". To give the segments their weighted sizes,
run a **Frequencies** of the cluster variable on the weighted data.

**In:** `data` (SurveyData) → **Out:** `data` (SurveyData), `table` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Items** | variables (several) | required | ordinal / interval / ratio variables | Variables to segment on. |
| **Clusters** | whole number | `3` | 2–12 | Number of clusters. |
| **Cluster variable** | text | `cluster` | — | Name of the new cluster variable. |
| **Seed** | whole number | `42` | — | Random seed; the same seed gives the same clusters. |
| **Standardize items** | checkbox | on | — | Put the items on a common scale before clustering. |

### Compare groups

`analyze.compare_groups` — a nonparametric test of whether a variable differs
between groups: Mann-Whitney U for two groups, Kruskal-Wallis H for more.

**In:** `data` (SurveyData) → **Out:** `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Variable** | variable | required | ordinal / interval / ratio variables | The variable to compare. |
| **Group** | variable | required | nominal / ordinal variables | The grouping variable. |
| **Test** | choice | `auto` | `auto`, `kruskal`, `mannwhitney` | `auto` uses Mann-Whitney U for two groups and Kruskal-Wallis H for more. |

Rank tests have no standard weighted form: on weighted data the test runs on
the respondents as they are, and the statistics add `weight` = "unweighted
(the weight 'weight' is not applied)".

### Conjoint

`analyze.conjoint` — part-worths and attribute importance from a
choice-based conjoint question: what people gave up to get what.

**In:** `data` (SurveyData) → **Out:** `table` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Conjoint question** | text | required | — | The question's id or name. Its attributes and design are read from the questionnaire. |

Every level is measured against the first level of its own attribute, which
sits at zero. Importance is an attribute's range of part-worths over the sum of
all ranges — **of the levels you tested**: price from £10 to £12 will look
unimportant beside price from £10 to £100, and that is a fact about your
design. Estimates are aggregate; for individual-level part-worths, export with
**Conjoint data for HB**. The statistics give the **Question**, the **Base**
("812 respondents"), **Tasks read**, the **Method** ("conditional logit
(aggregate)"), the **Reference**, **Pseudo R²** and a **Note** that importance
is of the levels tested. After **Apply weight** the part-worths — and so the
importances — are fitted on the weighted choices, the **Base** gives the
weighted total beside the people ("812 respondents (798 weighted)") and
**Weight** names the column. See
[[MaxDiff and Conjoint|Studio-MaxDiff-and-Conjoint]].

### Share of preference

`analyze.conjoint_shares` — a market simulator: what the part-worths predict a
market of specific products would do.

**In:** `data` (SurveyData) → **Out:** `table` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Conjoint question** | text | required | — | The conjoint question's id or name. |
| **Products** | JSON | required | — | Name → one level code per attribute, e.g. {"Ours": {"brand": 1, "price": 15}}. A half-specified product has no utility. |
| **Include "none of these"** | checkbox | off | — | Only when the question offered it. Leaving it out rescales everyone who would have walked away into buyers. |

A half-specified product has no utility, so give every attribute a level.
Leaving "none of these" out when the question offered it rescales the people
who would have walked away into buyers.

The table has one row per product (its utility and share) and a footer; the
`stat` output carries the same footer: **Question**, **Base** ("812
respondents"), **Method** ("logit rule on aggregate conditional-logit
part-worths") and **Note** — "shares of the products listed, not market
shares", or with **Include "none of these"** "shares of the products listed
and of choosing none, not market shares". After **Apply weight** the shares
come from part-worths fitted on the weighted choices, as in **Conjoint**; the
**Base** adds the weighted total ("812 respondents (798 weighted)") and
**Weight** names the column.

### Correlation

`analyze.correlation` — Spearman rank correlation between two variables (the
only method offered).

**In:** `data` (SurveyData) → **Out:** `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **X** | variable | required | ordinal / interval / ratio variables | First variable. |
| **Y** | variable | required | ordinal / interval / ratio variables | Second variable. |

A rank correlation has no standard weighted form: on weighted data it runs on
the respondents as they are, and the statistics add `weight` = "unweighted
(the weight 'weight' is not applied)".

### Crosstab

`analyze.crosstab` — a cross-tabulation with the percentages you choose and,
optionally, the chi-square test and Cramér's V.

**In:** `data` (SurveyData) → **Out:** `table` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Rows** | variable | required | nominal / ordinal variables | Row variable. |
| **Columns** | variable | required | nominal / ordinal variables | Column variable. |
| **Percentages** | choice | `col` | `none`, `row`, `col`, `total` | Which percentages to show: `none`, `row`, `col` (column %) or `total`. |
| **Chi-square test** | checkbox | on | — | Add the chi-square test and Cramér's V. |

For a multiple-answer row variable the table counts respondents, not answers,
and does not offer a chi-square test (its independence assumption does not
hold).

After **Apply weight**, the cells and totals are sums of weights (to one
decimal) and the percentages are taken from them the same way. The
chi-square test is run on the counts scaled down to the effective (Kish)
sample size, as the **Banner table** does: weights make a sample behave like a
smaller one. With **Chi-square test** on, the statistics keep **N** (the
respondents counted) and add
**Weighted N**, **Effective N**, **Weight** and **Base** ("effective (Kish)
for the test; weighted counts shown"); with the test off they are **Weighted
N** and **Weight**. For a multiple-answer row variable the percentages are of
each column's weighted base, and an **Unweighted base** row follows the "Base
(respondents answering)" row.

### Describe

`analyze.describe` — a summary table of the data: one row per codebook
variable with its label, scale, N, missing and unique values — or the codebook
itself.

**In:** `data` (SurveyData) → **Out:** `table` (Table)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Show** | choice | `variables` | `variables`, `codebook` | `variables`: one row per variable with N, missing and unique values; `codebook`: the codebook table. |

The rows include the variables earlier nodes made. The counts are of rows
(records), which is what a completeness check is about; after **Apply
weight** a `weighted_n_valid` column stands beside them — the sum of the
weights of the rows that have a value, the weighted base a table of that
variable would report.

### Frequencies

`analyze.freq` — the distribution of one variable with value labels, %, and
cumulative %.

**In:** `data` (SurveyData) → **Out:** `table` (Table)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Variable** | variable | required | — | The variable to tabulate. |
| **Exclude missing** | checkbox | on | — | Leave blank answers out of the table. |
| **Sort** | choice | `value` | `value`, `freq`, `label` | `value` (by code), `freq` (largest count first) or `label` (alphabetical). |

For a multiple-answer question, each option's share is of the respondents who
answered, so the column sums above 100 %; the base is a row of its own and
there is no cumulative column.

After **Apply weight**, **N** is the sum of the weights (to one decimal) and
the percentages are taken from it, an **Unweighted N** column beside **N** gives the respondents
actually counted — the number a reader judges a percentage by — and the
statistics add **Weighted N** and **Weight**. For a multiple-answer question
the weighted counts are rounded to whole numbers, the base row carries the
unweighted base under **Unweighted N**, and the statistics read, for example,
"812 respondents (798 weighted)".

### MaxDiff

`analyze.maxdiff` — what a best–worst question found: one row per item, best
first, with the counting score, the conditional-logit utility and the share it
implies.

**In:** `data` (SurveyData) → **Out:** `table` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **MaxDiff question** | text | required | — | The question's id or name. Its design is read from the questionnaire, so nothing has to be re-entered here. |
| **Estimate** | choice | `both` | `both`, `counts`, `utilities` | Counting is best minus worst over shown and anyone can recount it. Utilities are a conditional logit on the choices the design actually showed. |

The design is read from the questionnaire, so the only thing to name is the
question. Utilities come from an **aggregate** conditional logit; individual
ones need hierarchical Bayes, which **Choice data for HB** exports for. The
footer gives the **Question**, the **Base** ("812 respondents"), **Tasks
read**, the **Method**, the **Reference** item and **Pseudo R²**.

After **Apply weight** every column is weighted: **Shown**, **Best** and
**Worst** are sums of weights (rounded to whole numbers), the **Score**
follows them, and the **Utility** and **Share %** are fitted on the weighted
choices. The footer adds **Weight** and gives the weighted total beside the
people: "812 respondents (798 weighted)". Before this was fixed the
**Utility** and **Share %** columns stayed unweighted; a weighted flow run
again gives different numbers there.

### Group means

`analyze.means` — mean, SD, median and N of a variable by group, with the
matching significance test chosen by the engine.

**In:** `data` (SurveyData) → **Out:** `table` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Variable** | variable | required | ordinal / interval / ratio variables | The variable whose mean is compared. |
| **By** | variable | required | nominal / ordinal variables | The grouping variable. |
| **Significance test** | checkbox | on | — | Add the matching significance test. |

After **Apply weight**, each group's mean, SD and median are weighted (the SD
is scaled so that equal weights give exactly the ordinary sample SD; the
median is the value at which the cumulative weight reaches half). **N** stays
the number of respondents and the significance test stays unweighted; the
statistics add **Weight** and the note "means, SD and medians are weighted; N
and the test are not".

### Net Promoter Score

`analyze.nps` — detractors (0–6), passives (7–8) and promoters (9–10) of a
0–10 item, and the score with its standard error and 95 % confidence interval.
Uses the applied weight.

**In:** `data` (SurveyData) → **Out:** `table` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **0–10 item** | variable | required | ordinal / interval / ratio variables | A 0–10 likelihood-to-recommend item. |

After **Apply weight** the group shares and the score are weighted and the
standard error uses Kish's effective base; the **N** column still counts
respondents, and the statistics add **Weight**.

### Principal components

`analyze.pca` — loadings and explained variance of a set of items. Three
outputs: `loadings` (Table), `variance` (Table: eigenvalues and explained
variance) and `stat`; the node's preview shows the loadings.

**In:** `data` (SurveyData) → **Out:** `loadings` (Table), `variance` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Items** | variables (several) | required | ordinal / interval / ratio variables | The items to analyze. |
| **Components** | whole number | — | at least 1 | Empty keeps the components with an eigenvalue above 1. |
| **Standardize items** | checkbox | on | — | Analyze the correlation rather than the covariance matrix. |

After **Apply weight** the components are those of the weighted covariance
(or, standardized, correlation) matrix, so the loadings, eigenvalues and
explained variance are weighted; equal weights give the unweighted result.
The `n` statistic stays the rows analyzed, and `weight` names the column.

### Proportion CI

`analyze.proportion_ci` — the share of respondents who gave one answer, with
its confidence interval.

**In:** `data` (SurveyData) → **Out:** `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Variable** | variable | required | — | The variable. |
| **Answer code** | JSON | required | — | The answer code whose share you want, typed as JSON: `1` or `"yes"`. |
| **Confidence** | number | `0.95` | 0–1 | Confidence level between 0 and 1. |
| **Weighted** | checkbox | off | — | Use the applied weight. |

The statistics are `p` (the share), `lower`, `upper` and `n`. The base is
the respondents who answered the variable — someone who skipped it is not
counted as "did not choose".

- **Weighted** ticked: the share is weighted and `n` is Kish's effective base
  of those respondents; a missing weight counts as 0, and weights of 1 give
  the unweighted result. The statistics add `weight` with the column's name.
  Earlier, a weighted share also counted the respondents who did not answer,
  which made it too small; a flow run again reports the corrected share.
- **Weighted** unticked on weighted data: the share is of the respondents as
  they are, and `weight` reads "unweighted (the weight 'weight' is not
  applied)".

### Regression

`analyze.regression` — linear (OLS) or logistic regression with a coefficient
table. With a weight applied, OLS becomes weighted least squares and the
logistic model is weighted too, and the statistics add `weight`. Nominal
predictors are dummy-coded against their first category, using the codebook's
labels.

**In:** `data` (SurveyData) → **Out:** `table` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Outcome** | variable | required | — | Two values → logistic (auto); otherwise linear. |
| **Predictors** | variables (several) | required | — | Nominal predictors are dummy-coded against their first category. |
| **Model** | choice | `auto` | `auto`, `ols`, `logit` | `auto` picks logistic for a two-valued outcome and linear otherwise; `ols` and `logit` force one. |

### Scale reliability

`analyze.reliability` — Cronbach's alpha for a set of items, with item–total
correlations and alpha-if-deleted per item.

**In:** `data` (SurveyData) → **Out:** `table` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Items** | variables (several) | required | ordinal / interval / ratio variables | The items of the scale. |

After **Apply weight** alpha, the item means, the item–total correlations and
alpha-if-deleted are all computed with the weight, and the statistics add
`weight`. A row is dropped for a missing item, never for a missing weight
(that weighs 0), so the respondents counted (`n`) are the same either way.

### TURF

`analyze.turf` — how many **different** people a shortlist of options reaches
together: "which three flavors should we stock?" rather than "which three are
most popular".

**In:** `data` (SurveyData) → **Out:** `table` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Options** | variables (several) | required | — | One 0/1 column per option. Run prepare.explode on a multiple-choice question to get them. |
| **Largest portfolio** | whole number | `3` | at least 1 | — |
| **Search** | choice | `best` | `best`, `greedy` | Best tries every combination. Greedy extends the previous winner and is fast, but can miss the best portfolio — the table says which ran. |
| **Always include** | variables (several) | empty | — | Options that are in the portfolio whatever they add — shelf space already committed. |

- Each respondent is counted once however many options they chose — that is
  what makes it *unduplicated* reach rather than a sum of percentages. The
  base is the respondents who answered; the applied weight is used, and the
  statistics then add **Weight**.
- The table also reports frequency (the mean number of a portfolio's options a
  reached respondent chose) and names which search ran, because an exhaustive
  answer and a greedy one are not the same claim.
- Options must be 0/1 columns. An exhaustive search that would not finish
  says so and suggests the ways out.
- Where the columns come from: an **Explode multiple choice** node upstream
  (its indicator columns are offered in **Options**), a Multiple choice
  question with **Data layout** `wide`, or a set of yes/no questions coded
  0/1.

---

## Visualize

SurveyData in, **Chart** out. All four accept a **Title**, a **Figure width
(in)** and **Figure height (in)** (2–30 inches, 10 × 6 by default) and a
**Palette** — **Heatmap** takes a **Color map** instead. Width and height
resize the figure the engine draws, not the picture of it, so the axis labels
keep their proportion.

After **Apply weight** a chart either draws the weighted numbers or says
under its title that it does not — so a picture never disagrees in silence
with a weighted table beside it:

| Chart | On weighted data |
|---|---|
| **Bar chart** | weighted: bars are sums of weights, or weighted means with **By** — matching the **Frequencies** and **Group means** tables of the same data |
| **Heatmap** with **By** | weighted means by group; the color bar reads "Weighted mean" |
| **Box plot**, **Scatter plot**, **Heatmap** without **By** | unweighted — a box, a point per respondent and a rank correlation have no standard weighted form — with a second title line "unweighted (the weight 'weight' is not applied)", under your own **Title** too |

### Bar chart

`visualize.bar` — the distribution of a variable, or its mean by group when
**By** is set.

**In:** `data` (SurveyData) → **Out:** `chart` (Chart)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Variable** | variable | required | — | The variable to chart. |
| **By** | variable | — | nominal / ordinal variables | Optional grouping variable: when set, the chart shows the variable's mean by group. |
| **Horizontal** | checkbox | off | — | Draw horizontal bars. |
| **Show values** | checkbox | on | — | Print the value on each bar. |
| **Title** | text | — | — | Chart title. |
| **Figure width (in)** | number | `10` | 2–30 | The figure itself, in inches — the axis labels scale with it. |
| **Figure height (in)** | number | `6` | 2–30 | — |
| **Palette** | choice | `muted` | `muted`, `deep`, `pastel`, `dark`, `colorblind`, `Set2`, `tab10` | Color palette. |

After **Apply weight**, a distribution's bars are sums of weights — the axis
reads "Weighted count" and the values on the bars have one decimal when they
are fractional — and with **By** the bars are weighted means, on an axis
"Weighted mean *label*". Unweighted, the axes read "Count" and "Mean *label*".

### Box plot

`visualize.boxplot` — the distribution of a variable across groups.

**In:** `data` (SurveyData) → **Out:** `chart` (Chart)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Variable** | variable | required | ordinal / interval / ratio variables | The variable whose distribution is shown. |
| **By** | variable | required | nominal / ordinal variables | The grouping variable (required). |
| **Show points** | checkbox | off | — | Overlay the individual points. |
| **Title** | text | — | — | Chart title. |
| **Figure width (in)** | number | `10` | 2–30 | The figure itself, in inches — the axis labels scale with it. |
| **Figure height (in)** | number | `6` | 2–30 | — |
| **Palette** | choice | `muted` | `muted`, `deep`, `pastel`, `dark`, `colorblind`, `Set2`, `tab10` | Color palette. |

Quartiles and whiskers are of the respondents as they are; on weighted data
the title's second line says "unweighted (the weight 'weight' is not
applied)".

### Heatmap

`visualize.heatmap` — the correlation matrix of several items, or their means
by group when **By** is set.

**In:** `data` (SurveyData) → **Out:** `chart` (Chart)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Items** | variables (several) | required | — | The items to show. |
| **By** | variable | — | nominal / ordinal variables | Optional grouping variable: with it the heatmap shows item means by group; without it, the correlation matrix of the items. |
| **Title** | text | — | — | Chart title. |
| **Figure width (in)** | number | `10` | 2–30 | The figure itself, in inches — the axis labels scale with it. |
| **Figure height (in)** | number | `6` | 2–30 | — |
| **Color map** | text | `YlOrRd` | — | A matplotlib colormap, used when means are shown by a group; a correlation matrix keeps its own diverging scale. |

After **Apply weight**, the means by group are weighted and the color bar is
labeled "Weighted mean". The correlation matrix (no **By**) is a Spearman
correlation, which is never weighted: its title's second line says
"unweighted (the weight 'weight' is not applied)".

### Scatter plot

`visualize.scatter` — two variables against each other, optionally colored by
a third, with a trend line.

**In:** `data` (SurveyData) → **Out:** `chart` (Chart)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **X** | variable | required | interval / ratio / ordinal variables | Horizontal axis. |
| **Y** | variable | required | interval / ratio / ordinal variables | Vertical axis. |
| **Color by** | variable | — | nominal / ordinal variables | Optional variable that colors the points. |
| **Trend line** | checkbox | on | — | Draw a fitted trend line. |
| **Title** | text | — | — | Chart title. |
| **Figure width (in)** | number | `10` | 2–30 | The figure itself, in inches — the axis labels scale with it. |
| **Figure height (in)** | number | `6` | 2–30 | — |
| **Palette** | choice | `muted` | `muted`, `deep`, `pastel`, `dark`, `colorblind`, `Set2`, `tab10` | Color palette. |

Every respondent is one point and the trend line is fitted unweighted; on
weighted data the title's second line says "unweighted (the weight 'weight'
is not applied)".

---

## Output

Where results leave the flow.

### Choice data for HB

`output.choice_data` — writes a MaxDiff's answers in the long format that R's
hierarchical-Bayes packages read.

**In:** `data` (SurveyData) → **Out:** none (writes files, a table or a tile)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **MaxDiff question** | text | required | — | The question's id or name. Its design is read from the questionnaire. |
| **Path** | file path | required | — | Output CSV path under `outputs/`, e.g. `outputs/brands.csv`. The dictionary and R script are written beside it. |

Three files, so that estimating individual-level utilities on your own machine
needs no rewriting: the choices (`<name>.csv`), a dictionary saying what every
column means (`<name>.dictionary.json`) and a script that runs the model and
writes the per-respondent estimates back (`<name>.hb.R`). The **Path** help
adds: "The file has no weight column (the HB packages take none), so an
applied weight is not in it; weight the individual utilities when you
aggregate them."

Why export rather than estimate here: hierarchical Bayes takes minutes of
MCMC, and a flow run has one CPU and a few minutes for everything. A cut-down
chain would be a worse answer under the same name. The tables **MaxDiff** and
**Conjoint** produce are aggregate estimates, which is a different — and
honestly labeled — thing.

### Conjoint data for HB

`output.conjoint_data` — the same for a choice-based conjoint: the choices in
long format, a column dictionary and an R script.

**In:** `data` (SurveyData) → **Out:** none (writes files, a table or a tile)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Conjoint question** | text | required | — | The question's id or name. Its attributes and design are read from the questionnaire. |
| **Path** | file path | required | — | Output CSV path under `outputs/`. The dictionary and R script are written beside it. |

As for MaxDiff, the file has no weight column: weight the individual
part-worths when you aggregate them.

### Export file

`output.export_file` — writes the data to a file, with its dictionary
(`<name>.dictionary.json`) beside it. The extension in **Path** decides the
format: `.parquet`, `.csv`, `.xlsx`, `.sav` or `.dta` (SPSS and Stata files
also carry the labels inside).

**In:** `data` (SurveyData) → **Out:** none (writes files, a table or a tile)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Path** | file path | required | — | Output file under `outputs/`, e.g. `outputs/clean.sav`. The extension decides the format. |

The file appears in **Files** and as a download chip on the run's card — as
long as **Path** starts with `outputs/`.

### Live tile

`output.live_tile` — publishes whatever is connected to it — a number, a
table, a chart or a statistic — as a tile on the **Live** screen. See
[[Live Monitoring|Studio-Live-Monitoring]].

**In:** `input` (Any) → **Out:** none (writes files, a table or a tile)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Kind** | choice | `number` | `number`, `table`, `chart`, `stat`, `text` | How the tile shows the value: `number`, `table`, `chart`, `stat` or `text`. |
| **Label** | text | required | — | The tile's caption on the Live screen. |
| **Show** | choice | `value` | `value`, `rows` | rows: the number of respondents in the data connected. |

- Tiles are published by every run of the flow (a manual run, a scheduled
  run of this flow, a live recompute). **Run all** and **Run to here** do not
  publish tiles, and do not clear them either: the Live screen shows the
  tiles of the flow's latest completed run. After a rename it goes on showing
  them until the flow runs under its new name.
- **Show** = `rows` is the usual way to show "respondents after cleaning":
  connect the SurveyData output of the last cleaning step.
- A tile's size on the Live screen is not set from the canvas; tiles appear at
  the standard size.

### Report section

`output.report_section` — collects tables, charts and statistics into one
section of a report, with a heading, introductory text, a caption per item
and a closing note. Without a heading it is a plain block of Markdown between
the sections around it. Usually edited in the flow's **Report** view — see
[[Reports|Studio-Reports]].

**In:** `items` (Table or Chart or Stat, several, optional) → **Out:** `report` (Report)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Heading** | text | — | — | Section title, on one line. Leave empty for a plain block of text between sections. |
| **Text** | Markdown | — | — | Introductory text (Markdown). |
| **Captions** | one caption per input | — | — | A caption for each connected table, chart or statistic. |
| **Size and placement** | size per input | — | — | Per item — a width (60%, 320px), an alignment, or a page break before it. The Markdown is unaffected. |
| **Note** | Markdown | — | — | A closing note (Markdown) — methods, source, base. |

- The order you connect items in is the order they appear.
- A statistic (a **Stat** output) is printed as one line —
  `Caption: key = value; …` — where its caption is the label before the
  values. It has no size or placement: under **Size and placement** its row
  reads "one line" ("A statistic is one line of the report: size and
  placement apply to tables and charts only").
- Size and placement reach the HTML only; the Markdown is unaffected.

### Save report

`output.save_report` — combines sections, in the order you connect them, into
one report and saves it: Markdown (the content, with each chart as
`fig_N.png` beside it) and, by default, an HTML twin (the look, stylesheet
and images inside the file). A report produced by a run on the platform ends
with a provenance footer while **Settings → Reports → End every report with
the provenance footer** is on (the default).

**In:** `sections` (Report, several) → **Out:** `report` (Report)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Title** | text | required | — | The report's title. |
| **Path** | file path | `outputs/report.md` | — | Where the Markdown file is written. Keep it under `outputs/`. |
| **Also save HTML** | checkbox | on | — | Also write the styled `.html` twin next to the Markdown. |
| **Table of contents** | checkbox | off | — | Add a table of contents. |
| **Look** | report look | — | — | Typefaces, measure, table style and page size of the rendered report. The Markdown is unaffected. |

- The **Look** parameter is edited in the **Look** tab of the Report view
  ([Reports](Studio-Reports#the-look-tab)). A node created by the Report view
  or added from the palette starts with the project's house style as its
  look, when the project has one. A node with no look renders with the
  engine's defaults — on the platform, in previews and in a research bundle
  alike; the house style is not applied to it behind the scenes.
- Keep **Path** under `outputs/`; set the same file as the flow's **Report
  path** (Flow settings) if you want this report in the combined report of
  **Run all**. The Report view does both for you when it creates the node;
  changing the node's **Path** (or clearing it back to `outputs/report.md`)
  moves a **Report path** that named the old file along with it, and deleting
  the node clears the **Report path** it set. A node added from the palette
  sets no **Report path**. A **Report path** that no **Save report** node of
  the flow writes gets a warning at **Check** and at Save ("… but no Save
  report step saves there: Run all will fail this flow. …").
- There is no PDF output: a path ending in `.pdf` fails. Print the HTML
  instead.

### Write table

`output.write_table` · platform — saves the data as a project table: a source
for other flows (**Project table**) and a table on the **Data** screen.

**In:** `data` (SurveyData) → **Out:** none (writes files, a table or a tile)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Table name** | text | required | — | Table name: lowercase letters, digits and `_`, starting with a letter or `_`, at most 63 characters. |
| **If it exists** | choice | `replace` | `fail`, `replace`, `append` | `replace` (drop and recreate), `append` (add rows) or `fail` (stop the run with "table already exists"). |

- The table keeps the variables of the columns it holds — labels, scales and
  value labels, including those of variables the flow created — so a flow
  that reads it gets them back (see [Project table](#project-table)). With
  `append`, the variables are merged with those the table already carries.
- A preview (**Run to here**, **Preview all**) never writes the table. The
  node's Preview pane says what a run would do: "Not written: a preview never
  writes project tables. A run writes 812 rows to table 'clean_responses' (if
  it exists: replace)."
- In a research bundle, when the script is given a data file, this node is
  skipped: there is no project database outside Studio.

---

## What is deliberately absent

- **A Python or SQL node.** Every node is a documented engine call, which is
  what keeps the generated script honest and the sandbox safe. Need custom
  code? Download the `.py` and continue in your own environment.
- **Branches and loops.** A flow is a directed acyclic graph: it reads top to
  bottom, like the script it becomes. The canvas refuses a connection that
  would close a cycle.
- **A model anywhere inside a run.** Open answers are coded by **Code open
  answers**, which applies a scheme built earlier and frozen — so a flow always
  produces the same numbers and never calls out to anything.
- **A PDF writer.** Reports are Markdown and HTML; print or convert the HTML.

## See also

- [[Analysis Flows|Studio-Flows]]
- [[Cleaning and Weighting Data|Studio-Cleaning-and-Weighting]]
- [[Coding Open Answers|Studio-Open-Answer-Coding]]
- [[Reports|Studio-Reports]]
- [[MaxDiff and Conjoint|Studio-MaxDiff-and-Conjoint]]

<!-- studio-nav -->
---

← [[Analysis Flows|Studio-Flows]] · [Studio contents](Studio-Overview#all-pages) · [[Cleaning and Weighting Data|Studio-Cleaning-and-Weighting]] →
