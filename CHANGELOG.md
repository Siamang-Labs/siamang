# Changelog

All notable changes to `siamang` will be documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.5.0]

### Changed — React runtime no longer needs Node at run time

The React bundle (`siamang/frontend/templates/react/dist/bundle.js`)
is now built **once at wheel-build time** and shipped verbatim inside
the package. At survey-render time `ReactRuntime` reads it from
package data — no `npx`, no `sucrase`, no `esbuild`, no
`@babel/standalone` in-browser fallback. Removes the entire class of
"slow first paint / silent fallback / npm registry timeout" failure
modes that plagued 0.4.2 through 0.4.9.

Practical impact:

- A user on a Colab kernel without Node now starts `siamang preview`
  in milliseconds instead of waiting 5-15 s for `npx` to fetch
  `sucrase` from the npm registry.
- Containers and CI images without Node work out of the box.
- The bundle is deterministic per siamang version — every install of
  0.5.0 serves the identical compiled JS.
- If the bundle is missing (someone hand-edited the wheel or built
  from a source checkout without running the build script),
  `ReactRuntime` raises a clear `RuntimeError` instead of silently
  falling through to a degraded path.

### Added

- **`scripts/build_react_bundle.py`** — rebuilds `dist/bundle.js` from
  the JSX sources. Run after editing `app.jsx` or `questions.jsx`.
  Supports `--check` for CI-style drift detection (exit code 2 if
  the committed bundle doesn't match the sources).
- **Visibility expression memoisation.** `evalConditionMemoized`
  caches per-AST-node, keyed by the dependency slice — repeated
  evaluations of the same `show_if` against the same values return
  the cached result without walking the JSON AST again.
- **Visibility-dep signature for `pages` useMemo.** The
  `visiblePages` list now depends on a string signature derived only
  from answers that some `show_if` / `hide_if` actually references,
  instead of the full `answers` object reference. Typing into a
  free-text field that no expression depends on no longer bumps the
  pages list reference, which means downstream `useMemo` and
  `React.memo` skips fire correctly.

### Removed

- `_compile_jsx_to_js`, `_combined_jsx`, `_maybe_minify`, the
  `npx sucrase` and `npx esbuild` subprocess pipeline, the
  `@babel/standalone` browser-side fallback, and the
  `[react] sucrase / esbuild …` diagnostic banner in
  `siamang preview` — none needed now that the bundle ships
  precompiled.
- `import os, shutil, subprocess, tempfile, sys` and `from pathlib
  import Path` from `siamang/frontend/runtime/react.py`. The
  runtime module is now pure I/O over package data.

### Compatibility

- `ReactRuntime(precompile=...)` keeps the `precompile` keyword
  argument as a no-op for API stability. The runtime always serves
  the packaged bundle now.
- `Questionnaire` Python API unchanged. Surveys authored against
  0.4.x render identically.

## [0.4.9]

### Performance

Continuation of the 0.4.8 work, attacking the two remaining causes of
"feels laggy in Colab" that were outside the React render path itself.

- **React UMD vendored into the bundle.** Previously
  `react.production.min.js` and `react-dom.production.min.js` were
  pulled from `unpkg.com` on first paint. Through the Colab port
  proxy this added 1-3 s of round-trip latency on every fresh visit.
  Both files now ship inside the wheel under
  `siamang/frontend/templates/react/vendor/` (~140 KB total) and the
  HTML template references `vendor/react.production.min.js` /
  `vendor/react-dom.production.min.js`. No external CDN dependency
  on the survey rendering path. Works offline.
- **`LocalFrontend` static-asset router accepts nested paths.** The
  previous guard refused any URL containing `/`, so the vendored
  files would have 404'd. Now allows nested paths but still rejects
  absolute paths and `..` traversal attempts.
- **`siamang preview` prints a compile-path diagnostic.** On
  startup the CLI now writes one of:
    `[react] sucrase + esbuild minify available — fast path`
    `[react] sucrase available, esbuild not — \`npm install -g esbuild\` …`
    `[react] sucrase not found — \`npm install -g sucrase esbuild\` …`
    `[react] no \`npx\` on PATH — bundle falls back to @babel/standalone …`
  So you can tell at a glance whether the slow in-browser JSX
  compile path is in use, instead of guessing.

## [0.4.8]

### Performance

Five complementary fixes targeting the "preview feels laggy" complaint
that wasn't fully solved by the 0.4.7 changes. Combined effect:
bundle shrinks from ~67 KB to ~40 KB, typing in a text/numeric field
no longer re-renders the entire app on every keystroke, and the
always-visible GPU compositor passes are gone.

- **Uncontrolled OpenText / NumericInput.** The DOM owns the live
  value while typing; React state is updated on blur and on a 600 ms
  idle. Previously every keystroke flowed through `setAnswers` and
  re-rendered every other question on the page. Now typing produces
  ~3 DOM mutations total (was O(N) per char, where N = questions on
  the page).
- **`React.memo` on the `Question` dispatcher.** Combined with the
  stable callbacks below, clicking a radio in question A no longer
  re-renders questions B…Z. Comparator is conservative — ignores
  `answers` unless the question pipes text from another answer
  (`{answer:x}` / `{var:x}` / `{label:x}`).
- **Stable `setAnswer` / `handleBlur` / `handleNext` / `handlePrev`.**
  All wrapped in `useCallback([…])`; volatile state flows through
  refs so the callbacks never need to be recreated. `SurveyPage` /
  `Question` API changed: receives stable `setAnswer` plus `qId`, and
  the dispatcher builds per-question `onChange`/`onBlur` closures
  internally so memo's identity check isn't defeated by per-render
  inline arrow functions.
- **`backdrop-filter: blur(...)` removed in three places.** Two were
  on overlays shown only briefly (loading/retry), the third was on
  the always-visible theme-toggle pill. The blur was triggering a
  compositor pass every frame; replaced with a solid background.
- **Autosave moved to `requestIdleCallback`.** `localStorage.setItem`
  with a sizable JSON payload was running synchronously on the
  debounced 2 s timer, blocking the main thread. Now scheduled
  through `requestIdleCallback` (falls back to `setTimeout(…, 1)` on
  Safari).
- **Bundle minification step.** After Sucrase/Babel transpile, the
  output is piped through `npx esbuild --minify --target=es2020`.
  Cuts the bundle from ~67 KB to ~40 KB (~60% smaller, lower browser
  parse/execute cost). If esbuild isn't installed, ReactRuntime
  silently keeps the unminified output.

## [0.4.7]

### Performance

- **Listener churn cut.** `keydown` and `beforeunload` `useEffect`
  hooks used to depend on `answers`, so every keystroke
  re-registered them. Now bound once on mount; live state is read
  through refs synced in a separate effect.
- **Autosave indicator pile-up fixed.** Each keystroke scheduled a
  pending `setSaving(false)` timer that piled up; added a dedicated
  ref so the previous indicator timer is cleared on every save tick.
- **`__pages__` / `__options__` no longer in localStorage.** The
  autosave payload was serialising the entire PAGES tree on every
  save — now `saveToLocalStorage` strips any `__*` keys from the
  answers map before `JSON.stringify`.
- **`transition: all` → explicit property lists.** Three CSS rules
  were animating every property on every state change; replaced with
  named lists (transform/box-shadow/background-color/color).

See `docs/react_preview_performance_audit.md` for the full audit.

## [0.4.6]

### Performance

- **Page transitions feel snappy again.** The fade-in animation
  between pages dropped from 280 ms → 140 ms, and the
  `setTimeout` that clears the CSS class now matches.
- **Removed the smooth scroll-to-top on Next/Prev.** A browser-driven
  smooth scroll can take 300-800 ms; the page already animates in via
  CSS, and combining them gave a perceptible "laggy button" feel.
  Replaced with an instant `window.scrollTo(0, 0)`.
- **Removed the 100 ms `setTimeout` chasing the first input.** The
  CSS animation overlapped with the focus attempt, producing nothing
  visible but extra render churn.

Net effect: clicking *Next section →* now stabilises the new page in
~140 ms instead of ~480-1100 ms, depending on how far the previous
page had been scrolled. There are no public-API changes.

### Note on first-page load

If you see a `[siamang] WARNING: could not compile JSX with
\`npx sucrase\`` line when starting `siamang preview`, the runtime is
shipping raw JSX and the browser is compiling it via
`@babel/standalone` (a ~3 MB CDN dependency). First page load can be
multi-second in that path. To switch to the fast path, install
`sucrase` once: `npm install -g sucrase`.

## [0.4.5]

### Added

- **`UIConfig.allow_back` (default `True`).** A single global switch
  that controls whether respondents can return to earlier pages. When
  set to `False`, the React runtime hides the "Previous" button
  entirely, disables the Escape-key shortcut, ignores
  swipe-right gestures, and prevents the progress-dot navigation
  from jumping backward. Useful for fixed-order surveys where
  changing earlier answers would invalidate later branching.

  ```python
  from siamang.frontend import UIConfig
  survey.deploy(ui=UIConfig(allow_back=False), ...)
  ```

  Forwarded into the React payload as ``window.SURVEY.allowBack``;
  the previously-existing ``SurveySchema.allow_back`` (which the
  React runtime ignored) is now honoured.

## [0.4.4]

### Fixed

- **`examples/demo_survey.py` jumped straight to the exit screen after
  answering the consent question.** Two problems combined:
  1. `q_consent` had `id="q_consent"` set, so the React runtime stored
     the answer under the key `q_consent`, but every subsequent page's
     `show_if=consent.eq(1)` checked `answers["consent"]` (the variable
     name) — which was always undefined. All middle pages stayed
     hidden and `Next` jumped to the only remaining visible page,
     `exit`.
  2. `q_consent` also carried `skip_to="exit"`, which on the SurveyJS
     runtime would skip *every* respondent to the exit page (it does
     not branch by answer value). The React runtime ignores
     `skip_to` entirely, but the field still mislead anyone reading
     the example.
  Dropped the misleading `id=` and `skip_to=` overrides; navigation
  now relies on `show_if` filtering, which is what the React runtime
  actually evaluates. Added a note at the page-definition site so
  future readers know the React runtime does not honour `Page.next_if`
  or `Question.skip_to` (those are SurveyJS-only).

## [0.4.3]

### Changed

- **`pip install siamang` now installs every runtime dependency.**
  Previously a fresh install gave you only `pandas`, and `siamang
  preview` / `siamang deploy` / SPSS / Stata / Excel I/O each
  required a separate `pip install 'siamang[<extra>]'` step.
  All of those are now in the base `dependencies`:
  `fastapi`, `uvicorn`, `openpyxl`, `pyreadstat`, `scipy`, `supabase`,
  `requests`. After `pip install siamang` everything just works.
  The legacy extras (`[server]`, `[excel]`, `[pyreadstat]`,
  `[scipy]`, `[supabase]`, `[vercel]`, `[all]`) are kept as empty
  no-ops so old install commands still succeed.

## [0.4.2]

### Fixed

- **`_compile_jsx_to_js` always failed on sucrase.** The CLI sucrase
  expects a directory, not a file path; the previous code passed a
  single ``.jsx`` and got ``ENOTDIR`` every time, silently falling
  through to the next strategy. Now a temp directory is created, the
  JSX is dropped into it, and ``sucrase --production --out-dir`` is
  invoked correctly. Both compile paths exercised end-to-end.
- **Two compiled scripts collided in the same global scope.**
  ``app.jsx`` and ``questions.jsx`` both declared
  ``const { useState, … } = React;`` at the top, and sucrase emitted
  per-file ``_jsxFileName`` constants — once both files loaded as
  ``<script>`` tags, the duplicates threw
  ``Identifier '…' has already been declared`` and React crashed.
  Both files are now concatenated, the duplicate React destructure is
  removed, and the result is shipped as one ``bundle.js`` (or
  ``bundle.jsx`` in the in-browser Babel fallback). The HTML template
  loads a single script tag.
- **`app.jsx` TDZ regression.** A ``useEffect`` listed
  ``currentPage`` in its dependency array, but ``currentPage`` was
  declared later in the function body. React 18 evaluated the deps
  immediately and threw ``Cannot access 'currentPage' before
  initialization``, leaving the survey blank. Dropped the redundant
  dep (``currentPage = pages[pageIdx]`` is already covered by
  ``pages`` and ``pageIdx``).

## [0.4.1]

### Fixed

- **ReactRuntime: JSX fallback was broken.** When `npx sucrase` /
  `npx @babel/cli` were unavailable or unreachable (Colab kernels,
  sandboxed CI, offline machines), the runtime used to ship raw JSX
  inside `app.js` / `questions.js`. Browsers then refused to parse
  the JSX and the preview rendered as a blank page with
  `Uncaught SyntaxError: Unexpected token '<'`.
  The runtime now ships true `.jsx` files in that case and the
  generated `index.html` loads `@babel/standalone` from a CDN with
  `type="text/babel"` script tags, so the survey renders correctly
  even without a working Node toolchain. A warning is printed to
  stderr so authors know they are on the slower client-side path.

## [Unreleased — library-only branch]

### Added

- **Per-option visibility and media.** New `Option` dataclass attaches
  `show_if`, `hide_if`, and a `Media` payload to individual answer
  choices on `SingleChoice`, `MultiChoice`, and `Ranking`. Pass via
  `choices=[Option(code, label, ...), ...]`; without `choices` the
  legacy `Variable.labels` mapping still works.
- **`hide_if` everywhere.** `Page`, `Block`, `Question`, and `Option`
  all accept `hide_if` alongside `show_if`. An element is visible when
  `show_if` evaluates to true **and** `hide_if` does not.
- **Block-level visibility.** `Block` now carries `show_if` and
  `hide_if`. Compiled pages always preserve block structure (loose
  questions get wrapped in a synthetic untitled block) so per-block
  gates survive even on mixed pages.
- **`Media` attachments.** New `Media(url, kind=None, alt=None,
  caption=None, autoplay=False, loop=False, controls=True)` with
  `kind` ∈ `{image, video, audio}`. Inferred from the URL extension
  when omitted. Attachable to `Question.media` (single or list) and
  to `Option.media`.
- **Validation.** `Questionnaire.validate()` now checks
  `show_if`/`hide_if` on every page, block, question, and option for
  unknown-variable references and unevaluable expressions.

### Removed

- **Studio IDE.** The entire `siamang.studio` subpackage, the
  `siamang studio` CLI subcommand, the `[studio]` optional extras
  (`fastapi`, `uvicorn`, `libcst`, `watchdog`, `websockets`), the
  bundled Vite/Monaco frontend, vendor-asset fetcher, and all
  `tests/studio/` files have been dropped from this branch.
- `vite.config.ts`, `tsconfig.json`, and the Vite-related `npm`
  scripts. `package.json` keeps only the babel pipeline used by
  `siamang.frontend` to compile the survey JSX bundle.
- The release wheel no longer ships any browser editor or vendored
  fonts/Monaco; `python -m build` produces a pure-Python distribution.
- See the `main` branch for the full distribution that includes Studio.

## [0.4.0]

### Added

- **Self-contained Studio bundle.** `pip install siamang[studio]` now
  ships the production Vite bundle, a vendored copy of the Monaco
  editor, and the IBM Plex / Source Serif 4 webfonts inside the wheel.
  `siamang studio` starts without any network access.
- **Studio UI pass — pragmatic UX rewrite.** TopBar, ModeRail, MoreMenu
  consolidated; every previously-dead button now has a real handler
  with toast feedback. New `ui.overlay` and `ui.pendingAddKind` slices
  let any component request a wizard or overlay without prop-drilling.
- **MIT License.** Siamang is now released under the MIT License,
  free for any use — academic, commercial, personal.
- New `scripts/fetch_vendor_assets.py` to populate vendored runtime
  assets from npm tarballs (idempotent, used by the release CI).
- New `.github/workflows/release.yml` — on tag push, builds the wheel,
  verifies the bundled assets, smoke-tests the install in a clean
  venv against every static route, and attaches artifacts to the
  GitHub release. PyPI publishing step is wired but commented out
  until a `PYPI_TOKEN` secret is configured.

### Fixed

- Static file routes in `siamang.studio.app` no longer point at source
  files that don't exist in an installed wheel. New routes:
  `/assets/{path}`, `/vendor/{path}`, `/siamang_logo_{N}.png`. Path
  traversal is rejected.
- Survey sidebar tree items are now real buttons (were unclickable
  `<div>`s); they dispatch `SET_SELECTION` and highlight the active
  node. Same fix to PageCard / BlockCard context-menu "Add Question"
  items (previously no-ops).
- DeployToolbar / DeployChecklist `Deploy` and `Dry Run` buttons now
  do real work and report status via toast.
- `SettingsOverlay` inputs were uncontrolled — settings are now
  persisted to a new `state.settings` slice; the accessibility
  toggles (reduce motion, larger font, persistent focus) drive
  `data-studio-*` attributes on `<html>` so the underlying CSS
  variables actually take effect.
- Typography pass: switched the UI font from IBM Plex Mono to IBM
  Plex Sans, bumped the type scale 1–2 px, plumbed every size through
  `--si-font-scale`, added a global `:focus-visible` rule.
- Pre-existing TypeScript errors in `ShowIfBuilder` and
  `AddQuestionWizard` were fixed along the way; `tsc --noEmit` is
  green.

### Removed

- Internal development scratch directories (`.hermes/`, `dmt_out/`,
  loose `docs/assets/`) from the repository root — they were noise
  for end users and were never meant to ship.

## [0.3.0]

### Added

- **Studio G.3 — design-reference visual port.** The IDE frontend was
  rebuilt to match the designer-authored prototype in `siamang-studio/`:
  - **Light + dark themes** with a topbar toggle, persisted in
    `localStorage`; the light theme is a warm beige + walnut palette.
  - **Drag-resizable panes** (Outline 180–420px, right column
    300–900px) via dedicated `Resizer` handles.
  - **Topbar redesign** — gradient brand mark, folder/file breadcrumb
    with dirty/clean dot indicator, build-state pulse animation,
    overflow ⋯-menu for Save/Validate/Lint/Simulate.
  - **Outline polish** — search-filter input, badges (`*` required,
    `⌘` has-show_if), per-kind colour chips (page=accent,
    variable=warn, question=purple, block=cyan, quota=pink).
  - **Right column tabs** — `Inspector` / `Preview` toggle above a
    fixed-height (200px) Logs panel; Logs gained level-filter buttons
    (ALL / OK / WARN / ERR with counts) and a `lvl`-column.
  - **Real Monaco editor with a derived theme.** `defineStudioMonacoTheme`
    reads `--syn-kw / --syn-string / --syn-num / --syn-comment /
    --syn-builtin` and `--studio-bg / --studio-text / --studio-accent`
    from `:root` at runtime, so theme switches cascade into the
    editor (light → vs base, dark → vs-dark base).
  - **Preview pane** keeps the live `/preview/*` iframe but adds a
    `desktop / tablet / mobile` viewport switcher (720 / 560 / 380px
    max-width) and a "● live" badge on the Preview tab.
  - **Inspector** — sectioned form (Content / Behaviour / show_if)
    with a working show_if visual builder (variable / op / value rows
    + AND/OR conjunction + generated-code preview); resets state when
    a new outline node is selected. ~33 fields auto-save through the
    libcst PatchService (300ms debounce for text/number, immediate for
    toggles/selects) with a per-field pending indicator dot.

- **`siamang studio` — in-process IDE for siamang questionnaires.**
  Run `siamang studio path/to/survey.py [--port 9000] [--open]` to open a
  three-pane web app at `http://127.0.0.1:9000/`:
  - **Outline** — Document AST extracted from the file via `libcst`,
    grouped into Questionnaire / Pages / Blocks / Questions / Variables
    / Quotas, clickable to reveal the source line in Monaco.
  - **Code editor** — Monaco-from-CDN with Python syntax highlighting,
    Ctrl/Cmd-S save, dirty/saved indicator, scroll-into-view on outline
    click.
  - **Preview + Logs** — "Build preview" button mounts the in-memory
    ReactRuntime bundle at `/preview/*` and shows it in an iframe;
    a logs pane streams `validate` / `lint` / `simulate` / `preview`
    output. Frequencies for the top 5 variables are echoed on
    `simulate`.
  - **Live file-watcher** — `watchdog` on the parent directory + a
    `/ws/events` WebSocket; the editor reloads from disk when the file
    changes externally (and warns when local edits would be overwritten).
- New `siamang.studio` subpackage:
  - `siamang.studio.parser` — `libcst → DocumentTree` extractor (24
    tests).
  - `siamang.studio.app:create_app(path)` — FastAPI app with endpoints
    `GET /api/file`, `POST /api/file/save`, `GET /api/document`,
    `POST /api/run/{validate,lint,simulate,preview}`, `WS /ws/events`,
    static `GET /preview/<file>` for the live bundle, and `GET /`,
    `/studio/<asset>` for the IDE frontend.
  - `siamang.studio.actions` — high-level run-actions returning
    JSON-safe results.
  - `siamang.studio.loader.FileLoader` — mtime-keyed `importlib`
    cache for the user's file.
  - `siamang.studio.server.serve(path, host, port, open_browser, block)`
    — uvicorn launcher used by the CLI.
- New `[studio]` extras: `fastapi`, `uvicorn`, `libcst`, `watchdog`,
  `websockets`.
- 38 new tests in `tests/studio/test_app.py` cover every endpoint via
  `fastapi.testclient.TestClient`, plus 24 parser tests from G.1.

End-to-end smoke (manual): `siamang studio examples/digital_media_trust.py
--port 19500` serves the IDE; the demo's 70 siamang nodes (Variable,
NumericInput, SingleChoice, MultiChoice, LikertScale, OpenText, Matrix,
Ranking, MissingValue, Page, Questionnaire) parse cleanly, validate
returns ok, lint returns 7 structured warnings, preview build renders
into `/preview/index.html`.

### Added — Studio H (PatchService)

- **H.1 — PatchService core.** `siamang.studio.patch` subpackage with libcst-based
  transformers enabling round-trip code modification via eight generic operations:
  `SetKwarg`, `UnsetKwarg`, `SetPositional`, `ReplaceNode`, `ReorderListField`,
  `AddListItem`, `RemoveListItem`, `AppendModuleAssign`.
- **H.2 — Patch API endpoint.** `POST /api/patch` accepts a list of patch
  operation JSON objects with an optional staleness guard (`expected_source`),
  applies them via libcst, and returns the updated file content and document
  tree. Returns 409 on concurrent-edit conflicts, 422 on libcst errors.
- **H.3 — show_if round-trip.** Parse `show_if` conditions from Python code into
  an AST, render them as a visual builder (variable / op / value rows + AND/OR
  conjunction), and write back the modified condition via libcst. 14 new tests.
- **H.4 — Per-kind form bindings.** Inspector tab renders different form fields
  depending on the selected node kind (Variable → labels editor, Question →
  text/hint/required, Page → title/show_if). 17 new tests.
- **H.5 — Add/Remove items.** `AddListItem` / `RemoveListItem` /
  `AppendModuleAssign` transformers. AddDialog modal for inserting new
  variables, questions, pages, or blocks at the top-level or into parent
  containers. Context menu with Move up/Move down/Delete actions. 11 new tests.

### Added — Studio I (Analytics)

- **I.1 — Analytics backend.** Cached endpoints: `GET /api/analytics/frequencies`
  (single variable), `GET /api/analytics/crosstab` (two-variable cross-tabulation),
  `GET /api/analytics/banner` (banner table with weighted/unweighted),
  `GET /api/analytics/mean` (mean and standard deviation). 14 tests.
- **I.2 — Analytics UI.** Tabbed panel with Frequencies / Crosstab / Banner views
  integrated into the Studio right column. Table rendering with sortable columns.

### Added — Studio AI Codegen

- **`siamang.studio.ai` subpackage** with `provider.py` (OpenAI, Anthropic, Google,
  DeepSeek, OpenRouter support), `codegen.py` (prompt → Python code generation),
  `critic.py` (self-critique of generated code), `conversation.py` (dialog session
  management), `safety.py` (code safety checks), `schemas.py` (Pydantic models).
  14 tests covering code generation and critique flows.

### Added — Script system

- **`siamang.core.script.Script`** — injectable JavaScript behavior dataclass with
  7 trigger points: `onInit`, `onPageEnter`, `onPageExit`, `onQuestionShow`,
  `onAnswer`, `onSubmit`, `onRandomize`. Supported by both the Python compiler
  (serialised into survey payload) and the React runtime (`ScriptRunner` with
  sandboxed `new Function` execution, built-in `utils` and `api` helpers).

### Added — ReactRuntime enhancements

- **ErrorBoundary** wrapping each question component, catches rendering errors
  without crashing the whole survey. Shows recovery UI with "Reload survey" button.
- **AppErrorBoundary** wrapping the entire `<App>` component as a final safety net.
- **Keyboard navigation:** Enter/Space to advance, Escape to go back, number keys
  (1–9) for Likert scale selection without mouse. `beforeunload` protection when
  answers exist.
- **Touch/swipe navigation** on mobile devices.
- **Theme toggle** with `localStorage` persistence and `prefers-color-scheme` detection.
- **Auto-save to localStorage** with 2-second debounce, restore prompt on return.
- **Access code gate** with configurable codes and error handling.
- **Celebration confetti** on survey completion.
- 17 runtime tests in `tests/frontend/test_react_runtime.py`.

### Added — Vercel deployment

- **`siamang.deploy.frontends.vercel.VercelFrontend`** — publishes survey bundles
  to Vercel via REST API or CLI, with Content-Security-Policy, security headers,
  and cache-control for static assets. 9 tests.
- **`siamang.frontend.bundle.SurveyBundle`** — in-memory file collection with
  `write_to()`, `to_zip()`, and manifest metadata.

### Added — Infrastructure (Batch 9)

- **CI pipeline** — GitHub Actions workflow running tests on Python 3.11/3.12,
  ruff linting and format checking.
- **pre-commit hooks** — ruff format + lint, trailing whitespace, end-of-file fixer,
  YAML validation, large-file guard.
- **Docker support** — `Dockerfile` for portable dev environment, `docker-compose.yml`
  for Studio server.
- **npm build scripts** — `npm run build` compiles JSX→JS via Babel, `npm run clean`
  removes compiled output.
- **Git hygiene** — `.gitignore` covers `node_modules/`, `*.egg-info/`, build
  artifacts, `.env`, and IDE files.

### Added — Production polish (Batch 10)

- **`siamang.__version__`** — reads version from package metadata.
- **Backward-compat shim** — `import survlib` redirects to `siamang`.
- **Supabase pagination** — `get_responses(limit=1000, offset=0)` and
  `get_all_responses(page_size=1000)` for scalable data retrieval.
- **Supabase migration export** — `provision(migration_dir=...)` writes `.sql`
  migration files alongside inline SQL execution.
- **Preload hints** in `index.html.tpl` for CSS, env.js, app.js, questions.js.
- **dmt_out/ cleanup** — stale hash-suffixed compiled bundles removed, canonical
  set preserved.

- **`ReactRuntime` — new default runtime** rendering survey questions
  client-side with React 18 + Babel-standalone from CDN. Ships a full
  ~1200-line design-system stylesheet (extracted from `design/`),
  custom JSX components for every question type (`questions.jsx`), and
  the App state machine in `app.jsx` (page navigation, validation,
  AST-based `show_if` evaluator, submission via `window.SURVLIB_TRANSPORTS`).
  SurveyJS is no longer required for the default deploy path.
- `siamang.frontend.compiler.react.compile_react_payload(survey, ui=…, options=…)`
  produces `{SURVEY, PAGES}` consumed by the React app. Reads live
  `Questionnaire` objects (not the lossy SurveyJS-shaped schema), so
  question-type-specific fields (`display`, `points`, `leftLabel`,
  `multiline`, `maxChars`, matrix columns/rows, ranking max, …) survive
  the compile step.
- `UIConfig` gains `accent_color`, `surface_color`, `muted_text_color`,
  `border_color`, `heading_font_family`, `ui_font_family`,
  `mono_font_family`, `line_height`, `font_pair`, `radius`, `density`,
  `question_style` (`plain` / `divided` / `carded` / `accent`),
  `error_color`, `error_soft_color`, `logo_text`, `estimated_minutes`,
  `study_subtitle`, `institution_name`, `show_section_numbers`,
  `show_progress_text`. `logo_position` also accepts `center`.
- `LocalFrontend` now serves any extra static asset from `bundle.files`
  (e.g. `app.jsx`, `questions.jsx`) with the right content-type — no
  per-runtime web-server changes required.
- `RuntimeAdapter.stylesheet(context)` hook: a runtime can ship its own
  full stylesheet instead of relying on the SurveyJS theme module.
- `FrontendBuilder.build(...)` accepts `survey=` and forwards it through
  `RuntimeRenderContext.survey` so the React runtime can compile the
  payload from the live questionnaire.
- 17 new tests in `tests/frontend/test_react_runtime.py` cover the
  compiler (every question kind, AST-serialised `show_if`,
  block/page structure, UIConfig propagation) and the runtime (bundle
  file set, density/qstyle class injection, stylesheet contents,
  static-asset shipping, manifest fields). Full suite: 193 passed,
  4 skipped.

### Changed

- `Questionnaire.deploy(...)` defaults to `ReactRuntime`. Pass
  `runtime=SurveyJSRuntime()` (via `**options`) to opt back into the
  SurveyJS path.
- `examples/digital_media_trust.py` switched to `ReactRuntime`.

- **Research-grade default theme.** The frontend bundle now ships with a
  calm serif look modelled on academic/PEW-style surveys: narrow measure,
  single-accent palette, generous spacing, focus rings, semantic
  `<header>`/`<main>`/`<footer>` landmarks, "Skip to questionnaire" link,
  numbered progress strip ("Page 2 of 5"), and a research footer with
  institution name, privacy URL, contact email, and ethics statement.
- **Extended `UIConfig`** with `accent_color`, `surface_color`,
  `muted_text_color`, `border_color`, `heading_font_family`,
  `mono_font_family`, `line_height`, `font_pair` (`"serif"`/`"sans"`/`"mixed"`),
  `radius`, `density` (`"compact"`/`"comfortable"`/`"spacious"`),
  `institution_name`, `study_subtitle`, `show_section_numbers`,
  `show_progress_text`, `privacy_url`, `contact_email`,
  `ethics_statement`. `logo_position` now also accepts `"center"`.
- New theme preset **`modern`** (sans-serif, public-facing); the existing
  `dark`, `academic`, `high_contrast` presets were retuned to match the
  new variables.
- 11 new tests for the academic theme + SurveyJS runtime
  (`tests/frontend/test_runtime.py`, expanded `test_theme.py`).

### Changed

- `SURVEYJS_VERSION` pinned to **`2.5.23`** (the previous `1.9.139` did
  not exist on the CDN — `survey-js-ui` only starts at 1.11.x).
- `index.html.tpl` now uses the SurveyJS 2.x renderer
  (`window.SurveyUI.renderSurvey(model, container)`) with fallbacks for
  alternative globals; the old `Survey.SurveyNG.render(...)` call is gone.
- CDN URLs switched from `cdnjs.cloudflare.com` to
  `unpkg.com/survey-core@<v>/...` and
  `unpkg.com/survey-js-ui@<v>/...` (these are the canonical SurveyJS 2.x
  distributions).
- `compile_css` rewritten as a full stylesheet (CSS custom properties +
  SurveyJS class overrides + `.siamang-header`/`.siamang-progress`/
  `.siamang-footer` styling + print-friendly fallbacks).

Full suite: 176 passed, 4 skipped.

## [0.2.0] — 2026-05-11

### Added

- **Modular frontend constructor** (`siamang.frontend`):
  `FrontendBuilder` composes a `SurveyBundle` from four pluggable parts —
  `RuntimeAdapter` (SurveyJS), `UIConfig`/theme, `BackendClientTemplate`
  (Local / Supabase), and the compiled `SurveySchema` IR.
- `Questionnaire.compile(**options) -> SurveySchema` — canonical IR
  consumable by any runtime / hosting target.
- **Real local deploy:** `LocalBackend` (SQLite store with atomic quota
  increment) + `LocalFrontend` (FastAPI + uvicorn served on a free port).
  `Questionnaire.deploy()` now runs the full pipeline and
  `result.collect()` returns a DataFrame.
- **Supabase backend** (`SupabaseBackend`) with PostgREST + service-key
  provisioning; service key never reaches the bundle.
- **Vercel frontend** (`VercelFrontend`) using the v13 deployments REST
  upload.
- **Adapter registry** via `importlib.metadata.entry_points`
  (`siamang.backends`, `siamang.frontends`) with built-in fallbacks.
- **Config layer** (`siamang.config`): `~/.siamang.toml` loader with
  `[defaults]`, `[backends.*]`, `[frontends.*]`, `[profiles.*]`, env
  overrides via `SURVLIB_<ADAPTER>_<KEY>`, 600-perm hardening.
- **CLI** (`siamang`): `init` / `validate` / `preview` / `deploy`.
- `AND` / `OR` / `NOT` helpers on top of the Expression AST.
- 65 new tests in `tests/frontend/`, `tests/deploy/`, `tests/config/`,
  `tests/cli/`. Full suite: **157 passed, 4 skipped**.

### Fixed

- Restored dropped APIs from a previous broken merge:
  `MissingValue`, `ValidationIssue`, `LintWarning`, banner-table /
  metadata-validation / R-export layers were silently removed in 19073d4
  and are now reinstated. The package is importable again.

### Changed

- `Questionnaire.collect()` now points users to the
  `survey.deploy(...).collect()` flow instead of the prior
  "use simulate()" message.
- `BackendConfig` distinguishes `settings` (forwarded to the frontend
  bundle) from `internal` (server-side state).
- `pyproject.toml` declares console_script `siamang`, entry_points for
  backends/frontends, optional extras `[server]`, `[supabase]`,
  `[vercel]`, `py.typed` marker, packaged frontend templates.

## [0.1.0] — 2026-04-XX

Initial baseline: core Variable / Question / Block / Page /
Questionnaire, SurveyData with analysis/processing/tables, CSV / Excel /
R / SPSS / Stata IO, structured missing values, validation.
