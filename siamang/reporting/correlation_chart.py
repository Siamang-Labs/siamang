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

from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

from siamang.reporting.chart_parts import Footnote, axes_points, chars_in, left_out_note, wrap

if TYPE_CHECKING:
    from siamang.reporting.charts import HeatMap


def draw(chart: HeatMap) -> None:
    """Build ``chart``'s correlation matrix by its ``method``."""

    import matplotlib.pyplot as plt
    import seaborn as sns

    from siamang.data import inference
    from siamang.reporting import chart_theme

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
    numbered = max(len(label) for label in labels) > 14
    texts = [f"{index}. {label}" if numbered else label for index, label in enumerate(labels, 1)]
    size, rows = _row_labels(texts, chart.figsize)
    matrix = result.coefficients.copy()
    # An item that correlates with nothing (the same answer from everyone) has
    # no correlation with itself either: its diagonal is blank, as its row is.
    complete = source[columns].dropna()  # listwise, as the coefficients
    for name in columns:
        if complete[name].nunique() < 2:
            matrix.loc[name, name] = np.nan
    matrix.index = rows
    matrix.columns = [str(index) for index in range(1, len(labels) + 1)] if numbered else rows
    lines = max(row.count("\n") + 1 for row in rows)

    chart_theme.set_theme(style="whitegrid")
    fig, ax = plt.subplots(figsize=chart.figsize)
    chart._fig, chart._ax = fig, ax
    name = inference.CORRELATION_NAMES[method]
    symbol = {"pearson": "r", "spearman": "rho", "kendall": "tau"}[method]
    sns.heatmap(
        matrix,
        annot=False,
        cmap=chart_theme.cmap("RdBu_r", "diverging"),
        vmin=-1,
        vmax=1,
        center=0,
        ax=ax,
        linewidths=0.5,
        cbar_kws={"label": f"{'Weighted ' if weighted else ''}{name} {symbol}"},
    )
    ax.grid(False)  # the theme's lines would cross a blank cell
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
        # A pair named as the chart names its variables: by number, or label.
        shown = {
            column: str(index) if numbered else label
            for index, (column, label) in enumerate(zip(columns, labels, strict=True), 1)
        }
        pairs = [_pair_note(note, shown) for note in result.notes]
        notes.append("Not computed (a blank cell): " + "; ".join(pairs) + ".")
    note = left_out_note(left_out, data.variables)
    if note:
        notes.append(note)
    # Each row as tall as its label.
    footnote = Footnote(fig, notes, axes=ax, least=len(rows) * (lines * size * 1.2 + 4.0))
    footnote.apply()
    if chart.annot and not _annotate(ax, matrix.to_numpy(dtype=float)):
        footnote.add("The cells are too small to hold their coefficients: see the table.")
        footnote.apply()


def draw_means(chart: HeatMap) -> None:
    """Build ``chart``'s mean of each item in each group of ``by`` in the
    theme's colours: the classic form's numbers but for the codebook's missing
    codes, which are left out and counted (the classic form averaged a 99 = Not
    applicable into a 1–5 scale's mean), long item labels numbered and wrapped
    so the cells keep the plot, each group's base under its name, and the base,
    the weight and what was left out under the chart."""

    import matplotlib.pyplot as plt
    import seaborn as sns

    from siamang.data import inference
    from siamang.reporting import chart_theme
    from siamang.reporting.charts import _get_label, _get_value_labels, _weighted_means

    data = chart.data
    columns = list(dict.fromkeys(chart.columns))
    by = str(chart.by)
    unknown = [name for name in [*columns, by] if name not in data.frame.columns]
    if unknown:
        raise ValueError(f"No variable {unknown[0]!r} in the data.")
    source, left_out = inference.without_missing_codes(data.frame, [*columns, by], data.variables)
    frame = source[[*columns, by]][source[by].notna()].copy()
    for name in columns:
        numbers = pd.to_numeric(frame[name], errors="coerce")
        if numbers.notna().sum() < frame[name].notna().sum():
            raise ValueError(
                f"{_label(chart, name)} holds answers that are not numbers, so it has no mean."
            )
        frame[name] = numbers.astype(float)
    answered = frame[columns].notna().any(axis=1)
    frame = frame[answered]
    if frame.empty:
        raise ValueError(
            f"No respondent answered an item and {_get_label(data, by)}: there is no mean to draw."
        )
    weighted = data.weight is not None
    weights = None
    if weighted:
        if data.weight not in data.frame.columns:
            raise ValueError(f"Weight column '{data.weight}' not found in frame.")
        weights = (
            pd.to_numeric(data.frame.loc[frame.index, data.weight], errors="coerce")
            .fillna(0.0)
            .astype(float)
        )
        chart._weighted()
    # Each item's mean of those who answered it, as Group means computes it.
    means = {}
    for name in columns:
        part = frame[[name, by]].dropna()
        if weights is None:
            means[name] = part.groupby(by)[name].mean()
        else:
            means[name] = _weighted_means(part, [name], by, weights.loc[part.index])[name]
    grouped = pd.DataFrame(means)
    sizes = frame.groupby(by).size()
    by_labels = _get_value_labels(data, by)
    from siamang.reporting.chart_parts import code_order, code_text

    order = sorted(grouped.index, key=code_order)
    grouped = grouped.loc[order]

    labels = [_label(chart, name) for name in columns]
    labels = [
        f"{label} ({name})" if labels.count(label) > 1 else label
        for label, name in zip(labels, columns, strict=True)
    ]
    # "MaxDiff score: Focus sessions", "MaxDiff score: …" on every row: the
    # rows name what differs, and what they share goes to the colour bar.
    from siamang.reporting.chart_parts import common_prefix, in_sentence

    shared, labels = common_prefix(labels)
    numbered = max(len(label) for label in labels) > 14
    texts = [f"{index}. {label}" if numbered else label for index, label in enumerate(labels, 1)]
    size, rows = _row_labels(texts, chart.figsize)
    groups = [
        f"{by_labels.get(code, code_text(code))}\n(n = {int(sizes[code]):,})" for code in order
    ]
    matrix = grouped.T.copy()
    matrix.index = rows
    matrix.columns = groups
    lines = max(row.count("\n") + 1 for row in rows)

    chart_theme.set_theme(style="whitegrid")
    fig, ax = plt.subplots(figsize=chart.figsize)
    chart._fig, chart._ax = fig, ax
    sns.heatmap(
        matrix,
        annot=False,
        cmap=chart_theme.cmap(chart.cmap, "sequential"),
        vmin=chart.vmin,
        vmax=chart.vmax,
        ax=ax,
        linewidths=0.5,
        cbar_kws={
            "label": ("Weighted mean" if weighted else "Mean")
            + (f" {in_sentence(shared)}" if shared else "")
        },
    )
    ax.grid(False)
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=size)
    by_label = _get_label(data, by)
    ax.set_xlabel(by_label)
    title = chart.title or f"Mean values by {by_label}"
    ax.set_title(wrap(title, chars_in(chart.figsize[0] * 72.0 * 0.8, 12.0)))

    notes = [
        f"Base: {len(frame):,} {'respondent' if len(frame) == 1 else 'respondents'} who answered "
        f"{by_label} and an item; each group's n is under its name. Each cell is the mean of "
        "the group's respondents who answered the item, as Group means gives it."
    ]
    if weighted:
        notes.append(f"Weighted by '{data.weight}': the means are weighted; n counts respondents.")
    note = left_out_note(left_out, data.variables)
    if note:
        notes.append(note)
    footnote = Footnote(fig, notes, axes=ax, least=len(rows) * (lines * size * 1.2 + 4.0))
    footnote.apply()
    # The groups' names under their columns as the Bar chart places its
    # labels: level when they fit, else turned in as many lines as fit.
    from siamang.reporting.bars import _tick_labels

    placed = _tick_labels(groups, axes_points(ax)[0] / max(len(groups), 1))
    names, rotation, name_size = (
        placed if placed is not None else ([g.replace("\n", " ") for g in groups], 45, 8.0)
    )
    ax.set_xticklabels(
        names,
        rotation=rotation,
        ha="right" if rotation else "center",
        rotation_mode="anchor" if rotation else "default",
        fontsize=min(size, name_size),
    )
    footnote.apply()
    if chart.annot and not _annotate(ax, matrix.to_numpy(dtype=float), mean=True):
        footnote.add("The cells are too small to hold their means: see the Group means table.")
        footnote.apply()


def _row_labels(texts: list[str], figsize: tuple[float, float]) -> tuple[float, list[str]]:
    """The row labels' size and wrapped text: the largest size and narrowest
    column (10 pt in a third of the width, down to 8 pt in a half) at which
    the rows fit the figure's height grown by at most 60 % — else the
    smallest, the figure growing to hold them — so the matrix keeps most of
    the width and a small figure is not stretched into a strip."""

    width_pt, height_pt = figsize[0] * 72.0, figsize[1] * 72.0
    count = max(len(texts), 1)
    room = height_pt * 0.62 * 1.6
    tries = ((10.0, 0.34), (9.0, 0.34), (9.0, 0.42), (8.0, 0.42), (8.0, 0.5))
    for size, share in tries:
        rows = [wrap(text, chars_in(share * width_pt, size)) for text in texts]
        lines = max(row.count("\n") + 1 for row in rows)
        if count * (lines * size * 1.2 + 4.0) <= room:
            return size, rows
    return size, rows


def _pair_note(note: str, shown: dict[str, str]) -> str:
    """``"x × c: reason"`` with the two variables named as the chart names them."""

    head, colon, reason = note.partition(": ")
    first, cross, second = head.partition(" × ")
    if colon and cross and first in shown and second in shown:
        return f"{shown[first]} × {shown[second]}: {reason}"
    return note


def _annotate(ax: Any, values: np.ndarray, *, mean: bool = False) -> bool:
    """Each coefficient (or ``mean``) in its cell, at a size its cell holds
    ("-0.03" in it; a mean's own width): at most 10 pt, and none below 6 pt,
    where they would run together. Returns whether they were written."""

    from siamang.reporting.chart_parts import CHAR_WIDTH, ink_on

    count, across = values.shape
    width, height = axes_points(ax)
    cell_w, cell_h = width / max(across, 1), height / max(count, 1)
    finite = values[np.isfinite(values)]
    digits = max((len(f"{value:,.2f}") for value in finite), default=5) if mean else 5
    size = min(10.0, cell_w * 0.9 / (digits * CHAR_WIDTH), cell_h / 1.4)
    if size < 6:
        return False
    cmap, norm = ax.collections[0].cmap, ax.collections[0].norm
    for i in range(count):
        for j in range(across):
            value = values[i, j]
            if value != value:
                continue
            ax.text(
                j + 0.5,
                i + 0.5,
                f"{value:,.2f}" if mean else f"{value:.2f}",
                ha="center",
                va="center",
                fontsize=size,
                color=ink_on(cmap(norm(value))),
            )
    return True


def _label(chart: HeatMap, name: str) -> str:
    variables = chart.data.variables
    if variables and name in variables:
        return variables[name].label or name
    return name


__all__ = ["draw", "draw_means"]
