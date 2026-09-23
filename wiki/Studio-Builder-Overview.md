# The Builder

The **Builder** tab is where the questionnaire is made. It edits the real
engine document, so anything you build here is something the engine can run,
validate and turn into Python. This page is a tour of the screen: the header,
the tabs, the Structure view, pages and blocks, the Inspector, previewing,
saving, drafts and the read-only states. The question types themselves are in
[[Question Types|Studio-Question-Types]].

---

## The screen

```
┌ [Survey title                ]  Version 17 · edited ▾        ↶ ↷  [More ▾] [Preview] [Save changes] ┐
├───────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Structure · Codebook · Logic map · Validation · Test · More ▾                                         │
├───────────────┬──────────────────────────────────────────────────────────┬──────────────────────────┤
│ PAGES         │ [Structure|Preview]  Page 3 of 5 ‹ Brands ›  [Library] ↑↓ │ INSPECTOR                │
│ [Find question…] [id] │ ▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬ (page meter)                     │ [Single choice ▾] q7 → q7 [x]│
│ 1 Before we start     │ Brands                                           │ ▸ Question               │
│ 2 Awareness           │ ┌ Single choice  q7 → q7   optional  show if ↑↓┐│ ▸ Options                │
│ 3 Brands   ⤳          │ │ Which brand did you use most?                ││ ▸ Variable     codebook  │
│   ● Which brand…      │ │ ○ Acme  ○ Globex  ○ Initech                  ││ ▸ Logic                  │
│   ○ Why?              │ └──────────────────────────────────────────────┘│ ▸ Advanced               │
│ 4 About you           │ ┌ Block: About you                         ↑↓ ┐│ ▸ Comments               │
│ 5 Thank you  final    │ │ …                        [+ Add to block]    ││                          │
│ [+ Page] [+ Question] │ └──────────────────────────────────────────────┘│                          │
└───────────────────────┴──────────────────────────────────────────────────┴──────────────────────────┘
```

Three columns: the **pages rail** on the left, the **canvas** in the middle and
the **Inspector** on the right. The Inspector shows whatever you selected.

---

## The header

**Title** — the survey title, editable in place. It cannot be empty: a Save of
a questionnaire with an empty title is refused.

**Version chip** — reads **Version 17** (or **No saved version** before the
first Save), followed by **· edited** when you have unsaved edits (**· being
edited** while you follow a colleague). Hover, focus or tap it for a popover
with the size of what is on the screen — **pages**, **questions**,
**variables** and, if there are any, **quotas** — and the state of your draft.

**↶ ↷** — **Undo** and **Redo** (`Ctrl/Cmd + Z`, `Shift + Ctrl/Cmd + Z` or
`Ctrl/Cmd + Y`). See [Undo and redo](#undo-and-redo).

**More ▾** — the occasional actions:

| Item | What it does |
|---|---|
| **Import** | replaces the working document with a questionnaire from a file or pasted JSON — [[Importing Questionnaires\|Studio-Importing-Questionnaires]] |
| **Export Python** | downloads the `questionnaire.py` generated for the **current Save** — [Export Python](#export-python) |
| **Discard changes** | drops all unsaved edits and returns to the last Save (no confirmation; disabled when there is nothing to discard) |

**Preview** — builds a standalone preview of the current Save and opens it in a
new tab. See [The Preview button](#the-preview-button).

**Save** / **Save changes** — opens the Save dialog (`Ctrl/Cmd + S`). The label
reads **Save changes** when you have unsaved edits. See [Saving](#saving).

---

## The Builder tabs

Five tabs are always in the strip; five more are under **More ▾**, because they
are set up once per study rather than used every minute. On a narrow window
more tabs move into **More ▾**; the tab you are on always stays visible. The
**Structure** tab carries an **edited** marker while you have unsaved edits.

| Tab | What it is for | Details |
|---|---|---|
| **Structure** | building: pages, blocks, questions and the Inspector | this page |
| **Codebook** | every variable in one table | [[Codebook and Variables\|Studio-Codebook-and-Variables]] |
| **Logic map** | the routing between pages and the conditions on questions | [[Logic and Branching\|Studio-Logic-and-Branching]] |
| **Validation** | structure checks, the engine's check without saving, the last Save's issues, the AI review | [[Testing Your Survey\|Studio-Testing-Your-Survey]] |
| **Test** | walkthrough, simulated data, a public preview link | [[Testing Your Survey\|Studio-Testing-Your-Survey]] |
| **More ▾ → Quotas** | quota cells | [[Quotas and Randomization\|Studio-Quotas-and-Randomization]] |
| **More ▾ → Randomization** | every shuffle in one place | [[Quotas and Randomization\|Studio-Quotas-and-Randomization]] |
| **More ▾ → Scripts** | the behavior library and custom JavaScript | [[Scripts\|Studio-Scripts]] |
| **More ▾ → Theme** | colors, fonts, logo, progress, wording | [[Theme and Branding\|Studio-Theme-and-Branding]] |
| **More ▾ → Source** | the questionnaire as JSON | [The Source tab](#the-source-tab) |

---

## Question Id and variable name

> **Important — keep each question's Id identical to its variable name.**
> A single-answer question (Single choice, Likert scale, Number, Open text,
> Ranking, and Multiple choice in the array layout) stores its answer under the
> question's **Id** — that is the name of its column in your data. Conditions,
> piping and quotas, on the other hand, look an answer up by its **variable
> name**. When the two differ, a condition on that variable never matches,
> piping shows the placeholder instead of the answer, a quota on it never
> fills, and the data column is not called what your codebook says.
> **Presets** create exactly this mismatch (Id `q5`, variable `nps_5`), and so
> does renaming a variable in the Variable card.
> **Fix:** select the question, open **Advanced → Id** and set it to the
> variable name (for example `nps_5`). Every question card shows
> `id → variable` in its header, so a mismatch is easy to spot. Matrix,
> MaxDiff and Conjoint questions already store each answer under its own
> variable name.

---

## The Structure view

### The pages rail

The left rail lists the pages in interview order: number, title (or name if
the page has no title) and, for special pages, a pill — **final**,
**screen-out** or **redirect**. A `⤳` marks a page with branch rules.

The **current page** unfolds to show its questions and blocks:

- a block shows a folder icon, its title and `⇄` when its questions are
  shuffled;
- a question shows a dot — filled for **required**, a ring for **optional** —
  its text (or **(no text)**) and a `?` when it has a show/hide condition.
  Hover to see `id → variables`.

At the top of the rail:

- **Find question…** — filters the current page's questions by text, id or
  variable name;
- **id** — shows question ids instead of their texts ("Show ids instead of
  text").

Click a page to select it (the Inspector shows its properties); click a
question or block to select it.

### Adding pages and questions

The bottom of the rail has two buttons.

**+ Page** opens a menu and inserts the new page **after the current page**:

| Menu item | Creates |
|---|---|
| **Content page** | an ordinary question page, titled "New page", named `page`, `page_2`, … |
| **Final page** | a thank-you page: "Thank you" / "Thank you for taking part." |
| **Screen-out page** | a screen-out: "Thank you" / "You do not qualify for this study." |
| **Redirect page** | a redirect to `https://example.com` (change it in the Inspector) |

**+ Question** opens a two-column menu — **Types** (the nine question types)
and **Presets** (eight ready-made configurations) — with **Block** at the
bottom of the Presets column. The new item goes **at the end of the current
page**, or at the end of the **selected block** when a block is selected. See
[[Question Types|Studio-Question-Types]] for what each one is.

New questions are called **New question**, are optional, and get the next free
id `q1`, `q2`, … Their variable is named after the id (`q7`) — or, for a
preset, after the preset (`nps_7`, `yes_no_7`) — see
[Question Id and variable name](#question-id-and-variable-name).

### The canvas bar

Above the page:

- **Structure | Preview** — the editable cards, or the survey as the respondent
  sees it ([Structure and Preview](#structure-and-preview));
- the pager — **Page 3 of 5**, **‹** and **›** to move between pages, and the
  page's title in between (click it to select the page);
- **Library** — **Insert from library…**, **Save question to library…** /
  **Save block to library…** (disabled as **Save selection to library…** until
  you select a question or block: "Select a question or a block first") and
  **Save questionnaire as template…** — see
  [[Question Bank, Templates and Library|Studio-Question-Bank-and-Library]];
- **↑ ↓** — **Move page up** / **Move page down** in the interview order.

A thin meter under the bar shows where the page sits in the questionnaire.

### Question cards

Each question is a card with its type, `id → variables`, its text (or
*Question text…*), its hint and a layout sketch of the answers. The sketch is a
quick outline, not the real runtime — for that, switch to **Preview**.

Pills on a card:

| Pill | Meaning |
|---|---|
| **optional** | the question is not required (required questions carry no pill — they are the normal case) |
| **show if** / **hide if** | the question has a condition; hover to read it |
| comment count | open comments on this question |
| **→ page_name** | the question has **Skip to** set |
| **script** | a script on the **Scripts** tab targets this question |

A card for a choice question with no options says "No answer options yet. Add
choices in Options."

A **block** is drawn as a frame with its title, a **randomized** pill when its
questions are shuffled, a **show if**/**hide if** pill, its questions inside
and an **Add to block** menu at the bottom.

Each card and block has **Move up** / **Move down** buttons, which move it
within its own page or block.

### Empty states

| You see | Meaning |
|---|---|
| "This page has no questions yet." + **Add your first question** | an empty question page |
| "A text-only page — add a question to make it interactive." + **Add your first question** | a page that has a Body but no questions — see [Pages and page kinds](#pages-and-page-kinds) before adding one |
| "No pages yet." + **Page** | the questionnaire has no pages |
| **No questionnaire yet** — "This project has no survey/questionnaire.json. Create one from the empty template, or restore a Save that has one." | the project has no questionnaire document; **Create questionnaire** opens the Save dialog with a one-page questionnaire; **Draft from a brief** asks the [[AI Assistant\|Studio-AI-Assistant]] *(Plus)* |

---

## Pages and page kinds

A **page** is what the respondent sees at one time. The page Inspector's
**Kind** has four values:

| Kind (Inspector) | What the respondent sees | Body |
|---|---|---|
| **Content** | the page title, the questions, **Previous** and **Next** | **not shown** — see below |
| **Final (thank you)** | the title and the Body (without them: "Thank you for participating" / "Your responses help inform open research."), plus the response ID and submission time; the interview is submitted as **completed** | shown |
| **Screen-out** | the title (default "Thank you") and the Body; the interview is submitted as **screened out** | shown |
| **Redirect** | the title and the Body, "Redirecting you now. Continue if you are not redirected.", then the browser goes to the **Redirect URL** after **Delay (s)** seconds (5 if empty) | shown |

Give every Final and Screen-out page a **Title** and **Body** of your own: the
defaults above are in English and are not among the phrases **Theme → Wording**
can replace.

Final, Screen-out and Redirect pages end the interview. Reaching one records
the response. They are usually gated with a **Show if** condition or reached
through a branch rule — see [[Logic and Branching|Studio-Logic-and-Branching]].

**Text-only pages.** Templates and imported questionnaires can also contain
*text-only* pages — an introduction, an information sheet, a debrief. The
Inspector shows them as **Content** too. The respondent sees their title and
Body (with **Previous** and **Next**) and nothing else.

> **Current limitation.** The **Body** of an ordinary question page is not
> shown to respondents, even though the canvas displays it. To give
> respondents introductory text:
>
> - use the page **Title** for a short heading, or a question's **Hint** for a
>   sentence under the question; or
> - use a **text-only page** before the questions. Keep the one a template
>   gave you, or add one in the **Source** tab as a page object like
>   `{"name": "intro", "kind": "content", "title": "Welcome", "body": "<p>Thank you for taking part…</p>"}`
>   placed in the `pages` list where you want it, then **Apply**.
>
> Do not add questions to a text-only page: the respondent sees only its Body.
> Check the result in **Preview**.

**Body text is HTML**, not Markdown: `<p>…</p>`, `<b>…</b>`, `<a href="…">…</a>`
and similar tags work; plain text works too, but line breaks collapse. In a
text-only page's Body and in page titles, piping (`{answer:variable}`,
`{label:variable}`) fills in an earlier answer. The Body of a Final,
Screen-out or Redirect page is shown as written — piping is not filled in
there.

### Page properties

Select a page (click it in the rail, or its title in the pager) to edit it:

- header: **Page 3** and the page's name, and a delete button (**Delete
  page**; disabled when it is the only page);
- **Page** section:
  - **Title** — shown as the page heading;
  - **Name** ("used by logic (skip to, next if)") — letters, digits and `_`;
    other characters turn into `_`, and the name cannot be emptied. Renaming a
    page updates every branch rule, **Default next** and **Skip to** that
    points at it. Names must be unique;
  - **Kind** — **Content**, **Final (thank you)**, **Screen-out**,
    **Redirect**;
  - **Body** (all kinds except Redirect);
  - **Redirect URL** and **Delay (s)** — whole seconds, 0 or more (Redirect
    pages);
  - **Randomize block order** (Content pages) — shuffles the page's blocks per
    respondent;
- **Logic** section — **Show if**, **Hide if**, **Branch (next if)** ("first
  matching rule wins"; **+ Rule** adds one, each rule is a condition → target
  page) and **Default next** ("when no rule matches"; **— following page —**
  by default). See [[Logic and Branching|Studio-Logic-and-Branching]];
- **Comments** — a discussion thread on this page for your team
  ([[Working Together|Studio-Collaboration]]).

---

## Blocks

A **block** groups questions inside a page so the group can be shown, hidden
or shuffled as a unit. Add one from **+ Question → Block** (it is called "New
block").

Block properties:

- header: **Block**, the number of items, and **Delete block and its
  questions**;
- **Block** section — **Title** and **Randomize question order**;
- **Logic** section — **Show if**, **Hide if**.

---

## Adding, moving and deleting

- **Add** with **+ Page**, **+ Question**, **Add to block** or **Add your first
  question** (see above).
- **Drag** a question card or a block:
  - onto another card — it drops before or after it, depending on which half
    you release over;
  - into a block's body — it goes to the end of that block;
  - onto a page in the rail — it goes to the end of that page;
  - onto **Drop here to move to the end of the page**, which appears while you
    drag.
  A block cannot be dropped into itself.
- **Drag a page** in the rail to reorder the interview, or use **↑ ↓** in the
  canvas bar.
- The **Move up** / **Move down** buttons on a card are the keyboard
  alternative (within the same page or block).
- **Delete** with the trash button in the Inspector header — **Delete
  question**, **Delete block and its questions**, **Delete page**.

> **Note.** Deletes happen immediately, with no confirmation. If you delete
> the wrong thing, press **↶** (`Ctrl/Cmd + Z`).

---

## The Inspector

The right-hand panel shows the selected question, block or page in collapsible
sections. Studio remembers which sections you keep open, per browser. With
nothing selected it says "Select a page or a question to edit it."

### Question

- **Header** — the **type** dropdown (changing it converts the question — see
  [Converting a type](Studio-Question-Types#converting-a-type)),
  `id → variables`, and **Delete question**.
- **Question** — **Question text**, **Hint** ("optional guidance shown below
  the question"), **Required**, **Randomize option order** (Single choice,
  Multiple choice, Ranking), **Attention check** (Single choice, Likert scale,
  Number, Open text) and, when the assistant is on for your organization,
  **Reword** and **Suggest options** ([[AI Assistant|Studio-AI-Assistant]]).
- **Options** (choice questions) or **Answer** (all others) — the
  type-specific settings; see [[Question Types|Studio-Question-Types]].
- **Variable** (marked *codebook*) — the codebook entry this question writes:
  name, scale, variable label, value labels, valid range; see
  [[Codebook and Variables|Studio-Codebook-and-Variables]].
- **Logic** — **Show if**, **Hide if** and **Skip to** ("after answering";
  **— next page —** or a page name). Opens by itself when the question has
  logic.
- **Advanced** (closed by default) —
  - **Id** ("stable reference; used in logic") — letters, digits and `_`;
    other characters turn into `_`;
  - a reminder that `{answer:variable}` and `{label:variable}` insert a
    previous answer into the question text or hint;
  - **Tags** ("comma-separated") — free labels for your own organization;
  - **Media URL** ("image / video shown with the question") — a link ending in
    `.mp4` or `.webm` is shown as a video, anything else as an image.
- **Comments** (closed by default) — the question's comment thread.

> **Tip.** For **Media URL**, use a stable public address (your website, a
> public bucket, an image host). A download link copied from **Files** is
> signed and **expires after 5 minutes**, so respondents would see a broken
> image.

### Block and page

See [Blocks](#blocks) and [Page properties](#page-properties).

### Resizing

Drag the divider between the canvas and the Inspector to make the Inspector
wider or narrower (300 to 760 pixels, and at most 55 % of the window). With the
divider focused, `←` and `→` move it by 16 pixels; `Home` or a double-click
resets it to 340 pixels. The width is remembered in this browser.

---

## Conditions in brief

**Show if**, **Hide if**, branch rules and option conditions all use the same
editor. Closed, it shows the condition as a sentence with **Edit** and
**Clear** (or **Add condition**). Open, it is a list of rows —
*variable · operator · value* — combined with **ALL of the following** or
**ANY of the following**, plus **+ Condition** and **Done**:

| Operator | Meaning |
|---|---|
| `=`, `≠`, `>`, `≥`, `<`, `≤` | compare the answer with a value |
| **in**, **not in** | the answer is (not) one of several codes — pick them under **choose codes** |
| **chose**, **did not choose** | for multiple choice: the answers include (do not include) a code |

For a variable with value labels, the value is picked from a list
("Satisfied (4)"). A condition the rows cannot represent (nested groups, text
from an import) opens as JSON instead. Everything else — piping, skip logic,
the Logic map, the checks — is in
[[Logic and Branching|Studio-Logic-and-Branching]].

---

## Structure and Preview

**Structure | Preview** in the canvas bar switches the middle column:

- **Structure** — the editable cards described above.
- **Preview** — the engine's actual survey runtime, rendering your *working*
  document (unsaved edits included) the way a respondent sees it. It rebuilds
  about half a second after each edit.
  - **Desktop | Mobile** switches the frame width.
  - The status line reads "Respondent view · page *name* · click a question to
    edit it": clicking a question selects it in the Inspector, and selecting a
    page or question in the rail moves the preview there.
  - **Restart** ("Restart the preview from page 1") starts the interview over.
  - Answers are **never stored**; submitting shows the toast "Preview
    submitted — answers are not stored".
  - If the document cannot be built you see "Could not build the preview" with
    the reason, and "Fix the document to render the preview."

### The Preview button

**Preview** in the header goes further: it builds a **preview deployment** —
the full published survey at its own address — from the **current Save** and
opens it in a new tab when it is ready.

- It needs a Save of what you see: with unsaved edits you get "Save first — a
  preview is built from a Save".
- Toasts: **Building preview of #17…**, then **Preview ready — not accepting
  responses**.
- A Save marked `errors` cannot be previewed.
- The preview deployment also appears on **Distribute**; it never collects
  responses. See [Preview deployments](Studio-Publishing-and-Environments#preview-deployments).

For a link colleagues can open without an account, use **Test → Share
preview** ([[Testing Your Survey|Studio-Testing-Your-Survey]]).

---

## Saving

Press **Save changes** (or `Ctrl/Cmd + S`, which works even while you are
typing in a field). The **Save** dialog explains what will happen — "A new
version of questionnaire.json and a Save you can deploy, preview or restore
later." — and asks for a **Message** (optional, placeholder
`Add charging-access question`, up to 240 characters). `Enter` or **Save**
saves.

- With nothing changed the dialog says "No document changed — this Save
  re-pins the current versions and re-validates them with the current engine."
  That is useful after an engine update.
- With the message left empty, Studio writes one: `Update questionnaire`.
- The engine validates the questionnaire and generates `questionnaire.py`.
  The toast says **Saved #18**, **Saved #18 (warnings)** or **Saved #18 with
  errors — see History**.
- A **malformed** document is refused outright and nothing is saved: "Save
  failed." followed by the engine's reason. The usual causes are listed in
  [What the engine refuses](Studio-Question-Types#what-the-engine-refuses).
- A document the engine can read but that breaks a rule (a duplicate question
  id, a skip to a page that does not exist, a page nobody can reach, …) **is**
  saved, marked `errors`, and cannot be published until you fix it and Save
  again.

### When a colleague saved first

If someone saved while you were editing, the dialog says who:

> *Ada Lovelace* saved #18 ("Add region quota") while you were editing on top
> of #17. Reload their Save to see it (your edits stay as an unsaved draft), or
> save yours on top of it as #19.

**Reload #18** loads their Save and keeps your edits on top as an unsaved
draft; **Save on top** saves yours as #19 anyway; **Cancel** closes the dialog.

---

## Drafts and autosave

Between Saves your edits are autosaved to the server as a private **draft**
1.5 seconds after your last change. The routine messages sit quietly in the
version-chip popover:

| Message | Meaning |
|---|---|
| "Draft waiting to sync…" | an edit will be saved as a draft in a moment |
| "Syncing draft…" | the draft is being written |
| "Draft synced — not yet saved as a version." | your edits are safe; they are not a Save yet |

Messages that need your attention appear in a band under the header:

| Message | What to do |
|---|---|
| "Draft sync failed. Your edits remain in this tab. Retry before closing it." | press **Retry draft sync**; do not close the tab until it succeeds |
| "A newer version exists. Review the conflict when saving." | someone saved since your draft started; the Save dialog will show who |
| "Restored draft. Draft restored — save a version when ready." | Studio brought back unsaved edits from an earlier visit |
| "An unsaved draft from an older version was not restored — the document has been saved since." | your old draft was older than the current Save, so it was not applied |
| "Could not check for a saved draft. Your current edits are kept in this tab." | a network problem; your edits in this tab are fine |
| "Could not clear the previous draft. Reopen the editor to review it before publishing." | reopen the Builder before you publish |

Switching to another project tab and back simply picks your edits up again.
When you open the Builder after a reload, in a new tab or on another computer
and Studio finds unsaved edits you made earlier, a toast says **Unsaved edits
restored — Save to keep them as a version**. To throw them away, use **More ▾
→ Discard changes**. If you try to close or reload the
tab with unsaved edits, the browser asks whether you really want to leave.

---

## Undo and redo

- **↶** / **↷**, `Ctrl/Cmd + Z` and `Shift + Ctrl/Cmd + Z` (or `Ctrl/Cmd + Y`)
  undo and redo up to **100** steps.
- While your cursor is in a text field, these keys undo your typing in that
  field instead.
- Undo covers everything that changes the document, including imports,
  deletes and **Apply** in the Source tab.
- The history is **cleared** when you Save, when you **Discard changes**, and
  when you leave the Builder or switch project. (Your draft survives; the undo
  steps do not.)

---

## The Source tab

**More ▾ → Source** shows the questionnaire document as JSON — the same
`survey/questionnaire.json` that is versioned and published.

| Control | What it does |
|---|---|
| **Copy** | copies the JSON to the clipboard |
| **.json** | downloads it as `questionnaire.json` (importable into any project) |
| **Revert** | throws away your edits in this tab |
| **Check** | runs the engine's check on the text without saving; shows **Check result** with the issues, or "No issues — the document validates." |
| **Apply** | replaces the working document with the text (an ordinary, undoable edit) |

While you have typed in Source without applying, a band says "You have
unapplied source edits. Apply or revert them in Source before saving.", with
**Open Source** when you are on another tab, and **Save** is disabled ("Apply
or revert source edits before saving"). If the text is not valid JSON you see
"This is not valid JSON" with the parser's message, or "The document must be a
JSON object."

Source is the escape hatch for anything the Builder does not offer yet, such as
text-only pages or missing-value codes (see
[[Codebook and Variables|Studio-Codebook-and-Variables]]).

---

## Export Python

**More ▾ → Export Python** ("Download the generated questionnaire.py for the
current Save") downloads the `questionnaire.py` the engine generated when the
current Save was made — the exact file that was validated and is published,
not a fresh re-generation. The toast says **Downloaded questionnaire.py**. It
is disabled until the project has a Save. The file's header explains how to
run it with `pip install siamang` and `siamang validate questionnaire.py`. See
[[Reproducibility: Code, Bundles and Citation|Studio-Reproducibility]].

---

## Read-only states

**A colleague holds the edit lock.** Only one person edits the questionnaire at
a time. When someone else is editing, a banner says:

> **Ada Lovelace** is editing — you are following their changes live (last
> edit 2 minutes ago). Your own edits are off until you take over; comments
> stay open.

You see their unsaved edits as they make them; **Save** is disabled ("Ada
Lovelace is editing"). **Take over** moves the lock to you; they get the
message "… took over editing — you are now following their changes", and their
unsaved work stays as their private draft. See
[[Working Together|Studio-Collaboration]].

**The workspace is frozen.** Support can freeze an organization; a banner then
says "This workspace is frozen and read-only." Everything stays viewable and
exportable, but every change — including a Save — is refused. A trial that
ends does **not** freeze the workspace: it continues on the Free plan. See
[[Plans, Trial and Billing|Studio-Plans-and-Billing]].

Older Saves are not opened in the Builder: they open read-only in **History**,
where you can restore one as a new Save
([[History and Versions|Studio-History-and-Versions]]).

---

## On a phone

On a phone-width screen a bar with **Preview** and **Save** stays at the bottom
of the screen, so you never have to scroll back to the header to save.

## See also

- [[Question Types|Studio-Question-Types]]
- [[Codebook and Variables|Studio-Codebook-and-Variables]]
- [[Logic and Branching|Studio-Logic-and-Branching]]
- [[Testing Your Survey|Studio-Testing-Your-Survey]]
- [[Projects|Studio-Projects]]

<!-- studio-nav -->
---

← [[Plans, Trial and Billing|Studio-Plans-and-Billing]] · [Studio contents](Studio-Overview#all-pages) · [[Question Types|Studio-Question-Types]] →
