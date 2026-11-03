#!/usr/bin/env python3
"""Check, prepare, or launch the offline three-contribution defense demo."""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.defense_demo import (
    DEFAULT_BUNDLE,
    audit_demo_evidence,
    build_demo_bundle,
    validate_demo_bundle,
)


def _dependency_errors() -> list[str]:
    return [
        name
        for name in ("streamlit", "plotly", "pandas", "numpy")
        if importlib.util.find_spec(name) is None
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Validate and exit.")
    parser.add_argument(
        "--audit-evidence",
        action="store_true",
        help="Recompute headline metrics from lower-level artifacts and exit.",
    )
    parser.add_argument(
        "--audit-details",
        action="store_true",
        help="Include every recomputed metric in the evidence-audit output.",
    )
    parser.add_argument(
        "--rebuild", action="store_true", help="Rebuild the compact bundle first."
    )
    parser.add_argument("--port", type=int, default=8501)
    parser.add_argument("--address", default="127.0.0.1")
    parser.add_argument(
        "--show-browser",
        action="store_true",
        help="Let Streamlit open the browser automatically.",
    )
    args = parser.parse_args()

    bundle = REPO_ROOT / DEFAULT_BUNDLE
    if args.rebuild or not bundle.is_file():
        build_demo_bundle(REPO_ROOT, bundle)

    missing = _dependency_errors()
    report = validate_demo_bundle(REPO_ROOT, bundle, verify_source_hashes=True)
    report["missing_dependencies"] = missing
    report["ok"] = report["ok"] and not missing
    if args.audit_evidence and report["ok"]:
        audit = audit_demo_evidence(REPO_ROOT, bundle)
        if args.audit_details:
            output = audit
        else:
            output = {key: value for key, value in audit.items() if key != "checks"}
            output["failed_checks"] = [
                item["name"] for item in audit["checks"] if not item["passed"]
            ]
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0 if audit["ok"] else 2
    if args.check or not report["ok"]:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["ok"] else 2

    app = REPO_ROOT / "dashboard" / "defense_contributions_demo.py"
    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app),
        "--server.address",
        args.address,
        "--server.port",
        str(args.port),
        "--server.headless",
        "false" if args.show_browser else "true",
        "--browser.gatherUsageStats",
        "false",
    ]
    print(f"Demo: http://{args.address}:{args.port}")
    print("Mode: offline measured-artifact replay; press Ctrl+C to stop.")
    process = subprocess.Popen(command, cwd=REPO_ROOT)
    try:
        return process.wait()
    except KeyboardInterrupt:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
