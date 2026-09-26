# Coding Open Answers

Open-ended answers are rich and unwieldy: before they can go into a table
they need a **coding scheme** — a set of themes — and a decision about which
answer belongs to which theme. This page explains how Studio does that with
a *frozen codeframe*: how to build one with the AI assistant, check and save
it, apply it in a flow, extend it later, and what that means for privacy and
reproducibility.

---

## The frozen-codeframe approach

Studio splits coding into two jobs that never mix:

1. **Building the codeframe** — once, on request. The assistant reads the
   answers, proposes themes and assigns every distinct answer to one. You read
   the result, rename what reads badly, and save it as a document of the
   project: `analysis/<variable>.codeframe.json`.
2. **Applying the codeframe** — in a flow, on every run. The **Code open
   answers** node looks each answer up in the saved codeframe. No model, no
   network, no randomness.

The consequence is the point. The same answers get the same themes on every
run; the scheme is a file a reviewer can read and disagree with; it is
versioned with every Save and travels in the research bundle; and anyone who
re-runs your study gets your numbers. An analysis that called a model at run
time could give different themes next month and could not be checked.

---

## Before you start

- **Plan:** the assistant is part of *(Plus)* and higher, and of the trial.
- **Consent:** an organization **owner** must turn the assistant on:
  Organization settings → **Integrations** → **AI assistant** → **Turn the
  assistant on**. Until then requests are refused with "the assistant is off
  for this organization — an owner can turn it on in Settings…".
- **Answers:** the open-text question must have answers in an environment
  that has been published.
- **Role:** member or higher.

> **Privacy — read this before you use it.** Building a codeframe sends your
> respondents' **open-answer texts** (and the question's wording) to the AI
> provider — currently **DeepSeek, which processes it in China**. No respondent
> id, timing or other metadata is sent, but open answers can contain anything
> a respondent chose to write, including personal information. The consent an
> owner gives in the organization settings is worded around "questionnaire
> and analysis text". **Check that your respondents' consent wording, your
> ethics approval and your data-protection obligations allow sending their
> answers to a third-party provider abroad** before you start a coding job. If
> they do not, use the [manual alternatives](#manual-alternatives).

---

## Building a codeframe with the assistant

The dialog opens from a **Code open answers** node: in its inspector, next to
**Codeframe**, click **Code open answers…** (or **Code more answers…** once the
project has a codeframe).

### 1. Choose what to code

The dialog, **Code open answers**, explains: "The assistant reads the answers,
proposes themes, and assigns every answer to one. You read the scheme before
anything is coded — and the flow node applies the saved scheme, never a model,
so the same answers code the same way every time. Costs by the size of the
job."

| Field | Meaning |
|---|---|
| **Open-text question** | every open-text question of the questionnaire, as `variable — question text`. With none: "This questionnaire has no open-text questions." |
| **Environment** | "every wave published to it" — answers from all deployments of that environment are coded |
| **Also judge sentiment** | "negative / neutral / positive, beside the theme" — adds a sentiment per answer |

Click **Start coding** (or **Cancel**).

The job is refused, before anything is spent, when "nothing has been
published to *environment* yet, so there are no answers to code" or "nobody
has written anything in *variable* yet", and when the organization's
allowance cannot cover the job's estimate (see [Credits](#credits)).

### 2. Wait for the job

Coding is a background job, not an instant answer. The dialog shows "Coding
`variable`…" and a progress line that the job updates as it goes — "The job is
queued.", then "Coded 40 of 812 answers.", "Coded 80 of 812 answers.", ….

How it works:

- The answers are reduced to **distinct** texts; each is clipped to **400
  characters**. At most **4,000** distinct answers are read in one job; with
  more, the first 4,000 in alphabetical order are coded and the rest stay
  uncoded.
- **Pass one — the scheme.** The assistant reads an even spread of up to 180
  of them and proposes **at most 24 themes**, each with a short label, a
  one-sentence definition and two or three example answers copied from the
  data. Themes are written in the language of the answers. Studio numbers the
  themes itself (1, 2, 3, …) so codes never change meaning between runs.
- **Pass two — the verdicts.** The answers are assigned to the themes in
  batches of 40. The assistant may say that no theme fits; such answers are
  left **uncoded** rather than forced into a theme. With sentiment, each
  answer also gets −1, 0 or 1 for its own tone.

**Close — it keeps running** closes the dialog; the job finishes in the
background and appears in the Flows **Run history** (as a **flow** run on
`analysis/<variable>.codeframe.json`), and its codeframe file is kept in
**Files** under `outputs/codeframe_<variable>/`.

> **Current limitation.** The dialog cannot be reopened on a finished job's
> result, and only the dialog saves a codeframe into the project. **Keep the
> dialog open until the job finishes** if you want to save the codeframe.

If the job fails, the dialog says "The job did not finish." with the reason
— for example "The assistant proposed no themes for these answers." or "The
assistant stopped: …". Credits already spent on the calls that ran are still
charged.

### 3. Read and rename

When the job completes, the dialog shows a summary — "12 themes over 790 of
812 distinct answers (164 credits). Read it, edit it, save it as a codeframe
document." — and the themes, each with its code, an editable label and its
definition.

"Rename anything that reads badly — the labels are what a table will show."
The definitions and assignments are shown as proposed; the dialog edits
labels only.

### 4. Save it

**Save codeframe** opens the ordinary Save dialog: the codeframe becomes
`analysis/<variable>.codeframe.json`, a document of the project, in a new
Save. If you opened the dialog from a node, that node's **Codeframe** is set
to the new file. **Discard** throws the proposal away (the credits are spent
either way).

A saved codeframe is checked like any document; one with themes but no
assigned answers gets the warning "This codeframe has themes but no answers
assigned to them."

---

## Applying it in a flow

Add **Code open answers** (Prepare) after your source and cleaning steps:

| Parameter | Value |
|---|---|
| **Codeframe** | choose the file from the dropdown (**— choose a codeframe —**) |
| **Theme variable** | leave empty for the codeframe's own name, `<variable>_theme` |
| **Also add sentiment** | tick only if the codeframe was built with sentiment |

The node has three outputs:

- **`data`** — the dataset plus the theme variable, labeled `Theme:
  <variable>`, whose value labels are your theme labels; with sentiment, also
  `<theme variable>_sentiment`, coded −1 / 0 / 1 = Negative / Neutral /
  Positive.
- **`table`** — one row per theme with N and % (largest first), then
  **Coded** and **Uncoded** rows. A theme's % is of the **coded** answers;
  **Coded** and **Uncoded** are shares of **everyone who answered**, so the
  table says how much of the answers the themes describe. With **Also add
  sentiment** and a codeframe built with it, each row adds **Negative %**,
  **Neutral %** and **Positive %**. Wire it into a **Report section** — it is
  the table most reports need. It counts answers, not weights: after **Apply
  weight** it stays unweighted and says so ("Weight: unweighted (the weight
  'weight' is not applied)").
- **`stat`** — the table's statistics: the variable, how many people
  answered, the number of themes, the **Coverage** ("75.0 % of the answers
  have a theme"), the **Distinct uncoded answers** — how many different
  answers a new coding job would have to read — and which model built the
  codeframe, when; with sentiment, the overall **Sentiment** ("negative 66.7
  %, neutral 0.0 %, positive 33.3 % of 3 answers") and the **Net sentiment**.
  Sentiment asked of a codeframe built without it reads "not in this
  codeframe". Connect it to a **Live tile** to watch the coverage as new
  answers arrive.

> **Note.** The **Uncoded** share used to be taken of the coded answers — one
> uncoded answer in four read 33.3 %. It is now a share of everyone who
> answered (25 %); run a flow again for the corrected table.

Answers are matched by their text (normalized for spacing and case), so the
same answer is coded the same way wherever it appears. An answer the
codeframe has never seen — typically one collected after it was built — stays
**uncoded**, and the table's **Uncoded** row says how many there are.

**Run to here** on the node previews it with the codeframe of your current
Save, as a run does.

**Using the theme variable in later nodes.** Type its name in **Theme
variable** — for example `feedback_theme`, the name the codeframe carries —
and the nodes after it offer it in their variable lists ("made by *node*"):
a **Crosstab** of themes by region, a **Filter rows** on one theme. Left
empty, the node still creates the variable under the codeframe's name, but
the pickers do not list it. The sentiment variable is not offered in the
pickers; take it further with **Export file** or **Write table**.

---

## Coding more answers later

When fieldwork continues, the **Uncoded** count grows. **Code more answers…**
starts a new job over **all** answers collected so far and proposes a **new
scheme** — themes can differ from the previous one. Saving it replaces the
variable's codeframe document with a new version (the previous one stays in
History), and the next run of your flow uses the new scheme. Compare the two
versions in [[History and Versions|Studio-History-and-Versions]] before you
save, and mention the recoding in your methods.

---

## Credits

A coding job is priced by its size and charged for the tokens actually used,
against the organization's assistant allowance (see
[[AI Assistant|Studio-AI-Assistant]] and
[[Plans, Trial and Billing|Studio-Plans-and-Billing]]). Before a job starts,
Studio checks that the allowance covers a deliberately generous estimate:

| Plan | Model used | Estimate |
|---|---|---|
| Plus | the standard model | 12 + 6 per 40 answers — about 160 credits for 1,000 answers |
| Pro, Corporate | the larger model | 47 + 22 per 40 answers — about 600 credits for 1,000 answers |

The monthly allowances are 8,000 credits on Plus, 50,000 on Pro and 300,000 on
Corporate, with daily limits of 2,000, 8,000 and 30,000; the trial has a
one-off 500 credits (200 a day). A job also counts as one assistant request
toward the per-person hourly limit (30 / 100 / 300 by plan, 10 on the trial).
When the allowance cannot cover a job you see, for example, "this
organization's assistant monthly allowance cannot cover this request (7,900 of
8,000 credits used) — it resets next month, or support can raise it".

---

## Reproducibility

- The codeframe is a document of the Save: it is in every research bundle
  (`analysis/<variable>.codeframe.json`), and the flow script loads it from
  there — re-running the bundle codes the same answers the same way, with no
  model and no account.
- The codeframe records which model built it and when (`model`, `built_at`)
  and how many distinct answers it read (`source_rows`). Its fields:
  `variable`, `into` (the theme variable's name), `themes` (code, label,
  definition, examples), `assignments` (a fingerprint of each answer's text →
  theme code) and, with sentiment, `sentiment`.
- The **Documents** tab of a Save in History downloads it as `.json`.

---

## Manual alternatives

If sending answers to a provider is not acceptable, or you prefer human
coding:

- **Code outside Studio.** Export the responses (**Data → Export**, see
  [[Data Exports|Studio-Data-Exports]]), code the open answers in your own
  tool, and analyze the coded file there.
- **Ask a closed question as well.** A single-choice follow-up ("Which of
  these comes closest?") gives a coded variable you can tabulate and, with
  **Recode**, regroup.
- **Keep the verbatims in the report.** For a small study, quoting answers in
  a section's text may serve better than any coding.

## See also

- [[Node Reference|Studio-Node-Reference]] — [Code open answers](Studio-Node-Reference#code-open-answers)
- [[AI Assistant|Studio-AI-Assistant]]
- [[Security and Privacy|Studio-Security-and-Privacy]]
- [[Analysis Flows|Studio-Flows]]
- [[Reproducibility: Code, Bundles and Citation|Studio-Reproducibility]]

<!-- studio-nav -->
---

← [[Cleaning and Weighting Data|Studio-Cleaning-and-Weighting]] · [Studio contents](Studio-Overview#all-pages) · [[Reports|Studio-Reports]] →
