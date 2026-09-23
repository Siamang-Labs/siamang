# Recipes

Step-by-step solutions to the tasks people ask about most. Each recipe is the
short path; the linked pages have every option and caveat.

**Contents**

- Questionnaire: [consent page](#a-consent-page-that-screens-out-non-consenters) ·
  [eligibility screener](#an-eligibility-screener) ·
  [follow-up for some respondents](#a-follow-up-question-for-some-respondents-only) ·
  [attention check](#an-attention-check-that-ends-the-survey) ·
  [NPS](#measure-and-report-nps) ·
  [shuffle options or blocks](#shuffle-answer-options-questions-or-blocks) ·
  [another language](#run-the-survey-in-another-language) ·
  [bring a Qualtrics survey](#move-a-qualtrics-survey-into-studio)
- Fieldwork: [pilot then launch](#pilot-then-launch) ·
  [fix a live survey](#change-a-survey-that-is-already-in-the-field) ·
  [roll back](#roll-back-to-an-earlier-version) ·
  [stop a full quota cell](#stop-a-quota-cell-that-is-full) ·
  [Prolific](#field-a-study-on-prolific) ·
  [email invitations](#invite-a-list-by-email-and-remind-non-responders) ·
  [invited participants only](#restrict-the-survey-to-invited-participants) ·
  [embed](#embed-the-survey-in-your-website)
- Data and analysis: [erasure request](#handle-a-data-erasure-request) ·
  [SPSS / Stata / R](#get-labeled-data-into-spss-stata-or-r) ·
  [weighted table](#a-weighted-table-with-significance-tests) ·
  [banner table](#a-banner-table-for-a-client-deck) ·
  [clean once, reuse](#clean-once-and-reuse-the-clean-data-in-several-flows) ·
  [open answers](#code-open-ended-answers) ·
  [nightly report](#a-nightly-report-on-a-schedule) ·
  [client dashboard](#a-live-dashboard-for-a-client) ·
  [Google Sheets](#keep-a-google-sheet-in-sync)
- Keeping it: [pre-register and cite](#pre-register-and-get-a-doi) ·
  [reproduce on a laptop](#reproduce-the-study-on-your-own-computer)

> **Names in these recipes.** Conditions, piping, quotas and your data use a
> question's **variable name** (`consent`, `nps`). When a recipe says "rename
> the variable", type the new name in the Inspector's **Variable** card. The
> question's **Id** (Inspector → **Advanced**) may stay as Studio numbered it;
> setting it to the same name makes the Logic map and validation messages,
> which name questions by Id, easier to read. Rename variables **before** you
> write conditions on them —
> renaming does not update conditions that already use the old name. See
> [Question Id and variable name](Studio-Builder-Overview#question-id-and-variable-name).

---

## Questionnaire

### A consent page that screens out non-consenters

1. On the first page add **+ Question → Presets → Yes / No** — *Do you agree
   to take part?* — and turn **Required** on. Rename the variable to
   `consent`.
2. Put the information text in the question's **Hint** (a page's Body is not
   shown on pages with questions).
3. **+ Page → Screen-out page** (Studio names it `disqualification`); write a
   polite message in its **Body**. Drag it to the end of the page list,
   **after** a Final page (add one with **+ Page → Final page** if you have
   none): pages run in order, so everyone who passes stops at the Final page
   and only the rule below reaches the Screen-out page.
4. Select the consent page → **Logic → Branch (next if) → + Rule** →
   **Add condition**: `consent` **=** **No (0)** → **Done**; target
   `disqualification`.
5. **Test → Walkthrough** — answer **No** and confirm you land on the
   screen-out page.

The Pilot study template starts with this pattern.
→ [[Logic and Branching|Studio-Logic-and-Branching]]

### An eligibility screener

Put the screening questions on their own page, then one **Branch (next if)**
rule per exclusion, each pointing to the Screen-out page — for example
`age` **<** `18`, then `employment` **in** `[5, 6]`. The first rule that
matches wins; everyone else continues to the next page. Screened-out
interviews are stored with the status `screened_out` and count toward the
environment's response cap.

### A follow-up question for some respondents only

Select the follow-up question → **Logic → Show if → Add condition** — for
example `nps` **≤** `6`. To mention the earlier answer, pipe it into the text:
*You gave us {answer:nps} out of 10 — what should we improve?* Use
`{label:region}` for the label of a choice instead of its code. Check the
**Logic map → Questions** lens: an arc drawn upward in red means the
condition reads an answer the respondent has not given yet.

### An attention check that ends the survey

1. **+ Question → Presets → Attention check** (a required single choice,
   already marked, with its expected answer). Rename the variable to
   `attention`.
2. In the Inspector, tick **Also end the survey for respondents who fail** —
   Studio adds a branch rule from the check's page to the first Screen-out
   page. If there is none, Studio creates one and places it directly
   **before** the first Final (or Redirect) page, adding a Final page after
   your last content page when there is none.
3. **Check the page order.** Pages run in order, so a Screen-out page placed
   in front of the Final page is where respondents who **pass** the check end
   up too — recorded as screened out. Drag the Screen-out page **below** the
   Final page in the page rail (the rule follows it by name), as in
   [Screening people out](Studio-Logic-and-Branching#screening-people-out).
   If the project started from a template with a consent page, its
   `screen_out` page is visible only to people who decline consent, and the rule
   points at it. Add a Screen-out page of your own below the Final page, then
   set the rule's target to it in the page's **Logic** section.
   Confirm with **Test → Walkthrough** twice: once answering the check
   correctly, once failing it.
4. To flag rather than exclude, leave that box off and use the **Response
   quality** node in your flow (**Fill from the questionnaire** picks up the
   check).

→ [[Data Quality|Studio-Data-Quality]]

### Measure and report NPS

1. **+ Question → Presets → NPS (0–10)**; rename the variable to `nps`.
2. Optionally add an **Open text** follow-up shown if `nps` **≤** `6`.
3. In a flow: source → **Net Promoter Score** (**0–10 item** `nps`) — the
   score (promoters minus detractors) with a confidence interval. Connect its
   `table` to a **Report section**, or its output to a **Live tile**.

### Shuffle answer options, questions or blocks

- Options: select the question → **Randomize option order** (Single choice,
  Multiple choice, Ranking). Only an **Other (please specify)** option stays
  last; "None of the above" is shuffled with the rest.
- Questions inside a block: select the block → **Randomize question order**.
- Blocks on a page: select the page → **Randomize block order**.
- Pages: **More ▾ → Scripts → Randomize pages**. It keeps the **first** and
  the **last** page in place, and every **Final**, **Screen-out** and
  **Redirect** page wherever it sits, and shuffles the other pages among the
  remaining positions.
- **More ▾ → Randomization** lists every shuffle in one table.

→ [[Quotas and Randomization|Studio-Quotas-and-Randomization]]

### Run the survey in another language

One questionnaire is one language. Write the question texts, options and page
texts in the target language, then **More ▾ → Theme → Wording** and replace
the runtime's fixed phrases (buttons, saving and failure messages). A few
runtime texts are still English only — see
[[Theme and Branding|Studio-Theme-and-Branding]]. For several languages, use
one project per language.

### Move a Qualtrics survey into Studio

1. In Qualtrics: **Tools → Import/Export → Export survey** (`.qsf`).
2. In Studio: **Builder → More ▾ → Import**, drop the file, read the **Not
   imported** list, press **Check with the engine**, then **Import**.
3. Review the variable names — they become your data columns and the names
   conditions read — recreate anything listed as not imported (embedded data,
   quotas, loop & merge are not carried), **Save**.

→ [[Importing Questionnaires|Studio-Importing-Questionnaires]]

---

## Fieldwork

### Pilot, then launch

1. **Distribute → Publish** panel: **Target** `pilot` → **Publish to pilot**.
   Send the link to a few colleagues.
2. Check **Data**, fix in the Builder, **Save**, press **Republish #N** on the
   pilot card; repeat until clean.
3. **Target** `main` → **Publish to main**. The `main` link stays the same for
   the whole study.

New projects cap `pilot` at 50 and `main` at 1,200 completed responses.
→ [[Publishing and Environments|Studio-Publishing-and-Environments]]

### Change a survey that is already in the field

Safe mid-field: typo fixes, new questions at the end, theme colors. Risky:
renaming variables, changing option codes, removing questions — your data will
have two shapes. Edit, **Save**, then **Republish #N** on the card and read the
warning ("The live field switches from Save #X to #N mid-collection…").
Responses record the environment, not the Save, so note the switch time — the
project **Activity** log records every publish.

### Roll back to an earlier version

**History** → open the Save that worked → **Deploy** → choose the environment
→ **Deploy #N**. The link and the responses stay; only the questionnaire
changes. Your working version in the Builder is untouched. To make the old
version the one you edit, use **Restore** instead.
→ [[History and Versions|Studio-History-and-Versions]]

### Stop a quota cell that is full

Quota cells are counted but do not close by themselves. When
`region=1 · 100/100` on the Distribute card:

1. Select the page that asks `region` → add a **Branch (next if)** rule
   `region` **=** **North (1)** → the Screen-out page (or a page telling them
   the group is full).
2. **Save** and **Republish #N**.

For an overall target, the environment's response cap is enforced
automatically. → [[Quotas and Randomization|Studio-Quotas-and-Randomization]]

### Field a study on Prolific

1. **Distribute** → your `main` card → **Panel** chip → **Provider**
   **Prolific**. The id parameter becomes `PROLIFIC_PID`.
2. Copy **Entry link for the provider** into the Prolific study's URL.
3. In the three return URLs, replace `<COMPLETION_CODE>`, `<SCREENOUT_CODE>`
   and `<QUOTA_FULL_CODE>` with the codes from your Prolific study page.
4. **Save panel setup**, then republish `main`.
5. When fieldwork ends, reconcile with **Outcomes · reconcile with the
   provider** (completed / screened out / partial CSVs).

→ [[Panel Providers|Studio-Panel-Providers]]

### Invite a list by email and remind non-responders

*(Plus and above, after the first payment.)*

1. Publish the environment you will invite to.
2. **Distribute → Email invitations → Import contacts**: paste one per line
   (`ada@example.com`, `Ada Lovelace <ada@example.com>`, or a CSV with an
   `email` column); tick the consent confirmation; **Import**.
3. **New mailing**: subject, message containing `{link}` (and `{name}` if you
   have names), your **From name** and **Reply-to**; check the preview; **Send
   to N**.
4. Three to five days later, press **Remind** on that mailing row — it goes
   only to invitees who have not completed.

→ [[Email Invitations|Studio-Email-Invitations]]

### Restrict the survey to invited participants

**Distribute** → card → **Access codes** → **Generate codes** (how many,
prefix) — Studio saves a new version; republish the environment. **Export
CSV** gives you the codes to hand out. The check runs in the respondent's
browser and codes can be reused, so treat it as a light gate. For per-person
tracking use email invitations. → [[Links, QR Codes, Embeds and Access Control|Studio-Distribution-Channels]]

### Embed the survey in your website

**Distribute** → card → **Embed** → copy the **Inline frame** snippet (or the
script version) into your page. Both show the survey in a 720-pixel-high frame;
set the height to suit your page.

---

## Data and analysis

### Handle a data erasure request

1. Find the response. The respondent's thank-you screen showed a **Response
   ID** — that is the `id` column. Otherwise search by a panel id or an
   invitation in the `meta` column.
2. **Data → responses**: type the id in **Filter loaded rows…** and press
   **Delete** on the row, confirm. Only owners and admins see the **Delete**
   button.
3. The grid loads the **newest** 100 rows of the table. If the response is
   older than that, an owner or admin can delete it with the API
   (`DELETE /projects/{id}/database/responses/{response_id}`) — see
   [[API and API Keys|Studio-API-and-API-Keys]].
4. The deletion is recorded in the Activity log (without its content) — keep
   that as your evidence. Quota counts are not reduced.

→ [[Responses and the Data Tab|Studio-Responses-and-Data]]

### Get labeled data into SPSS, Stata or R

- SPSS: **Data → responses → Export ▾ → SPSS** — variable labels, value labels
  and declared missing values from the current Save.
- Stata: **Builder → Test → Simulate** downloads `.dta` for simulated data; for
  real data use the API (`…/export?format=dta`) or a flow's **Export file**
  node with a `.dta` path.
- R: read the `.sav` with `haven::read_sav()` (labels kept), or export
  **Parquet** for a type-faithful table.

Exports contain every row of the table — all environments and partial
interviews; filter on `survey_id` and `partial`. → [[Data Exports|Studio-Data-Exports]]

### A weighted table with significance tests

In a flow: **Responses** → **Rake weights** (targets such as
`{"region": {"1": 0.45, "2": 0.30, "3": 0.25}}`) → **Apply weight** →
**Banner table** (**Questions (down)** `satisfaction`, **Breakdowns (across)**
`region`, **Significance letters** on). The banner shows weighted column
percentages and tests on the effective base.

For a single weighted crosstab, a **Crosstab** node after **Apply weight**
works too: **Rows** `satisfaction`, **Columns** `region`, **Percentages**
`col`. Its cells are sums of weights, and its chi-square test uses the
effective base.

> **Note.** After **Apply weight**, **Frequencies**, **Crosstab**, **Group
> means**, **Banner table**, **Net Promoter Score**, **Regression**, **TURF**
> and **Proportion CI** (with **Weighted** ticked) use the weight. The charts,
> **Compare groups**, **Correlation** and several other analyses (the full
> list is on the linked page) are still unweighted — say so in the report
> section's note.

→ [[Cleaning and Weighting Data|Studio-Cleaning-and-Weighting]]

### A banner table for a client deck

Source → cleaning → **Banner table**: questions down (**Questions**), breakdowns
across (**Breakdowns**), **Significance letters** on. Connect it to a
**Report section**; download the report as HTML. → [[Node Reference|Studio-Node-Reference]]

### Clean once and reuse the clean data in several flows

1. Flow `a_clean`: **Responses** → **Dedup respondents** → **Speeders &
   partials** → **Write table** (`clean`).
2. Flow `b_tables`: **Project table** (`clean`) → your analysis.

**Run all** sees that `b_tables` reads the table `a_clean` writes and runs
`a_clean` first, whatever the names. If `a_clean` fails, `b_tables` is
skipped ("skipped: needs a_clean, which failed") while unrelated flows still
run. Running `b_tables` on its own does not run `a_clean` first — it reads
the table as it was last written. In a downloaded bundle, flows read the
responses file instead of the table — see
[[Reproducibility|Studio-Reproducibility]].

### Code open-ended answers

In a flow, add **Code open answers**, press **Code open answers…**, choose the
open-text question and environment, **Start coding**. Read and rename the
proposed themes, **Save codeframe**, then point the node at it and run. The
answers' text is sent to the AI provider — check your consent wording first.
→ [[Coding Open Answers|Studio-Open-Answer-Coding]]

### A nightly report on a schedule

*(Plus and above.)* **Flows → Schedules → Schedule a run** → **What to run**:
your flow (or all flows) → **When**: **Daily at 02:00** (UTC) → **Schedule**.
Each run replaces the report on **Reports**; owners get an email if a
scheduled run fails. On Free, the button reads **Requires Plus** and opens
the plans instead. → [[Schedules and Webhooks|Studio-Schedules-and-Webhooks]]

### A live dashboard for a client

*(Plus and above.)* Add **Live tile** nodes to a flow (a respondent count with
**Show** `rows`, a crosstab, a chart), tick **Live: recompute on new
responses** in the flow settings, **Save** and **Run** once. On **Live**, press
**Create public link** and send it. **Revoke** it when the engagement ends.
→ [[Live Monitoring|Studio-Live-Monitoring]]

### Keep a Google Sheet in sync

*(Plus and above.)* Create a Google service account, share the sheet with its
`client_email`, then **Settings → Connectors → Google Sheets → + Add**:
**Spreadsheet ID**, **Range**, **Source table** `responses`, and a
**Credentials secret** holding the service-account JSON → **+ Add & Save**.
Press **Run export** whenever you want a refresh (connectors run on demand,
not on a schedule; only owners and admins can run one). →
[[Connectors|Studio-Connectors]]

---

## Keeping it

### Pre-register and get a DOI

1. **Settings → General → Study & citation**: authors (`Name; ORCID;
   affiliation`), license, keywords, abstract → **Save study metadata**.
2. **History** → open the Save you field with → **More ▾ → Pre-register**.
3. Add your Zenodo token under **Settings → Secrets** (owners and admins).
4. **More ▾ → Deposit** → **Zenodo**, pick the token, **untick "Use
   sandbox.zenodo.org"**, tick **Publish immediately** for a DOI now →
   **Deposit**.

→ [[History and Versions|Studio-History-and-Versions]]

### Reproduce the study on your own computer

**History** → open a Save → **More ▾ → Download a bundle → With the responses
so far**, then:

```bash
mkdir my-study && unzip <project>-s<N>-data.zip -d my-study && cd my-study
bash environment/run.sh
```

`run.sh` installs the pinned engine, validates the questionnaire and runs
every flow on the bundled data; reports land in `outputs/`.
→ [[Reproducibility: Code, Bundles and Citation|Studio-Reproducibility]]

## See also

- [[Tutorial: A Study from Start to Finish|Studio-Tutorial-End-to-End]]
- [[FAQ and Troubleshooting|Studio-FAQ-and-Troubleshooting]]
- [[Key Concepts|Studio-Key-Concepts]]

<!-- studio-nav -->
---

← [[Security and Privacy|Studio-Security-and-Privacy]] · [Studio contents](Studio-Overview#all-pages) · [[Limits and Quotas at a Glance|Studio-Limits-Reference]] →
