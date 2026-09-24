"""The key an answer is stored under.

A single-variable question's answer is stored under its *variable* — the
column the codebook describes and the name every condition, quota and
``{answer:…}`` reads — not under the author-facing question id. The two come
apart when an id is edited apart from its variable (id ``q1``, variable
``nps_1``), in an imported document and in older documents, and when the
runtime keyed answers by id nothing built on the variable ever fired.
"""

from __future__ import annotations

import pytest

from siamang.core import (
    Block,
    Matrix,
    MultiChoice,
    NumericInput,
    OpenText,
    Option,
    Page,
    Questionnaire,
    Script,
    SingleChoice,
    Variable,
)
from siamang.core.question import question_fallback_id, question_output_name
from siamang.frontend.compiler.react import compile_react_payload
from siamang.model import from_document, to_document
from siamang.model.scripts import (
    rewrite_answer_keys,
    script_for_runtime,
    stale_answer_key_references,
)

AGREE = {1: "Agree", 2: "Disagree"}


def _nps_document(**extra) -> dict:
    """An NPS question whose id was edited apart from its variable: id `q1`,
    variable `nps_1`, and a page gated on the variable."""

    return {
        "schema_version": "1.0",
        "title": "NPS",
        "variables": {
            "nps_1": {
                "scale": "ordinal",
                "label": "NPS",
                "labels": {str(i): str(i) for i in range(11)},
            },
            "why": {"scale": "nominal", "label": "Why"},
        },
        "pages": [
            {
                "name": "p1",
                "items": [
                    {"type": "SingleChoice", "id": "q1", "var": "nps_1", "text": "How likely?"}
                ],
            },
            {
                "name": "p2",
                "show_if": {
                    "type": "expression",
                    "op": "<=",
                    "left": {"type": "var", "name": "nps_1"},
                    "right": 6,
                },
                "items": [{"type": "OpenText", "id": "q2", "var": "why", "text": "Why?"}],
            },
        ],
        **extra,
    }


def _items(payload: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for page in payload["PAGES"]:
        for item in page.get("items", []):
            out[item["id"]] = item
        for block in page.get("blocks", []):
            for item in block.get("items", []):
                out[item["id"]] = item
    return out


def test_the_answer_is_stored_under_the_variable_the_condition_reads():
    loaded = from_document(_nps_document())
    loaded.survey.validate()
    payload = compile_react_payload(loaded.survey)

    item = payload["PAGES"][0]["items"][0]
    assert item["id"] == "nps_1", "the answer key is the variable"
    assert item["qid"] == "q1", "design mode still addresses the question by its id"
    gate = payload["PAGES"][1]["showIf"]
    assert gate == {"deps": ["nps_1"], "fn": '(a["nps_1"]<=6)'}
    assert gate["deps"] == [item["id"]], "the condition reads the key the answer is stored under"


def test_the_document_is_not_rewritten_to_get_there():
    """The fix is in what the compiler hands the runtime, not in the document:
    `id` stays the author's, and no `name` is invented — a Studio Save and
    the generated .py see the document the author wrote."""

    document = _nps_document()
    loaded = from_document(document)
    question = loaded.survey.all_questions()[0]
    assert question.id == "q1" and question.name is None
    item = to_document(loaded.survey, loaded.options)["pages"][0]["items"][0]
    assert item["id"] == "q1" and item["var"] == "nps_1" and "name" not in item


def test_output_name_by_question_shape():
    agree = Variable("agree", "nominal", labels=AGREE)
    m1 = Variable("m1", "ordinal", labels=AGREE)
    m2 = Variable("m2", "ordinal", labels=AGREE)
    owns_a = Variable("owns_a", "nominal", labels={0: "No", 1: "Yes"})
    owns_b = Variable("owns_b", "nominal", labels={0: "No", 1: "Yes"})

    plain = SingleChoice("Agree?", var=agree)
    with_id = SingleChoice("Agree?", var=agree, id="q7")
    named = SingleChoice("Agree?", var=agree, id="q7", name="agree")
    misnamed = SingleChoice("Agree?", var=agree, id="q7", name="col")
    matrix = Matrix("Rate", var=[m1, m2], id="grid")
    matrix_named = Matrix("Rate", var=[m1, m2], id="grid", name="ratings")
    matrix_unnamed = Matrix("Rate", var=[m1, m2])
    wide = MultiChoice("Own?", vars=[owns_a, owns_b], id="q_own")

    # A single-variable question: the variable, whatever the id or the name says.
    assert question_output_name(plain) == "agree" and question_fallback_id(plain) == "agree"
    assert question_output_name(with_id) == "agree" and question_fallback_id(with_id) == "q7"
    assert question_output_name(named) == "agree"
    # A name that is not the variable does not move the answer — validate() refuses it.
    assert question_output_name(misnamed) == "agree"
    # Several variables under one item: the name, or else the id, exactly as before.
    assert question_output_name(matrix) == "grid"
    assert question_output_name(matrix_named) == "ratings"
    assert question_output_name(matrix_unnamed) == "matrix_m1"
    assert question_output_name(wide) == "q_own"


def test_a_single_variable_questions_name_is_its_variable():
    """`name` used to override the key, so id `q1`, name `col`, variable
    `nps_1` put the answer under `col` while the condition read `nps_1` — the
    same defect through another field. The key is the variable: a name that
    agrees is allowed, a name that differs is refused, naming both."""

    nps = Variable("nps_1", "ordinal", labels={str(i): str(i) for i in range(11)})
    agreed = Questionnaire(
        title="T",
        pages=[Page("p1", items=[SingleChoice("How likely?", var=nps, id="q1", name="nps_1")])],
    )
    agreed.validate()
    item = compile_react_payload(agreed)["PAGES"][0]["items"][0]
    assert item["id"] == "nps_1" and item["qid"] == "q1"
    disagreed = Questionnaire(
        title="T",
        pages=[Page("p1", items=[SingleChoice("How likely?", var=nps, id="q1", name="col")])],
    )
    with pytest.raises(
        ValueError, match="Question 'q1' has name 'col' but writes variable 'nps_1'"
    ):
        disagreed.validate()
    # Without an id the name is also the fallback id; the rule is the same.
    only_named = Questionnaire(
        title="T", pages=[Page("p1", items=[SingleChoice("How likely?", var=nps, name="col")])]
    )
    with pytest.raises(
        ValueError, match="Question 'col' has name 'col' but writes variable 'nps_1'"
    ):
        only_named.validate()
    # A multi-variable item's name is its key; there is no one variable to agree with.
    m1 = Variable("m1", "ordinal", labels=AGREE)
    m2 = Variable("m2", "ordinal", labels=AGREE)
    grid = Questionnaire(
        title="T",
        pages=[Page("p1", items=[Matrix("Rate", var=[m1, m2], id="grid", name="ratings")])],
    )
    grid.validate()
    assert compile_react_payload(grid)["PAGES"][0]["items"][0]["id"] == "ratings"


def test_multi_variable_questions_are_compiled_as_before():
    m1 = Variable("m1", "ordinal", labels=AGREE)
    m2 = Variable("m2", "ordinal", labels=AGREE)
    survey = Questionnaire(
        title="T", pages=[Page("p", items=[Matrix("Rate", var=[m1, m2], id="grid")])]
    )
    item = compile_react_payload(survey)["PAGES"][0]["items"][0]
    assert item["id"] == "grid" and item["qid"] == "grid"
    assert [row["id"] for row in item["rows"]] == ["m1", "m2"]


# ── scripts name questions by id; the runtime matches them by key ────────────


def _scripted_survey(*scripts: Script) -> Questionnaire:
    news = Variable("news_source", "nominal", labels={1: "TV", 2: "Web"})
    email = Variable("email", "nominal")
    email2 = Variable("email_confirm", "nominal")
    return Questionnaire(
        title="T",
        pages=[
            Page(
                "p1",
                items=[
                    SingleChoice(
                        "News?", var=news, id="q1", choices=[Option(1, "TV"), Option(2, "Web")]
                    ),
                    SingleChoice("Email?", var=email, id="q2"),
                    SingleChoice("Again?", var=email2, id="q3"),
                ],
            )
        ],
        scripts=list(scripts),
    )


def test_a_script_may_target_the_id_or_the_variable():
    _scripted_survey(Script.randomize_options("q1")).validate()
    _scripted_survey(Script.randomize_options("news_source")).validate()
    with pytest.raises(ValueError, match="not a known question ID"):
        _scripted_survey(Script.randomize_options("q9")).validate()


def test_library_scripts_reach_the_runtime_keyed_like_the_answers():
    """`randomize_options("q1")` shuffles `__options__["q1"]`; the runtime keeps
    the options under the item id, which is now `news_source`. So the script is
    regenerated for the key — code included, not just its target."""

    survey = _scripted_survey(
        Script.randomize_options("q1", seed="s"),
        Script.timed_question("q1", seconds=45),
        Script.validate_fields_match("q2", "q3", message="Emails differ."),
        Script(code="answers.x = 1;", trigger="onQuestionShow", target="q2", name="custom"),
        Script(code="answers.y = 1;", trigger="onPageEnter", target="p1", name="page_scoped"),
    )
    compiled = compile_react_payload(survey)["SURVEY"]["scripts"]
    by_name = {script["name"]: script for script in compiled}

    shuffle = by_name["randomize_news_source"]
    assert shuffle["target"] == "news_source"
    assert 'const qid = "news_source";' in shuffle["code"] and '"q1"' not in shuffle["code"]
    assert shuffle["context"] == {"seed": "s"}
    timed = by_name["timed_news_source"]
    assert timed["target"] == "news_source" and "const timeout = 45000;" in timed["code"]
    match = by_name["validate_match_email_email_confirm"]
    # No target: it re-checks the pair whichever of the two fields changes.
    assert match["target"] is None
    assert 'const fa = "email";' in match["code"] and 'const fb = "email_confirm";' in match["code"]
    assert '"Emails differ."' in match["code"]
    # A custom script keeps its code; only the target it is scoped to is translated.
    assert by_name["custom"]["target"] == "email" and by_name["custom"]["code"] == "answers.x = 1;"
    # A page-scoped trigger's target is a page name and is left alone.
    assert by_name["page_scoped"]["target"] == "p1"
    # The survey's own scripts are untouched: the document still says `q1`.
    assert survey.scripts[0].target == "q1"


def test_only_a_question_scoped_target_is_translated():
    """The runtime dispatches onPageEnter / onPageExit with the page's name
    and onQuestionShow / onAnswer with the item's key; onInit, onSubmit and
    onRandomize carry no target at all. So only a question-scoped target is a
    key — and a page may be called `q1` next to a question whose id is `q1`:
    translating the page's target would silence the script on that page."""

    nps = Variable("nps_1", "ordinal", labels={str(i): str(i) for i in range(11)})
    triggers = (
        "onPageEnter",
        "onPageExit",
        "onQuestionShow",
        "onAnswer",
        "onInit",
        "onSubmit",
        "onRandomize",
    )
    survey = Questionnaire(
        title="T",
        pages=[Page("q1", items=[SingleChoice("How likely?", var=nps, id="q1")])],
        scripts=[
            Script(code="answers.x = 1;", trigger=trigger, target="q1", name=trigger)
            for trigger in triggers
        ],
    )
    survey.validate()
    compiled = {s["name"]: s["target"] for s in compile_react_payload(survey)["SURVEY"]["scripts"]}
    assert compiled == {
        "onPageEnter": "q1",
        "onPageExit": "q1",
        "onQuestionShow": "nps_1",
        "onAnswer": "nps_1",
        "onInit": "q1",
        "onSubmit": "q1",
        "onRandomize": "q1",
    }
    # Straight from the translation, no page in sight: the trigger decides.
    aliases = {"q1": "nps_1"}
    on_page = Script(code="answers.x = 1;", trigger="onPageEnter", target="q1")
    on_answer = Script(code="answers.x = 1;", trigger="onAnswer", target="q1")
    assert script_for_runtime(on_page, aliases) is on_page
    assert script_for_runtime(on_answer, aliases).target == "nps_1"


def test_scripts_of_a_survey_whose_ids_are_its_variables_are_passed_through():
    news = Variable("news_source", "nominal", labels={1: "TV", 2: "Web"})
    script = Script.randomize_options("news_source")
    survey = Questionnaire(
        title="T", pages=[Page("p1", items=[SingleChoice("News?", var=news)])], scripts=[script]
    )
    assert compile_react_payload(survey)["SURVEY"]["scripts"] == [script.to_dict()]


def test_a_custom_script_reads_the_answer_by_the_key():
    """A custom script keeps its code, except that the accesses naming an
    aliased id — and only those — are turned to the key the runtime uses."""

    aliases = {"q1": "nps_1"}
    forms = {
        'answers["q1"]': 'answers["nps_1"]',
        "answers['q1']": "answers['nps_1']",
        "answers.q1": "answers.nps_1",
        'answers.__errors__["q1"]': 'answers.__errors__["nps_1"]',
        "answers.__errors__['q1']": "answers.__errors__['nps_1']",
        "answers.__errors__.q1": "answers.__errors__.nps_1",
        '__errors__["q1"]': '__errors__["nps_1"]',
        "__errors__.q1": "__errors__.nps_1",
        # The runtime keeps shuffled options and timer handles under the key as well.
        'answers.__options__["q1"]': 'answers.__options__["nps_1"]',
        'answers.__options__?.["q1"]': 'answers.__options__?.["nps_1"]',
        "answers?.q1": "answers?.nps_1",
        'answers.__timers__["q1"]': 'answers.__timers__["nps_1"]',
        "__timers__.q1": "__timers__.nps_1",
        # Whitespace inside the brackets, a template literal as the key.
        'answers[ "q1" ]': 'answers[ "nps_1" ]',
        "answers[\n  'q1'\n]": "answers[\n  'nps_1'\n]",
        "answers[`q1`]": "answers[`nps_1`]",
        "answers.__errors__?.[ `q1` ]": "answers.__errors__?.[ `nps_1` ]",
    }
    for source, expected in forms.items():
        assert rewrite_answer_keys(source, aliases) == expected, source
    # An id that is not aliased, a longer id that merely starts with an aliased
    # one, an access that is not one of these forms, a bare string.
    for untouched in (
        "answers.age",
        'answers["age"]',
        "answers.q10",
        'answers["q10"]',
        "answers['q10']",
        "answers.q1x",
        "answers.q1_note",
        'other["q1"]',
        "lookup.q1",
        "myanswers.q1",
        '"q1"',
        "const q1 = 1;",
        # An `answers` or `__errors__` that is a property of some other object.
        "state.answers.q1",
        'ctx.answers["q1"]',
        "state?.answers.q1",
        'ctx?.answers?.["q1"]',
        'snapshot.__errors__["q1"]',
        "snapshot.__errors__.q1",
        "state.answers.__options__.q1",
    ):
        assert rewrite_answer_keys(untouched, aliases) == untouched, untouched
    assert rewrite_answer_keys("answers.q1 + state.answers.q1", aliases) == (
        "answers.nps_1 + state.answers.q1"
    )
    # No aliases: the code is handed back as is.
    assert rewrite_answer_keys('answers["q1"]', {}) == 'answers["q1"]'


def test_the_rewrite_reads_ids_and_writes_keys_as_javascript_would():
    """An id that is not an identifier can only have been written in the
    bracket form — `answers.a-b` is `answers.a` minus `b` — and a key is
    emitted in a form JavaScript reads back as that key."""

    # Only the bracket form is looked for when the id is not an identifier.
    assert rewrite_answer_keys('answers["a-b"]', {"a-b": "nps"}) == 'answers["nps"]'
    assert rewrite_answer_keys("answers.a-b", {"a-b": "nps"}) == "answers.a-b"
    assert rewrite_answer_keys("answers.a-b + answers['a-b']", {"a-b": "n"}) == (
        "answers.a-b + answers['n']"
    )
    # A key that is not an identifier is reached by subscript.
    assert rewrite_answer_keys("answers.q1", {"q1": "a-b"}) == 'answers["a-b"]'
    assert rewrite_answer_keys("answers?.q1", {"q1": "a-b"}) == 'answers?.["a-b"]'
    # Identifiers are not only ASCII, in JavaScript or in a survey.
    assert rewrite_answer_keys("answers.возраст", {"возраст": "age"}) == "answers.age"
    assert rewrite_answer_keys("answers.q1", {"q1": "возраст"}) == "answers.возраст"
    # A key the author's quotes cannot spell verbatim — it holds that quote, a
    # backslash, or `${` inside backticks — is spliced in as a JSON literal.
    assert rewrite_answer_keys("answers['q1']", {"q1": "it's"}) == 'answers["it\'s"]'
    assert rewrite_answer_keys('answers["q1"]', {"q1": 'a"b'}) == 'answers["a\\"b"]'
    assert rewrite_answer_keys("answers['q1']", {"q1": "a\\b"}) == 'answers["a\\\\b"]'
    assert rewrite_answer_keys("answers[`q1`]", {"q1": "${x}"}) == 'answers["${x}"]'
    assert rewrite_answer_keys("answers[`q1`]", {"q1": "a`b"}) == 'answers["a`b"]'
    # Otherwise the author's quotes are kept.
    assert rewrite_answer_keys("answers['q1']", {"q1": 'say "hi"'}) == "answers['say \"hi\"']"


def test_what_the_rewrite_leaves_behind_is_reported():
    """The compiler rewrites the accesses it knows; an id anywhere else — a
    lookup key in a local, an object literal, a helper's argument — reaches
    the runtime naming a question it does not know by that name."""

    aliases = {"q1": "nps_1", "a-b": "k"}

    def stale(code: str) -> list[str]:
        return stale_answer_key_references(Script(code=code, trigger="onAnswer"), aliases)

    assert stale('const q = "q1"; answers[q] = 1;') == ["q1"]
    assert stale("utils.pick(answers, 'q1')") == ["q1"]
    assert stale("utils.pick(answers, `q1`)") == ["q1"]
    assert stale("x = {q1: 1}") == ["q1"]
    assert stale("if (q1) {}") == ["q1"]
    # Another object's `answers` is not rewritten, so what it says is reported.
    assert stale('ctx.answers["q1"] = 1;') == ["q1"]
    # An id that is not an identifier can only be a string.
    assert stale('x("a-b")') == ["a-b"]
    assert stale('x("a-b", "q1")') == ["q1", "a-b"], "in the order of the aliases, each once"
    # Translated accesses, another object's property, a longer name, an
    # arithmetic `a-b`, an unrelated string: not the id.
    for clean in (
        'answers["q1"] = 1;',
        "answers.__errors__.q1 = 'x';",
        "answers.__timers__[`q1`]",
        "lookup.q1",
        "state?.q1",
        "answers.q1_note",
        "x = a-b;",
        '"q10"',
    ):
        assert stale(clean) == [], clean
    # A library script is regenerated whole, and a survey without aliases has
    # nothing to report.
    assert stale_answer_key_references(Script.randomize_options("q1"), aliases) == []
    assert stale_answer_key_references(Script(code='x("q1")', trigger="onAnswer"), {}) == []


def test_strict_lint_names_the_script_that_still_says_the_id():
    """A script that goes on naming `q1` where the compiler cannot translate
    it is reported by `lint(level="strict")` — which script, which id, which
    key — instead of going dark in the field."""

    nps = Variable("nps_1", "ordinal", labels={str(i): str(i) for i in range(11)})
    stale = Script(code='const q = "q1";\nanswers[q] = 10;', trigger="onAnswer", name="stale")
    literal = Script(code="answers = {...answers, q1: 10};", trigger="onSubmit", name="literal")
    fine = Script(
        code='answers["q1"] = answers.__timers__?.q1 ? 1 : 0;', trigger="onAnswer", name="fine"
    )
    survey = Questionnaire(
        title="T",
        pages=[Page("p1", items=[SingleChoice("How likely?", var=nps, id="q1")])],
        scripts=[stale, literal, fine, Script.randomize_options("q1")],
    )
    survey.validate()
    findings = [w for w in survey.lint(level="strict") if w.code == "SCRIPT_STALE_QUESTION_ID"]
    assert [(w.location, w.severity) for w in findings] == [
        ("stale", "warning"),
        ("literal", "warning"),
    ]
    assert findings[0].message.startswith("Script 'stale' still names question 'q1'")
    assert "stored under 'nps_1'" in findings[0].message
    # Strict is the level that says so; basic does not, and it is a warning,
    # so a strict validate() still passes.
    assert not [w for w in survey.lint() if w.code == "SCRIPT_STALE_QUESTION_ID"]
    survey.validate(strict=True)
    # A survey whose ids are its variables has nothing to be told.
    plain = Questionnaire(
        title="T",
        pages=[Page("p1", items=[SingleChoice("How likely?", var=nps)])],
        scripts=[Script(code='const q = "nps_1"; answers[q] = 10;', trigger="onAnswer", name="s")],
    )
    assert not [w for w in plain.lint(level="strict") if w.code == "SCRIPT_STALE_QUESTION_ID"]


def test_an_id_in_a_comment_or_in_prose_is_not_a_stale_reference():
    """A comment is not code, and a string that merely mentions the id is not
    a reference to it; the id as a whole string or a bare identifier is."""

    aliases = {"q1": "nps_1"}

    def stale(code: str) -> list[str]:
        return stale_answer_key_references(Script(code=code, trigger="onAnswer"), aliases)

    for clean in (
        "// q1 is the NPS question\nanswers.x = 1;",
        "answers.x = 1; // was q1",
        "/* q1: see the codebook */ answers.x = 1;",
        "/* multi\n   line q1\n*/ answers.x = 1;",
        '// answers["q1"] used to be read here\nanswers.x = 1;',
        "const note = 'q1 was renamed'; answers.x = 1;",
        'const note = "see q1"; answers.x = 1;',
        "const note = `about q1`; answers.x = 1;",
        "const url = 'https://x/q1'; answers.x = 1;",
    ):
        assert stale(clean) == [], clean
    for still in (
        'const q = "q1"; // q1\nanswers[q] = 1;',
        # An apostrophe in a comment, or a quote inside a string, does not
        # swallow the code after it.
        "// don't\nconst q = 'q1';",
        'const s = "it\'s q1"; if (q1) {}',
        "x(`q1`)",
        "x(`${q1}`)",
        'x(`${"q1"}`)',
        "/* q1 */ x = {q1: 1}",
    ):
        assert stale(still) == ["q1"], still
    # Through lint: a script whose only `q1` is a comment is not reported.
    nps = Variable("nps_1", "ordinal", labels={str(i): str(i) for i in range(11)})
    survey = Questionnaire(
        title="T",
        pages=[Page("p1", items=[SingleChoice("How likely?", var=nps, id="q1")])],
        scripts=[
            Script(
                code="// q1 is stored as nps_1\nanswers.x = 1;",
                trigger="onAnswer",
                name="commented",
            ),
            Script(
                code="answers.x = 1; /* q1 */ const q = 'q1';", trigger="onAnswer", name="coded"
            ),
        ],
    )
    survey.validate()
    findings = [w for w in survey.lint(level="strict") if w.code == "SCRIPT_STALE_QUESTION_ID"]
    assert [w.location for w in findings] == ["coded"]


def test_strict_lint_reports_a_target_of_the_wrong_kind_for_its_trigger():
    """validate() takes any question id, key or page name as a target; the
    runtime dispatches onQuestionShow / onAnswer with the question's key and
    onPageEnter / onPageExit with the page's name. A question-scoped script
    aimed at a page, or a page-scoped script aimed at a question, therefore
    validates and never runs — so strict lint says which, and why."""

    nps = Variable("nps_1", "ordinal", labels={str(i): str(i) for i in range(11)})
    why = Variable("why", "nominal")

    def script(name: str, trigger: str, target: str) -> Script:
        return Script(code="answers.x = 1;", trigger=trigger, target=target, name=name)

    survey = Questionnaire(
        title="T",
        pages=[
            Page("p1", items=[SingleChoice("How likely?", var=nps, id="q1")]),
            Page("p2", items=[OpenText("Why?", var=why)]),
        ],
        scripts=[
            script("show_on_page", "onQuestionShow", "p1"),
            script("answer_on_page", "onAnswer", "p2"),
            script("enter_on_question", "onPageEnter", "q1"),
            script("exit_on_key", "onPageExit", "nps_1"),
            script("exit_on_why", "onPageExit", "why"),
            # The right kind of target: a question by id or by key, a page by name.
            script("show_by_id", "onQuestionShow", "q1"),
            script("answer_by_key", "onAnswer", "nps_1"),
            script("enter_page", "onPageEnter", "p1"),
            script("exit_page", "onPageExit", "p2"),
            # No target is global, and no kind at all.
            Script(code="answers.x = 1;", trigger="onInit", name="init"),
        ],
    )
    survey.validate()
    findings = [w for w in survey.lint(level="strict") if w.code.startswith("SCRIPT_TARGET_IS_A_")]
    assert [(w.code, w.location, w.severity) for w in findings] == [
        ("SCRIPT_TARGET_IS_A_PAGE", "show_on_page", "warning"),
        ("SCRIPT_TARGET_IS_A_PAGE", "answer_on_page", "warning"),
        ("SCRIPT_TARGET_IS_A_QUESTION", "enter_on_question", "warning"),
        ("SCRIPT_TARGET_IS_A_QUESTION", "exit_on_key", "warning"),
        ("SCRIPT_TARGET_IS_A_QUESTION", "exit_on_why", "warning"),
    ]
    assert findings[0].message == (
        "Script 'show_on_page' runs on onQuestionShow but its target 'p1' is a page, not a "
        "question; the runtime dispatches onQuestionShow with the question's key, so the "
        "script would never run. Target a question, or use onPageEnter / onPageExit for "
        "page 'p1'."
    )
    assert findings[2].message == (
        "Script 'enter_on_question' runs on onPageEnter but its target 'q1' is a question, "
        "not a page; the runtime dispatches onPageEnter with the page's name, so the script "
        "would never run. Target the page that holds question 'q1', or use onQuestionShow / "
        "onAnswer."
    )
    # Strict is the level that says so; basic does not; and it is a warning,
    # so a strict validate() still passes — existing documents keep loading.
    assert not [w for w in survey.lint() if w.code.startswith("SCRIPT_TARGET_IS_A_")]
    survey.validate(strict=True)
    # A page that shares its name with a question id is either, and is not reported.
    shared = Questionnaire(
        title="T",
        pages=[Page("q1", items=[SingleChoice("How likely?", var=nps, id="q1")])],
        scripts=[script("show", "onQuestionShow", "q1"), script("enter", "onPageEnter", "q1")],
    )
    shared.validate()
    assert not [w for w in shared.lint(level="strict") if w.code.startswith("SCRIPT_TARGET_IS_A_")]
    # An unnamed script is reported by its position.
    anonymous = Questionnaire(
        title="T",
        pages=[Page("p1", items=[SingleChoice("How likely?", var=nps, id="q1")])],
        scripts=[Script(code="answers.x = 1;", trigger="onAnswer", target="p1")],
    )
    anonymous.validate()
    assert [
        w.location for w in anonymous.lint(level="strict") if w.code == "SCRIPT_TARGET_IS_A_PAGE"
    ] == ["script #1"]


def test_a_custom_script_is_rewritten_for_the_key_when_compiled():
    """`q1` is `nps_1` in the field; `q10` and `age` are their own keys, and a
    `q10` in the code is not a `q1`."""

    nps = Variable("nps_1", "ordinal", labels={str(i): str(i) for i in range(11)})
    q10 = Variable("q10", "nominal", labels=AGREE)
    age = Variable("age", "ratio")
    code = (
        'if (answers["q1"] <= 6 && answers.q10 === 1) {\n'
        '  answers.__errors__["q1"] = "Really? " + answers.age + answers[\'q10\'];\n'
        "}\n"
    )
    custom = Script(code=code, trigger="onAnswer", name="custom")
    scoped = Script(code=code, trigger="onQuestionShow", target="q1", name="scoped")
    survey = Questionnaire(
        title="T",
        pages=[
            Page(
                "p1",
                items=[
                    SingleChoice("How likely?", var=nps, id="q1"),
                    SingleChoice("Agree?", var=q10, id="q10"),
                    NumericInput("Age?", var=age),
                ],
            )
        ],
        scripts=[custom, scoped],
    )
    survey.validate()
    compiled = {s["name"]: s for s in compile_react_payload(survey)["SURVEY"]["scripts"]}
    expected = (
        'if (answers["nps_1"] <= 6 && answers.q10 === 1) {\n'
        '  answers.__errors__["nps_1"] = "Really? " + answers.age + answers[\'q10\'];\n'
        "}\n"
    )
    assert compiled["custom"]["code"] == expected and compiled["custom"]["target"] is None
    assert compiled["scoped"]["code"] == expected and compiled["scoped"]["target"] == "nps_1"
    # The survey's own script is the author's, untouched.
    assert survey.scripts[0].code == code
    # And a script that names no aliased id is the very same object.
    plain = Script(code="answers.age = 40;", trigger="onAnswer", name="plain")
    assert script_for_runtime(plain, {"q1": "nps_1"}) is plain


# ── skip_to names a page or a question id; the runtime resolves it by page ───


def _routed_survey() -> Questionnaire:
    start = Variable("start", "nominal", labels=AGREE)
    detour = Variable("detour", "nominal", labels=AGREE)
    inner = Variable("inner", "nominal", labels=AGREE)
    final = Variable("final", "nominal", labels=AGREE)
    return Questionnaire(
        title="T",
        pages=[
            Page(
                "p1",
                items=[
                    # A question id whose key differs: `q4` is stored as `final`
                    # and sits on page `p3`.
                    SingleChoice("Start?", var=start, id="q1", skip_to="q4"),
                ],
            ),
            Page(
                "p2",
                items=[
                    # A page name is not a question id and is left alone.
                    SingleChoice("Detour?", var=detour, id="q2", skip_to="p_end"),
                    # A question inside a block goes through the same translation.
                    Block(
                        title="B",
                        items=[SingleChoice("Inner?", var=inner, id="q3", skip_to="q4")],
                    ),
                ],
            ),
            Page("p3", items=[SingleChoice("Final?", var=final, id="q4")]),
            Page("p_end", kind="final", body="Thanks"),
        ],
    )


def test_skip_to_by_question_id_is_emitted_as_the_page_that_holds_it():
    """The runtime resolves a skip target by page name and then by item id —
    which is the key, not the id the author wrote. Naming the page the
    question sits on lands the respondent in the same place with no id to
    translate, and no key that could collide with a page's name."""

    survey = _routed_survey()
    survey.validate()
    items = _items(compile_react_payload(survey))
    assert items["final"]["qid"] == "q4"
    assert items["start"]["skipTo"] == "p3", "skip_to='q4' lands on the page holding q4"
    assert items["inner"]["skipTo"] == "p3", "inside a block too"
    assert items["detour"]["skipTo"] == "p_end", "a page name is unchanged"
    # The document still says `q4`.
    assert survey.all_questions()[0].skip_to == "q4"


def test_skip_to_by_page_name_is_left_alone_even_when_a_question_has_that_id():
    """A page called `q1` next to a question whose id is `q1` (stored as
    `nps_1`): the runtime resolves page names first, so the page it is."""

    a = Variable("a", "nominal", labels=AGREE)
    b = Variable("b", "nominal", labels=AGREE)
    nps = Variable("nps_1", "ordinal", labels={str(i): str(i) for i in range(11)})
    survey = Questionnaire(
        title="T",
        pages=[
            Page("p1", items=[SingleChoice("A?", var=a, skip_to="q1")]),
            Page("p2", items=[SingleChoice("B?", var=b)]),
            Page("q1", items=[SingleChoice("How likely?", var=nps, id="q1")]),
        ],
    )
    survey.validate()
    assert _items(compile_react_payload(survey))["a"]["skipTo"] == "q1"


def test_skip_to_by_question_id_names_the_page_whatever_the_ids_are():
    a = Variable("a", "nominal", labels=AGREE)
    b = Variable("b", "nominal", labels=AGREE)
    survey = Questionnaire(
        title="T",
        pages=[
            Page("p1", items=[SingleChoice("A?", var=a, skip_to="b")]),
            Page("p2", items=[SingleChoice("B?", var=b)]),
        ],
    )
    survey.validate()
    assert _items(compile_react_payload(survey))["a"]["skipTo"] == "p2"
    # A flat questionnaire is rendered as one synthetic page; its questions
    # are on it.
    flat = Questionnaire(
        title="T", blocks=[SingleChoice("A?", var=a, skip_to="b"), SingleChoice("B?", var=b)]
    )
    flat.validate()
    assert _items(compile_react_payload(flat))["a"]["skipTo"] == "page1"


# ── validate(): a key is unique, and no id shadows another question's key ────


def test_an_id_may_not_be_another_questions_answer_key():
    nps = Variable("nps_1", "ordinal", labels={str(i): str(i) for i in range(11)})
    why = Variable("why", "nominal")
    survey = Questionnaire(
        title="T",
        pages=[
            Page("p1", items=[SingleChoice("How likely?", var=nps, id="q1")]),
            # `nps_1` is where q1's answer lands: the runtime could not tell
            # this question's id from that key.
            Page("p2", items=[OpenText("Why?", var=why, id="nps_1")]),
        ],
    )
    with pytest.raises(ValueError, match="'nps_1' has the id under which question 'q1'"):
        survey.validate()


def test_two_questions_may_not_share_an_answer_key():
    col = Variable("col", "nominal", labels=AGREE)
    m1 = Variable("m1", "ordinal", labels=AGREE)
    m2 = Variable("m2", "ordinal", labels=AGREE)
    survey = Questionnaire(
        title="T",
        pages=[
            Page(
                "p1",
                items=[
                    # A matrix's name is its key — here the key of the question after it.
                    Matrix("Rate", var=[m1, m2], id="grid", name="col"),
                    SingleChoice("B?", var=col, id="q2"),
                ],
            )
        ],
    )
    with pytest.raises(ValueError, match="Duplicate answer key.*'grid' and 'q2'.*'col'"):
        survey.validate()


def test_two_questions_on_one_variable_are_still_a_duplicate_variable():
    """Two questions bound to one variable share an answer key as well; the
    message that names the cause is the one an author has always seen."""

    col = Variable("col", "nominal", labels=AGREE)
    survey = Questionnaire(
        title="T",
        pages=[
            Page(
                "p1",
                items=[SingleChoice("A?", var=col, id="q1"), SingleChoice("B?", var=col, id="q2")],
            )
        ],
    )
    with pytest.raises(ValueError, match="Duplicate variable in questionnaire: col"):
        survey.validate()


def test_a_document_whose_ids_are_its_variables_still_validates():
    a = Variable("a", "nominal", labels=AGREE)
    b = Variable("b", "nominal", labels=AGREE)
    m1 = Variable("m1", "ordinal", labels=AGREE)
    m2 = Variable("m2", "ordinal", labels=AGREE)
    owns_a = Variable("owns_a", "nominal", labels={0: "No", 1: "Yes"})
    owns_b = Variable("owns_b", "nominal", labels={0: "No", 1: "Yes"})
    survey = Questionnaire(
        title="T",
        pages=[
            Page(
                "p1",
                items=[
                    SingleChoice("A?", var=a, id="a"),
                    SingleChoice("B?", var=b),
                    Matrix("Rate", var=[m1, m2], id="grid"),
                    OpenText("Note", var=Variable("note", "nominal")),
                    MultiChoice("Own?", vars=[owns_a, owns_b]),
                ],
            )
        ],
    )
    survey.validate()
    # id == key for every question, and the multi-variable items keep their id.
    assert [question_output_name(q) for q in survey.all_questions()] == [
        question_fallback_id(q) for q in survey.all_questions()
    ]
