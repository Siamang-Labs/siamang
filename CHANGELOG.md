# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **`UIConfig.allow_theme_switch`** — whether the respondent may change the
  survey's light/dark theme. The runtime has always shown that button and
  remembered the choice, which made `default_theme` only ever a starting point:
  a stored value beat it. Set it to `False` and the button is not rendered, the
  stored value is not consulted, and the survey is pinned to `default_theme` —
  the questionnaire is an instrument, and a presentation half the sample can
  change is an uncontrolled variable. It stays `True` by default, because
  reading on a dark screen is an accessibility need rather than a preference.
  `default_theme` is now validated by `UIConfig` like its other enumerations.

- **`theme` and `layout` flow parameters** and per-item placement on `Report`.
  `Report.add()` / `.image()` take a `width`, an `align` and a `break_before`,
  validated where they are written; `output.save_report` takes a `theme` and
  `output.report_section` a `layout` keyed by the item's node, both read by
  `check_flow` so a misspelled field is named on the document rather than raised
  in a run. They are kinds of their own for the same reason `formula` is one.
  The theme travels as plain data in the generated script — no import to add —
  and everything that accepts a theme accepts a mapping too. All of it reaches
  the HTML only: Markdown is the report's content and carries no layout.

- **The respondent's theme is remembered per survey.** The key was the constant
  `siamang_theme`, and `localStorage` is per origin, so every survey served from
  one host shared it: a respondent who chose dark in one study arrived in the
  next one dark. It is now `siamang_theme_<survey id>`, keyed like the saved
  answers beside it by the transport's `survey_id` (the id the runtime read
  before was never set; see the storage entry under *Fixed*), and reading and
  writing it are wrapped: storage does not merely come back empty in a private
  window, it throws.

- **`siamang.reporting.ReportTheme`** and a real HTML document. `Report.to_html()`
  returned a bare `markdown.markdown()` fragment — no `<head>`, no charset, no
  stylesheet — so every caller had to invent a look, which is another way of
  saying the report had none of its own. `to_html(standalone=True)` and
  `save("r.html")` now write a whole document with the theme's stylesheet in it,
  its tables rendered by the table components (so `SurveyTable.to_html()` and its
  `siamang-table` class are finally reached) and its figures in a `<figure>` with
  their caption. The theme is the questionnaire's `UIConfig` shape — one named
  preset plus tokens you may override, stored sparsely — and `academic`,
  `modern` and `humanist` name the same typefaces in both. `Report(theme=…)`,
  `Report.combine(…, theme=…)` and `ReportTheme.from_env()` (via
  `SIAMANG_REPORT_THEME`, mirroring `SIAMANG_PROVENANCE`) are the ways in.
  `to_html()` without `standalone` is unchanged, byte for byte, and Markdown is
  untouched by any of it.

- **Figure geometry on the chart nodes.** `visualize.bar` / `boxplot` /
  `scatter` take `width` and `height` in inches and a `palette`;
  `visualize.heatmap` takes `width`, `height` and `cmap`. `SurveyChart` and the
  `plot` accessor already accepted all of it — the node specifications simply
  never passed it on, so a flow could not change the size of the figure it
  drew. `SurveyChart.dpi` is a field now (default 150) and `save()` falls back
  to it, so whatever writes a figure out can raise the resolution of every
  chart at once without threading an argument through.

- **`MaxDiff`** — best–worst scaling. A few items at a time, and for each set
  the respondent picks the best and the worst; the trade-off is the
  measurement. `siamang.design.maxdiff_design` builds the balanced incomplete
  block design and reports its own balance — how often each item and each pair
  was shown — because a design nobody can check is a design nobody should
  trust. The design is fixed by a seed (derived from the question when none is
  given), so the same questionnaire always asks the same tasks.
- **`siamang.data.choice`** — choice sets and a conditional logit fitted on
  them by maximum likelihood, on numpy and scipy alone. The shape every
  trade-off method needs: alternatives in rows, grouped into the sets one
  choice was made from.
- **`siamang.data.maxdiff`** — counting scores (best minus worst over shown,
  per item and per respondent) and utilities with the shares they imply.
  `report.maxdiff(...)` tabulates both against a base; `analyze.maxdiff` runs
  it from a flow.
- **`Conjoint`** and **`Attribute`** — choice-based conjoint: whole products
  side by side, pick one. `siamang.design.cbc_design` builds the design by
  improving several random starts on D-error, and reports the level balance and
  the task overlap against the floor that is arithmetically forced. A design too
  small to be fitted reports so, and `lint()` says it in words before fieldwork
  rather than after the model fails to converge.
- **`siamang.data.conjoint`** — part-worths in one currency across attributes,
  attribute importance (of the levels tested, which the table says out loud),
  and shares of preference for hypothetical products. `report.conjoint(...)`,
  `analyze.conjoint` and `analyze.conjoint_shares`.
- **`siamang.io.choice.write_maxdiff_choices`** — the choices in the long
  format R's hierarchical-Bayes packages read, with a column dictionary and a
  script, so individual-level utilities can be estimated outside the engine.
  `output.choice_data` and `output.conjoint_data` write it from a flow.
- **`siamang.data.formula`** and **`SurveyData.derive_formula`** — a derived
  variable computed by arithmetic rather than by a condition: the four
  operators, `mean`/`sum`/`min`/`max`/`abs`/`round`/`log`/`coalesce`, and
  `if … then … else`. The formula is text, parsed by hand into a tree and
  evaluated vectorized; nothing is executed, and what cannot be read is
  reported with the character reading stopped at. Missing stays missing —
  dividing by zero gives no value rather than infinity, which would read as a
  number all the way into a report. `formula` is a flow parameter kind, so
  `check_flow` catches a typo before a run; `prepare.derive` runs it.
- **`report.banner(...)`** and **`analyze.banner`** — the cross-break, in the
  shape an agency reads: blocks of columns, a base row, and each cell carrying
  its column percentage, its count and the letters of the columns it is
  significantly higher than. Columns are compared only within a banner
  variable, whose values are mutually exclusive; on weighted data the test uses
  Kish's effective base, and a column under thirty respondents is not tested at
  all. `data.tables.banner` still gives the same numbers in tidy form.
- **`siamang.model`** — the questionnaire as a JSON document.
  `to_document(survey, options)` serializes every core object (`Variable`,
  all seven question types, `Option`, `Media`, `Block`, `Page`,
  `Expression`, `Script`, `Quota`, `UIConfig`, compiler options, deadline)
  into a plain dict; `from_document(doc)` rebuilds them. The round trip is
  lossless: the rebuilt survey compiles to the same `SurveySchema`, and
  re-serializing it returns the same document. Factory-made scripts are
  stored by name and parameters; codebook codes keep their type and order.
- **JSON Schema** for the document format
  (`siamang/schemas/questionnaire-1.0.json`, generated from the dataclasses
  by `scripts/gen_document_schema.py`) and `validate_document()` on top of
  it. `jsonschema` is a new dependency.
- **`siamang model import`** writes a module's `survey` + `options` as a
  document; **`siamang model check`** validates a document the way
  `siamang validate` validates a module.
- **`siamang.codegen`** — `generate_questionnaire(document)` renders a
  document as the Python file a researcher would have written: variables,
  questions, pages (with the page factories), scripts, `survey`, `options`,
  each object marked with `# studio: …`. Output is deterministic, laid out
  like `ruff format` and passed through it when ruff is installed
  (`pip install "siamang[codegen]"`), and converts back to the same
  document with `siamang.model.to_document`. CLI: **`siamang codegen
  questionnaire.json [-o questionnaire.py]`**.
- **Pipeline helpers in `siamang.data`** — `respondents` (`dedup_responses`,
  `completion_time`, `partial_flag`, `speeders`), `weights`
  (`cell_weights`, `rake_weights` with an optional `cap`,
  `effective_sample_size`) and `stats` (`frequencies`, `crosstab`, `chi2`
  on a bare frame). Plain pandas functions that combine with
  `SurveyData.with_frame`; the first two sets were previously only
  available in the Siamang Cloud SDK.
- **`siamang.flow`** — analysis flows. A flow document (`flow-1.0.json`
  schema) is a graph of typed nodes from a YAML **node registry**
  (30 nodes: sources, prepare, analyze, visualize, output; `siamang flow
  nodes`). `check_flow` validates it against the registry and the
  questionnaire's codebook; `FlowRunner` executes it in-process on a
  `SurveyData` or a snapshot, with `live.capture()` collecting the tiles
  `output.live_tile` nodes publish; `generate_flow` renders the script a
  researcher would have written, with a `--data` switch between the
  platform database and a local snapshot. Runner and generator use the
  node templates verbatim, so the script reproduces the runner's report.
  `PyYAML` is a new dependency. CLI: **`siamang flow check | run | nodes`**
  and **`siamang codegen <name>.flow.json --questionnaire …`**.
- `SurveyData.filter(expression)` keeps the rows matching a questionnaire
  condition; `SurveyTable.stats` exposes a table's statistics as a dict;
  `Report.add` accepts a statistics mapping.
- **Snapshots** — `siamang.io.read_snapshot` / `write_snapshot`: a data
  file (Parquet, CSV, Excel, SPSS, Stata) plus `<name>.dictionary.json`,
  read back into a `SurveyData` with the codebook, embedded metadata or the
  questionnaire's variables. Parquet via the new `siamang[parquet]` extra;
  `SurveyDataReader` accepts `.parquet`.

### Fixed

- A required `Matrix` let the respondent through after one row. The runtime
  called any answer object with a key answered — MaxDiff and conjoint already
  asked for every task, a matrix asked for nothing more — so nine rows of a
  ten-row battery the author had made required could be left empty. Next now
  needs an answer in every row (a row answered "Not applicable" has one; a
  matrix has no conditions on its rows, so every row is asked). With some rows
  answered it says "Please answer every row." — the new
  `UIConfig.required_rows_text`, `{n}` being the rows left — and marks those
  rows until each has an answer, in the error colour and with `aria-invalid` on
  their cells; with none it says `required_text`, as before (a row a script set
  to `null` is not an answer). Only Next marks rows: leaving the matrix
  unanswered, or a script's message on it, shows the message alone. Leaving the
  matrix still only asks for an answer at all: focus moves between its cells
  while the respondent works down the rows. A `Script.timed_question`'s
  automatic Next is an ordinary Next and is held the same way, so on a required
  matrix answered in part the respondent stays on the page, finishes the rows
  and presses Next. A `skip_to` on a matrix fires on any row, as before, and
  Studio's walkthrough trace keeps saying so for the skip, while its "answered"
  count now counts a matrix once every row is answered — what Required asks
  for, as it already did for a MaxDiff.
- A matrix could not be answered from the keyboard beyond its first row. The
  arrow keys moved a marker, not the focus — after ↓ the next → answered row 1
  again — and the "Not applicable" column was out of their reach; and Enter or
  Space on any button (a matrix cell, a rating point, a picture choice, the
  dropdown, Previous) pressed Next, so no cell could be chosen and Previous went
  forward. With a required matrix now asking for every row, a respondent without
  a mouse could not finish one. The arrow keys now move the focus from cell to
  cell — ← → along the row, answering it with the cell they reach, the N/A
  column included; ↑ ↓ to the same column of the row below or above — and
  Enter and Space on a button or a link are its own: they choose the cell or
  the point, go back, open the dropdown. So are they on a video or audio player
  (Space plays or pauses — it used to go on, and on the last page to submit
  the survey), on a `<summary>` and on the like in a page's own HTML, and a
  contenteditable region is a text field. Right after the mouse pressed a
  button or a link, while the focus it left there stays, they go on, as they
  always had: in Chromium the key would click again, and a MaxDiff or
  conjoint pick — a toggle — would be taken back. Elsewhere outside a text
  field they still go to the next page.
- The keyboard focus did not show on a chosen matrix cell or MaxDiff pick: the
  inner ring that marks one as chosen replaced the theme's focus ring. The
  arrow keys leave the focus on a chosen cell, and ↑ ↓ onto a row answered the
  same way changed nothing on screen. A chosen cell or pick in focus now shows
  both rings.
- A `SingleChoice` shown as a dropdown could not be answered from the keyboard.
  Enter on its button opened the list with the focus in the search box, and
  there no key worked: the options took no focus, ↓ ↑ and Enter did nothing,
  Esc was ignored and Tab left the list open — a required dropdown held a
  respondent without a mouse for good. The search box is now a combobox over
  the options: ↓ ↑ move along them (`aria-activedescendant`), Enter chooses
  the one they are on and gives the focus back to the button, typing narrows
  the list and puts the keys on its first match, and Esc or Tab away closes
  it. On the button ↓ opens the list and Esc closes it.
- `validate()` let a question whose id is not its answer key (id `q1`,
  variable `nps_1`) carry as its id a name the answers already hold something
  else under: another question's Other text key (`brand_other`), a matrix's
  row variable, a variable `Script.assign_condition` assigns, a codebook
  variable no question collects that a custom script writes
  (`answers.panel = …`, `[answers.panel, x] = …`, `for (answers.panel of …)`,
  `answers.panel.push(…)` — any assignment, update, `delete`, destructuring
  or loop target, or change in place), or one of the runtime's `__` keys. The
  compiler rewrites a custom script's `answers["<id>"]` to the key,
  so `answers["brand_other"]` read the note instead of the Other text, and a
  platform keying an old runtime's answers by id moved the Other text into the
  note's column. Such a document is now refused — "Question 'brand_other'
  stores its answer under 'note', but 'brand_other' is also the key question
  'q1' stores its “Other (please specify)” text under. A script that names
  'brand_other' could mean either; give the question another id." — while an
  id that is its question's own key, which nothing renames, stays free, and so
  does a codebook variable nothing writes: the runtime captures no embedded
  data, and the Builder before patch 0043 left such an entry behind whenever a
  question's variable was renamed (id `q2`, variable `comment`, entry `q2`), so
  those documents stay valid.
- A spread of a question's answer in a custom script — `[...answers.q1]`,
  `Math.max(...answers["q1"])` — was not rewritten to the answer key when the
  id is not the key: the rewrite took the `.` of `...` for some other object's
  `answers`, and the strict lint's stale-id check did not report it either, so
  the script spread `undefined` and failed. It is rewritten like any other
  access now.
- `validate()` rejected a `show_if` / `next_if` on a variable no question
  collects — the arm `Script.assign_condition` writes, or embedded data declared
  in the codebook — as "unknown variables", which made the one thing an
  assignment exists for impossible to publish. Both now count as known
  (`Questionnaire.assigned_variables()`, `Script.assigns`); a name nothing
  writes is still refused. `validate_options` likewise accepts a quota on an
  assigned arm, checking the value against the arm codes — the cell a balanced
  assignment needs — and the piping lint no longer calls an arm piped on the
  first page a forward reference.
- `Script.randomize_pages()` pinned the first and last page and shuffled
  everything between them — a screen-out in the middle of the deck included,
  which put it in front of the questions it is gated on. Every terminal page
  (`disqualification`, `final`, `redirect`) now keeps its own position, along
  with the first and last page; the other pages are dealt into the remaining
  slots.
- `FreqTable`, `CrossTable` and `GroupMeanTable` ignored `SurveyData.weight`
  while the banner, NPS and regression honoured it, so a report built after
  `with_weight()` (the flow's Apply weight node) showed unweighted frequencies,
  crosstabs and means under a weighted heading. They now weight: frequencies
  and crosstab cells are sums of weights with the same percentage
  normalisation, the χ² is computed on counts scaled to the effective (Kish)
  sample size as the banner does, and group means, SDs and medians are
  weighted while N stays the people counted. A weighted frequency table adds an
  `Unweighted N` column and a weighted multiple-choice table an unweighted
  base row; unweighted output is unchanged.
- MaxDiff and conjoint read `SurveyData.weight` for their counts but fitted the
  conditional logit unweighted: `choice_sets()` resolved each row's weight and
  then passed the set weights to the model only when a `weight=` argument was
  given, which no flow node does. So after Apply weight the Score and the
  Utility of one MaxDiff table described two different samples, and conjoint
  part-worths, importance and share of preference were the raw sample's. The
  resolved weight now reaches the model, and `mnl()` rescales set weights to
  sum to Kish's effective number of sets — the estimates are unchanged by the
  scale, the standard errors become those of the effective base rather than of
  the raw rows or of a population total (this also changes the standard errors
  of an explicit `weight=`). The MaxDiff, conjoint and new `ShareTable`
  (`data.report.conjoint_shares`) footers name the `Weight` and give the base as
  `N respondents (W weighted)`; `analyze.conjoint_shares` gains a `stat` output.
- The rest of the analysis now either uses the weight or says it does not.
  `BarChart` draws sums of weights / weighted means and `HeatMap` with `by`
  weighted means (axis or colour bar "Weighted …"); `BoxPlot`, `ScatterPlot`
  and the correlation `HeatMap` get a second title line `unweighted (the weight
  'w' is not applied)`, exposed as `SurveyChart.weight_note`. `pca()` and
  `reliability()` take a `weight` and use the weighted covariance matrix (R's
  `cov.wt`; equal weights reproduce the unweighted result), and the `analysis`
  accessor passes the data's weight. `kruskal`, `mannwhitney`, `spearman`,
  `cluster()`, an unweighted `proportion_ci`, and the quality and theme tables
  say `unweighted (the weight 'w' is not applied)`. A weighted
  `proportion_ci` counted respondents who did not answer in its base, as a
  share of 0, and took Kish's `n` over every row, so a routed or skipped
  question got a diluted share and too narrow an interval (weights of 1 did
  not give the unweighted result); its base is now those who answered, as
  for the unweighted share and the weighted frequencies. `describe_variables()` adds
  `weighted_n_valid`; regression, NPS, TURF and a crosstab without a test name
  the weight. Apply weight's description no longer promises "every table and
  statistic downstream": its help lists what is weighted and what is not.
- The simulator (`siamang.local_simulator`, behind `Questionnaire.simulate()`
  and Studio's Test → Simulate) replayed page and question conditions and the
  routing, but answered every question of a hidden block, picked answer options
  their own conditions hide, never filled the arm of `Script.assign_condition`
  — so a page gated on the arm was empty in every row — and knew nothing of
  page shuffles or quotas. Block `show_if` / `hide_if` (nested blocks too) and
  option `show_if` / `hide_if` now apply — in a wide `MultiChoice` too, where
  a hidden option's variable is missing rather than 0, as the runtime stores
  it, and an exclusive choice now stands alone; a question whose options are
  all hidden is left unanswered. `simulate_from_pages()` takes `scripts=` and
  `quotas=`: each assignment draws its arm before the first page by the arms'
  weights (balanced against the quota cells, as the platform picks, when it
  asks to be), `Script.randomize_pages` deals each respondent a page order,
  block shuffles decide which `skip_to` is met first, and a respondent holding
  a value in a full cell ends on the page being left — an answer, or the arm
  drawn before the first page, as the runtime checks it — only completes
  filling a cell.
  `simulate_questionnaire(survey, …, quotas=)` passes the questionnaire's own
  scripts, and `simulate_survey()` returns the `SurveyData` with a codebook
  entry for each arm; the flow's `source.simulated` node now runs it, and so
  does `Questionnaire.simulate(n, seed)` (without quotas, which are compiler
  options). The walk stays deterministic under its seed, and a survey with
  none of these features simulates exactly as before.
- A single-variable question whose `id` differed from its variable's name stored
  the answer under the **id**, while every `show_if` / `next_if`, quota,
  `{answer:…}` and the codebook read the **variable**. Nothing built on such a
  question ever fired in the field, and its column came out under the id.
  `question_output_name` now returns the variable for a question that writes
  one — a `name` no longer overrides it, and `validate()` rejects a
  single-variable question whose `name` is not its variable; matrix, wide,
  MaxDiff and Conjoint items keep their `name` or id — so the runtime's item
  `id`, the answer key, is the variable and `qid` stays the author's id. A
  `skip_to` and a script still
  name questions by id: the compiler emits a `skip_to` that names a question
  as the name of the page holding it (a page name is left alone), translates
  the target of an `onQuestionShow` / `onAnswer` script — the triggers the
  runtime dispatches with a key; a page-scoped target is a page name and is
  left alone — as well as a `randomize_options` / `timed_question` question
  and the two `validate_fields_match` fields to the key, and rewrites the
  `answers["q1"]`, `answers.q1`, `__errors__[…]`, `__options__[…]` and
  `__timers__[…]` accesses of such an id in a custom script's code.
  `lint(level="strict")` reports `SCRIPT_STALE_QUESTION_ID` where a custom
  script still names such an id as a string or a bare identifier the compiler
  does not translate (a comment, or a string that merely mentions the id, does
  not count), and `SCRIPT_TARGET_IS_A_PAGE` / `SCRIPT_TARGET_IS_A_QUESTION`
  where an `onQuestionShow` / `onAnswer` script targets a page or an
  `onPageEnter` / `onPageExit` script targets a question — a target the
  runtime never dispatches those triggers with, so the script never ran;
  `validate()` accepts a target by either name and rejects a document in which
  two questions share a key or a question's id is another question's key.
  Responses collected before this change under such an id are not moved.
- `data.tables.banner` died with "Grouper not 1-dimensional" when a variable was
  used as both a row and a banner column — which is how you read a base
  distribution across the banner. It now builds its own frame instead of
  indexing the original by label.
- `local_simulator` crashed on a half-open `valid_range` such as `(16, None)`,
  treated an unreadable string `hide_if` as met — hiding that question from
  every simulated respondent — and both produced columns of nulls, which look
  exactly like a question nobody reached.
- A `Matrix` cell stored its column's **position + 1**, not a code: a 0–10
  scale was recorded as 1–11, and any codebook not coded 1…n (a recode, a
  "Refused" 9) came out wrong. A cell now stores the code of the row
  variables' codebook that `Matrix.columns()` pairs with its header — by the
  label's text, else by position once the codebook's declared missing codes —
  an N/A, a refusal, a don't know — are set apart (a header naming one of them
  takes its code, wherever the codebook lists it: SPSS-origin codebooks put
  -8 "Don't know" before 0 … 10), else by position over every label when the
  counts match, else 1, 2, 3 … as before. Without headers the columns are the labels in code order,
  less the not_applicable code `na_option` offers in its own column (it was
  offered twice, first in the middle of the scale). Responses already
  collected keep the positions they were stored with.
- A `Matrix`, a `MaxDiff` and a `Conjoint` stored their answers as **one
  object under the question's key** (`{"trust": {"trust_parl": 3, …}}`), while
  every `show_if` / `next_if`, quota, `{answer:…}` and the codebook read the
  variables by name — so a condition on a matrix row or a task never fired.
  Each variable is now a top-level key of the answers (`trust_parl: 2`,
  `md_t1_best: 3`, `md_version: 0`) and nothing is stored under the question's
  key, which stays the handle a script targets. Answers a respondent saved in
  the browser under the old layout are moved to the new one when they resume
  (a saved matrix position becomes its code). Responses already collected keep
  the nested object.
- `{label:x}` piping inserted the raw code: the runtime looked the labels up in
  `window.SURVEY.pages`, which does not exist, so its label index was always
  empty. It reads the pages now — a choice's label, a matrix column's header, a
  MaxDiff item.
- A **wide** `MultiChoice` (one 0/1 variable per choice) stored the list of the
  chosen variables' *names* under the question's id, so its variables stayed
  empty, a condition or quota on them never matched, and `exclusive` — which
  names choice codes — never applied, the options' codes being variable names.
  Each variable is now stored under its own name, `1` when chosen and `0` when
  the question is answered and the option is not (nothing while unanswered,
  nor for an option its own `show_if` / `hide_if` hid: it was not offered.
  The condition is read again after every answer, whatever gives it — a click,
  a Likert digit key, a script — so one given later, on the same page say,
  that offers or hides the option makes it 0 or nothing, and so does another
  wide question's 0 turning into nothing when the condition reads it);
  with one choice per variable, option *i* is choice *i* on variable *i*, so
  `exclusive` works. A saved answer in the old layout is converted when the
  respondent resumes. Responses already collected keep the list.
- **"Other (please specify)", "None of the above" and N/A stored sentinels**
  instead of codes: a `SingleChoice` with Other wrote `{"code": "__other__",
  "text": …}`, a `MultiChoice` with Other always wrote `{"selected": […],
  "otherText": …}` (so `contains` conditions on it never matched, and two such
  questions collided once the object was unwrapped), "None of the above" was
  `"__none__"` and N/A `"na"`. Other now stores a code of the variable —
  `metadata["other_code"]`, default `-66` (`DEFAULT_OTHER_CODE`); a choice with
  that code *is* the Other option — and the typed text goes under
  `<variable>_other` (a wide question: `<name or id>_other`) while Other is
  chosen. "None of the above" stores `metadata["none_code"]`, default `-77`
  (`DEFAULT_NONE_CODE`). N/A stores the variable's `not_applicable` missing code
  (`na_code`) and keeps `"na"` only when the codebook declares none. The
  dropdown display now offers Other at all. `validate()` refuses a code that is
  neither a number nor a string, a None code that is already an answer's, the
  default Other code on a question whose choices use it, and an Other text key
  that is another answer's; the Other text is a variable a condition may read.
  `lint()` reports `ADDED_CODE_WITHOUT_LABEL` and `NA_STORED_AS_TEXT`. Answers
  a respondent saved in the browser with the old sentinels are converted when
  they resume; responses already collected keep them. The Qualtrics importer
  sets `other_code` to the recode of the text-entry choice, which was shown
  twice before — as itself and as the runtime's own "Other".
- A completed response carried the runtime's own state next to the answers:
  `__pages__` (the whole questionnaire, in the respondent's order),
  `__options__`, `__errors__`, `__timers__`. Besides bloating every row, a
  reader that unwraps nested objects one level turned `__options__` into
  columns named after the questions, over the answers. A submission now holds
  the answers and `__status` only.
- **Quotas were never enforced by the survey runtime.** Nothing called the
  transport's `checkQuota`, so cells filled past their limits and nobody was
  turned away. The compiled survey now names its quota variables
  (`SURVEY.quotaVars`, not their values or limits), and when a respondent
  leaves a page the runtime asks `checkQuota(variable, value)` about each of
  them holding a value it has not already found open — a list for a
  `MultiChoice`. On `{ok: false}` the interview ends before routing on the
  "quota full" screen (and `ui.quota_full_redirect_url`, if set), with nothing
  submitted; an error, a transport without `checkQuota` or a check slower
  than 4 s lets the respondent go on. The bundled transports now throw on a
  failed request instead of answering `{ok: false}`, which would have read as
  "full".
- The Qualtrics importer dropped a wide multi-select's exclusive answers
  ("not available when choices are separate variables") and gave it no
  choices. It now keeps the choices beside the variables — choice i on
  variable i — with their exclusive codes and, for a text-entry choice,
  `other_code`, all of which the runtime honours in the wide layout.
- The `body` of an ordinary page with questions was never shown: the runtime
  rendered a body only on engine-kind `"content"` pages (and terminal ones),
  so an introduction above a page's questions silently disappeared. A body is
  now shown above the questions on every page. It is HTML, inserted as the
  author wrote it, with piped answers escaped — as documented; a question's
  text and hint stay plain text.
- The title and body of a terminal page (`final`, `disqualification`,
  `redirect`) were shown as written: `{answer:x}` / `{label:x}` stayed
  literal braces on exactly the page that thanks a respondent by name. They
  are piped now, the body's values escaped, as on every other page.
- `UIConfig(show_title=False)` did not hide the title once a logo or an
  institution was set: the header was shown for them and always included the
  title. The payload now carries `showTitle` apart from `showHeader`, and the
  header leaves the title out when it is false.
- `Script.validate_fields_match` re-checked only when the *second* field
  changed, and never removed its message: correcting the first field left the
  error in place and Next blocked. The script now has no target, so it runs on
  every answer, sets the message on a mismatch and removes it on a match; and
  the runtime shows a script-written message from the store instead of a copy
  taken when Next was pressed, so a cleared message disappears at once.
- A seeded `Script.assign_condition` sent every respondent to the **same arm**,
  and every respondent saw the same MaxDiff/Conjoint design version: both are
  keyed by `answers.__respondent__`, which nothing set. The runtime now sets it
  when the survey loads — the transport's `respondentId()` when it has one,
  else a random id kept in the browser until the interview is submitted (or
  ended by a full quota), so a reload keeps the arm and the design.
- An embedded survey never told the page around it how tall it was, so an
  "auto-height" embed kept its initial height and scrolled inside the page.
  In an iframe the runtime now posts `{type: "siamang:height", height}` to
  its parent on load and whenever its content's height changes.
- The **page dots** (`progress_style="dots"` / `"both"`) jumped to any page,
  forward included: a respondent could skip past unanswered required questions
  and the routing between the current page and the one clicked. A dot now goes
  back only to a page on the path that led to the current one (and not at all
  with `allow_back=False`); a dot ahead, or of a page the routing skipped, is
  disabled. Going back by a dot runs `onPageExit` like Previous and retraces
  the path, which the autosave now keeps, so a resumed interview can still go
  back the way it came.
- A `MultiChoice`'s `min_answers` and a `NumericInput`'s valid range were not
  enforced: Next checked only `required`, the text formats and script messages,
  so one choice of a minimum of two, or 150 on a 1–10 scale, went through; the
  number's "Minimum value is …" / "Maximum value is …" message was the
  component's own and was never rendered. Next now refuses both with those
  messages ("Select at least N more" for the choices), and a number out of
  range is flagged as soon as its field is left. An optional question left
  empty is still not held by its minimum, and neither is an exclusive answer
  ("None of these" clears every other choice, so it is a whole answer by
  itself). The "Select at least N more" hint under the options now also shows
  without `max_answers`, once the question is answered or when it is required,
  until an exclusive answer is picked.
- `Script.timed_question`'s timer was never cancelled: a respondent who left
  the page before it ran out had Next pressed for them later, on whatever page
  was showing — the last one included, which submitted the survey. The runtime
  now cancels every timer kept in `answers.__timers__` whenever a page is left
  (Next, Previous, a page dot, Studio's design-mode jump) and when the survey
  is submitted or ended by a full quota; and the next-page hook does nothing
  once the interview is over, while it is being submitted, or on a terminal
  page. A timer still runs once per question.
- `Script.randomize_options(question, seed=…)` ignored its seed: the runtime
  shuffled with `Math.random`, so "same seed, same order" held for nobody and
  a reload reshuffled. The order is now drawn from `"<seed>:<respondent id>"`
  with the FNV-1a/mulberry32 pair a seeded `assign_condition` uses: each
  respondent keeps one order across reloads and resumes, and it can be
  recomputed from the seed and their id. `utils.shuffle(list, seed)` and
  `utils.sample(list, n, seed)` take the optional seed for custom scripts;
  without one they are random as before.
- Shuffling a question's options — `randomize=True` or
  `Script.randomize_options` — moved "None of the above" and a `MultiChoice`'s
  exclusive answers ("None of these") into the middle of the list, and a choice
  that is the question's "Other" (`metadata["other_code"]`) with them; only the
  runtime's own "Other", added after the options, stayed last. The compiler now
  marks those options `"fixed": true` and both shuffles keep them in their
  place, dealing the other options into the remaining positions.
  `utils.shuffleOptions(options, seed?)` does the same for custom scripts.
- A script's **`context`** was only the static dict set on the `Script`: the
  runtime passed an empty object for its own part, so the documented and
  templated uses — `context.startedAt` to flag speeders, the page being left for
  a dwell time — read `undefined`. It now also holds `trigger`, `startedAt`
  (the page load, or for a resumed interview the sitting that saved it — kept
  with the autosave), `respondentId`, `surveyId`, `page`, `pageEnteredAt` and,
  for `onQuestionShow` / `onAnswer`, `question`; a key the `Script` sets itself
  wins. `Script.sandbox` was documented as running the code "in a sandboxed
  iframe" / "no DOM access", and nothing ever applied it: the docs now say it
  is recorded but not applied, and that scripts run as part of the page.
- `progress_style="dots"` showed the bar as well as the dots — the same as
  `"both"` — and `show_progress=False` hid the bar but left the dots of a
  `"dots"` or `"both"` style. The bar (with its text) now shows for `"bar"` and
  `"both"`, the dots for `"dots"` and `"both"`, and `show_progress=False` hides
  both.
- The progress text and the page's section label ("Welcome", "Section *n* of
  *m*", "Final thoughts") were baked into each page by the compiler from its
  place in the document, counting the end pages: a survey ending on a thank-you
  and a screen-out page showed "Section 2 of 4" on its last question page and
  never reached "Final thoughts" or a full bar, and after `randomize_pages` the
  labels travelled with the pages ("Section 3" shown second). The runtime now
  works them out from the pages the respondent answers — visible, in their
  order, without the end pages — and so does the bar's percentage; the page
  dots are one per such page. `UIConfig.show_section_numbers` and
  `show_progress_text`, which nothing read, now apply: without section numbers
  the page has no label and the bar says "Page *n* of *m*" (`page_text`,
  `of_total_text`, until now heard only by screen readers); without progress
  text the bar has none.
- **The runtime's wording is all replaceable.** `UIConfig.estimated_minutes`,
  `of_text`, `select_placeholder`, `selected_text`, `completion_title` and
  `completion_body` were accepted and never used, and about forty phrases were
  English in the runtime or the compiler — "Welcome", "Section n of m", "Final
  thoughts", "Other", "None of the above", "Not applicable", the format
  messages, "Response ID", the closed, full-sample and error screens, the
  redirect notices, the footer's "Privacy" and "Contact research team",
  "Invalid access code…", "Attempt n of 3." and more. `estimated_minutes` now
  shows under the first page's title ("About 12 minutes"); the existing fields
  reach the dropdown, the multiple-choice counter and the completion screen
  (`completion_body` before the `completion_text` option); and `UIConfig`
  gains a field for every other phrase — `welcome_text`, `section_text`,
  `final_section_text`, `estimated_time_text`, `other_text`,
  `other_placeholder`, `none_of_above_text`, `not_applicable_text`,
  `min_choices_text`, `max_reached_text`, `min_value_text`, `max_value_text`,
  `chars_remaining_text`, `search_placeholder`, `no_options_text`,
  `ranking_hint_text`, `ranking_remaining_text`, `invalid_format_text`,
  `invalid_email_text`, `invalid_phone_text`, `invalid_url_text`,
  `invalid_date_text`, `invalid_time_text`, `response_id_text`,
  `submitted_text`, `screen_out_title`, `redirect_countdown_text`,
  `redirect_link_text`, `redirecting_text`, `redirecting_link_text`,
  `quota_full_title`, `quota_full_body`, `closed_title`, `closed_body`,
  `error_title`, `error_body`, `attempt_text`, `privacy_text`, `contact_text`,
  `skip_link_text`, `access_error`, `page_error_title`, `page_error_body`,
  `app_error_title`, `app_error_body`, `reload_action` — all `None` by default,
  which keeps today's English. The document schema admits them; the static
  closed page uses `closed_*` / `quota_full_*` too.
- What the runtime keeps in the browser — the autosave, the theme, the
  interview's id — was keyed by `SURVEY.surveyId`, which the compiler never
  sets, so every survey used `…_siamang_survey`. On a host that serves many
  surveys from one origin (Studio: `study.siamang.org/<survey id>/`) a
  respondent was offered one study's saved answers to resume in another, and
  Studio's transport, which reads `siamang_answers_<survey_id>` to post partial
  responses, never found any. The key is now the transport's `survey_id`
  (`SIAMANG_ENV.survey_id`) unless the host sets `SURVEY.surveyId`; the old
  constant is only the fallback of a page with neither. Progress saved under
  the old key is not offered after the update — it may be another survey's.
- A condition comparing with `None` meant something else in the browser than
  in Python. The compiler wrote `x != None` as `a["x"] !== null`, but the
  runtime has no key for a question nobody answered — its value is
  `undefined` — so "x was answered" held for every respondent who skipped `x`,
  `x = None` held for nobody, and `x in [None, 1]` never matched an empty
  answer. An attention check on a question without codes (screen out when
  `check != None and check != 3`, as Studio writes it) screened out everyone
  who left an optional check empty. Comparisons with `None` are now compiled
  loosely (`== null` / `!= null`, and an unanswered value counts as `null` in
  an `in` list), in the compiled conditions, in the runtime's evaluator of
  expression trees and in its parser of string conditions alike, matching
  `Expression.evaluate`; in a string condition (`"{x} != null"`, as
  `Expression.to_surveyjs()` writes `None`) `null` is now the literal rather
  than a variable of that name, so `{x} in [null, 3]` also holds for an
  answer stored as `null`.
- The runtime asked "Leave site?" when a respondent closed or reloaded a
  survey they had not touched, whenever a script had written a variable at
  load — the arm `Script.assign_condition` draws, an id an `onInit` script
  notes: it counted any answer key in the store as the respondent's. It now
  asks only once the respondent has answered something in this sitting (and
  the interview is not over).
- **A nested block's `show_if`, `hide_if` and `randomize` never reached the
  survey runtime**: the compiler flattened a block's nested blocks into one
  list of questions, so a hidden nested block's questions were shown — and a
  required one among them held Next — while `validate()`, the model and the
  simulator treated them as hidden. Each question inside nested blocks now
  carries those blocks' conditions (`gates` in the payload) and is shown only
  while all of them and its own condition allow it; Studio's walkthrough trace
  lists the nested blocks and says which one hides a question. A nested
  block's `randomize` shuffles its own items, and a shuffling block moves a
  nested block as one item, its questions together and in order (sent as the
  block's `layout`); the simulator deals block shuffles the same way. A block
  without nested blocks compiles exactly as before. In a questionnaire made
  only of blocks, where each block becomes a page, the block's conditions now
  gate its page and its `randomize` shuffles the page's items; the simulator
  walks such a questionnaire on those pages too (it answered every question of
  it, hidden blocks and question conditions notwithstanding), and so does the
  questionnaire document (`to_document`, `siamang model`), which dropped the
  blocks' conditions and shuffle — an owners-only block was shown to everyone
  once the questionnaire was imported — and took loose questions out of their
  blocks.
- `check_flow` reported a node naming the arm of `Script.assign_condition` —
  a crosstab by `condition` — as `UNKNOWN_VARIABLE` unless the questionnaire
  document also declared it in `variables`, although real responses and
  Simulated data carry the column. The arm now counts as known, as it does for
  `validate()`, and is nominal unless the codebook says otherwise.
- The local server (`siamang preview`, `backend="local"`) answered the
  runtime's quota check with `LocalBackend.increment_quota`, which claimed a
  place in the cell for every respondent whose answer was checked — those who
  dropped out afterwards or were screened out included — so a cell filled
  before its completes reached the limit. `/quota-check` now only reads
  (`check_quota`, which takes a list and is full when any value's cell is),
  and `store_response` counts a completed response — anything but
  `__status: "screened_out"` — in every cell its answers fill, a list answer
  in the cell of each value it holds, as Studio counts them. Only a variable
  answered with a list (an array `MultiChoice`, a `Ranking`) is counted that
  way: a list posted for a single-answer variable fills no cell, so one
  submission cannot take a place in every cell of it. Both go through the
  survey's cells in one pass, whatever the length of the list posted.
- The autosave of an interview that had ended was written back after it
  ended. It is written 2 s after the last answer, and ending the interview
  (Submit, a full quota on leaving a page or in the reply to a submission)
  removed the saved answers without cancelling the save still pending from an
  answer given just before — the usual case. The thank-you or quota-full
  screen was followed by a fresh `siamang_answers_<survey_id>`, the next visit
  within a day offered to resume the finished interview (a second completed
  response when accepted), and Studio's transport, which reads that key for
  partial responses, posted it as one. An ended interview now cancels the
  pending save and writes none afterwards; a submission refused as a full
  quota also forgets the saved answers and the interview id, as a full quota
  found on leaving a page does.
- Resuming a survey with `Script.randomize_pages` landed on the wrong page.
  The shuffle deals a new page order at every load, and the autosave kept the
  page's position and the path but not the order they count in, so the
  resumed interview applied the old position to the new order: the
  respondent landed on a page already answered, pages before it they had
  never reached were never shown, others were shown twice, and a "completed"
  response lacked required answers. The autosave now keeps the page order
  (`pageOrder`, the pages' names) and Resume restores it when it names the
  survey's pages; progress saved by an earlier runtime resumes as before.
- A Likert answered with a digit key (1–9, when no field has the focus) was
  written past the runtime's answer handling: it was not autosaved, ran no
  `onAnswer` script and left the question's error on screen. It is now
  answered as a click answers it. On a scale that starts at 0 the digit is
  still the point's value, and a digit the scale does not have (5 on 0–4)
  answers nothing; it stored that value.
- **Generated code ran what an author's text put after a line break.** A flow
  node's banner comment (`# ── Report section: <heading>`) carries its
  parameters as written, and the questionnaire module marks each definition
  `# studio: <question id>` (a variable's, a page's name). A heading or an id
  holding a line break ended the comment there, and what followed was
  module-level code: it ran on import — in a platform's flow run and on the
  machine of whoever runs a research bundle (`environment/run.sh`). Every line
  break and control character on a comment line is now a space; the text
  itself still reaches the report and the questionnaire as written.
- **An object-form codebook meant what its text happened to list first.** The
  shorthand `{"0": "No trust at all", …, "10": "Complete trust", "-1": "Not
  applicable"}` was read in the order of its JSON text, and nothing keeps that
  order: Postgres `jsonb` lists keys by length ("-1" between "9" and "10"), a
  browser lists the whole-number keys first. The order is the one a choice
  shows its options in and a matrix lines its headers up with, so the same
  document stored in `jsonb` offered "Not applicable" between 9 and 10, and a
  matrix headed `0` … `10`, "Not applicable" over it stored -1 for "10" and 10
  for "Not applicable" — where a browser's copy of that document, a preview,
  stored 10 and -1. The shorthand is now read in one order whatever its text
  lists: codes 0 and up ascending, then the negative codes from -1 down, then
  text codes as listed — for whole-number codes the order a browser gives the
  codebook read back from `jsonb`. The list form keeps the author's order as
  before. A hand-written document whose object lists its codes in another
  order (5 … 1, or -8 before 0) is now read in this one — its options, a
  matrix's positions and a MaxDiff's implied design (one with no stored
  `design`) with it; writing the codebook as a list in the object's order
  keeps the earlier reading.

## [0.6.0] — 2026-08-30

Runtime documentation-parity release: everything the docs describe for the
respondent experience now actually runs in the browser.

### Added

- **Routing in the respondent runtime**: `Question.skip_to`,
  `Page.next_if`, and `Page.default_next` are compiled into the React
  payload and executed — skip_to of the first answered visible question
  wins, then the first matching `next_if` rule, then `default_next`, then
  the next visible page. Targets may be page names or question ids; a jump
  to a page hidden by its own gates falls through to the next visible page
  in document order. "Previous" retraces the actual visited path.
- **String conditions**: plain-string gates in the SurveyJS dialect
  (`"{age} >= 18"`, `"age >= 18"`, `and`/`or`/`not`, `in [..]`,
  `contains`, `empty`/`notempty`, parentheses) are now parsed and
  evaluated by the React runtime, for page/block/question/option gates and
  string `next_if` rules. An unparsable string keeps the historical
  always-visible behaviour (with a console warning); as a routing
  condition it counts as not matched.
- **All seven script triggers dispatched**: `onPageEnter`, `onPageExit`,
  `onQuestionShow` (when a question first becomes visible), and
  `onRandomize` now fire alongside `onInit`/`onAnswer`/`onSubmit`. Script
  writes into `answers` sync back to the reactive store, which makes the
  documented `answers.__options__` / `__pages__` / `__errors__` /
  `__timers__` contracts real: `Script.randomize_options` reorders
  options, `Script.randomize_pages` reorders navigation,
  `Script.validate_fields_match` messages render under the field and block
  "Next" until resolved, `Script.timed_question` auto-advances via the new
  `window.siamangNext` hook.
- **Author-declared randomization**: `Question.randomize`,
  `Block.randomize`, and `Page.randomize_blocks` are applied once per
  respondent at load time (standalone questions keep their positions).
- **Choice behaviours**: `MultiChoice.exclusive` codes clear — and are
  cleared by — other selections; `SingleChoice.none_of_above` appends the
  documented option (sentinel code `__none__`, mirroring `__other__`).
- **Matrix**: `subquestions` override row labels; `na_option` adds the
  "Not applicable" column (stored as `"na"`, same as `LikertScale`).
- `SurveyData.create_index(method="sum")` (row sum, `min_count=1`);
  `"mean"` remains the default.

### Fixed

- Option-level `show_if`/`hide_if` never gated anything: the
  `isVisibleGated` helper that the option renderer called was not defined.
- `siamang deploy` now loads `~/.siamang.toml` automatically, as
  documented — defaults, profiles (`--profile`), and stored credentials
  apply without an explicit `--config`.
- Environment credential overlays (`SIAMANG_*`, `VERCEL_TOKEN`,
  `NETLIFY_AUTH_TOKEN`, legacy `SURVLIB_*`) now apply even when no config
  file exists on disk.
- Question components re-render when their option order or option gates
  change (previously blocked by the memo comparator).

### Changed

- **License**: switched from MIT to dual licensing. Noncommercial use is
  free under the **PolyForm Noncommercial License 1.0.0** (`LICENSE`);
  commercial use now requires a separate commercial license
  (`LICENSE-COMMERCIAL.md`). Versions up to and including 0.5.0 remain
  available under the MIT License.
- Build: `setuptools>=77` is now required (PEP 639 license metadata).

### Known limitations

- `simulate()` still ignores routing (`next_if`/`skip_to`) — it models
  visibility gates only.
- `Questionnaire.preview()` (the Python method) returns a one-line
  summary; use `siamang preview` for the real rendered survey.
- `validate()` checks that `skip_to` targets exist but does not include
  `skip_to` edges in reachability/cycle detection.
- The alternative SurveyJS runtime does not evaluate the new routing
  payload; the default React runtime does.

## [0.5.0] — 2026-05-28

### Added

- **Theming system**: `UIConfig` with `font_preset` (classic, modern, humanist),
  `accent_color`, and CSS custom properties for full visual customization.
- **"Other (specify)"** option for `SingleChoice` and `MultiChoice` questions
  via `other_specify=True`.
- **Answers store**: lightweight reactive store (`useSyncExternalStore`) replacing
  top-level `useState` — eliminates full-tree re-renders on every keystroke.
- **Compiled visibility**: `show_if`/`hide_if` conditions compiled to JS functions
  at load time (no more per-render AST interpretation).
- **Hooks decomposition**: `useSurveyNav`, `useSubmission`, `useAutosave`,
  `useLifecycleScripts`, `useKeyboardShortcuts`, `useTheme`.
- Supabase backend now uses a single shared `responses` table with `survey_id`
  column (consistent with local SQLite backend).
- Environment variable naming: `SIAMANG_SUPABASE_*` with backward-compatible
  fallback to legacy `SURVLIB_SUPABASE_*`.
- Script factory functions now use `json.dumps()` for parameter escaping
  (prevents injection from special characters in IDs/messages).

### Changed

- Development status set to **Beta** (honest reflection of current test coverage).
- Slider component: adaptive tick rendering (≤20 steps → labeled ticks,
  >20 steps → end-labels only). Fixes the "wall of numbers" bug.
- Frontend JS globals renamed: `window.SIAMANG_ENV` / `window.SIAMANG_TRANSPORTS`
  (runtime falls back to legacy `SURVLIB_*` names for backward compatibility).

### Fixed

- Supabase backend/frontend mismatch: frontend now POSTs `{survey_id, data}`
  matching the shared table schema (previously sent `{survey_id, payload}` to
  a per-survey table that didn't have a `survey_id` column).
- Slider rendering bug: no longer outputs 61 `<option>` elements for range 0–60.

### Removed

- Per-survey table creation (`responses_{survey_id}`) in Supabase backend —
  replaced by shared `responses` table.
- `BUILD.md` reference removed from MANIFEST.in (file never existed).

## [0.4.1] — 2026-04-15

### Added

- Initial public structure with core survey engine, React frontend, CLI,
  local SQLite backend, and Supabase/Vercel deployment support.
