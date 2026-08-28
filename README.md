# NHS RTLS Value Potential Index (RVPI)

A reproducible Python project for identifying NHS trusts whose observable operational conditions suggest greater **Real-Time Location System (RTLS) value potential**. The repository demonstrates applied healthcare analytics, health-economic prioritisation, exact organisation-code linkage, composite-index construction, sensitivity analysis, and reproducible reporting.

## Why this project matters

Hospitals face pressure from high bed occupancy, emergency demand, treatment backlogs, estates constraints, and limited capacity. RTLS may support asset tracking, patient-flow coordination, equipment availability, and workflow redesign, but public data do not identify which NHS trusts have adopted RTLS or how it was implemented.

This project therefore does not estimate treatment effects or financial returns. It builds an ex-ante **potential-value prioritisation** index that helps identify settings where local RTLS workflow assessment may be most worthwhile.

## Objectives

- Integrate official NHS England provider-level operational and estates data using exact ODS organisation codes.
- Construct six transparent operational-pressure indicators.
- Build the equal-weight RTLS Value Potential Index (RVPI).
- Define a publication-facing primary sample of comparable general acute trusts.
- Compare primary-sample results with a full-provider sensitivity analysis.
- Test ranking robustness under three prespecified alternative specifications.
- Produce reproducible tables, figures, rankings, merge audits, and validation reports.

## Health-economic and managerial relevance

RVPI supports the allocation of scarce diagnostic, implementation-planning, and business-case resources before technology procurement. A higher score indicates stronger observable conditions for further investigation; it does **not** mean that a trust is a poor performer or that RTLS will deliver savings.

The index is not a causal estimate of RTLS impact, realised savings, avoided cost, implementation feasibility, or return on investment.

## Data sources and freeze

The locked analysis uses publicly available, aggregate provider-level data:

| Domain | Official source | Pinned period |
|---|---|---|
| Beds | [NHS England KH03 overnight bed availability and occupancy](https://www.england.nhs.uk/statistics/statistical-work-areas/bed-availability-and-occupancy/bed-data-overnight/) | Q4 2025–26 |
| Emergency care | [NHS England A&E attendances and emergency admissions](https://www.england.nhs.uk/statistics/statistical-work-areas/ae-waiting-times-and-activity/ae-attendances-and-emergency-admissions-2025-26/) | Revised March 2026 |
| Waiting times | [NHS England provider RTT incomplete pathways](https://www.england.nhs.uk/statistics/statistical-work-areas/rtt-waiting-times/rtt-data-2025-26/) | Revised March 2026 full extract |
| Estates | [NHS England Digital ERIC](https://digital.nhs.uk/data-and-information/publications/statistical/estates-returns-information-collection/summary-page-and-dataset-for-eric-2024-25) | 2024–25 |

The successful live run was frozen on **15 August 2026**. Exact URLs, file sizes, retrieval timestamps, and SHA-256 checksums are recorded in `config/sources.json` and `data/raw/manifest.json`.

Raw source binaries are not redistributed. The collection script retrieves them from the pinned official URLs, and `data/raw/manifest.json` supplies the expected sizes and checksums. This avoids republishing source-file metadata while preserving verifiability. See `data/README.md` for attribution and reuse terms.

## Analytical method

The six RVPI components are:

1. General & Acute bed occupancy pressure.
2. A&E four-hour delay burden.
3. Emergency admissions intensity per available bed.
4. Referral-to-treatment waiting-list burden.
5. Estates backlog burden per occupied floor area.
6. A&E activity relative to available bed capacity.

Each component is oriented so that higher values represent greater operational pressure. Components are standardised within the relevant analysis sample using population z-scores. Baseline RVPI is the unweighted mean of available component z-scores, requiring at least four of six components.

The primary sample contains general acute providers with General & Acute available beds greater than zero, A&E attendances greater than zero, and at least four available components. Exact ERIC trust types define general acute status. Names are never used for fuzzy linkage; ODS codes are the linkage key.

K-means clusters are exploratory descriptions of multivariate operating conditions. They are not validated intervention groups.

Full definitions are provided in `documentation/methodology.md` and `documentation/data_dictionary.md`.

## Repository structure

```text
config/                 pinned source definitions and explicit code crosswalk
data/raw/               source acquisition/checksum manifest; downloads ignored
data/intermediate/      cleaned canonical provider-level source tables
data/final/             primary and full-provider analytical datasets
outputs/figures/        final RVPI distributions and exploratory clusters
outputs/tables/         statistics, rankings, correlations, and audit outputs
scripts/                collection, cleaning, analysis, reporting, orchestration
tests/                  unit tests for core transformations
documentation/          methods, sources, dictionary, limitations, validation
```

## Reproduce the locked analysis

Python 3.11 or later is recommended.

```bash
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pytest -q
```

Download the pinned official snapshots, then reproduce the locked analysis:

```bash
python scripts/collect_data.py
python scripts/clean_sources.py
python scripts/build_rvpi.py
python scripts/generate_manuscript_tables.py
python scripts/robustness_audit.py
```

`robustness_audit.py` stops if a downloaded source or locked primary result checksum differs from the audit freeze.

To intentionally overwrite local raw files with a fresh retrieval from the pinned official URLs:

```bash
python scripts/run_pipeline.py --mode live --force-download
```

Treat a changed upstream file as a new analysis version. Do not silently replace the frozen manuscript inputs.

For software-only verification with fictional providers:

```bash
python scripts/run_pipeline.py --mode demo
```

The demo is deterministic synthetic data and is not NHS evidence. Run it in a disposable clone because it overwrites generated intermediate and output files.

## Key verified findings

- Full provider spine: **207** organisations.
- Primary general acute-trust sample: **114** trusts.
- Reportable primary RVPI scores: **114**.
- Empirical top decile: **12** trusts.
- Mean General & Acute bed occupancy: **93.07%**.
- Mean A&E delay burden: **25.80%**.
- Primary versus full-provider rank correlation: **Spearman 0.879**; median absolute rank change **7.5** places.
- Exploratory clusters were unstable across the primary and full-provider populations (adjusted Rand index **0.000**).

Robustness ranking correlations with the baseline were 0.8866 when estates burden was excluded, 0.8997 with percentile-rank components, and 0.9999 in the six-component complete-case analysis.

These are descriptive potential-value prioritisation findings, not estimates of causal RTLS effects or ROI.

## Limitations

The design is ecological and cross-sectional at trust level. It does not observe RTLS adoption, implementation quality, workflow suitability, local costs, staff time, asset loss, or patient-level outcomes. ERIC is one year behind the other source periods. Provider boundaries and published schemas may change. Equal weighting is transparent but normative, and correlated pressure components may partly overlap. See `documentation/limitations.md`.

## Project status

**Unpublished project; manuscript prepared for journal submission.** This repository contains the reproducible analytical package, not the manuscript, journal correspondence, or submission documents. Initial repository visibility should remain **private** until submission status and the journal's repository and prior-dissemination requirements have been confirmed.

## Researcher

Dr. Mohannad Mahmoud Alarqan

## Recommended citation

Alarqan, M. M. (2026). *NHS RTLS Value Potential Index (RVPI): Reproducible Python pipeline* (Version 1.0.0) [Computer software].

Machine-readable citation metadata are available in `CITATION.cff`.

## Licence

Project code and original documentation are released under the MIT License. NHS England source data retain their original rights and Open Government Licence conditions; no NHS endorsement is implied.
