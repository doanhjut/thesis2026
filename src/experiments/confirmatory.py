"""Confirmatory cross-fold protocol for XAI-guided active learning.

The pilot runner intentionally uses one protected split.  This module adds
disjoint outer test folds, a full-training-pool reference in every fold and a
predeclared label-efficiency target on excess AUC above chance.
"""
from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, train_test_split

from . import active_learning, reporting
from .common import (load_dataset, require, source_metadata, stats, write_json)
from .signals import METHODS
from .verification import verify_al


def fold_manifests(y, out, folds=5, seed=2026):
    """Create outer test folds with a stratified validation split inside develop."""
    y = np.asarray(y, dtype=int)
    require(folds >= 2, 'At least two outer folds are required.')
    require(np.min(np.bincount(y)) >= folds, 'Each class must have at least one row per outer fold.')
    out.mkdir(parents=True, exist_ok=False)
    splitter = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
    manifests = []
    for fold, (develop, test) in enumerate(splitter.split(np.zeros(len(y)), y)):
        train, validation = train_test_split(
            develop, test_size=.25, random_state=seed + fold,
            stratify=y[develop],
        )
        split = np.empty(len(y), dtype=object)
        split[train], split[validation], split[test] = 'train_pool', 'validation', 'test'
        frame = pd.DataFrame({'row_id': np.arange(len(y)), 'split': split, 'label': y})
        path = out / f'fold_{fold}.csv'
        frame.to_csv(path, index=False)
        manifests.append(path)
    return manifests


def full_pool_reference(data, out, trees=60, threads=2, seed=2026):
    """Fit the predeclared fully labelled train-pool reference for one fold."""
    params = dict(
        objective='binary', metric='auc', learning_rate=.05, num_leaves=15,
        max_depth=4, min_data_in_leaf=10, num_threads=threads,
        deterministic=True, force_col_wise=True, feature_fraction=1.,
        bagging_fraction=1., bagging_freq=0, verbosity=-1, seed=seed,
        data_random_seed=seed, feature_fraction_seed=seed,
    )
    model = lgb.train(
        params,
        lgb.Dataset(data.X[data.train], label=data.y[data.train], feature_name=data.names),
        num_boost_round=trees,
    )
    model.save_model(str(out))
    validation = model.predict(data.X[data.validation], num_threads=threads)
    test = model.predict(data.X[data.test], num_threads=threads)
    return {
        'validation_auc': float(roc_auc_score(data.y[data.validation], validation)),
        'validation_ap': float(average_precision_score(data.y[data.validation], validation)),
        'test_auc': float(roc_auc_score(data.y[data.test], test)),
        'test_ap': float(average_precision_score(data.y[data.test], test)),
        'training_labels': int(len(data.train)),
    }


def _summary_rows(frame, metrics):
    rows = []
    for method, group in frame.groupby('method'):
        row = {'method': method, 'n_fold_seed_pairs': int(len(group))}
        for metric in metrics:
            row[f'{metric}_mean'] = float(group[metric].mean())
            row[f'{metric}_sd'] = float(group[metric].std(ddof=1)) if len(group) > 1 else None
        rows.append(row)
    return rows


def _json_records(frame):
    """Convert pandas missing values to JSON null for strict artifact JSON."""
    return json.loads(frame.to_json(orient='records'))


def run(data_path, row_manifest, out, folds=5, fold_seed=2026,
        seeds=(11, 22, 33, 44, 55), initial_labels=200, rounds=10,
        batch_size=100, trees=60, threads=2, target_tpr=.95,
        target_excess_auc_fraction=.95):
    require(0 < target_excess_auc_fraction <= 1,
            'target_excess_auc_fraction must be in (0,1].')
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    started = perf_counter()
    base = load_dataset(data_path, split_seed=fold_seed, row_manifest=row_manifest)
    manifests = fold_manifests(base.y, out / 'fold_manifests', folds, fold_seed)
    config = {
        'kind': 'confirmatory_active_learning',
        'data_path': str(Path(data_path).resolve()),
        'row_manifest': None if row_manifest is None else str(Path(row_manifest).resolve()),
        'dataset': base.audit,
        'outer_folds': folds,
        'outer_fold_seed': fold_seed,
        'validation_fraction_within_develop': .25,
        'seeds': list(seeds),
        'initial_labels': initial_labels,
        'rounds': rounds,
        'batch_size': batch_size,
        'trees': trees,
        'threads': threads,
        'target_validation_tpr': target_tpr,
        'label_efficiency_target': (
            'Per fold: 0.5 + target_excess_auc_fraction * '
            '(full-pool validation AUC - 0.5). Test is not used.'
        ),
        'target_excess_auc_fraction': target_excess_auc_fraction,
        'primary_metrics': [
            'normalized test ROC-AUC AULC', 'training labels to validation target',
            'test TPR at validation-selected FPR 1% and 5%',
        ],
        **source_metadata(),
    }
    write_json(out / 'config.json', config)

    all_metrics, all_areas, all_costs, references, checks = [], [], [], [], []
    for fold, split_path in enumerate(manifests):
        fold_out = out / f'fold_{fold}'
        fold_out.mkdir()
        data = load_dataset(data_path, split_file=split_path, row_manifest=row_manifest)
        require(initial_labels + rounds * batch_size <= len(data.train),
                f'Fold {fold}: AL budget exceeds {len(data.train)} training rows.')
        reference = full_pool_reference(
            data, fold_out / 'full_pool_reference.txt', trees, threads, fold_seed + fold)
        target = .5 + target_excess_auc_fraction * (reference['validation_auc'] - .5)
        require(.5 <= target <= 1, 'Derived validation target is outside [0.5,1].')
        reference.update({'fold': fold, 'target_validation_auc': target})
        references.append(reference)
        al_out = fold_out / 'al'
        active_learning.run(
            data, al_out, tuple(seeds), initial_labels, rounds, batch_size,
            trees, threads, target_tpr, target,
        )
        reporting.al_report(al_out)
        check = verify_al(al_out, data)
        check['fold'] = fold
        checks.append(check)
        for filename, destination in [
            ('metrics.csv', all_metrics),
            ('learning_curve_summary.csv', all_areas),
            ('budget_to_target.csv', all_costs),
        ]:
            frame = pd.read_csv(al_out / filename)
            frame.insert(0, 'fold', fold)
            destination.append(frame)

    metrics = pd.concat(all_metrics, ignore_index=True)
    areas = pd.concat(all_areas, ignore_index=True)
    costs = pd.concat(all_costs, ignore_index=True)
    references = pd.DataFrame(references)
    metrics.to_csv(out / 'metrics_all_folds.csv', index=False)
    areas.to_csv(out / 'aulc_all_folds.csv', index=False)
    costs.to_csv(out / 'budget_to_target_all_folds.csv', index=False)
    references.to_csv(out / 'full_pool_references.csv', index=False)
    write_json(out / 'verification.json', {'status': 'passed', 'folds': checks})

    final = metrics[metrics['round'] == rounds].copy()
    final.to_csv(out / 'final_metrics_all_folds.csv', index=False)
    final_metric_names = [
        'test_auc', 'test_ap', 'test_fpr', 'test_tpr',
        'test_standardized_pauc_fpr_05',
        'test_tpr_at_val_fpr_01', 'test_fpr_at_val_cap_01',
        'test_tpr_at_val_fpr_05', 'test_fpr_at_val_cap_05',
    ]
    method_summary = pd.DataFrame(_summary_rows(final, final_metric_names))
    method_summary.to_csv(out / 'method_summary.csv', index=False)

    aulc_summary = pd.DataFrame(_summary_rows(areas, ['auc_aulc', 'ap_aulc',
                                                     'total_train_seconds', 'total_query_seconds']))
    aulc_summary.to_csv(out / 'aulc_summary.csv', index=False)
    reach = (costs.groupby('method').agg(
        reached=('reached', 'sum'), total=('reached', 'size'),
        mean_labels_reached=('n_training_labels', 'mean'),
        median_labels_reached=('n_training_labels', 'median'),
    ).reset_index())
    reach.to_csv(out / 'target_reach_summary.csv', index=False)

    comparisons = []
    xai_final = final[final.method == 'XAI_full'].set_index(['fold', 'seed'])
    xai_area = areas[areas.method == 'XAI_full'].set_index(['fold', 'seed'])
    for baseline in METHODS[:-1]:
        base_final = final[final.method == baseline].set_index(['fold', 'seed'])
        base_area = areas[areas.method == baseline].set_index(['fold', 'seed'])
        for key in xai_final.index:
            row = {'fold': int(key[0]), 'seed': int(key[1]), 'baseline': baseline}
            for metric in final_metric_names:
                row[f'{metric}_difference'] = float(xai_final.loc[key, metric] - base_final.loc[key, metric])
            row['auc_aulc_difference'] = float(xai_area.loc[key, 'auc_aulc'] - base_area.loc[key, 'auc_aulc'])
            row['ap_aulc_difference'] = float(xai_area.loc[key, 'ap_aulc'] - base_area.loc[key, 'ap_aulc'])
            comparisons.append(row)
    paired = pd.DataFrame(comparisons)
    paired.to_csv(out / 'paired_xai_differences.csv', index=False)

    summary = {
        'status': 'confirmatory_measured',
        'outer_folds': folds,
        'al_seeds_per_fold': len(seeds),
        'fold_seed_pairs_per_method': folds * len(seeds),
        'full_pool_reference': {
            'validation_auc': stats(references.validation_auc),
            'test_auc': stats(references.test_auc),
        },
        'methods': _json_records(method_summary),
        'target_reach': _json_records(reach),
        'elapsed_seconds': perf_counter() - started,
        'limitations': [
            'AL seeds nested in one fold share validation/test rows; fold-seed rows are not independent population samples.',
            'Outer test folds are row-stratified, not malware-family-held-out or temporal.',
            'Label counts measure oracle queries, not analyst wall-clock hours.',
            'A positive conclusion requires paired effects and uncertainty; a favorable grand mean alone is insufficient.',
        ],
    }
    write_json(out / 'summary.json', summary)
    (out / 'README.md').write_text(
        '# Confirmatory XAI-Guided Active Learning\n\n'
        'Mỗi outer fold giữ một test fold riêng, tách validation bên trong phần develop, '
        'và chạy cùng initial set/ngân sách cho năm chiến lược. Ngưỡng hiệu quả nhãn '
        'được tính từ full-pool validation AUC theo công thức đã khai báo trong config.json.\n\n'
        'Dùng method_summary.csv, aulc_summary.csv, target_reach_summary.csv và '
        'paired_xai_differences.csv để viết kết quả. Không dùng test để chọn target, '
        'hyperparameter, vòng dừng hoặc phương pháp.\n',
        encoding='utf-8',
    )
    return summary
