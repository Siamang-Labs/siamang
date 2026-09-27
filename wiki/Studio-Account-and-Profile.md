# Account and Profile

Everything personal to you, as opposed to your organization, lives under the
avatar in the top-right corner: your name, your password, how the app looks in
this browser, and your personal API keys. This page also explains the parts of
the topbar that are always on screen and the banners that can appear under it.

---

## The topbar

The topbar is the same on every screen:

```
 Siamang Studio  Beta   [AR  Brand Awareness Study ▾]  ● valid #17        Pro trial · 27d   (JD)
 └ wordmark ┘ └stage┘   └──── workspace chip ───────┘  └ Save badge ┘     └ trial pill ┘  └avatar┘
```

| Element | What it is |
|---|---|
| Wordmark and **Beta** | the product name. The **Beta** label says Studio is in open beta. |
| **Workspace chip** | the colored square with your organization's initials, followed by the name of the **project** you are in, or the **organization** name when you are not in a project. Click it to switch organization or project. |
| **Save badge** | shown only inside a project: the project's current Save and its validation state, e.g. `● valid #17`, `● warnings #17`, `● errors #17`, `checking #17`, `unsaved`, `saving…`. Click it to open that Save in **History**. See [[Key Concepts\|Studio-Key-Concepts]]. |
| **Trial pill** | `Pro trial · 27d`: the days left on your organization's Pro trial. Hover for "Pro trial — 27 days left". During a paid period that ends on a date, such as a 12-month beta offer, the pill names the plan instead, for example `Plus · 200d` (hover: "Paid period — 200 days left"), and reads `Paid period ended` in the short time between its end and the switch to Free. Absent when the organization's plan has no end date. See [[Plans, Trial and Billing\|Studio-Plans-and-Billing]]. |
| **Avatar** | a colored circle with your initials. Hover shows your name. Click it for the avatar menu. |

Below the topbar are the **tabs**: the organization's (**Projects**, **Team**,
**Library**, **Settings**) or, inside a project, the project's. On narrower
windows, project tabs that don't fit move into a **More** menu.

### The workspace chip menu

The chip opens a two-column menu:

```
 ORGANIZATIONS                          PROJECTS
 [AR] Acme Research   27d  owner  ✓     ● Brand Awareness Study   ✓
 [LB] Lab of Behavior      member       ● Employee Pulse Q3
 ─────────────────────                  ● Course Evaluation
 Manage organizations                   ───────────────────
 Create organization                    All projects
                                        New project
```

- **Organizations** lists every organization you belong to. Each row shows a
  role pill (`owner`, `admin`, `member`), a days-left pill (e.g. `27d`) when
  that organization's trial or paid period runs to a date (hover: "Pro trial —
  27 days left" or "Paid period — 27 days left"), and a ✓ on the current one.
  Click another organization to switch to it. You land on its **Projects**
  tab.
- **Manage organizations** opens the **Organizations** screen (see
  [[Organizations and Team|Studio-Organizations-and-Team]]).
- **Create organization** opens the **Create organization** dialog. It is
  there however many organizations you already belong to; see
  [Creating another organization](Studio-Organizations-and-Team#creating-another-organization).
- **Projects** lists up to ten projects of the current organization with a
  status dot, and a ✓ on the one you are in. Clicking one opens it. If you were
  already inside a project, the other project opens on the same tab (for
  example **Data**); otherwise it opens in the **Builder**.
- **All projects** goes to the organization's **Projects** tab. **New
  project** opens the **New project** dialog (see [[Projects|Studio-Projects]]).
  It is disabled when the organization has reached its plan's project limit
  (on Free, hovering it says "Your plan allows 2 projects — upgrade to add
  more") and for members ("Only owners and admins can create projects").

Press `Esc` or click outside to close the menu.

---

## The avatar menu

| Item | What it does |
|---|---|
| *your name* | shown for reference (not clickable) |
| *your email* | shown for reference |
| *organization* | the organization you are in, with its colored square |
| **Profile** | opens **Profile settings** (below) |
| **Organizations** | opens the **Organizations** screen |
| **Dark theme** / **Light theme** | switches the theme; the label names the theme you will switch *to* |
| **Compact density** / **Comfortable density** | switches between the default spacing and a denser layout that fits more rows on screen |
| **Documentation** | opens this wiki in a new tab |
| **Sign out** | signs you out of this browser |

Theme and density are **preferences of this browser**, not of your account.
They are remembered on this computer and do not follow you to another one.
Everything Studio keeps in your browser — its one cookie included — is listed
under [Cookies and browser storage](Studio-Security-and-Privacy#cookies-and-browser-storage).

---

## Banners under the topbar

Two banners can appear across the top of every screen of an organization.

**Trial or paid period ending.** Shown in the last three days of a Pro trial:

> **Pro trial ends in 3 days.** After the trial, Free plan limits apply. Your
> data is preserved and stays exportable. Choose a paid plan in Settings →
> Billing to keep using paid features.

The first sentence counts down ("Pro trial ends in 1 day.") and reads **Your
Pro trial has ended.** right after the trial lapses. Studio moves the
organization to Free within half an hour after that, and the banner goes
away.

A paid period that ends on a date, such as a 12-month beta offer, gets the
same banner in its own words:

> **Your paid Plus period ends in 3 days.** Afterward, Free plan limits apply.
> Your data is preserved and stays exportable. Renew in Settings → Billing to
> keep using paid features.

Once it is over, the first sentence reads **Your paid period has ended.** See
[[Plans, Trial and Billing|Studio-Plans-and-Billing]].

**Frozen workspace.** Shown only if Siamang has frozen the organization, which
is a manual action by support and does not happen when a trial ends:

> **This workspace is frozen and read-only.** All your data is preserved: you
> can keep viewing and exporting everything (Data → Export). Editing, deploys,
> flows and response collection are unavailable. Contact support to resolve
> the freeze.

---

## Profile settings

Open **Profile** from the avatar menu. The page is titled **Profile settings**,
shows your email under the title, and starts with a reminder: "Personal
settings — your account, appearance and developer credentials. These apply to
you across every organization."

It has five tabs: **Account**, **Security**, **Appearance**, **API keys**,
**Support**.

### Account

| Field | Notes |
|---|---|
| Avatar | "Your avatar is generated from your initials." There is no picture upload. |
| **Name** | how colleagues see you: presence avatars, Save authors, comments, the member list and the Activity log. Up to 200 characters. |
| **Email** | marked "read-only". It is your identity: invitations, notices and the one-trial-per-address rule all key on it. To change it, write to `info@siamang-team.org`. |

Edit the name and click **Save changes**. The button is active only when the
name has changed and is not empty. A "Profile updated" notice confirms it.
The change is recorded in the Activity log of every organization you belong
to, as `profile.update`, with the new name as the target and the old one in
the exported `meta`.

### Security

This tab changes the password you use with **Continue with Email**.

> Set a new password for your account. Your current session stays active.

1. Type the new password in **New password**. The checklist below it checks off
   the rules: **At least 8 characters**, **A lowercase letter**, **An uppercase
   letter**, **A number**, **A symbol (e.g. ! ? @ #)**.
2. Type it again in **Confirm new password**. If the two differ, the field says
   "Passwords don't match".
3. Click **Update password** ("Updating…"). A "Password updated" notice
   confirms it, and you stay signed in.

Studio does not ask for your current password here: you are already signed in.
Sign out when you leave a shared computer. The new password goes straight to
the managed sign-in service, so the change does not appear in any
organization's Activity log.

**If you sign in with Google or Microsoft**, the same form **sets** a password
on your account. From then on you can also sign in with **Continue with
Email** and that password. Your Google or Microsoft sign-in keeps working.

If the change fails, the notice starts with "Could not change your password."
and gives the reason.

### Appearance

**Theme**: **Dark** or **Light**, "applies across the app". Until you choose,
Studio follows your operating system's light or dark setting. Your choice is
remembered in this browser, and the sign-in page uses it too (it also has its
own theme button in the corner).

The **Dark theme** / **Light theme** item in the avatar menu does the same
thing in one click. Density is only in the avatar menu.

### API keys

Personal tokens that let scripts and CI jobs call the Studio API as you.

> Personal tokens for programmatic access (CI, scripts). Send as
> `Authorization: Bearer sck_…`. Shown once on creation.

**Create a key**

1. Type a name you will recognize later in **Key name (e.g. ci-pipeline)**, for
   example `laptop` or `nightly-export` (up to 80 characters).
2. Click **Create key** (or press `Enter`).
3. A box appears: "New key — copy it now, it won't be shown again:" with the
   full token (`sck_…`). Click **Copy**.
4. Store it somewhere safe, such as your CI system's secret store. Only a hash
   of the token is kept. Nobody, including support, can show it to you again.
   If you lose it, create a new key and revoke the old one. The box disappears
   when you leave the tab.

**Use a key.** Send it as a bearer token: `Authorization: Bearer sck_…`. See
[[API and API Keys|Studio-API-and-API-Keys]].

**The list.** Every key you created appears, newest first, with:

- its name, and a **revoked** pill if it was revoked;
- the first characters of the token (`sck_ab12cd34…`) so you can match it to
  where it is used;
- when it was last used ("used Sep 21, 2026") or **never used**.

While the list loads you see placeholder rows. If loading fails, the message
starts with "Could not load your API keys." and a **Retry** button appears.
With no keys the tab says "No API keys yet."

**Revoke a key.** Click **Revoke** on its row. The dialog **Revoke API key**
asks: "Revoke "*name*" (*sck_…*…)? Any tool using it will stop working." Click
**Revoke**. The key stops working at once and stays in the list marked
**revoked**.

What to know about keys:

- A key acts **as you**, with your role, in **every organization** you belong
  to. Treat it like your password.
- Keys created here **do not expire**. Revoke keys you no longer use.
- When you leave an organization, your keys lose access to it along with you.
  Revoke keys you created for a team's automation when you hand it over.
- Creating and revoking a key is recorded in the Activity log of every
  organization you belong to (`api_key.create`, `api_key.revoke`), under your
  name. The entry names the key by its first characters (`sck_ab12cd34`), the
  same way this list does; the full token is never recorded. Owners and admins
  of those organizations can see these entries.

### Support

Four tiles:

| Tile | Buttons |
|---|---|
| **Contact team**: "Get help with your account, repositories, organizations, billing, or technical issues." | **Contact team** opens an email to `info@siamang-team.org` |
| **Documentation**: "Read guides and references for using Siamang Studio." | **API**, **Examples**, **Wiki**: the engine's documentation, examples and this wiki on GitHub |
| **Report bugs and request features** | **Report issue** (the issue tracker), **Request feature** (discussions) |
| **Legal**: "Read the terms of use and how Siamang Studio handles your data." | **Terms of Use**, **Privacy Policy** |

---

## What Studio knows about you

- Your **name**, **email**, and which organizations you belong to with which
  role. Passwords and Google or Microsoft sign-ins are handled by a managed
  authentication service; Studio's own servers never receive your password.
- **Your actions inside an organization**, recorded in its Activity log under
  your name: Saves, publishing, data exports, deletions, member changes and so
  on. Changes to your name and the creation and revocation of your API keys
  are account events: they appear in every organization you belong to.
  Sign-ins and password changes go through the managed sign-in service and
  are not recorded there. See
  [Activity](Studio-Organizations-and-Team#activity).
- **Personal drafts**: your unsaved Builder and Flows edits, stored per person
  so a colleague taking over a document cannot lose them.
- **Your API keys**: name, first characters, creation and last-use time. The
  token itself is stored only as a hash.
- If you turned the AI assistant on for an organization, the record that you
  did and when.
- A record of the platform emails sent to you: invitations, trial,
  paid-period and billing notices.

Respondent data is a separate matter; see
[[Security and Privacy|Studio-Security-and-Privacy]].

---

## Leaving an organization or deleting your account

- **Leave an organization.** There is no "leave" button. Ask an owner or admin
  to remove you under **Settings → Members** of that organization. Admins can
  remove themselves the same way. An owner cannot leave or be removed from
  their own organization.
- **Delete your account.** Not self-service in the beta. Write to
  `info@siamang-team.org` from the address you signed up with.
- **Delete a project.** Self-service for owners and admins, and permanent;
  members see **Delete project** disabled. See
  [[Project Settings|Studio-Project-Settings]].

## See also

- [[Sign Up and Sign In|Studio-Sign-Up-and-Sign-In]]
- [[Organizations and Team|Studio-Organizations-and-Team]]
- [[API and API Keys|Studio-API-and-API-Keys]]
- [[Security and Privacy|Studio-Security-and-Privacy]]

<!-- studio-nav -->
---

← [[Sign Up and Sign In|Studio-Sign-Up-and-Sign-In]] · [Studio contents](Studio-Overview#all-pages) · [[Organizations and Team|Studio-Organizations-and-Team]] →
