# Form 990 panel: codebook (METHODOLOGY D47, task F9)

Files: `data/org_990_panel_phase1.csv` (six owners of exposed DPGs, built 2026-10-29), `data/org_990_panel.csv` (all EINs in `org_ein_map.csv`, phase 2).
Script: `scripts/09_990_panel.py` (+ `scripts/irs_zip.py`). Raw downloads: `cache/irs_efile/` (index CSVs, zip directories, `xml/<object_id>.xml`).
One row per EIN x fiscal year, FY2019 to FY2025. Descriptive use only (D47); employees describe the whole organisation, not the DPG.

| column | meaning |
|---|---|
| owner_name, ein, attribution, ein_confidence | from `org_ein_map.csv`. `attribution` parent/host means the figures describe a bigger organisation than the DPG owner; do not use in case studies (DESIGN A4) |
| fiscal_year | calendar year in which the tax period ENDS (FYE June 2023 = FY2023) |
| tax_period | YYYYMM of the period end, as filed |
| form_type | 990, 990EZ or 990PF |
| status | `filed`; `not yet filed` (extended due date, 15th of the 11th month after year end, is still ahead of 2026-10-29); `not found` (due date passed, no e-file record and no ProPublica record) |
| source | `irs_efile_xml` (all fields below parsed from the IRS return); `propublica_structured` (revenue, contributions, expenses, salaries, net assets only; employees and government grants blank); `pdf` (a filing exists but only as a ProPublica PDF; all figures blank, to be read by hand); `irs_efile_index_only` (return indexed, XML could not be read) |
| filing_date | date the return was submitted (from the XML header) |
| total_revenue | Part I line 12 (990), line 9 (EZ) |
| contributions_grants | Part I line 8 |
| government_grants | Part VIII line 1e. 990 only. **Zero when the IRS XML omits the line** (e-file omits zero lines); `gov_grants_tag_present` shows which |
| total_expenses | Part I line 18 |
| salaries_comp | Part I line 15 (salaries, other compensation, employee benefits) |
| employees | Part I line 5, number of employees in the US-reported total (990 only; the EZ has no count) |
| foreign_employees | Schedule F total employees outside the US, when the return has Schedule F |
| volunteers | Part I line 6 |
| net_assets_eoy | Part I line 22 (end of year) |
| n_returns | number of returns filed for the same period; the latest (amended) one is used |
| object_id | IRS TEOS object id of the XML used |
| pdf_url | ProPublica PDF for `pdf` rows |
| notes | reason for any blank or fallback |

## Read before using
- **Line 1e is only grants received directly from government.** US federal money that reaches an organisation as a subaward through another organisation is reported as other contributions or as program service revenue, not on line 1e. Medic shows 0 in every year although it is an exposed owner (subaward score 2). Use `funding_flags.csv` for exposure, and this panel only for the organisation's size and totals.
- Employees can swing from one year to the next for reasons that are not layoffs (VillageReach 139 in FY2022, 62 in FY2023). Do not read a single year as a headcount cut.
- `employees` counts what the organisation reports as employees on payroll in the US plus its own definition; it excludes contractors. Foreign staff of US charities are often engaged through local entities and appear in `foreign_employees` only when Schedule F lists them.
- 990 data lag: FY2025 returns of calendar-year filers are not due until 2026-11-15; those rows read `not yet filed` unless already submitted.

## Method notes
- IRS e-file XML comes from the TEOS yearly zips (1 to 4 GB each). They are read member by member with HTTP range requests, so no zip is downloaded whole. 2025-26 zips use Deflate64 compression, decoded with the `inflate64` package.
- A year is never recorded as zero when it is not yet filed or not found.
- ProPublica PDF downloads are blocked to scripts (HTTP 403). `pdf` rows are left blank; they need to be read by hand from a browser.

## Phase 2 result (2026-10-29)
247 rows, 35 EINs: 194 read from IRS XML, 3 indexed but XML not located, 18 PDF-only (to read by hand), 20 not yet filed, 12 not found.
`not found` rows are mostly years before the organisation existed or filed under this EIN (Mojaloop Foundation FY2019, OpenMined FY2019-23, Open Supply Hub FY2019-20, Resolve to Save Lives FY2019-20); OpenMRS Inc FY2022-23 is a real gap to check by hand.
US-nonprofit implementers named in the owner map are not yet included (no EINs matched for them); add on request.


## employees_calendar_year (added 2026-10-29)
`employees` is Form 990 Part I line 5 = Part V line 2a: the number of W-2s for the **calendar year ending with or within the tax year**. So `employees_calendar_year` = the tax-period end year if the period ends in December, otherwise that year minus 1. Example: a fiscal year ending September 2025 (FY2025) reports calendar-2024 employees. W-2 counts include anyone employed at any time in the year, so they are not a point-in-time headcount, and a jump between years can reflect hiring for a project rather than staff size. No filed return in this panel covers calendar 2025 yet (December filers' FY2025 returns are due 2026-11-15).
