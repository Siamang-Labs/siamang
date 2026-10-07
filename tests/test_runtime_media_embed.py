"""In Chromium: a YouTube or Vimeo video waits for the respondent's press.

A question's or an option's video (media of kind ``embed``) and, with the
host's ``click_to_play``, a page body's player are a play button until it is
pressed: nothing is requested from YouTube or Vimeo before. The bundle is
served over HTTP from its own origin, as a survey host serves it; every
request to another origin is recorded and refused, so a test reads what the
page asked for and when. ``test_media_embed.py`` checks what the engine
writes; these play it.
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

from siamang.core.media import PLAYER_ALLOW
from siamang.frontend import ClientEnv, FrontendBuilder, ReactRuntime, UIConfig
from siamang.frontend.compiler import compile_questionnaire
from siamang.frontend.csp import insert_csp_meta, media_sources, survey_csp
from siamang.model import from_document

from .test_runtime_browser import _node, _QuietHandler, _RecordingClient

# Opens `page` (a path under the served bundle) at `viewport`, with `init` run
# first in every document and frame, plays `scenario` (the body of an async
# function of `page` and `foreign`, the list of other origins' requests so
# far), and reports what it returned, the page's errors and every request
# made to another origin.
_HARNESS = r"""
const [url, scenarioFile, initFile, viewportJson] = process.argv.slice(2);
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
  const foreign = [];
  try {
    const page = await browser.newPage({ viewport: JSON.parse(viewportJson) });
    page.on("pageerror", (e) => errors.push(e.message));
    const origin = new URL(url).origin;
    await page.route(/.*/, (route) => {
      const asked = route.request().url();
      if (new URL(asked).origin === origin) return route.continue();
      foreign.push(asked);
      return route.abort();
    });
    await page.addInitScript(
      "window.__csp = [];" +
      "document.addEventListener('securitypolicyviolation', (e) => window.__csp.push(e.effectiveDirective + ' ' + e.blockedURI));" +
      "window.__posted = [];" +
      "window.addEventListener('message', (e) => { if (e.data && e.data.type) window.__posted.push(e.data); });" +
      fs.readFileSync(initFile, "utf8"));
    await page.goto(url);
    await page.waitForSelector(".sd-page", { timeout: 15000 }).catch(() => {});
    const scenario = new Function("page", "foreign", "return (async () => {" +
      fs.readFileSync(scenarioFile, "utf8") + "})();");
    const result = await scenario(page, foreign);
    console.log(JSON.stringify({ result, errors, foreign }));
  } finally {
    await browser.close();
  }
})().catch((e) => { console.log(JSON.stringify({ error: String((e && e.stack) || e), errors: [], foreign: [] })); });
"""

YOUTUBE = "aBcDeFgHiJ0"
VIMEO = "123456789"
VIMEO_KEY = "abcdef1234"
PROVIDERS = ("youtube-nocookie.com", "youtube.com", "ytimg.com", "vimeo.com", "vimeocdn.com")


def _build(document: dict[str, Any], out: Path, **builder: Any) -> Path:
    loaded = from_document(document)
    options = dict(loaded.options)
    ui = options.pop("ui", None) or UIConfig()
    schema = compile_questionnaire(loaded.survey, options=options)
    env = ClientEnv(survey_id="t", backend="test", settings={})
    bundle = FrontendBuilder(ui=ui, runtime=ReactRuntime(), **builder).build(
        schema, client=_RecordingClient(), env=env, survey=loaded.survey
    )
    return bundle.write_to(out)


def _play(
    out: Path,
    scenario: str,
    tmp_path: Path,
    *,
    init: str = "",
    page: str = "index.html",
    viewport: tuple[int, int] = (1000, 900),
) -> dict[str, Any]:
    """Serve ``out``, open ``page`` and play ``scenario``; the outcome has
    ``result``, ``errors`` and ``foreign`` (every request to another origin)."""

    node = _node()
    handler = functools.partial(_QuietHandler, directory=str(out))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    harness = tmp_path / "embed.cjs"
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
                f"http://127.0.0.1:{server.server_address[1]}/{page}",
                str(scenario_file),
                str(init_file),
                json.dumps({"width": viewport[0], "height": viewport[1]}),
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


def _to_providers(requests: list[str]) -> list[str]:
    return [url for url in requests if any(host in url for host in PROVIDERS)]


def _youtube(**extra: Any) -> dict[str, Any]:
    return {
        "kind": "embed",
        "provider": "youtube",
        "id": YOUTUBE,
        # What the author pasted: never what the player is built from.
        "url": "https://videos.example/watch?v=other&autoplay=1",
        **extra,
    }


def _vimeo(**extra: Any) -> dict[str, Any]:
    return {
        "kind": "embed",
        "provider": "vimeo",
        "id": VIMEO,
        "key": VIMEO_KEY,
        "url": "x",
        **extra,
    }


def _document(
    *,
    media: Any = None,
    choices: list[dict[str, Any]] | None = None,
    multi: list[dict[str, Any]] | None = None,
    body: str | None = None,
    ui: dict[str, Any] | None = None,
    intro: bool = False,
) -> dict[str, Any]:
    labels = [{"code": 1, "label": "Bees"}, {"code": 2, "label": "Wasps"}]
    items: list[dict[str, Any]] = [
        {"type": "SingleChoice", "id": "q", "var": "q", "text": "Which one?", "choices": choices}
        if choices
        else {"type": "SingleChoice", "id": "q", "var": "q", "text": "Which one?"}
    ]
    if media is not None:
        items[0]["media"] = media
    if multi:
        items.append(
            {"type": "MultiChoice", "id": "m", "var": "m", "text": "Which ones?", "choices": multi}
        )
    page: dict[str, Any] = {"name": "p1", "title": "Watch", "items": items}
    if body is not None:
        page["body"] = body
    pages = [page, {"name": "done", "kind": "final", "title": "Thanks"}]
    if intro:
        pages.insert(0, {"name": "intro", "title": "Hello", "body": "<p>Welcome.</p>"})
    document: dict[str, Any] = {
        "schema_version": "1.0",
        "title": "Videos",
        "variables": {
            "q": {"scale": "nominal", "labels": labels},
            "m": {"scale": "nominal", "labels": labels},
        },
        "pages": pages,
    }
    if ui:
        document["ui"] = ui
    return document


def _option(code: int, label: str, media: dict[str, Any] | None) -> dict[str, Any]:
    option: dict[str, Any] = {"code": code, "label": label}
    if media is not None:
        option["media"] = media
    return option


# ── A question's video ───────────────────────────────────────────────────────

_FACADE = """
    const facade = (root) => {
        const b = (root || document).querySelector(".siamang-embed__facade");
        if (!b) return null;
        const described = (b.getAttribute("aria-describedby") || "").split(" ")
            .map((id) => document.getElementById(id)).filter(Boolean)
            .map((el) => el.textContent).join(" ");
        const box = b.closest(".siamang-embed").getBoundingClientRect();
        return { tag: b.tagName, type: b.getAttribute("type"), name: b.getAttribute("aria-label"),
                 description: described, text: b.textContent, width: box.width, height: box.height };
    };
    const frames = () => Array.from(document.querySelectorAll("iframe")).map((f) => ({
        src: f.getAttribute("src"), allow: f.getAttribute("allow"), title: f.getAttribute("title"),
        fullscreen: f.hasAttribute("allowfullscreen"), referrer: f.getAttribute("referrerpolicy"),
        sandbox: f.hasAttribute("sandbox"), focused: document.activeElement === f }));
"""


def test_a_question_video_is_a_named_button_and_nothing_loads_before_it_is_pressed(tmp_path):
    out = _build(_document(media=[_youtube(start=62, alt="Bees at work")]), tmp_path / "b")
    outcome = _play(
        out,
        """
        await page.waitForTimeout(1200);
        const before = await page.evaluate(() => { """
        + _FACADE
        + """ return { facade: facade(), frames: frames() }; });
        const asked = foreign.length;
        // From the keyboard: the button takes the focus and Enter presses it
        // (it is not Next: the page stays).
        await page.focus(".siamang-embed__facade");
        await page.keyboard.press("Enter");
        await page.waitForTimeout(400);
        const after = await page.evaluate(() => { """
        + _FACADE
        + """ return { facade: facade(), frames: frames(),
                     title: document.querySelector(".sd-page__title").textContent }; });
        return { before, asked, after };
        """,
        tmp_path,
    )
    assert outcome["errors"] == []
    result = outcome["result"]
    before, after = result["before"], result["after"]
    # Before the press: a button, named after the video, that says where it
    # plays from; no frame, and not one request to another origin.
    assert before["frames"] == []
    assert result["asked"] == 0
    assert before["facade"]["tag"] == "BUTTON" and before["facade"]["type"] == "button"
    assert before["facade"]["name"] == "Play video: Bees at work"
    assert before["facade"]["description"] == "Plays from YouTube when you press play"
    assert "Bees at work" in before["facade"]["text"]
    # Pressed: the player, built from the provider and the id (not from the
    # author's url), with the provider's own allow list, and the focus on it.
    assert after["facade"] is None and after["title"] == "Watch"
    assert after["frames"] == [
        {
            "src": f"https://www.youtube-nocookie.com/embed/{YOUTUBE}"
            "?autoplay=1&rel=0&playsinline=1&start=62",
            "allow": PLAYER_ALLOW["youtube"],
            "title": "Bees at work",
            "fullscreen": True,
            "referrer": "strict-origin-when-cross-origin",
            "sandbox": False,
            "focused": True,
        }
    ]
    assert _to_providers(outcome["foreign"]) == [after["frames"][0]["src"]]
    assert not [url for url in outcome["foreign"] if "videos.example" in url]


def test_without_alt_text_the_button_is_named_after_the_question(tmp_path):
    out = _build(_document(media=_vimeo()), tmp_path / "b")
    outcome = _play(
        out,
        """
        await page.waitForTimeout(800);
        const before = await page.evaluate(() => { """
        + _FACADE
        + """ return facade(); });
        await page.click(".siamang-embed__facade");
        await page.waitForTimeout(300);
        const after = await page.evaluate(() => { """
        + _FACADE
        + """ return frames(); });
        return { before, after };
        """,
        tmp_path,
    )
    result = outcome["result"]
    assert result["before"]["name"] == "Play video: Which one?"
    assert result["before"]["description"] == "Plays from Vimeo when you press play"
    assert [frame["src"] for frame in result["after"]] == [
        f"https://player.vimeo.com/video/{VIMEO}?h={VIMEO_KEY}&dnt=1&autoplay=1"
    ]
    assert result["after"][0]["allow"] == PLAYER_ALLOW["vimeo"]
    assert result["after"][0]["title"] == "Vimeo video"


def test_the_runtime_checks_a_video_again_before_it_builds_a_player(tmp_path):
    """A payload whose video is not one (an id that is not an id, a provider
    the runtime does not know) shows nothing: no button, no frame."""

    out = _build(_document(media=_youtube()), tmp_path / "b")
    outcome = _play(
        out,
        """
        await page.waitForTimeout(500);
        return await page.evaluate(() => ({
            bad: [
                embedOf({ kind: "embed", provider: "youtube", id: 'aBcDeFgHiJ"' }),
                embedOf({ kind: "embed", provider: "youtube", id: "aBcDeFgHiJ0/../x" }),
                embedOf({ kind: "embed", provider: "__proto__", id: "aBcDeFgHiJ0" }),
                embedOf({ kind: "embed", provider: "constructor", id: "aBcDeFgHiJ0" }),
                embedOf({ kind: "embed", provider: "dailymotion", id: "x8abc" }),
                embedOf({ kind: "embed", provider: "vimeo", id: "1", key: "NOTHEX" }),
                embedOf({ kind: "embed", provider: "vimeo", id: "12a" }),
                embedOf({ kind: "image", provider: "youtube", id: "aBcDeFgHiJ0" }),
            ],
            good: embedOf({ kind: "embed", provider: "youtube", id: "aBcDeFgHiJ0", start: 99999,
                            url: "javascript:alert(1)" }),
        }));
        """,
        tmp_path,
        # The payload is tampered with before the runtime reads it.
        init="""
        Object.defineProperty(window, "PAGES", { configurable: true,
            get() { return this.__pages; },
            set(value) { value[0].items[0].media[0].id = "x\\" onload=\\"alert(1)"; this.__pages = value; } });
        """,
    )
    result = outcome["result"]
    assert result["bad"] == [None] * 8
    # A start out of range is dropped; the address is the provider's own.
    assert result["good"]["src"] == (
        f"https://www.youtube-nocookie.com/embed/{YOUTUBE}?autoplay=1&rel=0&playsinline=1"
    )
    assert _to_providers(outcome["foreign"]) == []


# ── An option's video ────────────────────────────────────────────────────────

_ROWS = """
    const rows = () => ({
        radios: Array.from(document.querySelectorAll("input[type=radio]")).map((r) => ({
            checked: r.checked, label: r.labels[0].textContent })),
        boxes: Array.from(document.querySelectorAll("input[type=checkbox]")).map((r) => r.checked),
        buttons: Array.from(document.querySelectorAll(".sd-choice-play")).map((b) => ({
            name: b.getAttribute("aria-label"), inLabel: !!b.closest("label"),
            row: b.parentElement.className })),
        dialogs: Array.from(document.querySelectorAll("dialog")).map((d) => ({
            open: d.open, name: d.getAttribute("aria-label"),
            frames: Array.from(d.querySelectorAll("iframe")).map((f) => [f.getAttribute("src"),
                f.getAttribute("allow"), f.getAttribute("referrerpolicy"), f.hasAttribute("allowfullscreen")]),
            box: (() => { const b = d.querySelector(".siamang-embed"); if (!b) return null;
                const r = b.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; })(),
            close: (d.querySelector(".siamang-player-dialog__close") || {}).textContent })),
        focus: document.activeElement ? (document.activeElement.getAttribute("aria-label")
            || document.activeElement.textContent) : null,
        page: (document.querySelector(".sd-page__title") || {}).textContent,
    });
"""


def test_an_options_video_plays_in_a_window_and_never_chooses_the_option(tmp_path):
    document = _document(
        choices=[_option(1, "Bees", _vimeo()), _option(2, "Wasps", _youtube(alt="Wasp nest"))],
        multi=[_option(1, "Bees", _youtube()), _option(2, "Wasps", None)],
        intro=True,
    )
    out = _build(document, tmp_path / "b")
    outcome = _play(
        out,
        """
        await page.click(".sd-navigation__next-btn");
        await page.waitForSelector(".sd-choice-play");
        await page.waitForTimeout(600);
        const read = () => page.evaluate(() => { """
        + _ROWS
        + """ return rows(); });
        const start = await read();
        const asked = foreign.length;
        const named = await page.getByRole("radio", { name: "Bees", exact: true }).count();
        await page.click(".sd-choice-play >> nth=0");
        await page.waitForTimeout(300);
        const open = await read();
        // Escape closes the window, and does not go back a page.
        await page.keyboard.press("Escape");
        await page.waitForTimeout(300);
        const escaped = await read();
        await page.click(".sd-choice-play >> nth=0");
        await page.waitForTimeout(200);
        await page.click(".siamang-player-dialog__close");
        await page.waitForTimeout(300);
        const closed = await read();
        // One player at a time: the second opens, the first is gone.
        await page.click(".sd-choice-play >> nth=0");
        await page.waitForTimeout(200);
        await page.evaluate(() => document.querySelectorAll(".sd-choice-play")[1].click());
        await page.waitForTimeout(300);
        const second = await read();
        await page.keyboard.press("Escape");
        await page.waitForTimeout(200);
        // A checkbox option's Play leaves the box as it was.
        await page.click(".sd-choice-play >> nth=2");
        await page.waitForTimeout(200);
        const multi = await read();
        return { start, asked, named, open, escaped, closed, second, multi };
        """,
        tmp_path,
    )
    assert outcome["errors"] == []
    result = outcome["result"]
    start = result["start"]
    # Nothing asked of either provider before a press.
    assert result["asked"] == 0
    # The Play buttons sit beside the options, outside their labels: the
    # radio is still named after its option alone.
    assert result["named"] == 1
    assert [r["label"] for r in start["radios"]] == ["Bees", "Wasps"]
    assert start["buttons"] == [
        {"name": "Play video: Bees", "inLabel": False, "row": "sd-choice-row"},
        {"name": "Play video: Wasps", "inLabel": False, "row": "sd-choice-row"},
        {"name": "Play video: Bees", "inLabel": False, "row": "sd-choice-row"},
    ]
    open_ = result["open"]
    assert [r["checked"] for r in open_["radios"]] == [False, False]
    assert len(open_["dialogs"]) == 1
    dialog = open_["dialogs"][0]
    # Named as the button that opened it: a screen reader hears it holds a video.
    assert dialog["open"] and dialog["name"] == "Play video: Bees" and dialog["close"] == "Close"
    assert dialog["frames"] == [
        [
            f"https://player.vimeo.com/video/{VIMEO}?h={VIMEO_KEY}&dnt=1&autoplay=1",
            PLAYER_ALLOW["vimeo"],
            "strict-origin-when-cross-origin",
            True,
        ]
    ]
    assert dialog["box"][0] >= 200 and dialog["box"][1] >= 200
    assert open_["focus"] == "Close"  # the window has the focus
    # Escape: the window and its player are gone, the focus is back on Play,
    # and the respondent is still on the page.
    escaped = result["escaped"]
    assert escaped["dialogs"] == [] and escaped["page"] == "Watch"
    assert escaped["focus"] == "Play video: Bees"
    closed = result["closed"]
    assert closed["dialogs"] == [] and closed["focus"] == "Play video: Bees"
    assert [r["checked"] for r in closed["radios"]] == [False, False]
    second = result["second"]
    assert len(second["dialogs"]) == 1
    assert second["dialogs"][0]["name"] == "Play video: Wasp nest"
    assert second["dialogs"][0]["frames"][0][0].startswith(
        f"https://www.youtube-nocookie.com/embed/{YOUTUBE}?"
    )
    multi = result["multi"]
    assert multi["boxes"] == [False, False] and len(multi["dialogs"]) == 1


# ── Room to play ─────────────────────────────────────────────────────────────


def test_on_a_phone_every_player_keeps_200_px_each_way(tmp_path):
    document = _document(
        media=[_youtube(alt="Wide"), _youtube(aspect="9:16", alt="Tall")],
        choices=[_option(1, "Bees", _youtube()), _option(2, "Wasps", None)],
    )
    out = _build(document, tmp_path / "b")
    outcome = _play(
        out,
        """
        await page.waitForTimeout(800);
        const boxes = await page.evaluate(() => Array.from(document.querySelectorAll(
            ".sd-question__header .siamang-embed")).map((b) => {
                const r = b.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; }));
        await page.click(".siamang-embed__facade >> nth=0");
        await page.waitForTimeout(300);
        const player = await page.evaluate(() => { const r = document.querySelector(
            ".sd-question__header iframe").getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; });
        await page.click(".sd-choice-play");
        await page.waitForTimeout(300);
        const dialog = await page.evaluate(() => { const r = document.querySelector(
            "dialog iframe").getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; });
        const scroll = await page.evaluate(() => document.documentElement.scrollWidth);
        return { boxes, player, dialog, scroll };
        """,
        tmp_path,
        viewport=(320, 640),
    )
    result = outcome["result"]
    wide, tall = result["boxes"]
    # 16:9 would be under 200 px tall at this width; 200 is the least.
    assert wide[0] >= 200 and wide[1] >= 200 and wide[0] <= 320
    assert tall[0] >= 200 and tall[1] >= 356 and tall[1] > tall[0]
    assert result["player"] == wide
    assert result["dialog"][0] >= 200 and result["dialog"][1] >= 200
    assert result["dialog"][0] <= 320 - 32
    assert result["scroll"] <= 320


# Relative luminance contrast of two computed colors (rgb() or color(srgb …)).
_CONTRAST = """
    // Any CSS color (rgb(), color(srgb …), oklab() …) as sRGB, through a canvas.
    const paint = document.createElement("canvas").getContext("2d", { willReadFrequently: true });
    const channels = (text) => {
        paint.clearRect(0, 0, 1, 1);
        paint.fillStyle = "#000";
        paint.fillStyle = text;
        paint.fillRect(0, 0, 1, 1);
        return Array.from(paint.getImageData(0, 0, 1, 1).data.slice(0, 3)).map((v) => v / 255);
    };
    const luminance = (text) => {
        const [r, g, b] = channels(text).map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
        return 0.2126 * r + 0.7152 * g + 0.0722 * b;
    };
    const contrast = (a, b) => {
        const [x, y] = [luminance(a), luminance(b)].sort((p, q) => q - p);
        return (x + 0.05) / (y + 0.05);
    };
"""


def test_in_the_dark_theme_a_play_button_keeps_3_to_1(tmp_path):
    document = _document(media=_youtube(alt="Hive"), choices=[_option(1, "Bees", _vimeo())])
    out = _build(document, tmp_path / "b")
    outcome = _play(
        out,
        """
        await page.waitForSelector(".sd-choice-play");
        await page.waitForTimeout(400);
        const read = () => page.evaluate(() => { """
        + _CONTRAST
        + """
            const play = getComputedStyle(document.querySelector(".sd-choice-play"));
            const glyph = getComputedStyle(document.querySelector(".siamang-embed__glyph"));
            const facade = getComputedStyle(document.querySelector(".siamang-embed__facade"));
            return {
                glyph: contrast(play.color, play.backgroundColor),
                ring: contrast(play.borderTopColor, play.backgroundColor),
                circle: contrast(glyph.backgroundColor, facade.backgroundColor),
            };
        });
        const light = await read();
        await page.evaluate(() => document.documentElement.setAttribute("data-theme", "dark"));
        await page.waitForTimeout(400);  // the colors' transitions
        const dark = await read();
        return { light, dark };
        """,
        tmp_path,
    )
    assert outcome["errors"] == []
    for theme in ("light", "dark"):
        values = outcome["result"][theme]
        assert values["glyph"] >= 3 and values["circle"] >= 3, (theme, values)
    assert outcome["result"]["dark"]["ring"] >= 3, outcome["result"]["dark"]


def test_with_buttons_an_options_video_keeps_the_lists_width(tmp_path):
    document = _document(choices=[_option(1, "Bees", _vimeo()), _option(2, "Wasps", None)])
    document["pages"][0]["items"][0]["display"] = "buttons"
    out = _build(document, tmp_path / "b")
    outcome = _play(
        out,
        """
        await page.waitForSelector(".sd-choice-play");
        return await page.evaluate(() => {
            const width = (el) => Math.round(el.getBoundingClientRect().width);
            const row = document.querySelector(".sd-choice-row");
            const plain = Array.from(document.querySelectorAll(".sd-choices--buttons > .sd-radio"));
            return { row: width(row), radio: width(row.querySelector(".sd-radio")),
                     play: width(row.querySelector(".sd-choice-play")), plain: plain.map(width) };
        });
        """,
        tmp_path,
        viewport=(1280, 900),
    )
    assert outcome["errors"] == []
    result = outcome["result"]
    # The option with a video is a bar as wide as the others, less its Play
    # button and the gap: not a pill of its label's width.
    assert result["plain"] and result["row"] == result["plain"][0]
    assert result["radio"] >= result["row"] - result["play"] - 12


def test_a_play_box_tints_on_hover_only_where_there_is_hover():
    # On a touch screen the last tap keeps :hover: the play box that lands
    # under the finger after Next stayed tinted.
    css = (
        Path(__file__).resolve().parents[1] / "siamang/frontend/templates/react/style.css.tpl"
    ).read_text(encoding="utf-8")
    start = css.index("@media (hover: hover)")
    block = css[start : css.index("\n}\n", start)]
    reduced = css.index("@media (prefers-reduced-motion: reduce) {\n  .siamang-embed__facade")
    outside = css.replace(block, "").replace(css[reduced : css.index("\n}\n", reduced)], "")
    for rule in (
        ".siamang-embed__facade:hover {",
        ".siamang-embed__facade:hover .siamang-embed__glyph {",
        ".sd-choice-play:hover {",
    ):
        assert rule in block and rule not in outside, rule


# ── A page body's players ────────────────────────────────────────────────────

_BODY = (
    "<p>Watch this first.</p>"
    f'<iframe width="560" height="315" src="https://www.youtube.com/embed/{YOUTUBE}?start=42" '
    'title="Hive tour"></iframe>'
    f'<iframe src="https://vimeo.com/{VIMEO}/{VIMEO_KEY}"></iframe>'
    # An author's look-alike of a play button: not one.
    f'<div class="siamang-embed" data-src="https://www.youtube-nocookie.com/embed/{YOUTUBE}">'
    '<span class="siamang-embed__facade" id="fake">Press</span></div>'
)


def test_with_click_to_play_a_bodys_players_wait_for_a_press(tmp_path):
    out = _build(_document(body=_BODY), tmp_path / "b", click_to_play=True)
    outcome = _play(
        out,
        """
        await page.waitForTimeout(1200);
        const read = () => page.evaluate(() => { """
        + _FACADE
        + """ const body = document.querySelector(".sd-page__body");
            return { frames: frames(),
                facades: Array.from(body.querySelectorAll("button.siamang-embed__facade")).map((b) => ({
                    name: b.getAttribute("aria-label"), text: b.textContent,
                    ratio: b.parentElement.style.aspectRatio })) }; });
        const before = await read();
        const asked = foreign.length;
        await page.click("#fake");
        await page.waitForTimeout(300);
        const fake = await read();
        await page.click(".sd-page__body button.siamang-embed__facade >> nth=0");
        await page.waitForTimeout(300);
        const first = await read();
        const focused = await page.evaluate(() => document.activeElement.tagName);
        await page.click(".sd-page__body button.siamang-embed__facade");
        await page.waitForTimeout(300);
        const both = await read();
        return { before, asked, fake, first, focused, both };
        """,
        tmp_path,
    )
    assert outcome["errors"] == []
    result = outcome["result"]
    assert result["before"]["frames"] == [] and result["asked"] == 0
    assert result["before"]["facades"] == [
        {
            "name": "Play video: Hive tour",
            "text": "Hive tourPlays from YouTube when you press play",
            "ratio": "560 / 315",
        },
        # An untitled player: the sanitizer's "Vimeo video player" is not the
        # author's title, so the box shows none and is named as a question's
        # video is.
        {
            "name": "Play video: Vimeo video",
            "text": "Plays from Vimeo when you press play",
            "ratio": "",
        },
    ]
    # The look-alike does nothing.
    assert result["fake"]["frames"] == []
    first = result["first"]["frames"]
    assert first == [
        {
            "src": f"https://www.youtube-nocookie.com/embed/{YOUTUBE}?start=42&autoplay=1",
            "allow": PLAYER_ALLOW["youtube"],
            "title": "Hive tour",
            "fullscreen": True,
            "referrer": "strict-origin-when-cross-origin",
            "sandbox": False,
            "focused": True,
        }
    ]
    assert result["focused"] == "IFRAME"
    assert [frame["src"] for frame in result["both"]["frames"]] == [
        first[0]["src"],
        f"https://player.vimeo.com/video/{VIMEO}?h={VIMEO_KEY}&autoplay=1&dnt=1",
    ]


def test_a_body_vimeo_player_loads_with_dnt_1_alone(tmp_path):
    # The sanitizer keeps a Vimeo player's dnt, repeats included; the press
    # sets it to 1 and drops the repeats (dnt=1&dnt=0 would leave the choice
    # to Vimeo).
    body = (
        f'<iframe src="https://player.vimeo.com/video/{VIMEO}?h={VIMEO_KEY}&amp;dnt=0&amp;dnt=0'
        '#t=5s" title="Clip"></iframe>'
    )
    out = _build(_document(body=body), tmp_path / "b", click_to_play=True)
    outcome = _play(
        out,
        """
        await page.waitForTimeout(1000);
        await page.click(".sd-page__body button.siamang-embed__facade");
        await page.waitForTimeout(300);
        return await page.evaluate(() =>
            Array.from(document.querySelectorAll("iframe")).map((f) => f.getAttribute("src")));
        """,
        tmp_path,
    )
    assert outcome["errors"] == []
    assert outcome["result"] == [
        f"https://player.vimeo.com/video/{VIMEO}?h={VIMEO_KEY}&dnt=1&autoplay=1#t=5s"
    ]


def test_without_click_to_play_a_bodys_players_are_frames_as_before(tmp_path):
    out = _build(_document(body=_BODY), tmp_path / "b")
    outcome = _play(
        out,
        """
        await page.waitForTimeout(800);
        return await page.evaluate(() => ({
            frames: Array.from(document.querySelectorAll(".sd-page__body iframe")).map((f) => f.getAttribute("src")),
            facades: document.querySelectorAll("button.siamang-embed__facade").length,
            clickToPlay: window.SURVEY.clickToPlay === undefined }));
        """,
        tmp_path,
    )
    result = outcome["result"]
    assert result == {
        "frames": [
            f"https://www.youtube-nocookie.com/embed/{YOUTUBE}?start=42",
            f"https://player.vimeo.com/video/{VIMEO}?h={VIMEO_KEY}",
        ],
        "facades": 0,
        "clickToPlay": True,
    }


# ── Pages that cannot play ───────────────────────────────────────────────────


def test_in_a_design_preview_a_video_says_it_cannot_play_and_tells_the_host(tmp_path):
    document = _document(
        media=_youtube(),
        choices=[_option(1, "Bees", _vimeo()), _option(2, "Wasps", None)],
        body=_BODY,
    )
    out = _build(document, tmp_path / "b", click_to_play=True)
    outcome = _play(
        out,
        """
        await page.waitForTimeout(800);
        await page.click(".sd-question__header .siamang-embed__facade");
        await page.waitForTimeout(300);
        const question = await page.evaluate(() => document.querySelector(
            ".sd-question__header .siamang-embed__note").textContent);
        await page.click(".sd-page__body button.siamang-embed__facade >> nth=0");
        await page.waitForTimeout(300);
        const body = await page.evaluate(() => document.querySelector(
            ".sd-page__body .siamang-embed__note").textContent);
        await page.click(".sd-choice-play");
        await page.waitForTimeout(300);
        const dialog = await page.evaluate(() => document.querySelector("dialog .siamang-embed").textContent);
        return { question, body, dialog,
                 frames: await page.evaluate(() => document.querySelectorAll("iframe").length),
                 posted: await page.evaluate(() => window.__posted.filter((m) => m.type === "siamang:embed-blocked")),
                 opened: await page.evaluate(() => window.__opened) };
        """,
        tmp_path,
        init="window.SIAMANG_DESIGN = { select: false };"
        "window.__opened = []; window.open = (u, t) => { window.__opened.push([u, t]); return {}; };",
    )
    result = outcome["result"]
    blocked = "This preview can't play videos."
    assert result["question"] == result["body"] == result["dialog"] == blocked
    assert result["frames"] == 0 and result["opened"] == []
    assert result["posted"] == [
        {"source": "siamang-runtime", "type": "siamang:embed-blocked", "provider": "youtube"},
        {"source": "siamang-runtime", "type": "siamang:embed-blocked", "provider": "youtube"},
        {"source": "siamang-runtime", "type": "siamang:embed-blocked", "provider": "vimeo"},
    ]
    assert _to_providers(outcome["foreign"]) == []


def test_in_a_sandboxed_page_a_video_opens_on_its_site(tmp_path):
    document = _document(
        media=_youtube(start=62),
        choices=[_option(1, "Bees", _vimeo(start=5)), _option(2, "Wasps", None)],
        body=_BODY,
    )
    out = _build(document, tmp_path / "b", click_to_play=True)
    (out / "sandboxed.html").write_text(
        '<!doctype html><html><head><meta charset="utf-8"></head><body>'
        '<iframe sandbox="allow-scripts allow-popups" src="index.html" '
        'style="width:900px;height:1400px;border:0"></iframe></body></html>',
        encoding="utf-8",
    )
    outcome = _play(
        out,
        """
        await page.waitForTimeout(500);
        const frame = page.frames().find((f) => f.url().endsWith("/index.html"));
        await frame.waitForSelector(".sd-page", { timeout: 15000 });
        await frame.waitForTimeout(500);
        const origin = await frame.evaluate(() => window.origin);
        await frame.click(".sd-question__header .siamang-embed__facade");
        await frame.click(".sd-choice-play");
        await frame.click(".sd-page__body button.siamang-embed__facade >> nth=1");
        await frame.waitForTimeout(300);
        const opened = await frame.evaluate(() => window.__opened);
        const frames = await frame.evaluate(() => document.querySelectorAll("iframe").length);
        const dialogs = await frame.evaluate(() => document.querySelectorAll("dialog").length);
        // A browser that refuses the tab: the box says the video cannot play.
        await frame.evaluate(() => { window.open = () => null; });
        await frame.click(".sd-question__header .siamang-embed__facade");
        await frame.waitForTimeout(200);
        const refused = await frame.evaluate(() => document.querySelector(
            ".sd-question__header .siamang-embed__note").textContent);
        return { origin, opened, frames, dialogs, refused };
        """,
        tmp_path,
        page="sandboxed.html",
        init="window.__opened = []; window.open = (u, t) => { window.__opened.push([u, t]);"
        " return { opener: window }; };",
    )
    result = outcome["result"]
    assert result["origin"] == "null"
    assert result["opened"] == [
        [f"https://www.youtube.com/watch?v={YOUTUBE}&t=62", "_blank"],
        [f"https://vimeo.com/{VIMEO}/{VIMEO_KEY}#t=5s", "_blank"],
        [f"https://vimeo.com/{VIMEO}/{VIMEO_KEY}", "_blank"],
    ]
    assert result["frames"] == 0 and result["dialogs"] == 0
    assert result["refused"] == "This preview can't play videos."
    assert _to_providers(outcome["foreign"]) == []


def test_the_survey_words_its_video_buttons(tmp_path):
    ui = {
        "media_play_text": "Video abspielen",
        "media_loads_from_text": "Wird von {service} geladen",
        "media_close_text": "Schließen",
        "media_preview_blocked_text": "Hier nicht abspielbar.",
    }
    document = _document(
        media=_youtube(alt="Bienen"),
        choices=[_option(1, "Bees", _vimeo()), _option(2, "Wasps", None)],
        ui=ui,
    )
    out = _build(document, tmp_path / "b")
    outcome = _play(
        out,
        """
        await page.waitForTimeout(800);
        const read = () => page.evaluate(() => { """
        + _FACADE
        + """ return facade(); });
        const before = await read();
        await page.click(".sd-choice-play");
        await page.waitForTimeout(200);
        const close = await page.textContent(".siamang-player-dialog__close");
        const play = await page.evaluate(() => document.querySelector(".sd-choice-play").getAttribute("aria-label"));
        await page.keyboard.press("Escape");
        await page.evaluate(() => { window.SIAMANG_DESIGN = {}; });
        await page.click(".siamang-embed__facade");
        await page.waitForTimeout(200);
        const note = await page.textContent(".siamang-embed__note");
        return { before, close, play, note };
        """,
        tmp_path,
    )
    result = outcome["result"]
    assert result["before"]["name"] == "Video abspielen: Bienen"
    assert result["before"]["description"] == "Wird von YouTube geladen"
    assert result["close"] == "Schließen"
    assert result["play"] == "Video abspielen: Bees"
    assert result["note"] == "Hier nicht abspielbar."


# ── Under the survey's own policy ────────────────────────────────────────────

_PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="


def _with_policy(document: dict[str, Any], out: Path, *, frames: bool) -> Path:
    index = out / "index.html"
    page = index.read_text("utf-8")
    sources = media_sources(document)
    policy = survey_csp(
        page,
        img_src=sources.img,
        media_src=sources.media,
        frame_src=sources.frame if frames else (),
    )
    index.write_text(insert_csp_meta(page, policy), "utf-8")
    return out


_POLICY_PLAY = """
    await page.waitForTimeout(800);
    const picture = await page.evaluate(() => {
        const img = document.querySelector(".siamang-media--image img");
        return img ? img.naturalWidth : null; });
    const quiet = await page.evaluate(() => window.__csp.slice());
    await page.click(".siamang-embed__facade");
    await page.waitForTimeout(500);
    return { picture, quiet, after: await page.evaluate(() => window.__csp.slice()) };
"""


def test_under_the_policy_of_its_own_media_a_survey_plays_its_video(tmp_path):
    document = _document(media=[{"url": _PNG, "kind": "image", "alt": "dot"}, _youtube()])
    out = _with_policy(document, _build(document, tmp_path / "b"), frames=True)
    outcome = _play(out, _POLICY_PLAY, tmp_path)
    assert outcome["errors"] == []
    result = outcome["result"]
    assert media_sources(document).frame == ("https://www.youtube-nocookie.com",)
    assert media_sources(document).img == ("data:",)
    assert result["picture"] == 1
    assert result["quiet"] == [] and result["after"] == []
    assert len(_to_providers(outcome["foreign"])) == 1


def test_a_policy_without_the_player_blocks_it(tmp_path):
    """The control: the same survey with no frame-src source for the player."""

    document = _document(media=[{"url": _PNG, "kind": "image"}, _youtube()])
    out = _with_policy(document, _build(document, tmp_path / "b"), frames=False)
    result = _play(out, _POLICY_PLAY, tmp_path)["result"]
    assert result["quiet"] == []
    assert any(
        entry.startswith("frame-src https://www.youtube-nocookie.com") for entry in result["after"]
    )
