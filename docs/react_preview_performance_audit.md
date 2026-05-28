# React preview/performance audit (survey frontend)

## Context
Анализ выполнен по текущим файлам runtime/шаблонов React в `siamang/frontend/templates/react` и `siamang/frontend/runtime/react.py`.

## Findings

1. **Global re-render on each answer update — confirmed.**
   - `setAnswer()` обновляет единый объект `answers` через `setAnswers`.
   - Это вызывает ререндер `App`, после чего заново мапится список `items` и для каждого `QuestionRenderer` создаётся новый inline-callback `onChange={(v) => setAnswer(q.id, v)}`.
   - `QuestionRenderer` и дочерние компоненты не обёрнуты в `React.memo`.

2. **`visiblePages` recomputation tied to `answers` — confirmed.**
   - `const pages = useMemo(() => visiblePages(allPages, answers), [allPages, answers]);`
   - Для каждой печати/клика пересчитываются условия видимости страниц.

3. **Event listeners recreated frequently — confirmed.**
   - `keydown`-effect зависит от `[submitting, phase, pageIdx, pages, answers]`, поэтому listener удаляется/добавляется при каждом изменении `answers`.
   - `beforeunload`-effect зависит от `[answers, phase]` и также переустанавливается.

4. **Timer cascade on every keystroke — confirmed.**
   - В `setAnswer`: `setTimeout(...ScriptRunner.onAnswer...)`, debounce 2000 мс для save, внутри него `setSaving(true)` и ещё один `setTimeout` на 800 мс для `setSaving(false)`.

5. **Autosave payload stores service keys — confirmed.**
   - При инициализации в `answers` добавляются `__options__` и `__pages__`.
   - `saveToLocalStorage` сериализует `currentAnswers` целиком.

6. **Compilation/minification concern — partially confirmed with nuance.**
   - React runtime действительно сначала пробует `npx sucrase`, который только транспилирует JSX и **не минифицирует**.
   - Fallback при неуспешной предкомпиляции: отдаётся `bundle.jsx` + `@babel/standalone` в браузере (заметно хуже cold start для preview).
   - Прямого встроенного этапа minify (terser/esbuild/swc minify) в runtime нет.

7. **CSS perf risks — confirmed.**
   - В стилях есть `backdrop-filter: blur(...)`.
   - Есть `transition: all` на нескольких селекторах.
   - Есть бесконечные анимации (`animation: ... infinite`) для некоторых элементов.

8. **`q_consent` / buttons behavior — plausible, but form-specific.**
   - Для single-choice в режиме `display="buttons"` компонент рендерит `<button>`-вариант и это может усиливать repaint/reflow под активными transition.
   - Сам runtime ведёт себя ожидаемо; это не баг компилятора, а cost выбранного UI-режима.

## Root-cause summary
Проблема не в одной точке, а в комбинации:
- coarse-grained state (`answers`) + отсутствие memoization компонентов вопросов;
- эффекты, завязанные на `answers`, которые churn-ят listeners;
- синхронный `localStorage.setItem(JSON.stringify(largeObject))`;
- CSS с дорогостоящими свойствами/анимациями;
- отсутствие minification шага для bundle и возможный JSX-in-browser fallback.

## Priority fixes (recommended order)

1. **Стабилизировать render-path**
   - Обернуть `QuestionRenderer`/тяжёлые question-компоненты в `React.memo`.
   - Вынести `onChange` в стабильный callback (например, `useCallback` + child receives `questionId`).

2. **Развязать listeners от `answers`**
   - Для `keydown`/`beforeunload` подписываться один раз и читать актуальное состояние из `useRef`.

3. **Оптимизировать autosave**
   - Не сохранять служебные `__options__`, `__pages__`.
   - Сохранять только «чистые ответы» + метаданные.
   - Перевести save на `requestIdleCallback` (с fallback) и ограничить частоту записи.

4. **CSS hygiene**
   - Заменить `transition: all` на список конкретных свойств (`opacity`, `transform`, `color` и т.п.).
   - Для blur-элементов уменьшить радиус/частоту изменения, либо убрать на low-end.
   - Отключать анимации при `prefers-reduced-motion`.

5. **Build pipeline**
   - После JSX transpile добавить minification step (esbuild/swc/terser).
   - В preview явно логировать, когда включился JSX fallback, чтобы это было заметно сразу.

## Preview vs compilation interpretation
- Если slowdown заметен именно в локальном `preview`, сначала проверьте: не попал ли runtime в fallback `bundle.jsx + @babel/standalone`.
- Даже при успешной предкомпиляции, без minify и при текущем render/CSS профиле lag на вводе останется.
