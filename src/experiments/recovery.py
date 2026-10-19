"""Recover source row IDs and optional JSONL metadata for a shuffled mini CSV."""
import hashlib
import json
from pathlib import Path
import zipfile

import numpy as np
import numpy.lib.format as npformat
import pandas as pd

from .common import require, sha256, write_json


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
    result = {'path': str(path), 'size_bytes': path.stat().st_size, 'arrays': arrays,
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
    out.mkdir(parents=True, exist_ok=False)
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
