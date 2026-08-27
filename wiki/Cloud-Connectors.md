# Connectors

Connectors move data in or out of external stores — object storage, data warehouses,
Google Sheets, or your own SQL database. You use them to export a project table (say your
cleaned responses) to somewhere your team already works, or to pull an external table
into your project.

Connectors are a **Pro / Corporate** feature. The same plan entitlement covers **Git
mirrors** (keeping your repository in sync with GitHub or GitLab), which are now managed
in **Repository → Remotes**. See [[Plans & Billing|Cloud-Subscription-Tiers]].

## The catalog

| Destination | `target` | Typical use |
| :--- | :--- | :--- |
| Object storage — Amazon S3, Cloudflare R2, MinIO | `s3` | Drop an export file into a bucket |
| Google Cloud Storage | `gcs` | Drop an export file into a GCS bucket |
| Azure Blob Storage | `azure` | Drop an export file into a container |
| Your own SQL database (Postgres / MySQL) | `database` | Push a table out, or pull one in |
| Google Sheets | `sheets` | Export a table to a spreadsheet |
| Google BigQuery | `bigquery` | Sync a table into a dataset |
| Snowflake | `snowflake` | Sync a table into a warehouse |

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
      key: digital-life/responses.parquet
```

The destination-specific settings always go **inside** `config:`. Each target requires a
different set of keys (below).

## Required `config` for each target

| `target` | Required `config` keys | Secret |
| :--- | :--- | :--- |
| `s3` | `bucket`, `key` | Optional (for private buckets) |
| `gcs` | `bucket`, `key` | Service-account JSON |
| `azure` | `container`, `path` | Connection string / SAS |
| `database` | — (a `dsn` may go in `config` instead of the secret) | DSN |
| `sheets` | `spreadsheet_id` | Service-account JSON |
| `bigquery` | `dataset`, `table` | Service-account JSON |
| `snowflake` | `database`, `schema`, `table` | Connection parameters |

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
`key`), the configuration is reported as invalid so you can fix it before it runs.

## Credentials: use a project secret, never inline

Never put credentials in `siamang.yaml` — the file is committed to your repository. Each
connector's `secret:` field names a **project secret** that you set separately in the web
app, under your project's settings. The platform looks up that named secret when the
connector runs.

Set the secret first (for example a value named `aws_creds`), then reference it by name
from the connector task. Project secrets are write-only in the app: you can set or replace
a value, but it is never shown back to you.

## Git mirrors

Git mirrors are the other half of the same plan entitlement. A mirror keeps your
project's repository in sync with an external remote on **GitHub** or **GitLab**, so your
survey-as-code lives in your own organization's Git host as well. You set them up in
**Repository → Remotes** (not project settings): pick the provider, give the remote path,
and supply an access token as a project secret. From there you can **Sync now**,
**pause/resume**, or remove a mirror. See [[Repository & Editing|Cloud-Repository-and-Editing]].

## See also

- [[Plans & Billing|Cloud-Subscription-Tiers]] — connectors and Git mirrors are Pro / Corporate
- [[Project Config (siamang.yaml)|Cloud-siamang-yaml]] — where connector tasks are declared
- [[Cloud Analysis SDK|Cloud-Analysis-SDK]] — `db.export_table` writes a table to a file
