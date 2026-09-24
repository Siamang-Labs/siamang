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
    document: dict[str, Any], scenario: str, tmp_path: Path, *, init: str = ""
) -> Any:
    """Open ``document`` as a respondent and run ``scenario`` — the body of an
    async function of Playwright's ``page`` — returning what it returns."""

    node = _node()
    out = build_bundle(document, tmp_path / "bundle")
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

_NEXT = """
    await page.click(".sd-navigation__next-btn, .sd-navigation__complete-btn");
    await page.waitForTimeout(250);
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
            JSON.parse(localStorage.getItem("siamang_answers_siamang_survey") || "{}")) };
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
        localStorage.setItem("siamang_answers_siamang_survey", JSON.stringify({
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
        localStorage.setItem("siamang_answers_siamang_survey", JSON.stringify({
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
        localStorage.setItem("siamang_answers_siamang_survey", JSON.stringify({
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
