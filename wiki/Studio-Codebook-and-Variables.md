# Codebook and Variables

In most survey tools the codebook is something you write afterwards, by hand.
In Studio it is part of the questionnaire: every question writes one or more
**variables**, and each variable carries its scale, label, value labels, valid
range and missing codes. That is why an SPSS export arrives labeled, why tables
show "Satisfied" instead of `4`, and why the research bundle ships a
`codebook.md` nobody had to type. This page covers what a variable has, where
you edit it, and the rules that keep the codebook and the data in step.

---

## What a variable has

| Property | Meaning | Example |
|---|---|---|
| **Name** | the variable's name — the column name in exports and flows | `age`, `region`, `trust_gov` |
| **Scale** | measurement level | nominal · ordinal · interval · ratio |
| **Label** | the human description (SPSS "variable label") | `Age in completed years` |
| **Value labels** | code → meaning | `1 = Woman`, `2 = Man`, `99 = Prefer not to say` |
| **Valid range** | minimum and maximum for numeric answers | `18 … 99` |
| **Missing codes** | codes that mean "no valid answer" | `98 = Don't know`, `99 = Refused` |
| **Description** | a longer note for the codebook | the source of the wording |

Names may contain letters, digits and underscores; other characters turn into
`_` as you type. Keep them short and analysis-friendly — they become column
names everywhere downstream.

> **Note — the variable is the column.** A question's answer is stored under
> its **variable name**, so that is the column name in the Data tab, in
> exports and in flows, and the name conditions, piping and quotas use. The
> question's **Id** may differ from it (a preset starts with Id `q5` and
> variable `nps_5`), but no question's Id may be another question's variable
> name. See
> [Question Id and variable name](Studio-Builder-Overview#question-id-and-variable-name).

---

## What Studio proposes

When you add a question, Studio creates its variable for you:

- **Name** — the question's Id (`q7`); for a preset, the preset's name and
  number (`nps_7`, `yes_no_7`); for a Matrix, `q7_1`, `q7_2`, … one per row;
  for a Multiple choice switched to the wide layout, one per choice named
  after the choice's code (`q7_1`, `q7_2`, …); for MaxDiff and Conjoint, one
  per task plus a version variable (see
  [[MaxDiff and Conjoint|Studio-MaxDiff-and-Conjoint]]). If a name is taken,
  `_2`, `_3`, … is added.
- **Label** — the question's text when the variable is created, or its **Id**
  while the text is still "New question" (so most new questions get the Id);
  for a wide Multiple choice, each choice's label. Write a real label — it is
  what SPSS, the Data tab and every table show.
- **Scale** — from the type:

  | Type | Scale |
  |---|---|
  | Single choice, Multiple choice (both layouts), Open text, MaxDiff, Conjoint | nominal |
  | Likert scale, Matrix rows, Ranking | ordinal |
  | Number | ratio |

- **Value labels** — from the choices, scale points or matrix columns (see
  [Value labels](#value-labels)).

---

## Where you edit variables

### The Variable card

In the Builder, select the question: its **Variable** section (marked
*codebook*) shows one card per variable it writes.

| Field | Notes |
|---|---|
| name | editable, including each variable of a wide Multiple choice; applied when you leave the field or press `Enter` (see [Renaming a variable](#renaming-a-variable)). Matrix, MaxDiff and Conjoint variables are named by the question and cannot be renamed here. |
| scale | **nominal**, **ordinal**, **interval**, **ratio** |
| **Variable label (as in SPSS)** | the label |
| value labels | shown read-only as `1=Strongly disagree · 2 · …` |
| **Min** / **Max** | the valid range; shown only when the scale is **ratio** or **interval** |

### The Codebook tab

**Builder → Codebook** lists every variable in the questionnaire, A–Z, in one
table:

| Column | What it shows |
|---|---|
| **Variable** | the name; a **no entry** pill means a question writes this variable but the codebook has no entry for it |
| **Label** | editable in place (`—` when empty) |
| **Scale** | editable in place |
| **Values** | **N labels** (click to open the row), or the valid range as `18 … 99`, or the data type (click to open the row) |
| **Used by** | the Id of each question that writes the variable — click to jump to it in **Structure** — or **unused** |
| (last) | **Delete**, for a variable no question uses |

Opening a row shows three more fields: **Value labels** (code and label rows,
**+ Label**, and — for a variable a question writes — the hint "choice
questions overwrite these on edit"), **Description** and **Missing codes**
("code, then its label — e.g. -9 Refused, -8 Don't know"; see
[Missing codes](#missing-codes)). With no questions yet the tab says "No
variables yet — every question you add creates one."

The valid range is edited in the Variable card, not in the Codebook tab. A
variable that has a valid range and no value labels shows its range in
**Values** and cannot be opened from there.

---

## Scales, and why they matter

| Scale | Typical question | What the analysis does with it |
|---|---|---|
| **nominal** | single and multiple choice, open text | frequencies, crosstabs, χ² |
| **ordinal** | Likert, matrix rows, ranking | frequencies, medians, rank tests |
| **interval** | scores without a true zero | means, correlations |
| **ratio** | age, counts, money, durations | means, all arithmetic |

The flow nodes use the scale to decide which variables a parameter offers: a
parameter that accepts only some scales says so in its hint (for example
`nominal`) and lists only matching variables. The engine also checks that the
scale fits the question: a Number question on a nominal variable or a Likert
scale on a non-ordinal one gets `INCOMPATIBLE_QUESTION_SCALE`, and a nominal or
ordinal choice variable without value labels gets `CATEGORICAL_WITHOUT_LABELS`.

---

## Value labels

For most question types Studio writes the value labels for you — and rewrites
them **every time you edit the question**, so the codebook always follows the
question:

| Type | Value labels come from | Rewritten on every edit of the question |
|---|---|---|
| Single choice, Multiple choice (array layout), Ranking | the choices | yes |
| Multiple choice (wide layout) | `0` No, `1` Yes on every per-choice variable; the choice's label becomes the variable label | yes |
| Likert scale | the points: `1 — <left label>`, `2`, …, `N — <right label>` | yes |
| Matrix | the columns, coded `1` … *n* | yes (every row variable) |
| MaxDiff | the items | yes (every task variable) |
| Conjoint | "Concept 1" … "Concept *n*" (and the "none" text) | yes (every task variable) |
| Number, Open text | — | no: the labels are yours to write |

So: change answer wording in the question (choices, scale labels, columns), not
in the Codebook tab — edits there to a variable of the types marked "yes" are
overwritten the next time you touch the question (for a wide Multiple choice,
the variable labels too). For a Likert scale this means
the middle points are labeled with their numbers only; if every point needs
words, use a **Single choice** with **Display → buttons** and one option per
point.

Codes are what the data stores; the label is only its meaning. The engine warns
with `OPTION_CODE_WITHOUT_LABEL` when a choice's code has no value label.

---

## Valid range

For **ratio** and **interval** variables, **Min** and **Max** in the Variable
card set the valid range (either can be left empty). For a Number question the
range limits the input and sets the slider's ends. A range whose Min is greater
than its Max makes the questionnaire impossible to save. The engine warns with
`RANGE_LABEL_MISMATCH` when a value label falls outside the range.

The runtime does not stop a respondent from typing an out-of-range number; see
[Number](Studio-Question-Types#number).

---

## Missing codes

A **missing code** is a value that is stored but must not be treated as data:
`98 = Don't know`, `99 = Refused`, `-9 = Not asked`. Declared missing codes:

- are exported as declared missing values in `.sav` and `.dta`, so SPSS and
  Stata honor them without a syntax file;
- are turned into blanks by the **Missing values** node in a flow ("Turn the
  codebook's missing codes into blanks, optionally dropping the rows" — see
  [[Cleaning and Weighting Data|Studio-Cleaning-and-Weighting]]);
- keep means and percentages honest.

Every missing code needs a label — the questionnaire format requires one.

**Declaring missing codes in the Codebook tab**

1. If the code is an answer option (a "Don't know" choice), add it to the
   question's choices first — for example `98` "Don't know" — so it is also a
   value label.
2. In **Builder → Codebook**, open the variable's row (click its **Values**
   entry) and type the codes in **Missing codes**: each code followed by its
   label, entries separated by commas — the field's hint is "code, then its
   label — e.g. -9 Refused, -8 Don't know". `-7=Not asked` works too.
3. Save.

How the field reads what you type:

- A code typed without a label keeps the label it already had; failing that,
  it takes the variable's value label for that code; failing that, it is
  labeled `Missing (<code>)` — so `98` alone becomes `98 Don't know` when
  `98` is labeled "Don't know".
- A code that looks like a number is stored as a number (`-9`), anything else
  as text (`NA`).
- The comma separates entries, so a label cannot contain one.
- The field shows the codes back with their labels, for example
  `-9 Refused, -8 Don't know`.

A missing code that is not among the variable's value labels triggers the
warning `MISSING_CODE_NOT_IN_LABELS` — it still works, but the refusal code
never appears as a category.

**In the Source tab.** Two things need **More ▾ → Source**:

- the **kind** of a missing code. Add `"kind"` to the entry in the variable's
  `"missing"` list:

  ```json
  "missing": [
    {"code": 98, "label": "Don't know", "kind": "dont_know"}
  ]
  ```

  Allowed values are `dont_know`, `not_applicable`, `not_asked`, `refusal`
  and `system_missing` (the default). The Codebook field keeps a kind you set
  here as long as the code stays in the list.
- missing codes for a variable whose Codebook row cannot be opened — one with
  a valid range and no value labels (see [The Codebook tab](#the-codebook-tab)).

Click **Check**, then **Apply**, then Save.

---

## Matrix variables

A matrix writes **one variable per row**, all sharing the column scale as value
labels. A five-statement battery gives five ordinal variables, ready for an
index or a reliability check without reshaping.

Builder-made matrices name their variables `<base>_1`, `<base>_2`, … (for
question `q4`: `q4_1`, `q4_2`, …). They cannot be renamed in the Builder; to
give rows meaningful names (`trust_gov`, `trust_press`), edit the `var` list
and the `variables` entries in the **Source** tab, or start from a question
bank block such as *Trust in institutions*, whose rows are already named. Each
row variable's label ("<question> — <statement>") is set when the row is
created and does not follow later edits of the statement — update it in the
Codebook tab.

---

## Multiple-choice layouts

- **array** — one variable holding the list of selected codes. Exports write it
  as `1;3`; frequency tables use respondents as the base.
- **wide** — one 0/1 variable per choice. Clicking **wide** under **Options →
  Data layout** replaces the question's variable with `<variable>_<code>` for
  each choice (`brands` becomes `brands_1`, `brands_2`), each coded `0` No /
  `1` Yes and labeled with its choice. Adding, removing or relabeling a choice
  keeps the variables in step, and clicking **array** collapses them back
  into one variable. Details in
  [Multiple choice](Studio-Question-Types#multiple-choice).

> **Current limitation.** The published survey does not yet write the wide
> layout as 0/1 columns: real responses arrive as one column named after the
> question's Id, listing the chosen options' variable names, and the
> per-choice variables stay empty (simulated data on **Test** does show 0/1
> columns). Keep **array** for fieldwork, and when an analysis needs one 0/1
> column per option, add an **Explode multiple choice** node in the flow ("One
> 0/1 column per option of a multiple-answer question, so weights,
> regression, clustering and TURF can read it."): **Multiple-choice
> variable**, **Column prefix** (default: the variable's name and an
> underscore, so option 1 becomes `brand_1`) and **Drop the original column**
> (off).

---

## Renaming a variable

Type the new name in the Variable card and press `Enter` (or leave the field).
The name is lower-cased, and if it is taken, `_2` is appended. The new name
gets a fresh codebook entry, the one Studio proposes for a new question: the
question's text (or its Id) as its label, the type's default scale and, for choice
questions, the choices as value labels. A label, scale, valid range, missing
codes or description you had set stay on the **old** entry — copy them over
in the Variable card or the Codebook tab. From then on the question's answers
are stored under the new name.

What renaming does **not** do:

- it does not rewrite **conditions**, **quotas**, **piping** or **scripts**
  that use the old name — they keep pointing at it and silently stop working;
- it does not remove the old entry: it stays in the Codebook tab as
  **unused** (delete it there), and because it still exists no check warns
  about the conditions that refer to it;
- it does not change the question's **Id**. That is fine — the Id and the
  variable name may differ — but do not give a variable the name of another
  question's Id: the Save is then marked `errors` ("Question '…' has the id
  under which question '…' stores its answer; …"). See
  [Question Id and variable name](Studio-Builder-Overview#question-id-and-variable-name).

After a rename, open **Logic map** and **Validation** and update every
condition, quota and pipe that used the old name. Renaming a **page** is
different: page references are updated for you.

---

## Codebook drift across versions

If you rename a variable, add a choice or change a code **after** answers have
been collected, older answers were collected under the old codebook. Two facts
to keep in mind:

- each response records the **environment** that collected it (its survey
  id), not the Save — republishing an environment keeps the same id, so
  answers collected under #17 and #18 look alike in the data;
- data exports label every column with the codebook of the project's
  **current** Save, whatever Save was live when the answers came in.

Every Save keeps its own questionnaire in **History**, so the old codebook is
never lost — but nothing converts old answers for you. Practical rules:

- **Before fieldwork:** rename freely.
- **During fieldwork:** adding a question is safe; renaming a variable or
  recoding options splits your data. Add a new code rather than reusing an old
  one, and never swap codes between options.
- **After a mid-field change:** harmonize the waves with a **Recode** node in
  your flow ([[Cleaning and Weighting Data|Studio-Cleaning-and-Weighting]]).

---

## Where the codebook shows up

- **Data → Export** to SPSS or Stata: variable labels, value labels and
  declared missing values included ([[Data Exports|Studio-Data-Exports]]).
- **Distribute → an environment → Codebook**: the variables of that
  environment's latest build.
- **Flows**: variable pickers show names with labels and offer only variables
  of a suitable scale.
- **Research bundle**: `survey/codebook.md` and the questionnaire document
  ([[Reproducibility: Code, Bundles and Citation|Studio-Reproducibility]]).
- **History → a Save → Methods**: a draft measurement section built from the
  codebook ([[History and Versions|Studio-History-and-Versions]]).

## See also

- [[Question Types|Studio-Question-Types]]
- [[The Builder|Studio-Builder-Overview]]
- [[Data Exports|Studio-Data-Exports]]
- [[Cleaning and Weighting Data|Studio-Cleaning-and-Weighting]]

<!-- studio-nav -->
---

← [[Question Types|Studio-Question-Types]] · [Studio contents](Studio-Overview#all-pages) · [[Logic and Branching|Studio-Logic-and-Branching]] →
