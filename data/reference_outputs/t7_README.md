# T7: who reviews merged PRs, and how much is AI (full cache, 2026-10-29)

Scope: repos in `data/all_repos.csv` with confidence == high, one row per full_name (181 repos had a usable cache; 1 had none). 267,720 merged PRs by human authors, merged 2020 to 2026-10-29. Authors classed with `actor_class` from `scripts/03_aggregate.py` (bots and AI agents excluded as authors).

## Definitions
Each merged human PR is put in one group using reviews submitted on or before `mergedAt`, ignoring reviews by the PR author:
- **human reviewed**: at least one reviewer who is a human.
- **AI only** (`share_ai_only`): no human reviewer, at least one AI review agent (CodeRabbit, Copilot reviewer, Greptile, Cursor, Codex connector, Gemini Code Assist, Claude, Qodo, Korbit, Ellipsis, Sourcery; anything matching AI_AGENTS in `scripts/03_aggregate.py`).
- **Automation only** (`share_automation_only`): no human or AI reviewer; only non-AI automation (github-actions, mergify, other dependency or house bots).
- **unreviewed**: no review at all.
Shares sum to 1. A PR with both AI and automation reviews counts as AI only. Year and half-year come from the merge date.

## Files (script: `scripts/13b_review_ai.py`)
- `t7_review_ai_by_year.csv`, `t7_review_ai_by_half_year.csv` (2024H1 to 2026H2).
- `t7_review_repo_spread.csv`: repos with at least 20 merged human PRs in both 2023-24 and 2025-26 (93 repos); human-review share in each period and the change in points.
- `t7_review_concentration.csv`: the 10 repos adding most unreviewed merged PRs, 2024 vs 2026.
- `t7_ai_reviewers_by_year.csv`: top 10 AI/bot reviewer logins per year, by number of reviews.

## Caveats
- **2026 is partial** (to 29 Oct). 2026H2 covers only July to October and is flagged `partial`; its drop in human review is the least settled number. In the concentration ranking only, 2026 unreviewed counts are multiplied by 4/3 (a rough annualisation of ten months to twelve); everything else uses raw counts.
- **Reviews are capped at the first 10 per PR.** This affects 4.7% of PRs. A human reviewer who comes after ten earlier reviews or bot comments would be missed, so human review is slightly understated on busy PRs. Because AI reviewers leave many reviews, this cap leans slightly toward the "AI only" group in 2025-26.
- Automation-only is small (about 1% by 2026); github-actions is the main one. The rise in AI-only from 2025 is mostly CodeRabbit and the Copilot reviewer. `t7_ai_reviewers_by_year.csv` still lists github-actions among top reviewers, since it lists all non-human reviewers.
- Review on GitHub is not all review: discussion in chat, issues, or pair work is invisible, as are approvals given in comments by the author's own team before opening a PR.
- A few fast-growing repos carry much of the change (see concentration); pooled shares are PR-weighted, so large repos dominate.
