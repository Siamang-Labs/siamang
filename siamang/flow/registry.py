"""The node registry: what a flow can be made of.

Every node type is one YAML file under ``siamang/flow/nodes/<category>/``::

    type: analyze.crosstab
    category: analyze
    title: Crosstab
    description: Cross-tabulation with chi-square and Cramér's V.
    inputs:
      data: SurveyData
    outputs:
      table: Table
      stat: Stat
    params:
      row: {kind: variable, scales: [nominal, ordinal], required: true}
      col: {kind: variable, scales: [nominal, ordinal], required: true}
      pct: {kind: enum, values: [none, row, col, total], default: col}
    template: |
      {out.table} = {in.data}.report.crosstab({row!r}, {col!r}, pct={pct!r})
      {out.stat} = {out.table}.stats
    preview: table

The template is the node's only implementation: the code generator writes it
into the analysis script and :class:`~siamang.flow.runner.FlowRunner` executes
the very same text, so batch and interactive results cannot drift apart.
Placeholders: ``{in.<port>}`` and ``{out.<port>}`` are variable names,
``{<param>!r}`` is the parameter rendered as a Python literal (a condition
becomes an ``Expression`` call, targets and mappings get typed codes), and
``{node!r}`` is the node id.

A template may also be a list of fragments, each either a string or
``{when: <condition>, code: ...}`` — the fragment is written only when the
condition holds. A condition is ``<param>`` (set: not empty and not false),
``<param>=<value>`` or ``<param>!=<value>``, several joined by ``&`` when all
must hold.

``subtitle`` is the node's one-line summary (``{row} × {col}``), or a list of
them written as template fragments — ``{when: <condition>, text: ...}`` or a
plain string — of which the first that holds is used; the last plain one is
also what :meth:`NodeSpec.to_json` gives a builder as ``subtitle``, with the
list as ``subtitles``.

``checks`` are rules between parameters that :func:`~siamang.flow.check_flow`
reports on the node (``PARAM_CONFLICT``) — a post-hoc test that does not follow
the test chosen, a parameter the node would ignore::

    checks:
    - when: posthoc=tukey
      require: method=anova          # or a list: any one of them
      message: Tukey's HSD follows a one-way ANOVA — set Test to anova.
      severity: error                # or warning
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any

PORT_TYPES = ("SurveyData", "Table", "Chart", "Stat", "Report", "Any")
PARAM_KINDS = (
    "variable",
    "variables",
    "enum",
    "int",
    "float",
    "bool",
    "string",
    "condition",
    # Arithmetic over variables, written as text (siamang.data.formula). A kind
    # of its own rather than a plain string so check_flow can read it and name a
    # typo before a run rather than after one.
    "formula",
    "mapping",
    "targets",
    "path",
    "markdown",
    "captions",
    # How a report looks (siamang.reporting.ReportTheme) and how one item in it
    # is placed. Kinds of their own rather than `json` for the same reason
    # `formula` is one: check_flow reads them, so a misspelled field or an
    # impossible width is named on the canvas rather than raised in a sandbox.
    "theme",
    "layout",
    "json",
)
CATEGORIES = ("source", "prepare", "analyze", "visualize", "output")
SCALES = ("nominal", "ordinal", "interval", "ratio")


class RegistryError(ValueError):
    """A node specification that cannot be loaded."""


@dataclass(frozen=True, slots=True)
class PortSpec:
    name: str
    types: tuple[str, ...]
    many: bool = False
    optional: bool = False

    def accepts(self, port_type: str) -> bool:
        return "Any" in self.types or port_type in self.types

    def to_json(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "type": list(self.types) if len(self.types) > 1 else self.types[0]
        }
        if self.many:
            payload["many"] = True
        if self.optional:
            payload["optional"] = True
        return payload


@dataclass(frozen=True, slots=True)
class ParamSpec:
    name: str
    kind: str
    required: bool = False
    default: Any = None
    values: tuple[Any, ...] = ()
    scales: tuple[str, ...] = ()
    label: str | None = None
    help: str | None = None
    creates: str | None = None  # "variable" | "column": the value names something new
    minimum: float | None = None
    maximum: float | None = None
    #: A variable param's names beyond the codebook's variables that a picker
    #: should offer, with what to call them: ``(name, label)`` pairs (the
    #: Trend's Time offers the responses' timestamps).
    extra: tuple[tuple[str, str], ...] = ()

    def to_json(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"kind": self.kind}
        if self.required:
            payload["required"] = True
        if self.default is not None:
            payload["default"] = self.default
        if self.values:
            payload["values"] = list(self.values)
        if self.scales:
            payload["scales"] = list(self.scales)
        if self.label:
            payload["label"] = self.label
        if self.help:
            payload["help"] = self.help
        if self.creates:
            payload["creates"] = self.creates
        if self.minimum is not None:
            payload["minimum"] = self.minimum
        if self.maximum is not None:
            payload["maximum"] = self.maximum
        if self.extra:
            payload["extra"] = [{"name": name, "label": label} for name, label in self.extra]
        return payload


@dataclass(frozen=True, slots=True)
class Fragment:
    code: str
    when: str | None = None  # "<param>" or "<param>=<value>"


@dataclass(frozen=True, slots=True)
class Check:
    """A rule between a node's parameters: when ``when`` holds, one of
    ``require`` must hold too (with no ``require``, ``when`` alone is the
    problem). Conditions are written as a template's ``when``."""

    when: str
    require: tuple[str, ...] = ()
    message: str = ""
    severity: str = "error"  # error | warning

    def violated(self, params: dict[str, Any]) -> bool:
        if not condition_holds(self.when, params):
            return False
        return not any(condition_holds(option, params) for option in self.require)


@dataclass(frozen=True, slots=True)
class NodeSpec:
    type: str
    category: str
    title: str
    description: str
    inputs: dict[str, PortSpec]
    outputs: dict[str, str]
    params: dict[str, ParamSpec]
    template: tuple[Fragment, ...]
    preview: str | None = None
    subtitle: str | None = None
    #: Subtitles that hold for some parameters only (``text`` in ``code``); the
    #: first whose ``when`` holds wins, ``subtitle`` otherwise.
    subtitles: tuple[Fragment, ...] = ()
    imports: tuple[str, ...] = ()
    #: Runs only on a platform (needs the project database).
    platform: bool = False
    #: A data source a local snapshot can stand in for (``--data``).
    snapshot: bool = False
    tags: tuple[str, ...] = field(default_factory=tuple)
    #: Rules between the parameters, reported by ``check_flow``.
    checks: tuple[Check, ...] = ()

    @property
    def name(self) -> str:
        return self.type.split(".", 1)[1]

    def reads(self, name: str, params: dict[str, Any]) -> bool:
        """Whether the node's code reads parameter ``name`` with these values.

        A template written in fragments for some choices reads a parameter only
        under those choices: the t-test writes Groups into its code for the
        independent design, Second measurement for the paired one. A value the
        code never reads changes nothing, so :func:`~siamang.flow.check_flow`
        does not check it (a stale Group A of a paired t-test is not an error)
        and a builder need not ask for it.

        ``name`` is read when a fragment that names it — as ``{name!r}`` or in
        its ``when`` — holds for the node's *choices*: the terms of its ``when``
        of the form ``<param>=<value>`` or ``<param>!=<value>`` on an ``enum``
        or ``bool`` parameter other than ``name``. Whether another field is
        filled in (``group_a``) is not a choice: counting it would hide Group B
        until Group A was typed. A required parameter, and one that no fragment
        names, is always read. ``params`` are the resolved values
        (:func:`~siamang.flow.document.resolved_params`).
        """

        if name not in self.params or self.params[name].required:
            return True
        named = False
        for fragment in self.template:
            conditions = condition_params(fragment.when) if fragment.when else []
            if f"{{{name}!r}}" not in fragment.code and name not in conditions:
                continue
            named = True
            choices = [
                term
                for term in (fragment.when or "").split("&")
                if term.strip() and self._is_choice(term) and _term_param(term) != name
            ]
            if all(_term_holds(term.strip(), params) for term in choices):
                return True
        return not named

    def _is_choice(self, term: str) -> bool:
        """``<enum or bool>=<value>`` or ``!=``: a choice, not a field filled in."""
        if "=" not in term:
            return False
        param = self.params.get(_term_param(term))
        value = term.split("=", 1)[1].strip()
        return value != "None" and param is not None and param.kind in ("enum", "bool")

    def to_json(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "type": self.type,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "inputs": {name: port.to_json() for name, port in self.inputs.items()},
            "outputs": dict(self.outputs),
            "params": {name: param.to_json() for name, param in self.params.items()},
        }
        if self.preview:
            payload["preview"] = self.preview
        if self.subtitle:
            payload["subtitle"] = self.subtitle
        if self.subtitles:
            payload["subtitles"] = [
                {"when": item.when, "text": item.code} if item.when else {"text": item.code}
                for item in self.subtitles
            ]
        if self.platform:
            payload["platform"] = True
        if self.snapshot:
            payload["snapshot"] = True
        if self.tags:
            payload["tags"] = list(self.tags)
        return payload


class Registry:
    """All node specifications, keyed by type."""

    def __init__(self, specs: list[NodeSpec]) -> None:
        self._specs: dict[str, NodeSpec] = {}
        for spec in specs:
            if spec.type in self._specs:
                raise RegistryError(f"Duplicate node type {spec.type!r}.")
            self._specs[spec.type] = spec

    @classmethod
    def load(cls, root: str | Path | None = None) -> Registry:
        """Load every ``*.yaml`` under ``root`` (default: the bundled nodes)."""

        base = (
            Path(root) if root is not None else Path(str(resources.files("siamang.flow") / "nodes"))
        )
        files = sorted(base.rglob("*.yaml"))
        if not files:
            raise RegistryError(f"No node specifications found under {base}.")
        return cls([load_spec(path) for path in files])

    def __contains__(self, node_type: str) -> bool:
        return node_type in self._specs

    def __iter__(self):
        return iter(self._specs.values())

    def __len__(self) -> int:
        return len(self._specs)

    def get(self, node_type: str) -> NodeSpec:
        try:
            return self._specs[node_type]
        except KeyError as exc:
            raise RegistryError(f"Unknown node type {node_type!r}.") from exc

    def types(self) -> list[str]:
        return list(self._specs)

    def by_category(self) -> dict[str, list[NodeSpec]]:
        grouped: dict[str, list[NodeSpec]] = {category: [] for category in CATEGORIES}
        for spec in self._specs.values():
            grouped.setdefault(spec.category, []).append(spec)
        return grouped

    def to_json(self) -> list[dict[str, Any]]:
        """The registry as the frontend receives it (palette + inspector schema)."""

        return [spec.to_json() for spec in self._specs.values()]

    def dumps(self) -> str:
        return json.dumps(self.to_json(), indent=2, ensure_ascii=False) + "\n"


_default: Registry | None = None


def default_registry() -> Registry:
    """The bundled registry, loaded once."""

    global _default
    if _default is None:
        _default = Registry.load()
    return _default


# ─── loading ─────────────────────────────────────────────────────────────────


def load_spec(path: str | Path) -> NodeSpec:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise RegistryError("PyYAML is required to load node specifications.") from exc
    source = Path(path)
    try:
        payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise RegistryError(f"{source}: {exc}") from exc
    try:
        return spec_from_dict(payload)
    except (KeyError, TypeError, ValueError) as exc:
        raise RegistryError(f"{source}: {exc}") from exc


def spec_from_dict(payload: dict[str, Any]) -> NodeSpec:
    if not isinstance(payload, dict):
        raise RegistryError("node specification must be a mapping.")
    node_type = _require_str(payload, "type")
    category = _require_str(payload, "category")
    if category not in CATEGORIES:
        raise RegistryError(f"{node_type}: category must be one of {', '.join(CATEGORIES)}.")
    if not node_type.startswith(f"{category}."):
        raise RegistryError(f"{node_type}: type must start with its category '{category}.'.")

    inputs = {
        name: _port_from(name, value) for name, value in (payload.get("inputs") or {}).items()
    }
    outputs: dict[str, str] = {}
    for name, value in (payload.get("outputs") or {}).items():
        if value not in PORT_TYPES or value == "Any":
            raise RegistryError(f"{node_type}: output '{name}' has unknown type {value!r}.")
        outputs[name] = value
    params = {
        name: _param_from(node_type, name, value)
        for name, value in (payload.get("params") or {}).items()
    }
    template = _template_from(node_type, payload.get("template"), params)
    subtitle, subtitles = _subtitles_from(node_type, payload.get("subtitle"), params)
    preview = payload.get("preview")
    if preview is not None and preview not in {"table", "chart", "stat", "text", "rows", "report"}:
        raise RegistryError(f"{node_type}: unknown preview {preview!r}.")
    imports = tuple(payload.get("imports") or ())
    for statement in imports:
        if not isinstance(statement, str) or not statement.startswith(("import ", "from ")):
            raise RegistryError(
                f"{node_type}: imports must be import statements, got {statement!r}."
            )
    return NodeSpec(
        type=node_type,
        category=category,
        title=_require_str(payload, "title"),
        description=str(payload.get("description") or ""),
        inputs=inputs,
        outputs=outputs,
        params=params,
        template=template,
        preview=preview,
        subtitle=subtitle,
        subtitles=subtitles,
        imports=imports,
        platform=bool(payload.get("platform", False)),
        snapshot=bool(payload.get("snapshot", False)),
        tags=tuple(payload.get("tags") or ()),
        checks=_checks_from(node_type, payload.get("checks"), params),
    )


def _require_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RegistryError(f"'{key}' is required and must be a non-empty string.")
    return value


def _port_from(name: str, value: Any) -> PortSpec:
    if isinstance(value, str):
        types: tuple[str, ...] = (value,)
        many = optional = False
    elif isinstance(value, dict):
        raw = value.get("type")
        types = tuple(raw) if isinstance(raw, list) else (raw,)
        many = bool(value.get("many", False))
        optional = bool(value.get("optional", False))
    else:
        raise RegistryError(f"input '{name}' must be a type name or a mapping.")
    for port_type in types:
        if port_type not in PORT_TYPES:
            raise RegistryError(f"input '{name}' has unknown type {port_type!r}.")
    return PortSpec(name=name, types=types, many=many, optional=optional)


def _param_from(node_type: str, name: str, value: Any) -> ParamSpec:
    if not isinstance(value, dict):
        raise RegistryError(f"{node_type}: param '{name}' must be a mapping.")
    kind = value.get("kind")
    if kind not in PARAM_KINDS:
        raise RegistryError(f"{node_type}: param '{name}' has unknown kind {kind!r}.")
    values = tuple(value.get("values") or ())
    if kind == "enum" and not values:
        raise RegistryError(f"{node_type}: enum param '{name}' needs 'values'.")
    scales = tuple(value.get("scales") or ())
    for scale in scales:
        if scale not in SCALES:
            raise RegistryError(f"{node_type}: param '{name}' has unknown scale {scale!r}.")
    default = value.get("default")
    if kind == "enum" and default is not None and default not in values:
        raise RegistryError(f"{node_type}: param '{name}' default {default!r} not in values.")
    creates = value.get("creates")
    if creates not in (None, "variable", "column"):
        raise RegistryError(f"{node_type}: param '{name}' creates must be variable or column.")
    extra = value.get("extra") or {}
    if extra and (
        kind != "variable"
        or not isinstance(extra, dict)
        or not all(isinstance(key, str) and isinstance(text, str) for key, text in extra.items())
    ):
        raise RegistryError(
            f"{node_type}: param '{name}' extra must map names to labels, on a variable param."
        )
    return ParamSpec(
        name=name,
        kind=kind,
        required=bool(value.get("required", False)),
        default=default,
        values=values,
        scales=scales,
        label=value.get("label"),
        help=value.get("help"),
        creates=creates,
        minimum=value.get("minimum"),
        maximum=value.get("maximum"),
        extra=tuple(extra.items()),
    )


def _template_from(node_type: str, raw: Any, params: dict[str, ParamSpec]) -> tuple[Fragment, ...]:
    if raw is None:
        raise RegistryError(f"{node_type}: 'template' is required.")
    fragments: list[Fragment] = []
    items = raw if isinstance(raw, list) else [raw]
    for item in items:
        if isinstance(item, str):
            fragments.append(Fragment(code=item.rstrip("\n")))
        elif isinstance(item, dict) and isinstance(item.get("code"), str):
            when = item.get("when")
            if when is not None:
                for param in condition_params(str(when)):
                    if param not in params:
                        raise RegistryError(
                            f"{node_type}: template 'when' names unknown param {param!r}."
                        )
            fragments.append(Fragment(code=item["code"].rstrip("\n"), when=when))
        else:
            raise RegistryError(
                f"{node_type}: template fragments must be strings or {{when, code}}."
            )
    if not fragments:
        raise RegistryError(f"{node_type}: 'template' must not be empty.")
    return tuple(fragments)


# ─── conditions ──────────────────────────────────────────────────────────────


def condition_holds(condition: str, params: dict[str, Any]) -> bool:
    """Whether a ``when`` condition holds for these parameter values.

    ``<param>`` holds when the value is set — not None, empty or false (a code
    of 0 is set); ``<param>=<value>`` / ``<param>!=<value>`` compare the value's
    text; terms joined by ``&`` must all hold.
    """

    return all(_term_holds(term.strip(), params) for term in condition.split("&"))


def _term_holds(term: str, params: dict[str, Any]) -> bool:
    if "!=" in term:
        name, expected = term.split("!=", 1)
        return str(params.get(name.strip())) != expected.strip()
    if "=" in term:
        name, expected = term.split("=", 1)
        return str(params.get(name.strip())) == expected.strip()
    value = params.get(term)
    return value is not None and value is not False and value not in ("", [], {})


def condition_params(condition: str) -> list[str]:
    """The parameters a condition reads."""

    return [_term_param(term) for term in condition.split("&")]


def _term_param(term: str) -> str:
    return (term.split("!=", 1)[0] if "!=" in term else term.split("=", 1)[0]).strip()


def _subtitles_from(
    node_type: str, raw: Any, params: dict[str, ParamSpec]
) -> tuple[str | None, tuple[Fragment, ...]]:
    """A subtitle, or a list of ``{when, text}`` / strings: the plain one is the
    default, the list is kept in order."""

    if raw is None or isinstance(raw, str):
        return raw, ()
    if not isinstance(raw, list):
        raise RegistryError(f"{node_type}: 'subtitle' must be a string or a list.")
    variants: list[Fragment] = []
    default: str | None = None
    for item in raw:
        if isinstance(item, str):
            variants.append(Fragment(code=item))
            default = item
        elif isinstance(item, dict) and isinstance(item.get("text"), str) and item.get("when"):
            for param in condition_params(str(item["when"])):
                if param not in params:
                    raise RegistryError(
                        f"{node_type}: subtitle 'when' names unknown param {param!r}."
                    )
            variants.append(Fragment(code=item["text"], when=str(item["when"])))
        else:
            raise RegistryError(f"{node_type}: subtitles must be strings or {{when, text}}.")
    return default, tuple(variants)


def _checks_from(node_type: str, raw: Any, params: dict[str, ParamSpec]) -> tuple[Check, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise RegistryError(f"{node_type}: 'checks' must be a list.")
    checks: list[Check] = []
    for item in raw:
        if not isinstance(item, dict) or not isinstance(item.get("when"), str):
            raise RegistryError(f"{node_type}: a check needs 'when'.")
        require = item.get("require") or ()
        require = (require,) if isinstance(require, str) else tuple(str(r) for r in require)
        message = item.get("message")
        if not isinstance(message, str) or not message.strip():
            raise RegistryError(f"{node_type}: a check needs a 'message'.")
        severity = item.get("severity", "error")
        if severity not in ("error", "warning"):
            raise RegistryError(f"{node_type}: check severity must be error or warning.")
        for condition in (item["when"], *require):
            for param in condition_params(condition):
                if param not in params:
                    raise RegistryError(f"{node_type}: check names unknown param {param!r}.")
        checks.append(Check(item["when"], require, message.strip(), severity))
    return tuple(checks)


__all__ = [
    "CATEGORIES",
    "PARAM_KINDS",
    "PORT_TYPES",
    "SCALES",
    "Check",
    "Fragment",
    "NodeSpec",
    "ParamSpec",
    "PortSpec",
    "Registry",
    "RegistryError",
    "condition_holds",
    "default_registry",
    "load_spec",
    "spec_from_dict",
]
