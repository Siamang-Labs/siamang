"""Customer Pulse — NPS analysis, client deliverables, combined report."""

import dataclasses
from pathlib import Path

import numpy as np
import pandas as pd

import siamang as sg
from survey import ATTRIBUTES, channel_pref, priorities, product, survey

OUT = Path("out")
OUT.mkdir(exist_ok=True)

data = survey.simulate(n=600, seed=7)
frame = data.frame

# ── 1. Rehearse the sentinel cleanup real data will need ──────────────────────
# (simulate() never produces them, so inject a few for the rehearsal)
frame = frame.astype({"attr_support": object, "product": object, "channel_pref": object})
frame.loc[frame.sample(30, random_state=1).index, "attr_support"] = "na"      # Matrix "Not used"
frame.loc[frame.sample(20, random_state=2).index, "product"] = [
    {"code": "__other__", "text": "Desktop client"}] * 20                     # other_specify
frame.loc[frame.sample(25, random_state=3).index, "channel_pref"] = "__none__"  # none_of_above

attr_cols = [v.name for v in ATTRIBUTES]
clean = frame.copy()
# Matrix / Likert "Not applicable" answers arrive as the string "na" → NaN
clean[attr_cols] = clean[attr_cols].replace("na", np.nan).apply(pd.to_numeric)
# other_specify arrives as {"code": "__other__", "text": ...} → code 99 + a verbatim column
is_other = clean["product"].map(lambda v: isinstance(v, dict))
clean["product_other"] = clean.loc[is_other, "product"].map(lambda d: d["text"])
clean["product"] = clean["product"].map(lambda v: 99 if isinstance(v, dict) else v)
# none_of_above arrives as "__none__" → give it a real code and register the label
clean["channel_pref"] = clean["channel_pref"].replace("__none__", 0)
data = data.with_frame(clean)
data.variables["channel_pref"] = dataclasses.replace(
    channel_pref, labels={0: "None of these", **channel_pref.labels})
data.variables.add(sg.Variable("product_other", scale="nominal", label="Other product (verbatim)"))
print("errors after cleanup:", [i.code for i in data.validate() if i.severity == "error"])

# ── 2. NPS ────────────────────────────────────────────────────────────────────
data = data.recode("nps", into="nps_group", bins=[0, 7, 9, 11],
                   labels=["Detractor (0-6)", "Passive (7-8)", "Promoter (9-10)"],
                   label="NPS group")
data = data.derive(name="is_promoter", expression=data.variables["nps"].ge(9),
                   label="Promoter", labels={0: "No", 1: "Yes"})
data = data.derive(name="is_detractor", expression=data.variables["nps"].le(6),
                   label="Detractor", labels={0: "No", 1: "Yes"})
share = data.frame[["is_promoter", "is_detractor"]].mean() * 100
nps_score = round(share["is_promoter"] - share["is_detractor"], 1)
print(f"NPS = {nps_score:+}")
print(data.report.freq("nps_group").to_markdown())
print(data.report.crosstab("customer_type", "nps_group", pct="row").to_markdown())
print(data.report.means("nps", by="customer_type").to_markdown())      # interval → ANOVA
print(data.analysis.proportion_ci("is_promoter", value=1))

# NPS by segment as a plain frame (for a dashboard or a spreadsheet)
seg = (data.frame.groupby("customer_type")[["is_promoter", "is_detractor"]].mean() * 100)
seg["nps"] = (seg["is_promoter"] - seg["is_detractor"]).round(1)
seg.index = seg.index.map(data.variables["customer_type"].labels)
print(seg.round(1))

# ── 3. Attributes and priorities ──────────────────────────────────────────────
print("alpha (attributes):", round(data.scale_alpha(attr_cols), 3))
data = data.create_index("attr_index", items=attr_cols, method="mean", label="Attribute index")
print(data.analysis.spearman("attr_index", "nps"))

# Ranking answers are lists in rank order → "ranked first" and "in top 3" tables
ranks = data.frame["priorities"].dropna()
top = pd.DataFrame({
    "ranked_first_%": ranks.map(lambda r: r[0] if r else None).value_counts(normalize=True) * 100,
    "in_top3_%": ranks.explode().value_counts() / len(ranks) * 100,
}).round(1)
top.index = top.index.map(priorities.labels)
print(top.sort_values("ranked_first_%", ascending=False))

# ── 4. Deliverables ───────────────────────────────────────────────────────────
banner = data.tables.banner(rows=["nps_group", "overall_sat", "channel_pref"],
                            columns=["customer_type", "product"])
banner.export_xlsx(OUT / "pulse_banner.xlsx")
data.report.crosstab("customer_type", "nps_group", pct="row").export_xlsx(OUT / "nps_by_type.xlsx")
data.plot.bar("nps_group", palette="colorblind").save(OUT / "nps_groups.png")
data.plot.boxplot("nps", by="customer_type", show_points=True).save(OUT / "nps_by_type.png")

sample = (sg.Report(title="Sample")
          .value("Completed interviews", len(data.frame))
          .add(data.report.freq("customer_type"), caption="Customer type"))
findings = (sg.Report(title="Findings", description="Net Promoter Score and drivers")
            .value("NPS", f"{nps_score:+}")
            .add(data.report.means("nps", by="customer_type"), caption="Table 1. NPS by segment")
            .add(data.plot.heatmap(attr_cols, by="customer_type", vmin=1, vmax=5),
                 caption="Figure 1. Attribute ratings by segment")
            .add(seg.round(1), caption="Table 2. Promoters, detractors and NPS by segment"))
verbatims = (sg.Report(title="Verbatims")
             .add(data.frame.loc[is_other, ["product_other"]].head(10),
                  caption="'Other' products mentioned"))
full = sg.Report.combine([sample, findings, verbatims], title="Customer Pulse 2026 — report")
full.save(OUT / "pulse_report.md")
full.save(OUT / "pulse_report.html")
print(sorted(p.name for p in OUT.iterdir()))
