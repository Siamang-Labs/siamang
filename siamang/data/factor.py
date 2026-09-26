"""Exploratory factor analysis: which items move together, and how strongly.

Principal components (:func:`siamang.data.models.pca`) summarise all of the
items' variance. A factor analysis models only what the items *share*: each
item is a weighted sum of a few common factors plus a part of its own, and the
loadings say how much of each item each factor explains. It is what a scale is
checked with before its items are averaged into an index.

:func:`analyze` runs it on a :class:`~siamang.data.survey_data.SurveyData`
and returns tables for a report and, when asked, the data with a score per
factor; :func:`fit` is the same on a plain matrix.

The items are standardised (the analysis is of their Pearson correlation
matrix). A respondent missing any item is left out (listwise), the codebook's
missing codes counted as missing. The analysis is unweighted: on weighted data
its statistics say so.

Conventions — chosen to reproduce the ``factor_analyzer`` package and R's
``psych::fa`` (and ``factanal`` for maximum likelihood):

- **Extraction.** ``minres`` minimises the sum of squared residual
  correlations over the uniquenesses (L-BFGS-B, bounds 0.005–1, started from
  1 − the squared multiple correlations), as ``factor_analyzer`` and
  ``psych::fa(fm="minres")``; here with the exact gradient, so it converges to
  the optimum they approach. ``principal`` is iterated principal axis
  factoring as ``psych::fa(fm="pa")``: communalities start at the squared
  multiple correlations and are replaced by the fitted ones until their sum
  changes by less than 0.001, at most 50 times. ``ml`` is maximum likelihood,
  ``factanal``'s objective, gradient and start; it adds the likelihood-ratio
  test of fit, ``(n − 1 − (2p + 5)/6 − 2m/3) · F`` on ``((p − m)² − p − m)/2``
  df. With more factors than the data carry the likelihood has local optima
  that one start can stop at, so ML also starts from the minres solution,
  1 − SMC, 0.5 and ten points drawn from a fixed seed, keeps the lowest
  objective (the same data, the same solution) and warns when the starts
  reached different optima.
- **Number of factors.** Fixed, or by the Kaiser criterion (eigenvalues of the
  correlation matrix above 1), or by Horn's parallel analysis: the leading
  eigenvalues that exceed the 95th percentile of those of 100 random normal
  data sets of the same size, drawn from a fixed seed with NumPy's
  ``RandomState`` (whose stream NumPy keeps stable across versions) —
  Glorfeld's (1995) percentile rather than Horn's mean. At least one; fewer
  than the items.
- **Rotation.** ``varimax`` with Kaiser normalization (R's ``stats::varimax``
  algorithm and tolerance, as ``factor_analyzer``). ``promax`` with power 4 in
  ``factor_analyzer``'s (and SPSS's) form: the rows are Kaiser-normalized, the
  target is built from the normalized varimax solution, and the result is
  de-normalized; R's ``stats::promax`` builds the target from the
  de-normalized varimax loadings instead, which moves loadings in the second
  decimal. ``oblimin`` is direct quartimin (γ = 0) by gradient projection
  without normalization, as ``GPArotation::oblimin`` (and so ``psych::fa``)
  and ``factor_analyzer``. Oblique rotations report the pattern loadings and
  the factor correlations; the communalities, which a rotation does not
  change, come from the unrotated solution.
- **Sign and order.** Each factor is signed so its loadings sum to a positive
  number, and the factors are ordered by the sum of their squared (pattern)
  loadings, largest first — both as ``factor_analyzer`` and ``psych`` do. The
  factor correlations follow the same signs and order (``factor_analyzer``
  0.5 reorders the loadings but not its ``phi_``).
- **Variance.** The eigenvalues are those of the correlation matrix; the
  extracted and rotated variance of a factor is the sum of its squared
  loadings. After an oblique rotation the factors overlap, so their variances
  do not add up and no percentage is given for them (SPSS does the same).
- **Adequacy.** Kaiser–Meyer–Olkin, overall and per item (the MSA), from the
  anti-image (partial) correlations; Bartlett's test of sphericity,
  ``−(n − 1 − (2p + 5)/6) ln |R|`` on ``p (p − 1)/2`` df — both exactly as
  ``factor_analyzer``. RMSR is the root mean square of the off-diagonal
  residual correlations.
- **Scores.** The regression (Thurstone) method: the standardised items times
  ``R⁻¹ S``, with ``S`` the structure matrix (the loadings, for an orthogonal
  solution). The items are standardised with the sample SD (n − 1), as R's
  ``scale()`` and ``psych::factor.scores``; ``factor_analyzer.transform`` uses
  the population SD, so its scores are √(n / (n − 1)) times these.

Refused, with the reason: fewer than three items, no more respondents than
items, an item that does not vary, a singular correlation matrix (an item that
is a copy or a total of others), and as many factors as items.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

from siamang.data.inference import no_spread
from siamang.data.listwise import (
    distinct,
    label_of,
    listwise,
    p_rounded,
    result_table,
    rounded,
    unweighted,
)

if TYPE_CHECKING:
    from siamang.data.survey_data import SurveyData
    from siamang.reporting.result_table import ResultTable

EXTRACTIONS = ("minres", "principal", "ml")
ROTATIONS = ("varimax", "promax", "oblimin", "none")
CRITERIA = ("kaiser", "parallel")
OBLIQUE = ("promax", "oblimin")

PROMAX_POWER = 4
PARALLEL_ITERATIONS = 100
PARALLEL_PERCENTILE = 95
#: The bounds of a uniqueness in minres and ml, as factor_analyzer and factanal.
PSI_BOUNDS = (0.005, 1.0)
#: Maximum likelihood is started from four fixed points and this many random
#: ones, drawn from ML_SEED, and keeps the best (see ``_ml``).
ML_RANDOM_STARTS = 10
ML_SEED = 20_260_925

EXTRACTION_NAMES = {
    "minres": "minimum residual (minres)",
    "principal": "principal axis factoring",
    "ml": "maximum likelihood",
}
ROTATION_NAMES = {
    "varimax": "varimax, Kaiser-normalized",
    "promax": f"promax (power {PROMAX_POWER}), Kaiser-normalized",
    "oblimin": "oblimin (direct quartimin, gamma 0)",
    "none": "none",
}


@dataclass(frozen=True, slots=True)
class FactorSolution:
    """A fitted factor model, as numbers (items in the order given)."""

    n: int
    correlation: np.ndarray  # p × p
    eigenvalues: np.ndarray  # of the correlation matrix, largest first
    unrotated: np.ndarray  # p × m, signed and ordered
    loadings: np.ndarray  # p × m, rotated (the pattern, when oblique)
    structure: np.ndarray  # p × m, loadings @ phi
    phi: np.ndarray  # m × m factor correlations (identity when orthogonal)
    communalities: np.ndarray
    kmo: float
    kmo_items: np.ndarray
    bartlett: tuple[float, int, float]  # chi-square, df, p
    method: str
    rotation: str
    criterion: str  # fixed | kaiser | parallel
    parallel: np.ndarray | None  # the random eigenvalues' percentile, per position
    rmsr: float
    fit: tuple[float, int, float | None] | None  # ml: chi-square, df, p
    iterations: int
    converged: bool
    means: np.ndarray
    sds: np.ndarray
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def n_factors(self) -> int:
        return int(self.loadings.shape[1])

    @property
    def uniquenesses(self) -> np.ndarray:
        return 1.0 - self.communalities

    @property
    def oblique(self) -> bool:
        return self.rotation in OBLIQUE

    def scores(self, matrix: Any) -> np.ndarray:
        """Regression-method factor scores of the rows of ``matrix`` (the items
        in the fitted order), standardised by the fitted means and SDs."""
        z = (np.asarray(matrix, dtype=float) - self.means) / self.sds
        weights = np.linalg.solve(self.correlation, self.structure)
        return z @ weights


@dataclass(frozen=True, slots=True)
class FactorAnalysis:
    """What :func:`analyze` returns.

    ``loadings`` (items × factors, with communality, uniqueness and MSA),
    ``variance`` (eigenvalues and variance explained) and ``correlations``
    (between the factors) are report tables whose footer is ``stats``;
    ``data`` is the input, with the factor scores added when asked for.
    """

    data: SurveyData
    loadings: ResultTable
    variance: ResultTable
    correlations: ResultTable
    stats: dict[str, Any]
    solution: FactorSolution
    scores: list[str] = field(default_factory=list)


# ── on survey data ───────────────────────────────────────────────────────────


def analyze(
    data: SurveyData,
    items: list[str],
    *,
    n_factors: int | None = None,
    criterion: str = "kaiser",
    method: str = "minres",
    rotation: str = "varimax",
    sort: bool = False,
    hide_below: float = 0.0,
    scores: bool = False,
    into: str = "factor_",
    seed: int = 42,
    read_later: Iterable[str] = (),
) -> FactorAnalysis:
    """Exploratory factor analysis of ``items`` — the ``analyze.factor`` node.

    ``n_factors`` fixes the number of factors; left empty, ``criterion``
    (``kaiser`` or ``parallel``, drawn from ``seed``) chooses it. ``sort``
    orders the items by the factor they load on most, then by that loading;
    ``hide_below`` blanks loadings smaller in absolute value in the table.
    ``scores`` adds ``<into>1`` … ``<into>m`` to the data (``into`` empty:
    ``factor_``): regression-method scores, missing for respondents left out.

    ``read_later`` names the score variables a later step reads — a flow
    passes the ones the nodes downstream name. With the number of factors
    chosen by a rule, one of those the rule did not keep is added empty and
    labelled why (``Factor 3 score (not made: the Kaiser criterion kept 2
    factors)``), so the step finds a variable that says what happened rather
    than a KeyError; no other score is added.
    """

    items = list(items or [])
    distinct(items)
    into = str(into or "").strip() or "factor_"  # a cleared field is the default
    rows = listwise(data, items)
    solution = fit(
        rows.frame[items].to_numpy(),
        n_factors=n_factors,
        criterion=criterion,
        method=method,
        rotation=rotation,
        seed=seed,
        names=[label_of(data, item) for item in items],
    )
    m = solution.n_factors
    names = [f"Factor {j}" for j in range(1, m + 1)]

    stats: dict[str, Any] = {
        "Extraction": EXTRACTION_NAMES[method],
        "Rotation": ROTATION_NAMES[rotation] if m > 1 else "none (one factor)",
        "Factors": m,
        "Factors chosen by": _criterion_text(solution.criterion, seed),
        "Items": len(items),
        "N": rows.n,
        "Variance explained %": rounded(solution.communalities.sum() / len(items) * 100, 1),
        "KMO": rounded(solution.kmo, 3),
        "Bartlett chi-square": rounded(solution.bartlett[0], 3),
        "Bartlett df": solution.bartlett[1],
        "Bartlett p": p_rounded(solution.bartlett[2]),
        "RMSR": rounded(solution.rmsr, 4),
    }
    if solution.fit is not None:
        stats["Fit chi-square"] = rounded(solution.fit[0], 3)
        stats["Fit df"] = solution.fit[1]
        if solution.fit[2] is not None:
            stats["Fit p"] = p_rounded(solution.fit[2])
    if method == "principal":
        stats["Iterations"] = solution.iterations
    if solution.warnings:
        stats["Warning"] = "; ".join(solution.warnings)

    created: list[str] = []
    result_data = data
    if scores:
        values = solution.scores(rows.frame[items].to_numpy())
        detail = method if m == 1 or rotation == "none" else f"{method}, {rotation} rotation"
        for j in range(m):
            name = f"{into}{j + 1}"
            # By position, not by label: a repeated index label would put one
            # respondent's score on every row that shares it.
            placed = np.full(len(data.frame), np.nan)
            placed[rows.mask] = values[:, j]
            series = pd.Series(placed, index=data.frame.index, dtype=float)
            result_data = result_data.with_derived(
                name,
                series,
                label=f"Factor {j + 1} score ({detail})",
                scale="interval",
            )
            created.append(name)
        stats["Scores"] = f"{', '.join(created)} (regression method)"
        if n_factors is None:
            # Chosen by a rule, the number of factors is known only after the
            # run, so check_flow lets a later node name every score the analysis
            # could make (one fewer than the items). One of those a later node
            # reads that the rule did not keep is made too, empty, and says why
            # — a node reading factor_2 after the rule kept one finds an empty
            # variable labelled so, not a KeyError. Only those: every other
            # would be an empty column in the data, its exports and its tables.
            rule = "the Kaiser criterion" if solution.criterion == "kaiser" else "parallel analysis"
            kept = f"{rule} kept {m} {'factor' if m == 1 else 'factors'}"
            wanted = set(read_later)
            empty = []
            for j in range(m + 1, len(items)):
                name = f"{into}{j}"
                if name not in wanted:
                    continue
                result_data = result_data.with_derived(
                    name,
                    pd.Series(np.nan, index=data.frame.index, dtype=float),
                    label=f"Factor {j} score (not made: {kept})",
                    scale="interval",
                )
                empty.append(name)
            if empty:
                stats["Scores"] += f"; {', '.join(empty)} empty: {kept}"
    rows.report(stats, "any of the items")
    unweighted(stats, data)

    loadings = _loadings_frame(data, items, solution, names, sort=sort, hide_below=hide_below)
    variance = _variance_frame(solution)
    correlations = pd.DataFrame(solution.phi.round(3), columns=names)
    correlations.insert(0, "Factor", names)
    correlation_footer: dict[str, Any] = {"Rotation": stats["Rotation"]}
    if not solution.oblique or m == 1:
        correlation_footer["Note"] = (
            "an orthogonal solution: the factors are uncorrelated by construction"
        )
    variance_footer: dict[str, Any] = {"Extraction": stats["Extraction"], "N": rows.n}
    if solution.oblique and m > 1:
        variance_footer["Note"] = (
            "after an oblique rotation the factors correlate, so their variances overlap "
            "and are not added up"
        )
    # Each output may stand alone in a report, so each says it is unweighted.
    unweighted(variance_footer, data)
    unweighted(correlation_footer, data)
    return FactorAnalysis(
        data=result_data,
        loadings=result_table(data, loadings, stats),
        variance=result_table(data, variance, variance_footer),
        correlations=result_table(data, correlations, correlation_footer),
        stats=stats,
        solution=solution,
        scores=created,
    )


def _criterion_text(criterion: str, seed: int) -> str:
    if criterion == "kaiser":
        return "Kaiser criterion (eigenvalues above 1)"
    if criterion == "parallel":
        return (
            f"parallel analysis ({PARALLEL_PERCENTILE}th percentile of "
            f"{PARALLEL_ITERATIONS} random data sets, seed {seed})"
        )
    return "fixed"


def _loadings_frame(
    data: SurveyData,
    items: list[str],
    solution: FactorSolution,
    names: list[str],
    *,
    sort: bool,
    hide_below: float,
) -> pd.DataFrame:
    frame = pd.DataFrame(solution.loadings.round(3), columns=names)
    if hide_below and hide_below > 0:
        frame = frame.mask(frame.abs() < hide_below)
    frame.insert(0, "Variable", items)
    frame.insert(1, "Label", [label_of(data, item) for item in items])
    frame["Communality"] = solution.communalities.round(3)
    frame["Uniqueness"] = solution.uniquenesses.round(3)
    frame["MSA"] = solution.kmo_items.round(3)
    if sort:
        frame = frame.iloc[_sorted_order(solution.loadings)].reset_index(drop=True)
    return frame


def _sorted_order(loadings: np.ndarray) -> list[int]:
    """Items grouped by the factor they load on most, largest loading first
    (psych's ``fa.sort``)."""
    strongest = np.abs(loadings).argmax(axis=1)
    size = np.abs(loadings).max(axis=1)
    return sorted(range(len(loadings)), key=lambda i: (strongest[i], -size[i], i))


def _variance_frame(solution: FactorSolution) -> pd.DataFrame:
    p = len(solution.eigenvalues)
    m = solution.n_factors
    eigen = solution.eigenvalues
    frame = pd.DataFrame(
        {
            "Factor": [f"Factor {j}" for j in range(1, p + 1)],
            "Eigenvalue": eigen.round(3),
            "% of variance": (eigen / p * 100).round(2),
            "Cumulative %": (np.cumsum(eigen) / p * 100).round(2),
        }
    )
    blank = np.full(p - m, np.nan)

    def column(values: np.ndarray, digits: int) -> np.ndarray:
        return np.concatenate([np.round(values, digits), blank])

    extracted = (solution.unrotated**2).sum(axis=0)
    frame["Extracted SS"] = column(extracted, 3)
    frame["Extracted %"] = column(extracted / p * 100, 2)
    frame["Extracted cumulative %"] = column(np.cumsum(extracted) / p * 100, 2)
    if solution.rotation != "none" and m > 1:
        rotated = (solution.loadings**2).sum(axis=0)
        frame["Rotated SS"] = column(rotated, 3)
        if not solution.oblique:
            frame["Rotated %"] = column(rotated / p * 100, 2)
            frame["Rotated cumulative %"] = column(np.cumsum(rotated) / p * 100, 2)
    if solution.parallel is not None:
        frame[f"Random {PARALLEL_PERCENTILE}th percentile"] = solution.parallel.round(3)
    return frame


# ── the model ────────────────────────────────────────────────────────────────


def fit(
    matrix: Any,
    *,
    n_factors: int | None = None,
    criterion: str = "kaiser",
    method: str = "minres",
    rotation: str = "varimax",
    seed: int = 42,
    names: list[str] | None = None,
) -> FactorSolution:
    """Fit an exploratory factor model to ``matrix`` (respondents × items,
    complete rows). ``names`` are used in the messages."""

    from scipy.stats import chi2

    if method not in EXTRACTIONS:
        raise ValueError(f"method must be one of {', '.join(EXTRACTIONS)}.")
    if rotation not in ROTATIONS:
        raise ValueError(f"rotation must be one of {', '.join(ROTATIONS)}.")
    if n_factors is None and criterion not in CRITERIA:
        raise ValueError(f"criterion must be one of {', '.join(CRITERIA)}.")
    x = np.asarray(matrix, dtype=float)
    if x.ndim != 2:
        raise ValueError("fit() takes a respondents × items matrix.")
    n, p = x.shape
    names = list(names) if names is not None else [f"item {i + 1}" for i in range(p)]
    if p < 3:
        raise ValueError(
            f"A factor analysis needs at least three items; {p} "
            f"{'was' if p == 1 else 'were'} given."
        )
    if n <= p:
        raise ValueError(
            f"A factor analysis needs more respondents than items: {n} answered all "
            f"{p} items. With fewer the correlations cannot be estimated."
        )
    if np.isnan(x).any():
        raise ValueError("fit() takes complete rows; drop the missing values first.")
    sds = x.std(axis=0, ddof=1)
    flat = [names[i] for i in range(p) if no_spread(x[:, i])]
    if flat:
        raise ValueError(
            f"{', '.join(flat)} {'has' if len(flat) == 1 else 'have'} the same answer "
            "from every respondent, so there is nothing to correlate; leave "
            f"{'it' if len(flat) == 1 else 'them'} out."
        )
    correlation = np.corrcoef(x, rowvar=False)
    eigenvalues, eigenvectors = np.linalg.eigh(correlation)
    if eigenvalues[0] < 1e-8:
        raise ValueError(_singular_message(correlation, eigenvectors[:, 0], names))
    eigenvalues = eigenvalues[::-1]

    kmo, kmo_items = _kmo(correlation)
    _, logdet = np.linalg.slogdet(correlation)
    bartlett_stat = float(-(n - 1 - (2 * p + 5) / 6) * logdet)
    bartlett_df = p * (p - 1) // 2
    bartlett = (bartlett_stat, bartlett_df, float(chi2.sf(bartlett_stat, bartlett_df)))

    warnings: list[str] = []
    most = p - 1
    if method == "ml":
        most = max(m for m in range(1, p) if _dof(p, m) >= 0 or m == 1)
    parallel = None
    if n_factors is not None:
        m = int(n_factors)
        chosen = "fixed"
        if m < 1:
            raise ValueError("The number of factors must be at least 1.")
        if m > most:
            if m >= p:
                raise ValueError(
                    f"{m} factors for {p} items is as many factors as items; a factor "
                    f"analysis explains items by fewer factors (at most {most} here)."
                )
            raise ValueError(
                f"Maximum likelihood cannot fit {m} factors to {p} items: the model would "
                f"have more parameters than the correlations it explains. Use at most {most}."
            )
    else:
        chosen = criterion
        if criterion == "kaiser":
            m = int((eigenvalues > 1).sum())
        else:
            parallel = _parallel(n, p, seed)
            exceeds = eigenvalues > parallel
            m = int(np.argmin(exceeds)) if not exceeds.all() else p
        m = max(1, m)
        if m > most:
            warnings.append(
                f"the {criterion} rule suggests {m} factors; {most} is the most "
                f"{'maximum likelihood can fit' if method == 'ml' else 'the items allow'}"
            )
            m = most
    if _dof(p, m) < 0 and method != "ml":
        warnings.append(
            f"{m} factors have more parameters than {p} items' correlations can "
            "identify (negative degrees of freedom); the solution is not unique"
        )

    iterations, converged = 0, True
    fit_test = None
    if method == "minres":
        unrotated, converged, iterations = _minres(correlation, m)
    elif method == "ml":
        unrotated, converged, iterations, objective, several = _ml(correlation, m)
        if several:
            warnings.append(
                "maximum likelihood reached different solutions from different starting "
                f"points; the best of {ML_RANDOM_STARTS + 4} is shown. That usually means more "
                "factors than the data carry: compare a solution with fewer"
            )
        dof = _dof(p, m)
        statistic = float((n - 1 - (2 * p + 5) / 6 - 2 * m / 3) * objective)
        fit_test = (statistic, dof, float(chi2.sf(statistic, dof)) if dof > 0 else None)
    else:
        unrotated, converged, iterations = _principal_axis(correlation, m)
    if not converged:
        warnings.append(f"the {EXTRACTION_NAMES[method]} fit did not converge")

    unrotated = _signed_and_ordered(unrotated)[0]
    communalities = (unrotated**2).sum(axis=1)
    heywood = [names[i] for i in range(p) if communalities[i] >= 1 - PSI_BOUNDS[0] - 1e-6]
    if heywood:
        warnings.append(
            f"Heywood case: {', '.join(heywood)} "
            f"{'has' if len(heywood) == 1 else 'have'} (almost) no uniqueness left, "
            "which usually means too many factors or an item that duplicates another"
        )
    if kmo < 0.5:
        warnings.append(
            f"KMO is {kmo:.2f}, below 0.5: the items share too little for a factor "
            "analysis to mean much"
        )

    phi = np.eye(m)
    loadings = unrotated
    if m > 1 and rotation == "varimax":
        loadings = _varimax(unrotated)[0]
    elif m > 1 and rotation == "promax":
        loadings, phi = _promax(unrotated)
    elif m > 1 and rotation == "oblimin":
        loadings, phi, rotated_ok = _oblimin(unrotated)
        if not rotated_ok:
            warnings.append("the oblimin rotation did not converge")
    loadings, phi = _signed_and_ordered(loadings, phi)

    residual = correlation - unrotated @ unrotated.T
    lower = residual[np.tril_indices(p, -1)]
    return FactorSolution(
        n=n,
        correlation=correlation,
        eigenvalues=eigenvalues,
        unrotated=unrotated,
        loadings=loadings,
        structure=loadings @ phi,
        phi=phi,
        communalities=communalities,
        kmo=kmo,
        kmo_items=kmo_items,
        bartlett=bartlett,
        method=method,
        rotation=rotation,
        criterion=chosen,
        parallel=parallel,
        rmsr=float(np.sqrt(np.mean(lower**2))),
        fit=fit_test,
        iterations=iterations,
        converged=converged,
        means=x.mean(axis=0),
        sds=sds,
        warnings=tuple(warnings),
    )


def _dof(p: int, m: int) -> int:
    return ((p - m) ** 2 - p - m) // 2


def _singular_message(correlation: np.ndarray, null: np.ndarray, names: list[str]) -> str:
    p = len(names)
    for i in range(p):
        for j in range(i + 1, p):
            if abs(correlation[i, j]) > 1 - 1e-9:
                return (
                    f"The items' correlation matrix is singular: {names[i]} and {names[j]} "
                    "are perfectly correlated (one is a copy or a recoding of the other). "
                    "Leave one of them out."
                )
    involved = [names[i] for i in np.argsort(-np.abs(null)) if abs(null[i]) > 0.05]
    return (
        "The items' correlation matrix is singular: one item is an exact combination of "
        f"others ({', '.join(involved)}) — a total or an average of them, say. Leave it out."
    )


def _kmo(correlation: np.ndarray) -> tuple[float, np.ndarray]:
    inverse = np.linalg.inv(correlation)
    scale = np.sqrt(np.diag(inverse))
    partial = -inverse / np.outer(scale, scale)
    r2 = correlation**2
    q2 = partial**2
    np.fill_diagonal(r2, 0.0)
    np.fill_diagonal(q2, 0.0)
    items = r2.sum(axis=0) / (r2.sum(axis=0) + q2.sum(axis=0))
    return float(r2.sum() / (r2.sum() + q2.sum())), items


def _parallel(n: int, p: int, seed: int) -> np.ndarray:
    # RandomState, not default_rng: NumPy guarantees its stream across versions,
    # so the same seed chooses the same number of factors on any install.
    rng = np.random.RandomState(seed)
    draws = np.empty((PARALLEL_ITERATIONS, p))
    for i in range(PARALLEL_ITERATIONS):
        sample = rng.standard_normal((n, p))
        draws[i] = np.linalg.eigvalsh(np.corrcoef(sample, rowvar=False))[::-1]
    return np.percentile(draws, PARALLEL_PERCENTILE, axis=0)


def _smc(correlation: np.ndarray) -> np.ndarray:
    return 1.0 - 1.0 / np.diag(np.linalg.inv(correlation))


def _top(matrix: np.ndarray, m: int) -> tuple[np.ndarray, np.ndarray]:
    values, vectors = np.linalg.eigh(matrix)
    return values[::-1], vectors[:, ::-1]


def _minres(correlation: np.ndarray, m: int) -> tuple[np.ndarray, bool, int]:
    from scipy.optimize import minimize

    tiny = np.finfo(float).eps * 100

    def objective(psi: np.ndarray) -> tuple[float, np.ndarray]:
        reduced = correlation - np.diag(psi)
        values, vectors = _top(reduced, m)
        loadings = vectors[:, :m] * np.sqrt(np.maximum(values[:m], tiny))
        residual = reduced - loadings @ loadings.T
        return float((residual**2).sum()), -2.0 * np.diag(residual)

    start = np.clip(1.0 - _smc(correlation), *PSI_BOUNDS)
    result = minimize(
        objective,
        start,
        jac=True,
        method="L-BFGS-B",
        bounds=[PSI_BOUNDS] * len(start),
        options={"maxiter": 1000, "ftol": 1e-14, "gtol": 1e-10},
    )
    values, vectors = _top(correlation - np.diag(result.x), m)
    loadings = vectors[:, :m] * np.sqrt(np.maximum(values[:m], 0.0))
    return loadings, _converged(result, objective), int(result.nit)


def _ml(correlation: np.ndarray, m: int) -> tuple[np.ndarray, bool, int, float, bool]:
    """Maximum likelihood, ``factanal``'s objective, from several starts.

    A single start — ``factanal``'s — can stop at a local optimum when the
    model has more factors than the data carry (1 in 6 simulated data sets for
    three factors on two), and its test of fit is then computed on the wrong
    solution. So the fit also starts from the minres solution, from 1 − SMC,
    from 0.5 and from :data:`ML_RANDOM_STARTS` uniform points drawn from
    :data:`ML_SEED`, and keeps the lowest objective: the same data always
    gives the same solution. The last value returned says whether converged
    starts ended at different optima.
    """

    from scipy.optimize import minimize

    p = len(correlation)

    def parts(psi: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        scale = 1.0 / np.sqrt(psi)
        return _top(correlation * np.outer(scale, scale), m)

    def objective(psi: np.ndarray) -> tuple[float, np.ndarray]:
        values, vectors = parts(psi)
        rest = values[m:]
        value = -(float(np.sum(np.log(rest) - rest)) - m + p)
        loadings = np.sqrt(psi)[:, None] * (
            vectors[:, :m] * np.sqrt(np.maximum(values[:m] - 1.0, 0.0))
        )
        gradient = np.diag(loadings @ loadings.T + np.diag(psi) - correlation) / psi**2
        return value, gradient

    minres = _minres(correlation, m)[0]
    # RandomState, as in _parallel: its stream is the same on every NumPy.
    random = np.random.RandomState(ML_SEED).uniform(0.05, 0.95, (ML_RANDOM_STARTS, p))
    starts = [
        (1.0 - 0.5 * m / p) / np.diag(np.linalg.inv(correlation)),  # factanal's
        1.0 - (minres**2).sum(axis=1),
        1.0 - _smc(correlation),
        np.full(p, 0.5),
        *random,
    ]
    best, optima = None, []
    for start in starts:
        result = minimize(
            objective,
            np.clip(start, *PSI_BOUNDS),
            jac=True,
            method="L-BFGS-B",
            bounds=[PSI_BOUNDS] * p,
            options={"maxiter": 1000, "ftol": 1e-14, "gtol": 1e-10},
        )
        converged = _converged(result, objective)
        if converged:
            optima.append(float(result.fun))
        # A start must do clearly better to replace an earlier one, so where
        # they reach the same optimum the solution is factanal's own.
        if (
            best is None
            or (converged and not best[1])
            or (converged == best[1] and result.fun < best[0].fun - 1e-10)
        ):
            best = (result, converged)
    result, converged = best
    values, vectors = parts(result.x)
    loadings = np.sqrt(result.x)[:, None] * (
        vectors[:, :m] * np.sqrt(np.maximum(values[:m] - 1.0, 0.0))
    )
    several = bool(optima) and max(optima) - min(optima) > 1e-6 * max(1.0, min(optima))
    return loadings, converged, int(result.nit), float(result.fun), several


def _converged(result: Any, objective: Any) -> bool:
    """L-BFGS-B stops "abnormally" when a line search cannot improve on a point
    that is already optimal; what matters is the projected gradient there."""
    if result.success:
        return True
    _, gradient = objective(result.x)
    low, high = PSI_BOUNDS
    free = ~(
        ((result.x <= low + 1e-9) & (gradient > 0)) | ((result.x >= high - 1e-9) & (gradient < 0))
    )
    return bool(np.all(np.abs(gradient[free]) < 1e-5))


def _principal_axis(correlation: np.ndarray, m: int) -> tuple[np.ndarray, bool, int]:
    """psych's ``fm="pa"``: SMC start, |Δ Σ communalities| < 0.001, at most 50 steps."""
    reduced = correlation.copy()
    communality = float(np.trace(correlation))
    np.fill_diagonal(reduced, _smc(correlation))
    loadings = np.zeros((len(correlation), m))
    for step in range(1, 51):
        values, vectors = _top(reduced, m)
        loadings = vectors[:, :m] * np.sqrt(np.maximum(values[:m], 0.0))
        fitted = (loadings**2).sum(axis=1)
        change = abs(communality - float(fitted.sum()))
        communality = float(fitted.sum())
        np.fill_diagonal(reduced, fitted)
        if change <= 0.001:
            return loadings, True, step
    return loadings, False, 50


def _signed_and_ordered(
    loadings: np.ndarray, phi: np.ndarray | None = None
) -> tuple[np.ndarray, np.ndarray]:
    """Each factor signed so its loadings sum positive; factors ordered by the
    sum of their squared loadings, largest first; ``phi`` follows both."""
    m = loadings.shape[1]
    phi = np.eye(m) if phi is None else phi
    signs = np.sign(loadings.sum(axis=0))
    signs[signs == 0] = 1.0
    loadings = loadings * signs
    phi = phi * np.outer(signs, signs)
    order = np.argsort(-(loadings**2).sum(axis=0), kind="stable")
    return loadings[:, order], phi[np.ix_(order, order)]


def _varimax(
    loadings: np.ndarray, *, normalize: bool = True, eps: float = 1e-5
) -> tuple[np.ndarray, np.ndarray]:
    """R's ``stats::varimax``: SVD iterations until the criterion grows by
    less than a relative ``eps``."""
    p, m = loadings.shape
    x = loadings.copy()
    scale = np.ones(p)
    if normalize:
        scale = np.sqrt((x**2).sum(axis=1))
        scale[scale == 0] = 1.0
        x = x / scale[:, None]
    rotation = np.eye(m)
    criterion = 0.0
    for _ in range(1000):
        z = x @ rotation
        target = x.T @ (z**3 - z * (z**2).sum(axis=0) / p)
        u, s, vt = np.linalg.svd(target)
        rotation = u @ vt
        previous, criterion = criterion, float(s.sum())
        if criterion < previous * (1 + eps):
            break
    return (x @ rotation) * scale[:, None], rotation


def _promax(loadings: np.ndarray, power: int = PROMAX_POWER) -> tuple[np.ndarray, np.ndarray]:
    """Promax as factor_analyzer (and SPSS): Kaiser-normalized varimax, a target
    of the loadings raised to ``power`` keeping their sign, the least-squares
    transformation towards it, de-normalized."""
    scale = np.sqrt((loadings**2).sum(axis=1))
    scale[scale == 0] = 1.0
    normalized = loadings / scale[:, None]
    varimax, _ = _varimax(normalized, normalize=False)
    target = varimax * np.abs(varimax) ** (power - 1)
    transform = np.linalg.lstsq(varimax, target, rcond=None)[0]
    transform = transform @ np.diag(np.sqrt(np.diag(np.linalg.inv(transform.T @ transform))))
    rotated = (varimax @ transform) * scale[:, None]
    inverse = np.linalg.inv(transform)
    return rotated, inverse @ inverse.T


def _oblimin(
    loadings: np.ndarray, *, eps: float = 1e-5, max_iter: int = 1000
) -> tuple[np.ndarray, np.ndarray, bool]:
    """Direct quartimin by gradient projection — ``GPArotation::GPFoblq`` with
    ``vgQ.oblimin(gam = 0)``: the criterion is Σ over rows of the products of
    squared loadings on different factors, divided by 4."""
    m = loadings.shape[1]
    off = 1.0 - np.eye(m)

    def criterion(pattern: np.ndarray) -> tuple[float, np.ndarray]:
        cross = (pattern**2) @ off
        return float((pattern**2 * cross).sum() / 4), pattern * cross

    rotation = np.eye(m)
    pattern = loadings @ np.linalg.inv(rotation).T
    value, gradient_q = criterion(pattern)
    gradient = -(pattern.T @ gradient_q @ np.linalg.inv(rotation)).T
    step = 1.0
    converged = False
    for _ in range(max_iter + 1):
        projected = gradient - rotation @ np.diag((rotation * gradient).sum(axis=0))
        size = float(np.sqrt((projected**2).sum()))
        if size < eps:
            converged = True
            break
        step *= 2
        for _ in range(11):
            candidate = rotation - step * projected
            candidate = candidate / np.sqrt((candidate**2).sum(axis=0))
            new_pattern = loadings @ np.linalg.inv(candidate).T
            new_value, new_gradient_q = criterion(new_pattern)
            if value - new_value > 0.5 * size**2 * step:
                break
            step /= 2
        rotation, pattern, value = candidate, new_pattern, new_value
        gradient = -(pattern.T @ new_gradient_q @ np.linalg.inv(rotation)).T
    return pattern, rotation.T @ rotation, converged


__all__ = [
    "CRITERIA",
    "EXTRACTIONS",
    "ROTATIONS",
    "FactorAnalysis",
    "FactorSolution",
    "analyze",
    "fit",
]
