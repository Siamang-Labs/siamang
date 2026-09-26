"""Key drivers: Johnson's relative weights and the Shapley value (LMG) split of R².

The reference values are quoted, not computed here: R 4.4's ``relaimpo``
2.2-7 (``calc.relimp(type = "lmg")``, with and without weights) and ``lm`` on
the ``swiss`` data its documentation uses, and Johnson's weights as the Python
package ``relativeImp`` 0.0.2 computes them on ``swiss`` and on the example R's
``rwa`` package documents (``mtcars``: mpg on cyl, disp, hp and gear). The
two-predictor case is worked by hand.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from siamang.core.variable import MissingValue, Variable, VariableMap
from siamang.data import SurveyData, drivers

# fmt: off
SWISS = [  # Fertility, Agriculture, Examination, Education, Catholic, Infant.Mortality
    (80.2, 17, 15, 12, 9.96, 22.2),
    (83.1, 45.1, 6, 9, 84.84, 22.2),
    (92.5, 39.7, 5, 5, 93.4, 20.2),
    (85.8, 36.5, 12, 7, 33.77, 20.3),
    (76.9, 43.5, 17, 15, 5.16, 20.6),
    (76.1, 35.3, 9, 7, 90.57, 26.6),
    (83.8, 70.2, 16, 7, 92.85, 23.6),
    (92.4, 67.8, 14, 8, 97.16, 24.9),
    (82.4, 53.3, 12, 7, 97.67, 21),
    (82.9, 45.2, 16, 13, 91.38, 24.4),
    (87.1, 64.5, 14, 6, 98.61, 24.5),
    (64.1, 62, 21, 12, 8.52, 16.5),
    (66.9, 67.5, 14, 7, 2.27, 19.1),
    (68.9, 60.7, 19, 12, 4.43, 22.7),
    (61.7, 69.3, 22, 5, 2.82, 18.7),
    (68.3, 72.6, 18, 2, 24.2, 21.2),
    (71.7, 34, 17, 8, 3.3, 20),
    (55.7, 19.4, 26, 28, 12.11, 20.2),
    (54.3, 15.2, 31, 20, 2.15, 10.8),
    (65.1, 73, 19, 9, 2.84, 20),
    (65.5, 59.8, 22, 10, 5.23, 18),
    (65, 55.1, 14, 3, 4.52, 22.4),
    (56.6, 50.9, 22, 12, 15.14, 16.7),
    (57.4, 54.1, 20, 6, 4.2, 15.3),
    (72.5, 71.2, 12, 1, 2.4, 21),
    (74.2, 58.1, 14, 8, 5.23, 23.8),
    (72, 63.5, 6, 3, 2.56, 18),
    (60.5, 60.8, 16, 10, 7.72, 16.3),
    (58.3, 26.8, 25, 19, 18.46, 20.9),
    (65.4, 49.5, 15, 8, 6.1, 22.5),
    (75.5, 85.9, 3, 2, 99.71, 15.1),
    (69.3, 84.9, 7, 6, 99.68, 19.8),
    (77.3, 89.7, 5, 2, 100, 18.3),
    (70.5, 78.2, 12, 6, 98.96, 19.4),
    (79.4, 64.9, 7, 3, 98.22, 20.2),
    (65, 75.9, 9, 9, 99.06, 17.8),
    (92.2, 84.6, 3, 3, 99.46, 16.3),
    (79.3, 63.1, 13, 13, 96.83, 18.1),
    (70.4, 38.4, 26, 12, 5.62, 20.3),
    (65.7, 7.7, 29, 11, 13.79, 20.5),
    (72.7, 16.7, 22, 13, 11.22, 18.9),
    (64.4, 17.6, 35, 32, 16.92, 23),
    (77.6, 37.6, 15, 7, 4.97, 20),
    (67.6, 18.7, 25, 7, 8.65, 19.5),
    (35, 1.2, 37, 53, 42.34, 18),
    (44.7, 46.6, 16, 29, 50.43, 18.2),
    (42.8, 27.7, 22, 29, 58.33, 19.3),
]
MTCARS = [  # mpg, cyl, disp, hp, gear
    (21, 6, 160, 110, 4),
    (21, 6, 160, 110, 4),
    (22.8, 4, 108, 93, 4),
    (21.4, 6, 258, 110, 3),
    (18.7, 8, 360, 175, 3),
    (18.1, 6, 225, 105, 3),
    (14.3, 8, 360, 245, 3),
    (24.4, 4, 146.7, 62, 4),
    (22.8, 4, 140.8, 95, 4),
    (19.2, 6, 167.6, 123, 4),
    (17.8, 6, 167.6, 123, 4),
    (16.4, 8, 275.8, 180, 3),
    (17.3, 8, 275.8, 180, 3),
    (15.2, 8, 275.8, 180, 3),
    (10.4, 8, 472, 205, 3),
    (10.4, 8, 460, 215, 3),
    (14.7, 8, 440, 230, 3),
    (32.4, 4, 78.7, 66, 4),
    (30.4, 4, 75.7, 52, 4),
    (33.9, 4, 71.1, 65, 4),
    (21.5, 4, 120.1, 97, 3),
    (15.5, 8, 318, 150, 3),
    (15.2, 8, 304, 150, 3),
    (13.3, 8, 350, 245, 3),
    (19.2, 8, 400, 175, 3),
    (27.3, 4, 79, 66, 4),
    (26, 4, 120.3, 91, 5),
    (30.4, 4, 95.1, 113, 5),
    (15.8, 8, 351, 264, 5),
    (19.7, 6, 145, 175, 5),
    (15, 8, 301, 335, 5),
    (21.4, 4, 121, 109, 4),
]
# fmt: on

SWISS_PREDICTORS = ["Agriculture", "Examination", "Education", "Catholic", "Infant.Mortality"]


def _swiss(weight: bool = False) -> SurveyData:
    columns = ["Fertility", *SWISS_PREDICTORS]
    frame = pd.DataFrame(SWISS, columns=columns)
    if weight:
        # relaimpo's weighted example below: w = 1 + (row %% 3), rows from 1.
        frame["w"] = 1 + np.arange(1, len(frame) + 1) % 3
        return SurveyData(frame=frame).with_weight("w")
    return SurveyData(frame=frame)


# ─── the numbers ─────────────────────────────────────────────────────────────


def test_shapley_matches_relaimpo_lmg_on_swiss():
    """calc.relimp(lm(Fertility ~ ., swiss), type = "lmg"): R² 0.706735001593;
    lmg 0.0570912207681, 0.1711730289002, 0.2601346786244, 0.1055701503735,
    0.1127659229265 (Agriculture … Infant.Mortality); rela = TRUE: 0.0807816517357,
    0.2422025632160, 0.3680795178364, 0.1493772773891, 0.1595589898228."""

    result = drivers.analyze(_swiss(), "Fertility", SWISS_PREDICTORS, method="shapley")
    assert result.r_squared == pytest.approx(0.706735001593, abs=1e-11)
    lmg = [0.0570912207681, 0.1711730289002, 0.2601346786244, 0.1055701503735, 0.1127659229265]
    assert list(result.importance) == pytest.approx(lmg, abs=1e-12)
    rela = [0.0807816517357, 0.2422025632160, 0.3680795178364, 0.1493772773891, 0.1595589898228]
    assert list(result.percent / 100) == pytest.approx(rela, abs=1e-12)
    # lm's standardized coefficients: b · sd(x) / sd(y).
    betas = [-0.312921282500, -0.164778222539, -0.670400780106, 0.347600028144, 0.251135976299]
    assert list(result.betas) == pytest.approx(betas, abs=1e-11)
    # relaimpo's "first": the squared correlations with the outcome.
    first = [0.124664909906, 0.417164470501, 0.440615646724, 0.215003501619, 0.173518927325]
    assert list(result.correlations**2) == pytest.approx(first, abs=1e-11)


def test_the_table_and_the_tests_are_lm_s():
    """summary(lm(Fertility ~ ., swiss)): F = 19.7610592622 on 5 and 41 df
    (p-value 5.594e-10), adjusted R² 0.670970977397; the coefficients' p
    Agriculture 1.87271543852e-02, Examination 0.315461723144, Education
    2.43060459074e-05, Catholic 5.19007854517e-03, Infant.Mortality
    7.33571532060e-03 — a standardized β has the t of its raw coefficient."""

    result = drivers.analyze(_swiss(), "Fertility", SWISS_PREDICTORS)
    stats = result.stats
    assert stats["Method"] == "Johnson's relative weights"
    assert stats["N"] == 47 and stats["Drivers"] == 5 and stats["Excluded"] == 0
    assert stats["R²"] == 0.7067 and stats["Adjusted R²"] == 0.671
    assert stats["F"] == 19.761 and stats["df"] == "5, 41" and stats["p"] == 5.594e-10
    table = result.table.to_frame()
    assert list(table.columns) == [
        "Rank",
        "Driver",
        "r",
        "Beta",
        "Beta p",
        "VIF",
        "Relative weight",
        "% of R²",
    ]
    # Largest share first.
    assert list(table["Driver"]) == [
        "Education",
        "Examination",
        "Infant.Mortality",
        "Catholic",
        "Agriculture",
    ]
    by_name = table.set_index("Driver")
    assert by_name.loc["Agriculture", "Beta p"] == 0.01873
    assert by_name.loc["Examination", "Beta p"] == 0.3155
    assert by_name.loc["Education", "Beta p"] == 2.431e-05
    assert by_name.loc["Catholic", "Beta p"] == 0.00519
    assert by_name.loc["Infant.Mortality", "Beta p"] == 0.007336
    assert table["% of R²"].sum() == pytest.approx(100, abs=0.2)
    # Agriculture correlates positively and weighs negatively: a suppressor.
    assert stats["Warning"].startswith("Agriculture: the beta has the opposite sign")
    assert result.table.analysis is result
    assert json.dumps(stats)


def test_relative_weights_match_relativeimp_and_the_rwa_example():
    """relativeImp(swiss, "Fertility", …): 0.048416895812, 0.154708249806,
    0.271964104646, 0.114680029948, 0.116965721381. On rwa's mtcars example
    (mpg ~ cyl + disp + hp + gear): 0.228479725928, 0.222146870540,
    0.232174439299, 0.096388603215, rescaled 29.322736660925, 28.509987739305,
    29.796910493120, 12.370365106650 %, R² 0.779189638983 (relaimpo's R²)."""

    swiss = drivers.analyze(_swiss(), "Fertility", SWISS_PREDICTORS)
    weights = [0.048416895812, 0.154708249806, 0.271964104646, 0.114680029948, 0.116965721381]
    assert list(swiss.importance) == pytest.approx(weights, abs=1e-12)
    cars = SurveyData(frame=pd.DataFrame(MTCARS, columns=["mpg", "cyl", "disp", "hp", "gear"]))
    result = drivers.analyze(cars, "mpg", ["cyl", "disp", "hp", "gear"])
    assert list(result.importance) == pytest.approx(
        [0.228479725928, 0.222146870540, 0.232174439299, 0.096388603215], abs=1e-12
    )
    assert list(result.percent) == pytest.approx(
        [29.322736660925, 28.509987739305, 29.796910493120, 12.370365106650], abs=1e-9
    )
    assert result.r_squared == pytest.approx(0.779189638983, abs=1e-11)
    # relaimpo's lmg on the same model: cyl 0.2470520332352, disp 0.2434995947956,
    # hp 0.2109128995443, gear 0.0777251114079 — close to Johnson's, not equal.
    lmg = drivers.analyze(cars, "mpg", ["cyl", "disp", "hp", "gear"], method="shapley")
    assert list(lmg.importance) == pytest.approx(
        [0.2470520332352, 0.2434995947956, 0.2109128995443, 0.0777251114079], abs=1e-12
    )


def test_two_predictors_by_hand():
    """r₁₂ = 0.5, r_y1 = 0.6, r_y2 = 0.4. R² = (0.36 + 0.16 − 2 · 0.6 · 0.4 · 0.5)
    / (1 − 0.25) = 0.28 / 0.75. LMG: predictor 1 gains 0.36 alone and R² − 0.16
    after 2, so ½ (0.36 + 0.28/0.75 − 0.16) = 0.28667; predictor 2 gets the rest.
    Johnson: Λ½ = [[a, b], [b, a]] with a, b = (√1.5 ± √0.5) / 2, β* = Λ½⁻¹ r,
    weight₁ = a² β*₁² + b² β*₂² — the same 0.28667 (with two predictors the two
    methods agree)."""

    r_xx = np.array([[1.0, 0.5], [0.5, 1.0]])
    r_xy = np.array([0.6, 0.4])
    r2 = 0.28 / 0.75
    expected = [0.5 * (0.36 + r2 - 0.16), 0.5 * (0.16 + r2 - 0.36)]
    assert list(drivers.shapley(r_xx, r_xy)) == pytest.approx(expected)
    a, b = (1.5**0.5 + 0.5**0.5) / 2, (1.5**0.5 - 0.5**0.5) / 2
    star = np.linalg.solve([[a, b], [b, a]], r_xy)
    by_hand = [a**2 * star[0] ** 2 + b**2 * star[1] ** 2, b**2 * star[0] ** 2 + a**2 * star[1] ** 2]
    assert by_hand == pytest.approx(expected)
    assert list(drivers.relative_weights(r_xx, r_xy)) == pytest.approx(by_hand)
    # Uncorrelated predictors: each gets exactly its squared correlation.
    assert list(drivers.relative_weights(np.eye(3), [0.5, 0.3, 0.1])) == pytest.approx(
        [0.25, 0.09, 0.01]
    )
    assert list(drivers.shapley(np.eye(3), [0.5, 0.3, 0.1])) == pytest.approx([0.25, 0.09, 0.01])
    assert drivers.subset_r_squared(r_xx, r_xy)[0b11] == pytest.approx(r2)


def test_weights_reach_every_number_as_relaimpo_weighs():
    """calc.relimp(lm(Fertility ~ ., swiss, weights = w), type = "lmg") with
    w = 1 + (1:47 %% 3): R² 0.694332891423; lmg 0.0518208063017,
    0.1549452302086, 0.2559770835712, 0.1019573530969, 0.1296324182449."""

    result = drivers.analyze(_swiss(weight=True), "Fertility", SWISS_PREDICTORS, method="shapley")
    assert result.r_squared == pytest.approx(0.694332891423, abs=1e-11)
    lmg = [0.0518208063017, 0.1549452302086, 0.2559770835712, 0.1019573530969, 0.1296324182449]
    assert list(result.importance) == pytest.approx(lmg, abs=1e-12)
    stats = result.stats
    w = 1 + np.arange(1, 48) % 3
    base = w.sum() ** 2 / (w**2).sum()
    assert stats["Weight"] == "w" and stats["Effective N"] == round(base, 1)
    assert stats["Tests on"] == "Kish's effective N"
    assert stats["df"] == f"5, {round(base - 6, 2)}"
    # Equal weights are no weights.
    even = _swiss().frame.assign(w=2.5)
    same = drivers.analyze(SurveyData(frame=even).with_weight("w"), "Fertility", SWISS_PREDICTORS)
    plain = drivers.analyze(_swiss(), "Fertility", SWISS_PREDICTORS)
    assert list(same.importance) == pytest.approx(list(plain.importance), abs=1e-12)
    assert same.stats["F"] == plain.stats["F"]


# ─── on survey data ──────────────────────────────────────────────────────────


def _ratings(n: int = 200) -> SurveyData:
    rng = np.random.default_rng(4)
    common = rng.normal(size=n)
    x = np.column_stack([0.5 * common + rng.normal(size=n) for _ in range(3)])
    y = x @ [0.6, 0.3, 0.1] + rng.normal(size=n)
    frame = pd.DataFrame(np.round(x + 5).clip(1, 9), columns=["price", "service", "range"])
    frame["overall"] = np.round(y + 5).clip(1, 9)
    frame.loc[:4, "service"] = 99  # Don't know
    frame["region"] = rng.integers(1, 4, n)
    frame["member"] = rng.integers(0, 2, n)
    dk = (MissingValue(99, "Don't know"),)
    variables = VariableMap()
    variables.add_many(
        [
            Variable("overall", "interval", label="Overall rating"),
            Variable("price", "interval", label="Value for money"),
            Variable("service", "interval", label="Service", missing=dk),
            Variable("range", "interval", label="Product range"),
            Variable("region", "nominal", label="Region",
                     labels={1: "North", 2: "South", 3: "West"}),
            Variable("member", "nominal", label="Member", labels={0: "No", 1: "Yes"}),
        ]
    )  # fmt: skip
    return SurveyData(frame=frame, variables=variables)


def test_missing_codes_binary_nominals_and_what_is_refused():
    data = _ratings()
    result = drivers.analyze(data, "overall", ["price", "service", "range", "member"])
    stats = result.stats
    assert stats["N"] == 195 and stats["Excluded"] == 5
    assert stats["Missing codes"] == "5 answers with a missing code (99 = Don't know) left out"
    assert stats["Outcome"] == "Overall rating"
    assert result.table.to_frame()["Driver"][0] == "Value for money"
    with pytest.raises(ValueError, match=r"Region is nominal with 3 answers \(1 = North, 2 = So"):
        drivers.analyze(data, "overall", ["price", "region"])
    with pytest.raises(ValueError, match="two or more predictors; 1 was given"):
        drivers.analyze(data, "overall", ["price"])
    flat = data.with_frame(data.frame.assign(range=3.0))
    with pytest.raises(ValueError, match="Product range is the same for every respondent"):
        drivers.analyze(flat, "overall", ["price", "range"])
    twice = data.with_frame(data.frame.assign(total=data.frame["price"] + data.frame["range"]))
    with pytest.raises(ValueError, match="Value for money, Product range, total are collinear"):
        drivers.analyze(twice, "overall", ["price", "range", "total"])
    with pytest.raises(ValueError, match="price is listed twice"):
        drivers.analyze(data, "overall", ["price", "price"])
    few = data.with_frame(data.frame.iloc[:8])
    with pytest.raises(ValueError, match="needs at least 5 respondents .*; there are 3"):
        drivers.analyze(few, "overall", ["price", "service", "range"])
    with pytest.raises(ValueError, match="method must be one of"):
        drivers.analyze(data, "overall", ["price", "range"], method="dominance")
    listed = data.with_frame(data.frame.assign(price=[[1, 2]] * len(data.frame)))
    with pytest.raises(TypeError, match="prepare.explode"):
        drivers.analyze(listed, "overall", ["price", "range"])


def test_shapley_is_refused_beyond_its_limit_and_collinearity_is_warned():
    rng = np.random.default_rng(9)
    x = rng.normal(size=(120, 16))
    frame = pd.DataFrame(x, columns=[f"x{i}" for i in range(16)])
    frame["y"] = x.sum(axis=1) + rng.normal(size=120)
    data = SurveyData(frame=frame)
    names = [f"x{i}" for i in range(16)]
    with pytest.raises(ValueError, match="with 16 that is 65,536 subset regressions"):
        drivers.analyze(data, "y", names, method="shapley")
    assert drivers.count_problem("shapley", 15) is None
    assert drivers.analyze(data, "y", names).stats["Drivers"] == 16  # Johnson's: no limit
    near = data.with_frame(frame.assign(x1=frame["x0"] + rng.normal(scale=0.2, size=120)))
    warned = drivers.analyze(near, "y", ["x0", "x1", "x2"])
    assert warned.stats["Warning"].startswith("strong collinearity — VIF x0 (")
    assert "x1 (" in warned.stats["Warning"] and "x2 (" not in warned.stats["Warning"]


def test_weighted_survey_data_says_so():
    data = _ratings()
    weighted = data.with_frame(data.frame.assign(w=np.linspace(0.5, 1.5, 200))).with_weight("w")
    result = drivers.analyze(weighted, "overall", ["price", "service", "range"])
    assert result.stats["Weight"] == "w" and result.weight == "w"
    assert "Effective N" in result.stats


# ─── the chart ───────────────────────────────────────────────────────────────


def _bars(fig):
    ax = fig.axes[0]
    return ax, [patch for patch in ax.patches if patch.get_width() > 0]


def test_the_chart_draws_every_driver_largest_first(tmp_path):
    result = drivers.analyze(_swiss(weight=True), "Fertility", SWISS_PREDICTORS)
    fig = drivers.plot(result)
    path = tmp_path / "drivers.png"
    fig.savefig(path)
    assert path.stat().st_size > 10_000
    ax, bars = _bars(fig)
    assert len(bars) == 5
    # Top to bottom, the table's order: bar lengths are the % of R².
    table = result.table.to_frame()
    tops = sorted(bars, key=lambda bar: bar.get_y())
    assert [round(bar.get_width(), 1) for bar in tops] == list(table["% of R²"])
    assert [label.get_text() for label in ax.get_yticklabels()] == list(table["Driver"])
    # Agriculture's beta is negative: its bar is the second colour, with a legend.
    colours = {bar.get_facecolor()[:3] for bar in bars}
    assert len(colours) == 2
    negative = [bar for bar in tops if bar.get_facecolor()[:3] != tops[0].get_facecolor()[:3]]
    assert len(negative) == 2  # Education and Agriculture
    assert [text.get_text() for text in ax.get_legend().get_texts()] == [
        "positive beta",
        "negative beta",
    ]
    title = ax.get_title(loc="left")
    assert title.splitlines() == [
        "Key drivers of Fertility",
        "Johnson's relative weights, R² = 0.694",
        "weighted by 'w'",
    ]
    values = [text.get_text() for text in ax.texts]
    assert values == [f"{value:.1f} %" for value in table["% of R²"]]


def test_the_chart_wraps_long_labels_and_grows_with_the_drivers():
    rng = np.random.default_rng(2)
    x = rng.normal(size=(300, 14))
    frame = pd.DataFrame(x, columns=[f"q{i}" for i in range(14)])
    frame["y"] = x @ np.linspace(1, 0.1, 14) + rng.normal(size=300)
    variables = VariableMap()
    variables.add_many(
        [
            Variable(f"q{i}", "interval", label=f"A long attribute statement number {i} about "
                     "how the service was delivered in the store and online")
            for i in range(14)
        ]
    )  # fmt: skip
    result = drivers.analyze(SurveyData(frame=frame, variables=variables), "y", list(frame)[:14])
    fig = drivers.plot(result)
    ax, bars = _bars(fig)
    assert len(bars) == 14 and ax.get_legend() is None  # every beta positive: one colour
    assert fig.get_size_inches()[1] > 6  # taller than the default for fourteen rows
    labels = [label.get_text() for label in ax.get_yticklabels()]
    assert all(1 < label.count("\n") + 1 <= 3 for label in labels)
    # A third of the 10-inch width at 9 pt: 48 characters a line.
    assert all(len(line) <= 48 for label in labels for line in label.splitlines())
    # A figure too short for its rows grows rather than print labels over each
    # other; one tall enough keeps its size.
    small = drivers.plot(result, figsize=(8, 5), title="Drivers")
    assert small.get_size_inches()[0] == 8 and small.get_size_inches()[1] > 8
    assert small.axes[0].get_title(loc="left").startswith("Drivers\n")
    assert tuple(drivers.plot(result, figsize=(8, 20)).get_size_inches()) == (8, 20)
    narrow = drivers.plot(result, figsize=(5, 4))
    labels = [label.get_text() for label in narrow.axes[0].get_yticklabels()]
    assert all(label.count("\n") == 2 and label.endswith("…") for label in labels)
