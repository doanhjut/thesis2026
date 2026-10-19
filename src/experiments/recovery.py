"""Recover source row IDs and optional JSONL metadata for a shuffled mini CSV."""
import hashlib
import json
from pathlib import Path
import sqlite3
import zipfile

import numpy as np
import numpy.lib.format as npformat
import pandas as pd

from .common import require, sha256, write_json


SOREL_TEST_SPLIT = 1547279640.0
SOREL_TAGS = [
    'adware', 'flooder', 'ransomware', 'dropper', 'spyware', 'packed',
    'crypto_miner', 'file_infector', 'installer', 'worm', 'downloader',
]


def _header(stream):
    version = npformat.read_magic(stream)
    try:
        return npformat._read_array_header(stream, version)
    except AttributeError:
        return (npformat.read_array_header_1_0(stream) if version == (1, 0)
                else npformat.read_array_header_2_0(stream))


def inspect_npz(path, hash_source=False):
    path = Path(path).resolve()
    require(path.suffix.lower() == '.npz' and path.is_file(), 'Source must be an existing NPZ file.')
    arrays = []
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if not name.endswith('.npy'):
                continue
            with archive.open(name) as stream:
                shape, fortran, dtype = _header(stream)
            arrays.append({'entry': name, 'shape': list(map(int, shape)), 'fortran_order': bool(fortran), 'dtype': str(dtype)})
    require(any(len(item['shape']) == 1 for item in arrays) and any(len(item['shape']) == 2 for item in arrays),
            'Expected one label vector and one feature matrix in NPZ.')
    feature_info = next(item for item in arrays if len(item['shape']) == 2)
    label_info = next(item for item in arrays if len(item['shape']) == 1)
    require(feature_info['shape'][0] == label_info['shape'][0], 'Feature and label row counts differ in NPZ.')
    label_key = label_info['entry'][:-4] if label_info['entry'].endswith('.npy') else label_info['entry']
    with np.load(path) as source:
        labels = np.asarray(source[label_key]).ravel()
    values, counts = np.unique(labels, return_counts=True)
    result = {'path': str(path), 'size_bytes': path.stat().st_size, 'arrays': arrays,
              'feature_entry': feature_info['entry'], 'label_entry': label_info['entry'],
              'rows': int(feature_info['shape'][0]), 'features': int(feature_info['shape'][1]),
              'label_counts': {str(value.item() if hasattr(value, 'item') else value): int(count)
                               for value, count in zip(values, counts)},
              'source_sha256': sha256(path) if hash_source else None,
              'source_sha256_status': 'computed' if hash_source else 'skipped; use --hash-source for the frozen manifest'}
    return result


def _array_names(path):
    info = inspect_npz(path)
    feature = next(item['entry'] for item in info['arrays'] if len(item['shape']) == 2)
    label = next(item['entry'] for item in info['arrays'] if len(item['shape']) == 1)
    return feature, label, info


def _load_labels(path, label_entry):
    key = label_entry[:-4] if label_entry.endswith('.npy') else label_entry
    with np.load(path) as source:
        return np.asarray(source[key]).ravel()


def sampled_source_indices(labels, n_negative=1500, n_positive=500, seed=42):
    labels = np.asarray(labels).astype(int)
    negative, positive = np.flatnonzero(labels == 0), np.flatnonzero(labels == 1)
    require(len(negative) >= n_negative and len(positive) >= n_positive,
            f'Source does not contain requested class counts: need {n_negative} label-0 and {n_positive} label-1 rows.')
    rng = np.random.default_rng(seed)
    selected = np.r_[rng.choice(negative, n_negative, replace=False),
                     rng.choice(positive, n_positive, replace=False)]
    return np.asarray(sorted(map(int, selected)), dtype=np.int64)


def _stream_rows(path, feature_entry, selected):
    wanted, collected, source_rows = set(map(int, selected)), [], []
    maximum = int(np.max(selected))
    with zipfile.ZipFile(path) as archive, archive.open(feature_entry) as stream:
        shape, fortran, dtype = _header(stream)
        require(not fortran, 'Fortran-order source is not supported by the memory-safe row streamer.')
        n_rows, n_features = map(int, shape)
        require(maximum < n_rows, 'Selected source index exceeds the feature matrix.')
        row_bytes, chunk_rows, position = n_features * dtype.itemsize, 20_000, 0
        while position <= maximum:
            raw = stream.read(row_bytes * chunk_rows)
            require(raw, 'Feature stream ended before selected rows were recovered.')
            rows = len(raw) // row_bytes
            require(rows > 0 and len(raw) == rows * row_bytes, 'Partial feature row encountered in NPZ stream.')
            values = np.frombuffer(raw, dtype=dtype).reshape(rows, n_features)
            for local, source_index in enumerate(range(position, position + rows)):
                if source_index in wanted:
                    source_rows.append(source_index)
                    collected.append(values[local].copy())
            position += rows
    require(source_rows == selected.tolist(), 'Recovered NPZ row order differs from selected indices.')
    return np.vstack(collected)


def _final_shuffle_order(size, seed):
    return pd.DataFrame({'position': np.arange(size)}).sample(frac=1, random_state=seed).position.to_numpy()


def _metadata_for_indices(paths, selected):
    selected_set, maximum = set(map(int, selected)), int(np.max(selected))
    found, global_index = {}, 0
    for path in map(Path, paths):
        with path.open('r', encoding='utf-8') as stream:
            for line in stream:
                if global_index in selected_set:
                    obj = json.loads(line)
                    found[global_index] = {key: obj.get(key) for key in ['sha256', 'appeared', 'label', 'avclass']}
                global_index += 1
                if global_index > maximum:
                    break
        if global_index > maximum:
            break
    require(len(found) == len(selected),
            f'Metadata JSONL ended or is misaligned: found {len(found)}/{len(selected)} selected source rows.')
    return found, global_index


def _feature_digest(row):
    canonical = np.asarray(row, dtype='<f8')
    return hashlib.sha256(canonical.tobytes()).hexdigest()


def recover(source, mini, out, metadata_jsonl=None, n_negative=1500, n_positive=500,
            seed=42, hash_source=False, rtol=1e-6, atol=1e-8):
    source, mini, out = Path(source).resolve(), Path(mini).resolve(), Path(out)
    if out.exists():
        require(out.is_dir() and not any(out.iterdir()), 'Output directory must be new or empty.')
    else:
        out.mkdir(parents=True)
    feature_entry, label_entry, inspection = _array_names(source)
    if hash_source:
        inspection = inspect_npz(source, hash_source=True)
    labels = _load_labels(source, label_entry)
    inspection['label_counts'] = {str(value): int(np.sum(labels == value)) for value in np.unique(labels)}
    write_json(out / 'source_inspection.json', inspection)
    selected = sampled_source_indices(labels, n_negative, n_positive, seed)
    recovered = _stream_rows(source, feature_entry, selected)
    permutation = _final_shuffle_order(len(selected), seed)
    source_indices = selected[permutation]
    recovered = recovered[permutation]
    recovered_labels = labels[source_indices].astype(int)
    frame = pd.read_csv(mini, encoding='utf-8-sig')
    require('label' in frame, 'Mini CSV requires the exact label column used by the measured runner.')
    mini_features = frame.drop(columns='label').to_numpy(dtype=float)
    mini_labels = frame.label.to_numpy(dtype=int)
    require(mini_features.shape == recovered.shape, f'Feature shape mismatch: mini={mini_features.shape}, recovered={recovered.shape}.')
    require(np.array_equal(mini_labels, recovered_labels), 'Labels do not match the reconstructed sample/shuffle order.')
    differences = np.abs(mini_features - recovered)
    matching_rows = np.all(np.isclose(mini_features, recovered, rtol=rtol, atol=atol), axis=1)
    require(matching_rows.all(), f'{int((~matching_rows).sum())} mini rows do not match recovered source features.')
    manifest = pd.DataFrame({
        'row_id': np.arange(len(frame)), 'source_index': source_indices,
        'label': mini_labels, 'feature_sha256': [_feature_digest(row) for row in mini_features],
    })
    metadata_status = 'not_supplied'
    if metadata_jsonl:
        metadata, lines_scanned = _metadata_for_indices(metadata_jsonl, selected)
        ordered = [metadata[int(index)] for index in source_indices]
        for key in ['sha256', 'appeared', 'avclass', 'label']:
            manifest['sample_' + key if key == 'label' else key] = [item.get(key) for item in ordered]
        require(manifest.sha256.notna().all() and manifest.sha256.astype(str).str.fullmatch(r'[0-9a-fA-F]{64}').all(),
                'Metadata does not provide a valid SHA-256 for every selected row.')
        require(np.array_equal(pd.to_numeric(manifest.sample_label).to_numpy(dtype=int), mini_labels),
                'Metadata labels do not align with NPZ labels; do not join these sources.')
        metadata_status = 'row_order_and_label_verified'
    else:
        lines_scanned = None
    manifest.to_csv(out / 'row_manifest.csv', index=False)
    report = {
        'status': 'recovered', 'source': str(source), 'mini': str(mini),
        'source_sha256': inspection['source_sha256'], 'mini_sha256': sha256(mini),
        'feature_entry': feature_entry, 'label_entry': label_entry,
        'sampling': {'seed': seed, 'n_label_0': n_negative, 'n_label_1': n_positive,
                     'final_shuffle': 'pandas.DataFrame.sample(frac=1, random_state=seed)'},
        'verification': {'matching_rows': int(matching_rows.sum()), 'max_absolute_feature_difference': float(differences.max()),
                         'rtol': rtol, 'atol': atol},
        'metadata_status': metadata_status, 'metadata_jsonl': [str(Path(p).resolve()) for p in metadata_jsonl or []],
        'metadata_lines_scanned': lines_scanned,
        'label_semantics': 'unverified: label 1 must not be renamed ransomware without source documentation.',
    }
    write_json(out / 'recovery_report.json', report)
    return report


def _sqlite_columns(connection, table):
    return {row[1] for row in connection.execute(f'PRAGMA table_info({table})')}


def _text_sha(value):
    if isinstance(value, bytes):
        value = value.decode('ascii')
    value = str(value)
    require(len(value) == 64 and all(char in '0123456789abcdefABCDEF' for char in value),
            f'Invalid SHA-256 value in SOREL metadata: {value!r}')
    return value.lower()


def recover_sorel_metadata(manifest, source_inspection, meta_db, missing_shas, out,
                           test_split=SOREL_TEST_SPLIT, hash_meta_db=False):
    """Map official SOREL LightGBM NPZ row indices back to meta.db records.

    The official array builder iterates the SQLite test query without shuffling and
    removes records without EMBER features. This function reproduces that order,
    checks the complete filtered row count and verifies the binary label at every
    selected source index before exporting SHA-256 and weak malware tags.
    """
    manifest, source_inspection = Path(manifest).resolve(), Path(source_inspection).resolve()
    meta_db, missing_shas, out = Path(meta_db).resolve(), Path(missing_shas).resolve(), Path(out)
    require(manifest.is_file(), 'Recovered row_manifest.csv does not exist.')
    require(source_inspection.is_file(), 'source_inspection.json does not exist.')
    require(meta_db.is_file(), 'SOREL meta.db does not exist.')
    require(missing_shas.is_file(), 'shas_missing_ember_features.json does not exist.')
    if out.exists():
        require(out.is_dir() and not any(out.iterdir()), 'Output directory must be new or empty.')
    else:
        out.mkdir(parents=True)

    rows = pd.read_csv(manifest)
    required_manifest = {'row_id', 'source_index', 'label'}
    require(required_manifest.issubset(rows.columns),
            f'Manifest requires columns {sorted(required_manifest)}.')
    require(not rows[list(required_manifest)].isna().any().any(), 'Manifest identifiers or labels contain missing values.')
    require(rows.row_id.is_unique and rows.source_index.is_unique, 'Manifest row_id and source_index must be unique.')
    require(np.array_equal(np.sort(rows.row_id.astype(int)), np.arange(len(rows))),
            'Manifest row_id must contain every integer from 0 to N-1.')
    rows['source_index'] = rows.source_index.astype(np.int64)
    rows['label'] = rows.label.astype(int)

    inspection = json.loads(source_inspection.read_text(encoding='utf-8'))
    expected_source_rows = int(inspection['rows'])
    require(rows.source_index.between(0, expected_source_rows - 1).all(),
            'Manifest source_index exceeds the inspected NPZ row range.')
    missing_values = json.loads(missing_shas.read_text(encoding='utf-8'))
    require(isinstance(missing_values, list), 'Missing-feature artifact must be a JSON list of SHA-256 strings.')
    missing = {_text_sha(value) for value in missing_values}

    connection = sqlite3.connect(f'file:{meta_db}?mode=ro', uri=True)
    try:
        columns = _sqlite_columns(connection, 'meta')
        needed = {'sha256', 'is_malware', 'rl_fs_t', *SOREL_TAGS}
        require(needed.issubset(columns), f'SOREL meta table is missing columns: {sorted(needed - columns)}')
        optional = ['rl_ls_const_positives'] if 'rl_ls_const_positives' in columns else []
        selected_columns = ['sha256', 'is_malware', 'rl_fs_t', *optional, *SOREL_TAGS]
        boundary_query = 'select sha256 from meta where(rl_fs_t = ?)'
        boundary_shas = {_text_sha(value[0]) for value in connection.execute(boundary_query, (float(test_split),))}
        # Reproduce the exact projection used by SOREL's LightGBM array builder.
        # The upstream SQL has no ORDER BY, so adding timestamp/tag columns can
        # change SQLite's selected index and therefore the iteration order.
        query = f'select sha256,is_malware from meta where(rl_fs_t >= {float(test_split)})'
        query_plan = [list(item) for item in connection.execute('explain query plan ' + query)]
        index_definitions = [
            {'name': name, 'sql': sql}
            for name, sql in connection.execute(
                "select name,sql from sqlite_master where type='index' and tbl_name='meta' order by name")
        ]
        cursor = connection.execute(query)
        targets = set(map(int, rows.source_index))
        inclusive_recovered, exclusive_recovered = {}, {}
        inclusive_index, exclusive_index, database_test_rows = 0, 0, 0
        boundary_rows_before_filter, boundary_rows_after_filter = len(boundary_shas), 0
        for sha_value, is_malware in cursor:
            database_test_rows += 1
            record = {'sha256': _text_sha(sha_value), 'is_malware': is_malware}
            on_boundary = record['sha256'] in boundary_shas
            if record['sha256'] in missing:
                continue
            if inclusive_index in targets:
                inclusive_recovered[inclusive_index] = record
            inclusive_index += 1
            if on_boundary:
                boundary_rows_after_filter += 1
                continue
            if exclusive_index in targets:
                exclusive_recovered[exclusive_index] = record
            exclusive_index += 1
    finally:
        connection.close()

    expected_labels = rows.label.to_numpy(dtype=int)

    def candidate(name, operator, count, recovered):
        complete = len(recovered) == len(rows)
        if complete:
            candidate_ordered = [recovered[int(index)] for index in rows.source_index]
            candidate_labels = np.asarray([int(item['is_malware']) for item in candidate_ordered])
            matching_labels = int(np.sum(candidate_labels == expected_labels))
        else:
            candidate_ordered, candidate_labels, matching_labels = None, None, 0
        return {
            'name': name, 'operator': operator, 'filtered_rows': int(count),
            'expected_rows': expected_source_rows, 'recovered_selected_rows': int(len(recovered)),
            'matching_selected_labels': matching_labels,
            'valid': bool(count == expected_source_rows and complete and matching_labels == len(rows)),
            '_ordered': candidate_ordered, '_labels': candidate_labels,
        }

    inclusive = candidate('inclusive_boundary', '>=', inclusive_index, inclusive_recovered)
    candidates = [inclusive]
    if not inclusive['valid'] and boundary_rows_after_filter:
        candidates.append(candidate('exclusive_boundary', '>', exclusive_index, exclusive_recovered))
    valid = [item for item in candidates if item['valid']]
    alignment_audit = {
        'status': 'aligned' if len(valid) == 1 else 'not_aligned',
        'test_split_timestamp': float(test_split),
        'database_rows_at_or_after_boundary_before_missing_filter': int(database_test_rows),
        'boundary_rows_before_missing_filter': int(boundary_rows_before_filter),
        'boundary_rows_after_missing_filter': int(boundary_rows_after_filter),
        'missing_sha_count_all_splits': int(len(missing)),
        'builder_query': query,
        'builder_query_plan': query_plan,
        'meta_index_definitions': index_definitions,
        'candidates': [{key: value for key, value in item.items() if not key.startswith('_')}
                       for item in candidates],
    }
    write_json(out / 'sorel_alignment_audit.json', alignment_audit)
    require(len(valid) == 1,
            f'Could not uniquely align SOREL metadata to NPZ: inclusive={inclusive_index}, '
            f'exclusive={exclusive_index}, boundary_after_filter={boundary_rows_after_filter}, '
            f'expected={expected_source_rows}. See sorel_alignment_audit.json.')
    chosen = valid[0]
    ordered_keys, metadata_labels = chosen['_ordered'], chosen['_labels']

    chosen_shas = [item['sha256'] for item in ordered_keys]
    metadata = {}
    connection = sqlite3.connect(f'file:{meta_db}?mode=ro', uri=True)
    try:
        for start in range(0, len(chosen_shas), 500):
            chunk = chosen_shas[start:start + 500]
            placeholders = ','.join('?' for _ in chunk)
            metadata_query = ('select ' + ','.join(selected_columns) +
                              f' from meta where sha256 in ({placeholders})')
            for values in connection.execute(metadata_query, chunk):
                record = dict(zip(selected_columns, values))
                record['sha256'] = _text_sha(record['sha256'])
                metadata[record['sha256']] = record
    finally:
        connection.close()
    require(len(metadata) == len(chosen_shas),
            f'Only recovered full SOREL metadata for {len(metadata)}/{len(chosen_shas)} selected SHA-256 values.')
    ordered = [metadata[sha] for sha in chosen_shas]

    augmented = rows.copy()
    augmented['sha256'] = [item['sha256'] for item in ordered]
    augmented['first_seen_timestamp'] = [item['rl_fs_t'] for item in ordered]
    augmented['meta_is_malware'] = metadata_labels
    if optional:
        augmented['av_positive_count'] = [item['rl_ls_const_positives'] for item in ordered]
    for tag in SOREL_TAGS:
        augmented['tag_' + tag] = [int(item[tag] is not None and float(item[tag]) != 0.0) for item in ordered]
    augmented.to_csv(out / 'sorel_row_manifest.csv', index=False)

    tag_counts = {tag: int(augmented['tag_' + tag].sum()) for tag in SOREL_TAGS}
    report = {
        'status': 'sorel_metadata_recovered',
        'inputs': {
            'row_manifest': str(manifest), 'row_manifest_sha256': sha256(manifest),
            'source_inspection': str(source_inspection), 'source_inspection_sha256': sha256(source_inspection),
            'meta_db': str(meta_db), 'meta_db_size_bytes': meta_db.stat().st_size,
            'meta_db_sha256': sha256(meta_db) if hash_meta_db else None,
            'meta_db_sha256_status': 'computed' if hash_meta_db else 'skipped; use --hash-meta-db for the frozen manifest',
            'missing_shas': str(missing_shas), 'missing_shas_sha256': sha256(missing_shas),
        },
        'official_order_replay': {
            'test_split_timestamp': float(test_split),
            'base_query': query,
            'query_plan': query_plan,
            'selected_split_operator': chosen['operator'],
            'selected_split_policy': chosen['name'],
            'database_test_rows_before_missing_filter': int(database_test_rows),
            'boundary_rows_before_missing_filter': int(boundary_rows_before_filter),
            'boundary_rows_after_missing_filter': int(boundary_rows_after_filter),
            'missing_sha_count_all_splits': int(len(missing)),
            'inclusive_rows_after_missing_filter': int(inclusive_index),
            'exclusive_rows_after_missing_filter': int(exclusive_index),
            'test_rows_after_missing_filter': int(chosen['filtered_rows']),
            'expected_npz_rows': expected_source_rows,
            'selected_rows': int(len(rows)),
            'selected_labels_matching': int(np.sum(metadata_labels == expected_labels)),
        },
        'selected_label_counts': {str(k): int(v) for k, v in augmented.label.value_counts().sort_index().items()},
        'selected_tag_counts': tag_counts,
        'ransomware_tagged_selected_rows': int(tag_counts['ransomware']),
        'label_semantics': {
            'label': 'SOREL-20M is_malware binary label',
            'tag_ransomware': 'SOREL-20M weak multi-label ransomware tag; not a verified malware-family ground truth',
        },
        'limitations': [
            'The official LightGBM NPZ contains no SHA-256 or tags; this mapping replays the official SQLite iteration and missing-feature filter.',
            'When inclusive and exclusive timestamp boundaries differ, a policy is accepted only if the complete NPZ row count and every selected binary label match; the chosen boundary is recorded in the audit.',
            'All selected binary labels and the complete filtered row count must match, but exact feature-to-SHA confirmation additionally requires the corresponding SOREL ember_features LMDB.',
            'SOREL metadata and EMBER features do not provide executable behavior traces; PID still requires paired binaries or sandbox reports.',
        ],
    }
    write_json(out / 'sorel_metadata_recovery_report.json', report)
    return report
