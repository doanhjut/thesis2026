"""Shared input, split, metric and provenance rules for the research runners."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import platform
import subprocess

import lightgbm as lgb
import numpy as np
import pandas as pd
import sklearn
from sklearn.metrics import average_precision_score, confusion_matrix, roc_auc_score
from sklearn.model_selection import train_test_split

REPO = Path(__file__).resolve().parents[2]
DEFAULT_DATA = REPO / 'data/processed/real_mini_dataset.csv'
DATA_LIMITATION = (
    'The CSV source, original file identities and ransomware-specific label semantics '
    'are not verified. Row-disjoint measurements are an internal pilot, not a '
    'verified ransomware, family-held-out or zero-day benchmark.'
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def source_metadata():
    def git(*args):
        return subprocess.check_output(['git', *args], cwd=REPO, text=True).strip()
    files = sorted((REPO / 'src/experiments').glob('*.py')) + [REPO / 'src/pid_fusion.py', REPO / 'scripts/run_experiments.py']
    return {
        'repository_commit': git('rev-parse', 'HEAD'),
        'working_tree_status': git('status', '--porcelain'),
        'source_sha256': {str(p.relative_to(REPO)): sha256(p) for p in files},
        'versions': {'python': platform.python_version(), 'numpy': np.__version__,
                     'pandas': pd.__version__, 'sklearn': sklearn.__version__, 'lightgbm': lgb.__version__},
    }


def probabilities(values):
    a = np.asarray(values, dtype=float)
    require(a.ndim == 1 and len(a) > 0 and np.isfinite(a).all(), 'Probabilities must be a finite nonempty vector.')
    require(np.all((a >= 0) & (a <= 1)), 'Scores must be in [0, 1].')
    return a


def binary_labels(values):
    a = np.asarray(values)
    require(a.ndim == 1 and set(np.unique(a)) == {0, 1}, 'Both binary classes 0 and 1 are required; do not cast fractional labels.')
    return a.astype(np.int64)


def choose_threshold(y_validation, p_validation, target=0.95):
    y = binary_labels(y_validation)
    p = probabilities(p_validation)
    require(len(y) == len(p) and 0 < target <= 1, 'Invalid validation threshold inputs.')
    positives = np.sort(p[y == 1])[::-1]
    return float(positives[math.ceil(target * len(positives)) - 1])


def choose_threshold_at_max_fpr(y_validation, p_validation, max_fpr):
    """Select a validation-only threshold with the best TPR under an FPR cap.

    The empirical FPR is discrete.  Ties are resolved by lower FPR and then a
    higher threshold, so the choice is deterministic and conservative.
    """
    y = binary_labels(y_validation)
    p = probabilities(p_validation)
    require(len(y) == len(p) and 0 <= max_fpr < 1, 'Invalid low-FPR threshold inputs.')
    top = float(np.nextafter(p.max(), np.inf))
    thresholds = np.r_[top, np.unique(p)[::-1]]
    feasible = []
    for threshold in thresholds:
        measured = evaluate(y, p, float(threshold))
        if measured['fpr'] <= max_fpr + 1e-15:
            feasible.append((measured['tpr'], -measured['fpr'], float(threshold)))
    require(feasible, 'No feasible threshold under the requested FPR cap.')
    return max(feasible)[2]


def evaluate(y, scores, threshold):
    y, p = binary_labels(y), probabilities(scores)
    require(len(y) == len(p) and np.isfinite(threshold), 'Invalid metric inputs.')
    tn, fp, fn, tp = confusion_matrix(y, p >= threshold, labels=[0, 1]).ravel()
    return {'auc': float(roc_auc_score(y, p)), 'ap': float(average_precision_score(y, p)),
            'fpr': float(fp / (fp + tn)), 'tpr': float(tp / (tp + fn)),
            'tn': int(tn), 'fp': int(fp), 'fn': int(fn), 'tp': int(tp)}


def low_fpr_metrics(y_validation, p_validation, y_test, p_test, limits=(.01, .05)):
    """Evaluate test decisions at validation-selected low-FPR operating points."""
    result = {}
    y_test, p_test = binary_labels(y_test), probabilities(p_test)
    require(len(y_test) == len(p_test), 'Invalid low-FPR test inputs.')
    for limit in limits:
        require(0 < limit < 1, 'Low-FPR limits must be in (0,1).')
        tag = f'{int(round(limit * 100)):02d}'
        threshold = choose_threshold_at_max_fpr(y_validation, p_validation, limit)
        validation = evaluate(y_validation, p_validation, threshold)
        testing = evaluate(y_test, p_test, threshold)
        result.update({
            f'threshold_at_val_fpr_{tag}': threshold,
            f'val_fpr_at_cap_{tag}': validation['fpr'],
            f'val_tpr_at_fpr_{tag}': validation['tpr'],
            f'test_fpr_at_val_cap_{tag}': testing['fpr'],
            f'test_tpr_at_val_fpr_{tag}': testing['tpr'],
        })
    result['test_standardized_pauc_fpr_05'] = float(roc_auc_score(y_test, p_test, max_fpr=.05))
    return result


@dataclass
class Dataset:
    X: np.ndarray
    y: np.ndarray
    names: list[str]
    train: np.ndarray
    validation: np.ndarray
    test: np.ndarray
    audit: dict
    identity_manifest: pd.DataFrame | None

    def save_split(self, out):
        split = np.empty(len(self.y), dtype=object)
        for name, ids in [('train_pool', self.train), ('validation', self.validation), ('test', self.test)]:
            split[ids] = name
        pd.DataFrame({'row_id': np.arange(len(self.y)), 'split': split, 'label': self.y}).to_csv(out / 'split_manifest.csv', index=False)
        write_json(out / 'splits.json', {name: ids.tolist() for name, ids in
                   [('train_pool', self.train), ('validation', self.validation), ('test', self.test)]})
        write_json(out / 'data_audit.json', self.audit)
        if self.identity_manifest is not None:
            self.identity_manifest.to_csv(out / 'source_manifest.csv', index=False)


def load_dataset(path=DEFAULT_DATA, split_seed=42, split_file=None, row_manifest=None):
    path = Path(path).resolve()
    frame = pd.read_csv(path, encoding='utf-8-sig')
    require('label' in frame.columns, 'Input requires an explicit label column; no label-column guessing.')
    y = binary_labels(frame['label'].to_numpy())
    features = frame.drop(columns='label')
    require(features.shape[1] > 0, 'No feature columns.')
    X = features.to_numpy(dtype=np.float64)
    require(np.isfinite(X).all(), 'Non-finite features: define imputation on training data before running.')
    require(not features.duplicated().any(), 'Duplicate feature vectors found. Resolve duplicates or design grouped data upstream.')
    ids = np.arange(len(y))
    if split_file:
        manifest = pd.read_csv(split_file)
        require({'row_id', 'split'} <= set(manifest), 'Split file requires row_id,split.')
        require(manifest.row_id.is_unique and set(manifest.row_id) == set(ids), 'Split file must assign every row exactly once.')
        require(set(manifest.split) == {'train_pool', 'validation', 'test'}, 'Use train_pool, validation and test split names.')
        train, val, test = [manifest.loc[manifest.split == name, 'row_id'].to_numpy(dtype=int)
                            for name in ['train_pool', 'validation', 'test']]
        split_description = {'kind': 'provided', 'sha256': sha256(split_file), 'path': str(Path(split_file).resolve())}
    else:
        develop, test = train_test_split(ids, test_size=.2, random_state=split_seed, stratify=y)
        train, val = train_test_split(develop, test_size=.25, random_state=split_seed, stratify=y[develop])
        split_description = {'kind': 'stratified_random_rows', 'seed': split_seed, 'fractions': [.6, .2, .2]}
    for subset in [train, val, test]:
        binary_labels(y[subset])
    identity, provenance_status, provenance = None, 'unverified', {}
    limitations = [DATA_LIMITATION]
    if row_manifest:
        manifest_path = Path(row_manifest).resolve()
        identity = pd.read_csv(manifest_path, dtype={'sha256': str})
        required = {'row_id', 'label', 'sha256'}
        require(required.issubset(identity.columns), f'Row manifest requires columns {sorted(required)}.')
        require(identity.row_id.is_unique and set(identity.row_id) == set(ids),
                'Row manifest must identify every dataset row exactly once.')
        identity = identity.sort_values('row_id').reset_index(drop=True)
        require(np.array_equal(identity.label.to_numpy(dtype=int), y), 'Row-manifest labels differ from dataset labels.')
        require(identity.sha256.notna().all() and identity.sha256.str.fullmatch(r'[0-9a-fA-F]{64}').all(),
                'Row manifest requires a valid SHA-256 for every row.')
        require(identity.sha256.str.lower().is_unique, 'Row-manifest SHA-256 values must be unique.')
        if 'source_feature_float32_sha256' in identity:
            feature_hashes = [hashlib.sha256(np.asarray(row, dtype='<f4').tobytes()).hexdigest() for row in X]
            require(np.array_equal(identity.source_feature_float32_sha256.astype(str), np.asarray(feature_hashes)),
                    'Row-manifest feature hashes differ from the CSV features after float32 round-trip.')
        provenance_status = 'verified_static_identity'
        provenance = {
            'row_manifest_path': str(manifest_path), 'row_manifest_sha256': sha256(manifest_path),
            'identity_rows': int(len(identity)), 'unique_sha256': int(identity.sha256.nunique()),
            'appeared_min': None if 'appeared' not in identity else str(identity.appeared.dropna().min()),
            'appeared_max': None if 'appeared' not in identity else str(identity.appeared.dropna().max()),
            'avclass_nonmissing': None if 'avclass' not in identity else int(identity.avclass.notna().sum()),
        }
        limitations = [
            'Static row identity, SHA-256 and binary labels are verified against the supplied EMBER manifest.',
            'EMBER label 1 means generic malware, not ransomware; AVClass is optional weak family metadata.',
            'A random row split does not establish family-held-out, temporal/zero-day or cross-dataset generalization.',
            'Static EMBER artifacts contain no executable behavior traces; they do not validate PID fusion.',
        ]
    audit = {'data_path': str(path), 'data_sha256': sha256(path), 'rows': len(y), 'features': X.shape[1],
             'feature_names': list(features.columns), 'exact_duplicate_vectors': 0, 'split': split_description,
             'class_counts': {name: {str(k): int(np.sum(y[ix] == k)) for k in [0, 1]}
                             for name, ix in [('train_pool', train), ('validation', val), ('test', test)]},
             'provenance_status': provenance_status, **provenance, 'limitations': limitations}
    return Dataset(X, y, list(features.columns), train, val, test, audit, identity)


def finish_manifest(out):
    write_json(out / 'artifact_sha256.json', {
        str(p.relative_to(out)): sha256(p) for p in sorted(out.rglob('*'))
        if p.is_file() and p.name != 'artifact_sha256.json'
    })


def stats(values):
    a = np.asarray(values, dtype=float)
    return {'mean': float(a.mean()), 'sd': float(a.std(ddof=1)) if len(a) > 1 else None, 'n': len(a)}
