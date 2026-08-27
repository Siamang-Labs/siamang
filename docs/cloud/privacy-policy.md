# Siamang Cloud — Privacy Policy

_Last updated: 25 June 2026_

Siamang Cloud is an open-beta service operated by **Siamang Labs LLC**, a Wyoming limited
liability company, the team behind the open-source
[`siamang`](https://github.com/Siamang-Labs/siamang) engine. This policy explains, in
plain language, what data the Siamang Cloud **console** collects about you (the account
holder) and how we handle it. It is offered in good faith and will be updated as the
project matures.

## 1. Scope: two kinds of data

There are two very different kinds of data on the platform:

- **Your account and usage data** — information about you as a user of the console.
  This policy describes how *we* handle it.
- **Survey respondent data** — the answers you collect from people who take your
  surveys. **You decide what to collect and why; you are the data *controller* and
  Siamang Cloud is only your *processor***, storing and processing that data on your
  behalf and on your instructions. Respondents should be pointed to *your* privacy
  notice, not this one. You are responsible for a lawful basis, notice and consent —
  see the [Terms of Use](terms-of-use.md).

## 2. What we collect

**Account information** you give us:

- email address and a display name;
- the organizations and projects you create or join;
- credentials you add (hashed passwords where applicable; API keys and SSH public keys,
  stored to authenticate you).

**Content you create:** questionnaires, analysis scripts, project configuration and
generated outputs/reports — stored in your project's Git repository and database schema
so the Service can run.

**Respondent data (on your behalf):** the survey responses your deployed surveys
collect, stored in your project's database. We process this only to provide the Service
to you.

**Technical and usage data:** the basic logs needed to operate the Service — for
example request metadata, timestamps, an audit trail of actions in your organization
(deploys, runs, invites), and error logs. We keep this to run, secure and debug the
Service.

We do **not** run advertising trackers, and we do not sell your data.

## 3. Cookies

The console uses only the cookies and local storage needed to **sign you in and keep
your session** (and to remember preferences such as light/dark theme). We do not use
third-party advertising or cross-site tracking cookies in the console. A survey you
build can optionally enable its own analytics — that is your choice and your
responsibility, configured per survey.

## 4. How we use data

We use account, content and technical data to:

- provide and operate the Service (authenticate you, run validation/preview/deploy,
  collect responses, run analysis, show dashboards);
- keep the Service secure and reliable (abuse prevention, debugging, backups);
- communicate with you about your account or important service changes;
- understand aggregate usage to improve the product.

Where the GDPR or similar laws apply, our lawful bases are: performing our agreement
with you (the Terms), our legitimate interest in operating and securing the Service,
and your consent where required. For respondent data, your instructions as the
controller govern our processing.

## 5. Where data is stored and who processes it

Siamang Cloud runs on third-party infrastructure acting as our **subprocessors**, used
only to deliver the Service:

- cloud hosting/compute for the application and the sandboxed run environment;
- a PostgreSQL database (your account data and per-project data);
- object storage for files, artifacts and report outputs;
- a Git service for your project repositories;
- an authentication provider for sign-in (depending on deployment).

We share data with these providers only to run the Service, and with others only if
required by law or to protect rights and safety. If the project is ever transferred, we
will keep this policy's protections in place and let you know.

## 6. Data retention

- Account and content data are kept while your account or organization is active.
- When you delete a response, project, organization or your account, we delete the
  associated data from active systems; residual copies in backups roll off on the
  normal backup cycle.
- Operational logs and the audit trail are kept only as long as needed to operate and
  secure the Service.

## 7. Your rights and choices

From within the app or by contacting us, you can:

- **access and export** your data (the platform supports exporting tables/datasets);
- **correct** your account details;
- **delete** individual responses, projects, organizations, or your whole account
  (response and project deletion is built into the app — useful for honouring
  respondents' erasure/GDPR requests as the controller);
- object to or restrict certain processing where the law gives you that right.

For respondent data you hold as controller, you remain in control: delete it in-app or
ask us and we will act on your instructions. If a respondent contacts us directly, we
will refer them to you.

## 8. Security

We take reasonable measures to protect data — including isolation between projects,
sandboxed execution of user code, hashed credentials, and access controls. No system is
perfectly secure; please use a strong password, keep your API and SSH keys safe, and
tell us promptly if you suspect a problem.

## 9. Children

The console is not intended for people under 16 as account holders. If you collect data
from minors through your surveys, you are responsible for the additional protections and
consents the law requires.

## 10. International users

The Service may process and store data in countries other than yours. Where required, we
rely on appropriate safeguards for any cross-border transfer.

## 11. Changes to this policy

We may update this policy as the project evolves; the "Last updated" date above will
change and significant updates will be surfaced in the app.

## 12. Contact

Privacy questions or requests? Email **info@siamang-team.org** or open an issue at
<https://github.com/Siamang-Labs/siamang/issues>.

The data controller for your account and usage data is Siamang Labs LLC, 30 N Gould St
Ste N, Sheridan, WY 82801, USA.

---

_Siamang Cloud is an independent open-beta project. This policy is written in good faith
and in plain language; it is not legal advice and will be refined as the project grows._
