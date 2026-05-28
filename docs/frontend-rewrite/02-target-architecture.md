# Target Architecture: React Runtime v2 (Phase 2 & 3)

This document outlines the target architecture implemented in the `frontend-rewrite` branch. It addresses the four structural problems identified in `01-diagnosis.md` by introducing a reactive answers store, compiled visibility conditions, modular hooks, and a flexible theming system.

---

## 1. Architectural Blueprint

The v2 React runtime decouples form state from the React render cycle and compiles expression DSLs into raw JavaScript functions at survey load time.

```
+─────────────────────────────────────────────────────────────────────────+
│                            React Runtime v2                             │
+─────────────────────────────────────────────────────────────────────────+
                                     │
      ┌──────────────────────────────┴──────────────────────────────┐
      ▼                                                             ▼
+───────────+                                                 +───────────+
│   Form    │                                                 │Visibility │
│  Answers  │                                                 │  Engine   │
│   Store   │                                                 │ (Compiled)│
+───────────+                                                 +───────────+
      │                                                             │
      ├─────────────────────── useFieldValue(id)                    │
      ▼                                                             ▼
+───────────+                                                 +───────────+
│ Question  │◄────────────────────────────────────────────────┤   App /   │
│ Component │                                                 │SurveyPage │
+───────────+                                                 +───────────+
```

---

## 2. Core Components

### 2.1. Answers Store (`store.jsx`)

Form values are stored in a lightweight, reactive external store instead of React component state. Question components subscribe only to their respective field values.

* **Reactive State:** Uses `useSyncExternalStore` to let React subscribe to external data sources safely and efficiently.
* **Granular Subscriptions:** `subscribeField(id, cb)` notifies only the specific component when its answer changes.
* **Performance Impact:** Typing into a text input or selecting an option only re-renders that single question component. The rest of the page remains untouched.

### 2.2. Compiled Visibility Engine (`visibility.jsx`)

Instead of recursively walking a JSON AST on every render, visibility conditions are compiled into optimized JavaScript functions.

* **Python Compiler Support (`compiler/react.py`):** The compiler translates `Expression` trees into clean JavaScript expressions and extracts explicit dependency lists (`deps`).
* **JIT Compilation:** At survey load time, the browser runtime compiles the JS strings into functions using `new Function("a", "return " + fn)`.
* **Fine-Grained Subscriptions:** The visibility engine subscribes to the store using only the variables listed in `deps`. If an unrelated answer changes, the visibility condition is not re-evaluated.

### 2.3. Modular Hooks (`hooks.jsx`)

The monolithic `App.jsx` has been refactored into a thin orchestrator. All non-UI concerns are extracted into modular hooks:

* `useTheme(defaultTheme)` — Manages light/dark/system theme state and local storage persistence.
* `useAutosave(store, surveyId, pageIdxRef)` — Handles periodic saving of progress to `localStorage` using `requestIdleCallback` to prevent UI thread blocking.
* `useSurveyNav(allPages, store, visibilityEngine)` — Manages active page navigation, filters visible pages dynamically, and calculates progress.
* `useSubmission(store, clearSaved)` — Manages survey submission, retry logic (up to 3 attempts), and local backup recovery on failure.
* `useKeyboardShortcuts` — Handles global shortcuts (Enter for Next, Escape for Back, numbers 1-9 for Likert scales).
* `useTouchGestures` — Enables swipe-to-navigate gestures on mobile devices.

---

## 3. Theming & Font Presets

The v2 runtime introduces a flexible, non-intrusive theming system based on **CSS Custom Properties** and pre-configured **Font Presets**.

### 3.1. Font Presets

Three high-quality typography presets are available via `UIConfig`:

| Preset Name | Body Font | Heading Font | UI Font | Google Fonts URL |
| :--- | :--- | :--- | :--- | :--- |
| **`academic`** | Source Serif 4 | Source Serif 4 | Inter | Source Serif 4 & Inter |
| **`modern`** | Inter | Inter | Inter | Inter |
| **`humanist`** | Nunito | Nunito | Nunito | Nunito |

### 3.2. Configuration API (`ui_config.py`)

The `UIConfig` dataclass has been extended with the `font_preset` field and helper properties:

* `font_preset: str = "academic"` — Selects one of the typography presets.
* `effective_body_font` — Resolves the body font family (respects custom overrides if set).
* `effective_ui_font` — Resolves the UI font family.
* `effective_google_fonts_url` — Resolves the corresponding Google Fonts stylesheet URL.

### 3.3. Integration

* **HTML Template (`index.html.tpl`):** Dynamically injects `${google_fonts_url}` to fetch only the required fonts from the Google Fonts CDN.
* **React Runtime (`react.py`):** Passes the resolved fonts to the `stylesheet()` generator to bind them to `--siamang-font` and `--siamang-ui-font` CSS variables.
