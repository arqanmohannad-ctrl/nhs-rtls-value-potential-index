"""Build the trust-level RTLS Value Potential Index from canonical clean inputs.

RVPI ranks observable operational pressure; it does not estimate adoption effects,
causal impacts, cash-releasing savings, or return on investment.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Headless, workspace-local plotting makes runs deterministic on servers/CI.
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "data" / "intermediate" / ".matplotlib"))
# A single deterministic worker also avoids platform-specific physical-core
# discovery warnings in restricted research/CI environments.
os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler

INPUTS = ROOT / "data" / "intermediate"
FINAL = ROOT / "data" / "final"
TABLES = ROOT / "outputs" / "tables"
FIGURES = ROOT / "outputs" / "figures"
COMPONENTS = ["bed_occupancy_pressure", "ae_delay_burden", "emergency_admissions_intensity",
              "waiting_list_burden", "estates_burden", "resource_capacity_strain"]
GENERAL_ACUTE_TYPES = {
    "ACUTE - LARGE", "ACUTE - MEDIUM", "ACUTE - MULTI-SERVICE",
    "ACUTE - SMALL", "ACUTE - TEACHING",
}


def norm_name(value: object) -> str:
    text = re.sub(r"[^A-Z0-9 ]+", " ", str(value).upper())
    text = re.sub(r"\b(NHS|FOUNDATION|TRUST|THE)\b", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def read_input(name: str) -> pd.DataFrame:
    path = INPUTS / f"{name}_clean.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}. Run clean_sources.py or generate_demo_data.py.")
    frame = pd.read_csv(path)
    frame["trust_code"] = frame["trust_code"].astype(str).str.strip().str.upper()
    crosswalk_path = ROOT / "config" / "trust_crosswalk.csv"
    if crosswalk_path.exists():
        crosswalk = pd.read_csv(crosswalk_path, dtype=str).dropna(subset=["source_trust_code", "canonical_trust_code"])
        crosswalk = crosswalk[crosswalk["source"].isin([name, "*"])]
        if crosswalk.source_trust_code.duplicated().any():
            raise ValueError(f"Ambiguous {name} mappings in {crosswalk_path}")
        mapping = dict(zip(crosswalk.source_trust_code.str.upper(), crosswalk.canonical_trust_code.str.upper()))
        frame["trust_code"] = frame.trust_code.replace(mapping)
    return frame


def zscore(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    sd = s.std(ddof=0)
    return (s - s.mean()) / sd if sd and np.isfinite(sd) else pd.Series(0.0, index=s.index)


def classify_provider(provider_type: object, trust_name: object) -> tuple[str, str]:
    """Classify with exact ERIC categories, with only literal name fallbacks.

    This is deterministic classification, not fuzzy linkage.  The live ERIC
    extract supplies Trust Type for every spine organisation; name rules exist
    only to keep synthetic or legacy inputs explicit rather than silently acute.
    """
    source_type = str(provider_type).strip().upper() if pd.notna(provider_type) else ""
    if source_type in GENERAL_ACUTE_TYPES:
        return "acute_general", "eric_trust_type"
    exact_types = {
        "ACUTE - SPECIALIST": "specialist",
        "MENTAL HEALTH AND LEARNING DISABILITY": "mental_health",
        "COMMUNITY": "community",
        "AMBULANCE": "ambulance",
        "CARE TRUST": "care_trust_non_acute",
    }
    if source_type in exact_types:
        return exact_types[source_type], "eric_trust_type"
    name = str(trust_name).upper()
    literal_rules = [
        (r"\bAMBULANCE\b", "ambulance"),
        (r"\bMENTAL HEALTH\b", "mental_health"),
        (r"\bCOMMUNITY\b", "community"),
        (r"\bSPECIALIST\b", "specialist"),
    ]
    for pattern, group in literal_rules:
        if re.search(pattern, name):
            return group, "organisation_name_literal_keyword"
    return "unknown_or_other", "unclassified"


def assemble_inputs() -> tuple[pd.DataFrame, list[dict], pd.DataFrame]:
    org = read_input("organisations")[["trust_code", "trust_name"]].drop_duplicates("trust_code")
    data = org.copy()
    audits = []
    name_audits = []
    for source in ("beds", "ae", "rtt", "eric"):
        frame = read_input(source)
        dup = int(frame.duplicated("trust_code").sum())
        if dup:
            raise ValueError(f"{source} has {dup} duplicate trust codes; aggregate before building")
        if "trust_name" in frame:
            check = org.merge(frame[["trust_code", "trust_name"]], on="trust_code", how="inner", suffixes=("_master", "_source"))
            check["name_agrees_after_normalisation"] = check.trust_name_master.map(norm_name) == check.trust_name_source.map(norm_name)
            check.insert(0, "source", source)
            name_audits.append(check.loc[~check.name_agrees_after_normalisation])
        before = len(data)
        data = data.merge(frame.drop(columns=["trust_name"], errors="ignore"), on="trust_code", how="left", validate="one_to_one")
        audits.append({"source": source, "master_trusts": before, "matched": int(data[frame.columns.difference(['trust_code','trust_name'])].notna().any(axis=1).sum())})

    numeric = ["available_beds", "occupied_beds", "ae_attendances", "ae_within_4h", "emergency_admissions",
               "rtt_total_waiting", "rtt_over_18_weeks", "backlog_maintenance_cost", "floor_area_m2"]
    data[numeric] = data[numeric].apply(pd.to_numeric, errors="coerce")
    classifications = data.apply(
        lambda row: classify_provider(row.get("provider_type_source"), row["trust_name"]), axis=1
    )
    data[["provider_group", "provider_type_inference_source"]] = pd.DataFrame(
        classifications.tolist(), index=data.index
    )
    data["is_acute_general"] = data.provider_group.eq("acute_general")
    for group in ("specialist", "mental_health", "community", "ambulance"):
        data[f"flag_{group}"] = data.provider_group.eq(group)
    data["flag_non_acute"] = ~data.is_acute_general

    # These six constructions are identical in primary and sensitivity analyses.
    data["bed_occupancy_pressure"] = data.occupied_beds / data.available_beds
    data["ae_delay_burden"] = 1 - data.ae_within_4h / data.ae_attendances
    data["emergency_admissions_intensity"] = data.emergency_admissions / data.available_beds
    data["waiting_list_burden"] = data.rtt_over_18_weeks / data.rtt_total_waiting
    data["estates_burden"] = data.backlog_maintenance_cost / data.floor_area_m2
    # Capacity strain captures throughput relative to staffed/available bed stock.
    data["resource_capacity_strain"] = data.ae_attendances / data.available_beds
    data.replace([np.inf, -np.inf], np.nan, inplace=True)
    data["raw_components_available"] = data[COMPONENTS].notna().sum(axis=1)
    name_audit = pd.concat(name_audits, ignore_index=True) if name_audits else pd.DataFrame()
    return data, audits, name_audit


def score_sample(data: pd.DataFrame, sample_name: str) -> tuple[pd.DataFrame, dict]:
    """Standardise and score within one declared analysis population."""
    data = data.copy()
    data["rvpi_standardisation_sample"] = sample_name

    for col in COMPONENTS:
        data[f"{col}_z"] = zscore(data[col])
        data[f"{col}_pct"] = data[col].rank(pct=True, method="average") * 100
    zcols = [f"{c}_z" for c in COMPONENTS]
    data["components_available"] = data[zcols].notna().sum(axis=1)
    data["rvpi_z"] = data[zcols].mean(axis=1, skipna=True)
    data.loc[data.components_available < 4, "rvpi_z"] = np.nan
    data["rvpi_percentile"] = data.rvpi_z.rank(pct=True, method="average") * 100
    data["rvpi_rank"] = data.rvpi_z.rank(ascending=False, method="min").astype("Int64")

    complete = data[zcols].dropna()
    data["cluster"] = pd.Series(pd.NA, index=data.index, dtype="Int64")
    cluster_meta = {"sample": sample_name, "performed": False, "reason": "insufficient complete cases"}
    if len(complete) >= 12:
        x = StandardScaler().fit_transform(complete)
        candidates = range(2, min(6, len(complete) - 1))
        scores = {}
        for k in candidates:
            labels = KMeans(n_clusters=k, random_state=42, n_init=20).fit_predict(x)
            scores[k] = silhouette_score(x, labels)
        best_k = max(scores, key=scores.get)
        labels = KMeans(n_clusters=best_k, random_state=42, n_init=20).fit_predict(x)
        # Stable label order: 1 is the cluster with the lowest mean RVPI pressure.
        means = pd.Series(data.loc[complete.index, "rvpi_z"].to_numpy()).groupby(labels).mean()
        mapping = {old: new + 1 for new, old in enumerate(means.sort_values().index)}
        data.loc[complete.index, "cluster"] = pd.Series(labels, index=complete.index).map(mapping).astype("Int64")
        cluster_meta = {"sample": sample_name, "performed": True, "k": int(best_k),
                        "complete_cases": int(len(complete)),
                        "silhouette_scores": {str(k): float(v) for k, v in scores.items()},
                        "interpretation": "Exploratory descriptive grouping; not validated RTLS treatment segments."}
    return data, cluster_meta


def sample_flow(data: pd.DataFrame) -> pd.DataFrame:
    """Create a transparent, sequential primary-sample flow with overlap counts."""
    remaining = pd.Series(True, index=data.index)
    rows = [{"step": "full_provider_spine", "criterion": "All trusts in beds/ERIC spine",
             "overall_flag_count": len(data), "sequential_excluded": 0, "remaining": len(data)}]
    rules = [
        ("exclude_non_general_acute_type", data.is_acute_general, (~data.is_acute_general).sum()),
        ("exclude_missing_general_acute_beds", data.available_beds.notna(), data.available_beds.isna().sum()),
        ("exclude_zero_or_negative_general_acute_beds", data.available_beds.gt(0), data.available_beds.le(0).sum()),
        ("exclude_missing_ae_activity", data.ae_attendances.notna(), data.ae_attendances.isna().sum()),
        ("exclude_zero_or_negative_ae_activity", data.ae_attendances.gt(0), data.ae_attendances.le(0).sum()),
        ("exclude_fewer_than_four_components", data.raw_components_available.ge(4), data.raw_components_available.lt(4).sum()),
    ]
    descriptions = {
        "exclude_non_general_acute_type": "ERIC Trust Type is not a general acute category",
        "exclude_missing_general_acute_beds": "General & Acute available beds is missing",
        "exclude_zero_or_negative_general_acute_beds": "General & Acute available beds <= 0",
        "exclude_missing_ae_activity": "A&E attendances is missing",
        "exclude_zero_or_negative_ae_activity": "A&E attendances <= 0",
        "exclude_fewer_than_four_components": "Fewer than four of six raw components available",
    }
    for step, keep, overall in rules:
        excluded = int((remaining & ~keep).sum())
        remaining &= keep
        rows.append({"step": step, "criterion": descriptions[step], "overall_flag_count": int(overall),
                     "sequential_excluded": excluded, "remaining": int(remaining.sum())})
    rows.append({"step": "primary_acute_trust_sample", "criterion": "All primary inclusion criteria met",
                 "overall_flag_count": int(remaining.sum()), "sequential_excluded": 0,
                 "remaining": int(remaining.sum())})
    return pd.DataFrame(rows)


def sensitivity_comparison(primary: pd.DataFrame, full: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    full_fields = full[["trust_code", "rvpi_rank", "rvpi_z", "rvpi_percentile", "cluster"]].rename(columns={
        "rvpi_rank": "full_rvpi_rank", "rvpi_z": "full_rvpi_z",
        "rvpi_percentile": "full_rvpi_percentile", "cluster": "full_cluster",
    })
    comparison = primary[["trust_code", "trust_name", "rvpi_rank", "rvpi_z", "rvpi_percentile", "cluster"]].rename(columns={
        "rvpi_rank": "primary_rvpi_rank", "rvpi_z": "primary_rvpi_z",
        "rvpi_percentile": "primary_rvpi_percentile", "cluster": "primary_cluster",
    }).merge(full_fields, on="trust_code", how="left", validate="one_to_one")
    comparison["rank_change_primary_minus_full"] = comparison.primary_rvpi_rank - comparison.full_rvpi_rank
    comparison["absolute_rank_change"] = comparison.rank_change_primary_minus_full.abs()
    comparison["percentile_change_primary_minus_full"] = comparison.primary_rvpi_percentile - comparison.full_rvpi_percentile
    comparison["ordered_cluster_label_agrees"] = (
        comparison.primary_cluster.notna() & comparison.full_cluster.notna()
        & comparison.primary_cluster.eq(comparison.full_cluster)
    )
    paired_ranks = comparison.dropna(subset=["primary_rvpi_rank", "full_rvpi_rank"])
    clustered = comparison.dropna(subset=["primary_cluster", "full_cluster"])
    statistics = {
        "rank_overlap_n": int(len(paired_ranks)),
        "spearman_rank_correlation": float(paired_ranks.primary_rvpi_rank.corr(paired_ranks.full_rvpi_rank, method="spearman")),
        "median_absolute_rank_change": float(paired_ranks.absolute_rank_change.median()),
        "cluster_overlap_n": int(len(clustered)),
        "adjusted_rand_index": float(adjusted_rand_score(clustered.full_cluster, clustered.primary_cluster)) if len(clustered) else None,
        "ordered_cluster_label_agreement": float(clustered.ordered_cluster_label_agrees.mean()) if len(clustered) else None,
    }
    return comparison.sort_values("primary_rvpi_rank"), statistics


def missingness_table(full: pd.DataFrame, primary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for sample_name, frame in (("full_provider_sensitivity", full), ("primary_acute_trusts", primary)):
        for component in COMPONENTS:
            missing = int(frame[component].isna().sum())
            rows.append({"sample": sample_name, "component": component, "total_n": len(frame),
                         "observed_n": len(frame) - missing, "missing_n": missing,
                         "missing_percent": 100 * missing / len(frame) if len(frame) else np.nan})
    return pd.DataFrame(rows)


def markdown_table(frame: pd.DataFrame) -> str:
    values = frame.astype(object).where(pd.notna(frame), "")
    header = "| " + " | ".join(map(str, values.columns)) + " |"
    divider = "|" + "|".join(["---"] * len(values.columns)) + "|"
    body = ["| " + " | ".join(str(value) for value in row) + " |" for row in values.itertuples(index=False, name=None)]
    return "\n".join([header, divider, *body])


def write_validation_report(full: pd.DataFrame, primary: pd.DataFrame, flow: pd.DataFrame,
                            missingness: pd.DataFrame, comparison_stats: dict,
                            full_cluster: dict, primary_cluster: dict) -> None:
    top = primary.sort_values("rvpi_rank")[["rvpi_rank", "trust_code", "trust_name", "rvpi_z", "rvpi_percentile"]].head(10).copy()
    top[["rvpi_z", "rvpi_percentile"]] = top[["rvpi_z", "rvpi_percentile"]].round(3)
    report = f"""# RVPI validation report

Generated by `scripts/build_rvpi.py` from the pinned source snapshots.

## Sample counts

- Full provider spine: {len(full)}
- Zero General & Acute available beds (full spine, overlaps allowed): {int(full.available_beds.eq(0).sum())}
- Missing General & Acute available beds: {int(full.available_beds.isna().sum())}
- Zero A&E attendances (full spine, overlaps allowed): {int(full.ae_attendances.eq(0).sum())}
- Missing A&E attendances: {int(full.ae_attendances.isna().sum())}
- Primary acute-trust sample: {len(primary)}
- Reportable RVPI, full-provider sensitivity: {int(full.rvpi_z.notna().sum())}
- Reportable RVPI, primary acute-trust analysis: {int(primary.rvpi_z.notna().sum())}

## Primary sample flow

{markdown_table(flow)}

## Missingness by component

{markdown_table(missingness.round({"missing_percent": 2}))}

## Top 10 primary acute-trust RVPI results

{markdown_table(top)}

## Sensitivity and cluster stability

- Spearman correlation of primary versus full-provider ranks: {comparison_stats['spearman_rank_correlation']:.3f} (n={comparison_stats['rank_overlap_n']}).
- Median absolute rank change: {comparison_stats['median_absolute_rank_change']:.1f} places.
- Full-provider clustering: k={full_cluster.get('k', 'not performed')}; complete cases={full_cluster.get('complete_cases', 0)}.
- Primary clustering: k={primary_cluster.get('k', 'not performed')}; complete cases={primary_cluster.get('complete_cases', 0)}.
- Adjusted Rand Index on overlapping clustered trusts: {comparison_stats['adjusted_rand_index'] if comparison_stats['adjusted_rand_index'] is not None else 'not available'} (n={comparison_stats['cluster_overlap_n']}).

The selected cluster counts differ between samples and the Adjusted Rand Index indicates that cluster assignments are not stable across populations. Cluster labels are ordered by mean RVPI pressure but remain exploratory. RVPI is a potential-value prioritisation index, not a causal estimate of RTLS impact, cash-releasing savings, or ROI.
"""
    (ROOT / "documentation" / "validation_report.md").write_text(report, encoding="utf-8")


def build() -> dict[str, pd.DataFrame]:
    raw, audits, name_audit = assemble_inputs()
    flow = sample_flow(raw)
    primary_mask = (
        raw.is_acute_general & raw.available_beds.gt(0) & raw.ae_attendances.gt(0)
        & raw.raw_components_available.ge(4)
    )
    raw["primary_acute_eligible"] = primary_mask
    full, full_cluster_meta = score_sample(raw, "full_provider_sensitivity")
    primary, primary_cluster_meta = score_sample(raw.loc[primary_mask], "primary_acute_trusts")
    comparison, comparison_stats = sensitivity_comparison(primary, full)
    missingness = missingness_table(full, primary)

    for directory in (FINAL, TABLES, FIGURES):
        directory.mkdir(parents=True, exist_ok=True)
    full.to_csv(FINAL / "rvpi_full_provider_sensitivity.csv", index=False)
    primary.to_csv(FINAL / "rvpi_primary_acute_trusts.csv", index=False)
    # Backward-compatible alias for users of the initial pipeline release.
    full.to_csv(FINAL / "rvpi_trust_level.csv", index=False)
    pd.DataFrame(audits).to_csv(TABLES / "merge_audit.csv", index=False)
    name_audit.to_csv(TABLES / "name_discrepancy_audit.csv", index=False)
    flow.to_csv(TABLES / "primary_sample_flow.csv", index=False)
    missingness.to_csv(TABLES / "missingness_by_component.csv", index=False)
    comparison.to_csv(TABLES / "sensitivity_comparison.csv", index=False)
    ranking_fields = ["trust_code", "trust_name", "provider_type_source", "rvpi_rank", "rvpi_z",
                      "rvpi_percentile", "cluster", "components_available"]
    primary.sort_values("rvpi_rank")[ranking_fields].to_csv(TABLES / "primary_rvpi_rankings.csv", index=False)
    full.sort_values("rvpi_rank")[ranking_fields].to_csv(TABLES / "rvpi_rankings.csv", index=False)
    full[COMPONENTS + ["rvpi_z", "rvpi_percentile"]].describe().T.to_csv(TABLES / "descriptive_statistics.csv")
    primary[COMPONENTS + ["rvpi_z"]].corr().to_csv(TABLES / "correlation_matrix.csv")
    metadata = {"full_provider_sensitivity": full_cluster_meta, "primary_acute_trusts": primary_cluster_meta,
                "stability": comparison_stats}
    (TABLES / "cluster_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    write_validation_report(full, primary, flow, missingness, comparison_stats,
                            full_cluster_meta, primary_cluster_meta)
    plot_sample(primary, "primary_rvpi_distribution.png", "primary_rvpi_clusters.png",
                "Primary acute-trust")
    plot_sample(full, "rvpi_distribution.png", "rvpi_clusters.png", "Full-provider sensitivity")
    return {"full": full, "primary": primary, "comparison": comparison}

def plot_sample(data: pd.DataFrame, distribution_name: str, cluster_name: str, label: str) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(data.rvpi_z.dropna(), bins="auto", color="#006747", edgecolor="white")
    ax.axvline(0, color="#263238", linestyle="--", linewidth=1)
    ax.set(title=f"{label} RVPI distribution", xlabel="RVPI (mean component z-score)", ylabel="Trusts")
    fig.tight_layout(); fig.savefig(FIGURES / distribution_name, dpi=180); plt.close(fig)

    plot = data.dropna(subset=["bed_occupancy_pressure", "ae_delay_burden", "cluster"])
    fig, ax = plt.subplots(figsize=(8, 6))
    for cluster, group in plot.groupby("cluster"):
        ax.scatter(group.bed_occupancy_pressure * 100, group.ae_delay_burden * 100,
                   s=35 + group.rvpi_percentile.fillna(0), alpha=.75, label=f"Cluster {cluster}")
    ax.set(title=f"{label} exploratory clusters", xlabel="Bed occupancy (%)", ylabel="A&E delay burden (%)")
    ax.legend(title="K-means", fontsize=8); fig.tight_layout()
    fig.savefig(FIGURES / cluster_name, dpi=180); plt.close(fig)


def main() -> None:
    argparse.ArgumentParser(description="Build RVPI from canonical intermediate files").parse_args()
    result = build()
    print(f"Built full-provider sensitivity for {len(result['full'])} trusts; "
          f"primary acute sample has {len(result['primary'])} trusts")


if __name__ == "__main__":
    main()
