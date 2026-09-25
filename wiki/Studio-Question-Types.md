# Question Types

Studio has **nine question types** and **eight presets** — a preset is one of
the types, pre-configured the way "NPS" is really an 11-point scale. Every type
maps onto a class of the siamang engine, so every question you build exports to
`questionnaire.py`, to a labeled `.sav`, and into the analysis nodes. This page
describes each type: what the respondent sees, every option in the Inspector,
how the answer is coded, and the rules that apply.

For the Builder screen itself see [[The Builder|Studio-Builder-Overview]]; for
the codebook side of each question see
[[Codebook and Variables|Studio-Codebook-and-Variables]].

---

## The types at a glance

| **+ Question** menu label | What the respondent does | Variables written | Scale |
|---|---|---|---|
| **Single choice** | picks one option | 1 | nominal |
| **Multiple choice** | picks any number of options | 1, or 1 per choice in the wide layout | nominal |
| **Likert scale** | picks a point on a numbered scale or stars | 1 | ordinal |
| **Number** | types a number or moves a slider | 1 | ratio |
| **Open text** | types text, an email, a phone number, a web address, a date or a time | 1 | nominal (text) |
| **Matrix** | rates several statements on one shared scale | 1 per row | ordinal |
| **Ranking** | puts items in order | 1 | ordinal |
| **Best–worst (MaxDiff)** | picks the best and the worst of a few items, several times | 2 per task + 1 | nominal |
| **Conjoint (choice)** | picks one of several products, several times | 1 per task + 1 | nominal |

Presets: **Yes / No**, **Rating (stars)**, **NPS (0–10)**, **CES (1–7)**,
**Attention check**, **Date**, **Email**, **Phone** — see [Presets](#presets).

---

## Fields every question has

| Field | Where | Notes |
|---|---|---|
| **Question text** | Question | Shown as plain text: Markdown and HTML are not rendered. Piping works: `{answer:variable}` inserts an earlier answer, `{label:variable}` the chosen option's label (for an Other answer, the text the respondent typed). |
| **Hint** | Question | Smaller text under the question ("optional guidance shown below the question"); piping works here too. |
| **Required** | Question | The respondent cannot continue without answering: **Next** shows "This question requires an answer." A Matrix asks for an answer in **every row** (the checkbox's hint says "an answer in every row", or "an answer in every row — N/A counts" when the matrix offers N/A) — see [Matrix](#matrix); MaxDiff and Conjoint ask for every task. Required questions show an asterisk to respondents. New questions start **optional**. |
| **Randomize option order** | Question | Shuffles the options per respondent. Single choice, Multiple choice and Ranking only. "None of the above", exclusive choices (such as "None of these") and a choice that is the question's Other keep their place; the other options are shuffled around them. The "Other" option Studio adds always comes last. |
| **Attention check** | Question | Single choice, Likert scale, Number and Open text — see [Attention checks](#attention-checks). |
| **Variable** | Variable | The codebook entry the question writes — [[Codebook and Variables\|Studio-Codebook-and-Variables]]. A variable name starting with `__` is flagged here ("Variables starting with “__” are the survey runtime’s own: it never submits __x, so these answers never reach the data. Rename the variable."): the survey never submits such a key. |
| **Show if** / **Hide if** / **Skip to** | Logic | [[Logic and Branching\|Studio-Logic-and-Branching]]. |
| **Id** | Advanced | The question's own handle ("names the question in scripts and comments; logic and data use the variable"): scripts target it, comments hang on it, checks quote it. Letters, digits and `_` (other characters turn into `_`). Must be non-empty, unique, and not the variable name of another question — the field says "Another question already has this id." or "This is the variable … stores its answer under — the engine refuses an id that is another question’s variable." An Id that differs from the question's variable may not start with `__`, nor be a name the survey stores something else under (a Matrix row, another question's Other text, an assigned arm, a codebook variable a custom script writes): the field says why, for example "This is where brand stores the text typed into Other — scripts naming it would reach this question’s variable instead." An Id that is the question's own variable is never flagged for this. See [Names an Id may not take](Studio-Builder-Overview#names-an-id-may-not-take). |
| **Tags** | Advanced | Free labels, comma-separated, for your own organization of the instrument. |
| **Media URL** | Advanced | An image, or a video if the link ends in `.mp4`/`.webm`, shown with the question ("a public https:// address; a file under Files has no public link"). Use a stable public URL (a download link from **Files** expires after 5 minutes). |

To respondents, questions are numbered `Q01`, `Q02`, …

> **Note — Id and variable name.** The answer is stored under the question's
> **variable name**: that is its column in your data, and the name conditions,
> piping and quotas use. The **Id** may differ from it — a preset starts with
> Id `q5` and variable `nps_5` — as long as no question's Id is another
> question's variable name or, for an Id that differs from its variable,
> another name the survey stores something under. Details:
> [Question Id and variable name](Studio-Builder-Overview#question-id-and-variable-name).

### The options editor

Single choice, Multiple choice, Ranking, MaxDiff items and conjoint levels all
use the same list editor ("code · label"):

- each row has a **Code** (what is stored), a **Label** (what is shown), **Move
  up**, **Move down** and **Remove option**;
- **+ Option** adds "Option N" with the next free code (the highest numeric
  code + 1);
- `Enter` in a label adds a blank option under it;
- a code that looks like a number is stored as a number (`3`), anything else
  as text (`dk`).

Codes must be unique and every label must have text — an empty label or a
duplicate code makes the questionnaire impossible to save (see
[What the engine refuses](#what-the-engine-refuses)).

---

## Single choice

One answer from a list.

**The respondent sees** radio buttons, a dropdown or a row of buttons. The
dropdown is searchable: it shows "— Select —", a search box ("Type to search…")
and "No options found" when nothing matches. It works from the keyboard too:
`Enter`, `Space` or `↓` opens it, `↓` / `↑` move through the options, typing
narrows them, `Enter` chooses and `Esc` closes (see
[Keyboard and touch](Studio-Respondent-Experience#answering)).

**Inspector → Options**

| Option | Values | Default |
|---|---|---|
| **Display** | **radio** · **dropdown** · **buttons** | radio |
| **Choices** | code · label list | `1` Option 1, `2` Option 2 |
| **Add “None of the above”** | on/off; when on, the hint says what it stores ("stored as -77") | off |
| **Add “Other (please specify)”** | on/off; when on, the hint says what it stores and where the text goes ("stored as -66; the text goes to q1_other") | off |

**Coding.** One variable, nominal, with the choices as value labels. The answer
is the chosen code. Adding, removing or relabeling a choice updates that
code's value label; a label you wrote for another code in the Codebook tab
stays.

- **None of the above** adds an option "None of the above" after the choices,
  stored as the code `-77` and labeled `-77 = None of the above` in the
  codebook.
- **Other (please specify)** adds an option "Other" at the very end; choosing
  it opens a text box ("Please specify..."). The answer is the code `-66`,
  labeled `-66 = Other`, and the typed text goes to a column of its own,
  `<variable>_other`. With **Display = dropdown**, Other is the last entry of
  the list and its text box appears under the dropdown.

How these codes are chosen, and what happens when a choice already uses one,
is in [Codes for Other, None of the above and N/A](#codes-for-other-none-of-the-above-and-na).

**Rules.** At least one choice; unique codes; non-empty labels. With Other on,
the text column `<variable>_other` must not be a name a question already
stores an answer under. The Builder says so before you save, under **Add
“Other (please specify)”** ("q9 already stores an answer under q1_other, and
the engine refuses that — rename this question's variable or q9's.") and in
**Validation → Structure** ("q1: stores its “Other (please specify)” text
under "q1_other", which q9 already stores an answer under, and the engine
refuses that — rename this question's variable or q9's"). Saved anyway, the
Save is marked `errors`: "Question 'q1' stores its “Other (please specify)”
text under 'q1_other', which question 'q9' already stores an answer under."
Renaming this question's variable gives its Other text a column of its own
under the new name and leaves `q1_other` with the question that stores it.

---

## Multiple choice

Any number of answers.

**The respondent sees** checkboxes. Picking an **exclusive** option clears the
others, and picking any other option clears an exclusive one — in both data
layouts. With **Max answers** set, further boxes are disabled once the limit
is reached and a counter shows "2 of 3 selected" / "Maximum reached".

**Inspector → Options**

| Option | Values | Default |
|---|---|---|
| **Choices** | code · label list | `1`–`3` Option 1–3 |
| **Min answers** | a whole number, 0 or more | empty |
| **Max answers** | a whole number; "empty = no limit" | empty |
| **Exclusive choices** | a chip per choice; "picking one clears the rest" | none |
| **Data layout** | **array** · **wide** ("array: one column of codes · wide: one 0/1 variable per choice") | array |
| **Add “Other (please specify)”** | on/off; when on, the hint says what it stores and where the text goes ("stored as -66; the text goes to q7_other") | off |

**Min answers** (2 or more) is checked when the respondent clicks **Next**:
someone who picked some options but too few sees "Select at least 1 more"
under the question, and **Next** does not move on until they pick enough. An
exclusive answer ("None of these") is a complete answer on its own — it
satisfies the minimum, and the hint disappears once it is picked. **Min
answers** does not make the question required: an optional question can
still be left empty, and a required one asks for an answer first ("This
question requires an answer."). Under the options, the counter hint "Select at
least N more" appears once the question is answered, or at once when it is
required; it also shows without **Max answers**. A **Min answers** of `1` is
not checked on **Next** — to require an answer, turn on **Required**.

**Coding — array layout** (the default). One variable, nominal, with the
choices as value labels. The answer is the list of chosen codes. In CSV,
Excel, SPSS and Stata exports it is written as codes separated by semicolons
(`1;3`); Parquet keeps a list. Frequency tables of such a question use
**respondents** as the base, so the shares add up to more than 100 %. In
conditions, use **chose** / **did not choose** — `=` compares the whole list.
A quota on the variable counts a completed response in the cell of every
value it chose. With **Other (please specify)**, the list holds Other's code (`-66`)
beside the others and the typed text goes to `<variable>_other`.

**Coding — wide layout.** Clicking **wide** replaces the question's one
variable with one variable per choice, named after the old variable and the
choice's code (`q7` becomes `q7_1`, `q7_2`, `q7_3`; `_2` is added to a name
that is taken). Each is nominal, coded `0` No / `1` Yes, and takes the choice's
label as its variable label. Studio keeps them in step with the choices: a new
choice gets a new variable, a removed choice's variable leaves the codebook,
and relabeling a choice relabels its variable. Clicking **array** collapses
them back into one variable (`q7`) with the choices as value labels. A wide
question that came from a template or an import without a list of choices
keeps its variables as they are while you edit it; switching it to **array**
replaces them with a single variable and leaves the question without choices
until you add some.

In the data, each per-choice variable holds:

| Value | Meaning |
|---|---|
| `1` | chosen |
| `0` | offered and not chosen (the respondent answered the question) |
| empty | the question was not answered, or this option was hidden from the respondent by its own **Show if** / **Hide if** |

Whether an option left unchosen is `0` or empty is decided again after
every answer, whatever gives it — a click, a rating-scale digit key, a
script, a resumed interview. An answer given later, on the same page say,
that offers the option makes it `0`, and one that hides it clears it. An
option whose condition reads another wide question's variable (**Show if**
`aware_globex = 0`) follows that variable as it is now: when the other
question's option is hidden in turn and cleared, this one is cleared too.

Conditions, piping and quotas on a per-choice variable (`q7_1 = 1`) see the
answer, and **Exclusive choices** work. With **Other (please specify)**, Other
has no 0/1 variable of its own: the typed text goes to `<Id>_other`, named
after the question's **Id** (`q7_other`), which holds the text while Other is
chosen. When a question already stores an answer under that name, or one of
this question's own options does, the Builder flags it under **Add “Other
(please specify)”** and in **Validation → Structure** — ending "…rename q9's
variable" (or "…rename that option's variable") — and a Save that keeps it
is marked `errors`. When an analysis of an **array** question needs one 0/1
column per option (weighting, regression, TURF), you can also add an
**Explode multiple choice** node in the flow — see
[[Node Reference|Studio-Node-Reference]].

**Rules.** Min answers 0 or more; Max answers at least Min answers
("max_answers must be >= min_answers"); in the wide layout, Max answers no
more than the number of per-choice variables ("max_answers cannot exceed
number of wide-mode variables"); exclusive codes should be among the choices
(otherwise the warning `EXCLUSIVE_CODE_UNKNOWN`, array layout only).

---

## Likert scale

A numbered scale with anchored ends — agreement, satisfaction, likelihood.

**The respondent sees** a row of numbered buttons (or stars that light up to
the one chosen), the end labels under the scale and, if offered, a **Not
applicable** choice. Outside a text field, a digit key `1`–`9` picks that
point on the page's first scale that has it, exactly as a click does (the
answer is saved and the question's error message goes). On a scale that
starts at 0 the key is the point's number, and a digit the scale does not
have (`5` on a `0`–`4` scale) does nothing.

**Inspector → Answer**

| Option | Values | Default |
|---|---|---|
| **Points** | 2–11 | 5 |
| **Left label** / **Right label** | text | Strongly disagree / Strongly agree |
| **Offer “N/A”** | on/off; when on, the hint says what N/A stores ("stored as -1, a missing code") | off |
| **Display** | **Numbers** · **Stars** | Numbers |
| **First point** | **1** · **0** ("0-based: an NPS scale is 0–10 (11 points)") | 1 |

**Coding.** One variable, ordinal. The answer is the point's number (`1`–`5`,
or `0`–`10` with First point 0). Value labels are generated as `1 — Strongly
disagree`, `2`, `3`, `4`, `5 — Strongly agree`. A label you write in the
Codebook tab for a point — `3 = Neither agree nor disagree` — stays when you
edit the question, until an edit changes that point's own label (a new
**Right label** relabels the top point, and only it).

**Not applicable** is stored as a declared missing code: turning on **Offer
“N/A”** adds `-1 = Not applicable` to the variable's value labels and declares
`-1` as its not-applicable missing code, so means and percentages leave it
out. If the codebook declares no not-applicable code — a question set up
before this was automatic and not edited since, or an import — N/A is stored
as the text `na` instead (hint: "stored as the text “na” — the codebook
declares no not-applicable code") and the Save shows the warning
`NA_STORED_AS_TEXT`. See
[Codes for Other, None of the above and N/A](#codes-for-other-none-of-the-above-and-na).

**Rules.** The variable should be ordinal (otherwise the error-level lint
`INCOMPATIBLE_QUESTION_SCALE`); when the number of value labels differs from
the number of points you get `LIKERT_POINTS_LABEL_MISMATCH`.

---

## Number

A number: age, hours, income, a count. Menu label **Number**.

**The respondent sees** a number box with the unit beside it, or a slider with
the current value above it. The slider's range is the variable's valid range
(0–10 when none is set); its handle starts in the middle, and nothing is
recorded until the respondent moves it.

**Inspector → Answer**

| Option | Values | Default |
|---|---|---|
| **Display** | **input** · **slider** | input |
| **Unit** | text shown next to the field (placeholder `years`) | none |
| **Step** | a number greater than 0 | empty (1) |

**Inspector → Variable → Min / Max** (shown when the scale is ratio or
interval) set the valid range, which becomes the input's limits and the
slider's range.

**Coding.** One variable, ratio, stored as a number.

**The range is enforced.** A typed number below **Min** or above **Max** shows
"Minimum value is 18" or "Maximum value is 99" under the question as soon as
the respondent leaves the field, and again on **Next**, which does not move on
until the number is corrected. The slider cannot leave the range. An empty
optional field is not checked. Both messages can be reworded in **Theme →
Wording** ("Number below its minimum", "Number above its maximum").

**Rules.** Step greater than 0; Min not greater than Max; the variable must be
interval or ratio (otherwise `INCOMPATIBLE_QUESTION_SCALE`).

---

## Open text

Free text, and the typed inputs built on it.

**The respondent sees** a one-line box, or a four-line box for **Multi-line**.
With a format, the browser shows the matching input (an email keyboard, a
phone keypad, a date picker, a time picker). With **Max characters**, a counter
("12 / 400") appears, and "N characters remaining" once 80 % is used.

**Inspector → Answer**

| Option | Values | Default |
|---|---|---|
| **Format** | **Free text** · **Email** · **Phone** · **Web address** · **Date** · **Time** | Free text |
| **Multi-line** | on/off — available only with Free text | off |
| **Max characters** | 1 or more | none |
| **Placeholder** | text shown in the empty box | none |

**What the respondent must type** (checked on **Next**):

| Format | Accepted | Message |
|---|---|---|
| **Email** | `name@domain.xx` | "Please enter a valid email address." |
| **Phone** | an optional `+`, a digit, then at least five more digits, spaces, dots, dashes or brackets | "Please enter a valid phone number." |
| **Web address** | starts with `http://` or `https://` | "Please enter a valid web address (https://…)." |
| **Date** | `YYYY-MM-DD` (what the date picker produces) | "Please enter a valid date." |
| **Time** | `HH:MM` or `HH:MM:SS` | "Please enter a valid time." |

**Coding.** One variable, nominal, stored as text.

**Rules.** Multi-line cannot be combined with a format ("a multiline answer
cannot have a format"); Max characters at least 1.

---

## Matrix

A grid: statements down the side, one shared scale across the top.

**The respondent sees** a table with one row per statement and one column per
scale point (plus an N/A column if offered).

**Keyboard.** One cell of the grid is in the tab order. `←` / `→` move along
the row and answer it with the cell they reach, the N/A column included;
`↑` / `↓` move to the same column in the row above or below without
answering; `Space` or `Enter` chooses the focused cell; `Tab` leaves the
grid. A required matrix can therefore be finished without a mouse. The cell
in focus shows the focus ring, a chosen one included.

**Inspector → Options**

| Option | Values | Default |
|---|---|---|
| **Rows (statements)** | a list; "one variable per row"; **+ Row**. Hover a row's number to see the variable it writes | Statement 1, Statement 2 |
| **Columns (scale)** | a list; **+ Column** | Strongly disagree, Disagree, Neutral, Agree, Strongly agree |
| **Offer “N/A”** | on/off; when on, the hint says what N/A stores ("stored as -1, a missing code") | off |

**Coding.** One ordinal variable **per row**, named `<base>_1`, `<base>_2`, …
(for a question `q4`: `q4_1`, `q4_2`). Each row is its own column in the data,
which is what scale construction and reliability analysis want. Every row
variable gets the columns as value labels — coded `1` to *n* from left to
right in a matrix you build — and the answer stored for a row is the **code**
of the chosen column. A matrix inserted or imported with other codes keeps
them: the question bank's *Trust in institutions*, headed `0` … `10`, stores
`0`–`10`; a Qualtrics matrix stores its recodes.

- **Rows.** Each row keeps its own variable. **+ Row** adds a row with a new
  variable (`q4_3`), which takes the first row's value labels, declared
  missing codes (a Refused, a Don't know) and valid range — on a matrix
  without column headers too — so it stores, labels and leaves out as missing
  the same codes as the other rows; removing a row removes its variable and
  its codebook entry, and the other rows keep theirs (and their data
  columns). A row variable's label follows its statement, as "<question
  text> — <statement>".
  Rename a row's variable in the **Variable** section, which has a name field
  for each row ("Matrix rows write one variable each, in the order of Options
  → Rows; rename a row's variable here."). A matrix whose rows came from its
  variables' labels (an import, the example study) lists those labels under
  **Rows**; editing, adding or removing a row turns them into statements.
- **Columns.** A column's code follows its header. Renaming a column changes
  only its label: the code it stores stays, also while you type the new text
  letter by letter (on the way from "Strongly agree" to "Agree strongly" the
  header passes through "Agree" without taking that column's code). Moving or
  removing a column leaves the codes of the others as they are — remove `5`
  from a `0` … `10` scale and `6` … `10` still store `6` … `10`. One rename
  changes the code: a header renamed to the label of a declared missing code
  that no column stores (a "Don't know" beside a declared `-8` Don't know)
  takes that code.
- **New columns.** A column added with **+ Column** takes its code from the
  text you type into it: the code of the codebook label with exactly that
  text, if no column stores it yet (a "Refused" column beside a declared
  missing `9` Refused stores `9`, and stays a missing code; "Refusal" and
  "Don't know" beside ESS-style `77` / `88` store those); otherwise the next
  scale code of the codebook after the ones the columns store, so headers
  typed one by one onto a matrix that had none keep the codes its columns
  showed; otherwise the next code up that nothing uses.
- **A missing code without a column.** When you remove or retype the column
  of a declared missing code (`77 = Refusal`), the code keeps its value label
  and its missing declaration in the codebook, so answers already stored with
  it stay labeled and missing.
- **Not applicable** is an extra column at the end. It stores the row's
  declared not-applicable code: turning on **Offer “N/A”** labels `-1 = Not
  applicable` and declares it missing on every row variable. A matrix without
  column headers (possible from an import or the **Source** tab) keeps storing
  the text `na` when declaring a code would change which code its columns
  store; the Save then shows `NA_STORED_AS_TEXT`.
- **Required** on a matrix asks for an answer in **every row**; a row answered
  N/A counts. The Inspector says so beside the checkbox: "an answer in every
  row", or "an answer in every row — N/A counts" when **Offer “N/A”** is on.
  A matrix has no conditions on its rows, so every row is one the respondent
  sees. On **Next**:
  - a required matrix with no row answered shows "This question requires an
    answer.", as any required question does;
  - one answered in some rows but not all shows "Please answer every row."
    (**Theme → Wording → Required matrix: rows left**, where `{n}` is the
    number of rows left);
  - in both cases **Next** waits, and the rows still without an answer are
    marked: the statement turns the error color with a bar on its left, and
    the row's cells get error-colored outlines. Each mark goes when its row is
    answered; the message goes with the next answer, as any question's does.

  Leaving the matrix with no row answered shows "This question requires an
  answer." at once; rows left empty wait for **Next**, since the respondent
  is still working down the grid. A row a script cleared (set to empty) is
  unanswered. In the Walkthrough, a matrix counts toward "A/V answered" only
  once every row is answered.
- **Skip to** on a matrix fires as soon as **any** row is answered — on an
  optional matrix, one row is enough; a required one is held by **Next** until
  every row is answered, and then skips.
- Conditions and piping later in the survey can use a row's variable
  (**Show if** `q4_1 ≥ 4`, `{label:q4_1}`).

**Which code a column stores.** The survey reads each column's code off the
first row variable's value labels and declared missing codes. The Builder
follows the same rules, and so does Studio when it reads an older response
that stored a column's position (for a matrix with headers). They matter most
for a matrix from an import or the **Source** tab, whose codebook was not
built with it. The rules are tried in turn:

1. Every header is the text of exactly one value label: each column stores
   that label's code.
2. The codebook declares missing codes (N/A, a refusal, a don't know): a
   header whose text is one of their labels stores that code, wherever the
   codebook lists it, and the other headers take the codes of the remaining
   labels in order, when there are as many of each. Codebooks that come from
   SPSS often list `-8` "Don't know" before `0` … `10`; a matrix headed "0"
   … "10", "Don't know" over such a codebook stores `0` … `10` and `-8`.
3. There are as many value labels as headers: the columns take the labels'
   codes in order (a 0–10 scale headed "0" … "10" over labels "No trust at
   all" … "Complete trust").
4. Otherwise the codebook gives nothing to go by, and the columns store `1`,
   `2`, `3` … from left to right.

A matrix without column headers shows the first row's value labels as its
columns, in code order; with **Offer “N/A”** on, the N/A code is left out of
them and has its column at the end. "In order" is the codebook's order; for
labels written as an object in the **Source** tab, see
[Value labels in the Source tab](Studio-Codebook-and-Variables#value-labels-in-the-source-tab).

**Rules.** The number of rows must equal the number of variables.

---

## Ranking

Put items in order.

**The respondent sees** the items under "Tap or drag to rank". Tapping an item
moves it into the ranked list with its position number; ranked items can be
dragged to reorder or removed with ✕; the rest stay under "Remaining options".

**Inspector → Options**

| Option | Values | Default |
|---|---|---|
| **Items to rank** | code · label list | `1`–`3` Option 1–3 |
| **Rank at most** | 1 or more; "empty = all" | empty |

**Coding.** One variable, ordinal, with the items as value labels. The answer
is the ordered list of codes, first = rank 1; text exports write it as codes
separated by semicolons.

**Rules.** At least one item; Rank at most 1 or more.

---

## Best–worst (MaxDiff)

Shows a few items at a time and asks which is best and which is worst.

**The respondent sees** all tasks on one page. Each task is a small table:
the **Best** column, the item, the **Worst** column. One item cannot be both
best and worst in the same task. The question counts as answered only when
every task has both picks. A pick is a button: clicked again, or pressed with
`Space` or `Enter` once the keyboard has moved to it, it is released. Pressing
`Enter` right after clicking a pick goes to the next page and keeps it (see
[Keyboard and touch](Studio-Respondent-Experience#answering)). A chosen
pick in keyboard focus shows the focus ring.

**Inspector → Options:** **Items** (default Item 1–6), **Items per task**
(default 4), **Tasks** (default 8), **Versions** (default 20), **Best is
called**, **Worst is called**.

**Coding.** Two variables per task plus one for the design version:
`<name>_t1_best`, `<name>_t1_worst`, …, `<name>_version` — 17 variables for 8
tasks. They cannot be renamed; lowering **Tasks** removes the variables (and
codebook entries) of the tasks that went. Later pages can test and pipe them
(`{label:q7_t1_best}`).

The design, the lints and the analysis are described in
[[MaxDiff and Conjoint|Studio-MaxDiff-and-Conjoint]].

---

## Conjoint (choice)

Shows whole products side by side and asks which one the respondent would
choose.

**The respondent sees** all tasks on one page. Each task shows "1 / 10", a
grid with the attributes as rows and one column per product, a button under
each product and, if configured, a "none of these" choice. Every task must be
answered.

**Inspector → Options:** **Attributes** (default Brand: Brand A, Brand B;
Price: Low, High), **Products per task** (default 3), **Tasks** (default 10),
**Versions** (default 20), **“None of these”** (empty = force a choice).

**Coding.** One variable per task — which product was chosen, `1` to *n* from
left to right, *n*+1 for "none" — plus one for the design version:
`<name>_t1` … `<name>_t10`, `<name>_version`. As for MaxDiff, lowering
**Tasks** removes the variables of the tasks that went, and later pages can
use the task variables in conditions and piping.

Details in [[MaxDiff and Conjoint|Studio-MaxDiff-and-Conjoint]].

---

## Codes for Other, None of the above and N/A

Three answers are added with a switch rather than typed as choices: **Add
“Other (please specify)”** (Single choice and Multiple choice), **Add “None of
the above”** (Single choice) and **Offer “N/A”** (Likert scale and Matrix).
Each is stored as a code of the question's variable, and Studio writes that
code into the codebook for you, so exports label it and the Save has nothing
to warn about. The hint beside the switch always says what is stored.

| Option | Stored as | Added to the codebook |
|---|---|---|
| Other (please specify) | `-66` in the question's column; the typed text in `<variable>_other` (wide layout: `<Id>_other`) | the value label `-66 = Other` (not in the wide layout, which has no code column for it), and a variable `<variable>_other` — nominal, text, labeled "<question text> — other (please specify)" — whose **Used by** is the question |
| None of the above | `-77` | the value label `-77 = None of the above` |
| Not applicable | `-1` | the value label `-1 = Not applicable` and the missing code `-1 Not applicable` of kind *not applicable* — on the variable, or on every row variable of a matrix |

- **When a code is taken.** If one of the question's choices already uses
  `-66` or `-77`, Studio uses the next free code down (`-67`, `-78`, …) and the
  hint says so ("stored as -67; the text goes to q1_other"). Adding a choice
  coded `-66` to a question that offers Other moves Other to `-67`; the new
  choice stays an ordinary option. N/A starts at `-1` and moves down the same
  way when the scale uses `-1`.
- **A choice as the Other option.** In the **Source** tab, `other_code` in the
  question's `metadata` can name the code of one of its choices: that choice
  becomes the Other option — it opens the text box, and no second "Other" is
  added. A Qualtrics import does this for a text-entry choice.
- **Options that come from the codebook.** A Single choice, or a Multiple
  choice in the array layout, from an import or the example study can have no
  **Choices** of its own: the survey then offers its variable's value labels.
  Switching Other or None of the above on for such a question first copies
  those labels into its **Choices** list (without the Other or None code
  itself), so the new option is added beside them and the Save stays valid.
- **Scales with a valid range** (an NPS 0–10, a CES 1–7): the Other and None
  codes are also declared as missing codes, so means and the range check leave
  them out.
- **Switching an option off** removes its value label (and, for Other, the
  `<variable>_other` entry) unless the code is declared missing. Switching
  **Offer “N/A”** off keeps the "Not applicable" label and the missing code,
  so answers already stored with it stay missing; delete them in the Codebook
  tab if you do not want them.
- **Wording.** Respondents see "Other", "Please specify...", "None of the
  above" and "Not applicable". Replace them in **Theme → Wording** (**“Other”
  option**, **“Other” text box**, **“None of the above” option**, **“N/A”
  option**) — see [[Theme and Branding|Studio-Theme-and-Branding]].
- **Questions set up before these codes were written for you.** A question
  that offered Other, None or N/A and has not been edited since has no labels
  for these codes. The Save then warns `ADDED_CODE_WITHOUT_LABEL` ("Question
  'q1' stores “Other (please specify)” as -66, which variable 'q1' has no
  value label for.") or `NA_STORED_AS_TEXT`, and its N/A is stored as the text
  `na`. Edit the question once in the Builder — switching the option off and
  on again is enough — and Studio adds the labels, the `<variable>_other`
  entry and the N/A missing code.

---

## Older surveys and responses

The survey runtime now stores several answers differently from earlier
versions of Studio. Two things follow.

**A survey published before the change keeps its old build** until you
[republish](Studio-Publishing-and-Environments#republishing) it: Save (a Save
with no changes will do), then **Republish #N** on the environment's card. Until
then its respondents get the old behavior: no Other entry in a dropdown, wide
Multiple choice variables and exclusive choices that do not work, **Min
answers** and a Number's range not checked on **Next**, conditions on matrix
rows and MaxDiff or conjoint tasks that never fire, a required Matrix that
lets the respondent on after one row, and no page Body above the questions.

**Responses already collected are read in today's layout** — in the Data tab,
every export, flows and the research bundle — so old and new responses sit in
the same columns:

| Stored by an earlier build | Read as |
|---|---|
| Other, which showed up as columns named `code` (`__other__`) and `text` for a Single choice, or `selected` and `otherText` for a Multiple choice | the question's Other code (`-66` unless the question names another) in the question's own column, and the text in `<variable>_other` (`<Id>_other` for a wide question) |
| None of the above: the text `__none__` | the None code (`-77` unless the question names another) |
| N/A: the text `na` | the variable's declared not-applicable code, once the codebook declares one; without one it stays `na` |
| Wide Multiple choice: one column named after the question's Id, listing the chosen options' variables | `1` in each chosen option's variable and `0` in the question's other variables |
| Matrix: the chosen column's position (`1` … *n*) | the column's code — a 0–10 scale that was stored as `1`–`11` reads `0`–`10` |

An export you make now can therefore differ from one you downloaded earlier
for the same responses (`0`–`10` where it said `1`–`11`, `-66` where it said
`__other__`). Two things cannot be recovered: an older wide answer cannot tell
an option hidden from the respondent from one they did not choose, so both
read `0`; and quota cells on a per-choice variable or a matrix row count only
responses collected by a survey built after the change.

---

## Presets

The **Presets** column of the **+ Question** menu. After insertion a preset is
an ordinary question of its type — change anything you like.

| Preset | Type | Configured as | Variable |
|---|---|---|---|
| **Yes / No** | Single choice | **buttons**; `1` Yes, `0` No | `yes_no_<n>` |
| **Rating (stars)** | Likert scale | 5 points, **Stars**, no end labels | `rating_<n>` |
| **NPS (0–10)** | Likert scale | 11 points, First point 0, "Not at all likely" / "Extremely likely", text "How likely are you to recommend us to a friend or colleague?" | `nps_<n>` |
| **CES (1–7)** | Likert scale | 7 points, First point 1, "Strongly disagree" / "Strongly agree", text "The company made it easy for me to handle my issue." | `ces_<n>` |
| **Attention check** | Single choice | text "To show you are reading carefully, please choose “Rarely”.", **Required**, `1` Never … `5` Always, marked as an attention check expecting `2` | `attention_<n>` |
| **Date** | Open text | Format **Date** | `date_<n>` |
| **Email** | Open text | Format **Email**, placeholder `name@example.com` | `email_<n>` |
| **Phone** | Open text | Format **Phone**, placeholder `+1 555 000 0000` | `phone_<n>` |

`<n>` is the question's number, and the question's Id is `q<n>`.

> **Note.** A preset's Id (`q5`) and variable (`nps_5`) differ on purpose. The
> answer is stored under the variable, `nps_5` — the column in your data and
> the name to use in conditions — so there is nothing to fix. Rename either
> one if you like; see
> [Question Id and variable name](Studio-Builder-Overview#question-id-and-variable-name).

The question bank's NPS, CSAT and CES blocks are **Single choice** questions
with an open follow-up, not Likert scales — see
[[Question Bank, Templates and Library|Studio-Question-Bank-and-Library]].

---

## Attention checks

An *instructed-response* item ("please choose Rarely") tells you who is reading.
It is available on Single choice, Likert scale, Number and Open text questions,
in the **Question** section:

1. Turn on **Attention check** ("scored in the flow, not in the survey").
2. Set **Expected answer** ("what a reading respondent gives") — a list of the
   question's codes, or a free field for open questions. Until it is set the
   Inspector warns "Until an answer is set, this question checks nothing."
3. Optionally turn on **Also end the survey for respondents who fail** (hint:
   "adds a screen-out branch", then "branches to *page*"). Studio adds an
   ordinary **Branch (next if)** rule to the question's page that sends anyone
   who answered something else to a Screen-out page. The rule is evaluated
   when the page is left, a respondent who skipped the question is not
   screened out, and a failing respondent's answers are still collected and
   counted as screened out. You can edit or delete the rule (or change its
   target page) in the page's **Logic** section like any other; turning the
   option off removes the rule and leaves the page.

   The Screen-out page the rule points at sits **after the last Final or
   Redirect page**, so that only the rule leads there: respondents who pass
   finish on the Final page and are recorded as completed.
   - If such a Screen-out page already exists (one without a **Show if** or
     **Hide if** of its own, after the Final page), the rule points at it.
   - Otherwise Studio adds one, named `disqualification` ("Thank you" / "You
     do not qualify for this study."), right after the last Final or Redirect
     page. A conditional Screen-out page elsewhere — such as the consent
     screen-out of the built-in templates — keeps its own job and is not used.
   - If no Final or Redirect page without a condition ends the survey, Studio
     first adds a **Final** page ("Thank you" / "Thank you for taking part.")
     after the last content page and any end pages right behind it.

   The explanation under the checkbox reads: "An ordinary page branch,
   editable in Logic: it is evaluated when this page is left, so they finish
   the page first, and their answers are still collected and counted as
   screened out. Its Screen-out page sits after the Final page, so only this
   branch leads there. Leave it off to keep everyone and decide in the
   analysis instead."

**Questionnaires saved with an older placement.** Earlier versions of Studio
put the Screen-out page in front of the Final page, or pointed the rule at an
existing conditional Screen-out page. The Inspector says what goes wrong,
under the checkbox — as it does, in any questionnaire, when a **Skip to** on
the same page keeps the rule from firing (the last row below) — and
**Validation → Structure** lists it as "*q7*: the screen-out branch for
failing this attention check does not work. …":

| Message | What happens | Fix |
|---|---|---|
| "Respondents who pass reach “*page*” too: it comes after this page with no Final page in between, and pages are shown in order." | everyone who passes is screened out as well | **Fix the branch** moves that Screen-out page, with its wording, right after the last Final or Redirect page (adding a Final page first if none ends the survey) and points the rule at it |
| "“*page*” has a show if or hide if of its own. Where it is hidden, a respondent who fails is sent on to the next page shown after it instead of being screened out." | failing respondents are not screened out | **Fix the branch** points the rule at a Screen-out page after the Final page, adding one if needed; the conditional page keeps its job |
| "Skip to on *question* is checked before branch rules, so for anyone who answers *question* this branch never fires." | the rule never fires for anyone who answers that question | no automatic fix: clear that question's **Skip to**, or move the check to another page |

Walk through a passing and a failing answer in **Preview** before you publish;
details in [Attention checks](Studio-Logic-and-Branching#attention-checks).

Without step 3 nobody is screened out during the interview: the check is
scored afterwards by the **Response quality** node, whose **Attention checks**
parameter is filled from these settings. See
[[Data Quality|Studio-Data-Quality]].

---

## Converting a type

The type dropdown at the top of the Inspector converts the question in place.

| Kept | Dropped |
|---|---|
| question text, hint, Id, Required, Show if, Hide if, Skip to, Randomize option order, the variable name, and the choices when both types have them (Single choice, Multiple choice, Ranking, MaxDiff) | tags, Media URL, the attention-check setting, Other and None of the above, display and all other type-specific settings |

Converting to or from MaxDiff or Conjoint replaces the question's variables with
a fresh set. Check the **Variable** section afterwards: the codebook entry
keeps its old scale (a Single choice turned into a Number is still *nominal*,
which the engine flags as `INCOMPATIBLE_QUESTION_SCALE`).

---

## What the engine refuses

These make the questionnaire **malformed**: Save is refused with "Save failed."
and the engine's reason, and the Preview cannot be built. Fix them before you
Save.

- an empty survey title, question text or question Id;
- an option with an empty label, or two options with the same code;
- **Multi-line** together with a text **Format**;
- **Step** of 0 or less; **Rank at most** of 0; **Max characters** of 0;
- **Max answers** smaller than **Min answers**, or — in the wide layout —
  larger than the number of per-choice variables;
- a valid range whose Min is greater than its Max;
- a redirect **Delay (s)** that is not a whole number;
- a missing code without a label (possible only in the **Source** tab — the
  Codebook tab always writes one; see
  [Missing codes](Studio-Codebook-and-Variables#missing-codes));
- a MaxDiff with fewer than three items; a conjoint with fewer than two
  attributes, an attribute with fewer than two levels, an attribute name that
  is not a plain identifier, or two attributes with the same name.

> **Tip.** The message names the field that is wrong and where it is, by page
> name and question Id — for example "questionnaire:
> pages/0/items/0/text: must not be empty (page 'page1', question 'q1')", or
> "…/choices: needs at least 3 entries (page 'page1', question 'q7')" for a
> MaxDiff with two items. `pages/0/items/2` counts from zero: page 1, item 3.
> Inside a block the place reads "(page 'page1', block 1, question 'q1')".

Other problems — a duplicate question Id, a question Id that is another
question's variable name, an Id that differs from its question's variable and
is a name the survey stores something else under (a Matrix row, another
question's Other text, an assigned arm; see
[Names an Id may not take](Studio-Builder-Overview#names-an-id-may-not-take)),
**Skip to** a page that no longer exists, a page
nobody can reach, an **Other** whose default code `-66` is already a choice's
code (possible only from the **Source** tab or an import), a "None of the
above" code that is one of the answers, an Other text column that another
question writes — do **not** stop the Save; the Save is marked `errors` and
cannot be published. The Validation tab lists them; see
[[Testing Your Survey|Studio-Testing-Your-Survey]].

---

## What is deliberately missing

- **Loop & merge** — not in the engine, so not in Studio.
- **Multi-language questionnaires** — one questionnaire is one language. To run
  a survey in a single other language, write the questions in that language
  and replace the runtime's phrases (buttons, the required-answer message, the
  resume prompt, "Other", "Please specify...", "None of the above", "Not
  applicable", the minimum and maximum messages, the text-format messages, …)
  under **Theme → Wording**, and the default thank-you text under **Theme →
  Respondent experience → Completion screen**
  ([[Theme and Branding|Studio-Theme-and-Branding]]). Labels that only
  screen readers announce — such as "Task 1" on a MaxDiff task, "Choice 1" on
  a conjoint task or "Loading survey" — stay in English.
- **Exotic widgets** — constant sum, side-by-side grids, drill-downs, file
  upload, signatures, heat maps. When you import a questionnaire that has them,
  they are listed as not imported.

If your design needs one of these, say so through **Profile → Support**.

## See also

- [[The Builder|Studio-Builder-Overview]]
- [[Codebook and Variables|Studio-Codebook-and-Variables]]
- [[MaxDiff and Conjoint|Studio-MaxDiff-and-Conjoint]]
- [[Logic and Branching|Studio-Logic-and-Branching]]
- [[Data Quality|Studio-Data-Quality]]

<!-- studio-nav -->
---

← [[The Builder|Studio-Builder-Overview]] · [Studio contents](Studio-Overview#all-pages) · [[Codebook and Variables|Studio-Codebook-and-Variables]] →
