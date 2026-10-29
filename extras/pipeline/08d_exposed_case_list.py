"""One-page list of the exposed DPGs (primary definition, score 2-3) for the case-study section.
Inputs: data/funding_flags.csv, data/funding_flags_awards.csv, data/analysis_sample.csv, data/donor_flags.csv (terminated_award, when DON has merged it).
Outputs: data/exposed_dpgs_case_list.md, data/exposed_dpgs_case_list.csv
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
ff = pd.read_csv(ROOT / "data/funding_flags.csv")
ev = pd.read_csv(ROOT / "data/funding_flags_awards.csv")
sa = pd.read_csv(ROOT / "data/analysis_sample.csv")[["dpgid", "in_joint_test", "dpg_confidence", "owner_type", "owner_country"]]
dn = pd.read_csv(ROOT / "data/donor_flags.csv")[["dpgid", "terminated_award"]]
x = ff[ff.exposed == 1].merge(sa, on="dpgid").merge(dn, on="dpgid", how="left").sort_values(["exposure_score", "dpg"], ascending=[False, True])

def money(v): return f"${v/1e6:.1f}M" if abs(v) >= 1e6 else f"${v/1e3:.0f}k"
def term(v): return "pending (DON join)" if pd.isna(v) or v == "" else str(v)

rows, md = [], ["# Exposed DPGs (primary definition: score 2 or 3)", "",
    "Exposure = a US foreign-aid award (USAID, State, MCC, CDC) to the DPG's owner active between 2022-10-01 and 2025-01-19. "
    "Score 3 = a direct (prime) award; score 2 = a subaward passed through another organisation. "
    "Dollar figures are the full face value of each award, **not prorated to the window**. US federal money only: non-US donors are not included here. "
    "Owner and recipient matches are provisional until the independent check rechecks the rebuilt rows. A DPG with no award found is scored 0, which can also mean an unreported subaward.", ""]
for r in x.itertuples():
    a = ev[ev.dpgid == r.dpgid].head(3)
    awards = []
    for t in a.itertuples():
        via = f" via {t.prime_recipient.title()}" if t.tier == "subaward" and isinstance(t.prime_recipient, str) else ""
        desc = (t.description or "")[:80].strip() if isinstance(t.description, str) else ""
        span = f"{str(t.start)[:7]}-{str(t.end)[:7]}" if isinstance(t.end, str) else str(t.start)[:7]
        awards.append(f"{t.tier} {t.prime_award_id or t.award_id} ({t.sub_agency if t.agency == 'Department of Health and Human Services' else t.agency}{via}, {span}, {money(t.amount)}){': ' + desc if desc else ''}")
    flags = []
    if not r.in_joint_test: flags.append(f"not in joint sample (repo confidence: {r.dpg_confidence})")
    if r.check_purchase_order_only: flags.append("**check: the only foreign-aid award is a purchase order, likely a product sale**")
    md += [f"## {r.dpg}", f"- Owner: {r.owner_name} ({r.owner_type}, {r.owner_country}); score {int(r.exposure_score)}; "
           f"{int(r.n_fa_prime)} prime and {int(r.n_fa_subaward)} sub awards active; about {money(r.fa_usd_window_unprorated)} face value",
           "- Main awards: " + "; ".join(awards), f"- Award terminated in 2025: {term(r.terminated_award)}"] + ([f"- Note: {'; '.join(flags)}"] if flags else []) + [""]
    rows.append(dict(dpg=r.dpg, owner=r.owner_name, owner_type=r.owner_type, owner_country=r.owner_country, exposure_score=int(r.exposure_score),
                     in_joint_sample=bool(r.in_joint_test), repo_confidence=r.dpg_confidence, n_prime=int(r.n_fa_prime), n_sub=int(r.n_fa_subaward),
                     face_value_usd=int(r.fa_usd_window_unprorated), main_awards=" | ".join(awards), terminated_2025=term(r.terminated_award),
                     check_purchase_order_only=bool(r.check_purchase_order_only)))
(ROOT / "data/exposed_dpgs_case_list.md").write_text("\n".join(md), encoding="utf-8")
pd.DataFrame(rows).to_csv(ROOT / "data/exposed_dpgs_case_list.csv", index=False)
print(f"{len(rows)} exposed DPGs; in joint sample: {int(x.in_joint_test.sum())}; owners: {x.owner_name.nunique()}")
