"""Read a LimeSurvey survey structure (``.lss``) export as a questionnaire document.

An LSS file is the XML LimeSurvey writes for "Export survey structure": one
``<document>`` with a table per entity — ``groups``, ``questions``,
``subquestions``, ``answers``, ``question_attributes``, ``conditions``,
``surveys``, ``surveys_languagesettings`` and (LimeSurvey 4+) the ``*_l10ns``
tables that carry the texts. This module maps what the questionnaire format
can hold and reports the rest, like :mod:`siamang.model.import_qsf`::

    result = import_lss(xml_text)
    result.document          # questionnaire-1.0
    result.skipped           # [Skipped(where="q7", what="Array dual scale", why=...), ...]
    result.warnings          # things that were transferred approximately

What maps
    L / ! / O (list, dropdown, list with comment) -> SingleChoice; M / P ->
    MultiChoice (subquestions as choices); Y, G, 5 -> SingleChoice with fixed
    codes; N -> NumericInput (slider attributes -> slider, min/max -> range);
    K -> one NumericInput per subquestion; S / T / U -> OpenText (long texts
    multiline, maximum_chars); Q -> one OpenText per subquestion; F / H / A /
    B / C / E arrays -> Matrix (one variable per subquestion); R -> Ranking;
    X -> the page body; D (date) -> OpenText with a warning. Mandatory, "other"
    answers, answer/subquestion order, choice randomization (random_order),
    the survey format (group by group / question by question / all in one),
    group order, welcome and end texts, back button, progress bar, language,
    question relevance (ExpressionScript comparisons joined with and/or, on
    single, multi, matrix, numeric and text answers) and group relevance,
    legacy conditions when a question carries no relevance equation.

What is reported as skipped
    Array dual scale / numbers / texts, equations, file upload, language
    switch; question randomization groups and group randomization (order is
    kept); quotas and assessments; relevance that tests anything but an
    answer with =, !=, <, <=, >, >= (is_empty, regex, arithmetic, functions);
    validation regexes (preg); comment fields of O / P; default answers.
"""

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from siamang.model.document import SCHEMA_VERSION, DocumentError
from siamang.model.import_qsf import Skipped, _code, _ident, _number, _suffix, _text

_MAX_SOURCE = 20_000_000

_UNSUPPORTED = {
    "1": "Array dual scale",
    ":": "Array (numbers)",
    ";": "Array (texts)",
    "*": "Equation",
    "|": "File upload",
    "I": "Language switch",
}
_FIXED_CHOICES: dict[str, list[tuple[Any, str]]] = {
    "Y": [("Y", "Yes"), ("N", "No")],
    "G": [("M", "Male"), ("F", "Female")],
    "5": [(1, "1"), (2, "2"), (3, "3"), (4, "4"), (5, "5")],
}
_FIXED_SCALES: dict[str, list[tuple[Any, str]]] = {
    "A": [(1, "1"), (2, "2"), (3, "3"), (4, "4"), (5, "5")],
    "B": [(n, str(n)) for n in range(1, 11)],
    "C": [("Y", "Yes"), ("N", "No"), ("U", "Uncertain")],
    "E": [("I", "Increase"), ("S", "Same"), ("D", "Decrease")],
}
_COMPARE = {"==": "=", "=": "=", "!=": "!=", "<": "<", "<=": "<=", ">": ">", ">=": ">="}
_TOKEN_RE = re.compile(
    r"\s*(?:(?P<num>-?\d+(?:\.\d+)?)|(?P<str>\"[^\"]*\"|'[^']*')|(?P<op>==|!=|<=|>=|<|>|&&|\|\||=|\(|\)|!)"
    r"|(?P<word>[A-Za-z_][A-Za-z0-9_.]*))"
)


@dataclass(frozen=True, slots=True)
class LssImportResult:
    document: dict[str, Any]
    warnings: list[str] = field(default_factory=list)
    skipped: list[Skipped] = field(default_factory=list)


# ─── XML helpers ─────────────────────────────────────────────────────────────


def _rows(root: ET.Element, table: str) -> list[dict[str, str]]:
    """The rows of one exported table as dicts of plain strings."""
    node = root.find(table)
    if node is None:
        return []
    out: list[dict[str, str]] = []
    for row in node.iter("row"):
        record: dict[str, str] = {}
        for cell in row:
            record[cell.tag] = (cell.text or "").strip()
        out.append(record)
    return out


def _rich(value: str) -> str:
    """Question/group texts are HTML: plain text for labels, HTML kept for bodies."""
    return _text(html.unescape(value)) if value else ""


# ─── converted questions ─────────────────────────────────────────────────────


@dataclass(slots=True)
class _Converted:
    qid: str
    code: str
    items: list[dict[str, Any]]
    body: str | None = None
    kind: str = "single"  # single | multi | multi_wide | matrix | number | text | ranking | none
    var: str | None = None
    row_vars: dict[str, str] = field(default_factory=dict)  # subquestion code -> variable
    codes: dict[str, Any] = field(default_factory=dict)  # answer code -> stored code


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
    def __init__(self, root: ET.Element) -> None:
        self.root = root
        self.warnings: list[str] = []
        self.skipped: list[Skipped] = []
        self.variables: dict[str, dict[str, Any]] = {}
        self.ids = _Names()
        self.var_names = _Names()
        self.page_names = _Names()
        self.language = "en"
        self.survey: dict[str, str] = {}
        self.settings: dict[str, str] = {}
        self.groups: list[dict[str, str]] = []
        self.questions: list[dict[str, str]] = []
        self.subquestions: dict[str, list[dict[str, str]]] = {}
        self.answers: dict[str, list[dict[str, str]]] = {}
        self.attributes: dict[str, dict[str, str]] = {}
        self.conditions: dict[str, list[dict[str, str]]] = {}
        self.converted: dict[str, _Converted] = {}
        self.by_code: dict[str, _Converted] = {}
        self.logic_refs: set[str] = set()

    # ── entry ────────────────────────────────────────────────────────────
    def run(self) -> dict[str, Any]:
        self._collect()
        for q in self.questions:
            conv = self._question(q)
            self.converted[q["qid"]] = conv
            self.by_code[conv.code] = conv
        pages = self._pages()
        self._attach_relevance()
        self._prune_variables(pages)
        title = _rich(self.settings.get("surveyls_title", "")) or "Imported survey"
        document: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "title": title}
        options = self._options()
        if options:
            document["options"] = options
        document["variables"] = self.variables
        document["pages"] = pages
        if self.settings.get("surveyls_url"):
            document["ui"] = {"redirect_url": self.settings["surveyls_url"]}
        return document

    def _collect(self) -> None:
        root = self.root
        if (root.findtext("LimeSurveyDocType") or "").strip() != "Survey":
            raise DocumentError("Not a LimeSurvey survey export (LimeSurveyDocType is not Survey).")
        languages = [lang.text.strip() for lang in root.iter("language") if lang.text]
        surveys = _rows(root, "surveys")
        self.survey = surveys[0] if surveys else {}
        self.language = (self.survey.get("language") or (languages[0] if languages else "en"))[:2]
        if len(set(languages)) > 1:
            self.warnings.append(
                f"Multilingual survey: only '{self.language}' was imported ({', '.join(sorted(set(languages)))})."
            )
        settings = [
            r
            for r in _rows(root, "surveys_languagesettings")
            if r.get("surveyls_language", self.language) == self.language
        ] or _rows(root, "surveys_languagesettings")
        self.settings = settings[0] if settings else {}
        # texts: LimeSurvey 4+ keeps them in *_l10ns tables, 3.x inline
        group_texts = self._l10ns("group_l10ns", "gid")
        question_texts = self._l10ns("question_l10ns", "qid")
        answer_texts = self._l10ns("answer_l10ns", "aid")
        self.groups = sorted(
            (self._merge(r, group_texts.get(r.get("gid", ""))) for r in self._lang_rows("groups")),
            key=lambda r: _number(r.get("group_order")) or 0,
        )
        questions = [
            self._merge(r, question_texts.get(r.get("qid", "")))
            for r in self._lang_rows("questions")
            if (r.get("parent_qid") or "0") == "0"
        ]
        self.questions = sorted(
            questions,
            key=lambda r: (
                self._group_order(r.get("gid", "")),
                _number(r.get("question_order")) or 0,
            ),
        )
        for r in self._lang_rows("subquestions"):
            r = self._merge(r, question_texts.get(r.get("qid", "")))
            self.subquestions.setdefault(r.get("parent_qid", ""), []).append(r)
        for sub in self.subquestions.values():
            sub.sort(
                key=lambda r: (
                    _number(r.get("scale_id")) or 0,
                    _number(r.get("question_order")) or 0,
                )
            )
        for r in self._lang_rows("answers"):
            r = self._merge(r, answer_texts.get(r.get("aid", "")))
            self.answers.setdefault(r.get("qid", ""), []).append(r)
        for ans in self.answers.values():
            ans.sort(
                key=lambda r: (_number(r.get("scale_id")) or 0, _number(r.get("sortorder")) or 0)
            )
        for r in _rows(root, "question_attributes"):
            if r.get("language") and r["language"] != self.language:
                continue
            self.attributes.setdefault(r.get("qid", ""), {})[r.get("attribute", "")] = r.get(
                "value", ""
            )
        for r in _rows(root, "conditions"):
            self.conditions.setdefault(r.get("qid", ""), []).append(r)
        if not self.questions and not self.groups:
            raise DocumentError("Not a LimeSurvey export: no groups or questions found.")
        if _rows(root, "quota"):
            self.skipped.append(
                Skipped(
                    "survey",
                    "Quotas",
                    "quotas are fieldwork settings, not part of the questionnaire",
                )
            )
        if _rows(root, "assessments"):
            self.skipped.append(Skipped("survey", "Assessments", "no assessments in the format"))
        # multi-choice questions whose subquestions are tested by relevance are stored wide
        for q in self.questions:
            self._scan_relevance(q.get("relevance", ""))
        for g in self.groups:
            self._scan_relevance(g.get("grelevance", ""))
        for rows in self.conditions.values():
            for c in rows:
                field_name = c.get("cfieldname", "")
                m = re.match(r"^\d+X\d+X(\d+)(.*)$", field_name)
                if m and m.group(2):
                    self.logic_refs.add(m.group(1))

    def _l10ns(self, table: str, key: str) -> dict[str, dict[str, str]]:
        out: dict[str, dict[str, str]] = {}
        for r in _rows(self.root, table):
            if r.get("language", self.language) != self.language and r.get(key) in out:
                continue
            if r.get("language", self.language) == self.language or r.get(key) not in out:
                out[r.get(key, "")] = r
        return out

    def _lang_rows(self, table: str) -> list[dict[str, str]]:
        rows = _rows(self.root, table)
        mine = [r for r in rows if not r.get("language") or r["language"] == self.language]
        return mine or rows

    @staticmethod
    def _merge(row: dict[str, str], texts: dict[str, str] | None) -> dict[str, str]:
        if not texts:
            return row
        merged = dict(row)
        for key in ("question", "help", "answer", "group_name", "description"):
            if texts.get(key) and not merged.get(key):
                merged[key] = texts[key]
        return merged

    def _group_order(self, gid: str) -> float:
        for index, g in enumerate(self.groups):
            if g.get("gid") == gid:
                return index
        return len(self.groups)

    def _scan_relevance(self, expression: str) -> None:
        for m in re.finditer(
            r"([A-Za-z_][A-Za-z0-9]*)_([A-Za-z0-9]+)(?:\.NAOK)?\s*(?:==|!=|=)", expression
        ):
            self.logic_refs.add(m.group(1))

    # ── questions ────────────────────────────────────────────────────────
    def _question(self, q: dict[str, str]) -> _Converted:
        code = _ident(q.get("title") or f"q{q.get('qid')}", "q")
        qtype = q.get("type", "")
        text = _rich(q.get("question", "")) or code
        where = q.get("title") or code
        out = _Converted(qid=q.get("qid", ""), code=code, items=[])
        attrs = self.attributes.get(out.qid, {})
        if qtype == "X":
            out.kind = "none"
            out.body = html.unescape(q.get("question", "")) or text
            return out
        if qtype in _UNSUPPORTED:
            self.skipped.append(
                Skipped(where, _UNSUPPORTED[qtype], "no such question type in the format")
            )
            out.kind = "none"
            return out
        if q.get("preg"):
            self.skipped.append(
                Skipped(where, "Validation regex", "only numeric ranges and lengths")
            )
        if attrs.get("random_group") or attrs.get("randomization_group"):
            self.skipped.append(Skipped(where, "Randomization group", "question order is kept"))
        handler = {
            "L": self._list,
            "!": self._list,
            "O": self._list,
            "Y": self._fixed,
            "G": self._fixed,
            "5": self._fixed,
            "M": self._multi,
            "P": self._multi,
            "N": self._numeric,
            "K": self._numeric_many,
            "S": self._free_text,
            "T": self._free_text,
            "U": self._free_text,
            "D": self._free_text,
            "Q": self._text_many,
            "F": self._array,
            "H": self._array,
            "A": self._array,
            "B": self._array,
            "C": self._array,
            "E": self._array,
            "R": self._ranking,
        }.get(qtype)
        if handler is None:
            self.skipped.append(Skipped(where, f"{qtype or '?'} question", "unknown question type"))
            out.kind = "none"
            return out
        handler(out, q, where, text, qtype, attrs)
        return out

    def _common(self, q: dict[str, str], attrs: dict[str, str], where: str) -> dict[str, Any]:
        base: dict[str, Any] = {}
        if (q.get("mandatory") or "N").upper().startswith("Y"):
            base["required"] = True
        if attrs.get("random_order") == "1":
            base["randomize"] = True
        if _rich(q.get("help", "")):
            self.skipped.append(Skipped(where, "Help text", "no help field in the format"))
        return base

    def _variable(self, wanted: str, spec: dict[str, Any]) -> str:
        name = self.var_names.claim(wanted)
        self.variables[name] = spec
        return name

    def _item(self, out: _Converted, wanted_id: str, item: dict[str, Any]) -> None:
        item["id"] = self.ids.claim(wanted_id)
        out.items.append(item)

    def _answer_options(self, out: _Converted, where: str) -> list[dict[str, Any]]:
        options: list[dict[str, Any]] = []
        for a in self.answers.get(out.qid, []):
            if (_number(a.get("scale_id")) or 0) != 0:
                continue
            raw = a.get("code", "")
            code = _code(raw)
            out.codes[raw] = code
            options.append({"code": code, "label": _rich(a.get("answer", "")) or raw})
        return options

    def _list(
        self, out: _Converted, q: dict, where: str, text: str, qtype: str, attrs: dict
    ) -> None:
        options = self._answer_options(out, where)
        if not options:
            self.skipped.append(Skipped(where, "List", "no answer options"))
            out.kind = "none"
            return
        var = self._variable(
            out.code,
            {
                "scale": "nominal",
                "label": text[:120],
                "labels": [{"code": o["code"], "label": o["label"]} for o in options],
            },
        )
        out.var, out.kind = var, "single"
        item: dict[str, Any] = {
            "type": "SingleChoice",
            "text": text,
            "var": var,
            "choices": options,
            **self._common(q, attrs, where),
        }
        if (q.get("other") or "N").upper() == "Y":
            item["other_specify"] = True
        if qtype == "!":
            item["display"] = "dropdown"
        self._item(out, out.code, item)
        if qtype == "O":
            self.skipped.append(
                Skipped(
                    where, "Comment field", "list with comment: the comment box is not transferred"
                )
            )

    def _fixed(
        self, out: _Converted, q: dict, where: str, text: str, qtype: str, attrs: dict
    ) -> None:
        options = [{"code": code, "label": label} for code, label in _FIXED_CHOICES[qtype]]
        for o in options:
            out.codes[str(o["code"])] = o["code"]
        scale = "ordinal" if qtype == "5" else "nominal"
        var = self._variable(
            out.code, {"scale": scale, "label": text[:120], "labels": [dict(o) for o in options]}
        )
        out.var, out.kind = var, "single"
        item: dict[str, Any] = {
            "type": "SingleChoice",
            "text": text,
            "var": var,
            "choices": options,
            **self._common(q, attrs, where),
        }
        if qtype == "5":
            item["display"] = "buttons"
        self._item(out, out.code, item)

    def _multi(
        self, out: _Converted, q: dict, where: str, text: str, qtype: str, attrs: dict
    ) -> None:
        subs = self.subquestions.get(out.qid, [])
        if not subs:
            self.skipped.append(Skipped(where, "Multiple choice", "no subquestions"))
            out.kind = "none"
            return
        options: list[dict[str, Any]] = []
        for s in subs:
            raw = s.get("title", "")
            code = _code(raw)
            out.codes[raw] = code
            options.append({"code": code, "label": _rich(s.get("question", "")) or raw})
        other = (q.get("other") or "N").upper() == "Y"
        exclusive = [
            o["code"]
            for o in options
            if str(o["code"])
            in {x.strip() for x in attrs.get("exclude_all_others", "").split(";") if x.strip()}
        ]
        if qtype == "P":
            self.skipped.append(
                Skipped(
                    where,
                    "Comment fields",
                    "multiple choice with comments: the comment boxes are not transferred",
                )
            )
        if out.qid in self.logic_refs or out.code in self.logic_refs:
            yes_no = [{"code": 0, "label": "No"}, {"code": 1, "label": "Yes"}]
            variables: list[str] = []
            for s, o in zip(subs, options, strict=True):
                var = self._variable(
                    f"{out.code}_{_suffix(s.get('title', ''))}",
                    {"scale": "nominal", "label": o["label"][:120], "labels": yes_no},
                )
                out.row_vars[s.get("title", "")] = var
                variables.append(var)
            out.kind, out.var = "multi_wide", variables[0]
            item: dict[str, Any] = {
                "type": "MultiChoice",
                "text": text,
                "var": variables,
                "mode": "wide",
                **self._common(q, attrs, where),
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
            self._item(out, out.code, item)
            return
        var = self._variable(
            out.code,
            {
                "scale": "nominal",
                "label": text[:120],
                "labels": [{"code": o["code"], "label": o["label"]} for o in options],
            },
        )
        out.var, out.kind = var, "multi"
        item = {
            "type": "MultiChoice",
            "text": text,
            "var": var,
            "choices": options,
            **self._common(q, attrs, where),
        }
        if other:
            item["other_specify"] = True
        if exclusive:
            item["exclusive"] = exclusive
        self._item(out, out.code, item)

    def _numeric_spec(
        self, text: str, attrs: dict[str, str]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        spec: dict[str, Any] = {"scale": "ratio", "label": text[:120]}
        extra: dict[str, Any] = {}
        slider = attrs.get("slider_layout") == "1"
        low = _number(attrs.get("slider_min") if slider else attrs.get("min_num_value_n"))
        high = _number(attrs.get("slider_max") if slider else attrs.get("max_num_value_n"))
        if low is not None or high is not None:
            spec["valid_range"] = [low, high]
        if slider:
            spec["scale"] = "interval"
            extra["display"] = "slider"
            step = _number(attrs.get("slider_accuracy"))
            if step:
                extra["step"] = step
        elif attrs.get("num_value_int_only") == "1":
            extra["step"] = 1
        return spec, extra

    def _numeric(
        self, out: _Converted, q: dict, where: str, text: str, qtype: str, attrs: dict
    ) -> None:
        spec, extra = self._numeric_spec(text, attrs)
        var = self._variable(out.code, spec)
        out.var, out.kind = var, "number"
        self._item(
            out,
            out.code,
            {
                "type": "NumericInput",
                "text": text,
                "var": var,
                **extra,
                **self._common(q, attrs, where),
            },
        )

    def _numeric_many(
        self, out: _Converted, q: dict, where: str, text: str, qtype: str, attrs: dict
    ) -> None:
        subs = self.subquestions.get(out.qid, [])
        if not subs:
            self.skipped.append(Skipped(where, "Multiple numerical input", "no subquestions"))
            out.kind = "none"
            return
        out.kind = "number"
        for s in subs:
            label = _rich(s.get("question", "")) or s.get("title", "")
            spec, extra = self._numeric_spec(label, attrs)
            var = self._variable(f"{out.code}_{_suffix(s.get('title', ''))}", spec)
            out.row_vars[s.get("title", "")] = var
            out.var = out.var or var
            self._item(
                out,
                f"{out.code}_{_suffix(s.get('title', ''))}",
                {
                    "type": "NumericInput",
                    "text": f"{text} — {label}",
                    "var": var,
                    **extra,
                    **self._common(q, attrs, where),
                },
            )

    def _free_text(
        self, out: _Converted, q: dict, where: str, text: str, qtype: str, attrs: dict
    ) -> None:
        var = self._variable(out.code, {"scale": "nominal", "label": text[:120]})
        out.var, out.kind = var, "text"
        item: dict[str, Any] = {
            "type": "OpenText",
            "text": text,
            "var": var,
            **self._common(q, attrs, where),
        }
        if qtype in {"T", "U"}:
            item["multiline"] = True
        max_chars = _number(attrs.get("maximum_chars"))
        if isinstance(max_chars, int) and max_chars > 0:
            item["max_chars"] = max_chars
        if qtype == "D":
            self.warnings.append(
                f"{where}: date question became free text (no date type in the format)."
            )
        self._item(out, out.code, item)

    def _text_many(
        self, out: _Converted, q: dict, where: str, text: str, qtype: str, attrs: dict
    ) -> None:
        subs = self.subquestions.get(out.qid, [])
        if not subs:
            self.skipped.append(Skipped(where, "Multiple short text", "no subquestions"))
            out.kind = "none"
            return
        out.kind = "text"
        for s in subs:
            label = _rich(s.get("question", "")) or s.get("title", "")
            var = self._variable(
                f"{out.code}_{_suffix(s.get('title', ''))}",
                {"scale": "nominal", "label": label[:120]},
            )
            out.row_vars[s.get("title", "")] = var
            out.var = out.var or var
            self._item(
                out,
                f"{out.code}_{_suffix(s.get('title', ''))}",
                {
                    "type": "OpenText",
                    "text": f"{text} — {label}",
                    "var": var,
                    **self._common(q, attrs, where),
                },
            )

    def _array(
        self, out: _Converted, q: dict, where: str, text: str, qtype: str, attrs: dict
    ) -> None:
        subs = self.subquestions.get(out.qid, [])
        if qtype in _FIXED_SCALES:
            answers = [{"code": c, "label": lbl} for c, lbl in _FIXED_SCALES[qtype]]
            for a in answers:
                out.codes[str(a["code"])] = a["code"]
        else:
            answers = self._answer_options(out, where)
        if not subs or not answers:
            self.skipped.append(Skipped(where, "Array", "no subquestions or no answer options"))
            out.kind = "none"
            return
        labels = [{"code": a["code"], "label": a["label"]} for a in answers]
        variables: list[str] = []
        subquestions: list[str] = []
        for s in subs:
            label = _rich(s.get("question", "")) or s.get("title", "")
            var = self._variable(
                f"{out.code}_{_suffix(s.get('title', ''))}",
                {"scale": "ordinal", "label": label[:120], "labels": labels},
            )
            out.row_vars[s.get("title", "")] = var
            variables.append(var)
            subquestions.append(label)
        out.kind, out.var = "matrix", variables[0]
        self._item(
            out,
            out.code,
            {
                "type": "Matrix",
                "text": text,
                "var": variables,
                "subquestions": subquestions,
                "column_labels": [a["label"] for a in answers],
                **self._common(q, attrs, where),
            },
        )

    def _ranking(
        self, out: _Converted, q: dict, where: str, text: str, qtype: str, attrs: dict
    ) -> None:
        options = self._answer_options(out, where)
        if not options:
            self.skipped.append(Skipped(where, "Ranking", "no answer options"))
            out.kind = "none"
            return
        var = self._variable(
            out.code,
            {
                "scale": "nominal",
                "label": text[:120],
                "labels": [{"code": o["code"], "label": o["label"]} for o in options],
            },
        )
        out.var, out.kind = var, "ranking"
        self._item(
            out,
            out.code,
            {
                "type": "Ranking",
                "text": text,
                "var": var,
                "choices": options,
                **self._common(q, attrs, where),
            },
        )

    # ── pages ────────────────────────────────────────────────────────────
    def _pages(self) -> list[dict[str, Any]]:
        pages: list[dict[str, Any]] = []
        welcome = self.settings.get("surveyls_welcometext", "")
        if _rich(welcome):
            pages.append(
                {
                    "name": self.page_names.claim("welcome"),
                    "kind": "content",
                    "title": _rich(self.settings.get("surveyls_title", "")) or "Welcome",
                    "body": html.unescape(welcome),
                }
            )
        fmt = (self.survey.get("format") or "G").upper()
        if fmt == "A":
            self.warnings.append(
                "Survey format 'all in one': every group is one page anyway (the format has no single-page mode)."
            )
        by_group: dict[str, list[dict[str, str]]] = {}
        for q in self.questions:
            by_group.setdefault(q.get("gid", ""), []).append(q)
        for g in self.groups:
            gid = g.get("gid", "")
            title = _rich(g.get("group_name", "")) or "page"
            base = _ident(title, "page")
            condition = self._condition(g.get("grelevance", ""), f"group '{title}'")
            if g.get("randomization_group"):
                self.skipped.append(Skipped(title, "Group randomization", "group order is kept"))
            if fmt == "S":
                units = [[q] for q in by_group.get(gid, [])]
            else:
                units = [by_group.get(gid, [])]
            first = True
            for unit in units:
                items: list[dict[str, Any]] = []
                body: list[str] = []
                if first and g.get("description") and _rich(g["description"]):
                    body.append(html.unescape(g["description"]))
                for q in unit:
                    conv = self.converted.get(q.get("qid", ""))
                    if conv is None:
                        continue
                    if conv.body:
                        if items:
                            self.warnings.append(
                                f"{conv.code}: text display placed in the page body of '{base}' (it sat between questions)."
                            )
                        body.append(conv.body)
                    items.extend(conv.items)
                if not items and not body:
                    first = False
                    continue
                page: dict[str, Any] = {"name": self.page_names.claim(base), "title": title}
                if body:
                    page["body"] = "\n".join(body)
                if items:
                    page["items"] = items
                else:
                    page["kind"] = "content"
                if condition is not None:
                    page["show_if"] = condition
                pages.append(page)
                first = False
        end_text = self.settings.get("surveyls_endtext", "")
        if _rich(end_text):
            pages.append(
                {
                    "name": self.page_names.claim("end"),
                    "kind": "final",
                    "title": "Thank you",
                    "body": html.unescape(end_text),
                }
            )
        if not pages:
            raise DocumentError("The survey has no pages the format can hold.")
        return pages

    def _options(self) -> dict[str, Any]:
        options: dict[str, Any] = {}
        if self.language:
            options["language"] = self.language.lower()[:2]
        if "allowprev" in self.survey:
            options["allow_back"] = self.survey["allowprev"].upper().startswith("Y")
        if "showprogress" in self.survey:
            options["show_progress"] = self.survey["showprogress"].upper().startswith("Y")
        return options

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

    # ── relevance ────────────────────────────────────────────────────────
    def _attach_relevance(self) -> None:
        for q in self.questions:
            conv = self.converted.get(q.get("qid", ""))
            if conv is None or not conv.items:
                continue
            expression = (q.get("relevance") or "").strip()
            condition: dict[str, Any] | None = None
            if expression and expression != "1":
                condition = self._condition(expression, conv.code)
            elif self.conditions.get(conv.qid):
                condition = self._legacy_conditions(self.conditions[conv.qid], conv.code)
            if condition is None:
                continue
            for item in conv.items:
                item["show_if"] = condition

    def _legacy_conditions(self, rows: list[dict[str, str]], where: str) -> dict[str, Any] | None:
        """Conditions table (LimeSurvey 2/3): scenarios are OR-ed, rows within
        a scenario AND-ed; ``cfieldname`` is sidXgidXqid[subcode]."""
        scenarios: dict[str, list[dict[str, Any]]] = {}
        for c in rows:
            m = re.match(r"^\d+X\d+X(\d+)(.*)$", c.get("cfieldname", ""))
            if not m:
                self.skipped.append(
                    Skipped(where, "Condition", f"unreadable field {c.get('cfieldname')!r}")
                )
                return None
            conv = self.converted.get(m.group(1))
            method = _COMPARE.get(c.get("method", "=="))
            if conv is None or conv.kind == "none" or method is None:
                self.skipped.append(
                    Skipped(
                        where,
                        "Condition",
                        "refers to a question that was not imported or uses an operator the format lacks",
                    )
                )
                return None
            part = self._compare(conv, m.group(2) or None, method, c.get("value", ""), where)
            if part is None:
                return None
            scenarios.setdefault(c.get("scenario", "1"), []).append(part)
        groups = [_chain(parts, "and") for parts in scenarios.values()]
        return _chain(groups, "or") if groups else None

    def _condition(self, expression: str, where: str) -> dict[str, Any] | None:
        expression = (expression or "").strip()
        if not expression or expression == "1":
            return None
        try:
            tokens = _tokenize(expression)
            parser = _Parser(tokens, self, where)
            result = parser.parse()
            if parser.pos != len(tokens):
                raise _Unsupported("trailing text")
            return result
        except _Unsupported as exc:
            self.skipped.append(
                Skipped(where, "Relevance", f"{exc} — shown always: {expression[:80]}")
            )
            return None

    def _compare(
        self, conv: _Converted, sub: str | None, op: str, raw: str, where: str
    ) -> dict[str, Any] | None:
        value: Any = raw
        if conv.kind == "multi_wide" and sub:
            var = conv.row_vars.get(sub)
            if var is None:
                return None
            truthy = str(raw).strip().upper() in {"Y", "1"}
            return _cmp(var, "=" if (op == "=") == truthy else "!=", 1)
        if conv.kind in {"matrix", "number", "text"} and sub:
            var = conv.row_vars.get(sub)
        else:
            var = conv.var
        if var is None:
            return None
        if conv.kind in {"single", "ranking", "matrix", "multi"}:
            value = conv.codes.get(str(raw), _code(raw))
        elif conv.kind == "number":
            value = _number(raw) if _number(raw) is not None else raw
        return _cmp(var, op, value)


# ─── relevance expressions ───────────────────────────────────────────────────


class _Unsupported(Exception):
    pass


def _tokenize(expression: str) -> list[tuple[str, str]]:
    tokens: list[tuple[str, str]] = []
    pos = 0
    while pos < len(expression):
        if expression[pos].isspace():
            pos += 1
            continue
        m = _TOKEN_RE.match(expression, pos)
        if not m or m.end() == pos:
            raise _Unsupported(f"unreadable at {expression[pos : pos + 12]!r}")
        pos = m.end()
        kind = m.lastgroup or ""
        tokens.append((kind, m.group(kind)))
    return tokens


class _Parser:
    """``or`` > ``and`` > ``not`` > comparison, with parentheses."""

    def __init__(self, tokens: list[tuple[str, str]], importer: _Importer, where: str) -> None:
        self.tokens = tokens
        self.pos = 0
        self.importer = importer
        self.where = where

    def peek(self) -> tuple[str, str] | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def take(self) -> tuple[str, str]:
        token = self.peek()
        if token is None:
            raise _Unsupported("unexpected end")
        self.pos += 1
        return token

    def parse(self) -> dict[str, Any]:
        left = self.parse_and()
        while self.peek() in {("op", "||"), ("word", "or"), ("word", "OR")}:
            self.take()
            left = {"type": "expression", "op": "or", "left": left, "right": self.parse_and()}
        return left

    def parse_and(self) -> dict[str, Any]:
        left = self.parse_not()
        while self.peek() in {("op", "&&"), ("word", "and"), ("word", "AND")}:
            self.take()
            left = {"type": "expression", "op": "and", "left": left, "right": self.parse_not()}
        return left

    def parse_not(self) -> dict[str, Any]:
        if self.peek() in {("op", "!"), ("word", "not"), ("word", "NOT")}:
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
        if token[0] != "word":
            raise _Unsupported(f"unexpected {token[1]!r}")
        name = token[1]
        if self.peek() == ("op", "("):
            raise _Unsupported(f"function {name}()")
        op_token = self.take()
        if op_token[0] != "op" or op_token[1] not in _COMPARE:
            raise _Unsupported(f"operator {op_token[1]!r}")
        value_token = self.take()
        if value_token[0] == "str":
            raw = value_token[1][1:-1]
        elif value_token[0] == "num":
            raw = value_token[1]
        else:
            raise _Unsupported("comparison with another answer")
        return self.compare(name, _COMPARE[op_token[1]], raw)

    def compare(self, name: str, op: str, raw: str) -> dict[str, Any]:
        base = name.split(".")[0]  # strip .NAOK / .shown / .value
        conv = self.importer.by_code.get(base)
        sub: str | None = None
        if conv is None and "_" in base:
            # qcode_subcode: a subquestion of a multi, array, numeric or text question
            code, _, sub = base.rpartition("_")
            conv = self.importer.by_code.get(code)
            if conv is not None and sub not in conv.row_vars:
                conv = None
        if conv is None or conv.kind == "none":
            raise _Unsupported(f"refers to {name!r}, which was not imported")
        result = self.importer._compare(conv, sub, op, raw, self.where)
        if result is None:
            raise _Unsupported(f"cannot be expressed on {name!r}")
        return result


def _var(name: str) -> dict[str, Any]:
    return {"type": "var", "name": name}


def _cmp(var: str, op: str, value: Any) -> dict[str, Any]:
    return {"type": "expression", "op": op, "left": _var(var), "right": value}


def _chain(parts: list[dict[str, Any]], op: str) -> dict[str, Any]:
    result = parts[0]
    for part in parts[1:]:
        result = {"type": "expression", "op": op, "left": result, "right": part}
    return result


# ─── public API ──────────────────────────────────────────────────────────────


def import_lss(text: str | bytes) -> LssImportResult:
    """Convert a LimeSurvey structure export (XML text) to a document."""
    if len(text) > _MAX_SOURCE:
        raise DocumentError("File too large to import (20 MB limit).")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise DocumentError(f"Not valid XML: {exc}") from exc
    if root.tag != "document":
        raise DocumentError("Not a LimeSurvey export: expected a <document> root.")
    importer = _Importer(root)
    document = importer.run()
    return LssImportResult(document=document, warnings=importer.warnings, skipped=importer.skipped)


def import_lss_file(path: str | Path) -> LssImportResult:
    return import_lss(Path(path).read_bytes())


__all__ = ["LssImportResult", "import_lss", "import_lss_file"]
