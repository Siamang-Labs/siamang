"""SurveyData container with processing and analysis accessors."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from siamang.core.expression import Expression
from siamang.core.questionnaire import Questionnaire
from siamang.core.variable import ValidationIssue, Variable, VariableMap
from siamang.data import multi
from siamang.data.analysis import DataAnalysis
from siamang.data.processing import DataProcessing
from siamang.data.tables import SurveyTables


@dataclass(frozen=True, slots=True)
class ClusterAssignment:
    """What :meth:`SurveyData.cluster` returns: the data with the cluster
    variable, and the centroids table."""

    data: SurveyData
    centroids: pd.DataFrame
    stats: dict[str, float | int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SurveyData:
    frame: pd.DataFrame
    variables: VariableMap | None = None
    questionnaire: Questionnaire | None = None
    weight: str | None = None

    @property
    def processing(self) -> DataProcessing:
        return DataProcessing(self.frame)

    @property
    def analysis(self) -> DataAnalysis:
        return DataAnalysis(self.frame, weight_column=self.weight, variables=self.variables)

    @property
    def tables(self) -> SurveyTables:
        return SurveyTables(self.frame, variables=self.variables, weight_column=self.weight)

    @property
    def report(self):
        """Declarative table-generation accessor (FreqTable, CrossTable, GroupMeanTable)."""
        from siamang.reporting.accessors import ReportAccessor

        return ReportAccessor(self)

    @property
    def plot(self):
        """Declarative chart-generation accessor (BarChart, BoxPlot, HeatMap, ScatterPlot)."""
        from siamang.reporting.accessors import PlotAccessor

        return PlotAccessor(self)

    def with_frame(self, frame: pd.DataFrame) -> SurveyData:
        return SurveyData(
            frame=frame,
            variables=self.variables,
            questionnaire=self.questionnaire,
            weight=self.weight,
        )

    def with_derived(
        self,
        name: str,
        values: pd.Series,
        *,
        label: str | None = None,
        scale: str = "nominal",
        labels: dict[object, str] | None = None,
    ) -> SurveyData:
        """Attach a computed column *and* the variable that documents it.

        :meth:`with_frame` carries ``variables`` through untouched, so a column
        added that way is invisible to :meth:`codebook`, to ``analyze.describe``
        and to the dictionary written beside an export — and naming it in a
        later node is an error, because it is not in the codebook. :meth:`derive`
        registers a variable but only accepts an :class:`Expression`; this takes
        a Series any helper can produce.
        """

        frame = self.frame.copy()
        frame[name] = values
        variables = self._variables_with(
            Variable(name, scale, label=label or name, labels=labels or {}, role="derived")
        )
        return SurveyData(
            frame=frame,
            variables=variables,
            questionnaire=self.questionnaire,
            weight=self.weight,
        )

    def explode_multi(
        self,
        column: str,
        *,
        prefix: str | None = None,
        drop: bool = False,
    ) -> SurveyData:
        """Turn a multiple-choice column into one 0/1 variable per option.

        A list of codes is the honest way to *store* the answer and the wrong
        shape for most of what is done with it afterward: weighting, regression,
        clustering and TURF all need a rectangle of numbers. This makes that
        rectangle — ``<column>_<code>`` per option, labeled from the codebook
        and registered as variables, so the columns are nameable in later nodes.

        Non-respondents get missing values rather than zeros, which keeps every
        base computed downstream the same as the one
        :func:`siamang.data.multi.frequencies` reports. ``drop`` removes the
        original column; by default it stays, because the two shapes answer
        different questions and both are cheap to keep.
        """

        if column not in self.frame.columns:
            raise ValueError(f"Column '{column}' not found in frame.")
        source = self.variables.get(column) if self.variables is not None else None
        labels: dict[Any, str] = dict(source.labels) if source is not None else {}
        # Codebook order first — it is the order the question was asked in —
        # then anything the data holds that the codebook does not know about.
        codes: list[Any] = list(labels)
        codes += [code for code in multi.codes_in(self.frame[column]) if code not in codes]
        if not codes:
            raise ValueError(f"Column '{column}' has no answers to explode.")

        stem = f"{column}_" if prefix is None else prefix
        indicators = multi.explode(self.frame[column], codes=codes, prefix=stem)
        frame = self.frame.copy()
        for name in indicators.columns:
            frame[name] = indicators[name]
        if drop:
            frame = frame.drop(columns=[column])

        question = (source.label if source is not None else None) or column
        # Same contract as with_derived: a frame that was carrying no codebook
        # still comes back with one for the columns this just invented.
        variables = VariableMap()
        if self.variables is not None:
            for existing in self.variables.values():
                if existing.name in indicators.columns or (drop and existing.name == column):
                    continue
                variables.add(existing)
        for code in codes:
            variables.add(
                Variable(
                    f"{stem}{code}",
                    "nominal",
                    label=f"{question}: {labels.get(code, code)}",
                    labels={0: "No", 1: "Yes"},
                    role="derived",
                    description=f"Chose code {code!r} of multiple-choice {column}",
                )
            )
        return SurveyData(
            frame=frame,
            variables=variables,
            questionnaire=self.questionnaire,
            weight=self.weight,
        )

    def with_weight(self, column: str) -> SurveyData:
        if column not in self.frame.columns:
            raise ValueError(f"Weight column '{column}' not found in frame.")
        return SurveyData(
            frame=self.frame,
            variables=self.variables,
            questionnaire=self.questionnaire,
            weight=column,
        )

    def codebook(self) -> pd.DataFrame:
        if self.variables is None:
            raise ValueError("SurveyData has no variable metadata. Attach VariableMap first.")
        rows = []
        for variable in self.variables.values():
            rows.append(
                {
                    "name": variable.name,
                    "label": variable.label,
                    "scale": variable.scale,
                    "dtype": variable.dtype,
                    "role": variable.role,
                    "description": variable.description,
                    "missing_values": list(variable.missing_values),
                    "missing_kinds": variable.missing_kinds_dict(),
                    "missing": [item.to_dict() for item in variable.structured_missing_values()],
                    "valid_range": list(variable.valid_range)
                    if variable.valid_range is not None
                    else None,
                }
            )
        return pd.DataFrame(rows)

    def describe_variables(self) -> pd.DataFrame:
        if self.variables is None:
            raise ValueError("SurveyData has no variable metadata. Attach VariableMap first.")
        rows = []
        for variable in self.variables.values():
            series = (
                self.frame[variable.name]
                if variable.name in self.frame.columns
                else pd.Series(dtype="object")
            )
            rows.append(
                {
                    "name": variable.name,
                    "label": variable.label or variable.name,
                    "scale": variable.scale,
                    "n": int(series.shape[0]),
                    "n_missing": int(series.isna().sum()) if series.shape[0] else 0,
                    "n_unique": int(series.nunique(dropna=True)) if series.shape[0] else 0,
                }
            )
        return pd.DataFrame(rows)

    def validate(self, raise_on_error: bool = False) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        if self.variables is None:
            issues.append(
                ValidationIssue(
                    code="MISSING_METADATA",
                    severity="warning",
                    message="SurveyData has no variable metadata; frame validation was skipped.",
                )
            )
        else:
            issues.extend(self.variables.validate_frame(self.frame))

        if self.weight is not None:
            if self.weight not in self.frame.columns:
                issues.append(
                    ValidationIssue(
                        code="MISSING_WEIGHT_COLUMN",
                        severity="error",
                        message=f"SurveyData weight column '{self.weight}' is not present in frame.",
                        column=self.weight,
                    )
                )
            elif not pd.api.types.is_numeric_dtype(self.frame[self.weight].dropna()):
                issues.append(
                    ValidationIssue(
                        code="INVALID_WEIGHT",
                        severity="error",
                        message=f"SurveyData weight column '{self.weight}' must be numeric.",
                        column=self.weight,
                    )
                )

        if self.questionnaire is not None:
            from siamang.core.question import question_variable_names

            expected = {
                name
                for question in self.questionnaire.all_questions()
                for name in question_variable_names(question)
            }
            missing = sorted(expected - set(self.frame.columns))
            for name in missing:
                issues.append(
                    ValidationIssue(
                        code="QUESTIONNAIRE_COLUMN_MISSING",
                        severity="error",
                        message=f"Questionnaire variable '{name}' is missing from SurveyData frame.",
                        variable=name,
                        column=name,
                    )
                )

        if raise_on_error and any(issue.severity == "error" for issue in issues):
            codes = ", ".join(issue.code for issue in issues if issue.severity == "error")
            raise ValueError(f"SurveyData validation failed: {codes}")
        return issues

    def apply_missing_values(
        self, kinds: set[str] | list[str] | tuple[str, ...] | None = None
    ) -> SurveyData:
        if self.variables is None:
            raise ValueError("SurveyData has no variable metadata. Attach VariableMap first.")
        selected_kinds = set(kinds) if kinds is not None else None
        frame = self.frame.copy()
        for variable in self.variables.values():
            if variable.name not in frame.columns:
                continue
            missing_codes = [
                item.code
                for item in variable.structured_missing_values()
                if selected_kinds is None or item.kind in selected_kinds
            ]
            if missing_codes:
                frame[variable.name] = frame[variable.name].replace(missing_codes, pd.NA)
        return self.with_frame(frame)

    def drop_missing(self, column: str) -> SurveyData:
        frame = self.frame.copy()
        frame = frame.dropna(subset=[column])
        return self.with_frame(frame)

    def recode(
        self,
        column: str,
        *,
        into: str,
        bins: list[int | float],
        labels: list[str] | None = None,
        right: bool = False,
        label: str | None = None,
    ) -> SurveyData:
        if len(bins) < 2:
            raise ValueError("bins must contain at least two boundaries.")
        category_labels = labels or _bin_labels(bins)
        if len(category_labels) != len(bins) - 1:
            raise ValueError("labels length must be exactly len(bins) - 1.")
        categories = pd.cut(
            self.frame[column],
            bins=bins,
            labels=range(1, len(category_labels) + 1),
            include_lowest=True,
            right=right,
        )
        frame = self.frame.copy()
        frame[into] = categories.astype("Int64")
        variables = self._variables_with(
            Variable(
                into,
                "ordinal",
                label=label or into,
                labels={index + 1: value for index, value in enumerate(category_labels)},
                role="derived",
            )
        )
        return SurveyData(
            frame=frame,
            variables=variables,
            questionnaire=self.questionnaire,
            weight=self.weight,
        )

    def recode_values(
        self,
        column: str,
        mapping: dict[object, object],
        *,
        into: str | None = None,
        label: str | None = None,
        scale: str | None = None,
    ) -> SurveyData:
        target = into or f"{column}_recoded"
        frame = self.frame.copy()
        frame[target] = frame[column].map(mapping)
        source = (
            self.variables[column]
            if self.variables is not None and column in self.variables
            else None
        )
        value_labels = {value: str(value) for value in mapping.values()}
        variables = self._variables_with(
            Variable(
                target,
                scale or (source.scale if source is not None else "nominal"),
                label=label or target,
                labels=value_labels,
                role="derived",
            )
        )
        return SurveyData(
            frame=frame,
            variables=variables,
            questionnaire=self.questionnaire,
            weight=self.weight,
        )

    def filter(self, expression: Expression) -> SurveyData:
        """Keep the rows for which ``expression`` (a questionnaire condition) is true.

        The expression is evaluated row by row against the frame's columns, the
        same way visibility conditions are evaluated against answers.
        """

        if not isinstance(expression, Expression):
            raise TypeError("filter() expects an Expression built from questionnaire variables.")
        mask = self.frame.apply(lambda row: bool(expression.evaluate(row.to_dict())), axis=1)
        if mask.empty:
            return self.with_frame(self.frame.copy())
        return self.with_frame(self.frame[mask.astype(bool)])

    def derive(
        self,
        *,
        name: str,
        expression: Expression,
        label: str | None = None,
        scale: str = "nominal",
        labels: dict[object, str] | None = None,
    ) -> SurveyData:
        frame = self.frame.copy()
        frame[name] = frame.apply(lambda row: int(expression.evaluate(row.to_dict())), axis=1)
        variables = self._variables_with(
            Variable(
                name,
                scale,
                label=label or name,
                labels=labels or {0: "No", 1: "Yes"},
                role="derived",
            )
        )
        return SurveyData(
            frame=frame,
            variables=variables,
            questionnaire=self.questionnaire,
            weight=self.weight,
        )

    def derive_formula(
        self,
        name: str,
        formula: str,
        *,
        label: str | None = None,
        scale: str = "ratio",
        labels: dict[object, str] | None = None,
    ) -> SurveyData:
        """A new variable computed by arithmetic over the existing ones.

        :meth:`derive` builds an indicator from a *condition* — the answer is
        yes or no. This builds a number: spend per month from spend per year,
        the gap between two ratings, a score rescaled. The formula is text,
        parsed and evaluated by :mod:`siamang.data.formula`; nothing is
        executed, and a formula that cannot be read says where reading stopped.

        The default scale is ``ratio`` because arithmetic produces quantities.
        Say otherwise when the result is a code rather than an amount.

            data.derive_formula("spend_month", "round(spend_year / 12, 2)")
            data.derive_formula("band", "if age < 30 then 1 else 2",
                                scale="ordinal", labels={1: "Under 30", 2: "30+"})
        """

        from siamang.data.formula import parse

        values = parse(formula).evaluate(self.frame)
        frame = self.frame.copy()
        frame[name] = values
        variables = self._variables_with(
            Variable(
                name,
                scale,
                # The formula itself is the most honest label there is: it says
                # exactly how the number was made, and it travels with the
                # codebook into every export and dictionary.
                label=label or formula,
                labels=labels or {},
                role="derived",
            )
        )
        return SurveyData(
            frame=frame,
            variables=variables,
            questionnaire=self.questionnaire,
            weight=self.weight,
        )

    def _variables_with(self, variable: Variable) -> VariableMap:
        variables = VariableMap()
        if self.variables is not None:
            for existing in self.variables.values():
                if existing.name != variable.name:
                    variables.add(existing)
        variables.add(variable)
        return variables

    def scale_alpha(self, items: list[str]) -> float:
        if len(items) < 2:
            raise ValueError("scale_alpha requires at least two items.")
        frame = self._numeric_items_frame(items).dropna()
        if frame.empty:
            return 0.0
        item_variances = frame.var(axis=0, ddof=1).sum()
        total_variance = frame.sum(axis=1).var(ddof=1)
        if total_variance <= 0:
            return 0.0
        k = len(items)
        return float((k / (k - 1)) * (1 - item_variances / total_variance))

    def create_index(
        self,
        name: str,
        *,
        items: list[str],
        method: str = "mean",
        label: str | None = None,
    ) -> SurveyData:
        if method not in ("mean", "sum"):
            raise ValueError("create_index supports method='mean' or method='sum'.")
        if not items:
            raise ValueError("create_index requires at least one item.")
        frame = self.frame.copy()
        item_frame = self._numeric_items_frame(items)
        if method == "sum":
            frame[name] = item_frame.sum(axis=1, skipna=True, min_count=1)
        else:
            frame[name] = item_frame.mean(axis=1, skipna=True)
        variables = self._variables_with(
            Variable(
                name,
                "interval",
                label=label or name,
                role="derived",
                description=f"{method.capitalize()} index from items: {', '.join(items)}",
            )
        )
        return SurveyData(
            frame=frame,
            variables=variables,
            questionnaire=self.questionnaire,
            weight=self.weight,
        )

    def cluster(
        self,
        items: list[str],
        *,
        k: int = 3,
        into: str = "cluster",
        seed: int | None = 42,
        standardize: bool = True,
        label: str | None = None,
    ) -> ClusterAssignment:
        """k-means on ``items``: a copy of the data with the cluster number in
        ``into`` (a nominal variable labeled "Cluster 1".."Cluster k") and the
        centroid table (:func:`siamang.data.models.kmeans`)."""
        from siamang.data.models import kmeans

        result = kmeans(
            self._numeric_items_frame(items),
            items,
            k=k,
            seed=seed,
            standardize=standardize,
        )
        frame = self.frame.copy()
        frame[into] = result.labels.astype("Int64")
        variables = self._variables_with(
            Variable(
                into,
                "nominal",
                label=label or f"Cluster ({', '.join(items)})",
                labels={i: f"Cluster {i}" for i in range(1, k + 1)},
                role="derived",
                description=f"k-means, k={k}, on items: {', '.join(items)}",
            )
        )
        data = SurveyData(
            frame=frame, variables=variables, questionnaire=self.questionnaire, weight=self.weight
        )
        return ClusterAssignment(data=data, centroids=result.centroids, stats=result.stats)

    def _numeric_items_frame(self, items: list[str]) -> pd.DataFrame:
        missing_normalized = self.apply_missing_values() if self.variables is not None else self
        frame = missing_normalized.frame[items]
        listed = [name for name in items if multi.is_multi(frame[name])]
        if listed:
            # to_numeric would coerce every list to NaN and the item would drop
            # out of the index in silence, which is the worst of the outcomes.
            raise TypeError(
                f"{', '.join(listed)} hold multiple-choice answers (lists of codes), "
                "which have no single numeric value. Run prepare.explode first: it "
                "turns each option into its own 0/1 column, and those are what an "
                "index, a scale or a cluster is built from."
            )
        return frame.apply(pd.to_numeric, errors="coerce")

    def export_dictionary(self, path: str = "survey_dictionary.json"):
        if self.variables is None:
            raise ValueError("SurveyData has no variable metadata. Attach VariableMap first.")
        from siamang.io.dictionary import DictionaryWriter

        return DictionaryWriter().write(self.variables, path)

    def export(self, fmt: str, path: str | None = None, **kwargs):
        fmt = fmt.lower()
        if fmt == "csv":
            from pathlib import Path

            from siamang.io.csv import CSVWriter

            output = Path(path or "survey_data.csv")
            return CSVWriter().write(self, output, **kwargs)
        if fmt in {"xlsx", "excel"}:
            from pathlib import Path

            from siamang.io.excel import ExcelWriter

            output = Path(path or "survey_data.xlsx")
            return ExcelWriter().write(self, output, **kwargs)
        if fmt == "r":
            from pathlib import Path

            from siamang.io.r import RScriptWriter

            output = Path(path or "survey_r_export")
            return RScriptWriter().write(self, output)
        if fmt in {"spss", "sav"}:
            from pathlib import Path

            from siamang.io.spss import SPSSWriter

            output = Path(path or "survey_data.sav")
            return SPSSWriter().write(self, output, **kwargs)
        if fmt in {"stata", "dta"}:
            from pathlib import Path

            from siamang.io.stata import StataWriter

            output = Path(path or "survey_data.dta")
            return StataWriter().write(self, output, **kwargs)
        raise NotImplementedError(f"Unsupported export format: {fmt}")


def _bin_labels(bins: list[int | float]) -> list[str]:
    labels: list[str] = []
    for start, end in zip(bins[:-1], bins[1:], strict=True):
        labels.append(f"{start}-{end}")
    return labels
