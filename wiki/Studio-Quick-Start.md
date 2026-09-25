# Quick Start

This page takes you from "no account" to a published survey, your own test
response in the database, a first table, and the code that reproduces it.
Allow about twenty minutes. Every step links to the page that covers it in
depth.

```
 1 Sign up ─▶ 2 New project ─▶ 3 Add a question ─▶ 4 Preview ─▶ 5 Save
      ─▶ 6 Publish to pilot ─▶ 7 Answer it ─▶ 8 Look at Data ─▶ 9 First flow ─▶ 10 Take the code
```

---

## 1. Create your account

Go to **`studio.siamang.org`**. The **Sign in** card offers:

- **Continue with Google** or **Continue with Microsoft** — one click; the
  account is created on first sign-in.
- **Continue with Email →** — type your address and press **Continue**. If the
  address is new, Studio shows **Create your account**: your name and a
  password (at least 8 characters with a lower-case and an upper-case letter,
  a number and a symbol — the checklist under the field turns green as you
  go). Press **Create account**, then click the link in the confirmation email.

On sign-up you get your **own organization**, named after you, with you as its
owner, on a **30-day Pro trial**. The topbar shows `Pro trial · 30d`.

→ [[Sign Up and Sign In|Studio-Sign-Up-and-Sign-In]]

## 2. Create a project

You land on the organization's **Projects** tab. Press **New project**
(or, on an empty list, **Start from the example study** to explore a finished
study first).

1. **Name** — e.g. `Customer Pulse 2026`. The dim line under it, "Its
   address will be `/customer-pulse-2026`", shows the project's address; it
   cannot be changed later. A name in another script is spelled in Latin
   letters (`Опрос удовлетворённости` → `/opros-udovletvorennosti`), and an
   address the organization already has gets `-2`, `-3`, … added.
2. **Start from** — **Blank project** ("Start with one placeholder question")
   or **Template**. For this tour choose **Blank project**.
3. Press **Create →**.

The project opens in the **Builder**. Its first Save, `#1`, already exists
and is `valid`.

→ [[Projects|Studio-Projects]]

## 3. Add a question

In the Builder's **Structure** tab, the blank project's first page, `page1`,
already holds one placeholder question: a **Single choice** reading "New
question", with the choices **Option 1** and **Option 2**, stored in the
variable `q1`. Make it your first question:

1. Click the question card. The **Inspector** on the right shows it. In
   **Question**, replace "New question" with your wording, e.g. *How did you
   hear about us?*
2. In **Options**, edit the **Choices** — each has a **Code** (what is stored)
   and a **Label** (what is shown). **+ Option** adds one; pressing `Enter` in
   a label adds the next row.
3. Open **Variable** and give the variable a real **Variable label (as in
   SPSS)** — e.g. *Source of awareness*. This is your codebook entry.
4. Add a second question: at the bottom of the pages rail on the left, press
   **+ Question**. The menu has two columns — **Types** and **Presets**.
   Choose **Open text** and write *Anything else you would like to tell us?*

> **Note.** A question has two names, shown as `id → variable` in its card
> and Inspector header. The answer is stored under the **variable name**: it
> is the column in **Data** and in exports, and the name conditions, piping
> and quotas read. The **Id** (Inspector → **Advanced**) is the question's
> handle in the Builder — scripts target it, and the Logic map and validation
> messages show it. Plain types start with the two equal (`q1` / `q1`);
> presets such as **NPS (0–10)** do not (`q3` / `nps_3`), and that is fine.
> The main rule: an Id must not be **another** question's variable name, or
> the Save is marked `errors`. Studio never gives a new question such an Id
> (nor one of the few other names an Id may not take), and if you type one,
> the **Id** field says so at once ("This is the variable … stores its answer
> under — the engine refuses an id that is another question’s variable.").
> See
> [Question Id and variable name](Studio-Builder-Overview#question-id-and-variable-name).

→ [[Question Types|Studio-Question-Types]] ·
[[Codebook and Variables|Studio-Codebook-and-Variables]]

## 4. See it as a respondent will

Above the canvas, switch **Structure | Preview**. The preview is the real
survey runtime rendering your current (unsaved) document; switch between
**Desktop** and **Mobile**, and click a question to jump back to it. Answers
given here are not stored.

## 5. Save

Press **Save changes** (or `Ctrl/Cmd + S`). The **Save** dialog takes an
optional message — *First two questions* — then **Save**.

A Save is a numbered version of the whole project. The engine validates it and
generates `questionnaire.py`, stored with that version. The topbar badge now
reads `● valid #2` (or `● warnings #2` — click it to see why).

→ [[History and Versions|Studio-History-and-Versions]]

## 6. Publish to the pilot environment

Open the **Distribute** tab. In the **Publish** panel on the right:

1. **Current** shows `#2 ● valid`; **Draft** shows `no unsaved edits`.
2. Set **Target** to `pilot`.
3. Press **Publish to pilot**.

A card for `pilot` appears. It shows **◌ Building** with a progress stepper
and a build log, then **● Live** with the survey link:

```
https://study.siamang.org/<survey-id>/
```

Press **Copy**. That link stays the same every time you republish `pilot`.

> New projects come with two environments: `pilot` (capped at 50 completed
> interviews) and `main` (capped at 1,200). Use `pilot` for testing, `main`
> for fieldwork. Only completed interviews count toward a cap — not
> screen-outs, not unfinished interviews. On the Free plan the project as a
> whole also stops at 1,000 completed interviews, `pilot` and `main`
> together. See
> [Response caps](Studio-Publishing-and-Environments#response-caps).

→ [[Publishing and Environments|Studio-Publishing-and-Environments]]

## 7. Answer your own survey

Open the link in a new tab, answer, and submit. The thank-you screen shows a
**Response ID** — the row number of your answer in the database.

→ [[What Respondents See|Studio-Respondent-Experience]]

## 8. Look at the data

Open the **Data** tab and pick the `responses` table in the rail. Your row is
at the top — the grid shows the newest rows first: one column per variable
(named after the variable, not the question's Id), plus `survey_id`,
`respondent_id`, `partial`, timestamps and a `meta` column with fieldwork
details.

- **Insights** — instant frequencies and crosstabs, no setup.
- **Export ▾** — CSV, Excel, SPSS, Stata, Parquet or SQLite of the whole
  table. In an export the `meta` column becomes ordinary columns
  (`duration_s`, `started_at`, one `url_<name>` per link parameter, …).

→ [[Responses and the Data Tab|Studio-Responses-and-Data]] ·
[[Data Exports|Studio-Data-Exports]]

## 9. Your first analysis flow

1. Open **Flows** → **New flow**. Give it a title (*Awareness*) and press
   **Open canvas**.
2. The canvas starts with a **Responses** source. Select it and, in the
   inspector, set **Environment** to `pilot` (its default is `main`).
3. From the palette on the left, drag **Frequencies** (under **Analyze**) onto
   the canvas. Drag from the Responses node's `data` output to the
   Frequencies node's `data` input.
4. Select Frequencies and pick your question's **Variable**.
5. Press `Ctrl/Cmd + Enter` (**Run to here**). The inspector shows the table.
6. **Save**, then **Run**. The run appears in **Run history** with its log.

To turn it into a document, add a **Report section** and a **Save report**
node — see [[Reports|Studio-Reports]].

→ [[Analysis Flows|Studio-Flows]] · [[Node Reference|Studio-Node-Reference]]

## 10. Take the code with you

- **Builder → More ▾ → Export Python** downloads `questionnaire.py` for the
  current Save.
- **History** → open a Save → **More ▾ → Download a bundle** → **With the
  responses so far** downloads the whole study — generated code, documents,
  codebook, a Methods draft, a citation file, provenance and your data — as a
  zip you can run outside Studio.

→ [[Reproducibility: Code, Bundles and Citation|Studio-Reproducibility]]

---

## Where to go next

- The whole journey on a realistic study:
  [[Tutorial: A Study from Start to Finish|Studio-Tutorial-End-to-End]]
- The vocabulary in one place: [[Key Concepts|Studio-Key-Concepts]]
- Routing and screen-outs: [[Logic and Branching|Studio-Logic-and-Branching]]
- Before real fieldwork: [[Testing Your Survey|Studio-Testing-Your-Survey]]
- Working with colleagues:
  [[Organizations and Team|Studio-Organizations-and-Team]] and
  [[Working Together|Studio-Collaboration]]

## See also

- [[Siamang Studio — Overview|Studio-Overview]]
- [[Key Concepts|Studio-Key-Concepts]]
- [[Recipes|Studio-Recipes]]
- [[FAQ and Troubleshooting|Studio-FAQ-and-Troubleshooting]]

<!-- studio-nav -->
---

← [[Siamang Studio — Overview|Studio-Overview]] · [Studio contents](Studio-Overview#all-pages) · [[Key Concepts|Studio-Key-Concepts]] →
