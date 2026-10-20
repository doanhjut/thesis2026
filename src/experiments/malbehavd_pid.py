"""Safe, report-only PID benchmark built from MalBehavD-V1 and VT metadata.

No executable is downloaded or executed.  The dynamic channel is the ordered
API-call sequence published by MalBehavD-V1.  The static channel is restricted
to intrinsic PE structure returned for the same SHA-256 by VirusTotal.
"""
from __future__ import annotations

from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

from .common import (choose_threshold, evaluate, low_fpr_metrics, require,
                     sha256, source_metadata, stats, write_json)
from .temporal_fusion import score_trajectory, select_on_validation


DATASET_URL = 'https://github.com/mpasco/MalbehavD-V1'
DATASET_COMMIT = '6aac5027635ac3d2832d323a873fccd7cdd89a5e'
EXPECTED_DATASET_SHA256 = '1e39c43a014e9b4ee56766ad6bb367ffe8ec4316eb0be75eb182c3b2d15f6364'
SAFE_VT_TOP_LEVEL = {'sha256', 'size', 'type_tag', 'pe_info'}
EXCLUDED_VT_FIELDS = [
    'last_analysis_results', 'last_analysis_stats', 'popular_threat_classification',
    'threat_names', 'crowdsourced_yara_results', 'sandbox_verdicts', 'tags', 'names',
]


def _counts(values):
    return {str(key): int(value) for key, value in pd.Series(values).value_counts().sort_index().items()}


def prepare(source, out, min_events=20, folds=5, seed=2026):
    """Audit, deduplicate and freeze the public API-sequence cohort."""
    source, out = Path(source).resolve(), Path(out)
    require(source.is_file(), f'Missing MalBehavD-V1 CSV: {source}')
    require(min_events >= 2, 'At least two ordered API events are required.')
    require(folds >= 2, 'At least two outer folds are required.')
    out.mkdir(parents=True, exist_ok=False)
    frame = pd.read_csv(source, dtype=str, encoding='utf-8-sig')
    require({'sha256', 'labels'} <= set(frame), 'MalBehavD-V1 requires sha256 and labels columns.')
    require(frame.sha256.str.fullmatch(r'[0-9a-fA-F]{64}').all(), 'Invalid SHA-256 in source CSV.')
    require(set(frame.labels.dropna()) == {'0', '1'}, 'Expected binary labels 0/1.')
    frame['sha256'] = frame.sha256.str.lower()
    frame['label'] = frame.labels.astype(int)
    frame['source_row'] = np.arange(len(frame), dtype=int)
    api_columns = [name for name in frame.columns if name not in {'sha256', 'labels', 'label', 'source_row'}]
    sequences = []
    for row in frame[api_columns].itertuples(index=False, name=None):
        sequences.append([str(value) for value in row if pd.notna(value) and str(value).strip()])
    frame['api_sequence'] = sequences
    frame['api_count'] = [len(value) for value in sequences]

    conflicts = frame.groupby('sha256').label.nunique()
    require(not (conflicts > 1).any(), 'Duplicate SHA-256 values have conflicting labels.')
    duplicate_rows = int(frame.sha256.duplicated(keep=False).sum())
    duplicate_hashes = int(frame.loc[frame.sha256.duplicated(keep=False), 'sha256'].nunique())
    # Keep the longest published trace; source row resolves exact ties deterministically.
    unique = (frame.sort_values(['sha256', 'api_count', 'source_row'], ascending=[True, False, True])
              .drop_duplicates('sha256', keep='first'))
    eligible = unique.loc[unique.api_count >= min_events].copy()
    require(len(eligible) >= folds * 4, 'Cohort is too small for the requested folds.')
    require(eligible.groupby('label').size().min() >= folds * 2, 'Each class needs at least two samples per fold.')
    eligible = eligible.sort_values('sha256').reset_index(drop=True)
    eligible['row_id'] = np.arange(len(eligible), dtype=int)
    eligible['outer_fold'] = -1
    splitter = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
    for fold, (_, test) in enumerate(splitter.split(np.zeros(len(eligible)), eligible.label)):
        eligible.loc[test, 'outer_fold'] = fold
    require((eligible.outer_fold >= 0).all(), 'Outer-fold assignment failed.')

    manifest_columns = ['row_id', 'sha256', 'label', 'api_count', 'source_row', 'outer_fold']
    eligible[manifest_columns].to_csv(out / 'cohort_manifest.csv', index=False)
    sequence_table = eligible[manifest_columns].copy()
    sequence_table['api_sequence_json'] = eligible.api_sequence.map(
        lambda value: json.dumps(value, ensure_ascii=False, separators=(',', ':')))
    sequence_table.to_csv(out / 'api_sequences.csv.gz', index=False, compression='gzip')
    dataset_hash = sha256(source)
    audit = {
        'status': 'prepared_public_report_only_cohort',
        'source': str(source), 'source_url': DATASET_URL,
        'source_repository_commit': DATASET_COMMIT,
        'source_sha256': dataset_hash,
        'expected_source_sha256': EXPECTED_DATASET_SHA256,
        'source_sha256_matches_expected': dataset_hash == EXPECTED_DATASET_SHA256,
        'source_rows': int(len(frame)), 'source_class_counts': _counts(frame.label),
        'unique_sha256': int(unique.sha256.nunique()),
        'duplicate_rows_involved': duplicate_rows, 'duplicate_sha256': duplicate_hashes,
        'conflicting_duplicate_labels': 0,
        'minimum_api_events': int(min_events), 'eligible_rows': int(len(eligible)),
        'eligible_class_counts': _counts(eligible.label),
        'folds': int(folds), 'fold_seed': int(seed),
        'fold_class_counts': {
            str(fold): _counts(group.label) for fold, group in eligible.groupby('outer_fold')
        },
        'label_semantics': '0=benign, 1=malware as published by MalBehavD-V1.',
        'license': 'MIT as published in the source repository.',
        'citation': 'Maniriho et al., API-MalDetect, Journal of Network and Computer Applications, 2023.',
        'safety': 'CSV-only public artifact; no PE executable is downloaded or executed.',
        'limitations': [
            'The benchmark is generic Windows malware detection, not ransomware-specific ground truth.',
            'API calls are ordered but do not include wall-clock timestamps; PID is indexed by event count.',
            'Benign and malware samples were collected from different upstream sources, so source bias must be discussed.',
        ],
    }
    write_json(out / 'dataset_audit.json', audit)
    (out / 'README.md').write_text(
        '# MalBehavD-V1 event-indexed PID cohort\n\n'
        'This directory contains identifiers, labels and ordered API-call strings only. '
        'It contains no Windows executable. `outer_fold` was frozen before querying VirusTotal '
        'or fitting any model. Cite Maniriho et al., API-MalDetect, JNCA 2023.\n', encoding='utf-8')
    return audit


def _finite(value, default=0.0):
    try:
        number = float(value)
        return number if np.isfinite(number) else default
    except (TypeError, ValueError):
        return default


def _summary(values, prefix):
    array = np.asarray([_finite(value) for value in values], dtype=float)
    if not len(array):
        return {f'{prefix}_{name}': 0.0 for name in ['sum', 'mean', 'sd', 'min', 'max']}
    return {
        f'{prefix}_sum': float(array.sum()), f'{prefix}_mean': float(array.mean()),
        f'{prefix}_sd': float(array.std()), f'{prefix}_min': float(array.min()),
        f'{prefix}_max': float(array.max()),
    }


def _hash_counts(tokens, prefix, bins):
    values = np.zeros(bins, dtype=float)
    for token in tokens:
        digest = hashlib.sha256(str(token).lower().encode('utf-8', 'replace')).digest()
        values[int.from_bytes(digest[:4], 'big') % bins] += 1.0
    return {f'{prefix}_{index:03d}': float(np.log1p(value))
            for index, value in enumerate(values)}


def safe_static_features(response):
    """Extract an explicit allow-list; AV detections and threat names are unreachable."""
    attributes = response.get('data', {}).get('attributes', {})
    selected = {key: attributes.get(key) for key in SAFE_VT_TOP_LEVEL}
    pe = selected.get('pe_info') or {}
    sections = pe.get('sections') or []
    imports = pe.get('import_list') or []
    resources = pe.get('resource_details') or []
    exports = pe.get('exports') or []
    overlay = pe.get('overlay') or {}
    size = _finite(selected.get('size'))
    entry = _finite(pe.get('entry_point'))
    result = {
        's_file_size_log1p': float(np.log1p(max(size, 0))),
        's_entry_point_log1p': float(np.log1p(max(entry, 0))),
        's_entry_point_ratio': float(entry / max(size, 1)),
        's_section_count': float(len(sections)),
        's_import_library_count': float(len(imports)),
        's_import_function_count': float(sum(len(item.get('imported_functions') or []) for item in imports)),
        's_export_count': float(len(exports)), 's_resource_count': float(len(resources)),
        's_overlay_present': float(bool(overlay)),
        's_overlay_size_log1p': float(np.log1p(max(_finite(overlay.get('size')), 0))),
        's_overlay_entropy': _finite(overlay.get('entropy')),
        's_overlay_chi2_log1p': float(np.log1p(max(_finite(overlay.get('chi2')), 0))),
    }
    for field in ['entropy', 'raw_size', 'virtual_size', 'chi2']:
        values = [section.get(field) for section in sections]
        if field in {'raw_size', 'virtual_size', 'chi2'}:
            values = [np.log1p(max(_finite(value), 0)) for value in values]
        result.update(_summary(values, f's_section_{field}'))
    result['s_section_executable_count'] = float(sum('x' in str(item.get('flags', '')).lower() for item in sections))
    result['s_section_writable_count'] = float(sum('w' in str(item.get('flags', '')).lower() for item in sections))
    result.update(_summary([item.get('entropy') for item in resources], 's_resource_entropy'))
    import_tokens = []
    for item in imports:
        library = str(item.get('library_name') or '').lower()
        if library:
            import_tokens.append('lib:' + library)
        import_tokens.extend('api:' + str(name).lower() for name in item.get('imported_functions') or [])
    categorical = [f"machine:{pe.get('machine_type')}", f"type:{selected.get('type_tag')}"]
    categorical.extend('section:' + str(item.get('name') or '').lower() for item in sections)
    categorical.extend('resource:' + str(item.get('type') or '').lower() for item in resources)
    result.update(_hash_counts(import_tokens, 's_import_hash', 128))
    result.update(_hash_counts(categorical, 's_structure_hash', 32))
    return result


def _read_vt(path):
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        return json.load(stream)


def collect_vt(cohort, out, limit=None, seed=2026, requests_per_minute=4.0,
               api_key_env='VT_API_KEY', max_new=None):
    """Fetch metadata by hash with a resumable cache; never request file bytes."""
    cohort, out = Path(cohort).resolve(), Path(out)
    require(cohort.is_file(), f'Missing cohort manifest: {cohort}')
    require(requests_per_minute > 0, 'requests_per_minute must be positive.')
    require(max_new is None or max_new > 0, 'max_new must be positive when supplied.')
    api_key = os.environ.get(api_key_env)
    require(bool(api_key), f'Missing environment secret: {api_key_env}')
    out.mkdir(parents=True, exist_ok=True)
    raw = out / 'raw_vt_file_metadata'
    raw.mkdir(exist_ok=True)
    frame = pd.read_csv(cohort, dtype={'sha256': str})
    require({'row_id', 'sha256', 'label'} <= set(frame), 'Invalid cohort manifest.')
    if limit is not None:
        require(limit >= 2, 'Pilot limit must be at least two.')
        pieces = []
        labels = sorted(frame.label.unique())
        base, remainder = divmod(limit, len(labels))
        for order, label in enumerate(labels):
            group = frame[frame.label == label]
            take = min(len(group), base + (1 if order < remainder else 0))
            pieces.append(group.sample(n=take, random_state=seed + int(label)))
        frame = pd.concat(pieces).sort_values('row_id').reset_index(drop=True)
    frame.to_csv(out / 'selected_cohort.csv', index=False)
    interval = 60.0 / requests_per_minute
    records = []
    last_request = None
    new_requests = 0
    fetched_requests = 0
    rate_limit_encountered = False
    invocation_started = datetime.now(timezone.utc).isoformat()
    history_path = out / 'request_history.csv'
    for item in frame.itertuples(index=False):
        target = raw / f'{item.sha256}.json.gz'
        if target.is_file():
            try:
                response = _read_vt(target)
                status, detail = 'cached', 'ok'
                require(response.get('data', {}).get('attributes', {}).get('sha256') == item.sha256,
                        f'Cached VirusTotal SHA mismatch: {item.sha256}')
            except Exception as error:
                target.unlink(missing_ok=True)
                status, detail = 'cache_invalid', f'{type(error).__name__}: {error}'
        else:
            if rate_limit_encountered:
                records.append({'row_id': int(item.row_id), 'sha256': item.sha256,
                                'label': int(item.label), 'status': 'deferred_rate_limit',
                                'retrieved_at_utc': None,
                                'detail': 'Not requested after VirusTotal returned HTTP 429.'})
                continue
            if max_new is not None and new_requests >= max_new:
                records.append({'row_id': int(item.row_id), 'sha256': item.sha256,
                                'label': int(item.label), 'status': 'deferred_quota',
                                'retrieved_at_utc': None,
                                'detail': 'Not requested in this invocation because --max-new was reached.'})
                continue
            if last_request is not None:
                time.sleep(max(0.0, interval - (time.monotonic() - last_request)))
            request = urllib.request.Request(
                'https://www.virustotal.com/api/v3/files/' + item.sha256,
                headers={'x-apikey': api_key, 'Accept': 'application/json'})
            try:
                last_request = time.monotonic()
                new_requests += 1
                with urllib.request.urlopen(request, timeout=45) as stream:
                    response = json.load(stream)
                require(response.get('data', {}).get('attributes', {}).get('sha256') == item.sha256,
                        f'VirusTotal SHA mismatch: {item.sha256}')
                with gzip.open(target, 'wt', encoding='utf-8') as stream:
                    json.dump(response, stream, ensure_ascii=False, separators=(',', ':'))
                status, detail = 'fetched', 'ok'
                fetched_requests += 1
            except urllib.error.HTTPError as error:
                status, detail = f'http_{error.code}', error.read(500).decode('utf-8', 'replace')
                rate_limit_encountered = error.code == 429
            except Exception as error:
                status, detail = 'error', f'{type(error).__name__}: {error}'
            attempt = pd.DataFrame([{
                'invocation_started_at_utc': invocation_started,
                'attempted_at_utc': datetime.now(timezone.utc).isoformat(),
                'row_id': int(item.row_id), 'sha256': item.sha256,
                'label': int(item.label), 'status': status, 'detail': detail,
            }])
            attempt.to_csv(history_path, mode='a', header=not history_path.is_file(), index=False)
        retrieved_at = (datetime.fromtimestamp(target.stat().st_mtime, timezone.utc).isoformat()
                        if target.is_file() else None)
        records.append({'row_id': int(item.row_id), 'sha256': item.sha256,
                        'label': int(item.label), 'status': status,
                        'retrieved_at_utc': retrieved_at, 'detail': detail})
        pd.DataFrame(records).to_csv(out / 'request_log.csv', index=False)

    pd.DataFrame(records).to_csv(out / 'request_log.csv', index=False)

    features = []
    for item in frame.itertuples(index=False):
        target = raw / f'{item.sha256}.json.gz'
        if not target.is_file():
            continue
        response = _read_vt(target)
        row = {'row_id': int(item.row_id), 'sha256': item.sha256, 'label': int(item.label)}
        row.update(safe_static_features(response))
        features.append(row)
    feature_frame = pd.DataFrame(features).sort_values('row_id') if features else pd.DataFrame()
    require(len(feature_frame) > 0, 'No usable VirusTotal metadata was collected.')
    feature_frame.to_csv(out / 'static_features.csv.gz', index=False, compression='gzip')
    selected_rows = int(len(frame))
    summary = {
        'status': 'vt_metadata_collected', 'cohort_manifest': str(cohort),
        'cohort_manifest_sha256': sha256(cohort), 'requested_rows': selected_rows,
        'usable_rows': int(len(feature_frame)), 'coverage': float(len(feature_frame) / selected_rows),
        'usable_class_counts': _counts(feature_frame.label),
        'api_endpoint': 'GET /api/v3/files/{sha256}',
        'binary_downloaded': False, 'safe_top_level_allowlist': sorted(SAFE_VT_TOP_LEVEL),
        'explicitly_excluded_fields': EXCLUDED_VT_FIELDS,
        'feature_count': int(len([name for name in feature_frame if name.startswith('s_')])),
        'requests_per_minute': float(requests_per_minute),
        'new_requests_this_invocation': int(new_requests),
        'successful_fetches_this_invocation': int(fetched_requests),
        'rate_limit_encountered': bool(rate_limit_encountered),
        'request_history': str(history_path.resolve()),
        'max_new': None if max_new is None else int(max_new),
        'limitations': [
            'VirusTotal metadata availability can create missingness; coverage is reported before modeling.',
            'Raw API responses may contain AV verdicts for audit, but feature extraction uses an explicit structural allow-list.',
            'No executable content endpoint is called by this collector.',
        ],
    }
    write_json(out / 'collection_summary.json', summary)
    write_json(out / 'feature_schema.json', {
        'identity': ['row_id', 'sha256', 'label'],
        'features': [name for name in feature_frame if name.startswith('s_')],
        'allowlist': sorted(SAFE_VT_TOP_LEVEL), 'excluded': EXCLUDED_VT_FIELDS,
    })
    return summary


def audit_collection(cohort, collection, min_coverage=.9):
    """Audit a resumable VT collection without issuing any network request."""
    cohort, collection = Path(cohort).resolve(), Path(collection)
    require(cohort.is_file(), f'Missing cohort manifest: {cohort}')
    require(0 < min_coverage <= 1, 'min_coverage must be in (0, 1].')
    feature_path = collection / 'static_features.csv.gz'
    log_path = collection / 'request_log.csv'
    require(feature_path.is_file() and log_path.is_file(),
            'Collection requires static_features.csv.gz and request_log.csv.')
    expected = pd.read_csv(cohort, dtype={'sha256': str})
    features = pd.read_csv(feature_path, dtype={'sha256': str})
    request_log = pd.read_csv(log_path, dtype={'sha256': str})
    required = {'row_id', 'sha256', 'label', 'outer_fold'}
    require(required <= set(expected), 'Cohort manifest lacks identity/fold columns.')
    require({'row_id', 'sha256', 'label'} <= set(features), 'Invalid static feature table.')
    require({'row_id', 'sha256', 'label', 'status'} <= set(request_log), 'Invalid request log.')
    require(expected.row_id.is_unique and expected.sha256.is_unique, 'Cohort identities must be unique.')
    require(features.row_id.is_unique and features.sha256.is_unique, 'Feature identities must be unique.')
    require(request_log.row_id.is_unique and request_log.sha256.is_unique,
            'Request log must contain one final status per cohort identity.')
    require(len(request_log) == len(expected), 'Request log must cover the complete cohort.')
    identity = expected[['row_id', 'sha256', 'label']].merge(
        features[['row_id', 'sha256', 'label']], on=['row_id', 'sha256', 'label'],
        how='inner', validate='one_to_one')
    require(len(identity) == len(features), 'Static features include identities outside the cohort.')
    usable_ids = set(features.row_id)
    expected = expected.copy()
    expected['usable'] = expected.row_id.isin(usable_ids)
    rows = []
    for (fold, label), group in expected.groupby(['outer_fold', 'label'], sort=True):
        usable = int(group.usable.sum())
        rows.append({'outer_fold': int(fold), 'label': int(label),
                     'cohort_rows': int(len(group)), 'usable_rows': usable,
                     'remaining_rows': int(len(group) - usable),
                     'coverage': float(usable / len(group))})
    coverage_frame = pd.DataFrame(rows)
    coverage_frame.to_csv(collection / 'coverage_by_fold_label.csv', index=False)
    status_counts = {str(k): int(v) for k, v in request_log.status.value_counts().items()}
    deferred = int(request_log.status.astype(str).str.startswith('deferred_').sum())
    total, usable = int(len(expected)), int(len(features))
    target_rows = int(np.ceil(min_coverage * total))
    coverage = usable / total
    if deferred:
        status = 'collection_incomplete'
    elif coverage >= min_coverage:
        status = 'collection_complete_ready_for_confirmatory'
    else:
        status = 'collection_complete_below_coverage_threshold'
    history_path = collection / 'request_history.csv'
    history_counts = {}
    if history_path.is_file():
        history = pd.read_csv(history_path)
        history_counts = {str(k): int(v) for k, v in history.status.value_counts().items()}
    audit = {
        'status': status, 'network_requests_issued': False,
        'cohort_rows': total, 'usable_rows': usable, 'coverage': float(coverage),
        'minimum_coverage': float(min_coverage), 'target_usable_rows': target_rows,
        'additional_usable_rows_needed': int(max(0, target_rows - usable)),
        'deferred_rows': deferred, 'request_status_counts': status_counts,
        'recorded_network_attempt_status_counts': history_counts,
        'class_coverage': {
            str(label): {
                'cohort_rows': int(len(group)), 'usable_rows': int(group.usable.sum()),
                'coverage': float(group.usable.mean()),
            } for label, group in expected.groupby('label', sort=True)
        },
        'fold_label_coverage_file': 'coverage_by_fold_label.csv',
        'cohort_manifest_sha256': sha256(cohort),
        'static_features_sha256': sha256(feature_path),
        'request_log_sha256': sha256(log_path),
        'binary_downloaded': False,
        'decision': ('Do not run confirmatory modeling while collection is incomplete.'
                     if deferred else
                     'Run confirmatory modeling.' if coverage >= min_coverage else
                     'Do not use as primary PID evidence; final coverage is below threshold.'),
    }
    write_json(collection / 'coverage_audit.json', audit)
    return audit


def _load_sequences(path):
    frame = pd.read_csv(path, dtype={'sha256': str})
    require({'row_id', 'sha256', 'label', 'outer_fold', 'api_sequence_json'} <= set(frame),
            'Invalid prepared API sequence table.')
    frame['api_sequence'] = frame.api_sequence_json.map(json.loads)
    return frame


def _platt_fit(scores, labels):
    model = LogisticRegression(solver='lbfgs', max_iter=1000, random_state=2026)
    model.fit(np.asarray(scores).reshape(-1, 1), np.asarray(labels, dtype=int))
    return model


def _platt_predict(model, scores):
    return model.predict_proba(np.asarray(scores).reshape(-1, 1))[:, 1]


def _prefix_examples(frame, windows):
    texts, labels, owners, counts = [], [], [], []
    for item in frame.itertuples(index=False):
        for count in windows:
            texts.append(' '.join(item.api_sequence[:count]))
            labels.append(int(item.label)); owners.append(int(item.row_id)); counts.append(int(count))
    return texts, np.asarray(labels), np.asarray(owners), np.asarray(counts)


def _fusion_frame(frame, p_static, vectorizer, dynamic_model, dynamic_calibrator, windows):
    rows = []
    for position, item in enumerate(frame.itertuples(index=False)):
        texts = [' '.join(item.api_sequence[:count]) for count in windows]
        raw_dynamic = dynamic_model.decision_function(vectorizer.transform(texts))
        dynamic = _platt_predict(dynamic_calibrator, raw_dynamic)
        for step, (count, probability) in enumerate(zip(windows, dynamic)):
            rows.append({
                'row_id': int(item.row_id), 'sha256': item.sha256,
                'execution_id': f'public_report_{item.sha256}', 'time_step': step,
                'event_count': float(count), 'label': int(item.label),
                'probability': float(p_static[position]), 'p_dynamic': float(probability),
            })
    return pd.DataFrame(rows)


def _final_rows(frame):
    return frame.sort_values(['row_id', 'event_count']).groupby('row_id', sort=False).tail(1)


def _bootstrap_difference(final, left='PID', right='Fixed_weight', iterations=1000, seed=2026):
    pivot_score = final.pivot(index='row_id', columns='fusion', values='score')
    pivot_label = final.pivot(index='row_id', columns='fusion', values='predicted_label')
    labels = final.drop_duplicates('row_id').set_index('row_id').label.loc[pivot_score.index].to_numpy()
    left_scores, right_scores = pivot_score[left].to_numpy(), pivot_score[right].to_numpy()
    left_predictions = pivot_label.loc[pivot_score.index, left].to_numpy(dtype=int)
    right_predictions = pivot_label.loc[pivot_score.index, right].to_numpy(dtype=int)
    rng = np.random.default_rng(seed)
    values = {'auc': [], 'ap': [], 'brier': [], 'fpr': [], 'tpr': []}
    for _ in range(iterations):
        ids = rng.integers(0, len(labels), len(labels))
        if len(np.unique(labels[ids])) < 2:
            continue
        sampled_labels = labels[ids]
        values['auc'].append(roc_auc_score(sampled_labels, left_scores[ids]) -
                             roc_auc_score(sampled_labels, right_scores[ids]))
        values['ap'].append(average_precision_score(sampled_labels, left_scores[ids]) -
                            average_precision_score(sampled_labels, right_scores[ids]))
        values['brier'].append(brier_score_loss(sampled_labels, left_scores[ids]) -
                               brier_score_loss(sampled_labels, right_scores[ids]))
        negative, positive = sampled_labels == 0, sampled_labels == 1
        values['fpr'].append(left_predictions[ids][negative].mean() -
                             right_predictions[ids][negative].mean())
        values['tpr'].append(left_predictions[ids][positive].mean() -
                             right_predictions[ids][positive].mean())
    result = {
        metric: {'mean': float(np.mean(samples)),
                 'ci95_low': float(np.quantile(samples, .025)),
                 'ci95_high': float(np.quantile(samples, .975)), 'iterations': len(samples)}
        for metric, samples in values.items()
    }
    return {
        'comparison': f'{left}_minus_{right}',
        'interpretation': {
            'auc': 'positive_favors_left', 'ap': 'positive_favors_left',
            'brier': 'negative_favors_left', 'fpr': 'negative_favors_left',
            'tpr': 'positive_favors_left',
        },
        'samples': int(len(labels)), 'metrics': result,
    }


def _timepoint_metrics(predictions):
    """Return fold-level and pooled out-of-fold ranking/calibration metrics."""
    rows = []
    for (fold, fusion, event_count), group in predictions.groupby(
            ['outer_fold', 'fusion', 'event_count'], sort=True):
        rows.append({
            'outer_fold': int(fold), 'fusion': fusion,
            'event_count': int(event_count), 'samples': int(len(group)),
            'auc': float(roc_auc_score(group.label, group.score)),
            'ap': float(average_precision_score(group.label, group.score)),
            'brier': float(brier_score_loss(group.label, group.score)),
        })
    pooled = []
    for (fusion, event_count), group in predictions.groupby(['fusion', 'event_count'], sort=True):
        pooled.append({
            'fusion': fusion, 'event_count': int(event_count),
            'samples': int(len(group)),
            'auc': float(roc_auc_score(group.label, group.score)),
            'ap': float(average_precision_score(group.label, group.score)),
            'brier': float(brier_score_loss(group.label, group.score)),
        })
    return pd.DataFrame(rows), pd.DataFrame(pooled)


def _fold_effects(metrics, left='PID', right='Fixed_weight'):
    """Compute paired outer-fold effects; positive is a literal left-minus-right delta."""
    rows = []
    for fold, group in metrics.groupby('outer_fold', sort=True):
        indexed = group.set_index('fusion')
        require({left, right} <= set(indexed.index), f'Missing paired methods in fold {fold}.')
        for metric in ['auc', 'ap', 'fpr', 'tpr', 'brier']:
            rows.append({
                'outer_fold': int(fold), 'metric': metric,
                'left': left, 'right': right,
                'left_value': float(indexed.loc[left, metric]),
                'right_value': float(indexed.loc[right, metric]),
                'difference_left_minus_right': float(indexed.loc[left, metric] - indexed.loc[right, metric]),
                'lower_is_better': metric in {'fpr', 'brier'},
            })
    return pd.DataFrame(rows)


def _win_tie_loss(effects, tolerance=1e-12):
    result = {}
    for metric, group in effects.groupby('metric'):
        difference = group.difference_left_minus_right.to_numpy()
        favorable = -difference if bool(group.lower_is_better.iloc[0]) else difference
        result[metric] = {
            'pid_better_folds': int(np.sum(favorable > tolerance)),
            'tied_folds': int(np.sum(np.abs(favorable) <= tolerance)),
            'pid_worse_folds': int(np.sum(favorable < -tolerance)),
            'folds': int(len(group)),
        }
    return result


def run_event_pid(sequences, static_features, out, windows=(5, 10, 15, 20),
                  target_tpr=.95, min_coverage=.8, validation_fraction=.2,
                  calibration_fraction=.2, bootstrap=1000, seed=2026,
                  selection=None):
    """Run five-fold, leakage-controlled event-indexed PID ablations."""
    sequences, static_features, out = Path(sequences), Path(static_features), Path(out)
    windows = tuple(int(value) for value in windows)
    require(len(windows) >= 2 and list(windows) == sorted(set(windows)) and min(windows) > 0,
            'Event windows must be unique, positive and increasing.')
    require(0 <= min_coverage <= 1, 'Invalid minimum coverage.')
    require(0 < validation_fraction < .5 and 0 < calibration_fraction < .5,
            'Invalid development split fractions.')
    out.mkdir(parents=True, exist_ok=False)
    sequence_frame = _load_sequences(sequences)
    selection_metadata = None
    if selection is not None:
        selection = Path(selection).resolve()
        selected = pd.read_csv(selection, dtype={'sha256': str})
        require({'row_id', 'sha256', 'label'} <= set(selected),
                'Selection manifest requires row_id, sha256 and label.')
        require(selected.row_id.is_unique and selected.sha256.is_unique,
                'Selection manifest identities must be unique.')
        expected = selected[['row_id', 'sha256', 'label']]
        sequence_frame = sequence_frame.merge(expected, on=['row_id', 'sha256', 'label'],
                                              how='inner', validate='one_to_one')
        require(len(sequence_frame) == len(selected),
                'Selection manifest contains identities absent from the sequence table.')
        selection_metadata = {'path': str(selection), 'sha256': sha256(selection),
                              'rows': int(len(selected))}
    static = pd.read_csv(static_features, dtype={'sha256': str})
    require({'row_id', 'sha256', 'label'} <= set(static), 'Invalid static feature table.')
    static_columns = [name for name in static if name.startswith('s_')]
    require(static_columns, 'No allow-listed static features found.')
    joined = sequence_frame.merge(static, on=['row_id', 'sha256', 'label'], how='inner', validate='one_to_one')
    coverage = len(joined) / len(sequence_frame)
    require(coverage >= min_coverage, f'Static metadata coverage {coverage:.3f} is below {min_coverage:.3f}.')
    require((joined.api_sequence.map(len) >= max(windows)).all(), 'Some traces are shorter than the final event window.')
    folds = sorted(joined.outer_fold.unique())
    require(len(folds) >= 2, 'At least two outer folds are required.')
    kinds = ['Static_only', 'Dynamic_only', 'Average_50_50', 'Fixed_weight', 'P', 'PI', 'PID']
    metrics, predictions, searches = [], [], []

    for fold in folds:
        development = joined[joined.outer_fold != fold].copy()
        test = joined[joined.outer_fold == fold].copy()
        train_cal, validation = train_test_split(
            development, test_size=validation_fraction, random_state=seed + int(fold),
            stratify=development.label)
        model_train, calibration = train_test_split(
            train_cal, test_size=calibration_fraction, random_state=seed + 100 + int(fold),
            stratify=train_cal.label)
        for subset in [model_train, calibration, validation, test]:
            require(set(subset.label) == {0, 1}, f'Fold {fold} contains a single-class partition.')

        static_model = make_pipeline(
            SimpleImputer(strategy='median'), StandardScaler(),
            LogisticRegression(max_iter=2000, class_weight='balanced', random_state=seed + int(fold)))
        static_model.fit(model_train[static_columns], model_train.label)
        static_calibrator = _platt_fit(static_model.decision_function(calibration[static_columns]), calibration.label)
        p_static_validation = _platt_predict(static_calibrator, static_model.decision_function(validation[static_columns]))
        p_static_test = _platt_predict(static_calibrator, static_model.decision_function(test[static_columns]))

        train_text, train_y, _, _ = _prefix_examples(model_train, windows)
        calibration_text, calibration_y, _, _ = _prefix_examples(calibration, windows)
        vectorizer = TfidfVectorizer(token_pattern=r'[^ ]+', lowercase=False, ngram_range=(1, 2),
                                     min_df=2, max_features=10000, sublinear_tf=True)
        train_x = vectorizer.fit_transform(train_text)
        dynamic_model = LogisticRegression(max_iter=2000, class_weight='balanced', random_state=seed + int(fold))
        dynamic_model.fit(train_x, train_y)
        dynamic_calibrator = _platt_fit(
            dynamic_model.decision_function(vectorizer.transform(calibration_text)), calibration_y)
        validation_frame = _fusion_frame(
            validation, p_static_validation, vectorizer, dynamic_model, dynamic_calibrator, windows)
        test_frame = _fusion_frame(test, p_static_test, vectorizer, dynamic_model, dynamic_calibrator, windows)

        settings = {'Static_only': 1., 'Dynamic_only': 0., 'Average_50_50': .5}
        for kind in ['Fixed_weight', 'P', 'PI', 'PID']:
            setting, trials = select_on_validation(validation_frame, kind, target_tpr)
            settings[kind] = setting
            searches.append({'outer_fold': int(fold), 'fusion': kind,
                             'selected': setting, 'trials': trials})
        for kind in kinds:
            validation_trajectory = score_trajectory(validation_frame, kind, settings[kind])
            test_trajectory = score_trajectory(test_frame, kind, settings[kind])
            final_validation, final_test = _final_rows(validation_trajectory), _final_rows(test_trajectory)
            threshold = choose_threshold(final_validation.label, final_validation.score, target_tpr)
            measured = evaluate(final_test.label, final_test.score, threshold)
            extra = low_fpr_metrics(final_validation.label, final_validation.score,
                                    final_test.label, final_test.score)
            metrics.append({
                'outer_fold': int(fold), 'fusion': kind,
                'selected_setting': json.dumps(settings[kind]), 'threshold': threshold,
                'brier': float(brier_score_loss(final_test.label, final_test.score)),
                **measured, **extra,
            })
            test_trajectory = test_trajectory.copy()
            test_trajectory['outer_fold'] = int(fold); test_trajectory['fusion'] = kind
            test_trajectory['threshold'] = threshold
            test_trajectory['predicted_label'] = (test_trajectory.score >= threshold).astype(int)
            predictions.append(test_trajectory)

    metric_frame = pd.DataFrame(metrics)
    prediction_frame = pd.concat(predictions, ignore_index=True)
    final = (prediction_frame.sort_values(['row_id', 'event_count'])
             .groupby(['outer_fold', 'fusion', 'row_id'], sort=False).tail(1))
    # Replay every fold/method metric from the persisted prediction-level representation.
    replayed = 0
    for item in metric_frame.itertuples(index=False):
        selected = final[(final.outer_fold == item.outer_fold) & (final.fusion == item.fusion)]
        check = evaluate(selected.label, selected.score, item.threshold)
        for metric in ['auc', 'ap', 'fpr', 'tpr', 'tn', 'fp', 'fn', 'tp']:
            require(np.isclose(check[metric], getattr(item, metric)), f'Replay mismatch: fold={item.outer_fold}, {item.fusion}, {metric}')
        replayed += len(selected)
    metric_frame.to_csv(out / 'fusion_metrics.csv', index=False)
    prediction_frame.to_csv(out / 'event_predictions.csv.gz', index=False, compression='gzip')
    timepoint_frame, pooled_timepoint_frame = _timepoint_metrics(prediction_frame)
    timepoint_frame.to_csv(out / 'timepoint_metrics.csv', index=False)
    pooled_timepoint_frame.to_csv(out / 'timepoint_oof_metrics.csv', index=False)
    fold_effects = _fold_effects(metric_frame)
    fold_effects.to_csv(out / 'fold_effects_pid_minus_fixed.csv', index=False)
    write_json(out / 'validation_search.json', searches)
    effects = _bootstrap_difference(final, iterations=bootstrap, seed=seed)
    write_json(out / 'paired_bootstrap_pid_minus_fixed.json', effects)
    summary = {
        'status': 'measured_from_public_ordered_api_reports',
        'samples': int(len(joined)), 'static_metadata_coverage': float(coverage),
        'selection': selection_metadata,
        'class_counts': _counts(joined.label), 'outer_folds': int(len(folds)),
        'event_windows': list(windows), 'time_axis': 'ordered_api_event_count',
        'results': [
            {'fusion': kind, **{metric: stats(group[metric]) for metric in ['auc', 'ap', 'fpr', 'tpr', 'brier']}}
            for kind, group in metric_frame.groupby('fusion')
        ],
        'paired_bootstrap_pid_minus_fixed': effects,
        'fold_win_tie_loss_pid_vs_fixed': _win_tie_loss(fold_effects),
        'limitations': [
            'Event count is a discrete observation axis, not wall-clock time or measured sandbox latency.',
            'MalBehavD-V1 supports generic binary Windows malware detection, not ransomware-specific claims.',
            'Static fields are allow-listed VirusTotal PE metadata; source-collection bias remains possible.',
        ],
        **source_metadata(),
    }
    write_json(out / 'summary.json', summary)
    write_json(out / 'verification.json', {
        'status': 'passed', 'metric_rows_replayed': int(len(metric_frame)),
        'prediction_rows_checked': int(replayed), 'no_executable_downloaded': True,
        'static_feature_prefix_enforced': True,
    })
    (out / 'REPORT.md').write_text(
        '# Event-indexed PID benchmark\n\n'
        'Static, Dynamic, Average, Fixed, P, PI and PID are compared with five frozen outer folds. '
        'Base models, calibration and fusion validation use disjoint development partitions. '
        'The observation axis is ordered API-event count, not seconds. '
        'See timepoint_metrics.csv for fold-level trajectories, timepoint_oof_metrics.csv for pooled '
        'out-of-fold trajectories, fold_effects_pid_minus_fixed.csv for paired fold effects, and '
        'paired_bootstrap_pid_minus_fixed.json for uncertainty intervals.\n', encoding='utf-8')
    return summary
