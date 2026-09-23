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
  next one dark. It is now `siamang_theme_<survey id>`, the way the saved answers
  beside it have always been keyed, and reading and writing it are wrapped —
  storage does not merely come back empty in a private window, it throws.

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

### Fixed

- `validate()` rejected a `show_if` / `next_if` on a variable no question
  collects — the arm `Script.assign_condition` writes, or embedded data declared
  in the codebook — as "unknown variables", which made the one thing an
  assignment exists for impossible to publish. Both now count as known
  (`Questionnaire.assigned_variables()`, `Script.assigns`); a name nothing
  writes is still refused. `validate_options` likewise accepts a quota on an
  assigned arm, checking the value against the arm codes — the cell a balanced
  assignment needs — and the piping lint no longer calls an arm piped on the
  first page a forward reference.
- `data.tables.banner` died with "Grouper not 1-dimensional" when a variable was
  used as both a row and a banner column — which is how you read a base
  distribution across the banner. It now builds its own frame instead of
  indexing the original by label.
- `local_simulator` crashed on a half-open `valid_range` such as `(16, None)`,
  treated an unreadable string `hide_if` as met — hiding that question from
  every simulated respondent — and both produced columns of nulls, which look
  exactly like a question nobody reached.

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
