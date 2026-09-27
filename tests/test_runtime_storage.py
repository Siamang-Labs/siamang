"""What the survey runtime keeps in the respondent's browser, and for how long.

`dist/bundle.js` is loaded into a bare Node context (as in
``test_runtime_store.py``) with a working ``localStorage`` and a clock the
test sets, and the functions that keep, date and drop what a survey stores
are called directly: nothing is written before the respondent starts, a
survey's keys go together a week after it last wrote, and the one response
per browser mark stays. The same behavior is played end to end in
``test_runtime_browser.py``.
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
const [bundle, initial, expression] = process.argv.slice(-3);
// localStorage as a browser has it: getItem/setItem/removeItem, key(i), length.
const values = new Map(Object.entries(JSON.parse(initial)));
const localStorage = {
  getItem: (k) => (values.has(String(k)) ? values.get(String(k)) : null),
  setItem: (k, v) => { values.set(String(k), String(v)); },
  removeItem: (k) => { values.delete(String(k)); },
  key: (i) => { const keys = Array.from(values.keys()); return i < keys.length ? keys[i] : null; },
  get length() { return values.size; },
};
const window = {
  SURVEY: {}, PAGES: [], addEventListener: noop, removeEventListener: noop,
  location: { search: "" }, matchMedia: () => ({ matches: false }),
  SIAMANG_ENV: { transport: "test", survey_id: "s1" }, SIAMANG_TRANSPORTS: {},
};
const context = {
  React, window, console, localStorage,
  ReactDOM: { createRoot: () => ({ render: noop }) },
  document: { getElementById: () => ({}), addEventListener: noop, documentElement: {} },
  setTimeout, clearTimeout, requestAnimationFrame: noop,
};
window.window = window;
vm.createContext(context);
vm.runInContext(require("fs").readFileSync(bundle, "utf8"), context);
// The clock: Date.now() is what `now(ms)` last set.
vm.runInContext("var __now = 0; Date.now = () => __now; function now(ms) { __now = ms; }", context);
const result = vm.runInContext(expression, context);
console.log(JSON.stringify({
  result: result === undefined ? null : result,
  storage: Object.fromEntries(values),
}));
"""

DAY = 24 * 60 * 60 * 1000
WEEK = 7 * DAY
T0 = 1_800_000_000_000  # an arbitrary "now", in ms


def run_js(expression: str, storage: dict[str, str] | None = None) -> dict[str, Any]:
    """Evaluate ``expression`` against the bundle with ``storage`` in
    localStorage; returns ``{"result": …, "storage": …}`` (storage after)."""

    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    result = subprocess.run(
        [node, "-e", _STUBS, "--", str(_BUNDLE), json.dumps(storage or {}), expression],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


def _survey(sid: str, at: int | None) -> dict[str, str]:
    """Everything a survey can keep here: the runtime's keys, a host's
    (Studio's respondent id, end mark, one-response mark), and the note."""

    keys = {
        f"siamang_answers_{sid}": json.dumps({"answers": {"q": 1}, "pageIdx": 0}),
        f"siamang_respondent_{sid}": "r-" + sid,
        f"siamang_interview_{sid}": "i-" + sid,
        f"siamang_ended_{sid}": "1700000000000",
        f"siamang_theme_{sid}": "dark",
        f"siamang_done_{sid}": "2026-09-01T00:00:00.000Z",
    }
    if at is not None:
        keys[f"siamang_kept_{sid}"] = str(at)
    return keys


def test_a_survey_not_written_for_a_week_is_dropped_with_its_note():
    storage = {**_survey("old", T0 - WEEK), "other_app": "x"}
    after = run_js(f"sweepKept({T0})", storage)["storage"]
    # The one-response mark stays: forgetting it would let the browser
    # answer again; another application's key is not the runtime's.
    assert after == {"siamang_done_old": storage["siamang_done_old"], "other_app": "x"}


def test_a_survey_written_within_the_week_is_kept_whole():
    storage = _survey("recent", T0 - 6 * DAY)
    assert run_js(f"sweepKept({T0})", storage)["storage"] == storage


def test_each_survey_on_the_origin_has_its_own_week():
    storage = {**_survey("a", T0 - 8 * DAY), **_survey("b", T0 - DAY)}
    after = run_js(f"sweepKept({T0})", storage)["storage"]
    assert not any(key.endswith("_a") for key in after if "done" not in key)
    assert after["siamang_done_a"] == storage["siamang_done_a"]
    assert {key: after[key] for key in after if key.endswith("_b")} == _survey("b", T0 - DAY)


def test_keys_kept_before_the_notes_are_dated_then_and_go_a_week_later():
    storage = _survey("legacy", None)
    first = run_js(f"sweepKept({T0})", storage)["storage"]
    assert first == {**storage, "siamang_kept_legacy": str(T0)}
    assert run_js(f"sweepKept({T0 + WEEK - 1})", first)["storage"] == first
    last = run_js(f"sweepKept({T0 + WEEK})", first)["storage"]
    assert last == {"siamang_done_legacy": storage["siamang_done_legacy"]}


def test_a_note_with_nothing_left_beside_it_goes():
    storage = {"siamang_kept_gone": str(T0), "siamang_done_gone": "2026-09-01"}
    after = run_js(f"sweepKept({T0})", storage)["storage"]
    assert after == {"siamang_done_gone": "2026-09-01"}


def test_keeping_a_value_notes_when():
    out = run_js(f'now({T0}); keepItem("s1", "siamang_theme_s1", "dark")')
    assert out["result"] is True
    assert out["storage"] == {"siamang_theme_s1": "dark", "siamang_kept_s1": str(T0)}


def test_the_runtimes_own_id_is_kept_only_once_the_respondent_starts():
    out = run_js(
        f"""(() => {{
          now({T0});
          const id = interviewRespondentId("s1");
          const before = localStorage.length;
          startInterview("s1");
          const kept = localStorage.getItem("siamang_interview_s1");
          startInterview("s1");  // once per page load
          return {{ id, before, kept }};
        }})()"""
    )
    result = out["result"]
    assert result["before"] == 0
    assert result["kept"] == result["id"]
    assert out["storage"] == {"siamang_interview_s1": result["id"], "siamang_kept_s1": str(T0)}


def test_a_saved_id_is_the_interviews_and_the_end_forgets_it():
    out = run_js(
        """(() => {
          const id = interviewRespondentId("s1");
          startInterview("s1");
          forgetInterview("s1");
          return id;
        })()""",
        {"siamang_interview_s1": "saved-id", "siamang_kept_s1": str(T0)},
    )
    assert out["result"] == "saved-id"
    assert "siamang_interview_s1" not in out["storage"]


def test_a_transport_with_its_own_id_is_told_when_the_respondent_starts():
    out = run_js(
        f"""(() => {{
          now({T0});
          const calls = [];
          window.SIAMANG_TRANSPORTS.test = {{
            respondentId() {{ calls.push("respondentId"); return "t-1"; }},
            onStart() {{ calls.push("onStart"); }},
          }};
          const id = interviewRespondentId("s1");
          const before = localStorage.length;
          startInterview("s1");
          startInterview("s1");
          return {{ id, before, calls }};
        }})()"""
    )
    assert out["result"] == {"id": "t-1", "before": 0, "calls": ["respondentId", "onStart"]}
    # The runtime keeps no id of its own beside the transport's: only the note
    # that dates what the transport keeps from here.
    assert out["storage"] == {"siamang_kept_s1": str(T0)}


def test_a_failing_on_start_does_not_stop_the_respondent():
    out = run_js(
        """(() => {
          window.SIAMANG_TRANSPORTS.test = { onStart() { throw new Error("down"); } };
          interviewRespondentId("s1");
          startInterview("s1");
          return localStorage.getItem("siamang_interview_s1") !== null;
        })()"""
    )
    assert out["result"] is True


def test_in_memory_mode_nothing_reaches_the_browser():
    storage = _survey("old", T0 - 30 * DAY)
    out = run_js(
        f"""(() => {{
          window.SIAMANG_STORAGE = "memory";
          now({T0});
          sweepKept({T0});
          const id = interviewRespondentId("s1");
          startInterview("s1");
          keepItem("s1", "siamang_theme_s1", "dark");
          return [keptGet("siamang_interview_s1") === id, keptGet("siamang_theme_s1")];
        }})()""",
        storage,
    )
    assert out["result"] == [True, "dark"]
    # The browser's own storage is not read, written or swept.
    assert out["storage"] == storage
