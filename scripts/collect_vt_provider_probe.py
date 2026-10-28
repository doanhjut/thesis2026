#!/usr/bin/env python3
"""Download one alternate VT HTML report per sample from selected providers."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import pathlib
from collections import Counter

from collect_vt_behaviour_pilot import (
    Collector,
    inspect_report,
    utc_now,
    write_csv,
    write_gzip,
)


PROVIDER_PRIORITY = (
    "VirusTotal Cuckoofork",
    "VenusEye Sandbox",
)


def read_manifest(path: pathlib.Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return {row["sha256"].lower(): row for row in csv.DictReader(handle)}


def choose(items: list[dict]) -> dict | None:
    rank = {name: index for index, name in enumerate(PROVIDER_PRIORITY)}
    candidates = [
        item
        for item in items
        if item.get("attributes", {}).get("has_html_report") is True
        and item.get("attributes", {}).get("sandbox_name") in rank
    ]
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda item: (
            rank[item["attributes"]["sandbox_name"]], item.get("id", "")
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--listings", type=pathlib.Path, required=True)
    parser.add_argument("--manifest", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--requests-per-minute", type=int, default=4)
    args = parser.parse_args()

    api_key = os.environ.get("VT_API_KEY")
    if not api_key:
        raise SystemExit("VT_API_KEY is not set")
    manifest = read_manifest(args.manifest)
    collector = Collector(api_key, args.requests_per_minute)
    args.output.mkdir(parents=True, exist_ok=True)

    audit_rows = []
    quota_exhausted = False
    for listing_path in sorted(args.listings.glob("*.json.gz")):
        sample_sha256 = listing_path.name.removesuffix(".json.gz").lower()
        listing = json.loads(gzip.decompress(listing_path.read_bytes()))
        report = choose(listing.get("data", []))
        if report is None:
            continue
        metadata = manifest[sample_sha256]
        attributes = report.get("attributes", {})
        row = {
            "sample_sha256": sample_sha256,
            "label": int(metadata["label"]),
            "outer_fold": int(metadata["outer_fold"]),
            "behaviour_object_id": report.get("id"),
            "sandbox_name": attributes.get("sandbox_name"),
        }
        status, body, redirect_host = collector.download_html(report["id"])
        row["report_http_status"] = status
        row["redirect_host"] = redirect_host
        if status == 429:
            row["status"] = "deferred_quota"
            audit_rows.append(row)
            quota_exhausted = True
            break
        if status != 200:
            row["status"] = "report_error"
            audit_rows.append(row)
            continue
        write_gzip(
            args.output / "raw_html_reports" / f"{sample_sha256}.html.gz", body
        )
        row.update(inspect_report(body))
        row["status"] = "report_collected"
        audit_rows.append(row)

    write_csv(args.output / "provider_probe_coverage.csv", audit_rows)
    write_csv(args.output / "request_history.csv", collector.history)
    counts = Counter(row["status"] for row in audit_rows)
    summary = {
        "status": "quota_exhausted" if quota_exhausted else "probe_complete",
        "generated_at_utc": utc_now(),
        "binary_downloaded": False,
        "provider_priority": PROVIDER_PRIORITY,
        "attempted_rows": len(audit_rows),
        "status_counts": dict(sorted(counts.items())),
        "label_counts": {
            str(label): sum(row["label"] == label for row in audit_rows)
            for label in (0, 1)
        },
    }
    (args.output / "provider_probe_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 75 if quota_exhausted else 0


if __name__ == "__main__":
    raise SystemExit(main())
