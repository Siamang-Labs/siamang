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
  ├→ Data check              (values against the codebook — a table, not a filter)
  → Dedup respondents
  → Speeders & partials
  → Response quality          (flag, or drop)
  → Missing values            (codebook missing codes → blanks)
  → Recode / Derive / Bands / Index / Explode multiple choice
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

Variables you create in a flow — with **Recode**, **Derive**, **Bands**,
**Index / scale**, **Explode multiple choice**, **MaxDiff scores**,
**Response quality**, **Speeders & partials**, and the scores of a **Factor
analysis** — are offered by the variable dropdowns and checklists of the
nodes after them, labeled "*label* · made by *node*": a recoded variable can
go straight into a **Crosstab**, a quality score into a **Filter rows**, a
derived measure into **Group means**. See
[Parameters and variable pickers](Studio-Flows#parameters-and-variable-pickers).

---

## Checking the data against the codebook

Before you clean, look at what is in the data. **Data check** (Analyze),
wired to the source, lists the values outside a variable's valid range, codes
the codebook has no label for, duplicate IDs and columns the codebook does
not declare — one row per problem, errors first, each with how many rows have
it and examples (`17 (1), 999 (1)`). It reads the codebook's
missing codes as what they are, so a declared 999 "Refused" is not flagged as
out of range, and it expects the weight column and the response metadata
(`respondent_id`, `duration_s`, the `url_*` parameters, …). With nothing
wrong it reads "no problems found".

It changes nothing: fix a wrong code with **Recode**, leave impossible values
out with **Filter rows**, or correct the codebook in the Builder. Wire its
table into your report's methods section. See
[Data check](Studio-Node-Reference#data-check).

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

The newer analyses leave missing codes out on their own and say how many:
the **t-test**, **Correlation matrix**, **Paired tests** (Cochran's Q too),
**Factor analysis**, **Key drivers**, **Perceptual map**, **Price
sensitivity**, **Regression** with **Model** `ordinal`, **Bands**, and any
test you choose by hand (**Correlation** `pearson` or `kendall`, a **Group
means** **Test** other than `auto`, **Compare groups** with Dunn's test,
**Crosstab** with Fisher's test). So do the newer charts: the **Likert
chart**, the **Trend**, a **Heatmap** with **Method** `pearson` or `kendall`
or with **By** and **Color map** `theme`, and a **Bar chart** with **Show**
`percent`, **Split by**, **Sort** `value`, **Top N**, **Confidence
intervals**, or **Layout** `histogram` or `donut` — each names what it left
out under the plot ("Left out as missing: Trust: Acme: 108 (9 = Refused)").
The **Tab book (Excel)** leaves them out of every sheet and lists them on its
Notes sheet.
**Descriptive statistics** leaves them out too but counts them in its
**Missing** column, with the blanks, and names the codes rather than counting
them ("Missing codes = trust_acme: 9"). The defaults that were there before — **Correlation**
`spearman`, **Group means** `auto`, **Compare groups** without Dunn's test,
the **Crosstab** chi-square — still count a code as an answer, so that a
stored flow keeps its numbers, and now say so: "Missing codes counted as
answers = Trust: Acme: 44 (9 = Refused); run Missing values first to leave
them out". The classic **Bar chart** (**Show** `count`, no **Split by**,
**Sort** `code`, no **Top N** or intervals), the Spearman **Heatmap** and a
**Heatmap** of means with a named **Color map** also draw such a code as an
answer, as they always have. **Missing values** before them settles it for
every node.

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
  **Label** (as above). Where the labels matter in the table, make the
  variable with **Derive** and its **Value labels** instead, or cut a number
  with **Bands**, which labels its bands.
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
| Age band | `age_band` | `if age < 30 then 1 else if age < 50 then 2 else 3`, **Value labels** `{"1": "Under 30", "2": "30–49", "3": "50 or over"}` | `ordinal` |
| Difference of two ratings | `gap` | `rating_after - rating_before` | `interval` |
| Treat "no children" blanks as zero | `kids` | `coalesce(children, 0)` | `ratio` |

A blank stays blank — a respondent who skipped either rating has no `gap` —
and dividing by zero gives a blank, not infinity. The **Label** defaults to the
formula itself. A typo is reported when you press **Check** or Save, pointing
at the character. **Value labels** (code → label, as JSON) name the codes of
a formula that yields codes, so tables of it print "Under 30" rather than
`1`.

### Bands

For the age band above, **Bands** does it in one step and labels the bands
itself: **Variable** `age`, **Boundaries** `[18, 30, 50, 100]`, **New
variable** `age_band` gives an ordinal variable with the bands "18 to under
30", "30 to under 50" and "50 to under 100" (or your own **Band labels**,
`["18–29", "30–49", "50+"]`). A band includes its lower boundary and runs up
to, not including, the next; tick **Bands include their upper boundary** for
the other way round. Its advantages over a formula: the variable's missing
codes are taken out first, so a 999 "Refused" never lands in the top band,
and its statistics count each band and whatever fell outside every band —
which stays blank rather than being forced into the nearest one. See
[Bands](Studio-Node-Reference#bands).

## Scales: reliability, then an index

Whether a set of items measures one thing or several is a question for
**Factor analysis**: its loadings show which items move together, and KMO and
Bartlett's test whether the items share enough to be factored at all (see
[Exploratory factor analysis with scores](Studio-Recipes#exploratory-factor-analysis-with-scores)).
For each scale it finds:

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
axis) — with **Show** `percent`, the weighted percentages ("% of respondents
(weighted)"), which should read 45 % for code `1` — and a **Banner table**
with the weighting variables as questions also shows weighted percentages.
Large caps, or targets far from the sample, are the usual reasons for a
miss.

### Making tables and tests use the weight

**Apply weight** tells the dataset which column to use. Its palette
description says what follows: "Weight the results downstream by a column.
Weighted results say so, and a result with no weighted form says it is
unweighted." From there on:

- **Frequencies** and **Crosstab** — counts and percentages are sums of
  weights. A frequency table shows the unweighted N in a column beside them, a
  crosstab in its statistics (with **Significance test** on), and the
  crosstab's chi-square test uses Kish's effective base. Fisher's exact test
  needs whole counts, so it counts respondents and says so.
- **Group means** — weighted means, SDs and medians; N, the significance
  test and the post-hoc pairs stay unweighted, and the table says so.
- **Descriptive statistics** — weighted mean, SD, median and quartiles
  beside a **Weighted N** column, with Kish's effective N and the design
  effect in its statistics; N, Missing, skewness and kurtosis are not
  weighted.
- **Correlation** and **Correlation matrix** with **Method** `pearson` — the
  weighted coefficient, with p (and the CI) on Kish's effective base.
- **Banner table** (tests on Kish's effective base), **Net Promoter Score**,
  **Regression** (linear, logistic and ordinal) and **TURF** (reach and
  frequency).
- **MaxDiff** — every column, **Utility** and **Share %** included;
  **Conjoint** part-worths and importances; **Share of preference**.
- **Principal components** and **Scale reliability**.
- **Key drivers** — the correlations, betas, R² and shares, with the tests
  on Kish's effective N.
- **Perceptual map** — every cell of the table it maps is a sum of weights
  (its chi-square test counts respondents, and says so).
- **Price sensitivity** — every curve and share; **N** stays the
  respondents.
- **Bar chart** (weighted counts, weighted percentages — split into groups
  too, in a histogram and a donut too — or weighted means with **By**; its
  confidence intervals and significance letters on Kish's effective base),
  **Heatmap** with **By** (weighted means) or with **Method** `pearson`
  (weighted coefficients), the **Likert chart** (weighted shares) and the
  **Trend** (weighted percents, means and counts, its band on Kish's
  effective base) — so a chart matches the weighted table beside it.
- **Tab book (Excel)** — every sheet's counts are sums of weights, beside
  the unweighted base, its percentages are of those sums, and its letters
  test on Kish's effective base.
- **Result chart** — as the result it draws; its title's second line says
  which.
- **Proportion CI**, when its **Weighted** box is ticked.

These have no weighted form and say so — "unweighted (the weight 'weight' is
not applied)" in their statistics, table or chart title: **Compare groups**,
**Correlation** and **Correlation matrix** with `spearman` or `kendall`,
**t-test**, **Paired tests** (Cochran's Q among them), **Factor analysis**,
**Cluster (k-means)**, **Box plot**, **Scatter plot**, **Heatmap** without
**By** with **Method** `spearman` or `kendall`, **Proportion CI** unticked,
the tables of **Response quality**, **Code open answers** and **Data check**,
and the counts of **MaxDiff scores** and **Bands** (the variables they make
are weighted like any other in the tables after them). A **Result chart** of
one of these results says so in its title too. **Describe** counts rows and
adds a `weighted_n_valid` column. Say in the section's note which results are
weighted where a reader could miss it. The details per node are in
[Apply weight](Studio-Node-Reference#apply-weight).

> **Note.** MaxDiff utilities and shares, Conjoint, Share of preference,
> Principal components, Scale reliability, the Bar chart and the Heatmap of
> means used to ignore the weight, and a weighted Proportion CI counted
> non-respondents in its base; TURF's frequency was unweighted. A weighted
> flow run again gives the corrected numbers; reports from earlier runs keep
> the old ones.

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
  k-means clustering, box and scatter plots and Spearman and Kendall
  correlation heatmaps stay unweighted, as do t-tests, the tests of group
  means (ANOVA, Welch's ANOVA) and their post-hoc comparisons, paired tests
  (Cochran's Q among them), Fisher's exact test, a perceptual map's
  chi-square test, rank correlations and factor analysis)".
- **Data check**'s table, for "the data were screened for out-of-range
  values and undeclared codes".

## See also

- [[Node Reference|Studio-Node-Reference]]
- [[Analysis Flows|Studio-Flows]]
- [[Data Quality|Studio-Data-Quality]]
- [[Codebook and Variables|Studio-Codebook-and-Variables]]
- [[Reports|Studio-Reports]]

<!-- studio-nav -->
---

← [[Node Reference|Studio-Node-Reference]] · [Studio contents](Studio-Overview#all-pages) · [[Coding Open Answers|Studio-Open-Answer-Coding]] →
