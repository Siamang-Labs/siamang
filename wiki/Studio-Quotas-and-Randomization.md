# Quotas and Randomization

Two Builder tabs that are about the sample rather than the wording.
**Quotas** counts completed responses per cell (region = North, age group =
18–29…). **Randomization** gathers every shuffle in the questionnaire into one
table. This page also covers experimental assignment, which sends each
respondent to one arm of a split-ballot or A/B test.

Both tabs are under **More** in the Builder's tab strip.

---

## Quotas

A **quota cell** is one variable, one value and a limit: `region = 1 (North),
limit 400`. After you publish, Studio counts how many completed responses fall
into each cell and shows the fill on the Distribute card and on Live.

> **Current limitation.** Quota cells are **counted, but they do not screen
> respondents out**. A full cell does not stop anyone and does not send anyone
> to a screen-out page. The only automatic stop is the environment's
> [response cap](Studio-Publishing-and-Environments#response-caps). Plan your
> fieldwork around this; see [Managing quotas today](#managing-quotas-today).
> The Quotas tab's own note ("later respondents are screened out") describes
> the intended behavior, not the current one.

### The Quotas tab

```
A quota closes a cell once limit responses have the target value; …
[+ Add one cell]  │  or one for every value of [ region ▾ ] , limit [ 100 ] each   [Add 4 cells]

Variable        Value                 Limit
[ region ▾ ]    [ North (1)    ▾ ]    [ 400 ]    Remove
[ region ▾ ]    [ Capital (2)  ▾ ]    [ 300 ]    Remove
```

- **Add one cell** (tooltip "Add one empty cell and pick its variable, value
  and limit yourself") adds a row with the first labeled variable, its first
  value and a limit of **100**. Change all three in the row.
- **or one for every value of [variable] , limit [n] each** creates one cell
  per value label of the chosen variable, all with the same limit (default
  100, at least 1). The button says what it will do: **Add N cells**, adding
  only values that have no cell yet. When every value already has one it reads
  **All values covered** (tooltip "Every value of <variable> already has a
  cell").
- The table has **Variable**, **Value** and **Limit** columns, plus
  **Remove**. With no cells it reads "No quotas."
- **Variable** lists only codebook variables **with value labels**: single
  choice, multiple choice, Likert, ranking and similar. Number and open-text
  questions cannot be quota variables here.
- **Value** is a dropdown of `Label (code)`. The cell stores the code.
- **Limit** is a whole number, at least 1.
- The number of cells appears in the Builder's version popover ("N quotas").

When you Save, the engine checks every cell. Each of these marks the Save
**errors** (so it cannot be published) until you fix it:

- "Quota references unknown variable: <name>"
- "Quota on '<variable>' targets value <v>, which is not a defined category (…)"
- "Duplicate quota for '<variable>' value <v>."

These are Save-time checks. The Validation tab's **Check now** does not run
them, but **Source → Check** and every Save do.

### How cells are counted

- Counters exist **per environment**. They are created when you publish: a
  new environment starts at zero, and `pilot` and `main` count separately.
- Republishing an environment keeps its counts and applies the new limits. A
  cell you remove from the questionnaire keeps its old counter in that
  environment.
- A cell counts **completed** responses, once per respondent. Resuming or
  retrying a completed interview does not count it twice. Partial interviews
  do not count.
- **Screen-outs count.** A respondent who reaches a Screen-out or Redirect
  page has submitted a response, so any cell their answers match goes up.
- Counters are **never decremented**. Deleting a response in Data does not
  give its count back.
- The counters live in the project's `quota_counters` table, which you can
  open and export from **Data** (see
  [[Responses and the Data Tab|Studio-Responses-and-Data]]).

> **Current limitation.** A cell on a **multiple-choice** variable never
> fills, because a multiple-choice answer is a list of codes rather than one
> code. Put quotas on single-answer questions.

> **Important.** A cell only counts when the question's **Id** is identical
> to its variable name (Inspector → **Advanced**). See
> [[The Builder|Studio-Builder-Overview]].

### Where to watch the fill

- **Distribute**: each environment card that serves the survey (not preview
  cards) lists **Responses** against the cap, then one row per cell:
  `region=1`, a bar, `112/400`.
- **Live**: the fieldwork monitor shows the same bars (see
  [[Live Monitoring|Studio-Live-Monitoring]]).

### Managing quotas today

Until full cells close by themselves:

1. **Use the environment's response cap for the overall target.** The cap
   refuses submissions once it is reached ("Thank you for your interest — We
   have already reached our target sample for participants like you.") and,
   with a panel set up, sends respondents to the **Quota full** return URL.
   See [Response caps](Studio-Publishing-and-Environments#response-caps).
2. **Watch the bars** on Distribute or Live during fieldwork, especially at
   the start and after each invitation wave.
3. **When a cell fills**, choose one:
   - **Pause** or **close** the environment if the whole study is done (see
     [Pause and resume](Studio-Publishing-and-Environments#pause-and-resume)).
   - **Route the full cell out.** On the page that asks the quota question,
     add a **Branch (next if)** rule "region **=** North (1) **→** your
     Screen-out page", Save, and **republish** the environment. The link and
     the counts stay; new North respondents are screened out from then on. See
     [[Logic and Branching|Studio-Logic-and-Branching]].
   - Tell your panel provider to stop sending that group, if they target it.
4. Put the quota question **early**, ideally on the screener page, so a
   screen-out rule you add later stops people before they spend time on the
   survey.

**Interlocked cells** (region × gender) need one variable whose codes stand
for the combinations, for example a single screener question with one option
per combination. A cell is always one variable and one value, and the tab
generates cells for one variable at a time.

---

## Randomization

**Builder → Randomization** lists every place the questionnaire draws
something at random, so you can review them all before fieldwork.

```
3 of 5 randomizations on. Order switches are the item's own property — …
                                                  ☐ only enabled   [Open Scripts]
Where                          What                          Enabled
page1                          block order (3 blocks)        ☑ on        open
page1 › Brand block            question order (4)            ☐ off       open
page1 › q_brand                option order (8 options)      ☑ on        open
questionnaire                  page order                    ● on        edit in Scripts
condition                      condition assignment (2 arms) ● on        edit in Scripts
```

- The note reads: "**X of Y randomizations on.** Order switches are the
  item's own property — the Inspector edits the same ones. Script rows are
  owned by **Scripts** and shown here read-only. Order never touches the
  codebook or the data; condition assignment writes its arm to a variable."
- **only enabled** hides what is switched off. **Open Scripts** goes to the
  Scripts tab (tooltip "Page order, seeded option order and condition
  assignment live in Scripts").
- The three **order switches** can be ticked here or in the Inspector; it is
  the same setting. **open** selects the item in Structure.
- **Script rows** ("page order", "option order (seedable)", "condition
  assignment (N arms[, balanced by quota])") always read **● on**. Change or
  remove them with **edit in Scripts**.
- Empty states: "Nothing to randomize yet — add a choice question, a block
  with several questions, or a page with several blocks." and, with the
  filter on, "No randomization is enabled."

Shuffles are drawn per respondent when the survey loads. Shuffled order
never changes the stored codes, so your analysis is unaffected. A respondent
who reloads or resumes the survey may get a new order.

### Option order

**Randomize option order** (Inspector → Question, on single choice, multiple
choice and ranking questions; row "option order (N options)") shuffles the
answer options for each respondent.

What stays in place: only **Other (please specify)**, which is always shown
after the options. **"None of the above"** (single choice) and **exclusive**
options (multiple choice) are shuffled together with the rest.

> **Tip.** To shuffle all options but keep the last one ("None of these")
> last, leave the switch off and use a small custom script *(Plus)*. See
> [Shuffle but keep the last option last](Studio-Scripts#shuffle-but-keep-the-last-option-last).

### Question order in a block

**Randomize question order** (Inspector → Block; row "question order (N)")
shuffles the questions inside the block. Only questions inside a block can be
shuffled. To shuffle questions on a page, put them in a block.

### Block order on a page

**Randomize block order** (Inspector → Page, content pages only; row "block
order (N blocks)") shuffles the page's blocks. Questions that sit on the page
outside any block keep their positions; only blocks trade places with each
other.

### Page order

There is no page switch. Add **Scripts → Add script → Randomize pages**
(row "page order").

- The **first** and the **last** page of the questionnaire stay where they
  are. Every page in between is shuffled for each respondent, **end pages
  included**.
- It does nothing unless the questionnaire has **more than 3 pages**.

This matters for end pages. A Final or Screen-out page that is not last can be
shuffled into the middle, and respondents who reach it there end the
interview early. With Randomize pages:

- make the first page your introduction or screener, since it stays first;
- keep at most **one** end page, and make it the last page. If you also need
  a screen-out, a working layout is: no Final page (the survey ends with the
  completion screen after the last content page), a Screen-out page **last**
  with a **Show if** holding the failing condition, and a branch rule from
  the screener to it. Qualified respondents never see the hidden screen-out
  page; failing ones are sent to it. See
  [[Logic and Branching|Studio-Logic-and-Branching]].
- or shuffle blocks on a page instead of pages.

### Seeded option order

**Scripts → Shuffle options** shuffles one question's options, like the
switch, and offers a **Seed** field.

> **Current limitation.** The seed has no effect: each respondent gets an
> independent random order, exactly as with the switch.

---

## Experimental assignment

**Scripts → Add script → Assign to a condition** draws each respondent into
exactly **one** arm (split-ballot, vignette versions, A/B stimuli) before the
first page, and stores the arm's code in a variable. This is a choice, not an
order, so it appears in Randomization as "condition assignment".

| Field | What to enter |
|---|---|
| **Variable** | where the arm is stored (default `condition`). Letters, digits and `_`, not starting with a digit, and not a variable a question already collects |
| **Seed** | leave empty (see the limitation below) |
| **Balance** | **Keep the arms level against their quotas** |
| **Arms** | **Code**, **Label** (placeholder "Control"), **Weight** (whole number, 1 or more) and the resulting **Share** in %. **Add arm** adds one; at least two arms are required |

- Defaults: arm `1` **Control** and arm `2` **Treatment**, equal weights.
- Weights set the shares: weights 2 and 1 give 67% and 33%.
- On **Add**/**Apply**, the variable is written to the codebook with the arm
  labels (label "Experimental condition"), so it exports with the data and
  your flows can group by it.
- The draw happens once. A respondent who resumes keeps their arm.

**Balance.** A random draw lets arms drift apart over a field period, and a
screen-out that hits one arm harder is never made up. With **Keep the arms
level against their quotas** ticked, each new respondent goes to the arm that
is furthest behind its own quota target (current ÷ limit, so a 2:1 design
keeps its proportions; ties are broken at random). It needs one quota cell per
arm on the assignment variable. The form tells you:

- "Each respondent goes to the arm furthest behind its quota, so no arm
  completes while another starves. N cells declared on <variable>."
- "**No quota cell for <arm>.** Balancing needs one per arm — until then the
  survey falls back to the weighted draw above. Add them in Quotas."
- Off: "Off: arms are drawn independently. Over a field period they drift
  apart, and a screen-out that hits one arm harder is never made up."

While balancing, the first page waits up to 2 seconds for the answer. If none
arrives, the respondent keeps the weighted draw. Previews always use the
weighted draw. **Seed** is disabled while balancing ("off while balancing —
the arm depends on who answered first").

> **Current limitation.** A **seeded** assignment sends **every respondent
> to the same arm**. Leave **Seed** empty.

> **Current limitation.** You cannot yet branch on the arm. A show if, hide if
> or branch rule that reads the assignment variable makes the Save fail the
> engine's check ("… references unknown variables: condition"), and the Save
> cannot be published. Use the arm for analysis and quota balancing. Showing
> different questions to different arms is not possible yet.

---

## Checking both before launch

- **Test → Walkthrough** shows the survey in a randomized order (press
  **Restart** for a new draw), but the side panel does not list option or
  page order.
- **Test → Simulate** applies **no** randomization, no assignment and no
  quotas: simulated rows are in document order, the assignment variable is
  not filled, and quotas are not counted.
- Publish to `pilot` and answer it a few times: the quota bars on the pilot
  card fill with your test answers, which confirms each cell is counted. Pilot
  counters are separate from `main`.

## See also

- [[Logic and Branching|Studio-Logic-and-Branching]]
- [[Scripts|Studio-Scripts]]
- [[Publishing and Environments|Studio-Publishing-and-Environments]]
- [[Live Monitoring|Studio-Live-Monitoring]]
- [[Testing Your Survey|Studio-Testing-Your-Survey]]
