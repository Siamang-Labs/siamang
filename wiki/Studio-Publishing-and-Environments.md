# Publishing and Environments

**Distribute** is where a Save becomes a live survey. This page covers
environments, the Distribute screen, publishing and republishing, rolling back,
pausing and closing, failed builds, preview deployments and response caps. For
the ways you hand the link out — QR codes, embeds, access codes, captcha — see
[[Links, QR Codes, Embeds and Access Control|Studio-Distribution-Channels]].

---

## Environments

An **environment** is a named publishing target. Each environment has:

- its own permanent survey link (`https://study.siamang.org/<survey-id>/`);
- its own optional response cap;
- its own quota counters, drop-off funnel and codebook.

Every new project — empty, from a template or from the example — starts with
two environments:

| Environment | Response cap | Use it for |
|---|---|---|
| `pilot` | **50** | a test wave: colleagues, a soft launch |
| `main` | **1,200** | the real fieldwork |

The caps matter: with the defaults, `main` refuses submissions after 1,200
completed responses (see [Response caps](#response-caps)).

Environments are declared in the project's `studio/settings.json`. An
environment name must start with a lowercase letter and may contain lowercase
letters, digits and hyphens (up to 63 characters); names must be unique. A cap,
when set, is a whole number of at least 1. If a project declares no
environments at all, Distribute offers `pilot` and `main` without a cap of
their own (the plan's cap still applies).

### Changing environments

**Settings → Environments** lists the environments and their caps read-only,
with the note: "Editing environments in the UI arrives in phase 1; until then
edit studio/settings.json via a Save." In the beta there is no screen that
edits them. To change a cap or add an environment (`wave2`, `fr`,
`internal`, …), a changed `studio/settings.json` has to be saved as a new
Save, which today means using the [[API|Studio-API-and-API-Keys]]. If that is
not practical for you, contact support with the project and the caps you need.

A changed cap takes effect when you next publish that environment.

---

## The Distribute screen

```
┌ Distribute   2 environments · current Save #17 ─── [More ▾] [Preview] [New environment] ┐
│ ┌Responses · main┐┌Completion┐┌Median duration┐┌Quality screen┐┌Today┐   ┌ Publish ─────────┐ │
│ │ 247 / 1,200    ││ 78%      ││ 6:10          ││ 3%           ││ +31 │   │ Current  #17 ●valid│ │
│ │ ▓▓▓░░░░░░      ││ drop-off…││ 12 speeders   ││ 7 of 240 …   ││ ▂▃▅▇│   │ Draft    no unsaved│ │
│ └────────────────┘└──────────┘└───────────────┘└──────────────┘└─────┘   │ Target  [main ▾]   │ │
│ ┌ ● Live  main  #17  published 6/4/2026, 2:32 PM         [Pause] [Close] ┐ │ [Publish to main]  │ │
│ │ study.siamang.org/3f9a1c07b2de/                             [Copy]     │ ├────────────────────┤ │
│ │ [QR] [Embed] [Access codes] [Captcha] [Panel] [Drop-off] [Codebook]    │ │ Download the survey│ │
│ │ [Build log]                                                            │ │ as a Python program│ │
│ │ Responses · 21%   ▓▓░░░░░░░░                         247/1,200         │ │ [questionnaire.py] │ │
│ │ region="north"    ▓▓▓░░░░░░░                          90/400           │ └────────────────────┘ │
│ └────────────────────────────────────────────────────────────────────────┘                        │
│ ┌ ○ Closed  pilot  #12  closed 6/1/2026 …                        [Reopen] ┐                        │
│ └──────────────────────────────────────────────────────────────────────────┘                        │
│ Email invitations …                                                                                │
└────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Header

- The subtitle shows how many environments the project has been published to
  and the current Save (`current Save #17`, or `unsaved`).
- **More ▾** holds **Show archive** / **Back to current** and **Reset history**
  (see [Reset history and the archive](#reset-history-and-the-archive)).
- **Preview** builds a staged, non-collecting copy of the current Save
  ([Preview deployments](#preview-deployments)). It shows **Building…** while
  it starts.
- **New environment** opens the **New deployment** dialog
  ([Rolling back](#rolling-back-with-new-deployment)).

### Metric tiles

When at least one environment is live or paused, a row of tiles summarizes it
— `main` if it is in the field, otherwise the first live environment. The tiles
refresh every 30 seconds while the tab is visible, and again when you come back
to the tab.

| Tile | What it shows |
|---|---|
| **Responses · `<env>`** | every response row of that environment, partial interviews included, against its cap, with a bar; **no cap** when there is none |
| **Completion** | completed ÷ all rows, as a percentage; underneath, **drop-off peaks on `<page>`** (the page where most partial respondents stopped) or **no drop-off recorded** |
| **Median duration** | median time of completed responses (`m:ss`); underneath, the number of **speeders** — completed responses faster than a third of the median — or **timing arrives with responses** |
| **Quality screen** | share of completed responses that failed an attention check or straightlined a matrix, with **`X` of `Y` flagged · `<what was checked>`**; **add an attention check in Builder** when the questionnaire has nothing to check. See [[Data Quality\|Studio-Data-Quality]] |
| **Today** | **+N** completed responses since midnight (UTC), with a 14-day sparkline, or **last 14 days** when there is nothing to draw |

### Environment cards

Each environment you have published to is a card. Cards are ordered: in the
field (live or paused) first, then building, failed, closed, and previews last.

**Top line.** Status, environment name, the Save it was built from (`#17`,
tooltip "The Save this deployment was built from"), and the time: **published
…**, **started …** (while building) or **closed …**.

| Status | Meaning |
|---|---|
| **● Live** | collecting responses |
| **◌ Building** | queued or being built |
| **✕ Failed** | the last build failed |
| **‖ Paused** | the page is up, submissions are refused |
| **○ Closed** | the link shows a "closed" page |
| `preview` (extra pill) | a staged preview that never collects |

**Link.** The survey link with **Copy**. On a failed rebuild whose previous
version still serves the link, the card adds **· previous version still live**.

**Chips.** Buttons that open a panel under the card:

| Chip | Shown when | Opens |
|---|---|---|
| **QR** | the link serves a survey (live, paused, or failed rebuild with the previous version live); never on previews | QR code download — see [QR code](Studio-Distribution-Channels#qr-code) |
| **Embed** | same | iframe and script snippets — see [Embedding](Studio-Distribution-Channels#embedding-the-survey) |
| **Access codes** | same | [Access codes](Studio-Distribution-Channels#access-codes) |
| **Captcha** | same | [Captcha](Studio-Distribution-Channels#captcha) |
| **Panel** | same | [[Panel Providers\|Studio-Panel-Providers]] |
| **Drop-off** | also on closed environments | [Drop-off by page](Studio-Live-Monitoring#drop-off-by-page) |
| **Codebook** | also on closed environments | the variables of the environment's latest build |
| **Build log** | whenever a log exists | [Build log](#build-log) |
| **Republish #N** | the current Save differs from the published one and the environment is collecting | [Republishing](#republishing) |

**Closes line.** If the questionnaire has a deadline (or the environment
declares a closing date or a post-close redirect), the card shows **Closes
`<date>` → redirect `<url>`**.

> **Current limitation.** The deadline and closing date are only displayed:
> nothing closes the survey automatically when the date passes. Close the
> environment by hand (see [Closing and reopening](#closing-and-reopening)).

**Monitor block.** A **Responses** bar (`247/1,200`, with the percentage when
there is a cap), one bar per quota cell (`region="north"` `90/400`), and **Last
response `<date>`**. See [[Live Monitoring|Studio-Live-Monitoring]] for what the
numbers count.

### Publish panel

The sticky panel on the right turns the current Save — or your unsaved draft —
into a deployment.

| Row | Shows |
|---|---|
| **Current** | the latest Save (`#17`, click to open it in History) and its state: **● valid**, **● warnings** or **● error**; **not saved yet** before the first Save |
| **Draft** | **unsaved edits** if the Builder holds a draft that differs from the Save, otherwise **no unsaved edits**. While it checks: **Checking draft…**; if the check fails: **Draft status unavailable** with **Retry** |
| **Target** | the environment to publish to. Environments in the field carry **· live**. It defaults to `main` if `main` is in the field, otherwise the first environment in the field, otherwise the last declared environment |

Messages that can appear:

| Message | When |
|---|---|
| **⚠ Publishing switches the live field on `main` from #16 mid-collection.** | the target is live or paused and runs a different Save |
| **⚠ Save & publish saves your draft as #18 and switches the live field on `main` from #16 mid-collection.** | same, with unsaved edits |
| **Save #17 has validation errors — fix them in the Builder before publishing.** | the current Save has errors; the button is disabled |
| **#17 is what main runs — nothing to publish.** | the target already runs the current Save and there is no draft; the button is disabled |
| **Save the project in the Builder first.** | the project has never been saved |

The button reads **Publish to `<env>`**, or **Save & publish to `<env>`** when
you have unsaved edits (it saves them first, with the message "Publish to
`<env>`", so the field always runs a numbered Save). While it works:
**Publishing…**.

### Download the survey as a Python program

Under the Publish panel: "Download your survey and run it on your own machine:
it is a program on a source-available engine, and it runs without Studio." The
**questionnaire.py** button downloads the generated program of the current
Save (disabled until the project has a Save). See
[[Reproducibility|Studio-Reproducibility]].

---

## Publishing

1. Save in the Builder (or let **Save & publish** do it).
2. On **Distribute**, choose the **Target** environment — `pilot` first.
3. Click **Publish to `<env>`**.
   - A Save with **errors** cannot be published.
   - A Save with **warnings** asks first: **Publish #17 with warnings** —
     "Save #17 validated with warnings (see History). Publish it to main
     anyway?" → **Publish**.
4. A toast says **Deploying #17 to main…** and the card appears as **◌
   Building** with the steps **Queued → Build → Live** and the build log open.
5. When the build finishes, the card turns **● Live** and shows the link.

Publishing builds the survey from the Python stored with that Save, in an
isolated sandbox, and publishes the result on the environment's link. The
link stays the same for every later publish to the same environment.

Only one build per environment runs at a time; a second publish while one is
building is refused with "a deployment for this environment is already in
progress".

### Republishing

When you save a newer version while an environment is collecting, its card
shows the **Republish #18** chip. Clicking it asks:

> **Republish main with Save #18** — "The live field switches from Save #17 to
> #18 mid-collection: responses collected so far keep the old codebook.
> Continue?" → **Republish #18**

The Publish panel does the same for the selected target. When you republish:

- the link does not change, and responses keep collecting into the same table;
- until the new build is ready, the previous version keeps serving the link;
- quota counters keep their counts (targets are updated from the new Save);
- a **paused** environment becomes **live** again;
- respondents who already have the old page open can still submit.

### Rolling back with New deployment

**New environment** in the header (and **Deploy** on any Save in History)
opens the **New deployment** dialog. It deploys **any valid Save**, not just the
latest — that is how you roll back.

| Field | Notes |
|---|---|
| **Version** | every Save without errors, newest first: `#17 (current) — <message>`. Hint: "only valid Saves can be deployed", or "saved with warnings" |
| **Environment** | one button per declared environment (default `main`) |
| **Max responses** | read-only: the environment's cap, or **unlimited (plan quota applies)** |

Click **Deploy #N** (**Deploying…** while it starts). Without any Save the
dialog says "Save the project first — a deployment is built from a Save, so the
survey you publish is exactly the version you saw in the Builder." and offers
**Open Builder →**.

> **Note.** Unlike the Publish panel, this dialog does not ask for confirmation
> before replacing what a live environment runs, and does not warn about
> warnings. Check the version before you click **Deploy**.

---

## Lifecycle

| State | How it gets there | What respondents see | Card |
|---|---|---|---|
| Building (first publish) | **Publish**, **Deploy** | nothing yet — the link does not exist until the build finishes | **◌ Building**, steps, log open |
| Live | the build finished | the survey | **● Live**, **Pause**, **Close** |
| Republishing | publish to a live environment | the previous version until the new one is in place | **◌ Building** |
| Failed (first publish) | build error, or no progress for 15 minutes | nothing — there is no link | **✕ Failed**, error, **Redeploy current**, **View Save →** |
| Failed rebuild | a republish failed | the previous version, still collecting | **✕ Failed**, **· previous version still live**, **Close** |
| Paused | **Pause** | the survey opens and can be answered; at submit: "This survey is paused — The researchers have paused collection. Please try again later." | **‖ Paused**, **Resume**, **Close** |
| Closed | **Close** | a page "This survey is closed — The researchers have stopped collecting responses."; someone with the old page open gets the same message at submit | **○ Closed**, **Reopen** |
| Cap reached | completed responses reached the cap | the survey opens and can be answered; at submit: "Thank you for your interest — We have already reached our target sample for participants like you." | unchanged |
| Preview | **Preview** | a staged copy at its own address; submissions fail | `preview` pill, **Remove** |

The respondent side of each state is described in
[[What Respondents See|Studio-Respondent-Experience]].

---

## Pause and resume

**Pause** (tooltip "Stop accepting responses without taking the page down")
stops collection immediately; **Resume** restarts it. Neither rebuilds
anything. Toasts: **Collection paused**, **Collection resumed**.

While an environment is paused, the page keeps working, so people can still
open and fill in the survey — the refusal comes when they submit. Their
answers stay in their browser for 24 hours, so someone who returns after you
resume can pick up where they left off (same browser only). Progress of
unfinished interviews is not recorded during a pause, so the drop-off funnel
has a gap for that period.

Only a live environment can be paused, and only a paused one resumed.

---

## Closing and reopening

**Close** ends collection for good and replaces the survey with a static
"closed" page at the same link. It asks first:

> **Close survey** — "Close "main"? Respondents see a "survey closed" notice at
> the link and no more responses are accepted. Reopen builds Save #17 again
> into the same link." → **Close survey**

On a failed rebuild whose previous version is still live, the text reads: "The
last build of "main" failed, but the previous version is still live and
collecting. Close the survey? The page will show a "survey closed" notice;
Reopen builds Save #17 again."

**Reopen** (tooltip "Build Save #17 again into main") rebuilds the same Save
into the same link; responses collected before stay attached. Toast:
**Reopening main with Save #17…**. To reopen with a newer Save, publish to the
environment instead.

A closed environment keeps its responses and its drop-off funnel. Its
**Codebook** chip shows the closed version until the environment is published
again with another Save.

---

## Failed builds

A failed card shows the error, the steps with **Build** marked failed, and the
build log. Common causes:

- the Save has validation errors (it cannot be deployed at all);
- on the **Free** plan, the Save contains custom JavaScript or custom CSS:
  "Custom JavaScript in the questionnaire is included from Plus — remove the
  script or upgrade to deploy this Save" / "Custom CSS in the theme is included
  from Plus — clear it under Theme → Custom CSS or upgrade to deploy this Save";
- the build ran out of time (a build that shows no progress for 15 minutes is
  marked failed).

What you can do:

- **Redeploy current** (tooltip "Rebuild this environment from the current
  Save") — on a first publish that failed. It builds the **current** Save, so
  fix the problem, save, then redeploy.
- **View Save →** — opens the Save in History.
- On a failed rebuild, the previous version keeps serving and collecting; fix,
  save and publish again, or **Close**.

The organization's owners also receive an email, **Deployment failed:
`<org>/<project>`**, with the error, so a failure is noticed even when nobody
is watching the screen.

---

## Preview deployments

**Preview** (Distribute header; also **Preview** on a Save in History) builds a
staged copy of a Save at its own address, marked with a `preview` pill:

- Distribute's **Preview** always stages the **current** Save; History's
  previews the Save you are looking at.
- Toasts: **Building preview of #17…**, then **Preview ready — not accepting
  responses** or **Preview build failed — see the card's log**.
- A preview **never collects responses**. Someone who answers it gets the
  "Submission failed" dialog at the end. Use it for review, not for pilots —
  pilots belong in `pilot`.
- **Remove** takes it down ("Take the staged preview down?" → **Remove**).
  Previews are also removed automatically after **7 days**; the card then shows
  as closed.
- Previewing the same Save again reuses its address.

For a reviewer link inside the Builder, see
[[Testing Your Survey|Studio-Testing-Your-Survey]].

---

## Reset history and the archive

**More ▾ → Reset history** tidies the list:

> **Reset deployment history** — "Archive all closed, failed (never published)
> and preview deployments from this list? Live deployments and failed redeploys
> whose previous version is still live are not touched, the rest move to the
> archive (Show archive), and the full history stays in the audit log." →
> **Reset history**

Nothing is deleted. **More ▾ → Show archive** lists the archived cards (empty:
"No archived deployments — Reset history moves closed, failed and preview
deployments here."); **Back to current** returns. You can **Reopen** a closed
environment from the archive, which brings it back to the list.

---

## Build log

The **Build log** chip opens the log of the environment's last build. While a
build runs, lines stream in; afterwards the stored log is shown (or **No logs
recorded.**). Lines you may see:

| Line | Meaning |
|---|---|
| `built N files; deployed to <url>` | success |
| `[note] no quota cells seeded — …` | the questionnaire declares no quotas, so there is nothing to count |
| `[stop] Unpublished — survey link now shows a closed page` | the environment was closed |
| `[stop] Preview removed — staging link no longer served` | a preview was removed |
| `[reaper] deployment timed out and was marked failed, but the build finished afterward: …` | a slow build finished after being marked failed; the survey is up — **Redeploy** to bring the status up to date, or **Close** it |

---

## Response caps

Two caps apply to every environment, and the tighter one wins:

| Cap | Value |
|---|---|
| Environment cap | `max_responses` from `studio/settings.json` (defaults: `pilot` 50, `main` 1,200); without one, a cap set in the questionnaire's own settings, if any |
| Plan cap | **Free:** 1,000 completed responses per environment. **Plus, Pro, Corporate:** none |

How the cap works:

- It counts **completed** responses of that environment — every submitted
  interview, **including screen-outs** (a respondent who reached a
  disqualification page is a submitted response). Partial interviews do not
  count.
- The plan cap applies **per environment**, not to the project as a whole.
- When the cap is reached, the survey still opens. The refusal comes **at
  submit**: "Thank you for your interest — We have already reached our target
  sample for participants like you." With a panel's quota-full URL set, the
  respondent is sent there after 3 seconds (see
  [[Panel Providers|Studio-Panel-Providers]]).
- Unfinished interviews keep saving progress after the cap is reached.
- The **Responses** count on cards and tiles includes partial interviews, so
  it can read higher than the number the cap counts.
- The plan cap is not shown on the card; the **Max responses** field of the
  New deployment dialog shows the environment cap.

> **Current limitation.** Quota cells are counted and displayed, but a full
> cell does not yet stop new respondents — only the environment's response cap
> refuses submissions. Watch the quota bars during fieldwork and pause or close
> the environment when your cells are full. See
> [[Quotas and Randomization|Studio-Quotas-and-Randomization]].

If your trial ends while a survey is running, the survey keeps running on the
Free plan, and the Free cap of 1,000 completed responses per environment
applies from then on.

---

## Version discipline during fieldwork

Each response records the **environment** that collected it — its `survey_id`,
which is also the 12-character id in the survey link — not the Save. Because
republishing keeps the same link and the same `survey_id`, answers collected
under #17 and #18 in `main` look alike in the data. To reconstruct which Save
was in the field when:

- **Settings → Activity** lists every publish (`deploy.create`,
  `deploy.reopen`) with its time and environment; **Export CSV** includes the
  Save number of each publish.
- Compare those times with the responses' `created_at`.

The per-environment **Codebook** chip shows the variables of the environment's
**latest** build, not of earlier ones; History holds every Save's
questionnaire.

Mid-field changes therefore need care:

- **Safe:** fixing a typo, adding a page after the current ones, changing a
  theme color.
- **Risky:** renaming a variable, changing option codes, removing a question —
  your dataset now has two shapes. If you must, harmonize later with a
  **Recode** node ([[Cleaning and Weighting Data|Studio-Cleaning-and-Weighting]]).
- **Always:** pilot first, write a clear Save message for every version you
  publish, and read the republish warning before confirming.

---

## Who can publish

| Action | Who |
|---|---|
| Publish, republish, deploy, preview, pause, resume, close, reopen, reset history | any member of the organization (member, admin, owner) |
| Deploy a Save with custom JavaScript or custom CSS | *(Plus)* — on Free such a Save is refused |

Every action is recorded in the project's activity log (**Settings →
Activity**).

## See also

- [[Links, QR Codes, Embeds and Access Control|Studio-Distribution-Channels]]
- [[What Respondents See|Studio-Respondent-Experience]]
- [[Live Monitoring|Studio-Live-Monitoring]]
- [[History and Versions|Studio-History-and-Versions]]
- [[Project Settings|Studio-Project-Settings]]
