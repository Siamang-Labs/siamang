"""siamang.design — the experimental design a MaxDiff question freezes."""

from __future__ import annotations

from collections import Counter
from itertools import combinations

import pytest

from siamang.design import MaxDiffDesign, maxdiff_design

ITEMS = list(range(1, 11))


def test_the_same_seed_gives_the_same_design():
    """The reason the design is generated once and stored rather than drawn at
    fieldwork time: an analysis re-run later must be answering the same
    question, and a reviewer must be able to rebuild what was asked."""

    first = maxdiff_design(ITEMS, per_task=4, tasks=8, versions=20, seed=7)
    assert (
        first.to_dict() == maxdiff_design(ITEMS, per_task=4, tasks=8, versions=20, seed=7).to_dict()
    )
    other = maxdiff_design(ITEMS, per_task=4, tasks=8, versions=20, seed=8)
    assert first.to_dict() != other.to_dict()


def test_a_design_round_trips_through_its_document_form():
    design = maxdiff_design(ITEMS, per_task=4, tasks=8, versions=5, seed=1)
    again = MaxDiffDesign.from_dict(design.to_dict())
    assert again.to_dict() == design.to_dict()
    assert again.task(0, 0) == design.task(0, 0)


def test_every_task_shows_the_right_number_of_distinct_items():
    design = maxdiff_design(ITEMS, per_task=4, tasks=8, versions=20, seed=3)
    assert len(design.versions) == 20
    for version in design.versions:
        assert len(version) == 8
        for task in version:
            assert len(task) == 4
            assert len(set(task)) == 4, "an item shown twice in one task has nothing to beat"
            assert set(task) <= set(ITEMS)


def test_items_are_shown_equally_often_and_pairs_nearly_so():
    """Unequal exposure means some items are estimated from more evidence than
    others, and nobody is told which. A pair that never meets is worse: it is a
    comparison the data cannot make at all."""

    design = maxdiff_design(ITEMS, per_task=4, tasks=8, versions=20, seed=5)
    shown = Counter(item for version in design.versions for task in version for item in task)
    assert set(shown) == set(ITEMS)
    assert min(shown.values()) == max(shown.values()) == 64  # 20 × 8 × 4 / 10
    assert design.balance.perfect
    assert design.balance.item_min == 64 and design.balance.item_max == 64

    pairs = Counter(
        pair
        for version in design.versions
        for task in version
        for pair in combinations(sorted(task), 2)
    )
    assert len(pairs) == len(list(combinations(ITEMS, 2))), "every pair must meet at least once"
    assert design.balance.pair_min == min(pairs.values())
    assert design.balance.pair_max == max(pairs.values())
    assert design.balance.pair_max - design.balance.pair_min <= 4


def test_balance_is_measured_not_predicted():
    """32 slots do not divide by 10, so no single version can be even — and the
    design still is, because the deal carries across versions."""

    one = maxdiff_design(ITEMS, per_task=4, tasks=8, versions=1, seed=2)
    assert not one.balance.perfect
    many = maxdiff_design(ITEMS, per_task=4, tasks=8, versions=20, seed=2)
    assert many.balance.perfect


def test_a_bigger_design_stays_fast_and_connected():
    """Forty items is an ordinary MaxDiff, and this runs at Save time."""

    design = maxdiff_design(list(range(40)), per_task=5, tasks=15, versions=50, seed=1)
    assert design.balance.item_max - design.balance.item_min <= 1
    assert design.balance.pair_min > 0


def test_versions_wrap_rather_than_raise():
    """The runtime picks a version from a respondent id; a hash landing past the
    end must not be how a respondent meets an error page."""

    design = maxdiff_design(ITEMS, per_task=3, tasks=4, versions=3, seed=1)
    assert design.task(7, 0) == design.task(1, 0)
    assert design.tasks == 4


def test_a_design_that_cannot_work_says_why():
    with pytest.raises(ValueError, match="at least three items"):
        maxdiff_design([1, 2], per_task=2)
    with pytest.raises(ValueError, match="nothing to beat"):
        maxdiff_design(ITEMS, per_task=1)
    with pytest.raises(ValueError, match="more items than the question has"):
        maxdiff_design(ITEMS, per_task=11)
    with pytest.raises(ValueError, match="complete, not incomplete"):
        maxdiff_design(ITEMS, per_task=10)
    with pytest.raises(ValueError, match="at least one task"):
        maxdiff_design(ITEMS, per_task=4, tasks=0)
    with pytest.raises(ValueError, match="at least one version"):
        maxdiff_design(ITEMS, per_task=4, versions=0)


def test_duplicate_items_are_collapsed_not_counted_twice():
    design = maxdiff_design(["a", "b", "c", "a", "d"], per_task=2, tasks=4, versions=2, seed=1)
    assert design.items == ("a", "b", "c", "d")


def test_the_generator_itself_is_pinned():
    """A golden, and the reason for one.

    The design lives in a questionnaire as a seed and a handful of numbers, not
    as a stored table, so what a past study actually showed its respondents is
    whatever this function returns today for that seed. If the heuristic is ever
    improved, every questionnaire written before the change quietly starts
    describing tasks nobody was asked. This test makes that a failure instead of
    a silence — and if the improvement is worth having, it is worth also
    bumping the format and keeping the old path for old documents.
    """

    design = maxdiff_design([1, 2, 3, 4, 5], per_task=3, tasks=3, versions=2, seed=42)
    assert [[list(task) for task in version] for version in design.versions] == [
        [[4, 2, 3], [5, 1, 4], [3, 1, 5]],
        [[2, 4, 3], [2, 1, 5], [2, 3, 4]],
    ]
