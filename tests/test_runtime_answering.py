"""In Chromium: a respondent answers from the keyboard and a screen reader as
the page looks, and what is answered is kept when the page is left.

A 0–10 scale or a row of stars is one radio group (one tab stop, the arrow
keys and Home/End move the choice); a digit answers the scale the focus is
in, "1" then "0" its 10; the keyboard's focus shows on an option's row; a text
or number field is named by its question; a step dot is a 24 px target; a
long scale wraps into even rows of equal cells; an answer given just before
the page is hidden is in the save a transport reads then; and an error a
question shows as it is left waits for the press that left it to end. Same
infrastructure as test_runtime_browser.py (Node, `playwright`, a Chromium;
skipped without them).
"""

from __future__ import annotations

from typing import Any

from .test_runtime_browser import _RELOAD, run_in_browser

_VISITS = [
    {"code": 1, "label": "This is my first visit"},
    {"code": 2, "label": "A few times a month"},
    {"code": 3, "label": "Weekly or more"},
]


def _scales_document(*, required: bool = False) -> dict[str, Any]:
    """A café's feedback page: how often (a choice), satisfaction in five
    stars, the 0–10 recommendation with its end labels, what was tried (boxes);
    then a page of its own and the end."""

    return {
        "schema_version": "1.0",
        "title": "Example Cafe - quick feedback",
        "ui": {"progress_style": "dots"},
        "variables": {
            "visit": {"scale": "nominal", "labels": _VISITS},
            "sat": {"scale": "ordinal"},
            "nps": {"scale": "ordinal"},
            "tried_tea": {
                "scale": "nominal",
                "labels": [{"code": 0, "label": "No"}, {"code": 1, "label": "Yes"}],
            },
            "tried_cake": {
                "scale": "nominal",
                "labels": [{"code": 0, "label": "No"}, {"code": 1, "label": "Yes"}],
            },
            "again": {
                "scale": "nominal",
                "labels": [{"code": 1, "label": "Yes"}, {"code": 2, "label": "No"}],
            },
            "note": {"scale": "nominal"},
        },
        "pages": [
            {
                "name": "visit",
                "title": "Your visit",
                "items": [
                    {
                        "type": "SingleChoice",
                        "id": "visit",
                        "var": "visit",
                        "required": required,
                        "text": "How often do you visit Example Cafe?",
                        "choices": _VISITS,
                    },
                    {
                        "type": "LikertScale",
                        "id": "sat",
                        "var": "sat",
                        "text": "How satisfied were you today?",
                        "points": 5,
                        "display": "stars",
                    },
                    {
                        "type": "LikertScale",
                        "id": "nps",
                        "var": "nps",
                        "text": "How likely are you to recommend Example Cafe to a friend?",
                        "points": 11,
                        "start": 0,
                        "left_label": "Not at all likely",
                        "right_label": "Extremely likely",
                    },
                    {
                        "type": "MultiChoice",
                        "id": "tried",
                        "text": "What did you try?",
                        "mode": "wide",
                        "var": ["tried_tea", "tried_cake"],
                        "choices": [{"code": 1, "label": "Tea"}, {"code": 2, "label": "Cake"}],
                    },
                ],
            },
            {
                "name": "again",
                "title": "Next time",
                "items": [
                    {
                        "type": "SingleChoice",
                        "id": "again",
                        "var": "again",
                        "text": "Will you come again?",
                        "choices": [{"code": 1, "label": "Yes"}, {"code": 2, "label": "No"}],
                    }
                ],
            },
            {
                "name": "more",
                "title": "One more thing",
                "items": [_open_text("note", "Anything else?")],
            },
            {"name": "done", "kind": "final", "title": "Thanks"},
        ],
    }


def _open_text(name: str, text: str, **extra: Any) -> dict[str, Any]:
    return {"type": "OpenText", "id": name, "var": name, "text": text, **extra}


# `scale(i)` is the i-th scale on the page; `checked(i)` its checked point's
# text or name (null: none); `focused()` the focused element's text or name.
_SCALES = """
    const scale = (i) => page.locator(".sd-rating__scale").nth(i);
    const checked = (i) => scale(i).evaluate((s) => {
        const c = s.querySelector('[aria-checked="true"], .is-selected');
        return c ? (c.getAttribute("aria-label") || c.textContent.trim()) : null;
    });
    const focused = () => page.evaluate(() => {
        const el = document.activeElement;
        return el ? (el.getAttribute("aria-label") || el.textContent.trim() || el.tagName) : null;
    });
    const press = async (...keys) => {
        for (const key of keys) { await page.keyboard.press(key); await page.waitForTimeout(60); }
    };
"""


# ── A scale is a radio group ─────────────────────────────────────────────────


def test_a_scale_is_one_radio_group_the_arrow_keys_move_through(tmp_path):
    """Every point of a scale was a toggle button of its own: eleven tab stops
    on a 0–10 scale, each announced as "0, toggle button, not pressed" with no
    place on the scale and no end label. A scale is a radio group now: its
    points are radios, checked or not, one of them in the tab order (the
    chosen one, else the first); the arrow keys move the choice and the focus
    with it, Home and End go to the ends, and an arrow stops at an end rather
    than jump to the other one. The end labels describe the end points."""

    scenario = (
        _SCALES
        + """
        const roles = await page.evaluate(() => [...document.querySelectorAll(".sd-rating__scale")].map((s) => ({
            group: s.getAttribute("role"),
            points: [...s.children].map((b) => [b.getAttribute("role"), b.getAttribute("aria-checked")].join(" ")),
            stops: [...s.children].filter((b) => b.tabIndex === 0).length,
        })));
        const named = {
            stars: await scale(0).getByRole("radio", { name: "4", exact: true }).count(),
            group: await page.getByRole("radiogroup", { name: "How likely are you to recommend Example Cafe to a friend?" })
                .getByRole("radio").count(),
            low: await scale(1).locator("[role=radio]").first().evaluate((b) =>
                document.getElementById(b.getAttribute("aria-describedby")).textContent),
            high: await scale(1).locator("[role=radio]").last().evaluate((b) =>
                document.getElementById(b.getAttribute("aria-describedby")).textContent),
        };
        // Tab from the top of the page through the questions to Next.
        await page.evaluate(() => document.activeElement && document.activeElement.blur());
        const stops = [];
        for (let i = 0; i < 20; i++) {
            await page.keyboard.press("Tab");
            const where = await page.evaluate(() => {
                const el = document.activeElement;
                const s = el.closest(".sd-rating__scale");
                return s ? "scale " + [...document.querySelectorAll(".sd-rating__scale")].indexOf(s) + ": " + (el.getAttribute("aria-label") || el.textContent)
                    : el.className.includes("next-btn") ? "next" : null;
            });
            if (where) stops.push(where);
            if (where === "next") break;
        }
        await scale(1).locator("[role=radio]").first().focus();
        const moves = [];
        for (const key of ["ArrowRight", "ArrowRight", "ArrowDown", "ArrowLeft", "End", "ArrowRight", "Home", "ArrowLeft", "ArrowUp"]) {
            await press(key);
            moves.push([key, await checked(1), await focused()]);
        }
        await press("End", "ArrowLeft");
        // With Alt, Ctrl or Cmd an arrow is the browser's (Alt+Left: Back).
        const modified = [];
        for (const key of ["Alt+ArrowLeft", "Control+ArrowRight", "Meta+ArrowLeft", "Alt+Home"]) {
            await page.keyboard.press(key);
            await page.waitForTimeout(60);
            modified.push(await checked(1));
        }
        // Out of the group and back: the focus comes back to the chosen point.
        await press("Tab");
        await page.keyboard.down("Shift");
        await press("Tab");
        await page.keyboard.up("Shift");
        const back = await focused();
        await scale(0).locator("[role=radio]").nth(1).focus();
        await press("ArrowRight", "ArrowRight");
        const stars = [await checked(0), await focused()];
        const tabbable = await scale(1).locator("[tabindex='0']").allTextContents();
        // An arrow at the end, or End on the end chosen, changes nothing and
        // writes no save: once the last one is written (2 s after the last
        // answer), none follows.
        await scale(1).locator("[role=radio]").last().focus();
        await press("End");
        await page.waitForTimeout(2600);
        await page.evaluate(() => {
            window.__writes = 0;
            const set = Storage.prototype.setItem;
            Storage.prototype.setItem = function (k, v) { window.__writes += 1; return set.call(this, k, v); };
        });
        await press("ArrowRight", "End", "ArrowDown");
        await page.waitForTimeout(2600);
        const rewritten = await page.evaluate(() => window.__writes);
        return { roles, named, stops, moves, modified, back, stars, rewritten, tabbable };
    """
    )
    state = run_in_browser(_scales_document(), scenario, tmp_path)
    assert state["roles"] == [
        {"group": "radiogroup", "points": ["radio false"] * 5, "stops": 1},
        {"group": "radiogroup", "points": ["radio false"] * 11, "stops": 1},
    ]
    assert state["named"] == {
        "stars": 1,
        "group": 11,
        "low": "Not at all likely",
        "high": "Extremely likely",
    }
    assert [stop for stop in state["stops"] if stop.startswith("scale")] == [
        "scale 0: 1",
        "scale 1: 0",
    ]
    assert state["moves"] == [
        ["ArrowRight", "1", "1"],
        ["ArrowRight", "2", "2"],
        ["ArrowDown", "3", "3"],
        ["ArrowLeft", "2", "2"],
        ["End", "10", "10"],
        ["ArrowRight", "10", "10"],
        ["Home", "0", "0"],
        ["ArrowLeft", "0", "0"],
        ["ArrowUp", "0", "0"],
    ]
    assert state["modified"] == ["9", "9", "9", "9"]
    assert state["back"] == "9"
    assert state["tabbable"] == ["9"]
    assert state["stars"] == ["4", "4"]
    assert state["rewritten"] == 0


# ── Digits ───────────────────────────────────────────────────────────────────


def test_a_digit_answers_the_scale_the_focus_is_in_and_two_make_ten(tmp_path):
    """A digit went to the page's first scale that had the point, whichever
    question the respondent was at: "1" at the 0–10 scale changed the stars
    above it, and 10 could not be typed. It answers the scale the focus is in
    now ("1" then "0" is its 10, "0" alone its 0), the page's only scale when
    the focus is in no question, and nothing at all from another question or
    with two scales and the focus in neither."""

    scenario = (
        _SCALES
        + """
        await scale(1).locator("[role=radio]").nth(5).click();
        const seen = { clicked: [await checked(0), await checked(1)] };
        await press("1");
        seen.one = [await checked(0), await checked(1), await focused()];
        await page.keyboard.press("1");
        await page.keyboard.press("0");
        await page.waitForTimeout(60);
        seen.ten = [await checked(0), await checked(1), await focused()];
        await page.waitForTimeout(900);
        await press("0");
        seen.zero = [await checked(0), await checked(1)];
        await scale(0).locator("[role=radio]").first().focus();
        await press("3");
        seen.stars = [await checked(0), await checked(1), await focused()];
        await press("7");
        seen.noSuchStar = [await checked(0), await checked(1)];
        // From another question, and with the focus in no question.
        await page.locator(".sd-radio input").first().focus();
        await press("8");
        seen.choice = [await checked(0), await checked(1)];
        await page.evaluate(() => document.activeElement && document.activeElement.blur());
        await press("6");
        seen.nowhere = [await checked(0), await checked(1)];
        return seen;
    """
    )
    seen = run_in_browser(_scales_document(), scenario, tmp_path)
    assert seen == {
        "clicked": [None, "5"],
        "one": [None, "1", "1"],
        "ten": [None, "10", "10"],
        "zero": [None, "0"],
        "stars": ["3", "0", "3"],
        "noSuchStar": ["3", "0"],
        "choice": ["3", "0"],
        "nowhere": ["3", "0"],
    }


# ── Focus on an option's row ─────────────────────────────────────────────────


def test_the_keyboard_focus_shows_on_an_options_row(tmp_path):
    """An option's input is hidden under its decorator, and the focus ring
    was drawn on the hidden input: tabbing through a choice or a set of boxes
    showed nothing. The row has a solid ring, 3:1 or more on the card in light
    and dark; a click with the mouse draws none."""

    scenario = """
        const ring = (selector, index) => page.evaluate(([selector, index]) => {
            const row = index === undefined ? document.activeElement.closest(selector)
                : document.querySelectorAll(selector)[index];
            const cs = getComputedStyle(row);
            const rgb = (c) => {
                const v = c.match(/[\\d.]+/g).slice(0, 3).map(Number);
                return c.startsWith("color(") ? v.map((x) => x * 255) : v;
            };
            const lum = (c) => {
                const [r, g, b] = rgb(c).map((v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; });
                return 0.2126 * r + 0.7152 * g + 0.0722 * b;
            };
            const card = getComputedStyle(document.querySelector(".sd-page")).backgroundColor;
            const [hi, lo] = [lum(cs.outlineColor), lum(card)].sort((x, y) => y - x);
            // An outline of style none draws nothing, whatever its width: since
            // Chromium 147 its computed width keeps the specified one (3px,
            // medium) where it was 0 (CSSWG #11494), so the width read is the
            // one drawn.
            const none = cs.outlineStyle === "none";
            return { style: cs.outlineStyle, width: none ? "0px" : cs.outlineWidth, contrast: none ? 0 : (hi + 0.05) / (lo + 0.05) >= 3 };
        }, [selector, index]);
        const seen = {};
        for (const theme of ["light", "dark"]) {
            await page.evaluate((theme) => document.documentElement.setAttribute("data-theme", theme), theme);
            await page.evaluate(() => document.activeElement && document.activeElement.blur());
            await page.locator(".sd-page__title").click();
            await page.keyboard.press("Tab");
            seen[theme + " radio"] = await ring(".sd-radio");
            await page.locator(".sd-checkbox input").first().focus();
            await page.keyboard.press("Shift+Tab");
            await page.keyboard.press("Tab");
            seen[theme + " checkbox"] = await ring(".sd-checkbox");
            // A number of a scale, not chosen: the same solid ring, and its
            // text as readable as the card's (a button's own black was all
            // but invisible on a dark card).
            await page.locator(".sd-rating__scale").nth(1).locator("[role=radio]").first().focus();
            seen[theme + " number"] = await ring(".sd-rating__item");
            await page.waitForTimeout(200);  // the points' color eases in over 80 ms
            seen[theme + " digits"] = await page.evaluate(() => {
                const point = document.querySelectorAll(".sd-rating__scale")[1].children[3];
                return getComputedStyle(point).color === getComputedStyle(document.querySelector(".sd-question__title")).color;
            });
        }
        await page.locator(".sd-radio").nth(1).click();
        seen.clicked = await ring(".sd-radio", 1);
        // Forced colors drop every box-shadow, and the fill a chosen number
        // was told by: an outline shows the focus, and the chosen point is
        // drawn in the system's Highlight.
        await page.emulateMedia({ forcedColors: "active" });
        await page.locator(".sd-radio input").first().focus();
        await page.keyboard.press("Shift+Tab");
        await page.keyboard.press("Tab");
        seen.forced = (await ring(".sd-radio")).style;
        await page.locator(".sd-rating__scale").nth(1).locator("[role=radio]").nth(7).click();
        seen.chosen = await page.evaluate(() => {
            const points = document.querySelectorAll(".sd-rating__scale")[1].children;
            return getComputedStyle(points[7]).backgroundColor !== getComputedStyle(points[6]).backgroundColor;
        });
        return seen;
    """
    seen = run_in_browser(_scales_document(), scenario, tmp_path)
    shown = {"style": "solid", "width": "2px", "contrast": True}
    assert seen == {
        "light radio": shown,
        "light checkbox": shown,
        "light number": shown,
        "light digits": True,
        "dark radio": shown,
        "dark checkbox": shown,
        "dark number": shown,
        "dark digits": True,
        "clicked": {"style": "none", "width": "0px", "contrast": 0},
        "forced": "solid",
        "chosen": True,
    }


# ── Named fields ─────────────────────────────────────────────────────────────


def test_a_text_and_a_number_field_are_named_by_their_question(tmp_path):
    """A text field, a text box of several lines and a number field had no
    name: a screen reader said "edit text" and nothing of the question above.
    Each is named by its question's title, as the respondent reads it (with
    an earlier answer piped in), and says when its answer is wrong."""

    document = {
        "schema_version": "1.0",
        "title": "Example Cafe - quick feedback",
        "variables": {
            "name": {"scale": "nominal"},
            "improve": {"scale": "nominal"},
            "cups": {"scale": "ratio", "valid_range": [0, 50]},
        },
        "pages": [
            {"name": "p1", "items": [_open_text("name", "What is your first name?")]},
            {
                "name": "p2",
                "items": [
                    _open_text("improve", "What should we improve, {answer:name}?", multiline=True),
                    {
                        "type": "NumericInput",
                        "id": "cups",
                        "var": "cups",
                        "text": "How many cups a week?",
                    },
                ],
            },
            {"name": "done", "kind": "final", "title": "Thanks"},
        ],
    }
    scenario = """
        const named = (role, name) => page.getByRole(role, { name, exact: true }).count();
        const seen = { name: await named("textbox", "What is your first name?") };
        await page.fill("input.sd-input", "Ann");
        await page.click(".sd-navigation__next-btn");
        await page.waitForSelector("textarea");
        seen.improve = await named("textbox", "What should we improve, Ann?");
        seen.cups = await named("spinbutton", "How many cups a week?");
        seen.valid = await page.locator("input[type=number]").getAttribute("aria-invalid");
        await page.fill("input[type=number]", "80");
        await page.locator("textarea").focus();
        await page.waitForSelector(".sd-question__error");
        seen.invalid = await page.locator("input[type=number]").getAttribute("aria-invalid");
        // The field names its error, so a screen reader on it hears why.
        seen.why = await page.locator("input[type=number]").evaluate((el) => {
            const id = el.getAttribute("aria-describedby");
            const error = el.closest(".sd-question").querySelector(".sd-question__error");
            return id && document.getElementById(id) === error ? "the error" : id;
        });
        return seen;
    """
    seen = run_in_browser(document, scenario, tmp_path)
    assert seen == {
        "name": 1,
        "improve": 1,
        "cups": 1,
        "valid": None,
        "invalid": "true",
        "why": "the error",
    }


# ── Step dots ────────────────────────────────────────────────────────────────

# The dots' buttons and the dots drawn in them on the second page, and where
# a click 9 px beside the first dot's center goes (a tap 8 px beside it: the
# old dot's edge was 5 px from its center).
_DOTS = """
    const dots = async (p, off, finger) => {
        await p.locator(".sd-radio").first().click();
        await p.click(".sd-navigation__next-btn");
        await p.waitForSelector(".siamang-step-dot.is-active:nth-child(2)");
        await p.waitForTimeout(300);
        const seen = await p.evaluate(() => {
            const dot = document.querySelector(".siamang-step-dot");
            const b = dot.getBoundingClientRect();
            const drawn = getComputedStyle(dot, "::before");
            const card = document.querySelector(".sd-page").getBoundingClientRect();
            return {
                button: [Math.round(b.width), Math.round(b.height)],
                drawn: [drawn.width, drawn.height],
                // From the middle of the dot to the top of the page card: 24 px
                // under a 10 px dot, as before the buttons grew.
                toCard: Math.round(card.top - (b.top + b.height / 2)),
            };
        });
        const b = await p.locator(".siamang-step-dot").first().boundingBox();
        const x = b.x + b.width / 2 + off, y = b.y + b.height / 2;
        if (finger) await p.touchscreen.tap(x, y); else await p.mouse.click(x, y);
        await p.waitForTimeout(300);
        seen.after = await p.evaluate(() => document.querySelector(".sd-page__title").textContent);
        return seen;
    };
    const mouse = await dots(page, 9, false);
    const ctx = await page.context().browser().newContext({ hasTouch: true, viewport: { width: 390, height: 844 } });
    const phone = await ctx.newPage();
    await phone.goto(page.url());
    await phone.waitForSelector(".sd-page");
    const finger = await dots(phone, 8, true);
    await ctx.close();
    return { mouse, finger };
"""


def test_a_step_dot_is_a_target_of_24_px_and_draws_the_same_dot(tmp_path):
    """A respondent goes back with a step dot, and the dot was a 10 px
    target. Its button is 24 px now (32 px on a touch screen), the dot drawn
    in it is the same 10 px one, and neither it nor the page under it moved."""

    seen = run_in_browser(_scales_document(), _DOTS, tmp_path)
    assert seen["mouse"] == {
        "button": [24, 24],
        "drawn": ["10px", "10px"],
        "toCard": 29,
        "after": "Your visit",
    }
    assert seen["finger"] == {
        "button": [32, 32],
        "drawn": ["10px", "10px"],
        "toCard": 29,
        "after": "Your visit",
    }


def test_a_long_surveys_step_dots_narrow_under_a_finger_before_they_wrap(tmp_path):
    """Under a finger a dot's button is 32 px; on a long survey it narrows,
    down to 24 px and never less, before the row wraps, so fourteen pages keep
    one row on a 390 px phone and the page stays put; eighteen wrap."""

    def pages(count: int) -> dict[str, Any]:
        document = _scales_document()
        extra = [
            {
                "name": f"more{i}",
                "title": f"More {i}",
                "items": [_open_text(f"more{i}", f"Anything else ({i})?")],
            }
            for i in range(count - 3)
        ]
        document["pages"][3:3] = extra
        for i in range(count - 3):
            document["variables"][f"more{i}"] = {"scale": "nominal"}
        return document

    scenario = """
        const ctx = await page.context().browser().newContext({ hasTouch: true, viewport: { width: 390, height: 844 } });
        const phone = await ctx.newPage();
        await phone.goto(page.url());
        await phone.waitForSelector(".siamang-step-dot");
        const seen = await phone.evaluate(() => {
            const dots = [...document.querySelectorAll(".siamang-step-dot")];
            const first = dots[0].getBoundingClientRect();
            const card = document.querySelector(".sd-page").getBoundingClientRect();
            return {
                dots: dots.length,
                rows: new Set(dots.map((d) => Math.round(d.getBoundingClientRect().top))).size,
                least: Math.min(...dots.map((d) => d.getBoundingClientRect().width)) >= 24,
                height: Math.round(first.height),
                toCard: Math.round(card.top - (first.top + first.height / 2)),
            };
        });
        await ctx.close();
        return seen;
    """
    fourteen = run_in_browser(pages(14), scenario, tmp_path / "14")
    eighteen = run_in_browser(pages(18), scenario, tmp_path / "18")
    assert fourteen == {"dots": 14, "rows": 1, "least": True, "height": 32, "toCard": 29}
    assert eighteen["rows"] == 2 and eighteen["least"]


# ── A long scale on a narrow screen ──────────────────────────────────────────


def test_a_long_scale_is_cells_of_one_width_in_one_row_or_two_even_ones(tmp_path):
    """A 0–10 scale too wide for its row wrapped as flex items: 0–8 in one row
    and 9 and 10, twice as wide, in another. Its points are cells of one
    width: in one row where each keeps its least width (44 px, 40 px on a
    phone), else in two even rows (0–5, 6–10). That is measured on the scale,
    not on the window: an 8-point scale stays one row at 600 px, and a survey
    whose theme is 480 px wide wraps both at a desktop's width rather than
    squeeze their cells below 44 px. Five stars stay a row of their own."""

    def document(width: str | None = None) -> dict[str, Any]:
        doc = _scales_document()
        doc["variables"]["eight"] = {"scale": "ordinal"}
        doc["pages"][0]["items"].insert(
            2,
            {
                "type": "LikertScale",
                "id": "eight",
                "var": "eight",
                "text": "How was the music?",
                "points": 8,
            },
        )
        if width:
            doc["ui"]["width"] = width
        return doc

    rows = """
        const rows = () => page.evaluate(() => {
            const scales = [...document.querySelectorAll(".sd-rating__scale")];
            const layout = (scale) => {
                const byTop = {};
                for (const b of scale.children) {
                    const r = b.getBoundingClientRect();
                    (byTop[Math.round(r.top)] = byTop[Math.round(r.top)] || []).push(Math.round(r.width * 10) / 10);
                }
                const lines = Object.keys(byTop).map(Number).sort((a, b) => a - b).map((top) => byTop[top]);
                const widths = lines.flat();
                return { rows: lines.map((l) => l.length), equal: new Set(widths).size === 1, least: Math.min(...widths) };
            };
            const stars = new Set([...scales[0].children].map((b) => Math.round(b.getBoundingClientRect().top)));
            const [eight, eleven] = [layout(scales[1]), layout(scales[2])];
            return { eight: eight.rows, eleven: eleven.rows, equal: eight.equal && eleven.equal,
                     least: Math.min(eight.least, eleven.least), starRows: stars.size };
        });
    """
    scenario = (
        rows
        + """
        const seen = {};
        for (const width of [1440, 600, 390]) {
            await page.setViewportSize({ width, height: 900 });
            await page.waitForTimeout(100);
            seen[width] = await rows();
        }
        return seen;
    """
    )
    seen = run_in_browser(document(), scenario, tmp_path / "window")
    for width, least in (("1440", 44), ("600", 40), ("390", 40)):
        assert seen[width].pop("least") >= least, width
    assert seen == {
        "1440": {"eight": [8], "eleven": [11], "equal": True, "starRows": 1},
        "600": {"eight": [8], "eleven": [11], "equal": True, "starRows": 1},
        "390": {"eight": [4, 4], "eleven": [6, 5], "equal": True, "starRows": 1},
    }
    narrow = run_in_browser(
        document("480px"),
        rows
        + "await page.setViewportSize({ width: 1200, height: 900 }); await page.waitForTimeout(100); return rows();",
        tmp_path / "theme",
    )
    assert narrow.pop("least") >= 44
    assert narrow == {"eight": [4, 4], "eleven": [6, 5], "equal": True, "starRows": 1}


# ── Leaving the page ─────────────────────────────────────────────────────────

# A transport's own listener, put on the document before the runtime's: what
# the save held as the page was hidden. `hide()` hides the page as switching
# to another tab or locking the phone does.
_LEAVE = """
    window.__seen = [];
    document.addEventListener("visibilitychange", () => {
        if (document.visibilityState !== "hidden") return;
        const raw = localStorage.getItem("siamang_answers_t");
        window.__seen.push(raw ? JSON.parse(raw).answers : null);
    });
"""
_HIDE = """
    const hide = () => page.evaluate(() => {
        Object.defineProperty(document, "visibilityState", { configurable: true, get: () => "hidden" });
        document.dispatchEvent(new Event("visibilitychange"));
        delete document.visibilityState;
    });
    const seen = () => page.evaluate(() => window.__seen.slice(-1)[0]);
"""


def test_what_is_answered_just_before_the_page_is_hidden_is_in_its_save(tmp_path):
    """The save waits 2 s after the last answer (and a field's text 600 ms
    after its last key), and a transport reads it to send the partial response
    as the page is hidden or closed: whatever was answered in those seconds
    was not in it. The save waiting is written as the page is hidden, before
    the transport's own listener runs, with the text still in a field; a
    reload right after an answer offers to resume it."""

    document = _scales_document()
    document["pages"][1]["items"].append(_open_text("why", "Why?"))
    document["pages"][1]["items"].append(
        {"type": "NumericInput", "id": "cups", "var": "cups", "text": "How many cups a week?"}
    )
    document["variables"]["why"] = {"scale": "nominal"}
    document["variables"]["cups"] = {"scale": "ratio"}
    scenario = (
        _SCALES
        + _HIDE
        + _RELOAD
        + """
        const out = {};
        await page.locator(".sd-radio").nth(1).click();
        await scale(1).locator("[role=radio]").nth(8).click();
        await page.waitForTimeout(300);
        await hide();
        out.answered = await seen();
        await page.click(".sd-navigation__next-btn");
        await page.waitForSelector("input[type=number]");
        await page.locator(".sd-radio").first().click();
        await page.locator("input[type=number]").focus();
        await page.keyboard.type("3");
        await page.locator("input.sd-input:not([type=number])").pressSequentially("Late again");
        await page.waitForTimeout(100);
        await hide();
        const typed = await seen();
        out.typed = [typed.again, typed.why, typed.cups];
        await page.locator("input[type=number]").fill("4");
        await page.waitForTimeout(50);
        await page.evaluate(() => window.dispatchEvent(new PageTransitionEvent("pagehide", { persisted: false })));
        out.closed = await page.evaluate(() => JSON.parse(localStorage.getItem("siamang_answers_t")).answers.cups);
        // A reload a moment after an answer: the save was written as the page went.
        await page.locator(".sd-radio").nth(1).click();
        await reload(".siamang-resume-banner");
        await page.click("button:text-is('Resume')");
        await page.waitForSelector("input[type=number]");
        out.resumed = await page.evaluate(() => ({
            again: document.querySelector(".sd-item--checked .sd-choice-label").textContent,
            why: document.querySelector("input.sd-input:not([type=number])").value,
            cups: document.querySelector("input[type=number]").value,
        }));
        return out;
    """
    )
    out = run_in_browser(document, scenario, tmp_path, init=_LEAVE)
    assert out["answered"] == {"visit": 2, "nps": 8}
    assert out["typed"] == [1, "Late again", 3]
    assert out["closed"] == 4
    assert out["resumed"] == {"again": "No", "why": "Late again", "cups": "4"}


# ── An error that comes in as a question is left ─────────────────────────────


def test_a_press_on_the_next_question_lands_where_it_was_pressed(tmp_path):
    """Leaving a required question unanswered says so at once, and it was
    said as the mouse went down on the next question: the error came in above
    it and moved it down, the button came up somewhere else, and the click was
    lost. The check waits for the press to end, the click lands, and the
    error shows after it."""

    scenario = (
        _SCALES
        + """
        const pressAt = async (p, index) => {
            await p.evaluate(() => document.activeElement && document.activeElement.blur());
            await p.locator(".sd-page__title").click();
            await p.keyboard.press("Tab");
            const point = p.locator(".sd-rating__scale").nth(1).locator("[role=radio], button").nth(index);
            const b = await point.boundingBox();
            await p.mouse.move(b.x + b.width / 2, b.y + b.height - 6);
            await p.mouse.down();
            await p.waitForTimeout(80);
            const during = await p.locator(".sd-question__error").count();
            await p.mouse.up();
            await p.waitForTimeout(150);
            return { during, after: await p.locator(".sd-question__error").count() };
        };
        const mouse = await pressAt(page, 4);
        mouse.chosen = await checked(1);
        // The question left says, as a group, that it is required and why it
        // is invalid; the scale, not required, says neither.
        const group = (name) => page.getByRole("radiogroup", { name }).evaluate((g) => [
            g.getAttribute("aria-required"), g.getAttribute("aria-invalid"),
            g.getAttribute("aria-describedby") && document.getElementById(g.getAttribute("aria-describedby")).textContent,
        ]);
        const groups = {
            visit: await group("How often do you visit Example Cafe?"),
            nps: await group("How likely are you to recommend Example Cafe to a friend?"),
        };
        // A finger: the error waits for the tap's end too, and the tap lands.
        const ctx = await page.context().browser().newContext({ hasTouch: true, viewport: { width: 390, height: 844 } });
        const phone = await ctx.newPage();
        await phone.goto(page.url());
        await phone.waitForSelector(".sd-page");
        await phone.locator(".sd-page__title").click();
        await phone.keyboard.press("Tab");
        const cdp = await ctx.newCDPSession(phone);
        const point = phone.locator(".sd-rating__scale").nth(1).locator("[role=radio]").nth(7);
        const b = await point.boundingBox();
        const at = [{ x: b.x + b.width / 2, y: b.y + b.height - 6 }];
        await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: at });
        await phone.waitForTimeout(120);
        const touch = { during: await phone.locator(".sd-question__error").count() };
        await cdp.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
        await phone.waitForTimeout(800);
        touch.after = await phone.locator(".sd-question__error").count();
        touch.chosen = await phone.locator(".sd-rating__scale").nth(1).evaluate((s) => {
            const c = s.querySelector('[aria-checked="true"]');
            return c ? c.textContent.trim() : null;
        });
        await ctx.close();
        // A press whose end never came (let go in another window): the next
        // key ends it, and the question left by the keyboard says what is
        // missing at once.
        await page.reload();
        await page.waitForSelector(".sd-page");
        await page.locator(".sd-radio input").first().focus();
        await page.evaluate(() => window.dispatchEvent(new PointerEvent("pointerdown", { pointerType: "mouse", bubbles: true })));
        await page.keyboard.press("Tab");
        await page.keyboard.press("Tab");
        await page.waitForTimeout(150);
        const stuck = await page.locator(".sd-question__error").count();
        return { mouse, groups, touch, stuck };
    """
    )
    seen = run_in_browser(_scales_document(required=True), scenario, tmp_path)
    assert seen["mouse"] == {"during": 0, "after": 1, "chosen": "4"}
    assert seen["groups"] == {
        "visit": ["true", "true", "This question requires an answer."],
        "nps": [None, None, None],
    }
    assert seen["touch"] == {"during": 0, "after": 1, "chosen": "7"}
    assert seen["stuck"] == 1
