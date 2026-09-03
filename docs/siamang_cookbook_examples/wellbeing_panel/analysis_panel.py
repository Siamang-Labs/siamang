"""Wellbeing Panel — combine two waves, round-trip the codebook, report the trend."""

from pathlib import Path

import numpy as np
import pandas as pd

import siamang as sg
from siamang.io import DictionaryReader, DictionaryWriter, SPSSWriter, StataWriter, read_spss, read_stata

from codebook import WB_ITEMS, panel_id
import wave1
import wave2

OUT = Path("out")
OUT.mkdir(exist_ok=True)
wb_cols = [v.name for v in WB_ITEMS]


def prepare(data: sg.SurveyData, ids: pd.Series, wave: int) -> sg.SurveyData:
    """Attach panel ids (simulate() does not run scripts) and the wave marker."""
    frame = data.frame.assign(panel_id=ids.values, wave=wave)
    data = data.with_frame(frame)
    data.variables.add(sg.Variable("wave", scale="ordinal", label="Wave",
                                   labels={1: "Wave 1", 2: "Wave 2"}))
    data = data.apply_missing_values()                 # gender 99 → NA
    data = data.with_frame(data.frame.assign(gender=pd.to_numeric(data.frame["gender"])))
    return data.create_index("who5", items=wb_cols, method="sum", label="WHO-5 score (0-25)")


# ── 1. Two waves of (simulated) responses ─────────────────────────────────────
w1 = wave1.survey.simulate(n=400, seed=1)
ids_w1 = pd.Series([f"P{i:04d}" for i in range(1, 401)])
w1 = prepare(w1, ids_w1, wave=1)

w2 = wave2.survey.simulate(n=300, seed=2)
rng = np.random.default_rng(3)
ids_w2 = pd.Series(rng.choice(ids_w1, size=300, replace=False))   # 25% attrition
w2 = prepare(w2, ids_w2, wave=2)

# ── 2. Validate each wave against its codebook (role="id" catches duplicates) ──
for name, d in (("wave 1", w1), ("wave 2", w2)):
    print(name, [i.code for i in d.validate() if i.severity == "error"])
dup = w1.with_frame(pd.concat([w1.frame, w1.frame.iloc[[0]]], ignore_index=True))
print("duplicate id →", [i.code for i in dup.validate() if i.severity == "error"])

# ── 3. Archive wave 1 with its codebook and prove the round trip ───────────────
DictionaryWriter().write(w1.variables, OUT / "panel_dictionary.json")
w1.export("csv", path=str(OUT / "wave1.csv"))
restored = sg.SurveyData(frame=pd.read_csv(OUT / "wave1.csv"),
                         variables=DictionaryReader().read(OUT / "panel_dictionary.json"))
assert restored.variables["gender"].labels == w1.variables["gender"].labels
assert restored.variables["gender"].missing_kinds_dict() == {99: "refusal"}

SPSSWriter().write(w1, OUT / "wave1.sav")
back = read_spss(str(OUT / "wave1.sav"))
print("SPSS keeps:", back.variables["wb_calm"].labels[5], "|", back.variables["life_sat"].scale,
      "| missing:", back.variables["gender"].missing_values)
StataWriter().write(w1, OUT / "wave1.dta", version=15)
back_dta = read_stata(str(OUT / "wave1.dta"))
print("Stata keeps labels:", back_dta.variables["wb_calm"].labels.get(5),
      "| numeric missing codes dropped:", back_dta.variables["gender"].missing_values)

# ── 4. Long file: both waves stacked ──────────────────────────────────────────
long_frame = pd.concat([w1.frame, w2.frame], ignore_index=True)
panel = sg.SurveyData(frame=long_frame, variables=w2.variables)   # wave-2 codebook is a superset
print(panel.report.crosstab("wave", "employment", pct="row").to_markdown())
print(panel.report.means("who5", by="wave").to_markdown())        # interval, 2 groups → t-test
print(panel.report.means("life_sat", by="wave").to_markdown())

# ── 5. Wide file: within-person change ────────────────────────────────────────
wide = (w1.frame.set_index("panel_id")[["who5", "life_sat", "employment"]]
        .join(w2.frame.set_index("panel_id")[["who5", "life_sat", "job_change"]],
              lsuffix="_w1", rsuffix="_w2", how="inner"))
wide["who5_change"] = wide["who5_w2"] - wide["who5_w1"]
print(f"panel cases: {len(wide)}, mean WHO-5 change: {wide['who5_change'].mean():+.2f}")
change = sg.SurveyData(
    frame=wide.reset_index(),
    variables=sg.VariableMap(),
)
change.variables.add_many([
    sg.Variable("who5_change", scale="interval", label="Change in WHO-5 (w2 - w1)"),
    sg.Variable("job_change", scale="nominal", label="Changed job",
                labels={1: "Yes", 2: "No"}),
])
print(change.report.means("who5_change", by="job_change").to_markdown())

# ── 6. Report per wave, combined with a table of contents ─────────────────────
def wave_report(d: sg.SurveyData, title: str) -> sg.Report:
    return (sg.Report(title=title)
            .value("Respondents", len(d.frame))
            .add(d.report.freq("employment"), caption="Employment status")
            .add(d.report.means("who5", by="employment"), caption="WHO-5 by employment"))

trend = (sg.Report(title="Trend", description="Wave 1 → Wave 2")
         .add(panel.report.means("who5", by="wave"), caption="WHO-5 score by wave")
         .add(panel.plot.boxplot("who5", by="wave"), caption="Figure 1. WHO-5 by wave")
         .add(change.report.means("who5_change", by="job_change"),
              caption="Within-person change by job change"))
full = sg.Report.combine([wave_report(w1, "Wave 1"), wave_report(w2, "Wave 2"), trend],
                         title="Wellbeing Panel — waves 1-2")
full.save(OUT / "panel_report.md")

# ── 7. Hand the long file to R ────────────────────────────────────────────────
panel.export("r", path=str(OUT / "panel_R"))
print(sorted(p.name for p in OUT.iterdir()))
