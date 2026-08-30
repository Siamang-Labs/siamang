# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
