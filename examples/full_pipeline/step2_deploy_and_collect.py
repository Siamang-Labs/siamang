"""Step 2: Simulation, Deployment, and Data Collection.

This script demonstrates how to:
1. Simulate synthetic respondent data for pre-testing analytical code.
2. Deploy the survey locally to a development server.
3. Collect submitted responses programmatically.
"""

from __future__ import annotations

import os
from examples.full_pipeline.step1_survey_design import survey


def main() -> None:
    # ═══════════════════════════════════════════════════════════════════════════════
    # 1. SURVEY SIMULATION (Pre-testing)
    # ═══════════════════════════════════════════════════════════════════════════════
    print("--- 1. Simulating Survey Responses ---")
    # Simulate 250 respondents with random seed for reproducibility.
    # The simulator respects all conditional routing logic (show_if/hide_if).
    survey_data = survey.simulate(n=250, seed=42)

    # Save the simulated data to CSV for analysis
    os.makedirs("data", exist_ok=True)
    simulated_path = "data/simulated_responses.csv"
    survey_data.frame.to_csv(simulated_path, index=False)
    print(f"✓ Generated 250 simulated responses and saved to '{simulated_path}'")
    print(f"DataFrame Shape: {survey_data.frame.shape}")

    # Describe variables in the dataset
    desc_df = survey_data.describe_variables()
    print("\nVariable Summary from Simulation:")
    print(desc_df[["name", "scale", "n", "n_missing"]])

    # ═══════════════════════════════════════════════════════════════════════════════
    # 2. LOCAL DEPLOYMENT (Demonstration)
    # ═══════════════════════════════════════════════════════════════════════════════
    print("\n--- 2. Survey Deployment ---")
    print("To deploy this survey to a local development server, you would run:")
    print("    result = survey.deploy(backend='local', frontend='local')")
    print("This spins up a local FastAPI server and builds a self-contained React frontend bundle.")

    print("\nTo deploy this survey to production (Supabase backend + Vercel static hosting):")
    print("    result = survey.deploy(backend='supabase', frontend='vercel')")

    # ═══════════════════════════════════════════════════════════════════════════════
    # 3. DATA COLLECTION
    # ═══════════════════════════════════════════════════════════════════════════════
    print("\n--- 3. Data Collection ---")
    print("Once the survey is live, you can collect responses programmatically:")
    print("    # Using the deploy result:")
    print("    df = result.collect()")
    print("    ")
    print("    # Or directly from the backend database:")
    print("    from siamang.deploy.backends.supabase import SupabaseBackend")
    print("    backend = SupabaseBackend(survey_id='it_workplace_2026')")
    print("    df = backend.get_responses()")


if __name__ == "__main__":
    main()
