# Data Quality

Studio helps you spot inattentive, hurried and automated responses at three
moments: while you build (attention checks), while the field is open (the
quality numbers on Distribute, captcha verdicts, behavioral signals) and in
the analysis (the **Speeders & partials** and **Response quality** nodes). The
principle throughout: **flag, don't silently drop** — keep every response,
mark the suspicious ones, and decide in the analysis where the decision is
documented and can be revisited.

---

## At a glance

| Signal | Where you set it up | Where you see it |
|---|---|---|
| Attention checks | Builder → question inspector | Distribute **Quality screen** tile; **Response quality** node |
| Straightlining | automatic for matrices with 3+ rows (Distribute); battery chosen in the node (flows) | **Quality screen** tile; **Response quality** node |
| Speeders | automatic | **Median duration** tile (speeder count); `duration_s` column in exports and flows; **Speeders & partials** node |
| Captcha | Distribute → **Captcha** chip | `captcha` in `meta`; **Captcha unavailable** quick filter; `captcha` column in exports and flows |
| Tab switches, time away, pastes | automatic | `meta`; columns in exports and flows |
| Contradictions, duplicate patterns | the **Response quality** node | `quality_flags` column |
| Unfinished interviews | automatic (surveys built with the current runtime) | `partial`; **Partial** quick filter; drop-off funnel |

---

## Marking attention checks in the Builder

An attention check is an instructed-response item ("to show you are reading
carefully, please choose *Rarely*"). Studio records the answer a reading
respondent gives and compares it later. It is **scored in the analysis, not in
the survey**: a respondent who fails still finishes and is flagged in the
data, where the decision can be re-examined.

### The quick way: the preset

In the Builder's add menu, **Attention check** inserts a ready-made question:
"To show you are reading carefully, please choose “Rarely”." with the options
Never · Rarely · Sometimes · Often · Always, required, with **Rarely** (code 2)
as the expected answer.

### Any question as a check

On a **Single choice**, **Likert scale**, **Number** or **Open text**
question, in the inspector's **Question** section:

1. Check **Attention check** (hint: "scored in the flow, not in the survey").
2. Choose the **Expected answer** (hint: "what a reading respondent gives") —
   from the question's codes, or typed for an open question. Until you do, the
   field warns "Until an answer is set, this question checks nothing."
3. Optionally check **Also end the survey for respondents who fail** (hint:
   "adds a screen-out branch", or "branches to `<page>`" once added). This adds
   an ordinary branch rule to the page, editable in Logic. The inspector
   explains it: "An ordinary page branch, editable in Logic: it is evaluated
   when this page is left, so they finish the page first, and their answers are
   still collected and counted as screened out. Its Screen-out page sits after
   the Final page, so only this branch leads there. Leave it off to keep
   everyone and decide in the analysis instead." (The middle sentence appears
   when it is true.)

Where the Screen-out page goes matters, because pages are shown in order and
an end page reached in order ends the interview. The branch therefore points
at a Screen-out page placed **after** the last **Final** or **Redirect** page,
where nobody arrives by walking forward — so respondents who pass finish
normally and are recorded as completed:

- If such a Screen-out page already exists (with no **Show if** / **Hide if**
  of its own), the branch uses it.
- Otherwise Studio adds one right after the last Final or Redirect page, named
  `disqualification` (`disqualification_2`, … if the name is taken), with the
  title "Thank you" and the body "You do not qualify for this study."
- If nothing ends the survey for everyone (no Final or Redirect page without
  a condition), Studio first adds a **Final** page ("Thank you" / "Thank you
  for taking part.") after your last question page.
- A Screen-out page that only some respondents see — such as the templates'
  consent screen-out — is left to its own job; the check gets a page of its
  own.

**Checks set up before this placement.** A branch saved earlier may point at
a Screen-out page in the running order, or at one with a condition of its own.
The inspector then shows the problem under the checkbox, and Builder →
Validation lists it as "`<question id>`: the screen-out branch for failing this
attention check does not work. …":

| Message | Meaning |
|---|---|
| "Respondents who pass reach “`<page>`” too: it comes after this page with no Final page in between, and pages are shown in order." | people who pass are screened out too |
| "“`<page>`” has a show if or hide if of its own. Where it is hidden, a respondent who fails is sent on to the next page shown after it instead of being screened out." | people who fail are not screened out (in the consent templates they land back at the start) |
| "Skip to on `<question id>` is checked before branch rules, so for anyone who answers `<question id>` this branch never fires." | a **Skip to** on the same page wins; change the routing by hand |

The first two come with a **Fix the branch** button: it moves the old
Screen-out page (keeping its wording) behind the last Final or Redirect page —
or adds a new one, leaving a conditional page to its own job — adding a Final
page first if none ends the survey, and points the branch at it. Save and
republish afterward, and walk the survey once as a respondent who passes. See
[Attention checks](Studio-Logic-and-Branching#attention-checks) and
[Screening people out](Studio-Logic-and-Branching#screening-people-out).

Rules:

- A check **fails** only when it was answered and the answer differs from the
  expected one. A skipped check is not a failure, and the screen-out branch
  never fires for it. (In a survey published before the current runtime, a
  respondent who skipped an optional **Number** or **Open text** check was
  screened out by the branch; republish to apply the rule above.)
- Only **Single choice**, **Likert scale**, **Number** and **Open text**
  questions can be attention checks; matrix and ranking questions cannot.
- A new or changed check reaches the field when you save and republish.

---

## During fieldwork: the Distribute tiles

The tiles above the environment cards count quality **while there is still
fieldwork left to change**. They only count — nothing is dropped or stored.

### Quality screen

The share of **submitted** responses of the environment (screen-outs included,
partial interviews not) that failed an attention check **or** straightlined:

- **Attention checks**: the questions marked in the Builder, with their
  expected answers.
- **Straightlining**: every **Matrix** with three or more rows counts as a
  battery; a response is flat when all rows are answered and all answers are
  identical. A Multiple choice in the wide layout also writes one variable per
  choice, but it is not a battery — checking every option is not
  straightlining.

The checks come from the questionnaire **the environment is running**, not
your latest edits. The tile shows the percentage and **`X` of `Y` flagged ·
`2 attention checks · 1 matrix battery`**. With nothing checkable it reads
**add an attention check in Builder** (and **—**) rather than a reassuring
0 %.

Straightlining is found in matrix rows whichever survey build collected them:
rows stored the current way, one variable per row, and rows an older build
stored together under the question. (An older build stored a matrix answer as
the column's position rather than its code; for "all answers identical" that
makes no difference.)

These are the same definitions the **Response quality** node uses at its
defaults, so the live number and your analysis agree.

### Median duration and speeders

**Median duration** is the median time from opening the survey to submitting,
over submitted responses, screen-outs included (`m:ss`). Underneath, **N
speeders**: submitted responses faster than **one third of the median**. Until
timings arrive the tile says **timing arrives with responses**.

### Completion and drop-off

**Completion** is submitted interviews ÷ all rows (partials included); its
subline names the page where most unfinished interviews stopped. The
**Drop-off** chip shows the whole funnel — see
[[Live Monitoring|Studio-Live-Monitoring]]. Unfinished interviews arrive only
from a survey built with the current runtime; for an environment published
earlier, **Completion** reads 100 % and the funnel stays empty until you
[republish](Studio-Publishing-and-Environments#republishing) it.

---

## Captcha verdicts

With the [captcha](Studio-Distribution-Channels#captcha) on, every stored
response carries a verdict in `meta`:

| `captcha` | Meaning |
|---|---|
| `pass` | a valid token arrived |
| `unavailable` | no token (blocked by an extension, a proxy or the network), or the check service could not be reached — the response was kept |

Forged or replayed tokens are refused and never stored. In the Data tab, the
**Captcha unavailable** quick filter shows the kept-without-token responses;
in an export or a flow, filter on the `captcha` column. `unavailable` is not
proof of a bot — treat it as one signal among several.

---

## Behavioral signals

Every response records three counts in `meta` — never content:

| Signal | Meaning |
|---|---|
| `tab_switches` | how often the respondent left the survey's tab |
| `hidden_seconds` | total seconds the tab was in the background |
| `pastes` | how many times they pasted into the survey |

With `duration_seconds` they tell a respondent who answered in one sitting
from one who had the questions open in another tab — or pasted open answers.
In Data exports and in flows they are columns `tab_switches`,
`hidden_seconds`, `pastes` (and `duration_s`), ready for a **Filter rows**
node, a crosstab or your own statistics package. Studio does not score them
for you: choose thresholds that fit your survey and report them.

---

## In the Data tab

The quick filters of the grid:

| Chip | Shows |
|---|---|
| **Completed** / **Partial** | finished and unfinished interviews |
| **Captcha unavailable** | responses stored without a captcha token |
| **Quality flags** | rows with a non-empty `quality_flags` — in a table a flow wrote after a **Response quality** node |

The chips work on the rows loaded in the grid — the 100 newest, or the rows a
whole-table search found (type in the filter and press `Enter`). **Completed**
keeps screen-outs too. See
[[Responses and the Data Tab|Studio-Responses-and-Data]].

---

## In a flow

### Speeders & partials

**Speeders & partials** adds `duration_s` and `partial` columns and **drops**
responses that were too fast or incomplete:

| Parameter | Default | Meaning |
|---|---|---|
| **Minimum seconds** | 60 | responses faster than this are dropped |
| **Required answers** | none | variables a response must have to count as complete |
| **Drop partials** | on | also drop incomplete responses |

Note the two speeder definitions: the Distribute tile uses *faster than a
third of the median*; this node uses a fixed **Minimum seconds**. Set the node
to the threshold you will report.

### Response quality

**Response quality** marks — and by default keeps — responses that fail up to
four checks:

| Parameter | Meaning |
|---|---|
| **Battery to check** | a matrix or battery of same-scale items; straightlining and duplicate patterns are measured across it |
| **Duplicates also match on** | other answers a duplicate must repeat as well as the battery — age, gender and a few questions of the respondent's own; empty, the battery alone decides |
| **Answers that must agree** | pairs `left variable: right variable`; answering them differently is a contradiction |
| **Attention checks** | `variable: expected answer`. **Fill from the questionnaire (N marked)** copies the checks marked in the Builder |
| **Straightlining tolerance** | the spread across the battery at or below which a response counts as flat; `0` (default) means identical answers |
| **Mode** | **flag** (default) adds the columns and keeps everyone; **drop** also removes flagged responses |
| **Flags column** / **Score column** | names of the two new columns, `quality_flags` and `quality_score` by default |

What the checks mean:

- **straightlining** — all battery items answered, spread within the
  tolerance (a battery needs at least 3 items);
- **inconsistency** — a pair answered differently (both answered);
- **duplicate** — the same complete answer pattern as another respondent
  across a battery of at least 5 items, and the same answers to the
  **Duplicates also match on** questions (two unanswered ones match); every
  member of such a group is flagged, because which one is the original cannot
  be known. A flat pattern — the same answer all the way down — is
  straightlining, never a duplicate: two straightliners of one column match
  whoever they are. Two honest respondents can answer a battery alike now and
  then; the more answers a duplicate must share, the surer the match;
- **attention** — an attention check answered with anything but the expected
  answer.

`quality_flags` names every failed check, joined with `; ` (e.g.
`straightlining; duplicate`); `quality_score` counts them (0 = clean). The node
also outputs a table with the count per reason, an "Any check" total and the
clean remainder as shares of everyone screened — computed before anything is
dropped, and ready for a report section.

Details of every parameter: [[Node Reference|Studio-Node-Reference]].
Where these nodes fit in a cleaning flow:
[[Cleaning and Weighting Data|Studio-Cleaning-and-Weighting]].

> **In the example study.** The flow `cleaning` of a project started from
> the [example study](Studio-Projects#the-example-study) runs both nodes on
> the sample responses: **Speeders & partials** with **Minimum seconds**
> `240`, and **Response quality** in **drop** mode over the eleven statements
> of its two matrices, with the age group asked checked against the age
> typed (cut into the same groups by **Bands**), the attention check among
> the phone statements, and **Duplicates also match on** age, gender, area,
> employment, life satisfaction and hours on screens. The sample has all four
> problems planted, among them interviews submitted twice. Its report, *Data
> quality*, gives the table of failed checks with *Screened* and *Clean*
> under it — the numbers to report (see [Reporting exclusions](#reporting-exclusions)).

---

## A recommended workflow

1. **Build:** add one or two attention checks (the preset is enough) and keep
   **Also end the survey for respondents who fail** off.
2. **Before launch:** turn on the captcha if the link will be public.
3. **Pilot:** publish to `pilot`, watch **Quality screen**, **Median
   duration** and the drop-off funnel. A high failure rate usually means a
   confusing check or a page that is too long, not bad respondents.
4. **Fieldwork:** check the tiles daily; pause if something is clearly wrong.
5. **Analysis:** start the flow with **Response quality** in **flag** mode and
   **Speeders & partials** with a threshold you can justify; write the flagged
   table with **Write table** so you can inspect it in Data with the **Quality
   flags** chip.
6. **Decide and document:** filter in the flow, not by deleting responses, so
   the rule is visible in the node, in the downloaded `.py` and in the Methods
   text.

### Reporting exclusions

Report the counts before exclusion (the **Response quality** table), the rule
you applied, and the number of responses left. "3.2 % of responses failed the
attention check and were excluded" is a statement a reader can check; "we
removed the suspicious ones" is not.

## See also

- [[Cleaning and Weighting Data|Studio-Cleaning-and-Weighting]]
- [[Node Reference|Studio-Node-Reference]]
- [[Live Monitoring|Studio-Live-Monitoring]]
- [[Responses and the Data Tab|Studio-Responses-and-Data]]
- [[Links, QR Codes, Embeds and Access Control|Studio-Distribution-Channels]]

<!-- studio-nav -->
---

← [[Data Exports|Studio-Data-Exports]] · [Studio contents](Studio-Overview#all-pages) · [[Analysis Flows|Studio-Flows]] →
