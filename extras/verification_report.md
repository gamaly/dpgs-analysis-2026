# Verification report

Generated 2026-10-29 by `verify_numbers.py` from `numbers_ledger.csv` (79 claims) and the five notebooks.

## Summary

| grade | claims |
|---|---|
| exact | 45 |
| rounding | 22 |
| qualitative-yes | 3 |
| external | 9 |

70 of 70 data claims reproduce (45 exact, 22 within rounding, 3 qualitative checks passed). 9 claims are external figures.

*exact* = identical number; *rounding* = identical after rounding to the precision the post shows.

## Claim by claim

| claim | ledger value | reproduced value | match | notebook | note |
|---|---|---|---|---|---|
| N001 | 3 | 3 | yes (exact) | 01_registry_and_sample |  |
| N002 | 5 | - | n/a | - | external, not reproducible from data: https://gregmaly.substack.com/p/what-happens-when-anyone-can-build |
| N003 | 23; 90+ | - | n/a | - | external, not reproducible from data: https://dhis2.org/invest-in-routine-systems/ |
| N009 | 79; 37; 33.3%; 69.7%; 90% | - | n/a | - | external, not reproducible from data: https://dhis2.org/invest-in-routine-systems/ |
| N010 | 10 | - | n/a | - | external, not reproducible from data: https://dhis2.org/norad-hisp-5-year-agreement/ |
| N011 | 133; 86 | - | n/a | - | external, not reproducible from data: https://content.digitalpublicgoods.net/2024-DPG-Ecosystem-Report.pdf |
| N012 | 1 | - | n/a | - | external, not reproducible from data: https://github.com/DPGAlliance/dpg-resources/blob/main/docs/dpg-review-policy.md |
| N013 | 21 | 21 | yes (exact) | 01_registry_and_sample |  |
| N014 | 54 | 54 | yes (exact) | 01_registry_and_sample |  |
| N015 | 12; 9; 3 | 12, 9, 3 | yes (exact) | 05_funding_exposure_and_cuts |  |
| N017 | 166 | 166 | yes (exact) | 01_registry_and_sample |  |
| N018 | 190 | 190, 198 | yes (exact) | 01_registry_and_sample |  |
| N019 | 2020-01-01 to 2026-10-29; 256 | 2020, 1, 1, 2026, 10, 29, 256 | yes (exact) | 01_registry_and_sample |  |
| N020 | 68 | 68 | yes (exact) | 03_ai_features |  |
| N021 | 43 | 43 | yes (exact) | 03_ai_features |  |
| N022 | 8; 13; 8; 16 (2020-2023); 18; 37; 51 | 8, 13, 8, 16, 18, 37, 51, 2020, 2023 | yes (exact) | 03_ai_features |  |
| N023 | 39; 578 | 39, 578 | yes (exact) | 03_ai_features |  |
| N024 | 1 in 88 (1.14%) | 1, 87.5969, 1.14159 | yes (rounding) | 03_ai_features |  |
| N025 | 85.9 | 85.8929 | yes (rounding) | 03_ai_features |  |
| N026 | 6.0 | 6 | yes (exact) | 03_ai_features |  |
| N030 | 196; 1120 | 196, 1120 | yes (exact) | 03_ai_features |  |
| N031 | 1 | 1 | yes (exact) | 03_ai_features |  |
| N032 | nan | True | yes (check) | 03_ai_features | ledger value is not numeric; notebook test = True |
| N033 | 100 | 100 | yes (exact) | 02_teams_and_activity |  |
| N034 | 3141; 5260 | 3141, 5260 | yes (exact) | 02_teams_and_activity |  |
| N035 | 11.0; 14.0 | 11.0284, 13.9968 | yes (rounding) | 02_teams_and_activity |  |
| N036 | 423; 913 | 423, 913 | yes (exact) | 02_teams_and_activity |  |
| N037 | 49; 60; 55; 55 | 49, 60, 55, 55 | yes (exact) | 02_teams_and_activity |  |
| N038 | 61.5; 32.7 | 61.4828, 32.7163 | yes (rounding) | 02_teams_and_activity |  |
| N039 | 8.79; 10.74; 11.05; 14.61; +66% | 8.78501, 10.7393, 11.0465, 14.6055, 66.255 | yes (rounding) | 02_teams_and_activity |  |
| N040 | 7.35; 6.49; 5.63; 5.99 | 7.3467, 6.49227, 5.63033, 5.98951 | yes (rounding) | 02_teams_and_activity |  |
| N041 | 21; 69 | 21, 69 | yes (exact) | 04_review_and_ai_disclosure |  |
| N042 | 54.7 | 54.689 | yes (rounding) | 04_review_and_ai_disclosure |  |
| N043 | 8.15 | 8.1539 | yes (rounding) | 04_review_and_ai_disclosure |  |
| N045 | quote | - | n/a | - | external, not reproducible from data: https://getdx.com/report/state-of-ai-impact-in-engineering-q3-report/ |
| N046 | 43; 17 (106 active = remainder) | 106, 17, 43 | yes (exact) | 01_registry_and_sample |  |
| N047 | 25.9 | 25.9036 | yes (rounding) | 01_registry_and_sample |  |
| N048 | 810.5; 887.5; 844; 857.7 | 810.5, 887.5, 844, 857.667 | yes (rounding) | 02_teams_and_activity |  |
| N049 | 12.5; 24.0 | 12.5, 24 | yes (exact) | 02_teams_and_activity |  |
| N050 | 5; 4 | 5, 4 | yes (exact) | 02_teams_and_activity |  |
| N051 | 52; 3 -> 1.5; 18.75% -> 35.3% | 52, 3, 1.5, 18.75, 35.2564 | yes (rounding) | 02_teams_and_activity |  |
| N052 | 48; 7 -> 6.5; 5.7% -> 11.8% | 48, 7, 6.5, 5.72917, 11.8056 | yes (rounding) | 02_teams_and_activity |  |
| N053 | 9; 5; 3 | 9, 5, 3 | yes (exact) | 02_teams_and_activity |  |
| N054 | 75.3; 74.8; 75.9; 75.0; 68.1 | 75.33, 74.76, 75.87, 74.95, 68.06 | yes (rounding) | 04_review_and_ai_disclosure |  |
| N055 | 24.7; 25.2; 23.9; 21.7; 24.8 | 24.66, 25.2, 23.87, 21.72, 24.75 | yes (rounding) | 04_review_and_ai_disclosure |  |
| N056 | 0.03; 2.7; 6.13 | 0.03, 2.7, 6.13 | yes (exact) | 04_review_and_ai_disclosure |  |
| N057 | 372; 14136 | 372, 14136 | yes (exact) | 04_review_and_ai_disclosure |  |
| N058 | 6; 3250 | 6, 3250 | yes (exact) | 04_review_and_ai_disclosure |  |
| N059 | 93; 23; 50; 20 | 93, 23, 50, 20 | yes (exact) | 04_review_and_ai_disclosure |  |
| N060 | 10 | 10 | yes (exact) | 04_review_and_ai_disclosure |  |
| N061 | 5 of 10 | 5, 10 | yes (exact) | 04_review_and_ai_disclosure |  |
| N062 | 64.4; 27.6 | 64.43, 27.59 | yes (rounding) | 04_review_and_ai_disclosure |  |
| N063 | 17 Apr 2026 | - | n/a | - | external, not reproducible from data: https://www.deeplearning.ai/the-batch/issue-349/ |
| N064 | 27 Feb 2026 | - | n/a | - | external, not reproducible from data: https://www.atlassian.com/blog/ai-at-work/designers-workflow-for-shipping-code |
| N067 | 18.78; 19.36; 17.18; 14.05; 12.52 | 18.78, 19.36, 17.18, 14.05, 12.52 | yes (exact) | 02_teams_and_activity |  |
| N068 | 13.69; 18.3 | 13.69, 18.2533 | yes (rounding) | 02_teams_and_activity |  |
| N069 | 32.8-39.1 | 32.8289, 39.1459 | yes (rounding) | 02_teams_and_activity |  |
| N070 | 24.7; 19.5 | 24.6539, 19.4861 | yes (rounding) | 02_teams_and_activity |  |
| N071 | 8 | 8 | yes (exact) | 05_funding_exposure_and_cuts |  |
| N072 | 7; 2; 0 | 7, 2, 0 | yes (exact) | 05_funding_exposure_and_cuts |  |
| N073 | 7; 5; 0 | 7, 5, 0 | yes (exact) | 05_funding_exposure_and_cuts |  |
| N074 | 4; 2; 0 | 4, 2, 0 | yes (exact) | 05_funding_exposure_and_cuts |  |
| N075 | 5; 2; 1; 3-4; 2 | 5, 2, 1, 3, 4, 2 | yes (exact) | 05_funding_exposure_and_cuts |  |
| N076 | 0 | 0 | yes (exact) | 05_funding_exposure_and_cuts |  |
| N077 | 27; 15 | 27, 15 | yes (exact) | 05_funding_exposure_and_cuts |  |
| N078 | 9-13; 7-10; 6 | 9, 13, 7, 10, 6 | yes (exact) | 05_funding_exposure_and_cuts |  |
| N079 | 8-19 (mean 14.4) | 8, 19, 14.3636 | yes (rounding) | 05_funding_exposure_and_cuts |  |
| N080 | 9.18 -> 5.52 (-40%); 6.69 -> 6.45 (-4%); 8 vs 136 | 9.17857, 5.51786, 6.69119, 6.44538, -39.8833, -3.67372, 8, 136 | yes (rounding) | 05_funding_exposure_and_cuts |  |
| N081 | 2024Q4 | 2024, 4 | yes (exact) | 05_funding_exposure_and_cuts |  |
| N082 | post-2024Q4 team coefficients -0.05 to 0.20, none significant; pre-trend chi2 7.6 on 3 df, p = 0.054 | 2024, 4, -0.0538632, 0.203641, 7.62584, 3, 0.0544116 | yes (rounding) | 05_funding_exposure_and_cuts | no post-2024Q4 coefficient has /t/ >= 1.5 |
| N083 | none significant | True | yes (check) | 05_funding_exposure_and_cuts | ledger value is not numeric; notebook test = True |
| N084 | 0.41 log points (~33%); 0.76 log points (~53%) | 0.406338, 33.3915, 0.759285, 53.1999 | yes (rounding) | 05_funding_exposure_and_cuts |  |
| N085 | 6; 2024 | 6, 2024, 2024 | yes (exact) | 05_funding_exposure_and_cuts |  |
| N086 | 3; 3 | 3, 3 | yes (exact) | 05_funding_exposure_and_cuts |  |
| N087 | 26; 13 | 26, 13 | yes (exact) | 05_funding_exposure_and_cuts |  |
| N088 | 14; 34 | 14, 34 | yes (exact) | 05_funding_exposure_and_cuts |  |
| N089 | 22 | 22 | yes (exact) | 01_registry_and_sample |  |
| N090 | 24 of 30 (80%) | 24, 30, 80 | yes (exact) | 04_review_and_ai_disclosure |  |
| N091 | nan | 129 | yes (check) | 04_review_and_ai_disclosure | ledger value is not numeric; notebook test = True |

## Notebook claims no longer in the ledger (orphaned, skipped)

- N027 (03_ai_features)
- N028 (03_ai_features)
- N029 (03_ai_features)
