"""US federal awards (prime + subawards) for DPG owner orgs and their related orgs, via the USAspending API.
Two stages, with a hand-review step between them (see DESIGN.md, rules B2):
  --lookup : search AWARD records by name (prime grants/contracts + subawards) and list the distinct recipient
             names/UEIs they contain -> data/usg_recipient_candidates.csv. (The /recipient/ index misses real
             recipients, e.g. Jembi Health Systems, and subawardees are often recorded by name only, without UEI.)
  --awards : for each row of the HAND-CURATED data/usg_recipient_map.csv (confidence high/medium), fetch all awards
             since FY2008 by name and by UEI, keeping only rows whose recipient UEI matches or whose normalised name
             matches exactly -> data/org_awards_usg.csv. Parent/host/implementer orgs (universities, UN agencies, big companies, named contractors)
             are limited to USAID, State, MCC and CDC awards; their other federal work says nothing about the DPG.
Cache: cache/usaspending/.
"""
import json, re, sys, time
from difflib import SequenceMatcher
from pathlib import Path
import pandas as pd, requests

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache/usaspending"
CACHE.mkdir(parents=True, exist_ok=True)
API = "https://api.usaspending.gov/api/v2"
START, END = "2007-10-01", "2026-09-30"
GRANTS, CONTRACTS = ["02", "03", "04", "05"], ["A", "B", "C", "D"]
FOREIGN_AID = [{"type": "awarding", "tier": "toptier", "name": "Agency for International Development"},
               {"type": "awarding", "tier": "toptier", "name": "Department of State"},
               {"type": "awarding", "tier": "toptier", "name": "Millennium Challenge Corporation"},
               {"type": "awarding", "tier": "subtier", "name": "Centers for Disease Control and Prevention"}]
# owner names as written in dpg_owner_map -> names USAspending is likely to hold (legal / full names)
ALIASES = {
    "UNICEF": ["United Nations Children's Fund", "UNICEF"],
    "World Food Programme": ["World Food Programme", "World Food Program"],
    "FAO": ["Food and Agriculture Organization"],
    "World Health Organization": ["World Health Organization"],
    "UNDP": ["United Nations Development Programme"],
    "UNIDO": ["United Nations Industrial Development Organization"],
    "WMO Regional Office for Africa": ["World Meteorological Organization"],
    "GIZ": ["Deutsche Gesellschaft fur Internationale Zusammenarbeit", "GIZ"],
    "Humanity & Inclusion": ["Handicap International", "Humanity & Inclusion"],
    "Plan International": ["Plan International"],
    "Digital Impact Alliance (DIAL)": ["Digital Impact Alliance", "United Nations Foundation"],
    "Drupal Association": ["Drupal Association", "DrupalCon"],
    "Learning Equality": ["Foundation for Learning Equality", "Learning Equality"],
    "Medic (Medic Mobile Inc)": ["Medic Mobile"],
    "Medtronic LABS": ["Medtronic LABS", "Medtronic Global Health Foundation"],
    "USAID Global Health Supply Chain Program (GHSC-PSM)": ["Chemonics International"],
    "Columbia University (Columbia International eHealth Laboratory)": ["Trustees of Columbia University"],
    "University of Washington (I-TECH / DIGI)": ["University of Washington"],
    "IIIT Bangalore (MOSIP)": ["International Institute of Information Technology Bangalore"],
    "University of Oslo (HISP Centre)": ["University of Oslo", "Universitetet i Oslo"],
    "London School of Hygiene & Tropical Medicine": ["London School of Hygiene"],
    "Jembi Health Systems NPC": ["Jembi Health Systems", "Jembi"],
    "Get ODK Inc": ["Get ODK", "ODK"],
    "Kobo Inc": ["Kobo Inc", "KoboToolbox"],
}
S = requests.Session()
FAILED = []  # cache keys of requests that failed after all retries

def post(path, body, cache_key):
    f = CACHE / f"{cache_key}.json"
    if f.exists(): return json.loads(f.read_text(encoding="utf-8"))
    for attempt in range(7):  # the API drops connections under load; back off up to ~10 min in total
        try:
            r = S.post(f"{API}/{path}", json=body, timeout=180)
        except requests.exceptions.RequestException:
            time.sleep(15 * (attempt + 1)); continue
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(15 * (attempt + 1)); continue
        r.raise_for_status()
        j = r.json(); break
    else:  # not cached, so a re-run retries it; FAILED is reported at the end
        FAILED.append(cache_key)
        print(f"  gave up: {cache_key}", flush=True)
        return {"results": [], "page_metadata": {"hasNext": False}}
    f.write_text(json.dumps(j), encoding="utf-8")
    time.sleep(1)
    return j

def slug(s): return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_").lower()[:80]

def norm(s):
    s = re.sub(r"\b(inc|incorporated|corp|corporation|the|llc|ltd|limited|co|org|of|and|for)\b|[^a-z0-9 ]", " ", s.lower())
    return " ".join(s.split())

def nname(s):
    """Normalised recipient name for exact matching: upper case, no punctuation, no leading THE."""
    s = re.sub(r"[^A-Z0-9 ]", " ", (s or "").upper().replace("&", " AND "))
    return re.sub(r"^THE ", "", " ".join(s.split()))

def queries(name):
    """Search strings for an owner/related org: aliases, else the name outside and inside parentheses."""
    if name in ALIASES: return ALIASES[name]
    out = [re.sub(r"\s*\(.*?\)", "", name).strip()]
    out += [p.strip() for p in re.findall(r"\((.*?)\)", name) if len(p.strip()) > 3]
    return [q for q in dict.fromkeys(out) if q]

def fetch_awards(text, sub, codes, max_pages=None, agencies=None):
    fields = (["Sub-Award ID", "Sub-Awardee Name", "Sub-Recipient UEI", "Sub-Award Amount", "Sub-Award Date", "Sub-Award Type",
               "Prime Award ID", "Prime Recipient Name", "Awarding Agency", "Awarding Sub Agency"] if sub else
              ["Award ID", "Recipient Name", "Recipient UEI", "Award Amount", "Total Outlays", "Start Date", "End Date",
               "Awarding Agency", "Awarding Sub Agency", "Funding Agency", "Award Type", "Description"])
    filters = {"recipient_search_text": [text], "time_period": [{"start_date": START, "end_date": END}], "award_type_codes": codes}
    if agencies: filters["agencies"] = agencies
    out, page = [], 1
    while True:
        key = f"awards_{slug(text)}_{'sub' if sub else 'prime'}_{codes[0]}{'_fa' if agencies else ''}_p{page}"
        j = post("search/spending_by_award/", {"subawards": sub, "limit": 100, "page": page, "fields": fields, "filters": filters}, key)
        out += j.get("results", [])
        if not (j.get("page_metadata") or {}).get("hasNext") or (max_pages and page >= max_pages): return out
        page += 1

def lookup():
    om = pd.read_csv(ROOT / "data/dpg_owner_map.csv", dtype=str).fillna("")
    em = pd.read_csv(ROOT / "data/org_ein_map.csv", dtype=str).fillna("")
    irs = dict(zip(em.owner_name, em.irs_name))
    ok = om[om.confidence.isin(["high", "medium"]) & om.owner_type.ne("UNKNOWN")]
    targets = {}  # org name -> [role, dpgs]
    for _, r in ok.iterrows():
        targets.setdefault(r.owner_name, ["owner", set()])[1].add(r.dpg)
        for rel in filter(None, (x.strip() for x in r.related_orgs.split(";"))):
            targets.setdefault(rel, ["related", set()])[1].add(r.dpg)
    rows = []
    for org, (role, dpgs) in targets.items():
        for q in dict.fromkeys(queries(org) + ([irs[org]] if irs.get(org) else [])):
            hits = {}
            for sub in (False, True):
                for codes in (GRANTS, CONTRACTS):
                    for a in fetch_awards(q, sub, codes, max_pages=3):
                        name = a.get("Sub-Awardee Name" if sub else "Recipient Name") or ""
                        h = hits.setdefault((name, a.get("Sub-Recipient UEI" if sub else "Recipient UEI")), [0, 0.0, set(), set()])
                        h[0] += 1; h[1] += a.get("Sub-Award Amount" if sub else "Award Amount") or 0
                        h[2].add("sub" if sub else "prime"); h[3].add(a.get("Awarding Agency") or "")
            for (name, uei), (n, amt, tiers, ags) in hits.items():
                rows.append(dict(org=org, role=role, dpgs="|".join(sorted(dpgs)), query=q, recipient_name=name, uei=uei,
                                 n_awards_seen=n, amount_seen=round(amt), tiers="|".join(sorted(tiers)),
                                 agencies="|".join(sorted(ags))[:200],
                                 name_sim=round(SequenceMatcher(None, norm(q), norm(name)).ratio(), 2)))
    df = pd.DataFrame(rows).sort_values(["org", "name_sim", "amount_seen"], ascending=[True, False, False])
    df.to_csv(ROOT / "data/usg_recipient_candidates.csv", index=False)
    print(f"orgs searched: {len(targets)} ({sum(v[0] == 'owner' for v in targets.values())} owners); candidate rows: {len(df)}; "
          f"orgs with a close name match (sim>=0.8): {df[df.name_sim >= 0.8].org.nunique()}")

def awards():
    rm = pd.read_csv(ROOT / "data/usg_recipient_map.csv", dtype=str).fillna("")
    rm = rm[rm.confidence.isin(["high", "medium"])]
    rows = []
    for _, m in rm.iterrows():
        ags = FOREIGN_AID if m.attribution in ("parent", "host", "implementer") else None
        for text in filter(None, dict.fromkeys([m.recipient_name, m.uei])):
            for sub in (False, True):
                for codes in (GRANTS, CONTRACTS):
                    for a in fetch_awards(text, sub, codes, agencies=ags):
                        name = a.get("Sub-Awardee Name" if sub else "Recipient Name")
                        uei = a.get("Sub-Recipient UEI" if sub else "Recipient UEI")
                        if not ((m.uei and uei == m.uei) or nname(name) == nname(m.recipient_name)):
                            continue  # text search also returns other recipients
                        rows.append(dict(org=m.org, role=m.role, attribution=m.attribution, map_confidence=m.confidence,
                                         recipient_name=name, uei=uei, scope="foreign_aid_only" if ags else "all_agencies",
                                         tier="subaward" if sub else "prime", award_kind="grant" if codes is GRANTS else "contract",
                                         award_id=a.get("Sub-Award ID") if sub else a.get("Award ID"),
                                         prime_award_id=a.get("Prime Award ID") if sub else a.get("Award ID"),
                                         prime_recipient=a.get("Prime Recipient Name") if sub else a.get("Recipient Name"),
                                         amount=a.get("Sub-Award Amount") if sub else a.get("Award Amount"),
                                         outlays=None if sub else a.get("Total Outlays"),
                                         date=a.get("Sub-Award Date") if sub else a.get("Start Date"),
                                         end_date=None if sub else a.get("End Date"),
                                         agency=a.get("Awarding Agency"), sub_agency=a.get("Awarding Sub Agency"),
                                         award_type=a.get("Sub-Award Type") if sub else a.get("Award Type"),
                                         description=(a.get("Description") or "")[:200]))
    df = pd.DataFrame(rows)
    n0 = len(df)
    # the same award comes back from the name and the UEI search, and subaward reports repeat identical rows;
    # negative amounts are de-obligations and are kept
    df = df.drop_duplicates(["org", "tier", "award_id", "prime_award_id", "date", "amount"])
    df.to_csv(ROOT / "data/org_awards_usg.csv", index=False)
    print(f"map rows: {len(rm)}; award rows: {len(df)} (dropped {n0 - len(df)} duplicates)")
    print(df.groupby(["tier", "agency"]).amount.sum().div(1e6).round(1).sort_values(ascending=False).head(12).to_string())

if __name__ == "__main__":
    {"--lookup": lookup, "--awards": awards}[sys.argv[1]]()
    if FAILED:
        print(f"WARNING: {len(FAILED)} requests failed and are missing from the output; re-run to retry them: {FAILED[:10]}")
