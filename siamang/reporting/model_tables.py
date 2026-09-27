"""What a report shows of a regression and of a scale's reliability.

:func:`siamang.data.models.regression` and :func:`~siamang.data.models.reliability`
keep their numbers as computed — ``RegressionResult.table`` (``term``,
``estimate``, ``std_error`` …) and ``ReliabilityResult.items`` — because a chart
and a script read those columns. Put in a report as they are, they printed
pandas' column names, variable names instead of the codebook's labels, six
significant digits (``1.94157e-45``), ``None`` in the odds ratio of an ordinal
model's thresholds, and the model's statistics nowhere. The tables here are
the same numbers for a reader: labelled from the codebook, rounded as the
other analyses' tables are, with the model's statistics under them.

:class:`RegressionTable` keeps the :class:`~siamang.data.models.RegressionResult`
it shows (``.result``): a Result chart of the Regression node draws from that,
as it drew from the result's own table.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

from siamang.data.listwise import round_p
from siamang.reporting.result_table import ResultTable
from siamang.reporting.tables import _get_label

if TYPE_CHECKING:
    from siamang.data.models import RegressionResult, ReliabilityResult
    from siamang.data.survey_data import SurveyData


def _rounded(value: Any, digits: int) -> float | None:
    """``value`` rounded, or None (a blank cell) when it is missing or infinite."""
    if value is None:
        return None
    number = float(value)
    return round(number, digits) if np.isfinite(number) else None


def _p(value: Any) -> float | None:
    if value is None:
        return None
    number = float(value)
    return round_p(number) if np.isfinite(number) else None


def _interval(lower: Any, upper: Any) -> str | None:
    low, high = _rounded(lower, 3), _rounded(upper, 3)
    if low is None or high is None:
        return None
    return f"{low:.3f} – {high:.3f}"


# ─── regression ──────────────────────────────────────────────────────────────


@dataclass
class RegressionTable(ResultTable):
    """A regression's coefficients as a report shows them; ``result`` is the
    :class:`~siamang.data.models.RegressionResult` they come from."""

    result: Any = None


_MODELS = {
    "OLS": "Linear (OLS)",
    "WLS": "Linear (weighted least squares)",
    "logit": "Logit",
}


def _term_label(term: str, labels: dict[str, str], reference: dict[str, str]) -> str:
    """A coefficient's name for a reader: the predictor's label, and for a
    level of a nominal predictor the level against the one it is compared
    with (``Region: North (vs Capital)``)."""
    if term == "(intercept)":
        return "(Intercept)"
    if term in labels:
        return labels[term]
    name, separator, level = term.partition(" = ")
    if separator:
        label = labels.get(name, name)
        against = reference.get(name)
        return f"{label}: {level}" + (f" (vs {against})" if against else "")
    return term


def _taken_as_numbers(raw: pd.DataFrame, data: SurveyData) -> str:
    """The ordinal predictors the model took as numbers — one slope across
    their codes, which assumes the steps between the answers are equal — by
    their labels. A nominal predictor is dummy-coded instead."""
    variables = data.variables
    if variables is None:
        return ""
    kinds = raw["type"] if "type" in raw.columns else pd.Series("coefficient", index=raw.index)
    names = [
        str(term)
        for term, kind in zip(raw["term"], kinds, strict=True)
        if kind == "coefficient" and term != "(intercept)" and " = " not in str(term)
    ]
    return ", ".join(
        _get_label(data, name)
        for name in names
        if name in variables and variables[name].scale == "ordinal"
    )


def regression_table(result: RegressionResult, data: SurveyData) -> RegressionTable:
    """``result`` as a report table: one row per coefficient (for an ordinal
    model, then one per threshold) with the estimate, its standard error, the
    test statistic and p — and for a logit or an ordinal model the odds ratio,
    and its 95 % Wald interval where the model gives one, on the coefficients
    only (a threshold is where the scale is cut, not an effect). Rounded to
    three decimals (the statistic to two, p as the other tables print it);
    the model's N and fit are the footer."""

    raw = result.table
    stats = dict(result.stats)
    labels = dict(raw.attrs.get("labels") or {})
    reference = dict(raw.attrs.get("reference") or {})
    ordinal = result.kind == "ordinal"
    statistic = "t" if result.kind == "ols" else "z"
    has_ratio = "odds_ratio" in raw.columns
    has_interval = "odds_ratio_lower" in raw.columns
    rows: list[dict[str, Any]] = []
    for record in raw.to_dict("records"):
        threshold = ordinal and record.get("type") == "threshold"
        term = str(record["term"])
        row: dict[str, Any] = {
            "Term": f"Threshold: {term}" if threshold else _term_label(term, labels, reference),
            "Estimate": _rounded(record["estimate"], 3),
            "SE": _rounded(record["std_error"], 3),
            statistic: _rounded(record["statistic"], 2),
            "p": _p(record["p_value"]),
        }
        if has_ratio:
            row["Odds ratio"] = None if threshold else _rounded(record.get("odds_ratio"), 3)
        if has_interval:
            row["95% CI"] = (
                None
                if threshold
                else _interval(record.get("odds_ratio_lower"), record.get("odds_ratio_upper"))
            )
        rows.append(row)
    frame = pd.DataFrame(rows)
    # A logit's outcome is "y = the answer modelled".
    y, _, answer = str(stats.get("outcome", "")).partition(" = ")
    outcome = labels.get(y, y) + (f" = {answer}" if answer else "")
    footer: dict[str, Any] = {}
    if ordinal:
        footer["Model"] = "Proportional odds (cumulative logit)"
        footer["Outcome"] = outcome
        if stats.get("order"):
            footer["Answers in order"] = stats["order"]
    else:
        footer["Model"] = _MODELS.get(str(stats.get("model")), stats.get("model"))
        footer["Outcome"] = outcome
    footer["N"] = stats.get("n")
    if "r_squared" in stats:
        footer["R²"] = _rounded(stats["r_squared"], 4)
        footer["Adjusted R²"] = _rounded(stats.get("adj_r_squared"), 4)
        footer["Residual SE"] = _rounded(stats.get("residual_se"), 3)
    if "pseudo_r_squared" in stats:
        footer["McFadden's pseudo-R²"] = _rounded(stats["pseudo_r_squared"], 4)
    if "lr_chi_square" in stats:
        footer["LR chi-square"] = _rounded(stats["lr_chi_square"], 3)
        footer["df"] = stats.get("lr_df")
        footer["p"] = _p(stats.get("lr_p"))
    if "aic" in stats:
        footer["AIC"] = _rounded(stats["aic"], 1)
    if ordinal:
        footer["Coefficients"] = stats.get("coefficients")
    linear = _taken_as_numbers(raw, data)
    if linear:
        footer["Taken as numbers"] = (
            f"{linear} (ordinal, one slope across the codes, which assumes equal steps "
            "between the answers)"
        )
    if stats.get("converged") == 0:
        footer["Converged"] = "no — the estimates may not be the maximum"
    for key, name in (
        ("missing_codes", "Missing codes left out"),
        ("note", "Note"),
        ("warning", "Warning"),
        ("weight", "Weight"),
        ("weights", "Weights"),
    ):
        if stats.get(key):
            footer[name] = stats[key]
    footer = {key: value for key, value in footer.items() if value is not None}
    return RegressionTable(data=data, frame=frame, footer=footer, result=result)


# ─── reliability ─────────────────────────────────────────────────────────────


def reliability_table(result: ReliabilityResult, data: SurveyData) -> ResultTable:
    """Cronbach's alpha as a report table: one row per item with its label, its
    mean, its correlation with the sum of the other items (the corrected
    item-total correlation) and the alpha without it,
    rounded to three decimals; alpha, the number of items and N are the footer."""

    rows = [
        {
            "Variable": record["item"],
            "Label": _get_label(data, str(record["item"])),
            "Mean": _rounded(record["mean"], 3),
            "Item-total r": _rounded(record["item_total_correlation"], 3),
            "Alpha if deleted": _rounded(record["alpha_if_deleted"], 3),
        }
        for record in result.items.to_dict("records")
    ]
    stats = dict(result.stats)
    footer: dict[str, Any] = {
        "Cronbach's alpha": _rounded(result.alpha, 3),
        "Items": stats.get("n_items"),
        "N": stats.get("n"),
        "Item-total r": "corrected: each item with the sum of the others",
    }
    if stats.get("weight"):
        footer["Weight"] = stats["weight"]
    return ResultTable(data=data, frame=pd.DataFrame(rows), footer=footer)


__all__ = ["RegressionTable", "regression_table", "reliability_table"]
