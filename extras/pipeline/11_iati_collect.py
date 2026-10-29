"""N1 (this part of the study) step 1: collect IATI activities that name a DPG owner / related implementer as participating org.

Search names come from data/dpg_owner_map.csv (owner_name, related_orgs; read-only). One phrase query per name
against the IATI Datastore (key in .env as IATI_API_KEY, never printed). US-government reporters (US-*) are
excluded server side: they belong to the USAspending part (DESIGN B). Raw responses are cached under cache/iati/
before any matching (DESIGN E). Matching and the window test are step 2 (11_iati_match.py).

Stage 1 counts hits per name; stage 2 fetches documents for names with <= MAX_DOCS hits. Names above that are large
parent/host bodies (UNICEF, GIZ ...): logged in cache/iati/_skipped_big.csv, sensitivity-only per DESIGN B3.
Rate limit 5 req/s, 25,000 req/day: we sleep 0.3s between calls.

Usage: python -I scripts/11_iati_collect.py [--count-only] [--limit N]
"""
import argparse
import csv
import hashlib
import json
import re
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache/iati"
BASE = "https://api.iatistandard.org/datastore/activity/select"
MAX_DOCS = 1500
ROWS = 200
# large for-profit tech named as related orgs: their contracts don't fund the DPG (DESIGN B)
SKIP = {"microsoft", "esri", "acquia", "thoughtworks", "ciq", "unknown"}
FL = ("iati_identifier,reporting_org_ref,reporting_org_narrative,reporting_org_type,title_narrative,"
      "description_narrative,activity_status_code,activity_date_type,activity_date_iso_date,"
      "participating_org_ref,participating_org_narrative,participating_org_role,participating_org_type,"
      "recipient_country_code,sector_code,default_currency,transaction_transaction_type_code,"
      "transaction_transaction_date_iso_date,transaction_value,transaction_value_currency,"
      "transaction_receiver_org_narrative,transaction_provider_org_narrative,last_updated_datetime")


def key():
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("IATI_API_KEY="):
            return line.split("=", 1)[1].strip().strip("\"'")
    raise SystemExit("IATI_API_KEY missing from .env")


def search_names():
    d = pd.read_csv(ROOT / "data/dpg_owner_map.csv")
    names = {}
    for _, r in d.iterrows():
        cands = [(r.owner_name, "owner")]
        if isinstance(r.related_orgs, str):
            cands += [(x.strip(), "related") for x in r.related_orgs.split(";") if x.strip()]
        for n, role in cands:
            if not isinstance(n, str):
                continue
            variants = {n.strip()}
            stripped = re.sub(r"\s*\(.*?\)", "", n).strip()
            if stripped:
                variants.add(stripped)
            for v in variants:
                if v.lower() in SKIP or len(v) < 4:
                    continue
                names.setdefault(v, set()).add((r.dpgid, role))
    return names


def fname(name):
    return re.sub(r"[^a-z0-9]+", "_", name.lower())[:60] + "_" + hashlib.md5(name.encode()).hexdigest()[:6]


def call(sess, k, params):
    time.sleep(0.3)
    for attempt in range(4):
        r = sess.get(BASE, headers={"Ocp-Apim-Subscription-Key": k}, params=params, timeout=120)
        if r.status_code == 429:
            time.sleep(5 * (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()["response"]
    raise RuntimeError("rate limited repeatedly")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count-only", action="store_true")
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / "docs").mkdir(exist_ok=True)
    k, sess = key(), requests.Session()
    names = sorted(search_names())
    if a.limit:
        names = names[: a.limit]
    print(len(names), "search names")
    counts_f = CACHE / "_counts.csv"
    counts = {}
    if counts_f.exists():
        counts = dict(pd.read_csv(counts_f).values.tolist())
    for n in names:
        if n in counts:
            continue
        q = f'participating_org_narrative:"{n}" AND -reporting_org_ref:US-*'
        resp = call(sess, k, {"q": q, "rows": 0, "wt": "json"})
        counts[n] = resp["numFound"]
        pd.DataFrame(sorted(counts.items()), columns=["name", "numFound"]).to_csv(counts_f, index=False)
    print("counted; names with hits:", sum(v > 0 for v in counts.values()),
          "| over cap:", sum(v > MAX_DOCS for v in counts.values()))
    if a.count_only:
        return
    skipped = []
    for n in names:
        nf = counts[n]
        out = CACHE / "docs" / (fname(n) + ".json")
        if nf == 0 or out.exists():
            continue
        if nf > MAX_DOCS:
            skipped.append((n, nf))
            continue
        q = f'participating_org_narrative:"{n}" AND -reporting_org_ref:US-*'
        docs = []
        for start in range(0, nf, ROWS):
            docs += call(sess, k, {"q": q, "rows": ROWS, "start": start, "fl": FL, "sort": "iati_identifier asc",
                                   "wt": "json"})["docs"]
        out.write_text(json.dumps({"name": n, "numFound": nf, "docs": docs}), encoding="utf-8")
        print(f"{n}: {len(docs)} docs")
    with open(CACHE / "_skipped_big.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["name", "numFound"])
        w.writerows(skipped + [(n, c) for n, c in counts.items() if c > MAX_DOCS and (n, c) not in skipped])


if __name__ == "__main__":
    main()
