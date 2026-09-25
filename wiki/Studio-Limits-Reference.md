# Limits and Quotas at a Glance

Every number Studio enforces, in one place: plan limits, per-feature caps,
sizes, timeouts and retention. The pages linked in each section explain what
happens when you reach a limit and what to do about it.

Plans are **per organization**. A limit you are already over — after a
downgrade or when a trial ends — never locks existing work: you can keep
saving and deleting, you just cannot add more.

---

## Plan limits

| | Free | Plus | Pro | Corporate |
|---|---|---|---|---|
| Price shown in the app | Free | $25/mo | $99/mo | Custom (Contact sales) |
| Projects per organization | 2 | 10 | unlimited | unlimited |
| Members per organization (owner and pending invitations count) | 2 | 15 | unlimited | unlimited |
| Completed interviews per project (all environments together; screen-outs, partials and the Example template's sample rows not counted) | 1,000 | unlimited | unlimited | unlimited |
| File storage per organization (uploads **and** run outputs) | 250 MB | 5 GB | 50 GB | unlimited |
| Analysis flows per project | 3 | 20 | unlimited | unlimited |
| Access codes per questionnaire | 100 | 5,000 | unlimited | unlimited |
| One flow run: time / memory | 5 min / 512 MB | 15 min / 1 GB | 30 min / 2 GB | 30 min / 2 GB |
| "Run to here" previews per user, per project, per hour | 30 | 120 | 600 | unlimited |
| Previews running at once per user | 1 | 1 | 2 | 4 |
| Custom JavaScript and custom CSS in a published survey | — | ✓ | ✓ | ✓ |
| Live auto-recompute and public live links | — | ✓ | ✓ | ✓ |
| Schedules · webhooks · connectors | — | ✓ | ✓ | ✓ |
| Connectors available | — | Sheets, Excel 365, Supabase, HubSpot | + S3/R2/MinIO, GCS, Azure Blob, BigQuery, Snowflake, Postgres, SFTP, REDCap, Salesforce, HTTP | + (coming) MCP |
| Saving to the organization library | — | ✓ | ✓ | ✓ |
| Email invitations: per month / per day / first mailing | — | 1,000 / 300 / 200 | 5,000 / 1,500 / 500 | no caps |
| AI assistant: credits per month / per day | — | 8,000 / 2,000 | 50,000 / 8,000 | 300,000 / 30,000 |
| AI requests per person per hour | — | 30 | 100 | 300 |
| Larger AI model (drafts, open-answer coding) | — | — | ✓ | ✓ |
| SSO | — | — | after the beta | after the beta |
| Self-hosting | — | — | — | ✓ |

Free on every plan: the whole Builder (all question types, logic, quotas,
randomization, theme, the script library), imports, the question bank and
templates, Download .py, research bundles, every data export, History,
pre-registration and deposits, comments and edit locks, API keys.

→ [[Plans, Trial and Billing|Studio-Plans-and-Billing]]

## The trial

| | |
|---|---|
| Length | 30 days of Pro, once per email address |
| Not included during the trial | email invitations (import and send unlock with the first payment) |
| AI during the trial | 500 credits in total, at most 200 per day and 10 requests per hour |
| Reminders | email 7 days and 1 day before the end; banner in the last 3 days |
| When it ends | the organization moves to the **Free** plan; nothing is deleted |
| Extra organizations you create | start on Free, no trial |

---

## Accounts and organizations

| Item | Limit |
|---|---|
| Password | at least 8 characters, with a lower-case letter, an upper-case letter, a number and a symbol |
| Name | 1–200 characters |
| Organization slug | 3–40 characters (`a–z`, `0–9`, `-`), generated from the name, permanent |
| Team invitation link | valid 7 days |
| API key name | 1–80 characters; the key is shown once; keys made in the app do not expire |
| Email lookup on the sign-in page | 10 per minute per address and network, and 20 per minute per network across all addresses |
| Organization house style (**Branding**) | **Custom CSS** up to 64 KB; every other value up to 4 KB; 128 KB for the whole style |

## Projects and the Builder

| Item | Limit |
|---|---|
| Project slug | 3–64 characters (`a–z`, `0–9`, `-`), made from the name — other scripts spelled in Latin letters, a long name cut at a word break, `project` when nothing can be spelled, `-project` added to a name of one or two characters (`Q1` → `q1-project`), `-2`, `-3`, … when the organization already has it; permanent, unique in the organization |
| Project name (rename) | 1–120 characters |
| Default environments of a new project | `pilot` capped at 50 completed interviews, `main` capped at 1,200 |
| Undo history | 100 steps; cleared by each Save |
| Draft autosave | 1.5 seconds after your last change |
| Save message | up to 240 characters |
| Likert points | 2–11 |
| Custom JavaScript per script | 2,000 characters |
| Import file | up to 2 MB, UTF-8 |
| Library item | name up to 120 characters, description up to 500 |
| Share-preview links | valid 24 hours; up to 50 new links per person per day |
| Simulate | 1–5,000 responses (default 200, seed 42); preview shows the first 50 rows |
| Edit lock | renewed every 30 s; expires 2 minutes after the last renewal |
| Pages, questions, options | no fixed limit |

## Fieldwork

| Item | Limit |
|---|---|
| Survey link | `study.siamang.org/<12-character survey id>/`, one per environment, stable across republishes |
| Response cap | the tighter of the environment's cap (counted in that environment) and the plan's (Free: 1,000 per project, all environments together); counts completed interviews only — screen-outs and partials never count, and a screen-out is recorded even when the cap is full; checked when the survey page opens and when a respondent submits |
| Quota cell | closes at its limit of completed interviews; checked when the respondent leaves a page; a check that gets no answer within 4 seconds lets the respondent go on; previews never check |
| Closing date | the earlier of the questionnaire's `deadline` and the environment's `closes_at` as of the published Save, or a date set in the card's **Closing date** panel (applies at once); once it passes, the page shows the closed notice as it opens, and submissions and progress saves are refused (a date without a time zone is read as UTC) |
| One per browser | off by default; one interview per browser per environment, remembered in the respondent's browser |
| Preview deployments | removed automatically after 7 days |
| URL parameters stored per response | the first 8; names lower-cased, up to 40 characters; values up to 200 characters |
| Browser autosave for respondents | 24 hours, same browser only, one per survey; cleared once the interview is submitted or ended by a full quota |
| Submit retries | 3 attempts |
| Redirect delays | completion 5 s; terminal page 5 s by default; quota-full and full-cap 3 s; closed notice to the environment's post-close redirect 3 s |
| Access codes | format `PREFIX-NNNN` (prefix up to 8 characters, 10,000 codes per prefix); 1–5,000 generated at a time |
| Captcha: completions without a token | 3 per hour per survey per network address |
| Submissions | 60 requests per minute per survey per network address; progress saves, the status check as the page opens and quota checks each have a separate allowance of the same size |
| One submission | answers up to 256 KB and 2,000 answer keys (key names up to 200 characters); the whole request up to 2 MB |
| Contacts import | up to 20,000 lines per import |
| Mailing | subject up to 200 characters; message up to 20,000; sent in batches; month and day boundaries in UTC |
| Automatic mailing pause | complaints ≥ 1 and ≥ 0.05 % of delivered, or bounces ≥ 3 and ≥ 2 % |
| Live tiles auto-recompute | 10 seconds after the last completed response (Plus and above) |
| Monitor refresh | Distribute and Live every 30 seconds while the tab is visible |

## Data

| Item | Limit |
|---|---|
| Data grid | 100 rows of a table, newest first (tables with a `created_at` or `id` column), 25 per page; **Search all rows** searches every row and loads the newest 100 matches |
| Export (Data tab, API, bundle with data) | up to 100,000 rows per file |
| Insights | top 50 values per frequency; top 2,500 cells per crosstab |
| Panel outcome CSVs | every response of the outcome |
| Response retention | kept until you delete them or the project |

## Flows and reports

| Item | Limit |
|---|---|
| Flow run | 1 CPU, no internet; time and memory by plan (above) |
| Outputs collected per run | 50 files, 200 MB in total, written under `outputs/`; when a run writes more, report documents (`.md`, `.html`) are kept ahead of figures and other files |
| Preview run | 512 MB, 2 minutes, on every plan |
| Run history shown | the latest 50 runs |
| Output download links | valid 5 minutes |
| Flow and connector names | lower-case letters, digits, `_`; start with a letter; up to 63 characters; not `survey` |
| Report custom CSS | anything except the sequence `</` |

## Open-answer coding with AI

| Item | Limit |
|---|---|
| Distinct answers per job | 4,000 |
| Themes per codeframe | up to 24 |
| Answer length read | first 400 characters |
| Credits | about 160 for 1,000 answers (Plus model), about 600 (Pro model) |

## History, files and automation

| Item | Limit |
|---|---|
| Saves | kept for the life of the project; History lists the latest 100 |
| Comments | up to 4,000 characters; the oldest 500 of a project are loaded |
| File upload | up to 50 MB per file; name up to 128 characters |
| File download links | valid 5 minutes |
| Connector rows | 100,000 per run (Google Sheets 50,000; Excel 365 10,000); a larger table fails the whole run |
| Schedules | 5-field cron, UTC, checked every minute |
| Webhooks | URL up to 500 characters; up to 5 attempts, retried after 2, 4, 8 and 16 minutes; 10-second timeout |
| Deposits | 2-minute timeout per request to Zenodo or OSF |
| Activity log | latest 100 events shown; export as CSV |

## See also

- [[Plans, Trial and Billing|Studio-Plans-and-Billing]]
- [[FAQ and Troubleshooting|Studio-FAQ-and-Troubleshooting]]
- [[Security and Privacy|Studio-Security-and-Privacy]]
- [[Glossary|Studio-Glossary]]

<!-- studio-nav -->
---

← [[Recipes|Studio-Recipes]] · [Studio contents](Studio-Overview#all-pages) · [[Keyboard Shortcuts|Studio-Keyboard-Shortcuts]] →
