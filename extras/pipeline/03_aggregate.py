"""Aggregate cached raw repo JSON to quarterly metrics per repo and per DPG.
Spec: METHODOLOGY D4, D5, D6, D9, D14, D19 (no circular measures), D21 (fixed cohort, DPG-level people de-duplicated), TASKS G3/G12, msgs M0002/M0008.
Outputs: data/repo_quarterly.csv, data/dpg_quarterly.csv.
  * TEAM (D19) = human commit authors on the default branch + human PR mergers + human reviewers. PR authorship is NOT team activity.
    active_contributors = any such event in the quarter; core_team = events in >=2 distinct months of the quarter; maintainers = mergers + reviewers.
  * OUTPUT = releases (major/minor/patch, tags as fallback), issues closed, merged human PRs.
  * DPG level: people are the UNION across the DPG's repos (not summed). Output is summed over the DPG's repos created before 2024-01-01 (in_cohort, D21).
  * Current quarter is flagged partial_quarter and must be dropped from estimation (D20).
Identities are raw logins/emails here; anonymise before sharing. Alias merging beyond noreply->login is G5 (not yet hand-validated).
Run: python -I scripts/03_aggregate.py
"""
import hashlib, json, re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"
START = pd.Timestamp("2020-01-01")
COHORT_BEFORE = pd.Timestamp("2024-01-01")
MIGRATION_MIN_COMMITS = 50  # D45: a repo created later still counts as cohort if it has >=50 commits dated before 2024 (migrated history)
TODAY = pd.Timestamp.today().normalize()
CURRENT_Q = str(TODAY.to_period("Q"))

# Automation accounts. Patterns catch "-bot", "[bot]", "-ci", "automation", release/builder bots; HAND_BOTS lists user accounts found by scanning the cache
# (checked, 2026-10-29). Names that merely contain "bot"/"robot" but belong to people (TimidRobot, vbothe23, ...) are deliberately NOT matched.
DEP_BOTS = re.compile(r"dependabot|renovate|github-actions|pre-commit-ci|snyk|greenkeeper|allcontributors|weblate|transifex|crowdin|codecov|imgbot|sonar"
                      r"|[-_.]bot(?:$|[-_.\[])|\[bot\]|^bot[-_]|[-_]ci$|automation|actions-user|semantic-release|release-bot|-builder$|auto-merge|mergify|fossabot|houndci", re.I)
HAND_BOTS = {"blsqbot", "framabot", "terraframe-builder", "chiaautomation", "aam-digital-ci", "openelis-bot", "dask-bot", "consulbot", "ersilia-bot",
             "cc-open-source-bot", "epiverse-trace-bot", "publiccode-pr-bot", "step-security-bot", "flintcibot", "cc-creativecommons-github-io-bot", "pix-service-auto-merge"}
AI_AGENTS = re.compile(r"^copilot|copilot-swe-agent|devin-ai|^claude|claude-bridge|codex|cursor(?:-?agent|\[bot\])|^cursor$|sweep-ai|openhands|jules"
                       r"|coderabbit|greptile|gemini-code-assist|qodo|sourcery-ai|korbit-ai|ellipsis-dev|codeant-ai|bito-code", re.I)  # AI reviewers added (D50 check, 2026-10-29)
NOREPLY = re.compile(r"^(?:\d+\+)?(.+)@users\.noreply\.github\.com$", re.I)

def actor_class(login, typename=None):
    """human | dep_bot | ai_agent | unknown (D6)."""
    if not isinstance(login, str) or not login: return "unknown"
    if AI_AGENTS.search(login): return "ai_agent"
    if typename == "Bot" or login.endswith("[bot]") or login.lower() in HAND_BOTS or DEP_BOTS.search(login): return "dep_bot"
    return "human"

def pkey(login=None, email=None, name=None):
    """Person key: login if known, else GitHub noreply login, else lowercase email, else name."""
    if isinstance(login, str) and login: return login.lower()
    if isinstance(email, str) and email:
        m = NOREPLY.match(email)
        return m.group(1).lower() if m else email.lower()
    return name.lower() if isinstance(name, str) and name else None

def ts(x):
    t = pd.Timestamp(x)
    return t.tz_convert(None) if t.tzinfo else t

def qs(t): return str(t.to_period("Q"))

def semver(tag):
    m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", tag or "")
    return tuple(int(x or 0) for x in m.groups()) if m else None

def release_kinds(rels, tags):
    """Classify as major/minor/patch against the highest version so far (backports are not bumps). Tags are the fallback."""
    if rels: src, method = [(r["tagName"], r["publishedAt"] or r["createdAt"], r["isPrerelease"]) for r in rels], "releases"
    else:
        src, method = [(t["name"], (t.get("target") or {}).get("committedDate") or ((t.get("target") or {}).get("tagger") or {}).get("date"), False) for t in (tags or [])], "tags"
    rows = sorted(((ts(t), semver(n)) for n, t, pre in src if t and not pre and semver(n)), key=lambda r: r[0])
    out, best = [], None
    for t, v in rows:
        if best is None: kind = "first"
        elif v[0] > best[0]: kind = "major"
        elif v[1] > best[1]: kind = "minor"
        elif v <= best: kind = "backport"
        else: kind = "patch"
        out.append((t, kind))
        if best is None or v > best: best = v
    return out, method

def process(d):
    """-> (repo rows keyed by quarter, team events [(quarter, month, person, role)], method)"""
    rows, team = {}, []
    pairs = set()  # (email, login) seen on the same commit: used for alias merging
    name_login, email_name = {}, {}  # name-based alias merging (conservative; see DPG roll-up)
    def add(q, k, v=1): rows.setdefault(q, {}); rows[q][k] = rows[q].get(k, 0) + v
    merge_hours = {}
    for p in d.get("prs") or []:
        au = p.get("author") or {}
        cls = actor_class(au.get("login"), au.get("__typename"))
        c = ts(p["createdAt"])
        if c >= START:
            add(qs(c), f"pr_opened_{cls}")
            if cls == "human": team.append((qs(c), c.month, pkey(au.get("login")), "pr_open"))  # role measure only (D44)
            title = p.get("title") or ""
            labels = [n["name"] for n in ((p.get("labels") or {}).get("nodes") or [])]
            if cls == "human" and (re.match(r"(?i)^\s*(feat|feature)\b", title) or any(re.search(r"(?i)feature|enhancement", n) for n in labels)):
                add(qs(c), "pr_feature_labelled_or_titled")
        if p.get("mergedAt"):
            m = ts(p["mergedAt"])
            if m >= START:
                add(qs(m), f"pr_merged_{cls}")
                if cls == "human":
                    merge_hours.setdefault(qs(m), []).append((m - c).total_seconds() / 3600)
                    add(qs(m), "lines_changed", (p.get("additions") or 0) + (p.get("deletions") or 0))
                if cls == "human": team.append((qs(m), m.month, pkey(au.get("login")), "pr_author"))  # author of a merged PR (D39 variant; see ACTIVITY note)
                mg = (p.get("mergedBy") or {}).get("login")
                if cls == "human":
                    revs = [rv for rv in ((p.get("reviews") or {}).get("nodes") or []) if (rv.get("author") or {}).get("login") and rv.get("submittedAt")
                            and rv["author"]["login"].lower() != (au.get("login") or "").lower() and actor_class(rv["author"]["login"]) == "human" and ts(rv["submittedAt"]) <= m]
                    if revs: add(qs(m), "pr_reviewed_before_merge")
                    elif mg and mg.lower() == (au.get("login") or "").lower(): add(qs(m), "pr_self_merged_unreviewed")
                if actor_class(mg) == "human" and m >= START: team.append((qs(m), m.month, pkey(mg), "merge"))
        elif p.get("closedAt") and ts(p["closedAt"]) >= START:
            add(qs(ts(p["closedAt"])), f"pr_closed_unmerged_{cls}")
        for rv in ((p.get("reviews") or {}).get("nodes") or []):
            rl = (rv.get("author") or {}).get("login")
            if rl and rv.get("submittedAt") and actor_class(rl) == "human" and ts(rv["submittedAt"]) >= START:
                t = ts(rv["submittedAt"]); team.append((qs(t), t.month, pkey(rl), "review"))
    for i in d.get("issues") or []:
        if ts(i["createdAt"]) >= START: add(qs(ts(i["createdAt"])), "issues_opened")
        if i.get("closedAt") and ts(i["closedAt"]) >= START: add(qs(ts(i["closedAt"])), "issues_closed")
    kinds, method = release_kinds(d.get("releases"), d.get("tags"))
    for t, k in kinds:
        if t >= START: add(qs(t), f"release_{k}"); add(qs(t), "release_total")
    ccount = {}
    for cm in d.get("commits") or []:
        au = cm.get("author") or {}
        login = (au.get("user") or {}).get("login")
        cls = actor_class(login) if login else ("dep_bot" if DEP_BOTS.search(au.get("name") or "") or "[bot]" in (au.get("name") or "") else "human")
        t = ts(cm["committedDate"]); q = qs(t)
        add(q, f"commits_{cls}")
        if cm.get("ai_trailer"): add(q, "commits_ai_trailer")
        if login and au.get("email") and not NOREPLY.match(au["email"]): pairs.add((au["email"].lower(), login.lower()))
        nm = (au.get("name") or "").strip().lower()
        if nm and cls == "human":
            if login: name_login.setdefault(nm, set()).add(login.lower())
            else:
                k_ = pkey(None, au.get("email"), au.get("name"))
                if k_ and "@" in k_: email_name[k_] = nm
        if cls == "human":
            k = pkey(login, au.get("email"), au.get("name"))
            if k: team.append((q, t.month, k, "commit")); ccount.setdefault(q, {}); ccount[q][k] = ccount[q].get(k, 0) + 1
    for q, h in merge_hours.items(): rows[q]["pr_median_merge_hours"] = float(pd.Series(h).median())
    for q, cc in ccount.items():
        v = sorted(cc.values(), reverse=True)
        rows.setdefault(q, {})["top1_commit_share"] = v[0] / sum(v); rows[q]["top2_commit_share"] = sum(v[:2]) / sum(v)
    return rows, team, method, pairs, {"name_login": name_login, "email_name": email_name}

ACTIVITY = ("commit", "merge", "review", "pr_author")  # D39: commit, merged PR, or PR review. Variant without pr_author is stored as *_nopr (sensitivity)

def team_metrics(events, roles=ACTIVITY):
    """events: (quarter, month, person, role) -> {quarter: dict(active_contributors, core_team, dev_months, maintainers)} (D39)."""
    df = pd.DataFrame(events, columns=["q", "m", "p", "role"]).dropna()
    df = df[df.role.isin(roles)]
    out = {}
    if df.empty: return out
    for q, g in df.groupby("q"):
        months = g.groupby("p").m.nunique()
        out[q] = dict(active_contributors=len(months), core_team=int((months >= 2).sum()), dev_months=int(months.sum()),
                      maintainers=g[g.role.isin(["merge", "review"])].p.nunique())
    return out

def role_counts(events):
    """D44: distinct people per role per quarter (bots/AI agents already excluded; people de-duplicated across the DPG's repos)."""
    df = pd.DataFrame(events, columns=["q", "m", "p", "role"]).dropna()
    out = {}
    for q, g in df.groupby("q"):
        out[q] = dict(authors=g[g.role.isin(["commit", "pr_open"])].p.nunique(), reviewers=g[g.role == "review"].p.nunique(), mergers=g[g.role == "merge"].p.nunique())
    return out

def departures(events, quarters, last_complete, roles=ACTIVITY):
    """D39 departures. established(q) = active in >=4 of the previous 8 quarters. A departure in q = established person active in q whose last
    active (complete) quarter is q. Defined only for q <= last_complete-2 (needs 2 silent complete quarters); history needs 8 prior quarters in data."""
    df = pd.DataFrame(events, columns=["q", "m", "p", "role"]).dropna(); df = df[df.role.isin(roles)]
    act = {}  # person -> sorted quarter ordinals active (complete quarters only)
    lc = pd.Period(last_complete).ordinal
    for p, g in df.groupby("p"): act[p] = sorted({pd.Period(q).ordinal for q in g.q if pd.Period(q).ordinal <= lc})
    res = {}
    for q in quarters:
        o = pd.Period(q).ordinal
        est = [p for p, a in act.items() if sum(1 for x in a if o - 8 <= x < o) >= 4]
        censored = o > lc - 2
        dep = None if censored else sum(1 for p in est if act[p] and act[p][-1] == o)
        res[q] = dict(established_start=len(est), departures=dep, departure_rate=(dep / len(est)) if dep is not None and est else None,
                      departures_censored=censored, history_complete=o - 8 >= pd.Period("2020Q1").ordinal)
    return res

if __name__ == "__main__":
    inv = pd.read_csv(ROOT / "data/all_repos.csv")
    inv = inv[inv.confidence.isin(["high", "medium", "low"])].drop_duplicates(["dpgid", "full_name"])
    dconf = pd.read_csv(ROOT / "data/dpg_confidence.csv")[["dpgid", "dpg_confidence"]]
    ndpg = inv.groupby(inv.full_name.str.lower()).dpgid.nunique()
    per_repo, skipped, nerr, all_pairs = {}, [], 0, set()
    for f in sorted(CACHE.glob("*__*.json")):
        if f.name.startswith(("_", "inv_")): continue
        try: d = json.loads(f.read_text())
        except Exception: nerr += 1; continue
        if d.get("status") != "ok": skipped.append(d.get("full_name")); continue
        rows, team, method, pairs, ainfo = process(d)
        all_pairs |= pairs
        m = d["meta"]
        cdates = [agg_ts for agg_ts in (ts(c["committedDate"]) for c in d.get("commits") or [])]
        pre = [t for t in cdates if t < COHORT_BEFORE]
        created = ts(m["createdAt"])
        in_cohort = created < COHORT_BEFORE or len(pre) >= MIGRATION_MIN_COMMITS
        eff_start = min([created] + pre) if len(pre) >= MIGRATION_MIN_COMMITS else created
        per_repo[d["full_name"].lower()] = dict(in_cohort=in_cohort, eff_start=eff_start, migrated=bool(in_cohort and created >= COHORT_BEFORE), rows=rows, team=team, ainfo=ainfo, method=method, created=ts(m["createdAt"]), renamed=bool(d.get("renamed")),
                                                archived=m["isArchived"], fork=m["isFork"], name=d["full_name"])
        # the registry may use the old name; index by the canonical name too
        per_repo[m["nameWithOwner"].lower()] = per_repo[d["full_name"].lower()]
    # alias merging: an email seen with exactly one login on any commit maps email-only authors to that login (G5/D39; hand-validation = QC Q5)
    e2l = {}
    for em, lg in all_pairs: e2l.setdefault(em, set()).add(lg)
    e2l = {em: next(iter(l)) for em, l in e2l.items() if len(l) == 1}
    n_alias = 0; n_email_alias = 0
    for v in {id(v): v for v in per_repo.values()}.values():
        new = []
        for q, m_, p_, role in v["team"]:
            if p_ and "@" in p_ and p_ in e2l: p_ = e2l[p_]; n_alias += 1
            new.append((q, m_, p_, role))
        v["team"] = new
    out = []
    for key, r in {v["name"].lower(): v for v in per_repo.values()}.items():
        tm = team_metrics(r["team"])
        for q in set(r["rows"]) | set(tm):
            row = {**r["rows"].get(q, {}), **tm.get(q, {})}
            out.append({"full_name": r["name"], "quarter": q, **row, "release_method": r["method"], "repo_created": r["created"].date(),
                        "in_cohort": r["in_cohort"], "cohort_via_migration_rule": r["migrated"], "partial_quarter": q == CURRENT_Q, "renamed": r["renamed"],
                        "repo_archived": r["archived"], "repo_is_fork": r["fork"], "n_dpgs_for_repo": int(ndpg.get(r["name"].lower(), 1))})
    rq = pd.DataFrame(out)
    num = [c for c in rq.columns if c not in ("full_name", "quarter", "release_method", "repo_created", "in_cohort", "cohort_via_migration_rule", "partial_quarter", "renamed", "repo_archived", "repo_is_fork", "n_dpgs_for_repo", "top1_commit_share", "top2_commit_share", "pr_median_merge_hours")]
    rq[num] = rq[num].fillna(0)
    # one row per (dpgid, full_name) mapping; repo_quarterly is repo-level: do NOT sum it across dpgid (shared repos, see data notes)
    rq.merge(inv[["dpgid", "dpg", "full_name", "confidence"]].assign(k=lambda x: x.full_name.str.lower()).drop_duplicates("k")[["full_name", "dpgid", "dpg", "confidence"]], how="left", on="full_name").to_csv(ROOT / "data/repo_quarterly.csv", index=False)

    # DPG roll-up: people = union across the DPG's repos; output = sum over the DPG's in-cohort repos; balanced quarterly panel with zeros.
    allq = [str(p) for p in pd.period_range("2020Q1", CURRENT_Q, freq="Q")]
    LAST_COMPLETE = str(pd.Period(CURRENT_Q) - 1)
    count_cols = [c for c in num if c not in ("active_contributors", "core_team", "maintainers", "dev_months")]
    dpg_rows, people_rows, alias_rows, nocoh_rows = [], [], [], []
    for dpgid, g in inv.groupby("dpgid"):
        repos = {k: per_repo[k] for k in {x.lower() for x in g.full_name} if k in per_repo}
        if not repos: continue
        uniq = {v["name"].lower(): v for v in repos.values()}
        coh = [v for v in uniq.values() if v["in_cohort"]]
        nl, en = {}, {}
        for v in uniq.values():
            for nm_, lgs in v["ainfo"]["name_login"].items(): nl.setdefault(nm_, set()).update(lgs)
            en.update(v["ainfo"]["email_name"])
        # merge an unlinked email into a login only if the author name has >=2 words and maps to exactly one login within this DPG
        alias = {em: next(iter(nl[nm_])) for em, nm_ in en.items() if len(nm_.split()) >= 2 and len(nl.get(nm_, ())) == 1}
        for em, lg in alias.items(): alias_rows.append({"dpgid": dpgid, "email_key": em, "author_name": en[em], "merged_into_login": lg})
        fix = lambda evs: [(q_, m_, alias.get(p_, p_), r_) for q_, m_, p_, r_ in evs]
        n_alias += sum(1 for v in coh for e in v["team"] if e[2] in alias)
        ev = fix([e for v in coh for e in v["team"]])  # union of people across the DPG's cohort repos (D21)
        ev_all = fix([e for v in uniq.values() for e in v["team"]])  # sensitivity: all repos
        tm = team_metrics(ev); tm_nopr = team_metrics(ev, roles=("commit", "merge", "review")); tm_all = team_metrics(ev_all)
        dep = departures(ev, allq, LAST_COMPLETE); rc = role_counts(ev)
        sums = {q: {} for q in allq}
        for v in coh:
            for q, r in v["rows"].items():
                for c, x in r.items():
                    if c in count_cols and c in rq.columns: sums[q][c] = sums[q].get(c, 0) + (x if x == x else 0)
        first = min([v["eff_start"] for v in coh], default=None)
        if not coh:  # no repo created before 2024: not measurable in the fixed cohort (D21); listed, never written as zeros (AMRIT, M0133)
            nocoh_rows.append({"dpgid": dpgid, "dpg": g.dpg.iloc[0], "repos": "|".join(sorted(v["name"] for v in uniq.values())),
                               "earliest_repo_created": min(v["created"] for v in uniq.values()).date(), "reason": "all repos created on/after 2024-01-01 and <50 commits before 2024 (D21/D45)"})
            continue
        # people file: hashed ids only (raw logins/emails stay in the cache)
        pdf = pd.DataFrame(ev, columns=["q", "m", "p", "role"]).dropna()
        pdf = pdf[pdf.role.isin(ACTIVITY)]
        for (q, p_), gg in pdf.groupby(["q", "p"]):
            pid = hashlib.sha1(f"dpg-people-v1|{p_}".encode()).hexdigest()[:10]
            people_rows.append({"dpgid": dpgid, "quarter": q, "person_id": pid, "months_active": gg.m.nunique(), "roles": "|".join(sorted(gg.role.unique())), "core": gg.m.nunique() >= 2})
        for q in allq:
            if first is not None and pd.Period(q).end_time < first: continue  # before any cohort repo existed
            row = {c: 0 for c in count_cols}; row.update(sums[q])
            t, tn, ta, dd = tm.get(q, {}), tm_nopr.get(q, {}), tm_all.get(q, {}), dep[q]
            row.update(active_contributors_dpg=t.get("active_contributors", 0), core_team_dpg=t.get("core_team", 0), dev_months_dpg=t.get("dev_months", 0),
                       maintainers_dpg=t.get("maintainers", 0), core_team_dpg_nopr=tn.get("core_team", 0), dev_months_dpg_nopr=tn.get("dev_months", 0),
                       authors_dpg=rc.get(q, {}).get("authors", 0), reviewers_dpg=rc.get(q, {}).get("reviewers", 0), mergers_dpg=rc.get(q, {}).get("mergers", 0),
                       review_coverage=(row.get("pr_reviewed_before_merge", 0) / row["pr_merged_human"]) if row.get("pr_merged_human") else None,
                       self_merge_unreviewed=(row.get("pr_self_merged_unreviewed", 0) / row["pr_merged_human"]) if row.get("pr_merged_human") else None,
                       core_team_dpg_allrepos=ta.get("core_team", 0), established_start_dpg=dd["established_start"], departures_dpg=dd["departures"],
                       departure_rate_dpg=dd["departure_rate"], departures_censored=dd["departures_censored"], history_complete=dd["history_complete"])
            dpg_rows.append({"dpgid": dpgid, "dpg": g.dpg.iloc[0], "quarter": q, **row, "n_repos_cohort": len(coh), "n_cohort_via_migration_rule": sum(v["migrated"] for v in coh), "n_repos_all": len(uniq),
                             "partial_quarter": q == CURRENT_Q, "any_renamed_repo": any(v["renamed"] for v in uniq.values())})
    NOTES = {"PSMRI/AMRIT": "registry lists only an umbrella repo created 2024-10; the project code spans ~81 repos in the PSMRI org (earliest created 2023-05) that D30/D45 do not pick up; no manual pick (PM M0166)"}
    nc = pd.DataFrame(nocoh_rows)
    if len(nc): nc["note"] = [next((v for k, v in NOTES.items() if k.lower() in r.lower()), "") for r in nc.repos]
    nc.to_csv(ROOT / "data/dpg_no_cohort_repo.csv", index=False)
    pd.DataFrame(people_rows).to_csv(ROOT / "data/people_quarterly.csv", index=False)
    pd.DataFrame(alias_rows).to_csv(CACHE / "_alias_merges.csv", index=False)  # raw identities: internal, for the hand-validation sample; never share
    dq = pd.DataFrame(dpg_rows).merge(dconf, how="left", on="dpgid")
    dq.to_csv(ROOT / "data/dpg_quarterly.csv", index=False)
    print(f"name-merged events (cohort): {n_alias}; " f"repos aggregated: {len({v['name'] for v in per_repo.values()})}; repo-quarters: {len(rq)}; DPGs: {dq.dpgid.nunique()}; dpg-quarters: {len(dq)}; skipped not-ok: {skipped}; unreadable: {nerr}")
