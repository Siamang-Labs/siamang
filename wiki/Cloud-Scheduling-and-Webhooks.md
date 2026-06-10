# Cloud Scheduling and Webhooks

This page covers the platform's time- and event-driven plumbing:

- **Cron schedules** that fire analysis runs on a timetable.
- **Incoming Gitea webhooks** that turn a `git push` into a validation job.
- **Outgoing webhooks** that notify your endpoints of terminal events, with a
  signed payload and exponential-backoff retries.

All of these are driven by ARQ cron jobs registered in
`worker/app/settings.py`:

```python
cron_jobs = [
    cron(scheduler_tick,        second=0),                          # fire due schedules every minute
    cron(webhook_retry_tick,    second=15),                         # retry failed deliveries every minute
    cron(reap_deployments,      minute=set(range(0, 60, 5)), second=30),
    cron(cleanup_expired_trials, minute={0, 30}),
    cron(purge_stale_previews,  hour={3}, minute={15}),
]
```

## Scheduled analysis runs

A **schedule** ties a cron expression to either a single analysis script
(`run_script`) or a full `run_all`, on a chosen branch. Schedules are managed
through the API (`api/app/routers/schedules.py`):

- `GET /projects/{id}/schedules` — list schedules.
- `POST /projects/{id}/schedules` — create one (role `analyst`+).
- `DELETE /projects/{id}/schedules/{schedule_id}` — remove one.

The create payload (`ScheduleIn`):

```json
{
  "kind": "run_all",          // "run_script" or "run_all"
  "script_name": null,        // required when kind == "run_script"
  "cron": "0 2 * * *",        // standard 5-field cron; validated with croniter
  "branch": "main",
  "enabled": true
}
```

The cron expression is validated with `croniter` on create, and `script_name` is
required for `run_script` schedules. Scheduling is a paid feature, so creating a
schedule checks the org's plan (see [[Cloud Subscription Tiers|Cloud-Subscription-Tiers]]).

### The `scheduler_tick` cron

`scheduler_tick` runs **once a minute** (`worker/app/tasks/scheduler.py`):

1. Load enabled schedules joined with their repo and `last_run_at`
   (`due_schedules`).
2. For each one, decide whether it is **due** with the pure `is_due()` check
   (`worker/app/scheduler_core.py`) — `croniter` computes the next fire time from
   `last_run_at` (or one minute ago if it has never run, so a brand-new schedule
   does not backfill its whole missed history).
3. For a due schedule, create a `runs` row and enqueue the matching job —
   `run_all` or `run_script` — checking out the schedule's **branch name**
   directly (no Gitea HEAD lookup, keeping the tick cheap), then stamp
   `last_run_at` (`mark_schedule_run`).

One broken schedule (bad cron, enqueue hiccup) is logged and skipped so it never
starves every other org's schedules. The tick returns `{checked, fired, errors}`.

### A cron example

```yaml
# Run all analysis tasks every night at 02:00 UTC, on the main branch.
kind: run_all
cron: "0 2 * * *"
branch: main
enabled: true
```

```yaml
# Re-run just the daily tables on weekdays at 07:30 UTC.
kind: run_script
script_name: tables
cron: "30 7 * * 1-5"
branch: main
```

## Incoming Gitea push webhooks

Validation is triggered by a Gitea `push` webhook at `POST /webhooks/git`
(`api/app/routers/webhooks.py`):

1. The raw body is verified against the configured `git_webhook_secret` using an
   HMAC-SHA256 signature in the `X-Gitea-Signature` header; a bad signature is
   rejected with `401`.
2. The project is resolved by `repository.id` (the `gitea_repo_id`). An unknown
   repo is acknowledged without action (`{"status": "ignored"}`).
3. A `commit_status` row is upserted to `pending` for the pushed commit (`after`)
   and branch.
4. A `validate` job is enqueued with the commit SHA, branch, and repo full name.

The endpoint responds `202 Accepted`. The rest of validation is covered in
[[Cloud Survey Lifecycle|Cloud-Survey-Lifecycle]].

## Outgoing webhooks

An organization can register webhook **endpoints** that receive a JSON payload on
terminal events — `deploy.live`, `deploy.failed`, `run.completed`,
`run.failed`. (Slack-compatible incoming-webhook URLs work too.) Endpoints are
managed under the org routes (`api/app/routers/orgs.py`):

- `GET /{org}/webhooks` — list endpoints.
- `POST /{org}/webhooks` — create one (role `admin`+); paid feature.
- `DELETE /{org}/webhooks/{webhook_id}` — remove one.
- `GET /{org}/webhooks/deliveries` — the **delivery journal** (newest first).

The create payload (`WebhookIn`):

```json
{
  "url": "https://example.com/hooks/siamang",
  "secret": "whsec_…",   // optional; enables HMAC signing
  "events": [],          // empty list = subscribe to all events
  "enabled": true
}
```

### Delivery, signing, and the journal

When a task finishes it calls `notify.emit(...)`, which POSTs the payload to each
enabled endpoint subscribed to the event (`worker/app/notify.py`). Delivery is
fully best-effort: any failure — including journaling — is swallowed so the
originating deploy/run task never breaks.

Each request carries:

- `Content-Type: application/json`
- `X-Siamang-Event: <event>`
- `X-Siamang-Signature: sha256=<hex>` — present only when the endpoint has a
  secret; the HMAC-SHA256 of the exact request body.

Verify the signature on your side:

```python
import hashlib, hmac

def verify(secret: str, body: bytes, header: str) -> bool:
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header)
```

Every attempt is recorded in the `webhook_deliveries` journal. A successful POST
is marked `ok`; a failure (any `>= 400` status or transport error) is saved as
`pending` with the error and a `next_attempt_at`.

### Retry with backoff — the `webhook_retry_tick` cron

`webhook_retry_tick` runs every minute and calls `retry_due_deliveries`, which
re-sends `pending` deliveries whose `next_attempt_at` has passed. Rows are
claimed with `FOR UPDATE … SKIP LOCKED` so concurrent ticks never double-send.
On each retry:

- Success → marked `ok`.
- Another failure → `next_attempt_at` pushed out by exponential backoff
  (`2, 4, 8, …` minutes, capped at 60) until `MAX_ATTEMPTS` (5).
- Exhausted, or the endpoint was disabled after the event fired → marked
  `failed` with the last error.

The delivery journal therefore always shows the terminal state of every
notification, which the `GET /{org}/webhooks/deliveries` endpoint surfaces in the
web app.

## See also

[[Cloud Survey Lifecycle|Cloud-Survey-Lifecycle]] · [[Cloud Analysis and Reporting|Cloud-Analysis-and-Reporting]] · [[Cloud REST API|Cloud-REST-API]] · [[Project Config (siamang.yaml)|Cloud-siamang-yaml]] · [[Cloud Subscription Tiers|Cloud-Subscription-Tiers]]
