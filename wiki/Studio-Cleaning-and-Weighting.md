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
respondents each step removed.

> **Current limitation.** The variable dropdowns and checklists of later nodes
> list the **questionnaire's** variables only. Variables you create in a flow
> — with **Recode**, **Derive**, **Index / scale**, **Explode multiple
> choice** — are kept in the data, written by **Export file** and **Write
> table**, and listed by **Describe**, but cannot yet be picked in, say, a
> **Crosstab** or **Group means**. Parameters you *type* can use them:
> weighting targets, **Apply weight**'s column, and **Derive** formulas. If a
> derived measure must appear in your tables today, consider computing it in
> the questionnaire.

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

> **Current limitation.** **Filter rows** offers only the questionnaire's own
> variables, so you cannot filter on `quality_score` (or on any variable a
> flow creates) from the condition editor. Use **Mode** `drop` to exclude
> flagged responses.

## Missing values

**Missing values** with **Action** `to_nan` turns every declared missing code
in the codebook ("Don't know", "Refused", …) into a blank, so means, tests and
correlations stop treating `98` and `99` as answers. With `drop_rows` it also
removes the rows that are blank in the variables you list under **Drop rows
missing in** — use it for the few variables every analysis needs. Missing
codes are declared in the Builder; see
[[Codebook and Variables|Studio-Codebook-and-Variables]].

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
- Today the recoded variable reaches exports and written tables, and can be
  used in formulas and weighting targets; it cannot yet be picked in a table
  node (see the limitation above).

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

Reverse-keyed items: reverse them inside the formula of a **Derive** node
that computes the index directly — `mean(q1, q2, 6 - q3, q4)` — since items
recoded in the flow cannot yet be picked in **Index / scale**'s item list. The
index, like any created variable, goes to your exports and written tables.

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

After **Apply weight**, add a **Proportion CI** for a category of each
weighting variable with **Weighted** ticked — for example **Variable**
`region`, **Answer code** `1` — and preview it: the share should equal your
target (0.45). A **Banner table** with the weighting variables as questions
also shows weighted percentages. Large caps, or targets far from the sample,
are the usual reasons for a miss.

### Making tables and tests use the weight

**Apply weight** tells the dataset which column to use.

> **Current limitation.** Not every node uses the applied weight yet.
> **Weighted:** **Banner table** (tests on Kish's effective base), **Net
> Promoter Score**, **Regression**, **TURF**, and **Proportion CI** with
> **Weighted** on. **Unweighted even after Apply weight:** **Frequencies**,
> **Crosstab**, **Group means**, **Compare groups**, **Correlation**,
> **MaxDiff**, **Conjoint**, **Share of preference**, **Cluster (k-means)**,
> **Principal components**, **Scale reliability** and the charts. For weighted
> percentages in a report, use a **Banner table**; for a weighted share with
> its interval, **Proportion CI**. Say in the table's note which results are
> weighted.

## Writing the cleaned data to a table

To clean once and analyze in several flows:

1. End the cleaning flow with **Write table**: **Table name** `clean_responses`,
   **If it exists** `replace`.
2. Start each analysis flow with **Project table**, **Table** `clean_responses`.
3. **Name the flows so the cleaning flow sorts first** — `a_clean`,
   `b_tables`, `c_models`. **Run all** runs flows in alphabetical order of
   their names and nothing else decides the order; if `b_tables` ran first it
   would read yesterday's table. Flows cannot be renamed yet, so choose names
   when you create them. (The example study's `cleaning` and `tables` happen
   to sort correctly.)
4. The table also appears on the **Data** screen.

Things to know:

- **A table holds rows and columns, not codebook entries.** The reading flow
  labels columns from the questionnaire's codebook, so variables the cleaning
  flow *created* (`satisfaction_3`, `quality_score`, `cluster`) arrive without
  labels, cannot be picked in the reading flow's variable dropdowns, and a node
  that names one fails the engine check. Create derived variables in the flow
  that analyzes them (or recreate them there). A weight column is fine: **Apply
  weight** takes its name as text.
- **Run to here** on a Write table node (or **Preview all**) writes the table
  for real — see [Run to here](Studio-Flows#run-to-here-and-preview-all).
- In a research bundle, **Write table** is skipped and **Project table** reads
  the raw responses file, so chained flows do not reproduce there; see
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
  of every flow with its parameters.

## See also

- [[Node Reference|Studio-Node-Reference]]
- [[Analysis Flows|Studio-Flows]]
- [[Data Quality|Studio-Data-Quality]]
- [[Codebook and Variables|Studio-Codebook-and-Variables]]
- [[Reports|Studio-Reports]]

<!-- studio-nav -->
---

← [[Node Reference|Studio-Node-Reference]] · [Studio contents](Studio-Overview#all-pages) · [[Coding Open Answers|Studio-Open-Answer-Coding]] →
