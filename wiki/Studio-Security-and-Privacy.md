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
Surveys first published in the earlier address form
(`study.siamang.org/<organization>/<project>/<environment>/`) may still answer
on it.

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
  admins can delete a response or read the organization-wide Activity log.
- **Public by design, and only when you create them:**

| Public surface | What it shows | Lifetime |
|---|---|---|
| A published survey link, or the survey embedded in your site | the questionnaire, for respondents to answer | until you close or unpublish it |
| A **share preview** link | the respondent view of a draft, for reviewers. Answers given there are not stored. | 24 hours. Each person can create up to 50 per day. |
| A **Live share link** *(Plus)* | the Live tiles only: no raw rows, no questionnaire | until revoked. Creating a new link revokes the previous one. It stops working if the organization drops below Plus. |
| The **unsubscribe** link in invitation emails | a page where the recipient opts out of further mailings | sent with every invitation email |
| A **team invitation** link | the inviter's name, the organization name, the role, a masked email address (`j***@example.com`) and the expiry date | 7 days, or until used or revoked |

Nothing else is public.

---

## Respondent data

- **What a response holds:** the answers plus fieldwork metadata: timings,
  the last page reached, and any URL parameters that were in the link.
- **IP addresses are not stored with responses.** They are used briefly to
  limit how fast one address can submit. On surveys where you switch on the
  **captcha**, the respondent's IP address is sent to Cloudflare together with
  the captcha token so Cloudflare can verify it.
- **The respondent id** is a random identifier that lets an interview resume
  and lets you deduplicate. It is not an identity.
- **Personal data you ask for** (a name, an email, a phone number) is personal
  data you collected. Treat it accordingly, and say so on your consent page.
- **Email invitations** store the contact list you imported, each person's
  status (sent, started, completed), unsubscribes, and addresses suppressed
  after a bounce or a spam complaint. See
  [[Email Invitations|Studio-Email-Invitations]].

### Erasure requests

1. Find the response in **Data**: by `respondent_id`, by invitation address,
   or by a panel id in the URL parameters.
2. Delete it. Only owners and admins can.
3. The row is removed from the database, and the deletion is recorded in the
   Activity log (`response.delete`) **without** its content, which gives you
   the evidence.

Exports and research bundles downloaded **before** the deletion still contain
the row. Delete or re-create those copies as well. See
[[Responses and the Data Tab|Studio-Responses-and-Data]].

### Consent and ethics

**Builder → Theme** carries the fields an ethics committee usually asks for:
**Estimated minutes**, **Contact email**, **Privacy URL** and **Ethics
statement**. Put your consent text on the first page with a required "I agree"
question, and route anyone who declines to the end of the survey (see
[[Logic and Branching|Studio-Logic-and-Branching]]).

---

## Code execution

- **Your generated code** (the questionnaire and your analysis flows) runs in
  an ephemeral, isolated sandbox with **no network access**, one CPU, memory
  and time ceilings set by your plan, and no way to change anything outside
  its own output folder.
- **Imported Python is never executed.** A `questionnaire.py` you import is
  read as text. Anything the reader cannot follow is reported with line
  numbers, not run.
- **Custom JavaScript** *(Plus)* runs only in the respondent's browser, inside
  the survey. It never runs on Siamang's servers and never touches the analysis.

---

## Secrets

Project secrets (connector credentials, tokens) are **encrypted at rest** and
**write-only**: once saved, nobody can read them back through Studio, you
included. Only their names are listed. They are handed to runs by name. To
rotate a secret, overwrite it; to revoke it, delete it. Only owners and admins
can set or delete secrets, and both actions are recorded in the Activity log.
See [[Project Settings|Studio-Project-Settings]].

## API keys

Personal API keys (`sck_…`) are stored **only as a hash** and shown **once**,
when you create them. A key acts as you, with your role, in every organization
you belong to. Keys created in the app **do not expire**, so revoke the ones
you no longer use. Creating and revoking keys is not recorded in the Activity
log. See [[Account and Profile|Studio-Account-and-Profile]] and
[[API and API Keys|Studio-API-and-API-Keys]].

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
  analysis descriptions, a brief you write. If you use AI coding of open
  answers, the **text of those answers** is sent. It goes without respondent
  ids, metadata or timings, and each answer is clipped to 400 characters.
- **The owner can turn it off** at any time with **Turn the assistant off**.

If your ethics approval or data agreement does not allow processing in China,
leave the assistant off. See [[AI Assistant|Studio-AI-Assistant]] and the
[Privacy Policy](https://siamang.org/privacy-policy).

---

## Audit trail

Each organization keeps an append-only **Activity** log: Saves, restores,
publishing, pausing and closing, runs, response deletions, bundle downloads,
Live share links, contact imports, mailings (including bounces and spam
complaints), member changes, secret changes, plan and billing events, and the
AI assistant switch. Owners and admins read the organization-wide log; every
member can read a single project's log. Sign-ins, profile changes, API keys,
organization renames, webhook changes and access-code generation are **not**
recorded. The full list is under
[Activity](Studio-Organizations-and-Team#activity).

---

## Sign-in security

- **Passwords** must have at least 8 characters, with a lowercase letter, an
  uppercase letter, a number and a symbol. Signing up with email and password
  requires **confirming the address** from the email Studio sends.
- **Captcha** (Cloudflare Turnstile) protects sign-up, sign-in and password
  reset when it is enabled.
- **Too many attempts** are slowed down: the sign-in service limits attempts,
  and Studio limits how fast the same address can be looked up.
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
- Download bundles with care: a bundle **with data** contains raw responses.
  Store and share it like the personal data it may be.
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
