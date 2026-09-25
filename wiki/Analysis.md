# Analysis

The `data.analysis` accessor (`DataAnalysis`) provides descriptive and
inferential statistics that are aware of survey weights and variable metadata.
The `data.processing` accessor offers quick value-level recoding. This page
covers the most common methods with runnable examples on simulated data.

```python
# All examples below assume `data` is a SurveyData (see Simulation):
from siamang.core import Variable, VariableMap, SingleChoice, NumericInput, LikertScale, Page, Questionnaire

age = Variable("age", scale="ratio", label="Age", valid_range=(18, 75))
it_role = Variable("it_role", scale="nominal", label="IT Role",
                   labels={1: "Engineer", 2: "Data Scientist", 3: "DevOps", 4: "PM"})
remote_freq = Variable("remote_freq", scale="ordinal", label="Remote Frequency",
                       labels={1: "Never", 2: "Occasionally", 3: "Hybrid", 4: "Mostly remote", 5: "Fully remote"})
autonomy = Variable("autonomy", scale="ordinal", label="Autonomy",
                    labels={1: "Very low", 2: "Low", 3: "Moderate", 4: "High", 5: "Very high"})

variables = VariableMap()
variables.add_many([age, it_role, remote_freq, autonomy])

survey = Questionnaire(
    title="Work Study",
    pages=[Page(name="main", items=[
        NumericInput("Age?", var=age),
        SingleChoice("Role?", var=it_role),
        SingleChoice("Remote?", var=remote_freq),
        LikertScale("Autonomy?", var=autonomy, points=5),
    ])],
    variables=variables,
)
data = survey.simulate(n=200, seed=123)
```

---

## Descriptive statistics

### `mean`

```python
def mean(self, column: str, weighted: bool = False) -> float: ...
```

Arithmetic mean of a column (NaNs dropped). With `weighted=True`, uses the
default weight column set via `with_weight(...)`; raises `ValueError` if no
weight is configured.

```python
data.analysis.mean("autonomy")        # 3.06
```

### `median`

```python
def median(self, column: str) -> float: ...
```

Median of a column (NaNs dropped).

```python
data.analysis.median("age")
```

### `grouped_mean`

```python
def grouped_mean(self, column: str, by: str,
                 weighted: bool = False, labels: bool = False) -> pd.DataFrame: ...
```

Mean of `column` within each category of `by`. Returns a DataFrame with `group`,
`mean`, and `n`. With `labels=True`, adds a `label` column resolving each
group's value label. With `weighted=True`, `n` is the summed weight per group.

```python
print(data.analysis.grouped_mean("autonomy", by="remote_freq", labels=True))
#    group      mean     n          label
# 0      1  3.222222  45.0          Never
# 1      2  2.923077  39.0   Occasionally
# 2      3  2.897959  49.0         Hybrid
# 3      4  3.000000  31.0  Mostly remote
# 4      5  3.277778  36.0   Fully remote
```

For a formatted, significance-tested version of this comparison, prefer the
[[Reporting Tables|Reporting-Tables]] `data.report.means(...)` table.

---

## Inferential tests

These methods require **`scipy`**, which ships with the base install (they raise
`ImportError` if it is somehow missing). Each returns a plain `dict`.

### `kruskal`

```python
def kruskal(self, column: str, group: str) -> dict[str, Any]: ...
```

Kruskal–Wallis H-test for 3+ independent groups (the non-parametric analogue of
one-way ANOVA). Returns `{"statistic", "p_value", "groups"}`, where `groups` is
the number of groups compared. Raises `ValueError` with fewer than two
non-empty groups.

```python
data.analysis.kruskal("autonomy", "remote_freq")
# {'statistic': 2.1330..., 'p_value': 0.7112..., 'groups': 5.0}
```

### `mannwhitney`

```python
def mannwhitney(self, column: str, group: str) -> dict[str, Any]: ...
```

Mann–Whitney U-test for **exactly two** independent groups (two-sided). Returns
`{"statistic", "p_value", "group_a", "group_b"}`, where `group_a`/`group_b` are
the two group values compared. Raises `ValueError` unless exactly two non-empty
groups are present.

```python
two_levels = data.with_frame(data.frame[data.frame["remote_freq"].isin([1, 5])])
two_levels.analysis.mannwhitney("autonomy", "remote_freq")
# {'statistic': 794.0, 'p_value': 0.8796..., 'group_a': 1, 'group_b': 5}
```

> The [[Reporting Tables|Reporting-Tables]] `GroupMeanTable` picks between
> t-test, ANOVA, Mann–Whitney, and Kruskal–Wallis automatically based on scale
> and group count — use it when you want the test chosen for you, and name the
> test yourself (below) when you want a particular one.

---

## Choosing the test yourself

The methods and tables in this section compute with `siamang.data.inference`
(numpy and SciPy only; SciPy 1.11 is enough). They share three rules:

- **Missing codes are not answers.** The codebook's declared missing codes (a
  "Don't know" coded 99) are left out, and the result says how many:
  `Missing codes left out = Satisfaction: 12 (99 = Don't know)`. The defaults
  above — `spearman`, `kruskal`, `mannwhitney`, the automatic test of
  `report.means` and the chi-square of `report.crosstab` — read the data as they
  always have; put `apply_missing_values()` (the flow's **Missing values** node)
  before them to have them do the same.
- **What the data cannot carry is said in words.** One respondent in a group or
  no variance at all gives `Test = not run: …` with the reason, not a number or
  a crash. A group of identical decimal values (1.4, 1.4, 1.4) or paired
  answers that all differ by the same decimal amount has no variance, although
  floating-point rounding leaves one of about 1e-32: values whose range is at
  most 10⁻¹² of their size count as the same (`inference.no_spread`). A request that cannot work — a t-test of a grouping with three
  groups and none named — is a `ValueError` that lists the groups.
- **The weight is used where there is a standard weighted form** (Pearson's
  correlation) and otherwise the result says `unweighted (the weight 'w' is not
  applied)`.

### Correlation: `correlation` and `report.correlation_matrix`

```python
def correlation(self, x: str, y: str, *, method: str = "pearson",
                confidence: float = 0.95) -> dict[str, Any]: ...
```

`method` is `"pearson"`, `"spearman"` or `"kendall"` (tau-b, which corrects
for ties). The result has `method`, the coefficient under its symbol (`r`,
`rho` or `tau`), `p_value` (two-sided) and `n`; Pearson adds a Fisher-z
confidence interval `lower` – `upper`. On weighted data Pearson is the weighted
coefficient, with p and interval on Kish's effective base (`n_effective`), so a
weight never makes a correlation look more certain than the respondents behind
it; equal weights give the unweighted result.

```python
data.analysis.correlation("age", "autonomy")
# {'method': 'Pearson', 'r': -0.00277..., 'p_value': 0.9689..., 'n': 200,
#  'lower': -0.1414..., 'upper': 0.1360..., 'confidence': 0.95}
data.analysis.correlation("age", "autonomy", method="kendall")
# {'method': 'Kendall tau-b', 'tau': -0.00238..., 'p_value': 0.9637..., 'n': 200}
```

A matrix of several variables is a table:

```python
data.report.correlation_matrix(["age", "autonomy", "remote_freq"],
                               method="spearman", missing="pairwise",
                               adjust="holm", layout="matrix")
```

```text
| Variable | Age | Autonomy | Remote Frequency |
|---|---|---|---|
| Age | — |  |  |
| Autonomy | -0.003 | — |  |
| Remote Frequency | 0.125 | 0.009 | — |

Method = Spearman rank correlation; Missing = pairwise: each pair uses everyone
who answered both; N = 200; p adjustment = Holm, over 3 pairs; Marks = * p < .05,
** p < .01, *** p < .001 (adjusted p)
```

`missing="listwise"` keeps only the respondents who answered every variable;
`adjust` is `"none"`, `"holm"`, `"bonferroni"` or `"fdr_bh"`; `layout="pairs"`
gives one row per pair with the coefficient, p, the adjusted p and N — the one
to read when N differs from pair to pair. The numbers are on `table.result`
(`coefficients`, `p_values`, `p_adjusted`, `n` as square frames).

### t-tests: `report.ttest`

```python
data.report.ttest(column, *, kind="independent", by=None, groups=None,
                  other=None, mu=0.0, variances="welch", confidence=0.95)
```

- `kind="independent"` compares `column` between two groups of `by`. When `by`
  has more than two values, `groups=[a, b]` names the two (as codes); without it
  the call is refused with the groups listed. `variances="welch"` (the default)
  does not assume the groups vary equally; `"student"` pools the variances.
- `kind="paired"` compares `column` with `other` on the same respondents, over
  the complete pairs; the footer counts the incomplete ones left out.
- `kind="one_sample"` tests the mean of `column` against `mu`.

The table has one row per group (or measurement) with N, mean, SD and SE; the
footer gives the test, t, df, p, the mean difference (first minus second, or
mean minus `mu`) with its CI, and Cohen's d — pooled-SD d and Hedges' g for two
groups, d_z for paired data.

```python
print(data.report.ttest("age", by="it_role", groups=[1, 4]).to_markdown())
```

```text
| IT Role | N | Mean | SD | SE |
|---|---|---|---|---|
| Engineer | 58 | 46.845 | 16.559 | 2.174 |
| PM | 52 | 47.5 | 18.873 | 2.617 |

Test = Welch's t-test (unequal variances); t = -0.1930; df = 102.1500; p = 0.8477;
Mean difference = -0.6550; Difference = Engineer − PM; 95% CI = -7.404 – 6.094;
Cohen's d = -0.0370; Hedges' g = -0.0370; N = 110; Variable = Age
```

### Several groups and post-hoc tests: `report.means`

```python
data.report.means(column, *, by, test=True, method="auto",
                  posthoc="none", adjust="holm")
```

`method` names the test instead of letting the table choose: `"student"`,
`"welch"` (two groups), `"anova"`, `"welch_anova"` (two or more; Welch's does
not assume equal variances), `"mannwhitney"`, `"kruskal"` (ranks). Each reports
its statistic, df, p and an effect size — Cohen's d, η², the rank-biserial r or
ε². A two-group test asked of three groups says `not run: … choose anova or
welch_anova`.

`posthoc` compares every pair of groups after the test it belongs to —
`"tukey"` after `"anova"` (Tukey-Kramer for unequal groups), `"games_howell"`
after `"welch_anova"`, `"dunn"` after `"kruskal"` with p adjusted by `adjust`
(`"holm"` or `"bonferroni"`). Any other pairing is a `ValueError`. The pairs
render under the means table and are `table.posthoc_table`; `export_xlsx` puts
them on a second sheet.

```python
print(data.report.means("age", by="it_role", method="welch_anova",
                        posthoc="games_howell").to_markdown())
```

```text
| IT Role | Mean | SD | Median | N |
|---|---|---|---|---|
| Engineer | 46.845 | 16.559 | 47.0 | 58 |
| Data Scientist | 41.851 | 15.043 | 40.0 | 47 |
| DevOps | 46.209 | 16.29 | 44.0 | 43 |
| PM | 47.5 | 18.873 | 41.0 | 52 |

Test = Welch's ANOVA; F = 1.2530; df = 3, 106.78; p = 0.2942; η² = 0.0170;
Post-hoc = Games-Howell: 0 of 6 pairs differ at p < 0.05; N = 200; Variable = Age

**Post-hoc: Games-Howell**

| Pair | Difference | 95% CI low | 95% CI high | q | df | p |
|---|---|---|---|---|---|---|
| Engineer vs Data Scientist | 4.994 | -3.075 | 13.063 | 2.286 | 101.62 | 0.374 |
| Engineer vs DevOps | 0.636 | -8.004 | 9.275 | 0.272 | 91.45 | 0.9975 |
| …
```

Tukey and Games-Howell give the difference of the means with its simultaneous
interval, the studentized range statistic q and a p that already allows for the
number of pairs; Dunn gives the difference of the mean ranks, z, and p before
and after the adjustment.

`compare_groups` is the same for the rank tests alone, as a dict:

```python
data.analysis.compare_groups("autonomy", "remote_freq", posthoc="dunn")
# {'test': 'Kruskal-Wallis H', 'statistic': 2.133..., 'p_value': 0.7112...,
#  'groups': 5.0, 'n': 200, 'posthoc': "Dunn's test (Holm)",
#  'Never vs Occasionally': 'z = 0.939, p = 1.0000', …}
```

### Fisher's exact test: `report.crosstab(..., method="fisher")`

For small counts, where the chi-square's approximation is poor. A 2 × 2 table
gets the two-sided p, the odds ratio (conditional maximum likelihood) and its
exact 95 % CI, as R's `fisher.test` reports them. A larger table gets the
Fisher–Freeman–Halton test: the p is summed exactly over every table with the
observed margins when there are at most 200,000 of them, and otherwise estimated
from 20,000 random tables drawn from a fixed seed — so a rerun gives the same
p, and the footer says which it was and the Monte Carlo error. The test counts
respondents (an exact test needs whole counts), so on weighted data the cells
are weighted and the footer says the test is not.

```text
| IT Role | Never | Fully remote | Total |
|---|---|---|---|
| Engineer | 10 | 9 | 19 |
| Data Scientist | 9 | 15 | 24 |
| Total | 19 | 24 | 43 |

Test = Fisher's exact test; p = 0.3678; Odds ratio = 1.8250; OR 95% CI = 0.463 – 7.466;
Odds ratio of = Never (vs Fully remote) for Engineer over Data Scientist;
Estimate = conditional maximum likelihood, as R's fisher.test; N = 43
```

### Multiple comparisons: `adjust_p`

```python
from siamang.data.inference import adjust_p

adjust_p([0.01, 0.04, 0.03, 0.2], "holm")      # [0.04, 0.09, 0.09, 0.2]
```

`"bonferroni"`, `"holm"` and `"fdr_bh"` (Benjamini–Hochberg) give what R's
`p.adjust` gives; a missing p stays missing and does not count.

### In a flow

| Node | Parameters |
| :--- | :--- |
| **Correlation** | **Method**: `pearson`, `spearman` (default), `kendall` |
| **Correlation matrix** | **Variables**, **Method**, **Missing answers** (`pairwise` / `listwise`), **p adjustment**, **Layout** (`matrix` / `pairs`) |
| **t-test** | **Design** (`independent` / `paired` / `one_sample`), **Variable**, **Groups**, **Group A**, **Group B**, **Variances**, **Second measurement**, **Test value**, **Confidence** |
| **Group means** | **Significance test**, **Test** (`auto` default), **Post-hoc**, **Dunn p adjustment** |
| **Compare groups** | **Test**, **Post-hoc** (`none` / `dunn`), **Dunn p adjustment** |
| **Crosstab** | **Significance test**, **Test** (`chi2` default / `fisher`) |

The flow check refuses a post-hoc test that does not follow its test ("Tukey's
HSD follows a one-way ANOVA — set Test to anova, or Post-hoc to none.") and
warns when a choice would be ignored. A flow saved before these parameters
existed runs exactly as before.

---

## Paired tests

`kruskal` and `mannwhitney` compare *different* people. When the *same*
respondents answer two or more questions — one scale asked about two brands, a
rating before and after a message, three concepts each rated by everyone —
`siamang.data.paired` asks whether their answers shift. Each function takes the
`SurveyData` and returns a `PairedResult`: `table` and `pairs` (tables with the
statistics as their footer), `stats` (the same statistics as a `dict`) and
`test` (the unrounded numbers). The flow node is **Paired tests**
(`analyze.paired`).

```python
from siamang.data import paired

result = paired.wilcoxon(data, "remote_freq", "autonomy")   # second minus first
result.stats["p"], result.stats["r"], result.stats["Rank-biserial r"]
print(result.table.to_markdown())                          # N, mean, SD, median
```

| Function | Test | Main statistics |
|----------|------|-----------------|
| `wilcoxon(data, x, y, *, zeros="wilcox", p_value="auto")` | Wilcoxon signed-rank, two ordered variables | `W+`, `W-`, `Z`, `p`, `r = Z/√n`, `Rank-biserial r`; positive, negative and zero differences |
| `mcnemar(data, x, y, *, yes=None, p_value="auto")` | McNemar, two yes/no variables | `% yes` of each, the difference in points, both discordant counts, `Chi-square` or the exact binomial `p`, `Cohen's g`, `Odds ratio` |
| `friedman(data, variables, *, posthoc="holm")` | Friedman, three or more ordered variables | `Chi-square`, `df`, `p`, `Kendall's W`; `pairs`: a Wilcoxon test per pair with Holm- (or Bonferroni-) adjusted p |
| `compare(data, variables, *, test="auto", …)` | what the flow node runs | `auto`: Wilcoxon for two variables, Friedman for more |

- **Who is compared.** A respondent missing any of the variables is left out
  of all of them, and the codebook's missing codes (a "Refused" coded 9) count
  as missing, not as answers. `stats` says how many were left out (`Excluded`)
  and which codes were met (`Missing codes`).
- **Wilcoxon.** A respondent who gave both the same answer is dropped before
  ranking (`zeros="wilcox"`, as R and SPSS) or ranked and left out of the sums
  (`zeros="pratt"`). The p-value is exact for small samples — up to 50 pairs
  with no ties or zeros, up to 13 with them — and otherwise the tie-corrected
  normal approximation, as SciPy computes it; `p_value="exact"` or
  `"approximate"` forces either.
- **McNemar.** `yes` is the code, or list of codes, that counts as yes
  (`yes=[4, 5]` is a top-two box); every other answer is no. For 0/1 variables
  it can be left out. Below 25 respondents who answered the two differently the
  p-value is the exact binomial test, above it the chi-square with continuity
  correction.
- **Friedman.** The pairwise comparisons are Wilcoxon tests on the same
  respondents; `posthoc="none"` skips them.
- Wilcoxon and Friedman rank answers, so a nominal variable is refused (use
  McNemar for yes/no questions). Everyone giving the same answer twice is a
  result, not an error: `p` is left out and `Note` says why.
- None of these tests has a weighted form: on weighted data `stats["Weight"]`
  reads `unweighted (the weight 'w' is not applied)`.

---

## Factor analysis

`siamang.data.factor.analyze` is an exploratory factor analysis: which items of
a scale move together, how strongly each belongs to each factor, and whether
the items share enough to be factored at all. It is what a scale is checked
with before its items are averaged into an index. The flow node is **Factor
analysis** (`analyze.factor`).

```python
from siamang.data import factor

items = ["q1", "q2", "q3", "q4", "q5", "q6", "q7", "q8"]   # eight statements rated 1–5
fa = factor.analyze(data, items, rotation="promax", sort=True, hide_below=0.3)
print(fa.loadings.to_markdown())    # items × factors, communality, uniqueness, MSA
fa.stats["KMO"], fa.stats["Bartlett p"], fa.stats["Variance explained %"]
fa.variance.to_frame()              # eigenvalues and variance explained
fa.correlations.to_frame()          # between the factors (promax, oblimin)

scored = factor.analyze(data, items, n_factors=2, scores=True).data
scored.report.means("factor_1", by="it_role")
```

| Argument | Values |
|----------|--------|
| `n_factors` | a number, or `None` to choose by `criterion`: `"kaiser"` (eigenvalues above 1) or `"parallel"` (parallel analysis from `seed`) |
| `method` | `"minres"` (default), `"principal"` (iterated principal axis), `"ml"` (maximum likelihood, with a test of fit) |
| `rotation` | `"varimax"` (default, uncorrelated factors), `"promax"`, `"oblimin"` (correlated factors), `"none"` |
| `sort`, `hide_below` | group the items by their main factor; blank the small loadings in the table |
| `scores`, `into` | add regression-method scores `factor_1`, `factor_2`, … to the data |

The items are analysed through their correlations (standardised). A respondent
missing any item is left out, the codebook's missing codes counted as missing.
The numbers reproduce the `factor_analyzer` package and R's `psych::fa` (and
`factanal` for maximum likelihood): each factor is signed so its loadings sum
positive, and the factors are ordered by the variance they carry. The analysis
refuses, with the reason, fewer than three items, no more respondents than
items, an item everyone answered the same, and an item that copies or totals
others; it warns in `stats["Warning"]` about a KMO below 0.5 or an item with
(almost) no uniqueness left. Maximum likelihood with more factors than the data
carry — more than parallel analysis or the Kaiser rule suggest — can have
several optima: the fit is started from 14 fixed points, keeps the best, and
warns when they disagree, which is a reason to compare a solution with fewer
factors. It is unweighted, and says so on weighted data.

---

## Weighted statistics

Set a default weight column once with `with_weight(...)`, then pass
`weighted=True` to any method that supports it (`mean`, `grouped_mean`,
`frequencies`, `crosstab`, `proportion_ci`). `proportion_ci` says which it did:
`"weight": "w"` when weighted, and `"weight": "unweighted (the weight 'w' is not
applied)"` when called without `weighted=True` on weighted data. Weighted or not,
its base is the respondents who answered the question: weights of 1 give the
unweighted `p` and `n`.

The models read the weight on their own: `regression` fits WLS or a weighted
logit, and `pca` and `reliability` work from the weighted covariance matrix
(the unbiased estimate for reliability weights, as R's `cov.wt` computes it, so
equal weights reproduce the unweighted result). Each names the column in
`stats["weight"]`.

`correlation` with Pearson (and a Pearson correlation matrix) is weighted too,
with its p on Kish's effective base, and names the column. `kruskal`,
`mannwhitney`, `spearman`, `compare_groups`, `correlation` with Spearman or
Kendall, the t-tests, the paired tests, factor analysis and `SurveyData.cluster`
have no standard weighted form and run on the respondents as they are; on weighted data their result carries
`"weight": "unweighted (the weight 'w' is not applied)"` (the tables: `Weight`),
so it cannot be mistaken for a weighted one. The declarative tables and charts follow
the same rule — see [[Working with Data|Working-with-Data#what-the-weight-reaches]].

```python
import numpy as np

# attach a synthetic design weight for illustration
weighted = data.with_frame(data.frame.assign(w=np.linspace(0.5, 1.5, len(data.frame)))) \
               .with_weight("w")

weighted.analysis.mean("autonomy", weighted=True)
weighted.analysis.effective_sample_size()   # Kish's ESS = (Σw)² / Σw²
```

`effective_sample_size()` reports Kish's effective sample size for the weighted
frame and raises `ValueError` if no weight is set. See
[[Working with Data|Working-with-Data]] for `with_weight`.

---

## Quick recoding: `data.processing.recode`

```python
def recode(self, column: str, mapping: dict[Any, Any]) -> SurveyData: ...
```

`DataProcessing.recode` applies a raw `{old: new}` mapping to the column
(values not listed in the mapping are kept) and returns a bare `SurveyData`
around the transformed frame. It is a thin convenience wrapper and **does
not** carry over variable metadata, the questionnaire, or a configured
weight.

```python
# Collapse the 5-point remote-frequency scale into 3 levels
collapsed = data.processing.recode("remote_freq", {1: 1, 2: 1, 3: 2, 4: 3, 5: 3})
```

> **Note:** For research-grade, metadata-aware recoding that registers a new
> variable with proper labels and scale, prefer `SurveyData.recode_values(...)`
> (collapse/remap discrete codes), `SurveyData.recode(...)` (bin a continuous
> variable into ordinal categories), or `SurveyData.derive(...)` (build a 0/1
> indicator from an [[Visibility and Branching|Visibility-and-Branching]]
> expression). These live on `SurveyData` itself, not on the `processing`
> accessor.

```python
# Metadata-aware: bin age into ordinal brackets, registered as a new variable
banded = data.recode("age", into="age_band", bins=[18, 30, 45, 75],
                      labels=["18-29", "30-44", "45+"], label="Age band")
banded.variables["age_band"].labels   # {1: '18-29', 2: '30-44', 3: '45+'}
```

---

## Descriptive statistics: `data.report.descriptives`

```python
data.report.descriptives(columns: list[str], *, by: str | None = None,
                         detail: bool = False) -> DescriptivesTable
```

One row per variable — or per variable and group with `by` — with `N`,
`Missing`, `Mean`, `SD`, `Min`, `Median` and `Max`; `detail=True` adds `Q1`,
`Q3` (linear interpolation, R's type 7), `Skewness` and `Kurtosis` (the
bias-corrected G1 and excess G2 that SPSS and Excel report). The flow node is
**Descriptive statistics** (`analyze.descriptives`).

```python
table = data.report.descriptives(["age", "autonomy"])
print(table.to_markdown())
# | Variable | Label | N | Missing | Mean | SD | Min | Median | Max |
# |---|---|---|---|---|---|---|---|---|
# | age | Age | 200 | 0 | 45.705 | 16.82 | 18.0 | 42.0 | 75.0 |
# | autonomy | Autonomy | 200 | 0 | 3.06 | 1.452 | 1.0 | 3.0 | 5.0 |

data.report.descriptives(["autonomy"], by="it_role", detail=True).to_frame()
#    Variable     Label         IT Role   N  Missing   Mean     SD  Min   Q1  Median    Q3  Max  Skewness  Kurtosis
# 0  autonomy  Autonomy        Engineer  58        0  3.121  1.557  1.0  2.0     3.5  4.75  5.0    -0.179    -1.529
# …
```

- **A missing code is not an answer.** A code the codebook declares missing (a
  99 "Don't know") counts in `Missing`, as does a value that is not a number;
  `stats` names them (`Missing codes`, `Not numbers`). With `by`, a blank or a
  missing code of the group variable is no group (`Not in a group`).
- **Weighted data:** `Mean`, `SD`, `Median` and the quartiles are weighted —
  the same formulas as the `GroupMeanTable` (the SD scaled by n / (n − 1), the
  median the first value whose cumulative weight reaches half), so the two never
  disagree — while `N` and `Missing` stay counts of respondents beside a
  `Weighted N` column. `stats` gives `Weighted N`, `Effective N` (Kish) and the
  `Design effect`; skewness and kurtosis stay unweighted and the `Note` says so.
- **Undefined is blank.** The SD of one answer, skewness below three answers and
  kurtosis below four (or without spread) are NaN in `to_frame()` and empty
  cells in Markdown and HTML.

`siamang.data.descriptives.describe(frame, columns, variables=…, weight=…,
by=…, detail=…)` is the same computation on a bare frame.

## Checking the data: `data.report.data_check`

`SurveyData.validate()` says *that* a variable has values outside its valid
range; the data check says **how many rows and which values**, one row per
problem, errors first. The flow node is **Data check** (`analyze.data_check`).

```python
checked = data.report.data_check()          # or data_check(["age"])
checked.to_frame()
#   Severity  Variable                              Problem  Rows Examples                 Code
# 0    error       age        outside the valid range 18–75     3  999 (3)         OUT_OF_RANGE
# 1    error  autonomy  codes the codebook has no label for     1    7 (1)  INVALID_LABEL_VALUE
checked.stats   # {'Checked': '4 variables, 200 rows', 'Errors': 2, 'Warnings': 0}
```

Declared missing codes are not flagged as out of range. Columns the codebook
does not know, and codebook variables the data lacks (common after a Select),
are gathered into one row each. With nothing wrong the table is empty and
`stats["Result"]` reads `no problems found`. The check counts rows, so on
weighted data `stats["Weight"]` says the weight is not applied.

## MaxDiff scores per respondent

`siamang.data.maxdiff.with_scores(data, question, prefix=None)` adds one
variable per item, `<question>_score_<code>` by default, holding each
respondent's counting score — best minus worst over the times the item was
shown to *them*, from −1 to 1, blank where it was never shown. The variables are
labelled `MaxDiff score: <item>`, interval, with a valid range of −1…1, so they
feed a crosstab, a cluster or a regression. The flow node is **MaxDiff scores**
(`prepare.maxdiff_scores`); its `stat` names the respondents scored and the
answers that could not be read against the design.

```python
from siamang.data import maxdiff

# on the responses to a questionnaire with a MaxDiff whose id is "q_md"
scored = maxdiff.with_scores(responses, "q_md")
scored.data.report.means("q_md_score_1", by="region")
scored.stats["Respondents scored"]
```

## TURF: a fixed portfolio

`siamang.data.turf.evaluate(frame, portfolio, items=…, weight=…, labels=…)`
reads one portfolio instead of searching for the best: each option's `reach`,
its `unique` reach (the respondents no other option of the portfolio reaches —
what dropping it would lose) and `frequency`, then a `(portfolio)` row with the
reach and frequency of all of them together. `items` is the question's whole
list of options, so the base is the one `turf()` uses. In a flow: **TURF** with
Search = `fixed` and a **Portfolio**. On weighted data the reach is a sum of
weights and the frequency a weighted mean — in the search too.

## Bands

`siamang.data.bands.bands(data, "age", bins=[18, 30, 45, 76], into="age_band")`
cuts a number into a labelled ordinal variable (`18 to under 30`, …) after
taking the codebook's missing codes out, so a 999 "Refused" never lands in the
top band; `stats` counts every band and whatever fell outside. The flow node is
**Bands** (`prepare.bands`). **Derive** takes `labels` for a formula that
yields codes (`if age < 50 then 1 else 2` → `{1: "Under 50", 2: "50 or over"}`).

---

See also: [[Working with Data|Working-with-Data]] · [[Reporting Tables|Reporting-Tables]] · [[Banner Tables|Banner-Tables]] · [[Simulation]] · [[Variables and Measurement|Variables-and-Measurement]]
