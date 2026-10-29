"""Q3 (AI features are measured from dependency manifests and from PR text): shipped status of AI-feature PRs + AI features in release notes. Reuses FEAT/DROP_LINE from 03f unchanged."""
import json, re, importlib.util
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parent.parent
sp = importlib.util.spec_from_file_location("f03", ROOT / "scripts/03f_ai_feature_prs.py"); f03 = importlib.util.module_from_spec(sp); sp.loader.exec_module(f03)
FEAT, DROP = f03.FEAT, f03.DROP_LINE

def load(full):
    f = ROOT / "cache" / (full.replace("/", "__") + ".json")
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}

# 1 shipped status
ai = pd.read_csv(ROOT / "data/ai_feature_prs.csv"); rel_cache = {}
def rels(full):
    if full not in rel_cache:
        d = load(full)
        r = sorted([(x["publishedAt"] or x["createdAt"], x["tagName"]) for x in (d.get("releases") or []) if not x.get("isPrerelease") and (x.get("publishedAt") or x.get("createdAt"))])
        t = sorted([((x.get("target") or {}).get("committedDate"), x["name"]) for x in (d.get("tags") or []) if (x.get("target") or {}).get("committedDate")])
        rel_cache[full] = (r, t)
    return rel_cache[full]
out = []
for p in ai.itertuples():
    r, t = rels(p.full_name)
    src, lst = ("releases", r) if r else (("tags", t) if t else ("none", []))
    nxt = [x for x in lst if x[0] > p.merged_at]
    out.append((nxt[0][1], nxt[0][0], src) if nxt else ("", "", src))
ai["shipped"] = [bool(o[1]) for o in out]; ai["first_release_tag"] = [o[0] for o in out]; ai["first_release_date"] = [o[1] for o in out]
ai["days_to_release"] = [round((pd.Timestamp(o[1]) - pd.Timestamp(m)).total_seconds() / 86400, 1) if o[1] else None for o, m in zip(out, ai.merged_at)]
ai["release_source"] = [o[2] for o in out]
ai.to_csv(ROOT / "data/ai_feature_prs_shipped.csv", index=False)

# 3 release notes
a = pd.read_csv(ROOT / "data/all_repos.csv", low_memory=False).drop_duplicates("full_name").set_index("full_name")
rows, allrel = [], []
for f in (ROOT / "cache/release_notes").glob("*.json"):
    d = json.loads(f.read_text(encoding="utf-8"))
    if d.get("status") != "ok": continue
    fn = d["full_name"]; dpgid, dpg = a.loc[fn, "dpgid"], a.loc[fn, "dpg"]
    for x in d["releases"]:
        if x.get("isPrerelease") or not x.get("publishedAt") or x["publishedAt"] < "2020": continue
        txt = "\n".join(l for l in ((x.get("name") or "") + "\n" + (x.get("description") or "")).splitlines() if not DROP.search(l))
        m = FEAT.search(txt)
        allrel.append((dpgid, x["publishedAt"][:4], bool(m)))
        if m:
            rows.append({"dpgid": dpgid, "dpg": dpg, "full_name": fn, "tag": x["tagName"], "published_at": x["publishedAt"], "term": m.group(0).lower(),
                         "context": txt[max(0, m.start() - 100): m.end() + 100].replace("\n", " ")[:200]})
pd.DataFrame(rows).sort_values(["dpg", "published_at"]).to_csv(ROOT / "data/release_notes_ai.csv", index=False)
al = pd.DataFrame(allrel, columns=["dpgid", "year", "hit"])
y = al.groupby("year").agg(releases=("hit", "size"), releases_with_ai_feature=("hit", "sum")).reset_index()
y["dpgs_with_ai_release"] = [al[(al.year == yr) & al.hit].dpgid.nunique() for yr in y.year]
y.to_csv(ROOT / "data/release_notes_ai_yearly.csv", index=False)
s = ai
print(y.to_string()); print("PRs", len(s), "shipped", s.shipped.sum(), s.release_source.value_counts().to_dict())
print("DPGs shipped", s[s.shipped].dpgid.nunique(), "of", s.dpgid.nunique(), "median days", s.days_to_release.median())
print("DPGs release-notes AI", len({r['dpgid'] for r in rows}), "since2024", len({r['dpgid'] for r in rows if r['published_at']>='2024'}))
