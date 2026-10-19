"""Cross-model and cross-fold robustness study for TreeSHAP deletion tests."""
from __future__ import annotations

import itertools
import json
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from . import fidelity, reporting
from .common import load_dataset, require, source_metadata, stats, write_json
from .verification import verify_fidelity


def _split_paths(split_dir):
    if split_dir is None:
        return [None]
    paths = sorted(Path(split_dir).glob('fold_*.csv'))
    require(paths, 'No fold_*.csv manifests found in split-dir.')
    return paths


def run(data_path, row_manifest, out, split_dir=None,
        seeds=(41, 42, 43, 44, 45), baselines=('mean', 'median'),
        k_values=(10, 25, 50), repetitions=20, bootstrap=500,
        trees=100, threads=2, max_test_rows=1000,
        feature_fraction=.8, bagging_fraction=.8):
    require(len(seeds) >= 2 and len(set(seeds)) == len(seeds),
            'At least two unique model seeds are required.')
    require(set(baselines) <= {'mean', 'median'} and len(set(baselines)) == len(baselines),
            'Baselines must be unique values from mean, median.')
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    started = perf_counter()
    paths = _split_paths(split_dir)
    config = {
        'kind': 'confirmatory_fidelity',
        'data_path': str(Path(data_path).resolve()),
        'row_manifest': None if row_manifest is None else str(Path(row_manifest).resolve()),
        'split_dir': None if split_dir is None else str(Path(split_dir).resolve()),
        'folds': len(paths), 'model_seeds': list(seeds), 'mask_baselines': list(baselines),
        'k_values': list(k_values), 'random_masks_per_k': repetitions,
        'bootstrap_repetitions_per_model': bootstrap, 'trees': trees,
        'feature_fraction': feature_fraction, 'bagging_fraction': bagging_fraction,
        'model_variation': (
            'LightGBM is deterministic within a seed; feature and row subsampling '
            'make fitted models differ reproducibly across seeds.'
        ),
        **source_metadata(),
    }
    write_json(out / 'config.json', config)

    model_rows, mask_rows, importance, checks = [], [], {}, []
    for fold, split_path in enumerate(paths):
        data = load_dataset(data_path, split_file=split_path, row_manifest=row_manifest)
        for seed in seeds:
            for baseline in baselines:
                run_out = out / f'fold_{fold}' / f'seed_{seed}_{baseline}'
                result = fidelity.run(
                    data, run_out, seed, tuple(k_values), repetitions, bootstrap,
                    trees, threads, max_test_rows, baseline,
                    feature_fraction, bagging_fraction,
                )
                reporting.fidelity_report(run_out)
                check = verify_fidelity(run_out, data)
                check.update({'fold': fold, 'seed': seed, 'mask_baseline': baseline})
                checks.append(check)
                model_rows.append({
                    'fold': fold, 'seed': seed, 'mask_baseline': baseline,
                    'baseline_test_auc': result['baseline_test_roc_auc'],
                    'baseline_test_ap': result['baseline_test_average_precision'],
                    'ec': result['ec'], 'cf': result['cf'],
                    'max_shap_additivity_error': result['max_shap_additivity_error'],
                })
                table = pd.read_csv(run_out / 'mask_metrics.csv')
                table.insert(0, 'fold', fold)
                table.insert(1, 'seed', seed)
                table.insert(2, 'mask_baseline', baseline)
                mask_rows.append(table)
                if baseline == 'mean':
                    phi = np.load(run_out / 'shap_values.npz')['phi']
                    importance[(fold, seed)] = np.mean(np.abs(phi), axis=0)

    models = pd.DataFrame(model_rows)
    masks = pd.concat(mask_rows, ignore_index=True)
    models.to_csv(out / 'model_metrics.csv', index=False)
    masks.to_csv(out / 'mask_metrics_all_models.csv', index=False)
    write_json(out / 'verification.json', {'status': 'passed', 'runs': checks})

    comparisons = []
    for (fold, seed, baseline, k), group in masks.groupby(['fold', 'seed', 'mask_baseline', 'k']):
        top = group[group.method == 'top_abs_treeshap'].iloc[0]
        random = group[group.method == 'uniform_random']
        comparisons.append({
            'fold': int(fold), 'seed': int(seed), 'mask_baseline': baseline, 'k': int(k),
            'top_shap_auc_drop': float(top.auc_drop),
            'random_auc_drop_mean': float(random.auc_drop.mean()),
            'top_minus_random_auc_drop': float(top.auc_drop - random.auc_drop.mean()),
            'top_shap_probability_change': float(top.mean_absolute_probability_change),
            'random_probability_change_mean': float(random.mean_absolute_probability_change.mean()),
        })
    comparisons = pd.DataFrame(comparisons)
    comparisons.to_csv(out / 'model_deletion_comparisons.csv', index=False)
    deletion_summary = (comparisons.groupby(['mask_baseline', 'k']).agg(
        models=('top_shap_auc_drop', 'size'),
        top_shap_auc_drop_mean=('top_shap_auc_drop', 'mean'),
        top_shap_auc_drop_sd=('top_shap_auc_drop', 'std'),
        random_auc_drop_mean=('random_auc_drop_mean', 'mean'),
        random_auc_drop_sd=('random_auc_drop_mean', 'std'),
        top_minus_random_mean=('top_minus_random_auc_drop', 'mean'),
        top_minus_random_sd=('top_minus_random_auc_drop', 'std'),
    ).reset_index())
    deletion_summary.to_csv(out / 'deletion_summary.csv', index=False)

    stability = []
    for left, right in itertools.combinations(sorted(importance), 2):
        a, b = importance[left], importance[right]
        record = {
            'left_fold': left[0], 'left_seed': left[1],
            'right_fold': right[0], 'right_seed': right[1],
            'same_fold': left[0] == right[0],
            'spearman_global_importance': float(spearmanr(a, b).statistic),
        }
        for k in k_values:
            top_a = set(np.argsort(a)[-k:])
            top_b = set(np.argsort(b)[-k:])
            record[f'jaccard_top_{k}'] = len(top_a & top_b) / len(top_a | top_b)
        stability.append(record)
    stability = pd.DataFrame(stability)
    stability.to_csv(out / 'shap_rank_stability.csv', index=False)

    summary = {
        'status': 'confirmatory_measured',
        'models_per_baseline': len(paths) * len(seeds),
        'folds': len(paths), 'model_seeds': len(seeds),
        'baseline_auc': stats(models[models.mask_baseline == baselines[0]].baseline_test_auc),
        'deletion': json.loads(deletion_summary.to_json(orient='records')),
        'shap_stability': {
            'pair_count': int(len(stability)),
            'spearman': stats(stability.spearman_global_importance),
            **{f'jaccard_top_{k}': stats(stability[f'jaccard_top_{k}']) for k in k_values},
        },
        'ofs': None,
        'ofs_reason': 'No validated common-scale aggregation rule; components remain separate.',
        'elapsed_seconds': perf_counter() - started,
        'limitations': [
            'Deletion is performed in EMBER feature space and need not correspond to a valid executable.',
            'Mean and median replacement can create out-of-distribution feature combinations.',
            'Rank stability measures reproducibility of the fitted model explanations, not causal correctness.',
            'Repeated random masks within one fitted model are controls, not independent model replications.',
        ],
    }
    write_json(out / 'summary.json', summary)
    (out / 'README.md').write_text(
        '# Confirmatory Fidelity\n\n'
        'Bộ chạy lặp TreeSHAP deletion trên nhiều outer fold, model seed và hai '
        'training-derived mask baseline. Bằng chứng chính nằm trong '
        'deletion_summary.csv; độ ổn định giải thích nằm trong '
        'shap_rank_stability.csv. OFS không được tổng hợp.\n',
        encoding='utf-8',
    )
    return summary
