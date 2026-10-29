"""R1 step 1 : per-file history of the archived DPGAlliance/publicgoods-candidates repo.

Reads the local clone at cache/hist/pgc (git clone, no API budget). For every file that was ever in
digitalpublicgoods/ (or carried "stage": "DPG"), walks its history (--follow) and records:
  first_nominee, first_candidate, first_stage_dpg (first version whose JSON has stage == "DPG"),
  first_in_dpg_dir (first commit where the path is under digitalpublicgoods/), last_seen, deleted flag.
Output: data/hist_pgc_lineages.csv (one row per file lineage; matching to dpgid is in 10_cert_dates.py).
Run: python -I scripts/10_cert_history.py
"""
import csv, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PGC = ROOT / "cache" / "hist" / "pgc"
OUT = ROOT / "data" / "hist_pgc_lineages.csv"


def git(*args):
    r = subprocess.run(["git", "-C", str(PGC), *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.stdout


def paths_ever_in_dpg_dir():
    names = set()
    for line in git("log", "--name-only", "--format=", "--", "digitalpublicgoods").splitlines():
        if line.startswith("digitalpublicgoods/") and line.endswith(".json"):
            names.add(line)
    return sorted(names)


def lineage(path):
    """Commits oldest->newest as (sha, date, path_after, status) following renames."""
    out = git("log", "--follow", "-M", "--name-status", "--format=@%H %ad", "--date=short", "--", path)
    commits, cur = [], None
    for line in out.splitlines():
        if line.startswith("@"):
            sha, date = line[1:].split()
            cur = [sha, date, None, None]
            commits.append(cur)
        elif line.strip() and cur is not None and cur[2] is None:
            parts = line.split("\t")
            cur[3] = parts[0][0]
            cur[2] = parts[-1]
    commits.reverse()
    return [c for c in commits if c[2]]


def stage_at(sha, p):
    txt = git("show", f"{sha}:{p}")
    if not txt.strip():
        return None, None
    try:
        d = json.loads(txt.lstrip("﻿"))
    except Exception:
        return None, None
    return d.get("stage"), d.get("name")


def main():
    rows = []
    paths = paths_ever_in_dpg_dir()
    print(len(paths), "paths ever in digitalpublicgoods/", file=sys.stderr)
    for i, p in enumerate(paths):
        cs = lineage(p)
        if not cs:
            continue
        first = {"nominee": "", "candidate": "", "dpg_stage": "", "dpg_dir": ""}
        name = ""
        for sha, date, pa, st in cs:
            if st == "D":
                continue
            top = pa.split("/")[0]
            if top == "nominees" and not first["nominee"]:
                first["nominee"] = date
            if top == "candidates" and not first["candidate"]:
                first["candidate"] = date
            if top == "digitalpublicgoods" and not first["dpg_dir"]:
                first["dpg_dir"] = date
            stg, nm = stage_at(sha, pa)
            name = nm or name
            if stg == "DPG" and not first["dpg_stage"]:
                first["dpg_stage"] = date
            if stg == "candidate" and not first["candidate"]:
                first["candidate"] = date
            if stg == "nominee" and not first["nominee"]:
                first["nominee"] = date
        exists = (PGC / p).exists()
        rows.append({
            "path": p, "slug": Path(p).stem, "name_in_file": name,
            "first_commit": cs[0][1], "first_path": cs[0][2],
            "first_nominee": first["nominee"], "first_candidate": first["candidate"],
            "first_stage_dpg": first["dpg_stage"], "first_in_dpg_dir": first["dpg_dir"],
            "last_commit": cs[-1][1], "present_at_archive": exists,
        })
        if i % 25 == 0:
            print(i, file=sys.stderr)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print("wrote", OUT, len(rows))


if __name__ == "__main__":
    main()
