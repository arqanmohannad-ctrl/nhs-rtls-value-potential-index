"""Download configured official snapshots and write a checksum manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "config" / "sources.json")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    raw = ROOT / "data" / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    records = []
    session = requests.Session()
    session.headers["User-Agent"] = "Academic RVPI pipeline/1.0"
    for source in config["sources"]:
        target = raw / source["filename"]
        if args.force or not target.exists():
            response = session.get(source["url"], timeout=120)
            response.raise_for_status()
            target.write_bytes(response.content)
        payload = target.read_bytes()
        records.append({
            "name": source["name"], "filename": target.name, "url": source["url"],
            "landing_page": source.get("landing_page", ""), "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        })
    (raw / "manifest.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(f"Prepared {len(records)} source snapshots in {raw}")


if __name__ == "__main__":
    main()

