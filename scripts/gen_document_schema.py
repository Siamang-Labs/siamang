"""Generate ``siamang/schemas/questionnaire-1.0.json`` from the engine dataclasses.

The JSON Schema is committed so that non-Python consumers (a survey builder,
an editor) can validate documents without importing siamang. Re-run this
script whenever a core dataclass or UIConfig gains a field; the test suite
fails if the committed file is stale::

    python scripts/gen_document_schema.py
"""

from __future__ import annotations

import dataclasses
import json
import sys
import types
import typing
from pathlib import Path
from typing import Any

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
)
from siamang.core.script import _VALID_TRIGGERS
from siamang.core.variable import _VALID_DTYPES, _VALID_MISSING_KINDS, _VALID_ROLES, _VALID_SCALES
from siamang.frontend.theme.ui_config import (
    _DENSITY_VALUES,
    _FONT_PAIR_VALUES,
    _FONT_PRESET_VALUES,
    _LOGO_POSITIONS,
    _QUESTION_STYLES,
    UIConfig,
)
from siamang.model.document import OPTION_KEYS, SCHEMA_VERSION

OUT = (
    Path(__file__).resolve().parents[1]
    / "siamang"
    / "schemas"
    / f"questionnaire-{SCHEMA_VERSION}.json"
)

REF = "#/$defs/"


def ref(name: str) -> dict[str, str]:
    return {"$ref": REF + name}


def nullable(schema: dict[str, Any]) -> dict[str, Any]:
    return {"anyOf": [schema, {"type": "null"}]}


STRING = {"type": "string"}
BOOL = {"type": "boolean"}
INT = {"type": "integer"}
NUMBER = {"type": "number"}
NONEMPTY = {"type": "string", "minLength": 1}


def enum(values: set[str] | tuple[str, ...]) -> dict[str, Any]:
    return {"enum": sorted(values)}


# ─── Shared definitions ──────────────────────────────────────────────────────

DEFS: dict[str, Any] = {
    "scalar": {"type": ["string", "number", "boolean", "null"]},
    "code": {
        "description": "An answer code as used in Variable.labels: an integer, a number or a string.",
        "type": ["integer", "number", "string"],
    },
    "varref": {
        "type": "object",
        "properties": {"type": {"const": "var"}, "name": NONEMPTY},
        "required": ["type", "name"],
        "additionalProperties": False,
    },
    "operand": {
        "anyOf": [
            ref("expression"),
            ref("varref"),
            ref("scalar"),
            {"type": "array", "items": {"anyOf": [ref("scalar"), ref("varref")]}},
        ]
    },
    "expression": {
        "description": "Expression AST, as produced by Expression.to_dict().",
        "type": "object",
        "properties": {
            "type": {"const": "expression"},
            "op": {
                "enum": [
                    "=",
                    "!=",
                    ">",
                    ">=",
                    "<",
                    "<=",
                    "in",
                    "not in",
                    "contains",
                    "not contains",
                    "and",
                    "or",
                    "not",
                    "raw",
                ]
            },
            "left": ref("operand"),
            "right": ref("operand"),
        },
        "required": ["type", "op"],
        "additionalProperties": False,
    },
    "condition": {
        "description": "A visibility or branching condition.",
        "oneOf": [
            {
                "type": "object",
                "properties": {"type": {"const": "raw"}, "text": STRING},
                "required": ["type", "text"],
                "additionalProperties": False,
            },
            ref("expression"),
            ref("varref"),
        ],
    },
    "media": {
        "type": "object",
        "properties": {
            "url": NONEMPTY,
            "kind": {"enum": ["image", "video", "audio"]},
            "alt": STRING,
            "caption": STRING,
            "autoplay": BOOL,
            "loop": BOOL,
            "controls": BOOL,
        },
        "required": ["url"],
        "additionalProperties": False,
    },
    "option": {
        "type": "object",
        "properties": {
            "code": ref("code"),
            "label": NONEMPTY,
            "show_if": ref("condition"),
            "hide_if": ref("condition"),
            "media": ref("media"),
        },
        "required": ["code", "label"],
        "additionalProperties": False,
    },
    "labels": {
        "description": "Value labels in display order. The object form is accepted as shorthand.",
        "anyOf": [
            {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"code": ref("code"), "label": STRING},
                    "required": ["code", "label"],
                    "additionalProperties": False,
                },
            },
            {"type": "object", "additionalProperties": STRING},
        ],
    },
    "variable": {
        "type": "object",
        "properties": {
            "scale": enum(_VALID_SCALES),
            "label": STRING,
            "labels": ref("labels"),
            "missing": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "code": ref("code"),
                        "label": NONEMPTY,
                        "kind": enum(_VALID_MISSING_KINDS),
                    },
                    "required": ["code", "label"],
                    "additionalProperties": False,
                },
            },
            "missing_values": {"type": "array", "items": ref("code")},
            "missing_labels": {"type": "object", "additionalProperties": STRING},
            "dtype": enum(_VALID_DTYPES),
            "role": enum(_VALID_ROLES),
            "description": STRING,
            "construct": STRING,
            "source": STRING,
            "valid_range": {
                "type": "array",
                "items": nullable(NUMBER),
                "minItems": 2,
                "maxItems": 2,
            },
        },
        "required": ["scale"],
        "additionalProperties": False,
    },
    "block": {
        "type": "object",
        "properties": {
            "type": {"const": "Block"},
            "title": STRING,
            "randomize": BOOL,
            "show_if": ref("condition"),
            "hide_if": ref("condition"),
            "items": {"type": "array", "items": ref("item")},
        },
        "required": ["type", "items"],
        "additionalProperties": False,
    },
    "page": {
        "type": "object",
        "properties": {
            "name": NONEMPTY,
            "kind": {"enum": ["content", "disqualification", "final", "redirect"]},
            "title": STRING,
            "body": STRING,
            "redirect_url": STRING,
            "redirect_delay": {"type": "integer", "minimum": 0},
            "items": {"type": "array", "items": ref("item")},
            "show_if": ref("condition"),
            "hide_if": ref("condition"),
            "next_if": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "condition": nullable(ref("condition")),
                        "target": NONEMPTY,
                    },
                    "required": ["target"],
                    "additionalProperties": False,
                },
            },
            "default_next": NONEMPTY,
            "randomize_blocks": BOOL,
        },
        "required": ["name"],
        "additionalProperties": False,
    },
    "quota": {
        "type": "object",
        "properties": {
            "variable": NONEMPTY,
            "target_value": ref("code"),
            "limit": {"type": "integer", "minimum": 1},
        },
        "required": ["variable", "target_value", "limit"],
        "additionalProperties": False,
    },
    "script": {
        "oneOf": [
            {
                "type": "object",
                "properties": {
                    "type": {"const": "custom"},
                    "name": NONEMPTY,
                    "trigger": enum(_VALID_TRIGGERS),
                    "target": NONEMPTY,
                    "code": NONEMPTY,
                    "context": {"type": "object"},
                    "sandbox": BOOL,
                },
                "required": ["type", "code"],
                "additionalProperties": False,
            },
            {
                "type": "object",
                "properties": {
                    "type": {"const": "randomize_options"},
                    "question": NONEMPTY,
                    "seed": STRING,
                },
                "required": ["type", "question"],
                "additionalProperties": False,
            },
            {
                "type": "object",
                "properties": {
                    "type": {"const": "assign_condition"},
                    "variable": {"type": "string", "pattern": "^[A-Za-z_][A-Za-z0-9_]*$"},
                    "arms": {
                        "type": "array",
                        "minItems": 2,
                        "items": {
                            "type": "object",
                            "properties": {
                                "code": {"type": ["integer", "string"]},
                                "label": NONEMPTY,
                                "weight": {"type": "integer", "minimum": 1},
                            },
                            "required": ["code", "label"],
                            "additionalProperties": False,
                        },
                    },
                    "seed": STRING,
                    "balance": {"type": "boolean"},
                },
                "required": ["type", "variable", "arms"],
                "additionalProperties": False,
            },
            {
                "type": "object",
                "properties": {"type": {"const": "randomize_pages"}},
                "required": ["type"],
                "additionalProperties": False,
            },
            {
                "type": "object",
                "properties": {
                    "type": {"const": "timed_question"},
                    "question": NONEMPTY,
                    "seconds": {"type": "integer", "minimum": 1},
                },
                "required": ["type", "question", "seconds"],
                "additionalProperties": False,
            },
            {
                "type": "object",
                "properties": {
                    "type": {"const": "validate_fields_match"},
                    "field_a": NONEMPTY,
                    "field_b": NONEMPTY,
                    "message": STRING,
                },
                "required": ["type", "field_a", "field_b"],
                "additionalProperties": False,
            },
        ]
    },
}

# ─── Questions: base fields from the dataclass, specifics per type ───────────

_BASE_OVERRIDES: dict[str, Any] = {
    "text": NONEMPTY,
    "var": {"anyOf": [NONEMPTY, {"type": "array", "items": NONEMPTY, "minItems": 1}]},
    "required": BOOL,
    "hint": STRING,
    "show_if": ref("condition"),
    "hide_if": ref("condition"),
    "skip_to": NONEMPTY,
    "randomize": BOOL,
    "other_specify": BOOL,
    "tag": {"anyOf": [STRING, {"type": "array", "items": STRING}]},
    "id": NONEMPTY,
    "name": NONEMPTY,
    "media": {"anyOf": [ref("media"), {"type": "array", "items": ref("media")}]},
    "metadata": {"type": "object"},
}

_SPECIFIC: dict[type[Question], dict[str, Any]] = {
    SingleChoice: {
        "display": {"enum": ["radio", "dropdown", "buttons"]},
        "none_of_above": BOOL,
        "choices": {"type": "array", "items": ref("option"), "minItems": 1},
    },
    MultiChoice: {
        "min_answers": {"type": "integer", "minimum": 0},
        "max_answers": nullable({"type": "integer", "minimum": 0}),
        "exclusive": {"type": "array", "items": ref("code")},
        "mode": {"enum": ["array", "wide"]},
        "choices": {"type": "array", "items": ref("option"), "minItems": 1},
    },
    LikertScale: {
        "points": {"type": "integer", "minimum": 2},
        "left_label": STRING,
        "right_label": STRING,
        "na_option": {"type": ["boolean", "string"]},
        "start": {"enum": [0, 1]},
        "display": {"enum": ["scale", "stars"]},
    },
    NumericInput: {
        "display": {"enum": ["input", "slider"]},
        "unit": STRING,
        "step": {"type": "number", "exclusiveMinimum": 0},
    },
    OpenText: {
        "multiline": BOOL,
        "max_chars": {"type": "integer", "minimum": 1},
        "placeholder": STRING,
        "format": {"enum": ["text", "email", "phone", "url", "date", "time"]},
    },
    Matrix: {
        "var": {"type": "array", "items": NONEMPTY, "minItems": 1},
        "subquestions": {"type": "array", "items": STRING},
        "column_labels": {"type": "array", "items": STRING},
        "na_option": {"type": ["boolean", "string"]},
    },
    Ranking: {
        "max_ranked": {"type": "integer", "minimum": 1},
        "choices": {"type": "array", "items": ref("option"), "minItems": 1},
    },
    MaxDiff: {
        "var": {"type": "array", "items": NONEMPTY, "minItems": 3},
        "choices": {"type": "array", "items": ref("option"), "minItems": 3},
        "per_task": {"type": "integer", "minimum": 2},
        "tasks": {"type": "integer", "minimum": 1},
        "versions": {"type": "integer", "minimum": 1},
        "seed": {"type": ["integer", "null"]},
        "best_label": STRING,
        "worst_label": STRING,
        # The frozen design: the questionnaire is where it lives, so it travels
        # into the snapshot, the downloaded script and the provenance file.
        "design": {
            "type": ["object", "null"],
            "properties": {
                "items": {"type": "array", "minItems": 3},
                "per_task": {"type": "integer", "minimum": 2},
                "seed": {"type": ["integer", "null"]},
                "versions": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"type": "array", "minItems": 2},
                    },
                },
                "balance": {"type": "object"},
            },
            "required": ["items", "per_task", "versions"],
        },
    },
}


def question_schema(cls: type[Question]) -> dict[str, Any]:
    properties: dict[str, Any] = {"type": {"const": cls.__name__}}
    specifics = _SPECIFIC[cls]
    for field in dataclasses.fields(cls):
        if field.name in specifics:
            properties[field.name] = specifics[field.name]
        elif field.name in _BASE_OVERRIDES:
            properties[field.name] = _BASE_OVERRIDES[field.name]
        else:
            raise SystemExit(f"{cls.__name__}.{field.name} has no schema; add it to the generator.")
    unknown = set(specifics) - {field.name for field in dataclasses.fields(cls)}
    if unknown:
        raise SystemExit(f"{cls.__name__}: schema lists unknown fields {sorted(unknown)}.")
    return {
        "type": "object",
        "properties": properties,
        "required": ["type", "id", "text", "var"],
        "additionalProperties": False,
    }


for question_cls in _SPECIFIC:
    DEFS[question_cls.__name__] = question_schema(question_cls)

DEFS["item"] = {"oneOf": [ref("block"), *(ref(cls.__name__) for cls in _SPECIFIC)]}


# ─── UIConfig: one property per field, typed from the annotation ─────────────

_UI_ENUMS = {
    "font_preset": _FONT_PRESET_VALUES,
    "font_pair": _FONT_PAIR_VALUES,
    "density": _DENSITY_VALUES,
    "question_style": _QUESTION_STYLES,
    "logo_position": _LOGO_POSITIONS,
    "progress_style": {"bar", "dots", "both"},
    "default_theme": {"light", "dark", "system"},
}


def ui_property(field: dataclasses.Field) -> dict[str, Any]:
    if field.name in _UI_ENUMS:
        return enum(_UI_ENUMS[field.name])
    annotation = typing.get_type_hints(UIConfig)[field.name]
    optional = False
    if isinstance(annotation, types.UnionType):
        members = [arg for arg in typing.get_args(annotation) if arg is not type(None)]
        optional = len(members) < len(typing.get_args(annotation))
        annotation = members[0]
    if annotation is str:
        schema: dict[str, Any] = STRING
    elif annotation is bool:
        schema = BOOL
    elif annotation is int:
        schema = INT
    elif typing.get_origin(annotation) is list:
        schema = {"type": "array", "items": STRING}
    else:
        raise SystemExit(f"UIConfig.{field.name}: unsupported annotation {annotation!r}.")
    return nullable(schema) if optional else schema


DEFS["ui"] = {
    "description": "UIConfig fields; only fields that differ from the engine defaults are stored.",
    "type": "object",
    "properties": {field.name: ui_property(field) for field in dataclasses.fields(UIConfig)},
    "additionalProperties": False,
}

DEFS["options"] = {
    "description": "Compiler options (the keys of the module-level `options` dict except quota and ui).",
    "type": "object",
    "properties": {
        "language": NONEMPTY,
        "description": STRING,
        "completion_text": STRING,
        "show_progress": BOOL,
        "allow_back": BOOL,
        "one_question_per_page": BOOL,
        "max_responses": nullable({"type": "integer", "minimum": 1}),
        "metadata": {"type": "object"},
    },
    "additionalProperties": False,
}
assert set(DEFS["options"]["properties"]) == set(OPTION_KEYS)


SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": f"https://siamang.org/schemas/questionnaire-{SCHEMA_VERSION}.json",
    "title": "Siamang questionnaire document",
    "description": (
        "A questionnaire as stored by a survey builder: the same objects as "
        "siamang.core, one JSON object per engine class. Written by "
        "siamang.model.to_document, read by siamang.model.from_document."
    ),
    "type": "object",
    "properties": {
        "schema_version": {"const": SCHEMA_VERSION},
        "title": NONEMPTY,
        "options": ref("options"),
        "deadline": nullable({"type": "string", "format": "date-time"}),
        "variables": {"type": "object", "additionalProperties": ref("variable")},
        "pages": {"type": "array", "items": ref("page")},
        "quotas": {"type": "array", "items": ref("quota")},
        "scripts": {"type": "array", "items": ref("script")},
        "ui": ref("ui"),
        "layout": {
            "description": "Builder-owned state (collapsed pages, logic-map positions); ignored by the engine.",
            "type": "object",
        },
    },
    "required": ["schema_version", "title", "pages"],
    "additionalProperties": False,
    "$defs": DEFS,
}


def render() -> str:
    return json.dumps(SCHEMA, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str]) -> int:
    text = render()
    if "--check" in argv:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != text:
            print(f"{OUT} is stale; run python scripts/gen_document_schema.py")
            return 1
        print(f"{OUT} is up to date")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
