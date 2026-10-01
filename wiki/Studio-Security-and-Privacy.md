# Security and Privacy

What Studio stores, who can reach it, what leaves the platform, and what to
tell your ethics committee or data-protection officer. Read this before a
study that collects personal or sensitive data.

---

## Where things live

| Thing | Where |
|---|---|
| The application | `studio.siamang.org` |
| The API (used by the app, your scripts and API keys) | `api.studio.siamang.org` |
| Published surveys | `study.siamang.org/<survey id>/`, a separate host that shares no cookies or session with the app |
| Sign-in | a managed authentication service (passwords and Google or Microsoft sign-ins are handled there, not by Studio's own servers) |
| Your responses | a database schema dedicated to your project |
| Uploaded files and run outputs | object storage, reachable only through signed links that expire |

**Survey links.** A published survey's address uses a random
**12-character survey id**, for example `https://study.siamang.org/3f9a1c07b2de/`.
The id is unguessable, and the link does not reveal your organization or
project name. It stays the same when you republish to the same environment.
An environment you publish for the first time now is reachable only there:
nobody can open it (a pilot, an invitation-only wave) by guessing your
organization's and project's names. An environment that was already published
before this change may still also answer at the earlier, guessable address
form (`study.siamang.org/<organization>/<project>/<environment>/`), whichever
link you handed out, and keeps doing so when you republish or close it,
because respondents may hold such links. Studio does not remove those
addresses.

**Isolation.** Every project has its **own database schema**. Every
organization's records are separated by row-level security, and every request
is scoped to the organization it belongs to. Flow runs connect to the database
with a role that can see only their own project.

---

## Who can see what

- **Only members of your organization** can open its projects, data and
  settings. For anyone else, a project or organization that exists gives the
  same "not found" as one that doesn't, so outsiders cannot even tell which
  names exist.
- **Roles** decide what a member can do: see
  [Roles](Studio-Organizations-and-Team#roles). For example, only owners and
  admins can delete a response or a project, delete library items other
  members saved, manage webhooks or read the organization-wide Activity log;
  members find those controls hidden or disabled.
- **Public by design, and only when you create them:**

| Public surface | What it shows | Lifetime |
|---|---|---|
| A published survey link, or the survey embedded in your site | the questionnaire, for respondents to answer | until you close or unpublish it, or until its closing date passes (the questionnaire's deadline, the environment's closing date, or a date set under **Distribute → Closing date**). After that the link shows "This survey is closed" as it opens (a survey published before this update shows it only when the respondent submits, until you republish it), and no response is accepted. |
| A **share preview** link | the respondent view of a draft, for reviewers. Answers given there are not stored. | 24 hours. Each person can create up to 50 per day. |
| A **Live share link** *(Plus)* | the Live tiles only: no raw rows, no questionnaire. Chart tiles are interactive and carry the numbers they draw; a chart that plots respondents' own answers (a scatter plot, a box plot with outliers or **Show points**) shows only its picture there | until revoked. Creating a new link revokes the previous one. It stops working if the organization drops below Plus. |
| The **unsubscribe** link in invitation emails | a page where the recipient opts out of further mailings | sent with every invitation email |
| A **team invitation** link | the inviter's name, the organization name, the role, a masked email address (`j***@example.com`) and the expiry date | 7 days, or until used, revoked, replaced by a newer invitation to the same address, or closed because the person was added to the organization directly. After that it shows no details; opened by the invited person while signed in, a used or closed link still takes them into the organization. |

Nothing else is public.

---

## Respondent data

- **What a response holds:** the answers (including anything a custom script
  writes) plus fieldwork metadata: when the interview started and how long it
  took, the last page reached, the captcha verdict when the captcha is on,
  three behavioral counts (tab switches, seconds the page was hidden, pastes),
  and any URL parameters that were in the link, such as a panel's respondent
  id or, for an email invitation, the personal invitation token (`url_inv`).
- **What a download carries.** **Data → Export** turns that metadata into
  columns: `duration_s`, `started_at`, `captcha`, `tab_switches`,
  `hidden_seconds`, `pastes`, and one `url_<name>` column per link parameter,
  panel ids and the invitation token included (the last page reached stays
  out). Exports downloaded before this update had none of these columns. A
  research bundle or a deposit **with data** keeps the timings, the captcha
  verdict and the counts, but only the link parameters a flow reads, and
  never the invitation token. See [[Data Exports|Studio-Data-Exports]] and
  [[Reproducibility: Code, Bundles and Citation|Studio-Reproducibility]].
- **Answers arrive before the respondent submits.** Each time the respondent
  moves to another page, and each time they leave the tab, the answers so far
  are sent to Studio as a **partial** response, so someone who stops halfway
  still leaves a row. The final submission replaces it.
- **IP addresses are not stored with responses.** They are used briefly to
  limit how fast one address can submit. On surveys where you switch on the
  **captcha**, the check loads from Cloudflare when the respondent submits —
  not before — so Cloudflare sees the IP address and browser of each
  respondent who sends their answers, and Studio sends Cloudflare the
  respondent's IP address with the captcha token so Cloudflare can verify it.
  The **Captcha** panel on the Distribute card says so and asks you to name
  Cloudflare Turnstile in your survey's privacy notice (see
  [Captcha](Studio-Distribution-Channels#captcha)).
- **The respondent id** is a random identifier the survey page keeps in the
  respondent's browser for one interview, once they start answering, so that
  its saved progress and the finished response land on the same row. It is
  dropped when the interview ends, and the next interview in that browser gets
  a new one. It is not an identity: Studio cannot tell whether two responses
  came from the same person.
- **One response per browser**, an option on the Distribute card (off by
  default), makes the survey page keep a mark in the respondent's own browser
  that the survey was answered there. Nothing about the browser is sent to
  Studio, so cleared browser data, a private window, another browser or
  another device can answer again. The mark stays on the respondent's device
  after they answer, until they clear their browser data — the survey's other
  browser data goes after a week, the mark does not — so mention it in your
  consent text. Unique invitation links are more reliable, especially for
  respondents in the EU, where keeping such a mark on a device needs the
  respondent's consent. A survey published before this option existed needs
  one republish of its environment for its page to honor it.
- **In the respondent's browser**, the survey keeps a draft of the answers
  given so far for up to a week, so that a reload or a later visit can resume
  the interview, and removes it once the interview is submitted or ends on a
  full quota. Until then, someone else opening the same link in that browser
  is offered to resume. Everything a survey keeps there, and for how long, is
  under [Cookies and browser storage](#cookies-and-browser-storage).
- **Personal data you ask for** (a name, an email, a phone number) is personal
  data you collected. Treat it accordingly, and say so on your consent page.
- **Email invitations** store the contact list you imported, each person's
  status (sent, started, completed), unsubscribes, and addresses suppressed
  after a bounce or a spam complaint. See
  [[Email Invitations|Studio-Email-Invitations]].

### Erasure requests

1. Find the response in **Data**. Type what identifies it in the filter (its
   response id, the `respondent_id`, a panel id from the survey link, or an
   answer such as an email address the person typed) and press `Enter` or
   click **Search all rows**. The search covers the whole table on the
   server, not only the newest rows loaded in the grid.
2. Delete it. Only owners and admins can; members don't see the **Delete**
   button on response rows.
3. The row is removed from the database, and the deletion is recorded in the
   Activity log (`response.delete`) **without** its content, which gives you
   the evidence. The response counts, and any quota cell the response filled,
   go down with it.

If the person was also on an email-invitation contact list, delete the
contact too. There is no screen for that in the beta, so it goes through the
API (see [[API and API Keys|Studio-API-and-API-Keys]]). The deletion is
recorded as `contacts.delete` by the contact's id, never by address.

Exports and research bundles downloaded **before** the deletion still contain
the row. Delete or re-create those copies as well. See
[[Responses and the Data Tab|Studio-Responses-and-Data]].

### Consent and ethics

**Builder → Theme** carries the fields an ethics committee usually asks for:
**Estimated minutes** (shown to respondents as "About N minutes" under the
first page's title; a survey published before this update shows it after one
republish), **Contact email**, **Privacy URL** and **Ethics statement**. Put your consent text on the first page with a required "I agree"
question, and route anyone who declines to the end of the survey (see
[[Logic and Branching|Studio-Logic-and-Branching]]). What the consent text
should say about the respondent's browser and the services a survey uses is
under [What to say in your consent text](#what-to-say-in-your-consent-text).

### Open answers and codeframes

What respondents write in open questions stays in Studio when you code it:

- **The codeframe editor** reads the answers from your project's own
  responses, on Studio's servers, and shows them only to members of the
  project. No model, provider or other service is involved.
- **A codeframe stores fingerprints, never answers.** The coding decisions
  in `analysis/<name>.codeframe.json` are keyed by a fingerprint of each
  answer (sixteen hexadecimal characters computed from its text), not by the
  text; the engine refuses a codeframe (version 2) that holds an answer's
  text.
- **A fingerprint is not anonymization.** It cannot be turned back into the
  text, but whoever holds the file and guesses an answer's exact words can
  confirm it was given. Words you type into rules and theme labels are stored
  as typed. A codeframe is in every Save and every research bundle, with or
  without data: share it as you would the study's other documents.
- **AI coding of open answers is switched off** on this platform (see
  [below](#the-ai-assistant-and-your-data)).

See [[Coding Open Answers|Studio-Open-Answer-Coding]].

### Interactive charts and your data

A report saved with **Interactive charts in HTML**, and every **chart** tile
on the Live tab and its public page, hold each chart's numbers as data that
anyone with the file or the page can read out — not only as a picture:

- **Most charts carry aggregates only**: what the chart draws — counts,
  percentages, means, intervals, histogram bins, a heatmap's cells, an
  analysis's estimates — computed in the run before the chart leaves it.
  Never a response, a respondent id or another answer.
- **Two charts plot respondents one by one**, and carry exactly what they
  plot: a **Scatter plot**'s points (each point's **X**, **Y** and **Color
  by** group) and a **Box plot**'s outliers and, with **Show points**, all
  its points (each value and its group). The points are listed in sorted
  order, not in the data's order, so a point's place in one chart does not
  match it to the same respondent in another chart.
- **Small groups show as they do in the picture.** A bar of a group of three
  respondents tells a reader about those three, whether they read it off the
  picture or out of the file.
- **The public Live page** shows a **Scatter plot**, or a **Box plot** with
  outliers or with **Show points**, as its picture only, so a public link
  never hands out respondents' values — an outlier is one respondent's
  answer, and in a small group it could point to a person. A **Box plot**
  with no outliers and without **Show points** stays interactive there.

Look at an interactive report's scatter plots and box plots before you send
it, and leave out a chart — or send the report without **Interactive charts
in HTML** — when those values should not travel. See
[Interactive charts](Studio-Reports#interactive-charts).

### Data files you upload

A data file you upload under [[Files|Studio-Files]] — a panel file, a
client's spreadsheet, a Qualtrics export — may hold personal data your own
survey never asked for.

- **Reading it keeps no answer.** Each data upload is read once it is stored,
  in the same isolated sandbox with no network access that flows run in, and
  Studio keeps only what describes it: its rows and columns, each column's
  name, label, type, scale and codes, and two hints. The file itself stays in
  object storage like any upload; a flow reads it only when it names it. See
  [What Studio reads from a data file](Studio-Files#what-studio-reads-from-a-data-file).
- **Personal-data hints are hints.** Files and the **Data file** node point
  out the columns whose names or values look like an e-mail or IP address, a
  location, a name, a phone number, an address or a participant ID — a
  Qualtrics export's `IPAddress`, `LocationLatitude` and `RecipientEmail`, a
  `PROLIFIC_PID`. Nothing is dropped for you, and the hints go by names (in
  English and Russian) and by the look of e-mail and IP addresses: a column
  of names called `q12`, or an open answer that holds a phone number, is not
  pointed out. Check the columns yourself.
- **Drop such columns early.** **Add a Select columns node without them**, in
  the node's [Columns panel](Studio-Node-Reference#the-columns-panel), puts a
  **Select columns** node right after the **Data file**, so no table,
  report, chart tile or export a flow makes downstream carries them. A
  research bundle **with data** still contains the upload as it is, so when
  the columns are not needed at all, delete the upload and upload a copy
  without them.

---

## Cookies and browser storage

What Studio and your surveys keep in the browser, and which other services a
browser talks to. Neither Studio nor a survey uses analytics, advertising or
tracking cookies or scripts.

### Studio's cookie and storage

Studio sets **one cookie**, `sc_auth`, on `studio.siamang.org`. Its value is
`1`: it says nothing about you, and only tells Studio's web server whether to
show you the app or the sign-in page — your sign-in itself is checked by the
API on every request. It lasts 7 days, renewed each time you open Studio, and
**Sign out** removes it. So does Studio itself when it finds no sign-in stored
in the browser (say, the browser's storage for Studio was cleared but not its
cookies): you then see the sign-in page. It is marked `Secure`, so the browser
sends it over HTTPS only, and `SameSite=Lax`.

Everything else is in the browser's storage for `studio.siamang.org` — local
storage, and for two entries (`sc_oauth_provider`, `sc_oauth_next`) the tab's
session storage — which the browser never sends anywhere on its own:

| Key | What it holds | How long |
|---|---|---|
| `sc_session` | your sign-in: the token the API checks, the token that renews it, your name, email and organizations | until you sign out |
| `sc_next` | the team invitation to return to once you have signed in | until you have signed in |
| `sc_oauth_provider` | which sign-in button, Google or Microsoft, started the trip to the provider's page, so the sign-in page knows which provider you came back from | until you come back from the provider; at most until the tab is closed |
| `sc_oauth_next` | the address you opened before signing in with Google or Microsoft, so it opens once you are back (the provider always returns you to the bare sign-in page) | until you have signed in; at most until the tab is closed |
| `ss_theme`, `ss_density` | the theme and density you picked (see [[Account and Profile\|Studio-Account-and-Profile]]) | until you clear the browser's data for Studio |
| `sc_last_opened` | when you last opened each project in this browser, for **Sort: Last opened** | the same |
| `siamang.builder.inspector`, `siamang.flows.node-inspector`, `siamang.flows.report-preview` | the panel widths you dragged | the same |
| `siamang.flows.palette-open`, `ui:insp:…`, `ui:theme:…`, `ui:report-theme:…` | the node groups and the Inspector and theme sections you keep open | the same |

### A survey's storage

A published survey sets **no cookies**. Its page keeps a few entries in the
browser's local storage for the survey host (`study.siamang.org`), each named
after the survey id (`<id>` below) — and **nothing until the respondent
starts**: their first answer, their first move to another page, **Resume** or
**Start over**, or the light/dark button, which keeps only that choice.
Someone who opens the link and leaves keeps nothing.

| Key | What it holds | How long |
|---|---|---|
| `siamang_answers_<id>` | the draft: the answers so far, the page reached and the path taken, and when they were saved — what **Resume** brings back | removed when the interview is submitted (a screen-out included) or ends on a full quota; otherwise 7 days |
| `siamang_respondent_<id>` | the interview's `respondent_id`, which ties its partial responses and its completion to one row | from the start until the interview ends; at most 7 days |
| `siamang_ended_<id>` | when an interview in this browser last ended, so nothing of it is sent again as a new one | 7 days |
| `siamang_theme_<id>` | light or dark, once the respondent presses the light/dark button | 7 days |
| `siamang_kept_<id>` | when the survey last wrote there — the clock for the 7 days | goes with the rest |
| `siamang_done_<id>` | only with [One response per browser](Studio-Distribution-Channels#one-response-per-browser) on: the date and time this browser sent its response, or ended on a screen-out or a full quota | **not** cleared after a week — it stays until the respondent clears their browser data |

**The week.** Everything but `siamang_done_<id>` goes once the survey has not
written there for 7 days — a week after the respondent's last answer. A
browser cannot delete anything on a timer, so the entries go the next time any
survey from the survey host opens in that browser, before anything reads them;
a draft older than 7 days is never offered back.

**Previews keep nothing.** The Builder's canvas preview, the Walkthrough and
share-preview links keep their state in memory: a reload starts over, and the
browser is left as it was. A staged preview from the Builder's **Preview**
button is a real build and keeps a draft as a live survey does. See
[[Testing Your Survey|Studio-Testing-Your-Survey]].

### Other services

| Service | When a browser talks to it | What it learns |
|---|---|---|
| **Supabase** (sign-in) | on the sign-in page and while you work: your browser signs in and renews its session with Supabase's authentication service; a Google or Microsoft sign-in passes through Supabase and the provider's own pages | your IP address, browser and sign-in details; the provider's pages keep their own cookies on their own sites |
| **Stripe** (payments) | only when an owner clicks **Continue to checkout** or **Manage billing**: the browser leaves Studio for Stripe's own pages | what you enter there; Stripe's cookies stay on Stripe's sites, and Studio's pages load nothing from Stripe |
| **Cloudflare Turnstile** (captcha) | in Studio, on the sign-up, password and **Reset your password** forms of the sign-in page — not on its first, email step; in a survey, only with the [captcha](Studio-Distribution-Channels#captcha) on, and only when the respondent submits | the IP address and browser; Studio sends Cloudflare the IP address with the token to verify it |
| Fonts | none: Studio's own fonts come with the app, and a survey's (Source Serif 4, Inter, Nunito) come from the survey host — for previews, from Studio's API. Nothing is requested from Google Fonts or any other font service | — |
| Whatever you link yourself | a **Logo URL**, a font or image your **Custom CSS** loads, a request a custom script makes | the site you name sees each respondent's IP address and browser: name it in your privacy notice |

### Why there is no cookie banner

Studio's cookie and its storage in the browser do only what you asked for —
keeping you signed in, bringing you back to an invitation or to the page you
opened before signing in — or remember a choice you made:
the theme, the density, panel widths, open sections. Nothing tracks you, and
nothing is shared with another site. Under the EU's ePrivacy rules, storage
that is strictly necessary for a service the user asked for, or that keeps a
choice the user made, needs no consent, so Studio shows no cookie banner.

A survey's draft, its `respondent_id` and the respondent's light/dark choice
are of the same kind: they let the respondent resume, and keep their own
preference. The exception is the **One per browser** mark: it serves you, not
the respondent. That is why it belongs in your consent text, and why unique
invitation links ([[Email Invitations|Studio-Email-Invitations]] *(Plus)*) are the
better tool for respondents in the EU, where keeping such a mark on a device
needs the respondent's consent. This is how Siamang reads the rules; your
data-protection officer decides for your study.

### What to say in your consent text

Tell respondents, in the survey's consent text or privacy notice:

- that the survey keeps their answers so far in their browser for up to a
  week, so they can resume — and that on a shared computer, the next person to
  open the link in that browser within the week is offered to resume an
  unfinished interview (**Start over** discards it);
- that their answers reach you page by page, as **partial** responses, even if
  they never submit;
- what is recorded besides the answers: when they started and how long they
  took, the last page reached, and three counts — how often they left the
  tab, for how long, and how many times they pasted;
- with **One per browser** on, that a mark stays in their browser after they
  answer, until they clear their browser data;
- with the captcha on, that Cloudflare Turnstile checks their browser when
  they submit and sees their IP address;
- anything the link carries that identifies them (an invitation, a panel id),
  and anything the survey loads from another site (a logo, fonts, scripts).

> **Note.** A survey keeps the runtime it was built with. One published before
> this update loads its fonts from Google Fonts and the captcha as the page
> opens, keeps the respondent id from the moment the page opens, and keeps a
> draft for 24 hours but everything else with no limit. Republish its
> environment (a Save with nothing changed will do) to get what this section
> describes; see [Republishing](Studio-Publishing-and-Environments#republishing).
> Previews are rendered fresh and need nothing.

---

## Code execution

- **Your generated code** (the questionnaire and your analysis flows) runs in
  an ephemeral, isolated sandbox with **no network access**, one CPU, memory
  and time ceilings set by your plan, and no way to change anything outside
  its own output folder.
- **Uploaded data files are read in the same sandbox**, as untrusted input:
  the engine works out their columns there, and only that description comes
  back (see [Data files you upload](#data-files-you-upload)).
- **Imported Python is never executed.** A `questionnaire.py` you import is
  read as text. Anything the reader cannot follow is reported with line
  numbers, not run.
- **Custom JavaScript** *(Plus)* runs only in the respondent's browser, inside
  the survey page and with the page's own access: it is not sandboxed from
  it. It never runs on Siamang's servers. What a script writes to the answers
  is submitted with the response (keys starting with `__` excepted), so it
  reaches your data like any answer, and a script can also call other web
  addresses from the respondent's browser. Review scripts you did not write
  before you publish.
- **Reports are shown, not run** — except a report saved with **Interactive
  charts in HTML**, whose charts need the chart libraries it carries. On the
  **Reports** screen that report runs in a frame of its own whose origin is
  no one's: its scripts cannot read your session, Studio's pages or storage,
  call Studio's API, fetch anything, open windows, submit forms or start
  downloads. Studio frames a report so only when it carries the engine's
  chart libraries and interactive charts; any other HTML, a `<script>`
  written into a report's text included, runs no scripts at all.
- **Live chart tiles** are drawn by Studio's own code from the chart's data
  alone: nothing in a chart can make your browser — or a public viewer's —
  fetch anything, and the chart libraries are served by Studio, never by a
  third party.

---

## Secrets

Project secrets (connector credentials, tokens) are **encrypted at rest** and
**write-only**: once saved, nobody can read them back through Studio, you
included. Only their names are listed. Connectors and repository deposits read
them by name; analysis flow runs never receive them. To rotate a secret,
overwrite it; to revoke it, delete it. Only owners and admins can set or delete
secrets (members see **Add secret** disabled), and both actions are recorded in
the Activity log. See [[Project Settings|Studio-Project-Settings]].

**Webhook secrets.** A webhook's signing **Secret**, set when an owner or admin
adds the webhook under **Settings → Integrations**, is stored encrypted and is
never shown again. Each delivery then carries an `X-Siamang-Signature` header
(`sha256=` followed by an HMAC-SHA256 of the request body), so your endpoint
can check that the request came from Studio. A webhook added without a secret
is sent unsigned, and its row in the list carries an **unsigned** pill. A
secret cannot be added later: delete the webhook and add it again with one.
See [Integrations](Studio-Organizations-and-Team#integrations).

## API keys

Personal API keys (`sck_…`) are stored **only as a hash** and shown **once**,
when you create them. A key acts as you, with your role, in every organization
you belong to. Keys created in the app **do not expire**, so revoke the ones
you no longer use. Creating and revoking a key is recorded in the Activity log
of every organization its owner belongs to, with the key's first characters
and never the full token. See [[Account and Profile|Studio-Account-and-Profile]]
and [[API and API Keys|Studio-API-and-API-Keys]].

---

## The AI assistant and your data

The Builder's AI assistant *(Plus)* sends your questionnaire and analysis text
to a third-party language-model provider, so turning it on is an explicit
decision:

- **It is off by default** in every organization.
- **Only the owner can turn it on**, under **Settings → Integrations**. The
  switch states the terms: "By turning this on you agree that questionnaire and
  analysis text from this organization may be sent to a third-party model
  provider, currently **DeepSeek**, which processes it in China. What is sent,
  and what never is, is set out in the Privacy Policy and the Terms of Use."
- **The consent is recorded.** The card shows who turned it on and when ("On ·
  turned on by *name* on *date*."), and the Activity log records `ai.enable`
  and `ai.disable`, as well as each assistant task.
- **What is sent** is the text you ask it to work on: questionnaire wording,
  analysis descriptions, a brief you write. **Nothing a respondent wrote is
  sent.** AI coding of open answers — the one feature that sent the text of
  respondents' answers — is **switched off** on this platform: its buttons
  are gone, the API refuses a coding request ("AI coding of open answers is
  switched off on this platform."), and a coding job queued earlier ends
  without reading an answer. Open answers are coded by hand and by rules in
  the codeframe editor, which calls no model.
- **The owner can turn it off** at any time with **Turn the assistant off**.

If your ethics approval or data agreement does not allow processing in China,
leave the assistant off. See [[AI Assistant|Studio-AI-Assistant]] and the
[Privacy Policy](https://siamang.org/privacy-policy).

---

## Audit trail

Each organization keeps an append-only **Activity** log: Saves, restores,
publishing and how each build ended, pausing and closing, closing dates and the
**One response per browser** switch, runs and how they ended, schedules,
response deletions, bundle downloads, Live share
links, contact imports and deletions (by contact id, never the address),
mailings (including bounces and spam complaints), member changes including
role changes, name changes, secret changes, plan and billing events, the AI
assistant switch, organization renames, webhooks added or deleted (with the
endpoint, never the signing secret), personal API keys created or revoked (by
their first characters, never the token), and Saves that add access codes
(the count, never the codes). Data leaving the platform is recorded too:
every download from **Data → Export** (the table, the format and the number
of rows) and every panel outcome CSV (the environment and the outcome), never
the data itself. Owners and admins read the organization-wide log; every
member can read a single project's log. Sign-ins and password changes that go
through the managed sign-in service are **not** recorded. The full list is
under [Activity](Studio-Organizations-and-Team#activity).

---

## Sign-in security

- **Passwords** must have at least 8 characters, with a lowercase letter, an
  uppercase letter, a number and a symbol. Signing up with email and password
  requires **confirming the address** from the email Studio sends.
- **Captcha** (Cloudflare Turnstile) protects sign-up, sign-in and password
  reset when it is enabled. The check loads from Cloudflare when the sign-up,
  password or **Reset your password** form opens — not on the first, email
  step.
- **Too many attempts** are slowed down: the sign-in service limits attempts,
  and Studio limits how often it tells whether an email address has an
  account. From one network (IP) address it answers at most 10 lookups a
  minute for the same email and at most 20 a minute across all emails, so a
  list of addresses cannot be checked quickly. Past that limit the email step
  says "Could not check your email. Too many sign-in attempts from your
  network just now — wait a minute and try again." It never treats a failed
  lookup as "no account".
- **Google and Microsoft** sign-in inherit the provider's protections,
  including its two-factor authentication. This is the recommended route for
  sensitive studies. A provider sign-in whose email address is not verified
  is refused.
- **Sessions** are renewed in the background while you work. After about a
  week without opening Studio you are asked to sign in again. **Sign out**
  invalidates the session's token.
- **Not yet available:** Studio's own two-factor authentication, and
  organization single sign-on (SAML / OIDC), which arrives after the beta.

See [[Sign Up and Sign In|Studio-Sign-Up-and-Sign-In]].

---

## Compliance status

Be straightforward with your committee:

- The beta does **not** carry SOC 2, ISO 27001, HIPAA or similar
  certifications.
- Sign-in is handled by a managed authentication service. The
  [Privacy Policy](https://siamang.org/privacy-policy) names the processors and
  where data is handled.
- **Self-hosting** is available on the Corporate plan for regulated
  environments.
- The engine is source-available, so your instrument and analysis can be
  reviewed and re-run independently of Siamang. Many committees accept this as
  an argument in itself (see
  [[Reproducibility: Code, Bundles and Citation|Studio-Reproducibility]]).

For the current legal texts see the
[Terms of Use](https://siamang.org/terms-of-use) and the
[Privacy Policy](https://siamang.org/privacy-policy).

---

## Your responsibilities

- Collect only what your study needs, and say what you collect.
- Get consent before contacting people. The contact importer asks you to
  confirm it, and the import is recorded.
- Decide deliberately about the AI assistant (above) before turning it on.
- Check interactive reports and chart tiles for what their numbers reveal
  before you send or share them — above all scatter plots, box plots and
  charts of small groups (see
  [Interactive charts and your data](#interactive-charts-and-your-data)).
- Download bundles and exports with care. A bundle **with data** contains raw
  responses, the project tables and uploaded files the flows read, and the
  survey-link parameters a flow reads. A **Data → Export** file carries every
  link parameter, panel ids and invitation tokens included. Store and share
  them like the personal data they may be, and check what is in the data
  before you check **Include the data collected so far** in a deposit.
- Leave out the columns of personal data that an uploaded data file carries
  and the analysis does not need, as early in the flow as you can (see
  [Data files you upload](#data-files-you-upload)).
- Remove people from the organization when they leave, and revoke API keys
  you no longer use.

## See also

- [[Organizations and Team|Studio-Organizations-and-Team]]
- [[Account and Profile|Studio-Account-and-Profile]]
- [[Responses and the Data Tab|Studio-Responses-and-Data]]
- [[AI Assistant|Studio-AI-Assistant]]
- [[Email Invitations|Studio-Email-Invitations]]

<!-- studio-nav -->
---

← [[Working Together|Studio-Collaboration]] · [Studio contents](Studio-Overview#all-pages) · [[Recipes|Studio-Recipes]] →
