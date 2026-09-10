"""Models beyond descriptives: regression, principal components, k-means and
scale reliability — on plain frames, with numpy and SciPy only.

Every function returns a small result object whose pieces drop straight
into a report: a coefficient table (``DataFrame``) and a statistics
mapping, loadings and explained variance, cluster centroids and sizes.
Weighted variants take a weight column the way the descriptives do.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from siamang.core.variable import VariableMap


@dataclass(frozen=True, slots=True)
class RegressionResult:
    kind: str  # ols | logit
    table: pd.DataFrame  # term, estimate, std_error, statistic, p_value, (odds_ratio)
    stats: dict[str, float | int | str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PcaResult:
    loadings: pd.DataFrame  # item × component
    variance: pd.DataFrame  # component, eigenvalue, variance_pct, cumulative_pct
    stats: dict[str, float | int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ClusterResult:
    labels: pd.Series  # 1..k, NaN where an item was missing
    centroids: pd.DataFrame  # cluster, size, share, one column per item
    stats: dict[str, float | int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ReliabilityResult:
    alpha: float
    items: pd.DataFrame  # item, mean, item_total_correlation, alpha_if_deleted
    stats: dict[str, float | int] = field(default_factory=dict)


# ── design matrices ──────────────────────────────────────────────────────────


def _is_categorical(name: str, variables: VariableMap | None, series: pd.Series) -> bool:
    if variables is not None and name in variables:
        return variables[name].scale == "nominal"
    return series.dtype == object


def _label_of(name: str, code: Any, variables: VariableMap | None) -> str:
    if variables is not None and name in variables:
        labels = variables[name].labels or {}
        if code in labels:
            return str(labels[code])
    return str(code)


def design_matrix(
    frame: pd.DataFrame, predictors: list[str], variables: VariableMap | None = None
) -> tuple[np.ndarray, list[str]]:
    """Intercept plus one column per numeric predictor; a nominal predictor
    becomes dummy columns against its first (lowest) category."""

    columns: list[np.ndarray] = [np.ones(len(frame))]
    names = ["(intercept)"]
    for name in predictors:
        series = frame[name]
        if _is_categorical(name, variables, series):
            levels = sorted(series.dropna().unique(), key=lambda v: (str(type(v)), v))
            for level in levels[1:]:
                columns.append((series == level).astype(float).to_numpy())
                names.append(f"{name} = {_label_of(name, level, variables)}")
        else:
            columns.append(pd.to_numeric(series, errors="coerce").astype(float).to_numpy())
            names.append(name)
    return np.column_stack(columns), names


def _complete(frame: pd.DataFrame, columns: list[str], weight: str | None) -> pd.DataFrame:
    keep = list(dict.fromkeys(columns + ([weight] if weight else [])))
    return frame[keep].dropna().reset_index(drop=True)


# ── regression ───────────────────────────────────────────────────────────────


def regression(
    frame: pd.DataFrame,
    y: str,
    predictors: list[str],
    *,
    kind: str = "auto",
    weight: str | None = None,
    variables: VariableMap | None = None,
) -> RegressionResult:
    """Linear (OLS / WLS) or logistic regression of ``y`` on ``predictors``.

    ``kind="auto"`` fits a logit when ``y`` takes exactly two values (coded
    as 0/1 by their order), OLS otherwise. Rows with a missing value in any
    column are dropped.
    """

    if not predictors:
        raise ValueError("regression needs at least one predictor.")
    if kind not in ("auto", "ols", "logit"):
        raise ValueError("kind must be 'auto', 'ols' or 'logit'.")
    data = _complete(frame, [y, *predictors], weight)
    if data.empty:
        raise ValueError("regression: no complete rows.")
    x, names = design_matrix(data, predictors, variables)
    target = pd.to_numeric(data[y], errors="coerce").astype(float).to_numpy()
    w = data[weight].astype(float).to_numpy() if weight else np.ones(len(data))
    values = np.unique(target)
    if kind == "auto":
        kind = "logit" if len(values) == 2 else "ols"
    if kind == "logit":
        if len(values) != 2:
            raise ValueError("logit needs an outcome with exactly two values.")
        positive = values[1]
        if float(positive).is_integer():
            positive = int(positive)
        target = (target == values[1]).astype(float)
        return _logit(x, target, w, names, y, len(data), positive=positive)
    return _ols(x, target, w, names, y, len(data))


def _p_from_t(t: np.ndarray, df: int) -> np.ndarray:
    from scipy.stats import t as t_dist

    return 2 * t_dist.sf(np.abs(t), df)


def _p_from_z(z: np.ndarray) -> np.ndarray:
    from scipy.stats import norm

    return 2 * norm.sf(np.abs(z))


def _ols(
    x: np.ndarray, y: np.ndarray, w: np.ndarray, names: list[str], outcome: str, n: int
) -> RegressionResult:
    xtw = x.T * w
    beta = np.linalg.pinv(xtw @ x) @ (xtw @ y)
    fitted = x @ beta
    resid = y - fitted
    df_resid = max(n - x.shape[1], 1)
    sigma2 = float((w * resid**2).sum() / df_resid)
    cov = sigma2 * np.linalg.pinv(xtw @ x)
    se = np.sqrt(np.clip(np.diag(cov), 0, None))
    with np.errstate(divide="ignore", invalid="ignore"):
        t = np.where(se > 0, beta / se, np.nan)
    p = _p_from_t(np.nan_to_num(t), df_resid)
    y_mean = float((w * y).sum() / w.sum())
    ss_tot = float((w * (y - y_mean) ** 2).sum())
    ss_res = float((w * resid**2).sum())
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    k = x.shape[1] - 1
    adj = 1 - (1 - r2) * (n - 1) / df_resid if n > k + 1 else r2
    table = pd.DataFrame(
        {"term": names, "estimate": beta, "std_error": se, "statistic": t, "p_value": p}
    )
    stats = {
        "model": "OLS" if np.allclose(w, 1) else "WLS",
        "outcome": outcome,
        "n": n,
        "r_squared": float(r2),
        "adj_r_squared": float(adj),
        "residual_se": float(sigma2**0.5),
    }
    return RegressionResult(kind="ols", table=table, stats=stats)


def _logit(
    x: np.ndarray,
    y: np.ndarray,
    w: np.ndarray,
    names: list[str],
    outcome: str,
    n: int,
    *,
    positive: Any,
) -> RegressionResult:
    beta = np.zeros(x.shape[1])
    converged = False
    for _ in range(50):
        eta = np.clip(x @ beta, -30, 30)
        mu = 1 / (1 + np.exp(-eta))
        wt = w * mu * (1 - mu)
        gradient = x.T @ (w * (y - mu))
        hessian = (x.T * wt) @ x
        step = np.linalg.pinv(hessian) @ gradient
        beta = beta + step
        if float(np.abs(step).max()) < 1e-8:
            converged = True
            break
    eta = np.clip(x @ beta, -30, 30)
    mu = 1 / (1 + np.exp(-eta))
    cov = np.linalg.pinv((x.T * (w * mu * (1 - mu))) @ x)
    se = np.sqrt(np.clip(np.diag(cov), 0, None))
    with np.errstate(divide="ignore", invalid="ignore"):
        z = np.where(se > 0, beta / se, np.nan)
    p = _p_from_z(np.nan_to_num(z))
    eps = 1e-12
    ll = float((w * (y * np.log(mu + eps) + (1 - y) * np.log(1 - mu + eps))).sum())
    p0 = float((w * y).sum() / w.sum())
    ll0 = float((w * (y * np.log(p0 + eps) + (1 - y) * np.log(1 - p0 + eps))).sum())
    table = pd.DataFrame(
        {
            "term": names,
            "estimate": beta,
            "std_error": se,
            "statistic": z,
            "p_value": p,
            "odds_ratio": np.exp(beta),
        }
    )
    stats = {
        "model": "logit",
        "outcome": f"{outcome} = {positive}",
        "n": n,
        "log_likelihood": ll,
        "pseudo_r_squared": float(1 - ll / ll0) if ll0 < 0 else 0.0,
        "converged": int(converged),
    }
    return RegressionResult(kind="logit", table=table, stats=stats)


# ── principal components ─────────────────────────────────────────────────────


def pca(
    frame: pd.DataFrame,
    items: list[str],
    *,
    n_components: int | None = None,
    standardize: bool = True,
) -> PcaResult:
    """Principal components of ``items`` (complete rows). Without
    ``n_components`` the components with an eigenvalue above 1 are kept
    (Kaiser), at least one."""

    if len(items) < 2:
        raise ValueError("pca needs at least two items.")
    data = frame[items].apply(pd.to_numeric, errors="coerce").dropna()
    if len(data) < 3:
        raise ValueError("pca: fewer than three complete rows.")
    matrix = data.to_numpy(dtype=float)
    matrix = matrix - matrix.mean(axis=0)
    if standardize:
        sd = matrix.std(axis=0, ddof=1)
        sd[sd == 0] = 1.0
        matrix = matrix / sd
    _, singular, vt = np.linalg.svd(matrix, full_matrices=False)
    eigen = singular**2 / (len(data) - 1)
    total = float(eigen.sum()) or 1.0
    keep = n_components or max(1, int((eigen > 1).sum()))
    keep = min(keep, len(items))
    components = [f"PC{i + 1}" for i in range(keep)]
    loadings = pd.DataFrame(
        (vt[:keep].T * np.sqrt(eigen[:keep])), index=items, columns=components
    ).reset_index(names="item")
    share = eigen / total * 100
    variance = pd.DataFrame(
        {
            "component": [f"PC{i + 1}" for i in range(len(eigen))],
            "eigenvalue": eigen,
            "variance_pct": share,
            "cumulative_pct": np.cumsum(share),
        }
    )
    stats = {"n": int(len(data)), "components": keep, "explained_pct": float(share[:keep].sum())}
    return PcaResult(loadings=loadings, variance=variance, stats=stats)


# ── k-means ──────────────────────────────────────────────────────────────────


def kmeans(
    frame: pd.DataFrame,
    items: list[str],
    *,
    k: int = 3,
    seed: int | None = 42,
    standardize: bool = True,
    max_iter: int = 100,
) -> ClusterResult:
    """k-means (k-means++ seeding, Lloyd's iterations) on ``items``. Rows
    with a missing item get no cluster."""

    if k < 2:
        raise ValueError("kmeans needs k >= 2.")
    numeric = frame[items].apply(pd.to_numeric, errors="coerce")
    complete = numeric.dropna()
    if len(complete) < k:
        raise ValueError("kmeans: fewer complete rows than clusters.")
    matrix = complete.to_numpy(dtype=float)
    scaled = matrix.copy()
    if standardize:
        mean = scaled.mean(axis=0)
        sd = scaled.std(axis=0, ddof=1)
        sd[sd == 0] = 1.0
        scaled = (scaled - mean) / sd
    rng = np.random.default_rng(seed)
    centers = scaled[[rng.integers(len(scaled))]]
    while len(centers) < k:
        dist = ((scaled[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2).min(axis=1)
        probabilities = (
            dist / dist.sum() if dist.sum() > 0 else np.full(len(scaled), 1 / len(scaled))
        )
        centers = np.vstack([centers, scaled[rng.choice(len(scaled), p=probabilities)]])
    labels = np.zeros(len(scaled), dtype=int)
    for _ in range(max_iter):
        dist = ((scaled[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        new_labels = dist.argmin(axis=1)
        if np.array_equal(new_labels, labels) and _ > 0:
            break
        labels = new_labels
        for j in range(k):
            members = scaled[labels == j]
            if len(members):
                centers[j] = members.mean(axis=0)
    inertia = float(((scaled - centers[labels]) ** 2).sum())
    # Number clusters by size (largest first) so the labels are stable to read.
    order = np.argsort(-np.bincount(labels, minlength=k), kind="stable")
    rank = {old: new + 1 for new, old in enumerate(order)}
    numbered = np.array([rank[label] for label in labels])
    series = pd.Series(np.nan, index=frame.index, dtype=float)
    series.loc[complete.index] = numbered
    rows = []
    for cluster in range(1, k + 1):
        members = matrix[numbered == cluster]
        row: dict[str, Any] = {
            "cluster": cluster,
            "size": int(len(members)),
            "share_pct": float(len(members) / len(matrix) * 100),
        }
        for i, item in enumerate(items):
            row[item] = float(members[:, i].mean()) if len(members) else float("nan")
        rows.append(row)
    stats = {"n": int(len(complete)), "k": k, "inertia": inertia}
    return ClusterResult(labels=series, centroids=pd.DataFrame(rows), stats=stats)


# ── reliability ──────────────────────────────────────────────────────────────


def reliability(frame: pd.DataFrame, items: list[str]) -> ReliabilityResult:
    """Cronbach's alpha with item–total correlations and alpha if deleted."""

    if len(items) < 2:
        raise ValueError("reliability needs at least two items.")
    data = frame[items].apply(pd.to_numeric, errors="coerce").dropna()
    n = len(data)
    if n < 3:
        raise ValueError("reliability: fewer than three complete rows.")

    def alpha_of(columns: list[str]) -> float:
        k = len(columns)
        if k < 2:
            return float("nan")
        item_var = data[columns].var(axis=0, ddof=1).sum()
        total_var = data[columns].sum(axis=1).var(ddof=1)
        return float((k / (k - 1)) * (1 - item_var / total_var)) if total_var > 0 else 0.0

    alpha = alpha_of(items)
    rows = []
    for item in items:
        others = [i for i in items if i != item]
        rest = data[others].sum(axis=1)
        corr = float(data[item].corr(rest)) if rest.std(ddof=1) > 0 else float("nan")
        rows.append(
            {
                "item": item,
                "mean": float(data[item].mean()),
                "item_total_correlation": corr,
                "alpha_if_deleted": alpha_of(others),
            }
        )
    stats = {"alpha": alpha, "n_items": len(items), "n": int(n)}
    return ReliabilityResult(alpha=alpha, items=pd.DataFrame(rows), stats=stats)
