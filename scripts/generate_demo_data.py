"""Generate deterministic synthetic canonical inputs for testing; not research evidence."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "intermediate"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20260815)
    n = 40
    codes = [f"R{i:02d}" for i in range(n)]
    org = pd.DataFrame({"trust_code": codes, "trust_name": [f"Synthetic NHS Trust {i+1}" for i in range(n)]})
    available = rng.integers(180, 1050, n)
    occupancy = np.clip(rng.normal(.89, .045, n), .72, .99)
    attend = rng.integers(2500, 16000, n)
    admissions = (attend * rng.uniform(.17, .34, n)).astype(int)
    four_hour = np.clip(rng.normal(.73, .09, n), .45, .94)
    waiting = rng.integers(9000, 120000, n)
    over18 = (waiting * rng.uniform(.28, .62, n)).astype(int)
    backlog = rng.lognormal(17.0, .8, n)
    floor = rng.integers(50000, 420000, n)
    beds = org.assign(available_beds=available, occupied_beds=available * occupancy)
    ae = org.assign(ae_attendances=attend, ae_within_4h=attend * four_hour, emergency_admissions=admissions)
    rtt = org.assign(rtt_total_waiting=waiting, rtt_over_18_weeks=over18)
    eric = org.assign(provider_type_source="ACUTE - LARGE", backlog_maintenance_cost=backlog, floor_area_m2=floor)
    for name, frame in {"organisations": org, "beds": beds, "ae": ae, "rtt": rtt, "eric": eric}.items():
        frame.to_csv(OUT / f"{name}_clean.csv", index=False)
    (OUT / "DEMO_DATA.txt").write_text("Synthetic deterministic data. Never use as empirical NHS results.\n", encoding="utf-8")
    print(f"Wrote deterministic demo inputs for {n} fictional trusts")


if __name__ == "__main__":
    main()
