"""F6: per-DPG federal-award exposure score -> data/funding_flags.csv (hand-off to the joint test).
Rules: DESIGN.md section B, "Scoring mechanics". Inputs: data/org_awards_usg.csv, data/usg_recipient_map.csv, data/dpg_owner_map.csv.
Outputs: data/funding_flags.csv, data/funding_flags_dropped_awards.csv.
Score: 3 = active foreign-aid prime award; 2 = foreign-aid subaward only; 1 = other federal award only; 0 = none found.
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
WS, WE = pd.Timestamp("2022-10-01"), pd.Timestamp("2025-01-19")
FOREIGN_AID = {"Agency for International Development", "Department of State", "Millennium Challenge Corporation"}

aw = pd.read_csv(ROOT / "data/org_awards_usg.csv")
rm = pd.read_csv(ROOT / "data/usg_recipient_map.csv", dtype=str, keep_default_na=False)
om = pd.read_csv(ROOT / "data/dpg_owner_map.csv", dtype=str, keep_default_na=False)

aw["date_p"] = pd.to_datetime(aw.date, errors="coerce")
aw["end_p"] = pd.to_datetime(aw.end_date, errors="coerce")
prime = aw.tier.eq("prime")
# drop impossible dates (logged), then decide activity in the window
bad = (aw.date_p.isna() & ~prime) | (aw.date_p.dt.year > 2040) | (aw.end_p.dt.year > 2040) | (aw.end_p < aw.date_p) | (aw.date_p.isna() & prime)
aw.loc[bad].drop(columns=["date_p", "end_p"]).to_csv(ROOT / "data/funding_flags_dropped_awards.csv", index=False)
aw = aw[~bad].copy()
prime = aw.tier.eq("prime")
active = (prime & aw.end_p.notna() & (aw.date_p <= WE) & (aw.end_p >= WS)) | \
         (prime & aw.end_p.isna() & aw.date_p.between(WS, WE)) | (~prime & aw.date_p.between(WS, WE))
aw = aw[active].copy()
aw["foreign_aid"] = aw.agency.isin(FOREIGN_AID) | aw.sub_agency.eq("Centers for Disease Control and Prevention")

# net subaward rows per award (corrections included); a prime award stands on its face value
aw["key"] = aw.org + "|" + aw.tier + "|" + aw.prime_award_id.fillna("") + "|" + aw.award_id.fillna("")
net = aw.groupby("key").agg(org=("org", "first"), tier=("tier", "first"), attribution=("attribution", "first"),
                            map_confidence=("map_confidence", "first"), foreign_aid=("foreign_aid", "first"),
                            award_id=("award_id", "first"), prime_award_id=("prime_award_id", "first"),
                            award_kind=("award_kind", "first"), agency=("agency", "first"), sub_agency=("sub_agency", "first"), prime_recipient=("prime_recipient", "first"),
                            start=("date", "first"), end=("end_date", "first"), description=("description", "first"), amount=("amount", "sum")).reset_index()
net = net[net.amount > 0]

PRIMARY = net.map_confidence.eq("high") & net.attribution.isin(["direct", "partial"])
net["in_primary_set"] = PRIMARY

# DPG -> linked orgs (owner + related orgs named in the owner map)
links = []
for _, r in om.iterrows():
    for org in [r.owner_name] + [x.strip() for x in r.related_orgs.split(";") if x.strip()]:
        links.append((r.dpgid, org))
links = pd.DataFrame(links, columns=["dpgid", "org"]).drop_duplicates()
mapped_orgs = set(rm[rm.confidence.isin(["high", "medium"])].org)
usable = lambda df: df.drop_duplicates(["award_id", "prime_award_id", "tier"])  # same award via two linked orgs counts once

def purchase_only(fa):
    """Diagnostic only (score unchanged): every foreign-aid prime award behind a score of 3 is a purchase order.
    Contract IDs (PIIDs) carry the instrument type after the fiscal year, e.g. 75D301 23 P 17661; P = purchase order."""
    pr = fa[fa.tier == "prime"]
    is_po = pr.award_id.fillna("").map(lambda i: len(i) >= 9 and i[8] == "P") & pr.award_kind.eq("contract")
    return bool(len(pr)) and bool(is_po.all())

def score(awards):
    if awards.empty: return 0, 0, 0, 0, 0.0, "", False
    awards = usable(awards)
    fa = awards[awards.foreign_aid]
    sc = 3 if (fa.tier == "prime").any() else 2 if (fa.tier == "subaward").any() else 1
    ev = "; ".join(f"{r.org}:{r.tier}:{r.prime_award_id or r.award_id}" for r in fa.sort_values("amount", ascending=False).head(3).itertuples())
    return sc, int((fa.tier == "prime").sum()), int((fa.tier == "subaward").sum()), int((~awards.foreign_aid).sum()), float(fa.amount.sum()), ev, purchase_only(fa) and sc == 3

rows = []
for _, r in om.iterrows():
    lk = links[links.dpgid == r.dpgid].org
    out = dict(dpgid=r.dpgid, dpg=r.dpg, owner_name=r.owner_name, owner_confidence=r.confidence)
    if r.confidence == "low" or r.owner_type == "UNKNOWN":
        out.update(exposure_score="", exposed="", exposure_score_sens="", exposed_sens="", zero_reason="owner low confidence: no score (B1)")
        rows.append(out); continue
    mine = net[net.org.isin(lk)]
    p_sc, p_pr, p_sub, p_oth, p_usd, p_ev, p_po = score(mine[mine.in_primary_set])
    s_sc, s_pr, s_sub, s_oth, s_usd, s_ev, s_po = score(mine)
    matched = lk.isin(mapped_orgs).any()
    out.update(exposure_score=p_sc, exposed=int(p_sc >= 2), exposure_score_sens=s_sc, exposed_sens=int(s_sc >= 2),
               n_fa_prime=p_pr, n_fa_subaward=p_sub, n_other_federal=p_oth, fa_usd_window_unprorated=round(p_usd),
               n_fa_prime_sens=s_pr, n_fa_subaward_sens=s_sub, fa_usd_window_unprorated_sens=round(s_usd),
               evidence=p_ev or s_ev, check_purchase_order_only=bool(p_po),
               attribution_basis="|".join(sorted(set(mine.attribution))) if len(mine) else "",
               zero_reason="" if s_sc else ("recipient matched, nothing active in window" if matched else "no recipient in the map (no federal award found)"))
    rows.append(out)
ff = pd.DataFrame(rows)
# award-level evidence behind the PRIMARY score, for the case-study list
ev_rows = []
for _, r in om.iterrows():
    lk = links[links.dpgid == r.dpgid].org
    mine = usable(net[net.org.isin(lk) & net.in_primary_set & net.foreign_aid])
    for a in mine.sort_values("amount", ascending=False).head(5).itertuples():
        ev_rows.append(dict(dpgid=r.dpgid, dpg=r.dpg, org=a.org, tier=a.tier, agency=a.agency, sub_agency=a.sub_agency,
                            prime_award_id=a.prime_award_id, award_id=a.award_id, prime_recipient=a.prime_recipient,
                            start=a.start, end=a.end, amount=a.amount, description=a.description))
pd.DataFrame(ev_rows).to_csv(ROOT / "data/funding_flags_awards.csv", index=False)
ff["in_primary"] = ff.owner_confidence.isin(["high", "medium"]) & ff.exposure_score.ne("")
ff.to_csv(ROOT / "data/funding_flags.csv", index=False)

sc = ff[ff.exposure_score.ne("")]
print(f"DPGs: {len(ff)}; scored: {len(sc)}; unscored (owner low confidence): {len(ff) - len(sc)}")
print("dropped awards (bad/missing dates):", int(bad.sum()))
print("primary score:", sc.exposure_score.value_counts().sort_index().to_dict(), "| exposed:", int(sc.exposed.sum()))
print("sensitivity score:", sc.exposure_score_sens.value_counts().sort_index().to_dict(), "| exposed:", int(sc.exposed_sens.sum()))
print(sc.zero_reason.value_counts().to_string())
print("exposed (primary) flagged purchase-order-only:", sc[sc.exposed.eq(1)].check_purchase_order_only.sum(), "| owners behind the exposed DPGs:", sc[sc.exposed.eq(1)].owner_name.nunique())
