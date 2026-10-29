"""N2 (this part of the study): parse the ITPC list of USAID terminated/active awards (6 March 2025) -> data/usg_terminations.csv.

Source: ITPC, "Synthesis of USAID Terminated and Active Awards as of 6 March 2025", cleaned from a leaked memo to
Congress (Zivahub / figshare article 28881605, file 54013763, md5 f52b28991c611c32ee0985f626668b85). Unofficial;
the administration published no award-status list. Raw file: cache/terminations/raw/itpc/.

The workbook has no status column. Status is the row fill colour of the Award ID cell:
  FBE4D6 (orange) = terminated, E2EFDA (green) = active, unparsed/theme colour = treated as terminated (medium).
Check (run every time): orange + unparsed award rows must equal the published 5,341 terminated of ~6,239.
Multi-line records (vendor/description wrapped over rows with no Award ID) are merged into the preceding award.
"""
import hashlib
import sys
from pathlib import Path

import openpyxl
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "cache/terminations/raw/itpc/USAID-Terminated-Active-Awards_2025-03-06_Clean.xlsx"
OUT = ROOT / "data/usg_terminations.csv"
MD5 = "f52b28991c611c32ee0985f626668b85"
COLS = ["award_id", "piid", "vendor", "description", "total_est_cost", "obligated", "start", "end", "office"]
TERM, ACTIVE = "FFFBE4D6", "FFE2EFDA"


def money(s):
    try:
        return float(str(s).replace("$", "").replace(",", ""))
    except ValueError:
        return None


def main():
    if hashlib.md5(SRC.read_bytes()).hexdigest() != MD5:
        sys.exit("md5 mismatch: source file changed")
    ws = openpyxl.load_workbook(SRC).active
    recs = []
    for row in ws.iter_rows(min_row=2):
        vals = [c.value for c in row[:9]]
        if vals[0] is not None:
            f = row[0].fill.fgColor.rgb if row[0].fill.fill_type else None
            if f == TERM:
                st, basis = "terminated", "fill_orange"
            elif f == ACTIVE:
                st, basis = "active", "fill_green"
            else:
                st, basis = "terminated", "fill_unparsed_assumed_terminated"
            recs.append(dict(zip(COLS, vals), status=st, status_basis=basis))
        elif recs:  # continuation row: append wrapped text
            for k, v in zip(COLS, vals):
                if v is not None and k in ("vendor", "description", "office"):
                    recs[-1][k] = f"{recs[-1][k] or ''} {v}".strip()
    d = pd.DataFrame(recs)
    d["award_id"] = d.award_id.astype(str).str.strip()
    d["total_est_cost"] = d.total_est_cost.map(money)
    d["obligated"] = d.obligated.map(money)
    d["start"] = pd.to_datetime(d.start, errors="coerce").dt.date
    d["end"] = pd.to_datetime(d.end, errors="coerce").dt.date
    d["source"] = "ITPC/Zivahub fig 28881605 (leaked congressional memo)"
    d["source_date"] = "2025-03-06"
    d["retrieved"] = "2026-10-29"
    d.to_csv(OUT, index=False)
    n_t = (d.status == "terminated").sum()
    print(f"{len(d)} awards; terminated {n_t} (published 5,341), active {(d.status=='active').sum()}; "
          f"unparsed-fill {(d.status_basis=='fill_unparsed_assumed_terminated').sum()}; "
          f"dup award_id {d.award_id.duplicated().sum()}")
    if n_t != 5341:
        print("WARNING: terminated count differs from published 5,341")


if __name__ == "__main__":
    main()
