# Data dictionary

Every column of every CSV in `data/`. Files marked HAND-CURATED were built by hand from evidence and carry confidence columns. Dates are ISO (YYYY-MM-DD) unless noted; quarters look like `2025Q3`. Blank = not applicable or unknown (never zero unless stated). The data stop on 2026-10-29; 2026Q4 is partial and flagged. Scripts named in brackets are in `pipeline/`. `prereg_lock.json` is the locked pre-registered specification of the event study (no columns).

## ai_feature_prs.csv

One row per merged human PR that matches the AI-feature terms (03f).
1,123 rows, 89 KB.

| column | meaning |
|---|---|
| `dpgid` | DPG identifier from the registry (GID...). Join key across files. |
| `dpg` | DPG name as listed in the registry. |
| `confidence` | Repo confidence tier (METHODOLOGY D14): high / medium / low / excluded. |
| `full_name` | GitHub repository as owner/name (after following renames). Public project identifier. |
| `merged_at` | Merge timestamp of the pull request (UTC). |
| `source` | Where the match came from: title or body of the PR (ai_feature_prs); listed_repo or org_enumerated (all_repos). |
| `term` | The matched keyword. |
| `title` | PR title. Blank except for the few PRs the post quotes or paraphrases (privacy). |

## ai_feature_prs_shipped.csv

Same rows plus whether and when the change reached a release (03f/03g).
1,123 rows, 138 KB.

| column | meaning |
|---|---|
| `dpgid` | DPG identifier from the registry (GID...). Join key across files. |
| `dpg` | DPG name as listed in the registry. |
| `confidence` | Repo confidence tier (METHODOLOGY D14): high / medium / low / excluded. |
| `full_name` | GitHub repository as owner/name (after following renames). Public project identifier. |
| `merged_at` | Merge timestamp of the pull request (UTC). |
| `source` | Where the match came from: title or body of the PR (ai_feature_prs); listed_repo or org_enumerated (all_repos). |
| `term` | The matched keyword. |
| `title` | PR title. Blank except for the few PRs the post quotes or paraphrases (privacy). |
| `shipped` | True if a release or tag was published after the merge. |
| `first_release_tag` | Tag/name of the first release after the merge. |
| `first_release_date` | Date of that release. |
| `days_to_release` | Days from merge to first release. |
| `release_source` | Whether the release came from GitHub Releases or from a git tag. |

## ai_feature_prs_yearly.csv

Merged PRs and AI-feature PRs per year and repo tier.
14 rows, 0 KB.

| column | meaning |
|---|---|
| `confidence` | Repo confidence tier (METHODOLOGY D14): high / medium / low / excluded. |
| `year` | Calendar year. |
| `merged_prs` | Merged human-authored PRs in the high-tier repos that year (denominator for the AI-feature share). |
| `ai_feature_prs` | Merged PRs matching the AI-feature terms (title or cleaned body). |
| `ai_feature_prs_title` | Of those, matches in the title. |
| `dpgs` | DPGs with any merged PR that year. |
| `dpgs_with_ai_feature_pr` | DPGs with at least one AI-feature PR that year. |

## all_repos.csv

Repo inventory with confidence tiers (02a, 02b). Rejected organisation repos are summarised separately.
1,170 rows, 221 KB.

| column | meaning |
|---|---|
| `dpgid` | DPG identifier from the registry (GID...). Join key across files. |
| `dpg` | DPG name as listed in the registry. |
| `source` | Where the match came from: title or body of the PR (ai_feature_prs); listed_repo or org_enumerated (all_repos). |
| `listed` | True if the repo is listed directly in the registry. |
| `full_name` | GitHub repository as owner/name (after following renames). Public project identifier. |
| `resolved` | True if the repo still resolves on GitHub. |
| `moved` | True if GitHub redirected the repo (renamed or transferred); full_name holds the new name. |
| `fork` | True if the repo is a fork. |
| `mirror` | True if the repo is a mirror. |
| `archived` | Archived on GitHub. |
| `pushed_at` | Date of the last push. |
| `stars` | GitHub stars at collection time. |
| `name_match` | True if the repo name matches the DPG name or an alias. |
| `shared` | True if the repo is attributed to more than one DPG. |
| `confidence` | Repo confidence tier (METHODOLOGY D14): high / medium / low / excluded. |
| `confidence_reason` | Why the repo got its tier. |
| `org_dedicated` | True if the DPG's GitHub organisation is dedicated to it (rule D30). |
| `nonproduct_name` | True if the repo name looks like a non-product repo (docs, website, ...). |
| `stale_since_2020` | True if the repo has had no push since 2020-01-01. |

## all_repos_not_matched_summary.csv

Per DPG: number of organisation repos rejected by the name rule.
8 rows, 0 KB.

| column | meaning |
|---|---|
| `dpgid` | DPG identifier from the registry (GID...). Join key across files. |
| `dpg` | DPG name as listed in the registry. |
| `n_org_repos_not_matched` | Number of organisation repos rejected by the name rule (not released). |

## analysis_sample.csv

Per-DPG sample membership, owner and exposure flags (07).
256 rows, 82 KB.

| column | meaning |
|---|---|
| `dpgid` | DPG identifier from the registry (GID...). Join key across files. |
| `dpg` | DPG name as listed in the registry. |
| `owner_name` | Owner organisation (hand-curated). An organisation, not a person. |
| `owner_type` | USNP = US nonprofit filing a 990; NP non-US nonprofit; CO company; GOV government; UN UN body; MDB development bank; UNIV university; COMM community project; UNKNOWN. |
| `owner_country` | Owner's country (ISO code). |
| `confidence` | Repo confidence tier (METHODOLOGY D14): high / medium / low / excluded. |
| `us_990_candidate` | True if the owner is a US nonprofit that could be matched to a Form 990. |
| `reviewed` | Human review flag of the hand-curated map (blank until reviewed). |
| `declared_owner` | Owner as declared to the DPG Alliance (registry clearOwnership). Individuals' names replaced by [individual]. |
| `declared_owner_url` | URL given with the declaration. |
| `ownership_check` | Result of comparing the declaration with other clues (D38). |
| `ein` | US Employer Identification Number of the owner. |
| `ein_confidence` | Confidence of the owner-to-EIN match. |
| `attribution` | How much of the filer is the DPG: direct / partial (whole org, DPG is one product) / parent / host. |
| `baseline_990_years` | Number of 990 years available before 2025. |
| `dpg_confidence` | DPG confidence tier (high / medium / low / no_usable_repo). |
| `exposure_score` | US foreign-aid exposure of the owner: 3 prime award, 2 sub-award, 1 other federal money, 0 none (DESIGN part B). |
| `exposed` | 1 if exposure_score is 2 or 3, 0 if not, blank if the DPG is not in the exposure sample. |
| `exposure_score_sens` | Same, sensitivity definition (looser owner matching). |
| `exposed_sens` | Exposed flag, sensitivity definition. |
| `check_purchase_order_only` | True if the only evidence is a purchase order (weak). |
| `in_funding_990` | In the Form 990 sample. |
| `in_funding_990_sens` | Same, sensitivity. |
| `in_exposure` | In the exposure sample. |
| `in_exposure_sens` | Same, sensitivity. |
| `in_joint_test` | In the joint sample used for the event study (exposure data + usable high-confidence repo + panel rows). |
| `in_joint_test_sens` | Same, sensitivity. |

## donor_flags.csv

Non-US donor exposure and terminated awards per DPG (11).
256 rows, 66 KB.

| column | meaning |
|---|---|
| `dpgid` | DPG identifier from the registry (GID...). Join key across files. |
| `dpg` | DPG name as listed in the registry. |
| `owner_name` | Owner organisation (hand-curated). An organisation, not a person. |
| `owner_type` | USNP = US nonprofit filing a 990; NP non-US nonprofit; CO company; GOV government; UN UN body; MDB development bank; UNIV university; COMM community project; UNKNOWN. |
| `owner_conf` | Owner-map confidence carried into donor_flags. |
| `n_act_high` | Non-US donor activities found (IATI), high-confidence matches. |
| `donors_high` | Donors named in those activities. |
| `n_act_sens` | Same, sensitivity matches. |
| `donors_sens` | Donors, sensitivity matches. |
| `nonus_exposed` | True if a non-US donor with 2025 cuts funded the owner (high matches). |
| `nonus_exposed_sens` | Same, sensitivity. |
| `cut_2025_activities` | Number of those activities touched by 2025 cuts. |
| `terminated_award` | True if a US award to the owner appears on the termination list. |
| `owner_searched_big_body` | True if the owner is a large body for which the search is less reliable. |
| `caveat` | Standing caveat for the row. |
| `source` | Where the match came from: title or body of the PR (ai_feature_prs); listed_repo or org_enumerated (all_repos). |
| `terminated_award_n` | Number of terminated awards. |

## dpg_confidence.csv

DPG confidence tier (02b).
202 rows, 11 KB.

| column | meaning |
|---|---|
| `dpgid` | DPG identifier from the registry (GID...). Join key across files. |
| `dpg` | DPG name as listed in the registry. |
| `n_repos` | Number of repos attributed to the DPG. |
| `n_high` | ...of which high. |
| `n_medium` | ...of which medium. |
| `n_low` | ...of which low. |
| `org_only` | True if the DPG lists only a GitHub organisation. |
| `dpg_confidence` | DPG tier. |
| `n_listed_lost` | Listed repos that no longer resolve. |

## dpg_no_cohort_repo.csv

DPGs with no cohort repo (D45).
23 rows, 4 KB.

| column | meaning |
|---|---|
| `dpgid` | DPG identifier from the registry (GID...). Join key across files. |
| `dpg` | DPG name as listed in the registry. |
| `repos` | Repos of the DPG (| separated). |
| `earliest_repo_created` | Creation date of its oldest repo. |
| `reason` | Why the DPG has no cohort repo. |
| `note` | Free note. |

## dpg_owner_map.csv

HAND-CURATED owner map with confidence columns (04, D38).
256 rows, 70 KB.

| column | meaning |
|---|---|
| `dpgid` | DPG identifier from the registry (GID...). Join key across files. |
| `dpg` | DPG name as listed in the registry. |
| `owner_name` | Owner organisation (hand-curated). An organisation, not a person. |
| `owner_type` | USNP = US nonprofit filing a 990; NP non-US nonprofit; CO company; GOV government; UN UN body; MDB development bank; UNIV university; COMM community project; UNKNOWN. |
| `owner_country` | Owner's country (ISO code). |
| `confidence` | Repo confidence tier (METHODOLOGY D14): high / medium / low / excluded. |
| `related_orgs` | Implementers/funders/hosts also searched for awards (organisations). |
| `notes` | Free-text notes of the curator (no personal data). |
| `us_990_candidate` | True if the owner is a US nonprofit that could be matched to a Form 990. |
| `reviewed` | Human review flag of the hand-curated map (blank until reviewed). |
| `declared_owner` | Owner as declared to the DPG Alliance (registry clearOwnership). Individuals' names replaced by [individual]. |
| `declared_owner_url` | URL given with the declaration. |
| `ownership_check` | Result of comparing the declaration with other clues (D38). |

## dpg_quarterly.csv

DPG-quarter panel (03_aggregate.py).
3,837 rows, 691 KB.

| column | meaning |
|---|---|
| `dpgid` | DPG identifier from the registry (GID...). Join key across files. |
| `dpg` | DPG name as listed in the registry. |
| `quarter` | Calendar quarter, e.g. 2025Q3. |
| `pr_opened_human` | PRs opened by human authors. |
| `pr_merged_human` | PRs merged that were authored by humans. |
| `lines_changed` | Additions + deletions of merged human PRs (context only; AI inflates it). |
| `pr_reviewed_before_merge` | Merged human PRs with a review by someone other than the author before merge. |
| `pr_closed_unmerged_human` | Human PRs closed without merge. |
| `pr_opened_dep_bot` | PRs opened by dependency/automation bots (Dependabot, Renovate, github-actions, ...). |
| `pr_merged_dep_bot` | ...merged. |
| `pr_closed_unmerged_dep_bot` | ...closed unmerged. |
| `issues_closed` | Issues closed. |
| `commits_dep_bot` | Commits by dependency bots. |
| `commits_human` | Commits by humans. |
| `release_minor` | Releases whose version increases the minor number. |
| `release_total` | All releases (GitHub Releases, or tags if a repo has no Releases). |
| `release_patch` | Patch releases. |
| `commits_ai_trailer` | Commits with an AI co-author trailer. |
| `pr_opened_unknown` | PRs opened by accounts of unknown type (deleted). |
| `pr_merged_unknown` | ...merged. |
| `pr_closed_unmerged_unknown` | ...closed unmerged. |
| `issues_opened` | Issues opened. |
| `pr_self_merged_unreviewed` | Human PRs merged by their own author with no review. |
| `pr_feature_labelled_or_titled` | Merged human PRs labelled or titled as a feature by the team. |
| `release_first` | First version seen in a repo (unclassified). |
| `release_backport` | Version at or below the highest so far (unclassified). |
| `commits_ai_agent` | Commits by AI-agent accounts. |
| `pr_opened_ai_agent` | PRs opened by AI-agent accounts (Copilot agent, Devin, ...). |
| `pr_closed_unmerged_ai_agent` | ...closed unmerged. |
| `pr_merged_ai_agent` | ...merged. |
| `release_major` | Releases whose version increases the major number. |
| `active_contributors_dpg` | People active in the quarter (commit, merged PR or review), de-duplicated across the DPG's repos; bots excluded. |
| `core_team_dpg` | Core contributors: active in at least 2 of the 3 months (D39). Primary team measure. |
| `dev_months_dpg` | Sum over people of months active in the quarter. |
| `maintainers_dpg` | People who merged or reviewed PRs. |
| `core_team_dpg_nopr` | Core contributors counting commits only (no PR/review activity). |
| `dev_months_dpg_nopr` | Developer-months, commits only. |
| `authors_dpg` | People authoring commits or PRs. |
| `reviewers_dpg` | People submitting PR reviews. |
| `mergers_dpg` | People merging PRs. |
| `review_coverage` | Share of merged human PRs reviewed before merge. |
| `self_merge_unreviewed` | Share of merged human PRs self-merged without review. |
| `core_team_dpg_allrepos` | Core contributors counting all repos of the DPG, not just the cohort. |
| `established_start_dpg` | Established contributors (active in >=4 of the previous 8 quarters) at the start of the quarter. |
| `departures_dpg` | Established contributors whose last active quarter is this one and who stay silent for 2+ quarters. |
| `departure_rate_dpg` | departures / established_start. |
| `departures_censored` | True if the departure test cannot be completed (too close to the end of the data). |
| `history_complete` | True if the DPG's cohort history covers the whole quarter. |
| `n_repos_cohort` | Cohort repos of the DPG. |
| `n_cohort_via_migration_rule` | Of them, included by the >=50 pre-2024 commits rule (D45). |
| `n_repos_all` | All high-confidence repos of the DPG. |
| `partial_quarter` | True for 2026Q4 (collection stopped on 29 Oct 2026). Dropped in all analyses. |
| `any_renamed_repo` | True if any repo was renamed/moved. |
| `dpg_confidence` | DPG confidence tier (high / medium / low / no_usable_repo). |

## dpg_repo_map.csv

DPG-to-repo map from the registry (01).
240 rows, 67 KB.

| column | meaning |
|---|---|
| `dpgid` | DPG identifier from the registry (GID...). Join key across files. |
| `dpg` | DPG name as listed in the registry. |
| `categories` | Registry categories. |
| `sectors` | Registry sectors. |
| `sdgs` | Registry SDGs (HTML entities left as in the source). |
| `orgs` | Registry organisations field (equals the DPG name, NOT the legal owner). |
| `host` | github / github_org / gitlab. |
| `repo_label` | Label given in the registry. |
| `raw_url` | URL as given in the registry. |
| `full_name` | GitHub repository as owner/name (after following renames). Public project identifier. |
| `full_name_lc` | full_name lower-cased. |

## dpg_status.csv

Active/slowing/dormant per DPG (03b).
347 rows, 25 KB.

| column | meaning |
|---|---|
| `dpgid` | DPG identifier from the registry (GID...). Join key across files. |
| `dpg` | DPG name as listed in the registry. |
| `repo_set` | high or high+medium repos used for the DPG status. |
| `status` | active / slowing / dormant (D32), or filed / not yet filed / not found for Form 990 rows. |
| `n_repos` | Number of repos attributed to the DPG. |
| `n_active` | Repos active. |
| `n_slowing` | Repos slowing. |
| `n_dormant` | Repos dormant. |
| `last_event_date` | Date of the last merged PR or release in the DPG. |
| `check_move` | True if a dormant DPG has a renamed repo (may have moved). |
| `bot_only` | True if the DPG is dormant except for bot merges. |

## dpgs_without_code_repo.csv

DPGs with no code repository (01).
54 rows, 13 KB.

| column | meaning |
|---|---|
| `dpgid` | DPG identifier from the registry (GID...). Join key across files. |
| `dpg` | DPG name as listed in the registry. |
| `categories` | Registry categories. |
| `sectors` | Registry sectors. |
| `sdgs` | Registry SDGs (HTML entities left as in the source). |
| `orgs` | Registry organisations field (equals the DPG name, NOT the legal owner). |
| `repos_raw` | Registry repository entries for a DPG without a code repo (public URLs). |

## exposed_dpgs_case_list.csv

The 12 exposed DPGs (08d).
12 rows, 5 KB.

| column | meaning |
|---|---|
| `dpg` | DPG name as listed in the registry. |
| `owner` | Owner organisation of the exposed DPG. |
| `owner_type` | USNP = US nonprofit filing a 990; NP non-US nonprofit; CO company; GOV government; UN UN body; MDB development bank; UNIV university; COMM community project; UNKNOWN. |
| `owner_country` | Owner's country (ISO code). |
| `exposure_score` | US foreign-aid exposure of the owner: 3 prime award, 2 sub-award, 1 other federal money, 0 none (DESIGN part B). |
| `in_joint_sample` | True if the DPG is in the event-study sample. |
| `repo_confidence` | Repo confidence of the DPG. |
| `n_prime` | Prime awards matched. |
| `n_sub` | Sub-awards matched. |
| `face_value_usd` | Face value of the matched awards (USD). |
| `main_awards` | Largest award ids. |
| `terminated_2025` | 'yes: <award ids>' if an award is on the (unofficial) 6 Mar 2025 termination list; 'no match' otherwise. |
| `check_purchase_order_only` | True if the only evidence is a purchase order (weak). |

## funding_flags.csv

US foreign-aid exposure per DPG (08b).
256 rows, 42 KB.

| column | meaning |
|---|---|
| `dpgid` | DPG identifier from the registry (GID...). Join key across files. |
| `dpg` | DPG name as listed in the registry. |
| `owner_name` | Owner organisation (hand-curated). An organisation, not a person. |
| `owner_confidence` | Owner-map confidence. |
| `exposure_score` | US foreign-aid exposure of the owner: 3 prime award, 2 sub-award, 1 other federal money, 0 none (DESIGN part B). |
| `exposed` | 1 if exposure_score is 2 or 3, 0 if not, blank if the DPG is not in the exposure sample. |
| `exposure_score_sens` | Same, sensitivity definition (looser owner matching). |
| `exposed_sens` | Exposed flag, sensitivity definition. |
| `n_fa_prime` | Foreign-aid prime awards. |
| `n_fa_subaward` | Foreign-aid sub-awards. |
| `n_other_federal` | Other federal awards. |
| `fa_usd_window_unprorated` | Foreign-aid USD in the window (not prorated). |
| `n_fa_prime_sens` | Same, sensitivity. |
| `n_fa_subaward_sens` | Same, sensitivity. |
| `fa_usd_window_unprorated_sens` | Same, sensitivity. |
| `evidence` | Award or match evidence (organisation:type:award id; or match method). |
| `check_purchase_order_only` | True if the only evidence is a purchase order (weak). |
| `attribution_basis` | Why the awards are attributed to the DPG. |
| `zero_reason` | Why exposure is zero. |
| `in_primary` | In the primary exposure sample. |

## org_990_panel.csv

Form 990 panel per EIN-year (09_990_panel.py); see org_990_panel_codebook.md.
247 rows, 47 KB.

| column | meaning |
|---|---|
| `owner_name` | Owner organisation (hand-curated). An organisation, not a person. |
| `ein` | US Employer Identification Number of the owner. |
| `attribution` | direct / partial / parent / host. |
| `ein_confidence` | Confidence of the owner-to-EIN match. |
| `fiscal_year` | Fiscal year of the filing. |
| `tax_period` | Tax period end. |
| `form_type` | 990 / 990-EZ / 990-PF. |
| `status` | active / slowing / dormant (D32), or filed / not yet filed / not found for Form 990 rows. |
| `source` | Where the match came from: title or body of the PR (ai_feature_prs); listed_repo or org_enumerated (all_repos). |
| `filing_date` | Filing date. |
| `total_revenue` | Total revenue (USD). |
| `contributions_grants` | Contributions and grants (USD). |
| `government_grants` | Government grants, Part VIII line 1e (USD). |
| `gov_grants_tag_present` | True if the e-file carried that line. |
| `total_expenses` | Total functional expenses (USD). |
| `salaries_comp` | Salaries and compensation (USD). |
| `employees` | Number of employees, Part I line 5. |
| `employees_calendar_year` | Calendar year the employee count refers to. |
| `foreign_employees` | Employees outside the US, where reported. |
| `volunteers` | Number of volunteers. |
| `net_assets_eoy` | Net assets at year end (USD). |
| `n_returns` | Returns found for the year. |
| `object_id` | IRS e-file object id. |
| `pdf_url` | ProPublica PDF link. |
| `notes` | Free-text notes of the curator (no personal data). |

## org_ein_map.csv

HAND-CURATED owner-to-EIN map with confidence (05).
39 rows, 6 KB.

| column | meaning |
|---|---|
| `owner_name` | Owner organisation (hand-curated). An organisation, not a person. |
| `ein` | US Employer Identification Number of the owner. |
| `irs_name` | Name on IRS records. |
| `city` | City. |
| `state` | State. |
| `attribution` | How much of the filer is the DPG: direct / partial (whole org, DPG is one product) / parent / host. |
| `confidence` | Repo confidence tier (METHODOLOGY D14): high / medium / low / excluded. |
| `evidence` | Award or match evidence (organisation:type:award id; or match method). |
| `notes` | Free-text notes of the curator (no personal data). |
| `reviewed` | Human review flag of the hand-curated map (blank until reviewed). |

## people_quarterly.csv

Person-DPG-quarter activity with hashed ids (03_aggregate.py).
47,448 rows, 2,630 KB.

| column | meaning |
|---|---|
| `dpgid` | DPG identifier from the registry (GID...). Join key across files. |
| `quarter` | Calendar quarter, e.g. 2025Q3. |
| `person_id` | Hashed person id (stable within this release; not reversible without the original login list). |
| `months_active` | Months active in the quarter (1-3). |
| `roles` | | separated: commit, pr_author, merge, review. |
| `core` | True if months_active >= 2. |

## pr_level.csv

One row per merged PR in a high-confidence repo, derived from the raw cache by 99_build_release.py. No text, logins or e-mails.
276,525 rows, 24,211 KB.

| column | meaning |
|---|---|
| `full_name` | GitHub repository as owner/name (after following renames). Public project identifier. |
| `dpgid` | DPG identifier from the registry (GID...). Join key across files. |
| `created_date` | PR creation date. |
| `merged_date` | PR merge date. |
| `actor_class` | Author class used for review analysis: human, ai_agent, dep_bot, unknown (deleted account). |
| `text_class` | Author class used for disclosure analysis: human, ai_agent, bot. |
| `review_class` | human_reviewed / ai_only / automation_only / unreviewed (blank unless human-authored, merged 2020+). |
| `reviews_capped` | True if the PR has >= 10 stored reviews (collector keeps the first 10). |
| `ai_disclosure_claude` | True if title/body names Claude after the negation filter (D15d). |

## pr_text_ai_precision.csv

Hand-check verdicts of the AI-disclosure precision gate (no text).
179 rows, 3 KB.

| column | meaning |
|---|---|
| `id` | Row id. |
| `group` | Keyword group of the hand-checked match (claude, copilot, ...). |
| `round` | Precision-check round (1 before, 2 after the negation fix). |
| `verdict` | 1 = the matched text says AI helped write the change, 0 = false positive. |

## qgis_template_check.csv

Evidence for the QGIS template claim (counts and a boolean only).
1 rows, 0 KB.

| column | meaning |
|---|---|
| `n_qgis_lines_removed_by_negation_filter` | QGIS template lines removed by the negation filter (D15d). |
| `qgis_template_text_in_cached_pr_body` | True if the QGIS template wording about evaluating LLM/AI use appears in a cached QGIS PR body. |
| `n_qgis_prs_with_that_text` | Number of such PRs. |

## registry_dpgs.csv

Registry extract without contact details.
256 rows, 16 KB.

| column | meaning |
|---|---|
| `dpgid` | DPG identifier from the registry (GID...). Join key across files. |
| `name` | Name. |
| `stage` | Registry stage (all DPG). |
| `website` | Website. |
| `n_listed_repositories` | Repositories listed in the registry. |

## release_notes_ai.csv

Releases whose notes name an AI feature (03g); context text removed.
165 rows, 12 KB.

| column | meaning |
|---|---|
| `dpgid` | DPG identifier from the registry (GID...). Join key across files. |
| `dpg` | DPG name as listed in the registry. |
| `full_name` | GitHub repository as owner/name (after following renames). Public project identifier. |
| `tag` | Release tag or name. |
| `published_at` | Release publication date. |
| `term` | The matched keyword. |

## repo_quarterly.csv

Repo-quarter panel (03_aggregate.py).
4,323 rows, 1,231 KB.

| column | meaning |
|---|---|
| `full_name` | GitHub repository as owner/name (after following renames). Public project identifier. |
| `quarter` | Calendar quarter, e.g. 2025Q3. |
| `pr_opened_human` | PRs opened by human authors. |
| `pr_merged_human` | PRs merged that were authored by humans. |
| `lines_changed` | Additions + deletions of merged human PRs (context only; AI inflates it). |
| `pr_reviewed_before_merge` | Merged human PRs with a review by someone other than the author before merge. |
| `pr_closed_unmerged_human` | Human PRs closed without merge. |
| `pr_opened_dep_bot` | PRs opened by dependency/automation bots (Dependabot, Renovate, github-actions, ...). |
| `pr_merged_dep_bot` | ...merged. |
| `pr_closed_unmerged_dep_bot` | ...closed unmerged. |
| `issues_closed` | Issues closed. |
| `commits_dep_bot` | Commits by dependency bots. |
| `commits_human` | Commits by humans. |
| `pr_median_merge_hours` | Median hours from open to merge. |
| `top1_commit_share` | Share of commits by the top committer. |
| `top2_commit_share` | Share by the top two. |
| `active_contributors` | Repo-level active contributors. |
| `core_team` | Repo-level core contributors. |
| `dev_months` | Repo-level developer-months. |
| `maintainers` | Repo-level maintainers. |
| `release_method` | releases (GitHub Releases) or tags (fallback). |
| `repo_created` | Repo creation date. |
| `in_cohort` | In the fixed cohort (D21/D45). |
| `cohort_via_migration_rule` | In the cohort by the migration rule. |
| `partial_quarter` | True for 2026Q4 (collection stopped on 29 Oct 2026). Dropped in all analyses. |
| `renamed` | Repo was renamed/moved. |
| `repo_archived` | Repo archived. |
| `repo_is_fork` | Repo is a fork. |
| `n_dpgs_for_repo` | DPGs sharing this repo. |
| `release_minor` | Releases whose version increases the minor number. |
| `release_total` | All releases (GitHub Releases, or tags if a repo has no Releases). |
| `release_patch` | Patch releases. |
| `commits_ai_trailer` | Commits with an AI co-author trailer. |
| `pr_opened_unknown` | PRs opened by accounts of unknown type (deleted). |
| `pr_merged_unknown` | ...merged. |
| `pr_closed_unmerged_unknown` | ...closed unmerged. |
| `issues_opened` | Issues opened. |
| `pr_self_merged_unreviewed` | Human PRs merged by their own author with no review. |
| `pr_feature_labelled_or_titled` | Merged human PRs labelled or titled as a feature by the team. |
| `release_first` | First version seen in a repo (unclassified). |
| `release_backport` | Version at or below the highest so far (unclassified). |
| `commits_ai_agent` | Commits by AI-agent accounts. |
| `pr_opened_ai_agent` | PRs opened by AI-agent accounts (Copilot agent, Devin, ...). |
| `pr_closed_unmerged_ai_agent` | ...closed unmerged. |
| `pr_merged_ai_agent` | ...merged. |
| `release_major` | Releases whose version increases the major number. |
| `dpgid` | DPG identifier from the registry (GID...). Join key across files. |
| `dpg` | DPG name as listed in the registry. |
| `confidence` | Repo confidence tier (METHODOLOGY D14): high / medium / low / excluded. |

## repo_status.csv

Active/slowing/dormant per repo (03b).
278 rows, 27 KB.

| column | meaning |
|---|---|
| `full_name` | GitHub repository as owner/name (after following renames). Public project identifier. |
| `status` | active / slowing / dormant (D32). |
| `status_incl_prerelease` | Status if pre-releases were counted (sensitivity). |
| `events_last12` | Events in the last 12 months. |
| `events_prior12` | Events in the 12 months before. |
| `last_event_date` | Date of the last merged PR or release. |
| `dormant_since` | Date dormancy began. |
| `human_commits_12m` | Human commits in the last 12 months. |
| `dep_bot_merges_12m` | Bot merges in the last 12 months. |
| `bot_only_flag` | True if recent activity is bots only. |
| `archived` | Archived on GitHub. |
| `renamed` | Repo was renamed/moved. |
| `pushed_at` | Date of the last push. |
| `release_method` | releases (GitHub Releases) or tags (fallback). |

## review_bots_by_year.csv

Top non-human reviewer accounts per year (bots/AI agents), from the raw cache.
35 rows, 1 KB.

| column | meaning |
|---|---|
| `year` | Calendar year. |
| `reviewer_login` | Login of a non-human reviewer account (bots/AI agents only; no people). |
| `reviews` | Reviews submitted by that account that year. |
