"""The Result chart of the later analyses: Key drivers, the Perceptual map,
Price sensitivity, Cochran's Q and the ordinal logit.

:mod:`siamang.reporting.result_charts` draws an analysis's result in a flow
(``visualize.result_chart``) through a registry of renderers. The analyses of
this module came after it, each with its own chart where it has one —
:func:`siamang.data.drivers.plot`, :func:`siamang.data.correspondence.plot`,
:func:`siamang.data.pricing.plot` — so what is registered here draws those
figures as they are, rather than a second picture of the same result that could
disagree with the first: the flow's chart is the chart the module documents.
Their tables (``DriverTable``, ``MapTable``, ``PriceTable``) carry the whole
result in ``analysis``, so any of an analysis's tables draws it.

========================== ============ ======================================
Result                     Kind         Chart
========================== ============ ======================================
Key drivers                importance   each driver's share of R², largest
                                        first (:func:`drivers.plot`)
Perceptual map             map          the symmetric map of the first two
                                        dimensions (:func:`correspondence.plot`)
Price sensitivity          curves       Van Westendorp's four curves and
                                        points (and the NMS trial curve), or
                                        Gabor-Granger's demand and revenue
                                        (:func:`pricing.plot`)
Cochran's Q                shares       each variable's share saying yes with
                                        its Wilson interval, as McNemar's
Ordinal logit (Regression) coefficients the coefficients' odds ratios with
                                        their Wald intervals; the thresholds
                                        between the answers are left out
========================== ============ ======================================

The three figures drawn by the analyses keep their own title (the Title given
replaces its first line), weight line and color-blind-safe colors, so the
Palette is not read for them; their labels are placed for the figure's final
layout, which the chart therefore does not lay out again
(:meth:`ResultChart.adopt`). Their interactive form (``vega_lite()``) is
recorded from the analysis's result as the figure draws it
(:mod:`siamang.reporting.result_specs`): the drivers' shares, the map's points
with each name where the figure placed it, the price curves and points.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from siamang.reporting import result_specs
from siamang.reporting.result_charts import (
    ResultChart,
    _dots,
    _forest,
    _ink,
    _mark_note,
    _percent,
    _test_line,
    register,
    register_output,
)

__all__ = ["TWO_PANELS", "labels_overlap", "register_all"]


# ─── Key drivers, the Perceptual map, Price sensitivity ──────────────────────


def _analysis_of(result: Any, table_type: type, result_type: type) -> Any:
    """The whole result a table carries in ``analysis``, or the result itself."""
    if isinstance(result, result_type):
        return result
    if isinstance(result, table_type):
        return result.analysis
    return None


def _draw_drivers(result: Any, chart: ResultChart) -> str:
    from siamang.data import drivers

    analysis = _analysis_of(result, drivers.DriverTable, drivers.KeyDrivers)
    chart.adopt(drivers.plot(analysis, title=chart.title, figsize=chart.figsize))
    heading = f"Key drivers of {analysis.outcome}"
    result_specs.record_drivers(chart, analysis, heading=chart.title or heading)
    return heading


def _draw_map(result: Any, chart: ResultChart) -> str:
    """The map at the chart's size, or taller when its labels crowd it.

    The map places each label beside its point where it overlaps nothing, as
    far as the plot's room allows; on a figure shorter than the map's own
    (10 × 8 inches) a crowded map can be left with labels over each other.
    Such a map is drawn again, a fifth taller each time, until no two labels
    overlap or it is a fifth taller than it is wide — as the row charts grow
    taller rather than print their labels over each other; one still crowded
    then numbers its points and lists their names under it."""
    from siamang.data import correspondence

    analysis = _analysis_of(result, correspondence.MapTable, correspondence.PerceptualMap)
    width, height = (float(value) for value in chart.figsize)
    asked, tallest = height, max(height, width * 1.2)
    numbered = False
    while True:
        fig = correspondence.plot(
            analysis, title=chart.title, figsize=(width, height), numbered=False
        )
        if not labels_overlap(fig.axes[0]):
            break
        if height >= tallest:
            # Still crowded at its tallest: numbered points, and their names
            # listed under the map — a map at least 0.8 as tall as it is wide.
            fig = correspondence.plot(
                analysis,
                title=chart.title,
                figsize=(width, max(asked, 0.8 * width)),
                numbered=True,
            )
            numbered = True
            break
        height = min(height * 1.2, tallest)
    chart.adopt(fig)
    heading = f"Perceptual map: {analysis.row_title} × {analysis.column_title}"
    # Interactive, a crowded map leaves its names to the tooltips and a box
    # that writes them on the map, where zooming in sets them apart.
    result_specs.record_map(chart, analysis, numbered=numbered, heading=chart.title or heading)
    return heading


def labels_overlap(ax: Any) -> bool:
    """Whether two of the texts drawn on ``ax`` overlap by more than a point
    across and up — the texts alone, not the lines that lead a label back to
    its point."""
    from matplotlib.text import Text

    fig = ax.figure
    if not hasattr(fig.canvas, "get_renderer"):
        from matplotlib.backends.backend_agg import FigureCanvasAgg

        FigureCanvasAgg(fig)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    texts = [text for text in ax.texts if text.get_visible() and text.get_text().strip()]
    if len(texts) < 2:
        return False
    boxes = np.array([Text.get_window_extent(text, renderer).extents for text in texts])
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


def _draw_price(result: Any, chart: ResultChart) -> str:
    from siamang.data import pricing

    analysis = _analysis_of(result, pricing.PriceTable, pricing.PriceSensitivity)
    chart.adopt(pricing.plot(analysis, title=chart.title, figsize=_price_size(analysis, chart)))
    name = "Van Westendorp" if analysis.method == "van_westendorp" else "Gabor-Granger"
    heading = f"Price sensitivity ({name})"
    result_specs.record_prices(chart, analysis, heading=chart.title or heading)
    return heading


#: The least height of a price chart of two panels, in inches: on a shorter
#: figure the lower panel is shorter than its own axis title.
TWO_PANELS = 6.0


def _price_size(analysis: Any, chart: ResultChart) -> tuple[float, float]:
    """The chart's size — at least :data:`TWO_PANELS` tall where the analysis
    draws two panels: Gabor-Granger's demand over revenue, Van Westendorp's
    curves over the NMS trial curve."""
    width, height = (float(value) for value in chart.figsize)
    two = analysis.method == "gabor_granger" or "trial" in analysis.shares
    return (width, max(height, TWO_PANELS)) if two else (width, height)


# ─── Cochran's Q ─────────────────────────────────────────────────────────────


def _is_cochran_table(table: Any) -> bool:
    columns = [str(column) for column in table.to_frame().columns]
    return columns == ["Variable", "N", "Yes", "% yes"] and table.stats.get("Test") == (
        "Cochran's Q"
    )


def _draw_cochran(table: Any, chart: ResultChart) -> str:
    from siamang.data.intervals import proportion_interval

    frame = table.to_frame()
    stats = table.stats
    n = int(stats.get("N") or 0)
    intervals = [proportion_interval(int(count), n) for count in frame["Yes"]]
    estimate = [
        interval.estimate * 100 if interval.estimate is not None else np.nan
        for interval in intervals
    ]
    ax, size = _dots(
        chart,
        [str(value) for value in frame["Variable"]],
        [
            {
                "estimate": estimate,
                "lower": [i.lower * 100 if i.defined else np.nan for i in intervals],
                "upper": [i.upper * 100 if i.defined else np.nan for i in intervals],
                "text": [_percent(value) for value in estimate],
                "color": chart.colors(1)[0],
            }
        ],
    )
    result_specs.note(chart, row_title="Question")
    ax.set_xlim(0, 100)
    ax.set_xlabel("Share saying yes (%) with its 95 % confidence interval (Wilson)", color=_ink())
    _mark_note(
        ax,
        f"The same {n} respondents answered each; counts as yes: "
        f"{stats.get('Counts as yes', '')}; {_test_line(stats)}. The pairs are compared in "
        "the pairs output.",
        size,
    )
    return "Cochran's Q: the share saying yes to each"


# ─── The ordinal logit ───────────────────────────────────────────────────────


def _is_ordinal_coefficients(frame: Any) -> bool:
    return {"term", "type", "estimate", "std_error", "odds_ratio"} <= set(frame.columns) and (
        frame["type"].astype(str) == "threshold"
    ).any()


def _draw_ordinal(frame: Any, chart: ResultChart, stats: dict[str, Any]) -> str:
    """The coefficients as odds ratios with their 95 % Wald intervals — the
    table's own (R's ``exp(confint.default(fit))``). The thresholds are where
    the scale is cut, not an effect of anything, so they are left out."""
    coefficients = frame[frame["type"].astype(str) == "coefficient"]
    coefficients.attrs = dict(frame.attrs)
    order = stats.get("order")
    _forest(
        coefficients,
        chart,
        stats,
        note="An odds ratio above 1 makes the higher answers more likely"
        + (f" ({order})" if order else "")
        + "; the thresholds between the answers are in the table.",
    )
    outcome = stats.get("outcome")
    outcome = (frame.attrs.get("labels") or {}).get(str(outcome), outcome) if outcome else outcome
    return f"Ordinal logit: odds ratios{f' — {outcome}' if outcome else ''}"


# ─── Registration ────────────────────────────────────────────────────────────


def register_all() -> None:
    """Register the renderers and the flow outputs of this module's analyses
    (called once by :mod:`siamang.reporting.result_charts`, after its own, so
    these win where both accept a result)."""
    from siamang.data import correspondence, drivers, pricing
    from siamang.data.models import RegressionResult
    from siamang.data.paired import PairedResult
    from siamang.reporting.model_tables import RegressionTable
    from siamang.reporting.result_table import ResultTable

    register(
        drivers.DriverTable,
        ("importance",),
        _draw_drivers,
        accepts=lambda table: table.analysis is not None,
        name="Key drivers",
    )
    register(drivers.KeyDrivers, ("importance",), _draw_drivers, name="Key drivers")
    register(
        correspondence.MapTable,
        ("map",),
        _draw_map,
        accepts=lambda table: table.analysis is not None,
        name="Perceptual map",
    )
    register(correspondence.PerceptualMap, ("map",), _draw_map, name="Perceptual map")
    register(
        pricing.PriceTable,
        ("curves",),
        _draw_price,
        accepts=lambda table: table.analysis is not None,
        name="Price sensitivity",
    )
    register(pricing.PriceSensitivity, ("curves",), _draw_price, name="Price sensitivity")
    register(
        ResultTable, ("shares",), _draw_cochran, accepts=_is_cochran_table, name="Paired tests"
    )
    register(
        PairedResult,
        ("shares",),
        lambda result, chart: _draw_cochran(result.table, chart),
        accepts=lambda result: _is_cochran_table(result.table),
        name="Paired tests",
    )
    register(
        pd.DataFrame,
        ("coefficients",),
        lambda frame, chart: _draw_ordinal(frame, chart, chart.stats),
        accepts=_is_ordinal_coefficients,
        name="Regression",
    )
    register(
        RegressionResult,
        ("coefficients",),
        lambda result, chart: _draw_ordinal(result.table, chart, {**chart.stats, **result.stats}),
        accepts=lambda result: result.kind == "ordinal",
        name="Regression",
    )
    register(
        RegressionTable,
        ("coefficients",),
        lambda table, chart: _draw_ordinal(
            table.result.table, chart, {**chart.stats, **table.result.stats}
        ),
        accepts=lambda table: table.result is not None and table.result.kind == "ordinal",
        name="Regression",
    )

    register_output("analyze.drivers", "table", ("importance",))
    for port in ("table", "rows", "columns"):
        register_output("analyze.correspondence", port, ("map",))
    for port in ("table", "curves"):
        register_output("analyze.price", port, ("curves",))
    means = ("means", "means_sd")
    register_output(
        "analyze.paired",
        "table",
        lambda params: ("shares",) if params.get("test") in ("mcnemar", "cochran") else means,
    )
