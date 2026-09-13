"""Flow documents: the graph a builder stores, and everything that checks it.

A flow (``schema_version`` 1.0)::

    schema_version  "1.0"
    name            slug (the file name, the script name)
    title, description
    nodes           [{id, type, params, position: [x, y], label?}]
    edges           [{from: {node, port}, to: {node, port}}]
    outputs         {report?: path, files?: [path]}
    live            {enabled, debounce_seconds, tiles: [{node, w, h}]}
    schedule?       cron string

:func:`validate_flow` checks the JSON Schema; :func:`check_flow` then checks
the graph against the node registry (types, ports, parameters, cycles) and,
when given, against the questionnaire's codebook (variables and scales).
:func:`node_order` is the execution order both the runner and the code
generator use.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import cache
from importlib import resources
from typing import Any

from siamang.flow.registry import NodeSpec, ParamSpec, Registry, default_registry

FLOW_SCHEMA_VERSION = "1.0"
_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class FlowError(ValueError):
    """A flow document that cannot be used."""


@dataclass(frozen=True, slots=True)
class FlowIssue:
    severity: str  # error | warning
    code: str
    message: str
    node: str | None = None


@dataclass(frozen=True, slots=True)
class Edge:
    source: str
    source_port: str
    target: str
    target_port: str


@dataclass(slots=True)
class FlowGraph:
    """The document resolved against the registry: what the runner and generator walk."""

    document: dict[str, Any]
    registry: Registry
    nodes: dict[str, dict[str, Any]]
    specs: dict[str, NodeSpec]
    edges: list[Edge]
    order: list[str]
    #: ``inputs[node][port]`` -> upstream ``(node, port)`` pairs, in edge order.
    inputs: dict[str, dict[str, list[tuple[str, str]]]] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return self.document["name"]

    def params(self, node_id: str) -> dict[str, Any]:
        """Parameters of a node with the registry defaults filled in."""

        spec = self.specs[node_id]
        given = self.nodes[node_id].get("params") or {}
        resolved: dict[str, Any] = {}
        for name, param in spec.params.items():
            resolved[name] = given.get(name, param.default)
        return resolved

    def upstream(self, node_id: str) -> list[str]:
        seen: list[str] = []
        for sources in self.inputs.get(node_id, {}).values():
            for source, _port in sources:
                if source not in seen:
                    seen.append(source)
        return seen


# ─── JSON Schema ─────────────────────────────────────────────────────────────


@cache
def load_flow_schema(version: str = FLOW_SCHEMA_VERSION) -> dict[str, Any]:
    if version != FLOW_SCHEMA_VERSION:
        raise FlowError(f"No schema for flow version {version!r}.")
    path = resources.files("siamang.schemas").joinpath(f"flow-{version}.json")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_flow(document: Any) -> None:
    """Check ``document`` against the flow JSON Schema; raise :class:`FlowError`."""

    import jsonschema

    if not isinstance(document, dict):
        raise FlowError(f"Flow must be an object, got {type(document).__name__}.")
    version = document.get("schema_version")
    if version != FLOW_SCHEMA_VERSION:
        raise FlowError(
            f"Unsupported schema_version {version!r}; this engine reads {FLOW_SCHEMA_VERSION}."
        )
    validator = jsonschema.Draft202012Validator(load_flow_schema(version))
    errors = sorted(validator.iter_errors(document), key=lambda error: list(error.absolute_path))
    if errors:
        error = jsonschema.exceptions.best_match(errors)
        location = "/".join(str(part) for part in error.absolute_path) or "flow"
        raise FlowError(f"{location}: {error.message}")


# ─── Graph checks ────────────────────────────────────────────────────────────


def check_flow(
    document: dict[str, Any],
    *,
    registry: Registry | None = None,
    questionnaire: dict[str, Any] | None = None,
) -> list[FlowIssue]:
    """Every problem of the graph: unknown nodes, bad params, wrong edges, cycles.

    ``questionnaire`` is the questionnaire *document* (``siamang.model``); with
    it, variable parameters are checked against the codebook and its scales.
    Errors make the flow unusable; warnings are worth showing. Returns the
    list — :func:`resolve_flow` raises on the first error instead.
    """

    validate_flow(document)
    registry = registry or default_registry()
    issues: list[FlowIssue] = []
    nodes: dict[str, dict[str, Any]] = {}
    for node in document.get("nodes") or []:
        node_id = node["id"]
        if node_id in nodes:
            issues.append(
                FlowIssue("error", "DUPLICATE_NODE", f"Node id {node_id!r} is used twice.", node_id)
            )
            continue
        nodes[node_id] = node
        if node["type"] not in registry:
            issues.append(
                FlowIssue(
                    "error", "UNKNOWN_NODE_TYPE", f"Unknown node type {node['type']!r}.", node_id
                )
            )

    known_variables = _known_variables(document, nodes, registry, questionnaire)
    scales = {
        name: payload.get("scale")
        for name, payload in ((questionnaire or {}).get("variables") or {}).items()
    }
    for node_id, node in nodes.items():
        if node["type"] not in registry:
            continue
        spec = registry.get(node["type"])
        issues.extend(
            _check_params(node_id, spec, node.get("params") or {}, known_variables, scales)
        )

    edges: list[Edge] = []
    seen_single: set[tuple[str, str]] = set()
    for index, raw in enumerate(document.get("edges") or []):
        edge = Edge(raw["from"]["node"], raw["from"]["port"], raw["to"]["node"], raw["to"]["port"])
        where = f"edges[{index}]"
        source, target = nodes.get(edge.source), nodes.get(edge.target)
        if source is None or target is None:
            missing = edge.source if source is None else edge.target
            issues.append(
                FlowIssue(
                    "error", "UNKNOWN_EDGE_NODE", f"{where}: unknown node {missing!r}.", missing
                )
            )
            continue
        if source["type"] not in registry or target["type"] not in registry:
            continue
        source_spec, target_spec = registry.get(source["type"]), registry.get(target["type"])
        if edge.source_port not in source_spec.outputs:
            issues.append(
                FlowIssue(
                    "error",
                    "UNKNOWN_PORT",
                    f"{where}: {source_spec.type} has no output {edge.source_port!r}.",
                    edge.source,
                )
            )
            continue
        port = target_spec.inputs.get(edge.target_port)
        if port is None:
            issues.append(
                FlowIssue(
                    "error",
                    "UNKNOWN_PORT",
                    f"{where}: {target_spec.type} has no input {edge.target_port!r}.",
                    edge.target,
                )
            )
            continue
        produced = source_spec.outputs[edge.source_port]
        if not port.accepts(produced):
            issues.append(
                FlowIssue(
                    "error",
                    "PORT_TYPE_MISMATCH",
                    f"{where}: {edge.source}.{edge.source_port} is {produced}, but "
                    f"{edge.target}.{edge.target_port} takes {' | '.join(port.types)}.",
                    edge.target,
                )
            )
            continue
        if not port.many:
            key = (edge.target, edge.target_port)
            if key in seen_single:
                issues.append(
                    FlowIssue(
                        "error",
                        "INPUT_CONNECTED_TWICE",
                        f"{edge.target}.{edge.target_port} has more than one incoming edge.",
                        edge.target,
                    )
                )
                continue
            seen_single.add(key)
        edges.append(edge)

    connected = {(edge.target, edge.target_port) for edge in edges}
    for node_id, node in nodes.items():
        if node["type"] not in registry:
            continue
        for name, port in registry.get(node["type"]).inputs.items():
            if not port.optional and (node_id, name) not in connected:
                issues.append(
                    FlowIssue(
                        "error",
                        "INPUT_NOT_CONNECTED",
                        f"Input {name!r} of {node_id} is not connected.",
                        node_id,
                    )
                )

    if not any(issue.severity == "error" for issue in issues):
        try:
            order = node_order(nodes, edges)
        except FlowError as exc:
            issues.append(FlowIssue("error", "CYCLE", str(exc)))
        else:
            reachable = _reachable(nodes, edges, registry)
            for node_id in order:
                if node_id not in reachable:
                    issues.append(
                        FlowIssue(
                            "warning",
                            "UNREACHABLE_NODE",
                            f"Node {node_id} is not fed by any source.",
                            node_id,
                        )
                    )

    for tile in (document.get("live") or {}).get("tiles") or []:
        if tile["node"] not in nodes:
            issues.append(
                FlowIssue(
                    "error",
                    "UNKNOWN_TILE_NODE",
                    f"live.tiles names unknown node {tile['node']!r}.",
                    tile["node"],
                )
            )
        elif nodes[tile["node"]]["type"] != "output.live_tile":
            issues.append(
                FlowIssue(
                    "warning",
                    "TILE_NOT_LIVE_TILE",
                    f"live.tiles names {tile['node']}, which is not an output.live_tile.",
                    tile["node"],
                )
            )
    return issues


def resolve_flow(
    document: dict[str, Any],
    *,
    registry: Registry | None = None,
    questionnaire: dict[str, Any] | None = None,
) -> FlowGraph:
    """Check the flow and return the resolved graph; raise :class:`FlowError` on errors."""

    registry = registry or default_registry()
    issues = check_flow(document, registry=registry, questionnaire=questionnaire)
    errors = [issue for issue in issues if issue.severity == "error"]
    if errors:
        first = errors[0]
        more = f" (+{len(errors) - 1} more)" if len(errors) > 1 else ""
        raise FlowError(f"{first.message}{more}")
    nodes = {node["id"]: node for node in document.get("nodes") or []}
    edges = [
        Edge(raw["from"]["node"], raw["from"]["port"], raw["to"]["node"], raw["to"]["port"])
        for raw in document.get("edges") or []
    ]
    inputs: dict[str, dict[str, list[tuple[str, str]]]] = {node_id: {} for node_id in nodes}
    for edge in edges:
        inputs[edge.target].setdefault(edge.target_port, []).append((edge.source, edge.source_port))
    return FlowGraph(
        document=document,
        registry=registry,
        nodes=nodes,
        specs={node_id: registry.get(node["type"]) for node_id, node in nodes.items()},
        edges=edges,
        order=node_order(nodes, edges),
        inputs=inputs,
    )


def node_order(nodes: dict[str, dict[str, Any]], edges: list[Edge]) -> list[str]:
    """Execution order: by depth from the sources, then position y, x, then id."""

    incoming: dict[str, set[str]] = {node_id: set() for node_id in nodes}
    outgoing: dict[str, set[str]] = {node_id: set() for node_id in nodes}
    for edge in edges:
        incoming[edge.target].add(edge.source)
        outgoing[edge.source].add(edge.target)

    depth: dict[str, int] = {}
    remaining = dict(incoming)
    ready = sorted(node_id for node_id, sources in remaining.items() if not sources)
    for node_id in ready:
        depth[node_id] = 0
    while ready:
        node_id = ready.pop(0)
        for target in sorted(outgoing[node_id]):
            remaining[target] = remaining[target] - {node_id}
            depth[target] = max(depth.get(target, 0), depth[node_id] + 1)
            if not remaining[target] and target not in ready:
                ready.append(target)
    if len(depth) != len(nodes):
        stuck = sorted(set(nodes) - set(depth))
        raise FlowError(f"The flow has a cycle through {', '.join(stuck)}.")

    def key(node_id: str) -> tuple[int, float, float, str]:
        position = nodes[node_id].get("position") or [0, 0]
        return (depth[node_id], float(position[1]), float(position[0]), node_id)

    return sorted(nodes, key=key)


# ─── helpers ─────────────────────────────────────────────────────────────────


def _known_variables(
    document: dict[str, Any],
    nodes: dict[str, dict[str, Any]],
    registry: Registry,
    questionnaire: dict[str, Any] | None,
) -> set[str] | None:
    """Variables a node may name, or ``None`` when there is no codebook to check against."""

    if questionnaire is None:
        return None
    known = set((questionnaire.get("variables") or {}).keys())
    for node in nodes.values():
        if node["type"] not in registry:
            continue
        spec = registry.get(node["type"])
        params = node.get("params") or {}
        for name, param in spec.params.items():
            if param.creates and isinstance(params.get(name), str) and params[name]:
                known.add(params[name])
            if param.creates and isinstance(param.default, str) and param.default:
                known.add(param.default)
        if spec.type == "prepare.recode" and params.get("variable") and not params.get("into"):
            known.add(f"{params['variable']}_recoded")
        if spec.type == "prepare.speeders":
            known.update({"duration_s", "partial"})
        if spec.type == "prepare.explode" and params.get("variable"):
            known.update(_exploded_names(questionnaire, params))
    return known


def _exploded_names(questionnaire: dict[str, Any], params: dict[str, Any]) -> set[str]:
    """The indicator columns ``prepare.explode`` will create, by codebook order.

    Named here rather than declared with ``creates`` because the node invents one
    column per option instead of one per parameter, and a later node that cannot
    name them is a node that cannot use them.
    """

    variable = params["variable"]
    payload = (questionnaire.get("variables") or {}).get(variable) or {}
    prefix = params.get("prefix") or f"{variable}_"
    return {f"{prefix}{item.get('code')}" for item in payload.get("labels") or []}


def _check_params(
    node_id: str,
    spec: NodeSpec,
    params: dict[str, Any],
    known: set[str] | None,
    scales: dict[str, str | None],
) -> list[FlowIssue]:
    issues: list[FlowIssue] = []
    for name in params:
        if name not in spec.params:
            issues.append(
                FlowIssue(
                    "error", "UNKNOWN_PARAM", f"{spec.type} has no parameter {name!r}.", node_id
                )
            )
    for name, param in spec.params.items():
        value = params.get(name, param.default)
        # An empty mapping means "not set", exactly as an empty list does. Without
        # {} here an optional `mapping` param could never be left alone: its empty
        # default reached _param_problem and came back "expected a non-empty
        # code → value object", while a required one reported the wrong code.
        if value is None or value == "" or value == [] or value == {}:
            if param.required:
                issues.append(
                    FlowIssue(
                        "error",
                        "PARAM_REQUIRED",
                        f"Parameter {name!r} of {node_id} is required.",
                        node_id,
                    )
                )
            continue
        problem = _param_problem(param, value)
        if problem:
            issues.append(
                FlowIssue(
                    "error", "PARAM_INVALID", f"Parameter {name!r} of {node_id}: {problem}", node_id
                )
            )
            continue
        if known is not None and param.kind in {"variable", "variables"} and not param.creates:
            names = value if isinstance(value, list) else [value]
            for variable in names:
                if variable not in known:
                    issues.append(
                        FlowIssue(
                            "error",
                            "UNKNOWN_VARIABLE",
                            f"Parameter {name!r} of {node_id} names unknown variable {variable!r}.",
                            node_id,
                        )
                    )
                elif param.scales and variable in scales and scales[variable] not in param.scales:
                    issues.append(
                        FlowIssue(
                            "error",
                            "VARIABLE_SCALE",
                            f"Parameter {name!r} of {node_id}: {variable!r} is {scales[variable]}, "
                            f"expected {' | '.join(param.scales)}.",
                            node_id,
                        )
                    )
        if known is not None and param.kind == "targets":
            for variable in value:
                if variable not in known:
                    issues.append(
                        FlowIssue(
                            "error",
                            "UNKNOWN_VARIABLE",
                            f"Parameter {name!r} of {node_id} names unknown variable {variable!r}.",
                            node_id,
                        )
                    )
        if param.kind == "condition":
            for variable in sorted(_condition_variables(value)):
                if known is not None and variable not in known:
                    issues.append(
                        FlowIssue(
                            "error",
                            "UNKNOWN_VARIABLE",
                            f"Condition of {node_id} names unknown variable {variable!r}.",
                            node_id,
                        )
                    )
    return issues


def _param_problem(param: ParamSpec, value: Any) -> str | None:
    kind = param.kind
    if kind in {"string", "path", "markdown", "variable"}:
        if not isinstance(value, str):
            return f"expected a string, got {type(value).__name__}."
    elif kind == "variables":
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            return "expected a list of variable names."
    elif kind == "enum":
        if value not in param.values:
            return f"{value!r} is not one of {', '.join(map(str, param.values))}."
    elif kind == "int":
        if isinstance(value, bool) or not isinstance(value, int):
            return f"expected an integer, got {value!r}."
    elif kind == "float":
        if isinstance(value, bool) or not isinstance(value, int | float):
            return f"expected a number, got {value!r}."
    elif kind == "bool":
        if not isinstance(value, bool):
            return f"expected true or false, got {value!r}."
    elif kind == "condition":
        if not isinstance(value, dict) or value.get("type") not in {"expression", "var"}:
            return "expected an expression (raw string conditions cannot be evaluated on data)."
        if _has_raw(value):
            return "raw string conditions cannot be evaluated on data."
    elif kind == "mapping":
        if not isinstance(value, dict) or not value:
            return "expected a non-empty code → value object."
    elif kind == "targets":
        if (
            not isinstance(value, dict)
            or not value
            or not all(isinstance(margin, dict) and margin for margin in value.values())
        ):
            return "expected variable → {code: share} objects."
    elif kind == "captions" and (
        not isinstance(value, dict) or not all(isinstance(item, str) for item in value.values())
    ):
        return "expected node id → caption strings."
    if kind in {"int", "float"} and not isinstance(value, bool) and isinstance(value, int | float):
        if param.minimum is not None and value < param.minimum:
            return f"must be at least {param.minimum}."
        if param.maximum is not None and value > param.maximum:
            return f"must be at most {param.maximum}."
    return None


def _has_raw(node: Any) -> bool:
    if isinstance(node, dict):
        if node.get("type") == "raw" or (
            node.get("type") == "expression" and node.get("op") == "raw"
        ):
            return True
        return _has_raw(node.get("left")) or _has_raw(node.get("right"))
    if isinstance(node, list):
        return any(_has_raw(item) for item in node)
    return False


def _condition_variables(node: Any) -> set[str]:
    if isinstance(node, dict):
        if node.get("type") == "var":
            return {node["name"]}
        return _condition_variables(node.get("left")) | _condition_variables(node.get("right"))
    if isinstance(node, list):
        names: set[str] = set()
        for item in node:
            names |= _condition_variables(item)
        return names
    return set()


def _reachable(nodes: dict[str, dict[str, Any]], edges: list[Edge], registry: Registry) -> set[str]:
    reached = {
        node_id
        for node_id, node in nodes.items()
        if registry.get(node["type"]).category == "source"
    }
    changed = True
    while changed:
        changed = False
        for edge in edges:
            if edge.source in reached and edge.target not in reached:
                reached.add(edge.target)
                changed = True
    return reached


def dumps(document: dict[str, Any]) -> str:
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def loads(text: str) -> dict[str, Any]:
    document = json.loads(text)
    if not isinstance(document, dict):
        raise FlowError("Flow must be a JSON object.")
    return document


__all__ = [
    "FLOW_SCHEMA_VERSION",
    "Edge",
    "FlowError",
    "FlowGraph",
    "FlowIssue",
    "check_flow",
    "dumps",
    "load_flow_schema",
    "loads",
    "node_order",
    "resolve_flow",
    "validate_flow",
]
