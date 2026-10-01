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

A tab with unsaved changes — **General** (the project name and the **Study &
citation** card), **Runtime** or **Reports** — asks before you leave it,
whether you click another tab or press `Enter` or `Space` on it: **Discard
unsaved changes?** — "The *tab* tab has unsaved changes. Switching tabs
discards them." **Discard** drops the changes and opens the other tab;
**Cancel** keeps you, and the focus, on the tab with your changes. The arrow
keys only move the focus between the tabs, so they never leave one.

---

## General

| Field | Notes |
|---|---|
| **Project name** | Editable. Click **Save changes**; you see "Settings saved". Renaming needs the **owner** or **admin** role: for other members **Save changes** stays disabled (tooltip "Only owners and admins can do this") and the card says "Only owners and admins can rename a project." The name is not part of a Save |
| **Slug** | "read-only after creation". It is the project's address (`…/projects/<slug>`) and what **Delete project** asks you to type |
| **Survey host** | "where deployments are served", shown as `study.siamang.org/<org>/<project>/<environment>` |

> **Note.** Published surveys use the address shown on each card in
> **Distribute** — normally `study.siamang.org/<survey-id>/` — not the pattern in
> the **Survey host** field. A survey published with such a link is not
> reachable at `<org>/<project>/<environment>` at all, so nobody who knows your
> organization's and project's slugs can open an environment by its name. Only
> a survey that was already served at that older path keeps answering there
> (and shows its closed page there after **Close**). Always copy links from
> **Distribute**. See
> [[Publishing and Environments|Studio-Publishing-and-Environments]].

If you leave **General** with an unsaved name or unsaved edits in **Study &
citation**, Studio asks **Discard unsaved changes?** — "The General tab has
unsaved changes. Switching tabs discards them." — with **Discard**. If you
choose **Discard**, the tab you chose (with a click, `Enter` or `Space`) opens
and has the focus; **Cancel** keeps you, and the focus, on **General**.

### Study & citation

"Every research bundle carries a CITATION.cff built from this, and the Methods
draft names the authors. Part of studio/settings.json, so it is versioned with
every Save."

| Field | Format | Notes |
|---|---|---|
| **Study title** | text, up to 300 characters | "defaults to the project name" |
| **Authors** | one per line: `Name; ORCID; affiliation` | e.g. `Ada Lovelace; 0000-0002-1825-0097; Analytical Engines`. ORCID and affiliation are optional; write `Name;; affiliation` to skip the ORCID, and the card shows that author the same way after a Save |
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

- **Python version** — **3.11** (the default) or **3.12**, with the hint "for
  the research bundle — Studio runs flows on Python 3.11". Studio runs every
  flow on Python 3.11 whatever you pick here: the setting is the version a
  research bundle asks for, written to its `environment/python-version` and
  `siamang.yaml`. The bundle's README says both ("Python: Studio ran the flows
  on 3.11; `environment/python-version` asks for 3.12 (Settings → Runtime)"),
  and its `PROVENANCE.md` names the version the flows actually ran on.
- **Packages** — "pip requirement specifiers", for example `scipy>=1.11`. Type
  one and click **Add** (or press `Enter`); **Remove** takes one off. New
  projects start with `siamang[charts]`. With an empty list the card says "No
  extra packages declared."

Click **Save runtime** to create a Save "Update runtime".

With **3.12** chosen, every Save carries the warning `RUNTIME_PYTHON` —
"Studio runs every flow on Python 3.11. Python 3.12 (Settings → Runtime) is
the version a research bundle asks for (environment/python-version), not the
one the flows run on here." — so its state is **warnings** rather than
**valid**. Publishing and running are not affected. Pick **3.11** again to
clear it.

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
  version and the data snapshot it was built from". On by default. Turn it
  off and save, and the reports of later runs — single flows, Run all and its
  combined report, scheduled runs — end without the "Provenance" footer, and
  so do the reports a research bundle of that Save produces when you run it.
  Reports already stored keep the footer they were made with. Previews
  (**Run to here**, **Preview all**) never print the footer. See
  [The provenance footer](Studio-Reports#the-provenance-footer).
- **Combined report** — "where Run all writes the merged report: a Markdown
  file inside the project". You type the folders and the name, such as
  `reports/full`, before a fixed `.md`; empty, it is the default
  `reports/report.md`. The line under it says where it goes: "After Run all:
  Files and Reports → reports/full.md, with an .html copy beside it". A
  problem is said on that line instead, with a one-click fix when there is
  one, and keeps **Save report settings** and **Apply to every flow** off
  until you fix it: a name with `..` ("“..” and “.” can't be folders here:
  the file has to stay in the project."), a character other than Latin
  letters (A–Z, a–z), digits, `-`, `_` and `.`, or another ending, such as
  `reports/report.docx` ("Take .docx off the name: the combined report is
  Markdown (.md), with an .html copy beside it — for Word or a PDF, open the
  .html.", with **Use reports/report**). A path saved earlier that **Run
  all** accepts, such as one with Cyrillic letters, shows the same advice but
  does not keep the other report settings from being saved. A path saved
  earlier without a Markdown ending is shown under "Kept as it was written",
  with **Save it as *path*.md instead**. The **Reports** screen marks the
  report at this path with the **combined** badge, including a custom path.
- **House style** — the report theme form (typeface, density, table style,
  page size, **P values**, sizes, figures, captions, colors, and the chart
  colors of the charts whose **Palette** is `theme`), described on
  [[Reports|Studio-Reports]] (see [Chart colors](Studio-Reports#chart-colors)
  and [P values](Studio-Reports#p-values)). A note above the form says what
  its **P values** does besides: "Its P values also sets how Studio writes a
  p-value in node previews and Live tiles, so the study reads the same here
  as in its reports. They follow a change from their next run." The form
  offers only the three choices; a `p_values` written into
  `studio/settings.json` by other means is refused unless it is `exact`,
  `0.01` or `0.001`, and the Save is not made: "settings: report/theme:
  p_values: '0.05' is not one of exact, 0.01, 0.001."

Buttons:

- **Save report settings** creates a Save "Update report settings". The house
  style is stamped into a **Save report** node when one is created — by the
  report composer or from the canvas palette — and Run all uses it for the
  combined report, which has no node of its own.
- **Apply to every flow** — "Write this style into the Save report node of
  every flow, so each flow — and each bundle — carries it". It creates one Save
  "Apply the report house style to *N* flows". This is an ordinary edit you can
  see in the diff and undo by restoring. If nothing needed changing you see
  "Every flow already uses the house style".

A flow's report is always drawn with the style stored in its own **Save
report** node — on the platform, in its downloaded script and in a research
bundle alike. Changing the house style alone does not restyle existing flows;
**Apply to every flow** does.

> **Note.** A flow whose **Save report** node names no look of its own — for
> example one made before the project had a house style — renders with the
> engine's defaults. Earlier versions of Studio silently drew such a flow in
> the house style on the platform (but not from its downloaded script), so its
> next run may look plainer than before. Click **Apply to every flow** to
> stamp the house style into it.

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

A cap counts **completed interviews** of that environment's survey:
screen-outs and partial (unfinished) responses do not use it up. Your plan's
per-project response limit applies on top — on Free, **1,000** completed
interviews for the whole project, all environments together (the sample rows
of a project made from the example template do not count). When either is
reached, the survey stops taking new respondents; see
[Response caps](Studio-Publishing-and-Environments#response-caps).

Both counts are taken from the stored responses whenever they are checked, so
responses collected before these rules count the same way: an environment
that looked full only because of its screen-outs takes respondents again,
and on Free a project whose environments together already hold 1,000
completed interviews takes no more in any of them, even where each
environment on its own is below 1,000. When a
project declares no environments at all, deployments use `pilot` and `main`
with the plan's limit ("No environments declared — deployments use pilot and
main with the plan's quota.").

An environment in `studio/settings.json` can also carry a closing date
(`closes_at`) and a page to send respondents to once it is closed
(`redirect_after_close`, an `http://` or `https://` address). Both are applied
when you publish to that environment: the survey stops accepting responses at
the earlier of this date and the questionnaire's own deadline, and a
respondent who opens a closed survey is sent on to the redirect. A closing
date set with the **Closing date** panel on a **Distribute** card takes
precedence: a republish keeps it, and `closes_at` applies to that deployment
again only after **Use the Save’s date**. The tab does not show these two
fields. See
[Deadlines](Studio-Publishing-and-Environments#deadlines).

> **Current limitation.** The list is read-only: "Editing environments in the UI
> arrives in phase 1; until then edit studio/settings.json via a Save." The app
> has no editor for `studio/settings.json` itself. To add an environment,
> change a cap or set an environment's `closes_at` / `redirect_after_close`
> today, save a new version of `studio/settings.json` through the API (see
> [Change settings through the API](Studio-API-and-API-Keys#change-studiosettingsjson-through-the-api)),
> or contact support, then publish to that environment again. An environment
> name uses lowercase letters, digits and `-`, starts with a letter and is
> unique; a cap is a whole number of at least 1. To move one deployment's
> closing date without a new Save, use the **Closing date** panel on its
> **Distribute** card instead.

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

"Who did what in this project, and how builds and runs ended: Saves, deploys,
flow runs, connector exports, schedules, data exports and secret changes. Live
recomputes are not listed, only clicks on Recompute now."

- Shows the **latest 100 events** of this project, newest first: the action
  (for example `snapshot.save`, `snapshot.restore`, `snapshot.tag`,
  `bundle.download`, `bundle.deposit`, `deploy.create`, `deploy.live`,
  `deploy.stop`, `run.start`, `run.completed`, `connector.run`,
  `schedule.create`, `schedule.delete`, `live.recompute`, `secret.set`,
  `response.delete`), its target, who did it and when.
- Data leaving the project is recorded too, never the data itself:
  `data.export` for a download from **Data → Export** or the export API (the
  table as the target; the format and the number of rows in the details), and
  `outcomes.export` for an outcome CSV from **Distribute** (the environment as
  the target, `<project>:<environment>`). Deleting contacts is
  `contacts.delete` (the contact's id, or "*N* deleted" for all of them).
- Changes on a **Distribute** card that need no Save are recorded as
  `deploy.closing_date` (a new closing date, or "Use the Save’s date") and
  `deploy.one_response_per_browser` (the **One per browser** switch, with
  `enabled` true or false in the details).
- A Save that renames or deletes a flow keeps that in its details: `renamed`
  (old and new path) and `paused_schedules` (how many of the flow's schedules
  it paused). A `snapshot.restore` that takes a rename back or removes a flow
  carries the same two details.
- A Save that adds access codes (**Generate codes** / **Generate more** or
  **Import CSV** on **Distribute**) is also recorded as
  `access_codes.generate`, with the Save number as the target and the number
  of codes added — never the codes themselves.
- What Studio records on its own when a build or a run ends appears here
  too, with "—" in place of a person: `deploy.live`, `deploy.failed`,
  `deploy.preview_live`, `deploy.preview_failed`, `run.completed`,
  `run.failed`, `connector.completed`, `connector.failed`. The person who
  started the build or the run has an entry of their own (`deploy.create` or
  `deploy.reopen`, `deploy.preview`, `run.start` for **Run** and **Run all**,
  `schedule.run` for a schedule's **Run now**, `connector.run`); a run that a
  schedule started on its timer has only the entry for how it ended.
- A build or a run that Studio marks failed because it stopped responding gets
  a failure entry with `"reason": "timed out"` in its details. If such a build
  finishes afterward, its survey or preview is up after all, and a
  `deploy.live` or `deploy.preview_live` entry follows, with
  `"after": "timed out"`.
- **Live recomputes are not listed**, neither those that new responses start
  nor the runs **Recompute now** starts: they are in **Run history** on
  **Flows**. A click on **Recompute now** that queues a recompute is recorded,
  as `live.recompute`, under the name of the person who clicked.
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

Only the **owner** or an **admin** can delete a project. For members,
**Delete project** is disabled (tooltip "Only owners and admins can do this")
and the card adds "Only owners and admins can delete a project." Before you
delete, download what you need — a research bundle with the responses (History → a Save
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
