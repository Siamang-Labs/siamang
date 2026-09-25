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
into each cell and shows the fill on the Distribute card and on Live. Once a
cell is full, it **closes**: a later respondent who gives that answer is
stopped on the "quota full" screen (see
[When a cell is full](#when-a-cell-is-full)).

> **Note.** Quotas used to be counted without stopping anyone, and they
> counted screen-outs. Both changed: cells now close, and they count completed
> interviews only. A survey published before the change keeps letting
> everyone through until you **publish it again**; its cells are already
> counted the new way (see [How cells are counted](#how-cells-are-counted)).

### The Quotas tab

```
A quota closes a cell once limit completed responses have the target value. …
[+ Add one cell]  │  or one for every value of [ region ▾ ] , limit [ 100 ] each   [Add 4 cells]

Variable        Value                 Limit
[ region ▾ ]    [ North (1)    ▾ ]    [ 400 ]    Remove
[ region ▾ ]    [ Capital (2)  ▾ ]    [ 300 ]    Remove
```

- The note reads: "A quota closes a cell once **limit** completed responses
  have the target value. A later respondent who gives that answer — for a
  multiple choice, any answer whose cell is full — is stopped when they leave
  its page, on the “quota full” screen (Theme → Wording). Screen-outs and
  unfinished responses do not count. Previews do not check quotas; after
  publishing, Live shows how full each cell is."
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
  choice, multiple choice, Likert, ranking and similar, each row variable of a
  Matrix, and each per-choice variable of a wide Multiple choice (`No (0)` /
  `Yes (1)`, so a cell such as `brands_1 = Yes (1)` counts everyone who chose
  that brand). Number and open-text questions cannot be quota variables here.
- **Value** is a dropdown of `Label (code)`. The cell stores the code.
- **Limit** is a whole number, at least 1.
- The number of cells appears in the Builder's version popover ("N quotas").

The engine checks every cell at each Save, and on the working document when
you press **Check now** in **Validation → Engine**. Each of these is a
`VALIDATION` error that marks the Save **errors** (so it cannot be
published) until you fix it:

- "Quota references unknown variable: <name>"
- "Quota on '<variable>' targets value <v>, which is not a defined category (…)"
- "Duplicate quota for '<variable>' value <v>."

**Source → Check** runs them too.

### How cells are counted

- Counters exist **per environment**. They are created when you publish: a
  new environment starts at zero, and `pilot` and `main` count separately.
- Republishing an environment keeps its counts and applies the new limits. A
  cell that a later Save adds to a survey already collecting starts at the
  number of completed responses that already have its value, not at zero.
- A cell counts **completed** responses, once per respondent. Resuming or
  retrying a completed interview does not count it twice. Partial interviews
  do not count.
- **Screen-outs do not count.** A respondent who reaches a Screen-out page is
  stored as screened out and fills no cell. A respondent who reaches a Final
  or Redirect page, or submits on the last question page, has completed.
- A **multiple-choice** answer kept as one variable (the list layout) counts
  in the cell of **every** value it holds; so does a Ranking. Someone who
  chose North and Capital fills both cells.
- **Erasing a response** (**Delete** on its row in **Data**, see
  [Deleting a response](Studio-Responses-and-Data#deleting-a-response))
  lowers the cells it had filled: the survey's cells are recounted from the
  responses that remain.
- A cell you remove from the questionnaire (or move to another value) keeps
  counting, and can still stop respondents, until you publish the Save
  without it: publishing drops from that environment every cell the Save no
  longer declares, and it no longer shows under **Distribute** and **Live**.
  If a later Save adds the cell back, it starts again at the
  number of completed responses that have its value. To reopen a full cell,
  give it a higher limit and publish again.
- The counters live in the project's `quota_counters` table, which you can
  open and export from **Data** (see
  [[Responses and the Data Tab|Studio-Responses-and-Data]]).

When this counting came in, every existing cell was recounted once from the
completed responses already stored, so cells that screen-outs had inflated
went down.

> **Limitation.** A cell on a **Matrix row** or on a **per-choice variable of
> a wide Multiple choice** counts only responses collected by a survey built
> with the current runtime. Responses collected before you republished stored
> those answers in an older layout; **Data** and exports read them correctly,
> but the cell counts (and the recount after an erasure) leave them out. Set
> such a cell's limit with that in mind, or watch the question in **Data**.

A cell is matched against the answer stored under its **variable**, whatever
the question's **Id** is (see [[The Builder|Studio-Builder-Overview]]).

> **Note.** Earlier versions of Studio stored the answer of a question whose
> Id differed from its variable name (every preset, for example) under the
> Id, so it never reached its cell. Those stored answers have been moved to
> the variable once, wherever that was unambiguous (an answer already stored
> under the variable is never overwritten, and an Id that could belong to
> something else is left alone). The cells of each variable that received
> answers this way were recounted from the completed responses, so their
> counts may have changed. A survey published before the change keeps counting
> correctly: its answers are filed under the variable as they arrive.

### When a cell is full

The published survey checks quotas **when the respondent leaves a page**
(**Next**, or **Submit responses** on the last page), before any routing:

1. Each quota variable that has a new value on this page, or that a script
   set (such as the arm of **Assign to a condition**), is put to the server.
   While the check runs, **Next** and **Previous** are briefly disabled; their
   labels do not change.
2. If a cell holding that value is full, the interview ends on the quota-full
   screen: "Thank you for your interest" / "We have already reached our target
   sample for participants like you." (reword both under Theme → Wording →
   **Quota full: title** and **Quota full: text**).
3. With a **Quota full → return URL** set on the Panel chip (see
   [[Panel Providers|Studio-Panel-Providers]]), the screen adds "Redirecting
   you now. Continue if you are not redirected." and sends the respondent
   back to the provider after 3 seconds.

For a multiple-choice answer, the respondent is stopped when **any** value
they chose has a full cell. A value found open is not asked about again unless
the answer changes.

The interview is not submitted, so it is not a completed response and fills
no cell. What the survey had already saved as a partial response on earlier
pages stays in **Data** as a partial, as for anyone who stops early. The
browser forgets the interview: reopening the link starts a new one, and with
**One per browser** switched on for the environment, the browser that hit a
full quota sees "You have already taken part".

The check never stops anyone by mistake: if the server cannot be reached or
does not answer within 4 seconds, the respondent goes on, and the value is
checked again on a later page. If the environment was paused or closed in the
meantime, the check shows that notice instead of the next page.

Previews do not check quotas: not **Structure → Preview**, the
**Walkthrough**, share links or the header **Preview**. To see the quota-full
screen before fieldwork, publish to `pilot` with a small limit.

> **Note.** The environment's
> [response cap](Studio-Publishing-and-Environments#response-caps) is a
> separate, overall limit on completed interviews. A survey whose cap is
> reached shows the same "Thank you for your interest" notice as soon as the
> page opens.

### Where to watch the fill

- **Distribute**: each environment card that serves the survey (not preview
  cards) lists **Responses** (with a cap, the completed interviews against
  it), then one row per cell: `region=1`, a bar, `112/400`.
- **Live**: the fieldwork monitor shows the same bars (see
  [[Live Monitoring|Studio-Live-Monitoring]]).

### Planning quotas

1. **Put the quota question early**, ideally on the screener page. A
   respondent is stopped when they leave the page that holds the answer, so
   an early quota question spares people from answering a long survey first.
2. **Use the environment's response cap for the overall target**, and quota
   cells for the groups inside it. See
   [Response caps](Studio-Publishing-and-Environments#response-caps).
3. **Set the Quota full return URL** if a panel provider sends the sample, so
   stopped respondents go back to the provider with the right status.
4. **Watch the bars** on Distribute or Live during fieldwork, especially at
   the start and after each invitation wave. Tell your panel provider to stop
   sending a group whose cell has closed, if they target it.
5. **Check the effect before launch**: **Test → Simulate** applies the cells
   to its synthetic respondents (see
   [Checking both before launch](#checking-both-before-launch)).

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

Shuffles are drawn per respondent. Shuffled order never changes the stored
codes, so your analysis is unaffected. What a reload or a resume keeps:

| Shuffle | After a reload or resume |
|---|---|
| the three order switches (options, questions in a block, blocks on a page) | drawn again when the survey loads, so the order may change |
| **Shuffle options** with a **Seed** | the same order for the same respondent |
| **Shuffle options** without a seed | drawn again |
| **Randomize pages** | a respondent who resumes continues in the order they were dealt, on the page they left; starting over deals a new order |
| **Assign to a condition** | a respondent who resumes keeps their arm; with a **Seed**, so does one who starts over |

### Option order

**Randomize option order** (Inspector → Question, on single choice, multiple
choice and ranking questions; row "option order (N options)") shuffles the
answer options for each respondent.

What stays in place: **"None of the above"** (single choice), **exclusive**
options such as "None of these" (multiple choice), and a choice that is the
question's **Other (please specify)** keep their positions; the other options
are shuffled among the remaining positions. The Other option Studio adds
itself is always shown after the options. (Surveys built before this change
shuffled "None of the above" and exclusive options with the rest; publish
again.)

> **Tip.** To keep another option in place — an ordinary last option such
> as "Don't know" that is not exclusive — leave the switch off and use a small
> custom script *(Plus)*. See
> [Shuffle but keep the last option last](Studio-Scripts#shuffle-but-keep-the-last-option-last).

### Question order in a block

**Randomize question order** (Inspector → Block; row "question order (N)")
shuffles the questions inside the block. Only questions inside a block can be
shuffled. To shuffle questions on a page, put them in a block. A block inside
the block moves as one piece, its questions staying together; switch on its
own **Randomize question order** to shuffle them as well.

### Block order on a page

**Randomize block order** (Inspector → Page, content pages only; row "block
order (N blocks)") shuffles the page's blocks. Questions that sit on the page
outside any block keep their positions; only blocks trade places with each
other.

### Page order

There is no page switch. Add **Scripts → Add script → Randomize pages**
(row "page order").

- The **first** page, the **last** page and every **end page** (Final,
  Screen-out, Redirect) keep their positions, wherever they sit.
- Every other page is shuffled into the remaining positions for each
  respondent.
- Nothing is shuffled unless at least **two** pages are free to move.
- A respondent who resumes a saved interview continues in the order they were
  dealt, on the page they left. (Surveys built before this fix could resume
  on the wrong page of a new order; publish again.)

Routing still follows the shuffled order: **— following page —** and
sequential **Next** go to the next page of the respondent's order, while
branch rules and **Default next** jump to a page by name. So:

- make the first page your introduction or screener: apart from the last
  page, it is the only content page that keeps its place;
- put your end pages after the last content page, as in the usual layout
  (content pages, then the **Final** page, then the **Screen-out** page; see
  [Screening people out](Studio-Logic-and-Branching#screening-people-out)).
  An end page between content pages keeps its position, but the shuffled
  pages around it change, so a respondent can reach it by pressing **Next**
  on whichever page was dealt into the slot before it;
- or shuffle blocks on a page instead of pages.

A survey published with an earlier version of Studio kept only the first and
last page in place. Publish it again to get this behavior.

### Seeded option order

**Scripts → Shuffle options** shuffles one question's options, like the
switch, when the question is first shown, and offers a **Seed** field (hint
"optional — with a seed each respondent keeps one order, after a reload too;
respondents still differ"). The same options keep their place as with the
switch.

- **Without a seed**, each load of the survey draws a new order.
- **With a seed**, the order is drawn from the seed and the respondent's id:
  each respondent sees one stable order, kept after a reload or a resume,
  while orders still differ between respondents.
- Two questions shuffled with the **same seed** and the same number of
  options are shown in the same order to a given respondent, which keeps a
  brand list in one order across several questions. Give them different
  seeds for independent orders.

A survey built before seeds worked ignored the seed; publish it again.

---

## Experimental assignment

**Scripts → Add script → Assign to a condition** draws each respondent into
exactly **one** arm (split-ballot, vignette versions, A/B stimuli) before the
first page, and stores the arm's code in a variable. This is a choice, not an
order, so it appears in Randomization as "condition assignment".

| Field | What to enter |
|---|---|
| **Variable** | where the arm is stored (default `condition`). Letters, digits and `_`, not starting with a digit, and not a variable a question already collects |
| **Seed** | optional (hint "optional — with a seed a respondent always gets the same arm") |
| **Balance** | **Keep the arms level against their quotas** |
| **Arms** | **Code**, **Label** (placeholder "Control"), **Weight** (whole number, 1 or more) and the resulting **Share** in %. **Add arm** adds one; at least two arms are required |

- Defaults: arm `1` **Control** and arm `2` **Treatment**, equal weights.
- Weights set the shares: weights 2 and 1 give 67% and 33%.
- On **Add**/**Apply**, the variable is written to the codebook with the arm
  labels (label "Experimental condition"), so it exports with the data and
  your flows can group by it.
- The draw happens once. A respondent who resumes keeps their arm.
- **Seed.** Without a seed, each new interview is an independent weighted
  draw. With a seed, the draw is worked out from the seed and the
  respondent's id: respondents are still spread over the arms by their
  weights, and the same respondent always lands in the same arm, even after
  starting over in the same browser. (A survey built before this fix sent
  every respondent of a seeded assignment to the same arm; publish it again.)

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

**Quota cells on the arm close too.** Like every quota cell, an arm's cell
stops respondents once it is full: a respondent whose arm has a full cell
ends on the quota-full screen when they leave the first page (see
[When a cell is full](#when-a-cell-is-full)). With **Balance** on and a cell
on every arm, new respondents go to arms that still have room; the weighted
draw decides only when every arm is full or the server does not answer in
time. Without **Balance**, the weighted draw can put a respondent into a full
arm while other arms still have room, and that respondent is turned away:
tick **Balance** whenever the arms have quota cells.

**Branching on the arm.** The assignment variable is an ordinary variable for
Logic. Pick it in any condition editor (it is in the codebook with the arm
labels, so the value list reads `Control (1)`, `Treatment (2)`):

- a **Show if** such as `condition = Treatment (2)` on a question, block or
  page shows it to one arm only. This is how vignette versions and A/B
  stimuli are built;
- a **Branch (next if)** rule on the arm sends each arm down its own route;
- piping `{answer:condition}` inserts the arm's code. `{label:condition}`
  inserts the code too, not the label: piped labels come from a question's
  answer options, and no question asks the arm.

The arm is drawn before the first page, so conditions on the first page can
read it too, and Studio's check never reports it as a forward reference. See
[Assignment and "embedded data"](Studio-Logic-and-Branching#assignment-and-embedded-data).

---

## Checking both before launch

- **Test → Walkthrough** shows the survey in a randomized order and draws an
  arm with the weighted draw (press **Restart** for a new draw), but the side
  panel does not list option or page order. Restart until you have walked
  each arm's route. The Walkthrough does not check quotas.
- **Test → Simulate** plays the assignment, the page order and the quotas:
  each simulated respondent gets an arm drawn by the arms' weights (with
  **Balance**, the arm furthest behind its quota among the simulated
  respondents so far), and the arm is a column of the result with its
  codebook entry; pages and questions gated on the arm are filled for that
  arm; **Randomize pages** deals each respondent a page order; and a
  respondent who answers into a full quota cell stops there, as in the
  survey, with the later pages empty. Only simulated completes fill the
  cells. Option shuffles are not drawn, since they do not change the data;
  question and block shuffles only change which Skip to a respondent meets
  first.
- Publish to `pilot` and answer it a few times: the quota bars on the pilot
  card fill with your completed test interviews (screen-outs do not count),
  which confirms each cell is counted. With a small limit you also see the
  quota-full screen. Pilot counters are separate from `main`.

## See also

- [[Logic and Branching|Studio-Logic-and-Branching]]
- [[Scripts|Studio-Scripts]]
- [[Publishing and Environments|Studio-Publishing-and-Environments]]
- [[Live Monitoring|Studio-Live-Monitoring]]
- [[Testing Your Survey|Studio-Testing-Your-Survey]]

<!-- studio-nav -->
---

← [[Logic and Branching|Studio-Logic-and-Branching]] · [Studio contents](Studio-Overview#all-pages) · [[MaxDiff and Conjoint|Studio-MaxDiff-and-Conjoint]] →
