# Reproducibility notes

## Environment

- Recommended Python: 3.11 or later.
- Dependencies are listed in `requirements.txt` with bounded major versions.
- All scripts resolve paths relative to the repository root; no machine-specific paths are used.
- Matplotlib uses a repository-local cache and the non-interactive `Agg` backend.

## Frozen reproduction

The source manifest records the official snapshots used for the 15 August 2026 analytical freeze. Run, in order:

```bash
python -m pytest -q
python scripts/collect_data.py
python scripts/clean_sources.py
python scripts/build_rvpi.py
python scripts/generate_manuscript_tables.py
python scripts/robustness_audit.py
```

The collection step downloads missing source files from the pinned official URLs. The robustness audit checks those files, the primary analytical dataset, and locked Tables 1–4 against SHA-256 hashes before calculating alternative rankings.

## Full orchestration

`python scripts/run_pipeline.py --mode live` uses existing raw files when present and downloads only missing sources. `--force-download` intentionally refreshes every source from the pinned URL. Because upstream files can be revised, a checksum change must be treated as a new version.

`python scripts/run_pipeline.py --mode demo` creates deterministic fictional data using seed `20260815`. It verifies software behaviour only and overwrites generated intermediate and output files, so use a disposable clone.

## Determinism

- Component z-scores use population standard deviations (`ddof=0`).
- K-means uses random state 42 and 20 initialisations.
- Candidate cluster counts are 2–5 and are selected by silhouette score.
- Trust linkage uses exact ODS codes; no fuzzy joins are permitted.

## Expected locked results

- Full provider spine: 207.
- Primary acute-trust sample and reportable RVPI: 114.
- Top decile: 12 trusts.
- Primary versus full-provider Spearman rank correlation: 0.879.
- Robustness Spearman correlations: 0.8866, 0.8997, and 0.9999.

See `documentation/validation_report.md` and `outputs/tables/audit_lock_manifest.json` for machine-readable verification details.
