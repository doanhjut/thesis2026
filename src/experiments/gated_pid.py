"""Cross-fitted uncertainty-gate analysis for a saved event-PID run.

The held-out fold is never used to select its static gate. Gate thresholds are
selected from out-of-fold static predictions belonging to the other folds.
This remains exploratory when the underlying fusion method was developed after
inspecting the same cohort.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (average_precision_score, brier_score_loss,
                             confusion_matrix, roc_auc_score)

from .common import require, sha256, source_metadata, write_json
from .malbehavd_pid import _write_gzip_csv


LOW_GRID = [.001, .005, .01, .025, .05, .075, .1, .15, .2, .25, .3, .35, .4, .45, .5]
HIGH_GRID = [.5, .55, .6, .65, .7, .75, .8, .85, .9, .925, .95, .975, .99, .995, .999]
PRIMARY_METHODS = [
    'Average_50_50', 'Fixed_weight', 'Logistic_stack',
    'Reliability_P', 'Reliability_PI', 'Reliability_PID',
    'Reliability_full_PID',
]


def gate_counts(labels, scores, low, high):
    labels = np.asarray(labels, dtype=int)
    scores = np.asarray(scores, dtype=float)
    early_benign, early_malware = scores < low, scores > high
    routed = ~(early_benign | early_malware)
    positive, negative = labels == 1, labels == 0
    return {
        'routed_fraction': float(routed.mean()),
        'early_fnr_all_positive': float(np.sum(early_benign & positive) / positive.sum()),
        'early_fpr_all_negative': float(np.sum(early_malware & negative) / negative.sum()),
        'routed_rows': int(routed.sum()),
    }


def select_gate_grid(labels, scores, error_cap, lows=LOW_GRID, highs=HIGH_GRID):
    """Minimize routing subject to validation-only early-FN/FP constraints."""
    require(0 <= error_cap < .5, 'Gate error cap must be in [0,.5).')
    feasible = []
    for low in lows:
        for high in highs:
            if low > high:
                continue
            measured = gate_counts(labels, scores, low, high)
            if (measured['early_fnr_all_positive'] <= error_cap and
                    measured['early_fpr_all_negative'] <= error_cap):
                feasible.append((measured['routed_fraction'],
                                 measured['early_fnr_all_positive'] + measured['early_fpr_all_negative'],
                                 float(low), float(high), measured))
    require(feasible, 'No feasible gate on the predeclared threshold grid.')
    _, _, low, high, measured = min(feasible, key=lambda row: row[:4])
    return low, high, measured, len(feasible)


def _binary_metrics(labels, scores, predictions):
    labels = np.asarray(labels, dtype=int)
    scores = np.asarray(scores, dtype=float)
    predictions = np.asarray(predictions, dtype=int)
    require(set(np.unique(labels)) == {0, 1}, 'Both classes are required for gate metrics.')
    tn, fp, fn, tp = confusion_matrix(labels, predictions, labels=[0, 1]).ravel()
    return {
        'auc': float(roc_auc_score(labels, scores)),
        'ap': float(average_precision_score(labels, scores)),
        'brier': float(brier_score_loss(labels, scores)),
        'fpr': float(fp / (fp + tn)), 'tpr': float(tp / (tp + fn)),
        'tn': int(tn), 'fp': int(fp), 'fn': int(fn), 'tp': int(tp),
    }


def _bootstrap(frame, left, right, scope, iterations, seed):
    selected = frame[frame.scope == scope]
    scores = selected.pivot(index='row_id', columns='method', values='score')
    decisions = selected.pivot(index='row_id', columns='method', values='predicted_label')
    labels = selected.drop_duplicates('row_id').set_index('row_id').label.loc[scores.index].to_numpy()
    left_score, right_score = scores[left].to_numpy(), scores[right].to_numpy()
    left_decision, right_decision = decisions[left].to_numpy(), decisions[right].to_numpy()
    rng = np.random.default_rng(seed)
    values = {name: [] for name in ['auc', 'ap', 'brier', 'fpr', 'tpr']}
    for _ in range(iterations):
        indices = rng.integers(0, len(labels), len(labels))
        sampled = labels[indices]
        if len(np.unique(sampled)) < 2:
            continue
        negative, positive = sampled == 0, sampled == 1
        values['auc'].append(roc_auc_score(sampled, left_score[indices]) -
                             roc_auc_score(sampled, right_score[indices]))
        values['ap'].append(average_precision_score(sampled, left_score[indices]) -
                            average_precision_score(sampled, right_score[indices]))
        values['brier'].append(brier_score_loss(sampled, left_score[indices]) -
                               brier_score_loss(sampled, right_score[indices]))
        values['fpr'].append(left_decision[indices][negative].mean() -
                             right_decision[indices][negative].mean())
        values['tpr'].append(left_decision[indices][positive].mean() -
                             right_decision[indices][positive].mean())
    return {
        'comparison': f'{left}_minus_{right}', 'scope': scope, 'samples': int(len(labels)),
        'metrics': {name: {
            'mean': float(np.mean(samples)),
            'ci95_low': float(np.quantile(samples, .025)),
            'ci95_high': float(np.quantile(samples, .975)),
            'iterations': int(len(samples)),
        } for name, samples in values.items()},
    }


def _final_predictions(predictions):
    required = {'outer_fold', 'method', 'row_id', 'label', 'score',
                'predicted_label', 'event_count'}
    require(required <= set(predictions), 'Saved event predictions are incomplete.')
    return (predictions.sort_values(['row_id', 'event_count'])
            .groupby(['outer_fold', 'method', 'row_id'], sort=False).tail(1))


def run(source_run, out, primary_error_cap=.01,
        sensitivity_caps=(.005, .01, .02), bootstrap=1000, seed=2026):
    source_run, out = Path(source_run).resolve(), Path(out)
    prediction_path = source_run / 'event_predictions.csv.gz'
    require(prediction_path.is_file(), 'Missing saved event predictions.')
    out.mkdir(parents=True, exist_ok=False)
    predictions = pd.read_csv(prediction_path)
    final = _final_predictions(predictions)
    methods = [method for method in PRIMARY_METHODS if method in set(final.method)]
    require(set(PRIMARY_METHODS) <= set(methods), 'A required gated-fusion baseline is missing.')
    static = final[final.method == 'Static_only'][
        ['outer_fold', 'row_id', 'sha256', 'label', 'score']].rename(columns={'score': 'p_static'})
    require(static.row_id.is_unique, 'Static OOF rows must be unique.')

    gates, metric_rows, decision_frames = [], [], []
    for cap in sensitivity_caps:
        for fold in sorted(static.outer_fold.unique()):
            development = static[static.outer_fold != fold]
            test_static = static[static.outer_fold == fold]
            low, high, development_gate, feasible = select_gate_grid(
                development.label, development.p_static, float(cap))
            test_gate = gate_counts(test_static.label, test_static.p_static, low, high)
            gates.append({
                'error_cap': float(cap), 'outer_fold': int(fold),
                'tau_low': low, 'tau_high': high, 'feasible_settings': feasible,
                **{f'development_{key}': value for key, value in development_gate.items()},
                **{f'test_{key}': value for key, value in test_gate.items()},
            })
            for method in methods:
                method_rows = final[(final.outer_fold == fold) & (final.method == method)]
                merged = method_rows.merge(test_static, on=['outer_fold', 'row_id', 'sha256', 'label'],
                                           validate='one_to_one')
                routed = merged.p_static.between(low, high, inclusive='both')
                hybrid_decision = np.where(
                    merged.p_static < low, 0,
                    np.where(merged.p_static > high, 1, merged.predicted_label)).astype(int)
                hybrid_score = np.where(routed, merged.score, merged.p_static)
                full_metrics = _binary_metrics(merged.label, hybrid_score, hybrid_decision)
                hard = merged[routed].copy()
                require(set(hard.label) == {0, 1}, 'Routed subset became single-class.')
                hard_metrics = _binary_metrics(hard.label, hard.score, hard.predicted_label)
                metric_rows.extend([
                    {'error_cap': float(cap), 'outer_fold': int(fold), 'method': method,
                     'scope': 'end_to_end', 'samples': int(len(merged)),
                     'routed_fraction': float(routed.mean()), **full_metrics},
                    {'error_cap': float(cap), 'outer_fold': int(fold), 'method': method,
                     'scope': 'routed_subset', 'samples': int(len(hard)),
                     'routed_fraction': float(routed.mean()), **hard_metrics},
                ])
                if np.isclose(cap, primary_error_cap):
                    base = merged[['outer_fold', 'row_id', 'sha256', 'label']].copy()
                    end = base.assign(method=method, scope='end_to_end', score=hybrid_score,
                                      predicted_label=hybrid_decision, routed=routed.to_numpy(),
                                      p_static=merged.p_static.to_numpy(), tau_low=low, tau_high=high)
                    routed_frame = base.loc[routed].assign(
                        method=method, scope='routed_subset', score=hard.score.to_numpy(),
                        predicted_label=hard.predicted_label.to_numpy(dtype=int), routed=True,
                        p_static=hard.p_static.to_numpy(), tau_low=low, tau_high=high)
                    decision_frames.extend([end, routed_frame])

    gate_frame = pd.DataFrame(gates)
    metrics = pd.DataFrame(metric_rows)
    decisions = pd.concat(decision_frames, ignore_index=True)
    comparisons = {}
    pairs = [
        ('Reliability_P', 'Fixed_weight'),
        ('Reliability_PID', 'Reliability_P'),
        ('Reliability_full_PID', 'Reliability_PI'),
        ('Reliability_full_PID', 'Average_50_50'),
    ]
    for scope in ['end_to_end', 'routed_subset']:
        for left, right in pairs:
            key = f'{scope}:{left}_minus_{right}'
            comparisons[key] = _bootstrap(decisions, left, right, scope, bootstrap, seed)

    gate_frame.to_csv(out / 'gate_thresholds.csv', index=False)
    metrics.to_csv(out / 'fold_metrics.csv', index=False)
    _write_gzip_csv(decisions, out / 'gated_predictions.csv.gz')
    write_json(out / 'paired_bootstrap.json', comparisons)
    primary = metrics[np.isclose(metrics.error_cap, primary_error_cap)]
    summary_rows = []
    for (scope, method), group in primary.groupby(['scope', 'method']):
        summary_rows.append({
            'scope': scope, 'method': method,
            **{name: {'mean': float(group[name].mean()),
                      'sd': float(group[name].std(ddof=1)), 'n': int(len(group))}
               for name in ['samples', 'routed_fraction', 'auc', 'ap', 'brier', 'fpr', 'tpr']},
        })
    summary = {
        'status': 'exploratory_cross_fitted_static_gate_on_saved_oof_predictions',
        'source_run': str(source_run), 'source_predictions_sha256': sha256(prediction_path),
        'primary_error_cap': primary_error_cap,
        'sensitivity_caps': list(map(float, sensitivity_caps)),
        'gate_selection': (
            'For outer fold k, choose low/high from OOF static predictions in all other folds. '
            'Minimize routed fraction subject to separate early-FNR and early-FPR caps.'),
        'results': summary_rows, 'paired_bootstrap': comparisons,
        'limitations': [
            'The fusion methods were developed after inspecting this cohort; results remain exploratory.',
            'Gate thresholds are cross-fitted across model-specific OOF score distributions, not selected from the current fold model validation scores.',
            'Generic Windows malware labels do not establish ransomware-specific performance.',
            'AUC of the end-to-end hybrid mixes static scores for early decisions and fusion scores for routed samples.',
        ],
        **source_metadata(),
    }
    write_json(out / 'summary.json', summary)
    write_json(out / 'verification.json', {
        'status': 'passed', 'source_prediction_rows': int(len(predictions)),
        'primary_decision_rows': int(len(decisions)),
        'unique_static_oof_rows': int(static.row_id.nunique()),
        'test_fold_used_for_its_gate_selection': False,
    })
    (out / 'REPORT_VI.md').write_text(_report(summary), encoding='utf-8')
    return summary


def _report(summary):
    rows = []
    for result in summary['results']:
        if result['scope'] != 'end_to_end':
            continue
        rows.append(
            f"| {result['method']} | {result['routed_fraction']['mean']*100:.2f}% | "
            f"{result['auc']['mean']:.4f} | {result['fpr']['mean']*100:.2f}% | "
            f"{result['tpr']['mean']*100:.2f}% | {result['brier']['mean']:.4f} |")
    p_fixed = summary['paired_bootstrap']['end_to_end:Reliability_P_minus_Fixed_weight']['metrics']
    full_pi = summary['paired_bootstrap']['end_to_end:Reliability_full_PID_minus_Reliability_PI']['metrics']
    full_average = summary['paired_bootstrap']['end_to_end:Reliability_full_PID_minus_Average_50_50']['metrics']
    return (
        '# Exploratory uncertainty-gated PID\n\n'
        '> Gate của mỗi outer fold được chọn từ OOF predictions thuộc các folds còn lại. '
        'Phương pháp vẫn là exploratory vì fusion đã được phát triển sau khi xem cohort này.\n\n'
        f"Gate chính giới hạn early-FNR và early-FPR trên development ở {summary['primary_error_cap']*100:.1f}%.\n\n"
        '| Phương pháp | Chuyển dynamic | AUC | FPR | TPR | Brier |\n'
        '|---|---:|---:|---:|---:|---:|\n' + '\n'.join(rows) + '\n\n'
        '## Bootstrap ghép cặp\n\n'
        f"- Reliability-P trừ Fixed: ΔFPR {p_fixed['fpr']['mean']*100:+.2f} điểm phần trăm, "
        f"CI 95% [{p_fixed['fpr']['ci95_low']*100:+.2f}; {p_fixed['fpr']['ci95_high']*100:+.2f}]; "
        f"ΔTPR {p_fixed['tpr']['mean']*100:+.2f} điểm phần trăm.\n"
        f"- Full PID trừ PI: ΔFPR {full_pi['fpr']['mean']*100:+.2f} điểm phần trăm, "
        f"CI 95% [{full_pi['fpr']['ci95_low']*100:+.2f}; {full_pi['fpr']['ci95_high']*100:+.2f}]; "
        f"ΔTPR {full_pi['tpr']['mean']*100:+.2f} điểm phần trăm.\n"
        f"- Full PID trừ Average: ΔFPR {full_average['fpr']['mean']*100:+.2f} điểm phần trăm, "
        f"CI 95% [{full_average['fpr']['ci95_low']*100:+.2f}; {full_average['fpr']['ci95_high']*100:+.2f}]; "
        f"ΔTPR {full_average['tpr']['mean']*100:+.2f} điểm phần trăm, "
        f"CI [{full_average['tpr']['ci95_low']*100:+.2f}; {full_average['tpr']['ci95_high']*100:+.2f}].\n\n"
        '## Kết luận\n\n'
        'Gate làm rõ giá trị của adaptive fusion trên nhóm static bất định, nhưng không đảo ngược ablation: '
        'P vẫn có FPR tốt nhất, còn full PID không hơn PI/P. Full PID giảm FPR so với Average nhưng đánh đổi TPR. '
        'Vì vậy run này chưa chứng minh full PID vượt trội.\n'
    )
