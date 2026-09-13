"""Experimental designs: which items a respondent is asked about, and when.

A MaxDiff question does not show its items; it shows a few of them at a time,
several times over, and the *pattern* of which items met which decides what can
be estimated afterward. A choice-based conjoint does the same with whole
products: which levels of which attributes appeared together, and against what.
That pattern is a design, and this module builds it.

Two things make a design trustworthy, and both are here rather than assumed:

    **It is frozen, not rolled.** The design is generated once from a seed and
    then stored in the questionnaire. It travels into the snapshot, into the
    downloaded ``.py`` and into the provenance file, so an analysis re-run a
    year later is answering the same question. A design re-drawn at fieldwork
    time is a design nobody can check.

    **It reports its own balance.** Every item should appear about as often as
    every other, and every pair about as often as every other pair, or some
    items are estimated from more evidence than others and nobody is told. The
    generator returns those counts, in the open, along with whether perfect
    balance was arithmetically possible at all.
"""

from __future__ import annotations

import math
import random
from collections.abc import Hashable, Sequence
from dataclasses import dataclass, field
from itertools import combinations
from typing import Any

import numpy as np

__all__ = [
    "Balance",
    "CbcBalance",
    "CbcDesign",
    "MaxDiffDesign",
    "cbc_design",
    "maxdiff_design",
]


@dataclass(frozen=True, slots=True)
class Balance:
    """How evenly a design spreads its items, as plain counts.

    ``perfect`` is whether every item really did end up shown the same number of
    times. It is measured, not predicted: 10 items over 8 tasks of 4 cannot come
    out even *within one version* — 32 slots do not divide by 10 — yet across 20
    versions they do, because the deal carries over. A researcher asking "is
    every item asked about equally often?" wants that answer, not the one the
    arithmetic of a single version suggests.

    Pairs are the other half and never come out exactly even at realistic sizes;
    ``pair_min`` matters most, because a pair that never meets is a comparison
    the data cannot make.
    """

    item_min: int
    item_max: int
    pair_min: int
    pair_max: int
    perfect: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_min": self.item_min,
            "item_max": self.item_max,
            "pair_min": self.pair_min,
            "pair_max": self.pair_max,
            "perfect": self.perfect,
        }

    def __str__(self) -> str:
        items = (
            f"every item shown {self.item_min} times"
            if self.perfect
            else f"each item shown {self.item_min}–{self.item_max} times"
        )
        return f"{items}, each pair {self.pair_min}–{self.pair_max} times"


@dataclass(frozen=True, slots=True)
class MaxDiffDesign:
    """``versions`` blocks of ``tasks`` tasks, each naming ``per_task`` items."""

    items: tuple[Hashable, ...]
    per_task: int
    versions: tuple[tuple[tuple[Hashable, ...], ...], ...]
    seed: int | None = None
    balance: Balance | None = field(default=None)

    @property
    def tasks(self) -> int:
        return len(self.versions[0]) if self.versions else 0

    def task(self, version: int, task: int) -> tuple[Hashable, ...]:
        """The items shown in one task, with the version taken modulo the count.

        Out-of-range versions wrap rather than raise: the runtime picks a
        version from a respondent id, and a respondent must never see an error
        because a hash landed past the end.
        """

        if not self.versions:
            raise ValueError("This design has no versions.")
        return self.versions[version % len(self.versions)][task]

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "items": list(self.items),
            "per_task": self.per_task,
            "versions": [[list(task) for task in version] for version in self.versions],
        }
        if self.seed is not None:
            payload["seed"] = self.seed
        if self.balance is not None:
            payload["balance"] = self.balance.to_dict()
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> MaxDiffDesign:
        balance = payload.get("balance")
        return cls(
            items=tuple(payload["items"]),
            per_task=int(payload["per_task"]),
            versions=tuple(
                tuple(tuple(task) for task in version) for version in payload["versions"]
            ),
            seed=payload.get("seed"),
            balance=Balance(**balance) if balance else None,
        )


def _pairs_of(task: Sequence[Hashable]) -> list[tuple[Hashable, Hashable]]:
    return [tuple(sorted(pair, key=str)) for pair in combinations(task, 2)]  # type: ignore[misc]


def _deal(
    items: Sequence[Hashable],
    per_task: int,
    tasks: int,
    rng: random.Random,
    deck: list[Hashable],
) -> list[list[Hashable]]:
    """One version's tasks, dealt round-robin from a repeatedly shuffled deck.

    ``deck`` is the caller's and carries across versions on purpose, and it is
    extended in place rather than rebound. Restarting it per version let each
    version pick afresh which items got the spare slot, and those picks
    accumulated: sixty-one showings against sixty-seven where every item should
    have had sixty-four.

    Dealing this way spreads the items as evenly as the slot count allows, and — because the later swaps only exchange items *between* tasks of
    the same version — that spread is then fixed for good: a swap moves an item
    from one task to another and leaves how often it appears unchanged. So item
    balance is settled here, and the swaps are free to work on pairs alone.
    """

    version: list[list[Hashable]] = []
    for _ in range(tasks):
        task: list[Hashable] = []
        while len(task) < per_task:
            pick = next((item for item in deck if item not in task), None)
            if pick is None:
                # Either the deck is empty or everything left in it is already
                # in this task. Extend it in place — rebinding the name would
                # quietly abandon the caller's deck and put every version back
                # to choosing its own spare slots.
                fresh = list(items)
                rng.shuffle(fresh)
                deck += fresh
                continue
            deck.remove(pick)
            task.append(pick)
        version.append(task)
    return version


def _swap_delta(
    counts: dict[tuple[Hashable, Hashable], int],
    ideal: float,
    removed: Sequence[tuple[Hashable, Hashable]],
    added: Sequence[tuple[Hashable, Hashable]],
) -> float:
    """How much a swap changes the squared spread of pair counts.

    Only the pairs the swap touches, which is why a design of forty items builds
    in a second instead of twenty: rescoring every pair on every candidate swap
    was the whole cost.
    """

    delta = 0.0
    for pair in removed:
        delta += 1 - 2 * (counts.get(pair, 0) - ideal)
    for pair in added:
        delta += 1 + 2 * (counts.get(pair, 0) - ideal)
    return delta


def maxdiff_design(
    items: Sequence[Hashable],
    *,
    per_task: int = 4,
    tasks: int = 8,
    versions: int = 20,
    seed: int | None = None,
) -> MaxDiffDesign:
    """A balanced incomplete block design for a MaxDiff question.

    ``versions`` independent blocks so that different respondents see different
    combinations — together they cover far more of the item space than any one
    respondent could be asked to sit through. The same ``seed`` always returns
    the same design; that is the whole point of generating it once and storing
    it rather than drawing it at fieldwork time.
    """

    items = list(dict.fromkeys(items))
    if len(items) < 3:
        raise ValueError("A MaxDiff needs at least three items to compare.")
    if per_task < 2:
        raise ValueError("A task must show at least two items — one has nothing to beat.")
    if per_task > len(items):
        raise ValueError(f"per_task={per_task} is more items than the question has ({len(items)}).")
    if per_task == len(items):
        raise ValueError(
            "Showing every item in every task makes the design complete, not incomplete: "
            "nothing is learned from which items met. Show fewer items per task."
        )
    if tasks < 1:
        raise ValueError("A MaxDiff needs at least one task.")
    if versions < 1:
        raise ValueError("A MaxDiff needs at least one version.")

    rng = random.Random(seed)
    deck: list[Hashable] = []
    blocks = [_deal(items, per_task, tasks, rng, deck) for _ in range(versions)]

    # Pair balance is optimized across the whole design, not version by version:
    # what has to be estimable is how often two items met *in the study*, and a
    # pair that never meets anywhere is a comparison nobody can make.
    counts: dict[tuple[Hashable, Hashable], int] = {}
    for block in blocks:
        for task in block:
            for pair in _pairs_of(task):
                counts[pair] = counts.get(pair, 0) + 1
    n_pairs = len(items) * (len(items) - 1) // 2
    ideal = sum(counts.values()) / n_pairs if n_pairs else 0.0

    for _ in range(60 * versions * tasks):
        block = blocks[rng.randrange(versions)]
        a, b = rng.randrange(tasks), rng.randrange(tasks)
        if a == b:
            continue
        i, j = rng.randrange(per_task), rng.randrange(per_task)
        left, right = block[a][i], block[b][j]
        if left == right or left in block[b] or right in block[a]:
            continue
        removed = [
            *(tuple(sorted((left, other), key=str)) for other in block[a] if other != left),
            *(tuple(sorted((right, other), key=str)) for other in block[b] if other != right),
        ]
        added = [
            *(tuple(sorted((right, other), key=str)) for other in block[a] if other != left),
            *(tuple(sorted((left, other), key=str)) for other in block[b] if other != right),
        ]
        if _swap_delta(counts, ideal, removed, added) >= 0:
            continue
        block[a][i], block[b][j] = right, left
        for pair in removed:
            counts[pair] = counts.get(pair, 0) - 1
        for pair in added:
            counts[pair] = counts.get(pair, 0) + 1

    per_item: dict[Hashable, int] = dict.fromkeys(items, 0)
    for block in blocks:
        for task in block:
            for item in task:
                per_item[item] += 1
    pair_counts = [
        counts.get(pair, 0) for pair in (tuple(sorted(p, key=str)) for p in combinations(items, 2))
    ]
    balance = Balance(
        item_min=min(per_item.values()),
        item_max=max(per_item.values()),
        pair_min=min(pair_counts) if pair_counts else 0,
        pair_max=max(pair_counts) if pair_counts else 0,
        perfect=min(per_item.values()) == max(per_item.values()),
    )
    return MaxDiffDesign(
        items=tuple(items),
        per_task=per_task,
        versions=tuple(tuple(tuple(task) for task in block) for block in blocks),
        seed=seed,
        balance=balance,
    )


# ─── Choice-based conjoint ───────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class CbcBalance:
    """Whether every level got a fair hearing, and how precise the design is.

    ``imbalance`` is the largest gap, *within* any one attribute, between its
    most and least often shown level. Comparing counts across attributes would
    be meaningless — an attribute with two levels shows each of them twice as
    often as one with four — so the number that matters is whether each
    attribute treated its own levels alike. Zero is even.

    ``overlap`` is the average number of attributes per task whose level is
    repeated across the alternatives. A task where every alternative has the
    same price teaches nothing about price, so lower is better — but not all of
    it is avoidable: an attribute with fewer levels than the task has
    alternatives *must* repeat one. ``overlap_min`` is that floor, so the two
    numbers together say whether the design did as well as it could rather than
    leaving a reader to work it out.

    ``d_error`` is the standard D-error under a null model:
    ``det(information**-1) ** (1/p)``, lower being more precise. It is
    comparable between candidate designs *of the same question* — which is what
    it is used for here, to pick one — and is not an absolute score.

    It is ``None`` when the design cannot estimate its own parameters at all:
    too few tasks for the number of levels leaves the information matrix
    singular, and no amount of fieldwork fixes that. Saying "not estimable" is
    the useful answer; a very large number would read as merely imprecise.
    """

    imbalance: int
    overlap: float
    overlap_min: int
    d_error: float | None
    perfect: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "imbalance": self.imbalance,
            "overlap": self.overlap,
            "overlap_min": self.overlap_min,
            "d_error": self.d_error,
            "perfect": self.perfect,
        }

    def __str__(self) -> str:
        levels = (
            "each attribute shows its levels equally often"
            if self.perfect
            else f"levels within an attribute differ by up to {self.imbalance} showings"
        )
        forced = " (the least possible)" if self.overlap <= self.overlap_min else ""
        precision = (
            "not estimable — too few tasks for this many levels"
            if self.d_error is None
            else f"D-error {self.d_error:.4f}"
        )
        return f"{levels}, {self.overlap:.2f} repeated attributes per task{forced}, {precision}"


@dataclass(frozen=True, slots=True)
class CbcDesign:
    """``versions`` blocks of ``tasks``, each a handful of whole products.

    A profile is one level code per attribute, in the attributes' own order.
    """

    attributes: tuple[str, ...]
    levels: tuple[tuple[Hashable, ...], ...]  # the codes of each attribute
    alternatives: int
    versions: tuple[tuple[tuple[tuple[Hashable, ...], ...], ...], ...]
    seed: int | None = None
    balance: CbcBalance | None = field(default=None)

    @property
    def tasks(self) -> int:
        return len(self.versions[0]) if self.versions else 0

    def task(self, version: int, task: int) -> tuple[tuple[Hashable, ...], ...]:
        """The profiles shown in one task; the version wraps rather than raising."""

        if not self.versions:
            raise ValueError("This design has no versions.")
        return self.versions[version % len(self.versions)][task]

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "attributes": list(self.attributes),
            "levels": [list(codes) for codes in self.levels],
            "alternatives": self.alternatives,
            "versions": [
                [[list(profile) for profile in task] for task in version]
                for version in self.versions
            ],
        }
        if self.seed is not None:
            payload["seed"] = self.seed
        if self.balance is not None:
            payload["balance"] = self.balance.to_dict()
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> CbcDesign:
        balance = payload.get("balance")
        return cls(
            attributes=tuple(payload["attributes"]),
            levels=tuple(tuple(codes) for codes in payload["levels"]),
            alternatives=int(payload["alternatives"]),
            versions=tuple(
                tuple(tuple(tuple(profile) for profile in task) for task in version)
                for version in payload["versions"]
            ),
            seed=payload.get("seed"),
            balance=CbcBalance(**balance) if balance else None,
        )


def _dummy(profile: Sequence[Hashable], levels: Sequence[Sequence[Hashable]]) -> list[float]:
    """One profile as the row a main-effects model would fit on it.

    The first level of each attribute is the reference and gets no column, so a
    part-worth is read as "against that level" — the same convention the
    estimator uses, which is why the design is scored on the matrix that will
    actually be fitted rather than on a tidier one.
    """

    row: list[float] = []
    for value, codes in zip(profile, levels, strict=True):
        row.extend(1.0 if value == code else 0.0 for code in codes[1:])
    return row


def _task_information(
    task: Sequence[Sequence[Hashable]], levels: Sequence[Sequence[Hashable]]
) -> np.ndarray:
    """What one choice task contributes when every alternative is equally likely.

    ``X'(P - pp')X`` with ``p = 1/J`` — the Fisher information of a conditional
    logit at the null, which is the standard thing a choice design is scored on
    before any data exists.
    """

    block = np.array([_dummy(profile, levels) for profile in task])
    share = 1.0 / len(task)
    mean = block.mean(axis=0)
    return share * (block.T @ block) - np.outer(mean, mean)


def _d_error_of(information: np.ndarray) -> float:
    """``det(information**-1) ** (1/p)`` — lower is more precise."""

    width = information.shape[0]
    if width == 0:
        return float("inf")
    sign, logdet = np.linalg.slogdet(information)
    if sign <= 0 or not np.isfinite(logdet):
        return float("inf")
    # Through the log, because the determinant of a design of any size
    # underflows to zero long before the design stops being informative.
    return float(np.exp(-logdet / width))


def _d_error(
    blocks: Sequence[Sequence[Sequence[Sequence[Hashable]]]],
    levels: Sequence[Sequence[Hashable]],
) -> float:
    information = _information_of(blocks, levels)
    return _d_error_of(information)


def _information_of(
    blocks: Sequence[Sequence[Sequence[Sequence[Hashable]]]],
    levels: Sequence[Sequence[Hashable]],
) -> np.ndarray:
    width = sum(len(codes) - 1 for codes in levels)
    information = np.zeros((width, width))
    for version in blocks:
        for task in version:
            information += _task_information(task, levels)
    return information


def _overlap(task: Sequence[Sequence[Hashable]]) -> int:
    """Attributes whose level is repeated across this task's alternatives.

    A task where every alternative has the same price says nothing about price.
    """

    return sum(1 for column in zip(*task, strict=True) if len(set(column)) < len(column))


def _cbc_block(
    levels: Sequence[Sequence[Hashable]],
    alternatives: int,
    tasks: int,
    rng: random.Random,
    decks: list[list[Hashable]],
) -> list[list[tuple[Hashable, ...]]]:
    """One version, dealt so each attribute's levels come up in turn.

    ``decks`` run across versions for the same reason the MaxDiff deal does: it
    is what makes the level counts of the whole design come out even instead of
    each version deciding afresh which level gets the spare slot.
    """

    block: list[list[tuple[Hashable, ...]]] = []
    for _ in range(tasks):
        task: list[list[Hashable]] = [[] for _ in range(alternatives)]
        for attribute, codes in enumerate(levels):
            for position in range(alternatives):
                if not decks[attribute]:
                    fresh = list(codes)
                    rng.shuffle(fresh)
                    decks[attribute] += fresh
                # Prefer a level this task has not used yet: a repeated level
                # across alternatives is a comparison the task cannot make.
                already = {task[other][attribute] for other in range(position) if task[other]}
                pick = next((c for c in decks[attribute] if c not in already), decks[attribute][0])
                decks[attribute].remove(pick)
                task[position].append(pick)
        block.append([tuple(profile) for profile in task])
    return block


def cbc_design(
    attributes: Sequence[str],
    levels: Sequence[Sequence[Hashable]],
    *,
    alternatives: int = 3,
    tasks: int = 10,
    versions: int = 20,
    seed: int | None = None,
    starts: int = 6,
) -> CbcDesign:
    """A choice design: whole products, several at a time, several times over.

    Built the way choice designs are built in practice — several random starts,
    each improved by swapping levels, keeping whichever came out most precise.
    "Most precise" is the D-error, which is what the criterion exists for; the
    level counts and the overlap are reported beside it because they are what a
    researcher can check without taking the determinant on trust.

    The same ``seed`` always returns the same design.
    """

    attributes = list(attributes)
    levels = [list(dict.fromkeys(codes)) for codes in levels]
    if len(attributes) != len(levels):
        raise ValueError("Each attribute needs its own list of levels.")
    if len(attributes) < 2:
        raise ValueError("A conjoint needs at least two attributes to trade off.")
    if any(len(codes) < 2 for codes in levels):
        raise ValueError("Every attribute needs at least two levels — one is a constant.")
    if alternatives < 2:
        raise ValueError("A choice task needs at least two alternatives to choose between.")
    if tasks < 1:
        raise ValueError("A conjoint needs at least one task.")
    if versions < 1:
        raise ValueError("A conjoint needs at least one version.")
    if starts < 1:
        raise ValueError("starts must be at least 1.")

    best_blocks: list[list[list[tuple[Hashable, ...]]]] | None = None
    best_error = float("inf")
    for start in range(starts):
        # Each start needs its own stream, and all of them need to follow from
        # the one seed, or "the same seed gives the same design" stops holding.
        rng = random.Random(f"{seed}:{start}" if seed is not None else None)
        decks: list[list[Hashable]] = [[] for _ in levels]
        blocks = [_cbc_block(levels, alternatives, tasks, rng, decks) for _ in range(versions)]
        blocks = _improve(blocks, levels, rng)
        error = _d_error(blocks, levels)
        # `best_blocks is None` covers the case where every start is singular:
        # the question is under-identified whatever we deal, and the researcher
        # still gets a design back, with the balance saying it cannot be fitted.
        if best_blocks is None or error < best_error:
            best_blocks, best_error = blocks, error

    counts: dict[tuple[int, Hashable], int] = {}
    for version in best_blocks:
        for task in version:
            for profile in task:
                for attribute, value in enumerate(profile):
                    counts[(attribute, value)] = counts.get((attribute, value), 0) + 1
    # Within each attribute, never across them: an attribute with two levels
    # shows each of them twice as often as one with four, and that is arithmetic,
    # not imbalance.
    spreads = [
        max(counts.get((a, code), 0) for code in codes)
        - min(counts.get((a, code), 0) for code in codes)
        for a, codes in enumerate(levels)
    ]
    overlaps = [_overlap(task) for version in best_blocks for task in version]
    balance = CbcBalance(
        imbalance=max(spreads) if spreads else 0,
        overlap=round(sum(overlaps) / len(overlaps), 3) if overlaps else 0.0,
        # An attribute with fewer levels than the task has alternatives must
        # repeat one; that part of the overlap is not the design's fault.
        overlap_min=sum(1 for codes in levels if len(codes) < alternatives),
        d_error=round(best_error, 5) if math.isfinite(best_error) else None,
        perfect=bool(spreads) and max(spreads) == 0,
    )
    return CbcDesign(
        attributes=tuple(attributes),
        levels=tuple(tuple(codes) for codes in levels),
        alternatives=alternatives,
        versions=tuple(tuple(tuple(task) for task in version) for version in best_blocks),
        seed=seed,
        balance=balance,
    )


def _improve(
    blocks: list[list[list[tuple[Hashable, ...]]]],
    levels: Sequence[Sequence[Hashable]],
    rng: random.Random,
    passes: int = 600,
) -> list[list[list[tuple[Hashable, ...]]]]:
    """Swap one attribute's level between two alternatives, keep what helps.

    Swapping rather than re-drawing keeps each attribute's level counts exactly
    where the deal put them — the same property the MaxDiff swaps rely on — so
    this is free to work on precision and overlap alone.

    A swap touches one task, so only that task's contribution to the information
    matrix is recomputed. Rescoring the whole design each time was what made a
    thirty-version design take fourteen seconds at Save.
    """

    current = [[list(task) for task in version] for version in blocks]
    information = _information_of(current, levels)
    score = _d_error_of(information)
    for _ in range(passes):
        v = rng.randrange(len(current))
        t = rng.randrange(len(current[v]))
        task = current[v][t]
        a, b = rng.randrange(len(task)), rng.randrange(len(task))
        if a == b:
            continue
        attribute = rng.randrange(len(levels))
        left, right = list(task[a]), list(task[b])
        if left[attribute] == right[attribute]:
            continue
        before_overlap = _overlap(task)
        before = _task_information(task, levels)
        left[attribute], right[attribute] = right[attribute], left[attribute]
        task[a], task[b] = tuple(left), tuple(right)
        after = _task_information(task, levels)
        candidate_information = information - before + after
        candidate = _d_error_of(candidate_information)
        # Precision decides; overlap breaks ties, because two designs of equal
        # D-error are not equally readable to the respondent.
        if candidate < score or (candidate == score and _overlap(task) < before_overlap):
            information, score = candidate_information, candidate
        else:
            task[a], task[b] = tuple(right), tuple(left)
    return [[list(task) for task in version] for version in current]
