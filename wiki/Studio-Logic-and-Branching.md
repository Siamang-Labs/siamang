# Logic and Branching

Logic decides what each respondent **sees** (show if / hide if) and where
they **go** next (Skip to, branch rules, default next). This page covers the
condition editor, every kind of routing and the order in which it applies,
screen-out pages, piping, the Logic map, and the checks that catch broken
logic before you publish.

> **Note.** Logic reads a question's **variable name**, and the survey stores
> the answer under that same name. The question's **Id** (Inspector →
> **Advanced**) is only its handle in the Builder and in script targets, so
> the two may differ: a preset, for example, gets Id `q5` and variable
> `nps_5`, and conditions, piping and quotas on `nps_5` work. See
> [[The Builder|Studio-Builder-Overview]].
>
> A survey published with an earlier version of Studio stored such a
> question's answer under its **Id**, so in that build, conditions and piping
> that read the variable never fire. Answers that build still sends are filed
> under the variable when they arrive, so **Data** and the quota counts are
> right. To fix the routing in the respondent's browser, publish the survey
> again.

> **Note.** The survey runtime was updated. Conditions on Matrix rows, on the
> per-choice variables of a wide Multiple choice and on MaxDiff and Conjoint
> tasks now fire, a nested block's conditions now apply, a comparison with an
> empty value now means "not answered" in the browser too, and piping now
> works on end pages. A survey that is already in the field keeps the runtime
> it was built with: **publish it again** to give respondents the new
> behavior. Every Save you publish from now on gets it.

---

## Where logic lives

| Level | Field | Where to set it | What it does |
|---|---|---|---|
| Page | **Show if**, **Hide if** | Inspector → Page → **Logic** | shows or skips the whole page; checked when the respondent arrives at it |
| Page | **Branch (next if)**, **Default next** | Inspector → Page → **Logic** | where the respondent goes when leaving the page |
| Block | **Show if**, **Hide if** | Inspector → Block → **Logic** | shows or hides every question in the block together, including the questions of blocks inside it |
| Question | **Show if**, **Hide if** | Inspector → Question → **Logic** | shows or hides one question |
| Question | **Skip to** | Inspector → Question → **Logic** | jumps to a page once the question is answered (on **Next**) |
| Answer option | show if / hide if | **Source** tab only | hides one answer option of a question |

The **Logic** section of the Inspector opens by itself when the item already
has logic. On the canvas, a question or block with a condition carries a
**show if** or **hide if** pill (hover it to read the condition). A question
with a Skip to shows **→ page name**. In the page rail, **⤳** marks a page
that has branch rules or a default next.

Answer-option conditions have no editor in the Builder. You can write them in
the **Source** tab (or bring them in by import). The runtime applies them,
**Test → Simulate** applies them, and the Logic map shows them as **OPTION
SHOW IF** / **OPTION HIDE IF**. In a wide Multiple choice, the 0/1 variable of
an option that its own condition hid from a respondent is left empty
(missing) rather than 0: 0 means "offered and not chosen".

---

## The condition editor

Every **Show if**, **Hide if** and branch-rule condition uses the same editor.
Collapsed, a condition reads as a sentence followed by **Edit** and **Clear**
links. An empty condition shows an **Add condition** link.

```
Show if   (age ≥ 18) and (region in [1, 2])      Edit  Clear

  ┌──────────────────────────────────────────────────────────────┐
  │ [ALL of the following ▾]                               Done  │
  │ [ age    ▾ ]  [ ≥  ▾ ]  [ 18            ]                 ×  │
  │ [ region ▾ ]  [ in ▾ ]  [ 1, 2        ▾ ]                 ×  │
  │ + Condition                                                   │
  └──────────────────────────────────────────────────────────────┘
```

- A condition is a **flat list of rows**. Each row is **variable · operator ·
  value**, with **×** to remove it (**Remove condition**). **+ Condition** adds
  a row.
- With two or more rows, a selector appears at the top: **ALL of the
  following** (every row must hold) or **ANY of the following** (at least one
  must hold). One condition cannot mix ALL and ANY, and there is no nesting in
  the visual editor.
- **Done** closes the editor. **Clear** removes the whole condition.
- The variable list holds **every** variable of the questionnaire, sorted
  alphabetically: question variables plus codebook entries (such as the arm
  of **Assign to a condition**), including variables asked **later**.
  Picking a later one is allowed but is flagged (see
  [Studio's check](#studios-check)).
- A question that writes several variables offers each of them: one per
  Matrix row, one 0/1 variable per choice of a wide Multiple choice (for
  example `brands_1 = Yes (1)`), the best and worst variables of each MaxDiff
  task and the variable of each Conjoint task. The text typed into "Other
  (please specify)" is a variable too, `<variable>_other`.
- With no variables yet (no question and no codebook entry), **+ Condition**
  is disabled with "Add a question first — conditions reference its
  variable."

### Operators

| Label | Meaning |
|---|---|
| **=** | the answer equals the value |
| **≠** | the answer differs from the value (also true when unanswered) |
| **>**, **≥**, **<**, **≤** | numeric comparison |
| **in** | the answer is one of several values |
| **not in** | the answer is none of several values (also true when unanswered) |
| **chose** | a multiple-choice answer includes this code (on a single answer, same as **=**) |
| **did not choose** | a multiple-choice answer does not include this code (also true when unanswered) |

Use **chose** / **did not choose** for multiple-choice questions. An answer of
"1 and 3" is not **=** 1, so a condition written with **=** never matches
anyone who picked more than one option.

The comparison is exact: the code `2` and the text `"2"` are different values.

### Comparing with "no answer"

A row whose value is left empty compares with no answer at all. The sentence
shows it as `∅`:

- `q7 = ∅` holds for a respondent who has not answered `q7` (or never saw
  it);
- `q7 ≠ ∅` holds for a respondent who has.

The survey and **Test → Simulate** now read these the same way. (Surveys
built before the runtime update treated an unanswered question as never
equal to `∅`, so `≠ ∅` held for everyone; publish again to change that.) On
a variable with value labels the engine's check warns about an empty value
(`UNKNOWN_CONDITION_VALUE`); there, **in** with every code of the question
says "answered" without a warning. A new branch rule cannot be added with an
empty value (see [Adding a rule](#adding-a-rule)).

### Value pickers

| Variable and operator | Value control |
|---|---|
| labeled variable with **=**, **≠**, **chose**, **did not choose** | dropdown of `Label (code)` |
| labeled variable with **in** / **not in** | **choose codes**: a checkbox list; the button then shows the chosen codes |
| unlabeled variable with **in** / **not in** | text field, comma-separated (placeholder `1, 2, 3`) |
| anything else (including **>**, **<** on a labeled variable) | text field (placeholder `value`) |

Whatever you pick, the condition stores the **code**. Typed numbers are stored
as numbers, `true` / `false` as booleans, and anything else as text.

### The sentence

The collapsed sentence shows the stored comparison. Several rows are wrapped
in parentheses and joined with `and` / `or`: `(age ≥ 18) and (region in [1, 2])`.
A single-value comparison on a labeled variable also shows the label:
`region = Capital (1)`. Lists show codes, not labels.

### Conditions the editor cannot show

A condition with groups nested inside each other, a `not`, or raw text (from
an import, or written in **Source**) opens as JSON instead:

> This condition nests groups or uses a raw expression — edit it as JSON
> (schema: condition).

Edit the JSON and press **Apply**, or **Cancel**. A malformed entry shows
"Could not read this condition" with the reason. Raw-text conditions are
evaluated by the survey, but the Builder cannot read them: they draw nothing
on the Logic map and no check applies to them.

---

## Show if and Hide if

- **Show if**: empty means "always shown". With a condition, the item appears
  only when the condition is true.
- **Hide if**: empty means "never hidden". Use it when the exception is easier
  to state than the rule.
- An item is visible when its Show if holds **and** its Hide if does not.
  Setting both on one item gives the warning `CONTRADICTORY_VISIBILITY`.
- Hidden questions are not asked, record no answer and are not required. A
  **Required** question with a Show if gives the warning
  `REQUIRED_CONDITIONAL` in Validation. That is expected, and you can accept
  it.
- A hidden **page** is passed over in navigation, as if it were not there.
- A **block inside a block** behaves as it reads: its own Show if / Hide if
  gates every question inside it, on top of the outer block's. Only a page's
  own blocks show their **Title** to respondents; the title of a block inside
  another block is not displayed.
- Conditions are live: a question further down the same page appears or
  disappears as soon as the answer it depends on changes.

Put a condition on the **highest** item that needs it. One condition on a
block is easier to maintain than the same condition copied onto five
questions.

---

## Skip to

**Skip to** (hint "on Next, after any answer to this question — checked
before the page’s Branch rules") is a page dropdown on a question. The
default is **— next page —**. It works like this:

- It is **unconditional**. It fires for **any** answer, not for a particular
  one.
- It fires when the respondent presses **Next** on that page, not the moment
  they answer.
- The question must be **visible and answered**. An unanswered or hidden
  question does not skip.
- On a **Matrix**, one answered row is enough. A required matrix is still
  held by **Next** until every row is answered (see
  [Matrix](Studio-Question-Types#matrix)), so its Skip to fires only then.
- If several questions on the page have a Skip to, the **first** answered,
  visible one wins.
- Skip to wins over the page's branch rules and default next.

To route people **by their answer**, use a branch rule on the page instead.

The dropdown lists pages. A questionnaire brought in by import (or edited in
**Source**) may name a question's Id as the target instead; the survey then
goes to the page that holds that question, and Studio's check accepts it.

---

## Branch (next if) and Default next

On a page, Inspector → **Logic**:

- **Branch (next if)** (hint "first matching rule wins") is an ordered list of
  rules. Each rule is a condition plus a target page (**→** page name, the
  **Target page** list). **×** (**Remove rule**) deletes a rule. The target
  list offers every page except the current one. **+ Rule** is disabled while
  the questionnaire has only one page.
- **Default next** (hint "when no rule matches"): the page to go to when no
  rule matched. **— following page —** means the next **visible** page in
  document order.

### Adding a rule

**+ Rule** opens a **draft** rule under the existing ones, with the condition
editor already open. It starts with one comparison, **=** on the last
question of this page (or the first variable, on a page without questions),
and the first other page as its target. While the draft is open, **+ Rule**
is hidden.

```
Branch (next if)                      first matching rule wins
                                                              Done
  [ age ▾ ]  [ =  ▾ ]  [ value     ]                           ×
  + Condition
  Pick what the rule tests — it is added once the condition is complete.
  →  [ about_you ▾ ]                          [Add rule]  [Cancel]
```

The note under the comparisons disappears once every comparison has a value.

- Pick the variable, the operator and the value, and the target page.
- **Add rule** stays disabled until every comparison has a value. Pressing it
  adds the rule at the end of the list.
- **Cancel** drops the draft; nothing was added.

A draft is not part of the questionnaire until you press **Add rule**, so a
half-written rule never reaches the survey or the Logic map.

### Rules with no condition

A rule whose condition is empty never matches: it is not an "otherwise". A
draft cannot be added empty, but a rule can still lose its condition (press
**Clear** on it) or arrive without one from an import or an older document.
Studio flags such a rule until you give it a condition:

- under the rule in the Inspector: "Add a condition — an empty rule never
  fires.";
- on the Logic map, its arc is labeled "no condition — never fires";
- in **Validation → Structure**: `<page>: the branch to "<target>" has no condition — an empty rule never fires; add one, or use Default next`.

Give every rule a condition, and use **Default next** for "everyone else".

### What happens when Next is pressed

First the page is checked: required questions, formats and limits, script
messages. Then, in a published survey with quotas, the answers are checked
against the quota cells: a respondent whose answer falls into a full cell
ends on the quota-full screen here, before any routing (see
[[Quotas and Randomization|Studio-Quotas-and-Randomization]]). Otherwise
Studio works through these in order and uses the first that applies:

1. **Skip to** of the first visible, answered question on the page that has one.
2. The first **Branch (next if)** rule whose condition is true.
3. **Default next**, if set.
4. The next **visible** page in document order.

If the chosen page is hidden by its own Show if / Hide if, the respondent
lands on the first visible page after it.

The **Previous** button retraces the path the respondent actually took, so
someone who was branched past three pages goes straight back to where they
came from. The page dots (Theme → **Progress**) follow the same path: they go
back only to pages the respondent visited on the way here, never forward. A
respondent who resumes a saved interview goes back along the saved path too.

This is how you build interview routes: send employed respondents down one
path and students down another, then bring them together on a common page
with **Default next**.

---

## End pages

A page's **Kind** (Inspector → Page) is **Content**, **Final (thank you)**,
**Screen-out** or **Redirect**. The rail's **+ Page** menu adds each kind
directly: **Content page**, **Final page**, **Screen-out page**, **Redirect
page**. When routing reaches an end page, the interview ends there:

| Kind | What the respondent sees | Recorded as |
|---|---|---|
| **Final (thank you)** | the page's title and body (defaults "Thank you" / "Thank you for taking part."), with a **Response ID** and **Submitted** time | completed |
| **Screen-out** | the page's title and body (defaults "Thank you" / "You do not qualify for this study.") | screened out |
| **Redirect** | the page, then a redirect to **Redirect URL** after **Delay (s)** (5 seconds by default) | redirect |

- Reaching an end page **submits the response**. A redirect counts as a
  completed response. A screen-out is stored and shows in **Data**, but it
  is not a completed interview: it does not count toward the environment's
  [response cap](Studio-Publishing-and-Environments#response-caps) or the
  Free plan's per-project cap, and it fills no quota cell.
- The **Body** of a Final or Screen-out page is HTML (hint "HTML, shown to
  the respondent; {answer:variable} or {label:variable} pipes an earlier
  answer"). [Piping](#piping) works in the title and body of every end page.
- A Final page without a title shows the completion screen's **Title**, and
  one without a body shows its **Message**; a Screen-out page without a title
  shows the Wording field **Screen-out page title** ("Thank you"). See
  [Completion screen](Studio-Theme-and-Branding#completion-screen).
- If the survey ends on a content page instead, the respondent presses
  **Submit responses** and sees the completion screen (see
  [Completion screen](Studio-Theme-and-Branding#completion-screen)).
- Panel providers can receive each outcome on its own return URL (see
  [[Panel Providers|Studio-Panel-Providers]]).

End pages end the interview only when someone **reaches** them. Everyone who
walks sequentially past your last content page lands on the next page in the
document, whatever its kind. Order your end pages with that in mind.

---

## Screening people out

The dependable pattern:

1. Add a **Screen-out page** (rail → **+ Page** → **Screen-out page**) with a
   polite message.
2. Order the pages so qualified respondents never walk into it: content pages
   first, then the **Final** page, then the **Screen-out** page last.

   ```
   screener → about_you → … → thanks (Final) → screenout (Screen-out)
   ```

3. On the screener page, add a **Branch (next if)** rule: the failing condition
   (for example `age < 18`) **→** `screenout`.

Qualified respondents continue page by page, reach **thanks** and stop there.
Failing respondents jump from the screener straight to **screenout**.

Do not use **Skip to** for this. It cannot tell a failing answer from a
passing one.

### Attention checks

For an instructed-response item ("please choose *Rarely*"), tick **Attention
check** on the question ("scored in the flow, not in the survey") and pick the
**Expected answer**. Until you set one, the Builder warns "Until an answer is
set, this question checks nothing." The option is available on single choice,
Likert, number and open text questions.

By default, a failed check is only flagged in the data, for your analysis to
decide (see [[Data Quality|Studio-Data-Quality]]). To stop the interview
instead, tick **Also end the survey for respondents who fail** (hint "adds a
screen-out branch"; once ticked, "branches to <page>"). This adds an ordinary
branch rule to the page that holds the check, pointing at a Screen-out page
that only this rule leads to. Under the box the Inspector explains:

> An ordinary page branch, editable in Logic: it is evaluated when this page
> is left, so they finish the page first, and their answers are still
> collected and counted as screened out. Its Screen-out page sits after the
> Final page, so only this branch leads there. Leave it off to keep everyone
> and decide in the analysis instead.

(The middle sentence appears only while the Screen-out page really does sit
behind the Final page.) The rule appears in the page's **Logic** section like
any other, and unticking the box removes it; the Screen-out page stays.

**Who is screened out.** Only a respondent who answered, and answered
something other than the expected answer:

- on a question with answer codes (single choice, Likert, or a variable with
  value labels), the rule is "the answer is one of the other codes" (**in**);
- on a number or open-text question without codes, it is "answered and
  different" (`≠ ∅` and `≠` the expected answer).

A respondent who leaves an optional check empty is not screened out. (In a
survey built before the runtime update, the "answered and different" rule
also caught respondents who left a number or open-text check empty; publish
again to fix that.)

**Where the Screen-out page goes.** Pages are shown in order, so a Screen-out
page anywhere a respondent can walk onto would catch the people who passed.
Studio therefore places it **after the last Final or Redirect page**:

- If a Screen-out page without a Show if / Hide if already sits there, the
  rule points at it.
- Otherwise Studio adds one right after the last Final or Redirect page,
  named `disqualification`, with the title "Thank you" and the body "You do
  not qualify for this study." (edit both as you like).
- If no Final or Redirect page ends the survey for everyone (one without a
  Show if / Hide if), Studio first adds a Final page, `final` ("Thank you" /
  "Thank you for taking part."), after your last content page and any end
  pages right behind it.

```
before:  screener → about_you
after:   screener → about_you → final (Final) → disqualification (Screen-out)
```

Respondents who pass walk on to the Final page and are recorded as
completed. Respondents who fail jump from the check's page to the Screen-out
page and are recorded as screened out.

A conditional Screen-out page that already exists keeps its own job. Every
template that asks for consent has one (`screen_out`, right after the consent
page, **Show if** `consent = 0`); the attention check does not use it, because
for everyone who consented it is hidden, and a branch to a hidden page lands
on the first visible page after it.

#### Checks saved before this placement

Studio used to put the new Screen-out page in front of the Final page, or
reuse a conditional one. A questionnaire saved that way shows an error under
the checkbox, and the same finding in **Validation → Structure** as
`<question>: the screen-out branch for failing this attention check does not work. <reason>`:

| Reason shown | What it means | Fix |
|---|---|---|
| "Respondents who pass reach “<page>” too: it comes after this page with no Final page in between, and pages are shown in order." | respondents who pass walk into the Screen-out page and are recorded as screened out | **Fix the branch** |
| "“<page>” has a show if or hide if of its own. Where it is hidden, a respondent who fails is sent on to the next page shown after it instead of being screened out." | the rule points at a conditional Screen-out page (the consent templates' `screen_out`) | **Fix the branch** |
| "Skip to on <question> is checked before branch rules, so for anyone who answers <question> this branch never fires." | a question on the same page has a Skip to, which wins over every branch rule | remove the Skip to, or put the check on a page of its own |

**Fix the branch** rebuilds the rule as a new tick would. A Screen-out page
that passing respondents walk into is moved, with its wording, to right after
the last Final or Redirect page (a Final page is added first if none ends the
survey), and the rule is pointed at it. A conditional Screen-out page is left
where it is for its own job, and the rule is pointed at a Screen-out page
behind the Final page, added if there is none. Save, then publish again: a
survey already in the field keeps the old routing until you do.

---

## Piping

Insert an earlier answer into text:

| Token | Inserts |
|---|---|
| `{answer:variable}` | the stored answer (the code, number or text) |
| `{var:variable}` | same as `{answer:…}` |
| `{label:variable}` | the label of the chosen option (the raw value for questions without options) |

```
Text:  You told us you mostly use {label:main_brand}. How satisfied are you with it?
```

- **Where it works:** question text and hint; a page's title and **Body**
  (on a page with questions the body is shown above them); and the title and
  body of Final, Screen-out and Redirect pages. The Inspector reminds you
  under Question → **Advanced**: "To insert a previous answer into question
  text or a hint, use {answer:variable} or {label:variable}."
- **Where it does not:** answer-option labels.
- `{label:…}` shows the chosen option's label. For "Other (please specify)"
  it shows what the respondent typed. A Matrix row's variable gives the
  column's label, and a MaxDiff task's best or worst variable the item's
  label (`{label:md_t1_best}`).
- A multiple-choice answer is inserted as a comma-separated list ("Daily,
  Weekly").
- An **unanswered** variable leaves the token on screen exactly as typed
  (`{label:main_brand}`). Only pipe answers the respondent is sure to have
  given.
- Validation warns about piping a variable that does not exist
  (`PIPE_UNKNOWN_VARIABLE`) or one that is answered later
  (`PIPE_FORWARD_REFERENCE`). The arm of **Assign to a condition** is never
  a forward reference: it exists before the first page.

**Redirect URLs** (a Redirect page's **Redirect URL** and the panel return
URLs) accept the same tokens plus `{url:NAME}`, the value of the `?NAME=`
parameter the respondent arrived with. Values are URL-encoded, and an unknown
token is removed rather than sent. See [[Panel Providers|Studio-Panel-Providers]].

---

## Assignment and "embedded data"

Studio has no embedded-data element. What exists:

- **URL parameters** are stored with each response as `url_<name>`
  columns (see [URL parameters](Studio-Distribution-Channels#url-parameters)).
  Conditions cannot read them. Only redirect URLs can, through `{url:NAME}`.
- **Assign to a condition** (Scripts) draws each respondent into an
  experimental arm and writes the arm's code to a variable, which it declares
  in the codebook with the arm labels (see [[Scripts|Studio-Scripts]]).
- **Custom JavaScript** can write values into the answers (see
  [[Scripts|Studio-Scripts]]).

A condition may read any variable that:

- a **question** collects;
- **Assign to a condition** writes. The arm is drawn before the first page,
  so a show if, hide if or branch rule anywhere in the survey, the first page
  included, can read it. Pick it in the condition editor like any other
  variable: `condition = Treatment (2)` on a page's **Show if** shows that page
  to one arm only;
- the codebook declares without a question. The Codebook tab has no button
  for this; add the entry under `variables` in the **Source** tab. Use it for a
  value your custom JavaScript writes: the condition reads whatever the script
  has stored by the time the condition is checked.

A variable that **Assign to a condition** writes, or that the codebook
declares and a custom script writes, cannot also be the Id of a question
whose own variable is different: a script naming it would reach that
question's answer instead. The Builder flags such an Id and the Save is
marked **errors** (see
[Names an Id may not take](Studio-Builder-Overview#names-an-id-may-not-take)).

A condition that reads any other name fails the engine's check when you
Save: "… references unknown variables: <name>". The Save is marked
**errors** and cannot be published.

> **Note.** Because a codebook entry counts as a known variable, a condition
> that reads a name only the codebook declares passes both checks even when
> nothing ever writes it: **=**, **in** or **chose** on it then never match
> anyone, and **≠**, **not in** or **did not choose** match everyone. In the
> Logic map's **Questions** lens, such a condition's **Reads answers from**
> shows the name as "not collected by any question". Make sure a script
> really writes it.

---

## Renaming variables and pages

Logic refers to variables and pages by name, and renaming either one carries
the references along.

**A variable.** Renaming a variable in the Inspector's **Variable** section
renames it everywhere the questionnaire uses it: conditions and branch rules,
quotas, `{answer:}` / `{label:}` piping, script targets, and `answers.<name>`
accesses in Custom JavaScript. Its codebook entry moves with it, so no unused
old entry is left behind. A string inside custom code that merely holds the
name is not changed. See
[Renaming a variable](Studio-Codebook-and-Variables#renaming-a-variable).
Once the questionnaire has been published, the Inspector adds: "This
questionnaire has been published. Renaming a variable renames its column in
the data: answers already collected keep the old name, answers collected
after you publish again get the new one."

**A page.** The page's **Name** field (hint "used by logic (skip to, next
if) and page scripts") takes the new name when it loses focus or when you
press `Enter`; `Escape` puts the current name back. A name another page
already has is refused with "Another page already has this name." The rename
updates every branch rule and **Default next** that points at the page, every
**Skip to** that names it, and the target of Custom JavaScript that runs on
it (**onPageEnter** / **onPageExit**), so the next Save does not fail on a
stale script target.

---

## The Logic map

**Builder → Logic map** has two lenses, because "logic" means two things:
where a respondent **goes**, and what a respondent **sees**. The switch sits
in the header, beside the counts:

- **Pages**: "Where the respondent goes next: routing between pages".
- **Questions**: "What the respondent sees: show if / hide if, and the answer
  each condition reads".

### Pages lens

One box per page in document order. Each box shows the page name and "N · N
questions", or its kind (**final**, **screen-out**, **redirect**). Arrows
show the routing:

| Line | Meaning | Label |
|---|---|---|
| short arrow between neighbors | next page | none |
| arc | **Default next** | "otherwise" |
| arc | **Branch (next if)** rule | the condition, or "no condition — never fires" for an empty one |
| thin arc | **Skip to** | "<question> answered" |
| red arc | part of a cycle | none |

Forward jumps arc above the row and backward jumps below it. The header reads
"N pages · N routing rules" and "✕ N issues" when there are problems. The ⓘ
button explains the view.

Two problems are listed above the map. The engine rejects both at Save — the
Save is marked **errors** and cannot be published until you fix them:

- **UNREACHABLE**: "No route leads to page X — the engine rejects the
  questionnaire until a rule points at it or it moves into the flow." Click it
  to select the page.
- **CYCLE**: "The routing loops back on itself (red arcs). The engine rejects
  cycles in the page graph."

Skip to arcs are drawn but, as in the engine, they do not make a page
reachable. Only the page order, default next and branch rules do. A branch
rule with an empty condition still counts here, although no respondent ever
takes it.

Select a page (or click an arc) to fill the side panel:

- **Leads to**: "next page X", "otherwise X", "if <condition> → X" ("if no
  condition — never fires → X" for an empty rule), "skip to X when
  <question> is answered", or "end of the survey".
- **Reached from**: the pages and rules that lead here, "the first page", or
  "nothing — unreachable".
- **Edit page logic →** opens the page in **Structure** with its Logic
  section. Double-clicking a page box, or pressing `Enter` on it, does the
  same.

Clicking a rule in the list highlights its arc; editing happens in Structure.

### Questions lens

Every item that carries a condition, or whose answer a condition reads, in
the order the survey **evaluates** them. A rail on the left draws one arc from
each answer to the condition that reads it. The ordering is the point:

> An arc that points **upward** reads an answer that has not been given yet,
> so that condition can never be true.

Page show / hide rows sit above the page's questions (checked on arrival).
Branch-rule rows sit below them (checked on leaving).

Reading a row, left to right:

| Part | What it says |
|---|---|
| the dot, or `!` | the kind of item (page, block, question, branch rules), or `!` for a condition that can never be true |
| the identifier | the question id, the block title or the page name |
| the text under it | the question text, the page title, "branch rules", or how many items a block holds |
| the chips | the action (**SHOW IF**, **HIDE IF**, **BRANCH IF**, **OPTION SHOW IF**, **OPTION HIDE IF**), then one chip per term with **AND** / **OR** between them. Two terms show; **+N conditions** expands the rest |
| `used by N rules` | this question's answer is read by N conditions |

- Page boundaries appear as "page N · name — title".
- Runs of questions that take no part in any logic collapse into "⋯ N
  questions omitted". Click it to open the run ("hide N questions again").
- The header shows "N items in logic", "N dependencies" and, when there are
  problems, "✕ N issues". Click the count to step through the issues. A banner
  shows "ISSUE i/N" with the message, **Show dependency** and **Next**.
- Raw-text conditions are counted in a **NOT READ** banner: "N conditions are
  raw text (…). The Builder cannot read them, so they have no arcs and none of
  the checks apply to them."
- The filter narrows the rows: **All logic**, **Visibility conditions**,
  **Branching**, **Dependencies** (only items at either end of an arc),
  **Errors only**, **Referenced questions**. When nothing matches: "Nothing
  matches <filter>. Choose another filter to see the rest of the map." The
  filter never changes what the side panel says about the item you selected.
- With no conditions at all: "**No conditional logic yet.** Show if / hide if
  on a question, a block, a page or a single answer option will appear here,
  with an arc from the answer each condition reads."

The side panel (**Logic inspector**) starts with "Select an item to inspect
its dependencies and logic." For a selected item it shows:

- **Visibility**: its conditions as chips;
- **Reads answers from**: each variable, marked "earlier ✓", "later ✗" or
  "not collected by any question";
- **Referenced by**: which conditions read this item's answer ("0 rules" when
  none);
- for a broken item: "**This rule can never be true.** <item> reads <var>,
  which <question> collects later in the survey.", the two positions and a
  **Go to <question>** button;
- **Edit condition →**, which opens the item in Structure (double-click or
  `Enter` on a row does the same).

---

## Checks that catch broken logic

Two layers check logic, and they are not the same.

### Studio's check

Studio's check runs as you edit. It appears under **Validation → Structure**
(the condition problems also on the Logic map's **Questions** lens), and it
never blocks a Save:

- **Forward references.** A condition that
  reads an answer not yet given:
  `<item>: the condition reads "<var>", but <question> on page <page> has not been answered when this condition is evaluated — it can never be true`.
  For page Show if / Hide if the wording is "…when this page is entered…".
  Question and block conditions may read earlier questions on the same page;
  page conditions only earlier pages; branch rules may read the page's own
  questions.
- A condition that reads a variable no question collects and the codebook does
  not declare: `<item>: the condition reads "<var>", which no question collects and the codebook does not declare`.
  A variable that only the codebook declares (the arm of **Assign to a
  condition**, for example) is not flagged.
- A branch rule with an empty condition:
  `<page>: the branch to "<target>" has no condition — an empty rule never fires; add one, or use Default next`.
- An attention check whose screen-out branch cannot work:
  `<question>: the screen-out branch for failing this attention check does not work. <reason>`
  (see [Checks saved before this placement](#checks-saved-before-this-placement)).
- `<question>: skip_to points at unknown page "<page>"` (a Skip to that names
  an existing question's Id is not reported: it goes to that question's page),
  `<page>: next_if target "<t>" does not exist`,
  `<page>: default_next "<t>" does not exist`.

### The engine's check

The engine's check runs at every Save, and on the working document when you
press **Check now** in **Validation → Engine**. These errors mark the Save
**errors** and block publishing:

- unreachable pages and cycles in the page routing;
- a Skip to, branch or default-next target that does not exist;
- duplicate question ids, empty or duplicate page names;
- a condition that reads a variable that no question collects, no **Assign
  to a condition** writes and the codebook does not declare (see
  [Assignment and "embedded data"](#assignment-and-embedded-data));
- the same variable written by two questions;
- a question whose **Id** is another question's variable name ("Question
  '<id>' has the id under which question '<other>' stores its answer; an id
  may not be another question's variable or output name."). Logic and script
  targets could not tell the two apart;
- a question whose **Id** differs from its variable and is a name the
  survey stores something else under: a variable any question stores (a
  Matrix row included), a question's Other text, the arm of an
  **Assign to a condition**, a codebook variable no question collects that a
  custom script writes, or a name starting with `__` ("Question '<id>' stores
  its answer under '<variable>', but '<id>' is also <what>. A script that
  names '<id>' could mean either; give the question another id.", with "…or,
  if the codebook entry '<id>' is left over from renaming this question's
  variable, delete that entry so that '<id>' in the script means the
  question." added for a codebook variable a script writes). Studio
  translates a script's `answers["<id>"]` to the question's variable, so the
  script would reach the question instead (see
  [Names an Id may not take](Studio-Builder-Overview#names-an-id-may-not-take));
- a Matrix, MaxDiff, Conjoint or wide Multiple choice whose **Id** is another
  question's variable name ("Duplicate answer key in questionnaire: questions
  '<a>' and '<b>' both store their answer under '<name>'."). The survey
  knows such a question by its Id (its variables are stored under their own
  names, but scripts and messages address the question by the Id), so the
  two would share one name.

It also returns warnings, which do not block. Examples: a condition that
compares with a code the variable no longer has (`UNKNOWN_CONDITION_VALUE`),
`CONTRADICTORY_VISIBILITY`, `REQUIRED_CONDITIONAL` and the piping warnings.
The engine does **not** detect forward references or empty branch rules; only
Studio's check does.

See [[Testing Your Survey|Studio-Testing-Your-Survey]] for the whole
Validation tab.

---

## Testing the logic

- **Test → Walkthrough**: take the survey yourself, including unsaved edits,
  with a panel listing each show / hide result, which branch rule matched,
  whether a Skip to fires, and where **Next** will take you.
- **Test → Simulate**: synthetic respondents that follow page, block
  (nested blocks included) and question show / hide, answer-option
  conditions, Skip to, branch rules and default next. Each simulated
  respondent is drawn into an arm of **Assign to a condition**, so pages and
  questions gated on the arm are filled for that arm, gets their own page
  order from **Randomize pages**, and is stopped by a full quota cell. The
  Walkthrough runs the assignment too (with the weighted draw), so you can
  walk each arm's route.
- **Logic map** for reachability and forward references at a glance.
- **Validation** for the engine's own verdict.

See [[Testing Your Survey|Studio-Testing-Your-Survey]].

---

## Practical advice

- Settle variable names before you publish. Renaming a variable updates the
  logic that reads it, but after publishing it also starts a new data column
  (see [Renaming variables and pages](#renaming-variables-and-pages)).
- Name pages meaningfully (`screener`, `about_you`, `thanks`). Page names are
  what rules and the Logic map show. Renaming a page updates the rules, Skip
  to targets and page scripts that point at it.
- Give every branch rule a condition, and let **Default next** be the
  "otherwise".
- Prefer **in** over a chain of **=** rows under **ANY**: it reads better and
  is one row to maintain.
- Use **chose** for multiple-choice screeners.
- Walk the survey in the **Walkthrough** after every routing change, once as
  someone who qualifies and once as someone who does not. It catches what
  checks cannot, like sending everyone to the thank-you page.

## See also

- [[The Builder|Studio-Builder-Overview]]
- [[Quotas and Randomization|Studio-Quotas-and-Randomization]]
- [[Scripts|Studio-Scripts]]
- [[Testing Your Survey|Studio-Testing-Your-Survey]]
- [[Panel Providers|Studio-Panel-Providers]]

<!-- studio-nav -->
---

← [[Codebook and Variables|Studio-Codebook-and-Variables]] · [Studio contents](Studio-Overview#all-pages) · [[Quotas and Randomization|Studio-Quotas-and-Randomization]] →
