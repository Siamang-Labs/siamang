"""In Chromium: what the runtime draws stays where it is.

Nothing moves while the answers are saved, the offer to resume is on the page
when it is first drawn, a page title and a section eyebrow keep a section gap
above the first question (as 0.6.0 drew them, before every question went into
a slot), nothing an author writes runs out of its place, and in design mode
the selected question's ring clears what is around it and moves nothing, and
the host can bring a question into view and put a rebuilt frame back where
the last one was. Same infrastructure as test_runtime_browser.py (Node,
`playwright`, a Chromium; skipped without them).
"""

from __future__ import annotations

from typing import Any

import pytest

from .test_runtime_browser import _RELOAD, _autosaved, run_in_browser

_YES_NO = [{"code": 1, "label": "Yes"}, {"code": 2, "label": "No"}]


def _choice(name: str, text: str) -> dict[str, Any]:
    return {"type": "SingleChoice", "id": name, "var": name, "text": text, "hint": "Pick one."}


def _layout_document(**ui: Any) -> dict[str, Any]:
    """A page with a title, one without (only the eyebrow), one with a block
    title, one with a Body."""

    choices = ["q1", "q2", "q3", "q4", "q5", "q6", "q7", "q8"]
    return {
        "schema_version": "1.0",
        "title": "Neighborhood life",
        "ui": ui,
        "variables": {
            **{name: {"scale": "nominal", "labels": _YES_NO} for name in choices},
        },
        "pages": [
            {
                "name": "titled",
                "title": "About you",
                "items": [_choice("q1", "Do you rent?"), _choice("q2", "Do you drive?")],
            },
            {
                "name": "untitled",
                "items": [_choice("q3", "Do you cycle?"), _choice("q4", "Do you walk?")],
            },
            {
                "name": "blocked",
                "title": "Work",
                "items": [
                    {
                        "type": "Block",
                        "title": "Commute",
                        "items": [_choice("q5", "By train?"), _choice("q6", "By bus?")],
                    }
                ],
            },
            {
                "name": "body",
                "title": "Home",
                "body": "<p>A few questions about where you live.</p>",
                "items": [_choice("q7", "A garden?"), _choice("q8", "A balcony?")],
            },
            {"name": "done", "kind": "final", "title": "Thanks"},
        ],
    }


# ── Saving ───────────────────────────────────────────────────────────────────

# Before the runtime: the layout shifts the browser records, and the tops of
# the page and of every question on each frame.
_WATCH = """
    window.__shifts = [];
    new PerformanceObserver((list) => {
        for (const e of list.getEntries()) window.__shifts.push({ value: e.value, input: e.hadRecentInput });
    }).observe({ type: "layout-shift", buffered: true });
    window.__tops = new Set();
    const tick = () => {
        const tops = [...document.querySelectorAll("#surveyContainer, .sd-question")]
            .map((el) => el.getBoundingClientRect().top.toFixed(1)).join(",");
        if (tops) window.__tops.add(tops);
        requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
"""


@pytest.mark.parametrize(
    ("style", "show"), [("bar", True), ("dots", True), ("both", True), ("bar", False)]
)
@pytest.mark.parametrize("viewport", [(1440, 900), (390, 844)])
def test_nothing_on_the_page_moves_while_the_answers_are_saved(tmp_path, style, show, viewport):
    """ "Saving…" showed in the flow above the page for 0.8 s, 2 s after an
    answer, and pushed the whole page down a line (24.8 px) and back up. It
    hangs above the page card's right corner now, takes no room, covers
    nothing, and is not a status a screen reader is told about."""

    document = _layout_document(progress_style=style)
    document["options"] = {"show_progress": show}
    width, height = viewport
    scenario = f"""
        await page.setViewportSize({{ width: {width}, height: {height} }});
        await page.evaluate(() => document.fonts.ready);
        await page.waitForTimeout(300);
        await page.evaluate(() => {{ window.__shifts = []; window.__tops = new Set(); }});
        await page.locator(".sd-question .sd-radio").first().click();
        await page.waitForSelector(".siamang-saving-indicator", {{ timeout: 6000 }});
        await page.waitForTimeout(250);
        const shown = await page.evaluate(() => {{
            const ind = document.querySelector(".siamang-saving-indicator");
            const r = ind.getBoundingClientRect();
            const overlaps = (b) => Math.min(r.right, b.right) - Math.max(r.left, b.left) > 0
                && Math.min(r.bottom, b.bottom) - Math.max(r.top, b.top) > 0;
            const main = document.getElementById("surveyContainer").getBoundingClientRect();
            return {{
                text: ind.textContent,
                covers: [...document.querySelectorAll(
                    ".siamang-header, .siamang-progress, .siamang-step-dot, .sd-page, .sd-question, .sd-btn")]
                    .filter((el) => overlaps(el.getBoundingClientRect())).map((el) => el.className),
                onScreen: r.top >= 0 && r.bottom <= window.innerHeight && r.width > 0,
                aboveCard: r.bottom <= main.top,
                rightEdge: Math.round(main.right - r.right),
                hidden: !!ind.closest('[aria-hidden="true"]'),
                live: !!ind.closest('[aria-live], [role="status"], [role="alert"]'),
            }};
        }});
        await page.waitForSelector(".siamang-saving-indicator", {{ state: "detached", timeout: 6000 }});
        await page.waitForTimeout(100);
        return {{
            shown,
            shifts: await page.evaluate(() => window.__shifts.filter((s) => !s.input).length),
            layouts: await page.evaluate(() => window.__tops.size),
        }};
    """
    state = run_in_browser(document, scenario, tmp_path, init=_WATCH)
    assert state["shifts"] == 0
    assert state["layouts"] == 1
    assert state["shown"] == {
        "text": "Saving…",
        "covers": [],
        "onScreen": True,
        "aboveCard": True,
        "rightEdge": 0,
        "hidden": True,
        "live": False,
    }


def test_a_saved_interview_is_offered_on_the_page_as_first_drawn(tmp_path):
    """The offer to resume was read after the first render and, on many
    reloads, came in above a page already drawn, pushing it down (118 px on a
    desktop). It is read before, so it is in the page as first inserted, on
    every reload. Checked at the insertion itself, not by an observer told
    later: the old runtime's second render sometimes came before an observer
    was, and a test that looked then passed on it."""

    init = """
        window.__offerAtFirstPage = null;
        const check = (node) => {
            // React builds the page out of the document and puts it in at once.
            if (window.__offerAtFirstPage !== null || !(node instanceof Element) || !node.isConnected) return;
            if (node.id !== "surveyContainer" && !node.querySelector("#surveyContainer")) return;
            window.__offerAtFirstPage = !!document.querySelector(".siamang-resume-banner");
        };
        for (const name of ["appendChild", "insertBefore"]) {
            const insert = Node.prototype[name];
            Node.prototype[name] = function (node, ...rest) {
                const out = insert.call(this, node, ...rest);
                try { check(node); } catch (e) {}
                return out;
            };
        }
    """
    scenario = (
        """
        await page.locator(".sd-question .sd-radio").first().click();
    """
        + _autosaved("answers.q1 === 1")
        + _RELOAD
        + """
        const seen = [];
        for (let i = 0; i < 5; i++) {
            await reload(".siamang-resume-banner");
            seen.push(await page.evaluate(() => window.__offerAtFirstPage));
        }
        return seen;
    """
    )
    assert run_in_browser(_layout_document(), scenario, tmp_path, init=init) == [True] * 5


def _saving_scenario(width: int) -> str:
    return f"""
        await page.setViewportSize({{ width: {width}, height: 800 }});
        await page.evaluate(() => document.fonts.ready);
        await page.locator(".sd-question .sd-radio").first().click();
        await page.waitForSelector(".siamang-saving-indicator", {{ timeout: 6000 }});
        await page.waitForTimeout(250);
        return await page.evaluate(() => {{
            const ind = document.querySelector(".siamang-saving-indicator");
            const text = ind.querySelector(".siamang-saving-indicator__text") || ind;
            const r = ind.getBoundingClientRect();
            const main = document.getElementById("surveyContainer").getBoundingClientRect();
            return {{
                left: r.left >= 0,
                rightEdge: Math.round(main.right - r.right),
                width: Math.round(r.width) <= Math.round(main.width),
                oneLine: r.height < 20,
                cut: text.scrollWidth > text.clientWidth && getComputedStyle(text).textOverflow === "ellipsis",
                above: r.top >= 0 && r.bottom <= main.top,
            }};
        }});
    """


@pytest.mark.parametrize("width", [390, 320])
def test_a_long_saving_text_ends_in_an_ellipsis_on_a_phone(tmp_path, width):
    """ "Saving…" is one line hung from the page's right edge: a saving_text
    longer than the page ran off the left of a phone's screen, where nobody
    could read its start. It ends in "…" now, inside the page."""

    document = _layout_document(
        saving_text="Ihre Antworten werden gerade in diesem Browser gespeichert, "
        "bitte warten Sie einen Augenblick"
    )
    state = run_in_browser(document, _saving_scenario(width), tmp_path)
    assert state == {
        "left": True,
        "rightEdge": 0,
        "width": True,
        "oneLine": True,
        "cut": True,
        "above": True,
    }


def test_a_screen_reader_is_told_of_the_first_save_and_not_of_every_save(tmp_path):
    """ "Saving…" itself is aria-hidden, and a polite region always in the
    page says it at the first save of a sitting only: a screen reader is
    told the answers are kept without hearing it after every answer."""

    scenario = """
        const said = () => page.evaluate(() => {
            const region = document.querySelector(".siamang-saving-status");
            return region && [region.getAttribute("role"), region.getAttribute("aria-live"), region.textContent];
        });
        const seen = { before: await said() };
        await page.locator(".sd-question .sd-radio").first().click();
        await page.waitForSelector(".siamang-saving-indicator", { timeout: 6000 });
        seen.first = await said();
        await page.waitForSelector(".siamang-saving-indicator", { state: "detached", timeout: 6000 });
        seen.after = await said();
        await page.locator(".sd-question").nth(1).locator(".sd-radio").first().click();
        await page.waitForSelector(".siamang-saving-indicator", { timeout: 6000 });
        seen.second = await said();
        return seen;
    """
    seen = run_in_browser(_layout_document(), scenario, tmp_path)
    assert seen == {
        "before": ["status", "polite", ""],
        "first": ["status", "polite", "Saving…"],
        "after": ["status", "polite", ""],
        "second": ["status", "polite", ""],
    }


# ── Gaps a respondent sees ───────────────────────────────────────────────────

# For each density and question style: the gap above each page's first
# question, between its first two, and above a block's first question, each
# page reached with design mode's goto (which shows a page as it is).
_GAPS = """
    const visit = async (name) => {
        await page.evaluate((name) => window.postMessage({ type: "siamang:goto", page: name }, "*"), name);
        await page.waitForFunction((name) => window.__page === name, name);
        await page.evaluate(() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done))));
    };
    const gaps = {};
    for (const name of ["titled", "untitled", "blocked", "body"]) {
        await visit(name);
        for (const density of ["compact", "comfortable", "spacious"]) for (const style of ["plain", "carded"]) {
            gaps[`${name} ${density} ${style}`] = await page.evaluate(([density, style]) => {
                document.documentElement.className = `density-${density} qstyle-${style}`;
                const slots = [...document.querySelectorAll(".sd-question-slot")];
                const box = (el) => el.getBoundingClientRect();
                const above = slots[0].previousElementSibling;
                return {
                    above: above ? above.className : null,
                    first: Math.round((box(slots[0]).top - box(above).bottom) * 10) / 10,
                    next: Math.round((box(slots[1]).top - box(slots[0]).bottom) * 10) / 10,
                };
            }, [density, style]);
        }
    }
    return gaps;
"""

# The runtime tells its host which page it shows; a page without a host is
# its own parent.
_DESIGN = """
    window.SIAMANG_DESIGN = { enabled: true };
    window.addEventListener("message", (e) => {
        if (e.data && e.data.type === "siamang:page") window.__page = e.data.name;
    });
"""


def test_a_title_or_an_eyebrow_keeps_a_section_gap_above_the_first_question(tmp_path):
    """0.6.0 gave the first question a section gap under the page title
    (18, 28, 40 px at compact, comfortable, spacious) and under the eyebrow of
    a page without one; carded questions sat 10 px apart. Since every question
    went into a slot those rules matched every question: the title sat flush
    on the first one, the eyebrow 6 px above it, and cards a section gap
    apart. A block title keeps its own item gap, a Body its own 1.25rem."""

    gaps = run_in_browser(_layout_document(), _GAPS, tmp_path, init=_DESIGN)
    section = {"compact": 18, "comfortable": 28, "spacious": 40}
    item = {"compact": 10, "comfortable": 14, "spacious": 18}
    for density in section:
        for style in ("plain", "carded"):
            between = 10 if style == "carded" else section[density]
            titled = gaps[f"titled {density} {style}"]
            untitled = gaps[f"untitled {density} {style}"]
            blocked = gaps[f"blocked {density} {style}"]
            body = gaps[f"body {density} {style}"]
            assert titled == {
                "above": "sd-page__title",
                "first": 10 if style == "carded" else section[density],
                "next": between,
            }
            assert untitled == {
                "above": "sd-page__eyebrow",
                "first": 10 if style == "carded" else section[density],
                "next": between,
            }
            assert blocked == {"above": "sd-block__title", "first": item[density], "next": between}
            assert body["above"] == "sd-page__html sd-page__body" and body[
                "first"
            ] == pytest.approx(19.4, abs=0.1)


# ── Design mode's ring ───────────────────────────────────────────────────────

# Every question of every page selected in turn, at each density and question
# style, light and dark: what moved, how near the ring's outer edge comes to
# any text outside the question, and the ring's contrast on the page card.
_RINGS = """
    // The progress bar's fill takes 280 ms to its new width after a page change.
    const visit = async (name) => {
        await page.evaluate((name) => window.postMessage({ type: "siamang:goto", page: name }, "*"), name);
        await page.waitForFunction((name) => window.__page === name, name);
        await page.waitForTimeout(400);
    };
    const frame = () => page.evaluate(() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done))));
    const seen = [];
    for (const name of ["titled", "untitled", "blocked", "body"]) {
        await visit(name);
        for (const theme of ["light", "dark"]) for (const density of ["compact", "comfortable", "spacious"])
        for (const style of ["plain", "divided", "carded", "accent"]) {
            await page.evaluate(([theme, density, style]) => {
                document.documentElement.className = `density-${density} qstyle-${style}`;
                document.documentElement.setAttribute("data-theme", theme);
                window.postMessage({ type: "siamang:select", id: null }, "*");
            }, [theme, density, style]);
            await frame();
            const slots = await page.evaluate(() => [...document.querySelectorAll(".sd-question-slot")].map((s) => s.dataset.qid));
            for (const id of slots) {
                // Where everything is in the page (a question the host selects
                // may be scrolled into view; that moves nothing).
                const layout = () => page.evaluate(() => [...document.querySelectorAll("#survey *")].map((el) => {
                    const b = el.getBoundingClientRect(); return [b.x + scrollX, b.y + scrollY, b.width, b.height].join(",");
                }).join("|"));
                const before = await layout();
                await page.evaluate((id) => window.postMessage({ type: "siamang:select", id }, "*"), id);
                await page.waitForSelector(`.sd-question-slot.is-design-selected[data-qid="${id}"]`);
                await frame();
                const moved = before !== (await layout());
                seen.push(await page.evaluate(([id, moved, where]) => {
                    const slot = document.querySelector(`.sd-question-slot[data-qid="${id}"]`);
                    // The ring: the outline of the slot, or of the question in it.
                    const drawn = [slot, slot.firstElementChild].find((el) => getComputedStyle(el).outlineStyle !== "none") || slot;
                    const cs = getComputedStyle(drawn);
                    const out = parseFloat(cs.outlineOffset) + parseFloat(cs.outlineWidth);
                    const b = drawn.getBoundingClientRect();
                    const ring = { l: b.left - out, t: b.top - out, r: b.right + out, b: b.bottom + out };
                    let clear = Infinity;
                    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                    for (let n = walker.nextNode(); n; n = walker.nextNode()) {
                        if (!n.nodeValue.trim() || slot.contains(n) || n.parentElement.closest(".siamang-announce")) continue;
                        const range = document.createRange();
                        range.selectNodeContents(n);
                        for (const t of range.getClientRects()) {
                            const dx = Math.max(ring.l - t.right, t.left - ring.r, 0);
                            const dy = Math.max(ring.t - t.bottom, t.top - ring.b, 0);
                            clear = Math.min(clear, dx || dy ? Math.hypot(dx, dy) : -1);
                        }
                    }
                    // WCAG's contrast of the ring's color on the card it sits on.
                    // "rgb(r, g, b)", or "color(srgb r g b)" (0–1) for a color-mix.
                    const rgb = (c) => {
                        const v = c.match(/[\\d.]+/g).slice(0, 3).map(Number);
                        return c.startsWith("color(") ? v.map((x) => x * 255) : v;
                    };
                    const lum = (c) => {
                        const [r, g, bl] = rgb(c).map((v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; });
                        return 0.2126 * r + 0.7152 * g + 0.0722 * bl;
                    };
                    const card = getComputedStyle(document.querySelector(".sd-page")).backgroundColor;
                    const [hi, lo] = [lum(cs.outlineColor), lum(card)].sort((x, y) => y - x);
                    return { where, id, moved, ring: cs.outlineStyle !== "none", clear, contrast: (hi + 0.05) / (lo + 0.05) };
                }, [id, moved, `${name} ${theme} ${density} ${style}`]));
            }
        }
    }
    return seen;
"""


@pytest.mark.parametrize("width", [1440, 390])
def test_the_selected_questions_ring_clears_what_is_around_it_and_moves_nothing(tmp_path, width):
    """Design mode drew the selected question's ring 8 px out from the
    question, on a page title that sat flush on the first question: it ran
    9 px into the title. With the gaps back, the ring is 6 px out (4 px
    around a card, 10 px from the next), clears every neighbor's text, moves
    nothing when it comes, and has at least 3:1 on the card in dark mode too
    (the light primary had 2.6:1 there)."""

    scenario = f"await page.setViewportSize({{ width: {width}, height: 900 }});" + _RINGS
    seen = run_in_browser(_layout_document(), scenario, tmp_path, init=_DESIGN)
    assert len(seen) == 4 * 2 * 3 * 4 * 2
    assert [s for s in seen if not s["ring"] or s["moved"]] == []
    assert min(s["clear"] for s in seen) > 3
    assert min(s["contrast"] for s in seen) >= 3


# ── What an author writes stays in its place ─────────────────────────────────

# A 160 × 100 picture, as a data: address (the harness reaches no network).
_PICTURE = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAKAAAABkCAIAAACO1KzYAAAAsUlEQVR42u3RQQkAAAgEweuPb+OYzRoiA5tg"
    "Jz2lx8UCwAIswAIswAIswIAFWIAFWIAFWIABC7AAC7AAC7AACzBgARZgARZgARZgwAIswAIswAIswIAFWIAF"
    "WIAFWIAFGLAAC7AAC7AACzBgARZgARZgARZgwC4AFmABFmABFmABBizAAizAAizAAgxYgAVYgAVYgAVYgAEL"
    "sAALsAALsAADFmABFmABFmABBizAAqx7LcUVNtxuGUMGAAAAAElFTkSuQmCC"
)
_LONG_WORD = "https://www.example.org/neighborhood-life/2026/questionnaire/part-two/your-street"
_SCALE = ["Poor", "Fair", "Good", "Very good", "Excellent"]
_OFTEN = [
    "Never at all",
    "Less than once a year",
    "Once or twice a year",
    "Every few months",
    "About once a month",
    "Two or three times a month",
    "About once a week",
    "Several times a week",
    "Every day",
]


def _authored_document() -> dict[str, Any]:
    """A Body with a picture floated beside its one line, a hint that is one
    long address, a wide matrix and a required one."""

    matrix_vars = {f"m_{k}": {"scale": "ordinal", "labels": []} for k in "abcde"}
    return {
        "schema_version": "1.0",
        "title": "Neighborhood life",
        "variables": {
            "q1": {"scale": "nominal", "labels": _YES_NO},
            "q2": {"scale": "nominal", "labels": _YES_NO},
            "addr": {"scale": "nominal"},
            **matrix_vars,
        },
        "pages": [
            {
                "name": "park",
                "title": "The park",
                "body": f'<p><img src="{_PICTURE}" alt="A park" width="160" height="100" align="right">'
                "The park by the river is the one we mean.</p>",
                "items": [
                    _choice("q1", "Do you go there?"),
                    {
                        "type": "OpenText",
                        "id": "addr",
                        "var": "addr",
                        "text": f"Paste the address: {_LONG_WORD}",
                        "hint": "Supercalifragilisticexpialidociousandthensomemorelettersthatdonotbreak",
                    },
                ],
            },
            {
                "name": "matrices",
                "title": "Getting around",
                "items": [
                    {
                        "type": "Matrix",
                        "id": "wide",
                        "text": "How often do you use each one?",
                        "var": ["m_a", "m_b"],
                        "subquestions": ["The bus that runs along the river", "The train"],
                        "column_labels": _OFTEN,
                        "na_option": True,
                    },
                    {
                        "type": "Matrix",
                        "id": "rate",
                        "text": "How do you rate your commute?",
                        "var": ["m_c", "m_d", "m_e"],
                        "subquestions": ["Time it takes", "What it costs", "How crowded it is"],
                        "column_labels": _SCALE,
                        "required": True,
                    },
                    {**_choice("q2", "Is that all?"), "required": True},
                ],
            },
            {"name": "done", "kind": "final", "title": "Thanks"},
        ],
    }


def test_a_floated_picture_a_long_word_and_a_missing_rows_mark_keep_their_place(tmp_path):
    """A picture floated in a page's Body hung out of it over the first
    question; a word longer than the line (an address) ran past the card and
    gave a phone's page a sideways scroll; and on a phone a required matrix
    row's mark was drawn over its statement's first letter. The Body holds its
    float (its gap to the first question is unchanged without one), a long
    word breaks, and the mark stands beside the statement."""

    scenario = """
        const seen = {};
        for (const width of [1440, 390]) {
            await page.setViewportSize({ width, height: 900 });
            await page.evaluate(() => window.scrollTo(0, 0));
            seen[width] = await page.evaluate(() => {
                const img = document.querySelector(".sd-page__body img").getBoundingClientRect();
                const first = document.querySelector(".sd-question-slot").getBoundingClientRect();
                const body = document.querySelector(".sd-page__body").getBoundingClientRect();
                const card = document.querySelector(".sd-page").getBoundingClientRect();
                const right = (el) => {
                    const r = document.createRange(); r.selectNodeContents(el);
                    return Math.max(...[...r.getClientRects()].map((x) => x.right));
                };
                const slot = document.querySelectorAll(".sd-question-slot")[1];
                return {
                    floatClear: Math.round(first.top - img.bottom),
                    bodyHolds: img.bottom <= body.bottom + 0.5,
                    titleInCard: right(slot.querySelector(".sd-question__title")) <= card.right,
                    hintInCard: right(slot.querySelector(".sd-question__description")) <= card.right,
                    sideways: document.documentElement.scrollWidth > innerWidth,
                };
            });
        }
        await page.locator(".sd-navigation__next-btn").click();
        await page.waitForFunction(() => document.querySelector(".sd-page__title").textContent === "Getting around");
        await page.locator(".sd-navigation__next-btn").click();
        await page.waitForSelector("tr.is-missing");
        seen.shake = await page.evaluate(() => [...new Set([...document.querySelectorAll(".sd-question.has-error")]
            .map((q) => getComputedStyle(q).animationName))]);
        seen.mark = await page.evaluate(() => {
            const td = document.querySelector("tr.is-missing td:first-child");
            const r = document.createRange(); r.selectNodeContents(td);
            const text = r.getClientRects()[0];
            const mark = getComputedStyle(td, "::before");
            const left = td.getBoundingClientRect().left + parseFloat(mark.left);
            return { clear: Math.round(text.left - (left + parseFloat(mark.width))), inset: getComputedStyle(td).boxShadow };
        });
        return seen;
    """
    seen = run_in_browser(_authored_document(), scenario, tmp_path)
    for width in ("1440", "390"):
        assert seen[width]["floatClear"] >= 18
        assert seen[width]["bodyHolds"] is True
        assert seen[width]["titleInCard"] is True
        assert seen[width]["hintInCard"] is True
        assert seen[width]["sideways"] is False
    assert seen["mark"] == {"clear": 6, "inset": "none"}
    # A respondent's page keeps its shake.
    assert seen["shake"] == ["siamang-error-shake"]


def test_a_selected_wide_matrix_and_an_error_stay_inside_the_ring(tmp_path):
    """A matrix wider than its question scrolls in a box half a section gap
    wider on each side: the ring ran through its last column. The selected one
    is drawn to the question's width, so nothing of it is outside the ring (a
    card's padding holds it already). A question with an error shook 6 px
    under a ring that stays put, across it; in design mode it shakes 2 px, in
    the room between it and its ring, whether it is selected or not."""

    scenario = """
        await page.setViewportSize({ width: 1440, height: 900 });
        await page.evaluate(() => window.postMessage({ type: "siamang:goto", page: "matrices" }, "*"));
        await page.waitForFunction(() => window.__page === "matrices");
        const seen = {};
        for (const density of ["compact", "comfortable", "spacious"]) for (const style of ["plain", "accent", "carded"]) {
            seen[`${density} ${style}`] = await page.evaluate(([density, style]) => {
                document.documentElement.className = `density-${density} qstyle-${style}`;
                window.postMessage({ type: "siamang:select", id: "wide" }, "*");
                return new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(() => {
                    const slot = document.querySelector('.sd-question-slot[data-qid="wide"]');
                    const ring = parseFloat(getComputedStyle(slot).outlineOffset);
                    const s = slot.getBoundingClientRect();
                    const w = slot.querySelector(".sd-matrix-wrapper");
                    const b = w.getBoundingClientRect();
                    const m = getComputedStyle(w).clipPath.match(/inset\\(([\\d.]+)px(?: ([\\d.]+)px)?/);
                    const cut = m ? parseFloat(m[2] ?? m[1]) : 0;
                    done({
                        scrolls: w.scrollWidth > w.clientWidth,
                        outside: Math.max(0, s.left - ring - (b.left + cut), b.right - cut - (s.right + ring)),
                    });
                })));
            }, [density, style]);
        }
        await page.evaluate(() => {
            document.documentElement.className = "density-comfortable qstyle-plain";
            window.postMessage({ type: "siamang:select", id: "rate" }, "*");
        });
        await page.waitForSelector('.sd-question-slot.is-design-selected[data-qid="rate"]');
        const shake = {};
        for (const style of ["plain", "carded", "accent"]) {
            await page.evaluate((style) => { document.documentElement.className = `density-compact qstyle-${style}`; }, style);
            await page.locator(".sd-navigation__next-btn").click();
            await page.waitForSelector('[data-qid="rate"] .sd-question.has-error');
            // Each peak of the shake, held: how far the selected question's
            // edges come past the ring's inner edge.
            shake[style] = await page.evaluate(() => {
                const slot = document.querySelector('.sd-question-slot[data-qid="rate"]');
                const q = slot.querySelector(".sd-question");
                const ring = parseFloat(getComputedStyle(slot).outlineOffset);
                const s = slot.getBoundingClientRect();
                let past = -Infinity;
                const names = [...document.querySelectorAll(".sd-question.has-error")].map((x) => getComputedStyle(x).animationName);
                for (const a of q.getAnimations()) {
                    for (const at of [67.5, 135, 202.5, 270]) {
                        a.pause(); a.currentTime = at;
                        const b = q.getBoundingClientRect();
                        past = Math.max(past, (s.left - ring) - b.left, b.right - (s.right + ring));
                    }
                    a.finish();
                }
                return { names: [...new Set(names)], past: Math.round(past * 10) / 10 };
            });
            await page.evaluate(() => window.postMessage({ type: "siamang:goto", page: "park" }, "*"));
            await page.waitForFunction(() => window.__page === "park");
            await page.evaluate(() => window.postMessage({ type: "siamang:goto", page: "matrices" }, "*"));
            await page.waitForFunction(() => window.__page === "matrices");
        }
        seen.shake = shake;
        return seen;
    """
    seen = run_in_browser(_authored_document(), scenario, tmp_path, init=_DESIGN)
    shake = seen.pop("shake")
    for where, state in seen.items():
        assert state == {"scrolls": True, "outside": 0}, where
    for style, state in shake.items():
        assert state["names"] == ["siamang-error-shake-small"], style
        assert state["past"] <= 0, style


# ── Design mode: the host's selection and a rebuilt frame ────────────────────


def _long_document() -> dict[str, Any]:
    names = [f"q{i}" for i in range(1, 13)]
    return {
        "schema_version": "1.0",
        "title": "Neighborhood life",
        "variables": {name: {"scale": "nominal", "labels": _YES_NO} for name in names},
        "pages": [
            {
                "name": "long",
                "title": "About you",
                "items": [_choice(n, f"Question {n}?") for n in names[:10]],
            },
            {
                "name": "short",
                "title": "Work",
                "items": [_choice(n, f"Question {n}?") for n in names[10:]],
            },
            {"name": "done", "kind": "final", "title": "Thanks"},
        ],
    }


# The runtime's own messages, in the order it posts them (a page without a
# host is its own parent).
_MESSAGES = """
    window.SIAMANG_DESIGN = { enabled: true };
    window.__said = [];
    window.addEventListener("message", (e) => {
        if (e.data && e.data.source === "siamang-runtime") window.__said.push(e.data);
        if (e.data && e.data.type === "siamang:page") window.__page = e.data.name;
    });
"""


def test_the_host_brings_a_question_into_view_and_puts_a_rebuilt_frame_back(tmp_path):
    """A host may rebuild its frame after an edit, and a new frame started at
    the top of page 1. A question the host selects is scrolled into
    view when it is not (a click in the page is in view, and its echo moves
    nothing); a page it sends the runtime to starts at its top; the window's
    place is posted as it scrolls; and a restore puts a new frame on the page,
    the question and the place the last one had, then says it is done."""

    scenario = """
        await page.setViewportSize({ width: 1024, height: 600 });
        const host = (msg) => page.evaluate((msg) => window.postMessage(msg, "*"), msg);
        const settle = () => page.evaluate(() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done))));
        const where = (id) => page.evaluate((id) => {
            const b = document.querySelector(`.sd-question-slot[data-qid="${id}"]`).getBoundingClientRect();
            return { y: Math.round(scrollY), inView: b.top >= 0 && b.bottom <= innerHeight };
        }, id);
        const seen = {};
        await host({ type: "siamang:select", id: "q9" });
        await settle();
        seen.selected = await where("q9");
        // A click in the page, and the host's answer naming the same question.
        await page.evaluate(() => window.scrollBy(0, -120));
        await settle();
        const before = await page.evaluate(() => Math.round(scrollY));
        await page.locator('.sd-question-slot[data-qid="q8"] .sd-question__title').click();
        await host({ type: "siamang:select", id: "q8" });
        await settle();
        seen.click = (await page.evaluate(() => Math.round(scrollY))) === before;
        await host({ type: "siamang:goto", page: "short" });
        await page.waitForFunction(() => window.__page === "short");
        await settle();
        seen.goto = await page.evaluate(() => Math.round(scrollY));
        await host({ type: "siamang:goto", page: "long" });
        await page.waitForFunction(() => window.__page === "long");
        await page.evaluate(() => { window.__said = []; window.scrollTo(0, 123); });
        await page.waitForFunction(() => window.__said.some((m) => m.type === "siamang:scroll"));
        seen.reported = await page.evaluate(() => window.__said.filter((m) => m.type === "siamang:scroll").map((m) => m.y));
        // A new frame's runtime: on page 1 at the top, told where the last one was.
        await host({ type: "siamang:goto", page: "short" });
        await page.waitForFunction(() => window.__page === "short");
        await page.evaluate(() => { window.__said = []; });
        await host({ type: "siamang:restore", page: "long", id: "q7", y: 300 });
        await page.waitForFunction(() => window.__said.some((m) => m.type === "siamang:restored"));
        seen.restored = await page.evaluate(() => ({
            said: window.__said.find((m) => m.type === "siamang:restored"),
            page: window.__page,
            y: Math.round(scrollY),
            ring: document.querySelector(".is-design-selected").dataset.qid,
        }));
        // Without a y: the page from its top, the question in view.
        await host({ type: "siamang:goto", page: "short" });
        await page.waitForFunction(() => window.__page === "short");
        await page.evaluate(() => { window.__said = []; });
        await host({ type: "siamang:restore", page: "long", id: "q10" });
        await page.waitForFunction(() => window.__said.some((m) => m.type === "siamang:restored"));
        seen.revealed = { ...(await where("q10")), page: await page.evaluate(() => window.__page) };
        // A page it cannot show: a y read on another page is not used there.
        await page.evaluate(() => { window.__said = []; });
        await host({ type: "siamang:restore", page: "nowhere", id: null, y: 400 });
        await page.waitForFunction(() => window.__said.some((m) => m.type === "siamang:restored"));
        seen.nowhere = await page.evaluate(() => ({ page: window.__page, y: Math.round(scrollY) }));
        return seen;
    """
    seen = run_in_browser(_long_document(), scenario, tmp_path, init=_MESSAGES)
    assert seen["selected"]["inView"] is True and seen["selected"]["y"] > 0
    assert seen["click"] is True
    assert seen["goto"] == 0
    assert seen["reported"][-1] == 123
    restored = seen["restored"]
    assert restored["page"] == "long" and restored["y"] == 300 and restored["ring"] == "q7"
    assert restored["said"] == {
        "source": "siamang-runtime",
        "type": "siamang:restored",
        "page": "long",
        "y": 300,
    }
    assert (
        seen["revealed"]["page"] == "long"
        and seen["revealed"]["inView"] is True
        and seen["revealed"]["y"] > 0
    )
    assert seen["nowhere"] == {"page": "long", "y": 0}
