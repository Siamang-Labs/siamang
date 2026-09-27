"""Charts of what an analysis found — the ``visualize.result_chart`` node.

The charts of :mod:`siamang.reporting.charts` draw from the data; these draw
from the result an analysis already computed, so the picture beside a table
shows the table's own numbers: Group means with their confidence intervals,
a factor analysis's scree plot, TURF's reach curve. Nothing is recomputed that
the result holds; what it does not hold and a chart needs — the interval of a
weighted mean, the standard error of a MaxDiff utility — is computed the way
the analysis computes the rest (:mod:`siamang.data.intervals`).

    from siamang.reporting import result_charts

    chart = result_charts.chart(data.report.means("satisfaction", by="region"))
    chart.save("means.png")
    result_charts.chart(pca.variance, kind="scree", title="Scree plot")

:func:`chart` takes one result, or a list of them — what a flow connects to the
node: an analysis's table, and its stat beside it where the table does not say
what the chart should (the weight of a regression, the base of its interval).
A chart follows the weight of the result it draws: the note the result carries
(``weighted by 'w'``, or ``unweighted (the weight 'w' is not applied)``) is the
second line of its title and :attr:`~siamang.reporting.charts.SurveyChart.weight_note`.

Registry
--------
Each kind of result is drawn by a renderer registered for its class::

    register(result_type, kinds, fn, *, accepts=None, name=None)

``result_type`` is the class (or a tuple of classes) of the result; ``kinds``
the charts it can draw, the first being what ``kind="auto"`` draws; ``fn(result,
chart)`` draws ``result`` on the figure it asks the :class:`ResultChart` for
(:meth:`ResultChart.figure`, or :meth:`ResultChart.rows` for one row per
category) and returns the title to use when none is given — ``chart.drawn`` is
the kind to draw. ``accepts(result)`` tells apart results of one class — a
regression's coefficients and a PCA's loadings are both DataFrames — and
``name`` is what the analysis is called in messages. The last registration that
accepts a result wins, so a later node can take a result over. A new kind is
also a value of the node's ``kind`` enum (``siamang/flow/nodes/visualize/
result_chart.yaml``).

What :func:`~siamang.flow.check_flow` knows before a run is registered apart,
since it has the node's type and parameters rather than its result::

    register_output(node_type, port, kinds)

``kinds`` is a tuple, or a function of the node's parameters returning one
(TURF draws its reach curve, or with ``method: fixed`` each option's reach).
An output not registered, other than a Stat of a node that has one, is named
before the run as one the chart cannot draw. The renderers of the analyses that
came after this module — Key drivers, the Perceptual map, Price sensitivity,
Cochran's Q, the ordinal logit — are in :mod:`siamang.reporting.method_charts`.
"""

from __future__ import annotations

import math
import re
import textwrap
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from siamang.reporting import chart_theme
from siamang.reporting.charts import SurveyChart, _require_matplotlib, plt, sns

__all__ = [
    "KINDS",
    "Renderer",
    "ResultChart",
    "ResultChartError",
    "chart",
    "check_sources",
    "kinds_of",
    "letters",
    "output_kinds",
    "register",
    "register_output",
    "renderer_for",
]

#: Every kind a built-in renderer draws, in the order the node lists them.
KINDS = (
    "means",
    "means_sd",
    "interval",
    "stacked",
    "reach",
    "items",
    "utilities",
    "scores",
    "shares",
    "importance",
    "partworths",
    "scree",
    "loadings",
    "profile",
    "coefficients",
    "heatmap",
    "sentiment",
    "map",
    "curves",
)

_INK = "#333333"
_MUTED = "#767676"
_TRACK = "#e6e6e6"
# A diverging pair with a grey midpoint (red–grey–blue, safe for red–green
# colour blindness): detractors, passives and promoters; negative, neutral and
# positive sentiment.
_NEGATIVE, _NEUTRAL, _POSITIVE = "#d6604d", "#bababa", "#4393c3"


# The colours above, or — while a chart of palette "theme" is drawn — the
# report theme's text, secondary text, grid and diverging pair.
def _ink() -> str:
    return chart_theme.text(_INK)


def _muted() -> str:
    return chart_theme.muted(_MUTED)


def _track() -> str:
    return chart_theme.grid(_TRACK)


def _negative() -> str:
    return chart_theme.low(_NEGATIVE)


def _neutral() -> str:
    return chart_theme.neutral(_NEUTRAL)


def _positive() -> str:
    return chart_theme.high(_POSITIVE)


# What the title, the axis labels and the tick labels take of a figure's height.
_CHROME = 1.3
# The most a row of a row chart takes, and the shortest such chart, in inches.
_PITCH, _SHORTEST = 0.7, 2.6


class ResultChartError(ValueError):
    """A result the chart cannot draw, or a kind that does not suit it; the
    message says what it draws instead."""


# ─── Registry ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Renderer:
    """How one kind of result is drawn: see the module's Registry."""

    result_type: type | tuple[type, ...]
    kinds: tuple[str, ...]
    fn: Callable[[Any, ResultChart], str]
    accepts: Callable[[Any], bool] | None = None
    name: str = ""

    def draws(self, result: Any) -> bool:
        if not isinstance(result, self.result_type):
            return False
        return self.accepts is None or bool(self.accepts(result))


_RENDERERS: list[Renderer] = []
_OUTPUTS: dict[tuple[str, str], tuple[str, ...] | Callable[[dict[str, Any]], tuple[str, ...]]] = {}


def register(
    result_type: type | tuple[type, ...],
    kinds: Sequence[str],
    fn: Callable[[Any, ResultChart], str] | None = None,
    *,
    accepts: Callable[[Any], bool] | None = None,
    name: str | None = None,
) -> Any:
    """Register ``fn`` to draw results of ``result_type`` as ``kinds``.

    Without ``fn`` it is a decorator. Returns the :class:`Renderer` (or the
    function, as a decorator)."""

    kinds = tuple(kinds)
    if not kinds or not all(isinstance(kind, str) and kind and kind != "auto" for kind in kinds):
        raise ValueError("kinds must be one or more names other than 'auto'.")

    def add(function: Callable[[Any, ResultChart], str]) -> Renderer:
        renderer = Renderer(result_type, kinds, function, accepts, name or _type_name(result_type))
        _RENDERERS.append(renderer)
        return renderer

    if fn is None:

        def decorator(function: Callable[[Any, ResultChart], str]) -> Callable:
            add(function)
            return function

        return decorator
    return add(fn)


def register_output(
    node_type: str,
    port: str,
    kinds: Sequence[str] | Callable[[dict[str, Any]], tuple[str, ...]],
) -> None:
    """Say that output ``port`` of ``node_type`` draws ``kinds`` — a tuple, or
    a function of the node's parameters returning one — for ``check_flow``."""

    _OUTPUTS[(node_type, port)] = kinds if callable(kinds) else tuple(kinds)


def renderer_for(result: Any) -> Renderer | None:
    """The renderer that draws ``result``, or None."""

    for renderer in reversed(_RENDERERS):
        if renderer.draws(result):
            return renderer
    return None


def kinds_of(result: Any) -> tuple[str, ...]:
    """The kinds ``result`` can be drawn as; empty when it cannot be drawn."""

    renderer = renderer_for(result)
    return renderer.kinds if renderer is not None else ()


def output_kinds(node_type: str, port: str, params: dict[str, Any]) -> tuple[str, ...] | None:
    """The kinds output ``port`` of a ``node_type`` node with ``params`` draws,
    or None when a Result chart cannot draw it."""

    kinds = _OUTPUTS.get((node_type, port))
    if kinds is None:
        return None
    return tuple(kinds(params)) if callable(kinds) else kinds


def _analyses() -> str:
    names = list(dict.fromkeys(renderer.name for renderer in _RENDERERS if renderer.name))
    return ", ".join(names)


def _type_name(result_type: type | tuple[type, ...]) -> str:
    if isinstance(result_type, tuple):
        return " or ".join(item.__name__ for item in result_type)
    return result_type.__name__


# ─── The flow's entry point ──────────────────────────────────────────────────


def chart(
    results: Any,
    kind: str = "auto",
    *,
    title: str | None = None,
    figsize: tuple[float, float] = (10, 6),
    palette: str = "muted",
    dpi: int = 150,
) -> ResultChart:
    """The chart of ``results`` — one result, or the outputs a flow connected.

    The first result a renderer draws is drawn (with ``kind``, the first that
    can be drawn as it); the others lend it what they say, such as the weight.
    The chart is built here, so a result it cannot draw fails the node that
    asked for it, with the reason, rather than the preview after it.
    """

    if kind != "auto" and kind not in _all_kinds():
        raise ResultChartError(f"Unknown kind {kind!r}; the kinds are auto, {', '.join(KINDS)}.")
    items = list(results) if isinstance(results, list | tuple) else [results]
    drawable = [item for item in items if renderer_for(item) is not None]
    if not drawable:
        what = ", ".join(_describe(item) for item in items) or "nothing"
        raise ResultChartError(
            f"A Result chart cannot draw {what}. It draws the results of {_analyses()} "
            "— connect the table of one of them."
        )
    if kind == "auto":
        chosen = drawable[0]
    else:
        chosen = next((item for item in drawable if kind in kinds_of(item)), None)
        if chosen is None:
            offered = "; ".join(
                f"{renderer_for(item).name} draws {_listed(kinds_of(item))}"  # type: ignore[union-attr]
                for item in drawable
            )
            raise ResultChartError(f"Kind {kind!r} does not suit this result: {offered}.")
    from siamang.data.survey_data import SurveyData

    data = getattr(chosen, "data", None) if not isinstance(chosen, pd.DataFrame) else None
    figure = ResultChart(
        data=data if isinstance(data, SurveyData) else None,  # type: ignore[arg-type]
        result=chosen,
        kind=kind,
        context=[item for item in items if item is not chosen],
        figsize=(float(figsize[0]), float(figsize[1])),
        palette=palette,
        title=title or None,
        dpi=dpi,
    )
    figure._ensure_built()
    return figure


def _all_kinds() -> set[str]:
    return set(KINDS) | {kind for renderer in _RENDERERS for kind in renderer.kinds}


def _listed(kinds: Sequence[str]) -> str:
    quoted = [f"'{kind}'" for kind in kinds]
    return quoted[0] if len(quoted) == 1 else ", ".join(quoted[:-1]) + " or " + quoted[-1]


def _describe(item: Any) -> str:
    if isinstance(item, pd.DataFrame):
        columns = [str(column) for column in item.columns[:4]]
        more = ", …" if len(item.columns) > 4 else ""
        return f"a table of {', '.join(columns)}{more}" if columns else "an empty table"
    if isinstance(item, dict):
        keys = [str(key) for key in list(item)[:4]]
        more = ", …" if len(item) > 4 else ""
        return f"statistics ({', '.join(keys)}{more})" if keys else "empty statistics"
    columns = []
    if callable(getattr(item, "to_frame", None)):
        try:
            columns = [str(column) for column in item.to_frame().columns]
        except Exception:  # noqa: BLE001 - a table that cannot build is named by its class
            columns = []
    more = ", …" if len(columns) > 4 else ""
    shown = f" ({', '.join(columns[:4])}{more})" if columns else ""
    return f"a {type(item).__name__}{shown}"


# ─── The chart ───────────────────────────────────────────────────────────────


@dataclass
class ResultChart(SurveyChart):
    """A chart of an analysis's result; see :func:`chart`.

    ``result`` is what is drawn, ``kind`` the chart asked for (``auto``: the
    one the result suits) and ``context`` the other outputs connected, read for
    what the result does not say itself (its weight, a regression's base).
    ``data`` is the result's data where it has one, else None.
    """

    result: Any = None
    kind: str = "auto"
    context: list[Any] = field(default_factory=list)
    #: The kind being drawn — what ``auto`` resolved to.
    drawn: str = field(init=False, default="")
    _room: list[tuple[Any, list[Any], str]] = field(init=False, repr=False, default_factory=list)
    _suptitle: bool = field(init=False, repr=False, default=False)
    #: The font size of the tick labels, which the axis labels follow.
    _size: float = field(init=False, repr=False, default=10.0)
    #: Room between the title and the axes, in points (a legend sits there).
    _title_pad: float = field(init=False, repr=False, default=8.0)
    #: The figure is an analysis's own, finished as drawn (:meth:`adopt`).
    _adopted: bool = field(init=False, repr=False, default=False)

    # ── building ──

    def _build(self) -> None:
        renderer = renderer_for(self.result)
        if renderer is None:
            raise ResultChartError(
                f"A Result chart cannot draw {_describe(self.result)}. It draws the results "
                f"of {_analyses()}."
            )
        kind = renderer.kinds[0] if self.kind == "auto" else self.kind
        if kind not in renderer.kinds:
            raise ResultChartError(
                f"Kind {kind!r} does not suit this result: {renderer.name} draws "
                f"{_listed(renderer.kinds)}."
            )
        self.drawn = kind
        if sns is not None:
            chart_theme.set_theme(style="whitegrid", palette=self.palette)
        self._room, self._size, self._title_pad, self._adopted = [], 10.0, 8.0, False
        title = renderer.fn(self.result, self)
        if self._fig is None:
            raise RuntimeError(f"The renderer of {renderer.name} drew no figure.")
        self._weight_note = weight_note(self.result, *self.context)
        if not self._adopted:
            self._finish(title)

    def _finish(self, title: str) -> None:
        width = self._fig.get_size_inches()[0]
        text = self._title_text(self.title or title, width * 72)
        if self._suptitle:
            self._fig.suptitle(text, fontsize=12, color=_ink())
        else:
            self._ax.set_title(text, fontsize=12, color=_ink(), loc="left", pad=self._title_pad)
        for ax in self._fig.axes:
            for label in (ax.xaxis.label, ax.yaxis.label):
                label.set_fontsize(self._size + 1)
                label.set_color(_ink())
        self._fig.tight_layout()
        self._fit_text(self.title or title)
        if self._room:
            for ax, artists, axis in self._room:
                _make_room(ax, artists, axis)
            self._fig.tight_layout()

    def _title_text(self, title: str, room_pt: float) -> str:
        """``title`` wrapped to ``room_pt`` points, the weight line under it."""
        text = textwrap.fill(" ".join(str(title).split()), max(int(room_pt / (12 * 0.55)), 20))
        return f"{text}\n{self._weight_note}" if self._weight_note else text

    def _fit_text(self, title: str) -> None:
        """The title, the axis titles and the notes wrapped to the plot as it is
        laid out: the title starts at the plot's left edge, which long row
        labels put at a third of the figure, and the figure's width is not
        all its room (a title wrapped to it ran past the edge, and the PNG was
        saved wider than asked)."""
        fig = self._fig
        width, height = (value * 72 for value in fig.get_size_inches())
        if not self._suptitle:
            left = self._ax.get_position().x0 * width
            self._ax.set_title(
                self._title_text(title, width - left - 8),
                fontsize=12,
                color=_ink(),
                loc="left",
                pad=self._title_pad,
            )
        for ax in fig.axes:
            box = ax.get_position()
            for label, length in (
                (ax.xaxis.label, box.width * width),
                (ax.yaxis.label, box.height * height),
            ):
                text = label.get_text()
                chars = max(int(length / (label.get_fontsize() * 0.55)), 12)
                if text and max(len(line) for line in text.split("\n")) > chars:
                    label.set_text(textwrap.fill(" ".join(text.split()), chars))
            for note in ax.texts:
                raw = getattr(note, "_siamang_note", None)
                if raw is not None:
                    room = width - box.x0 * width - 8
                    note.set_text(
                        textwrap.fill(raw, max(int(room / ((note.get_fontsize()) * 0.55)), 30))
                    )
        fig.tight_layout()

    # ── what a renderer asks for ──

    @property
    def stats(self) -> dict[str, Any]:
        """The statistics of the result and of the outputs beside it, the
        result's winning a key both have."""
        merged: dict[str, Any] = {}
        for item in reversed([self.result, *self.context]):
            merged.update(_stats_of(item))
        return merged

    def figure(self, *, height: float | None = None, nrows: int = 1, ncols: int = 1, **kwargs):
        """A new figure of the chart's size (``height`` overrides its height);
        returns ``(figure, axes)`` as :func:`matplotlib.pyplot.subplots` does."""
        _require_matplotlib()
        size = (self.figsize[0], height if height is not None else self.figsize[1])
        fig, axes = plt.subplots(nrows, ncols, figsize=size, **kwargs)
        self._fig = fig
        self._ax = axes if nrows * ncols == 1 else np.asarray(axes).flat[0]
        self._suptitle = nrows * ncols > 1
        return fig, axes

    def rows(
        self, labels: Sequence[Any], *, series: int = 1, legend: Sequence[str] = ()
    ) -> tuple[Any, np.ndarray, float]:
        """Axes with one row per label, the first at the top: long labels are
        wrapped, and many rows get a smaller font — the figure grows taller when
        even that cannot hold them. ``legend`` names the entries of the legend
        the chart will have, so the rows leave it room. Returns ``(axes, y
        positions, font size)``."""
        reserve = 0.0
        if legend:
            _, lines = _legend_layout(self.figsize[0], legend, 10)
            reserve = lines * 10 * 1.55 / 72 + 0.15
        wrapped, size, height = fit_rows(self.figsize, labels, series=series, reserve=reserve)
        _, ax = self.figure(height=height)
        self._size = size
        y = np.arange(len(labels), dtype=float)
        ax.set_yticks(y)
        ax.set_yticklabels(wrapped, fontsize=size, color=_ink())
        ax.set_ylim(len(labels) - 0.5, -0.5)
        ax.tick_params(axis="x", labelsize=size, colors=_ink())
        ax.grid(axis="y", visible=False)
        return ax, y, size

    def adopt(self, fig: Any) -> None:
        """Take ``fig`` as the chart's figure: one an analysis's own plot
        function drew whole — its title with the weight line, its layout, labels
        placed for that layout. The chart leaves it as drawn; titling and laying
        it out again would move what was placed."""
        self._fig = fig
        self._ax = fig.axes[0]
        self._adopted = True

    def colors(self, n: int) -> list[Any]:
        """``n`` colours of the chart's palette, in its order — never one twice:
        past the palette's own, lighter and darker ones (``series_colours``)."""
        if sns is not None:
            from siamang.reporting.chart_parts import series_colours

            return list(series_colours(self.palette, max(n, 1)))
        cmap = plt.get_cmap("tab10")
        return [cmap(i % 10) for i in range(max(n, 1))]

    def make_room(self, ax: Any, artists: list[Any], axis: str = "x") -> None:
        """Widen ``ax`` along ``axis`` until ``artists`` (value labels) fit inside it."""
        self._room.append((ax, [artist for artist in artists if artist is not None], axis))

    def legend(self, ax: Any, *, size: float | None = None, **kwargs: Any) -> Any:
        """The legend of ``ax``, in a row (or rows) between the title and the
        axes, where it covers nothing and a long label has the whole width."""
        size = size or self._size
        handles, labels = ax.get_legend_handles_labels()
        if not handles:
            return None
        columns, lines = _legend_layout(self._fig.get_size_inches()[0], labels, size)
        title = kwargs.pop("title", None)
        legend = ax.legend(
            handles,
            labels,
            loc="lower left",
            bbox_to_anchor=(0, 1.0),
            ncol=columns,
            frameon=False,
            fontsize=size,
            title=title,
            title_fontsize=size,
            alignment="left",
            borderaxespad=0.3,
            handlelength=1.4,
            columnspacing=1.4,
            **kwargs,
        )
        self._title_pad = lines * size * 1.55 + (size * 1.6 if title else 0) + 12
        return legend


# ─── helpers the renderers share ─────────────────────────────────────────────


def weight_note(*sources: Any) -> str | None:
    """What the first of ``sources`` that says anything about the weight says:
    ``unweighted (the weight 'w' is not applied)`` as it is, a weight column's
    name as ``weighted by 'w'``."""
    for source in sources:
        stats = _stats_of(source)
        for key in ("Weight", "weight"):
            value = stats.get(key)
            if isinstance(value, str) and value:
                return value if value.startswith("unweighted") else f"weighted by '{value}'"
    return None


def _stats_of(item: Any) -> dict[str, Any]:
    if isinstance(item, dict):
        return item
    if isinstance(item, pd.DataFrame):
        # A table an analysis returns bare (a regression's, a PCA's, a
        # cluster's, TURF's) carries its weight in attrs, as its stat does.
        weight = item.attrs.get("weight")
        return {"Weight": weight} if isinstance(weight, str) and weight else {}
    try:
        stats = getattr(item, "stats", None)
    except Exception:  # noqa: BLE001 - a table that cannot build has nothing to say
        return {}
    return stats if isinstance(stats, dict) else {}


def wrap(text: Any, width: int, lines: int = 3) -> str:
    """``text`` wrapped at ``width`` characters in at most ``lines`` lines, the
    last cut with an ellipsis when it does not fit."""
    width = max(int(width), 8)
    wrapped = textwrap.wrap(str(text), width=width) or [""]
    if len(wrapped) > lines:
        wrapped = wrapped[:lines]
        wrapped[-1] = wrapped[-1][: width - 1].rstrip() + "…"
    return "\n".join(wrapped)


def _legend_layout(width: float, labels: Sequence[Any], size: float) -> tuple[int, int]:
    """Columns and lines of a legend of ``labels`` across a figure ``width`` wide."""
    longest = max((len(str(label)) for label in labels), default=1)
    room = width * 0.62 * 72
    columns = max(1, min(len(labels), int(room // (longest * size * 0.55 + 34))))
    return columns, math.ceil(len(labels) / columns)


def fit_rows(
    figsize: tuple[float, float],
    labels: Sequence[Any],
    *,
    series: int = 1,
    reserve: float = 0.0,
) -> tuple[list[str], float, float]:
    """Wrapped labels, their font size and the figure height for one row per
    label: the largest font (10 pt down to 7) and the most lines (3, or 4 at
    8 pt) at which every label is whole and the rows fit the figure's height;
    when none does, the figure grows at 9 or 8 pt rather than cut a label. A
    label is cut with an ellipsis only past four lines of 8 pt, and never so
    that two different labels read alike. ``reserve`` is height taken by
    something else, a legend, in inches."""
    width, height = float(figsize[0]), float(figsize[1])
    chrome = _CHROME + reserve
    count = max(len(labels), 1)
    extra = 0.12 * max(series - 1, 0)

    def layout(size: float, lines: int) -> tuple[list[str], float, bool]:
        chars = int(0.34 * width * 72 / (size * 0.55))
        wrapped = [wrap(label, chars, lines) for label in labels]
        whole = [wrap(label, chars, 1000) for label in labels]
        cut = wrapped != whole
        if cut:
            # Two labels that differ only past the cut would read alike: those
            # keep every line.
            seen: dict[str, int] = {}
            for text in wrapped:
                seen[text] = seen.get(text, 0) + 1
            wrapped = [
                full if seen[text] > 1 else text for text, full in zip(wrapped, whole, strict=True)
            ]
        tallest = max((label.count("\n") + 1 for label in wrapped), default=1)
        need = count * (tallest * size * 1.25 / 72 + 0.06 + extra)
        return wrapped, need, cut

    for size, lines in ((10, 3), (9, 3), (8, 3), (8, 4), (7, 2), (7, 1)):
        wrapped, need, cut = layout(size, lines)
        if not cut and need <= height - chrome:
            # Few rows do not stretch across a tall figure: a row is at most
            # _PITCH high (more with several series in it).
            most = count * (_PITCH + 2 * extra) + chrome
            return wrapped, size, max(min(height, most), min(height, _SHORTEST))
    for size, lines in ((9, 3), (8, 3), (8, 4)):
        wrapped, need, cut = layout(size, lines)
        if not cut:
            return wrapped, size, max(height, need + chrome)
    wrapped, need, _ = layout(8, 4)
    return wrapped, 8, max(height, need + chrome)


def _make_room(ax: Any, artists: list[Any], axis: str) -> None:
    """Widen the limits of ``ax`` along ``axis`` until ``artists`` lie inside
    it — through the data transform, so a log scale widens as a log scale."""
    if not artists:
        return
    fig = ax.figure
    along = 0 if axis == "x" else 1
    for _ in range(4):
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        box = ax.get_window_extent(renderer).get_points()  # [[x0, y0], [x1, y1]]
        extents = [artist.get_window_extent(renderer).get_points() for artist in artists]
        low_edge = min(extent[0][along] for extent in extents) - 3
        high_edge = max(extent[1][along] for extent in extents) + 3
        if low_edge >= box[0][along] and high_edge <= box[1][along]:
            return
        inverse = ax.transData.inverted()
        corner = box[0].copy()
        limits = list(ax.get_xlim() if axis == "x" else ax.get_ylim())
        if low_edge < box[0][along]:
            corner[along] = low_edge
            limits[0] = float(inverse.transform(corner)[along])
        if high_edge > box[1][along]:
            corner[along] = high_edge
            limits[1] = float(inverse.transform(corner)[along])
        if axis == "x":
            ax.set_xlim(*limits)
        else:
            ax.set_ylim(*limits)


def _label(
    ax: Any, x: float, y: float, text: str, size: float, *, left: bool = False, **kwargs: Any
) -> Any:
    """A value label just beside ``(x, y)`` — to its right, or left of it."""
    if x is None or x != x:
        return None
    return ax.annotate(
        text,
        (x, y),
        xytext=(-4 if left else 4, 0),
        textcoords="offset points",
        ha="right" if left else "left",
        va="center",
        fontsize=size - 0.5,
        color=_ink(),
        **kwargs,
    )


def _number(value: Any, digits: int = 2, *, thousands: bool = False) -> str:
    if value is None or value != value:
        return ""
    text = f"{float(value):,.{digits}f}" if thousands else f"{float(value):.{digits}f}"
    return text[1:] if text.startswith("-") and float(text.replace(",", "")) == 0 else text


def _mean_axis_thousands(ax: Any) -> None:
    """A means axis of thousands (a mean income) separates them, as the Bar
    chart's counts do: 40,000, not 40000."""
    if max(abs(value) for value in ax.get_xlim()) >= 1000:
        from siamang.reporting.chart_parts import thousands_axis

        thousands_axis(ax.xaxis)


def _digits(values: Any) -> int:
    """Two decimals, or three for numbers that all lie within ±1 (a MaxDiff
    score, a part-worth), so no two of them print alike."""
    array = np.abs(np.asarray(values, dtype=float))
    array = array[np.isfinite(array)]
    return 3 if array.size and float(array.max()) < 1 else 2


def _percent(value: Any, digits: int = 1) -> str:
    if value is None or value != value:
        return ""
    return f"{float(value):.{digits}f} %"


def _hide_spines(ax: Any, *sides: str) -> None:
    for side in sides or ("top", "right"):
        ax.spines[side].set_visible(False)


def _confidence(confidence: float) -> str:
    return f"{confidence * 100:g} %"


def _dots(
    chart: ResultChart,
    labels: Sequence[Any],
    series: list[dict[str, Any]],
    *,
    reference: float | None = None,
    legend_title: str | None = None,
    dodge: bool = True,
) -> tuple[Any, float]:
    """One row per label; each series a point with its interval (``estimate``,
    ``lower``, ``upper``, ``text`` per row, a ``label`` and a ``color``),
    dodged within the row when there are several. Returns the axes and the
    font size."""
    names = [str(item["label"]) for item in series if item.get("label")] if len(series) > 1 else []
    ax, y, size = chart.rows(labels, series=len(series) if dodge else 1, legend=names)
    count = len(series)
    offsets = np.linspace(-0.22, 0.22, count) if count > 1 and dodge else np.zeros(count)
    artists = []
    for offset, item in zip(offsets, series, strict=True):
        estimate = np.asarray(item["estimate"], dtype=float)
        lower = np.asarray(item["lower"], dtype=float)
        upper = np.asarray(item["upper"], dtype=float)
        rows = y + offset
        whiskers = ~np.isnan(lower) & ~np.isnan(upper)
        color = item["color"]
        ax.hlines(
            rows[whiskers], lower[whiskers], upper[whiskers], color=color, linewidth=2, zorder=2
        )
        ax.plot(
            estimate,
            rows,
            "o",
            color=color,
            markersize=7 if count == 1 else 6,
            markeredgecolor="white",
            markeredgewidth=1,
            zorder=3,
            label=item.get("label"),
            linestyle="none",
        )
        for row, value, top, text in zip(rows, estimate, upper, item["text"], strict=True):
            end = top if top == top else value
            artists.append(_label(ax, end, row, text, size if count == 1 else size - 1))
    if reference is not None:
        ax.axvline(reference, color=_muted(), linewidth=1, zorder=1)
    if count > 1:
        chart.legend(ax, title=legend_title)
    _hide_spines(ax)
    chart.make_room(ax, artists)
    return ax, size


def _bars(
    chart: ResultChart,
    labels: Sequence[Any],
    values: Sequence[Any],
    texts: Sequence[str],
    *,
    color: Any = None,
    reference: float | None = 0.0,
) -> tuple[Any, np.ndarray, float]:
    """Horizontal bars, one per label, each with its value beside it (left of
    a negative bar). Returns the axes, the row positions and the font size."""
    ax, y, size = chart.rows(labels)
    numbers = np.asarray([np.nan if v is None else v for v in values], dtype=float)
    ax.barh(y, np.nan_to_num(numbers), height=0.66, color=color or chart.colors(1)[0], zorder=2)
    artists = [
        _label(ax, value, row, text, size, left=value < 0)
        for row, value, text in zip(y, numbers, texts, strict=True)
        if value == value
    ]
    if reference is not None:
        ax.axvline(reference, color=_muted(), linewidth=1, zorder=1)
    _hide_spines(ax)
    chart.make_room(ax, artists)
    return ax, y, size


def _mark_note(ax: Any, text: str, size: float) -> None:
    """A note under the axis label (what the letters mean, what a base is),
    wrapped to the width of the axes."""
    width = ax.figure.get_size_inches()[0] * 0.62 * 72
    note = ax.annotate(
        textwrap.fill(text, max(int(width / ((size - 1) * 0.52)), 40)),
        (0, 0),
        xycoords=("axes fraction", ax.xaxis.label),
        xytext=(0, -4),
        textcoords="offset points",
        ha="left",
        va="top",
        fontsize=size - 1,
        color=_muted(),
    )
    note._siamang_note = text  # rewrapped to the laid-out plot (ResultChart._fit_text)


# ─── Means: Group means, Descriptive statistics, t-test, Paired tests ────────


def _means_series(
    chart: ResultChart,
    intervals: list[Any],
    sds: list[Any],
    means: list[Any],
    *,
    digits: int = 2,
) -> tuple[list[float], list[float], list[float], list[str]]:
    """Estimates, lower and upper ends, and value labels for the kind drawn:
    ``means`` the confidence interval, ``means_sd`` one SD either side."""
    estimate, lower, upper, texts = [], [], [], []
    for interval, sd, mean in zip(intervals, sds, means, strict=True):
        value = float(mean) if mean is not None and mean == mean else float("nan")
        estimate.append(value)
        if chart.drawn == "means_sd":
            spread = float(sd) if sd is not None and sd == sd else float("nan")
            lower.append(value - spread)
            upper.append(value + spread)
            texts.append(
                _number(value, digits, thousands=True)
                + ("" if spread == spread else " (one answer: no SD)")
            )
        else:
            lower.append(interval.lower if interval.defined else float("nan"))
            upper.append(interval.upper if interval.defined else float("nan"))
            note = "" if interval.defined or value != value else f" ({interval.note})"
            texts.append(_number(value, digits, thousands=True) + note)
    return estimate, lower, upper, texts


def _means_axis(chart: ResultChart, what: str, confidence: float = 0.95) -> str:
    if chart.drawn == "means_sd":
        return f"{what}, ± 1 SD"
    return f"{what} with its {_confidence(confidence)} confidence interval"


def _group_mean_samples(table: Any) -> list[tuple[np.ndarray, np.ndarray | None]]:
    """The answers (and weights) behind each row of a Group means table, in its
    order — the rows :class:`~siamang.reporting.tables.GroupMeanTable` reads."""
    from siamang.data import multi
    from siamang.reporting.tables import _get_value_labels, _weights_of

    data = table.data
    frame = data.frame
    samples: list[tuple[np.ndarray, np.ndarray | None]] = []
    if multi.is_multi(frame[table.by]):
        series = frame[table.by]
        values = pd.to_numeric(frame[table.column], errors="coerce")
        weights = _weights_of(data, frame.index)
        labels = _get_value_labels(data, table.by)
        for code in labels or multi.codes_in(series):
            chose = (multi.reach(series, code) & multi.responded(series) & values.notna()).to_numpy(
                dtype=bool
            )
            samples.append(
                (
                    values[chose].to_numpy(dtype=float),
                    None if weights is None else weights[chose].to_numpy(dtype=float),
                )
            )
        return samples
    source = frame
    if table._chosen():
        from siamang.data.inference import without_missing_codes

        source, _ = without_missing_codes(source, [table.column, table.by], data.variables)
    rows = source[[table.column, table.by]].dropna()
    weights = _weights_of(data, rows.index)
    grouped = rows.assign(_w=np.ones(len(rows)) if weights is None else weights.to_numpy())
    for _value, group in grouped.groupby(table.by):
        samples.append(
            (
                pd.to_numeric(group[table.column], errors="coerce").to_numpy(dtype=float),
                None if weights is None else group["_w"].to_numpy(dtype=float),
            )
        )
    return samples


def _draw_group_means(table: Any, chart: ResultChart) -> str:
    from siamang.data.intervals import mean_interval
    from siamang.reporting.tables import _get_label

    frame = table.to_frame()
    by_label = str(frame.columns[0])
    labels = [str(value) for value in frame[by_label]]
    samples = _group_mean_samples(table)
    if len(samples) != len(frame):  # pragma: no cover - the rows are the table's own
        raise RuntimeError("Group means: the rows read do not match the table's.")
    intervals = [mean_interval(values, weights) for values, weights in samples]
    estimate, lower, upper, texts = _means_series(
        chart, intervals, list(frame["SD"]), list(frame["Mean"])
    )
    marks = _posthoc_letters(table, labels, estimate)
    if marks:
        texts = [
            f"{text}   {marks.get(label, '')}".rstrip()
            for text, label in zip(texts, labels, strict=True)
        ]
    ax, size = _dots(
        chart,
        _with_n(labels, frame["N"]),
        [
            {
                "estimate": estimate,
                "lower": lower,
                "upper": upper,
                "text": texts,
                "color": chart.colors(1)[0],
            }
        ],
    )
    column = _get_label(table.data, table.column)
    weighted = table.data.weight is not None
    ax.set_xlabel(_means_axis(chart, f"{'Weighted mean' if weighted else 'Mean'}"), color=_ink())
    _mean_axis_thousands(ax)
    if marks:
        posthoc = table.posthoc_table.result
        _mark_note(
            ax,
            f"Means sharing a letter do not differ ({posthoc.name}, p < .05).",
            size,
        )
    return f"{column} by {by_label}"


def _with_n(labels: Sequence[Any], counts: Any) -> list[str]:
    """Each row's label with its base, ``North (n = 97)``: an interval is read
    with the number of answers behind it."""
    return [
        f"{label} (n = {int(count):,})" if count == count and count is not None else str(label)
        for label, count in zip(labels, counts, strict=True)
    ]


def _posthoc_letters(table: Any, labels: list[str], estimate: list[float]) -> dict[str, str]:
    """The compact letter display of a Group means table's post-hoc pairs."""
    posthoc = table.posthoc_table
    if posthoc is None:
        return {}
    pairs = posthoc.result.table
    named = set(pairs["group_1"].astype(str)) | set(pairs["group_2"].astype(str))
    groups = [
        label
        for label, value in sorted(
            zip(labels, estimate, strict=True),
            key=lambda item: -item[1] if item[1] == item[1] else math.inf,
        )
        if label in named
    ]
    different = [
        (str(a), str(b))
        for a, b, p in zip(pairs["group_1"], pairs["group_2"], pairs["p_adjusted"], strict=True)
        if p == p and p < 0.05
    ]
    return letters(groups, different)


def letters(groups: Sequence[str], different: Sequence[tuple[str, str]]) -> dict[str, str]:
    """The compact letter display: groups that share a letter do not differ.

    Piepho's insert-and-absorb algorithm (2004, *Journal of Computational and
    Graphical Statistics* 13, 456–466), as R's ``multcompView`` implements it:
    every group starts in one letter's set; each pair that differs splits every
    set holding both into two, one without each; a set inside another is then
    absorbed. The letters are given in ``groups``' order, so with the groups
    ordered by mean, highest first, the highest has ``a``.
    """

    order = {group: index for index, group in enumerate(groups)}
    sets: list[set[str]] = [set(groups)] if groups else []
    for first, second in different:
        if first not in order or second not in order:
            continue
        split: list[set[str]] = []
        for members in sets:
            if first in members and second in members:
                split += [members - {second}, members - {first}]
            else:
                split.append(members)
        sets = []
        for index, members in enumerate(split):
            inside = any(
                members < other or (members == other and later < index)
                for later, other in enumerate(split)
                if later != index
            )
            if members and not inside:
                sets.append(members)
    sets.sort(key=lambda members: min(order[group] for group in members))
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return {
        group: "".join(
            alphabet[index % len(alphabet)]
            for index, members in enumerate(sets)
            if group in members
        )
        for group in groups
    }


def _draw_descriptives(table: Any, chart: ResultChart) -> str:
    from siamang.data import descriptives
    from siamang.data.intervals import mean_interval

    frame = table.to_frame()
    data = table.data
    variables = data.variables
    by_label = None if not table.by else descriptives._label(variables, table.by)
    raw = data.frame.reset_index(drop=True)
    weights = descriptives._weights(raw, data.weight)
    groups = (
        descriptives._groups(raw, table.by, variables) if table.by else [(None, None, raw.index)]
    )
    intervals = []
    for name in dict.fromkeys(table.columns):
        values, _, _ = descriptives._numeric(raw[name], descriptives._variable(variables, name))
        for _value, _label_text, index in groups:
            usable = values.loc[index].dropna()
            intervals.append(
                mean_interval(
                    usable.to_numpy(dtype=float),
                    None if weights is None else weights.loc[usable.index].to_numpy(dtype=float),
                )
            )
    if len(intervals) != len(frame):  # pragma: no cover - the rows are the table's own
        raise RuntimeError("Descriptive statistics: the rows read do not match the table's.")
    frame = frame.assign(_interval=intervals)
    # A row per variable, named by its label — and by its name too where two
    # variables share a label (the same question asked twice).
    rows = list(dict.fromkeys(frame["Variable"].astype(str)))
    label_of = dict(zip(frame["Variable"].astype(str), frame["Label"].astype(str), strict=False))
    shown = [label_of[name] for name in rows]
    shown = [
        f"{label} ({name})" if shown.count(label) > 1 else label
        for label, name in zip(shown, rows, strict=True)
    ]
    names = [None] if by_label is None else list(dict.fromkeys(frame[by_label].astype(str)))
    colors = chart.colors(len(names))
    if _separate_scales(frame, rows):
        return _descriptives_panels(chart, frame, rows, shown, names, colors, by_label, data)
    if by_label is None:  # one series: each row's base beside its label
        counts = dict(zip(frame["Variable"].astype(str), frame["N"], strict=False))
        shown = _with_n(shown, [counts.get(name) for name in rows])
    series = []
    for name, color in zip(names, colors, strict=True):
        part = frame if name is None else frame[frame[by_label].astype(str) == name]
        found = {
            str(variable): row
            for variable, (_, row) in zip(part["Variable"], part.iterrows(), strict=True)
        }
        picked = [found.get(label) for label in rows]
        estimate, lower, upper, texts = _means_series(
            chart,
            [row["_interval"] if row is not None else _no_interval() for row in picked],
            [row["SD"] if row is not None else None for row in picked],
            [row["Mean"] if row is not None else None for row in picked],
        )
        series.append(
            {
                "estimate": estimate,
                "lower": lower,
                "upper": upper,
                "text": texts,
                "color": color,
                "label": name if name is None else f"{name} ({_n_range(part['N'])})",
            }
        )
    ax, _ = _dots(chart, shown, series, legend_title=by_label)
    weighted = data.weight is not None
    ax.set_xlabel(_means_axis(chart, "Weighted mean" if weighted else "Mean"), color=_ink())
    _mean_axis_thousands(ax)
    return "Means" if by_label is None else f"Means by {by_label}"


#: Variables whose means reach further than this many times one another are
#: drawn each on a scale of its own: an income and an age on one axis put the
#: ages at 0, their intervals and value labels on top of one another.
SCALE_RATIO = 5.0


def _separate_scales(frame: pd.DataFrame, rows: list[str]) -> bool:
    """Whether the variables of a Descriptive statistics table need a panel
    each: two or more, the furthest reach of one's means and intervals more
    than :data:`SCALE_RATIO` times another's."""
    if len(rows) < 2:
        return False
    reach = []
    for name in rows:
        part = frame[frame["Variable"].astype(str) == name]
        ends = [abs(float(value)) for value in part["Mean"] if value == value and value is not None]
        ends += [
            abs(float(end))
            for interval in part["_interval"]
            if interval.defined
            for end in (interval.lower, interval.upper)
        ]
        if ends:
            reach.append(max(ends))
    positive = [value for value in reach if value > 0]
    return len(positive) >= 2 and max(positive) > SCALE_RATIO * min(positive)


def _descriptives_panels(
    chart: ResultChart,
    frame: pd.DataFrame,
    rows: list[str],
    shown: list[str],
    names: list[Any],
    colors: list[Any],
    by_label: str | None,
    data: Any,
) -> str:
    """A panel per variable, one above the other, each on its own scale; in a
    panel a row per group (named with its base), in the group's colour."""
    from siamang.reporting.chart_parts import wrap as wrap_words

    per_panel = [
        [
            # Without By the panel's title names the variable: its row, the base.
            (f"n = {int(n):,}" if by_label is None else f"{name} (n = {int(n):,})")
            if n == n and n is not None
            else str(name)
            for name, n in _panel_bases(frame, row, names, by_label)
        ]
        for row in rows
    ]
    labels = [label for panel in per_panel for label in panel]
    wrapped, size, _ = fit_rows(chart.figsize, labels, series=1)
    lines = max(text.count("\n") + 1 for text in wrapped)
    row_in = lines * size * 1.25 / 72 + 0.12
    heights = [len(panel) * row_in + 0.5 for panel in per_panel]
    height = max(chart.figsize[1], sum(heights) + _CHROME)
    fig, axes = chart.figure(
        height=height,
        nrows=len(rows),
        ncols=1,
        squeeze=False,
        gridspec_kw={"height_ratios": [len(panel) for panel in per_panel]},
    )
    chart._size = size
    chars = int(0.34 * chart.figsize[0] * 72 / (size * 0.55))
    weighted = data.weight is not None
    for index, (row, title, panel) in enumerate(zip(rows, shown, per_panel, strict=True)):
        ax = axes[index][0]
        part = frame[frame["Variable"].astype(str) == row]
        by_group = (
            {None: part.iloc[0]}
            if by_label is None
            else {
                str(group): record
                for group, (_, record) in zip(part[by_label], part.iterrows(), strict=True)
            }
        )
        y = np.arange(len(names), dtype=float)
        ax.set_yticks(y)
        ax.set_yticklabels(
            [_wrap_with_base(label, chars, wrap_words) for label in panel],
            fontsize=size,
            color=_ink(),
        )
        ax.set_ylim(len(names) - 0.5, -0.5)
        ax.tick_params(axis="x", labelsize=size, colors=_ink())
        ax.grid(axis="y", visible=False)
        artists = []
        for position, (name, color) in enumerate(zip(names, colors, strict=True)):
            record = by_group.get(name if name is None else str(name))
            if record is None:
                continue
            estimate, lower, upper, texts = _means_series(
                chart, [record["_interval"]], [record["SD"]], [record["Mean"]]
            )
            if lower[0] == lower[0] and upper[0] == upper[0]:
                ax.hlines(position, lower[0], upper[0], color=color, linewidth=2, zorder=2)
            ax.plot(
                estimate,
                [position],
                "o",
                color=color,
                markersize=7,
                markeredgecolor="white",
                markeredgewidth=1,
                zorder=3,
                linestyle="none",
            )
            end = upper[0] if upper[0] == upper[0] else estimate[0]
            artists.append(_label(ax, end, position, texts[0], size))
        ax.set_title(title, loc="left", fontsize=size + 1, color=_ink())
        _hide_spines(ax)
        chart.make_room(ax, artists)
        _mean_axis_thousands(ax)
    axes[-1][0].set_xlabel(
        _means_axis(chart, "Weighted mean" if weighted else "Mean"), color=_ink()
    )
    what = "Means" if by_label is None else f"Means by {by_label}"
    return f"{what}, each variable on its own scale"


def _wrap_with_base(label: str, chars: int, wrap_words: Any) -> str:
    """``label`` wrapped, its "(n = 67)" kept on one line."""
    held = re.sub(r"\(n = ([^)]*)\)", lambda match: f"(n\u00a0=\u00a0{match.group(1)})", label)
    return wrap_words(held, chars).replace("\u00a0", " ")


def _panel_bases(
    frame: pd.DataFrame, row: str, names: list[Any], by_label: str | None
) -> list[tuple[Any, Any]]:
    """Each group's name (the variable's, without By) and its base, for one
    variable's panel."""
    part = frame[frame["Variable"].astype(str) == row]
    if by_label is None:
        return [(part["Label"].iloc[0], part["N"].iloc[0])]
    counts = dict(zip(part[by_label].astype(str), part["N"], strict=False))
    return [(name, counts.get(str(name))) for name in names]


def _n_range(counts: Any) -> str:
    """``n = 97``, or ``n = 90–97`` when the variables' bases differ."""
    values = [int(value) for value in counts if value == value and value is not None]
    if not values:
        return "n = 0"
    low, high = min(values), max(values)
    return f"n = {low:,}" if low == high else f"n = {low:,}–{high:,}"


def _no_interval() -> Any:
    from siamang.data.intervals import Interval

    return Interval(float("nan"), None, None, 0, 0.95, "", note="no answers")


def _draw_ttest(table: Any, chart: ResultChart) -> str:
    from siamang.data.intervals import t_interval
    from siamang.reporting.tables import _get_label, stat_text

    frame = table.to_frame()
    first = str(frame.columns[0])
    if table.kind == "paired":
        frame = frame.iloc[:2]  # the two measurements; their difference is the test's
    confidence = float(table.confidence)
    intervals = [
        t_interval(row["Mean"], row["SD"], row["N"], confidence=confidence)
        for _, row in frame.iterrows()
    ]
    labels = [str(value) for value in frame[first]]
    estimate, lower, upper, texts = _means_series(
        chart, intervals, list(frame["SD"]), list(frame["Mean"])
    )
    stats = table.stats
    ax, size = _dots(
        chart,
        _with_n(labels, frame["N"]),
        [
            {
                "estimate": estimate,
                "lower": lower,
                "upper": upper,
                "text": texts,
                "color": chart.colors(1)[0],
            }
        ],
        reference=float(table.mu) if table.kind == "one_sample" else None,
    )
    ax.set_xlabel(_means_axis(chart, "Mean", confidence), color=_ink())
    _mean_axis_thousands(ax)
    ci = f"{confidence * 100:g}% CI"
    if stats.get("Mean difference") is not None and stats.get(ci):
        note = (
            f"{stats['Test']}: difference {stats['Difference']} = {stats['Mean difference']} "
            f"({ci} {stats[ci]}), p = {stat_text(stats['p'])}"
        )
        if table.kind == "one_sample":
            note += f"; the line is the test value, {table.mu:g}"
        _mark_note(ax, note, size)
    elif str(stats.get("Test", "")).startswith("not run"):
        _mark_note(ax, f"Test {stats['Test']}", size)
    column = _get_label(table.data, table.column)
    if table.kind == "independent":
        return f"{column} by {first}"
    if table.kind == "paired":
        return f"{column} and {labels[1]}: the same respondents" if len(labels) > 1 else column
    return column


def _is_paired_table(table: Any) -> bool:
    columns = [str(column) for column in table.to_frame().columns]
    return columns[:5] == ["Variable", "N", "Mean", "SD", "Median"]


def _is_mcnemar_table(table: Any) -> bool:
    columns = [str(column) for column in table.to_frame().columns]
    return (
        len(columns) == 4
        and columns[3] == "Total"
        and columns[1].endswith(": yes")
        and columns[2].endswith(": no")
    )


def _draw_paired(table: Any, chart: ResultChart) -> str:
    from siamang.data.intervals import t_interval

    frame = table.to_frame()
    frame = frame[~frame["Variable"].astype(str).str.startswith("Difference (")]
    intervals = [t_interval(row["Mean"], row["SD"], row["N"]) for _, row in frame.iterrows()]
    estimate, lower, upper, texts = _means_series(
        chart, intervals, list(frame["SD"]), list(frame["Mean"])
    )
    ax, size = _dots(
        chart,
        [str(value) for value in frame["Variable"]],
        [
            {
                "estimate": estimate,
                "lower": lower,
                "upper": upper,
                "text": texts,
                "color": chart.colors(1)[0],
            }
        ],
    )
    ax.set_xlabel(_means_axis(chart, "Mean"), color=_ink())
    _mean_axis_thousands(ax)
    stats = table.stats
    n = stats.get("N")
    _mark_note(
        ax,
        f"The same {n} respondents answered each; the test compares their ranks — "
        f"{_test_line(stats)}.",
        size,
    )
    return f"{stats.get('Test', 'Paired test')}: means of the measurements"


def _test_line(stats: dict[str, Any]) -> str:
    """The test and its p as the table's footer prints them, or why there is none."""
    from siamang.reporting.tables import stat_text

    test = stats.get("Test", "the test")
    if stats.get("p") is None:
        return f"{test}: {stats.get('Note', 'not run')}"
    return f"{test}, p = {stat_text(stats['p'])}"


def _draw_mcnemar(table: Any, chart: ResultChart) -> str:
    from siamang.data.intervals import proportion_interval

    frame = table.to_frame()
    columns = [str(column) for column in frame.columns]
    first = columns[0]
    second = columns[1][: -len(": yes")]
    total = frame.iloc[-1]
    n = int(total["Total"])
    yes = [int(frame.iloc[0]["Total"]), int(total[columns[1]])]
    intervals = [proportion_interval(count, n) for count in yes]
    estimate = [interval.estimate * 100 for interval in intervals]
    ax, size = _dots(
        chart,
        [first, second],
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
    ax.set_xlim(0, 100)
    ax.set_xlabel("Share saying yes (%) with its 95 % confidence interval (Wilson)", color=_ink())
    stats = table.stats
    _mark_note(
        ax,
        f"The same {n} respondents answered both; counts as yes: "
        f"{stats.get('Counts as yes', '')}; {_test_line(stats)}.",
        size,
    )
    return "McNemar: the share saying yes to each"


# ─── Proportion CI and Net Promoter Score ────────────────────────────────────


def _is_proportion(result: Any) -> bool:
    return {"p", "lower", "upper", "n"} <= set(result)


def _draw_proportion(result: dict[str, Any], chart: ResultChart) -> str:
    fig, ax = chart.figure()
    share, low, high = (float(result[key]) * 100 for key in ("p", "lower", "upper"))
    color = chart.colors(1)[0]
    ax.hlines(0, 0, 100, color=_track(), linewidth=10, zorder=1)
    ax.hlines(0, low, high, color=color, linewidth=10, alpha=0.45, zorder=2)
    ax.plot([share], [0], "o", color=color, markersize=14, markeredgecolor="white", zorder=3)
    ax.set_xlim(-2, 102)
    ax.set_ylim(-1, 1.2)
    ax.set_yticks([])
    ax.grid(False)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.set_xticks(range(0, 101, 10))
    ax.set_xticklabels([f"{tick} %" for tick in range(0, 101, 10)], color=_ink())
    ax.text(50, 0.7, _percent(share), ha="center", va="center", fontsize=30, color=_ink())
    weighted = "weight" in result and not str(result["weight"]).startswith("unweighted")
    base = float(result["n"])
    base_text = f"effective base {base:.1f}" if weighted else f"base {int(round(base))} respondents"
    # What the share is of and the interval's level: a 90 % interval is not
    # drawn as a 95 % one (proportion_ci's result says both; a bare dict not).
    level = getattr(result, "confidence", None)
    interval = f"{_confidence(level)} confidence interval" if level else "confidence interval"
    ax.text(
        50,
        -0.55,
        f"{interval} {low:.1f} – {high:.1f} %, {base_text}",
        ha="center",
        va="center",
        fontsize=11,
        color=_muted(),
    )
    variable = getattr(result, "variable_label", None)
    if variable:
        return f"{variable}: {getattr(result, 'value_label', '')}".rstrip(": ")
    return "Proportion"


def _draw_nps(table: Any, chart: ResultChart) -> str:
    frame = table.to_frame().set_index("Group")
    stats = table.stats
    fig, ax = chart.figure()
    colors = {"Detractors": _negative(), "Passives": _neutral(), "Promoters": _positive()}
    start = 0.0
    for group, color in colors.items():
        share = float(frame.loc[group, "%"])
        ax.barh(
            0,
            share,
            left=start,
            height=0.5,
            color=color,
            edgecolor="white",
            linewidth=2,
            label=f"{group} ({frame.loc[group, 'Range']}): {share:.1f} %",
        )
        if share >= 7:
            ax.text(
                start + share / 2,
                0,
                f"{share:.1f} %",
                ha="center",
                va="center",
                fontsize=11,
                color=chart_theme.ink_on(color, "white" if group != "Passives" else _INK),
            )
        start += share
    ax.set_xlim(0, 100)
    ax.set_ylim(-1.1, 1.3)
    ax.set_yticks([])
    ax.grid(False)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.set_xticks(range(0, 101, 20))
    ax.set_xticklabels([f"{tick} %" for tick in range(0, 101, 20)], color=_ink())
    score = stats.get("NPS")
    if score is not None:
        low, high = stats.get("CI95 low"), stats.get("CI95 high")
        interval = f" (95 % CI {low:+.1f} to {high:+.1f})" if low is not None else ""
        ax.text(
            50,
            0.85,
            f"NPS {score:+.1f}{interval}",
            ha="center",
            va="center",
            fontsize=18,
            color=_ink(),
        )
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, 0.2),
        ncol=3,
        frameon=False,
        fontsize=10,
    )
    ax.set_xlabel(f"Share of the {stats.get('N valid', '')} respondents who answered", color=_ink())
    return f"Net Promoter Score: {stats.get('Variable', table.column)}"


# ─── TURF ────────────────────────────────────────────────────────────────────


def _is_turf_search(table: Any) -> bool:
    return getattr(table, "method", None) != "fixed" and "size" in table.columns


def _is_turf_fixed(table: Any) -> bool:
    return getattr(table, "method", None) == "fixed" and "option" in table.columns


def _draw_turf_reach(table: Any, chart: ResultChart) -> str:
    fig, ax = chart.figure()
    count = len(table)
    x = np.arange(count, dtype=float)
    reach = table["reach_percent"].to_numpy(dtype=float)
    added = table["incremental_percent"].to_numpy(dtype=float)
    color = chart.colors(1)[0]
    ax.plot(
        x, reach, "-o", color=color, linewidth=2, markersize=8, markeredgecolor="white", zorder=3
    )
    width = float(chart.figsize[0])
    per_slot = max(int(width * 0.8 * 72 / max(count, 1) / (9 * 0.55)), 10)
    names = _named_options(getattr(table, "labels", None) or {})
    # Each size is named by what it adds to the portfolio before it — the step
    # a TURF curve shows; a best portfolio that is not the last one plus one
    # option is listed in full under the chart.
    portfolios = [[item.strip() for item in str(items).split(",")] for items in table["items"]]
    ticks, listed = [], []
    for index, (size, portfolio) in enumerate(zip(table["size"], portfolios, strict=True)):
        before = portfolios[index - 1] if index else []
        new = [item for item in portfolio if item not in before]
        grows = set(before) <= set(portfolio)
        shown = ", ".join(str(names.get(item, item)) for item in new)
        text = ("+ " + shown) if index and grows else shown if not index else "a new set"
        ticks.append(f"{int(size)}\n" + _whole_words(text, per_slot, 4))
        if not grows:
            listed.append(
                f"{int(size)}: " + ", ".join(str(names.get(item, item)) for item in portfolio)
            )
    ax.set_xticks(x)
    ax.set_xticklabels(ticks, fontsize=9 if count <= 6 else 8, color=_ink())
    artists = []
    for position, value, gain, first in zip(x, reach, added, range(count), strict=True):
        text = _percent(value) + ("" if first == 0 else f"\n(+{gain:.1f})")
        artists.append(
            ax.annotate(
                text,
                (position, value),
                xytext=(0, 8),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=9,
                color=_ink(),
            )
        )
    ax.set_ylim(0, 100)
    ax.set_yticks(range(0, 101, 20))
    ax.set_yticklabels([f"{tick} %" for tick in range(0, 101, 20)], color=_ink())
    ax.set_xlim(-0.5, count - 0.5)
    ax.grid(axis="x", visible=False)
    ax.set_ylabel("Reach: respondents who chose at least one", color=_ink())
    ax.set_xlabel(
        f"Portfolio size and the option the {'best' if table.method == 'best' else 'greedy'} "
        f"portfolio of that size adds (base {table.base} respondents)",
        color=_ink(),
    )
    if listed:
        _mark_note(ax, "The best portfolios of " + "; ".join(listed) + ".", 10.0)
    _hide_spines(ax)
    chart.make_room(ax, artists, "y")
    return "TURF: reach by portfolio size"


def _whole_words(text: str, width: int, lines: int) -> str:
    """``text`` wrapped at ``width`` characters, a word never broken, in at
    most ``lines`` lines (the last cut with an ellipsis)."""
    wrapped = textwrap.wrap(text, width=max(width, 8), break_long_words=False) or [""]
    if len(wrapped) > lines:
        wrapped = wrapped[:lines]
        wrapped[-1] = wrapped[-1][: max(width, 8) - 1].rstrip() + "…"
    return "\n".join(wrapped)


def _named_options(names: dict[Any, Any]) -> dict[Any, str]:
    """The options by their own names: an exploded question's options are all
    labelled "Question: option", and the question on every tick left no room
    for the option ("App features they would use: Focus sessions")."""
    from siamang.reporting.chart_parts import common_prefix

    keys = list(names)
    _, labels = common_prefix([names[key] for key in keys])
    return dict(zip(keys, labels, strict=True))


def _draw_turf_items(table: Any, chart: ResultChart) -> str:
    frame = pd.DataFrame(table)
    options = frame[frame["option"] != "(portfolio)"]
    whole = frame[frame["option"] == "(portfolio)"]
    from siamang.reporting.chart_parts import common_prefix

    _, labels = common_prefix([str(value) for value in options["label"]])
    ax, y, size = chart.rows(
        labels, legend=["Reach", "Reached by this option only", "All together"]
    )
    light, dark = _track(), chart.colors(1)[0]
    reach = options["reach_percent"].to_numpy(dtype=float)
    unique = options["unique_percent"].to_numpy(dtype=float)
    ax.barh(y, reach, height=0.66, color=light, zorder=2, label="Reach")
    ax.barh(y, unique, height=0.66, color=dark, zorder=3, label="Reached by this option only")
    artists = [
        _label(ax, value, row, f"{value:.1f} % ({only:.1f} % only)", size)
        for row, value, only in zip(y, reach, unique, strict=True)
    ]
    if len(whole):
        total = float(whole["reach_percent"].iloc[0])
        ax.axvline(
            total,
            color=_ink(),
            linewidth=1.2,
            zorder=4,
            label=f"{whole['label'].iloc[0]}: {total:.1f} %",
        )
    ax.set_xlim(0, 100)
    ax.set_xlabel(f"Reach (%) of the {table.base} respondents who answered", color=_ink())
    chart.legend(ax)
    _hide_spines(ax)
    chart.make_room(ax, artists)
    return "TURF: what each option of the portfolio reaches"


# ─── MaxDiff, Conjoint, Share of preference ──────────────────────────────────


def _has_utilities(table: Any) -> bool:
    return "Utility" in table.to_frame().columns


def _draw_maxdiff(table: Any, chart: ResultChart) -> str:
    frame = table.to_frame()
    stats = table.stats
    labels = [str(value) for value in frame["Item"]]
    color = chart.colors(1)[0]
    question = stats.get("Question") or table.question
    if chart.drawn == "utilities":
        from scipy.stats import norm

        from siamang.data import maxdiff

        # The table keeps the estimates; their standard errors are the fit's.
        fit = maxdiff.utilities(table.data, maxdiff.question_of(table.data, table.question))
        errors = dict(zip(fit.table["term"], fit.table["std_error"], strict=True))
        z = float(norm.ppf(0.975))
        utility = frame["Utility"].to_numpy(dtype=float)
        se = np.array([float(errors.get(label, 0.0)) for label in labels])
        reference = stats.get("Reference")
        digits = _digits(utility)
        texts = [
            _number(value, digits) + (" (reference)" if label == reference else "")
            for value, label in zip(utility, labels, strict=True)
        ]
        lower = np.where(se > 0, utility - z * se, np.nan)
        upper = np.where(se > 0, utility + z * se, np.nan)
        ax, size = _dots(
            chart,
            labels,
            [{"estimate": utility, "lower": lower, "upper": upper, "text": texts, "color": color}],
            reference=0.0,
        )
        ax.set_xlabel(
            f"Utility (conditional logit) with its 95 % confidence interval, "
            f"against {reference} at 0",
            color=_ink(),
        )
        _base_note(ax, stats, size)
        return f"MaxDiff utilities: {question}"
    if chart.drawn == "shares":
        values = frame["Share %"].to_numpy(dtype=float)
        ax, _, size = _bars(chart, labels, values, [_percent(v) for v in values], color=color)
        ax.set_xlabel("Share of picks if every item were offered at once (%)", color=_ink())
        _base_note(ax, stats, size)
        return f"MaxDiff shares: {question}"
    values = frame["Score"].to_numpy(dtype=float)
    digits = _digits(values)
    ax, _, size = _bars(chart, labels, values, [_number(v, digits) for v in values], color=color)
    ax.set_xlabel("Counting score: (best − worst) / shown", color=_ink())
    _base_note(ax, stats, size)
    return f"MaxDiff scores: {question}"


def _base_note(ax: Any, stats: dict[str, Any], size: float, then: str = "") -> None:
    """``Base: 500 respondents.`` under the axis, and what follows it."""
    base = stats.get("Base") or (f"{stats['N']} respondents" if stats.get("N") else "")
    text = " ".join(part for part in (f"Base: {base}." if base else "", then) if part)
    if text:
        _mark_note(ax, text, size)


def _draw_conjoint(table: Any, chart: ResultChart) -> str:
    frame = table.to_frame()
    stats = table.stats
    question = stats.get("Question") or table.question
    attributes = list(dict.fromkeys(frame["Attribute"].astype(str)))
    if chart.drawn == "importance":
        importance = [
            float(frame.loc[frame["Attribute"].astype(str) == name, "Importance %"].iloc[0])
            for name in attributes
        ]
        ax, _, size = _bars(
            chart,
            attributes,
            importance,
            [_percent(value) for value in importance],
            color=chart.colors(1)[0],
        )
        ax.set_xlabel("Importance: the attribute's share of the decision (%)", color=_ink())
        _base_note(ax, stats, size, "Of the levels tested, not of the attribute in general.")
        return f"Attribute importance: {question}"
    labels, values, colors = [], [], []
    palette = chart.colors(len(attributes))
    # Each attribute's levels in the design's order (the table sorts them by
    # worth): an ordered attribute such as price reads as its curve.
    designed: dict[str, dict[str, int]] = {}
    try:
        from siamang.data import conjoint

        for attribute in conjoint.question_of(table.data, table.question).attributes:
            designed[str(attribute.label or attribute.name)] = {
                str(level.label): position for position, level in enumerate(attribute.levels)
            }
    except (AttributeError, KeyError, TypeError, ValueError):
        designed = {}
    for name, color in zip(attributes, palette, strict=True):
        part = frame[frame["Attribute"].astype(str) == name]
        places = designed.get(name, {})
        if places:
            part = part.assign(
                _place=[places.get(str(level), len(places)) for level in part["Level"]]
            ).sort_values("_place", kind="stable")
        for level, worth in zip(part["Level"], part["Part-worth"], strict=True):
            labels.append(f"{name}: {level}")
            values.append(float(worth))
            colors.append(color)
    ax, y, size = chart.rows(labels)
    ax.barh(y, values, height=0.66, color=colors, zorder=2)
    digits = _digits(values)
    artists = [
        _label(ax, value, row, _number(value, digits), size, left=value < 0)
        for row, value in zip(y, values, strict=True)
    ]
    ax.axvline(0, color=_muted(), linewidth=1, zorder=1)
    _hide_spines(ax)
    chart.make_room(ax, artists)
    ax.set_xlabel("Part-worth, against each attribute's first level at 0", color=_ink())
    _base_note(ax, stats, size)
    return f"Part-worths: {question}"


def _draw_shares(table: Any, chart: ResultChart) -> str:
    frame = table.to_frame()
    values = frame["share"].to_numpy(dtype=float)
    ax, _, size = _bars(
        chart,
        [str(value) for value in frame["product"]],
        values,
        [_percent(value) for value in values],
        color=chart.colors(1)[0],
    )
    ax.set_xlabel("Share of preference (%)", color=_ink())
    _mark_note(ax, str(table.stats.get("Note", "")).capitalize() + ".", size)
    return "Share of preference"


# ─── Principal components and factor analysis ───────────────────────────────


def _is_pca_variance(frame: pd.DataFrame) -> bool:
    return {"component", "eigenvalue", "variance_pct", "cumulative_pct"} <= set(frame.columns)


def _is_pca_loadings(frame: pd.DataFrame) -> bool:
    columns = [str(column) for column in frame.columns]
    return (
        len(columns) > 1
        and columns[0] == "item"
        and all(column.startswith("PC") for column in columns[1:])
    )


def _is_factor_variance(table: Any) -> bool:
    columns = [str(column) for column in table.to_frame().columns]
    return columns[:2] == ["Factor", "Eigenvalue"]


def _is_factor_loadings(table: Any) -> bool:
    columns = set(table.to_frame().columns)
    return {"Variable", "Label", "Communality", "Uniqueness", "MSA"} <= columns


def _scree(
    chart: ResultChart,
    eigenvalues: np.ndarray,
    kept: int | None,
    *,
    random: np.ndarray | None = None,
    name: str = "Component",
) -> str:
    fig, ax = chart.figure()
    count = len(eigenvalues)
    x = np.arange(1, count + 1)
    color = chart.colors(1)[0]
    ax.plot(x, eigenvalues, "-", color=color, linewidth=2, zorder=2)
    kept_mask = np.zeros(count, dtype=bool) if kept is None else x <= kept
    label = "Eigenvalue" if kept is None else f"Eigenvalue ({kept} kept: filled)"
    ax.plot(
        x[kept_mask],
        eigenvalues[kept_mask],
        "o",
        color=color,
        markersize=8,
        markeredgecolor="white",
        zorder=3,
    )
    ax.plot(
        x[~kept_mask],
        eigenvalues[~kept_mask],
        "o",
        color="white",
        markeredgecolor=color,
        markeredgewidth=1.8,
        markersize=7,
        zorder=3,
    )
    ax.plot([], [], "-o", color=color, label=label)
    ax.axhline(
        1.0,
        color=_ink(),
        linewidth=1,
        linestyle=(0, (4, 3)),
        zorder=1,
        label="Kaiser criterion: eigenvalue 1",
    )
    if random is not None:
        ax.plot(
            x,
            random,
            "-",
            color=_muted(),
            linewidth=1.5,
            zorder=2,
            label="Random data, 95th percentile (parallel analysis)",
        )
    shown = x[kept_mask] if kept else x[: min(count, 3)]
    artists = [
        ax.annotate(
            f"{eigenvalues[i - 1]:.2f}",
            (i, eigenvalues[i - 1]),
            xytext=(6, 4),
            textcoords="offset points",
            fontsize=9,
            color=_ink(),
        )
        for i in shown
    ]
    if count <= 25:
        ax.set_xticks(x)
    else:
        from matplotlib.ticker import MaxNLocator

        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_xlim(0.5, count + 0.5)
    ax.set_ylim(0, max(float(np.nanmax(eigenvalues)), 1.0) * 1.12)
    ax.set_xlabel(name, color=_ink())
    ax.set_ylabel("Eigenvalue", color=_ink())
    ax.grid(axis="x", visible=False)
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    _hide_spines(ax)
    chart.make_room(ax, artists, "y")
    return "Scree plot"


def _loadings(chart: ResultChart, items: list[str], columns: list[str], values: np.ndarray) -> str:
    from matplotlib.colors import TwoSlopeNorm

    wrapped, size, height = fit_rows(chart.figsize, items)
    fig, ax = chart.figure(height=height)
    limit = max(1.0, float(np.nanmax(np.abs(values))) if np.isfinite(values).any() else 1.0)
    masked = np.ma.masked_invalid(values)
    cmap = plt.get_cmap(chart_theme.cmap("RdBu_r")).with_extremes(bad="#f4f4f4")
    norm = TwoSlopeNorm(0.0, -limit, limit)
    image = ax.imshow(
        masked,
        cmap=cmap,
        norm=norm,
        aspect="auto",
        interpolation="nearest",
    )
    rows, cols = values.shape
    cell = min((chart.figsize[0] * 0.55) / max(cols, 1), (height - _CHROME) / max(rows, 1))
    annotate = cell >= 0.22
    if annotate:
        for i in range(rows):
            for j in range(cols):
                value = values[i, j]
                if value != value:
                    continue
                ax.text(
                    j,
                    i,
                    f"{value:.2f}",
                    ha="center",
                    va="center",
                    fontsize=min(size, 9),
                    color=chart_theme.ink_on(
                        cmap(norm(value)), "white" if abs(value) > 0.6 * limit else _INK
                    ),
                )
    ax.set_yticks(range(rows))
    ax.set_yticklabels(wrapped, fontsize=size, color=_ink())
    ax.set_xticks(range(cols))
    ax.set_xticklabels(columns, fontsize=size, color=_ink())
    ax.xaxis.tick_top()
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_visible(False)
    bar = fig.colorbar(image, ax=ax, fraction=0.04, pad=0.02)
    bar.set_label("Loading", color=_ink())
    bar.outline.set_visible(False)
    if not annotate:
        ax.set_xlabel("The values are in the table.", color=_muted())
    return "Loadings"


def _draw_pca_variance(frame: pd.DataFrame, chart: ResultChart) -> str:
    kept = chart.stats.get("components")
    return _scree(
        chart,
        frame["eigenvalue"].to_numpy(dtype=float),
        int(kept) if isinstance(kept, int | np.integer) else None,
    )


def _draw_pca_loadings(frame: pd.DataFrame, chart: ResultChart) -> str:
    columns = [str(column) for column in frame.columns[1:]]
    names = dict(frame.attrs.get("labels") or {})  # the codebook's, as a factor's loadings
    _loadings(
        chart,
        [str(names.get(item, item)) for item in frame["item"]],
        columns,
        frame[columns].to_numpy(dtype=float),
    )
    return "Principal component loadings"


def _draw_pca_result(result: Any, chart: ResultChart) -> str:
    if chart.drawn == "scree":
        return _scree(
            chart,
            result.variance["eigenvalue"].to_numpy(dtype=float),
            int(result.stats.get("components", 0)) or None,
        )
    return _draw_pca_loadings(result.loadings, chart)


def _draw_factor_variance(table: Any, chart: ResultChart) -> str:
    frame = table.to_frame()
    random = next((column for column in frame.columns if str(column).startswith("Random ")), None)
    kept = int(frame["Extracted SS"].notna().sum()) if "Extracted SS" in frame else None
    title = _scree(
        chart,
        frame["Eigenvalue"].to_numpy(dtype=float),
        kept,
        random=None if random is None else frame[random].to_numpy(dtype=float),
        name="Factor",
    )
    extraction = table.stats.get("Extraction")
    return f"{title}: {extraction}" if extraction else title


def _draw_factor_loadings(table: Any, chart: ResultChart) -> str:
    frame = table.to_frame()
    columns = [str(column) for column in frame.columns if str(column).startswith("Factor ")]
    _loadings(
        chart,
        [str(label) for label in frame["Label"]],
        columns,
        frame[columns].to_numpy(dtype=float),
    )
    stats = table.stats
    method = ", ".join(str(stats[key]) for key in ("Extraction", "Rotation") if stats.get(key))
    return f"Factor loadings: {method}" if method else "Factor loadings"


def _draw_factor_analysis(result: Any, chart: ResultChart) -> str:
    return (_draw_factor_variance if chart.drawn == "scree" else _draw_factor_loadings)(
        result.variance if chart.drawn == "scree" else result.loadings, chart
    )


# ─── Cluster, Regression, Correlation matrix ─────────────────────────────────


def _is_centroids(frame: pd.DataFrame) -> bool:
    return [str(column) for column in frame.columns[:3]] == [
        "cluster",
        "size",
        "share_pct",
    ] and len(frame.columns) > 3


def _draw_profile(
    frame: pd.DataFrame, chart: ResultChart, labels: dict[str, str] | None = None
) -> str:
    items = [str(column) for column in frame.columns[3:]]
    labels = labels or dict(frame.attrs.get("labels") or {})
    names = [labels.get(item, item) for item in items]
    colors = chart.colors(len(frame))
    series = []
    for (_, row), color in zip(frame.iterrows(), colors, strict=True):
        means = [float(row[item]) for item in items]
        series.append(
            {
                "estimate": means,
                "lower": [np.nan] * len(items),
                "upper": [np.nan] * len(items),
                "text": [_number(mean) for mean in means] if len(frame) <= 3 else [""] * len(items),
                "color": color,
                "label": f"Cluster {int(row['cluster'])} (n = {int(row['size'])}, {float(row['share_pct']):.1f} %)",
            }
        )
    # A snake plot: each cluster a line down the items, so its profile reads as
    # a shape and two clusters' as two shapes.
    ax, _ = _dots(chart, names, series, dodge=False)
    for item in series:
        ax.plot(
            item["estimate"], range(len(items)), "-", color=item["color"], linewidth=1.6, zorder=2
        )
    ax.set_xlabel("Mean of the cluster's members on each item", color=_ink())
    return "Cluster profiles"


def _draw_cluster(result: Any, chart: ResultChart) -> str:
    variables = getattr(getattr(result, "data", None), "variables", None)
    labels = (
        {
            name: variables[name].label or name
            for name in result.centroids.columns[3:]
            if name in variables
        }
        if variables is not None
        else None
    )
    return _draw_profile(result.centroids, chart, labels)


def _is_coefficients(frame: pd.DataFrame) -> bool:
    columns = set(frame.columns)
    return {
        "term",
        "estimate",
        "std_error",
        "statistic",
        "p_value",
    } <= columns and "share" not in columns


def _forest(frame: pd.DataFrame, chart: ResultChart, stats: dict[str, Any], note: str = "") -> str:
    from scipy.stats import norm
    from scipy.stats import t as t_dist

    labels = dict(frame.attrs.get("labels") or {})
    reference = dict(frame.attrs.get("reference") or {})
    terms = frame[frame["term"].astype(str) != "(intercept)"]
    logit = "odds_ratio" in frame.columns or stats.get("model") == "logit"
    estimate = terms["estimate"].to_numpy(dtype=float)
    se = terms["std_error"].to_numpy(dtype=float)
    n = stats.get("n")
    if logit:
        q, basis = float(norm.ppf(0.975)), "Wald"
    elif isinstance(n, int | np.integer) and n > len(frame):
        q, basis = float(t_dist.ppf(0.975, int(n) - len(frame))), f"t with {int(n) - len(frame)} df"
    else:
        q, basis = (
            float(norm.ppf(0.975)),
            "normal approximation: connect the stat for the t interval",
        )
    lower, upper = estimate - q * se, estimate + q * se
    if logit:
        estimate, lower, upper = np.exp(estimate), np.exp(lower), np.exp(upper)
    texts = [
        f"{_number(value)} ({_number(low)} – {_number(high)})"
        for value, low, high in zip(estimate, lower, upper, strict=True)
    ]
    ax, size = _dots(
        chart,
        [_term(str(term), labels) for term in terms["term"]],
        [
            {
                "estimate": estimate,
                "lower": lower,
                "upper": upper,
                "text": texts,
                "color": chart.colors(1)[0],
            }
        ],
        reference=1.0 if logit else 0.0,
    )
    if logit:
        from matplotlib.ticker import FuncFormatter, LogLocator

        ax.set_xscale("log")
        # Odds ratios as numbers (0.5, 1, 2), not powers of ten.
        ax.xaxis.set_major_locator(LogLocator(base=10, subs=(1.0, 2.0, 5.0)))
        ax.xaxis.set_minor_locator(LogLocator(base=10, subs=(1.25, 1.5, 3.0, 4.0, 7.0)))
        ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:g}"))
        ax.xaxis.set_minor_formatter(FuncFormatter(lambda value, _: _minor_label(ax, value)))
        ax.tick_params(axis="x", which="minor", labelsize=size, colors=_ink())
        ax.set_xlabel(
            f"Odds ratio with its 95 % confidence interval ({basis}), log scale", color=_ink()
        )
    else:
        ax.set_xlabel(f"Coefficient with its 95 % confidence interval ({basis})", color=_ink())
    # The base, what each nominal predictor's answers are compared with, and
    # what the caller adds (the ordinal logit's reading).
    parts = [f"N = {int(n)} respondents in the model" if isinstance(n, int | np.integer) else ""]
    if reference:
        parts.append(
            "compared with "
            + ", ".join(f"{labels.get(name, name)} = {level}" for name, level in reference.items())
        )
    lines = "; ".join(part for part in parts if part)
    text = ". ".join(
        part for part in (lines[:1].upper() + lines[1:] if lines else "", note) if part
    )
    if text:
        _mark_note(ax, text if text.endswith(".") else text + ".", size)
    outcome = stats.get("outcome")
    outcome = labels.get(str(outcome), outcome) if outcome else outcome
    return f"Regression coefficients{f': {outcome}' if outcome else ''}"


def _term(term: str, labels: dict[str, str]) -> str:
    """A model term by the codebook's label: ``age`` → ``Age in years``,
    ``region = North`` → ``Region = North``."""
    if term in labels:
        return str(labels[term])
    name, equals, level = term.partition(" = ")
    return f"{labels[name]} = {level}" if equals and name in labels else term


def _minor_label(ax: Any, value: float) -> str:
    """A minor tick's label on a log axis of odds ratios: named only while
    fewer than three major ticks (0.5, 1, 2, …) fall within the axis — a narrow
    range needs 1.25 and 1.5 to be read, and on a wide one they would run into
    the major labels."""
    low, high = sorted(ax.get_xlim())
    majors = [tick for tick in ax.xaxis.get_majorticklocs() if low <= tick <= high]
    return f"{value:g}" if len(majors) < 3 else ""


def _draw_coefficients(frame: pd.DataFrame, chart: ResultChart) -> str:
    return _forest(frame, chart, chart.stats)


def _draw_regression(result: Any, chart: ResultChart) -> str:
    return _forest(result.table, chart, {**chart.stats, **result.stats})


def _draw_correlations(table: Any, chart: ResultChart) -> str:
    from matplotlib.colors import TwoSlopeNorm

    from siamang.reporting.tables import _get_label

    result = table.result
    columns = list(result.columns)
    labels = [_get_label(table.data, column) for column in columns]
    labels = [
        f"{label} ({column})" if labels.count(label) > 1 else label
        for label, column in zip(labels, columns, strict=True)
    ]
    count = len(columns)
    values = result.coefficients.loc[columns, columns].to_numpy(dtype=float)
    p = (result.p_adjusted if table.adjust != "none" else result.p_values).loc[columns, columns]
    p = p.to_numpy(dtype=float)
    shown = np.full((count, count), np.nan)
    below = np.tril(np.ones((count, count), dtype=bool), -1)
    shown[below] = values[below]
    numbered = [f"{i + 1}. {label}" for i, label in enumerate(labels)]
    short = max((len(label) for label in labels), default=0) <= 14
    wrapped, size, height = fit_rows(chart.figsize, labels if short else numbered)
    fig, ax = chart.figure(height=height)
    cmap = plt.get_cmap(chart_theme.cmap("RdBu_r")).with_extremes(bad="white")
    norm = TwoSlopeNorm(0.0, -1.0, 1.0)
    image = ax.imshow(np.ma.masked_invalid(shown), cmap=cmap, norm=norm, aspect="auto")
    # "-.65***" has to fit its cell (a coefficient without its leading zero, as
    # APA writes one): the font follows the cell, and below 6 pt the numbers are
    # left to the table.
    across = chart.figsize[0] * 0.5 / count
    down = (height - _CHROME) / count
    font = min(9.0, across * 72 * 0.9 / (7 * 0.55), down * 72 / 1.4)
    annotate = font >= 6
    for i in range(count):
        for j in range(count):
            if j == i:
                ax.text(j, i, "—", ha="center", va="center", fontsize=min(size, 9), color=_muted())
            elif j < i and annotate:
                value = values[i, j]
                text = "n/a" if value != value else f"{_coefficient(value)}{_marks(p[i, j])}"
                ax.text(
                    j,
                    i,
                    text,
                    ha="center",
                    va="center",
                    fontsize=font,
                    color=chart_theme.ink_on(
                        cmap(norm(value)),
                        "white" if value == value and abs(value) > 0.6 else _INK,
                    ),
                )
    ax.set_yticks(range(count))
    ax.set_yticklabels(wrapped, fontsize=size, color=_ink())
    ax.set_xticks(range(count))
    if short:
        ax.set_xticklabels(wrapped, fontsize=size, color=_ink(), rotation=45, ha="right")
    else:
        ax.set_xticklabels([str(i + 1) for i in range(count)], fontsize=size, color=_ink())
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_visible(False)
    bar = fig.colorbar(image, ax=ax, fraction=0.04, pad=0.02)
    bar.set_label("Coefficient", color=_ink())
    bar.outline.set_visible(False)
    stats = table.stats
    marks = stats.get("Marks") or "* p < .05, ** p < .01, *** p < .001" + (
        " (adjusted p)" if table.adjust != "none" else ""
    )
    ax.set_xlabel(
        marks if annotate else "The coefficients and their marks are in the table.",
        color=_muted(),
    )
    if stats.get("N"):
        missing = str(stats.get("Missing") or "").split(":")[0]
        _mark_note(ax, f"N = {stats['N']}" + (f" ({missing})" if missing else "") + ".", size)
    return str(stats.get("Method", "Correlations"))


def _coefficient(value: float) -> str:
    """A correlation to two decimals without its leading zero: .52, -.07."""
    text = _number(value)
    return text.replace("0.", ".", 1) if abs(float(text)) < 1 else text


def _marks(p: float) -> str:
    if p != p:
        return ""
    return "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""


# ─── Code open answers ───────────────────────────────────────────────────────


def _has_sentiment(table: Any) -> bool:
    return "Positive %" in table.to_frame().columns


def _draw_themes(table: Any, chart: ResultChart) -> str:
    frame = table.to_frame()
    stats = table.stats
    themes = frame[~frame["Theme"].isin(["Coded", "Uncoded"])]
    labels = [str(value) for value in themes["Theme"]]
    variable = stats.get("Variable", "")
    data = getattr(table, "data", None)
    known = getattr(data, "variables", None)
    if known is not None and variable in known and known[variable].label:
        variable = known[variable].label  # the question, not its column
    if chart.drawn == "sentiment":
        ax, y, size = chart.rows(labels, legend=["Negative", "Neutral", "Positive"])
        start = np.zeros(len(themes))
        parts = (
            ("Negative %", _negative()),
            ("Neutral %", _neutral()),
            ("Positive %", _positive()),
        )
        for column, color in parts:
            share = themes[column].to_numpy(dtype=float)
            ax.barh(
                y,
                np.nan_to_num(share),
                left=start,
                height=0.66,
                color=color,
                edgecolor="white",
                linewidth=1.5,
                label=column.replace(" %", ""),
                zorder=2,
            )
            for row, left, value in zip(y, start, share, strict=True):
                if value == value and value >= 8:
                    ax.text(
                        left + value / 2,
                        row,
                        f"{value:.0f} %",
                        ha="center",
                        va="center",
                        fontsize=size - 1,
                        color=chart_theme.ink_on(color, "white" if column != "Neutral %" else _INK),
                    )
            start = start + np.nan_to_num(share)
        for row, total in zip(y, start, strict=True):
            if total == 0:
                ax.text(
                    1,
                    row,
                    "no answer here has a sentiment",
                    va="center",
                    fontsize=size - 1,
                    color=_muted(),
                )
        ax.set_xlim(0, 100)
        ax.set_xlabel("Sentiment of the theme's answers (%)", color=_ink())
        chart.legend(ax)
        _hide_spines(ax)
        return f"Sentiment by theme: {variable}"
    values = themes["%"].to_numpy(dtype=float)
    counts = themes["N"].to_numpy()
    ax, _, size = _bars(
        chart,
        labels,
        values,
        [f"{value:.1f} % ({int(n)})" for value, n in zip(values, counts, strict=True)],
        color=chart.colors(1)[0],
    )
    ax.set_xlabel("Share of the coded answers (%), with the number of answers", color=_ink())
    coverage = stats.get("Coverage")
    if coverage:
        _mark_note(ax, f"Coverage: {coverage}.", size)
    return f"Themes: {variable}"


def _themes_sentiment_problem(table: Any) -> None:
    """Asked for sentiment where the table has none: say why."""
    reason = table.stats.get("Sentiment")
    why = (
        "this codeframe was built without sentiment"
        if reason == "not in this codeframe"
        else "Code open answers ran with Also add sentiment off"
    )
    raise ResultChartError(f"There is no sentiment to draw: {why}.")


# ─── Registration ────────────────────────────────────────────────────────────


def _register_builtins() -> None:
    from siamang.data.factor import FactorAnalysis
    from siamang.data.models import ClusterResult, PcaResult, RegressionResult
    from siamang.data.paired import PairedResult
    from siamang.data.survey_data import ClusterAssignment
    from siamang.data.turf import TurfTable
    from siamang.reporting.model_tables import RegressionTable
    from siamang.reporting.result_table import ResultTable
    from siamang.reporting.stat_tables import CorrelationMatrixTable, TTestTable
    from siamang.reporting.summaries import DescriptivesTable
    from siamang.reporting.tables import (
        ConjointTable,
        GroupMeanTable,
        MaxDiffTable,
        NpsTable,
        ShareTable,
        ThemeTable,
    )

    means = ("means", "means_sd")
    register(GroupMeanTable, means, _draw_group_means, name="Group means")
    register(DescriptivesTable, means, _draw_descriptives, name="Descriptive statistics")
    register(TTestTable, means, _draw_ttest, name="t-test")
    register(ResultTable, means, _draw_paired, accepts=_is_paired_table, name="Paired tests")
    register(
        ResultTable, ("shares",), _draw_mcnemar, accepts=_is_mcnemar_table, name="Paired tests"
    )
    register(
        PairedResult,
        means,
        lambda result, chart: _draw_paired(result.table, chart),
        accepts=lambda result: _is_paired_table(result.table),
        name="Paired tests",
    )
    register(
        PairedResult,
        ("shares",),
        lambda result, chart: _draw_mcnemar(result.table, chart),
        accepts=lambda result: _is_mcnemar_table(result.table),
        name="Paired tests",
    )
    register(dict, ("interval",), _draw_proportion, accepts=_is_proportion, name="Proportion CI")
    register(NpsTable, ("stacked",), _draw_nps, name="Net Promoter Score")
    register(TurfTable, ("reach",), _draw_turf_reach, accepts=_is_turf_search, name="TURF")
    register(TurfTable, ("items",), _draw_turf_items, accepts=_is_turf_fixed, name="TURF")
    register(
        MaxDiffTable,
        ("utilities", "scores", "shares"),
        _draw_maxdiff,
        accepts=_has_utilities,
        name="MaxDiff",
    )
    register(
        MaxDiffTable,
        ("scores",),
        _draw_maxdiff,
        accepts=lambda table: not _has_utilities(table),
        name="MaxDiff",
    )
    register(ConjointTable, ("importance", "partworths"), _draw_conjoint, name="Conjoint")
    register(ShareTable, ("shares",), _draw_shares, name="Share of preference")
    register(
        pd.DataFrame,
        ("scree",),
        _draw_pca_variance,
        accepts=_is_pca_variance,
        name="Principal components",
    )
    register(
        pd.DataFrame,
        ("loadings",),
        _draw_pca_loadings,
        accepts=_is_pca_loadings,
        name="Principal components",
    )
    register(PcaResult, ("scree", "loadings"), _draw_pca_result, name="Principal components")
    register(
        ResultTable,
        ("scree",),
        _draw_factor_variance,
        accepts=_is_factor_variance,
        name="Factor analysis",
    )
    register(
        ResultTable,
        ("loadings",),
        _draw_factor_loadings,
        accepts=_is_factor_loadings,
        name="Factor analysis",
    )
    register(FactorAnalysis, ("scree", "loadings"), _draw_factor_analysis, name="Factor analysis")
    register(
        pd.DataFrame, ("profile",), _draw_profile, accepts=_is_centroids, name="Cluster (k-means)"
    )
    register(
        (ClusterAssignment, ClusterResult), ("profile",), _draw_cluster, name="Cluster (k-means)"
    )
    register(
        pd.DataFrame,
        ("coefficients",),
        _draw_coefficients,
        accepts=_is_coefficients,
        name="Regression",
    )
    register(RegressionResult, ("coefficients",), _draw_regression, name="Regression")
    # The Regression node's table (a report's view of the model) draws the model.
    register(
        RegressionTable,
        ("coefficients",),
        lambda table, chart: _draw_regression(table.result, chart),
        accepts=lambda table: table.result is not None,
        name="Regression",
    )
    register(CorrelationMatrixTable, ("heatmap",), _draw_correlations, name="Correlation matrix")
    register(
        ThemeTable,
        ("shares", "sentiment"),
        _draw_themes,
        accepts=_has_sentiment,
        name="Code open answers",
    )
    register(
        ThemeTable,
        ("shares", "sentiment"),
        lambda table, chart: _draw_themes(table, chart)
        if chart.drawn != "sentiment"
        else _themes_sentiment_problem(table),
        accepts=lambda table: not _has_sentiment(table),
        name="Code open answers",
    )

    register_output("analyze.means", "table", means)
    register_output("analyze.descriptives", "table", means)
    register_output("analyze.ttest", "table", means)
    register_output(
        "analyze.paired",
        "table",
        lambda params: ("shares",) if params.get("test") == "mcnemar" else means,
    )
    register_output("analyze.proportion_ci", "stat", ("interval",))
    register_output("analyze.nps", "table", ("stacked",))
    register_output(
        "analyze.turf",
        "table",
        lambda params: ("items",) if params.get("method") == "fixed" else ("reach",),
    )
    register_output(
        "analyze.maxdiff",
        "table",
        lambda params: ("scores",)
        if params.get("method") == "counts"
        else ("utilities", "scores", "shares"),
    )
    register_output("analyze.conjoint", "table", ("importance", "partworths"))
    register_output("analyze.conjoint_shares", "table", ("shares",))
    register_output("analyze.pca", "variance", ("scree",))
    register_output("analyze.pca", "loadings", ("loadings",))
    register_output("analyze.factor", "variance", ("scree",))
    register_output("analyze.factor", "loadings", ("loadings",))
    register_output("analyze.cluster", "table", ("profile",))
    register_output("analyze.regression", "table", ("coefficients",))
    register_output("analyze.correlation_matrix", "table", ("heatmap",))
    register_output(
        "prepare.text_code",
        "table",
        lambda params: ("shares", "sentiment") if params.get("sentiment") else ("shares",),
    )


# ─── check_flow ──────────────────────────────────────────────────────────────


def check_sources(
    kind: str, sources: Sequence[tuple[str, str, str, str, str, dict[str, Any]]]
) -> list[tuple[str, str, str]]:
    """What ``check_flow`` says about a Result chart before the run.

    ``sources`` are the outputs connected to it, in order, each as
    ``(node id, node type, node title, port, port type, the node's
    parameters)``. Returns ``(severity, code, message)`` for each problem: an
    output the chart cannot draw (``RESULT_NOT_DRAWABLE``), a ``kind`` none of
    them draws (``RESULT_KIND``), results of several analyses
    (``RESULT_SOURCES``, a warning).
    """

    problems: list[tuple[str, str, str]] = []
    drawable: list[tuple[str, str, str, tuple[str, ...]]] = []
    stats_only: list[tuple[str, str, str, str]] = []
    for node, node_type, title, port, port_type, params in sources:
        kinds = output_kinds(node_type, port, params)
        if kinds is not None:
            drawable.append((node, title, port, kinds))
        elif port_type == "Stat" and _draws_something(node_type):
            stats_only.append((node, node_type, title, port))
        else:
            problems.append(
                (
                    "error",
                    "RESULT_NOT_DRAWABLE",
                    f"A Result chart cannot draw the {port} output of {title} ({node}); it "
                    f"draws the results of {_analyses()}.",
                )
            )
    if not drawable:
        for node, node_type, title, port in stats_only:
            ports = [p for (t, p) in _OUTPUTS if t == node_type]
            problems.append(
                (
                    "error",
                    "RESULT_NOT_DRAWABLE",
                    f"The {port} output of {title} ({node}) only tells a chart its weight and "
                    f"base; connect the output it draws, {' or '.join(ports)}, too.",
                )
            )
        return problems
    if kind in _all_kinds() and not any(kind in kinds for *_, kinds in drawable):
        node, title, port, kinds = drawable[0]
        hint = ""
        node_type = next(t for n, t, *_ in sources if n == node)
        others = [p for (t, p) in _OUTPUTS if t == node_type and p != port]
        for other in others:
            other_params = next(params for n, *_, params in sources if n == node)
            if kind in (output_kinds(node_type, other, other_params) or ()):
                hint = f"; its {other} output draws '{kind}'"
        problems.append(
            (
                "error",
                "RESULT_KIND",
                f"Kind '{kind}' does not suit the {port} output of {title} ({node}), which "
                f"draws {_listed(kinds)}{hint}.",
            )
        )
    nodes = list(dict.fromkeys(node for node, *_ in drawable))
    if len(nodes) > 1:
        chosen = next((item for item in drawable if kind == "auto" or kind in item[3]), drawable[0])
        problems.append(
            (
                "warning",
                "RESULT_SOURCES",
                f"The results connected come from {', '.join(nodes)}; a Result chart draws one "
                f"of them — the {chosen[2]} output of {chosen[1]} ({chosen[0]}).",
            )
        )
    return problems


def _draws_something(node_type: str) -> bool:
    return any(t == node_type for t, _port in _OUTPUTS)


_register_builtins()


def _register_methods() -> None:
    """The later analyses' renderers (:mod:`siamang.reporting.method_charts`),
    after the built-in ones so that theirs win where both accept a result."""
    from siamang.reporting import method_charts

    method_charts.register_all()


_register_methods()
