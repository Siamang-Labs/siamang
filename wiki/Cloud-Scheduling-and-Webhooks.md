# Schedules & Webhooks

Two ways to put your project on autopilot: **schedules** run your analysis on a timetable,
and **webhooks** notify your own systems when something finishes. Both are a **Plus and
up** feature — see [[Plans & Billing|Cloud-Subscription-Tiers]].

## Schedules: run analysis on a timetable

A schedule runs your analysis without anyone clicking a button — for example, clean the
data and rebuild your report every night. You choose what runs, on which branch, and how
often (as a cron expression).

A schedule runs one of:

- **A single script** (`run_script`) — one analysis task, named by its task name from
  [[Project Config (siamang.yaml)|Cloud-siamang-yaml]].
- **Run all** (`run_all`) — every analysis task in order, producing the combined report.

### Add a schedule

In the web app, open your project's **Analysis** screen and go to **Schedules**. Add a
schedule by choosing:

- **What runs** — a single script (pick the task) or *Run all*.
- **Branch** — the branch to check out and run (usually `main`).
- **Cron** — a standard five-field cron expression (minute, hour, day-of-month, month,
  day-of-week), interpreted in UTC.
- **Enabled** — toggle a schedule on or off without deleting it.

A new schedule starts from when you create it; it does not back-fill runs it "missed"
before then. You can disable or remove a schedule at any time.

### Cron examples

```text
0 2 * * *       Every day at 02:00 UTC
30 7 * * 1-5    07:30 UTC on weekdays (Mon–Fri)
0 */6 * * *     Every 6 hours
0 9 * * 1       09:00 UTC every Monday
```

A nightly *Run all*, for instance, is `0 2 * * *`. To re-run just your `tables` script on
weekday mornings, schedule a `run_script` for that task with `30 7 * * 1-5`.

## Webhooks: get notified on events

A webhook lets the platform tell *your* systems when a deploy or a run finishes. You
register an endpoint URL, and the platform sends it an outgoing `POST` with a JSON body
each time a subscribed event happens.

### Events

| Event | Fires when |
| :--- | :--- |
| `deploy.live` | A deployment finished and the survey is live |
| `deploy.failed` | A deployment failed |
| `run.completed` | An analysis run finished successfully |
| `run.failed` | An analysis run failed |

### Register an endpoint

Webhook endpoints are set per organization, in your organization's settings. To add one,
provide:

- **URL** — where the platform should `POST`. A **Slack incoming-webhook URL works
  directly**, so you can get run/deploy notifications in a Slack channel with no extra
  glue.
- **Events** — the events to subscribe to. Leave the list **empty to receive all events**.
- **Secret** (optional) — a shared secret used to sign each request so you can verify it
  came from siamang Cloud (see below).
- **Enabled** — turn the endpoint on or off.

The app also keeps a **delivery log** for each endpoint, so you can see what was sent and
whether it succeeded. If a delivery fails, the platform retries it automatically with
increasing delays before giving up.

### What a delivery looks like

Each request is a JSON `POST` whose body includes the `event` name plus a few details
about what happened (for example a `run.completed` carries the run and script; a
`deploy.live` carries the survey URL). Every request also carries these headers:

- `Content-Type: application/json`
- `X-Siamang-Event: <event>` — the event name.
- `X-Siamang-Signature: sha256=<hex>` — present only when you set a secret; an HMAC-SHA256
  signature of the exact request body.

### Verify the signature

If you set a secret, check the signature on your side before trusting the payload. Compute
the HMAC-SHA256 of the raw request body with your secret and compare it to the header:

```python
import hashlib
import hmac

def verify(secret: str, body: bytes, header: str) -> bool:
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header)
```

Use the raw bytes of the body exactly as received (don't re-serialize the JSON first), or
the signatures won't match.

## See also

- [[Plans & Billing|Cloud-Subscription-Tiers]] — schedules and webhooks are Plus and up
- [[Analysis & Reports|Cloud-Analysis-and-Reporting]] — what a run produces
- [[Project Config (siamang.yaml)|Cloud-siamang-yaml]] — name the tasks a schedule runs
