# History and Versions

Studio versions your project without asking you to learn version control.
Every **Save** is a numbered, validated state of the whole project —
questionnaire, flows and settings — and history is never rewritten. This page
covers saving, the **History** tab, comparing and restoring versions, rolling
back the survey in the field, the Methods draft, pre-registration and deposits
to Zenodo or OSF.

---

## What a Save is

A Save is one numbered version (`#17`) of **every document in the project**.
When you save:

1. Every document you changed gets a new version. Documents you did not change
   keep their current version.
2. The engine validates the complete project — the questionnaire first, then
   every flow against the codebook being saved — and generates the Python for
   each document (`questionnaire.py`, `<flow>.py`). The code is stored **with
   that version**.
3. The whole set is stamped with the next sequence number, your name, a message
   and a validation state.

Publishing, flow runs, connector runs and research bundles always use a
specific Save, never your unsaved edits. That is what makes "which version was
in the field?" answerable months later.

### Validation states

| State | Meaning |
|---|---|
| **valid** | the engine found nothing to report |
| **warnings** | saved; the engine has remarks — still publishable. The list may include issues graded as errors: errors the engine's lint found in the questionnaire, and a flow that failed the engine check (see below) |
| **error** | saved, but the questionnaire did not validate (or the second check below found a package outside the allowlist) — this Save cannot be published, previewed or deposited |
| **checking** | the verdict is not in yet |

The topbar Save badge shows the current Save's state as **valid**, **warnings**
or **errors** with its number; click it to open that Save in History.

Only the state **error** stops a Save from being published. Two kinds of
errors leave a Save at **warnings** instead:

- **A flow that fails the engine check.** It is saved without generated code
  and cannot run until you fix it and save again; the questionnaire can still
  be published, and every other flow, Run all and previews still work. Its row
  on the **Flows** screen carries a red **errors** pill. See
  [[Analysis Flows|Studio-Flows]].
- **Errors the engine's lint finds in the questionnaire** (for example a
  question page with nothing on it). They do not stop a Save or publishing,
  but publishing from **Distribute** asks for a confirmation first ("Publish
  #*N* with errors" → **Publish anyway**). Fix them before fieldwork; they are
  listed in **Builder → Validation**.

> **Note.** A questionnaire that fails validation is still saved (with state
> **error**) so you never lose work. A document that is malformed — not valid
> JSON of the right shape — is refused and nothing is saved.

### The second check after a Save

A few seconds after each Save, Studio re-checks it in the same sandbox that
runs your flows and adds what only that sandbox can see:

- a runtime package outside the curated allowlist turns the Save to **error**
  with "packages not available in the sandbox: *name*. Use a package from the
  curated allowlist, or request it be added." (see
  [Runtime](Studio-Project-Settings#runtime));
- a connector whose target needs a higher plan adds the warning
  `CONNECTOR_PLAN` — "connector '*name*' (*target*) needs the '*plan*' plan to
  run".

Because of this, a Save's state can change shortly after you save. Reload the
page to see the updated verdict.

The **Python version** under **Settings → Runtime** is checked by the Save
itself: anything other than 3.11 adds the warning `RUNTIME_PYTHON` at once
(see [Runtime](Studio-Project-Settings#runtime)).

---

## The Save dialog

Open it with:

- **Save** / **Save changes** in the Builder or on a flow's canvas;
- `Ctrl/Cmd + S` in the Builder or on a flow's canvas (see
  [[Keyboard Shortcuts|Studio-Keyboard-Shortcuts]]);
- **Save now** on the History tab.

```
┌ Save ─────────────────────────────────────────────── ✕ ┐
│ A new version of questionnaire.json and a Save you can  │
│ deploy, preview or restore later.                       │
│                                                         │
│ Message                                      optional   │
│ [ Add charging-access question                      ]   │
│                                                         │
│                                      Cancel   ✓ Save    │
└─────────────────────────────────────────────────────────┘
```

- The text names the documents that will get a new version. With nothing
  changed it says "No document changed — this Save re-pins the current versions
  and re-validates them with the current engine." That is useful to re-check a
  project against a newer engine or to mark a milestone.
- **Message** is optional, up to **240 characters**. Press `Enter` to save.
- After saving you see one of these, the first that applies:

  | Toast | When |
  |---|---|
  | "Saved #*N* with errors — see History" | the Save's state is **error** |
  | "Saved #*N* — flow *name* has errors and cannot run until fixed" ("… — flows *a*, *b* have errors …" for several) | a flow failed the engine check |
  | "Saved #*N* — the questionnaire has 1 error (see Builder → Validation)" ("… has *N* errors …") | the engine's lint found errors in the questionnaire |
  | "Saved #*N* (warnings)" | other remarks |
  | "Saved #*N*" | nothing to report |

Write real messages: History becomes the project's changelog.

### Automatic messages

When you leave **Message** empty, Studio writes one from what changed:
"Update questionnaire", "Update settings", "Update *flow-name*", "Update
codeframe *name*" (joined with commas when several changed), or "Save (no
changes)". Actions that save on their own use fixed messages:

| Action | Message |
|---|---|
| Creating a project | "Initialize empty project", "Initialize example study (Digital Life & Wellbeing)", "Initialize from template “*name*”", "Initialize from library questionnaire “*name*”" |
| Settings → General → **Save study metadata** | "Update study metadata" |
| Settings → Runtime → **Save runtime** | "Update runtime" |
| Settings → Reports | "Update report settings", "Apply the report house style to *N* flows" |
| Adding a connector | "Add connector *name*" |
| Flows → **Rename…** / **Duplicate…** / **Delete…** (or the flow editor's **More** menu) | "Rename flow *a* to *b*", "Duplicate flow *a* as *b*", "Delete flow *a*" |
| Generating access codes | "Generate *N* access codes" |
| Importing access codes (**Import CSV**) | "Import *N* access codes" |
| Turning access codes off | "Turn off access codes" |
| Captcha on / off | "Turn on the captcha" / "Turn off the captcha" |
| Panel setup | "Configure panel" |
| Restoring | "Restore version #*N*" |

History marks the messages Studio writes for an empty **Message** with
**auto**; the fixed messages in the table above are not marked. A Save that adds access codes
(generated or imported) is also recorded in the project's Activity as
`access_codes.generate`, with the number of codes added (see
[Activity](Studio-Project-Settings#activity)).

### When a Save is refused

| You see | Why | What to do |
|---|---|---|
| "Save failed." with a plan message such as "Plan 'free' allows up to 3 analysis flows per project; this Save would have 4 — delete one or upgrade." | the Save would add a flow or access codes beyond your plan's cap | delete a flow or upgrade; a Save that keeps or reduces the count always goes through |
| "Save failed." naming the document and the problem (for example a flow named `survey`, or a connector with the same name as a flow: "task name '*x*' is already in use") | the document is malformed or names collide | fix the named item and save again |
| "Save failed. questionnaire: pages/0/items/0/text: must not be empty (page 'page1', question 'q1')" | a questionnaire field that must be filled in is empty, or has the wrong shape; the message gives the field's path, then the page (by name), any block ("block 2") and the question (by id or variable). Other forms: "… needs at least 1 entry", "… 'Nope' is not a question type", "questionnaire: title: must not be empty" | fill in or correct that field (the same text appears as the **DOCUMENT** issue of **Source → Check** in the Builder) |
| "Save failed. *Name* has this open for editing — yours will save once they are done." | a colleague holds the edit lock on a flow this Save would delete or rename | wait until they are done, or ask them; see [One editor per document](Studio-Collaboration#one-editor-per-document) |
| The dialog turns into a conflict notice | a colleague saved since you started | see [Save conflicts](Studio-Collaboration#save-conflicts) |

Flow and access-code caps per plan are in
[[Limits and Quotas at a Glance|Studio-Limits-Reference]].

---

## Drafts and autosave

Between Saves, your edits are autosaved as a **draft** — private to you and to
that document — about 1.5 seconds after you stop typing. A draft is not
validated, not published and not in History. Saving (or **Discard changes** in
the Builder's **More** menu) clears it. If you close the tab with unsaved
edits, the browser asks before leaving.

In the Builder the ordinary sync messages appear in the version chip under the
title (**Version 17 · edited**); anything that needs your attention appears as
a band above the tabs. On a flow they appear in the **More** menu, with a dot
on the button when something needs attention.

| Message | Meaning |
|---|---|
| "Draft waiting to sync…" / "Syncing draft…" | your latest edits are on their way to the server |
| "Draft synced — not yet saved as a version." | the draft is safe; it is not a Save yet |
| "Draft kept in this tab — save a version before closing it." | a brand-new flow: its draft exists only in this browser tab until the first Save |
| "Draft restored — save a version when ready." | Studio reopened edits you left unsaved (toast: "Unsaved edits restored — Save to keep them as a version") |
| "An unsaved draft from an older version was not restored — the document has been saved since." | your old draft was built on a version that is no longer current, so it was set aside rather than rolling the document back |
| "A newer version exists. Review the conflict when saving." | someone saved this document after your draft began |
| "Draft sync failed. Your edits remain in this tab. Retry before closing it." | click **Retry draft sync**; do not close the tab until it succeeds |
| "Could not check for a saved draft. Your current edits are kept in this tab." | the server could not be asked; your screen is unaffected |
| "Could not clear the previous draft. Reopen the editor to review it before publishing." | a Save or discard succeeded but the old draft stayed behind |

---

## The History list

**History** lists every Save, newest first.

```
History  every Save · brand-2026                                      [ Save now ]

 Save                  Message                   Changed        Validation         When
 #18 current           Reworded the screener     questionnaire  ● valid   [main]   Sep 23, 2026  ↓
 #17 pre-registered    Update settings · auto    —              ● warnings         Sep 21, 2026  ↓
 #16                   Add charging question     —              ● error            Sep 20, 2026  ↓
```

| Column | Shows |
|---|---|
| **Save** | the number, plus **current** on the newest Save and **pre-registered** on the registered one |
| **Message** | your message, or Studio's automatic one marked **auto** |
| **Changed** | for Saves made during your current session, which documents changed (questionnaire, settings, flow names); otherwise — |
| **Validation** | the state, and a green pill listing the environments where this Save is **live** right now (hover: "Live on") |
| **When** | the date of the Save |
| ↓ | downloads that Save's `questionnaire.py` (not available for a Save with errors) |

Studio loads the **latest 100 Saves** and shows 20 at a time; **Show more (*N*
older)** reveals the next 20.

> **Current limitation.** Saves older than the latest 100 are kept but do not
> appear in History, and opening one by its address shows "Save #*N* not
> found". Download bundles of milestone Saves while they are within the latest
> 100.

With no Saves yet the tab says **No Saves yet** — "Save the project from the
Builder to create the first version." — with **Open the Builder**.

**To open a Save**, click its row (or focus it and press `Enter`), click the
Save badge in the topbar for the current Save, or go to
`…/<project>/history/<number>`.

---

## One Save

```
Save #12  [pre-registered]                  [← All Saves] [More ▾] [Deploy] [Restore]
Reworded the screener · Sep 20, 2026 · engine 1.8.0

● valid      2 changed     3 documents     7 pages
validation

[ Changes ]  [ Validation 4 ]  [ Documents ]
```

- **Header**: `Save #N`, with **current** and/or **pre-registered** pills; below
  it the message (with "(auto)" for automatic ones), the date and the engine
  version that validated it.
- **Stats**: validation state, changed documents, number of documents, and the
  questionnaire's number of pages.
- **Deposited:** — if the Save was deposited, a bar lists each deposit, for
  example **Zenodo · published** with its DOI link, **Zenodo sandbox · draft**,
  or **OSF · published** with the file link, and "with data" when the responses
  were included.

### Buttons

| Button | What it does |
|---|---|
| **All Saves** | back to the list |
| **More ▾** → **Methods** | a draft Methods section from this Save ([below](#methods-draft)) |
| **More ▾** → **Deposit** | send this Save's research bundle to Zenodo or OSF ([below](#depositing-to-zenodo-or-osf)) |
| **More ▾** → **Pre-register** / **Pre-registered** | tag this Save as the pre-registration, or remove the tag ([below](#pre-registration)) |
| **More ▾** → **Preview** | build a preview of this version ([below](#roll-back-the-survey-in-the-field)) |
| **More ▾** → **Download a bundle**: **Code & documents** | the research bundle: questionnaire.py, JSON documents, flows, README |
| **More ▾** → **With the responses so far** | "plus data/: the responses (latest), the tables and uploads the flows read" — the same bundle plus `data/responses.csv` (the latest responses), the project tables the flows read and the files uploaded under **Files** that they name |
| **More ▾** → **questionnaire.py only** | just the generated questionnaire |
| **Deploy** | publish this version to an environment |
| **Restore** | make this version current again (not shown on the current Save) |

**Deposit**, **Pre-register**, **Preview** and **Deploy** are unavailable for a
Save with errors ("A Save with errors cannot be deployed"). Bundles download
as `<project-slug>-s<N>.zip`, or `<project-slug>-s<N>-data.zip` with responses.
A bundle with responses is limited to **100,000 responses**; beyond that the
download fails with "This table exceeds the synchronous export limit of
100,000 rows." The responses in a bundle are laid out as a flow reads them —
one column per variable (responses collected by an earlier version of the
survey page included, read in today's layout), plus fieldwork columns such as
`duration_s` — but the survey link's parameters (`url_*` columns, such as
panel ids) are left out of every data file, the responses and the project
tables alike, unless a flow reads them, and the invitation token (`url_inv`)
is never included. What is inside a bundle is described in
[[Reproducibility|Studio-Reproducibility]].

### Changes tab

What changed, as a **line-by-line comparison of the documents' JSON**. Each
document is shown in a normalized form (keys sorted, two-space indentation),
so the comparison shows only real changes. Added lines are green, removed lines
red, and `@@` lines mark where a changed region starts.

- **Compare with** chooses the Save to compare against: **previous Save
  (#*N−1*)** by default, or any other Save in the list (the pre-registered one
  is marked "(pre-registered)"). The line next to it says how many documents
  differ, for example "2 documents differ between #12 and #17".
- Each changed document gets its own section headed by its path, for example
  `survey/questionnaire.json` or `flows/tables.flow.json`.
- With nothing to show you see "First Save — every document is new.", "No
  document differs between #*A* and #*B*." or "No document changed in this Save
  (versions re-pinned)."

> **Tip.** Question ids, variable names and option labels appear as they are
> in the document, so searching the page (`Ctrl/Cmd + F`) for a question id is
> the quickest way to find its change.

### Validation tab

The engine's issues for this Save, with a count on the tab. Each line shows a
colored dot for its severity, the issue code, the message and where it is (the
document and, for the questionnaire, the location). A clean Save says "This
Save validated without issues."

### Documents tab

Every document in the Save — `questionnaire`, `settings`, each flow by name,
and any codeframe by path — with a **changed** pill where applicable.

- **.json** downloads the document exactly as it was at this Save.
- **.py** downloads the code the engine generated for it at this Save (the
  questionnaire and flows; settings have no code).

---

## Restore an earlier version

**Restore** makes an older Save the current state again.

```
┌ Restore version #12 ──────────────────────────────────── ✕ ┐
│ Make #12 the current version? History is never rewritten —  │
│ this creates a new Save with the documents of #12.          │
│                                        Cancel   Restore     │
└─────────────────────────────────────────────────────────────┘
```

What happens:

- A **new** Save is created on top of history with the message "Restore version
  #12"; the toast says "Restored version #12 as #20". Nothing is overwritten —
  #13 to #19 stay in History.
- The restored documents are checked as any Save's. A restore that check
  refuses says "Restore failed." followed by the reason, as a refused Save
  does; "Restore failed. Snapshot #*N* not found." means that Save does not
  exist.
- The documents become exactly those of #12. **Flows and codeframes that did not
  exist in #12 are removed** in the new Save (they remain in the older Saves,
  so restoring one of those brings them back). The schedules of a flow the
  restore removes are **paused**, as when you delete the flow; its past runs
  and reports stay.
- **Renamed flows go back to their old names with what followed them.** If a
  flow was renamed after #12, restoring #12 brings it back under its old name
  together with its schedules (enabled or paused, as they were) and its
  comment threads. Its runs and reports made under the newer name keep that
  name. A different flow that has since taken the newer name (the renamed
  flow was deleted and a new one created under its name) is not part of
  this: the restore removes it like any flow #12 did not have. Its schedules
  are paused and, like its comments, stay with it rather than moving to the
  restored flow.
- A flow that was **deleted** after #12 comes back with the restore, but its
  schedules stay paused: resume them on the **Flows** screen.
- The restored documents are validated again with the **current** engine, so
  the new Save's state can differ from #12's.
- Restoring does not publish anything. The environments keep serving what they
  served; republish when you want the restored version in the field.

Restoring needs the member role or higher.

## Roll back the survey in the field

To put an older version back in front of respondents **without** changing what
you are editing, deploy it:

1. Open the Save and click **Deploy**.
2. The **New deployment** dialog opens with that Save preselected under
   **Version** ("#12 — Reworded the screener"). Only Saves without the state
   **error** are listed. The hint under the field reads "only valid Saves can
   be deployed" for a valid Save, "saved with warnings" for a Save with
   warnings, and "saved with 1 error — publishable after a confirmation" ("…
   *N* errors …") for a Save whose questionnaire has lint errors — this dialog
   deploys it without asking again, so read the Save's **Validation** tab
   first.
3. Choose the **Environment** and click **Deploy #12**.

Your working documents stay as they are. Every deployment points at a Save,
so the **live** pill in History always shows which version each environment
serves. Responses, however, do not record the Save that collected them: a
republish keeps the environment's link and `survey_id`. To tell which version
collected an answer, compare its `created_at` with the publish times in
**Settings → Activity** (`deploy.create`; its **Export CSV** includes each
publish's Save number). The `deploy.live` entry that follows marks when the
build finished and the new version started collecting. Publishing is covered in
[[Publishing and Environments|Studio-Publishing-and-Environments]].

**More ▾ → Preview** builds a preview of that Save for looking at — it never
accepts responses — and takes you to **Distribute**. You see "Building preview
of #12…", then "Preview ready — not accepting responses". The preview shows a
fixed banner "Preview — answers are not stored" at the bottom and ends on the
survey's normal completion page. Preview builds are removed automatically
after **7 days**.

---

## Methods draft

**More ▾ → Methods** opens **Methods — Save #*N***: a draft Methods section
derived from this Save's questionnaire, codebook and flows. "Nothing is
invented; passages marked [...] need you. Paste it into the paper and edit."

The draft has these sections:

- **Participants** — mostly `[...]` for you to fill in (population, sampling
  frame, recruitment);
- **Instrument** — pages, question types, blocks, randomization, logic, quotas,
  scripts, environments; an **Assign to a condition** script is described as
  the experiment it is — "each respondent was randomly assigned to one of 2
  conditions (…), recorded as `…`", with the arms' ratio when they are
  weighted and whether the draw is seeded or balanced against quotas;
- **Measures** — per question: type, scale, number of options, range, missing
  codes, variable and label;
- **Procedure** — how the questionnaire was administered, consent, closing
  pages;
- **Data handling and analysis** — every flow in the order **Run all** runs
  them (a flow after the flows whose tables it reads), and every node of each
  in execution order, in words, naming the test each analysis runs: "mean Age was
  compared by Region with a one-way ANOVA, followed by Tukey's HSD for every
  pair of groups", "mean Age was compared between two groups of Gender with
  Welch's t-test (unequal variances), reporting the mean difference with its
  95% confidence interval and Cohen's d", "Age was cross-tabulated against
  Region with Fisher's exact test (Fisher-Freeman-Halton beyond 2 × 2, its p
  estimated from 20,000 random tables with the same margins when there are too
  many to enumerate), counting respondents", "an exploratory factor analysis of 8 items was run
  (minimum residual extraction, promax rotation), retaining factors with an
  eigenvalue above 1";
- **Pre-registration** — which Save was registered and what changed since;
- **Software** — engine and Studio versions;
- a closing line naming the authors from
  [Study & citation](Studio-Project-Settings#study--citation).

For a project started from the example study, Save #1's draft describes 18
pages with 33 questions (its Screen-out, Redirect and Final pages are not
counted), the random assignment to the sleep or the time message (recorded
as `message_arm`, drawn with a fixed seed), the consent "on page 2", piped
text as "[answer to main_app]", each wide multiple choice with as many options
as it has variables, and the six flows from *1. Clean raw responses* to *6.
Segments*, naming the variables they derive by their labels (*Wellbeing index
(1-5)*, *Usage segment*) and the arm as *Message arm*, as their tables do.

Switch between **Rendered** and **Markdown**, click **Copy Markdown**, or
**.md** to download `METHODS-s<N>.md`. The same draft is included in every
research bundle as `METHODS.md`.

---

## Pre-registration

**Pre-register** tags one Save as the registered questionnaire and analysis
plan. Later Saves are reported against it.

```
┌ Pre-register Save #12? ─────────────────────────────────────────── ✕ ┐
│ #12 becomes the registered questionnaire and analysis plan (replacing  │
│ #9). Later Saves are reported against it: the Methods draft and every  │
│ bundle's PROVENANCE.md list the documents that changed since. Tag it   │
│ before fieldwork starts.                                               │
│                                                Cancel   Pre-register   │
└────────────────────────────────────────────────────────────────────────┘
```

What it does:

- The Save shows a **pre-registered** pill in History and in its header, and is
  marked "(pre-registered)" in **Compare with**, so the deviations are one
  comparison away.
- Every bundle's `PROVENANCE.md` gets a *Pre-registration* line: "this Save
  (#12) is the pre-registration", or the registered Save and the documents
  changed since, or "no document changed since".
- The Methods draft states "The questionnaire and the analysis plan were frozen
  as Save #12 on *date*…" and lists the documents changed since.

Rules:

- One per project: tagging another Save moves the tag (the dialog says which
  Save it replaces).
- To remove it, click **Pre-registered** → "Remove the pre-registration tag from
  #12?" → **Remove tag**. "Later Saves stop being reported against this one in
  the Methods draft and PROVENANCE.md. Nothing else changes."
- Not available for a Save with errors. Any member can tag, move or remove it;
  the change appears in the project's Activity as `snapshot.tag`.

What it does **not** do:

- **Nothing is locked.** Later Saves can still change any document; the tag
  only makes the changes visible and reported.
- **The date is the Save's own date**, not the moment you tagged it. Studio
  keeps no separate registration timestamp.

> **Tip.** For a timestamp and a record that do not depend on Studio,
> [deposit](#depositing-to-zenodo-or-osf) the pre-registered Save to Zenodo
> before fieldwork: you get a citable DOI for the actual executable instrument
> and analysis plan, not a PDF describing them.

---

## Depositing to Zenodo or OSF

**More ▾ → Deposit** sends this Save's research bundle — code, documents,
Methods draft, `CITATION.cff`, `PROVENANCE.md` — to a repository that keeps it
citable. "Zenodo mints a DOI; OSF stores the file in your project."

### Before you start

1. Create a personal access token in your repository account: on Zenodo under
   your account's applications settings (a token for **sandbox.zenodo.org** is
   separate and created on the sandbox site); on OSF under your account's
   personal access tokens.
2. Store it as a project secret under
   [Settings → Secrets](Studio-Project-Settings#secrets), for example
   `ZENODO_TOKEN` or `OSF_TOKEN`. Only owners and admins can add secrets.
3. Fill in [Study & citation](Studio-Project-Settings#study--citation) — it
   becomes the deposit's metadata.

### The dialog

| Field | Notes |
|---|---|
| **Repository** | **Zenodo** (default) or **OSF** |
| **Access token** | a project secret; Studio preselects one whose name contains "zenodo". With no secrets the list says "(no secrets yet)" and the hint "add the token under Settings → Secrets first" |
| **OSF project id** | OSF only — "the short code in osf.io/<id>", for example `ab3cd` |
| "Use sandbox.zenodo.org (test DOI; needs a sandbox token)" | Zenodo only — **checked by default** |
| "Publish immediately (mints the DOI; otherwise a draft to review on Zenodo)" | Zenodo only — unchecked by default |
| "Include the data collected so far: data/responses.csv, and the project tables and uploaded files the flows read. Survey-link parameters (panel ids) are included only where a flow reads one; invitation tokens never are." | both; unchecked by default; at most 100,000 responses |

> **Important.** The sandbox box is **on by default**, which gives a *test* DOI
> on sandbox.zenodo.org. For a real DOI, uncheck it and choose a secret that
> holds a token from zenodo.org.

Click **Deposit** (it shows "Depositing…" while the bundle is built and
uploaded). Deposits need the member role or higher and are available on every
plan. They are not available for a Save with errors.

### What is sent

**Zenodo.** Studio creates a deposition, uploads the bundle
(`<project-slug>-s<N>.zip`, or `-data.zip` with responses) and sets its
metadata:

| Zenodo field | Taken from |
|---|---|
| Title | **Study title**, else the project name, else the questionnaire title |
| Creators | **Authors**, written "Family, Given" with ORCID and affiliation; if none, the project name |
| Description | the **Abstract**, followed by a paragraph describing the bundle (pages, flows, responses included) |
| Version | `save-N` |
| Keywords | **Keywords**, or `survey`, `siamang` if none |
| License | **License**, when it is CC-BY-4.0, CC-BY-SA-4.0, CC-BY-NC-4.0, CC0-1.0, MIT or ODbL-1.0 (the deposit is then open access); otherwise no license is set |
| Upload type | dataset |

Without **Publish immediately** the deposition stays a **draft** that you review
and publish on Zenodo; Zenodo may already show a reserved DOI for it.

**OSF.** The bundle is uploaded to the OSF project's storage. OSF assigns no
DOI to a file; the deposit records the file's link. Registering the OSF project
for a DOI is done on OSF.

### Results

| State | Meaning |
|---|---|
| **draft** | on Zenodo, not published yet |
| **published** | published on Zenodo (DOI minted), or uploaded to OSF |
| failed | the repository refused; the reason is shown and nothing appears on the Save |

Successful deposits appear in the **Deposited:** bar of the Save, with the DOI
or link. Toasts: "Deposited Save #12 — DOI 10.5281/zenodo.… (draft, review it
on Zenodo)", "Deposited Save #12 to OSF".

Errors you may see:

- "Deposit failed. No project secret named '*KEY*'; add the repository token
  under Settings → Secrets."
- "the OSF project id is the short code in its URL, like 'ab3cd'"
- "could not create the deposition: HTTP 401 …" (and likewise "could not upload
  the bundle", "could not set the metadata", "could not publish the
  deposition", "could not upload the bundle to OSF") — the repository's own
  message follows; a 401 or 403 usually means a wrong, expired or
  under-privileged token, or a sandbox token used against zenodo.org (or the
  reverse)
- "Zenodo is unreachable: …" / "OSF is unreachable: …"
- "Deposit failed. This table exceeds the synchronous export limit of 100,000
  rows. …" — deposit without responses instead

> **Note.** The DOI Zenodo mints is not copied back into Study & citation. Add
> it to the **DOI** field yourself so later bundles cite it.

---

## Retention

Saves, their documents and their generated code are kept for the life of the
project; nothing is pruned. Deleting a project deletes its history with
everything else, so download a bundle of any version you might need before you
use the [Danger Zone](Studio-Project-Settings#danger-zone). Only the latest 100
Saves are listed in History (see above).

## See also

- [[Reproducibility: Code, Bundles and Citation|Studio-Reproducibility]]
- [[Publishing and Environments|Studio-Publishing-and-Environments]]
- [[Working Together|Studio-Collaboration]]
- [[Project Settings|Studio-Project-Settings]]
- [[Key Concepts|Studio-Key-Concepts]]

<!-- studio-nav -->
---

← [[Reports|Studio-Reports]] · [Studio contents](Studio-Overview#all-pages) · [[Reproducibility: Code, Bundles and Citation|Studio-Reproducibility]] →
