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
  /* A MaxDiff fills one object over several screens, so "has any key" would
     call it answered after the first task. Every task needs both picks, or the
     design has holes where the analysis expects comparisons. */
  if (q && q.kind === "maxdiff") return maxDiffRemaining(q, v) === 0;
  /* Same reason: a conjoint fills one object over several tasks, and every task
     needs a choice or the design has holes where comparisons were expected. */
  if (q && q.kind === "conjoint") {
    return (q.taskVars || []).every((name) => v && v[name] !== undefined);
  }
  if (typeof v === "object") return Object.keys(v).length > 0;
  return true;
}

/* How many of a MaxDiff's tasks are still missing a best or a worst. */
function maxDiffRemaining(q, v) {
  const answers = v || {};
  let left = 0;
  for (const [best, worst] of q.taskVars || []) {
    if (answers[best] === undefined || answers[worst] === undefined) left += 1;
  }
  return left;
}

/* An OpenText with a format (email, phone, url, date, time) refuses a value
   that does not look like one — the browser input already steers the
   respondent, this is the check that holds on "Next". */
const TEXT_FORMAT_RE = {
  email: /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/,
  phone: /^\+?[0-9][0-9\s().-]{5,}$/,
  url: /^https?:\/\/[^\s]+\.[^\s]+$/i,
  date: /^\d{4}-\d{2}-\d{2}$/,
  time: /^\d{2}:\d{2}(:\d{2})?$/,
};
function textFormatError(q, v, texts) {
  if (!q || q.kind !== "text" || !q.format || q.format === "text") return null;
  if (v === undefined || v === null || v === "") return null;
  const re = TEXT_FORMAT_RE[q.format];
  if (!re || re.test(String(v).trim())) return null;
  if (q.format === "date" && !isNaN(Date.parse(String(v)))) return null;
  return (texts && texts.formats && texts.formats[q.format]) || (texts && texts.invalidFormat) || "Please check the format of your answer.";
}

function extractOptions(pages) {
  const opts = {};
  const collect = (items) => {
    for (const q of items || []) {
      if (q && q.options) opts[q.id] = q.options;
    }
  };
  for (const p of pages) {
    collect(p.items);
    for (const b of p.blocks || []) collect(b.items);
  }
  return opts;
}

/* ─── Author-declared randomization (Question.randomize, Block.randomize,
   Page.randomize_blocks) ─────────────────────────────────────────────────
   Applied once per respondent at load time; the shuffled option order is
   captured into answers.__options__ via extractOptions() afterwards. */

function applyRandomization(pages) {
  let touched = false;
  const shuffle = (arr) => {
    const a = [...arr];
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  };
  const mapQ = (q) => {
    if (q && q.randomize && Array.isArray(q.options) && q.options.length > 1) {
      touched = true;
      return { ...q, options: shuffle(q.options) };
    }
    return q;
  };
  const out = pages.map((p) => {
    if (Array.isArray(p.items)) {
      return { ...p, items: p.items.map(mapQ) };
    }
    if (Array.isArray(p.blocks)) {
      let blocks = p.blocks.map((b) => {
        let items = (b.items || []).map(mapQ);
        if (b.randomize && items.length > 1) {
          touched = true;
          items = shuffle(items);
        }
        return { ...b, items };
      });
      if (p.randomizeBlocks) {
        // Shuffle only real authored blocks among their own slots; wrappers
        // holding standalone questions keep their positions.
        const slots = blocks.map((b, i) => (b.isBlock ? i : -1)).filter((i) => i >= 0);
        if (slots.length > 1) {
          touched = true;
          const shuffled = shuffle(slots.map((i) => blocks[i]));
          const next = [...blocks];
          slots.forEach((slot, k) => { next[slot] = shuffled[k]; });
          blocks = next;
        }
      }
      return { ...p, blocks };
    }
    return p;
  });
  return { pages: out, touched };
}

/* ─── ScriptRunner ──────────────────────────────────────────────────── */

// `new Function` compiles a sync body; scripts need `await`, and the async
// constructor is not a global.
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;

// How long the first page waits on an awaiting onInit script before showing
// anyway. The script has already written its offline fallback, so a slow or
// dead backend costs a moment and a little balance, never the session.
const INIT_AWAIT_TIMEOUT_MS = 2000;

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
    // Which of `values` is the least-full open quota cell of `variable`, as
    // the backend sees it across every respondent so far. The URL and its
    // credentials differ per backend, so this goes through the transport
    // rather than being built here. Returns null whenever there is no usable
    // answer — no transport (offline preview, static export), no quota on
    // this variable, or every cell full — and the caller keeps its own draw.
    pickQuota: async (variable, values) => {
      const env = window.SIAMANG_ENV || window.SURVLIB_ENV || {};
      const transport = (window.SIAMANG_TRANSPORTS || window.SURVLIB_TRANSPORTS || {})[env.transport];
      if (!transport || typeof transport.pickQuota !== "function") return null;
      try {
        const res = await transport.pickQuota(variable, values);
        if (!res || res.ok === false || res.value === undefined || res.value === null) return null;
        return res.value;
      } catch (e) { return null; }
    },
  },

  // Set once by App; lets script writes into `answers` flow back into the
  // reactive store (scripts receive a mutable working copy, see below).
  _store: null,

  /** One-level-deep copy, so a script mutating a nested object is visible. */
  _copy(src) {
    const out = { ...src };
    for (const k of Object.keys(out)) {
      const v = out[k];
      if (Array.isArray(v)) out[k] = [...v];
      else if (v && typeof v === "object") out[k] = { ...v };
    }
    return out;
  },

  _differs(a, b) {
    if (a === b) return false;
    if (a && typeof a === "object" && b && typeof b === "object") {
      try { return JSON.stringify(a) !== JSON.stringify(b); }
      catch (e) { return true; /* unserializable (e.g. timer handles) */ }
    }
    return true;
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
    if (!matching.length) return;

    // Scripts mutate `answers` (including nested objects such as
    // __errors__ / __options__ / __pages__). Hand them a one-level-deep
    // working copy of the live store state, then sync changes back so the
    // UI reacts and later triggers observe the writes.
    const store = ScriptRunner._store;
    let work = answers;
    let base = null;
    if (store) {
      base = store.snapshot();
      work = ScriptRunner._copy(base);
    }

    // Scripts are compiled as async functions so a body may `await` (a
    // balanced assignment asks the backend which arm is furthest behind).
    // Everything before the first `await` still runs synchronously inside
    // this call, so a script that never awaits behaves exactly as before.
    const pending = [];
    for (const script of matching) {
      try {
        const fn = new AsyncFunction("answers", "utils", "api", "context", script.code);
        const result = fn(work, ScriptRunner._utils, ScriptRunner._api, { ...script.context, ...context });
        if (result && typeof result.then === "function") {
          pending.push(result.catch((err) => {
            console.warn(`siamang Script error [${script.name || script.trigger}]:`, err);
          }));
        }
      } catch (err) {
        console.warn(`siamang Script error [${script.name || script.trigger}]:`, err);
      }
    }

    // Sync writes land now, exactly as before. Anything a script writes after
    // an await lands in a second pass — but only the keys it actually touched
    // after the first pass: `work` is a copy taken before the scripts ran, so
    // blindly re-applying all of it would undo whatever else wrote to the
    // store while we were awaiting (the onRandomize run that follows onInit
    // reorders `__pages__`, for one).
    const flush = (since) => {
      if (!store || !base) return;
      const now = store.snapshot();
      const updates = {};
      for (const k of Object.keys(work)) {
        if (since && !ScriptRunner._differs(work[k], since[k])) continue;
        if (!ScriptRunner._differs(work[k], now[k])) continue;
        updates[k] = work[k];
      }
      if (Object.keys(updates).length) store.setMany(updates);
    };
    flush(null);
    if (!pending.length) return null;
    // Taken synchronously: an awaiting script is suspended at its first
    // `await`, so nothing has resumed yet.
    const afterSync = ScriptRunner._copy(work);
    return Promise.all(pending).then(() => flush(afterSync));
  },

  runForQuestion(questionId, answers) { ScriptRunner.run("onQuestionShow", answers, {}, questionId); },
  runForPage(pageName, answers) { ScriptRunner.run("onPageEnter", answers, {}, pageName); },
  runOnInit(answers) { return ScriptRunner.run("onInit", answers); },
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
        {ui.title && ui.showTitle !== false ? <h1 className="siamang-header__title">{ui.title}</h1> : null}
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

/* ─── Design mode (Studio preview) ────────────────────────────────────────
   Enabled when the host page sets window.SIAMANG_DESIGN before the bundle
   loads. The runtime then talks to its parent frame by postMessage:
     host → runtime  {type:"siamang:goto", page: <name|index>}
                     {type:"siamang:select", id: <question id|null>}
     runtime → host  {type:"siamang:page", name, index, total}
                     {type:"siamang:select", id, page}     (a click on a question)
   Nothing else changes: the survey behaves exactly as respondents see it. */
/* Walkthrough trace (Studio's Test tab): what the logic decided on the
   current page for the current answers — which gated questions/blocks are
   visible, which next_if rules match, which skip_to would fire, and where
   "Next" lands. Posted to the parent as `siamang:trace` on every page
   change and (debounced) on every answer change. */
function buildDesignTrace(page, index, answers, visibilityEngine) {
  const items = [];
  const blocks = [];
  if (page.items) {
    for (const q of page.items) items.push({ q, block: null });
  } else if (page.blocks) {
    for (const b of page.blocks) {
      const gated = b.showIf != null || b.hideIf != null;
      const visible = isConditionVisible(b.showIf, b.hideIf, answers);
      if (gated) blocks.push({ title: b.title || null, visible: visible, showIf: b.showIf != null, hideIf: b.hideIf != null });
      for (const q of b.items || []) items.push({ q, block: visible ? null : (b.title || "block") });
    }
  }
  const conditions = [];
  const skips = [];
  let answered = 0;
  let visibleCount = 0;
  for (const { q, block } of items) {
    const qid = q.qid || q.id;
    const gated = q.showIf != null || q.hideIf != null;
    const visible = block == null && isConditionVisible(q.showIf, q.hideIf, answers);
    if (gated) conditions.push({ id: qid, visible: visible, showIf: q.showIf != null, hideIf: q.hideIf != null, hiddenByBlock: block });
    if (visible) {
      visibleCount += 1;
      const done = isAnswered(q, itemValue(q, answers));
      if (done) answered += 1;
      if (q.skipTo) skips.push({ id: qid, target: q.skipTo, answered: done });
    }
  }
  const rules = (page.nextIf || []).map((r, i) => ({ index: i, target: r.target, matched: evaluateRouteCondition(r.if, answers) }));
  const route = computeRouteTarget(page, answers, visibilityEngine);
  return {
    page: page.name, index: index, kind: page.kind || "content",
    conditions: conditions, blocks: blocks, rules: rules, skips: skips,
    defaultNext: page.defaultNext || null, route: route,
    visible: visibleCount, answered: answered,
  };
}

/* Where the respondent is, told to the transport that asked for it.
   A transport may expose an optional onPage({ name, index, total }); when it
   does, it is called on every page change. The runtime sends nothing and
   stores nothing itself, and a transport without the hook behaves exactly as
   before — so a hosted survey can record how far people get without the
   questionnaire knowing what a host is, and a questionnaire.py run from
   someone's own machine keeps working unchanged. Failures are swallowed:
   telemetry must never cost a respondent their answers. */
function useTransportPage(nav) {
  const pageName = nav.currentPage ? nav.currentPage.name : null;
  const index = nav.pageIdx;
  const total = nav.pages.length;
  useEffect(() => {
    if (!pageName) return;
    try {
      const env = window.SIAMANG_ENV || window.SURVLIB_ENV || {};
      const transport = (window.SIAMANG_TRANSPORTS || window.SURVLIB_TRANSPORTS || {})[env.transport];
      if (transport && typeof transport.onPage === "function") {
        transport.onPage({ name: pageName, index: index, total: total });
      }
    } catch (e) { /* a transport must not be able to break the survey */ }
  }, [pageName, index, total]);
}

function useDesignMode(nav, store, visibilityEngine, allPages) {
  const enabled = typeof window !== "undefined" && !!window.SIAMANG_DESIGN;
  const selectable = enabled && window.SIAMANG_DESIGN.select !== false;
  const [selectedId, setSelectedId] = useState(null);
  const post = useCallback((msg) => {
    try { window.parent.postMessage(Object.assign({ source: "siamang-runtime" }, msg), "*"); } catch (e) { /* no parent */ }
  }, []);
  const navRef = useRef(nav);
  navRef.current = nav;
  const pageName0 = nav.currentPage ? nav.currentPage.name : null;
  useEffect(() => {
    if (!enabled || !store || !visibilityEngine) return undefined;
    let timer = null;
    const emit = () => {
      timer = null;
      const n = navRef.current;
      if (!n.currentPage) return;
      try {
        const answers = store.snapshot();
        // Document order (scripts may reorder it via answers.__pages__); the
        // nav's `pages` are the currently visible ones.
        const ordered = Array.isArray(answers.__pages__) && answers.__pages__.length ? answers.__pages__ : (allPages || n.pages);
        const cur = ordered.findIndex((p) => p.name === n.currentPage.name);
        const nextVisible = n.pages[n.pageIdx + 1] ? n.pages[n.pageIdx + 1].name : null;
        const skipped = [];
        if (cur >= 0) {
          for (let i = cur + 1; i < ordered.length; i++) {
            const p = ordered[i];
            if (p.name === nextVisible) break;
            if (p.showIf != null || p.hideIf != null) skipped.push({ name: p.name, showIf: p.showIf != null, hideIf: p.hideIf != null });
          }
        }
        const trace = buildDesignTrace(n.currentPage, cur >= 0 ? cur : n.pageIdx, answers, visibilityEngine);
        post(Object.assign({ type: "siamang:trace", next: nextVisible, skipped: skipped, position: n.pageIdx + 1, total: n.pages.length }, trace));
      } catch (e) { /* a trace must never break the survey */ }
    };
    emit();
    const unsubscribe = store.subscribe(() => { if (timer) clearTimeout(timer); timer = setTimeout(emit, 60); });
    return () => { if (timer) clearTimeout(timer); unsubscribe(); };
  }, [enabled, store, visibilityEngine, pageName0, post]);
  useEffect(() => {
    if (!enabled) return undefined;
    const onMessage = (e) => {
      const d = e.data;
      if (!d || typeof d !== "object" || typeof d.type !== "string") return;
      if (d.type === "siamang:goto") {
        const pages = navRef.current.pages;
        const idx = typeof d.page === "number" ? d.page : pages.findIndex((p) => p.name === d.page);
        if (idx >= 0 && idx < pages.length && idx !== navRef.current.pageIdx) navRef.current.goTo(idx);
      } else if (d.type === "siamang:select") {
        setSelectedId(d.id || null);
      }
    };
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [enabled]);
  const pageName = nav.currentPage ? nav.currentPage.name : null;
  useEffect(() => {
    if (enabled && pageName) post({ type: "siamang:page", name: pageName, index: nav.pageIdx, total: nav.pages.length });
  }, [enabled, pageName, nav.pageIdx, nav.pages.length, post]);
  const onSelect = useCallback((id) => {
    if (!selectable) return;
    setSelectedId(id);
    post({ type: "siamang:select", id: id, page: navRef.current.currentPage ? navRef.current.currentPage.name : null });
  }, [post, selectable]);
  return { enabled, selectable, selectedId, onSelect };
}

function SurveyPage({ page, store, visibilityEngine, setAnswer, errors, onNext, onPrev, isFirst, isLast, totalQuestions, qStart, submitting, checking, handleBlur, uiTexts, design }) {
  // While a quota check runs the buttons wait; the page itself stays as it is.
  const busy = submitting || checking;
  const answers = useAnswersStore(store);
  let qNum = qStart;

  const renderItem = (q) => {
    if (!visibilityEngine.isItemVisible(q, answers)) return null;
    qNum += 1;
    const qid = q.qid || q.id;
    const selected = design && design.enabled && design.selectedId === qid;
    return (
      <div
        key={q.id}
        className={"sd-question-slot" + (selected ? " is-design-selected" : "")}
        data-qid={qid}
        onClickCapture={design && design.selectable ? () => design.onSelect(qid) : undefined}
      >
        <ErrorBoundary>
          <Question
            q={q}
            qId={q.id}
            value={itemValue(q, answers)}
            setAnswer={setAnswer}
            num={"Q" + String(qNum).padStart(2, "0")}
            error={errors[q.id]}
            handleBlur={handleBlur}
            answers={answers}
            onAutoAdvance={onNext}
          />
        </ErrorBoundary>
      </div>
    );
  };

  return (
    <div className="sd-page">
      {page.section ? <div className="sd-page__eyebrow">{page.section}</div> : null}
      {page.title ? <h2 className="sd-page__title">{processPipedText(page.title, answers)}</h2> : null}
      {page.description ? <p className="sd-page__description">{processPipedText(page.description, answers)}</p> : null}

      {/* A page's body is HTML shown above its questions — on a content page,
          which usually has none, it is the page. It used to be rendered for
          engine-kind "content" pages only, so an ordinary page's introduction
          never reached the respondent. */}
      {page.body
        ? <div className="sd-page__html sd-page__body" dangerouslySetInnerHTML={{ __html: processPipedHtml(page.body, answers) }} />
        : null}
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
            disabled={isFirst || busy}
            style={isFirst || busy ? { opacity: 0.4, cursor: "not-allowed" } : null}
          >
            {uiTexts.previous}
          </button>
        ) : null}
        <button
          type="button"
          className={"sd-btn " + (isLast ? "sd-navigation__complete-btn" : "sd-navigation__next-btn")}
          onClick={onNext}
          disabled={busy}
          aria-busy={checking ? "true" : undefined}
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

function ClosedScreen({ reason, redirectUrl }) {
  // A panel's quota-full return: send the respondent back once the notice showed.
  useEffect(() => {
    if (!redirectUrl) return;
    const t = setTimeout(() => { window.location.href = redirectUrl; }, 3000);
    return () => clearTimeout(t);
  }, [redirectUrl]);
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
      {redirectUrl ? (
        <p className="sd-completedpage__redirect">
          Redirecting you now. <a href={redirectUrl}>Continue</a> if you are not redirected.
        </p>
      ) : null}
    </div>
  );
}

/* ─── Terminal pages (disqualification / final / redirect) ─────────────── */

function TerminalScreen({ page, store, submit, phase, submitId, submittedAt, uiTexts }) {
  const firedRef = useRef(false);
  // The page's own redirect, else the survey's default for this outcome
  // (screen-out or completion); {url:NAME} and piped answers filled in.
  const ui = window.SURVEY || {};
  const fallback = page.kind === "disqualification" ? ui.screenOutRedirectUrl : ui.redirectUrl;
  const redirectUrl = useMemo(() => redirectTemplate(page.redirectUrl || fallback || null, store.snapshot()), [page.redirectUrl, fallback]);
  const delayMs = (page.redirectDelay != null ? page.redirectDelay : 5) * 1000;

  // Record the response once when the respondent reaches a terminal page.
  // Disqualification pages are flagged screened-out in the stored payload.
  useEffect(() => {
    if (firedRef.current) return;
    firedRef.current = true;
    const status = page.kind === "disqualification" ? "screened_out"
      : page.kind === "redirect" ? "redirect" : "completed";
    try { store.set("__status", status); } catch (e) {}
    submit();
  }, []);

  // Redirect (if configured) once the response is safely recorded.
  useEffect(() => {
    if (redirectUrl && phase === "completed") {
      const t = setTimeout(() => { window.location.href = redirectUrl; }, delayMs);
      return () => clearTimeout(t);
    }
  }, [redirectUrl, phase, delayMs]);

  const screenedOut = page.kind === "disqualification";
  const wrapCls = screenedOut ? "siamang-closed" : "sd-completedpage";
  const titleCls = screenedOut ? "siamang-closed__title" : "sd-completedpage__title";
  const bodyCls = screenedOut ? "siamang-closed__body" : "sd-completedpage__body";
  // The last page pipes answers like every other one ({answer:x}, {label:x}):
  // the answers are final by now.
  const answers = store.snapshot();
  return (
    <div className={wrapCls}>
      <h2 className={titleCls}>{processPipedText(page.title, answers) || (screenedOut ? "Thank you" : uiTexts.completedTitle)}</h2>
      {page.body
        ? <div className={"sd-page__html " + bodyCls} dangerouslySetInnerHTML={{ __html: processPipedHtml(page.body, answers) }} />
        : <p className={bodyCls}>{uiTexts.completedBody}</p>}
      {(submitId || submittedAt) && !screenedOut ? (
        <dl className="sd-completedpage__meta">
          {submitId ? <div><dt>Response ID</dt><dd>{submitId}</dd></div> : null}
          {submittedAt ? <div><dt>Submitted</dt><dd>{submittedAt}</dd></div> : null}
        </dl>
      ) : null}
      {redirectUrl ? (
        <p className="sd-completedpage__redirect">
          Redirecting you now. <a href={redirectUrl}>Continue</a> if you are not redirected.
        </p>
      ) : null}
    </div>
  );
}

/* ─── App ──────────────────────────────────────────────────────────────── */

function App() {
  const ui = window.SURVEY || {};
  const surveyId = ui.surveyId || "siamang_survey";

  // ─── Author-declared randomization (applied once per respondent) ───
  const randomized = useMemo(() => applyRandomization(window.PAGES || []), []);
  const allPages = randomized.pages;
  // Every item by its id: an answer is handed over by the item's id and
  // stored under the variables the item writes (answerUpdates).
  const itemsById = useMemo(() => {
    const index = {};
    forEachItem(allPages, (q) => { if (q.id) index[q.id] = q; });
    return index;
  }, [allPages]);

  // ─── Answers Store (replaces useState for form values) ───
  const store = useMemo(() => {
    const initial = {
      __options__: extractOptions(allPages),
      __pages__: allPages,
      __errors__: {},
    };
    return createAnswersStore(initial);
  }, []);
  const storeRef = useRef(store);
  storeRef.current = store;
  ScriptRunner._store = store;

  // ─── Visibility Engine ───
  const visibilityEngine = useVisibilityEngine(allPages, store);

  // ─── Theme ───
  const { theme, toggle: toggleTheme } = useTheme(ui.defaultTheme, ui.allowThemeSwitch !== false, surveyId);

  // ─── Navigation ───
  const pageIdxRef = useRef(0);
  const nav = useSurveyNav(allPages, store, visibilityEngine);
  pageIdxRef.current = nav.pageIdx;

  // ─── Design mode (Studio preview only) ───
  const design = useDesignMode(nav, store, visibilityEngine, allPages);
  useTransportPage(nav);

  // ─── Autosave ───
  const { saving, savedData, setSavedData, scheduleSave, clearSaved, saveNow } = useAutosave(store, surveyId, pageIdxRef);

  // ─── Submission ───
  const { phase, setPhase, closedReason, setClosedReason, submitting, setSubmitting, submitId, submittedAt, submitAttempts, submit } = useSubmission(store, clearSaved);
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
  const initRanRef = useRef(false);
  useEffect(() => {
    if (!initializing || initRanRef.current) return;
    // Nothing to initialize against yet (or ever): drop the skeleton rather
    // than hold an empty questionnaire behind it.
    if (nav.pages.length === 0) { setInitializing(false); return; }
    initRanRef.current = true;
    const pending = ScriptRunner.runOnInit(store.snapshot());
    // Author-declared randomization ran at load; onInit scripts (e.g.
    // randomize_pages) may also have shuffled state. Fire onRandomize
    // so scripts can react to the final randomized state.
    ScriptRunner.run("onRandomize", store.snapshot());
    if (!pending) { setInitializing(false); return; }
    // An onInit script is still waiting on the backend — a balanced
    // assignment asking which arm is furthest behind. The respondent must not
    // see page 1 assigned one way and then watch it change, so the skeleton
    // stays up; the timeout guarantees it comes down regardless.
    let settled = false;
    let timer = null;
    const finish = () => {
      if (settled) return;
      settled = true;
      if (timer !== null) clearTimeout(timer);
      setInitializing(false);
    };
    timer = setTimeout(finish, INIT_AWAIT_TIMEOUT_MS);
    pending.then(finish, finish);
  }, [initializing, nav.pages.length]);

  // ─── onPageEnter / onQuestionShow lifecycle triggers ───
  const currentPageName = nav.currentPage ? nav.currentPage.name : null;
  const shownQuestionsRef = useRef(new Set());
  useEffect(() => {
    if (initializing || !currentPageName) return;
    ScriptRunner.run("onPageEnter", store.snapshot(), {}, currentPageName);
  }, [initializing, currentPageName]);
  useEffect(() => {
    if (initializing || !nav.currentPage) return;
    const answers = store.snapshot();
    const items = visibilityEngine.visibleItems(nav.currentPage, answers);
    for (const q of items) {
      if (!shownQuestionsRef.current.has(q.id)) {
        shownQuestionsRef.current.add(q.id);
        ScriptRunner.runForQuestion(q.id, store.snapshot());
      }
    }
  }, [initializing, currentPageName, visibilityEngine._sig]);

  // ─── UI Texts ───
  const uiTexts = useMemo(() => ({
    nextSection: ui.nextButtonText || "Next section \u2192",
    previous: ui.prevButtonText || "\u2190 Previous",
    submit: ui.submitButtonText || "Submit responses",
    submitting: ui.submittingText || "Submitting your responses\u2026",
    required: ui.requiredText || "This question requires an answer.",
    invalidFormat: ui.invalidFormatText || "Please check the format of your answer.",
    formats: {
      email: ui.invalidEmailText || "Please enter a valid email address.",
      phone: ui.invalidPhoneText || "Please enter a valid phone number.",
      url: ui.invalidUrlText || "Please enter a valid web address (https://…).",
      date: ui.invalidDateText || "Please enter a valid date.",
      time: ui.invalidTimeText || "Please enter a valid time.",
    },
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

  // ─── Script-written validation messages (answers.__errors__) ───
  const scriptErrors = useFieldValue(store, "__errors__") || {};

  // ─── Stable setAnswer callback ───
  const setAnswer = useCallback((id, val) => {
    const q = itemsById[id];
    store.setMany(q ? answerUpdates(q, val) : { [id]: val });
    // A change to the field invalidates any script-written message for it;
    // onAnswer scripts re-add it below if the problem persists.
    const se = store.get("__errors__");
    if (se && se[id] !== undefined) {
      const next = { ...se };
      delete next[id];
      store.set("__errors__", next);
    }
    setTimeout(() => ScriptRunner.run("onAnswer", store.snapshot(), {}, id), 0);
    scheduleSave();
    if (errorsRef.current[id]) {
      setErrors((prev) => { const n = { ...prev }; delete n[id]; return n; });
    }
  }, [store, scheduleSave, itemsById]);

  // ─── Stable handleBlur ───
  const handleBlur = useCallback((questionId) => {
    const page = nav.pages[pageIdxRef.current];
    if (!page) return;
    const answers = store.snapshot();
    const items = visibilityEngine.visibleItems(page, answers);
    const q = items.find((item) => item.id === questionId);
    if (q && q.required && !isAnswered(q, itemValue(q, answers))) {
      setErrors((prev) => ({ ...prev, [q.id]: uiTexts.required }));
      return;
    }
    const formatError = textFormatError(q, answers[q.id], uiTexts);
    if (formatError) setErrors((prev) => ({ ...prev, [q.id]: formatError }));
  }, [store, visibilityEngine, nav.pages, uiTexts]);

  // ─── Quotas (checked when a page is left) ───
  const quotaVars = useMemo(() => (Array.isArray(ui.quotaVars) ? ui.quotaVars : []), []);
  const quotaFull = useQuotaCheck(quotaVars);
  const [checking, setChecking] = useState(false);
  const leavingRef = useRef(false);

  // ─── handleNext with validation ───
  const handleNext = useCallback(() => {
    if (leavingRef.current) return;
    const answers = store.snapshot();
    const page = nav.pages[pageIdxRef.current];
    if (!page) return;
    const items = visibilityEngine.visibleItems(page, answers);
    const errs = {};
    const se = answers.__errors__ || {};
    for (const q of items) {
      const formatError = textFormatError(q, answers[q.id], uiTexts);
      if (q.required && !isAnswered(q, itemValue(q, answers))) {
        errs[q.id] = uiTexts.required;
      } else if (formatError) {
        errs[q.id] = formatError;
      } else if (se[q.id]) {
        // Script-written validation message blocks navigation too.
        errs[q.id] = se[q.id];
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
    const proceed = () => {
      if (nav.isLast) {
        setSubmitting(true);
        submit();
        return;
      }
      nav.goNext();
    };
    if (!quotaVars.length) { proceed(); return; }
    // A quota cell this respondent's answers fall into may be full: ask
    // before routing anywhere, the last page's submission included.
    leavingRef.current = true;
    setChecking(true);
    quotaFull(answers).then((full) => {
      leavingRef.current = false;
      setChecking(false);
      if (!full) { proceed(); return; }
      clearSaved();
      setClosedReason("quota_full");
      setPhase("closed");
    });
  }, [store, nav, visibilityEngine, uiTexts, submit, setSubmitting, quotaVars, quotaFull, clearSaved, setClosedReason, setPhase]);

  const handlePrev = useCallback(() => {
    if (leavingRef.current) return;
    setErrors({});
    nav.goPrev();
  }, [nav]);

  // Timed-question scripts auto-advance through this global hook.
  useEffect(() => {
    window.siamangNext = handleNext;
    return () => { if (window.siamangNext === handleNext) delete window.siamangNext; };
  }, [handleNext]);

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

  // ─── Terminal pages (disqualification / final / redirect) ───
  // When the respondent reaches a terminal page it ends the survey: record the
  // response (screened-out for disqualification) and show the page's content.
  const _cur = nav.currentPage;
  if (_cur && (_cur.kind === "disqualification" || _cur.kind === "final" || _cur.kind === "redirect")) {
    return (
      <>
        <a className="siamang-skip-link" href="#surveyContainer">Skip to questionnaire</a>
        <div id="survey"><Header /><main id="surveyContainer" role="main">
          <TerminalScreen page={_cur} store={store} submit={submit} phase={phase} submitId={submitId} submittedAt={submittedAt} uiTexts={uiTexts} />
        </main><Footer /></div>
      </>
    );
  }

  // ─── Closed / Completed ───
  if (phase === "closed") {
    return (
      <>
        <a className="siamang-skip-link" href="#surveyContainer">Skip to questionnaire</a>
        <div id="survey"><Header /><main id="surveyContainer" role="main"><ClosedScreen reason={closedReason || "closed"} redirectUrl={closedReason === "quota_full" ? redirectTemplate(ui.quotaFullRedirectUrl || null, store.snapshot()) : null} /></main><Footer /></div>
      </>
    );
  }

  if (phase === "completed") {
    return (
      <>
        <a className="siamang-skip-link" href="#surveyContainer">Skip to questionnaire</a>
        <div id="survey"><Header /><main id="surveyContainer" role="main"><CompletedScreen surveyId={submitId} submittedAt={submittedAt} uiTexts={uiTexts} redirectUrl={redirectTemplate(ui.redirectUrl || null, store.snapshot())} /></main><Footer /></div>
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
                // The runtime's own state (__pages__, __options__, …) stays;
                // the answers come back in today's layout.
                const internal = {};
                for (const [k, v] of Object.entries(store.snapshot())) if (k.startsWith("__")) internal[k] = v;
                store.replace({ ...internal, ...upgradeSavedAnswers(allPages, savedData.answers) });
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
            {nav.currentPage && !initializing ? (
              <ErrorBoundary>
                <SurveyPage
                  page={nav.currentPage}
                  store={store}
                  visibilityEngine={visibilityEngine}
                  setAnswer={setAnswer}
                  errors={{ ...scriptErrors, ...errors }}
                  onNext={handleNext}
                  onPrev={handlePrev}
                  isFirst={nav.isFirst}
                  isLast={nav.isLast}
                  qStart={qStart}
                  submitting={submitting}
                  checking={checking}
                  handleBlur={handleBlur}
                  uiTexts={uiTexts}
                  design={design}
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
        {ui.allowThemeSwitch !== false && (
          <div className="siamang-footer__row" style={{ justifyContent: "center", marginTop: 12 }}>
            <button type="button" className="siamang-theme-toggle" onClick={toggleTheme} aria-label={`Switch to ${theme === "light" ? "dark" : "light"} mode`}>
              {theme === "light" ? "\uD83C\uDF19" : "\u2600\uFE0F"}
            </button>
          </div>
        )}
      </div>
    </>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <AppErrorBoundary><App /></AppErrorBoundary>
);
