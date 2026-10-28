#!/usr/bin/env python3
"""Extract ordered API/timestamp pairs from VT Cuckoofork HTML reports."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import pathlib
import re
import statistics
from collections import Counter
from datetime import datetime, timezone
from typing import Any


API_VALUE = re.compile(
    r"[\"']api[\"']\s*:\s*(\"(?:\\.|[^\"])*\"|'(?:\\.|[^'])*')",
    re.I,
)
TIMESTAMP_VALUE = re.compile(
    r"[\"']timestamp[\"']\s*:\s*(\"(?:\\.|[^\"])*\"|'(?:\\.|[^'])*'|-?\d+(?:\.\d+)?)",
    re.I,
)
CUCKOO_DATETIME = re.compile(r"^(\d{14})(?:\.(\d+))?$")


def decode_string(token: str) -> str:
    if token.startswith('"'):
        return str(json.loads(token))
    if token.startswith("'"):
        return token[1:-1].replace("\\'", "'").replace("\\\\", "\\")
    return token


def read_coverage(path: pathlib.Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return {row["sample_sha256"].lower(): row for row in csv.DictReader(handle)}


def write_csv(path: pathlib.Path, rows: list[dict[str, Any]]) -> None:
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_gzip_csv(path: pathlib.Path, rows: list[dict[str, Any]]) -> None:
    fields = sorted({key for row in rows for key in row})
    with gzip.open(path, "wt", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def infer_unit(tokens: list[str]) -> str:
    if tokens and all(CUCKOO_DATETIME.fullmatch(token) for token in tokens):
        return "cuckoofork_yyyymmddHHMMSS_fractional_seconds"
    values = [float(token) for token in tokens]
    magnitude = statistics.median(abs(value) for value in values)
    if magnitude >= 1e16:
        return "windows_filetime_or_high_resolution_unknown"
    if magnitude >= 1e12:
        return "epoch_milliseconds"
    if magnitude >= 1e9:
        return "epoch_seconds"
    return "relative_or_unknown"


def timestamp_to_seconds(token: str, unit: str) -> float:
    if unit == "cuckoofork_yyyymmddHHMMSS_fractional_seconds":
        match = CUCKOO_DATETIME.fullmatch(token)
        if not match:
            raise ValueError(f"Invalid Cuckoofork timestamp: {token}")
        base = datetime.strptime(match.group(1), "%Y%m%d%H%M%S").replace(
            tzinfo=timezone.utc
        )
        fraction = float(f"0.{match.group(2)}") if match.group(2) else 0.0
        return base.timestamp() + fraction
    value = float(token)
    if unit == "epoch_milliseconds":
        return value / 1000.0
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports", type=pathlib.Path, required=True)
    parser.add_argument("--coverage", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()

    coverage = read_coverage(args.coverage)
    event_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []

    for report_path in sorted(args.reports.glob("*.html.gz")):
        sample_sha256 = report_path.name.removesuffix(".html.gz").lower()
        metadata = coverage[sample_sha256]
        text = gzip.decompress(report_path.read_bytes()).decode(
            "utf-8", errors="replace"
        )
        api_matches = list(API_VALUE.finditer(text))
        timestamp_matches = list(TIMESTAMP_VALUE.finditer(text))
        pair_count = min(len(api_matches), len(timestamp_matches))
        pairs = []
        for index in range(pair_count):
            api_match = api_matches[index]
            timestamp_match = timestamp_matches[index]
            api_name = decode_string(api_match.group(1))
            timestamp_token = decode_string(timestamp_match.group(1))
            try:
                float(timestamp_token)
            except ValueError:
                continue
            pairs.append(
                {
                    "event_index": index,
                    "api_name": api_name,
                    "timestamp_raw": timestamp_token,
                    "key_position_distance": abs(
                        api_match.start() - timestamp_match.start()
                    ),
                }
            )

        timestamp_tokens = [str(pair["timestamp_raw"]) for pair in pairs]
        unit = infer_unit(timestamp_tokens) if timestamp_tokens else "unavailable"
        timestamps = [
            timestamp_to_seconds(token, unit) for token in timestamp_tokens
        ]
        if timestamps:
            first_seconds = timestamps[0]
            for pair in pairs:
                seconds = timestamp_to_seconds(str(pair["timestamp_raw"]), unit)
                pair["timestamp_seconds"] = seconds
                pair["timestamp_relative_seconds"] = seconds - first_seconds
        transitions = max(0, len(timestamps) - 1)
        nondecreasing = sum(
            current >= previous
            for previous, current in zip(timestamps, timestamps[1:])
        )
        positive_deltas = [
            current - previous
            for previous, current in zip(timestamps, timestamps[1:])
            if current > previous
        ]
        local_pairs = sum(pair["key_position_distance"] <= 2000 for pair in pairs)
        usable = bool(
            len(pairs) >= 3
            and len(api_matches) == len(timestamp_matches) == len(pairs)
            and len(set(timestamps)) >= 3
            and (nondecreasing / transitions if transitions else 0.0) >= 0.95
            and local_pairs / len(pairs) >= 0.8
        )

        audit_rows.append(
            {
                "sample_sha256": sample_sha256,
                "label": int(metadata["label"]),
                "outer_fold": int(metadata["outer_fold"]),
                "sandbox_name": metadata["sandbox_name"],
                "api_match_count": len(api_matches),
                "timestamp_match_count": len(timestamp_matches),
                "parsed_pair_count": len(pairs),
                "unique_api_count": len({pair["api_name"] for pair in pairs}),
                "distinct_timestamp_count": len(set(timestamps)),
                "timestamp_unit_inference": unit,
                "timestamp_raw_min": min(timestamp_tokens) if timestamp_tokens else None,
                "timestamp_raw_max": max(timestamp_tokens) if timestamp_tokens else None,
                "elapsed_seconds": max(timestamps) - min(timestamps) if timestamps else None,
                "median_positive_delta_seconds": (
                    statistics.median(positive_deltas) if positive_deltas else None
                ),
                "nondecreasing_fraction": (
                    nondecreasing / transitions if transitions else None
                ),
                "local_pair_fraction": local_pairs / len(pairs) if pairs else None,
                "median_key_position_distance": (
                    statistics.median(
                        pair["key_position_distance"] for pair in pairs
                    )
                    if pairs
                    else None
                ),
                "usable_event_sequence": usable,
            }
        )
        for pair in pairs:
            event_rows.append(
                {
                    "sample_sha256": sample_sha256,
                    "label": int(metadata["label"]),
                    "outer_fold": int(metadata["outer_fold"]),
                    "sandbox_name": metadata["sandbox_name"],
                    **pair,
                }
            )

    args.output.mkdir(parents=True, exist_ok=True)
    write_csv(args.output / "event_sequence_audit.csv", audit_rows)
    write_gzip_csv(args.output / "timestamped_api_events.csv.gz", event_rows)
    status_counts = Counter(
        "usable" if row["usable_event_sequence"] else "rejected"
        for row in audit_rows
    )
    summary = {
        "reports": len(audit_rows),
        "events": len(event_rows),
        "status_counts": dict(status_counts),
        "usable_by_label": {
            str(label): sum(
                row["usable_event_sequence"] and row["label"] == label
                for row in audit_rows
            )
            for label in (0, 1)
        },
        "unit_inference_counts": dict(
            Counter(row["timestamp_unit_inference"] for row in audit_rows)
        ),
        "limitations": [
            "API and timestamp values are paired by their ordered occurrence in the provider report.",
            "Unit inference must be confirmed before computing wall-clock derivatives.",
            "Process IDs are not yet joined to individual calls.",
        ],
    }
    (args.output / "event_extraction_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
