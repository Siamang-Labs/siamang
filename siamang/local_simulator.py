"""Local synthetic response simulator for questionnaires."""

from __future__ import annotations

import random

import pandas as pd

from siamang.core.question import (
    LikertScale,
    MultiChoice,
    NumericInput,
    OpenText,
    Question,
    SingleChoice,
)


def _simulate_value(question: Question):
    if isinstance(question, NumericInput):
        return random.randint(18, 70)
    if isinstance(question, LikertScale):
        return random.randint(1, question.points)
    if isinstance(question, SingleChoice):
        codes = _choice_codes(question)
        if codes:
            return random.choice(codes)
        return 1
    if isinstance(question, MultiChoice) and question.mode == "array":
        return _simulate_array_multichoice(question)
    if isinstance(question, OpenText):
        return "sample text"
    return None


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
        set(random.sample([variable.name for variable in variables], count))
        if count
        else set()
    )
    return {variable.name: int(variable.name in selected) for variable in variables}


def simulate_dataframe(
    questions: list[Question], n: int = 100, seed: int | None = 42
) -> pd.DataFrame:
    if seed is not None:
        random.seed(seed)
    rows = []
    for _ in range(n):
        row = {}
        for q in questions:
            if isinstance(q, MultiChoice) and q.mode == "wide":
                row.update(_simulate_wide_multichoice(q))
            elif isinstance(q.var, list):
                for var in q.var:
                    row[var.name] = _simulate_value(q)
            else:
                row[q.var.name] = _simulate_value(q)
        rows.append(row)
    return pd.DataFrame(rows)
