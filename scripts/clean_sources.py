"""Convert downloaded NHS publications into explicit canonical CSV contracts.

The cleaners intentionally fail with a column inventory when a publication schema
changes. Update ALIASES after checking the official data dictionary; do not guess.
"""
from __future__ import annotations

import argparse
import re
import zipfile
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "intermediate"

ALIASES = {
    "trust_code": ["org code", "organisation code", "provider code", "provider org code", "trust code"],
    "trust_name": ["org name", "organisation name", "provider name", "trust name"],
    "available_beds": ["total available", "available beds", "average daily number of beds available"],
    "occupied_beds": ["total occupied", "occupied beds", "average daily number of beds occupied"],
    "ae_attendances": ["total attendances", "total a&e attendances", "a&e attendances"],
    "ae_within_4h": ["total attendances < 4 hours", "attendances within 4 hours", "total attendances 4 hours or less"],
    "emergency_admissions": ["total emergency admissions", "emergency admissions"],
    "rtt_total_waiting": ["total", "total incomplete pathways", "total number of incomplete pathways"],
    "rtt_over_18_weeks": ["18+ weeks", "over 18 weeks", "incomplete pathways over 18 weeks"],
    "backlog_maintenance_cost": ["total backlog maintenance", "backlog maintenance cost", "total cost to eradicate backlog"],
    "floor_area_m2": ["occupied floor area", "total occupied floor area", "occupied floor area (m2)"],
}


def key(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()


def read_table(path: Path, sheet_name=0, header=0) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path, encoding_errors="replace", header=header)
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path, sheet_name=sheet_name, header=header)
    raise ValueError(f"Unsupported table: {path}")


def find_header(path: Path, required_tokens=("code", "name"), max_rows=30) -> int:
    """Find the first likely header row in NHS workbooks containing title rows."""
    preview = read_table(path, header=None)
    for i, row in preview.head(max_rows).iterrows():
        cells = " | ".join(key(x) for x in row.dropna())
        if all(token in cells for token in required_tokens):
            return int(i)
    return 0


def canonicalise(frame: pd.DataFrame, required: list[str]) -> pd.DataFrame:
    columns = {key(c): c for c in frame.columns}
    rename = {}
    missing = []
    for target in required:
        match = next((columns[key(alias)] for alias in ALIASES[target] if key(alias) in columns), None)
        if match is None:
            missing.append(target)
        else:
            rename[match] = target
    if missing:
        raise ValueError(f"Missing canonical fields {missing}. Observed columns: {list(frame.columns)}")
    out = frame.rename(columns=rename)[required].copy()
    out["trust_code"] = out.trust_code.astype(str).str.strip().str.upper()
    out["trust_name"] = out.trust_name.astype(str).str.strip()
    out = out[out.trust_code.str.fullmatch(r"[A-Z0-9]{3,5}", na=False)]
    return out


def numeric(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for col in columns:
        frame[col] = pd.to_numeric(frame[col].astype(str).str.replace(",", "", regex=False), errors="coerce")
    return frame


def aggregate(frame: pd.DataFrame, values: list[str]) -> pd.DataFrame:
    return frame.groupby(["trust_code", "trust_name"], as_index=False)[values].sum(min_count=1)


def clean_beds(path: Path) -> pd.DataFrame:
    """Clean the KH03 2025-26 provider-by-sector workbook.

    The workbook has a two-level header.  On ``NHS Trust by Sector`` the first
    metric block is explicitly labelled ``Available`` and the second is
    ``Occupied``; each block then repeats ``Total`` and ``General & Acute``.
    Pandas flattens those repeated names to ``Total``/``Total.1`` and
    ``General & Acute``/``General & Acute.1``.  We use the original group row,
    rather than relying on the generated ``.1`` suffix, to establish meaning.
    General & Acute is preferred for this acute-flow study; Total is the
    documented fallback when that sector is absent from either block.
    """
    sheet = "NHS Trust by Sector"
    with pd.ExcelFile(path) as workbook:
        if sheet not in workbook.sheet_names:
            raise ValueError(f"KH03 provider sheet {sheet!r} not found. Sheets: {workbook.sheet_names}")
        raw = pd.read_excel(workbook, sheet_name=sheet, header=None)

    header_row = find_header_in_frame(raw)
    title_text = " ".join(key(value) for value in raw.iloc[:header_row].to_numpy().ravel() if pd.notna(value))
    required_title_phrases = ("available and occupied beds", "open overnight", "by sector")
    if not all(phrase in title_text for phrase in required_title_phrases):
        raise ValueError(
            "KH03 title check failed; expected a provider-sector table of available and occupied beds open overnight"
        )

    group_row = next(
        (i for i in range(header_row - 1, -1, -1)
         if "available" in {key(v) for v in raw.iloc[i] if pd.notna(v)}
         and "occupied" in {key(v) for v in raw.iloc[i] if pd.notna(v)}),
        None,
    )
    if group_row is None:
        raise ValueError("KH03 two-level header check failed: Available and Occupied groups were not found")

    groups = {key(value): i for i, value in enumerate(raw.iloc[group_row]) if pd.notna(value)}
    available_start, occupied_start = groups["available"], groups["occupied"]
    percent_start = groups.get("occupied", raw.shape[1])
    # ``% Occupied`` normalises to ``occupied`` too, so recover its later position.
    occupied_positions = [i for i, value in enumerate(raw.iloc[group_row]) if key(value) == "occupied"]
    if len(occupied_positions) < 2 or not available_start < occupied_positions[0] < occupied_positions[1]:
        raise ValueError("KH03 group order check failed; expected Available, Occupied, then % Occupied")
    occupied_start, percent_start = occupied_positions[:2]

    headers = [key(value) for value in raw.iloc[header_row]]

    def exact_column(label: str, start: int, end: int) -> int | None:
        return next((i for i in range(start, end) if headers[i] == label), None)

    metric = "general acute"
    available_col = exact_column(metric, available_start, occupied_start)
    occupied_col = exact_column(metric, occupied_start, percent_start)
    if available_col is None or occupied_col is None:
        metric = "total"
        available_col = exact_column(metric, available_start, occupied_start)
        occupied_col = exact_column(metric, occupied_start, percent_start)
    if available_col is None or occupied_col is None:
        raise ValueError("KH03 header check failed: no matching General & Acute or Total pair in both bed groups")

    code_col = exact_column("org code", 0, available_start)
    name_col = exact_column("org name", 0, available_start)
    if code_col is None or name_col is None:
        raise ValueError("KH03 identifier check failed: Org Code and Org Name were not found")

    out = raw.iloc[header_row + 1:, [code_col, name_col, available_col, occupied_col]].copy()
    out.columns = ["trust_code", "trust_name", "available_beds", "occupied_beds"]
    # Filter true blanks before string conversion; otherwise NaN becomes the
    # three-character string "NAN" and can masquerade as an organisation code.
    out = out[out["trust_code"].notna()].copy()
    out["trust_code"] = out.trust_code.astype(str).str.strip().str.upper()
    out["trust_name"] = out.trust_name.astype(str).str.strip()
    out = out[out.trust_code.str.fullmatch(r"[A-Z0-9]{3,5}", na=False)]
    return aggregate(numeric(out, ["available_beds", "occupied_beds"]), ["available_beds", "occupied_beds"])


def find_header_in_frame(frame: pd.DataFrame, max_rows: int = 30) -> int:
    """Locate an exact Org Code/Org Name row without fuzzy matching."""
    for i, row in frame.head(max_rows).iterrows():
        labels = {key(value) for value in row if pd.notna(value)}
        if {"org code", "org name"}.issubset(labels):
            return int(i)
    raise ValueError("Could not locate a KH03 header row containing exact Org Code and Org Name labels")


def clean_ae(path: Path) -> pd.DataFrame:
    frame = read_table(path)
    attendance_cols = [
        "A&E attendances Type 1", "A&E attendances Type 2", "A&E attendances Other A&E Department",
        "A&E attendances Booked Appointments Type 1", "A&E attendances Booked Appointments Type 2",
        "A&E attendances Booked Appointments Other Department",
    ]
    delayed_cols = [
        "Attendances over 4hrs Type 1", "Attendances over 4hrs Type 2",
        "Attendances over 4hrs Other Department", "Attendances over 4hrs Booked Appointments Type 1",
        "Attendances over 4hrs Booked Appointments Type 2",
        "Attendances over 4hrs Booked Appointments Other Department",
    ]
    admission_cols = [
        "Emergency admissions via A&E - Type 1", "Emergency admissions via A&E - Type 2",
        "Emergency admissions via A&E - Other A&E department", "Other emergency admissions",
    ]
    required = ["Org Code", "Org name", *attendance_cols, *delayed_cols, *admission_cols]
    missing = [col for col in required if col not in frame]
    if missing:
        raise ValueError(f"A&E schema missing exact published columns: {missing}")
    frame[attendance_cols + delayed_cols + admission_cols] = frame[attendance_cols + delayed_cols + admission_cols].apply(pd.to_numeric, errors="coerce")
    out = pd.DataFrame({
        "trust_code": frame["Org Code"],
        "trust_name": frame["Org name"],
        # Booked-appointment columns are additional published attendance/delay
        # categories, so all Type 1, Type 2 and Other categories are summed.
        "ae_attendances": frame[attendance_cols].sum(axis=1, min_count=1),
        "ae_within_4h": frame[attendance_cols].sum(axis=1, min_count=1) - frame[delayed_cols].sum(axis=1, min_count=1),
        "emergency_admissions": frame[admission_cols].sum(axis=1, min_count=1),
    })
    out = out[out.trust_code.notna()].copy()
    out["trust_code"] = out.trust_code.astype(str).str.strip().str.upper()
    out["trust_name"] = out.trust_name.astype(str).str.strip()
    out = out[out.trust_code.str.fullmatch(r"[A-Z0-9]{3,5}", na=False) & out.trust_code.ne("TOTAL")]
    return aggregate(out, ["ae_attendances", "ae_within_4h", "emergency_admissions"])


def clean_eric(path: Path) -> pd.DataFrame:
    frame = read_table(path)
    columns = {key(col): col for col in frame.columns}
    code_col = columns.get("trust code")
    name_col = columns.get("trust name")
    type_col = columns.get("trust type")
    floor_col = columns.get("occupied floor area m")
    backlog_keys = [
        "cost to eradicate high risk backlog",
        "cost to eradicate significant risk backlog",
        "cost to eradicate moderate risk backlog",
        "cost to eradicate low risk backlog",
    ]
    backlog_cols = [columns.get(label) for label in backlog_keys]
    if code_col is None or name_col is None or type_col is None or floor_col is None or any(col is None for col in backlog_cols):
        raise ValueError(
            "ERIC site schema missing exact trust identifiers, occupied floor area, or one of the four risk backlog fields"
        )
    measures = frame[[floor_col, *backlog_cols]].apply(
        lambda col: pd.to_numeric(col.astype(str).str.replace(",", "", regex=False), errors="coerce")
    )
    out = pd.DataFrame({
        "trust_code": frame[code_col], "trust_name": frame[name_col],
        "provider_type_source": frame[type_col],
        "floor_area_m2": measures[floor_col],
        # ERIC reports backlog separately for high, significant, moderate and
        # low risk. Their sum is the total cost to eradicate backlog at site.
        "backlog_maintenance_cost": measures[backlog_cols].sum(axis=1, min_count=1),
    })
    out = out[out.trust_code.notna()].copy()
    out["trust_code"] = out.trust_code.astype(str).str.strip().str.upper()
    out["trust_name"] = out.trust_name.astype(str).str.strip()
    out["provider_type_source"] = out.provider_type_source.astype(str).str.strip().str.upper()
    out = out[out.trust_code.str.fullmatch(r"[A-Z0-9]{3,5}", na=False)]
    type_counts = out.groupby("trust_code").provider_type_source.nunique()
    if type_counts.gt(1).any():
        raise ValueError(f"ERIC has conflicting Trust Type values for: {type_counts[type_counts.gt(1)].index.tolist()}")
    return out.groupby(["trust_code", "trust_name", "provider_type_source"], as_index=False)[
        ["backlog_maintenance_cost", "floor_area_m2"]
    ].sum(min_count=1)


def clean_rtt(path: Path) -> pd.DataFrame:
    candidates = []
    if path.suffix.lower() == ".zip":
        extract = OUT / "rtt_extracted"
        extract.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path) as archive:
            safe = [n for n in archive.namelist() if not n.startswith(("/", "\\")) and ".." not in Path(n).parts]
            archive.extractall(extract, members=safe)
        candidates = list(extract.rglob("*.csv"))
    else:
        candidates = [path]
    errors = []
    for candidate in candidates:
        try:
            frame = read_table(candidate)
            required = ["Provider Org Code", "Provider Org Name", "RTT Part Description", "Total All"]
            if not all(col in frame for col in required):
                raise ValueError(f"missing exact full-extract fields: {[c for c in required if c not in frame]}")
            frame = frame[frame["RTT Part Description"].eq("Incomplete Pathways")].copy()
            week_cols = []
            for col in frame.columns:
                match = re.fullmatch(r"Gt (\d+)(?: To \d+)? Weeks SUM 1", str(col))
                if match and int(match.group(1)) >= 18:
                    week_cols.append(col)
            if not week_cols or "Gt 18 To 19 Weeks SUM 1" not in week_cols:
                raise ValueError("could not identify the exact 18+ week incomplete-pathway bands")
            # Provider Parent is the commissioning ICB in this full extract;
            # provider organisation is therefore the required trust-level key.
            code = frame["Provider Org Code"]
            name = frame["Provider Org Name"]
            values = frame[["Total All", *week_cols]].apply(pd.to_numeric, errors="coerce")
            out = pd.DataFrame({
                "trust_code": code, "trust_name": name,
                "rtt_total_waiting": values["Total All"],
                "rtt_over_18_weeks": values[week_cols].sum(axis=1, min_count=1),
            })
            out = out[out.trust_code.notna()].copy()
            out["trust_code"] = out.trust_code.astype(str).str.strip().str.upper()
            out["trust_name"] = out.trust_name.astype(str).str.strip()
            out = out[out.trust_code.str.fullmatch(r"[A-Z0-9]{3,5}", na=False)]
            return aggregate(out, ["rtt_total_waiting", "rtt_over_18_weeks"])
        except (ValueError, KeyError) as exc:
            errors.append(f"{candidate.name}: {exc}")
    raise ValueError("No RTT member matched the provider-incomplete contract. " + " | ".join(errors[:5]))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--beds", type=Path, default=RAW / "beds_q4_2025_26.xlsx")
    parser.add_argument("--ae", type=Path, default=RAW / "ae_march_2026.csv")
    parser.add_argument("--rtt", type=Path, default=RAW / "rtt_march_2026_revised.zip")
    parser.add_argument("--eric", type=Path, default=RAW / "eric_site_2024_25.csv")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    frames = {"beds": clean_beds(args.beds), "ae": clean_ae(args.ae), "rtt": clean_rtt(args.rtt), "eric": clean_eric(args.eric)}
    # Beds and ERIC are NHS trust/provider collections.  Use their union as the
    # organisation spine so independent A&E/RTT organisations cannot enter the
    # trust-level analytical population merely by appearing in activity files.
    org = pd.concat([frames[name][["trust_code", "trust_name"]] for name in ("beds", "eric")]).drop_duplicates("trust_code", keep="last")
    org.to_csv(OUT / "organisations_clean.csv", index=False)
    for name, frame in frames.items():
        frame.to_csv(OUT / f"{name}_clean.csv", index=False)
    print("Wrote canonical inputs:", ", ".join(f"{k}={len(v)}" for k, v in frames.items()))


if __name__ == "__main__":
    main()
