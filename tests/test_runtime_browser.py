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
    assert submitted["trust"]["trust_parl"] == 2
    assert submitted["trust"]["trust_pol"] == 10
