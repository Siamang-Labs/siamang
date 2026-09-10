"""Read a SurveyJS survey definition (JSON) as a questionnaire document.

SurveyJS (the Survey Creator / Survey Library) describes a survey as one
JSON object: ``pages`` of ``elements`` (questions and panels), each element
with a ``type``, a ``name``, a ``title`` and type-specific properties, and
``visibleIf`` expressions over answers. This module maps what the
questionnaire format can hold and reports the rest, like the Qualtrics and
LimeSurvey importers::

    result = import_surveyjs(text_or_object)
    result.document          # questionnaire-1.0
    result.skipped           # [Skipped(where="q7", what="Signature pad", why=...), ...]
    result.warnings          # things that were transferred approximately

What maps
    radiogroup / dropdown / imagepicker -> SingleChoice; checkbox / tagbox ->
    MultiChoice (wide when visibleIf tests its items); boolean -> SingleChoice
    yes/no; rating -> SingleChoice on the rate values (buttons); text ->
    OpenText or NumericInput (inputType number/range, min/max, maxLength);
    comment -> OpenText multiline; multipletext -> one OpenText per item;
    matrix -> Matrix (one variable per row); matrixdropdown with one column
    of choices -> Matrix; ranking -> Ranking; html / expression / image -> the
    page body (html) or the report; panels are flattened (a randomized panel
    becomes a Block). isRequired, "other" and "none" items, choicesOrder,
    questionsOrder (page-level shuffle), visibleIf on questions, panels and
    pages (=, <>, <, <=, >, >=, contains / notcontains on checkboxes, anyof,
    and / or / not, parentheses), locale, showPrevButton, showProgressBar,
    completedHtml, navigateToUrl.

What is reported as skipped
    file, signaturepad, paneldynamic, matrixdynamic, matrixdropdown with
    several columns or non-choice cells, expression questions; validators
    other than numeric ranges and text length; visibleIf with functions,
    arithmetic, empty / notempty, allof, or references to variables and
    calculated values; enableIf / requiredIf; triggers; calculatedValues;
    choicesByUrl; correct answers (quiz mode).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from siamang.model.document import SCHEMA_VERSION, DocumentError
from siamang.model.import_qsf import Skipped, _code, _ident, _number, _suffix, _text

_MAX_SOURCE = 20_000_000

_UNSUPPORTED = {
    "file": "File upload",
    "signaturepad": "Signature pad",
    "paneldynamic": "Dynamic panel",
    "matrixdynamic": "Dynamic matrix",
    "expression": "Expression",
    "geo": "Geo location",
    "microphone": "Microphone",
}
_COMPARE = {"=": "=", "==": "=", "<>": "!=", "!=": "!=", "<": "<", "<=": "<=", ">": ">", ">=": ">="}
_TOKEN_RE = re.compile(
    r"(?P<var>\{[^}]+\})|(?P<num>-?\d+(?:\.\d+)?)|(?P<str>'[^']*'|\"[^\"]*\")"
    r"|(?P<op>==|<>|!=|<=|>=|=|<|>|\(|\)|\[|\]|,)|(?P<word>[A-Za-z_][A-Za-z0-9_]*)"
)


@dataclass(frozen=True, slots=True)
class SurveyJsImportResult:
    document: dict[str, Any]
    warnings: list[str] = field(default_factory=list)
    skipped: list[Skipped] = field(default_factory=list)


def _loc(value: Any, locale: str) -> str:
    """A localizable string: plain text or {"default": ..., "de": ...}."""
    if isinstance(value, dict):
        value = value.get(locale) or value.get("default") or next(iter(value.values()), "")
    return _text(str(value)) if value is not None else ""


def _html(value: Any, locale: str) -> str:
    if isinstance(value, dict):
        value = value.get(locale) or value.get("default") or next(iter(value.values()), "")
    return str(value) if value is not None else ""


@dataclass(slots=True)
class _Converted:
    name: str
    items: list[dict[str, Any]]
    body: str | None = None
    kind: str = "single"  # single | multi | multi_wide | matrix | number | text | ranking | none
    var: str | None = None
    row_vars: dict[str, str] = field(default_factory=dict)  # item value / row -> variable
    codes: dict[str, Any] = field(default_factory=dict)  # choice value -> stored code


class _Names:
    def __init__(self) -> None:
        self._taken: set[str] = set()

    def claim(self, wanted: str) -> str:
        name = wanted
        n = 2
        while name in self._taken:
            name = f"{wanted}_{n}"
            n += 1
        self._taken.add(name)
        return name


class _Importer:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.locale = str(payload.get("locale") or "en")[:2].lower() or "en"
        self.warnings: list[str] = []
        self.skipped: list[Skipped] = []
        self.variables: dict[str, dict[str, Any]] = {}
        self.ids = _Names()
        self.var_names = _Names()
        self.page_names = _Names()
        self.converted: dict[str, _Converted] = {}
        self.logic_refs: set[str] = set()
        self.deferred: list[tuple[dict[str, Any], str, str]] = []  # (item, expression, where)

    # ── entry ────────────────────────────────────────────────────────────
    def run(self) -> dict[str, Any]:
        pages_in = self.payload.get("pages")
        if not isinstance(pages_in, list):
            elements = self.payload.get("elements") or self.payload.get("questions")
            if not isinstance(elements, list):
                raise DocumentError("Not a SurveyJS survey: no pages or elements list.")
            pages_in = [{"name": "page1", "elements": elements}]
        self._scan_logic(self.payload)
        for key in ("triggers", "calculatedValues"):
            if self.payload.get(key):
                self.skipped.append(
                    Skipped("survey", key, "not part of the questionnaire (runtime behavior)")
                )
        pages: list[dict[str, Any]] = []
        for page_in in pages_in:
            if isinstance(page_in, dict):
                pages.extend(self._page(page_in))
        self._attach_logic()
        self._prune_variables(pages)
        completed = _html(self.payload.get("completedHtml"), self.locale)
        if _text(completed):
            pages.append(
                {
                    "name": self.page_names.claim("end"),
                    "kind": "final",
                    "title": "Thank you",
                    "body": completed,
                }
            )
        if not pages:
            raise DocumentError("The survey has no pages the format can hold.")
        title = _loc(self.payload.get("title"), self.locale) or "Imported survey"
        document: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "title": title}
        options = self._options()
        if options:
            document["options"] = options
        document["variables"] = self.variables
        document["pages"] = pages
        if self.payload.get("navigateToUrl"):
            document["ui"] = {"redirect_url": str(self.payload["navigateToUrl"])}
        return document

    def _options(self) -> dict[str, Any]:
        options: dict[str, Any] = {"language": self.locale}
        if "showPrevButton" in self.payload:
            options["allow_back"] = bool(self.payload.get("showPrevButton"))
        if "showProgressBar" in self.payload:
            options["show_progress"] = str(self.payload.get("showProgressBar") or "off") not in {
                "off",
                "false",
                "False",
            }
        return options

    def _scan_logic(self, node: Any) -> None:
        """Checkbox questions whose items appear in contains / anyof tests are
        stored wide (one yes/no variable per item)."""
        if isinstance(node, dict):
            for key, value in node.items():
                if key in {"visibleIf", "enableIf", "requiredIf"} and isinstance(value, str):
                    for m in re.finditer(
                        r"\{([^}]+)\}\s*(?:contains|notcontains|anyof|allof)\b", value, re.I
                    ):
                        self.logic_refs.add(m.group(1).strip())
                else:
                    self._scan_logic(value)
        elif isinstance(node, list):
            for value in node:
                self._scan_logic(value)

    # ── pages and panels ─────────────────────────────────────────────────
    def _page(self, page_in: dict[str, Any]) -> list[dict[str, Any]]:
        title = _loc(page_in.get("title"), self.locale)
        name = _ident(str(page_in.get("name") or title or "page"), "page")
        items, body = self._elements(
            page_in.get("elements") or page_in.get("questions") or [], name
        )
        description = _html(page_in.get("description"), self.locale)
        if _text(description):
            body.insert(0, description)
        if not items and not body:
            return []
        page: dict[str, Any] = {"name": self.page_names.claim(name)}
        if title:
            page["title"] = title
        if body:
            page["body"] = "\n".join(body)
        if items:
            if str(page_in.get("questionsOrder") or "") == "random":
                page["items"] = [{"type": "Block", "randomize": True, "items": items}]
            else:
                page["items"] = items
        else:
            page["kind"] = "content"
        if isinstance(page_in.get("visibleIf"), str) and page_in["visibleIf"].strip():
            self.deferred.append((page, page_in["visibleIf"], f"page {name}"))
        return [page]

    def _elements(self, elements: list[Any], where: str) -> tuple[list[dict[str, Any]], list[str]]:
        items: list[dict[str, Any]] = []
        body: list[str] = []
        for element in elements:
            if not isinstance(element, dict):
                continue
            etype = str(element.get("type") or "")
            name = str(element.get("name") or "")
            if etype == "panel":
                inner, inner_body = self._elements(
                    element.get("elements") or element.get("questions") or [], name or where
                )
                body.extend(inner_body)
                if not inner:
                    continue
                if str(element.get("questionsOrder") or "") == "random" or element.get("visibleIf"):
                    block: dict[str, Any] = {"type": "Block", "items": inner}
                    panel_title = _loc(element.get("title"), self.locale)
                    if panel_title:
                        block["title"] = panel_title
                    if str(element.get("questionsOrder") or "") == "random":
                        block["randomize"] = True
                    if isinstance(element.get("visibleIf"), str) and element["visibleIf"].strip():
                        self.deferred.append((block, element["visibleIf"], f"panel {name}"))
                    items.append(block)
                else:
                    items.extend(inner)
                continue
            conv = self._question(element, etype, name)
            if conv.body:
                if items:
                    self.warnings.append(
                        f"{conv.name}: HTML placed in the page body of '{where}' (it sat between questions)."
                    )
                body.append(conv.body)
            items.extend(conv.items)
        return items, body

    # ── questions ────────────────────────────────────────────────────────
    def _question(self, q: dict[str, Any], etype: str, name: str) -> _Converted:
        code = _ident(name or etype, "q")
        where = name or code
        text = _loc(q.get("title"), self.locale) or name or code
        out = _Converted(name=name, items=[])
        self.converted[name] = out
        if etype in {"html", "image"}:
            out.kind = "none"
            out.body = (
                _html(q.get("html"), self.locale)
                if etype == "html"
                else (f'<img src="{q.get("imageLink", "")}" alt="{text}">')
            )
            return out
        if etype in _UNSUPPORTED:
            self.skipped.append(
                Skipped(where, _UNSUPPORTED[etype], "no such question type in the format")
            )
            out.kind = "none"
            return out
        for key, label in (("enableIf", "enableIf"), ("requiredIf", "requiredIf")):
            if q.get(key):
                self.skipped.append(
                    Skipped(where, label, "only visibility (show_if) can be expressed")
                )
        if q.get("correctAnswer") is not None:
            self.skipped.append(Skipped(where, "Correct answer", "no quiz mode in the format"))
        if q.get("choicesByUrl"):
            self.skipped.append(Skipped(where, "choicesByUrl", "choices loaded at run time"))
        handler = {
            "radiogroup": self._single,
            "dropdown": self._single,
            "imagepicker": self._single,
            "checkbox": self._multi,
            "tagbox": self._multi,
            "boolean": self._boolean,
            "rating": self._rating,
            "text": self._text_input,
            "comment": self._comment,
            "multipletext": self._multiple_text,
            "matrix": self._matrix,
            "matrixdropdown": self._matrix_dropdown,
            "ranking": self._ranking,
        }.get(etype)
        if handler is None:
            self.skipped.append(Skipped(where, f"{etype or '?'} question", "unknown question type"))
            out.kind = "none"
            return out
        handler(out, q, where, text, code)
        if isinstance(q.get("visibleIf"), str) and q["visibleIf"].strip():
            for item in out.items:
                self.deferred.append((item, q["visibleIf"], where))
        return out

    def _common(self, q: dict[str, Any], where: str) -> dict[str, Any]:
        base: dict[str, Any] = {}
        if q.get("isRequired"):
            base["required"] = True
        if str(q.get("choicesOrder") or "") in {"random"}:
            base["randomize"] = True
        elif str(q.get("choicesOrder") or "") in {"asc", "desc"}:
            self.warnings.append(
                f"{where}: choices sorted {q['choicesOrder']} in SurveyJS keep their file order."
            )
        for validator in q.get("validators") or []:
            vtype = validator.get("type") if isinstance(validator, dict) else None
            if vtype not in {"numeric", "text", None}:
                self.skipped.append(
                    Skipped(where, f"Validator {vtype}", "only numeric ranges and text length")
                )
        return base

    def _variable(self, wanted: str, spec: dict[str, Any]) -> str:
        name = self.var_names.claim(wanted)
        self.variables[name] = spec
        return name

    def _item(self, out: _Converted, wanted_id: str, item: dict[str, Any]) -> None:
        item["id"] = self.ids.claim(wanted_id)
        out.items.append(item)

    def _choices(
        self, q: dict[str, Any], out: _Converted, key: str = "choices"
    ) -> list[dict[str, Any]]:
        options: list[dict[str, Any]] = []
        raw_choices = q.get(key)
        if isinstance(raw_choices, dict):
            raw_choices = list(raw_choices.values())
        for choice in raw_choices or []:
            if isinstance(choice, dict):
                value = choice.get("value")
                label = _loc(choice.get("text"), self.locale) or str(value)
                if choice.get("visibleIf") or choice.get("enableIf"):
                    self.skipped.append(
                        Skipped(out.name, f"Logic on choice {value}", "choice-level")
                    )
            else:
                value, label = choice, _text(str(choice))
            if value is None:
                continue
            code = _code(value)
            out.codes[str(value)] = code
            options.append({"code": code, "label": label or str(value)})
        return options

    def _extra_items(
        self, q: dict[str, Any], out: _Converted, options: list[dict[str, Any]]
    ) -> tuple[bool, list[Any]]:
        """SurveyJS 'other', 'none' and 'select all' items: other -> other_specify,
        none -> an exclusive choice, select all -> reported."""
        other = bool(q.get("hasOther") or q.get("showOtherItem"))
        exclusive: list[Any] = []
        if q.get("hasNone") or q.get("showNoneItem"):
            code = _code(q.get("noneValue") or "none")
            label = _loc(q.get("noneText"), self.locale) or "None"
            options.append({"code": code, "label": label})
            out.codes[str(q.get("noneValue") or "none")] = code
            exclusive.append(code)
        if q.get("hasSelectAll") or q.get("showSelectAllItem"):
            self.skipped.append(
                Skipped(out.name, "Select all item", "no 'select all' in the format")
            )
        return other, exclusive

    def _single(self, out: _Converted, q: dict, where: str, text: str, code: str) -> None:
        options = self._choices(q, out)
        other, _exclusive = self._extra_items(q, out, options)
        if not options:
            self.skipped.append(Skipped(where, q.get("type", "choice"), "no choices"))
            out.kind = "none"
            return
        var = self._variable(
            code, {"scale": "nominal", "label": text[:120], "labels": [dict(o) for o in options]}
        )
        out.var, out.kind = var, "single"
        item: dict[str, Any] = {
            "type": "SingleChoice",
            "text": text,
            "var": var,
            "choices": options,
            **self._common(q, where),
        }
        if other:
            item["other_specify"] = True
        if q.get("type") == "dropdown":
            item["display"] = "dropdown"
        if q.get("type") == "imagepicker":
            self.warnings.append(
                f"{where}: image picker became a plain single choice (images dropped)."
            )
        self._item(out, code, item)

    def _multi(self, out: _Converted, q: dict, where: str, text: str, code: str) -> None:
        options = self._choices(q, out)
        other, exclusive = self._extra_items(q, out, options)
        if not options:
            self.skipped.append(Skipped(where, "Checkbox", "no choices"))
            out.kind = "none"
            return
        common = self._common(q, where)
        if out.name in self.logic_refs:
            yes_no = [{"code": 0, "label": "No"}, {"code": 1, "label": "Yes"}]
            variables: list[str] = []
            for raw_value, option in zip(list(out.codes), options, strict=False):
                var = self._variable(
                    f"{code}_{_suffix(str(option['code']))}",
                    {"scale": "nominal", "label": option["label"][:120], "labels": yes_no},
                )
                out.row_vars[raw_value] = var
                variables.append(var)
            out.kind, out.var = "multi_wide", variables[0]
            item: dict[str, Any] = {
                "type": "MultiChoice",
                "text": text,
                "var": variables,
                "mode": "wide",
                **common,
            }
            if other:
                item["other_specify"] = True
            if exclusive:
                self.skipped.append(
                    Skipped(
                        where,
                        "Exclusive answer",
                        "not available when choices are separate variables",
                    )
                )
            self.warnings.append(
                f"{where}: stored as one yes/no variable per choice ({', '.join(variables)}) because logic tests its choices."
            )
            self._item(out, code, item)
            return
        var = self._variable(
            code, {"scale": "nominal", "label": text[:120], "labels": [dict(o) for o in options]}
        )
        out.var, out.kind = var, "multi"
        item = {"type": "MultiChoice", "text": text, "var": var, "choices": options, **common}
        if other:
            item["other_specify"] = True
        if exclusive:
            item["exclusive"] = exclusive
        max_count = _number(q.get("maxSelectedChoices"))
        if isinstance(max_count, int) and max_count > 0:
            item["max_answers"] = max_count
        self._item(out, code, item)

    def _boolean(self, out: _Converted, q: dict, where: str, text: str, code: str) -> None:
        yes = q.get("valueTrue", True)
        no = q.get("valueFalse", False)
        options = [
            {
                "code": _code(yes) if not isinstance(yes, bool) else 1,
                "label": _loc(q.get("labelTrue"), self.locale) or "Yes",
            },
            {
                "code": _code(no) if not isinstance(no, bool) else 0,
                "label": _loc(q.get("labelFalse"), self.locale) or "No",
            },
        ]
        out.codes[str(yes).lower()] = options[0]["code"]
        out.codes[str(no).lower()] = options[1]["code"]
        var = self._variable(
            code, {"scale": "nominal", "label": text[:120], "labels": [dict(o) for o in options]}
        )
        out.var, out.kind = var, "single"
        self._item(
            out,
            code,
            {
                "type": "SingleChoice",
                "text": text,
                "var": var,
                "choices": options,
                "display": "buttons",
                **self._common(q, where),
            },
        )

    def _rating(self, out: _Converted, q: dict, where: str, text: str, code: str) -> None:
        values = q.get("rateValues")
        options: list[dict[str, Any]] = []
        if isinstance(values, list) and values:
            options = self._choices({"choices": values}, out)
        else:
            low = _number(q.get("rateMin")) if q.get("rateMin") is not None else 1
            high = (
                _number(q.get("rateMax"))
                if q.get("rateMax") is not None
                else (_number(q.get("rateCount")) or 5)
            )
            step = _number(q.get("rateStep")) or 1
            value = low
            while value is not None and high is not None and value <= high:
                options.append({"code": value, "label": str(value)})
                out.codes[str(value)] = value
                value += step
        if not options:
            self.skipped.append(Skipped(where, "Rating", "no rate values"))
            out.kind = "none"
            return
        if _loc(q.get("minRateDescription"), self.locale):
            options[0]["label"] = (
                f"{options[0]['label']} — {_loc(q.get('minRateDescription'), self.locale)}"
            )
        if _loc(q.get("maxRateDescription"), self.locale):
            options[-1]["label"] = (
                f"{options[-1]['label']} — {_loc(q.get('maxRateDescription'), self.locale)}"
            )
        var = self._variable(
            code, {"scale": "ordinal", "label": text[:120], "labels": [dict(o) for o in options]}
        )
        out.var, out.kind = var, "single"
        self._item(
            out,
            code,
            {
                "type": "SingleChoice",
                "text": text,
                "var": var,
                "choices": options,
                "display": "buttons",
                **self._common(q, where),
            },
        )

    def _numeric_bounds(self, q: dict[str, Any]) -> tuple[Any, Any]:
        low, high = _number(q.get("min")), _number(q.get("max"))
        for validator in q.get("validators") or []:
            if isinstance(validator, dict) and validator.get("type") == "numeric":
                low = (
                    _number(validator.get("minValue"))
                    if validator.get("minValue") is not None
                    else low
                )
                high = (
                    _number(validator.get("maxValue"))
                    if validator.get("maxValue") is not None
                    else high
                )
        return low, high

    def _text_input(self, out: _Converted, q: dict, where: str, text: str, code: str) -> None:
        input_type = str(q.get("inputType") or "text").lower()
        numeric = input_type in {"number", "range"} or any(
            isinstance(v, dict) and v.get("type") == "numeric" for v in q.get("validators") or []
        )
        if numeric:
            spec: dict[str, Any] = {"scale": "ratio", "label": text[:120]}
            low, high = self._numeric_bounds(q)
            if low is not None or high is not None:
                spec["valid_range"] = [low, high]
            var = self._variable(code, spec)
            out.var, out.kind = var, "number"
            item: dict[str, Any] = {
                "type": "NumericInput",
                "text": text,
                "var": var,
                **self._common(q, where),
            }
            if input_type == "range":
                item["display"] = "slider"
                spec["scale"] = "interval"
            step = _number(q.get("step"))
            if step:
                item["step"] = step
            self._item(out, code, item)
            return
        if input_type in {"date", "datetime-local", "time", "month", "week"}:
            self.warnings.append(
                f"{where}: {input_type} input became free text (no date type in the format)."
            )
        var = self._variable(code, {"scale": "nominal", "label": text[:120]})
        out.var, out.kind = var, "text"
        item = {"type": "OpenText", "text": text, "var": var, **self._common(q, where)}
        max_len = _number(q.get("maxLength"))
        for validator in q.get("validators") or []:
            if (
                isinstance(validator, dict)
                and validator.get("type") == "text"
                and validator.get("maxLength")
            ):
                max_len = _number(validator.get("maxLength"))
        if isinstance(max_len, int) and max_len > 0:
            item["max_chars"] = max_len
        self._item(out, code, item)

    def _comment(self, out: _Converted, q: dict, where: str, text: str, code: str) -> None:
        var = self._variable(code, {"scale": "nominal", "label": text[:120]})
        out.var, out.kind = var, "text"
        item: dict[str, Any] = {
            "type": "OpenText",
            "text": text,
            "var": var,
            "multiline": True,
            **self._common(q, where),
        }
        max_len = _number(q.get("maxLength"))
        if isinstance(max_len, int) and max_len > 0:
            item["max_chars"] = max_len
        self._item(out, code, item)

    def _multiple_text(self, out: _Converted, q: dict, where: str, text: str, code: str) -> None:
        fields = q.get("items") or []
        if not fields:
            self.skipped.append(Skipped(where, "Multiple text", "no items"))
            out.kind = "none"
            return
        out.kind = "text"
        for entry in fields:
            if isinstance(entry, dict):
                item_name = str(entry.get("name") or "")
                label = _loc(entry.get("title"), self.locale) or item_name
            else:
                item_name = label = str(entry)
            var = self._variable(
                f"{code}_{_suffix(item_name)}", {"scale": "nominal", "label": label[:120]}
            )
            out.row_vars[item_name] = var
            out.var = out.var or var
            self._item(
                out,
                f"{code}_{_suffix(item_name)}",
                {
                    "type": "OpenText",
                    "text": f"{text} — {label}",
                    "var": var,
                    **self._common(q, where),
                },
            )

    def _matrix(self, out: _Converted, q: dict, where: str, text: str, code: str) -> None:
        rows = q.get("rows") or []
        columns = self._choices(q, out, key="columns")
        if not rows or not columns:
            self.skipped.append(Skipped(where, "Matrix", "no rows or no columns"))
            out.kind = "none"
            return
        self._matrix_items(out, q, where, text, code, rows, columns)

    def _matrix_dropdown(self, out: _Converted, q: dict, where: str, text: str, code: str) -> None:
        columns = q.get("columns") or []
        rows = q.get("rows") or []
        if len(columns) != 1 or not isinstance(columns[0], dict):
            self.skipped.append(
                Skipped(where, "Matrix dropdown", "only one column of choices per matrix")
            )
            out.kind = "none"
            return
        column = columns[0]
        cell_type = str(column.get("cellType") or q.get("cellType") or "dropdown")
        if cell_type not in {"dropdown", "radiogroup"}:
            self.skipped.append(
                Skipped(where, f"Matrix dropdown ({cell_type} cells)", "only choice cells")
            )
            out.kind = "none"
            return
        choices = self._choices({"choices": column.get("choices") or q.get("choices") or []}, out)
        if not rows or not choices:
            self.skipped.append(Skipped(where, "Matrix dropdown", "no rows or no choices"))
            out.kind = "none"
            return
        self._matrix_items(out, q, where, text, code, rows, choices)

    def _matrix_items(
        self,
        out: _Converted,
        q: dict,
        where: str,
        text: str,
        code: str,
        rows: list[Any],
        columns: list[dict[str, Any]],
    ) -> None:
        labels = [{"code": c["code"], "label": c["label"]} for c in columns]
        variables: list[str] = []
        subquestions: list[str] = []
        for row in rows:
            if isinstance(row, dict):
                value = str(row.get("value") or "")
                label = _loc(row.get("text"), self.locale) or value
            else:
                value = label = str(row)
            var = self._variable(
                f"{code}_{_suffix(value)}",
                {"scale": "ordinal", "label": label[:120], "labels": labels},
            )
            out.row_vars[value] = var
            variables.append(var)
            subquestions.append(label)
        out.kind, out.var = "matrix", variables[0]
        item: dict[str, Any] = {
            "type": "Matrix",
            "text": text,
            "var": variables,
            "subquestions": subquestions,
            "column_labels": [c["label"] for c in columns],
            **self._common(q, where),
        }
        if q.get("isAllRowRequired"):
            item["required"] = True
        if str(q.get("rowsOrder") or "") == "random":
            item["randomize"] = True
        self._item(out, code, item)

    def _ranking(self, out: _Converted, q: dict, where: str, text: str, code: str) -> None:
        options = self._choices(q, out)
        if not options:
            self.skipped.append(Skipped(where, "Ranking", "no choices"))
            out.kind = "none"
            return
        var = self._variable(
            code, {"scale": "nominal", "label": text[:120], "labels": [dict(o) for o in options]}
        )
        out.var, out.kind = var, "ranking"
        self._item(
            out,
            code,
            {
                "type": "Ranking",
                "text": text,
                "var": var,
                "choices": options,
                **self._common(q, where),
            },
        )

    def _prune_variables(self, pages: list[dict[str, Any]]) -> None:
        used: set[str] = set()

        def walk(items: list[Any]) -> None:
            for item in items:
                if not isinstance(item, dict):
                    continue
                if isinstance(item.get("items"), list):
                    walk(item["items"])
                var = item.get("var")
                for name in var if isinstance(var, list) else [var]:
                    if isinstance(name, str):
                        used.add(name)

        for page in pages:
            walk(page.get("items") or [])
        for name in list(self.variables):
            if name not in used:
                del self.variables[name]

    # ── visibleIf ────────────────────────────────────────────────────────
    def _attach_logic(self) -> None:
        for target, expression, where in self.deferred:
            condition = self._condition(expression, where)
            if condition is not None:
                target["show_if"] = condition

    def _condition(self, expression: str, where: str) -> dict[str, Any] | None:
        try:
            tokens = _tokenize(expression)
            parser = _Parser(tokens, self)
            result = parser.parse()
            if parser.pos != len(tokens):
                raise _Unsupported("trailing text")
            return result
        except _Unsupported as exc:
            self.skipped.append(
                Skipped(where, "visibleIf", f"{exc} — shown always: {expression[:80]}")
            )
            return None

    def compare(self, ref: str, op: str, raw: Any) -> dict[str, Any]:
        """``{name}`` or ``{name.row}`` / ``{name.item}`` compared to a literal."""
        name, _, sub = ref.partition(".")
        conv = self.converted.get(name)
        if conv is None or conv.kind == "none":
            raise _Unsupported(f"refers to {{{ref}}}, which was not imported")
        if op in {"contains", "notcontains"}:
            if conv.kind in {"single", "ranking"} and conv.var is not None:
                # anyof / contains on a single choice: "the answer is one of"
                code = conv.codes.get(str(raw), _code(raw))
                return _cmp(conv.var, "=" if op == "contains" else "!=", code)
            if conv.kind != "multi_wide":
                raise _Unsupported(f"'{op}' on {name}, which is not a checkbox stored wide")
            var = conv.row_vars.get(str(raw))
            if var is None:
                raise _Unsupported(f"{name} has no item {raw!r}")
            return _cmp(var, "=" if op == "contains" else "!=", 1)
        if conv.kind in {"matrix", "text", "number"} and sub or sub and conv.kind == "multi_wide":
            var = conv.row_vars.get(sub)
        else:
            var = conv.var
        if var is None:
            raise _Unsupported(f"cannot be expressed on {{{ref}}}")
        value: Any = raw
        if conv.kind in {"single", "ranking", "matrix", "multi"}:
            value = conv.codes.get(
                str(raw).lower() if isinstance(raw, bool) else str(raw), _code(raw)
            )
        elif conv.kind == "number":
            value = _number(raw) if _number(raw) is not None else raw
        return _cmp(var, op, value)


class _Unsupported(Exception):
    pass


def _tokenize(expression: str) -> list[tuple[str, Any]]:
    tokens: list[tuple[str, Any]] = []
    pos = 0
    while pos < len(expression):
        if expression[pos].isspace():
            pos += 1
            continue
        m = _TOKEN_RE.match(expression, pos)
        if not m:
            raise _Unsupported(f"unreadable at {expression[pos:pos + 12]!r}")
        pos = m.end()
        kind = m.lastgroup or ""
        text = m.group(kind)
        if kind == "var":
            tokens.append(("var", text[1:-1].strip()))
        elif kind == "str":
            tokens.append(("lit", text[1:-1]))
        elif kind == "num":
            tokens.append(("lit", _number(text)))
        elif kind == "word":
            lowered = text.lower()
            if lowered in {"true", "false"}:
                tokens.append(("lit", lowered == "true"))
            else:
                tokens.append(("word", lowered))
        else:
            tokens.append(("op", text))
    return tokens


class _Parser:
    """``or`` > ``and`` > ``not`` > comparison, with parentheses; the
    operators SurveyJS writes: = <> < <= > >= contains notcontains anyof."""

    def __init__(self, tokens: list[tuple[str, Any]], importer: _Importer) -> None:
        self.tokens = tokens
        self.pos = 0
        self.importer = importer

    def peek(self) -> tuple[str, Any] | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def take(self) -> tuple[str, Any]:
        token = self.peek()
        if token is None:
            raise _Unsupported("unexpected end")
        self.pos += 1
        return token

    def parse(self) -> dict[str, Any]:
        left = self.parse_and()
        while self.peek() in {("word", "or"), ("op", "||")}:
            self.take()
            left = {"type": "expression", "op": "or", "left": left, "right": self.parse_and()}
        return left

    def parse_and(self) -> dict[str, Any]:
        left = self.parse_not()
        while self.peek() in {("word", "and"), ("op", "&&")}:
            self.take()
            left = {"type": "expression", "op": "and", "left": left, "right": self.parse_not()}
        return left

    def parse_not(self) -> dict[str, Any]:
        if self.peek() in {("word", "not"), ("op", "!")}:
            self.take()
            return {"type": "expression", "op": "not", "left": self.parse_not()}
        return self.parse_atom()

    def parse_atom(self) -> dict[str, Any]:
        token = self.take()
        if token == ("op", "("):
            inner = self.parse()
            if self.take() != ("op", ")"):
                raise _Unsupported("missing )")
            return inner
        if token[0] != "var":
            raise _Unsupported(f"unexpected {token[1]!r}")
        ref = str(token[1])
        op_token = self.take()
        if op_token[0] == "op" and op_token[1] in _COMPARE:
            value = self.take()
            if value[0] != "lit":
                raise _Unsupported("comparison with another answer")
            return self.importer.compare(ref, _COMPARE[op_token[1]], value[1])
        if op_token[0] == "word" and op_token[1] in {"contains", "notcontains"}:
            value = self.take()
            if value[0] != "lit":
                raise _Unsupported("contains with a non-literal")
            return self.importer.compare(ref, op_token[1], value[1])
        if op_token[0] == "word" and op_token[1] == "anyof":
            values = self.parse_list()
            parts = [self.importer.compare(ref, "contains", v) for v in values]
            if not parts:
                raise _Unsupported("anyof with no values")
            result = parts[0]
            for part in parts[1:]:
                result = {"type": "expression", "op": "or", "left": result, "right": part}
            return result
        if op_token[0] == "word" and op_token[1] in {"empty", "notempty", "allof"}:
            raise _Unsupported(f"'{op_token[1]}' has no counterpart")
        raise _Unsupported(f"operator {op_token[1]!r}")

    def parse_list(self) -> list[Any]:
        if self.take() != ("op", "["):
            raise _Unsupported("anyof needs a list")
        values: list[Any] = []
        while True:
            token = self.take()
            if token == ("op", "]"):
                return values
            if token[0] != "lit":
                raise _Unsupported("list of non-literals")
            values.append(token[1])
            if self.peek() == ("op", ","):
                self.take()


def _var(name: str) -> dict[str, Any]:
    return {"type": "var", "name": name}


def _cmp(var: str, op: str, value: Any) -> dict[str, Any]:
    return {"type": "expression", "op": op, "left": _var(var), "right": value}


# ─── public API ──────────────────────────────────────────────────────────────


def looks_like_surveyjs(payload: Any) -> bool:
    """True for a parsed SurveyJS survey: pages of elements (or a bare
    elements list), never a questionnaire document (pages of items)."""
    if not isinstance(payload, dict) or "SurveyElements" in payload:
        return False
    pages = payload.get("pages")
    if isinstance(pages, list) and pages:
        first = next((p for p in pages if isinstance(p, dict)), None)
        return (
            first is not None
            and ("elements" in first or "questions" in first)
            and "items" not in first
        )
    return isinstance(payload.get("elements") or payload.get("questions"), list)


def import_surveyjs(payload: dict[str, Any] | str) -> SurveyJsImportResult:
    """Convert a SurveyJS survey definition (parsed JSON or its text) to a document."""
    if isinstance(payload, str):
        if len(payload) > _MAX_SOURCE:
            raise DocumentError("File too large to import (20 MB limit).")
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise DocumentError(f"Not valid JSON: line {exc.lineno}: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise DocumentError("Not a SurveyJS survey: expected a JSON object.")
    importer = _Importer(payload)
    document = importer.run()
    return SurveyJsImportResult(
        document=document, warnings=importer.warnings, skipped=importer.skipped
    )


def import_surveyjs_file(path: str | Path) -> SurveyJsImportResult:
    return import_surveyjs(Path(path).read_text(encoding="utf-8"))


__all__ = ["SurveyJsImportResult", "import_surveyjs", "import_surveyjs_file", "looks_like_surveyjs"]
