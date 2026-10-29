"""Clean the DPG registry into a DPG->repo mapping. Input: data/raw/registry.json"""
import json, re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
reg = json.load(open(ROOT / "data/raw/registry.json", encoding="utf-8"))

GH = re.compile(r"github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)", re.I)
GL = re.compile(r"gitlab\.[a-z.]+/([A-Za-z0-9_./-]+)", re.I)
RESERVED = {"orgs", "sponsors", "topics", "features", "marketplace"}

def clean_repo(name):
    name = re.sub(r"\.git$", "", name)
    return name.rstrip(".")  # registry typos like "patient-service."

rows, nocode = [], []
for d in reg:
    cats = [c for c in d.get("categories", []) if c]
    base = dict(dpgid=d["dpgid"], dpg=d["name"], categories="|".join(cats),
                sectors="|".join(s for s in d.get("sectors", []) if s),
                sdgs="|".join(d.get("sdgs", {}).get("sdg", [])),
                orgs="|".join(f'{o.get("name")}:{o.get("org_type")}' for o in d.get("organizations", [])))
    found = 0
    for r in d.get("repositories") or []:
        raw = r.get("url") or ""
        # split messy multi-URL strings
        for part in re.split(r"[,\s;]+", raw):
            if not part:
                continue
            m = GH.search(part)
            if m and m.group(1).lower() not in RESERVED:
                rows.append({**base, "host": "github", "repo_label": r.get("name"),
                             "raw_url": raw.strip(), "full_name": f"{m.group(1)}/{clean_repo(m.group(2))}"})
                found += 1
                continue
            mo = re.search(r"github\.com/([A-Za-z0-9_-]+)/?$", part, re.I)
            if mo and mo.group(1).lower() not in RESERVED:
                rows.append({**base, "host": "github_org", "repo_label": r.get("name"),
                             "raw_url": raw.strip(), "full_name": mo.group(1)})
                found += 1
                continue
            m = GL.search(part)
            if m:
                path = re.split(r"/-/|/blob/|/tree/", m.group(1))[0].rstrip("/")
                rows.append({**base, "host": "gitlab", "repo_label": r.get("name"),
                             "raw_url": raw.strip(), "full_name": clean_repo(path)})
                found += 1
    if not found:
        nocode.append({**base, "repos_raw": json.dumps(d.get("repositories"))})

df = pd.DataFrame(rows).drop_duplicates(["dpgid", "host", "full_name"])
df["full_name_lc"] = df.full_name.str.lower()
df.to_csv(ROOT / "data/dpg_repo_map.csv", index=False)
pd.DataFrame(nocode).to_csv(ROOT / "data/dpgs_without_code_repo.csv", index=False)
print(f"DPGs: {len(reg)}; with GitHub repo: {df[df.host=='github'].dpgid.nunique()}; org-only: {df[df.host=='github_org'].dpgid.nunique()}; "
      f"with GitLab: {df[df.host=='gitlab'].dpgid.nunique()}; no code repo: {len(nocode)}")
print(f"unique GitHub repos: {df[df.host=='github'].full_name_lc.nunique()}; "
      f"repos shared by >1 DPG: {(df.groupby('full_name_lc').dpgid.nunique()>1).sum()}")
