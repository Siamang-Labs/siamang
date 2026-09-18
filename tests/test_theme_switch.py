"""The respondent's theme: a starting point, or a decision the study makes.

The runtime has always shown a light/dark button and remembered the choice, so
`default_theme` was only ever the first value — a stored preference beat it, and
because the key was a constant and localStorage is per origin, a choice made in
one study arrived in the next one. `allow_theme_switch` is the other half: the
button goes away, the stored value is not consulted, and the instrument looks
the same for every respondent. The rendering itself is exercised in a browser;
what is pinned here is the payload the runtime reads and the source it reads it
with.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import siamang as sg
from siamang.frontend.compiler.react import compile_react_payload
from siamang.frontend.theme.ui_config import UIConfig

_REACT = Path(__file__).resolve().parent.parent / "siamang" / "frontend" / "templates" / "react"


def _survey() -> sg.Questionnaire:
    age = sg.Variable("age", scale="ratio", label="Age")
    return sg.Questionnaire(title="T", pages=[sg.Page(name="p", items=[sg.NumericInput("Age?", var=age)])])


def test_the_switch_is_on_by_default() -> None:
    assert UIConfig().allow_theme_switch is True


def test_default_theme_is_validated_like_every_other_enum() -> None:
    for value in ("light", "dark", "system"):
        assert UIConfig(default_theme=value).default_theme == value
    with pytest.raises(ValueError, match="default_theme must be one of"):
        UIConfig(default_theme="auto")


@pytest.mark.parametrize("allow", [True, False])
def test_the_payload_carries_the_choice(allow: bool) -> None:
    payload = compile_react_payload(_survey(), ui=UIConfig(default_theme="dark", allow_theme_switch=allow))
    assert payload["SURVEY"]["allowThemeSwitch"] is allow
    assert payload["SURVEY"]["defaultTheme"] == "dark"


def test_the_document_schema_accepts_the_field() -> None:
    schema = json.loads((Path(__file__).resolve().parent.parent / "siamang" / "schemas" / "questionnaire-1.0.json").read_text())
    ui = schema["$defs"]["ui"]
    # `ui` is a closed allowlist, so a field the schema has not been told about
    # would be rejected on a Save however well the runtime handled it.
    assert ui["additionalProperties"] is False
    assert ui["properties"]["allow_theme_switch"] == {"type": "boolean"}


def test_the_stored_theme_is_keyed_by_survey() -> None:
    """The answers were already per survey; the theme was the one that was not.

    localStorage is per origin and every survey of a deployment shares one, so a
    constant key let a choice made in one instrument follow the respondent into
    the next.
    """
    hooks = (_REACT / "hooks.jsx").read_text()
    assert '"siamang_theme_" + surveyId' in hooks
    # The bundle rather than the source for the negative: the old constant is
    # named in a comment above the line that replaced it, and the build strips
    # comments — so this asks the artifact that actually ships whether any code
    # still reaches for the shared key.
    bundle = (_REACT / "dist" / "bundle.js").read_text()
    assert "siamang_theme_" in bundle
    assert not re.search(r'"siamang_theme"(?!_)', bundle)


def test_the_button_and_the_stored_value_are_both_behind_the_flag() -> None:
    app = (_REACT / "app.jsx").read_text()
    hooks = (_REACT / "hooks.jsx").read_text()
    # Rendered only when switching is allowed …
    assert "ui.allowThemeSwitch !== false && (" in app
    # … and a stored choice is only consulted then, or an old one would override
    # the decision this study made.
    body = hooks[hooks.index("function useTheme") : hooks.index("function useAutosave")]
    assert "if (!allowSwitch) return preferred();" in body
    assert body.index("if (!allowSwitch)") < body.index("localStorage.getItem")
