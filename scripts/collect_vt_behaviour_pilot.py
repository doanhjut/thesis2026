#!/usr/bin/env python3
"""Collect a deterministic, report-only VirusTotal behaviour pilot.

The collector never requests the file download endpoint. It lists sandbox
behaviour objects and, when available, downloads one HTML behaviour report per
sample. Cross-host redirects are followed without forwarding the VT API key.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import os
import pathlib
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from typing import Any


VT_API_ROOT = "https://www.virustotal.com/api/v3"
ALLOWED_REPORT_HOSTS = {
    "vtbehaviour.commondatastorage.googleapis.com",
    "vtcuckoo.commondatastorage.googleapis.com",
}
PREFERRED_SANDBOXES = (
    "CAPE Sandbox",
    "VirusTotal Jujubox",
    "Tencent HABO",
)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_gzip(path: pathlib.Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wb", compresslevel=9) as handle:
        handle.write(data)


def read_cohort(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    required = {"sha256", "label", "outer_fold"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"Cohort must contain {sorted(required)}")
    for row in rows:
        if not re.fullmatch(r"[0-9a-fA-F]{64}", row["sha256"]):
            raise ValueError("Invalid SHA-256 in cohort")
    return rows


def select_balanced_pilot(
    rows: list[dict[str, str]], per_fold_label: int
) -> list[dict[str, str]]:
    grouped: dict[tuple[int, int], list[dict[str, str]]] = {}
    for row in rows:
        key = (int(row["outer_fold"]), int(row["label"]))
        grouped.setdefault(key, []).append(row)
    selected: list[dict[str, str]] = []
    for key in sorted(grouped):
        candidates = sorted(grouped[key], key=lambda item: item["sha256"])
        if len(candidates) < per_fold_label:
            raise ValueError(f"Insufficient rows for fold/label {key}")
        selected.extend(candidates[:per_fold_label])
    return selected


class Collector:
    def __init__(self, api_key: str, requests_per_minute: int) -> None:
        self.api_key = api_key
        self.min_interval = 60.0 / requests_per_minute
        self.last_vt_request_at: float | None = None
        self.history: list[dict[str, Any]] = []
        self.no_redirect = urllib.request.build_opener(NoRedirect)

    def _wait(self) -> None:
        if self.last_vt_request_at is None:
            return
        remaining = self.min_interval - (time.monotonic() - self.last_vt_request_at)
        if remaining > 0:
            time.sleep(remaining)

    def vt_get(self, url: str, *, accept: str) -> tuple[int, bytes, dict[str, str]]:
        self._wait()
        attempted_at = utc_now()
        request = urllib.request.Request(
            url,
            headers={"x-apikey": self.api_key, "accept": accept},
        )
        status = 0
        body = b""
        headers: dict[str, str] = {}
        try:
            with self.no_redirect.open(request, timeout=60) as response:
                status = response.status
                body = response.read()
                headers = dict(response.headers.items())
        except urllib.error.HTTPError as error:
            status = error.code
            body = error.read()
            headers = dict(error.headers.items())
        finally:
            self.last_vt_request_at = time.monotonic()
            self.history.append(
                {
                    "attempted_at_utc": attempted_at,
                    "endpoint": urllib.parse.urlparse(url).path,
                    "http_status": status,
                }
            )
        return status, body, headers

    def list_behaviours(self, sha256: str) -> tuple[int, bytes]:
        url = f"{VT_API_ROOT}/files/{sha256}/behaviours?limit=40"
        status, body, _ = self.vt_get(url, accept="application/json")
        return status, body

    def download_html(self, object_id: str) -> tuple[int, bytes, str | None]:
        encoded = urllib.parse.quote(object_id, safe="")
        url = f"{VT_API_ROOT}/file_behaviours/{encoded}/html"
        status, body, headers = self.vt_get(
            url, accept="text/html,application/octet-stream"
        )
        if status not in {301, 302, 303, 307, 308}:
            return status, body, None
        location = headers.get("Location") or headers.get("location")
        if not location:
            return status, b"", None
        host = urllib.parse.urlparse(location).hostname
        if host not in ALLOWED_REPORT_HOSTS:
            raise RuntimeError(f"Refusing unexpected report redirect host: {host}")
        # The signed storage URL is fetched without x-apikey.
        request = urllib.request.Request(
            location, headers={"accept": "text/html,application/octet-stream"}
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return response.status, response.read(), host
        except urllib.error.HTTPError as error:
            return error.code, error.read(), host


def choose_report(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    eligible = [
        item
        for item in items
        if item.get("attributes", {}).get("has_html_report") is True
    ]
    if not eligible:
        return None
    rank = {name: index for index, name in enumerate(PREFERRED_SANDBOXES)}
    return min(
        eligible,
        key=lambda item: (
            rank.get(item.get("attributes", {}).get("sandbox_name"), 999),
            item.get("id", ""),
        ),
    )


def inspect_report(body: bytes) -> dict[str, Any]:
    lowered = body.lower()
    return {
        "size_bytes": len(body),
        "report_sha256": sha256_bytes(body),
        "contains_timestamp_token": b"timestamp" in lowered,
        "contains_api_token": b"api" in lowered,
        "contains_calls_token": b"calls" in lowered,
        "contains_process_token": b"process" in lowered,
    }


def write_csv(path: pathlib.Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row}) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cohort", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--per-fold-label", type=int, default=2)
    parser.add_argument("--requests-per-minute", type=int, default=4)
    args = parser.parse_args()

    api_key = os.environ.get("VT_API_KEY")
    if not api_key:
        raise SystemExit("VT_API_KEY is not set")

    rows = read_cohort(args.cohort)
    pilot = select_balanced_pilot(rows, args.per_fold_label)
    args.output.mkdir(parents=True, exist_ok=True)
    write_csv(args.output / "pilot_manifest.csv", pilot)

    collector = Collector(api_key, args.requests_per_minute)
    audit_rows: list[dict[str, Any]] = []
    quota_exhausted = False

    for row in pilot:
        sha256 = row["sha256"].lower()
        record: dict[str, Any] = {
            "sample_sha256": sha256,
            "label": int(row["label"]),
            "outer_fold": int(row["outer_fold"]),
        }
        status, listing_body = collector.list_behaviours(sha256)
        record["list_http_status"] = status
        if status == 429:
            record["status"] = "deferred_quota"
            audit_rows.append(record)
            quota_exhausted = True
            break
        if status != 200:
            record["status"] = "list_error"
            audit_rows.append(record)
            continue

        write_gzip(
            args.output / "raw_listings" / f"{sha256}.json.gz", listing_body
        )
        listing = json.loads(listing_body)
        items = listing.get("data", [])
        record["behaviour_object_count"] = len(items)
        report = choose_report(items)
        if report is None:
            record["status"] = "no_html_report"
            audit_rows.append(record)
            continue

        attributes = report.get("attributes", {})
        record["sandbox_name"] = attributes.get("sandbox_name")
        record["behaviour_object_id"] = report.get("id")
        download_status, report_body, redirect_host = collector.download_html(
            report["id"]
        )
        record["report_http_status"] = download_status
        record["redirect_host"] = redirect_host
        if download_status == 429:
            record["status"] = "deferred_quota"
            audit_rows.append(record)
            quota_exhausted = True
            break
        if download_status != 200:
            record["status"] = "report_error"
            audit_rows.append(record)
            continue

        report_path = args.output / "raw_html_reports" / f"{sha256}.html.gz"
        write_gzip(report_path, report_body)
        record.update(inspect_report(report_body))
        record["status"] = "report_collected"
        audit_rows.append(record)

    write_csv(args.output / "coverage_by_sample.csv", audit_rows)
    write_csv(args.output / "request_history.csv", collector.history)
    counts = Counter(row.get("status", "unknown") for row in audit_rows)
    summary = {
        "status": "quota_exhausted" if quota_exhausted else "pilot_complete",
        "generated_at_utc": utc_now(),
        "binary_downloaded": False,
        "cohort": str(args.cohort),
        "cohort_sha256": sha256_bytes(args.cohort.read_bytes()),
        "selected_rows": len(pilot),
        "attempted_rows": len(audit_rows),
        "requests_per_minute": args.requests_per_minute,
        "status_counts": dict(sorted(counts.items())),
        "timestamp_token_reports": sum(
            bool(row.get("contains_timestamp_token")) for row in audit_rows
        ),
        "api_token_reports": sum(
            bool(row.get("contains_api_token")) for row in audit_rows
        ),
        "limitations": [
            "Token presence is a schema triage signal, not proof of per-event timestamps.",
            "Raw reports must be parsed and validated before PID evaluation.",
            "No executable or PE binary endpoint is requested by this collector.",
        ],
    }
    (args.output / "coverage_audit.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if not quota_exhausted else 75


if __name__ == "__main__":
    raise SystemExit(main())
