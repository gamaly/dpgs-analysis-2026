"""AI-disclosure shares in merged PRs by year and half-year (METHODOLOGY D15, P5; negation filter = logged deviation).
Reuses the frozen term lists, regex helpers and author_class from 03c_pr_text_ai.py by executing the part of that
file before its data-processing section (03c has no importable module form; its term lists are not changed here).
Adds a line filter: lines stating AI was NOT used are dropped before matching.
Only groups in PASSED_GROUPS (D15 precision gate >= 80%) are reported.
Outputs: docs/post/findings_tables/t8_ai_disclosure_by_year.csv, t8_ai_disclosure_by_half.csv,
         data/pr_text_ai_claude_matches.csv (every counted match with context, for precision sampling),
         data/pr_text_ai_negation_removed.csv (matches the filter removed).
Run: python -I scripts/03h_ai_disclosure.py
"""
import json, re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
_src = (ROOT / "scripts" / "03c_pr_text_ai.py").read_text(encoding="utf-8").split("conf = pd.read_csv")[0]
_src = _src.replace("ROOT = Path(__file__).resolve().parent.parent", f"ROOT = Path(r'{ROOT}')")
exec(_src)  # defines CACHE, DATA, WINDOW_START, AUTHOR_TERMS, AUTH_RX, hits, author_class

PASSED_GROUPS = ["claude"]  # precision gate result; update only with a new gate round
OUT = ROOT / "docs" / "post" / "findings_tables"
NEG = re.compile(r"no ai tool|certify that no|were not used|was not used|not (?:generated|written|assisted) (?:by|with|using)|"
                 r"without (?:the use of )?(?:any )?ai|did not use|no ai[- ]generated", re.I)

def strip_negated(text):
    return "\n".join(l for l in text.split("\n") if not NEG.search(l))

conf = pd.read_csv(DATA / "all_repos.csv").drop_duplicates("full_name")
cl = {r.full_name.lower(): (r.confidence, r.dpgid) for r in conf.itertuples()}
rows, matches, removed = [], [], []
for f in sorted(CACHE.glob("*__*.json")):
    if f.name.startswith(("_", "inv_")): continue
    d = json.loads(f.read_text(encoding="utf-8"))
    if d.get("status") != "ok": continue
    full = d["full_name"]; tier, dpg = cl.get(full.lower(), ("unknown", None))
    if tier != "high": continue
    for p in d.get("prs") or []:
        if not p.get("mergedAt") or p["createdAt"] < WINDOW_START: continue
        cls = author_class(p.get("author"))
        if cls == "bot": continue
        raw = (p.get("title") or "") + "\n" + (p.get("bodyText") or "")
        h_raw = {k: (m, c) for k, m, c in hits(AUTH_RX, raw) if k in PASSED_GROUPS}
        h = {k: (m, c) for k, m, c in hits(AUTH_RX, strip_negated(raw)) if k in PASSED_GROUPS}
        for k in h_raw:
            if k not in h:
                removed.append(dict(full_name=full, created=p["createdAt"][:10], cls=cls, group=k, title=(p.get("title") or "")[:120], context=h_raw[k][1]))
        for k, (m, c) in h.items():
            if cls == "human":
                matches.append(dict(full_name=full, created=p["createdAt"][:10], group=k, title=(p.get("title") or "")[:150], match=m, context=c))
        rows.append(dict(full_name=full, dpgid=dpg, created=p["createdAt"], cls=cls, signal=bool(h)))
d = pd.DataFrame(rows)
pd.DataFrame(matches).to_csv(DATA / "pr_text_ai_claude_matches.csv", index=False, encoding="utf-8")
pd.DataFrame(removed).to_csv(DATA / "pr_text_ai_negation_removed.csv", index=False, encoding="utf-8")
d["year"] = d.created.str[:4]
d["half"] = d.year + "H" + ((d.created.str[5:7].astype(int) > 6).astype(int) + 1).astype(str)

# per-DPG year shares (human merged PRs), so the spread across DPGs can be shown plainly
hy = d[d.cls == "human"].groupby(["dpgid", "year"]).agg(merged_human_prs=("signal", "size"), with_signal=("signal", "sum")).reset_index()
hy["share"] = (hy.with_signal / hy.merged_human_prs).round(4)
hy.to_csv(ROOT / "docs/post/findings_tables/t8_ai_disclosure_per_dpg_year.csv", index=False)


def table(key):
    out = []
    for k, g in d.groupby(key):
        h = g[g.cls == "human"]; a = g[g.cls == "ai_agent"]
        per = h.groupby("dpgid").agg(n=("signal", "size"), s=("signal", "mean"))
        per = per[per.n >= 20]
        top = h[h.signal].full_name.value_counts()
        out.append({key: k, "repos": g.full_name.nunique(), "dpgs_active": g.dpgid.nunique(),
                    "merged_human_prs": len(h), "human_with_signal": int(h.signal.sum()),
                    "share_human_signal": round(h.signal.mean(), 5) if len(h) else None,
                    "median_dpg_share_dpgs_ge20_prs": round(per.s.median(), 5) if len(per) else None,
                    "n_dpgs_ge20_prs": len(per),
                    "merged_ai_agent_prs": len(a), "share_ai_agent_of_human_plus_agent": round(len(a) / len(g), 6),
                    "dpgs_with_disclosed_ai_pr": h[h.signal].dpgid.nunique(),
                    "dpgs_with_ai_agent_pr": a.dpgid.nunique(),
                    "top6_repo_share_of_signal": round(top.head(6).sum() / top.sum(), 3) if len(top) else None,
                    "partial_period": k in ("2026", "2026H2")})
    return pd.DataFrame(out)
OUT.mkdir(parents=True, exist_ok=True)
y = table("year"); y.to_csv(OUT / "t8_ai_disclosure_by_year.csv", index=False)
hf = table("half"); hf = hf[hf.half >= "2024H1"]; hf.to_csv(OUT / "t8_ai_disclosure_by_half.csv", index=False)
pd.set_option("display.width", 250); print(y.to_string()); print(hf.to_string())
r = pd.DataFrame(removed)
print("removed by negation filter:", len(r), "| QGIS:", int((r.full_name == "qgis/QGIS").sum()) if len(r) else 0, "| human only:", int((r.cls == "human").sum()) if len(r) else 0)
