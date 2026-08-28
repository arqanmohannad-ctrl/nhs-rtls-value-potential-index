"""Run the frozen-manuscript RVPI robustness and audit-lock checks.

This script reads the already-built primary acute-trust dataset. It does not
modify the baseline RVPI formula, primary data, manuscript Tables 1--4, or any
main result. All identity checks and comparisons use exact ODS organisation
codes; no fuzzy name matching is performed.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PRIMARY_PATH = ROOT / "data" / "final" / "rvpi_primary_acute_trusts.csv"
TABLES = ROOT / "outputs" / "tables"
RAW = ROOT / "data" / "raw"

COMPONENTS = [
    "bed_occupancy_pressure",
    "ae_delay_burden",
    "emergency_admissions_intensity",
    "waiting_list_burden",
    "estates_burden",
    "resource_capacity_strain",
]

FREEZE_DATE = "2026-08-15"
PINNED_PERIODS = {
    "beds": "KH03 overnight beds, Q4 2025-26",
    "ae": "Monthly A&E, revised March 2026",
    "rtt": "Provider incomplete RTT pathways, revised March 2026",
    "eric": "ERIC site data, 2024-25",
}

# These hashes lock the NHS source bytes used in the live manuscript run.
SOURCE_LOCKS = {
    "beds": ("beds_q4_2025_26.xlsx", "6be516436644adbff1f3f3ead64df1c33e62bfc5559daeb7fc4a7eeafad845e7"),
    "ae": ("ae_march_2026.csv", "5a6557670b5eb8d2f2999cecec9e61fca334d2e555ab5dc35461dc3fe44d5058"),
    "rtt": ("rtt_march_2026_revised.zip", "87f8ead7be83f5c63fafac1cd441909b7306b7625aeda2dcf019ec949118fa80"),
    "eric": ("eric_site_2024_25.csv", "a9b6798fd6bc57aaf810164f575d4ac914ee313834cdfa87cabbe05f23dfe84f"),
}

# Baseline input and publication Tables 1--4 are intentionally immutable for
# this audit. A mismatch stops the robustness run rather than silently changing
# the manuscript results.
LOCKED_OUTPUT_HASHES = {
    "data/final/rvpi_primary_acute_trusts.csv": "113ee9cc13cd0b6483e03a7f520177c9731892f7d210fda5292282d972269c2e",
    "outputs/tables/manuscript_table_1_data_sources_indicators.csv": "79926667a4233bd1fca76e124948a5b31bc3dc556e52ddb595f12c50370600c7",
    "outputs/tables/manuscript_table_2_primary_sample_flow.csv": "cb78fa87bab94a403b4107818531887ba89317efa6e8af29a5d41dba9f6bafda",
    "outputs/tables/manuscript_table_3_descriptive_statistics.csv": "3c675db8f51393f9c2ee4259d6a710d7b67ebc59b4df193ee58bd276b6f5bacf",
    "outputs/tables/manuscript_table_4_top_decile_rvpi.csv": "ba57a654a52d63c35d2de5b415c325b6dd141cbffadccddf8ef03a36383dc726",
}

# Manually reviewed ODS-code/name pairs for the locked baseline top decile.
# Names are confirmation fields only; selection and identity use exact ODS code.
TOP_DECILE_REVIEW = {
    "RXQ": "BUCKINGHAMSHIRE HEALTHCARE NHS TRUST",
    "RCB": "YORK AND SCARBOROUGH TEACHING HOSPITALS NHS FOUNDATION TRUST",
    "RCF": "AIREDALE NHS FOUNDATION TRUST",
    "RCX": "THE QUEEN ELIZABETH HOSPITAL KING'S LYNN NHS FOUNDATION TRUST",
    "RAJ": "MID AND SOUTH ESSEX NHS FOUNDATION TRUST",
    "R1K": "LONDON NORTH WEST UNIVERSITY HEALTHCARE NHS TRUST",
    "RAX": "KINGSTON HOSPITAL NHS FOUNDATION TRUST",
    "RA9": "TORBAY AND SOUTH DEVON NHS FOUNDATION TRUST",
    "RD1": "ROYAL UNITED HOSPITALS BATH NHS FOUNDATION TRUST",
    "RJ6": "CROYDON HEALTH SERVICES NHS TRUST",
    "RYR": "UNIVERSITY HOSPITALS SUSSEX NHS FOUNDATION TRUST",
    "RYJ": "IMPERIAL COLLEGE HEALTHCARE NHS TRUST",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def zscore(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    sd = values.std(ddof=0)
    if not sd or not np.isfinite(sd):
        return pd.Series(0.0, index=values.index)
    return (values - values.mean()) / sd


def score_z(data: pd.DataFrame, components: list[str], minimum_available: int) -> pd.DataFrame:
    scored = pd.DataFrame(index=data.index)
    for component in components:
        scored[f"{component}_z"] = zscore(data[component])
    z_columns = list(scored.columns)
    scored["components_available"] = scored[z_columns].notna().sum(axis=1)
    scored["score"] = scored[z_columns].mean(axis=1, skipna=True)
    scored.loc[scored.components_available < minimum_available, "score"] = np.nan
    scored["rank"] = scored.score.rank(ascending=False, method="min").astype("Int64")
    return scored


def score_percentiles(data: pd.DataFrame, minimum_available: int = 4) -> pd.DataFrame:
    scored = pd.DataFrame(index=data.index)
    for component in COMPONENTS:
        scored[f"{component}_pct"] = (
            pd.to_numeric(data[component], errors="coerce").rank(pct=True, method="average") * 100
        )
    percentile_columns = list(scored.columns)
    scored["components_available"] = scored[percentile_columns].notna().sum(axis=1)
    scored["score"] = scored[percentile_columns].mean(axis=1, skipna=True)
    scored.loc[scored.components_available < minimum_available, "score"] = np.nan
    scored["rank"] = scored.score.rank(ascending=False, method="min").astype("Int64")
    return scored


def audit_freeze() -> dict:
    manifest = json.loads((RAW / "manifest.json").read_text(encoding="utf-8"))
    manifest_by_name = {item["name"]: item for item in manifest}
    source_audit = {}
    for name, (filename, expected_hash) in SOURCE_LOCKS.items():
        item = manifest_by_name.get(name)
        if item is None or item.get("filename") != filename or item.get("sha256") != expected_hash:
            raise RuntimeError(f"Pinned manifest metadata changed for {name}")
        observed_hash = sha256(RAW / filename)
        if observed_hash != expected_hash:
            raise RuntimeError(f"Raw source checksum mismatch for {filename}")
        source_audit[name] = {
            "filename": filename,
            "sha256": expected_hash,
            "retrieved_utc": item["retrieved_utc"],
            "period": PINNED_PERIODS[name],
        }

    locked_outputs = {}
    for relative_path, expected_hash in LOCKED_OUTPUT_HASHES.items():
        observed_hash = sha256(ROOT / relative_path)
        if observed_hash != expected_hash:
            raise RuntimeError(f"Audit lock failed for {relative_path}")
        locked_outputs[relative_path] = observed_hash
    return {"sources": source_audit, "locked_outputs": locked_outputs}


def comparison_row(
    label: str,
    specification: str,
    eligibility_rule: str,
    baseline: pd.DataFrame,
    alternative: pd.DataFrame,
) -> dict:
    paired = baseline[["trust_code", "baseline_rank"]].merge(
        alternative[["trust_code", "robustness_rank"]],
        on="trust_code",
        how="inner",
        validate="one_to_one",
    ).dropna(subset=["baseline_rank", "robustness_rank"])
    paired["absolute_rank_movement"] = (
        paired.baseline_rank.astype(int) - paired.robustness_rank.astype(int)
    ).abs()

    baseline_top_n = math.ceil(baseline.baseline_rank.notna().sum() * 0.10)
    robustness_top_n = math.ceil(alternative.robustness_rank.notna().sum() * 0.10)
    baseline_top = set(baseline.loc[baseline.baseline_rank.le(baseline_top_n), "trust_code"])
    robustness_top = set(alternative.loc[alternative.robustness_rank.le(robustness_top_n), "trust_code"])
    overlap = len(baseline_top & robustness_top)
    return {
        "robustness_check": label,
        "specification": specification,
        "eligibility_rule": eligibility_rule,
        "analysis_n": int(alternative.robustness_rank.notna().sum()),
        "baseline_overlap_n": int(len(paired)),
        "spearman_correlation_with_baseline": paired.baseline_rank.corr(
            paired.robustness_rank, method="spearman"
        ),
        "median_absolute_rank_movement": paired.absolute_rank_movement.median(),
        "baseline_top_decile_n": baseline_top_n,
        "robustness_top_decile_n": robustness_top_n,
        "top_decile_overlap_n": overlap,
        "top_decile_overlap_percent": 100 * overlap / baseline_top_n,
    }


def build_robustness_outputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    primary = pd.read_csv(PRIMARY_PATH, dtype={"trust_code": str})
    if len(primary) != 114 or primary.trust_code.duplicated().any():
        raise RuntimeError("The locked baseline must contain 114 unique ODS trust codes")
    primary["trust_code"] = primary.trust_code.str.strip().str.upper()

    # Independently reconstruct the baseline from the six raw components to
    # confirm that the frozen input still implements the published formula.
    baseline_check = score_z(primary, COMPONENTS, minimum_available=4)
    if not np.allclose(baseline_check.score, primary.rvpi_z, rtol=0, atol=1e-12, equal_nan=True):
        raise RuntimeError("Baseline RVPI values do not reproduce from the six frozen components")
    if not baseline_check["rank"].equals(primary.rvpi_rank.astype("Int64")):
        raise RuntimeError("Baseline RVPI ranks do not reproduce from the frozen components")

    baseline = primary[["trust_code", "trust_name", "rvpi_z", "rvpi_rank"]].rename(
        columns={"rvpi_z": "baseline_score", "rvpi_rank": "baseline_rank"}
    )

    # A: remove estates, retain the frozen primary sample, standardise the five
    # remaining components within that sample, and require at least four of five.
    no_estates_components = [component for component in COMPONENTS if component != "estates_burden"]
    no_estates = score_z(primary, no_estates_components, minimum_available=4)
    no_estates = pd.concat([primary[["trust_code"]], no_estates[["score", "rank"]]], axis=1).rename(
        columns={"score": "robustness_score", "rank": "robustness_rank"}
    )

    # B: replace component z-scores with within-primary-sample percentile ranks;
    # equal weights and the four-of-six reporting threshold are unchanged.
    percentiles = score_percentiles(primary, minimum_available=4)
    percentiles = pd.concat([primary[["trust_code"]], percentiles[["score", "rank"]]], axis=1).rename(
        columns={"score": "robustness_score", "rank": "robustness_rank"}
    )

    # C: use only all-six-component complete cases and restandardise every
    # component inside that complete-case population before equal-weight scoring.
    complete_mask = primary[COMPONENTS].notna().all(axis=1)
    complete_primary = primary.loc[complete_mask].copy()
    complete_scores = score_z(complete_primary, COMPONENTS, minimum_available=6)
    complete_case = pd.concat(
        [complete_primary[["trust_code"]], complete_scores[["score", "rank"]]], axis=1
    ).rename(columns={"score": "robustness_score", "rank": "robustness_rank"})

    specifications = [
        (
            "A_excluding_estates_burden",
            "Equal-weight mean of five within-primary-sample component z-scores; estates_burden excluded",
            "Frozen primary sample; at least 4 of 5 non-estates components",
            no_estates,
        ),
        (
            "B_percentile_rank_components",
            "Equal-weight mean of six within-primary-sample component percentile ranks",
            "Frozen primary sample; at least 4 of 6 components",
            percentiles,
        ),
        (
            "C_complete_case_six_components",
            "Equal-weight mean of six component z-scores restandardised in the complete-case sample",
            "All six components observed",
            complete_case,
        ),
    ]

    summary_rows = [
        comparison_row(label, specification, eligibility, baseline, alternative)
        for label, specification, eligibility, alternative in specifications
    ]
    summary = pd.DataFrame(summary_rows)
    summary["spearman_correlation_with_baseline"] = summary[
        "spearman_correlation_with_baseline"
    ].round(6)
    summary["median_absolute_rank_movement"] = summary[
        "median_absolute_rank_movement"
    ].round(1)
    summary["top_decile_overlap_percent"] = summary["top_decile_overlap_percent"].round(1)

    comparison = baseline.copy()
    for prefix, alternative in (
        ("no_estates", no_estates),
        ("percentile", percentiles),
        ("complete_case", complete_case),
    ):
        renamed = alternative.rename(columns={
            "robustness_score": f"{prefix}_score",
            "robustness_rank": f"{prefix}_rank",
        })
        comparison = comparison.merge(renamed, on="trust_code", how="left", validate="one_to_one")
        comparison[f"{prefix}_rank_movement"] = comparison[f"{prefix}_rank"] - comparison.baseline_rank
    baseline_top_n = math.ceil(len(baseline) * 0.10)
    comparison["baseline_top_decile_flag"] = comparison.baseline_rank.le(baseline_top_n)
    for prefix in ("no_estates", "percentile", "complete_case"):
        n = int(comparison[f"{prefix}_rank"].notna().sum())
        comparison[f"{prefix}_top_decile_flag"] = comparison[f"{prefix}_rank"].le(math.ceil(n * 0.10))
    comparison = comparison.sort_values("baseline_rank")

    locked_top = comparison.loc[comparison.baseline_top_decile_flag].copy()
    observed = dict(zip(locked_top.trust_code, locked_top.trust_name))
    if observed != TOP_DECILE_REVIEW:
        raise RuntimeError("Baseline top-decile ODS-code/name list differs from the manual audit lock")
    manual_review = locked_top[[
        "trust_code", "trust_name", "baseline_rank", "baseline_score"
    ]].copy()
    manual_review["baseline_score"] = manual_review.baseline_score.round(6)
    manual_review.insert(0, "manual_review_flag", "FLAGGED_FOR_FINAL_REVIEW")
    manual_review["identity_check"] = "Exact ODS-code match; trust name manually verified"
    manual_review["fuzzy_matching_used"] = False

    return summary, comparison, manual_review


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    freeze_audit = audit_freeze()
    summary, comparison, manual_review = build_robustness_outputs()

    summary.to_csv(TABLES / "robustness_summary.csv", index=False)
    comparison.to_csv(TABLES / "robustness_rank_comparison.csv", index=False)
    manual_review.to_csv(TABLES / "top_decile_manual_review.csv", index=False)

    audit_manifest = {
        "audit_status": "locked_and_verified",
        "live_run_date": FREEZE_DATE,
        "pinned_periods": PINNED_PERIODS,
        **freeze_audit,
        "generated_outputs": {
            "robustness_summary.csv": sha256(TABLES / "robustness_summary.csv"),
            "robustness_rank_comparison.csv": sha256(TABLES / "robustness_rank_comparison.csv"),
            "top_decile_manual_review.csv": sha256(TABLES / "top_decile_manual_review.csv"),
        },
        "linkage": "Exact ODS organisation code; no fuzzy joins",
        "interpretation": "RVPI supports RTLS value potential and potential-value prioritisation; it is not a causal RTLS effect or ROI estimate.",
    }
    (TABLES / "audit_lock_manifest.json").write_text(
        json.dumps(audit_manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(summary.to_string(index=False))
    print(f"Flagged {len(manual_review)} baseline top-decile trusts for exact-ODS manual review")


if __name__ == "__main__":
    main()
