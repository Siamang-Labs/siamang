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
