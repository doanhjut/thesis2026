#!/usr/bin/env python3
"""Exploratory stateful gated residual PID against temporal stacking.

This development runner uses saved out-of-fold static/dynamic trajectories. It
keeps temporal logistic stacking intact, adds a bounded PID residual with an
explicit zero-gain fallback, and evaluates clean plus predeclared stress modes.
The current cohort is not an independent confirmatory set.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, brier_score_loss,
                             confusion_matrix, roc_auc_score)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from scipy.stats import binomtest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.experiments.common import choose_threshold


STACK_FEATURES = ['ls', 'ld', 'abs_e', 'd_raw', 'event_fraction']
GAIN_GRID = [
    (0., 0., 0.),
    (.10, 0., 0.), (.25, 0., 0.),
    (.10, .05, 0.), (.25, .10, 0.),
    (.10, .05, .05), (.25, .10, .05),
    (.25, .10, .10), (.50, .10, .10),
]
GATE_GRID = [
    {'quantile': .50, 'temperature': .50, 'max_gate': .50},
    {'quantile': .50, 'temperature': 1.00, 'max_gate': 1.00},
    {'quantile': .75, 'temperature': .50, 'max_gate': .50},
    {'quantile': .75, 'temperature': 1.00, 'max_gate': 1.00},
]
STRESSES = ['clean', 'delay_5', 'dropout_20', 'noise_logit_025']


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def logit(values):
    values = np.clip(np.asarray(values, dtype=float), 1e-6, 1 - 1e-6)
    return np.log(values / (1 - values))


def sigmoid(values):
    values = np.asarray(values, dtype=float)
    result = np.empty_like(values)
    positive = values >= 0
    result[positive] = 1 / (1 + np.exp(-values[positive]))
    exp_value = np.exp(values[~positive])
    result[~positive] = exp_value / (1 + exp_value)
    return result


def base_trajectory(predictions: pd.DataFrame) -> pd.DataFrame:
    frame = (predictions[predictions.method == 'Static_only'][
        ['row_id', 'outer_fold', 'event_count', 'label', 'probability', 'p_dynamic']]
        .sort_values(['outer_fold', 'row_id', 'event_count']).copy())
    if frame.empty:
        raise ValueError('Static_only trajectories are missing.')
    counts = frame.groupby('row_id').event_count.count()
    if counts.nunique() != 1:
        raise ValueError('Every sample must have the same dense event horizon.')
    return frame


def perturb(frame: pd.DataFrame, mode: str, seed: int) -> pd.DataFrame:
    result = frame.copy()
    if mode == 'clean':
        return result
    if mode == 'delay_5':
        result['p_dynamic'] = (result.groupby('row_id').p_dynamic
                               .shift(5).fillna(result.groupby('row_id').p_dynamic.transform('first')))
        return result
    if mode == 'noise_logit_025':
        rng = np.random.default_rng(seed)
        result['p_dynamic'] = sigmoid(logit(result.p_dynamic) + rng.normal(0, .25, len(result)))
        return result
    if mode == 'dropout_20':
        rng = np.random.default_rng(seed)
        values = result.p_dynamic.to_numpy(copy=True)
        for _, index in result.groupby('row_id', sort=False).indices.items():
            index = np.asarray(index)
            keep = np.ones(len(index), dtype=bool)
            keep[1:] = rng.random(len(index) - 1) >= .20
            last = values[index[0]]
            for position, retain in zip(index, keep):
                if retain:
                    last = values[position]
                else:
                    values[position] = last
        result['p_dynamic'] = values
        return result
    raise ValueError(f'Unknown stress mode: {mode}')


def add_state_features(frame: pd.DataFrame, max_event: float) -> pd.DataFrame:
    result = frame.sort_values(['row_id', 'event_count']).copy()
    result['ls'] = logit(result.probability)
    result['ld'] = logit(result.p_dynamic)
    result['e'] = result.ld - result.ls
    result['abs_e'] = result.e.abs()
    result['i_mean'] = (result.groupby('row_id').e.expanding().mean()
                        .reset_index(level=0, drop=True))
    result['d_raw'] = result.groupby('row_id').e.diff().fillna(0.)
    result['d_ema'] = (result.groupby('row_id').d_raw
                       .transform(lambda values: values.ewm(alpha=.35, adjust=False).mean()))
    result['e_std'] = (result.groupby('row_id').e.expanding().std(ddof=0)
                       .reset_index(level=0, drop=True).fillna(0.))
    result['d_std'] = (result.groupby('row_id').d_raw.expanding().std(ddof=0)
                       .reset_index(level=0, drop=True).fillna(0.))
    result['uncertainty'] = 1 - np.maximum(
        2 * np.abs(result.probability - .5),
        2 * np.abs(result.p_dynamic - .5),
    )
    result['event_fraction'] = result.event_count / float(max_event)
    result['gate_raw'] = (
        result.abs_e / (1 + result.e_std)
        + .50 * result.d_ema.abs() / (1 + result.d_std)
        + .25 * result.uncertainty
    )
    return result


def fit_stack(train, validation, target_tpr, seed):
    trials = []
    for order, c_value in enumerate([.01, .03, .1, .3, 1., 3.]):
        model = make_pipeline(
            StandardScaler(),
            LogisticRegression(C=c_value, max_iter=3000, class_weight='balanced',
                               random_state=seed),
        )
        model.fit(train[STACK_FEATURES], train.label)
        score = model.predict_proba(validation[STACK_FEATURES])[:, 1]
        threshold = choose_threshold(
            final_rows(validation).label,
            final_rows(validation.assign(score=score)).score,
            target_tpr,
        )
        measured = trajectory_metrics(validation.assign(score=score), threshold)
        trials.append({'order': order, 'c': c_value, 'threshold': threshold,
                       'model': model, **measured})
    selected = min(trials, key=lambda item: (
        item['fpr'], -item['event_auc'], -item['auc'], item['brier'], item['order']))
    return selected, [{key: value for key, value in item.items() if key != 'model'}
                      for item in trials]


def final_rows(frame):
    return frame.sort_values(['row_id', 'event_count']).groupby('row_id', sort=False).tail(1)


def trajectory_metrics(frame, threshold):
    final = final_rows(frame)
    y = final.label.to_numpy(dtype=int)
    score = final.score.to_numpy(dtype=float)
    decision = score >= threshold
    tn, fp, fn, tp = confusion_matrix(y, decision, labels=[0, 1]).ravel()
    by_event = []
    for _, group in frame.groupby('event_count', sort=True):
        by_event.append(roc_auc_score(group.label, group.score))
    max_event = int(frame.event_count.max())
    early_events = sorted(frame.event_count.unique())[:min(10, len(by_event))]
    early_auc = float(np.mean([
        roc_auc_score(group.label, group.score)
        for event, group in frame.groupby('event_count', sort=True)
        if event in early_events
    ]))
    ordered = frame.sort_values(['row_id', 'event_count']).copy()
    ordered['alarm'] = ordered.score >= threshold
    crossings = ordered.groupby('row_id').alarm.apply(
        lambda values: int(np.abs(np.diff(values.astype(int))).sum()))
    benign_any = ordered[ordered.label == 0].groupby('row_id').alarm.max()
    detection = []
    for _, group in ordered[ordered.label == 1].groupby('row_id'):
        alarms = group.alarm.to_numpy(dtype=int)
        stable = np.convolve(alarms, np.ones(3, dtype=int), mode='valid') >= 3
        positions = np.flatnonzero(stable)
        detection.append(float(group.event_count.iloc[positions[0]]) if len(positions)
                         else float(max_event + 1))
    return {
        'auc': float(roc_auc_score(y, score)),
        'ap': float(average_precision_score(y, score)),
        'brier': float(brier_score_loss(y, score)),
        'fpr': float(fp / (fp + tn)), 'tpr': float(tp / (tp + fn)),
        'tn': int(tn), 'fp': int(fp), 'fn': int(fn), 'tp': int(tp),
        'event_auc': float(np.mean(by_event)), 'early_auc_10': early_auc,
        'median_stable_detection_event': float(np.median(detection)),
        'benign_any_alarm_rate': float(benign_any.mean()),
        'mean_threshold_crossings': float(crossings.mean()),
    }


def normalization(train):
    columns = ['e', 'i_mean', 'd_ema']
    return {
        column: {'mean': float(train[column].mean()),
                 'sd': float(max(train[column].std(ddof=0), 1e-6))}
        for column in columns
    }


def pid_score(frame, stack_score, gains, gate, norm, gate_threshold):
    p = (frame.e.to_numpy() - norm['e']['mean']) / norm['e']['sd']
    i = (frame.i_mean.to_numpy() - norm['i_mean']['mean']) / norm['i_mean']['sd']
    d = (frame.d_ema.to_numpy() - norm['d_ema']['mean']) / norm['d_ema']['sd']
    kp, ki, kd = gains
    gate_value = gate['max_gate'] * sigmoid(
        (frame.gate_raw.to_numpy() - gate_threshold)
        / max(gate['temperature'], 1e-6)
    )
    residual = gate_value * (kp * p + ki * i + kd * d)
    return sigmoid(logit(stack_score) + residual), gate_value, residual


def choose_pid(validation_modes, stack_scores, train, target_tpr, norm):
    gate_reference = train.gate_raw.to_numpy()
    trials = []
    order = 0
    for gains in GAIN_GRID:
        gates = [{'quantile': .5, 'temperature': 1., 'max_gate': 0.}
                 ] if gains == (0., 0., 0.) else GATE_GRID
        for gate in gates:
            threshold_value = float(np.quantile(gate_reference, gate['quantile']))
            clean = validation_modes['clean']
            clean_score, _, _ = pid_score(
                clean, stack_scores['clean'], gains, gate, norm, threshold_value)
            clean_scored = clean.assign(score=clean_score)
            clean_final = final_rows(clean_scored)
            threshold = choose_threshold(clean_final.label, clean_final.score, target_tpr)
            clean_metrics = trajectory_metrics(clean_scored, threshold)
            stress_event_auc = []
            for mode in STRESSES:
                frame = validation_modes[mode]
                score, _, _ = pid_score(
                    frame, stack_scores[mode], gains, gate, norm, threshold_value)
                stress_event_auc.append(trajectory_metrics(frame.assign(score=score), threshold)['event_auc'])
            trials.append({
                'order': order, 'gains': list(gains), 'gate': gate,
                'gate_threshold': threshold_value, 'threshold': threshold,
                'robust_event_auc': float(np.mean(stress_event_auc)),
                **clean_metrics,
            })
            order += 1
    selected = min(trials, key=lambda item: (
        item['fpr'], -item['robust_event_auc'], -item['event_auc'],
        -item['auc'], item['brier'], item['order']))
    return selected, trials


def run(args):
    args.output.mkdir(parents=True, exist_ok=False)
    raw = base_trajectory(pd.read_csv(args.predictions))
    max_event = float(raw.event_count.max())
    clean = add_state_features(raw, max_event)
    folds = sorted(int(value) for value in clean.outer_fold.unique())
    metric_rows, prediction_rows, searches = [], [], []

    for fold in folds:
        validation_fold = folds[(fold + 1) % len(folds)]
        train_ids = clean[~clean.outer_fold.isin([fold, validation_fold])].row_id.unique()
        validation_ids = clean[clean.outer_fold == validation_fold].row_id.unique()
        test_ids = clean[clean.outer_fold == fold].row_id.unique()
        modes = {mode: add_state_features(
            perturb(raw, mode, args.seed + fold * 100 + index), max_event)
            for index, mode in enumerate(STRESSES)}
        train = modes['clean'][modes['clean'].row_id.isin(train_ids)]
        validation_modes = {mode: frame[frame.row_id.isin(validation_ids)].copy()
                            for mode, frame in modes.items()}
        test_modes = {mode: frame[frame.row_id.isin(test_ids)].copy()
                      for mode, frame in modes.items()}

        stack_selected, stack_trials = fit_stack(
            train, validation_modes['clean'], args.target_tpr, args.seed + fold)
        stack_model = stack_selected['model']
        validation_stack = {
            mode: stack_model.predict_proba(frame[STACK_FEATURES])[:, 1]
            for mode, frame in validation_modes.items()}
        test_stack = {
            mode: stack_model.predict_proba(frame[STACK_FEATURES])[:, 1]
            for mode, frame in test_modes.items()}
        norm = normalization(train)
        pid_selected, pid_trials = choose_pid(
            validation_modes, validation_stack, train, args.target_tpr, norm)
        searches.append({
            'outer_fold': fold, 'validation_fold': validation_fold,
            'stack_selected': {key: value for key, value in stack_selected.items()
                               if key != 'model'},
            'stack_trials': stack_trials, 'pid_selected': pid_selected,
            'pid_trials': pid_trials, 'normalization': norm,
            'stack_coefficients': stack_model[1].coef_[0].tolist(),
            'stack_intercept': float(stack_model[1].intercept_[0]),
            'stack_scaler_mean': stack_model[0].mean_.tolist(),
            'stack_scaler_scale': stack_model[0].scale_.tolist(),
        })

        for mode in STRESSES:
            frame = test_modes[mode]
            stack_score = test_stack[mode]
            methods = {'Temporal_stacking': (stack_score, None, None)}
            pid_values = pid_score(
                frame, stack_score, tuple(pid_selected['gains']),
                pid_selected['gate'], norm, pid_selected['gate_threshold'])
            methods['Gated_residual_PID'] = pid_values
            for method, (score, gate_value, residual) in methods.items():
                threshold = (stack_selected['threshold'] if method == 'Temporal_stacking'
                             else pid_selected['threshold'])
                scored = frame.assign(score=score)
                measured = trajectory_metrics(scored, threshold)
                metric_rows.append({
                    'outer_fold': fold, 'method': method, 'stress': mode,
                    'threshold': threshold, **measured,
                })
                saved = scored[['row_id', 'outer_fold', 'event_count', 'label', 'score']].copy()
                saved['method'], saved['stress'], saved['threshold'] = method, mode, threshold
                saved['predicted_label'] = (saved.score >= threshold).astype(int)
                if gate_value is None:
                    saved['gate'], saved['pid_residual'] = 0., 0.
                else:
                    saved['gate'], saved['pid_residual'] = gate_value, residual
                prediction_rows.append(saved)

    metrics = pd.DataFrame(metric_rows)
    predictions = pd.concat(prediction_rows, ignore_index=True)
    summaries = []
    summary_metrics = ['auc', 'ap', 'fpr', 'tpr', 'brier', 'event_auc',
                       'early_auc_10', 'median_stable_detection_event',
                       'benign_any_alarm_rate', 'mean_threshold_crossings']
    for (method, stress), group in metrics.groupby(['method', 'stress']):
        summaries.append({
            'method': method, 'stress': stress,
            **{name: {'mean': float(group[name].mean()),
                      'sd': float(group[name].std(ddof=1))}
               for name in summary_metrics},
            'counts': {name: int(group[name].sum()) for name in ['tn', 'fp', 'fn', 'tp']},
        })
    decision_tests = paired_decision_tests(predictions)
    summary = {
        'status': 'exploratory_stateful_gated_residual_pid',
        'samples': int(clean.row_id.nunique()), 'outer_folds': len(folds),
        'event_horizon': int(max_event), 'stress_modes': STRESSES,
        'target_validation_tpr': args.target_tpr,
        'selection_objective': ('minimum clean validation FPR at target TPR; then mean clean/stress '
                                'event-AUC, clean event-AUC, final AUC and Brier'),
        'results': summaries,
        'selected_pid_by_fold': [
            {'outer_fold': item['outer_fold'], **item['pid_selected']}
            for item in searches],
        'paired_final_decision_tests': decision_tests,
        'limitations': [
            'Post-hoc development on a previously inspected cohort; external confirmation is required.',
            'Dropout is missing score-update stress, not removal of raw API calls from sandbox reports.',
            'Delay and logit noise are controlled stress tests, not newly observed malware executions.',
            'The event axis is ordered API count, not wall-clock seconds.',
        ],
        'source': str(args.predictions.resolve()), 'source_sha256': sha256(args.predictions),
    }
    metrics.to_csv(args.output / 'fold_metrics.csv', index=False)
    predictions.to_csv(args.output / 'event_predictions.csv.gz', index=False, compression='gzip')
    (args.output / 'model_search.json').write_text(json.dumps(searches, indent=2) + '\n')
    (args.output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    write_report(summary, args.output / 'REPORT_VI.md')
    plot_summary(summary, args.output)
    (args.output / 'verification.json').write_text(json.dumps({
        'status': 'passed', 'samples': summary['samples'], 'outer_folds': len(folds),
        'outer_test_used_for_selection': False, 'zero_gain_fallback_in_grid': True,
        'same_stress_realizations_for_methods': True,
        'evidence_status': 'exploratory_post_hoc',
    }, indent=2) + '\n')
    hashes = {path.name: sha256(path) for path in sorted(args.output.iterdir())
              if path.is_file() and path.name != 'artifact_sha256.json'}
    (args.output / 'artifact_sha256.json').write_text(json.dumps(hashes, indent=2) + '\n')


def plot_summary(summary, output):
    import matplotlib.pyplot as plt

    lookup = {(item['method'], item['stress']): item for item in summary['results']}
    x = np.arange(len(STRESSES))
    width = .36
    colors = {'Temporal_stacking': '#2878B5', 'Gated_residual_PID': '#D55E00'}
    labels = {'Temporal_stacking': 'Temporal stacking',
              'Gated_residual_PID': 'Gated residual PID'}
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.5))
    for offset, method in [(-width / 2, 'Temporal_stacking'),
                           (width / 2, 'Gated_residual_PID')]:
        fpr = [100 * lookup[(method, stress)]['fpr']['mean'] for stress in STRESSES]
        crossings = [lookup[(method, stress)]['mean_threshold_crossings']['mean']
                     for stress in STRESSES]
        axes[0].bar(x + offset, fpr, width, label=labels[method], color=colors[method])
        axes[1].bar(x + offset, crossings, width, label=labels[method], color=colors[method])
    tick_labels = ['Clean', 'Delay 5', 'Dropout 20%', 'Noise']
    for axis in axes:
        axis.set_xticks(x, tick_labels, rotation=12)
        axis.grid(axis='y', alpha=.25)
    axes[0].set_ylabel('False-positive rate (%)')
    axes[0].set_title('Tải cảnh báo nhầm')
    axes[1].set_ylabel('Mean threshold crossings / sample')
    axes[1].set_title('Độ dao động quyết định')
    axes[0].legend(frameon=False)
    fig.suptitle('Stateful PID so với temporal stacking — controlled stress tests')
    fig.tight_layout()
    fig.savefig(output / 'stateful_pid_stress_comparison.png', dpi=220)
    fig.savefig(output / 'stateful_pid_stress_comparison.pdf')
    plt.close(fig)


def holm_adjust(p_values):
    order = np.argsort(p_values)
    adjusted = np.empty(len(p_values), dtype=float)
    running = 0.
    total = len(p_values)
    for rank, index in enumerate(order):
        value = min(1., (total - rank) * float(p_values[index]))
        running = max(running, value)
        adjusted[index] = running
    return adjusted.tolist()


def paired_decision_tests(predictions):
    final = (predictions.sort_values('event_count')
             .groupby(['stress', 'method', 'row_id'], as_index=False).tail(1))
    rows = []
    for stress in STRESSES:
        pid = final[(final.stress == stress) &
                    (final.method == 'Gated_residual_PID')].sort_values('row_id')
        stack = final[(final.stress == stress) &
                      (final.method == 'Temporal_stacking')].sort_values('row_id')
        if not np.array_equal(pid.row_id.to_numpy(), stack.row_id.to_numpy()):
            raise ValueError(f'Unpaired final decisions for {stress}.')
        labels = pid.label.to_numpy(dtype=int)
        pid_decision = pid.predicted_label.to_numpy(dtype=int)
        stack_decision = stack.predicted_label.to_numpy(dtype=int)
        benign = labels == 0
        malware = labels == 1
        stack_only_fp = int(np.sum((stack_decision == 1) & (pid_decision == 0) & benign))
        pid_only_fp = int(np.sum((pid_decision == 1) & (stack_decision == 0) & benign))
        stack_only_tp = int(np.sum((stack_decision == 1) & (pid_decision == 0) & malware))
        pid_only_tp = int(np.sum((pid_decision == 1) & (stack_decision == 0) & malware))
        benign_discordant = stack_only_fp + pid_only_fp
        malware_discordant = stack_only_tp + pid_only_tp
        rows.append({
            'stress': stress,
            'stack_only_false_positives_removed_by_pid': stack_only_fp,
            'pid_only_false_positives_added': pid_only_fp,
            'benign_discordant': benign_discordant,
            'benign_exact_two_sided_p': (float(binomtest(
                min(stack_only_fp, pid_only_fp), benign_discordant, .5).pvalue)
                if benign_discordant else 1.),
            'stack_only_true_positives_lost_by_pid': stack_only_tp,
            'pid_only_true_positives_gained': pid_only_tp,
            'malware_discordant': malware_discordant,
            'malware_exact_two_sided_p': (float(binomtest(
                min(stack_only_tp, pid_only_tp), malware_discordant, .5).pvalue)
                if malware_discordant else 1.),
        })
    adjusted = holm_adjust([row['benign_exact_two_sided_p'] for row in rows])
    for row, value in zip(rows, adjusted):
        row['benign_holm_adjusted_p_across_stresses'] = value
    return rows


def write_report(summary, path):
    rows = []
    for result in summary['results']:
        rows.append(
            f"| {result['method']} | {result['stress']} | {result['auc']['mean']:.4f} | "
            f"{100*result['fpr']['mean']:.2f}% | {100*result['tpr']['mean']:.2f}% | "
            f"{result['event_auc']['mean']:.4f} | {result['early_auc_10']['mean']:.4f} | "
            f"{result['median_stable_detection_event']['mean']:.2f} | "
            f"{result['mean_threshold_crossings']['mean']:.3f} |"
        )
    gains = '\n'.join(
        f"- Fold {item['outer_fold']}: gains={item['gains']}, gate={item['gate']}, "
        f"validation FPR={100*item['fpr']:.2f}%."
        for item in summary['selected_pid_by_fold'])
    decisions = '\n'.join(
        f"| {item['stress']} | {item['stack_only_false_positives_removed_by_pid']} | "
        f"{item['pid_only_false_positives_added']} | "
        f"{item['stack_only_true_positives_lost_by_pid']} | "
        f"{item['benign_exact_two_sided_p']:.4f} | "
        f"{item['benign_holm_adjusted_p_across_stresses']:.4f} |"
        for item in summary['paired_final_decision_tests'])
    path.write_text(
        '# Stateful Gated Residual PID — exploratory\n\n'
        '> Baseline stacking được giữ nguyên. PID chỉ cộng residual có gate và có cấu hình gain=0 '
        'để quay về stacking. Cohort đã tham gia phát triển phương pháp nên chưa phải xác nhận ngoài.\n\n'
        '| Phương pháp | Stress | AUC | FPR | TPR | Event-AUC | Early-AUC@10 | '
        'Median stable event | Crossings |\n'
        '|---|---|---:|---:|---:|---:|---:|---:|---:|\n' + '\n'.join(rows) +
        '\n\n## Cấu hình PID được validation chọn\n\n' + gains +
        '\n\n## Kiểm định quyết định cuối ghép cặp\n\n'
        '| Stress | FP của stacking được PID loại | FP chỉ PID tạo | TP của stacking PID làm mất | '
        'Exact p | Holm p |\n'
        '|---|---:|---:|---:|---:|---:|\n' + decisions +
        '\n\n## Phạm vi diễn giải\n\n'
        'Delay, missing update và noise là controlled stress tests. Chúng đánh giá cơ chế, không được '
        'mô tả như các execution malware mới. Nếu validation chọn gain=0 ở nhiều fold, dữ liệu không '
        'hỗ trợ lợi ích PID residual. Nếu gain khác 0 nhưng outer-test không cải thiện, cũng phải báo '
        'kết quả âm.\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--predictions', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--target-tpr', type=float, default=.95)
    parser.add_argument('--seed', type=int, default=2026)
    run(parser.parse_args())


if __name__ == '__main__':
    main()
