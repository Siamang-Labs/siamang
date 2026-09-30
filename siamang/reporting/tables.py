"""Declarative table components for survey reporting.

Each table class auto-resolves variable labels and value labels from the
attached SurveyData metadata, similar to SPSS output tables.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

from siamang.data.listwise import round_p
from siamang.reporting import p_values

if TYPE_CHECKING:
    from siamang.data.survey_data import SurveyData


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _get_label(data: SurveyData, var_name: str) -> str:
    """Get the human-readable label for a variable, falling back to the name."""
    if data.variables and var_name in data.variables:
        return data.variables[var_name].label or var_name
    return var_name


def _get_value_labels(data: SurveyData, var_name: str) -> dict[Any, str]:
    """Get value labels for a variable."""
    if data.variables and var_name in data.variables:
        return data.variables[var_name].labels or {}
    return {}


def _weights_of(data: SurveyData, index: pd.Index) -> pd.Series | None:
    """The weight of each row in ``index``, or None when the data is unweighted.

    ``data.weight`` names the column (``SurveyData.with_weight``, the flow's
    Apply weight node); a weight that is missing or not a number counts 0.
    """
    column = data.weight
    if column is None:
        return None
    if column not in data.frame.columns:
        raise ValueError(f"Weight column '{column}' not found in frame.")
    raw = data.frame.loc[index, column]
    return pd.to_numeric(raw, errors="coerce").fillna(0.0).astype(float)


def _unweighted_note(data: SurveyData) -> str | None:
    """What a table that does not use the data's weight says about it, or None."""
    if data.weight is None:
        return None
    from siamang.data.analysis import unweighted_note

    return unweighted_note(data.weight)


def _weighted_summary(values: np.ndarray, weights: np.ndarray) -> tuple[float, float, float, int]:
    """Weighted mean, SD and median of ``values``, and their unweighted count.

    The SD is the weighted variance scaled by n / (n - 1), so equal weights give
    exactly the sample SD the unweighted table shows. An answer weighted 0 (a
    missing weight counts 0) takes no part in it — n is the answers that carry
    weight, and with fewer than two of them the SD is undefined (NaN), not 0.
    The count stays every answer. The median is the value at which the
    cumulative weight first reaches half the total.
    """
    n = int(len(values))
    total = float(weights.sum())
    if n == 0 or total <= 0:
        return float("nan"), float("nan"), float("nan"), n
    mean = float(np.average(values, weights=weights))
    kept = int((weights > 0).sum())
    if kept > 1:
        variance = float(np.average((values - mean) ** 2, weights=weights)) * kept / (kept - 1)
        sd = variance**0.5
    else:
        sd = float("nan")
    order = np.argsort(values, kind="stable")
    cumulative = np.cumsum(weights[order])
    at = min(int(np.searchsorted(cumulative, total / 2.0)), n - 1)
    return mean, sd, float(values[order][at]), n


def _counted(
    stats: dict[str, Any], data: SurveyData, frame: pd.DataFrame, columns: list[str]
) -> None:
    """Say so in ``stats`` when ``frame`` reads the codebook's missing codes as
    answers — as a table's default path does, for stored flows' sake."""
    from siamang.data.inference import missing_codes_counted

    note = missing_codes_counted(frame, columns, data.variables)
    if note:
        stats["Missing codes counted as answers"] = note


def _get_scale(data: SurveyData, var_name: str) -> str | None:
    """Get measurement scale for a variable."""
    if data.variables and var_name in data.variables:
        return data.variables[var_name].scale
    return None


def _frame_to_markdown(df: pd.DataFrame) -> str:
    """Convert a DataFrame to a GitHub-flavored Markdown pipe table."""
    lines = []
    headers = list(df.columns)
    lines.append("| " + " | ".join(markdown_cell(h) for h in headers) + " |")
    lines.append("|" + "|".join("---" for _ in headers) + "|")
    # Row by row with each column's own type: iterrows() casts a row of numbers
    # to one float dtype, which printed a count of 4 as "4.0".
    for row in df.itertuples(index=False, name=None):
        lines.append("| " + " | ".join(markdown_cell(v) for v in row) + " |")
    return "\n".join(lines)


def markdown_cell(value: Any) -> str:
    """A cell of a Markdown pipe table: a "|" in its text (a label "A|B") is
    escaped, where it would end the cell and move the rest a column right."""
    return str(value).replace("|", "\\|")


def stat_text(value: Any) -> str:
    """A statistic as a table's footer and a report's statistics line print it.

    A float keeps up to four decimals, without padding (``df = 124.98``, not
    ``124.9800``; a whole one keeps its ``.0``, as a table cell prints it); one
    that is not 0 but below 0.0001 — a p-value, most often — keeps four
    significant digits with its exponent (``p = 5.8e-07``, ``p = 7.988e-32``),
    so nothing that is not 0 is printed as ``0.0000``. That is
    :func:`~siamang.data.listwise.round_p`'s rule, so the footer and the
    statistics give the same p: ``5e-05``, not ``0.0001`` beside it. A value
    below 1 that four significant digits already hold prints as it is kept —
    the p of Paired tests and factor analysis
    (:func:`~siamang.data.listwise.p_rounded`: ``p = 0.002343``, not ``0.0023``).
    """
    if isinstance(value, float) and not isinstance(value, bool):
        if not np.isfinite(value):
            return str(value)
        if value != 0 and abs(value) < 1e-4:
            return f"{value:.4g}"
        if value != 0 and abs(value) < 1 and float(f"{value:.4g}") == value:
            return str(float(value))  # float(): a numpy float's str is its repr
        text = f"{value:.4f}".rstrip("0")
        text = text + "0" if text.endswith(".") else text
        return "0.0" if text == "-0.0" else text
    return str(value)


def stat_item(key: Any, value: Any, *, p: bool | None = None) -> str:
    """A statistic as a table's footer and a report's statistics line write
    it: ``key = value``, the value as :func:`stat_text` prints it.

    A p-value below the threshold the report asks for
    (:attr:`~siamang.reporting.theme.ReportTheme.p_values`, see
    :mod:`siamang.reporting.p_values`) is written as the bound — ``p < 0.01``,
    ``Bartlett p < 0.001`` — and so is a ``p = …`` the engine wrote into a
    sentence (a pair of groups compared). ``p`` says whether the statistic is
    a p-value; by default its name says (:func:`~siamang.reporting.p_values.is_p`).
    Under the default, ``exact``, it is ``key = value`` as it always was.
    """
    mode = p_values.current()
    if mode != p_values.DEFAULT:
        if (p_values.is_p(key) if p is None else p) and p_values.is_below(value, mode):
            return f"{key} {p_values.bound(mode)}"
        if isinstance(value, str):
            return f"{key} = {p_values.in_text(value, mode)}"
    return f"{key} = {stat_text(value)}"


def frame_to_html(df: pd.DataFrame, caption: str | None = None, *, rounded: bool = True) -> str:
    """Convert a DataFrame to a clean HTML table.

    Public because a report renders bare DataFrames through the same path as
    its table components, so every table in a document carries the same class
    and the stylesheet has one thing to style.

    A number is written as the Markdown beside it writes it. A table
    component's cells are rounded already, and its Markdown prints each with
    ``str``, so the HTML does too: pandas' own formatting pads a column to one
    width and turned a p of ``3.363e-07`` into ``0.0`` beside a ``.md`` that
    said ``3.363e-07``. A bare DataFrame added to a report as it is
    (``rounded=False`` — a regression's coefficients, a PCA's loadings) is not
    rounded, and its Markdown goes through tabulate, which writes a float in a
    column of numbers with six significant digits (``62.263``,
    ``6.15462e-38``); so does its HTML, rather than ``62.26300527031391``.
    """
    shown = df.astype(object)
    for position in range(shown.shape[1]):
        column = shown.iloc[:, position]
        text = _float_text if rounded or not _numbers_only(column) else _tabulated
        shown.iloc[:, position] = column.map(text)
    html = shown.to_html(index=False, classes="siamang-table", border=0)
    if caption:
        html = html.replace("<table", f"<caption>{caption}</caption>\n<table", 1)
    return html


def _float_text(value: Any) -> Any:
    """A float as ``str`` writes it (NaN left for pandas to print)."""
    return str(value) if isinstance(value, float) and value == value else value


def _tabulated(value: Any) -> Any:
    """A number in a column of numbers as tabulate writes it: ``format(value, "g")``."""
    if isinstance(value, float | np.floating) and value == value:
        return format(float(value), "g")
    return value


def _numbers_only(column: pd.Series) -> bool:
    """Whether tabulate reads ``column`` as numbers: every value present is an
    int or a float (a bool, a text or a date makes it a column of text)."""
    for value in column:
        if value is None or (isinstance(value, float) and value != value):
            continue
        if isinstance(value, bool | np.bool_) or not isinstance(
            value, int | float | np.integer | np.floating
        ):
            return False
    return True


# Kept under its old private name for anything that reached for it.
_frame_to_html = frame_to_html


# ─── Base Class ───────────────────────────────────────────────────────────────


@dataclass
class SurveyTable:
    """Base class for all declarative table components."""

    data: SurveyData
    _result: pd.DataFrame = field(init=False, repr=False, default=None)
    _stats: dict[str, Any] = field(init=False, repr=False, default_factory=dict)

    def _build(self) -> None:
        """Build the table. Subclasses must implement this."""
        raise NotImplementedError

    def _ensure_built(self) -> None:
        if self._result is None:
            if not self.data.frame.index.is_unique:
                # The tables select rows by label (a group's rows, the weights of
                # the rows kept); a label the index repeats would pull in every
                # row that shares it. A table carries no index, so it is built
                # on the rows numbered by position.
                self.data = self.data.with_frame(self.data.frame.reset_index(drop=True))
            self._build()

    def to_frame(self) -> pd.DataFrame:
        """Return the table as a pandas DataFrame."""
        self._ensure_built()
        return self._result.copy()

    @property
    def stats(self) -> dict[str, Any]:
        """The statistics the table reports under itself (χ², p, N, …), as a dict."""
        self._ensure_built()
        return dict(self._stats)

    def to_markdown(self, *, theme: Any = None) -> str:
        """Return the table as a GitHub-flavored Markdown string.

        ``theme`` (a :class:`~siamang.reporting.theme.ReportTheme`, or its
        fields as a dict) says how its p-values are written (``p_values``);
        without one, as the report rendering the table asks, and outside a
        report as they are kept.
        """
        with p_values.showing(theme):
            self._ensure_built()
            md = _frame_to_markdown(self._shown(self._result))
            if self._stats:
                md += "\n\n" + self._format_stats()
        return md

    def to_html(self, *, theme: Any = None) -> str:
        """Return the table as an HTML string (``theme``: as :meth:`to_markdown`)."""
        with p_values.showing(theme):
            self._ensure_built()
            html = _frame_to_html(self._shown(self._result))
            if self._stats:
                html += f"\n<p class='siamang-stats'>{self._format_stats()}</p>"
        return html

    def _p_columns(self) -> list[Any]:
        """The columns that hold p-values, which a report may write as a bound
        (:mod:`siamang.reporting.p_values`): those named as p-values are
        (``p``, ``p (Holm)``, ``Beta p`` …). A table whose columns are named by
        the data — a crosstab's answers — says it has none."""
        return [column for column in self._result.columns if p_values.is_p(column)]

    def _shown(self, frame: pd.DataFrame) -> pd.DataFrame:
        """``frame`` (the table, or its printable form) with its p-values
        written as the report asks; ``frame`` itself under ``exact``."""
        return p_values.cells(frame, self._p_columns())

    def export_xlsx(self, path: str | Path) -> Path:
        """Export the table to an Excel file."""
        from siamang.io.excel_text import to_excel

        self._ensure_built()
        path = Path(path)
        to_excel(self._result, path, index=False, sheet_name="Table")
        return path

    def _format_stats(self) -> str:
        """Format statistics footer (each as :func:`stat_item` writes it: the
        value as :func:`stat_text` does, a p-value as the report asks)."""
        footer = self._footer()
        keys = p_values.statistics(footer)
        return "; ".join(stat_item(key, val, p=key in keys) for key, val in footer.items())

    def _footer(self) -> dict[str, Any]:
        """The statistics the footer prints: :attr:`stats`."""
        return self._stats

    def __repr__(self) -> str:
        self._ensure_built()
        return self._result.to_string()

    def _repr_html_(self) -> str:
        """Jupyter notebook HTML representation."""
        return self.to_html()


def _value_order(value: Any) -> tuple[int, float, str]:
    """Where a value sorts in a table by value: numbers (and number-like
    text, "2") by their value, then other text alphabetically. A column
    holding both — codes, and a text an earlier runtime or an import left
    among them ("25-34") — could not be sorted at all, and the table
    stopped its whole report."""
    if isinstance(value, bool):
        return (0, float(value), "")
    if isinstance(value, int | float | np.integer | np.floating):
        return (0, float(value), "")
    try:
        return (0, float(str(value)), str(value))
    except ValueError:
        return (1, 0.0, str(value))


# ─── FreqTable ────────────────────────────────────────────────────────────────


@dataclass
class FreqTable(SurveyTable):
    """Univariate frequency distribution table.

    Automatically resolves value labels and computes N, %, and cumulative %.

    Parameters
    ----------
    data : SurveyData
        The survey data container with variable metadata.
    column : str
        Name of the variable to tabulate.
    exclude_missing : bool
        If True (default), excludes rows where the column is NaN.
    sort : str
        Sort order: "value" (by code, default), "freq" (by count descending),
        or "label" (alphabetical by label).
    """

    column: str = ""
    exclude_missing: bool = True
    sort: str = "value"

    def _build(self) -> None:
        from siamang.data import multi

        col = self.column
        series = self.data.frame[col]
        if multi.is_multi(series):
            self._build_multi(series)
            return

        if self.exclude_missing:
            series = series.dropna()

        counts = series.value_counts(dropna=self.exclude_missing)
        # Weighted data: N and the percentages are sums of weights, and the raw
        # count stands beside them — it is the number a reader trusts a
        # percentage by. Unweighted, the table is exactly what it was.
        weights = _weights_of(self.data, series.index)
        weighted = (
            weights.groupby(series, dropna=self.exclude_missing).sum()
            if weights is not None
            else None
        )
        value_labels = _get_value_labels(self.data, col)

        rows = []
        # A weighted N is shown to one decimal, but the percentages are of the
        # sums of weights as they are (as a Crosstab's, a bar chart's): of the
        # rounded sums, weights summing to 1 over 1000 respondents made every
        # answer 20.0 %.
        exact: list[float] = []
        for value in sorted(counts.index, key=_value_order):
            n = int(counts[value])
            label = value_labels.get(value, str(value))
            row: dict[str, Any] = {"Value": value, "Label": label, "N": n}
            if weighted is not None:
                row["N"] = round(float(weighted.get(value, 0.0)), 1)
                row["Unweighted N"] = n
            rows.append(row)
            exact.append(float(weighted.get(value, 0.0)) if weighted is not None else float(n))

        columns = ["Value", "Label", "N"] + (["Unweighted N"] if weighted is not None else [])
        if rows:
            df = pd.DataFrame(rows, columns=columns)
        else:
            df = pd.DataFrame(columns=columns)
        sums = pd.Series(exact, index=df.index, dtype=float)

        if self.sort in ("freq", "label") and not df.empty:
            if self.sort == "label":
                order = df.sort_values("Label")
            elif weighted is None:
                order = df.sort_values("N", ascending=False)
            else:
                order = df.assign(_exact=sums).sort_values("_exact", ascending=False)
            df = order[columns].reset_index(drop=True)
            sums = sums[order.index].reset_index(drop=True)

        total = float(sums.sum()) if not df.empty else 0.0
        n_valid = int(counts.sum())
        df["%"] = (sums / total * 100).round(1) if total > 0 else 0.0
        if weighted is not None and total > 0:
            df["Cumulative %"] = (sums.cumsum() / total * 100).round(1)
        else:
            df["Cumulative %"] = df["%"].cumsum().round(1) if not df.empty else 0.0

        # Append total row
        total_entry: dict[str, Any] = {
            "Value": "",
            "Label": "Total",
            "N": round(total, 1) if weighted is not None else int(total),
            "%": 100.0,
            "Cumulative %": 100.0,
        }
        if weighted is not None:
            total_entry["Unweighted N"] = n_valid
        total_row = pd.DataFrame([total_entry])
        df = pd.concat([df, total_row], ignore_index=True)

        self._result = df
        self._stats = {"Variable": _get_label(self.data, col), "N valid": n_valid}
        if weighted is not None:
            self._stats["Weighted N"] = round(total, 1)
            # What the weighting costs in precision, on the answers counted: a
            # weighted percentage is as precise as one of Kish's effective N
            # respondents, the design effect times fewer than N valid.
            squares = float((weights.astype(float) ** 2).sum())
            if total > 0 and squares > 0:
                effective = total**2 / squares
                self._stats["Effective N"] = round(effective, 1)
                self._stats["Design effect"] = round(n_valid / effective, 3)
            self._stats["Weight"] = self.data.weight

    def _build_multi(self, series: pd.Series) -> None:
        """A multiple-choice question: one row per option, base of respondents.

        Not a variant of the table above but a different table, because the
        numbers mean something different. Each option's share is of the people
        who answered the question, so the column sums above 100 % — which is why
        the base is a row of its own and the footer says it in words. There is no
        cumulative column: options overlap, so adding them up is meaningless.
        """
        from siamang.data import multi

        labels = _get_value_labels(self.data, self.column)
        weight = self.data.weight
        if weight is not None and weight not in self.data.frame.columns:
            raise ValueError(f"Weight column '{weight}' not found in frame.")
        raw = multi.frequencies(
            self.data.frame, self.column, labels=labels or None, codes=list(labels) or None
        )
        counts = (
            multi.frequencies(
                self.data.frame,
                self.column,
                labels=labels or None,
                codes=list(labels) or None,
                weight=weight,
            )
            if weight is not None
            else raw
        )
        rows = []
        for (_, row), (_, raw_row) in zip(counts.iterrows(), raw.iterrows(), strict=True):
            entry: dict[str, Any] = {
                "Value": row["value"],
                "Label": row["label"],
                "N": row["count"],
                "%": row["percent"],
            }
            if weight is not None:
                entry["Unweighted N"] = raw_row["count"]
            rows.append(entry)
        if self.sort == "freq":
            rows.sort(key=lambda r: (-r["N"], str(r["Label"])))
        elif self.sort == "label":
            rows.sort(key=lambda r: str(r["Label"]))
        base_row: dict[str, Any] = {
            "Value": "",
            "Label": "Base (respondents answering)",
            "N": counts.base,
            "%": 100.0,
        }
        if weight is not None:
            base_row["Unweighted N"] = raw.base
        rows.append(base_row)
        columns = ["Value", "Label", "N", *(["Unweighted N"] if weight is not None else []), "%"]
        self._result = pd.DataFrame(rows, columns=columns)
        self._stats = {
            "Variable": _get_label(self.data, self.column),
            "Base": f"{counts.base} respondents",
            "Answers": counts.answers,
            "Note": "multiple answers allowed; percentages are of respondents",
        }
        if weight is not None:
            self._stats["Base"] = f"{raw.base} respondents ({counts.base} weighted)"
            self._stats["Weight"] = weight


# ─── NpsTable ─────────────────────────────────────────────────────────────────


@dataclass
class NpsTable(SurveyTable):
    """Net Promoter Score of a 0–10 "how likely are you to recommend" item.

    Detractors are 0–6, passives 7–8, promoters 9–10; the score is the share
    of promoters minus the share of detractors (−100 … +100). The table has
    one row per group with N and %, plus a total row; the score, its
    standard error and a 95 % confidence interval are the stats. Weighted
    when the data carries a weight column.

    Parameters
    ----------
    data : SurveyData
        The survey data container with variable metadata.
    column : str
        The 0–10 variable.
    """

    column: str = ""

    GROUPS = (("Detractors", 0, 6), ("Passives", 7, 8), ("Promoters", 9, 10))

    def _build(self) -> None:
        import numpy as np

        col = self.column
        frame = self.data.frame
        series = pd.to_numeric(frame[col], errors="coerce")
        keep = series.notna()
        values = series[keep].to_numpy(dtype=float)
        if self.data.weight and self.data.weight in frame.columns:
            weights = pd.to_numeric(frame.loc[keep, self.data.weight], errors="coerce")
            weights = weights.fillna(0).to_numpy(dtype=float)
        else:
            weights = np.ones(len(values))
        out_of_range = ((values < 0) | (values > 10)).sum()
        if out_of_range:
            raise ValueError(
                f"{col!r} has {int(out_of_range)} values outside 0–10; NPS needs a 0–10 scale"
            )
        total_w = float(weights.sum())
        n = int(keep.sum())
        weighted = bool(self.data.weight and self.data.weight in frame.columns)
        rows = []
        shares: dict[str, float] = {}
        for label, lo, hi in self.GROUPS:
            mask = (values >= lo) & (values <= hi)
            share = float(weights[mask].sum()) / total_w * 100 if total_w > 0 else 0.0
            shares[label] = share
            row: dict[str, Any] = {"Group": label, "Range": f"{lo}–{hi}"}
            if weighted:
                # N is what the % is of, as in a weighted frequency table: the
                # weighted count, with the respondents beside it. An unweighted
                # N next to a weighted % (348 of 579 beside 61.8 %) reads as a
                # sum that does not add up.
                row["N"] = round(float(weights[mask].sum()), 1)
                row["Unweighted N"] = int(mask.sum())
            else:
                row["N"] = int(mask.sum())
            row["%"] = round(share, 1)
            rows.append(row)
        total: dict[str, Any] = {"Group": "Total", "Range": "0–10"}
        if weighted:
            total["N"] = round(total_w, 1)
            total["Unweighted N"] = n
        else:
            total["N"] = n
        total["%"] = 100.0 if n else 0.0
        rows.append(total)
        columns = ["Group", "Range", "N", *(["Unweighted N"] if weighted else []), "%"]
        self._result = pd.DataFrame(rows, columns=columns)

        score = shares["Promoters"] - shares["Detractors"]
        # Standard error of a difference of two proportions from one sample
        # (Rocks, 2016), on the effective sample size when weighted.
        p_pro, p_det = shares["Promoters"] / 100, shares["Detractors"] / 100
        n_eff = total_w**2 / float((weights**2).sum()) if total_w > 0 else 0.0
        variance = (p_pro + p_det - (p_pro - p_det) ** 2) / n_eff if n_eff > 0 else float("nan")
        se = float(np.sqrt(variance)) * 100 if variance == variance else float("nan")
        self._stats = {
            "Variable": _get_label(self.data, col),
            "NPS": round(score, 1),
            "SE": round(se, 1) if se == se else None,
            "CI95 low": round(max(-100.0, score - 1.96 * se), 1) if se == se else None,
            "CI95 high": round(min(100.0, score + 1.96 * se), 1) if se == se else None,
            "N valid": n,
        }
        if self.data.weight and self.data.weight in frame.columns:
            self._stats["Weight"] = self.data.weight


# ─── CrossTable ───────────────────────────────────────────────────────────────


def _sparse_cells(expected: np.ndarray) -> str | None:
    """What a chi-square test's footer says when its table is too sparse for
    the test's p to be trusted (Cochran's rule: no expected count below 1, and
    at most a fifth of them below 5), or None. The expected counts are those
    the test was run on — of the effective sample when weighted."""

    cells = int(expected.size)
    if cells == 0:
        return None
    below = int((expected < 5).sum())
    smallest = float(expected.min())
    if below <= cells / 5 and smallest >= 1:
        return None
    return (
        f"{below} of {cells} cells ({below / cells * 100:.0f}%) expect fewer than 5 "
        f"respondents, the smallest {smallest:.1f}: the chi-square's p is not reliable "
        "with so few; merge sparse answers, or use Fisher's exact test"
    )


@dataclass
class CrossTable(SurveyTable):
    """Bivariate cross-tabulation with optional statistical tests.

    Automatically resolves value labels for both variables and computes
    Chi-square, Cramer's V, and significance.

    Parameters
    ----------
    data : SurveyData
        The survey data container with variable metadata.
    row : str
        Row variable name (independent variable).
    col : str
        Column variable name (dependent variable).
    pct : str
        Percentage direction: "none", "row", "col", or "total".
    test : bool
        If True, runs the test ``method`` names and reports it in ``stats``.
    method : str
        ``"chi2"`` (default): Chi-square with df, p and Cramer's V.
        ``"fisher"``: Fisher's exact test — for a 2x2 table with the odds ratio
        and its interval, larger tables by the Fisher-Freeman-Halton test. It
        counts respondents, leaves the codebook's missing codes out of the table
        and says so (see :func:`siamang.reporting.stat_tables.fisher_stats`).
    """

    row: str = ""
    col: str = ""
    pct: str = "none"
    test: bool = True
    method: str = "chi2"

    def _p_columns(self) -> list[Any]:
        # The columns are the answers of `col`, named by its labels: one
        # labeled "p" holds counts or percentages, not p-values.
        return []

    def _build(self) -> None:
        from siamang.data import multi

        if self.method not in ("chi2", "fisher"):
            raise ValueError(f"method must be 'chi2' or 'fisher'; got {self.method!r}.")
        if multi.is_multi(self.data.frame[self.row]):
            self._build_multi()
            return
        fisher = self.test and self.method == "fisher"
        source, left_out = self.data.frame, {}
        if fisher:
            from siamang.data.inference import without_missing_codes

            source, left_out = without_missing_codes(
                source, [self.row, self.col], self.data.variables
            )
        frame = source[[self.row, self.col]].dropna()
        row_labels = _get_value_labels(self.data, self.row)
        col_labels = _get_value_labels(self.data, self.col)

        # Build contingency table — of weights when the data is weighted, so the
        # percentages below are weighted with the same normalisation.
        weights = _weights_of(self.data, frame.index)
        if weights is None:
            contingency = pd.crosstab(frame[self.row], frame[self.col])
        else:
            contingency = pd.crosstab(
                frame[self.row], frame[self.col], values=weights, aggfunc="sum"
            ).fillna(0.0)

        # Apply percentage normalization
        if self.pct == "row":
            display = contingency.div(contingency.sum(axis=1), axis=0) * 100
        elif self.pct == "col":
            display = contingency.div(contingency.sum(axis=0), axis=1) * 100
        elif self.pct == "total":
            display = contingency / contingency.values.sum() * 100
        else:
            display = contingency.copy()

        display = display.round(1)

        # Apply labels
        if row_labels:
            display.index = [row_labels.get(v, str(v)) for v in display.index]
        if col_labels:
            display.columns = [col_labels.get(v, str(v)) for v in display.columns]

        # The margins. In a table of percentages the margin that is not a base
        # holds percentages too — the overall distribution the rows (or the
        # columns) are read against — and the counts the percentages are of are
        # named "Base". A "Total" row of counts under row percentages read as
        # percentages that did not add up (9.1, 29.6, … under 3.9, 7.4, …).
        row_sums = contingency.sum(axis=1).to_numpy(dtype=float)
        col_sums = contingency.sum(axis=0).to_numpy(dtype=float)
        grand = float(contingency.to_numpy(dtype=float).sum())

        def base(value: float) -> int | float:
            return round(float(value), 1) if weights is not None else int(round(value))

        def share(values: np.ndarray) -> list[float]:
            if grand <= 0:
                return [0.0 for _ in values]
            return [round(float(value) / grand * 100, 1) for value in values]

        def add_row(name: str, values: list[Any]) -> None:
            # As objects, so a column of whole counts stays whole ("58", not
            # "58.0") beside the percentages of the other columns.
            display.loc[name] = pd.Series(values, index=display.columns, dtype=object)

        if self.pct == "row":
            display["Base"] = [base(value) for value in row_sums]
            add_row("Total", [*share(col_sums), base(grand)])
        elif self.pct == "col":
            display["Total"] = share(row_sums)
            add_row("Base", [*(base(value) for value in col_sums), base(grand)])
        elif self.pct == "total":
            display["Total"] = share(row_sums)
            add_row("Total", [*share(col_sums), 100.0 if grand > 0 else 0.0])
        else:
            display["Total"] = [base(value) for value in row_sums]
            add_row("Total", [*(base(value) for value in col_sums), base(grand)])

        # Reset index for clean output
        display = display.reset_index()
        display = display.rename(columns={"index": _get_label(self.data, self.row)})

        self._result = display

        # Statistical tests
        if fisher:
            from siamang.reporting.stat_tables import fisher_stats

            self._stats = fisher_stats(
                self.data,
                pd.crosstab(frame[self.row], frame[self.col]),
                row=self.row,
                col=self.col,
                weights=weights,
                left_out=left_out,
            )
        elif self.test:
            try:
                from scipy.stats import chi2_contingency

                table = contingency.values
                if weights is not None:
                    # Weights make a sample behave like a smaller one; a test on
                    # the weighted counts as if they were people would find
                    # significance the data does not support. The counts are
                    # scaled to the effective sample size (Kish), as the banner
                    # table does.
                    total_w = float(weights.sum())
                    n_eff = total_w**2 / float((weights**2).sum()) if total_w > 0 else 0.0
                    table = table * (n_eff / total_w) if total_w > 0 else table
                chi2_stat, p_value, dof, expected = chi2_contingency(table)
                n = table.sum()
                min_dim = min(contingency.shape[0] - 1, contingency.shape[1] - 1)
                cramers_v = (chi2_stat / (n * min_dim)) ** 0.5 if n > 0 and min_dim > 0 else 0.0
                self._stats = {
                    "χ²": round(chi2_stat, 3),
                    "df": int(dof),
                    "p": round_p(p_value),
                    "Cramér's V": round(cramers_v, 3),
                    "N": int(frame.shape[0]),
                }
                if weights is not None:
                    self._stats["Weighted N"] = round(total_w, 1)
                    self._stats["Effective N"] = round(n_eff, 1)
                    self._stats["Weight"] = self.data.weight
                    shown = "weighted counts" if self.pct == "none" else "weighted bases"
                    self._stats["Base"] = f"effective (Kish) for the test; {shown} shown"
                sparse = _sparse_cells(np.asarray(expected, dtype=float))
                if sparse:
                    self._stats["Warning"] = sparse
            except ImportError:
                self._stats = {"error": "scipy not installed"}
        elif weights is not None:
            self._stats = {"Weighted N": round(float(weights.sum()), 1), "Weight": self.data.weight}
        if not fisher:
            _counted(self._stats, self.data, frame, [self.row, self.col])

    def _build_multi(self) -> None:
        """A multiple-choice question against a group: reach within each column.

        Percentages are of each group's own base, which is the number a reader
        compares across columns. No chi-square: the categories overlap, so the
        test's independence assumption does not hold and a p-value here would be
        a number that looks like evidence and is not.
        """
        from siamang.data import multi

        test_name = "Fisher's exact test" if self.method == "fisher" else "chi-square"
        labels = _get_value_labels(self.data, self.row)
        weight = self.data.weight
        if weight is not None and weight not in self.data.frame.columns:
            raise ValueError(f"Weight column '{weight}' not found in frame.")
        table = multi.crosstab(
            self.data.frame,
            self.row,
            self.col,
            labels=labels or None,
            codes=list(labels) or None,
            weight=weight,
        )
        bases = table.base if isinstance(table.base, dict) else {}
        # The groups are named as the single-answer crosstab names them: by
        # the labels of the column variable, not its codes ("1.0").
        col_labels = _get_value_labels(self.data, self.col)
        names = {group: str(col_labels.get(group, group)) for group in bases}
        display = table.drop(columns=["value"]).rename(
            columns={
                "label": _get_label(self.data, self.row),
                **{str(group): name for group, name in names.items()},
            }
        )
        display.loc[len(display)] = ["Base (respondents answering)", *bases.values()]
        if weight is not None:
            # The weighted base is what the percentages are of; the people
            # behind it are the other number a reader needs.
            raw = multi.crosstab(
                self.data.frame,
                self.row,
                self.col,
                labels=labels or None,
                codes=list(labels) or None,
            )
            raw_bases = raw.base if isinstance(raw.base, dict) else {}
            display.loc[len(display)] = [
                "Unweighted base",
                *(raw_bases.get(group, 0) for group in bases),
            ]
        self._result = display
        self._stats = {
            "Variable": _get_label(self.data, self.row),
            "Base": ", ".join(f"{names[group]}: {size}" for group, size in bases.items()),
            "Note": (
                "multiple answers allowed; percentages are of each group, and no "
                f"{test_name} is reported because the categories overlap"
            ),
        }
        if weight is not None:
            self._stats["Base"] += " (weighted)"
            self._stats["Weight"] = weight


class _BlankUndefined:
    """Print NaN and None as empty cells; :meth:`SurveyTable.to_frame` keeps them.

    For tables whose cells can be undefined (an SD of one answer, the sentiment
    of a theme nobody was scored on): a report should show a blank there, not
    ``nan``.
    """

    def _printable(self) -> pd.DataFrame:
        self._ensure_built()  # type: ignore[attr-defined]
        frame = self._result.astype(object)  # type: ignore[attr-defined]
        return frame.where(frame.notna(), "")

    def to_markdown(self, *, theme: Any = None) -> str:
        with p_values.showing(theme):
            md = _frame_to_markdown(self._shown(self._printable()))  # type: ignore[attr-defined]
            if self._stats:  # type: ignore[attr-defined]
                md += "\n\n" + self._format_stats()  # type: ignore[attr-defined]
        return md

    def to_html(self, *, theme: Any = None) -> str:
        with p_values.showing(theme):
            html = frame_to_html(self._shown(self._printable()))  # type: ignore[attr-defined]
            if self._stats:  # type: ignore[attr-defined]
                stats = self._format_stats()  # type: ignore[attr-defined]
                html += f"\n<p class='siamang-stats'>{stats}</p>"
        return html


# ─── GroupMeanTable ───────────────────────────────────────────────────────────


@dataclass
class GroupMeanTable(_BlankUndefined, SurveyTable):
    """Grouped means comparison table with automatic significance testing.

    Compares the mean of a continuous variable across categories of a
    grouping variable. Automatically selects the appropriate test based
    on the number of groups and the measurement scale.

    Parameters
    ----------
    data : SurveyData
        The survey data container with variable metadata.
    column : str
        Continuous dependent variable (interval/ratio).
    by : str
        Categorical grouping variable (nominal/ordinal).
    test : bool
        If True, runs a significance test — the one ``method`` names.
    method : str
        ``"auto"`` (default) chooses by scale and number of groups:
        - 2 groups: Mann-Whitney U (ordinal) or Independent t-test (interval/ratio)
        - 3+ groups: Kruskal-Wallis H (ordinal) or One-way ANOVA (interval/ratio)
        Or by hand: ``"student"``, ``"welch"``, ``"anova"``, ``"welch_anova"``,
        ``"mannwhitney"``, ``"kruskal"`` — reported with df and an effect size.
    posthoc : str
        ``"none"`` (default), or every pair of groups compared after the test:
        ``"tukey"`` after ``anova``, ``"games_howell"`` after ``welch_anova``,
        ``"dunn"`` after ``kruskal`` (p adjusted by ``adjust``: ``"holm"`` or
        ``"bonferroni"``). The pairs render under the table and are
        :attr:`posthoc_table`.

    A test chosen by hand leaves the codebook's missing codes out of the table
    and the test, and says how many; ``"auto"`` reads the data as it always has.
    """

    column: str = ""
    by: str = ""
    test: bool = True
    method: str = "auto"
    posthoc: str = "none"
    adjust: str = "holm"
    _posthoc: Any = field(init=False, repr=False, default=None)

    @property
    def posthoc_table(self) -> Any:
        """The post-hoc pairs (a :class:`~siamang.reporting.stat_tables.PostHocTable`),
        or None when none was asked for or it could not run."""
        self._ensure_built()
        return self._posthoc

    def to_markdown(self, *, theme: Any = None) -> str:
        from siamang.reporting.stat_tables import render_with_posthoc

        with p_values.showing(theme):
            return render_with_posthoc(super().to_markdown(), self.posthoc_table, html=False)

    def to_html(self, *, theme: Any = None) -> str:
        from siamang.reporting.stat_tables import render_with_posthoc

        with p_values.showing(theme):
            return render_with_posthoc(super().to_html(), self.posthoc_table, html=True)

    def export_xlsx(self, path: str | Path) -> Path:
        if self.posthoc_table is None:
            return super().export_xlsx(path)
        from siamang.reporting.stat_tables import export_with_posthoc

        return export_with_posthoc(self, self.posthoc_table, path)

    def _chosen(self) -> bool:
        """Whether the test was chosen by hand rather than automatically; checks
        that the method, the post-hoc test and its adjustment go together."""
        from siamang.data.inference import POSTHOC_FOLLOWS, POSTHOC_NAMES
        from siamang.reporting.stat_tables import MEANS_TESTS

        if self.method != "auto" and self.method not in MEANS_TESTS:
            choices = ", ".join(["auto", *MEANS_TESTS])
            raise ValueError(f"method must be one of {choices}; got {self.method!r}.")
        if self.posthoc != "none":
            follows = POSTHOC_FOLLOWS.get(self.posthoc)
            if follows is None:
                raise ValueError(
                    f"posthoc must be none, tukey, games_howell or dunn; got {self.posthoc!r}."
                )
            if self.method != follows:
                raise ValueError(
                    f"{POSTHOC_NAMES[self.posthoc]} follows {MEANS_TESTS[follows]}: "
                    f"method={follows!r}."
                )
        if self.adjust not in ("holm", "bonferroni"):
            raise ValueError("adjust must be 'holm' or 'bonferroni'.")
        return self.test and (self.method != "auto" or self.posthoc != "none")

    def _build(self) -> None:
        from siamang.data import multi

        chosen = self._chosen()
        if multi.is_multi(self.data.frame[self.by]):
            self._build_multi()
            return
        source, left_out = self.data.frame, {}
        if chosen:
            from siamang.data.inference import without_missing_codes

            source, left_out = without_missing_codes(
                source, [self.column, self.by], self.data.variables
            )
        frame = source[[self.column, self.by]].dropna()
        by_labels = _get_value_labels(self.data, self.by)
        col_label = _get_label(self.data, self.column)
        col_scale = _get_scale(self.data, self.column)

        weights = _weights_of(self.data, frame.index)
        if weights is None:
            # In float64: a float32 column (a Stata "float", Parquet from other
            # tools) aggregates to float32, which round(3) cannot hold, and the
            # cells printed 3.444000005722046.
            grouped = frame[self.column].astype(float).groupby(frame[self.by])
            agg = grouped.agg(["mean", "std", "median", "count"])
        else:
            # Weighted mean, SD and median per group; N stays the people counted.
            summaries = {}
            for value, group in frame.assign(_weight=weights.to_numpy()).groupby(self.by):
                values = pd.to_numeric(group[self.column], errors="coerce").to_numpy(dtype=float)
                summaries[value] = _weighted_summary(values, group["_weight"].to_numpy(dtype=float))
            agg = pd.DataFrame.from_dict(
                summaries, orient="index", columns=["mean", "std", "median", "count"]
            )
            agg.index.name = self.by
        agg = agg.round(3)

        # Apply group labels
        if by_labels:
            agg.index = [by_labels.get(v, str(v)) for v in agg.index]

        agg = agg.reset_index()
        by_col_label = _get_label(self.data, self.by)
        agg.columns = [by_col_label, "Mean", "SD", "Median", "N"]

        self._result = agg

        # Significance testing
        if self.test:
            groups = [g[self.column].values for _, g in frame.groupby(self.by)]
            n_groups = len(groups)

            if n_groups < 2:
                self._stats = {"note": "fewer than 2 groups, no test performed"}
            elif chosen:
                self._chosen_test(frame, by_labels, col_label)
            else:
                self._test(groups, col_scale, col_label, int(frame.shape[0]))
        if left_out:
            from siamang.data.inference import missing_codes_note

            self._stats["Missing codes left out"] = missing_codes_note(
                left_out, self.data.variables
            )
        elif not chosen:
            _counted(self._stats, self.data, frame, [self.column, self.by])
        if weights is not None:
            self._stats["Weight"] = self.data.weight
            self._stats["Note"] = "means, SD and medians are weighted; N and the test are not"

    def _test(self, groups: list, col_scale: str | None, col_label: str, n: int) -> None:
        n_groups = len(groups)
        try:
            from scipy import stats as sp_stats

            # Choose test based on scale and number of groups
            use_nonparametric = col_scale in ("ordinal", None)

            if n_groups == 2:
                if use_nonparametric:
                    stat, p = sp_stats.mannwhitneyu(groups[0], groups[1], alternative="two-sided")
                    self._stats = {"Mann-Whitney U": round(stat, 3), "p": round_p(p)}
                else:
                    stat, p = sp_stats.ttest_ind(groups[0], groups[1])
                    self._stats = {"t": round(stat, 3), "p": round_p(p)}
            else:
                if use_nonparametric:
                    stat, p = sp_stats.kruskal(*groups)
                    self._stats = {"Kruskal-Wallis H": round(stat, 3), "p": round_p(p)}
                else:
                    stat, p = sp_stats.f_oneway(*groups)
                    self._stats = {"F": round(stat, 3), "p": round_p(p)}

            self._stats["N"] = n
            self._stats["Variable"] = col_label

        except ImportError:
            self._stats = {"error": "scipy not installed"}

    def _chosen_test(self, frame: pd.DataFrame, by_labels: dict[Any, str], col_label: str) -> None:
        """The test named by ``method``, and the post-hoc pairs after it."""
        from siamang.reporting.stat_tables import means_test, posthoc_for

        samples, names = [], []
        for value, group in frame.groupby(self.by):
            samples.append(pd.to_numeric(group[self.column], errors="coerce").to_numpy(dtype=float))
            names.append(str(by_labels.get(value, value)))
        by_label = _get_label(self.data, self.by)
        self._stats = means_test(samples, names, self.method, by_label=by_label)
        if self.posthoc != "none":
            summary, self._posthoc = posthoc_for(
                self.data, samples, names, self.posthoc, adjust=self.adjust, by=self.by
            )
            self._stats.update(summary)
        self._stats["N"] = int(frame.shape[0])
        self._stats["Variable"] = col_label

    def _build_multi(self) -> None:
        """Grouped by a multiple-choice question: one row per option.

        The groups overlap — a respondent who named two barriers is in two rows
        — which is exactly the comparison people want ("how satisfied are the
        ones who mentioned price?") and exactly what makes a significance test
        invalid here. So the table gives means and bases and says why there is
        no p-value, rather than printing one that cannot mean what it looks like.
        """
        from siamang.data import multi

        series = self.data.frame[self.by]
        values = pd.to_numeric(self.data.frame[self.column], errors="coerce")
        weights = _weights_of(self.data, self.data.frame.index)
        labels = _get_value_labels(self.data, self.by)
        rows = []
        for code in labels or multi.codes_in(series):
            chose = multi.reach(series, code) & multi.responded(series) & values.notna()
            group = values[chose]
            if weights is None:
                mean = round(float(group.mean()), 3) if len(group) else None
                sd = round(float(group.std(ddof=1)), 3) if len(group) > 1 else None
                median = round(float(group.median()), 3) if len(group) else None
            else:
                w_mean, w_sd, w_median, _ = _weighted_summary(
                    group.to_numpy(dtype=float), weights[chose].to_numpy(dtype=float)
                )
                mean = round(w_mean, 3) if len(group) else None
                sd = round(w_sd, 3) if len(group) > 1 else None
                median = round(w_median, 3) if len(group) else None
            rows.append(
                {
                    _get_label(self.data, self.by): (labels or {}).get(code, str(code)),
                    "Mean": mean,
                    "SD": sd,
                    "Median": median,
                    "N": int(len(group)),
                }
            )
        self._result = pd.DataFrame(rows)
        self._stats = {
            "Variable": _get_label(self.data, self.column),
            "Base": f"{int(multi.base_size(series))} respondents",
            "Note": (
                "grouped by a multiple-choice question, so the groups overlap and "
                "no significance test is reported"
            ),
        }
        if weights is not None:
            self._stats["Weight"] = self.data.weight
            self._stats["Note"] += "; means, SD and medians are weighted, N is not"


# ─── QualityTable ─────────────────────────────────────────────────────────────


@dataclass
class QualityTable(SurveyTable):
    """How many responses each quality check flagged, and how many were clean.

    Reads the column ``prepare.quality`` wrote — one string per respondent
    naming every check they failed — and counts it by reason. A respondent who
    failed two checks appears in both rows, so the reason counts do not add up
    to the flagged total; the "Any check" row is the one that says how many
    responses are affected, and it is the number a methods section quotes.

    The percentages are of everyone screened, which is why the table is built
    before anything is dropped: "3.2 % of responses were flagged" is a fact
    about the sample, while the same count over the survivors is a fact about
    nothing.

    Parameters
    ----------
    data : SurveyData
        The screened data, with the flags column still on it.
    column : str
        The flags column, as named in the node (default ``quality_flags``).
    """

    column: str = "quality_flags"

    def _build(self) -> None:
        from siamang.data.quality import REASONS

        frame = self.data.frame
        screened = int(len(frame))
        flags = (
            frame[self.column].fillna("").astype(str)
            if self.column in frame.columns
            else pd.Series([""] * screened, dtype="object")
        )
        reasons = [str(r).split("; ") for r in flags]
        counts = {
            reason: sum(1 for parts in reasons if reason in parts)
            for reason in REASONS
            if any(reason in parts for parts in reasons)
        }
        flagged = int(sum(1 for value in flags if value))
        share = lambda n: round(n / screened * 100, 1) if screened else 0.0  # noqa: E731
        rows = [
            {"Check": reason.capitalize(), "N": n, "%": share(n)} for reason, n in counts.items()
        ]
        rows.append({"Check": "Any check", "N": flagged, "%": share(flagged)})
        rows.append({"Check": "Clean", "N": screened - flagged, "%": share(screened - flagged)})
        self._result = pd.DataFrame(rows, columns=["Check", "N", "%"])
        self._stats = {"Screened": screened, "Flagged": flagged}
        several = sum(1 for parts in reasons if len([p for p in parts if p]) > 1)
        if several:
            # Without it a reader adds the rows up: 20 straightlining and 32
            # attention read as 52 responses when they share most of them.
            self._stats["Overlap"] = (
                f"{several} {'response' if several == 1 else 'responses'} failed more than "
                "one check: counted under each, and once in Any check"
            )
        # Screening is about the responses received, not the population they
        # stand for, so the counts are of responses whatever the weight.
        if (note := _unweighted_note(self.data)) is not None:
            self._stats["Weight"] = note


# ─── Undefined cells ──────────────────────────────────────────────────────────


# ─── ThemeTable ───────────────────────────────────────────────────────────────


@dataclass
class ThemeTable(_BlankUndefined, SurveyTable):
    """What the open answers were coded as, and how much was left uncoded.

    One row per theme with its share of the answers that were coded, then two
    rows that keep the table honest: how many answers the codeframe coded and
    how many it had no theme for — answers collected after it was built, or
    simply never seen — each as a share of everyone who answered. A theme share
    quoted without them is a share of an unstated denominator. The stats carry
    the coverage and how many *different* answers are uncoded, which is the
    work a re-coding would be.

    With ``sentiment`` and a codeframe built with it, each row also splits its
    answers into negative, neutral and positive (of those with a sentiment),
    and the stats give the overall split and the net (positive minus negative).
    A codeframe without sentiment says so in the stats rather than being
    silently ignored.

    A version 2 codeframe counts respondents: each theme's row is a share of
    everyone who answered (with several themes an answer they add up to more
    than 100 %, which the stats say), a net's row — ``<group> (net)``, its
    themes under it — counts a respondent once however many of its themes they
    have, ``No theme`` counts the answers a coder decided have none, and
    ``Coded`` splits into ``Coded by hand`` and ``Coded by rules`` before
    ``Uncoded``. The stats carry the same counts.
    """

    codeframe: Any = None
    sentiment: bool = False

    def _build(self) -> None:
        from siamang.data import text_coding

        if getattr(self.codeframe, "version", 1) >= 2:
            self._build_v2()
            return
        frame = self.data.frame
        cf = self.codeframe
        series = frame[cf.variable]
        themes = text_coding.codes(series, cf)
        counts = themes.value_counts()
        cover = text_coding.coverage(frame, cf)
        answered, coded, uncoded = cover["answered"], cover["coded"], cover["uncoded"]
        share = lambda n: round(n / coded * 100, 1) if coded else 0.0  # noqa: E731
        of_answered = lambda n: round(n / answered * 100, 1) if answered else 0.0  # noqa: E731
        rows = [
            {
                "Theme": theme.label,
                "N": int(counts.get(theme.code, 0)),
                "%": share(int(counts.get(theme.code, 0))),
                "_code": theme.code,
            }
            for theme in cf.themes
        ]
        rows.sort(key=lambda row: (-row["N"], row["Theme"]))
        # The last two rows split the answers, so they are shares of everyone
        # who answered; above them a theme is a share of what was coded. (The
        # uncoded share used to be taken of the coded answers: one uncoded
        # answer in four read as 33.3 %.)
        rows.append({"Theme": "Coded", "N": coded, "%": of_answered(coded), "_code": "coded"})
        rows.append(
            {"Theme": "Uncoded", "N": uncoded, "%": of_answered(uncoded), "_code": "uncoded"}
        )
        columns = ["Theme", "N", "%"]
        self._stats = {
            "Variable": cf.variable,
            "Answered": answered,
            "Themes": len(cf.themes),
            "Coverage": f"{of_answered(coded)} % of the answers have a theme",
            "Distinct uncoded answers": int(
                text_coding.uncoded_answers(frame, cf).map(text_coding.fingerprint).nunique()
            ),
            "Percentages": "a theme: of the coded answers; Coded and Uncoded: of all answers",
        }
        if self.sentiment and cf.sentiment:
            columns += self._add_sentiment(rows, series, themes)
        elif self.sentiment:
            self._stats["Sentiment"] = "not in this codeframe"
        self._result = pd.DataFrame(rows, columns=columns)
        if cf.model:
            self._stats["Codeframe"] = f"{cf.model}{f', {cf.built_at}' if cf.built_at else ''}"
        if (note := _unweighted_note(self.data)) is not None:
            self._stats["Weight"] = note

    def theme_rows(self) -> pd.DataFrame:
        """The rows that are themes — not nets, and not the Coded, Uncoded and
        by-hand/by-rules rows under them: what a chart of the table draws."""
        self._ensure_built()
        kinds = getattr(self, "_kinds", None)
        if kinds is None:
            return self._result[~self._result["Theme"].isin(["Coded", "Uncoded"])]
        return self._result[[kind == "theme" for kind in kinds]]

    def _build_v2(self) -> None:
        """A version 2 codeframe: a row per theme and per net, shares of the
        respondents who answered; then Coded (by hand and by the rules) and
        Uncoded."""
        from siamang.data import text_coding

        frame = self.data.frame
        cf = self.codeframe
        series = frame[cf.variable]
        coded = text_coding.coding(series, cf)
        counts = text_coding.tally(coded)
        answered = counts["answered"]
        of_answered = lambda n: round(n / answered * 100, 1) if answered else 0.0  # noqa: E731
        have = [set(item.codes or ()) for item in coded]
        rows: list[dict[str, Any]] = []
        kinds: list[str] = []
        masks: list[pd.Series] = []

        def row(label: str, kind: str, mask: list[bool]) -> None:
            n = int(sum(mask))
            rows.append({"Theme": label, "N": n, "%": of_answered(n)})
            kinds.append(kind)
            masks.append(pd.Series(mask, index=series.index, dtype=bool))

        def count(code: int) -> int:
            return int(sum(code in got for got in have))

        # A net and its themes stay together; the nets and the themes in no net
        # are ordered by their counts, and so are the themes inside a net.
        nets = cf.nets
        in_net = {code for members in nets.values() for code in members}
        labels = cf.labels
        blocks: list[tuple[int, str, tuple[int, ...] | None, int | None]] = []
        for name, members in nets.items():
            n = int(sum(bool(got.intersection(members)) for got in have))
            blocks.append((n, f"{name} (net)", members, None))
        for theme in cf.themes:
            if theme.code not in in_net:
                blocks.append((count(theme.code), theme.label, None, theme.code))
        blocks.sort(key=lambda block: (-block[0], block[1]))
        for _, label, members, code in blocks:
            if members is None:
                row(label, "theme", [code in got for got in have])
                continue
            row(label, "net", [bool(got.intersection(members)) for got in have])
            for member in sorted(members, key=lambda c: (-count(c), labels[c])):
                row(labels[member], "theme", [member in got for got in have])
        # A coder's "no theme" is a decision, not a gap: its own row, in Coded.
        none = [item.source == "hand" and not item.codes for item in coded]
        if any(none):
            row("No theme", "none", none)
        row("Coded", "coded", [item.source in ("hand", "rule") for item in coded])
        row("Coded by hand", "hand", [item.source == "hand" for item in coded])
        row("Coded by rules", "rules", [item.source == "rule" for item in coded])
        row("Uncoded", "uncoded", [item.source == "uncoded" for item in coded])
        self._kinds = kinds
        columns = ["Theme", "N", "%"]
        uncoded = {
            text_coding.fingerprint(value)
            for value, item in zip(series, coded, strict=True)
            if item.source == "uncoded"
        }
        percentages = "of the respondents who answered"
        if cf.multiple:
            percentages += (
                "; a respondent can have several themes, so the themes add up to more than 100 %"
            )
        self._stats = {
            "Variable": cf.variable,
            "Answered": answered,
            "Themes": len(cf.themes),
            "Coverage": f"{of_answered(counts['coded'])} % of the answers are coded",
            "Coded by hand": counts["by_hand"],
            "Coded by rules": counts["by_rules"],
            "Distinct uncoded answers": len(uncoded),
            "Percentages": percentages,
        }
        if nets:
            self._stats["Nets"] = (
                "a net counts a respondent once, however many of its themes they have"
            )
        if self.sentiment and cf.sentiment:
            answered_mask = pd.Series(
                [item.source != "blank" for item in coded], index=series.index, dtype=bool
            )
            columns += self._sentiment_split(rows, masks, series, answered_mask)
        elif self.sentiment:
            self._stats["Sentiment"] = "not in this codeframe"
        self._result = pd.DataFrame(rows, columns=columns)
        if cf.model:
            self._stats["Codeframe"] = f"{cf.model}{f', {cf.built_at}' if cf.built_at else ''}"
        if (note := _unweighted_note(self.data)) is not None:
            self._stats["Weight"] = note

    def _add_sentiment(
        self, rows: list[dict[str, Any]], series: pd.Series, themes: pd.Series
    ) -> list[str]:
        """Negative / neutral / positive per row, of the answers with a sentiment."""
        from siamang.data import text_coding

        answered = series.map(lambda v: text_coding.normalise(v) != "")
        masks = {
            "coded": themes.notna() & answered,
            "uncoded": themes.isna() & answered,
        }
        row_masks: list[Any] = []
        for row in rows:
            code = row.pop("_code")
            mask = masks.get(code) if isinstance(code, str) else (themes == code).fillna(False)
            row_masks.append(mask)
        return self._sentiment_split(rows, row_masks, series, answered)

    def _sentiment_split(
        self,
        rows: list[dict[str, Any]],
        row_masks: list[Any],
        series: pd.Series,
        answered: pd.Series,
    ) -> list[str]:
        from siamang.data import text_coding

        scores = text_coding.sentiment_scores(series, self.codeframe)
        names = {-1: "Negative %", 0: "Neutral %", 1: "Positive %"}
        for row, mask in zip(rows, row_masks, strict=True):
            scored = scores[mask.astype(bool)].dropna()
            for value, name in names.items():
                row[name] = (
                    round(float((scored == value).sum()) / len(scored) * 100, 1)
                    if len(scored)
                    else float("nan")
                )
        overall = scores[answered.astype(bool)].dropna()
        if len(overall):
            split = {value: float((overall == value).sum()) / len(overall) * 100 for value in names}
            self._stats["Sentiment"] = (
                f"negative {split[-1]:.1f} %, neutral {split[0]:.1f} %, "
                f"positive {split[1]:.1f} % of {len(overall)} answer"
                + ("" if len(overall) == 1 else "s")
            )
            self._stats["Net sentiment"] = round(split[1] - split[-1], 1)
        else:
            self._stats["Sentiment"] = "no answer here has a sentiment in the codeframe"
        return list(names.values())


# ─── MaxDiffTable ─────────────────────────────────────────────────────────────


@dataclass
class MaxDiffTable(SurveyTable):
    """What a best–worst question found, with the base it found it on.

    One row per item, ordered best first. ``Score`` is the counting score — best
    minus worst over shown — which anyone can recount from the data by hand.
    ``Utility`` is the conditional-logit estimate, on an interval scale so the
    distance between two items means something, and ``Share`` is that utility
    as the percentage of picks the item would take if every item were offered
    at once. The two orders normally agree; when they do not, the utilities are
    the ones to trust, because they know which items each pick was made against.

    The footer carries the base and the estimation method, because a preference
    order without them is not a finding, and it names the reference item, since
    utilities are read against one.

    On weighted data every column is weighted — Shown, Best and Worst are sums
    of weights, and the utilities are fitted on the weighted choices — and the
    footer names the weight and gives the weighted base beside the people.
    """

    question: Any = None
    method: str = "both"

    def _build(self) -> None:
        from siamang.data import maxdiff

        question = maxdiff.question_of(self.data, self.question)
        read = maxdiff.answers(self.data, question)
        counts = maxdiff.counts(self.data, question)
        frame = counts.rename(
            columns={
                "label": "Item",
                "shown": "Shown",
                "best": "Best",
                "worst": "Worst",
                "score": "Score",
            }
        )[["Item", "Shown", "Best", "Worst", "Score"]]

        stats: dict[str, Any] = {
            "Question": question.text,
            "Base": _base(self.data, read.respondents, question.version_variable.name),
            "Tasks read": int(len(read.frame)),
        }
        if self.data.weight is not None:
            stats["Weight"] = self.data.weight
        if self.method in {"utilities", "both"}:
            result = maxdiff.utilities(self.data, question)
            utility = dict(zip(result.table["term"], result.table["estimate"], strict=True))
            share = dict(zip(result.table["term"], result.table["share"], strict=True))
            frame["Utility"] = [utility.get(item, 0.0) for item in frame["Item"]]
            frame["Share %"] = [share.get(item, 0.0) for item in frame["Item"]]
            frame = frame.sort_values("Utility", ascending=False).reset_index(drop=True)
            stats["Method"] = "counting score and conditional logit"
            stats["Reference"] = result.stats.get("reference", "")
            stats["Pseudo R²"] = result.stats.get("pseudo_r2", 0.0)
            if not result.stats.get("converged", True):
                stats["Warning"] = "the model did not converge; read the utilities with care"
        else:
            stats["Method"] = "counting score"

        if read.dropped:
            # Answers that cannot be read against the design are named, not
            # dropped quietly: an item picked that its task never showed means
            # the design changed after fieldwork, which is a finding of its own.
            stats["Unreadable answers"] = f"{read.dropped} ({_reasons(read.reasons)})"
        self._result = frame
        self._stats = stats


def _reasons(reasons: dict[str, int]) -> str:
    return ", ".join(f"{reason}: {count}" for reason, count in reasons.items())


def _base(data: SurveyData, respondents: int, version: str) -> str:
    """The base: the respondents, and their weighted total when the data is weighted.

    A choice question's base is everyone with a design version, the same rows
    its reader counts as respondents.
    """
    if data.weight is None:
        return f"{respondents} respondents"
    frame = data.frame
    weights = _weights_of(data, frame.index[frame[version].notna()])
    total = float(weights.sum()) if weights is not None else 0.0
    return f"{respondents} respondents ({_round_base(total)} weighted)"


# ─── ConjointTable ────────────────────────────────────────────────────────────


@dataclass
class ConjointTable(SurveyTable):
    """What a conjoint found: every level's worth and every attribute's weight.

    Two tables in one, because they are read together. ``Part-worth`` is what a
    level is worth in a currency shared across all attributes, against the first
    level of its own attribute at zero. ``Importance`` is the share of the
    decision the attribute accounted for — the range of its part-worths over all
    the ranges — and it is repeated on each of that attribute's rows so the
    table can be sorted without losing it.

    Importance means what it says only for the levels that were shown. Price
    tested from £10 to £12 will look unimportant beside price tested from £10 to
    £100, and that is a fact about the design; the footer says so rather than
    leaving a client to infer a market truth from a design decision.

    On weighted data the part-worths, and so the importances, are fitted on the
    weighted choices; the footer names the weight and the weighted base.
    """

    question: Any = None

    def _build(self) -> None:
        from siamang.data import conjoint

        question = conjoint.question_of(self.data, self.question)
        read = conjoint.answers(self.data, question)
        result = conjoint.part_worths(self.data, question)
        weights = conjoint.importance(self.data, question)
        estimate = dict(zip(result.table["term"], result.table["estimate"], strict=True))
        by_attribute = dict(zip(weights["attribute"], weights["importance"], strict=True))

        rows = []
        for attribute in question.attributes:
            name = attribute.label or attribute.name
            for position, level in enumerate(attribute.levels):
                term = f"{name}: {level.label}"
                rows.append(
                    {
                        "Attribute": name,
                        "Level": level.label,
                        "Part-worth": 0.0 if position == 0 else round(estimate.get(term, 0.0), 4),
                        "Importance %": by_attribute.get(name, 0.0),
                    }
                )
        frame = pd.DataFrame(rows, columns=["Attribute", "Level", "Part-worth", "Importance %"])
        order = {name: i for i, name in enumerate(weights["attribute"])}
        frame = (
            frame.assign(_o=frame["Attribute"].map(order))
            .sort_values(["_o", "Part-worth"], ascending=[True, False])
            .drop(columns="_o")
            .reset_index(drop=True)
        )

        stats: dict[str, Any] = {
            "Question": question.text,
            "Base": _base(self.data, read.respondents, question.version_variable.name),
            "Tasks read": int(len(read.frame)),
            "Method": "conditional logit (aggregate)",
            "Reference": result.stats.get("reference", ""),
            "Pseudo R²": result.stats.get("pseudo_r2", 0.0),
            "Note": ("importance is of the levels tested, not of the attribute in general"),
        }
        if self.data.weight is not None:
            stats["Weight"] = self.data.weight
        if not result.stats.get("converged", True):
            stats["Warning"] = "the model did not converge; read the part-worths with care"
        if read.dropped:
            stats["Unreadable answers"] = f"{read.dropped} ({_reasons(read.reasons)})"
        self._result = frame
        self._stats = stats


# ─── ShareTable ───────────────────────────────────────────────────────────────


@dataclass
class ShareTable(SurveyTable):
    """What the conjoint's part-worths predict a market of these products would do.

    The rows are :func:`siamang.data.conjoint.shares` unchanged — ``product``,
    ``utility`` and ``share`` — and the footer says what they rest on: the
    base, the model, and on weighted data the weight the part-worths were
    fitted with, so a share never looks like a count of anyone.
    """

    question: Any = None
    products: Any = None
    include_none: bool = False

    def _build(self) -> None:
        from siamang.data import conjoint

        question = conjoint.question_of(self.data, self.question)
        read = conjoint.answers(self.data, question)
        self._result = conjoint.shares(
            self.data, question, self.products, include_none=self.include_none
        )
        stats: dict[str, Any] = {
            "Question": question.text,
            "Base": _base(self.data, read.respondents, question.version_variable.name),
            "Method": "logit rule on aggregate conditional-logit part-worths",
            "Note": (
                "shares of the products listed"
                + (" and of choosing none" if self.include_none else "")
                + ", not market shares"
            ),
        }
        if self.data.weight is not None:
            stats["Weight"] = self.data.weight
        self._stats = stats


# ─── BannerTable ──────────────────────────────────────────────────────────────


#: Columns get letters so a cell can say which other columns it beats. They run
#: across the whole banner (A, B, C, …) rather than restarting per block, so a
#: letter identifies a column uniquely in the table.
_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


@dataclass
class BannerTable(SurveyTable):
    """The cross-break: several questions down, several breakdowns across.

    The workhorse of agency reporting, and the reason is the shape — one page
    that answers "how does this differ by region, by age, by segment" without
    flipping between tables. :meth:`SurveyData.tables.banner` produces the same
    numbers in tidy form, one row per pair, for feeding to something else; this
    is the one meant to be read.

    Each cell is a column percentage with its count, and — when ``test`` is on —
    the letters of the columns it is significantly higher than. Comparisons are
    made **within a banner variable only**: its columns are mutually exclusive
    groups of the same people, which is what the test assumes. Columns from
    different banner variables overlap (a northerner is also under 35), so
    comparing them would be arithmetic without a meaning, and the table does not
    offer it.

    Three things are said in ``stats`` rather than assumed, because each of them
    changes what a letter means: the test and its level, whether a multiple-
    comparison correction was applied, and — on weighted data — that the base is
    Kish's effective sample size rather than the raw count. Weights make a
    sample behave like a smaller one; testing on the raw n would manufacture
    significance.
    """

    rows: list[str] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)
    weight: str | None = None
    test: bool = True
    level: float = 0.05
    correction: str = "none"
    #: A column with fewer than this many (effective) respondents takes no part
    #: in testing: a headline difference computed off seven people is noise with
    #: a letter beside it.
    min_base: int = 30

    def _build(self) -> None:
        import numpy as np

        from siamang.data.tables import _banner_pair

        if not self.rows:
            raise ValueError("A banner needs at least one row variable.")
        if not self.columns:
            raise ValueError("A banner needs at least one banner variable.")
        if self.correction not in {"none", "bonferroni"}:
            raise ValueError("correction must be 'none' or 'bonferroni'")

        frame = self.data.frame
        weight_column = self.weight or self.data.weight
        if weight_column is not None and weight_column not in frame.columns:
            raise ValueError(f"Weight column '{weight_column}' not found in frame.")

        # Column headers, in order, with their letters: one block per banner
        # variable, one column per value of it.
        blocks: list[list[tuple[str, Any, str]]] = []  # (variable, value, header)
        letters: dict[tuple[str, Any], str] = {}
        index = 0
        for variable in self.columns:
            values = self._values_of(variable)
            block: list[tuple[str, Any, str]] = []
            for value in values:
                letter = column_letter(index)
                label = _get_value_labels(self.data, variable).get(value, value)
                header = f"{_get_label(self.data, variable)}: {label} ({letter})"
                letters[(variable, value)] = letter
                block.append((variable, value, header))
                index += 1
            blocks.append(block)
        headers = [header for block in blocks for _var, _val, header in block]

        # Bases: the weighted total per column, and the effective base the test
        # uses. Unweighted they are the same number.
        bases: dict[tuple[str, Any], float] = {}
        effective: dict[tuple[str, Any], float] = {}
        for variable in self.columns:
            for value in self._values_of(variable):
                mask = frame[variable] == value
                if weight_column is None:
                    total = float(mask.sum())
                    bases[(variable, value)] = total
                    effective[(variable, value)] = total
                    continue
                weights = pd.to_numeric(frame.loc[mask, weight_column], errors="coerce").dropna()
                total = float(weights.sum())
                squared = float((weights**2).sum())
                bases[(variable, value)] = total
                effective[(variable, value)] = (total**2 / squared) if squared > 0 else 0.0

        records: list[dict[str, Any]] = []
        records.append(
            {
                "Question": "Base",
                "Answer": "respondents",
                **{
                    header: _round_base(bases[(variable, value)])
                    for block in blocks
                    for variable, value, header in block
                },
            }
        )

        tested = 0
        for row_variable in self.rows:
            # One shared computation per (row, column) pair: the same helper the
            # tidy accessor uses, so the two can never disagree about a number.
            shares: dict[tuple[Any, str, Any], float] = {}
            counts: dict[tuple[Any, str, Any], float] = {}
            for column_variable in self.columns:
                pair = _banner_pair(
                    frame,
                    row_variable,
                    column_variable,
                    weight_column,
                    self.data.variables,
                    labels=True,
                )
                for record in pair.to_dict("records"):
                    key = (record["row_value"], column_variable, record["column_value"])
                    shares[key] = float(record["percent"])
                    counts[key] = float(record["n"])

            row_labels = _get_value_labels(self.data, row_variable)
            for row_value in self._values_of(row_variable):
                cells: dict[str, Any] = {}
                for block in blocks:
                    marks = self._letters_for(block, row_value, shares, effective, letters, np)
                    tested += len(block) if self.test else 0
                    for variable, value, header in block:
                        key = (row_value, variable, value)
                        share = shares.get(key, 0.0) * 100
                        count = counts.get(key, 0.0)
                        mark = marks.get((variable, value), "")
                        cells[header] = f"{share:.1f}% ({_round_base(count)})" + (
                            f" {mark}" if mark else ""
                        )
                records.append(
                    {
                        "Question": _get_label(self.data, row_variable),
                        "Answer": str(row_labels.get(row_value, row_value)),
                        **cells,
                    }
                )

        self._result = pd.DataFrame(records, columns=["Question", "Answer", *headers])

        thin = sorted(
            {
                letters[key]
                for key, value in effective.items()
                if value < self.min_base and self.test
            }
        )
        stats: dict[str, Any] = {
            "Rows": ", ".join(_get_label(self.data, name) for name in self.rows),
            "Banner": ", ".join(_get_label(self.data, name) for name in self.columns),
            "Percentages": "of the column",
        }
        if self.test:
            stats["Test"] = (
                f"two-sided z-test of column proportions at {self.level:g}, "
                f"within each banner variable only"
            )
            stats["Correction"] = (
                "Bonferroni, within each banner variable"
                if self.correction == "bonferroni"
                else "none (columns are compared pairwise)"
            )
        else:
            stats["Test"] = "not run"
        if weight_column is not None:
            stats["Weight"] = weight_column
            stats["Base"] = "effective (Kish) where a test was run; weighted counts shown"
        if thin:
            stats["Not tested"] = (
                f"columns {', '.join(thin)} — fewer than {self.min_base} respondents"
            )
        self._stats = stats

    def _values_of(self, variable: str) -> list[Any]:
        """The values of a variable, in codebook order where the codebook has one."""
        return banner_values(self.data.frame[variable], _get_value_labels(self.data, variable))

    def _letters_for(
        self,
        block: list[tuple[str, Any, str]],
        row_value: Any,
        shares: dict[tuple[Any, str, Any], float],
        effective: dict[tuple[str, Any], float],
        letters: dict[tuple[str, Any], str],
        np: Any,
    ) -> dict[tuple[str, Any], str]:
        """Which columns of this block each column is significantly higher than."""
        if not self.test or len(block) < 2:
            return {}
        keys = [(variable, value) for variable, value, _header in block]
        return proportion_letters(
            {key: shares.get((row_value, *key), 0.0) for key in keys},
            {key: effective[key] for key in keys},
            {key: letters[key] for key in keys},
            level=self.level,
            correction=self.correction,
            min_base=self.min_base,
        )


def banner_values(series: pd.Series, labels: dict[Any, Any]) -> list[Any]:
    """The values of a banner variable as its columns are ordered: the
    codebook's labeled ones in its order, then the others by their text.

    The Banner table's and the Tab book's order, which their letters follow
    (:func:`column_letter`); a Bar chart split by the variable names its groups
    by the same letters.
    """
    present = series.dropna().unique().tolist()
    ordered = [value for value in labels if value in present]
    ordered += [value for value in sorted(present, key=str) if value not in ordered]
    return ordered


def column_letter(index: int) -> str:
    """The letter of the banner's ``index``-th column (from 0): A–Z, then #27 …"""
    return _LETTERS[index] if index < len(_LETTERS) else f"#{index + 1}"


def proportion_letters(
    shares: dict[Any, float],
    bases: dict[Any, float],
    letters: dict[Any, str],
    *,
    level: float = 0.05,
    correction: str = "none",
    min_base: float = 30,
) -> dict[Any, str]:
    """Which columns each column's share is significantly higher than.

    The Banner table's test, shared with the Tab book and the Bar chart's
    significance letters: a two-sided z-test of two column proportions with
    the pooled variance, on each column's (effective) base, for every pair of
    columns of one banner variable. ``shares`` are fractions (0–1) and
    ``bases`` the bases the test uses — Kish's effective base when weighted —
    keyed alike, and ``letters`` names each column. A column whose base is
    below ``min_base`` takes no part; ``correction="bonferroni"`` divides the
    level by the number of pairs tested. Returns each column's letters, sorted,
    for the columns that beat another.
    """
    import numpy as np
    from scipy import stats as scipy_stats

    eligible = [key for key in letters if bases[key] >= min_base]
    if len(eligible) < 2:
        return {}
    alpha = level
    if correction == "bonferroni":
        comparisons = len(eligible) * (len(eligible) - 1) / 2
        alpha = level / comparisons if comparisons else level

    beats: dict[Any, list[str]] = {key: [] for key in eligible}
    for i, left in enumerate(eligible):
        for right in eligible[i + 1 :]:
            p1 = shares.get(left, 0.0)
            p2 = shares.get(right, 0.0)
            n1, n2 = bases[left], bases[right]
            pooled = (p1 * n1 + p2 * n2) / (n1 + n2)
            variance = pooled * (1 - pooled) * (1 / n1 + 1 / n2)
            if variance <= 0:
                continue
            z = (p1 - p2) / float(np.sqrt(variance))
            p_value = 2 * (1 - scipy_stats.norm.cdf(abs(z)))
            if p_value >= alpha:
                continue
            winner, loser = (left, right) if p1 > p2 else (right, left)
            beats[winner].append(letters[loser])
    return {key: "".join(sorted(marks)) for key, marks in beats.items() if marks}


def _round_base(value: float) -> int | float:
    """Weighted counts are fractional; a base of 41.0 should read as 41."""
    return int(round(value)) if abs(value - round(value)) < 1e-9 else round(value, 1)
