# Testing Your Survey

Studio gives you several ways to check a questionnaire before real
respondents see it. Each answers a different question:

| Tool | Where | Answers |
|---|---|---|
| **Validation** | Builder → **Validation** | Is the questionnaire correct, and can it be published? |
| **Preview** (canvas) | Builder → **Structure → Preview** | Does it look and behave right while I edit? |
| **Walkthrough** | Builder → **Test → Walkthrough** | Does the routing do what I meant? |
| **Simulate** | Builder → **Test → Simulate** | Will the data have the shape my analysis expects? |
| **Share preview** | Builder → **Test** → **Share preview** | Can a colleague or client look without an account? |
| **Preview** (header) | Builder header → **Preview** | What exactly will respondents get from this Save? |

This page covers each one and ends with a pre-launch checklist.

---

## Validation

**Builder → Validation** has four sections.

### Structure

"checked as you edit". Studio's own checks on the working document. The
section appears only when there is something to report; each row is amber,
and clicking it opens the item in Structure. The messages:

| Message | What to do |
|---|---|
| `<id>: question has no text` | write the question |
| `duplicate question id "<id>"` | give each question its own id |
| `<id>: no choices` | add options to the choice or ranking question |
| `<id>: one variable per row is required (N rows, M variables)` | a matrix's rows and variables got out of step |
| conjoint and MaxDiff design messages (tasks vs variables, too few attributes, levels or items) | see [[MaxDiff and Conjoint|Studio-MaxDiff-and-Conjoint]] |
| `<id>: skip_to points at unknown page "<page>"` | pick an existing page |
| `<id>: pipes {label:x}, but no variable "x" exists` | fix the piping token |
| `duplicate page name "<name>"` | rename one page |
| `<page>: next_if target "<t>" does not exist` / `<page>: default_next "<t>" does not exist` | pick an existing page |
| `<page>: the branch to "<target>" has no condition — an empty rule never fires; add one, or use Default next` | give the rule a condition, or remove it and set **Default next** |
| `<item>: the condition reads "<var>", which no question collects and the codebook does not declare` | a typo, or a variable that no longer exists |
| `<item>: the condition reads "<var>", but <question> on page <page> has not been answered when this condition is evaluated — it can never be true` | a forward reference: move the question earlier or the condition later |

These checks never block a Save. See also the Logic map in
[[Logic and Branching|Studio-Logic-and-Branching]].

### Engine

"compile + strict lint of the working document, without saving". Press
**Check now** ("Checking…") to run the engine's check on what is on screen,
unsaved edits included.

- Before a check: "Run a check to compile the working questionnaire with the
  engine."
- Clean: "Compiles cleanly — no warnings from the strict lint."
- Findings are listed with their code, message and location. They are not
  clickable.
- The result is cleared as soon as you edit again.
- **Check now** does **not** check quota cells. The Save does, and so does
  the **Check** button in the **Source** tab, which runs the full Save-time
  check without saving.

### Last Save

"#N · <state> · engine <version>": the findings recorded with your latest
Save. Before any Save: "Save the project to run validation." A clean Save:
"The last Save validated without issues."

### Assistant

The AI assistant's review of your wording. It is opinion, not a rule; see
[[AI Assistant|Studio-AI-Assistant]].

### What blocks publishing

Every Save is checked, and the **Save badge** in the topbar shows the result:
**● valid #N**, **● warnings #N**, **● errors #N**, **checking**, **unsaved**
or **saving…**.

| What the engine finds | Shown as | Save state | Publishing |
|---|---|---|---|
| a `VALIDATION` error: the questionnaire cannot run | red | **errors** | refused: "Saved #N has validation errors — fix them in the Builder before publishing" |
| a lint finding graded **error**, such as `EMPTY_PAGE`, `CATEGORICAL_WITHOUT_LABELS` or `INCOMPATIBLE_QUESTION_SCALE` | red | **warnings** | allowed after confirmation |
| a lint **warning** | amber | **warnings** | allowed after confirmation: "Publish #N with warnings" — "Save #N validated with warnings (see History). Publish it to <env> anyway?" → **Publish** |
| nothing | none | **valid** | allowed |

So a red finding does not always block. Only `VALIDATION` errors do. Read
every red finding anyway: a lint error usually means the data will be hard to
analyze.

A document the engine cannot even read (a malformed edit in **Source**, for
example) is not saved at all: Save reports the problem and nothing is
stored.

**`VALIDATION` errors**, which block publishing:

- pages nothing leads to ("Unreachable pages in navigation graph: …") and
  routing loops ("Cycle detected in page navigation graph.");
- a Skip to, branch rule or default next pointing at a page that does not
  exist;
- duplicate question ids, empty or duplicate page names, and the same
  variable written by two questions;
- a question whose Id is another question's variable name ("Question '<id>'
  has the id under which question '<other>' stores its answer …");
- a Matrix, MaxDiff, Conjoint or wide Multiple choice whose Id is another
  question's variable name. These questions store their answers under their
  Id, so the two would share one name ("Duplicate answer key in
  questionnaire: questions '<a>' and '<b>' both store their answer under
  '<name>'.");
- a condition that reads a variable that no question collects, no **Assign
  to a condition** writes and the codebook does not declare ("… references
  unknown variables: …");
- a script whose target no longer exists;
- quota cells on an unknown variable, on a value that is not one of the
  variable's categories, or twice for the same value.

**Lint findings graded error** (red, but publishable):

| Code | Meaning |
|---|---|
| `EMPTY_PAGE` | a content page with no questions. Pages that only show text are reported too; that is safe to publish |
| `INCOMPATIBLE_QUESTION_SCALE` | a number question on a nominal or ordinal variable, or a Likert question on a non-ordinal one |
| `CATEGORICAL_WITHOUT_LABELS` | a choice question whose variable has no value labels |
| `CONJOINT_TOO_FEW_ATTRIBUTES`, `CONJOINT_NOT_ESTIMABLE`, `MAXDIFF_TOO_FEW_ITEMS`, `MAXDIFF_COMPLETE_DESIGN` | a choice design that cannot be analyzed as set up |

**Lint warnings** (amber):

| Code | Meaning |
|---|---|
| `REQUIRED_CONDITIONAL` | a required question also has a show if (usually fine) |
| `CONTRADICTORY_VISIBILITY` | an item has both show if and hide if |
| `UNKNOWN_CONDITION_VALUE` | a condition compares with a code the variable does not have |
| `PIPE_UNKNOWN_VARIABLE`, `PIPE_FORWARD_REFERENCE` | piping a variable that does not exist, or one answered later |
| `REDUNDANT_NAVIGATION` | a default next that is the next page anyway |
| `MISSING_NAVIGATION` | a page with no way onward |
| `UNUSED_VARIABLE` | a codebook variable no question writes: the arm of **Assign to a condition** (expected), or a name left behind when you renamed a variable (check the conditions that still read it) |
| `SCRIPT_STALE_QUESTION_ID`, `SCRIPT_TARGET_IS_A_PAGE`, `SCRIPT_TARGET_IS_A_QUESTION` | a custom script that names a question by an Id its answer is not stored under, or targets the wrong kind of thing for its trigger (see [Checks and errors](Studio-Scripts#checks-and-errors)) |
| `EXCLUSIVE_CODE_UNKNOWN`, `OPTION_CODE_WITHOUT_LABEL`, `LIKERT_POINTS_LABEL_MISMATCH`, `MISSING_CODE_NOT_IN_LABELS`, `RANGE_LABEL_MISMATCH` | question options, value labels, missing codes and ranges out of step (see [[Codebook and Variables|Studio-Codebook-and-Variables]]) |
| `CONJOINT_SINGLE_VERSION`, `MAXDIFF_SINGLE_VERSION` | every respondent sees the same design |
| `EMPTY_QUESTIONNAIRE` | nothing to ask yet |

The engine does not detect forward references in conditions or branch rules
with an empty condition. Only the **Structure** section and the Logic map do.

---

## Preview on the canvas

**Structure → Preview** (the switch above the canvas) renders the **whole
survey** with the same runtime respondents get, built from your working
document, unsaved edits included. It rebuilds about half a second after each
edit.

- The bar shows **Desktop** / **Mobile** and a status: "Rendering…",
  "Respondent view · page <name> · click a question to edit it", or
  "Respondent view · the engine's runtime · answers are not stored".
- You can answer and move through pages as a respondent would. The preview
  follows your selection in the Builder, and clicking a question selects it
  for editing.
- **Restart** ("Restart the preview from page 1") starts over, with a new draw
  of every shuffle.
- Submitting shows "Preview submitted — answers are not stored". Nothing is
  saved anywhere.
- A document that cannot be built shows "Could not build the preview…" and
  "Fix the document to render the preview."

The canvas preview shows the same progress indicator as the published survey
(see
[Question style and progress](Studio-Theme-and-Branding#question-style-and-progress)).
For the exact published build of a Save, use the header
[Preview](#the-preview-button).

---

## Walkthrough

**Builder → Test → Walkthrough** puts the survey on the left and **Evaluated
conditions** on the right. It uses the working document, unsaved edits
included. Clicking a question does not select it here.

```
┌─ survey ───────────────────────────┐  Evaluated conditions
│                                    │  screener · page 1 of 6 · 2/3 answered
│  How old are you?   [ 34 ]         │  ● q_student show_if → hidden
│  Are you a student? ( ) Yes ( ) No │  ● next_if #1 → screenout · no match
│                                    │  ● next_if #2 → students · no match
│                     [Next →]       │  Next → about_you (next page)
└────────────────────────────────────┘  Path so far: welcome → screener
```

The panel lists, for the page you are on:

- "block <title> show_if|hide_if → shown|hidden";
- "<question> show_if|hide_if → shown|hidden", or "hidden with block <title>";
- "<question> skip_to <page> → fires" or "→ waits for an answer";
- "next_if #n → <page> · matches" or "· no match";
- "page <name> show_if|hide_if → skipped" for pages that will be passed over;
- "no conditions on this page";
- the line "Next → <page> (skip_to on <question> | next_if #n | default_next |
  next visible page | next page)", or "End of the survey.";
- **Path so far**, once you have visited two pages. Then: "Restart the
  preview to try another path."

The header line reads "<page> · page X of Y · A/V answered" (answered of
visible questions). Answer-option conditions, option order and scripts are
not listed.

Take the walkthrough at least twice: once as someone who qualifies, once as
someone who is screened out. It is the fastest way to debug routing. Scripts
run here, so an **Assign to a condition** arm is drawn (with the weighted
draw) and conditions on it are evaluated; press **Restart** to draw again.

---

## Simulate

**Builder → Test → Simulate** asks the engine for synthetic respondents
generated from your questionnaire: "Synthetic responses generated by the
engine from the questionnaire's logic (your unsaved edits included) — the
same generator the sandbox uses for simulate(). Use them to test flows and
exports before fieldwork."

| Control | Notes |
|---|---|
| **Responses** | 1 to 5,000; default 200 |
| **Seed** | default 42; the same seed gives the same data |
| **Simulate** | ("Simulating…") shows a preview table |
| **CSV**, **Excel**, **SPSS**, **Stata**, **Parquet** | download all the simulated rows as `simulated-<n>.<ext>`. Toasts: "Preparing simulated-200.csv…", then "Downloaded simulated-200.csv". SPSS and Stata files carry value labels and missing codes like a real export |

The result shows "Preview · 50 of 200 rows · seed 42" (the first 50 rows;
empty cells show "—"), then "Codebook · N variables" with each variable's
label, value labels and scale.

**What the generator does.** Each simulated respondent starts on page one
and moves the way a respondent would. It follows page show if / hide if,
question show if / hide if, Skip to, branch rules and default next, and stops
at the first end page it reaches. Questions never reached stay empty, so
screen-outs and branches split the sample. Answers are drawn at random:

- choice codes uniformly;
- numbers within the variable's valid range, otherwise between 18 and 70;
- `sample text` for open text, or a made-up address, phone number, web
  address, date or time for formatted fields.

**What it ignores:** block show if / hide if (questions in a hidden block are
still answered), answer-option conditions, randomization, scripts (so the
**Assign to a condition** arm is not filled, and conditions that read it are
checked as if it were unanswered), quotas, required answers and attention
checks.

The questionnaire must pass the engine's check: a `VALIDATION` error gives
"Simulation failed…" with the reason.

**Why bother.** You can build and debug your whole analysis flow before the
first real respondent arrives, then run the same flow on live data (a flow
can read simulated data; see [[Analysis Flows|Studio-Flows]]). It is also the
honest way to check that a long instrument produces the variables your
analysis plan assumes.

---

## Share preview

**Test → Share preview** (on both the Walkthrough and Simulate views) mints a
public link so a colleague or client can click through the survey without a
Studio account.

- Before you create one: "A public link to this working document for
  colleagues and clients — no account needed, expires in 24 hours." If there
  are no unsaved edits, it says "this Save" instead.
- Click **Share preview** ("Creating link…"). The link is **copied to your
  clipboard automatically** and shown with a **copy** button and "valid until
  <date and time> · answers are not stored".
- Anyone with the link can open it for **24 hours**. After that it answers
  "this preview link has expired or never existed".
- You can create up to **50 links per day**. Beyond that: "at most 50 shared
  previews per day; reuse an existing link".
- It is a plain respondent page, without the Walkthrough panel. Submitting
  shows the completion screen, but nothing is stored.

Use it for wording review and client sign-off. For a real pilot that records
answers, publish to the `pilot` environment
([[Publishing and Environments|Studio-Publishing-and-Environments]]).

---

## The Preview button

The Builder header's **Preview** ("Building…") builds the **latest Save** the
same way publishing does, as a preview deployment that never accepts
responses. It is the closest thing to the published survey: theme, progress
indicator, completion screen and scripts behave as they will in the field.

- With unsaved edits it refuses: "Save first — a preview is built from a
  Save".
- Toasts: "Building preview of #N…", then "Preview ready — not accepting
  responses" (or "Preview build failed — see the card's log").
- If this Save has been previewed before, the preview opens in a new tab.
  Otherwise it builds and appears as a `preview` card on **Distribute**, where
  you open it.
- Answering it to the end shows the **Submission failed** dialog, because
  preview deployments do not accept responses. That is expected.
- Previews are removed automatically after **7 days**. **History** can
  preview any earlier Save the same way.

See [Preview deployments](Studio-Publishing-and-Environments#preview-deployments).

---

## A pre-launch checklist

1. **Validation.** The last Save is **valid**, or every warning and red lint
   finding is understood. The **Structure** section is empty.
2. **Logic map.** No issues on either lens, and no branch rule labeled
   "no condition — never fires".
3. **Walkthrough, twice**: once qualifying, once screened out. Check that
   each route ends on the page you intended. If you used **Also end the
   survey for respondents who fail**, make sure the Screen-out page sits
   after the Final page (see
   [Attention checks](Studio-Logic-and-Branching#attention-checks)).
4. **Quotas.** Quota cells count but do not stop anyone. Set the environment's
   response cap for your total, put quota questions early, and decide how you
   will react when a cell fills
   ([[Quotas and Randomization|Studio-Quotas-and-Randomization]]).
5. **Randomization.** If you use **Randomize pages**, your introduction or
   screener is the first page and your end pages come after the last content
   page.
6. **Theme.** Contact email, privacy link and ethics statement are filled in.
   The expected duration is written into the first page (the **Estimated
   minutes** field is not shown).
7. **Simulate** 200 respondents, download the SPSS file and open it. Do the
   labels and missing codes look right? Build your flow on the simulated
   data ([[Analysis Flows|Studio-Flows]]).
8. **Header Preview.** Look at the progress indicator, logo, footer and
   completion screen as respondents will see them.
9. **Pilot.** Publish to `pilot`, answer it along each route, and look at
   **Data**: responses, screen-outs, and the quota bars on the pilot card.
10. Only then publish to `main`.

## See also

- [[Logic and Branching|Studio-Logic-and-Branching]]
- [[Publishing and Environments|Studio-Publishing-and-Environments]]
- [[Theme and Branding|Studio-Theme-and-Branding]]
- [[AI Assistant|Studio-AI-Assistant]]
- [[Data Quality|Studio-Data-Quality]]

<!-- studio-nav -->
---

← [[Question Bank, Templates and Library|Studio-Question-Bank-and-Library]] · [Studio contents](Studio-Overview#all-pages) · [[AI Assistant|Studio-AI-Assistant]] →
