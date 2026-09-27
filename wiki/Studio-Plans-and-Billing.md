# Plans, Trial and Billing

Studio is priced **per organization**, not per seat: one plan covers everyone in
the workspace, and responses are not metered on paid plans. This page lists
what each plan includes, explains the 30-day Pro trial, paid periods and what
happens when they end, walks through the **Billing** tab, and shows what you
see when you reach a limit.

---

## The plans

| | Free | Plus | Pro | Corporate |
|---|---|---|---|---|
| Price shown in Studio | Free | $25/mo | $99/mo | Custom (**Contact sales**) |
| Projects per organization | 2 | 10 | unlimited | unlimited |
| Members per organization (owner included) | 2 | 15 | unlimited | unlimited |
| Completed responses per project (all environments together) | 1,000 | unlimited | unlimited | unlimited |
| Stored files per organization | 250 MB | 5 GB | 50 GB | unlimited |
| Analysis flows per project | 3 | 20 | unlimited | unlimited |
| Access codes per questionnaire | 100 | 5,000 | unlimited | unlimited |
| One flow run may take | 5 min, 512 MB | 15 min, 1 GB | 30 min, 2 GB | 30 min, 2 GB |
| **Run to here** previews per person, per project, per hour | 30 | 120 | 600 | unlimited |
| Previews running at once, per person | 1 | 1 | 2 | 4 |
| Builder: all question types, logic, quotas, randomization, theme, script library | ✓ | ✓ | ✓ | ✓ |
| **Download .py**, research bundles, every data export | ✓ | ✓ | ✓ | ✓ |
| Flows: **Run**, **Run all** | ✓ | ✓ | ✓ | ✓ |
| Coding open answers by hand and by rules (the codeframe editor, the **Code open answers** node) | ✓ | ✓ | ✓ | ✓ |
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

- **Responses** are counted per **project**: the Free plan's 1,000 is shared
  by all of the project's environments together (`pilot` and `main`, say).
  Only **completed** interviews count. Partial interviews and screen-outs
  don't, and a screen-out is still recorded when the cap is full. In a
  project made from the example study, its sample rows don't count either. A
  survey's own response cap, if you set one, is counted over that survey
  alone, the same way; whichever cap fills first stops new completions.
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
  See [[AI Assistant|Studio-AI-Assistant]]. Coding open answers spends none:
  it is done by hand and by rules, and AI coding of open answers is switched
  off on this platform (see [[Coding Open Answers|Studio-Open-Answer-Coding]]).

> **Note.** The Free response cap used to be counted for each environment
> separately, with screen-outs included. It now counts completed interviews
> across the whole project, so the same responses can put a project on
> either side of the cap: a Free project with 700 completed responses in
> `pilot` and 400 in `main` has 1,100 and stops accepting completions, while
> one whose count was swollen by screen-outs gets room back. Nothing already
> collected is removed. To make room, delete test responses you no longer
> need in **Data** (owners and admins can), or upgrade.

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
- the **Organizations** screen: **Pro trial · 27d left**;
- **Settings → Billing**: "**Pro trial · 27 days left.** Full access to every
  Pro feature; one subscription covers the whole organization. Afterward the
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
  ends: "Your Siamang Studio Pro trial for *organization* ends in N day(s)".
- In the last **3 days**, a banner appears under the topbar: "**Pro trial ends
  in 3 days.** After the trial, Free plan limits apply. Your data is preserved
  and stays exportable. Choose a paid plan in Settings → Billing to keep using
  paid features."

**One trial per email address.** Signing up again with the same address does
not start a new trial, and organizations you create later (see
[Creating another organization](Studio-Organizations-and-Team#creating-another-organization))
start on Free.

---

## When the trial ends

The organization moves to the **Free** plan. It does **not** become read-only:
you keep signing in, editing, saving, publishing, running flows and
collecting responses, within Free's limits. Nothing is deleted. The owners get
an email: "*organization* is now on the free plan — the Siamang Studio Pro
trial ended". The end of a paid period works the same way (see
[Paid periods](#paid-periods)).

Concretely, once the trial is over:

| Area | What changes |
|---|---|
| Projects and members | Everything you have keeps working. **New project** is blocked while the organization has 2 or more projects, and **Invite member** while it has 2 or more members. |
| Responses | A project that already has **1,000 or more completed responses**, all its environments together, stops accepting new completions. Projects below that keep collecting until the project reaches 1,000. |
| Custom JavaScript / CSS | Publishing a Save that contains custom JavaScript or custom CSS is refused ("Custom JavaScript in the questionnaire is included from Plus — remove the script or upgrade to deploy this Save", or the CSS equivalent). Surveys already live keep running. |
| Flows | Runs get Free's 5 minutes and 512 MB. Saves may not add flows beyond 3 per project; existing ones stay. |
| **Run to here** | 30 per hour per project, one at a time. |
| Live | Tiles no longer recompute on their own (you can still refresh them by hand); public Live share links stop answering. |
| Schedules, webhooks, connectors | Scheduled runs are skipped; connector runs, new webhooks and new schedules need Plus. In **Flows**, **Schedule a run** is replaced by **Requires Plus**. |
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

## Paid periods

A beta year offer (see [The Billing tab](#the-billing-tab)) gives the
organization a plan for a paid period that ends on a date. Studio shows it as
paid, not as a trial:

| Where | During a paid Plus period (example) |
|---|---|
| Topbar pill | `Plus · 200d`, hover "Paid period — 200 days left" |
| Workspace chip menu | a `200d` pill, hover "Paid period — 200 days left" |
| **Organizations** screen | **Paid period · 200d left** |
| **Settings → Billing** | "**Plus · 200 days left of the paid period.** Full access to every Plus feature; one subscription covers the whole organization. …", and the Plus card carries a **paid period** pill |
| Banner, last 3 days | "**Your paid Plus period ends in 3 days.** Afterward, Free plan limits apply. Your data is preserved and stays exportable. Renew in Settings → Billing to keep using paid features." Once it is over: "**Your paid period has ended.**" |
| Owners' emails, 7 and 1 day before | "Your Siamang Studio paid Plus period for *organization* ends in N day(s)" |
| Owners' email at the end | "*organization* is now on the free plan — the Siamang Studio paid Plus period ended" |

A paid period is not a trial: **email invitations** to respondents work, and
the **AI assistant** has the plan's full monthly allowance, not the trial's
one-off 500 credits. When the period ends, the organization moves to Free
exactly as after a trial (see [When the trial ends](#when-the-trial-ends)).

---

## The Billing tab

**Settings → Billing** of an organization. Every member can open it, and **only
the owner can change the plan**. Other members see "Only the owner can change
the organization's plan." and the plan buttons are disabled for them.

```
┌ Pro trial · 27 days left. Full access to every Pro feature; …                ┐
┌ Beta offer: 12 months of Plus for $240 — one payment, 20% off …  [Get the Plus year] ┐
┌ Beta offer: 12 months of Pro for $900 — one payment, 24% off …   [Get the Pro year]  ┐
┌ Card, invoices and cancellation are managed in the Stripe portal. [Manage billing]   ┐

 ┌ Free ─────────┐ ┌ Plus ─────────┐ ┌ Pro  trial ───┐ ┌ Corporate ────┐
 │ Free          │ │ $25/mo        │ │ $99/mo        │ │ Custom        │
 │ Kick the …    │ │ Run real …    │ │ Scale …       │ │ Enterprise …  │
 │ • Core        │ │ • AI assistant│ │ • AI assistant│ │ • AI assistant│
 │   features    │ │ • …           │ │ • …           │ │ • …           │
 │               │ │ [Upgrade]     │ │ [Extend Pro]  │ │[Contact sales]│
 └───────────────┘ └───────────────┘ └───────────────┘ └───────────────┘
```

The sketch shows an organization on the Pro trial once card payments are
live. Until then, the cards' buttons read **Coming soon** (see the table
below).

**The status note** at the top shows the countdown while the organization
has a trial or a paid period that ends on a date: "**Pro trial · 27 days
left.**" or, for a paid period, "**Plus · 200 days left of the paid
period.**", followed by "Full access to every *plan* feature; one
subscription covers the whole organization. Afterward the organization
switches to the free plan — your data and surveys are kept." Once card
payments are live it adds "Subscribe or extend now: **billing starts only when
the free period ends**." When Plus was bought during the trial, the note says
instead "Afterward the organization moves to the **Plus** plan you chose, on
*date*." Without a countdown it reads "The Siamang engine is
source-available; Studio is billed per plan. One subscription covers the whole
organization."

**Plan cards.** One card per plan: its name (the plan whose trial or paid
period is running is highlighted and carries a **trial** or **paid period**
pill), its price, a one-line summary and the list of what it includes. The
summaries read:

| Plan | Summary on the card |
|---|---|
| Free | "Kick the tires — 2 studies, 1,000 responses each." |
| Plus | "Run real fieldwork — 10 studies, unlimited responses, schedules, webhooks & first connectors (Sheets, Excel 365, Supabase, GitHub)." |
| Pro | "Scale without limits — unlimited studies & team, all connectors (S3, warehouses, GitLab) and SSO." |
| Corporate | "Enterprise & self-hosted — run it on your own infra, with onboarding and support." |

> **Note.** The Plus and Pro summaries mention GitHub and GitLab; those are
> not available as Studio connectors. The connector lists above are what each
> plan actually includes.

Under the summary, each card lists the features the plan unlocks:

| Card | Listed features |
|---|---|
| Free | Core features |
| Plus | AI assistant · Connectors · Custom CSS in the survey theme · Custom JavaScript in surveys · Email invitations · Organization library · Live tiles recomputed on new responses · Scheduled runs · Webhooks |
| Pro | the Plus list, with **Larger AI model for drafts from a brief** after **AI assistant** |
| Corporate | the Pro list, plus **Self-hosting** |

Single sign-on is not listed on any card: it is not available in the beta.

The button at the bottom of a card is one of:

| Button | Meaning |
|---|---|
| **current plan** (a label) | the plan the organization is on, when no trial or paid period is running |
| **starts *date*** (a label) | the plan bought during the trial; it starts when the trial ends |
| **Upgrade** | a higher plan than the current one (during a trial or a paid period, whichever of Plus and Pro is not the running plan); opens the checkout dialog (owner only) |
| **Extend Pro** / **Extend Plus** | on the plan whose trial or paid period is running; subscribes now, with billing starting when the running period ends (owner only) |
| **Coming soon** (disabled) | card payments are not live yet in the beta ("Available at the official release"). Until they are, every card except the current plan and Corporate shows it. |
| **Contact sales** (disabled) | Corporate is arranged with the Siamang team, not bought in the app ("Sales-assisted — coming soon"). Write to `info@siamang-team.org`. |

There is no button to move to a lower plan on the cards. See
[Upgrading, downgrading and canceling](#upgrading-downgrading-and-canceling).

**Beta offers.** While a beta offer runs, the owner sees one line per offer
with its price and deadline:

- "**Beta offer: 12 months of Plus for $240** — one payment, 20% off the
  monthly price, until *date*." with **Get the Plus year**;
- "**Beta offer: 12 months of Pro for $900** — one payment, 24% off the
  monthly price, until *date*." with **Get the Pro year**.

An offer is a single payment for twelve months of that plan: a beta special
for one year, not a price that renews. Bought during a trial, the twelve months
start when the trial ends (a Plus year bought during the Pro trial leaves the
organization on Pro until then); otherwise they start on purchase. After the
twelve months the organization returns to Free unless you subscribe to a
plan. An offer cannot be added on top of an active monthly subscription
("…a subscription is active; a year offer cannot be added to it — cancel the
subscription first"). After the deadline the offers disappear.

**The checkout dialog.** **Upgrade**, **Extend Pro** (or **Extend Plus**) and the offer buttons
open **Switch to *plan***, which shows the plan and its price (`$25/mo`,
`$99/mo`, `$240 one-time`, `$900 one-time`), and the line "Plans, trials and
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
  billing starts right away. **Pro** (a subscription or the Pro year) keeps the
  organization on Pro. **Plus** (a subscription or the Plus year) starts when
  the trial ends: the organization stays on the Pro trial until then and then
  moves to Plus, not to Free. The Plus card shows **starts *date***, and
  canceling that Plus subscription before the trial ends leaves the trial
  running as if nothing was bought. In the last two days or so of the trial,
  when billing cannot wait, a Plus subscription starts right away. A purchase
  lifts the trial's limits (email invitations, the AI allowance) at once.
  While a Plus year you bought waits for the trial to end, no other plan can
  be bought, so its months are never lost.
- **Switching between Plus and Pro** on an existing subscription takes effect
  immediately. The difference is charged or credited pro rata.
- **A subscription that has already ended.** If the payment provider has
  already canceled or expired the organization's subscription before Studio
  heard about it, **Upgrade** takes you to a new checkout: Studio drops the
  ended subscription and sells a fresh one, as for an organization that never
  subscribed. The Activity log records this as `billing.subscription.stale`.
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
| Projects | **New project** is disabled on the **Projects** tab, in the workspace chip menu and on the **Library** tab ("Your plan allows 2 projects — upgrade to add more"). The **Projects** tab adds the note "You've reached the **2-project** limit on the free plan. **Upgrade your plan** to add more." The API answers "Could not create project. Plan 'free' allows up to 2 projects; upgrade to add more." |
| Members | **Invite member** is disabled ("Your plan allows 2 members — upgrade to add more") with a similar note. Pending invitations count toward the limit: "Could not add member. Plan 'free' allows up to 2 members; upgrade to add more." |
| Responses | Once the project's completed responses, all environments together, reach 1,000, its surveys stop accepting new completions. A respondent who opens the link then sees "Thank you for your interest" / "We have already reached our target sample for participants like you." (or the survey's own wording of that screen from **Theme → Wording**, and its quota-full redirect if it has one); someone already answering sees it when they submit. Screen-outs are still recorded. A survey published before this behavior shows the notice only on submitting: republish it so respondents see it as the page opens. |
| Storage | "Upload failed. Plan 'free' allows up to 250 MB of stored files; delete files or upgrade to add more." |
| Flows per project | the Save is refused: "Save failed. Plan 'free' allows up to 3 analysis flows per project; this Save would have 4 — delete one or upgrade." |
| Access codes | the Save is refused: "Save failed. Plan 'free' allows up to 100 access codes; this Save would have 150." |
| **Run to here** | "preview limit reached: 30 runs per hour on the free plan", or "a preview is already running: the free plan runs 1 at a time — wait for it to finish". **Run** still works. |
| Flow run time or memory | the run stops, and its log names the limit (see [How the numbers are counted](#how-the-numbers-are-counted)) |
| Email invitations | the mailing is refused with the month's or day's count, e.g. "this mailing would exceed the plus plan's 300 invitation emails per day (… sent today, … to send) — send the rest tomorrow", or "an organization's first mailing is limited to 200 recipients (… selected) — start with a smaller list, then send the rest" |
| AI assistant | "the assistant is not included in the free plan — upgrade to Plus", or the daily or monthly allowance message with the credits used |
| Schedules | In **Flows**, the **Schedule a run** button reads **Requires Plus** (hover: "Schedules are available from the Plus plan") and opens **Billing** |
| A Plus or Pro feature on a lower plan | the control shows a card such as "**Webhooks is a Plus feature** — Upgrade your plan to unlock webhooks." with **View plans**, which opens **Billing** |

Nothing is deleted when you reach a limit or downgrade: the data stays and
exports keep working.

---

## Academic and non-commercial use

The siamang engine that runs your questionnaire and analysis is
source-available and **free for non-commercial use**: personal use, research,
education, and non-commercial organizations. A research bundle you download
from Studio runs on it at no cost for such purposes. Paid Studio plans include
a commercial license for the engine. For a commercial license for using the
engine outside Studio, write to `info@siamang-team.org`.

## See also

- [[Organizations and Team|Studio-Organizations-and-Team]]
- [[Limits and Quotas at a Glance|Studio-Limits-Reference]]
- [[Connectors|Studio-Connectors]]
- [[AI Assistant|Studio-AI-Assistant]]
- [[Reproducibility: Code, Bundles and Citation|Studio-Reproducibility]]

<!-- studio-nav -->
---

← [[Project Settings|Studio-Project-Settings]] · [Studio contents](Studio-Overview#all-pages) · [[The Builder|Studio-Builder-Overview]] →
