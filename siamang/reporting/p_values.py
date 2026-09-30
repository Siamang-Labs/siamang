"""How a report writes a p-value: as it is kept, or below a threshold as a bound.

A p-value is kept as it was computed — rounded by
:func:`~siamang.data.listwise.round_p` (``0.0123``, ``1.134e-24``) or
:func:`~siamang.data.listwise.p_rounded` — in every result, table frame
(``to_frame()``), export and statistics dict, and nothing here changes that.
How a *report* writes one is the report's choice,
:attr:`~siamang.reporting.theme.ReportTheme.p_values`:

``"exact"`` (the default)
    As it is kept: what reports have always printed, byte for byte.
``"0.01"``
    One below 0.01 is written ``< 0.01`` — in a table cell ``< 0.01``, in a
    statistics line ``p < 0.01`` (not ``p = < 0.01``), in the report's Excel
    workbook a number shown as ``< 0.01`` by its number format, and in a
    chart's own APA style ``< .01``. One of 0.01 or more is written as kept.
``"0.001"``
    The same below 0.001.

The rendering layer asks :func:`current` which applies. A report sets it for
everything it renders (:func:`showing`), from its theme, so one setting
governs its tables, its statistics lines, its workbook and its charts; a
table rendered outside a report (a node's own output, a notebook) writes p as
it is kept unless it is given a theme (``to_markdown(theme=...)``). A chart
writes its notes when it is drawn, so a chart that wrote a p-value remembers
how (:func:`recording`), and a report in another setting draws it again
(:func:`siamang.reporting.chart_theme.in_report`).

Which cells and statistics are p-values is decided by name (:func:`is_p`):
``p``, ``p (Holm)``, ``p (unadjusted)``, ``p adjusted``, ``Beta p``,
``Bartlett p``, ``p_value``, ``lr_p`` … — the names the engine gives them.
"""

from __future__ import annotations

import contextlib
import contextvars
import re
from collections.abc import Iterator, Mapping
from typing import Any

import numpy as np
import pandas as pd

#: The choices of ``ReportTheme.p_values``, the default first.
MODES = ("exact", "0.01", "0.001")
DEFAULT = "exact"
_LIMITS = {"0.01": 0.01, "0.001": 0.001}

_SHOWING: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "siamang_p_values", default=None
)
#: While a chart is drawn (:func:`recording`): the settings its p-values were
#: written in, one entry per p-value written.
_WRITTEN: contextvars.ContextVar[list[str] | None] = contextvars.ContextVar(
    "siamang_p_written", default=None
)

#: A bound as a cell may already hold one: ``< 1e-07`` (Tukey's floor).
_BOUND = re.compile(r"\s*<\s*(\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)\s*")
#: ``p = 0.0023`` inside a sentence the engine wrote (a pair's
#: ``z = 2.954, p = 0.0063`` in a comparison of groups).
_IN_TEXT = re.compile(r"(?<![\w.])p = (\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)(?![\w.])")


# ─── which setting applies ───────────────────────────────────────────────────


def mode_of(theme: Any) -> str:
    """The setting ``theme`` asks for: a :class:`~siamang.reporting.theme.ReportTheme`,
    a mapping of its fields, a setting itself (``"0.01"``), or None (the default)."""

    if theme is None:
        return DEFAULT
    if isinstance(theme, str):
        if theme not in MODES:
            raise ValueError(f"p_values: {theme!r} is not one of {', '.join(MODES)}.")
        return theme
    if isinstance(theme, Mapping):
        from siamang.reporting.theme import ReportTheme

        theme = ReportTheme.from_dict(dict(theme))
    return str(getattr(theme, "p_values", DEFAULT))


@contextlib.contextmanager
def showing(theme: Any) -> Iterator[str]:
    """While rendering: p-values written as ``theme`` asks (see :func:`mode_of`).
    None leaves whatever is in force — a report's, or the default."""

    if theme is None:
        yield _SHOWING.get() or DEFAULT
        return
    mode = mode_of(theme)
    token = _SHOWING.set(mode)
    try:
        yield mode
    finally:
        _SHOWING.reset(token)


def current() -> str:
    """The setting in force: the report's being rendered, else the default.

    A chart being drawn (:func:`recording`) notes that it wrote a p-value."""

    mode = _SHOWING.get() or DEFAULT
    written = _WRITTEN.get()
    if written is not None:
        written.append(mode)
    return mode


@contextlib.contextmanager
def recording() -> Iterator[list[str]]:
    """While a chart is drawn: the settings of the p-values it writes (empty
    when it writes none), so a report can tell whether it must be drawn
    again in its own."""

    written: list[str] = []
    token = _WRITTEN.set(written)
    try:
        yield written
    finally:
        _WRITTEN.reset(token)


# ─── what is a p-value, and is it below ──────────────────────────────────────


def is_p(name: Any) -> bool:
    """Whether a column or a statistic of this name holds p-values: ``p``,
    ``p (Holm)``, ``p (unadjusted)``, ``p adjusted``, ``p_value``,
    ``p-value``, ``Beta p``, ``Bartlett p``, ``Fit p``, ``lr_p`` — not
    ``p adjustment`` or ``p method``, which say how p was found."""

    if not isinstance(name, str):
        return False
    text = name.strip().lower()
    return (
        text in {"p", "p_value", "p-value", "p value", "pvalue", "p_adjusted", "p adjusted"}
        or text.startswith("p (")
        or text.endswith((" p", "_p"))
    )


def limit(mode: str | None = None) -> float | None:
    """The threshold of ``mode`` (default :func:`current`); None for ``exact``."""

    return _LIMITS.get(mode if mode is not None else current())


def bound(mode: str) -> str:
    """What stands for a p-value below the threshold: ``< 0.01``."""

    return f"< {mode}"


def is_below(value: Any, mode: str) -> bool:
    """Whether ``value`` is a p-value below the threshold of ``mode`` — a
    number, or a bound a cell already holds (``< 1e-07``) at or under it."""

    threshold = _LIMITS.get(mode)
    if threshold is None or isinstance(value, bool | np.bool_):
        return False
    if isinstance(value, int | float | np.integer | np.floating):
        number = float(value)
        return bool(np.isfinite(number)) and 0 <= number < threshold
    if isinstance(value, str):
        match = _BOUND.fullmatch(value)
        return match is not None and float(match.group(1)) <= threshold
    return False


# ─── writing one ─────────────────────────────────────────────────────────────


def cell(value: Any, mode: str | None = None) -> Any:
    """A p-value as a table cell writes it: the bound when it is below the
    threshold, else as it is."""

    mode = mode if mode is not None else current()
    return bound(mode) if is_below(value, mode) else value


def in_text(text: str, mode: str | None = None) -> str:
    """``text`` with each ``p = <number>`` below the threshold as ``p < 0.01``:
    a p-value the engine wrote into a sentence (a pair of groups compared,
    ``z = 2.954, p = 0.0063``)."""

    mode = mode if mode is not None else current()
    threshold = _LIMITS.get(mode)
    if threshold is None or "p = " not in text:
        return text

    def written(match: re.Match[str]) -> str:
        return f"p {bound(mode)}" if float(match.group(1)) < threshold else match.group(0)

    return _IN_TEXT.sub(written, text)


def cells(frame: pd.DataFrame, names: Any = None, *, tabulated: bool = False) -> pd.DataFrame:
    """``frame`` with the p-values of its columns ``names`` (default: those
    :func:`is_p` names) written as the setting in force asks. ``frame`` itself
    comes back when nothing changes — always under ``exact`` — so the default
    renders exactly what it did.

    ``tabulated``: the frame is printed by tabulate (a bare DataFrame in a
    report), which writes a column of numbers with six significant digits but
    a column holding text as it is; the other numbers of a column that now
    holds a bound are written as tabulate wrote them (``format(value, "g")``),
    so only the p-values below the threshold change."""

    mode = current()
    if mode not in _LIMITS or frame.empty:
        return frame
    wanted = [column for column in frame.columns if is_p(column)] if names is None else list(names)
    out = frame
    for position, column in enumerate(frame.columns):
        if column not in wanted:
            continue
        values = frame.iloc[:, position]
        if not any(is_below(value, mode) for value in values):
            continue
        if out is frame:
            out = frame.copy()
        shown = [
            bound(mode)
            if is_below(value, mode)
            else format(float(value), "g")
            if tabulated and isinstance(value, float | np.floating) and value == value
            else value
            for value in values
        ]
        out.isetitem(position, np.array(shown, dtype=object))
    return out


def apa(p: float) -> str:
    """A p-value as APA writes one, without its leading zero: ``.012``, and
    below the threshold ``< .001`` — the chart's own style, ``< .01`` when the
    report says 0.01. ``exact`` keeps the style's ``< .001``."""

    mode = current()
    threshold = 0.01 if mode == "0.01" else 0.001
    if p < threshold:
        return "< " + f"{threshold:g}".replace("0.", ".", 1)
    return f"{p:.3f}".replace("0.", ".", 1)


def excel_format(mode: str) -> str | None:
    """The number format that shows a p-value below the threshold of ``mode``
    as the bound and any other as Excel's General does — the cell keeps its
    number. None for ``exact``: the cell is left as it was written."""

    if mode not in _LIMITS:
        return None
    return f'[<{mode}]"{bound(mode)}";General'


def statistics(stats: Mapping[Any, Any]) -> set[Any]:
    """The keys of ``stats`` that are p-values. A proportion with its interval
    (``{"p", "lower", "upper", "n"}``, ``analysis.proportion_ci``) keeps its
    ``p``: it is the proportion, not a test's p."""

    keys = {key for key in stats if is_p(key)}
    if {"lower", "upper"} <= set(stats) and "p" in stats:
        keys.discard("p")
    return keys


__all__ = [
    "DEFAULT",
    "MODES",
    "apa",
    "bound",
    "cell",
    "cells",
    "current",
    "excel_format",
    "in_text",
    "is_below",
    "is_p",
    "limit",
    "mode_of",
    "recording",
    "showing",
    "statistics",
]
