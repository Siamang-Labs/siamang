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
| `<id>: skip_to points at unknown page "<page>"` | pick an existing page (a Skip to that names an existing question's Id is accepted) |
| `<id>: pipes {label:x}, but no variable "x" exists` | fix the piping token |
| `<id>: the screen-out branch for failing this attention check does not work. <reason>` | press **Fix the branch** under the question's **Also end the survey for respondents who fail**, or follow the reason (see [Attention checks](Studio-Logic-and-Branching#attention-checks)) |
| `<id>: writes variable "<v>", which <other> already writes — each variable belongs to one question` | rename one of the variables |
| `<id>: stores its answer under "<key>", as <owner> does — rename one of them` | rename one question's Id or variable |
| `<id>: the id is the variable <owner> stores its answer under, and the engine refuses that — rename the id (Advanced → Id)` | give the question another Id |
| `<id>: the id is a variable <question> stores an answer under, and the engine refuses that — rename the id (Advanced → Id)` / `<id>: the id is one of the variables this question stores its answers under, and the engine refuses that — rename the id (Advanced → Id)` | the Id is a Matrix row or another variable a question stores (its own, for a matrix with a separate name) while the question's own variable is different: give the question another Id |
| `<id>: the id is where <question> stores the text typed into Other — scripts naming it would reach <variable> instead; rename the id (Advanced → Id)` (or "…where this question stores…"), `<id>: the id is the variable an Assign to a condition script stores the arm in — …` | the Id differs from the question's variable and is a name the survey stores something else under: give the question another Id (see [Names an Id may not take](Studio-Builder-Overview#names-an-id-may-not-take)) |
| `<id>: the id is a codebook variable a custom script writes — scripts naming it would reach <variable> instead; rename the id (Advanced → Id), or, if the codebook entry "<id>" is left over from renaming this question's variable, delete that entry in the Codebook tab so the script's "<id>" means this question` | give the question another Id if the script means the codebook variable; if the entry is a leftover and the script means the question (an older prefill by Id), delete the entry in **Builder → Codebook** instead |
| `<id>: ids starting with "__" are the survey runtime's own names — rename the id (Advanced → Id)` | the Id differs from the question's variable and starts with `__`: give the question another Id |
| `<id>: the variable "<v>" starts with "__" — the survey runtime never submits it; rename the variable` | the survey never submits a `__` key, so these answers would never reach the data: rename the variable |
| `<id>: stores its “Other (please specify)” text under "<key>", which <question> already stores an answer under, and the engine refuses that — rename this question's variable or <question>'s` (or "…which this question already stores…", "…rename that option's variable", "…rename <question>'s variable") | the Other text column is a name a question already stores an answer under: rename one of the two variables (see [Single choice](Studio-Question-Types#single-choice)) |
| `<id>: the codebook still declares a variable "<id>" that no question collects and nothing writes — delete it in the Codebook tab` | an unused codebook entry, usually left behind when an earlier Builder renamed the question's variable; the Id is fine. Delete the entry in **Builder → Codebook** |
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
- When the lint finds errors, a red line above the list says so: "1 error
  (red): it does not stop a Save, and publishing asks for a confirmation first
  — fix it before fieldwork." (or "N errors (red): they do not stop a Save, …
  — fix them before fieldwork.").
- **Check now** also checks the quota cells, as the Save does: a cell on an
  unknown variable or value, or a duplicate cell, shows as a `VALIDATION`
  error here, word for word as the Save reports it (see
  [Quotas](Studio-Quotas-and-Randomization#the-quotas-tab)).
- A document that breaks the questionnaire format fails the check with the
  message Save would give, naming the field, for example
  `questionnaire: pages/0/items/0/text: must not be empty (page 'page1', question 'q1')`.
- The result is cleared as soon as you edit again.
- The **Check** button in the **Source** tab runs the full Save-time check on
  your Source edits without saving.

### Last Save

"#N · <state> · engine <version>": the findings recorded with your latest
Save. When the lint found errors, the state reads "1 error — publishable after
a confirmation" (or "N errors — …"). Before any Save: "Save the project to run
validation." A clean Save: "The last Save validated without issues."

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
| a lint finding graded **error**, such as `EMPTY_PAGE`, `CATEGORICAL_WITHOUT_LABELS` or `INCOMPATIBLE_QUESTION_SCALE` | red | **warnings** | allowed after confirmation: "Publish #N with errors" — "Save #N has 1 error the engine's lint found in the questionnaire: <message>. It does not stop publishing, but the survey goes out with it — see Builder → Validation. Publish it to <env> anyway?" → **Publish anyway** |
| a lint **warning** | amber | **warnings** | allowed after confirmation: "Publish #N with warnings" — "Save #N validated with warnings (see History). Publish it to <env> anyway?" → **Publish** |
| nothing | none | **valid** | allowed |

With several lint errors the confirmation names the first ("<message> (and N
more)") and reads "They do not stop publishing, but the survey goes out with
them". Such a Save is announced as "Saved #N — the questionnaire has 1 error
(see Builder → Validation)" (or "N errors") instead of "Saved #N (warnings)",
and **New deployment → Version** marks it "saved with 1 error — publishable
after a confirmation".

So a red finding does not always block. Only `VALIDATION` errors do. Read
every red finding anyway: a lint error usually means the data will be hard to
analyze.

A document the engine cannot even read (a malformed edit in **Source**, for
example) is not saved at all: Save reports the problem, naming the field and
where it is (`questionnaire: pages/0/items/0/choices/0/label: must not be empty (page 'page1', question 'q1')`),
and nothing is stored.

**`VALIDATION` errors**, which block publishing:

- pages nothing leads to ("Unreachable pages in navigation graph: …") and
  routing loops ("Cycle detected in page navigation graph.");
- a Skip to, branch rule or default next pointing at a page that does not
  exist;
- duplicate question ids, empty or duplicate page names, and the same
  variable written by two questions;
- a question whose Id is another question's variable name ("Question '<id>'
  has the id under which question '<other>' stores its answer …");
- a question whose Id differs from its variable and is a name the survey
  stores something else under — a variable any question stores (a Matrix row
  included), a question's Other text (`<variable>_other`), the arm of
  an **Assign to a condition**, a codebook variable no question collects that
  a custom script writes, or a name starting with `__` ("Question '<id>'
  stores its answer under '<variable>', but '<id>' is also <what>. A script
  that names '<id>' could mean either; give the question another id." — for
  a codebook variable a script writes, it goes on: "…or, if the codebook
  entry '<id>' is left over from renaming this question's variable, delete
  that entry so that '<id>' in the script means the question."; see
  [Names an Id may not take](Studio-Builder-Overview#names-an-id-may-not-take));
- a Matrix, MaxDiff, Conjoint or wide Multiple choice whose Id is another
  question's variable name. The survey knows these questions by their Id
  (their variables are stored under their own names, but scripts and
  messages address the question by the Id), so the two would share one name
  ("Duplicate answer key in
  questionnaire: questions '<a>' and '<b>' both store their answer under
  '<name>'.");
- a condition that reads a variable that no question collects, no **Assign
  to a condition** writes and the codebook does not declare ("… references
  unknown variables: …");
- a script whose target no longer exists;
- quota cells on an unknown variable, on a value that is not one of the
  variable's categories, or twice for the same value (**Check now** reports
  these too).

**Lint findings graded error** (red, but publishable):

| Code | Meaning |
|---|---|
| `EMPTY_PAGE` | a page with neither questions nor text. A content page that only shows text (its **Body**) is not reported, and respondents see that text; one saved before this fix is reported until the Builder rewrites it at your next edit. An end page without a **Body** is reported too: a Final or Screen-out page whose body you cleared, and a Redirect page (the Inspector offers it no **Body** field) |
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
| `UNUSED_VARIABLE` | a codebook variable no question writes: the arm of **Assign to a condition** (expected), or an entry left over from an import or a Source edit. A variable a custom script writes (`answers.speeder = 1`, outside a comment) and the `<variable>_other` text of "Other (please specify)" are not reported |
| `SCRIPT_STALE_QUESTION_ID`, `SCRIPT_TARGET_IS_A_PAGE`, `SCRIPT_TARGET_IS_A_QUESTION` | a custom script that names a question by an Id its answer is not stored under, or targets the wrong kind of thing for its trigger (see [Checks and errors](Studio-Scripts#checks-and-errors)) |
| `EXCLUSIVE_CODE_UNKNOWN`, `OPTION_CODE_WITHOUT_LABEL`, `LIKERT_POINTS_LABEL_MISMATCH`, `MISSING_CODE_NOT_IN_LABELS`, `RANGE_LABEL_MISMATCH` | question options, value labels, missing codes and ranges out of step (see [[Codebook and Variables|Studio-Codebook-and-Variables]]) |
| `ADDED_CODE_WITHOUT_LABEL` | a question stores "Other (please specify)" or "None of the above" as a code its variable has no value label for (typically after an import; the Builder writes these labels itself) |
| `NA_STORED_AS_TEXT` | a Likert or Matrix question offers "Not applicable", but its variable declares no not-applicable missing code, so N/A is stored as the text `na`. The Inspector says so beside **Offer “N/A”**: "stored as the text “na” — the codebook declares no not-applicable code" |
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

- "block <title> show_if|hide_if → shown|hidden", for the page's blocks and
  for blocks inside them;
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
visible questions). A question counts as answered once it has everything
**Required** would ask of it: a Matrix once every row is answered, a MaxDiff
or Conjoint once every task is. A Matrix's Skip to line reads "→ fires" as
soon as any row is answered. Answer-option conditions, option order and
scripts are not listed.

Take the walkthrough at least twice: once as someone who qualifies, once as
someone who is screened out. It is the fastest way to debug routing. Scripts
run here, so an **Assign to a condition** arm is drawn (with the weighted
draw) and conditions on it are evaluated; press **Restart** to draw again.
Quotas are not checked in the Walkthrough: a full cell never stops you.

---

## Simulate

**Builder → Test → Simulate** asks the engine for synthetic respondents
generated from your questionnaire: "Synthetic responses generated by the
engine from the questionnaire's logic — conditions, routing, assigned arms,
page shuffles and quotas (your unsaved edits included). A respondent who
answers into a full quota cell stops there, as in the survey. Each answer is
drawn at random — every option as likely as the next, a number anywhere in
its valid range — so a consent or screening question turns away far more of
them than real fieldwork would, and their rows stop there. Use them to test
flows and exports before fieldwork." ("(your unsaved edits included)"
appears only when you have some.) On the example study, for instance, about
half the simulated respondents answer **No, not now** to the consent question
and stop there, so only about half reach the later pages; its sample
responses, on **Data**, are the realistic set.

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
and moves the way a respondent would. It follows page, block (blocks inside
blocks included) and question show if / hide if, Skip to, branch rules and
default next, and stops at the first end page it reaches. Questions never
reached, or hidden, stay empty, so screen-outs and branches split the sample.
On top of that:

- **Answer-option conditions**: an option hidden by its own show if / hide if
  is never chosen, and a question whose options are all hidden stays empty.
  In a wide Multiple choice, a hidden option's variable is empty rather than
  0, and an exclusive choice is never checked beside others.
- **Assign to a condition**: each respondent is drawn into an arm by the arms'
  weights (with **Balance**, the arm furthest behind its quota among the
  respondents simulated so far) before page one. The arm is a column of the
  result, with its codebook entry, and pages and questions gated on it are
  filled for that arm.
- **Randomize pages**: each respondent gets their own page order, first,
  last and end pages kept in place.
- **Quotas**: when a respondent leaves a page holding a value whose cell is
  already full, they stop there, as on the survey's quota-full screen: the
  later pages stay empty and they do not count as a complete. Only completes
  fill the cells, so the order of the simulated respondents matters, as in the
  field. An assigned arm counts too: once an arm's cell is full, the
  respondents drawn into it stop on leaving the first page, so no arm
  completes more than its limit.

Answers are drawn at random:

- choice codes uniformly, among the options on offer;
- numbers within the variable's valid range, otherwise between 18 and 70;
- `sample text` for open text, or a made-up address, phone number, web
  address, date or time for formatted fields;
- MaxDiff best and worst picks only among the items a task showed.

Every question a simulated respondent reaches is answered, required or not.

**What it ignores:** option shuffles (they do not change the data), the other
scripts (timers, **Shuffle options**, **Validate fields match**, Custom
JavaScript), and the text typed into "Other (please specify)". An attention
check's screen-out branch is an ordinary branch rule and is followed; the
check itself is not scored.

A file downloaded from Simulate before this update had no arm column and
answered questions in hidden blocks and hidden options; simulate again for
the current behavior.

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
Quotas are not checked.

- With unsaved edits it refuses: "Save first — a preview is built from a
  Save".
- A new tab opens at once, titled "Preview", with "Building the preview of
  Save #N… This tab shows it as soon as it is ready." It switches to the
  preview when the build is live, and closes if the build fails. Previewing a
  Save again waits for its rebuild before the tab loads.
- Toasts: "Building preview of #N…", then "Preview ready — not accepting
  responses" (or "Preview build failed — see the card's log").
- The build also appears as a `preview` card on **Distribute**.
- A fixed banner at the bottom reads "Preview — answers are not stored".
  Answering to the end shows the survey's normal completion page (or end
  page); nothing is stored. A preview built before this change ended on
  **Submission failed** instead; preview the Save again to rebuild it.
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
   survey for respondents who fail**, check that no attention check shows an
   error under the box (press **Fix the branch** if one does; see
   [Attention checks](Studio-Logic-and-Branching#attention-checks)).
4. **Quotas.** Full cells stop respondents on the quota-full screen, and only
   completed interviews count. Check each limit, put quota questions early,
   set the environment's response cap for your total, and set the **Quota
   full → return URL** if a panel sends the sample
   ([[Quotas and Randomization|Studio-Quotas-and-Randomization]]).
5. **Randomization.** If you use **Randomize pages**, your introduction or
   screener is the first page and your end pages come after the last content
   page.
6. **Theme.** Contact email, privacy link and ethics statement are filled in,
   and **Estimated minutes** is set (respondents see "About N minutes" on the
   first page). If the survey is not in English, every Wording field you need
   is translated.
7. **Simulate** 200 respondents, download the SPSS file and open it. Do the
   labels and missing codes look right? Do the arms and the quota cells split
   the sample as planned? Build your flow on the simulated data
   ([[Analysis Flows|Studio-Flows]]).
8. **Header Preview.** Look at the progress indicator, logo, footer and
   completion screen as respondents will see them.
9. **Pilot.** Publish to `pilot`, answer it along each route, and look at
   **Data**: responses, screen-outs, and the quota bars on the pilot card
   (screen-outs do not fill them).
10. Only then publish to `main`. A survey already in the field gets fixes to
    the survey runtime only when you publish it again.

## See also

- [[Logic and Branching|Studio-Logic-and-Branching]]
- [[Publishing and Environments|Studio-Publishing-and-Environments]]
- [[Theme and Branding|Studio-Theme-and-Branding]]
- [[AI Assistant|Studio-AI-Assistant]]
- [[Data Quality|Studio-Data-Quality]]

<!-- studio-nav -->
---

← [[Question Bank, Templates and Library|Studio-Question-Bank-and-Library]] · [Studio contents](Studio-Overview#all-pages) · [[AI Assistant|Studio-AI-Assistant]] →
