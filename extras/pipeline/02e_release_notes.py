"""Q3 (AI features are measured from dependency manifests and from PR text): fetch release notes (name, description) since 2020 for high/medium repos of DPGs with AI-feature PRs.
  python -I scripts/02e_release_notes.py [--limit N]  -> cache/release_notes/<owner>__<repo>.json (skips cached)
Token from .env GITHUB_TOKEN (never printed)."""
import json, re, sys, time
from pathlib import Path
import pandas as pd, requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "cache/release_notes"; OUT.mkdir(parents=True, exist_ok=True)
SINCE = "2020-01-01"
Q = """query($o:String!,$n:String!,$first:Int!,$after:String){rateLimit{remaining resetAt}
repository(owner:$o,name:$n){releases(first:$first,after:$after,orderBy:{field:CREATED_AT,direction:DESC}){
pageInfo{hasNextPage endCursor} nodes{name description tagName publishedAt createdAt isPrerelease}}}}"""


def token():
    for l in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*GITHUB_TOKEN\s*=\s*(.+?)\s*$", l)
        if m: return m.group(1).strip("'\"")
    sys.exit("no token")


def post(s, vars_):
    for attempt in range(8):
        try:
            r = s.post("https://api.github.com/graphql", json={"query": Q, "variables": vars_}, timeout=90)
        except requests.RequestException:
            time.sleep(10); continue
        if r.status_code in (502, 504): return "shrink"
        if r.status_code in (403, 429):
            time.sleep(int(r.headers.get("Retry-After", 60)) + 5); continue
        if r.status_code != 200:
            return {"errors": [{"message": f"http {r.status_code}"}]}
        j = r.json()
        rl = (j.get("data") or {}).get("rateLimit")
        if rl and rl["remaining"] < 100:
            reset = pd.Timestamp(rl["resetAt"]).timestamp()
            time.sleep(max(5, reset - time.time() + 5))
        return j
    return {"errors": [{"message": "retries exhausted"}]}


def fetch(s, full):
    o, n = full.split("/", 1)
    out, after, size = [], None, 50
    while True:
        j = post(s, {"o": o, "n": n, "first": size, "after": after})
        if j == "shrink":
            if size <= 5: return {"status": "error", "error": "502/504"}
            size = max(5, size // 2); time.sleep(3); continue
        if j.get("errors") and not (j.get("data") or {}).get("repository"):
            return {"status": "error", "error": j["errors"][0]["message"][:200]}
        conn = j["data"]["repository"]["releases"]
        stop = False
        for r in conn["nodes"]:
            if (r["createdAt"] or "") < SINCE: stop = True; break
            out.append(r)
        if stop or not conn["pageInfo"]["hasNextPage"]: break
        after = conn["pageInfo"]["endCursor"]; time.sleep(0.5)
    return {"status": "ok", "full_name": full, "releases": out}


def main():
    ai = pd.read_csv(ROOT / "data/ai_feature_prs.csv")
    a = pd.read_csv(ROOT / "data/all_repos.csv", low_memory=False).drop_duplicates("full_name")
    a = a[a.dpgid.isin(ai.dpgid.unique()) & a.confidence.isin(["high", "medium"]) & (a.resolved == True)]
    repos = sorted(a.full_name)
    lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    s = requests.Session(); s.headers["Authorization"] = "bearer " + token()
    done = 0
    for full in repos:
        f = OUT / (full.replace("/", "__") + ".json")
        if f.exists(): continue
        if lim is not None and done >= lim: break
        d = fetch(s, full); f.write_text(json.dumps(d), encoding="utf-8"); done += 1
        print(full, d["status"], len(d.get("releases", [])), flush=True); time.sleep(0.5)
    print("repos:", len(repos), "fetched now:", done)


if __name__ == "__main__":
    main()
