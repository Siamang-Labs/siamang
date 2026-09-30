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
- A flow is checked on its own: one that fails the engine's check cannot run
  until it is fixed, but it does not stop the questionnaire from being
  published or the other flows from running (see
  [A flow with errors](#a-flow-with-errors)).

> **Note.** Flows run against a Save. A project that has never been saved
> shows "This project has no Save yet — flows run against a Save. Save the
> project first." with an **Open Builder** button.

---

## The Flows screen

```
Flows  Load → Clean → Analyze → Report · run history          [More ▾] [+ New flow] [▶ Run flow]

Flows  6 · one document each under flows/
┌───────────────┬───────────────────────────────────────┬──────────────────────────────────┬───────────────────────────────────┬──────────────┐
│ Flow          │ Description                           │ Last run                         │ Report                            │              │
│ cleaning      │ 1. Clean raw responses                │ ● Sep 23, 2026, 9:14 AM · 0m 11s │ outputs/data_quality.md           │ review run ⋮ │
│ tables        │ 2. Key tables                         │ ● Sep 23, 2026, 9:12 AM          │ outputs/key_tables.md             │ review run ⋮ │
│ usage         │ 3. Screen use                         │ ● Sep 23, 2026, 9:12 AM          │ outputs/screen_use.md             │ review run ⋮ │
│ wellbeing     │ 4. Wellbeing: scales and drivers      │ ● Sep 23, 2026, 9:12 AM          │ outputs/wellbeing.md              │ review run ⋮ │
│ wellbeing_app │ 5. The app: features, reach and price │ ● Sep 23, 2026, 9:12 AM          │ outputs/app_features_and_price.md │ review run ⋮ │
│ segments      │ 6. Segments                           │ ● Sep 23, 2026, 9:12 AM          │ outputs/segments.md               │ review run ⋮ │
└───────────────┴───────────────────────────────────────┴──────────────────────────────────┴───────────────────────────────────┴──────────────┘

Pipeline  the order Run all runs them · a flow after the flows whose tables it reads
   ● cleaning ── ● tables ── ● usage ── ● wellbeing ── ● wellbeing_app ── ● segments

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
per flow, in the order **Run all** runs them — a flow after the flows whose
tables it reads, alphabetical where that leaves a choice (see
[Run all](#run-all)):

| Column | Shows |
|---|---|
| **Flow** | the flow's name (its file name), with a red **errors** pill when the flow did not pass the engine's check at the current Save (see [A flow with errors](#a-flow-with-errors)) and an amber **cycle** pill when it and another flow read each other's tables (see [Flows that read each other's tables](#flows-that-read-each-others-tables)); hover a pill for the details |
| **Description** | the flow's title (or description) |
| **Last run** | status dot, start time and duration ("0m 34s") of the flow's latest finished run — started by hand, by a schedule or by Live — or of the latest **Run all** that ran it, whichever is newer; "running" while a run of the flow is in progress; "never" when the flow has not finished a run since the last **Reset history** |
| **Report** | the flow's **Report path**, or "—" |

**Last run** comes from the server, so it survives a reload of the page, and
it is read again when a **Run all** you started finishes. A **Run all** counts
for each flow it ran, with that flow's own outcome (a green
dot for a flow that succeeded, red for one that failed or was skipped) and the
time the Run all started, but no duration: the Run all times its flows only
as a whole. The screen above is the example study after a **Run all** at
09:12, followed by a run of `cleaning` on its own at 09:14.

Click a row to open the flow on the canvas. On the right:

- **review** — asks the AI assistant to read the flow for analysis mistakes
  (see [AI flow review](#ai-flow-review)). Click it again to close the panel.
- **run** — runs the flow (disabled while it is already running, and for a
  flow with errors: "Fix this flow's errors and save first").
- **⋮** ("More for *flow*") — **Rename…**, **Duplicate…** and **Delete…**;
  see [Rename, duplicate or delete a flow](#rename-duplicate-or-delete-a-flow).

With no flows: "**No flows yet.** The example study ships six to read; start
your own with **New flow**." (See
[The example study's flows](#the-example-studys-flows).)

### Pipeline

The strip shows every flow as a chip with the status of its latest run —
the same run as its **Last run** in the table, a **Run all** that ran it
included, and a blinking dot while a run of the flow is in progress — in the
same order as the flows table, the order **Run all** runs them. Its
sub-title reads "the order Run all runs them · a flow after the flows whose
tables it reads". Click a chip to open the **Run flow** dialog with that flow
selected.

### The Run flow dialog

| Field | Content |
|---|---|
| **Flow** | the flow to run, in **Run all** order; the hint gives its place in that order, e.g. "step 2 of 3 — runs after cleaning" or "step 1 of 3 — runs first" ("flows run against the current Save" when the project has one flow). "runs after" names every flow before it in the order, not only the flows whose tables it reads |
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
│ ● success   flow   #412                      Sep 23, 2026, 9:13 AM     │
│ ✓ Queued ── ✓ Run ── ✓ Done      ran in 0m 34s                        │
│ tables · Save #17                                                      │
│ [key_tables.md  5.7 KB] [key_tables.html  199 KB] [key_tables.xlsx …] │
│ › View logs                               [Re-run] [Open flow →]      │
└───────────────────────────────────────────────────────────────────────┘
```

| Part | Content |
|---|---|
| Status | **success**, **warnings**, **failed** or **running** |
| Type | **flow**, **run all** or **connector** (open-answer coding jobs also appear, as **flow**) |
| `#id`, time | the run number and when it started |
| Steps | **Queued → Run → Done** with "ran in 0m 34s"; a Run all shows one step per flow, in the order of the flows table (the order it runs them), each marked as that flow finishes (a cross for a flow that failed or was skipped) |
| Entry | the flow name (or script path) and "· Save #N" — the Save it ran |
| Error line | for a failed run, the last line of its log (for example the Python error), or "Run failed — open the logs for details." For a failed Run all it is the summary line "failed: *flows*", followed by "; skipped: *flows*" when some were skipped — **View logs** shows every flow's outcome and error |
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
2. Type a **Title** (placeholder "Satisfaction by region"). **File name**
   fills in from it (`satisfaction_by_region`), and its hint shows where the
   flow is saved ("saved as flows/satisfaction_by_region.flow.json; Rename
   flow changes it later"). The name is the title spelled in Latin letters, as
   a project's address is ("Удовлетворенность клиентов" becomes
   `udovletvorennost_klientov`), in lowercase, with every run of other
   characters turned into `_` and leading digits dropped; with nothing left,
   it is `flow`. When a flow or connector already has that name, Studio adds
   `_2`, `_3` and so on. Type over the file name to choose another; one that
   breaks the rules below says so under the field (for a taken one, "A flow or
   connector named *name* already exists.").
3. **Open canvas →**. The new flow starts with one **Responses** node (id
   `src`), and **More ▾** reads "Analysis flow · new, not saved yet · …" until
   you save.
4. Build it, then **Save changes**. Only now does the flow exist, under the
   title you typed. From that Save on it is an ordinary saved flow: **▶ Run**,
   **Export Python**, **Rename flow…** and **Duplicate flow…** are available
   at once, and the address in the browser ends in the flow's name.

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

A Save that would exceed the cap is refused with "the Free plan allows up to 3
analysis flows per project; this Save would have 4 — delete one or upgrade". A
project that is already over the cap (after a downgrade) can still be saved as
long as the number of flows does not grow — a rename, for example, does not
add one. Deleting a flow frees its place. A project started from the example
study begins with its six flows on every plan, so on Free it is such a
project: its flows run and can be edited, and a new flow can be added once
fewer than three are left.

---

## Rename, duplicate or delete a flow

Each of these is an ordinary Save of its own: it gets a number in History,
the plan's flow cap applies to it, and restoring an earlier Save undoes it.
They are in two places:

- the **⋮** at the end of a row in the flows table ("More for *flow*"):
  **Rename…**, **Duplicate…**, **Delete…**;
- the editor's **More ▾** menu: **Rename flow…**, **Duplicate flow…**,
  **Delete flow…**.

In the editor, **Rename flow…** and **Duplicate flow…** are disabled while
the flow is new or has unsaved changes (tooltip "Save first"); **Rename
flow…** and **Delete flow…** are also disabled while a colleague holds the
edit lock ("*Name* is editing"). **Delete flow…** on a flow that was never
saved says "Not saved yet — All flows discards it".

### Rename

The dialog **Rename *flow*** reads: "A new Save stores the flow under the new
name. Its schedules and comments move with it, and Live keeps showing its
latest tiles; its past runs and reports keep the old name. Restoring an
earlier Save moves them back."

1. Type the new name in **Name**. The hint shows where it will be saved
   ("saved as flows/*name*.flow.json") or what is wrong with the name: "Give
   the flow a name.", "Use lowercase letters, digits and _, starting with a
   letter (at most 63).", "\"survey\" is the questionnaire's name." or "A flow
   or connector named *name* already exists."
2. **Rename** ("Saving…" while it works), or **Cancel**.

What follows a rename:

| Thing | After the rename |
|---|---|
| The flow document | stored as `flows/<new>.flow.json`; the old file is gone from the new Save. History records "Rename flow *old* to *new*" |
| Its default report path | a **Report path** and **Save report** path that were `outputs/<old>.md` become `outputs/<new>.md`; a path you chose yourself stays |
| Schedules | move to the new name, still active or paused as they were |
| Comments | move with the flow (the flow's and its nodes') |
| Live | the Live screen and a public Live link keep showing the flow's latest tiles until its next run |
| Past runs and reports | keep the old name: the run cards, and the reports under `outputs/<old>/` in **Reports** and **Files**. **Last run** reads "never" until the flow runs under its new name |

Restoring a Save from before the rename brings the flow back under its old
name, and moves its schedules (keeping their state) and comments back with
it.

Live and Restore follow a rename only into the flow that got the new name
from it. Say you rename *tables* to *summary*, delete *summary*, and later
create a new flow called *summary*: the new flow is a flow of its own. Live
shows no tiles for it until it runs (never the deleted flow's), and
restoring a Save from before the rename brings *tables* back without taking
anything from the new *summary* — its schedules and comments stay with it,
the schedules paused, as for any flow a Restore removes.

Rename always takes the flow **as it is saved now** — including a
colleague's newer Save — not the copy your tab loaded. It is refused while
you have unsaved changes to that flow: "*flow* has unsaved changes. Open it
and save them (or undo them) first: renaming saves the last saved version,
and the changes would be lost." It is also refused while a colleague has the
flow open: "*Name* is editing *flow*; it can be renamed once they are done."

### Duplicate

The dialog **Duplicate *flow*** reads: "A new Save adds a copy of the saved
flow under a new name. Schedules are not copied." The name offered is
`<name>_copy` (then `<name>_copy_2`, …) and the copy's title is "*title*
(copy)". The same name rules apply as for a rename; the button is
**Duplicate**. The copy is taken from the flow as it is saved now, and its
default report path follows its new name, so the copy does not write over
the original's report. History records "Duplicate flow *name* as *copy*".
A duplicate counts toward the plan's flow cap. From the editor, the copy
opens once it is saved.

### Delete

The confirmation **Delete *flow*** reads: "A new Save removes
flows/*flow*.flow.json. Its past runs and reports stay, its schedules are
paused, and restoring an earlier Save on the History screen brings the flow
back." From the editor, with unsaved changes, it adds that it "discards your
unsaved changes". Confirm with **Delete flow**. History records "Delete flow
*flow*". A flow a colleague has open cannot be deleted: "*Name* is editing
*flow*; it can be deleted once they are done."

Restoring an earlier Save
([History → Restore](Studio-History-and-Versions#restore-an-earlier-version))
brings a deleted flow back; its schedules stay paused until you **Resume**
them. A Restore that removes flows pauses their schedules too.

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
│ › Prepare 16 │                                   ↓               │ Preview   ▶ Run to here│
│ › Analyze 26 │                              [Save report]        │ Connections            │
│ › Visualize 7│                                                   │ Comments               │
│ › Output   8 │   [+ − ⤢]                              minimap    │ Checks 0 errors · …    │
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
| **More ▾** | "This flow" status line — "Analysis flow · edited · 9 nodes · 10 edges · no issues" and the file path; the draft-sync status; **Export Python**; **Rename flow…**, **Duplicate flow…**, **Delete flow…** (see [Rename, duplicate or delete a flow](#rename-duplicate-or-delete-a-flow)) |
| **▶ Run** | runs the flow as of the current Save; disabled for a new or edited flow (tooltip "Save first") and for a flow that failed the engine check at the current Save ("Fix this flow's errors and save first") |
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
**Output**, each with a count — 4, 16, 26, 7 and 8, 61 nodes in all. Only
**Sources** is open at first; the groups you open stay open in this browser.
The search box **Find node…** matches the title, the short name and the
description, and also the labels of a node's parameters and the choices they
offer, with their names — so "tukey" finds **Group means**, "wilcoxon" and
"cochran" **Paired tests**, "kendall" **Correlation**, **Correlation matrix**
and **Heatmap**, "shapley" **Key drivers**, "gabor" **Price sensitivity**,
"stacked to 100", "donut" and "histogram" the **Bar chart**, "iso week" the
**Trend** and "tab book" or "banner" the **Tab book (Excel)** — and opens every
group with a match. The
List view's node picker (`Ctrl/Cmd + K`) searches the same way.
Each item shows the title and a short name (`crosstab`), plus `· platform` for
nodes that need the project database. Hover an item for its description.

- **Click** an item to add the node to the right of the last node.
- **Drag** an item onto the canvas to drop it where you want.

A new node gets an id from its short name (`crosstab`, then `crosstab_2`, …)
and its parameters' defaults. A **Save report** node added from the palette
also starts with the project's report house style, when it has one, as its
**Look** (see
[[Reports|Studio-Reports]]).

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
  sections, a **Result chart**'s result — an analysis's table and its
  statistics) keep them in the order you connect them — for the report nodes,
  the order in the report.
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
| **Report path** | the report file this flow declares (placeholder `outputs/report.md`); **Run all** puts this file into the combined report — and counts the flow as failed when the file was not written — and the flows table and **Run flow** dialog show it. It follows the **Save report** node's **Path** when you change that (see [The combined report](#the-combined-report)) |
| **Live: recompute on new responses** | Live mode (see [Live mode](#live-mode)) |
| **Preview run** | the last preview's summary ("last run: 7 nodes ok") and **Preview all**, which previews the whole draft |
| **Comments** | comments on the flow as a whole |

**With a node selected:** its category and title with an **ⓘ** for what the
node does, **Duplicate (⌘D)** and **Delete (Del)** icons, its own problems,
**Node id**, the
parameters (only those its current choices read — see
[Parameters and variable pickers](#parameters-and-variable-pickers)), the
**Instant** counts where available, the **Preview** pane with
**Run to here**, **Connections** (what feeds it and what it feeds, each with
**remove**) and **Comments**.

What a node does and what each parameter means sit behind the **ⓘ** beside
the node's title and beside each label, rather than printed under it: hover
over it, or click it to keep it open (Esc or a click elsewhere closes it). A
screen reader reads the same text with the control. Printed in full, the help
set how far apart the controls were — a crosstab's settings ran past the
bottom of the screen.

Below the inspector, the **Checks** block lists the flow's problems ("Checks
2 errors · 0 warnings", up to twelve); click one to select its node.

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
reference). Variable parameters are dropdowns or checklists, shown as
`name — label` and filtered to the scales the node accepts (the scales are
the hint under the field, unless the field has help text of its own, as a
t-test's **Groups** does). They offer, in this order:

- the questionnaire's codebook variables;
- the variables that nodes **upstream** of this one make — a **Recode**,
  **Derive**, **Index / scale**, **Bands**, **Explode multiple choice**,
  **MaxDiff scores**, **Cluster (k-means)**, **Factor analysis** (with **Add
  factor scores** checked), **Code open answers** (its **Theme variable**, or,
  left empty, the name its codeframe carries), **Response quality**,
  **Speeders & partials** or weighting node earlier in the flow. Their label
  says so: "*label* · made by *node*", or "made by *node*" when the node gives no
  label (`duration_s` reads "completion time · made by *node*", `partial`
  "partial response · made by *node*", `factor_1` "factor 1 score · made by
  *node*", `q_md_score_3` "MaxDiff score: *item* · made by *node*"). A node
  further down the flow does not offer them: they do not exist yet when it
  runs;
- the variables brought by a table the flow reads (see
  [Tables between flows](#tables-between-flows)), labeled "from table
  *table* · made by *flow*".

The same list is behind the **Filter rows** condition editor and the
variable names listed under a formula. A stored name that is in none of
these shows as "(not in codebook)". In **Filter rows** the value pickers show
value labels — `Capital region (1)` — so you pick the meaning, not the code.

Where a node asks for an **answer** of a variable — a **t-test**'s **Group
A** and **Group B** (answers of **Groups**), **Paired tests**' **Counts as
yes (McNemar, Cochran's Q)**, a **Perceptual map**'s **Counts as yes
(attributes)**, **Price sensitivity**'s **Counts as would buy**,
**Proportion CI**'s **Answer code**, a **Trend**'s **Answer codes** — the
field lists that variable's value labels (`1 — Male`; for a list of
variables, the first one's), including the bands a **Bands** node made; the
t-test's groups and the Trend's codes leave its missing codes out.

A field that can read columns the codebook does not describe lists them last,
under **Beside the answers**: a **Trend**'s **Time** offers the timestamps the
survey's responses carry — `created_at — Response date (created_at)`,
`updated_at — Last change (updated_at)` and `started_at — Start time
(started_at)` — and the checks know them. A flow that reads them from a **Data
file** or **Simulated data**, which have none unless the file brings the
column, gets a warning. **Time** lists **Waves and dates** first (labeled
codes, ordinal variables, date columns, a Date question's answers), then
**Other variables**.

A picker leaves out what its node refuses as soon as it is picked: a
**Trend**'s **Time** and **Split by** and a **Bar chart**'s **Split by** do not
offer multiple-choice questions, rankings or open answers, and a **Trend**'s
**Measure variable** with **Measure** `mean` does not offer nominal or
multiple-choice questions. A variable already stored stays in the list, with
the reason: `aware (several answers: not one wave or date)`.

A few text fields suggest values as you type:
a **Bar chart**'s **Bins** (`auto`, `10`, `0, 18, 25, 35, 50, 65`) and a
**Heatmap**'s **Color map** (`theme` beside four matplotlib maps). **MaxDiff scores** lists the questionnaire's
MaxDiff questions. Mappings, weighting targets and other codes are typed as JSON
(`{"1": 0.45, "2": 0.55}`); an empty JSON box shows the example its help
gives.

**The inspector follows the node's choices.** A node that runs different
tests shows only the fields the chosen one reads — a **t-test**'s **Groups**,
**Group A**, **Group B** and **Variances** with **Design** `independent`, its
**Second measurement** with `paired`, its **Test value** with `one_sample`. A
field you filled in that the current choices do not read is named under the
others, and kept for when they apply: "Not used with these choices, and kept
for when they apply: **Groups** (with Design = independent)." — with a
**Clear it** link (**Clear them** for several; focus then moves to the field
whose choice hid them). The note says each field's choices as simply as they
go ("**Show** (with Layout ≠ donut)"), and brackets a part of several choices
when there is another: "**Confidence intervals** (with (Show = count and Sort
= code and Layout ≠ histogram and Layout ≠ donut) or Layout = grouped)". A value kept that way is not checked and does not stop
the flow — the run ignores it, and so does the engine's check at Save. A field
a choice needs is
marked required. A choice whose code is shorthand shows its name beside it
(`welch_anova — Welch's ANOVA`) — the node's own name where one code means
different things in two nodes: `ordinal` reads `ordinal — ordinal logit,
ordered answers` in a **Regression**'s **Model** and stays a scale in a
**Recode**. See
[Reading this page](Studio-Node-Reference#reading-this-page) in the node
reference for the full list.

**A Result chart's Kind** says under it what the connected analysis suits and
what `auto` draws — "Group means (means.table) suits means — means with 95 %
intervals; means_sd — means ± 1 SD. Auto draws means." — and marks the other
kinds "(not for this result)". Before anything is connected it reads "Connect
an analysis's table (or Proportion CI's stat) to see the charts it suits."
See [Result chart](Studio-Node-Reference#result-chart).

### Checks

Studio checks a flow twice:

- **As you edit**, on the canvas: required parameters, compatible wires,
  cycles, nodes not fed by any source, variables of the wrong scale, and
  variables that are neither in the codebook nor made by a node of the flow
  or brought by a table it reads — "variable: \"q99\" is neither in the
  codebook nor made by this flow or a table it reads." These light the nodes
  and fill the **Checks** block. A codebook variable of the wrong scale is a
  red error here, as it is for the engine — for example 'y: "brands" is
  nominal; this node expects ordinal/interval/ratio.' One that a node of the
  flow makes is a warning, as in the engine, and the flow still runs:
  'row: "factor_1" is interval (as fa makes it); this node expects
  nominal/ordinal.' Its scale is the one the nearest node upstream that makes
  it gives it — a Recode of a derived variable is ratio like its source,
  whatever order the nodes were added in — and the variable pickers offer it
  with that scale. An experimental arm that an **Assign to a condition** script
  writes counts as a codebook variable, nominal, even when the codebook does not
  list it. A **Filter rows** condition edited by hand is checked as the engine
  will write it: "condition: every part of a condition must be a comparison or
  a variable (built with the editor)." and "condition: every variable in a
  condition needs a name." are errors. So are choices of one node that do
  not go together, in the node's own words (`PARAM_CONFLICT`): "Tukey's HSD
  follows a one-way ANOVA — set Test to anova, or Post-hoc to none." is an
  error — the node cannot run that way — and "Post-hoc is not run while
  Significance test is off." a warning, naming a setting the node would
  ignore. Each node's rules are listed in the
  [[Node Reference|Studio-Node-Reference]].

  What the engine settles before any data is named here too, in its words: a
  **Result chart** fed an output it cannot draw (`RESULT_NOT_DRAWABLE`), a
  **Kind** the connected result does not suit (`RESULT_KIND`, naming the
  output that does draw it) or results of two analyses (`RESULT_SOURCES`, a
  warning); **Likert chart** items on two scales ("The items of a Likert chart
  must share one scale, and these do not: …"), with several answers or with no
  scale; a **Bar chart** split by, or stacking, a question that allows several
  answers, a histogram of a question with answers, a donut of a
  multiple-choice question, a **Split by** equal to its **Variable** and
  **Bins** it cannot read ("bins: The bins' edges must increase from one to
  the next, and 5 is followed by 3."); a **Trend**'s mean of a nominal or
  multiple-choice question, a multiple-choice **Time** or **Split by**, and a
  missing code among its **Answer codes** ("9 (Refused) is a missing code of
  Trust: Acme, not an answer: …"); a **Tab book (Excel)** whose **Path** is no
  workbook, or whose banner holds a multiple-choice question (and, as
  warnings, a **Path** outside `outputs/` or a ranking or open answer named
  in its **Questions**); a **Save report** whose **Look** names chart colors
  the engine refuses ("theme: chart_text_color: '#cccccc' on the charts' white
  background has a contrast of 1.6:1; text needs at least 4.5:1."); an ordinal
  **Regression** of a nominal outcome (`VARIABLE_SCALE`:
  "Region is nominal: its answers (Capital, North, South) have no order, …");
  **Key drivers** with fewer than two drivers, or more than 15 with Shapley; a
  **Perceptual map** with one attribute; **Price sensitivity**'s prices that do
  not match their questions; **Paired tests** with a number of variables its
  test cannot compare ("Cochran's Q compares three or more yes/no variables; 2
  were given. For two, use McNemar.").
- **With the engine**, when you press **Check**, when you preview and when you
  Save. The banner says "**Engine check: valid.** The engine can generate and
  run this flow." — or lists each problem by node. The engine's verdict is the
  one that counts. Studio tells the engine which response timestamps its
  responses carry (`created_at`, `updated_at`, `started_at`, not
  `submitted_at`) and adds four checks of its own: a step's text
  that is not one line (the error `PARAM_LINE_BREAK`, see
  [One-line texts](Studio-Node-Reference#reading-this-page)), a data source
  naming a table or environment no project can have (the errors
  `SOURCE_TABLE_NAME` and `SOURCE_ENVIRONMENT_NAME`), a **Report path**
  that no **Save report** step writes (the warning `REPORT_PATH_UNWRITTEN`,
  see [The combined report](#the-combined-report)), and a response timestamp
  read from a **Data file** or **Simulated data** (the warning
  `RESPONSE_TIME_SOURCE`, see [Trend](Studio-Node-Reference#trend)).

**Press Check before you Save**, and fix what it reports: a flow the engine
rejects is saved, but it cannot run.

### A flow with errors

A flow that fails the engine check at Save is still saved — without a
generated script — and only that flow is affected:

- The Save counts as **warnings**, not **error**. Its questionnaire can be
  published, and the project's other flows, **Run all** and previews go on
  working.
- The Save toast names it: "Saved #18 — flow tables has errors and cannot run
  until fixed" (several: "Saved #18 — flows cleaning, tables have errors and
  cannot run until fixed").
- The flows table shows a red **errors** pill next to its name. Its tooltip
  reads "Did not pass the engine check at the current Save, so it cannot run.
  Open it, fix these and save:" followed by one "• *node*: *message*" line per
  error.
- Its **run** link and the editor's **▶ Run** are disabled ("Fix this flow's
  errors and save first"). Starting it any other way is refused with "flow
  'tables' did not pass the engine check at Save #18: open it, fix its errors
  and save before running it".
- Opening it shows a banner above the canvas: "**This flow did not pass the
  engine check at the current Save, so it cannot run.** Fix these and save:
  *node*: *message* · …"
- In **Run all**, and in a schedule that fires for it, the flow fails with
  "flow 'tables' did not pass the engine check at Save #18, so it has no
  script to run: open it, fix its errors and save". The other flows run,
  except those that read a table it writes (see [Run all](#run-all)).
- **Export Python** has nothing to download for it.

A flow the engine itself fails on is such a flow too — a fault of the engine,
not of your flow, logged on the server for whoever maintains it. Its issue
reads "The engine failed while checking this flow (*error*); it has no code and
cannot run until the engine is fixed or the flow is changed", or "The engine
could not write this flow's code: *reason*" when the code generator refuses
something the check let through. It is stored like any flow with errors, so it
does not stop a Save of the questionnaire or of the other flows; **Check** and
a preview show the same issue.

Fix it, press **Check**, and Save: the next Save gives it a script again.

**Connections Studio repairs.** An earlier version of Studio saved an output
added with **+ Add output** in the **Report** view in a form the engine
rejects, so every check, preview and run of that flow failed with
"edges/*N*/from: Additional properties are not allowed ('title', 'type' were
unexpected)". Opening such a flow repairs its connections, and a banner says
"**Studio repaired this flow's connections.** An earlier version saved them in
a form the engine rejects, so the saved flow cannot run. Save changes to keep
the repair." Click **Save changes**, and the flow runs again.

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
| **Table** | a frequency table, crosstab, group-means table, banner, coefficient table, t-test, correlation matrix, factor loadings, key drivers, a perceptual map's dimensions, rows and columns, price points and curves, a Trend's points… |
| **Chart** | a bar chart (a histogram and a donut too), box plot, heatmap, Likert chart, scatter plot or trend, or the Result chart of an analysis |
| **Stat** | a test result or a set of statistics (χ², Fisher, t, Kruskal-Wallis, Wilcoxon, Cochran's Q, a correlation, a confidence interval), or what a Tab book wrote |
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
| table | the table (first 50 rows), with its statistics under it (a number below 0.0001 keeps four significant digits and its exponent there too, `p = 1.304e-09`). Its p-values are written as the house style's **P values** says (**Settings → Reports**; see [P values](Studio-Reports#p-values)) — at **< 0.001**, `< 0.001` in a p column and `p < 0.001` under the table — in the first 50 rows of a longer table, the node's other tables and a bare table alike. A node with several tables shows them all, the others each under its output's name: the **pairs** of Friedman or Cochran's Q under **Paired tests**, the **variance** and **correlations** tables under **Factor analysis**'s loadings, the **variance** under **Principal components**, the **rows** and **columns** under a **Perceptual map**'s dimensions, the **curves** under **Price sensitivity**'s price points (an empty one, such as the pairs of a two-variable test, is left out). The post-hoc pairs of **Group means** print under its means table |
| chart | the rendered chart — the picture a run draws, a chart of **Palette** `theme` in the look of the flow's **Save report**, its note's p (a **Result chart** of a t-test) as the house style's **P values** says. A **Trend** shows the table of its points under the picture. A chart that cannot be drawn (a Likert chart of items without a scale, a Result chart of a result it cannot draw) fails its own node, with the reason, not the report after it |
| stat | the statistics as a list of names and values. A number below 0.0001 is written with four significant digits and its exponent, as the table's footer writes it — a p of `1.132e-24`, not 0. A number below 1 that four significant digits hold is written as it is — a **Paired tests** p of `0.002343`, a **Bartlett p** of `0.00227` — as the footer writes it too. Every number reads as the footer writes it: a whole number the engine keeps as a decimal keeps its `.0` (a Welch t-test's `df` of `8.0`, the `n` of a Spearman correlation), a count has none, and thousands take a comma. A p below the threshold of the house style's **P values** reads as the bound, `< 0.01` |
| report | the report as rendered, with a **Rendered \| Markdown** switch in the Report view |
| table write | what a run would do, without doing it: "Not written: a preview never writes project tables. A run writes 812 rows to table 'clean_responses' (if it exists: replace)." |
| tab book | the **Tab book (Excel)** runs and shows its statistic (**Workbook**, **Sheets written**, **Questions skipped**, …) with "Not kept: a preview never keeps the files nodes write. A run writes outputs/tabbook.xlsx." |
| file, tile | "This node has no preview (its output is a file or a table write)." |

A preview is written when it runs, so after you change the house style's
**P values**, run the node again to see its p-values in the new setting.

A node that failed shows its error; nodes after it show "Not reached by the
last preview run." When you change a node, it and everything after it turn
**stale** ("changed since — run again") until the next preview. A failed node
also raises the message "Preview: *ids* failed — see the node".

**A preview writes nothing.** It does not appear in **Run history**, keeps no
files, and does not touch **Reports**, **Live** or the project's tables:

- A **Write table** node in a preview is recorded, not executed — the table
  other flows and the **Data** screen read stays as it is, and the node's
  Preview pane says what a run would write.
- What other output nodes write (an **Export file**, a **Save report**, a
  **Tab book (Excel)**) is discarded when the preview ends; only the previews
  shown in the inspector remain.
- **Live** keeps showing the tiles of the flow's latest completed real run;
  a preview does not blank them.
- The report preview has no provenance footer — that is added by real runs,
  while **Settings → Reports → End every report with the provenance footer**
  is on.

A preview reads what a run reads: the project's data, and the files uploaded
under **Files** that a **Data file** node names (`assets/<name>`).

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
different variables) connected **directly** to a **Responses** node that
reads the `responses` table also shows an **Instant** panel: the counts
straight from the responses table, refreshed as you change the parameters,
without a preview run and without using your preview allowance. It reads
"counting…", then "live" (or "unavailable").

The counts are exactly the rows the Responses node keeps. The pill names its
environment — **SQL · main**, or **SQL · main, completed** with **Only
completed responses** checked (tooltip "Counted by the server straight from
the responses table — no sandbox run") — and the note under the counts says
the same in words: "Counts what this source keeps: main's responses and any
rows no deployment claims (imported or sample data), partial ones included."
(", completed only" in place of ", partial ones included" when **Only
completed responses** is checked). The counts are always **unweighted**,
since the node is fed by the source directly. For a multiple-answer question
the panel notes that percentages are of the respondents who answered. A
Responses node that reads another table shows no Instant panel.

---

## Running a flow

**▶ Run** in the editor, **run** in the flows table, the **Run flow** dialog
or **Re-run** on a card runs the flow's generated script **as of the current
Save**, in an isolated sandbox, and records a run. The project's **Settings →
Activity** records who started it (`run.start`) and how it ended
(`run.completed` or `run.failed`, with `—` as the person). A flow can have one
run in progress at a time ("This flow already has a run in progress — see Run
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
for example "script timed out (300s) — the Free plan allows 5 min per flow run;
Plus allows 15 min". A run may also write at most 1 GB of files ("script
exceeded the sandbox disk budget (1024 MB written) and was stopped"). A run
stuck without any sign of life for 40 minutes is marked failed ("[reaper] run
timed out and was marked failed"), and the project's Activity gets a
`run.failed` entry with `"reason": "timed out"` in its details (not for a
Live recompute).

**Uploads a flow reads.** Before the sandbox starts, Studio copies in the
files uploaded under [[Files|Studio-Files]] that the project's flows name by
their path, `assets/<name>` — the **File** (and **Dictionary (JSON)**) of a
**Data file** node. Other uploads are not copied. When one cannot be, the log says
why before the script runs: "note: assets/panel.csv is not among this
project's Files", "note: assets/panel.csv is listed under Files but its
content is gone" or "note: uploads cannot be read (*reason*)"; the node that
reads it then fails with the path it looked for.

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
- in **Reports**, when they are `.md` or `.html` files — and a report's
  tables in Excel (`<name>.xlsx` beside it) as its **Excel** download, and
  each **Tab book (Excel)** workbook as a **Tab book** of its own;
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
   is followed by "skipped: needs cleaning, which failed". A flow that fails
   the engine check at Save counts as failed here ("… so it has no script to
   run …", see [A flow with errors](#a-flow-with-errors)).
3. **A missing report is that flow's failure.** When a flow runs but the file
   its **Report path** names was not written, the flow is marked failed with
   "report outputs/tables.md was not written: the flow's Report path names a
   file none of its nodes saves — set it to the Path of its Save report
   node". Its script did run, so the flows that read its tables still run.
   The Save already warns about such a flow (see
   [The combined report](#the-combined-report)).
4. **Once every flow has had its turn**, Studio writes the **combined
   report**. If any flow failed or was skipped, the run ends as **failed**,
   and the combined report holds the flows that succeeded, marked incomplete
   (see [The combined report](#the-combined-report)). **View logs** lists each
   flow as ok or failed, with each failed flow's error under it — one Run all
   names every broken flow, not only the first. The log's last line sums it
   up: "failed: tables" or "failed: tables; skipped: charts".

A project can have one Run all in progress at a time ("A run-all is already in
progress — see Run history").

> **Note.** Running a single flow never runs the flows it reads from; it reads
> their tables as they are.

### Flows that read each other's tables

Flows that read each other's tables in a circle (each needs a table the other
writes) cannot be put in order. Studio warns at Save: each flow of the circle
gets the warning "Flows cleaning and tables read each other's tables, so Run
all cannot put them in order: it runs them one after another in alphabetical
order, and each reads what the others wrote on an earlier run." (with three
or more: "Flows a, b and c …"), and the flows table marks them with an amber
**cycle** pill that shows the warning. **Run all** repeats it as the second
line of its log ("warning: flows cleaning, tables read each other's tables; no
order satisfies them, so they run one after another in alphabetical order").

Run all takes such a circle when nothing else can go, runs its flows in
alphabetical order, and then runs the flows that read what the circle wrote —
they still come after it. Break the circle (let one flow write a table the
other does not read back) to get a meaningful order.

### What Run all keeps

- The **combined report**, with its `.html` twin and figures.
- **Each successful flow's report** — its `.md`, the `.html` twin (when
  **Also save HTML** is on), the workbook of its tables (`<name>.xlsx`, when
  **Also save tables to Excel** is checked) and the figures the `.md` names —
  stored as soon as that flow finishes, under `outputs/<flow>/` in **Files**
  and on **Reports**, where a single run of the flow stores it. It replaces
  the flow's previous report there. Run all runs the flows in one working
  copy, so two flows may save to the same default `outputs/report.md`: a
  flow keeps only the twins its own **Save report** writes, never another
  flow's workbook or HTML left under that name.
- **Each successful flow's tab books** — the workbook every **Tab book
  (Excel)** node writes under `outputs/` — stored the same way.
- **What each flow's Live tile nodes published** — its tiles and the charts
  they show — so **Live** shows the tiles of this Run all (see
  [[Live Monitoring|Studio-Live-Monitoring]]).
- **The other files a flow's document declares as its outputs** — the list
  under `outputs.files` in `flows/<name>.flow.json`. The example study's
  flows declare their HTML twins, the R bundle of the cleaned data
  (`clean_responses.R`, `.csv` and `.dictionary.json`) and the MaxDiff choice
  data with its R script for hierarchical Bayes; a flow built on the canvas
  declares none.
- The tables its **Write table** nodes write, as in any run.

The tiles and the declared files are stored under `outputs/<flow>/` in
**Files**, where a single run of the flow stores them, and listed on the Run
all's card — each only when that flow wrote it during this Run all, so a file
an earlier flow left under the same name is never taken for another's. Other
files the flows write under `outputs/` — an **Export file** of a flow built
on the canvas, say — are not kept by Run all: run the flow on its own (or
schedule it) for those. Open the reports from **Reports**.

### The combined report

The combined report is titled with the questionnaire's title (the example
study's reads *Digital Life & Wellbeing 2026*; "Combined report" when the
questionnaire has none). It has a **Contents** list and one chapter per flow
that declares a **Report path**: the chapter is headed with that report's
own title, the flow's title stands under the heading, and the report's
sections follow one heading level down. The provenance footer (while
**Settings → Reports** has it on) comes once, at the end, rather than after
every chapter. It is written to `reports/report.md`
with an `.html` twin in the project's report house style — the twin carries
its figures inside it, as a flow's own HTML does — and appears on **Reports**
with a **combined** badge. The path can be changed in **Settings →
Reports**; the badge follows it.

The sections follow the order in which the flows ran. A flow without a
**Report path** is left out. Keep the **Report path** equal to the **Save
report** node's **Path**. Studio keeps them together where it can: the Report
view sets both when it creates the node, changing that node's **Path** in the
inspector (or clearing it back to the default `outputs/report.md`) moves the
**Report path** along, and deleting the node clears the **Report path** it
set. A **Report path** you pointed elsewhere yourself is left alone. When the
**Report path** names a file no **Save report** node of the flow saves — typed
by hand, or saved that way before — **Check** and the Save warn: "The flow's
Report path is “outputs/tables.md”, but no Save report step saves there: Run
all will fail this flow. Set it to the Path of a Save report step, or clear
it."

**After a failure** the combined report is still written from the flows that
succeeded, its title marked incomplete — *Digital Life & Wellbeing 2026
(incomplete)*, or **Combined report (incomplete)** for a questionnaire
without a title. Its first section,
**Missing from this report**, reads "This Run all did not finish every flow,
so this report has only the sections of the flows that did. Not in it:",
then one line per flow — "**tables** — failed: *reason*" or "**charts** —
skipped: needs tables, which failed" — and "Fix them and run all flows again
for the complete report." The log says "combined report (incomplete):
reports/report.md". It replaces the previous combined report on **Reports**.
When none of the flows that succeeded has a report, no combined report is
written and the previous one stays. See [[Reports|Studio-Reports]].

---

## Schedules *(Plus)*

**Schedule a run** on the **Schedules** heading runs a flow — or **Run all
flows (in dependency order)**, the order described in [Run all](#run-all) —
on a timer: **Every 30 minutes**, **Hourly**, **Daily at 02:00** (default),
**Weekdays at 08:00**, **Weekly, Monday 09:00**, or **Custom cron…** (five
fields, UTC). Scheduled runs use the Save that is current when they fire and
land in **Run history** like manual ones; **Run now** fires one immediately,
**Pause** / **Resume** stop and restart it. A schedule never starts a run
beside one that is still going: while the flow's previous run (for a Run all
schedule, a Run all) is queued or running, it waits, and fires at the
scheduler's first check (once a minute) after that run ends — late rather
than twice at once. If a scheduled
run fails, the organization's owners get an email. A renamed flow keeps its
schedules; a deleted one's are paused (see
[Rename, duplicate or delete a flow](#rename-duplicate-or-delete-a-flow)). On the Free plan the heading shows
**Requires Plus** in place of **Schedule a run** (tooltip "Schedules are
available from the Plus plan"); it opens **Billing** in the organization
settings. Full details: [[Schedules and Webhooks|Studio-Schedules-and-Webhooks]].

---

## Live mode

Check **Live: recompute on new responses** in the Flow settings and Save. From
then on, new responses trigger a recompute of the flow about ten seconds after
they arrive (a burst of responses gives one recompute), and its **Live tile**
nodes refresh the **Live** screen. Each recompute is an ordinary run: it
appears in **Run history**, replaces the flow's files and reports, and uses
the plan's run time. A recompute that fails sends no email (a failed
scheduled run does); it shows in **Run history**. Recomputes are not listed in
**Settings → Activity**. Automatic recompute is a *Plus* feature; on Free you refresh tiles by hand
with **Recompute now** on the Live screen. Live tiles are also refreshed by
any ordinary run of the flow, with or without Live mode, and by a **Run all**
in which the flow ran; the Live screen shows the tiles of the newest of
these. Previews do not change them. See
[[Live Monitoring|Studio-Live-Monitoring]].

---

## Export Python

**More ▾ → Export Python** downloads `<flow>.py`, the script the engine
generated for this flow **at the current Save** — the exact file a run
executes. It is disabled for a new or edited flow (tooltip "Save first"). A
flow saved with engine errors has no script ("Download failed. No generated
code for this document."). What the script needs to run outside Studio is
explained in [[Reproducibility|Studio-Reproducibility]].

---

## Tables between flows

A **Write table** node saves its data as a project table; another flow reads
it with a **Project table** node (or a **Responses** node whose **Table**
names it). The table keeps the variables of the columns it holds — labels,
scales and value labels — so a variable the writing flow made (a recode, a
derived variable, an index, a cluster, the quality flags) arrives in the
reading flow labeled, can be picked in its nodes ("from table *table* · made
by *flow*"), and passes the engine check at Save. **Run all** runs the writing
flow first. A table last written before tables kept their variables arrives
without those labels: run the writing flow once more to store them. A
multiple-choice question kept as one variable, and a ranking, come back as
the lists they were, as the **Responses** node gives them, so **Explode
multiple choice** (and the **Paired tests** or **TURF** after it) and a
**Tab book (Excel)** read them in the reading flow too.

Until the writing flow has run once, the table does not exist, and the
reading flow's **Project table** node stops — in a preview and in a run —
with "The table clean_responses does not exist yet: it is written by 1. Clean
raw responses. Run that flow (or Run all) first, then this one." (the title
of the flow whose **Write table** node writes it; "…: a flow's Write table
node makes it." when no flow of the project does). The nodes after it then
read "not reached". A new example project is in this state until you run
`cleaning`. The recipe is in
[Cleaning and Weighting Data](Studio-Cleaning-and-Weighting#writing-the-cleaned-data-to-a-table).

---

## Comments and working together

Comments attach to the flow (Flow settings → **Comments**) or to a node (its
inspector's **Comments**, with a count badge on the node). One person edits at
a time; the others follow live. Comments move with a renamed flow. See
[[Working Together|Studio-Collaboration]].

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

## The example study's flows

A project started from the example study (see
[The example study](Studio-Projects#the-example-study)) comes with six flows
that between them use most of the palette on its sample responses. Each is
about a dozen nodes with a report of its own; their titles are numbered in
the order **Run all** runs them, and the node ids named below are on the node
cards. Every report section says how its numbers were made, never what they
are — the same flow run on your own fieldwork gives other numbers — and
every **Save report** uses the example's Look, so the six reports and the
combined one look alike. All six pass **Check** without an issue.

Run `cleaning` first, or all six with **More ▾ → Run all flows**: the other
five read the table it writes (and `segments` the one `wellbeing` writes),
and until it has run they stop at their first node (see
[Tables between flows](#tables-between-flows)).

> **Plan.** The six flows come with the project on every plan. On Free, which
> allows 3 flows per project, you can run, edit, rename and delete them, but
> a Save that adds a flow is refused until fewer than three are left (see
> [Creating a flow](#creating-a-flow)).

### 1. Clean raw responses (`cleaning`)

From the completed interviews to an analysis-ready, weighted table.

| Node | What it shows you |
|---|---|
| `src` **Responses** | **Environment** `main` and **Only completed responses** on: the sample rows, which no deployment claims, count as `main`'s, and break-offs never reach the analyses |
| `check` **Data check** | the answers against the codebook, off to the side of the pipeline — a table, not a filter. It finds the commutes outside 0–240 and leaves them in the data for you to decide on |
| `dedup` **Dedup respondents** | one row per `respondent_id`, keeping the last |
| `speed` **Speeders & partials** | **Minimum seconds** `240` (four minutes, in a survey of about ten), **Drop partials** on, **Required answers** gender, age group and life satisfaction |
| `bands` **Bands** | the typed age in the three age groups (`16-29`, `30-44`, `45+`) as `age_band`, for the consistency check |
| `quality` **Response quality** | **Mode** `drop`: straightlining down the eleven statements of the two matrices (the attention check aside), the age group asked against `age_band` (**Answers that must agree**), the attention check (expected answer `2`, Disagree), and duplicates — the same grid answers plus the six answers under **Duplicates also match on** (age, gender, area, employment, life satisfaction, hours on screens), so that two strangers who answered the grids alike are not dropped as one person |
| `rake` **Rake weights** | illustrative population shares of age group, gender and area, each weight capped at 5 |
| `write` **Write table** | `clean_responses`, the table the other flows read |
| `export` **Export file** | `outputs/clean_responses.R`: the cleaned, weighted data for R, with its `.csv` and dictionary |
| `tile_n`, `tile_quality` **Live tile** | *Clean respondents* (**Show** `rows`) and *Quality checks* (the quality table); **Live: recompute on new responses** is on |
| `weights`, `weighted` → `age_mix` | **Descriptive statistics** of the weight by age group, and **Apply weight** → **Frequencies** of age group: what the weighting did |

Its report, *Data quality*, has two sections. **Checks and cleaning** gives
what the data check found and the responses that failed each quality check,
with the funnel under the tables: *Checked* (the completed interviews),
*Screened* (those left after the speeders) and *Clean* (those left after
the quality checks). **Weighting** gives the weights in each
age group, and each age group's weighted share beside its respondents, with
Kish's effective N — what the weighting costs in precision.

### 2. Key tables (`tables`)

The tables a client asks for first, weighted.

| Node | What it shows you |
|---|---|
| `src` **Project table** → `weight` **Apply weight** | `clean_responses`, with every table after it weighted |
| `sat` **Frequencies** | life satisfaction, weighted count and % beside the respondents, and the effective N |
| `band` **Derive** → `xtab` **Crosstab** | seven answers by three age groups leave cells too thin for a chi-square test, so `life_band` first puts the answers in three bands (`1-3`, `4-5`, `6-7`); **Percentages** `row`, the test on the effective base |
| `chart` **Bar chart** | mean life satisfaction by age group, with **Confidence intervals** |
| `missing` **Missing values** → `banner` **Banner table** | Prefer not to say and Not applicable become blanks, so they get no column or row; four habits down, age group and gender across, with significance letters |
| `tabbook` **Tab book (Excel)** | fourteen questions named in **Questions**, by age group, gender and area, in `outputs/tabbook.xlsx`. They are named because, left empty, the tab book would also take in the eight feelings and the thirteen MaxDiff variables; and the banner's own variables are left out, since crossed with themselves they give 100 % and 0 % |
| `code` **Code open answers** → `themes` **Result chart** | the open answers coded with `analysis/improve.codeframe.json`, **Also add sentiment** on, and a chart of the themes and their tone |

Its report, *Key tables* (**Also save tables to Excel** on), has the
sections **Life satisfaction** and **Habits by group, and one change in their
own words**.

### 3. Screen use (`usage`)

Charts of a number and of time, a test of four yes/no answers from the same
people, and a map.

| Node | What it shows you |
|---|---|
| `hist` **Bar chart** | **Layout** `histogram` of hours a day, in two-hour **Bins**, % of each age group in a panel of its own |
| `trend` **Trend** | the weekly mean of hours a day (**Time** `created_at`, **Period** `week`) over the ten weeks of fieldwork, with its confidence band — drawn low and wide (7.5 × 3.4 inches), so it also fills the tile below |
| `tile_trend` **Live tile** | the same chart as a tile, *Screen time by week*: `trend`'s `chart` goes both to the report section and to the tile. Live is off, so the tile changes when the flow runs |
| `explode` **Explode multiple choice** → `manage` **Paired tests** | the four ways of managing screen time as 0/1 columns, compared with Cochran's Q (**Test** `cochran`), each pair by McNemar with Holm's adjustment |
| `map` **Perceptual map** → `map_chart` **Result chart** | **Table** `attributes`: each respondent's kind of app against the eight feelings, so that each kind of app lands near the feelings its users name more often than average |

Its report, *Screen use*, has the sections **How much, and over the weeks**
and **Managing it, and the apps it goes to**.

### 4. Wellbeing: scales and drivers (`wellbeing`)

Two scales, and what goes with life satisfaction. Nothing here is weighted:
the scales, factors and models describe how the answers hang together, and
the report says so.

| Node | What it shows you |
|---|---|
| `recode` **Recode** | "I feel anxious about unread messages" reversed into `calm`, so that the five items run the same way |
| `index` **Index / scale** | `wellbeing_index`, the mean of the five |
| `alpha` **Scale reliability** | Cronbach's alpha, with each item's corrected item-total correlation and the alpha without it |
| `likert` **Likert chart** | the six phone statements (the attention check left out) |
| `factor` **Factor analysis** | **Factors** `2` — fixed, not left to a rule, because the regression below reads both scores and on other answers a rule could keep one — **Rotation** `promax`, sorted, loadings under 0.3 hidden, scores `digital_1` and `digital_2` |
| `drivers` **Key drivers** → `drivers_chart` **Result chart** | life satisfaction on sleep, waking rested, focus, calm, feeling in control and hours on screens: each one's share of R² |
| `ordinal` **Regression** | **Model** `ordinal`: life satisfaction on the index, the two factor scores, hours and age group, with odds ratios, N and McFadden's pseudo-R². Age group enters as one slope across its three groups, as the section and the table's notes say |
| `write` **Write table** | `scored_responses`: the clean data with the index and the scores, for `segments` |

Its report, *Wellbeing*, has the sections **Two scales** and **What goes with
life satisfaction**.

### 5. The app: features, reach and price (`wellbeing_app`)

What people want from the app idea, how many a shortlist reaches, and what it
should cost.

| Node | What it shows you |
|---|---|
| `maxdiff` **MaxDiff** | the eight features from most to least important: times shown, best, worst, score, utility and share |
| `explode` → `turf` **TURF** → `turf_chart` **Result chart** | the features people would use, as 0/1 columns; the best shortlist of one, two and three features and how many people it reaches — which need not be the most important features. The chart names the features |
| `framing` **t-test** | interest in the app by `message_arm` (Welch's t): the two arms compared as they were drawn, unweighted |
| `recommend` **Net Promoter Score** | the 0–10 recommendation question |
| `price` **Price sensitivity** → `price_chart` **Result chart** | Van Westendorp: the four price points, the range of acceptable prices and the curves, from those whose interest was 3 or more |

Its report, *App features and price*, has the sections **What people want
from it** and **Framing, recommendation and price**.

### 6. Segments (`segments`)

Three kinds of user, from `scored_responses`.

| Node | What it shows you |
|---|---|
| `cluster` **Cluster (k-means)** | three clusters on hours a day, social media use, feeling in control and restlessness without the phone (standardized); **Number clusters by** hours a day, fewest first, so the names below stay with their clusters even when two come out at close sizes |
| `segment` **Derive** | names the clusters *Intentional*, *Balanced* and *Always on* — names given after reading their profiles, to be read again on other answers |
| `means`, `ranks` **Group means** | the wellbeing index by segment (ANOVA with Tukey's pairs) and life satisfaction, a rating, by its ranks (Kruskal-Wallis with Dunn's pairs); both before the weight, so the means printed with the tests are the ones compared |
| `weight` **Apply weight** → `sizes` **Bar chart** | **Layout** `donut`: the segments' weighted sizes |
| `profile` **Descriptive statistics** | **Layout** `means`: a column per segment with each variable's weighted mean, a compact profile |
| `scores` **MaxDiff scores** → `wants` **Heatmap** | each respondent's score for each feature, and each segment's mean scores as a heatmap |
| `hb` **Choice data for HB** | `outputs/app_md_choices.csv` with its dictionary and an R script for a hierarchical Bayes estimate, which gives each respondent utilities of their own |

Its report, *Segments*, has one section, **Three kinds of user**.

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
      ├→ Group means (satisfaction by region, test)
      ├→ Bar chart (satisfaction, by region)
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
The **Bar chart** with **By** draws the weighted means too — its axis reads
"Weighted mean *label*" — so its bars match the table. What else is weighted,
and what says it is not, is listed under
[Apply weight](Studio-Node-Reference#apply-weight).

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
