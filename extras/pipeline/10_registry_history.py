"""R2/R3 (HIST): registry population at past dates + lapsed/orphan DPG candidates.
Inputs: data/certification_dates.csv (D29), data/hist_pgc_unmatched_urls.csv, cache/hist/cdx/old_slugs.json.
Outputs: data/registry_history.csv, data/lapsed_dpg_repos.csv.  python -I scripts/10_registry_history.py
Evidence tiers (METHODOLOGY D40): current (in API/sitemap now) | orphan_page (live registry page with 'DPG since',
absent from API/sitemap) | wayback_slug_only (slug archived 2025-26, absent now, no content seen) |
archive_submission (file in archived candidates repo, no current match; stage unknown -> NOT counted as DPG)."""
import json, re
from pathlib import Path
import pandas as pd
R = Path(__file__).resolve().parent.parent
c = pd.read_csv(R/'data/certification_dates.csv')
c['status'] = 'current'; c['confidence_pop'] = 'survivor_only'
c['in_registry_2024_01_01'] = c.cert_date <= '2024-01-01'
c['in_registry_2025_01_01'] = c.cert_date <= '2025-01-01'
c['evidence'] = 'current API; cert_date from registry page (D29)'
extra = [
 dict(dpgid='', name='Tilli', cert_date='2023-09-25', status='orphan_page', confidence_pop='medium',
      in_registry_2024_01_01=True, in_registry_2025_01_01='unknown',
      evidence='digitalpublicgoods.net/r/tilli live page: Verified Owner, DPG since 25.09.2023, last evaluated 25.09.2023; absent from API and sitemap (2026-10-29)'),
]
old = json.load(open(R/'cache/hist/cdx/old_slugs.json'))
for s, first, last, since, title in old:
    if s in ('tilli',): continue
    extra.append(dict(dpgid='', name=title or s, cert_date='', status='wayback_slug_only', confidence_pop='low',
        in_registry_2024_01_01='unknown', in_registry_2025_01_01='unknown',
        evidence=f'slug /r/{s} archived 200 from {first[:8]} to {last[:8]}; not in current sitemap; page content unreadable (Wayback blocked fetch / SPA shell)'))
u = pd.read_csv(R/'data/hist_pgc_unmatched_urls.csv').fillna('')
for _, x in u.iterrows():
    if x['current_match'] or not x['name'] or x['name'].lower().startswith('test'): continue
    extra.append(dict(dpgid='', name=x['name'], cert_date='', status='archive_submission', confidence_pop='low',
        in_registry_2024_01_01='unknown', in_registry_2025_01_01='unknown',
        evidence=f"file in publicgoods-candidates digitalpublicgoods/ from {x['first_in_dpg_dir']}; no current-registry match; stage unknown (renames not excluded)"))
h = pd.concat([c[['dpgid','name','cert_date','status','confidence_pop','in_registry_2024_01_01','in_registry_2025_01_01','evidence']], pd.DataFrame(extra)])
h.to_csv(R/'data/registry_history.csv', index=False)
print(h.status.value_counts().to_dict())
print('survivors certified by 2024-01-01:', int(c.in_registry_2024_01_01.sum()), ' by 2025-01-01:', int(c.in_registry_2025_01_01.sum()))
# repos
NOISE = {'airbnb/javascript','ropensci/software-review','italia/publiccode.yml','common-voice/','kotani-pay/docs','labfunctions/labfunctions','github.com/orgs'}
rows = [dict(name='Tilli', status='orphan_page', confidence='medium', host='github', repo=r, evidence='registry page lists github.com/tillioss repos')
        for r in ['tillioss/tilli-web-app','tillioss/tilli-ide','tillioss/tilli-backend-server']]
for _, x in u.iterrows():
    if x['current_match'] or not x['urls'] or x['name'].lower().startswith('test'): continue
    for item in x['urls'].split(' ; '):
        host, o, r = (item.split('/') + [''])[:3]
        if not r or f'{o}/{r}'.lower() in NOISE: continue
        rows.append(dict(name=x['name'], status='archive_submission', confidence='low', host=host.split('.')[0], repo=f'{o}/{r}',
                         evidence='URL in archived candidates file; stage unknown'))
lr = pd.DataFrame(rows).drop_duplicates(['host','repo'])
lr.to_csv(R/'data/lapsed_dpg_repos.csv', index=False)
print(len(lr), lr.groupby(['status','host']).size().to_dict())
