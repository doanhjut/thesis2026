"""Independent recomputation from saved predictions, models and selected masks."""
import json
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from .common import choose_threshold, evaluate, load_dataset, require, sha256
from .fidelity import explanation_geometry, mask_metrics


def close(a, b, message):
    require(np.allclose(a, b, rtol=1e-9, atol=1e-10), message)


def verify_al(out, data):
    config = json.loads((out / 'config.json').read_text())
    require(config['dataset']['data_sha256'] == data.audit['data_sha256'], 'Dataset checksum changed.')
    metrics = pd.read_csv(out / 'metrics.csv', float_precision='round_trip')
    pred = pd.read_csv(out / 'predictions.csv.gz', float_precision='round_trip')
    query = pd.read_csv(out / 'queries.csv', float_precision='round_trip')
    initial = json.loads((out / 'initial_sets.json').read_text())
    splits = json.loads((out / 'splits.json').read_text())
    require(not pred.duplicated(['seed', 'method', 'round', 'split', 'row_id']).any(), 'Duplicate predictions.')
    require(not query.duplicated(['seed', 'method', 'row_id']).any(), 'Repeated AL queries.')
    expected = len(config['seeds']) * len(config['methods']) * (config['rounds'] + 1)
    require(len(metrics) == expected, 'Missing checkpoints.')
    for row in metrics.itertuples():
        selected = pred[(pred.seed == row.seed) & (pred.method == row.method) & (pred['round'] == row.round)]
        val = selected[selected.split == 'validation']
        threshold = choose_threshold(val.label, val.probability, config['target_validation_tpr'])
        close(threshold, row.threshold, 'Threshold differs from validation-only calculation.')
        checkpoint = out / 'models' / f'seed{row.seed}_{row.method.replace("+", "_")}_round{row.round}.txt'
        model = lgb.Booster(model_file=str(checkpoint))
        for split in ['validation', 'test']:
            g = selected[selected.split == split]
            require(set(g.row_id) == set(splits[split]), 'Incomplete or changed held-out rows.')
            require(np.array_equal(g.label.to_numpy(), data.y[g.row_id]), 'Prediction labels do not match data.')
            close(model.predict(data.X[g.row_id], num_threads=2), g.probability, 'Model does not reproduce saved predictions.')
            computed = evaluate(g.label, g.probability, threshold)
            prefix = 'val' if split == 'validation' else 'test'
            for name, value in computed.items():
                close(value, getattr(row, f'{prefix}_{name}'), f'Metric mismatch: {prefix}_{name}')
            require(np.array_equal(g.prediction.to_numpy(), (g.probability >= threshold).astype(int)), 'Saved thresholded decisions differ.')
        selected_queries = query[(query.seed == row.seed) & (query.method == row.method) & (query['round'] <= row.round)]
        require(len(selected_queries) == row.round * config['batch_size'], 'Wrong query budget.')
        require(set(selected_queries.row_id) <= set(initial[str(row.seed)]['pool']), 'Query outside original pool.')
        require(not set(selected_queries.row_id) & set(initial[str(row.seed)]['labeled']), 'Initial row queried again.')
        require(np.array_equal(selected_queries.label.to_numpy(), data.y[selected_queries.row_id]), 'Oracle labels mismatch.')
    summary = json.loads((out / 'summary.json').read_text())
    final = metrics[metrics['round'] == config['rounds']]
    for method, g in final.groupby('method'):
        for name in ['auc', 'ap', 'fpr', 'tpr']:
            close(g[f'test_{name}'].mean(), summary['final'][method][name]['mean'], 'Final mean mismatch.')
    return {'status': 'passed', 'checkpoints_replayed': expected, 'prediction_records': len(pred), 'query_records': len(query)}


def verify_fidelity(out, data):
    config = json.loads((out / 'config.json').read_text())
    require(config['dataset']['data_sha256'] == data.audit['data_sha256'], 'Dataset checksum changed.')
    original = pd.read_csv(out / 'test_predictions.csv', float_precision='round_trip')
    mask_table = pd.read_csv(out / 'mask_metrics.csv', float_precision='round_trip')
    masks = np.load(out / 'mask_indices.npz')
    baseline = np.load(out / 'train_baseline.npz')
    ids = original.row_id.to_numpy()
    require(np.array_equal(ids, config['evaluation_row_ids']), 'Evaluation IDs changed.')
    require(set(ids) <= set(data.test), 'Fidelity rows are outside the test partition.')
    close(baseline['mean'], data.X[data.train].mean(axis=0), 'Mask baseline is not the training mean.')
    model = lgb.Booster(model_file=str(out / 'model.txt'))
    p = model.predict(data.X[ids], num_threads=2)
    close(p, original.p_original, 'Original Fidelity predictions mismatch.')
    saved_pred = pd.read_csv(out / 'mask_predictions.csv.gz', float_precision='round_trip')
    for row in mask_table.itertuples():
        key = f'{row.method}_k{row.k}_rep{row.replicate}'
        selected = masks[key]
        require(selected.shape == (len(ids), row.k), 'Incorrect mask shape.')
        require(all(len(set(a)) == row.k for a in selected), 'Repeated coordinates in mask.')
        require(np.all((selected >= 0) & (selected < data.X.shape[1])), 'Mask index out of bounds.')
        X = data.X[ids].copy()
        X[np.arange(len(ids))[:, None], selected] = baseline['mean'][selected]
        after = model.predict(X, num_threads=2)
        measured = mask_metrics(data.y[ids], p, after)
        for name, value in measured.items():
            close(value, getattr(row, name), f'Fidelity metric mismatch: {name}')
        g = saved_pred[(saved_pred.method == row.method) & (saved_pred.k == row.k) & (saved_pred.replicate == row.replicate)]
        require(np.array_equal(g.row_id.to_numpy(), ids), 'Masked prediction row order differs.')
        close(after, g.p_masked, 'Mask predictions do not match model replay.')
    attribution = np.load(out / 'shap_values.npz')
    raw = model.predict(data.X[ids], raw_score=True, num_threads=2)
    close(attribution['phi'].sum(axis=1) + attribution['intercept'], raw, 'SHAP additivity failed.')
    summary = json.loads((out / 'summary.json').read_text())
    geometry, _ = explanation_geometry(data.X[ids], attribution['phi'], data.y[ids], baseline['mean'], baseline['std'])
    for key in ['ec', 'cf']:
        if geometry[key] is None:
            require(summary[key] is None, 'Undefined EC reported as numeric.')
        else:
            close(geometry[key], summary[key], f'Geometry mismatch: {key}')
    close(roc_auc_score(data.y[ids], p), summary['baseline_test_roc_auc'], 'Baseline AUC mismatch.')
    require(summary['ofs'] is None, 'Unexpected aggregate OFS.')
    return {'status': 'passed', 'mask_batches_replayed': len(mask_table), 'prediction_records': len(saved_pred)}


def verify_manifest(out):
    manifest = json.loads((out / 'artifact_sha256.json').read_text())
    for name, digest in manifest.items():
        path = (out / name).resolve()
        require(path.is_relative_to(out.resolve()) and path.is_file(), 'Invalid manifest path.')
        require(sha256(path) == digest, f'Artifact checksum mismatch: {name}')
    return len(manifest)


def verify_saved_run(out, data_path=None):
    out = Path(out)
    checked = verify_manifest(out)
    result = {'artifact_files_checked': checked}
    for name, verifier in [('al', verify_al), ('fidelity', verify_fidelity)]:
        folder = out / name
        if not folder.exists():
            continue
        config = json.loads((folder / 'config.json').read_text())
        audit = config['dataset']
        # Replay exactly the saved split rather than relying on current defaults.
        data = load_dataset(data_path or audit['data_path'], split_file=folder / 'split_manifest.csv')
        result[name] = verifier(folder, data)
    require(len(result) > 1, 'No supported measured experiment found in this directory.')
    return result
