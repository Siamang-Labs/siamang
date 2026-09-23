# Project Settings

**Project → Settings** holds everything about one project that is not the
questionnaire or a flow: its name, citation metadata, the Python runtime, the
report house style, environments, secrets, connectors, the activity log and the
delete button. Billing and members are organization-wide and live in
**organization settings** (see
[[Organizations and Team|Studio-Organizations-and-Team]]).

```
Project settings   ▣ Brand Awareness Study 2026
Settings below apply to this project only. Billing and members live in organization settings.

[General] [Runtime] [Reports] [Environments] [Secrets] [Connectors] [Activity] [Danger Zone]
```

Most of these settings are stored in the project document
`studio/settings.json`. Changing them creates a **Save**, so they are
versioned, appear in History and travel in every research bundle. The
exceptions are the project name, secrets and the activity log, which are not
part of any Save.

---

## General

| Field | Notes |
|---|---|
| **Project name** | Editable. Click **Save changes**; you see "Settings saved". Renaming needs the **owner** or **admin** role: for other members **Save changes** stays disabled (tooltip "Only owners and admins can do this") and the card says "Only owners and admins can rename a project." The name is not part of a Save |
| **Slug** | "read-only after creation". It is the project's address (`…/projects/<slug>`) and what **Delete project** asks you to type |
| **Survey host** | "where deployments are served", shown as `study.siamang.org/<org>/<project>/<environment>` |

> **Note.** Published surveys use the address shown on each card in
> **Distribute** — normally `study.siamang.org/<survey-id>/` — not the pattern in
> the **Survey host** field. Always copy links from **Distribute**. See
> [[Publishing and Environments|Studio-Publishing-and-Environments]].

If you switch tabs with an unsaved name, Studio asks **Discard unsaved
changes?** — "The General tab has unsaved changes. Switching tabs discards
them." — with **Discard**.

### Study & citation

"Every research bundle carries a CITATION.cff built from this, and the Methods
draft names the authors. Part of studio/settings.json, so it is versioned with
every Save."

| Field | Format | Notes |
|---|---|---|
| **Study title** | text, up to 300 characters | "defaults to the project name" |
| **Authors** | one per line: `Name; ORCID; affiliation` | e.g. `Ada Lovelace; 0000-0002-1825-0097; Analytical Engines`. ORCID and affiliation are optional; write `Name;; affiliation` to skip the ORCID |
| **License** | **— not set —**, `CC-BY-4.0`, `CC-BY-SA-4.0`, `CC-BY-NC-4.0`, `CC0-1.0`, `MIT`, `ODbL-1.0`, `proprietary` | |
| **Keywords** | "comma-separated" | |
| **DOI** | e.g. `10.5281/zenodo.123456` | "once the bundle is deposited" — Studio does not fill it in for you |
| **Abstract** | optional, up to 4,000 characters | |

An ORCID must look like `0000-0002-1825-0097` (the last character may be `X`).
Otherwise the card shows "ORCID for *name* must look like
0000-0002-1825-0097." and the button stays disabled. Click **Save study
metadata** to create a Save "Update study metadata".

Where this metadata goes:

- **`CITATION.cff`** in every research bundle: title, authors (given and family
  names split at the last space, ORCID as a link, affiliation), license,
  keywords, abstract, DOI, with `save-N` as the version and the Save's date as
  the release date.
- **Zenodo deposits**: title, creators, description, keywords and license (only
  the six open licenses above are passed on). See
  [Depositing to Zenodo or OSF](Studio-History-and-Versions#depositing-to-zenodo-or-osf).
- **The Methods draft**: the title and "Authors on record".

---

## Runtime

"Runtime is part of studio/settings.json and versioned with every Save.
Packages must come from the platform's curated allowlist; a Save declaring
anything else fails validation."

- **Python version** — **3.11** or **3.12**. The choice is recorded in the
  project and in the research bundle's `siamang.yaml`.
- **Packages** — "pip requirement specifiers", for example `scipy>=1.11`. Type
  one and click **Add** (or press `Enter`); **Remove** takes one off. New
  projects start with `siamang[charts]`. With an empty list the card says "No
  extra packages declared."

Click **Save runtime** to create a Save "Update runtime".

The allowlist: `numpy`, `pandas`, `scipy`, `statsmodels`, `scikit-learn`,
`matplotlib`, `seaborn`, `pingouin`, `lifelines`, `openpyxl`, `pyreadstat`,
`pyarrow`, `tabulate`, `PyYAML`, `factor-analyzer`, `prince`, `semopy`,
`krippendorff`, plus `siamang` itself. These are already installed where your
flows run. The list you declare mainly documents the project and is written to
the bundle's `environment/requirements.txt` (the engine is pinned there
separately).

A package outside the allowlist does not stop the Save. A few seconds later the
Save turns to **error** with "packages not available in the sandbox: *name*.
Use a package from the curated allowlist, or request it be added." Remove the
package and save again. See
[The second check after a Save](Studio-History-and-Versions#the-second-check-after-a-save).

Most studies never touch this tab.

---

## Reports

How this project's reports look, and where the combined report goes.

"Part of studio/settings.json and versioned with every Save. The look reaches a
reader through the report's .html; the .md beside it carries the same content
with no styling, for a diff or a repository."

- **End every report with the provenance footer** — "the Save, the engine
  version and the data snapshot it was built from". On by default.
- **Combined report** — "where Run all writes the merged report; Markdown,
  inside the project". Default `reports/report.md`. A path that is absolute,
  contains `..` or does not end in `.md` / `.markdown` shows "A combined report
  must be a Markdown path inside the project, like reports/report.md."
- **House style** — the report theme form (typeface, density, table style,
  page size, sizes, figures, captions, colors), described on
  [[Reports|Studio-Reports]].

Buttons:

- **Save report settings** creates a Save "Update report settings". The house
  style is stamped into a new flow's **Save report** node when you create one,
  and Run all uses it for the combined report.
- **Apply to every flow** — "Write this style into the Save report node of
  every flow, so each flow — and each bundle — carries it". It creates one Save
  "Apply the report house style to *N* flows". This is an ordinary edit you can
  see in the diff and undo by restoring. If nothing needed changing you see
  "Every flow already uses the house style".

A flow's report is always drawn with the style stored in its own **Save
report** node, so a downloaded flow script looks the same outside Studio.
Changing the house style alone does not restyle existing flows; **Apply to every
flow** does.

---

## Environments

"Environments are the deployment targets (pilot, main, …) declared in
studio/settings.json. Each carries a response cap the survey host enforces."

The tab lists each environment with its cap ("*N* responses max" or "no cap").
Every new project starts with two:

| Environment | Response cap |
|---|---|
| `pilot` | 50 |
| `main` | 1,200 |

Your plan's per-project response limit applies on top. When a project declares
no environments at all, deployments use `pilot` and `main` with the plan's
limit ("No environments declared — deployments use pilot and main with the
plan's quota.").

> **Current limitation.** The list is read-only: "Editing environments in the UI
> arrives in phase 1; until then edit studio/settings.json via a Save." The app
> has no editor for `studio/settings.json` itself. To add an environment or
> change a cap today, save a new version of `studio/settings.json` through the
> API (see [Change settings through the API](Studio-API-and-API-Keys#change-studiosettingsjson-through-the-api)),
> or contact support. An environment name uses lowercase letters, digits and
> `-`, starts with a letter and is unique; a cap is a whole number of at
> least 1.

Publishing is covered in
[[Publishing and Environments|Studio-Publishing-and-Environments]].

---

## Secrets

"Encrypted, write-only project secrets. Values are never shown again after
creation — connectors and repository deposits read them by key; flow runs
cannot."

Secrets hold the credentials Studio uses on your behalf:

- **connectors** — each connector names the secret holding its credentials
  (see [[Connectors|Studio-Connectors]]);
- **deposits** — the Zenodo or OSF access token (see
  [Depositing to Zenodo or OSF](Studio-History-and-Versions#depositing-to-zenodo-or-osf)).

Secrets are **not** passed to flow runs. Flows run without network access and
without credentials. With no secrets yet the tab says "No secrets yet — values
are write-only, read by connectors and repository deposits."

### Add or replace a secret

1. Click **Add secret**.
2. **Key** — a name such as `ZENODO_TOKEN`. What you type is upper-cased, and
   any character other than `A–Z`, `0–9` and `_` becomes `_`. Keys start with a
   letter or `_` and are at most 64 characters.
3. **Value** — paste the credential exactly as the connector or repository
   expects it (a token, a JSON object, a connection string). Press `Enter` or
   click **Add secret**.

You see "Secret added". The list shows each key with `••••••••••••••` and
**set**. A value can never be displayed again, by anyone.

**To rotate a credential**, add a secret with the **same key**: the new value
replaces the old one, and every connector that references the key uses it on
its next run.

**To delete**, click **Delete** on the row → **Delete secret** — "Delete secret
"*KEY*"? Anything using it will stop working." → **Delete**.

Who can do what:

- **Owners and admins** add, replace and delete secrets. Members see the key
  names, but **Add secret** and each row's **Delete** are disabled for them
  (tooltip "Only owners and admins can do this"), and the tab says "Only
  owners and admins can add or delete secrets."
- Adding and deleting secrets is recorded in **Activity** (`secret.set`,
  `secret.delete`).

---

## Connectors

The connector catalog and your configured connectors: export response tables
to spreadsheets, storage, warehouses and CRMs, or import a table from Postgres.
*(Plus)* — on Free the tab shows "Connectors is a Plus feature" with **View
plans**. Adding a connector creates a Save; running one needs the owner or
admin role (members see **Run export** / **Run import** disabled). Everything
is covered in [[Connectors|Studio-Connectors]].

---

## Activity

"Everything that happened in this project — Saves, deploys, flow runs,
connector exports, schedules and secret changes."

- Shows the **latest 100 events** of this project, newest first: the action
  (for example `snapshot.save`, `snapshot.restore`, `snapshot.tag`,
  `bundle.download`, `bundle.deposit`, `deploy.create`, `deploy.stop`,
  `connector.run`, `schedule.create`, `secret.set`, `response.delete`), its
  target, who did it and when.
- A Save that adds access codes (**Generate codes** / **Generate more** or
  **Import CSV** on **Distribute**) is also recorded as
  `access_codes.generate`, with the Save number as the target and the number
  of codes added — never the codes themselves.
- What Studio records in the background when a build or a run ends —
  `deploy.live`, `deploy.failed`, `run.completed`, `run.failed`,
  `connector.completed`, `connector.failed` — is not tied to the project, so
  it does not appear here. Owners and admins find those events in the
  organization-wide log, where they show "—" in place of a project.
- The range buttons **24h**, **7d** (default), **30d** and **All** filter the
  list. With nothing in range you see "No activity in this period" and **Show
  all activity**.
- **Export CSV** downloads the visible events (time, action, target, user,
  meta) as `<project-slug>-activity.csv`.
- **Every member** of the organization can read a project's activity. The
  organization-wide log (Organization settings → **Activity**) is for owners and
  admins; members do not see that tab.

---

## Danger Zone

```
Delete project
This permanently deletes the questionnaire, flows, every Save, all
deployments and all collected data. This cannot be undone.      [ Delete project ]
```

Clicking **Delete project** opens **Delete *project name***:

> This deletes the questionnaire, its flows, every Save, all deployments and
> every response collected — for *project name*.
>
> Permanent, and immediate. There is no trash and no recovery window; a live
> survey stops answering the moment it goes. Export anything you need first.

Type the slug in **Type the slug to confirm**. **Delete project** becomes
active only when it matches exactly. You see "Project deleted" and return to
the Projects list.

What goes: the questionnaire, flows and settings with their whole history, the
response database, files and run outputs, secrets, schedules, runs, deposit
records and comments. Published survey links show a closed page and previews
are removed. Deposits already on Zenodo or OSF stay there.

Only the **owner** or an **admin** can delete a project; a member who tries
gets "Could not delete project. You do not have permission to do this." Before
you do,
download what you need — a research bundle with the responses (History → a Save
→ **More** → **With the responses so far**) and your data exports (see
[[Data Exports|Studio-Data-Exports]]).

## See also

- [[History and Versions|Studio-History-and-Versions]]
- [[Connectors|Studio-Connectors]]
- [[Reproducibility: Code, Bundles and Citation|Studio-Reproducibility]]
- [[Publishing and Environments|Studio-Publishing-and-Environments]]
- [[Projects|Studio-Projects]]

<!-- studio-nav -->
---

← [[Projects|Studio-Projects]] · [Studio contents](Studio-Overview#all-pages) · [[Plans, Trial and Billing|Studio-Plans-and-Billing]] →
