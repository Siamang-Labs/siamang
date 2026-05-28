"""Step 3: Statistical Analysis and Reporting.

This script loads the collected (simulated) data and performs a comprehensive
sociological and statistical analysis using the Siamang Analysis Engine.
It covers:
1. Univariate frequencies and descriptive statistics.
2. Bivariate analysis: crosstabs, Chi-square test, and Cramer's V.
3. Grouped means and non-parametric tests (Kruskal-Wallis).
4. Generating data visualizations and saving them as images.
5. Exporting high-quality cross-tabulation reports (Banner Tables) to Excel.
"""

from __future__ import annotations

import os
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from examples.full_pipeline.step1_survey_design import variables
from siamang.data.survey_data import SurveyData


def main() -> None:
    # ═══════════════════════════════════════════════════════════════════════════════
    # 1. LOAD DATA & INITIALIZE SURVEY DATA CONTAINER
    # ═══════════════════════════════════════════════════════════════════════════════
    print("--- 1. Loading and Validating Data ---")
    data_path = "data/simulated_responses.csv"
    if not os.path.exists(data_path):
        raise FileNotFoundError(
            f"Simulated data not found at '{data_path}'. Please run step 2 first!"
        )

    df = pd.read_csv(data_path)

    # Wrap the pandas DataFrame in Siamang's SurveyData container
    # This attaches the VariableMap codebook metadata for automatic validation
    survey_data = SurveyData(frame=df, variables=variables)

    # Validate data against the codebook schema
    issues = survey_data.validate()
    if not issues:
        print("✓ Data matches codebook specifications perfectly!")
    else:
        print(f"⚠ Found {len(issues)} data validation issues:")
        for issue in issues:
            print(f"  - [{issue.severity.upper()}] {issue.message}")

    # ═══════════════════════════════════════════════════════════════════════════════
    # 2. UNIVARIATE FREQUENCIES (Descriptive Statistics)
    # ═══════════════════════════════════════════════════════════════════════════════
    print("\n--- 2. Univariate Descriptive Analysis ---")

    # Get frequencies of IT Roles with category labels
    role_freq = survey_data.analysis.frequencies("it_role", normalize=True, labels=True)
    print("\nIT Professional Roles Distribution:")
    print(role_freq)

    # Get frequencies of Remote Work Frequency
    remote_freq = survey_data.analysis.frequencies("remote_freq", normalize=True, labels=True)
    print("\nRemote Work Frequency Distribution:")
    print(remote_freq)

    # ═══════════════════════════════════════════════════════════════════════════════
    # 3. BIVARIATE ANALYSIS & STATISTICAL TESTING
    # ═══════════════════════════════════════════════════════════════════════════════
    print("\n--- 3. Bivariate Analysis & Hypothesis Testing ---")

    # Cross-tabulate IT Role by Remote Work Frequency
    # Hypothesis: Software developers and data scientists have higher remote work frequency.
    ct, stats = survey_data.analysis.crosstab(
        row="it_role",
        col="remote_freq",
        normalize="index",  # Percentages within each role
        chi2=True,
        cramers_v=True,
        labels=True,
    )
    print("\nCrosstab: Remote Work Frequency by IT Role (Row %):")
    print(ct.round(3) * 100)
    print("\nAssociation Statistics:")
    print(f"  - Chi-Square: {stats['chi2']:.3f} (p-value: {stats['p_value']:.5f})")
    print(f"  - Cramer's V: {stats['cramers_v']:.3f}")

    # Grouped Mean: Workplace Autonomy by Remote Work Frequency
    # Hypothesis: Higher remote work frequency is associated with higher perceived autonomy.
    autonomy_by_remote = survey_data.analysis.grouped_mean(
        column="autonomy",
        by="remote_freq",
        labels=True,
    )
    print("\nMean Autonomy Score by Remote Work Frequency (Scale 1-5):")
    print(autonomy_by_remote)

    # Non-parametric test (Kruskal-Wallis) to see if autonomy differences are significant
    kw_stats = survey_data.analysis.kruskal("autonomy", "remote_freq")
    print("\nKruskal-Wallis Test (Autonomy ~ Remote Frequency):")
    print(f"  - H-Statistic: {kw_stats['statistic']:.3f}")
    print(f"  - p-value: {kw_stats['p_value']:.5f}")

    # ═══════════════════════════════════════════════════════════════════════════════
    # 4. DATA VISUALIZATION
    # ═══════════════════════════════════════════════════════════════════════════════
    print("\n--- 4. Generating Data Visualizations ---")
    os.makedirs("reports", exist_ok=True)

    # Plot 1: Workplace Autonomy by Remote Work Frequency
    plt.figure(figsize=(10, 6))
    sns.set_theme(style="whitegrid")
    sns.boxplot(
        data=df,
        x="remote_freq",
        y="autonomy",
        palette="viridis",
    )
    # Replace numeric tick labels with categories
    remote_labels = [variables["remote_freq"].labels[i] for i in sorted(variables["remote_freq"].labels.keys())]
    plt.xticks(ticks=range(len(remote_labels)), labels=remote_labels, rotation=15)
    plt.title("Workplace Autonomy by Remote Work Frequency", fontsize=14, fontweight="bold")
    plt.xlabel("Remote Work Frequency")
    plt.ylabel("Perceived Autonomy (1-5)")
    plt.tight_layout()

    plot_path = "reports/autonomy_by_remote.png"
    plt.savefig(plot_path, dpi=300)
    plt.close()
    print(f"✓ Saved boxplot to '{plot_path}'")

    # ═══════════════════════════════════════════════════════════════════════════════
    # 5. BANNER TABLES & EXCEL REPORT EXPORT
    # ═══════════════════════════════════════════════════════════════════════════════
    print("\n--- 5. Generating Professional Excel Crosstab Reports ---")

    # Build a comprehensive Banner Table (cross-tabulation of multiple variables at once)
    # Rows represent dependent variables (satisfaction, autonomy)
    # Columns represent independent variables / banners (it_role, remote_freq)
    banner_report = survey_data.tables.banner(
        rows=["satisfaction", "autonomy"],
        columns=["it_role", "remote_freq"],
        labels=True,
    )

    excel_path = "reports/it_workplace_banner_report.xlsx"
    banner_report.export_xlsx(excel_path)
    print(f"✓ Exported professional banner crosstab report to '{excel_path}'")


if __name__ == "__main__":
    main()
