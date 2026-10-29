"""Full repo inventory: every directly listed repo (resolved live) + every non-fork repo in each listed org.
Writes data/all_repos.csv (one row per repo, with source, status, name_match flag). Raw API pages cached in cache/inv_*.json."""
import json, os, re, time
from pathlib import Path
import pandas as pd, requests

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"; CACHE.mkdir(exist_ok=True)
for line in (ROOT / ".env").read_text().splitlines():
    if "=" in line and not line.lstrip().startswith("#"):
        k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip().strip("\"'"))
S = requests.Session()
S.headers.update({"Authorization": f"bearer {os.environ['GITHUB_TOKEN']}", "Accept": "application/vnd.github+json"})
norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())

def get(url, **params):
    for a in range(6):
        r = S.get(url, params=params, timeout=60)
        if r.status_code in (403, 429) and r.headers.get("x-ratelimit-remaining") == "0":
            time.sleep(max(5, int(r.headers["x-ratelimit-reset"]) - time.time() + 2)); continue
        if r.status_code in (403, 429): time.sleep(30 * (a + 1)); continue
        return r
    return r

def cached(name, fn):
    f = CACHE / f"inv_{name}.json"
    if f.exists(): return json.loads(f.read_text())
    out = fn(); f.write_text(json.dumps(out)); return out

def org_all(org):
    out = []
    for kind in ("orgs", "users"):
        page, out = 1, []
        while True:
            r = get(f"https://api.github.com/{kind}/{org}/repos", per_page=100, page=page, type="owner")
            if r.status_code != 200: break
            b = r.json(); out += b
            if len(b) < 100: break
            page += 1
        if out or r.status_code == 200: break
    return out

def one(full):
    r = get(f"https://api.github.com/repos/{full}")
    return r.json() if r.status_code == 200 else {"_status": r.status_code, "full_name": full}

m = pd.read_csv(ROOT / "data/dpg_repo_map.csv")
reg = {d["dpgid"]: d for d in json.load(open(ROOT / "data/raw/registry.json", encoding="utf-8"))}
rows = []
for r in m[m.host == "github"].itertuples():
    x = cached("repo_" + r.full_name.replace("/", "__"), lambda: one(r.full_name))
    ok = "_status" not in x
    rows.append(dict(dpgid=r.dpgid, dpg=r.dpg, source="listed_repo", listed=r.full_name, full_name=x.get("full_name", r.full_name),
        resolved=ok, http_status=x.get("_status", 200), moved=ok and x["full_name"].lower() != r.full_name.lower(),
        fork=x.get("fork"), mirror=bool(x.get("mirror_url")), archived=x.get("archived"), pushed_at=x.get("pushed_at"),
        stars=x.get("stargazers_count"), name_match=True))
for r in m[m.host == "github_org"].itertuples():
    keys = {norm(n) for n in [r.dpg] + [a for a in reg[r.dpgid].get("aliases") or [] if a] if len(norm(n)) >= 3}
    for x in cached("org_" + r.full_name, lambda: org_all(r.full_name)):
        rn = norm(x["name"])
        rows.append(dict(dpgid=r.dpgid, dpg=r.dpg, source="org_enumerated", listed=r.full_name, full_name=x["full_name"], resolved=True,
            http_status=200, moved=False, fork=x["fork"], mirror=bool(x.get("mirror_url")), archived=x["archived"],
            pushed_at=x["pushed_at"], stars=x["stargazers_count"], name_match=any(k in rn or rn in k for k in keys)))
df = pd.DataFrame(rows)
df.to_csv(ROOT / "data/all_repos.csv", index=False)
d = df[df.source == "listed_repo"]
print(f"listed repos: {len(d)}, resolved {d.resolved.sum()}, not found {(~d.resolved).sum()}, moved/renamed {d.moved.sum()}, fork {d.fork.sum()}, mirror {d.mirror.sum()}, archived {d.archived.sum()}")
o = df[df.source == "org_enumerated"]
print(f"org-enumerated: {len(o)} repos across {o.dpg.nunique()} DPGs; non-fork {(~o.fork).sum()}; non-fork & pushed>=2020 {((~o.fork) & (o.pushed_at >= '2020')).sum()}")
print(o[~o.fork].groupby('dpg').size().sort_values(ascending=False).to_string())
