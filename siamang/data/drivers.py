"""Key drivers: which of several predictors matter most for an outcome.

A regression's coefficients answer "what happens to the outcome when this
predictor moves and the others do not" — which is not the question a driver
analysis asks. When the predictors correlate, as ratings of one brand always
do, a coefficient can be small because a neighbour took its share, or even
change sign. Relative importance splits the model's R² between the predictors
instead: each gets the part of the explained variance it accounts for, alone
and together with the others, and the parts add up to R².

:func:`analyze` runs it on a :class:`~siamang.data.survey_data.SurveyData` — the
``analyze.drivers`` node — and :func:`plot` draws the result. Two methods:

- **Johnson's relative weights** (Johnson 2000), the default. The predictors'
  correlation matrix ``Rxx = Q Λ Qᵀ`` gives the orthogonal variables closest to
  them, with loadings ``Λ½ = Q Λ^½ Qᵀ``; the outcome is regressed on those,
  ``β* = Λ½⁻¹ r_xy``, and predictor j's weight is ``Σₖ (Λ½)ⱼₖ² β*ₖ²``. The
  weights sum to R². It is what R's ``rwa`` package and the Python
  ``relativeImp`` package compute.
- **Shapley value decomposition** of R² (``shapley``), known in regression as
  LMG after Lindeman, Merenda & Gold (1980): predictor j's share is its gain in
  R² when it joins the model, averaged over every order in which the predictors
  could enter — ``Σ_S |S|! (p − |S| − 1)! / p! · (R²(S ∪ j) − R²(S))`` over the
  subsets S of the others. Exact, from the R² of all 2^p subsets, as R's
  ``relaimpo::calc.relimp(type = "lmg")``; so it is computed for at most
  :data:`SHAPLEY_LIMIT` predictors (32,768 subsets). The two methods agree
  closely in practice.

Beside the importance the table gives each predictor's correlation with the
outcome (r), its standardized coefficient (β) with the regression's t-test p,
and its variance inflation factor (VIF = the diagonal of ``Rxx⁻¹``). The
statistics give R², adjusted R² and the regression's F-test. Importance is also
shown as a percentage of R², so the shares add up to 100 %.

**Who is analysed.** A respondent missing the outcome or any predictor is left
out (listwise), the codebook's missing codes counted as missing, and the
statistics say how many (:func:`siamang.data.listwise.listwise`). A nominal
variable with more than two answers has no amounts to weigh and is refused with
the way out (a 0/1 variable per answer); one with two answers — a 0/1 variable
from Explode multiple choice — is used as it is.

**Weights.** Everything is computed from the correlation matrix, so a weight
reaches every number through the weighted covariance matrix — R's ``cov.wt``,
which is what ``relaimpo`` uses when given weights; equal weights give the
unweighted result exactly. The tests (the regression's F and each β's t) are
taken on Kish's effective base ``(Σw)² / Σw²`` instead of the number of
respondents, as the weighted Pearson correlation is, so weighting never makes a
result look more certain than the respondents behind it; adjusted R² uses the
same base. A missing weight counts 0.

**Collinearity.** Predictors that are a combination of each other are refused
with their names; a VIF of :data:`VIF_WARNING` or more is warned in the
statistics — the coefficients of such predictors are unstable, while the
importance methods split the variance they share between them. A predictor
whose β has the opposite sign of its correlation with the outcome is named too:
it is a suppressor, and its share says little on its own.
"""

from __future__ import annotations

import math
import textwrap
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

from siamang.data.inference import no_spread
from siamang.data.listwise import distinct, label_of, listwise, p_rounded, rounded
from siamang.reporting.result_table import ResultTable

if TYPE_CHECKING:
    from siamang.data.survey_data import SurveyData

METHODS = ("relative_weights", "shapley")
METHOD_NAMES = {
    "relative_weights": "Johnson's relative weights",
    "shapley": "Shapley value decomposition of R² (LMG)",
}
#: The column the importance is in, by method.
IMPORTANCE_COLUMNS = {"relative_weights": "Relative weight", "shapley": "Shapley value"}
#: The Shapley decomposition fits every subset of the predictors: 2^p models.
SHAPLEY_LIMIT = 15
#: A variance inflation factor at or above this is warned in the statistics.
VIF_WARNING = 10.0

#: The chart's colours: the first two slots of a categorical palette that is
#: distinguishable with every common colour-vision deficiency.
POSITIVE, NEGATIVE = "#2a78d6", "#eb6834"
_INK, _MUTED = "#333333", "#767676"


@dataclass
class DriverTable(ResultTable):
    """The key drivers table; ``analysis`` is the whole result, which a chart draws."""

    analysis: KeyDrivers | None = None


@dataclass(frozen=True, slots=True)
class KeyDrivers:
    """What :func:`analyze` found: the table for a report, its statistics, and
    the unrounded numbers in the predictors' own order."""

    table: DriverTable
    stats: dict[str, Any]
    method: str
    outcome: str  # the outcome's label
    names: list[str]
    labels: list[str]
    correlations: np.ndarray  # r of each predictor with the outcome
    betas: np.ndarray  # standardized coefficients
    importance: np.ndarray  # the method's shares of R², summing to R²
    r_squared: float
    vif: np.ndarray
    n: int
    weight: str | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def percent(self) -> np.ndarray:
        """Importance as a percentage of R² (summing to 100)."""
        if self.r_squared <= 0:
            return np.zeros(len(self.importance))
        return self.importance / self.r_squared * 100


# ── on correlation matrices ──────────────────────────────────────────────────


def relative_weights(r_xx: Any, r_xy: Any) -> np.ndarray:
    """Johnson's (2000) relative weights from the predictors' correlation
    matrix ``r_xx`` and their correlations with the outcome ``r_xy``; they sum
    to R²."""

    r_xx = np.asarray(r_xx, dtype=float)
    r_xy = np.asarray(r_xy, dtype=float)
    eigenvalues, vectors = np.linalg.eigh(r_xx)
    eigenvalues = np.clip(eigenvalues, 0.0, None)
    half = vectors @ np.diag(np.sqrt(eigenvalues)) @ vectors.T
    beta_star = np.linalg.solve(half, r_xy)
    return (half**2) @ (beta_star**2)


def subset_r_squared(r_xx: Any, r_xy: Any) -> np.ndarray:
    """R² of the outcome on every subset of the predictors, indexed by bit mask
    (bit j set: predictor j in the model); R² of the empty model is 0."""

    r_xx = np.asarray(r_xx, dtype=float)
    r_xy = np.asarray(r_xy, dtype=float)
    p = len(r_xy)
    values = np.zeros(1 << p)
    for mask in range(1, 1 << p):
        members = [j for j in range(p) if mask >> j & 1]
        r = r_xy[members]
        values[mask] = float(r @ np.linalg.solve(r_xx[np.ix_(members, members)], r))
    return values


def shapley(r_xx: Any, r_xy: Any) -> np.ndarray:
    """The Shapley value (LMG) decomposition of R²: each predictor's gain in R²
    averaged over every order of entry. Exact; 2^p subset regressions."""

    r_xy = np.asarray(r_xy, dtype=float)
    p = len(r_xy)
    if p > SHAPLEY_LIMIT:
        raise ValueError(shapley_problem(p))
    r2 = subset_r_squared(r_xx, r_xy)
    masks = np.arange(1 << p)
    sizes = np.array([bin(mask).count("1") for mask in masks])
    # The weight of a subset of s others: s! (p − s − 1)! / p!.
    share = np.array(
        [math.factorial(s) * math.factorial(p - s - 1) / math.factorial(p) for s in range(p)]
    )
    values = np.zeros(p)
    for j in range(p):
        bit = 1 << j
        without = masks[(masks & bit) == 0]
        values[j] = float((share[sizes[without]] * (r2[without | bit] - r2[without])).sum())
    return values


def shapley_problem(count: int) -> str:
    """Why the Shapley decomposition is not computed for ``count`` predictors."""
    return (
        f"The Shapley value decomposition averages over every order of the predictors: "
        f"with {count} that is {1 << count:,} subset regressions, and it is computed for at "
        f"most {SHAPLEY_LIMIT} predictors. Use Johnson's relative weights, which come close "
        "to it, or fewer predictors."
    )


def count_problem(method: str, count: int) -> str | None:
    """Why ``method`` cannot weigh ``count`` predictors, or None when it can —
    what :func:`analyze` raises and what ``check_flow`` says before a run."""

    if count < 2:
        given = f"{count} {'was' if count == 1 else 'were'} given"
        return (
            "Key drivers splits R² between two or more predictors; "
            f"{given}. For one predictor, its correlation with the outcome is the whole story."
        )
    if method == "shapley" and count > SHAPLEY_LIMIT:
        return shapley_problem(count)
    return None


def _correlations(matrix: np.ndarray, weights: np.ndarray | None) -> np.ndarray:
    """The (weighted) correlation matrix of the columns of ``matrix``."""
    if weights is None:
        centred = matrix - matrix.mean(axis=0)
        covariance = centred.T @ centred
    else:
        share = weights / weights.sum()
        centred = matrix - share @ matrix
        covariance = (centred * share[:, None]).T @ centred
    scale = np.sqrt(np.diag(covariance))
    return covariance / np.outer(scale, scale)


# ── on survey data ───────────────────────────────────────────────────────────


def analyze(
    data: SurveyData,
    y: str,
    predictors: list[str],
    *,
    method: str = "relative_weights",
) -> KeyDrivers:
    """Key drivers of ``y`` among ``predictors`` — the ``analyze.drivers`` node.

    ``method`` is ``relative_weights`` (Johnson's, the default) or
    ``shapley`` (the LMG decomposition, for at most :data:`SHAPLEY_LIMIT`
    predictors). See the module's docstring for what is computed and how the
    weight reaches it.
    """

    from scipy.stats import f as f_dist
    from scipy.stats import t as t_dist

    if method not in METHODS:
        raise ValueError(f"method must be one of {', '.join(METHODS)}.")
    predictors = list(predictors or [])
    problem = count_problem(method, len(predictors))
    if problem:
        raise ValueError(problem)
    columns = [y, *predictors]
    distinct(columns)
    rows = listwise(data, columns)
    _amounts(data, rows.frame, columns)
    n, p = rows.n, len(predictors)
    outcome = label_of(data, y)
    if n < p + 2:
        raise ValueError(
            f"Key drivers of {outcome} fits a regression on {p} predictors, which needs at "
            f"least {p + 2} respondents who answered all of them; there are {n}."
        )
    matrix = rows.frame[columns].to_numpy(dtype=float)
    weights = _weights(data, rows)
    flat = [
        label_of(data, name)
        for name, column in zip(columns, matrix.T, strict=True)
        if no_spread(column if weights is None else column[weights > 0])
    ]
    if flat:
        what = "is" if len(flat) == 1 else "are"
        raise ValueError(
            f"{', '.join(flat)} {what} the same for every respondent analysed, so there is "
            "no variance to explain or to explain it with; leave it out."
        )
    correlation = _correlations(matrix, weights)
    r_xx, r_xy = correlation[1:, 1:], correlation[1:, 0]
    labels = [label_of(data, name) for name in predictors]
    _collinear(r_xx, labels)
    inverse = np.linalg.inv(r_xx)
    betas = inverse @ r_xy
    r2 = float(np.clip(r_xy @ betas, 0.0, 1.0))
    vif = np.diag(inverse).copy()
    importance = (
        relative_weights(r_xx, r_xy) if method == "relative_weights" else shapley(r_xx, r_xy)
    )

    base = float(n) if weights is None else float(weights.sum() ** 2 / (weights**2).sum())
    df2 = base - p - 1
    stats: dict[str, Any] = {
        "Method": METHOD_NAMES[method],
        "Outcome": outcome,
        "Drivers": p,
        "N": n,
        "R²": rounded(r2, 4),
    }
    beta_p = np.full(p, np.nan)
    if df2 > 0:
        stats["Adjusted R²"] = rounded(1 - (1 - r2) * (base - 1) / df2, 4)
        if r2 >= 1 - 1e-12:
            stats["Note"] = (
                "the drivers explain the outcome exactly, so there is no residual to test "
                "against"
            )
        else:
            f_value = (r2 / p) / ((1 - r2) / df2)
            stats["F"] = rounded(f_value, 3)
            stats["df"] = f"{p}, {int(df2) if float(df2).is_integer() else round(df2, 2)}"
            stats["p"] = p_rounded(float(f_dist.sf(f_value, p, df2)))
            se = np.sqrt((1 - r2) / df2 * np.diag(inverse))
            beta_p = 2 * t_dist.sf(np.abs(betas / se), df2)
    else:
        stats["Note"] = (
            f"with an effective base of {base:.1f} for {p} predictors there are no degrees of "
            "freedom left for the tests"
        )
    if weights is not None:
        stats["Weight"] = data.weight
        stats["Effective N"] = rounded(base, 1)
        stats["Tests on"] = "Kish's effective N"
    warnings = []
    high = [
        (label, value) for label, value in zip(labels, vif, strict=True) if value >= VIF_WARNING
    ]
    if high:
        listed = ", ".join(f"{label} ({value:.1f})" for label, value in high)
        warnings.append(
            f"strong collinearity — VIF {listed}: their betas are unstable, and the importance "
            "splits the variance they share between them"
        )
    suppressors = [
        label
        for label, r, beta in zip(labels, r_xy, betas, strict=True)
        if r * beta < 0 and abs(r) > 0.05 and abs(beta) > 0.05
    ]
    if suppressors:
        warnings.append(
            f"{', '.join(suppressors)}: the beta has the opposite sign of the correlation (a "
            "suppressor), so the share says little about it on its own"
        )
    if warnings:
        stats["Warning"] = "; ".join(warnings)
    rows.report(stats, "the outcome or any predictor")

    column = IMPORTANCE_COLUMNS[method]
    percent = importance / r2 * 100 if r2 > 0 else np.zeros(p)
    order = np.argsort(-importance, kind="stable")
    frame = pd.DataFrame(
        {
            "Rank": np.arange(1, p + 1),
            "Driver": [labels[j] for j in order],
            "r": [rounded(r_xy[j], 3) for j in order],
            "Beta": [rounded(betas[j], 3) for j in order],
            "Beta p": [p_rounded(beta_p[j]) for j in order],
            "VIF": [rounded(vif[j], 2) for j in order],
            column: [rounded(importance[j], 4) for j in order],
            "% of R²": [rounded(percent[j], 1) for j in order],
        }
    )
    table = DriverTable(data=data, frame=frame, footer=dict(stats))
    result = KeyDrivers(
        table=table,
        stats=stats,
        method=method,
        outcome=outcome,
        names=list(predictors),
        labels=labels,
        correlations=r_xy,
        betas=betas,
        importance=importance,
        r_squared=r2,
        vif=vif,
        n=n,
        weight=data.weight,
        notes=warnings,
    )
    table.analysis = result
    return result


def _amounts(data: SurveyData, frame: pd.DataFrame, columns: list[str]) -> None:
    """Refuse a nominal variable with more than two answers: its codes are not amounts."""
    if data.variables is None:
        return
    for name in columns:
        if name not in data.variables or data.variables[name].scale != "nominal":
            continue
        codes = sorted(pd.unique(frame[name]))
        if len(codes) <= 2:
            continue
        labels = data.variables[name].labels or {}
        shown = ", ".join(
            f"{_code(code)} = {labels[_code(code)]}" if _code(code) in labels else str(_code(code))
            for code in codes[:6]
        )
        more = ", …" if len(codes) > 6 else ""
        raise ValueError(
            f"{label_of(data, name)} is nominal with {len(codes)} answers ({shown}{more}): its "
            "codes are not amounts to weigh. Make a 0/1 variable per answer (Explode multiple "
            "choice, or Derive) and use those."
        )


def _code(value: Any) -> Any:
    return int(value) if isinstance(value, float) and value.is_integer() else value


def _weights(data: SurveyData, rows: Any) -> np.ndarray | None:
    if data.weight is None:
        return None
    column = data.weight
    if column not in data.frame.columns:
        raise KeyError(f"column not found: {column!r}")
    values = pd.to_numeric(data.frame[column], errors="coerce").fillna(0.0).to_numpy(dtype=float)
    values = values[rows.mask]
    if np.any(values < 0):
        raise ValueError(f"The weight column {column!r} has negative values.")
    if values.sum() <= 0:
        raise ValueError(f"The weights in {column!r} of the respondents analysed sum to zero.")
    return values


def _collinear(r_xx: np.ndarray, labels: list[str]) -> None:
    """Refuse predictors that are a combination of each other, naming them."""
    eigenvalues = np.linalg.eigvalsh(r_xx)
    if eigenvalues.min() > 1e-10 * max(1.0, eigenvalues.max()):
        return
    # Each predictor's R² on the others: 1 for those in the combination.
    tied = []
    for j in range(len(labels)):
        others = [k for k in range(len(labels)) if k != j]
        sub = r_xx[np.ix_(others, others)]
        r = r_xx[others, j]
        fit = float(r @ np.linalg.pinv(sub) @ r)
        if fit > 1 - 1e-8:
            tied.append(labels[j])
    named = ", ".join(tied) if tied else ", ".join(labels)
    raise ValueError(
        f"{named} are collinear: one is a combination of the others, so their shares cannot "
        "be told apart. Leave one of them out."
    )


# ── the chart ────────────────────────────────────────────────────────────────


def plot(
    result: KeyDrivers,
    *,
    title: str | None = None,
    figsize: tuple[float, float] | None = None,
    ax: Any = None,
) -> Any:
    """The drivers as horizontal bars of their share of R², largest on top.

    A bar is blue when the driver's beta is positive and orange when it is
    negative (with a legend when there are both); each carries its percentage.
    The title names the outcome, the method and R², and a second line says how
    the weight was used. ``ax`` draws into existing axes; otherwise a figure is
    made, ``figsize`` wide (default 10 inches) and as tall as it asks, or
    taller when the rows need it: labels wrap at a third of the width (three
    lines at most, then an ellipsis) and many rows get a smaller font.
    Returns the matplotlib Figure.
    """

    from matplotlib.figure import Figure
    from matplotlib.patches import Patch

    from siamang.reporting import chart_theme

    # The report theme's first two colours, text and grid in a Result chart
    # of palette "theme"; these otherwise.
    up, down = chart_theme.series(POSITIVE, 0), chart_theme.series(NEGATIVE, 1)
    ink, rule = chart_theme.text(_INK), chart_theme.grid("#e6e6e6")

    count = len(result.labels)
    order = np.argsort(-result.importance, kind="stable")
    percent = result.percent[order]
    width = figsize[0] if figsize else 10.0
    size = 10.0 if count <= 12 else 9.0 if count <= 20 else 8.0
    wrap = max(int(width * 72 / 3 / (size * 0.55)), 12)
    labels = [_wrapped(result.labels[j], wrap) for j in order]
    lines = max(label.count("\n") + 1 for label in labels) if labels else 1
    pitch = max(0.32, 0.2 * lines + 0.14) * size / 10
    # The height asked for is a least: rows that would not fit grow the figure
    # rather than print their labels over each other.
    height = max(figsize[1] if figsize else 3.2, count * pitch + 1.9)
    if ax is None:
        fig = Figure(figsize=(width, height))
        ax = fig.add_subplot(1, 1, 1)
    else:
        fig = ax.figure
    negative = result.betas[order] < 0
    colours = [down if flag else up for flag in negative]
    y = np.arange(count)
    ax.barh(y, percent, height=0.62, color=colours, edgecolor="white", linewidth=1.5)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=size, color=ink)
    ax.set_ylim(count - 0.5, -0.5)
    top = float(percent.max()) if count else 1.0
    ax.set_xlim(0, max(top * 1.18, 1.0))
    for position, value in zip(y, percent, strict=True):
        ax.text(
            value + top * 0.012,
            position,
            f"{value:.1f} %",
            va="center",
            ha="left",
            fontsize=size,
            color=ink,
        )
    ax.set_xlabel("Share of R² (%)", fontsize=size + 1, color=ink)
    ax.tick_params(axis="x", labelsize=size, colors=ink)
    ax.tick_params(axis="y", length=0)
    # Only the value axis has lines: a theme's row lines (seaborn's whitegrid,
    # which a chart drawn before may have set) would strike through the bars.
    ax.grid(False)
    ax.grid(axis="x", color=rule, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(chart_theme.grid("#bdbdbd"))
    if negative.any() and not negative.all():
        ax.legend(
            handles=[
                Patch(color=up, label="positive beta"),
                Patch(color=down, label="negative beta"),
            ],
            loc="lower right",
            frameon=False,
            fontsize=size,
        )
    heading = title or f"Key drivers of {result.outcome}"
    detail = f"{METHOD_NAMES[result.method]}, R² = {result.r_squared:.3f}, N = {result.n}"
    note = f"weighted by '{result.weight}'" if result.weight else None

    def titled(room: float) -> None:
        text = _wrapped(heading, max(int(room / (12 * 0.55)), 20))
        ax.set_title(
            "\n".join([text, detail] + ([note] if note else [])),
            fontsize=12,
            color=ink,
            loc="left",
            pad=10,
        )

    titled(width * 72)
    fig.tight_layout()
    # The title starts at the plot's left edge, which the labels put a third
    # in: wrapped to the room from there, it stays inside the figure.
    titled(width * 72 * (1 - ax.get_position().x0) - 8)
    fig.tight_layout()
    return fig


def _wrapped(text: str, width: int) -> str:
    lines = textwrap.wrap(str(text), width) or [""]
    if len(lines) > 3:
        lines = lines[:3]
        lines[-1] = lines[-1][: max(width - 1, 1)].rstrip() + "…"
    return "\n".join(lines)


__all__ = [
    "IMPORTANCE_COLUMNS",
    "METHODS",
    "METHOD_NAMES",
    "SHAPLEY_LIMIT",
    "VIF_WARNING",
    "DriverTable",
    "KeyDrivers",
    "analyze",
    "count_problem",
    "plot",
    "relative_weights",
    "shapley",
    "subset_r_squared",
]
