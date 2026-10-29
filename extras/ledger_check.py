"""Shared helper for the five notebooks and for verify_numbers.py: compare numbers we reproduce with the ledger.

THE LEDGER
----------
`extras/numbers_ledger.csv` is a copy of docs/post/numbers.csv: one row per claim in the blog post, with an id
(N001...), the number(s) the post uses (`value`), where it came from (`source_file`, `source_script`) and notes.

HOW A CLAIM IS CHECKED
----------------------
Each notebook ends with calls like

    lc.claim("N039", "merged PRs per core contributor 2021/24/25/26", [8.79, 10.74, 11.05, 14.61, 66])

giving the numbers it reproduced from the released data. The checker then:
  1. reads every number out of the ledger's `value` text (so a revised ledger is picked up automatically);
  2. looks for each of them among the reproduced numbers;
  3. grades each ledger number
        exact     the reproduced number equals the ledger number
        rounding  it equals it after rounding to the number of decimals the ledger shows (e.g. 8.7931 -> 8.79)
        MISMATCH  anything else
     and the claim takes its worst grade.
Claims whose ledger value has no number in it (for example "nan" or "none significant") are graded on a yes/no
test the notebook supplies (`ok=`).

Nothing here reads the internet. It only reads the ledger.
"""
import json
import re
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
REL = HERE.parent                      # repository root
LEDGER = HERE / "numbers_ledger.csv"   # lives in extras/ next to this file
OUTDIR = HERE / "_claims"

# numbers in text: 1,120 | 3141 | 0.03 | -0.05 ; a minus counts only when it is not a range hyphen (digit before it)
_NUM = re.compile(r"(?<![\w.])(-?)(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)")

CLAIMS = {}  # claim id -> dict(desc, values, ok, note)


def ledger_numbers(text):
    """All numbers in a ledger `value` string, as (float, decimals)."""
    out = []
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return out
    s = str(text)
    for m in _NUM.finditer(s):
        raw = m.group(2).replace(",", "")
        dec = len(raw.split(".")[1]) if "." in raw else 0
        v = float(raw) * (-1 if m.group(1) else 1)
        out.append((v, dec))
    return out


def _round_half_up(x, dec):
    q = Decimal(1).scaleb(-dec)
    return float(Decimal(repr(float(x))).quantize(q, rounding=ROUND_HALF_UP))


def grade_number(ledger_v, dec, repro_values):
    """Best grade of one ledger number against the reproduced numbers: exact / rounding / None."""
    best = None
    for r in repro_values:
        if r is None or (isinstance(r, float) and pd.isna(r)):
            continue
        if abs(r - ledger_v) < 1e-9:
            return "exact"
        if abs(_round_half_up(r, dec) - ledger_v) < 1e-9:
            best = "rounding"
    return best


def grade_claim(ledger_value, values, ok=None):
    """Return (grade, detail). grade in exact / rounding / MISMATCH / qualitative-yes / qualitative-NO."""
    nums = ledger_numbers(ledger_value)
    if not nums:
        if ok is None:
            return "not-numeric", "ledger value has no number and the notebook gave no yes/no test"
        return ("qualitative-yes" if ok else "qualitative-NO"), "ledger value is not numeric; notebook test = %s" % ok
    grades, missing = [], []
    for v, dec in nums:
        g = grade_number(v, dec, values)
        grades.append(g)
        if g is None:
            missing.append(v)
    if missing:
        return "MISMATCH", "ledger numbers not reproduced: %s" % missing
    if ok is False:
        return "MISMATCH", "numbers present but the notebook's yes/no test failed"
    return ("exact" if all(g == "exact" for g in grades) else "rounding"), ""


def claim(cid, desc, values=(), ok=None, note=""):
    """Register what a notebook reproduced for claim `cid`."""
    CLAIMS[cid] = dict(desc=desc, values=[float(v) for v in values], ok=ok, note=note)


def load_ledger():
    return pd.read_csv(LEDGER, dtype=str).set_index("id")


def show(notebook):
    """Print, by claim id, the ledger value next to what this notebook reproduced; save results for verify_numbers.py."""
    led = load_ledger()
    rows = []
    for cid, c in CLAIMS.items():
        if cid not in led.index:
            rows.append((cid, "(not in ledger)", c["desc"], "", "not-in-ledger"))
            continue
        lv = led.loc[cid, "value"]
        grade, detail = grade_claim(lv, c["values"], c["ok"])
        shown = ", ".join(("%g" % v) for v in c["values"]) if c["values"] else str(c["ok"])
        rows.append((cid, lv, shown, detail, grade))
    df = pd.DataFrame(rows, columns=["claim", "ledger value", "reproduced here", "detail", "grade"])
    with pd.option_context("display.max_colwidth", 70, "display.width", 250, "display.max_rows", 500):
        print(df.to_string(index=False))
    print("\nsummary:", df.grade.value_counts().to_dict())
    OUTDIR.mkdir(exist_ok=True)
    (OUTDIR / (notebook + ".json")).write_text(json.dumps(CLAIMS, indent=1), encoding="utf-8")
    return df
