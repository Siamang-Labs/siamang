# Coding Open Answers

Open-ended answers are rich and unwieldy: before they can go into a table
they need a **coding scheme** — a set of themes — and a decision about which
answer belongs to which theme. In Studio you build that scheme yourself, in
the **codeframe editor**: you code answers **by hand** and write short **word
rules** that code the rest, including the answers that arrive after you wrote
them. This page covers the editor, the rule syntax, how an answer gets its
themes, applying the codeframe in a flow, the table it makes, privacy and
reproducibility.

> **AI coding is switched off on this platform.** Studio used to offer **Code
> open answers…**, which had the AI assistant propose themes and assign
> answers to them. It was the one assistant feature that sent what
> *respondents* wrote — not your team's own text — to the model provider
> (DeepSeek, which processes it in China). It is switched off for every
> organization for now: the button and its dialog are gone, and a request to
> start a coding job through the API is refused with "AI coding of open
> answers is switched off on this platform." Codeframes the assistant built
> earlier keep working (see [Older codeframes](#older-codeframes-version-1)).
> The rest of the assistant is unchanged — see
> [[AI Assistant|Studio-AI-Assistant]].

---

## How Studio codes open answers

A **codeframe** is a document of your project,
`analysis/<name>.codeframe.json`, for one open-text variable. It holds the
themes, the decisions you made by hand and each theme's rules. The **Code open
answers** node of a flow applies it, and each answer is coded by the first of:

1. **By hand.** Your decision for that answer: one theme, several, or *no
   theme* (read, and belongs to none). A decision always wins.
2. **By the rules.** Each theme can have words and phrases that code the
   answers nobody decided — the ones on screen today and the ones collected
   next month, because the rules run at every run.
3. **Uncoded.** Neither reached it: it is left for you to read.

The node applies the codeframe the same way at every run — no model, no
network, no randomness. The same answers get the same themes; the scheme is a
file a reviewer can read and disagree with; it is versioned with every Save and
travels in the research bundle; and anyone who re-runs your study gets your
numbers. An analysis that called a model at run time could give different
themes next month and could not be checked.

The codeframe keeps **fingerprints** of answers, never their texts (see
[Privacy: only fingerprints are stored](#privacy-only-fingerprints-are-stored)).

> **In the example study.** A project started from the
> [example study](Studio-Projects#the-example-study) ships a codeframe
> already: `analysis/improve.codeframe.json`, for "If you could change one
> thing about your digital life, what would it be?" — six themes (*Fewer
> notifications*, *Less social media*, *Screen-free times and places*, *More
> time offline*, *Work boundaries*, *Happy as it is*), each with a definition
> and examples, and a theme and a tone for every answer it knows. It is an
> [older codeframe](#older-codeframes-version-1) (version 1), written with
> the example rather than built by the assistant, so it records no model. Its
> flow `tables` applies it (node `code`, **Also add sentiment** on) and charts
> the themes with their tone; two answers in the sample it has never seen stay
> **Uncoded**. Open it with **Edit codeframe…** on that node to code them by
> hand or give the themes rules.

---

## Before you start

- **Plan:** every plan. Coding by hand and by rules spends no AI credits.
- **Role:** members and higher build, change and save codeframes. A viewer
  can open one and read it, its answers and **Test a phrase**, but not change
  or save it.
- **Answers:** the editor lists the answers the project's responses hold —
  from every environment, or the one you pick. With none yet it says "Nobody
  has written anything in `variable` in these responses yet."; you can still
  write the themes and rules and save them.
- **Language:** the words the rules know — negations, clause words, stop
  words — are **English**. Answers in any other language keep their words and
  are matched by terms written in them; they just get no negation read in them.

---

## Open the editor

From any of these:

- **A flow's Code open answers node.** Under **Codeframe** (a dropdown of the
  project's codeframes, **— choose a codeframe —**): **New codeframe…** when
  none is chosen, **Edit codeframe…** for the chosen one. Opened from a node,
  the editor shows the answers that flow's **Responses** node reads, and a
  new codeframe is set on the node at once.
- **Files → Codeframes:** **New codeframe…**, or **edit** on a codeframe's
  row (see [[Files|Studio-Files]]).
- **History:** a Save's **Documents** lists each codeframe as *codeframe
  name*, with **Edit** beside **.json**. It opens the codeframe's current
  version; one the project no longer has opens as that Save left it, to be
  saved again.

**New codeframe…** opens the **New codeframe** dialog: "A codeframe codes the
answers to one open-text question: its themes, the words and phrases that give
each one, and the answers you code by hand. It is saved as
`analysis/<name>.codeframe.json` — with fingerprints of the answers, never
their text — and applied by the Code open answers node, the same way at every
run."

| Field | Meaning |
|---|---|
| **Variable** | the open-text questions of the questionnaire (`name — label`; not a date, email or phone field) and the text typed into an **Other (please specify)** (`<variable>_other`); **Another variable…** lets you type a name |
| **Name** | the file name (`file name: analysis/<name>.codeframe.json`): lower-case letters, digits and `_`, starting with a letter. It is filled in from the variable |

**Open the editor** goes on; **Cancel** does not. A name already taken says "A
codeframe of this name exists — choose another name, or edit that one." with a
button **Edit *name***.

The editor's address is `/flows/codeframe/<name>`, and its back button
returns where you came from: **Back to *flow***, **Back to Files**, **Back to
History** (or **All flows**).

---

## The editor at a glance

```
← Back to feedback
Codeframe why      analysis/why.codeframe.json · edited · coding by hand and by rules, no model
                                                           [↶] [↷]  [⋯]  [ ✓ Save changes ]
Answers from [every environment ▾]   [ ] Only completed responses

[■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■·······]
 ■ By hand 12.5%   ■ By rules 75%   □ Uncoded 12.5%   of 8 respondents who answered · 8 distinct answers

 Themes  1–9 give the first nine to …   [+ Add theme] │ [Answers] [Suggested words] [Test a phrase]
 1  Late delivery · Delivery             3 · 37.5%    │ [Search answers]  Show [All answers ▾]   8 answers
 2  Damaged · Delivery                   1 · 12.5%    │ [ ] The delivery was late                       1
 3  Rude staff                           1 · 12.5%    │       Late delivery  rule: late → “late”
 4  Nothing / Don't know  alone          2 · 25%      │ [ ] wasn't late, all fine                       1
 Nets: Delivery 3 (37.5%)                             │       uncoded  Late delivery: “late” is negated
 ┌ 1  Theme 1                          ↑  ↓  delete ┐ │ [ ] Great!                                      1
 │ Label             Late delivery                  │ │       by hand: no theme
 │ Definition        (optional)                     │ │ …
 │ Net               Delivery                       │ │
 │ Words and phrases (late ×) (delay* ×) [add…]     │ │
 │ But not           [a word that rules it out]     │ │
 │ ▸ More                                           │ │
 └──────────────────────────────────────────────────┘ │
 ▸ Codeframe settings                                 │
```

- **The head:** `Codeframe <variable>`, the file, and "new, not saved yet" or
  "edited"; **Undo** and **Redo**; the tools menu (**This codeframe**: how many
  themes and answers coded by hand, and the draft's state); and **Save
  changes** (**Saved** when there is nothing to save).
- **Answers from** chooses the responses the answers come from: **every
  environment**, or one environment ("*env* (and imported rows)"); **Only
  completed responses** leaves the others out. Opened from a node, both are
  set as that flow's Responses node reads them ("as the flow's Responses node
  reads them"). This changes what the editor shows, not the codeframe.
- **The coverage bar:** the share of the respondents who answered that is
  coded **By hand**, **By rules** and **Uncoded**, with how many answered, how
  many distinct answers there are and how many you coded as no theme. It is
  redrawn a moment after each change. While the codeframe has errors it reads
  "*N* distinct answers · the coverage shows once the codeframe can be
  applied".
- **Left:** the themes and the selected theme's details, then **Codeframe
  settings**.
- **Right:** three tabs — **Answers**, **Suggested words** and **Test a
  phrase**.

Everything the editor shows about the answers is computed on the server by
the same engine code the Code open answers node runs, so what you see is what
a flow will get.

---

## Themes

**Add theme** adds *Theme 1*, *Theme 2*, … with the next free code. The list
shows each theme's key (**1**–**9** for the first nine), its label, its net,
**alone** for an exclusive theme, and how many respondents it has with their
share ("3 · 37.5%"; hover for how many by hand and how many by rules). Click
a theme to edit it:

| Field | What it does |
|---|---|
| **Label** | what the table shows |
| **Definition** *(optional)* | "what belongs here, for whoever codes" |
| **Net** *(optional)* | "themes with the same net are also counted together" — type a name, or pick one already used (see [Nets](#nets)) |
| **Words and phrases** | the terms that give the theme (see [Writing rules](#writing-rules)) |
| **But not** | terms that rule it out where they appear |

Under **More**:

| Field | What it does |
|---|---|
| **Must also contain** | the theme is given only where one of these terms is present too. **Another list it must also contain one of** adds a second list (**And also one of**): then one term of *each* list must be present |
| **Reads** | "where the words must all be": **part of the answer (a clause)**, **the whole answer**, or as the codeframe does |
| **Only when no other theme applies (Nothing, Don't know)** | an [exclusive theme](#exclusive-themes) |
| **Priority** | "the higher is kept where an answer keeps one theme, or fewer" (see [Priority](#priority)) |

Type a term and press `Enter` (or type a comma); **×** on a chip removes it,
and `Backspace` in the empty box removes the last one. A term with a problem is
marked, and the message is written under the chips.

The detail's head shows the theme's code and its counts: "*N* respondents
(*P*%) · *h* by hand · *r* by rules", and "· *n* mention it only negated" —
the respondents who wrote one of its words under a negation and so did not get
it (read them, and code them by hand or with a `not_` term if they belong).

**↑** and **↓** move a theme: the order sets the keys **1**–**9** and breaks
ties of priority. A theme's code never changes when you rename or move it.
**Delete** asks "Delete theme “*label*”?" — "*N* answers were given it by hand;
they lose it (and an answer that had only it goes back to the rules)." — and
**Delete theme** removes it with its words and phrases.

---

## Writing rules

A theme is given to an answer where, **in one clause** (or in the whole
answer, with **Reads** set so):

- one of its **Words and phrases** matches,
- each **Must also contain** list has a term that matches, and
- no **But not** term matches.

Under the theme's words the editor reminds you of the syntax: "word* for word
forms · a|b for either · not_word for a negated mention · a ~3 b for words
near each other. A negated mention does not count: late does not find
“wasn't late”; not_late finds only that."

| Term | Finds | Does not find |
|---|---|---|
| `late` | *It was LATE!* | *latest*, *wasn't late* |
| `delay*` | *delay*, *delays*, *delayed* | *relay* |
| `*charg*` | *charge*, *recharging* | |
| `slow\|late` | *slow* or *late* | |
| `customer service` | *the customer service was bad* | *service to the customer* |
| `staff ~3 rude` | *the staff were very rude*, *rude staff* | *rude. The staff*, *rude, the staff* |
| `not_late` | *wasn't late*, *never late* | *it was late* |
| `not_friendly staff` | *no friendly staff* | *friendly staff* |
| `don't know` | *I don't know*, *I dont know*, *I do not know* | *I don't really know* (write `don't ~2 know`) |
| `would not recommend` | *would not recommend*, *wouldn't recommend* | |
| `not happy` | *not happy*, *wasn't happy* | *never happy* |
| `цена`, `café` | *Цена высокая*, *le café* | `cafe` does not find *café* |

- **Case** does not matter; **accents** do (*café* is not *cafe*).
- **`*`** stands for any letters of a word, anywhere in it.
- **`|`** gives alternatives at one place of a phrase:
  `customer serv*|support`. One alternative cannot be two words: write
  `e-mail` and `email` as two terms.
- **`~N`** finds two words (or phrases) within *N* words of each other, in
  either order, inside one clause — a comma ends its reach as a full stop does.
  At most `~20`.
- **`not_`** asks for a negated mention only. A negation written in the term
  itself (`not late`, `don't know`) is the term's own.
- **Words are split as in an answer:** `e-mail` and `n/a` are two words each
  (a `-`, `/` or `·` between two letters), so they find *E-mail* and *N/A*.
  Quotation marks around a term are dropped (`"late"` is `late`).
- **No regular expressions.** A term beginning `re:` is an error: "regular
  expressions are not supported: write the words, with * for word forms
  (delay*), | for alternatives (slow|late) and ~N for words near each other
  (staff ~3 rude)". Rules stay short enough to read back and defend.

### Negation

*not, no, never, cannot, without, nothing, none, nobody, neither, nor, hardly,
barely* and every *n't* form negate the next **three words**, stopping early
at the end of a clause and at *and, or, yet*. A term finds only mentions that
are **not** negated: *The delivery wasn't late* is not coded *Late delivery*,
and *not cheap, and fast* is negated only for *cheap*.

The spellings of *n't* are one: *dont* is read as *don't*, *cannot* and *can
not* as *can't*, and *do not, was not, would not*… (after *do, does, did, is,
are, was, were, has, have, had, can, could, will, would, shall, should, must,
need, might*) as *don't, wasn't, wouldn't*… — in the answers and in your
terms alike. The word *not* in a term stands for every negation written with
it: `not happy` finds *wasn't happy*.

What negation costs: *never received my parcel* is not coded *Parcel*, and
*not enough staff* is not coded *Staff*. The editor counts, per theme, the
respondents it loses this way, and each such answer shows "*theme*:
“*words*” is negated" — code the ones that belong by hand, or add a `not_`
term.

### Clauses

A clause ends at a line break, at punctuation (`. , ; : ! ? ( ) [ ] { }`,
the dashes `– —`, `…`, a bullet `•`, `|`), at `-`, `/` and `·` when they do
not join two letters (*fast - cheap*, *late / broken*), and at the words
*but, however, although, though, whereas, except* and *plus*. In *Delivery was
quick but the box was damaged*, a theme that must also contain *delivery* and
has the word *damaged* does not match when it reads a clause — they are in
different clauses — and does when it reads **the whole answer**. An answer
written on several lines is read line by line.

### Replacements

**Codeframe settings → Replacements** ("whole words or phrases, replaced
before the rules read an answer: typos, synonyms"): each row replaces the
words on the left (**words to replace**) with those on the right (leave it
empty — **(nothing)** — to drop them). `delievery → delivery` fixes a common
typo once for every theme; `cust service → customer service` makes one phrase
of two. Replacements are made in one pass: a word one replacement writes is
not replaced again. **Add a replacement** adds a row; a row with nothing to
replace is left out until you type its words ("Type the words it replaces —
until then it is left out.").

### Mistakes the editor catches

The engine checks the codeframe as you edit. **Errors** stop it from being
applied or saved; they are listed above the themes — "*N* errors — the
codeframe cannot be applied or saved until they are fixed." — and beside the
term, theme or setting at fault. Examples: "the codeframe has no themes" (a
new codeframe), a theme without a label, a code used twice, a `re:` term, a
`~N` over 20, a term longer than 200 characters, the same words replaced
twice.

**Warnings** do not stop anything but say what does nothing: "*term* can never
match within a clause: 'but' ends a clause (give the theme the scope
'answer')", "*term* has a part that can never match, 'e-mail': it is two words
…", "*term* is both included and excluded, so it never codes the theme", "its
rules have no include term, so its require and exclude terms do nothing", "the
net '*name*' has one theme, so no net row is shown for it", a term given
twice.

---

## Coding answers by hand

The **Answers** tab lists the variable's **distinct answers**, the most
frequent first, 100 to a page (**Previous page** / **Next page**, "1–100 of
*N*"). Answers that differ only in case or spacing are one answer. Each row
shows the answer, how many respondents gave it, its themes and how it got
them:

- **by hand**, or **by hand: no theme**;
- **rule: *term* → “*words*”** for each rule that gave it a theme — for
  example `rule: delay* → “delayed”`;
- **uncoded**;
- "*theme*: “*words*” is negated" when a theme's word is there, negated;
- "*theme* set aside: the codeframe gives one theme an answer, and keeps the
  one ranked highest" for a decision naming several themes in a codeframe that
  gives one.

**Search answers** finds answers containing the text. **Show** filters them:
**All answers**, **Uncoded**, **Coded by hand**, **Coded by rules**, **No
theme (by hand)**, or one theme (**With the theme**). While the codeframe has
errors only the search applies.

**Select** answers: a click selects that answer alone; `Ctrl/Cmd`-click or its
box adds it to the selection or takes it out; `Shift`-click selects a range.
The toolbar above the list then shows "*N* selected" and a button per theme,
**No theme**, **Back to rules** and **Clear selection**.

| Key (in the list) | Does |
|---|---|
| `↑` `↓`, `Home` `End` | move |
| `Space` (`Shift + Space`) | select (a range) |
| `Ctrl/Cmd + A` | select every answer on the page |
| `1`–`9` | give the selected answers theme 1–9 of the list — or take it away when they all have it |
| `0` | no theme: read, and belongs to none |
| `Delete` | back to the rules: take your decision away |
| `Esc` | clear the selection |

With nothing selected, a key codes the highlighted answer — click an answer,
press a number, move on. The list says so below it: "A click selects one
answer; ⌘/Ctrl-click or its box adds it to the selection, Shift-click a range.
…".

What a decision does:

- In a codeframe that gives **several themes**, a theme is added to the
  answer's others; in one that gives **one**, it replaces them.
- A decision is final for that answer: the rules no longer change it. **Back
  to rules** (or `Delete`) hands it back to them.
- **No theme** is a decision too: the answer counts as coded — in the table's
  **No theme** row — rather than uncoded.
- A decision is kept for the answer's text wherever it appears, in every
  environment and in answers collected later that say the same.

---

## Several themes, nets, exclusive themes and priority

### Several themes an answer

**Codeframe settings → An answer may have several themes.** Off (the
default), each answer gets one theme and the theme variable is an ordinary
single-choice (nominal) variable. On, an answer can have several, the theme
variable is **multiple-choice** (a list of codes per respondent) and **At
most** ("themes an answer — 0 for no limit") caps how many the rules give.
Your own decisions are kept as you made them.

Turning it off with answers coded by hand to several themes says "*N* answers
coded by hand have several themes, and the codeframe gives one an answer: each
keeps the one ranked highest (priority, then order)." — **Keep only that theme
in each** rewrites those decisions so the file says what is applied.

### Nets

Themes with the same **Net** form a net: a row that counts a respondent once,
however many of its themes they have. *Late delivery* and *Damaged* in the net
*Delivery*: a respondent with both counts once in **Delivery (net)**. The
editor shows the nets under the themes ("Nets: Delivery 3 (37.5%)"); a net
needs two themes or more.

### Exclusive themes

**Only when no other theme applies (Nothing, Don't know)** makes a theme
exclusive (**alone** in the list): the rules give it only when no other theme
matched the answer. *Nothing, but the delivery was late* is coded *Late
delivery*, not also *Nothing*.

### Priority

When the rules match more themes than an answer may keep — one, or **At most**
*N* — the answer keeps those ranked highest: the higher **Priority** first,
ties by their order in the list. With one theme an answer, *Box arrived
damaged, and two days late* matches *Late delivery* and *Damaged* and keeps
*Late delivery* (it comes first); give *Damaged* priority 1 and it keeps
*Damaged*.

### The order, in full

For each answer:

1. Your decision, if you made one — as you made it (a one-theme codeframe
   keeps the highest-ranked of several).
2. Otherwise the rules: every theme that matches; an exclusive theme dropped
   when another matched; the rest ranked by priority, then order; cut to **At
   most**, or to one.
3. Otherwise uncoded.

---

## Suggested words and Test a phrase

**Suggested words** lists the words and two-word phrases the answers not coded
yet hold most — up to 30 of each, held by two respondents or more — with how
many respondents used each (hover for an example answer). "click one to add it
to *theme*": a click adds it to the selected theme's **Words and phrases**.
English stop words are left out, and a word written negated comes as
`not_word`, ready to use. While the codeframe cannot be applied, the list is of
every answer.

**Test a phrase** shows how the codeframe reads one sentence ("how the
codeframe would code it, step by step"): type it under **A phrase** and press
**Test**.

- The result: the themes (or **No theme**) and how — "by the rules", "by hand
  (a coder's decision for this answer overrides the rules)", "uncoded".
- **Words:** the words as the rules read them (*do not* as *don't*), the
  negated ones marked (hover: "negated by “wasn't”").
- **Clauses:** where the answer was split.
- **Rules:** each rule that fired, was **vetoed** — with why, for example "it
  requires one of 'staff', 'driver', 'courier', and none is in this clause" or
  "it excludes 'free', which is there ('free')" — or was blocked by a
  **negated** mention.
- **Set aside:** themes that matched and were dropped — "exclusive, and
  another theme matched", "the codeframe gives one theme an answer, and one
  ranked higher matched", "max_codes keeps 1, and they ranked higher".

*The delivery wasn't late, but the box was broken* reads as two clauses, *the
delivery wasn't late* and *the box was broken*: *Late delivery* is negated,
*Damaged* fires — **Damaged — by the rules**.

---

## Codeframe settings

| Setting | Meaning |
|---|---|
| *(first line)* | "Codes `variable` · English (negations, clause words, stop words) · answers in other languages keep their words, with no negations found" |
| **Theme variable** | "the variable the flow's node makes" — `<variable>_theme` by default. A node's own **Theme variable** overrides it |
| **An answer may have several themes** | see [Several themes an answer](#several-themes-an-answer) |
| **At most** | with several themes: the most the rules give an answer; `0` for no limit |
| **Rules read** | "unless a theme says otherwise": **each part of an answer (a clause)** (the default) or **the whole answer** |
| **Replacements** | see [Replacements](#replacements) |

---

## Saving

**Save changes** (or `Ctrl/Cmd + S`) opens the ordinary **Save** dialog: the
codeframe becomes `analysis/<name>.codeframe.json` in a new Save, and it is in
**History** like any document. The button is disabled while the codeframe has
errors ("Fix the codeframe's errors first"). A saved codeframe is checked like
any document; one with themes but no rules and no decisions warns "This
codeframe has themes but no rules and no answers coded by hand, so it codes
nothing."

- **Undo** and **Redo** (`Ctrl/Cmd + Z`, `Shift + Ctrl/Cmd + Z`) step through
  your edits.
- **A new codeframe** is a document only once saved. Until then it is kept in
  the browser tab it was started in: leaving asks "Leave the codeframe?" —
  "This codeframe is not saved yet. It stays in this tab until you close it:
  open it again from the node or from Files to go on, or Save it first." The
  node that started it shows "*path* is not saved yet: it is kept in this tab
  until you save it in its editor."
- **Changes to a saved codeframe** stay as a draft, as the Builder's do:
  "Your changes are not saved as a version. They stay as a draft — open the
  codeframe again to go on, or Save them first." Closing the browser tab with
  unsaved changes asks first.
- **Started from a node**, the node's **Codeframe** is set to the new file at
  once — a change to the flow, which you save in the flow editor.
- **One person edits at a time**, as with other documents: while a colleague
  edits, you follow their changes live and can **Take over** (see
  [[Working Together|Studio-Collaboration]]).

There is no button to delete a codeframe; one that no node names does
nothing.

---

## Applying it in a flow

Add **Code open answers** (Prepare) after your source and cleaning steps:

| Parameter | Value |
|---|---|
| **Codeframe** | the file, from the dropdown (**— choose a codeframe —**) |
| **Theme variable** | leave empty for the codeframe's own (**Codeframe settings → Theme variable**, `<variable>_theme` by default) |
| **Also add sentiment** | only for an [older codeframe](#older-codeframes-version-1) that carries a tone for its answers |

The node has three outputs:

- **`data`** — the dataset plus the theme variable, labeled `Theme:
  <variable>`, with your theme labels as value labels. With one theme an
  answer it holds the code; with several, the list of codes. An answer coded
  as no theme and an uncoded one have nothing there, so a **Frequencies** of
  the theme variable counts the respondents *with a theme*; the theme table
  below counts everyone who answered.
- **`table`** — the theme table (below). Wire it into a **Report section**;
  a **Result chart** draws its themes.
- **`stat`** — the table's statistics. Connect it to a **Live tile** to watch
  the coverage as answers arrive.

**The theme variable in later nodes.** The nodes after it offer it in their
variable lists ("made by *node*") — for a **Crosstab** of themes by region,
say — whether you typed its name in **Theme variable** or left it to a
codeframe that is saved in the project. A multiple-choice theme variable is
treated as a multiple-choice question: a donut, a **Split by**, a banner
column or a Likert chart of it is refused. The sentiment variable is not
offered in the pickers.

**Run to here** on the node previews it with the codeframe of your current
Save, as a run does. The flow's check reads the project's codeframes, so a
codeframe the run could not apply is an error of the flow before it runs:
"Parameter 'codeframe' of *node*: *path* cannot be applied: …", or "… codes
'*variable*', which is not a variable of this questionnaire."

### The table

One row per theme and per net — a net's row, "*net* (net)", with its themes
under it — ordered by their counts; then **No theme** (when you coded answers
as no theme), **Coded**, **Coded by hand**, **Coded by rules** and
**Uncoded**. Every % is of the **respondents who answered**. With several
themes an answer, the themes add up to more than 100 %, and the table says
so.

An example. Eight people answered *Why that score?*: *The delivery was
late*; *Box arrived damaged, and two days late*; *The driver was rude*;
*Nothing*; *wasn't late, all fine*; *Great!*; *The parcel was delayed again*;
*I don't know*. The codeframe gives several themes an answer: *Late delivery*
(`late`, `delay*`) and *Damaged* (`damag*`, `broken|broke`) in the net
*Delivery*; *Rude staff* (`rude`, `unfriendly`, and it must also contain one
of `staff`, `driver`, `courier`); and *Nothing / Don't know* (`nothing`,
`don't know`), exclusive. A coder decided *Great!* has no theme. The table:

| Theme | N | % |
|---|---|---|
| Delivery (net) | 3 | 37.5 |
| Late delivery | 3 | 37.5 |
| Damaged | 1 | 12.5 |
| Nothing / Don't know | 2 | 25.0 |
| Rude staff | 1 | 12.5 |
| No theme | 1 | 12.5 |
| Coded | 7 | 87.5 |
| Coded by hand | 1 | 12.5 |
| Coded by rules | 6 | 75.0 |
| Uncoded | 1 | 12.5 |

The statistics under it: **Variable**, **Answered** (8), **Themes** (4),
**Coverage** ("87.5 % of the answers are coded"), **Coded by hand**, **Coded
by rules**, **Distinct uncoded answers** (how many different answers are left
to read), **Percentages** ("of the respondents who answered; a respondent can
have several themes, so the themes add up to more than 100 %") and, with nets,
**Nets** ("a net counts a respondent once, however many of its themes they
have"). The table counts answers, not weights: after **Apply weight** it stays
unweighted and says so ("Weight: unweighted (the weight 'weight' is not
applied)").

An older codeframe (version 1) gives the table it always did: theme rows as
shares of the **coded** answers, then **Coded** and **Uncoded** as shares of
everyone who answered, with **Coverage** "… % of the answers have a theme"
and, with **Also add sentiment**, the **Negative %**, **Neutral %** and
**Positive %** of each row and the **Sentiment** and **Net sentiment**
statistics. Sentiment asked of a codeframe without it reads "not in this
codeframe".

---

## New answers: every run codes them

The rules are not a one-off: at every run the node codes **all** the answers
it is given — the ones you saw in the editor and the ones collected since —
by your decisions first and the rules second. A new answer that says what an
earlier one said gets that decision; one the rules recognize gets its themes;
the rest land in **Uncoded**.

To keep up as fieldwork continues:

1. Open the codeframe (**Edit codeframe…**) and set **Show** to **Uncoded**.
   The editor reads the answers again once its last reading is a minute old,
   so an answer that has just arrived can take up to a minute to appear.
2. Code them by hand, or better, add the words that would have caught them
   (**Suggested words** lists the commonest).
3. **Save**, and run the flow (or let its schedule do it).

A **Live tile** of the node's `stat` output shows the coverage falling when
new answers bring new themes.

> **Note.** A rule you change recodes every answer it touches on the next run,
> the earlier ones too — that is what keeps the numbers consistent. Compare
> the two versions in [[History and Versions|Studio-History-and-Versions]]
> before you save a big change, and say in your methods that the scheme was
> revised.

---

## Privacy: only fingerprints are stored

- **The answers stay in Studio.** The editor reads them from the project's
  own responses and shows them only to members of the project. No model, no
  provider, no other service sees them.
- **The codeframe holds fingerprints, never answers.** A decision is stored
  under the answer's fingerprint — sixteen hexadecimal characters computed
  from its text, case and spacing set aside — not under the text. The engine
  refuses a codeframe (version 2) that holds an answer's text, and editing an
  older one leaves its example answers out.
- **A fingerprint is not a disguise.** It cannot be turned back into the
  text, but whoever has the file and guesses an answer's exact words can
  confirm that it was given. And the words you type into rules and labels are
  stored as you typed them. Treat a codeframe like the study's other
  documents: it is in every Save and every research bundle.

See [[Security and Privacy|Studio-Security-and-Privacy]].

---

## Older codeframes (version 1)

A codeframe the assistant built before AI coding was switched off — or the
example study's — is **version 1**: themes (with example answers), a theme for
each answer it was built from, sometimes a tone, and no rules. The node applies
it exactly as before, with the same table.

Opened in the editor it says "This codeframe is version 1: a theme for each
answer it was built from, and no rules. Editing it makes it version 2 — its
*N* example answers are left out, since version 2 keeps only fingerprints of
answers." Its decisions become your decisions by hand; you can then add rules,
nets and the rest. The version 1 file stays in History.

---

## Reproducibility

- The codeframe is a document of the Save: it is in every research bundle
  (`analysis/<name>.codeframe.json`), and the flow's script loads it from
  there. Re-running the bundle codes the same answers the same way — your
  decisions and the same rules, with no model and no account.
- Its fields, for a reviewer: `variable`, `into` (the theme variable),
  `language` (`en`), `multiple`, `max_codes`, `scope`, `replace`, `themes`
  (code, label, definition, `group` — the net —, `exclusive`, `priority`,
  `rules` with `include`, `require`, `exclude`, `scope`) and `assignments`
  (fingerprint → a code, a list of codes, or `[]` for no theme). A codeframe
  the assistant built also records which model built it and when (`model`,
  `built_at`) and how many answers it read (`source_rows`).
- The **Methods draft** says how the answers were coded: "by a coder's
  decision where one was recorded (*N* distinct answers) and otherwise by the
  scheme's word rules, which read answers collected later the same way".
- The **Documents** tab of a Save in History downloads it as `.json`.
- A bundle's engine pin may lag behind Studio: at such a pin the **Code open
  answers** node stops with an error. See
  [[Reproducibility: Code, Bundles and Citation|Studio-Reproducibility]].

---

## Other ways

- **Code outside Studio.** Export the responses (**Data → Export**, see
  [[Data Exports|Studio-Data-Exports]]), code the open answers in your own
  tool, and analyze the coded file there.
- **Ask a closed question as well.** A single-choice follow-up ("Which of
  these comes closest?") gives a coded variable you can tabulate and, with
  **Recode**, regroup.
- **Keep the verbatims in the report.** For a small study, quoting answers in
  a section's text may serve better than any coding.

## See also

- [[Node Reference|Studio-Node-Reference]] — [Code open answers](Studio-Node-Reference#code-open-answers)
- [[Analysis Flows|Studio-Flows]]
- [[Files|Studio-Files]]
- [[Security and Privacy|Studio-Security-and-Privacy]]
- [[Reproducibility: Code, Bundles and Citation|Studio-Reproducibility]]

<!-- studio-nav -->
---

← [[Cleaning and Weighting Data|Studio-Cleaning-and-Weighting]] · [Studio contents](Studio-Overview#all-pages) · [[Reports|Studio-Reports]] →
