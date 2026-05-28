"""Compile Expression AST into the SurveyJS visibleIf string language."""

from __future__ import annotations

from typing import Any

from siamang.core.expression import Expression, VarRef


def compile_expression(expression: Any) -> str | None:
    """Render an Expression / string condition into a SurveyJS expression.

    Accepts:
    - ``None`` -> returns ``None`` (no condition)
    - ``str``  -> returned unchanged (legacy raw expressions)
    - :class:`Expression` -> compiled via ``to_surveyjs``
    """

    if expression is None:
        return None
    if isinstance(expression, str):
        return expression
    if isinstance(expression, Expression):
        return expression.to_surveyjs()
    if isinstance(expression, VarRef):
        return str(expression)
    raise TypeError(
        f"Cannot compile expression of type {type(expression).__name__}; "
        "expected Expression, VarRef, str, or None."
    )


def expression_variables(expression: Any) -> set[str]:
    """Return the set of variable names referenced by an expression."""

    if expression is None or isinstance(expression, str):
        return set()
    if isinstance(expression, (Expression, VarRef)):
        return expression.variables()
    raise TypeError(
        f"Cannot extract variables from {type(expression).__name__}; "
        "expected Expression, VarRef, str, or None."
    )
