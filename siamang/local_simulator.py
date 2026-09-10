"""Local synthetic response simulator for questionnaires."""

from __future__ import annotations

import random
from typing import Any

import pandas as pd

from siamang.core.expression import Expression
from siamang.core.page import Page
from siamang.core.question import (
    LikertScale,
    Matrix,
    MultiChoice,
    NumericInput,
    OpenText,
    Question,
    Ranking,
    SingleChoice,
)


def _simulate_value(question: Question, var=None):
    """Simulate a single value for a question (or a specific variable within a Matrix)."""
    if isinstance(question, NumericInput):
        v = var or question.var
        if hasattr(v, "valid_range") and v.valid_range:
            lo, hi = v.valid_range
            return random.randint(int(lo), int(hi))
        return random.randint(18, 70)
    if isinstance(question, LikertScale):
        return random.choice(question.values)
    if isinstance(question, Matrix):
        # For Matrix, simulate based on the variable's labels (Likert-like)
        v = var or (question.var[0] if question.var else None)
        if v and v.labels:
            return random.choice(list(v.labels.keys()))
        return random.randint(1, 5)
    if isinstance(question, SingleChoice):
        codes = _choice_codes(question)
        if codes:
            return random.choice(codes)
        return 1
    if isinstance(question, MultiChoice) and question.mode == "array":
        return _simulate_array_multichoice(question)
    if isinstance(question, Ranking):
        codes = _choice_codes(question)
        if codes:
            max_ranked = question.max_ranked or len(codes)
            count = random.randint(1, min(max_ranked, len(codes)))
            return random.sample(codes, count)
        return [1]
    if isinstance(question, OpenText):
        return _simulate_text(question.format)
    return None


def _simulate_text(fmt: str) -> str:
    """A plausible answer for an OpenText of the given format."""
    if fmt == "email":
        return f"respondent{random.randint(1, 999)}@example.com"
    if fmt == "phone":
        return f"+1 555 {random.randint(100, 999)} {random.randint(1000, 9999)}"
    if fmt == "url":
        return f"https://example.com/{random.randint(1, 999)}"
    if fmt == "date":
        return (
            f"{random.randint(1960, 2010)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"
        )
    if fmt == "time":
        return f"{random.randint(0, 23):02d}:{random.randint(0, 59):02d}"
    return "sample text"


def _choice_codes(question: Question) -> list:
    """Return the option codes a respondent could choose, preferring the
    question's explicit ``choices`` list over the bound Variable.labels."""

    explicit = getattr(question, "choices", None)
    if explicit:
        return [opt.code for opt in explicit]
    labels = getattr(question.var, "labels", {})
    return list(labels.keys()) if labels else []


def _simulate_array_multichoice(question: MultiChoice) -> list:
    choices = _choice_codes(question) or [1]
    max_answers = min(question.max_answers or len(choices), len(choices))
    min_answers = min(question.min_answers, max_answers)
    count = random.randint(min_answers, max_answers) if max_answers > 0 else 0
    selected = random.sample(choices, count) if count else []
    exclusive_selected = [value for value in selected if value in question.exclusive]
    if exclusive_selected:
        return [exclusive_selected[0]]
    return selected


def _simulate_wide_multichoice(question: MultiChoice) -> dict[str, int]:
    variables = question.var
    max_answers = min(question.max_answers or len(variables), len(variables))
    min_answers = min(question.min_answers, max_answers)
    count = random.randint(min_answers, max_answers) if max_answers > 0 else 0
    selected = (
        set(random.sample([variable.name for variable in variables], count)) if count else set()
    )
    return {variable.name: int(variable.name in selected) for variable in variables}


def _evaluate_condition(condition: Any, answers: dict[str, Any]) -> bool:
    """Evaluate a show_if/hide_if condition against the current row answers.

    Returns True if the condition is met (i.e., the item should be shown).
    Returns True (show) if condition is None.
    """
    if condition is None:
        return True
    if isinstance(condition, Expression):
        try:
            return condition.evaluate(answers)
        except (TypeError, ValueError, KeyError):
            # If evaluation fails (e.g., missing variable), default to not showing
            return False
    # String expressions cannot be evaluated; default to showing
    return True


def _question_variable_names(question: Question) -> list[str]:
    """Get all variable names produced by a question."""
    if (
        isinstance(question, MultiChoice)
        and question.mode == "wide"
        or isinstance(question.var, list)
    ):
        return [v.name for v in question.var]
    else:
        return [question.var.name]


def _simulate_question_into_row(question: Question, row: dict[str, Any]) -> None:
    """Simulate a single question's value(s) and write into the row dict."""
    if isinstance(question, MultiChoice) and question.mode == "wide":
        row.update(_simulate_wide_multichoice(question))
    elif isinstance(question.var, list):
        for var in question.var:
            row[var.name] = _simulate_value(question, var=var)
    else:
        row[question.var.name] = _simulate_value(question)


def _set_question_missing(question: Question, row: dict[str, Any]) -> None:
    """Set all variables for a question to None (missing/NaN)."""
    if (
        isinstance(question, MultiChoice)
        and question.mode == "wide"
        or isinstance(question.var, list)
    ):
        for var in question.var:
            row[var.name] = None
    else:
        row[question.var.name] = None


def simulate_dataframe(
    questions: list[Question], n: int = 100, seed: int | None = 42
) -> pd.DataFrame:
    """Simulate responses without page-level visibility (legacy flat mode).

    This function is kept for backward compatibility. For page-aware simulation
    that respects show_if/hide_if on pages, use ``simulate_from_pages()``.
    """
    if seed is not None:
        random.seed(seed)
    rows = []
    for _ in range(n):
        row: dict[str, Any] = {}
        for q in questions:
            _simulate_question_into_row(q, row)
        rows.append(row)
    return pd.DataFrame(rows)


def _answered(question: Question, row: dict[str, Any]) -> bool:
    names = _question_variable_names(question)
    return any(row.get(name) not in (None, [], "") for name in names)


def _route_target(page: Page, row: dict[str, Any], visible: list[Question]) -> str | None:
    """Where "Next" lands from ``page`` — the runtime's rules, in order:
    ``skip_to`` on the first answered visible question, the first matching
    ``next_if`` rule, ``default_next``; ``None`` means the next page in
    sequence."""
    for question in visible:
        if question.skip_to and _answered(question, row):
            return question.skip_to
    for condition, target in page.next_if:
        if isinstance(condition, Expression) and _evaluate_condition(condition, row):
            return target
    if page.default_next is not None:
        return page.default_next
    return None


def simulate_from_pages(
    pages: list[Page], n: int = 100, seed: int | None = 42, *, routing: bool = True
) -> pd.DataFrame:
    """Simulate responses respecting visibility and — with ``routing`` —
    the questionnaire's navigation.

    Each simulated respondent starts on the first page and moves the way
    the runtime would: a page's ``show_if`` / ``hide_if`` decides whether it
    is answered (a hidden page is passed over — that is how a screen-out
    placed mid-questionnaire stays out of the way of those who qualify),
    a question's ``skip_to``, the page's ``next_if`` rules and
    ``default_next`` decide where "Next" lands, and a visible terminal page
    (screen-out, final, redirect) ends the interview. Pages never reached
    stay missing, so a screen-out really leaves the later variables empty
    and a branch really splits the sample. ``routing=False`` walks every
    page in document order (the previous behavior).
    """
    if seed is not None:
        random.seed(seed)

    # Collect all variable names across all pages to ensure consistent columns
    all_var_names: list[str] = []
    for page in pages:
        for q in page.flatten_questions():
            all_var_names.extend(_question_variable_names(q))
    by_name = {page.name: index for index, page in enumerate(pages)}

    rows = []
    for _ in range(n):
        row: dict[str, Any] = {name: None for name in all_var_names}
        index = 0
        steps = 0
        while 0 <= index < len(pages) and steps <= 2 * len(pages):
            steps += 1
            page = pages[index]
            page_visible = _evaluate_condition(page.show_if, row) and not (
                page.hide_if is not None and _evaluate_condition(page.hide_if, row)
            )
            visible: list[Question] = []
            for q in page.flatten_questions():
                q_visible = (
                    page_visible
                    and _evaluate_condition(q.show_if, row)
                    and not (q.hide_if is not None and _evaluate_condition(q.hide_if, row))
                )
                if q_visible:
                    _simulate_question_into_row(q, row)
                    visible.append(q)
                else:
                    _set_question_missing(q, row)
            if not routing:
                index += 1
                continue
            if page_visible and page.is_terminal:
                break
            target = _route_target(page, row, visible) if page_visible else None
            # Like the runtime: a routed target, else the next page in order
            # (a hidden page is passed over, a visible terminal page ends it).
            index = by_name[target] if target is not None and target in by_name else index + 1
        rows.append(row)

    return pd.DataFrame(rows)
