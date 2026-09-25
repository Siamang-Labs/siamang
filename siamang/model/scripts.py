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
from collections.abc import Container, Iterable, Mapping
from dataclasses import replace
from typing import Any

from siamang.core.script import _QUESTION_SCOPED_TRIGGERS, Script

_TIMEOUT_RE = re.compile(r"const timeout = (\d+);")
# A JavaScript identifier, near enough: a letter, `_` or `$`, then letters,
# digits, `_` or `$` — `\w` is Unicode-aware, as JavaScript's IdentifierName is.
_JS_IDENTIFIER_CHAR = r"[\w$]"
_JS_IDENTIFIER_RE = re.compile(r"^(?:[^\W\d]|\$)[\w$]*$")
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


def script_for_runtime(script: Script, aliases: Mapping[str, str]) -> Script:
    """The script as the runtime must see it when a question's answer key is
    not its id.

    Authors name questions by id: in ``target``, in ``randomize_options`` and
    ``timed_question``, in the two fields of ``validate_fields_match``. The
    runtime matches the ``target`` of an ``onQuestionShow`` or ``onAnswer``
    script against the item's answer key and reads ``answers[…]`` /
    ``__options__[…]`` by it. ``aliases`` maps a design-time id to that key
    (see ``question_output_name``); an id that already is the key is not in
    the map, and such a script comes back unchanged — which is every script of
    a survey whose ids are its variable names.

    A library script is regenerated from its parameters rather than patched,
    so the code the runtime runs is exactly what the factory writes for the
    key; its question is a question by construction. A custom script has its
    ``target`` translated only when its trigger is question-scoped: an
    ``onPageEnter`` / ``onPageExit`` target is a page name, which may equal a
    question id, and a target on ``onInit``, ``onSubmit`` or ``onRandomize``
    is never matched, so those are left as written. In its code, the reads
    and writes that name an aliased id — ``answers["q1"]``, ``answers.q1``,
    ``__errors__["q1"]``, ``__options__.q1``, ``__timers__[…]`` and the quote,
    whitespace and optional-chaining variants (see
    :func:`rewrite_answer_keys`) — are rewritten; the rest of the code is the
    author's, and what it may still say about the id is
    :func:`stale_answer_key_references`' business.
    """

    if not aliases:
        return script
    library = _detect_library_script(script)
    if library is not None:
        mapped = dict(library)
        for key in ("question", "field_a", "field_b"):
            if key in mapped:
                mapped[key] = aliases.get(mapped[key], mapped[key])
        return script_from_document(mapped) if mapped != library else script
    target = script.target
    if target is not None and script.trigger in _QUESTION_SCOPED_TRIGGERS:
        target = aliases.get(target, target)
    code = rewrite_answer_keys(script.code, aliases)
    if target == script.target and code == script.code:
        return script
    return replace(script, target=target, code=code)


# What the runtime keys by the item id: the answers themselves and, under
# `answers`, the validation messages (`__errors__`), the shuffled option order
# (`__options__`) and the timer handles `timed_question` keeps (`__timers__`).
_ANSWER_STORE = "answers"
_ANSWER_SUBSTORES = ("__errors__", "__options__", "__timers__")


def rewrite_answer_keys(code: str, aliases: Mapping[str, str]) -> str:
    """Rewrite the accesses in ``code`` that name a question by an aliased id
    to name its answer key.

    The runtime keeps answers, validation errors, shuffled options and timer
    handles under the item id — the answer key. A custom script written
    against the question id reaches for ``answers["q1"]`` and finds nothing
    once the key is ``nps_1``. This rewrites exactly the access forms
    ``answers["<id>"]``, ``answers['<id>']``, ``answers[`<id>`]`` — with or
    without whitespace inside the brackets — and ``answers.<id>``, and the
    same on ``__errors__``, ``__options__`` and ``__timers__`` (so
    ``answers.__errors__["q1"]`` is covered), with or without ``?.``, for the
    ids in ``aliases`` and nothing else: the id must fill the whole property
    (``q1`` leaves ``q10`` and ``q1x`` alone), a string that is not one of
    these accesses is not touched, an id that is not aliased is not touched,
    and a head that is itself a property of something else —
    ``state.answers.q1``, ``ctx?.answers["q1"]``, ``snapshot.__errors__.q1``
    — is some other object's and is not touched either (the stale check
    reports what it still says). An id that is not a JavaScript identifier
    can only have been written in the bracket form, so only that form is
    looked for; a key that
    is not one is emitted in the bracket form, and a key that could not be
    spelled verbatim in the author's quotes is emitted as a JSON literal.
    """

    if not aliases or not code:
        return code
    ordered = sorted(aliases, key=len, reverse=True)
    bracket_ids = "|".join(re.escape(alias) for alias in ordered)
    # `(?!)` never matches: it keeps the dot groups defined when no id is an
    # identifier.
    dot_ids = (
        "|".join(re.escape(alias) for alias in ordered if _JS_IDENTIFIER_RE.match(alias)) or "(?!)"
    )
    substores = "|".join(_ANSWER_SUBSTORES)
    # The head is the runtime's `answers`, one of its sub-stores reached from
    # it (`answers.__errors__`, `answers?.__options__`) or a sub-store on its
    # own. Not a head: an `answers` or `__errors__` preceded by `.` or `?.` —
    # a property of some other object.
    head = (
        rf"(?<!{_JS_IDENTIFIER_CHAR})(?<!\.)"
        rf"(?:{_ANSWER_STORE}(?:\??\.(?:{substores}))?|(?:{substores}))"
    )
    pattern = re.compile(
        rf"(?P<head>{head})"
        rf"(?:"
        rf"(?P<chain>\?\.)?\[(?P<lpad>\s*)(?P<quote>[\"'`])(?P<bracket_id>{bracket_ids})"
        rf"(?P=quote)(?P<rpad>\s*)\]"
        rf"|(?P<dot>\??\.)(?P<dot_id>{dot_ids})(?!{_JS_IDENTIFIER_CHAR})"
        rf")"
    )

    def substitute(match: re.Match[str]) -> str:
        head = match.group("head")
        if match.group("bracket_id") is not None:
            key = aliases[match.group("bracket_id")]
            literal = _js_string_literal(key, match.group("quote"))
            return (
                f"{head}{match.group('chain') or ''}"
                f"[{match.group('lpad')}{literal}{match.group('rpad')}]"
            )
        key = aliases[match.group("dot_id")]
        dot = match.group("dot")
        if _JS_IDENTIFIER_RE.match(key):
            return f"{head}{dot}{key}"
        # A key that is not a JavaScript identifier can only be reached by
        # subscript; keep the optional chaining if the author used it.
        chain = "?." if dot == "?." else ""
        return f"{head}{chain}[{json.dumps(key)}]"

    return pattern.sub(substitute, code)


def _js_string_literal(key: str, quote: str) -> str:
    """``key`` as a JavaScript string in the author's quotes — or, when it
    could not be spelled in them verbatim (it contains that quote, a backslash,
    or ``${`` inside backticks), as the JSON literal every engine reads."""

    if quote in key or "\\" in key or (quote == "`" and "${" in key):
        return json.dumps(key)
    return f"{quote}{key}{quote}"


def stale_answer_key_references(script: Script, aliases: Mapping[str, str]) -> list[str]:
    """The aliased ids a custom script's code still names once
    :func:`script_for_runtime` has rewritten it — as a whole string literal
    (``"q1"``, ``'q1'``, ```q1```) or as a bare identifier (``q1`` that is not
    a property of something) — in the order of ``aliases``, each once.

    :func:`rewrite_answer_keys` translates the access forms it knows and
    nothing else, so ``const q = "q1"; answers[q]``, ``utils.pick(answers,
    "q1")`` or ``{q1: 1}`` reach the runtime naming a question the runtime
    does not know by that name. ``lint(level="strict")`` reports each as
    ``SCRIPT_STALE_QUESTION_ID`` so the author is told instead of the script
    going dark. A library script is regenerated whole and has none. Comments
    are not code and a string that merely mentions the id (``"see q1"``) is
    not a reference to it: both are left out of the scan (see
    :func:`_scannable_code`).
    """

    if not aliases or not script.code or _detect_library_script(script) is not None:
        return []
    code = _scannable_code(script_for_runtime(script, aliases).code, aliases)
    stale: list[str] = []
    for design_id in aliases:
        escaped = re.escape(design_id)
        quoted = re.search(rf"([\"'`]){escaped}\1", code)
        bare = _JS_IDENTIFIER_RE.match(design_id) and re.search(
            rf"(?<!{_JS_IDENTIFIER_CHAR})(?<!\.){escaped}(?!{_JS_IDENTIFIER_CHAR})", code
        )
        if quoted or bare:
            stale.append(design_id)
    return stale


# An assignment to what precedes it: `=`, a compound one (`+=`, `??=`, …) —
# not a comparison (`==`, `<=`) — or an increment or decrement after it.
_WRITE_AFTER = r"\s*(?:(?:\*\*|<<|>>>?|&&|\|\||\?\?|[-+*/%&|^])?=(?!=)|\+\+|--)"


def answer_keys_written(script: Script, names: Iterable[str]) -> list[str]:
    """Which of ``names`` a custom script's code writes an answer under —
    ``answers.panel = …``, ``answers["panel"] += …``, ``answers.panel++`` —
    outside its comments and strings, in the order of ``names``, each once.

    Read in the code as the author wrote it, before :func:`script_for_runtime`
    rewrites the accesses that name an aliased id. A library script writes
    what its factory makes it write (``Script.assigns``) and is not scanned.
    """

    wanted = list(dict.fromkeys(names))
    if not wanted or not script.code or _detect_library_script(script) is not None:
        return []
    code = _scannable_code(script.code, set(wanted))
    head = rf"(?<!{_JS_IDENTIFIER_CHAR})(?<!\.)answers\s*"
    written: list[str] = []
    for name in wanted:
        escaped = re.escape(name)
        dot = rf"\.\s*{escaped}(?!{_JS_IDENTIFIER_CHAR})|" if _JS_IDENTIFIER_RE.match(name) else ""
        access = rf"{head}(?:{dot}\[\s*([\"'`]){escaped}\1\s*\])"
        if re.search(rf"{access}{_WRITE_AFTER}", code) or re.search(
            rf"(?:\+\+|--)\s*{access}", code
        ):
            written.append(name)
    return written


def _scannable_code(code: str, keep: Container[str]) -> str:
    """``code`` with its ``//`` and ``/* */`` comments removed and every string
    literal emptied — except a literal whose whole content is one of ``keep``,
    which is exactly the quoted reference the stale scan is after. The
    expressions of a template literal (``${…}``) are code and are kept,
    scanned the same way. Near enough to JavaScript: a regular-expression
    literal is read as code."""

    out: list[str] = []
    i, n = 0, len(code)
    while i < n:
        char = code[i]
        if char == "/" and code.startswith("//", i):
            end = code.find("\n", i)
            i = n if end < 0 else end  # the newline itself is kept
            continue
        if char == "/" and code.startswith("/*", i):
            end = code.find("*/", i + 2)
            out.append(" ")
            i = n if end < 0 else end + 2
            continue
        if char in "\"'`":
            quote = char
            body: list[str] = []
            expressions: list[str] = []
            j = i + 1
            while j < n and code[j] != quote:
                if code[j] == "\\":
                    body.append(code[j : j + 2])
                    j += 2
                elif quote == "`" and code.startswith("${", j):
                    depth, k = 1, j + 2
                    while k < n and depth:
                        depth += {"{": 1, "}": -1}.get(code[k], 0)
                        k += 1
                    expressions.append(code[j + 2 : k - 1 if depth == 0 else k])
                    j = k
                else:
                    body.append(code[j])
                    j += 1
            text = "".join(body)
            out.append(f"{quote}{text}{quote}" if not expressions and text in keep else quote * 2)
            out.extend(f" ({_scannable_code(expression, keep)}) " for expression in expressions)
            i = j + 1
            continue
        out.append(char)
        i += 1
    return "".join(out)


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
