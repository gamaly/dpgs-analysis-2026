"""Assign each repo a confidence tier (only high-confidence repositories and DPGs feed the main results). Reads/writes data/all_repos.csv; also writes data/dpg_confidence.csv."""
from pathlib import Path
import json, re
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
df = pd.read_csv(ROOT / "data/all_repos.csv")
for c in ("fork", "mirror", "archived", "moved", "name_match", "resolved"):
    df[c] = df[c].fillna(False).astype(bool)

# a repo already listed in the registry for a DPG must not also appear as an org-enumerated row for it (G13: duplicate rows)
listed_keys = set(zip(df[df.source == "listed_repo"].dpgid, df[df.source == "listed_repo"].full_name.str.lower()))
dup = (df.source == "org_enumerated") & pd.Series([(a, b.lower()) in listed_keys for a, b in zip(df.dpgid, df.full_name)], index=df.index)
n_dup = int(dup.sum()); df = df[~dup].copy()

# for organisation-only DPGs a rule selects the repositories: a dedicated organisation contributes all its product repositories, any other organisation only name matches: dedicated-org rule for org-only DPGs
norm = lambda x: re.sub(r"[^a-z0-9]", "", str(x).lower())
reg = {d["dpgid"]: d for d in json.load(open(ROOT / "data/raw/registry.json", encoding="utf-8"))}
org_rows = df[df.source == "org_enumerated"]
org_size = org_rows.groupby(["dpgid", "listed"]).size().to_dict()
def dedicated(r):
    names = [r.dpg] + [a for a in reg[r.dpgid].get("aliases") or [] if a]
    keys = {norm(n) for n in names if len(norm(n)) >= 3}
    return any(k in norm(r.listed) for k in keys) and org_size.get((r.dpgid, r.listed), 0) <= 100
df["org_dedicated"] = [(r.source == "org_enumerated") and dedicated(r) for r in df.itertuples()]
NONPRODUCT = re.compile(r"^(\.github|docs?|.*-docs?|documentation|website|site|.*\.github\.io|demo.*|.*-demo|sample.*|example.*|whitepaper)$", re.I)
df["nonproduct_name"] = [bool(NONPRODUCT.match(n.split("/")[-1])) for n in df.full_name]
df["stale_since_2020"] = df.pushed_at.fillna("") < "2020-01-01"

# a repo shared by more than one DPG cannot be attributed cleanly
shared = df.groupby(df.full_name.str.lower()).dpgid.nunique()
df["shared"] = df.full_name.str.lower().map(shared) > 1
review = ROOT / "data/manual_repo_review.csv"  # columns: full_name, decision(include|exclude), note. Hand-verified picks.
rev = pd.read_csv(review).set_index("full_name").decision.to_dict() if review.exists() else {}

def tier(r):
    if not r.resolved: return "excluded", "unresolved"
    if rev.get(r.full_name) == "exclude": return "excluded", "manual_exclude"
    if rev.get(r.full_name) == "include": return "high", "manual_verified"  # hand decision overrides the fork rule 
    if r.fork or r.mirror: return "excluded", "fork_or_mirror"
    if r.shared: return "low", "shared_between_dpgs"
    if r.source == "listed_repo": return "high", "listed_in_registry"
    if r.org_dedicated:  # for organisation-only DPGs a rule selects the repositories: a dedicated organisation contributes all its product repositories, any other organisation only name matches: whole dedicated org minus forks (above), stale and non-product repos
        if r.stale_since_2020: return "excluded", "org_repo_stale_since_2020"
        if r.nonproduct_name: return "excluded", "org_repo_nonproduct_name"
        return "medium", "org_dedicated_rule_D30"
    if r.name_match: return "medium", "org_name_match_unreviewed"
    return "excluded", "org_repo_not_matched"

df[["confidence", "confidence_reason"]] = df.apply(lambda r: pd.Series(tier(r)), axis=1)
df.to_csv(ROOT / "data/all_repos.csv", index=False)

# DPG-level: high only if every repo we attribute to it is high AND no org-only entry is still unreviewed
inc = df[df.confidence != "excluded"]
g = inc.groupby(["dpgid", "dpg"]).agg(n_repos=("full_name", "size"), n_high=("confidence", lambda s: (s == "high").sum()),
                                      n_medium=("confidence", lambda s: (s == "medium").sum()), n_low=("confidence", lambda s: (s == "low").sum())).reset_index()
org_only = set(df[df.source == "org_enumerated"].dpgid)
g["org_only"] = g.dpgid.isin(org_only)
g["dpg_confidence"] = "high"
# a listed repo we could not use (unresolved/fork/mirror) means the DPG's code is incomplete
lost = df[(df.source == "listed_repo") & (df.confidence == "excluded")].groupby("dpgid").size()
g["n_listed_lost"] = g.dpgid.map(lost).fillna(0).astype(int)
g.loc[(g.n_medium > 0) | (g.n_listed_lost > 0), "dpg_confidence"] = "medium"
g.loc[g.n_low > 0, "dpg_confidence"] = "low"
all_dpgs = pd.read_csv(ROOT / "data/dpg_repo_map.csv")[["dpgid", "dpg"]].drop_duplicates()
g = all_dpgs.merge(g, how="left", on=["dpgid", "dpg"]); g["dpg_confidence"] = g.dpg_confidence.fillna("no_usable_repo")
g.to_csv(ROOT / "data/dpg_confidence.csv", index=False)
print(f"removed {n_dup} org rows duplicating a listed repo")
print(df.groupby(["source", "confidence", "confidence_reason"]).size().to_string())
org = df[(df.source == "org_enumerated")]
rep = org.groupby("dpg").agg(org=("listed", "first"), org_repos=("full_name", "size"), dedicated=("org_dedicated", "first"),
        selected=("confidence", lambda x: (x == "medium").sum()), name_match_only=("name_match", lambda x: (x & ~org.loc[x.index, "fork"]).sum())).reset_index()
rep.to_csv(ROOT / "data/org_selection_d30.csv", index=False); print(rep.to_string(index=False))
print(g.dpg_confidence.value_counts().to_string())
