"""Civic Trust 2026 — analysis script.

Works on simulated data (rehearsal) or on collected data (`python analysis.py
responses.csv`). Produces weighted tables, a banner, charts, a report and exports.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

import siamang as sg
from codebook import ACTIVITIES, TRUST_ITEMS, variables
from helpers import rake
from survey import survey

OUT = Path("out")
OUT.mkdir(exist_ok=True)


# ── 1. Load ────────────────────────────────────────────────────────────────────
if len(sys.argv) > 1:                                    # collected responses
    frame = pd.read_csv(sys.argv[1])
    data = sg.SurveyData(frame=frame, variables=variables, questionnaire=survey)
else:                                                    # rehearsal on synthetic data
    data = survey.simulate(n=1000, seed=42)

# Keep eligible, complete interviews only.
f = data.frame
complete = (f["consent"] == 1) & (f["age"] >= 18) & (f["region"] != 99)
data = data.with_frame(f[complete].reset_index(drop=True))
print(f"Analysis base: {len(data.frame)} eligible respondents")

# ── 2. Validate against the codebook, then neutralise declared missing codes ──
issues = data.validate()
print("validation errors:", [i.code for i in issues if i.severity == "error"])
# describe_variables() cannot summarise list-valued cells (array-mode MultiChoice) — drop them.
scalar = data.with_frame(data.frame.drop(columns=["news_sources"]))
print(scalar.describe_variables().head(8).to_string())

# Cronbach's alpha and the trust index are computed *after* "Don't know" (98) and
# "Prefer not to say" (99) have become NA — otherwise 98 would count as a very high score.
clean = data.apply_missing_values()
trust_cols = [v.name for v in TRUST_ITEMS]
# replace() leaves object-dtype columns behind; make the items numeric again for charts/stats.
clean = clean.with_frame(clean.frame.assign(**{c: pd.to_numeric(clean.frame[c]) for c in trust_cols}))
print("Cronbach's alpha (trust battery):", round(clean.scale_alpha(trust_cols), 3))
clean = clean.create_index("trust_index", items=trust_cols, method="mean",
                           label="Institutional trust index (1-5)")

# Age bands as a registered ordinal variable (bins are [a, b) — last edge is exclusive).
clean = clean.recode("age", into="age_band", bins=[18, 30, 45, 65, 100],
                     labels=["18-29", "30-44", "45-64", "65+"], label="Age band")


# ── 3. Post-stratification weights (raking helper from helpers.py) ─────────────
CENSUS = {
    "region": {1: 0.31, 2: 0.24, 3: 0.27, 4: 0.18},
    "age_band": {1: 0.19, 2: 0.26, 3: 0.33, 4: 0.22},
}
weighted = clean.with_frame(clean.frame.assign(w=rake(clean.frame, CENSUS)))
weighted.variables.add(sg.Variable("w", scale="ratio", label="Raking weight", role="weight"))
weighted = weighted.with_weight("w")
print("Effective sample size (Kish):", round(weighted.analysis.effective_sample_size(), 1),
      "of", len(weighted.frame))

# ── 4. Tables ──────────────────────────────────────────────────────────────────
# Labeled, publication-ready tables (always unweighted)
print(weighted.report.freq("trust_govt").to_markdown())
xt = weighted.report.crosstab("region", "trust_govt", pct="row")
print(xt.to_markdown())
print(weighted.report.means("trust_index", by="age_band").to_markdown())   # ANOVA (interval)
print(weighted.report.means("interest", by="region").to_markdown())        # Kruskal-Wallis

# Weighted statistics live on the analysis accessor
print(weighted.analysis.frequencies("trust_govt", labels=True, weighted=True, normalize=True))
tab, stats = weighted.analysis.crosstab("region", "trust_govt", normalize="index",
                                        chi2=True, cramers_v=True, weighted=True, labels=True)
print(stats)
print(weighted.analysis.proportion_ci("trust_govt", value=5, weighted=True))
print(weighted.analysis.grouped_mean("trust_index", by="region", weighted=True, labels=True))

# Wide MultiChoice: one 0/1 column per activity → a "mentions" table
acts = [v.name for v in ACTIVITIES]
mentions = (weighted.frame[acts].mean() * 100).round(1).rename("percent").to_frame()
mentions.index = [variables[a].label for a in acts]
print(mentions)

# Array MultiChoice: explode the list column into a long table of mentions
long = weighted.frame[["news_sources"]].explode("news_sources").dropna()
base = weighted.frame["news_sources"].map(lambda s: isinstance(s, list) and len(s) > 0).sum()
news = (long["news_sources"].value_counts().rename("n").to_frame()
        .assign(percent=lambda t: (t["n"] / base * 100).round(1)))
news.index = news.index.map(variables["news_sources"].labels)
print(news)

# Banner for the appendix (weighted automatically via with_weight)
banner = weighted.tables.banner(rows=["trust_govt", "interest"], columns=["region", "age_band"])
banner.export_xlsx(OUT / "banner.xlsx")

# ── 5. Charts and report ───────────────────────────────────────────────────────
report = (
    sg.Report(title="Civic Trust 2026 — topline", description="Wave 1, weighted to census margins")
    .heading("Sample")
    .value("Eligible respondents", len(weighted.frame))
    .value("Effective sample size", round(weighted.analysis.effective_sample_size()))
    .add(weighted.report.freq("region"), caption="Table 1. Region (unweighted)")
    .heading("Trust in institutions")
    .add(weighted.report.means("trust_index", by="age_band"),
         caption="Table 2. Trust index by age band")
    .add(weighted.plot.bar("trust_index", by="region", palette="colorblind"),
         caption="Figure 1. Mean trust index by region")
    .add(weighted.plot.heatmap(trust_cols, by="region", vmin=1, vmax=5),
         caption="Figure 2. Mean trust per institution and region")
    .note("Estimates in the text are weighted; tables are unweighted counts.")
)
report.save(OUT / "topline.md")
report.save(OUT / "topline.html")

# ── 6. Exports ─────────────────────────────────────────────────────────────────
# SPSS/Stata cannot store list-valued cells — drop the array-mode column first.
flat = weighted.with_frame(weighted.frame.drop(columns=["news_sources"]))
flat.export("spss", path=str(OUT / "civic_trust.sav"))
flat.export("stata", path=str(OUT / "civic_trust.dta"))
flat.export("csv", path=str(OUT / "civic_trust.csv"))
flat.export_dictionary(str(OUT / "civic_trust_dict.json"))
flat.export("r", path=str(OUT / "civic_trust_R"))
print(sorted(p.name for p in OUT.iterdir()))
