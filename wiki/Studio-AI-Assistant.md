# AI Assistant

The AI assistant *(Plus)* reads your work and makes suggestions. It drafts a
questionnaire from a brief, rewords a question, proposes answer options,
reviews the wording of a whole questionnaire and reviews an analysis flow. It
can also build a coding scheme for open answers. This page covers each
feature, how to turn the assistant on, what it sends where, and how its
allowance of credits works.

---

## Suggestions, not edits

The assistant never changes your questionnaire or your flows by itself.
Everything it returns is a **proposal** shown next to what you have:

- nothing changes until you press **Use this**, **Use this wording**,
  **Replace options** or **Use this draft**;
- an applied suggestion is an ordinary edit: it can be undone, and it becomes
  part of your study only when you **Save**;
- answer **codes** stay yours. The assistant proposes labels only, and
  options you already have keep their codes;
- its findings are labeled as opinions ("suggestions, not rules"), separate
  from the engine's checks, which are facts about the document.

---

## Turning it on

The assistant is included from **Plus** and is **off until the organization's
owner turns it on**. Turning it on is a consent decision:

> By turning this on you agree that questionnaire and analysis text from this
> organization may be sent to a third-party model provider, currently
> **DeepSeek**, which processes it in China. What is sent, and what never is,
> is set out in the Privacy Policy and the Terms of Use.

1. Open **Organization → Settings → Integrations**.
2. On the **AI assistant** card ("Reviews the wording of a questionnaire and
   the soundness of an analysis, on request. Off until you turn it on."),
   click **Turn the assistant on** ("Turning on…").
3. The card now reads "On · turned on by <name> on <date>." **Turn the
   assistant off** reverses it at any time.

Only the owner can do this. Admins and members see "Only the organization
owner can make this decision, because it sends your team's work to a provider
in another country." On Free the card reads "The assistant is a Plus
feature". See [Integrations](Studio-Organizations-and-Team#integrations).

### What is sent, and what is not

| Feature | Sent to the provider |
|---|---|
| **Review wording** | the questionnaire title and description, page names and titles, and for each question its id, type, text, hint, whether it is required, the scale of its variable, and its answer labels; plus the engine's own findings, so they are not repeated |
| **Reword**, **Suggest options** | that one question (id, type, text, hint, required, scale, answer labels), the survey's title and description, and your note |
| **Draft from a brief** | your brief, the working title and the language you named |
| Flow **review** | the flow's title and description, its steps with their settings and connections, and the codebook (variable names, labels, scales) |
| **Code open answers** | the open answers of one variable, and the question text |

Never sent: your theme, scripts, quotas, files, contact lists, or anyone's
answers. The exception is open-answer coding, whose whole purpose is to read
the answers.

---

## Draft from a brief

Available in a project **with no questionnaire yet**: the Builder's empty
state ("No questionnaire yet") shows **Draft from a brief** next to **Create
questionnaire**.

The **Draft from a brief** dialog: "Describe who you are asking and what you
want to learn. The assistant proposes questions; you read them, change them
and save them — nothing is saved for you." followed by "About N of your R
remaining credits."

| Field | Notes |
|---|---|
| **Brief** | up to 8,000 characters: who the respondents are, what you want to learn |
| **Language** ("optional — the brief's own language by default") | e.g. `English`, `German` |

**Draft questions** ("Drafting…") returns "<title> — N questions across P
page(s). Read it in the Builder before you save." with a list of pages and
questions. **Try another brief** goes back; **Use this draft** opens the
ordinary **Save** dialog, so the draft becomes your first Save.

What a draft contains:

- up to **12 pages** and **40 questions**, grouped into short pages;
- only **Single choice**, **Multiple choice**, **Likert scale** (3 to 11
  points, 5 by default), **Number** and multi-line **Open text** questions;
  no matrix, ranking, MaxDiff or conjoint;
- choice questions with 2 to 12 options, coded 1, 2, 3…, and a codebook entry
  for every question;
- readable variable names chosen by the assistant (`visit_frequency`,
  `would_recommend`): lower case, letters, digits and `_`, at most 30
  characters before any suffix. A name used twice gets `_2`, `_3`…, and a
  question without a usable name is numbered by its position (`q7`). Each
  question's **Id** is the same as its variable name;
- a hint under a question when the assistant writes one (up to 300
  characters);
- no theme settings. Your organization's house style is not applied; use
  **Theme → Use the organization's house style** afterwards.

If the brief gave the assistant nothing to work with: "The assistant made
nothing usable of this brief. Say who the respondents are and what you want
to learn from them, and try again — the attempt was still charged." with
**Back to the brief**.

On **Pro** and **Corporate**, and during the Pro trial, drafting uses a
larger model. Plus uses the standard one.

---

## Review wording

**Builder → Validation → Assistant**: "wording and response options, read by
a language model — suggestions, not rules". It sits under the engine's checks
on purpose: the engine reports facts, the assistant offers opinions.

- Before a review: "Not read yet. It looks for leading or double-barreled
  questions, unbalanced scales and missing opt-outs — the things the strict
  lint above cannot see. Costs about N of your R remaining credits."
- **Review wording** ("Reading…") reads the questionnaire on screen, unsaved
  edits included.
- Each finding shows a code, one sentence and often "Suggested: <new
  wording>". **Use this wording** applies it to the question ("Applied — save
  to keep it."). Clicking a finding opens its question.
- Nothing wrong: "Nothing to flag across N questions."
- The review describes the version it read, so it disappears as soon as you
  edit.
- At most 40 findings per review.

| Code | Meaning |
|---|---|
| `LEADING` | the wording pushes the respondent toward one answer |
| `DOUBLE_BARRELLED` | one question asks about two things, so an answer is ambiguous |
| `ASSUMES` | the question presupposes something that may not be true of the respondent |
| `MISSING_OPT_OUT` | no honest answer for someone to whom the question does not apply, who does not know, or would rather not say |
| `UNBALANCED_SCALE` | more options on one side of the scale than the other |
| `OVERLAPPING_OPTIONS` | answer options overlap, or leave a gap |
| `SCALE_MISMATCH` | the answer labels do not fit what the question asks |
| `JARGON` | a term respondents are unlikely to understand the same way |
| `SENSITIVE` | a sensitive question without a way to decline |
| `OVERLONG` | a sentence long or convoluted enough to be misread |

---

## Reword and Suggest options

In the Inspector, a question's **Question** section has:

- **Reword**, which proposes up to **three** alternative wordings, each with a
  few words on what it fixes. **Use this** replaces the
  question text. If the wording is already fine: "Nothing to change — the
  assistant would leave this wording as it is."
- **Suggest options** (single choice, multiple choice and ranking only), which
  proposes up to **12** answer options in reading order, with a one-line note.
  **Replace options** applies them ("Options you already have keep their
  codes."). A proposed label that matches an existing one (ignoring case)
  keeps that option's code, new labels get the lowest free codes, and options
  not in the proposal are removed. If nothing comes back: "The assistant
  proposed no options for this question."
- **What to fix (optional)**: a short note for either button, such as "too
  formal" or "add a don't-know option". Keep it under 300 characters.

Both buttons show "Thinking…" while they work, and are disabled until the
question has text.

---

## Flow review

On **Flows**, each flow in the list has a **review** link (tooltip "Have the
assistant read this pipeline for analysis mistakes"). It reads the flow's
**saved** version and opens a panel under the list: "Assistant · <flow> ·
whether the analysis is sound, read by a language model — suggestions, not
rules · N credits, R left", with **Close**.

- While reading: "Reading the pipeline…".
- Findings show a code, a sentence and often "Suggested: …", with the step
  they concern. There is nothing to apply; change the flow yourself.
- "Nothing to flag across N steps.", or "This flow has no steps to read yet."
- The flow must pass its structural check first. If it does not, the review
  is refused ("fix what the structural check reports first — …") and the panel
  reads "Nothing came back. The structural check has to pass first."
- Clicking **review** again closes the panel. A second read costs credits
  again.

| Code | Meaning |
|---|---|
| `WEIGHTS_UNUSED` | weights are computed but never applied |
| `WEIGHTS_INCONSISTENT` | some analyses on the data are weighted and others are not |
| `MISSING_NOT_HANDLED` | a statistic counts missing codes (refusals, don't-knows) as real values |
| `TEST_SCALE_MISMATCH` | a test or statistic does not suit the variable's scale |
| `NO_DEDUP` | duplicates are not removed, so a respondent may count twice |
| `PARTIALS_INCLUDED` | incomplete or implausibly fast responses are not filtered out |
| `SPARSE_CROSSTAB` | a crosstab on a variable with so many categories that cells will be too thin |
| `ORDER` | a step comes after one that already invalidated it (filtering after weighting, recoding after the analysis) |
| `DEAD_END` | a node's result is never used |
| `UNREPORTED` | a result reaches neither the report nor a Live tile |

See [[Analysis Flows|Studio-Flows]].

---

## Coding open answers

On a flow's canvas, **Code open answers…** (or **Code more answers…**) has the
assistant read the answers to one open-text question, propose themes and
assign each answer to one. You review and rename the scheme before anything
is coded. See [[Coding Open Answers|Studio-Open-Answer-Coding]].

---

## Plans and credits

The assistant spends **credits**. One credit is roughly 1,000 tokens of text.
Allowances are **per organization**:

| Plan | Credits per month | Credits per day | Requests per person, per hour |
|---|---|---|---|
| Free | not available | — | — |
| Plus | 8,000 | 2,000 | 30 |
| Pro | 50,000 | 8,000 | 100 |
| Corporate | 300,000 | 30,000 | 300 |
| Pro trial (unpaid) | **500, once** (does not renew) | 200 | 10 |

- The monthly allowance resets at the start of each calendar month, and the
  daily one at midnight UTC.
- A trial's 500 credits are for the organization's whole trial. When they are
  gone, the assistant stops until you subscribe.
- The requests-per-hour limit counts each person's assistant requests of all
  kinds.

**Typical costs:**

| Feature | Typical credits |
|---|---|
| **Review wording** (a questionnaire of ordinary length) | about 11 |
| **Reword**, **Suggest options** | about 2 each |
| **Draft from a brief** | about 34 on Plus, about 115 on Pro and Corporate (larger model) |
| Flow **review** | about 7 |
| **Code open answers** | depends on the number of answers |

You are charged for what the provider actually processed. Before sending,
Studio checks that your remaining allowance covers a cautious estimate of the
largest possible reply, so near the end of an allowance a request can be
refused even though its typical cost would fit. A refused request costs
nothing. A completed one is charged even if its result is empty.

Remaining credits appear in the **Validation → Assistant** hint, in the
**Draft from a brief** dialog and in the flow review's header.

---

## When the assistant is unavailable

When the assistant cannot be used, the **Reword**, **Suggest options** and
**Draft from a brief** buttons are hidden. **Validation → Assistant** says
why:

| Reason | Message |
|---|---|
| plan | "The assistant is part of Plus and above." |
| not turned on | "Off for this organization. An owner can turn it on in Settings — that also confirms questionnaire text may be sent to the model provider." |
| paused by support | "Paused for this organization. Contact support." |
| platform limit | "Temporarily unavailable. Try again later." |

### Error messages

A failed request shows a toast such as "The assistant could not review this"
(or "…could not rewrite this question", "…could not propose options",
"…could not draft this", "…could not review this flow"), followed by the
reason:

| Message | What to do |
|---|---|
| "the assistant is not included in the <plan> plan — upgrade to Plus" | upgrade |
| "the assistant is off for this organization — an owner can turn it on in Settings, which also confirms that questionnaire text may be sent to the model provider" | ask the owner |
| "the assistant is paused for this organization — contact support" | contact support |
| "the assistant is temporarily unavailable — please try again later" | try later |
| "this organization's assistant daily allowance cannot cover this request (X of Y credits used) — it resets at midnight UTC; try a smaller document if needed" | wait, or send less |
| "this organization's assistant monthly allowance cannot cover this request (X of Y credits used) — it resets next month, or support can raise it" | wait, upgrade, or contact support |
| "this organization's assistant trial allowance cannot cover this request (X of 500 credits used) — subscribe to keep using it" | subscribe |
| "the assistant is limited to N requests an hour per person — try again shortly" | wait a little |
| "this questionnaire is too long for the assistant to review in one pass" (similarly "this question is too long to send", "this brief is too long to send", "this pipeline is too large for the assistant to review in one pass") | shorten it |
| "there are no questions to review yet" / "the question has no text yet" / "this flow has no steps to review yet" | add content first |
| "the assistant's draft could not be turned into a questionnaire — nothing was saved" | try again |

---

## Good practice

- Treat findings as a second reader's notes: accept what improves the
  question, ignore the rest. The engine's checks decide validity; the
  assistant does not.
- Review wording **before** you pilot. Rewording a question mid-field changes
  what the data means.
- Use **What to fix** to steer a rewrite. "Make it neutral" or "simpler for
  teenagers" works better than a bare request.
- After **Replace options**, check the codebook: removed options disappear
  from the question, and new ones take new codes. On a multiple-choice
  question in the wide layout, each new option also gets its own 0/1
  variable, and a removed option's variable goes.
- After **Use this draft**, add your theme and read every question as a
  respondent would.
- Tell your ethics board and your respondents' consent text what you send to
  the provider, if your institution requires it.

## See also

- [[Testing Your Survey|Studio-Testing-Your-Survey]]
- [[Coding Open Answers|Studio-Open-Answer-Coding]]
- [[Analysis Flows|Studio-Flows]]
- [[Plans, Trial and Billing|Studio-Plans-and-Billing]]
- [[Organizations and Team|Studio-Organizations-and-Team]]

<!-- studio-nav -->
---

← [[Testing Your Survey|Studio-Testing-Your-Survey]] · [Studio contents](Studio-Overview#all-pages) · [[Publishing and Environments|Studio-Publishing-and-Environments]] →
