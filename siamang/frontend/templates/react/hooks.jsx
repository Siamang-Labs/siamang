/* siamang React hooks — modular concerns extracted from the App monolith.
   Each hook owns its own state, effects, and contract. */

/* ─── useTheme ─────────────────────────────────────────────────────────── */

function useTheme(defaultTheme, allowSwitch, surveyId) {
  /* Keyed by survey, the way the answers are (useAutosave below): the key used
     to be the constant "siamang_theme", and localStorage is per origin, so a
     respondent who chose dark in one study arrived in the next one dark — a
     preference leaking between instruments that know nothing about each other.

     And it is only read when the respondent is allowed to choose. With the
     switch off the survey is pinned to what the researcher set, which is the
     whole point of turning it off; reading a stored value there would let an
     old choice override a decision made about this study. */
  const storageKey = "siamang_theme_" + surveyId;
  const preferred = () => {
    if (defaultTheme && defaultTheme !== "system") return defaultTheme;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  };

  const [theme, setTheme] = useState(() => {
    if (!allowSwitch) return preferred();
    try {
      const saved = localStorage.getItem(storageKey);
      if (saved === "light" || saved === "dark") return saved;
    } catch (err) {
      /* Storage can throw outright in private mode, not merely come back empty. */
    }
    return preferred();
  });

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  const toggle = useCallback(() => {
    const next = theme === "light" ? "dark" : "light";
    setTheme(next);
    try {
      localStorage.setItem(storageKey, next);
    } catch (err) {
      /* The choice still applies to this sitting; it just is not remembered. */
    }
  }, [theme, storageKey]);

  return { theme, toggle };
}

/* ─── useAutosave ──────────────────────────────────────────────────────── */

function useAutosave(store, surveyId, pageIdxRef) {
  const AUTO_SAVE_KEY = "siamang_answers_" + surveyId;
  const saveTimerRef = useRef(null);
  const savingTimerRef = useRef(null);
  const [saving, setSaving] = useState(false);
  const [savedData, setSavedData] = useState(null);

  // Load saved data on mount
  useEffect(() => {
    try {
      const raw = localStorage.getItem(AUTO_SAVE_KEY);
      if (raw) {
        const data = JSON.parse(raw);
        const age = Date.now() - new Date(data.savedAt).getTime();
        if (age < 86400000) setSavedData(data);
        else localStorage.removeItem(AUTO_SAVE_KEY);
      }
    } catch (e) {}
  }, []);

  const doSave = useCallback((currentAnswers, currentPage) => {
    const ric = window.requestIdleCallback || ((cb) => setTimeout(cb, 1));
    ric(() => {
      try {
        const cleanAnswers = {};
        for (const [k, v] of Object.entries(currentAnswers || {})) {
          if (!k.startsWith("__")) cleanAnswers[k] = v;
        }
        const data = { answers: cleanAnswers, pageIdx: currentPage, savedAt: new Date().toISOString() };
        localStorage.setItem(AUTO_SAVE_KEY, JSON.stringify(data));
      } catch (e) { /* quota exceeded */ }
    });
  }, [AUTO_SAVE_KEY]);

  const scheduleSave = useCallback(() => {
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    if (savingTimerRef.current) clearTimeout(savingTimerRef.current);
    saveTimerRef.current = setTimeout(() => {
      setSaving(true);
      doSave(store.snapshot(), pageIdxRef.current);
      savingTimerRef.current = setTimeout(() => setSaving(false), 800);
    }, 2000);
  }, [store, doSave, pageIdxRef]);

  const clearSaved = useCallback(() => {
    localStorage.removeItem(AUTO_SAVE_KEY);
    setSavedData(null);
  }, [AUTO_SAVE_KEY]);

  const saveNow = useCallback(() => {
    doSave(store.snapshot(), pageIdxRef.current);
  }, [store, doSave, pageIdxRef]);

  return { saving, savedData, setSavedData, scheduleSave, clearSaved, saveNow };
}

/* ─── useSurveyNav ─────────────────────────────────────────────────────── */

/* Resolve a routing target (a page name or a question id) to a page name.
   Question ids resolve to the page that contains the question. */
function resolveTargetPageName(target, orderedPages) {
  if (!target) return null;
  for (const p of orderedPages) {
    if (p.name === target) return p.name;
  }
  const containsQuestion = (items) =>
    Array.isArray(items) && items.some((q) => q && q.id === target);
  for (const p of orderedPages) {
    if (containsQuestion(p.items)) return p.name;
    if (Array.isArray(p.blocks) && p.blocks.some((b) => containsQuestion(b.items))) {
      return p.name;
    }
  }
  return null;
}

/* Decide where "Next" should land from `page`, honouring (in order):
   1. skip_to on the first answered visible question,
   2. the first matching next_if rule,
   3. default_next,
   4. the next visible page in sequence (return null → caller advances by 1).
   Returns a page NAME or null for plain sequential advance. */
function computeRouteTarget(page, answers, visibilityEngine) {
  if (!page) return null;
  const items = visibilityEngine.visibleItems(page, answers);
  for (const q of items) {
    if (q.skipTo && isAnswered(q, itemValue(q, answers))) return q.skipTo;
  }
  if (Array.isArray(page.nextIf)) {
    for (const rule of page.nextIf) {
      if (evaluateRouteCondition(rule.if, answers)) return rule.target;
    }
  }
  if (page.defaultNext) return page.defaultNext;
  return null;
}

function useSurveyNav(allPages, store, visibilityEngine) {
  const [pageIdx, setPageIdx] = useState(0);
  const [transitionDir, setTransitionDir] = useState(null);
  // Pages actually visited, as names — lets Previous retrace routed jumps.
  const historyRef = useRef([]);

  // Page order lives in the answers store (answers.__pages__) so lifecycle
  // scripts such as randomize_pages can reorder it; fall back to the static list.
  const storedOrder = useFieldValue(store, "__pages__");
  const orderedPages = Array.isArray(storedOrder) && storedOrder.length ? storedOrder : allPages;

  // Compute visible pages using the visibility engine
  const pages = useMemo(() => {
    return orderedPages.filter((p) => visibilityEngine.isPageVisible(p, store.snapshot()));
  }, [orderedPages, visibilityEngine, visibilityEngine._sig]);

  // Clamp pageIdx if visibility changes shrink the list
  useEffect(() => {
    if (pageIdx >= pages.length && pages.length > 0) {
      setPageIdx(Math.max(0, pages.length - 1));
    }
  }, [pages.length, pageIdx]);

  const currentPage = pages[pageIdx] || null;
  const isFirst = pageIdx === 0;
  const isLast = pageIdx === pages.length - 1;
  const totalPages = pages.length || 1;
  const progressPct = totalPages > 1
    ? Math.min(100, Math.round((pageIdx / (totalPages - 1)) * 100))
    : 100;

  const goNext = useCallback(() => {
    setTransitionDir("next");
    setTimeout(() => setTransitionDir(null), 140);
    const answers = store.snapshot();
    const from = pages[pageIdx] || null;
    let nextIdx = Math.min(pageIdx + 1, pages.length - 1);

    const targetName = resolveTargetPageName(
      computeRouteTarget(from, answers, visibilityEngine),
      orderedPages,
    );
    if (targetName) {
      let idx = pages.findIndex((p) => p.name === targetName);
      if (idx < 0) {
        // Target page exists but is currently hidden by its own gates:
        // land on the first visible page at-or-after it in document order.
        const orderedIdx = orderedPages.findIndex((p) => p.name === targetName);
        if (orderedIdx >= 0) {
          for (let j = orderedIdx + 1; j < orderedPages.length; j++) {
            const candidate = pages.findIndex((p) => p.name === orderedPages[j].name);
            if (candidate >= 0) { idx = candidate; break; }
          }
        }
      }
      if (idx >= 0) nextIdx = idx;
    }

    if (from) {
      historyRef.current.push(from.name);
      ScriptRunner.run("onPageExit", answers, {}, from.name);
    }
    setPageIdx(nextIdx);
    window.scrollTo(0, 0);
  }, [pages, pageIdx, orderedPages, store, visibilityEngine]);

  const goPrev = useCallback(() => {
    setTransitionDir("prev");
    setTimeout(() => setTransitionDir(null), 140);
    const from = pages[pageIdx] || null;
    if (from) ScriptRunner.run("onPageExit", store.snapshot(), {}, from.name);
    // Retrace the actual path (skips land back where the respondent was).
    while (historyRef.current.length > 0) {
      const prevName = historyRef.current.pop();
      const idx = pages.findIndex((p) => p.name === prevName);
      if (idx >= 0 && idx !== pageIdx) {
        setPageIdx(idx);
        window.scrollTo(0, 0);
        return;
      }
    }
    setPageIdx((i) => Math.max(i - 1, 0));
    window.scrollTo(0, 0);
  }, [pages, pageIdx, store]);

  const goTo = useCallback((idx) => {
    setPageIdx(idx);
  }, []);

  return {
    pageIdx, pages, currentPage, isFirst, isLast,
    totalPages, progressPct, transitionDir,
    goNext, goPrev, goTo, setPageIdx,
  };
}

/* ─── Quotas ───────────────────────────────────────────────────────────── */

/* The transport env.js registered for this survey, or null. */
function currentTransport() {
  const env = window.SIAMANG_ENV || window.SURVLIB_ENV || {};
  return (window.SIAMANG_TRANSPORTS || window.SURVLIB_TRANSPORTS || {})[env.transport] || null;
}

// How long leaving a page waits on a quota check before letting the
// respondent on: a slow or dead backend must never hold a survey hostage.
const QUOTA_CHECK_TIMEOUT_MS = 4000;

function hasAnswerValue(v) {
  return !(v === undefined || v === null || v === "" || (Array.isArray(v) && v.length === 0));
}

/* Quota enforcement. SURVEY.quotaVars names the variables some quota cell
   counts. When the respondent leaves a page, each of them that holds a value
   not yet found open — answered on this page, or set by a script — is put to
   the transport's checkQuota(variable, value) (a list for a MultiChoice); an
   answer of { ok: false } means a cell holding that value is full, and the
   interview ends as "quota full" before any routing, without a submission.
   No quotas, a transport without checkQuota, an error or a timeout: the
   respondent goes on — only a backend that says "full" stops anyone. */
function useQuotaCheck(quotaVars) {
  const checkedRef = useRef({});
  return useCallback(async (answers) => {
    const transport = currentTransport();
    if (!quotaVars.length || !transport || typeof transport.checkQuota !== "function") return false;
    const pending = quotaVars
      .filter((name) => hasAnswerValue(answers[name]))
      .map((name) => [name, answers[name], JSON.stringify(answers[name])])
      .filter(([name, , sig]) => checkedRef.current[name] !== sig);
    if (!pending.length) return false;
    const verdicts = await Promise.all(pending.map(async ([name, value, sig]) => {
      let timer = null;
      try {
        const timeout = new Promise((resolve) => { timer = setTimeout(() => resolve(null), QUOTA_CHECK_TIMEOUT_MS); });
        const res = await Promise.race([transport.checkQuota(name, value), timeout]);
        const full = !!res && res.ok === false;
        // Remember a value found open; a timeout or an error is asked again later.
        if (res && !full) checkedRef.current[name] = sig;
        return full;
      } catch (e) {
        return false;
      } finally {
        if (timer !== null) clearTimeout(timer);
      }
    }));
    return verdicts.some(Boolean);
  }, [quotaVars]);
}

/* ─── The respondent id ────────────────────────────────────────────────── */

/* One id per interview, the same for every script and every seeded draw:
   answers.__respondent__, which Script.assign_condition's seed and the
   MaxDiff / Conjoint design version are keyed by. A transport that knows the
   respondent (respondentId(), the id its own rows use) supplies it; otherwise
   the runtime makes one up and keeps it in this browser until the interview
   ends, so a reload resumes with the same arm and the same design. It never
   leaves the browser as an answer (submittedAnswers drops `__` keys). */
function interviewIdKey(surveyId) {
  return "siamang_interview_" + surveyId;
}

function randomInterviewId() {
  try {
    if (window.crypto && window.crypto.randomUUID) return window.crypto.randomUUID();
    if (window.crypto && window.crypto.getRandomValues) {
      const b = new Uint8Array(16);
      window.crypto.getRandomValues(b);
      return Array.from(b, (x) => ("0" + x.toString(16)).slice(-2)).join("");
    }
  } catch (e) { /* fall through */ }
  return Date.now().toString(36) + Math.random().toString(36).slice(2);
}

function interviewRespondentId(surveyId) {
  try {
    const transport = currentTransport();
    if (transport && typeof transport.respondentId === "function") {
      const id = transport.respondentId();
      if (id !== null && id !== undefined && String(id) !== "") return String(id);
    }
  } catch (e) { /* the runtime's own id below */ }
  try {
    const saved = localStorage.getItem(interviewIdKey(surveyId));
    if (saved) return saved;
  } catch (e) { /* private mode: an id for this page load */ }
  const id = randomInterviewId();
  try { localStorage.setItem(interviewIdKey(surveyId), id); } catch (e) { /* not kept */ }
  return id;
}

/* The interview is over (submitted, or ended by a full quota): the next one
   in this browser is a new respondent. */
function forgetInterview(surveyId) {
  try { localStorage.removeItem(interviewIdKey(surveyId)); } catch (e) { /* nothing kept */ }
}

/* ─── useSubmission ────────────────────────────────────────────────────── */

/* What a submission sends: the answers — every key a codebook variable — and
   the outcome (__status: completed, screened_out, redirect). The rest of the
   store is the runtime's own state and never an answer: __pages__ is the whole
   questionnaire in this respondent's order, __options__ every option list,
   __errors__ and a timed question's __timers__ bookkeeping. They used to go
   out with every completion, where a reader that unwraps nested objects
   turned __options__ into columns named after the questions — over the
   answers themselves. Keys a script cleared (undefined) are left out too. */
function submittedAnswers(snapshot) {
  const out = {};
  for (const [key, value] of Object.entries(snapshot || {})) {
    if (value === undefined) continue;
    if (key.startsWith("__") && key !== "__status") continue;
    out[key] = value;
  }
  return out;
}

function useSubmission(store, clearSaved, surveyId) {
  const [phase, setPhase] = useState("running"); // "running" | "completed" | "closed"
  // Why the survey closed on this respondent: "quota_full" (the sample is
  // complete) or "error" (the response could not be saved); null otherwise.
  const [closedReason, setClosedReason] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitId, setSubmitId] = useState(null);
  const [submittedAt, setSubmittedAt] = useState(null);
  const [submitAttempts, setSubmitAttempts] = useState(0);

  const submit = useCallback(async (isRetry = false) => {
    const env = window.SIAMANG_ENV || window.SURVLIB_ENV || {};
    const transport = (window.SIAMANG_TRANSPORTS || window.SURVLIB_TRANSPORTS || {})[env.transport];
    const stamp = new Date();
    if (!isRetry) setSubmitAttempts(0);
    setSubmitting(true);
    try {
      ScriptRunner.runOnSubmit(store.snapshot());
      if (transport && typeof transport.submit === "function") {
        const res = await transport.submit(submittedAnswers(store.snapshot()));
        if (res && res.status === "quota_full") {
          setSubmitting(false);
          setClosedReason("quota_full");
          setPhase("closed");
          return;
        }
        if (res && res.response_id !== undefined) {
          setSubmitId("R-" + String(res.response_id).padStart(5, "0"));
        } else if (res && res.id) {
          setSubmitId(String(res.id));
        }
      }
      setSubmittedAt(stamp.toLocaleString());
      clearSaved();
      forgetInterview(surveyId);
      setSubmitAttempts(0);
      setSubmitting(false);
      setPhase("completed");
    } catch (err) {
      console.error("siamang submit failed:", err);
      setSubmitting(false);
      const newAttempts = (isRetry ? submitAttempts : 0) + 1;
      setSubmitAttempts(newAttempts);
      if (newAttempts >= 3) {
        setClosedReason(err && err.status === 409 ? "quota_full" : "error");
        setPhase("closed");
      }
    }
  }, [store, clearSaved, submitAttempts, surveyId]);

  return { phase, setPhase, closedReason, setClosedReason, submitting, setSubmitting, submitId, submittedAt, submitAttempts, submit };
}

/* ─── useKeyboardShortcuts ─────────────────────────────────────────────── */

function useKeyboardShortcuts(navRef, storeRef, visibilityEngine) {
  useEffect(() => {
    const handler = (e) => {
      const nav = navRef.current;
      if (!nav) return;
      if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA" || e.target.tagName === "SELECT") return;

      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        if (nav.onNext) nav.onNext();
      }
      if (e.key === "Escape" && !nav.isFirst && (window.SURVEY || {}).allowBack !== false) {
        e.preventDefault();
        if (nav.onPrev) nav.onPrev();
      }
      if (/^[1-9]$/.test(e.key)) {
        const n = parseInt(e.key);
        const store = storeRef.current;
        const page = nav.currentPage;
        if (!page || !store) return;
        const answers = store.snapshot();
        const items = visibilityEngine.visibleItems(page, answers);
        for (const q of items) {
          if (q.kind === "likert" && n <= q.points) {
            store.set(q.id, n);
            break;
          }
        }
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);
}

/* ─── useTouchGestures ─────────────────────────────────────────────────── */

function useTouchGestures(onNext, onPrev, allowBack) {
  const touchStartX = useRef(null);

  const handleTouchStart = useCallback((e) => {
    touchStartX.current = e.touches[0].clientX;
  }, []);

  const handleTouchEnd = useCallback((e) => {
    if (!touchStartX.current) return;
    const diff = e.changedTouches[0].clientX - touchStartX.current;
    const threshold = 80;
    if (diff < -threshold) {
      onNext();
    } else if (diff > threshold && allowBack) {
      onPrev();
    }
    touchStartX.current = null;
  }, [onNext, onPrev, allowBack]);

  return { handleTouchStart, handleTouchEnd };
}

/* ─── useBeforeUnload ──────────────────────────────────────────────────── */

function useBeforeUnload(storeRef, phaseRef) {
  useEffect(() => {
    const handler = (e) => {
      const store = storeRef.current;
      if (!store) return;
      const answers = store.snapshot();
      const hasAnswers = Object.keys(answers).some((k) => !k.startsWith("__"));
      if (hasAnswers && phaseRef.current === "running") {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, []);
}
