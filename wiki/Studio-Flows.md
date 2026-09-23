# Analysis Flows

A **flow** is your analysis drawn as a diagram: load the data, clean it,
weight it, tabulate it, chart it, write a report. This page covers the
**Flows** tab, building a flow on the canvas, previewing it, running it on its
own or with the others, and what each run leaves behind. Every node and
parameter is described in [[Node Reference|Studio-Node-Reference]].

Each box on the canvas is one call into the engine, so the whole flow
generates a readable Python script you can download and run yourself. There is
no "Python node" and no code box on the canvas — by design. What you can build
here is exactly what the generated script does.

---

## How flows fit into a project

- A flow is one document of the project, `flows/<name>.flow.json`. It is
  versioned with every **Save**, like the questionnaire.
- **Run** always executes the flow **as of the current Save** — never your
  unsaved edits. **Run to here** is the exception: it previews your unsaved
  draft.
- Flows read the project's data (the `responses` table, tables other flows
  wrote, or simulated respondents) and leave results in **Files**, **Reports**,
  the **Data** screen (tables) and **Live** (tiles).
- Every run is recorded in **Run history** with its log and output files.

> **Note.** Flows run against a Save. A project that has never been saved
> shows "This project has no Save yet — flows run against a Save. Save the
> project first." with an **Open Builder** button.

---

## The Flows screen

```
Flows  Load → Clean → Analyze → Report · run history        [More ▾] [+ New flow] [▶ Run flow]

Flows  2 · one document each under flows/
┌──────────┬─────────────────────┬──────────────────────────┬───────────────────┬────────────┐
│ Flow     │ Description         │ Last run                 │ Report            │            │
│ cleaning │ Clean raw responses │ ● 23 Sep, 09:12 · 0m 08s │ —                 │ review run │
│ tables   │ Key tables          │ ● 23 Sep, 09:13 · 0m 34s │ outputs/tables.md │ review run │
└──────────┴─────────────────────┴──────────────────────────┴───────────────────┴────────────┘

Pipeline  flows run in order · each step may read the previous step's table
   ● cleaning ──── ● tables

Schedules  1 · cron, UTC · fired by the worker                         [+ Schedule a run]

Run history
   [run card] [run card] …                                   [Show more (12 older)]
```

The sections appear in this order: **Flows** (with the **Assistant** panel
under it while a review is open), **Pipeline**, **Schedules**, **Run history**.

### Header

| Control | What it does |
|---|---|
| **More ▾ → Run all flows** | Runs every flow of the current Save as one run, each flow after the flows whose tables it reads (see [Run all](#run-all)). Tooltip: "Run every flow in order". |
| **More ▾ → Show archive** / **Back to current** | Switches the run list to runs hidden by **Reset history**, and back. |
| **More ▾ → Reset history** | Archives finished runs (shown only when there are some). See [Reset history and the archive](#reset-history-and-the-archive). |
| **+ New flow** | Opens the **New flow** dialog. |
| **▶ Run flow** | Opens the **Run flow** dialog. |

### The flows table

The heading reads "**Flows** `N` · one document each under flows/". One row
per flow:

| Column | Shows |
|---|---|
| **Flow** | the flow's name (its file name) |
| **Description** | the flow's title (or description) |
| **Last run** | status dot, time and duration of the latest run you started or watched in this browser session; "running" while one is in progress |
| **Report** | the flow's **Report path**, or "—" |

Click a row to open the flow on the canvas. Two links on the right:

- **review** — asks the AI assistant to read the flow for analysis mistakes
  (see [AI flow review](#ai-flow-review)). Click it again to close the panel.
- **run** — runs the flow (disabled while it is already running).

> **Note.** After you reload the page, **Last run** may read "never" even for
> a flow that has run. **Run history** below is always complete.

With no flows: "**No flows yet.** The example study ships one to read; start
your own with **New flow**." (The example study ships two flows, `cleaning`
and `tables`.)

### Pipeline

The strip shows every flow as a chip with the status of its latest run, in
**alphabetical order of the flow names** — the order of the flows table. Its
sub-title reads "flows run in order · each step may read the previous step's
table". **Run all** does not always follow the strip: a flow that reads a
table another flow writes runs after that flow, even when its chip comes
first (see [Run all](#run-all)). The strip does not show the order **Run all**
uses. Click a chip to open the **Run flow** dialog with that flow
selected.

### The Run flow dialog

| Field | Content |
|---|---|
| **Flow** | the flow to run; the hint gives its place in the **Pipeline** strip, e.g. "step 2 of 3 — runs after cleaning" or "step 1 of 3 — runs first" ("flows run against the current Save" when the project has one flow). The hint counts the strip's alphabetical order, so for a flow that reads a table written by a flow that sorts after it, the hint differs from the order **Run all** uses |
| **Description** | read-only |
| **Runs as** | read-only, `scripts/<name>.py` — the generated script |
| **Report** | read-only, the report path, "written when the run completes" |

Buttons: **Open on canvas** and **Run** ("Already running…" while a run of that
flow is in progress). Running one flow runs only that flow — not the flows
whose tables it reads; it reads those tables as they are. With no flows yet
the dialog says "No flows yet — create one on the Flows canvas (Load → Clean →
Analyze → Report), Save, and run it from here." and offers **Open Flows**.

### Run history and run cards

Each run is a card, newest first; ten are shown, **Show more (N older)** adds
ten more, up to the 50 most recent runs.

```
┌───────────────────────────────────────────────────────────────────────┐
│ ● success   flow   #412                              23 Sep, 09:13     │
│ ✓ Queued ── ✓ Run ── ✓ Done      ran in 0m 34s                        │
│ tables · Save #17                                                      │
│ [tables.md  4.1 KB] [tables.html  88 KB] [fig_3.png  31 KB]            │
│ › View logs                               [Re-run] [Open flow →]      │
└───────────────────────────────────────────────────────────────────────┘
```

| Part | Content |
|---|---|
| Status | **success**, **warnings**, **failed** or **running** |
| Type | **flow**, **run all** or **connector** (open-answer coding jobs also appear, as **flow**) |
| `#id`, time | the run number and when it started |
| Steps | **Queued → Run → Done** with "ran in 0m 34s"; a Run all shows one step per flow, in the order of the flows table, each marked as that flow finishes (a cross for a flow that failed or was skipped) |
| Entry | the flow name (or script path) and "· Save #N" — the Save it ran |
| Error line | for a failed run, the last line of its log (for example the Python error), or "Run failed — open the logs for details." For a Run all it is the log's last line, which may be about a flow that succeeded (`task tables: ok`) — **View logs** shows every flow's outcome |
| Output chips | one per file the run kept, with its size; click to download |
| **View logs** / **Hide logs** | the run's log; while a run is in progress the logs are open and end with "running…" |
| **Re-run** | runs the same flow (or Run all) again |
| **Open flow →** | opens the flow on the canvas |
| **Run all** | appears instead of **Re-run** when the error says to run an earlier step first or to use Run all |

Output chips download through a link valid for five minutes. If the project's
file storage was not available when the run finished, the log ends with a
warning that the outputs were produced but not saved, and a chip answers "Could
not download this output. It wasn't stored in object storage — configure
storage to enable downloads."

### Reset history and the archive

**More ▾ → Reset history** asks "Archive all completed and failed runs?
In-flight runs are kept. Nothing is deleted — they move to the archive (Show
archive) and stay in the audit log." and confirms with **Reset history**
("Archived N runs" or "Nothing to archive"). It needs the member role or
higher. **More ▾ → Show archive** lists archived runs under **Archived runs**
("No archived runs — Reset history moves completed and failed runs here." when
empty; **Back to the run history** returns).

### Refreshing

While the tab is visible the screen refreshes run statuses every 30 seconds,
so runs fired by a schedule or by Live appear without a reload.

---

## Creating a flow

1. **+ New flow**. The dialog explains: "A flow is a small pipeline — load,
   clean, analyze, report — saved as `flows/<name>.flow.json` and run by the
   engine. Build it on the canvas; it is created at the first Save."
2. Type a **Title** (placeholder "Satisfaction by region"). The file name is
   derived from it and shown as the hint ("file name: satisfaction_by_region"):
   lowercase, every run of other characters becomes `_`, leading digits are
   dropped. If a flow of that name exists the hint says "a flow with this name
   already exists".
3. **Open canvas →**. The new flow starts with one **Responses** node (id
   `src`).
4. Build it, then **Save changes**. Only now does the flow exist.

Name rules: the name must start with a letter and contain only lowercase
letters, digits and `_` (at most 63 characters). `survey` is reserved, and a
flow cannot share its name with a connector; a Save that tries is refused
("task name 'survey' is reserved").

**How many flows** a project may hold is counted at Save:

| Plan | Flows per project |
|---|---|
| Free | 3 |
| Plus | 20 |
| Pro, Corporate | unlimited |

A Save that would exceed the cap is refused with "plan 'free' allows up to 3
analysis flows per project; this Save would have 4 — delete one or upgrade". A
project that is already over the cap (after a downgrade) can still be saved as
long as the number of flows does not grow.

> **Current limitation.** Flows cannot be renamed, duplicated or deleted from
> the interface yet. What you can do instead:
> - **Rename or copy:** create a new flow with the name you want and rebuild it
>   (inside one flow, **Duplicate** copies a node with its parameters).
> - **Remove a flow you just created:** restoring an earlier Save
>   ([History → Restore](Studio-History-and-Versions#restore-an-earlier-version))
>   removes every flow created after that Save — but it also restores the
>   questionnaire and settings of that Save, so use it only when nothing else
>   has changed since.
> - Otherwise contact support. On the Free plan (3 flows per project) plan your
>   flows before you create them.

---

## The flow editor

```
← All flows
Satisfaction by region            ↶ ↷  [Canvas|List|Report]  Check  More ▾  ▶ Run  [Save changes]
┌──────────────┬──────────────────────────────────────────────────┬────────────────────────┐
│ Find node…   │  [Responses]→[Dedup]→[Speeders]→[Rake]→[Apply]    │ NODE INSPECTOR         │
│ ▾ Sources  4 │                          ├──▶[Crosstab]→[Bar]     │ analyze  Crosstab      │
│   Data file  │                          └──▶[Group means]        │ Node id                │
│   Responses  │                                   ↓               │ Rows · Columns · …     │
│   …          │                            [Report section]       │ Instant (SQL)          │
│ › Prepare 14 │                                   ↓               │ Preview   ▶ Run to here│
│ › Analyze 17 │                              [Save report]        │ Connections            │
│ › Visualize 4│                                                   │ Comments               │
│ › Output   7 │   [+ − ⤢]                              minimap    │ Checks 0 errors · …    │
└──────────────┴──────────────────────────────────────────────────┴────────────────────────┘
```

### Header

| Control | What it does |
|---|---|
| **← All flows** | back to the Flows screen |
| Title | the flow's title, editable in place |
| **↶ ↷** | undo / redo (`Ctrl/Cmd + Z`, `Shift + Ctrl/Cmd + Z`) |
| **Canvas \| List \| Report** | the three views of the same flow (below) |
| **Check** | runs the engine's check on your draft ("Checking…"), see [Checks](#checks) |
| **More ▾** | "This flow" status line — "Analysis flow · edited · 9 nodes · 10 edges · no issues" and the file path; the draft-sync status; **Export Python** |
| **▶ Run** | runs the flow as of the current Save; disabled for a new or edited flow (tooltip "Save first") |
| **Save changes** / **Saved** | opens the Save dialog (`Ctrl/Cmd + S`) |

### Three views

- **Canvas** — the diagram: palette, canvas, inspector.
- **List** — the same flow as a table, in dependency order, operable entirely
  from the keyboard: "The same flow as a list, in dependency order — and the
  keyboard path through it: ↑ ↓ move between nodes and open each in the
  inspector, Enter runs the draft up to one, and an input with room offers the
  sources a drag would accept." Columns **Node**, **Inputs** (each input's
  connected sources with **disconnect**, plus a **connect…** / **add
  source…** dropdown of compatible outputs, or "nothing can feed this"),
  **Outputs**, **State** (ok / errors / warnings) and the links **run to**,
  **duplicate**, **delete**. **+ Node** under the table (or `Ctrl/Cmd + K`)
  opens a searchable node picker (↑ ↓ choose · Enter adds · Esc closes).
- **Report** — the report the flow writes, as a document you can edit. See
  [[Reports|Studio-Reports]].

The inspector keeps its width (drag the divider) per browser.

### The palette

Nodes grouped as **Sources**, **Prepare**, **Analyze**, **Visualize** and
**Output**, each with a count. Only **Sources** is open at first; the groups
you open stay open in this browser. The search box **Find node…** matches the
title, the short name and the description, and opens every group with a match.
Each item shows the title and a short name (`crosstab`), plus `· platform` for
nodes that need the project database. Hover an item for its description.

- **Click** an item to add the node to the right of the last node.
- **Drag** an item onto the canvas to drop it where you want.

A new node gets an id from its short name (`crosstab`, then `crosstab_2`, …)
and its parameters' defaults.

### Connecting nodes

Drag from an **output** handle (right edge of a node) to an **input** handle
(left edge of another). Handles are colored by data type; hover one for its
name and type.

- Only compatible ports connect. A refused connection says why, for example
  "Cannot connect: Chart cannot feed SurveyData input "data"" or "Cannot
  connect: that would create a cycle".
- An input that takes one connection keeps only the newest: connecting
  another source to it **replaces** the old wire.
- Inputs that take several (a **Report section**'s items, **Save report**'s
  sections) keep them in the order you connect them — which is the order in
  the report.
- To remove a wire, use **remove** next to it in the inspector's
  **Connections** (or **disconnect** in the List view).

The canvas pans and zooms (the **+ − ⤢** controls, or the mouse); it opens
fitted to the whole flow, and a minimap appears while you move.

### Node cards and status lights

A node card shows its category, title, id and a one-line summary of its key
parameters (`satisfaction × region`, "…" where one is unset). A **Report
section** also shows its number in the report ("—" when it is not wired into
**Save report**). A speech-bubble badge counts open comments.

The status light at the top right:

| Light | Meaning |
|---|---|
| green | no problems found |
| amber | warnings (hover for the count) |
| red | errors (hover for the count) |

After a preview run the light shows the preview instead: "previewed",
"failed in the preview run", "changed since the preview — run again" (stale),
"not reached", "running…" or "not run yet", and the node shows how long it
took (`120 ms`, `1.4 s`).

### The inspector

**With no node selected** it shows the **Flow** settings:

| Field | Meaning |
|---|---|
| **Title** | the flow's title |
| **Description** | shown in the flows table and the methods draft |
| **Report path** | the report file this flow declares (placeholder `outputs/report.md`); **Run all** puts this file into the combined report, and the flows table and **Run flow** dialog show it |
| **Live: recompute on new responses** | Live mode (see [Live mode](#live-mode)) |
| **Preview run** | the last preview's summary ("last run: 7 nodes ok") and **Preview all**, which previews the whole draft |
| **Comments** | comments on the flow as a whole |

**With a node selected:** its category and title with **Duplicate (⌘D)** and
**Delete (Del)** icons, its description, its own problems, **Node id**, the
parameters, the **Instant** counts where available, the **Preview** pane with
**Run to here**, **Connections** (what feeds it and what it feeds, each with
**remove**) and **Comments**.

Below the inspector, the **Checks** block lists the flow's problems ("Checks
2 errors · 1 warning", up to twelve); click one to select its node.

### Node ids

**Node id** ("used by captions and live tiles") names the node in the
generated script (`n_<id>`), in captions and in the report layout. Edit it
freely: it must start with a lowercase letter and contain only lowercase
letters, digits and `_`, and be unique in the flow — otherwise the field
quietly returns to the old id. Renaming carries every connection, caption and
size setting with it.

### Parameters and variable pickers

Each parameter has a control that fits its kind (see
[Reading this page](Studio-Node-Reference#reading-this-page) in the node
reference). Variable parameters are dropdowns or checklists of the codebook's
variables, shown as `name — label` and filtered to the scales the node accepts
(the scales are the hint under the field). A stored name that is no longer in
the codebook shows as "(not in codebook)". In **Filter rows** the value
pickers show value labels — `Capital region (1)` — so you pick the meaning,
not the code. Mappings, weighting targets and answer codes are typed as JSON
codes (`{"1": 0.45, "2": 0.55}`).

> **Current limitation.** The variable dropdowns and checklists list the
> questionnaire's variables only. A variable created earlier in the flow (by
> **Recode**, **Derive**, **Index / scale**, **Explode multiple choice**,
> **Cluster (k-means)** and the quality nodes) stays in the data — it is
> exported and listed by **Describe** — but cannot yet be picked in a later
> node. Parameters you type (weighting targets, **Apply weight**'s column,
> formulas) can name it.

### Checks

Studio checks a flow twice:

- **As you edit**, on the canvas: required parameters, compatible wires,
  cycles, nodes not fed by any source, variables not in the codebook. These
  light the nodes and fill the **Checks** block.
- **With the engine**, when you press **Check**, when you preview and when you
  Save. The banner says "**Engine check: valid.** The engine can generate and
  run this flow." — or lists each problem by node. The engine's verdict is the
  one that counts: a variable of the wrong scale, for example, is only a
  warning on the canvas but an error for the engine.

> **Warning.** A flow **with engine errors can still be saved**, but it has no
> generated script — and because every run uses the whole Save, that one flow
> stops **all** runs and previews of the project ("… failed before sandbox: …
> has no generated code (it did not pass the engine check at Save)") and the
> survey cannot be published from that Save ("snapshot #N has validation
> errors; fix them and save before deploying"). **Press Check before you
> Save**, and fix what it reports.

### Saving, drafts and the edit lock

**Save changes** opens the project's Save dialog; the flow becomes part of a
new numbered Save. Your edits are autosaved as a private draft while you work
(the draft status is in **More ▾**: "Draft synced — not yet saved as a
version.", "Draft restored — save a version when ready.", "Draft sync failed.
Your edits remain in this tab. Retry before closing it." with **Retry draft
sync**).

One person edits a flow at a time. Colleagues who open it see "**Name** is
editing — you are following their changes live … Your own edits are off until
you take over; comments stay open." with **Take over**. See
[[Working Together|Studio-Collaboration]].

---

## Data types on the wires

| Type | What flows through |
|---|---|
| **SurveyData** | the dataset *plus* its codebook and questionnaire — that is why tables come out labeled |
| **Table** | a frequency table, crosstab, group-means table, banner, coefficient table… |
| **Chart** | a bar chart, box plot, heatmap or scatter plot |
| **Stat** | a test result or a set of statistics |
| **Report** | a report section or a whole report |
| **Any** | accepted only by the **Live tile** input: anything can be shown on Live |

Weights, recodes and derived flags are *columns inside* SurveyData, not
separate wires.

---

## Run to here and Preview all

A **preview** executes your **unsaved draft** up to one node, in the same
sandbox and with the same node code as a real run, on the project's current
data — and shows each node's result in the inspector.

Ways to start one:

- select a node and press **▶ Run to here** in its Preview pane, or
  `Ctrl/Cmd + Enter`, or double-click the node;
- **run to** (or `Enter`) in the List view;
- **Preview all** in the Flow settings (or `Ctrl/Cmd + Enter` with nothing
  selected) — the whole draft;
- **Preview report** in the Report view — up to **Save report**.

Only the chosen node and the nodes that feed it run. Your draft is laid over
the current Save, so the project must have been saved once (the flow itself
need not be), and the draft must pass the engine's check.

**What the Preview pane shows:**

| Node output | Preview |
|---|---|
| data (SurveyData) | "N rows × M columns" and the first 20 rows — handy for counting what each cleaning step removed |
| table | the table (first 50 rows) |
| chart | the rendered chart |
| stat | the statistics as a list of names and values |
| report | the report as rendered, with a **Rendered \| Markdown** switch in the Report view |
| file, table write, tile | "This node has no preview (its output is a file or a table write)." |

A node that failed shows its error; nodes after it show "Not reached by the
last preview run." When you change a node, it and everything after it turn
**stale** ("changed since — run again") until the next preview. A failed node
also raises the message "Preview: *ids* failed — see the node".

Previews do not appear in **Run history**, do not save files and do not touch
**Reports** or **Live**. The report preview has no provenance footer — that is
added by real runs.

> **Current limitation.** A preview that reaches a **Write table** node really
> writes the project table. Preview the node *before* the Write table node, or
> expect the table to be replaced.

### Preview limits

| Plan | Previews started per hour | Previews at once |
|---|---|---|
| Free | 30 | 1 |
| Plus | 120 | 1 |
| Pro | 600 | 2 |
| Corporate | unlimited | 4 |

The hourly count is per person and per project, over the last 60 minutes; the
"at once" limit is per person across all projects. A preview runs with 512 MB
of memory and stops after 120 seconds on every plan. The messages you may see:
"Could not start the preview. The preview limit for this hour is reached on
your plan.", "Could not start the preview. A preview is already running — wait
for it to finish.", "Could not start the preview. The draft does not pass the
engine's check — fix the errors first."

### Instant counts

A **Frequencies** node (with a variable) or a **Crosstab** node (with two
different variables) connected **directly** to a **Responses** node also shows
an **Instant** panel marked **SQL · responses**: the counts straight from the
responses table, refreshed as you change the parameters, without a preview
run and without using your preview allowance. It reads "counting…", then
"live" (or "unavailable"). These counts are unweighted and cover all responses
in the table, whatever the Responses node's **Environment** and **Only
completed responses** say. For a multiple-answer question it notes that
percentages are of the respondents who answered.

---

## Running a flow

**▶ Run** in the editor, **run** in the flows table, the **Run flow** dialog
or **Re-run** on a card runs the flow's generated script **as of the current
Save**, in an isolated sandbox, and records a run. A flow can have one run in
progress at a time ("This flow already has a run in progress — see Run
history").

The sandbox has one CPU, no internet access (only the project's own data) and
these ceilings per flow run:

| Plan | Memory | Time |
|---|---|---|
| Free | 512 MB | 5 min |
| Plus | 1 GB | 15 min |
| Pro | 2 GB | 30 min |
| Corporate | 2 GB | 30 min |

A run that reaches the time limit stops with a message that names the limit,
for example "script timed out (300s) — the free plan allows 5 min per flow run;
plus allows 15 min". A run may also write at most 1 GB of files ("script
exceeded the sandbox disk budget (1024 MB written) and was stopped"). A run
stuck without any sign of life for 40 minutes is marked failed ("[reaper] run
timed out and was marked failed").

**What a run keeps.** Only files the flow writes **under `outputs/`** are kept:
up to 50 files and 200 MB per run. When a run writes more, Studio keeps `.json`
files first, then the report documents (`.md`, `.html`), then everything else
— figures, data files — each group in alphabetical order of its path. A file
that would take the run past 200 MB is left out, and smaller files after it
are still kept. So a flow that draws many charts still delivers its report;
the charts past the cap are missing next to its `.md`, while its `.html`
carries its charts inside. The kept files appear:

- in **Files**, as `outputs/<flow>/<file>` — each run of the flow replaces the
  previous version there;
- on the run's card as download chips — each run keeps its own;
- in **Reports**, when they are `.md` or `.html` files;
- on **Data** as tables, for **Write table** nodes;
- on **Live**, for **Live tile** nodes.

The log lists what was kept ("outputs: outputs/tables/tables.md, …").

---

## Run all

**More ▾ → Run all flows** runs every flow of the current Save as one run:

1. **Flows run in dependency order.** A flow that reads a table another flow
   writes runs after that flow. "Reads" means a **Project table** node — or a
   **Responses** node whose **Table** is set to that table — naming a table
   that a **Write table** node of the other flow writes. Studio first runs,
   in alphabetical order of their names, every flow that reads no other
   flow's table; then, again alphabetically, every flow whose tables have now
   been written by the flows before it; and so on. Studio works the order
   out from the flows at every run, so you do not need to name flows so that
   a writer sorts first.
2. **A failed flow does not stop the run.** The flows after it still run —
   except those that read a table it writes (and, in turn, the flows that read
   theirs): they would read an old table or none at all, so they are marked
   failed without running. In the log such a flow's "task tables: failed" line
   is followed by "skipped: needs cleaning, which failed".
3. When every flow has succeeded, Studio assembles the **combined report**. If
   any flow failed or was skipped, the run ends as **failed** once every flow
   has had its turn and no combined report is written; **View logs** lists
   each flow as ok or failed, with each failed flow's error under it — one Run
   all names every broken flow, not only the first.

Flows that read each other's tables in a circle (each needs a table the other
writes) cannot be put in order: they, and the flows that read their tables,
run last, in alphabetical order.

A project can have one Run all in progress at a time ("A run-all is already in
progress — see Run history").

> **Note.** Running a single flow never runs the flows it reads from; it reads
> their tables as they are. The **Pipeline** strip and the hint in the **Run
> flow** dialog list flows alphabetically and do not show the dependency order.

**What Run all keeps.** Only the combined report (and its figures). Each
flow's own report and files are **not** saved by Run all, and Live tiles are
not updated — run a flow on its own (or schedule it) for those.

### The combined report

The combined report — title "Combined report" — has a **Contents** list and
one section per flow that declares a **Report path**, titled with the flow's
title and containing that flow's report. It is written to `reports/report.md`
with an `.html` twin in the project's report house style, and appears on
**Reports** with a **combined** badge. The path can be changed in **Settings →
Reports**.

The sections follow the order in which the flows ran. A flow without a
**Report path** is left out. A flow whose **Report path** names a file the
flow does not write makes the whole Run all fail at once — the flows after it
do not run, and the log shows only the missing file's path. Keep the **Report
path** equal to the **Save report** node's **Path** (the Report view sets both
when it creates the node). See [[Reports|Studio-Reports]].

---

## Schedules *(Plus)*

**Schedule a run** on the **Schedules** heading runs a flow — or **Run all
flows (in dependency order)**, the order described in [Run all](#run-all) —
on a timer: **Every 30 minutes**, **Hourly**, **Daily at 02:00** (default),
**Weekdays at 08:00**, **Weekly, Monday 09:00**, or **Custom cron…** (five
fields, UTC). Scheduled runs use the Save that is current when they fire and
land in **Run history** like manual ones; **Run now** fires one immediately,
**Pause** / **Resume** stop and restart it. If a scheduled run fails, the
organization's owners get an email. On the Free plan the heading shows
**Requires Plus** in place of **Schedule a run** (tooltip "Schedules are
available from the Plus plan"); it opens **Billing** in the organization
settings. Full details: [[Schedules and Webhooks|Studio-Schedules-and-Webhooks]].

---

## Live mode

Tick **Live: recompute on new responses** in the Flow settings and Save. From
then on, new responses trigger a recompute of the flow about ten seconds after
they arrive (a burst of responses gives one recompute), and its **Live tile**
nodes refresh the **Live** screen. Each recompute is an ordinary run: it
appears in **Run history**, replaces the flow's files and reports, and uses
the plan's run time. Automatic recompute is a *Plus* feature; on Free you
refresh tiles by hand with **Recompute now** on the Live screen. Live tiles
are also refreshed by any ordinary run of the flow, with or without Live
mode. See [[Live Monitoring|Studio-Live-Monitoring]].

---

## Export Python

**More ▾ → Export Python** downloads `<flow>.py`, the script the engine
generated for this flow **at the current Save** — the exact file a run
executes. It is disabled for a new or edited flow (tooltip "Save first"). A
flow saved with engine errors has no script ("Download failed. No generated
code for this document."). What the script needs to run outside Studio is
explained in [[Reproducibility|Studio-Reproducibility]].

---

## Comments and working together

Comments attach to the flow (Flow settings → **Comments**) or to a node (its
inspector's **Comments**, with a count badge on the node). One person edits at
a time; the others follow live. See [[Working Together|Studio-Collaboration]].

---

## AI flow review

*(Plus; the assistant must be turned on for the organization.)* The **review**
link in the flows table asks a language model to read the **saved** flow for
analysis mistakes that pass the structural check — weights computed but never
applied, missing codes not cleared before a mean, a test that does not suit
the scale, duplicates not removed, results that reach no report. The panel
reads "**Assistant** `<flow>` · whether the analysis is sound, read by a
language model — suggestions, not rules · N credits, M left". Each finding
names a node, what is wrong and "Suggested: …" what to do. "Nothing to flag
across N steps." is a good answer. A flow with engine errors is not reviewed
("fix what the structural check reports first"). Only the flow and the
codebook are sent — no responses. A review typically costs about 7 credits.
See [[AI Assistant|Studio-AI-Assistant]].

---

## A worked example

*"Satisfaction by region, weighted, with a report."*

```
Simulated data (n 500, seed 42)
  → Dedup respondents (respondent_id, keep last)
  → Speeders & partials (min 90 s; required: age, region, satisfaction)
  → Missing values (to_nan)
  → Rake weights (region + gender to population shares)
  → Apply weight (weight)
      ├→ Banner table (satisfaction down × region across)
      ├→ Group means (satisfaction by region, test)  →  Bar chart (satisfaction by region)
      └→ Live tile (Show: rows, "Clean respondents")
                    ↓
            Report section ("Satisfaction by region", captions, base in the note)
                    ↓
            Save report (outputs/satisfaction.md, + HTML)
```

1. **+ New flow**, title "Satisfaction by region". Delete the starting
   **Responses** node and add **Simulated data** so you can build before
   fieldwork.
2. Add the Prepare nodes from the palette and wire each `data` output to the
   next node's `data` input.
3. Add the analysis and chart nodes, then switch to **Report** and **+ Add
   section**: it creates **Save report** and sets the flow's **Report path**.
   Add the banner, the means table and the chart as outputs and write the
   captions.
4. **Preview report**, then **Check**, then **Save changes**, then **▶ Run**.

On launch day, swap the source: nodes cannot change their type, so add a
**Responses** node, connect its `data` output to **Dedup respondents** (the
new wire replaces the old one), delete **Simulated data**, **Check**, Save.
Every table in the report now recomputes from real responses. The banner and
the **Group means** table use the applied weight (the means are weighted;
their N and test are not — see [Group means](Studio-Node-Reference#group-means)).
The **Bar chart** is drawn unweighted, so its bars can differ from the
weighted means in the table: say so in its caption, or leave it out of a
weighted report (see [Apply weight](Studio-Node-Reference#apply-weight)).

---

## Keyboard shortcuts

| Keys | Where | Action |
|---|---|---|
| `Delete` or `Backspace` | Canvas, List | delete the selected node |
| `Ctrl/Cmd + D` | Canvas, List | duplicate the selected node |
| `Ctrl/Cmd + Z` / `Shift + Ctrl/Cmd + Z` | Canvas, List | undo / redo |
| `Ctrl/Cmd + S` | anywhere in the editor | Save |
| `Ctrl/Cmd + Enter` | anywhere in the editor | preview up to the selected node (the whole draft when none is selected) |
| double-click a node | Canvas | preview up to it |
| `↑` / `↓`, `Enter` | List | move between nodes; preview up to the focused one |
| `Ctrl/Cmd + K` | List | open the node picker |

Delete, duplicate and undo are ignored while you type in a field, in the
Report view, and while a colleague holds the edit lock. See
[[Keyboard Shortcuts|Studio-Keyboard-Shortcuts]].

## See also

- [[Node Reference|Studio-Node-Reference]]
- [[Cleaning and Weighting Data|Studio-Cleaning-and-Weighting]]
- [[Reports|Studio-Reports]]
- [[Reproducibility: Code, Bundles and Citation|Studio-Reproducibility]]
- [[Schedules and Webhooks|Studio-Schedules-and-Webhooks]]

<!-- studio-nav -->
---

← [[Data Quality|Studio-Data-Quality]] · [Studio contents](Studio-Overview#all-pages) · [[Node Reference|Studio-Node-Reference]] →
