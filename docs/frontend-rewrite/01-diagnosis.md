# Frontend rewrite — diagnosis

A reset on why the React preview keeps "feeling laggy" despite seven
incremental patches (0.4.2 → 0.4.9). Six fixes shipped, each
plausible, each verified in headless Chromium — and yet the user
reports the survey is still slow in Colab. That's the signal that the
problem is structural, not a missing optimisation.

This document is the **diagnostic record** for the rewrite branch. It
does **not** contain the new architecture proposal — that lives in
`02-target-architecture.md` once we agree on this analysis.

---

## TL;DR

Four structural problems, ordered by impact:

1. **Bundle is JIT-compiled on every server start**, on the user's
   machine, via `npx`. Should be pre-built once at wheel-build time
   and shipped verbatim. Removes ~50 % of failure modes we've chased.

2. **`App.jsx` is an 870-line monolith** holding navigation, form
   state, submission, theme, access codes, lifecycle scripts,
   keyboard, touch, autosave, and beforeunload in a single React
   component. Every `setState` re-renders the whole tree.

3. **Form answers live in React component state.** Every keystroke
   passes through `setAnswers`, which re-renders the survey page,
   which re-evaluates the visibility AST for every page, which
   re-renders every question. Even with `React.memo` and stable
   callbacks (hacked in for 0.4.8) this fights React, it doesn't
   work with it. Serious form libraries (react-hook-form, tanstack-
   form, modular-forms, formik) put form values in **refs**, not
   state — that's the canonical answer to this exact problem.

4. **Expression evaluator interprets a JSON AST on every render.**
   For visibility (`show_if` / `hide_if`) on pages, blocks,
   questions, and options. Walked recursively, every time, even when
   the relevant answer didn't change. Should be compiled to a
   plain JS function once, with a known dependency list, so it
   only re-evaluates when its inputs change.

The first one is a self-inflicted infrastructure problem and easy to
fix. The other three are React-architecture problems that the
patches we've shipped only worked around.

---

## What I tried (0.4.2 → 0.4.9) and why each one wasn't enough

| Version | What it changed | Why it didn't fully solve "laggy" |
|---------|-----------------|------------------------------------|
| 0.4.2 | Fixed sucrase CLI calling convention (was always failing → JSX shipped as `.js`) | Made the runtime work at all. But the underlying re-compile-every-start design stayed. |
| 0.4.3 | `pip install siamang` pulls every runtime dep | UX win. No perf effect. |
| 0.4.4 | Fixed the example survey's `id="q_consent"` so `show_if` chain worked | Wasn't a perf bug — was a navigation bug. |
| 0.4.5 | Global `UIConfig.allow_back` switch | Feature, not perf. |
| 0.4.6 | Page transition fade 280 ms → 140 ms; killed smooth scroll | Removed one animation pile-up. Real win in the per-Next-click path, ~3-7× on that specific interaction. Did nothing for typing or general render. |
| 0.4.7 (codex) | Listener churn (refs instead of `answers` in `useEffect` deps); autosave shape | Real fixes for two genuine bugs. Still didn't solve "feels laggy". |
| 0.4.8 | `React.memo` on `Question`; uncontrolled OpenText/NumericInput; `requestIdleCallback` autosave; removed `backdrop-filter`; esbuild minify (bundle 67→40 KB) | All real. The uncontrolled-input change in particular drops typing churn from O(N) DOM mutations per keystroke to ~3 *total* for a 2-char fill. Still didn't solve "feels laggy". |
| 0.4.9 | Vendored React UMD locally (no unpkg.com); compile-path diagnostic banner | Removes the Colab-proxy → unpkg.com round-trip on first paint. Still didn't solve it. |

Pattern: every patch was correct, every patch was verified, the bundle
genuinely got smaller, the React re-render count genuinely dropped.
But the user's perception didn't track those numbers. That tells me
my measurements are testing the wrong thing. The real bottleneck is
somewhere I'm not looking.

The structural problems below explain why.

---

## Problem 1 — Bundle is JIT-compiled on every server start

### Current flow

```
siamang preview my_survey.py
    │
    ▼
LocalFrontend.publish(bundle, config)
    │
    ▼
FrontendBuilder.build(schema, ..., survey=survey)
    │
    ▼
ReactRuntime.render_html(context)
    │
    ▼
ReactRuntime._get_or_compile()
    │
    ├─ resources.files(...).read_text("questions.jsx")
    ├─ resources.files(...).read_text("app.jsx")
    ├─ concatenate, strip duplicate `const {...} = React;`
    ├─ subprocess.run(["npx", "--yes", "sucrase", ...])   ← Node call #1
    ├─ subprocess.run(["npx", "--yes", "esbuild", ...])   ← Node call #2
    │
    └─ return bundle.js (cached on the ReactRuntime instance, in-memory)
```

### Why this is structurally wrong

The bundle's content is a **pure function** of:

- `siamang/frontend/templates/react/app.jsx`
- `siamang/frontend/templates/react/questions.jsx`

Both files are shipped inside the wheel. They don't change between
installation and survey runtime. The compiled output is byte-identical
for every survey defined by every user using a given siamang version.

There is no reason to compile this at runtime. We're paying that cost
on every `siamang preview` and on every cold `siamang deploy`, and
inheriting all the failure modes of a Node-based build chain run by a
researcher on whatever machine they happen to be on (Colab kernel,
laptop, container without Node, server with `npx` blocked by network
policy, …).

### What the failure modes have cost

Counting the patches 0.4.2 → 0.4.9 above, **five of seven** were
fixes for problems in this runtime build chain or its fallbacks:

- 0.4.2 — sucrase CLI was being called wrong (`ENOTDIR`); needed to
  pass a directory, not a file; needed `--production`; needed to
  concat the two JSX files because each compile output declared a
  duplicate `_jsxFileName` const.
- 0.4.2 (cont.) — a TDZ in `app.jsx` that nobody noticed because the
  fallback path was being silently exercised.
- 0.4.6 — pre-emptive animation/scroll trimming to mask the slow path.
- 0.4.7 — codex audit, parts of which were workarounds for the JIT-
  compile feedback loop.
- 0.4.8 — esbuild minify added (which only helps if the rest works).
- 0.4.9 — vendored React UMD because the network path to unpkg.com
  was unpredictable; diagnostic banner because users couldn't tell
  which compile path they were on.

None of those engineering hours would have been spent if the bundle
were just a static `.js` file in the wheel.

### Concrete cost on a fresh Colab kernel

For a kernel with no warm npm cache:

1. `siamang preview` runs `npx --yes sucrase` — npm fetches
   `sucrase` from registry. Cold: 5-15 seconds. Network-bound.
2. `npx --yes esbuild` — same, another 5-15 seconds.
3. The pipe between them runs Node twice.
4. If either step fails for any reason — sandboxed proxy, missing
   Node, registry timeout — the runtime silently falls back to
   shipping raw JSX, and the browser pulls 3 MB of
   `@babel/standalone` from a CDN to compile JSX *in the browser*,
   adding 1-3 s to first paint.

For a researcher who just wants to look at their survey, that's
several minutes of "is it broken?" before they even see the welcome
page.

### Fix shape

Move the build to **wheel-build time**:

```
# Once, at `python -m build` time:
npx sucrase ...
npx esbuild --minify ...
→ siamang/frontend/templates/react/dist/bundle.js  (vendored)
```

At runtime:

```
ReactRuntime.static_assets() → reads siamang/.../dist/bundle.js verbatim
```

Node disappears from the runtime path entirely. `sucrase`, `esbuild`,
`@babel/standalone`, `babel.config.js`, `package.json`, the diagnostic
banner, the fallback chain in `_compile_jsx_to_js` — all gone.

Wheel grows by ~40 KB (the compiled, minified bundle). Wheel-build
gains a one-time Node dependency.

### Why we haven't done it yet

Inertia. The original design assumed Node would be available at deploy
time (Vercel deploys always have it; Vercel's own deploy command
needed it for sucrase fallback compilation in the React runtime
template-renderer). When the lib moved to a generic `pip install`
audience, the assumption stopped holding, but the architecture didn't
follow.

---

## Problem 2 — `App.jsx` is an 870-line monolith

### What's inside

`siamang/frontend/templates/react/app.jsx`, **one** React function
component, holds:

| Concern | Hooks | Notes |
|---------|-------|-------|
| Page navigation | `pageIdx`, `transitionDir`, `pages` (`useMemo`) | And derived `currentPage`, `qStart` computed inline on every render |
| Answers | `answers` | Plus `extractOptions(allPages)` shoved into `answers.__options__` as a side channel |
| Submission state machine | `phase`, `submitting`, `submitId`, `submittedAt`, `submitAttempts`, `savedData`, `saving` | Seven `useState`s. Some interact. |
| Errors / touched | `errors`, `touched` | |
| Theme | `theme` + `useEffect` to write `data-theme` attribute | |
| Access-code gate | `accessGranted`, `accessCode`, `accessError` | |
| Refs for refs | `saveTimerRef`, `savingIndicatorTimerRef`, `touchStartX`, `answersRef`, `phaseRef`, `submittingRef`, `pageIdxRef`, `pagesRef`, `errorsRef`, `uiTextsRef` | We added most of these in 0.4.8 specifically to break re-render loops. They're a symptom. |
| Effects | onInit / onAnswer / onSubmit scripts orchestration; keyboard handler; beforeunload; theme attribute sync; autosave; ref-sync effect | Seven `useEffect`s |
| Methods | `setAnswer`, `handleBlur`, `handleNext`, `handlePrev`, `handleTouchStart`, `handleTouchEnd`, `submit`, `verifyAccess`, `saveToLocalStorage`, `doSaveToLocalStorage` | All defined inline inside `App()`. |
| JSX | Header / Footer / SurveyPage / CompletedScreen / ClosedScreen / AppErrorBoundary delegation, plus inline access-gate, retry overlay, loading overlay, resume banner, progress, step dots, saving indicator, theme toggle, accessibility live region | 200+ lines of JSX at the bottom |

### Why it's a problem

- A `setState` from any one concern triggers re-render of the whole
  function — so a "Saving…" indicator update at the 2-second autosave
  mark re-runs every `useMemo`, recomputes every derived value, and
  potentially renders every question.
- Adding a new feature means another `useState`, another
  `useEffect`, more deps to wire correctly. The component is
  already past where one human can hold all of it in their head.
- Cross-concern bugs are subtle: e.g. the TDZ for `currentPage` we
  fixed in 0.4.2 only existed because `currentPage` was computed
  late in `App()` but referenced earlier in a `useEffect` dep
  array. A modular design wouldn't permit that.
- Refactor risk is high: every change touches the same file. There
  is no way to fix the navigation logic without also seeing every
  unrelated state slice.

### Fix shape

Decompose into focused hooks and child components:

```
App (orchestrator, ~80-100 lines)
├── <AccessGate> | <Survey>
├── <Survey>
│   ├── useSurveyNav(pages, answersStore)         — pageIdx, next/prev, currentPage
│   ├── useSubmission(transport)                  — state machine; idle → submitting → completed
│   ├── useAutosave(answersStore, surveyId)       — own its timers
│   ├── useLifecycleScripts(scripts)              — own its triggers
│   ├── useKeyboardShortcuts(navHandle)           — own its event listener
│   ├── useTouchGestures(navHandle)               — own its handlers
│   ├── useTheme()                                — own its localStorage + attr sync
│   ├── <Header />
│   ├── <Progress nav={nav} />
│   ├── <SurveyPage page={currentPage} answersStore={…} />
│   ├── <Footer />
│   ├── <CompletedScreen if phase === "completed" />
│   ├── <ClosedScreen if phase === "closed" />
│   └── <RetryOverlay if attempts > 0 />
```

Each hook has its own state, its own effects, its own contract. Each
component renders independently. The orchestrator just composes.

This is a **lot** of moving code, but each piece is small. With the
answers store from Problem 3 below, the cross-concern coupling that
forces re-renders disappears.

---

## Problem 3 — Form state lives in `useState`, not in a store

### Current shape

```js
const [answers, setAnswers] = useState({});

const setAnswer = (id, val) => {
  setAnswers(prev => ({ ...prev, [id]: val }));
};
```

Every input passes through `setAnswer`. Every `setAnswer`:

- creates a new `answers` object (referential change);
- triggers React re-render of `App`;
- re-runs `useMemo(() => visiblePages(allPages, answers), [allPages, answers])`,
  which recursively evaluates `show_if`/`hide_if` for **every page**;
- re-runs every other `useEffect` and `useMemo` that lists `answers`
  in its deps (we removed several of those in 0.4.7, but
  `visiblePages` and `qStart` still depend on it);
- re-renders `SurveyPage`, which iterates the items array and calls
  `renderItem` per question, which calls `isVisibleGated` for each
  question and creates a new `onChange`/`onBlur` closure per
  question (we partially fixed this in 0.4.8 by making the
  dispatcher build the closures internally with a stable
  `setAnswer`, but only for the dispatcher level).

The cost is amortised across the page's questions. With 20 questions,
each keystroke runs ~20 visibility checks plus ~20 `Question` props
diffs (memo bail-outs).

In other words: **the form library and the UI library are the same
library**. React-the-UI-library is doing form-state work it wasn't
designed for.

### What proper form libraries do

react-hook-form, tanstack-form, modular-forms, formik (in
"uncontrolled" mode), final-form:

- Form values live in a non-React store — usually a ref to a plain
  object, or a subscribable signal-like store.
- Inputs are **uncontrolled** (`defaultValue` + `ref`) by default.
- React only sees a value when something needs it — validation on
  submit, a derived flag for the current step, etc.
- Subscriptions are fine-grained: a component can subscribe to
  `form.values.age` and re-render only when that field changes.
- For visibility (`show_if`), a derived computed signal pulls from
  the store and updates only when its inputs change.

The 0.4.8 uncontrolled-input change for OpenText/NumericInput is a
patch in this direction, but only for two question types. The right
thing is for **all** question types to participate in this pattern.

### Fix shape

A small custom store (~50-80 lines of plain JS, no dependency
needed — we don't want a `zustand` peer dep). API:

```js
const store = createAnswersStore(initial);
store.get(id)            // synchronous read
store.set(id, value)     // updates, notifies subscribers
store.subscribe(ids, cb) // subscribe to specific field ids
store.snapshot()         // full copy, for autosave / submit
```

Or even simpler: a `useSyncExternalStore`-based React adapter. With
that, a question component renders only when its own field changes,
not when any field changes.

For `show_if`/`hide_if`, see Problem 4 — they compile to functions
with explicit dependency lists, which become the subscription keys.

### Side effect: uncontrolled inputs everywhere

With the store, every input becomes "DOM owns the value, store owns
the truth, React owns the layout". Re-renders happen only when
something the layout depends on changes — visibility flipped, error
appeared, page advanced. Typing in a text field never crosses a React
re-render boundary.

This is the change that actually solves "the form feels laggy when I
type", because the cost stops scaling with `questions on the page`.

---

## Problem 4 — Visibility expressions are interpreted, not compiled

### Current shape

`compile_react_payload` serialises every `Expression` as JSON:

```json
{
  "showIf": {
    "type": "expression",
    "op": "and",
    "left": { "type": "expression", "op": ">=", "left": { "type": "var", "name": "age" }, "right": 18 },
    "right": { "type": "expression", "op": "=",  "left": { "type": "var", "name": "consent" }, "right": 1 }
  }
}
```

In the browser, `evalNode` walks that tree recursively on every
visibility check:

```js
function evalNode(node, answers) {
  if (node.type === "var") return answers[node.name];
  if (node.type === "expression") {
    if (node.op === "and") return evalNode(node.left, answers) && evalNode(node.right, answers);
    // ...
  }
}
```

For a page with 5 conditional questions, each with a 3-deep AST,
each `visiblePages(allPages, answers)` call evaluates ~15 JSON-tree
walks. The deps array passes `answers` (a fat object reference) and
triggers re-evaluation every time *anything* in answers changes,
even fields the expressions don't reference.

### Fix shape

At payload-compile time (Python side, in `compile_react_payload`),
emit:

```json
{
  "showIf": {
    "deps": ["age", "consent"],
    "fn":   "a.age >= 18 && a.consent === 1"
  }
}
```

(or equivalent — generate a safe JS-expression string, validated
syntactically on the Python side. Already restricted vocabulary: just
the operators we know about. SurveyJS-string fallback stays as
opaque-truthy.)

In the browser:

```js
// Once at load time:
const isVisible_q42 = new Function("a", "return " + node.fn);
// At render time:
isVisible_q42(answersStore.snapshot());
```

`new Function(...)` is one-time cost. Per-render is a plain function
call. The `deps` array tells the store which fields to subscribe to.

This complements Problem 3: with the store, a question
`subscribe(deps_of_showIf, recheck_visibility)`. Visibility checks
become event-driven, not poll-on-render.

Security note: the expression strings are author-controlled (Python
source the researcher wrote, not respondent input), so `new Function`
is safe. No respondent value ever lands inside the function body.

---

## Out-of-scope but worth naming

Things that bug me but don't drive perception of "lag":

- **CSS is a 1849-line Python `string.Template` string** with `${var}`
  substitutions for every UIConfig field. Should be a static
  stylesheet with CSS custom properties set via a tiny `:root`
  block. Easier to audit, easier to override, much easier to test.
- **No CI for the React side.** Compile checks happen only when the
  preview server starts. No type checking, no lint, no test runner
  for the JSX. We should add at least a `npm run check` step (tsc
  --noEmit + eslint) once we have a real build.
- **The `Script` (lifecycle JS) sandbox is `new Function(...)`** with
  no isolation. For an in-process preview that's fine; for an
  unattended Vercel deploy serving respondents, that's a real
  concern. Probably needs a sandbox-iframe or a constrained
  scripting interpreter for production.
- **`Page.next_if` / `Question.skip_to`** are documented but the
  React runtime silently ignores them (only SurveyJS path honours
  them). We should either implement them in React or remove them
  from the model.

These are real but each is its own follow-up. Don't lump them into
this rewrite.

---

## What I recommend

**Phase 1 — Pre-built bundle (lowest risk, biggest infrastructure
win).** ✅ **Done in 0.5.0.**

Compiled `bundle.js` once at wheel-build time, ship it. Deleted
`_compile_jsx_to_js`, deleted `_combined_jsx`, deleted the diagnostic
banner, deleted the `@babel/standalone` fallback path, deleted the
`sucrase` and `esbuild` lookups. `babel.config.js` and `package.json`
are kept at repo root for the build script and the `siamang.frontend`
JSX templating that the *survey runtime* (separate from this React
preview runtime) uses at deploy time.

Build flow now:

    # one-time per repo, by maintainers, after editing
    # questions.jsx / app.jsx
    python scripts/build_react_bundle.py        # → dist/bundle.js (~42 KB)
    python scripts/build_react_bundle.py --check # CI-friendly drift check

The runtime React path at survey-render time is now pure I/O —
ReactRuntime reads `dist/bundle.js` from package data. No subprocess,
no network, no fallback.

Problem 1 is gone. Bonus: a partial Problem 4 mitigation also
landed — per-expression memoisation + a `visibilitySignature`
useMemo dependency so the pages list only recomputes when an answer
referenced by some `show_if` / `hide_if` changes. Typing into an
unrelated free-text field no longer bumps it.

What remains for the rewrite branch: Phase 2 (decompose App,
answers store) and Phase 3 proper (compile expressions to functions,
not just memoise their interpreter).

**Phase 2 — Answers store + decompose `App`.**

Build the small store (50-80 lines). Migrate `setAnswer`/`handleBlur`
to use it. Replace `useState({})` for answers with the store. Move
each concern into its own hook. Each migration is independent and
testable.

After this, Problems 2 and 3 are gone. The form stops fighting React.

**Phase 3 — Expression compiler.**

Emit JS strings instead of JSON AST. Subscribe `show_if` evaluators
to store fields by dependency. Validate that the existing
`AND/OR/NOT/in/notin/eq/ge/...` set maps cleanly to safe JS operators.

After this, Problem 4 is gone. Visibility becomes O(1) per change
instead of O(pages × depth × answer-tree-size).

Phases are independent: shipping Phase 1 alone gives the user a
runtime-Node-free wheel. Phase 2 then a noticeable form-typing
improvement. Phase 3 a smaller but real win on large surveys.

Each phase is a separate PR on this branch.

---

## What's NOT in this rewrite

- No new question types
- No new visibility semantics
- No new theming API
- No SurveyJS removal (it's a separate runtime path; users on
  SurveyJS still get SurveyJS)
- No backend changes
- No deploy changes
- No new Python API on `Questionnaire`

The Python-side public API stays identical. A questionnaire authored
on `minimal` v0.4.9 must render identically on the rewrite branch.
The only observable difference for end-users should be: it's faster.
