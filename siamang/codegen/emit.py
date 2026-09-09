"""A very small Python-source layout engine.

The generator builds a tree of :class:`Node` objects (calls, lists, dicts,
tuples, literals) and :func:`render` lays it out: one line when it fits in
the line length, otherwise one element per line with a trailing comma —
the same shape ``ruff format`` / black produce, so the formatter run
afterward has (almost) nothing left to do and the output stays readable
even without it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

LINE_LENGTH = 100
INDENT = "    "


class Node:
    """Base class of everything :func:`render` can lay out."""


@dataclass(frozen=True, slots=True)
class Raw(Node):
    """Source text that is emitted verbatim (an identifier, a literal)."""

    text: str


@dataclass(frozen=True, slots=True)
class Call(Node):
    name: str
    args: tuple[Node, ...] = ()
    kwargs: tuple[tuple[str, Node], ...] = ()


@dataclass(frozen=True, slots=True)
class List(Node):
    items: tuple[Node, ...] = ()


@dataclass(frozen=True, slots=True)
class Tuple(Node):
    items: tuple[Node, ...] = ()


@dataclass(frozen=True, slots=True)
class Dict(Node):
    items: tuple[tuple[Node, Node], ...] = ()


@dataclass(frozen=True, slots=True)
class BinOp(Node):
    """``left <op> right`` with the operands parenthesized when asked to."""

    op: str
    left: Node
    right: Node
    parens: bool = field(default=False)


@dataclass(frozen=True, slots=True)
class Unary(Node):
    op: str
    operand: Node


def literal(value: Any) -> Node:
    """A Python literal for a JSON value (``None``/``True``/``False`` included)."""

    if isinstance(value, Node):
        return value
    if value is None or isinstance(value, bool | int | float):
        return Raw(repr(value))
    if isinstance(value, str):
        return Raw(string(value))
    if isinstance(value, list | tuple):
        return List(tuple(literal(item) for item in value))
    if isinstance(value, dict):
        return Dict(tuple((literal(key), literal(item)) for key, item in value.items()))
    raise TypeError(f"Cannot render {type(value).__name__} as a literal.")


def string(value: str) -> str:
    """A double-quoted string literal, the way ruff normalizes quotes."""

    if '"' not in value or "'" in value:
        body = value.replace("\\", "\\\\").replace('"', '\\"')
        body = body.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
        return f'"{body}"'
    return repr(value)


def triple_string(value: str) -> str:
    """A triple-quoted literal for multi-line text such as JavaScript code."""

    body = value.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
    if body.endswith('"'):
        body = body[:-1] + '\\"'
    return f'"""{body}"""'


# ─── rendering ───────────────────────────────────────────────────────────────


def render(node: Node, indent: int = 0, *, width: int = LINE_LENGTH) -> str:
    """Lay ``node`` out at ``indent`` columns; the first line is not indented."""

    flat = _flat(node)
    if "\n" not in flat and indent + len(flat) <= width:
        return flat
    return _expanded(node, indent, width)


def _flat(node: Node) -> str:
    if isinstance(node, Raw):
        return node.text
    if isinstance(node, Call):
        parts = [_flat(arg) for arg in node.args]
        parts += [f"{key}={_flat(value)}" for key, value in node.kwargs]
        return f"{node.name}({', '.join(parts)})"
    if isinstance(node, List):
        return "[" + ", ".join(_flat(item) for item in node.items) + "]"
    if isinstance(node, Tuple):
        if len(node.items) == 1:
            return f"({_flat(node.items[0])},)"
        return "(" + ", ".join(_flat(item) for item in node.items) + ")"
    if isinstance(node, Dict):
        return "{" + ", ".join(f"{_flat(k)}: {_flat(v)}" for k, v in node.items) + "}"
    if isinstance(node, BinOp):
        text = f"{_flat(node.left)} {node.op} {_flat(node.right)}"
        return f"({text})" if node.parens else text
    if isinstance(node, Unary):
        return f"{node.op}{_flat(node.operand)}"
    raise TypeError(f"Unknown node {type(node).__name__}.")


def _expanded(node: Node, indent: int, width: int) -> str:
    inner = INDENT * (indent // 4 + 1)
    outer = INDENT * (indent // 4)
    if isinstance(node, Call):
        lines = [f"{node.name}("]
        for arg in node.args:
            lines.append(f"{inner}{render(arg, indent + 4, width=width)},")
        for key, value in node.kwargs:
            lines.append(f"{inner}{key}={render(value, indent + 4 + len(key) + 1, width=width)},")
        lines.append(f"{outer})")
        return "\n".join(lines)
    if isinstance(node, List | Tuple):
        open_, close = ("[", "]") if isinstance(node, List) else ("(", ")")
        lines = [open_]
        for item in node.items:
            lines.append(f"{inner}{render(item, indent + 4, width=width)},")
        lines.append(f"{outer}{close}")
        return "\n".join(lines)
    if isinstance(node, Dict):
        lines = ["{"]
        for key, value in node.items:
            key_text = render(key, indent + 4, width=width)
            lines.append(
                f"{inner}{key_text}: {render(value, indent + 4 + len(key_text) + 2, width=width)},"
            )
        lines.append(f"{outer}}}")
        return "\n".join(lines)
    if isinstance(node, BinOp):
        left = render(node.left, indent + (1 if node.parens else 0), width=width)
        right = render(node.right, indent + (1 if node.parens else 0), width=width)
        text = f"{left} {node.op} {right}"
        return f"({text})" if node.parens else text
    if isinstance(node, Unary):
        return f"{node.op}{render(node.operand, indent + len(node.op), width=width)}"
    if isinstance(node, Raw):
        return node.text
    raise TypeError(f"Unknown node {type(node).__name__}.")
