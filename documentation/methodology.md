# Methodological protocol

## Estimand and interpretation

There is no RTLS adoption or implementation dataset in this design. Consequently, RVPI is **not** an estimator of the average treatment effect, a causal impact estimate, or an ROI forecast. It combines observable operational conditions that may make location-aware workflow interventions more valuable. A high score is a hypothesis-generating signal for further operational diagnosis and business-case work.

## Unit, time and linkage

The unit is an NHS provider trust identified primarily by ODS organisation code. Names are descriptive and support only classification fallback or manual review; name-only fuzzy matching is deliberately excluded. Organisational mergers and code changes require an explicit, dated crosswalk before aggregation. KH03, A&E and revised March 2026 RTT are aligned to 2025-26. ERIC 2024-25 supplies provider type and estates fields with a one-year lag.

## Data freeze and audit lock

The manuscript analysis is frozen to the successful live run dated **15 August 2026**. The pinned sources are KH03 Q4 2025-26, revised March 2026 A&E, revised March 2026 provider incomplete RTT pathways, and ERIC 2024-25. Exact retrieval timestamps, URLs, file sizes and SHA-256 checksums are retained in `data/raw/manifest.json`; source-period metadata is retained in `config/sources.json`.

The audit-lock script verifies the raw checksums, the frozen primary analytical dataset, and the exported manuscript Tables 1-4 before calculating robustness results. Failure of any checksum or exact ODS-code/name check terminates the audit. Revised or replacement upstream data therefore require an explicitly versioned rerun and are not incorporated into this manuscript package automatically.

## Primary acute-trust analysis

The primary population is restricted before standardisation. A trust must have exact ERIC `Trust Type` in `ACUTE - LARGE`, `ACUTE - MEDIUM`, `ACUTE - MULTI-SERVICE`, `ACUTE - SMALL`, or `ACUTE - TEACHING`; General & Acute available beds greater than zero; A&E attendances greater than zero; and at least four of six raw components observed. These criteria improve operational comparability for acute-flow RTLS use cases.

`ACUTE - SPECIALIST`, mental-health/learning-disability, community, ambulance, care-trust, and unknown/other providers are excluded from the primary analysis and explicitly flagged in the full dataset. Exact ERIC categories take precedence. Only literal keywords such as “ambulance” or “mental health” are allowed as a fallback when ERIC type is missing; this is classification, not record linkage.

## Full-provider sensitivity analysis

The sensitivity population retains the full union of providers in the KH03 beds and ERIC trust collections. It therefore tests how rankings change when structurally different provider types remain in scope. Z-scores, percentiles, RVPI ranks and clusters are recalculated within each population. The raw indicator formulae, direction and equal weights do not change.

## Prespecified robustness checks

Three additional checks are calculated from the frozen 114-trust primary dataset without altering the baseline RVPI:

1. **Excluding estates burden:** `estates_burden` is omitted and the remaining five components are standardised within the frozen primary sample. The composite is their equal-weight mean, requiring at least four of five components.
2. **Percentile-rank scoring:** each of the six raw components is converted to its within-primary-sample empirical percentile rank. The equal-weight mean is calculated with the baseline requirement of at least four of six components.
3. **Complete-case scoring:** trusts are restricted to observations with all six components. Each component is restandardised within that complete-case population before the equal-weight mean and ranking are calculated.

Each alternative ranking is linked to the baseline only by exact ODS code. Agreement is summarised using Spearman rank correlation and median absolute rank movement among trusts ranked in both specifications. Top-decile overlap is also reported as a review aid. These are specification checks for RTLS value potential and potential-value prioritisation; they are not causal RTLS-effect, realised-savings or ROI analyses.

## Missingness and comparability

A provider receives RVPI only when at least four of six components are observed. Both outputs expose raw and scored component counts. Missing values are not mean-imputed. Zero denominators yield missing ratios. The validation report separates zero from missing beds/A&E values and reports component-level missingness for both populations.

## Clustering

K-means is exploratory. It uses complete, standardised component vectors; candidate `k` values are 2–5 and selection maximises silhouette score. Random state 42 and 20 initialisations are fixed. Primary versus full-provider stability is assessed using the Adjusted Rand Index among trusts clustered in both analyses. Clusters are descriptive patterns, not validated RTLS intervention segments.
