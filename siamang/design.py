"""Experimental designs: which items a respondent is asked about, and when.

A MaxDiff question does not show its items; it shows a few of them at a time,
several times over, and the *pattern* of which items met which decides what can
be estimated afterward. That pattern is a design, and this module builds it.

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

import random
from collections.abc import Hashable, Sequence
from dataclasses import dataclass, field
from itertools import combinations
from typing import Any

__all__ = ["Balance", "MaxDiffDesign", "maxdiff_design"]


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
