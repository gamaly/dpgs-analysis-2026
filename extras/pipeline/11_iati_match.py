"""N1 step 2 : apply DESIGN E to cached IATI docs -> data/donor_awards_nonus.csv.

Per (search name, activity) candidate:
  window: start <= 2025-01-19 and (end is blank or end >= 2022-10-01). start = actual (type 2) else planned (1);
          end = actual (4) else planned (3). Blank end counts only if status is active (2 implementation / 1 pipeline /3 finalisation).
  name:   exact = normalised participating-org narrative equals the search name; variant = narrative contains it.
  role:   taken only when participating_org_narrative and _role arrays have equal length (else 'unknown').
  tier:   candidate_high = exact name, role implementing(4)/extending(3)/funding-recipient unknown-or-4/3, in window,
          owner_type not UN/GOV/MDB (those are donors themselves), numFound <= 100 (not a parent-scale body)
          -> still needs the 'work fits' hand check (DESIGN E): column fit_review stays blank until reviewed.
          medium = variant name, or exact name but role unknown / parent scale. low = outside the window (kept, not used).
The reporting org must differ from the participating org (self-reporting is not donor funding).
"""
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
W0, W1 = "2022-10-01", "2025-01-19"
ACTIVE = {"1", "2", "3"}
# large for-profits (as in DESIGN B): their grants don't fund the DPG, so never candidate_high
NOT_DPG_FUNDING = {"google", "johnson and johnson", "hsbc", "red hat"}
US_REPORTERS = ("US-", "XI-IATI-US")  # US government publishers belong to the USAspending part of the analysis


def norm(s):
    s = re.sub(r"\(.*?\)", " ", str(s).lower()).replace("&", " and ")
    s = re.sub(r"\b(inc|ltd|llc|npc|the|gmbh|ag|foundation|trust|org)\b", " ", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def dates(doc):
    t, d = doc.get("activity_date_type") or [], doc.get("activity_date_iso_date") or []
    m = {}
    for a, b in zip(t, d):
        m.setdefault(str(a), b[:10])
    return (m.get("2") or m.get("1")), (m.get("4") or m.get("3")), m.get("3"), m.get("4")


def main():
    om = pd.read_csv(ROOT / "data/dpg_owner_map.csv")
    owners = {}  # search name -> list of (dpgid, role, owner_type, owner_conf)
    import importlib.util
    spec = importlib.util.spec_from_file_location("c", ROOT / "scripts/11_iati_collect.py")
    c = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(c)
    for n, pairs in c.search_names().items():
        owners[n] = pairs
    typ = om.set_index("dpgid")[["owner_type", "confidence"]].to_dict("index")
    rows = []
    for f in (ROOT / "cache/iati/docs").glob("*.json"):
        j = json.loads(f.read_text(encoding="utf-8"))
        n, nf = j["name"], j["numFound"]
        nn = norm(n)
        for d in j["docs"]:
            narr = d.get("participating_org_narrative") or []
            roles = d.get("participating_org_role") or []
            hit = [(i, x) for i, x in enumerate(narr) if nn and nn in norm(x)]
            if not hit:
                continue
            exact = any(norm(x) == nn for _, x in hit)
            i = next((i for i, x in hit if norm(x) == nn), hit[0][0])
            role = roles[i] if len(roles) == len(narr) else "unknown"
            rep = (d.get("reporting_org_narrative") or [""])[0]
            if norm(rep) == nn or norm(rep).startswith(nn) or nn.startswith(norm(rep)) and norm(rep):
                continue
            if str(d.get("reporting_org_ref") or "").startswith(US_REPORTERS) or "agency for international development" in rep.lower() or rep.lower().startswith("department of "):
                continue
            start, end, pend, aend = dates(d)
            st = str(d.get("activity_status_code"))
            in_win = bool(start and start <= W1 and ((end and end >= W0) or (not end and st in ACTIVE)))
            for dpgid, orole in owners[n]:
                ot = typ[dpgid]["owner_type"]
                if not in_win:
                    tier = "low_outside_window"
                elif exact and role in ("3", "4") and ot not in ("UN", "GOV", "MDB", "UNIV") and nf <= 100 and nn not in NOT_DPG_FUNDING:
                    tier = "candidate_high"
                else:
                    tier = "medium"
                title = (d.get("title_narrative") or [""])[0]
                rows.append(dict(
                    dpgid=dpgid, search_name=n, name_role=orole, owner_type=ot, owner_conf=typ[dpgid]["confidence"],
                    iati_id=d["iati_identifier"], reporting_org=rep, reporting_ref=d.get("reporting_org_ref"),
                    matched_narrative=narr[i], match="exact" if exact else "variant", org_role=role,
                    title=title, start=start, end=end, status=st, in_window=in_win, tier=tier,
                    countries=";".join(d.get("recipient_country_code") or []), name_numFound=nf,
                    # 2025 cut (DESIGN E): cancelled/suspended, or closed early on/after the 2025-01-20 freeze
                    cut_2025=bool(st in ("5", "6") or (aend and pend and aend >= "2025-01-20" and aend < pend)),
                    fit_review=""))
    out = pd.DataFrame(rows).drop_duplicates(["dpgid", "iati_id", "search_name"])
    # hand 'work fits' decisions (data/donor_fit_review.csv, curated, never overwritten here)
    fr = ROOT / "data/donor_fit_review.csv"
    if fr.exists():
        r = pd.read_csv(fr)[["dpgid", "iati_id", "search_name", "fit_review", "fit_note"]]
        out = out.drop(columns="fit_review").merge(r, how="left", on=["dpgid", "iati_id", "search_name"])
        out["fit_review"] = out.fit_review.fillna("")
    out["tier_final"] = out.tier.where(~((out.tier == "candidate_high") & (out.fit_review != "yes")),
                                       out.fit_review.map({"partial": "medium", "no": "low_no_fit", "": "candidate_high"}))
    out["tier_final"] = out.tier_final.replace({"candidate_high": "high"})
    out.to_csv(ROOT / "data/donor_awards_nonus.csv", index=False)
    print(len(out), "rows;", out.tier.value_counts().to_dict())
    print("final:", out.tier_final.value_counts().to_dict())
    h = out[out.tier == "candidate_high"]
    print("candidate_high DPGs:", h.dpgid.nunique(), "activities:", h.iati_id.nunique())
    print("medium DPGs:", out[out.tier == "medium"].dpgid.nunique())


if __name__ == "__main__":
    main()
