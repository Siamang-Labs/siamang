"""Arithmetic over a respondent's answers, written as text and read, never run.

A derived variable is the most ordinary thing in survey analysis — spend per
month from spend per year, a difference between two ratings, a price band from a
number — and until now the engine could only build one from a *condition*, which
gives a 0/1 indicator and nothing else.

This is a small language for the rest: the four operators, a handful of
functions, and ``if … then … else``. Two things are deliberate about it.

**Nothing is executed.** The text is tokenized and parsed into a tree, and the
tree is evaluated against a DataFrame. There is no ``eval``, and the formula
never becomes Python — the same posture as :mod:`siamang.model.parse_python`,
which reads a questionnaire without running it. What the parser cannot follow it
*reports*, with the position in the string, rather than guessing.

**Missing stays missing.** A respondent who skipped a question has no value, not
a zero, and arithmetic on it yields no value either. Division by zero gives the
same: not infinity, which would look like a number and quietly poison every mean
computed downstream. ``coalesce`` is how you say "treat a blank as zero", in one
visible place, when that is what you mean.

    >>> parse("(q1 + q2) / 2").variables()
    {'q1', 'q2'}
    >>> parse("if income > 0 then round(income / 12, 2) else 0")  # doctest: +ELLIPSIS
    Formula(...)

The grammar (spec/04-flows.md §3.2):

    expr    := ifexpr | orexpr
    ifexpr  := 'if' orexpr 'then' expr 'else' expr
    orexpr  := andexpr ('or' andexpr)*
    andexpr := notexpr ('and' notexpr)*
    notexpr := 'not' notexpr | compare
    compare := sum (('='|'!='|'>'|'>='|'<'|'<=') sum)?
    sum     := term (('+'|'-') term)*
    term    := unary (('*'|'/') unary)*
    unary   := '-' unary | atom
    atom    := number | name | func '(' expr (',' expr)* ')' | '(' expr ')'
    func    := mean | sum | min | max | abs | round | log | coalesce

The comparison and logical operators mean exactly what they mean in a
questionnaire condition (:mod:`siamang.core.expression`) — this is the same
vocabulary written inline, not a second dialect. ``contains`` is the one that
does not appear: it asks about a multiple answer, and a formula works on
numbers. Run ``prepare.explode`` first and use the 0/1 column it writes.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["Formula", "FormulaError", "parse"]


class FormulaError(ValueError):
    """A formula that cannot be read, and where reading stopped.

    Carries ``position`` (a 0-based offset into the formula text) so an editor
    can point at the character rather than repeating the message.
    """

    def __init__(self, message: str, position: int = 0) -> None:
        super().__init__(message)
        self.position = position

    def at(self) -> str:
        return f"{self} (at character {self.position + 1})"


# ── tokens ───────────────────────────────────────────────────────────────────

_KEYWORDS = frozenset({"if", "then", "else", "and", "or", "not"})
_FUNCTIONS = frozenset({"mean", "sum", "min", "max", "abs", "round", "log", "coalesce"})
_COMPARISONS = ("<=", ">=", "!=", "=", "<", ">")

_TOKEN_RE = re.compile(
    r"""
    (?P<space>\s+)
  | (?P<number>\d+\.\d+|\.\d+|\d+)
  | (?P<name>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<compare><=|>=|!=|=|<|>)
  | (?P<op>[+\-*/])
  | (?P<lparen>\()
  | (?P<rparen>\))
  | (?P<comma>,)
    """,
    re.VERBOSE,
)


@dataclass(frozen=True, slots=True)
class _Token:
    kind: str
    text: str
    position: int


def _tokenize(text: str) -> list[_Token]:
    tokens: list[_Token] = []
    index = 0
    while index < len(text):
        match = _TOKEN_RE.match(text, index)
        if match is None:
            raise FormulaError(f"{text[index]!r} does not belong in a formula", index)
        index = match.end()
        kind = match.lastgroup or ""
        if kind == "space":
            continue
        tokens.append(_Token(kind, match.group(), match.start()))
    return tokens


# ── the tree ─────────────────────────────────────────────────────────────────
#
# Every node evaluates to a pandas Series aligned to the frame it is given, so
# the whole formula is one vectorized pass rather than a call per row.


class _Node:
    def evaluate(self, frame: pd.DataFrame) -> pd.Series:  # pragma: no cover - interface
        raise NotImplementedError

    def variables(self) -> set[str]:
        return set()


@dataclass(frozen=True, slots=True)
class _Num(_Node):
    value: float

    def evaluate(self, frame: pd.DataFrame) -> pd.Series:
        return pd.Series(self.value, index=frame.index, dtype="float64")


@dataclass(frozen=True, slots=True)
class _Var(_Node):
    name: str
    position: int

    def evaluate(self, frame: pd.DataFrame) -> pd.Series:
        if self.name not in frame.columns:
            raise FormulaError(f"there is no variable named {self.name!r}", self.position)
        column = frame[self.name]
        numeric = pd.to_numeric(column, errors="coerce")
        # A column that is *entirely* unconvertible is a mistake worth naming:
        # silently turning every row into NaN produces an empty variable that
        # looks like a question nobody answered.
        if numeric.isna().all() and column.notna().any():
            raise FormulaError(
                f"{self.name!r} holds no numbers, so it cannot be used in arithmetic; "
                f"recode it first (prepare.recode) or explode it (prepare.explode)",
                self.position,
            )
        return numeric.astype("float64")

    def variables(self) -> set[str]:
        return {self.name}


@dataclass(frozen=True, slots=True)
class _Unary(_Node):
    operand: _Node

    def evaluate(self, frame: pd.DataFrame) -> pd.Series:
        return -self.operand.evaluate(frame)

    def variables(self) -> set[str]:
        return self.operand.variables()


@dataclass(frozen=True, slots=True)
class _BinOp(_Node):
    op: str
    left: _Node
    right: _Node
    position: int

    def evaluate(self, frame: pd.DataFrame) -> pd.Series:
        left = self.left.evaluate(frame)
        right = self.right.evaluate(frame)
        if self.op == "+":
            return left + right
        if self.op == "-":
            return left - right
        if self.op == "*":
            return left * right
        # Dividing by zero gives *missing*, not infinity. An infinity reads as a
        # number all the way to the report, where it takes the mean with it.
        with np.errstate(divide="ignore", invalid="ignore"):
            result = left / right.replace(0, np.nan)
        return result

    def variables(self) -> set[str]:
        return self.left.variables() | self.right.variables()


@dataclass(frozen=True, slots=True)
class _Compare(_Node):
    op: str
    left: _Node
    right: _Node

    def evaluate(self, frame: pd.DataFrame) -> pd.Series:
        left = self.left.evaluate(frame)
        right = self.right.evaluate(frame)
        if self.op == "=":
            return left == right
        if self.op == "!=":
            return left != right
        if self.op == ">":
            return left > right
        if self.op == ">=":
            return left >= right
        if self.op == "<":
            return left < right
        return left <= right

    def variables(self) -> set[str]:
        return self.left.variables() | self.right.variables()


@dataclass(frozen=True, slots=True)
class _BoolOp(_Node):
    op: str
    left: _Node
    right: _Node

    def evaluate(self, frame: pd.DataFrame) -> pd.Series:
        left = self.left.evaluate(frame).astype("boolean").fillna(False)
        right = self.right.evaluate(frame).astype("boolean").fillna(False)
        return (left & right) if self.op == "and" else (left | right)

    def variables(self) -> set[str]:
        return self.left.variables() | self.right.variables()


@dataclass(frozen=True, slots=True)
class _Not(_Node):
    operand: _Node

    def evaluate(self, frame: pd.DataFrame) -> pd.Series:
        return ~self.operand.evaluate(frame).astype("boolean").fillna(False)

    def variables(self) -> set[str]:
        return self.operand.variables()


@dataclass(frozen=True, slots=True)
class _IfElse(_Node):
    condition: _Node
    then: _Node
    otherwise: _Node

    def evaluate(self, frame: pd.DataFrame) -> pd.Series:
        mask = self.condition.evaluate(frame).astype("boolean").fillna(False).to_numpy(dtype=bool)
        chosen = np.where(mask, self.then.evaluate(frame), self.otherwise.evaluate(frame))
        return pd.Series(chosen, index=frame.index, dtype="float64")

    def variables(self) -> set[str]:
        return self.condition.variables() | self.then.variables() | self.otherwise.variables()


@dataclass(frozen=True, slots=True)
class _Call(_Node):
    name: str
    args: tuple[_Node, ...]
    position: int

    #: name -> (minimum arguments, maximum arguments or None for any number)
    ARITY: ClassVar[dict[str, tuple[int, int | None]]] = {
        "abs": (1, 1),
        "round": (1, 2),
        "log": (1, 2),
        "mean": (1, None),
        "sum": (1, None),
        "min": (1, None),
        "max": (1, None),
        "coalesce": (1, None),
    }

    def evaluate(self, frame: pd.DataFrame) -> pd.Series:
        values = [arg.evaluate(frame) for arg in self.args]
        if self.name == "abs":
            return values[0].abs()
        if self.name == "round":
            digits = int(_constant(self.args[1], self.position)) if len(values) > 1 else 0
            return values[0].round(digits)
        if self.name == "log":
            base = float(_constant(self.args[1], self.position)) if len(values) > 1 else math.e
            if base <= 0 or base == 1:
                raise FormulaError(f"log cannot use base {base:g}", self.position)
            # log of zero or a negative number is undefined, so it is missing —
            # not -inf, which would look like an extreme respondent.
            positive = values[0].where(values[0] > 0)
            with np.errstate(divide="ignore", invalid="ignore"):
                return np.log(positive) / math.log(base)
        # The rest are row-wise across the arguments.
        table = pd.concat(values, axis=1)
        if self.name == "mean":
            return table.mean(axis=1, skipna=True)
        if self.name == "sum":
            return table.sum(axis=1, skipna=True, min_count=1)
        if self.name == "min":
            return table.min(axis=1, skipna=True)
        if self.name == "max":
            return table.max(axis=1, skipna=True)
        # coalesce: the first argument that has a value, left to right.
        result = values[0]
        for other in values[1:]:
            result = result.where(result.notna(), other)
        return result

    def variables(self) -> set[str]:
        return set().union(*(arg.variables() for arg in self.args)) if self.args else set()


def _constant(node: _Node, position: int) -> float:
    """A function argument that has to be a plain number (``round``'s digits)."""
    if isinstance(node, _Num):
        return node.value
    if isinstance(node, _Unary) and isinstance(node.operand, _Num):
        return -node.operand.value
    raise FormulaError("this argument has to be a plain number, not a variable", position)


# ── the parser ───────────────────────────────────────────────────────────────


class _Parser:
    """Recursive descent over the token list.

    Hand-written rather than handed to Python's own parser: the grammar is
    fifteen lines, the error messages have to point at a character for the
    editor to underline, and ``ast.parse`` on somebody else's text is a
    different conversation about depth limits and surprises.
    """

    MAX_DEPTH = 32

    def __init__(self, text: str) -> None:
        self.text = text
        self.tokens = _tokenize(text)
        self.index = 0
        self.depth = 0

    # -- token helpers --

    def _peek(self) -> _Token | None:
        return self.tokens[self.index] if self.index < len(self.tokens) else None

    def _end(self) -> int:
        return len(self.text)

    def _take(self) -> _Token:
        token = self._peek()
        if token is None:
            raise FormulaError("the formula ends in the middle of an expression", self._end())
        self.index += 1
        return token

    def _accept(self, kind: str, text: str | None = None) -> _Token | None:
        token = self._peek()
        if token is None or token.kind != kind:
            return None
        if text is not None and token.text.lower() != text:
            return None
        self.index += 1
        return token

    def _expect(self, kind: str, what: str) -> _Token:
        token = self._peek()
        if token is None:
            raise FormulaError(f"expected {what}, but the formula ends", self._end())
        if token.kind != kind:
            raise FormulaError(f"expected {what}, found {token.text!r}", token.position)
        self.index += 1
        return token

    # -- grammar --

    def parse(self) -> _Node:
        if not self.tokens:
            raise FormulaError("the formula is empty", 0)
        node = self._expression()
        leftover = self._peek()
        if leftover is not None:
            raise FormulaError(f"{leftover.text!r} is left over at the end", leftover.position)
        return node

    def _expression(self) -> _Node:
        self.depth += 1
        if self.depth > self.MAX_DEPTH:
            raise FormulaError("the formula nests too deeply to read", self._end())
        try:
            token = self._peek()
            if token is not None and token.kind == "name" and token.text.lower() == "if":
                return self._conditional()
            return self._or()
        finally:
            self.depth -= 1

    def _conditional(self) -> _Node:
        self._take()  # 'if'
        condition = self._or()
        if self._accept("name", "then") is None:
            token = self._peek()
            raise FormulaError("'if' needs a 'then'", token.position if token else self._end())
        then = self._expression()
        if self._accept("name", "else") is None:
            token = self._peek()
            # Without an else the rows that fail the test have no value, and
            # "no value" should be said out loud rather than defaulted to.
            raise FormulaError(
                "'if … then' needs an 'else' — say what the other rows get",
                token.position if token else self._end(),
            )
        return _IfElse(condition, then, self._expression())

    def _or(self) -> _Node:
        node = self._and()
        while self._accept("name", "or") is not None:
            node = _BoolOp("or", node, self._and())
        return node

    def _and(self) -> _Node:
        node = self._not()
        while self._accept("name", "and") is not None:
            node = _BoolOp("and", node, self._not())
        return node

    def _not(self) -> _Node:
        if self._accept("name", "not") is not None:
            return _Not(self._not())
        return self._comparison()

    def _comparison(self) -> _Node:
        node = self._sum()
        token = self._peek()
        if token is not None and token.kind == "compare":
            self._take()
            if token.text not in _COMPARISONS:  # pragma: no cover - tokenizer guarantees it
                raise FormulaError(f"{token.text!r} is not a comparison", token.position)
            return _Compare(token.text, node, self._sum())
        return node

    def _sum(self) -> _Node:
        node = self._term()
        while True:
            token = self._peek()
            if token is None or token.kind != "op" or token.text not in "+-":
                return node
            self._take()
            node = _BinOp(token.text, node, self._term(), token.position)

    def _term(self) -> _Node:
        node = self._unary()
        while True:
            token = self._peek()
            if token is None or token.kind != "op" or token.text not in "*/":
                return node
            self._take()
            right = self._unary()
            if token.text == "/" and isinstance(right, _Num) and right.value == 0:
                # A literal zero divisor is a typo, not a data condition.
                raise FormulaError("dividing by zero", token.position)
            node = _BinOp(token.text, node, right, token.position)

    def _unary(self) -> _Node:
        token = self._peek()
        if token is not None and token.kind == "op" and token.text == "-":
            self._take()
            return _Unary(self._unary())
        if token is not None and token.kind == "op" and token.text == "+":
            self._take()
            return self._unary()
        return self._atom()

    def _atom(self) -> _Node:
        token = self._take()
        if token.kind == "number":
            return _Num(float(token.text))
        if token.kind == "lparen":
            node = self._expression()
            self._expect("rparen", "a closing ')'")
            return node
        if token.kind == "name":
            lowered = token.text.lower()
            if lowered in _FUNCTIONS:
                return self._call(lowered, token.position)
            if lowered in _KEYWORDS:
                raise FormulaError(f"{token.text!r} cannot start a value here", token.position)
            if self._peek() is not None and self._peek().kind == "lparen":  # type: ignore[union-attr]
                known = ", ".join(sorted(_FUNCTIONS))
                raise FormulaError(
                    f"there is no function called {token.text!r} — the ones there are: {known}",
                    token.position,
                )
            return _Var(token.text, token.position)
        raise FormulaError(f"{token.text!r} cannot start a value", token.position)

    def _call(self, name: str, position: int) -> _Node:
        self._expect("lparen", f"'(' after {name}")
        args: list[_Node] = []
        if self._accept("rparen") is None:
            args.append(self._expression())
            while self._accept("comma") is not None:
                args.append(self._expression())
            self._expect("rparen", f"a closing ')' for {name}")
        low, high = _Call.ARITY[name]
        if name in {"round", "log"} and len(args) > 1:
            # The digits of round and the base of log are properties of the
            # formula, not of the row. Caught here so check_flow reports it
            # before a run rather than the run reporting it after.
            _constant(args[1], position)
        if len(args) < low or (high is not None and len(args) > high):
            wanted = (
                f"{low}" if high == low else (f"{low} or more" if high is None else f"{low}–{high}")
            )
            raise FormulaError(f"{name} takes {wanted} argument(s), not {len(args)}", position)
        return _Call(name, tuple(args), position)


@dataclass(frozen=True)
class Formula:
    """A parsed formula: the text it came from, and what it computes.

    The text is kept because it is what a person wrote and what the generated
    script should show. A rendering of the tree would be a paraphrase.
    """

    text: str
    _root: _Node

    def variables(self) -> set[str]:
        """Every variable the formula reads. Used to check it against a codebook
        before anything runs."""
        return self._root.variables()

    def evaluate(self, frame: pd.DataFrame) -> pd.Series:
        """Compute the formula over a frame, one vectorized pass."""
        result = self._root.evaluate(frame)
        if result.dtype == bool or str(result.dtype) == "boolean":
            # A formula that is just a condition ("age >= 18") is a perfectly
            # good 0/1 indicator; give it as numbers so the variable behaves.
            return result.astype("boolean").astype("Float64").astype("float64")
        return result.astype("float64")

    def __repr__(self) -> str:
        return f"Formula({self.text!r})"


def parse(text: str) -> Formula:
    """Read a formula, or raise :class:`FormulaError` saying where reading stopped."""
    if not isinstance(text, str):
        raise FormulaError("a formula is text")
    if len(text) > 2000:
        raise FormulaError("the formula is too long to be meant seriously", 2000)
    return Formula(text, _Parser(text).parse())


def evaluate(text: str, frame: pd.DataFrame) -> pd.Series:
    """Parse and evaluate in one step (convenience for a one-off)."""
    return parse(text).evaluate(frame)


def check(text: str, known: Sequence[str] | set[str]) -> list[str]:
    """Variables the formula names that the codebook does not have.

    Raises :class:`FormulaError` if the formula cannot be read at all — the
    caller reports one problem or the other, never both at once.
    """
    return sorted(name for name in parse(text).variables() if name not in set(known))
