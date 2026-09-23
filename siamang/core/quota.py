"""Quota control primitives."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from siamang.core.questionnaire import Questionnaire


@dataclass(frozen=True, slots=True)
class Quota:
    variable: str
    target_value: Any
    limit: int

    def reached(self, answers: list[dict[str, Any]]) -> bool:
        matched = sum(1 for row in answers if row.get(self.variable) == self.target_value)
        return matched >= self.limit


def validate_options(survey: Questionnaire, options: Mapping[str, Any] | None) -> None:
    """Check the compiler options dict against the questionnaire it belongs to.

    Quotas are not stored on the :class:`Questionnaire` — they reach the compiler
    as ``options["quota"]`` — so nothing else ever cross-checks them against the
    survey. A quota naming a variable that does not exist matches no response,
    so its cell never fills and fieldwork runs past the target it was meant to
    cap. Raises :class:`ValueError` on the first problem found.
    """

    if options is None:
        return
    if not isinstance(options, Mapping):
        raise ValueError(f"Compiler options must be a dict, got {type(options).__name__}.")
    if "quota" not in options and "quotas" in options:
        raise ValueError(
            "Compiler options use key 'quotas'; the compiler reads 'quota'. "
            "Rename it or the quotas are ignored."
        )

    quotas = options.get("quota") or []
    if not quotas:
        return

    variables = {
        variable.name: variable
        for question in survey.all_questions()
        for variable in (question.var if isinstance(question.var, list) else [question.var])
    }
    if survey.variables:
        for name, variable in survey.variables.items():
            variables.setdefault(name, variable)
    # An arm drawn by `Script.assign_condition` is a variable too — the one a
    # balanced assignment needs a quota cell per arm on — and its categories are
    # the arm codes.
    arms_of: dict[str, list[Any]] = {}
    for script in getattr(survey, "scripts", []):
        assigned = getattr(script, "assigns", None)
        if assigned and assigned not in variables:
            arms_of[assigned] = [arm[0] for arm in (script.context or {}).get("arms", [])]

    seen: list[tuple[str, Any]] = []
    for quota in quotas:
        if not isinstance(quota, Quota):
            raise ValueError(
                f"options['quota'] must contain Quota objects, got {type(quota).__name__}."
            )
        bound = variables.get(quota.variable)
        if bound is None and quota.variable in arms_of:
            codes = arms_of[quota.variable]
            if not any(_same_code(code, quota.target_value) for code in codes):
                known = ", ".join(str(code) for code in codes)
                raise ValueError(
                    f"Quota on '{quota.variable}' targets value {quota.target_value}, "
                    f"which is not one of its arms ({known})"
                )
        elif bound is None:
            raise ValueError(f"Quota references unknown variable: {quota.variable}")
        # An empty codebook means there is nothing to check against — a quota on
        # an unlabelled variable (an external panel code, say) stays legal.
        elif bound.labels and not any(code == quota.target_value for code in bound.labels):
            known = ", ".join(str(code) for code in bound.labels)
            raise ValueError(
                f"Quota on '{quota.variable}' targets value {quota.target_value}, "
                f"which is not a defined category ({known})"
            )
        if quota.limit <= 0:
            raise ValueError(
                f"Quota on '{quota.variable}' value {quota.target_value} "
                f"has limit {quota.limit}; limit must be > 0"
            )
        key = (quota.variable, quota.target_value)
        if any(key == existing for existing in seen):
            raise ValueError(f"Duplicate quota for '{quota.variable}' value {quota.target_value}.")
        seen.append(key)


def _same_code(code: Any, value: Any) -> bool:
    """Arm codes come from a script's context and the quota's value from a
    document, so `1` and `"1"` are the same arm."""

    return code == value or str(code) == str(value)
