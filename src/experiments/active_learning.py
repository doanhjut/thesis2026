"""Paired active-learning ablations with fresh models and a protected test set."""
import csv
import gzip
from time import perf_counter

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from .common import choose_threshold, evaluate, low_fpr_metrics, require, source_metadata, stats, write_json
from .signals import METHODS, WEIGHTS, acquisition_scores


def run(data, out, seeds=(11, 22, 33, 44, 55), initial_labels=200, rounds=5,
        batch_size=100, trees=60, threads=2, target_tpr=.95, target_val_auc=None):
    require(len(seeds) > 0 and len(set(seeds)) == len(seeds), 'Seeds must be nonempty and unique.')
    require(all(isinstance(s, int) and 0 <= s < 2**32 for s in seeds), 'Invalid seed.')
    require(initial_labels >= 2 and rounds >= 1 and batch_size >= 1 and trees >= 1 and threads >= 1, 'Invalid AL budget/model parameters.')
    require(initial_labels + rounds * batch_size <= len(data.train), 'AL budget exceeds the training/pool partition.')
    require(0 < target_tpr <= 1, 'target_tpr must be in (0, 1].')
    require(target_val_auc is None or 0 < target_val_auc <= 1, 'Invalid predeclared validation AUC target.')
    out.mkdir(parents=True, exist_ok=False)
    (out / 'models').mkdir()
    started = perf_counter()
    data.save_split(out)
    params = dict(objective='binary', metric='auc', learning_rate=.05, num_leaves=15,
                  max_depth=4, min_data_in_leaf=10, num_threads=threads,
                  deterministic=True, force_col_wise=True, feature_fraction=1.,
                  bagging_fraction=1., bagging_freq=0, verbosity=-1)
    config = {'kind': 'active_learning', 'dataset': data.audit, 'seeds': list(seeds),
              'initial_labels': initial_labels, 'rounds': rounds, 'batch_size': batch_size,
              'trees': trees, 'model_parameters': params, 'methods': METHODS, 'weights': WEIGHTS,
              'target_validation_tpr': target_tpr, 'target_validation_auc': target_val_auc,
              'low_fpr_operating_points': [.01, .05],
              'tie_break': 'ascending original CSV row ID',
              'oracle': 'Existing labels revealed only for queried rows; seed set stratified offline.',
              'budget': 'Training labels only; validation labels are additional; no measured analyst time.',
              'timing': 'Score computation includes pool prediction, TreeSHAP, additivity and normalization; excludes sorting, labeling, training and I/O.',
              'test_policy': 'Fixed split across seeds. Never used to select queries, parameters, thresholds or stopping.',
              **source_metadata()}
    write_json(out / 'config.json', config)
    initial, pools = {}, {}
    for seed in seeds:
        pool, labeled = train_test_split(data.train, test_size=initial_labels, random_state=seed,
                                         stratify=data.y[data.train])
        initial[seed], pools[seed] = labeled, pool
    write_json(out / 'initial_sets.json', {str(s): {'labeled': initial[s].tolist(), 'pool': pools[s].tolist()} for s in seeds})
    fields = ['seed', 'method', 'round', 'n_labeled', 'split', 'row_id', 'label', 'probability', 'threshold', 'prediction']
    records, queries, max_error = [], [], 0.
    with gzip.open(out / 'predictions.csv.gz', 'wt', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for seed in seeds:
            for method in METHODS:
                labeled, pool = initial[seed].copy(), pools[seed].copy()
                rng = np.random.default_rng(seed)
                model = None
                for rnd in range(rounds + 1):
                    timing = {'query_seconds': 0., 'pool_inference_seconds': 0., 'tree_shap_seconds': 0., 'selection_seconds': 0.}
                    if rnd:
                        scores, signals, scaled, timing, error = acquisition_scores(model, data.X[pool], method, rng, threads)
                        max_error = max(max_error, error)
                        selection_start = perf_counter()
                        positions = np.lexsort((pool, -scores))[:batch_size]
                        chosen = pool[positions]
                        timing['selection_seconds'] = perf_counter() - selection_start
                        require(len(set(chosen)) == batch_size and not set(chosen) & set(labeled), 'Repeated query.')
                        for rank, (position, row_id) in enumerate(zip(positions, chosen), 1):
                            queries.append({'seed': seed, 'method': method, 'round': rnd, 'row_id': int(row_id),
                                            'rank': rank, 'score': float(scores[position]), 'label': int(data.y[row_id]),
                                            **{f'{k}_raw': float(v[position]) for k, v in signals.items()},
                                            **{f'{k}_normalized': float(v[position]) for k, v in scaled.items()}})
                        labeled = np.concatenate([labeled, chosen])
                        keep = np.ones(len(pool), dtype=bool)
                        keep[positions] = False
                        pool = pool[keep]
                    require(len(labeled) == initial_labels + rnd * batch_size, 'Incorrect cumulative budget.')
                    require(not set(labeled) & (set(data.validation) | set(data.test)), 'Held-out rows reached training.')
                    p = dict(params, seed=seed, data_random_seed=seed, feature_fraction_seed=seed)
                    train_start = perf_counter()
                    model = lgb.train(p, lgb.Dataset(data.X[labeled], label=data.y[labeled], feature_name=data.names), num_boost_round=trees)
                    train_seconds = perf_counter() - train_start
                    model.save_model(str(out / 'models' / f'seed{seed}_{method.replace("+", "_")}_round{rnd}.txt'))
                    evaluation_start = perf_counter()
                    val_p = model.predict(data.X[data.validation], num_threads=threads)
                    threshold = choose_threshold(data.y[data.validation], val_p, target_tpr)
                    test_p = model.predict(data.X[data.test], num_threads=threads)
                    validation = evaluate(data.y[data.validation], val_p, threshold)
                    testing = evaluate(data.y[data.test], test_p, threshold)
                    low_fpr = low_fpr_metrics(data.y[data.validation], val_p,
                                              data.y[data.test], test_p)
                    records.append({'seed': seed, 'method': method, 'round': rnd, 'n_labeled': len(labeled),
                                    'n_added': rnd * batch_size, 'threshold': threshold, **timing,
                                    'train_seconds': train_seconds, 'evaluation_seconds': perf_counter() - evaluation_start,
                                    **{f'val_{k}': v for k, v in validation.items()},
                                    **{f'test_{k}': v for k, v in testing.items()}, **low_fpr})
                    for split, ids, probs in [('validation', data.validation, val_p), ('test', data.test, test_p)]:
                        for row_id, probability in zip(ids, probs):
                            writer.writerow({'seed': seed, 'method': method, 'round': rnd, 'n_labeled': len(labeled),
                                             'split': split, 'row_id': int(row_id), 'label': int(data.y[row_id]),
                                             'probability': float(probability), 'threshold': threshold,
                                             'prediction': int(probability >= threshold)})
                print(f'AL seed={seed} method={method}: AUC={testing["auc"]:.6f}, FPR={testing["fpr"]:.4f}, TPR={testing["tpr"]:.4f}', flush=True)
    metrics = pd.DataFrame(records)
    metrics.to_csv(out / 'metrics.csv', index=False)
    pd.DataFrame(queries).to_csv(out / 'queries.csv', index=False)
    for seed, g in metrics[metrics['round'] == 0].groupby('seed'):
        for name in ['test_auc', 'test_ap', 'test_fpr', 'test_tpr', 'threshold']:
            require(g[name].nunique() == 1, f'Unequal initial conditions: {seed}, {name}')
    final = metrics[metrics['round'] == rounds]
    paired = []
    for method in METHODS:
        for baseline in ['Random', 'Uncertainty']:
            if method == baseline:
                continue
            a, b = [final[final.method == m].set_index('seed') for m in [method, baseline]]
            for metric in ['auc', 'ap', 'fpr', 'tpr']:
                for seed in seeds:
                    paired.append({'method': method, 'baseline': baseline, 'metric': metric, 'seed': seed,
                                   'difference': float(a.loc[seed, f'test_{metric}'] - b.loc[seed, f'test_{metric}'])})
    pd.DataFrame(paired).to_csv(out / 'paired_differences.csv', index=False)
    trapezoid = np.trapezoid if hasattr(np, 'trapezoid') else np.trapz
    area = []
    for (seed, method), g in metrics.groupby(['seed', 'method']):
        g = g.sort_values('n_labeled')
        area.append({'seed': int(seed), 'method': method,
                     'auc_aulc': float(trapezoid(g.test_auc, g.n_labeled) / (rounds * batch_size)),
                     'ap_aulc': float(trapezoid(g.test_ap, g.n_labeled) / (rounds * batch_size)),
                     'total_train_seconds': float(g.train_seconds.sum()),
                     'total_query_seconds': float(g.query_seconds.sum())})
    pd.DataFrame(area).to_csv(out / 'learning_curve_summary.csv', index=False)
    if target_val_auc is not None:
        costs = []
        for (seed, method), g in metrics.groupby(['seed', 'method']):
            reached = g.sort_values('round').query('val_auc >= @target_val_auc')
            first = reached.iloc[0] if len(reached) else None
            costs.append({'seed': seed, 'method': method, 'target_validation_auc': target_val_auc,
                          'reached': first is not None, 'n_training_labels': None if first is None else int(first.n_labeled),
                          'additional_validation_labels': len(data.validation),
                          'test_auc_at_first_reach': None if first is None else float(first.test_auc)})
        pd.DataFrame(costs).to_csv(out / 'budget_to_target.csv', index=False)
    summary = {'status': 'measured', 'scope': data.audit['limitations'],
               'n_seeds': len(seeds), 'final_training_labels': initial_labels + rounds * batch_size,
               'additional_validation_labels': len(data.validation),
               'final': {m: {k: stats(g[f'test_{k}']) for k in ['auc', 'ap', 'fpr', 'tpr']}
                         for m, g in final.groupby('method')},
               'counts': {'models': len(records), 'queries': len(queries),
                          'prediction_records': len(records) * (len(data.validation) + len(data.test))},
               'max_shap_additivity_error': max_error, 'elapsed_seconds': perf_counter() - started,
               'limitations': ['Seeds share one test set; SD is not a population confidence interval.',
                               'No conclusion about labels/time saved unless that quantity is separately measured.']}
    write_json(out / 'summary.json', summary)
    return summary
