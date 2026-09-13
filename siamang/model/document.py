"""The questionnaire as a JSON document.

``to_document`` walks a :class:`~siamang.core.Questionnaire` (plus the
module-level ``options`` dict that carries compiler settings, quotas and the
theme) and produces a plain JSON-compatible dict. ``from_document`` rebuilds
the engine objects from such a dict. The two are inverse of each other:

* ``from_document(to_document(survey, options))`` compiles to the same
  :class:`~siamang.frontend.schema.SurveySchema` as ``survey`` itself, and
* ``to_document(*from_document(doc))`` returns ``doc`` unchanged for any
  document ``to_document`` produced.

The document is what a graphical builder stores and edits; the Python file is
what it hands to researchers. Both describe the same survey, so the format is
deliberately close to the dataclasses: one object per engine class, the same
field names, engine defaults left implicit only where the object is purely
structural (pages, blocks). Question objects list every field they carry so a
stored document keeps its meaning even if an engine default changes later.

Layout of a document (``schema_version`` 1.0)::

    schema_version  "1.0"
    title           str
    options         {language?, description?, completion_text?, show_progress?,
                     allow_back?, one_question_per_page?, max_responses?, metadata?}
    deadline        ISO 8601 datetime | null
    variables       {name: Variable}           in order of first use
    pages           [Page]
    quotas          [{variable, target_value, limit}]
    scripts         [LibraryScript | CustomScript]
    ui              {UIConfig fields that differ from the defaults}
    layout?         object                     builder-owned, opaque to the engine

The JSON Schema for the format lives in ``siamang/schemas``; see
:func:`siamang.model.validate_document`.
"""

from __future__ import annotations

import dataclasses
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from siamang.core.block import Block
from siamang.core.expression import Expression, VarRef
from siamang.core.media import Media
from siamang.core.option import Option
from siamang.core.page import Page
from siamang.core.question import (
    LikertScale,
    Matrix,
    MaxDiff,
    MultiChoice,
    NumericInput,
    OpenText,
    Question,
    Ranking,
    SingleChoice,
    question_fallback_id,
)
from siamang.core.questionnaire import Questionnaire
from siamang.core.quota import Quota
from siamang.core.variable import MissingValue, Variable, VariableMap
from siamang.frontend.theme.ui_config import UIConfig
from siamang.model.scripts import script_from_document, script_to_document

#: Version of the document format written by :func:`to_document`.
SCHEMA_VERSION = "1.0"

#: Engine question classes by the ``type`` name used in documents.
QUESTION_TYPES: dict[str, type[Question]] = {
    cls.__name__: cls
    for cls in (
        SingleChoice,
        MultiChoice,
        LikertScale,
        NumericInput,
        OpenText,
        Matrix,
        Ranking,
        MaxDiff,
    )
}

#: Keys of the compiler ``options`` dict that travel in ``document["options"]``.
#: ``quota`` and ``ui`` are lifted to their own top-level sections.
OPTION_KEYS = (
    "language",
    "description",
    "completion_text",
    "show_progress",
    "allow_back",
    "one_question_per_page",
    "max_responses",
    "metadata",
)

_QUESTION_HEAD = ("text", "var", "id", "name")
_CONDITION_FIELDS = ("show_if", "hide_if")
_SLUG_RE = re.compile(r"[^a-z0-9]+")

WarningSink = Callable[[str], None]


class DocumentError(ValueError):
    """A document (or a questionnaire) that cannot be converted."""


@dataclass(frozen=True, slots=True)
class LoadedSurvey:
    """What :func:`from_document` returns.

    ``options`` is ready to pass to ``survey.compile(**options)`` /
    ``survey.deploy(**options)`` and to :func:`siamang.core.validate_options`:
    it carries the compiler settings from ``document["options"]`` plus
    ``quota`` (a list of :class:`~siamang.core.Quota`) and ``ui``
    (a :class:`~siamang.frontend.UIConfig`) when the document defines them.
    """

    survey: Questionnaire
    options: dict[str, Any]
    layout: dict[str, Any] | None = None
    schema_version: str = SCHEMA_VERSION

    @property
    def quotas(self) -> list[Quota]:
        return list(self.options.get("quota") or [])

    @property
    def ui(self) -> UIConfig | None:
        return self.options.get("ui")


# ─── Questionnaire -> document ───────────────────────────────────────────────


def to_document(
    survey: Questionnaire,
    options: dict[str, Any] | None = None,
    *,
    layout: dict[str, Any] | None = None,
    on_warning: WarningSink | None = None,
) -> dict[str, Any]:
    """Serialize ``survey`` (and its compiler ``options``) into a document.

    Raises :class:`DocumentError` for anything that has no representation in
    the format — a callable condition, a non-JSON value in ``metadata``.
    Conversions that keep the compiled survey identical but change its shape
    (a ``blocks=`` questionnaire becoming pages, an ``options`` key the
    document does not carry) are reported through ``on_warning`` instead.
    """

    if not isinstance(survey, Questionnaire):
        raise DocumentError(f"Expected a Questionnaire, got {type(survey).__name__}.")
    warn = on_warning or (lambda message: None)
    opts = dict(options or {})

    variables = _collect_variables(survey)
    pages = _pages_of(survey, warn)

    document: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "title": survey.title,
        "options": _options_to_doc(opts, warn),
        "deadline": survey.deadline.isoformat() if survey.deadline is not None else None,
        "variables": {name: _variable_to_doc(variable) for name, variable in variables.items()},
        "pages": [_page_to_doc(page) for page in pages],
        "quotas": [_quota_to_doc(quota) for quota in opts.get("quota") or []],
        "scripts": [script_to_document(script) for script in survey.scripts],
        "ui": _ui_to_doc(opts.get("ui")),
    }
    if layout is not None:
        document["layout"] = _json_value(layout, "layout")
    return document


def _collect_variables(survey: Questionnaire) -> dict[str, Variable]:
    """Every variable of the survey, in order of first use, then registry-only ones."""

    variables: dict[str, Variable] = {}
    for question in survey.all_questions():
        for variable in _question_variables(question):
            known = variables.get(variable.name)
            if known is None:
                variables[variable.name] = variable
            elif known != variable:
                raise DocumentError(
                    f"Variable '{variable.name}' is defined twice with different settings."
                )
    if survey.variables:
        for name, variable in survey.variables.items():
            known = variables.get(name)
            if known is None:
                variables[name] = variable
            elif known != variable:
                raise DocumentError(
                    f"Variable '{name}' differs between the questionnaire and its registry."
                )
    return variables


def _question_variables(question: Question) -> list[Variable]:
    return list(question.var) if isinstance(question.var, list) else [question.var]


def _pages_of(survey: Questionnaire, warn: WarningSink) -> list[Page]:
    """Pages of the survey; a ``blocks=`` questionnaire is paged like the compiler does."""

    if survey.pages:
        return list(survey.pages)
    if not survey.blocks:
        return []
    if all(isinstance(item, Block) for item in survey.blocks):
        warn("Questionnaire uses blocks=; each top-level block became a page.")
        pages = []
        for index, block in enumerate(survey.blocks, start=1):
            assert isinstance(block, Block)
            name = _slugify(block.title) if block.title else f"page{index}"
            pages.append(Page(name=name, title=block.title, items=list(block.items)))
        return pages
    warn("Questionnaire uses blocks= with loose questions; everything went onto one page.")
    return [Page(name="page1", items=list(survey.all_questions()))]


def _options_to_doc(options: dict[str, Any], warn: WarningSink) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key in OPTION_KEYS:
        if key in options:
            payload[key] = _json_value(options[key], f"options.{key}")
    for key in options:
        if key not in OPTION_KEYS and key not in {"quota", "ui"}:
            warn(f"options['{key}'] is not part of the document format and was dropped.")
    quotas = options.get("quota")
    if quotas is not None and not isinstance(quotas, list | tuple):
        raise DocumentError("options['quota'] must be a list of Quota objects.")
    return payload


def _variable_to_doc(variable: Variable) -> dict[str, Any]:
    where = f"variable '{variable.name}'"
    payload: dict[str, Any] = {"scale": variable.scale}
    if variable.label is not None:
        payload["label"] = variable.label
    if variable.labels:
        payload["labels"] = [
            {"code": _code(code, where), "label": label} for code, label in variable.labels.items()
        ]
    if variable.missing:
        payload["missing"] = [
            {"code": _code(item.code, where), "label": item.label, "kind": item.kind}
            for item in variable.missing
        ]
    for name in ("dtype", "role", "description", "construct", "source"):
        value = getattr(variable, name)
        if value is not None:
            payload[name] = value
    if variable.valid_range is not None:
        low, high = variable.valid_range
        payload["valid_range"] = [_json_value(low, where), _json_value(high, where)]
    return payload


def _page_to_doc(page: Page) -> dict[str, Any]:
    payload: dict[str, Any] = {"name": page.name}
    if page.kind is not None:
        payload["kind"] = page.kind
    if page.title is not None:
        payload["title"] = page.title
    if page.body is not None:
        payload["body"] = page.body
    if page.redirect_url is not None:
        payload["redirect_url"] = page.redirect_url
    if page.redirect_delay is not None:
        payload["redirect_delay"] = page.redirect_delay
    if page.items or page.kind is None:
        payload["items"] = [_item_to_doc(item, f"page '{page.name}'") for item in page.items]
    where = f"page '{page.name}'"
    _put_conditions(payload, page, where)
    if page.next_if:
        payload["next_if"] = [
            {
                "condition": _condition_to_doc(condition, f"{where} next_if"),
                "target": target,
            }
            for condition, target in page.next_if
        ]
    if page.default_next is not None:
        payload["default_next"] = page.default_next
    if page.randomize_blocks:
        payload["randomize_blocks"] = True
    return payload


def _item_to_doc(item: Question | Block, where: str) -> dict[str, Any]:
    if isinstance(item, Block):
        return _block_to_doc(item, where)
    if isinstance(item, Question):
        return _question_to_doc(item)
    raise DocumentError(f"{where} contains a {type(item).__name__}; expected Question or Block.")


def _block_to_doc(block: Block, where: str) -> dict[str, Any]:
    payload: dict[str, Any] = {"type": "Block"}
    if block.title is not None:
        payload["title"] = block.title
    if block.randomize:
        payload["randomize"] = True
    location = f"block '{block.title}' in {where}" if block.title else f"block in {where}"
    _put_conditions(payload, block, location)
    payload["items"] = [_item_to_doc(item, location) for item in block.items]
    return payload


def _question_to_doc(question: Question) -> dict[str, Any]:
    type_name = type(question).__name__
    if type_name not in QUESTION_TYPES:
        raise DocumentError(f"Unsupported question class: {type_name}.")
    question_id = question_fallback_id(question)
    where = f"question '{question_id}'"
    payload: dict[str, Any] = {"type": type_name, "id": question_id}
    if question.name is not None:
        payload["name"] = question.name
    payload["text"] = question.text
    payload["var"] = (
        [variable.name for variable in question.var]
        if isinstance(question.var, list)
        else question.var.name
    )
    for field in dataclasses.fields(question):
        name = field.name
        if name in _QUESTION_HEAD:
            continue
        value = getattr(question, name)
        if value is None:
            continue
        if name in _CONDITION_FIELDS:
            payload[name] = _condition_to_doc(value, f"{where} {name}")
        elif name == "media":
            payload[name] = (
                [item.to_dict() for item in value] if isinstance(value, list) else value.to_dict()
            )
        elif name == "choices":
            payload[name] = [_option_to_doc(option, where) for option in value]
        elif name == "metadata":
            if value:
                payload[name] = _json_value(dict(value), f"{where} metadata")
        elif name == "tag":
            payload[name] = list(value) if isinstance(value, list) else value
        elif name == "exclusive":
            if value:
                payload[name] = [_code(code, where) for code in value]
        elif isinstance(value, list | tuple):
            payload[name] = [_json_value(item, f"{where} {name}") for item in value]
        else:
            payload[name] = _json_value(value, f"{where} {name}")
    return payload


def _option_to_doc(option: Option, where: str) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": _code(option.code, where), "label": option.label}
    location = f"option {option.code!r} of {where}"
    _put_conditions(payload, option, location)
    if option.media is not None:
        payload["media"] = option.media.to_dict()
    return payload


def _put_conditions(payload: dict[str, Any], holder: Any, where: str) -> None:
    for name in _CONDITION_FIELDS:
        value = getattr(holder, name)
        if value is not None:
            payload[name] = _condition_to_doc(value, f"{where} {name}")


def _quota_to_doc(quota: Any) -> dict[str, Any]:
    if not isinstance(quota, Quota):
        raise DocumentError(
            f"options['quota'] must contain Quota objects, got {type(quota).__name__}."
        )
    where = f"quota on '{quota.variable}'"
    return {
        "variable": quota.variable,
        "target_value": _code(quota.target_value, where),
        "limit": quota.limit,
    }


def _ui_to_doc(ui: Any) -> dict[str, Any]:
    if ui is None:
        return {}
    if not isinstance(ui, UIConfig):
        raise DocumentError(f"options['ui'] must be a UIConfig, got {type(ui).__name__}.")
    defaults = UIConfig()
    payload: dict[str, Any] = {}
    for field in dataclasses.fields(UIConfig):
        value = getattr(ui, field.name)
        if value != getattr(defaults, field.name):
            payload[field.name] = _json_value(value, f"ui.{field.name}")
    return payload


# ─── conditions ──────────────────────────────────────────────────────────────


def _condition_to_doc(value: Any, where: str) -> dict[str, Any]:
    if isinstance(value, str):
        return {"type": "raw", "text": value}
    if isinstance(value, Expression):
        return _expression_to_doc(value, where)
    if isinstance(value, VarRef):
        return value.to_dict()
    raise DocumentError(
        f"{where} is a {type(value).__name__}; only Expression or str conditions "
        "can be stored in a document."
    )


def _expression_to_doc(expression: Expression, where: str) -> dict[str, Any]:
    # Same shape as Expression.to_dict(); sets are ordered the way the
    # compiler renders them so the compiled survey does not depend on set order.
    return {
        "type": "expression",
        "op": expression.op,
        "left": _operand_to_doc(expression.left, where),
        "right": _operand_to_doc(expression.right, where),
    }


def _operand_to_doc(node: Any, where: str) -> Any:
    if isinstance(node, VarRef):
        return node.to_dict()
    if isinstance(node, Expression):
        return _expression_to_doc(node, where)
    if isinstance(node, set | frozenset):
        return [_operand_to_doc(item, where) for item in sorted(node, key=repr)]
    if isinstance(node, list | tuple):
        return [_operand_to_doc(item, where) for item in node]
    return _json_value(node, where)


def _condition_from_doc(payload: Any, where: str) -> Any:
    if payload is None:
        return None
    if not isinstance(payload, dict):
        raise DocumentError(f"{where}: condition must be an object, got {type(payload).__name__}.")
    kind = payload.get("type")
    try:
        if kind == "raw":
            return str(payload["text"])
        if kind == "expression":
            return Expression.from_dict(payload)
        if kind == "var":
            return VarRef.from_dict(payload)
    except (KeyError, ValueError) as exc:
        raise DocumentError(f"{where}: {exc}") from exc
    raise DocumentError(f"{where}: unknown condition type {kind!r}.")


# ─── document -> Questionnaire ───────────────────────────────────────────────


def from_document(document: dict[str, Any]) -> LoadedSurvey:
    """Rebuild the engine objects described by ``document``.

    Only the structure is checked here (a question must name a known variable,
    a page must have a name, …); run ``survey.validate()`` / ``survey.lint()``
    on the result for the questionnaire-level rules, exactly as for a survey
    written by hand. Raises :class:`DocumentError` with the location of the
    first problem.
    """

    if not isinstance(document, dict):
        raise DocumentError(f"Document must be an object, got {type(document).__name__}.")
    version = document.get("schema_version")
    if version != SCHEMA_VERSION:
        raise DocumentError(
            f"Unsupported schema_version {version!r}; this engine reads {SCHEMA_VERSION}."
        )
    title = document.get("title")
    if not isinstance(title, str):
        raise DocumentError("Document must have a string 'title'.")

    variables: dict[str, Variable] = {}
    for name, payload in (document.get("variables") or {}).items():
        variables[name] = _variable_from_doc(name, payload)

    pages = [
        _page_from_doc(payload, variables, f"pages[{index}]")
        for index, payload in enumerate(document.get("pages") or [])
    ]
    scripts = []
    for index, payload in enumerate(document.get("scripts") or []):
        try:
            scripts.append(script_from_document(payload))
        except (KeyError, TypeError, ValueError) as exc:
            raise DocumentError(f"scripts[{index}]: {exc}") from exc

    deadline_text = document.get("deadline")
    deadline = None
    if deadline_text is not None:
        try:
            deadline = datetime.fromisoformat(deadline_text)
        except (TypeError, ValueError) as exc:
            raise DocumentError(f"deadline: {exc}") from exc

    registry = VariableMap()
    registry.add_many(list(variables.values()))
    try:
        survey = Questionnaire(
            title=title,
            pages=pages,
            deadline=deadline,
            variables=registry,
            scripts=scripts,
        )
    except (TypeError, ValueError) as exc:
        raise DocumentError(str(exc)) from exc

    options: dict[str, Any] = {}
    for key, value in (document.get("options") or {}).items():
        if key not in OPTION_KEYS:
            raise DocumentError(f"options.{key}: unknown option.")
        options[key] = value
    quotas = []
    for index, payload in enumerate(document.get("quotas") or []):
        try:
            quotas.append(
                Quota(payload["variable"], payload["target_value"], int(payload["limit"]))
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise DocumentError(f"quotas[{index}]: {exc}") from exc
    if quotas:
        options["quota"] = quotas
    ui_payload = document.get("ui") or {}
    if ui_payload:
        try:
            options["ui"] = UIConfig(**ui_payload)
        except (TypeError, ValueError) as exc:
            raise DocumentError(f"ui: {exc}") from exc

    return LoadedSurvey(
        survey=survey,
        options=options,
        layout=document.get("layout"),
        schema_version=version,
    )


def _variable_from_doc(name: str, payload: Any) -> Variable:
    where = f"variables.{name}"
    if not isinstance(payload, dict):
        raise DocumentError(f"{where}: must be an object.")
    kwargs: dict[str, Any] = {"name": name}
    for key, value in payload.items():
        if key == "labels":
            kwargs["labels"] = _codebook_from_doc(value, where)
        elif key == "missing":
            try:
                kwargs["missing"] = tuple(
                    MissingValue(item["code"], item["label"], item.get("kind", "system_missing"))
                    for item in value
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise DocumentError(f"{where}.missing: {exc}") from exc
        elif key == "missing_values":
            kwargs["missing_values"] = tuple(value)
        elif key == "missing_labels":
            kwargs["missing_labels"] = _codebook_from_doc(value, f"{where}.missing_labels")
        elif key == "valid_range":
            if not isinstance(value, list | tuple) or len(value) != 2:
                raise DocumentError(f"{where}.valid_range: must be [min, max].")
            kwargs["valid_range"] = tuple(value)
        elif key in {"scale", "label", "dtype", "role", "description", "construct", "source"}:
            kwargs[key] = value
        else:
            raise DocumentError(f"{where}.{key}: unknown variable field.")
    if "scale" not in kwargs:
        raise DocumentError(f"{where}: 'scale' is required.")
    try:
        return Variable(**kwargs)
    except (TypeError, ValueError) as exc:
        raise DocumentError(f"{where}: {exc}") from exc


def _codebook_from_doc(value: Any, where: str) -> dict[Any, str]:
    """``[{code, label}]`` (canonical) or ``{"code": label}`` (shorthand) -> dict."""

    if isinstance(value, dict):
        return {_parse_code_key(code): str(label) for code, label in value.items()}
    if isinstance(value, list):
        labels: dict[Any, str] = {}
        for item in value:
            if not isinstance(item, dict) or "code" not in item or "label" not in item:
                raise DocumentError(f"{where}: each label needs 'code' and 'label'.")
            labels[item["code"]] = str(item["label"])
        return labels
    raise DocumentError(f"{where}: labels must be a list of {{code, label}} objects.")


def _parse_code_key(key: str) -> Any:
    """Object keys are always strings in JSON; recover the numeric codes."""

    if isinstance(key, str):
        if re.fullmatch(r"-?\d+", key):
            return int(key)
        try:
            return float(key)
        except ValueError:
            return key
    return key


def _page_from_doc(payload: Any, variables: dict[str, Variable], where: str) -> Page:
    if not isinstance(payload, dict):
        raise DocumentError(f"{where}: must be an object.")
    name = payload.get("name")
    if not isinstance(name, str) or not name.strip():
        raise DocumentError(f"{where}: page needs a non-empty 'name'.")
    where = f"page '{name}'"
    kwargs: dict[str, Any] = {"name": name}
    for key, value in payload.items():
        if key == "name":
            continue
        if key == "items":
            kwargs["items"] = [
                _item_from_doc(item, variables, f"{where} items[{index}]")
                for index, item in enumerate(value or [])
            ]
        elif key in _CONDITION_FIELDS:
            kwargs[key] = _condition_from_doc(value, f"{where} {key}")
        elif key == "next_if":
            kwargs["next_if"] = [
                (
                    _condition_from_doc(rule.get("condition"), f"{where} next_if[{index}]"),
                    rule["target"],
                )
                for index, rule in enumerate(value or [])
            ]
        elif key in {
            "kind",
            "title",
            "body",
            "redirect_url",
            "redirect_delay",
            "default_next",
            "randomize_blocks",
        }:
            kwargs[key] = value
        else:
            raise DocumentError(f"{where}: unknown page field '{key}'.")
    try:
        return Page(**kwargs)
    except (TypeError, ValueError) as exc:
        raise DocumentError(f"{where}: {exc}") from exc


def _item_from_doc(payload: Any, variables: dict[str, Variable], where: str) -> Question | Block:
    if not isinstance(payload, dict):
        raise DocumentError(f"{where}: must be an object.")
    type_name = payload.get("type")
    if type_name == "Block":
        return _block_from_doc(payload, variables, where)
    if type_name in QUESTION_TYPES:
        return _question_from_doc(payload, variables, where)
    raise DocumentError(f"{where}: unknown item type {type_name!r}.")


def _block_from_doc(payload: dict[str, Any], variables: dict[str, Variable], where: str) -> Block:
    kwargs: dict[str, Any] = {}
    for key, value in payload.items():
        if key == "type":
            continue
        if key == "items":
            kwargs["items"] = [
                _item_from_doc(item, variables, f"{where} items[{index}]")
                for index, item in enumerate(value or [])
            ]
        elif key in _CONDITION_FIELDS:
            kwargs[key] = _condition_from_doc(value, f"{where} {key}")
        elif key in {"title", "randomize"}:
            kwargs[key] = value
        else:
            raise DocumentError(f"{where}: unknown block field '{key}'.")
    return Block(**kwargs)


def _question_from_doc(
    payload: dict[str, Any], variables: dict[str, Variable], where: str
) -> Question:
    cls = QUESTION_TYPES[payload["type"]]
    question_id = payload.get("id")
    where = f"question '{question_id}'" if question_id else where
    allowed = {field.name for field in dataclasses.fields(cls)}
    kwargs: dict[str, Any] = {}
    for key, value in payload.items():
        if key == "type":
            continue
        if key not in allowed:
            raise DocumentError(f"{where}: {cls.__name__} has no field '{key}'.")
        if key == "var":
            names = value if isinstance(value, list) else [value]
            resolved = []
            for name in names:
                if name not in variables:
                    raise DocumentError(f"{where}: unknown variable '{name}'.")
                resolved.append(variables[name])
            kwargs["var"] = resolved if isinstance(value, list) else resolved[0]
        elif key in _CONDITION_FIELDS:
            kwargs[key] = _condition_from_doc(value, f"{where} {key}")
        elif key == "media":
            try:
                kwargs["media"] = (
                    [Media.from_dict(item) for item in value]
                    if isinstance(value, list)
                    else Media.from_dict(value)
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise DocumentError(f"{where} media: {exc}") from exc
        elif key == "choices":
            kwargs["choices"] = [
                _option_from_doc(item, f"{where} choices[{index}]")
                for index, item in enumerate(value)
            ]
        elif key == "metadata":
            kwargs["metadata"] = dict(value or {})
        else:
            kwargs[key] = value
    try:
        return cls(**kwargs)
    except (TypeError, ValueError) as exc:
        raise DocumentError(f"{where}: {exc}") from exc


def _option_from_doc(payload: Any, where: str) -> Option:
    if not isinstance(payload, dict) or "code" not in payload or "label" not in payload:
        raise DocumentError(f"{where}: option needs 'code' and 'label'.")
    kwargs: dict[str, Any] = {"code": payload["code"], "label": payload["label"]}
    for key, value in payload.items():
        if key in {"code", "label"}:
            continue
        if key in _CONDITION_FIELDS:
            kwargs[key] = _condition_from_doc(value, f"{where} {key}")
        elif key == "media":
            try:
                kwargs["media"] = Media.from_dict(value)
            except (KeyError, TypeError, ValueError) as exc:
                raise DocumentError(f"{where} media: {exc}") from exc
        else:
            raise DocumentError(f"{where}: unknown option field '{key}'.")
    try:
        return Option(**kwargs)
    except (TypeError, ValueError) as exc:
        raise DocumentError(f"{where}: {exc}") from exc


# ─── JSON helpers ────────────────────────────────────────────────────────────


def dumps(document: dict[str, Any]) -> str:
    """Canonical text form: two-space indent, keys in document order, UTF-8 as is."""

    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def loads(text: str) -> dict[str, Any]:
    document = json.loads(text)
    if not isinstance(document, dict):
        raise DocumentError("Document must be a JSON object.")
    return document


def _code(value: Any, where: str) -> Any:
    """An answer code: int, float or str (bool is a Python quirk, not a code)."""

    if isinstance(value, bool) or not isinstance(value, int | float | str):
        raise DocumentError(
            f"{where}: code {value!r} is a {type(value).__name__}; codes must be int, float or str."
        )
    return value


def _json_value(value: Any, where: str) -> Any:
    """Return ``value`` if it is JSON-representable (tuples become lists)."""

    if value is None or isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, list | tuple):
        return [_json_value(item, where) for item in value]
    if isinstance(value, dict):
        for key in value:
            if not isinstance(key, str):
                raise DocumentError(f"{where}: object keys must be strings, got {key!r}.")
        return {key: _json_value(item, f"{where}.{key}") for key, item in value.items()}
    raise DocumentError(f"{where}: {type(value).__name__} values cannot be stored in a document.")


def _slugify(value: str) -> str:
    slug = _SLUG_RE.sub("_", value.lower()).strip("_")
    return slug or "page"
