"""siamang.data.factor — exploratory factor analysis.

Reference values come from the ``factor_analyzer`` package (0.5.1, which
follows ``psych::fa`` for minres and R's ``factanal`` for maximum likelihood)
fitted to the same data, from ``statsmodels`` for principal axis factoring and
oblimin, and from correlation matrices whose factor structure is known
exactly.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from siamang.core.variable import MissingValue, Variable, VariableMap
from siamang.data import SurveyData, factor

ITEMS = [f"q{i}" for i in range(1, 9)]


def _items(n: int = 240, seed: int = 2026) -> np.ndarray:
    """Two correlated clusters of four 1–5 items. RandomState: its stream is
    frozen, so the data — and the reference values below — never move."""
    rng = np.random.RandomState(seed)
    common = rng.standard_normal((n, 2))
    pattern = np.array(
        [
            [0.8, 0.1],
            [0.7, 0.0],
            [0.65, 0.2],
            [0.6, 0.1],
            [0.1, 0.75],
            [0.0, 0.7],
            [0.2, 0.6],
            [0.05, 0.55],
        ]
    )
    raw = common @ pattern.T + 0.6 * rng.standard_normal((n, 8))
    return np.clip(np.round(raw * 1.2 + 3), 1, 5)


# factor_analyzer.FactorAnalyzer(n_factors=2, method=…, rotation=…).fit(_items()).loadings_
MINRES_VARIMAX = [
    [0.8091, 0.1750],
    [0.6764, -0.0412],
    [0.6715, 0.2915],
    [0.6779, 0.1966],
    [0.1408, 0.7003],
    [0.0398, 0.7301],
    [0.2592, 0.6415],
    [0.0995, 0.6648],
]
MINRES_PROMAX = [
    [0.8228, 0.0127],
    [0.7267, -0.1882],
    [0.6527, 0.1657],
    [0.6791, 0.0637],
    [0.0047, 0.7125],
    [-0.1088, 0.7657],
    [0.1425, 0.6249],
    [-0.0319, 0.6838],
]
MINRES_OBLIMIN = [
    [0.8213, 0.0186],
    [0.7172, -0.1801],
    [0.6577, 0.1681],
    [0.6799, 0.0678],
    [0.0335, 0.7022],
    [-0.0775, 0.7539],
    [0.1675, 0.6169],
    [-0.0042, 0.6736],
]
ML_VARIMAX = [
    [0.8116, 0.1689],
    [0.6733, -0.0425],
    [0.6697, 0.2903],
    [0.6807, 0.1943],
    [0.1423, 0.6992],
    [0.0369, 0.7328],
    [0.2651, 0.6401],
    [0.1088, 0.6620],
]
MINRES_UNROTATED = [
    [0.7078, -0.4291],
    [0.4629, -0.4949],
    [0.6881, -0.2499],
    [0.6275, -0.3232],
    [0.5837, 0.4117],
    [0.5308, 0.5029],
    [0.6293, 0.2876],
    [0.5293, 0.4144],
]


@pytest.mark.parametrize(
    ("method", "rotation", "expected"),
    [
        ("minres", "varimax", MINRES_VARIMAX),
        ("minres", "promax", MINRES_PROMAX),
        ("minres", "oblimin", MINRES_OBLIMIN),
        ("minres", "none", MINRES_UNROTATED),
        ("ml", "varimax", ML_VARIMAX),
    ],
)
def test_loadings_match_factor_analyzer(method, rotation, expected):
    solution = factor.fit(_items(), n_factors=2, method=method, rotation=rotation)
    assert solution.loadings == pytest.approx(np.array(expected), abs=2e-4)


def test_communalities_variance_kmo_and_bartlett_match_factor_analyzer():
    solution = factor.fit(_items(), n_factors=2, rotation="varimax")
    assert solution.communalities == pytest.approx(
        [0.6852, 0.4592, 0.5359, 0.4982, 0.5102, 0.5346, 0.4787, 0.4519], abs=2e-4
    )
    assert (solution.loadings**2).sum(axis=0) == pytest.approx([2.1210, 2.0329], abs=2e-4)
    assert solution.eigenvalues == pytest.approx(
        [3.3513, 1.7551, 0.5586, 0.5431, 0.5125, 0.4774, 0.4544, 0.3477], abs=1e-4
    )
    assert solution.kmo == pytest.approx(0.82736, abs=1e-5)
    assert solution.kmo_items == pytest.approx(
        [0.7868, 0.8090, 0.8567, 0.8493, 0.8351, 0.7912, 0.8559, 0.8364], abs=1e-4
    )
    statistic, df, p = solution.bartlett
    assert statistic == pytest.approx(629.7656829914819, rel=1e-9)
    assert df == 28
    assert p == pytest.approx(8.872074195868672e-115, rel=1e-6)


def test_oblique_rotations_report_structure_and_factor_correlations():
    """factor_analyzer's structure matrix (loadings @ phi) for promax and
    oblimin; the factor correlations are what makes the two differ."""

    promax = factor.fit(_items(), n_factors=2, rotation="promax")
    assert promax.structure[:3] == pytest.approx(
        np.array([[0.8277, 0.3265], [0.6549, 0.0889], [0.7159, 0.4146]]), abs=2e-4
    )
    assert promax.phi == pytest.approx(np.array([[1, 0.3814], [0.3814, 1]]), abs=2e-4)
    oblimin = factor.fit(_items(), n_factors=2, rotation="oblimin")
    assert oblimin.structure[:3] == pytest.approx(
        np.array([[0.8276, 0.2973], [0.6561, 0.0633], [0.7148, 0.3913]]), abs=2e-4
    )
    assert oblimin.phi[0, 1] == pytest.approx(0.3393, abs=2e-4)
    # A rotation changes neither the communalities nor the fit to the
    # correlations: diag(P Φ Pᵀ) is the communality, whatever P and Φ are.
    for solution in (promax, oblimin):
        assert np.diag(solution.loadings @ solution.phi @ solution.loadings.T) == pytest.approx(
            solution.communalities, abs=1e-8
        )
        assert np.diag(solution.phi) == pytest.approx([1.0, 1.0])


def test_sign_and_order_conventions():
    for rotation in ("none", "varimax", "promax", "oblimin"):
        loadings = factor.fit(_items(), n_factors=3, rotation=rotation).loadings
        assert (loadings.sum(axis=0) > 0).all()
        size = (loadings**2).sum(axis=0)
        assert list(size) == sorted(size, reverse=True)


def test_principal_axis_follows_psych_and_approaches_the_converged_solution():
    """psych stops when the communalities' sum moves by less than 0.001; the
    fully converged principal axis solution (statsmodels, tol 1e-12) is the
    minres solution, and the psych-style stop is within 0.001 of it."""

    solution = factor.fit(_items(), n_factors=2, method="principal", rotation="none")
    assert solution.iterations == 7 and solution.converged
    assert solution.loadings == pytest.approx(np.array(MINRES_UNROTATED), abs=1e-3)


def _exact(correlation: np.ndarray, n: int = 200, seed: int = 5) -> np.ndarray:
    """Data whose sample correlation matrix is exactly ``correlation``."""
    rng = np.random.RandomState(seed)
    raw = rng.standard_normal((n, len(correlation)))
    raw -= raw.mean(axis=0)
    orthonormal, _ = np.linalg.qr(raw)
    return orthonormal * np.sqrt(n - 1) @ np.linalg.cholesky(correlation).T


def test_every_extraction_recovers_an_exact_one_factor_structure():
    """R = λλᵀ + diag(1 − λ²) is fitted exactly by one factor with loadings λ:
    minres and ML find it, principal axis to its 0.001 stopping rule, and the
    residuals and the ML test statistic are 0."""

    lam = np.array([0.8, 0.7, 0.6, 0.5, 0.4])
    correlation = np.outer(lam, lam)
    np.fill_diagonal(correlation, 1.0)
    x = _exact(correlation)
    for method, tolerance in (("minres", 1e-6), ("ml", 1e-5), ("principal", 5e-3)):
        solution = factor.fit(x, n_factors=1, method=method)
        assert solution.loadings[:, 0] == pytest.approx(lam, abs=tolerance), method
        assert solution.rmsr < 1e-2
    ml = factor.fit(x, n_factors=1, method="ml")
    statistic, df, p = ml.fit
    assert df == 5 and statistic == pytest.approx(0.0, abs=1e-6) and p == pytest.approx(1.0)


def test_the_ml_test_of_fit_is_the_likelihood_ratio_statistic():
    """F = ln|Σ| − ln|R| + tr(R Σ⁻¹) − p at the ML solution, Σ = LLᵀ + Ψ, scaled
    by Bartlett's (n − 1 − (2p + 5)/6 − 2m/3) as factanal does."""

    x = _items()
    solution = factor.fit(x, n_factors=2, method="ml", rotation="none")
    loadings, r = solution.unrotated, solution.correlation
    sigma = loadings @ loadings.T + np.diag(1 - solution.communalities)
    discrepancy = (
        np.linalg.slogdet(sigma)[1]
        - np.linalg.slogdet(r)[1]
        + np.trace(r @ np.linalg.inv(sigma))
        - len(r)
    )
    statistic, df, _ = solution.fit
    assert df == 13
    assert statistic == pytest.approx((240 - 1 - 21 / 6 - 4 / 3) * discrepancy, rel=1e-6)
    assert statistic == pytest.approx(6.2712165501504735, rel=1e-6)


def test_number_of_factors_by_kaiser_and_by_parallel_analysis():
    x = _items()
    assert factor.fit(x).n_factors == 2  # eigenvalues 3.35 and 1.76 above 1
    parallel = factor.fit(x, criterion="parallel", seed=42)
    assert parallel.n_factors == 2 and parallel.criterion == "parallel"
    # The 95th percentile of 100 random 240 × 8 data sets from RandomState(42).
    assert parallel.parallel[:3] == pytest.approx([1.3486, 1.2384, 1.1555], abs=1e-4)
    assert factor.fit(x, criterion="parallel", seed=42).parallel == pytest.approx(parallel.parallel)


def test_regression_scores_match_factor_analyzer_with_the_sample_sd():
    """factor_analyzer.transform standardises with the population SD; with the
    sample SD (R's scale()) its scores shrink by √((n − 1) / n)."""

    x = _items()
    solution = factor.fit(x, n_factors=2, rotation="varimax")
    scores = solution.scores(x)
    assert scores[:3] == pytest.approx(
        np.array([[-0.81492, -0.52764], [-0.02056, 0.14147], [1.03857, 0.42415]]), abs=1e-4
    )
    z = (x - x.mean(axis=0)) / x.std(axis=0, ddof=1)
    weights = np.linalg.solve(solution.correlation, solution.loadings)
    assert scores == pytest.approx(z @ weights)
    assert scores.mean(axis=0) == pytest.approx([0, 0], abs=1e-12)


def test_what_cannot_be_factored_is_refused_with_the_reason():
    x = _items()
    with pytest.raises(ValueError, match="at least three items; 2 were given"):
        factor.fit(x[:, :2])
    with pytest.raises(ValueError, match="more respondents than items: 8 answered all 8"):
        factor.fit(x[:8])
    flat = x.copy()
    flat[:, 3] = 3
    with pytest.raises(ValueError, match="item 4 has the same answer from every respondent"):
        factor.fit(flat)
    # 0.7 for everyone has an SD of 1e-16, not 0 (the mean is not exactly 0.7):
    # rounding, not spread — it was accepted with a communality of 2e-34.
    flat[:, 3] = 0.7
    assert flat[:, 3].std(ddof=1) > 0
    with pytest.raises(ValueError, match="item 4 has the same answer from every respondent"):
        factor.fit(flat)
    copy = np.column_stack([x, x[:, 0]])
    with pytest.raises(ValueError, match="item 1 and item 9 are perfectly correlated"):
        factor.fit(copy)
    total = np.column_stack([x[:, :4], x[:, :4].sum(axis=1)])
    with pytest.raises(ValueError, match="singular: one item is an exact combination"):
        factor.fit(total, names=["a", "b", "c", "d", "total"])
    with pytest.raises(ValueError, match="8 factors for 8 items"):
        factor.fit(x, n_factors=8)
    with pytest.raises(ValueError, match="Maximum likelihood cannot fit 5 factors to 8 items"):
        factor.fit(x, n_factors=5, method="ml")
    with pytest.raises(ValueError, match="rotation must be one of"):
        factor.fit(x, rotation="quartimax")


def test_warnings_for_a_poor_or_overfitted_solution():
    rng = np.random.RandomState(3)
    noise = rng.standard_normal((300, 5))
    solution = factor.fit(noise, n_factors=1)
    assert any("KMO is" in warning for warning in solution.warnings)
    lam = np.array([0.8, 0.7, 0.6, 0.5])
    correlation = np.outer(lam, lam)
    np.fill_diagonal(correlation, 1.0)
    overfitted = factor.fit(_exact(correlation), n_factors=3)
    assert any("negative degrees of freedom" in warning for warning in overfitted.warnings)


# ─── on survey data ──────────────────────────────────────────────────────────


def _survey(weighted: bool = False) -> SurveyData:
    x = _items()
    frame = pd.DataFrame(x, columns=ITEMS)
    frame.loc[0, "q1"] = 9  # Refused
    frame.loc[1, "q5"] = np.nan
    frame["w"] = 1.0
    refused = (MissingValue(9, "Refused"),)
    variables = VariableMap()
    variables.add_many(
        [
            Variable(name, "ordinal", label=f"Statement {name[1:]}", missing=refused)
            for name in ITEMS
        ]
    )
    data = SurveyData(frame=frame, variables=variables)
    return data.with_weight("w") if weighted else data


def test_analyze_leaves_out_missing_codes_and_builds_the_tables():
    result = factor.analyze(_survey(), ITEMS, n_factors=2, rotation="promax")
    stats = result.stats
    assert stats["N"] == 238 and stats["Excluded"] == 2
    assert stats["Missing codes"] == "1 answer with a missing code (9 = Refused) left out"
    assert stats["Extraction"] == "minimum residual (minres)"
    assert stats["Rotation"] == "promax (power 4), Kaiser-normalized"
    assert stats["Factors"] == 2 and stats["Factors chosen by"] == "fixed"
    assert stats["Bartlett df"] == 28 and 0.8 < stats["KMO"] < 0.9
    assert "Weight" not in stats
    expected = factor.fit(_items()[2:], n_factors=2, rotation="promax")
    loadings = result.loadings.to_frame()
    assert list(loadings.columns) == [
        "Variable",
        "Label",
        "Factor 1",
        "Factor 2",
        "Communality",
        "Uniqueness",
        "MSA",
    ]
    assert list(loadings["Label"])[:2] == ["Statement 1", "Statement 2"]
    assert loadings[["Factor 1", "Factor 2"]].to_numpy() == pytest.approx(
        expected.loadings, abs=5e-4
    )
    assert result.loadings.stats == stats
    variance = result.variance.to_frame()
    assert list(variance["Factor"]) == [f"Factor {i}" for i in range(1, 9)]
    assert variance["Cumulative %"].iloc[-1] == pytest.approx(100.0)
    assert variance["Extracted SS"].notna().sum() == 2
    # Oblique: the rotated variances overlap, so they have no percentages.
    assert "Rotated SS" in variance and "Rotated %" not in variance
    assert "not added up" in result.variance.stats["Note"]
    correlations = result.correlations.to_frame()
    assert correlations.loc[0, "Factor 2"] == pytest.approx(expected.phi[0, 1], abs=1e-3)
    assert result.scores == [] and "factor_1" not in result.data.frame  # none asked for


def test_analyze_adds_labeled_scores_missing_for_those_left_out():
    data = _survey()
    result = factor.analyze(data, ITEMS, scores=True, into="f")
    assert result.scores == ["f1", "f2"]
    frame = result.data.frame
    assert frame.loc[:1, ["f1", "f2"]].isna().all().all()
    assert frame["f1"].notna().sum() == 238
    variable = result.data.variables["f1"]
    assert variable.label == "Factor 1 score (minres, varimax rotation)"
    assert variable.scale == "interval"
    assert result.stats["Scores"] == "f1, f2 (regression method)"
    assert result.stats["Factors chosen by"] == "Kaiser criterion (eigenvalues above 1)"
    rows = data.frame.drop(index=[0, 1])[ITEMS].to_numpy(dtype=float)
    assert frame.loc[2:, "f1"].to_numpy() == pytest.approx(result.solution.scores(rows)[:, 0])
    assert data.frame.columns.tolist() == [*ITEMS, "w"]  # the input is untouched


def test_sorted_and_blanked_loadings_render_without_nan():
    result = factor.analyze(_survey(), ITEMS, n_factors=2, sort=True, hide_below=0.35)
    loadings = result.loadings.to_frame()
    # Grouped by the factor each item loads on most, then by that loading.
    assert set(loadings["Variable"][:4]) == {"q1", "q2", "q3", "q4"}
    first = loadings["Factor 1"][:4].abs().tolist()
    second = loadings["Factor 2"][4:].abs().tolist()
    assert first == sorted(first, reverse=True) and second == sorted(second, reverse=True)
    assert loadings["Factor 2"].isna().sum() == 4 and loadings["Factor 1"].isna().sum() == 4
    markdown = result.loadings.to_markdown()
    assert "nan" not in markdown.lower() and "Extraction = minimum residual" in markdown


def test_analyze_on_weighted_data_says_the_weight_is_not_applied():
    result = factor.analyze(_survey(weighted=True), ITEMS, n_factors=2, rotation="promax")
    note = "unweighted (the weight 'w' is not applied)"
    assert result.stats["Weight"] == note
    # Every output says so, since a report section may show the variance alone.
    for table in (result.loadings, result.variance, result.correlations):
        assert table.stats["Weight"] == note
        assert f"Weight = {note}" in table.to_markdown()
    unweighted = factor.analyze(_survey(), ITEMS, n_factors=2, rotation="promax")
    assert "Weight" not in unweighted.variance.stats
    assert "Weight" not in unweighted.correlations.stats


def test_analyze_refuses_lists_and_duplicates_and_defaults_the_prefix():
    data = _survey()
    with pytest.raises(ValueError, match="q1 is listed twice"):
        factor.analyze(data, ["q1", "q1", "q2"])
    assert factor.analyze(data, ITEMS, scores=True, into="").scores == ["factor_1", "factor_2"]
    listed = data.with_frame(data.frame.assign(q2=[[1, 2]] * len(data.frame)))
    with pytest.raises(TypeError, match="prepare.explode"):
        factor.analyze(listed, ITEMS)


def test_ml_is_started_several_times_and_keeps_the_best_optimum():
    """Three factors on two-factor data: factanal's start alone stopped at a
    local optimum, F = 0.10197, and reported its test of fit (chi-square 5.455,
    p .605) as converged, without a warning. The best of 15 random starts
    reaches F = 0.0927915 at an interior solution; so must the engine, the same
    on every run, and it says that the starts disagreed."""

    rng = np.random.default_rng(7)
    common = rng.normal(size=(60, 2))
    x = np.column_stack(
        [common[:, j % 2] + rng.normal(size=60) for j in range(7)]
        + [common[:, 0] + common[:, 1] + rng.normal(size=60)]
    )
    solution = factor.fit(x, n_factors=3, method="ml")
    objective = 0.0927915362537
    statistic, df, p = solution.fit
    # Bartlett's multiplier: 60 − 1 − (2·8 + 5)/6 − 2·3/3 = 53.5.
    assert statistic == pytest.approx(53.5 * objective, abs=1e-6) and df == 7
    assert solution.converged and solution.uniquenesses.min() > 0.01  # interior
    assert any("different solutions from different starting" in w for w in solution.warnings)
    again = factor.fit(x, n_factors=3, method="ml")
    assert np.array_equal(again.loadings, solution.loadings)
    # A model the data carry has one optimum: no warning, factanal's solution.
    two = factor.fit(x, n_factors=2, method="ml")
    assert not any("starting points" in warning for warning in two.warnings)


def test_scores_land_on_their_rows_when_the_index_repeats():
    """Scores are placed by position: a repeated index label used to raise
    "cannot set using a list-like indexer…" (or put a score on every row that
    shares the label)."""
    data = _survey()
    repeated = data.with_frame(data.frame.set_axis([i // 2 for i in range(len(data.frame))]))
    ours = factor.analyze(repeated, ITEMS, n_factors=2, scores=True).data.frame
    theirs = factor.analyze(data, ITEMS, n_factors=2, scores=True).data.frame
    assert ours.index.tolist() == repeated.frame.index.tolist()
    assert ours["factor_1"].to_numpy() == pytest.approx(theirs["factor_1"].to_numpy(), nan_ok=True)
    assert ours["factor_1"].isna().tolist()[:3] == [True, True, False]
