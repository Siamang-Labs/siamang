"""Scripts in the questionnaire document.

A :class:`~siamang.core.script.Script` built by one of the engine's factories
(``Script.timed_question`` and friends) is stored by *what it does* — the
factory name and its parameters — so a builder can show "timed question, 45 s"
instead of a wall of JavaScript, and regenerate the script from the current
engine on load. Anything else is stored verbatim as a ``custom`` script.

Detection is exact: a script is recorded as a library script only when the
factory, called with the recovered parameters, reproduces the script
field-for-field. That keeps the round trip lossless even if someone edited a
factory-generated script by hand — it then simply becomes ``custom``.
"""

from __future__ import annotations

import json
import re
from typing import Any

from siamang.core.script import Script

_TIMEOUT_RE = re.compile(r"const timeout = (\d+);")
_FIELD_A_RE = re.compile(r"const fa = (\"(?:[^\"\\]|\\.)*\");")
_FIELD_B_RE = re.compile(r"const fb = (\"(?:[^\"\\]|\\.)*\");")
_MESSAGE_RE = re.compile(r"answers\.__errors__\[fb\] = (\"(?:[^\"\\]|\\.)*\");")

LIBRARY_SCRIPT_TYPES = (
    "assign_condition",
    "randomize_options",
    "randomize_pages",
    "timed_question",
    "validate_fields_match",
)


def script_to_document(script: Script) -> dict[str, Any]:
    """Serialize a script, preferring the library form when it is exact."""

    if not isinstance(script, Script):
        raise TypeError(f"Expected a Script, got {type(script).__name__}.")
    library = _detect_library_script(script)
    if library is not None:
        return library
    payload: dict[str, Any] = {"type": "custom"}
    if script.name is not None:
        payload["name"] = script.name
    payload["trigger"] = script.trigger
    if script.target is not None:
        payload["target"] = script.target
    payload["code"] = script.code
    if script.context:
        payload["context"] = dict(script.context)
    payload["sandbox"] = script.sandbox
    return payload


def script_from_document(payload: dict[str, Any]) -> Script:
    kind = payload.get("type")
    if kind == "custom":
        return Script(
            code=payload["code"],
            trigger=payload.get("trigger", "onPageEnter"),
            name=payload.get("name"),
            target=payload.get("target"),
            context=dict(payload.get("context") or {}),
            sandbox=bool(payload.get("sandbox", True)),
        )
    if kind == "assign_condition":
        arms = [(arm["code"], arm["label"], int(arm.get("weight", 1))) for arm in payload["arms"]]
        return Script.assign_condition(
            payload["variable"],
            arms,
            seed=payload.get("seed"),
            balance=bool(payload.get("balance", False)),
        )
    if kind == "randomize_options":
        return Script.randomize_options(payload["question"], seed=payload.get("seed"))
    if kind == "randomize_pages":
        return Script.randomize_pages()
    if kind == "timed_question":
        return Script.timed_question(payload["question"], seconds=int(payload["seconds"]))
    if kind == "validate_fields_match":
        kwargs: dict[str, Any] = {}
        if "message" in payload:
            kwargs["message"] = payload["message"]
        return Script.validate_fields_match(payload["field_a"], payload["field_b"], **kwargs)
    raise ValueError(f"Unknown script type: {kind!r}.")


def _detect_library_script(script: Script) -> dict[str, Any] | None:
    for candidate in (
        _as_randomize_pages,
        _as_assign_condition,
        _as_randomize_options,
        _as_timed,
        _as_validate_match,
    ):
        found = candidate(script)
        if found is not None:
            return found
    return None


def _as_randomize_pages(script: Script) -> dict[str, Any] | None:
    if script == Script.randomize_pages():
        return {"type": "randomize_pages"}
    return None


def _as_assign_condition(script: Script) -> dict[str, Any] | None:
    # The parameters ride in `context`, so recovery is a read rather than a
    # regex over generated JavaScript — and the exactness check below still
    # decides whether this really is the factory's output.
    if not (script.name or "").startswith("assign_"):
        return None
    context = script.context or {}
    variable = context.get("variable")
    raw_arms = context.get("arms")
    if not isinstance(variable, str) or not isinstance(raw_arms, list):
        return None
    try:
        arms = [(arm[0], arm[1], int(arm[2]) if len(arm) > 2 else 1) for arm in raw_arms]
    except (IndexError, TypeError, ValueError):
        return None
    seed = context.get("seed")
    balance = bool(context.get("balance", False))
    if script != Script.assign_condition(variable, arms, seed=seed, balance=balance):
        return None
    payload: dict[str, Any] = {
        "type": "assign_condition",
        "variable": variable,
        "arms": [
            {"code": code, "label": label, **({"weight": weight} if weight != 1 else {})}
            for code, label, weight in arms
        ],
    }
    if seed is not None:
        payload["seed"] = seed
    if balance:
        payload["balance"] = True
    return payload


def _as_randomize_options(script: Script) -> dict[str, Any] | None:
    if script.target is None or not (script.name or "").startswith("randomize_"):
        return None
    seed = script.context.get("seed") if script.context else None
    if script != Script.randomize_options(script.target, seed=seed):
        return None
    payload: dict[str, Any] = {"type": "randomize_options", "question": script.target}
    if seed is not None:
        payload["seed"] = seed
    return payload


def _as_timed(script: Script) -> dict[str, Any] | None:
    if script.target is None or not (script.name or "").startswith("timed_"):
        return None
    match = _TIMEOUT_RE.search(script.code)
    if match is None:
        return None
    milliseconds = int(match.group(1))
    if milliseconds % 1000:
        return None
    seconds = milliseconds // 1000
    if script != Script.timed_question(script.target, seconds=seconds):
        return None
    return {"type": "timed_question", "question": script.target, "seconds": seconds}


def _as_validate_match(script: Script) -> dict[str, Any] | None:
    if not (script.name or "").startswith("validate_match_"):
        return None
    parts = [regex.search(script.code) for regex in (_FIELD_A_RE, _FIELD_B_RE, _MESSAGE_RE)]
    if any(part is None for part in parts):
        return None
    try:
        field_a, field_b, message = (json.loads(part.group(1)) for part in parts)  # type: ignore[union-attr]
    except ValueError:
        return None
    if script != Script.validate_fields_match(field_a, field_b, message=message):
        return None
    payload: dict[str, Any] = {
        "type": "validate_fields_match",
        "field_a": field_a,
        "field_b": field_b,
    }
    if message != "Fields do not match.":
        payload["message"] = message
    return payload
