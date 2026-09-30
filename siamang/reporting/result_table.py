"""A table whose numbers were computed elsewhere, with the statistics under it.

The declarative tables in :mod:`siamang.reporting.tables` compute their own
numbers from the data. An analysis that produces several tables at once — a
factor analysis gives loadings, variance explained and factor correlations
from one fit — would have to refit for each of them that way, so it computes
once and hands each table over as a :class:`ResultTable`. To a report, to the
Studio preview and to ``to_markdown`` / ``to_html`` it is a table like any
other: rows, and a footer of statistics.

A cell that does not apply (the rotated variance of a factor that was not
kept, a loading hidden below a threshold) is missing in the frame and blank
on the page, never "nan".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from siamang.reporting import p_values
from siamang.reporting.tables import SurveyTable, _frame_to_markdown, frame_to_html


@dataclass
class ResultTable(SurveyTable):
    """``frame`` shown as a table with ``footer`` as its statistics."""

    frame: pd.DataFrame | None = None
    footer: dict[str, Any] = field(default_factory=dict)

    def _build(self) -> None:
        self._result = (self.frame if self.frame is not None else pd.DataFrame()).copy()
        self._stats = dict(self.footer)

    def _display(self) -> pd.DataFrame:
        shown = self._result.astype(object)
        return shown.where(self._result.notna(), "")

    def to_markdown(self, *, theme: Any = None) -> str:
        with p_values.showing(theme):
            self._ensure_built()
            text = _frame_to_markdown(self._shown(self._display()))
            if self._stats:
                text += "\n\n" + self._format_stats()
        return text

    def to_html(self, *, theme: Any = None) -> str:
        with p_values.showing(theme):
            self._ensure_built()
            html = frame_to_html(self._shown(self._display()))
            if self._stats:
                html += f"\n<p class='siamang-stats'>{self._format_stats()}</p>"
        return html


__all__ = ["ResultTable"]
