"""Declarative chart components for survey reporting.

Each chart class auto-resolves variable labels and value labels from the
attached SurveyData metadata, producing publication-ready figures with
minimal configuration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

if TYPE_CHECKING:
    from siamang.data.survey_data import SurveyData

try:
    import matplotlib
    import matplotlib.pyplot as plt

    matplotlib.rcParams["figure.dpi"] = 100
except ImportError:
    plt = None

try:
    import seaborn as sns
except ImportError:
    sns = None


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _get_label(data: SurveyData, var_name: str) -> str:
    if data.variables and var_name in data.variables:
        return data.variables[var_name].label or var_name
    return var_name


def _get_value_labels(data: SurveyData, var_name: str) -> dict[Any, str]:
    if data.variables and var_name in data.variables:
        return data.variables[var_name].labels or {}
    return {}


def _get_scale(data: SurveyData, var_name: str) -> str | None:
    if data.variables and var_name in data.variables:
        return data.variables[var_name].scale
    return None


def _weights(data: SurveyData, index: pd.Index) -> pd.Series | None:
    """The weight of each row in ``index``, or None when the data is unweighted.

    Same resolution as the tables (``SurveyData.with_weight``, the flow's Apply
    weight node): a weight that is missing or not a number counts 0.
    """
    column = data.weight
    if column is None:
        return None
    if column not in data.frame.columns:
        raise ValueError(f"Weight column '{column}' not found in frame.")
    weights: pd.Series = pd.to_numeric(data.frame.loc[index, column], errors="coerce")
    return weights.fillna(0.0).astype(float)


def _weighted_means(
    frame: pd.DataFrame, columns: list[str], by: str, weights: pd.Series
) -> pd.DataFrame:
    """Weighted mean of each of ``columns`` per value of ``by`` (rows complete)."""
    rows = {}
    for value, group in frame.assign(_w=weights.to_numpy()).groupby(by):
        total = float(group["_w"].sum())
        rows[value] = {
            column: float((group[column].astype(float) * group["_w"]).sum() / total)
            if total > 0
            else float("nan")
            for column in columns
        }
    return pd.DataFrame.from_dict(rows, orient="index", columns=columns)


def _format_value(value: float) -> str:
    """A bar's label: whole counts as integers, weighted ones to one decimal."""
    return str(int(round(value))) if abs(value - round(value)) < 1e-9 else f"{value:.1f}"


def _require_matplotlib():
    if plt is None:
        raise ImportError(
            "matplotlib is required for chart generation. Install it with: pip install matplotlib"
        )


# ─── Base Class ───────────────────────────────────────────────────────────────


@dataclass
class SurveyChart:
    """Base class for all declarative chart components.

    Parameters
    ----------
    data : SurveyData
        The survey data container with variable metadata.
    figsize : tuple[float, float]
        Figure size in inches (width, height).
    palette : str
        Seaborn/matplotlib color palette name.
    title : str | None
        Override the auto-generated title.
    dpi : int
        Resolution the figure is written at by :meth:`save`.
    """

    data: SurveyData
    figsize: tuple[float, float] = (10, 6)
    palette: str = "muted"
    title: str | None = None
    dpi: int = 150

    _fig: Any = field(init=False, repr=False, default=None)
    _ax: Any = field(init=False, repr=False, default=None)
    _weight_note: str | None = field(init=False, repr=False, default=None)

    def _build(self) -> None:
        """Build the chart. Subclasses must implement this."""
        raise NotImplementedError

    def _ensure_built(self) -> None:
        if self._fig is None:
            _require_matplotlib()
            self._build()

    def plot(self):
        """Build and return the matplotlib Axes object."""
        self._ensure_built()
        return self._ax

    def show(self) -> None:
        """Display the chart (works in Jupyter and scripts)."""
        self._ensure_built()
        plt.show()

    def save(self, path: str | Path, dpi: int | None = None) -> Path:
        """Save the chart to a file.

        ``dpi`` defaults to the chart's own :attr:`dpi`, so a caller that holds
        the figure but not the argument list — a report writing its figures out
        — can raise the resolution of every chart at once by setting the field.
        Passing it explicitly still wins.
        """
        self._ensure_built()
        path = Path(path)
        self._fig.savefig(path, dpi=dpi if dpi is not None else self.dpi, bbox_inches="tight")
        return path

    def _auto_title(self, *parts: str) -> str:
        """Generate a title from variable labels."""
        if self.title:
            return self.title
        return " by ".join(parts)

    @property
    def weight_note(self) -> str | None:
        """What the chart says about the data's weight, or None when there is none.

        A chart either draws the weighted numbers (the bar chart, a heatmap of
        means) or says under its title that it does not — a picture beside a
        weighted table must never disagree with it in silence.
        """
        self._ensure_built()
        return self._weight_note

    def _unweighted(self, title: str) -> str:
        """``title`` with the note that the weight is not applied, when there is one."""
        if self.data.weight is None:
            return title
        self._weight_note = f"unweighted (the weight '{self.data.weight}' is not applied)"
        return f"{title}\n{self._weight_note}"

    def _weighted(self) -> None:
        if self.data.weight is not None:
            self._weight_note = f"weighted by '{self.data.weight}'"


# ─── BarChart ─────────────────────────────────────────────────────────────────


@dataclass
class BarChart(SurveyChart):
    """Categorical bar chart.

    If only `column` is specified, plots frequency distribution.
    If `by` is also specified, plots mean values of `column` grouped by `by`.

    On weighted data (``SurveyData.with_weight``) the bars are sums of weights,
    or weighted means, so they match the Frequencies and Group means tables
    of the same data; the axis says so.

    Parameters
    ----------
    column : str
        Variable to plot (frequencies if categorical, means if continuous with `by`).
    by : str | None
        Optional grouping variable. If provided, plots grouped means.
    horizontal : bool
        If True, plots horizontal bars.
    show_values : bool
        If True, annotates bars with values.
    """

    column: str = ""
    by: str | None = None
    horizontal: bool = False
    show_values: bool = True

    def _build(self) -> None:
        if sns:
            sns.set_theme(style="whitegrid", palette=self.palette)

        fig, ax = plt.subplots(figsize=self.figsize)
        self._fig = fig
        self._ax = ax

        col_label = _get_label(self.data, self.column)
        value_labels = _get_value_labels(self.data, self.column)

        if self.by is None:
            # Frequency bar chart
            series = self.data.frame[self.column].dropna()
            weights = _weights(self.data, series.index)
            if weights is None:
                counts = series.value_counts().sort_index()
                axis = "Count"
            else:
                counts = weights.groupby(series).sum().sort_index()
                axis = "Weighted count"
                self._weighted()

            if value_labels:
                labels = [value_labels.get(v, str(v)) for v in counts.index]
            else:
                labels = [str(v) for v in counts.index]

            if self.horizontal:
                ax.barh(
                    labels, counts.values, color=sns.color_palette(self.palette) if sns else None
                )
                ax.set_xlabel(axis)
                ax.set_ylabel(col_label)
            else:
                ax.bar(
                    labels, counts.values, color=sns.color_palette(self.palette) if sns else None
                )
                ax.set_ylabel(axis)
                ax.set_xlabel(col_label)
                plt.xticks(rotation=30, ha="right")

            if self.show_values:
                for i, v in enumerate(counts.values):
                    if self.horizontal:
                        ax.text(v + 0.5, i, _format_value(float(v)), va="center")
                    else:
                        ax.text(i, v + 0.5, _format_value(float(v)), ha="center")

            ax.set_title(self._auto_title(col_label))

        else:
            # Grouped mean bar chart
            by_label = _get_label(self.data, self.by)
            by_value_labels = _get_value_labels(self.data, self.by)

            frame = self.data.frame[[self.column, self.by]].dropna()
            weights = _weights(self.data, frame.index)
            if weights is None:
                grouped = frame.groupby(self.by)[self.column].mean()
                axis = f"Mean {col_label}"
            else:
                grouped = _weighted_means(frame, [self.column], self.by, weights)[self.column]
                axis = f"Weighted mean {col_label}"
                self._weighted()

            if by_value_labels:
                labels = [by_value_labels.get(v, str(v)) for v in grouped.index]
            else:
                labels = [str(v) for v in grouped.index]

            if self.horizontal:
                ax.barh(labels, grouped.values)
                ax.set_xlabel(axis)
                ax.set_ylabel(by_label)
            else:
                ax.bar(labels, grouped.values)
                ax.set_ylabel(axis)
                ax.set_xlabel(by_label)
                plt.xticks(rotation=30, ha="right")

            if self.show_values:
                for i, v in enumerate(grouped.values):
                    text = f"{v:.2f}"
                    if self.horizontal:
                        ax.text(v + 0.02, i, text, va="center")
                    else:
                        ax.text(i, v + 0.02, text, ha="center")

            ax.set_title(self._auto_title(f"Mean {col_label}", by_label))

        plt.tight_layout()


# ─── BoxPlot ──────────────────────────────────────────────────────────────────


@dataclass
class BoxPlot(SurveyChart):
    """Distribution comparison box plot.

    Compares the distribution of a continuous variable across categories.

    Quartiles and whiskers are of the respondents as they are: a box has no
    standard weighted form, so on weighted data the title says the weight is
    not applied rather than leaving the reader to assume it was.

    Parameters
    ----------
    column : str
        Continuous dependent variable (interval/ratio/ordinal).
    by : str
        Categorical grouping variable.
    show_points : bool
        If True, overlays individual data points (strip plot).
    """

    column: str = ""
    by: str = ""
    show_points: bool = False

    def _build(self) -> None:
        if sns:
            sns.set_theme(style="whitegrid", palette=self.palette)

        fig, ax = plt.subplots(figsize=self.figsize)
        self._fig = fig
        self._ax = ax

        col_label = _get_label(self.data, self.column)
        by_label = _get_label(self.data, self.by)
        by_value_labels = _get_value_labels(self.data, self.by)

        frame = self.data.frame[[self.column, self.by]].dropna().copy()

        if by_value_labels:
            frame["_group"] = frame[self.by].map(lambda v: by_value_labels.get(v, str(v)))
            order = [by_value_labels.get(v, str(v)) for v in sorted(by_value_labels.keys())]
        else:
            frame["_group"] = frame[self.by].astype(str)
            order = None

        if sns:
            sns.boxplot(
                data=frame,
                x="_group",
                y=self.column,
                hue="_group",
                ax=ax,
                palette=self.palette,
                order=order,
                legend=False,
            )
            if self.show_points:
                sns.stripplot(
                    data=frame,
                    x="_group",
                    y=self.column,
                    ax=ax,
                    color="0.3",
                    alpha=0.4,
                    size=3,
                    order=order,
                )
        else:
            groups = [g[self.column].values for _, g in frame.groupby("_group")]
            ax.boxplot(groups)

        ax.set_xlabel(by_label)
        ax.set_ylabel(col_label)
        ax.set_title(self._unweighted(self._auto_title(col_label, by_label)))
        plt.xticks(rotation=30, ha="right")
        plt.tight_layout()


# ─── HeatMap ──────────────────────────────────────────────────────────────────


@dataclass
class HeatMap(SurveyChart):
    """Matrix heatmap visualization.

    Plots mean values of multiple variables grouped by a category,
    or a correlation matrix if no `by` is specified.

    Parameters
    ----------
    columns : list[str]
        List of variables to include in the matrix.
    by : str | None
        If specified, plots mean of each column grouped by this variable
        (weighted means on weighted data). If None, plots a Spearman
        correlation matrix between the columns, which is never weighted —
        the title then says so.
    annot : bool
        If True, annotates cells with numeric values.
    cmap : str
        Colormap name.
    vmin : float | None
        Minimum value for color scale.
    vmax : float | None
        Maximum value for color scale.
    """

    columns: list[str] = field(default_factory=list)
    by: str | None = None
    annot: bool = True
    cmap: str = "YlOrRd"
    vmin: float | None = None
    vmax: float | None = None

    def _build(self) -> None:
        if sns is None:
            raise ImportError("seaborn is required for HeatMap. Install with: pip install seaborn")

        sns.set_theme(style="whitegrid")

        fig, ax = plt.subplots(figsize=self.figsize)
        self._fig = fig
        self._ax = ax

        # Resolve column labels
        col_labels = [_get_label(self.data, c) for c in self.columns]

        if self.by is not None:
            # Grouped means heatmap
            by_value_labels = _get_value_labels(self.data, self.by)
            by_label = _get_label(self.data, self.by)

            frame = self.data.frame[self.columns + [self.by]].dropna()
            weights = _weights(self.data, frame.index)
            if weights is None:
                grouped = frame.groupby(self.by)[self.columns].mean()
            else:
                grouped = _weighted_means(frame, self.columns, self.by, weights)
                self._weighted()

            if by_value_labels:
                grouped.index = [by_value_labels.get(v, str(v)) for v in grouped.index]

            grouped.columns = col_labels
            matrix = grouped.T

            sns.heatmap(
                matrix,
                annot=self.annot,
                fmt=".2f",
                cmap=self.cmap,
                vmin=self.vmin,
                vmax=self.vmax,
                ax=ax,
                linewidths=0.5,
                # Unweighted, the colour bar stays unlabelled as it always was.
                cbar_kws={"label": "Weighted mean"} if weights is not None else None,
            )
            ax.set_title(self._auto_title("Mean Values", by_label))
            ax.set_xlabel(by_label)

        else:
            # Correlation matrix
            frame = self.data.frame[self.columns].dropna()
            corr = frame.corr(method="spearman")
            corr.index = col_labels
            corr.columns = col_labels

            sns.heatmap(
                corr,
                annot=self.annot,
                fmt=".2f",
                cmap="RdBu_r",
                vmin=-1,
                vmax=1,
                ax=ax,
                linewidths=0.5,
                center=0,
            )
            ax.set_title(self._unweighted(self._auto_title("Spearman Correlation Matrix")))

        plt.tight_layout()


# ─── ScatterPlot ──────────────────────────────────────────────────────────────


@dataclass
class ScatterPlot(SurveyChart):
    """Bivariate scatter plot for continuous variables.

    Parameters
    ----------
    x : str
        X-axis variable name.
    y : str
        Y-axis variable name.
    hue : str | None
        Optional grouping variable for color coding.
    trendline : bool
        If True, adds a linear regression trendline.

    Every respondent is one point and the trend line is fitted unweighted, so
    on weighted data the title says the weight is not applied.
    """

    x: str = ""
    y: str = ""
    hue: str | None = None
    trendline: bool = True

    def _build(self) -> None:
        if sns is None:
            raise ImportError("seaborn is required for ScatterPlot.")

        sns.set_theme(style="whitegrid", palette=self.palette)

        fig, ax = plt.subplots(figsize=self.figsize)
        self._fig = fig
        self._ax = ax

        x_label = _get_label(self.data, self.x)
        y_label = _get_label(self.data, self.y)

        cols = [self.x, self.y]
        if self.hue:
            cols.append(self.hue)

        frame = self.data.frame[cols].dropna().copy()

        # Apply hue labels
        hue_col = None
        if self.hue:
            hue_labels = _get_value_labels(self.data, self.hue)
            if hue_labels:
                frame["_hue"] = frame[self.hue].map(lambda v: hue_labels.get(v, str(v)))
                hue_col = "_hue"
            else:
                hue_col = self.hue

        scatter_kwargs = dict(data=frame, x=self.x, y=self.y, ax=ax, alpha=0.7)
        if hue_col:
            scatter_kwargs["hue"] = hue_col
            scatter_kwargs["palette"] = self.palette
        sns.scatterplot(**scatter_kwargs)

        if self.trendline and self.hue is None:
            sns.regplot(
                data=frame,
                x=self.x,
                y=self.y,
                ax=ax,
                scatter=False,
                color="red",
                line_kws={"linewidth": 1.5},
            )

        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        ax.set_title(self._unweighted(self._auto_title(y_label, x_label)))
        plt.tight_layout()
