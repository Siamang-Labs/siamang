"""Local synthetic response simulator for questionnaires.

Each simulated respondent moves through the questionnaire the way the runtime
would move a real one, so the frame has the shape real data will have: the
same columns, the same holes where a condition hid a question, a branch sent
someone elsewhere or a screen-out ended the interview.

What is replayed: page, block and question ``show_if`` / ``hide_if``, answer
options' ``show_if`` / ``hide_if``, ``skip_to``, ``next_if`` and
``default_next``, terminal pages, and — given the questionnaire's scripts and
quotas — the arm ``Script.assign_condition`` draws (balanced against the
quotas when it asks to be), the page order ``Script.randomize_pages`` deals,
and quota cells that close once their completes reach the limit. Block
shuffles only change which ``skip_to`` is met first; option shuffles change
nothing in the data and are not drawn. Other scripts are JavaScript and are
not run. Every draw comes from one generator seeded once, so a seed gives the
same frame every time.
"""

from __future__ import annotations

import random
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import pandas as pd

from siamang.core.block import Block
from siamang.core.expression import Expression
from siamang.core.page import Page
from siamang.core.question import (
    Conjoint,
    LikertScale,
    Matrix,
    MaxDiff,
    MultiChoice,
    NumericInput,
    OpenText,
    Question,
    Ranking,
    SingleChoice,
)

if TYPE_CHECKING:
    from siamang.core.questionnaire import Questionnaire
    from siamang.core.quota import Quota
    from siamang.core.script import Script
    from siamang.data.survey_data import SurveyData


def _simulate_value(question: Question, var=None, answers: dict[str, Any] | None = None):
    """Simulate a single value for a question (or a specific variable within a Matrix).

    ``answers`` — what this respondent has answered so far — decides which
    answer options are on offer: an option whose ``show_if`` / ``hide_if``
    hides it is never picked, and a question whose options are all hidden is
    left unanswered (None), as nothing could be chosen.
    """
    if isinstance(question, NumericInput):
        v = var or question.var
        # A half-open range is ordinary — "16 or older" is written (16, None) —
        # so an absent bound means unbounded, not zero. int(None) used to raise
        # here and take the whole simulation down with it.
        low, high = getattr(v, "valid_range", None) or (None, None)
        low = int(low) if low is not None else 18
        high = int(high) if high is not None else max(low + 1, 70)
        return random.randint(low, high)
    if isinstance(question, LikertScale):
        return random.choice(question.values)
    if isinstance(question, Matrix):
        # For Matrix, simulate based on the variable's labels (Likert-like)
        v = var or (question.var[0] if question.var else None)
        if v and v.labels:
            return random.choice(list(v.labels.keys()))
        return random.randint(1, 5)
    if isinstance(question, SingleChoice):
        codes = _choice_codes(question, answers)
        if codes:
            return random.choice(codes)
        return None if _has_options(question) else 1
    if isinstance(question, MultiChoice) and question.mode == "array":
        return _simulate_array_multichoice(question, answers)
    if isinstance(question, Ranking):
        codes = _choice_codes(question, answers)
        if codes:
            max_ranked = question.max_ranked or len(codes)
            count = random.randint(1, min(max_ranked, len(codes)))
            return random.sample(codes, count)
        return None if _has_options(question) else [1]
    if isinstance(question, OpenText):
        return _simulate_text(question.format)
    if isinstance(question, Conjoint):
        return _simulate_conjoint(question)
    if isinstance(question, MaxDiff):
        # The whole answer at once — best and worst have to come from the same
        # task's items and cannot be the same item, so simulating one variable
        # at a time would produce combinations the design never showed.
        return _simulate_maxdiff(question)
    return None


def _simulate_conjoint(question: Conjoint) -> dict[str, Any]:
    """A version of the design, then one alternative picked per task."""

    design = question.resolved_design()
    version = random.randrange(len(design.versions))
    answer: dict[str, Any] = {question.version_variable.name: version}
    highest = question.alternatives + (1 if question.none_label else 0)
    for index in range(question.tasks):
        answer[question.task_variable(index).name] = random.randint(1, highest)
    return answer


def _simulate_maxdiff(question: MaxDiff) -> dict[str, Any]:
    """One respondent's picks: a version of the design, then best and worst.

    Draws only from the items each task actually showed, which is what makes
    simulated MaxDiff data usable for checking an estimator: feed it known
    utilities and the recovered ones should match.
    """

    design = question.resolved_design()
    version = random.randrange(len(design.versions))
    answer: dict[str, Any] = {question.version_variable.name: version}
    for index in range(question.tasks):
        shown = list(design.task(version, index))
        if len(shown) < 2:
            continue
        best, worst = random.sample(shown, 2)
        best_var, worst_var = question.task_variables(index)
        answer[best_var.name] = best
        answer[worst_var.name] = worst
    return answer


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


def _choice_codes(question: Question, answers: dict[str, Any] | None = None) -> list:
    """Return the option codes a respondent could choose, preferring the
    question's explicit ``choices`` list over the bound Variable.labels.

    With ``answers``, an explicit option hidden by its own ``show_if`` /
    ``hide_if`` is not among them — the runtime does not render it.
    """

    explicit = getattr(question, "choices", None)
    if explicit:
        return [opt.code for opt in explicit if answers is None or _is_visible(opt, answers)]
    labels = getattr(question.var, "labels", {})
    return list(labels.keys()) if labels else []


def _has_options(question: Question) -> bool:
    return bool(getattr(question, "choices", None))


def _simulate_array_multichoice(
    question: MultiChoice, answers: dict[str, Any] | None = None
) -> list | None:
    choices = _choice_codes(question, answers)
    if not choices and _has_options(question):
        return None  # every option is hidden: nothing to choose
    choices = choices or [1]
    max_answers = min(question.max_answers or len(choices), len(choices))
    min_answers = min(question.min_answers, max_answers)
    count = random.randint(min_answers, max_answers) if max_answers > 0 else 0
    selected = random.sample(choices, count) if count else []
    exclusive_selected = [value for value in selected if value in question.exclusive]
    if exclusive_selected:
        return [exclusive_selected[0]]
    return selected


def _simulate_wide_multichoice(
    question: MultiChoice, answers: dict[str, Any] | None = None
) -> dict[str, int | None]:
    """One 0/1 per variable, as the runtime offers the options: with a choice
    per variable, choice *i* is variable *i* (its code is what ``exclusive``
    names) and, with ``answers``, an option its own ``show_if`` / ``hide_if``
    hides is not offered — never ticked, and missing rather than 0. An
    exclusive choice drawn stands alone, as in array mode."""

    variables = question.var if isinstance(question.var, list) else [question.var]
    choices = question.choices or []
    if len(choices) == len(variables):
        offered = [
            (variable.name, choice.code)
            for variable, choice in zip(variables, choices, strict=True)
            if answers is None or _is_visible(choice, answers)
        ]
    else:
        offered = [(variable.name, variable.name) for variable in variables]
    if not offered:
        return {variable.name: None for variable in variables}  # nothing to choose
    max_answers = min(question.max_answers or len(offered), len(offered))
    min_answers = min(question.min_answers, max_answers)
    count = random.randint(min_answers, max_answers) if max_answers > 0 else 0
    selected = random.sample(offered, count) if count else []
    exclusive = [option for option in selected if option[1] in question.exclusive]
    if exclusive:
        selected = exclusive[:1]
    chosen = {name for name, _ in selected}
    shown = {name for name, _ in offered}
    return {
        variable.name: int(variable.name in chosen) if variable.name in shown else None
        for variable in variables
    }


def _evaluate_condition(condition: Any, answers: dict[str, Any], *, unknown: bool = True) -> bool:
    """Is this condition met, given the answers so far?

    ``unknown`` is the answer for a raw string condition, which the runtime's
    parser can evaluate and this simulator cannot. It differs by side, which is
    why it is a parameter: an unreadable ``show_if`` must not hide the question,
    and an unreadable ``hide_if`` must not hide it either.
    """
    if condition is None:
        return True
    if isinstance(condition, Expression):
        try:
            return condition.evaluate(answers)
        except (TypeError, ValueError, KeyError):
            # If evaluation fails (e.g., missing variable), default to not showing
            return False
    return unknown


def _is_visible(item: Any, answers: dict[str, Any]) -> bool:
    """Show unless something the simulator can read says otherwise.

    Both gates in one place because getting the pair wrong is silent: a
    ``hide_if`` written as a string used to count as "condition met" and so hid
    the question from *every* simulated respondent, leaving a column of nulls
    that looks exactly like a question nobody reached.
    """

    if not _evaluate_condition(getattr(item, "show_if", None), answers, unknown=True):
        return False
    hide = getattr(item, "hide_if", None)
    return hide is None or not _evaluate_condition(hide, answers, unknown=False)


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
    """Simulate a single question's value(s) and write into the row dict.

    ``row`` is also what the respondent has answered so far, which is what an
    option's condition reads.
    """
    if isinstance(question, MultiChoice) and question.mode == "wide":
        row.update(_simulate_wide_multichoice(question, row))
    elif isinstance(question, MaxDiff | Conjoint):
        row.update(_simulate_value(question))
    elif isinstance(question.var, list):
        for var in question.var:
            row[var.name] = _simulate_value(question, var=var, answers=row)
    else:
        row[question.var.name] = _simulate_value(question, answers=row)


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
    questions: list[Question],
    n: int = 100,
    seed: int | None = 42,
    *,
    scripts: Sequence[Script] | None = None,
) -> pd.DataFrame:
    """Simulate responses without page-level visibility (legacy flat mode).

    This function is kept for backward compatibility. For page-aware simulation
    that respects show_if/hide_if on pages, use ``simulate_from_pages()``.
    Answer options' conditions still apply, and ``scripts`` adds the arm of
    every ``Script.assign_condition`` among them, drawn before the questions.
    """
    if seed is not None:
        random.seed(seed)
    arms = _arms(scripts)
    rows = []
    for _ in range(n):
        row: dict[str, Any] = {}
        for arm in arms:
            row[arm.variable] = arm.draw(None)
        for q in questions:
            _simulate_question_into_row(q, row)
        rows.append(row)
    frame = pd.DataFrame(rows)
    if arms and not frame.empty:
        # Drawn first, as the runtime draws them, but listed after the
        # questions — where the page walk lists them too.
        assigned = [arm.variable for arm in arms]
        frame = frame[[c for c in frame.columns if c not in assigned] + assigned]
    return frame


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
    pages: list[Page],
    n: int = 100,
    seed: int | None = 42,
    *,
    routing: bool = True,
    scripts: Sequence[Script] | None = None,
    quotas: Sequence[Quota] | None = None,
) -> pd.DataFrame:
    """Simulate responses respecting visibility and — with ``routing`` —
    the questionnaire's navigation.

    Each simulated respondent starts on the first page and moves the way
    the runtime would: a page's ``show_if`` / ``hide_if`` decides whether it
    is answered (a hidden page is passed over — that is how a screen-out
    placed mid-questionnaire stays out of the way of those who qualify),
    a block's ``show_if`` / ``hide_if`` whether its questions are, an
    option's whether it can be picked; a question's ``skip_to``, the page's
    ``next_if`` rules and ``default_next`` decide where "Next" lands, and a
    visible terminal page (screen-out, final, redirect) ends the interview.
    Pages never reached stay missing, so a screen-out really leaves the later
    variables empty and a branch really splits the sample. ``routing=False``
    walks every page in document order (the previous behavior) and applies
    no quota.

    ``scripts`` are the questionnaire's (``Questionnaire.scripts``). Each
    ``Script.assign_condition`` gets its column, one arm drawn per respondent
    before the first page by the arms' weights — or, with ``balance=True``
    and a quota cell on every arm, the arm furthest behind its target, as the
    platform picks it. ``Script.randomize_pages`` deals each respondent their
    own page order (first, last and terminal pages pinned). Other scripts are
    JavaScript and are not run.

    ``quotas`` are the compiler options' ``quota`` cells. Leaving a page, a
    respondent holding a value in a full cell — an answer, or the arm drawn
    before the first page — ends there: the runtime's "quota full" screen,
    not a complete. Only completes count towards a cell, as ingest counts
    them, so a balanced assignment whose cells are all full keeps its draw
    and the respondent ends on the first page. The
    walk of respondent *k* therefore depends on the *k − 1* before it, which
    is what makes the sample shape of a quota visible here.
    """
    if seed is not None:
        random.seed(seed)

    # Collect all variable names across all pages to ensure consistent columns
    all_var_names: list[str] = []
    for page in pages:
        for q in page.flatten_questions():
            all_var_names.extend(_question_variable_names(q))
    arms = _arms(scripts)
    all_var_names += [arm.variable for arm in arms if arm.variable not in all_var_names]
    shuffled = routing and any(_deals_pages(script) for script in scripts or ())
    cells = _Cells(quotas if routing else None)

    rows = []
    for _ in range(n):
        row: dict[str, Any] = {name: None for name in all_var_names}
        for arm in arms:
            row[arm.variable] = arm.draw(cells)
        order = _dealt(pages) if shuffled else pages
        by_name = {page.name: index for index, page in enumerate(order)}
        completed = True
        index = 0
        steps = 0
        while 0 <= index < len(order) and steps <= 2 * len(order):
            steps += 1
            page = order[index]
            page_visible = _is_visible(page, row)
            visible = _walk_items(page.items, row, page_visible, shuffle=page.randomize_blocks)
            if not routing:
                index += 1
                continue
            if page_visible and page.is_terminal:
                completed = page.kind != "disqualification"
                break
            if page_visible and cells.closes(row):
                completed = False  # the runtime's quota_full screen
                break
            target = _route_target(page, row, visible) if page_visible else None
            # Like the runtime: a routed target, else the next page in order
            # (a hidden page is passed over, a visible terminal page ends it).
            index = by_name[target] if target is not None and target in by_name else index + 1
        if completed:
            cells.count(row)
        rows.append(row)

    return pd.DataFrame(rows)


def _walk_items(
    items: Iterable[Question | Block],
    row: dict[str, Any],
    visible: bool,
    *,
    shuffle: bool = False,
    deal: bool = False,
) -> list[Question]:
    """Answer the questions under ``items`` (or blank them when hidden).

    Questions are answered in document order, so a condition on an earlier
    question of the same page reads its answer. The list returned is the
    questions answered, in the order the runtime displays them — which is
    the order ``skip_to`` is looked for in. A block's shuffle
    (``Block.randomize``, ``deal``) deals its entries — a question, or a
    nested block as one piece, as the runtime does — and the page's
    (``Page.randomize_blocks``, ``shuffle``) moves blocks among the blocks'
    own places. They change that order and nothing else, so they are drawn
    only when they are there.
    """

    slots: list[tuple[bool, list[Question]]] = []  # (is a block, its answered questions)
    for item in items:
        if isinstance(item, Block):
            block_visible = visible and _is_visible(item, row)
            answered = _walk_items(item.items, row, block_visible, deal=item.randomize)
            slots.append((True, answered))
            continue
        if visible and _is_visible(item, row):
            _simulate_question_into_row(item, row)
            slots.append((False, [item]))
        else:
            _set_question_missing(item, row)
    if deal:
        # A nested block with nothing answered has no place in the order.
        slots = [slot for slot in slots if slot[1]]
        if len(slots) > 1:
            random.shuffle(slots)
    elif shuffle:
        places = [i for i, (is_block, _) in enumerate(slots) if is_block]
        if len(places) > 1:
            moved = [slots[i] for i in places]
            random.shuffle(moved)
            for place, slot in zip(places, moved, strict=True):
                slots[place] = slot
    return [question for _, answered in slots for question in answered]


def simulate_questionnaire(
    survey: Questionnaire,
    n: int = 100,
    seed: int | None = 42,
    *,
    quotas: Sequence[Quota] | None = None,
    routing: bool = True,
) -> pd.DataFrame:
    """The frame :func:`simulate_from_pages` gives, with the questionnaire's
    own scripts. ``quotas`` are the compiler options' ``quota`` (a document's
    ``quotas``, ``LoadedSurvey.quotas``): the questionnaire does not carry
    them. A questionnaire of blocks rather than pages is walked on the pages
    the runtime makes of it — a page per block, gated by the block's
    conditions (one page when loose questions sit among the blocks)."""

    from siamang.frontend.compiler.react import _pages_for_react

    pages = survey.pages or list(_pages_for_react(survey))
    return simulate_from_pages(
        pages, n=n, seed=seed, routing=routing, scripts=survey.scripts, quotas=quotas
    )


def simulate_survey(
    survey: Questionnaire,
    n: int = 100,
    seed: int | None = 42,
    *,
    quotas: Sequence[Quota] | None = None,
) -> SurveyData:
    """:meth:`Questionnaire.simulate` with the scripts and the quotas: the
    frame of :func:`simulate_questionnaire` and its codebook — the
    questionnaire's variables, or the questions' when it declares none, and a
    nominal variable for every assigned arm the codebook does not already
    have, labeled with the arms."""

    from siamang.core.variable import Variable, VariableMap
    from siamang.data.survey_data import SurveyData

    frame = simulate_questionnaire(survey, n=n, seed=seed, quotas=quotas)
    variables = survey.variables or VariableMap()
    if not variables:
        variables = VariableMap()
        for question in survey.all_questions():
            for variable in question.var if isinstance(question.var, list) else [question.var]:
                if variable.name not in variables:
                    variables.add(variable)
    missing = [arm for arm in _arms(survey.scripts) if arm.variable not in variables]
    if missing:
        known = VariableMap()
        for variable in variables.values() if isinstance(variables, dict) else variables:
            known.add(variable)
        for arm in missing:
            known.add(
                Variable(
                    arm.variable,
                    "nominal",
                    label=arm.variable,
                    labels=dict(zip(arm.codes, arm.labels, strict=True)),
                    description="Arm drawn by Script.assign_condition",
                )
            )
        variables = known
    return SurveyData(frame=frame, variables=variables, questionnaire=survey)


# ─── scripts ──────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class _Arm:
    """One ``Script.assign_condition``: where the arm goes and how it is drawn."""

    variable: str
    codes: tuple[Any, ...]
    labels: tuple[str, ...]
    weights: tuple[int, ...]
    balance: bool

    def draw(self, cells: _Cells | None) -> Any:
        """The runtime's draw: a cut through the cumulative weights. A balanced
        assignment then takes the arm the quotas say is furthest behind, when
        they can say so, and keeps the draw when they cannot."""
        cut = random.random() * sum(self.weights)
        chosen = self.codes[-1]
        for code, weight in zip(self.codes, self.weights, strict=True):
            cut -= weight
            if cut < 0:
                chosen = code
                break
        if self.balance and cells is not None:
            picked = cells.pick(self.variable, self.codes)
            if picked is not None:
                chosen = picked
        return chosen


def _arms(scripts: Sequence[Script] | None) -> list[_Arm]:
    arms: list[_Arm] = []
    for script in scripts or ():
        variable = getattr(script, "assigns", None)
        if not variable or any(arm.variable == variable for arm in arms):
            continue
        context = script.context or {}
        spec = [arm for arm in context.get("arms", []) if isinstance(arm, list | tuple) and arm]
        if not spec:
            continue
        arms.append(
            _Arm(
                variable=variable,
                codes=tuple(arm[0] for arm in spec),
                labels=tuple(str(arm[1]) if len(arm) > 1 else str(arm[0]) for arm in spec),
                weights=tuple(int(arm[2]) if len(arm) > 2 else 1 for arm in spec),
                balance=bool(context.get("balance")),
            )
        )
    return arms


def _deals_pages(script: Script) -> bool:
    """``Script.randomize_pages()`` — known by the name and trigger it makes."""
    return script.name == "randomize_pages" and script.trigger == "onInit"


def _dealt(pages: list[Page]) -> list[Page]:
    """One respondent's page order, as ``Script.randomize_pages`` deals it: the
    first and last page and every terminal page keep their place, the others
    are shuffled into the remaining places."""
    pinned = [
        index == 0 or index == len(pages) - 1 or page.is_terminal
        for index, page in enumerate(pages)
    ]
    movable = [page for page, pin in zip(pages, pinned, strict=True) if not pin]
    if len(movable) < 2:
        return list(pages)
    random.shuffle(movable)
    dealt = iter(movable)
    return [page if pin else next(dealt) for page, pin in zip(pages, pinned, strict=True)]


# ─── quotas ───────────────────────────────────────────────────────────────────


def _same_code(a: Any, b: Any) -> bool:
    """A code from a document and one from a draw: ``1`` and ``"1"`` are one arm."""
    return a == b or str(a) == str(b)


def _values(value: Any) -> list[Any]:
    """An answer as the codes it holds: a multiple choice counts every one."""
    if value is None:
        return []
    if isinstance(value, list | tuple | set):
        return list(value)
    return [value]


class _Cells:
    """The quota counters, as ingest keeps them: completes only."""

    def __init__(self, quotas: Sequence[Quota] | None) -> None:
        self.quotas = list(quotas or [])
        self.counts = [0] * len(self.quotas)

    def closes(self, row: dict[str, Any]) -> bool:
        """Leaving a page, does a value the respondent holds fall in a full
        cell? The runtime asks about every quota variable holding a value it
        has not found open yet — an answer from this page, and on the first
        page left the arm an assignment drew before it. The counts do not move
        during one respondent's walk, so asking about all of them at every
        page is asking about each the first time it holds a value."""
        if not self.quotas:
            return False
        for quota, count in zip(self.quotas, self.counts, strict=True):
            if count < quota.limit:
                continue
            if any(
                _same_code(value, quota.target_value) for value in _values(row.get(quota.variable))
            ):
                return True
        return False

    def count(self, row: dict[str, Any]) -> None:
        for index, quota in enumerate(self.quotas):
            if any(
                _same_code(value, quota.target_value) for value in _values(row.get(quota.variable))
            ):
                self.counts[index] += 1

    def pick(self, variable: str, codes: Sequence[Any]) -> Any | None:
        """The arm furthest behind its own target — completes over limit, so a
        2:1 design stays 2:1 — ties drawn at random. None when an arm has no
        cell (a partial quota cannot balance) or every cell is full."""
        ratios: list[tuple[float, Any]] = []
        for code in codes:
            cell = next(
                (
                    (count, quota.limit)
                    for quota, count in zip(self.quotas, self.counts, strict=True)
                    if quota.variable == variable and _same_code(quota.target_value, code)
                ),
                None,
            )
            if cell is None:
                return None
            count, limit = cell
            if limit > 0 and count < limit:
                ratios.append((count / limit, code))
        if not ratios:
            return None
        best = min(ratio for ratio, _ in ratios)
        return random.choice([code for ratio, code in ratios if ratio == best])
