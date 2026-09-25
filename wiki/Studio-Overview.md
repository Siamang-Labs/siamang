# Siamang Studio — Overview

**Siamang Studio** is a survey platform for researchers and small teams: a
visual questionnaire builder, publishing and fieldwork monitoring, a response
database with exports, a node-based analysis canvas, live dashboards and
reports — without writing a line of code.

What makes it different from the usual survey tool: **every document you build
is also Python.** Your questionnaire compiles to `questionnaire.py`, every
analysis flow to its own `.py`, and any version of your project downloads as a
*research bundle* — a zip that reproduces your tables, charts and report
outside Studio, on the siamang engine the bundle pins. Nothing you make in
Studio is trapped in Studio.

> *Click to build. Download the code.*

- **App:** `studio.siamang.org`
- **Published surveys:** `study.siamang.org/<survey-id>/` — one permanent link
  per environment

> **Beta.** Studio is in open beta. Signing up gives you your own organization
> on a **30-day Pro trial**. When the trial ends the organization continues on
> the Free plan — nothing is deleted. See
> [[Plans, Trial and Billing|Studio-Plans-and-Billing]].

---

## What you can do

| Stage | In Studio | Page |
|---|---|---|
| **Build** | Pages, blocks, nine question types plus presets, a visual condition builder, branching, quotas, randomization, a codebook built alongside the questions, theme, scripts, import from Qualtrics / LimeSurvey / SurveyJS | [[The Builder\|Studio-Builder-Overview]] |
| **Test** | Engine validation, a live preview on the real runtime, a routing walkthrough, simulated respondents, a public preview link for reviewers | [[Testing Your Survey\|Studio-Testing-Your-Survey]] |
| **Field** | Environments (`pilot`, `main`), permanent links, QR codes, embeds, access codes, captcha, one response per browser, panel-provider returns, email invitations with reminders, closing dates you can move without a rebuild | [[Publishing and Environments\|Studio-Publishing-and-Environments]] |
| **Monitor** | Completed interviews against caps, quota cells that close when full, drop-off by page, data quality while the field is open, live tiles from your analysis | [[Live Monitoring\|Studio-Live-Monitoring]] |
| **Data** | The response database, instant insights, exports to CSV, Excel, SPSS, Stata, Parquet and SQLite, deletion for erasure requests | [[Responses and the Data Tab\|Studio-Responses-and-Data]] |
| **Analyze** | A canvas of engine nodes: cleaning, weighting, crosstabs, banner tables, tests, regression, MaxDiff, conjoint, TURF, charts | [[Analysis Flows\|Studio-Flows]] |
| **Report** | Documents built from the flow with your own text, a report theme, HTML and print-to-PDF, public live dashboards | [[Reports\|Studio-Reports]] |
| **Keep** | Numbered versions of the whole project, diffs, restore, pre-registration, Zenodo / OSF deposits, research bundles | [[History and Versions\|Studio-History-and-Versions]] |

---

## Who it is for

- **Academic researchers and students** — build the instrument and the analysis
  without code, then attach the `.py` and the labeled `.sav` to the paper.
- **Small research and marketing agencies** — one per-organization price, the
  whole study in one project, a report and a bundle for the client.
- **UX, CX and product teams** — live dashboards from the analysis, exports to
  your warehouse through connectors.
- **Methods teachers** — every step has a *Download .py*, so students can see
  exactly how a questionnaire becomes data and a table.

---

## Where Studio sits in the Siamang family

```
siamang            the engine: a source-available Python library — questionnaire model,
   │               compiler, survey runtime, analysis, reports       → Library section of this wiki
   │
   ├── siamang Cloud    research-as-code: a Git repository per project,
   │                    for teams who write the survey as code           → Cloud section of this wiki
   │
   └── Siamang Studio   a visual survey platform: everything by mouse,
                        code included as a download                      → this section
```

Studio and Cloud are **separate products** with separate accounts and billing;
they share the engine. In Studio you never see or edit code — you download it.
If you later want to work with that code directly, the downloaded
`questionnaire.py` and flow scripts are ordinary programs for the
[[siamang library|Quickstart]] (and can be brought into Cloud).

---

## How to read this guide

The pages are ordered as a study unfolds; the sidebar follows the same order.

- **New to Studio?** [[Quick Start|Studio-Quick-Start]] (twenty minutes), then
  [[Key Concepts|Studio-Key-Concepts]].
- **Want the whole journey on one realistic study?**
  [[Tutorial: A Study from Start to Finish|Studio-Tutorial-End-to-End]].
- **Looking for how to do one thing?** [[Recipes|Studio-Recipes]] and
  [[FAQ and Troubleshooting|Studio-FAQ-and-Troubleshooting]].

### Conventions

- **Bold** marks buttons and screen labels exactly as they appear.
- `Monospace` marks things you type or see verbatim — file names, variable
  names, URLs, codes.
- *(Plus)*, *(Pro)*, *(Corporate)* after a feature means it needs that plan or
  higher. During the Pro trial everything marked *(Plus)* and *(Pro)* is
  available.
- **Save** with a capital S means a numbered project version (`#17`), not just
  pressing a button. See [[Key Concepts|Studio-Key-Concepts]].
- `Ctrl/Cmd` means `Cmd` on macOS and `Ctrl` elsewhere.

---

## All pages

### Get started
- [[Quick Start|Studio-Quick-Start]] — from sign-up to your first responses and your first table
- [[Key Concepts|Studio-Key-Concepts]] — organizations, projects, Saves, deployments, flows
- [[Tutorial: A Study from Start to Finish|Studio-Tutorial-End-to-End]] — one realistic study, every stage

### Account & workspace
- [[Sign Up and Sign In|Studio-Sign-Up-and-Sign-In]] — accounts, email confirmation, Google / Microsoft, passwords, invitations
- [[Account and Profile|Studio-Account-and-Profile]] — profile, appearance, API keys, support
- [[Organizations and Team|Studio-Organizations-and-Team]] — workspaces, roles, invitations, organization settings, audit log
- [[Projects|Studio-Projects]] — creating projects, templates, the projects list, Saves and drafts
- [[Project Settings|Studio-Project-Settings]] — name, citation metadata, runtime, environments, secrets, danger zone
- [[Plans, Trial and Billing|Studio-Plans-and-Billing]] — what each plan includes, the trial, limits

### Build the questionnaire
- [[The Builder|Studio-Builder-Overview]] — the screen, pages, blocks, questions, the inspector, saving
- [[Question Types|Studio-Question-Types]] — every type and preset, and every option
- [[Codebook and Variables|Studio-Codebook-and-Variables]] — scales, value labels, missing codes
- [[Logic and Branching|Studio-Logic-and-Branching]] — conditions, show/hide, skip, branch rules, piping, the Logic map
- [[Quotas and Randomization|Studio-Quotas-and-Randomization]] — quota cells, shuffles, experimental assignment
- [[MaxDiff and Conjoint|Studio-MaxDiff-and-Conjoint]] — choice designs from build to analysis
- [[Theme and Branding|Studio-Theme-and-Branding]] — the survey's look, wording, the organization's house style
- [[Scripts|Studio-Scripts]] — the behavior library and custom JavaScript
- [[Importing Questionnaires|Studio-Importing-Questionnaires]] — Qualtrics, LimeSurvey, SurveyJS, JSON and Python
- [[Question Bank, Templates and Library|Studio-Question-Bank-and-Library]] — reuse standard and your own material
- [[Testing Your Survey|Studio-Testing-Your-Survey]] — validation, preview, walkthrough, simulation, share links
- [[AI Assistant|Studio-AI-Assistant]] — reviews, rewrites, answer options, drafts from a brief

### Fieldwork
- [[Publishing and Environments|Studio-Publishing-and-Environments]] — publish, pause, close, closing dates, response caps, republish, roll back
- [[Links, QR Codes, Embeds and Access Control|Studio-Distribution-Channels]] — sharing the survey and restricting who answers
- [[Panel Providers|Studio-Panel-Providers]] — Prolific, Cint, Dynata and custom panels
- [[Email Invitations|Studio-Email-Invitations]] — contacts, personal links, reminders, unsubscribes
- [[What Respondents See|Studio-Respondent-Experience]] — the survey from the other side
- [[Live Monitoring|Studio-Live-Monitoring]] — fieldwork monitor, live tiles, public dashboards

### Data
- [[Responses and the Data Tab|Studio-Responses-and-Data]] — tables, columns, searching every row, insights, deleting a response
- [[Data Exports|Studio-Data-Exports]] — every format and what it carries
- [[Data Quality|Studio-Data-Quality]] — attention checks, speeders, straightliners, captcha flags

### Analysis & output
- [[Analysis Flows|Studio-Flows]] — the canvas, renaming and deleting flows, running, scheduling, live mode
- [[Node Reference|Studio-Node-Reference]] — every node and every parameter
- [[Cleaning and Weighting Data|Studio-Cleaning-and-Weighting]] — preparing data the documented way
- [[Coding Open Answers|Studio-Open-Answer-Coding]] — codeframes and the frozen-coding approach
- [[Reports|Studio-Reports]] — composing, styling, downloading, printing
- [[History and Versions|Studio-History-and-Versions]] — Saves, diffs, restore, Methods, pre-registration, deposits
- [[Reproducibility: Code, Bundles and Citation|Studio-Reproducibility]] — Download .py, the research bundle, citing

### Integrations & administration
- [[Files|Studio-Files]] — uploads and run outputs
- [[Connectors|Studio-Connectors]] — Sheets, Excel 365, warehouses, storage, CRM
- [[Schedules and Webhooks|Studio-Schedules-and-Webhooks]] — automation and notifications
- [[API and API Keys|Studio-API-and-API-Keys]] — scripting Studio
- [[Working Together|Studio-Collaboration]] — edit locks, following a colleague, comments, save conflicts
- [[Security and Privacy|Studio-Security-and-Privacy]] — where data lives, respondent privacy, ethics

### Reference
- [[Recipes|Studio-Recipes]] — step-by-step solutions to common tasks
- [[Limits and Quotas at a Glance|Studio-Limits-Reference]]
- [[Keyboard Shortcuts|Studio-Keyboard-Shortcuts]]
- [[FAQ and Troubleshooting|Studio-FAQ-and-Troubleshooting]]
- [[Glossary|Studio-Glossary]]

---

## Getting help

- In the app: avatar menu → **Documentation** opens this wiki; **Profile →
  Support** links to examples, the issue tracker and feature requests.
- Email: `info@siamang-team.org` — include the organization slug, the project
  slug and the Save number; that is usually enough to reproduce anything.
- Legal: [Terms of Use](https://siamang.org/terms-of-use) ·
  [Privacy Policy](https://siamang.org/privacy-policy)

<!-- studio-nav -->
---

[Studio contents](Studio-Overview#all-pages) · [[Quick Start|Studio-Quick-Start]] →
