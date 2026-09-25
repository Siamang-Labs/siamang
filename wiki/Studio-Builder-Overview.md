# The Builder

The **Builder** tab is where the questionnaire is made. It edits the real
engine document, so anything you build here is something the engine can run,
validate and turn into Python. This page is a tour of the screen: the header,
the tabs, the Structure view, pages and blocks, the Inspector, previewing,
saving, drafts and the read-only states. The question types themselves are in
[[Question Types|Studio-Question-Types]].

---

## The screen

```
┌ [Survey title                ]  Version 17 · edited ▾        ↶ ↷  [More ▾] [Preview] [Save changes] ┐
├───────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Structure · Codebook · Logic map · Validation · Test · More ▾                                         │
├───────────────┬──────────────────────────────────────────────────────────┬──────────────────────────┤
│ PAGES         │ [Structure|Preview]  Page 3 of 5 ‹ Brands ›  [Library] ↑↓ │ INSPECTOR                │
│ [Find question…] [id] │ ▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬ (page meter)                     │ [Single choice ▾] q7 → q7 [x]│
│ 1 Before we start     │ Brands                                           │ ▸ Question               │
│ 2 Awareness           │ ┌ Single choice  q7 → q7   optional  show if ↑↓┐│ ▸ Options                │
│ 3 Brands   ⤳          │ │ Which brand did you use most?                ││ ▸ Variable     codebook  │
│   ● Which brand…      │ │ ○ Acme  ○ Globex  ○ Initech                  ││ ▸ Logic                  │
│   ○ Why?              │ └──────────────────────────────────────────────┘│ ▸ Advanced               │
│ 4 About you           │ ┌ Block: About you                         ↑↓ ┐│ ▸ Comments               │
│ 5 Thank you  final    │ │ …                        [+ Add to block]    ││                          │
│ [+ Page] [+ Question] │ └──────────────────────────────────────────────┘│                          │
└───────────────────────┴──────────────────────────────────────────────────┴──────────────────────────┘
```

Three columns: the **pages rail** on the left, the **canvas** in the middle and
the **Inspector** on the right. The Inspector shows whatever you selected.

---

## The header

**Title** — the survey title, editable in place. It cannot be empty: a Save of
a questionnaire with an empty title is refused.

**Version chip** — reads **Version 17** (or **No saved version** before the
first Save), followed by **· edited** when you have unsaved edits (**· being
edited** while you follow a colleague). Hover, focus or tap it for a popover
with the size of what is on the screen — **pages**, **questions**,
**variables** and, if there are any, **quotas** — and the state of your draft.

**↶ ↷** — **Undo** and **Redo** (`Ctrl/Cmd + Z`, `Shift + Ctrl/Cmd + Z` or
`Ctrl/Cmd + Y`). See [Undo and redo](#undo-and-redo).

**More ▾** — the occasional actions:

| Item | What it does |
|---|---|
| **Import** | replaces the working document with a questionnaire from a file or pasted JSON — [[Importing Questionnaires\|Studio-Importing-Questionnaires]] |
| **Export Python** | downloads the `questionnaire.py` generated for the **current Save** — [Export Python](#export-python) |
| **Discard changes** | drops all unsaved edits and returns to the last Save (no confirmation; disabled when there is nothing to discard) |

**Preview** — builds a standalone preview of the current Save and opens it in a
new tab. See [The Preview button](#the-preview-button).

**Save** / **Save changes** — opens the Save dialog (`Ctrl/Cmd + S`). The label
reads **Save changes** when you have unsaved edits. See [Saving](#saving).

---

## The Builder tabs

Five tabs are always in the strip; five more are under **More ▾**, because they
are set up once per study rather than used every minute. On a narrow window
more tabs move into **More ▾**; the tab you are on always stays visible. The
**Structure** tab carries an **edited** marker while you have unsaved edits.

| Tab | What it is for | Details |
|---|---|---|
| **Structure** | building: pages, blocks, questions and the Inspector | this page |
| **Codebook** | every variable in one table | [[Codebook and Variables\|Studio-Codebook-and-Variables]] |
| **Logic map** | the routing between pages and the conditions on questions | [[Logic and Branching\|Studio-Logic-and-Branching]] |
| **Validation** | structure checks, the engine's check without saving, the last Save's issues, the AI review | [[Testing Your Survey\|Studio-Testing-Your-Survey]] |
| **Test** | walkthrough, simulated data, a public preview link | [[Testing Your Survey\|Studio-Testing-Your-Survey]] |
| **More ▾ → Quotas** | quota cells | [[Quotas and Randomization\|Studio-Quotas-and-Randomization]] |
| **More ▾ → Randomization** | every shuffle in one place | [[Quotas and Randomization\|Studio-Quotas-and-Randomization]] |
| **More ▾ → Scripts** | the behavior library and custom JavaScript | [[Scripts\|Studio-Scripts]] |
| **More ▾ → Theme** | colors, fonts, logo, progress, wording | [[Theme and Branding\|Studio-Theme-and-Branding]] |
| **More ▾ → Source** | the questionnaire as JSON | [The Source tab](#the-source-tab) |

---

## Question Id and variable name

Every question has two names, shown together as `id → variable` in its card
header and in the Inspector header:

- The **Id** (**Advanced → Id**, hint "names the question in scripts and
  comments; logic and data use the variable") is the question's own handle.
  Scripts on the **Scripts** tab target a question by its Id, comments are
  attached to it, checks and validation messages quote it, the Codebook's
  **Used by** column lists it, and the MaxDiff and Conjoint analysis nodes
  pick their question by it.
- The **variable** (the **Variable** section) is the answer. A single-answer
  question — Single choice, Likert scale, Number, Open text, Ranking, and
  Multiple choice in the array layout — stores its answer under its
  **variable name**: that is the column in the **Data** tab and in every
  export, and the name conditions, piping, quotas and attention-check scoring
  read. Matrix, MaxDiff, Conjoint and wide-layout Multiple choice questions
  write several variables, and each becomes its own column in your data (see
  [Multiple choice](Studio-Question-Types#multiple-choice) for the wide
  layout). A question offering **Other (please specify)** also writes the
  typed text to a column of its own, `<variable>_other`.

The two names may differ. **Presets** differ by design (Id `q5`, variable
`nps_5`), and so does a question whose variable you rename in the Variable
card; logic, piping and quotas on the variable work either way. What still
matters:

- **An Id must be unique and must not be another question's variable name.**
  The survey could not tell which of the two questions is meant. The Builder
  keeps you out of this: a new question's Id is never a name the
  questionnaire already uses (as an Id, a variable, a codebook entry or one
  of the names in [Names an Id may not take](#names-an-id-may-not-take)),
  and a variable you rename never takes another question's Id (a clash gets
  `_2`). If you type such an Id yourself, the **Id** field says so at once —
  "Another question already has this id." or "This is the variable q1 stores
  its answer under — the engine refuses an id that is another question’s
  variable." — and **Validation → Structure** lists it ("q2: the id is the
  variable q1 stores its answer under, and the engine refuses that — rename
  the id (Advanced → Id)"). Saved anyway, the Save is marked `errors`:
  "Question 'q2' has the id under which question 'q1' stores its answer; an
  id may not be another question's variable or output name." Rename one of
  the two.
- **An Id that differs from its variable must not be a name the survey
  stores something else under** — another question's Other text, a Matrix
  row, the arm an **Assign to a condition** draws, and a few more; see
  [Names an Id may not take](#names-an-id-may-not-take).
- **Renaming a variable renames it everywhere the questionnaire uses it** —
  conditions, branch rules, quotas, piping and scripts — and its codebook
  entry moves with it; see
  [Renaming a variable](Studio-Codebook-and-Variables#renaming-a-variable).
- **In custom JavaScript, answers are keyed by variable name**:
  `answers["nps_5"]`, and `answers.__errors__["nps_5"]` for a validation
  message. When Studio builds the survey it translates accesses written with
  the Id (`answers["q5"]`, `answers.q5`); Validation warns with
  `SCRIPT_STALE_QUESTION_ID` about other mentions of the Id it cannot
  translate. See [[Scripts|Studio-Scripts]].

> **Note — answers collected before this change.** Earlier versions of Studio
> stored a single-answer question's answer under its **Id**, so logic, piping
> and quotas on a question whose Id differed from its variable never matched,
> and its data column carried the Id. Studio has moved the answers already
> collected that way to the variable's name and recounted the quota cells
> involved; where a move could have mixed two questions' answers, the old
> column was left as it was. The move also covers a question whose variable
> was renamed after a Save (an earlier Builder gave every new question its Id
> as its variable) and one whose Id is a Matrix row or a per-choice variable
> of another question; only a response that shows nothing of the older build
> (some partial or resumed interviews) keeps such an answer under the Id. A
> survey published before the change keeps its old build: its answers are
> filed under the variable name as they arrive, but its show-if conditions,
> branching and piping on such questions only work once you publish it
> again.
>
> Filing an older build's answers never moves a value that is not a
> question's answer into a question's column: the text typed into an Other,
> the arm an **Assign to a condition** drew and the survey's own `__` names
> stay where the survey sent them, even when a question's Id has the same
> name. A survey published with the current Studio says that its answers are
> keyed by variable name, and Studio stores them exactly as sent — nothing in
> them is ever re-keyed. Republishing an older survey therefore also ends the
> filing for it. One case stays ambiguous: where a Save made before the rule
> in [Names an Id may not take](#names-an-id-may-not-take) gave a question
> the Id of another question's Other text (`brand_other`), that question's
> answers from an older build's partial or resumed interviews stay under the
> Id and read as `brand`'s Other text.

### Names an Id may not take

A question's Id may never be another question's Id or another question's
variable name (see above). An Id that differs from the question's variable
also may not start with `__`: those are the survey runtime's own names. For
such an Id the **Id** field says "Ids starting with “__” are the survey
runtime’s own names." and **Validation → Structure** lists "__score: ids
starting with "__" are the survey runtime's own names — rename the id
(Advanced → Id)". An Id that is the question's own variable (Id and
variable both `__x`) is not flagged for this; a **variable** that starts
with `__` is, because the survey never submits it and its answers never
reach the data: **Validation → Structure** lists "__x: the variable "__x"
starts with "__" — the survey runtime never submits it; rename the
variable", and the question's **Variable** section says "Variables starting
with “__” are the survey runtime’s own: it never submits __x, so these
answers never reach the data. Rename the variable." A new Id alone does not
help; rename the variable.

When the Id **differs from the question's own variable** — a preset's `q5` /
`nps_5`, or a question whose variable you renamed — it may not be any other
name the survey stores something under either. When Studio builds the survey
it translates `answers["q5"]` in custom JavaScript to the question's variable,
so a script that meant the other thing would reach the question's answer
instead. The engine refuses such an Id; the Builder says so before you Save:

| The Id is… | For example | The **Id** field says | **Validation → Structure** says |
|---|---|---|---|
| a variable another question stores an answer under: a Matrix row, a per-choice variable of a wide Multiple choice, a MaxDiff or Conjoint variable | Id `trust_1` on a question with variable `note`, while the matrix `trust` writes `trust_1` | "This is a variable trust stores an answer under — the engine refuses an id that is another question’s variable." | "trust_1: the id is a variable trust stores an answer under, and the engine refuses that — rename the id (Advanced → Id)" |
| one of the question's own variables (a matrix given a separate name, from an import or the **Source** tab, whose Id is one of its rows) | | "This is one of the variables this question stores its answers under — the engine refuses it as the id." | `<id>: the id is one of the variables this question stores its answers under, and the engine refuses that — rename the id (Advanced → Id)` |
| where a question stores the text typed into its **Other (please specify)**: `<variable>_other` (for a wide Multiple choice, `<Id>_other`) | Id `brand_other` on a question with variable `note`, while `brand` offers Other | "This is where brand stores the text typed into Other — scripts naming it would reach this question’s variable instead." ("…where this question stores…" for its own Other) | "brand_other: the id is where brand stores the text typed into Other — scripts naming it would reach note instead; rename the id (Advanced → Id)" |
| the variable an **Assign to a condition** script stores the arm in | Id `condition` on a question with variable `cond_q` | "This is the variable an Assign to a condition script stores the arm in — scripts naming it would reach this question’s variable instead." | "condition: the id is the variable an Assign to a condition script stores the arm in — scripts naming it would reach cond_q instead; rename the id (Advanced → Id)" |
| a codebook variable that no question collects and a custom script writes (see [What counts as a script writing a name](#what-counts-as-a-script-writing-a-name)) | Id `panel` on a question with variable `panel_q` | "This is a codebook variable a custom script writes — scripts naming it would reach this question’s variable instead. If the codebook entry is left over from renaming this question’s variable, delete it in the Codebook tab instead of renaming the id." | "panel: the id is a codebook variable a custom script writes — scripts naming it would reach panel_q instead; rename the id (Advanced → Id), or, if the codebook entry "panel" is left over from renaming this question's variable, delete that entry in the Codebook tab so the script's "panel" means this question" |

Saved anyway, such a Save is marked `errors` and cannot be published — as
is one with an Id that starts with `__` and differs from its variable. The
engine's reason names the clash, for example: "Question 'brand_other' stores
its answer under 'note', but 'brand_other' is also the key question 'brand'
stores its “Other (please specify)” text under. A script that names
'brand_other' could mean either; give the question another id." Rename the
Id. For a codebook variable a custom script writes, the engine names a
second way out: "…A script that names 'q2' could mean either; give the
question another id, or, if the codebook entry 'q2' is left over from
renaming this question's variable, delete that entry so that 'q2' in the
script means the question." (see below).

Two names that look similar are allowed:

- **A codebook entry that no question collects and nothing writes.** An
  earlier version of the Builder left the old codebook entry behind when you
  renamed a question's variable, under a name that is often the question's
  Id (`q2` renamed to `comment` kept `q2`). The Id is fine; the entry is
  simply unused. **Validation → Structure** suggests removing it — "q2: the
  codebook still declares a variable "q2" that no question collects and
  nothing writes — delete it in the Codebook tab" — and the Codebook tab
  lists it **unused** with **Delete**. The **Id** field says nothing.
- **A name a custom script writes that the codebook does not declare.** A
  script that writes the question's own Id (`answers.q5 = 7`, to prefill it)
  writes the question's answer: Studio translates it to `answers.nps_5`.
  Renaming the Id would leave the script writing a name nothing reads.

The two can meet in a questionnaire from that earlier Builder: the leftover
entry `q2` next to a script of its time that prefills the question by its Id
(`if (!answers.q2) answers.q2 = "(no comment)";`). The Id is then flagged
as a codebook variable a custom script writes. Do not rename the Id — the
script would go on writing `q2`, and the prefill would no longer reach the
question. Delete the leftover entry in the Codebook tab instead: the script's
`q2` then means the question again, and Studio translates it to `comment`.

### What counts as a script writing a name

For these checks a custom script writes a name when, outside its comments,
strings and regular expressions, it assigns it (`answers.panel = 1`, `+=`,
`??=` and the like), increments or decrements it (`answers.panel++`),
deletes it (`delete answers.panel`), uses it as the target of a
`for (… of …)` or `for (… in …)` loop or as a place in a destructuring
assignment (`[answers.panel, x] = …`, `({ v: answers.panel } = o)`), or
changes the value under it in place: a property or element assigned
(`answers.panel.source = "web"`, `answers.panel[0] = 1`), an array method
that changes it (`answers.panel.push(…)`, `.splice`, `.sort` …),
`Object.assign(answers.panel, …)`, `Object.defineProperty(answers.panel, …)`
or `Reflect.set(answers.panel, …)`. A value in brackets counts when the
brackets' value is changed: `(answers.panel || []).push(x)`,
`(0, answers.panel).push(x)`, `(c ? y : answers.panel).k = 1`. A write
counts wherever it stands — after `if (…)`, `else`, `do` or `return`
(`if (c) [answers.panel, x] = …`), and after a regular expression that holds
a quote or ends in `\/\/` (`s.replace(/["']/g, "")`, `/^https?:\/\//`).
`answers?.panel` counts like `answers.panel`. Everything else is a read: a
comparison, a condition, a value passed to a function (`f(answers.panel)`),
put in an array or object, or used as a subscript
(`obj[answers.panel] = 1`), a change to a copy
(`answers.panel.slice().push(x)`,
`Object.assign(answers.panel.slice(), o)`), and a string or a regular
expression that happens to spell a write (`"answers.panel = 1"`,
`/answers.panel = 1/`). The Builder, the Save and the engine read scripts
the same way.

---

## The Structure view

### The pages rail

The left rail lists the pages in interview order: number, title (or name if
the page has no title) and, for special pages, a pill — **final**,
**screen-out** or **redirect**. A `⤳` marks a page with branch rules.

The **current page** unfolds to show its questions and blocks:

- a block shows a folder icon, its title and `⇄` when its questions are
  shuffled;
- a question shows a dot — filled for **required**, a ring for **optional** —
  its text (or **(no text)**) and a `?` when it has a show/hide condition.
  Hover to see `id → variables`.

At the top of the rail:

- **Find question…** — filters the current page's questions by text, id or
  variable name;
- **id** — shows question ids instead of their texts ("Show ids instead of
  text").

Click a page to select it (the Inspector shows its properties); click a
question or block to select it.

### Adding pages and questions

The bottom of the rail has two buttons.

**+ Page** opens a menu and inserts the new page **after the current page**:

| Menu item | Creates |
|---|---|
| **Content page** | an ordinary question page, titled "New page", named `page`, `page_2`, … |
| **Final page** | a thank-you page: "Thank you" / "Thank you for taking part." |
| **Screen-out page** | a screen-out: "Thank you" / "You do not qualify for this study." |
| **Redirect page** | a redirect to `https://example.com` (change it in the Inspector) |

**+ Question** opens a two-column menu — **Types** (the nine question types)
and **Presets** (eight ready-made configurations) — with **Block** at the
bottom of the Presets column. The new item goes **at the end of the current
page**, or at the end of the **selected block** when a block is selected. See
[[Question Types|Studio-Question-Types]] for what each one is.

New questions are called **New question**, are optional, and get an Id
numbered after the questions already there (`q7` for the seventh). If that
name is taken — as another question's Id, a variable or a codebook entry —
the number moves up until one is free (`q8`, `q9`, …). Their variable is named
after the Id (`q7`) — or, for a preset, after the preset (`nps_7`,
`yes_no_7`); the answer is stored under the variable — see
[Question Id and variable name](#question-id-and-variable-name).

### The canvas bar

Above the page:

- **Structure | Preview** — the editable cards, or the survey as the respondent
  sees it ([Structure and Preview](#structure-and-preview));
- the pager — **Page 3 of 5**, **‹** and **›** to move between pages, and the
  page's title in between (click it to select the page);
- **Library** — **Insert from library…**, **Save question to library…** /
  **Save block to library…** (disabled as **Save selection to library…** until
  you select a question or block: "Select a question or a block first") and
  **Save questionnaire as template…** — see
  [[Question Bank, Templates and Library|Studio-Question-Bank-and-Library]];
- **↑ ↓** — **Move page up** / **Move page down** in the interview order.

A thin meter under the bar shows where the page sits in the questionnaire.

### Question cards

Each question is a card with its type, `id → variables`, its text (or
*Question text…*), its hint and a layout sketch of the answers. The sketch is a
quick outline, not the real runtime — for that, switch to **Preview**.

Pills on a card:

| Pill | Meaning |
|---|---|
| **optional** | the question is not required (required questions carry no pill — they are the normal case) |
| **show if** / **hide if** | the question has a condition; hover to read it |
| comment count | open comments on this question |
| **→ page_name** | the question has **Skip to** set |
| **script** | a script on the **Scripts** tab targets this question |

A card for a choice question with no options says "No answer options yet. Add
choices in Options."

A **block** is drawn as a frame with its title, a **randomized** pill when its
questions are shuffled, a **show if**/**hide if** pill, its questions inside
and an **Add to block** menu at the bottom.

Each card and block has **Move up** / **Move down** buttons, which move it
within its own page or block.

### Empty states

| You see | Meaning |
|---|---|
| "This page has no questions yet." + **Add your first question** | a page with neither questions nor a Body — the engine's check reports it as `EMPTY_PAGE` until you add one or the other |
| "A text-only page — add a question to make it interactive." + **Add your first question** | a page that has a Body but no questions: respondents see its title and Body — see [Pages and page kinds](#pages-and-page-kinds) |
| "No pages yet." + **Page** | the questionnaire has no pages |
| **No questionnaire yet** — "This project has no survey/questionnaire.json. Create one — it starts like a blank project, with one placeholder question — or restore a Save that has one." | the project has no questionnaire document; **Create questionnaire** opens the Save dialog with the questionnaire a blank project starts with (one page, one placeholder question, your organization's house style — its custom CSS only from the Plus plan); **Draft from a brief** asks the [[AI Assistant\|Studio-AI-Assistant]] *(Plus)* |

---

## Pages and page kinds

A **page** is what the respondent sees at one time. The page Inspector's
**Kind** has four values:

| Kind (Inspector) | What the respondent sees | Body |
|---|---|---|
| **Content** | the page title, the Body, the questions, **Previous** and **Next** | shown **above the questions**; on a page without questions the Body is the page |
| **Final (thank you)** | the title and the Body (without them: the **Completion screen** Title and Message of **Theme**, by default "Thank you for participating" / "Thank you for your participation!"), plus the response ID and submission time; the interview is submitted as **completed** | shown |
| **Screen-out** | the title (without one: **Theme → Wording → Screen-out page title**, by default "Thank you") and the Body (without one: the completion Message); the interview is submitted as **screened out** | shown |
| **Redirect** | the title and the Body, "Redirecting you now. Continue if you are not redirected.", then the browser goes to the **Redirect URL** after **Delay (s)** seconds (5 if empty) | shown |

Give every Final and Screen-out page a **Title** and **Body** of your own, or
set the survey-wide defaults in **Theme** — **Respondent experience →
Completion screen** (**Title**, **Message**) and **Wording** (**Screen-out
page title** and the redirect texts). The built-in defaults are in English.
See [[Theme and Branding|Studio-Theme-and-Branding]].

Final, Screen-out and Redirect pages end the interview. Reaching one records
the response. They are usually gated with a **Show if** condition or reached
through a branch rule — see [[Logic and Branching|Studio-Logic-and-Branching]].

**Text-only pages.** A page with a **Body** and no questions is a *text-only*
page — an introduction, an information sheet, a debrief. Make one with **+ Page
→ Content page**: write the **Body** and add no questions. The Inspector shows
it as **Content**, the canvas says "A text-only page — add a question to make
it interactive.", and the respondent sees its title and Body with **Previous**
and **Next**. Templates and imported questionnaires often contain them.

Studio stores such a page as the engine's *content* page, and a page with
questions as an ordinary one, and it keeps this in step as you edit: add a
question to a text-only page and it becomes an ordinary page that shows the
Body above the question; remove the last question from a page that has a Body
and it is a text-only page again. You only notice this in the **Source** tab
and in History diffs, where `"kind": "content"` appears on or disappears from
such a page — also on the pages of an older questionnaire, the first time you
edit anything in it after this change.

> **Note — surveys published earlier.** Older survey builds showed the Body
> of a page with questions only on the canvas, not to respondents, and showed
> an imported *content* page that held questions without its questions. A
> survey published before this change keeps that behavior until you
> [republish](Studio-Publishing-and-Environments#republishing) it.

**Body text is HTML**, not Markdown: `<p>…</p>`, `<b>…</b>`, `<a href="…">…</a>`
and similar tags work; plain text works too, but line breaks collapse. Piping
(`{answer:variable}`, `{label:variable}`) fills in an earlier answer in the
title and the Body of every kind of page, Final, Screen-out and Redirect pages
included; `{label:variable}` shows the chosen option's label, not its code.

### Page properties

Select a page (click it in the rail, or its title in the pager) to edit it:

- header: **Page 3** and the page's name, and a delete button (**Delete
  page**; disabled when it is the only page);
- **Page** section:
  - **Title** — shown as the page heading;
  - **Name** ("used by logic (skip to, next if) and page scripts") — letters,
    digits and `_`; other characters turn into `_`. The new name takes effect
    when you leave the field or press `Enter`; `Esc` puts the current name
    back, and so does leaving the field empty. Renaming a page updates every
    branch rule, **Default next** and **Skip to** that points at it, and the
    target of a custom JavaScript script that runs on the page. Names must be
    unique: a name another page has shows "Another page already has this
    name." and is not applied;
  - **Kind** — **Content**, **Final (thank you)**, **Screen-out**,
    **Redirect**;
  - **Body** (all kinds except Redirect) — hint "HTML, shown above the
    questions (the whole page, on a page without any); {answer:variable} or
    {label:variable} pipes an earlier answer" on a Content page, "HTML, shown
    to the respondent; {answer:variable} or {label:variable} pipes an earlier
    answer" on an end page;
  - **Redirect URL** and **Delay (s)** — whole seconds, 0 or more (Redirect
    pages);
  - **Randomize block order** (Content pages) — shuffles the page's blocks per
    respondent;
- **Logic** section — **Show if**, **Hide if**, **Branch (next if)** ("first
  matching rule wins"; each rule is a condition → target page) and **Default
  next** ("when no rule matches"; **— following page —** by default).
  **+ Rule** opens a draft rule with the condition editor already open (on the
  page's last question, when the page has one), the note "Pick what the rule
  tests — it is added once the condition is complete." and the buttons **Add
  rule** (disabled until every comparison has a value) and **Cancel**;
  **+ Rule** is hidden while a draft is open. A rule without a condition never fires, so a rule already
  in the document without one shows "Add a condition — an empty rule never
  fires."; for "otherwise", use **Default next**. See
  [[Logic and Branching|Studio-Logic-and-Branching]];
- **Comments** — a discussion thread on this page for your team
  ([[Working Together|Studio-Collaboration]]).

---

## Blocks

A **block** groups questions inside a page so the group can be shown, hidden
or shuffled as a unit. Add one from **+ Question → Block** (it is called "New
block").

Block properties:

- header: **Block**, the number of items, and **Delete block and its
  questions**;
- **Block** section — **Title** and **Randomize question order**;
- **Logic** section — **Show if**, **Hide if**.

---

## Adding, moving and deleting

- **Add** with **+ Page**, **+ Question**, **Add to block** or **Add your first
  question** (see above).
- **Drag** a question card or a block:
  - onto another card — it drops before or after it, depending on which half
    you release over;
  - into a block's body — it goes to the end of that block;
  - onto a page in the rail — it goes to the end of that page;
  - onto **Drop here to move to the end of the page**, which appears while you
    drag.
  A block cannot be dropped into itself.
- **Drag a page** in the rail to reorder the interview, or use **↑ ↓** in the
  canvas bar.
- The **Move up** / **Move down** buttons on a card are the keyboard
  alternative (within the same page or block).
- **Delete** with the trash button in the Inspector header — **Delete
  question**, **Delete block and its questions**, **Delete page**.

> **Note.** Deletes happen immediately, with no confirmation. If you delete
> the wrong thing, press **↶** (`Ctrl/Cmd + Z`).

---

## The Inspector

The right-hand panel shows the selected question, block or page in collapsible
sections. Studio remembers which sections you keep open, per browser. With
nothing selected it says "Select a page or a question to edit it."

### Question

- **Header** — the **type** dropdown (changing it converts the question — see
  [Converting a type](Studio-Question-Types#converting-a-type)),
  `id → variables`, and **Delete question**.
- **Question** — **Question text**, **Hint** ("optional guidance shown below
  the question"), **Required**, **Randomize option order** (Single choice,
  Multiple choice, Ranking), **Attention check** (Single choice, Likert scale,
  Number, Open text) and, when the assistant is on for your organization,
  **Reword** and **Suggest options** ([[AI Assistant|Studio-AI-Assistant]]).
- **Options** (choice questions) or **Answer** (all others) — the
  type-specific settings; see [[Question Types|Studio-Question-Types]].
- **Variable** (marked *codebook*) — the codebook entry this question writes:
  name, scale, variable label, value labels, valid range; one card per
  variable, including each row of a Matrix. Once the questionnaire has been
  published, the section adds: "This questionnaire has been published.
  Renaming a variable renames its column in the data: answers already
  collected keep the old name, answers collected after you publish again get
  the new one." See [[Codebook and Variables|Studio-Codebook-and-Variables]].
- **Logic** — **Show if**, **Hide if** and **Skip to** ("on Next, after any
  answer to this question — checked before the page’s Branch rules";
  **— next page —** or a page name). Opens by itself when the question has
  logic.
- **Advanced** (closed by default) —
  - **Id** ("names the question in scripts and comments; logic and data use
    the variable") — letters, digits and `_`; other characters turn into `_`.
    An Id another question already has, or one that is another question's
    variable, is flagged under the field (see
    [Question Id and variable name](#question-id-and-variable-name));
  - a reminder that `{answer:variable}` and `{label:variable}` insert a
    previous answer into the question text or hint;
  - **Tags** ("comma-separated") — free labels for your own organization;
  - **Media URL** ("image / video shown with the question — a public https://
    address; a file under Files has no public link") — a link ending in
    `.mp4` or `.webm` is shown as a video, anything else as an image.
- **Comments** (closed by default) — the question's comment thread.

> **Tip.** For **Media URL**, use a stable public address (your website, a
> public bucket, an image host). A download link copied from **Files** is
> signed and **expires after 5 minutes**, so respondents would see a broken
> image.

### Block and page

See [Blocks](#blocks) and [Page properties](#page-properties).

### Resizing

Drag the divider between the canvas and the Inspector to make the Inspector
wider or narrower (300 to 760 pixels, and at most 55 % of the window). With the
divider focused, `←` and `→` move it by 16 pixels; `Home` or a double-click
resets it to 340 pixels. The width is remembered in this browser.

---

## Conditions in brief

**Show if**, **Hide if**, branch rules and option conditions all use the same
editor. Closed, it shows the condition as a sentence with **Edit** and
**Clear** (or **Add condition**). Open, it is a list of rows —
*variable · operator · value* — combined with **ALL of the following** or
**ANY of the following**, plus **+ Condition** and **Done**:

| Operator | Meaning |
|---|---|
| `=`, `≠`, `>`, `≥`, `<`, `≤` | compare the answer with a value |
| **in**, **not in** | the answer is (not) one of several codes — pick them under **choose codes** |
| **chose**, **did not choose** | for multiple choice: the answers include (do not include) a code |

For a variable with value labels, the value is picked from a list
("Satisfied (4)"). A condition the rows cannot represent (nested groups, text
from an import) opens as JSON instead. Everything else — piping, skip logic,
the Logic map, the checks — is in
[[Logic and Branching|Studio-Logic-and-Branching]].

---

## Structure and Preview

**Structure | Preview** in the canvas bar switches the middle column:

- **Structure** — the editable cards described above.
- **Preview** — the engine's actual survey runtime, rendering your *working*
  document (unsaved edits included) the way a respondent sees it. It rebuilds
  about half a second after each edit.
  - **Desktop | Mobile** switches the frame width.
  - The status line reads "Respondent view · page *name* · click a question to
    edit it": clicking a question selects it in the Inspector, and selecting a
    page or question in the rail moves the preview there.
  - **Restart** ("Restart the preview from page 1") starts the interview over.
  - Answers are **never stored**; submitting shows the toast "Preview
    submitted — answers are not stored".
  - If the document cannot be built you see "Could not build the preview" with
    the reason, and "Fix the document to render the preview."

### The Preview button

**Preview** in the header goes further: it builds a **preview deployment** —
the full published survey at its own address — from the **current Save** and
shows it in a new tab.

- It needs a Save of what you see: with unsaved edits you get "Save first — a
  preview is built from a Save".
- The new tab opens at once, titled **Preview**, and says "Building the
  preview of Save #17… This tab shows it as soon as it is ready." It switches
  to the survey when the build is live. If the build fails the tab closes
  and the toast says **Preview build failed — see the card's log**.
- Toasts: **Building preview of #17…**, then **Preview ready — not accepting
  responses**.
- A Save marked `errors` cannot be previewed.
- The preview deployment also appears on **Distribute**; it never collects
  responses. The survey shows a fixed banner at the bottom, "Preview —
  answers are not stored", and ends on the survey's normal completion page. A
  preview built before this banner existed shows it once you build that
  preview again. See [Preview deployments](Studio-Publishing-and-Environments#preview-deployments).

For a link colleagues can open without an account, use **Test → Share
preview** ([[Testing Your Survey|Studio-Testing-Your-Survey]]).

---

## Saving

Press **Save changes** (or `Ctrl/Cmd + S`, which works even while you are
typing in a field). The **Save** dialog explains what will happen — "A new
version of questionnaire.json and a Save you can deploy, preview or restore
later." — and asks for a **Message** (optional, placeholder
`Add charging-access question`, up to 240 characters). `Enter` or **Save**
saves.

- With nothing changed the dialog says "No document changed — this Save
  re-pins the current versions and re-validates them with the current engine."
  That is useful after an engine update.
- With the message left empty, Studio writes one: `Update questionnaire`.
- The engine validates the questionnaire and generates `questionnaire.py`.
  The toast says one of:

  | Toast | Meaning |
  |---|---|
  | **Saved #18** | clean |
  | **Saved #18 (warnings)** | the engine has remarks; publishing asks you to confirm |
  | **Saved #18 — the questionnaire has 1 error (see Builder → Validation)** | the engine's check graded one or more findings as errors (for example an empty page, `EMPTY_PAGE`). They do not stop the Save or publishing — the Save is `warnings` — but publishing asks you to confirm with **Publish anyway** |
  | **Saved #18 — flow *name* has errors and cannot run until fixed** | a flow failed the engine's check; the questionnaire is unaffected ([[Analysis Flows\|Studio-Flows]]) |
  | **Saved #18 with errors — see History** | the questionnaire does not validate; the Save is `errors` and cannot be published |

- A **malformed** document is refused outright and nothing is saved: "Save
  failed." followed by the reason, which names the field and where it is —
  for example "questionnaire: pages/0/items/0/text: must not be empty (page
  'page1', question 'q1')". The usual causes are listed in
  [What the engine refuses](Studio-Question-Types#what-the-engine-refuses).
- A document the engine can read but that breaks a rule (a duplicate question
  id, a question Id that is another question's variable name, a skip to a page
  that does not exist, a page nobody can reach, …) **is** saved, marked
  `errors`, and cannot be published until you fix it and Save again.

### When a colleague saved first

If someone saved while you were editing, the dialog says who:

> *Ada Lovelace* saved #18 ("Add region quota") while you were editing on top
> of #17. Reload their Save to see it (your edits stay as an unsaved draft), or
> save yours on top of it as #19.

**Reload #18** loads their Save and keeps your edits on top as an unsaved
draft; **Save on top** saves yours as #19 anyway; **Cancel** closes the dialog.

---

## Drafts and autosave

Between Saves your edits are autosaved to the server as a private **draft**
1.5 seconds after your last change. The routine messages sit quietly in the
version-chip popover:

| Message | Meaning |
|---|---|
| "Draft waiting to sync…" | an edit will be saved as a draft in a moment |
| "Syncing draft…" | the draft is being written |
| "Draft synced — not yet saved as a version." | your edits are safe; they are not a Save yet |

Messages that need your attention appear in a band under the header:

| Message | What to do |
|---|---|
| "Draft sync failed. Your edits remain in this tab. Retry before closing it." | press **Retry draft sync**; do not close the tab until it succeeds |
| "A newer version exists. Review the conflict when saving." | someone saved since your draft started; the Save dialog will show who |
| "Restored draft. Draft restored — save a version when ready." | Studio brought back unsaved edits from an earlier visit |
| "An unsaved draft from an older version was not restored — the document has been saved since." | your old draft was older than the current Save, so it was not applied |
| "Could not check for a saved draft. Your current edits are kept in this tab." | a network problem; your edits in this tab are fine |
| "Could not clear the previous draft. Reopen the editor to review it before publishing." | reopen the Builder before you publish |

Switching to another project tab and back simply picks your edits up again.
When you open the Builder after a reload, in a new tab or on another computer
and Studio finds unsaved edits you made earlier, a toast says **Unsaved edits
restored — Save to keep them as a version**. To throw them away, use **More ▾
→ Discard changes**. If you try to close or reload the
tab with unsaved edits, the browser asks whether you really want to leave.

---

## Undo and redo

- **↶** / **↷**, `Ctrl/Cmd + Z` and `Shift + Ctrl/Cmd + Z` (or `Ctrl/Cmd + Y`)
  undo and redo up to **100** steps.
- While your cursor is in a text field, these keys undo your typing in that
  field instead.
- Undo covers everything that changes the document, including imports,
  deletes and **Apply** in the Source tab.
- The history is **cleared** when you Save, when you **Discard changes**, and
  when you leave the Builder or switch project. (Your draft survives; the undo
  steps do not.)

---

## The Source tab

**More ▾ → Source** shows the questionnaire document as JSON — the same
`survey/questionnaire.json` that is versioned and published.

| Control | What it does |
|---|---|
| **Copy** | copies the JSON to the clipboard |
| **.json** | downloads it as `questionnaire.json` (importable into any project) |
| **Revert** | throws away your edits in this tab |
| **Check** | runs the engine's check on the text without saving; shows **Check result** with the issues, or "No issues — the document validates." |
| **Apply** | replaces the working document with the text (an ordinary, undoable edit) |

While you have typed in Source without applying, a band says "You have
unapplied source edits. Apply or revert them in Source before saving.", with
**Open Source** when you are on another tab, and **Save** is disabled ("Apply
or revert source edits before saving"). If the text is not valid JSON you see
"This is not valid JSON" with the parser's message, or "The document must be a
JSON object."

Source is the escape hatch for anything the Builder does not offer yet, such as
the *kind* of a missing-value code, missing codes for a variable whose
Codebook row cannot be opened (see
[Missing codes](Studio-Codebook-and-Variables#missing-codes)), or the codes
an **Other** or **None of the above** option stores (`other_code`,
`none_code` in the question's `metadata`). **Apply** goes through the same
bookkeeping as any other edit: a page with a Body and no questions is stored
as a text-only page, and one with questions as an ordinary page.

---

## Export Python

**More ▾ → Export Python** ("Download the generated questionnaire.py for the
current Save") downloads the `questionnaire.py` the engine generated when the
current Save was made — the exact file that was validated and is published,
not a fresh re-generation. The toast says **Downloaded questionnaire.py**. It
is disabled until the project has a Save. The file's header explains how to
run it with `pip install siamang` and `siamang validate questionnaire.py`. See
[[Reproducibility: Code, Bundles and Citation|Studio-Reproducibility]].

---

## Read-only states

**A colleague holds the edit lock.** Only one person edits the questionnaire at
a time. When someone else is editing, a banner says:

> **Ada Lovelace** is editing — you are following their changes live (last
> edit 2 minutes ago). Your own edits are off until you take over; comments
> stay open.

You see their unsaved edits as they make them; **Save** is disabled ("Ada
Lovelace is editing"). **Take over** moves the lock to you; they get the
message "… took over editing — you are now following their changes", and their
unsaved work stays as their private draft. See
[[Working Together|Studio-Collaboration]].

**The workspace is frozen.** Support can freeze an organization; a banner then
says "This workspace is frozen and read-only." Everything stays viewable and
exportable, but every change — including a Save — is refused. A trial that
ends does **not** freeze the workspace: it continues on the Free plan. See
[[Plans, Trial and Billing|Studio-Plans-and-Billing]].

Older Saves are not opened in the Builder: they open read-only in **History**,
where you can restore one as a new Save
([[History and Versions|Studio-History-and-Versions]]).

---

## On a phone

On a phone-width screen a bar with **Preview** and **Save** stays at the bottom
of the screen, so you never have to scroll back to the header to save.

## See also

- [[Question Types|Studio-Question-Types]]
- [[Codebook and Variables|Studio-Codebook-and-Variables]]
- [[Logic and Branching|Studio-Logic-and-Branching]]
- [[Testing Your Survey|Studio-Testing-Your-Survey]]
- [[Projects|Studio-Projects]]

<!-- studio-nav -->
---

← [[Plans, Trial and Billing|Studio-Plans-and-Billing]] · [Studio contents](Studio-Overview#all-pages) · [[Question Types|Studio-Question-Types]] →
