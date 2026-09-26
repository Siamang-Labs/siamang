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
| `report.freq`, `report.crosstab`, `report.means` | Weighted counts and percentages (an `Unweighted N` beside them), crosstab χ² on Kish's effective base (Fisher's exact test counts respondents and says so in `Base`); group means, SDs and medians weighted while N, the test and the post-hoc pairs are not. Stats: `Weight`. |
| `analysis.correlation`, `report.correlation_matrix` with Pearson | The weighted coefficient; p and the Fisher-z interval on Kish's effective base (`n_effective`). Stats: `weight` / `Weight` (the column). |
| `report.banner`, `report.nps`, `analysis.regression`, TURF | Weighted; tests and the NPS standard error on Kish's effective base; stats `Weight` (`weight` for regression). The logit and the ordinal logit take the weights as frequencies in the likelihood (the ordinal model's `weights` says what they sum to when they do not average about 1). |
| `report.maxdiff`, `report.conjoint`, `report.conjoint_shares` and `siamang.data.maxdiff` / `conjoint` | Every column weighted: Shown/Best/Worst are sums of weights, Score, Utility, Share %, part-worths, importance and shares come from the weighted choices. Stats: `Weight` and a base of `N respondents (W weighted)`. |
| `analysis.pca`, `analysis.reliability` | The weighted covariance (or correlation) matrix; stats `weight`. |
| `analysis.proportion_ci` | Weighted only with `weighted=True` (then `weight`: the column); otherwise `weight`: `unweighted (the weight 'w' is not applied)`. |
| `analysis.kruskal`, `analysis.mannwhitney`, `analysis.spearman`, `analysis.compare_groups`, `analysis.correlation` / `report.correlation_matrix` with Spearman or Kendall, `report.ttest`, `cluster()` | Unweighted — rank tests, t-tests and k-means have no standard weighted form. Their result has `weight` (the tables: `Weight`): `unweighted (the weight 'w' is not applied)`. |
| `siamang.data.paired` (Wilcoxon, McNemar, Friedman), `siamang.data.factor` | Unweighted — no standard weighted form. Stats: `Weight`: `unweighted (the weight 'w' is not applied)`. |
| `report.quality`, `report.themes` | Count responses and answers. Stats: `Weight`: `unweighted (the weight 'w' is not applied)`. |
| `describe_variables()` | Counts rows, and adds `weighted_n_valid`, the weights of the rows with a value. |
| `plot.bar`, `plot.heatmap(by=…)` | Weighted counts, percentages (also with `split`) and weighted means; the axis (or colour bar) says "Weighted" or "(weighted)". |
| `plot.heatmap(method="pearson")` without `by` | Weighted Pearson coefficients (colour bar "Weighted Pearson r"), as `report.correlation_matrix` weights them. |
| `plot.likert` | Weighted shares of each answer ("% of respondents (weighted)"); `n` counts respondents. |
| `plot.boxplot`, `plot.scatter`, `plot.heatmap()` without `by` (Spearman, Kendall) | Unweighted; the title's second line reads `unweighted (the weight 'w' is not applied)`. |
| The HB exports (`siamang.io.choice`) | The files carry no weight column (the R packages take none); weight the individual utilities when you aggregate them. |
| `report.descriptives` / `siamang.data.descriptives` | Mean, SD, median and quartiles weighted (the `GroupMeanTable`'s formulas) beside a `Weighted N` column; N, Missing, skewness and kurtosis are not. Stats: `Weight`, `Weighted N`, `Effective N`, `Design effect`, `Note`. |
| `report.data_check`, `maxdiff.with_scores`, `bands.bands` | Count rows (the scores are per respondent). Stats: `Weight`: `unweighted (the weight 'w' is not applied)`. |
| `turf.turf` / `turf.evaluate` | Reach is a sum of weights and the frequency a weighted mean. |

Weighted conditional-logit fits (MaxDiff, conjoint) rescale the weights to sum to Kish's effective number of choice sets before fitting: the estimates are those of the weighted likelihood, and the standard errors are those of the effective base rather than of the raw sample or of a population-sized total.

### Inspection and Validation

* **`codebook() -> pd.DataFrame`**:
  Generates a comprehensive codebook DataFrame containing metadata (`name`, `scale`, `label`, `labels`, `missing_values`) for all registered variables. Raises a `ValueError` if `variables` is unset.
* **`describe_variables() -> pd.DataFrame`**:
  Generates a summary table containing the number of rows (`n`), missing responses (`n_missing`), and unique values (`n_unique`) for each variable. On weighted data a `weighted_n_valid` column adds the sum of the weights of the rows that have a value — the weighted base a table of that variable reports.
* **`validate(raise_on_error: bool = False) -> list[ValidationIssue]`**:
  Validates the underlying DataFrame against the `VariableMap` schema. It checks column presence, data types, value ranges, category labels, and weight constraints. Raises a `ValueError` if `raise_on_error=True` and issues are found.
  `siamang.data.checks.check(data, variables=None)` (and `data.report.data_check`) returns the same issues as a table — `Severity`, `Variable`, `Problem`, `Rows`, `Examples` (`"7 (12), 8 (1)"`), `Code`, errors first — with the file-level problems (`EXTRA_COLUMN`, `MISSING_COLUMN`) gathered into one row each and `stats` `Checked`, `Errors`, `Warnings` (and `Result: no problems found`). The weight column and the response metadata (`METADATA_COLUMNS` — `id`, `survey_id`, `respondent_id`, `created_at`, `updated_at`, `started_at`, `submitted_at`, `duration_s`, `partial`, `__status`, `captcha`, `tab_switches`, `hidden_seconds`, `pastes` — and `url_*`) are not `EXTRA_COLUMN`s; `stats["Not in the codebook, as expected"]` names them (`"weight (the weight); duration_s, partial, respondent_id (response metadata)"`).

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

#### A method chosen by hand

These two compute with [`siamang.data.inference`](#siamangdatainference) and, unlike the three above, leave the codebook's declared missing codes out of both variables, reporting what they left out as `"missing_codes"` (`"Satisfaction: 12 (99 = Don't know)"`).

* **`correlation(x: str, y: str, *, method: str = "pearson", confidence: float = 0.95) -> dict[str, Any]`**:
  Pearson, Spearman or Kendall tau-b. Returns `"method"`, the coefficient (`"r"`, `"rho"` or `"tau"`), `"p_value"` and `"n"`; Pearson adds a Fisher-z interval `"lower"` / `"upper"` and `"confidence"`. On weighted data Pearson is the weighted coefficient with p and interval on Kish's effective base (`"n_effective"`) and `"weight"` names the column; the rank methods carry the unweighted note. Pairs that cannot carry a correlation (fewer than three, or a variable that does not vary) give `None` and a `"note"` saying why.
* **`compare_groups(column: str, group: str, *, test: str = "auto", posthoc: str = "none", adjust: str = "holm") -> dict[str, Any]`**:
  Mann-Whitney (`test="mannwhitney"`, or `"auto"` with two groups) or Kruskal-Wallis, with the keys of `mannwhitney` / `kruskal` plus `"test"` and `"n"`. With `posthoc="dunn"` after Kruskal-Wallis it adds `"posthoc"` (`"Dunn's test (Holm)"`) and one entry per pair of groups keyed `"<label> vs <label>"`: `"z = 2.087, p = 0.1106"`, p adjusted by `adjust` (`"holm"` or `"bonferroni"`). With two groups `"posthoc"` says no post-hoc test is needed.

### Models

* **`regression(y: str, predictors: list[str], *, kind: str = "auto")`**: OLS, or a logit for a two-valued outcome; weighted (WLS / weighted logit) when the data is, with `stats["weight"]` naming the column. `kind="ordinal"` fits the proportional-odds model of three to 20 ordered answers (`siamang.data.ordinal.ordinal_regression`; `auto` never chooses it): `logit P(y ≤ j) = θⱼ − xβ` as `MASS::polr` — a positive coefficient makes the higher answers more likely. `table`: `term`, `type` (`coefficient`, then `threshold`, named `Low|Medium`), `estimate`, `std_error`, `statistic` (z), `p_value`, and for the coefficients `odds_ratio` with its Wald interval `odds_ratio_lower` / `odds_ratio_upper` (`exp(confint.default(fit))`; blank for the thresholds). `stats`: `model` (`ordinal logit (proportional odds)`), `outcome`, `categories`, `order` (`Low < Medium < High`), `n`, `log_likelihood`, `pseudo_r_squared` (McFadden), `lr_chi_square`, `lr_df`, `lr_p`, `aic`, `converged`, `coefficients` (the sign convention), `interval`, and when they apply `note` (a labelled answer nobody gave), `warning` (no convergence; separation), `missing_codes` (the codebook's missing codes are left out), `weight`, `weights` (their sum, when they do not average about 1: they are frequency weights, as the logit's and `polr`'s). Maximum likelihood by BFGS on the exact gradient, polished by Newton steps on the exact Hessian; SEs from the observed information. `ordinal.fit(x, answer, weights)` is the same on plain arrays (`OrdinalFit`).
* **`pca(items: list[str], *, n_components: int | None = None, standardize: bool = True)`**: loadings and explained variance. On weighted data the components are those of the weighted covariance (standardized: correlation) matrix, `Σ pᵢ (xᵢ − m)(xᵢ − m)ᵀ / (1 − Σ pᵢ²)` with `pᵢ = wᵢ / Σw` — R's `cov.wt` — so equal weights give the unweighted result exactly. `stats["n"]` stays the rows analyzed; `stats["weight"]` names the column.
* **`reliability(items: list[str])`**: Cronbach's alpha, item means, item–total correlations and alpha if deleted — all from the same weighted moments on weighted data, with `stats["weight"]`.
* `SurveyData.cluster(items, *, k, into, seed, standardize)` is k-means on the respondents as they are; on weighted data `stats["weight"]` says the weight is not applied. A Frequencies table of the cluster variable on the weighted data gives the segments' weighted sizes.

### Confidence Intervals & Sample Size

* **`proportion_ci(column: str, value: Any, confidence: float = 0.95, weighted: bool = False) -> dict[str, Any]`**:
  Calculates a normal-approximation confidence interval for a specific category proportion. Returns `"p"`, `"lower"`, `"upper"`, and `"n"`, of the respondents who answered `column` (with `weighted=True`, the weighted share and Kish's effective base of those respondents; a missing weight counts as 0). A weighted result adds `"weight"` (the column); an unweighted one on weighted data adds `"weight": "unweighted (the weight '<column>' is not applied)"`.
* **`effective_sample_size() -> float`**:
  Calculates Kish's effective sample size (ESS) for weighted datasets: $ESS = \frac{(\sum w)^2}{\sum w^2}$. Raises a `ValueError` if no weight column is set.

---

## `siamang.data.inference`

Significance tests, post-hoc comparisons and correlations on plain arrays, with numpy and SciPy only (SciPy 1.11 or later). The tables and the flow nodes that let a test be chosen by hand are built on it.

* **`adjust_p(pvalues, method="holm") -> np.ndarray`**: `"none"`, `"bonferroni"`, `"holm"` or `"fdr_bh"` (Benjamini-Hochberg), as R's `p.adjust`; a missing p stays missing and does not count towards m.
* **`correlate(x, y, *, method="pearson", weights=None, confidence=0.95) -> dict`** and **`correlation_matrix(frame, columns, *, method="spearman", missing="pairwise", adjust="none", weights=None) -> CorrelationMatrix`** (`coefficients`, `p_values`, `p_adjusted`, `n` as square frames, `notes`, `pairs()`).
* **`ttest_independent(a, b, *, equal_var=False, confidence=0.95, names=…)`**, **`ttest_paired(x, y, …)`**, **`ttest_one_sample(x, mu, …)`** `-> TTest` (`method`, `t`, `df`, `p_value`, `difference`, `lower`, `upper`, `cohens_d`, `hedges_g`). Cohen's d is the difference over the pooled SD for two groups (Hedges' g = d · (1 − 3 / (4(n₁ + n₂) − 9))), d_z for paired data.
* **`anova(samples)`**, **`welch_anova(samples, names)`**, **`kruskal(samples)`**, **`mannwhitney(a, b)`** `-> GroupTest` (`method`, `symbol`, `statistic`, `p_value`, `df`, `df2`, `effect_name`, `effect`: η², η², ε² = H / (N − 1), rank-biserial r = 2U / (n₁n₂) − 1).
* **`posthoc(samples, names, method, *, adjust="holm", confidence=0.95) -> PostHoc`**: `"tukey"` (Tukey-Kramer: q on the ANOVA's pooled variance against the studentized range for k groups and N − k df), `"games_howell"` (each pair's variances and Welch df, q = √2·|t|), `"dunn"` (z on the mean ranks of all N values, corrected for ties, p adjusted by `"holm"` or `"bonferroni"`). `table` has one row per pair: `group_1`, `group_2`, `difference`, `statistic`, `df`, `p_value`, `p_adjusted`, `lower`, `upper`. Tukey's and Games-Howell's p is SciPy's `studentized_range.sf`, which is computed to an absolute error of about 1e-11; one below `STUDENTIZED_P_FLOOR` (1e-07) is 0.0 — not a p but "smaller than that" — and `PostHocTable` prints it `< 1e-07`.
* **`fisher_exact(table, *, confidence=0.95) -> dict`**: 2 × 2 — SciPy's two-sided p, and the conditional maximum-likelihood odds ratio with its exact interval (as R's `fisher.test` defines them, solved to full precision: R's root finder stops sooner, so on a sparse table its printed limits can differ slightly — `[[8, 1], [2, 20]]` gives an upper limit of 3712.06 here and 3592.50 in R; the p-values agree). Larger — the Fisher-Freeman-Halton p, summed exactly over every table with the observed margins when there are at most `FISHER_EXACT_LIMIT` (200,000) and otherwise estimated from `FISHER_SAMPLES` (20,000) tables drawn by Patefield's algorithm from the fixed seed `FISHER_SEED`, so a rerun gives the same p (`"exact"`, `"samples"`, `"p_error"` say which). SciPy 1.11 has no exact test beyond 2 × 2, and a p that changed with the installed SciPy would not be reproducible, so the enumeration and the sampling are the engine's own.
* **`without_missing_codes(frame, columns, variables) -> (frame, left_out)`** and **`missing_codes_note(left_out, variables) -> str | None`**: the declared missing codes of `columns` as missing values, and the sentence that says what was left out.
* **`missing_codes_counted(frame, columns, variables) -> str | None`**: the sentence the older defaults give when `frame` holds declared missing codes they read as answers (`"Trust: Acme: 38 (9 = Refused); run Missing values first to leave them out"`) — `missing_codes_counted` in the dicts of `DataAnalysis.kruskal`, `mannwhitney` and `spearman`, `Missing codes counted as answers` in the stats of `GroupMeanTable` (automatic test) and `CrossTable` (chi-square). Their numbers are unchanged.

Data that cannot carry a test — fewer than two values in a group, no variance, identical ranks — raises **`NotTestable`** (a `ValueError`) with a sentence for the reader; the tables print it as `Test = not run: …`. "No variance" is decided by **`no_spread(values, *, scale=None)`**: the range is at most `SPREAD_TOLERANCE` (10⁻¹²) times the largest value, or times `scale` — for paired differences, the size of the answers they were taken from. Three answers of 1.4 have a floating-point variance of 7e-32 and 1.1 − 1.0 and 4.1 − 4.0 differ by 4e-16; neither is spread, so a group of identical decimal values is refused exactly as a group of identical whole numbers is. `factor.fit` refuses a constant decimal item the same way.

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

### Survey-method helpers exposed as flow nodes

| Function | Returns | Notes |
|----------|---------|-------|
| `descriptives.describe(frame, columns, *, variables=None, weight=None, by=None, detail=False)` | `Descriptives(table, stats)` | N, Missing, Mean, SD, Min, Median, Max (+ Q1, Q3 type 7, bias-corrected skewness G1 and excess kurtosis G2 with `detail`), per group with `by` (a multiple-choice `by`: one overlapping group per option, and `stats["Groups"]` says so). Declared missing codes and non-numbers count as missing; weighted mean/SD/median/quartiles; undefined cells NaN. `weighted_quantile(values, weights, q)` is the smallest value whose cumulative weight reaches `q`. |
| `checks.check(data, variables=None)` | `DataCheck(table, stats)` | See `validate` above. |
| `maxdiff.with_scores(data, question, *, prefix=None)` | `ScoredData(data, stats, names)` | One interval variable per item, `<prefix><code>` (default `<question>_score_`, `score_names()`), labelled `MaxDiff score: <item>`, valid range −1…1: best − worst over times shown to that respondent, NaN where never shown. Refuses to overwrite a column it did not write. |
| `turf.evaluate(frame, portfolio, *, items=None, weight=None, labels=None)` | `TurfTable` (`method == "fixed"`) | Per option `reach`, `reach_percent`, `unique`, `unique_percent`, `frequency`; a `(portfolio)` row with the portfolio's reach and frequency. `items` sets the base; an empty portfolio reads all items. |
| `bands.bands(data, column, *, bins, into, labels=None, right=False, label=None)` | `Banded(data, stats)` | `SurveyData.recode` after taking the column's missing codes out; default labels `18 to under 30` (`band_labels`); stats count each band and what fell outside. |
| `text_coding.uncoded_answers(frame, codeframe)` | Series | The answered texts the codeframe has no theme for. |

---

## Related samples and factor analysis: `paired`, `factor`

Two modules for questions the `analysis` accessor does not answer: whether the
same respondents answer two or more questions differently, and which items of a
scale move together. Both take a `SurveyData`, leave out a respondent missing
any of the variables (listwise; the codebook's missing codes count as
missing), and return tables whose footer is their statistics
(`siamang.reporting.result_table.ResultTable`: a report and a Studio preview
show it like any table, a cell that does not apply blank). Neither has a
standard weighted form; on weighted data the statistics carry `Weight`:
`unweighted (the weight 'w' is not applied)`. The statistics name the rows left
out (`Excluded`, `Excluded because`) and the missing codes met (`Missing
codes`: `2 answers with a missing code (9 = Refused) left out`).

```python
from siamang.data import factor, paired

paired.wilcoxon(data, "trust_before", "trust_after").stats
paired.mcnemar(data, "aware_a", "aware_b").stats          # 0/1 items: yes is 1
paired.mcnemar(data, "rating_a", "rating_b", yes=[4, 5])  # top-two box
result = paired.friedman(data, ["concept_1", "concept_2", "concept_3"])
result.table, result.pairs                                # pairs: Holm-adjusted

fa = factor.analyze(data, items, rotation="promax", scores=True)
fa.loadings, fa.variance, fa.correlations, fa.stats, fa.data  # data has factor_1, …
```

### `siamang.data.paired`

| Function | What it runs |
|----------|--------------|
| `compare(data, variables, *, test="auto", yes=None, zeros="wilcox", p_value="auto", posthoc="holm")` | The `analyze.paired` node: `auto` is Wilcoxon for two variables, Friedman for more. |
| `wilcoxon(data, x, y, *, zeros="wilcox", p_value="auto")` | Wilcoxon signed-rank of `x − y`. |
| `mcnemar(data, x, y, *, yes=None, p_value="auto")` | McNemar; `yes` is a code or a list of codes, the rest is no. Left empty it is 1 when both variables hold only 0 and 1, and an error that lists the codes otherwise. |
| `friedman(data, variables, *, posthoc="holm", zeros="wilcox", p_value="auto")` | Friedman on three or more; `posthoc` `holm` \| `bonferroni` \| `none` adjusts pairwise Wilcoxon tests. |
| `cochran(data, variables, *, yes=None, posthoc="holm", p_value="auto")` | Cochran's Q on three or more yes/no variables (`yes` as for McNemar); `posthoc` adjusts pairwise McNemar tests, whose p follows `p_value`. |
| `signed_rank(differences, *, zeros, p_value)`, `mcnemar_test(b, c, *, p_value)`, `friedman_test(matrix)`, `cochran_test(matrix)`, `adjust(pvalues, method)` | The same tests on plain numbers. |

Each returns a `PairedResult`: `table` (per variable N, mean, SD, median — and
for Wilcoxon the difference, for Friedman the mean rank; McNemar's is the 2 × 2
table of yes and no), `pairs` (Friedman's pairwise comparisons: A, B, N — every
respondent compared, as in the footer — Zero differences, W+, W−, Z, p, p
adjusted, r, rank-biserial r), `stats` and `test` (the unrounded
numbers).

- **Wilcoxon.** Differences are first minus second (`x − y`, as R's `wilcox.test(x, y, paired = TRUE)`, SciPy's `wilcoxon(x, y)` and the paired t-test; Friedman's pairs are A − B). `zeros="wilcox"` drops a
  pair that answered the same (R's `wilcox.test`, SPSS); `"pratt"` ranks it and
  leaves it out of the sums. The two-sided p-value follows SciPy's rule: exact
  up to 50 pairs with no ties or zeros, exact over the sign permutations up to
  13 pairs with them, the tie-corrected normal approximation without continuity
  correction otherwise. `p_value="exact"` computes the exact permutation
  distribution up to 1000 pairs; `"approximate"` always uses the normal one.
  Stats: `W+`, `W-`, `Z` (positive: the first is higher), `p`, `p-value` (how),
  `r = Z/√n` over the ranked pairs, `Rank-biserial r = (W+ − W−)/(W+ + W−)`,
  and the counts of positive, negative and zero differences.
- **McNemar.** Exact binomial p below 25 discordant pairs, otherwise
  `(|b − c| − 1)² / (b + c)` on 1 df (R, statsmodels). Stats: the share saying
  yes to each and the difference in points (`Difference`: first − second), both discordant counts,
  `Chi-square`/`df` when used, `Cohen's g`, `Odds ratio` (b / c).
- **Friedman.** Tie-corrected χ² on k − 1 df, `Kendall's W = χ² / (n (k − 1))`.
  Mean-rank post-hocs (Nemenyi, Dunn) are not offered: they compare two
  variables on ranks that depend on the others in the set.
- **Cochran's Q.** `Q = (k − 1)(k ΣCⱼ² − N²) / (k N − ΣRᵢ²)` on k − 1 df (Cj:
  yeses to variable j, Ri: yeses of respondent i, N: all yeses), as R's
  `DescTools::CochranQTest` and statsmodels' `cochrans_q`; a respondent saying
  yes to all or none carries no information. `table`: Variable, N, Yes, % yes;
  stats `Test`, `Counts as yes`, `Variables`, `N`, `Q`, `df`, `p`, `Pairwise`.
  `pairs`: per pair A, B, N, % yes A, % yes B, Difference (points, A − B), Yes
  only A, Yes only B, Chi-square (blank when exact), p, p adjusted; its footer
  names the adjustment, the p-value method and the pairs no respondent
  answered differently. `CochranTest` holds the unrounded Q, df, p and the yes
  count per variable.
- Nothing to test is a result, not an error: everyone giving the same answer
  twice, or no discordant pair, leaves out `p` and says why in `Note`.

### `siamang.data.factor`

`analyze(data, items, *, n_factors=None, criterion="kaiser", method="minres",
rotation="varimax", sort=False, hide_below=0.0, scores=False, into="factor_",
seed=42) -> FactorAnalysis`; `fit(matrix, …) -> FactorSolution` on a plain
respondents × items matrix.

| Argument | Values |
|----------|--------|
| `n_factors` | a number; `None` chooses by `criterion`: `kaiser` (eigenvalues above 1) or `parallel` (above the 95th percentile of 100 random data sets of the same size, from `seed` with NumPy's stable `RandomState`) |
| `method` | `minres` (factor_analyzer, `psych::fa`), `principal` (iterated principal axis as `psych::fa(fm="pa")`: SMC start, stops when the communalities' sum moves by < 0.001, 50 steps at most), `ml` (`factanal`'s objective; adds `Fit chi-square`, `Fit df`, `Fit p`; started from `factanal`'s start, the minres solution, 1 − SMC, 0.5 and `ML_RANDOM_STARTS` (10) points from the fixed `ML_SEED`, keeping the lowest objective) |
| `rotation` | `varimax` (Kaiser-normalized, R's algorithm), `promax` (power 4, Kaiser-normalized as factor_analyzer and SPSS), `oblimin` (direct quartimin, γ = 0, as GPArotation), `none` |
| `sort`, `hide_below` | order the items by the factor they load on most; blank loadings below the value in the table |
| `scores`, `into` | add regression-method scores `<into>1`, `<into>2`, … (interval, labelled), missing for respondents left out |
| `read_later` | score names a later step reads (a flow passes those its nodes downstream name): with `n_factors=None`, each the rule did not keep is added empty, labelled `Factor 3 score (not made: the Kaiser criterion kept 2 factors)` and named in `stats["Scores"]` (`…; factor_3 empty: the Kaiser criterion kept 2 factors`); no other score is added |

`FactorAnalysis` holds `loadings` (Variable, Label, Factor 1…, Communality,
Uniqueness, MSA), `variance` (every eigenvalue with its % and cumulative %,
then the extracted and — for varimax — rotated sums of squared loadings of the
kept factors; after an oblique rotation the rotated variances overlap and get
no percentage), `correlations` (between the factors; the identity after an
orthogonal rotation), `stats` (extraction, rotation, factors and how they were
chosen, N, variance explained, KMO, Bartlett's χ², df and p, RMSR, warnings;
on weighted data every one of the three tables says `Weight: unweighted (…)`),
`data` and `solution` (the numbers: loadings, structure, phi, communalities,
eigenvalues, KMO per item, …).

Every factor is signed so its loadings sum positive and the factors are ordered
by their sum of squared loadings; the communalities come from the unrotated
solution, which a rotation does not change. Scores standardise the items with
the sample SD (R's `scale()`; `factor_analyzer.transform` uses the population
SD). Refused with the reason: fewer than three items, no more complete
respondents than items, an item without variance, a singular correlation matrix
(an item that copies or totals others — named), as many factors as items, and
more factors than maximum likelihood can identify. Warned in `stats["Warning"]`:
KMO below 0.5, a Heywood case, a fit or rotation that did not converge, more
factors than the correlations identify, and maximum likelihood starts that
reached different optima ("maximum likelihood reached different solutions from
different starting points; the best of 14 is shown. That usually means more
factors than the data carry: compare a solution with fewer").

---

## `siamang.data.intervals`

The intervals a chart's error bars show (`siamang.reporting.result_charts`).
Each returns an **`Interval`** (`estimate`, `lower`, `upper`, `n`, `confidence`,
`method`, `se`, `note`, `defined`); when there is no interval — no answers, one
answer, nothing weighted — `lower` and `upper` are `None` and `note` says why
(`"no answers"`, `"one answer has no interval"`, `"no answer carries weight"`).

* **`mean_interval(values, weights=None, *, confidence=0.95)`**: unweighted,
  Student's t, mean ± t(n − 1) · SD / √n (R's `t.test`). Weighted, the
  linearization (Taylor series) standard error of a ratio mean under
  with-replacement sampling of the respondents, SE² = n / (n − 1) · Σ wᵢ² (yᵢ −
  ȳ)² / (Σ wᵢ)² — `survey::svymean` with `svydesign(ids = ~1, weights = ~w)` —
  with t(n − 1), as `confint(…, df = degf(design))`; an answer weighted 0 (a
  missing weight counts 0) takes no part, and equal weights give exactly the
  unweighted interval. A negative weight is refused.
* **`t_interval(mean, sd, n, *, confidence=0.95)`**: the same t interval from a
  table's own numbers.
* **`proportion_interval(successes, n, *, confidence=0.95)`**: Wilson's score
  interval (R's `prop.test(x, n, correct = FALSE)`), 0 and 1 exactly at 0 % and
  100 %.

---

## References

1. Agresti, Alan. *An Introduction to Categorical Data Analysis*. Wiley, 3rd edition, 2018.
2. McKinney, Wes. *Python for Data Analysis: Data Wrangling with pandas, NumPy, and Jupyter*. O'Reilly Media, 3rd edition, 2022.
3. Wickham, Hadley. *ggplot2: Elegant Graphics for Data Analysis*. Springer, 2nd edition, 2016.
