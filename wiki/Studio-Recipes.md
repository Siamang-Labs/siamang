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
  [closing date](#set-or-extend-a-closing-date) ·
  [quota cells](#close-quota-cells-when-they-are-full) ·
  [one response per browser](#accept-one-response-per-browser) ·
  [Prolific](#field-a-study-on-prolific) ·
  [email invitations](#invite-a-list-by-email-and-remind-non-responders) ·
  [invited participants only](#restrict-the-survey-to-invited-participants) ·
  [embed](#embed-the-survey-in-your-website)
- Data and analysis: [erasure request](#handle-a-data-erasure-request) ·
  [SPSS / Stata / R](#get-labeled-data-into-spss-stata-or-r) ·
  [weighted table](#a-weighted-table-with-significance-tests) ·
  [banner table](#a-banner-table-for-a-client-deck) ·
  [tab book](#a-tab-book-for-the-client) ·
  [correlations](#pearson-or-kendall-correlations-and-a-correlation-matrix) ·
  [Welch's t-test](#compare-two-groups-with-welchs-t-test) ·
  [ANOVA with post-hoc](#an-anova-with-post-hoc-comparisons) ·
  [before and after](#compare-before-and-after-in-the-same-respondents) ·
  [factor analysis](#exploratory-factor-analysis-with-scores) ·
  [MaxDiff scores in a crosstab](#maxdiff-scores-per-respondent-in-a-crosstab) ·
  [100 % stacked bars by segment](#a-100--stacked-bar-of-a-question-by-segment) ·
  [Likert battery chart](#a-likert-battery-chart) ·
  [significance letters on a bar chart](#a-bar-chart-with-significance-letters) ·
  [histogram](#a-histogram) ·
  [monthly trend by segment](#a-monthly-tracking-trend-by-segment) ·
  [brand colors in charts](#brand-colors-in-charts) ·
  [chart a MaxDiff or TURF result](#chart-a-maxdiff-or-turf-result) ·
  [key drivers](#a-key-driver-analysis) ·
  [perceptual map](#a-perceptual-map) ·
  [Van Westendorp](#a-van-westendorp-study) ·
  [ordinal regression](#an-ordinal-regression) ·
  [export for R](#export-the-cleaned-data-for-r) ·
  [clean once, reuse](#clean-once-and-reuse-the-clean-data-in-several-flows) ·
  [rename or delete a flow](#rename-duplicate-or-delete-a-flow) ·
  [analyze an uploaded file](#analyze-a-file-you-uploaded) ·
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
> which name questions by Id, easier to read. Renaming a variable updates the
> conditions, branch rules, quotas, piped text and scripts that already use
> it, but not your flows — and once the survey is in the field, answers
> collected after you publish again land in a column with the new name. So
> rename **before** fieldwork and before you build flows. See
> [Question Id and variable name](Studio-Builder-Overview#question-id-and-variable-name).

---

## Questionnaire

### A consent page that screens out non-consenters

1. On the first page add **+ Question → Presets → Yes / No** — *Do you agree
   to take part?* — and turn **Required** on. Rename the variable to
   `consent`.
2. Put the information text in the page's **Body**: it is shown above the
   question, as HTML.
3. **+ Page → Screen-out page** (Studio names it `disqualification`); write a
   polite message in its **Body**. Drag it to the end of the page list,
   **after** a Final page (add one with **+ Page → Final page** if you have
   none): pages run in order, so everyone who passes stops at the Final page
   and only the rule below reaches the Screen-out page.
4. Select the consent page → **Logic → Branch (next if) → + Rule**. The
   draft rule opens on `consent` **=**: pick **No (0)**, set the target to
   `disqualification`, press **Add rule**.
5. **Test → Walkthrough** — answer **No** and confirm you land on the
   screen-out page.

The templates that ask for consent (**Pilot study** among them) use a
variant: a Screen-out page `screen_out` right after the consent page, with
**Show if** `consent = 0`, so only people who decline ever see it. Both
patterns work.
→ [[Logic and Branching|Studio-Logic-and-Branching]]

### An eligibility screener

Put the screening questions on their own page, then one **Branch (next if)**
rule per exclusion, each pointing to the Screen-out page — for example
`age` **<** `18`, then `employment` **in** `[5, 6]`. The first rule that
matches wins; everyone else continues to the next page. Screened-out
interviews are stored with the status `screened_out` (the `__status` column
in Data). They do not count toward the environment's response cap or any
quota cell, and they are still recorded when the cap is full, so your
screener numbers stay complete.

### A follow-up question for some respondents only

Select the follow-up question → **Logic → Show if → Add condition** — for
example `nps` **≤** `6`. To mention the earlier answer, pipe it into the text:
*You gave us {answer:nps} out of 10 — what should we improve?* Use
`{label:region}` for the label of a choice instead of its code (a survey
published before `{label:…}` showed labels still shows the code until you
publish it again). Check the
**Logic map → Questions** lens: an arc drawn upward in red means the
condition reads an answer the respondent has not given yet.

### An attention check that ends the survey

1. **+ Question → Presets → Attention check** (a required single choice,
   already marked, with its expected answer). Rename the variable to
   `attention`.
2. In the Inspector, tick **Also end the survey for respondents who fail**
   (the hint then reads "branches to *page*"). Studio adds a branch rule from
   the check's page to a Screen-out page that only this rule leads to: one
   **after the last Final or Redirect page**, so respondents who pass walk on
   to the Final page and are recorded as completed.
   - A Screen-out page without a Show if / Hide if already there is reused.
   - Otherwise Studio adds one right after the last Final or Redirect page,
     named `disqualification` ("Thank you" / "You do not qualify for this
     study." — edit both).
   - If nothing ends the survey for everyone, Studio first adds a Final page
     after your last content page.
   - A consent template's conditional `screen_out` page is left to its own
     job; the rule gets a Screen-out page of its own behind the Final page.
3. Confirm with **Test → Walkthrough** twice: once answering the check
   correctly (you should end on the Final page), once failing it.
4. To flag rather than exclude, leave that box off and use the **Response
   quality** node in your flow (**Fill from the questionnaire** picks up the
   check).

A respondent who leaves an optional check empty is not screened out. In a
questionnaire saved when Studio still put this Screen-out page in front of
the Final page (or pointed the rule at a consent template's `screen_out`),
the Inspector shows why the branch does not work, with **Fix the branch**:
press it, Save, and publish again — see
[Attention checks](Studio-Logic-and-Branching#attention-checks).

→ [[Data Quality|Studio-Data-Quality]]

### Measure and report NPS

1. **+ Question → Presets → NPS (0–10)**; rename the variable to `nps`.
2. Optionally add an **Open text** follow-up shown if `nps` **≤** `6`.
3. In a flow: source → **Net Promoter Score** (**0–10 item** `nps`) — the
   score (promoters minus detractors) with a confidence interval. Connect its
   `table` to a **Report section**, or its output to a **Live tile**.

### Shuffle answer options, questions or blocks

- Options: select the question → **Randomize option order** (Single choice,
  Multiple choice, Ranking). "None of the above", exclusive choices such as
  "None of these" and the Other option keep their places; the other options
  are shuffled around them. (A survey published before this rule keeps
  shuffling them with the rest until you publish it again.)
- Questions inside a block: select the block → **Randomize question order**.
- Blocks on a page: select the page → **Randomize block order**.
- Pages: **More ▾ → Scripts → Randomize pages**. It keeps the **first** and
  the **last** page in place, and every **Final**, **Screen-out** and
  **Redirect** page wherever it sits, and shuffles the other pages among the
  remaining positions. A respondent who resumes a saved interview continues
  in the order they were dealt.
- **More ▾ → Randomization** lists every shuffle in one table.

→ [[Quotas and Randomization|Studio-Quotas-and-Randomization]]

### Run the survey in another language

One questionnaire is one language. Write the question texts, options and page
texts in the target language, then **More ▾ → Theme → Wording** and replace
the runtime's fixed phrases: buttons and section labels ("Welcome", "Section
{n} of {total}", "Final thoughts"), the estimated time, answering hints and
error messages, "Other", "None of the above" and "Not applicable", saving and
failure messages, the completion, screen-out, redirect and quota-full
screens. A few texts are still English only — among them the notices a
published survey shows when it is closed or paused, and labels only screen
readers announce; see [[Theme and Branding|Studio-Theme-and-Branding]].
Publish again after changing the wording. For several languages, use one
project per language.

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

New projects cap `pilot` at 50 and `main` at 1,200 completed interviews
(screen-outs and unfinished interviews do not count); on Free, the project as
a whole stops at 1,000, so pilot interviews use up part of that.
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

### Set or extend a closing date

1. **Distribute** → the environment's card → **Closing date** chip.
2. Pick a date and time (your browser's local time) → **Save date**. The toast
   reads "Collecting until *date*". It applies at once — no new Save, no
   rebuild — and the card shows **Closes *date* · set here**.
3. When the date passes, anyone who opens the link sees "This survey is
   closed", and the card reads **○ Closed** — "Closed — deadline passed
   *date*".
4. To collect again: **Extend** on the card → a later date → **Extend to
   this date**. The card turns back to **● Live**.

**No closing date** removes the date; **Use the Save’s date** goes back to
the questionnaire's deadline or the environment's `closes_at`. To stop right
now, use **Close** instead. A survey published before the closing check ran
as the page opens shows the notice only when someone submits, until you
publish it again.
→ [Deadlines](Studio-Publishing-and-Environments#deadlines)

### Close quota cells when they are full

1. **Builder → Quotas**: in "or one for every value of", pick the variable
   (for example `region`), set the limit, press **Add N cells**. **Save**.
2. Publish (or republish) the environment.

Each cell closes once its limit of **completed** interviews has the value;
screen-outs and unfinished interviews do not count. A later respondent who
gives that answer is stopped when they leave the page, on the quota-full
screen ("Thank you for your interest" / "We have already reached our target
sample for participants like you."); for panel respondents, set **Quota
full → return URL** on the **Panel** chip to send them back. Watch the
fill on the Distribute card (`region=1 · 64/100`). To take more from a full
cell, raise its limit, **Save** and **Republish #N**.

A survey published before quota cells closed lets everyone through until you
publish it again. The environment's response cap is a separate, overall
limit. → [When a cell is full](Studio-Quotas-and-Randomization#when-a-cell-is-full)

### Accept one response per browser

**Distribute** → the environment's card → **One per browser** → **Turn on**.
The toast reads "One response per browser — on for *env*" and the chip "One
per browser · on". From then on, a browser that has sent a response — or
ended on a screen-out or a full quota — sees "You have already taken part"
instead of the questionnaire. No new Save or rebuild is needed, but a survey
published before this option existed needs one republish.

It is checked in the respondent's browser only: a private window, cleared
browser data or another device can answer again, and people sharing one
browser count as one. For one answer per person, use email invitations or a
panel provider's own checks.
→ [One response per browser](Studio-Distribution-Channels#one-response-per-browser)

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
   only to invitees who have not completed, through the invitation or any
   earlier reminder, so you can send a second reminder safely. The
   **Completed** column counts completions via reminders under the total
   ("+N via reminders").

→ [[Email Invitations|Studio-Email-Invitations]]

### Restrict the survey to invited participants

**Distribute** → card → **Access codes** → **Generate codes** (how many,
prefix) — Studio saves a new version; republish the environment. **Export
CSV** gives you the codes to hand out. The check runs in the respondent's
browser, a code can be used any number of times, and the code a respondent
entered is not stored with the response, so treat it as a light gate. For
per-person tracking use email invitations. → [[Links, QR Codes, Embeds and Access Control|Studio-Distribution-Channels]]

### Embed the survey in your website

**Distribute** → card → **Embed**, then copy one of the two snippets into your
page:

- **Script (auto-height)** — the frame grows and shrinks with the survey, so
  visitors never scroll inside your page; it is never shorter than 720 pixels
  (or the `data-height` you put on its `div`). A survey published before
  auto-height existed keeps the minimum height until you publish it again.
- **Inline frame** — a plain frame 720 pixels high; change `height` to suit
  your page.

→ [Embedding the survey](Studio-Distribution-Channels#embedding-the-survey)

---

## Data and analysis

### Handle a data erasure request

1. Find what identifies the response: the **Response ID** the respondent's
   thank-you screen showed (the `id` column), their panel id or invitation
   token (in the `meta` column), or an answer only they would have given.
2. **Data → responses**: type it in **Filter loaded rows…** and press `Enter`
   (or **Search all rows**). Studio searches **every row** of the table, not
   only the 100 loaded, and the note reads "N rows of the whole table match
   “…”". The search matches any value that *contains* the text, so for an id
   such as `12` check the `id` column of the row you pick.
3. Press **Delete** on the row and confirm. Only owners and admins see the
   **Delete** button.
4. The deletion is permanent. The response counts and any quota cell the
   response filled go down with it. It is recorded in the Activity log
   (without its content) — keep that as your evidence.

→ [[Responses and the Data Tab|Studio-Responses-and-Data]]

### Get labeled data into SPSS, Stata or R

- SPSS: **Data → responses → Export ▾ → SPSS** — variable labels, value labels
  and declared missing values from the current Save.
- Stata: **Data → responses → Export ▾ → Stata** gives a labeled `.dta` the
  same way (and **Builder → Test → Simulate** downloads one for simulated
  data).
- R: read the `.sav` with `haven::read_sav()` (labels kept), or export
  **Parquet** for a type-faithful table. For the data *after* your flow's
  cleaning and weighting, with a script that labels it for you, see
  [Export the cleaned data for R](#export-the-cleaned-data-for-r).

Exports contain every row of the table — all environments, partial
interviews and screen-outs; filter on `survey_id`, `partial` and `__status`.
The answers come in the questionnaire's order, an "Other (please specify)"
answer as the question's Other code plus its text in `<variable>_other`, and
the fieldwork details as columns of their own (`duration_s`, `started_at`,
`url_<name>`, …). → [[Data Exports|Studio-Data-Exports]]

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

> **Note.** After **Apply weight**, **Frequencies**, **Crosstab** (not
> Fisher's exact test), **Group means** (not N or the test),
> **Descriptive statistics**, **Correlation** and **Correlation matrix** with
> Pearson, **Banner table**, **Net Promoter Score**, **Regression**,
> **TURF**, **MaxDiff**, **Conjoint**, **Share of preference**, **Principal
> components**, **Scale reliability**, **Key drivers**, **Perceptual map**
> (not its chi-square test), **Price sensitivity**, the **Bar chart**, a
> **Heatmap** with **By** or with Pearson, the **Likert chart**, the
> **Trend**, the **Tab book (Excel)** and **Proportion CI** (with
> **Weighted** ticked) use the weight.
> **Compare groups**, **Correlation** and **Correlation matrix** with
> Spearman or Kendall, **t-test**, **Paired tests**, **Factor analysis**,
> **Cluster (k-means)**, **Box plot**, **Scatter plot**, a Spearman or
> Kendall **Heatmap**, **Response quality**, **Code open answers** and
> **Data check** stay unweighted and say so in their output ("unweighted (the
> weight '…' is not applied)"); a **Result chart** says whichever its result
> is. See the linked page.

→ [[Cleaning and Weighting Data|Studio-Cleaning-and-Weighting]]

### A banner table for a client deck

Source → cleaning → **Banner table**: questions down (**Questions**), breakdowns
across (**Breakdowns**), **Significance letters** on. Connect it to a
**Report section**; download the report as HTML. For every question of the
study in Excel, use a tab book ([below](#a-tab-book-for-the-client)).
→ [[Node Reference|Studio-Node-Reference]]

### A tab book for the client

Every question of the study by the client's segments, in one Excel file.

1. In a flow, after your cleaning and weighting steps, add **Tab book
   (Excel)** (Output) and connect the data to it.
2. **Banner**: tick the segments — `gender`, `region`, `age_band` (age cut
   into ranges by **Bands**: a banner takes nominal and ordinal variables).
3. **Questions**: leave empty for every nominal, ordinal and multiple-choice
   question (open answers and rankings are left out, with the reason on the
   Contents sheet), or tick the ones the client asked for — a number you
   tick shows its mean.
4. Keep **Percentages** `column`, **Counts** and **Significance letters**
   on; **Path** `outputs/tabbook.xlsx`, or a name of your own
   (`outputs/client_q3.xlsx`).
5. **Save** and **Run**. The preview shows what it would write; the run
   keeps the workbook.
6. On **Reports**, pick **Tab book** and press **Excel** (or download it from
   **Files**).

The workbook opens on a **Contents** sheet linking to a sheet per question;
the **Notes** sheet says how it was computed — the weight, the test, the
minimum base, the missing codes left out. A question with several answers
cannot be a banner variable: **Explode multiple choice** first and use its
0/1 columns. → [Tab book (Excel)](Studio-Node-Reference#tab-book-excel)

### Pearson or Kendall correlations, and a correlation matrix

One pair — in a flow, after your cleaning steps:

1. Add **Correlation** (Analyze): **X** `age`, **Y** `spend_month`,
   **Method** `pearson — Pearson r`.
2. **Run to here**. The statistics give `r`, `p_value`, `n` and the 95 %
   interval `lower` – `upper`.

For two rating scales, choose **Method** `kendall — Kendall tau-b` (or leave
the default, Spearman): rank correlations suit answers on a 1–5 scale, and
tau-b allows for their many ties. Pearson and Kendall leave the codebook's
missing codes out and say how many (`missing_codes`); the default Spearman
counts them as answers unless **Missing values** comes first.

Every pair of several variables:

1. Add **Correlation matrix**: tick the **Variables** (`trust_1` …
   `trust_6`), **Method** `spearman`, **Missing answers** `pairwise`.
2. With many pairs, set **p adjustment** to `holm` (or `fdr_bh`): the stars
   then follow the adjusted p, and the footer says "Holm, over 15 pairs".
3. Connect its `table` to a **Report section**. The **Layout** `matrix`
   prints the lower triangle with `*` p < .05, `**` p < .01, `***` p < .001;
   `pairs` gives one row per pair with p and N — the one to read when N
   differs from pair to pair (the footer's **N** is then a range, `112–194`).

After **Apply weight** a Pearson correlation is weighted, with p on Kish's
effective base; Spearman and Kendall stay unweighted and say so.
→ [Correlation](Studio-Node-Reference#correlation) ·
[Correlation matrix](Studio-Node-Reference#correlation-matrix)

### Compare two groups with Welch's t-test

1. Add **t-test** (Analyze). **Design** is `independent — two groups`.
2. **Variable** `satisfaction_score`, **Groups** `gender`.
3. When **Groups** has more than two answers, pick the two in **Group A**
   (`1 — Male`) and **Group B** (`2 — Female`); with exactly two, leave both
   empty.
4. Leave **Variances** at `welch — Welch's t` — it does not assume the two
   groups vary equally. `student` pools the variances.
5. **Run to here**. The table gives each group's N, mean, SD and SE; the
   footer gives t, df, p, the **Mean difference** (Male − Female) with its
   **95% CI**, **Cohen's d** and **Hedges' g**.

The t-test is unweighted and says so on weighted data. For weighted means
beside the same test, use **Group means** with **Test** `welch` on a grouping
with two values (a filter or a recode can make one). Without Group A and
Group B on a three-group variable the check warns ("Gender has 3 answers (1 =
Male, 2 = Female, 3 = Other); a t-test compares two — name them in Group A and
Group B, unless the data this node reads holds only two of them.") and, unless
a filter upstream leaves two, the run stops with "Gender has 3 groups (1 =
Male, 2 = Female, 3 = Other); a t-test compares two — name them in Group A and
Group B."
→ [t-test](Studio-Node-Reference#t-test)

### An ANOVA with post-hoc comparisons

1. Add **Group means**: **Variable** `spend_month`, **By** `region`.
2. **Test** `anova — one-way ANOVA`, **Post-hoc** `tukey — Tukey HSD`.
3. **Run to here**. The footer gives F, df, p and η², and "Post-hoc = Tukey
   HSD: 1 of 3 pairs differ at p < 0.05"; the table **Post-hoc: Tukey HSD**
   under the means lists every pair of regions with the difference, its 95 %
   interval, q and p.

When the groups' spreads differ, use `welch_anova` with `games_howell`. For
ratings compared as ranks, `kruskal` with `dunn`, whose **Dunn p adjustment**
is `holm` (or `bonferroni`). A post-hoc test that does not follow its test is
refused as you choose it: "Tukey's HSD follows a one-way ANOVA — set Test to
anova, or Post-hoc to none." Connect the node's `table` to a **Report
section**: the post-hoc table goes into the report with it. Means, SDs and
medians are weighted after **Apply weight**; the test and the pairs are not.
→ [Group means](Studio-Node-Reference#group-means)

### Compare before and after in the same respondents

When the same people answered twice — a rating before and after a message,
the same scale about two brands — compare each respondent with themselves:

- **Means:** **t-test** with **Design** `paired — two variables, same
  people`, **Variable** `rating_before`, **Second measurement**
  `rating_after`. The footer gives t, df, p, the mean difference (before −
  after) with its CI, **Cohen's d (d_z)** and the incomplete pairs left out.
- **Ratings as ranks:** **Paired tests**, tick **Variables** `rating_before`
  then `rating_after` (the order you tick them is the order compared: the
  difference is the first minus the second). **Test** `auto` runs the Wilcoxon
  signed-rank test: W+, W-, Z, p and the rank-biserial r.
- **Yes/no answers:** **Paired tests** with **Test** `mcnemar` and **Counts
  as yes (McNemar)** ticked on the yes answer (tick 4 and 5 for a top-two
  box): the % yes of each, the change in points, and p.
- **Three or more** (three concepts rated by everyone): **Paired tests** with
  three **Variables** runs Friedman's test; its `pairs` output has a Wilcoxon
  test for every pair, Holm-adjusted.

A respondent who missed either question is left out of both, and the
codebook's missing codes count as missing; the footer says how many. These
tests are unweighted and say so.
→ [Paired tests](Studio-Node-Reference#paired-tests)

### Exploratory factor analysis with scores

1. Add **Factor analysis**: tick the **Items** of your battery (three or
   more, rated on the same scale).
2. Leave **Factors** empty and set **Number of factors by** to `parallel`
   (or type the number you expect in **Factors**).
3. **Rotation** `promax` when the factors may correlate (they usually do in
   attitudes), `varimax` when they should not. Tick **Sort items by factor**
   and set **Hide loadings below** to `0.3` so the structure reads at a
   glance.
4. **Run to here**. The preview shows the loadings (with each item's
   communality and MSA), the **variance** explained and the factor
   **correlations**; the statistics give **KMO** (below 0.5 comes with a
   warning), Bartlett's test and **Variance explained %**.
5. Tick **Add factor scores**: `factor_1`, `factor_2`, … are added to the
   data. Wire the node's `data` output on — a **Group means** of `factor_1` by
   `region`, a **Regression** on the scores, an **Export file**.

Before averaging a factor's items into a scale, run **Scale reliability** on
them and build it with **Index / scale**. Respondents missing any item are
left out (their scores are blank); the analysis is unweighted and says so.
→ [Factor analysis](Studio-Node-Reference#factor-analysis)

### MaxDiff scores per respondent in a crosstab

The **MaxDiff** node gives one score per item for everyone together. To break
preferences down by segment, give each respondent their own scores first:

1. Add **MaxDiff scores** (Prepare) after the source and pick the question in
   **MaxDiff question**. It adds one variable per item — `q_md_score_1`, … —
   labeled "MaxDiff score: *item*": best minus worst over the times that
   respondent saw the item, from −1 to 1, blank if they never saw it.
2. Mean score by segment: **Group means**, **Variable** `q_md_score_1`,
   **By** `region` (weighted after **Apply weight**).
3. As a crosstab: add **Bands** — **Variable** `q_md_score_1`,
   **Boundaries** `[-1, 0, 1]`, tick **Bands include their upper boundary**,
   **Band labels** `["Not ahead", "Ahead"]`, **New variable** `price_ahead`
   — then **Crosstab**, **Rows** `price_ahead`, **Columns** `region`. "Ahead"
   are the respondents who picked the item as best more often than as worst.

Respondents who never saw the item are blank, so they are in neither band.
→ [MaxDiff scores](Studio-Node-Reference#maxdiff-scores) ·
[[MaxDiff and Conjoint|Studio-MaxDiff-and-Conjoint]]

### A 100 % stacked bar of a question by segment

The chart of a crosstab's column percentages: one bar per segment, each
stacked to 100 %.

1. After your cleaning steps (and **Apply weight**, if the data is weighted),
   add **Bar chart** (Visualize): **Variable** `satisfaction`, **Split by**
   `region`.
2. **Layout** `stacked_100 — stacked to 100 %`. (`grouped` puts each
   region's bars side by side; with **Show** `percent` they are % of the
   region too.)
3. Optional: **Sort** `value` puts the regions with the largest share of the
   top answer first — the answers keep the scale's order — and **Horizontal**
   suits many or long segment names.
4. **Run to here**. Each region's `n` is under its name; under the plot:
   "Base: 385 respondents who answered both. Each group's n is under its
   name." and "Percentages are of each group of Region.", plus the missing
   codes left out ("Left out as missing: …").

On weighted data the percentages are weighted, as the Crosstab's column
percentages are, and the axis reads "% within Region (weighted)".
**Split by** needs one answer per respondent: a multiple-choice question is
refused before the run ("Split by needs one answer per respondent, and …
allows several: draw it as the Variable, or split by one of its options after
Explode multiple choice."). A multiple-choice **Variable** can be split, side
by side only.
→ [Bar chart](Studio-Node-Reference#bar-chart)

### A Likert battery chart

1. Add **Likert chart** (Visualize) and tick the **Items**: statements rated
   on the same scale, such as `trust_acme`, `trust_globex`, `trust_initech`
   (1 = No trust … 5 = Full).
2. Leave **Neutral answer** `split — half on either side`, or choose `side —
   in a panel at the right` to keep the middle answer apart. **Sort items**
   `top2` puts the item with the largest top-2 share first; `listed` keeps
   the order of **Items**.
3. **Run to here**. Each item is a bar centred on the neutral answer, with
   its bottom-2 and top-2 shares at the ends. The title is what the labels
   share ("Trust"), each bar the rest with its base ("Acme (n = 485)"), and
   the notes under the chart say which answers make the top-2 and bottom-2
   and which missing codes were left out.

Items on different scales are refused before the run — "The items of a
Likert chart must share one scale, and these do not: …" — so chart each
scale on its own, or recode the items onto one. Codes run low to high, left
to right: recode a scale written the other way (1 = Strongly agree) first.
After **Apply weight** the shares are weighted.
→ [Likert chart](Studio-Node-Reference#likert-chart)

### A bar chart with significance letters

Which regions are more satisfied than others, marked on the chart the way a
banner table marks it.

1. After your cleaning steps (and **Apply weight**), add **Bar chart**:
   **Variable** `satisfaction`, **Split by** `region`, **Show** `percent`,
   **Layout** `grouped`.
2. Tick **Significance letters**. Leave **Level** at `0.05`; with many
   groups, set **Multiple comparisons** `bonferroni`.
3. Optional: tick **Confidence intervals** for each bar's margin of error.
4. **Run to here**. The regions are lettered under their names —
   `Capital (A)`, `North (B)`, `South (C)` — and a letter over a bar names a
   region whose share of that answer is significantly lower. The note under
   the chart names the test; "No group's share of any answer is significantly
   higher than another's." when nothing differs, and "Not tested, fewer than
   30 respondents who answered: …" for a small group.

The letters are the **Banner table**'s two-sided z-test of column
proportions, on each group's respondents who answered (Kish's effective base
when weighted). A **Tab book** shows the same comparisons, with the letters
its banner gives the columns.
→ [Bar chart](Studio-Node-Reference#bar-chart)

### A histogram

How a number spreads — ages, amounts, minutes.

1. Add **Bar chart**: **Variable** `age` (an interval or ratio variable),
   **Layout** `histogram — histogram of a number, in Bins`.
2. **Bins**: leave `auto` (Freedman and Diaconis's width; whole-number
   answers get a whole width), type a number of bins (`10`), or type the
   edges you report in (`18, 25, 35, 50, 65, 100`).
3. **Show** `percent` for % of those who answered; **Split by** `gender` for
   a panel per group on the same bins.
4. **Run to here**. The note under the chart says how the bins were made
   ("Bins: 11 of width 8 (Freedman–Diaconis), each holding 8 whole
   numbers.").

A histogram of a nominal or ordinal question is refused before the run — draw
its answers as bars. Edges that do not increase are named on the field:
"bins: The bins' edges must increase from one to the next, and 5 is followed
by 3."
→ [Bar chart](Studio-Node-Reference#bar-chart)

### A monthly tracking trend by segment

Satisfaction month by month since launch, a line per segment.

1. After your cleaning steps (and **Apply weight**), add **Trend**
   (Visualize).
2. **Time**: `created_at — Response date (created_at)`, under **Beside the
   answers** (or your wave variable, for a wave-by-wave tracker). **Period**
   `month` (`week` for an ISO week, Monday to Sunday).
3. **Measure** `percent`, **Measure variable** `satisfaction`, **Answer
   codes** `4` and `5` ticked — a top-2 box. (`mean` tracks the average;
   `count` the respondents.)
4. **Split by** `segment`. Keep **Confidence band** on and **Minimum base**
   `30`.
5. **Run to here**. The preview shows the chart and, under it, the table of
   points — each month's percent, its 95 % interval and its base.

Every month from the first to the last is on the axis; a month without
respondents is a gap, and a point under 30 respondents is hollow, without a
band. With more than four segments the bands give way to marker shapes (the
table keeps the intervals). To put it in the report, add the `chart` (and
the `table`, for the numbers) to a **Report section**; for a live dashboard,
connect the `chart` to a **Live tile** (**Kind** `chart`).
→ [Trend](Studio-Node-Reference#trend)

### Brand colors in charts

Draw a report's charts in your brand's colors and typeface.

1. In the flow's **Report** view, open **Look → Chart colors**.
2. **Series**: paste your palette, in order — `#003f5c, #ffa600, #bc5090,
   #58508d` — or pick each swatch. Set **Magnitude** (the hue of an ordered
   scale, light to dark), the two **Diverging** ends (a Likert chart's
   disagree and agree sides), **Chart text** and **Chart typeface**
   (`Inter, sans-serif`) as you like.
3. On each chart node, set **Palette** to `theme — the report's chart colors
   (Save report's Look)` (a **Heatmap**'s **Color map** to `theme`).
4. **Preview report**. The charts are drawn in your colors, in the `.md`'s
   figures and the `.html` alike, and their node previews and Live tiles
   follow.

A color too faint on white, text under 4.5:1 or a color given twice is
refused on the node with the reason. To use the same colors in every flow,
set them in **Settings → Reports → House style** and **Apply to every flow**.
→ [Chart colors](Studio-Reports#chart-colors)

### Chart a MaxDiff or TURF result

A **Result chart** draws an analysis's own table, so the chart in the report
shows the same numbers as the table beside it.

**MaxDiff:**

1. Add **MaxDiff** (Analyze) with your **MaxDiff question**.
2. Add **Result chart** (Visualize) and connect the MaxDiff node's `table` to
   its **result** input.
3. **Kind** `auto` draws the utilities with their 95 % intervals, against
   the reference item at 0. Choose `scores` for the counting scores or
   `shares` for the shares. With **Estimate** `counts` the chart draws the
   scores.

**TURF:**

1. Add **TURF** with the 0/1 **Options** (from **Explode multiple choice**),
   **Largest portfolio** `3`, **Search** `best`.
2. Connect its `table` to a **Result chart**: the reach curve, each portfolio
   size named by the option it adds, with its reach and gain.
3. With **Search** `fixed` and a **Portfolio**, the chart draws each option's
   reach beside what only it reaches, and the whole portfolio's reach.

Put the table and the chart in one report section, at **Half** each to sit
side by side. Under the Result chart's **Kind** the inspector lists what the
connected result suits.
→ [Result chart](Studio-Node-Reference#result-chart) ·
[[MaxDiff and Conjoint|Studio-MaxDiff-and-Conjoint]]

### A key-driver analysis

Which attribute ratings matter most for overall satisfaction?

1. Add **Key drivers** (Analyze): **Outcome** `overall_sat`, **Drivers** the
   attribute ratings (`rate_price`, `rate_service`, `rate_range`,
   `rate_staff`).
2. Leave **Importance** at `relative_weights — Johnson's relative weights`,
   or choose `shapley — Shapley value (LMG)` (at most 15 drivers); the two
   agree closely.
3. **Run to here**. The table ranks the drivers by **% of R²** — together the
   100 % of what the model explains — beside each one's correlation (**r**),
   standardized **Beta** with its p, and **VIF**; the footer gives R²,
   adjusted R², F and p.
4. Connect the `table` to a **Result chart** for the bars, largest first.

Read **Warning** when it appears: a VIF of 10 or more (drivers that overlap
share their importance between them) or a suppressor (a beta whose sign
differs from its correlation). A driver with more than two unordered answers
is refused — make a 0/1 variable per answer with **Explode multiple choice**
or **Derive**. Respondents missing the outcome or any driver are left out
(**Excluded**).
→ [Key drivers](Studio-Node-Reference#key-drivers)

### A perceptual map

Which regions (or segments) go with which brands?

1. Add **Perceptual map** (Analyze): **Table** `crosstab — Rows by Columns`,
   **Rows** `region`, **Columns** `brand_used`.
2. **Run to here**. The first table gives each dimension's share of the
   inertia; the **rows** and **columns** tables give each point's
   coordinates, contribution and quality; the statistics give the chi-square
   test.
3. Connect any of its tables to a **Result chart**: the map. Points that lie
   near each other go together more than chance would have it; each axis
   says how much of the table it shows, and the title how much the map shows
   in all.

For a brand-image grid — which brands are seen as modern, as good value — use
**Table** `attributes`: **Rows** the brand and **Attributes** the 0/1
attribute columns, in data with one row per respondent and brand (bring such
a file in with a **Data file** node); set **Counts as yes (attributes)** when
the attributes are coded other than 0/1. With a question about the respondent
as **Rows** and an exploded multiple-choice question as **Attributes**, the
map shows which regions tick which options.
→ [Perceptual map](Studio-Node-Reference#perceptual-map)

### A Van Westendorp study

1. In the questionnaire, ask four prices as numbers (interval or ratio
   scale): so cheap you would doubt the quality, a bargain, getting
   expensive, too expensive. For the Newton-Miller-Smith extension, also ask
   how likely the respondent would be to buy at their bargain price and at
   their getting-expensive price (1–5, 5 = definitely).
2. In a flow, add **Price sensitivity** (Analyze), **Method**
   `van_westendorp — four price questions`, and choose **Too cheap**,
   **Cheap (a bargain)**, **Expensive (getting expensive)** and **Too
   expensive**. For NMS, choose the two likelihood questions as well; leave
   **Likelihood as probability (NMS)** empty for 5 → 0.7, 4 → 0.5, 3 → 0.3,
   2 → 0.1, 1 → 0.
3. **Run to here**. The table lists the price points — PMC, OPP, IPP, PME,
   and with NMS the prices of the highest trial and revenue — and the
   statistics the **Range of acceptable prices** ("6.4 – 14.34"); the
   **curves** are under it.
4. Connect the `table` to a **Result chart**: the four curves with the
   points named and the acceptable range shaded (with NMS, the trial curve
   below).

Respondents whose four prices are not in order are left out and counted in
**Inconsistent** — many of them suggest a question was misread. For
**Gabor-Granger** (buy or not at set prices), set **Method**
`gabor_granger`, tick one question per price in **Would buy at each price**,
list the prices in the same order in **Prices** (`[4.99, 6.99, 8.99]`) and,
on a likelihood scale, tick the answers that mean would buy in **Counts as
would buy** (4 and 5 for a top-two box).
→ [Price sensitivity](Studio-Node-Reference#price-sensitivity)

### An ordinal regression

For an outcome of ordered answers — very dissatisfied to very satisfied:

1. Add **Regression** (Analyze): **Outcome** `satisfaction` (an ordinal
   variable), **Predictors** `age`, `region`, `trust_acme`.
2. **Model** `ordinal — ordinal logit, ordered answers`.
3. **Run to here**. The table lists each coefficient with its standard
   error, z, p, odds ratio and 95 % interval, then the thresholds between
   neighbouring answers (`Very dissatisfied / Dissatisfied`); the statistics
   give the answers' `order`, `n`, McFadden's `pseudo_r_squared`, the
   likelihood-ratio test (`lr_p`) and `aic`.
4. Connect the `table` to a **Result chart**: the odds ratios with their
   intervals on a log scale, the thresholds left out.

A positive coefficient — an odds ratio above 1 — makes the higher answers
more likely, as in R's `MASS::polr`. The outcome must be ordered: a nominal
one such as a region is refused before the run ("Region is nominal: its
answers (Capital, North, South) have no order, …"); with two answers, use
the logit. The codebook's missing codes are left out and counted
(`missing_codes`), and the model is weighted after **Apply weight**.
→ [Regression](Studio-Node-Reference#regression)

### Export the cleaned data for R

1. End your cleaning flow with **Export file**, **Path** `outputs/clean.R`.
2. **Save changes** and **▶ Run** the flow.
3. The run writes three files, on the run's card and under **Files** as
   `outputs/<flow>/clean.R`, `clean.csv` and `clean.dictionary.json`.
   Download all three into one folder.
4. In R (with the `jsonlite` package installed): `source("clean.R")`. The
   data frame `survey_data` has the codebook's missing codes as `NA`,
   labelled codes as factors and each variable's codebook label as the
   column's `label` attribute.

The export carries what the flow made — recodes, bands, factor scores, the
weight column. `outputs/codebook.json` writes the codebook alone, and
`outputs/clean.sav` a labeled SPSS file that R's `haven` reads.
→ [Export file](Studio-Node-Reference#export-file) ·
[[Data Exports|Studio-Data-Exports]]

### Clean once and reuse the clean data in several flows

1. Flow `a_clean`: **Responses** → **Dedup respondents** → **Speeders &
   partials** → **Write table** (`clean`).
2. Flow `b_tables`: **Project table** (`clean`) → your analysis.

**Run all** sees that `b_tables` reads the table `a_clean` writes and runs
`a_clean` first, whatever the names. If `a_clean` fails, `b_tables` is
skipped ("skipped: needs a_clean, which failed") while unrelated flows still
run. Running `b_tables` on its own does not run `a_clean` first — it reads
the table as it was last written. `b_tables` gets the table's variables with
their labels and value labels, including variables `a_clean` made (a recode,
a derived variable, an index), so its pickers offer them ("from table clean ·
made by a_clean").

**Run to here** in `a_clean` never writes `clean`: only a run does. In a
research bundle made with data, `b_tables` reads `data/tables/clean.csv` —
the table as it was when the bundle was made — and the **Write table** step
does not run there; see [[Reproducibility|Studio-Reproducibility]].

### Rename, duplicate or delete a flow

On **Flows**, open the **⋮** at the end of the flow's row ("More for
*flow*") — or, in the editor, **More ▾**, where the same commands read
**Rename flow…**, **Duplicate flow…** and **Delete flow…** — and choose:

- **Rename…** — type the new name (lower-case letters, digits and `_`,
  starting with a letter) → **Rename**. A new Save stores the flow under the
  new name; its schedules and comments move with it, and Live keeps its
  tiles. Past runs and reports keep the old name. Save your own unsaved
  changes to the flow first — a rename takes the flow as last saved.
- **Duplicate…** — the name offered is `<name>_copy` → **Duplicate**. The
  copy's title gets "(copy)"; schedules are not copied, and the copy counts
  toward your plan's flow cap.
- **Delete…** → **Delete flow**. A new Save removes the flow; its past runs
  and reports stay, and its schedules are paused.

Each is an ordinary Save, so **History → Restore** of an earlier Save brings
a deleted or renamed flow back. A flow a colleague has open cannot be renamed
or deleted until they are done.
→ [Rename, duplicate or delete a flow](Studio-Flows#rename-duplicate-or-delete-a-flow)

### Analyze a file you uploaded

1. **Files → Upload** the data file (for example `panel.csv`).
2. On its row, click the copy icon ("Copy the path a flow reads it by:
   assets/panel.csv").
3. In a flow, add a **Data file** source and paste `assets/panel.csv` into
   **File**, then connect your analysis.

Runs, **Run all** and **Run to here** read the upload directly; a research
bundle made with data brings the uploads its flows name.
→ [[Files|Studio-Files]]

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
scheduled run fails. A schedule never starts a run beside one of the same
flow (or a Run all) that is still going: it fires as soon as that run
finishes. On Free, the button reads **Requires Plus** and opens the plans
instead. → [[Schedules and Webhooks|Studio-Schedules-and-Webhooks]]

### A live dashboard for a client

*(Plus and above.)* Add **Live tile** nodes to a flow (a respondent count with
**Show** `rows`, a crosstab, a chart, a **Trend** of completes per week), tick
**Live: recompute on new responses** in the flow settings, **Save** and
**Run** once. On **Live**, press **Create public link** and send it.
**Revoke** it when the engagement ends.
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
every flow on the bundled data, in the order Studio's **Run all** runs them;
reports land in `outputs/`. Read the bundle's `README.md` first: it says
where the engine comes from — when `requirements.txt` installs it from
GitHub, `run.sh` needs git and network access — and whether that engine can
be older than the one Studio runs, in which case some results may differ.
→ [[Reproducibility: Code, Bundles and Citation|Studio-Reproducibility]]

## See also

- [[Tutorial: A Study from Start to Finish|Studio-Tutorial-End-to-End]]
- [[FAQ and Troubleshooting|Studio-FAQ-and-Troubleshooting]]
- [[Key Concepts|Studio-Key-Concepts]]

<!-- studio-nav -->
---

← [[Security and Privacy|Studio-Security-and-Privacy]] · [Studio contents](Studio-Overview#all-pages) · [[Limits and Quotas at a Glance|Studio-Limits-Reference]] →
