"""Compile a Questionnaire into the React-runtime payload (SURVEY + PAGES).

The output of :func:`compile_react_payload` is consumed by
``siamang/frontend/templates/react/app.jsx``. It is a JSON-serialisable dict
with two keys:

* ``SURVEY`` — study / branding metadata pulled from :class:`UIConfig` and
  the questionnaire title.
* ``PAGES`` — one entry per :class:`Page`, each carrying either ``items`` or
  ``blocks`` and (optionally) a compiled visibility condition.

This compiler reads directly from the live :class:`Questionnaire` objects;
unlike the SurveyJS-style serializer it preserves question-type-specific
fields (``display``, ``points``, ``leftLabel``, etc.) that the React
question components need.

Visibility conditions are compiled to JavaScript expression strings with
explicit dependency lists, so the browser runtime can use `new Function()`
once at load time instead of interpreting a JSON AST on every render.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from siamang.core.block import Block
from siamang.core.expression import Expression, VarRef
from siamang.core.media import Media
from siamang.core.option import Option
from siamang.core.page import Page
from siamang.core.question import (
    Conjoint,
    LikertScale,
    Matrix,
    MaxDiff,
    MultiChoice,
    NumericInput,
    OpenText,
    Question,
    Ranking,
    SingleChoice,
    answer_key_aliases,
    question_fallback_id,
    question_output_name,
)
from siamang.core.questionnaire import Questionnaire
from siamang.frontend.theme.ui_config import UIConfig


def compile_react_payload(
    survey: Questionnaire,
    *,
    ui: UIConfig | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return ``{"SURVEY": {...}, "PAGES": [...]}`` for the React runtime."""

    ui = ui or UIConfig()
    options = dict(options or {})
    pages_src = list(_pages_for_react(survey))

    survey_meta = {
        "title": survey.title,
        "language": options.get("language", "en"),
        "institution": ui.institution_name or "",
        "subtitle": ui.study_subtitle or options.get("description") or "",
        "logoUrl": ui.logo_url or "",
        "logoText": ui.effective_logo_text,
        "logoPosition": ui.logo_position,
        "showHeader": ui.show_title or bool(ui.institution_name) or bool(ui.logo_url),
        "showProgress": options.get("show_progress", True),
        "estimatedMinutes": ui.estimated_minutes,
        "ethics": ui.ethics_statement or "",
        "privacyUrl": ui.privacy_url or "",
        "contactEmail": ui.contact_email or "",
        "completedTitle": options.get("completion_title"),
        "completedBody": options.get("completion_text"),
        "nextButtonText": ui.next_button_text,
        "prevButtonText": ui.prev_button_text,
        "submitButtonText": ui.submit_button_text,
        "submittingText": ui.submitting_text,
        "requiredText": ui.required_text,
        "savingText": ui.saving_text,
        "selectPlaceholder": ui.select_placeholder,
        "ofText": ui.of_text,
        "selectedText": ui.selected_text,
        "resumeTitle": ui.resume_title,
        "resumeAction": ui.resume_action,
        "restartAction": ui.restart_action,
        "pageText": ui.page_text,
        "ofTotalText": ui.of_total_text,
        "retryTitle": ui.retry_title,
        "retryBody": ui.retry_body,
        "retryAction": ui.retry_action,
        "saveLocalAction": ui.save_local_action,
        "progressStyle": ui.progress_style,
        "defaultTheme": ui.default_theme,
        "allowThemeSwitch": ui.allow_theme_switch,
        "redirectUrl": ui.redirect_url,
        "screenOutRedirectUrl": ui.screen_out_redirect_url,
        "quotaFullRedirectUrl": ui.quota_full_redirect_url,
        "requireAccessCode": ui.require_access_code,
        "accessCodes": ui.access_codes,
        "accessTitle": ui.access_title,
        "accessBody": ui.access_body,
        "accessPlaceholder": ui.access_placeholder,
        "accessButton": ui.access_button,
        "enableAnalytics": ui.enable_analytics,
        "allowBack": ui.allow_back,
    }

    # The runtime's item id is the answer key — the variable for a
    # single-variable question — while authors name questions by id. Wherever
    # the payload names a question, the compiler hands the runtime something
    # it resolves without that id: a `skip_to` to a question becomes the name
    # of the page that holds it (the runtime resolves a target page-name first
    # and then by item id, so the outcome is the same and no id is left to
    # translate; a page name, even one equal to a question id, is left alone),
    # and a script's target and code are translated to the key below.
    page_names = {page.name for page in pages_src}
    skip_targets = {
        question_fallback_id(question): page.name
        for page in pages_src
        for question in page.flatten_questions()
        if question_fallback_id(question) not in page_names
    }

    pages: list[dict[str, Any]] = []
    total = len(pages_src)
    for index, page in enumerate(pages_src):
        pages.append(_compile_page(page, index=index, total=total, skip_targets=skip_targets))

    # Serialize scripts. The runtime matches a question-scoped script's target
    # — and a library script reads answers and options — by the item's answer
    # key, so a script naming an id whose key differs is rewritten to the key.
    from siamang.model.scripts import script_for_runtime

    aliases = answer_key_aliases(survey.all_questions())

    scripts_list = []
    for script in getattr(survey, "scripts", []):
        scripts_list.append(script_for_runtime(script, aliases).to_dict())
    survey_meta["scripts"] = scripts_list

    if any(s.trigger == "onRandomize" for s in getattr(survey, "scripts", [])):
        survey_meta["hasRandomizeScripts"] = True

    return {"SURVEY": survey_meta, "PAGES": pages}


def _pages_for_react(survey: Questionnaire):
    """Yield Page-like objects to render. Wraps a flat `blocks` list if needed."""

    if survey.pages:
        yield from survey.pages
        return
    items = list(survey.blocks)
    if not items:
        yield Page(name="page1", items=[])
        return
    if all(isinstance(item, Block) for item in items):
        for index, block in enumerate(items, start=1):
            assert isinstance(block, Block)
            page_name = _slugify(block.title) if block.title else f"page{index}"
            yield Page(name=page_name, title=block.title, items=block.items)
        return
    yield Page(name="page1", items=items)


def _compile_page(
    page: Page, *, index: int, total: int, skip_targets: Mapping[str, str] | None = None
) -> dict[str, Any]:
    section = f"Section {index} of {max(0, total - 1)}" if total > 1 and index > 0 else None
    if index == 0:
        section = "Welcome"
    if index == total - 1 and total > 1:
        section = "Final thoughts"

    payload: dict[str, Any] = {
        "name": page.name,
        "title": page.title or "",
        "section": section,
    }

    show_if = _compile_condition(page.show_if)
    if show_if is not None:
        payload["showIf"] = show_if
    hide_if = _compile_condition(page.hide_if)
    if hide_if is not None:
        payload["hideIf"] = hide_if

    # Custom page kinds (content / disqualification / final / redirect).
    if page.kind is not None:
        payload["kind"] = page.kind
    if page.body is not None:
        payload["body"] = page.body
    if page.redirect_url is not None:
        payload["redirectUrl"] = page.redirect_url
    if page.redirect_delay is not None:
        payload["redirectDelay"] = page.redirect_delay

    # Routing: next_if rules (first match wins) and the default_next fallback.
    if page.next_if:
        rules = []
        for condition, target in page.next_if:
            compiled = _compile_condition(condition)
            rules.append({"if": compiled, "target": target})
        payload["nextIf"] = rules
    if page.default_next is not None:
        payload["defaultNext"] = page.default_next
    if page.randomize_blocks:
        payload["randomizeBlocks"] = True

    has_block = any(isinstance(item, Block) for item in page.items)
    if has_block:
        blocks: list[dict[str, Any]] = []
        loose: list[Question] = []
        for item in page.items:
            if isinstance(item, Block):
                if loose:
                    blocks.append(
                        {
                            "title": "",
                            "items": [
                                _compile_question(q, skip_targets=skip_targets) for q in loose
                            ],
                        }
                    )
                    loose = []
                blocks.append(_compile_block(item, skip_targets=skip_targets))
            else:
                loose.append(item)
        if loose:
            blocks.append(
                {
                    "title": "",
                    "items": [_compile_question(q, skip_targets=skip_targets) for q in loose],
                }
            )
        payload["blocks"] = blocks
    else:
        payload["items"] = [
            _compile_question(q, skip_targets=skip_targets) for q in page.flatten_questions()
        ]

    return payload


def _compile_block(
    block: Block, *, skip_targets: Mapping[str, str] | None = None
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "title": block.title or "",
        "items": [
            _compile_question(q, skip_targets=skip_targets) for q in block.flatten_questions()
        ],
        # Marks a real authored Block (vs. a wrapper for loose questions), so
        # the runtime knows which entries page-level randomize_blocks may move.
        "isBlock": True,
    }
    if block.randomize:
        payload["randomize"] = True
    show_if = _compile_condition(block.show_if)
    if show_if is not None:
        payload["showIf"] = show_if
    hide_if = _compile_condition(block.hide_if)
    if hide_if is not None:
        payload["hideIf"] = hide_if
    return payload


def _compile_question(
    question: Question, *, skip_targets: Mapping[str, str] | None = None
) -> dict[str, Any]:
    """One runtime item. ``skip_targets`` maps a design-time question id to
    the name of the page that holds the question, for every id that is not
    also a page name; a ``skip_to`` that names a question is emitted as that
    page name, and a ``skip_to`` that names a page is left alone."""

    base: dict[str, Any] = {
        "id": question_output_name(question),
        "title": question.text,
        "required": bool(question.required),
    }
    if question.id:
        # The author-facing id (distinct from the output variable): design
        # mode reports clicks and highlights questions by it.
        base["qid"] = question.id
    if question.hint:
        base["description"] = question.hint
    if question.show_if is not None:
        condition = _compile_condition(question.show_if)
        if condition is not None:
            base["showIf"] = condition
    if question.hide_if is not None:
        condition = _compile_condition(question.hide_if)
        if condition is not None:
            base["hideIf"] = condition
    media = _serialise_media(question.media)
    if media is not None:
        base["media"] = media
    if question.skip_to is not None:
        # A page name, or a question id. The runtime resolves the target by
        # page name first and then by item id — the answer key, which need not
        # be the id — so a question is named by its page, where the runtime
        # would have landed anyway.
        base["skipTo"] = (skip_targets or {}).get(question.skip_to, question.skip_to)
    if question.randomize:
        base["randomize"] = True

    if isinstance(question, SingleChoice):
        kind = "dropdown" if question.display == "dropdown" else "single"
        options = _options_payload(question.var, question.choices)
        if question.none_of_above:
            # Sentinel code mirrors the runtime's "__other__" convention.
            options = [
                *options,
                {"code": "__none__", "label": "None of the above", "noneOfAbove": True},
            ]
        payload = {
            **base,
            "kind": kind,
            "display": question.display,
            "options": options,
        }
        if question.other_specify:
            payload["otherSpecify"] = True
            other_meta = question.metadata or {}
            if other_meta.get("other_label"):
                payload["otherLabel"] = other_meta["other_label"]
            if other_meta.get("other_placeholder"):
                payload["otherPlaceholder"] = other_meta["other_placeholder"]
        return payload
    if isinstance(question, MultiChoice):
        if question.mode == "wide":
            options = [{"code": v.name, "label": v.label or v.name} for v in question.var]
        else:
            options = _options_payload(question.var, question.choices)
        payload = {**base, "kind": "multi", "options": options}
        if question.min_answers > 0:
            payload["min"] = question.min_answers
        if question.max_answers is not None:
            payload["max"] = question.max_answers
        if question.exclusive:
            payload["exclusive"] = list(question.exclusive)
        if question.other_specify:
            payload["otherSpecify"] = True
            other_meta = question.metadata or {}
            if other_meta.get("other_label"):
                payload["otherLabel"] = other_meta["other_label"]
            if other_meta.get("other_placeholder"):
                payload["otherPlaceholder"] = other_meta["other_placeholder"]
        return payload
    if isinstance(question, LikertScale):
        return {
            **base,
            "kind": "likert",
            "points": question.points,
            "start": question.start,
            "display": question.display,
            "leftLabel": question.left_label or "",
            "rightLabel": question.right_label or "",
            "naOption": question.na_option
            if isinstance(question.na_option, str)
            else ("Not applicable" if question.na_option else None),
        }
    if isinstance(question, NumericInput):
        payload = {**base, "kind": "numeric", "display": question.display}
        if question.unit:
            payload["unit"] = question.unit
        if question.step:
            payload["step"] = question.step
        valid_range = getattr(question.var, "valid_range", None)
        if valid_range:
            payload["min"], payload["max"] = valid_range
        return payload
    if isinstance(question, OpenText):
        return {
            **base,
            "kind": "text",
            "multiline": question.multiline,
            "format": question.format,
            "maxChars": question.max_chars,
            "placeholder": question.placeholder or "",
        }
    if isinstance(question, Matrix):
        columns = question.column_labels or _columns_from_first_var(question.var)
        if question.subquestions is not None:
            rows = [
                {"id": v.name, "label": label}
                for v, label in zip(question.var, question.subquestions, strict=False)
            ]
        else:
            rows = [{"id": v.name, "label": v.label or v.name} for v in question.var]
        payload = {**base, "kind": "matrix", "columns": columns, "rows": rows}
        if question.na_option:
            payload["naOption"] = (
                question.na_option if isinstance(question.na_option, str) else "Not applicable"
            )
        return payload
    if isinstance(question, Ranking):
        payload = {
            **base,
            "kind": "ranking",
            "options": _options_payload(question.var, question.choices),
        }
        if question.max_ranked:
            payload["max"] = question.max_ranked
        return payload

    if isinstance(question, MaxDiff):
        design = question.resolved_design()
        # Every version travels, and the runtime picks one from the respondent
        # id: a round trip to the server to be told which design to show would
        # be one more thing between a respondent and their first question.
        return {
            **base,
            "kind": "maxdiff",
            "options": _options_payload(question.var, question.choices),
            "perTask": question.per_task,
            "tasks": question.tasks,
            "bestLabel": question.best_label,
            "worstLabel": question.worst_label,
            "versions": [[list(task) for task in version] for version in design.versions],
            # Variable names, so the component writes one answer per variable
            # instead of an object nothing downstream can read.
            "taskVars": [
                [best.name, worst.name]
                for best, worst in (question.task_variables(t) for t in range(question.tasks))
            ],
            "versionVar": question.version_variable.name,
        }

    if isinstance(question, Conjoint):
        design = question.resolved_design()
        return {
            **base,
            "kind": "conjoint",
            # The attribute rows, in the order the respondent reads them, with
            # every level's label — so a profile is rendered by lookup rather
            # than by shipping the same strings once per task.
            "attributes": [
                {
                    "name": attribute.name,
                    "label": attribute.label or attribute.name,
                    "levels": {str(level.code): level.label for level in attribute.levels},
                }
                for attribute in question.attributes
            ],
            "alternatives": question.alternatives,
            "tasks": question.tasks,
            "noneLabel": question.none_label,
            "versions": [
                [[list(profile) for profile in task] for task in version]
                for version in design.versions
            ],
            "taskVars": [question.task_variable(t).name for t in range(question.tasks)],
            "versionVar": question.version_variable.name,
        }

    return {**base, "kind": "text", "multiline": False}


def _options_payload(var: Any, choices: list[Option] | None) -> list[dict[str, Any]]:
    if choices:
        return [_option_to_dict(opt) for opt in choices]
    variables = var if isinstance(var, list) else [var]
    primary = variables[0]
    labels = getattr(primary, "labels", {}) or {}
    return [{"code": code, "label": label} for code, label in labels.items()]


def _option_to_dict(opt: Option) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": opt.code, "label": opt.label}
    show_if = _compile_condition(opt.show_if)
    if show_if is not None:
        payload["showIf"] = show_if
    hide_if = _compile_condition(opt.hide_if)
    if hide_if is not None:
        payload["hideIf"] = hide_if
    if opt.media is not None:
        payload["media"] = opt.media.to_dict()
    return payload


def _serialise_media(media: Media | list[Media] | None) -> list[dict[str, Any]] | None:
    if media is None:
        return None
    items = media if isinstance(media, list) else [media]
    return [item.to_dict() for item in items]


def _columns_from_first_var(variables: list[Any]) -> list[str]:
    if not variables:
        return []
    labels = getattr(variables[0], "labels", {}) or {}
    return [label for _, label in sorted(labels.items())]


# ─── Expression → JS compilation ─────────────────────────────────────────────


def _compile_condition(condition: Any) -> dict[str, Any] | None:
    """Compile a visibility condition into a { deps, fn } payload.

    The browser runtime uses ``new Function("a", "return " + fn)`` once at
    load time. ``deps`` lists the variable names the expression references,
    enabling fine-grained store subscriptions.

    Falls back to the legacy AST format for ``raw`` string expressions that
    cannot be safely compiled.
    """
    if condition is None:
        return None
    if isinstance(condition, (Expression, VarRef)):
        deps = sorted(condition.variables())
        js_body = _expr_to_js(condition)
        if js_body is not None:
            return {"deps": deps, "fn": js_body}
        # Fallback: raw expression that can't be compiled → legacy AST
        return condition.to_dict()
    if isinstance(condition, str):
        # Raw string condition — cannot compile safely
        return condition
    return None


def _expr_to_js(node: Any) -> str | None:
    """Recursively compile an Expression/VarRef tree to a JS expression string.

    Returns None if the expression contains a ``raw`` operator that cannot
    be safely translated.
    """
    if isinstance(node, VarRef):
        return f"a[{_js_string(node.name)}]"

    if isinstance(node, Expression):
        if node.op == "raw":
            return None  # Cannot compile raw strings

        if node.op == "not":
            left_js = _expr_to_js(node.left)
            if left_js is None:
                return None
            return f"!({left_js})"

        if node.op == "and":
            left_js = _expr_to_js(node.left)
            right_js = _expr_to_js(node.right)
            if left_js is None or right_js is None:
                return None
            return f"(({left_js})&&({right_js}))"

        if node.op == "or":
            left_js = _expr_to_js(node.left)
            right_js = _expr_to_js(node.right)
            if left_js is None or right_js is None:
                return None
            return f"(({left_js})||({right_js}))"

        # Comparison operators
        left_js = _expr_to_js(node.left)
        right_js = _value_to_js(node.right)
        if left_js is None or right_js is None:
            return None

        op_map = {
            "=": "===",
            "==": "===",
            "eq": "===",
            "!=": "!==",
            "ne": "!==",
            ">": ">",
            "gt": ">",
            ">=": ">=",
            "ge": ">=",
            "<": "<",
            "lt": "<",
            "<=": "<=",
            "le": "<=",
        }

        if node.op in op_map:
            js_op = op_map[node.op]
            return f"({left_js}{js_op}{right_js})"

        if node.op == "in":
            return f"(Array.isArray({right_js})&&{right_js}.includes({left_js}))"

        if node.op in ("not in", "notin"):
            return f"(!Array.isArray({right_js})||!{right_js}.includes({left_js}))"

        if node.op in ("contains", "not contains", "notcontains"):
            # "Did they choose this code", the question `=` cannot answer for a
            # MultiChoice. A single answer contains what it equals, matching
            # Expression.evaluate, so the condition survives a question being
            # changed from several answers to one. Deliberately *not* the
            # substring test the raw-string parser does for scalars: these codes
            # are codes, and "11" must not match 1.
            test = (
                f"(Array.isArray({left_js})?{left_js}.includes({right_js}):{left_js}==={right_js})"
            )
            return test if node.op == "contains" else f"(!{test})"

        return None  # Unknown operator

    # Literal value (shouldn't appear as top-level condition, but handle gracefully)
    return _value_to_js(node)


def _value_to_js(value: Any) -> str | None:
    """Convert a Python literal to a JS literal string."""
    if isinstance(value, VarRef):
        return f"a[{_js_string(value.name)}]"
    if isinstance(value, Expression):
        return _expr_to_js(value)
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return repr(value)
    if isinstance(value, str):
        return _js_string(value)
    if isinstance(value, list | tuple | set):
        items = [_value_to_js(v) for v in value]
        if any(i is None for i in items):
            return None
        return "[" + ",".join(items) + "]"
    return repr(value)


def _js_string(s: str) -> str:
    """Safely quote a string for JS (JSON-compatible quoting)."""
    import json

    return json.dumps(s, ensure_ascii=False)


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(value: str) -> str:
    slug = _SLUG_RE.sub("_", value.lower()).strip("_")
    return slug or "page"
