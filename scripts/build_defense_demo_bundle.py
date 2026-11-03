#!/usr/bin/env python3
"""Create the compact, measured-artifact bundle used by the defense demo."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.defense_demo import DEFAULT_BUNDLE, build_demo_bundle, validate_demo_bundle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_BUNDLE,
        help="Output JSON path, relative to the repository root by default.",
    )
    args = parser.parse_args()

    output = build_demo_bundle(REPO_ROOT, args.output)
    report = validate_demo_bundle(REPO_ROOT, output, verify_source_hashes=True)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
