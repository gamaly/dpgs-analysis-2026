"""Check every number in the blog post's ledger against what the notebooks reproduce from release/data/.

Run from anywhere:   python -I extras/verify_numbers.py            (executes all five notebooks, ~2-4 minutes)
                     python -I extras/verify_numbers.py --no-exec  (re-grade using the results of the last run)

What it does, in order
 1. Refreshes extras/numbers_ledger.csv from docs/post/numbers.csv when that file exists next to the release
    (so a revised ledger is picked up automatically); otherwise it uses the copy already in the release.
 2. Executes the notebooks in the repository root with nbclient and saves them with their outputs. Each notebook
    registers the numbers it reproduced per claim id (see notebooks/ledger_check.py) in notebooks/_claims/*.json.
 3. Reads EVERY row of the ledger and grades it:
        exact       reproduced number equals the ledger number
        rounding    equals it after rounding to the decimals the ledger shows (8.7931 -> 8.79)
        MISMATCH    a ledger number was not reproduced (the report says which)
        qualitative the ledger value has no number (e.g. "none significant"); the notebook gives a yes/no test
        external    figures from outside sources (Octoverse, DX, Norad, ...): not reproducible from data
        not covered a data claim that no notebook reproduces
 4. Lists "orphaned" notebook claims: ids a notebook still reproduces that are no longer in the ledger
    (the ledger is being revised; such ids are simply skipped in the grading).
 5. Writes extras/verification_report.md.
Only files inside release/ are written. The ledger copy is the only thing read from outside release/.
"""
import argparse
import json
import shutil
import sys
from datetime import date
from pathlib import Path

import pandas as pd

EXTRAS = Path(__file__).resolve().parent        # public_repo/extras
ROOT = EXTRAS.parent                            # public_repo (notebooks sit here)
NBDIR = ROOT
sys.path.insert(0, str(EXTRAS))
import ledger_check as lc  # noqa: E402  (shared grading logic)

NOTEBOOKS = ["01_registry_and_sample", "02_teams_and_activity", "03_ai_features",
             "04_review_and_ai_disclosure", "05_funding_exposure_and_cuts"]
ORIGINAL_LEDGER = EXTRAS / "_no_original_ledger.csv"   # does not exist in the public repo


def execute_notebooks():
    import nbformat
    from nbclient import NotebookClient
    claims_dir = EXTRAS / "_claims"
    if claims_dir.exists():
        shutil.rmtree(claims_dir)                 # so a notebook that fails cannot leave stale results behind
    for name in NOTEBOOKS:
        path = NBDIR / (name + ".ipynb")
        print("executing", name, flush=True)
        nb = nbformat.read(path, 4)
        NotebookClient(nb, timeout=1800, resources={"metadata": {"path": str(NBDIR)}}).execute()
        nbformat.write(nb, path)


def load_claims():
    out = {}
    for name in NOTEBOOKS:
        f = EXTRAS / "_claims" / (name + ".json")
        if f.exists():
            for cid, c in json.loads(f.read_text(encoding="utf-8")).items():
                out[cid] = dict(c, notebook=name)
    return out


def is_external(row):
    script = str(row.get("source_script", ""))
    src = str(row.get("source_file", ""))
    return script.startswith("external") or src.startswith("http")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-exec", action="store_true", help="do not run the notebooks; use the last saved results")
    args = ap.parse_args()

    if ORIGINAL_LEDGER.exists():
        shutil.copy2(ORIGINAL_LEDGER, lc.LEDGER)
        print("ledger refreshed from", ORIGINAL_LEDGER)
    led = pd.read_csv(lc.LEDGER, dtype=str)

    if not args.no_exec:
        execute_notebooks()
    claims = load_claims()
    if not claims:
        sys.exit("no notebook results found: run without --no-exec")

    rows = []
    for r in led.to_dict("records"):
        cid = r["id"]
        c = claims.get(cid)
        if c is not None:
            grade, detail = lc.grade_claim(r["value"], c["values"], c["ok"])
            rows.append((cid, r["value"], ", ".join("%g" % v for v in c["values"]) if c["values"] else str(c["ok"]),
                         grade, c["notebook"], detail or c.get("note", "")))
        elif is_external(r):
            rows.append((cid, r["value"], "-", "external", "-", "external, not reproducible from data: " + str(r["source_file"])))
        else:
            rows.append((cid, r["value"], "-", "not covered", "-", "no notebook reproduces this claim"))
    df = pd.DataFrame(rows, columns=["claim", "ledger", "reproduced", "grade", "notebook", "note"])
    orphans = sorted(set(claims) - set(led.id))

    counts = df.grade.value_counts()
    data_rows = df[~df.grade.isin(["external"])]
    lines = ["# Verification report", "",
             f"Generated {date.today()} by `verify_numbers.py` from `numbers_ledger.csv` ({len(led)} claims) and the five notebooks.",
             "", "## Summary", "", "| grade | claims |", "|---|---|"]
    for g in ["exact", "rounding", "qualitative-yes", "MISMATCH", "qualitative-NO", "not-numeric", "not covered", "external"]:
        if g in counts:
            lines.append(f"| {g} | {counts[g]} |")
    n_ok = int(counts.get("exact", 0) + counts.get("rounding", 0) + counts.get("qualitative-yes", 0))
    lines += ["", f"{n_ok} of {len(data_rows)} data claims reproduce ({int(counts.get('exact', 0))} exact, "
              f"{int(counts.get('rounding', 0))} within rounding, {int(counts.get('qualitative-yes', 0))} qualitative checks passed). "
              f"{int(counts.get('external', 0))} claims are external figures.",
              "", "*exact* = identical number; *rounding* = identical after rounding to the precision the post shows.", "",
              "## Claim by claim", "", "| claim | ledger value | reproduced value | match | notebook | note |", "|---|---|---|---|---|---|"]
    for r in df.itertuples():
        def esc(x):
            return str(x).replace("|", "/").replace("\n", " ")
        match = {"exact": "yes (exact)", "rounding": "yes (rounding)", "qualitative-yes": "yes (check)", "external": "n/a",
                 "MISMATCH": "**NO**", "qualitative-NO": "**NO**", "not covered": "not covered"}.get(r.grade, r.grade)
        lines.append(f"| {r.claim} | {esc(r.ledger)} | {esc(r.reproduced)} | {match} | {r.notebook} | {esc(r.note)} |")
    lines += ["", "## Notebook claims no longer in the ledger (orphaned, skipped)", ""]
    lines += [f"- {c} ({claims[c]['notebook']})" for c in orphans] or ["none"]
    lines.append("")
    (EXTRAS / "verification_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(counts.to_dict())
    print("orphaned notebook claims:", orphans)
    print("wrote", EXTRAS / "verification_report.md")


if __name__ == "__main__":
    main()
