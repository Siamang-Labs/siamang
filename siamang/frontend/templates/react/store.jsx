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
   Nothing is stored under such a question's own key. */

function isSpreadItem(q) {
  return !!q && (q.kind === "matrix" || q.kind === "maxdiff" || q.kind === "conjoint");
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
  return [q.id];
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
  return a[q.id];
}

/* What storing `value` — as the item's component hands it over — writes:
   { key: value } for every key the item owns; undefined clears a key. */
function answerUpdates(q, value) {
  if (isSpreadItem(q)) {
    const v = value && typeof value === "object" ? value : {};
    const updates = {};
    for (const key of itemAnswerKeys(q)) updates[key] = v[key];
    return updates;
  }
  return { [q.id]: value };
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
   and a matrix cell as its column's position (1…n) rather than its code. */
function upgradeSavedAnswers(pages, saved) {
  const out = { ...(saved || {}) };
  forEachItem(pages, (q) => {
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
