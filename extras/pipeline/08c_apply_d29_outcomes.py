"""F11 / METHODOLOGY D29: write QC's second-coding outcomes (qc/q8_compare.csv) into the `reviewed` column of the owner, EIN and
recipient maps and apply the confidence changes:
  auto:agree     confidence unchanged
  auto:disagree  confidence set to low (rule B1/A3/B2 then drops the row from the primary analysis; logged in data/exclusions.csv)
  auto:promoted  confidence set to medium (FIN said low, QC found direct evidence meeting DESIGN high); no other promotions
Rows F12 rebuilt on clearOwnership (reviewed == 'F12:rebuilt') keep that mark: QC reruns the D29 review on them, and their old Q8
outcome is not applied. Rows QC did not code ('not_coded', QC-only, out of scope) are left unchanged and marked accordingly.
--lenient treats direct vs partial (both primary in DESIGN B3/A4) as the same attribution class; default is the literal D29 test.
Idempotent: always starts from the *_pre_f11.csv snapshot of each map (created on first run).
"""
import shutil, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
LENIENT = "--lenient" in sys.argv
q = pd.read_csv(ROOT / "qc/q8_compare.csv", dtype=str, keep_default_na=False)

def snap(name):
    src, bak = ROOT / f"data/{name}.csv", ROOT / f"data/{name}_pre_f11.csv"
    if not bak.exists(): shutil.copy(src, bak)
    return pd.read_csv(bak, dtype=str, keep_default_na=False)

def attribution_only(note):
    n = note.lower()
    return "attribution direct vs partial" in n or "attribution partial vs direct" in n

def decide(row):
    """Return (reviewed mark, new confidence or None)."""
    out = row.outcome
    if out == "auto:disagree" and LENIENT and attribution_only(row.note): return "auto:agree (lenient: direct vs partial)", None
    if out == "auto:agree": return "auto:agree", None
    if out == "auto:disagree": return "auto:disagree", "low"
    if out == "auto:promoted": return "auto:promoted", "medium"
    if out.startswith("outofscope"): return "out of D29 scope: " + out.split(":")[1], None
    return out or "not coded", None

# ---- owner map (key: dpgid)
om = snap("dpg_owner_map")
qo = q[q["map"] == "owner"].set_index("key")
for i, r in om.iterrows():
    if r.reviewed == "F12:rebuilt": continue
    if r.dpgid not in qo.index: om.loc[i, "reviewed"] = "not coded by QC"; continue
    mark, conf = decide(qo.loc[r.dpgid])
    om.loc[i, "reviewed"] = mark
    if conf: om.loc[i, "confidence"] = conf
om.to_csv(ROOT / "data/dpg_owner_map.csv", index=False)

# ---- EIN map (key: owner_name)
em = snap("org_ein_map")
em["reviewed"] = em.get("reviewed", "")
qe = q[q["map"] == "ein"].set_index("key")
for i, r in em.iterrows():
    if r.owner_name not in qe.index: em.loc[i, "reviewed"] = "not coded by QC"; continue
    mark, conf = decide(qe.loc[r.owner_name])
    em.loc[i, "reviewed"] = mark
    if conf: em.loc[i, "confidence"] = conf
em.to_csv(ROOT / "data/org_ein_map.csv", index=False)

# ---- recipient map (key: "org -> recipient_name uei")
rm = snap("usg_recipient_map")
qr = q[q["map"] == "recipient"].set_index("key")
for i, r in rm.iterrows():
    key = f"{r.org} -> {r.recipient_name} {r.uei}".strip()
    if r.confidence == "low": rm.loc[i, "reviewed"] = "rejected by FIN (low)"; continue
    if key not in qr.index: rm.loc[i, "reviewed"] = "F12:rebuilt (new row, not seen by QC)" if r.role == "owner" or r.org == "GIZ" else "not coded by QC"; continue
    if qr.loc[key].fin_code.replace(" ", "") != f"{r.attribution}|{r.confidence}".replace(" ", ""):
        rm.loc[i, "reviewed"] = "F12:rebuilt (row changed since QC saw it)"; continue  # QC's outcome was for the old row
    mark, conf = decide(qr.loc[key])
    rm.loc[i, "reviewed"] = mark
    if conf: rm.loc[i, "confidence"] = conf
rm.to_csv(ROOT / "data/usg_recipient_map.csv", index=False)

for name, df in (("owner", om), ("ein", em), ("recipient", rm)):
    print(name, df.reviewed.value_counts().to_dict(), "| confidence:", df.confidence.value_counts().to_dict())
print("mode:", "lenient (direct vs partial = same class)" if LENIENT else "literal D29")
