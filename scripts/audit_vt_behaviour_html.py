#!/usr/bin/env python3
"""Audit downloaded VT behaviour HTML for event-level time/API structure.

This script emits structural counts only. It does not copy raw report content
into the repository and does not claim timestamp usability from token presence
alone.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import pathlib
import re
from collections import Counter, defaultdict
from typing import Any


KEY_PATTERNS = {
    "timestamp_key_count": re.compile(r"[\"']timestamp[\"']\s*[:=]", re.I),
    "event_time_key_count": re.compile(r"[\"']event_?time[\"']\s*[:=]", re.I),
    "time_key_count": re.compile(r"[\"']time[\"']\s*[:=]", re.I),
    "api_key_count": re.compile(r"[\"']api(?:_name)?[\"']\s*[:=]", re.I),
    "calls_key_count": re.compile(r"[\"']calls?[\"']\s*[:=]", re.I),
    "process_id_key_count": re.compile(
        r"[\"'](?:process_?id|pid)[\"']\s*[:=]", re.I
    ),
}
ISO_TIME = re.compile(
    r"\b20\d{2}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?\b"
)
CLOCK_TIME = re.compile(r"\b\d{1,2}:\d{2}:\d{2}(?:\.\d{1,6})?\b")
HTML_ROW = re.compile(r"<tr\b[^>]*>.*?</tr>", re.I | re.S)
LEAF_OBJECT = re.compile(r"\{[^{}]{1,8000}\}", re.S)
TAG = re.compile(r"<[^>]+>")


def count_event_objects(text: str) -> int:
    count = 0
    for match in LEAF_OBJECT.finditer(text):
        block = match.group(0)
        has_api = bool(KEY_PATTERNS["api_key_count"].search(block))
        has_time = any(
            KEY_PATTERNS[name].search(block)
            for name in ("timestamp_key_count", "event_time_key_count", "time_key_count")
        )
        if has_api and has_time:
            count += 1
    return count


def count_event_rows(text: str) -> int:
    count = 0
    for match in HTML_ROW.finditer(text):
        row = TAG.sub(" ", match.group(0))
        has_time = bool(ISO_TIME.search(row) or CLOCK_TIME.search(row))
        # API rows generally expose API/call labels even when values are in cells.
        has_api = bool(re.search(r"\b(?:api|call)\b", row, re.I))
        if has_time and has_api:
            count += 1
    return count


def load_coverage(path: pathlib.Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return {row["sha256"]: row for row in csv.DictReader(handle)}


def write_csv(path: pathlib.Path, rows: list[dict[str, Any]]) -> None:
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports", type=pathlib.Path, required=True)
    parser.add_argument("--coverage", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()

    coverage = load_coverage(args.coverage)
    rows: list[dict[str, Any]] = []
    for report_path in sorted(args.reports.glob("*.html.gz")):
        sha256 = report_path.name.removesuffix(".html.gz")
        body = gzip.decompress(report_path.read_bytes())
        text = body.decode("utf-8", errors="replace")
        metadata = coverage.get(sha256, {})
        row: dict[str, Any] = {
            "sha256": sha256,
            "label": int(metadata["label"]),
            "outer_fold": int(metadata["outer_fold"]),
            "sandbox_name": metadata.get("sandbox_name"),
            "html_bytes": len(body),
            "iso_datetime_count": len(ISO_TIME.findall(text)),
            "clock_time_count": len(CLOCK_TIME.findall(text)),
            "event_object_api_time_count": count_event_objects(text),
            "event_row_api_time_count": count_event_rows(text),
        }
        for name, pattern in KEY_PATTERNS.items():
            row[name] = len(pattern.findall(text))
        row["strong_event_timeline_signal"] = bool(
            row["event_object_api_time_count"] > 0
            or row["event_row_api_time_count"] > 0
        )
        row["weak_time_and_api_signal"] = bool(
            (
                row["timestamp_key_count"]
                + row["event_time_key_count"]
                + row["time_key_count"]
                + row["iso_datetime_count"]
                + row["clock_time_count"]
            )
            > 0
            and (
                row["api_key_count"]
                + row["calls_key_count"]
                + int(bool(re.search(r"\bapi\b", text, re.I)))
            )
            > 0
        )
        rows.append(row)

    args.output.mkdir(parents=True, exist_ok=True)
    write_csv(args.output / "html_structure_by_sample.csv", rows)

    by_provider: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        provider = str(row["sandbox_name"])
        by_provider[provider]["reports"] += 1
        by_provider[provider]["strong"] += int(row["strong_event_timeline_signal"])
        by_provider[provider]["weak"] += int(row["weak_time_and_api_signal"])

    summary = {
        "reports_audited": len(rows),
        "strong_event_timeline_signal_reports": sum(
            int(row["strong_event_timeline_signal"]) for row in rows
        ),
        "weak_time_and_api_signal_reports": sum(
            int(row["weak_time_and_api_signal"]) for row in rows
        ),
        "strong_by_label": {
            str(label): sum(
                int(row["strong_event_timeline_signal"])
                for row in rows
                if row["label"] == label
            )
            for label in (0, 1)
        },
        "provider_counts": {
            provider: dict(counts) for provider, counts in sorted(by_provider.items())
        },
        "interpretation": (
            "Strong means the HTML contains an API key and a time key in the same "
            "leaf JSON object, or an HTML row with API/call and a clock timestamp. "
            "It is a structural screening result; a provider-specific parser and "
            "monotonicity validation are still required before PID evaluation."
        ),
        "raw_report_content_committed": False,
    }
    (args.output / "html_structure_audit.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
