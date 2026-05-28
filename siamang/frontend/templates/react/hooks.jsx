/* siamang React hooks — modular concerns extracted from the App monolith.
   Each hook owns its own state, effects, and contract. */

/* ─── useTheme ─────────────────────────────────────────────────────────── */

function useTheme(defaultTheme) {
  const [theme, setTheme] = useState(() => {
    const saved = localStorage.getItem("siamang_theme");
    if (saved) return saved;
    if (defaultTheme && defaultTheme !== "system") return defaultTheme;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  });

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  const toggle = useCallback(() => {
    const next = theme === "light" ? "dark" : "light";
    setTheme(next);
    localStorage.setItem("siamang_theme", next);
  }, [theme]);

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

function useSurveyNav(allPages, store, visibilityEngine) {
  const [pageIdx, setPageIdx] = useState(0);
  const [transitionDir, setTransitionDir] = useState(null);

  // Compute visible pages using the visibility engine
  const pages = useMemo(() => {
    return allPages.filter((p) => visibilityEngine.isPageVisible(p, store.snapshot()));
  }, [allPages, visibilityEngine, visibilityEngine._sig]);

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
    setPageIdx((i) => Math.min(i + 1, pages.length - 1));
    window.scrollTo(0, 0);
  }, [pages.length]);

  const goPrev = useCallback(() => {
    setTransitionDir("prev");
    setTimeout(() => setTransitionDir(null), 140);
    setPageIdx((i) => Math.max(i - 1, 0));
    window.scrollTo(0, 0);
  }, []);

  const goTo = useCallback((idx) => {
    setPageIdx(idx);
  }, []);

  return {
    pageIdx, pages, currentPage, isFirst, isLast,
    totalPages, progressPct, transitionDir,
    goNext, goPrev, goTo, setPageIdx,
  };
}

/* ─── useSubmission ────────────────────────────────────────────────────── */

function useSubmission(store, clearSaved) {
  const [phase, setPhase] = useState("running"); // "running" | "completed" | "closed"
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
        const res = await transport.submit(store.snapshot());
        if (res && res.status === "quota_full") {
          setSubmitting(false);
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
      setSubmitAttempts(0);
      setSubmitting(false);
      setPhase("completed");
    } catch (err) {
      console.error("siamang submit failed:", err);
      setSubmitting(false);
      const newAttempts = (isRetry ? submitAttempts : 0) + 1;
      setSubmitAttempts(newAttempts);
      if (newAttempts >= 3) {
        setPhase("closed");
      }
    }
  }, [store, clearSaved, submitAttempts]);

  return { phase, setPhase, submitting, setSubmitting, submitId, submittedAt, submitAttempts, submit };
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
