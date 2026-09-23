# Key Concepts

Siamang Studio has a small vocabulary, and every screen uses it the same way.
Read this page once and the rest of the guide — and the product — will make
sense. Each concept links to the page that covers it in full.

---

## The shape of a study

```
 Organization  (workspace: members, plan, library)
   └── Project  (one study)
         ├── Documents      questionnaire · flows · settings
         │      └── Saves   #1, #2, … #17   (numbered versions of all documents)
         ├── Deployments    a Save published to an environment (pilot, main, …)
         ├── Database       responses · quota_counters · tables your flows write
         ├── Runs           executions of flows, with logs and output files
         └── Files          uploads and run outputs
```

And the life of that study, left to right:

```
 Builder ──Save──▶ #17 ──Publish──▶ study.siamang.org/<survey-id>/  (env: main)
                    │                          │
                    ▼                          ▼
             questionnaire.py            respondents answer
                                               │
                                               ▼
 Flows ◀──────────── reads ─────────── responses table
   │
   ├──Run──▶ tables · charts · reports · live tiles
   └──────▶ <flow>.py  +  research bundle (zip that runs without Studio)
```

---

## Organization

A **workspace**. It owns projects, members, the plan and the bill. You get one
automatically when you sign up, and you can belong to several (your own plus
any you are invited to). Plans and limits are **per organization**, not per
person. Members have one of three roles: **owner**, **admin**, **member**.

→ [[Organizations and Team|Studio-Organizations-and-Team]] ·
[[Plans, Trial and Billing|Studio-Plans-and-Billing]]

## Project

**One study**: its questionnaire, its analysis flows, its settings, its
response database, its deployments and its complete history. Waves of the same
tracker usually belong in one project so the codebook and history stay
together.

Every project has nine tabs:

**Builder · Distribute · Data · Flows · Live · Reports · History · Files · Settings**

→ [[Projects|Studio-Projects]]

## Documents

Under the hood a project is a handful of documents:

| Document | What it holds | Edited in |
|---|---|---|
| `survey/questionnaire.json` | pages, blocks, questions, logic, quotas, codebook, theme, scripts | **Builder** |
| `flows/<name>.flow.json` | one analysis flow: nodes, connections, parameters, report layout, live tiles | **Flows** |
| `studio/settings.json` | environments, runtime, connectors, pinned insights, report house style, study and citation metadata | **Settings**, **Distribute** |
| `analysis/<name>.codeframe.json` | a coding scheme for one open-text question | **Flows** (Code open answers) |

You never have to open these files — you edit them through the screens. They
matter because they are what gets versioned, downloaded and reproduced.

## Draft

Your **unsaved edits**. While you work, Studio autosaves a private draft to the
server 1.5 seconds after your last change, so closing the tab loses nothing. A draft is not validated,
not published and not part of history. Colleagues see it only while they are
following your edits live (see *Edit lock* below).

## Save

A **Save** (capital S) is a numbered version of the **whole project** — `#17`.
Pressing **Save** does three things:

1. every changed document gets a new version;
2. the engine validates it and generates its Python (`questionnaire.py`,
   `<flow>.py`), which is stored **with that version**;
3. the set is stamped with a sequence number, a message and a validation
   state.

The **Save badge** in the topbar shows the project's current state from any
tab; click it to open that Save in History.

| Badge | Meaning |
|---|---|
| `● valid #17` | Save 17 is clean — publishable and runnable |
| `● warnings #17` | saved; the engine has remarks — publishable after you confirm |
| `● errors #17` | saved but broken — cannot be published |
| `checking #17` | validation of Save 17 is still running |
| `unsaved` | the project has never been saved |
| `saving…` | a Save is in progress |

Saves are never rewritten or deleted. Going back to an old version creates a
**new** Save ("Restore version #12").

→ [[History and Versions|Studio-History-and-Versions]]

## Edit lock

Each document has **one editor at a time**. Opening the Builder or a saved flow
takes the lock; it is renewed every 30 seconds while you work and released when
you leave the screen (or two minutes after your tab closes). Anyone else who opens the same document follows your draft live and
can comment; **Take over** moves the lock to them without losing your unsaved
work. The questionnaire and each flow lock independently.

→ [[Working Together|Studio-Collaboration]]

## Environment

A named **publishing target** with its own permanent link and optional
response cap. Two are conventional: `pilot` (test wave) and `main` (real
fieldwork). Each environment gets its own survey address, keyed by an
unguessable 12-character survey id:

```
https://study.siamang.org/3f9a1c07b2de/
```

The link never changes when you republish the same environment, so QR codes
and panel setups stay valid across versions.

## Deployment

**One Save published into one environment.** Publishing builds the survey from
the Python stored with that Save and serves it on the environment's link. A
deployment is **live**, **paused**, **closed**, **building** or **failed**.
Every response records the environment (survey id) that collected it. The
environment keeps its id across republishes, so to know which Save was live on
a given day, use the project's **Activity** log: every publish is recorded
there, and its **Export CSV** includes the Save number.

A **preview deployment** is a staged build for looking at: it never accepts
responses.

→ [[Publishing and Environments|Studio-Publishing-and-Environments]]

## Survey host

Published surveys are served from **`study.siamang.org`**, a separate host
from the app (`studio.siamang.org`). Respondents need no account, and the
survey shares no cookies or session with Studio.

→ [[What Respondents See|Studio-Respondent-Experience]]

## Response, respondent, partial

A **response** is one row of the project's `responses` table: the answers plus
fieldwork metadata (timings, last page, URL parameters). A **respondent id** is
a random identifier kept in the respondent's browser so an unfinished interview
can resume — it is not an identity, and it does not stop the same person from
answering twice. A **partial** is an interview that was started but not
submitted; partials appear in the data but do not count toward response caps
or quotas.

→ [[Responses and the Data Tab|Studio-Responses-and-Data]]

## Variable and codebook

Every question writes one or more **variables**. A variable carries its
**scale** (nominal, ordinal, interval, ratio), a **label**, **value labels**
(code → meaning), a valid range and **missing codes**. Together they are the
**codebook** — built while you write questions, not afterwards. It is why SPSS
exports arrive labeled and why tables show "Capital region" instead of `1`.

→ [[Codebook and Variables|Studio-Codebook-and-Variables]]

## Flow, node, run

A **flow** is an analysis drawn as a diagram of **nodes**: sources (the
responses, a table, a file, simulated data), preparation (cleaning, recoding,
weighting), analysis (frequencies, crosstabs, tests, models), charts, and
outputs (reports, tables, files, live tiles). Wires carry typed data:
**SurveyData** (the dataset with its codebook), **Table**, **Chart**, **Stat**
and **Report**.

- **Run to here** executes a flow up to one node and shows the result — a
  quick preview that produces no report and no run-history entry (a
  **Write table** node it reaches does write its table, though).
- **Run** executes the flow's stored Python for the current Save in an
  isolated sandbox and records a **run** with its log and output files.
- **Run all** runs every flow in dependency order and assembles a combined
  report.

There is no code box anywhere in a flow: every node is a documented engine
call, which is why each flow downloads as a readable `.py`.

→ [[Analysis Flows|Studio-Flows]] · [[Node Reference|Studio-Node-Reference]]

## Report and live tile

A **report** is a document a flow produces: headings, your text, tables and
charts with captions. It is written as Markdown (content) plus HTML (the
styled deliverable). A **live tile** is a flow output published to the **Live**
screen — and, if you choose, to a public read-only link for clients.

→ [[Reports|Studio-Reports]] · [[Live Monitoring|Studio-Live-Monitoring]]

## Research bundle and provenance

Any Save can be downloaded as a **research bundle**: a zip with the generated
code, the documents, the codebook, a draft Methods section, a citation file,
the pinned environment and, optionally, the responses. It runs outside Studio,
with the engine version its `environment/requirements.txt` names. **Provenance** — which Save, which data snapshot,
which engine version produced a result — is written into every bundle and into
the footer of every generated report.

→ [[Reproducibility|Studio-Reproducibility]]

---

## Where things are

Every screen has its own address, so you can bookmark it or send it to a
colleague (who needs to be a member of the organization to open it):

| Screen | Address |
|---|---|
| Projects of an organization | `studio.siamang.org/<org>/projects` |
| Team · Library | `studio.siamang.org/<org>/team`, `…/<org>/library` |
| Organization settings | `studio.siamang.org/<org>/settings`, `…/settings/billing`, … |
| A project tab | `studio.siamang.org/<org>/projects/<project>/<tab>` |
| One Save in History | `…/<project>/history/<number>` |
| One flow on the canvas | `…/<project>/flows/<flow-name>` |

The browser's Back and Forward buttons move between screens as you would
expect.

## See also

- [[Siamang Studio — Overview|Studio-Overview]]
- [[Quick Start|Studio-Quick-Start]]
- [[Tutorial: A Study from Start to Finish|Studio-Tutorial-End-to-End]]
- [[Glossary|Studio-Glossary]]
