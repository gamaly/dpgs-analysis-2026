"""P8 / Q3 (METHODOLOGY D36, measure 1): which collected repos declare an AI library in a dependency manifest?
List of libraries is FIXED below (D36); changes must be logged in METHODOLOGY before results are read.
Steps (each cached, resumable):
  1. file list per repo: REST git trees API (recursive) -> manifest paths      [needs GITHUB_TOKEN, 1 REST call/repo]
  2. manifest text from raw.githubusercontent.com (no API budget)               [cache/deps/<owner>__<repo>.json]
  3. parse offline -> data/ai_dependencies.csv (one row per repo/file/library), data/ai_dependencies_repo.csv (one row per repo)
Only repos already collected by G1 (cache/<owner>__<repo>.json, status ok) in tiers high+medium (D14).
Fetching is gated: it needs --gh-clear (GH has announced on the board that G1 is done and the token is free; M0018).
Usage: python -I scripts/03e_ai_dependencies.py --dry-run | --gh-clear [--limit N] | --parse-only
"""
import json, os, re, sys, time, tomllib
from pathlib import Path
import pandas as pd, requests

ROOT = Path(__file__).resolve().parent.parent
CACHE, DATA = ROOT / "cache", ROOT / "data"
DEPS = CACHE / "deps"
MAX_MANIFESTS, MAX_BYTES = 40, 300_000

# --- D36 fixed library list (normalised names: lowercase, '_' and '.' -> '-') -------------------------------------
LLM = {"openai", "anthropic", "@anthropic-ai/sdk", "google-generativeai", "@google/genai", "litellm", "ollama", "mistralai", "cohere"}
LLM_PREFIX = ("langchain", "@langchain/", "llama-index")  # langchain*, llama-index/llama_index
ML = {"scikit-learn", "tensorflow", "torch", "pytorch", "keras", "xgboost", "lightgbm", "transformers", "spacy", "onnxruntime"}
ML_ALIAS = {"sklearn": "scikit-learn"}  # old PyPI alias of scikit-learn; counted as the same library
EXCLUDED_GROUPS = re.compile(r"(^|[-_.])(dev|test|tests|testing|doc|docs|lint|ci|style|typing|benchmark)s?($|[-_.])", re.I)
MANIFEST = re.compile(r"(^|/)(package\.json|requirements[^/]*\.txt|pyproject\.toml|setup\.py|setup\.cfg|Pipfile|environment\.ya?ml|pom\.xml|"
                      r"build\.gradle(\.kts)?|go\.mod|Gemfile|composer\.json|Cargo\.toml|[^/]+\.csproj)$")
SKIP_DIR = re.compile(r"(^|/)(node_modules|vendor|third[-_]party|\.git|dist|build|test|tests|testdata|fixtures?|docs?|examples?)/", re.I)

def norm(n):
    n = re.split(r"[\[<>=!~;@ ]", n.strip().lower(), maxsplit=1)[0] if not n.strip().startswith("@") else n.strip().lower()
    return n.replace("_", "-").replace(".", "-")

def classify(name):
    n = norm(name)
    n = ML_ALIAS.get(n, n)
    if n in LLM or n.startswith(LLM_PREFIX): return n, "llm_genai"
    if n in ML: return n, "classic_ml"
    return None

def hit(out, name, section, method):
    c = classify(name)
    if c: out.append((c[0], c[1], section, method))

def scan(path, text):
    """-> list of (library, class, section, method). Dev/test/docs groups excluded where the format separates them."""
    out, base = [], path.rsplit("/", 1)[-1]
    try:
        if base == "package.json":
            j = json.loads(text)
            for sec in ("dependencies", "peerDependencies", "optionalDependencies"):
                for k in (j.get(sec) or {}): hit(out, k, sec, "parsed")
        elif base == "composer.json":
            for k in (json.loads(text).get("require") or {}): hit(out, k.split("/")[-1], "require", "parsed")
        elif base == "pyproject.toml":
            t = tomllib.loads(text)
            for d in (t.get("project", {}).get("dependencies") or []): hit(out, d, "project.dependencies", "parsed")
            for g, ds in (t.get("project", {}).get("optional-dependencies") or {}).items():
                if not EXCLUDED_GROUPS.search(g):
                    for d in ds: hit(out, d, f"optional:{g}", "parsed")
            po = t.get("tool", {}).get("poetry", {})
            for k in (po.get("dependencies") or {}): hit(out, k, "poetry.dependencies", "parsed")
            for g, v in (po.get("group") or {}).items():
                if not EXCLUDED_GROUPS.search(g):
                    for k in (v.get("dependencies") or {}): hit(out, k, f"poetry.group.{g}", "parsed")
        elif base == "Pipfile":
            for k in (tomllib.loads(text).get("packages") or {}): hit(out, k, "packages", "parsed")
        elif base == "Cargo.toml":
            for k in (tomllib.loads(text).get("dependencies") or {}): hit(out, k, "dependencies", "parsed")
        elif base.startswith("requirements") and base.endswith(".txt"):
            if EXCLUDED_GROUPS.search(base[:-4]): return out
            for line in text.splitlines():
                line = line.split("#")[0].strip()
                if line and not line.startswith(("-", "git+", "http")): hit(out, line, "requirements", "parsed")
        else:  # setup.py/cfg, environment.yml, pom.xml, gradle, go.mod, Gemfile, csproj: token search on dependency-looking text
            for lib in sorted(LLM | ML | set(ML_ALIAS)):
                if re.search(r"(?<![\w@/.-])" + re.escape(lib) + r"(?![\w])", text, re.I): hit(out, lib, "text", "text")
            if re.search(r"(?<![\w@/.-])(langchain|llama[-_]index)[\w-]*", text, re.I):
                m = re.search(r"(?<![\w@/.-])(langchain|llama[-_]index)[\w-]*", text, re.I); hit(out, m.group(0), "text", "text")
    except Exception as e:  # unparseable manifest: record nothing, count it
        out.append(("__parse_error__", "error", str(e)[:60], "parsed"))
    return out

def env_token():
    envf = ROOT / ".env"
    if envf.exists():
        for line in envf.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip().strip("\"'"))
    return os.environ["GITHUB_TOKEN"]

def repos():
    inv = pd.read_csv(DATA / "all_repos.csv").drop_duplicates("full_name")
    tier = {k.lower(): v for k, v in zip(inv.full_name, inv.confidence)}
    out = []
    for f in sorted(CACHE.glob("*__*.json")):
        if f.name.startswith(("_", "inv_")): continue
        d = json.loads(f.read_text())
        if d.get("status") == "ok" and tier.get(d["full_name"].lower()) in ("high", "medium"):
            out.append((d["full_name"], tier[d["full_name"].lower()], d["meta"].get("nameWithOwner", d["full_name"])))
    return out

def fetch(full, live, S):
    f = DEPS / (full.replace("/", "__") + ".json")
    if f.exists(): return
    r = S.get(f"https://api.github.com/repos/{live}/git/trees/HEAD?recursive=1", timeout=60)
    while r.status_code in (403, 429):  # rate limit: wait out
        time.sleep(max(30, int(r.headers.get("x-ratelimit-reset", time.time() + 60)) - time.time() + 2)); r = S.get(r.url, timeout=60)
    if r.status_code != 200:
        f.write_text(json.dumps({"full_name": full, "status": f"tree_http_{r.status_code}"})); return
    tree = r.json()
    paths = [t["path"] for t in tree.get("tree", []) if t["type"] == "blob" and MANIFEST.search(t["path"]) and not SKIP_DIR.search(t["path"])]
    paths = sorted(paths, key=lambda p: (p.count("/"), p))[:MAX_MANIFESTS]
    man = {}
    for p in paths:
        x = requests.get(f"https://raw.githubusercontent.com/{live}/HEAD/{p}", timeout=60)
        if x.status_code == 200 and len(x.content) <= MAX_BYTES: man[p] = x.text
    f.write_text(json.dumps({"full_name": full, "status": "ok", "truncated": bool(tree.get("truncated")), "n_manifests_found": len(paths), "manifests": man}))

def parse():
    rows, per = [], []
    for full, tier, _ in repos():
        f = DEPS / (full.replace("/", "__") + ".json")
        if not f.exists(): continue
        d = json.loads(f.read_text())
        hits = []
        for p, text in (d.get("manifests") or {}).items():
            for lib, cls, sec, meth in scan(p, text):
                rows.append({"full_name": full, "tier": tier, "file": p, "library": lib, "class": cls, "section": sec, "method": meth})
                if cls != "error": hits.append(cls)
        per.append({"full_name": full, "tier": tier, "status": d.get("status"), "tree_truncated": d.get("truncated"),
                    "n_manifests": len(d.get("manifests") or {}), "ships_llm": "llm_genai" in hits, "ships_classic_ml": "classic_ml" in hits})
    pd.DataFrame(rows, columns=["full_name", "tier", "file", "library", "class", "section", "method"]).to_csv(DATA / "ai_dependencies.csv", index=False)
    r = pd.DataFrame(per); r.to_csv(DATA / "ai_dependencies_repo.csv", index=False)
    print(f"repos scanned {len(r)}; with a manifest {int((r.n_manifests > 0).sum())}; LLM {int(r.ships_llm.sum())}; classic ML {int(r.ships_classic_ml.sum())}; "
          f"tree truncated {int(r.tree_truncated.fillna(False).sum())}; parse errors {sum(1 for x in rows if x['class']=='error')}")

if __name__ == "__main__":
    DEPS.mkdir(exist_ok=True)
    rs = repos()
    if "--limit" in sys.argv: rs = rs[: int(sys.argv[sys.argv.index("--limit") + 1])]
    todo = [r for r in rs if not (DEPS / (r[0].replace("/", "__") + ".json")).exists()]
    print(f"collected high+medium repos: {len(rs)}; manifests not yet fetched: {len(todo)}")
    if "--dry-run" in sys.argv: sys.exit()
    if "--parse-only" not in sys.argv:
        if "--gh-clear" not in sys.argv:
            sys.exit("Not fetching: needs --gh-clear (GH announced G1 complete and the token is free). Use --parse-only to parse cached manifests.")
        S = requests.Session(); S.headers["Authorization"] = f"bearer {env_token()}"
        for i, (full, _, live) in enumerate(todo, 1):
            print(f"[{i}/{len(todo)}] {full}", flush=True)
            try: fetch(full, live, S)
            except Exception as e: print("  FAILED", type(e).__name__)
    parse()
