"""AI mentions in PR and commit text over time (AI mentions in PR and commit text are matched by keyword and reported as a rough lower bound).
Reads cache/<owner>__<repo>.json (needs PR bodyText / commit messageBody from the updated 02 collector).
Two separate signals, never merged:
  author : text says AI helped write the change (Claude Code, Copilot, Cursor, ChatGPT, ...). Lower bound only (dependency bots are kept out of headline counts and AI agent accounts are a class of their own).
  topic  : the change is about AI features (chatbot/LLM, classifier/ML). Says what DPGs build, not how they code.
Outputs: data/pr_text_ai_repo_month.csv, data/pr_text_ai_monthly.csv (registry, by confidence tier),
         data/pr_text_ai_samples.csv (random matches per term for hand-checking precision).
Run: python -I scripts/03c_pr_text_ai.py
"""
import json, re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CACHE, DATA = ROOT / "cache", ROOT / "data"
WINDOW_START = "2020-01-01"  # the data window starts on 1 January 2020
PER_REPO_CAP = 5  # max matches per repo in the hand-check sample, so one repo cannot dominate (term groups that failed the hand-checked precision test are not reported)

# Term lists live here so they can change without refetching. Any change gets a line in AI mentions in PR and commit text are matched by keyword and reported as a rough lower bound.
AUTHOR_TERMS = {
    "claude": r"claude code|generated with \[?claude|co-authored-by:\s*claude|\bclaude\b",
    "copilot": r"co-authored-by:\s*copilot|github copilot|copilot (?:suggest|generated|wrote|agent)|(?:generated|written|authored|created) (?:by|with|using) copilot",
    "cursor": r"\bcursor (?:ai|ide|agent)\b|co-authored-by:\s*cursor|generated (?:by|with) cursor",
    "chatgpt_codex": r"chat\s?gpt|\bcodex\b|openai codex|written (?:by|with) gpt",
    "other_tool": r"\bdevin\b|\baider\b|\bwindsurf\b|\bcline\b|\bjules\b|amazon q|\bcodewhisperer\b|\btabnine\b",  # gemini terms removed (term groups that failed the hand-checked precision test are not reported): review bot / tool install, 0/4 precision
    "generic": r"ai[- ]generated|ai[- ]assisted|generated (?:by|with|using) (?:an )?(?:ai|llm)|written (?:by|with) (?:an )?(?:ai|llm)|\U0001F916 generated",
}
TOPIC_TERMS = {
    "chatbot_llm": r"chat\s?bot|\bllms?\b|large language model|\bgpt-?\d?|openai|anthropic|gemini|\bllama\b|mistral|"
                   r"langchain|llamaindex|\brag\b|retrieval[- ]augmented|embeddings?|vector (?:db|store|search)|prompts?\b|"
                   r"generative ai|genai|virtual assistant|conversational ai|\bwhisper\b|text[- ]to[- ]speech|speech[- ]to[- ]text",
    "classifier_ml": r"classifiers?|classification model|machine[- ]learning|\bML\b|deep learning|neural net|"
                     r"tensorflow|pytorch|scikit|sklearn|hugging ?face|\bnlp\b|natural language processing|"
                     r"computer vision|image recognition|object detection|\bxgboost\b|random forest|model training|"
                     r"train(?:ed|ing)? (?:a |the )?model|predictive model|\bAI\b|artificial intelligence",
}
# \bML\b and \bAI\b are matched case-sensitively; everything else case-insensitive.
CS = {"\\bML\\b", "\\bAI\\b"}
def compile_terms(d):
    out = {}
    for k, pat in d.items():
        cs_parts = [p for p in pat.split("|") if p in CS]
        ci_parts = [p for p in pat.split("|") if p not in CS]
        out[k] = (re.compile("|".join(ci_parts), re.I) if ci_parts else None,
                  re.compile("|".join(cs_parts)) if cs_parts else None)
    return out
AUTH_RX, TOPIC_RX = compile_terms(AUTHOR_TERMS), compile_terms(TOPIC_TERMS)

def hits(rx_map, text):
    found = []
    for k, (ci, cs) in rx_map.items():
        m = (ci.search(text) if ci else None) or (cs.search(text) if cs else None)
        if m: found.append((k, m.group(0), text[max(0, m.start() - 100):m.end() + 100].replace(chr(10), ' ')))
    return found

BOT_LOGINS = {"dependabot", "renovate", "github-actions", "pre-commit-ci", "snyk-bot", "greenkeeper", "weblate", "transifex-integration"}
def author_class(a):
    """human | bot | ai_agent. Copilot/Devin-style agents are their own class (dependency bots are kept out of headline counts and AI agent accounts are a class of their own), not dropped with dependency bots."""
    if not a: return "human"  # deleted account ('ghost')
    login = (a.get("login") or "").lower().replace("[bot]", "")
    if login in {"copilot", "copilot-swe-agent", "devin-ai-integration", "cursor", "codegen-sh", "claude"}: return "ai_agent"
    if a.get("__typename") == "Bot" or (a.get("login") or "").endswith("[bot]") or login in BOT_LOGINS: return "bot"
    return "human"

conf = pd.read_csv(DATA / "all_repos.csv").drop_duplicates("full_name").set_index("full_name")["confidence"].to_dict()
conf_l = {k.lower(): v for k, v in conf.items()}

rows, samples = [], []
for f in sorted(CACHE.glob("*__*.json")):
    if f.name.startswith("_") or f.name.startswith("inv_"): continue
    d = json.loads(f.read_text())
    if d.get("status") != "ok": continue
    full = d["full_name"]; tier = conf_l.get(full.lower(), "unknown")
    recs = []
    for p in d.get("prs") or []:
        txt_t, txt_b = p.get("title") or "", p.get("bodyText") or ""
        recs.append(("pr", p["createdAt"], author_class(p.get("author")), txt_t, txt_b))
    for c in d.get("commits") or []:
        recs.append(("commit", c["committedDate"], "human", c.get("messageHeadline") or "", c.get("messageBody") or ""))
    for kind, ts, cls, t, b in recs:
        if ts < WINDOW_START: continue  # collector pages by updatedAt, so older-created PRs come along
        a_hits = hits(AUTH_RX, t + "\n" + b)
        tp_t, tp_b = hits(TOPIC_RX, t), hits(TOPIC_RX, b)
        r = {"full_name": full, "tier": tier, "kind": kind, "month": ts[:7], "author_class": cls, "n": 1,
             "ai_author_any": bool(a_hits), "ai_topic_title": bool(tp_t), "ai_topic_any": bool(tp_t or tp_b)}
        for k in AUTHOR_TERMS: r["a_" + k] = any(h[0] == k for h in a_hits)
        for k in TOPIC_TERMS: r["t_" + k] = any(h[0] == k for h in tp_t + tp_b)
        rows.append(r)
        for src, hs in (("author", a_hits), ("topic", tp_t + tp_b)):
            for k, m, ctx in hs:
                samples.append({"full_name": full, "kind": kind, "month": ts[:7], "signal": src, "group": k, "match": m, "title": t[:150], "context": ctx})

df = pd.DataFrame(rows)
if df.empty:
    raise SystemExit("no cached repo data with text; run 02_collect_github.py first")
flag_cols = [c for c in df.columns if c.startswith(("ai_", "a_", "t_"))]
repo_month = df.groupby(["full_name", "tier", "kind", "author_class", "month"], as_index=False)[["n"] + flag_cols].sum()
repo_month.to_csv(DATA / "pr_text_ai_repo_month.csv", index=False)

# Registry level: human + ai_agent PRs separately from bots (dependency bots are kept out of headline counts and AI agent accounts are a class of their own). Tiers: primary = high, sensitivity = high+medium (only high-confidence repositories and DPGs feed the main results).
reg = []
for label, tiers in (("high", ["high"]), ("high+medium", ["high", "medium"])):
    sub = repo_month[repo_month.tier.isin(tiers)]
    g = sub.groupby(["kind", "author_class", "month"], as_index=False).agg(
        repos=("full_name", "nunique"), **{c: (c, "sum") for c in ["n"] + flag_cols})
    g.insert(0, "sample", label); reg.append(g)
monthly = pd.concat(reg)
for c in flag_cols: monthly["share_" + c] = monthly[c] / monthly["n"]
monthly.to_csv(DATA / "pr_text_ai_monthly.csv", index=False)

s = pd.DataFrame(samples)
if not s.empty:
    s = pd.concat([x.sample(frac=1, random_state=1).groupby("full_name").head(PER_REPO_CAP).head(30) for _, x in s.groupby(["signal", "group"])])  # keeps group columns
s.insert(len(s.columns), "correct", "")  # hand-check verdict: 1 = real AI-authorship/topic mention, 0 = false positive
sf = DATA / "pr_text_ai_samples.csv"
if sf.exists() and pd.read_csv(sf, dtype=str).get("correct", pd.Series(dtype=str)).notna().any():
    sf = DATA / "pr_text_ai_samples_new.csv"  # never overwrite hand-checked verdicts
    print(f"existing samples file has verdicts; wrote {sf.name} instead")
s.to_csv(sf, index=False)

# Precision gate (DESIGN D): per author group, share of hand-checked matches that are real. Needs >= 80%.
chk = pd.read_csv(DATA / "pr_text_ai_samples.csv", dtype={"correct": str})
chk = chk[(chk.signal == "author") & chk.correct.isin(["0", "1"])]
if len(chk):
    p = chk.assign(ok=chk.correct == "1").groupby("group").ok.agg(["sum", "count"])
    p["precision"] = (p["sum"] / p["count"]).round(2); p["passes_80"] = p.precision >= 0.8
    print("\nauthor-group precision from hand checks:\n" + p.to_string())

# Quick view: yearly share of human PRs mentioning AI (primary sample)
y = monthly[(monthly["sample"] == "high") & (monthly.kind == "pr") & (monthly.author_class == "human")].copy()
y["year"] = y.month.str[:4]
t = y.groupby("year")[["n", "ai_author_any", "ai_topic_title", "ai_topic_any", "t_chatbot_llm", "t_classifier_ml"]].sum()
for c in t.columns[1:]: t[c + "_%"] = (100 * t[c] / t["n"]).round(2)
print(t.to_string())
