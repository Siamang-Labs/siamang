# Importing Questionnaires

You do not have to rebuild an existing instrument by hand. The Builder's
**Import** reads a Studio questionnaire document, a siamang `questionnaire.py`,
a Qualtrics export (`.qsf`), a LimeSurvey structure export (`.lss`, or the
same export saved as `.xml`) or a SurveyJS survey (`.json`), shows you what it
found and what it could not carry
across, and replaces the working questionnaire with the result. Nothing is
saved until you Save. This page covers the dialog, every format and what each
one carries.

---

## Opening the Import dialog

In the Builder, open **More ▾ → Import** ("Replace the working document with a
questionnaire.json (from a bundle or another project)").

```
┌ Import questionnaire ─────────────────────────────────────────────── ✕ ┐
│ A questionnaire.py or questionnaire.json — from a bundle, another      │
│ project, Cloud or the engine — a Qualtrics export (.qsf) or a          │
│ LimeSurvey structure export (.lss, or the same export saved as .xml). …│
│ ┌────────────────────────────────────────────────────────────────────┐ │
│ │ Drop a .py, .json, .qsf, .lss or .xml file here, or click to choose│ │
│ └────────────────────────────────────────────────────────────────────┘ │
│ Not imported (3) — the questionnaire format has no place for these     │
│   QID12 · Constant sum — …                                             │
│ Document read from the file                               18,402 chars │
│ [{"schema_version": "1.0", "title": "…", "pages": [ … ]}            ]  │
│  7 pages   24 items   31 variables   Customer Pulse                    │
│  ● engine check: warnings · 2 issues                                   │
│              [Cancel] [Check with the engine] [Import]                 │
└────────────────────────────────────────────────────────────────────────┘
```

1. **Drop a file** on the drop zone, or click it to choose one ("Drop a .py,
   .json, .qsf, .lss or .xml file here, or click to choose"; the file picker
   offers these five types). While a file is being read it says **Reading…**,
   then "Loaded **file** — drop another file to replace".
2. Read what was **not imported** (if anything) and the **warnings** under the
   drop zone.
3. Look at the summary: **pages**, **items** (top-level items per page — a
   block counts once), **variables** and the **title**. If the document has
   structural problems you see "N structural issues (duplicate ids, missing
   targets…) — you can fix them in the Builder after importing."
4. Click **Check with the engine** (it reads **Checking…**) for the engine's
   verdict: "● engine check: valid", "warnings" or "error", with the number of
   issues and the first five errors. Files read on the server (`.py`, `.qsf`,
   `.lss`, `.xml`, SurveyJS) are checked automatically.
5. Click **Import** — or **Import anyway** when the check found errors — or
   **Cancel**.

Instead of a file you can paste a questionnaire document into the text box
("Or paste the document"; placeholder
`{"schema_version": "1.0", "title": "…", "pages": [ … ]}`). The box shows the
number of characters. For every file read on the server — `.py`, `.qsf`,
`.lss`, `.xml` and SurveyJS — the box is labeled "Document read from the
file" and holds the document that was read, which you can edit before
importing.

---

## What happens when you import

- The imported questionnaire **replaces the whole working questionnaire** —
  title, pages, questions, codebook, quotas, theme and scripts. The project's
  flows, settings, data and history are untouched.
- The Builder switches to **Structure**, on page 1.
- Pages are stored the way the Builder keeps them: a page with a Body and no
  questions as a text-only page, a page with questions as an ordinary page
  that shows its Body above the questions — also when the source file marked
  it as a text (*content*) page. See
  [Pages and page kinds](Studio-Builder-Overview#pages-and-page-kinds).
- The import is an ordinary edit: **↶** (`Ctrl/Cmd + Z`) takes you back to what
  you had, and nothing is saved until you **Save**. The project keeps its own
  history; the import becomes a new Save like any other.

---

## Formats

### Questionnaire document (`.json`)

The format Studio stores (`survey/questionnaire.json`): from a research bundle,
another project's **Source → .json**, or the siamang engine. A file that holds
the document under a `questionnaire` key is accepted too. It is read in your
browser.

- It must be an object with a `pages` list, otherwise: "Not a questionnaire
  document: expected an object with a "pages" array (survey/questionnaire.json)."
- `schema_version` must be `1.0`: "Unsupported schema_version 2.0 — Studio reads
  questionnaire-1.0."
- A document without a title gets "Imported survey".

### Python (`questionnaire.py`)

A siamang questionnaire written in Python — for example a `questionnaire.py`
from **Export Python**, a research bundle or a siamang Cloud project. The file
is **read, never run**: Studio walks its syntax and rebuilds the questionnaire
from the declarative subset of siamang code — the subset **Export Python**
writes, and the one hand-written questionnaires almost always stay in:

- imports of `siamang` (`import siamang as sg`, `from siamang import …`,
  `from siamang.core import …`, `from siamang.frontend import UIConfig`) and
  `from datetime import datetime`;
- module-level assignments (`name = …`) of literals, f-strings of constants and
  names defined earlier;
- calls of the engine's constructors and factories (`Page`, `SingleChoice`,
  `Variable`, `Quota`, `Script.timed_question`, `UIConfig`, …);
- conditions written with a variable's methods (`age.lt(18)`,
  `region.isin([1, 2])`, `barriers.contains(1)`), `AND` / `OR` / `NOT` /
  `compare` and the `&`, `|`, `~` operators;
- `codebook.add_many([...])` and `datetime.fromisoformat("…")`.

Everything else — loops, comprehensions, functions, `if`, other calls, other
imports — is **not run**. Each such construct is listed under **Not imported
(N) — the file was not executed**, with its line number, what it was and why,
and reading carries on. Only siamang's own building blocks are ever called, so
a hostile file can at worst produce a strange questionnaire.

### Qualtrics (`.qsf`)

The file Qualtrics writes for *Export survey* (also accepted when it was saved
with a `.json` extension).

| Carried across | Reported as not imported |
|---|---|
| multiple choice (single and multiple answer, dropdown, NPS) → Single or Multiple choice | constant sum, side-by-side, drill-down, pick-group-rank |
| text entry → Open text, or Number when it has a number validation; a form → one Open text per field | file upload, signature, timing, meta info, captcha |
| Likert matrix (single answer) → Matrix, one variable per row | heat maps, hot spots, highlight, drawing, gap analysis |
| slider → one Number (slider) per statement | matrix with multiple answers, bipolar or text entry |
| rank order → Ranking | display logic on embedded data, quotas or panel data |
| descriptive text → the page's text | embedded data, quotas, web services and authenticators in the flow |
| recodes, choice order, "other" text entries (the text-entry choice becomes the question's Other option, keeping its recode), exclusive answers (also on a multiple answer stored as one variable per choice), forced response | loop & merge; skip logic |
| question and choice randomization | validations other than "force response" and numeric ranges |
| display logic on questions (selected / not selected / comparisons) | block randomizers (pages keep their order) |
| page breaks, block order from the survey flow, branches (as page conditions) | choice display logic |
| end of survey inside a branch (as a screen-out page), back button, progress bar | |

### LimeSurvey (`.lss`)

The XML LimeSurvey writes for *Export survey structure* — as `.lss`, or the
same export saved with an `.xml` extension, which Studio recognizes by its
content and reads the same way.

| Carried across | Reported as not imported |
|---|---|
| list, dropdown, list with comment → Single choice; multiple choice (with or without comments) → Multiple choice | array dual scale, array numbers, array texts |
| yes/no, gender, 5-point choice → Single choice with fixed codes | equations, file upload, language switch |
| numerical input → Number (slider settings → slider, min/max → valid range); multiple numerical → one Number per subquestion | question randomization groups and group randomization (the order is kept) |
| short, long and huge free text → Open text (long texts multi-line, maximum characters); multiple short text → one Open text per subquestion | quotas and assessments |
| arrays (5-point, 10-point, yes/no/uncertain, increase/same/decrease, flexible, by column) → Matrix, one variable per subquestion | conditions testing anything other than an answer with `=`, `!=`, `<`, `<=`, `>`, `>=` (is empty, regular expressions, arithmetic, functions) |
| ranking → Ranking; text display → the page's text; date → Open text (with a warning) | validation regular expressions |
| mandatory, "other" answers, answer and subquestion order, choice randomization | comment fields of lists and multiple choice with comments |
| survey format (group by group, question by question, all in one), group order, welcome and end texts, back button, progress bar, language | default answers |
| question relevance (comparisons joined with and/or on single, multiple, matrix, numeric and text answers), group relevance, legacy conditions | |

### SurveyJS (`.json`)

A SurveyJS survey definition (Survey Creator / Survey Library): a `.json` file
whose pages contain `elements` is recognized automatically.

| Carried across | Reported as not imported |
|---|---|
| radio group, dropdown, image picker → Single choice | file, signature pad |
| checkbox, tag box → Multiple choice (wide when conditions test its items) | dynamic panels, dynamic matrices |
| boolean → Yes/No single choice; rating → Single choice on the rate values (buttons) | matrix dropdowns with several columns or non-choice cells |
| text → Open text or Number (number/range input, min/max, max length); comment → multi-line Open text; multiple text → one Open text per item | expression questions, calculated values, triggers |
| matrix → Matrix; matrix dropdown with one column of choices → Matrix | validators other than numeric ranges and text length |
| ranking → Ranking | conditions with functions, arithmetic, empty/not empty, all of, or references to variables and calculated values |
| html, expression and image elements → the page's text | enable-if / required-if |
| panels (flattened; a randomized panel becomes a block) | choices loaded from a URL |
| required, "other" and "none" items, choice order, question order (page shuffle) | correct answers (quiz mode) |
| visible-if on questions, panels and pages (=, <>, <, <=, >, >=, contains / not contains on checkboxes, any of, and / or / not, parentheses) | |
| locale, previous button, progress bar, completion HTML, navigate-to URL | |

---

## Limits and errors

| Limit | Value |
|---|---|
| File size | 2 MB |
| Encoding | UTF-8 text |
| File types | `.json`, `.py`, `.qsf`, `.lss`, `.xml` (a LimeSurvey export) |

Messages you may see (for a file read on the server — `.py`, `.qsf`, `.lss`,
`.xml`, SurveyJS — they follow "Could not read the file."):

| Message | Meaning |
|---|---|
| "File larger than 2 MB." | the file is too big to import |
| "The file is not UTF-8 text." | re-save the file as UTF-8 |
| "Unsupported file type: upload a questionnaire .py, .json, .qsf or .lss." | an `.xml` file that is not a LimeSurvey structure export |
| "Not valid JSON: line N: …" / "This is not valid JSON" | the file or pasted text is not valid JSON — a file with any extension other than the five above is treated as pasted text |
| "Not a questionnaire document: expected an object with a "pages" array …" | a JSON file that is none of the recognized formats |

> **Note.** The paste box reads **questionnaire documents only**. Pasting a
> Qualtrics or SurveyJS export into it does not convert it — save it as a file
> and drop the file instead.

---

## After importing: a checklist

1. **Read the not-imported list** and rebuild what matters (a skipped quota, a
   validation, logic on embedded data) in the Builder.
2. **Check the variable names.** Each question's answer is stored under its
   variable name, which becomes the column in your data; the card header
   shows `id → variable`. An Id that differs from its variable is fine, but a
   question's Id must not be another question's variable name — if the engine
   check reports that a question "has the id under which question … stores
   its answer", change that question's **Advanced → Id**. See
   [Question Id and variable name](Studio-Builder-Overview#question-id-and-variable-name).
3. **Look for introductory text.** A page that held only text becomes a
   text-only page and is shown as before. Text that shared a page with
   questions lands in that page's **Body**, which respondents see above the
   questions. Check in **Preview** that it reads well there (see
   [Pages and page kinds](Studio-Builder-Overview#pages-and-page-kinds)).
4. **Review wide multiple-choice questions.** When the source survey's logic
   tests individual choices, the importer stores the question as one yes/no
   variable per choice and warns "stored as one yes/no variable per choice
   (…) because logic tests its choices." Each of those variables is `1` when
   its option is chosen and `0` when it is not, so the imported conditions on
   them work, and a Qualtrics exclusive answer keeps working too (a LimeSurvey
   exclusive option, or a SurveyJS "none" item, in such a question is still
   listed as not imported: "Exclusive answer — not available when choices are
   separate variables").
   See [Multiple choice](Studio-Question-Types#multiple-choice).
5. **Check matrix codes.** A matrix stores the code of the chosen column, as
   its value labels give it, so an imported matrix keeps its Qualtrics
   recodes or its 0–10 scale. Check that each row's value labels are the
   codes you expect in the Codebook tab — see
   [Matrix](Studio-Question-Types#matrix).
6. **Review "Other" and "None" options.** An imported Other stores a code
   (`-66` unless the source gave one: a Qualtrics text-entry choice keeps its
   own code and becomes the Other option) and puts the typed text in
   `<variable>_other`. If the imported codebook has no labels for these codes,
   **Validation** warns `ADDED_CODE_WITHOUT_LABEL`; an N/A with no declared
   code gives `NA_STORED_AS_TEXT`. Edit the question once in the Builder — for
   example switch the option off and on — and Studio adds the labels, the
   `<variable>_other` entry and the N/A code. See
   [Codes for Other, None of the above and N/A](Studio-Question-Types#codes-for-other-none-of-the-above-and-na).
7. **Open Validation** and fix what the engine reports.
8. **Preview** the survey, then **Save** with a message such as "Imported from
   Qualtrics".

## See also

- [[The Builder|Studio-Builder-Overview]]
- [[Question Types|Studio-Question-Types]]
- [[Testing Your Survey|Studio-Testing-Your-Survey]]
- [[Question Bank, Templates and Library|Studio-Question-Bank-and-Library]]

<!-- studio-nav -->
---

← [[Scripts|Studio-Scripts]] · [Studio contents](Studio-Overview#all-pages) · [[Question Bank, Templates and Library|Studio-Question-Bank-and-Library]] →
