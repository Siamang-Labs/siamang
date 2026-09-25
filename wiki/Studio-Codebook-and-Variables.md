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
> name. An Id that differs from its variable also may not be a name the
> survey stores something else under: a Matrix row or other variable of any
> question, a question's `<variable>_other`, the variable an **Assign
> to a condition** writes, or a codebook variable no question collects that a
> custom script writes. See
> [Names an Id may not take](Studio-Builder-Overview#names-an-id-may-not-take).

---

## What Studio proposes

When you add a question, Studio creates its variable for you:

- **Name** — the question's Id (`q7`); for a preset, the preset's name and
  number (`nps_7`, `yes_no_7`); for a Matrix, `q7_1`, `q7_2`, … one per row;
  for a Multiple choice switched to the wide layout, one per choice named
  after the choice's code (`q7_1`, `q7_2`, …); for MaxDiff and Conjoint, one
  per task plus a version variable (see
  [[MaxDiff and Conjoint|Studio-MaxDiff-and-Conjoint]]). If a name is taken —
  by a variable, a codebook entry or another question's Id — `_2`, `_3`, … is
  added.
- **Label** — the question's text when the variable is created, or its **Id**
  while the text is still "New question" (so most new questions get the Id);
  for a wide Multiple choice, each choice's label; for a Matrix row, "<question
  text> — <statement>". Write a real label — it is what SPSS, the Data tab and
  every table show.
- **An extra variable for Other** — a question with **Add “Other (please
  specify)”** on also gets `<variable>_other` (for a wide Multiple choice,
  `<Id>_other`) for the typed text: nominal, text, labeled "<question text> —
  other (please specify)". Its **Used by** is the question, and it follows the
  question's variable when you rename it.
- **Scale** — from the type:

  | Type | Scale |
  |---|---|
  | Single choice, Multiple choice (both layouts), Open text, MaxDiff, Conjoint | nominal |
  | Likert scale, Matrix rows, Ranking | ordinal |
  | Number | ratio |

- **Value labels** — from the choices, scale points or matrix columns, plus
  the codes that **Other**, **None of the above** and **N/A** store (see
  [Value labels](#value-labels) and
  [Codes for Other, None of the above and N/A](Studio-Question-Types#codes-for-other-none-of-the-above-and-na)).

---

## Where you edit variables

### The Variable card

In the Builder, select the question: its **Variable** section (marked
*codebook*) shows one card per variable it writes.

| Field | Notes |
|---|---|
| name | editable, including each variable of a wide Multiple choice and each row variable of a Matrix; applied when you leave the field or press `Enter` (see [Renaming a variable](#renaming-a-variable)). MaxDiff and Conjoint variables are named by the question and cannot be renamed here. |
| scale | **nominal**, **ordinal**, **interval**, **ratio** |
| **Variable label (as in SPSS)** | the label |
| value labels | shown read-only as `1=Strongly disagree · 2 · …` |
| **Min** / **Max** | the valid range; shown only when the scale is **ratio** or **interval** |

Under the cards, a Matrix adds "Matrix rows write one variable each, in the
order of Options → Rows; rename a row's variable here." Once the
questionnaire has been published, the section also says: "This questionnaire
has been published. Renaming a variable renames its column in the data:
answers already collected keep the old name, answers collected after you
publish again get the new one."

### The Codebook tab

**Builder → Codebook** lists every variable in the questionnaire, A–Z, in one
table:

| Column | What it shows |
|---|---|
| **Variable** | the name; a **no entry** pill means a question writes this variable but the codebook has no entry for it |
| **Label** | editable in place (`—` when empty) |
| **Scale** | editable in place |
| **Values** | **N labels** (click to open the row), or the valid range as `18 … 99`, or the data type (click to open the row) |
| **Used by** | the Id of each question that writes the variable (for `<variable>_other`, the question whose Other text it holds) — click to jump to it in **Structure** — or **unused** |
| (last) | **Delete**, for a variable no question uses |

An **unused** entry whose name is a question's Id is usually what an earlier
version of the Builder left behind when it renamed that question's variable
(`q2` renamed to `comment` kept `q2`). **Validation → Structure** lists it —
"q2: the codebook still declares a variable "q2" that no question collects
and nothing writes — delete it in the Codebook tab" — and **Delete** removes
it. The question's Id can stay as it is. If a custom script writes that name
(`answers.q2 = …`), nobody can tell whether the script means the question or
the codebook variable, and the Id is flagged instead ("q2: the id is a
codebook variable a custom script writes — …"): rename the Id if the script
means the codebook variable, or delete the entry if it means the question
(see [Names an Id may not take](Studio-Builder-Overview#names-an-id-may-not-take)).

Opening a row shows three more fields: **Value labels** (code and label rows,
**+ Label**, and — for a variable a question writes — the hint "a code keeps
its label here until the question changes that code's choice or scale
point"), **Description** and **Missing codes**
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

For most question types Studio writes the value labels for you and keeps them
in step with the question — but only as far as the question changes:

| Type | Value labels come from |
|---|---|
| Single choice, Multiple choice (array layout), Ranking | the choices, plus the codes Other and None of the above store |
| Multiple choice (wide layout) | `0` No, `1` Yes on every per-choice variable; the choice's label becomes the variable label |
| Likert scale | the points: `1 — <left label>`, `2`, …, `N — <right label>`, plus the N/A code |
| Matrix | the columns, under the codes they store — `1` … *n* for a matrix you build — plus the N/A code, on every row variable |
| MaxDiff | the items, on every task variable |
| Conjoint | "Concept 1" … "Concept *n*" and the "none" text, on every task variable |
| Number, Open text | — the labels are yours to write |

The rule: **a code keeps the label the Codebook has for it until an edit of
the question changes that code's own choice, scale point, column, item or
concept label.** Then that code takes the question's new label. So:

- a label you write in the Codebook tab survives editing the question text,
  its hint, **Required**, or another choice — for a Likert scale you can label
  the middle points (`3 = Neither agree nor disagree`) in the Codebook, and
  they stay;
- relabeling a choice, column or item in the question replaces that code's
  label in the Codebook;
- a code the question stops using (a removed choice) loses its label;
- a code you added by hand in the Codebook, which the question never had,
  stays.

The same goes for the variable labels that follow a part of the question: a
wide Multiple choice variable takes its choice's new label only when that
choice is relabeled, and a Matrix row variable is relabeled "<question text> —
<statement>" only when the question text or that statement changes. A label
you write for either in the Codebook stays through every other edit.

Codes are what the data stores; the label is only its meaning. The engine warns
with `OPTION_CODE_WITHOUT_LABEL` when a choice's code has no value label.

### Value labels in the Source tab

In **More ▾ → Source** a variable's `"labels"` can be written two ways:

- as a list, `[{"code": 1, "label": "Low"}, {"code": 2, "label": "High"}]`,
  which keeps the order you write;
- as an object, `{"1": "Low", "2": "High"}`, a shorthand whose order does not
  survive storage (the database and the browser each reorder its keys). Studio
  reads it in one fixed order whatever you typed: codes `0` and up, ascending,
  then the negative codes from `-1` down, then text codes in the order
  written — `{"-9": …, "-8": …, "2": …, "1": …}` reads `1`, `2`, `-8`, `-9`.

The order the labels are read in — the list's, or this fixed one — is the
order in which a question that takes its options from the codebook shows
them, the order a matrix lines its headers up with (see
[Matrix](Studio-Question-Types#matrix)), and the order of a MaxDiff's items
(and so its design, when none is stored). To choose another order, write the
list.

---

## Valid range

For **ratio** and **interval** variables, **Min** and **Max** in the Variable
card set the valid range (either can be left empty). For a Number question the
range limits the input and sets the slider's ends. A range whose Min is greater
than its Max makes the questionnaire impossible to save. The engine warns with
`RANGE_LABEL_MISMATCH` when a value label falls outside the range.

For a Number question the survey enforces the range: a number typed below
**Min** or above **Max** shows "Minimum value is …" or "Maximum value is …"
and **Next** does not move on until it is corrected; see
[Number](Studio-Question-Types#number).

On a variable with a valid range (an NPS 0–10, a CES 1–7), the codes that
**Other** and **None of the above** store (`-66`, `-77`) are also declared as
missing codes, so the range check and the means leave them out.

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

**Declared for you.** Turning on **Offer “N/A”** on a Likert scale or a Matrix
declares the not-applicable code itself: `-1 Not applicable`, of kind
*not applicable*, with the value label `-1 = Not applicable` — on every row
variable of a matrix (except a matrix without column headers, which keeps
storing `na`; see [Matrix](Studio-Question-Types#matrix)). The survey then
stores `-1` for N/A instead of the text `na`. Turning the option off leaves the declaration in place, so answers
already stored with `-1` stay missing. See
[Codes for Other, None of the above and N/A](Studio-Question-Types#codes-for-other-none-of-the-above-and-na).

**In the Source tab.** Two things need **More ▾ → Source**:

- the **kind** of a missing code (other than the not-applicable code **Offer
  “N/A”** declares for you). Add `"kind"` to the entry in the variable's
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
question `q4`: `q4_1`, `q4_2`, …). To give rows meaningful names
(`trust_gov`, `trust_press`), rename them in the question's **Variable**
section, which has a name field per row, in the order of **Options → Rows**
(hover a row's number there to see its variable) — or start from a question
bank block such as *Trust in institutions*, whose rows are already named.

Each row keeps its own variable: removing a row removes its variable and its
codebook entry, and the rows below keep theirs, so their data columns stay
where they were. A new row gets the next free `<base>_<n>`, with the first
row's value labels, missing codes and valid range. Each row
variable's label reads "<question text> — <statement>" and follows edits of
the statement; a label you write yourself in the Codebook tab stays until the
question text or that statement changes.

The answer stored for a row is the code of the chosen column, as the value
labels give it: `1` … *n* in a matrix you build, `0` … `10` in *Trust in
institutions*. Renaming a column keeps its code, and moving or removing a
column leaves the other columns' codes as they are. A new column takes the
code of the codebook label with exactly its text, and a column renamed to the
label of a declared missing code that no column stores (a "Refusal" beside a
declared `77` Refusal) takes that code. A declared missing code whose column
you remove keeps its value label here. In a codebook that came with an
import, a header naming a declared missing code stores that code wherever the
codebook lists it. See [Matrix](Studio-Question-Types#matrix).

---

## Multiple-choice layouts

- **array** — one variable holding the list of selected codes. Exports write it
  as `1;3`; frequency tables use respondents as the base.
- **wide** — one 0/1 variable per choice. Clicking **wide** under **Options →
  Data layout** replaces the question's variable with `<variable>_<code>` for
  each choice (`brands` becomes `brands_1`, `brands_2`), each coded `0` No /
  `1` Yes and labeled with its choice. Adding, removing or relabeling a choice
  keeps the variables in step, and clicking **array** collapses them back
  into one variable. In the data each per-choice variable is `1` when the
  option was chosen, `0` when the question was answered without it, and empty
  when the question was not answered or the option was hidden by its own
  condition. Conditions, piping and quotas on a per-choice variable
  (`brands_1 = 1`) work, and so do exclusive choices. Details in
  [Multiple choice](Studio-Question-Types#multiple-choice).

Responses collected by a survey built before the wide layout was stored this
way — one column named after the question's Id, listing the chosen options'
variables — are read into the per-choice variables in the Data tab, exports
and flows: `1` for each chosen option, `0` for the others. See
[Older surveys and responses](Studio-Question-Types#older-surveys-and-responses).

For an **array** question, when an analysis needs one 0/1 column per option,
add an **Explode multiple choice** node in the flow ("One 0/1 column per
option of a multiple-answer question, so weights, regression, clustering and
TURF can read it."): **Multiple-choice variable**, **Column prefix** (default:
the variable's name and an underscore, so option 1 becomes `brand_1`) and
**Drop the original column** (off).

---

## Renaming a variable

Type the new name in the Variable card and press `Enter` (or leave the field).
The name is lower-cased, and if it is taken — by another variable, a codebook
entry or another question's Id — `_2` is appended. From then on the
question's answers are stored under the new name.

Renaming renames the variable **everywhere the questionnaire uses it**:

- the question that writes it;
- its **codebook entry**, which moves across whole — label, scale, value
  labels, valid range, missing codes, description — and keeps its place, so
  no **unused** entry is left behind under the old name;
- **conditions**: **Show if** / **Hide if** on pages, blocks, questions and
  options, and **Branch (next if)** rules;
- **quotas** on the variable;
- **piping**: `{answer:…}` and `{label:…}` in question texts, hints, page
  titles and bodies;
- **scripts**: a script whose target was the variable, and the answer
  accesses in custom JavaScript (`answers.old_name`, `answers["old_name"]`);
- the Other text column: `old_name_other` becomes `new_name_other`.

What renaming does **not** do:

- it does not change a string inside custom JavaScript that merely holds the
  name (`"old_name"` passed to a function) — check your scripts;
- it does not change **flows**: a flow whose nodes name the old variable
  fails the engine's check at the next Save — it is marked with errors and
  cannot run — until you pick the new name in those nodes
  ([[Analysis Flows|Studio-Flows]]);
- it does not change the question's **Id** — the Id and the variable name may
  differ (see
  [Question Id and variable name](Studio-Builder-Overview#question-id-and-variable-name));
- it does not rename collected data. Once the questionnaire has been
  published, the Variable section warns: "This questionnaire has been
  published. Renaming a variable renames its column in the data: answers
  already collected keep the old name, answers collected after you publish
  again get the new one."

Renaming a **page** updates its references for you too (branch rules,
**Default next**, **Skip to** and page scripts).

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
