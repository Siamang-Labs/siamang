# API and API Keys

Everything the Studio app does goes through a REST API, and you can call the
same API from a script: pull exports every night, download a bundle for the
archive, start Run all from your pipeline, register a signed webhook. This page
covers API keys, the basics of calling the API, a reference of the endpoints
you are most likely to script, and worked examples.

---

## API keys

A personal API key lets a script act **as you**. Create and revoke keys in
**Profile → API keys** (full walkthrough in
[[Account and Profile|Studio-Account-and-Profile]]):

1. Type a name in **Key name (e.g. ci-pipeline)** — up to 80 characters — and
   click **Create key** (or press `Enter`).
2. Copy the token from "New key — copy it now, it won't be shown again:" with
   **Copy**. Tokens look like `sck_` followed by 43 characters.
3. To revoke, click **Revoke** on the key's row and confirm **Revoke API key**.
   The key stops working at once and stays listed as **revoked**.

The list shows each key's name, its first characters (`sck_ab12cd34…`) and
"used *date*" or "never used".

What a key can do:

- **Everything you can do**, in **every organization you belong to**, with your
  role in each. There are no per-key scopes and no read-only keys. Use one key
  per script, store it like a password, and revoke rather than share.
- Keys created in the app **do not expire**. The API accepts an optional
  lifetime when you create a key through it (`expires_days`, 1–730); such a key
  stops working after that time.
- Only a hash of the token is kept; a lost key cannot be shown again — create a
  new one.
- Creating and revoking a key is recorded in the **Activity** of every
  organization you belong to (`api_key.create`, `api_key.revoke`), with the
  key's first characters (`sck_ab12cd34`) as the target and its name in the
  details — never the token. The organization-wide Activity is visible to
  owners and admins.

---

## Basics

| | |
|---|---|
| Base URL | `https://api.studio.siamang.org` |
| Authentication | header `Authorization: Bearer sck_…` on every request |
| Request bodies | JSON (`Content-Type: application/json`), except file uploads (multipart) |
| Responses | JSON, except downloads (files, zips, `.py`, Markdown) |
| Identifiers | organizations by **slug** (`acme-research`), projects by numeric **id**, Saves by their **number** (`seq`) |

Find a project's id with `GET /orgs/{org}/projects` (example 1 below).

### Errors

Errors come back as JSON with a `detail` field — usually a sentence, for
example `{"detail": "only owners and admins can create projects"}`; for
invalid input, a list of the fields that failed.

| Status | Meaning |
|---|---|
| 400 | the request is malformed (for example an unsupported export format) |
| 401 | missing, invalid or revoked key (`"invalid API key"`) |
| 402 | not included in the organization's plan, or a plan limit reached — the message names the plan |
| 403 | your role is not enough (`"insufficient role"`), or the workspace is frozen and read-only |
| 404 | not found — also returned for organizations and projects you are not a member of |
| 409 | a conflict: someone saved since your `base_seq`, a colleague has a flow open that your Save would delete or rename, a run is already in progress, a flow did not pass the engine check, the project was never saved |
| 413 | an export or bundle is larger than 100,000 rows, or an upload is larger than 50 MB |
| 422 | a document or body did not validate, or a table cannot be written in the export format asked for |
| 429 | a rate limit (for example preview runs per hour) |

> **Note.** The interactive API documentation (`/docs`) is turned off on the
> hosted service. Use this page and the examples below.

---

## Endpoint reference

**(admin)** marks endpoints that need the **owner** or **admin** role; the rest
need membership of the organization, and anything that changes a project needs
the member role or higher.

### Account and organizations

| Method and path | What it does |
|---|---|
| `GET /auth/me` | you and your memberships |
| `GET /orgs` | your organizations |
| `GET /orgs/{org}/projects` | the organization's projects: `id`, `slug`, `name`, `current_snapshot_seq`, `responses` |
| `POST /orgs/{org}/projects` **(admin)** | create a project: `{"slug": "…", "name": "…", "template": "empty"}`. A slug that breaks the rule answers 422 with "a project's address is 3 to 64 characters — lowercase letters, digits and hyphens — and starts and ends with a letter or a digit"; one the organization already has answers 409 ("project slug already exists in org") — unlike the app's **New project** dialog, the API does not add `-2` for you |
| `GET /orgs/{org}/audit` **(admin)** | the organization's activity log |
| `GET /auth/api-keys` · `POST /auth/api-keys` · `DELETE /auth/api-keys/{id}` | list, create (`{"name": "…", "expires_days": 90}`), revoke your keys |

### Data

| Method and path | What it does |
|---|---|
| `GET /projects/{id}/database/tables` | the project's tables with row counts |
| `GET /projects/{id}/database/tables/{table}/schema` | a table's columns |
| `GET /projects/{id}/database/tables/{table}/preview?limit=100` | up to `limit` rows (1–1,000; default 100), newest first when the table has a `created_at` or `id` column (as `responses` does). For `responses`, the answers come as one column per variable, in the questionnaire's order, as in the **Data** tab. Optional: `q` (up to 200 characters) searches **the whole table** — a row matches when any of its values contains the text, ignoring case (a response id, a respondent id, a panel id from the link, an answer); `outcome` = `completed`, `screened_out` or `partial` keeps those responses. With either, `matched` gives how many rows of the whole table match (the page holds at most `limit` of them); without, it is `null`. An unknown outcome answers 400 ("unknown outcome '*x*'; one of completed, screened_out, partial"), as does `outcome` on a table without response outcomes ("*table* has no response outcomes") |
| `GET /projects/{id}/database/tables/{table}/export?format=…` | the whole table as a file: `csv`, `xlsx`, `parquet`, `sav` (SPSS), `dta` (Stata) or `sqlite`; SPSS and Stata files carry the codebook labels; up to 100,000 rows. For `responses`: one column per variable in the questionnaire's order, then the fieldwork columns `url_<name>`, `duration_s`, `started_at`, `captcha`, `tab_switches`, `hidden_seconds`, `pastes` (see [[Data Exports\|Studio-Data-Exports]]). A table the format cannot hold answers 422 ("The table cannot be written as .*fmt*: *reason*"). Each download is recorded in the project's Activity as `data.export` |
| `DELETE /projects/{id}/database/responses/{response_id}` **(admin)** | delete one response (recorded in Activity); the quota cells of its survey are recounted from the responses that remain, so a cell it filled goes down |

### Saves and documents

| Method and path | What it does |
|---|---|
| `GET /projects/{id}/snapshots?limit=50&offset=0` | Saves, newest first (up to 200 per page). Each has `validation_state`, `issues` and `flow_errors` — the names of the flows that failed the engine check at that Save (they leave the state at `warnings` but cannot run) |
| `GET /projects/{id}/snapshots/{seq}` | one Save with every document's content |
| `GET /projects/{id}/snapshots/{seq}/diff?against={seq2}` | line diffs per changed document |
| `GET /projects/{id}/snapshots/{seq}/generated/survey/questionnaire.json` | that Save's `questionnaire.py` (use a flow's path, e.g. `flows/tables.flow.json`, for its `.py`) |
| `GET /projects/{id}/snapshots/{seq}/bundle?data=none` or `data=latest` | the research bundle zip, optionally with the responses |
| `GET /projects/{id}/snapshots/{seq}/methods` | the Methods draft as Markdown |
| `POST /projects/{id}/snapshots` | Save: `{"documents": {"<path>": <content>}, "message": "…", "base_seq": 17}` (a `null` content deletes a flow). To rename a flow so that its schedules and comments follow it, delete the old path (`null`), add the new one (its `name` set to the new name) and name the pair in `"renames": {"flows/old.flow.json": "flows/new.flow.json"}`; a pair that is not deleted and added in the same Save answers 422 ("rename '*old*' → '*new*': a rename deletes the old flow and adds the new one in the same Save"), and a new name that already exists answers 409 ("a flow named '*new*' already exists"). A Save that would delete or rename a flow a colleague has open answers 409 naming them |
| `POST /projects/{id}/snapshots/{seq}/restore` | restore as a new Save |
| `PUT /projects/{id}/snapshots/{seq}/tag` | pre-register: `{"tag": "preregistered"}`, or `{"tag": null}` to remove |
| `POST /projects/{id}/snapshots/{seq}/deposit` | deposit: `{"target": "zenodo", "secret_key": "ZENODO_TOKEN", "publish": false, "sandbox": false, "data": "none"}` (OSF: `"target": "osf", "osf_node": "ab3cd"`) |
| `GET /projects/{id}/deposits` | the project's deposits with status, DOI and URL |
| `GET /projects/{id}/documents` | the project's documents |
| `GET /projects/{id}/documents/{path}` | a document's current content, e.g. `studio/settings.json` |
| `POST /projects/{id}/documents/{path}/check` | run the engine's check on a document without saving: `{"content": {…}}` |

### Flows and runs

| Method and path | What it does |
|---|---|
| `GET /projects/{id}/scripts` | the project's flows, in the order Run all runs them. Each has `check_state` (`valid`, `warnings` or `error` at the current Save) with its `check_issues`, and its newest finished run of its own (manual, scheduled or Live — not Run all's): `last_run_status`, `last_run_started_at`, `last_run_finished_at` (`null` when it has none since **Reset history**) |
| `POST /projects/{id}/scripts/{flow}/run` | run one flow on the current Save. A flow whose `check_state` is `error` answers 409: "flow '*name*' did not pass the engine check at Save #*N*: open it, fix its errors and save before running it" |
| `POST /projects/{id}/scripts/run-all` | Run all |
| `GET /projects/{id}/runs?limit=50&type=…&path=…` | run history, newest first; `type` is `analysis`, `analysis_all` or `connector` |
| `GET /projects/{id}/runs/{run_id}/outputs/download?path=…` | a link (valid 5 minutes) to one output file of a run |
| `GET /projects/{id}/reports` | stored reports; `combined` is `true` on Run all's combined report (the path set under **Settings → Reports**) |
| `GET /projects/{id}/reports/{path}/markdown` | a Markdown report ready to open elsewhere, `{path}` being its path from the list (for example `outputs/tables/tables.md`): a zip with the `.md` and the figures it refers to in one folder (`tables.zip` → `tables/tables.md`, `tables/fig_1.png`), or the `.md` itself when it shows no figure. Errors: 400 "not a Markdown report", 404 "the stored report could not be read", 503 "object storage is not configured" |

### Connectors, schedules, secrets, files

| Method and path | What it does |
|---|---|
| `GET /projects/{id}/connectors` | declared connectors |
| `POST /projects/{id}/connectors/{name}/run` **(admin)** | run a connector; its runs: `GET /projects/{id}/runs?type=connector&path={name}` |
| `GET /projects/{id}/schedules` · `POST …/schedules` | list; create `{"kind": "run_all", "cron": "0 2 * * *"}` or `{"kind": "run_script", "flow_name": "tables", "cron": "…"}` |
| `PATCH /projects/{id}/schedules/{sid}` · `POST …/{sid}/run` · `DELETE …/{sid}` | change `{"enabled": false}` / `{"cron": "…"}`, run now, remove |
| `GET /projects/{id}/secrets` | secret **names** only |
| `POST /projects/{id}/secrets` **(admin)** · `DELETE /projects/{id}/secrets/{key}` **(admin)** | set `{"key": "…", "value": "…"}` (replaces an existing key), delete |
| `GET /projects/{id}/files` | stored files (uploads and run outputs) |
| `POST /projects/{id}/files` | upload (multipart field `upload`, up to 50 MB) |
| `GET /projects/{id}/files/{file_id}/download` | `{"url": …, "expires_in": 300}` |
| `DELETE /projects/{id}/files/{file_id}` | delete a file |

### Projects, activity and webhooks

| Method and path | What it does |
|---|---|
| `GET /projects/{id}` | the project, with `current_snapshot_seq` |
| `PATCH /projects/{id}` **(admin)** | rename: `{"name": "…"}` |
| `DELETE /projects/{id}` **(admin)** | delete the project permanently |
| `GET /projects/{id}/audit?limit=100` | the project's activity (up to 500) |
| `GET /projects/{id}/deployments` | deployments with status and URL, plus `responses` (completed interviews so far — not partials, not screen-outs), `closes_at` (when it stops accepting responses), `closes_at_manual` (the date was set on the card), `redirect_after_close` and `one_response_per_browser` |
| `POST /projects/{id}/deployments/{dep}/closing-date` | move the closing date without a new Save: `{"closes_at": "2026-10-31T18:00:00Z"}`, `{"closes_at": null}` for none, or `{"from_save": true}` to take the Save's date again. A date in the past answers 422 ("the closing date must be in the future — use Close to stop collecting now"); a preview answers 409 ("a preview has no closing date") |
| `POST /projects/{id}/deployments/{dep}/one-response-per-browser` | `{"one_response_per_browser": true}` or `false`; a preview answers 409 ("a preview takes no responses") |
| `GET /projects/{id}/dashboard/summary?days=14` | fieldwork totals: `responses` (every row), `completed` (what quota cells and response caps count), `screened_out`, `partial`, `partial_percent`, `last_response_at` and `per_day` (the last `days` days, 1–90). `respondents` and `duplicates` are still there for older scripts, but they count interviews, not people: Studio cannot tell whether two responses came from the same person |
| `GET /projects/{id}/dashboard/frequencies?variable=…` · `GET …/dashboard/crosstab?rows=…&cols=…` | the counts behind **Data → Insights**: a variable's `bins` and their `base`, or a crosstab's `cells` and totals (`multiple` is true for a multiple choice, whose shares add up to more than 100 %). By default over every row of `responses`; `environment=main` keeps that environment's responses plus rows no deployment claims (imported or sample data), and `only_completed=true` leaves out partial interviews — the rows a flow's **Responses** node with that **Environment** and **Only completed responses** reads |
| `GET /ingest/{survey_id}/status` | **no key needed** — whether a published survey is collecting, as its page asks when it opens: `state` is `open`, `closed`, `paused`, `deadline` (past its closing date) or `full` (a response cap is reached), with `redirect_url` (the environment's `redirect_after_close`, for a closed or past-deadline survey) and `one_response_per_browser`. An unknown survey answers 404 |
| `GET /orgs/{org}/webhooks` · `POST …/webhooks` · `DELETE …/webhooks/{id}` **(admin)** | list, create, delete webhooks. Each listed webhook has `signed` (it has a secret) and `unknown_events` (subscribed names no event carries); creating one with an unknown event name answers 422 (see [[Schedules and Webhooks\|Studio-Schedules-and-Webhooks]]) |
| `GET /orgs/{org}/webhooks/deliveries?limit=50` **(admin)** | the delivery log (up to 200) |

A frozen workspace answers every change with 403; reading and exporting keep
working.

---

## Worked examples

The examples use `curl` and [`jq`](https://jqlang.org/). Set your key once:

```bash
export SIAMANG_KEY="sck_…"
API=https://api.studio.siamang.org
AUTH="Authorization: Bearer $SIAMANG_KEY"
```

### 1. List your organizations and projects

```bash
curl -s -H "$AUTH" $API/orgs | jq -r '.[] | "\(.slug)\t\(.name)\t\(.plan)"'

curl -s -H "$AUTH" $API/orgs/acme-research/projects \
  | jq -r '.[] | "\(.id)\t\(.slug)\tSave #\(.current_snapshot_seq)\t\(.responses) responses"'
```

### 2. Export the responses as SPSS

```bash
curl -s -H "$AUTH" -o responses.sav \
  "$API/projects/42/database/tables/responses/export?format=sav"
```

The file carries variable and value labels from the current codebook. Its
answer columns follow the questionnaire's order, and responses collected by an
earlier version of the survey page are read in today's layout — for example a
legacy "Other (please specify)" answer as the question's Other code in
`<variable>` plus its text in `<variable>_other`. The fieldwork columns
(`url_<name>`, `duration_s`, `started_at`, `captcha`, `tab_switches`,
`hidden_seconds`, `pastes`) come after them, so a script that reads columns by
position should read them by name. Use `format=csv`, `xlsx`, `parquet`, `dta`
or `sqlite` for other formats. A table above 100,000 rows answers 413 with
nothing generated. What every column means is on
[[Data Exports|Studio-Data-Exports]].

### 3. Download the research bundle of a Save

```bash
SEQ=$(curl -s -H "$AUTH" $API/projects/42 | jq .current_snapshot_seq)
curl -s -H "$AUTH" -OJ "$API/projects/42/snapshots/$SEQ/bundle?data=latest"
# → brand-2026-s17-data.zip
```

`-OJ` keeps the file name Studio sends: `<project-slug>-s<N>.zip`, or
`-data.zip` with `data=latest`.

### 4. Start Run all and wait for it

```bash
RUN=$(curl -s -X POST -H "$AUTH" $API/projects/42/scripts/run-all | jq .id)

while true; do
  STATUS=$(curl -s -H "$AUTH" "$API/projects/42/runs?type=analysis_all&limit=5" \
           | jq -r ".[] | select(.id == $RUN) | .status")
  echo "run $RUN: $STATUS"
  [ "$STATUS" = completed ] || [ "$STATUS" = failed ] && break
  sleep 10
done
```

A run's `status` goes `queued` → `running` → `completed` or `failed`. Run all
runs the flows in dependency order (a flow after the flows whose tables it
reads) and does not stop at a failed flow: the flows that do not need its
tables still run, and the run ends as `failed` once every flow has had its
turn. The last line of its `log` names them — "failed: *names*" (then
"; skipped: *names*" for flows that needed a failed one). The reports of the
flows that succeeded are stored even then, and the combined report is written
from them as "Combined report (incomplete)" (the log says "combined report
(incomplete): reports/report.md"). Starting a second Run all while one is in
progress answers 409 ("a run-all is already in progress for this project"). A
project with no flows answers 409 ("project has no flows to run"). To run one
flow use `POST $API/projects/42/scripts/tables/run`; it answers 409 while that
flow is already running ("a run for this flow is already in progress") or when
it did not pass the engine check at the current Save.

To see where each flow stands without walking the run history, read the flows
list:

```bash
curl -s -H "$AUTH" $API/projects/42/scripts \
  | jq -r '.[] | "\(.name)\t\(.check_state)\t\(.last_run_status // "never")\t\(.last_run_finished_at // "")"'
```

### 5. Download an output file of the latest run

```bash
curl -s -H "$AUTH" "$API/projects/42/runs?type=analysis&limit=1" \
  | jq -r '.[0] | "run \(.id):", (.outputs[] | select(.downloadable) | .path)'

URL=$(curl -s -G -H "$AUTH" \
        --data-urlencode "path=report.html" \
        "$API/projects/42/runs/311/outputs/download" | jq -r .url)
curl -s -o report.html "$URL"
```

The download link is valid for 5 minutes and needs no key.

### 6. Create a signed webhook for failures

```bash
curl -s -X POST -H "$AUTH" -H "Content-Type: application/json" \
  $API/orgs/acme-research/webhooks \
  -d '{"url": "https://hooks.example.com/siamang",
       "secret": "whsec_3f1c…",
       "events": ["deploy.failed", "run.failed"],
       "enabled": true}'
```

Needs the owner or admin role and the Plus plan. The event names, the payloads
and the signature format are in
[[Schedules and Webhooks|Studio-Schedules-and-Webhooks]]. The same webhook —
secret and event filter included — can also be added in **Organization
settings → Integrations → Webhooks**; either way the secret is never returned
by the API or shown again. Creating and deleting webhooks is recorded in the
organization's Activity (`webhook.create`, `webhook.delete`).

### 7. Find a respondent's responses

```bash
curl -s -G -H "$AUTH" \
  --data-urlencode "q=PANEL-83921" --data-urlencode "limit=20" \
  "$API/projects/42/database/tables/responses/preview" \
  | jq '{matched, ids: [.rows[].id]}'
```

`q` searches every row of the table, not only the newest ones — useful for an
erasure request about an old response. `matched` is how many rows contain the
text; `rows` holds the newest `limit` of them. Add `outcome=completed` (or
`screened_out`, `partial`) to narrow it further. Deleting a response is
`DELETE /projects/42/database/responses/{id}` (owner or admin).

### 8. Download a report with its figures

```bash
curl -s -H "$AUTH" $API/projects/42/reports | jq -r '.[] | select(.path | endswith(".md")) | .path'

curl -s -H "$AUTH" -OJ "$API/projects/42/reports/outputs/tables/tables.md/markdown"
# → tables.zip (tables/tables.md and its figures), or tables.md when it has none
```

### 9. Check whether a survey is collecting

```bash
curl -s https://api.studio.siamang.org/ingest/3f9a1c07b2de/status
# → {"state": "open", "redirect_url": null, "one_response_per_browser": false}
```

This is the public check a survey page makes as it opens, so it needs no key;
use the `survey_id` from `GET /projects/{id}/deployments`. `state` is `open`,
`closed`, `paused`, `deadline` or `full`. It is rate-limited (429 "rate limit
exceeded; slow down"), so poll it gently.

---

## Change studio/settings.json through the API

Some settings have no editor in the app yet — the environments list, and
editing or removing a connector. Until they do, you can save a new version of
the settings document yourself. Any member can do this; it is an ordinary Save
and shows in History.

```bash
# 1. The current settings document and the current Save number
curl -s -H "$AUTH" "$API/projects/42/documents/studio/settings.json" | jq .content > settings.json
SEQ=$(curl -s -H "$AUTH" $API/projects/42 | jq .current_snapshot_seq)

# 2. Edit settings.json — e.g. set "max_responses" of "main" in "environments",
#    give it "closes_at": "2026-12-01T00:00:00Z" and
#    "redirect_after_close": "https://example.org/thanks",
#    or remove an entry from "connectors".

# 3. Save it as a new version
jq -n --slurpfile s settings.json --argjson base "$SEQ" \
  '{documents: {"studio/settings.json": $s[0]}, message: "Raise the main cap", base_seq: $base}' \
  | curl -s -X POST -H "$AUTH" -H "Content-Type: application/json" \
         --data @- "$API/projects/42/snapshots" | jq '{seq, validation_state}'
```

- Send the **whole** document, not just the part you changed.
- `base_seq` makes the Save fail with 409 instead of overwriting a colleague's
  Save made in between; fetch again and retry.
- A malformed document is refused with 422 and nothing is saved. An environment
  name uses lowercase letters, digits and `-`, starting with a letter, and must
  be unique; `max_responses` is a whole number of at least 1. Connector names
  must be unique and use lowercase letters, digits and `_`.
- New environments, caps, `closes_at` and `redirect_after_close` take effect
  when you next publish to that environment; until then its **Distribute**
  card adds "the environment’s closing settings changed — republish *env* to
  apply" when the settings name a redirect, or an earlier closing date, that
  the live deployment does not have yet. A closing date set on the
  **Distribute** card (`closes_at_manual`) outlives a republish: `closes_at`
  from the settings applies to that deployment again only after
  `{"from_save": true}` on its `closing-date` endpoint (**Use the Save’s
  date** in the app). A cap counts completed
  interviews only (not screen-outs or partial responses). The survey closes
  at the earlier of `closes_at` and the questionnaire's own deadline, and
  `redirect_after_close` is used only when it is an `http://` or `https://`
  address.
- A **Python version** other than 3.11 in `runtime` makes the Save
  **warnings** (`RUNTIME_PYTHON`): Studio runs flows on 3.11, and the setting
  only tells a research bundle which version to ask for.

## See also

- [[Account and Profile|Studio-Account-and-Profile]]
- [[Schedules and Webhooks|Studio-Schedules-and-Webhooks]]
- [[Data Exports|Studio-Data-Exports]]
- [[Reproducibility: Code, Bundles and Citation|Studio-Reproducibility]]
- [[Security and Privacy|Studio-Security-and-Privacy]]

<!-- studio-nav -->
---

← [[Schedules and Webhooks|Studio-Schedules-and-Webhooks]] · [Studio contents](Studio-Overview#all-pages) · [[Working Together|Studio-Collaboration]] →
