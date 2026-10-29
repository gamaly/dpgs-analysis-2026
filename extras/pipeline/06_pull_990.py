"""Pull yearly Form 990 financials from ProPublica for every EIN in data/org_ein_map.csv (all confidence levels;
inclusion rules are applied at analysis time, see "Experimental design" in the project notes).
Output: data/org_990_yearly.csv (one row per EIN x tax year). Cache: cache/propublica/org_<ein>.json.
ProPublica summary fields lack government grants (Part VIII 1e), employee count and Schedule I; those need IRS e-file XML.
"""
import json, time
from pathlib import Path
import pandas as pd, requests

ROOT = Path(__file__).resolve().parent.parent
PP = ROOT / "cache/propublica"
PP.mkdir(parents=True, exist_ok=True)
API = "https://projects.propublica.org/nonprofits/api/v2"
FIELDS = {"tax_prd_yr": "tax_year", "tax_prd": "tax_period", "formtype": "formtype", "totrevenue": "total_revenue",
          "totcntrbgfts": "contributions_grants", "totprgmrevnue": "program_service_revenue", "invstmntinc": "investment_income",
          "totfuncexpns": "total_expenses", "compnsatncurrofcr": "officer_comp", "othrsalwages": "other_salaries",
          "payrolltx": "payroll_tax", "totassetsend": "total_assets", "totliabend": "total_liabilities",
          "totnetassetend": "net_assets", "pdf_url": "pdf_url"}

def org(ein):
    f = PP / f"org_{ein}.json"
    if f.exists(): return json.loads(f.read_text(encoding="utf-8"))
    for attempt in range(5):
        r = requests.get(f"{API}/organizations/{int(ein)}.json", timeout=30)
        if r.status_code in (429, 500, 502, 503):
            time.sleep(5 * (attempt + 1)); continue
        r.raise_for_status(); break
    f.write_text(r.text, encoding="utf-8")
    time.sleep(0.5)
    return r.json()

em = pd.read_csv(ROOT / "data/org_ein_map.csv", dtype={"ein": str}).dropna(subset=["ein"])
rows, nodata = [], []
for _, m in em.iterrows():
    j = org(m.ein)
    fl = j.get("filings_with_data", [])
    if not fl: nodata.append(m.owner_name)
    for f in fl:
        rows.append({"owner_name": m.owner_name, "ein": m.ein, "attribution": m.attribution, "ein_confidence": m.confidence,
                     **{v: f.get(k) for k, v in FIELDS.items()}})
    for f in j.get("filings_without_data", []):  # PDF-only years: record so gaps are visible
        rows.append({"owner_name": m.owner_name, "ein": m.ein, "attribution": m.attribution, "ein_confidence": m.confidence,
                     "tax_year": f.get("tax_prd_yr"), "tax_period": f.get("tax_prd"), "formtype": f.get("formtype_str") or f.get("formtype"),
                     "pdf_url": f.get("pdf_url"), "pdf_only": True})
df = pd.DataFrame(rows)
df["pdf_only"] = df.get("pdf_only", False)
df["pdf_only"] = df["pdf_only"].fillna(False).astype(bool)
df["salaries_total"] = df[["officer_comp", "other_salaries"]].sum(axis=1, min_count=1)
df = df.sort_values(["owner_name", "tax_year"])
df.to_csv(ROOT / "data/org_990_yearly.csv", index=False)
d = df[~df.pdf_only]
print(f"EINs: {em.ein.nunique()}; rows with data: {len(d)}; years {int(d.tax_year.min())}-{int(d.tax_year.max())}")
print("latest data year per org:", d.groupby("owner_name").tax_year.max().value_counts().sort_index().to_dict())
print("no structured data:", nodata)
