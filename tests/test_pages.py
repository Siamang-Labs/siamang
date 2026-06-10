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


def test_react_payload_carries_page_kinds():
    payload = compile_react_payload(_q(), ui=UIConfig())
    by_name = {p["name"]: p for p in payload["PAGES"]}
    assert by_name["intro"]["kind"] == "content"
    assert by_name["dq"]["kind"] == "disqualification"
    assert by_name["dq"]["body"] == "<p>Not eligible</p>"
    assert by_name["rd"]["redirectUrl"] == "https://x"
