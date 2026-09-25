# Cleaning and Weighting Data

This page turns raw responses into an analysis-ready dataset inside a flow:
removing duplicates, speeders and partial interviews, flagging low-quality
responses, clearing missing codes, recoding and deriving variables, building
scales, weighting — and reporting what you excluded. Each recipe names the
nodes to use; their parameters are in [[Node Reference|Studio-Node-Reference]].

Every step is a node, so every step is visible on the canvas, in the generated
script and in the Methods draft. That is the point: a reader can see exactly
what was done to the data.

---

## The recommended order

```
Responses (or Simulated data)
  → Dedup respondents
  → Speeders & partials
  → Response quality          (flag, or drop)
  → Missing values            (codebook missing codes → blanks)
  → Recode / Derive / Index / Explode multiple choice
  → Cell weights  or  Rake weights
  → Apply weight
  → analysis, charts, report, Write table
```

Why this order:

- **Screen before you weight.** Weights are fitted to the rows that reach the
  weighting node; weighting and then dropping rows leaves weights that no
  longer hit the targets. The AI flow review calls this out as an `ORDER`
  problem.
- **Clear missing codes before any statistic.** A "Refused" coded `99` is a
  real number to a mean until **Missing values** turns it into a blank.
- **Derive after cleaning, weight last.** Derived variables and scales then
  describe only the respondents you keep, and the weighting sees the final
  set of rows.

Use **Run to here** on each node while you build: the preview of every
Prepare node starts with "N rows × M columns", so you can see how many
respondents each step removed. A preview never writes a project table, so
previewing up to a **Write table** node is safe.

Variables you create in a flow — with **Recode**, **Derive**, **Index /
scale**, **Explode multiple choice**, **Response quality**, **Speeders &
partials** — are offered by the variable dropdowns and checklists of the
nodes after them, labeled "*label* · made by *node*": a recoded variable can
go straight into a **Crosstab**, a quality score into a **Filter rows**, a
derived measure into **Group means**. See
[Parameters and variable pickers](Studio-Flows#parameters-and-variable-pickers).

---

## Completed interviews only

A **partial** is an interview that was started but not submitted. Two ways to
exclude them:

- On the **Responses** node, tick **Only completed responses**. The partials
  never enter the flow.
- Or keep them in and use **Speeders & partials** with **Drop partials**,
  which defines "partial" by the answers *you* require (below). This is the
  better choice when some submitted interviews are also unusable because key
  questions are blank.

> **Note.** Partial interviews reach the project only from surveys published
> with the current survey runtime. Once you publish a survey again, its
> partials start arriving, and a flow whose **Responses** node does not tick
> **Only completed responses** includes them — its counts can grow for that
> reason alone. Tick the box, or drop them as above, before you compare with
> earlier runs.

## One row per respondent

**Dedup respondents** keeps one row per `respondent_id` — the latest
submission by default (**Keep** `last`), ordered by **Order by**. On data
collected by Studio a resumed interview already updates its own row, so the
node usually removes little; it matters for imported data and it documents the
step. Rows without a respondent id are kept, each as its own respondent.

## Speeders and partials

**Speeders & partials** adds two columns, `duration_s` and `partial`, and
drops rows. The rule, precisely:

- **Speeder:** the interview length is known and is below **Minimum seconds**
  (default 60). Interviews whose length is unknown are never counted as
  speeders.
- **Partial:** *any* of the variables in **Required answers** is blank. With
  **Required answers** empty, nobody is partial and **Drop partials** removes
  nothing. A variable name that does not exist in the data marks everyone as
  partial — so check what the preview says after this node.

Recipe — drop interviews under 90 seconds and those missing age, region or
satisfaction:

| Parameter | Value |
|---|---|
| **Minimum seconds** | `90` |
| **Required answers** | tick `age`, `region`, `satisfaction` |
| **Drop partials** | on |

> **Tip.** Choose the threshold from your own data: the Distribute screen shows
> the median interview length. A fixed number that is sensible for a
> 5-minute survey removes half the sample of a 2-minute one.

## Quality flags without dropping

**Response quality** checks four things — straightlining across a battery,
contradictions between answers that must agree, duplicate answer patterns, and
failed attention checks — and by default only **marks** responses:

- `quality_flags` — the failed checks, e.g. `straightlining; attention`
  (empty when clean);
- `quality_score` — how many checks failed (0 when clean);
- a second output, a **table** with N and % per check, **Any check** and
  **Clean**, counted over everyone screened.

Recipe:

1. **Battery to check**: tick the items of your grid question.
2. **Straightlining tolerance**: `0` flags only literally identical answers;
   `0.5` also flags near-flat ones.
3. **Answers that must agree**: pairs of variables that should match, as JSON,
   e.g. `{"age_group": "age_group_check"}`.
4. **Attention checks**: click **Fill from the questionnaire (N marked)** to
   take the questions you marked as attention checks in the Builder, or type
   `{"attn_1": 3}`.
5. Leave **Mode** at `flag` while you look at the numbers; wire the **table**
   output into your report.
6. When you have decided, set **Mode** to `drop` — flagged responses are then
   removed, and the table still reports the shares of everyone screened.

To draw the line yourself, keep **Mode** at `flag` and add a **Filter rows**
after it: its condition editor offers `quality_score` and `quality_flags`, so
**Condition** `quality_score` = `0` keeps the clean responses, and
`quality_score` < `2` keeps those that failed at most one check. A condition
on any other variable you created works the same way.

The quality table counts responses, not weights: on weighted data it says
"Weight: unweighted (the weight 'weight' is not applied)".

## Missing values

**Missing values** with **Action** `to_nan` turns every declared missing code
in the codebook ("Don't know", "Refused", …) into a blank, so means, tests and
correlations stop treating `98` and `99` as answers. With `drop_rows` it also
removes the rows that are blank in the variables you list under **Drop rows
missing in** — use it for the few variables every analysis needs. Missing
codes are declared in the Builder; see
[[Codebook and Variables|Studio-Codebook-and-Variables]].

Codes the survey adds for you arrive in the data like any other answer:

- "Not applicable" on a Likert or matrix question is the code the Builder
  declares for it (`-1`, a missing code of kind "not applicable"), so
  `to_nan` clears it too. Where the codebook declares no such code, N/A
  arrives as the text `na`.
- "Other (please specify)" is the question's Other code (`-66` unless the
  question sets another), with the typed text in `<variable>_other`; "None
  of the above" is `-77` unless set. On a variable with a valid range — an
  NPS 0–10, say — the Builder also declares these codes missing, so `to_nan`
  keeps them out of means.

Responses collected before these codes were used are read the same way, so a
flow sees one layout for old and new rows. See
[Responses](Studio-Node-Reference#responses) for how every answer arrives.

## Recoding and harmonizing codes

**Recode** writes a new variable (default name `<variable>_recoded`) from a
code mapping, leaving the original alone.

Collapse a 5-point satisfaction scale to three groups:

| Parameter | Value |
|---|---|
| **Variable** | `satisfaction` |
| **Old code → new code** | `{"1": 1, "2": 1, "3": 2, "4": 3, "5": 3}` |
| **New variable** | `satisfaction_3` |
| **Label** | `Satisfaction (1 = low, 2 = neutral, 3 = high)` |
| **Scale** | `ordinal` |

Harmonize a code list that changed between versions of the questionnaire —
say an option added in a later Save as code `6` that means the same as the
old `5`: map `{"1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 5}`.

Two rules to remember:

- **Every code you do not list becomes blank** in the new variable. List the
  unchanged codes too.
- **The new variable's value labels are its codes** — Recode has no field for
  value labels, so the recoded variable shows `1`, `2`, `3`. Put the meaning in
  **Label** (as above).
- Later nodes offer the recoded variable in their lists — "Satisfaction (1 =
  low, 2 = neutral, 3 = high) · made by recode" — so it goes straight into a
  **Crosstab** or **Banner table**, as well as into formulas, weighting
  targets, exports and written tables.
- **Recode a matrix by its codes.** A matrix answer is the column's codebook
  code — a 0–10 scale is 0–10, also for responses collected before this was
  fixed, which stored the column's position (1–11). A mapping written against
  those positions needs updating.

> **Note.** One **Responses** node reads one environment. There is no node that
> stacks two sources, so comparing `pilot` with `main` means two branches,
> each from its own Responses node.

## Derived variables

**Derive** computes a new variable from a formula — arithmetic, functions and
`if … then … else` (full grammar in
[Derive](Studio-Node-Reference#derive)).

| Goal | New variable | Formula | Scale |
|---|---|---|---|
| Monthly spend from yearly | `spend_month` | `round(spend_year / 12, 2)` | `ratio` |
| Age band | `age_band` | `if age < 30 then 1 else if age < 50 then 2 else 3` | `ordinal` |
| Difference of two ratings | `gap` | `rating_after - rating_before` | `interval` |
| Treat "no children" blanks as zero | `kids` | `coalesce(children, 0)` | `ratio` |

A blank stays blank — a respondent who skipped either rating has no `gap` —
and dividing by zero gives a blank, not infinity. The **Label** defaults to the
formula itself. A typo is reported when you press **Check** or Save, pointing
at the character.

## Scales: reliability, then an index

1. Add **Scale reliability** with the scale's items and preview it: Cronbach's
   alpha, and per item the item–total correlation and "alpha if deleted".
   Drop items that lower alpha, or that you cannot justify.
2. Add **Index / scale** with the kept items: **Index name** `wellbeing`,
   **Method** `mean` (or `sum`), **Label** "Wellbeing index (mean of 5 items)".
3. Put the reliability table in your report next to the index — it is the
   evidence the index is one thing.

Reverse-keyed items: either reverse the item with a **Derive** node first
(**New variable** `q3_r`, **Formula** `6 - q3`) and tick `q3_r` in **Index /
scale**'s **Items** — later nodes offer it — or compute the index directly in
one **Derive**: `mean(q1, q2, 6 - q3, q4)`. The index, like any created
variable, can be picked in the nodes after it and goes to your exports and
written tables.

If you run **Scale reliability** after **Apply weight**, alpha and the
item statistics are weighted (the statistics say `weight`).

## Weighting

Both weighting nodes add a weight column (default `weight`), scaled to a mean
of 1 so the weighted N equals the number of rows. Neither applies it: follow
them with **Apply weight**.

### Cell weights or raking?

| | **Cell weights** | **Rake weights** |
|---|---|---|
| Matches | the full distribution of **one** variable | the margins of **several** variables at once |
| Needs | targets for that variable's categories | a target distribution per variable, not the joint cells |
| Use when | one variable drives the imbalance, or you have joint targets (weight on a combined variable made with **Derive**) | you know region, gender and age targets separately, as census tables usually give them |

**Targets.** Shares or counts, as JSON with codes as keys; each set is
normalized, so `{"1": 45, "2": 55}` equals `{"1": 0.45, "2": 0.55}`.

Cell weights on region:

```json
{"1": 0.45, "2": 0.30, "3": 0.25}
```

Raking on region and gender (**Targets (variable → code → share)**):

```json
{
  "region": {"1": 0.45, "2": 0.30, "3": 0.25},
  "gender": {"1": 0.48, "2": 0.52}
}
```

- A category you leave out keeps its current share.
- **Cap** limits extreme weights (weights of mean 1 are clipped to the cap and
  rescaled). It must be greater than 1; with a cap the targets are matched
  only approximately.
- Raking stops when no margin changes by more than **Tolerance** (default
  `1e-06`) or after **Max iterations** (default 50).
- A multiple-answer variable cannot be weighted on — a respondent in two
  categories has no single cell. Weight on a single-answer variable, or on the
  0/1 columns of **Explode multiple choice**.

### Checking the weights

After **Apply weight**, add a **Frequencies** node for each weighting variable
and preview it: the **%** column should equal your targets (45 % for code `1`
of `region`), with the respondents actually counted in the **Unweighted N**
column beside it. For a share with its confidence interval, use a
**Proportion CI** with **Weighted** ticked — for example **Variable**
`region`, **Answer code** `1` — which should give 0.45 (its base is the
respondents who answered `region`, and its `n` is their effective base). A
**Bar chart** of `region` draws the weighted counts ("Weighted count" on the
axis), and a **Banner table** with the weighting variables as questions also
shows weighted percentages. Large caps, or targets far from the sample, are
the usual reasons for a miss.

### Making tables and tests use the weight

**Apply weight** tells the dataset which column to use. Its palette
description says what follows: "Weight the results downstream by a column.
Weighted results say so, and a result with no weighted form says it is
unweighted." From there on:

- **Frequencies** and **Crosstab** — counts and percentages are sums of
  weights. A frequency table shows the unweighted N in a column beside them, a
  crosstab in its statistics (with the chi-square test on), and the
  crosstab's chi-square test uses Kish's effective base.
- **Group means** — weighted means, SDs and medians; N and the significance
  test stay unweighted, and the table says so.
- **Banner table** (tests on Kish's effective base), **Net Promoter Score**,
  **Regression** and **TURF**.
- **MaxDiff** — every column, **Utility** and **Share %** included;
  **Conjoint** part-worths and importances; **Share of preference**.
- **Principal components** and **Scale reliability**.
- **Bar chart** (weighted counts, or weighted means with **By**) and
  **Heatmap** with **By** (weighted means) — so a chart matches the weighted
  table beside it.
- **Proportion CI**, when its **Weighted** box is ticked.

These have no weighted form and say so — "unweighted (the weight 'weight' is
not applied)" in their statistics, table or chart title: **Compare groups**,
**Correlation**, **Cluster (k-means)**, **Box plot**, **Scatter plot**,
**Heatmap** without **By**, **Proportion CI** unticked, and the tables of
**Response quality** and **Code open answers**. **Describe** counts rows and
adds a `weighted_n_valid` column. Say in the section's note which results are
weighted where a reader could miss it. The details per node are in
[Apply weight](Studio-Node-Reference#apply-weight).

> **Note.** MaxDiff utilities and shares, Conjoint, Share of preference,
> Principal components, Scale reliability, the Bar chart and the Heatmap of
> means used to ignore the weight, and a weighted Proportion CI counted
> non-respondents in its base. A weighted flow run again gives the corrected
> numbers; reports from earlier runs keep the old ones.

## Writing the cleaned data to a table

To clean once and analyze in several flows:

1. End the cleaning flow with **Write table**: **Table name** `clean_responses`,
   **If it exists** `replace`.
2. Start each analysis flow with **Project table**, **Table** `clean_responses`.
3. Use **Run all** (or schedule it) to refresh everything. It sees that the
   analysis flows read `clean_responses` and runs the cleaning flow before
   them, whatever the flows are called. If the cleaning flow fails, the flows
   that read its table are not run — they are marked failed with "skipped:
   needs cleaning, which failed" (for a cleaning flow named `cleaning`) —
   rather than analyzing yesterday's table; flows that do not read it still
   run. See [Run all](Studio-Flows#run-all).
4. Running one analysis flow on its own reads `clean_responses` as it is: it
   does not run the cleaning flow first. After new responses arrive, run the
   cleaning flow (or **Run all**) before you rerun an analysis flow.
5. The table also appears on the **Data** screen.

Things to know:

- **The table keeps its variables.** **Write table** stores the variables of
  the columns it writes — labels, scales and value labels — with the table, so
  the variables the cleaning flow *created* (`satisfaction_3`,
  `quality_score`, `cluster`) arrive in the reading flow labeled. Its
  variable dropdowns offer them as "from table clean_responses · made by
  cleaning", and naming one passes the engine check at Save. A table last
  written before tables kept their variables has no labels for them yet: run
  the cleaning flow once more. A weight column travels too; **Apply weight**
  takes its name as text.
- **A preview never writes the table.** **Run to here** on a Write table node
  (or **Preview all**) shows what a run would write — "Not written: a
  preview never writes project tables. A run writes … rows to table
  'clean_responses' (if it exists: replace)." — and leaves the table as it
  is. See [Run to here](Studio-Flows#run-to-here-and-preview-all).
- In a research bundle made with data, **Write table** is skipped and
  **Project table** reads `data/tables/clean_responses.csv` — the table as it
  was when the bundle was made, with its variables beside it — so the
  analysis flows reproduce what they computed in Studio from that table, but
  running the cleaning flow there does not refresh it; see
  [[Reproducibility|Studio-Reproducibility]].

## Reporting exclusions

A methods section should say how many responses each step removed. Ways to
get the numbers into your report and onto Live:

- **Response quality**'s table output, wired into a **Report section**: N and
  % per check, **Any check** and **Clean**.
- A **Live tile** with **Show** `rows`, connected to the data after the last
  cleaning step (label it "Clean respondents"). Add one before and one after
  cleaning to see both counts on the Live screen.
- The preview of each Prepare node ("N rows × M columns") while you build —
  write the counts into the section's **Note**, e.g. "Base: 1,247 of 1,402
  completed interviews; 96 speeders under 90 s and 59 straightliners
  excluded."
- The Methods draft (History → a Save → **More ▾ → Methods**) lists every step
  of every flow with its parameters. For **Apply weight** it writes
  "estimates that support weights were weighted by `weight` (rank tests,
  k-means clustering, box and scatter plots and correlation heatmaps stay
  unweighted)".

## See also

- [[Node Reference|Studio-Node-Reference]]
- [[Analysis Flows|Studio-Flows]]
- [[Data Quality|Studio-Data-Quality]]
- [[Codebook and Variables|Studio-Codebook-and-Variables]]
- [[Reports|Studio-Reports]]

<!-- studio-nav -->
---

← [[Node Reference|Studio-Node-Reference]] · [Studio contents](Studio-Overview#all-pages) · [[Coding Open Answers|Studio-Open-Answer-Coding]] →
