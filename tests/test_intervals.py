"""siamang.data.intervals — the intervals a chart's error bars show.

Reference values are R's (``t.test``, ``prop.test`` without continuity
correction, and svymean's linearization formula evaluated in R) and samplics'
TaylorEstimator, an independent implementation of the same linearization —
quoted, not imported.
"""

from __future__ import annotations

import pytest

from siamang.data.intervals import (
    mean_interval,
    proportion_interval,
    share_interval,
    t_interval,
)


def test_the_mean_interval_is_students_t_as_r_gives_it():
    # R: t.test(c(2, 4, 4, 5, 7, 8))$conf.int -> 2.70080170952 7.29919829048;
    # conf.level = 0.9 -> 3.19768594371 6.80231405629.
    # The ends go through t.ppf, which SciPy 1.11 gives about 1e-9 off R's
    # (2.5705818366 for t(0.975, 5) against 2.5705818356): relative 1e-8.
    interval = mean_interval([2, 4, 4, 5, 7, 8])
    assert interval.estimate == 5.0 and interval.n == 6
    assert interval.lower == pytest.approx(2.70080170952, rel=1e-8)
    assert interval.upper == pytest.approx(7.29919829048, rel=1e-8)
    ninety = mean_interval([2, 4, 4, 5, 7, 8], confidence=0.9)
    assert (ninety.lower, ninety.upper) == pytest.approx((3.19768594371, 6.80231405629), rel=1e-8)
    # From a table's numbers: the SD of those six is 2.19089023002.
    table = t_interval(5.0, 2.19089023002, 6)
    assert (table.lower, table.upper) == pytest.approx((2.70080170952, 7.29919829048), rel=1e-8)


def test_the_weighted_mean_interval_is_the_linearization_one():
    """svymean's SE for ids = ~1: √(n/(n−1) Σ w²(y − ȳ)²) / Σw, with t(n − 1).

    Hand-computed in R from that formula: mean 3.225, SE 0.536855930734,
    interval 1.911360860729 – 4.538639139271. samplics' TaylorEstimator
    (an independent implementation of the same linearization) gives
    3.225, 0.5368559307342924, 1.9113608607287924, 4.538639139271208.
    """
    y = [3, 5, 2, 4, 4, 1, 5]
    w = [1.5, 0.5, 2, 1, 1, 0.8, 1.2]
    interval = mean_interval(y, w)
    assert interval.estimate == pytest.approx(3.225)
    assert interval.se == pytest.approx(0.536855930734, abs=1e-11)
    # The ends use t.ppf: relative 1e-8, which SciPy 1.11's quantile meets.
    assert (interval.lower, interval.upper) == pytest.approx(
        (1.911360860729, 4.538639139271), rel=1e-8
    )
    # Equal weights are the unweighted interval, whatever their size.
    plain = mean_interval(y)
    for scale in (1.0, 2.5):
        equal = mean_interval(y, [scale] * len(y))
        assert (equal.lower, equal.upper) == pytest.approx((plain.lower, plain.upper), abs=1e-12)


def test_a_weight_of_zero_or_missing_takes_no_part():
    interval = mean_interval([1, 2, 100, 3], [1, 1, 0, 1])
    assert interval.n == 3 and interval.estimate == 2.0
    same = mean_interval([1, 2, 3])
    assert (interval.lower, interval.upper) == pytest.approx((same.lower, same.upper))
    missing = mean_interval([1, 2, 100, 3], [1, 1, float("nan"), 1])
    assert missing.estimate == 2.0 and missing.n == 3
    with pytest.raises(ValueError, match="negative"):
        mean_interval([1, 2], [1, -1])


def test_no_interval_is_said_rather_than_drawn():
    assert mean_interval([]).note == "no answers" and not mean_interval([]).defined
    one = mean_interval([4.0])
    assert one.estimate == 4.0 and not one.defined and one.note == "one answer has no interval"
    assert mean_interval([1, 2], [0, 0]).note == "no answer carries weight"
    assert t_interval(3.0, None, 1).note == "one answer has no interval"
    assert t_interval(None, None, 0).note == "no answers"
    # No spread: an interval of no width, not an error.
    flat = mean_interval([3, 3, 3])
    assert flat.lower == flat.upper == 3.0


def test_the_share_interval_is_wilsons_as_prop_test_gives_it():
    # R: prop.test(12, 40, correct = FALSE)$conf.int -> 0.180748452297 0.454300188181;
    # prop.test(0, 25, ...) -> 0 0.133192250939; prop.test(25, 25, ...) -> 0.866807749061 1.
    share = proportion_interval(12, 40)
    assert share.estimate == 0.3
    assert (share.lower, share.upper) == pytest.approx((0.180748452297, 0.454300188181), abs=1e-11)
    none = proportion_interval(0, 25)
    assert none.lower == 0.0 and none.upper == pytest.approx(0.133192250939, abs=1e-11)
    every = proportion_interval(25, 25)
    assert every.upper == 1.0 and every.lower == pytest.approx(0.866807749061, abs=1e-11)
    assert proportion_interval(0, 0).note == "no answers"
    with pytest.raises(ValueError):
        proportion_interval(5, 4)


def test_a_weighted_share_takes_wilsons_interval_on_kishs_effective_base():
    """Six answers weighted 1, 3, 1, 2, 2, 2, the first, second and fifth a yes:
    the share is 6 / 11 and Kish's base (Σw)² / Σw² = 121 / 23 = 5.2609. Wilson's
    interval at that base, by hand: center (p + z²/2n) / (1 + z²/n), half-width
    z √(p(1 − p)/n + z²/4n²) / (1 + z²/n) → 0.202228729206 – 0.850313966386."""
    chose = [True, True, False, False, True, False]
    weights = [1.0, 3.0, 1.0, 2.0, 2.0, 2.0]
    share = share_interval(chose, weights)
    assert share.estimate == pytest.approx(6 / 11)
    assert (share.lower, share.upper) == pytest.approx((0.202228729206, 0.850313966386), abs=1e-11)
    assert share.n == 6 and share.method == "Wilson score on Kish's effective base, weighted"
    # Unweighted it is proportion_interval of the count; equal weights, the same.
    plain = share_interval(chose)
    assert (plain.lower, plain.upper) == (
        proportion_interval(3, 6).lower,
        proportion_interval(3, 6).upper,
    )
    for scale in (1.0, 2.5):
        equal = share_interval(chose, [scale] * 6)
        assert (equal.lower, equal.upper) == pytest.approx((plain.lower, plain.upper), abs=1e-12)
    # A weight of 0 (or missing) takes no part; nobody carrying weight is said.
    dropped = share_interval([True, False, True], [1.0, float("nan"), 0.0])
    assert dropped.n == 1 and dropped.estimate == 1.0 and dropped.upper == 1.0
    assert share_interval([True], [0.0]).note == "no answer carries weight"
    assert share_interval([], []).note == "no answers"
    none = share_interval([False, False], [1.0, 2.0])
    assert none.estimate == 0.0 and none.lower == 0.0
    with pytest.raises(ValueError, match="same length"):
        share_interval([True], [1.0, 2.0])
    with pytest.raises(ValueError, match="negative"):
        share_interval([True, False], [1.0, -1.0])
