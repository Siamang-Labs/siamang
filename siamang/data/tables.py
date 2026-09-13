"""Export-friendly survey table builders."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from siamang.core.variable import VariableMap


@dataclass(frozen=True, slots=True)
class BannerTable:
    """A banner in tidy form: one row per (row value × column value).

    The shape to feed to something else. For the wide cross-break a person
    reads — blocks of columns, a base row, significance letters — use
    ``data.report.banner(...)``, which computes its numbers with the same
    helper so the two can never disagree.
    """

    frame: pd.DataFrame

    def export_csv(self, path: str | Path, **kwargs: Any) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        self.frame.to_csv(output, index=False, **kwargs)
        return output

    def export_xlsx(self, path: str | Path, **kwargs: Any) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        self.frame.to_excel(output, index=False, **kwargs)
        return output


@dataclass(frozen=True, slots=True)
class SurveyTables:
    frame: pd.DataFrame
    variables: VariableMap | None = None
    weight_column: str | None = None

    def banner(
        self,
        rows: list[str],
        columns: list[str],
        weight: str | None = None,
        labels: bool = True,
    ) -> BannerTable:
        if not rows:
            raise ValueError("banner rows must not be empty.")
        if not columns:
            raise ValueError("banner columns must not be empty.")
        weight_column = weight or self.weight_column
        if weight_column is not None and weight_column not in self.frame.columns:
            raise ValueError(f"Weight column '{weight_column}' not found in frame.")

        parts = []
        for row in rows:
            for column in columns:
                parts.append(
                    _banner_pair(self.frame, row, column, weight_column, self.variables, labels)
                )
        if not parts:
            return BannerTable(pd.DataFrame())
        return BannerTable(pd.concat(parts, ignore_index=True))


def _banner_pair(
    frame: pd.DataFrame,
    row: str,
    column: str,
    weight_column: str | None,
    variables: VariableMap | None,
    labels: bool,
) -> pd.DataFrame:
    # Build a frame with names of our own rather than indexing the original by
    # label: a variable used as both a row and a banner column (the way you read
    # a base distribution across the banner) would otherwise select two columns
    # under one name and fail inside groupby.
    data = pd.DataFrame({"_row": frame[row], "_col": frame[column]})
    if weight_column is not None:
        data["_weight"] = frame[weight_column]
    data = data.dropna(subset=["_row", "_col"])
    if weight_column is None:
        grouped = data.groupby(["_row", "_col"], dropna=False).size().reset_index(name="n")
    else:
        grouped = (
            data.groupby(["_row", "_col"], dropna=False)["_weight"].sum().reset_index(name="n")
        )
    grouped["column_total"] = grouped.groupby("_col")["n"].transform("sum")
    grouped["percent"] = grouped["n"] / grouped["column_total"].replace({0: pd.NA})
    grouped["percent"] = grouped["percent"].fillna(0.0)

    row_labels = _labels_for(variables, row) if labels else {}
    column_labels = _labels_for(variables, column) if labels else {}
    result = pd.DataFrame(
        {
            "row_variable": row,
            "row_value": grouped["_row"],
            "row_label": grouped["_row"].map(row_labels) if labels else None,
            "column_variable": column,
            "column_value": grouped["_col"],
            "column_label": grouped["_col"].map(column_labels) if labels else None,
            "n": grouped["n"].astype(float),
            "percent": grouped["percent"].astype(float),
        }
    )
    return result[
        [
            "row_variable",
            "row_value",
            "row_label",
            "column_variable",
            "column_value",
            "column_label",
            "n",
            "percent",
        ]
    ]


def _labels_for(variables: VariableMap | None, name: str) -> dict[Any, str]:
    if variables is None or name not in variables:
        return {}
    return variables[name].labels
