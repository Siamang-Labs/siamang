# Connectors

*(Plus)* A **connector** moves a project table to another system — a Google
Sheet, an Excel workbook, cloud storage, a warehouse, a CRM, a server — or brings
a table from a Postgres database into the project. This page covers the
Connectors screen, adding and running a connector, every target with its
settings and credentials, and the rules and limits.

Connectors live in **Project → Settings → Connectors**. On the Free plan the
tab shows "Connectors is a Plus feature" with **View plans**.

---

## How connectors work

- A connector is **declared** in the project's `studio/settings.json`: a name, a
  target, a direction, a project table, the name of a secret and the target's
  settings. Adding one creates a **Save** ("Add connector *name*"), so the
  declaration is versioned and travels in the research bundle.
- Its **credentials** are a project secret (see
  [Secrets](Studio-Project-Settings#secrets)) — encrypted, write-only, and
  replaceable without touching the connector.
- You **run** it on demand. Each run uses the connector as declared in the
  project's current Save, reads the table at that moment, and writes the whole
  table to the destination.

> **Current limitation.** Connectors run only when someone clicks **Run
> export** / **Run import** (or calls the API). They cannot be put on a
> schedule, and a connector run sends no webhook and no email.

---

## The Connectors screen

A note at the top: "Connectors move project data in and out of external
systems. **Add** declares one in studio/settings.json (a new Save); its
credential lives under Settings → Secrets."

The catalog is grouped by what your plan can do with each target:

| Group | Meaning | Row action |
|---|---|---|
| **Available now** — "ready to use" | your plan includes it and it runs today | **Add** |
| **Upgrade to unlock** — "on a higher plan" | it runs today but needs a higher plan | **Upgrade to Pro** (or the plan it needs) |
| **Coming soon** — "after the open beta" | not available yet on any plan | a **soon** label |

Each catalog row shows the connector's name, its target code (for example
`sheets`) and its minimum plan.

Below the catalog, **Configured** ("from studio/settings.json") lists the
connectors of this project:

```
Configured  from studio/settings.json
 Connector        Target     Direction   Table       Secret
 export_sheets    sheets     export →    responses   GSHEETS_SA   [Validate] [Run export] [History]
 import_crm       database   ← import    crm_accts   CRM_DSN      [Validate] [Run import] [History]
```

| Button | What it does |
|---|---|
| **Validate** | a quick check in your browser of the plan, the secret and the target (see below). Nothing is contacted |
| **Run export** / **Run import** | queues a run: "Connector *name* queued (run #*N*)". Owners and admins only — for members the button is disabled (tooltip "Only owners and admins can run a connector") |
| **Requires Pro** (or another plan) | shown instead of Run when the target is above your plan; opens the plans |
| **soon** | shown instead of Run for a target that does not run yet |
| **History** | expands this connector's runs underneath, newest first ("No runs yet for this connector.") |

With nothing declared the section says "No connectors configured yet."

**Validate** answers with one of:

- "*target* needs the *Plan* plan to run"
- "This connector needs a secret — set one in Settings → Secrets and reference it"
- "Secret "*KEY*" is not set (Settings → Secrets)"
- "*target* is configured; it runs once it leaves beta"
- "Looks good — plan, secret and target are all set"

It does not test the credential itself. The first real test is a run.

---

## Add a connector

1. Click **Add** on the target's row in **Available now**. The dialog **Connect
   *target name*** opens.
2. **Connector name** — pre-filled as `export_<target>` (or `import_<target>`).
   Use **lowercase letters, digits and underscores, starting with a letter**, up
   to 63 characters. The name must be unique in the project, must not equal a
   flow's name, and must not be `survey`.
3. **Direction** — only for **Supabase (Postgres)** and **Your database
   (Postgres)**: **export →** or **← import**.
4. **Source table** (export) or **Destination table** (import) — a table of this
   project: `responses`, or a table a flow wrote (see
   [[Responses and the Data Tab|Studio-Responses-and-Data]]).
5. The target's own fields (see the table below). Required fields are unmarked;
   the others say *optional*.
6. **Credentials secret** — choose an existing project secret, or click **Add**
   to create one here: a key (pre-filled with a suggested name such as
   `GSHEETS_SA`), the value, then **Save secret**. Under the field the dialog
   shows **Format:** with the exact shape the target expects, and where to get
   it. Creating secrets needs the owner or admin role; a member who clicks
   **Save secret** gets "Could not add secret. You do not have permission to
   do this." — ask an owner or admin to add the secret, then choose it here.
7. Click **Add & Save**. You see "Connector *name* added — saved to
   studio/settings.json".

**Add & Save** stays disabled until the name, every required field (for Excel
365: the workbook path *or* item ID) and, where needed, a secret are filled in.

The file targets — Amazon S3, Google Cloud Storage, Azure Blob Storage and
SFTP (and Dropbox, coming soon) — write the table as a CSV file, replacing it
at each run, whatever its name ends in. The line under the name field says so:
"The table is written here as a CSV file, replacing the file at each run." A
name that ends in another format, such as `responses.xlsx`, gets a warning:
"The file will hold CSV text though its name ends in .xlsx, and programs that
trust the ending won't open it — end the name in .csv." An S3 object key or a
Google Cloud Storage object name that starts with `/` gets "A leading “/”
makes a folder with no name in the bucket — start with the folder or the file
name (exports/responses.csv)." These names are places in your own storage, not
in the project's `outputs/`, so you type them in full; the warnings do not
stop **Add & Save**.

If the Save is refused you see "Could not add connector." and the reason — for
example a name with capital letters ("…String should match pattern…") or a name
already used by a flow ("task name '*x*' is already in use"). "A connector named
"*x*" already exists" means you need another name.

A few seconds after the Save, Studio adds the warning `CONNECTOR_PLAN` to the
Save if a declared connector needs a higher plan than yours. See
[[History and Versions|Studio-History-and-Versions]].

### Editing or removing a connector

> **Current limitation.** The app has no button to edit or remove a declared
> connector. Your options today:
>
> - **Replace credentials** without touching the connector: add the secret again
>   under the same key (see [Secrets](Studio-Project-Settings#secrets)).
> - **Remove it by restoring** a Save from before it was added. This also rolls
>   back every other document to that Save, so do it right after adding the
>   wrong connector.
> - **Save a corrected `studio/settings.json` through the API** (see
>   [[API and API Keys|Studio-API-and-API-Keys]]), or contact support.

---

## All targets

"Live" targets run today. **Coming soon** ones can't be added from the catalog
yet. Every export writes the **whole table**, header row first, all values as
text.

> **Note — exporting `responses`.** A connector sends the project table's
> stored rows as they are. For `responses` that is one row per response with
> the table's own columns (`id`, `survey_id`, `respondent_id`, `partial`,
> `created_at`, `updated_at`), all the answers together in one `data` column
> and the fieldwork metadata in `meta` — not one column per variable. In a
> file, sheet or table, those two cells hold the values as Python writes them
> (single quotes, `True`, `None`), not as JSON. The way
> the **Data** tab, **Data → Export**, flows and research bundles read
> responses (answers in the questionnaire's order, older responses in today's
> layout and codes, a `<variable>_other` column for "Other" texts, columns
> such as `duration_s` and `url_*`) is not applied to a connector run. To send
> one column per variable, have a flow write the table with a **Write table**
> node and export that table instead.

| Target | Plan | Direction | Settings (* required) | Secret: suggested key and exact format | What each run writes | Rows |
|---|---|---|---|---|---|---|
| **Google Sheets** | Plus | export | **Spreadsheet ID*** ("From the sheet URL: /spreadsheets/d/<ID>/edit"); **Range** (optional, default `A1` on the first sheet) | `GSHEETS_SA` — a service-account JSON key: `{"client_email": "…@project.iam.gserviceaccount.com", "private_key": "-----BEGIN PRIVATE KEY-----\n…"}` | writes the table as plain values starting at the range | 50,000 |
| **Microsoft Excel 365 (OneDrive / SharePoint)** | Plus | export | **Drive ID***; **Workbook path** or **Item ID** (one of the two); **Worksheet** (optional, default `Sheet1`) | `GRAPH_APP` — `{"tenant_id": "…", "client_id": "…", "client_secret": "…", "refresh_token": "…"}` | writes the range from `A1` in the existing workbook and worksheet | 10,000 |
| **Supabase (Postgres)** | Plus | export · import | **Destination table** (optional, default: the project table's name); **Schema** (optional, default `public`) | `SUPABASE_DSN` — the connection string `postgresql://postgres:<password>@db.<ref>.supabase.co:5432/postgres` | export: drops and re-creates the table (all columns text) and inserts the rows; import: see [Importing a table](#importing-a-table) | 100,000 |
| **HubSpot (CRM)** | Plus | export | **CRM object** (optional, default `contacts`); **Match records on** (optional, default `email`) | `HUBSPOT_TOKEN` — a private-app access token, `pat-…` | creates or updates one record per row, matched on the chosen property | 100,000 |
| **Amazon S3 / R2 / MinIO** | Pro | export | **Bucket***; **Object key*** (e.g. `exports/responses.csv`) | `AWS_CREDS` — `{"access_key": "AKIA…", "secret_key": "…", "region": "eu-west-1", "endpoint": "https://…"}` (`region` and `endpoint` optional; `endpoint` for R2 or MinIO) | a CSV file (UTF-8, header row), replaced each run | 100,000 |
| **Google Cloud Storage** | Pro | export | **Bucket***; **Object name*** | `GCS_SA` — service-account JSON key (as for Sheets) | a CSV object, replaced each run | 100,000 |
| **Azure Blob Storage** | Pro | export | **Container***; **Blob name*** | `AZURE_BLOB` — `{"account": "mystorageaccount", "sas_token": "sv=…&sig=…"}` | a CSV block blob, replaced each run | 100,000 |
| **Google BigQuery** | Pro | export | **Dataset***; **Table***; **Project** (optional, defaults to the key's project) | `BQ_SA` — service-account JSON key | replaces the table's contents; every column is a STRING | 100,000 |
| **Snowflake** | Pro | export | **Database***; **Schema***; **Table***; **Warehouse*** | `SNOWFLAKE` — `{"account": "xy12345.eu-central-1", "user": "…", "private_key": "-----BEGIN PRIVATE KEY-----\n…"}` | replaces the table (all columns text) and inserts the rows | 100,000 |
| **Your database (Postgres)** | Pro | export · import | **Destination table** (optional); **Schema** (optional, default `public`) | `TARGET_DB_DSN` — `postgresql://user:pass@host:5432/db` (or `postgres://…`) | as Supabase | 100,000 |
| **SFTP** | Pro | export | **Host***; **Remote path*** (e.g. `/uploads/responses.csv`); **Port** (optional, default 22) | `SFTP_AUTH` — `{"username": "…", "password": "…"}` or `{"username": "…", "private_key": "…"}` | a CSV file at the path, replaced each run | 100,000 |
| **REDCap** | Pro | export | **API URL*** (e.g. `https://redcap.example.org/api/`) | `REDCAP_TOKEN` — the project's API token as plain text (not JSON) | imports the rows as REDCap records (existing records are updated) | 100,000 |
| **Salesforce (CRM)** | Pro | export | **Salesforce object*** (e.g. `Contact`); **External id field** (optional); **Login URL** (optional) | `SALESFORCE_CREDS` — `{"client_id": "3MVG…", "client_secret": "…"}` or `{"client_id": "3MVG…", "username": "you@org.com", "private_key": "-----BEGIN…"}` | a Bulk API 2.0 load: insert, or upsert when an external id field is set | 100,000 |
| **Custom HTTP endpoint** | Pro | export | **Endpoint URL***; **Body format** (optional: `csv` default, or `json`) | `HTTP_TOKEN` — optional; a bearer token | one `POST` with the whole table | 100,000 |
| **Airtable** | Plus | export | — | — | coming soon | — |
| **Dropbox** | Plus | export | — | — | coming soon | — |
| **Custom MCP servers** | Corporate | export | — | — | coming soon | — |

---

## Setting up each target

### Google Sheets

1. In Google Cloud, create a service account and a **JSON key** for it. Store
   the whole key file as the secret.
2. **Share the spreadsheet with the service account's `client_email`** (with
   edit rights), as you would with a colleague.
3. Copy the spreadsheet ID from its address: `/spreadsheets/d/<ID>/edit`.

Each run writes the header and rows starting at **Range**. Cells beyond the
new data are **not** cleared, so if the table shrinks, old rows remain below
it. Use a sheet that holds only this export.

### Microsoft Excel 365

1. Register an app in Microsoft Entra ID (Azure AD) with **delegated**
   `Files.ReadWrite` and `offline_access` permissions.
2. Sign in once as a user who can edit the workbook to obtain a **refresh
   token**. App-only tokens cannot update Excel ranges.
3. The secret is `{"tenant_id", "client_id", "client_secret", "refresh_token"}`.
   When consent expires or is revoked, replace the secret with a new refresh
   token.
4. **Drive ID** is the OneDrive or SharePoint drive. Address the workbook by
   **Workbook path** (e.g. `/Reports/responses.xlsx`) or by **Item ID**.

The workbook and the worksheet must already exist. A worksheet name may use
letters, digits, spaces, `_` and `-` (up to 31 characters). As with Sheets,
rows below the new data are not cleared.

### Supabase and your own Postgres

- Supabase: **Project Settings → Database → Connection string (URI)**.
- Your database: any `postgres://` or `postgresql://` connection string whose
  user can create and drop the table.
- The host must be a public address with a single host name; a connection
  string that overrides its host in query parameters is refused.

On export the destination table is **dropped and re-created** on every run
with all columns as text. Do not point it at a table you maintain by hand.
Column names must be simple identifiers (letters, digits and `_`, not starting
with a digit).

### HubSpot

1. In HubSpot, **Settings → Integrations → Private Apps**, create an app with
   write access to the object you export to, and copy its access token.
2. **CRM object**: `contacts` (default), `companies`, `deals`, `tickets`,
   `products`, `line_items`, `quotes`, or a custom object (`p_<name>` or its
   numeric type id).
3. **Match records on**: the property that identifies a record — `email`
   (default) for contacts, typically `domain` for companies. That column must
   be in the table you export.

HubSpot **upserts**: a re-run updates the same records instead of creating
duplicates. Every other column becomes a property of the same name, so the
property must exist in HubSpot with exactly that name. A column with **no
value leaves the CRM field alone** — a respondent who skipped a question does
not erase what your team typed. Rows without a value in the match column are
skipped. Rows are sent 100 at a time. If HubSpot rejects a batch, the run fails
with HubSpot's own explanation, and the batches before it have already been
written.

### Salesforce

1. In **Setup → App Manager**, use a connected app. The secret decides the
   sign-in method by itself:
   - `{"client_id", "client_secret"}` — client credentials;
   - `{"client_id", "username", "private_key"}` — the JWT bearer flow, running
     as that user (the private key of the app's certificate).
2. **Salesforce object**: `Contact`, `Lead`, a custom object…
3. **External id field**: set it and the load becomes an **upsert** on that
   field; leave it empty to **insert**.
4. **Login URL**: `https://login.salesforce.com` by default; a sandbox uses
   `https://test.salesforce.com`; a My Domain URL also works.

Column names must match Salesforce **field API names** exactly, including the
`__c` suffix of custom fields. Salesforce processes the load in the background,
and the run waits for it for up to 5 minutes:

- the job finished with no failed records — the run completes;
- the job finished with failures — the run **fails** with the counts and the
  address of the job's `failedResults` list;
- the job is still processing after 5 minutes — the run completes; check the
  job in Salesforce under **Setup → Bulk Data Load Jobs**.

### Amazon S3, Cloudflare R2, MinIO

An access key with permission to write objects (`PutObject`) to the bucket.
For R2 or MinIO add `"endpoint"`; it must be a public address.

### Google Cloud Storage

A service-account JSON key with write access to the bucket (the Storage Object
User role).

### Azure Blob Storage

A **shared access signature** (SAS) for the container or account with write
permission on blobs; account keys are not used. The secret is `{"account",
"sas_token"}`. A container name uses lowercase letters, digits and `-` (3–63
characters).

### Google BigQuery

A service-account JSON key with **BigQuery Data Editor** and **BigQuery Job
User** on the project. Each run replaces the table's contents; all columns are
loaded as STRING. Column names must be simple identifiers.

### Snowflake

Key-pair authentication: assign an RSA public key to the user (`ALTER USER …
SET RSA_PUBLIC_KEY = …`); the secret carries the **unencrypted** private key.
The account looks like `xy12345.eu-central-1`. Each run replaces the table
(`CREATE OR REPLACE`), then inserts the rows 500 at a time. The table and
column names are used exactly as written (quoted), so they are case-sensitive
in Snowflake.

### SFTP

A username with a password, or with a private key (Ed25519, ECDSA or RSA). The
host must be a public address. Each run uploads the table as CSV to **Remote
path**, replacing the file.

### REDCap

In the REDCap project: **API** → your token (the 32-character string), stored
as plain text. Column names must match the REDCap field names, including the
record-id field. Rows are imported as records; existing records are updated
with the values sent.

### Custom HTTP endpoint

Each run sends one `POST` to **Endpoint URL**: `text/csv` (header row plus
rows), or with **Body format** `json`:

```json
{"columns": ["id", "q1"], "rows": [{"id": 1, "q1": "yes"}]}
```

With a secret, it is sent as `Authorization: Bearer <secret>`. The endpoint
must answer within 30 seconds with a success status; any 4xx or 5xx answer
fails the run. The address must be public.

---

## Importing a table

**Supabase (Postgres)** *(Plus)* and **Your database (Postgres)** *(Pro)* can
also run in the **← import** direction: they read a table from the external
database into a table of this project.

- The dialog's **Destination table** (the project table) receives the data.
  The target field labeled **Destination table** in the Supabase / database
  settings names the **external table to read**. Leave it empty to read an
  external table with the same name. **Schema** defaults to `public`.
- Each import **replaces** the project table's contents; all columns arrive as
  text.
- `responses`, `survey_meta` and `quota_counters` cannot be import
  destinations ("cannot import into reserved survey table: …").
- At most **100,000 rows**; a larger table is refused entirely ("import exceeds
  the 100000 row limit; no rows were imported").

Read the imported table in a flow with a **Project table** node.

> **Current limitation.** The **Destination table** list offers only tables
> that already exist in the project. To import into a new table, first create
> it — for example with a flow whose **Write table** node writes a table of
> that name — then choose it; the import replaces its contents.

---

## Running and run history

Click **Run export** or **Run import**. The run is queued and then executed in
the background; open **History** under the connector to follow it. Connector
runs also appear in **Flows → Run history**. The project's **Settings →
Activity** records `connector.run`, under the person's name, when someone
starts a run, and `connector.completed` or `connector.failed`, with `—` as the
person, when it ends.

| State | Meaning |
|---|---|
| queued | waiting for a worker |
| running | in progress |
| completed | the log reads "*name*: *N* rows · *destination*", for example `s3://my-bucket/exports/responses.csv`, `sheets:1AbC…!A1`, `bigquery:proj.dataset.table`, `hubspot:contacts` |
| failed | the log gives the reason |

Only **owners and admins** can run a connector. Members see **Run export** /
**Run import** disabled, with the tooltip "Only owners and admins can run a
connector"; they can still open **History** and follow the runs.

Messages you may see when a run is refused or fails:

| Message | What to do |
|---|---|
| "project has not been saved yet" | save the project once |
| "the '*target*' connector requires the '*plan*' plan or higher (current plan: '*plan*'); upgrade to run it" | upgrade, or use a target your plan includes |
| "the '*target*' connector is coming soon — live exports today: …" | the target does not run yet |
| "import isn't available for the '*target*' connector yet — live imports today: database, supabase" | only those two can import |
| "this connector needs a `secret` (set it under Project → Secrets)" | pick a secret for the connector |
| "project secret '*KEY*' is not set (Project → Secrets)" | add the secret under that exact key |
| "*target*: the secret must be a JSON credentials object" / "*target*: secret is missing: *fields*" | fix the secret's value (see the formats above) |
| "export exceeds the *N* row limit; no rows were exported" | the table is larger than the target's limit; nothing was sent |
| "connector endpoint must target a public host" / "…must not target a private or reserved address" | use a public address |
| "cannot import into reserved survey table: *table*" | choose another destination table |
| "connector failed: …" followed by the destination's own error | read the destination's message; usually credentials, permissions or a missing sheet, bucket or table |

---

## Rules and limits

- **Plans.** Connectors need *(Plus)*; S3/R2/MinIO, Google Cloud Storage,
  Azure, BigQuery, Snowflake, Your database, SFTP, REDCap, Salesforce and Custom
  HTTP need *(Pro)*; Custom MCP servers *(Corporate)*. The plan is checked again
  on every run, so a connector stops running if the organization moves to a
  lower plan.
- **Roles.** Any member can add a connector (it is a Save) and validate it.
  Only owners and admins can run one or create its secret.
- **Whole-table, current-state exports.** Each run sends the entire table as it
  is at that moment, all values as text — for `responses`, the stored rows with
  the answers in one `data` column (see
  [the note under All targets](#all-targets)).
- **Row limits fail the whole run.** 100,000 rows, Google Sheets 50,000, Excel
  365 10,000. A larger table exports nothing.
- **Public destinations only.** Endpoints, hosts and database addresses must be
  public; private networks, `localhost` and internal names are refused.
- **What the run uses.** The connector as declared in the **current Save**, and
  the credential as currently stored in Secrets.

## See also

- [[Project Settings|Studio-Project-Settings]]
- [[Schedules and Webhooks|Studio-Schedules-and-Webhooks]]
- [[API and API Keys|Studio-API-and-API-Keys]]
- [[Data Exports|Studio-Data-Exports]]
- [[Plans, Trial and Billing|Studio-Plans-and-Billing]]

<!-- studio-nav -->
---

← [[Files|Studio-Files]] · [Studio contents](Studio-Overview#all-pages) · [[Schedules and Webhooks|Studio-Schedules-and-Webhooks]] →
