"""A heatmap of Pearson or Kendall correlations, as the Correlation matrix
computes them.

``HeatMap(method="spearman")``, its default, draws what it always drew:
Spearman's rho of the respondents who answered every item, unweighted, the
answers read as they are. The two other methods are drawn here from
:func:`siamang.data.inference.correlation_matrix` — the numbers of the
Correlation matrix table with ``missing="listwise"``, the heatmap's rule: the
codebook's missing codes are left out and counted, Pearson's r is weighted when
the data is (as the table weights it), and Kendall's tau-b, which has no
standard weighted form, says under its title that the weight is not applied.
A pair that cannot be computed (an item with the same answer from everyone) is
a blank cell, and the note under the plot says why.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from siamang.reporting.chart_parts import Footnote, chars_in, left_out_note, wrap

if TYPE_CHECKING:
    from siamang.reporting.charts import HeatMap


def draw(chart: HeatMap) -> None:
    """Build ``chart``'s correlation matrix by its ``method``."""

    import matplotlib.pyplot as plt
    import seaborn as sns

    from siamang.data import inference

    method = chart.method
    if method not in inference.CORRELATIONS:
        raise ValueError(
            f"method must be one of {', '.join(inference.CORRELATIONS)}; got {method!r}."
        )
    data = chart.data
    columns = list(dict.fromkeys(chart.columns))
    unknown = [name for name in columns if name not in data.frame.columns]
    if unknown:
        raise ValueError(f"No variable {unknown[0]!r} in the data.")
    source, left_out = inference.without_missing_codes(data.frame, columns, data.variables)
    source = source.reset_index(drop=True)
    weighted = data.weight is not None and method == "pearson"
    weights = None
    if weighted:
        if data.weight not in data.frame.columns:
            raise ValueError(f"Weight column '{data.weight}' not found in frame.")
        weights = pd.to_numeric(data.frame[data.weight], errors="coerce").fillna(0.0).to_numpy()
    result = inference.correlation_matrix(
        source, columns, method=method, missing="listwise", weights=weights
    )

    labels = [_label(chart, name) for name in columns]
    labels = [
        f"{label} ({name})" if labels.count(label) > 1 else label
        for label, name in zip(labels, columns, strict=True)
    ]
    # Long labels are numbered, as a correlation table numbers its variables:
    # the rows carry "1. label", the columns the number alone.
    size = 10.0
    numbered = max(len(label) for label in labels) > 14
    width = chars_in(0.34 * chart.figsize[0] * 72.0, size)
    rows = [
        wrap(f"{index}. {label}" if numbered else label, width)
        for index, label in enumerate(labels, 1)
    ]
    matrix = result.coefficients.copy()
    matrix.index = rows
    matrix.columns = [str(index) for index in range(1, len(labels) + 1)] if numbered else rows
    lines = max(row.count("\n") + 1 for row in rows)

    sns.set_theme(style="whitegrid")
    fig, ax = plt.subplots(figsize=chart.figsize)
    chart._fig, chart._ax = fig, ax
    name = inference.CORRELATION_NAMES[method]
    symbol = {"pearson": "r", "spearman": "rho", "kendall": "tau"}[method]
    sns.heatmap(
        matrix,
        annot=chart.annot,
        fmt=".2f",
        cmap="RdBu_r",
        vmin=-1,
        vmax=1,
        center=0,
        ax=ax,
        linewidths=0.5,
        cbar_kws={"label": f"{'Weighted ' if weighted else ''}{name} {symbol}"},
    )
    if numbered:
        ax.set_xticklabels(ax.get_xticklabels(), rotation=0, fontsize=size)
    else:
        ax.set_xticklabels(
            ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor", fontsize=size
        )
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=size)
    title = chart.title or f"{name} Correlation Matrix"
    title = wrap(title, chars_in(chart.figsize[0] * 72.0 * 0.8, 12.0))
    if weighted:
        chart._weighted()
    else:
        title = chart._unweighted(title)
    ax.set_title(title)

    complete = int(np.diag(result.n.to_numpy()).min()) if len(columns) else 0
    notes = [
        f"N = {complete} {'respondent' if complete == 1 else 'respondents'} who answered "
        "every item (listwise)."
    ]
    if weighted:
        notes.append(
            f"Weighted by '{data.weight}': the coefficients are weighted; N counts respondents."
        )
    if result.notes:
        notes.append("Not computed (a blank cell): " + "; ".join(result.notes) + ".")
    note = left_out_note(left_out, data.variables)
    if note:
        notes.append(note)
    # Each row as tall as its label.
    Footnote(fig, notes, axes=ax, least=len(rows) * (lines * size * 1.2 + 4.0)).apply()


def _label(chart: HeatMap, name: str) -> str:
    variables = chart.data.variables
    if variables and name in variables:
        return variables[name].label or name
    return name


__all__ = ["draw"]
