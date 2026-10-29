"""Pre-registered H2 specification (the locked funding-test rules). Written before any outcome data were looked at.

  python -I scripts/09_event_study_spec.py --lock             freeze SPEC into data/prereg_lock.json
  python -I scripts/09_event_study_spec.py --selftest         check the estimator on simulated data (no project data read)
  python -I scripts/09_event_study_spec.py --power            statistical power is computed from pre-period data before outcomes are read: minimum detectable effect from PRE-period data only
  python -I scripts/09_event_study_spec.py --run              event study on real data (needs lock + funding_flags + dpg_quarterly)

--run and --power refuse to read outcome data unless the lock exists and still matches SPEC, so a changed
specification cannot be used silently. Changes after locking are deviations: log them in the study rules first.
"""
import argparse, hashlib, json, sys, datetime as dt
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
LOCK = ROOT / "data/prereg_lock.json"

SPEC = {
    "hypothesis": "H2: exposed DPGs lost team members after the 2025 US funding freeze; output fell less than team size",
    "event_date": "2025-01-20",
    "first_quarter": "2024Q1",              # the funding test is an event study of exposed against unexposed DPGs; last quarter = last COMPLETE quarter (partial quarter dropped, outputs are modelled in logs and pre-trends are always checked)
    "reference_quarter": "2024Q4",          # event-study coefficient omitted (last pre-shock quarter)
    "unit": "DPG-quarter",                  # rates use a fixed set of repositories created before 2024
    "sample": "analysis_sample.in_joint_test == True (B1-B3 and repo confidence high); sensitivity: in_joint_test_sens",
    "exposure": "funding_flags.exposed (score 2 or 3, DESIGN B); dose-response with funding_flags.exposure_score",
    "outcomes": {                           # team size and output are never built from the same events: team and output from different events
        "team": "log1p(core_team_dpg)",     # a core contributor is a person active in at least 2 of the 3 months of a quarter: core contributors = active in >=2 of 3 months of the quarter, DPG level, de-duplicated, aliases merged
        "team_secondary": ["log1p(dev_months_dpg)", "log1p(departures_dpg)"],  # developer-months; departures of established contributors
        "output": "log1p(release_minor + release_major + issues_closed)",
        "secondary": ["log1p(pr_merged_human)", "log1p(active_contributors_dpg)", "log1p(maintainers_dpg)"],
    },
    "model": "OLS on log1p outcomes with DPG and quarter fixed effects, exposed x quarter coefficients, SE clustered by DPG (CR1)",
    "elasticity": "log output on log team size is descriptive; output per person is never a primary outcome",
    "checks": ["pre-trend: joint test that exposed x quarter coefficients before the reference quarter are zero",
               "placebo group: exposure_score == 1 (federal money, not foreign aid) vs score 0",
               "placebo date: fake shock at 2023-01-20 using 2022Q1-2023Q4"],
    "robustness": ["winsorise outcomes at 1/99 pct", "DPG-level medians", "restrict controls to the same owner_type as exposed",
                   "sensitivity sample incl. medium confidence"],
    "exploratory_only": ["AI-text signals", "category/sector breakdowns", "PR size", "other team measures"],
    "power": "statistical power is computed from pre-period data before outcomes are read: MDE ~= 2.8 * sd_between_dpg_change_in_pre_period * sqrt(1/n_exposed + 1/n_unexposed); computed from pre-period data only",
}


def spec_hash():
    return hashlib.sha256(json.dumps(SPEC, sort_keys=True).encode()).hexdigest()


def lock():
    if LOCK.exists(): sys.exit(f"{LOCK.name} exists; to change the spec log a deviation in the study rules and delete it deliberately")
    LOCK.write_text(json.dumps({"locked_on": str(dt.date.today()), "sha256": spec_hash(), "spec": SPEC}, indent=2))
    print("locked", spec_hash()[:12])


def require_lock():
    if not LOCK.exists(): sys.exit("no data/prereg_lock.json: run --lock first (before any outcome data are read)")
    if json.loads(LOCK.read_text())["sha256"] != spec_hash():
        sys.exit("SPEC differs from the locked version: that is a deviation. Log it in the study rules, then decide.")


def qkey(q): return int(q[:4]) * 4 + int(q[-1]) - 1
def last_complete_quarter(today=None):
    t = today or dt.date.today(); k = t.year * 4 + (t.month - 1) // 3 - 1
    return f"{k // 4}Q{k % 4 + 1}"


# ---- estimator (numpy only; statsmodels is not installed) ----
def demean_two_way(X, g1, g2, iters=200, tol=1e-10):
    X = X.astype(float).copy()
    for _ in range(iters):
        old = X.copy()
        for g in (g1, g2):
            m = pd.DataFrame(X).groupby(g).transform("mean").to_numpy()
            X = X - m
        if np.abs(X - old).max() < tol: break
    return X


def cluster_ols(y, X, dpg, g_time):
    """Two-way FE OLS (by demeaning) with CR1 cluster-robust SEs. Returns coef, se, cov, df."""
    Z = demean_two_way(np.column_stack([y, X]), dpg, g_time)
    yd, Xd = Z[:, 0], Z[:, 1:]
    XtXi = np.linalg.pinv(Xd.T @ Xd)
    b = XtXi @ Xd.T @ yd
    e = yd - Xd @ b
    ids = pd.factorize(dpg)[0]; G = ids.max() + 1; n, k = Xd.shape
    meat = np.zeros((k, k))
    for gi in range(G):
        s = Xd[ids == gi].T @ e[ids == gi]; meat += np.outer(s, s)
    n_fe = G + len(set(g_time)) - 1
    cov = XtXi @ meat @ XtXi * (G / (G - 1)) * ((n - 1) / max(n - k - n_fe, 1))
    return b, np.sqrt(np.diag(cov)), cov, G - 1


def event_study(panel, outcome, quarters, ref):
    """panel: dpgid, quarter, exposed(0/1), outcome column (already transformed)."""
    qs = [q for q in quarters if q != ref]
    X = np.column_stack([(panel.exposed.to_numpy() * (panel.quarter.to_numpy() == q)).astype(float) for q in qs])
    b, se, cov, df = cluster_ols(panel[outcome].to_numpy(), X, panel.dpgid.to_numpy(), panel.quarter.to_numpy())
    res = pd.DataFrame({"quarter": qs, "coef": b, "se": se}); res["t"] = res.coef / res.se
    pre = [i for i, q in enumerate(qs) if qkey(q) < qkey(ref)]
    chi2 = float(b[pre] @ np.linalg.pinv(cov[np.ix_(pre, pre)]) @ b[pre]) if pre else np.nan
    return res, chi2, len(pre)


def selftest():
    rng = np.random.default_rng(1)
    quarters = [f"{y}Q{q}" for y in (2023, 2024, 2025, 2026) for q in (1, 2, 3, 4)][:14]
    rows = []
    for i in range(900):
        ex = int(i < 300); a = rng.normal(2, 1)
        for q in quarters:
            eff = -0.5 * ex * (qkey(q) >= qkey("2025Q2"))
            rows.append((i, q, ex, a + rng.normal(0, 0.4) + eff))
    d = pd.DataFrame(rows, columns=["dpgid", "quarter", "exposed", "y"])
    res, chi2, k = event_study(d, "y", quarters, "2024Q4")
    post = res[res.quarter.map(qkey) >= qkey("2025Q2")].coef.mean(); pre = res[res.quarter.map(qkey) < qkey("2024Q4")].coef.abs().mean()
    print(f"true post effect -0.50; estimated {post:.2f}; mean |pre coef| {pre:.2f} (should be near 0); pre-trend chi2 {chi2:.1f} on {k} df")
    assert abs(post + 0.5) < 0.1 and pre < 0.15, "estimator failed self-test"
    print("selftest ok")


def load_panel(pre_only=False):
    """Real data. Refuses if inputs the spec relies on are missing."""
    need = {"data/funding_flags.csv": "funding_flags.csv from 08b_funding_flags.py", "data/dpg_quarterly.csv": "03_aggregate.py", "data/analysis_sample.csv": "07_analysis_sample.py"}
    miss = [f"{p} ({w})" for p, w in need.items() if not (ROOT / p).exists()]
    if miss: sys.exit("missing inputs: " + "; ".join(miss))
    flags = pd.read_csv(ROOT / "data/funding_flags.csv"); smp = pd.read_csv(ROOT / "data/analysis_sample.csv")
    for c in ("dpgid", "exposed", "exposure_score"):
        if c not in flags.columns: sys.exit(f"funding_flags.csv lacks column '{c}' (see message board)")
    q = pd.read_csv(ROOT / "data/dpg_quarterly.csv")
    for c in ("core_team_dpg", "dev_months_dpg", "departures_dpg"):
        if c not in q.columns: sys.exit(f"dpg_quarterly.csv lacks '{c}': team must be de-duplicated across repos (rates use a fixed set of repositories created before 2024, message ")
    keep = smp.loc[smp.in_joint_test, "dpgid"]
    p = q[q.dpgid.isin(keep)].merge(flags[["dpgid", "exposed", "exposure_score"]], on="dpgid")
    p["output"] = np.log1p(p.release_minor + p.release_major + p.issues_closed); p["team"] = np.log1p(p.core_team_dpg); p["dev_months"] = np.log1p(p.dev_months_dpg); p["departures"] = np.log1p(p.departures_dpg)
    last = last_complete_quarter()
    if pre_only:  # power (statistical power is computed from pre-period data before outcomes are read): 2023 and 2024 only, nothing from 2025 on
        return p[(p.quarter.map(qkey) >= qkey("2023Q1")) & (p.quarter.map(qkey) < qkey("2025Q1"))], last
    p = p[(p.quarter.map(qkey) >= qkey(SPEC["first_quarter"])) & (p.quarter.map(qkey) <= qkey(last))]
    return p, last


def power():
    require_lock(); p, _ = load_panel(pre_only=True)
    # placebo change = mean(2024 quarters) - mean(2023 quarters) per DPG, the same shape as the real 2025+ vs 2024 contrast
    p = p.assign(year=p.quarter.str[:4])
    ex = p.groupby("dpgid").exposed.first(); n1, n0 = int((ex == 1).sum()), int((ex == 0).sum())
    print(f"exposed {n1}, unexposed {n0} (DPGs with 2023-24 data)")
    for out in ("team", "output"):
        y = p.groupby(["dpgid", "year"])[out].mean().unstack()
        d = (y.get("2024") - y.get("2023")).dropna()
        mde = 2.8 * d.std() * np.sqrt(1 / max(n1, 1) + 1 / max(n0, 1))
        print(f"  {out}: sd of 2023->2024 change {d.std():.2f} (n={len(d)}); minimum detectable effect ~ {mde:.2f} log points (about {100 * (1 - np.exp(-mde)):.0f}% drop)")


def run():
    require_lock(); p, last = load_panel()
    qs = sorted(p.quarter.unique(), key=qkey)
    for out in ("team", "output", "dev_months", "departures"):
        po = p.dropna(subset=[out])  # departures are censored (NaN) in the last quarters
        res, chi2, k = event_study(po, out, sorted(po.quarter.unique(), key=qkey), SPEC["reference_quarter"])
        print(f"\n== {out}: exposed x quarter vs {SPEC['reference_quarter']}; pre-trend chi2 {chi2:.1f} on {k} df (last complete quarter {last}) ==")
        print(res.round(3).to_string(index=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); [ap.add_argument(f"--{x}", action="store_true") for x in ("lock", "selftest", "power", "run")]
    a = ap.parse_args()
    if a.lock: lock()
    elif a.selftest: selftest()
    elif a.power: power()
    elif a.run: run()
    else: print(__doc__)
