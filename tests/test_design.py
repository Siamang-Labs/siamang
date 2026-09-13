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


# ─── choice-based conjoint ───────────────────────────────────────────────────

ATTRIBUTES = ["brand", "price", "size", "warranty"]
LEVELS = [["Acme", "Globex", "Initech"], [10, 15, 20, 25], ["S", "L"], ["1y", "2y", "3y"]]


def test_a_conjoint_design_is_fixed_by_its_seed():
    from siamang.design import CbcDesign, cbc_design

    first = cbc_design(ATTRIBUTES, LEVELS, alternatives=3, tasks=8, versions=6, seed=3)
    again = cbc_design(ATTRIBUTES, LEVELS, alternatives=3, tasks=8, versions=6, seed=3)
    assert first.to_dict() == again.to_dict()
    other = cbc_design(ATTRIBUTES, LEVELS, alternatives=3, tasks=8, versions=6, seed=4)
    assert first.to_dict() != other.to_dict()
    assert CbcDesign.from_dict(first.to_dict()).to_dict() == first.to_dict()


def test_every_task_shows_whole_products():
    from siamang.design import cbc_design

    design = cbc_design(ATTRIBUTES, LEVELS, alternatives=3, tasks=8, versions=6, seed=3)
    assert len(design.versions) == 6 and design.tasks == 8
    for version in design.versions:
        for task in version:
            assert len(task) == 3
            for profile in task:
                assert len(profile) == len(ATTRIBUTES)
                for value, codes in zip(profile, LEVELS, strict=True):
                    assert value in codes


def test_each_attribute_shows_its_own_levels_equally_often():
    """Across attributes the counts differ by arithmetic — two levels are each
    shown twice as often as four. Within an attribute they should not."""

    from collections import Counter

    from siamang.design import cbc_design

    design = cbc_design(ATTRIBUTES, LEVELS, alternatives=3, tasks=10, versions=12, seed=5)
    for position, codes in enumerate(LEVELS):
        shown = Counter(
            profile[position] for version in design.versions for task in version for profile in task
        )
        assert set(shown) == set(codes)
        assert max(shown.values()) - min(shown.values()) == 0
    assert design.balance.perfect and design.balance.imbalance == 0


def test_overlap_is_reported_against_what_is_actually_avoidable():
    """`size` has two levels and every task shows three products, so one
    attribute must repeat. Saying only "1.0 repeated" would read as a flaw."""

    from siamang.design import cbc_design

    design = cbc_design(ATTRIBUTES, LEVELS, alternatives=3, tasks=10, versions=8, seed=1)
    assert design.balance.overlap_min == 1  # only `size` is short of levels
    assert design.balance.overlap <= design.balance.overlap_min + 0.001
    # With four alternatives, everything but `price` is short of levels.
    wider = cbc_design(ATTRIBUTES, LEVELS, alternatives=4, tasks=10, versions=8, seed=1)
    assert wider.balance.overlap_min == 3


def test_d_error_prefers_a_design_that_can_actually_be_estimated():
    """The criterion has to be able to tell a good design from a bad one, or
    choosing between random starts by it is theater."""

    from siamang.design import _d_error, cbc_design

    design = cbc_design(ATTRIBUTES, LEVELS, alternatives=3, tasks=10, versions=4, seed=2)
    # A design where every alternative in a task is identical carries no
    # information at all about anything.
    flat = [[tuple([task[0]] * 3) for task in version] for version in design.versions]
    assert _d_error(flat, LEVELS) > design.balance.d_error
    assert design.balance.d_error > 0


def test_more_tasks_estimate_more_precisely():
    from siamang.design import cbc_design

    small = cbc_design(ATTRIBUTES, LEVELS, alternatives=3, tasks=6, versions=4, seed=8)
    large = cbc_design(ATTRIBUTES, LEVELS, alternatives=3, tasks=18, versions=4, seed=8)
    assert large.balance.d_error < small.balance.d_error


def test_versions_wrap_and_a_bad_conjoint_says_why():
    from siamang.design import cbc_design

    design = cbc_design(ATTRIBUTES, LEVELS, alternatives=2, tasks=3, versions=2, seed=1)
    assert design.task(5, 0) == design.task(1, 0)

    with pytest.raises(ValueError, match="own list of levels"):
        cbc_design(["a", "b"], [["x", "y"]])
    with pytest.raises(ValueError, match="at least two attributes"):
        cbc_design(["a"], [["x", "y"]])
    with pytest.raises(ValueError, match="at least two levels"):
        cbc_design(["a", "b"], [["x"], ["y", "z"]])
    with pytest.raises(ValueError, match="at least two alternatives"):
        cbc_design(ATTRIBUTES, LEVELS, alternatives=1)
    with pytest.raises(ValueError, match="at least one task"):
        cbc_design(ATTRIBUTES, LEVELS, tasks=0)
    with pytest.raises(ValueError, match="at least one version"):
        cbc_design(ATTRIBUTES, LEVELS, versions=0)


def test_a_design_too_small_to_fit_says_so_instead_of_failing():
    """Two binary tasks cannot estimate three parameters, and no amount of
    fieldwork fixes that. The researcher gets the design and the reason, not a
    crash — and not a very large number, which would read as merely imprecise."""

    import json

    from siamang.design import cbc_design

    design = cbc_design(
        ["a", "b"], [["x", "y"], [1, 2, 3]], alternatives=2, tasks=2, versions=1, seed=42
    )
    assert design.balance.d_error is None
    assert "not estimable" in str(design.balance)
    json.dumps(design.to_dict())  # infinity is not valid JSON; None is


def test_the_conjoint_generator_is_pinned_too():
    """Same reason as the MaxDiff golden: a questionnaire stores a seed, not a
    table, so changing the heuristic rewrites what past studies asked."""

    from siamang.design import cbc_design

    design = cbc_design(
        ["brand", "price"], [["x", "y"], [1, 2, 3]], alternatives=2, tasks=6, versions=1, seed=42
    )
    assert [[list(map(list, task)) for task in version] for version in design.versions] == [
        [
            [["x", 1], ["y", 2]],
            [["x", 3], ["y", 1]],
            [["x", 3], ["y", 2]],
            [["x", 2], ["y", 1]],
            [["y", 3], ["x", 1]],
            [["x", 2], ["y", 3]],
        ]
    ]
