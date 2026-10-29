"""Collect raw GitHub activity per repo via GraphQL, cached as JSON under cache/.
Window: 2020-01-01 .. today (baseline 2020-2023 vs 2024+). Requires env GITHUB_TOKEN. Re-runnable: cached files are skipped.
Usage: python 02_collect_github.py [--limit N]
"""
import json, os, re, sys, time
from pathlib import Path
import pandas as pd, requests

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"
SINCE = "2020-01-01T00:00:00Z"
BODY_CAP = 3000  # chars of PR bodyText kept
URL = "https://api.github.com/graphql"
envf = ROOT / ".env"
if envf.exists():
    for line in envf.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"\''))
S = requests.Session()
S.headers["Authorization"] = f"bearer {os.environ['GITHUB_TOKEN']}"

def gql(query, variables, attempts=8):
    for attempt in range(attempts):
        try: r = S.post(URL, json={"query": query, "variables": variables}, timeout=120)
        except requests.RequestException:
            time.sleep(10 * (attempt + 1)); continue
        if r.status_code in (502, 503, 504):
            time.sleep(5 * (attempt + 1)); continue
        if r.status_code == 403 or r.status_code == 429:
            reset = int(r.headers.get("x-ratelimit-reset", time.time() + 60))
            time.sleep(max(5, reset - time.time() + 2)); continue
        try:
            r.raise_for_status()
            j = r.json()
        except (requests.HTTPError, ValueError):  # HTML error page / truncated body: back off and retry
            print(f"  gql retry {attempt+1}: HTTP {r.status_code}", flush=True)
            time.sleep(10 * (attempt + 1)); continue
        rl = (j.get("data") or {}).get("rateLimit")
        if rl and rl["remaining"] < 50:
            time.sleep(max(5, pd.Timestamp(rl["resetAt"]).timestamp() - time.time() + 2))
        if "errors" in j and not j.get("data"):
            if any(e.get("type") == "NOT_FOUND" for e in j["errors"]): return j
            time.sleep(5 * (attempt + 1)); continue
        return j
    raise RuntimeError("gql failed")

def paginate(owner, name, field, nodes_sel, extra_args="", stop_before=None, page_size=100):
    """stop_before: stop paging once a page's last node has updatedAt < this (needs updatedAt DESC order).
    A page that keeps failing (HTTP 200 with an unreadable body on big payloads) is retried with half the page size.
    Progress is checkpointed to cache/_partial/ every 20 pages so a long repo resumes instead of restarting."""
    ck = CACHE / "_partial" / f"{owner}__{name}__{field.split('(')[0]}.json"
    ck.parent.mkdir(exist_ok=True)
    out, cur = [], None
    if ck.exists():
        st = json.loads(ck.read_text()); out, cur = st["out"], st["cur"]
    pages = 0
    while True:
        q = """query($o:String!,$n:String!,$c:String){rateLimit{remaining resetAt}
      repository(owner:$o,name:$n){ %s(first:%d,after:$c%s){pageInfo{hasNextPage endCursor} nodes{%s}}}}""" % (field, page_size, extra_args, nodes_sel)
        try: j = gql(q, {"o": owner, "n": name, "c": cur}, attempts=3)
        except RuntimeError:
            if page_size <= 10: raise
            page_size = max(10, page_size // 2); print(f"  {owner}/{name} {field}: page size -> {page_size}", flush=True); continue
        repo = (j.get("data") or {}).get("repository")
        if not repo: return None
        blk = repo[field.split("(")[0]]
        for n in blk["nodes"]:  # keep PR text for AI-mention analysis (03c), capped to bound cache size
            if n.get("bodyText"): n["bodyText"] = n["bodyText"][:BODY_CAP]
        out += blk["nodes"]; pages += 1
        done = not blk["pageInfo"]["hasNextPage"] or (stop_before and blk["nodes"] and blk["nodes"][-1]["updatedAt"] < stop_before)
        if done:
            ck.unlink(missing_ok=True); return out
        cur = blk["pageInfo"]["endCursor"]
        if pages % 20 == 0: ck.write_text(json.dumps({"out": out, "cur": cur}))

AUTH = "author{login __typename}"
PR = ("updatedAt createdAt mergedAt closedAt state title bodyText isDraft additions deletions changedFiles "
      "mergedBy{login} reviews(first:10){nodes{submittedAt author{login}}} labels(first:10){nodes{name}} " + AUTH)
ISSUE = "updatedAt createdAt closedAt state"
REL = "createdAt publishedAt tagName isPrerelease"

def meta(owner, name):
    q = """query($o:String!,$n:String!){repository(owner:$o,name:$n){nameWithOwner url createdAt pushedAt isArchived isFork isMirror
      stargazerCount forkCount defaultBranchRef{name} primaryLanguage{name}
      parent{nameWithOwner} licenseInfo{spdxId}}}"""
    return gql(q, {"o": owner, "n": name})

def commits(owner, name):
    size, out, cur = 100, [], None
    ck = CACHE / "_partial" / f"{owner}__{name}__commits.json"; ck.parent.mkdir(exist_ok=True)
    if ck.exists():
        st = json.loads(ck.read_text()); out, cur = st["out"], st["cur"]
    pages = 0
    while True:
        q = """query($o:String!,$n:String!,$c:String){rateLimit{remaining resetAt}repository(owner:$o,name:$n){defaultBranchRef{target{... on Commit{
      history(first:%d,after:$c,since:"%s"){pageInfo{hasNextPage endCursor} nodes{committedDate message messageHeadline author{name email user{login}}}}}}}}}""" % (size, SINCE)
        try: j = gql(q, {"o": owner, "n": name, "c": cur}, attempts=3)
        except RuntimeError:
            if size <= 10: raise
            size = max(10, size // 2); print(f"  {owner}/{name} commits: page size -> {size}", flush=True); continue
        ref = ((j.get("data") or {}).get("repository") or {}).get("defaultBranchRef")
        if not ref: return out
        h = ref["target"]["history"]
        for n in h["nodes"]:  # keep headline + body capped, flag trailers
            msg = n.pop("message", "")
            n["messageBody"] = msg[len(n.get("messageHeadline", "")):][:BODY_CAP].strip()
            n["ai_trailer"] = any(k in msg.lower() for k in ("co-authored-by: claude", "co-authored-by: copilot", "co-authored-by: cursor", "generated with claude", "codex", "aider:"))
        out += h["nodes"]; pages += 1
        if not h["pageInfo"]["hasNextPage"]:
            ck.unlink(missing_ok=True); return out
        cur = h["pageInfo"]["endCursor"]
        if pages % 20 == 0: ck.write_text(json.dumps({"out": out, "cur": cur}))

def collect(full):
    f = CACHE / (full.replace("/", "__") + ".json")
    if f.exists(): return
    owner, name = full.split("/")
    m = meta(owner, name)
    repo = (m.get("data") or {}).get("repository")
    if not repo:
        f.write_text(json.dumps({"full_name": full, "status": "not_found"})); return
    # nameWithOwner differs from input => repo was renamed/moved (GitHub redirect followed)
    pr = paginate(owner, name, "pullRequests", PR, ",orderBy:{field:UPDATED_AT,direction:DESC}", SINCE, page_size=50)  # 100/page 502s on PR-heavy repos; 50 is stable (~3s/page, 1 point/page)
    iss = paginate(owner, name, "issues", ISSUE, ",orderBy:{field:UPDATED_AT,direction:DESC}", SINCE)
    rel = paginate(owner, name, "releases", REL)
    tags = paginate(owner, name, "refs", "name target{... on Commit{committedDate} ... on Tag{tagger{date}}}", ',refPrefix:"refs/tags/"')
    f.write_text(json.dumps({"full_name": full, "status": "ok", "meta": repo, "renamed": repo["nameWithOwner"].lower() != full.lower(),
        "prs": pr, "issues": iss, "releases": rel, "tags": tags, "commits": commits(owner, name)}))

ORG_POOL = 30  # candidate repos per org (top by stars, non-fork, pushed since SINCE)
ORG_FALLBACK = 3  # if no repo name matches the DPG, keep this many top-starred repos

def org_repos(org):
    """Top ORG_POOL repos for an org, with stars. Failures are not cached."""
    f = CACHE / f"_orgpool_{org}.json"
    if f.exists(): return json.loads(f.read_text())
    q = f"user:{org} fork:false pushed:>={SINCE[:10]}"
    for attempt in range(8):
        r = S.get("https://api.github.com/search/repositories",
                  params={"q": q, "sort": "stars", "order": "desc", "per_page": ORG_POOL})
        if r.status_code not in (403, 429): break
        wait = int(r.headers.get("retry-after", 0)) or 60 * (attempt + 1)  # secondary limit: back off
        print(f"  search limited, sleeping {wait}s", flush=True); time.sleep(wait)
    r.raise_for_status()
    b = r.json()
    out = {"org": org, "total_matching": b["total_count"],
           "pool": [{"full_name": x["full_name"], "stars": x["stargazers_count"], "archived": x["archived"]} for x in b["items"]]}
    f.write_text(json.dumps(out))
    time.sleep(2)  # search API: 30 req/min
    return out

def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())

def pick_org_repos(dpg_names, pool):
    """Repos in the org whose name contains (or is contained in) the DPG name or an alias."""
    keys = {norm(n) for n in dpg_names if len(norm(n)) >= 3}
    hits = []
    for p in pool:
        rn = norm(p["full_name"].split("/")[1])
        if any(k in rn or rn in k for k in keys):
            hits.append(p)
    if hits: return hits, "name_match"
    return pool[:ORG_FALLBACK], "top_stars_fallback"

if __name__ == "__main__":
    CACHE.mkdir(exist_ok=True)
    inv = pd.read_csv(ROOT / "data/all_repos.csv")  # from 02a/02b; tiers per METHODOLOGY.md D14
    tiers = sys.argv[sys.argv.index("--tiers") + 1].split(",") if "--tiers" in sys.argv else ["high", "medium"]
    inv = inv[inv.confidence.isin(tiers)].drop_duplicates("full_name")
    size = pd.read_csv(ROOT / "data/repo_size.csv").set_index("full_name").est_points.to_dict() if (ROOT / "data/repo_size.csv").exists() else {}
    conf = inv.set_index("full_name").confidence.to_dict()
    repos = sorted(conf, key=lambda x: (conf[x] != "high", size.get(x, 0), x.lower()))  # high first; small repos first so data lands early
    full_run = not any(a in sys.argv for a in ("--limit", "--repos", "--select-only", "--tiers", "--reverse"))
    if "--limit" in sys.argv: repos = repos[: int(sys.argv[sys.argv.index("--limit") + 1])]
    if "--repos" in sys.argv: repos = sys.argv[sys.argv.index("--repos") + 1].split(",")
    if "--reverse" in sys.argv: repos = repos[::-1]  # second process working from the big end; collect() skips cached repos
    if "--select-only" in sys.argv: sys.exit()
    if full_run: pd.DataFrame({"full_name": repos}).to_csv(ROOT / "data/repos_to_collect.csv", index=False)  # partial runs must not clobber it
    from concurrent.futures import ThreadPoolExecutor
    def job(ir):
        i, r = ir
        print(f"[{i}/{len(repos)}] {r}", flush=True)
        try: collect(r)
        except Exception as e: print("  FAILED", r, e, flush=True)
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 4
    with ThreadPoolExecutor(workers) as ex: list(ex.map(job, enumerate(repos, 1)))
