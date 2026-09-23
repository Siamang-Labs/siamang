"""Custom survey page kinds: content / disqualification / final / redirect."""

import pytest

from siamang.core import (
    ContentPage,
    DisqualificationPage,
    FinalPage,
    Page,
    Questionnaire,
    RedirectPage,
)
from siamang.frontend.compiler import compile_questionnaire
from siamang.frontend.compiler.react import compile_react_payload
from siamang.frontend.theme.ui_config import UIConfig


def _q() -> Questionnaire:
    return Questionnaire(
        title="T",
        pages=[
            ContentPage("intro", body="<p>Welcome</p>"),
            DisqualificationPage("dq", title="Sorry", body="<p>Not eligible</p>"),
            FinalPage(
                "done",
                title="Thanks",
                body="<p>Bye</p>",
                redirect_url="https://p/d",
                redirect_delay=3,
            ),
            RedirectPage("rd", redirect_url="https://x"),
        ],
    )


def test_factories_set_kind_and_fields():
    assert ContentPage("c", body="x").kind == "content"
    assert DisqualificationPage("d").kind == "disqualification"
    assert FinalPage("f").kind == "final"
    rp = RedirectPage("r", redirect_url="https://x", redirect_delay=2)
    assert rp.kind == "redirect" and rp.redirect_url == "https://x" and rp.redirect_delay == 2


def test_is_terminal():
    assert DisqualificationPage("d").is_terminal
    assert FinalPage("f").is_terminal
    assert RedirectPage("r", redirect_url="u").is_terminal
    assert not ContentPage("c", body="x").is_terminal
    assert not Page("normal").is_terminal


def test_unknown_kind_rejected():
    with pytest.raises(ValueError):
        Page("x", kind="bogus")


def test_questionnaire_validates_with_terminal_pages():
    _q().validate()  # must not raise


def test_schema_to_dict_carries_page_kinds():
    schema = compile_questionnaire(_q()).to_dict()
    by_name = {p["name"]: p for p in schema["pages"]}
    assert by_name["intro"]["kind"] == "content"
    assert by_name["intro"]["body"] == "<p>Welcome</p>"
    assert by_name["done"]["kind"] == "final"
    assert by_name["done"]["redirectUrl"] == "https://p/d"
    assert by_name["done"]["redirectDelay"] == 3
    assert by_name["rd"]["kind"] == "redirect"


def test_react_payload_carries_outcome_redirects():
    ui = UIConfig(
        redirect_url="https://panel/complete?id={url:PID}",
        screen_out_redirect_url="https://panel/screenout?id={url:PID}",
        quota_full_redirect_url="https://panel/quota",
    )
    survey = compile_react_payload(_q(), ui=ui)["SURVEY"]
    assert survey["redirectUrl"] == "https://panel/complete?id={url:PID}"
    assert survey["screenOutRedirectUrl"] == "https://panel/screenout?id={url:PID}"
    assert survey["quotaFullRedirectUrl"] == "https://panel/quota"
    default = compile_react_payload(_q(), ui=UIConfig())["SURVEY"]
    assert default["screenOutRedirectUrl"] is None and default["quotaFullRedirectUrl"] is None


def test_react_payload_carries_page_kinds():
    payload = compile_react_payload(_q(), ui=UIConfig())
    by_name = {p["name"]: p for p in payload["PAGES"]}
    assert by_name["intro"]["kind"] == "content"
    assert by_name["dq"]["kind"] == "disqualification"
    assert by_name["dq"]["body"] == "<p>Not eligible</p>"
    assert by_name["rd"]["redirectUrl"] == "https://x"


# ── Script.randomize_pages keeps terminal pages where the author put them ─────


def _run_script_in_node(script, pages: list[dict]) -> list[str]:
    """Run a script's code the way the runtime does, on a deck of page objects,
    with a `shuffle` that reverses — deterministic, and visibly not identity."""

    import json
    import shutil
    import subprocess

    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    harness = f"""
        const utils = {{ shuffle: (items) => [...items].reverse() }};
        const context = {{}};
        const answers = {{ __pages__: {json.dumps(pages)} }};
        (function () {{ {script.code} }})();
        console.log(JSON.stringify(answers.__pages__.map((p) => p.name)));
    """
    result = subprocess.run([node, "-e", harness], capture_output=True, text=True, check=True)
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_randomize_pages_pins_terminal_pages_not_just_the_ends():
    """A screen-out is gated on the questions before it; shuffled into an
    earlier slot it would be evaluated before those answers exist."""

    from siamang.core import Script

    deck = [
        {"name": "intro"},
        {"name": "a"},
        {"name": "b"},
        {"name": "screen_out", "kind": "disqualification"},
        {"name": "c"},
        {"name": "stimulus", "kind": "content"},
        {"name": "quota_full", "kind": "redirect"},
        {"name": "d"},
        {"name": "thanks", "kind": "final"},
    ]
    order = _run_script_in_node(Script.randomize_pages(), deck)
    # Pinned: first, last, and every terminal page — at their own index.
    assert order[0] == "intro" and order[-1] == "thanks"
    assert order[3] == "screen_out" and order[6] == "quota_full"
    # Everything else — an engine content page included — is dealt into the
    # remaining slots, here by the reversing shuffle.
    assert [order[i] for i in (1, 2, 4, 5, 7)] == ["d", "stimulus", "c", "b", "a"]
    assert sorted(order) == sorted(page["name"] for page in deck)


def test_randomize_pages_leaves_a_deck_with_one_movable_page_alone():
    from siamang.core import Script

    deck = [{"name": "intro"}, {"name": "only"}, {"name": "thanks", "kind": "final"}]
    assert _run_script_in_node(Script.randomize_pages(), deck) == ["intro", "only", "thanks"]


def test_randomize_pages_is_still_recognised_as_the_library_script():
    from siamang.core import Script
    from siamang.model.scripts import script_from_document, script_to_document

    assert script_to_document(Script.randomize_pages()) == {"type": "randomize_pages"}
    assert script_from_document({"type": "randomize_pages"}) == Script.randomize_pages()
