/* siamang React runtime — production app (v2 architecture).
   Reads SURVEY / PAGES from window globals (injected by ReactRuntime).
   Uses answers store for form state, compiled visibility engine,
   and modular hooks for each concern. */

const { useState, useEffect, useMemo, useRef, useCallback } = React;

/* ─── Legacy Expression AST evaluator (backward compat) ───────────────────
   Kept for surveys deployed with pre-compiled AST payloads.
   New payloads use { deps, fn } format handled by visibility.jsx. */

function evalNode(node, answers) {
  if (node === null || node === undefined) return null;
  if (typeof node !== "object") return node;
  if (Array.isArray(node)) return node;

  const t = node.type || node.kind;
  if (t === "var") return answers[node.name];
  if (t === "literal") return node.value;
  if (t === "expression") {
    const op = node.op;
    if (op === "and") return evalArgs(node, answers).every(Boolean);
    if (op === "or")  return evalArgs(node, answers).some(Boolean);
    if (op === "not") return !Boolean(evalNode(node.left, answers));
    const l = evalNode(node.left, answers);
    const r = evalNode(node.right, answers);
    if (op === "=" || op === "==" || op === "eq") return l === r;
    if (op === "!=" || op === "ne") return l !== r;
    if (op === ">"  || op === "gt") return l > r;
    if (op === ">=" || op === "ge") return l >= r;
    if (op === "<"  || op === "lt") return l < r;
    if (op === "<=" || op === "le") return l <= r;
    if (op === "in")     return Array.isArray(r) && r.includes(l);
    if (op === "not in" || op === "notin")
                          return !Array.isArray(r) || !r.includes(l);
    if (op === "raw") return false;
  }
  return null;
}

function evalArgs(node, answers) {
  if (Array.isArray(node.args)) return node.args.map((a) => evalNode(a, answers));
  return [evalNode(node.left, answers), evalNode(node.right, answers)];
}

const __exprDepsCache = new WeakMap();
const __exprResultCache = new WeakMap();

function collectExprDeps(node, out = new Set()) {
  if (node === null || node === undefined) return out;
  if (typeof node !== "object") return out;
  if (Array.isArray(node)) {
    for (const item of node) collectExprDeps(item, out);
    return out;
  }
  const t = node.type || node.kind;
  if (t === "var" && typeof node.name === "string") {
    out.add(node.name);
    return out;
  }
  if (node.left !== undefined) collectExprDeps(node.left, out);
  if (node.right !== undefined) collectExprDeps(node.right, out);
  if (Array.isArray(node.args)) {
    for (const arg of node.args) collectExprDeps(arg, out);
  }
  return out;
}

function evalConditionMemoized(condition, answers) {
  if (condition === null || condition === undefined) return true;
  if (typeof condition === "string") return true;
  if (typeof condition !== "object") return Boolean(condition);

  let deps = __exprDepsCache.get(condition);
  if (!deps) {
    deps = Array.from(collectExprDeps(condition));
    __exprDepsCache.set(condition, deps);
  }

  const depKey = deps.map((name) => JSON.stringify(answers[name])).join("|");
  const prev = __exprResultCache.get(condition);
  if (prev && prev.depKey === depKey) return prev.value;

  const value = Boolean(evalNode(condition, answers));
  __exprResultCache.set(condition, { depKey, value });
  return value;
}

/* ─── Helpers ───────────────────────────────────────────────────────── */

function isAnswered(q, v) {
  if (v === undefined || v === null || v === "") return false;
  if (Array.isArray(v)) return v.length > 0;
  if (typeof v === "object") return Object.keys(v).length > 0;
  return true;
}

function extractOptions(pages) {
  const opts = {};
  for (const p of pages) {
    const items = p.items || [];
    for (const q of items) {
      if (q.options) opts[q.id] = q.options;
    }
  }
  return opts;
}

/* ─── ScriptRunner ──────────────────────────────────────────────────── */

const ScriptRunner = {
  _utils: {
    shuffle: (arr) => {
      const a = [...arr];
      for (let i = a.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [a[i], a[j]] = [a[j], a[i]];
      }
      return a;
    },
    sample: (arr, n) => ScriptRunner._utils.shuffle(arr).slice(0, n),
    clamp: (v, min, max) => Math.min(Math.max(v, min), max),
    debounce: (fn, ms) => {
      let timer;
      return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), ms); };
    },
    now: () => Date.now(),
    formatDate: (d) => new Date(d).toISOString().split("T")[0],
  },

  _api: {
    get: async (url) => { try { return await (await fetch(url)).json(); } catch (e) { return null; } },
    post: async (url, data) => {
      try {
        return await (await fetch(url, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
        })).json();
      } catch (e) { return null; }
    },
  },

  run(trigger, answers, context = {}, target = null) {
    const scripts = (window.SURVEY && window.SURVEY.scripts) || [];
    if (!scripts.length) return;
    const matching = scripts.filter((s) => {
      if (s.trigger !== trigger) return false;
      if (target && s.target && s.target !== target) return false;
      if (!target && s.target) return false;
      return true;
    });
    for (const script of matching) {
      try {
        const fn = new Function("answers", "utils", "api", "context", script.code);
        fn(answers, ScriptRunner._utils, ScriptRunner._api, { ...script.context, ...context });
      } catch (err) {
        console.warn(`siamang Script error [${script.name || script.trigger}]:`, err);
      }
    }
  },

  runForQuestion(questionId, answers) { ScriptRunner.run("onQuestionShow", answers, {}, questionId); },
  runForPage(pageName, answers) { ScriptRunner.run("onPageEnter", answers, {}, pageName); },
  runOnInit(answers) { ScriptRunner.run("onInit", answers); },
  runOnSubmit(answers) { ScriptRunner.run("onSubmit", answers); },
};

/* ─── Error Boundaries ─────────────────────────────────────────────────── */

class ErrorBoundary extends React.Component {
  constructor(props) { super(props); this.state = { hasError: false }; }
  static getDerivedStateFromError() { return { hasError: true }; }
  componentDidCatch(error, info) { console.error("siamang ErrorBoundary:", error, info); }
  render() {
    if (this.state.hasError) {
      return (
        <div className="siamang-error-boundary" role="alert">
          <h3 className="siamang-error-boundary__title">Something went wrong</h3>
          <p className="siamang-error-boundary__body">An unexpected error occurred. Your previous answers have been saved.</p>
          <button className="sd-btn sd-navigation__next-btn" onClick={() => { this.setState({ hasError: false }); window.location.reload(); }}>Reload survey</button>
        </div>
      );
    }
    return this.props.children;
  }
}

class AppErrorBoundary extends React.Component {
  constructor(props) { super(props); this.state = { hasError: false }; }
  static getDerivedStateFromError() { return { hasError: true }; }
  componentDidCatch(error, info) { console.error("siamang AppErrorBoundary:", error, info); }
  render() {
    if (this.state.hasError) {
      return (
        <div className="siamang-app-error" role="alert">
          <div className="siamang-app-error__container">
            <h2 className="siamang-app-error__title">Survey temporarily unavailable</h2>
            <p className="siamang-app-error__body">We encountered an unexpected error. Your previous answers have been saved.</p>
            <button className="sd-btn sd-navigation__next-btn" onClick={() => { this.setState({ hasError: false }); window.location.reload(); }}>Reload survey</button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

/* ─── Header / Footer ──────────────────────────────────────────────────── */

function Header() {
  const ui = window.SURVEY || {};
  if (ui.showHeader === false) return null;
  const pos = ui.logoPosition || "left";
  return (
    <header className={"siamang-header " + pos}>
      {ui.logoUrl ? (
        <img className="siamang-header__logo" src={ui.logoUrl} alt="" role="presentation" />
      ) : ui.logoText ? (
        <div className="siamang-header__logo" aria-hidden="true">{ui.logoText}</div>
      ) : null}
      <div className="siamang-header__text">
        {ui.title ? <h1 className="siamang-header__title">{ui.title}</h1> : null}
        {ui.institution ? <p className="siamang-header__institution">{ui.institution}</p> : null}
        {ui.subtitle ? <p className="siamang-header__subtitle">{ui.subtitle}</p> : null}
      </div>
    </header>
  );
}

function Footer() {
  const ui = window.SURVEY || {};
  const links = [];
  if (ui.institution) links.push({ key: "i", node: <span>{ui.institution.split("—")[0].trim()}</span> });
  if (ui.privacyUrl) links.push({ key: "p", node: <a href={ui.privacyUrl} rel="noopener" target="_blank">Privacy</a> });
  if (ui.contactEmail) links.push({ key: "c", node: <a href={"mailto:" + ui.contactEmail}>Contact research team</a> });
  if (!links.length && !ui.ethics) return null;
  return (
    <footer className="siamang-footer">
      {links.length ? (
        <div className="siamang-footer__row">
          {links.map((l, i) => (
            <React.Fragment key={l.key}>
              {i > 0 ? <span className="siamang-footer__sep" aria-hidden="true"></span> : null}
              {l.node}
            </React.Fragment>
          ))}
        </div>
      ) : null}
      {ui.ethics ? <p className="siamang-footer__ethics">{ui.ethics}</p> : null}
    </footer>
  );
}

/* ─── SurveyPage ───────────────────────────────────────────────────────── */

function SurveyPage({ page, store, visibilityEngine, setAnswer, errors, onNext, onPrev, isFirst, isLast, totalQuestions, qStart, submitting, handleBlur, uiTexts }) {
  const answers = useAnswersStore(store);
  let qNum = qStart;

  const renderItem = (q) => {
    if (!visibilityEngine.isItemVisible(q, answers)) return null;
    qNum += 1;
    return (
      <ErrorBoundary key={q.id}>
        <Question
          key={q.id}
          q={q}
          qId={q.id}
          value={answers[q.id]}
          setAnswer={setAnswer}
          num={"Q" + String(qNum).padStart(2, "0")}
          error={errors[q.id]}
          handleBlur={handleBlur}
          answers={answers}
          onAutoAdvance={onNext}
        />
      </ErrorBoundary>
    );
  };

  return (
    <div className="sd-page">
      {page.section ? <div className="sd-page__eyebrow">{page.section}</div> : null}
      {page.title ? <h2 className="sd-page__title">{page.title}</h2> : null}
      {page.description ? <p className="sd-page__description">{page.description}</p> : null}

      {page.blocks
        ? page.blocks
            .filter((b) => visibilityEngine.isBlockVisible(b, answers))
            .map((b, i) => (
              <div key={i} className="sd-block">
                {b.title ? <h3 className="sd-block__title">{b.title}</h3> : null}
                {(b.items || []).map(renderItem)}
              </div>
            ))
        : (page.items || []).map(renderItem)}

      <div className="sd-navigation">
        {(window.SURVEY || {}).allowBack !== false ? (
          <button
            type="button"
            className="sd-btn sd-navigation__prev-btn"
            onClick={onPrev}
            disabled={isFirst || submitting}
            style={isFirst || submitting ? { opacity: 0.4, cursor: "not-allowed" } : null}
          >
            {uiTexts.previous}
          </button>
        ) : null}
        <button
          type="button"
          className={"sd-btn " + (isLast ? "sd-navigation__complete-btn" : "sd-navigation__next-btn")}
          onClick={onNext}
          disabled={submitting}
        >
          {submitting ? uiTexts.submitting : (isLast ? uiTexts.submit : uiTexts.nextSection)}
        </button>
      </div>
    </div>
  );
}

/* ─── Completed / Closed ──────────────────────────────────────────────── */

function CompletedScreen({ surveyId, submittedAt, uiTexts, redirectUrl }) {
  useEffect(() => {
    if (redirectUrl) {
      const timer = setTimeout(() => { window.location.href = redirectUrl; }, 5000);
      return () => clearTimeout(timer);
    }
  }, [redirectUrl]);

  return (
    <div className="sd-completedpage">
      <div className="sd-completedpage__icon" aria-hidden="true">
        <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
          <path d="M5 11.5L9.5 16L17 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </div>
      <h2 className="sd-completedpage__title">{uiTexts.completedTitle}</h2>
      <p className="sd-completedpage__body">{uiTexts.completedBody}</p>
      {(surveyId || submittedAt) ? (
        <dl className="sd-completedpage__meta">
          {surveyId ? <div><dt>Response ID</dt><dd>{surveyId}</dd></div> : null}
          {submittedAt ? <div><dt>Submitted</dt><dd>{submittedAt}</dd></div> : null}
        </dl>
      ) : null}
      {redirectUrl && (
        <p className="sd-completedpage__redirect">
          You will be redirected in 5 seconds. <a href={redirectUrl}>Click here</a> if not redirected.
        </p>
      )}
      <div className="siamang-celebration" aria-hidden="true">
        {Array.from({ length: 20 }, (_, i) => (
          <span key={i} className="siamang-confetti" style={{
            left: Math.random() * 100 + "%",
            animationDelay: Math.random() * 2 + "s",
            animationDuration: (2 + Math.random() * 3) + "s",
            backgroundColor: ["#2c5f8a", "#e78ab8", "#7ed99a", "#f5c66e", "#b78af5"][i % 5],
            width: (6 + Math.random() * 6) + "px",
            height: (6 + Math.random() * 6) + "px",
          }} />
        ))}
      </div>
    </div>
  );
}

function ClosedScreen({ reason }) {
  const messages = {
    quota_full: { title: "Thank you for your interest", body: "We have already reached our target sample for participants like you." },
    deadline: { title: "Survey closed", body: "Thank you. This survey is no longer accepting responses." },
    error: { title: "Submission error", body: "We could not save your responses. Please refresh and try again." },
    closed: { title: "Survey closed", body: "This survey is no longer accepting responses." },
  };
  const m = messages[reason] || messages.closed;
  return (
    <div className="siamang-closed">
      <div className="siamang-closed__icon" aria-hidden="true">
        <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
          <circle cx="11" cy="11" r="8" stroke="currentColor" strokeWidth="1.6"/>
          <path d="M11 6.5V11.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
          <circle cx="11" cy="14.6" r="0.9" fill="currentColor"/>
        </svg>
      </div>
      <h2 className="siamang-closed__title">{m.title}</h2>
      <p className="siamang-closed__body">{m.body}</p>
    </div>
  );
}

/* ─── App ──────────────────────────────────────────────────────────────── */

function App() {
  const ui = window.SURVEY || {};
  const allPages = window.PAGES || [];
  const surveyId = ui.surveyId || "siamang_survey";

  // ─── Answers Store (replaces useState for form values) ───
  const store = useMemo(() => {
    const initial = { __options__: extractOptions(allPages), __pages__: allPages };
    return createAnswersStore(initial);
  }, []);
  const storeRef = useRef(store);
  storeRef.current = store;

  // ─── Visibility Engine ───
  const visibilityEngine = useVisibilityEngine(allPages, store);

  // ─── Theme ───
  const { theme, toggle: toggleTheme } = useTheme(ui.defaultTheme);

  // ─── Navigation ───
  const pageIdxRef = useRef(0);
  const nav = useSurveyNav(allPages, store, visibilityEngine);
  pageIdxRef.current = nav.pageIdx;

  // ─── Autosave ───
  const { saving, savedData, setSavedData, scheduleSave, clearSaved, saveNow } = useAutosave(store, surveyId, pageIdxRef);

  // ─── Submission ───
  const { phase, setPhase, submitting, setSubmitting, submitId, submittedAt, submitAttempts, submit } = useSubmission(store, clearSaved);
  const phaseRef = useRef(phase);
  phaseRef.current = phase;

  // ─── Errors / Touched ───
  const [errors, setErrors] = useState({});
  const errorsRef = useRef(errors);
  errorsRef.current = errors;

  // ─── Access Code ───
  const [accessGranted, setAccessGranted] = useState(!(ui.requireAccessCode && ui.accessCodes));
  const [accessCode, setAccessCode] = useState("");
  const [accessError, setAccessError] = useState(false);

  // ─── Initializing ───
  const [initializing, setInitializing] = useState(true);
  useEffect(() => { setInitializing(false); }, []);
  useEffect(() => {
    if (!initializing && nav.pages.length > 0) {
      ScriptRunner.runOnInit(store.snapshot());
    }
  }, [initializing]);

  // ─── UI Texts ───
  const uiTexts = useMemo(() => ({
    nextSection: ui.nextButtonText || "Next section \u2192",
    previous: ui.prevButtonText || "\u2190 Previous",
    submit: ui.submitButtonText || "Submit responses",
    submitting: ui.submittingText || "Submitting your responses\u2026",
    required: ui.requiredText || "This question requires an answer.",
    saving: ui.savingText || "Saving\u2026",
    resumeTitle: ui.resumeTitle || "We saved your progress from earlier. Would you like to resume?",
    resumeAction: ui.resumeAction || "Resume",
    restartAction: ui.restartAction || "Start over",
    page: ui.pageText || "Page",
    of_total: ui.ofTotalText || "of",
    retryTitle: ui.retryTitle || "Submission failed",
    retryBody: ui.retryBody || "We could not save your responses.",
    retryAction: ui.retryAction || "Try again",
    saveLocalAction: ui.saveLocalAction || "Save locally and finish",
    completedTitle: ui.completedTitle || "Thank you for participating",
    completedBody: ui.completedBody || "Your responses help inform open research.",
  }), []);

  // ─── Stable setAnswer callback ───
  const setAnswer = useCallback((id, val) => {
    store.set(id, val);
    setTimeout(() => ScriptRunner.run("onAnswer", store.snapshot(), {}, id), 0);
    scheduleSave();
    if (errorsRef.current[id]) {
      setErrors((prev) => { const n = { ...prev }; delete n[id]; return n; });
    }
  }, [store, scheduleSave]);

  // ─── Stable handleBlur ───
  const handleBlur = useCallback((questionId) => {
    const page = nav.pages[pageIdxRef.current];
    if (!page) return;
    const answers = store.snapshot();
    const items = visibilityEngine.visibleItems(page, answers);
    const q = items.find((item) => item.id === questionId);
    if (q && q.required && !isAnswered(q, answers[q.id])) {
      setErrors((prev) => ({ ...prev, [q.id]: uiTexts.required }));
    }
  }, [store, visibilityEngine, nav.pages, uiTexts.required]);

  // ─── handleNext with validation ───
  const handleNext = useCallback(() => {
    const answers = store.snapshot();
    const page = nav.pages[pageIdxRef.current];
    if (!page) return;
    const items = visibilityEngine.visibleItems(page, answers);
    const errs = {};
    for (const q of items) {
      if (q.required && !isAnswered(q, answers[q.id])) {
        errs[q.id] = uiTexts.required;
      }
    }
    if (Object.keys(errs).length > 0) {
      setErrors(errs);
      requestAnimationFrame(() => {
        const el = document.querySelector(".sd-question.has-error");
        if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
      });
      return;
    }
    setErrors({});
    if (nav.isLast) {
      setSubmitting(true);
      submit();
      return;
    }
    nav.goNext();
  }, [store, nav, visibilityEngine, uiTexts.required, submit, setSubmitting]);

  const handlePrev = useCallback(() => {
    setErrors({});
    nav.goPrev();
  }, [nav]);

  // ─── Keyboard + Touch + BeforeUnload ───
  const navRef = useRef({ onNext: handleNext, onPrev: handlePrev, isFirst: nav.isFirst, currentPage: nav.currentPage });
  navRef.current = { onNext: handleNext, onPrev: handlePrev, isFirst: nav.isFirst, currentPage: nav.currentPage };
  useKeyboardShortcuts(navRef, storeRef, visibilityEngine);
  useBeforeUnload(storeRef, phaseRef);
  const { handleTouchStart, handleTouchEnd } = useTouchGestures(handleNext, handlePrev, ui.allowBack !== false);

  // ─── Question numbering ───
  const qStart = nav.pages.slice(0, nav.pageIdx)
    .reduce((acc, p) => acc + visibilityEngine.visibleItems(p, store.snapshot()).length, 0);

  const showProgress = ui.showProgress !== false;
  const progressStyle = ui.progressStyle || "bar";

  // ─── Access gate ───
  if (ui.requireAccessCode && !accessGranted) {
    const verifyAccess = () => {
      const codes = ui.accessCodes || [];
      if (codes.includes(accessCode.trim())) {
        setAccessGranted(true);
        setAccessError(false);
      } else {
        setAccessError("Invalid access code. Please try again.");
      }
    };
    return (
      <div id="survey">
        <div className="siamang-access-gate">
          <h2 className="siamang-access-gate__title">{ui.accessTitle || "Access required"}</h2>
          <p className="siamang-access-gate__body">{ui.accessBody || "Please enter the access code to begin this survey."}</p>
          <div className="siamang-access-gate__form">
            <input type="text" className="sd-input" value={accessCode} onChange={(e) => setAccessCode(e.target.value)} placeholder={ui.accessPlaceholder || "Enter access code"} onKeyDown={(e) => { if (e.key === "Enter") verifyAccess(); }} />
            <button className="sd-btn sd-navigation__next-btn" onClick={verifyAccess} disabled={!accessCode}>{ui.accessButton || "Continue"}</button>
            {accessError && <div className="sd-question__error" role="alert">{accessError}</div>}
          </div>
        </div>
      </div>
    );
  }

  // ─── Closed / Completed ───
  if (phase === "closed") {
    return (
      <>
        <a className="siamang-skip-link" href="#surveyContainer">Skip to questionnaire</a>
        <div id="survey"><Header /><main id="surveyContainer" role="main"><ClosedScreen reason="closed" /></main><Footer /></div>
      </>
    );
  }

  if (phase === "completed") {
    return (
      <>
        <a className="siamang-skip-link" href="#surveyContainer">Skip to questionnaire</a>
        <div id="survey"><Header /><main id="surveyContainer" role="main"><CompletedScreen surveyId={submitId} submittedAt={submittedAt} uiTexts={uiTexts} redirectUrl={ui.redirectUrl} /></main><Footer /></div>
      </>
    );
  }

  // ─── Main survey render ───
  return (
    <>
      <a className="siamang-skip-link" href="#surveyContainer">Skip to questionnaire</a>
      <div id="survey" onTouchStart={handleTouchStart} onTouchEnd={handleTouchEnd}>
        <Header />
        {savedData && (
          <div className="siamang-resume-banner" role="alert">
            <span>{uiTexts.resumeTitle}</span>
            <div className="siamang-resume-banner__actions">
              <button className="sd-btn sd-navigation__next-btn" onClick={() => {
                store.replace(savedData.answers);
                nav.setPageIdx(savedData.pageIdx);
                setSavedData(null);
              }}>{uiTexts.resumeAction}</button>
              <button className="sd-btn sd-navigation__prev-btn" onClick={() => {
                clearSaved();
              }}>{uiTexts.restartAction}</button>
            </div>
          </div>
        )}
        {showProgress ? (
          <div className="siamang-progress" role="status" aria-live="polite">
            <span className="siamang-progress__bar" aria-hidden="true">
              <span className="siamang-progress__fill" style={{ width: nav.progressPct + "%" }}></span>
            </span>
            <span className="siamang-progress__text">
              {nav.currentPage && nav.currentPage.section
                ? nav.currentPage.section
                : `${uiTexts.page} ${nav.pageIdx + 1} ${uiTexts.of_total} ${nav.totalPages}`}
            </span>
          </div>
        ) : null}
        {(progressStyle === "dots" || progressStyle === "both") && (
          <nav className="siamang-step-dots" aria-label="Survey progress">
            {nav.pages.map((p, i) => (
              <button key={i} type="button"
                className={"siamang-step-dot" + (i === nav.pageIdx ? " is-active" : "") + (i < nav.pageIdx ? " is-complete" : "")}
                aria-label={`${p.title || "Page " + (i + 1)}${i === nav.pageIdx ? " (current)" : ""}`}
                onClick={() => {
                  if (ui.allowBack === false && i < nav.pageIdx) return;
                  nav.goTo(i);
                }}
                disabled={submitting || (ui.allowBack === false && i < nav.pageIdx)}
              />
            ))}
          </nav>
        )}
        {saving && (
          <div className="siamang-saving-indicator" aria-live="polite" role="status">
            <span className="siamang-saving-indicator__dot"></span>
            {uiTexts.saving}
          </div>
        )}
        <div className="siamang-announce" role="status" aria-live="polite" aria-atomic="true" style={{ position: "absolute", width: "1px", height: "1px", overflow: "hidden", clip: "rect(0,0,0,0)" }}>
          {nav.currentPage ? `${uiTexts.page} ${nav.pageIdx + 1} ${uiTexts.of_total} ${nav.totalPages}` : ""}
        </div>
        <main id="surveyContainer" role="main" aria-label={ui.title || "Questionnaire"}>
          {initializing && (
            <div className="siamang-skeleton" aria-label="Loading survey">
              <div className="siamang-skeleton__header"><div className="siamang-skeleton__line siamang-skeleton__line--title"></div></div>
              <div className="siamang-skeleton__card">
                <div className="siamang-skeleton__line siamang-skeleton__line--heading"></div>
                <div className="siamang-skeleton__line"></div>
                <div className="siamang-skeleton__line siamang-skeleton__line--short"></div>
                <div style={{ height: 12 }}></div>
                <div className="siamang-skeleton__line"></div>
                <div className="siamang-skeleton__line siamang-skeleton__line--medium"></div>
              </div>
            </div>
          )}
          <div className={nav.transitionDir ? "siamang-page-enter" : ""}>
            {nav.currentPage ? (
              <ErrorBoundary>
                <SurveyPage
                  page={nav.currentPage}
                  store={store}
                  visibilityEngine={visibilityEngine}
                  setAnswer={setAnswer}
                  errors={errors}
                  onNext={handleNext}
                  onPrev={handlePrev}
                  isFirst={nav.isFirst}
                  isLast={nav.isLast}
                  qStart={qStart}
                  submitting={submitting}
                  handleBlur={handleBlur}
                  uiTexts={uiTexts}
                />
              </ErrorBoundary>
            ) : null}
          </div>
          {submitting && (
            <div className="siamang-loading-overlay" role="alert" aria-live="assertive">
              <div className="siamang-loading-overlay__spinner"><div className="siamang-spinner"></div></div>
              <p className="siamang-loading-overlay__text">{uiTexts.submitting}</p>
            </div>
          )}
        </main>
        {submitAttempts > 0 && submitAttempts < 3 && (
          <div className="siamang-retry-overlay" role="dialog" aria-modal="true" aria-label="Submission failed">
            <div className="siamang-retry-dialog">
              <div className="siamang-retry-dialog__icon" aria-hidden="true">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.5"/>
                  <path d="M12 7v5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                  <circle cx="12" cy="16" r="0.8" fill="currentColor"/>
                </svg>
              </div>
              <h3 className="siamang-retry-dialog__title">{uiTexts.retryTitle}</h3>
              <p className="siamang-retry-dialog__body">{uiTexts.retryBody} Attempt {submitAttempts} of 3.</p>
              <div className="siamang-retry-dialog__actions">
                <button className="sd-btn sd-navigation__next-btn" onClick={() => submit(true)}>{uiTexts.retryAction}</button>
                <button className="sd-btn sd-navigation__prev-btn" onClick={() => { saveNow(); setPhase("completed"); }}>{uiTexts.saveLocalAction}</button>
              </div>
            </div>
          </div>
        )}
        <Footer />
        <div className="siamang-footer__row" style={{ justifyContent: "center", marginTop: 12 }}>
          <button type="button" className="siamang-theme-toggle" onClick={toggleTheme} aria-label={`Switch to ${theme === "light" ? "dark" : "light"} mode`}>
            {theme === "light" ? "\uD83C\uDF19" : "\u2600\uFE0F"}
          </button>
        </div>
      </div>
    </>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <AppErrorBoundary><App /></AppErrorBoundary>
);
