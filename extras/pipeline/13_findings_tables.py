"""Descriptive tables for the findings memo. Reads existing outputs only.
Run: python -I scripts/13_findings_tables.py
Sample: DPGs with dpg_confidence == "high"; fixed cohort (rates use a fixed set of repositories created before 2024; the fixed set of repositories is those created before 2024 or holding at least 50 earlier commits) as built in dpg_quarterly.csv;
the partial current quarter (partial_quarter flag) is dropped. Descriptive only, no tests."""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "post" / "findings_tables"
OUT.mkdir(parents=True, exist_ok=True)

dq = pd.read_csv(ROOT / "data" / "dpg_quarterly.csv")
rq = pd.read_csv(ROOT / "data" / "repo_quarterly.csv")
conf = pd.read_csv(ROOT / "data" / "dpg_confidence.csv")

high = set(conf.loc[conf.dpg_confidence == "high", "dpgid"])
partial_q = set(dq.loc[dq.partial_quarter.astype(str) == "True", "quarter"]) | \
            set(rq.loc[rq.partial_quarter.astype(str) == "True", "quarter"])
d = dq[dq.dpgid.isin(high) & ~dq.quarter.isin(partial_q)].copy()
d["year"] = d.quarter.str[:4].astype(int)
last_q = d.quarter.max()
print(f"High-confidence DPGs in confidence file: {len(high)}; with panel rows: {d.dpgid.nunique()}")
print(f"Dropped partial quarters: {sorted(partial_q)}; last complete quarter: {last_q}")

# output definitions
d["output_a"] = d.release_minor + d.release_major + d.issues_closed
d["output_b"] = d.pr_merged_human
d["output_c"] = d.release_total + d.issues_closed
d["unclassified"] = d.release_total - d.release_major - d.release_minor - d.release_patch

# project age: oldest cohort repo creation year per DPG
rc = rq[rq.in_cohort.astype(str) == "True"].copy()
rc["created"] = pd.to_datetime(rc.repo_created, errors="coerce")
oldest = rc.groupby("dpgid").created.min()
d["oldest_repo_created"] = d.dpgid.map(oldest)
d["age_group"] = pd.NA
d.loc[d.oldest_repo_created < "2018-01-01", "age_group"] = "created_before_2018"
d.loc[(d.oldest_repo_created >= "2018-01-01") & (d.oldest_repo_created < "2024-01-01"), "age_group"] = "created_2018_2023"
print("DPGs without usable repo_created:", d.loc[d.age_group.isna(), "dpgid"].nunique())

def save(df, name):
    df.to_csv(OUT / f"{name}.csv", index=False)
    print(f"\n== {name} ({len(df)} rows)")
    print(df.to_string(index=False, max_rows=12 if len(df) > 14 else None, float_format=lambda x: f"{x:.3f}"))

def core_table(g, key):
    def agg(x):
        n = len(x)
        c = x.core_team_dpg
        return pd.Series({
            "n_dpgs": x.dpgid.nunique(), "n_dpg_quarters": n, "n_quarters": x.quarter.nunique(),
            "core_total": c.sum(), "core_median_per_dpg": c.median(),
            "share_dpgs_core_0": (c == 0).mean(),
            "share_dpgs_core_1_2": c.between(1, 2).mean(),
            "share_dpgs_core_3plus": (c >= 3).mean(),
            "active_total": x.active_contributors_dpg.sum(),
            "reviewers_total": x.reviewers_dpg.sum()})
    return d_groupby(g, key, agg)

def d_groupby(g, key, agg):
    keys = key if isinstance(key, list) else [key]
    rows = []
    for k, x in g.groupby(keys):
        k = k if isinstance(k, tuple) else (k,)
        rows.append({**dict(zip(keys, k)), **agg(x).to_dict()})
    return pd.DataFrame(rows)

def ratio_table(g, key):
    def agg(x):
        core = x.core_team_dpg.sum()
        return pd.Series({
            "n_dpgs": x.dpgid.nunique(), "n_dpg_quarters": len(x), "n_quarters": x.quarter.nunique(),
            "core_total": core, "output_a_total": x.output_a.sum(),
            "output_b_total": x.output_b.sum(), "output_c_total": x.output_c.sum(),
            "release_total": x.release_total.sum(), "unclassified_releases": x.unclassified.sum(),
            "unclassified_share": x.unclassified.sum() / x.release_total.sum() if x.release_total.sum() else float("nan"),
            "output_a_per_core": x.output_a.sum() / core if core else float("nan"),
            "output_c_per_core": x.output_c.sum() / core if core else float("nan"),
            "output_b_per_core": x.output_b.sum() / core if core else float("nan")})
    return d_groupby(g, key, agg)

# balanced set: DPGs with panel rows in every complete quarter from START_Q to last complete quarter
def balanced_ids(start):
    need = sorted(q for q in d.quarter.unique() if q >= start)
    cnt = d[d.quarter.isin(need)].groupby("dpgid").quarter.nunique()
    return set(cnt[cnt == len(need)].index), need[0]
bal_ids, start_q = balanced_ids("2021Q1")
n2021 = len(bal_ids)
if n2021 < 60:
    bal_ids, start_q = balanced_ids("2022Q1")
    print(f"Balanced from 2021Q1: {n2021} DPGs (< 60); using 2022Q1 instead")
print(f"BALANCED SET: {len(bal_ids)} DPGs with rows in every complete quarter {start_q}..{last_q} (from 2021Q1: {n2021})")
db = d[d.dpgid.isin(bal_ids) & (d.quarter >= start_q)]

def tables(df, sfx, label):
    print(f"#### {label}")
    save(core_table(df, "quarter"), f"t1_core_by_quarter{sfx}")
    save(core_table(df, "year"), f"t1_core_by_year{sfx}")
    for per in ("quarter", "year"):
        t = ratio_table(df, per)
        if not sfx:
            bt = ratio_table(db, per)[[per, "n_dpgs", "output_a_per_core", "output_c_per_core", "output_b_per_core"]]
            bt.columns = [per] + ["same_dpgs_" + c for c in bt.columns[1:]]
            t = t.merge(bt, on=per, how="left")
        save(t, f"t2_output_per_core_by_{per}{sfx}")
    da = df[df.age_group.notna()]
    save(core_table(da, ["age_group", "quarter"]), f"t3_core_by_age_quarter{sfx}")
    save(core_table(da, ["age_group", "year"]), f"t3_core_by_age_year{sfx}")
    save(ratio_table(da, ["age_group", "quarter"]), f"t3_output_per_core_by_age_quarter{sfx}")
    save(ratio_table(da, ["age_group", "year"]), f"t3_output_per_core_by_age_year{sfx}")

tables(d, "", "UNBALANCED (all high-confidence DPGs with rows that quarter)")
tables(db, "_balanced", f"BALANCED ({len(bal_ids)} DPGs, {start_q}..{last_q})")

# 4 releases: per DPG-year first, then summarise
py = d.groupby(["dpgid", "year"])[["release_total", "release_major", "release_minor", "release_patch"]].sum().reset_index()
rel = []
for y, x in py.groupby("year"):
    rel.append({"year": y, "n_dpgs": len(x), "n_dpgs_released": int((x.release_total > 0).sum()),
                "release_total": x.release_total.sum(),
                "median_releases_per_releasing_dpg": x.loc[x.release_total > 0, "release_total"].median(),
                "release_major": x.release_major.sum(), "release_minor": x.release_minor.sum(),
                "release_patch": x.release_patch.sum()})
rel = pd.DataFrame(rel)
rel["unclassified_releases"] = rel.release_total - rel.release_major - rel.release_minor - rel.release_patch
rel["unclassified_share"] = rel.unclassified_releases / rel.release_total
save(rel, "t4_releases_by_year")

# t4b: by release_method (repo-level: GitHub Releases vs tag fallback), cohort repos of high-confidence DPGs
rr = rq[(rq.in_cohort.astype(str) == "True") & rq.dpgid.isin(high) & ~rq.quarter.isin(partial_q)].copy()
rr["year"] = rr.quarter.str[:4].astype(int)
rr["unclassified"] = rr.release_total - rr.release_major - rr.release_minor - rr.release_patch
t4b = rr.groupby(["year", "release_method"])[["release_total", "release_major", "release_minor", "release_patch", "unclassified"]].sum().reset_index()
t4b["unclassified_share"] = t4b.unclassified / t4b.release_total
save(t4b, "t4_releases_by_year_and_method")

# 6 first-time contributors (people_quarterly.csv; person_id is hashed, de-duplicated per DPG, bots excluded)
pq = pd.read_csv(ROOT / "data" / "people_quarterly.csv")
pq = pq[pq.dpgid.isin(high) & ~pq.quarter.isin(partial_q)].copy()
pq["year"] = pq.quarter.str[:4].astype(int)
pq["qi"] = pq.quarter.str[:4].astype(int) * 4 + pq.quarter.str[5].astype(int) - 1
last_qi = int(last_q[:4]) * 4 + int(last_q[5]) - 1
pq["core"] = pq.core.astype(str) == "True"
def first_role(r):
    rs = set(str(r).split("|"))
    if rs & {"commit", "pr_author"}: return "code_author"
    if "merge" in rs: return "merger"
    return "reviewer_only"
pq["role_class"] = pq.roles.map(first_role)
pq = pq.sort_values(["dpgid", "person_id", "qi"])
key = ["dpgid", "person_id"]
first = pq.groupby(key).head(1).copy()            # first quarter in this DPG (data starts 2020Q1)
later = pq.merge(first[key + ["qi"]].rename(columns={"qi": "fqi"}), on=key)
later = later[later.qi > later.fqi]
back4 = later[later.qi <= later.fqi + 4].groupby(key).size().rename("n_back4")
core_later = later[later.core].groupby(key).size().rename("n_core_later")
first = first.join(back4, on=key).join(core_later, on=key)
first["evaluable"] = first.qi <= last_qi - 4      # a full 4-quarter follow-up window exists
first["returned"] = first.n_back4.fillna(0) > 0
first["became_core"] = first.n_core_later.fillna(0) > 0

def first_table(per, ids=None, start=None):
    f = first if ids is None else first[first.dpgid.isin(ids)]
    allp = pq if ids is None else pq[pq.dpgid.isin(ids)]
    dd = d if ids is None else d[d.dpgid.isin(ids)]
    if start: f, allp, dd = f[f.quarter >= start], allp[allp.quarter >= start], dd[dd.quarter >= start]
    rows = []
    for k, x in f.groupby(per):
        n = len(x); ev = x[x.evaluable]
        npd = dd.loc[dd[per] == k, "dpgid"].nunique()
        act = allp[allp[per] == k].drop_duplicates(key).shape[0]
        rows.append({per: k, "burn_in_2020": str(k).startswith("2020"), "n_dpgs_in_panel": npd,
            "first_timers": n, "first_timers_per_dpg": n / npd if npd else float("nan"),
            "active_people": act, "share_of_active_who_are_first_timers": n / act if act else float("nan"),
            "first_role_code_author": (x.role_class == "code_author").sum(),
            "first_role_reviewer_only": (x.role_class == "reviewer_only").sum(),
            "first_role_merger": (x.role_class == "merger").sum(),
            "n_evaluable_for_followup": len(ev),
            "followup_status": "complete" if len(ev) == n else ("censored" if len(ev) == 0 else "partly_censored"),
            "share_returned_within_4q": ev.returned.mean() if len(ev) else float("nan"),
            "share_ever_core_later": ev.became_core.mean() if len(ev) else float("nan")})
    return pd.DataFrame(rows)

for per in ("year", "quarter"):
    save(first_table(per), f"t6_first_time_contributors_by_{per}")
    save(first_table(per, bal_ids, start_q), f"t6_first_time_contributors_by_{per}_balanced")

# 5 roles and review
m = d[d.pr_merged_human > 0]
rows = []
for y, x in m.groupby("year"):
    rows.append({"year": y, "n_dpg_quarters": len(x), "n_dpgs": x.dpgid.nunique(),
                 "median_authors": x.authors_dpg.median(), "median_reviewers": x.reviewers_dpg.median(),
                 "median_mergers": x.mergers_dpg.median(),
                 "pooled_review_coverage": x.pr_reviewed_before_merge.sum() / x.pr_merged_human.sum(),
                 "pooled_self_merge_unreviewed": x.pr_self_merged_unreviewed.sum() / x.pr_merged_human.sum()})
save(pd.DataFrame(rows), "t5_roles_review_by_year")

# data checks
chk = d[["core_team_dpg", "active_contributors_dpg", "reviewers_dpg", "authors_dpg", "mergers_dpg",
         "release_total", "issues_closed", "pr_merged_human"]]
print("\nNaN counts:", chk.isna().sum()[chk.isna().sum() > 0].to_dict() or "none")
print("Negative values:", int((chk < 0).sum().sum()))
print("core > active rows:", int((d.core_team_dpg > d.active_contributors_dpg).sum()))
print("releases by type != total rows:", int((d.release_total < d.release_major + d.release_minor + d.release_patch).sum()))
