# Node Reference

Every node in the Flows palette: what it does, what it takes and gives, and
every parameter with its exact label, default and allowed values. Use it
alongside [[Analysis Flows|Studio-Flows]], which explains the canvas, and
[[Cleaning and Weighting Data|Studio-Cleaning-and-Weighting]], which puts the
preparation nodes in order.

The palette is served by the engine, so this list is the engine's own: 54
nodes in five groups — **Sources** (4), **Prepare** (16), **Analyze** (23),
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
| **Table** | a frequency table, crosstab, group-means table, banner, coefficient table, t-test, correlation matrix, factor loadings… |
| **Chart** | a bar chart, box plot, heatmap or scatter plot |
| **Stat** | a test result or a set of statistics (χ², Fisher's p, t, Kruskal-Wallis, Wilcoxon, a correlation, CIs, model fit) |
| **Report** | a report section or a whole report |
| **Any** | anything — only the **Live tile** input accepts every type |

Weights, recodes, flags and derived variables are *columns inside*
SurveyData, not separate wires.

**Parameters.** "required" in the Default column means the node reports an
error until you fill it in. The inspector marks every other parameter
*optional*. Types:

| Type | How you set it in the inspector |
|---|---|
| variable | a dropdown of the variables available at this node (`name — label`), filtered to the scales the node accepts. A stored variable of another scale stays shown as what the node reads, with its scale: "q_md_score_1 (interval — Rows takes nominal / ordinal)" — an error of the check for a codebook variable, a warning for one a node of the flow makes. A made variable has the scale the nearest node upstream that makes it gives it (a Recode of a derived variable is ratio, like its source), and the dropdown offers it with that scale; a name the codebook has keeps the codebook's. An arm an **Assign to a condition** script writes is offered as a nominal variable ("assigned by a script") when the codebook does not list it |
| variables (several) | a checklist of the same variables, filtered the same way; a ticked variable the list would not offer stays in it, with its scale or "(not in codebook)", and can be unticked |
| choice | a dropdown of the allowed values (**— default —** leaves the default). Where the code is a statistician's shorthand, the option shows its name beside it — `welch_anova — Welch's ANOVA`, `fdr_bh — Benjamini-Hochberg`; the stored value and the generated script keep the code |
| answer code | an answer of the variable another parameter names, picked from that variable's value labels (`1 — Male`): a dropdown (**— pick an answer —** when the field is required, **— none —** otherwise), or a checklist where several answers may be ticked. A t-test's **Group A** and **Group B** leave the codebook's missing codes out — its missing answers and its `missing_values` alike (a t-test refuses a missing code as a group). A stored code that is not among them reads "5 (not an answer of gender)" in a dropdown and "5 is not an answer of gender" under a checklist. A code stored as text is read as the node reads it: a t-test finds its groups by their text, so a **Group A** of `"1"` shows as `1 — Male`; **Proportion CI**'s answer and McNemar's **Counts as yes** compare codes by type, so there text "1" is not the answer 1 and shows as given, `"1" (not an answer of gender)`. When that variable has no value labels, the field is a JSON box instead |
| whole number, number | a number box; the placeholder shows the default |
| checkbox | ticked = on |
| text | a text box; where the text names a new variable or column, the hint says "names a new variable" |
| JSON object, JSON | a text box that must contain valid JSON; it is read when you leave the box, and a parse error is shown under it. Where the help gives an example, the empty box shows it (`[18, 30, 45, 65, 100]`) |
| condition | the Builder's condition editor, over the variables available at this node |
| formula | a monospaced box, with the variables available at this node listed under it |
| file path | a text box; paths are relative to the project, e.g. `outputs/clean.csv`. For a **Data file** the hint reads "assets/<name> — a file uploaded under Files", for an output node "outputs/… under Files" |

**The variables available at a node** are the questionnaire's codebook
variables, then those that nodes upstream of it make — a **Recode**,
**Derive**, **Index / scale**, **Bands**, **Explode multiple choice**,
**MaxDiff scores**, **Cluster (k-means)**, **Factor analysis** with **Add
factor scores** ticked, **Response quality**, **Speeders & partials**, a
weighting node, or a **Code open answers** whose **Theme variable** is filled
in — labeled "*label* · made by *node*" (or "made by *node*"), then those a
table the flow reads brings, labeled "from table *table* · made by *flow*". A
variable made further down the flow is not offered: it does not exist yet
when this node runs. See
[Parameters and variable pickers](Studio-Flows#parameters-and-variable-pickers).

**Fields that depend on a choice.** Some parameters are read only with some
choices of the node — a **t-test**'s **Groups** only with **Design**
`independent`, its **Second measurement** only with `paired`. The inspector
shows the fields the current choices read and hides the others; each node
below says which. A hidden field that still holds a value you gave it is
named under the others — "Not used with these choices, and kept for when they
apply: **Groups** (with Design = independent)." — with **Clear it** (**Clear
them** for several). Its value comes back into use when you switch back; until
then it is not checked — a Group A kept after **Design** went `paired`, or a
**Groups** naming a variable since removed, is no error, on the canvas or at
Save. A
field that one of the node's rules makes necessary (below) is marked
required rather than *optional*.

**Rules between parameters.** A few nodes have rules about how their choices
go together, written in the node's own words — for example "Tukey's HSD
follows a one-way ANOVA — set Test to anova, or Post-hoc to none." They are
checked as you edit, and by the engine at **Check** and at Save, with the
code `PARAM_CONFLICT`. An **error** is a combination the node cannot run: the
flow cannot run until you change it. A **warning** names a setting the node
would ignore with the other choices, such as a post-hoc test while
**Significance test** is off. Each node's rules are listed with it below.

**One-line texts.** The texts a node's card summarizes — a **Report
section**'s **Heading**, a **Derive** formula, a **Live tile**'s **Label**, a
path, a table or variable name — are written into a comment line of the
generated script, so they must be one line. A line break (or another control
character; a tab is fine) fails the engine check at **Check** and at Save,
on that node, with the error `PARAM_LINE_BREAK`: "“heading” holds a line
break or another control character: it must be one line of text." The flow
then has no script until you fix it. A flow saved before this check with
such a text is left out of a research bundle (see
[What is inside](Studio-Reproducibility#what-is-inside)).

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
  above), including a name that ends in a line break, fails the engine check
  at Save: "“x y” is not a table name: …" or "“Main” is not an environment
  name: …".
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
| **Crosstab** | cells and totals are sums of weights and the percentages are taken from them; the chi-square test uses Kish's effective base. Fisher's exact test counts respondents (see [Crosstab](#crosstab)) |
| **Group means** | means, SDs and medians; N, the significance test and the post-hoc pairs stay unweighted (see [Group means](#group-means)) |
| **Descriptive statistics** | mean, SD, median and quartiles, beside a **Weighted N** column; N, Missing, skewness and kurtosis are not weighted (see [Descriptive statistics](#descriptive-statistics)) |
| **Correlation**, **Correlation matrix** with **Method** `pearson` | the coefficient, with its p-value and CI on Kish's effective base (see [Correlation](#correlation)) |
| **Banner table** | percentages and counts; tests on Kish's effective base |
| **Net Promoter Score** | the shares and the score (its standard error on Kish's effective base); N counts respondents |
| **Regression** | linear models become weighted least squares; logistic models are weighted too |
| **TURF** | the base, each portfolio's reach and its frequency |
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
| **Compare groups** | statistic `weight` |
| **Correlation** with **Method** `spearman` or `kendall` | statistic `weight` |
| **Correlation matrix** with **Method** `spearman` or `kendall` | `Weight` under the table |
| **t-test** | `Weight` under the table |
| **Paired tests** | `Weight` under the table (and under Friedman's pairs) |
| **Factor analysis** | `Weight` under each of its three tables |
| **Group means** | the post-hoc table's `Weight` line (the means above it are weighted) |
| **Crosstab** with **Test** `fisher` | its `Base` line: "the test counts respondents (an exact test needs whole counts); weighted counts shown" |
| **Cluster (k-means)** | statistic `weight` |
| **Proportion CI** with **Weighted** unticked | statistic `weight` |
| **Box plot**, **Scatter plot**, **Heatmap** without **By** | second title line |
| **Response quality**, **Code open answers**, **Data check** | `Weight` under their table: they count responses, answers and rows |
| **Bands**, **MaxDiff scores** | `Weight` in their statistics: they count respondents, or score each one |

**Describe** counts rows and, on weighted data, adds a `weighted_n_valid`
column: the weighted base a table of each variable would report. The data
files of **Choice data for HB** and **Conjoint data for HB** have no weight
column. The Methods draft describes the step as "estimates that support
weights were weighted by `weight` (rank tests, k-means clustering, box and
scatter plots and correlation heatmaps stay unweighted, as do t-tests, the
tests of group means (ANOVA, Welch's ANOVA) and their post-hoc comparisons,
paired tests, Fisher's exact test, rank correlations and factor analysis)".

> **Note.** The MaxDiff **Utility** and **Share %**, Conjoint, Share of
> preference, Principal components, Scale reliability, the Bar chart and the
> Heatmap of means were computed unweighted after Apply weight before this was
> fixed, and a weighted **Proportion CI** counted non-respondents in its base.
> A TURF portfolio's frequency was unweighted too. Run a weighted flow again
> and these numbers change; reports and tiles from earlier runs keep the old
> ones.

### Bands

`prepare.bands` — "Cut a number into bands — age into age groups, income into
brackets — as a labelled ordinal variable; what falls outside every band is
counted."

**In:** `data` (SurveyData) → **Out:** `data` (SurveyData), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Variable** | variable | required | ordinal / interval / ratio variables | Its missing codes (a 999 "Refused") are left out before cutting, so they never land in a band. |
| **Boundaries** | JSON | required | — | Increasing numbers, e.g. `[18, 30, 45, 65, 100]`. A band includes its lower boundary and runs up to, not including, the next; values outside every band stay blank. |
| **Band labels** | JSON | — | — | One fewer than the boundaries, e.g. `["18–29", "30–44", "45–64", "65+"]`. Defaults to "18 to under 30" and so on. |
| **New variable** | text | required | — | Name of the band variable. |
| **Label** | text | — | — | Defaults to the variable's label and "(bands)". |
| **Bands include their upper boundary** | checkbox | off | — | Then a band runs from above its lower boundary up to and including the upper one (the first band takes its lower boundary too). |

- The new variable is ordinal, coded 1, 2, 3, … in the order of the bands,
  with the band labels as its value labels — so a **Crosstab** or **Group
  means** by it prints "18 to under 30", not `1`. Later nodes offer it in
  their variable lists ("made by *node*"), and a **t-test**'s **Group A** and
  **Group B** offer its bands.
- With **Bands include their upper boundary** ticked, the default labels read
  "18 to 30", "over 30 to 45", ….
- The `stat` output names the step (`Variable` = `age → age_band`), counts
  each band (`Bands` = `16 to under 30: 12; 30 to under 45: 15; …`) and what
  fell outside (`Outside the bands`), and adds `Missing codes`, `Blank` and
  `Not numbers` when there are any. A value outside every band (below the
  first boundary, or at or above the last) is blank in the new variable,
  never forced into the nearest band.
- Boundaries that do not increase, or labels whose number does not match,
  stop the run with the reason: "Band boundaries must increase, got [18, 18,
  30].", "5 boundaries make 4 bands, but 3 labels were given."
- The counts are of respondents; on weighted data the statistics add `Weight`
  = "unweighted (the weight 'weight' is not applied)". Tables of the band
  variable after **Apply weight** are weighted as usual.

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
| **Value labels** | JSON object | — | — | For a formula that yields codes: code → label, e.g. {"1": "Under 30", "2": "30 or over"}. Set the scale to ordinal or nominal with them. |

**Value labels** are typed as JSON, codes as keys:
`{"1": "Under 30", "2": "30 or over"}` for `if age < 30 then 1 else 2` — the
example the empty box shows. Tables of the new variable then print the labels,
not `1` and `2`, and a **t-test**'s **Group A** and **Group B** downstream offer
`1 — Under 30` and `2 — 30 or over`. To cut a number into ranges, **Bands**
writes the labels for you.

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

Each column is named with the option's code as the engine writes it: a code
the codebook's `{code: label}` form writes as `1.0` makes `brand_1.0`, and the
variable pickers downstream offer that name.
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

A condition edited by hand in the flow's JSON is checked as the engine will
write it: a part of an *and* / *or*, or what a *not* negates, that is not a
comparison or a variable, and a variable reference without a name, are errors
on the node before a Save.

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

### MaxDiff scores

`prepare.maxdiff_scores` — "One counting-score variable per MaxDiff item, per
respondent — best minus worst over the times it was shown — so the
preferences can go into a crosstab, a cluster or a regression."

**In:** `data` (SurveyData) → **Out:** `data` (SurveyData), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **MaxDiff question** | text | required | — | The question's id or name. Its design is read from the questionnaire. |
| **Variable prefix** | text | — | — | Each item's score is <prefix><item code>. Defaults to the question and _score_, so item 3 of q_md becomes q_md_score_3. |

- **MaxDiff question** is a dropdown of the questionnaire's MaxDiff questions
  (**— pick a MaxDiff question —**), each as `name — question text`. A stored
  name the questionnaire does not have is kept and marked "(not in the
  questionnaire)", and the engine check names it at **Check** and at Save:
  "Parameter 'question' of md_scores: no MaxDiff question named 'q_mdx'; this
  questionnaire has: q_md." With no MaxDiff question in the questionnaire the
  field is a text box.
- One variable per item, `q_md_score_1`, `q_md_score_2`, …, labeled
  "MaxDiff score: *item*", interval, from −1 (picked worst every time it was
  shown) to 1 (picked best every time). A respondent who was never shown an
  item has a **blank** for it, not a 0: "never picked" and "never offered" are
  different answers. Later nodes offer the variables ("MaxDiff score: Price ·
  made by *node*").
- The `stat` output gives the **Question**, **Respondents scored**, **Not
  scored**, **Items**, the **Variables** (`q_md_score_1 … q_md_score_5`), the
  **Score** ("best minus worst over times shown, −1 to 1; blank where never
  shown") and, when some answers could not be read against the design,
  **Unreadable answers** with the reasons.
- The scores are per respondent, so no weight enters them; on weighted data
  the statistics say "unweighted (the weight 'weight' is not applied)". A
  **Group means** of a score after **Apply weight** is weighted as usual.
- These are counting scores from a few tasks per person: coarse but real. The
  **MaxDiff** node gives the aggregate utilities; for individual utilities,
  export with **Choice data for HB**.

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

The inspector shows **Drop rows missing in** only while **Action** is
`drop_rows` (see [Fields that depend on a choice](#reading-this-page)).

Put this node before any analysis whose defaults count a missing code as an
answer — **Correlation** with `spearman`, **Compare groups** without Dunn's
test, **Group means** with **Test** `auto`, the **Crosstab** chi-square; each
of them says when it did. A test you choose by hand (**Correlation**
`pearson` or `kendall`, **Compare groups** with Dunn's test, **Group means**
with another **Test**, **Crosstab** with `fisher`), and the **t-test**,
**Correlation matrix**, **Paired tests**, **Factor analysis**, **Descriptive
statistics** and **Bands**, leave the codes out on their own (see
[Analyze](#analyze)).

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

**In:** `data` (SurveyData) → **Out:** `data` (SurveyData), `table` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Codeframe** | file path | required | — | The codeframe file (`analysis/<name>.codeframe.json`) built from these answers. |
| **Theme variable** | text | — | — | Defaults to the name the codeframe carries. |
| **Also add sentiment** | checkbox | off | — | A sentiment variable beside the theme, and each theme's negative / neutral / positive split in the table. Only when the codeframe was built with it — the stat says when it was not. |

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
- **Output `table`:** one row per theme with N and %, largest first, then
  **Coded** and **Uncoded** rows. A theme's % is of the **coded** answers;
  **Coded** and **Uncoded** are shares of **everyone who answered** — so one
  uncoded answer in four reads 25 %. (It used to be taken of the coded
  answers, which read 33.3 %; a flow run again gives the corrected share.)
  With **Also add sentiment** and a codeframe built with it, each row adds
  **Negative %**, **Neutral %** and **Positive %** of its answers.
- **Output `stat`** — the table's statistics, which it also prints under it:
  **Variable**, **Answered**, **Themes**, **Coverage** ("75.0 % of the answers
  have a theme"), **Distinct uncoded answers** (how many different answers a
  new coding job would have to look at), **Percentages** ("a theme: of the
  coded answers; Coded and Uncoded: of all answers") and **Codeframe** (the
  model and when it built the codeframe). With sentiment: **Sentiment**
  ("negative 66.7 %, neutral 0.0 %, positive 33.3 % of 3 answers") and **Net
  sentiment** (positive minus negative, in points); asked of a codeframe
  built without it, **Sentiment** reads "not in this codeframe". Wire it into
  a **Live tile** to watch the coverage fall as new answers arrive.
- The table counts answers, not weights; on weighted data it says "Weight:
  unweighted (the weight 'weight' is not applied)".
- Answers are matched by their normalized text. An answer the codeframe has
  never seen — collected after it was built — stays blank (uncoded) rather
  than being guessed.
- Later nodes offer the theme variable in their variable lists when you type
  its name in **Theme variable** (for example `feedback_theme`); left empty,
  the node still creates it under the codeframe's name, but the pickers do
  not list it. The sentiment variable is not offered.

---

## Analyze

SurveyData in; a **Table**, a **Stat**, or both (**Cluster (k-means)** and
**Factor analysis** also pass the data on). Frequencies and Crosstab wired
straight to a **Responses** node also show instant counts in the inspector —
see [Instant counts](Studio-Flows#instant-counts). How each node treats an
applied weight is summed up under [Apply weight](#apply-weight).

**Which test.** You can let a node choose, or name the test yourself:

| Question | Node and choice |
|---|---|
| Does a mean differ between two groups? | **t-test** (Welch's by default, or Student's), or **Group means** with **Test** `welch` / `student` |
| … between three or more groups? | **Group means** with **Test** `anova` or `welch_anova`, and **Post-hoc** `tukey` / `games_howell` for every pair |
| Do ratings (ranks) differ between groups? | **Compare groups** (Mann-Whitney U, Kruskal-Wallis H, with Dunn's test for the pairs), or **Group means** with **Test** `mannwhitney` / `kruskal` |
| Do the same respondents answer two questions differently? | **t-test** with **Design** `paired`; **Paired tests** (Wilcoxon signed-rank, or McNemar for yes/no) |
| … three or more questions? | **Paired tests** (Friedman, with pairwise Wilcoxon tests) |
| Is a mean different from a fixed value? | **t-test** with **Design** `one_sample` |
| Are two answers related? | **Crosstab** (chi-square, or Fisher's exact test for small counts); **Correlation** (Pearson, Spearman or Kendall) |
| How do several variables correlate? | **Correlation matrix** |
| Which items belong together? | **Factor analysis**, **Principal components**, **Scale reliability** |

Three rules hold for all of these tests:

- **Missing codes are not answers.** A test you choose by hand — and the
  **t-test**, **Correlation matrix**, **Paired tests** and **Factor analysis**
  — leaves the codebook's missing codes (a "Refused" coded 9) out and says how
  many: "Missing codes left out = Trust: Acme: 44 (9 = Refused)" (in **Paired
  tests** and **Factor analysis**: "Missing codes = 44 answers with a missing
  code (9 = Refused) left out"). **Descriptive statistics** leaves them out
  too, counts them in its **Missing** column with the blanks and names the
  codes ("Missing codes = trust_acme: 9"). The defaults — **Correlation** `spearman`, **Compare
  groups** without Dunn's test, **Group means** with **Test** `auto`, the
  **Crosstab** chi-square — read the data as they always have, so a flow
  keeps its numbers, and say when they counted a missing code as an answer:
  "Missing codes counted as answers = Trust: Acme: 44 (9 = Refused); run
  Missing values first to leave them out" (`missing_codes_counted` among the
  statistics of **Correlation** and **Compare groups**). That is why **Group means** can give a
  Kruskal-Wallis H with **Test** `auto` and a different one with `kruskal`.
  Put **Missing values** first to have every node leave them out.
- **What the data cannot carry is said in words.** A two-group test asked of
  three groups, one respondent in a group, or no spread at all gives a line
  such as "Test = not run: Welch's t-test (unequal variances) compares two
  groups and Region has 3 — choose anova or welch_anova", not a number or a
  crash. A request that cannot work at all (a **t-test** of a grouping with
  three groups and none named) stops the run with the reason; the check warns
  about it before the run ("Gender has 3 answers (1 = Male, 2 = Female, 3 =
  Other); a t-test compares two — name them in Group A and Group B, unless the
  data this node reads holds only two of them."), and a **Paired tests** node
  given a number of variables its test cannot compare is an error of the
  check, in the run's own words ("McNemar compares exactly two variables; 3
  were given.").
- **The weight is used where there is a standard weighted form** (Pearson's
  correlation) and otherwise the result says "unweighted (the weight 'weight'
  is not applied)" — see [Apply weight](#apply-weight).

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
between groups: "Mann-Whitney U for two groups, Kruskal-Wallis H for more —
with Dunn's test on every pair of groups after Kruskal-Wallis when asked."

**In:** `data` (SurveyData) → **Out:** `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Variable** | variable | required | ordinal / interval / ratio variables | The variable to compare. |
| **Group** | variable | required | nominal / ordinal variables | The grouping variable. |
| **Test** | choice | `auto` | `auto`, `kruskal`, `mannwhitney` | `auto` uses Mann-Whitney U for two groups and Kruskal-Wallis H for more. |
| **Post-hoc** | choice | `none` | `none`, `dunn` | Dunn's test compares every pair of groups after Kruskal-Wallis — one line per pair with z and the adjusted p. With it the codebook's missing codes are left out of the test too, and the result says how many; without it they are counted as answers, as they always were, and the result says so (missing_codes_counted) — so the Kruskal-Wallis result can change. Run Missing values first to have both leave them out. |
| **Dunn p adjustment** | choice | `holm` | `holm`, `bonferroni` | Shown only with **Post-hoc** `dunn`. |

- Without Dunn's test the statistics are `statistic` and `p_value`, with
  `groups` (Kruskal-Wallis) or `group_a` and `group_b` (Mann-Whitney), and
  `missing_codes_counted` when a missing code was counted as an answer. With
  it they name the `test` ("Kruskal-Wallis H"), `statistic`, `p_value`,
  `groups`, `n` and `posthoc` ("Dunn's test (Holm)"), then one entry per pair
  of groups, by their value labels — `Capital vs North` = "z = 0.193, p =
  1.0" (the adjusted p) — and `missing_codes` for the codes left out.
- Rule: "Dunn's test follows Kruskal-Wallis — set Test to kruskal or auto, or
  Post-hoc to none." (an error with **Test** `mannwhitney`).
- For the same test with the means table, the effect size and a table of the
  pairs, use **Group means** with **Test** `kruskal` and **Post-hoc** `dunn`.

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

`analyze.correlation` — "Pearson, Spearman or Kendall correlation between two
variables, with its p-value and N — Pearson with a 95 % CI, and weighted when
a weight is applied."

**In:** `data` (SurveyData) → **Out:** `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **X** | variable | required | ordinal / interval / ratio variables | First variable. |
| **Y** | variable | required | ordinal / interval / ratio variables | Second variable. |
| **Method** | choice | `spearman` | `pearson`, `spearman`, `kendall` | Spearman and Kendall (tau-b) correlate ranks and suit rating scales; Pearson measures a straight-line relationship and gives a 95 % CI. Pearson is weighted when a weight is applied, the rank methods are not and say so. Pearson and Kendall leave the codebook's missing codes (a 9 = Refused) out and say how many. Spearman, the default, counts them as answers — as this node always has, so flows made before keep their numbers — and says so in missing_codes_counted; run Missing values first to leave them out. |

The dropdown reads `pearson — Pearson r`, `spearman — Spearman rho`,
`kendall — Kendall tau-b`. What each gives:

| Method | Statistics |
|---|---|
| `spearman` | `rho`, `p_value`, `n`; `missing_codes_counted` when a missing code was counted as an answer |
| `pearson` | `method` ("Pearson"), `r`, `p_value`, `n`, the confidence interval `lower` – `upper` and `confidence` (0.95); `missing_codes` for the codes left out |
| `kendall` | `method` ("Kendall tau-b"), `tau`, `p_value`, `n`; `missing_codes` |

p is two-sided. Kendall's tau-b corrects for ties, which a rating scale is
full of. A flow saved before **Method** existed has no value there and runs
Spearman, exactly as before.

**On weighted data** Pearson's r is the weighted coefficient; its p and
interval are computed on Kish's effective base (`n_effective`), so a weight
never makes a correlation look more certain than the respondents behind it,
and `weight` names the column. Equal weights give the unweighted result.
Spearman and Kendall run on the respondents as they are and add `weight` =
"unweighted (the weight 'weight' is not applied)".

### Correlation matrix

`analyze.correlation_matrix` — "Pearson, Spearman or Kendall correlations
between every pair of several variables — coefficients with significance
marks, or one row per pair with p and N."

**In:** `data` (SurveyData) → **Out:** `table` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Variables** | variables (several) | required | ordinal / interval / ratio variables | The variables to correlate, every pair of them. |
| **Method** | choice | `spearman` | `pearson`, `spearman`, `kendall` | Spearman and Kendall (tau-b) correlate ranks and suit rating scales; Pearson measures straight-line relationships and is weighted when a weight is applied. |
| **Missing answers** | choice | `pairwise` | `pairwise`, `listwise` | Pairwise uses, for each pair, everyone who answered both, so N can differ between pairs; listwise keeps only the respondents who answered every variable. |
| **p adjustment** | choice | `none` | `none`, `holm`, `bonferroni`, `fdr_bh` | Allows for the number of pairs tested — Holm and Bonferroni hold the chance of any false finding at 5 %, fdr_bh (Benjamini-Hochberg) the share of false findings among the significant ones. The marks then follow the adjusted p. |
| **Layout** | choice | `matrix` | `matrix`, `pairs` | Matrix prints the lower triangle with \* p < .05, \*\* p < .01, \*\*\* p < .001; pairs gives one row per pair with the coefficient, p and N. |

`matrix` — the lower triangle, variables by their labels, `—` on the
diagonal:

```
| Variable             | Age    | Trust: Acme | Trust: Globex | Overall satisfaction |
| Age                  | —      |             |               |                      |
| Trust: Acme          | -0.031 | —           |               |                      |
| Trust: Globex        | -0.010 | 0.072       | —             |                      |
| Overall satisfaction | -0.042 | 0.045       | -0.067        | —                    |
```

`pairs` — one row per pair: **Variable 1**, **Variable 2**, the coefficient
(**r**, **rho** or **tau**), **p**, the adjusted p when there is one (**p
(Holm)**) and **N**. Read this one when N differs from pair to pair.

Under the table, and in the `stat` output: **Method** ("Spearman rank
correlation", "Pearson correlation", "Kendall rank correlation (tau-b)"),
**Missing** ("pairwise: each pair uses everyone who answered both", or
"listwise: only respondents who answered every variable"), **N** (a range
such as `112–194` when pairs differ), **p adjustment** ("none", "Holm,
over 3 pairs", or "Holm, over the 2 pairs computed (of 3)" when a pair could not
be computed — it reads `n/a` in the matrix), **Marks** (matrix layout; "(adjusted p)" when adjusted) and
**Missing codes left out** — the matrix leaves the codebook's missing codes
out with every method. On weighted data a Pearson matrix is weighted and adds
**Weight** and **Base** ("weighted coefficients; p on Kish's effective
base"); Spearman and Kendall say "Weight = unweighted (the weight 'weight' is
not applied)".

### Crosstab

`analyze.crosstab` — "Cross-tabulation with a chi-square test and Cramér's V,
or Fisher's exact test for small tables."

**In:** `data` (SurveyData) → **Out:** `table` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Rows** | variable | required | nominal / ordinal variables | Row variable. |
| **Columns** | variable | required | nominal / ordinal variables | Column variable. |
| **Percentages** | choice | `col` | `none`, `row`, `col`, `total` | Which percentages to show: `none`, `row`, `col` (column %) or `total`. |
| **Significance test** | checkbox | on | — | Add the test chosen under **Test**. (It was labeled **Chi-square test** before Fisher's test was added; stored flows keep their setting.) |
| **Test** | choice | `chi2` | `chi2`, `fisher` | Chi-square with Cramér's V, on Kish's effective base when weighted. Fisher's exact test suits small counts; for 2 × 2 it gives the odds ratio and its 95 % CI, larger tables use the Fisher-Freeman-Halton test (exact, or from 20,000 random tables with a fixed seed when there are too many to sum). Fisher counts respondents, unweighted, and leaves the codebook's missing codes out of the table and the test; chi-square keeps them as rows and columns of their own, as it always has, and says so. |

For a multiple-answer row variable the table counts respondents, not answers,
and does not offer a chi-square test (its independence assumption does not
hold).

**Chi-square** (`chi2`, the default) gives χ², df, p, Cramér's V and N. A
declared missing code (a "Refused") stays a row or column of its own, as it
always has, and the statistics then say "Missing codes counted as answers =
Trust: Acme: 12 (9 = Refused); run Missing values first to leave them out".

**Fisher's exact test** (`fisher`) is the test to use when cells are small —
the chi-square's approximation is poor when expected counts fall below 5. The
codebook's missing codes are left out of the table and the test
("Missing codes left out = …").

- A **2 × 2** table gets **Test** "Fisher's exact test", the two-sided **p**,
  the **Odds ratio** (conditional maximum likelihood) with its exact **OR 95%
  CI**, and **Odds ratio of**, which says which way round it is read:
  "Under 50 (vs 50 or over) for Male over Female". **Estimate** reads
  "conditional maximum likelihood with its exact interval, as R's fisher.test
  defines them (R stops its root search sooner, so its printed values can
  differ slightly on sparse tables)" — the p-values agree with R's.
- A **larger** table gets **Test** "Fisher-Freeman-Halton exact test" and
  **p**, summed exactly over every table with the observed margins when there
  are at most 200,000 of them (**p method** "exact, over every table with
  these margins"), and otherwise estimated from 20,000 random tables drawn
  from a fixed seed, so a rerun gives the same p: **p method** "Monte Carlo,
  20,000 random tables with these margins from a fixed seed (± 0.0021); too
  many tables to sum exactly", the ± being the Monte Carlo error.
- A table the test cannot use reads "Test = Fisher's exact test: not run —
  the table has fewer than two rows or columns with answers in them".
- **Rule:** "Fisher's exact test is not run while Significance test is off."
  (a warning).

After **Apply weight**, the cells and totals are sums of weights (to one
decimal) and the percentages are taken from them the same way. The
chi-square test is run on the counts scaled down to the effective (Kish)
sample size, as the **Banner table** does: weights make a sample behave like a
smaller one. With **Significance test** on, the statistics keep **N** (the
respondents counted) and add **Weighted N**, **Weight** and **Base**: for
chi-square also **Effective N**, with **Base** "effective (Kish) for the test;
weighted counts shown"; for Fisher's test, which needs whole counts, **Base**
"the test counts respondents (an exact test needs whole counts); weighted
counts shown". With the test off they are **Weighted N** and **Weight**. For
a multiple-answer row variable the percentages are of each column's weighted
base, and an **Unweighted base** row follows the "Base (respondents
answering)" row.

### Data check

`analyze.data_check` — "The data against its codebook before any analysis —
values outside the valid range, codes without a label, duplicate IDs, columns
nobody declared — with how many rows each and examples."

**In:** `data` (SurveyData) → **Out:** `table` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Variables** | variables (several) | empty | — | Check only these. Empty checks every column and every codebook variable. |

One row per problem, errors first, with the columns **Severity**
(`error` or `warning`), **Variable**, **Problem**, **Rows** (how many rows
have it), **Examples** (up to five offending values with their counts —
`17 (1), 999 (1)` — and "… (3 more)" beyond five) and **Code**:

| Problem | Code |
|---|---|
| outside the valid range 18–75 | `OUT_OF_RANGE` |
| codes the codebook has no label for | `INVALID_LABEL_VALUE` |
| the same ID on more than one row | `DUPLICATE_ID` |
| weight values that are not numbers | `INVALID_WEIGHT` |
| missing codes without a label | `MISSING_VALUE_WITHOUT_LABEL` |
| the weight column is not in the data | `MISSING_WEIGHT_COLUMN` |
| in the codebook but not in the data | `MISSING_COLUMN` |
| in the data but not in the codebook | `EXTRA_COLUMN` |

- A declared missing code is not "outside the valid range": a 999 "Refused"
  is not flagged for an age of 18–75.
- Columns the codebook does not know, and codebook variables the data lacks
  (common after a **Select columns**), are gathered into one row each.
- The weight column and the response metadata beside the answers —
  `respondent_id`, `duration_s`, `partial`, `started_at`, the `url_*`
  parameters and the like — are expected there, so they are not problems;
  the statistics name them under **Not in the codebook, as expected** (for
  example "weight (the weight)").
- The statistics: **Checked** ("9 variables, 240 rows"), **Errors**,
  **Warnings**, and with nothing wrong **Result** "no problems found" (the
  table is then empty).
- It counts rows, so on weighted data it adds "Weight: unweighted (the weight
  'weight' is not applied)".

Put it right after the source and wire its table into a **Report section**
or a **Live tile**: it is the check a methods section's "data were screened
for out-of-range values" rests on.

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

### Descriptive statistics

`analyze.descriptives` — "N, missing, mean, SD, median, minimum and maximum of
several numeric variables — by group if you like, with quartiles, skewness
and kurtosis on request."

**In:** `data` (SurveyData) → **Out:** `table` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Variables** | variables (several) | required | ordinal / interval / ratio variables | The codebook's missing codes (a 99 "Don't know") are not answers and count as missing. |
| **By group** | variable | — | nominal / ordinal variables | Optional. One row per variable and group; a blank or a missing code of the group variable is no group. A multiple-choice question gives one group per option, and they overlap. |
| **Quartiles, skewness and kurtosis** | checkbox | off | — | — |

One row per variable — or per variable and group — with **Variable**,
**Label**, the group, **N**, **Missing**, **Mean**, **SD**, **Min**,
**Median** and **Max**; the checkbox adds **Q1** and **Q3** (linear
interpolation, R's default) and **Skewness** and **Kurtosis** (the
bias-corrected G1 and excess G2 that SPSS and Excel report).

- **A missing code is not an answer.** A declared missing code, and a value
  that is not a number, count in **Missing**; the statistics name them
  (`Missing codes` = `trust_acme: 9`, `Not numbers`). This is the difference
  from **Describe**, which counts what is in the cells.
- **Undefined is blank.** The SD of one answer, skewness below three answers
  and kurtosis below four are empty cells, never `nan`.
- **By group:** a respondent whose group is blank or a missing code is in no
  group (**Not in a group**). A multiple-choice **By group** gives one group
  per option, of everyone who chose it; a respondent who chose two is in both,
  and **Groups** says the groups overlap.
- **On weighted data** the mean, SD, median and quartiles are weighted — the
  same formulas as **Group means**, so the two never disagree — beside a
  **Weighted N** column, while **N** and **Missing** stay counts of
  respondents and **Min** and **Max** those of every answer. A respondent
  weighted 0 (or with no weight) is set aside from the weighted statistics,
  the SD's n included, so one weighted answer has no SD. The statistics add
  **Weight**, **Weighted N**, **Effective N** (Kish), the **Design effect** and
  the **Note** "mean, SD and median are weighted; N and Missing count
  respondents" (with **Quartiles, skewness and kurtosis** ticked: "mean, SD,
  median and quartiles are weighted; N and Missing count respondents; skewness
  and kurtosis are unweighted") — with "; rows weighted 0 are left out of the
  weighted statistics" after "count respondents" when any row weighs 0.

### Factor analysis

`analyze.factor` — "Exploratory factor analysis of a set of items —
loadings, communalities, variance explained, KMO and Bartlett's test, factor
correlations, and factor scores if wanted." It is the check before a set of
items is averaged into a scale: which items move together, how strongly each
belongs to each factor, and whether the items share enough to be factored at
all.

**In:** `data` (SurveyData) → **Out:** `data` (SurveyData), `loadings` (Table), `variance` (Table), `correlations` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Items** | variables (several) | required | ordinal / interval / ratio variables | Three or more, analysed as standardised scores (their correlations). A respondent missing any item is left out; the codebook's missing codes count as missing. |
| **Factors** | whole number | — | at least 1 | Empty chooses the number by the rule below. |
| **Number of factors by** | choice | `kaiser` | `kaiser`, `parallel` | When Factors is empty. kaiser keeps the eigenvalues above 1; parallel keeps the factors whose eigenvalue beats the 95th percentile of 100 random data sets of the same size, drawn from Seed. |
| **Extraction** | choice | `minres` | `minres`, `principal`, `ml` | minres (minimum residual) as psych and factor_analyzer; principal is iterated principal axis factoring; ml is maximum likelihood, as R's factanal, and adds a test of fit; it is started from 14 fixed points and keeps the best, and warns when they disagree (often a sign of too many factors). |
| **Rotation** | choice | `varimax` | `varimax`, `promax`, `oblimin`, `none` | varimax keeps the factors uncorrelated. promax and oblimin let them correlate and report how much (the correlations output); their loadings are the pattern matrix. |
| **Sort items by factor** | checkbox | off | — | — |
| **Hide loadings below** | number | `0` | 0–1 | Blank out the loadings smaller than this in the table (0 shows every loading), so the structure reads at a glance. |
| **Add factor scores** | checkbox | off | — | Regression-method scores, one variable per factor, missing for the respondents left out. |
| **Score variable prefix** | text | `factor_` | — | The scores are named <prefix>1, <prefix>2, … — with Add factor scores on. The prefix itself is not a variable. Shown only with **Add factor scores** ticked. |
| **Seed (parallel analysis)** | whole number | `42` | — | Shown only with **Number of factors by** `parallel`. |

The dropdowns read `minres — minimum residual`, `principal — principal
axis`, `ml — maximum likelihood`; `varimax — orthogonal`, `promax —
oblique`, `oblimin — oblique, quartimin`; `kaiser — eigenvalues above 1`,
`parallel — parallel analysis`.

**The outputs.** The preview shows the three tables one under another, each
under its output's name.

| Output | What it holds |
|---|---|
| `loadings` | one row per item — **Variable**, **Label**, **Factor 1**, **Factor 2**, …, **Communality**, **Uniqueness** and **MSA** (the item's measure of sampling adequacy) |
| `variance` | one row per possible factor — **Eigenvalue**, **% of variance**, **Cumulative %**, then for the factors kept **Extracted SS**, **Extracted %**, **Extracted cumulative %** and, after a rotation, **Rotated SS**; with parallel analysis also **Random 95th percentile** |
| `correlations` | the correlations between the factors — after `promax` or `oblimin`; an orthogonal solution notes "an orthogonal solution: the factors are uncorrelated by construction" |
| `stat` | **Extraction**, **Rotation** ("promax (power 4), Kaiser-normalized"), **Factors**, **Factors chosen by** ("fixed", "Kaiser criterion (eigenvalues above 1)", "parallel analysis (95th percentile of 100 random data sets, seed 42)"), **Items**, **N**, **Variance explained %**, **KMO**, **Bartlett chi-square**, **Bartlett df**, **Bartlett p**, **RMSR**; with `ml` the test of fit, **Fit chi-square**, **Fit df** and **Fit p**; **Warning** when there is something to warn about; **Scores** with **Add factor scores**; **Excluded** and **Excluded because**; **Missing codes** |
| `data` | the data passed on — with **Add factor scores**, plus `factor_1`, `factor_2`, … |

- Each factor is signed so its loadings sum positive, and the factors are
  ordered by the variance they carry. The numbers reproduce R's `psych::fa`
  and the `factor_analyzer` package (and `factanal` for maximum likelihood).
- **Refusals**, with the reason: fewer than three items ("A factor analysis
  needs at least three items; 2 were given."), no more respondents than
  items, an item everyone answered the same, an item that copies or totals
  others, as many factors as items, and with `ml` more factors than maximum
  likelihood can fit ("Maximum likelihood cannot fit 3 factors to 5 items: …
  Use at most 2.").
- **Warnings** (in **Warning**): a KMO below 0.5, an item with (almost) no
  uniqueness left, a rule that suggests more factors than can be fitted (the
  most that fit is used), with `minres` or `principal` more factors than the
  items' correlations can identify, and with `ml`, starts that disagree — a
  reason to compare a solution with fewer factors.
- **Factor scores.** With **Add factor scores** ticked the `data` output
  carries `factor_1`, `factor_2`, … (interval), blank for the respondents
  left out, and later nodes offer them ("factor 1 score · made by *node*") —
  a **Group means** of `factor_1` by region, a **Regression** on them. With
  **Factors** empty the pickers list every score the analysis could make (one
  fewer than the items), the ones after the first as "factor 2 score (empty
  unless the rule keeps it) · made by *node*". The run makes the scores of the
  factors it kept, and of the others the ones a node downstream reads, empty and
  labelled "Factor 2 score (not made: the Kaiser criterion kept 1 factor)";
  **Scores** names them ("factor_1 (regression method); factor_2 empty: the
  Kaiser criterion kept 1 factor"). A score nothing reads is not added, so the
  data, its exports and its tables carry only the scores made and the ones in
  use.
- It is unweighted: on weighted data each table says "Weight: unweighted (the
  weight 'weight' is not applied)". The scores of a later **Group means** are
  weighted as usual.

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
ones need hierarchical Bayes, which **Choice data for HB** exports for. Each
respondent's own counting scores, as variables a crosstab or a cluster can
use, come from **MaxDiff scores** (Prepare). The footer gives the
**Question**, the **Base** ("812 respondents"), **Tasks read**, the
**Method**, the **Reference** item and **Pseudo R²**.

After **Apply weight** every column is weighted: **Shown**, **Best** and
**Worst** are sums of weights (rounded to whole numbers), the **Score**
follows them, and the **Utility** and **Share %** are fitted on the weighted
choices. The footer adds **Weight** and gives the weighted total beside the
people: "812 respondents (798 weighted)". Before this was fixed the
**Utility** and **Share %** columns stayed unweighted; a weighted flow run
again gives different numbers there.

### Group means

`analyze.means` — "Mean, SD, median and N of a variable by group, with a
significance test — chosen for you, or by hand with post-hoc comparisons of
every pair of groups."

**In:** `data` (SurveyData) → **Out:** `table` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Variable** | variable | required | ordinal / interval / ratio variables | The variable whose mean is compared. |
| **By** | variable | required | nominal / ordinal variables | The grouping variable. |
| **Significance test** | checkbox | on | — | Add the significance test. |
| **Test** | choice | `auto` | `auto`, `student`, `welch`, `anova`, `welch_anova`, `mannwhitney`, `kruskal` | Auto chooses by scale and groups (t-test or ANOVA for interval data, Mann-Whitney or Kruskal-Wallis for ordinal). Student and Welch compare two groups (Welch does not assume equal variances), ANOVA and Welch's ANOVA two or more, Mann-Whitney and Kruskal-Wallis compare ranks. A test chosen here reports df and an effect size and leaves the codebook's missing codes out. Auto counts them as answers, as it always has, and says so (Missing codes counted as answers); run Missing values first to leave them out. |
| **Post-hoc** | choice | `none` | `none`, `tukey`, `games_howell`, `dunn` | Every pair of groups compared after the test — Tukey's HSD after ANOVA, Games-Howell after Welch's ANOVA, Dunn after Kruskal-Wallis. The pairs appear under the table. |
| **Dunn p adjustment** | choice | `holm` | `holm`, `bonferroni` | How Dunn's p-values allow for the number of pairs. Tukey and Games-Howell allow for it themselves. Shown only with **Post-hoc** `dunn` (and a **Test** other than `auto`). |

The **Test** dropdown reads `student — Student's t`, `welch — Welch's t`,
`anova — one-way ANOVA`, `welch_anova — Welch's ANOVA`, `mannwhitney —
Mann-Whitney U`, `kruskal — Kruskal-Wallis H`; **Post-hoc** reads `tukey —
Tukey HSD`, `games_howell — Games-Howell`, `dunn — Dunn's test`.

**`auto`** (the default, and what every flow saved before **Test** existed
runs) picks by the variable's scale and the number of groups: Student's
t-test or a one-way ANOVA for interval and ratio data, Mann-Whitney U or
Kruskal-Wallis H for ordinal data. Its footer is a single line such as
"Kruskal-Wallis H = 2.417; p = 0.2986; N = 120; Variable = Satisfaction".

**A test chosen by hand** is named in the footer with its statistic, df, p
and an effect size, and leaves the codebook's missing codes out of the table
and the test ("Missing codes left out = …"):

| Test | Footer |
|---|---|
| `student`, `welch` | **Test** ("Welch's t-test (unequal variances)"), **t**, **df**, **p**, **Mean difference**, **Difference** ("Male − Female"), **95% CI**, **Cohen's d** |
| `anova`, `welch_anova` | **Test** ("One-way ANOVA", "Welch's ANOVA"), **F**, **df** ("2, 237"; Welch's has decimal df), **p**, **η²** |
| `mannwhitney` | **Test**, **U**, **p**, **rank-biserial r** |
| `kruskal` | **Test** ("Kruskal-Wallis H"), **H**, **df**, **p**, **ε²** |

A two-group test asked of more groups is not run and says what to choose
instead: "Test = not run: Welch's t-test (unequal variances) compares two
groups and Region has 3 — choose anova or welch_anova".

**Post-hoc comparisons.** With **Post-hoc** set, the footer adds a summary
("Post-hoc = Tukey HSD: 0 of 3 pairs differ at p < 0.05") and a second table
prints under the means table — in the preview and in the report —
headed **Post-hoc: Tukey HSD**, one row per pair of groups by their value
labels:

| Post-hoc | Columns |
|---|---|
| `tukey` (Tukey-Kramer for unequal groups) | **Pair**, **Difference**, **95% CI low**, **95% CI high**, **q**, **p** |
| `games_howell` | the same, with **df** before **p** |
| `dunn` | **Pair**, **Mean rank difference**, **z**, **p (unadjusted)**, **p (Holm)** (or **p (Bonferroni)**) |

Tukey and Games-Howell give the difference of the means with its
simultaneous interval, the studentized range q and a p that already allows for
the number of pairs; Dunn gives the difference of the mean ranks, z, and p
before and after the adjustment. A p below 0.0001 keeps four significant
digits (`3.363e-07`); a Tukey or Games-Howell p below 1e-07 reads `< 1e-07`,
because the studentized range is not computed finely enough to give a
smaller one — past that point it came out as the same tiny number for every
strong pair. Under the pairs: **Method**, **Groups**,
**Difference** ("mean of the first group minus the second", or for Dunn "mean
rank of the first group minus the second") and, for Tukey and Games-Howell,
**p** "adjusted for the number of pairs by the method itself" — with "; < 1e-07
where it is smaller than SciPy computes the studentized range to" when a pair
reads `< 1e-07`.

**Rules** (errors, then warnings):

- "Tukey's HSD follows a one-way ANOVA — set Test to anova, or Post-hoc to
  none."
- "Games-Howell follows Welch's ANOVA — set Test to welch_anova, or Post-hoc
  to none."
- "Dunn's test follows Kruskal-Wallis — set Test to kruskal, or Post-hoc to
  none."
- "Test is not run while Significance test is off." (warning)
- "Post-hoc is not run while Significance test is off." (warning)

After **Apply weight**, each group's mean, SD and median are weighted (the SD
is scaled so that equal weights give exactly the ordinary sample SD, counting
only the answers that carry weight — a respondent weighted 0 is set aside, and
a group with one weighted answer has no SD, a blank cell; the median is the
value at which the cumulative weight reaches half). **N** stays
the number of respondents, and the significance test and the post-hoc pairs
stay unweighted; the statistics add **Weight** and the note "means, SD and
medians are weighted; N and the test are not", and the post-hoc table says
"Weight: unweighted (the weight 'weight' is not applied)".

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

### Paired tests

`analyze.paired` — "The same respondents answering two or more questions —
Wilcoxon signed-rank or McNemar for two, Friedman for three or more, with
pairwise comparisons." Use it where **Compare groups** would be wrong because
the answers are not from different people: one scale asked about two
brands, a rating before and after a message, three concepts each rated by
everyone.

**In:** `data` (SurveyData) → **Out:** `table` (Table), `pairs` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Variables** | variables (several) | required | — | Two for Wilcoxon or McNemar, three or more for Friedman — asked of the same respondents, on the same answer scale. Differences are the first minus the second (for Friedman's pairs, A − B), as in the paired t-test. A respondent missing any of them is left out of all of them; the codebook's missing codes count as missing. |
| **Test** | choice | `auto` | `auto`, `wilcoxon`, `mcnemar`, `friedman` | Auto runs Wilcoxon signed-rank for two variables and Friedman for more. McNemar is for two yes/no questions. Wilcoxon and Friedman rank the answers, so they refuse a nominal variable. |
| **Counts as yes (McNemar)** | answer code | — | — | The answer code, or a list of codes, that counts as yes; every other answer counts as no. Empty works for 0/1 variables such as the ones Explode multiple choice makes. Shown only with **Test** `mcnemar`. |
| **Same answer twice (Wilcoxon)** | choice | `wilcox` | `wilcox`, `pratt` | wilcox drops the respondents who gave both the same answer before ranking, as R and SPSS do; pratt ranks them with the others and leaves them out of the sums. Shown with every **Test** but `mcnemar` (Friedman's pairwise tests use it too). |
| **p-value** | choice | `auto` | `auto`, `exact`, `approximate` | Auto is exact for small samples — Wilcoxon: up to 50 pairs with no ties or zeros, or up to 13 with them; McNemar: fewer than 25 respondents who answered the two differently — and the normal (Wilcoxon) or chi-square (McNemar) approximation otherwise. |
| **Pairwise comparisons (Friedman)** | choice | `holm` | `holm`, `bonferroni`, `none` | A Wilcoxon signed-rank test for every pair of variables, its p-value adjusted for the number of pairs by Holm's step-down method or by Bonferroni. The pairs output holds them. Shown with **Test** `friedman` or `auto` (auto is Friedman for three or more). |

**Counts as yes (McNemar)** is a checklist of the first variable's answers
(`4 High`, `5 Full`) — tick 4 and 5 for a top-two box. McNemar on variables
that are not 0/1 without it stops with the answers to choose from: "McNemar
needs to know which answer counts as yes: the variables hold 1 = No trust,
2 = Low, 3 = Medium, 4 = High, 5 = Full. Name that code (or a list of codes)
in Counts as yes …". Rule (a warning): "Counts as yes is read only by
McNemar — set Test to mcnemar, or clear it." A number of variables the test
cannot compare is an error of the check, before the run, in the run's own
words: "McNemar compares exactly two variables; 3 were given.", "Friedman's
test compares three or more variables; 2 were given. For two, use Wilcoxon
signed-rank (or McNemar for yes/no)."

**Who is compared.** Each respondent is compared with themselves, so a
respondent who did not answer every variable is left out of all of them
(listwise), and the codebook's missing codes count as missing. The footer
says how many: **Excluded** (91), **Excluded because** ("a missing value in
either variable (listwise)") and **Missing codes** ("95 answers with a
missing code (9 = Refused) left out").

**Direction.** Every difference is the first variable minus the second — as
in the **t-test** with **Design** `paired`, so the two agree in sign. **W+**
sums the ranks of the respondents whose first answer is higher.

What each test gives (the `table` output, with its statistics under it and in
`stat`):

| Test | Table | Statistics |
|---|---|---|
| **Wilcoxon signed-rank** | per variable and for the difference: **N**, **Mean**, **SD**, **Median** | **Difference** ("Trust: Acme − Trust: Globex"), **N**, **Positive differences**, **Negative differences**, **Zero differences**, **W+**, **W-**, **Z**, **p**, **p-value** ("exact" or "normal approximation, tie-corrected"), **r** (Z/√n), **Rank-biserial r**, **Zeros** ("dropped before ranking (Wilcoxon)") |
| **McNemar** | the 2 × 2 table of yes and no on the two variables | **Counts as yes** ("4 = High, 5 = Full"), **N**, **% yes** of each, **Difference (points)**, **Yes only** for each variable (the two discordant counts), **Chi-square** and **df**, or the exact binomial p, **p**, **p-value** ("chi-square with continuity correction", or "exact binomial (12 discordant pairs)"), **Cohen's g**, **Odds ratio** |
| **Friedman** | per variable: **N**, **Mean**, **SD**, **Median**, **Mean rank** | **Variables**, **N**, **Chi-square**, **df**, **p**, **Kendall's W**, **Pairwise** ("Wilcoxon signed-rank, Holm-adjusted p") |

The **`pairs`** output is Friedman's pairwise comparisons: one row per pair —
**Variable A**, **Variable B**, **N**, **Zero differences**, **W+**, **W-**,
**Z**, **p**, **p adjusted**, **r**, **Rank-biserial r** — with "Difference =
A − B" and "Adjustment = Holm (3 comparisons)" under it. The preview shows it
under the main table. With two variables it is empty and says "no pairwise
comparisons: two variables are one comparison; see the table's statistics".

- Everyone giving the same answer twice is a result, not an error: **p** is
  left out and a **Note** says why.
- A nominal variable is refused by Wilcoxon and Friedman, which rank answers;
  use McNemar for yes/no questions.
- None of these tests has a weighted form: on weighted data the statistics
  say "Weight: unweighted (the weight 'weight' is not applied)".

### Principal components

`analyze.pca` — loadings and explained variance of a set of items. Three
outputs: `loadings` (Table), `variance` (Table: eigenvalues and explained
variance) and `stat`; the node's preview shows the loadings, with the
variance table under them (headed **variance**). For latent factors rather
than components — communalities, rotations that let factors correlate, KMO
and Bartlett's test, factor scores — use **Factor analysis**.

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
| **Answer code** | answer code | required | — | The answer whose share you want, picked from the **Variable**'s value labels (`1 — Yes`). For a variable without value labels it is typed as JSON: `1` or `"yes"`. |
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

### t-test

`analyze.ttest` — "Compares means — of two groups (Welch's or Student's
t-test), of two measurements of the same respondents (paired), or of one
variable against a value — with t, df, p, the mean difference and its CI, and
Cohen's d."

**In:** `data` (SurveyData) → **Out:** `table` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Design** | choice | `independent` | `independent`, `paired`, `one_sample` | Independent compares two groups of respondents; paired compares two variables answered by the same respondents; one_sample compares a mean with a fixed value. |
| **Variable** | variable | required | ordinal / interval / ratio variables | — |
| **Groups** | variable | — | nominal / ordinal variables | Independent: the variable that splits the respondents into the groups compared — one answer each; for a multiple-choice question, run Explode multiple choice and use one option's 0/1 column. |
| **Group A** | answer code | — | — | Independent: the code of the first group — needed only when Groups has more than two values. |
| **Group B** | answer code | — | — | The code of the second group. |
| **Variances** | choice | `welch` | `welch`, `student` | Welch's test does not assume the two groups vary equally and is the safer default; Student's pools the variances. |
| **Second measurement** | variable | — | ordinal / interval / ratio variables | Paired: the variable compared with Variable, respondent by respondent. |
| **Test value** | number | `0` | — | One sample: the value the mean is tested against. |
| **Confidence** | number | `0.95` | 0.5–0.999 | — |

**The fields follow Design.** The dropdown reads `independent — two groups`,
`paired — two variables, same people`, `one_sample — a mean against a
value`, and the inspector shows only what that design reads:

| Design | Fields shown | Marked required |
|---|---|---|
| `independent` | **Variable**, **Groups**, **Group A**, **Group B**, **Variances**, **Confidence** | **Groups**; **Group B** once **Group A** is set (and the other way round) |
| `paired` | **Variable**, **Second measurement**, **Confidence** | **Second measurement** |
| `one_sample` | **Variable**, **Test value**, **Confidence** | — |

**Group A** and **Group B** list the answers of the **Groups** variable
(`1 — Male`, `2 — Female`, …), including the bands of a **Bands** node. Leave
both empty when **Groups** has exactly two values.

**Rules** (errors):

- "An independent-samples t-test compares two groups — choose the variable
  that splits them in Groups."
- "A paired t-test compares two measurements of the same respondents —
  choose the second in Second measurement."
- "Name both groups to compare in Group A and Group B, or neither when Groups
  has only two values."

**The table** has one row per group — or per measurement, plus a
**Difference** row for a paired test — with **N**, **Mean**, **SD** and
**SE**, the groups by their value labels:

```
| Gender | N  | Mean   | SD     | SE    |
| Male   | 89 | 54.045 | 23.356 | 2.476 |
| Female | 86 | 55.291 | 24.349 | 2.626 |

Test = Welch's t-test (unequal variances); t = -0.345; df = 172.0; p = 0.7303;
Mean difference = -1.246; Difference = Male − Female; 95% CI = -8.369 – 5.877;
Cohen's d = -0.052; Hedges' g = -0.052; N = 175; Variable = Age
```

| Design | Footer |
|---|---|
| `independent` | **Test** ("Welch's t-test (unequal variances)" or "Student's t-test (equal variances)"), **t**, **df** (Welch's df has decimals), **p**, **Mean difference**, **Difference** (Group A − Group B), the CI (**95% CI**), **Cohen's d**, **Hedges' g**, **N**, **Variable** |
| `paired` | **Test** "Paired t-test", **t**, **df**, **p**, **Mean difference**, **Difference** ("Trust: Acme − Trust: Globex"), the CI, **Cohen's d (d_z)**, **N** (the complete pairs), **Incomplete pairs left out** |
| `one_sample` | **Test** "One-sample t-test", **Test value**, **t**, **df**, **p**, **Mean difference**, **Difference** ("mean − 3"), the CI, **Cohen's d**, **N** |

The difference is always the first minus the second — Group A − Group B,
**Variable** − **Second measurement** — as in **Paired tests**, so a t-test and
a Wilcoxon test of the same two variables agree in sign. The codebook's
missing codes are left out ("Missing codes left out = …").

**Refusals** — the run stops on this node with the reason:

- a **Groups** variable with more than two groups and none named: "Gender has
  3 groups (1 = Male, 2 = Female, 3 = Other); a t-test compares two — name
  them in Group A and Group B.";
- the same group twice: "Group A and Group B are both 1 = Male; a t-test
  compares two different groups — name another in one of them.";
- a missing code named as a group ("… is a missing code of Gender, not a
  group — name two groups that are answers.");
- a multiple-choice **Groups**: "… holds several answers per respondent, so
  its groups overlap and a t-test, which compares two separate groups, cannot
  use them. Run Explode multiple choice and compare by one option's 0/1
  column (chose it or not)."

What the data cannot carry — a group of one, no spread at all — is said in
the footer ("Test = not run: …") rather than as a number.

The t-test has no standard weighted form here: on weighted data it runs on the
respondents as they are and says "Weight: unweighted (the weight 'weight' is
not applied)". For two groups, **Group means** with **Test** `welch` or
`student` runs the same test beside weighted means.

### TURF

`analyze.turf` — how many **different** people a shortlist of options reaches
together: "which three flavors should we stock?" rather than "which three are
most popular" — or, with **Search** `fixed`, what a portfolio you already
have reaches.

**In:** `data` (SurveyData) → **Out:** `table` (Table), `stat` (Stat)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Options** | variables (several) | required | — | One 0/1 column per option. Run prepare.explode on a multiple-choice question to get them. |
| **Largest portfolio** | whole number | `3` | at least 1 | — |
| **Search** | choice | `best` | `best`, `greedy`, `fixed` | Best tries every combination. Greedy extends the previous winner and is fast, but can miss the best portfolio — the table says which ran. Fixed searches nothing and reads the Portfolio below. |
| **Always include** | variables (several) | empty | — | Options that are in the portfolio whatever they add — shelf space already committed. |
| **Portfolio** | variables (several) | empty | — | For Search = fixed: exactly these options — each one's reach, what only it reaches, and the reach and frequency of all of them together. Empty reads every option. |

The **Search** dropdown reads `best — every combination`, `greedy — extend
the winner`, `fixed — the Portfolio as it is`. The inspector shows
**Largest portfolio** and **Always include** for `best` and `greedy`, and
**Portfolio** for `fixed`; the node's card reads "up to 3, best", or for a
fixed portfolio "fixed portfolio" and its options.

- Each respondent is counted once however many options they chose — that is
  what makes it *unduplicated* reach rather than a sum of percentages. The
  base is the respondents who answered; the applied weight is used, and the
  statistics then add **Weight**.
- **`best` and `greedy`:** one row per portfolio size with its options, reach,
  reach %, what it adds to the previous size and its frequency (the mean
  number of a portfolio's options a reached respondent chose). The table and
  the statistics (**Search**) name which search ran, because an exhaustive
  answer and a greedy one are not the same claim.
- **`fixed`:** one row per option of the **Portfolio** — its reach, its
  **unique** reach (the respondents no other option of the portfolio reaches:
  what dropping it would lose) and frequency — then a `(portfolio)` row, "All
  3 together", with the reach and frequency of the whole portfolio. The
  statistics give **Base**, **Search** "none: a fixed portfolio", **Reach**
  ("31.8 %"), **Frequency** and the **Note**. The base is the same as a
  search over **Options** would use: keep all the question's options in
  **Options**.
- **Rules** (warnings): "Always include is not read with Search = fixed, which
  evaluates exactly the Portfolio — add those options to Portfolio." and
  "Portfolio is read only with Search = fixed; best and greedy search for a
  portfolio themselves."
- On weighted data the reach is a sum of weights and the frequency a
  weighted mean.
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
"unweighted (the weight 'weight' is not applied)". For the coefficients with
their p-values, N and a choice of method, use **Correlation matrix**.

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

`output.export_file` — "Write the data as a file (format by extension:
.parquet .csv .xlsx .sav .dta) with its dictionary, as an R bundle (.R), or
the dictionary alone (.json)."

**In:** `data` (SurveyData) → **Out:** none (writes files, a table or a tile)

| Parameter | Type | Default | Allowed | Meaning |
|---|---|---|---|---|
| **Path** | file path | required | — | .parquet, .csv, .xlsx, .sav or .dta write the data and <name>.dictionary.json beside it. .R writes <name>.csv, <name>.dictionary.json and an R script that reads them with factors and NA for the missing codes. .json writes the codebook alone. |

What each extension writes, for **Path** `outputs/clean.<ext>`:

| Extension | Files |
|---|---|
| `.parquet`, `.csv`, `.xlsx` | the data and `clean.dictionary.json` |
| `.sav`, `.dta` | the data with its labels inside (variable labels, value labels, declared missing values) and `clean.dictionary.json` |
| `.R` | an **R bundle**: `clean.csv`, `clean.dictionary.json` and `clean.R` |
| `.json` | the data dictionary (codebook) alone, no data — an error when the data has no codebook |

**The R bundle.** `clean.R` reads `clean.csv` (as UTF-8) and its dictionary
(with the `jsonlite` package) into a data frame named `survey_data`: the
codebook's missing codes become `NA`, labelled codes become factors, and each
column's `label` attribute is the variable's label from the codebook (not the
question's text). A code the codebook has no
label for keeps a level of its own rather than turning into `NA`; a
multiple-choice column (codes joined by `;`) stays text, because a factor
holds one value per respondent; a text answer that reads `NA` stays an
answer. The script finds its two files beside itself, whether you run it with
`Rscript clean.R` or `source("path/to/clean.R")` from R.

The files appear in **Files** and as download chips on the run's card — as
long as **Path** starts with `outputs/`. Written after the cleaning and
weighting steps, the export carries the variables the flow made (recodes,
bands, factor scores, a weight column) with their labels.

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
