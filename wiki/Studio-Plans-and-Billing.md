# Plans, Trial and Billing

Studio is priced **per organization**, not per seat: one plan covers everyone in
the workspace, and responses are not metered on paid plans. This page lists
what each plan includes, explains the 30-day Pro trial and what happens when
it ends, walks through the **Billing** tab, and shows what you see when you
reach a limit.

---

## The plans

| | Free | Plus | Pro | Corporate |
|---|---|---|---|---|
| Price shown in Studio | Free | $25/mo | $99/mo | Custom (**Contact sales**) |
| Projects per organization | 2 | 10 | unlimited | unlimited |
| Members per organization (owner included) | 2 | 15 | unlimited | unlimited |
| Completed responses per published survey | 1,000 | unlimited | unlimited | unlimited |
| Stored files per organization | 250 MB | 5 GB | 50 GB | unlimited |
| Analysis flows per project | 3 | 20 | unlimited | unlimited |
| Access codes per questionnaire | 100 | 5,000 | unlimited | unlimited |
| One flow run may take | 5 min, 512 MB | 15 min, 1 GB | 30 min, 2 GB | 30 min, 2 GB |
| **Run to here** previews per person, per project, per hour | 30 | 120 | 600 | unlimited |
| Previews running at once, per person | 1 | 1 | 2 | 4 |
| Builder: all question types, logic, quotas, randomization, theme, script library | ✓ | ✓ | ✓ | ✓ |
| **Download .py**, research bundles, every data export | ✓ | ✓ | ✓ | ✓ |
| Flows: **Run**, **Run all** | ✓ | ✓ | ✓ | ✓ |
| Custom JavaScript and custom CSS in the questionnaire | — | ✓ | ✓ | ✓ |
| Live tiles that recompute on new responses; public Live share links | — | ✓ | ✓ | ✓ |
| Schedules and webhooks | — | ✓ | ✓ | ✓ |
| Saving to the organization library | — | ✓ | ✓ | ✓ |
| Email invitations to respondents, per month / per day | — | 1,000 / 300 | 5,000 / 1,500 | unlimited |
| Recipients in the organization's first mailing | — | up to 200 | up to 500 | no cap |
| AI assistant credits, per month / per day | — | 8,000 / 2,000 | 50,000 / 8,000 | 300,000 / 30,000 |
| AI assistant requests per person, per hour | — | 30 | 100 | 300 |
| Larger AI model for drafting a questionnaire from a brief | — | — | ✓ | ✓ |
| Connectors | — | everyday (see below) | all | all, plus MCP |
| Single sign-on (SAML / OIDC) | — | — | after the beta | after the beta |
| Self-hosting | — | — | — | ✓ |

**Connectors by plan** *(details in [[Connectors|Studio-Connectors]])*:

| Plan | Connectors |
|---|---|
| Plus | Google Sheets, Excel 365, Supabase, HubSpot (Airtable and Dropbox: coming soon) |
| Pro | everything in Plus, plus Amazon S3, Google Cloud Storage, Azure Blob Storage, BigQuery, Snowflake, PostgreSQL database, SFTP, REDCap, Salesforce, HTTP endpoint |
| Corporate | everything in Pro, plus MCP servers (coming soon) |

> **Plan.** During the Pro trial, everything marked *(Plus)* or *(Pro)* in this
> guide is available, with the exceptions listed under
> [The Pro trial](#the-pro-trial).

### How the numbers are counted

- **Responses** are counted per **published survey** (each environment's link,
  such as `pilot` or `main`, counts separately). Only **completed** responses
  count; partial interviews don't. A survey's own response cap, if you set one,
  applies too, and the lower of the two wins.
- **Storage** is the total of the files stored for all projects of the
  organization, checked when you upload. A single upload can be at most 50 MB
  on every plan.
- **Flows** and **access codes** are counted when you **Save**.
- **Run to here** previews: the hourly allowance is per person and per
  project, counted over the last 60 minutes. "At once" is per person across
  all projects.
- **Flow runs** get one CPU and no internet access on every plan. The plan
  buys time and memory. A run that hits its ceiling is stopped, and its log
  names the limit, for example "the free plan allows 5 min per flow run; plus
  allows 15 min". An early stop is never mistaken for a bug in your analysis.
- **AI credits** measure how much text the assistant sends to and receives
  from the model: one credit is about 1,000 tokens (pieces of words). The daily
  allowance resets at midnight UTC and the monthly one with the next month.
  See [[AI Assistant|Studio-AI-Assistant]].

### Your history is never capped

Every Save, every version, every research bundle and every export stays
available on every plan, for as long as the project exists. Going back to what
you did is what the product is *for*, and charging for it would be a paywall
on your own work.

The principle: **everything about owning your data and your code is free on
every plan.** You pay for computation, scale and integrations, never for the
right to take your work with you.

### Over a limit is not frozen

A count you are already over, after a downgrade for example, never locks a
project. You can keep saving, editing and deleting; you just cannot **add**.
A project with 10 flows on Free can still be saved, and can be cut down to 3,
but not grown to 11. The same goes for projects, members and access codes.

---

## The Pro trial

Every new account gets its own organization on a **30-day Pro trial**, with no
card required (see [[Sign Up and Sign In|Studio-Sign-Up-and-Sign-In]]).

**Where you see it**

- the topbar pill `Pro trial · 27d` (hover: "Pro trial — 27 days left");
- a `27d` pill next to the organization in the workspace chip menu;
- **Settings → Billing**: "**Pro · 27 days left.** Full access to every Pro
  feature; one subscription covers the whole organization. Afterward the
  organization switches to the free plan — your data and surveys are kept."

The day count is rounded up, so a trial with a few hours left shows `1d`.

**What is not unlocked during an unpaid trial**

- **Email invitations to respondents.** Mailings leave from a sending domain
  shared by every organization, so they unlock with the first payment. A new
  mailing is refused with "email invitations unlock with the first payment — a
  trial organization cannot send mailings".
- **The AI assistant** runs on a **one-off allowance of 500 credits** (at most
  200 a day and 10 requests per person per hour), not Pro's monthly 50,000. It
  does not renew. When it is spent, you see "…this organization's assistant
  trial allowance cannot cover this request (… of 500 credits used) — subscribe
  to keep using it". The owner still has to turn the assistant on first.
- **Single sign-on** is not available in the beta on any plan.

**Reminders**

- The owners get an email **7 days** and again **1 day** before the trial
  ends: "Your Siamang Studio Pro period for *organization* ends in N day(s)".
- In the last **3 days**, a banner appears under the topbar: "**Pro trial ends
  in 3 days.** After the trial, Free plan limits apply. Your data is preserved
  and stays exportable. Choose a paid plan in Settings → Billing to keep using
  paid features."

**One trial per email address.** Signing up again with the same address does
not start a new trial, and organizations you create later start on Free.

---

## When the trial ends

The organization moves to the **Free** plan. It does **not** become read-only:
you keep signing in, editing, saving, publishing, running flows and
collecting responses, within Free's limits. Nothing is deleted. The owners get
an email: "*organization* is now on the free plan — the Siamang Studio Pro
period ended".

Concretely, once the trial is over:

| Area | What changes |
|---|---|
| Projects and members | Everything you have keeps working. **New project** is blocked while the organization has 2 or more projects, and **Invite member** while it has 2 or more members. |
| Responses | A published survey that already has **1,000 or more completed responses** stops accepting new completions. Surveys below that keep collecting up to 1,000. |
| Custom JavaScript / CSS | Publishing a Save that contains custom JavaScript or custom CSS is refused ("Custom JavaScript in the questionnaire is included from Plus — remove the script or upgrade to deploy this Save", or the CSS equivalent). Surveys already live keep running. |
| Flows | Runs get Free's 5 minutes and 512 MB. Saves may not add flows beyond 3 per project; existing ones stay. |
| **Run to here** | 30 per hour per project, one at a time. |
| Live | Tiles no longer recompute on their own (you can still refresh them by hand); public Live share links stop answering. |
| Schedules, webhooks, connectors | Scheduled runs are skipped; connector runs, new webhooks and new schedules need Plus. |
| Email invitations, AI assistant | Not available on Free. |
| Storage | Uploads that would take the organization past 250 MB are refused; existing files stay. |
| Library | Saving to the organization library needs Plus; items already saved can still be used. |

Upgrading at any time lifts the limits immediately (see
[Upgrading, downgrading and canceling](#upgrading-downgrading-and-canceling)).

### Frozen workspaces

A **frozen** workspace is something different, and rare: Siamang support can
freeze an organization by hand. A trial ending never freezes anything. A
frozen organization is read-only: you can sign in, view and export everything,
but editing, publishing, flows and response collection stop. Every screen shows
the banner "**This workspace is frozen and read-only.** All your data is
preserved: you can keep viewing and exporting everything (Data → Export).
Editing, deploys, flows and response collection are unavailable. Contact
support to resolve the freeze." Any change you try is refused with "…This
workspace is frozen and read-only; your data is preserved and stays
viewable/exportable — contact support." A payment on the organization lifts the
freeze and resumes the surveys it paused.

---

## The Billing tab

**Settings → Billing** of an organization. Every member can open it, and **only
the owner can change the plan**. Other members see "Only the owner can change
the organization's plan." and the plan buttons are disabled for them.

```
┌ Pro · 27 days left. Full access to every Pro feature; …                      ┐
┌ Beta offer: 12 months of Plus for $200 — one payment, 33% off …  [Get the Plus year] ┐
┌ Beta offer: 12 months of Pro for $800 — one payment, 33% off …   [Get the Pro year]  ┐
┌ Card, invoices and cancellation are managed in the Stripe portal. [Manage billing]   ┐

 ┌ Free ─────────┐ ┌ Plus ─────────┐ ┌ Pro  trial ───┐ ┌ Corporate ────┐
 │ Free          │ │ $25/mo        │ │ $99/mo        │ │ Custom        │
 │ Kick the …    │ │ Run real …    │ │ Scale …       │ │ Enterprise …  │
 │ • …           │ │ • …           │ │ • …           │ │ • …           │
 │ [Coming soon] │ │ [Coming soon] │ │ [Extend Pro]  │ │[Contact sales]│
 └───────────────┘ └───────────────┘ └───────────────┘ └───────────────┘
```

**The status note** at the top shows the trial countdown while the
organization has one. Once card payments are live it adds "Subscribe or
extend now: **billing starts only when the free period ends**."

**Plan cards.** One card per plan: its name (the plan you are trialing carries
a **trial** pill and is highlighted), its price, a one-line summary and a
short list of what it includes. The summaries read:

| Plan | Summary on the card |
|---|---|
| Free | "Kick the tires — 2 studies, 1,000 responses each." |
| Plus | "Run real fieldwork — 10 studies, unlimited responses, schedules, webhooks & first connectors (Sheets, Excel 365, Supabase, GitHub)." |
| Pro | "Scale without limits — unlimited studies & team, all connectors (S3, warehouses, GitLab) and SSO." |
| Corporate | "Enterprise & self-hosted — run it on your own infra, with onboarding and support." |

> **Note.** The Plus and Pro summaries mention GitHub and GitLab; those are
> not available as Studio connectors. The connector lists above are what each
> plan actually includes.

The button at the bottom of a card is one of:

| Button | Meaning |
|---|---|
| **current plan** (a label) | the plan the organization is on, when it is not on a trial |
| **Upgrade** | a higher plan than the current one; opens the checkout dialog (owner only) |
| **Extend Pro** | on the plan you are trialing; subscribes now, with billing starting when the trial ends (owner only) |
| **Coming soon** (disabled) | card payments are not live yet in the beta ("Available at the official release") |
| **Contact sales** (disabled) | Corporate is arranged with the Siamang team, not bought in the app ("Sales-assisted — coming soon"). Write to `info@siamang-team.org`. |

There is no button to move to a lower plan on the cards. See
[Upgrading, downgrading and canceling](#upgrading-downgrading-and-canceling).

**Beta offers.** While a beta offer runs, the owner sees one line per offer
with its price and deadline:

- "**Beta offer: 12 months of Plus for $200** — one payment, 33% off the
  monthly price, until *date*." with **Get the Plus year**;
- "**Beta offer: 12 months of Pro for $800** — one payment, 33% off the
  monthly price, until *date*." with **Get the Pro year**.

An offer is a single payment for twelve months of that plan. Bought during a
trial, the twelve months start when the trial ends; otherwise they start on
purchase. After the twelve months the organization returns to Free unless you
buy again. An offer cannot be added on top of an active monthly subscription
("…a subscription is active; a year offer cannot be added to it — cancel the
subscription first"). After the deadline the offers disappear.

**The checkout dialog.** **Upgrade**, **Extend Pro** and the offer buttons
open **Switch to *plan***, which shows the plan and its price (`$25/mo`,
`$99/mo`, `$200 one-time`, `$800 one-time`), and the line "Plans, trials and
year offers are described in the Terms of Use; how we handle your data is in
the Privacy Policy. By continuing you agree to both." With card payments live,
it says "You'll be taken to Stripe's secure checkout to enter card details.
The plan activates as soon as the payment completes." and offers **Cancel** and
**Continue to checkout**.

**Manage billing.** Once card payments are live, the owner sees "Card,
invoices and cancellation are managed in the Stripe portal." and **Manage
billing**, which opens the payment portal. Before the organization's first
checkout it answers "Could not open the billing portal. No billing account yet
— complete a checkout first."

---

## Upgrading, downgrading and canceling

- **Upgrading.** Click **Upgrade** (or **Extend Pro**) → **Continue to
  checkout**, pay on Stripe's page, and you are brought back to Studio with the
  notice "Payment received — your plan is being activated". The new plan
  applies as soon as the payment is confirmed. If you leave the payment page
  instead, you see "Checkout canceled — your plan is unchanged".
- **Buying during the trial** never shortens it: billing starts when the free
  period ends. The exception is the last two days or so of a trial, when
  billing starts right away.
- **Switching between Plus and Pro** on an existing subscription takes effect
  immediately. The difference is charged or credited pro rata.
- **Downgrading and canceling** happen in the payment portal (**Manage
  billing**). A cancellation takes effect at the end of the period you have
  paid for; until then the plan stays. Buying the same plan again before that
  date keeps the subscription running.
- **Downgrades delete nothing.** Projects and members over the new limits keep
  working; you simply cannot create or invite more until usage fits. Features
  above the new plan stop being available.
- **A failed card payment.** The owners get an email, "Payment failed for
  *organization* on Siamang Studio". Update the card under **Manage billing**.
  The payment provider retries for a few days before the subscription is
  canceled.
- Until card payments are live, write to `info@siamang-team.org` about plans,
  invoices or cancellation.

---

## What happens at a limit

| Limit | What you see |
|---|---|
| Projects | **New project** is disabled ("Your plan allows 2 projects — upgrade to add more") with the note "You've reached the **2-project** limit on the free plan. **Upgrade your plan** to add more." The API answers "Could not create project. Plan 'free' allows up to 2 projects; upgrade to add more." |
| Members | **Invite member** is disabled ("Your plan allows 2 members — upgrade to add more") with a similar note. Pending invitations count toward the limit: "Could not add member. Plan 'free' allows up to 2 members; upgrade to add more." |
| Responses | The survey stops accepting new completed responses once it has reached the cap. |
| Storage | "Upload failed. Plan 'free' allows up to 250 MB of stored files; delete files or upgrade to add more." |
| Flows per project | the Save is refused: "Save failed. Plan 'free' allows up to 3 analysis flows per project; this Save would have 4 — delete one or upgrade." |
| Access codes | the Save is refused: "Save failed. Plan 'free' allows up to 100 access codes; this Save would have 150." |
| **Run to here** | "preview limit reached: 30 runs per hour on the free plan", or "a preview is already running: the free plan runs 1 at a time — wait for it to finish". **Run** still works. |
| Flow run time or memory | the run stops, and its log names the limit (see [How the numbers are counted](#how-the-numbers-are-counted)) |
| Email invitations | the mailing is refused with the month's or day's count, e.g. "this mailing would exceed the plus plan's 300 invitation emails per day (… sent today, … to send) — send the rest tomorrow", or "an organization's first mailing is limited to 200 recipients (… selected) — start with a smaller list, then send the rest" |
| AI assistant | "the assistant is not included in the free plan — upgrade to Plus", or the daily or monthly allowance message with the credits used |
| A Plus or Pro feature on a lower plan | the control shows a card such as "**Webhooks is a Plus feature** — Upgrade your plan to unlock webhooks." with **View plans**, which opens **Billing** |

Nothing is deleted when you reach a limit or downgrade: the data stays and
exports keep working.

---

## Academic and non-commercial use

The siamang engine that runs your questionnaire and analysis is
source-available and **free for non-commercial use**: personal use, research,
education, and non-commercial organizations. A research bundle you download
from Studio runs on it at no cost for such purposes. Paid Studio plans include
a commercial license for the engine. For academic pricing, or a commercial
license for using the engine outside Studio, write to `info@siamang-team.org`.

## See also

- [[Organizations and Team|Studio-Organizations-and-Team]]
- [[Limits and Quotas at a Glance|Studio-Limits-Reference]]
- [[Connectors|Studio-Connectors]]
- [[AI Assistant|Studio-AI-Assistant]]
- [[Reproducibility: Code, Bundles and Citation|Studio-Reproducibility]]

<!-- studio-nav -->
---

← [[Project Settings|Studio-Project-Settings]] · [Studio contents](Studio-Overview#all-pages) · [[The Builder|Studio-Builder-Overview]] →
