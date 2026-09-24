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
    na_code,
    none_code,
    other_code,
    other_text_key,
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
        # The header shows when there is something to show; the title is in it
        # only when show_title says so — a logo or an institution alone must not
        # bring the title back.
        "showHeader": ui.show_title or bool(ui.institution_name) or bool(ui.logo_url),
        "showTitle": ui.show_title,
        "showProgress": options.get("show_progress", True),
        # The section label above a page's title ("Welcome", "Section 2 of 5",
        # "Final thoughts") and the text beside the progress bar.
        "showSectionNumbers": ui.show_section_numbers,
        "showProgressText": ui.show_progress_text,
        "estimatedMinutes": ui.estimated_minutes,
        "ethics": ui.ethics_statement or "",
        "privacyUrl": ui.privacy_url or "",
        "contactEmail": ui.contact_email or "",
        # The completion screen: the UI's wording first, then the compiler
        # options (`completion_text` is the document's "Message").
        "completedTitle": ui.completion_title or options.get("completion_title"),
        "completedBody": ui.completion_body or options.get("completion_text"),
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
    for name in _WORDING_FIELDS:
        survey_meta[_camel(name)] = getattr(ui, name)

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

    # A page carries no section label ("Welcome", "Section 2 of 5"): the
    # runtime works it out from the pages the respondent actually goes through,
    # in their order and without the terminal pages, and words it from the UI
    # texts.
    # The labels the compiler writes into options ("None of the above", "Not
    # applicable"), in the survey's wording.
    texts = {
        "none_of_above": ui.none_of_above_text or "None of the above",
        "not_applicable": ui.not_applicable_text or "Not applicable",
    }
    pages = [_compile_page(page, skip_targets=skip_targets, texts=texts) for page in pages_src]

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

    quota_vars = _quota_variables(options)
    if quota_vars:
        # The variables some quota cell counts. Leaving a page, the runtime asks
        # the transport's checkQuota about each of them that has a new value,
        # and ends the interview as "quota full" when a cell is. The cells'
        # values and limits stay on the server.
        survey_meta["quotaVars"] = quota_vars

    return {"SURVEY": survey_meta, "PAGES": pages}


# The rest of the runtime's wording (UIConfig), sent as `SURVEY.<camelCase>`;
# a None leaves the runtime's English default in place.
_WORDING_FIELDS = (
    "welcome_text",
    "section_text",
    "final_section_text",
    "estimated_time_text",
    "other_text",
    "other_placeholder",
    "min_choices_text",
    "max_reached_text",
    "min_value_text",
    "max_value_text",
    "chars_remaining_text",
    "search_placeholder",
    "no_options_text",
    "ranking_hint_text",
    "ranking_remaining_text",
    "invalid_format_text",
    "invalid_email_text",
    "invalid_phone_text",
    "invalid_url_text",
    "invalid_date_text",
    "invalid_time_text",
    "response_id_text",
    "submitted_text",
    "screen_out_title",
    "redirect_countdown_text",
    "redirect_link_text",
    "redirecting_text",
    "redirecting_link_text",
    "quota_full_title",
    "quota_full_body",
    "closed_title",
    "closed_body",
    "error_title",
    "error_body",
    "attempt_text",
    "privacy_text",
    "contact_text",
    "skip_link_text",
    "access_error",
    "page_error_title",
    "page_error_body",
    "app_error_title",
    "app_error_body",
    "reload_action",
)


def _camel(name: str) -> str:
    head, *rest = name.split("_")
    return head + "".join(part.capitalize() for part in rest)


def _quota_variables(options: Mapping[str, Any]) -> list[str]:
    """The variables of the quotas in the compiler options: ``quota`` as
    :class:`~siamang.core.Quota` objects (``survey.compile(quota=…)``) or
    ``quotas`` as the compiled ``{variable, target_value, limit}`` dicts the
    schema carries (``ReactRuntime``)."""

    names: list[str] = []
    for quota in [*(options.get("quota") or []), *(options.get("quotas") or [])]:
        name = (
            quota.get("variable")
            if isinstance(quota, Mapping)
            else getattr(quota, "variable", None)
        )
        if isinstance(name, str) and name and name not in names:
            names.append(name)
    return names


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
    page: Page,
    *,
    skip_targets: Mapping[str, str] | None = None,
    texts: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": page.name,
        "title": page.title or "",
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
                                _compile_question(q, skip_targets=skip_targets, texts=texts)
                                for q in loose
                            ],
                        }
                    )
                    loose = []
                blocks.append(_compile_block(item, skip_targets=skip_targets, texts=texts))
            else:
                loose.append(item)
        if loose:
            blocks.append(
                {
                    "title": "",
                    "items": [
                        _compile_question(q, skip_targets=skip_targets, texts=texts) for q in loose
                    ],
                }
            )
        payload["blocks"] = blocks
    else:
        payload["items"] = [
            _compile_question(q, skip_targets=skip_targets, texts=texts)
            for q in page.flatten_questions()
        ]

    return payload


def _compile_block(
    block: Block,
    *,
    skip_targets: Mapping[str, str] | None = None,
    texts: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "title": block.title or "",
        "items": [
            _compile_question(q, skip_targets=skip_targets, texts=texts)
            for q in block.flatten_questions()
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
    question: Question,
    *,
    skip_targets: Mapping[str, str] | None = None,
    texts: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """One runtime item. ``skip_targets`` maps a design-time question id to
    the name of the page that holds the question, for every id that is not
    also a page name; a ``skip_to`` that names a question is emitted as that
    page name, and a ``skip_to`` that names a page is left alone. ``texts``
    words the labels the compiler adds ("none_of_above", "not_applicable")."""

    texts = texts or {}
    not_applicable = texts.get("not_applicable", "Not applicable")

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
            # A code of the variable (none_code), like every other answer.
            options = [
                *options,
                {
                    "code": none_code(question),
                    "label": texts.get("none_of_above", "None of the above"),
                    "noneOfAbove": True,
                    "fixed": True,
                },
            ]
        payload = {
            **base,
            "kind": kind,
            "display": question.display,
            "options": _pin_options(question, options),
        }
        if question.other_specify:
            payload.update(_other_payload(question))
        return payload
    if isinstance(question, MultiChoice):
        if question.mode == "wide":
            options = _wide_options(question)
        else:
            options = _options_payload(question.var, question.choices)
        payload = {**base, "kind": "multi", "options": _pin_options(question, options)}
        if question.mode == "wide":
            # Each option names the variable it sets: 1 when chosen, 0 when the
            # question is answered and it is not. Nothing is stored under the id.
            payload["wide"] = True
        if question.min_answers > 0:
            payload["min"] = question.min_answers
        if question.max_answers is not None:
            payload["max"] = question.max_answers
        if question.exclusive:
            payload["exclusive"] = list(question.exclusive)
        if question.other_specify:
            payload.update(_other_payload(question))
        return payload
    if isinstance(question, LikertScale):
        payload = {
            **base,
            "kind": "likert",
            "points": question.points,
            "start": question.start,
            "display": question.display,
            "leftLabel": question.left_label or "",
            "rightLabel": question.right_label or "",
            "naOption": question.na_option
            if isinstance(question.na_option, str)
            else (not_applicable if question.na_option else None),
        }
        if question.na_option and na_code(question.var) is not None:
            # The codebook's not_applicable code; without one the runtime
            # stores "na" (see na_code).
            payload["naCode"] = na_code(question.var)
        return payload
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
        # The headers, and the codebook code each column stores (Matrix.columns):
        # a cell used to store its position + 1, so any scale not coded 1…n —
        # 0–10, a recode, a "Refused" 9 — was recorded as the wrong value.
        pairs = question.columns()
        columns = [header for _code, header in pairs]
        if question.subquestions is not None:
            rows = [
                {"id": v.name, "label": label}
                for v, label in zip(question.var, question.subquestions, strict=False)
            ]
        else:
            rows = [{"id": v.name, "label": v.label or v.name} for v in question.var]
        if question.na_option:
            # Each row stores its own variable's not_applicable code, or "na".
            for row, variable in zip(rows, question.var, strict=False):
                if na_code(variable) is not None:
                    row["naCode"] = na_code(variable)
        payload = {
            **base,
            "kind": "matrix",
            "columns": columns,
            "columnCodes": [code for code, _header in pairs],
            "rows": rows,
        }
        if question.na_option:
            payload["naOption"] = (
                question.na_option if isinstance(question.na_option, str) else not_applicable
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


def _pin_options(
    question: SingleChoice | MultiChoice, options: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Mark the options a shuffle leaves in their place (``"fixed": true``):
    "None of the above", a MultiChoice's exclusive answers and a choice that is
    the question's "Other (please specify)". They close a list, and an order
    that moved "None of these" or "Other" into the middle would be read as a
    different question; the runtime's own Other, added after the options, is
    never shuffled. The question's Randomize switch and
    ``Script.randomize_options`` shuffle the rest among the remaining slots."""

    exclusive = list(getattr(question, "exclusive", None) or [])
    other = other_code(question) if question.other_specify else None
    pinned = []
    for option in options:
        code = option.get("code")
        if option.get("noneOfAbove") or code in exclusive or (other is not None and code == other):
            option = {**option, "fixed": True}
        pinned.append(option)
    return pinned


def _other_payload(question: SingleChoice | MultiChoice) -> dict[str, Any]:
    """ "Other (please specify)": the code the choice stores (``other_code``)
    and the key its text goes to (``other_text_key``). When the code is one of
    the question's own options, that option is the Other one and the runtime
    adds none of its own."""

    payload: dict[str, Any] = {
        "otherSpecify": True,
        "otherCode": other_code(question),
        "otherKey": other_text_key(question),
    }
    other_meta = question.metadata or {}
    if other_meta.get("other_label"):
        payload["otherLabel"] = other_meta["other_label"]
    if other_meta.get("other_placeholder"):
        payload["otherPlaceholder"] = other_meta["other_placeholder"]
    return payload


def _wide_options(question: MultiChoice) -> list[dict[str, Any]]:
    """A wide MultiChoice's options, each with the 0/1 variable it sets.

    With one choice per variable — the layout Studio's Builder writes — option
    ``i`` is choice ``i`` (its code, which ``exclusive`` names, its label,
    conditions and media) on variable ``i``. Without choices, or with a
    different number of them, an option is its variable: the variable's name
    is its code and its label the option's.
    """

    variables = list(question.var)
    choices = question.choices or []
    if len(choices) == len(variables):
        return [
            {**_option_to_dict(choice), "var": variable.name}
            for choice, variable in zip(choices, variables, strict=True)
        ]
    return [
        {"code": variable.name, "label": variable.label or variable.name, "var": variable.name}
        for variable in variables
    ]


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
            if js_op in ("===", "!==") and (node.left is None or node.right is None):
                # Loose against null. The store has no key for a question
                # nobody answered — its value is `undefined`, not `null` — and
                # `x != null` ("x was answered") must be false for it, as
                # Expression.evaluate has it, where a missing answer is None.
                # `== null` holds for undefined and null and nothing else, so an
                # attention check written `x != null and x != 3` no longer
                # screens out a respondent who left an optional check empty.
                js_op = js_op[:-1]
            return f"({left_js}{js_op}{right_js})"

        if node.op in ("in", "not in", "notin"):
            if _names_none(node.right):
                # `x in [None, …]`: an unanswered question is None there too.
                left_js = f"({left_js}===undefined?null:{left_js})"
            if node.op == "in":
                return f"(Array.isArray({right_js})&&{right_js}.includes({left_js}))"
            return f"(!Array.isArray({right_js})||!{right_js}.includes({left_js}))"

        if node.op in ("contains", "not contains", "notcontains"):
            # "Did they choose this code", the question `=` cannot answer for a
            # MultiChoice. A single answer contains what it equals, matching
            # Expression.evaluate, so the condition survives a question being
            # changed from several answers to one. Deliberately *not* the
            # substring test the raw-string parser does for scalars: these codes
            # are codes, and "11" must not match 1.
            same = "==" if node.right is None else "==="  # loose against null, as above
            scalar = f"{left_js}{same}{right_js}"
            test = f"(Array.isArray({left_js})?{left_js}.includes({right_js}):{scalar})"
            return test if node.op == "contains" else f"(!{test})"

        return None  # Unknown operator

    # Literal value (shouldn't appear as top-level condition, but handle gracefully)
    return _value_to_js(node)


def _names_none(value: Any) -> bool:
    """Whether a literal list on the right of ``in`` holds None."""
    return isinstance(value, list | tuple | set) and any(item is None for item in value)


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
