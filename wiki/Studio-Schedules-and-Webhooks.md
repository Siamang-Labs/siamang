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

1. Click **Schedule a run** (it needs at least one flow).
2. In **Schedule a run** — "The worker runs it on the current Save at the given
   times (UTC). Each run lands in the history like a manual one; outputs and
   reports are replaced." — choose:
   - **What to run**: **Run all flows (in dependency order)**, or one flow by
     name. Despite the label, Run all runs flows in alphabetical order of
     their names — see [[Analysis Flows|Studio-Flows]].
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
- Its end sends the `run.completed` or `run.failed` webhook (below).
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

Any member can create, run, pause and remove schedules. Creating one on the
Free plan is refused with "'schedules' is not available on the 'free' plan;
upgrade to enable it". To change a schedule's time, remove it and create a new
one (the API can also change the cron in place).

---

## Webhooks

A webhook sends an HTTP `POST` to a URL you choose whenever a deploy or a flow
run finishes, so another system can react: post to chat, page someone, start
your own pipeline.

Webhooks belong to the **organization** — they fire for events in all its
projects. Manage them in **Organization settings → Integrations → Webhooks**.
They need *(Plus)* (on Free the card says "Webhooks is a Plus feature") and the
**owner** or **admin** role.

### Add a webhook

"Send deploy and run events to Slack or your own endpoint."

| Field | Notes |
|---|---|
| **Endpoint URL** | an `http://` or `https://` address on the public internet, up to 500 characters. Private and internal addresses (`localhost`, private IP ranges, single-word host names) are refused: "webhook URL must target a public hostname" / "webhook URL must not target a private or reserved address" |
| **Secret** *(optional)* | "used to sign the request payload"; **Generate secret** fills in a random `whsec_…` value |
| **Events** | "none selected = receive everything"; chips **Deploys**, **Runs**, **Terminal** |

Click **Add webhook** (or press `Enter` in the URL field). The webhook appears
in the list with its URL, "all events" (or its event list), and **Delete**
(**Delete webhook** — "Stop sending events to *url*?").

> **Current limitation — leave Events unselected.** In the current build,
> selecting any of the **Events** chips stops that webhook from receiving
> anything. Leave all three unselected to receive every event, and filter on
> the `event` field at your end.

> **Current limitation — signing secrets.** A secret typed or generated in this
> form is not stored, so webhooks created here are sent **unsigned**. To get
> signed deliveries (or an event filter that works), create the webhook through
> the API as shown below.

There is no way to edit, pause or test a webhook in the app. To change one,
delete it and add it again.

### Create a signed webhook through the API

With an API key of an owner or admin (see
[[API and API Keys|Studio-API-and-API-Keys]]):

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

`events` takes the exact event names from the table below; an empty list
(`[]`) means every event. The webhook then appears in the app's list as usual.

### Events and payloads

| Event | When | Body |
|---|---|---|
| `deploy.live` | a deployment finished building and is serving | `{"event": "deploy.live", "deployment_id": 42, "url": "https://study.siamang.org/3f9a1c07b2de/", "survey_id": "3f9a1c07b2de"}` |
| `deploy.failed` | a deployment build failed | `{"event": "deploy.failed", "deployment_id": 42, "project": "acme-research/brand-2026", "environment": "main"}` |
| `deploy.stopped` | a deployment or preview was stopped | `{"event": "deploy.stopped", "deployment_id": 42, "project": "acme-research/brand-2026", "environment": "main"}` |
| `run.completed` | a flow run or Run all finished (manual or scheduled) | `{"event": "run.completed", "run_id": 311, "kind": "run_script", "script": "tables", "status": "completed"}` — for Run all: `{"event": "run.completed", "run_id": 312, "kind": "run_all", "status": "completed"}` |
| `run.failed` | a flow run or Run all failed | as `run.completed`, with `"event": "run.failed"` and `"status": "failed"` |

"Run to here" previews, connector runs, deposits and Saves send nothing.

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

Below the list of webhooks: **Recent deliveries** — "retried automatically with
backoff" — the organization's latest 50 deliveries, one row per event and
endpoint:

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

The payload is plain JSON without a `text` field. **A Slack incoming-webhook URL
does not accept it** — Slack refuses the request, and the delivery is marked
**failed**. The same applies to other chat tools that expect their own message
format. To get messages into chat, point the webhook at something that turns
the JSON into a message: an automation service such as Zapier or Make, or a
small endpoint of your own that calls Slack.

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
