/* siamang visibility engine — compiles show_if/hide_if conditions into
   plain JS functions at load time. No more recursive AST interpretation
   on every render.

   Two modes:
   1. Compiled: condition has { deps: [...], fn: "..." } — uses new Function
   2. Legacy AST: condition has { type: "expression", ... } — falls back to
      the memoized interpreter (backward compat with old payloads)

   The engine also provides a React-friendly hook that only re-renders
   when visibility-relevant answers change. */

/* ─── String-condition parser (SurveyJS dialect subset) ────────────────────
   Evaluates plain-string gates and routing conditions such as
     "{age} >= 18", "age >= 18 and gender = 2", "{color} in [1, 2]",
     "not ({consent} = 1)", "{name} notempty"
   Produces { deps, fn } compatible with the compiled-condition path.
   Anything the grammar cannot parse falls back to the historical
   behaviour (condition treated as true) with a one-time console warning. */

const __stringCondCache = new Map();

function __tokenizeCondition(src) {
  const tokens = [];
  let i = 0;
  const n = src.length;
  while (i < n) {
    const c = src[i];
    if (c === " " || c === "\t" || c === "\n" || c === "\r") { i++; continue; }
    if (c === "{") {
      const end = src.indexOf("}", i + 1);
      if (end < 0) return null;
      tokens.push({ t: "var", v: src.slice(i + 1, end).trim() });
      i = end + 1;
      continue;
    }
    if (c === "'" || c === '"') {
      let j = i + 1, out = "";
      while (j < n && src[j] !== c) { out += src[j]; j++; }
      if (j >= n) return null;
      tokens.push({ t: "str", v: out });
      i = j + 1;
      continue;
    }
    if (/[0-9]/.test(c) || (c === "-" && /[0-9]/.test(src[i + 1] || ""))) {
      let j = i + 1;
      while (j < n && /[0-9.eE+-]/.test(src[j])) {
        // stop a trailing +/- that is not part of an exponent
        if ((src[j] === "+" || src[j] === "-") && !/[eE]/.test(src[j - 1])) break;
        j++;
      }
      const num = Number(src.slice(i, j));
      if (Number.isNaN(num)) return null;
      tokens.push({ t: "num", v: num });
      i = j;
      continue;
    }
    if (c === "(") { tokens.push({ t: "(" }); i++; continue; }
    if (c === ")") { tokens.push({ t: ")" }); i++; continue; }
    if (c === "[") { tokens.push({ t: "[" }); i++; continue; }
    if (c === "]") { tokens.push({ t: "]" }); i++; continue; }
    if (c === ",") { tokens.push({ t: "," }); i++; continue; }
    const two = src.slice(i, i + 2);
    if (two === "!=" || two === "<>" ) { tokens.push({ t: "op", v: "!=" }); i += 2; continue; }
    if (two === ">=" || two === "<=" || two === "==") { tokens.push({ t: "op", v: two === "==" ? "=" : two }); i += 2; continue; }
    if (two === "&&") { tokens.push({ t: "kw", v: "and" }); i += 2; continue; }
    if (two === "||") { tokens.push({ t: "kw", v: "or" }); i += 2; continue; }
    if (c === "=" ) { tokens.push({ t: "op", v: "=" }); i++; continue; }
    if (c === ">" ) { tokens.push({ t: "op", v: ">" }); i++; continue; }
    if (c === "<" ) { tokens.push({ t: "op", v: "<" }); i++; continue; }
    if (c === "!" ) { tokens.push({ t: "kw", v: "not" }); i++; continue; }
    if (/[A-Za-z_]/.test(c)) {
      let j = i + 1;
      while (j < n && /[A-Za-z0-9_]/.test(src[j])) j++;
      const word = src.slice(i, j);
      const lower = word.toLowerCase();
      if (["and", "or", "not", "in", "empty", "notempty", "notin", "contains", "notcontains", "true", "false"].includes(lower)) {
        tokens.push({ t: "kw", v: lower });
      } else {
        tokens.push({ t: "ident", v: word });
      }
      i = j;
      continue;
    }
    return null; // unknown character
  }
  return tokens;
}

function __parseConditionString(src) {
  const tokens = __tokenizeCondition(src);
  if (!tokens || !tokens.length) return null;
  const deps = new Set();
  let pos = 0;
  const peek = () => tokens[pos];
  const eat = () => tokens[pos++];
  const isKw = (v) => peek() && peek().t === "kw" && peek().v === v;

  function parseOperand() {
    const tok = peek();
    if (!tok) return null;
    if (tok.t === "var" || tok.t === "ident") {
      eat();
      deps.add(tok.v);
      return { code: "a[" + JSON.stringify(tok.v) + "]", isVar: true };
    }
    if (tok.t === "num") { eat(); return { code: JSON.stringify(tok.v) }; }
    if (tok.t === "str") { eat(); return { code: JSON.stringify(tok.v) }; }
    if (tok.t === "kw" && (tok.v === "true" || tok.v === "false")) { eat(); return { code: tok.v }; }
    if (tok.t === "[") {
      eat();
      const items = [];
      while (peek() && peek().t !== "]") {
        const item = parseOperand();
        if (!item) return null;
        items.push(item.code);
        if (peek() && peek().t === ",") eat();
      }
      if (!peek()) return null;
      eat(); // ]
      return { code: "[" + items.join(",") + "]" };
    }
    return null;
  }

  function parseComparison() {
    if (peek() && peek().t === "(") {
      eat();
      const inner = parseOr();
      if (!inner || !peek() || peek().t !== ")") return null;
      eat();
      return "(" + inner + ")";
    }
    const left = parseOperand();
    if (!left) return null;
    const tok = peek();
    if (tok && tok.t === "op") {
      eat();
      const right = parseOperand();
      if (!right) return null;
      // Loose equality: answer stores may hold "2" vs 2 depending on input type.
      if (tok.v === "=") return "(" + left.code + "==" + right.code + ")";
      if (tok.v === "!=") return "(" + left.code + "!=" + right.code + ")";
      return "(" + left.code + tok.v + right.code + ")";
    }
    if (tok && tok.t === "kw") {
      if (tok.v === "in" || tok.v === "notin") {
        eat();
        const right = parseOperand();
        if (!right) return null;
        const test = "(Array.isArray(" + right.code + ")&&" + right.code + ".includes(" + left.code + "))";
        return tok.v === "in" ? test : "(!" + test + ")";
      }
      if (tok.v === "not" && tokens[pos + 1] && tokens[pos + 1].t === "kw" && tokens[pos + 1].v === "in") {
        eat(); eat();
        const right = parseOperand();
        if (!right) return null;
        return "(!(Array.isArray(" + right.code + ")&&" + right.code + ".includes(" + left.code + ")))";
      }
      if (tok.v === "contains" || tok.v === "notcontains") {
        eat();
        const right = parseOperand();
        if (!right) return null;
        const test = "(Array.isArray(" + left.code + ")?" + left.code + ".includes(" + right.code + "):String(" + left.code + "??\"\").includes(" + right.code + "))";
        return tok.v === "contains" ? test : "(!" + test + ")";
      }
      if (tok.v === "empty") {
        eat();
        return "((v=>v===undefined||v===null||v===\"\"||(Array.isArray(v)&&!v.length))(" + left.code + "))";
      }
      if (tok.v === "notempty") {
        eat();
        return "(!(v=>v===undefined||v===null||v===\"\"||(Array.isArray(v)&&!v.length))(" + left.code + "))";
      }
    }
    // Bare operand as boolean (e.g. "{consent}")
    return "(Boolean(" + left.code + "))";
  }

  function parseNot() {
    if (isKw("not")) {
      eat();
      const inner = parseNot();
      if (!inner) return null;
      return "(!" + inner + ")";
    }
    return parseComparison();
  }

  function parseAnd() {
    let left = parseNot();
    if (!left) return null;
    while (isKw("and")) {
      eat();
      const right = parseNot();
      if (!right) return null;
      left = "(" + left + "&&" + right + ")";
    }
    return left;
  }

  function parseOr() {
    let left = parseAnd();
    if (!left) return null;
    while (isKw("or")) {
      eat();
      const right = parseAnd();
      if (!right) return null;
      left = "(" + left + "||" + right + ")";
    }
    return left;
  }

  const body = parseOr();
  if (!body || pos !== tokens.length) return null;
  return { deps: Array.from(deps), src: body };
}

function getStringCondition(src) {
  if (__stringCondCache.has(src)) return __stringCondCache.get(src);
  let entry = null;
  const parsed = __parseConditionString(src);
  if (parsed) {
    try {
      entry = { deps: parsed.deps, fn: new Function("a", "return " + parsed.src) };
    } catch (e) {
      entry = null;
    }
  }
  if (!entry) {
    console.warn("siamang: cannot evaluate string condition, treating as true:", src);
  }
  __stringCondCache.set(src, entry);
  return entry;
}

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
  if (typeof condition === "string") {
    const entry = getStringCondition(condition);
    if (!entry) return true; // unparsable string — historical behaviour
    try { return Boolean(entry.fn(answers)); }
    catch (e) { return true; }
  }
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

/* Global alias used by questions.jsx for per-option gating (all runtime
   files share one scope in the built bundle). */
function isVisibleGated(showIf, hideIf, answers) {
  return isConditionVisible(showIf, hideIf, answers);
}

/* Evaluate a routing condition (page.nextIf rule). Routing conditions must
   affirmatively match, so — unlike visibility gates — an unparsable or
   failing condition counts as NOT matched. */
function evaluateRouteCondition(condition, answers) {
  if (condition === null || condition === undefined) return false;
  if (typeof condition === "string") {
    const entry = getStringCondition(condition);
    if (!entry) return false;
    try { return Boolean(entry.fn(answers)); }
    catch (e) { return false; }
  }
  if (typeof condition === "object" && condition.fn !== undefined) {
    const fn = getCompiledFn(condition);
    if (fn) {
      try { return Boolean(fn(answers)); }
      catch (e) { return false; }
    }
  }
  if (typeof condition === "object") {
    try { return Boolean(evalConditionMemoized(condition, answers)); }
    catch (e) { return false; }
  }
  return Boolean(condition);
}

/* ─── Dependency extraction ────────────────────────────────────────────── */

function getConditionDeps(condition) {
  if (typeof condition === "string") {
    const entry = getStringCondition(condition);
    return entry ? entry.deps : [];
  }
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
