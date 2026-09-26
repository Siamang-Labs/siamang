"""Descriptive analysis helpers for SurveyData."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import NormalDist
from typing import Any

import pandas as pd

from siamang.core.variable import VariableMap


def _chose(series: pd.Series, value: object) -> pd.Series:
    """True where the respondent gave ``value`` — one answer among several counts.

    A multiple-choice answer is a list, so ``series == value`` is false for
    everyone who chose it alongside something else: a proportion computed that
    way reported 0 % for an option a quarter of the sample had named.
    """
    from siamang.data import multi

    return multi.reach(series, value) if multi.is_multi(series) else series == value


def _answered(series: pd.Series) -> pd.Series:
    """True where there is an answer at all — an empty list is not one."""
    from siamang.data import multi

    return multi.responded(series) if multi.is_multi(series) else series.notna()


def unweighted_note(weight: str) -> str:
    """What a result that cannot use the data's weight says about it."""
    return f"unweighted (the weight '{weight}' is not applied)"


@dataclass(frozen=True, slots=True)
class DataAnalysis:
    """Tests and models on the frame, with the data's weight column when set.

    The rank tests (:meth:`kruskal`, :meth:`mannwhitney`, :meth:`spearman`)
    have no standard weighted form, so on weighted data they run on the
    respondents as they are and their result carries a ``weight`` entry
    saying so. :meth:`regression`, :meth:`pca` and :meth:`reliability` use
    the weight, and :meth:`correlation` does with Pearson;
    :meth:`proportion_ci` uses it when asked (``weighted=True``).
    """

    frame: pd.DataFrame
    weight_column: str | None = None
    variables: VariableMap | None = None

    def _unweighted(self, result: dict[str, Any]) -> dict[str, Any]:
        if self.weight_column is not None:
            result["weight"] = unweighted_note(self.weight_column)
        return result

    def _counted(
        self, result: dict[str, Any], frame: pd.DataFrame, columns: list[str]
    ) -> dict[str, Any]:
        """``missing_codes_counted`` when ``frame`` reads missing codes as answers."""
        from siamang.data.inference import missing_codes_counted

        note = missing_codes_counted(frame, columns, self.variables)
        if note:
            result["missing_codes_counted"] = note
        return result

    def mean(self, column: str, weighted: bool = False) -> float:
        # By position: the weights of the rows answered are picked with the same
        # mask, as a repeated index label would pull in every row sharing it.
        present = self.frame[column].notna().to_numpy()
        values = self.frame[column][present].astype(float).to_numpy()
        if not len(values):
            return 0.0
        if not weighted:
            return float(values.mean())
        if self.weight_column is None:
            raise ValueError("weighted=True requires SurveyData.weight to be set.")
        # A missing or non-numeric weight counts 0, as everywhere: numpy's sum,
        # unlike pandas', would make one NaN weight the whole mean.
        weights = (
            pd.to_numeric(self.frame[self.weight_column], errors="coerce")
            .fillna(0.0)
            .to_numpy(dtype=float)[present]
        )
        weight_sum = float(weights.sum())
        if weight_sum <= 0:
            return 0.0
        return float((values * weights).sum() / weight_sum)

    def median(self, column: str) -> float:
        values = self.frame[column].dropna().astype(float)
        if values.empty:
            return 0.0
        return float(values.median())

    def grouped_mean(
        self,
        column: str,
        by: str,
        weighted: bool = False,
        labels: bool = False,
    ) -> pd.DataFrame:
        selected_columns = [column, by] + (
            [self.weight_column] if weighted and self.weight_column else []
        )
        frame = self.frame[selected_columns].dropna(subset=[column, by])
        if weighted and self.weight_column is None:
            raise ValueError("weighted=True requires SurveyData.weight to be set.")
        rows = []
        label_map = (
            self.variables[by].labels
            if labels and self.variables is not None and by in self.variables
            else {}
        )
        for group_value, group in frame.groupby(by, dropna=False):
            values = group[column].astype(float)
            if weighted:
                weights = group[self.weight_column].astype(float)
                weight_sum = float(weights.sum())
                mean_value = float((values * weights).sum() / weight_sum) if weight_sum > 0 else 0.0
                n_value = weight_sum
            else:
                mean_value = float(values.mean()) if not values.empty else 0.0
                n_value = float(values.shape[0])
            row = {"group": group_value, "mean": mean_value, "n": n_value}
            if labels:
                row["label"] = label_map.get(group_value)
            rows.append(row)
        return pd.DataFrame(rows)

    def kruskal(self, column: str, group: str) -> dict[str, Any]:
        try:
            from scipy.stats import kruskal
        except ImportError as exc:
            raise ImportError("kruskal() requires scipy to be installed.") from exc
        used = self.frame[[column, group]].dropna()
        groups = [
            values[column].dropna().astype(float).to_numpy() for _, values in used.groupby(group)
        ]
        if len(groups) < 2:
            raise ValueError("kruskal() requires at least two non-empty groups.")
        statistic, p_value = kruskal(*groups)
        result = {
            "statistic": float(statistic),
            "p_value": float(p_value),
            "groups": float(len(groups)),
        }
        return self._unweighted(self._counted(result, used, [column, group]))

    def mannwhitney(self, column: str, group: str) -> dict[str, Any]:
        try:
            from scipy.stats import mannwhitneyu
        except ImportError as exc:
            raise ImportError("mannwhitney() requires scipy to be installed.") from exc
        used = self.frame[[column, group]].dropna()
        grouped = list(used.groupby(group))
        if len(grouped) != 2:
            raise ValueError("mannwhitney() requires exactly two non-empty groups.")
        (group_a, values_a), (group_b, values_b) = grouped
        statistic, p_value = mannwhitneyu(
            values_a[column].astype(float),
            values_b[column].astype(float),
            alternative="two-sided",
        )
        result = {
            "statistic": float(statistic),
            "p_value": float(p_value),
            "group_a": group_a,
            "group_b": group_b,
        }
        return self._unweighted(self._counted(result, used, [column, group]))

    def spearman(self, x: str, y: str) -> dict[str, Any]:
        try:
            from scipy.stats import spearmanr
        except ImportError as exc:
            raise ImportError("spearman() requires scipy to be installed.") from exc
        frame = self.frame[[x, y]].dropna()
        if frame.empty:
            return self._unweighted({"rho": 0.0, "p_value": 1.0, "n": 0.0})
        result = spearmanr(frame[x], frame[y])
        found = {
            "rho": float(result.statistic),
            "p_value": float(result.pvalue),
            "n": float(frame.shape[0]),
        }
        return self._unweighted(self._counted(found, frame, [x, y]))

    # ── a method chosen by hand (siamang.data.inference) ──────────────
    #
    # Unlike the defaults above, these leave the codebook's missing codes out
    # (a "Don't know" coded 99 is not an answer of 99) and say how many.

    def correlation(
        self, x: str, y: str, *, method: str = "pearson", confidence: float = 0.95
    ) -> dict[str, Any]:
        """Pearson, Spearman or Kendall (tau-b) correlation of ``x`` and ``y``.

        Returns ``method``, the coefficient (``r``, ``rho`` or ``tau``),
        ``p_value``, ``n`` and for Pearson a Fisher-z interval ``lower`` –
        ``upper``. Pearson uses the data's weight when it has one (the weighted
        coefficient, with p and interval on Kish's effective base,
        ``n_effective``, and ``weight`` naming the column); the rank
        correlations say they are unweighted. When the pairs cannot carry a
        correlation the coefficient is None and ``note`` says why.
        """
        from siamang.data import inference

        frame, left_out = inference.without_missing_codes(self.frame, [x, y], self.variables)
        weighted = method == "pearson" and self.weight_column is not None
        try:
            result = inference.correlate(
                frame[x],
                frame[y],
                method=method,
                weights=frame[self.weight_column] if weighted else None,
                confidence=confidence,
            )
        except inference.NotTestable as exc:
            pairs = frame[[x, y]].apply(pd.to_numeric, errors="coerce").dropna()
            result = {
                "method": inference.CORRELATION_NAMES[method],
                inference.CORRELATION_SYMBOLS[method]: None,
                "p_value": None,
                "n": int(len(pairs)),
                "note": str(exc),
            }
        note = inference.missing_codes_note(left_out, self.variables)
        if note:
            result["missing_codes"] = note
        if weighted:
            result["weight"] = self.weight_column
            return result
        return self._unweighted(result)

    def compare_groups(
        self,
        column: str,
        group: str,
        *,
        test: str = "auto",
        posthoc: str = "none",
        adjust: str = "holm",
    ) -> dict[str, Any]:
        """Kruskal-Wallis (or Mann-Whitney) and Dunn's test on every pair of groups.

        ``test`` is ``auto`` (Mann-Whitney for two groups, Kruskal-Wallis for
        more), ``kruskal`` or ``mannwhitney``, as in :meth:`kruskal` and
        :meth:`mannwhitney`, whose keys the result keeps (``statistic``,
        ``p_value``, and ``groups`` or ``group_a`` / ``group_b``) beside
        ``test`` and ``n``. With ``posthoc="dunn"`` after Kruskal-Wallis, one
        entry per pair of groups, keyed by their labels, gives Dunn's z and the
        p adjusted by ``adjust`` (``holm`` or ``bonferroni``); two groups need
        no post-hoc test and the result says so.
        """
        from siamang.data import inference

        if test not in ("auto", "kruskal", "mannwhitney"):
            raise ValueError("test must be 'auto', 'kruskal' or 'mannwhitney'.")
        if posthoc not in ("none", "dunn"):
            raise ValueError("posthoc must be 'none' or 'dunn'.")
        if posthoc == "dunn" and test == "mannwhitney":
            raise ValueError("Dunn's test follows Kruskal-Wallis: test='kruskal' or 'auto'.")
        frame, left_out = inference.without_missing_codes(
            self.frame, [column, group], self.variables
        )
        values = pd.to_numeric(frame[column], errors="coerce")
        clean = pd.DataFrame({"y": values, "g": frame[group]}).dropna()
        labels = (
            self.variables[group].labels
            if self.variables is not None and group in self.variables
            else {}
        )
        codes, samples = [], []
        for code, part in clean.groupby("g"):
            codes.append(code)
            samples.append(part["y"].to_numpy(dtype=float))
        if len(samples) < 2:
            raise ValueError(f"compare_groups() needs at least two non-empty groups of {group!r}.")
        two = test == "mannwhitney" or (test == "auto" and len(samples) == 2)
        try:
            if two:
                if len(samples) != 2:
                    raise ValueError("mannwhitney needs exactly two non-empty groups.")
                found = inference.mannwhitney(samples[0], samples[1])
                result: dict[str, Any] = {
                    "test": found.method,
                    "statistic": found.statistic,
                    "p_value": found.p_value,
                    "group_a": codes[0],
                    "group_b": codes[1],
                }
            else:
                found = inference.kruskal(samples)
                result = {
                    "test": found.method,
                    "statistic": found.statistic,
                    "p_value": found.p_value,
                    "groups": float(len(samples)),
                }
        except inference.NotTestable as exc:
            result = {"test": None, "statistic": None, "p_value": None, "note": str(exc)}
        result["n"] = int(len(clean))
        if posthoc == "dunn":
            if two:
                result["posthoc"] = "not needed: with two groups the test compares the pair"
            else:
                names = [str(labels.get(code, code)) for code in codes]
                try:
                    pairs = inference.posthoc(samples, names, "dunn", adjust=adjust)
                except inference.NotTestable as exc:
                    result["posthoc"] = f"not run: {exc}"
                else:
                    from siamang.reporting.tables import stat_text

                    result["posthoc"] = pairs.name
                    for row in pairs.table.itertuples():
                        result[f"{row.group_1} vs {row.group_2}"] = (
                            f"z = {row.statistic:.3f}, p = {stat_text(float(row.p_adjusted))}"
                        )
        note = inference.missing_codes_note(left_out, self.variables)
        if note:
            result["missing_codes"] = note
        return self._unweighted(result)

    def frequencies(
        self,
        column: str,
        normalize: bool = False,
        weighted: bool = False,
        labels: bool = False,
    ) -> pd.Series | pd.DataFrame:
        if not weighted:
            counts = self.frame[column].value_counts(normalize=normalize, dropna=False)
            return self._with_labels(column, counts) if labels else counts
        if self.weight_column is None:
            raise ValueError("weighted=True requires SurveyData.weight to be set.")
        grouped = self.frame.groupby(column, dropna=False)[self.weight_column].sum()
        if normalize:
            total = grouped.sum()
            if total == 0:
                counts = grouped * 0
            else:
                counts = grouped / total
        else:
            counts = grouped
        return self._with_labels(column, counts) if labels else counts

    def crosstab(
        self,
        row: str,
        col: str,
        normalize: str | bool = False,
        chi2: bool = False,
        cramers_v: bool = False,
        phi: bool = False,
        weighted: bool = False,
        labels: bool = False,
    ) -> pd.DataFrame | tuple[pd.DataFrame, dict[str, float]]:
        norm = normalize if normalize is not False else False
        if weighted:
            if self.weight_column is None:
                raise ValueError("weighted=True requires SurveyData.weight to be set.")
            table = pd.pivot_table(
                self.frame,
                index=row,
                columns=col,
                values=self.weight_column,
                aggfunc="sum",
                fill_value=0.0,
            )
            if norm:
                if norm == "index":
                    table = table.div(table.sum(axis=1).replace({0: pd.NA}), axis=0).fillna(0.0)
                elif norm == "columns":
                    table = table.div(table.sum(axis=0).replace({0: pd.NA}), axis=1).fillna(0.0)
                elif norm is True or norm == "all":
                    total = table.values.sum()
                    table = table / total if total else table * 0.0
                else:
                    raise ValueError(
                        "normalize must be one of False, 'index', 'columns', 'all', or True"
                    )
        else:
            table = pd.crosstab(self.frame[row], self.frame[col], normalize=norm, dropna=False)
        if labels:
            table = self._labeled_crosstab(table, row=row, col=col)
        if not chi2 and not cramers_v and not phi:
            return table
        contingency = pd.crosstab(self.frame[row], self.frame[col], dropna=False)
        try:
            from scipy.stats import chi2_contingency
        except ImportError as exc:
            raise ImportError(
                "chi2=True or cramers_v=True requires scipy to be installed."
            ) from exc
        chi2_stat, p_value, dof, _ = chi2_contingency(contingency.values)
        stats = {"chi2": float(chi2_stat), "p_value": float(p_value), "dof": float(dof)}
        if cramers_v:
            n = float(contingency.values.sum())
            rows, cols = contingency.shape
            min_dim = min(rows - 1, cols - 1)
            stats["cramers_v"] = (
                float((chi2_stat / (n * min_dim)) ** 0.5) if n > 0 and min_dim > 0 else 0.0
            )
        if phi:
            rows, cols = contingency.shape
            n = float(contingency.values.sum())
            if rows == 2 and cols == 2 and n > 0:
                stats["phi"] = float((chi2_stat / n) ** 0.5)
            else:
                raise ValueError("phi=True is only supported for 2x2 tables.")
        return table, stats

    def proportion_ci(
        self,
        column: str,
        value: object,
        confidence: float = 0.95,
        weighted: bool = False,
    ) -> dict[str, Any]:
        """Share choosing ``value`` with a normal-approximation interval.

        The base is the respondents who answered ``column``. ``weighted=True``
        weights the share and takes ``n`` as Kish's effective base of those
        respondents (a missing weight counts as 0). Unweighted on weighted
        data, the result says the weight is not applied.
        """
        if confidence <= 0 or confidence >= 1:
            raise ValueError("confidence must be in (0, 1)")
        result = self._proportion(column, value, confidence, weighted)
        # What the share is of, for a chart's title; the keys are what they were.
        from siamang.data.intervals import Proportion

        variables = self.variables
        variable = variables[column] if variables is not None and column in variables else None
        labels = (variable.labels or {}) if variable is not None else {}
        answer = labels.get(value) if not isinstance(value, list | dict) else None
        return Proportion(
            result,
            variable=column,
            value=value,
            confidence=confidence,
            variable_label=(variable.label if variable is not None else None) or column,
            value_label=str(answer) if answer is not None else None,
        )

    def _proportion(
        self, column: str, value: object, confidence: float, weighted: bool
    ) -> dict[str, Any]:
        z = NormalDist().inv_cdf((1 + confidence) / 2)
        if weighted:
            if self.weight_column is None:
                raise ValueError("weighted=True requires SurveyData.weight to be set.")
            # Of those who answered, as the unweighted share and the weighted
            # frequencies are: counting the others diluted the share.
            answered = _answered(self.frame[column])
            weights = pd.to_numeric(self.frame[self.weight_column], errors="coerce")
            weights = weights.fillna(0.0).astype(float)[answered]
            indicator = _chose(self.frame[column], value)[answered].astype(float)
            weight_sum = float(weights.sum())
            weight_sq = float((weights**2).sum())
            n_eff = weight_sum**2 / weight_sq if weight_sum > 0 and weight_sq > 0 else 0.0
            if n_eff <= 0 or weight_sum <= 0:
                return {
                    "p": 0.0,
                    "lower": 0.0,
                    "upper": 0.0,
                    "n": 0.0,
                    "weight": self.weight_column,
                }
            p = float((indicator * weights).sum() / weight_sum)
            n = n_eff
        else:
            n = float(_answered(self.frame[column]).sum())
            if n <= 0:
                return self._unweighted({"p": 0.0, "lower": 0.0, "upper": 0.0, "n": 0.0})
            p = float(_chose(self.frame[column], value).sum() / n)
        margin = z * ((p * (1 - p) / n) ** 0.5)
        lower = max(0.0, p - margin)
        upper = min(1.0, p + margin)
        result: dict[str, Any] = {"p": p, "lower": lower, "upper": upper, "n": n}
        if weighted:
            result["weight"] = self.weight_column
            return result
        return self._unweighted(result)

    # ── models (siamang.data.models) ──────────────────────────────
    def regression(self, y: str, predictors: list[str], *, kind: str = "auto"):
        """OLS / WLS (with the weight column), logit or the ordinal (proportional
        odds) logit; see :func:`siamang.data.models.regression`."""
        from siamang.data.models import regression

        return regression(
            self.frame,
            y,
            predictors,
            kind=kind,
            weight=self.weight_column,
            variables=self.variables,
        )

    def pca(self, items: list[str], *, n_components: int | None = None, standardize: bool = True):
        """Principal components, of the weighted matrix when the data is weighted;
        see :func:`siamang.data.models.pca`."""
        from siamang.data.models import labelled, pca

        result = pca(
            self.frame,
            items,
            n_components=n_components,
            standardize=standardize,
            weight=self.weight_column,
        )
        labelled(result.loadings, list(items), self.variables)  # for a chart's rows
        return result

    def reliability(self, items: list[str]):
        """Cronbach's alpha, weighted when the data is; see
        :func:`siamang.data.models.reliability`."""
        from siamang.data.models import reliability

        return reliability(self.frame, items, weight=self.weight_column)

    def effective_sample_size(self) -> float:
        if self.weight_column is None:
            raise ValueError("effective_sample_size requires SurveyData.weight to be set.")
        weights = self.frame[self.weight_column].astype(float)
        sum_w = float(weights.sum())
        sum_w2 = float((weights**2).sum())
        if sum_w <= 0 or sum_w2 <= 0:
            return 0.0
        return (sum_w**2) / sum_w2

    def _with_labels(self, column: str, counts: pd.Series) -> pd.DataFrame:
        label_map: dict[object, str] = {}
        if self.variables is not None and column in self.variables:
            label_map = self.variables[column].labels
        total = float(counts.sum()) if len(counts) else 0.0
        rows = []
        for value, n in counts.items():
            n_float = float(n)
            percent = (n_float / total) if total else 0.0
            rows.append(
                {
                    "value": value,
                    "label": label_map.get(value),
                    "n": n_float,
                    "percent": percent,
                }
            )
        return pd.DataFrame(rows)

    def _labeled_crosstab(self, table: pd.DataFrame, row: str, col: str) -> pd.DataFrame:
        labeled = table.copy()
        if self.variables is not None and row in self.variables:
            row_map = self.variables[row].labels
            labeled.index = [row_map.get(value, value) for value in labeled.index]
        if self.variables is not None and col in self.variables:
            col_map = self.variables[col].labels
            labeled.columns = [col_map.get(value, value) for value in labeled.columns]
        return labeled
