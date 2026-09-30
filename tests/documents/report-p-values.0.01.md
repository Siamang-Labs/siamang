# P values

## Tests

*Crosstab*

| gender | 1 | 2 | 3 | Total |
|---|---|---|---|---|
| 1 | 30 | 10 | 10 | 50 |
| 2 | 10 | 30 | 30 | 70 |
| Total | 40 | 40 | 40 | 120 |

χ² = 27.429; df = 2; p < 0.01; Cramér's V = 0.478; N = 120

*Group means*

| region | Mean | SD | Median | N |
|---|---|---|---|---|
| 1 | 1.89 | 0.729 | 1.85 | 40 |
| 2 | 2.427 | 0.747 | 2.45 | 40 |
| 3 | 2.853 | 0.789 | 2.85 | 40 |

Test = One-way ANOVA; F = 16.347; df = 2, 117; p < 0.01; η² = 0.218; Post-hoc = Tukey HSD: 3 of 3 pairs differ at p < 0.05; N = 120; Variable = other

**Post-hoc: Tukey HSD**

| Pair | Difference | 95% CI low | 95% CI high | q | p |
|---|---|---|---|---|---|
| 1 vs 2 | -0.537 | -0.937 | -0.136 | 4.495 | < 0.01 |
| 1 vs 3 | -0.963 | -1.364 | -0.563 | 8.069 | < 0.01 |
| 2 vs 3 | -0.427 | -0.827 | -0.026 | 3.574 | 0.0341 |

Method = Tukey HSD; Groups = region; Difference = mean of the first group minus the second; p = adjusted for the number of pairs by the method itself

*t-test*

| gender | N | Mean | SD | SE |
|---|---|---|---|---|
| 1 | 50 | 2.416 | 0.997 | 0.141 |
| 2 | 70 | 3.069 | 0.903 | 0.108 |

Test = Welch's t-test (unequal variances); t = -3.676; df = 99.12; p < 0.01; Mean difference = -0.653; Difference = 1 − 2; 95% CI = -1.005 – -0.300; Cohen's d = -0.692; Hedges' g = -0.688; N = 120; Variable = score

*Correlations*

| Variable 1 | Variable 2 | r | p | p (Holm) | N |
|---|---|---|---|---|---|
| score | other | 0.608 | < 0.01 | < 0.01 | 120 |
| score | noise | 0.013 | 0.8842 | 1.0 | 120 |
| other | noise | 0.025 | 0.7841 | 1.0 | 120 |

Method = Pearson correlation; Missing = pairwise: each pair uses everyone who answered both; N = 120; p adjustment = Holm, over 3 pairs

*Regression*

| Term | Estimate | SE | t | p |
|---|---|---|---|---|
| (Intercept) | 1.097 | 0.244 | 4.49 | < 0.01 |
| other | 0.713 | 0.086 | 8.27 | < 0.01 |
| noise | -0.002 | 0.078 | -0.03 | 0.9792 |

Model = Linear (OLS); Outcome = score; N = 120; R² = 0.3692; Adjusted R² = 0.3584; Residual SE = 0.795

*Drivers*

| Driver | Beta | Beta p |
|---|---|---|
| other | 0.91 | < 0.01 |
| noise | 0.02 | 0.4121 |

Bartlett p < 0.01; Fit p = 0.2311

*Bare*

| term   | p_value   |
|:-------|:----------|
| a      | < 0.01    |
| b      | 0.0345679 |

*Kruskal-Wallis*: statistic = 12.5; p_value < 0.01; n = 120

*Proportion*: p = 0.004; lower = 0.001; upper = 0.012; n = 250

*Pairs*: posthoc = Dunn; 1 vs 3 = z = -3.108, p < 0.01
