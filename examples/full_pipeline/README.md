# Siamang Full Research Pipeline Example

This folder contains a comprehensive, step-by-step example of a complete sociological research pipeline using the **Siamang** library [1]. The pipeline covers the entire lifecycle of a survey-based study: from defining research variables and designing the questionnaire to simulating responses, local deployment, and executing statistical analyses [2].

## Research Scenario

We explore **attitudes toward remote work, workplace autonomy, and digital monitoring/surveillance** among IT professionals. 
The study addresses several key sociological hypotheses:
1. **The Autonomy-Surveillance Paradox**: While remote work increases subjective workplace autonomy, it is often accompanied by more invasive digital tracking (e.g., keystroke logging, webcam tracking), which in turn reduces job satisfaction [3].
2. **Professional Stratification**: Different roles within the IT industry (e.g., Software Engineers vs. Product Managers) experience varying levels of remote work flexibility and monitoring pressure [4].

---

## Pipeline Structure

The pipeline is split into three executable Python scripts, representing the standard workflow of a quantitative social researcher [2]:

| Step | Script | Key Concepts Demonstrated |
| :--- | :--- | :--- |
| **Step 1** | [`step1_survey_design.py`](step1_survey_design.py) | Variable definitions (scales, missing values), Page & Block layout, complex routing logic (`show_if`). |
| **Step 2** | [`step2_deploy_and_collect.py`](step2_deploy_and_collect.py) | Synthetic response simulation (for pre-testing analytical code), local development server deployment, programmatic data collection. |
| **Step 3** | [`step3_statistical_analysis.py`](step3_statistical_analysis.py) | Data validation, univariate frequencies, bivariate crosstabs, Chi-square test, Cramer's V, non-parametric tests (Kruskal-Wallis), plotting, and Excel report export. |

---

## How to Run the Pipeline

### 1. Survey Design & Validation
Run Step 1 to validate the survey structure and view a text-based preview of the questionnaire:
```bash
python3 -m examples.full_pipeline.step1_survey_design
```

### 2. Simulate and Deploy
Run Step 2 to generate 250 simulated survey responses (respecting all logical routing rules like `show_if`) and save them to `data/simulated_responses.csv`:
```bash
python3 -m examples.full_pipeline.step2_deploy_and_collect
```

### 3. Analyze Data & Generate Reports
Run Step 3 to perform statistical tests, plot a boxplot of autonomy by remote work frequency, and export a professional multi-variable cross-tabulation report (Banner Table) to Excel:
```bash
python3 -m examples.full_pipeline.step3_statistical_analysis
```

---

## Key Outputs Generated

After running the complete pipeline, the following folders and files will be created in your workspace:
* `data/simulated_responses.csv`: Raw dataset containing 250 simulated respondents.
* `reports/autonomy_by_remote.png`: A high-quality boxplot visualizing how workplace autonomy varies across different remote work arrangements.
* `reports/it_workplace_banner_report.xlsx`: A publication-ready, styled Excel spreadsheet featuring cross-tabulations of satisfaction and autonomy against demographic and professional banner columns.

---

## References

1. Siamang Team. *Siamang: A Research-as-Code Framework for Sociological Surveys*. Siamang Documentation, 2026.
2. Manus AI. *Technical Architecture and Deployment Pipeline of Siamang*. Siamang Reference, 2026.
3. Sewell, Graham, and Barker, James R. *Coercion, Consent, and the Paradox of Cyber-Surveillance in the Contemporary Workplace*. Human Relations, 59(7), 2006.
4. Kalleberg, Arne L. *Good Jobs, Bad Jobs: The Rise of Polarized and Precarious Employment Systems in the United States, 1970s to 2000s*. Russell Sage Foundation, 2011.
