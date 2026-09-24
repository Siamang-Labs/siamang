# `siamang.data` — Data Analysis & Processing Reference

The `data` subpackage wraps a pandas DataFrame together with its `VariableMap` and exposes specialized accessors for cleaning, processing, analyzing, and visualizing survey data [1] [2].

```python
from siamang.data import SurveyData, SurveyTables, BannerTable
```

---

## `SurveyData`

The `SurveyData` class is the primary container for survey datasets. It binds a pandas DataFrame to a `VariableMap` and optionally a `Questionnaire` schema, enabling metadata-aware data operations.

```python
@dataclass(frozen=True, slots=True)
class SurveyData:
    frame: pd.DataFrame
    variables: VariableMap | None = None
    questionnaire: Questionnaire | None = None
    weight: str | None = None      # column name to use as the default weight
```

### Properties

| Property | Returns | Purpose |
| :--- | :--- | :--- |
| `analysis` | `DataAnalysis` | High-level descriptive and inferential statistics [1]. |
| `processing` | `DataProcessing` | Ad-hoc value-level transformations. |
| `tables` | `SurveyTables` | Complex multi-cell banner tables. |
| `report` | `ReportAccessor` | Declarative, metadata-aware table generation. |
| `plot` | `PlotAccessor` | Declarative, metadata-aware visualization generation [3]. |

### Immutable Updates

Since `SurveyData` is frozen and immutable, all data transformation methods return a new `SurveyData` instance containing the updated DataFrame and variables.

* **`with_frame(frame: pd.DataFrame) -> SurveyData`**:
  Returns a new instance with the underlying DataFrame replaced.
* **`with_weight(column: str | None) -> SurveyData`**:
  Sets the default weight column. Raises a `ValueError` if the specified column is not present in the DataFrame. See [What the weight reaches](#what-the-weight-reaches).

#### What the weight reaches

Once `with_weight()` is set (the flow's **Apply weight** node), a result either uses the weight and says so, or has no standard weighted form and says it is unweighted. A missing or non-numeric weight counts 0 everywhere.

| Result | With the weight |
| :--- | :--- |
| `report.freq`, `report.crosstab`, `report.means` | Weighted counts and percentages (an `Unweighted N` beside them), crosstab χ² on Kish's effective base; group means, SDs and medians weighted while N and the test are not. Stats: `Weight`. |
| `report.banner`, `report.nps`, `analysis.regression`, TURF | Weighted; tests and the NPS standard error on Kish's effective base; stats `Weight` (`weight` for regression). |
| `report.maxdiff`, `report.conjoint`, `report.conjoint_shares` and `siamang.data.maxdiff` / `conjoint` | Every column weighted: Shown/Best/Worst are sums of weights, Score, Utility, Share %, part-worths, importance and shares come from the weighted choices. Stats: `Weight` and a base of `N respondents (W weighted)`. |
| `analysis.pca`, `analysis.reliability` | The weighted covariance (or correlation) matrix; stats `weight`. |
| `analysis.proportion_ci` | Weighted only with `weighted=True` (then `weight`: the column); otherwise `weight`: `unweighted (the weight 'w' is not applied)`. |
| `analysis.kruskal`, `analysis.mannwhitney`, `analysis.spearman`, `cluster()` | Unweighted — rank tests and k-means have no standard weighted form. Their result has `weight`: `unweighted (the weight 'w' is not applied)`. |
| `report.quality`, `report.themes` | Count responses and answers. Stats: `Weight`: `unweighted (the weight 'w' is not applied)`. |
| `describe_variables()` | Counts rows, and adds `weighted_n_valid`, the weights of the rows with a value. |
| `plot.bar`, `plot.heatmap(by=…)` | Weighted counts and weighted means; the axis (or colour bar) says "Weighted". |
| `plot.boxplot`, `plot.scatter`, `plot.heatmap()` without `by` | Unweighted; the title's second line reads `unweighted (the weight 'w' is not applied)`. |
| The HB exports (`siamang.io.choice`) | The files carry no weight column (the R packages take none); weight the individual utilities when you aggregate them. |

Weighted conditional-logit fits (MaxDiff, conjoint) rescale the weights to sum to Kish's effective number of choice sets before fitting: the estimates are those of the weighted likelihood, and the standard errors are those of the effective base rather than of the raw sample or of a population-sized total.

### Inspection and Validation

* **`codebook() -> pd.DataFrame`**:
  Generates a comprehensive codebook DataFrame containing metadata (`name`, `scale`, `label`, `labels`, `missing_values`) for all registered variables. Raises a `ValueError` if `variables` is unset.
* **`describe_variables() -> pd.DataFrame`**:
  Generates a summary table containing the number of rows (`n`), missing responses (`n_missing`), and unique values (`n_unique`) for each variable. On weighted data a `weighted_n_valid` column adds the sum of the weights of the rows that have a value — the weighted base a table of that variable reports.
* **`validate(raise_on_error: bool = False) -> list[ValidationIssue]`**:
  Validates the underlying DataFrame against the `VariableMap` schema. It checks column presence, data types, value ranges, category labels, and weight constraints. Raises a `ValueError` if `raise_on_error=True` and issues are found.

### Missing-Value Handling

* **`apply_missing_values(kinds: set[str] | None = None) -> SurveyData`**:
  Replaces all user-defined missing value codes (e.g., `99` for refusal) with `pd.NA` in the DataFrame. If `kinds` is specified (e.g., `{"refusal", "dont_know"}`), only missing values matching those classifications are replaced.
* **`drop_missing(column: str) -> SurveyData`**:
  Returns a new instance with rows removed where the specified column is missing (`NaN` or `pd.NA`).

### Recoding and Derivations

* **`recode(column: str, *, into: str, bins: list[Any], labels: list[str] | None = None, right: bool = False, label: str | None = None) -> SurveyData`**:
  Bins continuous numerical variables into discrete categories using `pandas.cut` [2]. Automatically registers the new variable in the `VariableMap` with an `"ordinal"` scale.
* **`recode_values(column: str, mapping: dict[Any, Any], *, into: str | None = None, label: str | None = None, scale: str | None = None) -> SurveyData`**:
  Collapses or remaps discrete values (e.g., `{1: 0, 2: 0, 3: 1}` to collapse categories). The source column is never modified: if `into` is provided, the result is stored in that new column; otherwise it is stored in a new column named `<column>_recoded`. The new variable is registered either way. Values absent from `mapping` become `NaN`, so list every code you want to keep.
* **`derive(*, name: str, expression: Expression, label: str | None = None, scale: str = "nominal", labels: dict[Any, str] | None = None) -> SurveyData`**:
  Evaluates a logical `Expression` row-by-row to create a new binary indicator variable (0/1). Registers the new variable with the specified metadata.
* **`derive_formula(name: str, formula: str, *, label: str | None = None, scale: str = "ratio", labels: dict[Any, str] | None = None) -> SurveyData`**:
  A new variable computed by arithmetic rather than by a condition: `"round(spend_year / 12, 2)"`, `"if age < 30 then 1 else 2"`. The formula is text, parsed by `siamang.data.formula` and evaluated in one vectorized pass; nothing is executed. The label defaults to the formula itself, so the codebook says how the number was made and carries that into every export's dictionary. Registers the new variable with the `"derived"` role.

#### The formula language (`siamang.data.formula`)

`parse(text) -> Formula` reads a formula and raises `FormulaError` — carrying the
character reading stopped at — when it cannot. `Formula.variables()` lists the
variables it names, so it can be checked against a codebook before anything runs;
`Formula.evaluate(frame)` computes it.

```
expr    := ifexpr | orexpr
ifexpr  := 'if' orexpr 'then' expr 'else' expr
orexpr  := andexpr ('or' andexpr)*
andexpr := notexpr ('and' notexpr)*
notexpr := 'not' notexpr | compare
compare := sum (('='|'!='|'>'|'>='|'<'|'<=') sum)?
sum     := term (('+'|'-') term)*
term    := unary (('*'|'/') unary)*
unary   := '-' unary | atom
atom    := number | name | func '(' expr (',' expr)* ')' | '(' expr ')'
func    := mean | sum | min | max | abs | round | log | coalesce
```

`mean`, `sum`, `min`, `max` and `coalesce` work across their arguments, row by
row. `round`'s digits and `log`'s base have to be plain numbers, not variables.

Two behaviors are deliberate and worth knowing before you read a result:

* **Missing stays missing.** A respondent who skipped a question has no value,
  and arithmetic on it has none either. Dividing by zero gives missing rather
  than infinity — an infinity reads as a number all the way into a report, where
  it takes the mean with it — and so does `log` of a non-positive number. Write
  `coalesce(x, 0)` when you mean "treat a blank as zero".
* **A column of words is refused by name** rather than coerced into a column of
  `NaN`, which would look exactly like a question nobody answered. Recode it
  (`recode_values`) or explode it (`prepare.explode`) first.

The comparison and logical operators mean what they mean in a questionnaire
condition (`siamang.core.expression`). `contains` is the one that does not
appear: it asks about a multiple answer, and a formula works on numbers.

### Composite Measures

* **`scale_alpha(items: list[str]) -> float`**:
  Calculates Cronbach's alpha coefficient of internal consistency for a set of scale items. Requires at least 2 items.
* **`create_index(name: str, *, items: list[str], method: str = "mean", label: str | None = None) -> SurveyData`**:
  Creates a composite index variable (e.g., an index of autonomy) by aggregating a list of items. Supported aggregation methods: `"mean"` (default) or `"sum"` (row-wise sum with `min_count=1`, so a row with all items missing stays `NaN`). Automatically registers the new variable with an `"interval"` scale.

### Export

* **`export(fmt: str, path: str | Path | None = None, **kwargs) -> Any`**:
  Exports the dataset and its metadata. Supported formats: `"csv"`, `"xlsx"` (alias `"excel"`), `"spss"` (alias `"sav"`), `"stata"` (alias `"dta"` — a native `.dta` file with embedded variable and value labels), and `"r"` (a CSV, a JSON dictionary, and an R script to load the data with correct factor levels) [2]. An unknown format raises `NotImplementedError`.
* **`export_dictionary(path: str | Path) -> Path`**:
  Exports the `VariableMap` metadata to a standardized JSON schema file.

---

## `DataAnalysis`

The `DataAnalysis` class provides high-level statistical methods. It is accessed via the `data.analysis` property.

```python
@dataclass(frozen=True, slots=True)
class DataAnalysis:
    frame: pd.DataFrame
    weight_column: str | None = None
    variables: VariableMap | None = None
```

### Descriptives

* **`mean(column: str, weighted: bool = False) -> float`**:
  Calculates the mean. If `weighted=True`, uses the default weight column [1].
* **`median(column: str) -> float`**:
  Calculates the median value.
* **`grouped_mean(column: str, by: str, weighted: bool = False, labels: bool = False) -> pd.DataFrame`**:
  Calculates the mean of `column` grouped by categories of `by`. Returns a DataFrame with `group`, `mean`, and `n` columns. If `labels=True`, replaces category codes with their textual labels.

### Tables

* **`frequencies(column: str, normalize: bool = False, weighted: bool = False, labels: bool = False) -> pd.Series | pd.DataFrame`**:
  Generates a frequency distribution. If `normalize=True`, returns percentages instead of absolute counts. If `labels=True`, returns a DataFrame with category labels included.
* **`crosstab(row: str, col: str, normalize: str | bool = False, chi2: bool = False, cramers_v: bool = False, phi: bool = False, weighted: bool = False, labels: bool = False) -> pd.DataFrame | tuple[pd.DataFrame, dict[str, Any]]`**:
  Generates a two-way contingency table. `normalize` accepts `"index"` (row percentages), `"columns"` (column percentages), `"all"` (total percentages), or `False`. If any test flags (`chi2`, `cramers_v`, `phi`) are `True`, returns a tuple containing the contingency table and a dictionary of test results [1].

### Inferential Tests

These methods require `scipy` to be installed.

* **`kruskal(column: str, group: str) -> dict[str, Any]`**:
  Performs a Kruskal-Wallis H-test for independent samples. Returns a dictionary with `"statistic"`, `"p_value"` and `"groups"`.
* **`mannwhitney(column: str, group: str) -> dict[str, Any]`**:
  Performs a Mann-Whitney U-test for two independent samples. Returns a dictionary with `"statistic"`, `"p_value"`, `"group_a"`, and `"group_b"`.
* **`spearman(x: str, y: str) -> dict[str, Any]`**:
  Calculates Spearman's rank correlation coefficient. Returns a dictionary with `"rho"`, `"p_value"`, and `"n"`.

The three rank tests have no standard weighted form, so they run on the respondents as they are. On weighted data each result also carries `"weight": "unweighted (the weight '<column>' is not applied)"`.

### Models

* **`regression(y: str, predictors: list[str], *, kind: str = "auto")`**: OLS, or a logit for a two-valued outcome; weighted (WLS / weighted logit) when the data is, with `stats["weight"]` naming the column.
* **`pca(items: list[str], *, n_components: int | None = None, standardize: bool = True)`**: loadings and explained variance. On weighted data the components are those of the weighted covariance (standardized: correlation) matrix, `Σ pᵢ (xᵢ − m)(xᵢ − m)ᵀ / (1 − Σ pᵢ²)` with `pᵢ = wᵢ / Σw` — R's `cov.wt` — so equal weights give the unweighted result exactly. `stats["n"]` stays the rows analyzed; `stats["weight"]` names the column.
* **`reliability(items: list[str])`**: Cronbach's alpha, item means, item–total correlations and alpha if deleted — all from the same weighted moments on weighted data, with `stats["weight"]`.
* `SurveyData.cluster(items, *, k, into, seed, standardize)` is k-means on the respondents as they are; on weighted data `stats["weight"]` says the weight is not applied. A Frequencies table of the cluster variable on the weighted data gives the segments' weighted sizes.

### Confidence Intervals & Sample Size

* **`proportion_ci(column: str, value: Any, confidence: float = 0.95, weighted: bool = False) -> dict[str, Any]`**:
  Calculates a normal-approximation confidence interval for a specific category proportion. Returns `"p"`, `"lower"`, `"upper"`, and `"n"` (Kish's effective base when `weighted=True`). A weighted result adds `"weight"` (the column); an unweighted one on weighted data adds `"weight": "unweighted (the weight '<column>' is not applied)"`.
* **`effective_sample_size() -> float`**:
  Calculates Kish's effective sample size (ESS) for weighted datasets: $ESS = \frac{(\sum w)^2}{\sum w^2}$. Raises a `ValueError` if no weight column is set.

---

## `DataProcessing`

A thin, low-level utility wrapper accessed via `data.processing` for ad-hoc value transformations.

```python
@dataclass(frozen=True, slots=True)
class DataProcessing:
    frame: pd.DataFrame
```

* **`recode(column: str, mapping: dict[Any, Any]) -> SurveyData`**:
  Applies a raw `{old: new}` mapping via `pandas.replace` and returns a new `SurveyData` carrying only the recoded frame — the `VariableMap`, questionnaire, and weight are dropped. Use it only when the metadata is no longer needed; for research-grade, metadata-aware recoding, prefer `SurveyData.recode_values()`.

---

## `SurveyTables`

The `SurveyTables` class generates complex, publication-ready banner tables (cross-tabulating multiple row variables against multiple column variables simultaneously) [1]. It is accessed via `data.tables`.

```python
@dataclass(frozen=True, slots=True)
class SurveyTables:
    frame: pd.DataFrame
    variables: VariableMap | None = None
    weight_column: str | None = None
```

* **`banner(rows: list[str], columns: list[str], weight: str | None = None, labels: bool = True) -> BannerTable`**:
  Generates a banner table cross-tabulating all `rows` variables against all `columns` variables. If `labels=True`, uses variable and value labels for headers.

---

### `BannerTable`

An immutable container representing a compiled banner table in **tidy** form —
one row per (row value × column value), ready for export or for feeding to
something else. For the wide cross-break a person reads, with blocks of columns,
a base row and significance letters, use `data.report.banner(...)`
(`siamang.reporting.tables.BannerTable`); it computes its numbers with the same
helper, so the two cannot disagree.

```python
@dataclass(frozen=True, slots=True)
class BannerTable:
    frame: pd.DataFrame
```

#### Methods

* **`export_csv(path: str | Path, **pandas_kwargs) -> Path`**:
  Exports the banner table to a CSV file.
* **`export_xlsx(path: str | Path, **pandas_kwargs) -> Path`**:
  Exports the banner table to an Excel spreadsheet, automatically creating parent directories.

---

## Pipeline helpers: `respondents`, `weights`, `stats`

Three modules of plain pandas functions for the cleaning and weighting steps
that sit between "responses arrived" and "tables". They take and return
frames or Series, so they combine with `SurveyData.with_frame(...)` and work
on data from any source.

```python
from siamang.data import respondents, weights, stats

frame = data.frame
frame = respondents.dedup_responses(frame, id_col="respondent_id", keep="last")
frame["duration_s"] = respondents.completion_time(frame)
frame["partial"] = respondents.partial_flag(frame, required=["age", "region"])
frame = frame[~respondents.speeders(frame, min_seconds=90) & ~frame["partial"]]
frame["weight"] = weights.rake_weights(frame, {"region": {1: 0.45, 2: 0.30, 3: 0.25}})
clean = data.with_frame(frame).with_weight("weight")
```

### `siamang.data.respondents`

| Function | Returns | Notes |
|----------|---------|-------|
| `dedup_responses(df, *, id_col="respondent_id", order_by="submitted_at", keep="last")` | frame | One row per respondent; anonymous rows (null/blank id) are always kept; original order restored. |
| `completion_time(df, *, start_col="started_at", end_col="submitted_at", duration_col="duration_s")` | Series (seconds) | Uses `duration_col` when present, else end − start. |
| `partial_flag(df, required)` | bool Series | `True` where any required column is null/blank; a missing column flags every row. |
| `speeders(df, *, min_seconds, duration=None)` | bool Series | `True` under `min_seconds`; unknown durations are never flagged. |

### `siamang.data.weights`

| Function | Returns | Notes |
|----------|---------|-------|
| `cell_weights(df, column, targets, *, cap=None)` | Series, mean 1 | Post-stratification on one variable. Targets are proportions or counts. |
| `rake_weights(df, targets, *, max_iter=50, tol=1e-6, cap=None)` | Series, mean 1 | Iterative proportional fitting to several margins: `{"region": {1: .45, …}, "gender": {…}}`. |
| `effective_sample_size(weights)` | float | Kish's `(Σw)² / Σw²`. |

`cap` bounds the weights from above (after scaling to mean 1); capped rows are
then under-represented, so the fit to the targets becomes approximate.

### `siamang.data.stats`

Tidy-frame descriptives for scripts that do not go through `SurveyData`:

| Function | Returns |
|----------|---------|
| `frequencies(df, column, *, weight=None, dropna=True)` | `value` / `count` / `percent` rows |
| `crosstab(df, row, col, *, weight=None, normalize=None)` | two-way table; percentages when `normalize` is set |
| `chi2(df, a, b)` | `{"chi2", "dof", "p", "cramers_v", "n"}` |

---

## References

1. Agresti, Alan. *An Introduction to Categorical Data Analysis*. Wiley, 3rd edition, 2018.
2. McKinney, Wes. *Python for Data Analysis: Data Wrangling with pandas, NumPy, and Jupyter*. O'Reilly Media, 3rd edition, 2022.
3. Wickham, Hadley. *ggplot2: Elegant Graphics for Data Analysis*. Springer, 2nd edition, 2016.
