#!/usr/bin/env python3
"""Inspect the schema of a CSV stored in ZIP without extracting the member."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import zipfile


IDENTIFIER_NAMES = {
    "sha256", "sample_sha256", "file_sha256", "binary_sha256", "md5", "sha1",
    "row_id", "sample_id", "file_id", "id",
}
LABEL_NAMES = {
    "label", "is_malware", "malware", "target", "y", "is_ransomware",
    "ransomware", "avclass", "family", "tags",
}
METADATA_NAMES = {
    "appeared", "timestamp", "collection_date", "source", "split", "subset",
}


def normalized(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inspect(archive: Path, member: str | None, sample_rows: int) -> dict:
    archive = archive.resolve()
    if sample_rows < 1:
        raise ValueError("--sample-rows must be positive")
    with zipfile.ZipFile(archive) as zf:
        candidates = [item for item in zf.infolist()
                      if not item.is_dir() and item.filename.lower().endswith(".csv")]
        if member is None:
            if len(candidates) != 1:
                names = [item.filename for item in candidates]
                raise ValueError(f"Expected one CSV member; found {len(candidates)}: {names}")
            selected = candidates[0]
        else:
            selected = zf.getinfo(member)
            if selected.is_dir() or not selected.filename.lower().endswith(".csv"):
                raise ValueError("Selected member is not a CSV file")

        with zf.open(selected, "r") as raw:
            # utf-8-sig handles a BOM while errors=replace keeps the audit readable.
            import io
            text = io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace", newline="")
            reader = csv.reader(text)
            header = next(reader)
            rows = []
            widths = []
            for _, row in zip(range(sample_rows), reader):
                widths.append(len(row))
                rows.append(row)

    normalized_header = [normalized(name) for name in header]
    duplicate_columns = sorted({name for name in normalized_header
                                if normalized_header.count(name) > 1})
    identifiers = [header[i] for i, name in enumerate(normalized_header)
                   if name in IDENTIFIER_NAMES or "sha256" in name]
    labels = [header[i] for i, name in enumerate(normalized_header)
              if name in LABEL_NAMES]
    metadata = [header[i] for i, name in enumerate(normalized_header)
                if name in METADATA_NAMES]
    preview_columns = [i for i, name in enumerate(normalized_header)
                       if (name in IDENTIFIER_NAMES or name in LABEL_NAMES or
                           name in METADATA_NAMES or "sha256" in name)]
    preview = [
        {header[i]: row[i] if i < len(row) else None for i in preview_columns}
        for row in rows
    ]
    return {
        "status": "schema_inspected_without_extraction",
        "archive_path": str(archive),
        "archive_bytes": archive.stat().st_size,
        "archive_sha256": sha256(archive),
        "member": selected.filename,
        "member_uncompressed_bytes": selected.file_size,
        "member_compressed_bytes": selected.compress_size,
        "column_count": len(header),
        "columns": header,
        "normalized_duplicate_columns": duplicate_columns,
        "identifier_columns": identifiers,
        "label_or_family_columns": labels,
        "metadata_columns": metadata,
        "sample_rows_read": len(rows),
        "sample_row_widths": widths,
        "sample_rows_have_expected_width": all(width == len(header) for width in widths),
        "identity_preview_only": preview,
        "full_row_count": None,
        "member_crc_verified": False,
        "member_extracted": False,
        "pe_executed": False,
        "pid_assessment": (
            "static_identity_candidate" if any("sha256" in normalized(x) for x in identifiers)
            else "no_sha256_column_detected"
        ),
        "limitations": [
            "Only the header and requested first data rows were decompressed.",
            "The complete member row count, CRC and label distribution were not verified.",
            "A SHA-256 column identifies samples but does not provide PE binaries or dynamic reports.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect CSV headers inside a ZIP without extracting the member.")
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--member", help="CSV member name; optional when ZIP contains one CSV")
    parser.add_argument("--output", required=True, type=Path,
                        help="New JSON output path")
    parser.add_argument("--sample-rows", type=int, default=20)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"Output already exists: {args.output}")
    result = inspect(args.archive, args.member, args.sample_rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "output": str(args.output.resolve()),
        "column_count": result["column_count"],
        "identifier_columns": result["identifier_columns"],
        "label_or_family_columns": result["label_or_family_columns"],
        "pid_assessment": result["pid_assessment"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
