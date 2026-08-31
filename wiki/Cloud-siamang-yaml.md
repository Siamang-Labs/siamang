# Project Config (siamang.yaml)

Every siamang Cloud project has a `siamang.yaml` file at the root of its repository. It
is the one place where you wire the project together: where your survey lives, which
deployment environments exist, what analysis scripts to run, the runtime your scripts
use, and where reports go.

You edit this file like any other file in the project — in the web app's editor or over
Git — and commit it. The platform reads it when it validates a commit, deploys a survey,
and runs analysis.

## Annotated example

This is the kind of config generated for a new project, with a comment on each key. Every
part of it is editable.

```yaml
name: "Digital Life & Wellbeing 2026"  # the project's display name
org: "research-agency"               # the organization that owns it
version: "1.0"                       # config format version

tasks:
  # ── The survey itself ─────────────────────────────────────────────────────
  survey:
    type: survey
    entry: survey/questionnaire.py   # the module that defines `survey = Questionnaire(...)`
    environments:
      - { name: pilot, max_responses: 50 }     # a separate deployment + response cap
      - { name: main,  max_responses: 1200 }

  # ── Analysis scripts (run with the Cloud Analysis SDK) ────────────────────
  cleaning:
    type: analysis
    entry: scripts/cleaning.py
    description: "Dedup respondents, drop speeders/partials -> clean_responses"

  tables:
    type: analysis
    entry: scripts/tables.py
    description: "Frequencies, a crosstab with a chi-square test, Markdown report"
    report: outputs/tables.md        # the report this script saves

runtime:
  python: "3.11"                     # informational; the sandbox pins the version
  packages:                          # from the curated allowlist
    - "siamang[charts]>=0.5"
    - "pandas>=2.0"
    - "numpy>=1.26"

reports:
  combined: reports/report.md        # the "Run all" document

# Data insights are off by default; declare an `insights:` block to pin
# charts to the Dashboard (see below).
# insights:
#   - type: stats
#   - type: frequency
#     variable: life_satisfaction
```

## `name` and `org`

- `name` — the project's display name, shown across the web app.
- `org` — the slug of the organization that owns the project.

## `tasks`

`tasks` is a **mapping** of task name to spec — not a list. The key (`survey`,
`cleaning`, `tables`, …) is the task's name; it is also how the task is referred to
elsewhere (for example as a section heading in a combined report, or as the
`script_name` of a [[schedule|Cloud-Scheduling-and-Webhooks]]). Each spec has a `type`.

### `type: survey`

One survey task drives your deployments.

- `entry` (required) — the path to the questionnaire module that defines a module-level
  `survey` object (and, optionally, an `options` dict for compiler settings and quotas).
- `environments` — a list of `{ name, max_responses }`. Each environment is a separate
  deployment with its own response cap — for example a small `pilot` and a larger `main`.

### `type: analysis`

Each analysis task is one Python script you write with the
[[Cloud Analysis SDK|Cloud-Analysis-SDK]].

- `entry` (required) — the path to the script.
- `description` — a human-readable label; it becomes the section title in the combined
  report.
- `report` — the path to the report your script saves (via `Report.save(...)`). The
  platform opens it as a document and lists it among the run's outputs.
- `outputs` — extra generated files to keep (for example an Excel export). Markdown
  outputs are also folded into the combined report by **Run all**.

```yaml
  final_tables:
    type: analysis
    entry: scripts/final_tables.py
    description: "Build frequency tables and crosstabs"
    report: outputs/final_tables.md
    outputs:
      - outputs/final_tables.xlsx
```

### `type: connector`

A `type: connector` task moves a table in or out of an external store (S3, a data
warehouse, Google Sheets, your own database, and more). You name a destination, a project
table, a project secret for credentials, and a nested `config:` block:

```yaml
  export_to_s3:
    type: connector
    target: s3                 # where the data goes
    direction: out             # out (export) or in (import)
    table: clean_responses     # the project table to move
    secret: aws_creds          # a project secret holding the credentials
    config:
      bucket: my-research-exports
      key: work-wellbeing/responses.csv
```

The Connectors surface unlocks at **Plus**, and each target has its own minimum plan.
See [[Connectors|Cloud-Connectors]] for the full catalog of destinations and the
`config` keys each one needs. Note that the required `config` keys are checked when
the connector **runs**, not at commit time — commit validation only warns when a
declared target is above your organization's plan.

## `runtime`

The runtime applies to your analysis scripts (and survey compilation).

- `python` — declarative for now: all scripts run in the platform's sandbox image
  (Python 3.11), and picking another version is not yet implemented.
- `packages` — the packages available to your scripts. `siamang` and `pandas` are the
  usual entries. Packages must come from the platform's **curated allowlist**
  (numpy, pandas, scipy, statsmodels, scikit-learn, matplotlib, seaborn, and other
  research staples) — a commit declaring anything else fails validation with the
  package named.

## `reports`

These settings control the combined document that **Run all** produces by stitching your
analysis reports together (see [[Analysis & Reports|Cloud-Analysis-and-Reporting]]).

- `combined` — the combined document's path (default `reports/report.md`).
- `dir` and `formats` appear in some generated configs but are reserved — the
  platform currently reads only `combined` (reports are always rendered as Markdown
  and HTML; PDF is planned).

## `insights`

**Data insights** are off by default. Declaring an `insights:` block pins live
widgets to the project's **Dashboard** — a list of entries with a `type` of `stats`,
`timeseries`, `frequency` (with `variable:`), or `crosstab` (with `rows:` and
`cols:`), plus an optional `title`. See
[[Analysis & Reports|Cloud-Analysis-and-Reporting]] for what each widget shows.

```yaml
insights:
  - type: stats
  - type: timeseries
  - type: frequency
    variable: life_satisfaction
    title: "Overall life satisfaction"
  - type: crosstab
    rows: life_satisfaction
    cols: age_group
```

## See also

- [[Cloud Analysis SDK|Cloud-Analysis-SDK]] — write the scripts your analysis tasks run
- [[Connectors|Cloud-Connectors]] — declare `type: connector` tasks
- [[Schedules & Webhooks|Cloud-Scheduling-and-Webhooks]] — run tasks automatically
- [[Analysis & Reports|Cloud-Analysis-and-Reporting]] — run tasks and read reports
