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
from contextlib import suppress
from dataclasses import dataclass, field
from functools import cache
from importlib import resources
from typing import Any

from siamang.data.checks import RESPONSE_TIME_LABELS
from siamang.flow.registry import (
    NodeSpec,
    ParamSpec,
    Registry,
    condition_params,
    default_registry,
)

FLOW_SCHEMA_VERSION = "1.0"
_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
#: The response timestamps a platform's frame carries beside the answers (the
#: responses table's created_at and updated_at, the runtime's started_at) and
#: a frame's submitted_at. No codebook declares them, yet a node may name one:
#: a Trend over dates reads one as its Time.
RESPONSE_TIMES = tuple(RESPONSE_TIME_LABELS)


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
        """Parameters of a node with the registry defaults filled in.

        A parameter stored as null, "", [] or {} is not set and takes its
        default, as :func:`check_flow` reads it — so the code that runs is the
        code the check approved.
        """

        return resolved_params(self.specs[node_id], self.nodes[node_id].get("params") or {})

    def upstream(self, node_id: str) -> list[str]:
        seen: list[str] = []
        for sources in self.inputs.get(node_id, {}).values():
            for source, _port in sources:
                if source not in seen:
                    seen.append(source)
        return seen

    def read_after(self, node_id: str) -> set[str]:
        """The variables ``node_id`` makes that a node downstream of it reads.

        What a template passes as ``{read_after!r}``: Factor analysis makes the
        score of a factor its rule did not keep only when a later node names it
        (:func:`~siamang.data.factor.analyze`'s ``read_later``).
        """

        children: dict[str, set[str]] = {}
        for edge in self.edges:
            children.setdefault(edge.source, set()).add(edge.target)
        below: set[str] = set()
        stack = list(children.get(node_id, ()))
        while stack:
            other = stack.pop()
            if other not in below:
                below.add(other)
                stack.extend(children.get(other, ()))
        read: set[str] = set()
        for other in below:
            read |= variables_read(self.specs[other], self.params(other))
        return read & _made_names(self.specs[node_id], self.params(node_id))


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
    for name in _assigned_variables(questionnaire):
        # An arm the codebook leaves out is nominal, as Simulated data enters it.
        scales.setdefault(name, "nominal")
    # The scales the nodes upstream of each node give what they make (the
    # codebook's entry wins a shared name). A node naming one of the wrong scale
    # is warned, not stopped: a flow saved before this was checked may rely on
    # it and runs.
    made_at = (
        _made_scales(document, nodes, registry, questionnaire, scales)
        if questionnaire is not None
        else {}
    )
    for node_id, node in nodes.items():
        if node["type"] not in registry:
            continue
        spec = registry.get(node["type"])
        made = {
            name: scale for name, scale in made_at.get(node_id, {}).items() if name not in scales
        }
        issues.extend(
            _check_params(node_id, spec, node.get("params") or {}, known_variables, scales, made)
        )
        issues.extend(_check_rules(node_id, spec, node.get("params") or {}))
        issues.extend(_check_design(node_id, spec, node.get("params") or {}, questionnaire))
        if spec.type == "analyze.regression":
            issues.extend(
                _check_ordinal_outcome(
                    node_id, spec, node.get("params") or {}, questionnaire, scales, made
                )
            )
        if spec.type == "prepare.maxdiff_scores" and questionnaire is not None:
            issues.extend(_check_maxdiff_question(node_id, node.get("params") or {}, questionnaire))
        if spec.type == "visualize.likert" and questionnaire is not None:
            issues.extend(_check_likert_scale(node_id, node.get("params") or {}, questionnaire))
        if spec.type == "visualize.bar" and questionnaire is not None:
            issues.extend(
                _check_bar_answers(node_id, spec, node.get("params") or {}, questionnaire)
            )
        if spec.type == "visualize.trend" and questionnaire is not None:
            issues.extend(_check_trend(node_id, spec, node.get("params") or {}, questionnaire))
        if spec.type == "output.tabbook":
            issues.extend(_check_tabbook(node_id, spec, node.get("params") or {}, questionnaire))

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
    issues.extend(_check_result_charts(nodes, edges, registry))

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
    known.update(_assigned_variables(questionnaire))
    known.update(RESPONSE_TIMES)
    for node in nodes.values():
        if node["type"] not in registry:
            continue
        spec = registry.get(node["type"])
        params = node.get("params") or {}
        known.update(_made_names(spec, params))
        if spec.type == "prepare.explode" and params.get("variable"):
            known.update(_exploded_names(questionnaire, params))
        if spec.type == "prepare.maxdiff_scores" and isinstance(params.get("question"), str):
            known.update(_maxdiff_score_names(questionnaire, params))
    return known


def _made_names(spec: NodeSpec, params: dict[str, Any]) -> set[str]:
    """The names a node may make that need no codebook to tell: every
    ``creates`` parameter's value and its default, a Recode's
    ``<variable>_recoded``, the speeders' timing and flag, and factor scores."""

    made: set[str] = set()
    for name, param in spec.params.items():
        if param.creates and isinstance(params.get(name), str) and params[name]:
            made.add(params[name])
        if param.creates and isinstance(param.default, str) and param.default:
            made.add(param.default)
    if spec.type == "prepare.recode" and params.get("variable") and not params.get("into"):
        made.add(f"{params['variable']}_recoded")
    if spec.type == "prepare.speeders":
        made.update({"duration_s", "partial"})
    if spec.type == "analyze.factor" and params.get("scores"):
        made.update(_factor_score_names(spec, params))
    return made


def variables_read(spec: NodeSpec, params: dict[str, Any]) -> set[str]:
    """The variables a node's parameters name: a variable or variables
    parameter (not one that ``creates``), the names in a formula or a
    condition, a targets mapping's variables."""

    from siamang.data.formula import FormulaError, parse

    names: set[str] = set()
    for name, param in spec.params.items():
        value = params.get(name)
        if unset(value) or param.creates:
            continue
        if param.kind == "variable" and isinstance(value, str):
            names.add(value)
        elif param.kind == "variables" and isinstance(value, list):
            names.update(item for item in value if isinstance(item, str))
        elif param.kind == "formula" and isinstance(value, str):
            with suppress(FormulaError):  # a formula that does not parse is reported
                names.update(parse(value).variables())
        elif param.kind == "condition":
            names |= _condition_variables(value)
        elif param.kind == "targets" and isinstance(value, dict):
            names.update(str(key) for key in value)
    return names


def _made_scales(
    document: dict[str, Any],
    nodes: dict[str, dict[str, Any]],
    registry: Registry,
    questionnaire: dict[str, Any] | None,
    codebook: dict[str, str | None],
) -> dict[str, dict[str, str]]:
    """For each node, the scale of every variable the nodes upstream of it make
    — as the engine registers it: Derive its Scale (ratio by default), Recode
    its Scale or the source's, an index interval, Bands ordinal, a cluster,
    themes and quality flags nominal, the quality score ratio, Explode's columns
    nominal, factor and MaxDiff scores interval. Columns made without a variable
    (weights, the speeders' timing) have no scale to check.

    Walked along the edges, in the order the flow runs: a Recode takes the
    scale its source has where the Recode reads it — a Derive listed after it in
    the document is still upstream — and a name made twice has the scale of the
    maker nearest upstream of the node reading it, as it does at run time. With
    two inputs, the one that runs later wins a name both bring."""

    parents: dict[str, list[str]] = {node_id: [] for node_id in nodes}
    edges: list[Edge] = []
    for raw in document.get("edges") or []:
        source, target = raw["from"]["node"], raw["to"]["node"]
        if source in nodes and target in nodes:
            parents[target].append(source)
            edges.append(Edge(source, raw["from"]["port"], target, raw["to"]["port"]))
    try:
        order = node_order(nodes, edges)
    except FlowError:
        order = list(nodes)  # a cycle is an error of its own; walk as listed
    rank = {node_id: index for index, node_id in enumerate(order)}

    upstream: dict[str, dict[str, str]] = {}
    leaving: dict[str, dict[str, str]] = {}
    for node_id in order:
        inherited: dict[str, str] = {}
        for parent in sorted(set(parents[node_id]), key=rank.__getitem__):
            inherited.update(leaving.get(parent, {}))
        upstream[node_id] = inherited
        node = nodes[node_id]
        own = (
            _scales_made(node, registry.get(node["type"]), questionnaire, codebook, inherited)
            if node["type"] in registry
            else {}
        )
        leaving[node_id] = {**inherited, **own}
    return upstream


def _scales_made(
    node: dict[str, Any],
    spec: NodeSpec,
    questionnaire: dict[str, Any] | None,
    codebook: dict[str, str | None],
    inherited: dict[str, str],
) -> dict[str, str]:
    """The variables one node makes, with the scale it gives each; a Recode's
    source has the codebook's scale, else the one it has where the Recode
    reads it (``inherited``)."""

    scales: dict[str, str] = {}

    def made(name: Any, scale: str | None) -> None:
        if isinstance(name, str) and name and scale:
            scales.setdefault(name, scale)

    params = resolved_params(spec, node.get("params") or {})
    kind = spec.type
    if kind == "prepare.derive":
        made(params.get("name"), params.get("scale") or "ratio")
    elif kind == "prepare.recode" and isinstance(params.get("variable"), str):
        source = params["variable"]
        made(
            params.get("into") or f"{source}_recoded",
            params.get("scale") or codebook.get(source) or inherited.get(source) or "nominal",
        )
    elif kind == "prepare.index":
        made(params.get("name"), "interval")
    elif kind == "prepare.bands":
        made(params.get("into"), "ordinal")
    elif kind in ("analyze.cluster", "prepare.text_code"):
        made(params.get("into"), "nominal")
    elif kind == "prepare.quality":
        made(params.get("flags_column"), "nominal")
        made(params.get("score_column"), "ratio")
    elif kind == "prepare.explode" and params.get("variable") and questionnaire:
        for name in _exploded_names(questionnaire, params):
            made(name, "nominal")
    elif kind == "analyze.factor" and params.get("scores"):
        for name in _factor_score_names(spec, params):
            made(name, "interval")
    elif (
        kind == "prepare.maxdiff_scores"
        and questionnaire
        and isinstance(params.get("question"), str)
    ):
        for name in _maxdiff_score_names(questionnaire, params):
            made(name, "interval")
    return scales


def _assigned_variables(questionnaire: dict[str, Any] | None) -> list[str]:
    """The variables the questionnaire's scripts write for every respondent —
    the arm ``Script.assign_condition`` draws — as
    ``Questionnaire.assigned_variables()`` names them. No question collects an
    arm and the document need not declare it, yet real responses and Simulated
    data carry it as a column, so a node may name it (a crosstab by
    ``condition``), just as ``validate()`` lets a condition read it."""

    from siamang.model.scripts import script_from_document

    names: list[str] = []
    for payload in (questionnaire or {}).get("scripts") or []:
        try:
            assigned = script_from_document(payload).assigns
        except (KeyError, TypeError, ValueError, AttributeError):
            continue  # a broken script is the questionnaire check's to report
        if assigned and assigned not in names:
            names.append(assigned)
    return names


def _exploded_names(questionnaire: dict[str, Any], params: dict[str, Any]) -> set[str]:
    """The indicator columns ``prepare.explode`` will create, by codebook order.

    Named here rather than declared with ``creates`` because the node invents one
    column per option instead of one per parameter, and a later node that cannot
    name them is a node that cannot use them.
    """

    variable = params["variable"]
    if not isinstance(variable, str):
        return set()  # PARAM_INVALID: "expected a string"; it raised TypeError here
    payload = (questionnaire.get("variables") or {}).get(variable) or {}
    prefix = params.get("prefix") or f"{variable}_"
    return {f"{prefix}{code}" for code, _label in _labelled(payload.get("labels"))}


def _labelled(raw: Any) -> list[tuple[Any, str]]:
    """A codebook's value labels as ``(code, label)`` pairs, in either form a
    document writes them: a list of ``{code, label}`` in the author's order, or
    the ``{code: label}`` shorthand read as the questionnaire reads it
    (``_codebook_from_doc``: codes parsed, "01" is 1, 0 and up ascending, then
    the negative ones, then text). A shorthand iterated as a list gave its keys,
    strings, and ``item.get`` raised AttributeError — a 500 at Save."""

    from siamang.model.document import DocumentError, _codebook_from_doc

    if isinstance(raw, dict):
        try:
            return list(_codebook_from_doc(raw, "labels").items())
        except DocumentError:
            return []  # a broken codebook is the questionnaire check's to report
    if isinstance(raw, list):
        return [
            (item.get("code"), str(item.get("label", item.get("code"))))
            for item in raw
            if isinstance(item, dict) and "code" in item
        ]
    return []


def _code_text(code: Any) -> str:
    """A code as the codebook writes it: 3, not the 3.0 a JSON number may hold."""

    if isinstance(code, float) and code.is_integer():
        return str(int(code))
    return str(code)


def _factor_score_names(spec: NodeSpec, params: dict[str, Any]) -> set[str]:
    """The score variables ``analyze.factor`` adds: ``<into>1`` … one per factor.

    With a fixed number of factors those are the names; chosen by a rule, the
    number is known only after the run, so every name the analysis could make is
    allowed — a factor analysis has fewer factors than items.
    """

    prefix = params.get("into") or spec.params["into"].default
    fixed = params.get("n_factors")
    items = params.get("items")
    # Items that are not a list are PARAM_INVALID; len() of them raised here.
    listed = len(items) if isinstance(items, list) else 0
    count = fixed if isinstance(fixed, int) and fixed > 0 else listed - 1
    return {f"{prefix}{index}" for index in range(1, count + 1)}


def _maxdiff_score_names(questionnaire: dict[str, Any], params: dict[str, Any]) -> set[str]:
    """The score variables ``prepare.maxdiff_scores`` will create, one per item.

    Named here for the reason :func:`_exploded_names` names its columns: the
    node invents one variable per item of the question, and a later node that
    cannot name them cannot use them. The items are the question's ``choices``,
    else its first variable's labels — the pool ``MaxDiff.item_codes`` reads.
    """

    from siamang.data.maxdiff import score_names
    from siamang.model.document import DocumentError, _codebook_from_doc

    wanted = params["question"]
    item = _maxdiff_question(questionnaire, wanted)
    if item is None:
        return set()  # _check_maxdiff_question names the questions there are
    names = [name for name in item.get("var") or [] if isinstance(name, str)]
    try:
        if item.get("choices"):
            codes = list(_codebook_from_doc(item["choices"], wanted))
        else:
            payload = (questionnaire.get("variables") or {}).get(names[0]) or {}
            codes = list(_codebook_from_doc(payload.get("labels") or [], wanted))
    except DocumentError:
        return set()  # a broken codebook is the questionnaire check's to report
    return set(score_names(wanted, codes, params.get("prefix")).values())


def _maxdiff_questions(questionnaire: dict[str, Any]) -> list[tuple[dict[str, Any], str]]:
    """Every MaxDiff question of the document, with the name the runtime gives
    it (``question_output_name``: its name, else its id, else
    ``maxdiff_<first variable>``)."""

    found = []
    for item in _document_questions(questionnaire):
        names = [name for name in item.get("var") or [] if isinstance(name, str)]
        if item.get("type") == "MaxDiff" and names:
            found.append((item, item.get("name") or item.get("id") or f"maxdiff_{names[0]}"))
    return found


def _maxdiff_question(questionnaire: dict[str, Any], wanted: Any) -> dict[str, Any] | None:
    """The MaxDiff question ``wanted`` names — by id, name or runtime name."""

    for item, _name in _maxdiff_questions(questionnaire):
        first = next(name for name in item["var"] if isinstance(name, str))
        if wanted in {item.get("id"), item.get("name"), f"maxdiff_{first}"}:
            return item
    return None


def _check_maxdiff_question(
    node_id: str, params: dict[str, Any], questionnaire: dict[str, Any]
) -> list[FlowIssue]:
    """MaxDiff scores names a question the questionnaire has: a typo is named
    before the run, with the questions to choose from."""

    wanted = params.get("question")
    if not isinstance(wanted, str) or not wanted or _maxdiff_question(questionnaire, wanted):
        return []
    names = [name for _item, name in _maxdiff_questions(questionnaire)]
    known = f"this questionnaire has: {', '.join(names)}" if names else "it has none"
    return [
        FlowIssue(
            "error",
            "PARAM_INVALID",
            f"Parameter 'question' of {node_id}: no MaxDiff question named {wanted!r}; {known}.",
            node_id,
        )
    ]


def _document_questions(questionnaire: dict[str, Any]):
    """Every question of a questionnaire document, blocks opened."""

    def walk(items: Any):
        for item in items if isinstance(items, list) else []:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "Block":
                yield from walk(item.get("items"))
            else:
                yield item

    for page in questionnaire.get("pages") or []:
        if isinstance(page, dict):
            yield from walk(page.get("items"))


def _check_params(
    node_id: str,
    spec: NodeSpec,
    params: dict[str, Any],
    known: set[str] | None,
    scales: dict[str, str | None],
    made: dict[str, str] | None = None,
) -> list[FlowIssue]:
    issues: list[FlowIssue] = []
    for name in params:
        if name not in spec.params:
            issues.append(
                FlowIssue(
                    "error", "UNKNOWN_PARAM", f"{spec.type} has no parameter {name!r}.", node_id
                )
            )
    resolved = resolved_params(spec, params)
    for name, param in spec.params.items():
        if not spec.reads(name, resolved):
            # A value the node's code does not read with these choices (a Group A
            # kept after Design went paired) changes nothing, so it is not
            # checked: the run ignores it, and a builder that hides the field
            # would otherwise report an error in a field nobody can see.
            continue
        value = params.get(name, param.default)
        # An empty mapping means "not set", exactly as an empty list does. Without
        # {} here an optional `mapping` param could never be left alone: its empty
        # default reached _param_problem and came back "expected a non-empty
        # code → value object", while a required one reported the wrong code.
        if unset(value):
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
                elif (
                    param.scales
                    and made
                    and variable in made
                    and made[variable] not in param.scales
                ):
                    issues.append(
                        FlowIssue(
                            "warning",
                            "VARIABLE_SCALE",
                            f"Parameter {name!r} of {node_id}: {variable!r} is {made[variable]} "
                            f"(as the node that makes it gives it), expected "
                            f"{' | '.join(param.scales)}.",
                            node_id,
                        )
                    )
        if known is not None and param.kind == "formula":
            from siamang.data.formula import FormulaError, parse

            try:
                named = sorted(parse(value).variables())
            except FormulaError:
                named = []  # already reported as PARAM_INVALID above
            for variable in named:
                if variable not in known:
                    issues.append(
                        FlowIssue(
                            "error",
                            "UNKNOWN_VARIABLE",
                            f"Parameter {name!r} of {node_id} names unknown variable "
                            f"{variable!r}.",
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


def unset(value: Any) -> bool:
    """Whether a stored parameter value means "not set": null, "", [] or {}.

    Studio stores [] or "" when a field is cleared, and other clients may
    store null; each is the default, never a value of its own.
    """

    return value is None or (isinstance(value, str | list | dict) and len(value) == 0)


def resolved_params(spec: NodeSpec, given: dict[str, Any]) -> dict[str, Any]:
    """Every parameter of ``spec``: the value given, or the default when unset."""

    return {
        name: param.default if unset(given.get(name)) else given[name]
        for name, param in spec.params.items()
    }


def _check_rules(node_id: str, spec: NodeSpec, given: dict[str, Any]) -> list[FlowIssue]:
    """The spec's ``checks``: parameters that do not go together (a post-hoc
    test that does not follow the test chosen), or one the node would ignore.

    An error rule about a parameter the code does not read with these choices
    is not checked, as :func:`_check_params` does not check its value: it
    would stop a run over a value the run ignores. A warning is still given —
    saying that a value is ignored is what a warning rule is for.
    """

    params = resolved_params(spec, given)
    return [
        FlowIssue(check.severity, "PARAM_CONFLICT", f"{node_id}: {check.message}", node_id)
        for check in spec.checks
        if check.violated(params)
        and (
            check.severity != "error"
            or all(
                spec.reads(name, params)
                for condition in (check.when, *check.require)
                for name in condition_params(condition)
            )
        )
    ]


def _check_design(
    node_id: str, spec: NodeSpec, given: dict[str, Any], questionnaire: dict[str, Any] | None
) -> list[FlowIssue]:
    """What a node's parameters settle before any data, beyond the rules its
    grammar can say: how many variables a paired test compares (an error — the
    run would refuse it), a Bar chart's Bins that are not auto, a number or
    increasing edges (an error), and a t-test of two groups whose Groups has
    more than two answers in the codebook with none named (a warning: a filter
    upstream may leave two in the data)."""

    params = resolved_params(spec, given)
    if spec.type == "analyze.paired":
        from siamang.data.paired import count_problem

        variables = params.get("variables")
        if isinstance(variables, list) and variables:
            problem = count_problem(str(params.get("test")), len(variables))
            if problem:
                return [FlowIssue("error", "PARAM_CONFLICT", f"{node_id}: {problem}", node_id)]
    problem = _method_problem(spec.type, params)
    if problem:
        return [FlowIssue("error", "PARAM_CONFLICT", f"{node_id}: {problem}", node_id)]
    if (
        spec.type == "visualize.bar"
        and isinstance(params.get("split"), str)
        and params.get("split") == params.get("variable")
        and params.get("layout") not in ("histogram", "donut")
    ):
        return [
            FlowIssue(
                "error",
                "PARAM_CONFLICT",
                f"{node_id}: Split by must be another variable than Variable.",
                node_id,
            )
        ]
    if spec.type == "visualize.bar" and params.get("layout") == "histogram":
        from siamang.reporting.bars import parse_bins

        try:
            parse_bins(params.get("bins"))
        except ValueError as exc:
            return [
                FlowIssue(
                    "error", "PARAM_INVALID", f"Parameter 'bins' of {node_id}: {exc}", node_id
                )
            ]
    if (
        spec.type == "analyze.ttest"
        and questionnaire is not None
        and params.get("kind") == "independent"
        and unset(given.get("group_a"))
        and unset(given.get("group_b"))
        and isinstance(params.get("group"), str)
    ):
        payload = (questionnaire.get("variables") or {}).get(params["group"]) or {}
        answers = _answers(payload)
        if len(answers) > 2:
            listed = ", ".join(f"{code} = {label}" for code, label in answers)
            name = payload.get("label") or params["group"]
            return [
                FlowIssue(
                    "warning",
                    "PARAM_CONFLICT",
                    f"{node_id}: {name} has {len(answers)} answers ({listed}); a t-test "
                    "compares two — name them in Group A and Group B, unless the data "
                    "this node reads holds only two of them.",
                    node_id,
                )
            ]
    return []


def _check_ordinal_outcome(
    node_id: str,
    spec: NodeSpec,
    given: dict[str, Any],
    questionnaire: dict[str, Any] | None,
    scales: dict[str, str | None],
    made: dict[str, str],
) -> list[FlowIssue]:
    """An ordinal regression of a nominal outcome, in the words the run refuses
    it with: an error for the codebook's scale, a warning for the scale a node
    upstream gives what it makes (as other scale checks of made variables)."""

    from siamang.data.ordinal import outcome_problem

    params = resolved_params(spec, given)
    y = params.get("y")
    if params.get("kind") != "ordinal" or not isinstance(y, str):
        return []
    from_codebook = y in scales
    scale = scales.get(y) if from_codebook else made.get(y)
    payload = ((questionnaire or {}).get("variables") or {}).get(y) or {}
    problem = outcome_problem(
        str(payload.get("label") or y), scale, [label for _, label in _answers(payload)]
    )
    if not problem:
        return []
    severity = "error" if from_codebook else "warning"
    return [FlowIssue(severity, "VARIABLE_SCALE", f"{node_id}: {problem}", node_id)]


def _method_problem(node_type: str, params: dict[str, Any]) -> str | None:
    """What the parameters of an analysis node settle before any data, in the
    words the run would refuse it with: how many drivers Key drivers weighs
    (two or more, and at most 15 for the Shapley value), how many attributes a
    Perceptual map of attributes counts (two or more), and a Price sensitivity
    node's prices against its questions and its four different questions."""

    if node_type == "analyze.drivers":
        from siamang.data.drivers import count_problem

        predictors = params.get("predictors")
        if isinstance(predictors, list) and predictors:
            return count_problem(str(params.get("method")), len(predictors))
    if node_type == "analyze.correspondence" and params.get("layout") == "attributes":
        from siamang.data.correspondence import layout_problem

        attributes = params.get("attributes")
        if isinstance(attributes, list) and attributes:
            return layout_problem("attributes", attributes)
    if node_type == "analyze.price":
        from siamang.data.pricing import price_problem

        return price_problem(params)
    return None


def _answers(payload: dict[str, Any]) -> list[tuple[str, str]]:
    """A codebook variable's labelled answers as ``(code, label)``, its missing
    codes left out, in the order the questionnaire reads them (:func:`_labelled`).
    A missing code matches an answer by its text as the codebook writes it, so
    a missing 3.0 is the answer 3. The missing codes are the questionnaire's:
    ``missing``, a list of ``{code, label, kind}``, and ``missing_values``, a
    list of codes, which ``Variable`` counts as missing too (and the t-test
    leaves out); a bare code or a mapping keyed by code in ``missing`` is read
    as well."""

    left_out = _missing_codes(payload)
    return [
        (_code_text(code), label)
        for code, label in _labelled(payload.get("labels"))
        if _code_text(code) not in left_out
    ]


def _missing_codes(payload: dict[str, Any]) -> dict[str, str | None]:
    """A codebook variable's missing codes, as the codebook writes each (3,
    not 3.0), with its label where the document gives one (see :func:`_answers`
    for the forms read)."""

    from siamang.model.document import _parse_code_key

    raw = payload.get("missing")
    found: dict[str, str | None] = {}
    if isinstance(raw, dict):
        for code, label in raw.items():
            found[_code_text(_parse_code_key(code))] = label if isinstance(label, str) else None
    elif isinstance(raw, list):
        for item in raw:
            code = item.get("code") if isinstance(item, dict) else item
            label = item.get("label") if isinstance(item, dict) else None
            found[_code_text(code)] = label if isinstance(label, str) else None
    values = payload.get("missing_values")
    if isinstance(values, list):
        for code in values:
            found.setdefault(_code_text(code), None)
    labels = dict((_code_text(code), label) for code, label in _labelled(payload.get("labels")))
    return {code: label or labels.get(code) for code, label in found.items()}


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
        if not _names_given(value):
            return "every variable in a condition needs a name."
        # What the code generator cannot write is this check's to say: a part
        # of an and/or that is not an expression passed here and failed at
        # generate_flow, after the check had called the flow fine.
        from siamang.flow.template import render_condition

        try:
            render_condition(value)
        except FlowError as exc:
            return str(exc)
    elif kind == "formula":
        if not isinstance(value, str):
            return f"expected a formula, got {type(value).__name__}."
        from siamang.data.formula import FormulaError, parse

        try:
            parse(value)
        except FormulaError as exc:
            return exc.at()
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
    elif kind == "theme":
        from siamang.reporting.theme import ReportTheme, ReportThemeError

        try:
            ReportTheme.from_dict(value)
        except ReportThemeError as exc:
            return str(exc)
    elif kind == "layout":
        from siamang.reporting.document import layout_problem

        if not isinstance(value, dict):
            return "expected node id → {width, align, break_before}."
        for node, placement in value.items():
            problem = layout_problem(placement)
            if problem:
                return f"{node}: {problem}"
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


def _names_given(node: Any) -> bool:
    """Whether every variable reference in a condition names its variable."""
    if isinstance(node, dict):
        if node.get("type") == "var":
            return isinstance(node.get("name"), str) and bool(node["name"])
        return _names_given(node.get("left")) and _names_given(node.get("right"))
    if isinstance(node, list):
        return all(_names_given(item) for item in node)
    return True


def _condition_variables(node: Any) -> set[str]:
    if isinstance(node, dict):
        if node.get("type") == "var":
            # A reference without a name is PARAM_INVALID (_names_given).
            name = node.get("name")
            return {name} if isinstance(name, str) and name else set()
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


def _check_likert_scale(
    node_id: str, params: dict[str, Any], questionnaire: dict[str, Any]
) -> list[FlowIssue]:
    """A Likert chart's items share one scale: the same labelled answers in the
    codebook, missing codes aside (``_answers``) — else the whole numbers of a
    valid range, else the points of the Likert scale question asking it — as
    the chart requires when it runs (``siamang.reporting.likert.likert_scale``),
    and each has one answer. Items the codebook does not hold (made upstream)
    are the run's to check."""

    items = params.get("items")
    if not isinstance(items, list):
        return []
    variables = questionnaire.get("variables") or {}
    known = [name for name in items if isinstance(name, str) and name in variables]
    asked = _asked_by(questionnaire)

    def problem(message: str) -> list[FlowIssue]:
        return [FlowIssue("error", "PARAM_CONFLICT", f"{node_id}: {message}", node_id)]

    for name in known:
        if (asked.get(name) or {}).get("type") in _SEVERAL_ANSWERS:
            label = variables[name].get("label") or name
            return problem(
                f"{label} allows several answers; a Likert chart draws items with one answer "
                "each on a scale."
            )

    def scale(name: str) -> list[tuple[str, str]]:
        return [
            (code, " ".join(label.split()).casefold())
            for code, label in _likert_answers(variables[name], asked.get(name))
        ]

    def described(name: str) -> str:
        answers = _likert_answers(variables[name], asked.get(name))
        if not answers:
            return "no value labels"
        parts = [f"{code} = {label}" for code, label in answers]
        return ", ".join([*parts[:3], "…", *parts[-2:]] if len(parts) > 6 else parts)

    if known and len(known) == len(items) and not any(scale(name) for name in known):
        return problem(
            "A Likert chart draws the answers of a scale, and none of the items has value "
            "labels (or a valid range of whole numbers) in the codebook, or a Likert scale "
            "question, to say what the scale is."
        )
    if len(known) < 2:
        return []
    first = known[0]
    for name in known[1:]:
        if scale(name) != scale(first):
            label = variables[first].get("label") or first
            other = variables[name].get("label") or name
            return problem(
                f"The items of a Likert chart must share one scale, and these do not: {label} "
                f"has {described(first)}; {other} has {described(name)}. Draw them in "
                "separate charts, or recode them onto one scale first."
            )
    return []


#: The question types whose variable holds a list of answers.
_SEVERAL_ANSWERS = ("MultiChoice", "Ranking")


def _asked_by(questionnaire: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Each variable's question in the document, by the variable it asks."""

    found: dict[str, dict[str, Any]] = {}

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            name = node.get("var")
            if isinstance(name, str) and isinstance(node.get("type"), str):
                found.setdefault(name, node)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(questionnaire.get("pages") or [])
    walk(questionnaire.get("blocks") or [])
    return found


def _likert_answers(
    payload: dict[str, Any], question: dict[str, Any] | None
) -> list[tuple[str, str]]:
    """What a Likert chart reads as a variable's scale, as the run reads it
    (``likert._answers``): its labelled answers, else the whole numbers of its
    valid range (2 to 11 of them), else its Likert scale question's points."""

    answers = _answers(payload)
    if answers:
        return answers
    bounds = payload.get("valid_range")
    if isinstance(bounds, list) and len(bounds) == 2:
        try:
            low, high = (float(bound) for bound in bounds)
        except (TypeError, ValueError):
            low = high = 0.5
        if low.is_integer() and high.is_integer() and 2 <= high - low + 1 <= 11:
            return [(str(code), str(code)) for code in range(int(low), int(high) + 1)]
    if question and question.get("type") == "LikertScale":
        start = int(question.get("start") or 1)
        points = [start + index for index in range(int(question.get("points") or 5))]
        named = [(str(code), str(code)) for code in points]
        if points and question.get("left_label"):
            named[0] = (str(points[0]), str(question["left_label"]))
        if points and question.get("right_label"):
            named[-1] = (str(points[-1]), str(question["right_label"]))
        return named
    return []


def _check_bar_answers(
    node_id: str, spec: NodeSpec, given: dict[str, Any], questionnaire: dict[str, Any]
) -> list[FlowIssue]:
    """A Bar chart split by a question that allows several answers, or a stack
    of one's options; a histogram of a nominal, ordinal or multiple-choice
    question, and a donut of a multiple-choice one — refused by the run
    (``siamang.reporting.bars``), and knowable from the questionnaire."""

    params = resolved_params(spec, given)
    variables = questionnaire.get("variables") or {}
    asked = _asked_by(questionnaire)

    def several(name: Any) -> bool:
        return isinstance(name, str) and (asked.get(name) or {}).get("type") in _SEVERAL_ANSWERS

    def label(name: str) -> str:
        return str((variables.get(name) or {}).get("label") or name)

    split, drawn, layout = params.get("split"), params.get("variable"), params.get("layout")
    scale = (variables.get(drawn) or {}).get("scale") if isinstance(drawn, str) else None
    message = None
    if layout == "histogram" and several(drawn):
        message = (
            f"{label(drawn)} allows several answers; a histogram draws one number per respondent."
        )
    elif layout == "histogram" and scale in ("nominal", "ordinal"):
        message = (
            f"A histogram draws the distribution of a number, and {label(drawn)} is {scale}: "
            "draw its answers as bars (Layout = grouped)."
        )
    elif layout == "donut":
        if several(drawn):
            message = (
                f"{label(drawn)} allows several answers, so its shares add up to more than "
                "100 % and are not the parts of a whole: draw them as bars (Layout = grouped)."
            )
    elif several(split):
        message = (
            f"Split by needs one answer per respondent, and {label(split)} allows several: "
            "draw it as the Variable, or split by one of its options after Explode multiple "
            "choice."
        )
    elif not unset(split) and several(drawn) and params.get("layout") != "grouped":
        message = (
            f"{label(drawn)} allows several answers, so its options overlap and cannot be "
            "stacked: draw them side by side (Layout = grouped)."
        )
    if message:
        return [FlowIssue("error", "PARAM_CONFLICT", f"{node_id}: {message}", node_id)]
    # A number drawn as bars, a bar (or a series) for each value: the run
    # refuses more than bars.MAX_VALUES values, which the data tells; the
    # codebook's valid range can say so before.
    from siamang.reporting.bars import MAX_VALUES

    def many_values(name: Any) -> bool:
        payload = variables.get(name) or {} if isinstance(name, str) else {}
        span = payload.get("valid_range")
        if payload.get("scale") not in ("interval", "ratio") or payload.get("labels"):
            return False
        if not (isinstance(span, list | tuple) and len(span) == 2):
            return False
        try:
            return float(span[1]) - float(span[0]) + 1 > MAX_VALUES
        except (TypeError, ValueError):
            return False

    # (Split by takes a nominal or ordinal variable only: its parameter says so.)
    if many_values(drawn) and layout != "histogram" and unset(params.get("by")):
        return [
            FlowIssue(
                "warning",
                "PARAM_CONFLICT",
                f"{node_id}: {label(drawn)} is a number of up to "
                f"{_range_size(variables.get(drawn) or {})} values, and bars draw each value "
                "given: Layout histogram draws its distribution.",
                node_id,
            )
        ]
    return []


def _check_tabbook(
    node_id: str, spec: NodeSpec, given: dict[str, Any], questionnaire: dict[str, Any] | None
) -> list[FlowIssue]:
    """What a Tab book refuses when it runs (``write_tabbook``) and the flow
    already settles: a path that is not an .xlsx workbook, a banner variable
    whose question allows several answers — and, as warnings, a path the
    platform does not keep (outside outputs/) and a question named that is
    tabulated as asked but reads badly (a ranking, an open answer)."""

    params = resolved_params(spec, given)
    issues: list[FlowIssue] = []
    path = params.get("path")
    if isinstance(path, str) and path:
        if not path.lower().endswith(".xlsx"):
            issues.append(
                FlowIssue(
                    "error",
                    "PARAM_INVALID",
                    f"Parameter 'path' of {node_id}: A tab book is an Excel workbook: its path "
                    f"must end in .xlsx (got {path!r}).",
                    node_id,
                )
            )
        elif not _under_outputs(path):
            issues.append(
                FlowIssue(
                    "warning",
                    "PARAM_INVALID",
                    f"Parameter 'path' of {node_id}: {path!r} is not under outputs/, where a run "
                    "keeps what it writes.",
                    node_id,
                )
            )
    if questionnaire is None:
        return issues
    variables = questionnaire.get("variables") or {}
    asked = _asked_by(questionnaire)

    def label(name: str) -> str:
        return str((variables.get(name) or {}).get("label") or name)

    for name in params.get("banner") or []:
        if isinstance(name, str) and (asked.get(name) or {}).get("type") in _SEVERAL_ANSWERS:
            issues.append(
                FlowIssue(
                    "error",
                    "PARAM_CONFLICT",
                    f"{node_id}: {label(name)} holds multiple-choice answers, and a banner "
                    "column is a group of respondents that no one else is in. Explode it first "
                    "(prepare.explode) and use its columns, or choose another banner variable.",
                    node_id,
                )
            )
    for name in params.get("questions") or []:
        kind = (asked.get(name) or {}).get("type") if isinstance(name, str) else None
        if kind == "Ranking":
            issues.append(
                FlowIssue(
                    "warning",
                    "PARAM_CONFLICT",
                    f"{node_id}: {label(name)} is a ranking: every respondent orders every "
                    "option, so each option would read 100 % in every column — derive its "
                    "first choice (Derive) and tabulate that.",
                    node_id,
                )
            )
        elif kind == "OpenText":
            issues.append(
                FlowIssue(
                    "warning",
                    "PARAM_CONFLICT",
                    f"{node_id}: {label(name)} is an open answer: its answers would go into the "
                    "workbook word for word — code it first (Code open answers).",
                    node_id,
                )
            )
    return issues


def _under_outputs(path: str) -> bool:
    """Whether ``path`` (relative, as a flow names it) is inside outputs/."""
    parts = [part for part in path.replace("\\", "/").split("/") if part not in ("", ".")]
    return bool(parts) and parts[0] == "outputs" and ".." not in parts and len(parts) > 1


def _range_size(payload: dict[str, Any]) -> str:
    low, high = payload["valid_range"]
    return f"{int(float(high) - float(low) + 1):,}"


def _check_trend(
    node_id: str, spec: NodeSpec, given: dict[str, Any], questionnaire: dict[str, Any]
) -> list[FlowIssue]:
    """What a Trend refuses when it runs (``siamang.reporting.trend.trend``)
    and the questionnaire already settles: a multiple-choice question as Time
    or Split by, the mean of a nominal or multiple-choice question, a missing
    code named as an Answer code. Variables the codebook does not hold (made
    upstream, or a response time) are the run's to check."""

    params = resolved_params(spec, given)
    variables = questionnaire.get("variables") or {}
    asked = _asked_by(questionnaire)

    def several(name: Any) -> bool:
        return isinstance(name, str) and (asked.get(name) or {}).get("type") in _SEVERAL_ANSWERS

    def label(name: str) -> str:
        return str((variables.get(name) or {}).get("label") or name)

    time, by, measure = params.get("time"), params.get("by"), params.get("measure")
    variable, codes = params.get("variable"), params.get("codes")
    message = None
    if several(time):
        message = (
            f"{label(time)} holds multiple-choice answers (lists of codes), and Time is one wave "
            "or one date per respondent: choose the wave's variable or a date."
        )
    elif several(by):
        message = (
            f"Split by needs one answer per respondent, and {label(by)} allows several: split "
            "by one of its options after Explode multiple choice, or choose another variable."
        )
    elif measure == "mean" and several(variable):
        message = (
            f"{label(variable)} holds multiple-choice answers (lists of codes), which have no "
            "mean. Track the percent choosing an answer instead (Measure = percent)."
        )
    elif (
        measure == "mean"
        and isinstance(variable, str)
        and (variables.get(variable) or {}).get("scale") == "nominal"
    ):
        message = (
            f"{label(variable)} is nominal: its codes are names, not amounts, so their mean "
            "says nothing. Track the percent choosing an answer instead (Measure = percent)."
        )
    elif measure == "percent" and isinstance(variable, str) and variable in variables:
        missing = _missing_codes(variables[variable])
        named_codes = codes if isinstance(codes, list) else [] if unset(codes) else [codes]
        for code in named_codes:
            text = _code_text(code)
            if text in missing:
                named = f"{text} ({missing[text]})" if missing[text] else text
                message = (
                    f"{named} is a missing code of {label(variable)}, not an answer: missing "
                    "codes are left out of the base. Name an answer."
                )
                break
    return (
        [FlowIssue("error", "PARAM_CONFLICT", f"{node_id}: {message}", node_id)] if message else []
    )


def dumps(document: dict[str, Any]) -> str:
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


def loads(text: str) -> dict[str, Any]:
    document = json.loads(text)
    if not isinstance(document, dict):
        raise FlowError("Flow must be a JSON object.")
    return document


def _check_result_charts(
    nodes: dict[str, dict[str, Any]], edges: list[Edge], registry: Registry
) -> list[FlowIssue]:
    """What a Result chart is given, read before the run: an output it cannot
    draw, or a Kind that does not suit it, is named on the canvas rather than
    raised by the run — the node types and parameters upstream say enough
    (:func:`siamang.reporting.result_charts.check_sources`)."""

    charts = [
        node_id for node_id, node in nodes.items() if node["type"] == "visualize.result_chart"
    ]
    if not charts or "visualize.result_chart" not in registry:
        return []
    from siamang.reporting.result_charts import check_sources

    spec = registry.get("visualize.result_chart")
    issues: list[FlowIssue] = []
    for node_id in charts:
        sources = []
        for edge in edges:
            if edge.target != node_id or edge.target_port != "result":
                continue
            source = registry.get(nodes[edge.source]["type"])
            sources.append(
                (
                    edge.source,
                    source.type,
                    source.title,
                    edge.source_port,
                    source.outputs[edge.source_port],
                    resolved_params(source, nodes[edge.source].get("params") or {}),
                )
            )
        if not sources:
            continue  # INPUT_NOT_CONNECTED says so
        kind = resolved_params(spec, nodes[node_id].get("params") or {}).get("kind")
        for severity, code, message in check_sources(str(kind), sources):
            issues.append(FlowIssue(severity, code, f"{node_id}: {message}", node_id))
    return issues


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
