"""One-command orchestration for demo or downloaded official data."""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(script: str, *args: str) -> None:
    subprocess.run([sys.executable, str(ROOT / "scripts" / script), *args], check=True, cwd=ROOT)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("demo", "live"), default="demo")
    parser.add_argument("--force-download", action="store_true")
    args = parser.parse_args()
    if args.mode == "demo":
        run("generate_demo_data.py")
    else:
        run("collect_data.py", *(["--force"] if args.force_download else []))
        run("clean_sources.py")
    run("build_rvpi.py")


if __name__ == "__main__":
    main()

