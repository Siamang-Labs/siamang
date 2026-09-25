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
    """

    columns: list[str] = field(default_factory=list)
    by: str | None = None
    detail: bool = False

    def _build(self) -> None:
        from siamang.data.descriptives import describe

        result = describe(
            self.data.frame,
            self.columns,
            variables=self.data.variables,
            weight=self.data.weight,
            by=self.by,
            detail=self.detail,
        )
        self._result = result.table
        self._stats = result.stats


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
