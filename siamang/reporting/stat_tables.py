"""Tables for the tests beyond the defaults: t-tests, correlation matrices and
post-hoc comparisons, and the statistics Group means and Crosstab report when
a test is chosen by hand.

The numbers come from :mod:`siamang.data.inference`; this module only lays
them out — labels from the codebook, rounding, and a footer that names the
test, what it was computed on and what it left out. A test the data cannot
carry is reported in words ("not run: …") rather than as a number, and a cell
it leaves undefined (the SD of one answer, a pair that could not be compared)
is blank when printed — NaN in ``to_frame()``, never ``nan`` or ``None`` in a
report.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

from siamang.data import inference
from siamang.reporting.tables import (
    SurveyTable,
    _BlankUndefined,
    _get_label,
    _get_value_labels,
    _unweighted_note,
    _weights_of,
    frame_to_html,
)

if TYPE_CHECKING:
    from siamang.data.survey_data import SurveyData


#: The tests Group means can be told to run, and the name each goes by.
MEANS_TESTS = {
    "student": "Student's t-test (equal variances)",
    "welch": "Welch's t-test (unequal variances)",
    "anova": "One-way ANOVA",
    "welch_anova": "Welch's ANOVA",
    "mannwhitney": "Mann-Whitney U",
    "kruskal": "Kruskal-Wallis H",
}
_TWO_GROUP_TESTS = ("student", "welch", "mannwhitney")


def _df(value: float | None) -> int | float | None:
    if value is None or value != value:
        return None
    return int(value) if float(value).is_integer() else round(float(value), 2)


def _interval(lower: float | None, upper: float | None) -> str | None:
    if lower is None or upper is None or lower != lower or upper != upper:
        return None
    return f"{_number(lower)} – {_number(upper)}"


def _number(value: float) -> str:
    return "∞" if value == float("inf") else f"{value:.3f}"


def _ci_key(confidence: float) -> str:
    return f"{confidence * 100:g}% CI"


def _marks(p: float) -> str:
    if p != p:
        return ""
    return "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""


def _missing_codes(data: SurveyData, left_out: dict[str, list[tuple[Any, int]]]) -> dict[str, str]:
    note = inference.missing_codes_note(left_out, data.variables)
    return {"Missing codes left out": note} if note else {}


# ─── Group means with a test chosen by hand ──────────────────────────────────


def means_test(
    samples: list[np.ndarray],
    names: list[str],
    method: str,
    *,
    by_label: str,
) -> dict[str, Any]:
    """The footer of Group means for a test chosen by hand: the test's name,
    statistic, df, p and effect size — or, when the data cannot carry it, a
    sentence saying why."""

    name = MEANS_TESTS[method]
    if method in _TWO_GROUP_TESTS and len(samples) != 2:
        alternative = "kruskal" if method == "mannwhitney" else "anova or welch_anova"
        return {
            "Test": (
                f"not run: {name} compares two groups and {by_label} has {len(samples)} "
                f"— choose {alternative}"
            )
        }
    try:
        if method in ("student", "welch"):
            result = inference.ttest_independent(
                samples[0], samples[1], equal_var=method == "student", names=(names[0], names[1])
            )
            stats: dict[str, Any] = {
                "Test": result.method,
                "t": round(result.t, 3),
                "df": _df(result.df),
                "p": round(result.p_value, 4),
                "Mean difference": round(result.difference, 3),
                "Difference": f"{names[0]} − {names[1]}",
                _ci_key(result.confidence): _interval(result.lower, result.upper),
                "Cohen's d": round(result.cohens_d, 3) if result.cohens_d is not None else None,
            }
            return stats
        if method == "anova":
            found = inference.anova(samples)
        elif method == "welch_anova":
            found = inference.welch_anova(samples, names)
        elif method == "kruskal":
            found = inference.kruskal(samples)
        else:
            found = inference.mannwhitney(samples[0], samples[1])
    except inference.NotTestable as exc:
        return {"Test": f"not run: {exc}"}
    stats = {"Test": found.method, found.symbol: round(found.statistic, 3)}
    if found.df is not None:
        stats["df"] = (
            f"{_df(found.df)}, {_df(found.df2)}" if found.df2 is not None else _df(found.df)
        )
    stats["p"] = round(found.p_value, 4)
    if found.effect_name is not None and found.effect is not None:
        stats[found.effect_name] = round(found.effect, 3)
    return stats


def posthoc_for(
    data: SurveyData,
    samples: list[np.ndarray],
    names: list[str],
    method: str,
    *,
    adjust: str = "holm",
    by: str = "",
) -> tuple[dict[str, Any], PostHocTable | None]:
    """The post-hoc comparison of every pair of groups: its summary for the
    footer, and the table of pairs (None when it could not run)."""

    try:
        result = inference.posthoc(samples, names, method, adjust=adjust)
    except inference.NotTestable as exc:
        return {"Post-hoc": f"{inference.POSTHOC_NAMES[method]}: not run — {exc}"}, None
    tested = int(result.table["p_adjusted"].notna().sum())
    summary: dict[str, Any] = {
        "Post-hoc": f"{result.name}: {result.significant()} of {tested} pairs differ at p < 0.05"
    }
    if result.notes:
        summary["Post-hoc not compared"] = "; ".join(result.notes)
    return summary, PostHocTable(data=data, result=result, by=by)


# ─── PostHocTable ────────────────────────────────────────────────────────────


@dataclass
class PostHocTable(_BlankUndefined, SurveyTable):
    """Every pair of groups after a test of several, one row per pair.

    Tukey's HSD and Games-Howell give the difference of the means with its
    simultaneous confidence interval, the studentized range statistic q and a
    p that already allows for the number of pairs. Dunn's test gives the
    difference of the mean ranks, z, and p before and after the adjustment
    chosen (Holm or Bonferroni). Rendered under the Group means table it
    follows, and available on its own as ``GroupMeanTable.posthoc_table``.
    """

    result: Any = None
    by: str = ""

    @property
    def title(self) -> str:
        return f"Post-hoc: {self.result.name}"

    def _build(self) -> None:
        result: inference.PostHoc = self.result
        table = result.table
        pairs = [f"{a} vs {b}" for a, b in zip(table["group_1"], table["group_2"], strict=True)]
        rounded = lambda column, digits: [  # noqa: E731
            None if value != value else round(float(value), digits) for value in table[column]
        ]
        if result.method == "dunn":
            frame = pd.DataFrame(
                {
                    "Pair": pairs,
                    "Mean rank difference": rounded("difference", 3),
                    "z": rounded("statistic", 3),
                    "p (unadjusted)": rounded("p_value", 4),
                    f"p ({inference.ADJUSTMENT_NAMES[result.adjust]})": rounded("p_adjusted", 4),
                }
            )
        else:
            ci = _ci_key(result.confidence)
            columns: dict[str, Any] = {
                "Pair": pairs,
                "Difference": rounded("difference", 3),
                f"{ci} low": rounded("lower", 3),
                f"{ci} high": rounded("upper", 3),
                "q": rounded("statistic", 3),
            }
            if result.method == "games_howell":
                columns["df"] = rounded("df", 2)
            columns["p"] = rounded("p_adjusted", 4)
            frame = pd.DataFrame(columns)
        self._result = frame
        stats: dict[str, Any] = {"Method": result.name}
        if self.by:
            stats["Groups"] = _get_label(self.data, self.by)
        if result.method == "dunn":
            stats["Difference"] = "mean rank of the first group minus the second"
        else:
            stats["Difference"] = "mean of the first group minus the second"
            stats["p"] = "adjusted for the number of pairs by the method itself"
        if result.notes:
            stats["Not compared"] = "; ".join(result.notes)
        if (note := _unweighted_note(self.data)) is not None:
            stats["Weight"] = note
        self._stats = stats

    def to_markdown(self) -> str:
        return f"**{self.title}**\n\n" + super().to_markdown()

    def to_html(self) -> str:
        html = frame_to_html(self._printable(), caption=self.title)
        if self._stats:
            html += f"\n<p class='siamang-stats'>{self._format_stats()}</p>"
        return html


# ─── Crosstab with Fisher's exact test ───────────────────────────────────────


def fisher_stats(
    data: SurveyData,
    counts: pd.DataFrame,
    *,
    row: str,
    col: str,
    weights: pd.Series | None,
    left_out: dict[str, list[tuple[Any, int]]],
) -> dict[str, Any]:
    """The Crosstab footer for Fisher's exact test on ``counts`` (people, not
    weights: an exact test needs whole counts)."""

    n = int(counts.to_numpy().sum())
    stats: dict[str, Any]
    try:
        found = inference.fisher_exact(counts.to_numpy())
    except inference.NotTestable as exc:
        stats = {"Test": f"Fisher's exact test: not run — {exc}", "N": n}
    else:
        stats = {"Test": found["method"], "p": round(found["p_value"], 4)}
        if "odds_ratio" in found:
            row_labels = _get_value_labels(data, row)
            col_labels = _get_value_labels(data, col)
            r = [row_labels.get(value, str(value)) for value in counts.index]
            c = [col_labels.get(value, str(value)) for value in counts.columns]
            stats["Odds ratio"] = (
                "∞" if found["odds_ratio"] == float("inf") else round(found["odds_ratio"], 3)
            )
            stats[f"OR {_ci_key(found['confidence'])}"] = _interval(found["lower"], found["upper"])
            stats["Odds ratio of"] = f"{c[0]} (vs {c[1]}) for {r[0]} over {r[1]}"
            stats["Estimate"] = "conditional maximum likelihood, as R's fisher.test"
        elif found["exact"]:
            stats["p method"] = "exact, over every table with these margins"
        else:
            stats["p method"] = (
                f"Monte Carlo, {found['samples']:,} random tables with these margins from a "
                f"fixed seed (± {found['p_error']:.4f}); too many tables to sum exactly"
            )
        stats["N"] = n
    if weights is not None:
        stats["Weighted N"] = round(float(weights.sum()), 1)
        stats["Weight"] = data.weight
        stats["Base"] = (
            "the test counts respondents (an exact test needs whole counts); weighted counts shown"
        )
    stats.update(_missing_codes(data, left_out))
    return stats


# ─── TTestTable ──────────────────────────────────────────────────────────────

TTEST_KINDS = ("independent", "paired", "one_sample")


@dataclass
class TTestTable(_BlankUndefined, SurveyTable):
    """A t-test with the descriptives it rests on.

    ``kind="independent"`` compares ``column`` between two groups of ``by`` —
    the two named in ``groups`` when ``by`` has more than two values —
    with Welch's test (``variances="welch"``, the default: it does not assume
    equal variances) or Student's (``"student"``). ``"paired"`` compares
    ``column`` with ``other``, measured on the same respondents, over the
    complete pairs. ``"one_sample"`` tests the mean of ``column`` against
    ``mu``.

    One row per group (or measurement): N, mean, SD and the standard error;
    the footer gives t, df, p, the mean difference with its confidence
    interval and Cohen's d (Hedges' g beside it for two groups). The codebook's
    missing codes are left out and counted. The test has no standard weighted
    form, so on weighted data it runs on the respondents and says so.
    """

    column: str = ""
    kind: str = "independent"
    by: str | None = None
    groups: list[Any] | None = None
    other: str | None = None
    mu: float = 0.0
    variances: str = "welch"
    confidence: float = 0.95

    def _build(self) -> None:
        if self.kind not in TTEST_KINDS:
            raise ValueError(f"kind must be one of {', '.join(TTEST_KINDS)}; got {self.kind!r}.")
        if self.variances not in ("welch", "student"):
            raise ValueError("variances must be 'welch' or 'student'.")
        if not 0 < self.confidence < 1:
            raise ValueError("confidence must be between 0 and 1.")
        if self.kind == "independent":
            if not self.by:
                raise ValueError("An independent-samples t-test needs `by`, the grouping variable.")
            columns = [self.column, self.by]
        elif self.kind == "paired":
            if not self.other:
                raise ValueError("A paired t-test needs `other`, the second measurement.")
            columns = [self.column, self.other]
        else:
            columns = [self.column]
        source, left_out = inference.without_missing_codes(
            self.data.frame, columns, self.data.variables
        )
        stats: dict[str, Any]
        if self.kind == "independent":
            rows, stats = self._independent(source)
        elif self.kind == "paired":
            rows, stats = self._paired(source)
        else:
            rows, stats = self._one_sample(source)
        first = _get_label(self.data, self.by) if self.kind == "independent" else "Variable"
        self._result = pd.DataFrame(rows, columns=[first, "N", "Mean", "SD", "SE"])
        stats.update(_missing_codes(self.data, left_out))
        if (note := _unweighted_note(self.data)) is not None:
            stats["Weight"] = note
        self._stats = stats

    # ── the three designs ──

    def _independent(self, source: pd.DataFrame) -> tuple[list[list[Any]], dict[str, Any]]:
        by = str(self.by)
        values = pd.to_numeric(source[self.column], errors="coerce")
        frame = pd.DataFrame({"y": values, "g": source[by]}).dropna()
        labels = _get_value_labels(self.data, by)
        present = sorted(frame["g"].unique().tolist(), key=_order)
        named = lambda code: str(labels.get(code, code))  # noqa: E731
        if self.groups:
            if len(self.groups) != 2:
                raise ValueError("groups names the two groups to compare: [first, second].")
            variable = self.data.variables.get(by) if self.data.variables is not None else None
            declared = list(variable.missing_values) if variable is not None else []
            for code in self.groups:
                for missing in declared:
                    if _code_text(missing) == _code_text(code):
                        label = variable.missing_labels.get(missing)
                        raise ValueError(
                            f"{_code_text(missing)}{f' ({label})' if label else ''} is a missing "
                            f"code of {_get_label(self.data, by)}, not a group — name two groups "
                            "that are answers."
                        )
            known = present + [code for code in labels if code not in present]
            chosen = [_find(code, known, by, labels) for code in self.groups]
        elif len(present) > 2:
            listed = ", ".join(f"{_code_text(code)} = {named(code)}" for code in present)
            raise ValueError(
                f"{_get_label(self.data, by)} has {len(present)} groups ({listed}); a t-test "
                "compares two — name them in Group A and Group B."
            )
        else:
            chosen = present
        samples = [frame.loc[frame["g"] == code, "y"].to_numpy(dtype=float) for code in chosen]
        names = [named(code) for code in chosen]
        rows = [_describe(name, sample) for name, sample in zip(names, samples, strict=True)]
        stats: dict[str, Any] = {}
        if len(samples) < 2:
            stats["Test"] = (
                f"not run: only one group of {_get_label(self.data, by)} has answers"
                if samples
                else "not run: no answers"
            )
        else:
            try:
                result = inference.ttest_independent(
                    samples[0],
                    samples[1],
                    equal_var=self.variances == "student",
                    confidence=self.confidence,
                    names=(names[0], names[1]),
                )
            except inference.NotTestable as exc:
                stats["Test"] = f"not run: {exc}"
            else:
                stats.update(self._result_stats(result, f"{names[0]} − {names[1]}"))
        stats["N"] = int(sum(len(sample) for sample in samples))
        stats["Variable"] = _get_label(self.data, self.column)
        return rows, stats

    def _paired(self, source: pd.DataFrame) -> tuple[list[list[Any]], dict[str, Any]]:
        other = str(self.other)
        x = pd.to_numeric(source[self.column], errors="coerce")
        y = pd.to_numeric(source[other], errors="coerce")
        complete = x.notna() & y.notna()
        answered = x.notna() | y.notna()
        x, y = x[complete].to_numpy(dtype=float), y[complete].to_numpy(dtype=float)
        first, second = _get_label(self.data, self.column), _get_label(self.data, other)
        rows = [_describe(first, x), _describe(second, y), _describe("Difference", x - y)]
        stats: dict[str, Any] = {}
        try:
            result = inference.ttest_paired(x, y, confidence=self.confidence)
        except inference.NotTestable as exc:
            stats["Test"] = f"not run: {exc}"
        else:
            stats.update(self._result_stats(result, f"{first} − {second}"))
        stats["N"] = int(complete.sum())
        incomplete = int((answered & ~complete).sum())
        if incomplete:
            stats["Incomplete pairs left out"] = incomplete
        return rows, stats

    def _one_sample(self, source: pd.DataFrame) -> tuple[list[list[Any]], dict[str, Any]]:
        x = pd.to_numeric(source[self.column], errors="coerce").dropna().to_numpy(dtype=float)
        rows = [_describe(_get_label(self.data, self.column), x)]
        stats: dict[str, Any]
        try:
            result = inference.ttest_one_sample(x, self.mu, confidence=self.confidence)
        except inference.NotTestable as exc:
            stats = {"Test": f"not run: {exc}"}
        else:
            stats = self._result_stats(result, f"mean − {self.mu:g}")
        stats = {"Test": stats.pop("Test"), "Test value": self.mu, **stats}
        stats["N"] = int(len(x))
        return rows, stats

    @staticmethod
    def _result_stats(result: inference.TTest, difference: str) -> dict[str, Any]:
        stats: dict[str, Any] = {
            "Test": result.method,
            "t": round(result.t, 3),
            "df": _df(result.df),
            "p": round(result.p_value, 4),
            "Mean difference": round(result.difference, 3),
            "Difference": difference,
            _ci_key(result.confidence): _interval(result.lower, result.upper),
        }
        if result.cohens_d is not None:
            key = "Cohen's d (d_z)" if result.kind == "paired" else "Cohen's d"
            stats[key] = round(result.cohens_d, 3)
        if result.hedges_g is not None:
            stats["Hedges' g"] = round(result.hedges_g, 3)
        return stats


def _order(code: Any) -> tuple[int, Any]:
    """Numbers before text, each in their own order — codes can be either."""

    return (0, code) if isinstance(code, int | float) else (1, str(code))


def _code_text(code: Any) -> str:
    """A code as the codebook writes it: 1, not the 1.0 a column with a blank holds."""

    if isinstance(code, float) and code.is_integer():
        return str(int(code))
    return str(code)


def _find(code: Any, known: list[Any], by: str, labels: dict[Any, str]) -> Any:
    """The group ``code`` names — a JSON 1 finds a code of 1.0, "1" finds 1."""

    for value in known:
        if value == code or _code_text(value) == _code_text(code):
            return value
    listed = ", ".join(f"{_code_text(value)} = {labels.get(value, value)}" for value in known)
    raise ValueError(f"{by!r} has no group {code!r}; its groups are {listed or 'none'}.")


def _describe(name: str, values: np.ndarray) -> list[Any]:
    n = int(len(values))
    mean = round(float(values.mean()), 3) if n else None
    sd = round(float(values.std(ddof=1)), 3) if n > 1 else None
    se = round(float(values.std(ddof=1)) / float(np.sqrt(n)), 3) if n > 1 else None
    return [name, n, mean, sd, se]


# ─── CorrelationMatrixTable ──────────────────────────────────────────────────

_METHOD_TITLES = {
    "pearson": "Pearson correlation",
    "spearman": "Spearman rank correlation",
    "kendall": "Kendall rank correlation (tau-b)",
}


@dataclass
class CorrelationMatrixTable(_BlankUndefined, SurveyTable):
    """Correlations between every pair of ``columns``.

    ``layout="matrix"`` is the table a report prints: the lower triangle of
    coefficients, each with its significance marks (* p < .05, ** p < .01,
    *** p < .001 — on the adjusted p when ``adjust`` is set), and N in the
    footer. ``layout="pairs"`` gives one row per pair with the coefficient, p,
    the adjusted p and N, which is what to read when N differs from pair to
    pair. ``result`` holds the numbers as square frames.

    ``missing`` is ``pairwise`` (each pair uses everyone who answered both) or
    ``listwise`` (only those who answered every variable). The codebook's
    missing codes are left out and counted. Pearson is weighted when the data
    is, with its p on Kish's effective base; the rank correlations have no
    standard weighted form and say so.
    """

    columns: list[str] = field(default_factory=list)
    method: str = "spearman"
    missing: str = "pairwise"
    adjust: str = "none"
    layout: str = "matrix"
    _matrix: Any = field(init=False, repr=False, default=None)

    @property
    def result(self) -> inference.CorrelationMatrix:
        """The numbers behind the table: coefficients, p, adjusted p and N."""
        self._ensure_built()
        return self._matrix

    def _build(self) -> None:
        if self.layout not in ("matrix", "pairs"):
            raise ValueError("layout must be 'matrix' or 'pairs'.")
        columns = list(dict.fromkeys(self.columns))
        source, left_out = inference.without_missing_codes(
            self.data.frame, columns, self.data.variables
        )
        weighted = self.data.weight is not None and self.method == "pearson"
        weights = _weights_of(self.data, source.index) if weighted else None
        result = inference.correlation_matrix(
            source,
            columns,
            method=self.method,
            missing=self.missing,
            adjust=self.adjust,
            weights=weights,
        )
        self._matrix = result
        labels = [_get_label(self.data, column) for column in columns]
        # Two variables may share a label (the same question asked twice); the
        # columns of the matrix may not.
        labels = [
            f"{label} ({column})" if labels.count(label) > 1 else label
            for label, column in zip(labels, columns, strict=True)
        ]
        adjusted = self.adjust != "none"
        p_marks = result.p_adjusted if adjusted else result.p_values
        symbol = inference.CORRELATION_SYMBOLS[self.method]
        if self.layout == "matrix":
            rows = []
            for i, a in enumerate(columns):
                row: dict[str, Any] = {"Variable": labels[i]}
                for j, b in enumerate(columns):
                    if j < i:
                        value = result.coefficients.loc[a, b]
                        row[labels[j]] = (
                            "n/a" if value != value else f"{value:.3f}{_marks(p_marks.loc[a, b])}"
                        )
                    elif j == i:
                        row[labels[j]] = "—"
                    else:
                        row[labels[j]] = ""
                rows.append(row)
            frame = pd.DataFrame(rows, columns=["Variable", *labels])
        else:
            pairs = result.pairs()
            frame = pd.DataFrame(
                {
                    "Variable 1": [labels[columns.index(name)] for name in pairs["x"]],
                    "Variable 2": [labels[columns.index(name)] for name in pairs["y"]],
                    symbol: [None if v != v else round(float(v), 3) for v in pairs["coefficient"]],
                    "p": [None if v != v else round(float(v), 4) for v in pairs["p_value"]],
                }
            )
            if adjusted:
                frame[f"p ({inference.ADJUSTMENT_NAMES[self.adjust]})"] = [
                    None if v != v else round(float(v), 4) for v in pairs["p_adjusted"]
                ]
            frame["N"] = pairs["n"].astype(int).tolist()
        self._result = frame

        upper = np.triu_indices(len(columns), 1)
        counts = result.n.to_numpy()[upper]
        stats: dict[str, Any] = {"Method": _METHOD_TITLES[self.method]}
        if self.missing == "pairwise":
            stats["Missing"] = "pairwise: each pair uses everyone who answered both"
            low, high = int(counts.min()), int(counts.max())
            stats["N"] = low if low == high else f"{low}–{high}"
        else:
            stats["Missing"] = "listwise: only respondents who answered every variable"
            stats["N"] = int(counts.min()) if len(counts) else 0
        pairs_count = len(counts)
        stats["p adjustment"] = (
            f"{inference.ADJUSTMENT_NAMES[self.adjust]}"
            + (" (false discovery rate)" if self.adjust == "fdr_bh" else "")
            + f", over {pairs_count} pairs"
            if adjusted
            else "none"
        )
        if self.layout == "matrix":
            stats["Marks"] = "* p < .05, ** p < .01, *** p < .001" + (
                " (adjusted p)" if adjusted else ""
            )
        if result.notes:
            stats["Not computed"] = "; ".join(result.notes)
        stats.update(_missing_codes(self.data, left_out))
        if weighted:
            stats["Weight"] = self.data.weight
            stats["Base"] = "weighted coefficients; p on Kish's effective base"
        elif (note := _unweighted_note(self.data)) is not None:
            stats["Weight"] = note
        self._stats = stats


def export_with_posthoc(table: SurveyTable, posthoc: PostHocTable | None, path: str | Path) -> Path:
    """Write ``table`` to an Excel file, with its post-hoc pairs on a second sheet."""

    table._ensure_built()
    path = Path(path)
    with pd.ExcelWriter(path) as writer:
        table._result.to_excel(writer, index=False, sheet_name="Table")
        if posthoc is not None:
            posthoc.to_frame().to_excel(writer, index=False, sheet_name="Post-hoc")
    return path


def render_with_posthoc(markdown_or_html: str, posthoc: PostHocTable | None, *, html: bool) -> str:
    """A table's rendering with its post-hoc pairs under it, when there are any."""

    if posthoc is None:
        return markdown_or_html
    return markdown_or_html + ("\n" + posthoc.to_html() if html else "\n\n" + posthoc.to_markdown())


__all__ = [
    "MEANS_TESTS",
    "TTEST_KINDS",
    "CorrelationMatrixTable",
    "PostHocTable",
    "TTestTable",
    "fisher_stats",
    "means_test",
    "posthoc_for",
]
