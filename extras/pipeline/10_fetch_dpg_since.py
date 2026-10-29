"""R1 step 3 (HIST): official 'DPG since' date from each live registry page digitalpublicgoods.net/r/<slug>.
Slug = name lowercased, non-alphanumerics -> '-'; fallbacks: aliases, dpgid-less variants. Caches
{dpgid,slug,url,dpg_since,status} per DPG in cache/hist/live/<dpgid>.json (delete to refetch).
Public website, not the GitHub API. Writes data/dpg_since_raw.csv.  python -I scripts/10_fetch_dpg_since.py
"""
import json, re, time
from pathlib import Path
import requests, pandas as pd
R = Path(__file__).resolve().parent.parent
C = R/'cache/hist/live'; C.mkdir(parents=True, exist_ok=True)
reg = json.load(open(R/'data/raw/registry.json', encoding='utf-8'))
slug = lambda s: re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', s.lower())).strip('-')
PAT = re.compile(r'DPG since</p><p[^>]*>([^<]*)</p>')
def try_slug(sl):
    r = requests.get(f'https://digitalpublicgoods.net/r/{sl}', timeout=60)
    m = PAT.search(r.text)
    return r.status_code, (m.group(1).strip() if m else None)
rows = []
for x in reg:
    f = C/f"{x['dpgid']}.json"
    if f.exists():
        rows.append(json.load(open(f))); continue
    cands = []
    for n in [x['name']] + [a.strip() for a in x.get('aliases', [])]:
        s = slug(n)
        if s and s not in cands: cands.append(s)
    res = dict(dpgid=x['dpgid'], name=x['name'], slug=None, dpg_since=None, status=None)
    for s in cands[:3]:
        try:
            st, ds = try_slug(s)
        except Exception as e:
            st, ds = str(e)[:30], None
        res.update(slug=s, status=st)
        time.sleep(0.4)
        if ds:
            res['dpg_since'] = ds; break
    json.dump(res, open(f, 'w'))
    rows.append(res)
df = pd.DataFrame(rows)
df.to_csv(R/'data/dpg_since_raw.csv', index=False)
print(len(df), df.dpg_since.notna().sum(), 'with date')
