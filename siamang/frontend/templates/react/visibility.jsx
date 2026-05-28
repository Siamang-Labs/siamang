/* siamang visibility engine — compiles show_if/hide_if conditions into
   plain JS functions at load time. No more recursive AST interpretation
   on every render.

   Two modes:
   1. Compiled: condition has { deps: [...], fn: "..." } — uses new Function
   2. Legacy AST: condition has { type: "expression", ... } — falls back to
      the memoized interpreter (backward compat with old payloads)

   The engine also provides a React-friendly hook that only re-renders
   when visibility-relevant answers change. */

/* ─── Compiled condition cache ─────────────────────────────────────────── */

const __compiledFnCache = new WeakMap();

function getCompiledFn(condition) {
  if (__compiledFnCache.has(condition)) return __compiledFnCache.get(condition);
  let fn;
  if (condition.fn && typeof condition.fn === "string") {
    try {
      fn = new Function("a", "return " + condition.fn);
    } catch (e) {
      console.warn("siamang: failed to compile visibility fn:", condition.fn, e);
      fn = () => true;
    }
  } else {
    fn = null; // will fall back to AST interpreter
  }
  __compiledFnCache.set(condition, fn);
  return fn;
}

/* ─── Unified evaluator ────────────────────────────────────────────────── */

function evaluateCondition(condition, answers) {
  if (condition === null || condition === undefined) return true;
  if (typeof condition === "string") return true; // raw string — can't evaluate
  if (typeof condition !== "object") return Boolean(condition);

  // Compiled path (Phase 3 payloads)
  if (condition.fn !== undefined) {
    const fn = getCompiledFn(condition);
    if (fn) {
      try { return Boolean(fn(answers)); }
      catch (e) { return true; }
    }
  }

  // Legacy AST path (backward compat)
  return evalConditionMemoized(condition, answers);
}

function isConditionVisible(showIf, hideIf, answers) {
  if (!evaluateCondition(showIf, answers)) return false;
  if (hideIf === null || hideIf === undefined) return true;
  return !evaluateCondition(hideIf, answers);
}

/* ─── Dependency extraction ────────────────────────────────────────────── */

function getConditionDeps(condition) {
  if (!condition || typeof condition !== "object") return [];
  // Compiled path: deps are explicit
  if (Array.isArray(condition.deps)) return condition.deps;
  // Legacy AST path: extract from tree
  let cached = __exprDepsCache.get(condition);
  if (!cached) {
    cached = Array.from(collectExprDeps(condition));
    __exprDepsCache.set(condition, cached);
  }
  return cached;
}

/* ─── Visibility Engine object ─────────────────────────────────────────── */

function createVisibilityEngine(allPages, store) {
  // Collect ALL deps across all pages/blocks/questions
  const allDeps = new Set();
  const addCondDeps = (cond) => {
    if (!cond) return;
    for (const d of getConditionDeps(cond)) allDeps.add(d);
  };

  for (const page of allPages) {
    addCondDeps(page.showIf);
    addCondDeps(page.hideIf);
    if (Array.isArray(page.blocks)) {
      for (const block of page.blocks) {
        addCondDeps(block.showIf);
        addCondDeps(block.hideIf);
        if (Array.isArray(block.items)) {
          for (const item of block.items) {
            addCondDeps(item.showIf);
            addCondDeps(item.hideIf);
          }
        }
      }
    } else if (Array.isArray(page.items)) {
      for (const item of page.items) {
        addCondDeps(item.showIf);
        addCondDeps(item.hideIf);
      }
    }
  }

  const depsList = Array.from(allDeps);

  return {
    _sig: "", // will be updated reactively

    deps: depsList,

    isPageVisible(page, answers) {
      return isConditionVisible(page.showIf, page.hideIf, answers);
    },

    isBlockVisible(block, answers) {
      return isConditionVisible(block.showIf, block.hideIf, answers);
    },

    isItemVisible(item, answers) {
      return isConditionVisible(item.showIf, item.hideIf, answers);
    },

    visibleItems(page, answers) {
      let items;
      if (page.items) {
        items = page.items;
      } else if (page.blocks) {
        items = page.blocks
          .filter((b) => isConditionVisible(b.showIf, b.hideIf, answers))
          .flatMap((b) => b.items || []);
      } else {
        items = [];
      }
      return items.filter((q) => isConditionVisible(q.showIf, q.hideIf, answers));
    },

    pageItemsForAnswers(page, answers) {
      if (page.items) return page.items;
      if (page.blocks) {
        return page.blocks
          .filter((b) => isConditionVisible(b.showIf, b.hideIf, answers))
          .flatMap((b) => b.items || []);
      }
      return [];
    },
  };
}

/* Hook that provides a reactive visibility engine.
   Re-renders the consumer only when visibility-relevant answers change. */
function useVisibilityEngine(allPages, store) {
  const engine = useMemo(() => createVisibilityEngine(allPages, store), [allPages]);

  // Subscribe only to fields that affect visibility
  const sig = useFieldsSignature(store, engine.deps);

  // Attach current signature so useMemo in useSurveyNav can depend on it
  engine._sig = sig;

  return engine;
}
