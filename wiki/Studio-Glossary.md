# Glossary

The words Siamang Studio uses, in alphabetical order, with a link to the page
that explains each one in full.

---

**Access code** — a code a respondent must enter before the first question
(`PREFIX-NNNN`). Codes are stored in the questionnaire, so generating them
creates a Save; republish the environment to apply them. The check happens in
the respondent's browser: a code can be used any number of times, and the
code a respondent entered is not stored with the response.
→ [[Links, QR Codes, Embeds and Access Control|Studio-Distribution-Channels]]

**Activity** — the audit log: who saved, published, ran, exported or deleted
what, and who renamed the organization, added or removed a webhook, created
or revoked an API key or generated access codes; also sign-ins, password and
name changes, role changes, data and outcome exports, deleted contacts,
closing-date changes and the **One per browser** switch. Per organization
(owners and admins) and per project (all members).
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

**Bands** — a number cut into labelled ranges ("18 to under 30", …) as a new
ordinal variable, by the **Bands** node; missing codes are taken out first and
values outside every band stay blank. → [Bands](Studio-Node-Reference#bands)

**Banner table** — a cross-break: several questions down the page against
several breakdowns across it, with significance letters. For every question
of a study in Excel, see **Tab book**.
→ [Banner table](Studio-Node-Reference#banner-table)

**Block** — a group of questions inside a page, shown, hidden or shuffled
together. → [[The Builder|Studio-Builder-Overview]]

**Branch (next if)** — an ordered list of `condition → page` rules on a page;
the first rule whose condition is true decides where the respondent goes
next. A rule without a condition never fires.
→ [[Logic and Branching|Studio-Logic-and-Branching]]

**Build log** — the log of turning a Save into a published survey, on the
environment's card in Distribute.

**Chart colors** — the colors, text color, grid and typeface a report gives
its charts: part of a **Save report** node's **Look**. A chart takes them
when its **Palette** is `theme`; empty, they are eight colors that readers
with protanopia or deuteranopia can tell apart.
→ [Chart colors](Studio-Reports#chart-colors)

**Closing date** — when an environment stops accepting responses: the
questionnaire's deadline or the environment's `closes_at` (the earlier wins),
or a date set with the **Closing date** chip on its card, which applies at
once without a rebuild. Past it, the card reads **○ Closed** and offers
**Extend**. → [Deadlines](Studio-Publishing-and-Environments#deadlines)

**Cochran's Q** — McNemar's test for three or more yes/no questions put to
the same respondents (brands heard of, channels seen): is the share saying
yes the same for all of them? Followed by a McNemar test of every pair.
→ [Paired tests](Studio-Node-Reference#paired-tests)

**Codebook** — all variables with their scales, labels, value labels, valid
ranges and missing codes; built alongside the questions and exported with the
data. → [[Codebook and Variables|Studio-Codebook-and-Variables]]

**Codeframe** — a saved coding scheme for one open-text question
(`analysis/<name>.codeframe.json`); applied by the **Code open answers** node
without calling any model. → [[Coding Open Answers|Studio-Open-Answer-Coding]]

**Combined report** — the single document **Run all** assembles from every
flow's report. When a flow failed, it is titled "Combined report
(incomplete)" and opens with what is missing. → [[Reports|Studio-Reports]]

**Comment** — a note on a question, page, flow or flow node, visible to the
organization. → [[Working Together|Studio-Collaboration]]

**Completed** — an interview that was submitted and did not end on a
Screen-out page. Completed interviews are what response caps and quota cells
count, and the second total on **Data → Insights** and **Live**.

**Condition** — a rule over earlier answers (`age ≥ 18`, `region in [1, 2]`)
used by show if, hide if, branch rules and the Filter rows node.
→ [[Logic and Branching|Studio-Logic-and-Branching]]

**Conjoint** — a question type that shows whole products side by side and
asks which one the respondent would choose.
→ [[MaxDiff and Conjoint|Studio-MaxDiff-and-Conjoint]]

**Connector** — a configured link that exports a project table to another
system (Sheets, a warehouse, storage, a CRM) or imports one.
→ [[Connectors|Studio-Connectors]]

**Deadline** — a date and time set in the questionnaire (in **Source**) after
which a published environment accepts no more responses; one source of the
environment's **closing date**, shown on its card as **Closes `<date>`**.
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

**Effect size** — how large a difference or relationship is, beside whether
it is significant: Cohen's d and Hedges' g for two means, η² for an ANOVA,
ε² for Kruskal-Wallis, the rank-biserial r for rank tests, Kendall's W for
Friedman's test, Cramér's V for a crosstab.
→ [Node Reference](Studio-Node-Reference#analyze)

**Environment** — a named publishing target (`pilot`, `main`) with its own
permanent link and response cap. → [[Publishing and Environments|Studio-Publishing-and-Environments]]

**Export Python** — downloading the Python the engine generated for the
questionnaire or a flow at a given Save. → [[Reproducibility|Studio-Reproducibility]]

**Factor analysis** — an exploratory analysis of which items of a battery
move together (factors), how strongly each loads on each, and whether the
items share enough to be factored at all (KMO, Bartlett's test). Its
**factor scores** — one variable per factor, `factor_1`, `factor_2`, … — can
be used by later nodes. → [Factor analysis](Studio-Node-Reference#factor-analysis)

**Fisher's exact test** — a test of a crosstab that sums the exact
probabilities instead of the chi-square approximation, for small counts; for
2 × 2 it also gives the odds ratio, for larger tables it is the
Fisher-Freeman-Halton test. A **Crosstab** choice (**Test** `fisher`).
→ [Crosstab](Studio-Node-Reference#crosstab)

**Flow** — an analysis drawn as connected nodes; saved as a document and
generated into a Python script. It can be renamed, duplicated and deleted,
each as a Save of its own. A flow that fails the engine check at Save cannot
run until fixed; the rest of the project is not affected.
→ [[Analysis Flows|Studio-Flows]]

**Frozen workspace** — an organization that support has made read-only. Not
the same as the end of a trial, which moves the organization to the Free plan.

**Gabor-Granger** — a pricing method that asks at each of a set of prices
whether the respondent would buy, and gives the demand, the revenue and the
revenue-maximising price among those asked.
→ [Price sensitivity](Studio-Node-Reference#price-sensitivity)

**House style** — an organization's default survey look (Organization
settings → **Branding**), stamped into each new project; and, separately, a
project's default report look (Project settings → **Reports**).
→ [[Theme and Branding|Studio-Theme-and-Branding]] · [[Reports|Studio-Reports]]

**Id (question)** — a question's own handle in the Builder (**Advanced →
Id**): scripts target it, and the Logic map and validation messages name the
question by it. It may differ from the question's own variable name, but it
must not be another question's variable name — nor, when it differs, a name
the survey stores something else under (a Matrix row, another question's
Other text, an assigned arm).
→ [Question Id and variable name](Studio-Builder-Overview#question-id-and-variable-name)

**Insights** — instant frequencies and crosstabs computed by the server from a
table in **Data**, without a flow. → [[Responses and the Data Tab|Studio-Responses-and-Data]]

**ISO week** — the week of the international standard (ISO 8601): Monday to
Sunday, numbered within its ISO year, week 1 being the week that holds the
year's first Thursday. A **Trend** by **Period** `week` groups the responses
so and labels each point `2026-W22`; the days around New Year can belong to
the neighboring year's week. → [Trend](Studio-Node-Reference#trend)

**Key drivers** — how much of an overall rating each attribute explains: its
share of R² by Johnson's relative weights or the Shapley value, which a
regression's coefficients cannot give when the attributes correlate.
→ [Key drivers](Studio-Node-Reference#key-drivers)

**Likert chart** — a battery of statements on one scale as diverging bars
centred on the neutral answer, each with its top-2 and bottom-2 shares.
→ [Likert chart](Studio-Node-Reference#likert-chart)

**Live tile** — a flow output published to the **Live** screen and, if you
choose, to a public read-only page. → [[Live Monitoring|Studio-Live-Monitoring]]

**Mailing** — an email invitation or reminder sent to a project's contacts,
each with a personal link. → [[Email Invitations|Studio-Email-Invitations]]

**MaxDiff (best–worst)** — a question type that shows a few items at a time
and asks for the best and the worst.
→ [[MaxDiff and Conjoint|Studio-MaxDiff-and-Conjoint]]

**MaxDiff score** — a respondent's own counting score for one MaxDiff item:
best minus worst over the times they were shown it, from −1 to 1; made by the
**MaxDiff scores** node as one variable per item (`q_md_score_1`, …).
→ [MaxDiff scores](Studio-Node-Reference#maxdiff-scores)

**Methods draft** — a Methods section Studio writes from a Save's documents,
with `[...]` where you must fill in. → [[History and Versions|Studio-History-and-Versions]]

**Missing code** — a value that means "no valid answer" (`98 = Don't know`),
declared with its label in the Codebook and exported as a declared missing
value to SPSS and Stata. The tests you choose by hand leave missing codes out
and say how many; a few older defaults count them as answers and say so
("Missing codes counted as answers", or `missing_codes_counted` in
Correlation and Compare groups) until **Missing values** clears them.
→ [Missing codes](Studio-Codebook-and-Variables#missing-codes)

**Node** — one box in a flow: a source, a preparation step, an analysis, a
chart or an output. → [[Node Reference|Studio-Node-Reference]]

**One per browser** — an environment setting (off by default) under which a
browser that has already answered sees "You have already taken part" instead
of the questionnaire. Checked in the browser only; it does not identify
people. → [One response per browser](Studio-Distribution-Channels#one-response-per-browser)

**Ordinal regression** — a regression of an outcome of ordered answers
(dissatisfied … satisfied): the proportional-odds (cumulative logit) model,
with odds ratios above 1 making the higher answers more likely. **Regression**
with **Model** `ordinal`. → [Regression](Studio-Node-Reference#regression)

**Organization** — a workspace owning projects, members, the plan and the
bill. → [[Organizations and Team|Studio-Organizations-and-Team]]

**Other (please specify)** — an answer added with a switch on a single or
multiple choice question. It is stored as the question's Other code (`-66`
unless that code is taken) in the question's column, and the typed text in a
column of its own, `<variable>_other`.
→ [Codes for Other, None of the above and N/A](Studio-Question-Types#codes-for-other-none-of-the-above-and-na)

**p adjustment** — correcting p-values for the number of comparisons made at
once, so that testing many pairs does not turn up "significant" ones by
chance: Holm and Bonferroni (the chance of any false finding) or
Benjamini-Hochberg, `fdr_bh` (the share of false findings among the
significant ones). → [Correlation matrix](Studio-Node-Reference#correlation-matrix)

**Page kind** — what a page does: an ordinary **Content** page, a **Final**
(thank-you) page, a **Screen-out** page or a **Redirect** page.

**Paired test** — a test of answers from the same respondents (before and
after, two brands on one scale): the paired t-test, Wilcoxon signed-rank,
McNemar for yes/no, Friedman for three or more, Cochran's Q for three or more
yes/no. Each respondent is compared with themselves. → [Paired tests](Studio-Node-Reference#paired-tests)

**Panel provider** — a sample company (Prolific, Cint, Dynata, …) that sends
respondents with an id in the link and expects them back on a return URL.
→ [[Panel Providers|Studio-Panel-Providers]]

**Partial** — an interview that was started but not submitted. Stored in the
data (from surveys built with the current runtime); not counted toward caps
or quotas.

**Perceptual map** — a correspondence analysis drawn as a map: brands (or
regions, segments) and attributes (or answers) as points, near each other when
they go together more than chance would have it.
→ [Perceptual map](Studio-Node-Reference#perceptual-map)

**Piping** — inserting an earlier answer into text: `{answer:var}`,
`{label:var}` (or `{var:var}`). → [[Logic and Branching|Studio-Logic-and-Branching]]

**Post-hoc test** — after a test of three or more groups, the comparison of
every pair of groups: Tukey's HSD after an ANOVA, Games-Howell after Welch's
ANOVA, Dunn's test after Kruskal-Wallis. → [Group means](Studio-Node-Reference#group-means)

**Pre-registration** — a tag on one Save marking it as the registered
questionnaire and analysis plan; later Methods drafts and bundles report what
changed since. It does not lock anything.

**Preset** — a question type pre-configured for a common use (Yes / No, NPS,
CES, Attention check, Date, Email, Phone, Rating).
→ [[Question Types|Studio-Question-Types]]

**Preview** — seeing the survey as a respondent will: on the Builder canvas
(unsaved edits), as a preview deployment built from a Save (with the banner
"Preview — answers are not stored"), or through a 24-hour share link.
Answers are never stored, and quotas are not checked.
→ [[Testing Your Survey|Studio-Testing-Your-Survey]]

**Price sensitivity meter (Van Westendorp)** — four price questions (too
cheap, a bargain, getting expensive, too expensive) whose cumulative curves
cross at the price points; the range of acceptable prices lies between the
points of marginal cheapness and marginal expensiveness.
→ [Price sensitivity](Studio-Node-Reference#price-sensitivity)

**Project** — one study: questionnaire, flows, settings, database,
deployments and history. → [[Projects|Studio-Projects]]

**Provenance** — the record of what produced a result: project, Save, data
snapshot and engine version. In every bundle (`PROVENANCE.md`) and, unless
**Settings → Reports** turns the footer off, at the foot of every report.
→ [[Reproducibility|Studio-Reproducibility]]

**Quota cell** — a `variable = value` pair with a limit of completed
interviews. Once full it closes: a later respondent with that answer ends on
the quota-full screen when they leave the page. Screen-outs and partials do
not count. → [[Quotas and Randomization|Studio-Quotas-and-Randomization]]

**Quota-full screen** — where a respondent stopped by a full quota cell (or
arriving at a survey whose response cap is reached) ends: "Thank you for your
interest" / "We have already reached our target sample for participants like
you.", reworded in **Theme → Wording**. The interview is not submitted.

**Report section / Save report** — the flow nodes that assemble a document
from tables, charts and your text; **Save report** can also write the
report's tables to an Excel workbook. → [[Reports|Studio-Reports]]

**Research bundle** — a zip of one Save: generated code, documents, codebook,
Methods draft, citation file, provenance, environment pin and optionally the
responses. → [[Reproducibility|Studio-Reproducibility]]

**Respondent id** — a random identifier kept in the respondent's browser so
an interview can resume; not an identity.

**Response cap** — the number of completed interviews an environment accepts:
its own cap, counted in that environment (new projects: `pilot` 50, `main`
1,200), and on Free the plan's 1,000 per project, counted over all
environments together — the tighter wins. Screen-outs and partials do not
count. → [Response caps](Studio-Publishing-and-Environments#response-caps)

**Result chart** — the chart of an analysis's own result (means with their
intervals, a scree plot, a reach curve, odds ratios, a map, price curves),
drawn from the numbers the analysis computed, so it never disagrees with the
table beside it. → [Result chart](Studio-Node-Reference#result-chart)

**Run** — one execution of a flow (or of all flows) in the sandbox, with a log
and output files. → [[Analysis Flows|Studio-Flows]]

**Run all** — running every flow of the project one after another and
assembling the combined report. Flows run in dependency order (a flow that
reads a table another flow writes comes after it), alphabetically otherwise;
a failed flow skips only the flows that read a table it did not write (one
that ran and only missed its report file skips none).
→ [Run all](Studio-Flows#run-all)

**Run to here** — executing a flow up to the selected node to see its result,
without producing a report or a run-history entry, and without writing any
project table.

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
`screened_out` (the `__status` column); it is not a completed interview, so it
counts toward no response cap or quota cell.

**Secret** — an encrypted, write-only project credential used by connectors
and deposits. → [[Project Settings|Studio-Project-Settings]]

**Share preview** — a public link to the questionnaire valid for 24 hours;
answers are not stored.

**Significance letters** — letters that mark which columns of a table differ:
each column (or each group of a **Bar chart**'s **Split by**) gets a letter,
and a letter beside a percentage names a column whose share of that answer is
significantly lower, by a two-sided z-test of column proportions. Only
columns of the same banner variable are compared, a column under 30
respondents is not tested, and weighted data is tested on Kish's effective
base. The **Banner table**, the **Tab book (Excel)** and the **Bar chart**
use the same test. → [Banner table](Studio-Node-Reference#banner-table)

**Simulated data** — synthetic respondents generated from the questionnaire,
for building and testing the analysis before fieldwork. They follow its
conditions and routing, the arm of **Assign to a condition** and **Randomize
pages**; **Test → Simulate** also applies the quotas, while a flow's
**Simulated data** node does not. → [Simulate](Studio-Testing-Your-Survey#simulate)

**Skip to** — on a question: when the respondent presses Next on that page
with the question answered, jump to a chosen page.

**Survey host** — `study.siamang.org`, the separate domain that serves
published surveys.

**SurveyData** — the data type that flows between preparation and analysis
nodes: the dataset together with its codebook and questionnaire.

**t-test** — a test of whether two means differ: of two groups (Welch's,
which does not assume they vary equally, or Student's), of two answers of the
same respondents (paired), or of one mean against a value (one-sample).
→ [t-test](Studio-Node-Reference#t-test)

**Tab book** — the whole study in one Excel workbook: every question crossed
by a banner of segments (Total, then each gender, each region, …), one sheet
per question with its bases, counts, column percentages and significance
letters, a Contents sheet and a Notes sheet on how it was computed. Written
by the **Tab book (Excel)** node and listed on the **Reports** screen.
→ [Tab book (Excel)](Studio-Node-Reference#tab-book-excel)

**Template** — a complete questionnaire a new project can start from; Studio
ships twelve, and your organization can save its own.
→ [[Question Bank, Templates and Library|Studio-Question-Bank-and-Library]]

**Theme** — the survey's look and fixed wording, set in **Builder → Theme**.
→ [[Theme and Branding|Studio-Theme-and-Branding]]

**Top-2 box** — the share of respondents giving the two highest answers of a
scale (bottom-2: the two lowest); the Likert chart writes both at the ends of
each item's bar, and a **Trend** tracks it when both answers are ticked in its
**Answer codes**. → [Likert chart](Studio-Node-Reference#likert-chart)

**Trend** — a measure over time: the percent choosing an answer, a mean or
the number of respondents, wave by wave or by day, week, month, quarter or
year, a line per group, with each point's confidence band and base.
→ [Trend](Studio-Node-Reference#trend)

**Validation** — the engine's check of a document at every Save. A
questionnaire that fails validation makes the Save `errors`, which blocks
publishing; lint errors and warnings ask for confirmation; a flow that fails
its check cannot run, and blocks nothing else.
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
weight** then makes the nodes after it use the weight — the tables,
**Descriptive statistics**, a Pearson **Correlation** or **Correlation
matrix**, **Net Promoter Score**, **Regression**, **TURF**, **MaxDiff**,
**Conjoint**, **Share of preference**, **Principal components**, **Scale
reliability**, **Key drivers**, **Perceptual map**, **Price sensitivity**, the
**Bar chart**, the **Likert chart**, the **Trend**, the **Tab book (Excel)**
and a **Heatmap** with **By** or with Pearson. **Compare groups**, Spearman and Kendall correlations, the
**t-test**, **Paired tests**, Fisher's exact test, **Factor analysis**,
**Cluster (k-means)**, **Box plot**, **Scatter plot** and a Spearman or
Kendall **Heatmap** stay unweighted and say so in their output; a **Result
chart** follows the result it draws.
→ [[Cleaning and Weighting Data|Studio-Cleaning-and-Weighting]]

## See also

- [[Key Concepts|Studio-Key-Concepts]]
- [[FAQ and Troubleshooting|Studio-FAQ-and-Troubleshooting]]
- [[Limits and Quotas at a Glance|Studio-Limits-Reference]]

<!-- studio-nav -->
---

← [[FAQ and Troubleshooting|Studio-FAQ-and-Troubleshooting]] · [Studio contents](Studio-Overview#all-pages)
