"""Apply the inclusion rules in DESIGN.md to every DPG. Outputs:
data/analysis_sample.csv (one row per DPG: include flags for each analysis, primary and sensitivity),
data/exclusions.csv (one row per DPG x rule that excluded it). Prints the sample flow.
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
om = pd.read_csv(ROOT / "data/dpg_owner_map.csv")
em = pd.read_csv(ROOT / "data/org_ein_map.csv", dtype={"ein": str})
fin = pd.read_csv(ROOT / "data/org_990_yearly.csv", dtype={"ein": str})
base = fin[~fin.pdf_only & fin.tax_year.between(2019, 2023) & fin.total_expenses.notna()]
nyears = base.groupby("owner_name").tax_year.nunique()

df = om.merge(em[["owner_name", "ein", "confidence", "attribution"]].rename(columns={"confidence": "ein_confidence"}),
              on="owner_name", how="left")
df["baseline_990_years"] = df.owner_name.map(nyears).fillna(0).astype(int)
# repo confidence tier from the activity workstream (METHODOLOGY D14)
dc = pd.read_csv(ROOT / "data/dpg_confidence.csv")[["dpgid", "dpg_confidence"]]
df = df.merge(dc, on="dpgid", how="left")
# federal-award exposure (F6, DESIGN B); blank score = owner low confidence, so the DPG has no exposure value (rule B1)
ff = pd.read_csv(ROOT / "data/funding_flags.csv")[["dpgid", "exposure_score", "exposed", "exposure_score_sens", "exposed_sens", "check_purchase_order_only"]]
df = df.merge(ff, on="dpgid", how="left")
df["dpg_confidence"] = df.dpg_confidence.fillna("no_usable_repo")

# (rule, stage, test for primary, test for sensitivity, reason); tests return True when the DPG passes
OWNER_OK = df.confidence.isin(["high", "medium"]) & df.owner_type.ne("UNKNOWN")
RULES = [
    ("A1", "funding_990", OWNER_OK, OWNER_OK, "owner identification low confidence"),
    ("A2", "funding_990", df.owner_type.eq("USNP"), df.owner_type.eq("USNP"), "owner not a US nonprofit (no 990)"),
    ("A3", "funding_990", df.ein_confidence.eq("high"), df.ein_confidence.isin(["high", "medium"]), "EIN match below threshold"),
    ("A4", "funding_990", df.attribution.isin(["direct", "partial"]), df.attribution.isin(["direct", "partial", "parent"]),
     "org finances not attributable to the DPG (parent/host)"),
    ("A5", "funding_990", df.baseline_990_years.ge(3), df.baseline_990_years.ge(3), "fewer than 3 baseline 990 years (2019-2023)"),
    ("B1", "exposure", OWNER_OK, OWNER_OK, "owner identification low confidence"),
    # joint funding x activity test: exposure rules AND repo confidence (DESIGN "Joint sample"); B2/B3 join here once
    # data/funding_flags.csv exists
    ("B1", "joint_test", OWNER_OK, OWNER_OK, "owner identification low confidence"),
    ("D14", "joint_test", df.dpg_confidence.eq("high"), df.dpg_confidence.isin(["high", "medium"]),
     "repo confidence below threshold (METHODOLOGY D14)"),
]

exc = []
for stage in dict.fromkeys(r[1] for r in RULES):
    prim = pd.Series(True, index=df.index); sens = prim.copy()
    for rid, st, p, s, why in (r for r in RULES if r[1] == stage):
        for i in df.index[prim & ~p]:  # log only the first rule that drops a case in the primary sample
            exc.append(dict(dpgid=df.dpgid[i], dpg=df.dpg[i], owner_name=df.owner_name[i], analysis=stage, rule=rid,
                            reason=why, back_in_sensitivity=bool(sens[i] and s[i])))
        prim &= p; sens &= s
    df[f"in_{stage}"] = prim
    df[f"in_{stage}_sens"] = sens

df.drop(columns=["notes", "related_orgs"]).to_csv(ROOT / "data/analysis_sample.csv", index=False)
ex = pd.DataFrame(exc)
ex.to_csv(ROOT / "data/exclusions.csv", index=False)
for stage in ex.analysis.unique():
    print(f"\n{stage}: start {len(df)} DPGs")
    for rid, n in ex[ex.analysis == stage].groupby("rule").size().items():
        print(f"  {rid} drops {n}")
    print(f"  analysed (primary): {df[f'in_{stage}'].sum()} DPGs, {df[df[f'in_{stage}']].owner_name.nunique()} orgs; "
          f"sensitivity: {df[f'in_{stage}_sens'].sum()} DPGs")
