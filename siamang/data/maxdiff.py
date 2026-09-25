"""Reading a MaxDiff: what people chose, out of what they were shown.

Two numbers, and they answer slightly different questions.

The **counting score** is how often an item was picked as best minus how often
it was picked as worst, over how often it was shown at all: a number between −1
and 1 that anyone can check by hand from the data. It is also the only thing
here available per respondent without a hierarchical model, which is what makes
segmentation possible.

The **utilities** come from a conditional logit over the choices the design
actually put in front of people, with the best pick and then the worst of what
remained treated as two choices. They are on an interval scale, so the distance
between two items means something, and they rescale into shares that sum to a
hundred — which is how the result gets read by people who do not read logs.

Both are reported against a base, and answers that contradict the design are
counted and dropped rather than quietly used: an item picked that the task never
showed is a design that changed after fieldwork, not a preference.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

from siamang.data.choice import ChoiceSets, MnlResult, mnl

if TYPE_CHECKING:
    from siamang.core.question import MaxDiff
    from siamang.data.survey_data import SurveyData

__all__ = [
    "MaxDiffAnswers",
    "ScoredData",
    "answers",
    "choice_sets",
    "counts",
    "question_of",
    "respondent_scores",
    "score_names",
    "utilities",
    "with_scores",
]


@dataclass(frozen=True, slots=True)
class MaxDiffAnswers:
    """One row per (respondent, task) that can be read against the design."""

    frame: pd.DataFrame  # respondent, task, shown (tuple), best, worst
    respondents: int
    dropped: int
    reasons: dict[str, int] = field(default_factory=dict)


def question_of(data: SurveyData, question: MaxDiff | str) -> MaxDiff:
    """Resolve a question by name against the attached questionnaire."""

    from siamang.core.question import MaxDiff as MaxDiffQuestion
    from siamang.core.question import question_output_name

    if isinstance(question, MaxDiffQuestion):
        return question
    if data.questionnaire is None:
        raise ValueError(
            "This SurveyData has no questionnaire attached, so the MaxDiff design cannot be "
            "read. Pass the question itself, or load the data with its questionnaire."
        )
    for candidate in data.questionnaire.all_questions():
        if isinstance(candidate, MaxDiffQuestion) and (
            candidate.id == question or question_output_name(candidate) == question
        ):
            return candidate
    known = [
        question_output_name(c)
        for c in data.questionnaire.all_questions()
        if isinstance(c, MaxDiffQuestion)
    ]
    raise KeyError(
        f"No MaxDiff question named {question!r}. "
        + (f"This questionnaire has: {', '.join(known)}." if known else "It has none.")
    )


def answers(data: SurveyData, question: MaxDiff | str) -> MaxDiffAnswers:
    """The tasks a respondent answered, paired with the items they were shown.

    A row survives only if it can be read: the version has to be known, both
    picks present, both among the items that task showed, and different from
    each other. Everything else is counted by reason — a silent drop here is an
    estimate quietly computed on a subset nobody was told about.
    """

    question = question_of(data, question)
    design = question.resolved_design()
    frame = data.frame
    version_name = question.version_variable.name
    missing = [
        name
        for name in (version_name, *(v.name for v in question.var))
        if name not in frame.columns
    ]
    if missing:
        raise KeyError(
            f"The data has no column {missing[0]!r}. A MaxDiff writes one variable per pick "
            "and one for the design version; without them its answers cannot be read."
        )

    records: list[dict[str, Any]] = []
    reasons = {"no version": 0, "not answered": 0, "not in the task": 0, "same item twice": 0}
    respondents: set[Any] = set()
    for position, (index, row) in enumerate(frame.iterrows()):
        version = row[version_name]
        if pd.isna(version):
            reasons["no version"] += question.tasks
            continue
        respondents.add(index)
        for task in range(question.tasks):
            best_var, worst_var = question.task_variables(task)
            best, worst = row[best_var.name], row[worst_var.name]
            if pd.isna(best) or pd.isna(worst):
                reasons["not answered"] += 1
                continue
            shown = design.task(int(version), task)
            best, worst = _code(best, shown), _code(worst, shown)
            if best is None or worst is None:
                reasons["not in the task"] += 1
                continue
            if best == worst:
                reasons["same item twice"] += 1
                continue
            records.append(
                {
                    "respondent": index,
                    "row": position,
                    "task": task,
                    "shown": tuple(shown),
                    "best": best,
                    "worst": worst,
                }
            )
    columns = ["respondent", "row", "task", "shown", "best", "worst"]
    return MaxDiffAnswers(
        frame=pd.DataFrame(records, columns=columns),
        respondents=len(respondents),
        dropped=sum(reasons.values()),
        reasons={reason: n for reason, n in reasons.items() if n},
    )


def _code(value: Any, shown: tuple[Any, ...]) -> Any | None:
    """Match an answer to one of the codes the task showed.

    A text format brings codes back as strings and a float column as ``3.0``;
    the design holds ``3``. Comparing by string is what keeps a CSV round trip
    from looking like a respondent who chose something they were never offered.
    """

    for code in shown:
        if value == code or str(value) == str(code):
            return code
        if isinstance(value, float) and value.is_integer() and str(int(value)) == str(code):
            return code
    return None


def counts(data: SurveyData, question: MaxDiff | str, *, weight: str | None = None) -> pd.DataFrame:
    """Best minus worst over shown, per item — the score anyone can recount.

    ``score`` runs from −1 (picked worst every single time it appeared) to 1.
    """

    question = question_of(data, question)
    read = answers(data, question)
    labels = _labels(data, question)
    weights = _row_weights(data, weight)

    rows = []
    for code in question.item_codes:
        shown = best = worst = 0.0
        for record in read.frame.itertuples():
            w = weights[record.row] if weights is not None else 1.0
            if code not in record.shown:
                continue
            shown += w
            best += w if record.best == code else 0.0
            worst += w if record.worst == code else 0.0
        rows.append(
            {
                "item": code,
                "label": labels.get(code, str(code)),
                "shown": int(round(shown)),
                "best": int(round(best)),
                "worst": int(round(worst)),
                "score": round((best - worst) / shown, 3) if shown else 0.0,
            }
        )
    out = pd.DataFrame(rows, columns=["item", "label", "shown", "best", "worst", "score"])
    return out.sort_values("score", ascending=False).reset_index(drop=True)


def respondent_scores(data: SurveyData, question: MaxDiff | str) -> pd.DataFrame:
    """The counting score per respondent — individual numbers without a model.

    Coarse, because one respondent sees each item only a few times, but real:
    they carry into a crosstab, a cluster or a regression like any variable.
    """

    question = question_of(data, question)
    read = answers(data, question)
    labels = _labels(data, question)
    rows = []
    for respondent, block in read.frame.groupby("respondent", sort=False):
        for code in question.item_codes:
            shown = sum(1 for record in block.itertuples() if code in record.shown)
            if not shown:
                continue
            best = int((block["best"] == code).sum())
            worst = int((block["worst"] == code).sum())
            rows.append(
                {
                    "respondent": respondent,
                    "item": code,
                    "label": labels.get(code, str(code)),
                    "score": round((best - worst) / shown, 3),
                }
            )
    return pd.DataFrame(rows, columns=["respondent", "item", "label", "score"])


def choice_sets(
    data: SurveyData,
    question: MaxDiff | str,
    *,
    weight: str | None = None,
    coding: str = "sequential",
) -> ChoiceSets:
    """The answers as choice sets: two per task, because two picks were made.

    The worst pick is a choice too — of the *least* preferred — so the same
    utilities enter with the sign flipped, which lets one model use both halves
    of the answer instead of throwing half of it away.

    ``coding`` is where the two halves differ, and it matters enough to be a
    named argument rather than a detail:

    ``sequential`` (the default, and what this engine estimates on) offers the
    worst pick only what was left after the best was taken. That is what the
    respondent actually chose from, and it rules out "worst = best", which the
    data never contains.

    ``paired`` offers the worst pick the whole task again, negated. It is
    slightly the weaker model for exactly the reason above, and it is what the
    export writes, because every task then has the same number of alternatives
    — which is what the R packages that run hierarchical Bayes require.

    Each set carries its respondent's weight — ``weight`` when given, else the
    data's own (:meth:`SurveyData.with_weight`), the same resolution
    :func:`counts` makes, so the counting score and the utilities in one table
    are never on two different samples.
    """

    if coding not in {"sequential", "paired"}:
        raise ValueError("coding must be 'sequential' or 'paired'.")

    question = question_of(data, question)
    read = answers(data, question)
    labels = _labels(data, question)
    items = list(question.item_codes)
    if len(items) < 2:
        raise ValueError("A MaxDiff needs at least two items to compare.")
    reference = items[-1]
    index = {code: i for i, code in enumerate(items[:-1])}
    weights_by_row = _row_weights(data, weight)

    design_rows: list[np.ndarray] = []
    chosen: list[bool] = []
    group: list[int] = []
    set_weights: list[float] = []
    set_id = 0

    def add_set(pool: tuple[Any, ...], picked: Any, sign: float, w: float) -> None:
        nonlocal set_id
        for code in pool:
            row = np.zeros(len(items) - 1)
            if code != reference:
                row[index[code]] = sign
            design_rows.append(row)
            chosen.append(code == picked)
            group.append(set_id)
        set_weights.append(w)
        set_id += 1

    for record in read.frame.itertuples():
        w = float(weights_by_row[record.row]) if weights_by_row is not None else 1.0
        add_set(record.shown, record.best, 1.0, w)
        if coding == "paired":
            add_set(record.shown, record.worst, -1.0, w)
            continue
        remaining = tuple(code for code in record.shown if code != record.best)
        if len(remaining) >= 2:
            add_set(remaining, record.worst, -1.0, w)

    if not design_rows:
        raise ValueError(
            "No MaxDiff answers could be read against the design, so there is nothing to fit."
        )
    return ChoiceSets(
        design=np.array(design_rows),
        chosen=np.array(chosen),
        group=np.array(group),
        names=[labels.get(code, str(code)) for code in items[:-1]],
        weight=np.array(set_weights) if weights_by_row is not None else None,
        reference=labels.get(reference, str(reference)),
    )


def utilities(data: SurveyData, question: MaxDiff | str, *, weight: str | None = None) -> MnlResult:
    """Interval-scale preference for each item, and the shares it implies.

    Weighted by ``weight`` or, without it, by the data's own weight column.
    """

    question = question_of(data, question)
    read = answers(data, question)
    result = mnl(choice_sets(data, question, weight=weight))
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


def _labels(data: SurveyData, question: MaxDiff) -> dict[Any, str]:
    if question.choices:
        return {option.code: option.label for option in question.choices}
    variables = data.variables
    name = question.var[0].name
    if variables is not None and name in variables:
        return dict(variables[name].labels or {})
    return dict(question.var[0].labels or {})


def _row_weights(data: SurveyData, weight: str | None) -> np.ndarray | None:
    column = weight or data.weight
    if column is None:
        return None
    if column not in data.frame.columns:
        raise KeyError(f"column not found: {column!r}")
    return pd.to_numeric(data.frame[column], errors="coerce").fillna(0.0).to_numpy()


@dataclass(frozen=True, slots=True)
class ScoredData:
    """What :func:`with_scores` returns: the data with one score variable per
    item, and what the scores rest on."""

    data: SurveyData
    stats: dict[str, Any] = field(default_factory=dict)
    #: item code -> the variable holding its score, in the question's order.
    names: dict[Any, str] = field(default_factory=dict)


def score_names(question_name: str, codes: list[Any], prefix: str | None = None) -> dict[Any, str]:
    """The variable each item's score is written to: ``<prefix><code>``.

    The default prefix is ``<question>_score_``, from the name the question was
    asked for by — the one name a flow and its check both hold before anything
    runs, so a later node can name ``q_md_score_3`` and be checked against it.
    """

    stem = f"{question_name}_score_" if prefix is None or prefix == "" else prefix
    return {code: f"{stem}{code}" for code in codes}


def with_scores(
    data: SurveyData, question: MaxDiff | str, *, prefix: str | None = None
) -> ScoredData:
    """The counting score of every item, per respondent, as variables.

    The same number :func:`respondent_scores` gives in long form — best minus
    worst over the times the item was shown to *this* respondent, from −1 to 1
    — but one column per item, unrounded, labelled with the item and registered
    in the codebook, so it can go straight into a crosstab, a cluster or a
    regression. A respondent who was never shown an item has no score for it
    (a blank, not a zero: "never picked" and "never offered" are different
    answers), and one with no readable task has none at all.

    The scores are per respondent, so no weight enters them; weight the
    variables where they are summarized. ``stats`` names the base, the
    unreadable answers and — on weighted data — says the weight is not applied.
    """

    from siamang.core.question import question_output_name
    from siamang.core.variable import Variable, VariableMap
    from siamang.data.analysis import unweighted_note
    from siamang.data.survey_data import SurveyData as _SurveyData

    resolved = question_of(data, question)
    read = answers(data, resolved)
    labels = _labels(data, resolved)
    codes = list(resolved.item_codes)
    if not codes:
        raise ValueError("This MaxDiff has no items, so there is nothing to score.")
    asked_for = question if isinstance(question, str) else question_output_name(resolved)
    names = score_names(asked_for, codes, prefix)

    frame = data.frame
    ours = set(names.values())
    for name in sorted(ours & set(frame.columns)):
        existing = data.variables.get(name) if data.variables is not None else None
        if existing is None or existing.role != "derived":
            raise ValueError(
                f"The score of an item would be written to {name!r}, which the data already "
                "holds. Give the node another prefix."
            )

    position = {code: i for i, code in enumerate(codes)}
    shape = (len(frame), len(codes))
    shown, best, worst = np.zeros(shape), np.zeros(shape), np.zeros(shape)
    for record in read.frame.itertuples():
        for code in record.shown:
            if code in position:
                shown[record.row, position[code]] += 1
        if record.best in position:
            best[record.row, position[record.best]] += 1
        if record.worst in position:
            worst[record.row, position[record.worst]] += 1
    with np.errstate(divide="ignore", invalid="ignore"):
        scores = np.where(shown > 0, (best - worst) / shown, np.nan)

    out = frame.copy()
    variables = VariableMap()
    if data.variables is not None:
        for existing in data.variables.values():
            if existing.name not in ours:
                variables.add(existing)
    text = resolved.text or asked_for
    for code, name in names.items():
        out[name] = scores[:, position[code]]
        label = labels.get(code, str(code))
        variables.add(
            Variable(
                name,
                "interval",
                label=f"MaxDiff score: {label}",
                role="derived",
                valid_range=(-1, 1),
                description=(
                    f"Best minus worst over times shown, per respondent, for item {code!r} "
                    f"({label}) of {text}"
                ),
            )
        )
    scored = int((shown.sum(axis=1) > 0).sum())
    listed = list(names.values())
    stats: dict[str, Any] = {
        "Question": text,
        "Respondents scored": scored,
        "Not scored": int(len(frame) - scored),
        "Items": len(codes),
        "Variables": listed[0] if len(listed) == 1 else f"{listed[0]} … {listed[-1]}",
        "Score": "best minus worst over times shown, −1 to 1; blank where never shown",
    }
    if read.dropped:
        stats["Unreadable answers"] = (
            f"{read.dropped} ("
            + ", ".join(f"{reason}: {n}" for reason, n in read.reasons.items())
            + ")"
        )
    if data.weight is not None:
        stats["Weight"] = unweighted_note(data.weight)
    result = _SurveyData(
        frame=out, variables=variables, questionnaire=data.questionnaire, weight=data.weight
    )
    return ScoredData(data=result, stats=stats, names=names)
