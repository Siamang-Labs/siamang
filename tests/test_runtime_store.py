"""The runtime's answer layout, run in Node on the shipped bundle.

`dist/bundle.js` is loaded into a bare Node context — React, the DOM and the
page globals stubbed out — so the functions that decide where an answer is
stored can be called directly. Only Node is needed (skipped without it); the
same behaviour is played end to end in ``test_runtime_browser.py``.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from importlib import resources
from typing import Any

import pytest

_BUNDLE = resources.files("siamang.frontend.templates.react").joinpath("dist/bundle.js")

_STUBS = r"""
const vm = require("vm");
const noop = () => {};
class Component { constructor(props) { this.props = props; } }
const React = {
  Component, memo: (f) => f, createElement: noop, Fragment: "f",
  useState: (v) => [typeof v === "function" ? v() : v, noop], useRef: (v) => ({ current: v }),
  useEffect: noop, useMemo: (f) => f(), useCallback: (f) => f,
  useSyncExternalStore: (s, g) => g(),
};
const storage = {};
const window = {
  SURVEY: {}, PAGES: [], addEventListener: noop, removeEventListener: noop,
  location: { search: "" }, matchMedia: () => ({ matches: false }),
};
const context = {
  React, window, console,
  ReactDOM: { createRoot: () => ({ render: noop }) },
  document: { getElementById: () => ({}), addEventListener: noop, documentElement: {} },
  localStorage: { getItem: (k) => storage[k] ?? null, setItem: (k, v) => { storage[k] = String(v); },
                  removeItem: (k) => { delete storage[k]; } },
  setTimeout, clearTimeout, requestAnimationFrame: noop,
};
window.window = window;
vm.createContext(context);
const [bundle, expression] = process.argv.slice(-2);
vm.runInContext(require("fs").readFileSync(bundle, "utf8"), context);
const out = vm.runInContext(expression, context);
console.log(JSON.stringify(out === undefined ? null : out));
"""


def run_js(expression: str) -> Any:
    """Evaluate ``expression`` in a context holding the runtime bundle."""

    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    result = subprocess.run(
        [node, "-e", _STUBS, "--", str(_BUNDLE), expression],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


_MATRIX = {
    "id": "trust",
    "kind": "matrix",
    "columns": ["0", "1", "2"],
    "columnCodes": [0, 1, 2],
    "rows": [{"id": "trust_parl", "label": "Parliament"}, {"id": "trust_pol", "label": "Police"}],
}
_MAXDIFF = {
    "id": "md",
    "kind": "maxdiff",
    "taskVars": [["md_t1_best", "md_t1_worst"]],
    "versionVar": "md_version",
}


def _js(value: Any) -> str:
    return json.dumps(value)


def test_a_matrix_is_written_row_by_row_and_read_back_as_one_object():
    result = run_js(
        f"""(() => {{
          const q = {_js(_MATRIX)};
          const updates = answerUpdates(q, {{ trust_parl: 2 }});
          const answers = {{ ...updates, other: 1 }};
          return {{ updates, value: itemValue(q, answers), none: itemValue(q, {{}}) === undefined }};
        }})()"""
    )
    # Every row key is written — undefined for an unanswered row, which the
    # JSON drops — and nothing under the question's key.
    assert result["updates"] == {"trust_parl": 2}
    assert result["value"] == {"trust_parl": 2}
    assert result["none"] is True


def test_an_assembled_value_keeps_its_identity_while_its_parts_do():
    assert run_js(
        f"""(() => {{
          const q = {_js(_MATRIX)};
          const a = itemValue(q, {{ trust_parl: 1, x: 1 }});
          const b = itemValue(q, {{ trust_parl: 1, x: 2 }});
          const c = itemValue(q, {{ trust_parl: 2 }});
          return [a === b, a === c];
        }})()"""
    ) == [True, False]


def test_a_maxdiff_writes_each_task_variable_and_the_version():
    assert run_js(
        f"""answerUpdates({_js(_MAXDIFF)},
              {{ md_t1_best: 3, md_t1_worst: 1, md_version: 4 }})"""
    ) == {"md_t1_best": 3, "md_t1_worst": 1, "md_version": 4}


def test_answers_saved_in_the_nested_layout_are_moved_to_the_flat_one():
    """What an earlier runtime left in localStorage: a matrix nested under its
    key with positions (1…n), a MaxDiff nested with codes."""

    pages = [{"name": "p", "items": [_MATRIX, _MAXDIFF, {"id": "age", "kind": "numeric"}]}]
    saved = {
        "trust": {"trust_parl": 3, "trust_pol": 1},
        "md": {"md_t1_best": 2, "md_version": 0},
        "age": 40,
    }
    assert run_js(f"upgradeSavedAnswers({_js(pages)}, {_js(saved)})") == {
        "trust_parl": 2,
        "trust_pol": 0,
        "md_t1_best": 2,
        "md_version": 0,
        "age": 40,
    }


_WIDE = {
    "id": "b",
    "kind": "multi",
    "wide": True,
    "options": [
        {"code": 1, "label": "Acme", "var": "b_1"},
        {"code": 2, "label": "Globex", "var": "b_2"},
    ],
}


def test_a_wide_multichoice_writes_one_or_zero_per_option_and_reads_codes():
    result = run_js(
        f"""(() => {{
          const q = {_js(_WIDE)};
          const updates = answerUpdates(q, [2]);
          return {{ updates, value: itemValue(q, updates),
                   cleared: Object.keys(answerUpdates(q, [])).filter((k) =>
                       answerUpdates(q, [])[k] !== undefined) }};
        }})()"""
    )
    assert result["updates"] == {"b_1": 0, "b_2": 1}
    assert result["value"] == [2]
    assert result["cleared"] == []


def test_a_wide_answer_saved_as_variable_names_is_upgraded():
    pages = [{"name": "p", "items": [_WIDE]}]
    assert run_js(f"upgradeSavedAnswers({_js(pages)}, {_js({'b': ['b_1']})})") == {
        "b_1": 1,
        "b_2": 0,
    }
