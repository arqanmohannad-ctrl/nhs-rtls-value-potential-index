# Data sources

## Frozen analytical periods

| Source | File in repository | Analytical fields | Period |
|---|---|---|---|
| NHS England KH03 overnight beds | `data/raw/beds_q4_2025_26.xlsx` | Organisation code/name; General & Acute available and occupied beds | Q4 2025–26 |
| NHS England monthly A&E | `data/raw/ae_march_2026.csv` | Attendances, attendances within four hours, emergency admissions | Revised March 2026 |
| NHS England provider RTT | `data/raw/rtt_march_2026_revised.zip` | Incomplete pathways and pathways over 18 weeks | Revised March 2026 full extract |
| NHS England Digital ERIC site data | `data/raw/eric_site_2024_25.csv` | Trust type, occupied floor area, backlog maintenance cost | 2024–25 |

## Official landing pages

- KH03: https://www.england.nhs.uk/statistics/statistical-work-areas/bed-availability-and-occupancy/bed-data-overnight/
- A&E: https://www.england.nhs.uk/statistics/statistical-work-areas/ae-waiting-times-and-activity/ae-attendances-and-emergency-admissions-2025-26/
- RTT: https://www.england.nhs.uk/statistics/statistical-work-areas/rtt-waiting-times/rtt-data-2025-26/
- ERIC: https://digital.nhs.uk/data-and-information/publications/statistical/estates-returns-information-collection/summary-page-and-dataset-for-eric-2024-25

Direct URLs are pinned in `config/sources.json`; source checksums are in `data/raw/manifest.json`. Raw source binaries are downloaded by `scripts/collect_data.py` and are not redistributed in the repository package.

## Linkage and temporal alignment

ODS organisation code is the only record-linkage key. The optional `config/trust_crosswalk.csv` accepts explicit, dated code mappings; fuzzy matching is not used. Names are retained for description, deterministic provider classification fallback, and discrepancy review.

KH03, A&E, and provider RTT refer to 2025–26. ERIC 2024–25 is the latest preceding estates release used in the locked analysis, creating a documented one-year lag.

## Reuse

These official datasets are third-party content. See `data/README.md` for NHS attribution and reuse terms. The repository contains no NHS logos and does not imply NHS endorsement.
