"""siamang.data.models: regression, PCA, k-means and reliability on frames
with a known structure (numpy / SciPy only)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from siamang.core.variable import Variable, VariableMap
from siamang.data import SurveyData
from siamang.data.models import kmeans, pca, regression, reliability


def _frame(n: int = 400, seed: int = 3) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    age = rng.integers(18, 70, n).astype(float)
    region = rng.integers(1, 4, n)
    noise = rng.normal(0, 1, n)
    satisfaction = 2.0 + 0.05 * age + np.where(region == 3, 1.5, 0.0) + noise
    recommend = (satisfaction + rng.normal(0, 0.5, n) > 4.5).astype(int)
    # Two latent factors behind six items.
    f1, f2 = rng.normal(size=n), rng.normal(size=n)
    items = {
        "a1": f1 + rng.normal(0, 0.4, n),
        "a2": f1 + rng.normal(0, 0.4, n),
        "a3": f1 + rng.normal(0, 0.4, n),
        "b1": f2 + rng.normal(0, 0.4, n),
        "b2": f2 + rng.normal(0, 0.4, n),
        "b3": f2 + rng.normal(0, 0.4, n),
    }
    return pd.DataFrame(
        {
            "age": age,
            "region": region,
            "satisfaction": satisfaction,
            "recommend": recommend,
            **items,
        }
    )


def test_ols_recovers_the_slopes_and_dummy_codes_nominal_predictors():
    frame = _frame()
    variables = VariableMap()
    variables.add(Variable("region", "nominal", labels={1: "North", 2: "South", 3: "Capital"}))
    result = regression(frame, "satisfaction", ["age", "region"], variables=variables)
    assert result.kind == "ols" and result.stats["model"] == "OLS"
    table = result.table.set_index("term")
    assert list(table.index) == ["(intercept)", "age", "region = South", "region = Capital"]
    assert abs(table.loc["age", "estimate"] - 0.05) < 0.01
    assert abs(table.loc["region = Capital", "estimate"] - 1.5) < 0.4
    assert table.loc["age", "p_value"] < 0.001 and table.loc["region = South", "p_value"] > 0.01
    assert 0.3 < result.stats["r_squared"] < 0.9 and result.stats["n"] == 400
    # Weights change the fit but not its shape.
    frame["w"] = np.where(frame["region"] == 3, 2.0, 1.0)
    weighted = regression(frame, "satisfaction", ["age"], weight="w")
    assert weighted.stats["model"] == "WLS" and len(weighted.table) == 2


def test_logit_is_chosen_for_a_binary_outcome_and_reports_odds_ratios():
    frame = _frame()
    result = regression(frame, "recommend", ["satisfaction"])
    assert result.kind == "logit" and result.stats["model"] == "logit"
    assert result.stats["outcome"] == "recommend = 1" and result.stats["converged"] == 1
    table = result.table.set_index("term")
    assert table.loc["satisfaction", "estimate"] > 0 and table.loc["satisfaction", "odds_ratio"] > 1
    assert table.loc["satisfaction", "p_value"] < 0.001
    assert 0.2 < result.stats["pseudo_r_squared"] < 1
    with pytest.raises(ValueError, match="exactly two values"):
        regression(frame, "age", ["satisfaction"], kind="logit")
    with pytest.raises(ValueError, match="at least one predictor"):
        regression(frame, "recommend", [])


def test_pca_finds_the_two_factors():
    frame = _frame()
    result = pca(frame, ["a1", "a2", "a3", "b1", "b2", "b3"])
    assert result.stats["components"] == 2 and result.stats["explained_pct"] > 70
    loadings = result.loadings.set_index("item")
    # Each item loads mostly on one component; the a-items agree with each other.
    dominant = loadings[["PC1", "PC2"]].abs().idxmax(axis=1)
    assert dominant["a1"] == dominant["a2"] == dominant["a3"]
    assert dominant["b1"] == dominant["b2"] == dominant["b3"] and dominant["a1"] != dominant["b1"]
    assert list(result.variance["component"]) == [f"PC{i}" for i in range(1, 7)]
    assert abs(result.variance["cumulative_pct"].iloc[-1] - 100) < 1e-6
    fixed = pca(frame, ["a1", "a2", "a3"], n_components=1)
    assert list(fixed.loadings.columns) == ["item", "PC1"]


def test_kmeans_separates_clear_groups_and_numbers_them_by_size():
    rng = np.random.default_rng(1)
    a = rng.normal([0, 0], 0.3, (60, 2))
    b = rng.normal([5, 5], 0.3, (30, 2))
    frame = pd.DataFrame(np.vstack([a, b]), columns=["x", "y"])
    frame.loc[5, "x"] = np.nan  # one row without a cluster
    result = kmeans(frame, ["x", "y"], k=2, seed=7)
    assert result.centroids["cluster"].tolist() == [1, 2]
    assert result.centroids["size"].tolist() == [59, 30]  # largest first
    assert result.centroids.loc[0, "x"] < 1 and result.centroids.loc[1, "x"] > 4
    assert result.labels.isna().sum() == 1 and set(result.labels.dropna()) == {1.0, 2.0}
    # The same seed gives the same partition.
    again = kmeans(frame, ["x", "y"], k=2, seed=7)
    assert again.labels.equals(result.labels)
    with pytest.raises(ValueError, match="k >= 2"):
        kmeans(frame, ["x", "y"], k=1)


def test_survey_data_cluster_adds_a_labeled_variable():
    frame = _frame()
    data = SurveyData(frame=frame)
    assignment = data.cluster(["a1", "a2", "a3"], k=2, into="segment", seed=1)
    assert "segment" in assignment.data.frame.columns
    assert assignment.data.variables["segment"].labels == {1: "Cluster 1", 2: "Cluster 2"}
    assert assignment.centroids["size"].sum() == 400 and assignment.stats["k"] == 2


def test_reliability_reports_alpha_and_item_diagnostics():
    frame = _frame()
    result = reliability(frame, ["a1", "a2", "a3"])
    assert 0.8 < result.alpha < 1 and result.stats["n_items"] == 3
    items = result.items.set_index("item")
    assert (items["item_total_correlation"] > 0.6).all()
    assert (items["alpha_if_deleted"] < result.alpha).all()
    mixed = reliability(frame, ["a1", "a2", "b1"])
    assert mixed.alpha < result.alpha
    with pytest.raises(ValueError, match="at least two"):
        reliability(frame, ["a1"])
