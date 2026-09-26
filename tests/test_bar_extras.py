"""The Bar chart's Top N, confidence intervals, significance letters, histogram
and donut.

Every expected number is either arithmetic by hand on a small frame, or the
number another part of the engine gives for the same data: the letters are the
Tab book's (and the Banner table's where everyone answered), the intervals
``siamang.data.intervals``' and Proportion CI's, the histogram's counts
``numpy.histogram``'s with the weights. The charts are read from the figure.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
import pytest

from siamang.core.variable import Variable, VariableMap
from siamang.data import SurveyData

matplotlib.use("Agg")

DOCUMENTS = Path(__file__).resolve().parent / "documents"


@pytest.fixture(autouse=True)
def _close_figures():
    import matplotlib.pyplot as plt

    yield
    plt.close("all")


# ─── reading the figure ──────────────────────────────────────────────────────


def _bars(ax) -> list[list[float]]:
    """Each series' bar lengths (one list per series), error bars left aside."""
    from matplotlib.container import BarContainer

    horizontal = ax.get_ylim()[0] > ax.get_ylim()[1]
    return [
        [round(p.get_width() if horizontal else p.get_height(), 3) for p in container]
        for container in ax.containers
        if isinstance(container, BarContainer)
    ]


def _whiskers(ax) -> list[list[tuple[float, float]]]:
    """Each series' error bars as (low, high), in drawing order."""
    from matplotlib.container import ErrorbarContainer

    found = []
    for container in ax.containers:
        if not isinstance(container, ErrorbarContainer):
            continue
        segments = container.lines[2][0].get_segments()
        vertical = segments[0][0][0] == segments[0][1][0]
        axis = 1 if vertical else 0
        found.append([(float(s[0][axis]), float(s[1][axis])) for s in segments])
    return found


def _ticks(ax) -> list[str]:
    labels = ax.get_yticklabels() if ax.get_ylim()[0] > ax.get_ylim()[1] else ax.get_xticklabels()
    return [label.get_text() for label in labels]


def _footnote(chart) -> str:
    return " ".join(text.get_text() for text in chart.plot().figure.texts).replace("\n", " ")


def _rendered(chart, tmp_path, name: str = "chart.png") -> None:
    path = chart.save(tmp_path / name)
    assert path.stat().st_size > 5000  # a real picture


def _colour(patch) -> tuple[float, ...]:
    return tuple(round(c, 3) for c in patch.get_facecolor()[:3])


GREY = (0.72, 0.72, 0.72)


# ─── Top N ───────────────────────────────────────────────────────────────────


def _ranked() -> SurveyData:
    """Answers A–F given 2, 6, 3, 5, 1 and 3 times (20 in all); G never."""
    frame = pd.DataFrame(
        {
            "q": [1] * 2 + [2] * 6 + [3] * 3 + [4] * 5 + [5] * 1 + [6] * 3,
            "g": [1, 2] * 10,
            "m": [[1, 2], [1, 3], [1, 4], [2], [3, 4], [1]] + [None] * 14,
            "w": [1.0, 2.0] * 10,
        }
    )
    variables = VariableMap()
    variables.add_many(
        [
            Variable("q", "nominal", label="Brand", labels=dict(enumerate("ABCDEFG", start=1))),
            Variable("g", "nominal", label="Group", labels={1: "Left", 2: "Right"}),
            Variable("m", "nominal", label="Used", labels={1: "W", 2: "X", 3: "Y", 4: "Z"}),
        ]
    )
    return SurveyData(frame=frame, variables=variables)


def test_top_n_keeps_the_answers_given_most_and_other_combines_the_rest(tmp_path):
    # B 6 and D 5 are the two largest; C and F tie at 3: the first in code order,
    # C, is kept. Other is A + E + F = 2 + 1 + 3 = 6 of 20.
    chart = _ranked().plot.bar("q", show="percent", top=3, other=True)
    _rendered(chart, tmp_path)
    ax = chart.plot()
    assert _ticks(ax) == ["B", "C", "D", "Other"]
    assert _bars(ax) == [[30.0, 15.0, 25.0, 30.0]]
    patches = ax.containers[0].patches
    assert _colour(patches[-1]) == GREY and _colour(patches[0]) != GREY
    assert len({_colour(p) for p in patches[:-1]}) == 1
    assert "The 3 answers given most of 6 are drawn; Other combines the other 3." in _footnote(
        chart
    )
    # Largest first: Other stays last whatever its size.
    ordered = _ranked().plot.bar("q", show="percent", top=3, other=True, sort="value")
    assert _ticks(ordered.plot()) == ["B", "D", "C", "Other"]
    assert _bars(ordered.plot()) == [[30.0, 25.0, 15.0, 30.0]]
    # Without Other the rest are left out, and the note says so.
    alone = _ranked().plot.bar("q", top=2)
    assert _ticks(alone.plot()) == ["B", "D"] and _bars(alone.plot()) == [[6.0, 5.0]]
    assert "The 2 answers given most of 6 are drawn; the other 4 are left out." in _footnote(alone)
    # A Top N of every answer or more draws them all, without a note.
    every = _ranked().plot.bar("q", top=10, other=True)
    assert _ticks(every.plot()) == list("ABCDEF") and "given most" not in _footnote(every)


def test_other_of_a_multiple_choice_question_is_who_named_any_of_the_rest(tmp_path):
    # Six answered. W was named by four; X, Y and Z by two each — six mentions,
    # but by five respondents (all but the one who named W alone): 5 / 6.
    chart = _ranked().plot.bar("m", show="percent", top=1, other=True)
    _rendered(chart, tmp_path)
    assert _ticks(chart.plot()) == ["W", "Other"]
    assert _bars(chart.plot()) == [[66.667, 83.333]]
    assert (
        "The 1 options named most of 4 are drawn; Other is the respondents who named any of "
        "the other 3."
    ) in _footnote(chart)


def test_top_n_with_split_by_is_the_top_overall_and_other_within_each_group(tmp_path):
    data = _ranked().with_weight("w")
    chart = data.plot.bar("q", split="g", show="percent", top=2, other=True)
    _rendered(chart, tmp_path)
    frame = data.frame
    # Overall, weighted: B and D given most. Other: every other answer.
    table = pd.crosstab(frame["q"], frame["g"], values=frame["w"], aggfunc="sum").fillna(0)
    shares = table / table.sum() * 100
    expected = [
        [round(shares.loc[2, g], 3) for g in (1, 2)],
        [round(shares.loc[4, g], 3) for g in (1, 2)],
        [round(shares.drop([2, 4]).sum()[g], 3) for g in (1, 2)],
    ]
    ax = chart.plot()
    assert _bars(ax) == expected
    legend = [text.get_text() for text in ax.get_legend().get_texts()]
    assert legend == ["B", "D", "Other"]
    assert _colour(ax.containers[2].patches[0]) == GREY
    assert "The 2 answers given most overall of 6 are drawn" in _footnote(chart)
    # Stacked to 100 % with Other, every group's bar reaches 100.
    full = data.plot.bar("q", split="g", layout="stacked_100", top=2, other=True)
    assert np.array(_bars(full.plot())).sum(axis=0).round(6).tolist() == [100.0, 100.0]


def test_an_answer_called_other_keeps_its_name_beside_the_combined_one():
    frame = pd.DataFrame({"q": [1, 1, 1, 2, 2, 3, 4]})
    variables = VariableMap()
    variables.add(Variable("q", "nominal", labels={1: "Other", 2: "Acme", 3: "Globex", 4: "X"}))
    chart = SurveyData(frame=frame, variables=variables).plot.bar("q", top=2, other=True)
    assert _ticks(chart.plot()) == ["Other", "Acme", "Other (combined)"]


# ─── confidence intervals ────────────────────────────────────────────────────


def _small() -> SurveyData:
    """The frame of test_bar_forms: 9 is Refused, left out; one blank."""
    frame = pd.DataFrame(
        {
            "q": [1, 1, 2, 3, 9, np.nan, 1, 2],
            "g": [1, 1, 1, 2, 2, 2, 1, 2],
            "score": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 30.0, 80.0],
            "w": [1.0, 3.0, 1.0, 2.0, 1.0, 1.0, 2.0, 2.0],
        }
    )
    variables = VariableMap()
    variables.add_many(
        [
            Variable(
                "q",
                "nominal",
                label="Answer",
                labels={1: "Yes", 2: "No", 3: "Maybe", 9: "Refused"},
                missing_values=(9,),
                missing_labels={9: "Refused"},
            ),
            Variable("g", "nominal", label="Group", labels={1: "Left", 2: "Right"}),
            Variable("score", "interval", label="Score"),
        ]
    )
    return SurveyData(frame=frame, variables=variables)


def test_a_percentage_carries_wilsons_interval_as_prop_test_gives_it(tmp_path):
    # Yes 3, No 2, Maybe 1 of the 6 valid answers. R's prop.test(x, 6,
    # correct = FALSE)$conf.int: 3 → 0.187616306 0.812383694; 2 → 0.096771411
    # 0.700006685.
    from siamang.data.intervals import proportion_interval

    chart = _small().plot.bar("q", show="percent", intervals=True)
    _rendered(chart, tmp_path)
    ax = chart.plot()
    whiskers = _whiskers(ax)[0]
    assert whiskers[0] == pytest.approx((18.7616306, 81.2383694), abs=1e-6)
    assert whiskers[1] == pytest.approx((9.6771411, 70.0006685), abs=1e-6)
    maybe = proportion_interval(1, 6)
    assert whiskers[2] == pytest.approx((maybe.lower * 100, maybe.upper * 100), abs=1e-9)
    assert "Error bars: 95 % confidence intervals (Wilson score)." in _footnote(chart)
    # The value is written past the whisker, not over it.
    yes = next(text for text in ax.texts if text.get_text() == "50.0%")
    assert yes.xy[1] == pytest.approx(81.2383694, abs=1e-6)
    # A 90 % interval is narrower.
    ninety = _small().plot.bar("q", show="percent", intervals=True, confidence=0.9)
    low, high = _whiskers(ninety.plot())[0][0]
    assert low > 18.76 and high < 81.24
    assert "Error bars: 90 % confidence intervals" in _footnote(ninety)


def test_a_weighted_percentage_is_wilson_on_proportion_ci_s_share_and_effective_base(tmp_path):
    """Proportion CI weighs the share and puts it on Kish's effective base; the
    bar's interval is Wilson's at that share and base."""
    from scipy.stats import norm

    data = _small().with_weight("w")
    chart = data.plot.bar("q", show="percent", intervals=True, horizontal=True)
    _rendered(chart, tmp_path)
    clean = data.with_frame(data.frame[data.frame["q"] != 9])
    ci = clean.analysis.proportion_ci("q", 1, weighted=True)
    p, n = ci["p"], ci["n"]
    assert p == pytest.approx(6 / 11) and n == pytest.approx(121 / 23)
    z = norm.ppf(0.975)
    centre = (p + z**2 / (2 * n)) / (1 + z**2 / n)
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / (1 + z**2 / n)
    ax = chart.plot()
    assert _bars(ax)[0][0] == pytest.approx(p * 100, abs=1e-3)
    assert _whiskers(ax)[0][0] == pytest.approx(((centre - half) * 100, (centre + half) * 100))
    assert _whiskers(ax)[0][0] == pytest.approx((20.2228729206, 85.0313966386), abs=1e-8)
    assert "(Wilson score, on Kish's effective base)." in _footnote(chart)


def test_each_group_s_percentage_has_the_interval_of_its_own_base(tmp_path):
    from siamang.data.intervals import proportion_interval

    chart = _small().plot.bar("q", split="g", show="percent", intervals=True)
    _rendered(chart, tmp_path)
    # Left: Yes 3, No 1 of 4; Right: No 1, Maybe 1 of 2.
    expected = [
        [proportion_interval(3, 4), proportion_interval(0, 2)],
        [proportion_interval(1, 4), proportion_interval(1, 2)],
        [proportion_interval(0, 4), proportion_interval(1, 2)],
    ]
    for drawn, series in zip(_whiskers(chart.plot()), expected, strict=True):
        assert np.allclose(drawn, [(i.lower * 100, i.upper * 100) for i in series])


def test_a_mean_by_group_carries_the_interval_the_group_means_chart_draws(tmp_path):
    # R: t.test(c(10, 20, 30, 30))$conf.int → 7.265198192 37.734801808;
    # t.test(c(40, 50, 60, 80)) → 30.324691162 84.675308838.
    from siamang.data.intervals import mean_interval

    chart = _small().plot.bar("score", by="g", intervals=True)
    _rendered(chart, tmp_path)
    assert np.allclose(
        _whiskers(chart.plot())[0],
        [(7.265198192, 37.734801808), (30.324691162, 84.675308838)],
        atol=1e-8,
        rtol=0,
    )
    assert "confidence intervals of the mean (Student's t)." in _footnote(chart)
    weighted = _small().with_weight("w").plot.bar("score", by="g", intervals=True)
    frame = _small().frame
    expected = [
        mean_interval(frame["score"][frame["g"] == g], frame["w"][frame["g"] == g]) for g in (1, 2)
    ]
    assert np.allclose(
        _whiskers(weighted.plot())[0], [(i.lower, i.upper) for i in expected], atol=1e-12
    )
    assert "weighted: the linearization interval" in _footnote(weighted)
    # A group of one answer has no interval, and the note names it.
    one = _small().with_frame(_small().frame.assign(g=[1, 1, 1, 1, 1, 1, 1, 2]))
    single = one.plot.bar("score", by="g", intervals=True)
    assert len(_whiskers(single.plot())[0]) == 1
    assert "No interval for a group of one answer: Right." in _footnote(single)


def test_counts_have_no_intervals_and_the_chart_says_so():
    chart = _small().plot.bar("q", intervals=True)
    assert _whiskers(chart.plot()) == []
    assert "Confidence intervals are drawn for percentages and for means by group" in _footnote(
        chart
    )


# ─── significance letters ────────────────────────────────────────────────────


def _letters(ax) -> dict[tuple[str, str], str]:
    """``{(group label, answer): letters}`` from the bold texts over the bars."""
    groups = [text.split("\n")[0] for text in _ticks(ax)]
    legend = ax.get_legend() or ax.figure.legends[0]
    answers = [text.get_text() for text in legend.get_texts()]
    count = len(answers)
    thickness = 0.8 / count
    found = {}
    for text in ax.texts:
        if text.get_fontweight() not in ("bold", 700):
            continue
        x = text.xy[1] if ax.get_ylim()[0] > ax.get_ylim()[1] else text.xy[0]
        position = int(round(x))
        series = int(round((x - position + 0.4) / thickness - 0.5))
        found[(groups[position], answers[series])] = text.get_text()
    return found


def _tab_letters(data: SurveyData, question: str, banner: str, **kwargs):
    """``{(group label with its letter, answer): letters}`` of the Tab book."""
    from siamang.reporting.tabbook import tabulate

    book = tabulate(data, banner=[banner], questions=[question], **kwargs)
    tab = book.tabs[0]
    found = {}
    for (_code, answer), row in zip(tab.answers, tab.letters, strict=True):
        for column, letters in zip(tab.columns, row, strict=True):
            if column.variable is not None and letters:
                found[(column.header, answer)] = letters
    return found


def _survey(n: int = 600, seed: int = 3) -> SurveyData:
    rng = np.random.default_rng(seed)
    region = rng.choice([1, 2, 3, 4, 9], n, p=[0.3, 0.3, 0.2, 0.15, 0.05])
    shares = {
        1: [0.4, 0.3, 0.2, 0.05, 0.05],
        2: [0.2, 0.3, 0.3, 0.15, 0.05],
        3: [0.1, 0.2, 0.4, 0.25, 0.05],
        4: [0.3, 0.3, 0.2, 0.1, 0.1],
        9: [0.2] * 5,
    }
    answer = np.array([rng.choice([1, 2, 3, 4, 99], p=shares[r]) for r in region], dtype=float)
    answer[rng.random(n) < 0.05] = np.nan
    brands = [
        sorted(rng.choice([1, 2, 3, 4], rng.integers(1, 3), replace=False).tolist())
        if rng.random() > 0.1 * r
        else []
        for r in region
    ]
    frame = pd.DataFrame(
        {
            "region": region.astype(float),
            "rating": answer,
            "brands": brands,
            "w": rng.uniform(0.3, 2.5, n),
        }
    )
    variables = VariableMap()
    variables.add_many(
        [
            Variable(
                "region",
                "nominal",
                label="Region",
                labels={1: "North", 2: "South", 3: "East", 4: "West", 9: "Refused"},
                missing_values=(9,),
                missing_labels={9: "Refused"},
            ),
            Variable(
                "rating",
                "ordinal",
                label="Rating",
                labels={1: "Poor", 2: "Fair", 3: "Good", 4: "Great", 99: "Don't know"},
                missing_values=(99,),
                missing_labels={99: "Don't know"},
            ),
            Variable("brands", "nominal", label="Brands", labels={1: "A", 2: "B", 3: "C", 4: "D"}),
        ]
    )
    return SurveyData(frame=frame, variables=variables)


def test_letters_by_hand_name_the_group_a_share_is_significantly_higher_than(tmp_path):
    # Left: 60 of 100 say yes; Right: 40 of 100. Pooled 0.5, SE √(0.25 · 0.02)
    # = 0.0707, z = 2.828, p = 0.0047 < 0.05: Left's yes beats Right (B), and
    # Right's no beats Left (A). At 0.001 neither does.
    frame = pd.DataFrame(
        {"q": [1] * 60 + [2] * 40 + [1] * 40 + [2] * 60, "g": [1] * 100 + [2] * 100}
    )
    variables = VariableMap()
    variables.add_many(
        [
            Variable("q", "nominal", label="Answer", labels={1: "Yes", 2: "No"}),
            Variable("g", "nominal", label="Group", labels={1: "Left", 2: "Right"}),
        ]
    )
    data = SurveyData(frame=frame, variables=variables)
    chart = data.plot.bar("q", split="g", show="percent", letters=True)
    _rendered(chart, tmp_path)
    ax = chart.plot()
    assert [text.split("\n")[0] for text in _ticks(ax)] == ["Left (A)", "Right (B)"]
    assert _letters(ax) == {("Left (A)", "Yes"): "B", ("Right (B)", "No"): "A"}
    note = _footnote(chart)
    assert "significantly lower (two-sided z-test of column proportions, p < 0.05)" in note
    strict = data.plot.bar("q", split="g", show="percent", letters=True, level=0.001)
    assert _letters(strict.plot()) == {}
    assert "No group's share of any answer is significantly higher than another's." in (
        _footnote(strict)
    )


@pytest.mark.parametrize(
    ("weighted", "correction", "horizontal"),
    [(False, "none", False), (True, "none", True), (True, "bonferroni", False)],
)
def test_the_letters_are_the_tab_book_s_for_the_same_cells(weighted, correction, horizontal):
    """Missing codes of the question and of the split left out, a weight, and
    Bonferroni: the chart's letters are the Tab book's, cell for cell."""
    data = _survey()
    if weighted:
        data = data.with_weight("w")
    chart = data.plot.bar(
        "rating",
        split="region",
        show="percent",
        letters=True,
        correction=correction,
        horizontal=horizontal,
    )
    drawn = _letters(chart.plot())
    expected = _tab_letters(data, "rating", "region", correction=correction)
    assert drawn == expected
    assert len(drawn) >= 3  # the data has differences to find
    if correction == "bonferroni":
        assert "Bonferroni-corrected" in _footnote(chart)
    if weighted:
        assert "on Kish's effective base" in _footnote(chart)


def test_the_letters_of_a_multiple_choice_question_are_the_tab_book_s():
    data = _survey()
    chart = data.plot.bar("brands", split="region", show="percent", letters=True)
    assert _letters(chart.plot()) == _tab_letters(data, "brands", "region")


def test_where_everyone_answered_the_letters_are_the_banner_table_s():
    data = _survey()
    frame = data.frame
    complete = data.with_frame(
        frame[frame["rating"].isin([1, 2, 3, 4]) & frame["region"].isin([1, 2, 3, 4])]
    )
    chart = complete.plot.bar("rating", split="region", show="percent", letters=True)
    banner = complete.report.banner(["rating"], ["region"]).to_frame()
    expected = {}
    for _, row in banner[banner["Question"] == "Rating"].iterrows():
        for header in banner.columns[2:]:
            parts = str(row[header]).split(") ")
            if len(parts) == 2:  # "42.1% (80) BC"
                expected[(header.split(": ", 1)[1], row["Answer"])] = parts[1]
    assert _letters(chart.plot()) == expected and expected


def test_a_small_group_is_not_tested_and_the_note_names_it(tmp_path):
    data = _survey()
    frame = data.frame
    data = data.with_frame(frame.drop(frame.index[frame["region"] == 4][20:]))  # 20 in West
    chart = data.plot.bar("rating", split="region", show="percent", letters=True)
    _rendered(chart, tmp_path)
    tab = _tab_letters(data, "rating", "region")
    assert _letters(chart.plot()) == tab
    assert "Not tested, fewer than 30 respondents who answered: West (D)." in _footnote(chart)
    assert not any(group.startswith("West") for group, _ in tab)


def test_top_n_with_letters_tests_other_too(tmp_path):
    data = _survey()
    chart = data.plot.bar("rating", split="region", show="percent", letters=True, top=2, other=True)
    _rendered(chart, tmp_path)
    drawn = _letters(chart.plot())
    tab = _tab_letters(data, "rating", "region")
    kept = {answer for _, answer in drawn} - {"Other"}
    assert {key: value for key, value in drawn.items() if key[1] in kept} == {
        key: value for key, value in tab.items() if key[1] in kept
    }


# ─── histogram ───────────────────────────────────────────────────────────────


def _numbers(n: int = 500, seed: int = 11) -> SurveyData:
    rng = np.random.default_rng(seed)
    frame = pd.DataFrame(
        {
            "income": rng.lognormal(8.0, 0.6, n),
            "age": np.clip(rng.normal(45, 15, n).round(), 18, 90),
            "g": rng.choice([1, 2, 3], n).astype(float),
            "w": rng.uniform(0.4, 2.2, n),
        }
    )
    frame.loc[:4, "age"] = 999.0  # Refused
    variables = VariableMap()
    variables.add_many(
        [
            Variable("income", "ratio", label="Income"),
            Variable(
                "age",
                "ratio",
                label="Age",
                missing_values=(999,),
                missing_labels={999: "Refused"},
            ),
            Variable("g", "nominal", label="Region", labels={1: "North", 2: "South", 3: "East"}),
        ]
    )
    return SurveyData(frame=frame, variables=variables)


def _histogram(ax) -> tuple[np.ndarray, np.ndarray]:
    """The bins' edges and the bars' heights, from the patches drawn."""
    patches = ax.containers[0].patches
    edges = [p.get_x() for p in patches] + [patches[-1].get_x() + patches[-1].get_width()]
    return np.array(edges), np.array([p.get_height() for p in patches])


def test_a_histogram_is_numpy_s_with_freedman_diaconis_bins_weighted(tmp_path):
    data = _numbers().with_weight("w")
    chart = data.plot.bar("income", layout="histogram")
    _rendered(chart, tmp_path)
    frame = data.frame
    edges, heights = _histogram(chart.plot())
    expected_edges = np.histogram_bin_edges(frame["income"], bins="fd")
    assert np.allclose(edges, expected_edges)
    counts, _ = np.histogram(frame["income"], bins=expected_edges, weights=frame["w"])
    assert np.allclose(heights, counts)
    ax = chart.plot()
    assert ax.get_ylabel() == "Weighted count" and ax.get_title() == "Income"
    note = _footnote(chart)
    assert f"Bins: {len(counts)} of width" in note and "(Freedman–Diaconis)" in note
    assert "the width is of the answers as they are, the heights weighted" in note
    # As percent of the respondents who answered (their weights).
    share = data.plot.bar("income", layout="histogram", show="percent")
    assert np.allclose(_histogram(share.plot())[1], counts / frame["w"].sum() * 100)
    assert share.plot().get_ylabel() == "% of respondents (weighted)"


def test_whole_numbers_take_whole_bins_between_the_numbers():
    # 20 21 22 25 30 31 35 40 41 60: IQR 38.75 − 22.75 = 16, Freedman–Diaconis
    # 2 · 16 / ∛10 = 14.85 → 15; edges from 19.5: 19.5, 34.5, 49.5, 64.5.
    frame = pd.DataFrame({"x": [20, 21, 22, 25, 30, 31, 35, 40, 41, 60]})
    variables = VariableMap()
    variables.add(Variable("x", "ratio", label="Years"))
    chart = SurveyData(frame=frame, variables=variables).plot.bar("x", layout="histogram")
    edges, heights = _histogram(chart.plot())
    assert edges.tolist() == [19.5, 34.5, 49.5, 64.5]
    assert heights.tolist() == [6, 3, 1]
    assert "Bins: 3 of width 15 (Freedman–Diaconis), each holding 15 whole numbers." in (
        _footnote(chart)
    )
    # A fine width on whole numbers is one number a bin, not a comb of gaps.
    many = pd.DataFrame({"x": np.repeat(np.arange(0, 11), 400)})
    fine = SurveyData(frame=many, variables=variables).plot.bar("x", layout="histogram")
    edges, heights = _histogram(fine.plot())
    assert edges.tolist() == [x - 0.5 for x in range(12)] and heights.tolist() == [400] * 11


def test_a_number_of_bins_and_edges_given(tmp_path):
    data = _numbers()
    frame = data.frame[data.frame["age"] != 999]  # the missing code, left out
    chart = data.plot.bar("age", layout="histogram", bins=6)
    edges, heights = _histogram(chart.plot())
    counts, expected = np.histogram(frame["age"], bins=6)
    assert np.allclose(edges, expected) and np.allclose(heights, counts)
    assert "Left out as missing: Age: 5 (999 = Refused)." in _footnote(chart)

    given = data.plot.bar("age", layout="histogram", bins="30, 40, 50, 70", show="percent")
    _rendered(given, tmp_path)
    ax = given.plot()
    edges, heights = _histogram(ax)
    counts, _ = np.histogram(frame["age"], bins=[30, 40, 50, 70])
    assert edges.tolist() == [30, 40, 50, 70]
    assert np.allclose(heights, counts / len(frame) * 100)  # of everyone who answered
    outside = int(((frame["age"] < 30) | (frame["age"] > 70)).sum())
    note = _footnote(given)
    assert (
        f"{outside} answers outside the bins (below 30 or above 70) not drawn, but in the base."
        in note
    )
    assert "The bins differ in width: a bar's height is its percentage, not its density." in note
    assert [tick for tick in ax.get_xticks()] == [30, 40, 50, 70]


def test_a_histogram_split_by_a_group_is_a_panel_each(tmp_path):
    data = _numbers().with_weight("w")
    chart = data.plot.bar("income", layout="histogram", split="g", show="percent")
    _rendered(chart, tmp_path)
    fig = chart.plot().figure
    panels = [ax for ax in fig.axes if ax.get_visible()]
    assert len(panels) == 3
    frame = data.frame
    edges = np.histogram_bin_edges(frame["income"], bins="fd")
    for ax, code, name in zip(panels, (1, 2, 3), ("North", "South", "East"), strict=True):
        group = frame[frame["g"] == code]
        counts, _ = np.histogram(group["income"], bins=edges, weights=group["w"])
        drawn_edges, heights = _histogram(ax)
        assert np.allclose(drawn_edges, edges)
        assert np.allclose(heights, counts / group["w"].sum() * 100)
        assert ax.get_title(loc="left") == f"{name} (n = {len(group)})"
    # The panels share their bins and their scale.
    assert len({ax.get_xlim() for ax in panels}) == 1 and len({ax.get_ylim() for ax in panels}) == 1
    assert fig._suptitle.get_text() == "Income by Region"
    assert "Percentages are of each group of Region." in _footnote(chart)
    # Five groups: two columns, the figure taller than asked so each panel reads.
    rng = np.random.default_rng(2)
    five = data.with_frame(frame.assign(g=rng.choice([1, 2, 3, 4, 5], len(frame)).astype(float)))
    wide = five.plot.bar("income", layout="histogram", split="g", figsize=(8, 3))
    shown = [ax for ax in wide.plot().figure.axes if ax.get_visible()]
    assert len(shown) == 5
    heights = [ax.get_window_extent().height * 72 / ax.figure.dpi for ax in shown]
    assert min(heights) >= 50 and wide.plot().figure.get_figheight() > 3


@pytest.mark.parametrize(
    ("column", "kwargs", "message"),
    [
        ("g", {}, "A histogram draws the distribution of a number, and Region is nominal"),
        ("age", {"by": "g"}, "give split= for a histogram of each group"),
        ("age", {"top": 3}, "a histogram draws bins of a number"),
        ("age", {"intervals": True}, "not on a histogram"),
        ("age", {"bins": "10, 5"}, "10 is followed by 5"),
        ("age", {"bins": "0"}, "A number of bins is a whole number from 1 to 100"),
        ("age", {"bins": "ten"}, "Bins is auto"),
        ("age", {"bins": 2.5}, "A number of bins is a whole number"),
    ],
)
def test_what_a_histogram_refuses_is_said(column, kwargs, message):
    with pytest.raises(ValueError, match=message):
        _numbers().plot.bar(column, layout="histogram", **kwargs).plot()


def test_a_histogram_refuses_text_and_too_many_groups():
    data = _numbers()
    text = data.with_frame(data.frame.assign(income=data.frame["income"].astype(object)))
    text.frame.loc[7, "income"] = "a lot"
    with pytest.raises(
        ValueError, match="holds an answer that is not one \\(for example 'a lot'\\)"
    ):
        text.plot.bar("income", layout="histogram").plot()
    many = data.with_frame(data.frame.assign(g=np.arange(len(data.frame)) % 13))
    with pytest.raises(ValueError, match="has 13 groups, and a histogram draws a panel for each"):
        many.plot.bar("income", layout="histogram", split="g").plot()


# ─── donut ───────────────────────────────────────────────────────────────────


def _channels(counts=(10, 6, 2, 1, 1)) -> SurveyData:
    codes = [code for code, count in enumerate(counts, start=1) for _ in range(count)]
    frame = pd.DataFrame({"c": codes, "w": np.linspace(0.5, 1.5, len(codes))})
    variables = VariableMap()
    variables.add(
        Variable(
            "c",
            "nominal",
            label="Channel",
            labels={1: "Online", 2: "Shop", 3: "Phone", 4: "Post", 5: "Fair", 6: "Radio"},
        )
    )
    return SurveyData(frame=frame, variables=variables)


def _wedges(ax) -> list[tuple[str, float]]:
    from matplotlib.patches import Wedge

    return [
        (patch.get_label(), round((patch.theta2 - patch.theta1) / 3.6, 3))
        for patch in ax.patches
        if isinstance(patch, Wedge)
    ]


def test_a_donut_draws_the_shares_as_slices_with_the_base_in_the_middle(tmp_path):
    chart = _channels().plot.bar("c", layout="donut")
    _rendered(chart, tmp_path)
    ax = chart.plot()
    # 10, 6, 2, 1, 1 of 20; Post and Fair are under 3 %? No: 5 % each — kept.
    assert _wedges(ax) == [
        ("Online", 50.0),
        ("Shop", 30.0),
        ("Phone", 10.0),
        ("Post", 5.0),
        ("Fair", 5.0),
    ]
    texts = [text.get_text() for text in ax.texts]
    assert {"50.0%", "30.0%", "10.0%", "5.0%"} <= set(texts)
    assert "20" in texts and "respondents" in texts
    legend = [text.get_text() for text in ax.get_legend().get_texts()]
    assert legend == ["Online", "Shop", "Phone", "Post", "Fair"]
    assert ax.get_title() == "Channel"
    assert "Base: 20 respondents who answered." in _footnote(chart)
    # Clockwise from the top.
    first = next(p for p in ax.patches if p.get_label() == "Online")
    assert first.theta2 == pytest.approx(90.0)


def test_small_slices_are_combined_as_other_below_the_threshold(tmp_path):
    chart = _channels().plot.bar("c", layout="donut", min_slice=6)
    _rendered(chart, tmp_path)
    ax = chart.plot()
    assert _wedges(ax) == [("Online", 50.0), ("Shop", 30.0), ("Phone", 10.0), ("Other", 10.0)]
    other = next(p for p in ax.patches if p.get_label() == "Other")
    assert _colour(other) == GREY
    assert "Other combines 2 answers under 6 % each: Post and Fair." in _footnote(chart)
    # One small slice alone keeps its name: Other would only rename it.
    single = _channels((10, 6, 3, 1)).plot.bar("c", layout="donut", min_slice=6)
    assert [name for name, _ in _wedges(single.plot())] == ["Online", "Shop", "Phone", "Post"]
    # 0 keeps every slice; largest first keeps Other last.
    every = _channels().plot.bar("c", layout="donut", min_slice=0, sort="value")
    assert len(_wedges(every.plot())) == 5
    ranked = _channels((1, 6, 10, 1, 1)).plot.bar("c", layout="donut", min_slice=6, sort="value")
    assert [name for name, _ in _wedges(ranked.plot())] == ["Phone", "Shop", "Other"]


def test_a_donut_with_top_n_combines_the_rest_whatever_other_says(tmp_path):
    chart = _channels().plot.bar("c", layout="donut", top=2, figsize=(4, 4))
    _rendered(chart, tmp_path)
    ax = chart.plot()
    assert _wedges(ax) == [("Online", 50.0), ("Shop", 30.0), ("Other", 20.0)]
    assert (
        "The 2 answers given most of 5 are drawn; Other combines the other 3 — a donut's "
        "slices make a whole."
    ) in _footnote(chart)
    # A scale step nobody gave has no slice, and is named.
    variables = VariableMap()
    variables.add(
        Variable("c", "ordinal", label="Rating", labels={1: "Poor", 2: "Fair", 3: "Good", 4: "Top"})
    )
    rated = SurveyData(frame=pd.DataFrame({"c": [1] * 10 + [3] * 6 + [4] * 4}), variables=variables)
    drawn = rated.plot.bar("c", layout="donut", top=2)
    assert _wedges(drawn.plot()) == [("Poor", 50.0), ("Good", 30.0), ("Other", 20.0)]
    note = _footnote(drawn)
    assert "The 2 answers given most of 4 are drawn; Other combines the other 1" in note
    assert "Nobody answered Fair." in note
    # Narrow: the legend is under the donut.
    assert ax.get_legend() is None and len(ax.figure.legends) == 1


def test_a_weighted_donut_says_its_weighted_base():
    data = _channels().with_weight("w")
    chart = data.plot.bar("c", layout="donut")
    frame = data.frame
    shares = frame.groupby("c")["w"].sum() / frame["w"].sum() * 100
    assert [share for _, share in _wedges(chart.plot())] == pytest.approx(
        shares.round(3).tolist(), abs=1e-3
    )
    texts = [text.get_text() for text in chart.plot().texts]
    assert "weighted 20" in texts and chart.weight_note == "weighted by 'w'"


def test_a_thin_slice_s_percentage_goes_beside_it_without_covering_another():
    counts = (30, 20, 1, 1, 1, 1, 1, 1)
    chart = _channels(counts).plot.bar("c", layout="donut", min_slice=0, figsize=(6, 4))
    ax = chart.plot()
    ax.figure.canvas.draw()
    renderer = ax.figure.canvas.get_renderer()
    labels = [text for text in ax.texts if text.get_text().endswith("%")]
    assert len(labels) == 8
    boxes = [text.get_window_extent(renderer) for text in labels]
    for i, first in enumerate(boxes):
        for second in boxes[i + 1 :]:
            assert not first.overlaps(second)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"split": "g"}, "split cannot be drawn in it"),
        ({"by": "g"}, "by draws means"),
        ({"intervals": True}, "not on a donut"),
    ],
)
def test_what_a_donut_refuses_is_said(kwargs, message):
    data = _small()
    with pytest.raises(ValueError, match=message):
        data.plot.bar("q", layout="donut", **kwargs).plot()


def test_a_donut_of_a_multiple_choice_question_is_refused():
    with pytest.raises(ValueError, match="are not the parts of a whole"):
        _ranked().plot.bar("m", layout="donut").plot()


# ─── what the newer parameters refuse ────────────────────────────────────────


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"top": 0}, "top must be 1 or more"),
        ({"top": 2.5}, "top must be a whole number"),
        ({"other": True}, "give top= as well"),
        ({"top": 2, "by": "g"}, "with by the bars are means"),
        ({"letters": True}, "compare the groups of split"),
        ({"letters": True, "split": "g"}, "give show='percent'"),
        ({"letters": True, "split": "g", "show": "percent", "layout": "stacked"}, "not on stacks"),
        ({"intervals": True, "split": "g", "layout": "stacked_100"}, "a stacked bar has no end"),
        ({"intervals": True, "confidence": 95}, "confidence must be between 0 and 1"),
        ({"split": "g", "letters": True, "show": "percent", "level": 0}, "level must be between"),
        ({"split": "g", "correction": "holm"}, "correction must be one of none, bonferroni"),
        (
            {"layout": "pie"},
            "layout must be one of grouped, stacked, stacked_100, histogram, donut",
        ),
    ],
)
def test_what_the_newer_parameters_refuse_is_said(kwargs, message):
    with pytest.raises(ValueError, match=message):
        _small().plot.bar("q", **kwargs).plot()


def test_the_defaults_still_draw_the_classic_chart():
    from siamang.reporting import bars

    chart = _small().plot.bar("q")
    assert bars.is_classic(chart)
    for kwargs in (
        {"top": 2},
        {"intervals": True},
        {"layout": "donut"},
        {"layout": "histogram"},
        {"other": True},
    ):
        assert not bars.is_classic(_small().plot.bar("q", **kwargs))


# ─── the node ────────────────────────────────────────────────────────────────


def _flow(params):
    return {
        "schema_version": "1.0",
        "name": "t",
        "nodes": [
            {"id": "src", "type": "source.responses", "params": {}},
            {"id": "w", "type": "prepare.apply_weight", "params": {"column": "w"}},
            {"id": "n", "type": "visualize.bar", "params": params},
        ],
        "edges": [
            {"from": {"node": "src", "port": "data"}, "to": {"node": "w", "port": "data"}},
            {"from": {"node": "w", "port": "data"}, "to": {"node": "n", "port": "data"}},
        ],
    }


@pytest.fixture(scope="module")
def questionnaire_doc():
    from siamang.model import loads

    return loads((DOCUMENTS / "brand_awareness.questionnaire.json").read_text("utf-8"))


@pytest.fixture(scope="module")
def survey(questionnaire_doc):
    from siamang.model import from_document

    return from_document(questionnaire_doc).survey


def _issues(params, questionnaire_doc):
    from siamang.flow import check_flow

    return [
        (issue.severity, issue.message)
        for issue in check_flow(_flow(params), questionnaire=questionnaire_doc)
    ]


@pytest.mark.parametrize(
    ("params", "check"),
    [
        (
            {"variable": "satisfaction", "show": "percent", "top": 3, "other": True},
            lambda ax: _ticks(ax)[-1] == "Other" and len(_ticks(ax)) == 4,
        ),
        (
            {"variable": "aware", "split": "region", "show": "percent", "top": 2, "other": True},
            lambda ax: [t.get_text() for t in ax.get_legend().get_texts()][-1] == "Other",
        ),
        (
            {"variable": "satisfaction", "show": "percent", "intervals": True},
            lambda ax: len(_whiskers(ax)[0]) == 5,
        ),
        (
            {"variable": "age", "by": "region", "intervals": True, "confidence": 0.9},
            lambda ax: len(_whiskers(ax)[0]) == 3,
        ),
        (
            {
                "variable": "trust_acme",
                "split": "region",
                "show": "percent",
                "letters": True,
                "correction": "bonferroni",
                "intervals": True,
            },
            lambda ax: [t.split("\n")[0] for t in _ticks(ax)]
            == ["Capital (A)", "North (B)", "South (C)"],
        ),
        (
            {"variable": "age", "layout": "histogram", "bins": "18, 30, 45, 60, 80"},
            lambda ax: _histogram(ax)[0].tolist() == [18, 30, 45, 60, 80],
        ),
        (
            {"variable": "age", "layout": "histogram", "split": "gender", "show": "percent"},
            lambda ax: len([a for a in ax.figure.axes if a.get_visible()]) == 3,
        ),
        (
            {"variable": "region", "layout": "donut", "top": 2},
            lambda ax: [name for name, _ in _wedges(ax)][-1] == "Other",
        ),
    ],
)
def test_the_bar_node_checks_generates_and_runs_the_newer_forms(
    params, check, questionnaire_doc, survey, tmp_path
):
    from siamang.flow import FlowRunner, check_flow, generate_flow

    flow = _flow(params)
    assert check_flow(flow, questionnaire=questionnaire_doc) == []
    code = generate_flow(flow, questionnaire_doc)
    compile(code, "bar.py", "exec")
    simulated = survey.simulate(n=300, seed=7)
    frame = simulated.frame.assign(w=np.random.default_rng(1).uniform(0.5, 2.0, 300))
    data = SurveyData(frame=frame, variables=simulated.variables, questionnaire=survey)
    result = FlowRunner(flow, questionnaire=survey).run(sources={"src": data}, cwd=tmp_path)
    chart = result.output("n")
    _rendered(chart, tmp_path)
    assert check(chart.plot())
    assert chart.weight_note == "weighted by 'w'"


def test_the_node_writes_only_what_is_set(questionnaire_doc):
    from siamang.flow.document import resolve_flow
    from siamang.flow.template import render_node

    def code(params):
        return render_node(resolve_flow(_flow(params), questionnaire=questionnaire_doc), "n")

    assert code({"variable": "region", "top": 2, "other": True}) == (
        "n_n = n_w.plot.bar(\n    'region',\n    by=None,\n    horizontal=False,\n"
        "    show_values=True,\n    title=None,\n    figsize=(10.0, 6.0),\n"
        "    palette='muted',\n    top=2,\n    other=True,\n)\n"
    )
    split = code(
        {
            "variable": "satisfaction",
            "split": "region",
            "show": "percent",
            "letters": True,
            "level": 0.01,
        }
    )
    assert "    letters=True,\n    level=0.01,\n    correction='none',\n)\n" in split
    assert "intervals" not in split and "top=" not in split
    # Letters on a stack, Intervals on a histogram: not read, not written.
    stacked = code(
        {"variable": "satisfaction", "split": "region", "layout": "stacked", "letters": True}
    )
    assert "letters" not in stacked
    hist = code({"variable": "age", "layout": "histogram", "intervals": True, "top": 3})
    assert "intervals" not in hist and "top" not in hist and "bins='auto'" in hist
    donut = code({"variable": "region", "layout": "donut", "top": 2, "other": False})
    assert 'layout="donut"' in donut and "min_slice=3.0" in donut and "top=2" in donut
    assert "other" not in donut and "show=" not in donut


def test_the_node_shows_each_new_field_for_the_choices_that_read_it():
    from siamang.flow import default_registry
    from siamang.flow.document import resolved_params

    spec = default_registry().get("visualize.bar")

    def reads(name, **choices):
        return spec.reads(name, resolved_params(spec, choices))

    assert reads("bins", layout="histogram") and not reads("bins")
    assert reads("min_slice", layout="donut") and not reads("min_slice")
    assert reads("confidence", intervals=True) and not reads("confidence")
    assert not reads("confidence", intervals=True, layout="stacked")
    assert reads("letters", show="percent") and not reads("letters")
    assert not reads("letters", show="percent", layout="stacked_100")
    assert reads("level", letters=True, show="percent") and not reads("level", show="percent")
    assert reads("top") and reads("top", layout="donut") and not reads("top", layout="histogram")
    assert reads("other") and not reads("other", layout="donut")
    for name in ("by", "horizontal", "sort"):
        assert not reads(name, layout="histogram"), name
    for name in ("by", "show", "split", "horizontal"):
        assert not reads(name, layout="donut"), name


def test_the_node_checks_what_the_newer_forms_refuse(questionnaire_doc):
    def issues(params):
        return _issues(params, questionnaire_doc)

    assert issues({"variable": "region", "layout": "histogram"}) == [
        (
            "error",
            "n: A histogram draws the distribution of a number, and Region is nominal: draw "
            "its answers as bars (Layout = grouped).",
        )
    ]
    assert issues({"variable": "aware", "layout": "donut"}) == [
        (
            "error",
            "n: Brands heard of (unaided) allows several answers, so its shares add up to more "
            "than 100 % and are not the parts of a whole: draw them as bars (Layout = grouped).",
        )
    ]
    assert issues({"variable": "age", "layout": "histogram", "bins": "40, 20"}) == [
        (
            "error",
            "Parameter 'bins' of n: The bins' edges must increase from one to the next, and 40 "
            "is followed by 20.",
        )
    ]
    assert issues({"variable": "age", "by": "region", "top": 2}) == [
        (
            "error",
            "n: Top N keeps the answers given most, and with By the bars are means of groups — "
            "clear one of them.",
        )
    ]
    warnings = {
        "n: Stacked layouts apply only when Split by is set.": {
            "variable": "region",
            "layout": "stacked_100",
        },
        "n: Combine the rest as Other applies with Top N — set Top N.": {
            "variable": "region",
            "other": True,
        },
        "n: Top N keeps the answers given most; a histogram draws bins of a number, so it is "
        "not applied.": {"variable": "age", "layout": "histogram", "top": 3},
        "n: By (the mean in each group) is not drawn in a histogram; for a histogram of each "
        "group, use Split by.": {"variable": "age", "layout": "histogram", "by": "region"},
        "n: By (the mean in each group) is not drawn in a donut, which shows the shares of "
        "Variable's answers.": {"variable": "gender", "layout": "donut", "by": "region"},
        "n: Split by is not drawn in a donut, which shows one variable's answers as the parts "
        "of a whole; Layout stacked_100 shows the answers within each group.": {
            "variable": "gender",
            "layout": "donut",
            "split": "region",
        },
        "n: Confidence intervals are drawn on bars side by side (Layout grouped) only.": {
            "variable": "gender",
            "split": "region",
            "layout": "stacked",
            "intervals": True,
        },
        "n: Confidence intervals are drawn for percentages and for means by group; counts "
        "have none — set Show to percent.": {"variable": "gender", "intervals": True},
        "n: Significance letters compare the groups of Split by — set Split by.": {
            "variable": "gender",
            "show": "percent",
            "letters": True,
        },
        "n: Significance letters are drawn on bars side by side (Layout grouped), not on "
        "stacks.": {
            "variable": "gender",
            "split": "region",
            "show": "percent",
            "layout": "stacked_100",
            "letters": True,
        },
        "n: Significance letters compare percentages, as the Banner table's do — set Show to "
        "percent.": {"variable": "gender", "split": "region", "letters": True},
    }
    for message, params in warnings.items():
        assert issues(params) == [("warning", message)], params
