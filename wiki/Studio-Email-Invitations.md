# Email Invitations

*(Plus)* Instead of one anonymous link, give every respondent their **own**
link by email: completion is tracked per person, and a reminder goes only to
those who have not finished. Everything lives at the bottom of **Distribute**,
in the **Email invitations** panel.

> **Plan.** Email invitations are included from **Plus**. An organization on the
> unpaid **trial** cannot use them at all — neither import contacts nor send —
> until the first payment: the panel reads "Personal links by email — unlock
> with your first payment." with **Choose a plan**. On **Free** it reads
> "Personal links by email — included from Plus." with **Upgrade to Plus**.
> Invitations are sent from Studio's shared sending domain, which is why they
> are not available without a paid plan.

---

## The panel

```
┌ Email invitations                                        [Import contacts] [New mailing] ┐
│ 412 contacts · 3 unsubscribed · each invitee gets a personal link; reminders go to      │
│ those who have not finished. · 588 of 1,000 emails left this month · 300 per day        │
├──────────┬───────────────────────────────┬──────────┬─────────┬─────────────┬─────────────┤
│ Kind     │ Mailing                       │ Sent     │ Started │ Completed   │             │
│ invite   │ Brand study: your personal link│ 409 · 2 failed │ 188 │ 141 · 34% │ [Remind] [Recipients] │
│          │ main · 6/4/2026, 9:00 AM       │          │         │             │             │
│ reminder │ Reminder: Brand study: …       │ 266      │ 41      │ 60 · 23%    │ [Recipients]│
└──────────┴───────────────────────────────┴──────────┴─────────┴─────────────┴─────────────┘
```

The subtitle counts your contacts (**N contacts · M unsubscribed**) and, on a
plan with a monthly allowance, **N of CAP emails left this month**, the daily
allowance (**· 300 per day**) and — before your organization's very first
mailing — **· first mailing up to 200**.

With no mailing yet the panel says "No mailing yet — write the invitation and
send it to your contacts.", or, with no contacts, "Paste addresses (one per
line, optionally with a name) to build the contact list."

The **New mailing** button is disabled until you can send; its tooltip says
why: "Upgrade to Plus", "Import contacts first" or "Publish an environment
first".

---

## Contacts

Contacts belong to the **project**: each study has its own list, and an
unsubscribe applies to that study only.

### Importing

1. Click **Import contacts**.
2. Paste one contact per line, in any of these shapes:

   ```
   ada@example.com
   ada@example.com, Ada Lovelace
   Lovelace Ada, ada@example.com
   Grace Hopper <grace@example.com>
   ```

   Or paste a CSV whose first line is a header containing `email` (or
   `e-mail`). A `name` column fills the name; other columns are stored with the
   contact as attributes.
3. Check the consent box: "These people agreed to be contacted about this
   survey, or have an existing relationship with us. Every email carries an
   unsubscribe link; bounces and spam complaints pause mailings. Contact lists
   are processed on your behalf as described in the Privacy Policy."
4. Click **Import** (disabled until the box is checked — tooltip "Confirm
   consent first").

A toast reports the result: **12 contacts added, 3 updated, 1 skipped**.

| Rule | Detail |
|---|---|
| Addresses | lower-cased; lines without a valid address are skipped |
| Duplicates in one paste | the first occurrence wins; the rest are skipped |
| Known addresses | updated, not duplicated: a new name replaces the old one, attributes are merged |
| Unsubscribed, bounced or complained contacts | stay suppressed after a re-import |
| Size | up to **20,000** lines per import (the rest are skipped); up to 2 million characters of text |
| Consent | required; your confirmation is recorded in the project's activity log |

> **Note.** CSV attributes are stored but cannot be used in the message: only
> the four placeholders below are filled in. There is no screen that lists,
> edits or deletes contacts in the beta — the panel shows only the counts.

---

## Sending a mailing

**New mailing** needs at least one subscribed contact and a **live**
environment (a paused environment does not count).

| Field | Default | Notes |
|---|---|---|
| **Survey environment** | `main` if live, else another live environment | shown as `main · <link>`; the personal links point here |
| **Subject** | `<project name>: your personal link` | one line, up to 200 characters |
| **Message** | the invitation template below | plain text, up to 20,000 characters; hint "{name} {email} {link} {unsubscribe}" |
| **From name** | your organization's name | hint "the address stays the platform's"; up to 120 characters |
| **Reply-to** | your email address | where replies land; up to 200 characters |

The default invitation text:

```
Hi {name},

We are running a short survey and would value your answers. It takes a few
minutes and this link is personal to you:
{link}

Thank you!
```

### Placeholders

| Placeholder | Becomes |
|---|---|
| `{name}` | the contact's name — **empty** if you imported only an address |
| `{email}` | the contact's address |
| `{link}` | the contact's **personal link** — **required**; without it the dialog shows "The message must contain {link}" and cannot send |
| `{unsubscribe}` | the contact's unsubscribe link |

Any other `{…}` is sent as written. If the message has no `{unsubscribe}`,
Studio appends one at the end:

```
—
To stop receiving these emails: <unsubscribe link>
```

### Preview and send

The right-hand **Preview · as `<first contact's email>`** renders the subject
and text as your first contact will receive them (the personal token shows as
`TOKEN`). It updates as you type. Underneath: "Goes to N subscribed contacts.
Every email ends with an unsubscribe link."

Click **Send to N**. The mailing is queued and sent in the background in
batches; the toast says **Sending to N contacts…**, and the table row shows
**queued…** and **sending…** in the **Sent** column until it is done (the
panel refreshes every few seconds while a mailing is in flight). The number on
the button is an estimate; contacts who bounced or complained earlier are
skipped when the mailing is made.

A personal link is your survey link plus `?inv=<token>`. The token comes back
with the response, which is how Studio knows who started and who finished — no
change to the questionnaire is needed.

---

## Tracking

The table has one row per mailing:

| Column | Meaning |
|---|---|
| **Kind** | `invite` or `reminder` |
| **Mailing** | subject, environment and send time |
| **Sent** | emails that left (including those that then started or completed), plus **· N failed** |
| **Started** | invitees whose interview has saved progress but who have not submitted yet |
| **Completed** | invitees who submitted, with the completion rate (completed ÷ sent) |

**Recipients** expands the list of invitees (**Hide** collapses it): `Name
<email> · status`, with the reason on hover for failures.

| Status | Meaning |
|---|---|
| `queued` / `sending` | waiting in the send queue / being sent now |
| `sent` | the email was accepted for delivery |
| `failed` | it could not be sent, or it was skipped because the contact had unsubscribed, "complained earlier" or "bounced earlier" |
| `started` | the respondent began answering and their progress reached Studio (after answering something and moving on a page, or leaving the tab) — opening the link alone does not count |
| `completed` | the respondent submitted |
| `bounced` | the recipient's mail server rejected the email after it was sent |
| `complained` | the recipient marked it as spam |

A mailing whose emails all failed ends as `failed`.

> **Note.** A personal link is not single-use. Someone who forwards it, or
> opens it twice in different browsers, creates a separate response each time;
> the invitation is marked `completed` at the first submission.

---

## Reminders

On an **invite** row with more sent than completed, **Remind** (tooltip "Email
the invitees who have not completed") opens **Send a reminder**:

- **Subject** defaults to `Reminder: <original subject>`; the message to

  ```
  Hi {name},

  A quick reminder: our survey is still open and your answers matter. Your
  personal link:
  {link}

  Thank you!
  ```
- It goes to the invitees of that mailing who have **not completed** — minus
  anyone who has since unsubscribed, bounced or complained ("Goes to the N
  invitees of "…" who have not completed.").
- Every reminder email carries a **new** personal link. A respondent counts as
  completed on the mailing whose link they used: someone who finishes through
  the reminder's link shows as completed on the reminder row, not on the
  invitation row.

Reminders are sent by hand; there is no scheduling of mailings or automatic
reminders. A reminder row has no **Remind** button. A second **Remind** from
the invitation row again targets everyone who has not completed *through the
invitation's link* — which includes people who have since finished through
the first reminder. Send one reminder, not several.

---

## Unsubscribes, bounces and pauses

Every invitation email carries:

- an unsubscribe link in the text;
- one-click unsubscribe headers (`List-Unsubscribe`, `List-Unsubscribe-Post`),
  which Gmail and Yahoo require of bulk senders.

The unsubscribe page needs no login and works in one click: "Unsubscribed —
`<address>` has been unsubscribed from this study's emails. You will not
receive further invitations or reminders for it." Unsubscribing applies to
this project's contact list only.

Automatic protections:

- A **bounce** (other than a temporary one such as a full mailbox) suppresses
  the address: it receives no further mailings in this project.
- A **spam complaint** suppresses and unsubscribes the address.
- If a mailing crosses a threshold, it is **paused** — its remaining queued
  emails stay unsent — and **all mailings of your organization** are paused:

  | Threshold (per mailing, of the emails delivered so far) |
  |---|
  | at least 1 spam complaint and complaints ≥ 0.05 % |
  | at least 3 bounces and bounces ≥ 2 % |

  In practice a single complaint pauses a mailing of up to 2,000 recipients.
  While paused, a new mailing is refused with "mailings are paused for this
  organization (…) — contact support to resume", and the panel shows
  invitations as unavailable, with its buttons disabled. Support lifts the pause after a conversation; suppressed addresses
  stay suppressed.

This is strict on purpose: every organization sends from a shared domain, and
one bad list would damage deliverability for everybody.

---

## Sender identity

Emails come from Studio's sending address with your **From name** as the
display name (`"Brand Study Team" <…>`). If you leave **From name** empty, the
platform's own name is used. Replies go to **Reply-to**. Emails are plain text
— there is no HTML design.

---

## Allowances

| Plan | Per month | Per day | First mailing of the organization |
|---|---|---|---|
| Free | — | — | — |
| Trial (unpaid) | — | — | — |
| Plus | 1,000 | 300 | up to 200 recipients |
| Pro | 5,000 | 1,500 | up to 500 recipients |
| Corporate | no limit | no limit | no limit |

- Months and days are counted in **UTC**. Every invitation of a mailing counts
  when the mailing is created, reminders included.
- The first-mailing limit applies to your organization's very first mailing,
  in any project — the warm-up every new sender needs.
- A mailing that would exceed an allowance is refused as a whole, e.g. "this
  mailing would exceed the plus plan's 300 invitation emails per day (120 sent
  today, 250 to send) — send the rest tomorrow" or "an organization's first
  mailing is limited to 200 recipients (412 selected) — start with a smaller
  list, then send the rest".

---

## Who can do what

Any member of the organization (member, admin, owner) can import contacts,
send mailings and reminders. Imports and mailings are recorded in the
project's activity log.

---

## Good practice

- Import only lists you can justify: panel members, course participants,
  customers, prior study participants.
- Import names with the addresses, or write a greeting that works without one —
  `Hi {name},` becomes `Hi ,` for a contact without a name.
- Put the study name in the subject and the sponsor in the **From name**;
  anonymous invitations get reported as spam.
- Send the reminder **once**, three to five days later.
- Keep the message short and the link visible near the top.
- Check the preview on a phone-sized window before sending.
- Split a first list larger than your first-mailing limit: send the allowed
  number, then the rest in a second mailing.

## See also

- [[Publishing and Environments|Studio-Publishing-and-Environments]]
- [[Links, QR Codes, Embeds and Access Control|Studio-Distribution-Channels]]
- [[What Respondents See|Studio-Respondent-Experience]]
- [[Plans, Trial and Billing|Studio-Plans-and-Billing]]
- [[Security and Privacy|Studio-Security-and-Privacy]]
