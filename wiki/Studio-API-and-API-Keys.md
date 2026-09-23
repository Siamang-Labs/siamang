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
| 409 | a conflict: someone saved since your `base_seq`, a run is already in progress, the project was never saved |
| 413 | an export or bundle is larger than 100,000 rows |
| 422 | a document or body did not validate |
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
| `POST /orgs/{org}/projects` **(admin)** | create a project: `{"slug": "…", "name": "…", "template": "empty"}` |
| `GET /orgs/{org}/audit` **(admin)** | the organization's activity log |
| `GET /auth/api-keys` · `POST /auth/api-keys` · `DELETE /auth/api-keys/{id}` | list, create (`{"name": "…", "expires_days": 90}`), revoke your keys |

### Data

| Method and path | What it does |
|---|---|
| `GET /projects/{id}/database/tables` | the project's tables with row counts |
| `GET /projects/{id}/database/tables/{table}/schema` | a table's columns |
| `GET /projects/{id}/database/tables/{table}/preview?limit=100` | the first rows |
| `GET /projects/{id}/database/tables/{table}/export?format=…` | the whole table as a file: `csv`, `xlsx`, `parquet`, `sav` (SPSS), `dta` (Stata) or `sqlite`; SPSS and Stata files carry the codebook labels; up to 100,000 rows |
| `DELETE /projects/{id}/database/responses/{response_id}` **(admin)** | delete one response (recorded in Activity) |

### Saves and documents

| Method and path | What it does |
|---|---|
| `GET /projects/{id}/snapshots?limit=50&offset=0` | Saves, newest first (up to 200 per page) |
| `GET /projects/{id}/snapshots/{seq}` | one Save with every document's content |
| `GET /projects/{id}/snapshots/{seq}/diff?against={seq2}` | line diffs per changed document |
| `GET /projects/{id}/snapshots/{seq}/generated/survey/questionnaire.json` | that Save's `questionnaire.py` (use a flow's path, e.g. `flows/tables.flow.json`, for its `.py`) |
| `GET /projects/{id}/snapshots/{seq}/bundle?data=none` or `data=latest` | the research bundle zip, optionally with the responses |
| `GET /projects/{id}/snapshots/{seq}/methods` | the Methods draft as Markdown |
| `POST /projects/{id}/snapshots` | Save: `{"documents": {"<path>": <content>}, "message": "…", "base_seq": 17}` (a `null` content deletes a flow) |
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
| `GET /projects/{id}/scripts` | the runnable flows |
| `POST /projects/{id}/scripts/{flow}/run` | run one flow on the current Save |
| `POST /projects/{id}/scripts/run-all` | Run all |
| `GET /projects/{id}/runs?limit=50&type=…&path=…` | run history, newest first; `type` is `analysis`, `analysis_all` or `connector` |
| `GET /projects/{id}/runs/{run_id}/outputs/download?path=…` | a link (valid 5 minutes) to one output file of a run |
| `GET /projects/{id}/reports` | stored reports |

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
| `GET /projects/{id}/deployments` | deployments with status and URL |
| `GET /orgs/{org}/webhooks` · `POST …/webhooks` · `DELETE …/webhooks/{id}` **(admin)** | list, create, delete webhooks |
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

The file carries variable and value labels from the current codebook. Use
`format=csv`, `xlsx`, `parquet`, `dta` or `sqlite` for other formats. A table
above 100,000 rows answers 413 with nothing generated.

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

A run's `status` goes `queued` → `running` → `completed` or `failed`. Starting
a second Run all while one is in progress answers 409 ("a run-all is already in
progress for this project"). A project with no flows answers 409 ("project has
no flows to run"). To run one flow use `POST $API/projects/42/scripts/tables/run`.

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

Needs the owner or admin role and the Plus plan. The event names and the
signature format are in
[[Schedules and Webhooks|Studio-Schedules-and-Webhooks]]; this is currently
the only way to set a signing secret or an event filter.

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
- New environments and caps take effect when you next publish to that
  environment.

## See also

- [[Account and Profile|Studio-Account-and-Profile]]
- [[Schedules and Webhooks|Studio-Schedules-and-Webhooks]]
- [[Data Exports|Studio-Data-Exports]]
- [[Reproducibility: Code, Bundles and Citation|Studio-Reproducibility]]
- [[Security and Privacy|Studio-Security-and-Privacy]]
