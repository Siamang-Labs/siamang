"""Accessor classes for convenient reporting from SurveyData.

These provide a fluent API:
    data.report.freq("it_role")
    data.report.crosstab("it_role", "remote_freq")
    data.report.means("autonomy", by="remote_freq")

    data.plot.bar("it_role")
    data.plot.boxplot("autonomy", by="remote_freq")
    data.plot.heatmap(["surv_keystroke", "surv_camera"], by="remote_freq")
    data.plot.scatter("autonomy", "satisfaction")
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from siamang.data.survey_data import SurveyData
    from siamang.reporting.charts import BarChart, BoxPlot, HeatMap, ScatterPlot
    from siamang.reporting.tables import (
        CrossTable,
        FreqTable,
        GroupMeanTable,
        NpsTable,
        QualityTable,
        ThemeTable,
    )


class ReportAccessor:
    """Table-generation accessor attached to SurveyData.

    Usage:
        table = data.report.freq("remote_freq")
        print(table.to_markdown())
    """

    def __init__(self, data: SurveyData) -> None:
        self._data = data

    def freq(self, column: str, *, exclude_missing: bool = True, sort: str = "value") -> FreqTable:
        """Generate a frequency distribution table.

        Parameters
        ----------
        column : str
            Variable name to tabulate.
        exclude_missing : bool
            Exclude NaN values from the base (default True).
        sort : str
            Sort order: "value", "freq", or "label".
        """
        from siamang.reporting.tables import FreqTable

        return FreqTable(data=self._data, column=column, exclude_missing=exclude_missing, sort=sort)

    def quality(self, column: str = "quality_flags") -> QualityTable:
        """Counts per quality check from the column ``prepare.quality`` wrote:
        one row per reason, an "Any check" total and the clean remainder, all as
        a share of everyone screened."""
        from siamang.reporting.tables import QualityTable

        return QualityTable(data=self._data, column=column)

    def maxdiff(self, question: Any, *, method: str = "both") -> Any:
        """What a best–worst question found: one row per item, ordered best
        first, with the counting score and — unless ``method="counts"`` — the
        conditional-logit utilities and the shares they imply."""
        from siamang.reporting.tables import MaxDiffTable

        return MaxDiffTable(data=self._data, question=question, method=method)

    def conjoint(self, question: Any) -> Any:
        """What a choice-based conjoint found: one row per level with its
        part-worth, and each attribute's share of the decision beside it."""
        from siamang.reporting.tables import ConjointTable

        return ConjointTable(data=self._data, question=question)

    def conjoint_shares(self, question: Any, products: Any, *, include_none: bool = False) -> Any:
        """What the part-worths predict a market of ``products`` would do: one
        row per product with its utility and share, and the base, the model
        and — on weighted data — the weight in stats."""
        from siamang.reporting.tables import ShareTable

        return ShareTable(
            data=self._data, question=question, products=products, include_none=include_none
        )

    def themes(self, codeframe: Any, *, sentiment: bool = False) -> ThemeTable:
        """What a frozen codeframe coded these open answers as: one row per
        theme, plus how many answers it had no theme for, and the coverage in
        stats. ``sentiment`` adds each theme's negative / neutral / positive
        split when the codeframe carries sentiment."""
        from siamang.reporting.tables import ThemeTable

        return ThemeTable(data=self._data, codeframe=codeframe, sentiment=sentiment)

    def descriptives(
        self, columns: list[str], *, by: str | None = None, detail: bool = False
    ) -> Any:
        """N, missing, mean, SD, median, minimum and maximum of each variable
        (per group with ``by``; ``detail`` adds quartiles, skewness and
        kurtosis). Missing codes are not answers; on weighted data the mean,
        SD, median and quartiles are weighted and stats give Kish's effective N."""
        from siamang.reporting.summaries import DescriptivesTable

        return DescriptivesTable(data=self._data, columns=list(columns), by=by, detail=detail)

    def data_check(self, variables: list[str] | None = None) -> Any:
        """The data against its codebook: one row per problem ``validate()``
        finds, with how many rows have it and examples of the values."""
        from siamang.reporting.summaries import DataCheckTable

        return DataCheckTable(data=self._data, variables=list(variables) if variables else None)

    def nps(self, column: str) -> NpsTable:
        """Net Promoter Score of a 0–10 item: detractors / passives / promoters
        with N and %, the score with its standard error and 95 % CI in stats."""
        from siamang.reporting.tables import NpsTable

        return NpsTable(data=self._data, column=column)

    def banner(
        self,
        rows: list[str],
        columns: list[str],
        *,
        weight: str | None = None,
        test: bool = True,
        level: float = 0.05,
        correction: str = "none",
    ) -> Any:
        """The cross-break: several questions down, several breakdowns across.

        Each cell is a column percentage with its count and, unless ``test`` is
        off, the letters of the columns it is significantly higher than —
        compared only within a banner variable, whose columns are mutually
        exclusive. ``data.tables.banner`` gives the same numbers in tidy form
        for feeding to something else; this one is for reading.
        """
        from siamang.reporting.tables import BannerTable

        return BannerTable(
            data=self._data,
            rows=list(rows),
            columns=list(columns),
            weight=weight,
            test=test,
            level=level,
            correction=correction,
        )

    def crosstab(
        self,
        row: str,
        col: str,
        *,
        pct: str = "none",
        test: bool = True,
        method: str = "chi2",
    ) -> CrossTable:
        """Generate a cross-tabulation table.

        Parameters
        ----------
        row : str
            Row variable (independent).
        col : str
            Column variable (dependent).
        pct : str
            Percentage direction: "none", "row", "col", "total".
        test : bool
            Run the significance test and report statistics.
        method : str
            "chi2" (Chi-square, the default) or "fisher" (Fisher's exact test).
        """
        from siamang.reporting.tables import CrossTable

        return CrossTable(data=self._data, row=row, col=col, pct=pct, test=test, method=method)

    def means(
        self,
        column: str,
        *,
        by: str,
        test: bool = True,
        method: str = "auto",
        posthoc: str = "none",
        adjust: str = "holm",
    ) -> GroupMeanTable:
        """Generate a grouped means comparison table.

        Parameters
        ----------
        column : str
            Continuous dependent variable.
        by : str
            Categorical grouping variable.
        test : bool
            Run a significance test.
        method : str
            "auto" (chosen by scale and number of groups) or "student", "welch",
            "anova", "welch_anova", "mannwhitney", "kruskal".
        posthoc : str
            "none", "tukey" (after anova), "games_howell" (after welch_anova) or
            "dunn" (after kruskal, p adjusted by ``adjust``: "holm" or "bonferroni").
        """
        from siamang.reporting.tables import GroupMeanTable

        return GroupMeanTable(
            data=self._data,
            column=column,
            by=by,
            test=test,
            method=method,
            posthoc=posthoc,
            adjust=adjust,
        )

    def ttest(
        self,
        column: str,
        *,
        kind: str = "independent",
        by: str | None = None,
        groups: list[Any] | None = None,
        other: str | None = None,
        mu: float = 0.0,
        variances: str = "welch",
        confidence: float = 0.95,
    ) -> Any:
        """A t-test with its descriptives: ``kind="independent"`` compares
        ``column`` between two groups of ``by`` (the two codes in ``groups``
        when ``by`` has more), Welch's by default or Student's with
        ``variances="student"``; ``"paired"`` compares ``column`` with
        ``other`` on the same respondents; ``"one_sample"`` tests the mean
        against ``mu``. See :class:`~siamang.reporting.stat_tables.TTestTable`."""
        from siamang.reporting.stat_tables import TTestTable

        return TTestTable(
            data=self._data,
            column=column,
            kind=kind,
            by=by,
            groups=list(groups) if groups is not None else None,
            other=other,
            mu=float(mu),
            variances=variances,
            confidence=confidence,
        )

    def correlation_matrix(
        self,
        columns: list[str],
        *,
        method: str = "spearman",
        missing: str = "pairwise",
        adjust: str = "none",
        layout: str = "matrix",
    ) -> Any:
        """Correlations between every pair of ``columns`` — ``"pearson"``,
        ``"spearman"`` or ``"kendall"``, ``pairwise`` or ``listwise``, p
        adjusted by ``"holm"``, ``"bonferroni"`` or ``"fdr_bh"`` when asked —
        as a lower-triangle matrix with significance marks or one row per pair.
        See :class:`~siamang.reporting.stat_tables.CorrelationMatrixTable`."""
        from siamang.reporting.stat_tables import CorrelationMatrixTable

        return CorrelationMatrixTable(
            data=self._data,
            columns=list(columns),
            method=method,
            missing=missing,
            adjust=adjust,
            layout=layout,
        )


class PlotAccessor:
    """Chart-generation accessor attached to SurveyData.

    Usage:
        data.plot.bar("it_role")
        data.plot.boxplot("autonomy", by="remote_freq")
    """

    def __init__(self, data: SurveyData) -> None:
        self._data = data

    def bar(
        self,
        column: str,
        *,
        by: str | None = None,
        horizontal: bool = False,
        show_values: bool = True,
        figsize: tuple[float, float] = (10, 6),
        palette: str = "muted",
        title: str | None = None,
        show: str = "count",
        split: str | None = None,
        layout: str = "grouped",
        sort: str = "code",
    ) -> BarChart:
        """Create a bar chart.

        Parameters
        ----------
        column : str
            Variable to plot.
        by : str | None
            If specified, plots grouped means.
        horizontal : bool
            Horizontal bars.
        show_values : bool
            Annotate bars with values.
        show : str
            ``"count"`` or ``"percent"`` of the respondents who answered (for a
            multiple-choice question, of respondents: the bars add up to more
            than 100 %).
        split : str | None
            A second variable: the answers within each of its groups, as a
            crosstab's column percentages, drawn as ``layout`` says —
            ``"grouped"``, ``"stacked"`` or ``"stacked_100"``.
        sort : str
            ``"code"`` (the codebook's order) or ``"value"`` (largest first).
        """
        from siamang.reporting.charts import BarChart

        return BarChart(
            data=self._data,
            column=column,
            by=by,
            horizontal=horizontal,
            show_values=show_values,
            figsize=figsize,
            palette=palette,
            title=title,
            show=show,
            split=split,
            layout=layout,
            sort=sort,
        )

    def boxplot(
        self,
        column: str,
        *,
        by: str,
        show_points: bool = False,
        figsize: tuple[float, float] = (10, 6),
        palette: str = "muted",
        title: str | None = None,
    ) -> BoxPlot:
        """Create a box plot comparing distributions across groups.

        Parameters
        ----------
        column : str
            Continuous dependent variable.
        by : str
            Categorical grouping variable.
        show_points : bool
            Overlay individual data points.
        """
        from siamang.reporting.charts import BoxPlot

        return BoxPlot(
            data=self._data,
            column=column,
            by=by,
            show_points=show_points,
            figsize=figsize,
            palette=palette,
            title=title,
        )

    def heatmap(
        self,
        columns: list[str],
        *,
        by: str | None = None,
        annot: bool = True,
        cmap: str = "YlOrRd",
        vmin: float | None = None,
        vmax: float | None = None,
        figsize: tuple[float, float] = (10, 6),
        title: str | None = None,
        method: str = "spearman",
    ) -> HeatMap:
        """Create a heatmap.

        Parameters
        ----------
        columns : list[str]
            Variables to include.
        by : str | None
            If specified, plots grouped means. Otherwise, correlation matrix.
        method : str
            The correlation without ``by``: ``"spearman"`` (the default, as it
            always was), ``"pearson"`` (weighted on weighted data) or
            ``"kendall"``; those two leave the codebook's missing codes out.
        """
        from siamang.reporting.charts import HeatMap

        return HeatMap(
            data=self._data,
            columns=columns,
            by=by,
            annot=annot,
            cmap=cmap,
            vmin=vmin,
            vmax=vmax,
            figsize=figsize,
            title=title,
            method=method,
        )

    def scatter(
        self,
        x: str,
        y: str,
        *,
        hue: str | None = None,
        trendline: bool = True,
        figsize: tuple[float, float] = (10, 6),
        palette: str = "muted",
        title: str | None = None,
    ) -> ScatterPlot:
        """Create a scatter plot.

        Parameters
        ----------
        x : str
            X-axis variable.
        y : str
            Y-axis variable.
        hue : str | None
            Optional grouping variable for color.
        trendline : bool
            Add linear regression trendline.
        """
        from siamang.reporting.charts import ScatterPlot

        return ScatterPlot(
            data=self._data,
            x=x,
            y=y,
            hue=hue,
            trendline=trendline,
            figsize=figsize,
            palette=palette,
            title=title,
        )
