"""N2 join (this part of the study): fill terminated_award in data/donor_flags.csv.
Joins the funding analysis's per-DPG award evidence (data/funding_flags_awards.csv) to data/usg_terminations.csv (ITPC list, 6 Mar 2025) on
the prime award ID (a subaward is terminated when its prime is). Exact match after upper-casing/stripping only.
Values: 'yes: <ids>' = >=1 evidence award on the terminated list; 'on list, active: <ids>' = only on the active list;
'no match' = evidence awards but none on the list (list is USAID/State only and a March snapshot); '' = no awards.
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
ev = pd.read_csv(ROOT / "data/funding_flags_awards.csv")
t = pd.read_csv(ROOT / "data/usg_terminations.csv")
norm = lambda s: s.astype(str).str.upper().str.strip()
t["k"] = norm(t.award_id)
st = t.groupby("k").status.agg(lambda x: "terminated" if (x == "terminated").any() else "active").to_dict()
ev["pk"] = norm(ev.prime_award_id.fillna(ev.award_id))
ev["ak"] = norm(ev.award_id)
ev["status"] = ev.pk.map(st).fillna(ev.ak.map(st))
ev["key"] = ev.pk.where(ev.pk.isin(st), ev.ak)
def label(g):
    term = sorted(set(g[g.status == "terminated"].key)); act = sorted(set(g[g.status == "active"].key))
    if term: return f"yes: {', '.join(term[:3])}" + (f" (+{len(term)-3} more)" if len(term) > 3 else "")
    if act: return f"on list, active: {', '.join(act[:3])}"
    return "no match"
lab = ev.groupby("dpgid").apply(label, include_groups=False)
df = pd.read_csv(ROOT / "data/donor_flags.csv")
df["terminated_award"] = df.dpgid.map(lab).fillna("")
df["terminated_award_n"] = df.dpgid.map(ev[ev.status == "terminated"].groupby("dpgid").key.nunique()).fillna(0).astype(int)
df.to_csv(ROOT / "data/donor_flags.csv", index=False)
print("evidence rows:", len(ev), "| matched to list:", ev.status.notna().sum(), "| DPGs with evidence:", ev.dpgid.nunique())
print(df.terminated_award.str.split(":").str[0].replace("", "(no awards)").value_counts().to_dict())
