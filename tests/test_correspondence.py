"""Correspondence analysis — the Perceptual map.

The reference values are quoted from R 4.4: ``ca::ca`` 0.72 and FactoMineR
2.17's ``CA`` on the ``smoke`` table the ca package ships (Greenacre's staff
groups × smoking), and ``chisq.test``. The two packages leave each dimension's
sign as their SVD returns it — on ``smoke`` FactoMineR mirrors ca's second
dimension — so coordinates are compared after aligning each dimension's sign;
this module signs a dimension so the row contributing most to it is positive.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from siamang.core.variable import MissingValue, Variable, VariableMap
from siamang.data import SurveyData, correspondence

SMOKE = np.array([[4, 2, 3, 2], [4, 3, 7, 4], [25, 10, 12, 4], [18, 24, 33, 13], [10, 6, 7, 2]])
GROUPS = {1: "SM", 2: "JM", 3: "SE", 4: "JE", 5: "SC"}
SMOKING = {1: "none", 2: "light", 3: "medium", 4: "heavy"}

#: ca(smoke): principal coordinates (cacoord(fit, "principal")), three dimensions.
CA_ROWS = [
    [-0.06576838388, -0.19373700362, 0.070981028413],
    [0.25895842143, -0.24330457490, -0.033705189737],
    [-0.38059488705, -0.01065990720, -0.005155757497],
    [0.23295190822, 0.05774390775, 0.003305370919],
    [-0.20108912188, 0.07891123093, -0.008081076232],
]
CA_COLUMNS = [
    [-0.39330844858, -0.030492071109, -0.0008904826861],
    [0.09945592079, 0.141064289200, 0.0219980349296],
    [0.19632095640, 0.007359108587, -0.0256590866951],
    [0.29377598524, -0.197765656349, 0.0262108498846],
]


def _aligned(ours: np.ndarray, theirs: list[list[float]]) -> np.ndarray:
    """``ours`` with each dimension's sign turned to match ``theirs``."""
    theirs = np.asarray(theirs)
    signs = np.sign((ours * theirs).sum(axis=0))
    return ours * signs


def test_smoke_matches_ca_and_factominer():
    """ca(smoke): principal inertias 0.0747591058858, 0.0100171805122,
    0.0004135740799 (total 0.08518986048); row masses 0.05699481865, …;
    FactoMineR: % of variance 87.7558731361, 11.7586535018, 0.4854733621, row
    contributions (SE 51.2005548965 on the first dimension, JM 55.1150551610
    on the second), cos² and inertias (SM 0.002672932363, …)."""

    solution = correspondence.ca(SMOKE)
    assert list(solution.inertias) == pytest.approx(
        [0.0747591058858, 0.0100171805122, 0.0004135740799], abs=1e-12
    )
    assert solution.total_inertia == pytest.approx(0.08518986048, abs=1e-11)
    assert list(solution.explained) == pytest.approx(
        [87.7558731361, 11.7586535018, 0.4854733621], abs=1e-9
    )
    assert list(solution.row_masses) == pytest.approx(
        [0.05699481865, 0.09326424870, 0.26424870466, 0.45595854922, 0.12953367876], abs=1e-10
    )
    assert list(solution.column_masses) == pytest.approx(
        [0.3160621762, 0.2331606218, 0.3212435233, 0.1295336788], abs=1e-10
    )
    rows = _aligned(solution.row_principal, CA_ROWS)
    assert rows == pytest.approx(np.array(CA_ROWS), abs=1e-10)
    columns = _aligned(solution.column_principal, CA_COLUMNS)
    assert columns == pytest.approx(np.array(CA_COLUMNS), abs=1e-10)
    # Standard coordinates: principal / singular value (ca's rowcoord).
    assert abs(solution.row_standard[0, 1]) == pytest.approx(1.9357079271, abs=1e-9)
    contributions = [
        [0.3297658036, 21.3557600882, 69.433113258],
        [8.3658712302, 55.1150551610, 25.618602573],
        [51.2005548965, 0.2997603695, 1.698417746],
        [33.0973947037, 15.1772191471, 1.204515671],
        [7.0064133660, 8.0522052341, 2.045350752],
    ]
    assert solution.row_contributions * 100 == pytest.approx(np.array(contributions), abs=1e-8)
    cos2 = [
        [0.09223202566, 0.8003363897625, 0.1074315845791],
        [0.52639991251, 0.4646824608990, 0.0089176265870],
        [0.99903294805, 0.0007837196945, 0.0001833322532],
        [0.94193411850, 0.0578762421859, 0.0001896393190],
        [0.86534550593, 0.1332569973539, 0.0013974967113],
    ]
    assert solution.row_cos2 == pytest.approx(np.array(cos2), abs=1e-10)
    inertia = [0.002672932363, 0.011881176996, 0.038314128802, 0.026268627355, 0.006052994961]
    assert list(solution.row_inertia * solution.total_inertia) == pytest.approx(inertia, abs=1e-11)
    column_contributions = [
        [65.399582881, 2.9335998440, 0.06059965803],
        [3.084980273, 46.3173682199, 27.28158933053],
        [16.561650064, 0.1736757979, 51.14032180619],
        [14.953786781, 50.5753561381, 21.51748920525],
    ]
    assert solution.column_contributions * 100 == pytest.approx(
        np.array(column_contributions), abs=1e-8
    )


def test_each_dimension_is_signed_by_the_row_contributing_most():
    """SE carries 51 % of the first dimension, JM 55 % of the second and SM 69 %
    of the third: each lies on its dimension's positive side — so this map's
    first dimension is the mirror of ca's and FactoMineR's, its second of ca's."""

    solution = correspondence.ca(SMOKE)
    assert solution.row_principal[2, 0] > 0 and solution.row_principal[1, 1] > 0
    assert solution.row_principal[0, 2] > 0
    assert solution.row_principal[2, 0] == pytest.approx(-CA_ROWS[2][0])
    assert solution.row_principal[1, 1] == pytest.approx(-CA_ROWS[1][1])
    # A transposed table is the same analysis with rows and columns swapped.
    turned = correspondence.ca(SMOKE.T)
    assert list(turned.inertias) == pytest.approx(list(solution.inertias))
    assert np.abs(turned.row_principal) == pytest.approx(np.abs(solution.column_principal))


def test_a_table_that_cannot_be_mapped_says_why():
    with pytest.raises(ValueError, match="at least two rows and two columns"):
        correspondence.ca([[1, 2, 3]])
    with pytest.raises(ValueError, match="same profile.*independent"):
        correspondence.ca([[1, 2, 3], [2, 4, 6]])
    with pytest.raises(ValueError, match="positive total"):
        correspondence.ca([[1, 0], [2, 0]])
    line = correspondence.ca([[10, 5, 3], [2, 6, 9]])
    assert line.dimensions == 1


# ─── on survey data ──────────────────────────────────────────────────────────


def _smoke_survey(weight: float | None = None) -> SurveyData:
    rows = [(i + 1, j + 1) for i in range(5) for j in range(4) for _ in range(int(SMOKE[i, j]))]
    frame = pd.DataFrame(rows, columns=["staff", "smoking"])
    # Three more: a Refused, a blank, and an answer (6) nobody else gave with a blank.
    extra = pd.DataFrame({"staff": [9, np.nan, 6], "smoking": [1, 2, np.nan]})
    frame = pd.concat([frame, extra], ignore_index=True)
    variables = VariableMap()
    variables.add_many(
        [
            Variable("staff", "nominal", label="Staff group",
                     labels={**GROUPS, 6: "Interns", 9: "Refused"},
                     missing=(MissingValue(9, "Refused"),)),
            Variable("smoking", "nominal", label="Smoking", labels=SMOKING),
        ]
    )  # fmt: skip
    data = SurveyData(frame=frame, variables=variables)
    if weight is not None:
        data = data.with_frame(frame.assign(w=weight)).with_weight("w")
    return data


def test_a_crosstab_of_respondents_is_the_table_s_analysis():
    """chisq.test(smoke): X-squared = 16.441643, df = 12, p-value = 0.1718348,
    and R warns the approximation may be incorrect (7 of the 20 expected counts
    are below 5). χ² = n · total inertia = 193 · 0.08518986."""

    result = correspondence.analyze(_smoke_survey(), "staff", column="smoking")
    solution = result.solution
    assert solution.counts == pytest.approx(SMOKE)
    assert list(solution.inertias) == pytest.approx(list(correspondence.ca(SMOKE).inertias))
    stats = result.stats
    assert stats["Map"] == "Staff group × Smoking"
    assert (stats["Rows"], stats["Columns"], stats["N"]) == (5, 4, 193)
    assert stats["Total inertia"] == 0.0852 and stats["Dimensions"] == 3
    assert stats["Dimension 1 %"] == 87.8 and stats["Dimension 2 %"] == 11.8
    assert stats["Map %"] == 99.5
    assert stats["Chi-square"] == 16.442 and stats["df"] == 12 and stats["p"] == 0.1718
    assert stats["Chi-square note"].startswith("7 of the 20 cells expect fewer than 5")
    assert stats["Excluded"] == 3
    assert stats["Excluded because"] == "no answer (or a missing code) to Rows or Columns"
    assert stats["Missing codes"] == "1 answer with a missing code (9 = Refused) left out"
    # The one intern did not say how much they smoke: no row for interns.
    assert stats["Not in the map"] == "Interns (nobody counted in them)"
    assert "Weight" not in stats and json.dumps(stats)
    inertia = result.table.to_frame()
    assert list(inertia.columns) == [
        "Dimension",
        "Singular value",
        "Principal inertia",
        "% of inertia",
        "Cumulative %",
    ]
    assert list(inertia["Principal inertia"]) == [0.07476, 0.01002, 0.00041]
    rows = result.rows.to_frame()
    assert list(rows.columns) == [
        "Staff group",
        "Mass",
        "Quality",
        "Inertia %",
        "Dim 1",
        "Contribution 1 %",
        "cos² 1",
        "Dim 2",
        "Contribution 2 %",
        "cos² 2",
    ]
    assert list(rows["Staff group"]) == ["SM", "JM", "SE", "JE", "SC"]
    # ca's summary: quality 893, 991, 1000, 1000, 999 per mil; inertia 31, 139, 450, …
    assert list(rows["Quality"]) == [0.893, 0.991, 1.0, 1.0, 0.999]
    assert list(rows["Inertia %"]) == [3.1, 13.9, 45.0, 30.8, 7.1]
    assert list(rows["Contribution 1 %"]) == [0.3, 8.4, 51.2, 33.1, 7.0]
    assert rows["Dim 1"][2] == 0.381  # SE, positive: it contributes most
    columns = result.columns.to_frame()
    assert list(columns["Smoking"]) == ["none", "light", "medium", "heavy"]
    assert result.rows.stats["Coordinates"] == "principal (symmetric map)"
    assert result.table.analysis is result and result.columns.analysis is result
    # Three dimensions shown on request; more than there are is all of them.
    three = correspondence.analyze(_smoke_survey(), "staff", column="smoking", dimensions=5)
    assert three.shown == 3 and "cos² 3" in three.rows.to_frame().columns


def test_weights_weigh_the_cells_and_the_test_counts_respondents():
    plain = correspondence.analyze(_smoke_survey(), "staff", column="smoking")
    doubled = correspondence.analyze(_smoke_survey(weight=2.0), "staff", column="smoking")
    assert doubled.solution.counts == pytest.approx(2 * SMOKE)
    assert list(doubled.solution.inertias) == pytest.approx(list(plain.solution.inertias))
    stats = doubled.stats
    assert stats["Weight"] == "w" and stats["Weighted N"] == 386.0
    assert stats["Chi-square"] == 16.442  # respondents, not weights
    assert stats["Chi-square counts"] == "respondents (unweighted), as a test of a table must"
    assert doubled.rows.stats["Weight"] == "w"
    data = _smoke_survey()
    uneven = np.where(data.frame["staff"] == 4, 3.0, 1.0)
    weighted = data.with_frame(data.frame.assign(w=uneven)).with_weight("w")
    heavier = correspondence.analyze(weighted, "staff", column="smoking")
    expected = SMOKE.astype(float).copy()
    expected[3] *= 3
    assert heavier.solution.counts == pytest.approx(expected)
    assert list(heavier.solution.inertias) == pytest.approx(
        list(correspondence.ca(expected).inertias)
    )


def _brands() -> SurveyData:
    """A row per respondent and brand rated; three attributes ticked 1/0."""
    frame = pd.DataFrame(
        {
            "brand": [1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, np.nan],
            "modern": [1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 1, 1, 1],
            "cheap": [0, 0, 1, 0, 1, 1, 1, 1, 0, 1, 0, np.nan, 1],
            "friendly": [1, 0, 0, 0, 1, 1, 0, 1, 1, 1, 1, 0, 1],
        }
    )
    variables = VariableMap()
    variables.add_many(
        [
            Variable(
                "brand", "nominal", label="Brand", labels={1: "Acme", 2: "Globex", 3: "Initech"}
            ),
            Variable("modern", "nominal", label="Modern", labels={0: "No", 1: "Yes"}),
            Variable("cheap", "nominal", label="Cheap", labels={0: "No", 1: "Yes"}),
            Variable("friendly", "nominal", label="Friendly", labels={0: "No", 1: "Yes"}),
        ]
    )
    return SurveyData(frame=frame, variables=variables)


def test_an_attribute_grid_counts_ticks_per_brand():
    """Acme: modern 3, cheap 1, friendly 1; Globex 1, 4, 3; Initech 4, 1, 3 (a
    blank is no tick; the respondent with no brand is left out)."""

    result = correspondence.analyze(_brands(), "brand", attributes=["modern", "cheap", "friendly"])
    table = np.array([[3, 1, 1], [1, 4, 3], [4, 1, 3]])
    assert result.solution.counts == pytest.approx(table)
    assert list(result.solution.inertias) == pytest.approx(list(correspondence.ca(table).inertias))
    stats = result.stats
    assert stats["Map"] == "Brand × Attributes" and stats["Counts as yes"] == "1 = Yes"
    assert stats["N"] == 12 and stats["Excluded"] == 1
    assert "Chi-square" not in stats  # a respondent is in several cells
    assert list(result.columns.to_frame()["Attributes"]) == ["Modern", "Cheap", "Friendly"]
    assert list(result.rows.to_frame()["Brand"]) == ["Acme", "Globex", "Initech"]
    # Any code but a yes — a 9 for Refused — is no tick.
    refused = _brands().frame.assign(cheap=lambda f: f["cheap"].replace(1, 9))
    none = correspondence.analyze(
        _brands().with_frame(refused), "brand", attributes=["modern", "cheap", "friendly"],
        yes=1,
    )  # fmt: skip
    assert none.stats["Not in the map"] == "Cheap (nobody counted in them)"
    # "No" as the tick is the complement's map.
    flipped = correspondence.analyze(
        _brands(), "brand", attributes=["modern", "cheap", "friendly"], yes=0
    )
    assert flipped.solution.counts == pytest.approx(np.array([[1, 3, 3], [3, 0, 1], [0, 2, 1]]))
    coded = _brands().frame.assign(modern=lambda f: f["modern"].map({1: 5, 0: 2}))
    with pytest.raises(ValueError, match="name the code .* in Counts as yes"):
        correspondence.analyze(
            _brands().with_frame(coded), "brand", attributes=["modern", "cheap", "friendly"]
        )
    with pytest.raises(ValueError, match="two or more attribute variables; 1 was given"):
        correspondence.analyze(_brands(), "brand", attributes=["modern"])
    with pytest.raises(ValueError, match="either Columns .* or a set of Attributes"):
        correspondence.analyze(_brands(), "brand")
    with pytest.raises(ValueError, match="brand is listed twice"):
        correspondence.analyze(_brands(), "brand", attributes=["brand", "cheap"])


def test_a_multiple_choice_column_counts_each_answer_and_skips_the_test():
    frame = pd.DataFrame(
        {
            "region": [1, 1, 2, 2, 3, 3, 3],
            "used": [[1, 2], [1], [2, 3], [3], [1, 3], [2], []],
        }
    )
    variables = VariableMap()
    variables.add_many(
        [
            Variable("region", "nominal", label="Region", labels={1: "N", 2: "S", 3: "W"}),
            Variable("used", "nominal", label="Used", labels={1: "A", 2: "B", 3: "C"}),
        ]
    )
    result = correspondence.analyze(SurveyData(frame, variables), "region", column="used")
    assert result.solution.counts == pytest.approx(np.array([[2, 1, 0], [0, 1, 2], [1, 1, 1]]))
    assert result.stats["N"] == 6 and result.stats["Excluded"] == 1  # the empty list
    assert result.stats["Chi-square"].startswith("not computed: with a multiple-choice")


def test_a_blank_in_a_nullable_integer_column_is_no_answer():
    """A snapshot and the platform's data hold labelled codes as Int64, a skipped
    answer as pd.NA: the same respondents are left out as with NaN, and no
    "<NA>" row or column joins the map."""

    data = _smoke_survey()
    frame = data.frame.astype({"staff": "Int64", "smoking": "Int64"})
    assert frame["smoking"].isna().sum() == 1 and frame["smoking"].dtype == "Int64"
    nullable = correspondence.analyze(data.with_frame(frame), "staff", column="smoking")
    plain = correspondence.analyze(data, "staff", column="smoking")
    assert nullable.solution.counts == pytest.approx(SMOKE)
    assert list(nullable.rows.to_frame()["Staff group"]) == ["SM", "JM", "SE", "JE", "SC"]
    assert list(nullable.columns.to_frame()["Smoking"]) == ["none", "light", "medium", "heavy"]
    assert nullable.stats == plain.stats
    assert nullable.stats["N"] == 193 and nullable.stats["Excluded"] == 3
    # The attribute layout reads its rows the same way.
    brands = _brands()
    grid = correspondence.analyze(
        brands.with_frame(brands.frame.astype({"brand": "Int64"})),
        "brand",
        attributes=["modern", "cheap", "friendly"],
    )
    assert list(grid.rows.to_frame()["Brand"]) == ["Acme", "Globex", "Initech"]
    assert grid.stats["N"] == 12 and grid.stats["Excluded"] == 1


def test_empty_answers_are_named_and_a_line_is_a_map():
    data = _smoke_survey()
    # A heavy smoker's answer weighted 0 leaves the column empty: off the map, named.
    frame = data.frame.assign(w=np.where(data.frame["smoking"] == 4, 0.0, 1.0))
    weighted = data.with_frame(frame).with_weight("w")
    result = correspondence.analyze(weighted, "staff", column="smoking")
    assert result.stats["Columns"] == 3
    assert result.stats["Not in the map"] == "Interns, heavy (nobody counted in them)"
    frame = data.frame.assign(staff=data.frame["staff"].where(data.frame["staff"] <= 2))
    line = correspondence.analyze(data.with_frame(frame), "staff", column="smoking")
    assert line.solution.dimensions == 1 and line.shown == 1
    assert line.stats["Note"].startswith("the table has one dimension")
    fig = correspondence.plot(line)
    assert fig.axes[0].get_ylabel() == "Dimension 2 (none: the table has 1)"


# ─── the map ─────────────────────────────────────────────────────────────────


def _label_boxes(fig):
    ax = fig.axes[0]
    renderer = fig.canvas.get_renderer()
    return [text.get_window_extent(renderer) for text in ax.texts]


def _overlapping(boxes) -> int:
    return sum(
        1
        for i, a in enumerate(boxes)
        for b in boxes[i + 1 :]
        if min(a.x1, b.x1) - max(a.x0, b.x0) > 0.5 and min(a.y1, b.y1) - max(a.y0, b.y0) > 0.5
    )


def test_the_map_draws_rows_and_columns_with_labels_that_do_not_collide(tmp_path):
    result = correspondence.analyze(_smoke_survey(weight=1.5), "staff", column="smoking")
    fig = correspondence.plot(result)
    fig.savefig(tmp_path / "map.png")
    assert (tmp_path / "map.png").stat().st_size > 10_000
    ax = fig.axes[0]
    rows, columns = ax.collections[:2]
    assert np.asarray(rows.get_offsets()) == pytest.approx(result.solution.row_principal[:, :2])
    assert np.asarray(columns.get_offsets()) == pytest.approx(
        result.solution.column_principal[:, :2]
    )
    assert len({tuple(rows.get_facecolor()[0]), tuple(columns.get_facecolor()[0])}) == 2
    assert sorted(text.get_text() for text in ax.texts) == sorted(
        [*GROUPS.values(), *SMOKING.values()]
    )
    assert _overlapping(_label_boxes(fig)) == 0
    assert ax.get_aspect() == 1.0  # one scale on both axes: a symmetric map
    assert ax.get_xlabel() == "Dimension 1 (87.8 % of inertia)"
    assert ax.get_ylabel() == "Dimension 2 (11.8 % of inertia)"
    assert ax.get_title(loc="left").splitlines() == [
        "Perceptual map: Staff group × Smoking",
        "Correspondence analysis, symmetric map — 99.5 % of the inertia shown",
        "weighted by 'w'",
    ]
    assert [text.get_text() for text in ax.get_legend().get_texts()] == ["Staff group", "Smoking"]
    other = correspondence.plot(result, dimensions=(1, 3), title="Smoking by staff")
    assert other.axes[0].get_ylabel() == "Dimension 3 (0.5 % of inertia)"
    assert other.axes[0].get_title(loc="left").startswith("Smoking by staff\n")
    with pytest.raises(ValueError, match="The map has 3 dimensions"):
        correspondence.plot(result, dimensions=(1, 4))


def test_a_crowded_map_of_long_labels_stays_legible():
    """Twelve brands and ten attributes with long names: every label is drawn,
    wraps onto at most two lines, sits inside the axes and overlaps no other."""

    rng = np.random.default_rng(5)
    brands = [f"Brand number {i} with a rather long trading name" for i in range(12)]
    attributes = [f"Attribute statement {j} about the shopping trip" for j in range(10)]
    position_b, position_a = rng.normal(size=(12, 2)), rng.normal(size=(10, 2))
    rows = []
    for b in range(12):
        chance = 1 / (1 + np.exp(-(position_b[b] @ position_a.T - 0.5)))
        rows += [[b, *(rng.random(10) < chance).astype(int)] for _ in range(80)]
    frame = pd.DataFrame(rows, columns=["brand", *[f"a{j}" for j in range(10)]])
    variables = VariableMap()
    variables.add_many(
        [Variable("brand", "nominal", label="Brand", labels=dict(enumerate(brands)))]
        + [Variable(f"a{j}", "nominal", label=name) for j, name in enumerate(attributes)]
    )
    result = correspondence.analyze(
        SurveyData(frame, variables), "brand", attributes=[f"a{j}" for j in range(10)]
    )
    fig = correspondence.plot(result)
    ax = fig.axes[0]
    texts = [text.get_text() for text in ax.texts]
    assert len(texts) == 22 and all(text.count("\n") <= 1 for text in texts)
    boxes = _label_boxes(fig)
    assert _overlapping(boxes) == 0
    area = ax.get_window_extent(fig.canvas.get_renderer())
    assert all(
        box.x0 >= area.x0 - 1 and box.x1 <= area.x1 + 1 and box.y0 >= area.y0 - 1
        and box.y1 <= area.y1 + 1
        for box in boxes
    )  # fmt: skip
