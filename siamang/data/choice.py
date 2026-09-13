"""Discrete choice: what people picked, out of what they were shown.

Every choice method — MaxDiff, conjoint, a simple forced-choice — asks the same
question of the data: given the alternatives in front of this respondent, which
did they take? The shape that answers it is not one row per respondent but one
row per *alternative on offer*, grouped into the sets a single choice was made
from. This module holds that shape and the model fitted on it, so a method only
has to say how its answers become choice sets.

The model is the conditional logit. It is fitted by maximum likelihood with an
analytic gradient and an analytic Hessian, on numpy and ``scipy.optimize``
alone — the engine is imported in-process by servers that install neither
statsmodels nor scikit-learn, and an estimator that only works in some
deployments is worse than none.

One utility is fixed at zero. Choice data says how much better one alternative
is than another and nothing about the level, so without an anchor every utility
could be shifted by the same amount with no change in fit; the estimates are
read against the reference, and every table here names it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

__all__ = ["ChoiceSets", "MnlResult", "mnl", "shares"]


@dataclass(frozen=True, slots=True)
class ChoiceSets:
    """Alternatives in rows, grouped into the choices they were offered for.

    ``group`` must be non-decreasing: rows of one choice set lie together, which
    is what lets every per-set sum be one pass over the array rather than a
    Python loop over sets.
    """

    design: np.ndarray  # (rows, parameters)
    chosen: np.ndarray  # bool, exactly one True per group
    group: np.ndarray  # int, non-decreasing
    names: list[str]
    weight: np.ndarray | None = None  # one per group, not per row
    reference: str = "(reference)"  # the alternative held at utility zero

    def __post_init__(self) -> None:
        rows = self.design.shape[0]
        if not (len(self.chosen) == len(self.group) == rows):
            raise ValueError("design, chosen and group must describe the same rows.")
        if rows == 0:
            raise ValueError("There are no choice sets to fit.")
        if self.design.shape[1] != len(self.names):
            raise ValueError("design has a different number of columns than names.")
        if np.any(np.diff(self.group) < 0):
            raise ValueError("group must be non-decreasing: a choice set's rows lie together.")
        starts = self.starts
        picks = np.add.reduceat(self.chosen.astype(int), starts)
        if not np.all(picks == 1):
            raise ValueError("Every choice set needs exactly one chosen alternative.")
        if self.weight is not None and len(self.weight) != len(starts):
            raise ValueError("weight has one entry per choice set, not per row.")

    @property
    def starts(self) -> np.ndarray:
        """Index where each choice set begins."""

        if len(self.group) == 0:
            return np.empty(0, dtype=int)
        return np.flatnonzero(np.r_[True, self.group[1:] != self.group[:-1]])

    @property
    def sizes(self) -> np.ndarray:
        starts = self.starts
        return np.diff(np.r_[starts, len(self.group)])

    @property
    def n_sets(self) -> int:
        return len(self.starts)


@dataclass(frozen=True, slots=True)
class MnlResult:
    """Utilities, their uncertainty, and how well the model fits."""

    table: pd.DataFrame  # term, estimate, std_error, statistic, p_value, share
    stats: dict[str, float | int | str] = field(default_factory=dict)
    coefficients: np.ndarray = field(default_factory=lambda: np.empty(0))


def _log_likelihood(
    beta: np.ndarray, sets: ChoiceSets, weights: np.ndarray
) -> tuple[float, np.ndarray]:
    """Negative log-likelihood and its gradient, in one pass over the rows."""

    starts, sizes = sets.starts, sets.sizes
    eta = sets.design @ beta
    top = np.repeat(np.maximum.reduceat(eta, starts), sizes)
    exp = np.exp(eta - top)
    denom = np.add.reduceat(exp, starts)
    probability = exp / np.repeat(denom, sizes)

    per_set = eta[sets.chosen] - (np.maximum.reduceat(eta, starts) + np.log(denom))
    loglik = float(np.sum(weights * per_set))

    row_weight = np.repeat(weights, sizes)
    expected = sets.design * (probability * row_weight)[:, None]
    observed = sets.design[sets.chosen] * weights[:, None]
    gradient = observed.sum(axis=0) - expected.sum(axis=0)
    return -loglik, -gradient


def _hessian(beta: np.ndarray, sets: ChoiceSets, weights: np.ndarray) -> np.ndarray:
    """Observed information at ``beta`` — exact, not a difference of gradients."""

    starts, sizes = sets.starts, sets.sizes
    eta = sets.design @ beta
    top = np.repeat(np.maximum.reduceat(eta, starts), sizes)
    exp = np.exp(eta - top)
    probability = exp / np.repeat(np.add.reduceat(exp, starts), sizes)

    weighted = sets.design * probability[:, None]
    mean = np.add.reduceat(weighted, starts, axis=0)  # per set: Σ p_j x_j
    outer = np.einsum("ij,ik->ijk", weighted, sets.design)
    information = np.add.reduceat(outer, starts, axis=0)
    information -= np.einsum("ij,ik->ijk", mean, mean)
    return np.einsum("i,ijk->jk", weights, information)


def mnl(sets: ChoiceSets, *, max_iter: int = 200) -> MnlResult:
    """Fit a conditional logit to the choice sets.

    ``share`` in the table is the utility put back on a scale people read: the
    probability each alternative would be picked if all of them were offered
    together, times a hundred. Utilities are logs of odds and get compared by
    people who do not read logs; shares are the same information in the units
    the question was asked in.
    """

    from scipy.optimize import minimize
    from scipy.stats import norm

    weights = (
        np.ones(sets.n_sets, dtype=float) if sets.weight is None else np.asarray(sets.weight, float)
    )
    start = np.zeros(sets.design.shape[1], dtype=float)
    null_loglik = -_log_likelihood(start, sets, weights)[0]

    fit = minimize(
        _log_likelihood,
        start,
        args=(sets, weights),
        jac=True,
        method="L-BFGS-B",
        options={"maxiter": max_iter},
    )
    beta = np.asarray(fit.x, dtype=float)
    loglik = -float(fit.fun)

    information = _hessian(beta, sets, weights)
    covariance = np.linalg.pinv(information)
    errors = np.sqrt(np.clip(np.diag(covariance), 0.0, None))
    with np.errstate(divide="ignore", invalid="ignore"):
        statistic = np.where(errors > 0, beta / errors, 0.0)
    p_value = 2.0 * norm.sf(np.abs(statistic))

    # The reference alternative sits at zero by construction and belongs in the
    # table: leaving it out makes a reader hunt for the item they are comparing
    # everything against.
    utilities = np.r_[beta, 0.0]
    terms = [*sets.names, sets.reference]
    exponent = np.exp(utilities - utilities.max())
    table = pd.DataFrame(
        {
            "term": terms,
            "estimate": np.round(utilities, 4),
            "std_error": np.round(np.r_[errors, 0.0], 4),
            "statistic": np.round(np.r_[statistic, 0.0], 4),
            "p_value": np.round(np.r_[p_value, 1.0], 4),
            "share": np.round(exponent / exponent.sum() * 100, 1),
        }
    )
    stats: dict[str, float | int | str] = {
        "model": "conditional logit",
        "sets": int(sets.n_sets),
        "alternatives": int(sets.design.shape[0]),
        "log_likelihood": round(loglik, 3),
        "null_log_likelihood": round(null_loglik, 3),
        "pseudo_r2": round(1 - loglik / null_loglik, 4) if null_loglik else 0.0,
        "converged": bool(fit.success),
        "reference": sets.reference,
    }
    if not fit.success:
        stats["message"] = str(fit.message)
    return MnlResult(table=table, stats=stats, coefficients=beta)


def shares(utilities: np.ndarray) -> np.ndarray:
    """Utilities as the shares they imply when every alternative is offered."""

    exponent = np.exp(np.asarray(utilities, float) - np.max(utilities))
    total = exponent.sum()
    return exponent / total if total else exponent
