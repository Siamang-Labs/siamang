"""Read a Qualtrics Survey Format (``.qsf``) export as a questionnaire document.

A QSF file is the JSON Qualtrics writes for "Export survey": a ``SurveyEntry``
header and a list of ``SurveyElements`` — questions (``SQ``), blocks (``BL``),
the survey flow (``FL``), options (``SO``) and a few we do not need. This
module maps what the questionnaire format can hold and reports the rest, so
a migration never silently loses a question, a branch or a validation::

    result = import_qsf(json.loads(text))
    result.document          # questionnaire-1.0
    result.skipped           # [Skipped(where="Q7", what="Constant sum", why=...), ...]
    result.warnings          # things that were transferred approximately

What maps
    MC (single/multi, dropdown, NPS) -> SingleChoice / MultiChoice; TE -> OpenText
    (or NumericInput with a number validation; a Form becomes one OpenText per
    field); Matrix Likert single-answer -> Matrix (one variable per row);
    Slider -> NumericInput(slider) per statement; RO -> Ranking; DB -> the page
    body. Recodes, choice order, "other" text entries, exclusive answers,
    forced response, question/choice randomization, display logic on
    questions (Selected / NotSelected / comparisons), page breaks, block order
    from the survey flow, branches (as page-level show_if), End-of-survey
    inside a branch (a disqualification page), back button and progress bar.

What is reported as skipped
    Constant sum, side-by-side, drill-down, pick-group-rank, file upload,
    signature, timing, meta info, captcha, heat maps, hot spots, highlight;
    matrix multiple-answer / bipolar / text-entry; display logic on embedded
    data, quotas or panel data; embedded data, quotas, web services,
    authenticators in the flow; loop & merge; skip logic; validations other
    than "force response" and numeric ranges; block randomizers (pages keep
    their order); choice-display logic.
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from siamang.model.document import SCHEMA_VERSION, DocumentError

_MAX_SOURCE = 20_000_000

_SINGLE = {"SAVR", "SAHR", "SACOL", "DL", "SB", "NPS", "TB", "SBS"}
_MULTI = {"MAVR", "MAHR", "MACOL", "MSB"}
_UNSUPPORTED_TYPES = {
    "CS": "Constant sum",
    "SBS": "Side by side",
    "DD": "Drill down",
    "PGR": "Pick, group and rank",
    "FileUpload": "File upload",
    "Signature": "Signature",
    "Timing": "Timing",
    "Meta": "Meta info",
    "Captcha": "Captcha",
    "HeatMap": "Heat map",
    "HotSpot": "Hot spot",
    "HL": "Highlight",
    "Draw": "Drawing",
    "GAP": "Gap analysis",
    "TB": "Text / graphic (block)",
}
_COMPARE = {
    "EqualTo": "=",
    "NotEqualTo": "!=",
    "GreaterThan": ">",
    "GreaterThanOrEqual": ">=",
    "LessThan": "<",
    "LessThanOrEqual": "<=",
}
_TAG_RE = re.compile(r"<[^>]+>")
_BREAK_RE = re.compile(r"</(p|div|li|h[1-6]|tr)>|<br\s*/?>", re.IGNORECASE)
_IDENT_RE = re.compile(r"[^a-z0-9]+")
_LOCATOR_RE = re.compile(r"^q://(QID[0-9A-Za-z_]+)/([A-Za-z]+)(?:/([^/]+))?(?:/([^/]+))?$")


@dataclass(frozen=True, slots=True)
class Skipped:
    """One thing the importer did not transfer, and why."""

    where: str
    what: str
    why: str

    def __str__(self) -> str:
        return f"{self.where}: {self.what} — {self.why}"


@dataclass(frozen=True, slots=True)
class QsfImportResult:
    document: dict[str, Any]
    warnings: list[str] = field(default_factory=list)
    skipped: list[Skipped] = field(default_factory=list)


# ─── text helpers ────────────────────────────────────────────────────────────


def _text(value: Any) -> str:
    """Plain text of a Qualtrics rich-text field (HTML): tags out, entities in."""
    if not isinstance(value, str):
        return ""
    stripped = _BREAK_RE.sub("\n", value)
    stripped = _TAG_RE.sub("", stripped)
    lines = [" ".join(line.split()) for line in html.unescape(stripped).splitlines()]
    return "\n".join(line for line in lines if line).strip()


def _ident(value: str, fallback: str = "q") -> str:
    """An identifier for a tag or label: lowercase, underscores, never empty
    or starting with a digit."""
    slug = _suffix(value) or fallback
    if slug[0].isdigit():
        slug = f"{fallback}_{slug}"
    return slug


def _suffix(value: str) -> str:
    """The part after a tag (a choice key, a row label): digits are fine."""
    return _IDENT_RE.sub("_", value.lower()).strip("_")


def _code(value: Any) -> Any:
    """A choice key or recode as a code: integers stay integers."""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int | float):
        return value
    text = str(value).strip()
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    try:
        return float(text)
    except ValueError:
        return text


def _number(value: Any) -> float | int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        try:
            return float(text)
        except ValueError:
            return None


def _is_on(value: Any) -> bool:
    return str(value).strip().lower() in {"on", "true", "1", "yes", "force"}


def _ordered(mapping: Any, order: Any) -> list[tuple[str, Any]]:
    """Choices/Answers in display order (``ChoiceOrder`` / ``AnswerOrder``)."""
    if not isinstance(mapping, dict):
        return []
    keys = [str(k) for k in order] if isinstance(order, list) else list(mapping)
    seen: list[tuple[str, Any]] = []
    for key in keys:
        if key in mapping and all(key != k for k, _ in seen):
            seen.append((key, mapping[key]))
    for key in mapping:
        if all(key != k for k, _ in seen):
            seen.append((str(key), mapping[key]))
    return seen


class _Names:
    """Unique identifiers (question ids, variable names, page names)."""

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


# ─── converted questions ─────────────────────────────────────────────────────


@dataclass(slots=True)
class _Converted:
    """What one Qualtrics question became."""

    qid: str
    tag: str
    items: list[dict[str, Any]]
    # "text" for descriptive blocks (HTML for the page body)
    body: str | None = None
    # how display logic refers to this question
    kind: str = "single"  # single | multi | matrix | number | text | ranking | none
    var: str | None = None
    row_vars: dict[str, str] = field(default_factory=dict)
    choice_codes: dict[str, Any] = field(default_factory=dict)
    answer_codes: dict[str, Any] = field(default_factory=dict)


class _Importer:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.warnings: list[str] = []
        self.skipped: list[Skipped] = []
        self.variables: dict[str, dict[str, Any]] = {}
        self.ids = _Names()
        self.var_names = _Names()
        self.page_names = _Names()
        self.questions: dict[str, dict[str, Any]] = {}
        self.blocks: dict[str, dict[str, Any]] = {}
        self.flow: list[Any] = []
        self.options_element: dict[str, Any] = {}
        self.converted: dict[str, _Converted] = {}
        # question id -> page name, filled while pages are built
        self.page_of: dict[str, str] = {}
        # question ids whose choices appear in display or branch logic
        self.logic_refs: set[str] = set()

    # ── entry ────────────────────────────────────────────────────────────
    def run(self) -> dict[str, Any]:
        self._collect()
        for qid, question in self.questions.items():
            self.converted[qid] = self._question(qid, question)
        pages = self._pages()
        self._attach_display_logic()
        self._prune_variables(pages)
        entry = self.payload.get("SurveyEntry") or {}
        title = _text(entry.get("SurveyName")) or "Imported survey"
        document: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "title": title}
        options = self._options(entry)
        if options:
            document["options"] = options
        document["variables"] = self.variables
        document["pages"] = pages
        ui = self._ui()
        if ui:
            document["ui"] = ui
        return document

    def _prune_variables(self, pages: list[dict[str, Any]]) -> None:
        """Questions in the trash or in blocks outside the flow registered
        variables nobody asks: drop them so the codebook is what is fielded."""
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

    def _collect(self) -> None:
        elements = self.payload.get("SurveyElements")
        if not isinstance(elements, list):
            raise DocumentError("Not a Qualtrics export: no SurveyElements list.")
        for element in elements:
            if not isinstance(element, dict):
                continue
            kind = element.get("Element")
            body = element.get("Payload")
            if kind == "SQ" and isinstance(body, dict):
                qid = str(body.get("QuestionID") or element.get("PrimaryAttribute") or "")
                if qid:
                    self.questions[qid] = body
            elif kind == "BL":
                blocks = body.values() if isinstance(body, dict) else body
                for block in blocks or []:
                    if isinstance(block, dict) and block.get("ID"):
                        self.blocks[str(block["ID"])] = block
            elif kind == "FL" and isinstance(body, dict):
                self.flow = body.get("Flow") if isinstance(body.get("Flow"), list) else []
            elif kind == "SO" and isinstance(body, dict):
                self.options_element = body
        if not self.questions and not self.blocks:
            raise DocumentError("Not a Qualtrics export: no questions or blocks found.")
        # Multi-select questions whose choices are tested by display or branch
        # logic are stored wide (one yes/no variable per choice), because the
        # expression language has no "contains" for array answers.
        for question in self.questions.values():
            self._scan_logic(question.get("DisplayLogic"))
        self._scan_logic(self.flow)

    def _scan_logic(self, node: Any) -> None:
        if isinstance(node, dict):
            for value in node.values():
                self._scan_logic(value)
        elif isinstance(node, list):
            for value in node:
                self._scan_logic(value)
        elif isinstance(node, str):
            match = _LOCATOR_RE.match(node)
            if match and match.group(2) == "SelectableChoice":
                self.logic_refs.add(match.group(1))

    # ── questions ────────────────────────────────────────────────────────
    def _question(self, qid: str, q: dict[str, Any]) -> _Converted:
        raw_tag = q.get("DataExportTag") or qid
        tag = _ident(str(raw_tag), "q")
        where = str(raw_tag)
        qtype = str(q.get("QuestionType") or "")
        selector = str(q.get("Selector") or "")
        sub = str(q.get("SubSelector") or "")
        text = _text(q.get("QuestionText")) or _text(q.get("QuestionDescription")) or where
        out = _Converted(qid=qid, tag=tag, items=[])
        if "SkipLogic" in q:
            self.skipped.append(Skipped(where, "Skip logic", "add it as page logic (next_if)"))
        if qtype == "DB":
            out.kind = "none"
            out.body = q.get("QuestionText") if isinstance(q.get("QuestionText"), str) else text
            return out
        if qtype in _UNSUPPORTED_TYPES:
            self.skipped.append(
                Skipped(where, _UNSUPPORTED_TYPES[qtype], "no such question type in the format")
            )
            out.kind = "none"
            return out
        handler = {
            "MC": self._mc,
            "TE": self._te,
            "Matrix": self._matrix,
            "Slider": self._slider,
            "RO": self._ro,
        }.get(qtype)
        if handler is None:
            self.skipped.append(
                Skipped(where, f"{qtype} question", "unknown question type in the format")
            )
            out.kind = "none"
            return out
        handler(out, q, where, text, selector, sub)
        return out

    def _common(self, q: dict[str, Any], out: _Converted, where: str) -> dict[str, Any]:
        base: dict[str, Any] = {}
        validation = q.get("Validation") if isinstance(q.get("Validation"), dict) else {}
        settings = (
            validation.get("Settings") if isinstance(validation.get("Settings"), dict) else {}
        )
        if _is_on(settings.get("ForceResponse")) or _is_on(settings.get("ForceResponseType")):
            base["required"] = True
        vtype = settings.get("Type")
        if vtype not in (None, "", "None", "ValidNumber", "ContentType", "MinChar"):
            self.skipped.append(
                Skipped(where, f"Validation {vtype}", "only forced response and numeric ranges")
            )
        randomization = q.get("Randomization")
        if isinstance(randomization, dict) and randomization.get("Type"):
            if randomization.get("Type") == "All":
                base["randomize"] = True
            else:
                base["randomize"] = True
                self.warnings.append(
                    f"{where}: {randomization['Type']} choice randomization became plain "
                    "shuffle (fixed positions are not kept)."
                )
        return base

    def _choices(
        self, q: dict[str, Any], out: _Converted, where: str, key: str = "Choices"
    ) -> tuple[list[dict[str, Any]], bool, list[Any]]:
        """Options with recodes; also whether any is a text entry and the
        exclusive codes."""
        order_key = "ChoiceOrder" if key == "Choices" else "AnswerOrder"
        recodes = q.get("RecodeValues") if isinstance(q.get("RecodeValues"), dict) else {}
        options: list[dict[str, Any]] = []
        other = False
        exclusive: list[Any] = []
        codes = out.choice_codes if key == "Choices" else out.answer_codes
        for choice_key, choice in _ordered(q.get(key), q.get(order_key)):
            label = _text(choice.get("Display")) if isinstance(choice, dict) else _text(choice)
            code = _code(recodes.get(choice_key, choice_key)) if recodes else _code(choice_key)
            codes[choice_key] = code
            options.append({"code": code, "label": label or str(choice_key)})
            if isinstance(choice, dict):
                if _is_on(choice.get("TextEntry")):
                    other = True
                if _is_on(choice.get("ExclusiveAnswer")):
                    exclusive.append(code)
                if choice.get("DisplayLogic"):
                    self.skipped.append(
                        Skipped(where, f"Display logic on choice {choice_key}", "choice-level")
                    )
        return options, other, exclusive

    def _variable(self, out: _Converted, wanted: str, spec: dict[str, Any]) -> str:
        name = self.var_names.claim(wanted)
        self.variables[name] = spec
        return name

    def _item(self, out: _Converted, wanted_id: str, item: dict[str, Any]) -> None:
        item["id"] = self.ids.claim(wanted_id)
        out.items.append(item)

    def _mc(self, out: _Converted, q: dict, where: str, text: str, sel: str, sub: str) -> None:
        options, other, exclusive = self._choices(q, out, where)
        if not options:
            self.skipped.append(Skipped(where, "Multiple choice", "no choices"))
            out.kind = "none"
            return
        labels = [{"code": o["code"], "label": o["label"]} for o in options]
        multi = sel in _MULTI
        if multi and out.qid in self.logic_refs:
            self._mc_wide(out, q, where, text, options, other, exclusive)
            return
        var = self._variable(
            out, out.tag, {"scale": "nominal", "label": text[:120], "labels": labels}
        )
        out.var = var
        out.kind = "multi" if multi else "single"
        item: dict[str, Any] = {
            "type": "MultiChoice" if multi else "SingleChoice",
            "text": text,
            "var": var,
            "choices": options,
            **self._common(q, out, where),
        }
        if other:
            item["other_specify"] = True
        if multi and exclusive:
            item["exclusive"] = exclusive
        if not multi:
            if sel in {"DL", "SB"}:
                item["display"] = "dropdown"
            elif sel == "NPS":
                item["display"] = "buttons"
        self._item(out, out.tag, item)

    def _mc_wide(
        self,
        out: _Converted,
        q: dict[str, Any],
        where: str,
        text: str,
        options: list[dict[str, Any]],
        other: bool,
        exclusive: list[Any],
    ) -> None:
        """A multi-select whose choices are tested by logic: one yes/no
        variable per choice (as Qualtrics exports it), so "Acme is selected"
        becomes ``aware_1 = 1``."""
        yes_no = [{"code": 0, "label": "No"}, {"code": 1, "label": "Yes"}]
        variables: list[str] = []
        for key, option in zip(out.choice_codes, options, strict=True):
            var = self._variable(
                out,
                f"{out.tag}_{_suffix(str(option['code']))}",
                {"scale": "nominal", "label": option["label"][:120], "labels": yes_no},
            )
            out.row_vars[key] = var
            variables.append(var)
        out.kind = "multi_wide"
        out.var = variables[0]
        item: dict[str, Any] = {
            "type": "MultiChoice",
            "text": text,
            "var": variables,
            "mode": "wide",
            **self._common(q, out, where),
        }
        if other:
            item["other_specify"] = True
        if exclusive:
            self.skipped.append(
                Skipped(
                    where, "Exclusive answer", "not available when choices are separate variables"
                )
            )
        self.warnings.append(
            f"{where}: stored as one yes/no variable per choice ({', '.join(variables)}) "
            "because logic tests its choices."
        )
        self._item(out, out.tag, item)

    def _te(self, out: _Converted, q: dict, where: str, text: str, sel: str, sub: str) -> None:
        validation = q.get("Validation") if isinstance(q.get("Validation"), dict) else {}
        settings = (
            validation.get("Settings") if isinstance(validation.get("Settings"), dict) else {}
        )
        numeric = (
            settings.get("ContentType") == "ValidNumber" or settings.get("Type") == "ValidNumber"
        )
        if sel == "FORM":
            out.kind = "text"
            fields = _ordered(q.get("Choices"), q.get("ChoiceOrder"))
            if not fields:
                self.skipped.append(Skipped(where, "Form", "no fields"))
                out.kind = "none"
                return
            for key, choice in fields:
                label = _text(choice.get("Display")) if isinstance(choice, dict) else _text(choice)
                var = self._variable(
                    out,
                    f"{out.tag}_{_suffix(label or key)}",
                    {"scale": "nominal", "label": label or key},
                )
                out.row_vars[key] = var
                self._item(
                    out,
                    f"{out.tag}_{_suffix(label or key)}",
                    {
                        "type": "OpenText",
                        "text": f"{text} — {label}" if label else text,
                        "var": var,
                        **self._common(q, out, where),
                    },
                )
            return
        if numeric:
            bounds = (
                settings.get("ValidNumber") if isinstance(settings.get("ValidNumber"), dict) else {}
            )
            low, high = _number(bounds.get("Min")), _number(bounds.get("Max"))
            spec: dict[str, Any] = {"scale": "ratio", "label": text[:120]}
            if low is not None or high is not None:
                spec["valid_range"] = [low, high]
            var = self._variable(out, out.tag, spec)
            out.var, out.kind = var, "number"
            self._item(
                out,
                out.tag,
                {"type": "NumericInput", "text": text, "var": var, **self._common(q, out, where)},
            )
            return
        var = self._variable(out, out.tag, {"scale": "nominal", "label": text[:120]})
        out.var, out.kind = var, "text"
        item: dict[str, Any] = {
            "type": "OpenText",
            "text": text,
            "var": var,
            **self._common(q, out, where),
        }
        if sel in {"ML", "ESTB"}:
            item["multiline"] = True
        max_chars = _number(settings.get("MaxChars"))
        if isinstance(max_chars, int) and max_chars > 0:
            item["max_chars"] = max_chars
        self._item(out, out.tag, item)

    def _matrix(self, out: _Converted, q: dict, where: str, text: str, sel: str, sub: str) -> None:
        if sel != "Likert" or sub not in {"", "SingleAnswer", "DL", "DND"}:
            self.skipped.append(
                Skipped(where, f"Matrix {sel} {sub}".strip(), "only single-answer Likert matrices")
            )
            out.kind = "none"
            return
        rows = _ordered(q.get("Choices"), q.get("ChoiceOrder"))
        answers, _other, _exclusive = self._choices(q, out, where, key="Answers")
        if not rows or not answers:
            self.skipped.append(Skipped(where, "Matrix", "no rows or no scale points"))
            out.kind = "none"
            return
        labels = [{"code": a["code"], "label": a["label"]} for a in answers]
        row_tags = (
            q.get("ChoiceDataExportTags") if isinstance(q.get("ChoiceDataExportTags"), dict) else {}
        )
        subquestions: list[str] = []
        variables: list[str] = []
        for key, row in rows:
            label = _text(row.get("Display")) if isinstance(row, dict) else _text(row)
            custom = row_tags.get(key)
            wanted = (
                _ident(str(custom))
                if isinstance(custom, str) and custom
                else f"{out.tag}_{_suffix(str(key))}"
            )
            var = self._variable(
                out, wanted, {"scale": "ordinal", "label": (label or key)[:120], "labels": labels}
            )
            out.row_vars[str(key)] = var
            variables.append(var)
            subquestions.append(label or str(key))
        out.kind = "matrix"
        item: dict[str, Any] = {
            "type": "Matrix",
            "text": text,
            "var": variables,
            "subquestions": subquestions,
            "column_labels": [a["label"] for a in answers],
            **self._common(q, out, where),
        }
        self._item(out, out.tag, item)

    def _slider(self, out: _Converted, q: dict, where: str, text: str, sel: str, sub: str) -> None:
        config = q.get("Configuration") if isinstance(q.get("Configuration"), dict) else {}
        low = _number(config.get("CSSliderMin"))
        high = _number(config.get("CSSliderMax"))
        statements = _ordered(q.get("Choices"), q.get("ChoiceOrder")) or [("1", {"Display": ""})]
        out.kind = "number"
        for key, statement in statements:
            label = (
                _text(statement.get("Display")) if isinstance(statement, dict) else _text(statement)
            )
            wanted = out.tag if len(statements) == 1 else f"{out.tag}_{_suffix(label or str(key))}"
            spec: dict[str, Any] = {"scale": "interval", "label": (label or text)[:120]}
            if low is not None or high is not None:
                spec["valid_range"] = [low, high]
            var = self._variable(out, wanted, spec)
            out.row_vars[str(key)] = var
            if out.var is None:
                out.var = var
            item: dict[str, Any] = {
                "type": "NumericInput",
                "text": f"{text} — {label}" if label and len(statements) > 1 else text,
                "var": var,
                "display": "slider",
                **self._common(q, out, where),
            }
            decimals = _number(config.get("NumDecimals"))
            if decimals == 0:
                item["step"] = 1
            self._item(out, wanted, item)

    def _ro(self, out: _Converted, q: dict, where: str, text: str, sel: str, sub: str) -> None:
        options, _other, _exclusive = self._choices(q, out, where)
        if not options:
            self.skipped.append(Skipped(where, "Rank order", "no choices"))
            out.kind = "none"
            return
        labels = [{"code": o["code"], "label": o["label"]} for o in options]
        var = self._variable(
            out, out.tag, {"scale": "nominal", "label": text[:120], "labels": labels}
        )
        out.var, out.kind = var, "ranking"
        self._item(
            out,
            out.tag,
            {
                "type": "Ranking",
                "text": text,
                "var": var,
                "choices": options,
                **self._common(q, out, where),
            },
        )

    # ── pages from blocks and the flow ───────────────────────────────────
    def _pages(self) -> list[dict[str, Any]]:
        pages: list[dict[str, Any]] = []
        used: set[str] = set()
        if self.flow:
            self._walk(self.flow, None, pages, used, depth=0)
        else:
            self.warnings.append("No survey flow: blocks are taken in file order.")
        for block_id, block in self.blocks.items():
            if block_id in used or block.get("Type") == "Trash":
                continue
            if self.flow:
                self.skipped.append(
                    Skipped(
                        _text(block.get("Description")) or block_id,
                        "Block",
                        "not in the survey flow (unused block)",
                    )
                )
                continue
            pages.extend(self._block_pages(block, None))
        if not pages:
            raise DocumentError("The survey has no pages the format can hold.")
        return pages

    def _walk(
        self,
        items: list[Any],
        condition: dict[str, Any] | None,
        pages: list[dict[str, Any]],
        used: set[str],
        *,
        depth: int,
    ) -> None:
        for item in items:
            if not isinstance(item, dict):
                continue
            kind = item.get("Type")
            if kind in {"Block", "Standard"}:
                block_id = str(item.get("ID") or "")
                block = self.blocks.get(block_id)
                if block is None:
                    continue
                used.add(block_id)
                pages.extend(self._block_pages(block, condition))
            elif kind == "Branch":
                branch = self._condition(item.get("BranchLogic"), "flow branch")
                if branch is None:
                    self.warnings.append(
                        "A branch condition could not be transferred: its pages are always shown."
                    )
                self._walk(
                    item.get("Flow") or [], _and(condition, branch), pages, used, depth=depth + 1
                )
            elif kind == "EndSurvey":
                if condition is None and depth == 0:
                    continue  # the natural end of the survey
                page = self._end_page(item, condition)
                pages.append(page)
            elif kind in {"BlockRandomizer", "Group"}:
                if kind == "BlockRandomizer":
                    self.warnings.append(
                        "Block randomizer: its blocks keep their order (add randomize_pages to shuffle everything)."
                    )
                self._walk(item.get("Flow") or [], condition, pages, used, depth=depth + 1)
            elif kind == "EmbeddedData":
                fields = [
                    str(f.get("Field"))
                    for f in item.get("EmbeddedData") or []
                    if isinstance(f, dict) and f.get("Field")
                ]
                self.skipped.append(
                    Skipped(
                        "flow",
                        "Embedded data" + (f" ({', '.join(fields)})" if fields else ""),
                        "URL parameters and metadata are not part of the questionnaire",
                    )
                )
            else:
                self.skipped.append(
                    Skipped("flow", f"{kind} element", "not part of the questionnaire")
                )

    def _end_page(self, item: dict[str, Any], condition: dict[str, Any] | None) -> dict[str, Any]:
        options = item.get("Options") if isinstance(item.get("Options"), dict) else {}
        flag = str(options.get("ResponseFlag") or "")
        redirect = (
            options.get("EOSRedirectURL")
            if options.get("SurveyTermination") == "Redirect"
            else None
        )
        if redirect:
            kind = "redirect"
        elif flag.lower().startswith("screen") or condition is not None:
            kind = "disqualification"
        else:
            kind = "final"
        name = self.page_names.claim("screen_out" if kind == "disqualification" else "end")
        page: dict[str, Any] = {"name": name, "kind": kind}
        if kind == "disqualification":
            page["title"] = "Thank you"
            page["body"] = (
                "<p>Thank you for your interest — this survey is not for you this time.</p>"
            )
        elif kind == "final":
            page["title"] = "Thank you"
            page["body"] = "<p>Thank you for taking part.</p>"
        if condition is not None:
            page["show_if"] = condition
        if redirect:
            page["redirect_url"] = str(redirect)
        return page

    def _block_pages(
        self, block: dict[str, Any], condition: dict[str, Any] | None
    ) -> list[dict[str, Any]]:
        if block.get("Type") == "Trash":
            return []
        description = _text(block.get("Description")) or "page"
        base = _ident(description, "page")
        options = block.get("Options") if isinstance(block.get("Options"), dict) else {}
        randomize = str(options.get("RandomizeQuestions") or "")
        if options.get("Looping"):
            self.skipped.append(Skipped(description, "Loop & merge", "no loops in the format"))
        groups: list[list[Any]] = [[]]
        for element in block.get("BlockElements") or []:
            if not isinstance(element, dict):
                continue
            if element.get("Type") == "Page Break":
                groups.append([])
            elif element.get("Type") == "Question":
                groups[-1].append(str(element.get("QuestionID") or ""))
        pages: list[dict[str, Any]] = []
        for group in groups:
            items: list[dict[str, Any]] = []
            body: list[str] = []
            for qid in group:
                conv = self.converted.get(qid)
                if conv is None:
                    continue
                if conv.body:
                    if items:
                        self.warnings.append(
                            f"{conv.tag}: descriptive text placed in the page body of '{base}' "
                            "(it sat between questions)."
                        )
                    body.append(conv.body)
                for item in conv.items:
                    items.append(item)
                self.page_of[qid] = ""  # filled below once the page name is known
            if not items and not body:
                continue
            name = self.page_names.claim(base)
            for qid in group:
                if qid in self.page_of and not self.page_of[qid]:
                    self.page_of[qid] = name
            page: dict[str, Any] = {"name": name, "title": description}
            if body:
                page["body"] = "\n".join(body)
            if items:
                if randomize and randomize not in {"", "None"}:
                    if randomize != "RandomizeAll":
                        self.warnings.append(
                            f"'{description}': {randomize} question randomization became a plain shuffle."
                        )
                    page["items"] = [{"type": "Block", "randomize": True, "items": items}]
                else:
                    page["items"] = items
            else:
                page["kind"] = "content"
            if condition is not None:
                page["show_if"] = condition
            pages.append(page)
        return pages

    # ── display logic ────────────────────────────────────────────────────
    def _attach_display_logic(self) -> None:
        for qid, q in self.questions.items():
            logic = q.get("DisplayLogic")
            if not logic:
                continue
            conv = self.converted.get(qid)
            if conv is None or not conv.items:
                continue
            condition = self._condition(logic, conv.tag)
            if condition is None:
                continue
            for item in conv.items:
                item["show_if"] = condition

    def _condition(self, logic: Any, where: str) -> dict[str, Any] | None:
        """A Qualtrics BooleanExpression as a condition, or None (reported)."""
        if not isinstance(logic, dict):
            return None
        groups: list[dict[str, Any]] = []
        group_ops: list[str] = []
        for key in sorted((k for k in logic if str(k).isdigit()), key=int):
            group = logic[key]
            if not isinstance(group, dict):
                continue
            parts: list[dict[str, Any]] = []
            part_ops: list[str] = []
            for sub_key in sorted((k for k in group if str(k).isdigit()), key=int):
                expr = group[sub_key]
                if not isinstance(expr, dict):
                    continue
                converted = self._expression(expr, where)
                if converted is None:
                    return None
                parts.append(converted)
                part_ops.append(str(expr.get("Conjuction") or expr.get("Conjunction") or "And"))
            if not parts:
                continue
            groups.append(_join(parts, part_ops))
            group_ops.append(str(group.get("Conjuction") or group.get("Conjunction") or "Or"))
        if not groups:
            return None
        return _join(groups, group_ops)

    def _expression(self, expr: dict[str, Any], where: str) -> dict[str, Any] | None:
        logic_type = str(expr.get("LogicType") or "Question")
        if logic_type != "Question":
            self.skipped.append(
                Skipped(where, f"Display logic on {logic_type}", "only answers can be tested")
            )
            return None
        operator = str(expr.get("Operator") or "")
        locator = str(expr.get("LeftOperand") or expr.get("ChoiceLocator") or "")
        match = _LOCATOR_RE.match(locator)
        if not match:
            self.skipped.append(Skipped(where, "Display logic", f"unreadable locator {locator!r}"))
            return None
        qid, part, first, second = match.groups()
        conv = self.converted.get(qid)
        if conv is None or conv.kind == "none":
            self.skipped.append(
                Skipped(where, "Display logic", f"refers to {qid}, which was not imported")
            )
            return None
        negate = operator.startswith("Not")
        base_operator = operator[3:] if negate else operator
        result: dict[str, Any] | None = None
        if base_operator == "Selected":
            if conv.kind == "matrix" and first is not None and second is not None:
                var = conv.row_vars.get(first)
                code = conv.answer_codes.get(second)
                if var is not None and code is not None:
                    result = _cmp(var, "=", code)
            elif conv.kind == "multi_wide" and first is not None:
                var = conv.row_vars.get(first)
                if var is not None:
                    result = _cmp(var, "=", 1)
            elif conv.kind in {"single", "ranking"} and first is not None:
                code = conv.choice_codes.get(first)
                if conv.var is not None and code is not None:
                    result = _cmp(conv.var, "=", code)
        elif base_operator in _COMPARE:
            right = expr.get("RightOperand")
            value = _number(right)
            if value is None:
                value = str(right) if right is not None else ""
            var = conv.var
            if conv.kind == "matrix" and first is not None:
                var = conv.row_vars.get(first)
            elif (
                conv.kind == "text"
                and first is not None
                and first in conv.row_vars
                or conv.kind == "number"
                and first is not None
                and first in conv.row_vars
            ):
                var = conv.row_vars[first]
            if var is not None:
                result = _cmp(var, _COMPARE[base_operator], value)
        elif base_operator in {"Empty", "Displayed"}:
            pass
        if result is None:
            self.skipped.append(
                Skipped(where, f"Display logic {operator}", f"cannot be expressed on {conv.tag}")
            )
            return None
        return {"type": "expression", "op": "not", "left": result} if negate else result

    # ── survey options ───────────────────────────────────────────────────
    def _options(self, entry: dict[str, Any]) -> dict[str, Any]:
        so = self.options_element
        options: dict[str, Any] = {}
        language = entry.get("SurveyLanguage") or so.get("SurveyLanguage")
        if isinstance(language, str) and language.strip():
            options["language"] = language.strip().lower()[:2]
        if "BackButton" in so:
            options["allow_back"] = _is_on(so.get("BackButton"))
        if "ProgressBarDisplay" in so:
            options["show_progress"] = str(so.get("ProgressBarDisplay") or "None") != "None"
        return options

    def _ui(self) -> dict[str, Any]:
        so = self.options_element
        ui: dict[str, Any] = {}
        if so.get("SurveyTermination") == "Redirect" and so.get("EOSRedirectURL"):
            ui["redirect_url"] = str(so["EOSRedirectURL"])
        return ui


# ─── expression helpers ──────────────────────────────────────────────────────


def _var(name: str) -> dict[str, Any]:
    return {"type": "var", "name": name}


def _cmp(var: str, op: str, value: Any) -> dict[str, Any]:
    return {"type": "expression", "op": op, "left": _var(var), "right": value}


def _and(left: dict[str, Any] | None, right: dict[str, Any] | None) -> dict[str, Any] | None:
    if left is None:
        return right
    if right is None:
        return left
    return {"type": "expression", "op": "and", "left": left, "right": right}


def _join(parts: list[dict[str, Any]], ops: list[str]) -> dict[str, Any]:
    """Left-associative And/Or chain; ``ops[i]`` joins ``parts[i]`` to the left."""
    result = parts[0]
    for index in range(1, len(parts)):
        op = "or" if ops[index].lower().startswith("or") else "and"
        result = {"type": "expression", "op": op, "left": result, "right": parts[index]}
    return result


# ─── public API ──────────────────────────────────────────────────────────────


def import_qsf(payload: dict[str, Any] | str) -> QsfImportResult:
    """Convert a Qualtrics export (parsed JSON or its text) to a document."""
    if isinstance(payload, str):
        if len(payload) > _MAX_SOURCE:
            raise DocumentError("File too large to import (20 MB limit).")
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise DocumentError(f"Not valid JSON: line {exc.lineno}: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise DocumentError("Not a Qualtrics export: expected a JSON object.")
    importer = _Importer(payload)
    document = importer.run()
    return QsfImportResult(document=document, warnings=importer.warnings, skipped=importer.skipped)


def import_qsf_file(path: str | Path) -> QsfImportResult:
    return import_qsf(Path(path).read_text(encoding="utf-8"))


__all__ = ["QsfImportResult", "Skipped", "import_qsf", "import_qsf_file"]
