"""Tables that summarize the data before it is analysed.

:class:`DescriptivesTable` is the descriptive statistics of numeric variables
(:mod:`siamang.data.descriptives`) and :class:`DataCheckTable` the data checked
against its codebook (:mod:`siamang.data.checks`). They sit in a module of their
own rather than in :mod:`siamang.reporting.tables` only to keep that file's
history readable; they are :class:`~siamang.reporting.tables.SurveyTable`
components like the rest, with ``to_frame``, ``stats``, Markdown and HTML.

An undefined number (the SD of one answer) is NaN in :meth:`to_frame` and a
blank cell when the table is printed, so a report never shows ``nan``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from siamang.reporting.tables import SurveyTable, _BlankUndefined

__all__ = ["DataCheckTable", "DescriptivesTable"]


@dataclass
class DescriptivesTable(_BlankUndefined, SurveyTable):
    """N, missing, mean, SD, median, minimum and maximum of numeric variables.

    One row per variable, or per variable and group with ``by``; ``detail``
    adds Q1, Q3, skewness and kurtosis. The codebook's missing codes are not
    answers and are counted as missing. On weighted data the mean, SD, median
    and quartiles are weighted, N and Missing stay counts of respondents beside
    a ``Weighted N`` column, and the stats give the weighted total, Kish's
    effective N and the design effect (see :func:`siamang.data.descriptives.describe`).

    Parameters
    ----------
    columns : list[str]
        The variables to describe.
    by : str | None
        A grouping variable, or None.
    detail : bool
        Also Q1, Q3, skewness and kurtosis.
    layout : str
        With ``by``: ``"long"`` (default) is a row per variable and group;
        ``"means"`` a row per variable and a column per group holding its mean
        — a compact profile of the groups, their sizes in the stats. The long
        rows stay available as :meth:`long_frame` (a chart reads them).
    """

    columns: list[str] = field(default_factory=list)
    by: str | None = None
    detail: bool = False
    layout: str = "long"
    _long: Any = field(init=False, repr=False, default=None)

    def _build(self) -> None:
        from siamang.data.descriptives import describe

        if self.layout not in ("long", "means"):
            raise ValueError(f"layout must be 'long' or 'means'; got {self.layout!r}.")
        if self.layout == "means" and not self.by:
            raise ValueError("layout='means' shows the mean of each group: set by.")
        result = describe(
            self.data.frame,
            self.columns,
            variables=self.data.variables,
            weight=self.data.weight,
            by=self.by,
            detail=self.detail and self.layout == "long",
        )
        self._long = result.table
        self._result = result.table
        self._stats = result.stats
        if self.layout == "means":
            self._result, self._stats = self._means_by_group(result.table, result.stats)

    def long_frame(self) -> pd.DataFrame:
        """A row per variable (and group): N, missing, mean, SD, median …"""
        self._ensure_built()
        return self._long.copy()

    def _means_by_group(
        self, long: pd.DataFrame, stats: dict[str, Any]
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        """The long table as a profile: a row per variable, a column per group
        with its mean; the groups' sizes (respondents, and weighted) and what
        the cells are go to the stats."""
        from siamang.data import descriptives

        variables = self.data.variables
        by_label = descriptives._label(variables, str(self.by))
        frame = self.data.frame.reset_index(drop=True)
        groups = descriptives._groups(frame, str(self.by), variables)
        names = [label for _value, label, _rows in groups]
        rows = []
        for name in dict.fromkeys(long["Variable"]):
            part = long[long["Variable"] == name]
            row: dict[str, Any] = {"Variable": name, "Label": part["Label"].iloc[0]}
            means = dict(zip(part[by_label].astype(str), part["Mean"], strict=True))
            for group in names:
                row[group] = means.get(group)
            rows.append(row)
        table = pd.DataFrame(rows, columns=["Variable", "Label", *names])
        weights = (
            descriptives._weights(frame, self.data.weight) if self.data.weight is not None else None
        )
        sizes = [
            f"{label}: {len(index):,}"
            + (" respondents" if position == 0 else "")
            + (f" ({float(weights.loc[index].sum()):,.1f} weighted)" if weights is not None else "")
            for position, (_value, label, index) in enumerate(groups)
        ]
        shown: dict[str, Any] = {
            "Variables": stats.get("Variables"),
            "Rows": stats.get("Rows"),
            "By": by_label,
            "Groups": ", ".join(sizes),
            "Cells": "each variable's "
            + ("weighted mean" if weights is not None else "mean")
            + " in each group, of the group's respondents who answered it",
        }
        for key in ("Not in a group", "Missing codes", "Not numbers", "Weight"):
            if key in stats:
                shown[key] = stats[key]
        for key in ("Weighted N", "Effective N", "Design effect"):
            if key in stats:
                shown[key] = stats[key]
        if "overlap" in str(stats.get("Groups", "")):
            shown["Overlap"] = stats["Groups"]
        return table, shown


@dataclass
class DataCheckTable(_BlankUndefined, SurveyTable):
    """The data checked against its codebook: one row per problem, errors first.

    Each row names the variable, the problem, how many rows have it and
    examples of the values (``7 (12), 8 (1)``). Columns the codebook does not
    know, and variables the data does not have, are one row each. See
    :func:`siamang.data.checks.check`.

    Parameters
    ----------
    variables : list[str] | None
        Check only these variables; None checks everything.
    """

    variables: list[str] | None = None

    def _build(self) -> None:
        from siamang.data.checks import check

        result = check(self.data, self.variables)
        self._result = result.table
        self._stats = result.stats
