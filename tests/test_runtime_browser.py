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

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from siamang.frontend import ClientEnv, FrontendBuilder, ReactRuntime, UIConfig
from siamang.frontend.client.base import BackendClientTemplate
from siamang.frontend.compiler import compile_questionnaire
from siamang.model import from_document

from .test_runtime_store import fnv1a, mulberry32, seeded_shuffle

# A transport that keeps everything it is handed. `window.__T.full` lists the
# quota cells ([variable, value]) that answer "full"; `quotaThrows` makes every
# check fail the way an unreachable server does.
_TRANSPORT = r"""
window.SIAMANG_ENV = { transport: "test", survey_id: "t" };
window.SIAMANG_TRANSPORTS = window.SIAMANG_TRANSPORTS || {};
window.__T = Object.assign({ full: [], quotaThrows: false }, window.__T || {},
  { submitted: [], quotaCalls: [], pages: [] });
window.SIAMANG_TRANSPORTS.test = {
  onPage(p) { window.__T.pages.push(p.name); },
  async submit(r) {
    window.__T.submitted.push(JSON.parse(JSON.stringify(r)));
    return { response_id: 7 };
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


def build_bundle(document: dict[str, Any], out: Path) -> Path:
    """Compile a questionnaire document into a static bundle under ``out``."""

    loaded = from_document(document)
    options = dict(loaded.options)
    ui = options.pop("ui", None) or UIConfig()
    schema = compile_questionnaire(loaded.survey, options=options)
    env = ClientEnv(survey_id="t", backend="test", settings={})
    bundle = FrontendBuilder(ui=ui, runtime=ReactRuntime()).build(
        schema, client=_RecordingClient(), env=env, survey=loaded.survey
    )
    return bundle.write_to(out)


def run_in_browser(
    document: dict[str, Any],
    scenario: str,
    tmp_path: Path,
    *,
    init: str = "",
    extra_files: dict[str, str] | None = None,
) -> Any:
    """Open ``document`` as a respondent and run ``scenario`` — the body of an
    async function of Playwright's ``page`` — returning what it returns.
    ``extra_files`` are written next to the bundle's index.html."""

    node = _node()
    out = build_bundle(document, tmp_path / "bundle")
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
# read afterwards can come from the interview that was on screen before.
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
        await page.click("text=Acme");   // unticked again: the question is unanswered
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


def test_without_one_the_runtime_keeps_its_own_until_the_interview_ends(tmp_path):
    key = "siamang_interview_t"  # the transport's survey_id
    scenario = (
        _RELOAD
        + f"""
        const first = await page.evaluate(() => localStorage.getItem("{key}"));
        await reload();
        const again = await page.evaluate(() => localStorage.getItem("{key}"));
    """
        + _FINISH_BODY_DOCUMENT
        + f"""
        const after = await page.evaluate(() => localStorage.getItem("{key}"));
    """
        + _STATE.replace("return {", "return { first, again, after,")
    )
    state = run_in_browser(_rid_document(), scenario, tmp_path)
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


# ── Seeded randomisation ─────────────────────────────────────────────────────

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
        ["Section 1 of 3", "Section 1 of 3", "33%", 4],
        ["Section 2 of 3", "Section 2 of 3", "67%", 4],
        ["Final thoughts", "Final thoughts", "100%", 4],
    ]


def test_without_section_labels_the_bar_says_page_n_of_m(tmp_path):
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
    assert [row[:3] for row in seen][1] == [None, "Section 1 of 3", "33%"]


def test_section_labels_follow_the_respondents_order_of_pages(tmp_path):
    document = _sections_document()
    document["scripts"] = [{"type": "randomize_pages"}]
    seen = run_in_browser(document, _WALK, tmp_path, init=_FIXED_RANDOM)
    # The pages come in another order; the labels stay in the respondent's.
    assert [row[4] for row in seen] == ["Page 1", "Page 3", "Page 4", "Page 2"]
    assert [row[1] for row in seen] == [
        "Welcome",
        "Section 1 of 3",
        "Section 2 of 3",
        "Final thoughts",
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
