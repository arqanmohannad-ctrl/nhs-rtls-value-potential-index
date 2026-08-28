# Repository audit

Audit date: 28 August 2026

Repository version: 1.0.0

## Audit outcome

The repository package contains the verified RVPI analytical workflow and is reproducible from the pinned official NHS England URLs. No analysis, formula, sample, result, ranking, robustness statistic, or conclusion was changed when the repository package was created.

No essential user-supplied files are missing.

## Included

- All seven analytical and orchestration scripts used for collection, cleaning, integration, RVPI construction, robustness checks, demo generation, and reporting.
- Five unit tests for name normalisation, z-score behaviour, and deterministic provider classification.
- Pinned source URLs and the original source checksum manifest.
- Five cleaned canonical provider-level input tables.
- The 114-trust primary acute dataset and 207-provider sensitivity dataset.
- Final CSV/JSON/text tables, rankings, missingness, correlation, merge, cluster, and audit outputs.
- Four final PNG figures covering primary and full-provider distributions and exploratory clusters.
- Methodology, data dictionary, data sources, limitations, validation, and reproducibility documentation.
- MIT code licence, NHS data attribution, `CITATION.cff`, `.gitignore`, `.gitattributes`, and changelog.

## Excluded

- The submission-ready manuscript, title page, cover letter, supplementary submission document, final submission ZIP, and journal-facing correspondence.
- Raw source binaries. The official KH03 workbook includes publisher identity metadata unrelated to the analysis; all four source files are therefore reacquired from their pinned NHS England URLs instead of being republished.
- The obsolete June 2026 RTT archive and extracted file because the locked analysis uses the revised March 2026 provider incomplete-pathways release.
- Temporary extracted RTT files, plotting caches, render files, virtual environments, Python caches, and test caches.
- `rvpi_trust_level.csv`, which duplicates the full-provider sensitivity dataset under a legacy filename.
- Generated journal-facing DOCX and Markdown table compilations. Their construction script and analytical CSV outputs remain included.

## Executable verification

Validation was performed from isolated copies so generated test outputs could not alter the deliverable.

| Check | Result |
|---|---|
| Unit tests | 5 passed |
| Live orchestration | Passed; four source records prepared |
| Source cleaning | Passed; beds 184, A&E 189, RTT 532, ERIC 207 canonical rows |
| RVPI build | Passed; full spine 207 and primary sample 114 |
| Reporting-table generation | Passed |
| Robustness audit before and after report regeneration | Passed |
| Deterministic demo pipeline | Passed; 40 fictional trusts |
| Locked output comparison | 31 of 31 comparable data, table, JSON, text, and PNG artifacts matched byte-for-byte |
| Python compilation | Passed for all scripts and tests |

The verified robustness results were:

- Excluding estates burden: Spearman 0.8866; median absolute rank movement 8.0; top-decile overlap 8/12.
- Percentile-rank components: Spearman 0.8997; median absolute rank movement 7.0; top-decile overlap 7/12.
- Complete case: Spearman 0.9999; median absolute rank movement 1.0; top-decile overlap 12/12.

## Security and privacy review

- No passwords, API keys, access tokens, private keys, connection strings, personal email addresses, or machine-specific absolute paths were found.
- No patient-level, identifiable individual-level, confidential, or restricted-access health data are included.
- Provider names and ODS codes identify public NHS organisations.
- The intended researcher identity appears only in repository authorship, citation, and licence metadata.
- No manuscript, submission document, reviewer report, or journal correspondence is present.

## Materials still required

None for analytical reproduction. Internet access is required to download the four pinned official source files. If NHS England removes or replaces a pinned URL, the user must retrieve the exact archived file matching `data/raw/manifest.json`; it must not be replaced silently.

The eventual GitHub repository URL is not yet known and should be added to the citation and CV entry after repository creation.

## Publication recommendation

The package is technically safe for public release: it contains aggregate official provider data, intended researcher attribution, no credentials, and no confidential research records. Nevertheless, the configured initial visibility should remain **private** while the manuscript is being prepared or considered for submission. Make it public only after confirming the journal's code/data repository and prior-dissemination policy.

RVPI must continue to be described as RTLS value potential for potential-value prioritisation, not causal impact, realised savings, avoided cost, or ROI.
