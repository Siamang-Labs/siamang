/* siamang answers store — lightweight reactive form state.
   Decouples form values from React render cycle. Question components
   subscribe to individual fields via useSyncExternalStore; typing into
   one field never re-renders unrelated questions.

   API:
     const store = createAnswersStore(initial)
     store.get(id)                 — synchronous read
     store.set(id, value)          — update + notify subscribers
     store.snapshot()              — full answers object (immutable ref)
     store.subscribe(listener)     — useSyncExternalStore-compatible
     store.subscribeField(id, cb)  — fine-grained per-field subscription
     store.getFieldSnapshot(id)    — per-field snapshot for useSyncExternalStore
*/

function createAnswersStore(initial) {
  let state = { ...initial };
  let snapshot = state;
  const listeners = new Set();
  const fieldListeners = new Map();

  function notify(fieldId) {
    snapshot = { ...state };
    for (const cb of listeners) cb();
    const fls = fieldListeners.get(fieldId);
    if (fls) for (const cb of fls) cb();
  }

  return {
    get(id) {
      return state[id];
    },

    set(id, value) {
      if (state[id] === value) return;
      state = { ...state, [id]: value };
      notify(id);
    },

    setMany(updates) {
      let changed = false;
      for (const [id, value] of Object.entries(updates)) {
        if (state[id] !== value) {
          state = { ...state, [id]: value };
          changed = true;
        }
      }
      if (changed) {
        snapshot = { ...state };
        for (const cb of listeners) cb();
        for (const id of Object.keys(updates)) {
          const fls = fieldListeners.get(id);
          if (fls) for (const cb of fls) cb();
        }
      }
    },

    replace(newState) {
      state = { ...newState };
      snapshot = state;
      for (const cb of listeners) cb();
      for (const [id, fls] of fieldListeners) {
        for (const cb of fls) cb();
      }
    },

    snapshot() {
      return snapshot;
    },

    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },

    subscribeField(id, listener) {
      if (!fieldListeners.has(id)) fieldListeners.set(id, new Set());
      fieldListeners.get(id).add(listener);
      return () => {
        const fls = fieldListeners.get(id);
        if (fls) {
          fls.delete(listener);
          if (fls.size === 0) fieldListeners.delete(id);
        }
      };
    },

    getFieldSnapshot(id) {
      return state[id];
    },
  };
}

/* ─── Where an item's answer lives ────────────────────────────────────────
   Every key of the answers that reaches a backend is a codebook variable,
   and a condition, a quota, {answer:…} and the data all read a variable by
   its name. A question that writes one variable is stored under it — the
   item id. A matrix, a MaxDiff and a Conjoint write several, and each of
   them is a top-level key of its own: stored as one object under the
   question's key, a condition on a matrix row read `a["trust_parl"]` and
   found nothing, and so did every quota and piped text on it.

   Their components still work on one object ({row: code, …}); itemValue
   assembles it from the keys and answerUpdates splits one back into them.
   Nothing is stored under such a question's own key.

   A wide MultiChoice is the same idea for a list: its component works on the
   chosen codes, and each option's variable holds 1 when it is chosen and 0
   when the question is answered and it is not.

   "Other (please specify)" stores a code of the question's variable
   (q.otherCode) like any other choice, and the typed text under a key of its
   own, q.otherKey (`<variable>_other`): present — "" when nothing was typed —
   exactly while Other is chosen. Its component still gets the old shapes,
   { code, text } for one answer and { selected, otherText } for several. */

function isSpreadItem(q) {
  return !!q && (q.kind === "matrix" || q.kind === "maxdiff" || q.kind === "conjoint");
}

function isWideItem(q) {
  return !!q && q.kind === "multi" && q.wide === true;
}

/* A wide option's variable is chosen when it holds 1 (true or "1" from an
   older store or a script count as well). */
function isOn(value) {
  return value === 1 || value === true || value === "1";
}

/* Codes compare as conditions compare them loosely: 1 and "1" are one code. */
function sameCode(a, b) {
  if (a === b) return true;
  if (a === undefined || a === null || b === undefined || b === null) return false;
  return String(a) === String(b);
}

function hasOtherText(q) {
  return !!q && !!q.otherSpecify && !!q.otherKey &&
    (q.kind === "single" || q.kind === "dropdown" || q.kind === "multi");
}

/* A multiple answer as its component hands it over: the chosen codes and,
   with Other, the typed text. */
function splitMulti(value) {
  if (Array.isArray(value)) return { selected: value, text: "" };
  if (value && typeof value === "object") {
    return { selected: Array.isArray(value.selected) ? value.selected : [], text: value.otherText };
  }
  return { selected: [], text: "" };
}

/* The store keys an item writes. */
function itemAnswerKeys(q) {
  if (!q) return [];
  if (q.kind === "matrix") return (q.rows || []).map((r) => r.id);
  if (q.kind === "maxdiff") {
    const keys = [];
    for (const pair of q.taskVars || []) keys.push(...pair);
    if (q.versionVar) keys.push(q.versionVar);
    return keys;
  }
  if (q.kind === "conjoint") return [...(q.taskVars || []), ...(q.versionVar ? [q.versionVar] : [])];
  const keys = isWideItem(q) ? (q.options || []).map((o) => o.var).filter(Boolean) : [q.id];
  if (hasOtherText(q)) keys.push(q.otherKey);
  return keys;
}

/* An assembled value keeps its identity while its parts are unchanged, so a
   memoised question does not re-render on every change elsewhere. */
const __itemValueCache = new WeakMap();
function stableItemValue(q, value) {
  const sig = JSON.stringify(value === undefined ? null : value);
  const prev = __itemValueCache.get(q);
  if (prev && prev.sig === sig) return prev.value;
  __itemValueCache.set(q, { sig, value });
  return value;
}

/* The value an item's component is given, read from the answers. */
function itemValue(q, answers) {
  const a = answers || {};
  if (!q) return undefined;
  if (isSpreadItem(q)) {
    const out = {};
    let any = false;
    for (const key of itemAnswerKeys(q)) {
      if (a[key] !== undefined) { out[key] = a[key]; any = true; }
    }
    return stableItemValue(q, any ? out : undefined);
  }
  const other = hasOtherText(q);
  if (q.kind === "multi") {
    let chosen;
    if (isWideItem(q)) {
      chosen = [];
      for (const o of q.options || []) if (o && o.var && isOn(a[o.var])) chosen.push(o.code);
      if (other && a[q.otherKey] !== undefined && !chosen.some((c) => sameCode(c, q.otherCode))) {
        chosen.push(q.otherCode);
      }
    } else {
      chosen = Array.isArray(a[q.id]) ? a[q.id] : [];
    }
    // Nothing chosen is an unanswered question.
    if (!chosen.length) return isWideItem(q) || other ? stableItemValue(q, undefined) : a[q.id];
    if (other) return stableItemValue(q, { selected: chosen, otherText: a[q.otherKey] ?? "" });
    return isWideItem(q) ? stableItemValue(q, chosen) : a[q.id];
  }
  const code = a[q.id];
  if (other && sameCode(code, q.otherCode)) {
    return stableItemValue(q, { code, text: a[q.otherKey] ?? "" });
  }
  return code;
}

/* What storing `value` — as the item's component hands it over — writes:
   { key: value } for every key the item owns; undefined clears a key.
   `answers` (the answers so far) is what an option's own show_if / hide_if
   reads: a wide option it hides was never offered and stores nothing. */
function answerUpdates(q, value, answers) {
  if (isSpreadItem(q)) {
    const v = value && typeof value === "object" ? value : {};
    const updates = {};
    for (const key of itemAnswerKeys(q)) updates[key] = v[key];
    return updates;
  }
  const other = hasOtherText(q);
  if (q.kind === "multi") {
    const { selected, text } = splitMulti(value);
    const updates = {};
    if (isWideItem(q)) {
      for (const o of q.options || []) {
        if (!o || !o.var) continue;
        // Nothing chosen is an unanswered question: every variable is cleared.
        // 0 is "offered and not chosen"; an option its condition hid from this
        // respondent was not offered, and is missing like an unasked question.
        const chosen = selected.some((c) => sameCode(c, o.code));
        const offered = !answers || typeof gateOption !== "function" || gateOption(o, answers);
        updates[o.var] = selected.length && (chosen || offered) ? (chosen ? 1 : 0) : undefined;
      }
    } else {
      updates[q.id] = selected.length ? selected : undefined;
    }
    if (other) {
      updates[q.otherKey] = selected.some((c) => sameCode(c, q.otherCode)) ? String(text ?? "") : undefined;
    }
    return updates;
  }
  if (other) {
    const isObject = value !== null && typeof value === "object" && !Array.isArray(value);
    const code = isObject ? value.code : value;
    return {
      [q.id]: code,
      [q.otherKey]: sameCode(code, q.otherCode) ? String((isObject && value.text) || "") : undefined,
    };
  }
  return { [q.id]: value };
}

/* A wide question an option of which carries its own show_if / hide_if. */
function hasGatedOptions(q) {
  return isWideItem(q) && (q.options || []).some((o) => o && (o.showIf || o.hideIf));
}

/* The variables of every answered wide question whose options carry a
   condition, as those conditions read `answers` now. answerUpdates decides
   0 or missing when the question is answered, but an answer given after it —
   on the same page, or back on an earlier one — can offer an option the
   respondent left unticked (0, not missing) or take one away (missing, not
   0). A chosen option stays 1. Only the keys that change are returned.

   A condition may read another wide question's 0 or missing ("bought"
   offers Globex while aware_globex = 0), so each question is settled on
   what the ones before it settled, and the round repeats until nothing
   changes. Chosen options never change, so it ends; a round per question
   bounds conditions that feed each other in a circle. */
function wideGateUpdates(items, answers) {
  const a = answers || {};
  const gated = (items || []).filter(hasGatedOptions);
  const now = { ...a };
  for (let round = 0; round <= gated.length; round++) {
    let changed = false;
    for (const q of gated) {
      const value = itemValue(q, now);
      if (value === undefined) continue;
      for (const [key, v] of Object.entries(answerUpdates(q, value, now))) {
        if (now[key] !== v) { now[key] = v; changed = true; }
      }
    }
    if (!changed) break;
  }
  const updates = {};
  for (const key of Object.keys(now)) if (now[key] !== a[key]) updates[key] = now[key];
  return updates;
}

/* Keeps every answered wide question whose options carry a condition
   settled (wideGateUpdates) whatever writes the answers: a click, the Likert
   digit keys, a script, a resumed interview. */
function settleWideGates(store, items) {
  const gated = (items || []).filter(hasGatedOptions);
  if (!gated.length) return;
  let settling = false;
  store.subscribe(() => {
    if (settling) return;
    settling = true;
    try {
      const updates = wideGateUpdates(gated, store.snapshot());
      if (Object.keys(updates).length) store.setMany(updates);
    } finally {
      settling = false;
    }
  });
}

function forEachItem(pages, fn) {
  for (const p of pages || []) {
    for (const q of p.items || []) if (q) fn(q);
    for (const b of p.blocks || []) for (const q of b.items || []) if (q) fn(q);
  }
}

/* Answers saved in this browser by an earlier runtime, in today's layout —
   a respondent who resumes after the survey was redeployed must not have
   half their answers under keys nothing reads any more. Such a runtime kept a
   matrix, a MaxDiff or a Conjoint as one object under the question's key,
   a matrix cell as its column's position (1…n) rather than its code, a wide
   MultiChoice as the list of its chosen variables' names, Other as the code
   "__other__" with its text inside the answer ({ code, text } or
   { selected, otherText }), "None of the above" as "__none__" and N/A as
   "na" whatever the codebook declared. */
const LEGACY_OTHER = "__other__";
function upgradeSavedAnswers(pages, saved) {
  const out = { ...(saved || {}) };
  const otherCode = (q, code) => (code === LEGACY_OTHER && q.otherCode !== undefined ? q.otherCode : code);
  forEachItem(pages, (q) => {
    const legacy = out[q.id];
    if (q.kind === "multi" && legacy !== undefined && (isWideItem(q) || (legacy && typeof legacy === "object" && !Array.isArray(legacy)))) {
      const { selected, text } = splitMulti(legacy);
      if (isWideItem(q)) {
        if (!Array.isArray(legacy) && !(legacy && Array.isArray(legacy.selected))) return;
        delete out[q.id];
      }
      const chosen = [];
      for (const name of selected) {
        const o = (q.options || []).find((opt) => opt.var === name || sameCode(opt.code, name));
        chosen.push(o ? o.code : otherCode(q, name));
      }
      Object.assign(out, answerUpdates(q, hasOtherText(q) ? { selected: chosen, otherText: text } : chosen, out));
      return;
    }
    if ((q.kind === "single" || q.kind === "dropdown") && legacy !== undefined) {
      if (legacy && typeof legacy === "object" && legacy.code === LEGACY_OTHER) {
        Object.assign(out, answerUpdates(q, { code: otherCode(q, LEGACY_OTHER), text: legacy.text }));
      } else if (legacy === "__none__") {
        const none = (q.options || []).find((o) => o.noneOfAbove);
        if (none) out[q.id] = none.code;
      }
      return;
    }
    if (q.kind === "likert" && legacy === "na" && q.naCode !== undefined) {
      out[q.id] = q.naCode;
      return;
    }
    if (!isSpreadItem(q)) return;
    const nested = out[q.id];
    if (!nested || typeof nested !== "object" || Array.isArray(nested)) return;
    delete out[q.id];
    for (const key of itemAnswerKeys(q)) {
      if (nested[key] === undefined || out[key] !== undefined) continue;
      let value = nested[key];
      const columns = (q.columns || []).length;
      if (q.kind === "matrix" && Number.isInteger(value) && value >= 1 && value <= columns) {
        value = matrixColumnCode(q, value - 1);
      }
      if (q.kind === "matrix" && value === "na") {
        const row = (q.rows || []).find((r) => r.id === key);
        if (row && row.naCode !== undefined) value = row.naCode;
      }
      out[key] = value;
    }
  });
  return out;
}

/* React hooks for the store */

function useAnswersStore(store) {
  return React.useSyncExternalStore(store.subscribe, store.snapshot);
}

function useFieldValue(store, fieldId) {
  const subscribe = React.useCallback(
    (cb) => store.subscribeField(fieldId, cb),
    [store, fieldId]
  );
  const getSnapshot = React.useCallback(
    () => store.getFieldSnapshot(fieldId),
    [store, fieldId]
  );
  return React.useSyncExternalStore(subscribe, getSnapshot);
}

/* Hook to subscribe to a set of field IDs (for visibility deps) */
function useFieldsSignature(store, fieldIds) {
  const subscribe = React.useCallback(
    (cb) => {
      if (!fieldIds || fieldIds.length === 0) return () => {};
      const unsubs = fieldIds.map((id) => store.subscribeField(id, cb));
      return () => unsubs.forEach((u) => u());
    },
    [store, fieldIds]
  );
  const getSnapshot = React.useCallback(
    () => {
      if (!fieldIds || fieldIds.length === 0) return "";
      return fieldIds.map((id) => `${id}:${JSON.stringify(store.get(id))}`).join("|");
    },
    [store, fieldIds]
  );
  return React.useSyncExternalStore(subscribe, getSnapshot);
}
