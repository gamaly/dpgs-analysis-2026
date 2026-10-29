"""Search ProPublica Nonprofit Explorer for EIN candidates of US-nonprofit DPG owners (owner_type USNP in
data/dpg_owner_map.csv). Output: data/org_ein_candidates.csv (top hits per query, for hand review into data/org_ein_map.csv).
Cache: cache/propublica/search_<query>.json.
"""
import json, re, time
from difflib import SequenceMatcher
from pathlib import Path
import pandas as pd, requests

ROOT = Path(__file__).resolve().parent.parent
PP = ROOT / "cache/propublica"
PP.mkdir(parents=True, exist_ok=True)
API = "https://projects.propublica.org/nonprofits/api/v2"

# owner_name -> search queries (legal names / older names / fiscal hosts) where the plain name won't match
QUERIES = {
    "Medic (Medic Mobile Inc)": ["Medic Mobile"],
    "LF Charities (Linux Foundation)": ["LF Charities", "Linux Foundation"],
    "Linux Foundation (Janssen Project)": ["Linux Foundation"],
    "data.org (Epiverse-TRACE)": ["data.org", "Data Org"],
    "Digital Impact Alliance (DIAL)": ["Digital Impact Alliance", "United Nations Foundation"],
    "Humanitarian OpenStreetMap Team": ["Humanitarian OpenStreetMap Team", "Humanitarian Openstreetmap"],
    "The Computational Democracy Project": ["Computational Democracy Project"],
    "The Tor Project": ["Tor Project"],
    "Digital Green": ["Digital Green Foundation", "Digital Green"],
    "Resolve to Save Lives": ["Resolve to Save Lives", "Vital Strategies"],
    "Kobo Inc": ["Kobo Inc", "KoboToolbox"],
    "Open Concept Lab": ["Open Concept Lab", "OpenConceptLab"],
}

def search(q):
    f = PP / f"search_{re.sub(r'[^A-Za-z0-9]+', '_', q).strip('_').lower()}.json"
    if f.exists(): return json.loads(f.read_text(encoding="utf-8"))
    for attempt in range(5):
        r = requests.get(f"{API}/search.json", params={"q": q}, timeout=30)
        if r.status_code == 404: j = {"organizations": []}; break  # ProPublica returns 404 for zero hits
        if r.status_code in (429, 500, 502, 503):
            time.sleep(5 * (attempt + 1)); continue
        r.raise_for_status(); j = r.json(); break
    f.write_text(json.dumps(j), encoding="utf-8")
    time.sleep(0.5)
    return j

def norm(s):
    s = re.sub(r"\(.*?\)", " ", s.lower())
    s = re.sub(r"\b(inc|corp|corporation|the|llc|foundation|international)\b|[^a-z0-9 ]", " ", s)
    return " ".join(s.split())

om = pd.read_csv(ROOT / "data/dpg_owner_map.csv")
owners = om[om.owner_type == "USNP"].groupby("owner_name").dpg.agg("|".join)
rows = []
for owner, dpgs in owners.items():
    for q in QUERIES.get(owner, [re.sub(r"\s*\(.*?\)", "", owner)]):
        for rank, o in enumerate(search(q).get("organizations", [])[:8]):
            rows.append(dict(owner_name=owner, dpgs=dpgs, query=q, rank=rank, ein=o["ein"], strein=o.get("strein"),
                             pp_name=o.get("name"), sub_name=o.get("sub_name"), city=o.get("city"), state=o.get("state"),
                             ntee=o.get("ntee_code"), subseccd=o.get("subseccd"),
                             name_sim=round(SequenceMatcher(None, norm(q), norm(o.get("name") or "")).ratio(), 2)))
df = pd.DataFrame(rows)
df.to_csv(ROOT / "data/org_ein_candidates.csv", index=False)
hit = df[df.name_sim >= 0.8].owner_name.nunique()
print(f"owners: {len(owners)}; candidate rows: {len(df)}; owners with a close name match (sim>=0.8): {hit}")
print("no close match:", sorted(set(owners.index) - set(df[df.name_sim >= 0.8].owner_name)))
