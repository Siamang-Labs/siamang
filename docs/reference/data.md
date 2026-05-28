# `siamang.data` — analysis layer reference

The `data` subpackage wraps a pandas DataFrame together with its
`VariableMap` and exposes three accessors:

- `SurveyData.analysis` (`DataAnalysis`) — descriptive and inferential
  statistics
- `SurveyData.processing` (`DataProcessing`) — value-level transforms
- `SurveyData.tables` (`SurveyTables`) — multi-cell / banner tables

```python
from siamang.data import SurveyData, SurveyTables, BannerTable
```

---

## `SurveyData`

```python
@dataclass(frozen=True, slots=True)
class SurveyData:
    frame: pd.DataFrame
    variables: VariableMap | None = None
    questionnaire: Questionnaire | None = None
    weight: str | None = None      # column name to use as the default weight
```

The aggregate object. Construct it explicitly, or get one back from
`questionnaire.simulate()`, `DeployResult.collect()`, or any reader in
`siamang.io`.

### Properties

| Property | Returns | Purpose |
|----------|---------|---------|
| `analysis` | `DataAnalysis` | Frequencies, crosstabs, descriptives, tests, CIs |
| `processing` | `DataProcessing` | Lightweight value-level transforms |
| `tables` | `SurveyTables` | Banner tables |

### Immutable updates

`SurveyData` is frozen — every transform returns a new instance.

| Method | Returns | Behaviour |
|--------|---------|-----------|
| `with_frame(frame)` | `SurveyData` | Replace the underlying DataFrame. |
| `with_weight(column)` | `SurveyData` | Set the default weight column. Raises `ValueError` if the column is missing. |

### Inspection

| Method | Returns |
|--------|---------|
| `codebook()` | `DataFrame` (`name`, `scale`, `label`, `labels`, `missing_values`, …) — raises `ValueError` if `variables` is unset. |
| `describe_variables()` | `DataFrame` with `n`, `n_missing`, `n_unique` per variable. |
| `validate(raise_on_error=False)` | `list[ValidationIssue]` — same checks as `VariableMap.validate_frame`, plus weight column type checks and questionnaire/frame consistency. |

### Missing-value handling

```python
data.apply_missing_values()                            # all configured codes → pd.NA
data.apply_missing_values(kinds={"refusal", "dont_know"})  # only those kinds
```

`apply_missing_values(kinds=None)` returns a new `SurveyData` whose
DataFrame has every configured missing code (or a filtered subset by
`MissingValue.kind`) replaced with `pd.NA`. Raises `ValueError` if
`variables` is not set.

`drop_missing(column)` — return a new `SurveyData` with all rows where
`column` is `NaN` removed.

### Recoding and derived variables

```python
# Bin a numeric column into categories
data = data.recode(
    "age",
    into="age_group",
    bins=[18, 30, 45, 65, 99],
    labels=["18-29", "30-44", "45-64", "65+"],
    right=False,
    label="Age group",
)

# Remap discrete values
data = data.recode_values(
    "education",
    {1: 0, 2: 0, 3: 1, 4: 1, 5: 1},     # collapse to "no college"/"college"
    into="college",
    label="College education",
    scale="nominal",
)

# Boolean derived variable from an expression
data = data.derive(
    name="adult_woman",
    expression=age.ge(18) & gender.eq(2),
    label="Adult woman",
    labels={0: "No", 1: "Yes"},
)
```

| Method | Returns | Notes |
|--------|---------|-------|
| `recode(column, *, into, bins, labels=None, right=False, label=None)` | `SurveyData` | Numeric binning via `pandas.cut`. Validates that `len(labels) == len(bins) - 1` when provided. |
| `recode_values(column, mapping, *, into=None, label=None, scale=None)` | `SurveyData` | Apply a `{old: new}` mapping. When `into` is provided, the original column is kept and a new variable is added. |
| `derive(*, name, expression, label=None, scale="nominal", labels=None)` | `SurveyData` | Evaluate an `Expression` row-by-row and store the result (0/1 by default) in `name`. |

### Composite measures

| Method | Returns | Notes |
|--------|---------|-------|
| `scale_alpha(items: list[str])` | `float` | Cronbach's α (requires ≥ 2 items). |
| `create_index(name, *, items, method="mean", label=None)` | `SurveyData` | Methods: `"mean"`, `"sum"`. Raises `ValueError` for any other method or empty `items`. |

### Export

```python
data.export("csv",   path="out.csv")
data.export("xlsx",  path="out.xlsx")
data.export("spss",  path="out.sav")        # SPSS .sav with full metadata
data.export("stata", path="out.dta")        # Stata .dta with full metadata
data.export("r",     path="out_R/")         # CSV + JSON dict + .R loader
data.export_dictionary("dict.json")         # VariableMap → JSON
```

`export(fmt, path=None, **kwargs)` is a thin dispatcher to the
corresponding writer in `siamang.io`. Unknown `fmt` raises
`NotImplementedError`.

---

## `DataAnalysis`

```python
@dataclass(frozen=True, slots=True)
class DataAnalysis:
    frame: pd.DataFrame
    weight_column: str | None = None
    variables: VariableMap | None = None
```

Accessed via `data.analysis`. Methods that say "weighted" use
`weight_column`; methods that take a `weighted=` flag default to
unweighted.

### Descriptives

| Method | Returns |
|--------|---------|
| `mean(column, weighted=False)` | `float` (`0.0` when empty / weight sum non-positive). |
| `median(column)` | `float`. |
| `grouped_mean(column, by, weighted=False, labels=False)` | `DataFrame` columns: `group`, `mean`, `n`, plus `label` when `labels=True`. |

### Tables

```python
data.analysis.frequencies("party", labels=True, weighted=True)
data.analysis.crosstab("gender", "party", normalize="columns", chi2=True, cramers_v=True)
```

| Method | Returns | Notes |
|--------|---------|-------|
| `frequencies(column, normalize=False, weighted=False, labels=False)` | `Series` (counts/percentages) or `DataFrame` when `labels=True`. |
| `crosstab(row, col, normalize=False, chi2=False, cramers_v=False, phi=False, weighted=False, labels=False)` | `DataFrame`, or `(DataFrame, dict)` when any test flag is set. `normalize` ∈ `{False, True, "index", "columns", "all"}`. `phi` requires a 2×2 table. |

### Inferential tests

These require `scipy` (installed by default with `pip install siamang`) and raise
`ImportError` if unavailable.

| Method | Returns |
|--------|---------|
| `kruskal(column, group)` | `{"statistic", "pvalue"}` — Kruskal-Wallis test. Raises `ValueError` if fewer than two groups. |
| `mannwhitney(column, group)` | `{"statistic", "pvalue", "n1", "n2"}` — Mann-Whitney U test. Requires exactly two groups. |
| `spearman(x, y)` | `{"rho", "pvalue", "n"}` — rank correlation (uses pandas fallback if scipy missing). |

### Confidence intervals & effective sample size

| Method | Returns |
|--------|---------|
| `proportion_ci(column, value, confidence=0.95, weighted=False)` | `{"proportion", "ci_low", "ci_high", "n"}`. `confidence` must be in `(0, 1)`. |
| `effective_sample_size()` | `float`. Raises `ValueError` if `weight_column` is unset (Kish's ESS = `(Σw)² / Σw²`). |

---

## `DataProcessing`

```python
@dataclass(frozen=True, slots=True)
class DataProcessing:
    frame: pd.DataFrame
```

A thin wrapper that returns new `SurveyData` instances; mainly used for
ad-hoc explorations.

| Method | Returns | Behaviour |
|--------|---------|-----------|
| `recode(column, mapping)` | `SurveyData` | Apply `mapping` to `column` in place (in a new frame). |

For research-grade transforms with metadata, prefer
`SurveyData.recode_values()` / `.derive()`.

---

## `SurveyTables`

```python
@dataclass(frozen=True, slots=True)
class SurveyTables:
    frame: pd.DataFrame
    variables: VariableMap | None = None
    weight_column: str | None = None
```

Accessed via `data.tables`. Builds banner-style cross-tabulations
suitable for export.

```python
banner = data.tables.banner(
    rows=["trust", "trust_local"],
    columns=["gender", "region"],
    weight="weight_v2",          # overrides the default weight column
    labels=True,                  # use Variable.labels for human-readable headers
)
banner.export_xlsx("results.xlsx")
```

| Method | Returns | Raises |
|--------|---------|--------|
| `banner(rows, columns, weight=None, labels=True)` | `BannerTable` | `ValueError` if `rows` or `columns` is empty, or if `weight` is set but not present in the frame. |

### `BannerTable`

```python
@dataclass(frozen=True, slots=True)
class BannerTable:
    frame: pd.DataFrame
```

| Method | Returns |
|--------|---------|
| `export_csv(path, **pandas_kwargs)` | `Path` (creates parent directories) |
| `export_xlsx(path, **pandas_kwargs)` | `Path` (creates parent directories) |
