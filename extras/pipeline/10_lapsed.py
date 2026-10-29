"""R2/R3 (HIST): unmatched archived-repo files -> repo URLs -> match to current registry repos by owner/repo
(and by owner when the DPG is org-level). No match = lapsed/renamed candidate.
Version used: the latest committed content of the file (git show of last commit that had it).
Output data/hist_pgc_unmatched_urls.csv.  python -I scripts/10_lapsed.py"""
import re, subprocess
from pathlib import Path
import pandas as pd
R = Path(__file__).resolve().parent.parent
PGC = R/'cache/hist/pgc'
u = pd.read_csv(R/'data/hist_pgc_unmatched.csv')
cur = pd.read_csv(R/'data/dpg_repo_map.csv')
cur_full = dict(zip(cur.full_name_lc.dropna(), cur.dpg))
cur_owner = {}
for f, n in zip(cur.full_name_lc.dropna(), cur.dpg): cur_owner.setdefault(f.split('/')[0], n)
URL = re.compile(r'https?://(?:www\.)?(github\.com|gitlab\.com|bitbucket\.org)/([A-Za-z0-9_.-]+)(?:/([A-Za-z0-9_.-]+))?')
def git(*a):
    return subprocess.run(['git', '-C', str(PGC), *a], capture_output=True, text=True, encoding='utf-8', errors='replace').stdout
rows = []
for _, x in u.iterrows():
    p = x['path']
    sha = git('log', '-1', '--format=%H', '--', p).strip()
    txt = git('show', f'{sha}^:{p}') if not (PGC/p).exists() else git('show', f'HEAD:{p}')
    if not txt.strip(): txt = git('show', f'{sha}:{p}')
    found = []
    for host, o, r in URL.findall(txt):
        r = (r or '').removesuffix('.git').rstrip('.')
        if o.lower() in ('github', 'orgs', 'topics', 'sponsors'): continue
        found.append((host, o, r))
    uniq = list(dict.fromkeys(found))
    hit = ''
    for host, o, r in uniq:
        k = f'{o}/{r}'.lower()
        if k in cur_full: hit = f'repo:{cur_full[k]}'; break
    if not hit:
        for host, o, r in uniq:
            if o.lower() in cur_owner: hit = f'owner:{cur_owner[o.lower()]}'; break
    rows.append(dict(slug=x['slug'], name=x['name_in_file'], present_at_archive=x['present_at_archive'],
                     first_in_dpg_dir=x['first_in_dpg_dir'], last_commit=x['last_commit'],
                     urls=' ; '.join(f'{h}/{o}/{r}' for h, o, r in uniq[:6]), current_match=hit))
out = pd.DataFrame(rows)
out.to_csv(R/'data/hist_pgc_unmatched_urls.csv', index=False)
print(len(out), (out.current_match != '').sum(), 'matched a current DPG repo/owner;', (out.urls == '').sum(), 'no urls')
print(out[out.current_match != ''][['name', 'current_match']].to_string())
