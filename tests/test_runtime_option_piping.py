"""Piping in what a respondent reads as the answers.

``{answer:x}`` / ``{var:x}`` / ``{label:x}`` fill in an option's label as they
do a question's title: in the runtime, at the moment it is shown, and nowhere
else — the answer stored is the option's code and the questionnaire, its
codebook and its exports keep the label as authored. The functions are called
in Node on the shipped bundle (``test_runtime_store.run_js``); the questions
are played in Chromium (``test_runtime_browser.run_in_browser``), every
display a choice has.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any

import pandas as pd
import pytest

from siamang.core import Option, Page, Questionnaire, SingleChoice, Variable, VariableMap
from siamang.data import SurveyData
from siamang.frontend.compiler.react import compile_react_payload
from siamang.io import export_file

from .test_runtime_browser import _FIXED_RANDOM, _NEXT, _STATE, _cmp, _var, run_in_browser
from .test_runtime_store import _BUNDLE, _STUBS, run_js

# ── In Node, on the bundle ────────────────────────────────────────────────────

# A brand question, then a plan whose options pipe the brand — and one that
# pipes the plan itself — as the compiler sends them (window.PAGES).
_PAGES = [
    {
        "name": "p1",
        "items": [
            {
                "id": "brand",
                "kind": "single",
                "title": "Brand?",
                "options": [{"code": 1, "label": "Acme"}, {"code": 2, "label": "Globex"}],
            },
            {
                "id": "plan",
                "kind": "single",
                "title": "Which {label:brand} plan?",
                "options": [
                    {"code": 1, "label": "{label:brand} Basic"},
                    {"code": 2, "label": "{label:brand} Pro"},
                    {"code": 3, "label": "Same as {label:plan}"},
                ],
                "otherSpecify": True,
                "otherCode": -66,
                "otherKey": "plan_other",
                "otherLabel": "Another {label:brand} plan ({answer:plan_other})",
            },
            {"id": "nick", "kind": "text", "title": "Nickname?"},
            {
                "id": "md",
                "kind": "maxdiff",
                "title": "Pick",
                "options": [{"code": 1, "label": "{label:brand} Plus"}],
                "taskVars": [["md_t1_best", "md_t1_worst"]],
                "versionVar": "md_version",
            },
        ],
    }
]


def _run(expression: str) -> Any:
    """``expression`` with the pages above in place (the label index is built
    from them the first time a placeholder is piped)."""

    return run_js(
        f"""(() => {{
          window.PAGES = {json.dumps(_PAGES)};
          const [brand, plan, nick, md] = window.PAGES[0].items;
          return ({expression});
        }})()"""
    )


def test_an_option_shows_the_answer_it_pipes_and_keeps_its_code():
    result = _run(
        """(() => {
          const answers = { brand: 2 };
          const pipe = optionPiper(plan, answers);
          return {
            labels: plan.options.map((o) => pipe(o.label)),
            codes: plan.options.map((o) => o.code),
            other: pipe(plan.otherLabel),
            authored: plan.options[1].label,
            unanswered: optionPiper(plan, {}).call(null, plan.options[0].label),
            empty: optionPiper(plan, { brand: "" }).call(null, plan.options[0].label),
          };
        })()"""
    )
    # The label shows the brand; its own question's placeholder, and the Other
    # text not typed yet, stay as written.
    assert result["labels"] == ["Globex Basic", "Globex Pro", "Same as {label:plan}"]
    assert result["other"] == "Another Globex plan ({answer:plan_other})"
    # The option itself is untouched: it still stores its code, and the label
    # the payload carries is the authored one.
    assert result["codes"] == [1, 2, 3]
    assert result["authored"] == "{label:brand} Pro"
    assert result["unanswered"] == result["empty"] == "{label:brand} Basic"


def test_an_option_never_pipes_its_own_question():
    """`{label:plan}` among plan's options, and the Other text it collects,
    would change under the respondent's hand: they stay as typed."""

    assert _run(
        """(() => {
          const answers = { brand: 1, plan: 3, plan_other: "mine" };
          const pipe = optionPiper(plan, answers);
          return [pipe(plan.options[2].label), pipe(plan.otherLabel)];
        })()"""
    ) == ["Same as {label:plan}", "Another Acme plan ({answer:plan_other})"]


def test_label_inserts_the_option_as_the_respondent_read_it():
    """A later "Why {label:plan}?" reads the plan's label piped, as it was
    shown. A respondent's own text is inserted as typed and never scanned."""

    result = _run(
        """[
          processPipedText("Why {label:plan}?", { brand: 2, plan: 2 }),
          processPipedText("Why {label:plan}?", { plan: 2 }),
          processPipedHtml("<p>{label:plan}</p>", { brand: 2, plan: 2 }),
          processPipedText("{label:plan}", { brand: 1, plan: { code: -66, text: "{answer:brand}" }, plan_other: "{answer:brand}" }),
          processPipedText("Hi {answer:nick}", { nick: "{label:brand}", brand: 1 }),
          processPipedText("Best: {label:md_t1_best}", { brand: 1, md_t1_best: 1 }),
        ]"""
    )
    assert result == [
        "Why Globex Pro?",
        # Brand not answered: the label's own placeholder stays, as in it.
        "Why {label:brand} Pro?",
        "<p>Globex Pro</p>",
        "{answer:brand}",
        "Hi {label:brand}",
        # A MaxDiff item is shown as written, so it is inserted as written.
        "Best: {label:brand} Plus",
    ]


def test_labels_that_pipe_each_other_end():
    """Two questions whose options pipe each other's answer (a forward
    reference the lint reports) still give a text: the label inserted is the
    one the respondent read, which stops where it would come back to its own
    question. A chain that does not come back stops a few levels deep."""

    result = run_js(
        """(() => {
          window.PAGES = [{ name: "p", items: [
            { id: "a", kind: "single", title: "A", options: [{ code: 1, label: "a of {label:b}" }] },
            { id: "b", kind: "single", title: "B", options: [{ code: 1, label: "b of {label:a}" }] },
            { id: "q1", kind: "single", title: "1", options: [{ code: 1, label: "q1 of {label:q2}" }] },
            { id: "q2", kind: "single", title: "2", options: [{ code: 1, label: "q2 of {label:q3}" }] },
            { id: "q3", kind: "single", title: "3", options: [{ code: 1, label: "q3 of {label:q4}" }] },
            { id: "q4", kind: "single", title: "4", options: [{ code: 1, label: "q4 of {label:q5}" }] },
            { id: "q5", kind: "single", title: "5", options: [{ code: 1, label: "q5" }] },
          ] }];
          const [a] = window.PAGES[0].items;
          const answers = { a: 1, b: 1, q1: 1, q2: 1, q3: 1, q4: 1, q5: 1 };
          return [
            processPipedText("{label:a}", answers),
            optionPiper(a, answers)(a.options[0].label),
            processPipedText("{label:q1}", answers),
          ];
        })()"""
    )
    assert result == [
        "a of b of {label:a}",
        "a of b of {label:a}",
        "q1 of q2 of q3 of q4 of {label:q5}",
    ]


def test_an_option_does_not_show_its_own_answer_through_another_label():
    """A's option pipes B's label, and B's label pipes A's answer (or the
    Other text A collects): in A's option that placeholder stays as typed, as
    it would in A's option itself. In B's option, and in a title, it pipes."""

    result = run_js(
        """(() => {
          window.PAGES = [{ name: "p", items: [
            { id: "a", kind: "single", title: "A", otherSpecify: true, otherCode: -66, otherKey: "a_other",
              options: [{ code: 1, label: "a1 {label:b}" }, { code: 2, label: "a2" }] },
            { id: "b", kind: "single", title: "B",
              options: [{ code: 1, label: "b1 {label:a}" }, { code: 2, label: "b2 {answer:a_other}" }] },
          ] }];
          const [a, b] = window.PAGES[0].items;
          const answers = { a: 2, b: 1 };
          const typed = { a: { code: -66, text: "mine" }, a_other: "mine", b: 2 };
          return {
            a: optionPiper(a, answers)(a.options[0].label),
            b: optionPiper(b, answers)(b.options[0].label),
            title: processPipedText("Why {label:b}?", answers),
            aTyped: optionPiper(a, typed)(a.options[0].label),
            bTyped: optionPiper(b, typed)(b.options[1].label),
          };
        })()"""
    )
    assert result == {
        "a": "a1 b1 {label:a}",
        "b": "b1 a2",
        "title": "Why b1 a2?",
        "aTyped": "a1 b2 {answer:a_other}",
        "bTyped": "b2 mine",
    }


def test_a_question_whose_answers_do_not_pipe_shows_them_with_no_scan():
    """The work is done once per question: whether any of its answers pipes.
    Most do not, and their labels go through the identity — for a list of a
    few thousand options as for three."""

    result = run_js(
        """(() => {
          const options = Array.from({ length: 5000 }, (_, i) => ({ code: i, label: "Option " + i }));
          const plain = { id: "big", kind: "single", title: "Pick", options };
          const first = pipingOf(plain);
          const piped = { id: "big2", kind: "single", title: "Pick",
                          options: options.map((o) => ({ ...o, label: o.label + " of {answer:x}" })) };
          const pipe = optionPiper(piped, { x: "X" });
          const started = Date.now();
          let last = "";
          for (let render = 0; render < 20; render++) for (const o of piped.options) last = pipe(o.label);
          return {
            identity: optionPiper(plain, { x: 1 }) === keepText,
            cached: pipingOf(plain) === first,
            options: first.options,
            last,
            ms: Date.now() - started,
          };
        })()"""
    )
    assert result["identity"] and result["cached"] and result["options"] is False
    assert result["last"] == "Option 4999 of X"
    # 100,000 labels piped: generous, so a busy machine passes; it takes a few
    # tens of milliseconds.
    assert result["ms"] < 2000


def _memo(expression: str) -> Any:
    """``expression`` where ``Question.eq`` is the memo's comparison."""

    stubs = _STUBS.replace("memo: (f) => f,", "memo: (f, eq) => Object.assign(f, { eq }),")
    assert stubs != _STUBS
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    result = subprocess.run(
        [node, "-e", stubs, "--", str(_BUNDLE), expression],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_a_question_is_drawn_again_when_an_answer_its_options_pipe_changes():
    """The memo kept a question as it was unless its title or hint piped or
    an option had a condition: an option's label went on reading the answer
    it was first drawn with."""

    result = _memo(
        """(() => {
          const make = (q) => ({ q, qId: q.id, value: undefined, answers: { brand: 1 } });
          const changed = (props) => ({ ...props, answers: { brand: 2 } });
          const same = (props) => ({ ...props, answers: props.answers });
          const cases = {
            options: { id: "a", kind: "single", title: "A", options: [{ code: 1, label: "{label:brand} One" }] },
            matrix: { id: "m", kind: "matrix", title: "M", columns: ["Like {label:brand}"], rows: [{ id: "r", label: "R" }] },
            scale: { id: "s", kind: "likert", title: "S", points: 5, leftLabel: "Worse than {label:brand}" },
            title: { id: "t", kind: "single", title: "About {label:brand}", options: [{ code: 1, label: "One" }] },
            plain: { id: "p", kind: "single", title: "Plain", options: [{ code: 1, label: "One" }] },
            maxdiff: { id: "d", kind: "maxdiff", title: "D", options: [{ code: 1, label: "{label:brand} Plus" }] },
          };
          const out = {};
          for (const [name, q] of Object.entries(cases)) {
            const props = make(q);
            out[name] = { changed: Question.eq(props, changed(props)), same: Question.eq(props, same(props)) };
          }
          return out;
        })()"""
    )
    # eq true: kept as drawn; false: drawn again.
    assert result["options"] == {"changed": False, "same": True}
    assert result["matrix"] == {"changed": False, "same": True}
    assert result["scale"] == {"changed": False, "same": True}
    assert result["title"] == {"changed": False, "same": True}
    assert result["plain"] == {"changed": True, "same": True}
    # A MaxDiff's items are not piped, so they do not ask for it.
    assert result["maxdiff"] == {"changed": True, "same": True}


# ── What is stored and exported ───────────────────────────────────────────────


def _plan_variables() -> list[Variable]:
    return [
        Variable("brand", "nominal", label="Brand", labels={1: "Acme", 2: "Globex"}),
        Variable(
            "plan",
            "nominal",
            label="Plan",
            labels={1: "{label:brand} Basic", 2: "{label:brand} Pro"},
        ),
    ]


def test_the_compiler_and_the_exports_keep_the_label_as_authored(tmp_path):
    """Piping is the respondent's view: the payload carries the label with its
    placeholder, and the codebook and a data file label the code with it."""

    brand, plan = _plan_variables()
    choices = [Option(1, "{label:brand} Basic"), Option(2, "{label:brand} Pro")]
    survey = Questionnaire(
        title="T",
        pages=[
            Page("first", items=[SingleChoice("Brand?", var=brand)]),
            Page("second", items=[SingleChoice("Plan?", var=plan, choices=choices)]),
        ],
    )
    item = compile_react_payload(survey)["PAGES"][1]["items"][0]
    assert [o["label"] for o in item["options"]] == ["{label:brand} Basic", "{label:brand} Pro"]
    assert not [w for w in survey.lint() if w.code.startswith("PIPE_")]

    variables = VariableMap()
    for variable in (brand, plan):
        variables.add(variable)
    data = SurveyData(frame=pd.DataFrame({"brand": [2, 1], "plan": [2, 1]}), variables=variables)
    dictionary = export_file(data, tmp_path / "codebook.json").read_text(encoding="utf-8")
    assert "{label:brand} Pro" in dictionary and "Globex Pro" not in dictionary
    pyreadstat = pytest.importorskip("pyreadstat")
    _frame, meta = pyreadstat.read_sav(str(export_file(data, tmp_path / "survey.sav")))
    assert meta.variable_value_labels["plan"] == {
        1.0: "{label:brand} Basic",
        2.0: "{label:brand} Pro",
    }


# ── In the browser ────────────────────────────────────────────────────────────


def _labels(*labels: str, start: int = 1) -> list[dict[str, Any]]:
    return [{"code": code, "label": label} for code, label in enumerate(labels, start=start)]


def _choices_document() -> dict[str, Any]:
    """One page: a brand, then a question of every kind whose answers pipe it
    — options from the codebook and from choices, an option's picture, Other,
    an exclusive None, a ranking, a matrix's statements, headers and N/A, a
    scale's ends and N/A, a dropdown with Other — and one that pipes an answer
    typed on the page. The next page pipes the plan."""

    brand = _labels("Acme", "Globex")
    return {
        "schema_version": "1.0",
        "title": "Plans",
        "variables": {
            "brand": {"scale": "nominal", "labels": brand},
            "nick": {"scale": "nominal", "dtype": "str"},
            "plan": {
                "scale": "nominal",
                "labels": _labels(
                    "{label:brand} Basic", "{label:brand} Pro", "Same as {label:plan}"
                ),
            },
            "tier": {"scale": "nominal", "labels": _labels("One", "Two")},
            "addons": {
                "scale": "nominal",
                "labels": [
                    *_labels("{label:brand} Cloud", "{label:brand} Care"),
                    {"code": 9, "label": "No {label:brand} add-on"},
                ],
            },
            "order": {"scale": "nominal", "labels": _labels("Price", "Service")},
            "rate_a": {
                "scale": "ordinal",
                "labels": _labels("Not like {label:brand}", "Like {label:brand}"),
            },
            "rate_b": {
                "scale": "ordinal",
                "labels": _labels("Not like {label:brand}", "Like {label:brand}"),
            },
            "sat": {"scale": "ordinal", "labels": _labels("1", "2", "3", "4", "5")},
            "shop": {"scale": "nominal", "labels": _labels("Shop of {answer:nick}")},
            "store": {"scale": "nominal", "labels": _labels("North", "South")},
            "again": {
                "scale": "nominal",
                "labels": _labels("{label:plan} again", "Something else"),
            },
        },
        "pages": [
            {
                "name": "p1",
                "items": [
                    {"type": "SingleChoice", "id": "brand", "var": "brand", "text": "Brand?"},
                    {"type": "OpenText", "id": "nick", "var": "nick", "text": "Nickname?"},
                    {
                        "type": "SingleChoice",
                        "id": "plan",
                        "var": "plan",
                        "text": "Which {label:brand} plan?",
                        "other_specify": True,
                        "metadata": {"other_label": "Another {label:brand} plan"},
                        "choices": [
                            {
                                "code": 1,
                                "label": "{label:brand} Basic",
                                "media": {
                                    "kind": "image",
                                    "url": "basic.png",
                                    "alt": "The {label:brand} Basic box",
                                    "caption": "Boxed by {label:brand}",
                                },
                            },
                            {"code": 2, "label": "{label:brand} Pro"},
                            {"code": 3, "label": "Same as {label:plan}"},
                        ],
                    },
                    {
                        "type": "SingleChoice",
                        "id": "tier",
                        "var": "tier",
                        "text": "Tier?",
                        "display": "buttons",
                        "choices": _labels("{label:brand} One", "{label:brand} Two"),
                    },
                    {
                        "type": "MultiChoice",
                        "id": "addons",
                        "var": "addons",
                        "text": "Add-ons?",
                        "exclusive": [9],
                    },
                    {
                        "type": "Ranking",
                        "id": "order",
                        "var": "order",
                        "text": "Rank",
                        "choices": _labels("{label:brand} price", "{label:brand} service"),
                    },
                    {
                        "type": "Matrix",
                        "id": "rate",
                        "text": "About {label:brand}",
                        "var": ["rate_a", "rate_b"],
                        "subquestions": ["{label:brand} is fair", "{label:brand} is fast"],
                        "na_option": "Never used {label:brand}",
                    },
                    {
                        "type": "LikertScale",
                        "id": "sat",
                        "var": "sat",
                        "text": "Satisfied?",
                        "points": 5,
                        "left_label": "Worse than {label:brand}",
                        "right_label": "Better than {label:brand}",
                        "na_option": "No {label:brand} yet",
                    },
                    {"type": "SingleChoice", "id": "shop", "var": "shop", "text": "Shop?"},
                    {
                        "type": "SingleChoice",
                        "id": "store",
                        "var": "store",
                        "text": "Which {label:brand} store?",
                        "display": "dropdown",
                        "other_specify": True,
                        "metadata": {"other_label": "Another {label:brand} store"},
                        "choices": _labels("{label:brand} North", "{label:brand} South"),
                    },
                ],
            },
            {
                "name": "p2",
                "title": "About {label:plan}",
                "items": [
                    {"type": "SingleChoice", "id": "again", "var": "again", "text": "Again?"}
                ],
            },
            {"name": "done", "kind": "final", "title": "Thanks"},
        ],
    }


# What each question shows as its answers, and what names them to a screen
# reader: the group's name, a matrix cell's, an image's alt text.
_READ = """
    const read = () => page.evaluate(() => {
        const slot = (id) => document.querySelector(`.sd-question-slot[data-qid="${id}"]`);
        const all = (id, sel) => Array.from(slot(id).querySelectorAll(sel));
        const text = (id, sel) => all(id, sel).map((e) => e.textContent);
        const attr = (id, sel, name) => all(id, sel).map((e) => e.getAttribute(name));
        return {
            plan: text("plan", ".sd-choice-label"),
            planGroup: attr("plan", "[role=radiogroup]", "aria-label"),
            planAlt: attr("plan", "img", "alt"),
            planCaption: text("plan", "figcaption"),
            tier: text("tier", ".sd-choice-label"),
            addons: text("addons", ".sd-choice-label"),
            order: text("order", ".sd-ranking__label"),
            rateHead: text("rate", "thead th"),
            rateRows: text("rate", "tbody td:first-child"),
            rateCells: attr("rate", "button.sd-matrix__cell", "aria-label"),
            rateCards: text("rate", ".sd-matrix__col-label"),
            rateGroup: attr("rate", "table", "aria-label"),
            sat: text("sat", ".sd-rating__labels span"),
            satNa: text("sat", ".sd-rating__na .sd-choice-label"),
            shop: text("shop", ".sd-choice-label"),
            shopMarkup: all("shop", ".sd-choice-label *").length,
        };
    });
    const radio = (name) => page.getByRole("radio", { name, exact: true });
    // A choice's input sits under its drawn circle or box: it is checked
    // through the label, as a click on it does.
    const choose = (locator) => locator.check({ force: true });
"""


def test_every_display_shows_the_answer_its_options_pipe(tmp_path):
    """Before the brand is answered the placeholders stay as typed; once it
    is, every option on the same page that pipes it reads it — and again when
    it changes — in its text and its accessible name alike. The stored
    answers are the codes."""

    scenario = (
        _READ
        + """
        const before = await read();
        await choose(radio("Globex"));
        await page.waitForTimeout(100);
        const globex = await read();
        const tree = await page.locator("main").ariaSnapshot();
        const names = {
            pro: await radio("Globex Pro").count(),
            other: await radio("Another Globex plan").count(),
            basic: await radio("Globex Basic Boxed by Globex").count(),
            cloud: await page.getByRole("checkbox", { name: "Globex Cloud", exact: true }).count(),
            cell: await page.getByRole("button", { name: "Globex is fair: Like Globex", exact: true }).count(),
            group: await page.getByRole("radiogroup", { name: "Which Globex plan?", exact: true }).count(),
        };

        // A respondent's own text is text: no markup reaches the label.
        await page.fill('.sd-question-slot[data-qid="nick"] input', "<b>bold</b>");
        await page.locator('.sd-question-slot[data-qid="nick"] input').blur();
        await page.waitForTimeout(100);
        const typed = await read();

        await choose(radio("Globex Pro"));
        await choose(radio("Globex One"));
        await choose(page.getByRole("checkbox", { name: "Globex Cloud", exact: true }));
        await page.locator(".sd-ranking__item.is-unranked", { hasText: "Globex service" }).click();
        await page.locator(".sd-ranking__item.is-unranked", { hasText: "Globex price" }).click();
        await page.getByRole("button", { name: "Globex is fair: Like Globex", exact: true }).click();
        await page.getByRole("button", { name: "Globex is fast: Not like Globex", exact: true }).click();
        await page.locator(".sd-rating__scale button").nth(3).click();
        await choose(radio("Shop of <b>bold</b>"));

        // The dropdown: its list, its search and its button go by the piped label.
        const dropdown = '.sd-question-slot[data-qid="store"]';
        const trigger = dropdown + " .siamang-search-dropdown__trigger";
        await page.click(trigger);
        const search = dropdown + " .siamang-search-dropdown__search";
        const listed = async (text) => {
            await page.fill(search, text);
            return page.$$eval(dropdown + " [role=option]", (os) => os.map((o) => o.textContent));
        };
        const store = {
            all: await listed(""),
            globex: await listed("globex"),
            brand: await listed("brand"),
            listbox: await page.getAttribute(dropdown + " [role=listbox]", "aria-label"),
            combobox: await page.getAttribute(search, "aria-label"),
            south: await listed("south"),
        };
        await page.keyboard.press("Enter");
        store.chosen = await page.textContent(trigger);

        // The brand changes: the labels follow it, and the answers stay.
        await choose(radio("Acme"));
        await page.waitForTimeout(100);
        const acme = await read();
        store.acme = await page.textContent(trigger);
        const checked = await page.$$eval("input:checked", (is) => is.map((i) =>
            (i.closest("label") || i).textContent));
    """
        + _NEXT
        + """
        const second = {
            title: await page.textContent(".sd-page__title"),
            options: await page.$$eval(".sd-choice-label", (ls) => ls.map((l) => l.textContent)),
        };
        await choose(radio("Acme Pro again"));
    """
        + _NEXT
        + _STATE.replace(
            "return {",
            "return { before, globex, tree, names, typed, store, acme, checked, second,",
        )
    )
    state = run_in_browser(_choices_document(), scenario, tmp_path)
    before, globex, acme = state["before"], state["globex"], state["acme"]

    # Unanswered: as typed, the group's name too.
    assert before["plan"] == [
        "{label:brand} Basic",
        "{label:brand} Pro",
        "Same as {label:plan}",
        "Another {label:brand} plan",
    ]
    assert before["planGroup"] == ["Which {label:brand} plan?"]
    assert before["sat"] == ["Worse than {label:brand}", "Better than {label:brand}"]
    assert before["rateRows"] == ["{label:brand} is fair", "{label:brand} is fast"]

    # Answered on the same page: every display reads it at once.
    assert globex["plan"] == [
        "Globex Basic",
        "Globex Pro",
        "Same as {label:plan}",
        "Another Globex plan",
    ]
    assert globex["planGroup"] == ["Which Globex plan?"]
    assert globex["planAlt"] == ["The Globex Basic box"]
    assert globex["planCaption"] == ["Boxed by Globex"]
    assert globex["tier"] == ["Globex One", "Globex Two"]
    assert globex["addons"] == ["Globex Cloud", "Globex Care", "No Globex add-on"]
    assert globex["order"] == ["Globex price", "Globex service"]
    assert globex["rateHead"] == ["", "Not like Globex", "Like Globex", "Never used Globex"]
    assert globex["rateRows"] == ["Globex is fair", "Globex is fast"]
    assert globex["rateCells"] == [
        f"Globex is {row}: {column}"
        for row in ("fair", "fast")
        for column in ("Not like Globex", "Like Globex", "Never used Globex")
    ]
    assert globex["rateCards"] == ["Not like Globex", "Like Globex", "Never used Globex"] * 2
    assert globex["rateGroup"] == ["About Globex"]
    assert globex["sat"] == ["Worse than Globex", "Better than Globex"]
    assert globex["satNa"] == ["No Globex yet"]

    # The accessible names a screen reader reads are the piped ones, and no
    # placeholder is left in the page's tree but the one an option has of its
    # own question.
    assert state["names"] == {"pro": 1, "other": 1, "basic": 1, "cloud": 1, "cell": 1, "group": 1}
    assert 'img "The Globex Basic box"' in state["tree"]
    assert "{label:brand}" not in state["tree"]
    assert "Same as {label:plan}" in state["tree"]

    assert state["typed"]["shop"] == ["Shop of <b>bold</b>"]
    assert state["typed"]["shopMarkup"] == 0

    store = state["store"]
    assert store["all"] == ["Globex North", "Globex South", "Another Globex store"]
    assert store["globex"] == store["all"]
    assert store["brand"] == []
    assert store["south"] == ["Globex South"]
    assert store["listbox"] == store["combobox"] == "Which Globex store?"
    assert store["chosen"] == "Globex South"

    # Acme now: the labels follow, the choices made stay chosen.
    assert acme["plan"] == ["Acme Basic", "Acme Pro", "Same as {label:plan}", "Another Acme plan"]
    assert acme["order"] == ["Acme service", "Acme price"]
    assert acme["rateRows"] == ["Acme is fair", "Acme is fast"]
    assert store["acme"] == "Acme South"
    assert "Acme Pro" in state["checked"] and "Acme One" in state["checked"]

    # The next page reads the plan as it was shown, in its title and options.
    assert state["second"] == {
        "title": "About Acme Pro",
        "options": ["Acme Pro again", "Something else"],
    }

    # What is stored is the codes.
    [submitted] = state["submitted"]
    assert {
        key: submitted.get(key)
        for key in (
            "brand",
            "nick",
            "plan",
            "tier",
            "addons",
            "order",
            "rate_a",
            "rate_b",
            "sat",
            "shop",
            "store",
            "again",
        )
    } == {
        "brand": 1,
        "nick": "<b>bold</b>",
        "plan": 2,
        "tier": 1,
        "addons": [1],
        "order": [2, 1],
        "rate_a": 2,
        "rate_b": 1,
        "sat": 4,
        "shop": 1,
        "store": 2,
        "again": 1,
    }


# A payload the compiler does not write but the runtime draws: a picture
# choice (kind "image") and a slider's labels.
_PICTURES_AND_SLIDER = """
    let pages;
    Object.defineProperty(window, "PAGES", {
        configurable: true,
        get() { return pages; },
        set(value) {
            for (const page of value) for (const q of page.items || []) {
                if (q.id === "pic") q.kind = "image";
                if (q.id === "level") q.labels = { 0: "No {label:brand}", 2: "All {label:brand}" };
            }
            pages = value;
        },
    });
"""


def _pictures_document() -> dict[str, Any]:
    picture = lambda code, color: {  # noqa: E731
        "code": code,
        "label": "{label:brand} " + color,
        "media": {"kind": "image", "url": f"{color}.png"},
    }
    md_items = _labels(*("{label:brand} " + item for item in ("Plus", "Basic", "Pro", "Max")))
    md_vars = {
        f"md_t1_{side}": {"scale": "nominal", "labels": md_items} for side in ("best", "worst")
    }
    return {
        "schema_version": "1.0",
        "title": "Pictures",
        "variables": {
            "brand": {"scale": "nominal", "labels": _labels("Acme", "Globex")},
            "pic": {"scale": "nominal", "labels": _labels("red", "blue")},
            "level": {"scale": "interval", "valid_range": [0, 2]},
            **md_vars,
            "md_version": {"scale": "nominal"},
            "cj_t1": {"scale": "nominal"},
            "cj_version": {"scale": "nominal"},
        },
        "pages": [
            {
                "name": "p1",
                "items": [
                    {"type": "SingleChoice", "id": "brand", "var": "brand", "text": "Brand?"},
                    {
                        "type": "SingleChoice",
                        "id": "pic",
                        "var": "pic",
                        "text": "Which {label:brand} color?",
                        "choices": [picture(1, "red"), picture(2, "blue")],
                    },
                    {
                        "type": "NumericInput",
                        "id": "level",
                        "var": "level",
                        "text": "How much?",
                        "display": "slider",
                    },
                    {
                        "type": "MaxDiff",
                        "id": "md",
                        "text": "Best and worst for {label:brand}",
                        "var": ["md_t1_best", "md_t1_worst", "md_version"],
                        "per_task": 3,
                        "tasks": 1,
                        "versions": 1,
                        "best_label": "Best for {label:brand}",
                    },
                    {
                        "type": "Conjoint",
                        "id": "cj",
                        "text": "Which {label:brand} offer?",
                        "var": ["cj_t1", "cj_version"],
                        "attributes": [
                            {
                                "name": "price",
                                "label": "{label:brand} price",
                                "levels": _labels("{label:brand} low", "High"),
                            },
                            {"name": "size", "levels": _labels("Small", "Large")},
                        ],
                        "alternatives": 2,
                        "tasks": 1,
                        "versions": 1,
                    },
                ],
            },
            {"name": "done", "kind": "final", "title": "Thanks"},
        ],
    }


def test_a_picture_choice_and_a_slider_pipe_and_a_design_does_not(tmp_path):
    """A picture's label and alt text and a slider's labels read the brand;
    a MaxDiff's items and a Conjoint's levels are its design and are shown as
    written — only their titles pipe."""

    scenario = (
        """
        const read = () => page.evaluate(() => ({
            alts: Array.from(document.querySelectorAll(".sd-image-choice__img")).map((i) => i.alt),
            pictures: Array.from(document.querySelectorAll(".sd-image-choice__label")).map((l) => l.textContent),
            group: document.querySelector(".sd-image-choices").getAttribute("aria-label"),
            ticks: Array.from(document.querySelectorAll(".siamang-slider__tick")).map((t) => t.textContent),
            items: Array.from(document.querySelectorAll("td.sd-maxdiff__item")).map((t) => t.textContent),
            best: document.querySelector(".sd-maxdiff__side").textContent,
            picks: Array.from(document.querySelectorAll(".sd-maxdiff__pick")).map((b) => b.getAttribute("aria-label")),
            levels: Array.from(document.querySelectorAll(".sd-conjoint__grid th, .sd-conjoint__grid td")).map((t) => t.textContent),
            titles: Array.from(document.querySelectorAll(".sd-question__title")).map((t) => t.textContent),
        }));
        const before = await read();
        await page.getByRole("radio", { name: "Globex", exact: true }).check({ force: true });
        await page.waitForTimeout(100);
        const after = await read();
        await page.getByRole("button", { name: "Globex blue" }).click();
        await page.fill(".siamang-slider__input", "2");
    """
        + _NEXT
        + _STATE.replace("return {", "return { before, after,")
    )
    state = run_in_browser(_pictures_document(), scenario, tmp_path, init=_PICTURES_AND_SLIDER)
    before, after = state["before"], state["after"]
    assert before["alts"] == before["pictures"] == ["{label:brand} red", "{label:brand} blue"]
    assert after["alts"] == after["pictures"] == ["Globex red", "Globex blue"]
    assert after["group"] == "Which Globex color?"
    assert before["ticks"] == ["No {label:brand}", "1", "All {label:brand}"]
    assert after["ticks"] == ["No Globex", "1", "All Globex"]
    # The design, as written; the titles, piped.
    assert len(after["items"]) == 3
    assert all(item.startswith("{label:brand} ") for item in after["items"])
    assert after["best"] == "Best for {label:brand}"
    assert f"Best for {{label:brand}}: {after['items'][0]}" in after["picks"]
    assert "{label:brand} price" in after["levels"] and "{label:brand} low" in after["levels"]
    assert any("Best and worst for Globex" in t for t in after["titles"])
    assert any("Which Globex offer?" in t for t in after["titles"])
    # The picture and the slider store their codes.
    [submitted] = state["submitted"]
    assert (submitted["brand"], submitted["pic"], submitted["level"]) == (2, 2, 2)


def _order_and_conditions_document() -> dict[str, Any]:
    """A brand; a question whose options are shuffled and pipe it; one whose
    second option pipes it and is shown only for the second brand. The next
    page's options pipe it too."""

    flavors = ("Apple", "Berry", "Cherry", "Date", "Elder", "Fig")
    return {
        "schema_version": "1.0",
        "title": "Flavors",
        "variables": {
            "brand": {"scale": "nominal", "labels": _labels("Acme", "Globex")},
            "flavor": {
                "scale": "nominal",
                "labels": _labels(*("{label:brand} " + flavor for flavor in flavors)),
            },
            "where": {"scale": "nominal", "labels": _labels("Anywhere", "Only at {label:brand}")},
            "again": {"scale": "nominal", "labels": _labels("{label:brand} again", "Not again")},
        },
        "pages": [
            {
                "name": "p1",
                "items": [
                    {"type": "SingleChoice", "id": "brand", "var": "brand", "text": "Brand?"},
                    {
                        "type": "SingleChoice",
                        "id": "flavor",
                        "var": "flavor",
                        "text": "Flavor?",
                        "randomize": True,
                    },
                    {
                        "type": "SingleChoice",
                        "id": "where",
                        "var": "where",
                        "text": "Where?",
                        "choices": [
                            {"code": 1, "label": "Anywhere"},
                            {
                                "code": 2,
                                "label": "Only at {label:brand}",
                                "show_if": _cmp("=", _var("brand"), 2),
                            },
                        ],
                    },
                ],
            },
            {
                "name": "p2",
                "items": [
                    {"type": "SingleChoice", "id": "again", "var": "again", "text": "Again?"}
                ],
            },
            {"name": "done", "kind": "final", "title": "Thanks"},
        ],
    }


def test_a_shuffled_a_conditional_and_a_later_option_pipe(tmp_path):
    """Options shuffled for the respondent keep their order and read the
    brand once it is chosen; an option shown on a condition on the brand
    appears with the brand in its label; an option on the next page reads the
    brand chosen again after going back. The answers stored are the codes."""

    scenario = (
        """
        const labels = (id) => page.$$eval(
            `.sd-question-slot[data-qid="${id}"] .sd-choice-label`,
            (ls) => ls.map((l) => l.textContent));
        const radio = (name) => page.getByRole("radio", { name, exact: true });
        const choose = (locator) => locator.check({ force: true });
        const settle = () => page.waitForTimeout(100);
        const before = { flavor: await labels("flavor"), where: await labels("where") };
        await choose(radio("Globex"));
        await settle();
        const globex = { flavor: await labels("flavor"), where: await labels("where") };
        await choose(radio("Globex Cherry"));
        await choose(radio("Only at Globex"));
    """
        + _NEXT
        + """
        const second = await labels("again");
        await page.click(".sd-navigation__prev-btn");
        await page.waitForTimeout(250);
        await choose(radio("Acme"));
        await settle();
        const acme = { flavor: await labels("flavor"), where: await labels("where") };
        await choose(radio("Anywhere"));
    """
        + _NEXT
        + """
        const back = await labels("again");
        await choose(radio("Acme again"));
    """
        + _NEXT
        + _STATE.replace("return {", "return { before, globex, second, acme, back,")
    )
    state = run_in_browser(_order_and_conditions_document(), scenario, tmp_path, init=_FIXED_RANDOM)
    before, globex, acme = state["before"], state["globex"], state["acme"]
    authored = ["{label:brand} " + f for f in ("Apple", "Berry", "Cherry", "Date", "Elder", "Fig")]

    # Shuffled, and the order stays as the labels fill in and change.
    assert sorted(before["flavor"]) == authored and before["flavor"] != authored
    assert globex["flavor"] == [f.replace("{label:brand}", "Globex") for f in before["flavor"]]
    assert acme["flavor"] == [f.replace("{label:brand}", "Acme") for f in before["flavor"]]

    # The conditional option appears with the brand in its label.
    assert before["where"] == ["Anywhere"]
    assert globex["where"] == ["Anywhere", "Only at Globex"]
    assert acme["where"] == ["Anywhere"]

    # The next page reads the brand as it is now.
    assert state["second"] == ["Globex again", "Not again"]
    assert state["back"] == ["Acme again", "Not again"]

    [submitted] = state["submitted"]
    assert {key: submitted.get(key) for key in ("brand", "flavor", "where", "again")} == {
        "brand": 1,
        "flavor": 3,
        "where": 1,
        "again": 1,
    }
