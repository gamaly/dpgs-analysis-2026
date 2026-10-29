"""N3 : one row per dpgid -> data/donor_flags.csv (hand-off to the funding analysis; robustness input, METHODOLOGY D24).

nonus_exposed       1 if >=1 'high' IATI activity (DESIGN E: exact name, implementing/extending role, in window, work fits).
nonus_exposed_sens  1 if >=1 high or medium activity (adds partial-fit, variant names, UN/GOV/UNIV/parent-scale owners).
terminated_award    blank until FIN's data/org_awards_usg.csv exists (N2 join on award ID).
Zero means 'none found', not 'none exist': IATI is incomplete for foundations and UN agencies.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
om = pd.read_csv(ROOT / "data/dpg_owner_map.csv")
a = pd.read_csv(ROOT / "data/donor_awards_nonus.csv")
a = a[a.in_window]
big = set(pd.read_csv(ROOT / "cache/iati/_skipped_big.csv").name)
out = om[["dpgid", "dpg", "owner_name", "owner_type", "confidence"]].rename(columns={"confidence": "owner_conf"})


def agg(df, tag):
    g = df.groupby("dpgid")
    return pd.DataFrame({
        f"n_act_{tag}": g.iati_id.nunique(),
        f"donors_{tag}": g.reporting_org.agg(lambda x: "; ".join(sorted(set(x))[:6])),
    })


hi = a[a.tier_final == "high"]
sens = a[a.tier_final.isin(["high", "medium"])]
out = out.merge(agg(hi, "high"), how="left", on="dpgid").merge(agg(sens, "sens"), how="left", on="dpgid")
for c in ("n_act_high", "n_act_sens"):
    out[c] = out[c].fillna(0).astype(int)
out["nonus_exposed"] = (out.n_act_high > 0).astype(int)
out["nonus_exposed_sens"] = (out.n_act_sens > 0).astype(int)
cut = a[a.tier_final.isin(["high", "medium"]) & a.cut_2025].groupby("dpgid").iati_id.nunique()
out["cut_2025_activities"] = out.dpgid.map(cut).fillna(0).astype(int)
out["terminated_award"] = ""  # N2 join waits on FIN F5
out["owner_searched_big_body"] = out.owner_name.isin(big).astype(int)
out["caveat"] = "IATI incomplete for foundations/UN; zero = none found. Owner conf low/medium carries through."
out["source"] = "IATI Datastore 2026-10-29; hand fit review data/donor_fit_review.csv"
out.to_csv(ROOT / "data/donor_flags.csv", index=False)
print(len(out), "DPGs | exposed(high):", out.nonus_exposed.sum(), "| exposed(sens):", out.nonus_exposed_sens.sum(),
      "| with 2025 cut activity:", (out.cut_2025_activities > 0).sum(), "| owner is skipped big body:", out.owner_searched_big_body.sum())
