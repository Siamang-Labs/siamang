"""siamang.reporting.result_charts — the chart that suits an analysis's result.

Each chart is built from a result with known numbers and then read back from the
figure: the rows and their order, where each point and whisker sits, the bars'
lengths, the colours, the labels — so a chart that draws the wrong number, or
draws it where it cannot be read, fails here rather than in a report. The
intervals it draws are checked against R and against an independent survey
package, quoted.
"""

from __future__ import annotations

import struct

import matplotlib
import numpy as np
import pandas as pd
import pytest

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

from siamang.core import Variable, VariableMap  # noqa: E402
from siamang.data import SurveyData, factor, paired, text_coding, turf  # noqa: E402
from siamang.reporting import Report  # noqa: E402
from siamang.reporting import result_charts as rc  # noqa: E402


@pytest.fixture(autouse=True)
def _close_figures():
    yield
    plt.close("all")


# ─── reading a figure back ───────────────────────────────────────────────────


def _points(ax) -> list[tuple[float, float]]:
    """The markers of the dot rows: (x, y) of each point drawn."""
    found = []
    for line in ax.lines:
        if isinstance(line, Line2D) and line.get_marker() == "o" and line.get_linestyle() == "None":
            found += list(zip(line.get_xdata(), line.get_ydata(), strict=True))
    return [(float(x), float(y)) for x, y in found]


def _whiskers(ax) -> list[tuple[float, float, float]]:
    """(y, low, high) of each interval drawn with hlines."""
    found = []
    for collection in ax.collections:
        if isinstance(collection, LineCollection):
            for segment in collection.get_segments():
                (x0, y0), (x1, _) = segment
                found.append((float(y0), float(x0), float(x1)))
    return sorted(found)


def _bars(ax) -> list[Rectangle]:
    return [
        patch for patch in ax.patches if isinstance(patch, Rectangle) and patch.get_height() > 0
    ]


def _ticks(ax, axis: str = "y") -> list[str]:
    labels = ax.get_yticklabels() if axis == "y" else ax.get_xticklabels()
    return [label.get_text().replace("\n", " ") for label in labels]


def _texts(ax) -> list[str]:
    """The texts of ``ax``, a wrapped note read as one line."""
    return [text.get_text().replace("\n", " ") for text in ax.texts]


def _png_size(path) -> tuple[int, int]:
    with open(path, "rb") as handle:
        head = handle.read(24)
    assert head[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", head[16:24])


def _inside(chart, texts) -> None:
    """Every value label lies inside the axes it labels (nothing clipped)."""
    fig = chart._fig
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    box = chart._ax.get_window_extent(renderer)
    for text in texts:
        extent = text.get_window_extent(renderer)
        assert extent.x0 >= box.x0 - 1 and extent.x1 <= box.x1 + 1, text.get_text()


# ─── data ────────────────────────────────────────────────────────────────────

GROUPS = {1: "Alpha", 2: "Beta", 3: "Gamma"}


def _groups_data(weighted: bool = False) -> SurveyData:
    a = [2, 4, 4, 5, 7, 8]  # R: t.test(a)$conf.int = 2.70080170952, 7.29919829048
    b = [3, 5, 2, 4, 4, 1, 5]
    c = [6, 7, 7, 8]
    frame = pd.DataFrame(
        {
            "g": [1] * len(a) + [2] * len(b) + [3] * len(c),
            "y": [float(v) for v in a + b + c],
            "w": [1.0] * len(a) + [1.5, 0.5, 2, 1, 1, 0.8, 1.2] + [1.0] * len(c),
        }
    )
    variables = VariableMap()
    variables.add(Variable("g", "nominal", label="Group", labels=GROUPS))
    variables.add(Variable("y", "interval", label="Score"))
    data = SurveyData(frame=frame, variables=variables)
    return data.with_weight("w") if weighted else data


# ─── the compact letter display ──────────────────────────────────────────────


def test_letters_follow_piepho_insert_and_absorb():
    groups = ["A", "B", "C", "D"]
    assert rc.letters(groups, []) == dict.fromkeys(groups, "a")
    # Only A and C differ: B is between them.
    assert rc.letters(["A", "B", "C"], [("A", "C")]) == {"A": "a", "B": "ab", "C": "b"}
    # Every pair differs.
    everything = [("A", "B"), ("A", "C"), ("B", "C")]
    assert rc.letters(["A", "B", "C"], everything) == {"A": "a", "B": "b", "C": "c"}
    # multcompView's canonical chain: A–C, A–D and B–D differ.
    assert rc.letters(groups, [("A", "C"), ("A", "D"), ("B", "D")]) == {
        "A": "a",
        "B": "ab",
        "C": "bc",
        "D": "c",
    }
    # Every group that shares a letter with another does not differ from it.
    found = rc.letters(groups, [("A", "C"), ("A", "D"), ("B", "D")])
    for first in groups:
        for second in groups:
            share = bool(set(found[first]) & set(found[second]))
            differ = (first, second) in {("A", "C"), ("A", "D"), ("B", "D")} or (
                second,
                first,
            ) in {("A", "C"), ("A", "D"), ("B", "D")}
            assert share != differ or first == second


# ─── Group means ─────────────────────────────────────────────────────────────


def test_group_means_draws_each_mean_with_its_interval(tmp_path):
    table = _groups_data().report.means("y", by="g")
    chart = rc.chart(table)
    ax = chart._ax
    assert chart.drawn == "means" and chart.weight_note is None
    assert _ticks(ax) == ["Alpha", "Beta", "Gamma"]  # the table's order, top down
    means = table.to_frame()["Mean"].tolist()
    assert [x for x, _ in sorted(_points(ax), key=lambda p: p[1])] == means
    whiskers = _whiskers(ax)
    assert whiskers[0][1:] == pytest.approx((2.70080170952, 7.29919829048), abs=1e-9)
    assert all(low < mean < high for (_, low, high), mean in zip(whiskers, means, strict=True))
    assert "95 % confidence interval" in ax.get_xlabel()
    path = chart.save(tmp_path / "means.png")
    width, height = _png_size(path)
    assert width > 800 and height > 300


def test_weighted_group_means_draw_the_weighted_interval_and_say_so():
    table = _groups_data(weighted=True).report.means("y", by="g")
    chart = rc.chart(table)
    assert chart.weight_note == "weighted by 'w'"
    assert chart._ax.get_title(loc="left").endswith("\nweighted by 'w'")
    assert chart._ax.get_xlabel().startswith("Weighted mean")
    beta = _whiskers(chart._ax)[1]
    assert beta[1:] == pytest.approx((1.911360860729, 4.538639139271), abs=1e-9)
    assert sorted(_points(chart._ax), key=lambda p: p[1])[1][0] == 3.225  # the table's mean


def test_group_means_with_sd_bars_and_posthoc_letters():
    frame = pd.DataFrame(
        {
            "g": [1] * 6 + [2] * 6 + [3] * 6,
            "y": [1, 2, 1, 2, 1, 2, 1, 2, 2, 1, 2, 1, 5, 6, 5, 6, 5, 6],
        }
    )
    variables = VariableMap()
    variables.add(Variable("g", "nominal", label="Group", labels=GROUPS))
    variables.add(Variable("y", "interval", label="Score"))
    table = SurveyData(frame=frame, variables=variables).report.means(
        "y", by="g", method="anova", posthoc="tukey"
    )
    chart = rc.chart(table)
    texts = _texts(chart._ax)
    # Gamma is highest and differs from both; Alpha and Beta share a letter.
    assert "1.50   b" in texts and "5.50   a" in texts
    assert any("sharing a letter" in text and "Tukey" in text for text in texts)
    sd = rc.chart(table, kind="means_sd")
    assert sd.drawn == "means_sd" and sd._ax.get_xlabel().endswith("± 1 SD")
    spread = table.to_frame()["SD"].tolist()
    for (_, low, high), mean, deviation in zip(
        _whiskers(sd._ax), table.to_frame()["Mean"], spread, strict=True
    ):
        assert (low, high) == pytest.approx((mean - deviation, mean + deviation))


def test_many_groups_with_long_labels_stay_legible(tmp_path):
    rng = np.random.default_rng(1)
    labels = {
        code: f"Region {code}: a district with a long official name, number {code}"
        for code in range(1, 41)
    }
    frame = pd.DataFrame({"g": rng.integers(1, 41, 2000), "y": rng.normal(3, 1, 2000)})
    variables = VariableMap()
    variables.add(Variable("g", "nominal", label="Region", labels=labels))
    variables.add(Variable("y", "interval", label="Score"))
    table = SurveyData(frame=frame, variables=variables).report.means("y", by="g")
    chart = rc.chart(table)
    ax = chart._ax
    assert len(ax.get_yticklabels()) == 40
    # Too many rows for 6 inches at a legible size: the figure grew instead.
    assert chart._fig.get_size_inches()[1] > 6
    assert min(label.get_fontsize() for label in ax.get_yticklabels()) >= 7
    # A label longer than its room is wrapped (or cut with an ellipsis), never
    # left to run into the plot.
    assert all(
        max(len(line) for line in label.get_text().split("\n")) <= 70
        for label in ax.get_yticklabels()
    )
    _inside(chart, ax.texts[:-1] if ax.texts else [])
    assert (
        _png_size(chart.save(tmp_path / "many.png"))[1]
        > _png_size(rc.chart(_groups_data().report.means("y", by="g")).save(tmp_path / "few.png"))[
            1
        ]
    )


def test_few_rows_do_not_stretch_over_a_tall_figure():
    chart = rc.chart(_groups_data().report.means("y", by="g"), figsize=(10, 12))
    assert chart._fig.get_size_inches()[1] < 6


# ─── Descriptive statistics, t-test, Paired tests ────────────────────────────


def test_descriptives_draw_one_series_per_group():
    data = _groups_data()
    frame = data.frame.assign(z=data.frame["y"] * 2)
    variables = data.variables
    variables.add(Variable("z", "interval", label="Twice the score"))
    data = SurveyData(frame=frame, variables=variables)
    table = data.report.descriptives(["y", "z"], by="g")
    chart = rc.chart(table)
    ax = chart._ax
    assert _ticks(ax) == ["Score", "Twice the score"]
    legend = ax.get_legend()
    assert [text.get_text() for text in legend.get_texts()] == ["Alpha", "Beta", "Gamma"]
    assert legend.get_title().get_text() == "Group"
    assert len(_points(ax)) == 6  # two variables, three groups
    assert _whiskers(ax)[0][1:] == pytest.approx((2.70080170952, 7.29919829048), abs=1e-9)
    # Weighted, the interval is the weighted one, and the table's mean is drawn.
    weighted = rc.chart(_groups_data(weighted=True).report.descriptives(["y"], by="g"))
    beta = sorted(_whiskers(weighted._ax))[1]
    assert beta[1:] == pytest.approx((1.911360860729, 4.538639139271), abs=1e-9)
    assert weighted.weight_note == "weighted by 'w'"


def test_ttest_charts_the_groups_measurements_or_the_test_value():
    data = _groups_data()
    two = data.frame[data.frame["g"] != 3]
    independent = SurveyData(frame=two, variables=data.variables).report.ttest("y", by="g")
    chart = rc.chart(independent)
    assert _ticks(chart._ax) == ["Alpha", "Beta"]
    assert chart._ax.get_title(loc="left").startswith("Score by Group")
    assert _whiskers(chart._ax)[0][1:] == pytest.approx((2.70080170952, 7.29919829048), abs=1e-3)
    assert any("Welch" in text for text in _texts(chart._ax))

    one = SurveyData(frame=data.frame[data.frame["g"] == 1], variables=data.variables)
    tested = rc.chart(one.report.ttest("y", kind="one_sample", mu=3))
    assert [line.get_xdata()[0] for line in tested._ax.lines if line.get_linestyle() == "-"] == [
        3.0
    ]
    frame = pd.DataFrame({"a": [1.0, 2, 3, 4, 5], "b": [2.0, 2, 4, 5, 7]})
    pairs = rc.chart(SurveyData(frame=frame).report.ttest("a", kind="paired", other="b"))
    assert _ticks(pairs._ax) == ["a", "b"]  # the difference is the test's, in the note


def test_paired_tests_draw_the_measurements_and_mcnemars_shares():
    rng = np.random.default_rng(4)
    frame = pd.DataFrame({name: rng.integers(1, 6, 60).astype(float) for name in "abc"})
    data = SurveyData(frame=frame)
    friedman = rc.chart(paired.compare(data, ["a", "b", "c"]).table)
    assert _ticks(friedman._ax) == ["a", "b", "c"]
    assert "Friedman" in friedman._ax.get_title(loc="left")
    wilcoxon = rc.chart(paired.compare(data, ["a", "b"]))  # the result itself is drawable too
    assert _ticks(wilcoxon._ax) == ["a", "b"]  # not the row of differences

    yes = pd.DataFrame({"x": [1, 1, 1, 0, 0, 1, 0, 1, 1, 1], "y": [1, 0, 0, 0, 0, 1, 0, 0, 1, 1]})
    mcnemar = rc.chart(paired.compare(SurveyData(frame=yes), ["x", "y"], test="mcnemar").table)
    assert mcnemar.drawn == "shares"
    points = sorted(_points(mcnemar._ax), key=lambda p: p[1])
    assert [x for x, _ in points] == pytest.approx([70.0, 40.0])
    # R: prop.test(7, 10, correct = FALSE)$conf.int -> 0.396778147461 0.892208732594;
    # prop.test(4, 10, ...) -> 0.168180329706 0.687326230266.
    whiskers = _whiskers(mcnemar._ax)
    assert whiskers[0][1:] == pytest.approx((39.6778147461, 89.2208732594), abs=1e-8)
    assert whiskers[1][1:] == pytest.approx((16.8180329706, 68.7326230266), abs=1e-8)


# ─── Proportion CI and NPS ───────────────────────────────────────────────────


def test_a_proportion_is_its_number_and_interval():
    data = _groups_data(weighted=True)
    result = data.analysis.proportion_ci("g", 1, weighted=True)
    chart = rc.chart(result)
    ax = chart._ax
    assert chart.drawn == "interval" and chart.weight_note == "weighted by 'w'"
    assert _percent_text(result["p"] * 100) in _texts(ax)
    assert any("effective base" in text for text in _texts(ax))
    unweighted = rc.chart(_groups_data().analysis.proportion_ci("g", 1))
    assert unweighted.weight_note is None
    assert any("base 17 respondents" in text for text in _texts(unweighted._ax))
    on_weighted = rc.chart(data.analysis.proportion_ci("g", 1))  # weighted=False
    assert on_weighted.weight_note == "unweighted (the weight 'w' is not applied)"


def _percent_text(value: float) -> str:
    return f"{value:.1f} %"


def test_nps_stacks_its_three_groups_in_their_own_colours():
    frame = pd.DataFrame({"nps": [0, 3, 6, 7, 8, 9, 10, 10, 9, 5]})
    table = SurveyData(frame=frame).report.nps("nps")
    chart = rc.chart(table)
    bars = _bars(chart._ax)
    assert [round(bar.get_width(), 1) for bar in bars] == [40.0, 20.0, 40.0]
    assert [round(bar.get_x(), 1) for bar in bars] == [0.0, 40.0, 60.0]
    assert len({bar.get_facecolor() for bar in bars}) == 3
    assert "NPS +0.0" in " ".join(_texts(chart._ax))
    legend = [text.get_text() for text in chart._ax.get_legend().get_texts()]
    assert legend == [
        "Detractors (0–6): 40.0 %",
        "Passives (7–8): 20.0 %",
        "Promoters (9–10): 40.0 %",
    ]


# ─── TURF ────────────────────────────────────────────────────────────────────


def _turf_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "a": [1, 1, 0, 0, 1, 0, 0, 0],
            "b": [0, 1, 1, 0, 0, 0, 0, 1],
            "c": [0, 0, 0, 1, 0, 1, 0, 0],
            "d": [0, 0, 0, 0, 0, 0, 1, 0],
        },
        dtype=float,
    )


def test_turf_draws_the_reach_curve_and_each_options_reach():
    search = turf.turf(_turf_frame(), ["a", "b", "c", "d"], max_size=3)
    chart = rc.chart([search, {"Weight": "w"}])
    assert chart.drawn == "reach" and chart.weight_note == "weighted by 'w'"
    curve = next(line for line in chart._ax.lines if line.get_linestyle() == "-")
    assert list(curve.get_ydata()) == list(search["reach_percent"])
    assert [tick.split(" ")[0] for tick in _ticks(chart._ax, "x")] == ["1", "2", "3"]
    with pytest.raises(rc.ResultChartError, match="TURF draws 'reach'"):
        rc.chart(search, kind="items")

    fixed = turf.evaluate(_turf_frame(), ["a", "b"], items=["a", "b", "c", "d"])
    chart = rc.chart(fixed)
    assert chart.drawn == "items"
    assert _ticks(chart._ax) == ["a", "b"]
    widths = [round(bar.get_width(), 1) for bar in _bars(chart._ax)]
    reach = list(fixed["reach_percent"][:2])
    unique = list(fixed["unique_percent"][:2])
    assert widths == reach + unique
    together = [line for line in chart._ax.lines if line.get_label().startswith("All 2")]
    assert together and together[0].get_xdata()[0] == fixed["reach_percent"].iloc[-1]


# ─── PCA, factor analysis, cluster, regression ──────────────────────────────


def _items_data(n: int = 300) -> SurveyData:
    rng = np.random.default_rng(12)
    latent = rng.normal(size=(n, 2))
    frame = pd.DataFrame(
        {
            f"i{j}": np.clip(np.round(3 + latent[:, j % 2] + rng.normal(size=n) * 0.7), 1, 5)
            for j in range(6)
        }
    )
    frame["w"] = rng.uniform(0.5, 1.5, n)
    variables = VariableMap()
    for j in range(6):
        variables.add(Variable(f"i{j}", "interval", label=f"Item {j}: a statement to agree with"))
    return SurveyData(frame=frame, variables=variables)


def test_the_scree_plot_marks_the_kaiser_line_and_the_components_kept():
    data = _items_data().with_weight("w")
    pca = data.analysis.pca([f"i{j}" for j in range(6)])
    chart = rc.chart([pca.variance, pca.stats])
    ax = chart._ax
    eigen = next(
        line for line in ax.lines if line.get_linestyle() == "-" and len(line.get_xdata()) == 6
    )
    assert list(eigen.get_ydata()) == pytest.approx(list(pca.variance["eigenvalue"]))
    kaiser = [line for line in ax.lines if "Kaiser" in line.get_label()]
    assert kaiser and list(kaiser[0].get_ydata()) == [1.0, 1.0]
    filled = [
        line for line in ax.lines if line.get_marker() == "o" and line.get_linestyle() == "None"
    ]
    kept = int(pca.stats["components"])
    assert len(filled[0].get_xdata()) == kept and len(filled[1].get_xdata()) == 6 - kept
    assert chart.weight_note == "weighted by 'w'"
    # The loadings, as a heatmap of the numbers themselves.
    loadings = rc.chart(pca.loadings)
    assert loadings.drawn == "loadings"
    image = loadings._ax.images[0].get_array()
    assert np.allclose(image, pca.loadings.iloc[:, 1:].to_numpy())
    assert _ticks(loadings._ax, "x") == list(pca.loadings.columns[1:])
    # Both come from one result object in Python.
    assert rc.chart(pca, kind="loadings").drawn == "loadings"


def test_factor_analysis_scree_has_the_parallel_line_and_loadings_their_blanks():
    fa = factor.analyze(
        _items_data(), [f"i{j}" for j in range(6)], criterion="parallel", hide_below=0.3
    )
    scree = rc.chart(fa.variance)
    labels = [line.get_label() for line in scree._ax.lines]
    assert any("parallel analysis" in label for label in labels)
    assert any(label.startswith(f"Eigenvalue ({fa.stats['Factors']} kept") for label in labels)
    assert "Scree plot: minimum residual" in scree._ax.get_title(loc="left")
    loadings = rc.chart(fa.loadings)
    image = loadings._ax.images[0].get_array()
    assert (
        np.ma.is_masked(image)
        and image.mask.sum() == fa.loadings.to_frame().iloc[:, 2:4].isna().sum().sum()
    )
    assert _ticks(loadings._ax)[0] == "Item 0: a statement to agree with"
    assert loadings.weight_note is None
    unweighted = factor.analyze(_items_data().with_weight("w"), [f"i{j}" for j in range(6)])
    assert rc.chart(unweighted.loadings).weight_note == "unweighted (the weight 'w' is not applied)"
    assert rc.chart(unweighted, kind="scree").drawn == "scree"


def test_cluster_profiles_draw_one_line_per_cluster():
    data = _items_data()
    clusters = data.cluster([f"i{j}" for j in range(4)], k=3)
    chart = rc.chart([clusters.centroids, clusters.stats])
    ax = chart._ax
    legend = [text.get_text() for text in ax.get_legend().get_texts()]
    sizes = clusters.centroids["size"].tolist()
    assert [label.split(" (")[0] for label in legend] == ["Cluster 1", "Cluster 2", "Cluster 3"]
    assert all(f"n = {size}" in label for label, size in zip(legend, sizes, strict=True))
    profiles = [line for line in ax.lines if line.get_linestyle() == "-"]
    assert len(profiles) == 3
    assert list(profiles[0].get_xdata()) == pytest.approx(
        clusters.centroids.iloc[0, 3:].astype(float).tolist()
    )
    assert len({tuple(line.get_color()) for line in profiles}) == 3
    # The assignment itself names the items by their labels.
    assert _ticks(rc.chart(clusters)._ax)[0] == "Item 0: a statement to agree with"


def test_regression_is_a_forest_without_the_intercept():
    rng = np.random.default_rng(3)
    frame = pd.DataFrame({"x1": rng.normal(size=80), "x2": rng.normal(size=80)})
    frame["y"] = 1 + 2 * frame["x1"] - frame["x2"] + rng.normal(size=80)
    model = SurveyData(frame=frame).analysis.regression("y", ["x1", "x2"])
    chart = rc.chart([model.table, model.stats])
    ax = chart._ax
    assert _ticks(ax) == ["x1", "x2"]
    from scipy.stats import t as t_dist

    q = t_dist.ppf(0.975, 80 - 3)
    table = model.table.set_index("term")
    for (_, low, high), term in zip(_whiskers(ax), ["x1", "x2"], strict=True):
        estimate, se = table.loc[term, "estimate"], table.loc[term, "std_error"]
        assert (low, high) == pytest.approx((estimate - q * se, estimate + q * se))
    assert "t with 77 df" in ax.get_xlabel()
    # Without the stat, the base is unknown and the interval says it is normal.
    assert "normal approximation" in rc.chart(model.table)._ax.get_xlabel()

    frame["buy"] = (frame["y"] > 1).astype(int)
    logit = SurveyData(frame=frame).analysis.regression("buy", ["x1", "x2"])
    chart = rc.chart(logit)
    assert chart._ax.get_xscale() == "log"
    points = sorted(_points(chart._ax), key=lambda p: p[1])
    assert [x for x, _ in points] == pytest.approx(list(logit.table["odds_ratio"][1:]))


# ─── Correlation matrix ──────────────────────────────────────────────────────


def test_the_correlation_heatmap_is_the_tables_lower_triangle_with_marks():
    data = _items_data()
    table = data.report.correlation_matrix(["i0", "i1", "i2"], method="pearson")
    chart = rc.chart(table)
    ax = chart._ax
    image = ax.images[0].get_array()
    coefficients = table.result.coefficients.to_numpy()
    assert image.mask[0, 1] and image.mask[0, 0] and not image.mask[1, 0]
    assert image[2, 0] == pytest.approx(coefficients[2, 0])
    texts = _texts(ax)
    # i0 and i2 load on one factor: their correlation is marked significant,
    # written as APA writes a correlation (.52, without its leading zero).
    expected = f"{coefficients[2, 0]:.2f}".replace("0.", ".", 1)
    assert f"{expected}***" in texts
    assert texts.count("—") == 3
    assert "p < .001" in ax.get_xlabel()


# ─── Code open answers ───────────────────────────────────────────────────────


def _codeframe(**extra):
    payload = {
        "schema_version": "1.0",
        "variable": "why",
        "themes": [
            {"code": 1, "label": "Charging takes too long at the public stations"},
            {"code": 2, "label": "Price"},
        ],
        "assignments": {
            text_coding.fingerprint("slow"): 1,
            text_coding.fingerprint("dear"): 2,
        },
    }
    payload.update(extra)
    return text_coding.parse(payload)


def test_themes_draw_their_shares_and_sentiment_when_there_is_one():
    variables = VariableMap()
    variables.add(Variable("why", "nominal", label="Why?", dtype="str"))
    data = SurveyData(
        frame=pd.DataFrame({"why": ["slow", "slow", "slow", "dear", "other", ""]}),
        variables=variables,
    )
    cf = _codeframe(
        sentiment={text_coding.fingerprint("slow"): -1, text_coding.fingerprint("dear"): 1}
    )
    table = data.report.themes(cf, sentiment=True)
    chart = rc.chart(table)
    assert _ticks(chart._ax) == ["Charging takes too long at the public stations", "Price"]
    assert [round(bar.get_width(), 1) for bar in _bars(chart._ax)] == [75.0, 25.0]
    assert any("Coverage: 80.0 %" in text for text in _texts(chart._ax))
    split = rc.chart(table, kind="sentiment")
    drawn = [bar for bar in _bars(split._ax) if bar.get_width() > 0]
    # All of charging's answers are negative, all of price's positive.
    assert [(round(bar.get_width()), bar.get_facecolor()) for bar in drawn] == [
        (100, matplotlib.colors.to_rgba(rc._NEGATIVE)),
        (100, matplotlib.colors.to_rgba(rc._POSITIVE)),
    ]
    assert [text.get_text() for text in split._ax.get_legend().get_texts()] == [
        "Negative",
        "Neutral",
        "Positive",
    ]
    with pytest.raises(rc.ResultChartError, match="built without sentiment"):
        rc.chart(data.report.themes(_codeframe(), sentiment=True), kind="sentiment")
    with pytest.raises(rc.ResultChartError, match="Also add sentiment off"):
        rc.chart(data.report.themes(cf), kind="sentiment")


# ─── the registry and what the chart refuses ─────────────────────────────────


def test_a_result_the_chart_cannot_draw_is_named_with_what_it_draws():
    table = _groups_data().report.freq("g")
    with pytest.raises(rc.ResultChartError) as error:
        rc.chart(table)
    message = str(error.value)
    assert message.startswith("A Result chart cannot draw a FreqTable (Value, Label, N, %, …).")
    assert "Group means" in message and "Regression" in message
    with pytest.raises(rc.ResultChartError, match="cannot draw statistics"):
        rc.chart([{"model": "OLS", "n": 3}])
    with pytest.raises(rc.ResultChartError, match="Unknown kind 'pie'"):
        rc.chart(_groups_data().report.means("y", by="g"), kind="pie")
    with pytest.raises(rc.ResultChartError, match="Group means draws 'means' or 'means_sd'"):
        rc.chart(_groups_data().report.means("y", by="g"), kind="scree")


def test_a_later_node_registers_its_own_result():
    class Funnel:
        def __init__(self, steps):
            self.steps = steps
            self.stats = {"Weight": "unweighted (the weight 'w' is not applied)"}

    def draw(result, chart):
        ax, _, _ = rc._bars(
            chart,
            list(result.steps),
            list(result.steps.values()),
            list(map(str, result.steps.values())),
        )
        return "Funnel"

    renderer = rc.register(Funnel, ["funnel"], draw, name="Funnel")
    rc.register_output("analyze.funnel", "table", ("funnel",))
    try:
        chart = rc.chart(Funnel({"Saw it": 100, "Clicked": 40, "Bought": 5}))
        assert chart.drawn == "funnel" and rc.kinds_of(chart.result) == ("funnel",)
        assert [bar.get_width() for bar in _bars(chart._ax)] == [100, 40, 5]
        assert chart.weight_note.startswith("unweighted")
        assert rc.output_kinds("analyze.funnel", "table", {}) == ("funnel",)
        # A later registration for the same class wins.
        later = rc.register(Funnel, ["funnel", "steps"], draw, name="Funnel 2")
        assert rc.renderer_for(chart.result) is later
        rc._RENDERERS.remove(later)
    finally:
        rc._RENDERERS.remove(renderer)
        rc._OUTPUTS.pop(("analyze.funnel", "table"))
    with pytest.raises(ValueError, match="other than 'auto'"):
        rc.register(Funnel, ["auto"], draw)


def test_every_builtin_kind_is_listed_and_drawn_by_some_renderer():
    drawn = {kind for renderer in rc._RENDERERS for kind in renderer.kinds}
    assert drawn == set(rc.KINDS)


def test_a_chart_goes_into_a_report(tmp_path):
    report = Report(title="Charts")
    report.add(rc.chart(_groups_data().report.means("y", by="g")), caption="Means")
    report.save(tmp_path / "report.md")
    text = (tmp_path / "report.md").read_text("utf-8")
    assert "![Means](fig_" in text and "*Means*" in text
    figures = list(tmp_path.rglob("fig_*.png"))
    assert len(figures) == 1 and _png_size(figures[0])[0] > 800
    # The HTML embeds the same figure, as the Studio preview shows it.
    assert 'src="data:image/png;base64,' in report.to_html(standalone=True, embed_images=True)


# ─── degenerate results ──────────────────────────────────────────────────────


def test_a_group_of_one_answer_is_drawn_without_whiskers_and_says_why(tmp_path):
    frame = pd.DataFrame({"g": [1, 1, 1, 2], "y": [2.0, 3.0, 4.0, 5.0]})
    variables = VariableMap()
    variables.add(Variable("g", "nominal", label="Group", labels=GROUPS))
    variables.add(Variable("y", "interval", label="Score"))
    table = SurveyData(frame=frame, variables=variables).report.means("y", by="g")
    chart = rc.chart(table)
    assert len(_points(chart._ax)) == 2 and len(_whiskers(chart._ax)) == 1
    assert "5.00 (one answer has no interval)" in _texts(chart._ax)
    sd = rc.chart(table, kind="means_sd")
    assert "5.00 (one answer: no SD)" in _texts(sd._ax)
    assert _png_size(chart.save(tmp_path / "one.png"))[0] > 0


def test_two_variables_with_one_label_stay_two_rows():
    frame = pd.DataFrame({"a": [1.0, 2, 3], "b": [2.0, 3, 5]})
    variables = VariableMap()
    variables.add(Variable("a", "interval", label="Trust"))
    variables.add(Variable("b", "interval", label="Trust"))
    chart = rc.chart(SurveyData(frame=frame, variables=variables).report.descriptives(["a", "b"]))
    assert _ticks(chart._ax) == ["Trust (a)", "Trust (b)"]
    assert [x for x, _ in sorted(_points(chart._ax), key=lambda p: p[1])] == [2.0, 3.333]


def test_nothing_to_test_is_said_in_the_note():
    same = pd.DataFrame({"x": [1, 0, 1, 0], "y": [1, 0, 1, 0]})
    chart = rc.chart(paired.compare(SurveyData(frame=same), ["x", "y"], test="mcnemar").table)
    assert any(
        "McNemar: no respondent answered the two differently" in text for text in _texts(chart._ax)
    )
    flat = pd.DataFrame({"a": [3.0, 3, 3], "b": [3.0, 3, 3], "c": [3.0, 3, 3]})
    friedman = rc.chart(paired.compare(SurveyData(frame=flat), ["a", "b", "c"]).table)
    assert any("Friedman: every respondent gave the same answer" in t for t in _texts(friedman._ax))


def test_empty_and_one_sided_results_draw():
    empty = rc.chart({"p": 0.0, "lower": 0.0, "upper": 0.0, "n": 0.0})
    assert "0.0 %" in _texts(empty._ax)
    promoters = SurveyData(frame=pd.DataFrame({"nps": [9, 10, 10]})).report.nps("nps")
    bars = _bars(rc.chart(promoters)._ax)
    assert [bar.get_width() for bar in bars] == [0.0, 0.0, 100.0]
    variables = VariableMap()
    variables.add(Variable("why", "nominal", label="Why?", dtype="str"))
    uncoded = SurveyData(frame=pd.DataFrame({"why": ["new", "other"]}), variables=variables)
    themes = rc.chart(uncoded.report.themes(_codeframe()))
    assert [bar.get_width() for bar in themes._ax.patches] == [0.0, 0.0]
    assert any("Coverage: 0.0 %" in text for text in _texts(themes._ax))
