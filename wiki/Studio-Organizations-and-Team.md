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

- it is named after you (for example "Jane Doe"; the first 120 characters of
  your name, on one line, if it is longer). You can rename it under
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

The **Create organization** dialog asks for the **Organization name**
(placeholder `Acme Research`), up to 120 characters; the field stops there and
says "120 characters at most". Under the name it shows the address the
organization will get: "Its address will be /acme-research — it cannot be
changed later." That address is the organization's slug, and Studio makes it
the way it makes a project's (see
[The project's slug](Studio-Projects#the-projects-slug)): letters from other
alphabets are spelled in Latin letters (`Réseau Santé` → `reseau-sante`), and
the slug is 3 to 40 characters. A name with nothing Studio can spell gives
`organization`. A slug shorter than 3 characters, or made of exactly 12 hex
digits (the shape of a survey id), gets `-org` added, and one that an
organization you belong to already has gets `-2`, `-3` and so on.

Click **Create** ("Creating…"). Studio switches to the new organization, opens
its **Projects** tab and confirms "Organization *name* created". You are the
owner of a **cooperative** organization on the **Free** plan. A new
organization created this way gets no trial: the Pro trial comes once per
email address, with the organization you got at sign-up. Organization slugs
are unique across Studio; if another organization already has the address, you
see "Could not create organization. Org slug already taken." Choose a
different name.

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
(**Personal** or **Cooperative**), your role (for example "Owner"), its plan
(for example "Pro plan") and, during a trial, **Pro trial · 27d left**, or
during a paid period that ends on a date (a 12-month beta offer), **Paid
period · 200d left**. When Plus or the Plus year was bought for after the
trial, a further pill names it: **Plus from Oct 3, 2026** or **Plus year from
Oct 3, 2026** (hover: "Bought during the trial; it starts when the trial
ends").
**Manage** opens **Organization settings**. **Create organization**, at the top right, opens
the dialog described in
[Creating another organization](#creating-another-organization).

For a **personal** organization the screen also has a **Create a team**
section, subtitled "upgrade to a cooperative organization":

> A **personal** organization is for solo projects. Upgrade to a
> **cooperative** to give it a team name and invite people. The subscription
> stays with you as the owner.

Optionally type a new **Organization name** ("how your team will see it", up
to 120 characters) and click **Create cooperative**. Only the owner can do
this; others see "Only the owner can do this." The organization becomes
cooperative and Studio opens its settings.

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

  Pending invitations are not canceled by the switch, and a personal
  organization no longer lists them, so someone could still join through an
  old link. Revoke them under **Settings → Members** before you switch.

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
| Save items to the organization **Library** *(Plus)*; delete the items you saved yourself | ✓ | ✓ | ✓ |
| Delete (or, through the API, replace) a library item another member saved | ✓ | ✓ | — |
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

- **New project** is disabled for members, on the **Projects** tab, in the
  workspace chip menu and on the **Library** tab (on each template and on
  each questionnaire saved in the organization library). Hovering it says
  "Only owners and admins can create projects". An organization with no
  projects yet also shows "Only owners and admins can create projects — ask
  one to set it up." under its disabled buttons, and the **Library** tab shows
  the same line under its templates.
- On the **Library** tab, the **Delete** (trash) button is disabled on items
  another member saved. Hovering it says "Only owners and admins can delete an
  item another member saved", and a note under the table reads "Only owners
  and admins can delete items other members saved." Items you saved yourself
  can still be deleted.
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
- **Delete project** under **Project settings → Danger Zone** is disabled
  for members. Hovering it says "Only owners and admins can do this", and the
  Danger Zone adds "Only owners and admins can delete a project."

---

## Inviting people

Owners and admins invite from **Settings → Members** (or **Team** → **Manage
members**).

1. Click **Invite member**.
2. In the **Invite member** dialog, enter the **Email** (placeholder
   `colleague@example.com`). A malformed address shows "Enter a valid email
   address".
3. Choose the **Role**: `Admin` or `Member` (default `Member`). You cannot
   invite a second owner.
4. Click **Send invite** ("Sending…").

What happens next depends on the address:

| The address… | Result | Notice |
|---|---|---|
| **already has a Studio account** and is not a member | they are **added to the organization immediately**, with that role. No email is sent. The organization appears in their workspace chip the next time they open or reload Studio. | "*email* added to the team as *role*" |
| **has no account yet** | a **pending invitation** is created and they get an email with a link, **valid for 7 days**. An account set up with that address, by email or with Google or Microsoft, joins your organization as it is set up, whether or not they used the link, and opens in the inviting organization rather than in their own new workspace. | "Invitation sent to *email*" |
| **has no account and a pending invitation**, expired or not | the invitation is **replaced** by a new one with the role you picked, and a new link is emailed. The old link stops working. | "New invitation sent to *email* — the earlier link no longer works" |
| **belongs to a member with another role** | their role changes to the one you picked, recorded as a role change (`member.role`), not as an invitation, as with the role dropdown. No email is sent. | "*email* is already on the team — role changed from *old role* to *new role*" |
| **belongs to a member with that role** | nothing changes, and nothing is recorded. | "*email* is already on the team as *role* — nothing changed" |
| **is the owner's** | nothing changes. | "Could not add member. Cannot change the owner's role." |

What the invitee sees is described in
[[Sign Up and Sign In|Studio-Sign-Up-and-Sign-In]].

Good to know:

- **Your own address.** The notice reads "You are already on the team as
  *role* — nothing changed" or "Your role changed from *old role* to *new
  role*". An admin who picks `Member` for their own address gives up the admin
  role at once, and the page changes to what members see: **Invite member**,
  the role dropdowns, **Remove** and the **Activity** tab disappear.
- **A full organization.** If your organization has no room left on its plan
  when the invitee's account is set up, the invitation stays pending; they
  can accept it from the link once you have upgraded or made room (see
  [Member limits](#member-limits)). Once there is room, you can also invite
  that address again: they are added directly, and the invitation leaves the
  pending list. Opened while they are signed in, its link still takes them
  into the organization; signed out, it reads "This invitation link is invalid
  or has already been used.", and they only need to sign in.

### Pending invitations

Under the member table, owners and admins see:

> Pending invitations — sent by email, waiting to be accepted. Re-inviting the
> same address re-issues the link.

| Email | Role | Invited by | Expires | |
|---|---|---|---|---|
| `new.person@example.com` | `Member · pending` | Jane Doe | Oct 7, 2026 | **Revoke** |

**Revoke** cancels an invitation at once, without a confirmation step. The
notice reads "Invitation to *email* revoked", and the link then shows "This
invitation link is invalid or has already been used." An invitation past its
expiry date stays in the list until you revoke it or re-invite the address;
for an address that has an account, adding the person also takes it off.
The list is loaded when you open the **Members** tab and again after you send
an invitation or change a role, so a new or replaced invitation shows at once,
and one that closed because you added the person disappears. An invitation
someone accepts from its link while you have the tab open stays listed until
the list loads again.

### Member limits

The owner counts toward the member limit: **Free 2**, **Plus 15**, **Pro and
Corporate unlimited** (see [[Plans, Trial and Billing|Studio-Plans-and-Billing]]).

- At the limit, **Invite member** is disabled ("Your plan allows 2 members —
  upgrade to add more") and a note reads "You've reached the **2-member**
  limit on the Free plan. **Upgrade your plan** to invite more." The link opens
  **Billing**.
- When you invite a new address, **pending invitations count too**:
  members plus unexpired pending invitations must stay within the limit. If
  they don't, you see "Could not add member. The Free plan allows up to 2
  members; upgrade to add more." Revoke unused invitations to make room.
  Inviting an address again while its invitation is pending replaces that
  invitation, so it is not counted twice.
- The limit is checked again when an invitee's account is set up (a full
  organization leaves the invitation pending) and when someone accepts. A
  full organization answers "Could not accept the invitation. The Free plan
  allows up to 2 members; upgrade to add more."
- After a downgrade, everyone who is already a member keeps access. You just
  cannot add more until the team fits the limit.

---

## Managing members

In **Settings → Members**, owners and admins see the member table:

| Member | Email | Role | Since | |
|---|---|---|---|---|
| (JD) Jane Doe | `jane@example.com` | `Owner` | Sep 1, 2026 | |
| (ML) Maria Lopez | `maria@example.com` | `Admin ▾` | Sep 3, 2026 | **Remove** |

- **Change a role** with the dropdown (`Admin` / `Member`). The change applies
  immediately ("Role updated to member"). An admin who demotes themselves sees
  the page as a member does straight away, without the role dropdowns,
  **Invite member**, **Remove** or the **Activity** tab. The owner's row always
  shows a pill instead of a dropdown.
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
| [Billing](#billing) | trial or paid-period status, plan cards, offers, billing portal |
| [Integrations](#integrations) | AI assistant, webhooks |
| [Activity](#activity) | the organization's audit log (owners and admins) |

### General

| Field | Notes |
|---|---|
| Avatar and type pill | the organization's colored square and its type |
| **Organization name** | editable by owners and admins, up to 120 characters: the field stops there and says "120 characters at most". An older name that is longer shows "Organization name must be 120 characters or fewer." and cannot be saved until you shorten it. |
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

**Custom CSS** is a Plus feature. On a plan without it (Free, including an
organization whose trial has ended), every copy of the house style leaves
its custom CSS out: at project creation, and in the Builder on **Create
questionnaire**, on **Use this draft** (a draft from a brief) and on **Use the
organization's house style**. A study then never carries CSS that its plan
would refuse to publish.

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

Over a limit, the setting shows a message under it, such as "Custom CSS is
longer than 64 KB. Shorten it to save the style." or "Primary is longer than
4 KB. Shorten it to save the style.", and **Save changes** stays unavailable
until you shorten it; your edits stay in the form. A line above **Save
changes** names every setting that is over, even in a section you have
folded: "Shorten Primary (4 KB at most) and Custom CSS (64 KB at most) to save
the style." Over the whole limit, the line adds "The survey style is larger
than 128 KB altogether. Shorten the custom CSS or the longer texts to save
it."

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

The trial or paid-period status, the plan cards, any beta offers and, once
card payments are live, **Manage billing**. Every member can open this tab.
Only the owner can change the plan; others see "Only the owner can change the
organization's plan." Details are in
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
**Delete**, which asks "Stop sending events to *URL*?". Two pills can appear
on a row:

- **unsigned**: the webhook was added without a secret. Hover: "Deliveries
  carry no X-Siamang-Signature header. Delete the webhook and add it again
  with a secret to sign them." A secret cannot be added afterward.
- **never fires: terminal** (or another name): the webhook subscribes to an
  event nothing sends. Hover: "Nothing emits terminal: this webhook never
  fires for it. Delete it and add it again with the events you want."

Webhooks added with an earlier version of this form subscribed to `deploy`,
`run` or `terminal`, which nothing sends. They have been converted: `deploy`
now reads `deploy.live`, `deploy.failed`, `deploy.stopped`, `run` reads
`run.completed`, `run.failed`, and those webhooks receive these events.
`terminal` was removed from them, except where it was the webhook's only
event: that webhook keeps it, still receives nothing, and shows the **never
fires** pill. Delete it and add it again (see
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
| Action | `member.invite`, `snapshot.save`, `deploy.live`, `data.export`, `response.delete` |
| Project | `brand-awareness`, or `—` for organization-level events |
| Target | what it acted on: an email, a Save, an environment, a table |
| Who | the person's name, or `—` for automatic events such as the end of a build or a run, a lapsed trial or a payment |
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

- **People:** invitations sent (`member.invite`), role changes
  (`member.role`: the target is the member's email, and the exported `meta`
  holds the new role and the one before), invitations revoked, people
  accepting an invitation on its page (`member.join`), removals
  (`member.remove`). An account that joins as it is set up (see
  [Inviting people](#inviting-people)) adds no `member.join` row; the
  `member.invite` row of its invitation is the record.
- **Accounts:** name changes (`profile.update`: the target is the new name,
  and the old one is in the exported `meta`), recorded in every organization
  the person belongs to. On an installation that signs people in itself
  rather than through the managed sign-in service, password sign-ins
  (`auth.login`) and password changes (`auth.password_change`) are recorded
  the same way, with the person's email as the target. A failed sign-in is
  never recorded.
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
  (`billing.subscription.stale`), and a trial or a paid period lapsing to
  Free (`org.plan_lapsed`).
- **Projects:** created, renamed, deleted.
- **Saves:** new Saves, restores, tags, and a Save that adds access codes
  (`access_codes.generate`: the target is the Save, the exported `meta` says
  how many codes were added, and the codes themselves are never recorded).
- **Publishing:** publishes and previews (`deploy.create`, `deploy.preview`)
  and how each build ended (`deploy.live`, `deploy.failed`,
  `deploy.preview_live`, `deploy.preview_failed`, with `—` as the person; a
  build Studio marked failed because it stopped responding has
  `"reason": "timed out"` in the exported `meta`), pause, resume, close
  (`deploy.stop`), reopen, history reset, a closing date set, removed or
  handed back to the Save on the Distribute card (`deploy.closing_date`), and
  **One response per browser** switched on or off
  (`deploy.one_response_per_browser`: the target is `<project>:<environment>`).
- **Analysis:** flow runs started with **Run** or **Run all** (`run.start`;
  a schedule's **Run now** is recorded as `schedule.run` instead) and how
  those runs and scheduled runs ended (`run.completed`, `run.failed`, with `—`
  as the person), run history reset, schedules created, changed, removed or
  started with **Run now** (`schedule.create`, `schedule.update`,
  `schedule.delete`, `schedule.run`), connector runs (`connector.run`) and how
  they ended (`connector.completed`, `connector.failed`). Live recomputes are
  not recorded; a click on **Recompute now** is (`live.recompute`), not the
  runs it starts.
- **Data and sharing:** response deletions, downloads from **Data → Export**
  (`data.export`: the target is the table, and the exported `meta` holds the
  format and the number of rows), panel outcome CSVs from Distribute
  (`outcomes.export`: the target is `<project>:<environment>`, and the `meta`
  holds the outcome and the id parameter), bundle downloads and deposits,
  Live share links created and revoked, notable console commands. The data
  itself is never recorded.
- **Email invitations:** contact imports, contact deletions (`contacts.delete`:
  the target is the contact's id, or `N deleted` when all of a project's
  contacts go, never the address), mailings created or paused, bounces and
  spam complaints.
- **Secrets and library:** project secrets set or deleted; organization
  library items created, changed or deleted.

**Not recorded:** sign-ins and password changes that go through the managed
sign-in service (as on `studio.siamang.org`), and creating an organization.

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
