# Projects

A **project** is one study: its questionnaire, its analysis flows, its
settings, its response database, its deployments and its complete version
history. This page covers what a project is made of, how Saves and drafts work
at a glance, the Projects list, creating a project (blank, from the example
study, from a template or from your organization's library) and what Studio
sets up for you when it does.

---

## What a project is made of

A project is a handful of **documents** plus a **database**. You edit the
documents through the screens; they matter because they are what gets
versioned, downloaded and reproduced.

| Document | What it holds | Edited in |
|---|---|---|
| `survey/questionnaire.json` | the questionnaire: pages, blocks, questions, logic, quotas, codebook, theme, scripts | **Builder** |
| `flows/<name>.flow.json` | one analysis flow each: nodes, connections, parameters, live tiles | **Flows** |
| `studio/settings.json` | environments, runtime, connectors, pinned insights, report house style, study and citation metadata | **Settings**, **Data**, **Flows** |
| `analysis/<name>.codeframe.json` | a coding scheme (codeframe) for one open-text question | **Flows** — see [[Coding Open Answers\|Studio-Open-Answer-Coding]] |

The Builder's **Source** tab shows the questionnaire document as JSON and lets
you edit it directly — see [The Source tab](Studio-Builder-Overview#the-source-tab).

Alongside the documents the project owns:

- **a response database** — the `responses` table (one row per interview),
  `quota_counters` (how full each quota cell is), `survey_meta` (the title
  and variable dictionary of each published survey) and any table your flows
  write;
- **files** — media and data you upload, and the outputs of every flow run
  ([[Files|Studio-Files]]);
- **deployments** — each published version of the survey, per environment
  ([[Publishing and Environments|Studio-Publishing-and-Environments]]).

---

## Saves and drafts

**Save** creates a numbered version of the **whole project** (`#17`): every
changed document gets a new version, the engine validates it and generates
its Python (`questionnaire.py`, `<flow>.py`), and the set is stamped with a
number, an author, a message and a validation state. A Save message is
optional (up to 240 characters); when you leave it empty Studio writes one,
such as `Update questionnaire` or `Update questionnaire, tables`.

The **Save badge** next to the project name in the topbar shows the current
state from every tab. Click it to open that Save in **History**.

| Badge | Meaning |
|---|---|
| `● valid #17` | Save 17 is clean — publishable and runnable |
| `● warnings #17` | saved; the engine has remarks — publishable after you confirm. The remarks can include findings the engine grades as errors (an empty page, a design that cannot be estimated); they do not block publishing, but the confirmation names them |
| `● errors #17` | saved but broken — cannot be published or previewed |
| `● checking #17` | the Save's validation has not reported yet |
| `saving…` | a Save is in progress |
| `unsaved` | the project has never been saved |

The dot is green, amber or red for valid, warnings and errors.

**Drafts.** Between Saves your edits are autosaved as a private **draft**,
1.5 seconds after your last change, so a closed tab costs you nothing. A draft
is not validated, not published and not visible to colleagues — except as the
live document a colleague follows while you hold the edit lock. See
[Saving](Studio-Builder-Overview#saving) and
[Drafts and autosave](Studio-Builder-Overview#drafts-and-autosave).

Publishing pins a Save, flows run against a Save, and any Save can be restored
or downloaded as a research bundle. The full story is in
[[History and Versions|Studio-History-and-Versions]].

---

## The Projects list

The organization's **Projects** tab lists every study in the workspace.

```
┌ Projects   Acme Research                                        [+ New project] ┐
│ [Search projects by name…           ]  [Sort: Last opened ▾]                     │
│ ┌──────────────────────────────────────────────────────────────────────────────┐ │
│ │ Name                        Version  Status      Responses · 14d  Updated    │ │
│ │ Employee Pulse 2026 Q1      #17      ● valid     ▁▂▅▇▆  247       6/4/2026   │ │
│ │ Brand tracker (pilot)       #3       ● warnings  ▁▁▂▁▃   31       5/28/2026  │ │
│ └──────────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────────┘
```

| Column | What it shows |
|---|---|
| **Name** | the project's name; click the row to open the project on its **Builder** tab |
| **Version** | the number of the latest Save (`#17`), or `unsaved` |
| **Status** | a validation label: **valid**, **warnings**, **error** or **unsaved** |
| **Responses · 14d** | total responses collected, with a sparkline of the last 14 days (shown for the first 20 projects) |
| **Updated** | a date for the project |

> **Note.** **Status** and **Updated** are a quick guide, not a live record:
> they are not always current for projects you have not saved in this browser
> session. For the authoritative state, open the project and read the
> [Save badge](#saves-and-drafts) or **History**.

- **Search** — the box (placeholder `Search projects by name…`) matches the
  project's name or its slug. With no match you see **No matching projects**
  and a **Clear the search** button.
- **Sort** — **Sort: Last opened** (the projects you opened most recently in
  *this browser* first), **Sort: Name** (A–Z) or **Sort: Date created**
  (newest first).
- **Empty organization** — **No projects yet** — "Each project is a
  questionnaire, its flows and its own response database. Create it, preview
  it as a respondent, then Save and deploy." — with two buttons: **New
  project** and **Start from the example study**. For a member (not an owner
  or admin) both are disabled, with the line "Only owners and admins can
  create projects — ask one to set it up."

The workspace chip in the topbar (organization / project name) also lists up to
ten projects, plus **All projects** and **New project**. Switching project from
there keeps you on the same tab. **New project** in the chip is disabled in the
same cases as the button on the list: at your plan's project cap, and for
members.

### Project caps

| Plan | Projects per organization |
|---|---|
| Free | 2 |
| Plus | 10 |
| Pro, Corporate | unlimited |

At the cap every **New project** button — on the list, in the workspace chip,
**Start from the example study** on an empty list, and the **New project**
buttons on the **Library** tab (on each template card and on each saved
questionnaire) — is disabled; hovering says "Your plan allows 2 projects —
upgrade to add more" (10 on Plus). The list also shows, for example on Free: "You've reached the **2-project**
limit on the free plan. **Upgrade your plan** to add more." See
[[Plans, Trial and Billing|Studio-Plans-and-Billing]].

> **Plan.** On the Free plan each project also takes at most **1,000
> completed responses**, counted over all of its environments together.
> Screen-outs and partial responses do not count toward it, and neither do the
> sample responses of the [example study](#the-example-study).

---

## Creating a project

> **Plan and role.** Only **owners** and **admins** can create projects. For a
> member, every **New project** button — on the **Projects** list, in the
> workspace chip and on the **Library** tab — is disabled ("Only owners and
> admins can create projects" when you hover it), and the **Library** tab adds
> under its templates: "Only owners and admins can create projects — ask one
> to set it up." Members can open, edit and Save every project in the
> organization.

1. On **Projects**, click **New project** (or **Start from the example study**
   on an empty list, or **New project** on a template or saved questionnaire in
   the organization's [[Library|Studio-Question-Bank-and-Library]]).
2. Type a **Name**. Under it Studio shows the address the project will have:
   "Its address will be `/brand-awareness-study-2026`".
3. Under **Start from**, choose **Blank project** or **Template** (see below).
4. Click **Create**. The button reads **Creating…** while Studio sets the
   project up, then the project opens on its **Builder** tab. The toast says
   **Project brand-awareness-study-2026 created** (for the example: **Example
   study created — open the Builder to explore it**).

`Enter` in the Name field also creates. **Create** stays disabled until there
is a name and, if you picked **Template**, a template.

### The New project dialog

```
┌ New project ──────────────────────────────────────────── ✕ ┐
│ Name                                                       │
│ [Brand Awareness Study 2026                             ]  │
│ Its address will be /brand-awareness-study-2026            │
│                                                            │
│ Start from                                                 │
│ ┌────────────────────────────────────────────────────────┐ │
│ │ ○ Blank project                                        │ │
│ │   Start with one placeholder question                  │ │
│ ├────────────────────────────────────────────────────────┤ │
│ │ ● Template                                             │ │
│ │   [Course evaluation                               ▾]  │ │
│ │   End-of-course feedback: the course, the teaching, …  │ │
│ └────────────────────────────────────────────────────────┘ │
│                                        [Cancel] [Create →] │
└────────────────────────────────────────────────────────────┘
```

- **Blank project** — "Start with one placeholder question".
- **Template** — "Start with a pre-built questionnaire". Selecting it shows a
  picker (**Choose a template** until you pick one). The picker opens a list
  with a search box (`Search 13 templates…` — the count includes the example
  study and anything your organization saved) and, per row, the name, its size
  (`8 pages · 12 questions`) and a one-line description. If nothing matches:
  "Nothing matches “…”." When your organization has saved questionnaires, the
  list has two headings: **Templates** and **Your organization's library**.
- Picking a template while the **Name** field is empty (or still holds the name
  of the previous pick) fills in the template's name; once you type a name of
  your own, changing the template leaves it alone.
- Keyboard: `↓` opens the list, `↑`/`↓` move through it, `Esc` closes the list
  (a second `Esc` closes the dialog).

### The project's slug

The **slug** is the project's permanent address in Studio
(`studio.siamang.org/<org>/projects/<slug>`). It is derived from the name and
**cannot be changed later** — not even by renaming the project.

How the name becomes a slug:

1. The name is spelled in Latin letters: Cyrillic (Russian, Ukrainian,
   Belarusian, Kazakh, Serbian, Macedonian) and Greek letters are
   transliterated, and accented Latin letters lose their accents (`é` → `e`,
   `ß` → `ss`). Characters with no Latin spelling (Chinese, Japanese, Arabic,
   Hebrew, …) are dropped.
2. It is lower-cased, every run of characters other than `a–z` and `0–9`
   becomes a single hyphen, and hyphens are trimmed from the ends.
3. A slug longer than 64 characters is cut to 64, at a word break when there
   is one near the end.
4. A name with nothing left to spell (only CJK characters, or only
   punctuation) becomes `project`; one or two characters get `-project`
   added.
5. If the organization already has a project with that slug, `-2`, `-3`, … is
   added.

| Name | Address |
|---|---|
| `Employee Pulse 2026 Q1` | `/employee-pulse-2026-q1` |
| `Опрос удовлетворённости` | `/opros-udovletvorennosti` |
| `Щедрий вечір` | `/shchedriy-vechir` |
| `Café Größe` | `/cafe-grosse` |
| `Q1` | `/q1-project` |
| `調査` | `/project` |
| a second `Опрос` | `/opros-2` |

The dialog shows the result under the name ("Its address will be …") before
you create anything, so what you see there is the address the project gets.
The slug is always 3 to 64 characters of lower-case letters, digits and
hyphens, starting and ending with a letter or digit. You can rename the
project to anything afterwards; the slug stays.

### Blank project

One page (`page1`) holding one placeholder question, and default settings.
The question is an optional **Single choice** called "New question", with the
options `1` Option 1 and `2` Option 2, Id and variable `q1`, and its codebook
entry. Rewrite it into your first question or delete it, then add the rest —
see [[The Builder|Studio-Builder-Overview]].

The placeholder is there so that the new project checks clean: a page with
nothing on it is an error in the engine's check (`EMPTY_PAGE`). If you delete
the question and leave the page empty, that finding comes back until you add
a question or a Body.

### The example study

**Example study** is the first entry in the template list ("the full Digital
Life & Wellbeing study — questionnaire, a flow and sample responses"). It is
the fastest way to see what Studio does with a real study. The dialog suggests
the name `Digital Life & Wellbeing (example)`; the questionnaire keeps its own
title, *Digital Life & Wellbeing 2026*.

What you get:

- **A 15-page questionnaire**: an introduction page, consent (with a screen-out
  for people who decline), an age screener (under-16s are screened out), about
  you, work (a work-detail page shown only to people in work), devices, apps and
  media, screen time, how you feel, a closing page, a redirect page for people
  who agree to a follow-up, and a thank-you page.
- **22 questions** using every question type except MaxDiff and conjoint:
  single choice as radio buttons, dropdown and buttons; multiple choice in both
  layouts, with an exclusive "None of these"; Likert scales (one with N/A);
  numbers as an input and as sliders; open text; a five-statement matrix; and a
  ranking.
- **Logic** at page, question, block and option level, **randomized** blocks,
  options and block items, and a script that shuffles one question's options.
- **Three quotas** on age group (400 each).
- **A codebook** with declared missing values: gender `99` = Prefer not to
  say (a refusal) and, on the Likert scale that offers N/A, `-1` = Not
  applicable — the code the survey stores when a respondent picks **Not
  applicable**.
- **Two flows**: *Clean raw responses* (deduplicate, drop speeders under 120
  seconds and partials, write a `clean_responses` table, a live tile) and *Key
  tables* (a frequency table, a crosstab of life satisfaction by age group, a
  bar chart and a saved report).
- **300 synthetic responses** already in the database, so **Data**, **Live**
  and **Flows** have something to show before any fieldwork. About 8 % are
  partials and about 4 % are speeders, so the cleaning flow has real work to
  do. They are tagged with the survey id `sample-data`, and they never count
  toward a response cap: on the Free plan the project still takes 1,000
  completed responses from real respondents.
- Four pinned insights on the **Data** tab.

### Built-in templates

Twelve complete, publishable questionnaires. All of them validate cleanly as
they are. Most start with a consent page (Yes/No buttons, with a screen-out
page for people who answer No) and end with a thank-you page; rename the
brands, the course or the product and go.

| Template | Description | Pages · questions · variables |
|---|---|---|
| **Brand awareness tracker** | Awareness (aided and unaided), consideration, usage, brand image, NPS and demographics — the classic tracker, ready to rename the brands. | 8 · 12 · 18 |
| **Employee engagement pulse** | Engagement, manager, workload and eNPS in five minutes, with the group cuts kept to ten people or more. | 8 · 8 · 15 |
| **Course evaluation** | End-of-course feedback: the course, the teaching, an overall rating and two open questions. | 6 · 8 · 15 |
| **Customer satisfaction (CSAT)** | Transactional feedback right after a support contact: the channel, satisfaction, effort, recommendation and the demographics to cut by. | 7 · 11 · 11 |
| **Product feedback** | How often the product is used, satisfaction with each part of it, the one missing capability and a price that would feel fair. | 7 · 7 · 11 |
| **Website experience (UX)** | What the visitor came to do, whether they managed it, a four-item usability scale and the blocker in their own words. | 5 · 6 · 9 |
| **Event feedback** | Overall rating, the program, the practical side and whether they would come back next year. | 7 · 6 · 11 |
| **Concept test** | One concept on its own page, then purchase intent, how the idea is judged, two price points and demographics. | 6 · 8 · 11 |
| **Module evaluation** | The module as a unit of study: intended outcomes, prior knowledge, real workload in hours and how it was assessed. | 7 · 7 · 12 |
| **Health and wellbeing check** | Self-rated health with a refusal code, a five-item wellbeing scale, activity and sleep — with the consent wording a health survey needs. | 7 · 9 · 13 |
| **Pilot study** | The shape an ethics committee expects: information sheet, two-part consent, an eligibility screener, a short instrument and a debrief page. | 7 · 4 · 13 |
| **Exit interview** | Why someone is leaving, what would have kept them, and whether they would come back or recommend the place. | 7 · 8 · 12 |

The new questionnaire takes the project's name as its title. The same list,
with a **New project** button on each card, is on the organization's
**Library** tab.

### From your organization's library

Questionnaires your team saved with **Library → Save questionnaire as
template…** in the Builder appear in the same picker under **Your
organization's library** (with their description, or "a questionnaire from
your organization's library"). The new project gets a copy, retitled with the
project's name; later changes to the library item do not reach it.

> **Plan.** *Saving* to the organization's library is *(Plus)*. Starting a
> project from a questionnaire that is already in the library works on every
> plan. See [[Question Bank, Templates and Library|Studio-Question-Bank-and-Library]].

---

## What gets created

Creating a project sets up, in one step:

1. **A response database** for the project.
2. **Save #1**, with a message that says where it came from:

   | Started from | Save #1 message |
   |---|---|
   | Blank project | `Initialize empty project` |
   | Example study | `Initialize example study (Digital Life & Wellbeing)` |
   | A built-in template | `Initialize from template “Course evaluation”` |
   | A library questionnaire | `Initialize from library questionnaire “<name>”` |

3. **Your organization's survey house style** — logo, colors, typeface and the
   other look settings an owner set for the organization — copied into the new
   questionnaire's theme. It fills only what the starting questionnaire does
   not set itself, and it is a copy: changing the house style later does not
   touch existing projects. See [[Theme and Branding|Studio-Theme-and-Branding]].
4. **Two environments**: `pilot` with a cap of **50** responses and `main`
   with a cap of **1,200** — counted in completed interviews, so screen-outs
   and partial responses do not use them up. See
   [[Publishing and Environments|Studio-Publishing-and-Environments]].
5. For the example study only: the two flows, the 300 sample responses and the
   pinned insights described above.

A **blank** project, like the example study and the built-in templates, starts
at `● valid #1`: its placeholder question keeps the engine's check clean.

---

## The project tabs

Every project has nine tabs:

| Tab | What it is for | Page |
|---|---|---|
| **Builder** | the questionnaire: pages, questions, codebook, logic, theme | [[The Builder\|Studio-Builder-Overview]] |
| **Distribute** | publishing, environments, links, QR codes, invitations | [[Publishing and Environments\|Studio-Publishing-and-Environments]] |
| **Data** | the response database, insights, exports | [[Responses and the Data Tab\|Studio-Responses-and-Data]] |
| **Flows** | analysis flows | [[Analysis Flows\|Studio-Flows]] |
| **Live** | the fieldwork monitor and live tiles | [[Live Monitoring\|Studio-Live-Monitoring]] |
| **Reports** | the reports your flows produced | [[Reports\|Studio-Reports]] |
| **History** | every Save: diffs, restore, bundles, Methods | [[History and Versions\|Studio-History-and-Versions]] |
| **Files** | uploads and run outputs | [[Files\|Studio-Files]] |
| **Settings** | name, citation, runtime, environments, secrets, deletion | [[Project Settings\|Studio-Project-Settings]] |

**Distribute** shows the number of live environments and **Flows** the number
of flows next to their names. On screens narrower than 1280 pixels the tabs
after **Reports** move into a **More** menu; below 1024 pixels, the tabs after
**Flows**.

---

## Renaming and deleting

Both are in **Settings** and are for **owners and admins** only:

- **Settings → General → Project name**, then **Save changes** — 1 to 120
  characters. The slug does not change. A member sees **Save changes**
  disabled, with the note "Only owners and admins can rename a project."
- **Settings → Danger Zone → Delete project** — you type the slug to confirm.
  Deleting removes the questionnaire, the flows, every Save, all deployments
  and every response, immediately and permanently; live survey links stop
  accepting answers. Download a research bundle and export your data first.
  A member sees **Delete project** disabled ("Only owners and admins can do
  this"), with the note "Only owners and admins can delete a project."

Details in [[Project Settings|Studio-Project-Settings]].

---

## Practical conventions

- **One study per project.** Waves of the same tracker belong in one project,
  in separate environments or successive deployments, so the codebook and the
  history stay together.
- **Name projects for humans** (`Employee Pulse 2026 Q1`). A name in Cyrillic
  or Greek gets a readable transliterated address; a name written only in a
  script with no Latin spelling (Chinese, Japanese, Arabic, …) gets the
  address `/project`, so add a few Latin letters or digits if you want the
  address to say what the study is.
- **Save early, Save often, with messages.** Saves are cheap, and the message
  is what makes History readable six months later.
- **Start from the example study once.** It shows every part of the product
  working together on data you can safely break.

## See also

- [[The Builder|Studio-Builder-Overview]]
- [[History and Versions|Studio-History-and-Versions]]
- [[Project Settings|Studio-Project-Settings]]
- [[Question Bank, Templates and Library|Studio-Question-Bank-and-Library]]
- [[Key Concepts|Studio-Key-Concepts]]

<!-- studio-nav -->
---

← [[Organizations and Team|Studio-Organizations-and-Team]] · [Studio contents](Studio-Overview#all-pages) · [[Project Settings|Studio-Project-Settings]] →
