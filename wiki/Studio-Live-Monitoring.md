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
│   1,284          1,251           212 · 16.5%        6/4/2026, 2:41 PM                 │
│   responses      respondents     partial            last response                     │
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
| **responses** | every response row, **including partial interviews** |
| **respondents** | distinct respondent ids. Each finished interview gets its own id, so in practice this is close to **responses**; someone who answers twice counts twice |
| **partial** | interviews started and not submitted, with their share of all rows |
| **last response** | when the most recent row (partial or complete) arrived |

**Responses per day · last 14 days** charts all rows, partials included, by
the day they started. The chart is hidden while all fourteen days are zero.

The totals are loaded when you open the tab; open it again to update them.

### Live deployments

One card per environment that is **live** — a paused environment disappears
from this list until you resume it. Each card shows **● Live**, the
environment, the Save (`#17`), the publish time, the link, a **Responses** bar
against the environment's cap, and one bar per quota cell
(`region="north"` `240/400`). Cards refresh every 30 seconds while the tab is
visible.

An environment whose questionnaire deadline has passed still has a **● Live**
card here, although it no longer accepts responses; its counts simply stop
moving. See [Deadlines](Studio-Publishing-and-Environments#deadlines).

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
[Saving progress](Studio-Respondent-Experience#saving-progress)).

With nothing to show: "No partial responses recorded. The funnel fills in as
respondents leave a survey without submitting — from surveys published with a
runtime that reports it, so a wave published before this feature stays empty
until it is republished."

### Codebook

The **Codebook** chip lists the environment's variables (name, label, type) as
built in its **latest** build. For earlier versions of the questionnaire, open
the Save in [[History|Studio-History-and-Versions]].

### What each number counts

| Number | Where | Environment | Partials included? |
|---|---|---|---|
| Responses (tile, card bar) | Distribute, Live cards | one | **yes** |
| Completion | Distribute tile | one | completed ÷ all rows |
| Median duration, speeders | Distribute tile | one | completed only |
| Today, 14-day sparkline | Distribute tile | one | completed only |
| Quality screen | Distribute tile | one | completed only |
| responses, respondents, partial, per-day chart | Live tab | **all** | **yes** |
| Response cap | enforced at submit | one | completed only (screen-outs count) |

### Quota bars

Each quota cell shows `current/target` and a bar that stops at 100 %. Counts
advance once per completed response that falls in the cell; each environment
counts separately, so `pilot` never fills `main`'s cells. A cell counts the
answers of its variable whatever the question's Id is. Cells that had missed
answers stored under a question's Id — before Studio stored every answer under
its variable name — were recounted from the stored responses.

> **Current limitation.** A full quota cell does not yet stop new respondents.
> Counts can go past the target (the bar stays at 100 %). Watch the bars; when
> your cells are full, pause or close the environment, or lower its response
> cap. See [[Quotas and Randomization|Studio-Quotas-and-Randomization]].

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
- *(Plus)* **Automatic recompute.** After a completed response arrives, the
  live flows are re-run about **10 seconds** later; a burst of responses in that
  window causes one run, not fifty. Unfinished interviews do not trigger it.
  On Free the section header adds **· auto-recompute needs Plus**.

The tiles refresh on screen every 30 seconds, and every 8 seconds for three
minutes after **Recompute now**.

### Freshness and failed runs

Tiles always show the **last completed run** of their flow. If a later run
fails, the tiles keep the previous numbers — the **updated …** time tells you
how old they are, and the flow's run history shows the error. A table or chart
that could not be drawn shows a short error in the tile instead
("chart could not be rendered: …").

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
