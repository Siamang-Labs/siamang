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
| Straightlining | automatic for questions with 3+ items (Distribute); battery chosen in the node (flows) | **Quality screen** tile; **Response quality** node |
| Speeders | automatic | **Median duration** tile (speeder count); **Speeders & partials** node |
| Captcha | Distribute → **Captcha** chip | `captcha` in `meta`; **Captcha unavailable** quick filter; `captcha` column in flows |
| Tab switches, time away, pastes | automatic | `meta`; columns in flows |
| Contradictions, duplicate patterns | the **Response quality** node | `quality_flags` column |
| Unfinished interviews | automatic | `partial`; **Partial** quick filter; drop-off funnel |

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
   an ordinary branch rule to the page, editable in Logic: it is evaluated when
   the page is left, so respondents finish the page first, and their answers
   are still collected and counted as screened out. If Studio has to create
   the Screen-out page, it adds it at the end of the questionnaire — make sure
   a **Final** page comes before it. Leave the option off to keep everyone and
   decide in the analysis instead.

Rules:

- A check **fails** only when it was answered and the answer differs from the
  expected one. A skipped check is not a failure.
- Matrix and ranking questions cannot be attention checks.
- A new or changed check reaches the field when you save and republish.

---

## During fieldwork: the Distribute tiles

The tiles above the environment cards count quality **while there is still
fieldwork left to change**. They only count — nothing is dropped or stored.

### Quality screen

The share of **completed** responses of the environment that failed an
attention check **or** straightlined:

- **Attention checks**: the questions marked in the Builder, with their
  expected answers.
- **Straightlining**: every question that writes three or more variables (a
  matrix with three or more rows, for example) counts as a battery; a response
  is flat when all items are answered and all answers are identical.

The checks come from the questionnaire **the environment is running**, not
your latest edits. The tile shows the percentage and **`X` of `Y` flagged ·
`2 attention checks · 1 matrix battery`**. With nothing checkable it reads
**add an attention check in Builder** (and **—**) rather than a reassuring
0 %.

These are the same definitions the **Response quality** node uses at its
defaults, so the live number and your analysis agree.

### Median duration and speeders

**Median duration** is the median time from opening the survey to submitting,
over completed responses (`m:ss`). Underneath, **N speeders**: completed
responses faster than **one third of the median**. Until timings arrive the
tile says **timing arrives with responses**.

### Completion and drop-off

**Completion** is completed ÷ all rows (partials included); its subline names
the page where most unfinished interviews stopped. The **Drop-off** chip shows
the whole funnel — see [[Live Monitoring|Studio-Live-Monitoring]].

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
in flows, filter on the `captcha` column. `unavailable` is not proof of a bot —
treat it as one signal among several.

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
In flows they are columns `tab_switches`, `hidden_seconds`, `pastes` (and
`duration_s`), ready for a **Filter rows** node or a crosstab. Studio does not
score them for you: choose thresholds that fit your survey and report them.

---

## In the Data tab

The quick filters of the grid:

| Chip | Shows |
|---|---|
| **Completed** / **Partial** | finished and unfinished interviews |
| **Captcha unavailable** | responses stored without a captcha token |
| **Quality flags** | rows with a non-empty `quality_flags` — in a table a flow wrote after a **Response quality** node |

The chips work on the rows loaded in the grid (the first 100). See
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
  across a battery of at least 5 items; every member of such a group is
  flagged, because which one is the original cannot be known;
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
