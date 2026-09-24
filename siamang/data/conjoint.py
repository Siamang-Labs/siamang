"""Reading a choice-based conjoint: what people gave up to get what.

Three things come out of a conjoint, and they answer different questions.

**Part-worths** are how much each level is worth, in the same units as every
other level of every other attribute — which is the whole point of the method.
They are read against the first level of their own attribute, which sits at
zero, because choice data says how much better one thing is than another and
nothing about the level.

**Importance** is what the client asks for: how much of the decision each
attribute accounts for. It is the range of an attribute's part-worths as a share
of all the ranges added up, and it means what it says only for the levels that
were actually shown — an attribute tested from £10 to £12 will look unimportant
next to one tested from £10 to £100, and that is a fact about the design rather
than about the market.

**Shares of preference** are what the part-worths predict a market would do.
They come from putting hypothetical products through the same model, which is
the only honest way to answer "what if we changed the price": the alternative is
reading part-worths aloud and guessing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

from siamang.data.choice import ChoiceSets, MnlResult, mnl

if TYPE_CHECKING:
    from siamang.core.question import Conjoint
    from siamang.data.survey_data import SurveyData

__all__ = [
    "ConjointAnswers",
    "answers",
    "choice_sets",
    "importance",
    "part_worths",
    "question_of",
    "shares",
]

#: The name of the "none of these" alternative in every table that reports it.
NONE = "(none)"


@dataclass(frozen=True, slots=True)
class ConjointAnswers:
    """One row per (respondent, task) that can be read against the design."""

    frame: pd.DataFrame  # respondent, row, task, profiles, chosen
    respondents: int
    dropped: int
    reasons: dict[str, int] = field(default_factory=dict)


def question_of(data: SurveyData, question: Conjoint | str) -> Conjoint:
    """Resolve a question by name against the attached questionnaire."""

    from siamang.core.question import Conjoint as ConjointQuestion
    from siamang.core.question import question_output_name

    if isinstance(question, ConjointQuestion):
        return question
    if data.questionnaire is None:
        raise ValueError(
            "This SurveyData has no questionnaire attached, so the conjoint design cannot be "
            "read. Pass the question itself, or load the data with its questionnaire."
        )
    for candidate in data.questionnaire.all_questions():
        if isinstance(candidate, ConjointQuestion) and (
            candidate.id == question or question_output_name(candidate) == question
        ):
            return candidate
    known = [
        question_output_name(c)
        for c in data.questionnaire.all_questions()
        if isinstance(c, ConjointQuestion)
    ]
    raise KeyError(
        f"No conjoint question named {question!r}. "
        + (f"This questionnaire has: {', '.join(known)}." if known else "It has none.")
    )


def answers(data: SurveyData, question: Conjoint | str) -> ConjointAnswers:
    """The tasks a respondent answered, paired with the products they were shown."""

    question = question_of(data, question)
    design = question.resolved_design()
    frame = data.frame
    names = [question.version_variable.name, *(v.name for v in question.var)]
    missing = [name for name in names if name not in frame.columns]
    if missing:
        raise KeyError(
            f"The data has no column {missing[0]!r}. A conjoint writes one variable per task "
            "and one for the design version; without them its answers cannot be read."
        )

    highest = question.alternatives + (1 if question.none_label else 0)
    records: list[dict[str, Any]] = []
    reasons = {"no version": 0, "not answered": 0, "not an alternative shown": 0}
    respondents: set[Any] = set()
    for position, (index, row) in enumerate(frame.iterrows()):
        version = row[question.version_variable.name]
        if pd.isna(version):
            reasons["no version"] += question.tasks
            continue
        respondents.add(index)
        for task in range(question.tasks):
            answer = row[question.task_variable(task).name]
            if pd.isna(answer):
                reasons["not answered"] += 1
                continue
            try:
                chosen = int(answer)
            except (TypeError, ValueError):
                reasons["not an alternative shown"] += 1
                continue
            if not 1 <= chosen <= highest:
                reasons["not an alternative shown"] += 1
                continue
            records.append(
                {
                    "respondent": index,
                    "row": position,
                    "task": task,
                    "profiles": design.task(int(version), task),
                    "chosen": chosen,
                }
            )
    return ConjointAnswers(
        frame=pd.DataFrame(records, columns=["respondent", "row", "task", "profiles", "chosen"]),
        respondents=len(respondents),
        dropped=sum(reasons.values()),
        reasons={reason: n for reason, n in reasons.items() if n},
    )


def _terms(question: Conjoint) -> tuple[list[str], list[tuple[int, Any]]]:
    """Column names of the design matrix, and which (attribute, level) each is.

    The first level of each attribute is the reference and gets no column, so a
    part-worth is read as "against that level".
    """

    names: list[str] = []
    keys: list[tuple[int, Any]] = []
    for index, attribute in enumerate(question.attributes):
        for level in attribute.levels[1:]:
            names.append(f"{attribute.label or attribute.name}: {level.label}")
            keys.append((index, level.code))
    return names, keys


def _row(question: Conjoint, profile: Any, keys: list[tuple[int, Any]], none: bool) -> np.ndarray:
    row = np.zeros(len(keys) + (1 if none else 0))
    if profile is None:  # the "none of these" alternative
        if none:
            row[-1] = 1.0
        return row
    for position, (attribute, code) in enumerate(keys):
        if profile[attribute] == code:
            row[position] = 1.0
    return row


def choice_sets(
    data: SurveyData, question: Conjoint | str, *, weight: str | None = None
) -> ChoiceSets:
    """The answers as choice sets: one per task, the alternatives as rows.

    Each set carries its respondent's weight: ``weight`` when given, else the
    data's own (:meth:`SurveyData.with_weight`).
    """

    question = question_of(data, question)
    read = answers(data, question)
    names, keys = _terms(question)
    none = question.none_label is not None
    if none:
        # "None of these" is an alternative with its own utility, not a missing
        # answer: without a column for it, refusing to buy would be modeled as
        # indifference between the products on offer.
        names = [*names, NONE]
    weights_by_row = _row_weights(data, weight)

    design_rows: list[np.ndarray] = []
    chosen: list[bool] = []
    group: list[int] = []
    set_weights: list[float] = []
    for set_id, record in enumerate(read.frame.itertuples()):
        profiles: list[Any] = [*record.profiles]
        if none:
            profiles.append(None)
        for position, profile in enumerate(profiles):
            design_rows.append(_row(question, profile, keys, none))
            chosen.append(position + 1 == record.chosen)
            group.append(set_id)
        set_weights.append(float(weights_by_row[record.row]) if weights_by_row is not None else 1.0)

    if not design_rows:
        raise ValueError(
            "No conjoint answers could be read against the design, so there is nothing to fit."
        )
    # The zero is the reference *product* — every attribute at its first level —
    # whether or not a "none" alternative exists. "None" is an estimated
    # alternative with a coefficient of its own, not the baseline.
    return ChoiceSets(
        design=np.array(design_rows),
        chosen=np.array(chosen),
        group=np.array(group),
        names=names,
        weight=np.array(set_weights) if weights_by_row is not None else None,
        reference=_reference_label(question),
    )


def _reference_label(question: Conjoint) -> str:
    parts = [f"{a.label or a.name}: {a.levels[0].label}" for a in question.attributes]
    return " + ".join(parts)


def part_worths(
    data: SurveyData, question: Conjoint | str, *, weight: str | None = None
) -> MnlResult:
    """How much each level is worth, in one currency across all attributes.

    Weighted by ``weight`` or, without it, by the data's own weight column —
    and so are :func:`importance` and :func:`shares`, which are read off this.
    """

    question = question_of(data, question)
    read = answers(data, question)
    # No share column: a level is not an alternative, and the number would be
    # read as one. Shares of preference are what `shares()` is for.
    result = mnl(choice_sets(data, question, weight=weight), shares=False)
    column = weight or data.weight
    if column:
        result.stats["weight"] = column
    result.stats["respondents"] = read.respondents
    result.stats["tasks_used"] = int(len(read.frame))
    if read.dropped:
        result.stats["dropped"] = read.dropped
        result.stats["dropped_because"] = ", ".join(
            f"{reason}: {n}" for reason, n in read.reasons.items()
        )
    return result


def _utilities(question: Conjoint, result: MnlResult) -> dict[tuple[int, Any], float]:
    """Every level's utility, including the reference levels sitting at zero."""

    names, keys = _terms(question)
    estimate = dict(zip(result.table["term"], result.table["estimate"], strict=True))
    utilities = {key: float(estimate.get(name, 0.0)) for name, key in zip(names, keys, strict=True)}
    for index, attribute in enumerate(question.attributes):
        utilities.setdefault((index, attribute.levels[0].code), 0.0)
        utilities[(index, attribute.levels[0].code)] = 0.0
    return utilities


def importance(
    data: SurveyData, question: Conjoint | str, *, weight: str | None = None
) -> pd.DataFrame:
    """How much of the decision each attribute accounted for, as a percentage.

    The range of an attribute's part-worths over the sum of all the ranges. It
    is a statement about *the levels that were shown*: price tested from £10 to
    £12 will look unimportant beside one tested from £10 to £100, which is a
    fact about the design and not about the market. The table carries the range
    it was computed from so that is checkable rather than implied.
    """

    question = question_of(data, question)
    result = part_worths(data, question, weight=weight)
    utilities = _utilities(question, result)
    rows = []
    for index, attribute in enumerate(question.attributes):
        values = [utilities[(index, level.code)] for level in attribute.levels]
        rows.append(
            {
                "attribute": attribute.label or attribute.name,
                "levels": len(attribute.levels),
                "best": attribute.label_of(attribute.levels[int(np.argmax(values))].code),
                "worst": attribute.label_of(attribute.levels[int(np.argmin(values))].code),
                "range": round(max(values) - min(values), 4),
            }
        )
    total = sum(row["range"] for row in rows)
    for row in rows:
        row["importance"] = round(row["range"] / total * 100, 1) if total else 0.0
    out = pd.DataFrame(
        rows, columns=["attribute", "levels", "best", "worst", "range", "importance"]
    )
    return out.sort_values("importance", ascending=False).reset_index(drop=True)


def shares(
    data: SurveyData,
    question: Conjoint | str,
    products: dict[str, dict[str, Any]] | list[dict[str, Any]],
    *,
    weight: str | None = None,
    include_none: bool = False,
) -> pd.DataFrame:
    """What the estimated utilities predict a market of these products would do.

    ``products`` maps a name to one level code per attribute. Shares are of the
    products offered, which is why ``include_none`` exists: with a "none of
    these" alternative in the question, a market can also be left, and leaving
    that out silently rescales everyone who would have walked away into buyers.
    """

    question = question_of(data, question)
    result = part_worths(data, question, weight=weight)
    utilities = _utilities(question, result)
    named = (
        products
        if isinstance(products, dict)
        else {f"Product {i + 1}": product for i, product in enumerate(products)}
    )
    by_name = {attribute.name: index for index, attribute in enumerate(question.attributes)}

    totals: dict[str, float] = {}
    for name, product in named.items():
        unknown = set(product) - set(by_name)
        if unknown:
            raise KeyError(
                f"{name}: {sorted(unknown)[0]!r} is not an attribute of this conjoint "
                f"({', '.join(by_name)})."
            )
        missing = set(by_name) - set(product)
        if missing:
            raise KeyError(
                f"{name} has no level for {sorted(missing)[0]!r}. A product is one level of "
                "every attribute — a half-specified one has no utility."
            )
        total = 0.0
        for attribute_name, code in product.items():
            index = by_name[attribute_name]
            if (index, code) not in utilities:
                codes = ", ".join(map(str, question.attributes[index].codes))
                raise KeyError(f"{name}: {attribute_name}={code!r} is not a level ({codes}).")
            total += utilities[(index, code)]
        totals[name] = total

    if include_none:
        if question.none_label is None:
            raise ValueError(
                "This conjoint has no 'none of these' alternative, so there is no estimate of "
                "how many would buy nothing."
            )
        estimate = dict(zip(result.table["term"], result.table["estimate"], strict=True))
        totals[question.none_label] = float(estimate.get(NONE, 0.0))

    values = np.array(list(totals.values()))
    exponent = np.exp(values - values.max())
    share = exponent / exponent.sum() if exponent.sum() else exponent
    return (
        pd.DataFrame(
            {
                "product": list(totals),
                "utility": np.round(values, 4),
                "share": np.round(share * 100, 1),
            }
        )
        .sort_values("share", ascending=False)
        .reset_index(drop=True)
    )


def _row_weights(data: SurveyData, weight: str | None) -> np.ndarray | None:
    column = weight or data.weight
    if column is None:
        return None
    if column not in data.frame.columns:
        raise KeyError(f"column not found: {column!r}")
    return pd.to_numeric(data.frame[column], errors="coerce").fillna(0.0).to_numpy()
