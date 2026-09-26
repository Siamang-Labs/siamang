# Live Monitoring

Two screens watch fieldwork. **Distribute** shows each environment's numbers
on its card. The **Live** tab answers two questions for the whole project:
*how is fieldwork going right now?* and *what do my results look like so
far?* — the second through **live tiles** published by your analysis flows,
which you can also share with people outside Studio.

---

## The Live tab

```
┌ Live   fieldwork monitor · brand-awareness                  [Open data] [Distribute] ┐
│   1,284          1,003           212 · 16.5%        6/4/2026, 2:41 PM                 │
│   responses      completed       partial            last response                     │
│ ┌ Responses per day · last 14 days ──────────────────────────────────────────────┐   │
│ │            ▁▂▅▇▆▅▃                                                            │   │
│ └────────────────────────────────────────────────────────────────────────────────┘   │
│ Live deployments  2                                                                   │
│ ┌ ● Live  main  #17                                       6/4/2026, 9:00 AM ┐         │
│ │ https://study.siamang.org/3f9a1c07b2de/                                    │         │
│ │ Responses · 81%   ▓▓▓▓▓▓▓▓░░                                  972/1,200   │         │
│ │ region="north"    ▓▓▓▓▓▓░░░░                                  240/400     │         │
│ └────────────────────────────────────────────────────────────────────────────┘         │
│ Live tiles  2 flows with Live tile nodes                            [Recompute now] │
│ Share these tiles with people outside Studio …                  [Create public link] │
│ ┌ Fieldwork control room   fieldwork   live   updated 3 min ago · run #58 [Open flow →]│
│ │ [ Completes 972 ] [ Median minutes 6.2 ] [ Quota fill table ] [ Region chart ]    │
└───────────────────────────────────────────────────────────────────────────────────────┘
```

The header has **Open data** (the Data tab) and **Distribute**.

### Fieldwork totals

The strip at the top covers the **whole project** — all environments together:

| Number | What it counts |
|---|---|
| **responses** | every response row, **including partial and screened-out interviews**. Tooltip: "Every response row: completed, screened-out and partial interviews. Each interview counts on its own — Studio cannot tell whether two responses came from the same person." |
| **completed** | submitted interviews that did not end on a Screen-out page. Tooltip: "Submitted interviews that did not end on a screen-out page — what quota cells and response caps count. N screened out." |
| **partial** | interviews started and not submitted, with their share of all rows |
| **last response** | when the most recent row (partial or complete) arrived |

Someone who answers twice counts twice in every number: each interview is a
response of its own. To discourage repeat answers from one browser, see
[One response per browser](Studio-Distribution-Channels#one-response-per-browser).
Partial rows arrive only from surveys built with the current runtime; an
environment published earlier adds none until you
[republish](Studio-Publishing-and-Environments#republishing) it.

**Responses per day · last 14 days** charts all rows, partials included, by
the day they started. The chart is hidden while all fourteen days are zero.

The totals are loaded when you open the tab; open it again to update them.

### Live deployments

One card per environment that is **live** — a paused environment disappears
from this list until you resume it. Each card shows **● Live**, the
environment, the Save (`#17`), the publish time, the link, a **Responses** row
and one bar per quota cell (`region="north"` `240/400`). With an environment
cap, **Responses** shows the completed interviews against it (`972/1,200`,
with a bar and the percentage; the tooltip reads "972 completed interviews
count toward the cap of 1,200; 1,184 responses in all, partial and screened
out included"); without one, every response row. Cards refresh every 30
seconds while the tab is visible.

An environment past its closing date keeps a card here, marked **○ Closed**
(tooltip "Closed — deadline passed `<date>`"): it no longer accepts responses,
and its counts stop moving. To collect again, use **Extend** on Distribute.
See [Deadlines](Studio-Publishing-and-Environments#deadlines).

With nothing live: "Nothing is live — Deploy a Save to an environment and the
fieldwork monitor shows up here — responses, quota cells and the per-day
trend." with **New deployment**.

This part needs no configuration and works on every plan.

---

## Monitoring on Distribute

Each environment card on **Distribute** carries the same **Responses** and
quota bars plus **Last response `<time>`**, and the tiles row above the cards
adds completion, median duration, speeders, the quality screen and today's
count for the environment in the field. See
[The Distribute screen](Studio-Publishing-and-Environments#metric-tiles) for
the tiles and [[Data Quality|Studio-Data-Quality]] for the quality numbers.

### Drop-off by page

The **Drop-off** chip of an environment card shows where unfinished interviews
stopped: one bar per page, most abandoned first (**`page3` … 18 left**). It is
the funnel that tells you which page is too long or too intrusive. It counts
partial interviews by the last page they reached — progress arrives when a
respondent moves between pages or leaves the tab (see
[Saving progress](Studio-Respondent-Experience#saving-progress)). Respondents
whom a full quota cell stopped keep the partial row their progress had already
sent, so they usually show up on the page where they were stopped. Someone
stopped on leaving the first page usually leaves no row, because progress is
first sent when a respondent reaches the second page (or switches away from
the tab).

With nothing to show: "No partial responses recorded. The funnel fills in as
respondents leave a survey without submitting — from surveys published with a
runtime that reports it, so a wave published before this feature stays empty
until it is republished."

### Codebook

The **Codebook** chip lists the environment's variables (name, label, type) as
built in its **latest** build. For earlier versions of the questionnaire, open
the Save in [[History|Studio-History-and-Versions]].

### What each number counts

| Number | Where | Environment | What it counts |
|---|---|---|---|
| Responses (tile, card bar) | Distribute, Live cards | one | with an environment cap: completed interviews only; without one: every row, partials and screen-outs included |
| Completion | Distribute tile | one | submitted (screen-outs included) ÷ all rows |
| Median duration, speeders | Distribute tile | one | submitted only, screen-outs included |
| Today, 14-day sparkline | Distribute tile | one | submitted only, screen-outs included |
| Quality screen | Distribute tile | one | submitted only, screen-outs included |
| responses, partial, per-day chart | Live tab | **all** | every row, partials and screen-outs included |
| completed | Live tab | **all** | completed interviews only |
| responses total | Distribute header | all listed | completed interviews only |
| Response cap, quota cells | enforced: a cap as the page opens and at submit, a quota cell when the respondent leaves a page | one (Free plan cap: whole project) | completed interviews only — no partials, no screen-outs |

### Quota bars

Each quota cell shows `current/target` and a bar that stops at 100 %. Counts
advance once per **completed interview** that falls in the cell — screen-outs
and partial interviews do not count — and a Multiple choice kept as one
variable fills the cell of every value it holds. Each environment counts
separately, so `pilot` never fills `main`'s cells. A cell counts the answers of
its variable whatever the question's Id is. Erasing a response in **Data**
lowers the cells it had filled. When this counting came in, every cell was
recounted once from the stored responses, so cells that screen-outs had
inflated went down.

When a cell is full, the survey stops the respondents who fall into it as
they leave the page with that answer, on the quota-full screen; everyone else
goes on. Someone who passed the check earlier can still complete, so a count
can end slightly past its target (the bar stays at 100 %). This needs a survey
built with the current runtime: an environment published earlier lets
everyone through until you
[republish](Studio-Publishing-and-Environments#republishing) it. See
[When a cell is full](Studio-Quotas-and-Randomization#when-a-cell-is-full) and
[How cells are counted](Studio-Quotas-and-Randomization#how-cells-are-counted),
which also covers the cells that count only responses collected by the
current runtime (on a matrix row, or on one choice of a wide Multiple choice).

---

## Live tiles

Tiles are outputs of your analysis flows, published to the Live tab. A
dashboard is therefore a *view of your flow*, not a second thing to configure:
change the analysis, and the tiles change with it.

### Publishing a tile

1. In a flow, add a **Live tile** node and connect it to what you want on
   screen — a count, a table, a chart, a statistic.
2. Set its parameters:

   | Parameter | Options |
   |---|---|
   | **Label** | required — the tile's heading |
   | **Kind** | **number** (default), **table**, **chart**, **stat**, **text** |
   | **Show** | **value** (default) shows what is connected; **rows** shows the number of respondents in the connected data |

3. With no node selected, the inspector shows the **Flow** panel; check
   **Live: recompute on new responses** there.
4. **Save**, then **Run** the flow once.

The flow then appears under **Live tiles** with its tiles.

| Kind | Shows |
|---|---|
| **number** | one formatted number |
| **stat** | a list of named values (e.g. mean, sd, n) |
| **table** | the connected table |
| **chart** | the connected chart as an image |
| **text** | the value as text |

Numbers show up to three decimals; a number smaller than 0.001 — a p-value,
say — is written with its exponent (`2.35e-5`) rather than rounded to 0.

By default every tile takes one grid cell. Larger tiles can be set only in
the flow's document; there is no drag-to-resize on the Live tab.

### A flow's row

Each flow with Live tile nodes has a row: its title, a pill, the freshness,
the run number and **Open flow →**.

| Pill | Meaning |
|---|---|
| **live** | recomputed after new responses ("Recomputed after new responses") |
| **manual** | Live is on, but automatic recompute needs Plus ("Live is a Plus feature: recompute by hand") |
| **live off** | the flow has tile nodes, but **Live: recompute on new responses** is off ("Live is off for this flow — enable it on the canvas") |

Freshness reads **updated just now**, **updated 3 min ago**, **updated 2 h
ago**, then a date — or **not run yet**. A row without tiles says "No tiles
published yet — run the flow (or Recompute now) and its Live tile nodes fill
this row."

With no flow using tiles: "No live tiles yet. Add a Live tile node to a flow
and turn on Live on its canvas: after new responses the worker re-runs the
flow and its tiles land here."

### Recomputing

Every tile update is a full **run** of its flow — the same sandbox run as
**Run** in Flows, on the project's **current Save**, recorded in the flow's run
history. Recompute takes as long as the flow does: seconds for a few counts,
longer for weighting or models.

- **Recompute now** re-runs every flow whose Live is on (disabled otherwise:
  "Turn Live on for a flow first (canvas → Live: recompute on new
  responses)"). Toasts: **Recompute queued — tiles update when the runs
  finish**, or **A recompute is already pending**. Works on **every plan** —
  it is how Free projects refresh.
- *(Plus)* **Automatic recompute.** After a submitted response arrives, the
  live flows are re-run about **10 seconds** later; a burst of responses in that
  window causes one run, not fifty. Partial saves of unfinished interviews do
  not trigger it.
  On Free the section header adds **· auto-recompute needs Plus**.

The tiles refresh on screen every 30 seconds, and every 8 seconds for three
minutes after **Recompute now**.

### Freshness and failed runs

Tiles always show the **last completed run** of their flow. If a later run
fails, the tiles keep the previous numbers — the **updated …** time tells you
how old they are, and the flow's run history shows the error. A failed
recompute does not email the organization's owners (the "Scheduled analysis
failed" email is for schedules). A table or chart that could not be drawn
shows a short error in the tile instead ("chart could not be rendered: …").

Previewing a flow in the editor (**Run to here**, **Preview all**) never
changes its tiles, and a renamed flow keeps showing its latest tiles, on the
Live tab and on the public link. A new flow created under the name of one
that was renamed and then deleted is a flow of its own: it shows no tiles
until it runs, never the deleted flow's.

---

## Sharing tiles publicly

*(Plus)* A public link shows the tiles to anyone who has it — no account, no
access to the project, no raw data. The share bar appears once at least one
flow has Live tile nodes. On Free it reads "A public read-only link to these
tiles is a Plus feature." and the button is disabled.

### Create, copy, rotate, revoke

- **Create public link** → toast **Public link created**. The bar then shows
  the link, **Copy**, **Rotate**, **Revoke** and "**Anyone with this link can
  view these live tiles** — no Studio account, no sign-in. Created
  `<date, time>`. Revoke it when the study closes."
- **Rotate** issues a new address and revokes the old one:

  > **Replace the public link?** — "A new URL is issued for these tiles." —
  > "The current link stops working immediately. Anyone you have already sent
  > it to — in an email, a deck, a status page — sees a page-not-found until
  > you send them the new one." → **Replace link**

  Toast: **Link rotated — the old one is revoked**.
- **Revoke** ends public access:

  > **Revoke the public link?** — "These tiles stop being readable outside
  > Studio." — "Immediate and one-way: this URL can never be re-enabled.
  > Anyone holding it sees a page-not-found, and creating a link again gives a
  > different address." → **Revoke link**

  Afterwards the bar notes "Link revoked `<time>`. Anyone who kept it now sees
  a page-not-found. A new link gets a different address."

### What viewers see

The public page (`https://studio.siamang.org/live/<token>`) shows the project's
name, "live tiles · updated …", and for each flow its title, its **updated …**
time and its tiles — no pills, run numbers or links into the project. The
footer reads "Shared from Siamang Studio · read-only · refreshes
automatically"; the page refreshes every 30 seconds while it is open.

| Viewer sees | When |
|---|---|
| "Nothing published yet." | no flow has published tiles |
| "This live page does not exist or its link was revoked." | the link was revoked or rotated, the address is wrong, or the organization's plan no longer includes Live |
| "Could not load the live page." | a temporary problem; the page keeps trying |

### Rules

- **One link per project.** Creating a new link revokes the previous one.
- **No expiry.** A link works until you rotate or revoke it. If the
  organization drops below Plus, the page shows "does not exist…" until the
  plan is restored.
- Any member of the organization can create, rotate and revoke the link.
  Creating and revoking are recorded in the project's activity log.
- Treat the link like a password, and never publish a tile that could
  identify a respondent (small cells, open answers, ids).

---

## Practical patterns

**Fieldwork control room.** Tiles: completed count (**Show: rows** on the
cleaned data), completion rate, median duration, quota fill by region as a
table. Watch the first day; fix the screener if the funnel is wrong.

**Client dashboard.** Tiles: the three headline charts from your report, plus
an "n = …" number tile. Share the public link; it updates as the field runs
(on Plus, automatically).

**Sanity checks.** A frequency tile for each screener variable catches routing
mistakes within the first fifty interviews — far cheaper than discovering them
at analysis.

## See also

- [[Publishing and Environments|Studio-Publishing-and-Environments]]
- [[Analysis Flows|Studio-Flows]]
- [[Node Reference|Studio-Node-Reference]]
- [[Data Quality|Studio-Data-Quality]]
- [[Reports|Studio-Reports]]

<!-- studio-nav -->
---

← [[What Respondents See|Studio-Respondent-Experience]] · [Studio contents](Studio-Overview#all-pages) · [[Responses and the Data Tab|Studio-Responses-and-Data]] →
