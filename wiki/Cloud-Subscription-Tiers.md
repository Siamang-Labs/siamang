# Plans & Billing

siamang Cloud comes in four plans — **Free**, **Plus**, **Pro**, and **Corporate**. Your
plan applies to a whole **organization** and every project inside it, setting how much you
can create and which premium features you can use. This page covers what each plan
includes and how to change yours.

## Plans at a glance

| | **Free** | **Plus** | **Pro** | **Corporate** |
| :--- | :--- | :--- | :--- | :--- |
| **Price / month** | $0 | $25 | $200 | Custom |
| **How to get it** | Self-serve | Self-serve | Self-serve | Contact sales |
| **Projects** | 2 | 10 | Unlimited | Unlimited |
| **Team members** | 2 | 15 | Unlimited | Unlimited |
| **Responses per project** | 500 | Unlimited | Unlimited | Unlimited |
| **Webhooks** | — | Yes | Yes | Yes |
| **Schedules** | — | Yes | Yes | Yes |
| **Connectors** | — | Everyday set (Sheets, Excel 365, Supabase) | All targets (S3, GCS, Azure, BigQuery, Snowflake, BYO Postgres, SFTP, REDCap, HTTP) | All + custom MCP servers |
| **Git mirrors** | — | GitHub | GitHub, GitLab, self-hosted | GitHub, GitLab, self-hosted |
| **SSO (SAML / OIDC)** | — | — | Yes | Yes |
| **Self-hosted deployment** | — | — | — | Yes |

## What every plan includes

All plans — Free included — get the complete research-as-code product. Free is a
genuinely useful, capped tier rather than a stripped-down trial. On every plan you get:

- **Git-backed projects** — author surveys as code; commit, branch, and open and merge
  pull requests. Every commit is validated.
- **Deployments** — publish a survey to an environment, get a hosted survey URL, and
  collect responses.
- **Response database** — browse responses, inspect tables, and export to **CSV, XLSX,
  SPSS, Parquet, or SQLite**.
- **Analysis & reports** — run analysis scripts over your data and generate reports in
  **Markdown and HTML** (PDF is planned).
- **Files** — your project's generated outputs plus uploaded assets and exports.
- **Team** — invite members and assign roles.

The features below are additions on top of this core.

## Premium features

| Feature | Plans | What it does |
| :--- | :--- | :--- |
| **Webhooks** | Plus, Pro, Corporate | Get a signed `POST` to your own URL (or a Slack channel) when a deploy or run finishes. See [[Schedules & Webhooks\|Cloud-Scheduling-and-Webhooks]]. |
| **Schedules** | Plus, Pro, Corporate | Run an analysis script or a full run-all on a cron schedule. See [[Schedules & Webhooks\|Cloud-Scheduling-and-Webhooks]]. |
| **Connectors & Git mirrors** | Plus and up, tiered per target | Move tables to external stores and mirror the repo to an external Git host. The Connectors screen unlocks at Plus; each target has its own minimum plan — everyday destinations (Sheets, Excel 365, Supabase) and GitHub mirrors at Plus; storage, warehouses, BYO infrastructure (S3, GCS, Azure, BigQuery, Snowflake, your own Postgres, SFTP, REDCap, HTTP) and GitLab / self-hosted mirrors at Pro; custom MCP servers at Corporate. See [[Connectors\|Cloud-Connectors]]. |
| **SSO (SAML / OIDC)** | Pro, Corporate | Configure single sign-on for your organization. |
| **Self-hosted deployment** | Corporate | Run siamang Cloud on your own infrastructure for data-residency or control. |

## Choosing the right plan

- **Free** — for individuals, evaluation, and small one-off studies. Two projects, two
  members, and up to 500 responses per project.
- **Plus** — for small teams running recurring studies that need automation: unlimited
  responses, webhooks and schedules, everyday connectors (Sheets, Excel 365, Supabase),
  and GitHub mirrors.
- **Pro** — for teams that need scale and integrations: unlimited projects, members, and
  responses, plus the full connector catalog, GitLab / self-hosted mirrors, and SSO.
- **Corporate** — for organizations with data-residency or on-prem requirements:
  everything in Pro plus self-hosted deployment, arranged with sales.

When you reach a cap (for example, trying to add a third project on Free) or use a feature
your plan doesn't include, the app tells you and points you to **Billing** — you won't hit
a dead end.

## During the open beta

siamang Cloud is in **open beta**, so billing works a little differently for now. Open
**Organization settings → Billing** to see your status:

- **Every new workspace starts on a 30-day Pro trial** — full access to every Pro feature
  while it lasts, with a countdown shown on the Billing screen.
- **Until a payment provider is connected**, the other plans show **"Available at the
  official release"** and **nothing is ever charged**. Once Stripe billing is enabled,
  Free, Plus, and Pro become self-serve upgrades from the Billing screen (Corporate is
  arranged with sales).
- **When the trial ends**, the organization moves to the **Free** plan. Nothing is
  paused or removed: your projects, data, and running surveys keep working within the
  Free caps (2 projects, 2 members, 500 responses per project), and anything beyond
  them prompts an upgrade.

Billing is always per organization — one plan covers all of its members and projects —
and only the organization **owner** manages it.

## Plans vs. team roles

Your plan and your role are two different things. The **plan** decides what the
*organization* can do; your **role** decides what *you* can do inside it. Every member has
one of three roles:

| Role | Can do |
| :--- | :--- |
| **owner** | Everything, including changing the plan and billing, organization settings, and SSO. There is one owner. |
| **admin** | Manage the organization profile and members (invite, change roles, remove), create projects, set branch protection, and manage integrations. |
| **member** | Contribute to projects: edit code, run analysis, deploy, and manage project secrets. |

Only the **owner** can purchase, change, or cancel the subscription — regardless of plan.

## See also

- [[Connectors|Cloud-Connectors]] — unlock at Plus, tiered per target
- [[Schedules & Webhooks|Cloud-Scheduling-and-Webhooks]] — a Plus and up feature
- [[Cloud Overview|Cloud-Overview]] — what the platform does and who it's for
