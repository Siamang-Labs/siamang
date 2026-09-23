# Glossary

The words Siamang Studio uses, in alphabetical order, with a link to the page
that explains each one in full.

---

**Access code** — a code a respondent must enter before the first question
(`PREFIX-NNNN`). Codes are stored in the questionnaire, so generating them
creates a Save; republish the environment to apply them. The check happens in
the respondent's browser. → [[Links, QR Codes, Embeds and Access Control|Studio-Distribution-Channels]]

**Activity** — the audit log: who saved, published, ran, exported or deleted
what, and who renamed the organization, added or removed a webhook, created
or revoked an API key or generated access codes. Per organization (owners and
admins) and per project (all members).
→ [[Organizations and Team|Studio-Organizations-and-Team]]

**AI assistant** — optional suggestions from a language model: reviews of
wording and analysis, rewrites, answer options, drafts from a brief and the
coding of open answers. Off until the organization's owner turns it on;
Plus and above. → [[AI Assistant|Studio-AI-Assistant]]

**AI credit** — the unit the assistant's allowance is counted in, about 1,000
tokens of model input. → [[Plans, Trial and Billing|Studio-Plans-and-Billing]]

**API key** — a personal token (`sck_…`) that lets a script call the Studio
API as you. Shown once. → [[API and API Keys|Studio-API-and-API-Keys]]

**Assign to a condition** — a library script that puts each respondent in one
arm of an experiment. → [[Scripts|Studio-Scripts]]

**Attention check** — a question with a known correct answer, marked in the
Builder so the analysis can flag respondents who fail it.
→ [[Data Quality|Studio-Data-Quality]]

**Banner table** — a cross-break: several questions down the page against
several breakdowns across it, with significance letters.
→ [[Node Reference|Studio-Node-Reference]]

**Block** — a group of questions inside a page, shown, hidden or shuffled
together. → [[The Builder|Studio-Builder-Overview]]

**Branch (next if)** — an ordered list of `condition → page` rules on a page;
the first rule whose condition is true decides where the respondent goes
next. A rule without a condition never fires.
→ [[Logic and Branching|Studio-Logic-and-Branching]]

**Build log** — the log of turning a Save into a published survey, on the
environment's card in Distribute.

**Codebook** — all variables with their scales, labels, value labels, valid
ranges and missing codes; built alongside the questions and exported with the
data. → [[Codebook and Variables|Studio-Codebook-and-Variables]]

**Codeframe** — a saved coding scheme for one open-text question
(`analysis/<name>.codeframe.json`); applied by the **Code open answers** node
without calling any model. → [[Coding Open Answers|Studio-Open-Answer-Coding]]

**Combined report** — the single document **Run all** assembles from every
flow's report. → [[Reports|Studio-Reports]]

**Comment** — a note on a question, page, flow or flow node, visible to the
organization. → [[Working Together|Studio-Collaboration]]

**Condition** — a rule over earlier answers (`age ≥ 18`, `region in [1, 2]`)
used by show if, hide if, branch rules and the Filter rows node.
→ [[Logic and Branching|Studio-Logic-and-Branching]]

**Conjoint** — a question type that shows whole products side by side and
asks which one the respondent would choose.
→ [[MaxDiff and Conjoint|Studio-MaxDiff-and-Conjoint]]

**Connector** — a configured link that exports a project table to another
system (Sheets, a warehouse, storage, a CRM) or imports one.
→ [[Connectors|Studio-Connectors]]

**Deadline** — a date and time set in the questionnaire after which a
published environment accepts no more responses; the environment's card shows
it as **Closes `<date>`**.
→ [Deadlines](Studio-Publishing-and-Environments#deadlines)

**Default next** — where a page leads when none of its branch rules matches;
empty means the next visible page.

**Deployment** — one Save published into one environment. Live, paused,
closed, building or failed. → [[Publishing and Environments|Studio-Publishing-and-Environments]]

**Deposit** — sending a Save's research bundle to Zenodo (which mints a DOI)
or OSF. → [[History and Versions|Studio-History-and-Versions]]

**Document** — one of the files a project is made of: the questionnaire, each
flow, the settings, each codeframe. → [[Key Concepts|Studio-Key-Concepts]]

**Draft** — your unsaved, autosaved edits to a document. Private until you
Save, except that colleagues following your edit lock see it live.

**Drop-off** — where respondents who did not finish stopped, page by page.

**Edit lock** — the right to edit one document. One person holds it; others
follow live and can **Take over**. → [[Working Together|Studio-Collaboration]]

**Environment** — a named publishing target (`pilot`, `main`) with its own
permanent link and response cap. → [[Publishing and Environments|Studio-Publishing-and-Environments]]

**Export Python** — downloading the Python the engine generated for the
questionnaire or a flow at a given Save. → [[Reproducibility|Studio-Reproducibility]]

**Flow** — an analysis drawn as connected nodes; saved as a document and
generated into a Python script. → [[Analysis Flows|Studio-Flows]]

**Frozen workspace** — an organization that support has made read-only. Not
the same as the end of a trial, which moves the organization to the Free plan.

**House style** — an organization's default survey look (Organization
settings → **Branding**), stamped into each new project; and, separately, a
project's default report look (Project settings → **Reports**).
→ [[Theme and Branding|Studio-Theme-and-Branding]] · [[Reports|Studio-Reports]]

**Id (question)** — a question's own handle in the Builder (**Advanced →
Id**): scripts target it, and the Logic map and validation messages name the
question by it. It may differ from the question's own variable name, but it
must not be another question's variable name.
→ [Question Id and variable name](Studio-Builder-Overview#question-id-and-variable-name)

**Insights** — instant frequencies and crosstabs computed by the server from a
table in **Data**, without a flow. → [[Responses and the Data Tab|Studio-Responses-and-Data]]

**Live tile** — a flow output published to the **Live** screen and, if you
choose, to a public read-only page. → [[Live Monitoring|Studio-Live-Monitoring]]

**Mailing** — an email invitation or reminder sent to a project's contacts,
each with a personal link. → [[Email Invitations|Studio-Email-Invitations]]

**MaxDiff (best–worst)** — a question type that shows a few items at a time
and asks for the best and the worst.
→ [[MaxDiff and Conjoint|Studio-MaxDiff-and-Conjoint]]

**Methods draft** — a Methods section Studio writes from a Save's documents,
with `[...]` where you must fill in. → [[History and Versions|Studio-History-and-Versions]]

**Missing code** — a value that means "no valid answer" (`98 = Don't know`),
declared with its label in the Codebook and exported as a declared missing
value to SPSS and Stata.
→ [Missing codes](Studio-Codebook-and-Variables#missing-codes)

**Node** — one box in a flow: a source, a preparation step, an analysis, a
chart or an output. → [[Node Reference|Studio-Node-Reference]]

**Organization** — a workspace owning projects, members, the plan and the
bill. → [[Organizations and Team|Studio-Organizations-and-Team]]

**Page kind** — what a page does: an ordinary **Content** page, a **Final**
(thank-you) page, a **Screen-out** page or a **Redirect** page.

**Panel provider** — a sample company (Prolific, Cint, Dynata, …) that sends
respondents with an id in the link and expects them back on a return URL.
→ [[Panel Providers|Studio-Panel-Providers]]

**Partial** — an interview that was started but not submitted. Stored in the
data; not counted toward caps or quotas.

**Piping** — inserting an earlier answer into text: `{answer:var}`,
`{label:var}` (or `{var:var}`). → [[Logic and Branching|Studio-Logic-and-Branching]]

**Pre-registration** — a tag on one Save marking it as the registered
questionnaire and analysis plan; later Methods drafts and bundles report what
changed since. It does not lock anything.

**Preset** — a question type pre-configured for a common use (Yes / No, NPS,
CES, Attention check, Date, Email, Phone, Rating).
→ [[Question Types|Studio-Question-Types]]

**Preview** — seeing the survey as a respondent will: on the Builder canvas
(unsaved edits), as a preview deployment built from a Save, or through a
24-hour share link. Answers are never stored.
→ [[Testing Your Survey|Studio-Testing-Your-Survey]]

**Project** — one study: questionnaire, flows, settings, database,
deployments and history. → [[Projects|Studio-Projects]]

**Provenance** — the record of what produced a result: project, Save, data
snapshot and engine version. In every bundle (`PROVENANCE.md`) and at the foot
of every platform report. → [[Reproducibility|Studio-Reproducibility]]

**Quota cell** — a `variable = value` pair with a target number of completed
responses, counted during fieldwork. → [[Quotas and Randomization|Studio-Quotas-and-Randomization]]

**Report section / Save report** — the flow nodes that assemble a document
from tables, charts and your text. → [[Reports|Studio-Reports]]

**Research bundle** — a zip of one Save: generated code, documents, codebook,
Methods draft, citation file, provenance, environment pin and optionally the
responses. → [[Reproducibility|Studio-Reproducibility]]

**Respondent id** — a random identifier kept in the respondent's browser so
an interview can resume; not an identity.

**Response cap** — the number of completed responses an environment accepts
(the tighter of its own cap and the plan's).

**Run** — one execution of a flow (or of all flows) in the sandbox, with a log
and output files. → [[Analysis Flows|Studio-Flows]]

**Run all** — running every flow of the project one after another and
assembling the combined report. Flows run in dependency order (a flow that
reads a table another flow writes comes after it), alphabetically otherwise;
a failed flow skips only the flows that read its tables.
→ [Run all](Studio-Flows#run-all)

**Run to here** — executing a flow up to the selected node to see its result,
without producing a report or a run-history entry.

**Save (noun)** — a numbered version of the whole project (`#17`): validated,
with generated code stored alongside it. → [[History and Versions|Studio-History-and-Versions]]

**Save badge** — the topbar indicator of the project's current Save and its
state: `valid`, `warnings`, `errors`, `checking`, `unsaved`.

**Scale** — a variable's measurement level: nominal, ordinal, interval or
ratio.

**Schedule** — a cron entry (UTC) that runs a flow or Run all automatically.
→ [[Schedules and Webhooks|Studio-Schedules-and-Webhooks]]

**Screen-out** — ending an interview for someone who does not qualify, by
routing them to a Screen-out page. The response is stored with the status
`screened_out`.

**Secret** — an encrypted, write-only project credential used by connectors
and deposits. → [[Project Settings|Studio-Project-Settings]]

**Share preview** — a public link to the questionnaire valid for 24 hours;
answers are not stored.

**Simulated data** — synthetic respondents generated from the questionnaire,
for building and testing the analysis before fieldwork.

**Skip to** — on a question: when the respondent presses Next on that page
with the question answered, jump to a chosen page.

**Survey host** — `study.siamang.org`, the separate domain that serves
published surveys.

**SurveyData** — the data type that flows between preparation and analysis
nodes: the dataset together with its codebook and questionnaire.

**Template** — a complete questionnaire a new project can start from; Studio
ships twelve, and your organization can save its own.
→ [[Question Bank, Templates and Library|Studio-Question-Bank-and-Library]]

**Theme** — the survey's look and fixed wording, set in **Builder → Theme**.
→ [[Theme and Branding|Studio-Theme-and-Branding]]

**Validation** — the engine's check of a document at every Save. Errors block
publishing; warnings ask for confirmation.
→ [[Testing Your Survey|Studio-Testing-Your-Survey]]

**Variable** — one column of data with its codebook entry. A question's answer
is stored under its variable name, which conditions, piping and quotas read.
→ [[Codebook and Variables|Studio-Codebook-and-Variables]]

**Walkthrough** — taking the survey yourself with a panel that shows which
conditions fired and where you are routed.

**Webhook** — a URL Studio calls when a deployment goes live, fails or is
stopped, or a run completes or fails — for every event, or only the ones you
select. Each call carries a one-line `text` summary, so it can post straight
to Slack. → [[Schedules and Webhooks|Studio-Schedules-and-Webhooks]]

**Weighting** — adjusting respondents to known population shares: **Cell
weights** for one variable, **Rake weights** for several margins. **Apply
weight** then makes the tables (**Frequencies**, **Crosstab**, **Group
means**, **Banner table**), **Net Promoter Score**, **Regression** and **TURF**
after it use the weight; the charts, **Compare groups**, **Correlation** and
several other analyses still compute unweighted.
→ [[Cleaning and Weighting Data|Studio-Cleaning-and-Weighting]]

## See also

- [[Key Concepts|Studio-Key-Concepts]]
- [[FAQ and Troubleshooting|Studio-FAQ-and-Troubleshooting]]
- [[Limits and Quotas at a Glance|Studio-Limits-Reference]]

<!-- studio-nav -->
---

← [[FAQ and Troubleshooting|Studio-FAQ-and-Troubleshooting]] · [Studio contents](Studio-Overview#all-pages)
