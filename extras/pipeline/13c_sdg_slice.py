"""Descriptive slice by Sustainable Development Goal (the SDG slice counts a DPG under every goal it lists and is descriptive).

Each certified DPG lists the SDGs it serves in the DPGA registry; a DPG is counted under EVERY SDG it lists,
so the groups overlap and do not sum to the total. Sample: the high-confidence DPGs (only high-confidence repositories and DPGs feed the main results).

Per SDG:
  dpgs                 high-confidence DPGs listing that SDG
  dormant              of those, DPGs with no merged change and no release in 12 months (a repository is dormant with no merged PR or release in 12 months, slowing with fewer than half as many events as in the 12 months before, otherwise active, data/dpg_status.csv)
  ai_since_2024        DPGs with at least one merged AI-feature PR since 2024-01-01 (the text measures (merged PRs and release notes) are the main AI-feature measure, data/ai_feature_prs.csv)
  core_2023, core_2026 sum over DPGs of their mean core contributors per quarter (a core contributor is a person active in at least 2 of the 3 months of a quarter) in 2023 and in 2026Q1-Q3,
                       for DPGs with quarterly data in both periods (n_both); change = core_2026 / core_2023 - 1
Groups with fewer than 15 DPGs are flagged small (noisy).

Run: python -I scripts/13c_sdg_slice.py  ->  docs/post/findings_tables/t9_sdg.csv
"""
import re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
NAMES = {1: "No poverty", 2: "Zero hunger", 3: "Good health and well-being", 4: "Quality education", 5: "Gender equality",
         6: "Clean water and sanitation", 7: "Affordable and clean energy", 8: "Decent work and economic growth",
         9: "Industry, innovation and infrastructure", 10: "Reduced inequalities", 11: "Sustainable cities and communities",
         12: "Responsible consumption and production", 13: "Climate action", 14: "Life below water", 15: "Life on land",
         16: "Peace, justice and strong institutions", 17: "Partnerships for the goals"}

# SDG list per DPG, from the cleaned registry map (one row per DPG-repo; the sdgs text repeats per DPG)
m = pd.read_csv(ROOT / "data/dpg_repo_map.csv")[["dpgid", "sdgs"]].drop_duplicates("dpgid")
sd = pd.DataFrame([(r.dpgid, int(n)) for r in m.itertuples() for n in re.findall(r"SDG\s*(\d+)", str(r.sdgs))],
                  columns=["dpgid", "sdg"]).drop_duplicates()

conf = pd.read_csv(ROOT / "data/dpg_confidence.csv")
high = set(conf[conf.dpg_confidence == "high"].dpgid)
status = pd.read_csv(ROOT / "data/dpg_status.csv")
status = status[(status.repo_set == "high") & status.dpgid.isin(high)][["dpgid", "status"]]
ai = set(pd.read_csv(ROOT / "data/ai_feature_prs.csv").query("confidence == 'high' and merged_at >= '2024'").dpgid)

q = pd.read_csv(ROOT / "data/dpg_quarterly.csv")
core23 = q[q.quarter.between("2023Q1", "2023Q4")].groupby("dpgid").core_team_dpg.mean()
core26 = q[q.quarter.between("2026Q1", "2026Q3")].groupby("dpgid").core_team_dpg.mean()  # 2026Q4 is partial: excluded

d = sd[sd.dpgid.isin(high)].merge(status, on="dpgid", how="left")
rows = []
for k, g in d.groupby("sdg"):
    ids = set(g.dpgid)
    both = core23.index.intersection(core26.index).intersection(list(ids))
    a, b = core23[both].sum(), core26[both].sum()
    rows.append({"sdg": k, "sdg_name": NAMES.get(k, ""), "dpgs": len(ids),
                 "dormant": int((g.status == "dormant").sum()), "dormant_share": round((g.status == "dormant").mean(), 3),
                 "ai_since_2024": len(ids & ai), "ai_share": round(len(ids & ai) / len(ids), 3),
                 "n_both": len(both), "core_2023": round(a, 1), "core_2026": round(b, 1),
                 "core_change": round(b / a - 1, 3) if a else None, "small_group": len(ids) < 15})
out = pd.DataFrame(rows).sort_values("dpgs", ascending=False)
out.to_csv(ROOT / "docs/post/findings_tables/t9_sdg.csv", index=False)
print(out.to_string(index=False))
