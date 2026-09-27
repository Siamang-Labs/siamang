"""Correspondence analysis: a perceptual map of a table of counts.

Which brands are seen as modern and which as cheap, which regions use which
channels: a table of counts says it cell by cell, and a correspondence analysis
(CA) draws it. Rows (brands) and columns (attributes) become points on a map
where a row lies toward the columns it has more of than the average row, and
the axes are the dimensions that carry most of the table's departure from
independence (its *inertia*, χ² / n).

:func:`analyze` builds the table from a :class:`~siamang.data.survey_data.SurveyData`
— the ``analyze.correspondence`` node (Perceptual map) — in one of two ways:

- **crosstab**: the respondents in each pair of answers of two variables
  (Region × Brand used). A multiple-choice variable counts each answer chosen,
  so a respondent can be in several cells;
- **attributes**: for each answer of the row variable (the brand, in data with
  a row per respondent and brand), the respondents who checked each of a set of
  0/1 attribute variables — the usual brand-image grid. ``yes`` names the codes
  that count as checked (empty: 1, for 0/1 variables); anything else — a blank,
  a missing code — counts as unchecked.

:func:`ca` runs the analysis on a plain table and :func:`plot` draws the map.

The computation is simple CA as Greenacre (2017) and R's ``ca::ca`` and
FactoMineR's ``CA`` do it. With ``P = N / n``, row masses ``r`` and column
masses ``c``, the standardized residuals ``S = D_r^{-½} (P − r cᵀ) D_c^{-½}``
have the singular value decomposition ``S = U Σ Vᵀ``:

- the **principal inertias** are ``σₖ²`` and sum to the total inertia χ²/n;
  there are at most ``min(rows, columns) − 1`` of them;
- **standard coordinates** ``Φ = D_r^{-½} U`` and ``Γ = D_c^{-½} V``;
  **principal coordinates** ``F = Φ Σ`` and ``G = Γ Σ`` — the map is
  *symmetric*: rows and columns both in principal coordinates, as ``ca``'s and
  FactoMineR's default plots;
- a row's **contribution** to dimension k is ``rᵢ φᵢₖ²`` (the rows' add up to
  100 % per dimension; ``ca`` prints them per mil, FactoMineR in %), its
  **cos²** ``fᵢₖ² / Σₖ fᵢₖ²`` (the share of its squared distance from the
  center along k; ``ca``'s "cor"), its **quality** the sum of the cos² of the
  dimensions shown, and its **inertia** ``rᵢ Σₖ fᵢₖ²`` as a share of the total;
  the same for the columns.

**Signs.** An SVD fixes each dimension up to its sign, and packages disagree:
on the ``smoke`` table ``ca::ca`` and FactoMineR mirror the second dimension of
each other. Here each dimension is signed so that the row contributing most to
it lies on its positive side; a map may therefore be a mirror image of another
package's, with every distance and every number but the signs the same.

**Weights.** With a weight, a cell holds the sum of the weights of its
respondents, so the map is that of the weighted table; the chi-square test of
independence (crosstab of single answers only) counts respondents, as a test
of a table must, and says so. In the attributes layout, and with a
multiple-choice variable, a respondent is in several cells, so there is no
chi-square test at all.

**Who is counted.** The codebook's missing codes are not answers: a respondent
whose row (or, in a crosstab, column) answer is blank or a missing code is left
out and counted, as the other methods chosen by hand do. A row or column that
nobody is in is left off the map and named.
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

from siamang.data import multi
from siamang.data.listwise import distinct, label_of, p_rounded, rounded
from siamang.reporting import chart_theme
from siamang.reporting.result_table import ResultTable

if TYPE_CHECKING:
    from siamang.data.survey_data import SurveyData

LAYOUTS = ("crosstab", "attributes")
#: The most dimensions the tables show.
MAX_DIMENSIONS = 10

#: The map's colors: rows and columns, a pair distinguishable with every
#: common color-vision deficiency; the labels are in ink.
ROW_COLOUR, COLUMN_COLOUR = "#2a78d6", "#eb6834"
_INK, _MUTED, _RULE = "#333333", "#767676", "#bdbdbd"


# These colors, or — in a Result chart of palette "theme" — the report
# theme's first two, its text, secondary text and grid.
def _rows() -> str:
    return chart_theme.series(ROW_COLOUR, 0)


def _columns() -> str:
    return chart_theme.series(COLUMN_COLOUR, 1)


def _ink() -> str:
    return chart_theme.text(_INK)


def _muted() -> str:
    return chart_theme.muted(_MUTED)


def _rule() -> str:
    return chart_theme.grid(_RULE)


@dataclass
class MapTable(ResultTable):
    """A table of a perceptual map; ``analysis`` is the whole result, which a chart draws."""

    analysis: PerceptualMap | None = None


@dataclass(frozen=True, slots=True)
class CorrespondenceSolution:
    """Simple correspondence analysis of a table of counts (:func:`ca`).

    Every matrix has one column per dimension (those with a positive inertia);
    coordinates are signed as the module's docstring says.
    """

    counts: np.ndarray
    row_masses: np.ndarray
    column_masses: np.ndarray
    singular_values: np.ndarray
    total_inertia: float
    row_standard: np.ndarray
    column_standard: np.ndarray
    row_principal: np.ndarray
    column_principal: np.ndarray
    row_contributions: np.ndarray  # shares (0–1) of each dimension's inertia
    column_contributions: np.ndarray
    row_cos2: np.ndarray
    column_cos2: np.ndarray
    row_inertia: np.ndarray  # shares (0–1) of the total inertia
    column_inertia: np.ndarray

    @property
    def inertias(self) -> np.ndarray:
        """The principal inertias (eigenvalues), largest first."""
        return self.singular_values**2

    @property
    def explained(self) -> np.ndarray:
        """Each dimension's share of the total inertia, in %."""
        if self.total_inertia <= 0:
            return np.zeros(len(self.singular_values))
        return self.inertias / self.total_inertia * 100

    @property
    def dimensions(self) -> int:
        return len(self.singular_values)


@dataclass(frozen=True, slots=True)
class PerceptualMap:
    """What :func:`analyze` found: the inertia table (with the statistics as its
    footer), the rows' and columns' tables, the statistics, and the numbers."""

    table: MapTable
    rows: MapTable
    columns: MapTable
    stats: dict[str, Any]
    solution: CorrespondenceSolution
    row_labels: list[str]
    column_labels: list[str]
    row_title: str
    column_title: str
    shown: int  # dimensions in the tables
    weight: str | None = None


# ── on a table ───────────────────────────────────────────────────────────────


def ca(table: Any) -> CorrespondenceSolution:
    """Simple correspondence analysis of ``table`` (rows × columns of counts,
    weighted or not). Rows and columns must each have a positive total."""

    n = np.asarray(table, dtype=float)
    if n.ndim != 2:
        raise ValueError("Correspondence analysis takes a two-way table.")
    if np.any(n < 0):
        raise ValueError("Correspondence analysis takes counts, which are not negative.")
    if n.shape[0] < 2 or n.shape[1] < 2:
        raise ValueError(
            "A perceptual map needs at least two rows and two columns with counts; "
            f"this table has {n.shape[0]} × {n.shape[1]}."
        )
    if np.any(n.sum(axis=1) <= 0) or np.any(n.sum(axis=0) <= 0):
        raise ValueError("Every row and column of the table needs a positive total.")
    p = n / n.sum()
    r, c = p.sum(axis=1), p.sum(axis=0)
    residuals = (p - np.outer(r, c)) / np.sqrt(np.outer(r, c))
    u, sigma, vt = np.linalg.svd(residuals, full_matrices=False)
    total = float((residuals**2).sum())
    limit = min(n.shape) - 1
    keep = int(np.sum(sigma[:limit] > 1e-12 * max(1.0, float(sigma[0]))))
    if keep == 0:
        raise ValueError(
            "Every row of the table has the same profile (the same shares across the "
            "columns), so there is nothing to map: the table is independent."
        )
    u, sigma, v = u[:, :keep], sigma[:keep], vt[:keep].T
    row_standard = u / np.sqrt(r)[:, None]
    column_standard = v / np.sqrt(c)[:, None]
    # Sign: the row contributing most to a dimension lies on its positive side.
    for k in range(keep):
        top = int(np.argmax(r * row_standard[:, k] ** 2))
        if row_standard[top, k] < 0:
            row_standard[:, k] *= -1
            column_standard[:, k] *= -1
    row_principal = row_standard * sigma
    column_principal = column_standard * sigma
    row_distance = (row_principal**2).sum(axis=1)
    column_distance = (column_principal**2).sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        row_cos2 = np.where(row_distance[:, None] > 0, row_principal**2 / row_distance[:, None], 0)
        column_cos2 = np.where(
            column_distance[:, None] > 0, column_principal**2 / column_distance[:, None], 0
        )
    return CorrespondenceSolution(
        counts=n,
        row_masses=r,
        column_masses=c,
        singular_values=sigma,
        total_inertia=total,
        row_standard=row_standard,
        column_standard=column_standard,
        row_principal=row_principal,
        column_principal=column_principal,
        row_contributions=r[:, None] * row_standard**2,
        column_contributions=c[:, None] * column_standard**2,
        row_cos2=row_cos2,
        column_cos2=column_cos2,
        row_inertia=r * row_distance / total,
        column_inertia=c * column_distance / total,
    )


# ── on survey data ───────────────────────────────────────────────────────────


def layout_problem(layout: str, attributes: list[str] | None) -> str | None:
    """Why the layout cannot be built from these parameters, or None — what
    :func:`analyze` raises and what ``check_flow`` says before a run."""

    if layout == "attributes" and attributes is not None and len(attributes) < 2:
        return (
            "A perceptual map of attributes needs two or more attribute variables; "
            f"{len(attributes)} {'was' if len(attributes) == 1 else 'were'} given."
        )
    return None


def analyze(
    data: SurveyData,
    row: str,
    *,
    column: str | None = None,
    attributes: list[str] | None = None,
    yes: Any = None,
    dimensions: int = 2,
) -> PerceptualMap:
    """Correspondence analysis of ``row`` by ``column`` (a crosstab) or by the
    ``attributes`` checked for each answer of ``row`` — the ``analyze.correspondence``
    node. Exactly one of ``column`` and ``attributes`` is given. ``dimensions``
    is how many dimensions the tables show (the map draws the first two).
    See the module's docstring."""

    if (column is None) == (attributes is None or attributes == []):
        raise ValueError(
            "A perceptual map crosses Rows with either Columns (a crosstab) or a set of "
            "Attributes — give one of them."
        )
    if not isinstance(dimensions, int) or isinstance(dimensions, bool) or dimensions < 1:
        raise ValueError("dimensions must be a whole number, 1 or more.")
    dimensions = min(dimensions, MAX_DIMENSIONS)
    layout = "crosstab" if column is not None else "attributes"
    frame = data.frame
    names = [row, column] if column is not None else [row, *list(attributes or [])]
    missing = [name for name in names if name not in frame.columns]
    if missing:
        raise KeyError(f"column not found: {', '.join(map(repr, missing))}")
    distinct(names)
    problem = layout_problem(layout, list(attributes) if attributes is not None else None)
    if problem:
        raise ValueError(problem)
    weights = _weights(data)
    left_out: dict[str, int] = {}
    met: list[str] = []
    row_codes, row_hits, row_answered = _indicators(data, row, left_out, met)
    row_names = [_code_label(data, row, code) for code in row_codes]
    row_title = label_of(data, row)
    stats: dict[str, Any] = {}
    if column is not None:
        column_codes, column_hits, column_answered = _indicators(data, column, left_out, met)
        answered = row_answered & column_answered
        column_names = [_code_label(data, column, code) for code in column_codes]
        column_title = label_of(data, column)
        several = multi.is_multi(frame[row]) or multi.is_multi(frame[column])
        excluded_because = "no answer (or a missing code) to Rows or Columns"
    else:
        answered = row_answered
        names = list(attributes or [])
        codes = _yes(data, names, yes, answered)
        column_hits = np.column_stack(
            [frame[name].isin(codes).to_numpy(dtype=bool) for name in names]
        )
        column_names = [label_of(data, name) for name in names]
        column_title = "Attributes"
        several = True
        excluded_because = "no answer (or a missing code) to Rows"
        stats["Counts as yes"] = _codes_text(data, names, codes)
    w = weights if weights is not None else np.ones(len(frame))
    counts = (row_hits[answered] * w[answered, None]).T @ column_hits[answered].astype(float)
    kept_rows = counts.sum(axis=1) > 0
    kept_columns = counts.sum(axis=0) > 0
    empty = [name for name, kept in zip(row_names, kept_rows, strict=True) if not kept]
    empty += [name for name, kept in zip(column_names, kept_columns, strict=True) if not kept]
    counts = counts[kept_rows][:, kept_columns]
    row_names = [name for name, kept in zip(row_names, kept_rows, strict=True) if kept]
    column_names = [name for name, kept in zip(column_names, kept_columns, strict=True) if kept]
    try:
        solution = ca(counts)
    except ValueError as exc:
        raise ValueError(f"{row_title} × {column_title}: {exc}") from exc

    shown = min(dimensions, solution.dimensions)
    n = int(answered.sum())
    stats = {
        "Map": f"{row_title} × {column_title}",
        "Rows": len(row_names),
        "Columns": len(column_names),
        "N": n,
        **stats,
        "Total inertia": rounded(solution.total_inertia, 4),
        "Dimensions": solution.dimensions,
    }
    for k in range(min(2, solution.dimensions)):
        stats[f"Dimension {k + 1} %"] = rounded(float(solution.explained[k]), 1)
    stats["Map %"] = rounded(float(solution.explained[: min(2, solution.dimensions)].sum()), 1)
    if solution.dimensions == 1:
        stats["Note"] = (
            "the table has one dimension (two rows or two columns), so the map is a line"
        )
    if layout == "crosstab" and not several:
        chi_square = _chi_square(row_hits, column_hits, answered, kept_rows, kept_columns)
        stats["Chi-square"] = rounded(chi_square[0], 3)
        stats["df"] = chi_square[1]
        stats["p"] = p_rounded(chi_square[2])
        if weights is not None:
            stats["Chi-square counts"] = "respondents (unweighted), as a test of a table must"
        if chi_square[3]:
            stats["Chi-square note"] = chi_square[3]
    elif layout == "crosstab":
        stats["Chi-square"] = (
            "not computed: with a multiple-choice variable a respondent can be in several cells"
        )
    if weights is not None:
        stats["Weight"] = data.weight
        stats["Weighted N"] = rounded(float(w[answered].sum()), 1)
    if empty:
        stats["Not in the map"] = f"{', '.join(empty)} (nobody counted in them)"
    excluded = int(len(frame) - n)
    stats["Excluded"] = excluded
    if excluded:
        stats["Excluded because"] = excluded_because
    if left_out:
        count = sum(left_out.values())
        answers = "answer" if count == 1 else "answers"
        stats["Missing codes"] = (
            f"{count} {answers} with a missing code ({', '.join(met)}) left out"
        )

    inertia = _inertia_frame(solution)
    footer = dict(stats)
    rows_frame = _points_frame(row_title, row_names, solution, "row", shown)
    columns_frame = _points_frame(column_title, column_names, solution, "column", shown)
    point_footer: dict[str, Any] = {
        "Coordinates": "principal (symmetric map)",
        "Contribution": "% of the dimension's inertia",
        "Quality": f"cos² of the {shown} dimension{'s' if shown > 1 else ''} shown",
    }
    if weights is not None:
        point_footer["Weight"] = data.weight
    result_tables = (
        MapTable(data=data, frame=inertia, footer=footer),
        MapTable(data=data, frame=rows_frame, footer=dict(point_footer)),
        MapTable(data=data, frame=columns_frame, footer=dict(point_footer)),
    )
    result = PerceptualMap(
        table=result_tables[0],
        rows=result_tables[1],
        columns=result_tables[2],
        stats=stats,
        solution=solution,
        row_labels=row_names,
        column_labels=column_names,
        row_title=row_title,
        column_title=column_title,
        shown=shown,
        weight=data.weight,
    )
    for table in result_tables:
        table.analysis = result
    return result


def _weights(data: SurveyData) -> np.ndarray | None:
    if data.weight is None:
        return None
    if data.weight not in data.frame.columns:
        raise KeyError(f"column not found: {data.weight!r}")
    values = pd.to_numeric(data.frame[data.weight], errors="coerce").fillna(0.0)
    values = values.to_numpy(dtype=float)
    if np.any(values < 0):
        raise ValueError(f"The weight column {data.weight!r} has negative values.")
    return values


def _code(value: Any) -> Any:
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, np.integer):
        return int(value)
    return value


def _sorted(codes: set[Any]) -> list[Any]:
    return sorted(codes, key=lambda value: (str(type(value)), value))


def _indicators(
    data: SurveyData, name: str, left_out: dict[str, int], met: list[str]
) -> tuple[list[Any], np.ndarray, np.ndarray]:
    """The answers of ``name`` as indicators (respondents × codes), who answered,
    and the missing codes met (added to ``left_out`` and ``met``)."""

    series = data.frame[name]
    variable = (
        data.variables[name] if data.variables is not None and name in data.variables else None
    )
    missing = set(variable.missing_values) if variable is not None else set()
    missing_labels = variable.missing_labels if variable is not None else {}

    def drop(code: Any) -> bool:
        if _code(code) in missing:
            text = f"{_code(code)} = {missing_labels.get(_code(code), '')}".rstrip(" =")
            if text not in met:
                met.append(text)
            left_out[name] = left_out.get(name, 0) + 1
            return True
        return False

    def missing_value(value: Any) -> bool:
        # Any scalar NA: None, NaN, and the pd.NA of the nullable Int64 columns
        # a snapshot or the platform's data gives back for a skipped answer.
        return value is None or (pd.api.types.is_scalar(value) and bool(pd.isna(value)))

    if multi.is_multi(series):
        answers = []
        for value in series:
            chosen = value if isinstance(value, list | tuple | set) else [value]
            answers.append(
                [_code(code) for code in chosen if not missing_value(code) and not drop(code)]
            )
        codes = _sorted({code for answer in answers for code in answer})
        hits = np.zeros((len(series), len(codes)), dtype=bool)
        index = {code: j for j, code in enumerate(codes)}
        for i, answer in enumerate(answers):
            for code in answer:
                hits[i, index[code]] = True
        return codes, hits, hits.any(axis=1)
    values = [None if missing_value(value) else _code(value) for value in series]
    values = [None if value is not None and drop(value) else value for value in values]
    codes = _sorted({value for value in values if value is not None})
    index = {code: j for j, code in enumerate(codes)}
    hits = np.zeros((len(series), len(codes)), dtype=bool)
    for i, value in enumerate(values):
        if value is not None:
            hits[i, index[value]] = True
    return codes, hits, np.array([value is not None for value in values], dtype=bool)


def _code_label(data: SurveyData, name: str, code: Any) -> str:
    if data.variables is not None and name in data.variables:
        labels = data.variables[name].labels or {}
        if code in labels:
            return str(labels[code])
    return str(code)


def _yes(data: SurveyData, attributes: list[str], yes: Any, answered: np.ndarray) -> list[Any]:
    """The codes that count as checked; empty is 1 for 0/1 attributes."""
    if yes is not None and yes != [] and yes != "":
        return list(yes) if isinstance(yes, list | tuple | set) else [yes]
    listed = [name for name in attributes if multi.is_multi(data.frame[name])]
    if listed:
        raise TypeError(
            f"{', '.join(listed)} {'holds' if len(listed) == 1 else 'hold'} multiple-choice "
            "answers (lists of codes); an attribute is one 0/1 variable. Run "
            "prepare.explode first, or use the crosstab layout with the list as Columns."
        )
    values: set[Any] = set()
    for name in attributes:
        values.update(_code(value) for value in data.frame[name][answered].dropna().tolist())
    if values <= {0, 1}:
        return [1]
    shown = ", ".join(str(value) for value in _sorted(values)[:8])
    raise ValueError(
        f"The attributes hold {shown}: name the code (or codes) that counts as checking an "
        "attribute in Counts as yes — `yes` outside a flow."
    )


def _codes_text(data: SurveyData, names: list[str], codes: list[Any]) -> str:
    texts = []
    for code in codes:
        label = next(
            (
                str(data.variables[name].labels[code])
                for name in names
                if data.variables is not None
                and name in data.variables
                and code in (data.variables[name].labels or {})
            ),
            None,
        )
        texts.append(f"{code} = {label}" if label else str(code))
    return ", ".join(texts)


def _chi_square(
    row_hits: np.ndarray,
    column_hits: np.ndarray,
    answered: np.ndarray,
    kept_rows: np.ndarray,
    kept_columns: np.ndarray,
) -> tuple[float, int, float, str | None]:
    """Pearson's chi-square of independence on the respondents' counts."""
    from scipy.stats import chi2

    counts = row_hits[answered].astype(float).T @ column_hits[answered].astype(float)
    counts = counts[kept_rows][:, kept_columns]
    counts = counts[counts.sum(axis=1) > 0][:, counts.sum(axis=0) > 0]
    total = counts.sum()
    expected = np.outer(counts.sum(axis=1), counts.sum(axis=0)) / total
    statistic = float(((counts - expected) ** 2 / expected).sum())
    df = (counts.shape[0] - 1) * (counts.shape[1] - 1)
    small = int((expected < 5).sum())
    note = (
        f"{small} of the {expected.size} cells expect fewer than 5 respondents, so the "
        "p-value is only approximate"
        if small
        else None
    )
    return statistic, df, float(chi2.sf(statistic, df)) if df > 0 else float("nan"), note


def _inertia_frame(solution: CorrespondenceSolution) -> pd.DataFrame:
    explained = solution.explained
    return pd.DataFrame(
        {
            "Dimension": np.arange(1, solution.dimensions + 1),
            "Singular value": [rounded(value, 4) for value in solution.singular_values],
            "Principal inertia": [rounded(value, 5) for value in solution.inertias],
            "% of inertia": [rounded(value, 1) for value in explained],
            "Cumulative %": [rounded(value, 1) for value in np.cumsum(explained)],
        }
    )


def _points_frame(
    title: str, names: list[str], solution: CorrespondenceSolution, side: str, shown: int
) -> pd.DataFrame:
    principal = solution.row_principal if side == "row" else solution.column_principal
    masses = solution.row_masses if side == "row" else solution.column_masses
    contributions = solution.row_contributions if side == "row" else solution.column_contributions
    cos2 = solution.row_cos2 if side == "row" else solution.column_cos2
    inertia = solution.row_inertia if side == "row" else solution.column_inertia
    frame: dict[str, Any] = {
        title: names,
        "Mass": [rounded(value, 3) for value in masses],
        "Quality": [rounded(value, 3) for value in cos2[:, :shown].sum(axis=1)],
        "Inertia %": [rounded(value * 100, 1) for value in inertia],
    }
    for k in range(shown):
        frame[f"Dim {k + 1}"] = [rounded(value, 3) for value in principal[:, k]]
        frame[f"Contribution {k + 1} %"] = [
            rounded(value * 100, 1) for value in contributions[:, k]
        ]
        frame[f"cos² {k + 1}"] = [rounded(value, 3) for value in cos2[:, k]]
    return pd.DataFrame(frame)


# ── the map ──────────────────────────────────────────────────────────────────


def plot(
    result: PerceptualMap,
    *,
    dimensions: tuple[int, int] = (1, 2),
    title: str | None = None,
    figsize: tuple[float, float] | None = None,
    ax: Any = None,
    numbered: bool | None = None,
) -> Any:
    """The symmetric map of ``result`` on two of its dimensions (default the
    first two): rows as blue circles, columns as orange triangles, each
    labeled in ink beside its point where the label overlaps nothing — or, when
    every spot beside it is taken, a little further out with a line back to it.
    The axes keep one scale (a unit is as long across as up), cross at the
    center (the average profile) and say how much of the inertia each carries.
    A table of one dimension is drawn on a line.

    A map too crowded for its names to lie apart (``numbered=None``, the
    default: when two names would overlap; ``True``: always) numbers its
    points instead — rows 1, 2, …, then the columns — and lists the numbers
    with the names under the map, the figure growing taller for the list.
    Returns the matplotlib Figure.
    """

    from matplotlib.figure import Figure
    from matplotlib.lines import Line2D

    solution = result.solution
    first, second = dimensions
    if first < 1 or second < 1 or first == second:
        raise ValueError("dimensions are two different dimension numbers, from 1.")
    top = solution.dimensions
    if max(first, second) > max(top, 2) or (top == 1 and min(first, second) > 1):
        raise ValueError(f"The map has {top} dimension{'s' if top > 1 else ''}.")

    def coordinate(matrix: np.ndarray, k: int) -> np.ndarray:
        return matrix[:, k - 1] if k <= top else np.zeros(len(matrix))

    rows_xy = np.column_stack(
        [coordinate(solution.row_principal, first), coordinate(solution.row_principal, second)]
    )
    columns_xy = np.column_stack(
        [
            coordinate(solution.column_principal, first),
            coordinate(solution.column_principal, second),
        ]
    )
    width, height = figsize if figsize else (10.0, 8.0)
    if ax is None:
        fig = Figure(figsize=(width, height))
        ax = fig.add_subplot(1, 1, 1)
    else:
        fig = ax.figure
    count = len(rows_xy) + len(columns_xy)
    # The labels' size follows how many share each square inch of the figure.
    density = count / (width * height)
    size = 10.0 if density <= 0.45 else 9.0 if density <= 0.65 else 8.0 if density <= 1.0 else 7.0
    ax.axhline(0, color=_rule(), linewidth=0.8, zorder=1)
    ax.axvline(0, color=_rule(), linewidth=0.8, zorder=1)
    ax.scatter(
        rows_xy[:, 0], rows_xy[:, 1], s=46, marker="o", color=_rows(),
        edgecolor="white", linewidth=1.2, zorder=3,
    )  # fmt: skip
    ax.scatter(
        columns_xy[:, 0], columns_xy[:, 1], s=56, marker="^", color=_columns(),
        edgecolor="white", linewidth=1.2, zorder=3,
    )  # fmt: skip
    points = np.vstack([rows_xy, columns_xy])
    # The limits follow the points with a margin, and one scale on both axes
    # stretches the shorter to the box: fixed limits would fight the aspect.
    ax.margins(0.15)
    ax.set_aspect("equal", adjustable="datalim")

    def axis_title(k: int) -> str:
        if k > top:
            return f"Dimension {k} (none: the table has {top})"
        return f"Dimension {k} ({solution.explained[k - 1]:.1f} % of inertia)"

    ax.set_xlabel(axis_title(first), fontsize=size + 1, color=_ink())
    ax.set_ylabel(axis_title(second), fontsize=size + 1, color=_ink())
    ax.tick_params(labelsize=size - 1, colors=_muted())
    for side in ax.spines.values():
        side.set_color(_rule())
    ax.grid(False)
    legend = ax.legend(
        handles=[
            Line2D([], [], marker="o", linestyle="", color=_rows(), markersize=7,
                   label=textwrap.fill(str(result.row_title), 40)),
            Line2D([], [], marker="^", linestyle="", color=_columns(), markersize=8,
                   label=textwrap.fill(str(result.column_title), 40)),
        ],
        loc="upper left", bbox_to_anchor=(0.0, -0.1), ncol=2, frameon=False, fontsize=size,
    )  # fmt: skip
    heading = title or f"Perceptual map: {result.row_title} × {result.column_title}"
    shown = solution.explained[[k - 1 for k in (first, second) if k <= top]].sum()
    # The title starts at the axes, which leave the figure's left for the ticks.
    characters = max(int(width * 0.85 * 72 / (12 * 0.55)), 30)
    lines = [
        textwrap.fill(heading, characters),
        textwrap.fill(
            f"Correspondence analysis, symmetric map — {shown:.1f} % of the inertia shown"
            + (f", N = {result.stats['N']}" if result.stats.get("N") else ""),
            characters,
        ),
    ]
    if result.weight:
        lines.append(f"weighted by '{result.weight}'")
    ax.set_title("\n".join(lines), fontsize=12, color=_ink(), loc="left", pad=10)
    fig.tight_layout()
    _under_the_axis(fig, ax, legend)
    # A long label wraps onto a second line (then ends in an ellipsis), the
    # narrower the figure the shorter the line: less room, narrower labels.
    limit = max(int(width * 3.0), 16)
    names = [*result.row_labels, *result.column_labels]
    masses = np.concatenate([solution.row_masses, solution.column_masses])
    if not numbered:
        _place_labels(ax, points, [_lines(name, limit) for name in names], masses, size)
        if numbered is False or not _crowded(ax):
            return fig
        for text in list(ax.texts):
            text.remove()
    _key(fig, result, size)
    numbers = [str(number) for number in range(1, count + 1)]
    # A number is small: it may go further out, near another point, with a
    # line back, rather than on another number.
    _place_labels(ax, points, numbers, masses, max(size - 1, 7), clash=25.0)
    return fig


def _under_the_axis(fig: Any, ax: Any, legend: Any) -> None:
    """Hang the legend under the x axis's numbers and title, a fixed distance
    in inches below the plot: at a tenth of the plot's height (as it was) it
    sat on the axis title of a short map."""
    from matplotlib.transforms import ScaledTranslation

    if not hasattr(fig.canvas, "get_renderer"):
        from matplotlib.backends.backend_agg import FigureCanvasAgg

        FigureCanvasAgg(fig)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    drop = ax.get_window_extent(renderer).y0 - ax.xaxis.get_tightbbox(renderer).y0
    shift = ScaledTranslation(0, -(drop / fig.dpi + 4 / 72), fig.dpi_scale_trans)
    legend.set_bbox_to_anchor((0.0, 0.0), transform=ax.transAxes + shift)
    fig.tight_layout()


def _crowded(ax: Any) -> bool:
    """Whether two labels on ``ax`` overlap by more than a point across and up
    (the texts, not their leader lines)."""
    from matplotlib.text import Text

    fig = ax.figure
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    boxes = np.array([Text.get_window_extent(text, renderer).extents for text in ax.texts])
    if len(boxes) < 2:
        return False
    across = np.minimum(boxes[:, None, 2], boxes[None, :, 2]) - np.maximum(
        boxes[:, None, 0], boxes[None, :, 0]
    )
    up = np.minimum(boxes[:, None, 3], boxes[None, :, 3]) - np.maximum(
        boxes[:, None, 1], boxes[None, :, 1]
    )
    point = fig.dpi / 72
    clash = (across > point) & (up > point)
    np.fill_diagonal(clash, False)
    return bool(clash.any())


def _key(fig: Any, result: PerceptualMap, size: float) -> None:
    """The numbered points' names, under the legend: each variable's under its
    title, in as many columns as the figure's width holds, the figure growing
    taller by the list's height and the map keeping its own."""

    width = fig.get_figwidth() * 72
    rows, columns = list(result.row_labels), list(result.column_labels)
    entries = [f"{i}  {name}" for i, name in enumerate([*rows, *columns], 1)]
    column_pt = min(max(len(entry) for entry in entries) * size * 0.6 + 16, width - 20)
    if len(entries) > 10:  # a long list in two columns at least, names wrapped
        column_pt = min(column_pt, (width - 20) / 2)
    count = max(1, int((width - 20) // column_pt))
    chars = max(int(column_pt / (size * 0.6)), 12)
    blocks = []
    for title, part in (
        (result.row_title, entries[: len(rows)]),
        (result.column_title, entries[len(rows) :]),
    ):
        per = -(-len(part) // count)
        cells = [
            "\n".join(
                textwrap.fill(entry, chars, subsequent_indent="    ")
                for entry in part[k * per : (k + 1) * per]
            )
            for k in range(count)
        ]
        blocks.append((str(title), cells))
    line = size * 1.3
    heights = [
        max(cell.count("\n") + 1 for cell in cells if cell) * line + line * 1.6
        for _, cells in blocks
    ]
    needed = sum(heights) + 8
    old = fig.get_figheight() * 72
    fig.set_figheight((old + needed) / 72)
    total = fig.get_figheight() * 72
    fig.tight_layout(rect=(0, needed / total, 1, 1))
    y = needed - 4
    for (title, cells), height in zip(blocks, heights, strict=True):
        fig.text(0.012, y / total, title, fontsize=size, color=_ink(), weight="bold", va="top")
        for k, cell in enumerate(cells):
            fig.text(
                (10 + k * column_pt) / width,
                (y - line * 1.4) / total,
                cell,
                fontsize=size - 0.5,
                color=_ink(),
                va="top",
                linespacing=1.3,
            )
        y -= height
    fig.canvas.draw()


def _lines(text: str, width: int, most: int = 2) -> str:
    """``text`` wrapped at ``width`` characters, at most ``most`` lines."""
    lines = textwrap.wrap(str(text), width) or [""]
    if len(lines) > most:
        lines = lines[:most]
        lines[-1] = lines[-1][: max(width - 1, 1)].rstrip() + "…"
    return "\n".join(lines)


#: Where a label may sit around its point, in order of preference — right,
#: above-right, below-right, above, below, left, above-left, below-left, and
#: the eight between them — and how far out, in steps of the marker's size.
_SPOTS = (
    (1, 0), (1, 1), (1, -1), (0, 1), (0, -1), (-1, 0), (-1, 1), (-1, -1),
    (1, 0.5), (1, -0.5), (-1, 0.5), (-1, -0.5), (0.5, 1), (-0.5, 1), (0.5, -1), (-0.5, -1),
)  # fmt: skip
_REACHES = (1.0, 2.2, 3.4, 4.6, 5.8, 7.0)
#: Rounds of moving a label to a better spot once all are placed.
_ROUNDS = 12
#: The share of the plot the labels may cover before their font shrinks.
_CROWDED = 0.2
#: A label outside the axes runs into the tick labels and the axis title:
#: each pixel outside costs as much as this many pixels of overlap.
_OUTSIDE = 4.0


def _place_labels(
    ax: Any,
    points: np.ndarray,
    labels: list[str],
    masses: np.ndarray,
    size: float,
    clash: float = 1.0,
) -> None:
    """Label each point where its text overlaps no other label and no point,
    stays inside the axes, and lies nearer its own point than any other.

    Each label may take one of 96 spots: the sixteen directions of
    :data:`_SPOTS` at the distances of :data:`_REACHES` (beyond the first with
    a thin line back to the point). The labels are placed greedily, heaviest
    point first, each in the first spot free of all four problems or else the
    one where they add up least; then, for a few rounds, a label moves when
    another spot is better given where all the others are. Everything is
    measured in display pixels, after the axes' limits and aspect are fixed.
    """

    fig = ax.figure
    if not hasattr(fig.canvas, "get_renderer"):
        from matplotlib.backends.backend_agg import FigureCanvasAgg

        FigureCanvasAgg(fig)
    renderer = fig.canvas.get_renderer()
    fig.canvas.draw()
    anchors = ax.transData.transform(points)
    area = ax.get_window_extent(renderer)
    marker = 6.0
    # Another point keeps a halo around it: a label beside a point that is not
    # its own reads as that point's.
    halo = 2.2 * marker
    halos = np.column_stack([anchors - halo, anchors + halo])
    probe = ax.text(0, 0, "", fontsize=size)

    def measure() -> list[tuple[float, float]]:
        probe.set_fontsize(size)
        found = []
        for label in labels:
            probe.set_text(label)
            extent = probe.get_window_extent(renderer)
            found.append((extent.width, extent.height))
        return found

    # Labels that would cover more than a fifth of the plot get a smaller font
    # (down to 7 pt): past that no placement keeps them apart.
    sizes = measure()
    while size > 7 and sum(w * h for w, h in sizes) > _CROWDED * area.width * area.height:
        size -= 1
        sizes = measure()
    probe.remove()

    count = len(labels)
    candidates = []
    reaches = []
    for i in range(count):
        x, y = anchors[i]
        w, h = sizes[i]
        boxes, far = [], []
        for reach in _REACHES:
            gap = (marker + 3) * reach
            for dx, dy in _SPOTS:
                left = x + dx * gap - min(max((1 - dx) / 2, 0.0), 1.0) * w
                bottom = y + dy * gap - min(max((1 - dy) / 2, 0.0), 1.0) * h
                boxes.append((left, bottom, left + w, bottom + h))
                far.append(reach)
        candidates.append(np.array(boxes))
        reaches.append(far)

    def scores(i: int, placed: np.ndarray) -> np.ndarray:
        boxes = candidates[i]
        h = sizes[i][1]
        penalty = clash * _overlaps(boxes, placed) + _overlaps(boxes, np.delete(halos, i, axis=0))
        penalty += (
            np.clip(area.x0 - boxes[:, 0], 0, None) + np.clip(boxes[:, 2] - area.x1, 0, None)
            + np.clip(area.y0 - boxes[:, 1], 0, None) + np.clip(boxes[:, 3] - area.y1, 0, None)
        ) * h * _OUTSIDE  # fmt: skip
        own = _distances(boxes, anchors[i : i + 1])[:, 0]
        others = _distances(boxes, np.delete(anchors, i, axis=0))
        penalty += np.clip(own[:, None] + 2 * marker - others, 0, None).sum(axis=1) * h
        return penalty

    chosen = np.zeros(count, dtype=int)
    placed: dict[int, np.ndarray] = {}
    for i in np.argsort(-masses, kind="stable"):
        current = np.array(list(placed.values())).reshape(-1, 4)
        chosen[i] = int(np.argmin(scores(int(i), current)))
        placed[int(i)] = candidates[i][chosen[i]]
    for _ in range(_ROUNDS):
        moved = False
        for i in np.argsort(-masses, kind="stable"):
            others = np.array([placed[j] for j in range(count) if j != i]).reshape(-1, 4)
            found = scores(int(i), others)
            best = int(np.argmin(found))
            if found[best] < found[chosen[i]] - 1e-6:
                chosen[i] = best
                placed[int(i)] = candidates[i][best]
                moved = True
        if not moved:
            break

    dpi = fig.dpi
    for i in range(count):
        box = placed[i]
        x, y = anchors[i]
        # The text's own anchor: its bottom-left corner, in points from the point.
        offset = ((box[0] - x) * 72 / dpi, (box[1] - y) * 72 / dpi)
        ax.annotate(
            labels[i],
            xy=tuple(points[i]),
            xytext=offset,
            textcoords="offset points",
            ha="left",
            va="bottom",
            fontsize=size,
            color=_ink(),
            zorder=4,
            arrowprops=(
                {"arrowstyle": "-", "color": _muted(), "linewidth": 0.6, "shrinkA": 0, "shrinkB": 4}
                if reaches[i][chosen[i]] > 1
                else None
            ),
        )


def _overlaps(boxes: np.ndarray, others: np.ndarray) -> np.ndarray:
    """The area each of ``boxes`` shares with all of ``others`` (both n × 4)."""
    if len(others) == 0:
        return np.zeros(len(boxes))
    width = np.minimum(boxes[:, None, 2], others[None, :, 2]) - np.maximum(
        boxes[:, None, 0], others[None, :, 0]
    )
    height = np.minimum(boxes[:, None, 3], others[None, :, 3]) - np.maximum(
        boxes[:, None, 1], others[None, :, 1]
    )
    return (np.clip(width, 0, None) * np.clip(height, 0, None)).sum(axis=1)


def _distances(boxes: np.ndarray, points: np.ndarray) -> np.ndarray:
    """How far each point is from each box (0 inside it): boxes × points, in pixels."""
    dx = np.maximum.reduce(
        [boxes[:, None, 0] - points[None, :, 0], np.zeros((len(boxes), len(points))),
         points[None, :, 0] - boxes[:, None, 2]]
    )  # fmt: skip
    dy = np.maximum.reduce(
        [boxes[:, None, 1] - points[None, :, 1], np.zeros((len(boxes), len(points))),
         points[None, :, 1] - boxes[:, None, 3]]
    )  # fmt: skip
    return np.hypot(dx, dy)


__all__ = [
    "LAYOUTS",
    "MAX_DIMENSIONS",
    "CorrespondenceSolution",
    "MapTable",
    "PerceptualMap",
    "analyze",
    "ca",
    "layout_problem",
    "plot",
]
