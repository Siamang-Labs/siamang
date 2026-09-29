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
| Members per organization (owner and pending invitations count; an invitation sent again counts once) | 2 | 15 | unlimited | unlimited |
| Completed interviews per project (all environments together; screen-outs, partials and the Example template's sample rows not counted) | 1,000 | unlimited | unlimited | unlimited |
| File storage per organization (uploads **and** run outputs) | 250 MB | 5 GB | 50 GB | unlimited |
| Analysis flows per project (checked when a Save adds one: a project started from the example study keeps its six on every plan) | 3 | 20 | unlimited | unlimited |
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
| Larger AI model (drafts from a brief) | — | — | ✓ | ✓ |
| SSO | — | — | after the beta | after the beta |
| Self-hosting | — | — | — | ✓ |

Free on every plan: the whole Builder (all question types, logic, quotas,
randomization, theme, the script library), imports, the question bank and
templates, coding open answers by hand and by rules, Download .py, research
bundles, every data export, History, pre-registration and deposits, comments
and edit locks, API keys.

→ [[Plans, Trial and Billing|Studio-Plans-and-Billing]]

## The trial

| | |
|---|---|
| Length | 30 days of Pro, once per email address |
| Not included during the trial | email invitations (import and send unlock once a plan is bought) |
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
| One per browser | off by default; one interview per browser per environment, remembered by a mark in the respondent's browser that is not cleared after a week (it stays until they clear their browser data) |
| Preview deployments | removed automatically after 7 days |
| URL parameters stored per response | the first 8; names lower-cased, up to 40 characters; values up to 200 characters |
| Browser autosave for respondents | 7 days after the last answer, same browser only, one per survey; nothing is kept before the respondent starts; cleared once the interview is submitted or ended by a full quota. Everything else a survey keeps in the browser also goes after 7 days without a write, except the One per browser mark |
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

## Statistics in flows

The methods themselves cap a few computations; each result says which way it
went.

| Item | Limit |
|---|---|
| Fisher's exact test, tables larger than 2 × 2 | summed exactly over at most 200,000 tables with the observed margins; beyond that, 20,000 random tables from a fixed seed (the same p on every run) |
| Wilcoxon signed-rank exact p (**p-value** `auto`) | up to 50 pairs with no ties or zeros, up to 13 with them; the normal approximation above |
| Wilcoxon exact p on request (**p-value** `exact`) | up to 1,000 pairs; above, the normal approximation, and the result says so |
| McNemar exact binomial p (**p-value** `auto`) | fewer than 25 respondents who answered the two questions differently; the chi-square approximation from 25 |
| Correlation | at least three complete pairs |
| Factor analysis | at least 3 items and more respondents than items; parallel analysis draws 100 random data sets (95th percentile); maximum likelihood is started from 14 fixed points |
| Data check | up to 5 example values per problem, then "… (N more)" |
| TURF exhaustive search (**Search** `best`) | up to 200,000 combinations; beyond, the run stops and suggests a smaller portfolio, fewer options or `greedy` |
| Key drivers | at least 2 drivers; the Shapley value (**Importance** `shapley`) for at most 15 — Johnson's relative weights for more |
| Significance letters (Banner table, Bar chart, Tab book) | a column or group of fewer than 30 respondents is not tested (the Bar chart and the Tab book count those who answered the question); **Level** 0.001–0.2 |

## Charts, tab books and report colors

| Item | Limit |
|---|---|
| Figure size | 2–30 inches each way (10 × 6 by default); a chart whose labels need more room grows taller |
| Bar chart, newer forms | a number of more than 30 different values given is refused as bars, a split or a donut (a histogram draws it); with **Top N**, up to 30 of its values given most are drawn |
| Bar chart **Top N** | 1–100 answers |
| Bar chart **Bins** | at most 100 bins; a number of bins from 1 to 100 |
| Bar chart **Confidence** | 0.5–0.999 (0.95 by default) |
| Donut **Other below (%)** | 0–50 % (3 by default) |
| Trend | at most 500 points: the periods from the first date to the last, or the wave codes; bands for up to 4 lines (more lines: marker shapes, the table keeps the intervals); **Minimum base** 30 by default |
| Tab book | a banner variable of at most 30 different values; a question without answer labels of at most 30 different answers (a number shows its mean instead); sheet names cut to Excel's 31 characters; the letters as above |
| Likert chart scale | from value labels, or a valid range of 2 to 11 whole numbers |
| Chart colors (a report's **Look**) | **Series** 2–12 hex colors, none twice; a series or **Magnitude** color at least 1.3:1 on white; **Chart text** at least 4.5:1 |

## Coding open answers

Coding by hand and by rules, in the codeframe editor and the **Code open
answers** node. → [[Coding Open Answers|Studio-Open-Answer-Coding]]

| Item | Limit |
|---|---|
| AI coding of open answers | switched off on this platform |
| Codeframe name | `analysis/<name>.codeframe.json`: lower-case letters, digits, `_`; starts with a letter; up to 63 characters |
| Themes per codeframe | up to 200 (an older, version 1 codeframe: 64) |
| Terms per list (**Words and phrases**, **But not**, each **Must also contain** list) | up to 500 |
| A term | up to 200 characters; words near each other at most `~20` apart; no regular expressions |
| Replacements | up to 2,000, each side up to 200 characters |
| Negation | reaches the next 3 words, within the clause; English only |
| A "word" in an answer | longer than 200 characters (a pasted link), it matches no term |
| Keys in the answers list | `1`–`9` for the first nine themes |
| Distinct answers the editor reads | the 100,000 most frequent (beyond: "the rarest answers are left out") |
| Answers per page in the editor | 100 |
| New answers in the editor | read again once the last reading is a minute old |
| Suggested words | up to 30 words and 30 two-word phrases, each used by 2 respondents or more |
| Editor requests (answers, previews, tests, suggestions) | 60 per 10 seconds per person; one request up to 8 MB |
| Errors and warnings listed | the first 200 of each, with the total |
| Credits | none |

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
