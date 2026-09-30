# Publishing and Environments

**Distribute** is where a Save becomes a live survey. This page covers
environments, the Distribute screen, publishing and republishing, rolling back,
pausing and closing, deadlines and closing dates, failed builds, preview
deployments and response caps. For the ways you hand the link out and control
who answers — QR codes, embeds, access codes, captcha, one response per
browser — see
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

The caps matter: with the defaults, `main` stops taking responses once it has
1,200 completed interviews (see [Response caps](#response-caps)).

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

An environment can also declare a closing date (`closes_at`) and an address
to send respondents to once the survey has closed (`redirect_after_close`, an
`https://` or `http://` URL; `{url:NAME}` in it is filled from the link the
respondent arrived with); see [Deadlines](#deadlines):

```json
"environments": [
  { "name": "pilot", "max_responses": 50 },
  { "name": "main", "max_responses": 1200,
    "closes_at": "2026-07-01T00:00:00+02:00",
    "redirect_after_close": "https://example.org/study-closed" }
]
```

A changed cap, closing date or redirect takes effect when you next publish
that environment.

---

## The Distribute screen

```
┌ Distribute   2 environments · 259 responses total · current Save #17 ── [More ▾] [Preview] [New environment] ┐
│ ┌Responses · main┐┌Completion┐┌Median duration┐┌Quality screen┐┌Today┐   ┌ Publish ─────────┐ │
│ │ 247 / 1,200    ││ 78%      ││ 6:10          ││ 3%           ││ +31 │   │ Current  #17 ●valid│ │
│ │ ▓▓▓░░░░░░      ││ drop-off…││ 12 speeders   ││ 7 of 240 …   ││ ▂▃▅▇│   │ Draft    no unsaved│ │
│ └────────────────┘└──────────┘└───────────────┘└──────────────┘└─────┘   │ Target  [main ▾]   │ │
│ ┌ ● Live  main  #17  published Jun 4, 2026, 2:32 PM      [Pause] [Close] ┐ │ [Publish to main]  │ │
│ │ study.siamang.org/3f9a1c07b2de/                             [Copy]     │ ├────────────────────┤ │
│ │ [QR] [Embed] [Access codes] [Captcha] [One per browser] [Panel]        │ │ Download the survey│ │
│ │ [Closing date] [Drop-off] [Codebook] [Build log]                       │ │ as a Python program│ │
│ │ Closes Jul 1, 2026 → redirect https://example.org/thanks               │ │ [questionnaire.py] │ │
│ │ Responses · 21%   ▓▓░░░░░░░░                         247/1,200         │ └────────────────────┘ │
│ │ region="north"    ▓▓▓░░░░░░░                          90/400           │                        │
│ └────────────────────────────────────────────────────────────────────────┘                        │
│ ┌ ○ Closed  pilot  #12  closed Jun 1, 2026, …                    [Reopen] ┐                        │
│ └──────────────────────────────────────────────────────────────────────────┘                        │
│ Email invitations …                                                                                │
└────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Header

- The subtitle shows how many environments the project has been published to,
  **· N responses total** — the completed interviews (submitted and not
  screened out) of the environments listed, previews not included — and the
  current Save (`current Save #17`, or `unsaved`).
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
| **Responses · `<env>`** | with an environment cap: the **completed interviews** of that environment against its cap (`247 / 1,200`), with a bar — the number the cap counts. The tooltip adds everything else: "247 completed interviews count toward the cap of 1,200; 312 responses in all, partial and screened out included". Without an environment cap: every response row of the environment, and **no cap** |
| **Completion** | submitted interviews (screen-outs included) ÷ all rows, as a percentage; underneath, **drop-off peaks on `<page>`** (the page where most partial respondents stopped) or **no drop-off recorded**. Partial rows arrive only from a survey built with the current runtime (see [Republishing](#republishing)); for an older build this tile reads 100 % |
| **Median duration** | median time of submitted responses, screen-outs included (`m:ss`); underneath, the number of **speeders** — submitted responses faster than a third of the median — or **timing arrives with responses** |
| **Quality screen** | share of submitted responses (screen-outs included) that failed an attention check or straightlined a matrix, with **`X` of `Y` flagged · `<what was checked>`**; **add an attention check in Builder** when the questionnaire has nothing to check. See [[Data Quality\|Studio-Data-Quality]] |
| **Today** | **+N** submitted responses (screen-outs included) since midnight (UTC), with a 14-day sparkline, or **last 14 days** when there is nothing to draw |

### Environment cards

Each environment you have published to is a card. Cards are ordered: in the
field (live or paused) first, then building, failed, closed, and previews last.

**Top line.** Status, environment name, the Save it was built from (`#17`,
tooltip "The Save this deployment was built from"), the time — **published
…**, **started …** (while building) or **closed …** — and the buttons for the
state (**Pause**, **Resume**, **Close**, **Reopen**, **Extend**, …).

| Status | Meaning |
|---|---|
| **● Live** | collecting responses |
| **◌ Building** | queued or being built |
| **✕ Failed** | the last build failed |
| **‖ Paused** | the page is up, but it says the survey is paused and takes no responses |
| **○ Closed** | closed with **Close** — the link shows a "closed" page — or past its closing date (tooltip "Closed — deadline passed `<date>`", with an **Extend** button; see [Deadlines](#deadlines)) |
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
| **One per browser** (**One per browser · on** when on) | same | [One response per browser](Studio-Distribution-Channels#one-response-per-browser) |
| **Panel** | same | [[Panel Providers\|Studio-Panel-Providers]] |
| **Closing date** | the environment is collecting (live, paused, past its closing date, or a failed rebuild with the previous version live); never on previews | [The Closing date panel](#the-closing-date-panel) |
| **Drop-off** | also on closed environments | [Drop-off by page](Studio-Live-Monitoring#drop-off-by-page) |
| **Codebook** | also on closed environments | the variables of the environment's latest build |
| **Build log** | whenever a log exists | [Build log](#build-log) |
| **Republish #N** | the current Save differs from the published one and the environment is collecting | [Republishing](#republishing) |

**Closing line.** When the environment has a closing date or a post-close
redirect, the card shows **Closes `<date>`** (with **· set here** for a date set
in the **Closing date** panel), or **No closing date**, then **→ redirect
`<url>`** when there is a redirect. Past the date it reads **Closed — deadline
passed `<date>`**. When `studio/settings.json` now declares a post-close
redirect other than the one the running deployment has, or a `closes_at`
earlier than its closing date (or one where it has none, and no date was set
in the panel), the line adds "· the environment’s closing settings changed —
republish `<env>` to apply". A later `closes_at`, or a redirect you removed,
also applies only at the next publish, but the line does not point it out. See
[Deadlines](#deadlines).

**Monitor block.** A **Responses** bar — with an environment cap, the completed interviews
against it (`247/1,200`, with the percentage, and the same tooltip as the
tile); without one, every response row — one bar per quota cell
(`region="north"` `90/400`), and **Last response `<date and time>`**. See
[[Live Monitoring|Studio-Live-Monitoring]] for what the numbers count.

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
| **Save #17 has validation errors — fix them in the Builder before publishing.** | the current Save does not validate (state **● error**); the button is disabled |
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
   - A Save that does not validate (**● error**) cannot be published.
   - A Save with **warnings** asks first: **Publish #17 with warnings** —
     "Save #17 validated with warnings (see History). Publish it to main
     anyway?" → **Publish**.
   - When the engine's lint found **errors** in the questionnaire (a Save
     still marked **● warnings**, see
     [[Testing Your Survey|Studio-Testing-Your-Survey]]), the confirmation says
     so: **Publish #17 with errors** — "Save #17 has 1 error the engine's lint
     found in the questionnaire: Page 'thanks' has no items. It does not stop
     publishing, but the survey goes out with it — see Builder → Validation.
     Publish it to main anyway?" (with several: "… has 2 errors …: `<first
     message>` (and 1 more). They do not stop publishing, but the survey goes
     out with them …") → **Publish anyway**.
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
- quota counters keep their counts (targets are updated from the new Save); a
  cell the new Save adds starts at the number of completed responses that
  already have its value, and a cell it no longer declares (a quota you
  removed, or moved to another value) is dropped: it stops no one and leaves
  the quota bars on Distribute and Live;
- a **paused** environment becomes **live** again;
- respondents who already have the old page open can still submit;
- the environment's closing date and post-close redirect are read again from
  the new Save (see [Deadlines](#deadlines)) — except a date set in the
  **Closing date** panel, which stays;
- **One response per browser** stays as you set it.

> **Note — surveys built before the current runtime.** An environment keeps
> the build it was last published with. A survey published before the latest
> Studio update therefore still runs the older survey page until you
> republish it: Save in the Builder (a Save with no changes will do), then
> **Republish #N** on the card. Only the new build:
>
> - checks, as the page opens, whether the survey is closed, paused, past its
>   closing date or full, and sends respondents on to the environment's
>   post-close redirect ([What Respondents See](Studio-Respondent-Experience#paused-closed-and-full-surveys));
> - stops respondents whose quota cell is full ([When a cell is
>   full](Studio-Quotas-and-Randomization#when-a-cell-is-full)) and honors
>   [One response per browser](Studio-Distribution-Channels#one-response-per-browser);
> - sends partial responses, so the drop-off funnel, the **Completion** tile
>   and an invitation's `started` status fill in;
> - resizes itself inside the [script embed](Studio-Distribution-Channels#embedding-the-survey);
> - stores answers with today's codes (a matrix column's code, Other and
>   None of the above as codes, N/A as the variable's declared
>   not-applicable code, a wide Multiple choice as one 0/1 variable per
>   choice), spreads respondents over the arms of a seeded
>   **Assign to a condition** and gives them different MaxDiff and conjoint
>   design versions — an older build sent everyone to the same arm and the same
>   version.
>
> Responses collected by the older build are read in the same layout as new
> ones in Data, exports and flows, so one dataset holds both (see
> [Data from more than one version](Studio-Responses-and-Data#data-from-more-than-one-version)
> and [Older surveys and responses](Studio-Question-Types#older-surveys-and-responses)).
> One thing is lost at the switch: a respondent who was halfway through the
> older build cannot resume their saved progress in the new one and starts
> again. Republish between fieldwork peaks if you can.
>
> The same holds for a survey published before Studio began storing each
> answer under its variable name: show-if conditions, branching and piping on
> a question whose Id differs from its variable only work in a new build. See
> [Question Id and variable name](Studio-Builder-Overview#question-id-and-variable-name).

### Rolling back with New deployment

**New environment** in the header (and **Deploy** on any Save in History)
opens the **New deployment** dialog. It deploys **any valid Save**, not just the
latest — that is how you roll back.

| Field | Notes |
|---|---|
| **Version** | every Save that validates, newest first: `#17 (current) — <message>`. Hint: "only valid Saves can be deployed", "saved with warnings", or — when the engine's lint found errors — "saved with 1 error — publishable after a confirmation" |
| **Environment** | one button per declared environment (default `main`) |
| **Max responses** | read-only: the environment's cap, or **unlimited (plan quota applies)** |

Click **Deploy #N** (**Deploying…** while it starts). Without any Save the
dialog says "Save the project first — a deployment is built from a Save, so the
survey you publish is exactly the version you saw in the Builder." and offers
**Open Builder →**.

> **Note.** Unlike the Publish panel, this dialog does not ask for confirmation
> before replacing what a live environment runs, and does not stop for
> warnings or lint errors (the hint only names them). Check the version before
> you click **Deploy**.

---

## Lifecycle

| State | How it gets there | What respondents see | Card |
|---|---|---|---|
| Building (first publish) | **Publish**, **Deploy** | nothing yet — the link does not exist until the build finishes | **◌ Building**, steps, log open |
| Live | the build finished | the survey | **● Live**, **Pause**, **Close** |
| Republishing | publish to a live environment | the previous version until the new one is in place | **◌ Building** |
| Failed (first publish) | build error, or no progress for 15 minutes | nothing — there is no link | **✕ Failed**, error, **Deploy current Save #N** or **Retry Save #N**, **View Save →** |
| Failed rebuild | a republish failed | the previous version, still collecting | **✕ Failed**, **· previous version still live**, **Close** |
| Paused | **Pause** | as the page opens: "This survey is paused — The researchers have paused collection. Please try again later."; someone who already had the page open meets the same notice when they submit | **‖ Paused**, **Resume**, **Close** |
| Closed | **Close** | a page "This survey is closed — The researchers have stopped collecting responses.", then the environment's post-close redirect if it has one; someone with the old page open gets the same notice at submit | **○ Closed**, **Reopen** |
| Past the closing date | the questionnaire's deadline, the environment's `closes_at` or the date set in the **Closing date** panel passed | as the page opens: "This survey is closed — The researchers have stopped collecting responses.", then, after 3 seconds, the environment's post-close redirect if it has one | **○ Closed** (tooltip "Closed — deadline passed `<date>`"), **Extend**, **Close** |
| Cap reached | completed interviews reached a response cap | as the page opens: "Thank you for your interest — We have already reached our target sample for participants like you." (reworded by Theme → Wording, when you reword it), then the panel's quota-full URL if one is set; someone already answering meets it at submit | unchanged |
| Preview | **Preview** | a staged copy at its own address, with the banner "Preview — answers are not stored"; it ends on the survey's normal completion page | `preview` pill, **Remove** |

The page-open notices (paused, past the closing date, cap reached) come from
builds made with the current runtime; a survey built earlier shows them only
when the respondent submits, until you republish it (see
[Republishing](#republishing)). The respondent side of each state is
described in [[What Respondents See|Studio-Respondent-Experience]].

---

## Pause and resume

**Pause** (tooltip "Stop accepting responses without taking the page down")
stops collection immediately; **Resume** restarts it. Neither rebuilds
anything. Toasts: **Collection paused**, **Collection resumed**.

While an environment is paused, the page stays up, but someone who opens the
link sees "This survey is paused — The researchers have paused collection.
Please try again later." instead of the questionnaire. Someone who was
already answering when you paused can go on, and meets the same notice when
they submit. Their answers stay in their browser for 7 days after their last
answer, so someone who returns after you resume can pick up where they left off
(same browser only).
Progress of unfinished interviews is not recorded during a pause, so the
drop-off funnel has a gap for that period.

A survey built before the page-open check existed lets people answer the
whole questionnaire and shows the notice only at submit, until you republish
it.

Only a live environment can be paused, and only a paused one resumed. Pause
is not offered once an environment is past its closing date — it is already
closed; use **Extend** to collect again.

---

## Closing and reopening

**Close** ends collection for good and replaces the survey with a static
"closed" page at the same link: "This survey is closed — The researchers have
stopped collecting responses." If the environment declares a post-close
redirect (`redirect_after_close`), the page adds "Redirecting you now.
Continue if you are not redirected." and sends visitors there after 3 seconds,
filling any `{url:NAME}` in the address from the link they arrived with. Close
asks first:

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
environment instead. A reopened environment whose closing date has already
passed is closed again at once — move the date with **Extend** (see
[Deadlines](#deadlines)).

A closed environment keeps its responses and its drop-off funnel. Its
**Codebook** chip shows the closed version until the environment is published
again with another Save.

---

## Deadlines

An environment can stop collecting on its own at a date and time you choose —
its **closing date**. The date comes from one of three places:

- the questionnaire's **deadline**. The Builder has no field for it: add it at
  the top level of the questionnaire in **Builder → Source** — for example
  `"deadline": "2026-07-01T00:00:00+02:00"` — press **Apply** and Save, or
  import a `questionnaire.py` that sets one;
- the environment's `closes_at` in `studio/settings.json` (see
  [Changing environments](#changing-environments)). When a Save has both, the
  earlier one wins;
- a date you set on the card, in the **Closing date** panel (below). It
  replaces the Save's date at once, without a new Save or a rebuild.

A date written without a time zone is read as UTC. Each publish reads the
Save's date (deadline or `closes_at`) and the environment's post-close
redirect (`redirect_after_close`) again; a date set in the panel stays through
a republish, a rebuild of a failed deployment or a **Reopen**.

Once the closing date has passed:

- The environment stops accepting responses, and progress of unfinished
  interviews is no longer saved, so the drop-off funnel stops growing and
  invitations no longer turn `started`.
- Someone who opens the link sees "This survey is closed — The researchers have
  stopped collecting responses." as the page opens — the same notice as after
  **Close** — and, if the environment has a post-close redirect, is sent there
  after 3 seconds (`{url:NAME}` in the address is filled from the link they
  arrived with). Someone who was already answering meets the notice when they
  submit, and is sent on the same way. A survey built before this check existed
  shows the notice only at submit, until you republish it.
- The card reads **○ Closed**, with the line **Closed — deadline passed
  `<date>`**. **Pause** is gone; **Extend** (tooltip "Collect again: move the
  closing date — no rebuild") opens the **Closing date** panel. The Live tab
  shows the same **○ Closed**, and **New mailing** stays disabled unless
  another environment is still collecting (see
  [[Email Invitations|Studio-Email-Invitations]]).

Close the environment as well when you want the link itself to show the static
closed page.

### The Closing date panel

The **Closing date** chip opens the panel. Its header reads **Closing date ·
`<date>`** (or **· none**), with **· set here** when the date was set in the
panel. The text:

> When `main` stops accepting responses. A change here applies at once — no
> new Save, no rebuild: a respondent who opens the link after the date sees
> “This survey is closed” [and is sent on to the environment's redirect].

followed by either "Until you set one here, the date comes from the published
Save: the questionnaire’s deadline or the environment’s closes_at, whichever is
earlier. A date set here stays through a Redeploy or Reopen." or, once you have
set one, "This date was set here, so a Redeploy or Reopen keeps it; “Use the
Save’s date” hands it back to the questionnaire’s deadline and the
environment’s closes_at."

| Control | Does |
|---|---|
| date and time field | in your browser's local time. A date in the past shows "Pick a date in the future — to stop collecting now, use Close." |
| **Save date** (**Extend to this date** when the environment is past its date) | sets the date; toast **Collecting until `<date and time>`** |
| **No closing date** | the environment collects until you close it, whatever the Save says; toast **No closing date — collecting until you close it** |
| **Use the Save’s date** | shown only for a date set here: goes back to the Save's deadline or `closes_at`; toast **Closing date taken from the Save** |

If the change is refused, the toast reads "Could not change the closing date."
followed by the reason — for example "The closing date must be in the future —
use Close to stop collecting now." Previews have no closing date. Every change
is recorded in **Settings → Activity** as `deploy.closing_date`.

To extend a survey that has closed by its date: **Extend** → pick a later date
→ **Extend to this date**. The survey collects again at once, without a
rebuild; the card turns back to **● Live**.

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

- On a first publish that failed, the button names the Save it will build.
  Once you have saved a fix, it reads **Deploy current Save #18** (tooltip
  "Build the current Save #18 into main (the failed build was Save #17)"); while
  the failed Save is still the current one, it reads **Retry Save #17** (tooltip
  "Build Save #17 into main again"). So: fix the problem, save, then click it.
  The toast says **Redeploying #18…**.
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
- A preview **never collects responses**. A bar along the bottom of the page
  says "Preview — answers are not stored", nothing is sent to Studio (no
  partial saves, no quota checks), and someone who answers to the end sees the
  survey's normal completion page. Use it for review, not for pilots — pilots
  belong in `pilot`. A preview built before this banner existed ends on the
  "Submission failed" dialog instead; click **Preview** again to rebuild it.
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
build runs, lines stream in; afterward the stored log is shown (or **No logs
recorded.**). Lines you may see:

| Line | Meaning |
|---|---|
| `built N files; deployed to <url>` | success |
| `[note] no quota cells seeded — …` | the questionnaire declares no quotas, so there is nothing to count |
| `[stop] Unpublished — survey link now shows a closed page` | the environment was closed |
| `[stop] Preview removed — staging link no longer served` | a preview was removed |
| `[reaper] deployment timed out and was marked failed, but the build finished afterward: …` | a slow build finished after being marked failed; the survey is up (the card shows **· previous version still live**, and the project's **Settings → Activity** adds a `deploy.live` entry for it) — publish the environment again to bring the status up to date, or **Close** it |

---

## Response caps

Two caps apply to every environment, and the tighter one wins:

| Cap | Value | Counted over |
|---|---|---|
| Environment cap | `max_responses` from `studio/settings.json` (defaults: `pilot` 50, `main` 1,200); without one, a cap set in the questionnaire's own settings, if any | that environment |
| Plan cap | **Free:** 1,000 completed interviews per project. **Plus, Pro, Corporate:** none | every environment of the project together |

How the caps work:

- They count **completed interviews**: submitted responses that did not end on
  a Screen-out page. Partial interviews do not count, and neither do
  screen-outs. A screen-out is still recorded when a cap is full, so your
  screener numbers stay complete.
- The Free cap is shared by the whole project: `pilot` and `main` together
  can collect 1,000 completed interviews. In a project made from the
  **Example** template, the sample responses that come with it do not count;
  only real respondents do.
- When a cap is reached, someone who opens the link sees "Thank you for your
  interest — We have already reached our target sample for participants like
  you." as the page opens, instead of the questionnaire (the two texts follow
  Theme → Wording → **Quota full: title** / **Quota full: text** when you
  reword them). Someone who was already answering meets the same notice when
  they submit. With a panel's quota-full URL set, the respondent is sent there
  after 3 seconds (see [[Panel Providers|Studio-Panel-Providers]]). A survey
  built before the page-open check existed shows the notice only at submit,
  until you republish it.
- Unfinished interviews keep saving progress after the cap is reached.
- With an environment cap, the **Responses** tile and the card's **Responses**
  bar show the completed interviews against it — the number the cap counts —
  and their tooltip gives the total of all rows. Without an environment cap
  they show every response row, partial and screened-out ones included.
- The plan cap is not shown on the card; the **Max responses** field of the
  New deployment dialog shows the environment cap.

Quota cells are a separate limit: a full cell stops the respondents who fall
into it when they leave the page with that answer, while the others go on.
See [When a cell is full](Studio-Quotas-and-Randomization#when-a-cell-is-full).

If your trial ends while a survey is running, the survey keeps running on the
Free plan, and the Free cap of 1,000 completed interviews per project applies
from then on — counting the interviews the project already has.

---

## Version discipline during fieldwork

Each response records the **environment** that collected it — its `survey_id`,
which is also the 12-character id in the survey link — not the Save. Because
republishing keeps the same link and the same `survey_id`, answers collected
under #17 and #18 in `main` look alike in the data. To reconstruct which Save
was in the field when:

- **Settings → Activity** lists every publish (`deploy.create`,
  `deploy.reopen`) with its time and environment; **Export CSV** includes the
  Save number of each publish. When the build finishes, a `deploy.live` entry
  follows, with `—` as the person and the survey link as its target: from
  then on the new version is the one collecting.
- Compare those times with the responses' `created_at`.

The per-environment **Codebook** chip shows the variables of the environment's
**latest** build, not of earlier ones; History holds every Save's
questionnaire.

Mid-field changes therefore need care:

- **Safe:** fixing a typo, adding a page after the current ones, changing a
  theme color. Changing the **Id** of a single-answer question does not change
  your data either: its answer is stored under the variable name (see
  [Question Id and variable name](Studio-Builder-Overview#question-id-and-variable-name)).
- **Risky:** renaming a variable, changing option codes, removing a question —
  your dataset now has two shapes. Once the questionnaire has been published,
  the Builder says so when you rename a variable: "This questionnaire has been
  published. Renaming a variable renames its column in the data: answers
  already collected keep the old name, answers collected after you publish
  again get the new one." Changing a MaxDiff's item codes, a conjoint's
  attributes or level codes, their numbers of tasks and items shown, or — when
  no seed is set — the question's **Id** gives later respondents a different
  design from earlier ones. If
  you must, harmonize later with a **Recode** node
  ([[Cleaning and Weighting Data|Studio-Cleaning-and-Weighting]]).
- **Always:** pilot first, write a clear Save message for every version you
  publish, and read the republish warning before confirming.

What a republish changes in your data, including the switch from an older
build to the current runtime, is listed under
[Data from more than one version](Studio-Responses-and-Data#data-from-more-than-one-version).

---

## Who can publish

| Action | Who |
|---|---|
| Publish, republish, deploy, preview, pause, resume, close, reopen, extend or change the closing date, turn **One response per browser** on or off, reset history | any member of the organization (member, admin, owner) |
| Deploy a Save with custom JavaScript or custom CSS | *(Plus)* — on Free such a Save is refused |

Every action is recorded in the project's activity log (**Settings →
Activity**), and so is how each build ended (`deploy.live`, `deploy.failed`,
`deploy.preview_live`, `deploy.preview_failed`).

## See also

- [[Links, QR Codes, Embeds and Access Control|Studio-Distribution-Channels]]
- [[What Respondents See|Studio-Respondent-Experience]]
- [[Live Monitoring|Studio-Live-Monitoring]]
- [[History and Versions|Studio-History-and-Versions]]
- [[Project Settings|Studio-Project-Settings]]

<!-- studio-nav -->
---

← [[AI Assistant|Studio-AI-Assistant]] · [Studio contents](Studio-Overview#all-pages) · [[Links, QR Codes, Embeds and Access Control|Studio-Distribution-Channels]] →
