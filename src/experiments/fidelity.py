"""Fixed-model deletion controls and the explicitly defined thesis FF/EC/CF."""
import ast
import operator
from time import perf_counter

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.model_selection import train_test_split

from .common import REPO, require, sha256, source_metadata, write_json
from .signals import native_shap


def ember_schema(path):
    """Read the extractor's default v2 ordering without importing binary dependencies."""
    def number(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mult)):
            return (operator.add if isinstance(node.op, ast.Add) else operator.mul)(number(node.left), number(node.right))
        raise ValueError('Unsupported EMBER dimension expression.')
    tree = ast.parse(path.read_text())
    classes = {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}
    init = next(n for n in classes['PEFeatureExtractor'].body if isinstance(n, ast.FunctionDef) and n.name == '__init__')
    dictionary = next(n.value for n in ast.walk(init) if isinstance(n, ast.Assign) and
                      any(isinstance(t, ast.Name) and t.id == 'features' for t in n.targets) and isinstance(n.value, ast.Dict))
    rows, offset = [], 0
    for name in [v.func.id for v in dictionary.values] + ['DataDirectories']:
        expr = next(n.value for n in classes[name].body if isinstance(n, ast.Assign) and
                    any(isinstance(t, ast.Name) and t.id == 'dim' for t in n.targets))
        dimension = int(number(expr))
        rows.append({'group': name, 'start_inclusive': offset, 'end_exclusive': offset + dimension, 'dimension': dimension})
        offset += dimension
    require(offset == 2381, 'Unexpected EMBER schema; inspect extractor before reporting groups.')
    return rows


def mask_metrics(y, original, masked, epsilon=1e-12):
    change = original - masked
    before, after = roc_auc_score(y, original), roc_auc_score(y, masked)
    return {'auc_before': float(before), 'auc_after': float(after), 'auc_drop': float(before - after),
            'mean_absolute_probability_change': float(np.abs(change).mean()),
            'mean_signed_probability_drop': float(change.mean()),
            'probability_decrease_fraction': float(np.mean(change > 1e-12)),
            'probability_increase_fraction': float(np.mean(change < -1e-12)),
            'thesis_ff_raw_unclipped': float(np.mean(np.abs(change) / (original + epsilon)))}


def explanation_geometry(X, phi, y, mean, std, epsilon=1e-12):
    sx = cosine_similarity((X - mean) / std)
    sp = cosine_similarity(phi)
    upper = np.triu_indices(len(y), k=1)
    a, b = sx[upper], sp[upper]
    ec = float(np.corrcoef(a, b)[0, 1]) if a.std() > 0 and b.std() > 0 else None
    c0, c1 = phi[y == 0].mean(axis=0), phi[y == 1].mean(axis=0)
    numerator = float(np.linalg.norm(c1 - c0))
    denominator = float(np.linalg.norm(phi, axis=1).max())
    return {'ec': ec, 'ec_reason': None if ec is not None else 'Undefined: one similarity vector is constant.',
            'ec_pair_count': len(a), 'cf': numerator / (denominator + epsilon),
            'cf_numerator': numerator, 'cf_denominator_max_sample_shap_norm': denominator}, (sx, sp, c0, c1)


def run(data, out, seed=42, k_values=(10, 25, 50), repetitions=20, bootstrap=500,
        trees=100, threads=2, max_test_rows=1000):
    require(repetitions >= 2 and bootstrap >= 2 and trees > 0 and threads > 0, 'Invalid Fidelity parameters.')
    require(len(k_values) > 0 and len(set(k_values)) == len(k_values) and
            all(0 < k <= data.X.shape[1] for k in k_values), 'top-k must be unique positive values within the feature dimension.')
    require(max_test_rows >= 4, 'At least four evaluation rows are required.')
    out.mkdir(parents=True, exist_ok=False)
    start = perf_counter()
    data.save_split(out)
    test = data.test
    if len(test) > max_test_rows:
        test, _ = train_test_split(test, train_size=max_test_rows, random_state=seed, stratify=data.y[test])
    params = dict(n_estimators=trees, num_leaves=15, max_depth=4, learning_rate=.1,
                  min_child_samples=20, n_jobs=threads, random_state=seed,
                  deterministic=True, force_col_wise=True, verbosity=-1)
    config = {'kind': 'fidelity', 'dataset': data.audit, 'model_parameters': params, 'seed': seed,
              'k_values': list(k_values), 'random_repetitions': repetitions, 'bootstrap_repetitions': bootstrap,
              'evaluation_row_ids': test.tolist(), 'epsilon': 1e-12,
              'mask_baseline': 'Training-column arithmetic mean; only feature vectors are altered.',
              'shap': 'Native TreeSHAP on raw log-odds; bias excluded from ranking.',
              'ff': 'Mean absolute probability change divided by original probability + epsilon; unclipped.',
              'ec': 'Pearson correlation of upper-triangle cosine similarities: train-standardized features versus signed SHAP.',
              'cf': 'Distance between class SHAP centroids / maximum sample SHAP norm + epsilon.',
              'ofs': None, 'ofs_reason': 'No validated common-scale aggregation rule; report components separately.',
              'limitations': data.audit['limitations'] + [
                  'One fitted model; test bootstrap is conditional on that model.',
                  'Masking is not a validated transformation of executable PE files.',
                  'EC pairs share samples; no naive independent-pair p-value.',
                  'CF describes class separation, not causality or explanation correctness.'],
              **source_metadata()}
    schema_source = REPO / 'scripts/ember/ember/features.py'
    if data.X.shape[1] == 2381:
        write_json(out / 'feature_groups.json', ember_schema(schema_source))
        config['schema_source_sha256'] = sha256(schema_source)
        config['schema_status'] = (
            'EMBER v2 dimension and row identity verified; bundled extractor is a schema reference, '
            'not a reconstruction of the original release toolchain.'
            if data.audit['provenance_status'] == 'verified_static_identity'
            else 'Extractor reference; original CSV extraction provenance remains unverified.'
        )
    write_json(out / 'config.json', config)
    model = lgb.LGBMClassifier(**params)
    train_start = perf_counter()
    model.fit(data.X[data.train], data.y[data.train])
    train_seconds = perf_counter() - train_start
    booster = model.booster_
    booster.save_model(str(out / 'model.txt'))
    mean, std = data.X[data.train].mean(axis=0), data.X[data.train].std(axis=0)
    std[std == 0] = 1.
    np.savez_compressed(out / 'train_baseline.npz', mean=mean, std=std)
    X, y = data.X[test], data.y[test]
    original = booster.predict(X, num_threads=threads)
    phi, bias, raw, shap_seconds, error = native_shap(booster, X, threads)
    np.savez_compressed(out / 'shap_values.npz', row_id=test, phi=phi, intercept=bias, raw_scores=raw)
    pd.DataFrame({'row_id': test, 'label': y, 'p_original': original}).to_csv(out / 'test_predictions.csv', index=False)
    top_indices = np.argsort(np.abs(phi), axis=1)[:, ::-1]
    row_indices = np.arange(len(test))[:, None]
    records, predictions, masks, top_predictions = [], [], {}, {}
    mask_start = perf_counter()
    for k in k_values:
        for method in ['top_abs_treeshap', 'uniform_random']:
            for replicate in range(1 if method == 'top_abs_treeshap' else repetitions):
                if method == 'top_abs_treeshap':
                    selected = top_indices[:, :k]
                else:
                    rng = np.random.default_rng(np.random.SeedSequence([seed, k, replicate]))
                    selected = np.stack([rng.choice(X.shape[1], k, replace=False) for _ in test])
                masked = X.copy()
                masked[row_indices, selected] = mean[selected]
                p = booster.predict(masked, num_threads=threads)
                records.append({'method': method, 'k': k, 'replicate': replicate,
                                **mask_metrics(y, original, p),
                                'mean_actual_changed_coordinates': float(np.mean(np.sum(masked != X, axis=1)))})
                masks[f'{method}_k{k}_rep{replicate}'] = selected.astype(np.int32)
                if method == 'top_abs_treeshap':
                    top_predictions[k] = p
                predictions.append(pd.DataFrame({'method': method, 'k': k, 'replicate': replicate,
                                                 'row_id': test, 'label': y, 'p_original': original, 'p_masked': p}))
    mask_seconds = perf_counter() - mask_start
    table = pd.DataFrame(records)
    table.to_csv(out / 'mask_metrics.csv', index=False)
    pd.concat(predictions, ignore_index=True).to_csv(out / 'mask_predictions.csv.gz', index=False)
    np.savez_compressed(out / 'mask_indices.npz', **masks)
    geometry, arrays = explanation_geometry(X, phi, y, mean, std)
    np.savez_compressed(out / 'ec_cf_inputs.npz', feature_similarity=arrays[0], shap_similarity=arrays[1],
                        class0_centroid=arrays[2], class1_centroid=arrays[3])
    rng = np.random.default_rng(2026)
    strata = [np.flatnonzero(y == label) for label in [0, 1]]
    drops = {k: [] for k in k_values}
    for _ in range(bootstrap):
        selected = np.concatenate([rng.choice(s, len(s), replace=True) for s in strata])
        before = roc_auc_score(y[selected], original[selected])
        for k, p in top_predictions.items():
            drops[k].append(float(before - roc_auc_score(y[selected], p[selected])))
    np.savez_compressed(out / 'paired_test_bootstrap.npz', **{f'k{k}': a for k, a in drops.items()})
    comparisons = []
    for k in k_values:
        top = table[(table.k == k) & (table.method == 'top_abs_treeshap')].iloc[0]
        random = table[(table.k == k) & (table.method == 'uniform_random')]
        comparisons.append({'k': k, 'auc_before': float(top.auc_before),
                            'top_shap_auc_after': float(top.auc_after), 'top_shap_auc_drop': float(top.auc_drop),
                            'top_shap_auc_drop_bootstrap_test_ci95': np.quantile(drops[k], [.025, .975]).tolist(),
                            'random_auc_after_mean': float(random.auc_after.mean()),
                            'random_auc_drop_mean': float(random.auc_drop.mean()),
                            'random_auc_drop_sd_across_masks': float(random.auc_drop.std(ddof=1)),
                            'top_shap_ff_raw': float(top.thesis_ff_raw_unclipped),
                            'top_shap_mean_absolute_probability_change': float(top.mean_absolute_probability_change),
                            'random_mean_absolute_probability_change': float(random.mean_absolute_probability_change.mean())})
    summary = {'status': 'measured', 'evaluation_rows': len(test),
               'baseline_test_roc_auc': float(roc_auc_score(y, original)),
               'baseline_test_average_precision': float(average_precision_score(y, original)),
               'max_shap_additivity_error': error, 'deletion_comparisons': comparisons, **geometry,
               'ofs': None, 'ofs_reason': config['ofs_reason'], 'limitations': config['limitations'],
               'timings': {'train_seconds': train_seconds, 'native_shap_seconds': shap_seconds,
                           'mask_prediction_seconds': mask_seconds, 'total_seconds': perf_counter() - start}}
    write_json(out / 'summary.json', summary)
    print(f'Fidelity: AUC={summary["baseline_test_roc_auc"]:.6f}, EC={geometry["ec"]}, CF={geometry["cf"]:.6f}; OFS not aggregated.', flush=True)
    return summary
