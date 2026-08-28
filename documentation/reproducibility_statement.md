# Reproducibility statement

The RVPI manuscript package is frozen to the successful live run of 15 August 2026. Its pinned sources are NHS England KH03 Q4 2025-26, revised March 2026 A&E activity, revised March 2026 provider incomplete RTT pathways, and NHS England Digital ERIC 2024-25. Source URLs and periods are recorded in `config/sources.json`; retrieved file names, UTC timestamps, sizes and SHA-256 checksums are recorded in `data/raw/manifest.json`.

Trust-level linkage uses exact ODS organisation codes. Source-specific predecessor or successor mappings are permitted only through the explicit, dated `config/trust_crosswalk.csv`. Trust names are retained for description, classification fallback and manual identity review; no fuzzy matching or fuzzy joins are used.

The baseline pipeline is run with `.venv\Scripts\python scripts\run_pipeline.py --mode live`. The frozen robustness audit is run separately with `.venv\Scripts\python scripts\robustness_audit.py`. The audit verifies source and baseline-output checksums before calculating the prespecified alternatives and writes `outputs/tables/robustness_summary.csv`, `outputs/tables/robustness_rank_comparison.csv`, `outputs/tables/top_decile_manual_review.csv`, and `outputs/tables/audit_lock_manifest.json`. Manuscript Tables 1-4 and the baseline RVPI formula are not rewritten by this audit.

RVPI is a descriptive index of **RTLS value potential** for **potential-value prioritisation**. It does not estimate a causal effect of RTLS adoption, realised savings, implementation feasibility, or return on investment.
