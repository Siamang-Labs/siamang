"""Price sensitivity: Van Westendorp (with Newton-Miller-Smith) and Gabor-Granger.

The method is defined in the module's docstring, and these tests hold it to
that definition: by hand on small data, and on larger data against a literal
reading of it (a loop over the respondents) written here.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from siamang.core.variable import MissingValue, Variable, VariableMap
from siamang.data import SurveyData, pricing

QUESTIONS = {"too_cheap": "tc", "cheap": "ch", "expensive": "ex", "too_expensive": "te"}


def _two(weighted: bool = False) -> SurveyData:
    """A: 10, 20, 30, 40; B: 20, 30, 40, 50; C answered out of order (cheap
    below too cheap); D refused one question."""
    frame = pd.DataFrame(
        {
            "tc": [10, 20, 30, 10],
            "ch": [20, 30, 20, 20],
            "ex": [30, 40, 40, 99],
            "te": [40, 50, 50, 40],
            "lc": [5, 4, 3, 5],
            "le": [3, 2, 1, 3],
            "w": [1.0, 1.0, 1.0, 1.0],
        }
    )
    variables = VariableMap()
    variables.add_many(
        [
            Variable("tc", "ratio", label="Too cheap"),
            Variable("ch", "ratio", label="A bargain"),
            Variable("ex", "ratio", label="Getting expensive",
                     missing=(MissingValue(99, "Refused"),)),
            Variable("te", "ratio", label="Too expensive"),
        ]
    )  # fmt: skip
    data = SurveyData(frame=frame, variables=variables)
    return data.with_weight("w") if weighted else data


def test_van_westendorp_by_hand():
    """On the grid 10 … 50: too cheap 100, 50, 0, 0, 0 %; not cheap 0, 0, 50,
    100, 100; not expensive 100, 100, 50, 0, 0; too expensive 0, 0, 0, 50, 100.
    PMC: too cheap − not cheap = 100, 50, −50, … crosses halfway from 20 to 30,
    at 25 (25 %). OPP: too cheap − too expensive = 100, 50, 0, −50, −100 is 0 at
    30. IPP: not expensive − not cheap = 100, 100, 0, … is 0 at 30 (50 %). PME:
    not expensive − too expensive = 100, 100, 50, −50 crosses at 35 (25 %)."""

    result = pricing.van_westendorp(_two(), **QUESTIONS)
    assert result.points == {"PMC": 25.0, "OPP": 30.0, "IPP": 30.0, "PME": 35.0}
    table = result.table.to_frame()
    assert list(table["Point"]) == [
        "Point of marginal cheapness (PMC)",
        "Optimal price point (OPP)",
        "Indifference price point (IPP)",
        "Point of marginal expensiveness (PME)",
    ]
    assert list(table["Price"]) == [25.0, 30.0, 30.0, 35.0]
    assert list(table["Share %"]) == [25.0, 0.0, 50.0, 25.0]
    assert list(table["Where"]) == [
        "too cheap = not cheap",
        "too cheap = too expensive",
        "not cheap = not expensive",
        "not expensive = too expensive",
    ]
    curves = result.curves.to_frame()
    assert list(curves["Price"]) == [10, 20, 30, 40, 50]
    assert list(curves["Too cheap %"]) == [100.0, 50.0, 0.0, 0.0, 0.0]
    assert list(curves["Not cheap %"]) == [0.0, 0.0, 50.0, 100.0, 100.0]
    assert list(curves["Not expensive %"]) == [100.0, 100.0, 50.0, 0.0, 0.0]
    assert list(curves["Too expensive %"]) == [0.0, 0.0, 0.0, 50.0, 100.0]
    stats = result.stats
    assert stats["Method"] == "Van Westendorp price sensitivity meter"
    assert stats["N"] == 2 and stats["Inconsistent"] == 1 and stats["Excluded"] == 1
    assert stats["Inconsistent because"].startswith("their prices are not in the order")
    assert stats["Missing codes"] == "1 answer with a missing code (99 = Refused) left out"
    assert (stats["PMC"], stats["OPP"], stats["IPP"], stats["PME"]) == (25.0, 30.0, 30.0, 35.0)
    assert stats["Range of acceptable prices"] == "25 – 35"
    assert "Weight" not in stats and json.dumps(stats)
    assert result.table.analysis is result and result.curves.analysis is result


def test_the_intersection_is_the_middle_of_where_the_lines_meet():
    prices = [10, 20, 30, 40]
    # They run together from 20 to 30: the point is the middle, 25.
    assert pricing.intersection(prices, [75, 50, 50, 25], [25, 50, 50, 75]) == (25.0, 50.0, None)
    # They cross between two prices: where the straight lines meet.
    assert pricing.intersection(prices, [90, 80, 10, 0], [0, 20, 40, 60])[0] == pytest.approx(
        20 + 10 * 60 / 90
    )
    # They never meet within the prices named.
    assert pricing.intersection(prices, [90, 80, 70, 60], [0, 10, 20, 30]) == (None, None, "above")
    assert pricing.intersection(prices, [10, 5, 0, 0], [20, 30, 40, 50]) == (None, None, "below")
    assert pricing.intersection([], [], []) == (None, None, None)


def _literal(values, weights, grid):
    """The curves as the docstring defines them, respondent by respondent."""
    shares = {key: [] for key in ("too_cheap", "cheap", "expensive", "too_expensive")}
    total = sum(weights)
    for price in grid:
        tc = sum(w for (a, _, _, _), w in zip(values, weights, strict=True) if a >= price)
        ch = sum(w for (_, b, _, _), w in zip(values, weights, strict=True) if b >= price)
        ex = sum(w for (_, _, c, _), w in zip(values, weights, strict=True) if c <= price)
        te = sum(w for (_, _, _, d), w in zip(values, weights, strict=True) if d <= price)
        for key, value in zip(shares, (tc, ch, ex, te), strict=True):
            shares[key].append(value / total * 100)
    return shares


def test_the_curves_follow_their_definition_on_many_respondents():
    rng = np.random.default_rng(8)
    base = rng.uniform(5, 20, 300)
    values = np.column_stack(
        [np.round(base * f, 1) for f in (0.5, 0.8, 1.2, 1.7)]
    )  # ordered by construction
    weights = rng.uniform(0.2, 2.0, 300)
    grid, shares = pricing.curves(*values.T, weights=weights)
    assert list(grid) == sorted(set(values.ravel()))
    literal = _literal([tuple(row) for row in values], list(weights), grid)
    for key, expected in literal.items():
        assert list(shares[key]) == pytest.approx(expected)
    assert shares["not_cheap"] == pytest.approx(100 - shares["cheap"])
    assert shares["not_expensive"] == pytest.approx(100 - shares["expensive"])


def test_weights_are_copies_of_respondents():
    frame = _two().frame
    doubled = _two(weighted=True).with_frame(frame.assign(w=[2.0, 1.0, 1.0, 1.0]))
    weighted = pricing.van_westendorp(doubled, **QUESTIONS)
    copies = SurveyData(frame=pd.concat([frame.iloc[[0]], frame], ignore_index=True))
    plain = pricing.van_westendorp(copies, **QUESTIONS)
    assert weighted.points == pytest.approx(plain.points)
    assert weighted.stats["Weight"] == "w" and weighted.stats["Weighted N"] == 3.0
    assert weighted.stats["N"] == 2 and plain.stats["N"] == 3


def test_newton_miller_smith_by_hand():
    """A buys at their cheap price (20) with likelihood 5 → 0.7 and at their
    expensive price (30) with 3 → 0.3; B at 30 with 4 → 0.5 and at 40 with
    2 → 0.1. A's probability is 0 at 10 and 40, B's 0 at 10, 20 and 50. The
    trial curve is 0, 35, 40, 5, 0 % and price × trial 0, 7, 12, 2, 0: the
    highest trial and the highest revenue are both at 30."""

    result = pricing.van_westendorp(
        _two(), **QUESTIONS, likelihood_cheap="lc", likelihood_expensive="le"
    )
    assert list(result.shares["trial"]) == pytest.approx([0, 35, 40, 5, 0])
    assert list(result.shares["revenue"]) == pytest.approx([0, 7, 12, 2, 0])
    assert result.points["trial"] == 30.0 and result.points["revenue"] == 30.0
    stats = result.stats
    assert stats["Highest trial (NMS)"] == 30 and stats["Trial % at it"] == 40.0
    assert stats["Highest revenue (NMS)"] == 30 and stats["Revenue per respondent at it"] == 12.0
    assert stats["Calibration"] == "5 → 0.7, 4 → 0.5, 3 → 0.3, 2 → 0.1, 1 → 0"
    assert list(result.table.to_frame()["Point"])[-2:] == [
        "Highest trial (NMS)",
        "Highest revenue (NMS)",
    ]
    assert list(result.curves.to_frame()["Trial %"]) == [0.0, 35.0, 40.0, 5.0, 0.0]
    # One base for the points and the trial: those who answered all six.
    frame = _two().frame.assign(lc=[5, None, 3, 5])
    fewer = pricing.van_westendorp(
        _two().with_frame(frame), **QUESTIONS, likelihood_cheap="lc", likelihood_expensive="le"
    )
    assert fewer.stats["N"] == 1 and fewer.stats["Excluded"] == 2
    assert fewer.stats["Excluded because"] == (
        "a missing value in any of the price or likelihood questions (listwise)"
    )
    # A calibration of one's own, keyed as JSON keys are (text).
    own = pricing.van_westendorp(
        _two(), **QUESTIONS, likelihood_cheap="lc", likelihood_expensive="le",
        calibration={"5": 1, "4": 0.8, "3": 0.6, "2": 0.4, "1": 0.2},
    )  # fmt: skip
    # A: 0, 1.0, 0.6, 0; B: 0 at 20, 0.8 at 30, 0.4 at 40 → 0, 50, 70, 20, 0 %.
    assert list(own.shares["trial"]) == pytest.approx([0, 50, 70, 20, 0])
    # Cheap and expensive the same price: the mean of the two probabilities.
    same = pricing.trial([10], [20], [20], [30], [0.6], [0.2], [10, 20, 30])
    assert list(same) == pytest.approx([0, 40, 0])
    with pytest.raises(ValueError, match="both likelihood questions"):
        pricing.van_westendorp(_two(), **QUESTIONS, likelihood_cheap="lc")
    with pytest.raises(ValueError, match="calibration does not turn into a probability"):
        pricing.van_westendorp(
            _two(), **QUESTIONS, likelihood_cheap="lc", likelihood_expensive="le",
            calibration={"5": 0.7, "4": 0.5},
        )  # fmt: skip
    with pytest.raises(ValueError, match="a probability is between 0 and 1"):
        pricing.van_westendorp(
            _two(), **QUESTIONS, likelihood_cheap="lc", likelihood_expensive="le",
            calibration={"5": 70},
        )  # fmt: skip


def test_what_van_westendorp_cannot_read_it_says():
    # One respondent naming 10 four times: the curves cannot all cross.
    one = SurveyData(frame=pd.DataFrame({"tc": [10], "ch": [10], "ex": [10], "te": [10]}))
    result = pricing.van_westendorp(one, **QUESTIONS)
    assert result.points["PMC"] is None and result.points["OPP"] == 10.0
    assert result.stats["Note"] == (
        "PMC: too cheap stays above not cheap at every price named, so they do not meet; "
        "PME: not expensive stays below too expensive at every price named, so they do not meet"
    )
    assert "Range of acceptable prices" not in result.stats
    frame = _two().frame
    backwards = _two().with_frame(frame.assign(tc=frame["te"] + 1))
    with pytest.raises(ValueError, match="No respondent answered all four .* in order"):
        pricing.van_westendorp(backwards, **QUESTIONS)
    negative = _two().with_frame(frame.assign(tc=-1))
    with pytest.raises(ValueError, match="A price cannot be negative"):
        pricing.van_westendorp(negative, **QUESTIONS)
    with pytest.raises(ValueError, match="tc is listed twice"):
        pricing.van_westendorp(_two(), too_cheap="tc", cheap="tc", expensive="ex",
                               too_expensive="te")  # fmt: skip
    text = _two().with_frame(frame.assign(ch=["about 20"] * 4))
    with pytest.raises(TypeError, match="holds text that is not a number"):
        pricing.van_westendorp(text, **QUESTIONS)
    assert (
        pricing.price_problem(
            {"method": "van_westendorp", "too_cheap": "a", "cheap": "a", "expensive": "b"}
        )
        == "a answers more than one of the four price questions; each is its own variable."
    )


# ─── Gabor-Granger ───────────────────────────────────────────────────────────


def _intent() -> SurveyData:
    """Ten respondents, asked at 20, 5, 10 and 15 (in that order); 9, 7, 4 and
    1 of them would buy at 5, 10, 15 and 20. The last also said yes at 20 but
    no at 15 — not monotone. One more refused a question."""
    frame = pd.DataFrame(
        {
            "at20": [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1],
            "at5": [1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1],
            "at10": [1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 9],
            "at15": [1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1],
        }
    )
    variables = VariableMap()
    variables.add_many(
        [
            Variable(name, "nominal", label=f"Would buy at {name[2:]}",
                     labels={0: "No", 1: "Yes"}, missing=(MissingValue(9, "Refused"),))
            for name in frame.columns
        ]
    )  # fmt: skip
    return SurveyData(frame=frame, variables=variables)


def test_gabor_granger_by_hand():
    """Demand 90, 70, 40, 10 % at 5, 10, 15, 20; revenue per respondent 4.5,
    7.0, 6.0, 2.0 — highest at 10 (index 100; 4.5 is 64.3). Arc elasticity from
    5 to 10: (70 − 90) / 80 ÷ (10 − 5) / 7.5 = −0.375."""

    result = pricing.gabor_granger(
        _intent(), ["at20", "at5", "at10", "at15"], prices=[20, 5, 10, 15]
    )
    table = result.table.to_frame()
    assert list(table["Price"]) == [5, 10, 15, 20]
    assert list(table["Question"]) == [
        "Would buy at 5",
        "Would buy at 10",
        "Would buy at 15",
        "Would buy at 20",
    ]
    assert list(table["Would buy %"]) == [90.0, 70.0, 40.0, 10.0]
    assert list(table["Revenue per respondent"]) == [4.5, 7.0, 6.0, 2.0]
    assert list(table["Revenue index"]) == [64.3, 100.0, 85.7, 28.6]
    assert pd.isna(table["Elasticity"][0]) and table["Elasticity"][1] == -0.38
    assert "| 5 | Would buy at 5 | 90.0 | 4.5 | 64.3 |  |" in result.table.to_markdown()
    stats = result.stats
    assert stats["Method"] == "Gabor-Granger" and stats["Counts as yes"] == "1 = Yes"
    assert stats["Revenue-maximizing price"] == 10 and stats["Would buy % at it"] == 70.0
    assert stats["N"] == 10 and stats["Excluded"] == 1 and stats["Not monotone"] == 1
    assert "Missing codes" in stats and json.dumps(stats)
    assert result.points == {"revenue": 10.0}
    assert result.table.analysis is result


def test_gabor_granger_yes_codes_weights_and_refusals():
    scale = SurveyData(
        frame=pd.DataFrame({"a": [5, 4, 3, 2], "b": [4, 2, 2, 1], "w": [1.0, 3.0, 1.0, 1.0]})
    )
    with pytest.raises(ValueError, match="which answer means would buy: the questions hold 1, 2"):
        pricing.gabor_granger(scale, ["a", "b"], prices=[1, 2])
    top_two = pricing.gabor_granger(scale, ["a", "b"], prices=[1, 2], yes=[4, 5])
    assert list(top_two.shares["demand"]) == pytest.approx([50, 25])
    weighted = pricing.gabor_granger(scale.with_weight("w"), ["a", "b"], prices=[1, 2], yes=[4, 5])
    assert list(weighted.shares["demand"]) == pytest.approx([4 / 6 * 100, 1 / 6 * 100])
    assert weighted.stats["Weight"] == "w" and weighted.stats["Weighted N"] == 6.0
    for prices, message in (
        ([1], "lists 1 price for 2 purchase-intent questions"),
        ([1, 1], "Each price can be asked once"),
        ([1, "two"], "Prices must all be numbers"),
        ([-1, 2], "Prices cannot be negative"),
        ("1, 2", "Prices is a list of numbers"),
    ):
        with pytest.raises(ValueError, match=message):
            pricing.gabor_granger(scale, ["a", "b"], prices=prices, yes=[4, 5])
    nobody = pricing.gabor_granger(scale, ["a", "b"], prices=[1, 2], yes=[9])
    assert nobody.stats["Note"].startswith("no respondent would buy")


# ─── the charts ──────────────────────────────────────────────────────────────


def test_the_van_westendorp_chart_draws_the_curves_and_names_the_points(tmp_path):
    result = pricing.van_westendorp(_two(weighted=True), **QUESTIONS)
    fig = pricing.plot(result)
    fig.savefig(tmp_path / "psm.png")
    assert (tmp_path / "psm.png").stat().st_size > 10_000
    assert len(fig.axes) == 1
    ax = fig.axes[0]
    lines = [line for line in ax.get_lines() if line.get_label() in pricing.CURVE_NAMES.values()]
    assert [line.get_label() for line in lines] == [
        "Too cheap",
        "Not cheap",
        "Not expensive",
        "Too expensive",
    ]
    assert [line.get_linestyle() for line in lines] == ["-", "--", "--", "-"]
    assert len({line.get_color() for line in lines}) == 2  # cheapness and expensiveness
    assert list(lines[0].get_ydata()) == [100.0, 50.0, 0.0, 0.0, 0.0]
    names = sorted(text.get_text() for text in ax.texts)
    assert names == ["IPP 30", "OPP 30", "PMC 25", "PME 35"]
    # OPP and IPP share a price: one name sits under the other.
    heights = {text.get_text(): text.get_position()[1] for text in ax.texts}
    assert heights["OPP 30"] != heights["IPP 30"]
    marked = [c for c in ax.collections if len(c.get_offsets()) == 1]
    assert len(marked) == 4
    band = [patch for patch in ax.patches]
    assert len(band) == 1  # the range of acceptable prices, 25 to 35
    legend = fig.legends[0]
    assert [text.get_text() for text in legend.get_texts()] == [
        "Too cheap",
        "Not cheap",
        "Not expensive",
        "Too expensive",
    ]
    assert ax.get_title(loc="left").splitlines() == [
        "Price sensitivity (Van Westendorp)",
        "N = 2, weighted by 'w'",
    ]


def test_the_price_axis_names_the_unit_the_questions_share():
    """ "Too cheap ($ a month)" and the other three: the axis says "Price
    ($ a month)" rather than "Price". Labels that do not share one keep
    "Price"."""

    def labeled(last: str) -> SurveyData:
        variables = VariableMap()
        variables.add_many(
            [
                Variable("tc", "ratio", label="Too cheap ($ a month)"),
                Variable("ch", "ratio", label="A bargain ($ a month)"),
                Variable("ex", "ratio", label="Getting expensive ($ a month)"),
                Variable("te", "ratio", label=f"Too expensive ({last})"),
            ]
        )
        return SurveyData(frame=_two().frame, variables=variables)

    result = pricing.van_westendorp(labeled("$ a month"), **QUESTIONS)
    assert result.unit == "$ a month"
    assert pricing.plot(result).axes[0].get_xlabel() == "Price ($ a month)"
    assert pricing.van_westendorp(labeled("$ a year"), **QUESTIONS).unit is None
    plain = pricing.van_westendorp(_two(), **QUESTIONS)
    assert plain.unit is None and pricing.plot(plain).axes[0].get_xlabel() == "Price"


def test_the_nms_and_gabor_granger_charts_have_a_panel_per_measure():
    nms = pricing.van_westendorp(
        _two(), **QUESTIONS, likelihood_cheap="lc", likelihood_expensive="le"
    )
    fig = pricing.plot(nms, title="Price of the new blend")
    top, bottom = fig.axes
    assert top.get_title(loc="left").startswith("Price of the new blend\n")
    assert list(bottom.get_lines()[0].get_ydata()) == pytest.approx([0, 35, 40, 5, 0])
    assert sorted(text.get_text() for text in bottom.texts) == [
        "highest revenue 30",
        "highest trial 30",
    ]
    gg = pricing.gabor_granger(_intent(), ["at20", "at5", "at10", "at15"], prices=[20, 5, 10, 15])
    fig = pricing.plot(gg, figsize=(8, 7))
    assert tuple(fig.get_size_inches()) == (8, 7)
    demand_ax, revenue_ax = fig.axes
    assert list(demand_ax.get_lines()[0].get_ydata()) == pytest.approx([90, 70, 40, 10])
    bars = revenue_ax.patches
    assert [round(bar.get_height(), 2) for bar in bars] == [4.5, 7.0, 6.0, 2.0]
    colours = [bar.get_facecolor() for bar in bars]
    assert colours[1] != colours[0] and colours[0] == colours[2] == colours[3]
    assert [label.get_text() for label in revenue_ax.get_xticklabels()] == ["5", "10", "15", "20"]
    assert "highest revenue at 10" in [text.get_text() for text in demand_ax.texts]
    assert [text.get_text() for text in revenue_ax.texts] == ["4.50", "7.00", "6.00", "2.00"]


def _text_boxes(fig, texts):
    from matplotlib.text import Text

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    return [Text.get_window_extent(text, renderer) for text in texts]


def _touching(boxes) -> list[tuple[int, int]]:
    return [
        (i, j)
        for i in range(len(boxes))
        for j in range(i + 1, len(boxes))
        if boxes[i].overlaps(boxes[j])
    ]


def test_the_charts_stay_legible_on_small_figures():
    """A figure as a Result chart may ask for: the points named at one price
    (OPP and IPP both at 30) are stacked a text's height apart however short
    the panel, crowded prices are turned rather than run together, and the
    legend takes two rows on a narrow figure instead of running off it."""

    nms = pricing.van_westendorp(
        _two(), **QUESTIONS, likelihood_cheap="lc", likelihood_expensive="le"
    )
    for size in ((10, 4), (6, 3)):
        fig = pricing.plot(nms, figsize=size)
        top, bottom = fig.axes
        for ax in (top, bottom):
            assert _touching(_text_boxes(fig, ax.texts)) == [], (size, ax.get_ylabel())
    legend = pricing.plot(nms, figsize=(5, 6)).legends[0]
    assert legend._ncols == 2
    fig = legend.figure
    box = legend.get_window_extent(fig.canvas.get_renderer())
    assert box.x0 >= 0 and box.x1 <= fig.bbox.width
    assert pricing.plot(nms, figsize=(10, 6)).legends[0]._ncols == 4

    prices = [4.99, 6.99, 8.99, 9.99, 11.99, 14.99, 19.99]
    rng = np.random.default_rng(12)
    wtp = rng.lognormal(np.log(10), 0.4, 200)
    frame = pd.DataFrame({f"p{i}": (wtp >= price).astype(int) for i, price in enumerate(prices)})
    gg = pricing.gabor_granger(SurveyData(frame=frame), list(frame), prices=prices)
    narrow = pricing.plot(gg, figsize=(6, 6)).axes[1]
    assert {label.get_rotation() for label in narrow.get_xticklabels()} == {45.0}
    wide = pricing.plot(gg, figsize=(10, 6)).axes[1]
    assert {label.get_rotation() for label in wide.get_xticklabels()} == {0.0}
    assert _touching(_text_boxes(wide.figure, wide.get_xticklabels())) == []


def test_a_small_gabor_granger_chart_keeps_its_labels_apart():
    """Twelve prices at 5 × 3 inches: the revenue labels ran together
    ("117.73118.22117.70"), the demand labels touched ("24 %24 %"), and
    "highest revenue at 499" ran past the plot's right edge."""

    prices = [99, 149, 199, 249, 299, 349, 399, 449, 499, 549, 599, 649]
    rng = np.random.default_rng(2)
    frame = pd.DataFrame(
        {
            f"gg{i}": (rng.random(800) < 0.9 * np.exp(-p / 350)).astype(float)
            for i, p in enumerate(prices)
        }
    )
    result = pricing.gabor_granger(SurveyData(frame=frame), list(frame), prices=prices)
    best = result.points["revenue"]
    for size in ((5, 3), (10, 6)):
        fig = pricing.plot(result, figsize=size)
        demand_ax, revenue_ax = fig.axes
        renderer = fig.canvas.get_renderer()
        values = [t for t in demand_ax.texts if t.get_text().endswith(" %")], revenue_ax.texts
        for texts in values:
            shown = [text for text in texts if text.get_visible()]
            assert _touching(_text_boxes(fig, shown)) == [], size
        # The best price's numbers are always written.
        revenue = dict(zip(result.prices, result.shares["revenue"], strict=True))
        assert any(
            t.get_visible() and t.get_text() == f"{revenue[best]:.2f}" for t in revenue_ax.texts
        )
        note = next(t for t in demand_ax.texts if t.get_text().startswith("highest revenue"))
        box = note.get_window_extent(renderer)
        plot = demand_ax.get_window_extent(renderer)
        assert plot.x0 <= box.x0 and box.x1 <= plot.x1
    # On a figure with room every value is written.
    wide = pricing.plot(result, figsize=(16, 8))
    assert all(text.get_visible() for ax in wide.axes for text in ax.texts)


def test_the_point_names_leave_the_marked_points_and_the_axis_clear():
    """At 5 × 3.5 inches the IPP marker sat on the "IPP …" name and the PMC
    name ran onto the axis's "100"."""

    rng = np.random.default_rng(2)
    base = rng.lognormal(np.log(2500), 0.35, 800)
    frame = pd.DataFrame(
        {
            "tc": np.round(base * 0.45, -1),
            "ch": np.round(base * 0.7, -1),
            "ex": np.round(base * 1.2, -1),
            "te": np.round(base * 1.7, -1),
        }
    )
    result = pricing.van_westendorp(SurveyData(frame=frame), **QUESTIONS)
    for size in ((5, 3.5), (10, 6)):
        fig = pricing.plot(result, figsize=size)
        ax = fig.axes[0]
        renderer = fig.canvas.get_renderer()
        names = [text for text in ax.texts if text.get_text()[:3] in ("PMC", "OPP", "IPP", "PME")]
        assert len(names) == 4
        plot = ax.get_window_extent(renderer)
        marks = [c for c in ax.collections if len(c.get_offsets()) == 1]
        points = [ax.transData.transform(c.get_offsets()[0]) for c in marks]
        for name in names:
            box = name.get_window_extent(renderer)
            assert plot.x0 <= box.x0 and box.x1 <= plot.x1, (size, name.get_text())
            assert not any(box.padded(2).contains(*point) for point in points), name.get_text()
        assert _touching(_text_boxes(fig, names)) == []
