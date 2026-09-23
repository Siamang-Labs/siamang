# Question Bank, Templates and Library

Studio has three kinds of reusable material: the built-in **question bank**
(standard blocks with a ready codebook), the built-in **templates** (complete
questionnaires to start a project from), and your **organization's library**
(questions, blocks and questionnaires your team saved) *(Plus)*. This page
covers the **Library** screen, inserting blocks in the Builder, saving your own
material, and how names are resolved when a block lands in a questionnaire
that already uses them.

---

## Which one to use

| You want to… | Use | Plan |
|---|---|---|
| add standard demographics, NPS, CSAT, CES, an agreement scale, the BFI-10 or trust items to a questionnaire | the **question bank** — Builder → **Library → Insert from library…** | all plans |
| start a new study from a complete, publishable questionnaire | a **template** — **New project → Template** | all plans |
| reuse your own screener, block or question across projects | the **organization library** — save with **Library → Save … to library…**, insert with **Insert from library… → Organization** | *(Plus)* to save |
| start new projects from your own house questionnaire | **Library → Save questionnaire as template…**, then **New project** | *(Plus)* to save |

---

## The Library screen

The organization's **Library** tab (`studio.siamang.org/<org>/library`) shows
all three, with a search box (**Find in the library…**) that filters every
section at once. The header reads *Library — <organization> · question bank,
templates and your own blocks*.

### Organization library

"blocks and questionnaires saved from the Builder"

| Column | What it shows |
|---|---|
| **Name** | the item's name, with its description underneath |
| **Kind** | **Block**, **Questionnaire** or **Flow** |
| **Size** | `3 questions · 4 variables` for a block; `7 pages · 11 questions · 15 variables` for a questionnaire |
| **Saved** | the date it was saved |
| (actions) | **New project** (questionnaires only) and **Delete** |

**Delete** asks "Delete “Screener”?" — "The block is removed from the
organization's library. Projects that already used it keep their copy." —
**Delete**. Any member of the organization can delete a library item.

With nothing saved yet: **Nothing saved yet** — "In the Builder, select a
question or a block and choose Library → Save to library; a questionnaire can
be saved as a template the same way." — and **Open the Builder**. With a search
that matches nothing: **Nothing matches** and **Clear the search**.

> **Plan.** On the Free plan this section shows a card instead: **Your own
> library is a Plus feature** — "Save blocks and questionnaires from the
> Builder and reuse them across the organization's projects. The question bank
> and templates below are free." — with **View plans**.

### Templates

"start a project from a complete questionnaire" — one card per built-in
template with its description, its size (`8 pages · 12 questions · 18
variables`) and **New project**, which opens the New project dialog with the
template already chosen. Only owners and admins can create the project — a
member who tries gets "Could not create project. Only owners and admins can
create projects." (see [Creating a project](Studio-Projects#creating-a-project)).
The twelve templates and what they contain are listed in
[Built-in templates](Studio-Projects#built-in-templates).

### Question bank

"standard blocks with ready codebook entries — insert them in the Builder
(Structure → Library)" — one card per block with its category, description,
size and source. Blocks are inserted from the Builder, not from this screen.

If the library cannot be loaded, the screen says so and offers a retry.

---

## The question bank

Seven standard blocks. Each brings its questions **and** their codebook
entries (labels, scales, value labels, declared missing codes). Question
wording follows the public instruments loosely enough to be free of license
terms; the source is named so a Methods section can cite it.

| Block (category) | Contents | Source |
|---|---|---|
| **Core demographics** (Demographics) — "Gender, age group, education and employment — the four cuts every crosstab needs, coded like the European Social Survey harmonized variables." | a block *About you*: `gender` (Woman, Man, Non-binary or another identity, `99` Prefer not to say — declared as a refusal missing code), `age_group` (18–24 … 65 or older, required), `education` (5 levels, dropdown), `employment` (7 situations) | ESS / GSS harmonized background variables |
| **Net Promoter Score** (Satisfaction) — "The 0–10 likelihood-to-recommend question with the open follow-up; score = % promoters (9–10) minus % detractors (0–6)." | `nps`: single choice `0`–`10` as buttons, required (interval scale); `nps_reason`: multi-line open text | Reichheld (2003) |
| **Overall satisfaction (CSAT)** (Satisfaction) — "A five-point satisfaction rating with a follow-up on what to improve." | `satisfaction`: Very dissatisfied … Very satisfied, buttons, required; `improve`: multi-line open text | Standard CSAT item |
| **Customer effort (CES)** (Satisfaction) — "The seven-point ease-of-handling item with an open follow-up on what got in the way — the third of the standard experience metrics beside CSAT." | `ces`: "The company made it easy for me to handle my issue.", Strongly disagree … Strongly agree (7 points), buttons, required; `ces_reason`: multi-line open text | Dixon, Freeman & Toman (2010), Customer Effort Score |
| **Agreement scale (Likert, 5 points)** (Scales) — "A three-statement agreement matrix to adapt: replace the statements, keep the scale." | matrix `agreement` with rows `agree_1`–`agree_3`, Strongly disagree … Strongly agree | Likert (1932) five-point format |
| **Big Five Inventory — 10 items (BFI-10)** (Psychometrics) — "Two items per trait on a five-point agreement scale; reversed items are named so a flow can recode them before scoring." | matrix `bfi10` ("I see myself as someone who…") with rows `bfi_reserved`, `bfi_trusting`, `bfi_lazy`, `bfi_relaxed`, `bfi_artistic`, `bfi_outgoing`, `bfi_faults`, `bfi_thorough`, `bfi_nervous`, `bfi_imagination`; labels name the trait and "(reversed)" | Rammstedt & John (2007) |
| **Trust in institutions (0–10)** (Attitudes) — "Three 0–10 trust items in the ESS format; add or drop institutions as needed." | matrix `trust` with rows `trust_parliament`, `trust_legal`, `trust_police`, columns `0`–`10` | European Social Survey core module |

> **Current limitation.** Matrix answers are stored as the column's
> **position**, 1 to *n*. In **Trust in institutions**, a respondent who
> chooses the column "0" is stored as `1` and "10" as `11`, while the inserted
> codebook labels the codes `0`–`10`. Subtract 1 in your flow (for example with
> a **Recode** or **Derive** node) before you report the 0–10 scores. The
> other bank matrices use codes 1–5 and are not affected.

The NPS, CSAT and CES blocks are **Single choice** questions, not Likert
scales, so their codes are exactly the numbers shown.

---

## Inserting a block

1. In the Builder's **Structure** view, go to the page where the block should
   go. To put it inside an existing block, select that block.
2. Open **Library → Insert from library…**.
3. Choose **Question bank** or **Organization · N** (the number of blocks your
   organization saved), and optionally type in **Find a block…**.
4. Click **Insert** on a row. Each row shows the name, the category (or
   *organization*), the description and `N questions · N variables · <source>`.

The block goes **at the end of the current page** (or of the selected block).
The toast says **Inserted “Core demographics”**, and the first inserted item is
selected. The insert is an ordinary edit: **↶** undoes it, and nothing is saved
until you Save.

Messages in the dialog: **Loading…** while the bank loads; "No block
matches." for a search with no result; "Nothing saved yet — select a block or a
question in the Builder and choose Library → Save selection." when the
organization has saved no blocks; "Could not load the question bank" if it
failed to load.

### When names are already taken

Inserted questions and variables never overwrite what is already in the
questionnaire:

- a question whose **Id and variable name are the same** — every
  single-answer question in the question bank — is renamed as one: both get
  the first name that is free as an Id *and* as a variable, adding `_2`,
  `_3`, … (`nps` → Id `nps_2`, variable `nps_2`);
- any other **variable** whose name exists gets `_2`, `_3`, … (a matrix row
  `trust_police` → `trust_police_2`);
- any other **question Id** that exists gets a number with no underscore
  (the matrix `trust` → `trust1`, `trust2`, …);
- conditions (**Show if**, **Hide if**) on the inserted questions and blocks
  that refer to the inserted block's own renamed variables are updated to
  the new names.

What is **not** adjusted:

- conditions that refer to variables *outside* the block keep the names they
  had — they work only if this questionnaire has variables of those names;
- conditions on individual options are not renamed;
- **Skip to** targets are page names; if the page does not exist here, the
  Save is marked `errors` until you change or clear it;
- the Id of an inserted matrix (or other multi-variable question) is checked
  only against other Ids; if it equals a variable name already in the
  questionnaire, the Save is marked `errors` — change the matrix's
  **Advanced → Id**.

> **Note.** A question saved to your organization's library with an Id that
> differs from its variable (a preset such as Id `q5`, variable `nps_5`)
> keeps that difference when it is inserted. That is fine: the answer is
> stored under the variable — see
> [Question Id and variable name](Studio-Builder-Overview#question-id-and-variable-name).

---

## Saving to your organization's library *(Plus)*

In the Builder, open the **Library** menu:

| Menu item | Saves | Becomes |
|---|---|---|
| **Save question to library…** / **Save block to library…** | the selected question, or the selected block with all its questions, and the codebook entries of every variable they write | a **Block** item, insertable from **Insert from library… → Organization** |
| **Save questionnaire as template…** | the whole questionnaire (pages, logic, codebook, quotas, theme, scripts) | a **Questionnaire** item, offered in **New project → Template** under **Your organization's library** |

Without a selection the first item reads **Save selection to library…** and is
disabled ("Select a question or a block first").

The dialog — **Save block to library** or **Save questionnaire to library** —
explains what will happen ("The selection and its codebook entries become a
block anyone in the organization can insert from the Builder." / "The whole
questionnaire becomes a template your organization can start new projects
from." followed by "It is checked by the engine on the way in."), shows the
block's size, and asks for:

| Field | Notes |
|---|---|
| **Name** | pre-filled with the block's title, the question's text or the questionnaire's title; up to 120 characters |
| **Description** *(optional)* | "When to use it, what it assumes" — up to 500 characters |

**Save to library** stores it (**Saving…**, then **Saved “Screener” to the
library**). The engine checks the item first: a block or questionnaire it
marks as broken is refused ("… does not pass the engine's check"), and so is an
item larger than about 2 MB.

On a plan without the library, the menu items still open a dialog — **Save to
library** — that explains "Your organization's library — reusable blocks,
questionnaires and flows — is available from the **Plus** plan. The built-in
question bank and templates stay free." with **Upgrade to Plus**.

Good to know:

- Library items are **copies**. Inserting a block or starting a project copies
  it; later changes to the library item (or deleting it) do not reach projects
  that already used it, and edits in a project do not change the library.
- There is no editing in place: to update an item, save a new version under a
  new name and delete the old one.
- Flows cannot be saved to the library from Studio's screens; the **Flow** kind
  appears only for items created through the [[API|Studio-API-and-API-Keys]].
- Starting a project from a saved questionnaire works on every plan, including
  after a downgrade; only saving requires Plus.

## See also

- [[Projects|Studio-Projects]]
- [[The Builder|Studio-Builder-Overview]]
- [[Question Types|Studio-Question-Types]]
- [[Plans, Trial and Billing|Studio-Plans-and-Billing]]

<!-- studio-nav -->
---

← [[Importing Questionnaires|Studio-Importing-Questionnaires]] · [Studio contents](Studio-Overview#all-pages) · [[Testing Your Survey|Studio-Testing-Your-Survey]] →
