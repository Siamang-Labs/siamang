"""Numbers into bands: age into age groups, income into brackets.

:meth:`SurveyData.recode` does the cutting; this is the step around it a flow
needs. The codebook's missing codes are taken out first — a 999 "Refused" is
not a very old respondent, and with bins up to 1 000 it would otherwise land in
the top band — and what did not fall in any band is counted rather than left
for somebody to notice as a smaller N three tables later.

A band includes its lower bound and runs up to, not including, the next one
(``right=True`` turns that around), so ``[18, 30, 45]`` is 18–29.9… and
30–44.9…. The default labels say so: ``18 to under 30``.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pandas as pd

if TYPE_CHECKING:
    from siamang.data.survey_data import SurveyData

__all__ = ["Banded", "band_labels", "bands"]


@dataclass(frozen=True, slots=True)
class Banded:
    """What :func:`bands` returns: the data with the band variable, and counts."""

    data: SurveyData
    stats: dict[str, Any] = field(default_factory=dict)


def band_labels(bins: Sequence[float], *, right: bool = False) -> list[str]:
    """``18 to under 30``, …; with ``right``, ``over 18 to 30`` — the first band
    also takes its lower bound, as :meth:`SurveyData.recode` cuts it."""

    edges = [_number(edge) for edge in bins]
    if right:
        return [
            f"{low} to {high}" if i == 0 else f"over {low} to {high}"
            for i, (low, high) in enumerate(zip(edges, edges[1:], strict=False))
        ]
    return [f"{low} to under {high}" for low, high in zip(edges, edges[1:], strict=False)]


def bands(
    data: SurveyData,
    column: str,
    *,
    bins: Sequence[Any],
    into: str,
    labels: Sequence[str] | None = None,
    right: bool = False,
    label: str | None = None,
) -> Banded:
    """Cut ``column`` at ``bins`` into an ordinal variable ``into`` (codes 1, 2, …).

    ``bins`` are the boundaries, at least two, increasing; ``labels`` name the
    bands (one fewer than the boundaries), by default ``18 to under 30``.
    """

    if column not in data.frame.columns:
        raise KeyError(f"column not found: {column!r}")
    if into == column:
        raise ValueError(f"The bands go into a new variable, not into {column!r} itself.")
    if not isinstance(bins, list | tuple):
        raise ValueError(f"Band boundaries are a list of numbers, e.g. [18, 30, 45], not {bins!r}.")
    if len(bins) < 2:
        raise ValueError("Bands need at least two boundaries, e.g. [18, 30, 45, 65].")
    if labels is not None and (
        not isinstance(labels, list | tuple) or not all(isinstance(n, str) for n in labels)
    ):
        raise ValueError(f'Band labels are a list of texts, e.g. ["18–29", "30+"], not {labels!r}.')
    try:
        edges = [float(edge) for edge in bins]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Band boundaries must be numbers, got {list(bins)!r}.") from exc
    if any(b <= a for a, b in zip(edges, edges[1:], strict=False)):
        raise ValueError(f"Band boundaries must increase, got {list(bins)!r}.")
    names = list(labels) if labels else band_labels(bins, right=right)
    if len(names) != len(edges) - 1:
        raise ValueError(
            f"{len(edges)} boundaries make {len(edges) - 1} bands, but {len(names)} labels "
            "were given."
        )

    series = data.frame[column]
    variable = data.variables.get(column) if data.variables is not None else None
    codes = list(variable.missing_values) if variable is not None else []
    is_code = series.isin(codes).fillna(False).astype(bool) if codes else None
    numeric = pd.to_numeric(series, errors="coerce")
    if is_code is not None:
        numeric = numeric.mask(is_code)
    source = data.with_frame(data.frame.assign(**{column: numeric}))
    cut = source.recode(
        column,
        into=into,
        bins=[_number(edge) for edge in bins],
        labels=names,
        right=right,
        label=label or f"{_label(data, column)} (bands)",
    )
    frame = data.frame.copy()
    frame[into] = cut.frame[into]
    banded = cut.with_frame(frame)  # the source column exactly as it was

    counts = frame[into].value_counts()
    missing_codes = int(is_code.sum()) if is_code is not None else 0
    blank = int(series.isna().sum())
    outside = int(numeric.notna().sum() - counts.sum())
    stats: dict[str, Any] = {
        "Variable": f"{column} → {into}",
        "Bands": "; ".join(
            f"{name}: {int(counts.get(code, 0))}" for code, name in enumerate(names, start=1)
        ),
        "Outside the bands": outside,
    }
    if missing_codes:
        stats["Missing codes"] = missing_codes
    if blank:
        stats["Blank"] = blank
    text = series.notna() & pd.to_numeric(series, errors="coerce").isna()
    not_numbers = int((text & ~is_code).sum()) if is_code is not None else int(text.sum())
    if not_numbers:
        stats["Not numbers"] = not_numbers
    if data.weight is not None:
        from siamang.data.analysis import unweighted_note

        stats["Weight"] = unweighted_note(data.weight)  # the counts are of respondents
    return Banded(data=banded, stats=stats)


def _label(data: SurveyData, column: str) -> str:
    variable = data.variables.get(column) if data.variables is not None else None
    return (variable.label if variable is not None else None) or column


def _number(value: Any) -> Any:
    number = float(value)
    return int(number) if number.is_integer() else number
