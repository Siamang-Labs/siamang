# Schedules and Webhooks

Two ways to put a project on autopilot. **Schedules** *(Plus)* run your
analysis flows on a timetable. **Webhooks** *(Plus)* tell another system when a
deploy or a run finishes. This page covers both, including what the current
build does and does not do.

---

## Schedules

A schedule runs **Run all** or one flow at fixed times — a nightly report, or a
cleaning pass every 30 minutes during fieldwork.

Schedules are on the **Flows** tab, in the **Schedules** section below the flow
list ("*N* · cron, UTC · fired by the worker").

```
Schedules  2 · cron, UTC · fired by the worker                 [+ Schedule a run]
 What runs     When                          Last fired          State
 Run all       daily at 02:00  0 2 * * *     9/23/2026, 2:00 AM  ● active   [Run now] [Pause] [Remove]
 tables        every 30 min  */30 * * * *    never               ● paused   [Run now] [Resume] [Remove]
```

With none yet: "**No schedules.** Run a flow on a timer — a nightly report, a
cleaning pass every 30 minutes during fieldwork."

### Create a schedule

1. Click **Schedule a run** (it needs at least one flow). On the Free plan the
   heading shows **Requires Plus** in its place (tooltip "Schedules are
   available from the Plus plan"); it opens **Billing** in the organization
   settings.
2. In **Schedule a run** — "The worker runs it on the current Save at the given
   times (UTC). Each run lands in the history like a manual one; outputs and
   reports are replaced." — choose:
   - **What to run**: **Run all flows (in dependency order)**, or one flow by
     name. Run all runs a flow after the flows whose tables it reads (a table
     one flow writes with **Write table** and another reads with **Project
     table**), in alphabetical order among flows that do not depend on each
     other — see [Run all](Studio-Flows#run-all).
   - **When**: a preset or **Custom cron…**.
3. Click **Schedule**. You see "Scheduled Run all" or "Scheduled *flow*".

| Preset | Cron |
|---|---|
| Every 30 minutes | `*/30 * * * *` |
| Hourly | `0 * * * *` |
| Daily at 02:00 (default) | `0 2 * * *` |
| Weekdays at 08:00 | `0 8 * * 1-5` |
| Weekly, Monday 09:00 | `0 9 * * 1` |

**Custom cron…** adds **Cron expression** ("minute hour day month weekday ·
UTC", placeholder `0 6 * * 1`). It takes the standard five fields, each a
number, `*`, a range (`1-5`), a list (`1,15`) or a step (`*/10`). Weekday `0`
(or `7`) is Sunday. Examples:

```text
0 6 * * 1        06:00 UTC every Monday
30 7 * * 1-5     07:30 UTC on weekdays
0 */6 * * *      every 6 hours
0 0 1 * *        midnight UTC on the 1st of each month
```

An expression the server cannot read is refused with "invalid cron
expression". **All times are UTC**; convert from your local time, and remember
that UTC does not move with daylight saving time.

The **When** column describes common shapes in words — "every 30 min",
"hourly", "hourly at :15", "daily at 02:00", "weekdays at 08:00", "Mon at
09:00", "monthly, day 1 at 00:00" — and otherwise shows the expression.

### What a scheduled run does

- It runs the flow (or Run all) on the project's **current Save at that
  moment** — the same as clicking **Run**. Unsaved edits are never used.
- The run appears in **Run history** like a manual one; its outputs and report
  replace the previous ones under **Files** and **Reports**.
- A scheduled Run all behaves like a manual one: a failed flow does not stop
  it. Every flow that does not read the failed flow's tables still runs;
  those that do are marked failed without running ("skipped: needs *flow*,
  which failed" in the log). The run then ends as **failed**, with no
  combined report.
- Its end sends the `run.completed` or `run.failed` webhook (below).
- When a run the timer started fails, every **owner** of the organization gets
  an email, "Scheduled analysis failed: *org/project*", with the run number
  and a link to open the run log. Runs started with **Run now** send no email.
- Studio checks schedules once a minute. A new schedule starts from the moment
  you create it; it does not back-fill earlier times.
- A schedule is skipped while it is paused, while the project has never been
  saved, and while the organization's plan does not include schedules (for
  example after a trial ends on Free).
- Missed times are **not made up one by one**. If a schedule that has run
  before misses one or more times (because it was paused or its plan lapsed),
  it runs **once** at the first check after it can run again, then continues on
  its timetable.

> **Current limitation.** Schedules run flows only. Connectors cannot be
> scheduled; run them from **Settings → Connectors** (see
> [[Connectors|Studio-Connectors]]).

### Manage schedules

| Button | Effect |
|---|---|
| **Run now** | "Start this run now, outside the timer" — starts the same run immediately and stamps it as the schedule's last run. Unavailable while that run is already in progress ("A run for this schedule is already in progress — see Run history") |
| **Pause** / **Resume** | stops or restarts the timer; the schedule and its history stay ("Schedule paused" / "Schedule resumed") |
| trash icon | **Remove schedule** — "Stop *X* from running *when*? Past runs stay in the history." → **Remove** |

Any member can create, run, pause and remove schedules. On the Free plan the
app offers **Requires Plus** instead of **Schedule a run**; through the API,
creating one is refused with "'schedules' is not available on the 'free' plan;
upgrade to enable it". Schedules created before the organization moved to
Free stay listed and can still be run with **Run now**, paused and removed,
but the timer skips them. To change a schedule's time, remove it and create a
new one (the API can also change the cron in place).

---

## Webhooks

A webhook sends an HTTP `POST` to a URL you choose whenever a deploy or a flow
run finishes, so another system can react: post to chat, page someone, start
your own pipeline.

Webhooks belong to the **organization** — they fire for events in all its
projects. Manage them in **Organization settings → Integrations → Webhooks**.
They need *(Plus)* (on Free the card says "Webhooks is a Plus feature") and the
**owner** or **admin** role. Members see the card with only "Only owners and
admins can see and manage the organization's webhooks."

### Add a webhook

"Send deploy and run events to Slack or your own endpoint."

| Field | Notes |
|---|---|
| **Endpoint URL** | an `http://` or `https://` address on the public internet, up to 500 characters. Private and internal addresses (`localhost`, private IP ranges, single-word host names) are refused: "webhook URL must target a public hostname" / "webhook URL must not target a private or reserved address" |
| **Secret** *(optional)* | "used to sign the request payload" (placeholder "leave blank to skip"); **Generate secret** fills in a random `whsec_…` value. With a secret, every delivery carries a signature (see [Request format and signature](#request-format-and-signature)) |
| **Events** | "none selected = receive everything". Two rows of chips: **Deploys** — **live**, **failed**, **stopped**; **Runs** — **completed**, **failed**. Hover a chip to see its event name (for example `deploy.failed`) |

Select any combination of chips to receive only those events; leave them all
unselected to receive every event.

Click **Add webhook** (or press `Enter` in the URL field). The webhook appears
in the list with its URL, "all events" or the event names you chose (for
example `deploy.failed, run.failed`), and **Delete** (**Delete webhook** —
"Stop sending events to *url*?"). With none yet the card says "No webhooks
configured yet."

> **Important.** Copy the secret into your receiving system **before** you
> click **Add webhook**. The form clears it once the webhook is added, and
> Studio never shows it again — the list does not even say which webhooks
> have one. If you lose it, delete the webhook and add it again with a new
> secret.

Adding and deleting a webhook is recorded in the organization's **Activity**
as `webhook.create` and `webhook.delete`, with the endpoint URL (and, for a
new webhook, its event list) — never the secret.

There is no way to edit, pause or test a webhook in the app. To change one,
delete it and add it again.

> **Note — webhooks added in earlier versions.** Earlier versions of Studio
> offered the chips **Deploys**, **Runs** and **Terminal**, which saved the
> event names `deploy`, `run` and `terminal`. No event carries those names, so
> a webhook that lists any of them in its row receives nothing. Earlier
> versions also did not store the **Secret** typed in the form, so webhooks
> added in the app back then send unsigned requests. Delete such a webhook
> and add it again. A webhook that shows "all events" and needs no signature
> works as it is.

### Create a webhook through the API

The same webhook can be created with an API key of an owner or admin (see
[[API and API Keys|Studio-API-and-API-Keys]]), for example from a setup
script:

```bash
curl -X POST https://api.studio.siamang.org/orgs/acme-research/webhooks \
  -H "Authorization: Bearer sck_…" \
  -H "Content-Type: application/json" \
  -d '{
        "url": "https://hooks.example.com/siamang",
        "secret": "whsec_3f1c…",
        "events": ["deploy.failed", "run.failed"],
        "enabled": true
      }'
```

`events` takes the exact event names from the table below — the same names
the chips send; an empty list (`[]`) means every event. The webhook then
appears in the app's list as usual.

### Events and payloads

Every body is a JSON object with the `event` name, a one-line `text` summary
for people, and the event's fields:

| Event | When | Fields besides `event` and `text` | `text` example |
|---|---|---|---|
| `deploy.live` | a deployment finished building and is serving | `deployment_id`, `project`, `environment`, `url`, `survey_id` | `deploy.live · acme-research/brand-2026 (main) · https://study.siamang.org/3f9a1c07b2de/` |
| `deploy.failed` | a deployment build failed | `deployment_id`, `project`, `environment` | `deploy.failed · acme-research/brand-2026 (main)` |
| `deploy.stopped` | a deployment or preview was stopped | `deployment_id`, `project`, `environment` | `deploy.stopped · acme-research/brand-2026 (main)` |
| `run.completed` | a flow run or Run all finished (manual or scheduled) | `run_id`, `kind` (`run_script` or `run_all`), `project`, `script` (the flow's name; not for Run all), `status` | `run.completed · acme-research/brand-2026 · flow tables · completed` — for Run all: `run.completed · acme-research/brand-2026 · all flows · completed` |
| `run.failed` | a flow run or Run all failed | as `run.completed`, with `"status": "failed"` | `run.failed · acme-research/brand-2026 · flow tables · failed` |

`project` is `<organization-slug>/<project-slug>`. A complete body:

```json
{
  "event": "deploy.live",
  "text": "deploy.live · acme-research/brand-2026 (main) · https://study.siamang.org/3f9a1c07b2de/",
  "deployment_id": 42,
  "project": "acme-research/brand-2026",
  "environment": "main",
  "url": "https://study.siamang.org/3f9a1c07b2de/",
  "survey_id": "3f9a1c07b2de"
}
```

Parse the fields rather than `text`, which is a summary for people. "Run to
here" previews, connector runs, deposits and Saves send nothing.

### Request format and signature

Every delivery is a `POST` with:

- `Content-Type: application/json`
- `X-Siamang-Event: <event name>`
- `X-Siamang-Signature: sha256=<hex>` — only when the webhook has a secret. The
  value is the HMAC-SHA256 of the **raw request body** with your secret as the
  key.

Verify it before trusting a delivery, for example in Python:

```python
import hashlib, hmac

def is_authentic(raw_body: bytes, header: str, secret: str) -> bool:
    expected = "sha256=" + hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header or "")
```

Your endpoint should answer with a 2xx status within **10 seconds**.

### Retries

| Your endpoint answers | Studio does |
|---|---|
| 2xx | marks the delivery **ok** |
| no answer, a network error, 5xx, 408 or 429 | marks it **pending** and retries 2, 4, 8 and 16 minutes later — **5 attempts** in all — then marks it **failed** |
| any other 4xx (for example 400, 404, 410) | marks it **failed** at once; retrying would not help |

### Recent deliveries

Below the list of webhooks (once there is at least one): **Recent deliveries**
— "retried automatically with backoff" — the organization's latest 50
deliveries, one row per event and endpoint:

| Column | Shows |
|---|---|
| **Event** | the event name |
| **Endpoint** | the URL |
| **Status** | **ok**, **pending** (a retry is scheduled) or **failed** |
| **Attempts** | how many times it was sent |
| **Last error** | for example `HTTP 404`, or the network error |
| **When** | when it was delivered (or created) |

Click **Refresh** to update it. Before the first event: "No deliveries yet —
events appear here after a deploy or run finishes."

### Slack and other chat tools

Because every payload carries a `text` line, you can paste a **Slack
incoming-webhook URL** as the **Endpoint URL**: Slack accepts the delivery and
posts the line, for example "run.failed · acme-research/brand-2026 · flow
tables · failed".

Other chat tools expect their own message format. For those, or for a richer
message than one line, point the webhook at something that turns the JSON into
a message: an automation service such as Zapier or Make, or a small endpoint
of your own.

### Typical uses

- A message when fieldwork goes live (`deploy.live`) or a build fails
  (`deploy.failed`).
- An alert when a scheduled nightly run fails (`run.failed`).
- Starting your own ETL when Run all completes (`run.completed` with
  `"kind": "run_all"`), then fetching its outputs through the
  [[API|Studio-API-and-API-Keys]].

## See also

- [[Analysis Flows|Studio-Flows]]
- [[Connectors|Studio-Connectors]]
- [[API and API Keys|Studio-API-and-API-Keys]]
- [[Organizations and Team|Studio-Organizations-and-Team]]
- [[Plans, Trial and Billing|Studio-Plans-and-Billing]]

<!-- studio-nav -->
---

← [[Connectors|Studio-Connectors]] · [Studio contents](Studio-Overview#all-pages) · [[API and API Keys|Studio-API-and-API-Keys]] →
