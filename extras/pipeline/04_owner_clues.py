"""Collect clues to identify each DPG's legal owner (the registry only repeats the DPG name as the org).
Clues: contact-email domain, website domain + homepage title/site_name/copyright line, GitHub owner profiles,
"developed by ..." phrases in the registry description. Output: data/owner_clues.csv (input to the hand-curated
data/dpg_owner_map.csv). Caches: cache/_profile_<login>.json (GitHub REST), cache/web/<dpgid>.json (extracted fields only).
"""
import html, json, os, re, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse
import pandas as pd, requests

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"
WEB = CACHE / "web"
WEB.mkdir(parents=True, exist_ok=True)
envf = ROOT / ".env"
if envf.exists():
    for line in envf.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"\''))
GH = requests.Session()
GH.headers["Authorization"] = f"bearer {os.environ['GITHUB_TOKEN']}"
GENERIC = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "protonmail.com", "proton.me", "icloud.com"}
BY = re.compile(r"((?:developed|maintained|created|built|led|owned|stewarded|supported|funded) by|an? (?:initiative|project|product) of)\s+([^.;\n]{3,120})", re.I)

def domain(url):
    if not url: return ""
    if "://" not in url: url = "http://" + url
    d = urlparse(url.strip()).netloc.lower().split("@")[-1].split(":")[0]
    return d[4:] if d.startswith("www.") else d

def gh_profile(login):
    f = CACHE / f"_profile_{login}.json"
    if f.exists(): return json.loads(f.read_text(encoding="utf-8"))
    for attempt in range(5):
        r = GH.get(f"https://api.github.com/users/{login}", timeout=30)
        if r.status_code in (403, 429):
            time.sleep(max(5, int(r.headers.get("x-ratelimit-reset", time.time() + 60)) - time.time() + 2)); continue
        if r.status_code == 404:
            j = {"login": login, "status": "not_found"}; break
        r.raise_for_status()
        p = r.json()
        j = {k: p.get(k) for k in ("login", "type", "name", "company", "blog", "location", "email", "bio", "description")}
        if p.get("type") == "Organization":  # /users omits the org description
            o = GH.get(f"https://api.github.com/orgs/{login}", timeout=30)
            if o.ok: j["description"] = o.json().get("description")
        break
    f.write_text(json.dumps(j), encoding="utf-8")
    return j

def web_clues(dpgid, url):
    f = WEB / f"{dpgid}.json"
    if f.exists(): return json.loads(f.read_text(encoding="utf-8"))
    j = {"url": url, "final_url": "", "title": "", "site_name": "", "copyright": "", "error": ""}
    if url:
        try:
            r = requests.get(url if "://" in url else "https://" + url, timeout=20,
                             headers={"User-Agent": "Mozilla/5.0 (research; DPG owner mapping)"})
            t = r.text[:2_000_000]
            j["final_url"] = r.url
            m = re.search(r"<title[^>]*>(.*?)</title>", t, re.I | re.S)
            j["title"] = html.unescape(m.group(1)).strip()[:200] if m else ""
            m = re.search(r'property=["\']og:site_name["\'][^>]*content=["\']([^"\']+)', t, re.I)
            j["site_name"] = html.unescape(m.group(1))[:200] if m else ""
            txt = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<(script|style).*?</\1>", " ", t)))
            m = re.search(r"(?:©|&copy;|copyright)\s*([^|\n]{3,150})", txt, re.I)
            j["copyright"] = re.sub(r"\s+", " ", m.group(1)).strip()[:150] if m else ""
            if not r.ok: j["error"] = f"http {r.status_code}"
        except Exception as e:
            j["error"] = type(e).__name__
    f.write_text(json.dumps(j), encoding="utf-8")
    return j

reg = json.load(open(ROOT / "data/raw/registry.json", encoding="utf-8"))
rm = pd.read_csv(ROOT / "data/dpg_repo_map.csv")
rm = rm[rm.host.isin(["github", "github_org"])]
owners = rm.assign(login=rm.full_name.str.split("/").str[0]).groupby("dpgid").login.agg(lambda s: sorted(set(s), key=str.lower))

with ThreadPoolExecutor(8) as ex:
    webs = dict(zip([d["dpgid"] for d in reg], ex.map(lambda d: web_clues(d["dpgid"], (d.get("website") or "").strip()), reg)))

rows = []
for d in reg:
    o = (d.get("organizations") or [{}])[0]
    em = (o.get("contact_email") or "").split("@")[-1].strip().lower()
    logins = owners.get(d["dpgid"], [])
    profs = [gh_profile(l) for l in logins]
    w = webs[d["dpgid"]]
    by = "; ".join(" ".join(m) for m in BY.findall(d.get("description") or ""))[:300]
    rows.append(dict(
        dpgid=d["dpgid"], dpg=d["name"], categories="|".join(c for c in d.get("categories", []) if c),
        website=(d.get("website") or "").strip(), website_domain=domain(d.get("website")),
        final_domain=domain(w["final_url"]), email_domain=em, email_generic=em in GENERIC,
        web_title=w["title"], web_site_name=w["site_name"], web_copyright=w["copyright"], web_error=w["error"],
        gh_logins="|".join(logins),
        gh_names="|".join(p.get("name") or "" for p in profs),
        gh_company="|".join(p.get("company") or "" for p in profs),
        gh_blog="|".join(p.get("blog") or "" for p in profs),
        gh_location="|".join(p.get("location") or "" for p in profs),
        gh_desc="|".join((p.get("description") or p.get("bio") or "")[:150] for p in profs),
        desc_by=by,
        deploy_orgs="|".join(x.get("name", "") if isinstance(x, dict) else str(x) for x in (d.get("deploymentOrganisations") or []))[:300],
        awards=(d.get("awardsReceived") or "")[:300] if isinstance(d.get("awardsReceived"), str) else json.dumps(d.get("awardsReceived"))[:300],
    ))
df = pd.DataFrame(rows)
df.to_csv(ROOT / "data/owner_clues.csv", index=False)
print(f"DPGs: {len(df)}; generic email: {df.email_generic.sum()}; web errors: {(df.web_error != '').sum()}; "
      f"with GitHub owner: {(df.gh_logins != '').sum()}; with 'developed by' phrase: {(df.desc_by != '').sum()}")
