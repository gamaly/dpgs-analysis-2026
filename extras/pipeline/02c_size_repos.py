"""Cheap pre-count of PRs / issues / commits per repo (about 1 point per 25 repos) to order the collection and estimate its cost.
Writes data/repo_size.csv. Requires GITHUB_TOKEN (.env)."""
import importlib.util as u, sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parent.parent
sp = u.spec_from_file_location("c", ROOT / "scripts/02_collect_github.py"); c = u.module_from_spec(sp); sp.loader.exec_module(c)
inv = pd.read_csv(ROOT / "data/all_repos.csv")
repos = sorted(inv[inv.confidence.isin(["high", "medium"])].full_name.drop_duplicates())
rows = []
for i in range(0, len(repos), 25):
    chunk = repos[i:i + 25]
    body = " ".join(f'r{k}: repository(owner:"{r.split("/")[0]}",name:"{r.split("/")[1]}"){{nameWithOwner pushedAt isArchived '
                    f'pullRequests{{totalCount}} issues{{totalCount}} '
                    f'defaultBranchRef{{target{{... on Commit{{history(since:"{c.SINCE}"){{totalCount}}}}}}}}}}' for k, r in enumerate(chunk))
    j = c.gql("query{rateLimit{remaining resetAt} " + body + "}", {})
    for k, r in enumerate(chunk):
        x = (j.get("data") or {}).get(f"r{k}")
        if not x: rows.append(dict(full_name=r, found=False)); continue
        ref = x.get("defaultBranchRef")
        rows.append(dict(full_name=r, found=True, pushed_at=x["pushedAt"], archived=x["isArchived"], prs_total=x["pullRequests"]["totalCount"],
                         issues_total=x["issues"]["totalCount"], commits_since_2020=ref["target"]["history"]["totalCount"] if ref else 0))
df = pd.DataFrame(rows)
# cost model: PR pages of 25 at ~20 pts, issue/commit/release pages of 100 at ~1-2 pts (note: 5,000 pts/hr)
df["est_points"] = (df.prs_total.fillna(0) / 25 * 20 + (df.issues_total.fillna(0) + df.commits_since_2020.fillna(0)) / 100 * 2).round()
df.sort_values("est_points").to_csv(ROOT / "data/repo_size.csv", index=False)
print(f"repos {len(df)}, not found {(~df.found).sum()}, est total points {df.est_points.sum():,.0f} (~{df.est_points.sum()/5000:.1f} h at 5,000/h)")
print(df.est_points.describe().round(0).to_string()); print(df.sort_values("est_points", ascending=False).head(8)[["full_name", "prs_total", "est_points"]].to_string(index=False))
