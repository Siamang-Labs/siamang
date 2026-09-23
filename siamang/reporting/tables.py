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


def _weighted_summary(values: np.ndarray, weights: np.ndarray) -> tuple[float, float, float, int]:
    """Weighted mean, SD and median of ``values``, and their unweighted count.

    The SD is the weighted variance scaled by n / (n - 1), so equal weights give
    exactly the sample SD the unweighted table shows. The median is the value at
    which the cumulative weight first reaches half the total.
    """
    n = int(len(values))
    total = float(weights.sum())
    if n == 0 or total <= 0:
        return float("nan"), float("nan"), float("nan"), n
    mean = float(np.average(values, weights=weights))
    if n > 1:
        variance = float(np.average((values - mean) ** 2, weights=weights)) * n / (n - 1)
        sd = variance**0.5
    else:
        sd = float("nan")
    order = np.argsort(values, kind="stable")
    cumulative = np.cumsum(weights[order])
    at = min(int(np.searchsorted(cumulative, total / 2.0)), n - 1)
    return mean, sd, float(values[order][at]), n


def _get_scale(data: SurveyData, var_name: str) -> str | None:
    """Get measurement scale for a variable."""
    if data.variables and var_name in data.variables:
        return data.variables[var_name].scale
    return None


def _frame_to_markdown(df: pd.DataFrame) -> str:
    """Convert a DataFrame to a GitHub-flavored Markdown pipe table."""
    lines = []
    headers = list(df.columns)
    lines.append("| " + " | ".join(str(h) for h in headers) + " |")
    lines.append("|" + "|".join("---" for _ in headers) + "|")
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(v) for v in row.values) + " |")
    return "\n".join(lines)


def frame_to_html(df: pd.DataFrame, caption: str | None = None) -> str:
    """Convert a DataFrame to a clean HTML table.

    Public because a report renders bare DataFrames through the same path as
    its table components, so every table in a document carries the same class
    and the stylesheet has one thing to style.
    """
    html = df.to_html(index=False, classes="siamang-table", border=0)
    if caption:
        html = html.replace("<table", f"<caption>{caption}</caption>\n<table", 1)
    return html


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

    def to_markdown(self) -> str:
        """Return the table as a GitHub-flavored Markdown string."""
        self._ensure_built()
        md = _frame_to_markdown(self._result)
        if self._stats:
            md += "\n\n" + self._format_stats()
        return md

    def to_html(self) -> str:
        """Return the table as an HTML string."""
        self._ensure_built()
        html = _frame_to_html(self._result)
        if self._stats:
            html += f"\n<p class='siamang-stats'>{self._format_stats()}</p>"
        return html

    def export_xlsx(self, path: str | Path) -> Path:
        """Export the table to an Excel file."""
        self._ensure_built()
        path = Path(path)
        self._result.to_excel(path, index=False, sheet_name="Table")
        return path

    def _format_stats(self) -> str:
        """Format statistics footer."""
        parts = []
        for key, val in self._stats.items():
            if isinstance(val, float):
                parts.append(f"{key} = {val:.4f}")
            else:
                parts.append(f"{key} = {val}")
        return "; ".join(parts)

    def __repr__(self) -> str:
        self._ensure_built()
        return self._result.to_string()

    def _repr_html_(self) -> str:
        """Jupyter notebook HTML representation."""
        return self.to_html()


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
        for value in sorted(counts.index):
            n = int(counts[value])
            label = value_labels.get(value, str(value))
            row: dict[str, Any] = {"Value": value, "Label": label, "N": n}
            if weighted is not None:
                row["N"] = round(float(weighted.get(value, 0.0)), 1)
                row["Unweighted N"] = n
            rows.append(row)

        columns = ["Value", "Label", "N"] + (["Unweighted N"] if weighted is not None else [])
        if rows:
            df = pd.DataFrame(rows, columns=columns)
        else:
            df = pd.DataFrame(columns=columns)

        if self.sort == "freq" and not df.empty:
            df = df.sort_values("N", ascending=False).reset_index(drop=True)
        elif self.sort == "label" and not df.empty:
            df = df.sort_values("Label").reset_index(drop=True)

        total = float(df["N"].sum()) if not df.empty else 0.0
        n_valid = int(counts.sum())
        df["%"] = (df["N"] / total * 100).round(1) if total > 0 else 0.0
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
        rows = []
        shares: dict[str, float] = {}
        for label, lo, hi in self.GROUPS:
            mask = (values >= lo) & (values <= hi)
            share = float(weights[mask].sum()) / total_w * 100 if total_w > 0 else 0.0
            shares[label] = share
            rows.append(
                {"Group": label, "Range": f"{lo}–{hi}", "N": int(mask.sum()), "%": round(share, 1)}
            )
        rows.append({"Group": "Total", "Range": "0–10", "N": n, "%": 100.0 if n else 0.0})
        self._result = pd.DataFrame(rows, columns=["Group", "Range", "N", "%"])

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


# ─── CrossTable ───────────────────────────────────────────────────────────────


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
        If True, runs Chi-square test and reports chi2, df, p, Cramer's V.
    """

    row: str = ""
    col: str = ""
    pct: str = "none"
    test: bool = True

    def _build(self) -> None:
        from siamang.data import multi

        if multi.is_multi(self.data.frame[self.row]):
            self._build_multi()
            return
        frame = self.data.frame[[self.row, self.col]].dropna()
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

        # Add row/column totals
        row_totals = contingency.sum(axis=1).values
        total_col = list(contingency.sum(axis=0).values) + [contingency.values.sum()]
        if weights is not None:
            row_totals = np.round(row_totals, 1)
            total_col = [round(float(value), 1) for value in total_col]
        display["Total"] = row_totals
        display.loc["Total"] = total_col[: len(display.columns)]

        # Reset index for clean output
        display = display.reset_index()
        display = display.rename(columns={"index": _get_label(self.data, self.row)})

        self._result = display

        # Statistical tests
        if self.test:
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
                chi2_stat, p_value, dof, _ = chi2_contingency(table)
                n = table.sum()
                min_dim = min(contingency.shape[0] - 1, contingency.shape[1] - 1)
                cramers_v = (chi2_stat / (n * min_dim)) ** 0.5 if n > 0 and min_dim > 0 else 0.0
                self._stats = {
                    "χ²": round(chi2_stat, 3),
                    "df": int(dof),
                    "p": round(p_value, 4),
                    "Cramér's V": round(cramers_v, 3),
                    "N": int(frame.shape[0]),
                }
                if weights is not None:
                    self._stats["Weighted N"] = round(total_w, 1)
                    self._stats["Effective N"] = round(n_eff, 1)
                    self._stats["Weight"] = self.data.weight
                    self._stats["Base"] = "effective (Kish) for the test; weighted counts shown"
            except ImportError:
                self._stats = {"error": "scipy not installed"}

    def _build_multi(self) -> None:
        """A multiple-choice question against a group: reach within each column.

        Percentages are of each group's own base, which is the number a reader
        compares across columns. No chi-square: the categories overlap, so the
        test's independence assumption does not hold and a p-value here would be
        a number that looks like evidence and is not.
        """
        from siamang.data import multi

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
        display = table.drop(columns=["value"]).rename(
            columns={"label": _get_label(self.data, self.row)}
        )
        bases = table.base if isinstance(table.base, dict) else {}
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
            "Base": ", ".join(f"{group}: {size}" for group, size in bases.items()),
            "Note": (
                "multiple answers allowed; percentages are of each group, and no "
                "chi-square is reported because the categories overlap"
            ),
        }
        if weight is not None:
            self._stats["Base"] += " (weighted)"
            self._stats["Weight"] = weight


# ─── GroupMeanTable ───────────────────────────────────────────────────────────


@dataclass
class GroupMeanTable(SurveyTable):
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
        If True, automatically runs the appropriate significance test:
        - 2 groups: Mann-Whitney U (ordinal) or Independent t-test (interval/ratio)
        - 3+ groups: Kruskal-Wallis H (ordinal) or One-way ANOVA (interval/ratio)
    """

    column: str = ""
    by: str = ""
    test: bool = True

    def _build(self) -> None:
        from siamang.data import multi

        if multi.is_multi(self.data.frame[self.by]):
            self._build_multi()
            return
        frame = self.data.frame[[self.column, self.by]].dropna()
        by_labels = _get_value_labels(self.data, self.by)
        col_label = _get_label(self.data, self.column)
        col_scale = _get_scale(self.data, self.column)

        weights = _weights_of(self.data, frame.index)
        if weights is None:
            grouped = frame.groupby(self.by)[self.column]
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
            else:
                self._test(groups, col_scale, col_label, int(frame.shape[0]))
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
                    self._stats = {"Mann-Whitney U": round(stat, 3), "p": round(p, 4)}
                else:
                    stat, p = sp_stats.ttest_ind(groups[0], groups[1])
                    self._stats = {"t": round(stat, 3), "p": round(p, 4)}
            else:
                if use_nonparametric:
                    stat, p = sp_stats.kruskal(*groups)
                    self._stats = {"Kruskal-Wallis H": round(stat, 3), "p": round(p, 4)}
                else:
                    stat, p = sp_stats.f_oneway(*groups)
                    self._stats = {"F": round(stat, 3), "p": round(p, 4)}

            self._stats["N"] = n
            self._stats["Variable"] = col_label

        except ImportError:
            self._stats = {"error": "scipy not installed"}

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


# ─── ThemeTable ───────────────────────────────────────────────────────────────


@dataclass
class ThemeTable(SurveyTable):
    """What the open answers were coded as, and how much was left uncoded.

    One row per theme with its share of the answers that were coded, then two
    rows that keep the table honest: how many people answered at all, and how
    many of those the codeframe had no theme for — answers collected after it
    was built, or simply never seen. A theme share quoted without them is a
    share of an unstated denominator.

    The percentages are of coded answers, because that is what a theme can be a
    share of; "answered" and "uncoded" are counts for the same reason.
    """

    codeframe: Any = None

    def _build(self) -> None:
        from siamang.data import text_coding

        frame = self.data.frame
        cf = self.codeframe
        counts = text_coding.codes(frame[cf.variable], cf).value_counts()
        cover = text_coding.coverage(frame, cf)
        coded = cover["coded"]
        share = lambda n: round(n / coded * 100, 1) if coded else 0.0  # noqa: E731
        rows = [
            {
                "Theme": theme.label,
                "N": int(counts.get(theme.code, 0)),
                "%": share(int(counts.get(theme.code, 0))),
            }
            for theme in cf.themes
        ]
        rows.sort(key=lambda row: (-row["N"], row["Theme"]))
        rows.append({"Theme": "Coded", "N": coded, "%": 100.0 if coded else 0.0})
        rows.append({"Theme": "Uncoded", "N": cover["uncoded"], "%": share(cover["uncoded"])})
        self._result = pd.DataFrame(rows, columns=["Theme", "N", "%"])
        self._stats = {
            "Variable": cf.variable,
            "Answered": cover["answered"],
            "Themes": len(cf.themes),
        }
        if cf.model:
            self._stats["Codeframe"] = f"{cf.model}{f', {cf.built_at}' if cf.built_at else ''}"


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
            "Base": f"{read.respondents} respondents",
            "Tasks read": int(len(read.frame)),
        }
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
            "Base": f"{read.respondents} respondents",
            "Tasks read": int(len(read.frame)),
            "Method": "conditional logit (aggregate)",
            "Reference": result.stats.get("reference", ""),
            "Pseudo R²": result.stats.get("pseudo_r2", 0.0),
            "Note": ("importance is of the levels tested, not of the attribute in general"),
        }
        if not result.stats.get("converged", True):
            stats["Warning"] = "the model did not converge; read the part-worths with care"
        if read.dropped:
            stats["Unreadable answers"] = f"{read.dropped} ({_reasons(read.reasons)})"
        self._result = frame
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
                letter = _LETTERS[index] if index < len(_LETTERS) else f"#{index + 1}"
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
        present = self.data.frame[variable].dropna().unique().tolist()
        declared = list(_get_value_labels(self.data, variable))
        ordered = [value for value in declared if value in present]
        ordered += [value for value in sorted(present, key=str) if value not in ordered]
        return ordered

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
        eligible = [
            (variable, value)
            for variable, value, _header in block
            if effective[(variable, value)] >= self.min_base
        ]
        if len(eligible) < 2:
            return {}
        alpha = self.level
        if self.correction == "bonferroni":
            comparisons = len(eligible) * (len(eligible) - 1) / 2
            alpha = self.level / comparisons if comparisons else self.level

        from scipy import stats as scipy_stats

        beats: dict[tuple[str, Any], list[str]] = {key: [] for key in eligible}
        for i, left in enumerate(eligible):
            for right in eligible[i + 1 :]:
                p1 = shares.get((row_value, *left), 0.0)
                p2 = shares.get((row_value, *right), 0.0)
                n1, n2 = effective[left], effective[right]
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
