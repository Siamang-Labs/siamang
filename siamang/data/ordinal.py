"""Ordinal logistic regression: the proportional-odds (cumulative logit) model.

An outcome of ordered answers — dissatisfied to satisfied, never to always — is
neither a number an ordinary regression may average nor a yes/no a logit can
take. The proportional-odds model (McCullagh 1980) keeps the order and nothing
more: for each cut between two neighboring answers ``j | j + 1``

    logit P(y ≤ j | x) = θⱼ − xᵀβ,

one threshold ``θⱼ`` per cut and one coefficient per predictor, the same at
every cut. :func:`ordinal_regression` fits it by maximum likelihood; the
Regression node runs it as its model ``ordinal``
(:func:`siamang.data.models.regression` with ``kind="ordinal"``).

Conventions:

- **Sign.** ``θⱼ − xᵀβ``, as R's ``MASS::polr`` and ``ordinal::clm``, Stata's
  ``ologit``, SPSS's PLUM and statsmodels' ``OrderedModel``: a positive
  coefficient moves the respondents toward the *higher* answers, and
  ``exp(β)`` is the odds ratio of answering above any cut rather than at or
  below it. Some texts write ``θⱼ + xᵀβ``; their coefficients have the other
  sign.
- **Answers.** The outcome's codes in numeric order; the codebook's missing
  codes are left out (and counted), as in every method chosen by hand. Only
  the answers someone gave are categories — an answer nobody gave has no cut to
  estimate — and the statistics name any labeled answer that is missing.
- **Predictors.** Numbers as they are; a nominal predictor as dummy columns
  against its first (lowest) category, as the other models of the node do
  (:func:`siamang.data.models.design_matrix`). There is no intercept: the
  thresholds take its place.
- **Estimation.** The weighted log-likelihood is maximized with SciPy's BFGS
  on the exact (analytic) gradient, with the thresholds written as the first
  one and the logarithms of the gaps between them so their order holds, and on
  centered and scaled predictors so their units do not slow it down; the
  optimum is then polished by Newton steps on the exact Hessian in the
  original units. The standard errors are the square roots of the diagonal of
  the inverse observed information (that Hessian), z = estimate / SE, p from
  the normal distribution, and the odds ratio's interval is Wald's,
  ``exp(β ± z₀.₉₇₅ SE)`` — R's ``exp(confint.default(fit))``; ``confint`` on a
  ``polr`` fit profiles the likelihood instead and gives slightly different
  limits.
- **Fit.** McFadden's pseudo-R² ``1 − ℓ / ℓ₀`` against the thresholds-only
  model (whose maximum is the observed shares of the answers), the
  likelihood-ratio χ² ``2 (ℓ − ℓ₀)`` on as many df as coefficients, and AIC
  ``−2ℓ + 2k`` over all the parameters, as ``polr`` reports it.
- **Weights.** The weights multiply each respondent's log-likelihood, as the
  node's logit does and as ``polr(weights = …)`` and ``clm(weights = …)`` take
  them — frequency weights, so the standard errors count the weights: survey
  weights that average 1 (what Cell weights and Rake weights make) keep the
  sample size, and the statistics say when the weights sum to something else.
  A missing weight counts 0. The standard errors are the model's, not a
  design-based (sandwich) variance.

Refused, with the reason: an outcome with fewer than three answers (the model
is then the logit) or more than :data:`MAX_CATEGORIES`, text that is not a
code, no complete rows, a predictor that does not vary, predictors that are a
combination of each other. Warned in the statistics: a fit that did not
converge, and a predictor that separates the answers — its estimate runs off
toward infinity, and neither it nor its standard error can be read.

The proportional-odds assumption itself (one β for every cut) is not tested
here; the Brant test or a partial-proportional-odds model would.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from siamang.core.variable import VariableMap
    from siamang.data.models import RegressionResult

#: More ordered answers than this are not a set of categories to cut.
MAX_CATEGORIES = 20
#: Newton steps after BFGS, and the gradient at which the optimum is reached.
NEWTON_STEPS = 50
GRADIENT_TOLERANCE = 1e-8
#: A coefficient times its predictor's SD beyond this (an odds ratio of e¹⁰
#: per SD) is a sign that the predictor separates the answers; a standard
#: error beyond SEPARATION_SE, that the data cannot pin the estimate down.
SEPARATION_EFFECT = 10.0
SEPARATION_SE = 1e3

#: The statistics say what the weights sum to when their mean over the
#: respondents modeled is further than this from 1.
WEIGHT_SUM_TOLERANCE = 0.1

MODEL_NAME = "ordinal logit (proportional odds)"
SIGN_NOTE = (
    "a positive coefficient makes the higher answers more likely: "
    "logit P(y ≤ j) = threshold j − xβ, as R's MASS::polr"
)


@dataclass(frozen=True, slots=True)
class OrdinalFit:
    """The maximum-likelihood fit on plain arrays (:func:`fit`)."""

    thresholds: np.ndarray  # J − 1, increasing
    coefficients: np.ndarray  # p
    covariance: np.ndarray | None  # (J − 1 + p) square, thresholds first; None if singular
    log_likelihood: float
    null_log_likelihood: float
    converged: bool
    iterations: int
    gradient: float  # the largest absolute gradient at the optimum


# ── the likelihood ───────────────────────────────────────────────────────────


def _cdf(z: np.ndarray) -> np.ndarray:
    from scipy.special import expit

    return expit(z)


def _density(z: np.ndarray) -> np.ndarray:
    """The logistic density F(1 − F); 0 at ±∞."""
    f = _cdf(z)
    return f * _cdf(-z)


def _between(upper: np.ndarray, lower: np.ndarray) -> np.ndarray:
    """F(upper) − F(lower) without canceling: above 0 it is F(−lower) − F(−upper)."""
    high = lower > 0
    out = _cdf(upper) - _cdf(lower)
    out[high] = _cdf(-lower[high]) - _cdf(-upper[high])
    return np.maximum(out, 1e-300)


def _cuts(theta: np.ndarray, answer: np.ndarray, eta: np.ndarray) -> tuple[np.ndarray, ...]:
    """Each respondent's upper and lower cut, ``θ(y) − η`` and ``θ(y − 1) − η``."""
    upper = np.append(theta, np.inf)[answer] - eta
    lower = np.insert(theta, 0, -np.inf)[answer] - eta
    return upper, lower


def _loglik(
    theta: np.ndarray, beta: np.ndarray, x: np.ndarray, answer: np.ndarray, w: np.ndarray
) -> float:
    upper, lower = _cuts(theta, answer, x @ beta)
    return float(w @ np.log(_between(upper, lower)))


def _gradient(
    theta: np.ndarray, beta: np.ndarray, x: np.ndarray, answer: np.ndarray, w: np.ndarray
) -> tuple[float, np.ndarray, np.ndarray]:
    """The log-likelihood and its gradient in θ and β."""
    cuts = len(theta)
    upper, lower = _cuts(theta, answer, x @ beta)
    p = _between(upper, lower)
    fa, fb = _density(upper), _density(lower)
    grad_theta = np.zeros(cuts)
    top = answer < cuts  # has an upper cut θ(y)
    bottom = answer > 0  # has a lower cut θ(y − 1)
    np.add.at(grad_theta, answer[top], (w * fa / p)[top])
    np.add.at(grad_theta, answer[bottom] - 1, -(w * fb / p)[bottom])
    grad_beta = -x.T @ (w * (fa - fb) / p)
    return float(w @ np.log(p)), grad_theta, grad_beta


def _hessian(
    theta: np.ndarray, beta: np.ndarray, x: np.ndarray, answer: np.ndarray, w: np.ndarray
) -> np.ndarray:
    """The exact Hessian of the log-likelihood, thresholds first.

    With a = θ(y) − η, b = θ(y − 1) − η, P = F(a) − F(b), f the density and
    f' = f (1 − 2F): ∂²ℓ/∂θ(y)² = f'(a)/P − f(a)²/P², ∂²ℓ/∂θ(y−1)² =
    −f'(b)/P − f(b)²/P², ∂²ℓ/∂θ(y)∂θ(y−1) = f(a) f(b)/P², ∂²ℓ/∂θ(y)∂β =
    x [f(a)(f(a) − f(b))/P² − f'(a)/P], ∂²ℓ/∂θ(y−1)∂β = x [f'(b)/P −
    f(b)(f(a) − f(b))/P²], ∂²ℓ/∂β∂βᵀ = x xᵀ [(f'(a) − f'(b))/P − (f(a) −
    f(b))²/P²], each weighted and summed over the respondents.
    """
    cuts, k = len(theta), x.shape[1]
    upper, lower = _cuts(theta, answer, x @ beta)
    p = _between(upper, lower)
    fa, fb = _density(upper), _density(lower)
    da = fa * (1 - 2 * _cdf(upper))
    db = fb * (1 - 2 * _cdf(lower))
    size = cuts + k
    h = np.zeros((size, size))
    top = answer < cuts
    bottom = answer > 0
    both = top & bottom
    # threshold × threshold
    aa = w * (da / p - (fa / p) ** 2)
    bb = w * (-db / p - (fb / p) ** 2)
    ab = w * fa * fb / p**2
    np.add.at(h, (answer[top], answer[top]), aa[top])
    np.add.at(h, (answer[bottom] - 1, answer[bottom] - 1), bb[bottom])
    np.add.at(h, (answer[both], answer[both] - 1), ab[both])
    np.add.at(h, (answer[both] - 1, answer[both]), ab[both])
    # threshold × coefficient
    diff = fa - fb
    ta = w * (fa * diff / p**2 - da / p)
    tb = w * (db / p - fb * diff / p**2)
    cross = np.zeros((cuts, k))
    np.add.at(cross, answer[top], ta[top, None] * x[top])
    np.add.at(cross, answer[bottom] - 1, tb[bottom, None] * x[bottom])
    h[:cuts, cuts:] = cross
    h[cuts:, :cuts] = cross.T
    # coefficient × coefficient
    cc = w * ((da - db) / p - (diff / p) ** 2)
    h[cuts:, cuts:] = (x * cc[:, None]).T @ x
    return h


# ── the fit ──────────────────────────────────────────────────────────────────


def _null(answer: np.ndarray, w: np.ndarray, categories: int) -> tuple[np.ndarray, float]:
    """The thresholds-only model: the cumulative shares' logits, and its ℓ₀."""
    shares = np.bincount(answer, weights=w, minlength=categories) / w.sum()
    cumulative = np.clip(np.cumsum(shares)[:-1], 1e-12, 1 - 1e-12)
    theta = np.log(cumulative / (1 - cumulative))
    present = shares > 0
    ll0 = float(
        np.bincount(answer, weights=w, minlength=categories)[present] @ np.log(shares[present])
    )
    return theta, ll0


def fit(x: Any, answer: Any, weights: Any = None) -> OrdinalFit:
    """The proportional-odds model of ``answer`` (0, 1, …, J − 1) on ``x``.

    ``x`` is respondents × predictors (no intercept), ``weights`` frequency
    weights (default 1). Every answer from 0 to J − 1 must carry weight.
    """

    from scipy.optimize import minimize

    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = x[:, None]
    answer = np.asarray(answer, dtype=int)
    n, k = x.shape
    w = np.ones(n) if weights is None else np.asarray(weights, dtype=float)
    categories = int(answer.max()) + 1 if n else 0
    if categories < 2:
        raise ValueError("an ordinal model needs at least two answers")
    theta0, ll0 = _null(answer, w, categories)
    cuts = categories - 1

    # BFGS on centered, scaled predictors, the thresholds as the first one and
    # the logarithms of the gaps: every step keeps them in order.
    centre = (w @ x) / w.sum() if k else np.zeros(0)
    scale = np.sqrt(np.maximum((w @ (x - centre) ** 2) / w.sum(), 0.0)) if k else np.zeros(0)
    scale[scale == 0] = 1.0
    z = (x - centre) / scale if k else x

    def unpack(u: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        theta = np.cumsum(np.concatenate([u[:1], np.exp(u[1:cuts])]))
        return theta, u[cuts:]

    def objective(u: np.ndarray) -> tuple[float, np.ndarray]:
        theta, beta = unpack(u)
        ll, g_theta, g_beta = _gradient(theta, beta, z, answer, w)
        # dθⱼ/du₀ = 1, dθⱼ/duₘ = exp(uₘ) for m ≤ j: sums of the gradient from m on.
        tail = np.cumsum(g_theta[::-1])[::-1]
        g_u = np.concatenate([[tail[0]], tail[1:] * np.exp(u[1:cuts]), g_beta])
        return -ll, -g_u

    start = np.concatenate([theta0[:1], np.log(np.maximum(np.diff(theta0), 1e-6)), np.zeros(k)])
    found = minimize(
        objective,
        start,
        jac=True,
        method="BFGS",
        options={"gtol": 1e-6 * max(1.0, float(w.sum())) ** 0.5, "maxiter": 1000},
    )
    theta_z, beta_z = unpack(found.x)
    # Back to the predictors' own units: η = Σ β*ⱼ (xⱼ − mⱼ)/sⱼ.
    beta = beta_z / scale if k else beta_z
    theta = theta_z + (float(beta @ centre) if k else 0.0)
    iterations = int(found.nit)

    # Newton on the exact Hessian: the last digits BFGS leaves.
    ll, g_theta, g_beta = _gradient(theta, beta, x, answer, w)
    converged = False
    for _ in range(NEWTON_STEPS):
        gradient = np.concatenate([g_theta, g_beta])
        if float(np.abs(gradient).max()) < GRADIENT_TOLERANCE * max(1.0, float(w.sum())):
            converged = True
            break
        h = _hessian(theta, beta, x, answer, w)
        try:
            step = np.linalg.solve(h, -gradient)
        except np.linalg.LinAlgError:
            break
        size = 1.0
        while size > 1e-6:
            new_theta = theta + size * step[:cuts]
            new_beta = beta + size * step[cuts:]
            if np.all(np.diff(new_theta) > 0):
                new_ll = _loglik(new_theta, new_beta, x, answer, w)
                if new_ll >= ll - 1e-12 * abs(ll):
                    break
            size /= 2
        else:
            break
        theta, beta = new_theta, new_beta
        ll, g_theta, g_beta = _gradient(theta, beta, x, answer, w)
        iterations += 1
    gradient = np.concatenate([g_theta, g_beta])
    largest = float(np.abs(gradient).max()) if gradient.size else 0.0
    converged = converged or largest < GRADIENT_TOLERANCE * max(1.0, float(w.sum()))
    information = -_hessian(theta, beta, x, answer, w)
    covariance: np.ndarray | None
    try:
        covariance = np.linalg.inv(information)
        if not np.all(np.isfinite(covariance)) or np.any(np.diag(covariance) < 0):
            covariance = None
    except np.linalg.LinAlgError:
        covariance = None
    return OrdinalFit(
        thresholds=theta,
        coefficients=beta,
        covariance=covariance,
        log_likelihood=float(ll),
        null_log_likelihood=ll0,
        converged=bool(converged),
        iterations=iterations,
        gradient=largest,
    )


# ── on a frame: what the Regression node runs ────────────────────────────────


def ordinal_regression(
    frame: pd.DataFrame,
    y: str,
    predictors: list[str],
    *,
    weight: str | None = None,
    variables: VariableMap | None = None,
    confidence: float = 0.95,
) -> RegressionResult:
    """The proportional-odds model of the ordered answers ``y`` on ``predictors``.

    Returns a :class:`~siamang.data.models.RegressionResult` of kind
    ``ordinal``: ``table`` has one row per coefficient and then one per
    threshold (``type``), with ``estimate``, ``std_error``, ``statistic`` (z),
    ``p_value``, and for the coefficients ``odds_ratio`` and its Wald interval
    ``odds_ratio_lower`` – ``odds_ratio_upper``; ``stats`` the model, the
    answers' order, N, the log-likelihoods, McFadden's pseudo-R², the
    likelihood-ratio test, AIC, convergence and any warning. See the module's
    docstring for the conventions.
    """

    from scipy.stats import chi2, norm

    from siamang.data import inference
    from siamang.data.listwise import round_p
    from siamang.data.models import RegressionResult, design_matrix

    if not predictors:
        raise ValueError("regression needs at least one predictor.")
    columns = list(dict.fromkeys([y, *predictors]))
    missing = [name for name in columns + ([weight] if weight else []) if name not in frame]
    if missing:
        raise KeyError(f"column not found: {', '.join(map(repr, missing))}")
    from siamang.data import multi

    listed = [column for column in columns if multi.is_multi(frame[column])]
    if listed:
        raise TypeError(
            f"{', '.join(listed)} {'holds' if len(listed) == 1 else 'hold'} multiple-choice "
            "answers (lists of codes), which have no single value to model. Run "
            "prepare.explode first: it turns each option into its own 0/1 column."
        )
    if variables is not None and y in variables:
        problem = outcome_problem(
            _label(y, variables), variables[y].scale, list(_labels(y, variables).values())
        )
        if problem:
            raise ValueError(problem)
    cleaned, left_out = inference.without_missing_codes(frame, columns, variables)
    present = cleaned[columns].notna().all(axis=1).to_numpy()
    data = cleaned.loc[present, columns].reset_index(drop=True)
    name = _label(y, variables)
    if data.empty:
        raise ValueError(
            f"The ordinal model of {name}: no respondent answered it and every predictor."
        )
    outcome = pd.to_numeric(data[y], errors="coerce")
    if outcome.isna().any():
        sample = data.loc[outcome.isna(), y].iloc[0]
        raise ValueError(
            f"{name} holds text that is not a code (for example {sample!r}); an ordinal "
            "model orders the answers by their codes. Recode it to numeric codes first."
        )
    if weight:
        w = pd.to_numeric(cleaned.loc[present, weight], errors="coerce").fillna(0.0)
        w = w.to_numpy(dtype=float)
        if np.any(w < 0):
            raise ValueError(f"The weight column {weight!r} has negative values.")
        if w.sum() <= 0:
            raise ValueError(f"The weights in {weight!r} of the complete rows sum to zero.")
    else:
        w = np.ones(len(data))
    values = outcome.to_numpy(dtype=float)
    carried = np.array(sorted({v for v, weight_of in zip(values, w, strict=True) if weight_of > 0}))
    labels = _labels(y, variables)
    if len(carried) < 3:
        shown = ", ".join(_answer(v, labels) for v in carried) or "none"
        raise ValueError(
            f"{name} has {len(carried)} {'answer' if len(carried) == 1 else 'answers'} here "
            f"({shown}); the ordinal model needs three or more ordered answers — with two, "
            "use the logit."
        )
    if len(carried) > MAX_CATEGORIES:
        raise ValueError(
            f"{name} has {len(carried)} different values here; the ordinal model cuts "
            f"between ordered answers and takes at most {MAX_CATEGORIES}. For a scale of "
            "numbers use the linear model (ols), or group the values into bands first."
        )
    # A respondent weighted 0 on an answer nobody else gave is kept in N but
    # adds nothing, as everywhere a weight is 0.
    keep_answer = np.isin(values, carried)
    answer = np.searchsorted(carried, values)
    answer[~keep_answer] = 0
    w = np.where(keep_answer, w, 0.0)

    x_full, names = design_matrix(data, predictors, variables)
    x = x_full[:, 1:]
    names = names[1:]
    if x.shape[1] == 0:
        raise ValueError("regression needs at least one predictor with two or more values.")
    if np.isnan(x).any():
        bad = [
            predictor
            for predictor in predictors
            if pd.to_numeric(data[predictor], errors="coerce").isna().any()
            and not _nominal(predictor, variables, data[predictor])
        ]
        raise ValueError(
            f"{', '.join(bad) or 'a predictor'} holds text that is not a number; recode it, "
            "or mark it nominal in the codebook to compare its answers."
        )
    weighed = w > 0
    flat = [term for term, column in zip(names, x.T, strict=True) if np.ptp(column[weighed]) == 0]
    if flat:
        raise ValueError(
            f"{', '.join(flat)} {'has' if len(flat) == 1 else 'have'} the same value for every "
            "respondent in the model, so it predicts nothing; leave it out."
        )
    design = np.column_stack([np.ones(int(weighed.sum())), x[weighed]])
    if np.linalg.matrix_rank(design) < design.shape[1]:
        raise ValueError(
            f"The predictors {', '.join(names)} are collinear: one is a combination of the "
            "others (or of a constant), so their effects cannot be told apart. Leave one out."
        )

    result = fit(x, answer, w)
    cuts = len(carried) - 1
    k = len(names)
    estimates = np.concatenate([result.coefficients, result.thresholds])
    if result.covariance is not None:
        order = np.r_[cuts : cuts + k, 0:cuts]  # coefficients first, as the table
        se = np.sqrt(np.clip(np.diag(result.covariance)[order], 0.0, None))
    else:
        se = np.full(k + cuts, np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        z = np.where(se > 0, estimates / se, np.nan)
    p_values = np.where(np.isfinite(z), 2 * norm.sf(np.abs(z)), np.nan)
    q = float(norm.ppf((1 + confidence) / 2))
    answers = [_answer(v, labels) for v in carried]
    # "Low / Medium", where polr writes "Low|Medium": a pipe is a cell border in
    # a Markdown table, and would push the threshold's numbers a column right.
    cut_names = [f"{answers[j]} / {answers[j + 1]}" for j in range(cuts)]
    table = pd.DataFrame(
        {
            "term": [*names, *cut_names],
            "type": ["coefficient"] * k + ["threshold"] * cuts,
            "estimate": estimates,
            "std_error": se,
            "statistic": z,
            "p_value": p_values,
        }
    )
    with np.errstate(over="ignore"):  # a separated predictor's limit is infinite
        ratio = np.exp(result.coefficients)
        lower = np.exp(result.coefficients - q * se[:k])
        upper = np.exp(result.coefficients + q * se[:k])
    # The thresholds have no odds ratio: blank, not NaN, in a report.
    table["odds_ratio"] = pd.Series([*ratio, *[None] * cuts], dtype=object)
    table["odds_ratio_lower"] = pd.Series([*lower, *[None] * cuts], dtype=object)
    table["odds_ratio_upper"] = pd.Series([*upper, *[None] * cuts], dtype=object)

    ll, ll0 = result.log_likelihood, result.null_log_likelihood
    lr = max(2 * (ll - ll0), 0.0)
    stats: dict[str, Any] = {
        "model": MODEL_NAME,
        "outcome": y,
        "categories": len(carried),
        "order": " < ".join(answers),
        "n": int(len(data)),
        "log_likelihood": ll,
        "pseudo_r_squared": float(1 - ll / ll0) if ll0 < 0 else 0.0,
        "lr_chi_square": lr,
        "lr_df": k,
        "lr_p": round_p(float(chi2.sf(lr, k))),
        "aic": -2 * ll + 2 * (k + cuts),
        "converged": int(result.converged),
        "coefficients": SIGN_NOTE,
        "interval": f"{confidence * 100:g} % Wald interval of the odds ratio",
    }
    warnings = []
    if not result.converged:
        warnings.append(
            f"the fit did not converge (largest gradient {result.gradient:.2g} after "
            f"{result.iterations} iterations): the estimates may not be the maximum"
        )
    spread = x[weighed].std(axis=0)
    separated = [
        term
        for term, size in zip(names, np.abs(result.coefficients) * spread, strict=True)
        if size > SEPARATION_EFFECT
    ]
    if separated:
        warnings.append(
            f"{', '.join(separated)} {'separates' if len(separated) == 1 else 'separate'} the "
            "answers — some answer is predicted (almost) perfectly — so the estimate runs off "
            "toward infinity and neither it nor any standard error can be read; merge sparse "
            "answers or leave the predictor out"
        )
    else:
        vague = [
            term
            for term, error in zip([*names, *cut_names], se, strict=True)
            if np.isfinite(error) and error > SEPARATION_SE
        ]
        if vague:
            warnings.append(
                f"the standard errors of {', '.join(vague)} are huge: the data cannot pin "
                "the estimate down (an answer almost nobody gave, or a predictor that nearly "
                "separates the answers)"
            )
    if result.covariance is None:
        warnings.append("the information matrix is singular, so there are no standard errors")
    unused = [
        _answer(code, labels)
        for code in labels
        if isinstance(code, int | float)
        and not np.isnan(float(code))
        and float(code) not in carried
        and not (variables is not None and y in variables and variables[y].is_missing(code))
    ]
    if unused:
        stats["note"] = (
            f"nobody in the model answered {', '.join(unused)}, so the model has "
            f"{len(carried)} answers"
        )
    if warnings:
        stats["warning"] = "; ".join(warnings)
    note = inference.missing_codes_note(left_out, variables)
    if note:
        stats["missing_codes"] = note
    if weight:
        stats["weight"] = weight
        total = float(w.sum())
        # Survey weights average 1 over the sample, and about 1 over a part of
        # it; weights summing to the population (or to a tenth of the sample)
        # would make the standard errors count those instead.
        if abs(total / len(data) - 1) > WEIGHT_SUM_TOLERANCE:
            stats["weights"] = (
                f"frequencies: they sum to {total:,.1f} over {len(data)} respondents, and the "
                f"standard errors count {total:,.1f}"
            )
    if weight:
        table.attrs["weight"] = weight  # a chart of the table alone says it
    from siamang.data.models import describe_terms

    describe_terms(table, data, y, predictors, variables)
    return RegressionResult(kind="ordinal", table=table, stats=stats)


def outcome_problem(name: str, scale: str | None, answers: Sequence[Any] = ()) -> str | None:
    """Why the variable labeled ``name``, of ``scale``, cannot be an ordinal
    model's outcome, or None: a nominal variable's answers (``answers``, their
    labels) have no order the thresholds could follow — the model would read
    one from the codes (Capital < North < South) and report it as found."""

    if scale != "nominal":
        return None
    shown = ", ".join(str(answer) for answer in list(answers)[:6])
    more = ", …" if len(answers) > 6 else ""
    listed = f" ({shown}{more})" if shown else ""
    return (
        f"{name} is nominal: its answers{listed} have no order, and the ordinal model would "
        "take one from their codes. Use the logit for an outcome of two answers, or recode it "
        "onto an ordered scale (Recode with Scale = ordinal) first."
    )


def _label(name: str, variables: VariableMap | None) -> str:
    if variables is not None and name in variables:
        return variables[name].label or name
    return name


def _labels(name: str, variables: VariableMap | None) -> dict[Any, str]:
    if variables is not None and name in variables:
        return dict(variables[name].labels or {})
    return {}


def _answer(code: Any, labels: dict[Any, str]) -> str:
    value = float(code)
    whole = int(value) if value.is_integer() else value
    label = labels.get(whole, labels.get(value))
    return str(label) if label else str(whole)


def _nominal(name: str, variables: VariableMap | None, series: pd.Series) -> bool:
    if variables is not None and name in variables:
        return variables[name].scale == "nominal"
    return series.dtype == object


__all__ = ["MAX_CATEGORIES", "OrdinalFit", "fit", "ordinal_regression", "outcome_problem"]
