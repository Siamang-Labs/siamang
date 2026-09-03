"""Message Framing Experiment — balance checks, treatment effects, report."""

from pathlib import Path

import numpy as np
import pandas as pd

import siamang as sg
from survey import survey

OUT = Path("out")
OUT.mkdir(exist_ok=True)

# ── 1. Rehearsal data: simulate() runs no scripts, so assign the arm in pandas ─
data = survey.simulate(n=400, seed=11)
rng = np.random.default_rng(11)
frame = data.frame.assign(condition=rng.choice([1, 2], size=len(data.frame)))
# fake a small effect so the report has something to show
frame.loc[frame["condition"] == 2, "support"] = (
    frame.loc[frame["condition"] == 2, "support"].clip(upper=6) + 1)
data = data.with_frame(frame)
print(data.report.freq("condition").to_markdown())        # labels come from the registry

# ── 2. Exclusions: failed attention checks ────────────────────────────────────
n0 = len(data.frame)
data = data.with_frame(data.frame[data.frame["attention"] == 3].reset_index(drop=True))
print(f"attention check: kept {len(data.frame)} of {n0}")

# ── 3. Randomisation / balance check ─────────────────────────────────────────
print(data.report.crosstab("condition", "gender", pct="row").to_markdown())   # chi² ≈ n.s.
print(data.report.means("age", by="condition").to_markdown())                # t-test

# ── 4. Treatment effects ──────────────────────────────────────────────────────
print(data.report.means("support", by="condition").to_markdown())   # ordinal → Mann-Whitney
print(data.report.means("donate", by="condition").to_markdown())    # ratio → t-test
print(data.analysis.mannwhitney("support", "condition"))
data = data.derive(name="supports", expression=data.variables["support"].ge(5),
                   label="Supports the policy (5-7)", labels={0: "No", 1: "Yes"})
for arm in (1, 2):
    arm_data = data.with_frame(data.frame[data.frame["condition"] == arm])
    ci = arm_data.analysis.proportion_ci("supports", value=1)
    print(f"arm {arm}: support {ci['p']:.1%} [{ci['lower']:.1%}, {ci['upper']:.1%}]")
print(data.report.means("manip_check", by="condition").to_markdown())   # manipulation check

# ── 5. Report ─────────────────────────────────────────────────────────────────
report = (
    sg.Report(title="Framing experiment — results", description="Between-subjects, 2 arms")
    .heading("Design")
    .value("Analysed respondents", len(data.frame))
    .add(data.report.crosstab("condition", "gender"), caption="Table 1. Balance: gender by arm")
    .heading("Effects")
    .add(data.report.means("support", by="condition"), caption="Table 2. Policy support by arm")
    .add(data.plot.boxplot("support", by="condition", show_points=True),
         caption="Figure 1. Support by arm")
    .add(data.report.crosstab("condition", "supports", pct="row"),
         caption="Table 3. Share supporting the policy by arm")
    .note("Respondents failing the attention check were excluded before analysis.")
)
report.save(OUT / "framing_report.md")
print(sorted(p.name for p in OUT.iterdir()))
