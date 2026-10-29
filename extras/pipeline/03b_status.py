"""Repo and DPG status: active / slowing / dormant (METHODOLOGY D32). Run: python -I scripts/03b_status.py"""
import json, re
from pathlib import Path
import pandas as pd
import importlib.util as u

ROOT = Path(__file__).resolve().parent.parent
sp = u.spec_from_file_location("agg", ROOT / "scripts/03_aggregate.py"); agg = u.module_from_spec(sp); sp.loader.exec_module(agg)

REF = pd.Timestamp("2026-10-29")
R0, P0 = REF - pd.DateOffset(months=12), REF - pd.DateOffset(months=24)

def repo_status(d):
    ev = []  # timestamps of events (D32)
    bot_merges = 0
    for p in d.get("prs") or []:
        if not p.get("mergedAt"): continue
        au = p.get("author") or {}
        cls = agg.actor_class(au.get("login"), au.get("__typename"))
        t = agg.ts(p["mergedAt"])
        if cls in ("human", "ai_agent", "unknown"): ev.append(t)
        elif cls == "dep_bot" and t >= R0: bot_merges += 1
    kinds, method = agg.release_kinds(d.get("releases"), d.get("tags"))
    ev += [t for t, k in kinds]
    pre = [agg.ts(x["publishedAt"] or x["createdAt"]) for x in d.get("releases") or [] if x["isPrerelease"]]  # sensitivity only (D32 note)
    def label(events):
        s = pd.Series(events, dtype="datetime64[ns]")
        r = int(((s > R0) & (s <= REF)).sum()); p_ = int(((s > P0) & (s <= R0)).sum())
        return ("dormant" if r == 0 else ("slowing" if (r < 0.5 * p_ and p_ >= 6) else "active")), r, p_, s
    status, r, p_, s = label(ev)
    status_incl_pre = label(ev + pre)[0]
    hc = sum(1 for c in d.get("commits") or [] if agg.ts(c["committedDate"]) > R0 and agg.actor_class((c.get("author") or {}).get("user", {}) and (c["author"]["user"] or {}).get("login")) in ("human", "unknown"))
    last = s.max() if len(s) else pd.NaT
    return dict(full_name=d["full_name"], status=status, status_incl_prerelease=status_incl_pre, events_last12=r, events_prior12=p_, last_event_date=last.date() if pd.notna(last) else None,
                dormant_since=(last + pd.DateOffset(months=12)).date() if pd.notna(last) and status == "dormant" else None,
                human_commits_12m=hc, dep_bot_merges_12m=bot_merges, bot_only_flag=(r == 0 and bot_merges > 0),
                archived=d["meta"]["isArchived"], renamed=bool(d.get("renamed")), pushed_at=d["meta"]["pushedAt"][:10], release_method=method)

if __name__ == "__main__":
    rows = []
    for f in sorted((ROOT / "cache").glob("*__*.json")):
        if f.name.startswith(("_", "inv_")): continue
        d = json.loads(f.read_text())
        if d.get("status") == "ok": rows.append(repo_status(d))
    rs = pd.DataFrame(rows)
    inv = pd.read_csv(ROOT / "data/all_repos.csv")
    inv = inv[inv.confidence.isin(["high", "medium", "low"])].drop_duplicates(["dpgid", "full_name"])[["dpgid", "dpg", "full_name", "confidence"]]
    rs.to_csv(ROOT / "data/repo_status.csv", index=False)
    m = inv.assign(k=inv.full_name.str.lower()).merge(rs.assign(k=rs.full_name.str.lower()).drop(columns="full_name"), on="k")
    order = {"active": 0, "slowing": 1, "dormant": 2}
    def dpg_row(g, tiers):
        g = g[g.confidence.isin(tiers)]
        if g.empty: return None
        st = min(g.status, key=order.get)
        return dict(status=st, n_repos=len(g), n_active=(g.status == "active").sum(), n_slowing=(g.status == "slowing").sum(), n_dormant=(g.status == "dormant").sum(),
                    last_event_date=max([x for x in g.last_event_date if x] or [None]), check_move=bool(g.renamed.any()) and st == "dormant", bot_only=bool(st == "dormant" and g.bot_only_flag.any()))
    out = []
    for dpgid, g in m.groupby("dpgid"):
        for name, tiers in (("high", ["high"]), ("high+medium", ["high", "medium"])):
            r = dpg_row(g, tiers)
            if r: out.append({"dpgid": dpgid, "dpg": g.dpg.iloc[0], "repo_set": name, **r})
    ds = pd.DataFrame(out); ds.to_csv(ROOT / "data/dpg_status.csv", index=False)
    print("changed by counting pre-releases:", int((rs.status != rs.status_incl_prerelease).sum()), "of", len(rs))
    print("repos:", rs.status.value_counts().to_dict(), "| bot-only dormant:", int(rs.bot_only_flag.sum()))
    print(ds.groupby(["repo_set", "status"]).size().unstack(fill_value=0).to_string())
