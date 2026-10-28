#!/usr/bin/env python3
"""Resumable, report-only Cuckoofork collection for the frozen PID cohort."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import os
import pathlib
from collections import Counter
from typing import Any

from collect_vt_behaviour_pilot import Collector, utc_now, write_gzip


TERMINAL_STATUSES = {"no_cuckoofork", "report_collected", "not_found"}
STATE_FIELDS = [
    "sample_sha256",
    "label",
    "outer_fold",
    "status",
    "attempt_count",
    "last_attempt_utc",
    "list_http_status",
    "cuckoofork_available",
    "behaviour_object_id",
    "report_http_status",
    "report_sha256",
    "artifact_run_id",
    "error",
]


def read_csv(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: pathlib.Path, rows: list[dict[str, Any]], fields=None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = sorted({key for row in rows for key in row}) if rows else []
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def initialize_state(cohort_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows = []
    for source in cohort_rows:
        rows.append(
            {
                "sample_sha256": source["sha256"].lower(),
                "label": str(int(source["label"])),
                "outer_fold": str(int(source["outer_fold"])),
                "status": "pending",
                "attempt_count": "0",
                "last_attempt_utc": "",
                "list_http_status": "",
                "cuckoofork_available": "",
                "behaviour_object_id": "",
                "report_http_status": "",
                "report_sha256": "",
                "artifact_run_id": "",
                "error": "",
            }
        )
    return rows


def load_state(
    cohort_rows: list[dict[str, str]], state_path: pathlib.Path
) -> list[dict[str, str]]:
    if not state_path.exists():
        return initialize_state(cohort_rows)
    rows = read_csv(state_path)
    expected = {row["sha256"].lower() for row in cohort_rows}
    observed = {row["sample_sha256"].lower() for row in rows}
    if expected != observed:
        raise ValueError("Collection state SHA-256 set differs from frozen cohort")
    return rows


def balanced_order(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    groups: dict[tuple[int, int], list[dict[str, str]]] = {}
    for row in rows:
        key = (int(row["outer_fold"]), int(row["label"]))
        groups.setdefault(key, []).append(row)
    for values in groups.values():
        values.sort(key=lambda row: row["sample_sha256"])
    ordered = []
    max_size = max(map(len, groups.values()))
    for index in range(max_size):
        for key in sorted(groups):
            if index < len(groups[key]):
                ordered.append(groups[key][index])
    return ordered


def choose_cuckoofork(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    matches = [
        item
        for item in items
        if item.get("attributes", {}).get("sandbox_name")
        == "VirusTotal Cuckoofork"
        and item.get("attributes", {}).get("has_html_report") is True
    ]
    return min(matches, key=lambda item: item.get("id", "")) if matches else None


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cohort", type=pathlib.Path, required=True)
    parser.add_argument("--state", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--requests-per-minute", type=int, default=4)
    parser.add_argument("--max-api-requests", type=int, default=350)
    parser.add_argument("--max-samples", type=int, default=1000)
    args = parser.parse_args()

    api_key = os.environ.get("VT_API_KEY")
    if not api_key:
        raise SystemExit("VT_API_KEY is not set")
    cohort_rows = read_csv(args.cohort)
    state_rows = load_state(cohort_rows, args.state)
    state_by_sha = {row["sample_sha256"]: row for row in state_rows}
    pending = [row for row in balanced_order(state_rows) if row["status"] not in TERMINAL_STATUSES]
    collector = Collector(api_key, args.requests_per_minute)
    args.output.mkdir(parents=True, exist_ok=True)

    samples_attempted = 0
    stop_reason = "no_pending_samples"
    for state in pending:
        if samples_attempted >= args.max_samples:
            stop_reason = "max_samples_reached"
            break
        if len(collector.history) >= args.max_api_requests:
            stop_reason = "request_budget_reached"
            break
        sha256 = state["sample_sha256"]
        state["attempt_count"] = str(int(state.get("attempt_count") or 0) + 1)
        state["last_attempt_utc"] = utc_now()
        state["error"] = ""
        samples_attempted += 1

        list_status, listing_body = collector.list_behaviours(sha256)
        state["list_http_status"] = str(list_status)
        if list_status == 429:
            state["status"] = "pending"
            stop_reason = "http_429"
            break
        if list_status == 404:
            state["status"] = "not_found"
            continue
        if list_status != 200:
            state["status"] = "pending"
            state["error"] = f"list_http_{list_status}"
            if list_status in {401, 403}:
                stop_reason = f"list_http_{list_status}"
                break
            continue

        write_gzip(args.output / "raw_listings" / f"{sha256}.json.gz", listing_body)
        listing = json.loads(listing_body)
        report = choose_cuckoofork(listing.get("data", []))
        if report is None:
            state["cuckoofork_available"] = "false"
            state["status"] = "no_cuckoofork"
            continue
        state["cuckoofork_available"] = "true"
        state["behaviour_object_id"] = str(report.get("id", ""))

        if len(collector.history) >= args.max_api_requests:
            state["status"] = "pending"
            stop_reason = "request_budget_reached_before_report"
            break
        report_status, report_body, _ = collector.download_html(report["id"])
        state["report_http_status"] = str(report_status)
        if report_status == 429:
            state["status"] = "pending"
            stop_reason = "http_429"
            break
        if report_status != 200:
            state["status"] = "pending"
            state["error"] = f"report_http_{report_status}"
            if report_status in {401, 403}:
                stop_reason = f"report_http_{report_status}"
                break
            continue
        write_gzip(
            args.output / "raw_html_reports" / f"{sha256}.html.gz", report_body
        )
        state["report_sha256"] = sha256_bytes(report_body)
        state["artifact_run_id"] = args.run_id
        state["status"] = "report_collected"
    else:
        stop_reason = "collection_complete"

    write_csv(args.state, list(state_by_sha.values()), STATE_FIELDS)
    write_csv(args.output / "request_history.csv", collector.history)
    status_counts = Counter(row["status"] for row in state_rows)
    pending_rows = sum(
        row["status"] not in TERMINAL_STATUSES for row in state_rows
    )
    summary = {
        "status": "collection_complete" if pending_rows == 0 else "batch_complete",
        "generated_at_utc": utc_now(),
        "run_id": args.run_id,
        "binary_downloaded": False,
        "cohort_rows": len(cohort_rows),
        "samples_attempted_this_run": samples_attempted,
        "api_requests_this_run": len(collector.history),
        "stop_reason": stop_reason,
        "status_counts": dict(sorted(status_counts.items())),
        "terminal_rows": sum(
            row["status"] in TERMINAL_STATUSES for row in state_rows
        ),
        "pending_rows": pending_rows,
    }
    (args.output / "batch_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
