# Data contents and reuse

This repository contains aggregate, provider-level official statistics. It contains no patient-level, identifiable, confidential, or restricted-access health data.

## Folders

- `raw/`: `manifest.json`, which records the four pinned official URLs, retrieval timestamps, sizes, and SHA-256 checksums. Source binaries are downloaded by `scripts/collect_data.py` and ignored by Git.
- `intermediate/`: cleaned canonical trust-level tables used by the analytical pipeline. This folder is the project's processed-data layer.
- `final/`: the primary acute-trust dataset and full-provider sensitivity dataset.

Raw source binaries are deliberately not redistributed because official files can contain publisher metadata unrelated to the analysis. `collect_data.py` downloads them from NHS England. The large uncompressed RTT pathway-level extract is also not tracked; `clean_sources.py` reads it from the downloaded ZIP and extracts it to an ignored temporary folder when required.

## Source rights and attribution

The project's MIT License does not apply to NHS England source data. NHS England states that its content is reusable under the current Open Government Licence unless otherwise specified. Users must review the source page and current terms before reuse:

- NHS England terms: https://digital.nhs.uk/about-nhs-digital/terms-and-conditions
- Open Government Licence: https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/

Required project attribution:

> Contains information from NHS England, licenced under the current version of the Open Government Licence.

No endorsement by NHS England is implied. Provider names and ODS codes identify public organisations, not individuals.
