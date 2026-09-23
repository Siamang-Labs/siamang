# Tutorial: A Study from Start to Finish

This tutorial follows one realistic study through every stage of Studio — from
an empty project to a published report and a citable research bundle. It takes
about two hours the first time. Each part ends with a checkpoint, so you can
stop and come back.

**The study.** *Customer Pulse 2026*: a short satisfaction survey for the
customers of a regional service, fielded in three regions, with a consent page,
an age screener, an attention check, a Net Promoter Score, a satisfaction
rating and an open comment for unhappy customers. The analysis cleans the data,
weights it to the regional customer mix, tabulates satisfaction by region and
publishes a report and a live dashboard.

```
Part 1  Plan                     Part 5  Build the analysis on simulated data
Part 2  Build the questionnaire  Part 6  Pilot, pre-register, launch
Part 3  Make it look right       Part 7  Monitor fieldwork
Part 4  Test it                  Part 8  Report, close, archive
```

> **Before you start.** You need an organization on a plan that includes the
> features used here — the 30-day Pro trial covers all of them. Parts marked
> *(Plus)* need Plus or higher after the trial. See
> [[Plans, Trial and Billing|Studio-Plans-and-Billing]].

---

## Part 1 — Plan

Write down, before touching the Builder, what you need to be true of the data.
For this study:

| Decision | Choice |
|---|---|
| Who may answer | adults (18+) who agree to take part |
| Sample | 300 completed interviews, roughly 100 per region |
| Key measures | satisfaction (5-point), NPS (0–10) |
| Quality | one attention check; flag, don't drop |
| Weighting | to the known customer mix: North 45 %, Centre 30 %, South 25 % |
| Deliverables | a report with a weighted table and a chart, a live tile for the client, a research bundle |

Two naming rules make everything downstream easier:

- **Name variables for analysis** — `consent`, `age`, `region`, `satisfaction`,
  `nps`, `attention`, `comment`.
- **Keep each question's Id identical to its variable name.** Conditions,
  piping and quota counting find answers by variable name, and the data column
  is named after the Id; if the two differ, logic on that question silently does
  nothing. See [[The Builder|Studio-Builder-Overview]].

---

## Part 2 — Build the questionnaire

### Create the project

1. **Projects → New project**. **Name**: `Customer Pulse 2026`.
2. **Start from**: **Blank project** → **Create →**.

The Builder opens on an empty page. (A blank project starts at `warnings #1`
because its only page is empty — that disappears once you add questions.)

### Page 1 — consent

1. Select the page in the rail. In the Inspector (**Page**), set **Title** to
   *About this survey* and **Name** to `consent_page`.
2. **+ Question → Presets → Yes / No**. Set the **Question text** to
   *Do you agree to take part in this survey?* and turn **Required** on.
3. Open **Variable** and change the variable name to `consent` (press `Enter`).
   Then open **Advanced** and set **Id** to `consent` too.

> The Yes / No preset codes `1 = Yes`, `0 = No` and shows them as buttons.

Introductory text for respondents belongs on this page — but the page **Body**
is shown only on text-only, final and screen-out pages. Put the explanation in
the question's **Hint** instead: *The survey takes about five minutes. Your
answers are anonymous.*

### Page 2 — screener

1. **+ Page → Content page**. Title *About you*, name `screener`.
2. **+ Question → Types → Number**. Text *How old are you?*, **Required** on,
   **Unit** `years`. Variable name `age`, **Advanced → Id** `age`. In
   **Variable**, set **Min** `16` and **Max** `99`.
3. **+ Question → Types → Single choice**. Text *Where do you live?*,
   **Required** on. **Choices**: `1` North, `2` Centre, `3` South. Variable and
   Id `region`. Variable label *Region of residence*.

### Page 3 — experience

1. **+ Page → Content page**. Title *Your experience*, name `experience`.
2. **+ Question → Types → Likert scale**. Text *Overall, how satisfied are you
   with our service?* **Points** `5`, **Left label** *Very dissatisfied*,
   **Right label** *Very satisfied*. Variable and Id `satisfaction`.
3. **+ Question → Presets → NPS (0–10)**. Keep the standard wording. Variable
   and Id `nps`.
4. **+ Question → Presets → Attention check**. It is a required single choice
   (*…please choose "Rarely"*) already marked as an attention check with its
   expected answer. Variable and Id `attention`.
5. **+ Question → Types → Open text**. Text *You gave us {answer:nps} out of 10.
   What should we do better?* Turn **Multi-line** on. Variable and Id
   `comment`.

`{answer:nps}` is **piping**: the respondent sees the number they chose.

### The ending pages

1. **+ Page → Final page** — the thank-you page for completed interviews. Edit
   its **Title** and **Body** in the Inspector.
2. **+ Page → Screen-out page** — named `disqualification`, with the text *You
   do not qualify for this study.* Edit it if you like.

Check the order in the rail: `consent_page`, `screener`, `experience`,
`final`, `disqualification`. Drag pages to reorder if needed. Keep the
screen-out page **last**, after the final page — it is reached only by the
rules you add next.

### Routing

**Screen out non-consenters.** Select `consent_page`. In **Logic → Branch (next
if)** press **+ Rule**, then **Add condition**: **Variable** `consent`,
operator **=**, value **No (0)** → **Done**. Set the rule's target to
`disqualification`.

**Screen out minors.** Select `screener` and add a rule: `age` **<** `18` →
`disqualification`.

> A branch rule with an **empty** condition never fires, even though its
> placeholder reads "otherwise". Give every rule a condition and use **Default
> next** for "everyone else".

**Ask for a comment only from detractors.** Select the `comment` question.
**Logic → Show if → Add condition**: `nps` **≤** `6` → **Done**.

**Also screen out inattentive respondents?** For this study, no — we flag
them in the analysis instead. (The attention check's **Also end the survey
for respondents who fail** option would add a branch rule to the screen-out
page.)

### Check the routing

Open **Logic map**. The **Pages** lens should show
`consent_page → screener → experience → final`, with rule arrows from
`consent_page` and `screener` to `disqualification`. Switch to the
**Questions** lens: the `comment` row carries a `SHOW IF` chip reading `nps`,
and no arc is red (a red arc means a condition reads an answer given *later*).

### Quotas

Open **More ▾ → Quotas**. Next to "or one for every value of", pick `region`,
set the limit to `100` and press **Add 3 cells**.

> **Current limitation.** Quota cells are **counted and displayed** on
> Distribute and Live, but a full cell does **not** stop new respondents yet —
> only the environment's response cap does. Watch the bars during fieldwork
> (Part 7). See [[Quotas and Randomization|Studio-Quotas-and-Randomization]].

### Save

Press **Save changes**, message *Questionnaire v1*, **Save**. The badge should
read `● valid #2` or `● warnings #2`. If it says `errors`, open **Validation**
and fix what it lists.

**Checkpoint.** Five pages, seven questions, three quota cells, a valid Save.

---

## Part 3 — Make it look right

Open **More ▾ → Theme**.

1. **Appearance** — set a **Primary** color that matches your brand; read the
   contrast line under the colors (it turns red below the WCAG floor).
2. **Branding** — **Institution** *Customer Insights Team*. For a logo, paste
   a **Logo URL** from a stable public address (your website). Do not use a
   link from **Files** — those download links expire after a few minutes.
3. **Respondent experience** — fill **Contact email**, **Privacy URL** and the
   **Ethics statement**. They appear in the footer of every page.
4. **Wording** — optionally rephrase the runtime's fixed texts (buttons,
   saving and failure messages).

> **Current limitations.** Leave **Completion screen → Title** empty — setting
> it makes the questionnaire invalid; this study ends on its own Final page
> anyway. Published surveys currently show no progress bar whatever the
> **Progress** setting. **Estimated minutes** is not shown to respondents. See
> [[Theme and Branding|Studio-Theme-and-Branding]].

Switch the canvas to **Structure | Preview** and check both **Desktop** and
**Mobile**. **Save** (*Theme*).

---

## Part 4 — Test it

### Validation

Open **Validation**. The **Engine** section should report no errors (press
**Check now** after edits). Read every warning; lint remarks such as an
unused variable are fine if you understand them.

### Walkthrough — both paths

**Test → Walkthrough.** Take the survey as a consenting 35-year-old from the
North who is unhappy (NPS 4): the side panel should show `comment` evaluated
as shown. Restart and answer **No** to consent: the panel should report the
`consent_page` rule matching and routing you to `disqualification`. Restart
once more as a 16-year-old.

### Simulate

**Test → Simulate**: **Responses** `300`, **Seed** `42`, **Simulate**. Look at
the preview rows and the codebook, then download **SPSS** and open it: are the
variable and value labels right?

> Simulation follows page routing and screen-outs, but not block conditions,
> randomization, scripts or quotas.

### Share preview for reviewers

**Test → Share preview** creates a public link (copied automatically) that a
colleague or client can open without an account for 24 hours. Answers are not
stored. Collect wording comments; apply them; **Save**.

**Checkpoint.** Both routes behave; the simulated SPSS file is labeled.

→ [[Testing Your Survey|Studio-Testing-Your-Survey]]

---

## Part 5 — Build the analysis on simulated data

Build the whole analysis now, before the first real respondent arrives.

### Create the flow

**Flows → New flow**, **Title** *Satisfaction*, **Open canvas**. The canvas
starts with a **Responses** source; delete it for now (select it,
`Delete`).

### Wire the pipeline

Drag these nodes from the palette and connect each node's `data` output to the
next node's `data` input:

```
Simulated data ─▶ Response quality ─▶ Rake weights ─▶ Apply weight ─┬─▶ Banner table ┐
                        │                                             ├─▶ Bar chart ─┤
                        │                                             └─▶ Net Promoter Score
                        └──(table)───────────────────────────────────────────────────┤
                                                                                      ▼
                                                                          Report section ─▶ Save report
Apply weight ─▶ Live tile
```

Set the parameters:

| Node | Parameter | Value |
|---|---|---|
| **Simulated data** | **Respondents** · **Seed** | `300` · `42` |
| **Response quality** | **Attention checks** | use **Fill from the questionnaire** — it fills `attention` with its expected answer |
| | **Mode** | `flag` (adds `quality_flags` and `quality_score`, keeps everyone) |
| **Rake weights** | **Targets (variable → code → share)** | `{"region": {"1": 0.45, "2": 0.30, "3": 0.25}}` |
| **Apply weight** | **Weight column** | `weight` |
| **Banner table** | **Questions (down)** · **Breakdowns (across)** · **Significance letters** | `satisfaction` · `region` · on |
| **Bar chart** | **Variable** · **By** | `satisfaction` · `region` |
| **Net Promoter Score** | **0–10 item** | `nps` |
| **Report section** | **Heading** · **Text** | *Satisfaction by region* · a sentence of context |
| | **Captions** | one per connected item |
| | **Note** | *Base: all respondents, weighted by region.* |
| **Save report** | **Title** · **Path** | *Customer Pulse 2026* · `outputs/satisfaction.md` |
| **Live tile** | **Kind** · **Label** · **Show** | `number` · *Respondents so far* · `rows` |

Connect the Banner table's `table`, the Bar chart's `chart`, the NPS `table` and the
Response quality `table` (counts per quality flag) to the Report section's
`items` input in the order they should appear.

> **Why a Banner table and not a Crosstab?** Only some nodes use the weight
> that **Apply weight** sets: **Banner table**, **Net Promoter Score**,
> **Regression**, **TURF** and **Proportion CI** do; **Frequencies**,
> **Crosstab**, **Group means** and the charts currently ignore it. The bar
> chart here therefore shows the unweighted distribution — say so in its
> caption. See [[Cleaning and Weighting Data|Studio-Cleaning-and-Weighting]].

### Preview and check

- Select **Banner table** and press `Ctrl/Cmd + Enter` (**Run to here**) — the
  weighted table appears in the inspector, with column percentages, counts and
  significance letters.
- Press **Check** — the engine should report no errors. Fix anything it lists
  **before** saving: a flow saved with engine errors stops every run in the
  project and blocks publishing from that Save.
- Switch to **Report** view to write the words around the outputs and use
  **Preview report**.

**Save changes** (*Analysis v1*), then **Run**. The run appears in **Run
history**; the report appears on the **Reports** tab.

### Make the tile live *(Plus)*

With no node selected, the inspector shows **Flow** settings. Tick **Live:
recompute on new responses** and **Save**. New responses will re-run the flow
and refresh the tile.

**Checkpoint.** A saved, runnable flow and a report — all on simulated data.

→ [[Analysis Flows|Studio-Flows]] ·
[[Cleaning and Weighting Data|Studio-Cleaning-and-Weighting]] ·
[[Node Reference|Studio-Node-Reference]]

---

## Part 6 — Pilot, pre-register, launch

### Pilot

1. **Distribute → Publish** panel: **Target** `pilot` → **Publish to pilot**.
2. When the card shows **● Live**, **Copy** the link and send it to three
   colleagues. Answer it yourself on a phone.
3. Check **Data → responses**: are the columns what you expected? Is `comment`
   empty for promoters?
4. Fix anything you find in the Builder, **Save**, and press the **Republish #N**
   chip on the `pilot` card.

### Switch the analysis to real data

In the flow, drag in a **Responses** node, set **Environment** `main` and tick
**Only completed responses**. Connect its `data` output to **Response
quality** — this replaces the connection from Simulated data — then delete
**Simulated data**. **Check**, **Save**.

### Pre-register *(optional)*

**History** → open the latest Save → **More ▾ → Pre-register**. The Save is
tagged as the registered questionnaire and analysis plan; later Methods drafts
and bundle provenance report what changed since. For an external timestamp,
also **Deposit** it to Zenodo (Part 8 shows how).

### Launch

**Distribute → Publish** panel: **Target** `main` → **Publish to main**.
Share the `main` link: email it, print the **QR** code, or paste the **Embed**
snippet into your website.

> New projects cap `main` at **1,200** completed responses and `pilot` at
> **50**. When a cap is reached, further respondents are refused when they
> submit.

Alternative channels:

- a sample provider — [[Panel Providers|Studio-Panel-Providers]];
- personal email invitations with reminders *(Plus, after the first
  payment)* — [[Email Invitations|Studio-Email-Invitations]];
- restricted access with codes — [[Links, QR Codes, Embeds and Access Control|Studio-Distribution-Channels]].

**Checkpoint.** `main` is live; the analysis reads real responses.

---

## Part 7 — Monitor fieldwork

- **Distribute** tiles: **Responses · main** against the cap, **Completion**,
  **Median duration** (and speeders), **Quality screen** (share failing the
  attention check), **Today**.
- The `main` card: one bar per quota cell (`region=1 · 64/100`). When a region
  reaches its target, decide what to do — the cell will not close itself. A
  common move: add a branch rule on `screener` sending `region = North (1)` to
  `disqualification`, **Save**, and **Republish #N** on the card.
- **Drop-off** on the card: which page people abandon.
- **Live** tab: project totals, a responses-per-day chart and the flow's tiles.
  **Create public link** gives the client a read-only page with just the tiles
  *(Plus)*; **Revoke** it when the engagement ends.

→ [[Live Monitoring|Studio-Live-Monitoring]] · [[Data Quality|Studio-Data-Quality]]

---

## Part 8 — Report, close, archive

### Close the field

On the `main` card press **Close** → **Close survey**. Respondents now see
"This survey is closed". (**Reopen** would rebuild the same Save into the same
link.)

### Final run and report

**Flows → Satisfaction → Run**. On **Reports**, open the report and read it.
In the flow's **Report** view, the **Look** tab sets typeface, density, table
style and page size (`a4` for printing). Download **HTML** for the client or
use **Print / PDF**.

### Export the data

**Data → responses → Export ▾ → SPSS** gives a labeled `.sav` of the whole
table (all environments, partials included — filter on `survey_id` and
`partial`).

### Citation, bundle, deposit

1. **Settings → General → Study & citation**: title, authors (one per line:
   `Name; ORCID; affiliation`), license, keywords, abstract → **Save study
   metadata**.
2. **History** → open the final Save → **More ▾ → Methods**: a draft Methods
   section built from your documents; everything marked `[...]` needs you.
3. **More ▾ → Download a bundle → With the responses so far**: the study as a
   zip — questionnaire and flow code, documents, codebook, `METHODS.md`,
   `CITATION.cff`, `PROVENANCE.md` and the data.
4. **More ▾ → Deposit** *(needs a Zenodo token stored under **Settings →
   Secrets**)*: choose **Zenodo**, pick the token, **untick "Use
   sandbox.zenodo.org"** for a real DOI, decide on **Publish immediately**, and
   **Deposit**.

**Done.** The study, its analysis and its data are versioned, reproducible
and citable.

→ [[Reports|Studio-Reports]] ·
[[History and Versions|Studio-History-and-Versions]] ·
[[Reproducibility: Code, Bundles and Citation|Studio-Reproducibility]]

---

## What you practiced

| Skill | Where it is documented |
|---|---|
| Pages, presets, Ids and variables | [[The Builder\|Studio-Builder-Overview]], [[Question Types\|Studio-Question-Types]] |
| Branch rules, show if, piping, Logic map | [[Logic and Branching\|Studio-Logic-and-Branching]] |
| Quota cells and their current limits | [[Quotas and Randomization\|Studio-Quotas-and-Randomization]] |
| Theme and footer details | [[Theme and Branding\|Studio-Theme-and-Branding]] |
| Validation, walkthrough, simulation, share preview | [[Testing Your Survey\|Studio-Testing-Your-Survey]] |
| Flows, quality flags, raking, reports, live tiles | [[Analysis Flows\|Studio-Flows]], [[Reports\|Studio-Reports]] |
| Environments, pilot, launch, closing | [[Publishing and Environments\|Studio-Publishing-and-Environments]] |
| Pre-registration, bundles, deposits | [[History and Versions\|Studio-History-and-Versions]] |

## See also

- [[Quick Start|Studio-Quick-Start]]
- [[Recipes|Studio-Recipes]]
- [[Key Concepts|Studio-Key-Concepts]]
- [[FAQ and Troubleshooting|Studio-FAQ-and-Troubleshooting]]

<!-- studio-nav -->
---

← [[Key Concepts|Studio-Key-Concepts]] · [Studio contents](Studio-Overview#all-pages) · [[Sign Up and Sign In|Studio-Sign-Up-and-Sign-In]] →
