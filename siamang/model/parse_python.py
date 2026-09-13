"""Read a questionnaire ``.py`` file without executing it.

``siamang model import`` runs the module; that is fine for your own files
and wrong for a file somebody uploaded. This module walks the file's syntax
tree instead and rebuilds the questionnaire from the *declarative* subset of
siamang code — the subset ``siamang codegen`` writes, and the one hand-written
questionnaires almost always stay in:

* ``import siamang as sg`` / ``from siamang import …`` / ``from siamang.core
  import …`` / ``from siamang.frontend import UIConfig`` / ``from datetime
  import datetime``;
* ``name = <expression>`` at module level;
* literals (numbers, strings, booleans, ``None``, lists, tuples, dicts,
  f-strings of constants), references to names bound earlier;
* calls of the engine's constructors and factories (``sg.Page``,
  ``SingleChoice``, ``Script.timed_question``, ``UIConfig``, ``Quota``…),
  the condition methods of variables (``age.lt(18)``, ``region.isin([…])``,
  ``barriers.contains(1)``),
  ``sg.AND / OR / NOT / compare``, the ``& | ~`` operators on conditions,
  ``codebook.add_many([...])`` and ``datetime.fromisoformat("…")``.

Everything else — loops, comprehensions, functions, ``if``, arbitrary calls,
other imports — is **not run**. Each such construct becomes a
:class:`Dropped` entry with its line number so the researcher sees exactly
what did not make it, and parsing carries on. Only whitelisted engine
callables are ever invoked, with values that came out of this evaluator, so
a hostile file can at worst produce a strange questionnaire.
"""

from __future__ import annotations

import ast
import inspect
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import siamang
import siamang.core as _core
import siamang.frontend.theme as _theme
from siamang.core.expression import Expression
from siamang.core.variable import Variable, VariableMap
from siamang.model.document import DocumentError, to_document


@dataclass(frozen=True, slots=True)
class Dropped:
    """One construct the static reader skipped."""

    line: int
    what: str
    why: str

    def __str__(self) -> str:
        return f"line {self.line}: {self.what} — {self.why}"


@dataclass(frozen=True, slots=True)
class StaticImportResult:
    document: dict[str, Any]
    warnings: list[str] = field(default_factory=list)
    dropped: list[Dropped] = field(default_factory=list)


class _Missing:
    """Value of an expression that could not be read (already reported)."""

    __slots__ = ()

    def __repr__(self) -> str:
        return "<missing>"


MISSING = _Missing()


class _Unsupported(Exception):
    def __init__(self, what: str, why: str) -> None:
        super().__init__(f"{what}: {why}")
        self.what = what
        self.why = why


# ── What the reader may call ────────────────────────────────────────────────

_ENGINE_MODULES = ("siamang.core", "siamang.frontend.theme")


def _engine_callables() -> dict[str, Any]:
    """Public classes/functions of the engine's questionnaire vocabulary."""
    names: dict[str, Any] = {}
    for module in (siamang, _core, _theme):
        for name in getattr(module, "__all__", ()):
            obj = getattr(module, name, None)
            if obj is None or not callable(obj):
                continue
            where = getattr(obj, "__module__", "") or ""
            if where.startswith(_ENGINE_MODULES):
                names[name] = obj
    return names


_CALLABLES = _engine_callables()
_MODULE_NAMES = {
    "siamang": _CALLABLES,
    "siamang.core": {n: o for n, o in _CALLABLES.items() if hasattr(_core, n)},
    "siamang.frontend": {n: o for n, o in _CALLABLES.items() if hasattr(_theme, n)},
    "siamang.frontend.theme": {n: o for n, o in _CALLABLES.items() if hasattr(_theme, n)},
}
_VARIABLE_METHODS = frozenset(
    {"eq", "ne", "gt", "ge", "lt", "le", "isin", "notin", "contains", "notcontains"}
)
_VARIABLEMAP_METHODS = frozenset({"add", "add_many"})
_SCRIPT_FACTORIES = frozenset(
    {"randomize_options", "randomize_pages", "timed_question", "validate_fields_match"}
)


class _Module:
    """A stand-in for an imported module: only whitelisted attributes resolve."""

    __slots__ = ("name", "names")

    def __init__(self, name: str, names: dict[str, Any]) -> None:
        self.name = name
        self.names = names


class _Datetime:
    """``datetime`` as the generated code uses it."""

    __slots__ = ()

    @staticmethod
    def fromisoformat(text: str) -> datetime:
        return datetime.fromisoformat(text)

    def __call__(self, *args: Any) -> datetime:
        return datetime(*args)


_DATETIME = _Datetime()
_MAX_SOURCE = 2_000_000


# ── The reader ───────────────────────────────────────────────────────────────


class _Reader:
    def __init__(self) -> None:
        self.env: dict[str, Any] = {}
        self.dropped: list[Dropped] = []

    # statements ------------------------------------------------------------

    def read(self, tree: ast.Module) -> None:
        for node in tree.body:
            try:
                self._statement(node)
            except _Unsupported as exc:
                self._drop(node, exc.what, exc.why)

    def _drop(self, node: ast.AST, what: str, why: str) -> None:
        self.dropped.append(Dropped(getattr(node, "lineno", 0), what, why))

    def _statement(self, node: ast.stmt) -> None:
        if isinstance(node, ast.Expr):
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                return  # docstring / bare string
            if isinstance(node.value, ast.Call):
                self._call(node.value)  # e.g. codebook.add_many([...])
                return
            raise _Unsupported("expression statement", "only calls are read")
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in _MODULE_NAMES:
                    self.env[alias.asname or alias.name] = _Module(
                        alias.name, _MODULE_NAMES[alias.name]
                    )
                elif alias.name == "datetime":
                    self.env[alias.asname or "datetime"] = _Module(
                        "datetime", {"datetime": _DATETIME}
                    )
                else:
                    raise _Unsupported(f"import {alias.name}", "only siamang and datetime imports")
            return
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "datetime":
                for alias in node.names:
                    if alias.name != "datetime":
                        raise _Unsupported(f"from datetime import {alias.name}", "not supported")
                    self.env[alias.asname or alias.name] = _DATETIME
                return
            names = _MODULE_NAMES.get(module)
            if names is None:
                raise _Unsupported(f"from {module} import …", "only siamang and datetime imports")
            for alias in node.names:
                if alias.name not in names:
                    raise _Unsupported(
                        f"from {module} import {alias.name}",
                        "not part of the questionnaire vocabulary",
                    )
                self.env[alias.asname or alias.name] = names[alias.name]
            return
        if isinstance(node, ast.Assign | ast.AnnAssign):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if len(targets) != 1 or not isinstance(targets[0], ast.Name):
                raise _Unsupported("assignment", "only `name = value` is read")
            if node.value is None:
                return
            value = self._expr(node.value)
            self.env[targets[0].id] = value
            return
        if isinstance(node, ast.Pass):
            return
        raise _Unsupported(
            type(node).__name__.lower() + " statement", "not read: the file is not executed"
        )

    # expressions -----------------------------------------------------------

    def _expr(self, node: ast.expr) -> Any:
        try:
            return self._eval(node)
        except _Unsupported as exc:
            self._drop(node, exc.what, exc.why)
            return MISSING
        except (DocumentError, ValueError, TypeError, KeyError, AttributeError) as exc:
            self._drop(node, ast.unparse(node)[:60], f"{type(exc).__name__}: {exc}")
            return MISSING

    def _eval(self, node: ast.expr) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.List):
            return [v for v in (self._expr(e) for e in node.elts) if v is not MISSING]
        if isinstance(node, ast.Tuple):
            values = [self._expr(e) for e in node.elts]
            if any(v is MISSING for v in values):
                raise _Unsupported("tuple", "an element could not be read")
            return tuple(values)
        if isinstance(node, ast.Set):
            return {v for v in (self._expr(e) for e in node.elts) if v is not MISSING}
        if isinstance(node, ast.Dict):
            out: dict[Any, Any] = {}
            for k, v in zip(node.keys, node.values, strict=True):
                if k is None:
                    raise _Unsupported("dict unpacking", "`**` is not read")
                key = self._eval(k)
                value = self._expr(v)
                if value is not MISSING:
                    out[key] = value
            return out
        if isinstance(node, ast.JoinedStr):
            parts = []
            for piece in node.values:
                if isinstance(piece, ast.Constant):
                    parts.append(str(piece.value))
                elif isinstance(piece, ast.FormattedValue):
                    parts.append(str(self._eval(piece.value)))
                else:
                    raise _Unsupported("f-string", "unsupported part")
            return "".join(parts)
        if isinstance(node, ast.Name):
            if node.id in self.env:
                value = self.env[node.id]
                if value is MISSING:
                    raise _Unsupported(node.id, "its value could not be read")
                return value
            raise _Unsupported(node.id, "undefined name (defined by code that is not read?)")
        if isinstance(node, ast.Attribute):
            return self._attribute(node)
        if isinstance(node, ast.Call):
            return self._call(node)
        if isinstance(node, ast.UnaryOp):
            operand = self._eval(node.operand)
            if isinstance(node.op, ast.Invert) and isinstance(operand, Expression):
                return ~operand
            if (
                isinstance(node.op, ast.USub)
                and isinstance(operand, int | float)
                and not isinstance(operand, bool)
            ):
                return -operand
            if isinstance(node.op, ast.Not) and isinstance(operand, bool):
                return not operand
            raise _Unsupported(ast.unparse(node)[:60], "unsupported unary operator")
        if isinstance(node, ast.BinOp):
            left, right = self._eval(node.left), self._eval(node.right)
            if isinstance(left, Expression) and isinstance(right, Expression):
                if isinstance(node.op, ast.BitAnd):
                    return left & right
                if isinstance(node.op, ast.BitOr):
                    return left | right
            numbers = (int, float)
            if (
                isinstance(left, numbers)
                and isinstance(right, numbers)
                and not isinstance(left, bool)
            ):
                if isinstance(node.op, ast.Add):
                    return left + right
                if isinstance(node.op, ast.Sub):
                    return left - right
                if isinstance(node.op, ast.Mult):
                    return left * right
                if isinstance(node.op, ast.Div) and right != 0:
                    return left / right
            if isinstance(left, str) and isinstance(right, str) and isinstance(node.op, ast.Add):
                return left + right
            raise _Unsupported(ast.unparse(node)[:60], "unsupported operator for these values")
        raise _Unsupported(type(node).__name__, "not read: the file is not executed")

    def _attribute(self, node: ast.Attribute) -> Any:
        if node.attr.startswith("_"):
            raise _Unsupported(ast.unparse(node)[:60], "private attributes are not read")
        base = self._eval(node.value)
        if isinstance(base, _Module):
            if node.attr in base.names:
                return base.names[node.attr]
            raise _Unsupported(
                f"{base.name}.{node.attr}", "not part of the questionnaire vocabulary"
            )
        if base is _DATETIME and node.attr == "fromisoformat":
            return _DATETIME.fromisoformat
        if isinstance(base, Variable) and node.attr in _VARIABLE_METHODS:
            return getattr(base, node.attr)
        if isinstance(base, VariableMap) and node.attr in _VARIABLEMAP_METHODS:
            return getattr(base, node.attr)
        script = _CALLABLES.get("Script")
        if script is not None and base is script and node.attr in _SCRIPT_FACTORIES:
            return getattr(script, node.attr)
        raise _Unsupported(ast.unparse(node)[:60], "attribute access is not read")

    def _call(self, node: ast.Call) -> Any:
        func = self._eval(node.func)
        if not self._allowed(func):
            raise _Unsupported(
                ast.unparse(node.func)[:60] + "(…)", "only the engine's constructors are called"
            )
        args = []
        for a in node.args:
            if isinstance(a, ast.Starred):
                raise _Unsupported("*args", "unpacking is not read")
            value = self._expr(a)
            if value is MISSING:
                raise _Unsupported(
                    ast.unparse(node.func)[:60] + "(…)", "an argument could not be read"
                )
            args.append(value)
        kwargs = {}
        for kw in node.keywords:
            if kw.arg is None:
                raise _Unsupported("**kwargs", "unpacking is not read")
            value = self._expr(kw.value)
            if value is MISSING:
                raise _Unsupported(
                    f"{ast.unparse(node.func)[:60]}(…, {kw.arg}=…)", "an argument could not be read"
                )
            kwargs[kw.arg] = value
        return func(*args, **kwargs)

    def _allowed(self, func: Any) -> bool:
        if func is _DATETIME or func is _DATETIME.fromisoformat:
            return True
        if any(func is obj for obj in _CALLABLES.values()):
            return True
        script = _CALLABLES.get("Script")
        if script is not None and inspect.ismethod(func) and func.__self__ is script:
            return func.__name__ in _SCRIPT_FACTORIES
        if inspect.ismethod(func):
            owner = func.__self__
            if isinstance(owner, Variable):
                return func.__name__ in _VARIABLE_METHODS
            if isinstance(owner, VariableMap):
                return func.__name__ in _VARIABLEMAP_METHODS
        return False


# ── Public API ───────────────────────────────────────────────────────────────


def parse_source(source: str, *, attribute: str = "survey") -> StaticImportResult:
    """Read questionnaire Python source statically and return its document."""
    if len(source) > _MAX_SOURCE:
        raise DocumentError("File too large to import (2 MB limit).")
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise DocumentError(f"Not valid Python: line {exc.lineno}: {exc.msg}") from exc
    reader = _Reader()
    reader.read(tree)
    survey = reader.env.get(attribute)
    questionnaire_cls = _CALLABLES.get("Questionnaire")
    if survey is MISSING or survey is None:
        hint = "; ".join(str(d) for d in reader.dropped[:3])
        raise DocumentError(
            f"The file does not define `{attribute} = sg.Questionnaire(...)` in a form that "
            "can be read without running it" + (f" ({hint})" if hint else "") + "."
        )
    if questionnaire_cls is not None and not isinstance(survey, questionnaire_cls):
        raise DocumentError(f"`{attribute}` is not a Questionnaire.")
    options = reader.env.get("options")
    if options is MISSING:
        options = None
    if options is not None and not isinstance(options, dict):
        raise DocumentError(f"`options` must be a dict, got {type(options).__name__}.")
    warnings: list[str] = []
    document = to_document(survey, options, on_warning=warnings.append)
    return StaticImportResult(document=document, warnings=warnings, dropped=list(reader.dropped))


def parse_file(path: str | Path, *, attribute: str = "survey") -> StaticImportResult:
    return parse_source(Path(path).read_text(encoding="utf-8"), attribute=attribute)
