/* siamang runtime theme — mirrors siamang/frontend/theme/css.py contract.
   :root tokens are the stable design surface; restyle anything by overriding them. */

:root {
  /* Palette */
  --siamang-primary: ${primary};
  --siamang-accent: ${accent};
  --siamang-bg: ${bg};
  --siamang-surface: ${surface};
  --siamang-text: ${text};
  --siamang-muted: ${muted};
  --siamang-border: ${border};

  /* Typography */
  --siamang-font: ${font};
  --siamang-heading-font: ${heading_font};
  --siamang-ui-font: ${ui_font};
  --siamang-mono: ${mono};
  --siamang-font-size: ${font_size};
  --siamang-line-height: ${line_height};

  /* Layout */
  --siamang-width: ${width};
  --siamang-radius: ${radius};

  /* Density — defaults match the "comfortable" preset; root-class modifies */
  --siamang-section-gap: 28px;
  --siamang-item-gap: 14px;
  --siamang-control-pad: 12px;
  --siamang-page-pad: 36px;

  /* Computed */
  --siamang-focus-ring: 0 0 0 3px color-mix(in srgb, var(--siamang-accent) 32%, transparent);
  --siamang-error: ${error};
  --siamang-error-soft: ${error_soft};
  --siamang-warn: #9a6a1a;
}

/* Density modifiers */
:root.density-compact {
  --siamang-section-gap: 18px;
  --siamang-item-gap: 10px;
  --siamang-control-pad: 8px;
  --siamang-page-pad: 24px;
}
:root.density-spacious {
  --siamang-section-gap: 40px;
  --siamang-item-gap: 18px;
  --siamang-control-pad: 16px;
  --siamang-page-pad: 48px;
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --siamang-bg: #10131a;
    --siamang-surface: #171b24;
    --siamang-text: #e7e9ee;
    --siamang-muted: #9aa1ad;
    --siamang-border: #262b36;
    --siamang-error-soft: #2d1a1a;
  }
}

/* Manual toggle override */
:root[data-theme="dark"] {
  --siamang-bg: #10131a;
  --siamang-surface: #171b24;
  --siamang-text: #e7e9ee;
  --siamang-muted: #9aa1ad;
  --siamang-border: #262b36;
  --siamang-error-soft: #2d1a1a;
}
:root[data-theme="light"] {
  /* No overrides needed — :root values already are light */
}

/* ─── Base ─────────────────────────────────────────────────────────────── */

* { box-sizing: border-box; }

html, body {
  margin: 0;
  padding: 0;
  background: var(--siamang-bg);
  color: var(--siamang-text);
  font-family: var(--siamang-font);
  font-size: var(--siamang-font-size);
  line-height: var(--siamang-line-height);
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}

body { min-height: 100vh; }

:focus-visible {
  outline: none;
  box-shadow: var(--siamang-focus-ring);
  border-radius: 3px;
}

/* Skip link */
.siamang-skip-link {
  position: absolute;
  left: 12px;
  top: -40px;
  background: var(--siamang-accent);
  color: #fff;
  padding: 8px 14px;
  border-radius: var(--siamang-radius);
  font-family: var(--siamang-ui-font);
  font-size: 14px;
  text-decoration: none;
  z-index: 100;
  transition: top 120ms ease;
}
.siamang-skip-link:focus { top: 12px; }

/* ─── Page shell ───────────────────────────────────────────────────────── */

#survey {
  max-width: var(--siamang-width);
  margin: 0 auto;
  padding: var(--siamang-page-pad) 24px 96px;
  position: relative;
}

/* ─── Header ───────────────────────────────────────────────────────────── */

.siamang-header {
  display: flex;
  align-items: flex-start;
  gap: 20px;
  padding-bottom: 24px;
  border-bottom: 1px solid var(--siamang-border);
  margin-bottom: 28px;
}
.siamang-header.right { flex-direction: row-reverse; text-align: right; }
.siamang-header.right .siamang-header__text { text-align: right; }
.siamang-header.center {
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.siamang-header__logo {
  width: 56px;
  height: 56px;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  border: 1px solid var(--siamang-border);
  border-radius: var(--siamang-radius);
  background: var(--siamang-surface);
  font-family: var(--siamang-ui-font);
  font-weight: 600;
  font-size: 13px;
  color: var(--siamang-muted);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.siamang-header__text { flex: 1; min-width: 0; }

.siamang-header__title {
  font-family: var(--siamang-heading-font);
  font-size: 1.55rem;
  line-height: 1.2;
  font-weight: 600;
  margin: 2px 0 4px;
  letter-spacing: -0.01em;
  color: var(--siamang-text);
}

.siamang-header__institution {
  margin: 0;
  font-family: var(--siamang-ui-font);
  font-size: 0.82rem;
  font-weight: 500;
  color: var(--siamang-muted);
  letter-spacing: 0.02em;
}

.siamang-header__subtitle {
  margin: 8px 0 0;
  font-style: italic;
  font-size: 0.96rem;
  color: var(--siamang-muted);
  max-width: 56ch;
}

/* Minibar — compact title row when the full institutional header is off */
.siamang-minibar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 0 14px;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--siamang-border);
}
.siamang-minibar__title {
  font-family: var(--siamang-ui-font);
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--siamang-muted);
  letter-spacing: 0.02em;
}

/* ─── Progress strip ──────────────────────────────────────────────────── */

.siamang-progress {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 28px;
  font-family: var(--siamang-ui-font);
}

.siamang-progress__bar {
  flex: 1;
  height: 4px;
  background: color-mix(in srgb, var(--siamang-border) 70%, transparent);
  border-radius: 999px;
  overflow: hidden;
  position: relative;
}

.siamang-progress__fill {
  display: block;
  height: 100%;
  width: 0%;
  background: var(--siamang-accent);
  transition: width 280ms cubic-bezier(.4,.0,.2,1);
  border-radius: 999px;
}

.siamang-progress__text {
  font-size: 0.78rem;
  color: var(--siamang-muted);
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  font-weight: 500;
  white-space: nowrap;
}

/* Section eyebrow above page title */
.sd-page__eyebrow {
  font-family: var(--siamang-ui-font);
  font-size: 0.74rem;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--siamang-muted);
  margin-bottom: 6px;
}

/* ─── Page card (SurveyJS .sd-page) ────────────────────────────────────── */

.sd-page {
  background: var(--siamang-surface);
  border: 1px solid var(--siamang-border);
  border-radius: var(--siamang-radius);
  padding: var(--siamang-section-gap);
  position: relative;
}

.sd-page + .sd-page { margin-top: 28px; }

.sd-page__title {
  font-family: var(--siamang-heading-font);
  font-size: 1.28rem;
  font-weight: 600;
  line-height: 1.25;
  margin: 0 0 6px;
  letter-spacing: -0.005em;
}

.sd-page__description {
  font-family: var(--siamang-font);
  font-style: italic;
  color: var(--siamang-muted);
  margin: 0 0 var(--siamang-section-gap);
  max-width: 56ch;
}

.sd-page__title + .sd-page__description { margin-top: 4px; }
.sd-page__title:not(:has(+ .sd-page__description)),
.sd-page__title + .sd-question { margin-bottom: 0; }

.sd-block {
  margin-top: calc(var(--siamang-section-gap) - 4px);
  padding-top: calc(var(--siamang-section-gap) - 4px);
  border-top: 1px solid color-mix(in srgb, var(--siamang-border) 70%, transparent);
}
.sd-block:first-of-type { margin-top: var(--siamang-section-gap); padding-top: 0; border-top: none; }
.sd-block__title {
  font-family: var(--siamang-ui-font);
  font-size: 0.78rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--siamang-muted);
  margin: 0 0 var(--siamang-item-gap);
}

/* ─── Question ─────────────────────────────────────────────────────────── */

.sd-question {
  margin-top: var(--siamang-section-gap);
}
.sd-question:first-child,
.sd-block .sd-question:first-of-type { margin-top: 0; }
.sd-question + .sd-question { margin-top: var(--siamang-section-gap); }

/* ─── Question style variants (Tweak) ─────────────────────────────── */

/* "divided" — hairline rule between consecutive questions */
.qstyle-divided .sd-question + .sd-question {
  border-top: 1px solid color-mix(in srgb, var(--siamang-border) 70%, transparent);
  padding-top: var(--siamang-section-gap);
}
.qstyle-divided .sd-block + .sd-block { border-top: none; }

/* "carded" — page becomes the outer card; blocks are nested cards;
   questions are inner cards. Three levels of containment. */
.qstyle-carded .sd-page {
  background: color-mix(in srgb, var(--siamang-bg) 50%, var(--siamang-border) 50%);
  padding: calc(var(--siamang-section-gap) * 0.85);
}
.qstyle-carded .sd-block {
  border-top: none;
  padding: calc(var(--siamang-section-gap) * 0.85);
  margin-top: var(--siamang-item-gap);
  background: color-mix(in srgb, var(--siamang-bg) 92%, var(--siamang-border) 8%);
  border: 1px solid var(--siamang-border);
  border-radius: var(--siamang-radius);
}
.qstyle-carded .sd-block:first-of-type { margin-top: var(--siamang-section-gap); }
.qstyle-carded .sd-block__title { padding: 0; margin-bottom: var(--siamang-item-gap); }
.qstyle-carded .sd-question {
  background: var(--siamang-surface);
  border: 1px solid var(--siamang-border);
  border-radius: var(--siamang-radius);
  padding: calc(var(--siamang-section-gap) * 0.7) calc(var(--siamang-section-gap) * 0.85);
  margin-top: 10px;
  box-shadow: 0 1px 2px rgba(15, 20, 25, 0.025);
}
.qstyle-carded .sd-question + .sd-question { margin-top: 10px; }
.qstyle-carded .sd-block .sd-question:first-of-type { margin-top: 0; }
/* For pages without blocks, questions sit directly in the page card */
.qstyle-carded .sd-page > .sd-question:first-of-type { margin-top: var(--siamang-section-gap); }

/* "accent" — left rail in accent color */
.qstyle-accent .sd-question {
  padding-left: 18px;
  border-left: 2px solid color-mix(in srgb, var(--siamang-accent) 30%, var(--siamang-border));
  transition: border-color 100ms ease;
}
.qstyle-accent .sd-question:hover,
.qstyle-accent .sd-question:focus-within {
  border-left-color: var(--siamang-accent);
}
.qstyle-accent .sd-question.has-error { border-left-color: var(--siamang-error); }

.sd-question__header { margin-bottom: var(--siamang-item-gap); }

.sd-question__title {
  font-family: var(--siamang-heading-font);
  font-size: 1.04rem;
  font-weight: 600;
  line-height: 1.4;
  margin: 0;
  color: var(--siamang-text);
  display: block;
}
.sd-question__title > .sd-question__num {
  margin-right: 10px;
}

.sd-question__num {
  font-family: var(--siamang-ui-font);
  font-size: 0.78rem;
  font-weight: 500;
  color: var(--siamang-muted);
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
  letter-spacing: 0.04em;
}

.sd-question__required-text {
  color: var(--siamang-accent);
  margin-left: 2px;
  font-weight: 500;
}

.sd-question__description {
  font-family: var(--siamang-font);
  font-size: 0.93rem;
  font-style: italic;
  color: var(--siamang-muted);
  margin: 6px 0 0;
  max-width: 60ch;
}

/* Error state */
.sd-question.has-error .sd-input,
.sd-question.has-error .sd-radio__decorator,
.sd-question.has-error .sd-checkbox__decorator,
.sd-question.has-error .sd-rating__item,
.sd-question.has-error .sd-dropdown {
  border-color: var(--siamang-error);
}
.sd-question__error {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  padding: 8px 12px;
  background: var(--siamang-error-soft);
  border-left: 2px solid var(--siamang-error);
  color: var(--siamang-error);
  font-family: var(--siamang-ui-font);
  font-size: 0.85rem;
  border-radius: 2px;
}
.sd-question__error::before {
  content: "!";
  display: inline-grid;
  place-items: center;
  width: 16px; height: 16px;
  border-radius: 50%;
  background: var(--siamang-error);
  color: #fff;
  font-weight: 700;
  font-size: 11px;
  flex-shrink: 0;
}

/* ─── Inputs ───────────────────────────────────────────────────────────── */

.sd-input {
  width: 100%;
  padding: var(--siamang-control-pad) 14px;
  background: var(--siamang-surface);
  border: 1px solid var(--siamang-border);
  border-radius: var(--siamang-radius);
  font-family: var(--siamang-font);
  font-size: 1rem;
  color: var(--siamang-text);
  transition: border-color 100ms ease, box-shadow 100ms ease;
}
.sd-input:hover { border-color: color-mix(in srgb, var(--siamang-text) 30%, var(--siamang-border)); }
.sd-input:focus-visible { border-color: var(--siamang-accent); }
.sd-input::placeholder { color: color-mix(in srgb, var(--siamang-muted) 70%, transparent); }

textarea.sd-input { min-height: 96px; resize: vertical; line-height: 1.55; }

.sd-numeric {
  display: flex;
  align-items: center;
  gap: 10px;
  max-width: 280px;
}
.sd-numeric .sd-input { flex: 1; min-width: 0; }
.sd-numeric__unit {
  font-family: var(--siamang-ui-font);
  font-size: 0.85rem;
  color: var(--siamang-muted);
}

.sd-char-counter {
  font-family: var(--siamang-ui-font);
  font-size: 0.78rem;
  color: var(--siamang-muted);
  text-align: right;
  margin-top: 4px;
  font-variant-numeric: tabular-nums;
}

/* Dropdown */
.sd-dropdown {
  position: relative;
  max-width: 360px;
}
.sd-dropdown select.sd-input {
  appearance: none;
  -webkit-appearance: none;
  padding-right: 36px;
  cursor: pointer;
}
.sd-dropdown::after {
  content: "";
  position: absolute;
  right: 14px;
  top: 50%;
  width: 8px;
  height: 8px;
  border-right: 1.5px solid var(--siamang-muted);
  border-bottom: 1.5px solid var(--siamang-muted);
  transform: translateY(-65%) rotate(45deg);
  pointer-events: none;
}

/* ─── Radio / Single choice ────────────────────────────────────────────── */

.sd-choices { display: flex; flex-direction: column; gap: 2px; }

.sd-radio, .sd-checkbox {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 10px 12px;
  cursor: pointer;
  border-radius: var(--siamang-radius);
  transition: background-color 80ms ease;
  font-size: 1rem;
  line-height: 1.45;
}
.sd-radio:hover, .sd-checkbox:hover {
  background: color-mix(in srgb, var(--siamang-accent) 6%, transparent);
}

.sd-radio__decorator, .sd-checkbox__decorator {
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  border: 1.5px solid color-mix(in srgb, var(--siamang-muted) 60%, var(--siamang-border));
  background: var(--siamang-surface);
  margin-top: 3px;
  display: grid;
  place-items: center;
  transition: border-color 80ms, background-color 80ms;
}
.sd-radio__decorator { border-radius: 50%; }
.sd-checkbox__decorator { border-radius: 3px; }

.sd-item--checked .sd-radio__decorator,
.sd-item--checked .sd-checkbox__decorator {
  border-color: var(--siamang-accent);
}
.sd-item--checked .sd-radio__decorator::after {
  content: "";
  width: 9px; height: 9px;
  border-radius: 50%;
  background: var(--siamang-accent);
}
.sd-item--checked .sd-checkbox__decorator {
  background: var(--siamang-accent);
}
.sd-item--checked .sd-checkbox__decorator::after {
  content: "";
  width: 10px; height: 6px;
  border-left: 2px solid #fff;
  border-bottom: 2px solid #fff;
  transform: rotate(-45deg) translate(1px, -1px);
}

.sd-radio input, .sd-checkbox input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.sd-choice-label { flex: 1; min-width: 0; }

/* Buttons-style single choice */
.sd-choices--buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.sd-choices--buttons .sd-radio {
  border: 1px solid var(--siamang-border);
  padding: 10px 16px;
  background: var(--siamang-surface);
  font-family: var(--siamang-ui-font);
  font-size: 0.92rem;
}
.sd-choices--buttons .sd-radio:hover { background: color-mix(in srgb, var(--siamang-accent) 5%, var(--siamang-surface)); }
.sd-choices--buttons .sd-radio__decorator { display: none; }
.sd-choices--buttons .sd-item--checked {
  background: color-mix(in srgb, var(--siamang-accent) 10%, var(--siamang-surface));
  border-color: var(--siamang-accent);
  color: var(--siamang-accent);
  font-weight: 600;
}

/* ─── Likert / Rating ──────────────────────────────────────────────────── */

.sd-rating {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sd-rating__scale {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.sd-rating__item {
  flex: 1 1 0;
  min-width: 44px;
  min-height: 44px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  padding: 10px 8px;
  background: var(--siamang-surface);
  border: 1px solid var(--siamang-border);
  border-radius: var(--siamang-radius);
  cursor: pointer;
  font-family: var(--siamang-ui-font);
  font-size: 0.95rem;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
  transition: background-color 80ms, border-color 80ms, color 80ms;
}
.sd-rating__item:hover {
  background: color-mix(in srgb, var(--siamang-accent) 6%, transparent);
  border-color: color-mix(in srgb, var(--siamang-accent) 40%, var(--siamang-border));
}
.sd-rating__item.is-selected {
  background: var(--siamang-accent);
  border-color: var(--siamang-accent);
  color: #fff;
}
.sd-rating__num { font-size: 1rem; line-height: 1; }

.sd-rating__labels {
  display: flex;
  justify-content: space-between;
  font-family: var(--siamang-ui-font);
  font-size: 0.8rem;
  color: var(--siamang-muted);
  margin-top: 2px;
}

.sd-rating__na {
  margin-top: 8px;
  align-self: flex-start;
}
.sd-rating__na .sd-radio {
  padding: 6px 10px;
  font-family: var(--siamang-ui-font);
  font-size: 0.85rem;
  color: var(--siamang-muted);
}
.sd-rating__na .sd-radio__decorator { width: 14px; height: 14px; margin-top: 2px; }

/* ─── Matrix ───────────────────────────────────────────────────────────── */

.sd-matrix-wrapper { overflow-x: auto; margin: 0 calc(var(--siamang-section-gap) * -0.5); padding: 0 calc(var(--siamang-section-gap) * 0.5); }

.sd-matrix {
  width: 100%;
  border-collapse: collapse;
  font-family: var(--siamang-font);
  font-size: 0.95rem;
}

.sd-matrix thead th {
  font-family: var(--siamang-ui-font);
  font-size: 0.78rem;
  font-weight: 500;
  color: var(--siamang-muted);
  text-transform: none;
  letter-spacing: 0.02em;
  padding: 8px 6px 12px;
  vertical-align: bottom;
  text-align: center;
  border-bottom: 1px solid var(--siamang-border);
}
.sd-matrix thead th:first-child {
  text-align: left;
  width: 38%;
  min-width: 180px;
}

.sd-matrix tbody td {
  padding: 14px 6px;
  border-bottom: 1px solid color-mix(in srgb, var(--siamang-border) 60%, transparent);
  text-align: center;
}
.sd-matrix tbody td:first-child {
  text-align: left;
  font-weight: 500;
}
.sd-matrix tbody tr:last-child td { border-bottom: none; }
.sd-matrix tbody tr:hover { background: color-mix(in srgb, var(--siamang-accent) 3%, transparent); }

.sd-matrix__cell {
  display: inline-grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border: 1.5px solid color-mix(in srgb, var(--siamang-muted) 50%, var(--siamang-border));
  border-radius: 50%;
  background: var(--siamang-surface);
  cursor: pointer;
  transition: transform 80ms ease, box-shadow 80ms ease, background-color 80ms ease, color 80ms ease;
}
.sd-matrix__cell:hover { border-color: var(--siamang-accent); }
.sd-matrix__cell.is-selected {
  border-color: var(--siamang-accent);
  background: var(--siamang-accent);
  box-shadow: inset 0 0 0 3px var(--siamang-surface);
}

/* ─── Ranking ──────────────────────────────────────────────────────────── */

.sd-ranking { display: flex; flex-direction: column; gap: 6px; }

.sd-ranking__item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px 10px 10px;
  background: var(--siamang-surface);
  border: 1px solid var(--siamang-border);
  border-radius: var(--siamang-radius);
  cursor: grab;
  transition: border-color 80ms, transform 100ms;
}
.sd-ranking__item:hover { border-color: color-mix(in srgb, var(--siamang-accent) 50%, var(--siamang-border)); }
.sd-ranking__item.is-ranked {
  background: color-mix(in srgb, var(--siamang-accent) 6%, var(--siamang-surface));
  border-color: color-mix(in srgb, var(--siamang-accent) 35%, var(--siamang-border));
}

.sd-ranking__handle {
  font-family: var(--siamang-ui-font);
  color: color-mix(in srgb, var(--siamang-muted) 60%, transparent);
  font-size: 1.1rem;
  letter-spacing: -2px;
  user-select: none;
}

.sd-ranking__rank {
  width: 26px;
  height: 26px;
  display: grid;
  place-items: center;
  background: var(--siamang-surface);
  border: 1.5px solid var(--siamang-border);
  border-radius: 50%;
  font-family: var(--siamang-ui-font);
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--siamang-muted);
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
}
.sd-ranking__item.is-ranked .sd-ranking__rank {
  background: var(--siamang-accent);
  border-color: var(--siamang-accent);
  color: #fff;
}

.sd-ranking__label { flex: 1; }

.sd-ranking__actions {
  display: flex;
  gap: 4px;
  font-family: var(--siamang-ui-font);
}
.sd-ranking__btn {
  width: 28px; height: 28px;
  display: grid; place-items: center;
  border: 1px solid var(--siamang-border);
  background: var(--siamang-surface);
  border-radius: 3px;
  color: var(--siamang-muted);
  cursor: pointer;
  font-size: 14px;
  transition: transform 80ms ease, box-shadow 80ms ease, background-color 80ms ease, color 80ms ease;
}
.sd-ranking__btn:hover:not(:disabled) { border-color: var(--siamang-accent); color: var(--siamang-accent); }
.sd-ranking__btn:disabled { opacity: 0.35; cursor: not-allowed; }

/* ─── Navigation ───────────────────────────────────────────────────────── */

.sd-navigation {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-top: 32px;
  padding-top: 0;
}

.sd-btn {
  font-family: var(--siamang-ui-font);
  font-size: 0.95rem;
  font-weight: 500;
  padding: 12px 22px;
  border-radius: var(--siamang-radius);
  cursor: pointer;
  transition: background-color 100ms, border-color 100ms, color 100ms;
  border: 1px solid transparent;
  letter-spacing: 0.01em;
}

.sd-navigation__prev-btn {
  background: transparent;
  border-color: var(--siamang-border);
  color: var(--siamang-muted);
}
.sd-navigation__prev-btn:hover {
  border-color: color-mix(in srgb, var(--siamang-text) 40%, var(--siamang-border));
  color: var(--siamang-text);
}

.sd-navigation__next-btn,
.sd-navigation__complete-btn {
  background: var(--siamang-accent);
  border-color: var(--siamang-accent);
  color: #fff;
}
.sd-navigation__next-btn:hover,
.sd-navigation__complete-btn:hover {
  background: color-mix(in srgb, var(--siamang-accent) 88%, #000);
  border-color: color-mix(in srgb, var(--siamang-accent) 88%, #000);
}

.sd-navigation__hint {
  font-family: var(--siamang-ui-font);
  font-size: 0.78rem;
  color: var(--siamang-muted);
  font-style: italic;
}

/* ─── Completed / Closed pages ─────────────────────────────────────────── */

.sd-completedpage,
.siamang-closed {
  background: var(--siamang-surface);
  border: 1px solid var(--siamang-border);
  border-radius: var(--siamang-radius);
  padding: 56px 48px;
  text-align: center;
}

.sd-completedpage__icon,
.siamang-closed__icon {
  width: 48px; height: 48px;
  margin: 0 auto 20px;
  display: grid; place-items: center;
  border-radius: 50%;
  border: 1.5px solid var(--siamang-accent);
  color: var(--siamang-accent);
  font-family: var(--siamang-ui-font);
}
.siamang-closed__icon { border-color: var(--siamang-muted); color: var(--siamang-muted); }

.sd-completedpage__title,
.siamang-closed__title {
  font-family: var(--siamang-heading-font);
  font-size: 1.5rem;
  font-weight: 600;
  margin: 0 0 10px;
  letter-spacing: -0.01em;
}

.sd-completedpage__body,
.siamang-closed__body {
  margin: 0 auto 24px;
  max-width: 48ch;
  color: var(--siamang-muted);
  font-size: 1rem;
}

.sd-completedpage__meta,
.siamang-closed__meta {
  margin-top: 28px;
  padding-top: 20px;
  border-top: 1px solid var(--siamang-border);
  display: flex;
  justify-content: center;
  gap: 28px;
  font-family: var(--siamang-ui-font);
  font-size: 0.82rem;
  color: var(--siamang-muted);
}
.sd-completedpage__meta dt { font-size: 0.7rem; letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 4px; }
.sd-completedpage__meta dd { margin: 0; color: var(--siamang-text); font-weight: 500; font-variant-numeric: tabular-nums; }

/* ─── Footer ──────────────────────────────────────────────────────────── */

.siamang-footer {
  margin-top: 56px;
  padding-top: 24px;
  border-top: 1px solid var(--siamang-border);
  font-family: var(--siamang-ui-font);
  font-size: 0.82rem;
  color: var(--siamang-muted);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.siamang-footer__row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 18px;
}
.siamang-footer__row a {
  color: var(--siamang-muted);
  text-decoration: none;
  border-bottom: 1px solid color-mix(in srgb, var(--siamang-muted) 30%, transparent);
}
.siamang-footer__row a:hover { color: var(--siamang-text); border-bottom-color: var(--siamang-text); }

.siamang-footer__ethics {
  margin: 0;
  font-style: italic;
  max-width: 80ch;
  line-height: 1.55;
  font-size: 0.78rem;
}

.siamang-footer__sep {
  display: inline-block;
  width: 3px; height: 3px;
  border-radius: 50%;
  background: var(--siamang-muted);
  opacity: 0.6;
}

/* ─── Consent / Intro card ────────────────────────────────────────────── */

.sd-intro {
  background: var(--siamang-surface);
  border: 1px solid var(--siamang-border);
  border-radius: var(--siamang-radius);
  padding: 48px 44px;
}
.sd-intro__eyebrow {
  font-family: var(--siamang-ui-font);
  font-size: 0.74rem;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--siamang-accent);
  margin-bottom: 14px;
}
.sd-intro__title {
  font-family: var(--siamang-heading-font);
  font-size: 1.75rem;
  font-weight: 600;
  margin: 0 0 14px;
  line-height: 1.2;
  letter-spacing: -0.012em;
}
.sd-intro__body { color: var(--siamang-muted); max-width: 60ch; }
.sd-intro__body p { margin: 0 0 12px; }

.sd-intro__meta {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 20px;
  margin: 28px 0;
  padding: 20px 0;
  border-top: 1px solid var(--siamang-border);
  border-bottom: 1px solid var(--siamang-border);
  font-family: var(--siamang-ui-font);
}
.sd-intro__meta dt {
  font-size: 0.7rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--siamang-muted);
  margin-bottom: 6px;
  font-weight: 500;
}
.sd-intro__meta dd {
  margin: 0;
  font-size: 0.98rem;
  color: var(--siamang-text);
  font-weight: 500;
}

.sd-intro__consent {
  margin-top: 24px;
  padding: 16px 18px;
  background: color-mix(in srgb, var(--siamang-accent) 5%, transparent);
  border-left: 2px solid var(--siamang-accent);
  border-radius: 2px;
  font-size: 0.93rem;
}

/* ─── Page transition (between sections) ──────────────────────────────── */

.sd-transition {
  background: var(--siamang-surface);
  border: 1px solid var(--siamang-border);
  border-radius: var(--siamang-radius);
  padding: 48px 44px;
  text-align: center;
}
.sd-transition__step {
  font-family: var(--siamang-ui-font);
  font-size: 0.78rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--siamang-accent);
  margin-bottom: 14px;
  font-weight: 600;
}
.sd-transition__title {
  font-family: var(--siamang-heading-font);
  font-size: 1.45rem;
  font-weight: 600;
  margin: 0 0 12px;
  letter-spacing: -0.01em;
}
.sd-transition__body {
  color: var(--siamang-muted);
  max-width: 50ch;
  margin: 0 auto 28px;
}
.sd-transition__steps {
  display: flex;
  justify-content: center;
  gap: 6px;
  margin-top: 32px;
  list-style: none;
  padding: 0;
}
.sd-transition__steps li {
  height: 3px;
  width: 24px;
  background: var(--siamang-border);
  border-radius: 999px;
}
.sd-transition__steps li.is-done { background: var(--siamang-accent); }
.sd-transition__steps li.is-active {
  background: var(--siamang-accent);
  width: 36px;
}

/* ─── Page transitions ─────────────────────────────────────────────── */
.siamang-page-enter {
  animation: siamang-fade-in 140ms ease both;
}

@keyframes siamang-fade-in {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ─── Error shake ──────────────────────────────────────────────────── */
@keyframes siamang-error-shake {
  0%, 100% { transform: translateX(0); }
  15% { transform: translateX(-6px); }
  30% { transform: translateX(6px); }
  45% { transform: translateX(-4px); }
  60% { transform: translateX(4px); }
  75% { transform: translateX(-2px); }
  90% { transform: translateX(2px); }
}

.sd-question.has-error {
  animation: siamang-error-shake 0.45s ease;
}

/* ─── Loading overlay ─────────────────────────────────────────────── */
.siamang-loading-overlay {
  position: fixed;
  inset: 0;
  z-index: 200;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  /* Solid background instead of `backdrop-filter: blur(...)` — the
     blur triggers a compositor pass every frame, and this overlay
     only shows briefly while submitting, so the visual difference
     is imperceptible to users. */
  background: color-mix(in srgb, var(--siamang-bg) 96%, transparent);
}

.siamang-spinner {
  width: 36px;
  height: 36px;
  border: 3px solid var(--siamang-border);
  border-top-color: var(--siamang-accent);
  border-radius: 50%;
  animation: siamang-spin 0.7s linear infinite;
}

@keyframes siamang-spin {
  to { transform: rotate(360deg); }
}

.siamang-loading-overlay__text {
  font-family: var(--siamang-ui-font);
  font-size: 0.95rem;
  color: var(--siamang-muted);
  margin: 0;
}

/* ─── Skeleton loading ────────────────────────────────────────────── */
.siamang-skeleton {
  background: var(--siamang-surface);
  border: 1px solid var(--siamang-border);
  border-radius: var(--siamang-radius);
  padding: var(--siamang-section-gap);
}

.siamang-skeleton__header {
  padding-bottom: 20px;
  margin-bottom: 20px;
  border-bottom: 1px solid var(--siamang-border);
}

.siamang-skeleton__card {
  padding: 8px 0;
}

.siamang-skeleton__line {
  height: 14px;
  margin-bottom: 10px;
  background: color-mix(in srgb, var(--siamang-border) 60%, transparent);
  border-radius: 8px;
  animation: siamang-pulse 1.5s ease-in-out infinite;
}

.siamang-skeleton__line--title { width: 50%; height: 22px; }
.siamang-skeleton__line--heading { width: 35%; height: 18px; }
.siamang-skeleton__line--short { width: 25%; }
.siamang-skeleton__line--medium { width: 60%; }

@keyframes siamang-pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 0.8; }
}

/* ─── Resume banner ───────────────────────────────────────────────── */
.siamang-resume-banner {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  padding: 14px 18px;
  margin-bottom: 20px;
  background: color-mix(in srgb, var(--siamang-accent) 8%, transparent);
  border: 1px solid color-mix(in srgb, var(--siamang-accent) 25%, var(--siamang-border));
  border-radius: var(--siamang-radius);
  font-family: var(--siamang-ui-font);
  font-size: 0.9rem;
  color: var(--siamang-text);
}

.siamang-resume-banner__actions {
  display: flex;
  gap: 8px;
  margin-left: auto;
}

.siamang-resume-banner__actions .sd-btn {
  padding: 8px 16px;
  font-size: 0.85rem;
}

/* ─── Retry dialog ────────────────────────────────────────────────── */
.siamang-retry-overlay {
  position: fixed;
  inset: 0;
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
  background: color-mix(in srgb, var(--siamang-bg) 96%, transparent);
}

.siamang-retry-dialog {
  background: var(--siamang-surface);
  border: 1px solid var(--siamang-border);
  border-radius: var(--siamang-radius);
  padding: 36px 32px 28px;
  max-width: 420px;
  width: calc(100% - 32px);
  text-align: center;
  box-shadow: 0 16px 48px rgba(0,0,0,0.12);
}

.siamang-retry-dialog__icon {
  width: 44px;
  height: 44px;
  margin: 0 auto 16px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: color-mix(in srgb, var(--siamang-error) 12%, transparent);
  color: var(--siamang-error);
}

.siamang-retry-dialog__title {
  font-family: var(--siamang-heading-font);
  font-size: 1.15rem;
  font-weight: 600;
  margin: 0 0 8px;
}

.siamang-retry-dialog__body {
  color: var(--siamang-muted);
  font-size: 0.92rem;
  margin: 0 0 24px;
  line-height: 1.5;
}

.siamang-retry-dialog__actions {
  display: flex;
  gap: 10px;
  justify-content: center;
}

.siamang-retry-dialog__actions .sd-btn {
  padding: 10px 20px;
  font-size: 0.9rem;
}

/* ─── Multi-choice counter ────────────────────────────────────────── */
.siamang-multi-counter {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 12px;
  padding: 8px 12px;
  background: color-mix(in srgb, var(--siamang-accent) 5%, transparent);
  border-radius: var(--siamang-radius);
  font-family: var(--siamang-ui-font);
  font-size: 0.82rem;
}

.siamang-multi-counter__count {
  font-weight: 600;
  color: var(--siamang-text);
  font-variant-numeric: tabular-nums;
}

.siamang-multi-counter__hint {
  color: var(--siamang-muted);
  font-size: 0.78rem;
}

.siamang-multi-counter__hint.is-max {
  color: var(--siamang-accent);
  font-weight: 500;
}

/* ─── Media attachments ──────────────────────────────────────────── */
.siamang-media-gallery {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin: 12px 0 4px;
}
.siamang-media {
  margin: 0;
  max-width: 100%;
  border-radius: var(--siamang-radius);
  overflow: hidden;
  background: var(--siamang-surface);
}
.siamang-media img,
.siamang-media video {
  display: block;
  max-width: 100%;
  height: auto;
  border-radius: var(--siamang-radius);
}
.siamang-media audio {
  width: 100%;
}
.siamang-media--video,
.siamang-media--audio {
  width: 100%;
}
.siamang-media__caption {
  font-size: 0.82rem;
  color: var(--siamang-muted);
  padding: 6px 10px;
  font-family: var(--siamang-ui-font);
}
.sd-radio .siamang-media,
.sd-checkbox .siamang-media {
  margin-top: 6px;
  max-width: 180px;
}

/* ─── Saving indicator ────────────────────────────────────────────── */
.siamang-saving-indicator {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: var(--siamang-ui-font);
  font-size: 0.74rem;
  color: var(--siamang-muted);
  margin-left: auto;
  animation: siamang-fade-in 200ms ease;
}

.siamang-saving-indicator__dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--siamang-accent);
  animation: siamang-pulse 1s ease-in-out infinite;
}

/* ─── Char count warning ──────────────────────────────────────────── */
.siamang-char-warning {
  font-family: var(--siamang-ui-font);
  font-size: 0.78rem;
  color: var(--siamang-warn);
  text-align: right;
  margin-top: 2px;
  animation: siamang-fade-in 150ms ease;
}

/* ─── Drag-and-drop ranking ──────────────────────────────────────── */
.sd-ranking__item.is-dragging {
  opacity: 0.5;
  transform: scale(0.98);
}
.sd-ranking__item.is-drag-over {
  border-color: var(--siamang-accent);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--siamang-accent) 25%, transparent);
}
.sd-ranking__item.is-unranked {
  cursor: pointer;
  opacity: 0.85;
  transition: opacity 100ms, border-color 100ms;
}
.sd-ranking__item.is-unranked:hover {
  opacity: 1;
  border-color: color-mix(in srgb, var(--siamang-accent) 40%, var(--siamang-border));
}
.sd-ranking__section-label {
  font-family: var(--siamang-ui-font);
  font-size: 0.74rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--siamang-muted);
  font-weight: 600;
  margin: 16px 0 4px;
}
.sd-ranking__item {
  cursor: grab;
}
.sd-ranking__item:active {
  cursor: grabbing;
}

/* ─── NPS Slider ──────────────────────────────────────────────────── */
.siamang-slider {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-width: 520px;
}
.siamang-slider__input {
  width: 100%;
  accent-color: var(--siamang-accent);
  cursor: pointer;
}
.siamang-slider__value {
  text-align: center;
  font-family: var(--siamang-ui-font);
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--siamang-accent);
  font-variant-numeric: tabular-nums;
  line-height: 1;
}
.siamang-slider__labels {
  display: flex;
  justify-content: space-between;
  font-family: var(--siamang-ui-font);
  font-size: 0.74rem;
  color: var(--siamang-muted);
  text-align: center;
  margin-top: 4px;
}
.siamang-slider__tick {
  flex: 1;
  text-align: center;
  font-size: 0.72rem;
  color: var(--siamang-muted);
}
.siamang-slider__tick.is-active {
  color: var(--siamang-accent);
  font-weight: 600;
}
.siamang-slider__end-labels {
  display: flex;
  justify-content: space-between;
  font-family: var(--siamang-ui-font);
  font-size: 0.8rem;
  color: var(--siamang-muted);
  font-style: italic;
}

/* ─── Other (specify) input ──────────────────────────────────────── */
.sd-other-input {
  margin-top: 8px;
  padding-left: 32px;
}
.sd-other-input__field {
  width: 100%;
  max-width: 320px;
  font-size: 0.92rem;
  border-color: var(--siamang-accent);
}
.sd-other-input__field:focus {
  outline: 2px solid var(--siamang-accent);
  outline-offset: 1px;
}

/* ─── Image choice ────────────────────────────────────────────────── */
.sd-image-choices {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 12px;
}
.sd-image-choice {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 12px;
  border: 2px solid var(--siamang-border);
  border-radius: var(--siamang-radius);
  background: var(--siamang-surface);
  cursor: pointer;
  transition: border-color 100ms, background-color 100ms, transform 100ms;
  font-family: inherit;
  color: inherit;
}
.sd-image-choice:hover {
  border-color: color-mix(in srgb, var(--siamang-accent) 40%, var(--siamang-border));
  transform: translateY(-2px);
}
.sd-image-choice.is-selected {
  border-color: var(--siamang-accent);
  background: color-mix(in srgb, var(--siamang-accent) 6%, var(--siamang-surface));
}
.sd-image-choice__img {
  width: 100%;
  max-height: 96px;
  object-fit: contain;
  border-radius: 4px;
  pointer-events: none;
}
.sd-image-choice__label {
  font-family: var(--siamang-ui-font);
  font-size: 0.85rem;
  font-weight: 500;
  text-align: center;
}

/* ─── Searchable dropdown ─────────────────────────────────────────── */
.siamang-search-dropdown { position: relative; max-width: 400px; }
.siamang-search-dropdown__trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  text-align: left;
}
.siamang-search-dropdown__arrow {
  display: inline-block;
  width: 8px; height: 8px;
  border-right: 1.5px solid var(--siamang-muted);
  border-bottom: 1.5px solid var(--siamang-muted);
  transform: rotate(45deg);
  flex-shrink: 0;
  margin-left: 8px;
}
.siamang-search-dropdown__menu {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  z-index: 50;
  background: var(--siamang-surface);
  border: 1px solid var(--siamang-border);
  border-radius: var(--siamang-radius);
  box-shadow: 0 8px 24px rgba(0,0,0,0.1);
  max-height: 300px;
  display: flex;
  flex-direction: column;
}
.siamang-search-dropdown__search {
  border: none;
  border-bottom: 1px solid var(--siamang-border);
  border-radius: var(--siamang-radius) var(--siamang-radius) 0 0;
  padding: 10px 14px;
}
.siamang-search-dropdown__options {
  overflow-y: auto;
  flex: 1;
}
.siamang-search-dropdown__option {
  padding: 9px 14px;
  cursor: pointer;
  font-size: 0.95rem;
  transition: background 60ms;
}
.siamang-search-dropdown__option:hover { background: color-mix(in srgb, var(--siamang-accent) 6%, transparent); }
.siamang-search-dropdown__option.is-selected {
  background: color-mix(in srgb, var(--siamang-accent) 10%, transparent);
  color: var(--siamang-accent);
  font-weight: 500;
}
.siamang-search-dropdown__empty {
  padding: 20px 14px;
  text-align: center;
  color: var(--siamang-muted);
  font-size: 0.85rem;
}

/* ─── Theme toggle ─────────────────────────────────────────────────── */
.siamang-theme-toggle {
  background: none;
  border: 1px solid var(--siamang-border);
  border-radius: 50%;
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  cursor: pointer;
  font-size: 16px;
  transition: background 100ms, border-color 100ms;
  line-height: 1;
  padding: 0;
}
.siamang-theme-toggle:hover {
  background: color-mix(in srgb, var(--siamang-accent) 8%, transparent);
  border-color: var(--siamang-accent);
}

/* ─── Step dots ────────────────────────────────────────────────────── */
.siamang-step-dots {
  display: flex;
  justify-content: center;
  gap: 6px;
  margin-bottom: 24px;
  padding: 0;
}
.siamang-step-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 2px solid var(--siamang-border);
  background: transparent;
  cursor: pointer;
  padding: 0;
  transition: opacity 180ms ease, transform 180ms ease;
}
.siamang-step-dot:hover { border-color: var(--siamang-accent); }
.siamang-step-dot.is-active {
  background: var(--siamang-accent);
  border-color: var(--siamang-accent);
  transform: scale(1.25);
}
.siamang-step-dot.is-complete {
  background: color-mix(in srgb, var(--siamang-accent) 30%, transparent);
  border-color: var(--siamang-accent);
}
.siamang-step-dot[disabled] {
  cursor: not-allowed;
  opacity: 0.5;
}

/* ─── Celebration / confetti ───────────────────────────────────────── */
.siamang-celebration {
  position: fixed;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
  z-index: 10;
}
.siamang-confetti {
  position: absolute;
  top: -10px;
  border-radius: 2px;
  animation: siamang-confetti-fall linear forwards;
  opacity: 0.8;
}
@keyframes siamang-confetti-fall {
  0% { transform: translateY(0) rotate(0deg) scale(1); opacity: 0.8; }
  100% { transform: translateY(100vh) rotate(720deg) scale(0.3); opacity: 0; }
}

/* ─── Access gate ──────────────────────────────────────────────────── */
.siamang-access-gate {
  max-width: 420px;
  margin: 80px auto;
  background: var(--siamang-surface);
  border: 1px solid var(--siamang-border);
  border-radius: var(--siamang-radius);
  padding: 48px 40px;
  text-align: center;
}
.siamang-access-gate__title {
  font-family: var(--siamang-heading-font);
  font-size: 1.4rem;
  font-weight: 600;
  margin: 0 0 10px;
}
.siamang-access-gate__body {
  color: var(--siamang-muted);
  margin: 0 0 28px;
  font-size: 0.95rem;
}
.siamang-access-gate__form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* ─── Print ───────────────────────────────────────────────────────────── */

@media print {
  body { background: #fff; }
  #survey {
    max-width: 100%;
    padding: 0;
  }
  .sd-navigation,
  .siamang-skip-link,
  .siamang-progress,
  .screen-toolbar,
  .tweaks-fab,
  .tweaks-panel {
    display: none !important;
  }
  .sd-page,
  .sd-intro,
  .siamang-closed,
  .sd-completedpage,
  .sd-transition {
    border: 1px solid #000 !important;
    border-radius: 0 !important;
    background: #fff !important;
    page-break-inside: avoid;
  }
  .sd-page + .sd-page,
  .sd-intro + * { page-break-before: always; margin-top: 0; }
  .siamang-header { border-bottom: 2px solid #000; }
  .sd-rating__item,
  .sd-radio__decorator,
  .sd-checkbox__decorator { border-color: #000 !important; }
  .sd-item--checked .sd-radio__decorator::after,
  .sd-rating__item.is-selected,
  .sd-item--checked .sd-checkbox__decorator { background: #000 !important; }
}

/* ─── Reduced motion ──────────────────────────────────────────────────── */

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}

/* ─── Responsive ──────────────────────────────────────────────────────── */

@media (max-width: 600px) {
  #survey { padding: 20px 16px 64px; }
  .siamang-header { flex-direction: column; align-items: flex-start; gap: 12px; }
  .siamang-header.center { align-items: center; }
  .siamang-header__title { font-size: 1.3rem; }
  .sd-page,
  .sd-intro,
  .sd-completedpage,
  .siamang-closed,
  .sd-transition {
    padding: 24px 20px;
  }
  .sd-page__title { font-size: 1.15rem; }
  .sd-rating__scale { gap: 4px; }
  .sd-rating__item { min-width: 40px; padding: 8px 4px; font-size: 0.9rem; }
  .sd-navigation { flex-direction: column-reverse; }
  .sd-navigation .sd-btn { width: 100%; }
  .sd-choices--buttons { flex-direction: column; }
  .sd-choices--buttons .sd-radio { width: 100%; }
  .sd-matrix thead th:first-child { min-width: 120px; }
  .sd-completedpage__meta { flex-direction: column; gap: 14px; }
  .sd-radio, .sd-checkbox {
    padding: 14px 12px;
    min-height: 48px;
  }
  .sd-rating__item {
    min-width: 40px;
    min-height: 40px;
    padding: 8px 4px;
  }
  .sd-ranking__item {
    padding: 12px 10px;
  }
  .siamang-header__title { font-size: 1.15rem; }
  .sd-btn {
    padding: 14px 20px;
    font-size: 1rem;
  }
  .siamang-slider__input {
    height: 40px;
  }
  .siamang-search-dropdown__option {
    padding: 12px 14px;
    font-size: 1rem;
  }
  .sd-page__title { font-size: 1.1rem; }
  .sd-question__title { font-size: 0.98rem; }
  .siamang-multi-counter {
    padding: 10px 12px;
    font-size: 0.85rem;
  }
  .siamang-image-choices {
    grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
    gap: 8px;
  }
  .siamang-progress__text {
    font-size: 0.72rem;
  }
}

/* ─── Screen toolbar (prototype-only chrome) ─────────────────────────── */

.screen-toolbar {
  position: fixed;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 50;
  display: flex;
  gap: 4px;
  padding: 4px;
  /* `backdrop-filter: blur(12px)` on an always-visible pill was a
     constant compositor cost; replaced with a solid background. */
  background: rgb(20, 20, 22);
  border-radius: 999px;
  font-family: var(--siamang-ui-font);
  font-size: 0.78rem;
  color: rgba(255,255,255,0.65);
  box-shadow: 0 8px 32px rgba(0,0,0,0.18);
  max-width: calc(100vw - 32px);
  overflow-x: auto;
  -ms-overflow-style: none;
  scrollbar-width: none;
}
.screen-toolbar::-webkit-scrollbar { display: none; }
.screen-toolbar__btn {
  border: none;
  background: transparent;
  color: inherit;
  padding: 6px 12px;
  border-radius: 999px;
  cursor: pointer;
  white-space: nowrap;
  font-family: inherit;
  font-size: inherit;
  font-weight: 500;
  letter-spacing: 0.02em;
  transition: background 100ms, color 100ms;
}
.screen-toolbar__btn:hover { color: #fff; }
.screen-toolbar__btn.is-active {
  background: rgba(255,255,255,0.14);
  color: #fff;
}

@media print {
  .screen-toolbar { display: none; }
}

/* Mobile preview frame */
body.viewport-mobile { background: #2a2a2e; padding: 24px 0; }
body.viewport-mobile #survey-frame {
  width: 390px;
  max-width: 100%;
  margin: 0 auto;
  background: var(--siamang-bg);
  border-radius: 28px;
  box-shadow: 0 24px 64px rgba(0,0,0,0.25), 0 0 0 8px #0a0a0c, 0 0 0 9px #2a2a2e;
  overflow: hidden;
  min-height: 720px;
}
body.viewport-mobile #survey { padding: 20px 18px 48px; }
body.viewport-mobile .sd-rating__item { font-size: 0.88rem; padding: 8px 4px; min-width: 38px; }
body.viewport-mobile .sd-choices--buttons { flex-direction: column; }
body.viewport-mobile .sd-choices--buttons .sd-radio { width: 100%; }
body.viewport-mobile .sd-navigation { flex-direction: column-reverse; }
body.viewport-mobile .sd-navigation .sd-btn { width: 100%; }
body.viewport-mobile .siamang-header { flex-direction: column; align-items: flex-start; gap: 12px; }
body.viewport-mobile .sd-page,
body.viewport-mobile .sd-intro,
body.viewport-mobile .sd-completedpage,
body.viewport-mobile .siamang-closed,
body.viewport-mobile .sd-transition { padding: 22px 18px; }

/* Print-preview helper: emulate paged feel in normal screen view */
body.viewport-print {
  background: #d5d3cd;
  padding: 32px 0;
}
body.viewport-print #survey-frame {
  background: #fff;
  width: 794px; /* ~A4 width @ 96dpi */
  max-width: calc(100% - 24px);
  margin: 0 auto;
  box-shadow: 0 8px 28px rgba(0,0,0,0.15);
  padding: 56px 64px 72px;
  min-height: 1000px;
}
body.viewport-print .screen-toolbar { background: rgba(20,20,22,0.92); }
body.viewport-print #survey { padding: 0; max-width: 100%; }
body.viewport-print .sd-navigation,
body.viewport-print .siamang-progress { display: none; }
body.viewport-print .sd-page,
body.viewport-print .sd-intro,
body.viewport-print .sd-transition,
body.viewport-print .sd-completedpage,
body.viewport-print .siamang-closed {
  border: 1px solid #000;
  border-radius: 0;
  page-break-inside: avoid;
}
body.viewport-print .siamang-header { border-bottom: 2px solid #000; }
body.viewport-print .sd-rating__item,
body.viewport-print .sd-radio__decorator,
body.viewport-print .sd-checkbox__decorator,
body.viewport-print .sd-matrix__cell { border-color: #000; }

/* App-level error boundary */
.siamang-app-error {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  padding: 2rem;
}
.siamang-app-error__container {
  text-align: center;
  max-width: 480px;
}
.siamang-app-error__title {
  font-family: var(--heading-font, 'Georgia', serif);
  font-size: 1.5rem;
  color: var(--text, #1a1a1a);
  margin-bottom: 0.75rem;
}
.siamang-app-error__body {
  font-size: 1rem;
  color: var(--muted, #555);
  margin-bottom: 1.5rem;
  line-height: 1.5;
}
