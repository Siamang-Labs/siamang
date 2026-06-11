# Analysis & Reports

siamang Cloud gives you two ways to make sense of your data: the live
**Dashboard** for quick looks, and **analysis scripts** you commit and run for
full, reproducible analysis with shareable **reports**. This page shows how you
use both from the web app.

## Quick looks: the Dashboard

Open a project's **Dashboard** and find the **Data insights** section. It is
computed live over **all** of your collected responses, so the numbers stay
correct no matter how much data you have. Without writing anything you get:

- A **summary** — total responses, unique respondents, how many are partial, and
  when the last response arrived.
- A **responses-per-day** chart, so you can see fieldwork progress.
- **Frequencies** — pick any variable from the dropdown to see its distribution
  as a bar chart.
- A **crosstab** — choose two variables to see a two-way table (with row and
  column totals).

The Dashboard is read-only and meant for exploring. For weighting, significance
tests, custom tables, and anything you want to save or share, use analysis
scripts.

## Full analysis: scripts and runs

Your analysis is **code**: ordinary Python scripts that read the project's
responses, compute results, and produce tables, files, and reports. You commit
them to the repository and declare them in your project's `siamang.yaml`. The
platform runs each script in an **isolated environment** with read access to your
project's data, captures whatever it produces, and saves every run.

To write scripts, see [[Analysis SDK|Cloud-Analysis-SDK]] (the `siamang_cloud`
helpers for data access and statistics). To declare them, see
[[Project Config (siamang.yaml)|Cloud-siamang-yaml]].

### Declaring a script

Each analysis step is a `type: analysis` task in `siamang.yaml`. It names the
script and, optionally, the report it produces and any extra files to keep:

```yaml
tasks:
  cleaning:
    type: analysis
    entry: scripts/cleaning.py
    description: "Clean raw responses, write to clean_responses"

  final_tables:
    type: analysis
    entry: scripts/final_tables.py
    description: "Build frequency tables and crosstabs"   # becomes a report section title
    report: outputs/final_tables.md                        # the report the script saves
    outputs:
      - outputs/final_tables.xlsx                          # extra files to keep
```

The example project comes with three steps wired up this way: cleaning,
weighting, and final tables.

### Running scripts

Open the **Analysis** screen. The **Scripts** section lists every analysis step
from your `siamang.yaml`. From here you can:

- **Run** a single script — useful while you are iterating on one step.
- **Run all** — run every step in declaration order (e.g. clean → weight →
  tabulate) and combine the results into one report. If any step fails, the run
  stops there.

Each card shows when the script last ran, how long it took, and whether it
succeeded, plus chips linking to whatever it produced.

### Runs: completed or failed

Every time you run something, it creates a **run** that appears in **Run
history**. A run finishes in one of two states:

- **completed** — the script ran to the end successfully.
- **failed** — the script raised an error (open it to read the log and fix it).

Click any run to open its detail panel:

- **Logs** — everything the script printed, plus the error if it failed (with a
  **Copy** button).
- **Outputs** — links to what the run produced: a **report**, new **database
  tables** (jump to them in the Database), and **files** to download.

## Where your results go

A script can produce results in several ways at once, and each shows up in a
predictable place in the app:

| You write… | …and it appears in |
| :--- | :--- |
| `Report(...).add(...).save("outputs/report.md")` | The **report**, openable in the Repository and listed in the run's Outputs |
| `db.write_table("clean_responses", df)` | **Database → Tables** |
| a file under `outputs/` (e.g. an `.xlsx`) | **Files** and the run's Outputs (downloadable) |
| `print(...)` | The run's **Logs** |

## Reports

A **report** is the shareable document your analysis produces — built with the
[[Report Document|Report-Document]] builder (re-exported as `Report` in the
analysis SDK), which turns your tables, headings, and notes into a clean
document.

- Reports are generated in **Markdown** and **HTML** (PDF is planned).
- An individual script's report (its `report:` path) opens in the **Repository**
  as a rendered document, with **MD** and **HTML** download buttons.
- **Run all** combines every step's report into one document — with a table of
  contents, each step titled by its `description` — written to your project's
  reports folder (by default `reports/report.md`).
- Generated reports and files also appear under **Files** so you can find and
  download them later.

## Running analysis on a schedule

On the **Plus** plan and above, the **Analysis** screen has a **Schedules** panel
where you can run a single script or a full **run-all** automatically on a cron
schedule — handy for refreshing tables and reports nightly during fieldwork. See
[[Schedules & Webhooks|Cloud-Scheduling-and-Webhooks]] for schedules and for
getting notified when runs finish.

## See also

[[Analysis SDK|Cloud-Analysis-SDK]] · [[Project Config (siamang.yaml)|Cloud-siamang-yaml]] · [[Report Document|Report-Document]] · [[Schedules & Webhooks|Cloud-Scheduling-and-Webhooks]]
