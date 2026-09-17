"""Render a node's template into Python source.

The same rendering feeds :class:`~siamang.flow.runner.FlowRunner` (which
executes the text) and :func:`~siamang.flow.codegen.generate_flow` (which
writes it into a script), so a node behaves identically in both.
"""

from __future__ import annotations

import re
from typing import Any

from siamang.flow.document import FlowError, FlowGraph
from siamang.flow.registry import NodeSpec

_PLACEHOLDER = re.compile(r"\{(in|out)\.([a-z_][a-z0-9_]*)\}|\{([a-z_][a-z0-9_]*)!r\}")
_IDENT = re.compile(r"[^0-9a-zA-Z_]+")
_COMPARISONS = {"=", "!=", ">", ">=", "<", "<=", "in", "not in", "contains", "not contains"}


def output_names(node_id: str, spec: NodeSpec) -> dict[str, str]:
    """Variable name of each output: ``n_<id>`` alone, ``n_<id>_<port>`` when several."""

    base = "n_" + (_IDENT.sub("_", node_id).strip("_") or "node")
    if len(spec.outputs) == 1:
        return {next(iter(spec.outputs)): base}
    return {port: f"{base}_{port}" for port in spec.outputs}


def render_node(graph: FlowGraph, node_id: str) -> str:
    """The Python statements that execute ``node_id`` within ``graph``."""

    spec = graph.specs[node_id]
    params = graph.params(node_id)
    outputs = output_names(node_id, spec)
    inputs = _input_names(graph, node_id)
    values = {name: _render_param(spec, name, params[name], graph, node_id) for name in spec.params}
    values["node"] = repr(node_id)

    def substitute(match: re.Match[str]) -> str:
        kind, port, param = match.group(1), match.group(2), match.group(3)
        if kind == "in":
            if port not in inputs:
                raise FlowError(f"{spec.type}: template names unknown input {port!r}.")
            return inputs[port]
        if kind == "out":
            if port not in outputs:
                raise FlowError(f"{spec.type}: template names unknown output {port!r}.")
            return outputs[port]
        if param not in values:
            raise FlowError(f"{spec.type}: template names unknown parameter {param!r}.")
        return values[param]

    lines: list[str] = []
    for fragment in spec.template:
        if fragment.when is not None and not _when(fragment.when, params):
            continue
        lines.append(_PLACEHOLDER.sub(substitute, fragment.code))
    return "\n".join(lines) + "\n"


def subtitle(spec: NodeSpec, params: dict[str, Any]) -> str:
    """The node's one-line summary (``{row} × {col}``) with parameters filled in."""

    if not spec.subtitle:
        return ""
    try:
        return spec.subtitle.format(**{name: _short(value) for name, value in params.items()})
    except (KeyError, IndexError, ValueError):
        return ""


def _short(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    if isinstance(value, dict):
        return ", ".join(str(key) for key in value)
    return str(value)


def _when(condition: str, params: dict[str, Any]) -> bool:
    if "=" in condition:
        name, expected = condition.split("=", 1)
        return str(params.get(name)) == expected
    value = params.get(condition)
    return bool(value) and value != [] and value != {}


def _input_names(graph: FlowGraph, node_id: str) -> dict[str, str]:
    names: dict[str, str] = {}
    spec = graph.specs[node_id]
    for port_name, port in spec.inputs.items():
        sources = graph.inputs.get(node_id, {}).get(port_name, [])
        refs = [
            output_names(source, graph.specs[source])[source_port]
            for source, source_port in sources
        ]
        if port.many:
            names[port_name] = "[" + ", ".join(refs) + "]"
        elif refs:
            names[port_name] = refs[0]
        else:
            names[port_name] = "None"
    return names


# ─── parameters ──────────────────────────────────────────────────────────────


def _render_param(spec: NodeSpec, name: str, value: Any, graph: FlowGraph, node_id: str) -> str:
    kind = spec.params[name].kind
    if kind == "condition":
        return render_condition(value)
    if kind == "mapping":
        return repr({_code(key): item for key, item in value.items()}) if value else "None"
    if kind == "targets":
        return (
            repr(
                {
                    variable: {_code(key): share for key, share in margin.items()}
                    for variable, margin in value.items()
                }
            )
            if value
            else "None"
        )
    if kind == "captions":
        many = next((port for port in spec.inputs.values() if port.many), None)
        if many is None:
            return "[]"
        sources = graph.inputs.get(node_id, {}).get(many.name, [])
        captions = value or {}
        return repr([captions.get(source) for source, _port in sources])
    if kind == "layout":
        # The same shape `captions` takes: keyed by source node in the document
        # (so it survives a rename), positional in the code (so it lines up with
        # the `many` port the template zips over).
        many = next((port for port in spec.inputs.values() if port.many), None)
        if many is None:
            return "[]"
        sources = graph.inputs.get(node_id, {}).get(many.name, [])
        layout = value or {}
        return repr([dict(layout.get(source) or {}) for source, _port in sources])
    if kind == "theme":
        if not value:
            # Not "the default theme": no theme at all, so a house style handed
            # to the run (SIAMANG_REPORT_THEME) still applies.
            return "None"
        # Only the fields that were chosen, in the dataclass's own order, so the
        # script reads as a set of decisions. A plain dict rather than a
        # constructor call: it needs no import, and every other parameter in a
        # generated script is data too.
        from siamang.reporting.theme import ReportTheme

        return repr(ReportTheme.from_dict(value).to_dict())
    if kind == "float" and isinstance(value, int) and not isinstance(value, bool):
        return repr(float(value))
    return repr(value)


def _code(key: Any) -> Any:
    """JSON object keys are strings; answer codes are usually integers."""

    if isinstance(key, str):
        if re.fullmatch(r"-?\d+", key):
            return int(key)
        try:
            return float(key)
        except ValueError:
            return key
    return key


def render_condition(payload: Any) -> str:
    """A condition AST as an ``Expression``-building call chain.

    ``{op: "=", left: var, right: 2}`` -> ``sg.compare("consent", "=", 2)``;
    logical operators become ``sg.AND`` / ``sg.OR`` / ``sg.NOT``.
    """

    if not isinstance(payload, dict):
        raise FlowError(f"A condition must be an expression object, got {payload!r}.")
    kind = payload.get("type")
    if kind == "var":
        return f"sg.VarRef({payload['name']!r})"
    if kind != "expression":
        raise FlowError("Only structured expressions can be used in a flow (no raw strings).")
    op = payload.get("op")
    left, right = payload.get("left"), payload.get("right")
    if op in _COMPARISONS and isinstance(left, dict) and left.get("type") == "var":
        return f"sg.compare({left['name']!r}, {op!r}, {_operand(right)})"
    if op in {"and", "or"}:
        parts = _flatten(payload, op)
        return f"sg.{op.upper()}({', '.join(render_condition(part) for part in parts)})"
    if op == "not":
        return f"sg.NOT({render_condition(left)})"
    if op == "raw":
        raise FlowError("Raw string conditions cannot be evaluated on data.")
    return f"sg.Expression({op!r}, {_operand(left)}, {_operand(right)})"


def _operand(node: Any) -> str:
    if isinstance(node, dict) and node.get("type") in {"var", "expression"}:
        return render_condition(node)
    if isinstance(node, list):
        return "[" + ", ".join(_operand(item) for item in node) + "]"
    return repr(node)


def _flatten(node: dict[str, Any], op: str) -> list[Any]:
    items: list[Any] = []
    current: Any = node
    while (
        isinstance(current, dict)
        and current.get("type") == "expression"
        and current.get("op") == op
    ):
        items.append(current.get("right"))
        current = current.get("left")
    items.append(current)
    items.reverse()
    return items


__all__ = ["output_names", "render_condition", "render_node", "subtitle"]
