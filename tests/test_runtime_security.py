"""In Chromium: nothing an author writes runs, and the runtime works under a
Content-Security-Policy that lets nothing else run.

``test_safety.py`` checks what the engine writes; these play it. The bundle is
served over HTTP from its own origin (as a survey host serves it), every other
origin refused, and a payload that runs sets ``window.__pwned`` (``alert`` and
friends do too). The runtime's own last lines are called in Node: a redirect
goes only to an http(s) address however it was built.
"""

from __future__ import annotations

import functools
import http.server
import json
import os
import subprocess
import threading
from pathlib import Path
from typing import Any

import pytest

from siamang.frontend.csp import insert_csp_meta, survey_csp

from .test_runtime_browser import _cmp, _node, _QuietHandler, _var, build_bundle
from .test_runtime_store import run_js
from .test_safety import BODY_PAYLOADS, LEGITIMATE, TEXT_PAYLOADS

# Opens the served page with `init` run first in every document, plays
# `scenario` (the body of an async function of `page`), and reports what it
# returned, the page's errors, its dialogs and every CSP violation.
_HARNESS = r"""
const [url, scenarioFile, initFile] = process.argv.slice(2);
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
  const dialogs = [];
  try {
    const page = await browser.newPage();
    page.on("pageerror", (e) => errors.push(e.message));
    page.on("dialog", (d) => { dialogs.push(d.message()); d.dismiss().catch(() => {}); });
    const origin = new URL(url).origin;
    await page.route(/.*/, (route) =>
      new URL(route.request().url()).origin === origin ? route.continue() : route.abort());
    await page.addInitScript(
      "window.__csp = [];" +
      "document.addEventListener('securitypolicyviolation', (e) => window.__csp.push(e.effectiveDirective + ' ' + e.blockedURI));" +
      fs.readFileSync(initFile, "utf8"));
    await page.goto(url);
    await page.waitForSelector(".sd-page", { timeout: 15000 });
    const scenario = new Function("page", "return (async () => {" +
      fs.readFileSync(scenarioFile, "utf8") + "})();");
    const result = await scenario(page);
    console.log(JSON.stringify({ result, errors, dialogs }));
  } finally {
    await browser.close();
  }
})().catch((e) => { console.log(JSON.stringify({ error: String((e && e.stack) || e), errors: [], dialogs: [] })); });
"""

# Next, pressed from the page: a 560×315 player above the button can be under
# the pointer while the page scrolls smoothly to it, and take the click.
_NEXT_JS = """
    await page.$eval(".sd-navigation__next-btn, .sd-navigation__complete-btn", (b) => b.click());
    await page.waitForTimeout(250);
    await page.evaluate(() => new Promise((done) =>
        requestAnimationFrame(() => requestAnimationFrame(() => done()))));
"""

# Whatever a payload runs ends up here.
_TRAP = """
window.__pwned = undefined;
for (const name of ["alert", "confirm", "prompt"]) window[name] = () => { window.__pwned = name; };
"""


def run_served(out: Path, scenario: str, tmp_path: Path, *, init: str = _TRAP) -> dict[str, Any]:
    """Serve the bundle in ``out``, play ``scenario`` and return the outcome
    (``result``, ``errors``, ``dialogs``)."""

    node = _node()
    handler = functools.partial(_QuietHandler, directory=str(out))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    harness = tmp_path / "security.cjs"
    harness.write_text(_HARNESS, encoding="utf-8")
    scenario_file = tmp_path / "scenario.js"
    scenario_file.write_text(scenario, encoding="utf-8")
    init_file = tmp_path / "init.js"
    init_file.write_text(init, encoding="utf-8")
    try:
        result = subprocess.run(
            [
                node,
                str(harness),
                f"http://127.0.0.1:{server.server_address[1]}/index.html",
                str(scenario_file),
                str(init_file),
            ],
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
    return outcome


# ── Nothing an author wrote runs ─────────────────────────────────────────────

_PLAYER = (
    '<iframe width="560" height="315" src="https://www.youtube.com/embed/aBcDeFgHiJ0" '
    'title="Clip" allowfullscreen></iframe>'
)


def _hostile_document() -> dict[str, Any]:
    labels = [{"code": i + 1, "label": text} for i, text in enumerate(TEXT_PAYLOADS)]
    return {
        "schema_version": "1.0",
        "title": TEXT_PAYLOADS[0],
        "variables": {"q": {"scale": "nominal", "labels": labels}},
        "pages": [
            {
                "name": "p1",
                "title": TEXT_PAYLOADS[1],
                "body": "<p>Read <b>this</b>.</p>"
                + "".join(BODY_PAYLOADS)
                + _PLAYER
                + '<img class="ok" src="data:image/png;base64,iVBORw0KGgo=" alt="dot">',
                "items": [
                    {"type": "SingleChoice", "id": "q", "var": "q", "text": TEXT_PAYLOADS[2]}
                ],
            },
            {
                "name": "done",
                "kind": "final",
                "title": TEXT_PAYLOADS[0],
                "body": "".join(BODY_PAYLOADS),
            },
        ],
        "ui": {
            "institution_name": TEXT_PAYLOADS[1],
            "next_button_text": TEXT_PAYLOADS[0],
            "ethics_statement": TEXT_PAYLOADS[2],
            "privacy_url": "https://uni.example/privacy",
        },
    }


def test_nothing_an_author_wrote_runs_and_what_they_meant_is_shown(tmp_path):
    out = build_bundle(_hostile_document(), tmp_path / "bundle")
    scenario = (
        """
        await page.waitForTimeout(800);
        await page.evaluate(() => {
            window.questionTitle = (t) => Array.from(t.querySelectorAll("span"))
                .filter((s) => !/sd-question__(num|required)/.test(s.className))
                .map((s) => s.textContent).join("");
        });
        const before = await page.evaluate(() => ({
            pwned: window.__pwned ?? null,
            href: location.href,
            base: document.baseURI,
            title: questionTitle(document.querySelector(".sd-question__title")),
            next: document.querySelector(".sd-navigation__next-btn, .sd-navigation__complete-btn").textContent,
            body: (() => {
                const b = document.querySelector(".sd-page__body");
                return {
                    bold: b.querySelector("b") && b.querySelector("b").textContent,
                    frames: Array.from(b.querySelectorAll("iframe")).map((f) => [
                        f.getAttribute("src"), f.getAttribute("referrerpolicy"), f.hasAttribute("srcdoc")]),
                    handlers: Array.from(b.querySelectorAll("*")).flatMap((el) =>
                        Array.from(el.attributes).map((a) => a.name)).filter((n) => n.startsWith("on")),
                    links: Array.from(b.querySelectorAll("a[href]")).map((a) => a.getAttribute("href")),
                    picture: !!b.querySelector("img.ok"),
                    clobbered: !!document.getElementById("SIAMANG_DESIGN"),
                    banned: Array.from(b.querySelectorAll(
                        "script,style,svg,math,form,input,button,meta,base,link,object,embed,textarea"))
                        .map((el) => el.tagName),
                };
            })(),
            stylesheets: Array.from(document.styleSheets).map((s) => s.href),
        }));
        // Every link left in the body is clicked: none runs anything.
        await page.evaluate(() => document.querySelectorAll(".sd-page__body a").forEach((a) => {
            a.addEventListener("click", (e) => e.preventDefault()); a.click(); }));
        await page.getByText("""
        + json.dumps(TEXT_PAYLOADS[4])
        + """, { exact: true }).click();
    """
        + _NEXT_JS
        + """
        await page.waitForTimeout(800);
        const after = await page.evaluate(() => ({
            pwned: window.__pwned ?? null,
            href: location.href,
            heading: (document.querySelector(".sd-page__title, .sd-completedpage__title") || {}).textContent,
        }));
        return { before, after };
    """
    )
    outcome = run_served(out, scenario, tmp_path)
    assert outcome["dialogs"] == []
    before, after = outcome["result"]["before"], outcome["result"]["after"]
    assert before["pwned"] is None and after["pwned"] is None
    # No <meta refresh> and no <base> took over the page.
    assert before["href"].endswith("/index.html") and after["href"] == before["href"]
    assert after["heading"] == TEXT_PAYLOADS[0]  # the final page, its title as written
    assert before["base"] == before["href"]
    # The texts are shown as written.
    assert before["title"] == TEXT_PAYLOADS[2]
    assert before["next"] == TEXT_PAYLOADS[0]
    body = before["body"]
    assert body["bold"] == "this" and body["picture"] is True
    assert body["handlers"] == [] and body["banned"] == [] and body["clobbered"] is False
    assert all(link.startswith(("https://", "mailto:", "tel:", "#")) for link in body["links"])
    # The YouTube player stays, on the privacy-enhanced host, with the
    # referrer its player needs; the other frames are gone.
    assert body["frames"] == [
        [
            "https://www.youtube-nocookie.com/embed/aBcDeFgHiJ0",
            "strict-origin-when-cross-origin",
            False,
        ]
    ]
    # No stylesheet but the survey's own.
    assert all(href and "/style." in href for href in before["stylesheets"])


def test_the_runtime_takes_out_of_a_body_what_could_run_however_it_got_there(tmp_path):
    """The last line, on HTML that did not come through the compiler: the
    runtime's cleanBodyFragment, read as the browser reads it. On the
    compiler's output it changes nothing."""

    out = build_bundle(_hostile_document(), tmp_path / "bundle")
    scenario = (
        """
        const result = await page.evaluate(([payloads, legit]) => {
            const box = document.createElement("div");
            document.body.appendChild(box);
            const handlers = [];
            for (const html of payloads) {
                const holder = document.createElement("div");
                holder.appendChild(cleanBodyFragment(html));
                box.appendChild(holder);
                for (const el of holder.querySelectorAll("*")) {
                    for (const a of el.attributes) if (a.name.startsWith("on") || a.name === "srcdoc") handlers.push(a.name);
                }
            }
            const kept = legit.map((html) => {
                const t = document.createElement("template");
                t.innerHTML = html;
                const holder = document.createElement("div");
                holder.appendChild(cleanBodyFragment(html));
                return holder.innerHTML === t.innerHTML;
            });
            const hrefs = Array.from(box.querySelectorAll("[href],[src]")).map((el) =>
                el.getAttribute("href") || el.getAttribute("src"));
            return { handlers, kept, hrefs,
                     tags: Array.from(box.querySelectorAll("script,svg,math,iframe,object,embed,form,meta,base,link,style"))
                        .map((el) => el.tagName) };
        }, ["""
        + json.dumps(BODY_PAYLOADS)
        + ", "
        + json.dumps(list(LEGITIMATE))
        + """]);
        await page.waitForTimeout(800);
        result.pwned = await page.evaluate(() => window.__pwned ?? null);
        return result;
    """
    )
    outcome = run_served(out, scenario, tmp_path)
    result = outcome["result"]
    assert result["pwned"] is None and outcome["dialogs"] == []
    assert result["handlers"] == [] and result["tags"] == []
    assert not [
        h
        for h in result["hrefs"]
        if h.strip().lower().startswith(("javascript", "vbscript", "data:text"))
    ]
    assert all(result["kept"]), result["kept"]


# ── The addresses a respondent is sent to ────────────────────────────────────


@pytest.mark.parametrize(
    ("template", "search", "expected"),
    [
        ("javascript:window.__pwned=1", "", None),
        (" JaVaScRiPt:window.__pwned=1", "", None),
        ("java\tscript:window.__pwned=1", "", None),
        ("data:text/html,x", "", None),
        ("{url:to}", "?to=javascript:alert(1)", None),
        ("java{url:s}script:alert(1)", "?s=", None),
        ("https:///evil.example", "", None),
        (
            "https://panel.example/done?id={url:pid}",
            "?pid=a%26b%3Ac",
            "https://panel.example/done?id=a%26b%3Ac",
        ),
        (
            "https://panel.example/{url:pid}",
            "?pid=javascript:alert(1)",
            "https://panel.example/javascript%3Aalert(1)",
        ),
        ("  https://panel.example/ok\n", "", "https://panel.example/ok"),
    ],
)
def test_a_redirect_goes_only_to_an_http_address(template, search, expected):
    """The runtime's last check before location.href, whatever the compiler
    sent (it sends only http(s) addresses) and whatever a link carried."""

    # The Node context has no URLSearchParams of its own (a browser has).
    result = run_js(
        f"""(() => {{
          globalThis.URLSearchParams = class {{
            constructor(query) {{
              this.values = {{}};
              for (const pair of query.replace(/^\\?/, "").split("&")) {{
                if (!pair) continue;
                const [key, value = ""] = pair.split("=");
                this.values[decodeURIComponent(key)] = decodeURIComponent(value);
              }}
            }}
            get(key) {{ return key in this.values ? this.values[key] : null; }}
          }};
          window.location.search = {json.dumps(search)};
          return {{ redirect: redirectTemplate({json.dumps(template)}, {{}}),
                    privacy: safeNavigationUrl({json.dumps(template)}) }};
        }})()"""
    )
    assert result["redirect"] == expected
    if "{" not in template:
        assert result["privacy"] == expected


# ── Under a policy ───────────────────────────────────────────────────────────


def _logic_document() -> dict[str, Any]:
    yes = _cmp("=", _var("q1"), 1)
    return {
        "schema_version": "1.0",
        "title": "Logic",
        "variables": {
            "q1": {
                "scale": "nominal",
                "labels": [{"code": 1, "label": "Yes"}, {"code": 2, "label": "No"}],
            },
            "q2": {"scale": "nominal", "dtype": "str"},
            "q3": {"scale": "nominal", "dtype": "str"},
            "q4": {"scale": "nominal", "dtype": "str"},
            "q5": {"scale": "nominal", "dtype": "str"},
        },
        "pages": [
            {
                "name": "p1",
                "title": "One",
                "body": '<p style="color: #335577">Styled</p>' + _PLAYER,
                "items": [
                    {"type": "SingleChoice", "id": "q1", "var": "q1", "text": "Agree?"},
                    {
                        "type": "OpenText",
                        "id": "q2",
                        "var": "q2",
                        "text": "Shown on yes",
                        "show_if": yes,
                    },
                    {
                        "type": "OpenText",
                        "id": "q3",
                        "var": "q3",
                        "text": "Hidden on yes",
                        "hide_if": yes,
                    },
                ],
                "next_if": [{"condition": _cmp("=", _var("q1"), 2), "target": "p3"}],
            },
            {
                "name": "p2",
                "title": "Two",
                "items": [{"type": "OpenText", "id": "q4", "var": "q4", "text": "On two"}],
            },
            {
                "name": "p3",
                "title": "Three",
                "items": [{"type": "OpenText", "id": "q5", "var": "q5", "text": "On three"}],
            },
            {"name": "done", "kind": "final", "title": "Thanks"},
        ],
    }


_PLAY_LOGIC = (
    """
    const titles = () => page.$$eval(".sd-question__title", (ts) => ts.map((t) =>
        Array.from(t.querySelectorAll("span")).filter((s) => !/sd-question__(num|required)/.test(s.className))
            .map((s) => s.textContent).join("")));
    const start = await titles();
    const look = await page.evaluate(() => ({
        font: getComputedStyle(document.body).fontFamily,
        styled: getComputedStyle(document.querySelector(".sd-page__body p[style]")).color,
        player: document.querySelector(".sd-page__body iframe").getAttribute("src"),
    }));
    await page.click("text=Yes");
    await page.waitForTimeout(200);
    const onYes = await titles();
    await page.click("text=No");
    await page.waitForTimeout(200);
    const onNo = await titles();
"""
    + _NEXT_JS
    + """
    const next = await page.textContent(".sd-page__title");
    // A handler that got into the page anyway (it cannot through the body).
    await page.evaluate(() => document.body.insertAdjacentHTML("beforeend",
        '<img src="data:," onerror="window.__pwned = 1">'));
    await page.waitForTimeout(500);
    const after = await page.evaluate(() => ({ pwned: window.__pwned ?? null, csp: window.__csp }));
    return { start, onYes, onNo, next, look, after };
"""
)


def _with_policy(tmp_path: Path, *, eval_allowed: bool) -> dict[str, Any]:
    out = build_bundle(_logic_document(), tmp_path / "bundle")
    index = out / "index.html"
    page = index.read_text("utf-8")
    policy = survey_csp(page)
    if not eval_allowed:
        policy = policy.replace(" 'unsafe-eval'", "")
    index.write_text(insert_csp_meta(page, policy), "utf-8")
    return run_served(out, _PLAY_LOGIC, tmp_path)


def test_the_runtime_works_under_the_policy_it_needs_and_nothing_inline_runs(tmp_path):
    outcome = _with_policy(tmp_path, eval_allowed=True)
    assert outcome["errors"] == []
    result = outcome["result"]
    shown_on_yes, hidden_on_yes = "Shown on yes", "Hidden on yes"
    assert result["start"] == ["Agree?", hidden_on_yes]
    assert result["onYes"] == ["Agree?", shown_on_yes]
    assert result["onNo"] == ["Agree?", hidden_on_yes]
    assert result["next"] == "Three"  # "No" routes past page two
    # The stylesheet, the bundled typeface, a body's style="" and the player.
    assert result["look"] == {
        "font": '"Source Serif 4", Charter, Georgia, "Times New Roman", serif',
        "styled": "rgb(51, 85, 119)",
        "player": "https://www.youtube-nocookie.com/embed/aBcDeFgHiJ0",
    }
    # The inline handler did not run; the policy says so, and that is all it
    # ever had to block.
    assert result["after"]["pwned"] is None
    assert result["after"]["csp"] == ["script-src-attr inline"]


def test_without_unsafe_eval_every_condition_reads_as_true(tmp_path):
    """Why the policy keeps 'unsafe-eval': conditions are compiled with new
    Function. Without it a show_if always shows, a hide_if always hides and
    the first routing rule is always taken."""

    result = _with_policy(tmp_path, eval_allowed=False)["result"]
    assert result["start"] == ["Agree?", "Shown on yes"]
    assert result["onYes"] == result["onNo"] == ["Agree?", "Shown on yes"]
    assert any(
        entry.startswith("script-src") and "eval" in entry for entry in result["after"]["csp"]
    )
