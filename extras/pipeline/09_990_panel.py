"""the Form 990 panel is descriptive and covers US-nonprofit owners: Form 990 panel, one row per EIN x fiscal year (FY2019 .. latest) -> data/org_990_panel.csv.
Sources in order: IRS e-file XML (TEOS zips, read member by member with range requests, see irs_zip.py) -> ProPublica PDF-only years
(listed, figures left blank, source='pdf', to be read by hand) -> 'not yet filed' / 'not found'.
Usage: python -I scripts/09_990_panel.py --phase 1      (the six exposed-DPG owners with a US EIN)
       python -I scripts/09_990_panel.py --phase all    (every EIN in data/org_ein_map.csv)
Fiscal year = calendar year in which the tax period ENDS (FYE June 2023 -> FY2023), the same convention as ProPublica's tax_prd_yr.
Raw downloads: cache/irs_efile/ (index_YYYY.csv, cd_<batch>.json, xml/<object_id>.xml, pp_<ein>.json).
"""
import json, sys, time, xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import irs_zip

ROOT = Path(__file__).resolve().parent.parent
C = ROOT / "cache/irs_efile"; (C / "xml").mkdir(parents=True, exist_ok=True)
TODAY = date(2026, 10, 29)
FIRST_FY, LAST_FY = 2019, 2025
PHASE1 = {"Medic (Medic Mobile Inc)", "Development Gateway", "Humanitarian OpenStreetMap Team", "VillageReach", "Digital Green", "The Tor Project"}

phase = sys.argv[sys.argv.index("--phase") + 1] if "--phase" in sys.argv else "1"
em = pd.read_csv(ROOT / "data/org_ein_map.csv", dtype=str).dropna(subset=["ein"])
if phase == "1": em = em[em.owner_name.isin(PHASE1)]
em = em.drop_duplicates("ein")
EINS = set(em.ein)
print(f"phase {phase}: {len(EINS)} EINs")

# ---- 1. index rows for these EINs (all index years)
for y in range(2019, 2027):
    p = C / f"index_{y}.csv"
    if not p.exists():
        r = requests.get(f"https://apps.irs.gov/pub/epostcard/990/xml/{y}/index_{y}.csv", headers=irs_zip.H, timeout=600)
        if r.status_code == 200: p.write_bytes(r.content)
        else: print("no index", y, r.status_code)
parts = []
for p in sorted(C.glob("index_*.csv")):
    for ch in pd.read_csv(p, dtype=str, chunksize=500_000, usecols=lambda c: c in ("EIN", "TAX_PERIOD", "SUB_DATE", "RETURN_TYPE", "OBJECT_ID", "XML_BATCH_ID")):
        if "XML_BATCH_ID" not in ch: ch["XML_BATCH_ID"] = None
        ch = ch[ch.EIN.isin(EINS)]
        if len(ch): ch = ch.assign(index_year=p.stem[-4:]); parts.append(ch)
ix = pd.concat(parts)
ix = ix[ix.RETURN_TYPE.isin(["990", "990EZ", "990PF"]) & (ix.TAX_PERIOD.str[:4].astype(int) >= FIRST_FY)].copy()
ix["fy"] = ix.TAX_PERIOD.str[:4].astype(int)
ix["n_returns"] = ix.groupby(["EIN", "TAX_PERIOD", "RETURN_TYPE"]).OBJECT_ID.transform("count")
ix = ix.sort_values("OBJECT_ID").drop_duplicates(["EIN", "TAX_PERIOD", "RETURN_TYPE"], keep="last")  # latest = amended return wins
print("e-file returns found:", len(ix))

# ---- 2. locate each XML in a zip
bf = C / "batches.json"
batches = json.load(open(bf)) if bf.exists() else {}
def zips_for(year):
    if str(year) not in batches:
        found = []
        for m in range(1, 13):
            for s in "ABCDE":
                b = f"{year}_TEOS_XML_{m:02d}{s}"
                if irs_zip.exists(b): found.append(b)
        for n in range(1, 13):  # 2019-2020 folders use the older naming
            for b in (f"download990xml_{year}_{n}", f"{year}_TEOS_XML_CT{n}"):
                if irs_zip.exists(b): found.append(b)
        batches[str(year)] = found; json.dump(batches, open(bf, "w"))
    return batches[str(year)]

BASENAMES = {}
def locate(row):
    oid = row.OBJECT_ID
    if isinstance(row.XML_BATCH_ID, str): cands = [row.XML_BATCH_ID.upper()]
    else:
        iy = int(row.index_year)
        cands = [b for y in (iy, iy - 1, iy + 1) for b in zips_for(y)]
    for b in cands:
        bm = BASENAMES.get(b)  # members sit under a batch folder, a 'Cycles_...' folder, or at the root, depending on the zip
        if bm is None: bm = BASENAMES[b] = {n.rsplit("/", 1)[-1]: n for n in irs_zip.names(b, C)}
        if f"{oid}_public.xml" in bm: return b, bm[f"{oid}_public.xml"]
    return None

def fetch(row):
    out = C / "xml" / f"{row.OBJECT_ID}.xml"
    if out.exists(): return out.read_bytes()
    loc = locate(row)
    if loc is None: return None
    data = irs_zip.read_member(*loc)
    out.write_bytes(data); return data

# ---- 3. parse
def num(el, *tags):
    for t in tags:
        e = el.find(t)
        if e is not None and e.text not in (None, ""):
            try: return float(e.text)
            except ValueError: pass
    return None

def parse(data, rtype):
    root = ET.fromstring(data)
    for e in root.iter(): e.tag = e.tag.split("}")[-1]
    rd = root.find("ReturnData")
    f = rd.find({"990": "IRS990", "990EZ": "IRS990EZ", "990PF": "IRS990PF"}[rtype])
    sf = rd.find("IRS990ScheduleF")
    o = dict(name=(root.findtext("ReturnHeader/Filer/BusinessName/BusinessNameLine1Txt") or ""),
             filed_ts=root.findtext("ReturnHeader/ReturnTs") or "")
    if rtype == "990":
        o.update(total_revenue=num(f, "CYTotalRevenueAmt"), contributions_grants=num(f, "CYContributionsGrantsAmt"),
                 government_grants=num(f, "GovernmentGrantsAmt"), total_expenses=num(f, "CYTotalExpensesAmt"),
                 salaries_comp=num(f, "CYSalariesCompEmpBnftPaidAmt"), employees=num(f, "TotalEmployeeCnt", "EmployeeCnt"),
                 volunteers=num(f, "TotalVolunteersCnt"), net_assets_eoy=num(f, "NetAssetsOrFundBalancesEOYAmt"),
                 foreign_employees=num(sf, "TotalEmployeeCnt") if sf is not None else None,
                 gov_grants_tag_present=f.find("GovernmentGrantsAmt") is not None)
    elif rtype == "990EZ":
        o.update(total_revenue=num(f, "TotalRevenueAmt"), contributions_grants=num(f, "ContributionsGiftsGrantsEtcAmt"),
                 total_expenses=num(f, "TotalExpensesAmt"), salaries_comp=num(f, "SalariesOtherCompEmplBnftAmt"),
                 net_assets_eoy=num(f, "NetAssetsOrFundBalancesEOYAmt", "NetAssetsOrFundBalancesEOY"))
    else:
        o.update(total_revenue=num(f, "AnalysisOfRevenueAndExpenses/TotalRevAndExpnssAmt", "AnalysisOfRevenueAndExpenses/TotalRevenueAmt"),
                 total_expenses=num(f, "AnalysisOfRevenueAndExpenses/TotalExpensesRevAndExpnssAmt"))
    if rtype == "990" and not o["gov_grants_tag_present"]: o["government_grants"] = 0.0  # e-file omits zero-valued lines; flag kept
    return o

# ProPublica structured fields (revenue, contributions, expenses, salaries, net assets; no employees or government grants)
yearly = pd.read_csv(ROOT / "data/org_990_yearly.csv", dtype={"ein": str})
yearly = yearly[~yearly.pdf_only & yearly.total_revenue.notna()].copy()
yearly["fy"] = yearly.tax_period.astype(str).str[:4].astype(int)
yearly = yearly.drop_duplicates(["ein", "fy"], keep="last").set_index(["ein", "fy"])

# ---- 4. ProPublica listing: years that exist only as PDFs, and to detect filed-but-not-in-e-file
def pp_years(ein):
    p = C / f"pp_{ein}.json"
    if not p.exists():
        r = requests.get(f"https://projects.propublica.org/nonprofits/api/v2/organizations/{ein}.json", headers=irs_zip.H, timeout=60)
        p.write_text(r.text if r.status_code == 200 else "{}", encoding="utf-8")
    d = json.load(open(p, encoding="utf-8"))
    out = {}
    for k in ("filings_with_data", "filings_without_data"):
        for x in d.get(k, []):
            out[int(x["tax_prd_yr"])] = (x.get("formtype_str") or {0: "990", 1: "990EZ", 2: "990PF"}.get(x.get("formtype"), ""), x.get("pdf_url", ""))
    return out

def extended_due(fy_end_ym, fye_month):
    """Extended due date: 15th of the 11th month after the fiscal year end."""
    y, m = fy_end_ym, fye_month + 11
    y += (m - 1) // 12; m = (m - 1) % 12 + 1
    return date(y, m, 15)

rows = []
for r in em.itertuples():
    ppy = pp_years(r.ein)
    mine = ix[ix.EIN == r.ein].sort_values("fy")
    fye_month = int(mine.TAX_PERIOD.str[4:].iloc[-1]) if len(mine) else 12
    for fy in range(FIRST_FY, LAST_FY + 1):
        base = dict(owner_name=r.owner_name, ein=r.ein, attribution=r.attribution, ein_confidence=r.confidence, fiscal_year=fy)
        m = mine[mine.fy == fy]
        if len(m):
            for x in m.itertuples():
                rec = dict(base, tax_period=x.TAX_PERIOD, form_type=x.RETURN_TYPE, object_id=x.OBJECT_ID, n_returns=x.n_returns, status="filed", source="irs_efile_xml")
                try:
                    data = fetch(x)
                    if data is None: raise RuntimeError("zip member not located")
                    rec.update(parse(data, x.RETURN_TYPE)); rec["filing_date"] = rec.pop("filed_ts")[:10]
                except Exception as e:
                    rec.update(status="filed", source="irs_efile_index_only", notes=f"XML not read: {e}")
                    if (r.ein, fy) in yearly.index:  # same filing, ProPublica structured fields
                        y = yearly.loc[(r.ein, fy)]
                        rec.update(source="propublica_structured", total_revenue=y.total_revenue, contributions_grants=y.contributions_grants,
                                   total_expenses=y.total_expenses, salaries_comp=y.salaries_total, net_assets_eoy=y.net_assets,
                                   notes="IRS XML not available (zip not published); employees and government grants blank, read from PDF if needed")
                rows.append(rec)
        elif fy in ppy:
            rows.append(dict(base, form_type=ppy[fy][0], status="filed", source="pdf", notes="listed by ProPublica as PDF only; figures to be read by hand", pdf_url=ppy[fy][1]))
        else:
            due = extended_due(fy, fye_month)
            rows.append(dict(base, status="not yet filed" if due >= TODAY else "not found",
                             notes=f"extended due date {due}" if due >= TODAY else "no e-file or ProPublica record; due date passed"))
    print(r.owner_name, "done", flush=True)

panel = pd.DataFrame(rows)
cols = ["owner_name", "ein", "attribution", "ein_confidence", "fiscal_year", "tax_period", "form_type", "status", "source", "filing_date",
        "total_revenue", "contributions_grants", "government_grants", "gov_grants_tag_present", "total_expenses", "salaries_comp",
        "employees", "foreign_employees", "volunteers", "net_assets_eoy", "n_returns", "object_id", "pdf_url", "notes"]
for c in cols:
    if c not in panel: panel[c] = None
out = ROOT / ("data/org_990_panel.csv" if phase == "all" else "data/org_990_panel_phase1.csv")
panel[cols].sort_values(["owner_name", "fiscal_year"]).to_csv(out, index=False)
print("wrote", out, len(panel), "rows; status:", panel.status.value_counts().to_dict())
