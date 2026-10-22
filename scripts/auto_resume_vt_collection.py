#!/usr/bin/env python3
"""Resume a VirusTotal metadata collection without bypassing API quotas.

The worker uses the existing resumable collector, one process at a time.  It
waits after HTTP 429 responses, never downloads executable bytes, and stops
when every cohort row has received a terminal request status.  It deliberately
does not start confirmatory modeling.
"""

from __future__ import annotations

import argparse
import csv
import fcntl
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone


UTC = timezone.utc


def utc_now() -> datetime:
    return datetime.now(UTC)


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def request_status_counts(request_log: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    if not request_log.is_file():
        return counts
    with request_log.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            status = str(row.get("status", ""))
            counts[status] = counts.get(status, 0) + 1
    return counts


def initial_retry_time(history_path: Path, quota_window_hours: float) -> datetime | None:
    """Return first 429 after the latest fetch plus the conservative quota window."""
    if not history_path.is_file():
        return None
    events: list[tuple[datetime, str]] = []
    with history_path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            attempted = row.get("attempted_at_utc")
            if attempted:
                events.append((parse_utc(attempted), str(row.get("status", ""))))
    fetched = [when for when, status in events if status == "fetched"]
    last_fetched = max(fetched) if fetched else datetime.min.replace(tzinfo=UTC)
    exhausted = sorted(
        when for when, status in events if status == "http_429" and when > last_fetched
    )
    if not exhausted:
        return None
    return exhausted[0] + timedelta(hours=quota_window_hours, minutes=5)


def configure_logging(log_path: Path) -> logging.Logger:
    logger = logging.getLogger("vt-auto-resume")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)sZ %(levelname)s %(message)s")
    formatter.converter = time.gmtime
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.handlers[:] = [file_handler, stream_handler]
    return logger


def update_state(path: Path, started_at: str, status: str, **extra) -> None:
    state = {
        "pid": os.getpid(),
        "started_at_utc": started_at,
        "updated_at_utc": utc_now().isoformat(),
        "status": status,
        **extra,
    }
    write_json(path, state)


def interruptible_wait(
    deadline: datetime,
    stop_file: Path,
    state_path: Path,
    started_at: str,
    logger: logging.Logger,
    status: str,
) -> bool:
    update_state(
        state_path,
        started_at,
        status,
        next_attempt_at_utc=deadline.isoformat(),
    )
    logger.info("Waiting until %s", deadline.isoformat())
    while utc_now() < deadline:
        if stop_file.exists():
            logger.info("Stop file detected: %s", stop_file)
            update_state(state_path, started_at, "stopped_by_file")
            return False
        time.sleep(min(60.0, max(1.0, (deadline - utc_now()).total_seconds())))
    return True


def run_command(command: list[str], cwd: Path, logger: logging.Logger) -> int:
    result = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        env={**os.environ, "MPLCONFIGDIR": "/tmp/mplconfig", "XDG_CACHE_HOME": "/tmp/cache"},
    )
    if result.stdout.strip():
        logger.info("Command output:\n%s", result.stdout.rstrip())
    return int(result.returncode)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--requests-per-minute", type=float, default=4.0)
    parser.add_argument("--max-new", type=int, default=100)
    parser.add_argument("--min-coverage", type=float, default=0.90)
    parser.add_argument("--quota-window-hours", type=float, default=24.0)
    parser.add_argument("--rate-limit-retry-hours", type=float, default=6.0)
    parser.add_argument("--error-retry-hours", type=float, default=6.0)
    parser.add_argument("--batch-gap-seconds", type=float, default=20.0)
    parser.add_argument(
        "--status-only",
        action="store_true",
        help="Print the derived status and next retry time without issuing network requests.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repository = Path(__file__).resolve().parents[1]
    cohort = args.cohort.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    history_path = output / "request_history.csv"
    request_log = output / "request_log.csv"
    summary_path = output / "collection_summary.json"
    state_path = output / "auto_collection_state.json"
    stop_file = output / "STOP_AUTO_COLLECTION"
    lock_path = output / "auto_collection.lock"
    log_path = output / "auto_collection.log"
    started_at = utc_now().isoformat()
    logger = configure_logging(log_path)

    if not cohort.is_file():
        logger.error("Missing cohort: %s", cohort)
        return 2

    retry_at = initial_retry_time(history_path, args.quota_window_hours)
    counts = request_status_counts(request_log)
    derived = {
        "request_status_counts": counts,
        "next_attempt_at_utc": retry_at.isoformat() if retry_at else None,
        "stop_file": str(stop_file),
        "log_file": str(log_path),
    }
    if args.status_only:
        print(json.dumps(derived, ensure_ascii=False, indent=2))
        return 0

    if not os.environ.get("VT_API_KEY"):
        logger.error("VT_API_KEY is not available in the environment.")
        update_state(state_path, started_at, "blocked_missing_secret", **derived)
        return 2

    lock_handle = lock_path.open("w", encoding="utf-8")
    try:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        logger.error("Another automatic collector already holds %s", lock_path)
        return 4
    lock_handle.write(str(os.getpid()) + "\n")
    lock_handle.flush()

    if stop_file.exists():
        logger.error("Remove the existing stop file before starting: %s", stop_file)
        update_state(state_path, started_at, "blocked_stop_file_present")
        return 5

    logger.info("Automatic collector started with PID %s", os.getpid())
    logger.info("Cohort: %s", cohort)
    logger.info("Output: %s", output)
    if retry_at and retry_at > utc_now():
        if not interruptible_wait(
            retry_at,
            stop_file,
            state_path,
            started_at,
            logger,
            "waiting_initial_quota_window",
        ):
            return 0

    python = repository / ".venv" / "bin" / "python"
    runner = repository / "scripts" / "run_experiments.py"
    collect = [
        str(python),
        str(runner),
        "collect-vt-static",
        "--cohort",
        str(cohort),
        "--output",
        str(output),
        "--seed",
        str(args.seed),
        "--requests-per-minute",
        str(args.requests_per_minute),
        "--max-new",
        str(args.max_new),
    ]
    audit = [
        str(python),
        str(runner),
        "audit-vt-collection",
        "--cohort",
        str(cohort),
        "--collection",
        str(output),
        "--min-coverage",
        str(args.min_coverage),
    ]

    while True:
        if stop_file.exists():
            logger.info("Stop file detected before collection.")
            update_state(state_path, started_at, "stopped_by_file")
            return 0

        counts = request_status_counts(request_log)
        deferred = sum(value for key, value in counts.items() if key.startswith("deferred_"))
        if counts and deferred == 0:
            logger.info("No deferred cohort rows remain; collection attempts are complete.")
            run_command(audit, repository, logger)
            update_state(
                state_path,
                started_at,
                "collection_attempts_complete",
                request_status_counts=counts,
            )
            return 0

        update_state(
            state_path,
            started_at,
            "collecting",
            request_status_counts=counts,
        )
        logger.info("Starting one sequential batch; deferred rows before batch: %s", deferred)
        code = run_command(collect, repository, logger)
        if code != 0:
            logger.error("Collector exited with code %s", code)
            deadline = utc_now() + timedelta(hours=args.error_retry_hours)
            if not interruptible_wait(
                deadline,
                stop_file,
                state_path,
                started_at,
                logger,
                "waiting_after_collector_error",
            ):
                return 0
            continue

        summary = read_json(summary_path)
        counts = request_status_counts(request_log)
        deferred = sum(value for key, value in counts.items() if key.startswith("deferred_"))
        logger.info(
            "Batch finished: usable=%s coverage=%.6f new_requests=%s fetched=%s deferred=%s rate_limited=%s",
            summary.get("usable_rows"),
            float(summary.get("coverage", 0.0)),
            summary.get("new_requests_this_invocation"),
            summary.get("successful_fetches_this_invocation"),
            deferred,
            summary.get("rate_limit_encountered"),
        )
        run_command(audit, repository, logger)

        if summary.get("rate_limit_encountered"):
            deadline = utc_now() + timedelta(hours=args.rate_limit_retry_hours)
            if not interruptible_wait(
                deadline,
                stop_file,
                state_path,
                started_at,
                logger,
                "waiting_after_http_429",
            ):
                return 0
            continue

        if int(summary.get("successful_fetches_this_invocation", 0)) == 0:
            deadline = utc_now() + timedelta(hours=args.error_retry_hours)
            if not interruptible_wait(
                deadline,
                stop_file,
                state_path,
                started_at,
                logger,
                "waiting_after_no_progress",
            ):
                return 0
            continue

        if deferred == 0:
            logger.info("All cohort rows now have terminal request statuses.")
            update_state(
                state_path,
                started_at,
                "collection_attempts_complete",
                request_status_counts=counts,
                usable_rows=summary.get("usable_rows"),
                coverage=summary.get("coverage"),
            )
            return 0

        deadline = utc_now() + timedelta(seconds=args.batch_gap_seconds)
        if not interruptible_wait(
            deadline,
            stop_file,
            state_path,
            started_at,
            logger,
            "waiting_between_batches",
        ):
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
