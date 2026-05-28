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
  Sets the default weight column. Raises a `ValueError` if the specified column is not present in the DataFrame.

### Inspection and Validation

* **`codebook() -> pd.DataFrame`**:
  Generates a comprehensive codebook DataFrame containing metadata (`name`, `scale`, `label`, `labels`, `missing_values`) for all registered variables. Raises a `ValueError` if `variables` is unset.
* **`describe_variables() -> pd.DataFrame`**:
  Generates a summary table containing the number of valid responses (`n`), missing responses (`n_missing`), and unique values (`n_unique`) for each variable.
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
  Collapses or remaps discrete values (e.g., `{1: 0, 2: 0, 3: 1}` to collapse categories). If `into` is provided, stores the result in a new column and registers the new variable; otherwise, updates the column in-place.
* **`derive(*, name: str, expression: Expression, label: str | None = None, scale: str = "nominal", labels: dict[Any, str] | None = None) -> SurveyData`**:
  Evaluates a logical `Expression` row-by-row to create a new binary indicator variable (0/1). Registers the new variable with the specified metadata.

### Composite Measures

* **`scale_alpha(items: list[str]) -> float`**:
  Calculates Cronbach's alpha coefficient of internal consistency for a set of scale items. Requires at least 2 items.
* **`create_index(name: str, *, items: list[str], method: str = "mean", label: str | None = None) -> SurveyData`**:
  Creates a composite index variable (e.g., an index of autonomy) by aggregating a list of items. Supported aggregation methods: `"mean"` or `"sum"`. Automatically registers the new variable with an `"interval"` scale.

### Export

* **`export(fmt: str, path: str | Path | None = None, **kwargs) -> Any`**:
  Exports the dataset and its metadata. Supported formats: `"csv"`, `"xlsx"`, `"stata"` (exports a native `.dta` file with embedded variable and value labels), and `"r"` (exports a CSV, a JSON dictionary, and an R script to load the data with correct factor levels) [2].
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

* **`kruskal(column: str, group: str) -> dict[str, float]`**:
  Performs a Kruskal-Wallis H-test for independent samples. Returns a dictionary with `"statistic"` and `"pvalue"`.
* **`mannwhitney(column: str, group: str) -> dict[str, float]`**:
  Performs a Mann-Whitney U-test for two independent samples. Returns a dictionary with `"statistic"`, `"pvalue"`, `"n1"`, and `"n2"`.
* **`spearman(x: str, y: str) -> dict[str, float]`**:
  Calculates Spearman's rank correlation coefficient. Returns a dictionary with `"rho"`, `"pvalue"`, and `"n"`.

### Confidence Intervals & Sample Size

* **`proportion_ci(column: str, value: Any, confidence: float = 0.95, weighted: bool = False) -> dict[str, float]`**:
  Calculates a binomial confidence interval for a specific category proportion. Returns `"proportion"`, `"ci_low"`, `"ci_high"`, and `"n"`.
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
  Applies a raw `{old: new}` mapping to a column in-place. For research-grade, metadata-aware recoding, prefer `SurveyData.recode_values()`.

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

An immutable container representing a compiled banner table, ready for export.

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

## References

1. Agresti, Alan. *An Introduction to Categorical Data Analysis*. Wiley, 3rd edition, 2018.
2. McKinney, Wes. *Python for Data Analysis: Data Wrangling with pandas, NumPy, and Jupyter*. O'Reilly Media, 3rd edition, 2022.
3. Wickham, Hadley. *ggplot2: Elegant Graphics for Data Analysis*. Springer, 2nd edition, 2016.
