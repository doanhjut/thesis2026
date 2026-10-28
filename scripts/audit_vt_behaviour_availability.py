#!/usr/bin/env python3
"""Summarize provider/report availability from cached VT behaviour listings."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import pathlib
from collections import defaultdict
from typing import Any


def read_manifest(path: pathlib.Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return {row["sha256"].lower(): row for row in csv.DictReader(handle)}


def write_csv(path: pathlib.Path, rows: list[dict[str, Any]]) -> None:
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--listings", type=pathlib.Path, required=True)
    parser.add_argument("--manifest", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()

    manifest = read_manifest(args.manifest)
    rows: list[dict[str, Any]] = []
    for path in sorted(args.listings.glob("*.json.gz")):
        sample_sha256 = path.name.removesuffix(".json.gz").lower()
        metadata = manifest[sample_sha256]
        listing = json.loads(gzip.decompress(path.read_bytes()))
        for item in listing.get("data", []):
            attrs = item.get("attributes", {})
            rows.append(
                {
                    "sample_sha256": sample_sha256,
                    "label": int(metadata["label"]),
                    "outer_fold": int(metadata["outer_fold"]),
                    "behaviour_object_id": item.get("id"),
                    "sandbox_name": attrs.get("sandbox_name"),
                    "analysis_date": attrs.get("analysis_date"),
                    "has_html_report": bool(attrs.get("has_html_report")),
                    "has_evtx": bool(attrs.get("has_evtx")),
                    "has_pcap": bool(attrs.get("has_pcap")),
                    "attribute_count": len(attrs),
                    "attribute_keys": "|".join(sorted(attrs)),
                }
            )

    args.output.mkdir(parents=True, exist_ok=True)
    write_csv(args.output / "provider_availability_by_sample.csv", rows)

    providers: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "objects": 0,
            "samples": set(),
            "benign_samples": set(),
            "malware_samples": set(),
            "html_samples": set(),
            "evtx_samples": set(),
            "pcap_samples": set(),
        }
    )
    for row in rows:
        provider = str(row["sandbox_name"])
        bucket = providers[provider]
        sha = row["sample_sha256"]
        bucket["objects"] += 1
        bucket["samples"].add(sha)
        bucket["benign_samples" if row["label"] == 0 else "malware_samples"].add(sha)
        for flag, name in (
            ("has_html_report", "html_samples"),
            ("has_evtx", "evtx_samples"),
            ("has_pcap", "pcap_samples"),
        ):
            if row[flag]:
                bucket[name].add(sha)

    provider_summary = {}
    for provider, bucket in sorted(providers.items()):
        provider_summary[provider] = {
            key: len(value) if isinstance(value, set) else value
            for key, value in bucket.items()
        }

    sample_flags: dict[str, dict[str, Any]] = {}
    for sha, metadata in manifest.items():
        sample_rows = [row for row in rows if row["sample_sha256"] == sha]
        sample_flags[sha] = {
            "label": int(metadata["label"]),
            "has_any_html": any(row["has_html_report"] for row in sample_rows),
            "has_any_evtx": any(row["has_evtx"] for row in sample_rows),
            "has_any_pcap": any(row["has_pcap"] for row in sample_rows),
            "providers": sorted({str(row["sandbox_name"]) for row in sample_rows}),
        }

    summary = {
        "samples": len(manifest),
        "behaviour_objects": len(rows),
        "samples_with_html": sum(v["has_any_html"] for v in sample_flags.values()),
        "samples_with_evtx": sum(v["has_any_evtx"] for v in sample_flags.values()),
        "samples_with_evtx_by_label": {
            str(label): sum(
                v["has_any_evtx"] and v["label"] == label
                for v in sample_flags.values()
            )
            for label in (0, 1)
        },
        "provider_summary": provider_summary,
        "raw_report_content_committed": False,
    }
    (args.output / "provider_availability_audit.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
