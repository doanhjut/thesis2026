"""Validation-only calibration and uncertainty-gate analysis for saved AL models."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss
from sklearn.model_selection import train_test_split

from .common import require, sha256, source_metadata, stats, write_json
from .fusion import al_final_predictions


def _logit(values, epsilon=1e-9):
    p = np.clip(np.asarray(values, dtype=float), epsilon, 1 - epsilon)
    return np.log(p / (1 - p))


def _ece(y, p, bins=10):
    y, p = np.asarray(y), np.asarray(p)
    edges = np.linspace(0, 1, bins + 1)
    total = 0.0
    for left, right in zip(edges[:-1], edges[1:]):
        selected = (p >= left) & ((p < right) if right < 1 else (p <= right))
        if selected.any():
            total += selected.mean() * abs(y[selected].mean() - p[selected].mean())
    return float(total)


def fit_platt(y, p):
    model = LogisticRegression(C=1e6, solver='lbfgs', random_state=2026)
    model.fit(_logit(p)[:, None], np.asarray(y, dtype=int))
    return model


def calibrate(model, p):
    return model.predict_proba(_logit(p)[:, None])[:, 1]


def gate_counts(y, p, low, high):
    y, p = np.asarray(y, dtype=int), np.asarray(p, dtype=float)
    early_benign, early_malicious = p < low, p > high
    routed = ~(early_benign | early_malicious)
    positives, negatives = max(1, int((y == 1).sum())), max(1, int((y == 0).sum()))
    return {
        'routed_fraction': float(routed.mean()),
        'early_decision_fraction': float((~routed).mean()),
        'early_false_negative_rate_all_positives': float(np.sum(early_benign & (y == 1)) / positives),
        'early_false_positive_rate_all_negatives': float(np.sum(early_malicious & (y == 0)) / negatives),
        'early_false_negatives': int(np.sum(early_benign & (y == 1))),
        'early_false_positives': int(np.sum(early_malicious & (y == 0))),
        'routed_rows': int(routed.sum()),
        'early_rows': int((~routed).sum()),
    }


def select_gate(y, p, max_early_fnr=.02, max_early_fpr=.02):
    require(0 <= max_early_fnr <= 1 and 0 <= max_early_fpr <= 1, 'Invalid gate error constraints.')
    candidates = np.unique(np.r_[0., p, 1.])
    feasible = []
    for i, low in enumerate(candidates):
        for high in candidates[i:]:
            measured = gate_counts(y, p, low, high)
            if (measured['early_false_negative_rate_all_positives'] <= max_early_fnr and
                    measured['early_false_positive_rate_all_negatives'] <= max_early_fpr):
                feasible.append((measured['routed_fraction'],
                                 measured['early_false_negative_rate_all_positives'] + measured['early_false_positive_rate_all_negatives'],
                                 float(low), float(high), measured))
    require(feasible, 'No feasible gate; routing every row should always be feasible.')
    _, _, low, high, measured = min(feasible, key=lambda row: row[:4])
    return low, high, measured, len(feasible)


def _decisions(frame, low, high):
    action = np.full(len(frame), 'dynamic', dtype=object)
    action[frame.calibrated_probability.to_numpy() < low] = 'early_benign'
    action[frame.calibrated_probability.to_numpy() > high] = 'early_malicious'
    result = frame[['seed', 'method', 'split', 'row_id', 'label', 'probability', 'calibrated_probability']].copy()
    result['gate_action'] = action
    result['tau_low'], result['tau_high'] = low, high
    return result


def run(al_run, out, calibration_fraction=.5, partition_seed=2026,
        max_early_fnr=.02, max_early_fpr=.02):
    require(0.2 <= calibration_fraction <= 0.8, 'Calibration fraction must be in [0.2, 0.8].')
    predictions, al_config = al_final_predictions(al_run)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    reference = predictions[predictions.split == 'validation'][['row_id', 'label']].drop_duplicates()
    require(reference.row_id.is_unique, 'Validation labels differ across saved AL models.')
    calibration_ids, selection_ids = train_test_split(
        reference.row_id.to_numpy(), train_size=calibration_fraction,
        random_state=partition_seed, stratify=reference.label.to_numpy())
    write_json(out / 'validation_partition.json', {
        'calibration_row_ids': sorted(map(int, calibration_ids)),
        'gate_selection_row_ids': sorted(map(int, selection_ids)),
    })
    config = {
        'kind': 'static_uncertainty_gate', 'al_run': str(Path(al_run).resolve()),
        'al_dataset_sha256': al_config['dataset']['data_sha256'],
        'al_predictions': 'Final-round saved probabilities only.',
        'calibration': 'Platt scaling fit on the calibration subset of the original validation split.',
        'gate_selection': 'Minimize routed fraction subject to early error constraints on the disjoint gate-selection subset.',
        'partition_seed': partition_seed, 'calibration_fraction': calibration_fraction,
        'max_early_fnr': max_early_fnr, 'max_early_fpr': max_early_fpr,
        'scope': 'Static gate only. Routed rows have no final decision until real dynamic evidence is supplied.',
        'al_predictions_sha256': sha256(Path(al_run) / 'predictions.csv.gz'),
        **source_metadata(),
    }
    write_json(out / 'config.json', config)
    rows, calibration_rows, decisions = [], [], []
    calibration_ids, selection_ids = set(calibration_ids), set(selection_ids)
    for (seed, method), group in predictions.groupby(['seed', 'method']):
        validation = group[group.split == 'validation'].copy()
        test = group[group.split == 'test'].copy()
        cal = validation[validation.row_id.isin(calibration_ids)].copy()
        selection = validation[validation.row_id.isin(selection_ids)].copy()
        require(len(cal) + len(selection) == len(validation), 'Validation partition is incomplete.')
        model = fit_platt(cal.label, cal.probability)
        for frame in [cal, selection, test]:
            frame['calibrated_probability'] = calibrate(model, frame.probability)
        for split, frame in [('calibration', cal), ('gate_selection', selection), ('test', test)]:
            calibration_rows.append({
                'seed': int(seed), 'method': method, 'split': split,
                'brier_uncalibrated': float(brier_score_loss(frame.label, frame.probability)),
                'brier_calibrated': float(brier_score_loss(frame.label, frame.calibrated_probability)),
                'ece_uncalibrated': _ece(frame.label.to_numpy(), frame.probability.to_numpy()),
                'ece_calibrated': _ece(frame.label.to_numpy(), frame.calibrated_probability.to_numpy()),
                'platt_coefficient': float(model.coef_[0, 0]), 'platt_intercept': float(model.intercept_[0]),
            })
        low, high, selected_metrics, feasible_count = select_gate(
            selection.label.to_numpy(), selection.calibrated_probability.to_numpy(), max_early_fnr, max_early_fpr)
        test_metrics = gate_counts(test.label, test.calibrated_probability, low, high)
        rows.append({'seed': int(seed), 'method': method, 'tau_low': low, 'tau_high': high,
                     'feasible_validation_settings': feasible_count,
                     **{f'validation_{k}': v for k, v in selected_metrics.items()},
                     **{f'test_{k}': v for k, v in test_metrics.items()}})
        decisions.extend([_decisions(selection, low, high), _decisions(test, low, high)])
    metrics = pd.DataFrame(rows)
    metrics.to_csv(out / 'gate_metrics.csv', index=False)
    pd.DataFrame(calibration_rows).to_csv(out / 'calibration_metrics.csv', index=False)
    pd.concat(decisions, ignore_index=True).to_csv(out / 'gate_decisions.csv.gz', index=False)
    summary = {
        'status': 'measured_static_gate_only',
        'methods': [{
            'method': method,
            'test_routed_fraction': stats(g.test_routed_fraction),
            'test_early_false_negative_rate_all_positives': stats(g.test_early_false_negative_rate_all_positives),
            'test_early_false_positive_rate_all_negatives': stats(g.test_early_false_positive_rate_all_negatives),
        } for method, g in metrics.groupby('method')],
        'limitations': [
            config['scope'],
            'Threshold feasibility is estimated from half of a 400-row validation split and is therefore coarse.',
            'The same test split is shared across seeds; seed SD is not a population confidence interval.',
            'Calibration/gating does not establish ransomware-specific validity without source provenance.',
        ],
    }
    write_json(out / 'summary.json', summary)
    lines = [
        '# Kết quả static uncertainty gate', '',
        f'Calibration dùng {calibration_fraction:.0%} validation; phần còn lại chọn gate với giới hạn '
        f'early-FNR={max_early_fnr:.2%}, early-FPR={max_early_fpr:.2%}.', '',
        '| Phương pháp | Test chuyển dynamic | Early FN / tổng positive | Early FP / tổng negative |',
        '|---|---:|---:|---:|',
    ]
    for method, group in metrics.groupby('method'):
        def mean_sd(column):
            values = group[column].to_numpy() * 100
            return f'{values.mean():.2f}% ± {values.std(ddof=1):.2f}%'
        lines.append(f'| {method} | {mean_sd("test_routed_fraction")} | '
                     f'{mean_sd("test_early_false_negative_rate_all_positives")} | '
                     f'{mean_sd("test_early_false_positive_rate_all_negatives")} |')
    lines += ['', 'Đây mới là gate tĩnh: các dòng được chuyển dynamic chưa có final decision. '
              'Không diễn giải routed fraction thành mức tiết kiệm end-to-end trước khi đo sandbox và full-traffic quality.', '',
              *summary['limitations']]
    (out / 'REPORT.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    write_json(out / 'verification.json', verify(out, al_run))
    return summary


def verify(out, al_run=None):
    out = Path(out)
    config = json.loads((out / 'config.json').read_text())
    predictions, al_config = al_final_predictions(al_run or config['al_run'])
    require(al_config['dataset']['data_sha256'] == config['al_dataset_sha256'], 'Gate dataset checksum changed.')
    require(sha256(Path(al_run or config['al_run']) / 'predictions.csv.gz') == config['al_predictions_sha256'],
            'Saved AL predictions changed.')
    partition = json.loads((out / 'validation_partition.json').read_text())
    calibration_ids, selection_ids = set(partition['calibration_row_ids']), set(partition['gate_selection_row_ids'])
    metrics = pd.read_csv(out / 'gate_metrics.csv', float_precision='round_trip')
    saved_calibration = pd.read_csv(out / 'calibration_metrics.csv', float_precision='round_trip')
    saved_decisions = pd.read_csv(out / 'gate_decisions.csv.gz', float_precision='round_trip')
    checked = 0
    for row in metrics.itertuples():
        group = predictions[(predictions.seed == row.seed) & (predictions.method == row.method)]
        validation, test = group[group.split == 'validation'].copy(), group[group.split == 'test'].copy()
        cal = validation[validation.row_id.isin(calibration_ids)].copy()
        selection = validation[validation.row_id.isin(selection_ids)].copy()
        model = fit_platt(cal.label, cal.probability)
        parameters = saved_calibration[(saved_calibration.seed == row.seed) &
                                       (saved_calibration.method == row.method)].iloc[0]
        require(np.allclose(model.coef_[0, 0], parameters.platt_coefficient, rtol=1e-9, atol=1e-10), 'Platt coefficient mismatch.')
        require(np.allclose(model.intercept_[0], parameters.platt_intercept, rtol=1e-9, atol=1e-10), 'Platt intercept mismatch.')
        for split, frame in [('gate_selection', selection), ('test', test)]:
            frame['calibrated_probability'] = calibrate(model, frame.probability)
            measured = gate_counts(frame.label, frame.calibrated_probability, row.tau_low, row.tau_high)
            prefix = 'validation' if split == 'gate_selection' else 'test'
            for key, value in measured.items():
                require(np.allclose(value, getattr(row, f'{prefix}_{key}'), rtol=1e-9, atol=1e-10), f'Gate metric mismatch: {prefix}_{key}')
            expected = _decisions(frame, row.tau_low, row.tau_high).sort_values('row_id')
            saved = saved_decisions[(saved_decisions.seed == row.seed) & (saved_decisions.method == row.method) &
                                    (saved_decisions.split == ('validation' if split == 'gate_selection' else 'test'))].sort_values('row_id')
            require(np.array_equal(expected.row_id.to_numpy(), saved.row_id.to_numpy()), 'Gate decision IDs differ.')
            require(np.array_equal(expected.gate_action.to_numpy(), saved.gate_action.to_numpy()), 'Gate actions differ.')
            require(np.allclose(expected.calibrated_probability, saved.calibrated_probability, rtol=1e-9, atol=1e-10),
                    'Calibrated probabilities differ.')
            checked += len(frame)
    return {'status': 'passed', 'model_gate_pairs_replayed': len(metrics), 'decision_rows_replayed': checked}
