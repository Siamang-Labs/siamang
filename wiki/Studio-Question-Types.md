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
| **Multiple choice** | picks any number of options | 1 | nominal |
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
| **Question text** | Question | Shown as plain text: Markdown and HTML are not rendered. Piping works: `{answer:variable}` inserts an earlier answer, `{label:variable}` its label. |
| **Hint** | Question | Smaller text under the question ("optional guidance shown below the question"); piping works here too. |
| **Required** | Question | The respondent cannot continue without answering: **Next** shows "This question requires an answer." Required questions show an asterisk to respondents. New questions start **optional**. |
| **Randomize option order** | Question | Shuffles the options per respondent. Single choice, Multiple choice and Ranking only. |
| **Attention check** | Question | Single choice, Likert scale, Number and Open text — see [Attention checks](#attention-checks). |
| **Variable** | Variable | The codebook entry the question writes — [[Codebook and Variables\|Studio-Codebook-and-Variables]]. |
| **Show if** / **Hide if** / **Skip to** | Logic | [[Logic and Branching\|Studio-Logic-and-Branching]]. |
| **Id** | Advanced | A stable reference used by logic and comments: letters, digits and `_` (other characters turn into `_`). Must be non-empty and unique. |
| **Tags** | Advanced | Free labels, comma-separated, for your own organization of the instrument. |
| **Media URL** | Advanced | An image, or a video if the link ends in `.mp4`/`.webm`, shown with the question. Use a stable public URL (a download link from **Files** expires after 5 minutes). |

To respondents, questions are numbered `Q01`, `Q02`, …

> **Important — Id and variable name.** For single-answer questions the data
> column is named after the question's **Id**, while conditions, piping and
> quotas look the answer up by **variable name**. Keep the two identical: new
> presets (Id `q5`, variable `nps_5`) and renamed variables are the usual
> cause of a mismatch. Fix it with **Advanced → Id**. Details:
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
and "No options found" when nothing matches.

**Inspector → Options**

| Option | Values | Default |
|---|---|---|
| **Display** | **radio** · **dropdown** · **buttons** | radio |
| **Choices** | code · label list | `1` Option 1, `2` Option 2 |
| **Add “None of the above”** | on/off | off |
| **Add “Other (please specify)”** | on/off | off |

**Coding.** One variable, nominal, with the choices as value labels (kept in
sync: editing the choices rewrites the labels). The answer is the chosen code.

- **None of the above** adds an option shown as "None of the above" whose
  stored value is the text `__none__`. It has no value label and no numeric
  code.
- **Other (please specify)** adds an option shown as "Other"; choosing it opens
  a text box ("Please specify...").

> **Current limitation.** With **Add “Other (please specify)”** on, a
> respondent who picks Other is stored in two columns named `code` (value
> `__other__`) and `text` (what they typed) instead of the question's own
> column. With **Display = dropdown**, Other is not offered at all. Until this
> changes, add an ordinary option such as `97` "Other" and a separate **Open
> text** question with **Show if** *your variable* `=` 97. Likewise, for a
> "None of the above" you want to analyze, add it as an ordinary option with a
> code (for example `99`) rather than using **Add “None of the above”**.

**Rules.** At least one choice; unique codes; non-empty labels.

---

## Multiple choice

Any number of answers.

**The respondent sees** checkboxes. Picking an **exclusive** option clears the
others, and picking any other option clears an exclusive one. With **Max
answers** set, further boxes are disabled once the limit is reached and a
counter shows "2 of 3 selected" / "Maximum reached".

**Inspector → Options**

| Option | Values | Default |
|---|---|---|
| **Choices** | code · label list | `1`–`3` Option 1–3 |
| **Min answers** | a whole number, 0 or more | empty |
| **Max answers** | a whole number; "empty = no limit" | empty |
| **Exclusive choices** | a chip per choice; "picking one clears the rest" | none |
| **Data layout** | **array** · **wide** ("array: one column of codes · wide: one 0/1 column per choice") | array |
| **Add “Other (please specify)”** | on/off | off |

**Coding.** One variable, nominal, with the choices as value labels. The
answer is the list of chosen codes. In CSV, Excel, SPSS and Stata exports it is
written as codes separated by semicolons (`1;3`); Parquet keeps a list.
Frequency tables of such a question use **respondents** as the base, so the
shares add up to more than 100 %. In conditions, use **chose** / **did not
choose** — `=` compares the whole list.

> **Current limitation.** Choosing **Data layout → wide** in the Builder makes
> the questionnaire invalid: Save is refused with "MultiChoice wide mode expects
> vars to be a non-empty list of Variables." Keep **array**. When an analysis
> needs one 0/1 column per option (weighting, regression, TURF), add an
> **Explode multiple choice** node in the flow — see
> [[Node Reference|Studio-Node-Reference]]. Questions that arrive in the wide
> layout from a template or an import keep it; leave their layout as it is.

> **Current limitation.** **Min answers** is not enforced when the respondent
> clicks **Next**; it only adds the hint "Select at least N more" under the
> options, and only when **Max answers** is also set. To require at least one
> answer, turn on **Required**.

> **Current limitation.** With **Add “Other (please specify)”** on, every
> respondent's answer to this question is stored in columns named `selected`
> (the codes) and `otherText` (the typed text) instead of the question's own
> column — and two such questions overwrite each other. Use an ordinary
> "Other" option plus a separate **Open text** question shown if it was
> chosen (**Show if** *variable* **chose** *code*).

**Rules.** Min answers 0 or more; Max answers at least Min answers
("max_answers must be >= min_answers"); exclusive codes should be among the
choices (otherwise the warning `EXCLUSIVE_CODE_UNKNOWN`).

---

## Likert scale

A numbered scale with anchored ends — agreement, satisfaction, likelihood.

**The respondent sees** a row of numbered buttons (or stars that light up to
the one chosen), the end labels under the scale and, if offered, a **Not
applicable** choice.

**Inspector → Answer**

| Option | Values | Default |
|---|---|---|
| **Points** | 2–11 | 5 |
| **Left label** / **Right label** | text | Strongly disagree / Strongly agree |
| **Offer “N/A”** | on/off | off |
| **Display** | **Numbers** · **Stars** | Numbers |
| **First point** | **1** · **0** ("0-based: an NPS scale is 0–10 (11 points)") | 1 |

**Coding.** One variable, ordinal. The answer is the point's number (`1`–`5`,
or `0`–`10` with First point 0). Value labels are generated as `1 — Strongly
disagree`, `2`, `3`, `4`, `5 — Strongly agree`, and are **regenerated every time
you edit the question** — label the middle points in the question's end labels
rather than in the Codebook, where your edits would be overwritten. **Not
applicable** is stored as the text `na`, which has no value label.

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

> **Current limitation.** Min and Max do not stop a respondent from typing an
> out-of-range number and clicking **Next** — only **Required** and the text
> formats are checked there. Screen impossible values in your flow (for
> example with a **Filter rows** node) or use the slider, which cannot leave
> the range.

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
scale point (plus an N/A column if offered). Arrow keys move across a row.

**Inspector → Options**

| Option | Values | Default |
|---|---|---|
| **Rows (statements)** | a list; "one variable per row"; **+ Row** | Statement 1, Statement 2 |
| **Columns (scale)** | a list; **+ Column** | Strongly disagree, Disagree, Neutral, Agree, Strongly agree |
| **Offer “N/A”** | on/off | off |

**Coding.** One ordinal variable **per row**, named `<base>_1`, `<base>_2`, …
(for a question `q4`: `q4_1`, `q4_2`). Every row variable gets the columns as
value labels, coded `1` to *n* from left to right. **Not applicable** is stored
as `na`. Each row is its own column in the data, which is what scale
construction and reliability analysis want.

- **Required** on a matrix is satisfied as soon as one row is answered.
- The row variables cannot be renamed in the Builder (only in the **Source**
  tab).
- Deleting a row in the middle moves the later statements onto the earlier
  variable names — do not do it once fieldwork has started.

> **Current limitation.** A matrix answer is always stored as the column's
> **position** (`1` for the first column), whatever codes the row variables'
> value labels use. That matches every matrix you build in the Builder, but a
> matrix inserted or imported with other codes — the question bank's *Trust in
> institutions* (0–10), or a Qualtrics matrix with recodes — stores `1`–`11`
> where its labels say `0`–`10`. Recode in your flow before reporting.

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
every task has both picks.

**Inspector → Options:** **Items** (default Item 1–6), **Items per task**
(default 4), **Tasks** (default 8), **Versions** (default 20), **Best is
called**, **Worst is called**.

**Coding.** Two variables per task plus one for the design version:
`<name>_t1_best`, `<name>_t1_worst`, …, `<name>_version` — 17 variables for 8
tasks. They cannot be renamed.

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
`<name>_t1` … `<name>_t10`, `<name>_version`.

Details in [[MaxDiff and Conjoint|Studio-MaxDiff-and-Conjoint]].

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

> **Important.** A preset's Id (`q5`) and variable (`nps_5`) differ. Set
> **Advanced → Id** to the variable name (`nps_5`) straight away — see the box
> in [Fields every question has](#fields-every-question-has).

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
3. Optionally turn on **Also end the survey for respondents who fail**. Studio
   adds an ordinary **Branch (next if)** rule to the question's page that sends
   anyone who answered something else to a Screen-out page (creating one if
   the questionnaire has none). The rule is evaluated when the page is left, a
   respondent who skipped the question is not screened out, and the response
   is still recorded as screened out. You can edit or delete the rule in the
   page's **Logic** section like any other. A Screen-out page created this way
   is added at the very end, so make sure a **Final** page comes before it —
   otherwise respondents who pass the check walk into it.

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
- a multiple choice question switched to **wide** in the Builder;
- **Multi-line** together with a text **Format**;
- **Step** of 0 or less; **Rank at most** of 0; **Max characters** of 0;
- **Max answers** smaller than **Min answers**;
- a valid range whose Min is greater than its Max;
- a redirect **Delay (s)** that is not a whole number;
- missing codes entered in the Codebook tab (see
  [[Codebook and Variables|Studio-Codebook-and-Variables]]);
- a MaxDiff with fewer than three items; a conjoint with fewer than two
  attributes, an attribute with fewer than two levels, an attribute name that
  is not a plain identifier, or two attributes with the same name.

> **Tip.** The engine's message names the place (`pages/0/items/2`, i.e. page
> 1, item 3). For an empty field it sometimes names a neighboring property
> instead — if the message does not make sense, look for an empty text, label
> or Id on that question.

Other problems — a duplicate question Id, **Skip to** a page that no longer
exists, a page nobody can reach — do **not** stop the Save; the Save is marked
`errors` and cannot be published. The Validation tab lists them; see
[[Testing Your Survey|Studio-Testing-Your-Survey]].

---

## What is deliberately missing

- **Loop & merge** — not in the engine, so not in Studio.
- **Multi-language questionnaires** — one questionnaire is one language. To run
  a survey in a single other language, write the questions in that language
  and replace the runtime's phrases (buttons, the required-answer message, the
  resume prompt, …) under **Theme → Wording**
  ([[Theme and Branding|Studio-Theme-and-Branding]]). A few built-in phrases —
  "Other", "Please specify...", "None of the above", "Not applicable", the
  text-format messages and the default thank-you text — are not in Wording yet.
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
