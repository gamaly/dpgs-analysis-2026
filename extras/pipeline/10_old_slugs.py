"""R2/R3 (HIST): archived /r/<slug> pages (Wayback CDX) whose slug is not in today's sitemap.
Fetches the latest archived copy of each to read title and 'DPG since'. Output cache/hist/cdx/old_slugs.json."""
import json, re, time
from pathlib import Path
import requests
R = Path(__file__).resolve().parent.parent
BS = chr(92)
r = json.load(open(R/'cache/hist/cdx/r_slugs.json'))[1:]
cur = set(re.findall(r'/r/([^<]+)</loc>', open(R/'cache/hist/live/_sitemap.xml', encoding='utf-8').read().replace('\n', '')))
seen = {}
for k, ts, st in r:
    m = re.search(r'/r/([^/?#]+)$', k)
    if m: seen[m.group(1).strip(BS)] = ts
old = sorted(s for s in seen if s not in cur and s not in ('$1', 'dpg-slug') and '.' not in s)
print(len(old), old)
PAT = re.compile(r'DPG since</p><p[^>]*>([^<]*)</p>'); out = []
for s in old:
    q = requests.get(f'https://web.archive.org/cdx/search/cdx?url=digitalpublicgoods.net/r/{s}&output=json&fl=timestamp&filter=statuscode:200', timeout=60).json()[1:]
    ts = [x[0] for x in q]
    if not ts: out.append((s, None, None, None, None)); continue
    t = requests.get(f'https://web.archive.org/web/{ts[-1]}id_/https://digitalpublicgoods.net/r/{s}', timeout=90).text
    m = PAT.search(t); h1 = re.search(r'<h1[^>]*>(.*?)</h1>', t, re.S)
    out.append((s, ts[0], ts[-1], m.group(1) if m else None, re.sub('<[^>]+>', '', h1.group(1)).strip() if h1 else None))
    print(out[-1]); time.sleep(0.5)
json.dump(out, open(R/'cache/hist/cdx/old_slugs.json', 'w'))
