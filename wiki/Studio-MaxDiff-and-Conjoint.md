# MaxDiff and Conjoint

**Best–worst (MaxDiff)** and **Conjoint (choice)** are the two question types
that measure preference by making people trade things off. Studio builds the
experimental design for you, shows each respondent their share of it, records
which version they saw, and analyzes the choices in a flow. This page covers
when to use each, every option, how the design works, what respondents see,
the variables written and the analysis nodes.

---

## Which one to use

| | Best–worst (MaxDiff) | Conjoint (choice) |
|---|---|---|
| The question it answers | Which of these items matter most — and by how much? | Which product would people choose, and what would they give up for what? |
| What the respondent compares | a handful of single **items** (claims, features, messages) | whole **products** that differ on several **attributes** at once |
| Each task | pick the best and the worst of 3–5 items | pick one of 2–4 products (optionally "none") |
| Result | a score and a utility per item, and the share it implies | a part-worth per level, each attribute's share of the decision, and simulated market shares |
| Rule of thumb | 8–30 items, 4 per task | 2–6 attributes of 2–5 levels, 3 products per task |

Rating a long list on a scale gets ratings that all sit near the top, because
nothing forces a choice; asking directly how important price is gets an answer
everybody gives the same way. In both designs here, the trade-off *is* the
measurement.

---

## MaxDiff

### Building a MaxDiff question

**+ Question → Best–worst (MaxDiff)**. The **Options** section:

| Option | Meaning | Default | Rules |
|---|---|---|---|
| **Items** ("shown a few at a time") | the list being compared — code · label, like any choice list | Item 1 … Item 6 | at least 3 items; unique codes; non-empty labels |
| **Items per task** | how many items one task shows | 4 | at least 2, and fewer than the number of items |
| **Tasks** | how many tasks one respondent answers | 8 | at least 1 |
| **Versions** ("different respondents, different tasks") | how many different sets of tasks exist | 20 | at least 1 |
| **Best is called** | heading of the "best" column | Best | |
| **Worst is called** | heading of the "worst" column | Worst | |

Under the fields Studio shows how often each item is seen:

> Each respondent sees 8 × 4 of 6 items — about 5.3 showings each.

(With no items: "Add items to see how often each is shown.") That number is
the one to watch: it is per respondent, and if it is small every estimate rests
on very little. Across respondents, **Versions** spread the items so that
between them they cover far more combinations than any one person sees.

A second note says what the design is made from:

> The design is worked out from the question’s Id, the item codes and the
> numbers above, the same way on every build. Change any of them after
> fieldwork starts and later respondents get a different design from earlier
> ones.

See [How the design works](#how-the-design-works).

### What the respondent sees (MaxDiff)

All tasks appear **on one page**, one small table per task:

```
 Best            Worst
  ○   Low price    ○
  ●   Fast delivery ○
  ○   Free returns  ●
  ○   Eco packaging ○
```

- one pick in each column per task; an item cannot be both best and worst —
  picking it on one side releases it from the other;
- the question counts as answered only when **every** task has both a best and
  a worst; with **Required** on, **Next** stays blocked until then.

### Variables written (MaxDiff)

Two per task, plus the design version — 17 variables for 8 tasks:

| Variable | Holds | Codebook |
|---|---|---|
| `<name>_t1_best` | the code of the item picked as best in task 1 | nominal, the items as value labels, label "… — task 1, best" |
| `<name>_t1_worst` | the code of the item picked as worst in task 1 | nominal, the items as value labels, label "… — task 1, worst" |
| … | … up to `<name>_t8_worst` | |
| `<name>_version` | which version of the design this respondent saw (`0`, `1`, …) | nominal, no value labels, label "… — design version" |

`<name>` is the question's variable base (`q7` for a question `q7`). The list
is rebuilt whenever you change **Tasks** — lowering it removes the variables
and codebook entries of the tasks that went — and the variables cannot be
renamed by hand. Value labels you write for the items in the Codebook tab stay
until you change that item's label in **Items**.
The version variable is not bookkeeping: without it nobody can read the picks,
because knowing somebody chose "Price" says nothing until you know what Price
was up against.

Later pages can use these variables like any other: a **Show if** or a branch
rule on `q7_t1_best`, or `{label:q7_t1_best}` in a question text to name the
item picked as best in task 1.

### Checks (MaxDiff)

| Where | Message | Meaning |
|---|---|---|
| Save refused ("…/choices: needs at least 3 entries (page …, question 'q7')") | fewer than three items | a best and a worst need at least three items |
| Validation → Structure | "q7: a best–worst question needs at least three items" | same, while you edit |
| Validation → Structure | "q7: showing 6 of 6 items means every task shows everything, and nothing is learned from which items met" | lower **Items per task** or add items |
| Validation → Engine, Save `warnings` | `MAXDIFF_COMPLETE_DESIGN` (error) — "MaxDiff 'q7' shows 6 of 6 items per task, so every task shows everything: nothing is learned from which items met. Show fewer items per task." | same |
| Validation → Engine, Save `warnings` | `MAXDIFF_SINGLE_VERSION` (warning) — "… has one version of the design, so every respondent sees the same tasks. More versions cover more of the item space." | legal, rarely intended |

Lint findings, even error-level ones, do not stop a Save; they mark it
`warnings`. An error-level finding such as `MAXDIFF_COMPLETE_DESIGN` is still
called an error: the Save toast says "Saved #18 — the questionnaire has 1
error (see Builder → Validation)", and publishing asks you to confirm with
**Publish #18 with errors** → **Publish anyway**. Read **Validation** before
you publish.

---

## Conjoint

### Building a conjoint question

**+ Question → Conjoint (choice)**. The **Options** section:

**Attributes** ("what the products vary on") — one card per attribute:

- **name** (placeholder `name`) — a plain identifier (letters, digits, `_`,
  not starting with a digit); it becomes a column in the results;
- **label** (placeholder "What the respondent reads") — the row heading the
  respondent sees (the name is used if empty);
- **Move up**, **Move down**, **Remove attribute**;
- its **levels** — code · label, like any choice list, with the note "First
  level is the reference: the others are read against it." The first level's
  position is not cosmetic: every other level's part-worth is measured against
  it.

**+ Attribute** adds `attr3` with two levels. The defaults are **Brand** (Brand
A, Brand B) and **Price** (Low, High).

| Option | Meaning | Default | Rules |
|---|---|---|---|
| **Products per task** | how many products are shown side by side | 3 | at least 2 |
| **Tasks** | how many choices one respondent makes | 10 | at least 1 |
| **Versions** ("different respondents, different products") | how many different sets of tasks exist | 20 | at least 1 |
| **“None of these”** ("leave empty to force a choice", placeholder `I would buy none of these`) | adds a "none" option to every task | empty | |

Adding "none of these" changes what the question measures: with it, shares
are of a market that includes people who buy nothing; without it, of the
people who buy something.

Under the fields Studio says whether the design can be estimated:

> 3 part-worths to estimate from 200 choice tasks across all versions.

The part-worths are one per level beyond each attribute's first; the choice
tasks are **Tasks × Versions**. When the tasks are fewer than twice the
part-worths the line ends "— that is thin; add tasks or versions." instead of
the period. (With no attributes: "Add attributes and levels to see whether the
design can be estimated.")

A second note says what the design is made from:

> The design is worked out from the question’s Id, the attributes and their
> level codes and the numbers above, the same way on every build. Change any
> of them after fieldwork starts and later respondents get a different design
> from earlier ones.

### What the respondent sees (conjoint)

All tasks appear **on one page**. Each task shows its position (`1 / 10`), a
grid with the attributes as rows and one column per product, a button under
each product (✓ when chosen) and, if configured, the "none of these" choice
below:

```
 1 / 10
            ┌──────────┬──────────┬──────────┐
 Brand      │ Brand A  │ Brand B  │ Brand A  │
 Price      │ Low      │ High     │ High     │
            │   [ ]    │   [✓]    │   [ ]    │
            └──────────┴──────────┴──────────┘
 ○ I would buy none of these
```

On a narrow screen the grid scrolls sideways. Every task must be answered for
the question to count as answered.

### Variables written (conjoint)

One per task — which product was chosen — plus the design version:

| Variable | Holds | Codebook |
|---|---|---|
| `<name>_t1` … `<name>_t10` | `1` … *n* for the product chosen, left to right; *n*+1 for "none of these" | nominal, labels "Concept 1" … "Concept *n*" (and the none text), label "… — task 1" |
| `<name>_version` | which version of the design this respondent saw | nominal, no value labels, label "… — design version" |

One variable per task, not one per attribute: the answer *is* the choice, and
which levels it carried is in the design. Lowering **Tasks** removes the
variables and codebook entries of the tasks that went. As for MaxDiff, later
pages can test and pipe the task variables.

### Checks (conjoint)

| Where | Message | Meaning |
|---|---|---|
| Save refused (for example "…/attributes: needs at least 2 entries (page …, question 'q9')") | fewer than two attributes, an attribute with fewer than two levels, an attribute name that is not a plain identifier, two attributes with the same name, two levels with the same code | fix the attributes |
| Validation → Structure | "q9: a conjoint needs at least two attributes to trade off", "attribute name "x y" must be a plain identifier — it becomes a column in the results", "attribute "x" needs at least two levels — one level is a constant", "two attributes share a name" | same, while you edit |
| Validation → Engine, Save `warnings` | `CONJOINT_NOT_ESTIMABLE` (error) — "Conjoint 'q9' cannot be estimated: 2 tasks of 3 across 1 version cannot pin down 7 part-worths. Add tasks, add versions, add alternatives, or use fewer levels." | the design cannot be fitted at all — found before anyone is interviewed |
| Validation → Engine, Save `warnings` | `CONJOINT_SINGLE_VERSION` (warning) — "… has one version of the design, so every respondent sees the same products." | legal, rarely intended |

`CONJOINT_NOT_ESTIMABLE` does not stop the Save or the publish — no lint does
— but it is reported as an error: the Save toast counts it ("the
questionnaire has 1 error") and publishing asks you to confirm with **Publish
anyway**. Read **Validation** before you publish.

---

## How the design works

- The design — which items or products each task of each version shows — is
  computed by the engine from the question's **Id**, its parameters (**Items
  per task** or **Products per task**, **Tasks**, **Versions**), its **item
  or level codes** and, for a conjoint, the **attribute names**. The same
  inputs always give the same design, on any computer, so the published
  survey, the preview, the generated `questionnaire.py` and the analysis all
  agree.
- Nothing freezes the design: it is worked out again on every build, which is
  what the Inspector's note says. **Changing the Id, the items or levels (or
  their codes), the attribute names, Items/Products per task, Tasks or
  Versions produces a different design** — and after fieldwork has started,
  later respondents get that different design. Wording is not an input: item
  and level labels can change without touching the design.
- A questionnaire can carry a `seed` for the question, or the design itself,
  written in the **Source** tab. With a seed, the note names it instead of the
  Id ("The design is worked out from the seed (1234), …"). With a stored
  design, the note reads "The design is stored in the questionnaire (see
  Source) and used as it is; changing the items or the numbers above clears
  it." (for a conjoint: "changing the attributes or the numbers above clears
  it") — the design is then derived again from the new inputs. Any edit in
  **Items** or **Attributes** clears a stored design, a change to a label
  included.
- MaxDiff designs are balanced across versions: each item is shown about
  equally often, and pairs of items meet about equally often.
- Each respondent is dealt one version, drawn from their respondent id:
  respondents are spread over the versions, and a respondent who reloads the
  page or resumes the interview gets the same tasks back. The version is
  written into `<name>_version`.

> **Important.** Once fieldwork has started, do not change a MaxDiff or
> conjoint question at all — not even its Id. The analysis reads the design
> from the current questionnaire, and answers collected under an earlier
> design would be read against the wrong tasks. If you must change it, create
> a new question (with new variables) and treat the two as separate
> measurements. Labels (the wording of items and levels, attribute labels, and
> the Best/Worst headings) can be corrected safely: the design depends on the
> codes and names, not the words. The exception is a design stored in the
> questionnaire (see above): editing an item's or a level's label in the
> Builder clears it, and the design is worked out anew.

---

## Analyzing the results

Add the nodes below to a flow after a **Responses** (or other) source. Each
takes the question's Id (or name) and reads its design from the questionnaire —
nothing has to be re-entered. See [[Analysis Flows|Studio-Flows]] and
[[Node Reference|Studio-Node-Reference]].

> **In the example study.** A project started from the
> [example study](Studio-Projects#the-example-study) has a MaxDiff with its
> answers: "Which of these would matter most to you in the app, and which
> least?" (Id `app_md`) — eight features of an app idea, four per task, six
> tasks, 20 versions (so each item is shown three times to each respondent),
> with **Best is called** `Most` and **Worst is called** `Least`. The flow
> `wellbeing_app` runs the **MaxDiff** node on it (node `maxdiff`), and the
> flow `segments` gives each respondent their scores (**MaxDiff scores**,
> node `scores`), draws the segments' mean scores as a heatmap and saves the
> choices for a hierarchical Bayes estimate (**Choice data for HB**, node
> `hb`). See [The example study's flows](Studio-Flows#the-example-studys-flows).

### MaxDiff node

"What a best–worst question found — one row per item, with the counting score,
the conditional-logit utility and the share it implies."

| Parameter | Values |
|---|---|
| **MaxDiff question** | the question's Id |
| **Estimate** | `both` (default), `counts`, `utilities` — "Counting is best minus worst over shown and anyone can recount it. Utilities are a conditional logit on the choices the design actually showed." |

The table has one row per item, best first: **Item**, **Shown**, **Best**,
**Worst**, **Score** (best minus worst, divided by shown — you can check it by
hand) and, unless **Estimate** is `counts`, **Utility** and **Share %**. The
summary lists the question, the base ("247 respondents"), the tasks read, the
method, the reference item, a warning if the model did not converge, and how
many answers could not be read.

After **Apply weight**, every column is weighted: **Shown**, **Best** and
**Worst** are sums of weights (rounded to whole numbers), the **Score** is
computed from them, and **Utility** and **Share %** are fitted on the weighted
choices. The summary adds "Weight: *column*", and the base reads
"247 respondents (231.4 weighted)". See
[Apply weight](Studio-Node-Reference#apply-weight).

To chart it, connect the node's `table` to a **Result chart**: the utilities
with their 95 % intervals against the reference item at 0 (`utilities`, what
`auto` draws), the counting scores (`scores`) or the shares (`shares`); with
**Estimate** `counts`, the scores. See
[Chart a MaxDiff or TURF result](Studio-Recipes#chart-a-maxdiff-or-turf-result).

### MaxDiff scores (per respondent)

The **MaxDiff** node describes everyone together. To break preferences down
by segment — a crosstab by region, a cluster, a regression — the **MaxDiff
scores** node (Prepare) gives each respondent their own counting score for
every item: "One counting-score variable per MaxDiff item, per respondent —
best minus worst over the times it was shown — so the preferences can go into
a crosstab, a cluster or a regression."

| Parameter | Values |
|---|---|
| **MaxDiff question** | a dropdown of the questionnaire's MaxDiff questions |
| **Variable prefix** | "Each item's score is <prefix><item code>. Defaults to the question and _score_, so item 3 of q_md becomes q_md_score_3." |

Each variable, labeled "MaxDiff score: *item*", runs from −1 (picked worst
every time the respondent saw it) to 1 (picked best every time); a
respondent who never saw an item has a blank for it, not a 0. With a few
tasks per person the scores are coarse, but they are what each respondent
actually chose — no model is involved. They are counts per person, so no
weight enters them; a **Group means** of a score after **Apply weight** is
weighted as usual. A question name the questionnaire does not have is named
at **Check** and at Save ("… no MaxDiff question named 'q_mdx'; this
questionnaire has: q_md."). See
[MaxDiff scores per respondent in a crosstab](Studio-Recipes#maxdiff-scores-per-respondent-in-a-crosstab).

### Choice data for HB (MaxDiff)

For individual-level utilities, **Choice data for HB** writes "A MaxDiff's
answers in the long format R's hierarchical Bayes packages read, with a column
dictionary and a script that runs it."

| Parameter | Values |
|---|---|
| **MaxDiff question** | the question's Id |
| **Path** | "Written as `<name>.csv`, with `<name>.dictionary.json` and `<name>.hb.R` beside it. The file has no weight column (the HB packages take none), so an applied weight is not in it; weight the individual utilities when you aggregate them." |

You then run hierarchical Bayes on your own machine, with as many draws as it
needs.

### Conjoint node

"Part-worths and attribute importance from a choice-based conjoint — what
people gave up to get what."

| Parameter | Values |
|---|---|
| **Conjoint question** | the question's Id |

The table has one row per level: **Attribute**, **Level**, **Part-worth**
(`0` for each attribute's first, reference level) and **Importance %** — the
attribute's share of the decision. The summary adds the base, the tasks read,
the method (conditional logit, aggregate) and the note "importance is of the
levels tested, not of the attribute in general": price from £10 to £12 will
look unimportant beside price from £10 to £100. After **Apply weight** the
part-worths, and so the **Importance %**, are fitted on the weighted choices;
the summary adds "Weight: *column*" and gives the weighted base beside the
respondents ("247 respondents (231.4 weighted)"). A **Result chart** of its
`table` draws each attribute's importance (`importance`) or the part-worths
of its levels, in the design's order (`partworths`).

### Share of preference

"What the estimated part-worths predict a market of these products would do."
This answers "what if we changed the price".

| Parameter | Values |
|---|---|
| **Conjoint question** | the question's Id |
| **Products** | JSON: a name for each product → one level **code** per attribute, e.g. `{"Ours": {"brand": 1, "price": 2}, "Theirs": {"brand": 2, "price": 1}}`. "A half-specified product has no utility." |
| **Include "none of these"** | off by default — "Only when the question offered it. Leaving it out rescales everyone who would have walked away into buyers." |

The table has one row per product with its utility and predicted share (%).
A summary goes with it: **Question**, **Base** ("247 respondents"), **Method**
("logit rule on aggregate conditional-logit part-worths") and **Note**
("shares of the products listed, not market shares", or with **Include "none
of these"**: "shares of the products listed and of choosing none, not market
shares"). After **Apply weight** the shares come from the weighted
part-worths, the base adds the weighted total, and the summary names the
**Weight**. A **Result chart** of its `table` draws each product's share.

### Conjoint data for HB

**Conjoint data for HB** writes "A conjoint's choices in the long format R's
hierarchical Bayes packages read, with a column dictionary and a script that
runs it." Parameters: **Conjoint question** and **Path** (written as
`<name>.csv`, `<name>.dictionary.json` and `<name>.hb.R`). As for MaxDiff,
the file has no weight column: an applied weight is not in it, so weight the
individual utilities when you aggregate them.

---

## Pitfalls

- **Editing after launch.** Any change to the Id, codes or design parameters
  changes the design (see above). Pilot in `pilot`, then freeze the question.
- **Too few showings.** A MaxDiff where each item is seen once or twice per
  respondent gives noisy scores; add tasks or show more items per task.
- **Thin conjoint designs.** Heed "that is thin" and `CONJOINT_NOT_ESTIMABLE`
  before fieldwork, not after.
- **Unbalanced levels.** A price range that is too narrow makes price look
  unimportant; test the range you actually care about.
- **Required.** Both types count as answered only when every task is done; with
  many tasks, consider leaving **Required** off and checking completeness in the
  analysis ("Unreadable answers" in the summary).
- **The reference level.** Put the level you want to compare against first in
  each attribute.

## See also

- [[Question Types|Studio-Question-Types]]
- [[Analysis Flows|Studio-Flows]]
- [[Node Reference|Studio-Node-Reference]]
- [[Testing Your Survey|Studio-Testing-Your-Survey]]

<!-- studio-nav -->
---

← [[Quotas and Randomization|Studio-Quotas-and-Randomization]] · [Studio contents](Studio-Overview#all-pages) · [[Theme and Branding|Studio-Theme-and-Branding]] →
