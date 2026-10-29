"""R1 step 2 (HIST): match archived-repo lineages (data/hist_pgc_lineages.csv) to current dpgid.
Cert date rule (METHODOLOGY D29): date of the first commit placing the DPG's file in
digitalpublicgoods/ of DPGAlliance/publicgoods-candidates. The 2021-05-20 batch is a bulk
re-organisation (files moved from screening/), flagged 'medium'. Match: exact normalised name or
alias = high; difflib ratio >= 0.88 = medium (logged); else unmatched (left for Wayback / R2).
Writes data/certification_dates.csv (partial, repo-derived) and data/hist_pgc_unmatched.csv.
"""
import json, re, difflib
from pathlib import Path
import pandas as pd
R = Path(__file__).resolve().parent.parent
d = pd.read_csv(R/'data/hist_pgc_lineages.csv')
reg = json.load(open(R/'data/raw/registry.json', encoding='utf-8'))
norm = lambda s: re.sub(r'[^a-z0-9]', '', s.lower()) if isinstance(s, str) else ''
idx = {}
for r in reg:
    for n in [r['name']] + [a.strip() for a in r.get('aliases', [])]:
        if norm(n): idx.setdefault(norm(n), set()).add(r['dpgid'])
names = {r['dpgid']: r['name'] for r in reg}
rows, unm = [], []
for _, x in d.iterrows():
    hit = idx.get(norm(x['name_in_file'])) or idx.get(norm(x['slug']))
    how = 'name_exact'
    if not hit:
        best = max(idx, key=lambda k: difflib.SequenceMatcher(None, k, norm(x['name_in_file'])).ratio())
        if difflib.SequenceMatcher(None, best, norm(x['name_in_file'])).ratio() >= 0.88:
            hit, how = idx[best], 'name_fuzzy'
    if not hit or len(hit) > 1:
        unm.append(x.to_dict()); continue
    dpgid = next(iter(hit))
    conf = 'high' if how == 'name_exact' else 'medium'
    if x['first_in_dpg_dir'] == '2021-05-20': conf = 'medium' if conf == 'high' else 'low'
    rows.append(dict(dpgid=dpgid, name=names[dpgid], cert_date=x['first_in_dpg_dir'],
                     source='publicgoods-candidates:first commit in digitalpublicgoods/',
                     confidence=conf, match=how, first_commit_any_dir=x['first_commit'], file=x['path']))
out = pd.DataFrame(rows).sort_values('cert_date')
dup = out[out.dpgid.duplicated(keep=False)]
out = out.sort_values('cert_date').drop_duplicates('dpgid', keep='first')
out.to_csv(R/'data/certification_dates.csv', index=False)
pd.DataFrame(unm).to_csv(R/'data/hist_pgc_unmatched.csv', index=False)
print(len(out), 'matched;', len(unm), 'unmatched;', len(dup), 'dup rows'); print(out.confidence.value_counts())
print(out[out.match=='name_fuzzy'][['name','file']].to_string())
