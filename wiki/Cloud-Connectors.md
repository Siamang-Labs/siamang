# Connectors

Connectors move data in or out of external stores — object storage, data warehouses,
Google Sheets, or your own Postgres database. You use them to export a project table (say your
cleaned responses) to somewhere your team already works, or to pull an external table
into your project.

The Connectors screen unlocks on the **Plus** plan, and each target additionally
carries its own **minimum plan**: everyday destinations (Sheets, Excel 365, Supabase)
are Plus; object storage, warehouses, and bring-your-own infrastructure are Pro; custom
MCP servers are Corporate. The related **Git mirrors** (keeping your repository in sync
with an external remote, managed in **Repository → Remotes**) are gated per provider:
**GitHub from Plus; GitLab and self-hosted from Pro**. See
[[Plans & Billing|Cloud-Subscription-Tiers]].

## The catalog

Twelve targets transfer data today; `airtable`, `dropbox`, and `mcp` can be configured
but answer "coming soon" until they go live.

| Destination | `target` | Min. plan | Typical use |
| :--- | :--- | :--- | :--- |
| Google Sheets | `sheets` | Plus | Export a table to a spreadsheet |
| Excel on OneDrive / SharePoint | `excel365` | Plus | Write a table into an existing workbook |
| Supabase | `supabase` | Plus | Push a table out, or pull one in |
| Airtable *(coming soon)* | `airtable` | Plus | Sync a table into a base |
| Dropbox *(coming soon)* | `dropbox` | Plus | Drop an export file into a folder |
| Object storage — Amazon S3, Cloudflare R2, MinIO | `s3` | Pro | Drop an export file into a bucket |
| Google Cloud Storage | `gcs` | Pro | Drop an export file into a GCS bucket |
| Azure Blob Storage | `azure` | Pro | Drop an export file into a container |
| Your own Postgres (BYO database) | `database` | Pro | Push a table out, or pull one in |
| Google BigQuery | `bigquery` | Pro | Sync a table into a dataset |
| Snowflake | `snowflake` | Pro | Sync a table into a warehouse |
| SFTP server | `sftp` | Pro | Upload the export to a panel / agency exchange |
| REDCap | `redcap` | Pro | Import records into a REDCap project |
| Custom HTTP endpoint | `http` | Pro | `POST` the table to your own service |
| Custom MCP server *(coming soon)* | `mcp` | Corporate | Your own integration surface |

Two targets can also **import** an external table into your project: `database` and
`supabase`.

Live transfers share a few rules: each run **replaces** the destination's contents (no
incremental sync), all columns are written as **text**, exports are capped at
**100,000 rows** (Sheets 50,000; Excel 365 10,000), and connectors run on **manual
trigger** only.

## How you declare a connector

A connector is a task in your project's `siamang.yaml` (see
[[Project Config (siamang.yaml)|Cloud-siamang-yaml]]). You give it a `type: connector`,
pick a `target`, say which `table` to move and in which `direction`, name a project
`secret` for the credentials, and put destination details in a nested `config:` block:

```yaml
tasks:
  export_to_s3:
    type: connector
    target: s3
    direction: out                  # out = export from your project; in = import into it
    table: clean_responses          # the project table to move
    secret: aws_creds               # the name of a project secret (set in the web app)
    config:
      bucket: my-research-exports
      key: digital-life/responses.csv
```

Live export targets serialize the table as **CSV** (file-style destinations get a
`.csv` object; database-style destinations get a table of text columns). The
destination-specific settings always go **inside** `config:`. Each target requires a
different set of keys (below).

## Required `config` for each target

| `target` | Required `config` keys | Secret |
| :--- | :--- | :--- |
| `s3` | `bucket`, `key` | JSON `{access_key, secret_key}` (plus `endpoint` for R2 / MinIO) |
| `gcs` | `bucket`, `key` | Service-account JSON |
| `azure` | `container`, `path` | Connection string / SAS |
| `database` | — (optional `table`, `schema`) | `postgres://` DSN (required) |
| `sheets` | `spreadsheet_id` | Service-account JSON |
| `excel365` | `drive_id`, plus `item_id` or `item_path` | JSON `{tenant_id, client_id, client_secret}` |
| `supabase` | — (optional `table`, `schema`) | `postgres://` connection string (required) |
| `bigquery` | `dataset`, `table` | Service-account JSON |
| `snowflake` | `database`, `schema`, `table`, `warehouse` | JSON `{account, user, private_key}` (key-pair auth) |
| `sftp` | `host`, `path` | Password or private key |
| `redcap` | `api_url` | API token |
| `http` | `url` | Optional (sent as a bearer token) |

A few more examples:

```yaml
tasks:
  export_to_warehouse:
    type: connector
    target: bigquery
    direction: out
    table: clean_responses
    secret: bq_service_account
    config:
      dataset: research
      table: responses_export

  publish_to_sheet:
    type: connector
    target: sheets
    direction: out
    table: weighted_responses
    secret: sheets_service_account
    config:
      spreadsheet_id: 1A2b3C4d5E6f7G8h9I0jKlMnOpQrStUvWxYz
```

If you leave out a required key (for example an `s3` connector without a `bucket` or
`key`), the connector fails at **run time** with a message naming the missing keys —
commit validation does not check `config:` contents. What commit validation *does*
flag is a connector whose target is above your organization's plan (as a warning), so
you learn about the gate before you hit Run.

## Credentials: use a project secret, never inline

Never put credentials in `siamang.yaml` — the file is committed to your repository. Each
connector's `secret:` field names a **project secret** that you set separately in the web
app, under your project's settings. The platform looks up that named secret when the
connector runs.

Set the secret first (for example a value named `aws_creds`), then reference it by name
from the connector task. Project secrets are write-only in the app: you can set or replace
a value, but it is never shown back to you.

## Git mirrors

Git mirrors share the same integrations surface. A mirror keeps your project's
repository in sync with an external remote on **GitHub** (Plus and up) or **GitLab /
a self-hosted host** (Pro and up), so your
survey-as-code lives in your own organization's Git host as well. You set them up in
**Repository → Remotes** (not project settings): pick the provider, give the remote path,
and supply an access token as a project secret. From there you can **Sync now**,
**pause/resume**, or remove a mirror. See [[Repository & Editing|Cloud-Repository-and-Editing]].

## See also

- [[Plans & Billing|Cloud-Subscription-Tiers]] — connectors unlock at Plus, tiered per target
- [[Project Config (siamang.yaml)|Cloud-siamang-yaml]] — where connector tasks are declared
- [[Cloud Analysis SDK|Cloud-Analysis-SDK]] — `db.export_table` writes a table to a file
