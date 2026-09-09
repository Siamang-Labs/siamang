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
``{when: <param> | <param>=<value>, code: ...}`` — the fragment is written
only when the parameter is truthy / equal to the value.
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
    "mapping",
    "targets",
    "path",
    "markdown",
    "captions",
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
        return payload


@dataclass(frozen=True, slots=True)
class Fragment:
    code: str
    when: str | None = None  # "<param>" or "<param>=<value>"


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
    imports: tuple[str, ...] = ()
    #: Runs only on a platform (needs the project database).
    platform: bool = False
    #: A data source a local snapshot can stand in for (``--data``).
    snapshot: bool = False
    tags: tuple[str, ...] = field(default_factory=tuple)

    @property
    def name(self) -> str:
        return self.type.split(".", 1)[1]

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
        subtitle=payload.get("subtitle"),
        imports=imports,
        platform=bool(payload.get("platform", False)),
        snapshot=bool(payload.get("snapshot", False)),
        tags=tuple(payload.get("tags") or ()),
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
                param = str(when).split("=", 1)[0]
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


__all__ = [
    "CATEGORIES",
    "PARAM_KINDS",
    "PORT_TYPES",
    "SCALES",
    "Fragment",
    "NodeSpec",
    "ParamSpec",
    "PortSpec",
    "Registry",
    "RegistryError",
    "default_registry",
    "load_spec",
    "spec_from_dict",
]
