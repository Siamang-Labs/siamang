"""The survey runtime in a real browser.

The compiler tests pin the payload; these drive the built bundle — the
`dist/bundle.js` a respondent's browser runs — in headless Chromium and read
what it stores and submits. Each test compiles a questionnaire into a static
bundle whose transport records every submission and quota check on
``window.__T``, opens it from disk and plays a respondent.

They need Node, the `playwright` package and a Chromium it can launch, and are
skipped without them. Point them at an installation with ``NODE_PATH`` (a
``node_modules`` directory that holds `playwright`) and, when Playwright's own
browser download is not there, ``PLAYWRIGHT_CHROMIUM`` (the Chromium
executable)::

    NODE_PATH=…/node_modules PLAYWRIGHT_CHROMIUM=/opt/pw-browsers/chromium \\
        python -m pytest tests/test_runtime_browser.py
"""

from __future__ import annotations

import functools
import http.server
import json
import os
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Any

import pytest

from siamang.core.expression import Expression
from siamang.frontend import ClientEnv, FrontendBuilder, ReactRuntime, UIConfig
from siamang.frontend.client.base import BackendClientTemplate
from siamang.frontend.compiler import compile_questionnaire
from siamang.model import from_document

from .test_runtime_store import fnv1a, mulberry32, seeded_shuffle

# A transport that keeps everything it is handed. `window.__T.full` lists the
# quota cells ([variable, value]) that answer "full"; `quotaThrows` makes every
# check fail the way an unreachable server does; `submitReply` is what a
# submission is answered with; `failSubmits` makes that many submissions throw
# (with `failMessage` as their respondentMessage, when set); `holdSubmit`
# keeps each submission waiting until the page calls `window.__T.release()`.
_TRANSPORT = r"""
window.SIAMANG_ENV = { transport: "test", survey_id: "t" };
window.SIAMANG_TRANSPORTS = window.SIAMANG_TRANSPORTS || {};
window.__T = Object.assign({ full: [], quotaThrows: false, failSubmits: 0 }, window.__T || {},
  { submitted: [], quotaCalls: [], pages: [] });
window.SIAMANG_TRANSPORTS.test = {
  onPage(p) { window.__T.pages.push(p.name); },
  async submit(r) {
    window.__T.submitted.push(JSON.parse(JSON.stringify(r)));
    if (window.__T.holdSubmit) await new Promise((go) => { window.__T.release = go; });
    if (window.__T.failSubmits > 0) {
      window.__T.failSubmits -= 1;
      const err = new Error("submit failed: 503");
      err.status = 503;
      if (window.__T.failMessage) err.respondentMessage = window.__T.failMessage;
      throw err;
    }
    return window.__T.submitReply || { response_id: 7 };
  },
  respondentId() { return window.__T.rid; },
  async checkQuota(variable, value) {
    window.__T.quotaCalls.push([variable, value]);
    if (window.__T.quotaThrows) throw new Error("unreachable");
    const values = Array.isArray(value) ? value : [value];
    const full = (window.__T.full || []).some(([v, x]) => v === variable &&
      values.some((y) => JSON.stringify(y) === JSON.stringify(x)));
    return { ok: !full };
  },
};
"""

_HARNESS = r"""
const [dir, scenarioFile, initFile] = process.argv.slice(2);
const fs = require("fs");
let chromium;
try { ({ chromium } = require("playwright")); }
catch (e) { console.log(JSON.stringify({ skip: "playwright is not installed" })); process.exit(0); }
(async () => {
  let browser;
  try {
    const exe = process.env.PLAYWRIGHT_CHROMIUM;
    browser = await chromium.launch(exe ? { executablePath: exe } : {});
  } catch (e) {
    console.log(JSON.stringify({ skip: "no Chromium: " + String(e.message).split("\n")[0] }));
    process.exit(0);
  }
  const errors = [];
  try {
    const page = await browser.newPage();
    page.on("pageerror", (e) => errors.push(e.message));
    await page.route(/^https?:\/\//, (route) => route.abort());
    await page.addInitScript(fs.readFileSync(initFile, "utf8"));
    await page.goto("file://" + dir + "/index.html");
    await page.waitForSelector(".sd-page", { timeout: 15000 });
    const scenario = new Function("page", "return (async () => {" +
      fs.readFileSync(scenarioFile, "utf8") + "})();");
    const result = await scenario(page);
    console.log(JSON.stringify({ result, errors }));
  } finally {
    await browser.close();
  }
})().catch((e) => { console.log(JSON.stringify({ error: String((e && e.stack) || e), errors: [] })); });
"""


class _RecordingClient(BackendClientTemplate):
    name = "test"

    def render_env_js(self, env: ClientEnv) -> str:
        return _TRANSPORT


def _node() -> str:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    return node


def build_bundle(
    document: dict[str, Any], out: Path, *, client: BackendClientTemplate | None = None
) -> Path:
    """Compile a questionnaire document into a static bundle under ``out``
    (with the recording transport's template unless ``client`` is given)."""

    loaded = from_document(document)
    options = dict(loaded.options)
    ui = options.pop("ui", None) or UIConfig()
    schema = compile_questionnaire(loaded.survey, options=options)
    env = ClientEnv(survey_id="t", backend="test", settings={})
    bundle = FrontendBuilder(ui=ui, runtime=ReactRuntime()).build(
        schema, client=client or _RecordingClient(), env=env, survey=loaded.survey
    )
    return bundle.write_to(out)


def run_in_browser(
    document: dict[str, Any],
    scenario: str,
    tmp_path: Path,
    *,
    init: str = "",
    extra_files: dict[str, str] | None = None,
    client: BackendClientTemplate | None = None,
    env_js: bool | str = True,
) -> Any:
    """Open ``document`` as a respondent and run ``scenario`` — the body of an
    async function of Playwright's ``page`` — returning what it returns.
    ``extra_files`` are written next to the bundle's index.html. ``client``
    builds the bundle (see build_bundle); ``env_js=False`` takes its env.js
    out, as when it fails to load, and a string is what env.js holds instead."""

    node = _node()
    out = build_bundle(document, tmp_path / "bundle", client=client)
    if env_js is not True:
        (env,) = out.glob("env*.js")
        if env_js is False:
            env.unlink()
        else:
            env.write_text(env_js, encoding="utf-8")
    for name, text in (extra_files or {}).items():
        (out / name).write_text(text, encoding="utf-8")
    harness = tmp_path / "harness.cjs"
    harness.write_text(_HARNESS, encoding="utf-8")
    scenario_file = tmp_path / "scenario.js"
    scenario_file.write_text(scenario, encoding="utf-8")
    init_file = tmp_path / "init.js"
    init_file.write_text(init, encoding="utf-8")
    result = subprocess.run(
        [node, str(harness), str(out.resolve()), str(scenario_file), str(init_file)],
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ},
    )
    lines = [line for line in result.stdout.splitlines() if line.startswith("{")]
    if not lines:
        raise AssertionError(f"browser harness printed nothing:\n{result.stdout}\n{result.stderr}")
    outcome = json.loads(lines[-1])
    if "skip" in outcome:
        pytest.skip(outcome["skip"])
    if "error" in outcome:
        raise AssertionError(outcome["error"])
    assert outcome["errors"] == [], outcome["errors"]
    return outcome["result"]


# ── Shared steps ─────────────────────────────────────────────────────────────

# What the recording transport received, and what the store holds.
_STATE = """
    const T = await page.evaluate(() => window.__T);
    return { submitted: T.submitted, quotaCalls: T.quotaCalls, pages: T.pages };
"""

# Next, then a moment for the runtime to act on it — and, behind whatever the
# page already had queued when the moment is up (a busy machine starves it),
# two frames, so what is read next is what the page did with the click.
_NEXT = """
    await page.click(".sd-navigation__next-btn, .sd-navigation__complete-btn");
    await page.waitForTimeout(250);
    await page.evaluate(() => new Promise((done) =>
        requestAnimationFrame(() => requestAnimationFrame(() => done()))));
"""

# `reload(ready)` loads the page again and `visit(query, ready)` loads it with
# another query string (`?rid=…`, see _RID_FROM_URL); both wait until the
# *new* document shows `ready`. The old document is marked first, so nothing
# read afterward can come from the interview that was on screen before.
_RELOAD = """
    const fresh = async (ready) => {
        await page.waitForFunction(() => !window.__stale, null, { timeout: 10000 });
        await page.waitForSelector(ready);
    };
    const reload = async (ready = ".sd-page") => {
        await page.evaluate(() => { window.__stale = true; });
        await page.reload();
        await fresh(ready);
    };
    const visit = async (query, ready = ".sd-page") => {
        await page.evaluate(() => { window.__stale = true; });
        await page.goto(page.url().split("?")[0] + query);
        await fresh(ready);
    };
"""


def _autosaved(check: str) -> str:
    """Wait until the autosave — written 2 s after the last answer, when the
    browser is idle — holds answers for which the JS expression ``check`` (on
    ``answers``) is true, instead of sleeping and hoping it has run."""

    return f"""
        await page.waitForFunction(() => Object.keys(localStorage).some((key) => {{
            if (!key.startsWith("siamang_answers_")) return false;
            try {{ const answers = JSON.parse(localStorage.getItem(key)).answers; return {check}; }}
            catch (e) {{ return false; }}
        }}), null, {{ timeout: 15000 }});
    """


def _labels(codes: list[int]) -> list[dict[str, Any]]:
    return [{"code": code, "label": str(code)} for code in codes]


# ── Matrix ───────────────────────────────────────────────────────────────────


def _trust_matrix_document() -> dict[str, Any]:
    scale = [{"code": n, "label": str(n)} for n in range(0, 11)]
    return {
        "schema_version": "1.0",
        "title": "Trust",
        "variables": {
            "trust_parl": {"scale": "interval", "label": "Parliament", "labels": scale},
            "trust_pol": {"scale": "interval", "label": "Police", "labels": scale},
        },
        "pages": [
            {
                "name": "p1",
                "items": [
                    {
                        "type": "Matrix",
                        "id": "trust",
                        "text": "How much do you trust…",
                        "var": ["trust_parl", "trust_pol"],
                        "subquestions": ["Parliament", "Police"],
                        "column_labels": [str(n) for n in range(0, 11)],
                    }
                ],
            },
            {"name": "done", "kind": "final", "title": "Thanks"},
        ],
    }


_CLICK_MATRIX = """
    const rows = await page.$$("table.sd-matrix tbody tr");
    await (await rows[0].$$("button.sd-matrix__cell"))[2].click();
    await (await rows[1].$$("button.sd-matrix__cell"))[10].click();
"""


def test_a_matrix_cell_stores_its_columns_code_not_its_position(tmp_path):
    """0–10 scale: the third column is 2 and the last is 10 — not 3 and 11."""

    state = run_in_browser(_trust_matrix_document(), _CLICK_MATRIX + _NEXT + _STATE, tmp_path)
    (submitted,) = state["submitted"]
    assert submitted["trust_parl"] == 2
    assert submitted["trust_pol"] == 10


def test_a_labelled_na_code_leaves_the_scale_columns_where_they_are(tmp_path):
    """The ESS scale, labeled "No trust at all" … "Complete trust" under
    headers "0" … "10", with the N/A column's code declared and labeled: the
    headers still store 0 … 10, and N/A its code."""

    document = _trust_matrix_document()
    for name in ("trust_parl", "trust_pol"):
        labels = document["variables"][name]["labels"]
        labels[0]["label"], labels[10]["label"] = "No trust at all", "Complete trust"
        labels.append({"code": -1, "label": "Not applicable"})
        document["variables"][name]["missing"] = [
            {"code": -1, "label": "Not applicable", "kind": "not_applicable"}
        ]
    document["pages"][0]["items"][0]["na_option"] = True
    scenario = (
        _CLICK_MATRIX
        + """
        const headers = await page.$$eval("table.sd-matrix thead th", (els) => els.map((e) => e.textContent.trim()));
    """
        + _NEXT
        + _STATE.replace("return {", "return { headers,")
    )
    state = run_in_browser(document, scenario, tmp_path)
    assert state["headers"] == ["", *(str(n) for n in range(11)), "Not applicable"]
    (submitted,) = state["submitted"]
    assert submitted == {"trust_parl": 2, "trust_pol": 10, "__status": "completed"}


def test_a_dont_know_the_codebook_lists_first_is_stored_under_its_header(tmp_path):
    """ALLBUS-style: -8 "Don't know" before 0 … 10 in the codebook, headers
    "0" … "10" and "Don't know". Column "2" stores 2 and "Don't know" -8 —
    not 1 and 10, as a match by position had it."""

    document = _trust_matrix_document()
    for name in ("trust_parl", "trust_pol"):
        variable = document["variables"][name]
        labels = variable["labels"]
        labels[0]["label"], labels[10]["label"] = "No trust at all", "Complete trust"
        variable["labels"] = [{"code": -8, "label": "Don't know"}, *labels]
        variable["missing"] = [{"code": -8, "label": "Don't know", "kind": "dont_know"}]
    document["pages"][0]["items"][0]["column_labels"].append("Don't know")
    scenario = (
        """
        const headers = await page.$$eval("table.sd-matrix thead th", (els) => els.map((e) => e.textContent.trim()));
        const rows = await page.$$("table.sd-matrix tbody tr");
        await (await rows[0].$$("button.sd-matrix__cell"))[2].click();
        await (await rows[1].$$("button.sd-matrix__cell"))[11].click();
    """
        + _NEXT
        + _STATE.replace("return {", "return { headers,")
    )
    state = run_in_browser(document, scenario, tmp_path)
    assert state["headers"] == ["", *(str(n) for n in range(11)), "Don't know"]
    (submitted,) = state["submitted"]
    assert submitted == {"trust_parl": 2, "trust_pol": -8, "__status": "completed"}


def test_without_headers_the_na_column_is_offered_once(tmp_path):
    labels = [
        {"code": 1, "label": "Never"},
        {"code": 2, "label": "Sometimes"},
        {"code": 3, "label": "Always"},
        {"code": -1, "label": "Not applicable"},
    ]
    missing = [{"code": -1, "label": "Not applicable", "kind": "not_applicable"}]
    document = {
        "schema_version": "1.0",
        "title": "Often",
        "variables": {
            "a": {"scale": "ordinal", "labels": labels, "missing": missing},
            "b": {"scale": "ordinal", "labels": labels, "missing": missing},
        },
        "pages": [
            {
                "name": "p1",
                "items": [
                    {
                        "type": "Matrix",
                        "id": "often",
                        "text": "How often…",
                        "var": ["a", "b"],
                        "na_option": True,
                    }
                ],
            },
            {"name": "done", "kind": "final", "title": "Thanks"},
        ],
    }
    scenario = (
        """
        const headers = await page.$$eval("table.sd-matrix thead th", (els) => els.map((e) => e.textContent.trim()));
        const rows = await page.$$("table.sd-matrix tbody tr");
        await (await rows[0].$$("button.sd-matrix__cell"))[0].click();
        await (await rows[1].$$("button.sd-matrix__cell"))[3].click();
    """
        + _NEXT
        + _STATE.replace("return {", "return { headers,")
    )
    state = run_in_browser(document, scenario, tmp_path)
    assert state["headers"] == ["", "Never", "Sometimes", "Always", "Not applicable"]
    (submitted,) = state["submitted"]
    assert submitted == {"a": 1, "b": -1, "__status": "completed"}


def _gated_on_rows(document: dict[str, Any]) -> dict[str, Any]:
    """The trust matrix, then a page gated on one row and a question gated on
    the other, whose text pipes a row's label."""

    low = {"type": "expression", "op": "<=", "left": {"type": "var", "name": "trust_parl"}}
    document["variables"]["why"] = {"scale": "nominal", "label": "Why", "dtype": "str"}
    document["variables"]["cops"] = {"scale": "nominal", "label": "Cops", "dtype": "str"}
    document["pages"].insert(
        1,
        {
            "name": "follow_up",
            "show_if": {**low, "right": 3},
            "items": [
                {
                    "type": "OpenText",
                    "id": "why",
                    "text": "You said {label:trust_parl}. Why?",
                    "var": "why",
                },
                {
                    "type": "OpenText",
                    "id": "cops",
                    "text": "About the police?",
                    "var": "cops",
                    "show_if": {
                        "type": "expression",
                        "op": "=",
                        "left": {"type": "var", "name": "trust_pol"},
                        "right": 10,
                    },
                },
            ],
        },
    )
    return document


def test_a_condition_on_a_matrix_row_reads_the_rows_variable(tmp_path):
    """Each row is a top-level key, so a page and a question gated on rows show."""

    scenario = (
        _CLICK_MATRIX
        + _NEXT
        + """
        const shown = await page.textContent(".sd-page");
        return { shown, stored: await page.evaluate(() =>
            JSON.parse(localStorage.getItem("siamang_answers_t") || "{}")) };
    """
    )
    result = run_in_browser(_gated_on_rows(_trust_matrix_document()), scenario, tmp_path)
    assert "You said 2. Why?" in result["shown"]
    assert "About the police?" in result["shown"]


def test_a_matrix_that_misses_the_condition_skips_the_gated_page(tmp_path):
    scenario = (
        """
        const rows = await page.$$("table.sd-matrix tbody tr");
        await (await rows[0].$$("button.sd-matrix__cell"))[9].click();
    """
        + _NEXT
        + _STATE
    )
    state = run_in_browser(_gated_on_rows(_trust_matrix_document()), scenario, tmp_path)
    (submitted,) = state["submitted"]
    assert submitted["trust_parl"] == 9
    assert "follow_up" not in state["pages"]
    assert "trust" not in submitted


def _agree_matrix_document() -> dict[str, Any]:
    """Seven statements on the five-point agreement scale, the widest matrix a
    phone commonly gets."""

    scale = ["Strongly disagree", "Disagree", "Neutral", "Agree", "Strongly agree"]
    labels = [{"code": code, "label": label} for code, label in enumerate(scale, start=1)]
    names = [f"s{i}" for i in range(1, 8)]
    return {
        "schema_version": "1.0",
        "title": "Phone",
        "variables": {
            name: {"scale": "ordinal", "label": name, "labels": labels} for name in names
        },
        "pages": [
            {
                "name": "p1",
                "items": [
                    {
                        "type": "Matrix",
                        "id": "agree",
                        "text": "How much do you agree with each of these?",
                        "var": names,
                        "subquestions": [
                            f"Statement number {i}, long enough to wrap on a phone"
                            for i in range(1, 8)
                        ],
                        "column_labels": scale,
                    }
                ],
            },
            {"name": "done", "kind": "final", "title": "Thanks"},
        ],
    }


def test_on_a_phone_a_matrix_row_is_a_card_with_every_answer_on_screen(tmp_path):
    """At 390 px the table was 453 px in a 344 px box, scrolling sideways with
    nothing to say so: Agree and Strongly agree were off screen. Each row is a
    card now, its answers in one row under their own labels, all on screen, and
    a label answers as its circle does. On a wide screen nothing changes."""

    scenario = """
        const measure = () => page.evaluate(() => {
            const wrapper = document.querySelector(".sd-matrix-wrapper");
            const labels = [...document.querySelectorAll(
                "table.sd-matrix tbody tr:first-child .sd-matrix__col-label")];
            return {
                overflow: wrapper.scrollWidth - wrapper.clientWidth,
                header: getComputedStyle(document.querySelector("table.sd-matrix thead")).display,
                labels: labels.map((l) => getComputedStyle(l).display === "none" ? null : l.textContent),
                offscreen: [...document.querySelectorAll("button.sd-matrix__cell")].filter(
                    (b) => b.getBoundingClientRect().right > window.innerWidth).length,
            };
        });
        const wide = await measure();
        await page.setViewportSize({ width: 390, height: 844 });
        const phone = await measure();
        return { wide, phone };
    """
    state = run_in_browser(_agree_matrix_document(), scenario, tmp_path)
    assert state["wide"]["header"] != "none"
    assert state["wide"]["labels"] == [None] * 5
    assert state["phone"]["header"] == "none"
    assert state["phone"]["overflow"] <= 0 and state["phone"]["offscreen"] == 0
    assert state["phone"]["labels"] == [
        "Strongly disagree",
        "Disagree",
        "Neutral",
        "Agree",
        "Strongly agree",
    ]


def test_a_matrix_answered_by_its_labels_on_a_phone_stores_the_codes(tmp_path):
    scenario = (
        """
        await page.setViewportSize({ width: 390, height: 844 });
        const rows = await page.$$("table.sd-matrix tbody tr");
        for (const [i, row] of rows.entries()) {
            await (await row.$$(".sd-matrix__col-label"))[i % 5].click();
        }
    """
        + _NEXT
        + _STATE
    )
    state = run_in_browser(_agree_matrix_document(), scenario, tmp_path)
    (submitted,) = state["submitted"]
    assert [submitted[f"s{i}"] for i in range(1, 8)] == [1, 2, 3, 4, 5, 1, 2]


# ── Slider ───────────────────────────────────────────────────────────────────


def _slider_document() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "title": "Slider",
        "variables": {"likely": {"scale": "interval", "label": "Likely", "valid_range": [0, 10]}},
        "pages": [
            {
                "name": "p1",
                "items": [
                    {
                        "type": "NumericInput",
                        "id": "likely",
                        "var": "likely",
                        "text": "How likely?",
                        "display": "slider",
                        "step": 1,
                    }
                ],
            },
            {"name": "done", "kind": "final", "title": "Thanks"},
        ],
    }


_SLIDER = """
    const shown = () => page.evaluate(() => ({
        value: document.querySelector(".siamang-slider__value").textContent,
        untouched: document.querySelector(".siamang-slider").classList.contains("is-untouched"),
        active: document.querySelectorAll(".siamang-slider__tick.is-active").length,
        valuetext: document.querySelector(".siamang-slider__input").getAttribute("aria-valuetext"),
    }));
"""


def test_an_untouched_slider_reads_as_unanswered_and_stores_nothing(tmp_path):
    """The thumb starts in the middle, but nothing is stored until it is moved:
    it showed the middle (5) in bold as if answered, and someone who agreed
    with it went on with a blank. It reads "—" now, and stays blank."""

    scenario = (
        _SLIDER
        + "const before = await shown();"
        + _NEXT
        + _STATE.replace("return {", "return { before,")
    )
    state = run_in_browser(_slider_document(), scenario, tmp_path)
    assert state["before"] == {
        "value": "—",
        "untouched": True,
        "active": 0,
        "valuetext": "Not answered",
    }
    (submitted,) = state["submitted"]
    assert "likely" not in submitted


def test_a_slider_answers_where_it_is_let_go_even_at_its_start(tmp_path):
    """A click on the thumb where it waits changes no value, so no change event
    comes: letting go answers the value it shows. Moved, it answers as before."""

    let_go = (
        _SLIDER
        + """
        const box = await (await page.$(".siamang-slider__input")).boundingBox();
        await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
        const middle = await shown();
    """
        + _NEXT
        + _STATE.replace("return {", "return { middle,")
    )
    state = run_in_browser(_slider_document(), let_go, tmp_path / "let_go")
    assert state["middle"]["value"] == "5" and not state["middle"]["untouched"]
    assert state["middle"]["active"] == 1 and state["middle"]["valuetext"] is None
    (submitted,) = state["submitted"]
    assert submitted["likely"] == 5
    moved = (
        _SLIDER
        + """
        await page.focus(".siamang-slider__input");
        await page.keyboard.press("ArrowRight");
        const moved = await shown();
    """
        + _NEXT
        + _STATE.replace("return {", "return { moved,")
    )
    state = run_in_browser(_slider_document(), moved, tmp_path / "moved")
    assert state["moved"]["value"] == "6"
    (submitted,) = state["submitted"]
    assert submitted["likely"] == 6


def test_saved_answers_from_the_nested_layout_resume_in_the_flat_one(tmp_path):
    """A respondent who resumes after a redeploy: the old runtime kept the
    matrix nested under its key, and a cell as its position."""

    init = """
        localStorage.setItem("siamang_answers_t", JSON.stringify({
          answers: { trust: { trust_parl: 3, trust_pol: 11 } },
          pageIdx: 0, savedAt: new Date().toISOString() }));
    """
    scenario = (
        """
        await page.click(".siamang-resume-banner .sd-navigation__next-btn");
        await page.waitForTimeout(100);
        const selected = await page.$$eval("button.sd-matrix__cell.is-selected",
            (els) => els.map((el) => el.getAttribute("aria-label")));
    """
        + _NEXT
        + _STATE.replace("return {", "return { selected,")
    )
    state = run_in_browser(_trust_matrix_document(), scenario, tmp_path, init=init)
    assert state["selected"] == ["Parliament: 2", "Police: 10"]
    (submitted,) = state["submitted"]
    assert submitted["trust_parl"] == 2 and submitted["trust_pol"] == 10
    assert "trust" not in submitted


# ── A required matrix ────────────────────────────────────────────────────────


def _required_matrix_document(**matrix: Any) -> dict[str, Any]:
    """A required three-row matrix with an N/A column, then two pages — the
    second one a skip_to's target — and the end."""

    labels = [
        {"code": 1, "label": "Never"},
        {"code": 2, "label": "Sometimes"},
        {"code": 3, "label": "Always"},
        {"code": -1, "label": "Not applicable"},
    ]
    missing = [{"code": -1, "label": "Not applicable", "kind": "not_applicable"}]
    rows = {"tv": "TV", "radio": "Radio", "press": "Press"}
    variables: dict[str, Any] = {
        name: {"scale": "ordinal", "label": label, "labels": labels, "missing": missing}
        for name, label in rows.items()
    }
    variables["why"] = {"scale": "nominal", "dtype": "str"}
    variables["more"] = {"scale": "nominal", "dtype": "str"}
    item = {
        "type": "Matrix",
        "id": "media",
        "text": "How often do you use…",
        "var": list(rows),
        "na_option": True,
        "required": True,
        **matrix,
    }
    return {
        "schema_version": "1.0",
        "title": "Media",
        "variables": variables,
        "pages": [
            {"name": "p1", "items": [item]},
            {
                "name": "middle",
                "items": [{"type": "OpenText", "id": "why", "var": "why", "text": "Why?"}],
            },
            {
                "name": "end",
                "items": [{"type": "OpenText", "id": "more", "var": "more", "text": "More?"}],
            },
            {"name": "done", "kind": "final", "title": "Thanks"},
        ],
    }


# `pick(row, column)` clicks a cell (the N/A column is the last); `held()` is
# what the page says: its messages, which matrix rows are marked as missing,
# and the pages the respondent has been on.
_MATRIX_STEPS = """
    const pick = async (row, col) => {
        const rows = await page.$$("table.sd-matrix tbody tr");
        await (await rows[row].$$("button.sd-matrix__cell"))[col].click();
        await page.waitForTimeout(50);
    };
    const held = async () => ({
        errors: await page.$$eval(".sd-question__error", (es) => es.map((e) => e.textContent)),
        missing: await page.$$eval("table.sd-matrix tbody tr",
            (trs) => trs.map((tr) => tr.classList.contains("is-missing"))),
        pages: await page.evaluate(() => window.__T.pages.slice()),
    });
"""


def test_a_required_matrix_answered_in_every_row_goes_on(tmp_path):
    scenario = (
        _MATRIX_STEPS
        + """
        await pick(0, 0); await pick(1, 1); await pick(2, 2);
    """
        + _NEXT
        + "return await held();"
    )
    state = run_in_browser(_required_matrix_document(), scenario, tmp_path)
    assert state == {"errors": [], "missing": [], "pages": ["p1", "middle"]}


def test_a_required_matrix_holds_next_until_every_row_is_answered(tmp_path):
    """One row of three used to count as the answer Required asks for. Next
    now names the rows left and marks them until each is answered."""

    scenario = (
        _MATRIX_STEPS
        + _NEXT
        + """
        const none = await held();
        await pick(0, 1);
        const first = await held();
    """
        + _NEXT
        + """
        const one = await held();
        await pick(2, 0);
        const two = await held();
    """
        + _NEXT
        + """
        const still = await held();
        await pick(1, 2);
    """
        + _NEXT
        + """
        return { none, first, one, two, still, done: await held() };
    """
    )
    state = run_in_browser(_required_matrix_document(), scenario, tmp_path)
    # Nothing answered: the usual message, and every row is marked.
    assert state["none"]["errors"] == ["This question requires an answer."]
    assert state["none"]["missing"] == [True, True, True]
    # An answer clears the message; the rows still empty stay marked.
    assert state["first"]["errors"] == [] and state["first"]["missing"] == [False, True, True]
    assert state["one"]["errors"] == ["Please answer every row."]
    assert state["one"]["missing"] == [False, True, True]
    assert state["two"]["missing"] == [False, True, False]
    assert state["still"]["errors"] == ["Please answer every row."]
    assert state["still"]["pages"] == ["p1"]
    assert state["done"]["pages"] == ["p1", "middle"]


def test_not_applicable_answers_a_required_matrix_row(tmp_path):
    scenario = (
        _MATRIX_STEPS
        + """
        await pick(0, 3); await pick(1, 0); await pick(2, 3);
    """
        + _NEXT
        + _NEXT
        + _NEXT
        + _STATE
    )
    state = run_in_browser(_required_matrix_document(), scenario, tmp_path)
    (submitted,) = state["submitted"]
    assert submitted == {"tv": -1, "radio": 1, "press": -1, "__status": "completed"}


def test_a_matrix_skip_to_still_fires_on_any_answered_row(tmp_path):
    """Skip to is "on Next, after any answer": one row is an answer to an
    optional matrix; a required one is held first, then skips when complete."""

    scenario = (
        _MATRIX_STEPS
        + """
        await pick(1, 0);
    """
        + _NEXT
        + "return await held();"
    )
    optional = run_in_browser(
        _required_matrix_document(required=False, skip_to="end"), scenario, tmp_path / "optional"
    )
    assert optional["pages"] == ["p1", "end"]
    scenario = (
        _MATRIX_STEPS
        + """
        await pick(1, 0);
    """
        + _NEXT
        + """
        const one = await held();
        await pick(0, 0); await pick(2, 0);
    """
        + _NEXT
        + "return { one, all: await held() };"
    )
    required = run_in_browser(
        _required_matrix_document(skip_to="end"), scenario, tmp_path / "required"
    )
    assert required["one"]["errors"] == ["Please answer every row."]
    assert required["one"]["pages"] == ["p1"]
    assert required["all"]["pages"] == ["p1", "end"]


def test_a_resumed_required_matrix_still_needs_the_rows_left(tmp_path):
    scenario = (
        _MATRIX_STEPS
        + _RELOAD
        + """
        await pick(0, 0); await pick(1, 1);
    """
        + _autosaved("answers.tv === 1 && answers.radio === 2")
        + """
        await reload(".siamang-resume-banner");
        await page.click(".siamang-resume-banner .sd-navigation__next-btn");
        await page.waitForTimeout(250);
    """
        + _NEXT
        + """
        const resumed = await held();
        await pick(2, 2);
    """
        + _NEXT
        + _NEXT
        + _NEXT
        + """
        const T = await page.evaluate(() => window.__T);
        return { resumed, submitted: T.submitted };
    """
    )
    state = run_in_browser(_required_matrix_document(), scenario, tmp_path)
    assert state["resumed"]["errors"] == ["Please answer every row."]
    assert state["resumed"]["missing"] == [False, False, True]
    (submitted,) = state["submitted"]
    assert submitted == {"tv": 1, "radio": 2, "press": 3, "__status": "completed"}


def test_the_rows_message_is_the_surveys_wording(tmp_path):
    document = _required_matrix_document()
    document["ui"] = {"required_rows_text": "Noch {n} Zeilen beantworten"}
    scenario = (
        _MATRIX_STEPS
        + """
        await pick(0, 0);
    """
        + _NEXT
        + "return await held();"
    )
    state = run_in_browser(document, scenario, tmp_path)
    assert state["errors"] == ["Noch 2 Zeilen beantworten"]


# Design mode (Studio's walkthrough) posts its trace to the parent frame; a
# page without one is its own parent, so the trace comes back to it.
_TRACES = """
    window.SIAMANG_DESIGN = {};
    window.__traces = [];
    window.addEventListener("message", (e) => {
        if (e.data && e.data.type === "siamang:trace") window.__traces.push(e.data);
    });
"""


def test_the_walkthrough_counts_a_matrix_answered_once_every_row_is(tmp_path):
    """The trace's `answered` counts what Required asks for; a skip's
    `answered` is whether it fires, which is any row."""

    trace = """
        await page.waitForTimeout(300);
        const t = await page.evaluate(() => window.__traces[window.__traces.length - 1]);
        return { answered: t.answered, visible: t.visible, skips: t.skips };
    """
    scenario = (
        _MATRIX_STEPS
        + "const last = async () => {"
        + trace
        + "};"
        + """
        const before = await last();
        await pick(0, 0);
        const one = await last();
        await pick(1, 0); await pick(2, 3);
        return { before, one, all: await last() };
    """
    )
    state = run_in_browser(
        _required_matrix_document(skip_to="end"), scenario, tmp_path, init=_TRACES
    )
    skip = {"id": "media", "target": "end"}
    assert state["before"] == {"answered": 0, "visible": 1, "skips": [{**skip, "answered": False}]}
    assert state["one"] == {"answered": 0, "visible": 1, "skips": [{**skip, "answered": True}]}
    assert state["all"] == {"answered": 1, "visible": 1, "skips": [{**skip, "answered": True}]}


def test_the_rows_a_required_matrix_misses_are_marked_only_by_next(tmp_path):
    """Leaving the matrix unanswered and a script's own message on it say what
    they say without marking a row: the rows are marked once Next has held the
    matrix for them — for assistive technology too (aria-invalid). Any message
    on a required matrix used to mark every empty row, and the marks stayed
    while the respondent worked down the rows."""

    document = _required_matrix_document()
    document["variables"]["note"] = {"scale": "nominal", "dtype": "str"}
    document["pages"][0]["items"].append(
        {"type": "OpenText", "id": "note", "var": "note", "text": "Anything else?"}
    )
    document["scripts"] = [
        {
            "type": "custom",
            "trigger": "onAnswer",
            "target": "media",
            "code": (
                "if (!answers.__errors__) answers.__errors__ = {};\n"
                'if (answers.tv === 1) answers.__errors__.media = "Not TV, surely?";\n'
                "else delete answers.__errors__.media;\n"
            ),
        }
    ]
    scenario = (
        _MATRIX_STEPS
        + """
        const invalid = () => page.$$eval("table.sd-matrix tbody tr", (trs) => trs.map((tr) =>
            [...tr.querySelectorAll("button.sd-matrix__cell")]
                .every((b) => b.getAttribute("aria-invalid") === "true")));
        await page.focus("table.sd-matrix button[tabindex='0']");
        await page.focus("input.sd-input");
        await page.waitForTimeout(100);
        const blurred = await held();
        await pick(0, 1);
        const answered = await held();
        await pick(0, 0);
        const script = await held();
        await pick(0, 1);
    """
        + _NEXT
        + """
        return { blurred, answered, script, next: await held(), invalid: await invalid() };
    """
    )
    state = run_in_browser(document, scenario, tmp_path)
    assert state["blurred"]["errors"] == ["This question requires an answer."]
    assert state["blurred"]["missing"] == [False, False, False]
    assert state["answered"]["missing"] == [False, False, False]
    assert state["script"]["errors"] == ["Not TV, surely?"]
    assert state["script"]["missing"] == [False, False, False]
    assert state["next"]["errors"] == ["Please answer every row."]
    assert state["next"]["missing"] == [False, True, True]
    assert state["invalid"] == [False, True, True]


def test_a_matrix_row_a_script_set_to_null_is_not_an_answer(tmp_path):
    """A row key holding null (a script clearing the row) holds no answer: a
    required matrix with nothing else says "This question requires an
    answer.", and a skip_to does not fire on it. The key alone used to count
    as an answer to the matrix."""

    script = {
        "type": "custom",
        "trigger": "onPageEnter",
        "target": "p1",
        "code": "answers.tv = null;",
    }
    required = _required_matrix_document()
    required["scripts"] = [script]
    scenario = _MATRIX_STEPS + _NEXT + "return await held();"
    state = run_in_browser(required, scenario, tmp_path / "required")
    assert state["errors"] == ["This question requires an answer."]
    assert state["missing"] == [True, True, True]
    optional = _required_matrix_document(required=False, skip_to="end")
    optional["scripts"] = [script]
    state = run_in_browser(optional, scenario, tmp_path / "optional")
    assert state["pages"] == ["p1", "middle"]


def test_a_timed_required_matrix_waits_for_every_row(tmp_path):
    """A timed question's automatic Next is an ordinary Next: on a required
    matrix answered in one row it is held like the respondent's own, and the
    respondent finishes the rows and goes on."""

    document = _required_matrix_document()
    document["scripts"] = [{"type": "timed_question", "question": "media", "seconds": 1}]
    scenario = (
        _MATRIX_STEPS
        + """
        await pick(0, 0);
        await page.waitForSelector(".sd-question__error", { timeout: 10000 });
        const timed = await held();
        await pick(1, 0); await pick(2, 0);
    """
        + _NEXT
        + "return { timed, after: await held() };"
    )
    state = run_in_browser(document, scenario, tmp_path)
    assert state["timed"] == {
        "errors": ["Please answer every row."],
        "missing": [False, True, True],
        "pages": ["p1"],
    }
    assert state["after"]["pages"] == ["p1", "middle"]


# ── A matrix from the keyboard ───────────────────────────────────────────────

# `press(...keys)` presses keys where the focus is; `chosen()` is each row's
# chosen column (-1: none; the N/A column is the last), `focused()` the cell
# (or the class of the button) that has the focus, `tabbable()` the cells in
# the tab order.
_MATRIX_KEYS = """
    const press = async (...keys) => {
        for (const key of keys) { await page.keyboard.press(key); await page.waitForTimeout(60); }
    };
    const chosen = () => page.$$eval("table.sd-matrix tbody tr", (trs) => trs.map((tr) =>
        [...tr.querySelectorAll("button.sd-matrix__cell")]
            .findIndex((b) => b.getAttribute("aria-pressed") === "true")));
    const focused = () => page.evaluate(() =>
        document.activeElement.getAttribute("aria-label") || document.activeElement.className);
    const tabbable = () => page.$$eval("table.sd-matrix button.sd-matrix__cell[tabindex='0']",
        (bs) => bs.map((b) => b.getAttribute("aria-label")));
"""


def test_a_required_matrix_is_answered_row_by_row_from_the_keyboard(tmp_path):
    """Up and Down move the focus to the same column of the row below or
    above, Left and Right answer the row with the cell they move to — the N/A
    column included — and Space or Enter chooses the cell the focus is on. Up
    and Down used to leave the focus on row 1, N/A was out of the keys' reach
    and Space or Enter pressed Next, so a required matrix, which needs every
    row, could not be finished from the keyboard."""

    scenario = (
        _MATRIX_STEPS
        + _MATRIX_KEYS
        + """
        await page.focus("table.sd-matrix button.sd-matrix__cell[tabindex='0']");
        await press(" ");
        const space = { chosen: await chosen(), ...(await held()) };
        await press("ArrowDown");
        const down = await focused();
        await press("ArrowRight", "ArrowDown", "ArrowRight", "ArrowRight");
        const rows = { chosen: await chosen(), focused: await focused(), tabbable: await tabbable() };
        await press("ArrowUp", "Enter");
        const enter = { chosen: await chosen(), focused: await focused(), ...(await held()) };
        await press("Tab");
        const tab = await focused();
        await press("Enter");
        await page.waitForTimeout(250);
        return { space, down, rows, enter, tab, pages: await page.evaluate(() => window.__T.pages.slice()) };
    """
    )
    state = run_in_browser(_required_matrix_document(), scenario, tmp_path)
    assert state["space"] == {
        "chosen": [0, -1, -1],
        "errors": [],
        "missing": [False, False, False],
        "pages": ["p1"],
    }
    assert state["down"] == "Radio: Never"
    assert state["rows"] == {
        "chosen": [0, 1, 3],
        "focused": "Press: Not applicable",
        "tabbable": ["Press: Not applicable"],
    }
    assert state["enter"]["chosen"] == [0, 3, 3]
    assert state["enter"]["focused"] == "Radio: Not applicable"
    assert state["enter"]["pages"] == ["p1"]
    assert state["tab"] == "sd-btn sd-navigation__next-btn"
    assert state["pages"] == ["p1", "middle"]


# The focus-ring look of the button at `selector`'s `index`: its box shadow,
# outline and whether it has the focus, once transitions are over.
_LOOK = """
    const look = async (selector, index) => {
        await page.waitForTimeout(200);
        return page.$$eval(selector, (els, i) => {
            const cs = getComputedStyle(els[i]);
            return { shadow: cs.boxShadow, outline: cs.outlineStyle,
                     selected: els[i].getAttribute("aria-pressed") === "true",
                     focused: els[i].matches(":focus-visible") };
        }, index);
    };
"""


def test_the_focus_shows_on_a_chosen_matrix_cell_and_maxdiff_pick(tmp_path):
    """A chosen cell's inner ring replaced the focus ring, so the focus on a
    chosen cell did not show at all — and ← → leave it on one, ↑ ↓ onto a row
    answered the same way changed nothing on screen. A chosen MaxDiff pick was
    the same. Both now carry the focus ring over their own."""

    scenario = (
        _MATRIX_STEPS
        + _MATRIX_KEYS
        + _LOOK
        + """
        await pick(0, 1);
        await pick(1, 1);
        const cells = "table.sd-matrix tbody tr td:nth-child(3) button.sd-matrix__cell";
        await page.$$eval(cells, (bs) => bs[0].focus());
        await press("ArrowDown");
        return { focused: await focused(), on: await look(cells, 1), off: await look(cells, 0),
                 plain: await look(cells, 2) };
    """
    )
    state = run_in_browser(_required_matrix_document(), scenario, tmp_path / "matrix")
    assert state["focused"] == "Radio: Sometimes"
    on, off = state["on"], state["off"]
    assert on["selected"] and on["focused"] and off["selected"] and not off["focused"]
    assert on["shadow"] != off["shadow"]
    assert on["shadow"].startswith(off["shadow"] + ", ")
    scenario = (
        _MATRIX_KEYS
        + _LOOK
        + """
        const picks = "table.sd-maxdiff__task button.sd-maxdiff__pick";
        const tasks = await page.$$("table.sd-maxdiff__task");
        const first = (await tasks[1].$$("button.sd-maxdiff__pick"))[0];
        await page.$$eval(picks, (bs) => bs[0].focus());
        await press(" ");
        await first.focus();
        await press(" ");
        const index = await page.$$eval(picks, (bs) => bs.indexOf(document.activeElement));
        return { on: await look(picks, index), off: await look(picks, 0) };
    """
    )
    state = run_in_browser(_trade_off_document(), scenario, tmp_path / "maxdiff")
    on, off = state["on"], state["off"]
    assert on["selected"] and on["focused"] and off["selected"] and not off["focused"]
    assert on["shadow"].startswith(off["shadow"] + ", ")


def test_enter_and_space_on_a_button_are_the_buttons_own(tmp_path):
    """Enter or Space outside a text field goes on, as before — but on a
    button they are the button's: Previous goes back, a rating point is
    chosen. Both used to press Next."""

    scenario = (
        _MATRIX_KEYS
        + """
        const pages = () => page.evaluate(() => window.__T.pages.slice());
        await page.evaluate(() => document.activeElement && document.activeElement.blur());
        await press("Enter");
        await page.waitForTimeout(250);
        const outside = await pages();
        await page.focus(".sd-navigation__prev-btn");
        await press("Enter");
        await page.waitForTimeout(250);
        return { outside, back: await pages() };
    """
    )
    state = run_in_browser(_required_matrix_document(required=False), scenario, tmp_path / "prev")
    assert state["outside"] == ["p1", "middle"]
    assert state["back"] == ["p1", "middle", "p1"]
    scenario = (
        _MATRIX_KEYS
        + """
        await page.focus(".sd-rating__item:nth-child(3)");
        await press(" ");
        const space = await page.$$eval(".sd-rating__item.is-selected", (els) => els.map((e) => e.textContent.trim()));
        await page.focus(".sd-rating__item:nth-child(4)");
        await press("Enter");
        const enter = await page.$$eval(".sd-rating__item.is-selected", (els) => els.map((e) => e.textContent.trim()));
    """
        + _STATE.replace("return {", "return { space, enter,")
    )
    state = run_in_browser(_likert_gate_document(), scenario, tmp_path / "rating")
    assert (state["space"], state["enter"]) == (["3"], ["4"])
    assert state["submitted"] == [] and state["pages"] == ["p1"]


def _media_document() -> dict[str, Any]:
    """The last page before the end: a video on its question, and details in
    its body."""

    return {
        "schema_version": "1.0",
        "title": "Clip",
        "variables": {"why": {"scale": "nominal", "dtype": "str"}},
        "pages": [
            {
                "name": "p1",
                "body": "<details><summary>Why we ask</summary><p>Because.</p></details>",
                "items": [
                    {
                        "type": "OpenText",
                        "id": "why",
                        "var": "why",
                        "text": "Why?",
                        "media": {"kind": "video", "url": "clip.mp4"},
                    }
                ],
            },
            {"name": "done", "kind": "final", "title": "Thanks"},
        ],
    }


def test_a_players_and_a_summarys_keys_are_their_own(tmp_path):
    """Space on a video plays or pauses it, Enter on a summary opens its
    details: neither goes on. On the last page Space on the player submitted
    the survey. Elsewhere Space still goes on."""

    scenario = (
        _MATRIX_KEYS
        + """
        const pages = () => page.evaluate(() => window.__T.pages.slice());
        await page.focus("video", { timeout: 3000 });
        await press(" ", "Enter");
        await page.waitForTimeout(250);
        const video = { tag: await page.evaluate(() => document.activeElement.tagName), pages: await pages() };
        await page.focus("summary", { timeout: 3000 });
        await press("Enter");
        await page.waitForTimeout(250);
        const summary = { open: await page.$eval("details", (d) => d.open), pages: await pages() };
        await page.evaluate(() => document.activeElement.blur());
        await press(" ");
        await page.waitForTimeout(250);
    """
        + _STATE.replace("return {", "return { video, summary,")
    )
    state = run_in_browser(_media_document(), scenario, tmp_path)
    assert state["video"] == {"tag": "VIDEO", "pages": ["p1"]}
    assert state["summary"] == {"open": True, "pages": ["p1"]}
    assert state["submitted"] == [{"__status": "completed"}]


def _dropdown_document() -> dict[str, Any]:
    """A page before, then a required searchable dropdown of twelve fruits —
    a list long enough to scroll, as a dropdown's usually is."""

    names = "Apple Pear Plum Cherry Grape Lemon Mango Kiwi Lime Peach Fig Date".split()
    fruits = [{"code": code, "label": name} for code, name in enumerate(names, start=1)]
    return {
        "schema_version": "1.0",
        "title": "Fruit",
        "variables": {
            "name": {"scale": "nominal", "dtype": "str"},
            "fruit": {"scale": "nominal", "labels": fruits},
        },
        "pages": [
            {
                "name": "p1",
                "items": [{"type": "OpenText", "id": "name", "var": "name", "text": "Name?"}],
            },
            {
                "name": "p2",
                "items": [
                    {
                        "type": "SingleChoice",
                        "id": "fruit",
                        "var": "fruit",
                        "text": "Fruit?",
                        "display": "dropdown",
                        "required": True,
                    }
                ],
            },
            {"name": "done", "kind": "final", "title": "Thanks"},
        ],
    }


def test_a_required_dropdown_is_answered_from_the_keyboard_alone(tmp_path):
    """Enter on the button opened the menu with the focus in its search box,
    and there nothing worked: the options took no keys, Esc did nothing and
    Tab left the menu open. In the search box ↓ ↑ now move along the options,
    Enter chooses the one they are on and gives the focus back to the button,
    Esc closes the menu and Tab away closes it; typing narrows the list to
    what matches and Enter takes the first. On the button ↓ opens the menu and
    Esc closes it rather than going back a page.

    A list long enough to scroll was a Tab stop of its own (Chromium 130+):
    Tab from the search box put the focus on it and left the menu open, and
    there ↓ ↑ Enter did nothing and Esc went back a page. Tab now leaves the
    menu, and the keys work wherever in the menu the focus is (a click on the
    list's scroll bar puts it on the list)."""

    scenario = (
        _MATRIX_KEYS
        + _NEXT
        + """
        const pages = () => page.evaluate(() => window.__T.pages.slice());
        const menu = () => page.$$eval(".siamang-search-dropdown__menu", (m) => m.length);
        const label = () => page.$eval(".siamang-search-dropdown__trigger", (b) => b.textContent);
        const activeOption = () => page.evaluate(() => {
            const box = document.querySelector(".siamang-search-dropdown__search");
            const id = box && box.getAttribute("aria-activedescendant");
            return id ? document.getElementById(id).textContent : null;
        });
        const role = () => page.evaluate(() => document.activeElement.getAttribute("role"));
        const errors = () => page.$$eval(".sd-question__error", (es) => es.map((e) => e.textContent));
        await page.focus(".siamang-search-dropdown__trigger");
        await press("Enter");
        const opened = { menu: await menu(), role: await role(), errors: await errors() };
        await press("ArrowDown", "ArrowDown");
        const down = await activeOption();
        await press("ArrowUp");
        const up = await activeOption();
        await press("Escape");
        const escaped = { menu: await menu(), focused: await focused(), label: await label(), pages: await pages(),
            errors: await errors() };
        await press("ArrowDown");
        await page.keyboard.type("plu");
        const typed = await activeOption();
        await press("Enter");
        const picked = { menu: await menu(), focused: await focused(), label: await label() };
        await press("Enter", "Shift+Tab");
        await press("Escape");
        const closedOnButton = { menu: await menu(), pages: await pages() };
        await press("Enter");
        await page.focus(".siamang-search-dropdown__options");
        await press("ArrowUp");
        const onList = { role: await role(), active: await activeOption() };
        await press("Escape");
        const listEscaped = { menu: await menu(), focused: await focused(), label: await label(),
            pages: await pages() };
        await press("Enter", "Tab");
        const tabbed = { menu: await menu(), inside: await page.evaluate(() =>
            !!document.activeElement.closest(".siamang-search-dropdown")), pages: await pages() };
    """
        + _NEXT
        + _STATE.replace(
            "return {",
            "return { opened, down, up, escaped, typed, picked, closedOnButton, onList, "
            "listEscaped, tabbed,",
        )
    )
    state = run_in_browser(_dropdown_document(), scenario, tmp_path)
    # Opening the list says nothing about the answer it is there to take.
    assert state["opened"] == {"menu": 1, "role": "combobox", "errors": []}
    assert (state["down"], state["up"]) == ("Pear", "Apple")
    assert state["escaped"] == {
        "menu": 0,
        "focused": "sd-input siamang-search-dropdown__trigger",
        "label": "— Select —",
        "pages": ["p1", "p2"],
        "errors": [],
    }
    assert state["typed"] == "Plum"
    assert state["picked"] == {
        "menu": 0,
        "focused": "sd-input siamang-search-dropdown__trigger",
        "label": "Plum",
    }
    assert state["closedOnButton"] == {"menu": 0, "pages": ["p1", "p2"]}
    # Opened on Plum, ↑ from the list itself moves to Pear; Esc there closes.
    assert state["onList"] == {"role": "listbox", "active": "Pear"}
    assert state["listEscaped"] == {
        "menu": 0,
        "focused": "sd-input siamang-search-dropdown__trigger",
        "label": "Plum",
        "pages": ["p1", "p2"],
    }
    assert state["tabbed"] == {"menu": 0, "inside": False, "pages": ["p1", "p2"]}
    assert state["submitted"] == [{"fruit": 3, "__status": "completed"}]


def test_a_required_question_is_checked_when_the_focus_leaves_it(tmp_path):
    """Opening a required dropdown moves the focus from its button to its
    search box, and that blur checked the question: "This question requires
    an answer." appeared, and was announced (role=alert), before anything
    could be chosen - on a click as on Enter. The focus moving between a
    question's own controls no longer checks it; leaving the question does."""

    scenario = (
        _MATRIX_KEYS
        + _NEXT
        + """
        const errors = () => page.$$eval(".sd-question__error", (es) =>
            es.map((e) => [e.textContent, e.getAttribute("role")]));
        await page.click(".siamang-search-dropdown__trigger");
        const clicked = await errors();
        await press("Escape");
        const escaped = { errors: await errors(), focused: await focused() };
        await press("Tab");
        const left = { errors: await errors(), focused: await focused() };
        return { clicked, escaped, left };
    """
    )
    state = run_in_browser(_dropdown_document(), scenario, tmp_path)
    assert state["clicked"] == []
    assert state["escaped"] == {
        "errors": [],
        "focused": "sd-input siamang-search-dropdown__trigger",
    }
    assert state["left"] == {
        "errors": [["This question requires an answer.", "alert"]],
        "focused": "sd-btn sd-navigation__prev-btn",
    }


# ── MaxDiff and Conjoint ─────────────────────────────────────────────────────


def _trade_off_document() -> dict[str, Any]:
    items = [{"code": code, "label": label} for code, label in enumerate("ABCD", start=1)]
    variables: dict[str, Any] = {
        f"md_t{t}_{side}": {"scale": "nominal", "labels": items}
        for t in (1, 2)
        for side in ("best", "worst")
    }
    variables["md_version"] = {"scale": "nominal"}
    for name in ("cj_t1", "cj_t2", "cj_version"):
        variables[name] = {"scale": "nominal"}
    variables["liked"] = {"scale": "nominal", "dtype": "str"}
    levels = [{"code": 1, "label": "Cheap"}, {"code": 2, "label": "Dear"}]
    brands = [{"code": 1, "label": "X"}, {"code": 2, "label": "Y"}]
    return {
        "schema_version": "1.0",
        "title": "Trade-offs",
        "variables": variables,
        "pages": [
            {
                "name": "p1",
                "items": [
                    {
                        "type": "MaxDiff",
                        "id": "md",
                        "text": "Pick",
                        "var": [
                            "md_t1_best",
                            "md_t1_worst",
                            "md_t2_best",
                            "md_t2_worst",
                            "md_version",
                        ],
                        "per_task": 3,
                        "tasks": 2,
                        "versions": 1,
                    },
                    {
                        "type": "Conjoint",
                        "id": "cj",
                        "text": "Choose",
                        "var": ["cj_t1", "cj_t2", "cj_version"],
                        "attributes": [
                            {"name": "price", "levels": levels},
                            {"name": "brand", "levels": brands},
                        ],
                        "alternatives": 2,
                        "tasks": 2,
                        "versions": 1,
                    },
                ],
            },
            {
                "name": "p2",
                "items": [
                    {
                        "type": "OpenText",
                        "id": "liked",
                        "var": "liked",
                        "text": "Why {label:md_t1_best}?",
                        "show_if": {
                            "type": "expression",
                            "op": "=",
                            "left": {"type": "var", "name": "cj_t1"},
                            "right": 2,
                        },
                    },
                ],
            },
            {"name": "done", "kind": "final", "title": "Thanks"},
        ],
    }


def test_maxdiff_and_conjoint_tasks_are_stored_by_variable(tmp_path):
    scenario = (
        """
        const tasks = await page.$$("table.sd-maxdiff__task");
        for (const task of tasks) {
          const picks = await task.$$("button.sd-maxdiff__pick");
          await picks[0].click();   // best: the first item
          await picks[3].click();   // worst: the second item
        }
        const choices = await page.$$(".sd-conjoint__task");
        for (const task of choices) {
          const picks = await task.$$("button.sd-conjoint__pick");
          await picks[1].click();
        }
        const firstBest = await page.$eval("table.sd-maxdiff__task td.sd-maxdiff__item",
            (el) => el.textContent);
    """
        + _NEXT
        + """
        const shown = await page.textContent(".sd-page");
    """
        + _NEXT
        + _STATE.replace("return {", "return { firstBest, shown,")
    )
    state = run_in_browser(_trade_off_document(), scenario, tmp_path)
    (submitted,) = state["submitted"]
    assert "md" not in submitted and "cj" not in submitted
    for key in ("md_t1_best", "md_t1_worst", "md_t2_best", "md_t2_worst", "md_version"):
        assert key in submitted, key
    assert submitted["md_version"] == 0
    assert submitted["cj_t1"] == 2 and submitted["cj_t2"] == 2 and submitted["cj_version"] == 0
    # A condition on a conjoint task fires, and a MaxDiff pick pipes its label.
    assert f"Why {state['firstBest']}?" in state["shown"]


def test_a_required_maxdiff_and_conjoint_still_need_every_task(tmp_path):
    """Unchanged by the matrix rule: a required MaxDiff or conjoint is held with
    the usual message until every task is answered."""

    document = _trade_off_document()
    for item in document["pages"][0]["items"]:
        item["required"] = True
    # Picked in the page rather than with the mouse, which moves the focus: the
    # question left then says it is not finished, and its message pushes the
    # next question down under the pointer between the press and the release.
    scenario = (
        """
        const press = async (group, button, i, k) => {
          await page.evaluate(([group, button, i, k]) =>
            document.querySelectorAll(group)[i].querySelectorAll(button)[k].click(),
            [group, button, i, k]);
          await page.waitForTimeout(50);
        };
        const task = async (i) => {
          await press("table.sd-maxdiff__task", "button.sd-maxdiff__pick", i, 0);
          await press("table.sd-maxdiff__task", "button.sd-maxdiff__pick", i, 3);
          await press(".sd-conjoint__task", "button.sd-conjoint__pick", i, 1);
        };
        await task(0);
    """
        + _NEXT
        + """
        const errors = await page.$$eval(".sd-question__error", (es) => es.map((e) => e.textContent));
        const pages = await page.evaluate(() => window.__T.pages.slice());
        await task(1);
    """
        + _NEXT
        + """
        return { errors, pages, after: await page.evaluate(() => window.__T.pages.slice()) };
    """
    )
    state = run_in_browser(document, scenario, tmp_path)
    assert state["errors"] == ["This question requires an answer."] * 2
    assert state["pages"] == ["p1"]
    assert state["after"] == ["p1", "p2"]


# Every pick of `_trade_off_document`'s page clicked with the mouse, the last
# one the conjoint's second option of its second task.
_CLICK_TRADE_OFFS = """
    const tasks = await page.$$("table.sd-maxdiff__task");
    for (const task of tasks) {
      const picks = await task.$$("button.sd-maxdiff__pick");
      await picks[0].click();
      await picks[3].click();
    }
    const choices = await page.$$(".sd-conjoint__task");
    for (const task of choices) {
      const picks = await task.$$("button.sd-conjoint__pick");
      await picks[1].click();
    }
"""


def test_after_a_click_enter_and_space_go_on_with_every_pick_kept(tmp_path):
    """The mouse leaves the focus on the pick it pressed (Chromium does), and
    Enter or Space there were the pick's own keys: a MaxDiff or conjoint pick
    is a toggle, so the key took back the pick just made and the page stayed,
    and the next Next went on without that task. After a press of the mouse
    they go on, every pick kept — as they did before a button's keys were its
    own, and as a rating point clicked and Enter do. Once the focus moves
    (Tab, then Shift+Tab back) Enter is the pick's own again."""

    pages = "const pages = () => page.evaluate(() => window.__T.pages.slice());\n"
    scenario = (
        _MATRIX_KEYS
        + pages
        + _CLICK_TRADE_OFFS
        + """
        const focus = await page.evaluate(() => document.activeElement.getAttribute("aria-label"));
        await press("Enter");
        await page.waitForTimeout(250);
        const entered = await pages();
    """
        + _NEXT
        + _STATE.replace("return {", "return { focus, entered,")
    )
    state = run_in_browser(_trade_off_document(), scenario, tmp_path / "enter")
    assert state["focus"] == "Choice 2, option 2"
    assert state["entered"] == ["p1", "p2"]
    (submitted,) = state["submitted"]
    for key in ("md_t1_best", "md_t1_worst", "md_t2_best", "md_t2_worst", "md_version"):
        assert key in submitted, key
    assert submitted["cj_t1"] == submitted["cj_t2"] == 2

    scenario = (
        _MATRIX_KEYS
        + pages
        + """
        const pressed = () => page.$$eval("table.sd-maxdiff__task button[aria-pressed='true']",
            (bs) => bs.map((b) => b.getAttribute("aria-label")));
        const picks = await (await page.$$("table.sd-maxdiff__task"))[0].$$("button.sd-maxdiff__pick");
        await picks[0].click();
        await press("Tab", "Shift+Tab", "Enter");
        const moved = { pressed: await pressed(), pages: await pages() };
        await picks[0].click();
        await picks[3].click();
        const clicked = await pressed();
        await press(" ");
        await page.waitForTimeout(250);
        const spaced = await pages();
    """
        + _NEXT
        + _STATE.replace("return {", "return { moved, clicked, spaced,")
    )
    state = run_in_browser(_trade_off_document(), scenario, tmp_path / "space")
    assert state["moved"] == {"pressed": [], "pages": ["p1"]}
    assert len(state["clicked"]) == 2
    assert state["spaced"] == ["p1", "p2"]
    (submitted,) = state["submitted"]
    assert "md_t1_best" in submitted and "md_t1_worst" in submitted

    scenario = (
        _MATRIX_KEYS
        + """
        await (await page.$$(".sd-rating__item"))[1].click();
        await press("Enter");
        await page.waitForTimeout(250);
    """
        + _STATE
    )
    state = run_in_browser(_likert_gate_document(), scenario, tmp_path / "rating")
    assert state["submitted"] == [{"sat": 2, "__status": "completed"}]


def _choice_document() -> dict[str, Any]:
    """A picture choice (a SingleChoice whose options carry images), then a
    MultiChoice, then the end."""

    pets = [{"code": 1, "label": "Cat"}, {"code": 2, "label": "Dog"}]
    fruits = [{"code": 1, "label": "Apple"}, {"code": 2, "label": "Pear"}]
    pictures = [
        {
            **pet,
            "media": {"kind": "image", "url": f"{pet['label'].lower()}.png", "alt": pet["label"]},
        }
        for pet in pets
    ]
    return {
        "schema_version": "1.0",
        "title": "Choices",
        "variables": {
            "pet": {"scale": "nominal", "labels": pets},
            "fruit": {"scale": "nominal", "labels": fruits},
        },
        "pages": [
            {
                "name": "p1",
                "items": [
                    {
                        "type": "SingleChoice",
                        "id": "pet",
                        "var": "pet",
                        "text": "Which?",
                        "choices": pictures,
                    }
                ],
            },
            {
                "name": "p2",
                "items": [{"type": "MultiChoice", "id": "fruit", "var": "fruit", "text": "Which?"}],
            },
            {"name": "done", "kind": "final", "title": "Thanks"},
        ],
    }


def test_after_a_click_on_a_choice_enter_goes_on_and_space_is_its_own(tmp_path):
    """A click on a radio or a checkbox leaves the focus on it, and every key
    but Tab was ignored there: Enter did not go on, though it does anywhere
    else outside a text field - "click a picture, press Enter" stayed on the
    page. Enter now goes on with the choice kept; Space stays the radio's or
    the box's own (it checks the radio, checks or unchecks the box)."""

    scenario = (
        _MATRIX_KEYS
        + """
        const pages = () => page.evaluate(() => window.__T.pages.slice());
        const checked = (type) => page.$$eval(`input[type=${type}]`, (is) => is.map((i) => i.checked));
        await page.click("label.sd-radio >> nth=1");
        const focus = await page.evaluate(() => document.activeElement.type);
        await press(" ");
        await page.waitForTimeout(250);
        const radioSpace = { pages: await pages(), checked: await checked("radio") };
        await press("Enter");
        await page.waitForTimeout(250);
        const radioEnter = await pages();
        await page.click("label.sd-checkbox >> nth=0");
        await press(" ");
        const unticked = await checked("checkbox");
        await press(" ");
        const ticked = await checked("checkbox");
        await press("Enter");
        await page.waitForTimeout(250);
    """
        + _STATE.replace("return {", "return { focus, radioSpace, radioEnter, unticked, ticked,")
    )
    state = run_in_browser(_choice_document(), scenario, tmp_path)
    assert state["focus"] == "radio"
    assert state["radioSpace"] == {"pages": ["p1"], "checked": [False, True]}
    assert state["radioEnter"] == ["p1", "p2"]
    assert (state["unticked"], state["ticked"]) == ([False, False], [True, False])
    assert state["pages"] == ["p1", "p2", "done"]
    assert state["submitted"] == [{"pet": 2, "fruit": [1], "__status": "completed"}]


# ── Piping ───────────────────────────────────────────────────────────────────


def test_label_piping_inserts_the_chosen_options_label(tmp_path):
    document = {
        "schema_version": "1.0",
        "title": "Piping",
        "variables": {
            "fruit": {
                "scale": "nominal",
                "labels": [{"code": 1, "label": "Apple"}, {"code": 2, "label": "Pear"}],
            },
            "why": {"scale": "nominal", "dtype": "str"},
        },
        "pages": [
            {
                "name": "p1",
                "items": [
                    {"type": "SingleChoice", "id": "fruit", "var": "fruit", "text": "Which fruit?"}
                ],
            },
            {
                "name": "p2",
                "title": "About {label:fruit}",
                "items": [
                    {
                        "type": "OpenText",
                        "id": "why",
                        "var": "why",
                        "text": "Why {label:fruit} (code {answer:fruit})?",
                    }
                ],
            },
        ],
    }
    scenario = (
        """
        await page.click("text=Pear");
    """
        + _NEXT
        + """
        return await page.textContent(".sd-page");
    """
    )
    shown = run_in_browser(document, scenario, tmp_path)
    assert "About Pear" in shown
    assert "Why Pear (code 2)?" in shown


# ── Conditions on an unanswered question ─────────────────────────────────────


def _var(name: str) -> dict[str, Any]:
    return {"type": "var", "name": name}


def _cmp(op: str, left: Any, right: Any) -> dict[str, Any]:
    return {"type": "expression", "op": op, "left": left, "right": right}


def _attention_document() -> dict[str, Any]:
    # Studio's attention check for a question without codes: screened out when
    # the check was answered and is not the expected value.
    failed = _cmp("and", _cmp("!=", _var("attn"), None), _cmp("!=", _var("attn"), 3))
    return {
        "schema_version": "1.0",
        "title": "Attention",
        "variables": {
            "attn": {"scale": "ratio"},
            "skipped": {"scale": "nominal", "dtype": "str"},
            "maybe": {"scale": "nominal", "dtype": "str"},
            "b": {"scale": "nominal", "dtype": "str"},
        },
        "pages": [
            {
                "name": "p1",
                "title": "One",
                "items": [
                    {"type": "NumericInput", "id": "attn", "var": "attn", "text": "Type 3"},
                    {
                        "type": "OpenText",
                        "id": "skipped",
                        "var": "skipped",
                        "text": "Skipped",
                        "show_if": _cmp("=", _var("attn"), None),
                    },
                    {
                        "type": "OpenText",
                        "id": "maybe",
                        "var": "maybe",
                        "text": "Maybe",
                        "show_if": _cmp("in", _var("attn"), [None, 3]),
                    },
                ],
                "next_if": [{"condition": failed, "target": "out"}],
            },
            {
                "name": "p2",
                "title": "Two",
                "items": [{"type": "OpenText", "id": "b", "var": "b", "text": "B?"}],
            },
            {"name": "done", "kind": "final", "title": "Thanks"},
            {"name": "out", "kind": "disqualification", "title": "Sorry"},
        ],
    }


@pytest.mark.parametrize(
    ("typed", "shown", "route"),
    [
        ("", ["Type 3", "Skipped", "Maybe"], ["p1", "p2"]),
        ("3", ["Type 3", "Maybe"], ["p1", "p2"]),
        ("5", ["Type 3"], ["p1", "out"]),
    ],
)
def test_a_condition_on_null_holds_for_a_question_nobody_answered(tmp_path, typed, shown, route):
    scenario = (
        f"""
        const typed = {json.dumps(typed)};
        if (typed) {{
            await page.fill("input[type=number]", typed);
            await page.click("body");
            await page.waitForTimeout(100);
        }}
        const shown = await page.$$eval(".sd-question__title", (ts) => ts.map(
            (t) => t.querySelector("span:not(.sd-question__num)").textContent));
    """
        + _NEXT
        + _STATE.replace("return {", "return { shown,")
    )
    state = run_in_browser(_attention_document(), scenario, tmp_path)
    # "attn = null" and "attn in [null, 3]" hold while the check is empty, and
    # "attn != null and attn != 3" screens out only a wrong answer: a
    # respondent who left the optional check empty goes on.
    assert state["shown"] == shown
    assert state["pages"] == route


def _two_failed_checks() -> dict[str, Any]:
    # A screen-out after two failed attention checks of three, written as
    # Studio writes it: the OR of an AND per pair of checks. A check with
    # codes fails on any code but those that pass, and one without codes when
    # it was answered with none of them, so a skipped check never counts.
    fails = [
        _cmp("in", _var("swim"), [3, 4]),
        _cmp("in", _var("trap"), [1, 2]),
        _cmp(
            "and",
            _cmp("!=", _var("word"), None),
            _cmp("not in", _var("word"), ["blue", "Blue"]),
        ),
    ]
    first, second, third = fails
    return _cmp(
        "or",
        _cmp("or", _cmp("and", first, second), _cmp("and", first, third)),
        _cmp("and", second, third),
    )


def _attention_checks_document() -> dict[str, Any]:
    agree = ["Strongly disagree", "Disagree", "Agree", "Strongly agree"]
    colors = ["Red", "Green", "Blue"]

    def coded(labels: list[str]) -> list[dict[str, Any]]:
        return [{"code": code, "label": label} for code, label in enumerate(labels, 1)]

    def check(item: dict[str, Any], passes: Any) -> dict[str, Any]:
        return {**item, "metadata": {"attention_check": True, "expected": passes}}

    return {
        "schema_version": "1.0",
        "title": "Attention checks",
        "variables": {
            "swim": {"scale": "ordinal", "labels": coded(agree)},
            "trap": {"scale": "nominal", "labels": coded(colors)},
            "word": {"scale": "nominal", "dtype": "str"},
            "b": {"scale": "nominal", "dtype": "str"},
        },
        "pages": [
            {
                "name": "p1",
                "title": "One",
                "items": [
                    # A nonsensical statement: either disagree answer passes.
                    check(_choice("swim", "I swim across the Atlantic to get to work"), [1, 2]),
                    check(_choice("trap", "Choose the third color"), 3),
                    check(_text("word", "Type the word blue"), ["blue", "Blue"]),
                ],
                "next_if": [{"condition": _two_failed_checks(), "target": "out"}],
            },
            {"name": "p2", "title": "Two", "items": [_text("b", "B?")]},
            {"name": "done", "kind": "final", "title": "Thanks"},
            {"name": "out", "kind": "disqualification", "title": "Sorry"},
        ],
    }


@pytest.mark.parametrize(
    ("swim", "trap", "word", "route"),
    [
        (2, 3, "Blue", ["p1", "p2"]),  # every check passed
        (3, 3, "blue", ["p1", "p2"]),  # one failed
        (3, 1, "Blue", ["p1", "out"]),  # two failed
        (1, 2, "red", ["p1", "out"]),  # two failed, the statement passed
        (4, 3, "", ["p1", "p2"]),  # one failed, the word skipped
        (4, 1, "", ["p1", "out"]),  # two failed, the word skipped
    ],
)
def test_a_screen_out_after_two_failed_checks_counts_every_answer_that_passes(
    tmp_path, swim, trap, word, route
):
    scenario = (
        f"""
        const q = (n) => page.locator(".sd-question").nth(n);
        await q(0).locator(".sd-choice-label").nth({swim - 1}).click();
        await q(1).locator(".sd-choice-label").nth({trap - 1}).click();
        const word = {json.dumps(word)};
        if (word) {{
            await q(2).locator("input, textarea").first().fill(word);
            await page.click("body");
            await page.waitForTimeout(100);
        }}
    """
        + _NEXT
        + _STATE
    )
    state = run_in_browser(_attention_checks_document(), scenario, tmp_path)
    assert state["pages"] == route
    # The engine's own reading of the rule, which simulate() follows, agrees.
    answers = {"swim": swim, "trap": trap, "word": word or None}
    screened_out = Expression.from_dict(_two_failed_checks()).evaluate(answers)
    assert screened_out == (route[-1] == "out")


# ── Nested blocks ────────────────────────────────────────────────────────────


def _text(name: str, text: str, **extra: Any) -> dict[str, Any]:
    return {"type": "OpenText", "id": name, "var": name, "text": text, **extra}


def _choice(name: str, text: str) -> dict[str, Any]:
    return {"type": "SingleChoice", "id": name, "var": name, "text": text}


def _nested_conditions_document() -> dict[str, Any]:
    texts = ["before", "inner1", "inner2", "deep1", "after"]
    yes_no = [{"code": 1, "label": "Yes"}, {"code": 2, "label": "No"}]
    return {
        "schema_version": "1.0",
        "title": "Nested",
        "variables": {
            "route": {"scale": "nominal", "labels": yes_no},
            "depth": {"scale": "nominal", "labels": yes_no},
            **{name: {"scale": "nominal", "dtype": "str"} for name in texts},
        },
        "pages": [
            {"name": "p1", "items": [_choice("route", "Route?"), _choice("depth", "Depth?")]},
            {
                "name": "p2",
                "items": [
                    {
                        "type": "Block",
                        "title": "Outer",
                        "items": [
                            _text("before", "Before"),
                            {
                                "type": "Block",
                                "title": "Inner",
                                "show_if": _cmp("=", _var("route"), 1),
                                "items": [
                                    _text("inner1", "Inner 1", required=True),
                                    _text("inner2", "Inner 2"),
                                    {
                                        "type": "Block",
                                        "title": "Deep",
                                        "hide_if": _cmp("=", _var("depth"), 2),
                                        "items": [_text("deep1", "Deep 1")],
                                    },
                                ],
                            },
                            _text("after", "After"),
                        ],
                    }
                ],
            },
            {"name": "done", "kind": "final", "title": "Thanks"},
        ],
    }


# The questions shown, by their text.
_SHOWN = """
    const shown = async () => page.$$eval(".sd-question__title", (ts) => ts.map(
        (t) => t.querySelector("span:not(.sd-question__num)").textContent));
"""


@pytest.mark.parametrize(
    ("route", "depth", "shown"),
    [
        ("1", "1", ["Before", "Inner 1", "Inner 2", "Deep 1", "After"]),
        ("1", "2", ["Before", "Inner 1", "Inner 2", "After"]),
        # The inner block hides everything in it, the deep block's own
        # condition notwithstanding.
        ("2", "1", ["Before", "After"]),
    ],
)
def test_a_nested_blocks_condition_hides_its_questions(tmp_path, route, depth, shown):
    scenario = (
        _SHOWN
        + f"""
        const q = (n) => page.locator(".sd-question").nth(n);
        await q(0).locator(".sd-choice-label").nth({int(route) - 1}).click();
        await q(1).locator(".sd-choice-label").nth({int(depth) - 1}).click();
    """
        + _NEXT
        + """
        const onTwo = await shown();
    """
        + _NEXT
        + _STATE.replace("return {", "return { onTwo,")
    )
    state = run_in_browser(_nested_conditions_document(), scenario, tmp_path)
    assert state["onTwo"] == shown
    if route == "1":
        # "Inner 1" is required and shown: Next holds.
        assert state["pages"] == ["p1", "p2"] and state["submitted"] == []
    else:
        # A required question in a hidden block does not hold anyone up.
        assert state["pages"] == ["p1", "p2", "done"]
        (submitted,) = state["submitted"]
        assert "inner1" not in submitted


def _nested_shuffle_document() -> dict[str, Any]:
    inner = [f"I{i}" for i in range(1, 7)]
    unit = ["U1", "U2", "U3"]
    mixed = ["X1", "X2", "X3", "X4"]
    names = ["B1", *inner, "A1", *mixed, *unit]
    return {
        "schema_version": "1.0",
        "title": "Nested shuffle",
        "variables": {name.lower(): {"scale": "nominal", "dtype": "str"} for name in names},
        "pages": [
            {
                "name": "p1",
                "items": [
                    {
                        "type": "Block",
                        "title": "Kept",
                        "items": [
                            _text("b1", "B1"),
                            {
                                "type": "Block",
                                "randomize": True,
                                "items": [_text(n.lower(), n) for n in inner],
                            },
                            _text("a1", "A1"),
                        ],
                    },
                    {
                        "type": "Block",
                        "title": "Mixed",
                        "randomize": True,
                        "items": [
                            *[_text(n.lower(), n) for n in mixed[:3]],
                            {"type": "Block", "items": [_text(n.lower(), n) for n in unit]},
                            _text("x4", "X4"),
                        ],
                    },
                ],
            },
            {"name": "done", "kind": "final", "title": "Thanks"},
        ],
    }


def test_nested_blocks_shuffle_inside_themselves_and_move_as_one(tmp_path):
    scenario = _SHOWN + "return await shown();"
    order = run_in_browser(_nested_shuffle_document(), scenario, tmp_path, init=_FIXED_RANDOM)
    inner, mixed = order[1:7], order[8:]
    # A nested block's randomize shuffles its own questions; the block around
    # it keeps its order.
    assert order[0] == "B1" and order[7] == "A1"
    assert sorted(inner) == [f"I{i}" for i in range(1, 7)] and inner != sorted(inner)
    # A shuffling block deals its entries, and a nested block is one of them:
    # its questions stay together and in their order.
    assert sorted(mixed) == ["U1", "U2", "U3", "X1", "X2", "X3", "X4"]
    at = mixed.index("U1")
    assert mixed[at : at + 3] == ["U1", "U2", "U3"]
    assert [x for x in mixed if x.startswith("X")] != ["X1", "X2", "X3", "X4"]


# ── Wide MultiChoice ─────────────────────────────────────────────────────────


def _wide_document() -> dict[str, Any]:
    yes_no = [{"code": 0, "label": "No"}, {"code": 1, "label": "Yes"}]
    return {
        "schema_version": "1.0",
        "title": "Brands",
        "variables": {
            **{
                name: {"scale": "nominal", "label": label, "labels": yes_no}
                for name, label in (
                    ("brands_1", "Acme"),
                    ("brands_2", "Globex"),
                    ("brands_99", "None of these"),
                )
            },
            "acme_why": {"scale": "nominal", "dtype": "str"},
        },
        "pages": [
            {
                "name": "p1",
                "items": [
                    {
                        "type": "MultiChoice",
                        "id": "brands",
                        "text": "Which brands do you know?",
                        "var": ["brands_1", "brands_2", "brands_99"],
                        "mode": "wide",
                        "choices": [
                            {"code": 1, "label": "Acme"},
                            {"code": 2, "label": "Globex"},
                            {"code": 99, "label": "None of these"},
                        ],
                        "exclusive": [99],
                    }
                ],
            },
            {
                "name": "about_acme",
                "show_if": {
                    "type": "expression",
                    "op": "=",
                    "left": {"type": "var", "name": "brands_1"},
                    "right": 1,
                },
                "items": [
                    {"type": "OpenText", "id": "acme_why", "var": "acme_why", "text": "Acme?"}
                ],
            },
            {"name": "done", "kind": "final", "title": "Thanks"},
        ],
    }


def test_a_wide_multichoice_writes_one_and_zero_per_choice(tmp_path):
    scenario = (
        """
        await page.click("text=Acme");
        await page.click("text=Globex");
        await page.click("text=None of these");   // exclusive: clears the others
        const afterNone = await page.$$eval(".sd-checkbox input", (els) => els.map((e) => e.checked));
        await page.click("text=Acme");            // and a regular choice clears it
        const afterAcme = await page.$$eval(".sd-checkbox input", (els) => els.map((e) => e.checked));
    """
        + _NEXT
        + """
        const shown = await page.textContent(".sd-page");
    """
        + _NEXT
        + _STATE.replace("return {", "return { afterNone, afterAcme, shown,")
    )
    state = run_in_browser(_wide_document(), scenario, tmp_path)
    assert state["afterNone"] == [False, False, True]
    assert state["afterAcme"] == [True, False, False]
    # The page gated on `brands_1 = 1` is shown.
    assert "Acme?" in state["shown"]
    (submitted,) = state["submitted"]
    assert submitted["brands_1"] == 1
    assert submitted["brands_2"] == 0
    assert submitted["brands_99"] == 0
    assert "brands" not in submitted


def test_a_wide_multichoice_left_empty_writes_nothing(tmp_path):
    scenario = (
        """
        await page.click("text=Acme");
        await page.click("text=Acme");   // unchecked again: the question is unanswered
    """
        + _NEXT
        + _STATE
    )
    state = run_in_browser(_wide_document(), scenario, tmp_path)
    (submitted,) = state["submitted"]
    assert not {"brands", "brands_1", "brands_2", "brands_99"} & set(submitted)
    assert "about_acme" not in state["pages"]


def test_a_wide_answer_saved_as_a_list_of_names_resumes_as_ones_and_zeros(tmp_path):
    init = """
        localStorage.setItem("siamang_answers_t", JSON.stringify({
          answers: { brands: ["brands_2"] }, pageIdx: 0, savedAt: new Date().toISOString() }));
    """
    scenario = (
        """
        await page.click(".siamang-resume-banner .sd-navigation__next-btn");
        await page.waitForTimeout(100);
    """
        + _NEXT
        + _STATE
    )
    state = run_in_browser(_wide_document(), scenario, tmp_path, init=init)
    (submitted,) = state["submitted"]
    assert (submitted["brands_1"], submitted["brands_2"], submitted["brands_99"]) == (0, 1, 0)
    assert "brands" not in submitted


def _aware_bought_document() -> dict[str, Any]:
    yes_no = [{"code": 0, "label": "No"}, {"code": 1, "label": "Yes"}]
    brands = [(1, "acme", "Acme"), (2, "globex", "Globex")]

    def wide(name: str, text: str, gated: bool) -> dict[str, Any]:
        choices: list[dict[str, Any]] = [{"code": c, "label": label} for c, _, label in brands]
        if gated:
            # Globex is offered only to those aware of it.
            choices[1]["show_if"] = _cmp("=", _var("aware_globex"), 1)
        return {
            "type": "MultiChoice",
            "id": name,
            "text": text,
            "var": [f"{name}_{key}" for _, key, _ in brands],
            "mode": "wide",
            "choices": choices,
        }

    return {
        "schema_version": "1.0",
        "title": "Aware and bought",
        "variables": {
            f"{name}_{key}": {"scale": "nominal", "labels": yes_no}
            for name in ("aware", "bought")
            for _, key, _ in brands
        },
        "pages": [
            {"name": "p1", "items": [wide("aware", "Which do you know?", False)]},
            {"name": "p2", "items": [wide("bought", "Which have you bought?", True)]},
            {"name": "done", "kind": "final", "title": "Thanks"},
        ],
    }


def test_a_wide_option_its_condition_hid_is_missing_not_zero(tmp_path):
    """0 is "offered and not chosen": an option the respondent was never
    shown stores nothing, so the base of its column is who saw it."""

    scenario = (
        """
        await page.click("text=Acme");
    """
        + _NEXT
        + """
        const offered = await page.$$eval(".sd-choice-label", (els) => els.map((e) => e.textContent));
        await page.click("text=Acme");
    """
        + _NEXT
        + _STATE.replace("return {", "return { offered,")
    )
    state = run_in_browser(_aware_bought_document(), scenario, tmp_path)
    assert state["offered"] == ["Acme"]
    (submitted,) = state["submitted"]
    assert submitted == {
        "aware_acme": 1,
        "aware_globex": 0,
        "bought_acme": 1,
        "__status": "completed",
    }


def test_a_wide_option_offered_and_not_chosen_is_zero(tmp_path):
    scenario = (
        """
        await page.click("text=Acme");
        await page.click("text=Globex");
    """
        + _NEXT
        + """
        await page.click("text=Acme");
    """
        + _NEXT
        + _STATE
    )
    state = run_in_browser(_aware_bought_document(), scenario, tmp_path)
    (submitted,) = state["submitted"]
    assert (submitted["bought_acme"], submitted["bought_globex"]) == (1, 0)


def _aware_bought_one_page() -> dict[str, Any]:
    document = _aware_bought_document()
    aware, bought, done = document["pages"]
    document["pages"] = [{"name": "p1", "items": aware["items"] + bought["items"]}, done]
    return document


@pytest.mark.parametrize("globex", ["offered after", "hidden after"])
def test_a_wide_option_follows_an_answer_given_after_it(tmp_path, globex):
    """The answer that offers or hides a wide option can come after the wide
    question was answered — on the same page here. Globex offered afterward
    and left unchecked is 0, not missing; hidden afterward it is missing, not
    the 0 it had while it was offered."""

    aware, bought = "page.locator('text=Acme').nth(0)", "page.locator('text=Acme').nth(1)"
    globex_aware = "page.locator('text=Globex').nth(0)"
    first = "" if globex == "offered after" else f"await {globex_aware}.click();"
    scenario = (
        f"""
        await {aware}.click();
        {first}
        await page.waitForTimeout(100);
        await {bought}.click();
        await page.waitForTimeout(100);
        await {globex_aware}.click();
        await page.waitForTimeout(100);
        const offered = await page.$$eval(".sd-choice-label", (els) => els.map((e) => e.textContent));
    """
        + _NEXT
        + _STATE.replace("return {", "return { offered,")
    )
    state = run_in_browser(_aware_bought_one_page(), scenario, tmp_path)
    (submitted,) = state["submitted"]
    if globex == "offered after":
        assert state["offered"] == ["Acme", "Globex", "Acme", "Globex"]
        assert (submitted["aware_globex"], submitted["bought_acme"]) == (1, 1)
        assert submitted.get("bought_globex") == 0
    else:
        assert state["offered"] == ["Acme", "Globex", "Acme"]
        assert (submitted["aware_globex"], submitted["bought_acme"]) == (0, 1)
        assert "bought_globex" not in submitted


def _chained_gates_document() -> dict[str, Any]:
    """One page: a region; "aware" offers Globex in the North only; "bought"
    offers Globex to those shown it in "aware" who left it unchecked
    (aware_globex = 0) — a condition on another wide question's 0."""

    document = _aware_bought_one_page()
    document["variables"]["region"] = {
        "scale": "nominal",
        "labels": [{"code": 1, "label": "North"}, {"code": 2, "label": "South"}],
    }
    (page, done) = document["pages"]
    aware, bought = page["items"]
    aware["choices"][1]["show_if"] = _cmp("=", _var("region"), 1)
    bought["choices"][1]["show_if"] = _cmp("=", _var("aware_globex"), 0)
    region = {"type": "SingleChoice", "id": "region", "var": "region", "text": "Region?"}
    document["pages"] = [{"name": "p1", "items": [region, aware, bought]}, done]
    return document


def test_a_wide_option_gated_on_another_wide_question_settles_with_it(tmp_path):
    """North, Acme in both: aware_globex 0 offers Globex in "bought" (0).
    Then South: aware's Globex goes, so aware_globex is missing — and with it
    bought's Globex, whose condition read aware_globex = 0. Settled on the
    answers from before the change, bought_globex stayed 0."""

    scenario = (
        """
        await page.click("text=North");
        await page.waitForTimeout(100);
        await page.locator("text=Acme").nth(0).click();
        await page.waitForTimeout(100);
        await page.locator("text=Acme").nth(1).click();
        await page.waitForTimeout(100);
        const before = await page.$$eval(".sd-choice-label", (els) => els.map((e) => e.textContent));
        await page.click("text=South");
        await page.waitForTimeout(100);
        const after = await page.$$eval(".sd-choice-label", (els) => els.map((e) => e.textContent));
    """
        + _NEXT
        + _STATE.replace("return {", "return { before, after,")
    )
    state = run_in_browser(_chained_gates_document(), scenario, tmp_path)
    assert state["before"] == ["North", "South", "Acme", "Globex", "Acme", "Globex"]
    assert state["after"] == ["North", "South", "Acme", "Acme"]
    (submitted,) = state["submitted"]
    assert submitted == {"region": 2, "aware_acme": 1, "bought_acme": 1, "__status": "completed"}


def _likert_gate_document(start: int = 1) -> dict[str, Any]:
    """A 1–5 satisfaction Likert, then a wide "what to improve" whose Price
    is offered to the dissatisfied only (sat <= 3)."""

    points = range(start, start + 5)
    return {
        "schema_version": "1.0",
        "title": "Satisfaction",
        "variables": {
            "sat": {"scale": "ordinal", "labels": _labels(list(points))},
            "imp_service": {"scale": "nominal", "labels": _labels([0, 1])},
            "imp_price": {"scale": "nominal", "labels": _labels([0, 1])},
        },
        "pages": [
            {
                "name": "p1",
                "items": [
                    {
                        "type": "LikertScale",
                        "id": "sat",
                        "var": "sat",
                        "text": "How satisfied are you?",
                        "points": 5,
                        "start": start,
                    },
                    {
                        "type": "MultiChoice",
                        "id": "imp",
                        "text": "What should we improve?",
                        "mode": "wide",
                        "var": ["imp_service", "imp_price"],
                        "choices": [
                            {"code": 1, "label": "Service"},
                            {"code": 2, "label": "Price", "show_if": _cmp("<=", _var("sat"), 3)},
                        ],
                    },
                ],
            },
            {"name": "done", "kind": "final", "title": "Thanks"},
        ],
    }


def test_a_likert_answered_with_a_digit_key_settles_a_wide_option_too(tmp_path):
    """sat 2 offers Price, left unchecked (0); the key "5" then answers sat
    and Price is no longer offered, so imp_price is missing — as when 5 is
    clicked. The key wrote past the answer handling and left the 0."""

    scenario = (
        """
        await (await page.$$(".sd-rating__item"))[1].click();
        await page.waitForTimeout(100);
        await page.click("text=Service");
        await page.waitForTimeout(100);
        const before = await page.$$eval(".sd-choice-label", (els) => els.map((e) => e.textContent));
        await page.evaluate(() => document.activeElement && document.activeElement.blur());
        await page.keyboard.press("5");
        await page.waitForTimeout(100);
        const after = await page.$$eval(".sd-choice-label", (els) => els.map((e) => e.textContent));
    """
        + _NEXT
        + _STATE.replace("return {", "return { before, after,")
    )
    state = run_in_browser(_likert_gate_document(), scenario, tmp_path)
    assert (state["before"], state["after"]) == (["Service", "Price"], ["Service"])
    (submitted,) = state["submitted"]
    assert submitted == {"sat": 5, "imp_service": 1, "__status": "completed"}


def test_a_digit_key_answers_a_likert_that_starts_at_zero_with_its_own_points(tmp_path):
    """0 … 4: "4" is the last point, and "5" — no point of this scale — leaves
    the answer alone. It stored 5, a value the scale does not have."""

    scenario = (
        """
        const selected = () => page.$$eval(".sd-rating__item.is-selected", (els) => els.map((e) => e.textContent.trim()));
        await page.evaluate(() => document.activeElement && document.activeElement.blur());
        await page.keyboard.press("4");
        await page.waitForTimeout(100);
        const afterFour = await selected();
        await page.keyboard.press("5");
        await page.waitForTimeout(100);
        const afterFive = await selected();
    """
        + _NEXT
        + _STATE.replace("return {", "return { afterFour, afterFive,")
    )
    state = run_in_browser(_likert_gate_document(start=0), scenario, tmp_path)
    assert (state["afterFour"], state["afterFive"]) == (["4"], ["4"])
    (submitted,) = state["submitted"]
    assert submitted == {"sat": 4, "__status": "completed"}


# ── Other (please specify), None of the above, Not applicable ────────────────


def _choices_document(**fruit: Any) -> dict[str, Any]:
    fruit_labels = [
        {"code": 1, "label": "Apple"},
        {"code": 2, "label": "Pear"},
        {"code": -66, "label": "Other"},
    ]
    na = {"code": -1, "label": "Not applicable", "kind": "not_applicable"}
    scale = [{"code": n, "label": str(n)} for n in (1, 2, 3)]
    return {
        "schema_version": "1.0",
        "title": "Choices",
        "variables": {
            "fruit": {"scale": "nominal", "labels": fruit_labels},
            "snacks": {
                "scale": "nominal",
                "labels": [{"code": 1, "label": "Chips"}, {"code": 2, "label": "Nuts"}],
            },
            "drinks": {"scale": "nominal", "labels": [{"code": 1, "label": "Tea"}]},
            "city": {
                "scale": "nominal",
                "labels": [{"code": 1, "label": "Oslo"}, {"code": 2, "label": "Rome"}],
            },
            "pet": {"scale": "nominal", "labels": [{"code": 1, "label": "Cat"}]},
            "sat": {
                "scale": "ordinal",
                "labels": scale + [{"code": -1, "label": "N/A"}],
                "missing": [na],
            },
            "ease": {"scale": "ordinal", "labels": scale},
            "why": {"scale": "nominal", "dtype": "str"},
        },
        "pages": [
            {
                "name": "p1",
                "items": [
                    {
                        "type": "SingleChoice",
                        "id": "fruit",
                        "var": "fruit",
                        "text": "Fruit?",
                        "other_specify": True,
                        "choices": fruit_labels[:2],
                        **fruit,
                    },
                    {
                        "type": "MultiChoice",
                        "id": "snacks",
                        "var": "snacks",
                        "text": "Snacks?",
                        "other_specify": True,
                    },
                    {
                        "type": "MultiChoice",
                        "id": "drinks",
                        "var": "drinks",
                        "text": "Drinks?",
                        "other_specify": True,
                    },
                    {
                        "type": "SingleChoice",
                        "id": "city",
                        "var": "city",
                        "text": "City?",
                        "display": "dropdown",
                        "other_specify": True,
                    },
                    {
                        "type": "SingleChoice",
                        "id": "pet",
                        "var": "pet",
                        "text": "Pet?",
                        "none_of_above": True,
                    },
                    {
                        "type": "LikertScale",
                        "id": "sat",
                        "var": "sat",
                        "text": "Sat?",
                        "points": 3,
                        "na_option": True,
                    },
                    {
                        "type": "LikertScale",
                        "id": "ease",
                        "var": "ease",
                        "text": "Ease?",
                        "points": 3,
                        "na_option": True,
                    },
                ],
            },
            {
                "name": "p2",
                "items": [
                    {
                        "type": "OpenText",
                        "id": "why",
                        "var": "why",
                        "text": "Why {label:fruit}? You also like {label:snacks}.",
                        "show_if": {
                            "type": "expression",
                            "op": "contains",
                            "left": {"type": "var", "name": "snacks"},
                            "right": 1,
                        },
                    },
                ],
            },
            {"name": "done", "kind": "final", "title": "Thanks"},
        ],
    }


_ANSWER_CHOICES = (
    """
    const q = (n) => page.locator(".sd-question-slot").nth(n);
    await q(0).locator("text=Other").click();
    await q(0).locator(".sd-other-input__field").fill("Kiwi");
    await q(1).locator("text=Chips").click();
    await q(1).locator("text=Other").click();
    await q(1).locator(".sd-other-input__field").fill("Salsa");
    await q(2).locator("text=Other").click();
    await q(2).locator(".sd-other-input__field").fill("Kvass");
    await q(3).locator(".siamang-search-dropdown__trigger").click();
    const offered = await q(3).locator(".siamang-search-dropdown__option").allTextContents();
    await q(3).locator(".siamang-search-dropdown__option", { hasText: "Other" }).click();
    await q(3).locator(".sd-other-input__field").fill("Lima");
    await q(4).locator("text=None of the above").click();
    await q(5).locator(".sd-rating__na label").click();
    await q(6).locator(".sd-rating__na label").click();
    await page.click("body");
"""
    + _NEXT
)


def test_other_stores_its_code_and_its_text_under_variable_other(tmp_path):
    scenario = (
        _ANSWER_CHOICES
        + """
        const shown = await page.textContent(".sd-page");
    """
        + _NEXT
        + _STATE.replace("return {", "return { offered, shown,")
    )
    state = run_in_browser(_choices_document(), scenario, tmp_path)
    (submitted,) = state["submitted"]
    # One key per variable, values are codes; the text sits beside them.
    assert submitted["fruit"] == -66 and submitted["fruit_other"] == "Kiwi"
    assert submitted["snacks"] == [1, -66] and submitted["snacks_other"] == "Salsa"
    # A second MultiChoice with Other keeps its own text.
    assert submitted["drinks"] == [-66] and submitted["drinks_other"] == "Kvass"
    # The dropdown offers Other at the end of its list.
    assert state["offered"] == ["Oslo", "Rome", "Other"]
    assert submitted["city"] == -66 and submitted["city_other"] == "Lima"
    # None of the above and N/A are codes; N/A without a declared code stays "na".
    assert submitted["pet"] == -77
    assert submitted["sat"] == -1
    assert submitted["ease"] == "na"
    # `snacks contains 1` holds on a list (it could not on {selected, otherText}),
    # and {label:…} of Other pipes the text typed.
    assert "Why Kiwi? You also like Chips, Salsa." in state["shown"]
    assert not any(
        isinstance(value, dict) for key, value in submitted.items() if not key.startswith("__")
    )


def test_choosing_something_else_drops_the_other_text(tmp_path):
    scenario = (
        """
        const q = (n) => page.locator(".sd-question-slot").nth(n);
        await q(0).locator("text=Other").click();
        await q(0).locator(".sd-other-input__field").fill("Kiwi");
        await q(0).locator("text=Pear").click();
        await q(1).locator("text=Other").click();
        await q(1).locator(".sd-other-input__field").fill("Salsa");
        await q(1).locator("text=Other").click();
        await q(1).locator("text=Nuts").click();
    """
        + _NEXT
        + _NEXT
        + _STATE
    )
    state = run_in_browser(_choices_document(), scenario, tmp_path)
    (submitted,) = state["submitted"]
    assert submitted["fruit"] == 2 and "fruit_other" not in submitted
    assert submitted["snacks"] == [2] and "snacks_other" not in submitted


def test_a_choice_named_by_other_code_is_the_other_option(tmp_path):
    """`metadata.other_code` naming a choice: that choice gets the text box and
    no second "Other" is added."""

    document = _choices_document(
        choices=[{"code": 1, "label": "Apple"}, {"code": 3, "label": "Something else"}],
        metadata={"other_code": 3},
    )
    document["variables"]["fruit"]["labels"].append({"code": 3, "label": "Something else"})
    scenario = (
        """
        const q = page.locator(".sd-question-slot").nth(0);
        const labels = await q.locator(".sd-choice-label").allTextContents();
        await q.locator("text=Something else").click();
        await q.locator(".sd-other-input__field").fill("Kiwi");
    """
        + _NEXT
        + _NEXT
        + _STATE.replace("return {", "return { labels,")
    )
    state = run_in_browser(document, scenario, tmp_path)
    assert state["labels"] == ["Apple", "Something else"]
    (submitted,) = state["submitted"]
    assert submitted["fruit"] == 3 and submitted["fruit_other"] == "Kiwi"


def test_answers_saved_with_the_old_sentinels_resume_as_codes(tmp_path):
    init = """
        localStorage.setItem("siamang_answers_t", JSON.stringify({
          answers: {
            fruit: { code: "__other__", text: "Kiwi" },
            snacks: { selected: [1, "__other__"], otherText: "Salsa" },
            pet: "__none__", sat: "na", ease: "na",
          }, pageIdx: 0, savedAt: new Date().toISOString() }));
    """
    scenario = (
        """
        await page.click(".siamang-resume-banner .sd-navigation__next-btn");
        await page.waitForTimeout(100);
        const typed = await page.locator(".sd-other-input__field").first().inputValue();
    """
        + _NEXT
        + _NEXT
        + _STATE.replace("return {", "return { typed,")
    )
    state = run_in_browser(_choices_document(), scenario, tmp_path, init=init)
    assert state["typed"] == "Kiwi"
    (submitted,) = state["submitted"]
    assert submitted["fruit"] == -66 and submitted["fruit_other"] == "Kiwi"
    assert submitted["snacks"] == [1, -66] and submitted["snacks_other"] == "Salsa"
    assert submitted["pet"] == -77
    assert submitted["sat"] == -1 and submitted["ease"] == "na"


def test_a_wide_multichoice_other_writes_its_text_beside_the_zeros(tmp_path):
    document = _wide_document()
    document["pages"][0]["items"][0]["other_specify"] = True
    scenario = (
        """
        await page.click("text=Globex");
        await page.click("text=Other");
        await page.fill(".sd-other-input__field", "Initech");
    """
        + _NEXT
        + _STATE
    )
    state = run_in_browser(document, scenario, tmp_path)
    (submitted,) = state["submitted"]
    assert (submitted["brands_1"], submitted["brands_2"], submitted["brands_99"]) == (0, 1, 0)
    assert submitted["brands_other"] == "Initech"


# ── What a submission carries ────────────────────────────────────────────────


def test_a_submission_carries_the_answers_and_the_outcome_only(tmp_path):
    """Not the runtime's own state: __pages__ (the whole questionnaire),
    __options__, __errors__."""

    state = run_in_browser(_trust_matrix_document(), _CLICK_MATRIX + _NEXT + _STATE, tmp_path)
    (submitted,) = state["submitted"]
    assert submitted == {"trust_parl": 2, "trust_pol": 10, "__status": "completed"}


# ── Quotas ───────────────────────────────────────────────────────────────────


def _quota_document(**ui: Any) -> dict[str, Any]:
    document: dict[str, Any] = {
        "schema_version": "1.0",
        "title": "Quotas",
        "variables": {
            "gender": {
                "scale": "nominal",
                "labels": [{"code": 1, "label": "Male"}, {"code": 2, "label": "Female"}],
            },
            "snacks": {
                "scale": "nominal",
                "labels": [{"code": 1, "label": "Chips"}, {"code": 2, "label": "Nuts"}],
            },
            "age": {"scale": "ratio"},
        },
        "pages": [
            {
                "name": "p1",
                "items": [
                    {"type": "SingleChoice", "id": "gender", "var": "gender", "text": "Gender?"}
                ],
            },
            {
                "name": "p2",
                "items": [
                    {"type": "MultiChoice", "id": "snacks", "var": "snacks", "text": "Snacks?"}
                ],
            },
            {
                "name": "p3",
                "items": [{"type": "NumericInput", "id": "age", "var": "age", "text": "Age?"}],
            },
        ],
        "quotas": [
            {"variable": "gender", "target_value": 1, "limit": 100},
            {"variable": "gender", "target_value": 2, "limit": 100},
            {"variable": "snacks", "target_value": 2, "limit": 50},
        ],
    }
    if ui:
        document["ui"] = ui
    return document


_CLOSED = """
    const closed = await page.$(".siamang-closed");
    const text = closed ? await closed.textContent() : null;
"""


def test_a_full_quota_cell_ends_the_interview_before_routing(tmp_path):
    init = 'window.__T = { full: [["gender", 1]] };'
    scenario = (
        """
        await page.click("text=Male");
    """
        + _NEXT
        + _CLOSED
        + _STATE.replace("return {", "return { text,")
    )
    state = run_in_browser(_quota_document(), scenario, tmp_path, init=init)
    assert state["quotaCalls"] == [["gender", 1]]
    assert "Thank you for your interest" in state["text"]
    assert "We have already reached our target sample for participants like you." in state["text"]
    # No completion is submitted, and the next page was never shown.
    assert state["submitted"] == []
    assert state["pages"] == ["p1"]


def test_an_open_cell_is_asked_once_per_value(tmp_path):
    init = 'window.__T = { full: [["gender", 1]] };'
    scenario = (
        """
        await page.click("text=Female");
    """
        + _NEXT
        + """
        await page.click(".sd-navigation__prev-btn");
        await page.waitForTimeout(150);
    """
        + _NEXT
        + """
        await page.click("text=Chips");
    """
        + _NEXT
        + """
        await page.fill("input[type=number]", "40");
        await page.click("body");
    """
        + _NEXT
        + _STATE
    )
    state = run_in_browser(_quota_document(), scenario, tmp_path, init=init)
    # gender=2 is open: asked once, not again on the second pass; snacks is a list.
    assert state["quotaCalls"] == [["gender", 2], ["snacks", [1]]]
    (submitted,) = state["submitted"]
    assert submitted["gender"] == 2 and submitted["snacks"] == [1]


def test_a_multiple_answer_is_full_when_any_chosen_value_is(tmp_path):
    init = 'window.__T = { full: [["snacks", 2]] };'
    scenario = (
        """
        await page.click("text=Female");
    """
        + _NEXT
        + """
        await page.click("text=Chips");
        await page.click("text=Nuts");
    """
        + _NEXT
        + _CLOSED
        + _STATE.replace("return {", "return { text,")
    )
    state = run_in_browser(_quota_document(), scenario, tmp_path, init=init)
    assert ["snacks", [1, 2]] in state["quotaCalls"]
    assert "Thank you for your interest" in state["text"]
    assert state["submitted"] == []


def test_a_failed_quota_check_never_stops_a_respondent(tmp_path):
    init = 'window.__T = { full: [["gender", 1]], quotaThrows: true };'
    scenario = (
        """
        await page.click("text=Male");
    """
        + _NEXT
        + _CLOSED
        + _STATE.replace("return {", "return { text,")
    )
    state = run_in_browser(_quota_document(), scenario, tmp_path, init=init)
    assert state["text"] is None
    assert state["pages"] == ["p1", "p2"]


def test_quota_full_follows_the_panels_redirect(tmp_path):
    document = _quota_document(quota_full_redirect_url="https://panel.example/full?rid={url:pid}")
    init = 'window.__T = { full: [["gender", 1]] };'
    scenario = (
        """
        await page.click("text=Male");
    """
        + _NEXT
        + """
        const link = await page.getAttribute(".siamang-closed a", "href");
        return link;
    """
    )
    link = run_in_browser(document, scenario, tmp_path, init=init)
    assert link == "https://panel.example/full?rid="


# The autosave is written 2 s after the last answer, once the browser is idle.
# Wait well past that — and one idle callback more — then read what is kept
# and whether a reload offers to resume.
_AFTER_THE_AUTOSAVE = (
    _RELOAD
    + """
    await page.waitForTimeout(3000);
    await page.evaluate(() => new Promise((done) =>
        (window.requestIdleCallback || ((cb) => setTimeout(cb, 1)))(() => done())));
    const kept = await page.evaluate(() => localStorage.getItem("siamang_answers_t"));
    await reload("#survey");
    await page.waitForTimeout(250);
    const banner = !!(await page.$(".siamang-resume-banner"));
"""
)


def test_a_full_quota_leaves_no_autosave_behind(tmp_path):
    """The answer is given just before Next, so its autosave is still pending
    when the quota ends the interview: it must not be written afterward."""

    init = 'window.__T = { full: [["gender", 1]] };'
    scenario = (
        """
        await page.click("text=Male");
    """
        + _NEXT
        + _CLOSED
        + _AFTER_THE_AUTOSAVE
        + "return { text, kept, banner };"
    )
    state = run_in_browser(_quota_document(), scenario, tmp_path, init=init)
    assert "Thank you for your interest" in state["text"]
    assert state["kept"] is None
    assert state["banner"] is False


@pytest.mark.parametrize("reply", ["saved", "quota_full"])
def test_a_submitted_interview_leaves_no_autosave_behind(tmp_path, reply):
    """Submitted just after the last answer — saved, or refused by the server
    as a full quota."""

    init = (
        'window.__T = { submitReply: { status: "quota_full" } };' if reply == "quota_full" else ""
    )
    scenario = (
        """
        await page.click("text=Female");
    """
        + _NEXT
        + """
        await page.click("text=Chips");
    """
        + _NEXT
        + """
        await page.fill("input[type=number]", "40");
        await page.click("body");
    """
        + _NEXT
        + """
        const submitted = (await page.evaluate(() => window.__T.submitted)).length;
    """
        + _CLOSED
        + _AFTER_THE_AUTOSAVE
        + "return { submitted, text, kept, banner };"
    )
    state = run_in_browser(_quota_document(), scenario, tmp_path, init=init)
    assert state["submitted"] == 1
    assert (state["text"] is not None) == (reply == "quota_full")
    assert state["kept"] is None
    assert state["banner"] is False


# ── Page bodies ──────────────────────────────────────────────────────────────


def _body_document() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "title": "Bodies",
        "variables": {
            "name": {"scale": "nominal", "dtype": "str"},
            "fruit": {
                "scale": "nominal",
                "labels": [{"code": 1, "label": "Apple"}, {"code": 2, "label": "Pear"}],
            },
        },
        "pages": [
            {
                "name": "p1",
                "title": "About you",
                "body": "<p>Please read <b>carefully</b>.</p>",
                "items": [{"type": "OpenText", "id": "name", "var": "name", "text": "Name?"}],
            },
            {
                "name": "p2",
                "body": "<p>Thanks, {answer:name}.</p>",
                "items": [
                    {"type": "SingleChoice", "id": "fruit", "var": "fruit", "text": "Fruit?"}
                ],
            },
            {
                "name": "done",
                "kind": "final",
                "title": "Thanks {answer:name}",
                "body": "<p>You chose <b>{label:fruit}</b>, {answer:name}.</p>",
            },
        ],
    }


def test_the_body_of_a_page_with_questions_is_shown_above_them_as_html(tmp_path):
    scenario = (
        """
        const body = await page.$eval(".sd-page__body", (el) => el.innerHTML);
        const order = await page.$$eval(".sd-page__body, .sd-question",
            (els) => els.map((el) => el.className.split(" ")[0]));
        await page.fill("input.sd-input", "<i>Ann</i>");
        await page.click("body");
    """
        + _NEXT
        + """
        const piped = await page.$eval(".sd-page__body", (el) => el.innerHTML);
        return { body, order, piped };
    """
    )
    result = run_in_browser(_body_document(), scenario, tmp_path)
    assert result["body"] == "<p>Please read <b>carefully</b>.</p>"
    assert result["order"] == ["sd-page__html", "sd-question"]
    # A piped answer is text, never markup.
    assert result["piped"] == "<p>Thanks, &lt;i&gt;Ann&lt;/i&gt;.</p>"


def test_a_terminal_page_pipes_answers_into_its_title_and_body(tmp_path):
    scenario = (
        """
        await page.fill("input.sd-input", "Ann");
        await page.click("body");
    """
        + _NEXT
        + """
        await page.click("text=Pear");
    """
        + _NEXT
        + """
        const title = await page.textContent(".sd-completedpage__title");
        const body = await page.$eval(".sd-completedpage__body", (el) => el.innerHTML);
        return { title, body };
    """
    )
    result = run_in_browser(_body_document(), scenario, tmp_path)
    assert result["title"] == "Thanks Ann"
    assert result["body"] == "<p>You chose <b>Pear</b>, Ann.</p>"


# ── Sending the answers from an ending page ──────────────────────────────────

# Answer _body_document's two pages; the third is its ending ("final") page,
# which sends the answers as it opens.
_TO_THE_ENDING = (
    """
        await page.fill("input.sd-input", "Ann");
        await page.click("body");
    """
    + _NEXT
    + """
        await page.click("text=Pear");
    """
    + _NEXT
)

# What is on screen: the ending page's title, the "Submitting" overlay, the
# retry dialog's text and the closed screen's.
_ON_SCREEN = """
    const onScreen = async () => page.evaluate(() => {
        const text = (sel) => { const el = document.querySelector(sel); return el ? el.textContent : null; };
        return {
            ending: text(".sd-completedpage__title"),
            sending: !!document.querySelector(".siamang-loading-overlay"),
            retry: text(".siamang-retry-dialog__body"),
            closed: text(".siamang-closed"),
            submitted: window.__T.submitted.length,
        };
    });
"""


def test_an_ending_page_shows_the_answers_being_sent(tmp_path):
    """The ending page used to show at once, alone, while its answers were
    still on their way: a respondent read "your answers were recorded" and
    could close the tab before they were (a captcha that loads at submit
    makes that wait seconds long). The overlay shows over it now, and the
    page's own words come once the answers are stored."""
    scenario = (
        _ON_SCREEN
        + _TO_THE_ENDING
        + """
        const sending = await onScreen();
        await page.evaluate(() => window.__T.release());
        await page.waitForSelector(".siamang-loading-overlay", { state: "detached" });
        const sent = await onScreen();
        return { sending, sent };
    """
    )
    state = run_in_browser(
        _body_document(), scenario, tmp_path, init="window.__T = { holdSubmit: true };"
    )
    assert state["sending"]["ending"] is None
    assert state["sending"]["sending"] is True
    assert state["sent"]["sending"] is False
    assert state["sent"]["retry"] is None
    assert state["sent"]["ending"] == "Thanks Ann"


def test_a_send_that_fails_on_an_ending_page_offers_to_try_again(tmp_path):
    """A failed send from an ending page left the page as if nothing had
    happened, and the answers were never sent: the retry dialog of a page with
    questions now shows over it too."""
    scenario = (
        _ON_SCREEN
        + _TO_THE_ENDING
        + """
        await page.waitForSelector(".siamang-retry-dialog");
        const failed = await onScreen();
        await page.click(".siamang-retry-dialog .sd-navigation__next-btn");
        await page.waitForSelector(".siamang-retry-dialog", { state: "detached" });
        await page.waitForSelector(".sd-completedpage__meta");
        const retried = await onScreen();
        return { failed, retried };
    """
    )
    state = run_in_browser(
        _body_document(), scenario, tmp_path, init="window.__T = { failSubmits: 1 };"
    )
    assert state["failed"]["retry"] == "We could not save your responses. Attempt 1 of 3."
    assert state["failed"]["submitted"] == 1
    assert state["retried"]["submitted"] == 2
    assert state["retried"]["retry"] is None
    assert state["retried"]["ending"] == "Thanks Ann"


def test_answers_that_never_arrive_from_an_ending_page_end_on_the_error_screen(tmp_path):
    """After the last attempt the page no longer thanks the respondent for
    answers that were not recorded; the closed screen says they were not."""
    scenario = (
        _ON_SCREEN
        + _TO_THE_ENDING
        + """
        for (let n = 1; n <= 2; n++) {
            await page.waitForFunction((n) => {
                const body = document.querySelector(".siamang-retry-dialog__body");
                return body && body.textContent.includes(`Attempt ${n} of 3.`);
            }, n);
            await page.click(".siamang-retry-dialog .sd-navigation__next-btn");
        }
        await page.waitForSelector(".siamang-closed");
        return await onScreen();
    """
    )
    state = run_in_browser(
        _body_document(), scenario, tmp_path, init="window.__T = { failSubmits: 3 };"
    )
    assert state["submitted"] == 3
    assert state["ending"] is None
    assert state["retry"] is None
    assert "Submission error" in state["closed"]
    assert "We could not save your responses." in state["closed"]


# "Save locally and finish" in the retry dialog.
_SAVE_LOCALLY = """
    await page.waitForSelector(".siamang-retry-dialog");
    await page.click(".siamang-retry-dialog .sd-navigation__prev-btn");
    await page.waitForSelector(".siamang-retry-dialog", { state: "detached" });
"""

_SAVED_TITLE = "Your answers are saved in this browser"
_SAVED_BODY = (
    "They have not been sent yet. To send them, open this survey's link again in this "
    "browser within 7 days and choose Resume."
)


def test_keeping_the_answers_in_the_browser_ends_on_the_saved_screen(tmp_path):
    """Not on the ending page, which thanks the respondent as if the answers
    had been recorded (and may show a completion code): they were not sent."""
    scenario = (
        _ON_SCREEN
        + _TO_THE_ENDING
        + _SAVE_LOCALLY
        + """
        const finished = await onScreen();
        await page.waitForFunction(() => localStorage.getItem("siamang_answers_t"));
        const kept = await page.evaluate(() => JSON.parse(localStorage.getItem("siamang_answers_t")).answers);
        return { finished, kept };
    """
    )
    state = run_in_browser(
        _body_document(), scenario, tmp_path, init="window.__T = { failSubmits: 1 };"
    )
    assert state["finished"]["ending"] is None
    assert state["finished"]["closed"] == _SAVED_TITLE + _SAVED_BODY
    assert state["finished"]["submitted"] == 1
    assert state["kept"]["name"] == "Ann"


def test_the_retry_dialog_says_what_the_transport_knows_about_the_failure(tmp_path):
    """A transport can say why the answers were not sent and what the
    respondent can do (respondentMessage), in place of the generic text."""
    init = 'window.__T = { failSubmits: 1, failMessage: "  The check could not run. Allow it and try again. " };'
    scenario = (
        _ON_SCREEN
        + _TO_THE_ENDING
        + """
        await page.waitForSelector(".siamang-retry-dialog");
        return await onScreen();
    """
    )
    state = run_in_browser(_body_document(), scenario, tmp_path, init=init)
    assert state["retry"] == "The check could not run. Allow it and try again. Attempt 1 of 3."


# ── Sending the respondent on: only for answers that were stored ─────────────

# A panel's completion address carries its completion code: a respondent sent
# there is counted complete, so they must be sent there only once the survey
# has their answers.
_PANEL_COMPLETE = "https://panel.example/complete?cc=ABC123"


def _panel_document(*, ending: bool, **ui: Any) -> dict[str, Any]:
    """_body_document's two pages, then an ending page that shows the code and
    sends the respondent to the panel 2 s after the answers are stored — or no
    ending page, and the survey's redirect_url (the completion screen's 5 s
    countdown)."""

    document = _body_document()
    if ending:
        document["pages"][-1] = {
            "name": "done",
            "kind": "final",
            "title": "All done",
            "body": "<p>Your code is ABC123</p>",
            "redirect_url": _PANEL_COMPLETE,
            "redirect_delay": 2,
        }
    else:
        document["pages"].pop()
        ui = {"redirect_url": _PANEL_COMPLETE, **ui}
    if ui:
        document["ui"] = ui
    return document


# The panel answers with a page of its own (the harness aborts every other
# address), and every navigation to it is noted in `toPanel`. `onPage()` reads
# where the page is, the saved screen's text, what the survey shows (#root:
# the payload's own script holds the ending page's text), any link to the
# panel, anything that reads as done, and the autosave.
_PANEL = """
    const toPanel = [];
    page.on("request", (request) => {
        if (request.isNavigationRequest() && request.url().startsWith("https://panel.example/")) {
            toPanel.push(request.url());
        }
    });
    await page.route("https://panel.example/**", (route) => route.fulfill({
        status: 200, contentType: "text/html", body: "<p id='panel'>Back on the panel</p>" }));
    const onPage = async () => page.evaluate(() => {
        const root = document.getElementById("root");
        const saved = document.querySelector(".siamang-saved-locally");
        return {
            url: location.href,
            saved: saved ? saved.textContent : null,
            shown: root ? root.innerHTML : "",
            links: Array.from(document.querySelectorAll("a[href]"))
                .map((a) => a.href).filter((href) => href.startsWith("https://panel.example/")),
            done: !!document.querySelector(
                ".sd-completedpage, .sd-completedpage__meta, .siamang-celebration, .sd-completedpage__icon"),
            sending: !!document.querySelector(".siamang-loading-overlay"),
            kept: JSON.parse(localStorage.getItem("siamang_answers_t") || "null"),
        };
    });
"""

_FAIL_ONCE = "window.__T = { failSubmits: 1 };"


def test_saving_locally_never_takes_the_respondent_to_the_completion_address(tmp_path):
    """It ended on the completion screen, which sent the respondent to
    redirect_url 5 s later, carrying the panel's code, for answers the survey
    never got."""
    scenario = (
        _PANEL
        + _TO_THE_ENDING
        + _SAVE_LOCALLY
        + """
        const saved = await onPage();
        // Past the completion screen's 5 s countdown.
        await page.waitForTimeout(6000);
        return { saved, later: await onPage(), toPanel };
    """
    )
    state = run_in_browser(_panel_document(ending=False), scenario, tmp_path, init=_FAIL_ONCE)
    saved, later = state["saved"], state["later"]
    assert saved["saved"] == _SAVED_TITLE + _SAVED_BODY
    assert saved["done"] is False
    for text in ("Response ID", "Submitted", "Thank you for participating", "redirected"):
        assert text not in saved["shown"]
    assert state["toPanel"] == []
    assert later["url"].startswith("file://")
    assert later["saved"] == saved["saved"]
    assert saved["links"] == later["links"] == []
    assert later["kept"]["answers"] == {"name": "Ann", "fruit": 2}


def test_saving_locally_on_an_ending_page_shows_neither_its_code_nor_its_way_on(tmp_path):
    """The ending page stayed, its code on screen, and its redirect ran."""
    scenario = (
        _PANEL
        + _TO_THE_ENDING
        + _SAVE_LOCALLY
        + """
        const saved = await onPage();
        // Past the page's 2 s redirect_delay.
        await page.waitForTimeout(3000);
        return { saved, later: await onPage(), toPanel };
    """
    )
    state = run_in_browser(_panel_document(ending=True), scenario, tmp_path, init=_FAIL_ONCE)
    for seen in (state["saved"], state["later"]):
        assert seen["saved"] == _SAVED_TITLE + _SAVED_BODY
        assert "ABC123" not in seen["shown"] and "All done" not in seen["shown"]
        assert seen["links"] == [] and seen["done"] is False
        assert seen["url"].startswith("file://")
    assert state["toPanel"] == []
    assert state["later"]["kept"]["answers"] == {"name": "Ann", "fruit": 2}


def test_an_ending_pages_way_on_waits_for_the_answers_to_be_stored(tmp_path):
    """Its "Redirecting you now. Continue" link was in the page as the page
    opened, under the "Submitting" overlay: a way to the panel's code before
    the answers had arrived."""
    scenario = (
        _PANEL
        + _TO_THE_ENDING
        + """
        const sending = await onPage();
        await page.evaluate(() => window.__T.release());
        await page.waitForSelector(".sd-completedpage__redirect a");
        const stored = await onPage();
        await page.waitForURL((url) => url.href.startsWith("https://panel.example/"));
        return { sending, stored, toPanel, url: page.url() };
    """
    )
    state = run_in_browser(
        _panel_document(ending=True),
        scenario,
        tmp_path,
        init="window.__T = { holdSubmit: true };",
    )
    assert state["sending"]["sending"] is True
    assert state["sending"]["links"] == []
    assert state["stored"]["sending"] is False
    assert state["stored"]["links"] == [_PANEL_COMPLETE]
    assert state["toPanel"] == [_PANEL_COMPLETE]
    assert state["url"] == _PANEL_COMPLETE


def test_an_ending_pages_words_wait_for_the_answers_to_be_stored(tmp_path):
    """Its title and body were in the page as it opened, under the
    "Submitting" overlay and the retry dialog: a completion code faint through
    them and copyable, a link back to the panel that Tab reached, for answers
    not yet stored and perhaps never to be."""
    document = _body_document()
    document["pages"][-1] = {
        "name": "done",
        "kind": "final",
        "title": "All done",
        "body": f'<p>Your code is ABC123</p><p><a href="{_PANEL_COMPLETE}">Return</a></p>',
    }
    scenario = (
        _TO_THE_ENDING
        + """
        const read = () => page.evaluate(() => ({
            text: document.body.innerText,
            links: Array.from(document.querySelectorAll("[href]"), (el) => el.href)
                .filter((href) => href.includes("panel.example")),
            sending: !!document.querySelector(".siamang-loading-overlay"),
            retry: !!document.querySelector(".siamang-retry-dialog"),
        }));
        await page.waitForFunction(() => typeof window.__T.release === "function");
        const sending = await read();
        // The first send fails; Try again goes through.
        await page.evaluate(() => { window.__T.holdSubmit = false; window.__T.release(); });
        await page.waitForSelector(".siamang-retry-dialog");
        const failed = await read();
        await page.click(".siamang-retry-dialog .sd-navigation__next-btn");
        await page.waitForSelector(".sd-completedpage__title");
        const stored = await read();
        return { sending, failed, stored };
    """
    )
    state = run_in_browser(
        document,
        scenario,
        tmp_path,
        init="window.__T = { failSubmits: 1, holdSubmit: true };",
    )
    for seen in (state["sending"], state["failed"]):
        assert "ABC123" not in seen["text"] and "All done" not in seen["text"], seen["text"]
        assert seen["links"] == []
    assert state["sending"]["sending"] is True
    assert state["failed"]["retry"] is True
    stored = state["stored"]
    assert "All done" in stored["text"] and "Your code is ABC123" in stored["text"]
    assert stored["links"] == [_PANEL_COMPLETE]
    assert stored["sending"] is False and stored["retry"] is False


def test_saving_locally_waits_for_a_try_again_on_its_way(tmp_path):
    """The retry dialog stays up while a Try again is being sent, and Save
    locally and finish does nothing then: that attempt may yet store the
    answers, and the ending page, put back in place of the saved screen once
    it did, would send them a second time."""
    scenario = (
        _PANEL
        + _TO_THE_ENDING
        + """
        await page.waitForFunction(() => typeof window.__T.release === "function");
        // The first send fails.
        await page.evaluate(() => { const go = window.__T.release; window.__T.release = null; go(); });
        await page.waitForSelector(".siamang-retry-dialog");
        // Try again, held on its way; then Save locally and finish.
        await page.click(".siamang-retry-dialog .sd-navigation__next-btn");
        await page.waitForFunction(() => typeof window.__T.release === "function");
        await page.click(".siamang-retry-dialog .sd-navigation__prev-btn");
        await page.waitForTimeout(300);
        const during = await onPage();
        const dialog = await page.evaluate(() => !!document.querySelector(".siamang-retry-dialog"));
        // The Try again is stored.
        await page.evaluate(() => { window.__T.holdSubmit = false; window.__T.release(); });
        await page.waitForSelector(".sd-completedpage__redirect a");
        const sent = await page.evaluate(() => window.__T.submitted.length);
        await page.waitForURL((url) => url.href.startsWith("https://panel.example/"));
        return { during, dialog, sent, toPanel };
    """
    )
    state = run_in_browser(
        _panel_document(ending=True),
        scenario,
        tmp_path,
        init="window.__T = { failSubmits: 1, holdSubmit: true };",
    )
    assert state["during"]["saved"] is None
    assert state["during"]["sending"] is True
    assert state["dialog"] is True
    assert state["sent"] == 2
    assert state["toPanel"] == [_PANEL_COMPLETE]


def test_a_double_click_on_try_again_sends_one_attempt(tmp_path):
    """Try again did not wait for an attempt on its way: a double click sent
    two, the first one's failure let Save locally and finish through while
    the second was still going, and once that one was stored the ending page
    took the saved screen's place, sent the answers a fourth time and went
    to the panel."""
    scenario = (
        _PANEL
        + """
        // The first send fails after 50 ms, the second after 400 ms, and any
        // after them is stored, 2.5 s later.
        await page.evaluate(() => {
            const plan = [[50, false], [400, false]];
            window.SIAMANG_TRANSPORTS.test.submit = async (r) => {
                const [ms, ok] = plan[window.__T.submitted.length] || [2500, true];
                window.__T.submitted.push(JSON.parse(JSON.stringify(r)));
                await new Promise((go) => setTimeout(go, ms));
                if (ok) return { response_id: window.__T.submitted.length };
                const err = new Error("submit failed: 503");
                err.status = 503;
                throw err;
            };
        });
    """
        + _TO_THE_ENDING
        + """
        await page.waitForSelector(".siamang-retry-dialog");
        await page.dblclick(".siamang-retry-dialog .sd-navigation__next-btn");
        await page.waitForFunction(() => {
            const body = document.querySelector(".siamang-retry-dialog__body");
            return body && body.textContent.includes("Attempt 2 of 3.");
        });
        await page.click(".siamang-retry-dialog .sd-navigation__prev-btn");
        // Past where a third attempt would have been stored, then past the
        // page's 2 s redirect_delay after it.
        await page.waitForTimeout(3000);
        const during = await onPage();
        // Read on the survey's page; on the panel's there is nothing to read.
        const sent = await page.evaluate(() => window.__T ? window.__T.submitted.length : null);
        await page.waitForTimeout(2500);
        return { during, sent, later: await onPage(), toPanel };
    """
    )
    state = run_in_browser(_panel_document(ending=True), scenario, tmp_path)
    assert state["during"]["saved"] == _SAVED_TITLE + _SAVED_BODY
    assert state["sent"] == 2
    assert state["toPanel"] == []
    assert state["later"]["url"].startswith("file://")
    assert state["later"]["saved"] == _SAVED_TITLE + _SAVED_BODY


def test_answers_saved_locally_are_sent_from_the_next_visit_and_then_redirect(tmp_path):
    """The autosave stays: the link opened again in the same browser offers
    Resume, which sends the answers, and only then is the respondent sent
    to the panel."""
    # The first visit's sending fails once; the next one, opened with ?send,
    # goes through. Told by the address, not by localStorage: an init script
    # that reads localStorage as a file:// page loads again can leave that page
    # with an empty one in Chromium, and no resume to offer.
    init = 'window.__T = { failSubmits: location.search.includes("send") ? 0 : 1 };'
    scenario = (
        _PANEL
        + _RELOAD
        + _TO_THE_ENDING
        + _SAVE_LOCALLY
        + """
        // The respondent reads the screen, past the page's 2 s redirect_delay,
        // and comes back later.
        await page.waitForTimeout(3000);
        const left = toPanel.slice();
        if (left.length) return { left };
        await page.waitForFunction(() => localStorage.getItem("siamang_answers_t"));
        await visit("?send=1", ".siamang-resume-banner");
        const offered = await onPage();
        await page.click(".siamang-resume-banner .sd-navigation__next-btn");
        await page.waitForSelector(".sd-completedpage__redirect a");
        const submitted = await page.evaluate(() => window.__T.submitted);
        await page.waitForURL((url) => url.href.startsWith("https://panel.example/"));
        return { left, offered, submitted, toPanel, url: page.url() };
    """
    )
    state = run_in_browser(_panel_document(ending=True), scenario, tmp_path, init=init)
    assert state["left"] == []
    assert state["offered"]["saved"] is None and state["offered"]["links"] == []
    assert state["submitted"] == [{"name": "Ann", "fruit": 2, "__status": "completed"}]
    assert state["toPanel"] == [_PANEL_COMPLETE]
    assert state["url"] == _PANEL_COMPLETE


def test_the_saved_screen_speaks_the_surveys_wording(tmp_path):
    ui = {
        "saved_locally_title": "Im Browser gespeichert",
        "saved_locally_body": "Noch nicht gesendet.",
    }
    scenario = _PANEL + _TO_THE_ENDING + _SAVE_LOCALLY + "return await onPage();"
    state = run_in_browser(_panel_document(ending=True, **ui), scenario, tmp_path, init=_FAIL_ONCE)
    assert state["saved"] == "Im Browser gespeichertNoch nicht gesendet."


# ── A page whose transport is not there ──────────────────────────────────────


class _RequiringClient(_RecordingClient):
    """The recording transport, from a template that names it: the pages it
    builds need it to send their answers (``SURVEY.transport``)."""

    transport = "test"


_UNREACHABLE = (
    "We could not reach the server, so your answers could not be sent. "
    "Check your connection and try again."
)

# env.js that ran and registered no transport (a host's script that failed
# halfway).
_ENV_WITHOUT_TRANSPORT = 'window.SIAMANG_ENV = { transport: "test", survey_id: "t" };\n'

# _PANEL's record of every way to the panel, for a page without its env.js
# (nothing records a submission there). `settled()` waits for the retry
# dialog, or for what ends the survey in its place: an ending page's title,
# the completion screen, the closed or the saved screen. `attempt(n)` waits
# for the dialog's "Attempt n of 3.". `kept` is the autosave's answers.
_UNSENT = """
    page.setDefaultTimeout(10000);
    const toPanel = [];
    page.on("request", (request) => {
        if (request.isNavigationRequest() && request.url().startsWith("https://panel.example/")) {
            toPanel.push(request.url());
        }
    });
    await page.route("https://panel.example/**", (route) => route.fulfill({
        status: 200, contentType: "text/html", body: "<p id='panel'>Back on the panel</p>" }));
    const settled = () => page.waitForSelector(
        ".siamang-retry-dialog, .sd-completedpage__title, .siamang-closed");
    const attempt = (n) => page.waitForFunction((n) => {
        const body = document.querySelector(".siamang-retry-dialog__body");
        return body && body.textContent.includes(`Attempt ${n} of 3.`);
    }, n);
    const onPage = async () => page.evaluate(() => {
        const text = (sel) => { const el = document.querySelector(sel); return el ? el.textContent : null; };
        const root = document.getElementById("root");
        const key = Object.keys(localStorage).find((k) => k.startsWith("siamang_answers_"));
        return {
            url: location.href,
            retry: text(".siamang-retry-dialog__body"),
            saved: text(".siamang-saved-locally"),
            closed: text(".siamang-closed"),
            shown: root ? root.innerHTML : "",
            links: Array.from(document.querySelectorAll("[href]"), (el) => el.href)
                .filter((href) => href.startsWith("https://panel.example/")),
            done: !!document.querySelector(".sd-completedpage__title, .sd-completedpage__meta, "
                + ".siamang-celebration, .sd-completedpage__icon"),
            kept: key ? JSON.parse(localStorage.getItem(key)).answers : null,
        };
    });
"""


def _neither_done_nor_on_the_way(seen: dict[str, Any]) -> None:
    """Nothing reads as done, nothing leads to the panel, and the page is
    where it was: the completion screen's words, an ending page's ("All
    done", its code ABC123) and its links are not in the page."""
    assert seen["done"] is False and seen["links"] == []
    for text in ("All done", "ABC123", "Thank you for participating", "Response ID", "redirected"):
        assert text not in seen["shown"]
    assert seen["url"].startswith("file://")


@pytest.mark.parametrize("ending", [False, True], ids=["completion-screen", "ending-page"])
def test_a_page_without_the_transport_it_needs_never_ends_as_sent(tmp_path, ending):
    """Its env.js did not load. The page ended as if the answers had been
    sent: on the completion screen, and 5 s later at its redirect_url, or on
    the ending page, with its code, and 2 s later at its redirect_url — the
    panel's completion address, which counts the respondent complete — with
    nothing stored anywhere. Each attempt now fails as a send does: the retry
    dialog says why, and the third ends on the error screen."""
    scenario = (
        _UNSENT
        + _TO_THE_ENDING
        + """
        await settled();
        const first = await onPage();
        await page.click(".siamang-retry-dialog .sd-navigation__next-btn");
        await attempt(2);
        const second = await onPage();
        await page.click(".siamang-retry-dialog .sd-navigation__next-btn");
        await page.waitForSelector(".siamang-closed");
        const closed = await onPage();
        // Past the completion screen's 5 s countdown and the page's 2 s delay.
        await page.waitForTimeout(6000);
        return { first, second, closed, later: await onPage(), toPanel };
    """
    )
    state = run_in_browser(
        _panel_document(ending=ending),
        scenario,
        tmp_path,
        client=_RequiringClient(),
        env_js=False,
    )
    assert state["first"]["retry"] == _UNREACHABLE + " Attempt 1 of 3."
    assert state["second"]["retry"] == _UNREACHABLE + " Attempt 2 of 3."
    for seen in (state["closed"], state["later"]):
        assert seen["retry"] is None
        assert "Submission error" in seen["closed"]
        assert "We could not save your responses. Please refresh and try again." in seen["closed"]
    for seen in (state["first"], state["second"], state["closed"], state["later"]):
        _neither_done_nor_on_the_way(seen)
    assert state["toPanel"] == []


@pytest.mark.parametrize(
    "env_js", [False, _ENV_WITHOUT_TRANSPORT], ids=["env-not-loaded", "no-transport-registered"]
)
def test_saving_locally_without_the_transport_ends_on_the_saved_screen(tmp_path, env_js):
    """Save locally and finish, on an ending page whose send found no
    transport: the saved screen, never the ending page's code or its way on."""
    scenario = (
        _UNSENT
        + _TO_THE_ENDING
        + """
        await settled();
        const failed = await onPage();
        await page.click(".siamang-retry-dialog .sd-navigation__prev-btn");
        await page.waitForSelector(".siamang-saved-locally");
        const saved = await onPage();
        // Past the page's 2 s redirect_delay.
        await page.waitForTimeout(3000);
        return { failed, saved, later: await onPage(), toPanel };
    """
    )
    state = run_in_browser(
        _panel_document(ending=True),
        scenario,
        tmp_path,
        client=_RequiringClient(),
        env_js=env_js,
    )
    assert state["failed"]["retry"] == _UNREACHABLE + " Attempt 1 of 3."
    for seen in (state["saved"], state["later"]):
        assert seen["saved"] == _SAVED_TITLE + _SAVED_BODY
        assert seen["retry"] is None
    for seen in (state["failed"], state["saved"], state["later"]):
        _neither_done_nor_on_the_way(seen)
    assert state["toPanel"] == []
    assert state["later"]["kept"] == {"name": "Ann", "fruit": 2}


def test_without_its_transport_the_retry_dialog_speaks_the_surveys_failure_text(tmp_path):
    """The runtime's own explanation is English: a survey that words its
    failure text (retry_body), perhaps in another language, says that."""
    document = _panel_document(
        ending=True,
        retry_body="Wir konnten Ihre Antworten nicht speichern.",
        attempt_text="Versuch {n} von {max}.",
    )
    scenario = _UNSENT + _TO_THE_ENDING + "await settled(); return await onPage();"
    state = run_in_browser(document, scenario, tmp_path, client=_RequiringClient(), env_js=False)
    assert state["retry"] == "Wir konnten Ihre Antworten nicht speichern. Versuch 1 von 3."
    _neither_done_nor_on_the_way(state)


def test_an_attempt_made_once_the_transport_is_there_sends_through_it(tmp_path):
    """Each attempt looks for the transport again: one a host registers
    meanwhile takes the answers, and only then does the ending page show
    and send the respondent on."""
    scenario = (
        _UNSENT
        + _TO_THE_ENDING
        + """
        await settled();
        const failed = await onPage();
        await page.evaluate(() => {
            window.__sent = [];
            window.SIAMANG_ENV = { transport: "test", survey_id: "t" };
            window.SIAMANG_TRANSPORTS = { test: { async submit(r) {
                window.__sent.push(JSON.parse(JSON.stringify(r)));
                return { response_id: 3 };
            } } };
        });
        await page.click(".siamang-retry-dialog .sd-navigation__next-btn");
        await page.waitForSelector(".sd-completedpage__redirect a");
        const stored = await onPage();
        const sent = await page.evaluate(() => window.__sent);
        await page.waitForURL((url) => url.href.startsWith("https://panel.example/"));
        return { failed, stored, sent, toPanel, url: page.url() };
    """
    )
    state = run_in_browser(
        _panel_document(ending=True),
        scenario,
        tmp_path,
        client=_RequiringClient(),
        env_js=False,
    )
    assert state["failed"]["retry"] == _UNREACHABLE + " Attempt 1 of 3."
    _neither_done_nor_on_the_way(state["failed"])
    assert state["sent"] == [{"name": "Ann", "fruit": 2, "__status": "completed"}]
    assert "All done" in state["stored"]["shown"] and state["stored"]["retry"] is None
    assert state["stored"]["links"] == [_PANEL_COMPLETE]
    assert state["toPanel"] == [_PANEL_COMPLETE]
    assert state["url"] == _PANEL_COMPLETE


@pytest.mark.parametrize("ending", [False, True], ids=["completion-screen", "ending-page"])
def test_a_page_that_needs_no_transport_ends_without_one_as_before(tmp_path, ending):
    """A control, which the previous bundle passes too: a page built with no
    transport to require (a preview, a page its host gives no backend) ends
    without one as if the answers had been sent, and sends the respondent
    on."""
    scenario = (
        _UNSENT
        + _TO_THE_ENDING
        + """
        await settled();
        const ended = await onPage();
        await page.waitForURL((url) => url.href.startsWith("https://panel.example/"));
        return { ended, toPanel };
    """
    )
    state = run_in_browser(_panel_document(ending=ending), scenario, tmp_path, env_js=False)
    assert state["ended"]["retry"] is None and state["ended"]["done"] is True
    assert state["toPanel"] == [_PANEL_COMPLETE]


def test_a_page_that_needs_its_transport_sends_through_it_as_before(tmp_path):
    """A control, which the previous bundle passes too: with its env.js
    there, a page that requires the transport sends through it and goes on
    once the answers are stored."""
    scenario = (
        _PANEL
        + _TO_THE_ENDING
        + """
        await page.waitForSelector(".sd-completedpage__redirect a");
        const submitted = await page.evaluate(() => window.__T.submitted);
        await page.waitForURL((url) => url.href.startsWith("https://panel.example/"));
        return { submitted, toPanel };
    """
    )
    state = run_in_browser(
        _panel_document(ending=True), scenario, tmp_path, client=_RequiringClient()
    )
    assert state["submitted"] == [{"name": "Ann", "fruit": 2, "__status": "completed"}]
    assert state["toPanel"] == [_PANEL_COMPLETE]


# env.js that does not load on the first visit (it runs nothing: no
# SIAMANG_ENV, no transport) and loads on a visit opened with ?send.
_ENV_ON_THE_NEXT_VISIT = 'if (location.search.includes("send")) {\n' + _TRANSPORT + "}\n"


def test_answers_kept_without_env_js_are_offered_back_once_it_loads(tmp_path):
    """With the survey's id in env.js alone, a page whose env.js did not load
    would keep Save locally and finish's answers, and the interview's id,
    under the runtime's last resort, siamang_survey, a key every such survey
    of a host shares, while the next visit, its env.js loaded, reads
    siamang_answers_t: no Resume, and the answers could never be sent. The
    page carries its id along with the transport it needs."""
    scenario = (
        _PANEL
        + _RELOAD
        + _TO_THE_ENDING
        + _SAVE_LOCALLY
        + """
        await page.waitForSelector(".siamang-saved-locally");
        await page.waitForFunction(
            () => Object.keys(localStorage).some((k) => k.startsWith("siamang_answers_")));
        const keys = await page.evaluate(() => Object.keys(localStorage).sort());
        await visit("?send=1");
        const offered = !!(await page.waitForSelector(
            ".siamang-resume-banner", { timeout: 5000 }).catch(() => null));
        if (!offered) return { keys, offered };
        await page.click(".siamang-resume-banner .sd-navigation__next-btn");
        await page.waitForSelector(".sd-completedpage__redirect a");
        const submitted = await page.evaluate(() => window.__T.submitted);
        await page.waitForURL((url) => url.href.startsWith("https://panel.example/"));
        return { keys, offered, submitted, toPanel, url: page.url() };
    """
    )
    state = run_in_browser(
        _panel_document(ending=True),
        scenario,
        tmp_path,
        client=_RequiringClient(),
        env_js=_ENV_ON_THE_NEXT_VISIT,
    )
    # The test transport's survey_id is "t", as the page's own.
    assert "siamang_answers_t" in state["keys"] and "siamang_interview_t" in state["keys"]
    assert not any(key.endswith("siamang_survey") for key in state["keys"])
    assert state["offered"] is True
    assert state["submitted"] == [{"name": "Ann", "fruit": 2, "__status": "completed"}]
    assert state["toPanel"] == [_PANEL_COMPLETE]
    assert state["url"] == _PANEL_COMPLETE


def _rating_document() -> dict[str, Any]:
    """_body_document's first page, then a page whose one question is a 1-5
    rating scale, sent from there (no ending page)."""

    document = _body_document()
    del document["variables"]["fruit"]
    document["variables"]["sat"] = {"scale": "ordinal", "labels": _labels([1, 2, 3, 4, 5])}
    document["pages"][1:] = [
        {
            "name": "p2",
            "items": [
                {
                    "type": "LikertScale",
                    "id": "sat",
                    "var": "sat",
                    "text": "How satisfied are you?",
                    "points": 5,
                }
            ],
        }
    ]
    return document


# Answer _rating_document's two pages (3 on the scale) and send them.
_TO_THE_RATING = (
    """
        await page.fill("input.sd-input", "Ann");
        await page.click("body");
    """
    + _NEXT
    + """
        await page.click(".sd-rating__item >> nth=2");
    """
    + _NEXT
)


@pytest.mark.parametrize(
    ("document", "to_the_end"),
    [(_rating_document, _TO_THE_RATING), (_body_document, _TO_THE_ENDING)],
    ids=["a-rating-scale", "an-ending-page"],
)
def test_keys_do_nothing_on_the_saved_screen(tmp_path, document, to_the_end):
    """The page the saved screen took the place of still heard the keyboard:
    a digit answered its rating scale, and 2 s later the kept answers that
    Resume sends held that point; Escape went back a page, ran the pages'
    scripts and told the transport of a page no one saw."""
    scenario = (
        to_the_end
        + _SAVE_LOCALLY
        + """
        await page.waitForFunction(() => localStorage.getItem("siamang_answers_t"));
        const read = () => page.evaluate(() => {
            const kept = JSON.parse(localStorage.getItem("siamang_answers_t"));
            return {
                answers: kept.answers,
                pageIdx: kept.pageIdx,
                pages: window.__T.pages.slice(),
                saved: !!document.querySelector(".siamang-saved-locally"),
            };
        });
        const before = await read();
        await page.keyboard.press("5");
        await page.keyboard.press("Escape");
        // Past the 2 s a save waits after an answer.
        await page.waitForTimeout(3000);
        return { before, after: await read() };
    """
    )
    state = run_in_browser(document(), scenario, tmp_path, init=_FAIL_ONCE)
    assert state["before"]["saved"] is True
    assert state["before"]["pages"][-1] == ("p2" if document is _rating_document else "done")
    assert state["after"] == state["before"]


# ── An ending page stays where the interview ended ───────────────────────────

_COMPLETED = "https://panel.example/complete?cc=COMPLETE"
_SCREENED_OUT = "https://panel.example/complete?cc=SCREENOUT"


def _screen_out_document() -> dict[str, Any]:
    """_body_document's two pages, then a screen-out page without an address
    of its own: 2 s after the answers are stored it sends the respondent to
    the survey's screen_out_redirect_url, never to its redirect_url, the
    panel's completion code."""

    document = _body_document()
    document["pages"][-1] = {
        "name": "out",
        "kind": "disqualification",
        "title": "Not this time",
        "body": "<p>This study is looking for other participants.</p>",
        "redirect_delay": 2,
    }
    document["ui"] = {"redirect_url": _COMPLETED, "screen_out_redirect_url": _SCREENED_OUT}
    return document


# The pages the transport was told of, whether a page with questions is on
# screen, the statuses of the answers sent, and the links to the panel.
_AT_THE_END = """
    const atTheEnd = () => page.evaluate(() => ({
        pages: window.__T.pages.slice(),
        question: !!document.querySelector(".sd-page"),
        statuses: window.__T.submitted.map((answers) => answers.__status),
        links: Array.from(document.querySelectorAll("a[href]"), (a) => a.href)
            .filter((href) => href.startsWith("https://panel.example/")),
    }));
"""

# Escape on the screen-out page: while its answers are on their way, once
# they are stored (within the page's redirect_delay), and under the retry
# dialog after a failed send, then Try again.
_ESCAPE_ON_THE_SCREEN_OUT = {
    "sending": (
        "window.__T = { holdSubmit: true };",
        """
        await page.waitForFunction(() => typeof window.__T.release === "function");
        await page.keyboard.press("Escape");
        await page.waitForTimeout(300);
        const pressed = await atTheEnd();
        await page.evaluate(() => window.__T.release());
    """,
    ),
    "stored": (
        "",
        """
        await page.waitForSelector(".sd-completedpage__redirect a");
        await page.keyboard.press("Escape");
        await page.waitForTimeout(300);
        const pressed = await atTheEnd();
    """,
    ),
    "retrying": (
        _FAIL_ONCE,
        """
        await page.waitForSelector(".siamang-retry-dialog");
        await page.keyboard.press("Escape");
        await page.waitForTimeout(300);
        const pressed = await atTheEnd();
        await page.click(".siamang-retry-dialog .sd-navigation__next-btn");
    """,
    ),
}


@pytest.mark.parametrize("when", list(_ESCAPE_ON_THE_SCREEN_OUT))
def test_escape_on_a_screen_out_page_leaves_neither_it_nor_its_way_on(tmp_path, when):
    """Escape went back from an ending page: the page before it took its
    place, and once the answers were stored the completion screen took that
    one's and sent a screened-out participant to redirect_url, the panel's
    completion code, in place of screen_out_redirect_url."""
    init, press = _ESCAPE_ON_THE_SCREEN_OUT[when]
    scenario = (
        _PANEL
        + _AT_THE_END
        + _TO_THE_ENDING
        + press
        + """
        await page.waitForSelector(".sd-completedpage__redirect a");
        const stored = await atTheEnd();
        await page.waitForURL((url) => url.href.startsWith("https://panel.example/"));
        return { pressed, stored, toPanel, url: page.url() };
    """
    )
    state = run_in_browser(_screen_out_document(), scenario, tmp_path, init=init)
    for seen in (state["pressed"], state["stored"]):
        assert seen["pages"] == ["p1", "p2", "out"]
        assert seen["question"] is False
    tries = 2 if when == "retrying" else 1
    assert state["stored"]["statuses"] == ["screened_out"] * tries
    assert state["stored"]["links"] == [_SCREENED_OUT]
    assert state["toPanel"] == [_SCREENED_OUT]
    assert state["url"] == _SCREENED_OUT


def test_escape_on_a_final_page_keeps_its_own_way_on(tmp_path):
    """A final page's own redirect_url (an arm's code, say) gave way to the
    survey's redirect_url after Escape, the completion screen in its place.
    On a page with questions Escape still goes back, keeping the answers."""
    scenario = (
        _PANEL
        + _AT_THE_END
        + """
        await page.fill("input.sd-input", "Ann");
        await page.click("body");
    """
        + _NEXT
        + """
        await page.keyboard.press("Escape");
        await page.waitForFunction(() => window.__T.pages.length === 3);
        const back = await page.evaluate(() => ({
            pages: window.__T.pages.slice(),
            name: document.querySelector("input.sd-input").value,
        }));
    """
        + _NEXT
        + """
        await page.click("text=Pear");
    """
        + _NEXT
        + """
        await page.waitForSelector(".sd-completedpage__redirect a");
        await page.keyboard.press("Escape");
        await page.waitForTimeout(300);
        const pressed = await atTheEnd();
        await page.waitForURL((url) => url.href.startsWith("https://panel.example/"));
        return { back, pressed, toPanel, url: page.url() };
    """
    )
    document = _panel_document(ending=True, redirect_url=_COMPLETED)
    state = run_in_browser(document, scenario, tmp_path)
    assert state["back"] == {"pages": ["p1", "p2", "p1"], "name": "Ann"}
    pressed = state["pressed"]
    assert pressed["pages"] == ["p1", "p2", "p1", "p2", "done"]
    assert pressed["question"] is False
    assert pressed["statuses"] == ["completed"]
    assert pressed["links"] == [_PANEL_COMPLETE]
    assert state["toPanel"] == [_PANEL_COMPLETE]
    assert state["url"] == _PANEL_COMPLETE


# ── Resume: the page it was saved on, never under a page being left ──────────

_RESUMED_VARIABLES: dict[str, dict[str, Any]] = {
    "heard": {"scale": "nominal", "dtype": "str"},
    "gender": {
        "scale": "nominal",
        "labels": [{"code": 1, "label": "Male"}, {"code": 2, "label": "Female"}],
    },
    "fruit": {
        "scale": "nominal",
        "labels": [{"code": 1, "label": "Apple"}, {"code": 2, "label": "Pear"}],
    },
    "extra": {"scale": "nominal", "dtype": "str"},
}


def _resumed_document(*names: str, quota: bool = False) -> dict[str, Any]:
    """Of p0 (a question put in at the start), p1 (gender), p2 (fruit: a Pear
    is screened out), p3 (a question put in before the endings), the final
    page `done` and the screen-out page `out`, the pages ``names``, in that
    order; ``p3-for-a-pear`` is p3 shown to a Pear alone. Each ending sends
    the respondent on 2 s after the answers are stored: `done` to the
    survey's redirect_url (cc=COMPLETE), `out` to its screen_out_redirect_url
    (cc=SCREENOUT). With ``quota``, gender is a quota variable."""

    pages: dict[str, dict[str, Any]] = {
        "p0": {"name": "p0", "items": [_text("heard", "Where did you hear of us?")]},
        "p1": {"name": "p1", "items": [_choice("gender", "Gender?")]},
        "p2": {
            "name": "p2",
            "items": [_choice("fruit", "Fruit?")],
            "next_if": [{"condition": _cmp("=", _var("fruit"), 2), "target": "out"}],
        },
        "p3": {"name": "p3", "items": [_text("extra", "Anything else?")]},
        "p3-for-a-pear": {
            "name": "p3",
            "items": [_text("extra", "Anything else?")],
            "show_if": _cmp("=", _var("fruit"), 2),
        },
        "done": {"name": "done", "kind": "final", "title": "All done", "redirect_delay": 2},
        "out": {
            "name": "out",
            "kind": "disqualification",
            "title": "Not this time",
            "redirect_delay": 2,
        },
    }
    chosen = [pages[name] for name in names]
    used = {item["var"] for page in chosen for item in page.get("items", [])}
    document: dict[str, Any] = {
        "schema_version": "1.0",
        "title": "Resumed",
        "variables": {name: spec for name, spec in _RESUMED_VARIABLES.items() if name in used},
        "pages": chosen,
        "ui": {"redirect_url": _COMPLETED, "screen_out_redirect_url": _SCREENED_OUT},
    }
    if quota:
        document["quotas"] = [
            {"variable": "gender", "target_value": 1, "limit": 100},
            {"variable": "gender", "target_value": 2, "limit": 100},
        ]
    return document


def _saved_on(
    pages: list[str],
    on: str,
    answers: dict[str, Any],
    history: list[str],
    *,
    named: bool = True,
    unseen: tuple[str, ...] = (),
) -> str:
    """An init script that leaves, written just now, the autosave a sitting
    of a version whose pages were ``pages`` wrote on page ``on``; without
    ``named``, as a version that kept no pageName wrote it. The page index
    counts the pages on screen: not ``unseen``, pages the version did not
    show this respondent, which its page order has all the same."""

    shown = [name for name in pages if name not in unseen]
    save: dict[str, Any] = {
        "answers": answers,
        "pageIdx": shown.index(on),
        "history": history,
        "pageOrder": pages,
    }
    if named:
        save["pageName"] = on
    return (
        "localStorage.setItem('siamang_answers_t', JSON.stringify(Object.assign("
        + json.dumps(save)
        + ", { savedAt: new Date().toISOString(), startedAt: Date.now() })));"
    )


# The pages the transport was told of, the statuses of the answers sent,
# whether a page with questions is on screen and its chosen answers.
_RESUMED = """
    const read = () => page.evaluate(() => ({
        pages: window.__T.pages.slice(),
        statuses: window.__T.submitted.map((answers) => answers.__status),
        question: !!document.querySelector(".sd-page"),
        checked: Array.from(document.querySelectorAll(".sd-item--checked .sd-choice-label"),
            (el) => el.textContent),
    }));
"""


def test_resume_waits_for_the_quota_check_of_the_page_being_left(tmp_path):
    """Resume, clicked while a Next waited on a quota check, opened the saved
    screen-out page, which sent the answers as screened out. The check's
    answer then took the respondent off it to the page after the one Next
    was pressed on, and once the answers were stored the completion screen
    sent a screened-out participant to redirect_url (cc=COMPLETE). Resume is
    disabled while a check runs, and the answer moves only the page it was
    asked from."""
    init = _saved_on(["p1", "p2", "done", "out"], "out", {"gender": 1, "fruit": 2}, ["p1", "p2"])
    scenario = (
        _PANEL
        + _RESUMED
        + """
        await page.waitForSelector(".siamang-resume-banner");
        // The quota check waits until the test lets it answer.
        await page.evaluate(() => {
            window.SIAMANG_TRANSPORTS.test.checkQuota = () => new Promise((answer) => {
                window.__T.answerQuota = () => answer({ ok: true });
            });
        });
        await page.click("text=Female");
        await page.click(".sd-navigation .sd-navigation__next-btn");
        await page.waitForFunction(() => typeof window.__T.answerQuota === "function");
        // Resume while it waits, wherever the banner is.
        const offered = await page.evaluate(() => {
            const resume = document.querySelector(".siamang-resume-banner .sd-navigation__next-btn");
            if (resume) resume.click();
            return resume ? (resume.disabled ? "disabled" : "enabled") : "gone";
        });
        await page.waitForTimeout(300);
        const checking = await read();
        await page.evaluate(() => window.__T.answerQuota());
        await page.waitForTimeout(300);
        const answered = await read();
        if (!(await page.$(".siamang-resume-banner"))) {
            // Past the completion screen's 5 s countdown, should it be up.
            await page.waitForTimeout(6000);
            return { offered, checking, answered, toPanel };
        }
        await page.click(".siamang-resume-banner .sd-navigation__next-btn");
        await page.waitForSelector(".sd-completedpage__redirect a");
        const resumed = await read();
        await page.waitForURL((url) => url.href.startsWith("https://panel.example/"));
        return { offered, checking, answered, resumed, toPanel, url: page.url() };
    """
    )
    document = _resumed_document("p1", "p2", "done", "out", quota=True)
    state = run_in_browser(document, scenario, tmp_path, init=init)
    # Nothing sent and no page changed while the check ran; its answer took
    # the respondent on from p1, the page Next was pressed on.
    checking, answered = state["checking"], state["answered"]
    assert checking == {"pages": ["p1"], "statuses": [], "question": True, "checked": ["Female"]}
    assert answered == {"pages": ["p1", "p2"], "statuses": [], "question": True, "checked": []}
    assert state["offered"] == "disabled"
    # Resumed from there, the saved screen-out page sends the answers as
    # screened out, and the one way on is screen_out_redirect_url.
    assert state["resumed"]["pages"] == ["p1", "p2", "out"]
    assert state["resumed"]["statuses"] == ["screened_out"]
    assert state["toPanel"] == [_SCREENED_OUT]
    assert state["url"] == _SCREENED_OUT


def test_the_resume_banner_stays_through_a_quota_check(tmp_path):
    """While a Next waits on a quota check, Resume and Start over are
    disabled, and the banner stays, the same element: taken out for the
    check, its alert would go in anew, and be read out again, on every Next
    of a survey with quotas, the check answered at once or not, and the page
    would move up while a check was held."""
    init = _saved_on(["p0", "p1", "p2", "p3"], "p2", {"heard": "web", "gender": 1}, ["p0", "p1"])
    scenario = """
        await page.waitForSelector(".siamang-resume-banner");
        await page.evaluate(() => {
            window.__banner = document.querySelector(".siamang-resume-banner");
            window.__taken = 0;
            new MutationObserver((records) => {
                for (const record of records) {
                    for (const node of record.removedNodes) if (node === window.__banner) window.__taken++;
                }
            }).observe(document.getElementById("survey"), { childList: true, subtree: true });
        });
        const banner = () => page.evaluate(() => {
            const now = document.querySelector(".siamang-resume-banner");
            return {
                taken: window.__taken,
                same: now === window.__banner,
                disabled: now ? Array.from(now.querySelectorAll("button"), (b) => b.disabled) : null,
            };
        });
        const nextTop = () => page.evaluate(() => Math.round(document.querySelector(
            ".sd-navigation .sd-navigation__next-btn").getBoundingClientRect().top));
        // p0 has no quota variable: its check answers at once.
        await page.fill("input.sd-input", "web");
        await page.click("body");
        await page.click(".sd-navigation .sd-navigation__next-btn");
        await page.waitForSelector("text=Female");
        const atOnce = await banner();
        // p1's gender is checked, and the check waits until the test lets it
        // answer.
        await page.evaluate(() => {
            window.SIAMANG_TRANSPORTS.test.checkQuota = () => new Promise((answer) => {
                window.__T.answerQuota = () => answer({ ok: true });
            });
        });
        await page.click("text=Female");
        const before = await nextTop();
        await page.click(".sd-navigation .sd-navigation__next-btn");
        await page.waitForFunction(() => typeof window.__T.answerQuota === "function");
        await page.waitForTimeout(200);
        const during = { banner: await banner(), top: await nextTop() };
        await page.evaluate(() => window.__T.answerQuota());
        await page.waitForSelector("text=Apple");
        const after = await banner();
        return { atOnce, before, during, after };
    """
    document = _resumed_document("p0", "p1", "p2", "p3", quota=True)
    state = run_in_browser(document, scenario, tmp_path, init=init)
    assert state["atOnce"] == {"taken": 0, "same": True, "disabled": [False, False]}
    assert state["during"]["banner"] == {"taken": 0, "same": True, "disabled": [True, True]}
    assert state["during"]["top"] == state["before"]
    assert state["after"] == {"taken": 0, "same": True, "disabled": [False, False]}


def test_the_resume_banner_is_out_of_reach_while_the_answers_are_sent(tmp_path):
    """The banner stayed in the page under the "Submitting" overlay, and Tab
    reached its Resume: Enter put the saved screen-out page in place of the
    page being sent, which sent the old answers a second time, as screened
    out, and the participant went to screen_out_redirect_url whatever the
    first send stored."""
    # A Pear is screened out on `out`, shown for it alone; p2, the last page,
    # sends the answers, and the completion screen sends the respondent to
    # redirect_url.
    document = {
        "schema_version": "1.0",
        "title": "Resumed",
        "variables": {"fruit": _RESUMED_VARIABLES["fruit"], "extra": _RESUMED_VARIABLES["extra"]},
        "pages": [
            {"name": "p1", "items": [_choice("fruit", "Fruit?")]},
            {
                "name": "out",
                "kind": "disqualification",
                "title": "Not this time",
                "redirect_delay": 2,
                "show_if": _cmp("=", _var("fruit"), 2),
            },
            {"name": "p2", "items": [_text("extra", "Anything else?")]},
        ],
        "ui": {"redirect_url": _COMPLETED, "screen_out_redirect_url": _SCREENED_OUT},
    }
    init = "window.__T = { holdSubmit: true };" + _saved_on(
        ["p1", "out", "p2"], "out", {"fruit": 2}, ["p1"]
    )
    scenario = (
        _PANEL
        + """
        await page.waitForSelector(".siamang-resume-banner");
        await page.click("text=Apple");
        await page.click(".sd-navigation .sd-navigation__next-btn");
        await page.waitForSelector("input.sd-input");
        await page.fill("input.sd-input", "Ann");
        await page.click("body");
        await page.click(".sd-navigation .sd-navigation__complete-btn");
        await page.waitForFunction(() => typeof window.__T.release === "function");
        const banner = !!(await page.$(".siamang-resume-banner"));
        let reached = false;
        for (let tab = 0; tab < 30 && !reached; tab++) {
            await page.keyboard.press("Tab");
            reached = await page.evaluate(() =>
                !!(document.activeElement && document.activeElement.closest(".siamang-resume-banner")));
        }
        if (reached) await page.keyboard.press("Enter");
        await page.waitForTimeout(300);
        const sent = await page.evaluate(() => window.__T.submitted.map((answers) =>
            [answers.__status || null, answers.fruit, answers.extra || null]));
        await page.evaluate(() => window.__T.release());
        await page.waitForURL((url) => url.href.startsWith("https://panel.example/"), { timeout: 15000 });
        return { banner, reached, sent, toPanel, url: page.url() };
    """
    )
    state = run_in_browser(document, scenario, tmp_path, init=init)
    # Only the last page's answers, which carry no outcome (__status) of
    # their own: an ending page sets one. Their way on is redirect_url.
    assert state["sent"] == [[None, 1, "Ann"]]
    assert state["toPanel"] == [_COMPLETED]
    assert state["url"] == _COMPLETED
    # The banner is not in the page while they are sent, so Tab never
    # reaches it.
    assert state["banner"] is False
    assert state["reached"] is False


# The version that saved (its pages and the page saved on, the answers, the
# path, whether the save names the page, and any of its pages it did not show
# the respondent), today's pages, and what the respondent does after Resume:
# nothing, Next to the end, or Previous.
_REPUBLISHED = {
    "a-page-put-in-before-the-endings": (
        (["p1", "p2", "done", "out"], "out", {"gender": 1, "fruit": 2}, ["p1", "p2"], True),
        ["p1", "p2", "p3", "done", "out"],
        "",
    ),
    "its-page-taken-out": (
        (["p1", "p2", "p3", "done", "out"], "p3", {"gender": 1, "fruit": 1}, ["p1", "p2"], True),
        ["p1", "p2", "done", "out"],
        "next",
    ),
    "a-save-without-its-name-and-other-pages": (
        (["p1", "p2", "done", "out"], "out", {"gender": 1, "fruit": 2}, ["p1", "p2"], False),
        ["p1", "p2", "p3", "done", "out"],
        "next",
    ),
    "a-save-without-its-name-and-the-same-pages": (
        (["p1", "p2", "done", "out"], "out", {"gender": 1, "fruit": 2}, ["p1", "p2"], False),
        ["p1", "p2", "done", "out"],
        "next",
    ),
    # The same pages, p3 shown to an Apple alone then and to all today: the
    # place of `out` among a Pear's pages is `done`'s today.
    "a-save-without-its-name-and-p3-shown-to-all": (
        (
            ["p1", "p2", "p3", "done", "out"],
            "out",
            {"gender": 1, "fruit": 2},
            ["p1", "p2"],
            False,
            "p3",
        ),
        ["p1", "p2", "p3", "done", "out"],
        "next",
    ),
    # p3 shown to all then and to a Pear alone today: the place of `done`
    # among an Apple's pages is `out`'s today.
    "a-save-without-its-name-and-p3-for-a-pear": (
        (
            ["p1", "p2", "p3", "done", "out"],
            "done",
            {"gender": 1, "fruit": 1},
            ["p1", "p2", "p3"],
            False,
        ),
        ["p1", "p2", "p3-for-a-pear", "done", "out"],
        "next",
    ),
    "a-save-without-its-name-on-a-page-with-questions": (
        (["p1", "p2", "done", "out"], "p2", {"gender": 1}, ["p1"], False),
        ["p1", "p2", "done", "out"],
        "back",
    ),
    "a-page-put-in-at-the-start": (
        (["p1", "p2", "done", "out"], "p2", {"gender": 1}, ["p1"], True),
        ["p0", "p1", "p2", "done", "out"],
        "back",
    ),
}

_AFTER_RESUME = {
    "": "",
    # The banner, whose Resume _NEXT would click, is gone once it is used.
    "next": _NEXT * 2,
    "back": """
        await page.click(".sd-navigation .sd-navigation__prev-btn");
        await page.waitForTimeout(250);
    """,
}


@pytest.mark.parametrize("case", list(_REPUBLISHED))
def test_resume_opens_the_page_it_was_saved_on_after_a_redeploy(tmp_path, case):
    """The autosave keeps the page by its place among the pages on screen,
    and Resume opened whatever page had that place today. A redeploy under
    the same address with a page more or less before it made that another
    page: with a page put in before the endings, a screen-out page saved by
    Save locally and finish came back as the final page, which sent the
    answers as completed and the participant to redirect_url (cc=COMPLETE).
    The save names the page, and Resume opens the page of that name; with
    no such page, or a save without the name from a version with other
    pages, it opens the first page with the answers kept. So does a save
    without the name on an ending page: a show_if changed on a page before
    it gives its place to another page even with the same pages."""
    (saved_pages, on, answers, history, named, *unseen), today, then = _REPUBLISHED[case]
    init = _saved_on(saved_pages, on, answers, history, named=named, unseen=tuple(unseen))
    scenario = (
        _PANEL
        + _RESUMED
        + """
        await page.click(".siamang-resume-banner .sd-navigation__next-btn");
        await page.waitForTimeout(500);
        const landed = await read();
        if (!landed.statuses.length) {
    """
        + _AFTER_RESUME[then]
        + """
        }
        const after = await read();
        if (after.statuses.length) {
            await page.waitForURL((url) => url.href.startsWith("https://panel.example/"));
        }
        return { landed, after, toPanel };
    """
    )
    state = run_in_browser(_resumed_document(*today), scenario, tmp_path, init=init)
    landed, after = state["landed"], state["after"]
    if then == "":
        # On the screen-out page it was saved on, by its name.
        assert landed["pages"] == ["p1", "out"]
        assert landed["statuses"] == ["screened_out"]
        assert landed["question"] is False
        assert state["toPanel"] == [_SCREENED_OUT]
    elif then == "next":
        # From the first page, the answers kept and nothing sent until the
        # respondent reaches an ending, the one their answers route to.
        assert landed == {"pages": ["p1"], "statuses": [], "question": True, "checked": ["Male"]}
        if answers["fruit"] == 2:
            assert after["pages"] == ["p1", "p2", "out"]
            assert after["statuses"] == ["screened_out"]
            assert state["toPanel"] == [_SCREENED_OUT]
        else:
            assert after["pages"] == ["p1", "p2", "done"]
            assert after["statuses"] == ["completed"]
            assert state["toPanel"] == [_COMPLETED]
    else:
        # On p2, the page it was saved on, by its name or, without it, by its
        # place among the same pages (a control); Previous goes back the way
        # the respondent came, to p1, not to the page before it today.
        assert landed["pages"] == [today[0], "p2"]
        assert landed["statuses"] == [] and landed["question"] is True
        assert after["pages"] == [today[0], "p2", "p1"]
        assert after["checked"] == ["Male"]
        assert state["toPanel"] == []


# ── Header ───────────────────────────────────────────────────────────────────


def test_show_title_false_hides_the_title_beside_an_institution(tmp_path):
    document = _trust_matrix_document()
    document["title"] = "Secret study name"
    document["ui"] = {"show_title": False, "institution_name": "Acme University"}
    scenario = """
        return await page.textContent("header.siamang-header");
    """
    header = run_in_browser(document, scenario, tmp_path)
    assert "Acme University" in header
    assert "Secret study name" not in header


# ── Scripts ──────────────────────────────────────────────────────────────────


def _emails_document() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "title": "Emails",
        "variables": {
            "email": {"scale": "nominal", "dtype": "str"},
            "email2": {"scale": "nominal", "dtype": "str"},
        },
        "pages": [
            {
                "name": "p1",
                "items": [
                    {"type": "OpenText", "id": "email", "var": "email", "text": "Email?"},
                    {"type": "OpenText", "id": "email2", "var": "email2", "text": "Again?"},
                ],
            },
            {"name": "done", "kind": "final", "title": "Thanks"},
        ],
        "scripts": [
            {
                "type": "validate_fields_match",
                "field_a": "email",
                "field_b": "email2",
                "message": "The addresses differ.",
            }
        ],
    }


def test_fields_match_rechecks_when_the_first_field_is_corrected(tmp_path):
    scenario = (
        """
        const fields = page.locator("input.sd-input");
        await fields.nth(0).fill("a@x.org");
        await fields.nth(1).fill("b@x.org");
        await page.click("body");
        await page.waitForTimeout(150);
        const shown = await page.textContent(".sd-page");
        await page.click(".sd-navigation__next-btn");
        await page.waitForTimeout(150);
        const blocked = (await page.$$("text=Again?")).length > 0;
        await fields.nth(0).fill("b@x.org");
        await page.click("body");
        await page.waitForTimeout(150);
        const after = await page.textContent(".sd-page");
    """
        + _NEXT
        + _STATE.replace("return {", "return { shown, blocked, after,")
    )
    state = run_in_browser(_emails_document(), scenario, tmp_path)
    assert "The addresses differ." in state["shown"]
    assert state["blocked"] is True
    # Correcting the *first* field clears the message and lets the respondent on.
    assert "The addresses differ." not in state["after"]
    (submitted,) = state["submitted"]
    assert submitted["email"] == submitted["email2"] == "b@x.org"


# ── The respondent id ────────────────────────────────────────────────────────


def _rid_document() -> dict[str, Any]:
    document = _body_document()
    document["variables"]["rid_seen"] = {"scale": "nominal", "dtype": "str"}
    document["scripts"] = [
        {
            "type": "custom",
            "name": "note_rid",
            "trigger": "onInit",
            "code": "answers.rid_seen = answers.__respondent__;",
        }
    ]
    return document


_FINISH_BODY_DOCUMENT = (
    """
    await page.fill("input.sd-input", "Ann");
    await page.click("body");
"""
    + _NEXT
    + """
    await page.click("text=Pear");
"""
    + _NEXT
)


def test_the_transports_respondent_id_is_the_interviews(tmp_path):
    init = 'window.__T = { rid: "resp-123" };'
    state = run_in_browser(_rid_document(), _FINISH_BODY_DOCUMENT + _STATE, tmp_path, init=init)
    (submitted,) = state["submitted"]
    assert submitted["rid_seen"] == "resp-123"
    assert "__respondent__" not in submitted


def test_without_one_the_runtime_keeps_its_own_once_the_respondent_starts(tmp_path):
    """Opening the survey keeps nothing, a reload included; the first answer
    keeps the id the scripts drew with, so a reload goes on as the same
    respondent; the end of the interview forgets it."""

    key = "siamang_interview_t"  # the transport's survey_id
    scenario = (
        _RELOAD
        + f"""
        const keys = () => page.evaluate(() => Object.keys(localStorage).sort());
        const opened = await keys();
        await reload();
        const reopened = await keys();
        await page.fill("input.sd-input", "Ann");
        await page.click("body");
        // The answer reaches the store when the field commits it.
        await page.waitForFunction(() => localStorage.getItem("{key}") !== null);
        const first = await page.evaluate(() => localStorage.getItem("{key}"));
        const started = (await keys()).filter((key) => !key.startsWith("siamang_answers_"));
        await reload();
        // The answer was saved as the page went: the reload offers it back.
        await page.click("button:text-is('Resume')");
        const again = await page.evaluate(() => localStorage.getItem("{key}"));
    """
        + _FINISH_BODY_DOCUMENT
        + f"""
        const after = await page.evaluate(() => localStorage.getItem("{key}"));
    """
        + _STATE.replace("return {", "return { opened, reopened, first, started, again, after,")
    )
    state = run_in_browser(_rid_document(), scenario, tmp_path)
    assert state["opened"] == [] and state["reopened"] == []
    assert state["started"] == ["siamang_interview_t", "siamang_kept_t"]
    assert state["first"] and state["first"] == state["again"]
    (submitted,) = state["submitted"]
    assert submitted["rid_seen"] == state["first"]
    # A completed interview is forgotten: the next one is a new respondent.
    assert state["after"] is None


# ── Embedded height ──────────────────────────────────────────────────────────


_HOST = """<!doctype html><html><body style="margin:0">
<iframe id="f" src="index.html" style="width:600px;height:300px;border:0"></iframe>
<script>
  window.heights = [];
  window.addEventListener("message", function (e) {
    if (e.data && e.data.type === "siamang:height") {
      window.heights.push(e.data);
      document.getElementById("f").style.height = Math.ceil(e.data.height) + "px";
    }
  });
</script></body></html>"""


def test_an_embedded_survey_tells_its_host_its_height(tmp_path):
    scenario = """
        await page.goto(page.url().replace("index.html", "host.html"));
        const frame = page.frameLocator("#f");
        // Until the last height the host was told is the survey's (a frame
        // later than the render, and later still on a busy machine).
        const told = async () => {
            for (let i = 0; i < 100; i++) {
                const last = await page.evaluate(() => (window.heights.slice(-1)[0] || {}).height);
                const content = await frame.locator("#root").evaluate(
                    (el) => Math.ceil(el.getBoundingClientRect().height));
                if (last === content) return;
                await page.waitForTimeout(50);
            }
        };
        await frame.locator(".sd-page").waitFor();
        await told();
        const first = await page.evaluate(() => window.heights.slice());
        await frame.locator("input.sd-input").fill("Ann");
        await frame.locator(".sd-navigation__next-btn").click();
        await frame.locator("text=Pear").waitFor();
        await told();
        const all = await page.evaluate(() => window.heights.slice());
        const frameHeight = await page.$eval("#f", (f) => f.getBoundingClientRect().height);
        const content = await frame.locator("#root").evaluate(
            (el) => Math.ceil(el.getBoundingClientRect().height));
        return { first, all, frameHeight, content };
    """
    result = run_in_browser(_body_document(), scenario, tmp_path, extra_files={"host.html": _HOST})
    assert result["first"], "no height message on load"
    assert all(set(m) == {"type", "height"} for m in result["all"])
    assert all(isinstance(m["height"], int) and m["height"] > 0 for m in result["all"])
    # The frame follows the survey: it ends up as tall as the content.
    assert result["all"][-1]["height"] == result["content"]
    assert abs(result["frameHeight"] - result["content"]) <= 1


# ── Page dots ────────────────────────────────────────────────────────────────


def _dots_document(**ui: Any) -> dict[str, Any]:
    route = {
        "type": "expression",
        "op": "=",
        "left": {"type": "var", "name": "route"},
        "right": 1,
    }
    return {
        "schema_version": "1.0",
        "title": "Dots",
        "ui": {"progress_style": "both", **ui},
        "variables": {
            "route": {
                "scale": "nominal",
                "labels": [{"code": 1, "label": "Jump"}, {"code": 2, "label": "Stay"}],
            },
            "b": {"scale": "nominal", "dtype": "str"},
            "c": {"scale": "nominal", "dtype": "str"},
        },
        "pages": [
            {
                "name": "p1",
                "title": "One",
                "items": [
                    {
                        "type": "SingleChoice",
                        "id": "route",
                        "var": "route",
                        "text": "Route?",
                        "required": True,
                    }
                ],
                "next_if": [{"condition": route, "target": "p3"}],
            },
            {
                "name": "p2",
                "title": "Two",
                "items": [{"type": "OpenText", "id": "b", "var": "b", "text": "B?"}],
            },
            {
                "name": "p3",
                "title": "Three",
                "items": [{"type": "OpenText", "id": "c", "var": "c", "text": "C?"}],
            },
            {"name": "done", "kind": "final", "title": "Thanks"},
        ],
    }


# The page title on screen, and which dots are enabled.
_WHERE = """
    const where = async () => ({
        title: await page.textContent(".sd-page__title"),
        enabled: await page.$$eval(".siamang-step-dot", (ds) => ds.map((d) => !d.disabled)),
    });
"""


def test_a_page_dot_never_jumps_ahead_of_the_respondent(tmp_path):
    scenario = (
        _WHERE
        + """
        const start = await where();
        // A dot ahead of an unanswered required question does nothing.
        await page.$eval(".siamang-step-dot:nth-child(3)", (d) => d.click());
        await page.waitForTimeout(200);
        const afterForward = await where();
        await page.click("text=Stay");
    """
        + _NEXT
        + _NEXT
        + """
        const onThree = await where();
        await page.$eval(".siamang-step-dot:nth-child(1)", (d) => d.click());
        await page.waitForTimeout(250);
        const back = await where();
        return { start, afterForward, onThree, back };
    """
    )
    state = run_in_browser(_dots_document(), scenario, tmp_path)
    assert state["start"]["enabled"] == [False, False, False]
    assert state["afterForward"]["title"] == "One"
    # On page three, the two pages seen before are reachable; nothing ahead is.
    assert state["onThree"]["title"] == "Three"
    assert state["onThree"]["enabled"] == [True, True, False]
    assert state["back"]["title"] == "One"
    assert state["back"]["enabled"] == [False, False, False]


def test_a_page_dot_does_not_reach_a_page_routing_skipped(tmp_path):
    scenario = (
        _WHERE
        + """
        await page.click("text=Jump");
    """
        + _NEXT
        + """
        const onThree = await where();
        await page.$eval(".siamang-step-dot:nth-child(2)", (d) => d.click());
        await page.waitForTimeout(200);
        const after = await where();
        return { onThree, after };
    """
    )
    state = run_in_browser(_dots_document(), scenario, tmp_path)
    # p2 lies before p3 but was never shown: its dot stays disabled.
    assert state["onThree"]["title"] == "Three"
    assert state["onThree"]["enabled"] == [True, False, False]
    assert state["after"]["title"] == "Three"


def test_page_dots_do_not_go_back_when_going_back_is_off(tmp_path):
    scenario = (
        _WHERE
        + """
        await page.click("text=Stay");
    """
        + _NEXT
        + """
        const onTwo = await where();
        await page.$eval(".siamang-step-dot:nth-child(1)", (d) => d.click());
        await page.waitForTimeout(200);
        return { onTwo, after: await where() };
    """
    )
    state = run_in_browser(_dots_document(allow_back=False), scenario, tmp_path)
    assert state["onTwo"]["enabled"] == [False, False, False]
    assert state["after"]["title"] == "Two"


def test_a_resumed_interview_keeps_the_path_the_dots_go_back_along(tmp_path):
    scenario = (
        _WHERE
        + _RELOAD
        + """
        await page.click("text=Stay");
    """
        + _NEXT
        + _NEXT
        + """
        await page.fill("input.sd-input", "x");
        await page.click("body");
    """
        + _autosaved('answers.c === "x"')
        + """
        await reload(".siamang-resume-banner");
        await page.click(".siamang-resume-banner .sd-navigation__next-btn");
        await page.waitForTimeout(250);
        return { resumed: await where() };
    """
    )
    state = run_in_browser(_dots_document(), scenario, tmp_path)
    assert state["resumed"]["title"] == "Three"
    assert state["resumed"]["enabled"] == [True, True, False]


# ── Limits on an answer ──────────────────────────────────────────────────────


def _limits_document() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "title": "Limits",
        "variables": {
            "n": {"scale": "ratio", "valid_range": [1, 10]},
            "m": {
                "scale": "nominal",
                "labels": [{"code": i, "label": f"L{i}"} for i in range(1, 5)],
            },
        },
        "pages": [
            {
                "name": "p1",
                "items": [
                    {"type": "NumericInput", "id": "n", "var": "n", "text": "How many?"},
                    {
                        "type": "MultiChoice",
                        "id": "m",
                        "var": "m",
                        "text": "Which?",
                        "min_answers": 2,
                    },
                ],
            },
            {"name": "done", "kind": "final", "title": "Thanks"},
        ],
    }


def test_a_number_out_of_range_and_too_few_choices_hold_next(tmp_path):
    scenario = (
        """
        const text = async () => page.textContent(".sd-page");
        await page.fill("input[type=number]", "15");
        await page.click("body");
        await page.waitForTimeout(150);
        const onBlur = await text();
    """
        + _NEXT
        + """
        const afterHigh = await text();
        await page.fill("input[type=number]", "0");
    """
        + _NEXT
        + """
        const afterLow = await text();
        await page.fill("input[type=number]", "5");
        await page.click("body");  // the message goes, and the options move up
        await page.waitForTimeout(150);
        await page.click("text=L1");
    """
        + _NEXT
        + """
        const afterOne = await text();
        await page.click("text=L3");
    """
        + _NEXT
        + _STATE.replace("return {", "return { onBlur, afterHigh, afterLow, afterOne,")
    )
    state = run_in_browser(_limits_document(), scenario, tmp_path)
    assert "Maximum value is 10" in state["onBlur"]
    assert "Maximum value is 10" in state["afterHigh"]
    assert "Minimum value is 1" in state["afterLow"]
    # One choice of a minimum of two: Next is held with the counter's message.
    assert state["afterOne"].count("Select at least 1 more") == 2
    (submitted,) = state["submitted"]
    assert submitted["n"] == 5
    assert submitted["m"] == [1, 3]


def test_an_optional_question_left_empty_is_not_held_by_its_minimum(tmp_path):
    scenario = _NEXT + _STATE
    state = run_in_browser(_limits_document(), scenario, tmp_path)
    (submitted,) = state["submitted"]
    assert "m" not in submitted and "n" not in submitted


def _exclusive_minimum_document(wide: bool) -> dict[str, Any]:
    brands = [(1, "Acme"), (2, "Globex"), (3, "Initech"), (99, "None of these")]
    question: dict[str, Any] = {
        "type": "MultiChoice",
        "id": "brands",
        "text": "Which brands do you know?",
        "required": True,
        "min_answers": 2,
        "exclusive": [99],
    }
    if wide:
        yes_no = [{"code": 0, "label": "No"}, {"code": 1, "label": "Yes"}]
        variables = {f"brands_{c}": {"scale": "nominal", "labels": yes_no} for c, _ in brands}
        question.update(
            var=list(variables),
            mode="wide",
            choices=[{"code": c, "label": label} for c, label in brands],
        )
    else:
        labels = [{"code": c, "label": label} for c, label in brands]
        variables = {"brands": {"scale": "nominal", "labels": labels}}
        question["var"] = "brands"
    return {
        "schema_version": "1.0",
        "title": "Exclusive",
        "variables": variables,
        "pages": [
            {"name": "p", "items": [question]},
            {"name": "done", "kind": "final", "title": "Thanks"},
        ],
    }


@pytest.mark.parametrize("wide", [False, True])
def test_an_exclusive_answer_is_complete_without_the_minimum(tmp_path, wide):
    """Picking "None of these" clears every other choice, so a minimum of two
    can never be met by it: an exclusive answer is a whole answer. The
    counter asks for no more once it is picked, and Next moves on."""

    scenario = (
        """
        const hint = async () => {
            const el = await page.$(".siamang-multi-counter__hint");
            return el ? await el.textContent() : null;
        };
        const before = await hint();
        await page.click("text=None of these");
        await page.waitForTimeout(100);
        const afterNone = await hint();
    """
        + _NEXT
        + """
        const errText = await page.$$eval(".sd-question__error", (els) => els.map((e) => e.textContent));
    """
        + _STATE.replace("return {", "return { before, afterNone, errText,")
    )
    state = run_in_browser(_exclusive_minimum_document(wide), scenario, tmp_path)
    assert state["before"] == "Select at least 2 more"
    assert state["afterNone"] is None
    assert state["errText"] == []
    (submitted,) = state["submitted"]
    if wide:
        assert submitted == {
            "brands_1": 0,
            "brands_2": 0,
            "brands_3": 0,
            "brands_99": 1,
            "__status": "completed",
        }
    else:
        assert submitted == {"brands": [99], "__status": "completed"}


def test_a_regular_choice_beside_the_exclusive_ones_still_needs_the_minimum(tmp_path):
    scenario = (
        """
        await page.click("text=Acme");
    """
        + _NEXT
        + """
        const held = await page.textContent(".sd-page");
    """
        + _STATE.replace("return {", "return { held,")
    )
    state = run_in_browser(_exclusive_minimum_document(False), scenario, tmp_path)
    assert state["held"].count("Select at least 1 more") == 2
    assert state["submitted"] == []


# ── Timed questions ──────────────────────────────────────────────────────────


def _timed_document() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "title": "Timed",
        "variables": {
            "a": {"scale": "nominal", "dtype": "str"},
            "b": {"scale": "nominal", "dtype": "str"},
        },
        "pages": [
            {
                "name": "p1",
                "title": "One",
                "items": [{"type": "OpenText", "id": "a", "var": "a", "text": "A?"}],
            },
            {
                "name": "p2",
                "title": "Two",
                "items": [{"type": "OpenText", "id": "b", "var": "b", "text": "B?"}],
            },
            {"name": "done", "kind": "final", "title": "Thanks"},
        ],
        "scripts": [{"type": "timed_question", "question": "a", "seconds": 1}],
    }


def test_a_timed_question_still_moves_a_respondent_who_waits(tmp_path):
    # Page two comes up by itself once the question's second is over.
    scenario = """
        await page.waitForFunction(
            () => (document.querySelector(".sd-page__title") || {}).textContent === "Two",
            null, { timeout: 10000 });
        return { title: await page.textContent(".sd-page__title") };
    """
    assert run_in_browser(_timed_document(), scenario, tmp_path)["title"] == "Two"


def test_a_timed_questions_timer_ends_with_its_page(tmp_path):
    scenario = (
        """
        await page.fill("input.sd-input", "x");
        await page.click("body");
    """
        + _NEXT
        + """
        await page.waitForTimeout(1600);   // past the question's second
        const title = await page.textContent(".sd-page__title");
        await page.fill("input.sd-input", "y");
        await page.click("body");
    """
        + _NEXT
        + """
        // The interview is over: a late call of the hook submits nothing more.
        await page.evaluate(() => window.siamangNext && window.siamangNext());
        await page.waitForTimeout(250);
    """
        + _STATE.replace("return {", "return { title,")
    )
    state = run_in_browser(_timed_document(), scenario, tmp_path)
    assert state["title"] == "Two"
    assert state["pages"] == ["p1", "p2", "done"]
    (submitted,) = state["submitted"]
    assert submitted["a"] == "x" and submitted["b"] == "y"


# ── Seeded randomization ─────────────────────────────────────────────────────

# The transport's respondent id comes from the page's query string
# (`index.html?rid=r2`, as a panel link carries it), so a scenario changes
# respondent by loading the page again with another one (`visit`). It used to
# come from sessionStorage, set just before a reload: in a tab Playwright had
# just opened, the reloaded document now and then found sessionStorage empty —
# every key the first document had set, gone — and was respondent "r1" again.
_RID_FROM_URL = 'window.__T = { rid: new URLSearchParams(location.search).get("rid") || "r1" };'


def _shuffled_document(**script: Any) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "title": "Shuffle",
        "variables": {
            "brand": {
                "scale": "nominal",
                "labels": [{"code": i, "label": f"B{i}"} for i in range(1, 9)],
            },
        },
        "pages": [
            {
                "name": "p1",
                "items": [
                    {"type": "SingleChoice", "id": "brand", "var": "brand", "text": "Brand?"}
                ],
            },
            {"name": "done", "kind": "final", "title": "Thanks"},
        ],
        "scripts": [{"type": "randomize_options", "question": "brand", **script}],
    }


_ORDER = """
    const order = async () => (await page.$$eval(".sd-choice-label", (ls) => ls.map((l) => l.textContent)));
"""

_AS_R2 = """
    await visit("?rid=r2");
"""


def test_a_seeded_option_shuffle_is_the_respondents_own_and_reproducible(tmp_path):
    scenario = (
        _ORDER
        + _RELOAD
        + """
        const first = await order();
        await reload();
        const reloaded = await order();
    """
        + _AS_R2
        + """
        return { first, reloaded, other: await order() };
    """
    )
    state = run_in_browser(_shuffled_document(seed="42"), scenario, tmp_path, init=_RID_FROM_URL)
    labels = [f"B{i}" for i in range(1, 9)]
    # The order is drawn from "<seed>:<respondent id>" and nothing else.
    assert state["first"] == seeded_shuffle(labels, "42:r1")
    assert state["reloaded"] == state["first"]
    assert state["other"] == seeded_shuffle(labels, "42:r2") != state["first"]


def _assigned_document() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "title": "Assign",
        "variables": {"name": {"scale": "nominal", "dtype": "str"}},
        "pages": [
            {
                "name": "p1",
                "title": "Arm {answer:condition}",
                "items": [{"type": "OpenText", "id": "name", "var": "name", "text": "Name?"}],
            },
            {"name": "done", "kind": "final", "title": "Thanks"},
        ],
        "scripts": [
            {
                "type": "assign_condition",
                "variable": "condition",
                "arms": [{"code": 1, "label": "Control"}, {"code": 2, "label": "Treatment"}],
                "seed": "s1",
            }
        ],
    }


def _seeded_arm(seed: str, respondent: str, codes: list[int]) -> int:
    """The arm Script.assign_condition draws (equal weights), computed apart."""

    cut = mulberry32(fnv1a(f"{seed}:{respondent}"))() * len(codes)
    for code in codes:
        cut -= 1
        if cut < 0:
            return code
    return codes[-1]


def test_a_seeded_assignment_spreads_respondents_and_keeps_each_ones_arm(tmp_path):
    respondents = [f"r{i}" for i in range(12)] + ["r0"]
    # Each respondent is a new document: the id its transport hands over, and
    # the arm on its first page.
    scenario = (
        _RELOAD
        + f"""
        const seen = [];
        for (const rid of {json.dumps(respondents)}) {{
            await visit("?rid=" + rid, ".sd-page__title");
            seen.push(await page.evaluate(() => [
                window.__T.rid, document.querySelector(".sd-page__title").textContent]));
        }}
        return seen;
    """
    )
    seen = run_in_browser(_assigned_document(), scenario, tmp_path, init=_RID_FROM_URL)
    assert [rid for rid, _ in seen] == respondents
    arms = [title for _, title in seen]
    expected = [f"Arm {_seeded_arm('s1', rid, [1, 2])}" for rid in respondents]
    assert arms == expected
    # Both arms are used, and the same respondent lands in the same one again.
    assert set(arms) == {"Arm 1", "Arm 2"}
    assert arms[0] == arms[-1]


# Whether leaving the page now would ask "Leave site?": the runtime's
# beforeunload handler, called the way the browser calls it.
_LEAVING = """
    const leaving = () => page.evaluate(() => {
        const event = new Event("beforeunload", { cancelable: true });
        window.dispatchEvent(event);
        return event.defaultPrevented;
    });
"""


def test_leaving_asks_first_only_once_the_respondent_has_answered(tmp_path):
    scenario = (
        _LEAVING
        + """
        const untouched = await leaving();
        await page.fill("input.sd-input", "Ann");
        // A click beside the page, not at the body's middle: with a section
        // gap under the title, the field is there.
        await page.click("body", { position: { x: 5, y: 5 } });
        return { untouched, answered: await leaving() };
    """
    )
    # The assignment writes its arm into the answers at load; that is not the
    # respondent's work, and a survey opened and left untouched asks nothing.
    state = run_in_browser(_assigned_document(), scenario, tmp_path, init=_RID_FROM_URL)
    assert state == {"untouched": False, "answered": True}


def _pinned_document() -> dict[str, Any]:
    def labels(prefix: str, extra: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [{"code": i, "label": f"{prefix}{i}"} for i in range(1, 7)] + extra

    return {
        "schema_version": "1.0",
        "title": "Pinned",
        "variables": {
            "pet": {"scale": "nominal", "labels": labels("P", [])},
            "fruit": {"scale": "nominal", "labels": labels("F", [{"code": 98, "label": "Other"}])},
            "brands": {
                "scale": "nominal",
                "labels": labels("B", [{"code": 99, "label": "None of these"}]),
            },
        },
        "pages": [
            {
                "name": "p1",
                "items": [
                    {
                        "type": "SingleChoice",
                        "id": "pet",
                        "var": "pet",
                        "text": "Pet?",
                        "none_of_above": True,
                        "randomize": True,
                    },
                    {
                        "type": "SingleChoice",
                        "id": "fruit",
                        "var": "fruit",
                        "text": "Fruit?",
                        "other_specify": True,
                        "metadata": {"other_code": 98},
                        "randomize": True,
                    },
                    {
                        "type": "MultiChoice",
                        "id": "brands",
                        "var": "brands",
                        "text": "Brands?",
                        "exclusive": [99],
                    },
                ],
            },
            {"name": "done", "kind": "final", "title": "Thanks"},
        ],
        "scripts": [{"type": "randomize_options", "question": "brands", "seed": "7"}],
    }


# A repeatable Math.random, so the switch's shuffle is the same on every run.
_FIXED_RANDOM = """
Math.random = (() => { let s = 7; return () => (s = (s * 16807) % 2147483647) / 2147483647; })();
"""


def test_a_shuffle_keeps_none_of_the_above_exclusive_answers_and_other_in_place(tmp_path):
    scenario = """
        return await page.$$eval(".sd-question", (qs) => qs.map(
            (q) => Array.from(q.querySelectorAll(".sd-choice-label"), (l) => l.textContent)));
    """
    pet, fruit, brands = run_in_browser(
        _pinned_document(), scenario, tmp_path, init=_FIXED_RANDOM + _RID_FROM_URL
    )
    assert pet[-1] == "None of the above" and sorted(pet[:-1]) == [f"P{i}" for i in range(1, 7)]
    assert pet[:-1] != [f"P{i}" for i in range(1, 7)]  # the rest was shuffled
    assert fruit[-1] == "Other" and len(fruit) == 7  # no second "Other" is added
    assert fruit[:-1] != [f"F{i}" for i in range(1, 7)]
    # The seeded script deals the movable options only; "None of these" stays last.
    assert brands == seeded_shuffle([f"B{i}" for i in range(1, 7)], "7:r1") + ["None of these"]


# ── What a script's context holds ────────────────────────────────────────────


def _context_document() -> dict[str, Any]:
    seen = ["init_seen", "left_page", "dwell_ok", "last_q", "speeder", "started_seen", "own_page"]
    return {
        "schema_version": "1.0",
        "title": "Context",
        "variables": {
            "name": {"scale": "nominal", "dtype": "str"},
            "x": {"scale": "nominal", "dtype": "str"},
            **{key: {"scale": "nominal", "dtype": "str"} for key in seen},
        },
        "pages": [
            {
                "name": "p1",
                "items": [{"type": "OpenText", "id": "name", "var": "name", "text": "Name?"}],
            },
            {"name": "p2", "items": [{"type": "OpenText", "id": "x", "var": "x", "text": "X?"}]},
            {"name": "done", "kind": "final", "title": "Thanks"},
        ],
        "scripts": [
            {
                "type": "custom",
                "name": "init",
                "trigger": "onInit",
                "context": {"own": "yes"},
                "code": "answers.init_seen = [context.trigger, typeof context.startedAt, "
                "context.respondentId, context.surveyId, context.page, context.own].join('|');",
            },
            {
                "type": "custom",
                "name": "exit",
                "trigger": "onPageExit",
                "code": "answers.left_page = context.page; answers.dwell_ok = "
                "typeof context.pageEnteredAt === 'number' && utils.now() >= context.pageEnteredAt "
                "&& context.pageEnteredAt >= context.startedAt ? 'yes' : 'no';",
            },
            {
                "type": "custom",
                "name": "answer",
                "trigger": "onAnswer",
                "code": "if (context.question !== 'last_q') answers.last_q = context.question;",
            },
            {
                "type": "custom",
                "name": "speeder",
                "trigger": "onSubmit",
                "code": "answers.speeder = utils.now() - context.startedAt < 60000 ? 'fast' : 'slow';"
                " answers.started_seen = String(context.startedAt);",
            },
            {
                "type": "custom",
                "name": "own",
                "trigger": "onPageEnter",
                "context": {"page": "mine"},
                "code": "answers.own_page = context.page;",
            },
        ],
    }


def test_a_scripts_context_carries_what_the_runtime_knows(tmp_path):
    init = 'window.__T = { rid: "resp-9" };'
    scenario = (
        """
        await page.fill("input.sd-input", "Ann");
        await page.click("body");
    """
        + _NEXT
        + """
        await page.fill("input.sd-input", "y");
        await page.click("body");
    """
        + _NEXT
        + _STATE
    )
    state = run_in_browser(_context_document(), scenario, tmp_path, init=init)
    (submitted,) = state["submitted"]
    assert submitted["init_seen"] == "onInit|number|resp-9|t|p1|yes"
    assert submitted["left_page"] == "p2" and submitted["dwell_ok"] == "yes"
    assert submitted["last_q"] == "x"
    assert submitted["speeder"] == "fast"
    # A key the Script sets itself wins over the runtime's.
    assert submitted["own_page"] == "mine"


def test_a_resumed_interview_keeps_the_time_it_started(tmp_path):
    scenario = (
        _RELOAD
        + """
        await page.fill("input.sd-input", "Ann");
        await page.click("body");
    """
        + _autosaved('answers.name === "Ann"')
        + """
        const saved = await page.evaluate(() => {
            const key = Object.keys(localStorage).find((k) => k.startsWith("siamang_answers_"));
            return JSON.parse(localStorage.getItem(key)).startedAt;
        });
        await reload(".siamang-resume-banner");
        await page.click(".siamang-resume-banner .sd-navigation__next-btn");
        await page.waitForTimeout(200);
    """
        + _NEXT
        + """
        await page.fill("input.sd-input", "y");
        await page.click("body");
    """
        + _NEXT
        + _STATE.replace("return {", "return { saved,")
    )
    state = run_in_browser(_context_document(), scenario, tmp_path)
    (submitted,) = state["submitted"]
    assert isinstance(state["saved"], int)
    assert submitted["started_seen"] == str(state["saved"])


def _shuffled_pages_document() -> dict[str, Any]:
    yes_no = [{"code": 1, "label": "Yes"}, {"code": 2, "label": "No"}]
    return {
        "schema_version": "1.0",
        "title": "Shuffled pages",
        "variables": {f"q{i}": {"scale": "nominal", "labels": yes_no} for i in range(1, 7)},
        "pages": [
            *(
                {
                    "name": f"p{i}",
                    "items": [
                        {
                            "type": "SingleChoice",
                            "id": f"q{i}",
                            "var": f"q{i}",
                            "text": f"Question {i}?",
                            "required": True,
                        }
                    ],
                }
                for i in range(1, 7)
            ),
            {"name": "done", "kind": "final", "title": "Thanks"},
        ],
        "scripts": [{"type": "randomize_pages"}],
    }


def test_a_resumed_interview_keeps_its_shuffled_page_order(tmp_path):
    """randomize_pages deals a new order at every load. The first load here
    deals p1 p3 p4 p5 p6 p2 (Math.random is 0), the reload the document's
    order (Math.random is just below 1). Resuming after three pages lands on
    the fourth of the order the respondent was dealt, p5, and goes on in it:
    every page is asked once, not p4 again with p2 or p3 never asked."""

    init = """
        const load = Number(window.name || 0);
        window.name = String(load + 1);
        Math.random = load === 0 ? () => 0 : () => 0.9999;
    """
    answer = (
        """
        await page.click("text=Yes");
    """
        + _NEXT
    )
    scenario = (
        _RELOAD
        + answer * 3
        + """
        const before = await page.evaluate(() => window.__T.pages.slice());
        await page.click("text=No");
    """
        + _autosaved("answers.q5 === 2 || answers.q4 === 2")
        + """
        await reload(".siamang-resume-banner");
        await page.click(".siamang-resume-banner .sd-navigation__next-btn");
        await page.waitForTimeout(200);
        const landed = await page.textContent(".sd-page");
    """
        + answer * 3
        + _STATE.replace("return {", "return { before, landed,")
    )
    state = run_in_browser(_shuffled_pages_document(), scenario, tmp_path, init=init)
    assert state["before"] == ["p1", "p3", "p4", "p5"]
    assert "Question 5?" in state["landed"]
    # The second sitting shows its first page, then (resumed) p5, p6, p2.
    assert state["pages"][1:] == ["p5", "p6", "p2", "done"]
    (submitted,) = state["submitted"]
    assert {key: submitted.get(key) for key in ("q1", "q2", "q3", "q4", "q5", "q6")} == {
        "q1": 1,
        "q2": 1,
        "q3": 1,
        "q4": 1,
        "q5": 1,
        "q6": 1,
    }


# ── Progress indicator ───────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("style", "show", "bar", "dots"),
    [
        ("bar", True, True, False),
        ("dots", True, False, True),
        ("both", True, True, True),
        ("dots", False, False, False),  # Studio's "hidden" after "dots"
        ("both", False, False, False),
        ("bar", False, False, False),
    ],
)
def test_the_progress_indicator_is_what_its_style_says(tmp_path, style, show, bar, dots):
    document = _dots_document()
    document["ui"] = {"progress_style": style}
    document["options"] = {"show_progress": show}
    scenario = """
        return {
            bar: (await page.$$(".siamang-progress")).length > 0,
            dots: (await page.$$(".siamang-step-dots")).length > 0,
        };
    """
    assert run_in_browser(document, scenario, tmp_path) == {"bar": bar, "dots": dots}


def _sections_document(**ui: Any) -> dict[str, Any]:
    pages = [
        {
            "name": f"p{i}",
            "title": f"Page {i}",
            "items": [{"type": "OpenText", "id": f"t{i}", "var": f"t{i}", "text": "?"}],
        }
        for i in range(1, 5)
    ]
    return {
        "schema_version": "1.0",
        "title": "Sections",
        "ui": {"progress_style": "both", **ui},
        "variables": {f"t{i}": {"scale": "nominal", "dtype": "str"} for i in range(1, 5)},
        "pages": [
            *pages,
            {"name": "done", "kind": "final", "title": "Thanks"},
            {"name": "out", "kind": "disqualification", "title": "Sorry"},
        ],
    }


# On every page: the text beside the bar, the eyebrow, the bar's width, the
# number of dots, and the page title — then Next.
_WALK = """
    const seen = [];
    for (let k = 0; k < 4; k++) {
        seen.push(await page.evaluate(() => {
            const text = (sel) => { const el = document.querySelector(sel); return el ? el.textContent : null; };
            const fill = document.querySelector(".siamang-progress__fill");
            return [text(".siamang-progress__text"), text(".sd-page__eyebrow"),
                    fill ? fill.style.width : null,
                    document.querySelectorAll(".siamang-step-dot").length, text(".sd-page__title")];
        }));
        await page.click(".sd-navigation__next-btn");
        await page.waitForTimeout(200);
    }
    return seen;
"""


def test_progress_counts_the_pages_a_respondent_answers(tmp_path):
    seen = run_in_browser(_sections_document(), _WALK, tmp_path)
    # The end pages are not steps: the last question page is "Final thoughts"
    # and 100 %, and there is a dot per question page only.
    assert [row[:4] for row in seen] == [
        ["Welcome", "Welcome", "0%", 4],
        ["Page 2 of 4", "Page 2 of 4", "33%", 4],
        ["Page 3 of 4", "Page 3 of 4", "67%", 4],
        ["Final thoughts", "Final thoughts", "100%", 4],
    ]


def test_without_page_labels_the_bar_says_page_n_of_m(tmp_path):
    ui = {"show_section_numbers": False, "page_text": "Seite", "of_total_text": "von"}
    seen = run_in_browser(_sections_document(**ui), _WALK, tmp_path)
    assert [row[:2] for row in seen] == [
        ["Seite 1 von 4", None],
        ["Seite 2 von 4", None],
        ["Seite 3 von 4", None],
        ["Seite 4 von 4", None],
    ]


def test_the_progress_text_can_be_switched_off(tmp_path):
    seen = run_in_browser(_sections_document(show_progress_text=False), _WALK, tmp_path)
    assert [row[:3] for row in seen][1] == [None, "Page 2 of 4", "33%"]


def test_page_labels_follow_the_respondents_order_of_pages(tmp_path):
    document = _sections_document()
    document["scripts"] = [{"type": "randomize_pages"}]
    seen = run_in_browser(document, _WALK, tmp_path, init=_FIXED_RANDOM)
    # The pages come in another order; the labels stay in the respondent's.
    assert [row[4] for row in seen] == ["Page 1", "Page 3", "Page 4", "Page 2"]
    assert [row[1] for row in seen] == [
        "Welcome",
        "Page 2 of 4",
        "Page 3 of 4",
        "Final thoughts",
    ]


# A respondent reads "page" where the author does: the Next button, the label
# above a page's title, the text beside the bar and what a screen reader is
# told. The survey's own words (its title, the page titles, the questions) are
# the author's; everything else on every page and at the end, visible or named
# for a screen reader, is read for "section".
_RESPONDENT_READS = """
    const reads = () => page.evaluate(() => {
        const out = [];
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        for (let n = walker.nextNode(); n; n = walker.nextNode()) {
            if (!n.parentElement.closest("script, style, template")) out.push(n.textContent);
        }
        const names = ["aria-label", "aria-valuetext", "aria-roledescription", "title", "placeholder", "alt"];
        for (const el of document.querySelectorAll("*")) {
            for (const name of names) if (el.getAttribute(name)) out.push(el.getAttribute(name));
        }
        return out.join("\\n");
    });
    const text = (sel) => page.evaluate((s) => { const el = document.querySelector(s); return el ? el.textContent : null; }, sel);
    const seen = [];
    for (let k = 0; k < 4; k++) {
        seen.push({
            button: await text(".sd-navigation__next-btn, .sd-navigation__complete-btn"),
            bar: await text(".siamang-progress__text"),
            eyebrow: await text(".sd-page__eyebrow"),
            announced: await text(".siamang-announce"),
            reads: await reads(),
        });
        await page.click(".sd-navigation__next-btn, .sd-navigation__complete-btn");
        await page.waitForTimeout(250);
    }
    await page.waitForSelector(".sd-completedpage");
    seen.push({ reads: await reads() });
    return seen;
"""


def _pages_document(*, end_page: bool, **ui: Any) -> dict[str, Any]:
    document = _sections_document(**ui)
    document["title"] = "Parks"
    if not end_page:
        document["pages"] = document["pages"][:4]
    return document


@pytest.mark.parametrize("end_page", [True, False], ids=["end-page", "no-end-page"])
def test_a_respondent_reads_pages_by_default(tmp_path, end_page):
    seen = run_in_browser(_pages_document(end_page=end_page), _RESPONDENT_READS, tmp_path)
    labels = ["Welcome", "Page 2 of 4", "Page 3 of 4", "Final thoughts"]
    assert [row["bar"] for row in seen[:4]] == labels
    assert [row["eyebrow"] for row in seen[:4]] == labels
    # A screen reader is told the bar's count on every page.
    assert [row["announced"] for row in seen[:4]] == [f"Page {i} of 4" for i in range(1, 5)]
    # Next is "Next →"; the last question page submits under its own label,
    # unless an end page comes after it.
    last = "Next \u2192" if end_page else "Submit responses"
    assert [row["button"] for row in seen[:4]] == ["Next \u2192"] * 3 + [last]
    for row in seen:
        assert "section" not in row["reads"].lower(), row["reads"]


@pytest.mark.parametrize(
    ("section_text", "between"),
    [
        # A text written for the old default reads as it did: {n} and {total}
        # leave the first page out.
        ("{n} of {total}", ["1 of 3", "2 of 3"]),
        ("Seite {page} von {pages}", ["Seite 2 von 4", "Seite 3 von 4"]),
        ("Teil {n}/{total} \u00b7 {page}/{pages}", ["Teil 1/3 \u00b7 2/4", "Teil 2/3 \u00b7 3/4"]),
    ],
)
def test_a_surveys_own_page_label_and_next_button_are_its_own(tmp_path, section_text, between):
    ui = {"section_text": section_text, "next_button_text": "Weiter"}
    seen = run_in_browser(_pages_document(end_page=True, **ui), _RESPONDENT_READS, tmp_path)
    assert [row["bar"] for row in seen[1:3]] == between
    assert [row["eyebrow"] for row in seen[1:3]] == between
    assert [row["button"] for row in seen[:4]] == ["Weiter"] * 4


def _screen_out_between_document(**ui: Any) -> dict[str, Any]:
    """Three untitled question pages with a Screen-out page after the first,
    which the first page's default_next goes past, and an end page."""

    def page(i: int) -> dict[str, Any]:
        return {
            "name": f"p{i}",
            "items": [{"type": "OpenText", "id": f"t{i}", "var": f"t{i}", "text": "?"}],
        }

    return {
        "schema_version": "1.0",
        "title": "Parks",
        "ui": {"progress_style": "both", **ui},
        "variables": {f"t{i}": {"scale": "nominal", "dtype": "str"} for i in range(1, 4)},
        "pages": [
            {**page(1), "default_next": "p2"},
            {"name": "out", "kind": "disqualification"},
            page(2),
            page(3),
            {"name": "done", "kind": "final", "title": "Thanks"},
        ],
    }


# On every question page: what each step dot is named and which is current,
# the text beside the bar and what a screen reader is told — then Next.
_DOTS_READ = """
    const seen = [];
    for (let k = 0; k < 3; k++) {
        seen.push(await page.evaluate(() => {
            const dots = [...document.querySelectorAll(".siamang-step-dot")];
            const text = (sel) => { const el = document.querySelector(sel); return el ? el.textContent : null; };
            return {
                dots: dots.map((d) => d.getAttribute("aria-label")),
                current: dots.findIndex((d) => d.getAttribute("aria-current") === "step"),
                bar: text(".siamang-progress__text"),
                announced: text(".siamang-announce"),
            };
        }));
        await page.click(".sd-navigation__next-btn, .sd-navigation__complete-btn");
        await page.waitForTimeout(250);
    }
    return seen;
"""


@pytest.mark.parametrize(
    ("ui", "page_word", "of_word"),
    [
        ({}, "Page", "of"),
        # The survey's "Page" and "of" word the dots and, without its own
        # section_text, the label between the first page and the last.
        ({"page_text": "Seite", "of_total_text": "von"}, "Seite", "von"),
    ],
    ids=["default", "translated"],
)
def test_a_step_dot_and_the_page_label_count_as_the_bar_does(tmp_path, ui, page_word, of_word):
    seen = run_in_browser(_screen_out_between_document(**ui), _DOTS_READ, tmp_path)
    # An end page between two pages is no step: the second question page is
    # page 2 for its dot, its label, the bar and a screen reader alike. The
    # current dot is marked by aria-current, not by its name.
    assert [row["dots"] for row in seen] == [[f"{page_word} {i}" for i in (1, 2, 3)]] * 3
    assert [row["current"] for row in seen] == [0, 1, 2]
    between = f"{page_word} 2 {of_word} 3"
    assert [row["bar"] for row in seen] == ["Welcome", between, "Final thoughts"]
    assert [row["announced"] for row in seen] == [f"{page_word} {i} {of_word} 3" for i in (1, 2, 3)]


def test_the_walkthrough_trace_counts_the_pages_a_respondent_answers(tmp_path):
    """A host's walkthrough can print where the page is beside its preview:
    `step` of `steps` is the respondent's "Page n of m" (none on an end page),
    while `position` of `total` counts every visible page, end pages
    included."""

    scenario = """
        const last = async () => {
            await page.waitForTimeout(300);
            const t = await page.evaluate(() => window.__traces[window.__traces.length - 1]);
            return [t.page, t.position, t.total, t.step, t.steps];
        };
        const seen = [];
        for (let k = 0; k < 3; k++) {
            seen.push(await last());
            await page.click(".sd-navigation__next-btn, .sd-navigation__complete-btn");
        }
        seen.push(await last());
        return seen;
    """
    seen = run_in_browser(_screen_out_between_document(), scenario, tmp_path, init=_TRACES)
    assert seen == [
        ["p1", 1, 5, 1, 3],
        ["p2", 3, 5, 2, 3],
        ["p3", 4, 5, 3, 3],
        ["done", 5, 5, None, 3],
    ]


# ── Wording ──────────────────────────────────────────────────────────────────

_GERMAN = {
    "estimated_minutes": 12,
    "estimated_time_text": "Etwa {minutes} Minuten",
    "welcome_text": "Willkommen",
    "section_text": "Teil {n} von {total}",
    "final_section_text": "Zum Schluss",
    "select_placeholder": "— Bitte wählen —",
    "of_text": "von",
    "selected_text": "ausgewählt",
    "other_text": "Sonstiges",
    "other_placeholder": "Bitte angeben",
    "none_of_above_text": "Nichts davon",
    "min_choices_text": "Noch {n} auswählen",
    "invalid_email_text": "Bitte eine gültige E-Mail-Adresse",
    "privacy_url": "https://example.org/privacy",
    "privacy_text": "Datenschutz",
    "contact_email": "team@example.org",
    "contact_text": "Kontakt",
    "skip_link_text": "Zum Fragebogen",
    "response_id_text": "Antwort-Nr.",
    "submitted_text": "Gesendet",
    "completion_title": "Danke!",
    "completion_body": "Ihre Antworten sind gespeichert.",
}


def _worded_document(**ui: Any) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "title": "Wording",
        "ui": ui,
        "variables": {
            "city": {
                "scale": "nominal",
                "labels": [{"code": 1, "label": "Oslo"}, {"code": 2, "label": "Rom"}],
            },
            "m": {
                "scale": "nominal",
                "labels": [{"code": i, "label": f"M{i}"} for i in range(1, 5)],
            },
            "pet": {"scale": "nominal", "labels": [{"code": 1, "label": "Katze"}]},
            "mail": {"scale": "nominal", "dtype": "str"},
            "note": {"scale": "nominal", "dtype": "str"},
        },
        "pages": [
            {
                "name": "p1",
                "items": [
                    {
                        "type": "SingleChoice",
                        "id": "city",
                        "var": "city",
                        "text": "Stadt?",
                        "display": "dropdown",
                        "other_specify": True,
                    }
                ],
            },
            {
                "name": "p2",
                "items": [
                    {
                        "type": "MultiChoice",
                        "id": "m",
                        "var": "m",
                        "text": "M?",
                        "min_answers": 2,
                        "max_answers": 3,
                    },
                    {
                        "type": "SingleChoice",
                        "id": "pet",
                        "var": "pet",
                        "text": "Tier?",
                        "none_of_above": True,
                    },
                    {
                        "type": "OpenText",
                        "id": "mail",
                        "var": "mail",
                        "text": "E-Mail?",
                        "format": "email",
                    },
                ],
            },
            {
                "name": "p3",
                "items": [{"type": "OpenText", "id": "note", "var": "note", "text": "Noch etwas?"}],
            },
        ],
    }


def test_the_runtime_speaks_the_surveys_wording(tmp_path):
    scenario = """
        const text = (sel) => page.$eval(sel, (el) => el.textContent);
        const first = {
            eyebrow: await text(".sd-page__eyebrow"),
            estimate: await text(".sd-page__estimate"),
            trigger: await text(".siamang-search-dropdown__trigger"),
            skip: await text(".siamang-skip-link"),
            footer: await text(".siamang-footer"),
        };
        await page.click(".siamang-search-dropdown__trigger");
        await page.click(".siamang-search-dropdown__option >> text=Sonstiges");
        await page.waitForTimeout(100);
        first.otherPlaceholder = await page.getAttribute(".sd-other-input__field", "placeholder");
        await page.fill(".sd-other-input__field", "Bergen");
        await page.locator(".sd-other-input__field").blur();
        await page.click(".sd-navigation__next-btn");
        await page.waitForTimeout(250);
        const second = { eyebrow: await text(".sd-page__eyebrow"), estimate: (await page.$$(".sd-page__estimate")).length };
        await page.click("text=M1");
        await page.fill("input.sd-input", "nope");
        await page.locator("input.sd-input").blur();
        await page.waitForTimeout(100);
        second.counter = await text(".siamang-multi-counter");
        second.none = await page.$$eval(".sd-choice-label", (ls) => ls.map((l) => l.textContent));
        await page.click(".sd-navigation__next-btn");
        await page.waitForTimeout(250);
        second.errors = await page.$$eval(".sd-question__error", (es) => es.map((e) => e.textContent));
        await page.click("text=M2");
        await page.fill("input.sd-input", "a@b.org");
        await page.locator("input.sd-input").blur();
        await page.waitForTimeout(100);
        await page.click(".sd-navigation__next-btn");
        await page.waitForTimeout(250);
        const third = { eyebrow: await text(".sd-page__eyebrow") };
        await page.click(".sd-navigation__complete-btn");
        await page.waitForSelector(".sd-completedpage");
        const done = await text(".sd-completedpage");
        return { first, second, third, done };
    """
    state = run_in_browser(_worded_document(**_GERMAN), scenario, tmp_path)
    first, second = state["first"], state["second"]
    assert first["eyebrow"] == "Willkommen"
    assert first["estimate"] == "Etwa 12 Minuten"
    assert first["trigger"] == "— Bitte wählen —"
    assert first["skip"] == "Zum Fragebogen"
    assert "Datenschutz" in first["footer"] and "Kontakt" in first["footer"]
    assert first["otherPlaceholder"] == "Bitte angeben"
    assert second["eyebrow"] == "Teil 1 von 2" and second["estimate"] == 0
    assert second["counter"] == "1 von 3 ausgewähltNoch 1 auswählen"
    assert "Nichts davon" in second["none"]
    assert second["errors"] == ["Noch 1 auswählen", "Bitte eine gültige E-Mail-Adresse"]
    assert state["third"]["eyebrow"] == "Zum Schluss"
    for phrase in ("Danke!", "Ihre Antworten sind gespeichert.", "Antwort-Nr.", "Gesendet"):
        assert phrase in state["done"]


def test_the_estimated_time_has_an_english_default(tmp_path):
    scenario = 'return await page.textContent(".sd-page__estimate");'
    one = run_in_browser(_worded_document(estimated_minutes=1), scenario, tmp_path / "one")
    many = run_in_browser(_worded_document(estimated_minutes=12), scenario, tmp_path / "many")
    assert (one, many) == ("About 1 minute", "About 12 minutes")


def test_the_quota_full_screen_speaks_the_surveys_wording(tmp_path):
    init = 'window.__T = { full: [["gender", 1]] };'
    ui = {"quota_full_title": "Vielen Dank", "quota_full_body": "Die Stichprobe ist voll."}
    scenario = (
        """
        await page.click("text=Male");
    """
        + _NEXT
        + _CLOSED
        + "return text;"
    )
    text = run_in_browser(_quota_document(**ui), scenario, tmp_path, init=init)
    assert "Vielen Dank" in text and "Die Stichprobe ist voll." in text


# ── What the browser keeps, per survey ───────────────────────────────────────


def test_what_the_browser_keeps_is_keyed_by_the_transports_survey_id(tmp_path):
    scenario = (
        """
        await page.fill("input.sd-input", "Ann");
        await page.click("body");
    """
        + _autosaved('answers.name === "Ann"')
        + """
        return await page.evaluate(() => Object.keys(localStorage).sort());
    """
    )
    keys = run_in_browser(_body_document(), scenario, tmp_path)
    # The test transport's survey_id is "t"; a host such as Studio reads
    # siamang_answers_<survey_id> to post partial responses.
    assert "siamang_answers_t" in keys and "siamang_interview_t" in keys
    assert not any(key.endswith("siamang_survey") for key in keys)


def test_another_surveys_saved_answers_are_not_offered_for_resuming(tmp_path):
    # What another survey on the same host saved under the key every survey
    # used to share.
    saved = {"answers": {"name": "Other study"}, "pageIdx": 1, "savedAt": "2099-01-01T00:00:00Z"}
    key = "siamang_answers_siamang_survey"
    init = f"localStorage.setItem('{key}', " + json.dumps(json.dumps(saved)) + ");"
    scenario = 'return (await page.$$(".siamang-resume-banner")).length;'
    assert run_in_browser(_body_document(), scenario, tmp_path, init=init) == 0


# ── What the browser keeps, and for how long ─────────────────────────────────

_DAY_MS = 24 * 60 * 60 * 1000


def _keep(key: str, value: Any) -> str:
    """An init-script line that leaves ``key`` in localStorage: ``value``, as
    JSON unless it is a string."""

    text = value if isinstance(value, str) else json.dumps(value)
    return f"localStorage.setItem({json.dumps(key)}, {json.dumps(text)});"


def _note(survey_id: str, days_ago: float) -> str:
    """The note of a survey that last wrote in this browser ``days_ago``."""

    at = f"String(Date.now() - {days_ago * _DAY_MS})"
    return f"localStorage.setItem({json.dumps('siamang_kept_' + survey_id)}, {at});"


def _draft(days_ago: float, name: str = "Ann") -> str:
    """An autosave of the body document's first page, saved ``days_ago``."""

    return (
        "localStorage.setItem('siamang_answers_t', JSON.stringify({ answers: { name: "
        + json.dumps(name)
        + "}, pageIdx: 0, savedAt: new Date(Date.now() - "
        + str(days_ago * _DAY_MS)
        + ").toISOString() }));"
    )


_KEYS = "return await page.evaluate(() => Object.keys(localStorage).sort());"


def test_opening_a_survey_keeps_nothing_in_the_browser(tmp_path):
    # Well past the autosave's 2 s: nothing is pending either.
    scenario = "await page.waitForTimeout(2500);" + _KEYS
    assert run_in_browser(_body_document(), scenario, tmp_path) == []


def test_the_theme_button_keeps_the_choice_and_nothing_else(tmp_path):
    scenario = "await page.click('.siamang-theme-toggle');" + _KEYS
    keys = run_in_browser(_body_document(), scenario, tmp_path)
    assert keys == ["siamang_kept_t", "siamang_theme_t"]


def test_what_a_survey_kept_goes_a_week_after_it_last_wrote(tmp_path):
    init = "".join(
        [
            # This survey, last written eight days ago: its draft, its
            # interview, its theme — and the one-response mark a host keeps.
            _draft(8),
            _keep("siamang_interview_t", "old-id"),
            _keep("siamang_theme_t", "dark"),
            _note("t", 8),
            _keep("siamang_done_t", "2026-01-01T00:00:00.000Z"),
            # Another survey on the origin, as old (a host's respondent id),
            # and a third written yesterday.
            _keep("siamang_respondent_old", "r-1"),
            _keep("siamang_ended_old", "1"),
            _note("old", 10),
            _keep("siamang_answers_fresh", {"answers": {"q": 1}}),
            _note("fresh", 1),
            _keep("unrelated", "kept"),
        ]
    )
    scenario = """
        const banner = !!(await page.$(".siamang-resume-banner"));
        const theme = await page.getAttribute("html", "data-theme");
        const keys = await page.evaluate(() => Object.keys(localStorage).sort());
        return { banner, theme, keys };
    """
    state = run_in_browser(_body_document(), scenario, tmp_path, init=init)
    # Nothing of the old interview is offered or applied …
    assert state["banner"] is False
    assert state["theme"] == "light"
    # … and it is gone, but for the mark that has to outlast the week.
    assert state["keys"] == [
        "siamang_answers_fresh",
        "siamang_done_t",
        "siamang_kept_fresh",
        "unrelated",
    ]


def test_a_draft_saved_days_ago_is_still_offered_back(tmp_path):
    init = _draft(6) + _note("t", 6)
    scenario = """
        await page.waitForSelector(".siamang-resume-banner");
        await page.click(".siamang-resume-banner .sd-navigation__next-btn");
        return await page.inputValue("input.sd-input");
    """
    assert run_in_browser(_body_document(), scenario, tmp_path, init=init) == "Ann"


def test_a_completed_interview_leaves_no_draft_behind(tmp_path):
    scenario = (
        """
        await page.fill("input.sd-input", "Ann");
        await page.click("body");
    """
        + _autosaved('answers.name === "Ann"')
        + _NEXT
        + """
        await page.click("text=Pear");
    """
        + _NEXT
        + """
        const submitted = (await page.evaluate(() => window.__T.submitted)).length;
    """
        + _AFTER_THE_AUTOSAVE
        + """
        const keys = await page.evaluate(() => Object.keys(localStorage).sort());
        return { kept, banner, keys, submitted };
    """
    )
    state = run_in_browser(_body_document(), scenario, tmp_path)
    assert state["submitted"] == 1
    assert state["kept"] is None and state["banner"] is False
    # Neither the answers nor the interview's id, and — once the page has
    # opened again — not the note that dated them either.
    assert state["keys"] == []


def test_a_page_that_keeps_its_state_in_memory_leaves_nothing_behind(tmp_path):
    init = "".join(
        [
            'window.SIAMANG_STORAGE = "memory";',
            _draft(1),
            _note("t", 1),
            _keep("siamang_theme_old", "dark"),
            _note("old", 30),
        ]
    )
    scenario = """
        const banner = !!(await page.$(".siamang-resume-banner"));
        await page.fill("input.sd-input", "Ann");
        await page.click("body");
        await page.click(".siamang-theme-toggle");
        await page.waitForTimeout(3000);
        const keys = await page.evaluate(() => Object.keys(localStorage).sort());
        return { banner, keys };
    """
    state = run_in_browser(_body_document(), scenario, tmp_path, init=init)
    # The browser's storage is neither read (no banner for yesterday's draft)
    # nor written (no id, no theme) nor swept (the month-old theme is there).
    assert state["banner"] is False
    assert state["keys"] == [
        "siamang_answers_t",
        "siamang_kept_old",
        "siamang_kept_t",
        "siamang_theme_old",
    ]


# ── The typefaces, from the survey's own host ────────────────────────────────

_SERVED_HARNESS = r"""
const [url] = process.argv.slice(2);
let chromium;
try { ({ chromium } = require("playwright")); }
catch (e) { console.log(JSON.stringify({ skip: "playwright is not installed" })); process.exit(0); }
(async () => {
  let browser;
  try {
    const exe = process.env.PLAYWRIGHT_CHROMIUM;
    browser = await chromium.launch(exe ? { executablePath: exe } : {});
  } catch (e) {
    console.log(JSON.stringify({ skip: "no Chromium: " + String(e.message).split("\n")[0] }));
    process.exit(0);
  }
  const errors = [];
  try {
    const page = await browser.newPage();
    page.on("pageerror", (e) => errors.push(e.message));
    const origin = new URL(url).origin;
    const requested = [];
    page.on("request", (r) => requested.push(r.url()));
    // Whatever is not the survey's own host never answers.
    await page.route(/.*/, (route) =>
      new URL(route.request().url()).origin === origin ? route.continue() : route.abort());
    await page.goto(url);
    await page.waitForSelector(".sd-page", { timeout: 15000 });
    const families = ["Source Serif 4", "Inter"];
    await page.waitForFunction((names) => names.every((name) => Array.from(document.fonts)
      .some((f) => f.family.replace(/"/g, "") === name && f.status === "loaded")), families,
      { timeout: 15000 });
    console.log(JSON.stringify({ result: { requested, origin }, errors }));
  } finally {
    await browser.close();
  }
})().catch((e) => { console.log(JSON.stringify({ error: String((e && e.stack) || e), errors: [] })); });
"""


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        pass


def test_the_typefaces_load_from_the_surveys_own_host(tmp_path):
    """Served over HTTP as a host serves it (a browser does not load a font
    from file://), the academic preset's two families load, from fonts/ next
    to the stylesheet, and the page asks nothing of any other host."""

    node = _node()
    out = build_bundle(_body_document(), tmp_path / "bundle")
    handler = functools.partial(_QuietHandler, directory=str(out))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    harness = tmp_path / "served.cjs"
    harness.write_text(_SERVED_HARNESS, encoding="utf-8")
    try:
        result = subprocess.run(
            [node, str(harness), f"http://127.0.0.1:{server.server_address[1]}/index.html"],
            capture_output=True,
            text=True,
            timeout=120,
            env={**os.environ},
        )
    finally:
        server.shutdown()
        server.server_close()
    lines = [line for line in result.stdout.splitlines() if line.startswith("{")]
    assert lines, f"browser harness printed nothing:\n{result.stdout}\n{result.stderr}"
    outcome = json.loads(lines[-1])
    if "skip" in outcome:
        pytest.skip(outcome["skip"])
    assert "error" not in outcome, outcome.get("error")
    assert outcome["errors"] == []
    requested = outcome["result"]["requested"]
    origin = outcome["result"]["origin"]
    assert all(url.startswith(origin + "/") for url in requested), requested
    fonts = {url.rsplit("/", 1)[-1] for url in requested if "/fonts/" in url}
    # The English page needs the latin subsets, and only those are fetched.
    assert fonts == {"source-serif-4-latin-opsz-normal.woff2", "inter-latin-wght-normal.woff2"}
