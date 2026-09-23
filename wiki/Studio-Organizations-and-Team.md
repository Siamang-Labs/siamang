# Organizations and Team

An **organization** is a workspace. It owns projects, members, the plan and
the bill, and everything in Studio happens inside one. This page covers your
organizations, the three roles and what each may do, inviting and managing
people, the **Team** tab, and every tab of **Organization settings**,
including the Activity log.

---

## Your organizations

When you sign up you get an organization of your own, and you are its
**owner**:

- it is named after you (for example "Jane Doe"). You can rename it under
  [General](#general).
- its address (slug) is derived from that name with `-org` added, for example
  `jane-doe-org`. The slug appears in every URL
  (`studio.siamang.org/jane-doe-org/projects`) and never changes.
- it is a **cooperative** organization, so you can invite colleagues right
  away.
- it starts on a **30-day Pro trial** (see
  [[Plans, Trial and Billing|Studio-Plans-and-Billing]]).

You can belong to any number of organizations: your own, every one you are
invited to, and any you create. Plans, limits, members and projects are
**separate per organization**.

**Switch organizations** with the **workspace chip** in the topbar. Its left
column lists your organizations with your role in each; click one to switch.
You land on its **Projects** tab. See
[The workspace chip menu](Studio-Account-and-Profile#the-workspace-chip-menu).

### Creating another organization

You can create as many organizations as you need, for example a separate
workspace for a client or a grant. **Create organization** is offered in two
places, however many organizations you already belong to:

- the **workspace chip** menu in the topbar, under **Manage organizations**;
- the top of the [Organizations screen](#the-organizations-screen).

An account that belongs to **no organization at all** sees this screen
instead of the app. Because every new account gets its own organization, most
people never see it:

> **No organization yet**
> Your account isn't a member of any organization. Create one to get started,
> or ask an admin to invite you.
>
> [ **Create organization** ]  [ **Sign out** ]

The **Create organization** dialog asks for:

- **Organization name** (placeholder `Acme Research`);
- **Slug**: generated from the name ("auto-generated"), shown read-only and
  fixed forever. It must come out between 3 and 40 characters (letters, digits
  and hyphens), so keep the name short.

Click **Create** ("Creating…"). Studio switches to the new organization, opens
its **Projects** tab and confirms "Organization *name* created". You are the
owner of a **cooperative** organization on the **Free** plan. A new
organization created this way gets no trial: the Pro trial comes once per
email address, with the organization you got at sign-up. Organization slugs
are unique across Studio; if the name is taken you see "Could not create
organization. Org slug already taken."

Organizations cannot be deleted from the app in the beta. Write to
`info@siamang-team.org`.

---

## The Organizations screen

Open it from the avatar menu → **Organizations**, or from the workspace chip →
**Manage organizations**. A note at the top says how many organizations you
belong to. With several, it reads: "You belong to **3 organizations**; this
page is about **Acme Research** — the workspace chip switches. Each owns its
own projects, members and subscription. Owners and admins manage it here."
With one, it reads "You belong to one organization. It owns your projects,
members and subscription. Owners and admins manage it here."

The screen shows the organization you are in: its name and pills for its type
(**personal** or **cooperative**), your role, its plan (for example "Pro
plan") and, during a trial, **Pro trial · 27d left**. **Manage** opens
**Organization settings**. **Create organization**, at the top right, opens
the dialog described in
[Creating another organization](#creating-another-organization).

For a **personal** organization the screen also has a **Create a team**
section, subtitled "upgrade to a cooperative organization":

> A **personal** organization is for solo projects. Upgrade to a
> **cooperative** to give it a team name and invite people. The subscription
> stays with you as the owner.

Optionally type a new **Organization name** ("how your team will see it") and
click **Create cooperative**. Only the owner can do this; others see "Only the
owner can do this." The organization becomes cooperative and Studio opens its
settings.

---

## Personal and cooperative organizations

| Type | What it is |
|---|---|
| **Personal** | a solo workspace. The **Members** tab shows "This is a personal organization" and there is no one to invite. |
| **Cooperative** | a team. The member table, invitations and roles are available. |

Organizations created at sign-up or with **Create organization** are already
cooperative. The type is set in
[General](#general) and **only the owner can change it**:

- **Personal → Cooperative** takes one click: pick **Cooperative**, or click
  **Upgrade to cooperative** on the **Members** tab. The notice reads
  "Upgraded to a cooperative organization".
- **Cooperative → Personal** removes people. Studio asks first:

  > **Switch to a personal organization?**
  > Everyone except the owner will be removed from this organization. This
  > can't be undone.
  >
  > [ **Cancel** ]  [ **Switch to personal** ]

  Every admin and member loses access immediately. Their past Saves and
  activity stay, attributed to them.

---

## Roles

Every member has one of three roles:

- **owner**: exactly one per organization, the person who created it. The
  owner's role cannot be changed, the owner cannot be removed, and ownership
  cannot be transferred in the app.
- **admin**: manages the team and the projects.
- **member**: does the research work.

The table shows what Studio **enforces**. Controls your role may not use are
disabled or hidden, usually with a note saying who can (see
[Things members may notice](#things-members-may-notice)).

| Action | owner | admin | member |
|---|:-:|:-:|:-:|
| **Organization** | | | |
| See the organization's projects, team and settings screens, including Billing | ✓ | ✓ | ✓ |
| Change the plan, buy, open the billing portal | ✓ | — | — |
| Switch between personal and cooperative | ✓ | — | — |
| Turn the AI assistant on or off | ✓ | — | — |
| Configure single sign-on (when available) | ✓ | — | — |
| Rename the organization; set its house style (**Branding**) | ✓ | ✓ | — |
| Invite members, change roles, remove members | ✓ | ✓ | — |
| See and revoke pending invitations | ✓ | ✓ | — |
| Read the organization's **Activity** log | ✓ | ✓ | — |
| See and manage webhooks | ✓ | ✓ | — |
| Save items to the organization **Library** *(Plus)*; delete library items | ✓ | ✓ | ✓ |
| **Projects** | | | |
| Create, rename and delete projects | ✓ | ✓ | — |
| Delete an individual response | ✓ | ✓ | — |
| Delete all contacts of a project | ✓ | ✓ | — |
| Add or delete project secrets; run a connector | ✓ | ✓ | — |
| Edit the questionnaire and flows; Save; restore or tag a Save | ✓ | ✓ | ✓ |
| Publish, pause, close, reopen and republish surveys | ✓ | ✓ | ✓ |
| Run flows, **Run all**, **Run to here**, schedules, Live share links | ✓ | ✓ | ✓ |
| Upload and delete files | ✓ | ✓ | ✓ |
| View and export data | ✓ | ✓ | ✓ |
| Import contacts and send email invitations | ✓ | ✓ | ✓ |
| Read a project's **Activity** (Project settings) | ✓ | ✓ | ✓ |

A person's role applies to **every project** of the organization. There are no
per-project roles.

### Things members may notice

- **New project** is disabled for members, on the **Projects** tab and in the
  workspace chip menu. Hovering it says "Only owners and admins can create
  projects". An organization with no projects yet also shows "Only owners and
  admins can create projects — ask one to set it up." under its disabled
  buttons.
- **Organization settings** has no **Activity** tab for members. Opening its
  address directly shows "Only owners and admins can see the organization's
  activity." Each project's own log stays readable under **Project settings →
  Activity**.
- On **Settings → Integrations**, the **Webhooks** card only says "Only owners
  and admins can see and manage the organization's webhooks."
- On the other organization tabs, **Invite member**, the role dropdowns and
  **Remove** are hidden, and **Save changes** is disabled with a note such as
  "Only owners and admins can edit the profile."
- In a project's **Data** tab, response rows have no **Delete** button.
- In **Project settings**, **Save changes** under the project name is disabled
  ("Only owners and admins can rename a project."), and so are **Add secret**
  and each secret's **Delete** ("Only owners and admins can add or delete
  secrets.").
- On a connector, **Run export** or **Run import** is disabled. Hovering it
  says "Only owners and admins can run a connector".
- **Delete project** under **Project settings → Danger Zone** is still shown
  to members, but deleting fails with "Could not delete project. You do not
  have permission to do this."

---

## Inviting people

Owners and admins invite from **Settings → Members** (or **Team** → **Manage
members**).

1. Click **Invite member**.
2. In the **Invite member** dialog, enter the **Email** (placeholder
   `colleague@example.com`). A malformed address shows "Enter a valid email
   address".
3. Choose the **Role**: `admin` or `member` (default `member`). You cannot
   invite a second owner.
4. Click **Send invite** ("Sending…").

What happens next depends on the address:

| The address… | Result | Notice |
|---|---|---|
| **already has a Studio account** | they are **added to the organization immediately**, with that role. No email is sent. The organization appears in their workspace chip the next time they open or reload Studio. | "*email* added to the team" |
| **has no account yet** | a **pending invitation** is created and they get an email with a link, **valid for 7 days**. Opening it and signing in (or signing up) with that address makes them a member. | "Invitation sent to *email*" |

What the invitee sees is described in
[[Sign Up and Sign In|Studio-Sign-Up-and-Sign-In]].

Good to know:

- **Inviting someone who is already a member** changes their role to the one
  you picked. Inviting the owner's address fails with "Could not add member.
  Cannot change the owner's role."
- **Re-inviting** an address with a pending invitation issues a new link, and
  the old one stops working.

### Pending invitations

Under the member table, owners and admins see:

> Pending invitations — sent by email, waiting to be accepted. Re-inviting the
> same address re-issues the link.

| Email | Role | Invited by | Expires | |
|---|---|---|---|---|
| `new.person@example.com` | `member · pending` | Jane Doe | Oct 7, 2026 | **Revoke** |

**Revoke** cancels an invitation at once, without a confirmation step. The
notice reads "Invitation to *email* revoked", and the link then shows "This
invitation link is invalid or has already been used." An invitation past its
expiry date stays in the list until you revoke it or re-invite the address.

### Member limits

The owner counts toward the member limit: **Free 2**, **Plus 15**, **Pro and
Corporate unlimited** (see [[Plans, Trial and Billing|Studio-Plans-and-Billing]]).

- At the limit, **Invite member** is disabled ("Your plan allows 2 members —
  upgrade to add more") and a note reads "You've reached the **2-member**
  limit on the free plan. **Upgrade your plan** to invite more." The link opens
  **Billing**.
- When you invite a new address, **pending invitations count too**:
  members plus unexpired pending invitations must stay within the limit. If
  they don't, you see "Could not add member. Plan 'free' allows up to 2
  members; upgrade to add more." Revoke unused invitations to make room.
- The limit is checked again when someone accepts. A full organization
  answers "Could not accept the invitation. Plan 'free' allows up to 2 members;
  upgrade to add more."
- After a downgrade, everyone who is already a member keeps access. You just
  cannot add more until the team fits the limit.

---

## Managing members

In **Settings → Members**, owners and admins see the member table:

| Member | Email | Role | Since | |
|---|---|---|---|---|
| (JD) Jane Doe | `jane@example.com` | `owner` | 9/1/2026 | |
| (ML) Maria Lopez | `maria@example.com` | `admin ▾` | 9/3/2026 | **Remove** |

- **Change a role** with the dropdown (`admin` / `member`). The change applies
  immediately ("Role updated to member"). The owner's row always shows a pill
  instead of a dropdown.
- **Remove** someone: Studio asks "Remove member" / "Remove *name* from the
  team? They will lose access to this organization's projects." Click
  **Remove**. They lose access to every project of the organization at once.
  Their Saves, comments and Activity entries stay, attributed to them. Admins
  can remove themselves this way.
- **Nobody can leave on their own.** Ask an owner or admin to remove you.

Members (non-admins) see the same table read-only, with roles as pills and no
**Remove** buttons.

---

## The Team tab

**Team** is a read-only roster of everyone in the organization: **Member**,
**Email**, **Role**, **Since**. A note explains: "Read-only roster — invites,
role changes and removals live in **Organization settings → Members** using
the “Manage members” button above." **Manage members** jumps there.

Pending invitations are not shown on **Team**; they are listed under
**Settings → Members** for owners and admins.

For a personal organization, **Team** shows "Personal organization" / "This is
a personal workspace. Upgrade to a cooperative organization to invite
teammates." with a **Create a team** button that opens the **Organizations**
screen.

---

## Organization settings

Open the organization's **Settings** tab (or **Manage** on the Organizations
screen). The page is titled **Organization settings** and notes that
"profile, members, billing and integrations apply to every project in
*organization*. The subscription covers the whole organization."

It has six tabs, each with its own address (`…/<org>/settings/members`,
`…/settings/billing` and so on). Members see five: **Activity** is shown only
to owners and admins.

| Tab | Contents |
|---|---|
| [General](#general) | name, type, slug |
| [Branding](#branding) | the house style new surveys start from |
| [Members](#members) | the member table, invitations, roles |
| [Billing](#billing) | trial status, plan cards, offers, billing portal |
| [Integrations](#integrations) | AI assistant, webhooks |
| [Activity](#activity) | the organization's audit log (owners and admins) |

### General

| Field | Notes |
|---|---|
| Avatar and type pill | the organization's colored square and its type |
| **Organization name** | editable by owners and admins |
| **Type** | **Personal** / **Cooperative**, hint "personal = solo · cooperative = invite a team". Only the owner can change it (see [Personal and cooperative organizations](#personal-and-cooperative-organizations)). |
| **Slug** | "read-only". It is the organization's address and never changes, even when you rename it. |

Click **Save changes** after renaming ("Organization updated"). Members see
"Only owners and admins can edit the profile."

### Branding

**The look every new study starts from**: the organization's **house style**
(colors, typeface, logo, privacy link and similar). It is copied into a
project's questionnaire **when the project is created**, and never read
again, so what a study looks like lives in the study and travels with its
downloaded code. Changing it does not touch existing projects. To apply it to
one, open the project and use **Theme → Use the organization's house style**.

Owners and admins edit it and click **Save changes** ("Survey style saved").
**Discard** throws away unsaved edits. **Clear** asks "Clear the house style?"
("New studies will start from the engine's defaults again. The studies you
already have keep their look.") before removing it. Members see "Only owners
and admins can set the house style."

Because the house style is copied into every new project, its size is
capped:

| What | Limit |
|---|---|
| **Custom CSS** | 64 KB |
| Any other text setting, such as the **Ethics statement** | 4 KB |
| The whole house style | 128 KB |

Over a limit, **Save changes** stores nothing and your edits stay in the form
so you can shorten them. The message names the setting, for example "Could
not save the survey style. custom_css is longer than 64 KB, which is more than
a house style can hold; shorten it." or "Could not save the survey style. The
house style is larger than 128 KB altogether, which is more than a house style
can hold; shorten it."

The individual settings are described in
[[Theme and Branding|Studio-Theme-and-Branding]].

### Members

The member table, **Invite member**, pending invitations and the member limit
note. See [Inviting people](#inviting-people) and
[Managing members](#managing-members). A personal organization shows "This is
a personal organization" / "Upgrade to a cooperative organization to invite
teammates and manage their roles and permissions." with an **Upgrade to
cooperative** button for the owner.

### Billing

Trial status, the plan cards, any beta offers and, once card payments are
live, **Manage billing**. Every member can open this tab. Only the owner can
change the plan; others see "Only the owner can change the organization's
plan." Details are in
[The Billing tab](Studio-Plans-and-Billing#the-billing-tab).

### Integrations

**AI assistant** *(Plus)*: the organization-wide switch for the Builder's AI
assistant.

- On Free the card reads "The assistant is a Plus feature" with **View plans**.
- The assistant is **off until the owner turns it on**, because turning it on
  is a consent decision:

  > By turning this on you agree that questionnaire and analysis text from this
  > organization may be sent to a third-party model provider, currently
  > **DeepSeek**, which processes it in China. What is sent, and what never is,
  > is set out in the Privacy Policy and the Terms of Use.

- The owner clicks **Turn the assistant on** ("The assistant is on for this
  organization"). The card then shows "On · turned on by *name* on *date*."
  and **Turn the assistant off**.
- Admins and members see the card with the buttons disabled and the note "Only
  the organization owner can make this decision, because it sends your team's
  work to a provider in another country."

See [[AI Assistant|Studio-AI-Assistant]] for what the assistant does and how
its allowance works.

**Webhooks** *(Plus)*: send deploy and run events to Slack or your own
endpoint. Owners and admins:

1. Enter an **Endpoint URL** (a public `http://` or `https://` address).
2. Optionally enter a **Secret** ("used to sign the request payload"), or
   click **Generate secret** for a random one. Copy it before you add the
   webhook: it signs every delivery and is never shown again.
3. Choose the **Events** to send: under **Deploys**, **live**, **failed** and
   **stopped**; under **Runs**, **completed** and **failed**. None selected
   means every event.
4. Click **Add webhook**.

Configured webhooks are listed with the events they receive, by their full
names such as `deploy.live` or `run.failed` ("all events" when none were
chosen; hovering an event pill in the form shows the same name), and
**Delete**, which asks "Stop sending events to *URL*?". A webhook whose row
lists `deploy`, `run` or `terminal` was added with an earlier version of this
form and receives nothing; delete it and add it again (see
[Add a webhook](Studio-Schedules-and-Webhooks#add-a-webhook)).
**Recent deliveries** shows each attempt with its status. Adding and deleting
webhooks is recorded in [Activity](#activity). On Free, owners and admins see
"Webhooks is a Plus feature". Members see only the note "Only owners and
admins can see and manage the organization's webhooks." See
[[Schedules and Webhooks|Studio-Schedules-and-Webhooks]].

**Single sign-on** (SAML / OIDC) for organizations is not available in the
beta. Its settings card appears only after the official release.

### Activity

The organization's **audit log**: who did what, in every project, newest
first.

> Actions across every project in this organization (deploys, runs, connector
> exports, console commands, invites, deletions) are recorded here.

**Only owners and admins can read the organization log.** Members don't see
the **Activity** tab; opening its address shows "Only owners and admins can see
the organization's activity." Every member can read the log of a single
project under **Project settings → Activity** (see
[[Project Settings|Studio-Project-Settings]]).

Each row shows:

| Column | Example |
|---|---|
| Action | `member.invite`, `snapshot.save`, `deploy.live`, `response.delete` |
| Project | `brand-awareness`, or `—` for organization-level events |
| Target | what it acted on: an email, a Save, an environment |
| Who | the person's name, or `—` for automatic events such as a lapsed trial or a payment |
| When | the date |

- **Range**: **24h**, **7d** (the default), **30d**, **All**. The window is
  measured back from the newest entry. If nothing falls in it you see "No
  activity in this period" / "Nothing was recorded in the selected range."
  with **Show all activity**.
- **Export CSV** downloads the rows currently shown as
  `<org-slug>-activity.csv`, with the columns `time`, `action`, `project`,
  `target`, `user`, `meta`.
- The tab shows the **latest 100** events of the organization.

**What is recorded**

- **People:** invitations sent (a role change also appears as
  `member.invite`), invitations revoked, people joining through an invitation
  (`member.join`), removals (`member.remove`).
- **The organization:** renames (`org.rename`: the target is the new name, and
  the old one is in the exported `meta`), type changes, house style changes,
  webhooks added or deleted (`webhook.create`, `webhook.delete`: the target is
  the endpoint URL, never its secret), single sign-on configuration, the AI
  assistant turned on or off and each assistant task it ran.
- **Personal API keys:** a key created or revoked (`api_key.create`,
  `api_key.revoke`). The row names the key by its first characters, for
  example `sck_ab12cd34`, never by the full token. A key works in every
  organization its owner belongs to, so the event appears in the Activity log
  of each of them.
- **Plan and billing:** plan changes, checkouts started and completed,
  cancellations, failed payments, a subscription found to have already ended
  at the payment provider when the owner buys again
  (`billing.subscription.stale`), and a trial lapsing to Free
  (`org.plan_lapsed`).
- **Projects:** created, renamed, deleted.
- **Saves:** new Saves, restores, tags, and a Save that adds access codes
  (`access_codes.generate`: the target is the Save, the exported `meta` says
  how many codes were added, and the codes themselves are never recorded).
- **Publishing:** a deployment going live, preview builds, failed builds,
  pause, resume, close (`deploy.stop`), reopen, history reset.
- **Analysis:** runs completed or failed, run history reset, schedules created,
  changed or triggered, connector runs.
- **Data and sharing:** response deletions, bundle downloads and deposits,
  Live share links created and revoked, notable console commands.
- **Email invitations:** contact imports, mailings created or paused,
  bounces and spam complaints.
- **Secrets and library:** project secrets set or deleted; organization
  library items created, changed or deleted.

**Not recorded:** sign-ins, profile and password changes, and creating an
organization.

Use the log to answer "who switched the live version on Tuesday?", and to show
when a contact list was imported with consent if a mailing is disputed.

## See also

- [[Account and Profile|Studio-Account-and-Profile]]
- [[Sign Up and Sign In|Studio-Sign-Up-and-Sign-In]]
- [[Plans, Trial and Billing|Studio-Plans-and-Billing]]
- [[Working Together|Studio-Collaboration]]
- [[Security and Privacy|Studio-Security-and-Privacy]]

<!-- studio-nav -->
---

← [[Account and Profile|Studio-Account-and-Profile]] · [Studio contents](Studio-Overview#all-pages) · [[Projects|Studio-Projects]] →
