"""Audit whether the repository contains inputs needed for paired PID evidence."""
from pathlib import Path

import pandas as pd

from .common import REPO, sha256, write_json


IDENTIFIER_COLUMNS = {'sha256', 'sample_sha256', 'file_sha256', 'binary_sha256'}
PE_SUFFIXES = {'.exe', '.dll', '.sys', '.scr', '.msi'}
SOURCE_NAMES = {
    'train-features.npz', 'test-features.npz', 'validation-features.npz',
    'X_train.dat', 'y_train.dat', 'X_test.dat', 'y_test.dat',
}


def audit(data_path, repo=REPO, output=None):
    repo, data_path = Path(repo).resolve(), Path(data_path).resolve()
    header = pd.read_csv(data_path, nrows=0, encoding='utf-8-sig')
    with data_path.open('rb') as stream:
        row_count = sum(1 for _ in stream) - 1
    identifiers = sorted(IDENTIFIER_COLUMNS & set(header.columns))
    binaries = sorted(p for p in (repo / 'data').rglob('*') if p.is_file() and p.suffix.lower() in PE_SUFFIXES)
    sources = sorted(p for p in repo.rglob('*') if p.is_file() and p.name in SOURCE_NAMES)
    report_roots = [repo / 'data/dynamic_reports', repo / 'data/sandbox_reports', repo / 'data/cuckoo_reports']
    reports = sorted(p for root in report_roots if root.exists() for p in root.rglob('*') if p.is_file())
    demo_trace = repo / 'data/dynamic_logs/raw_pid_trace.csv'
    demo_source = repo / 'scripts/live_defense_demo.py'
    blockers = []
    if not identifiers:
        blockers.append('Feature CSV has no sample SHA-256 or other binary identifier.')
    if not binaries:
        blockers.append('No source PE binaries are available under data/.')
    if not sources:
        blockers.append('Original feature archive/raw EMBER arrays are unavailable, so sampled source indices cannot be reconstructed here.')
    if not reports:
        blockers.append('No per-sample sandbox reports are present in a supported report directory.')
    result = {
        'status': 'ready' if not blockers else 'blocked',
        'dataset': {'path': str(data_path), 'sha256': sha256(data_path), 'rows': row_count,
                    'columns': len(header.columns), 'identifier_columns': identifiers},
        'source_feature_files': [str(p.relative_to(repo)) for p in sources],
        'pe_binary_count': len(binaries),
        'dynamic_report_count': len(reports),
        'known_demo_artifacts': {
            'trace': str(demo_trace.relative_to(repo)) if demo_trace.exists() else None,
            'source': str(demo_source.relative_to(repo)) if demo_source.exists() else None,
            'usable_as_pid_evidence': False,
        },
        'blockers': blockers,
        'required_user_inputs': [
            'A row-to-binary manifest containing row_id and sample_sha256, or the original archive plus its metadata/index mapping.',
            'Authorized PE binaries or an existing sandbox corpus linked by sample_sha256.',
            'Per-execution dynamic reports with timestamps and multiple observation windows.',
            'A documented label source distinguishing benign, generic malware and ransomware.',
        ] if blockers else [],
    }
    if output:
        output = Path(output)
        output.mkdir(parents=True, exist_ok=False)
        write_json(output / 'audit_pid_inputs.json', result)
    return result
