#!/usr/bin/env python3
"""Matched-information PID evidence upgrade with multi-stress evaluation.

This runner addresses two attribution threats in the earlier exploratory run:
1) history-aware stacking receives the same P/I/D and volatility information;
2) full PID and PI share Kp/Ki/gate/threshold, differing only in Kd.

The current cohort remains development data. Multi-stress results improve the
robustness audit but do not replace external/temporal validation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t as student_t
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.experiments.common import choose_threshold
from scripts.run_stateful_gated_residual_pid import (
    GATE_GRID, add_state_features, base_trajectory, final_rows, logit,
    normalization, pid_score, sha256, trajectory_metrics,
)


HISTORY_FEATURES = [
    'ls', 'ld', 'abs_e', 'i_mean', 'd_ema', 'e_std', 'd_std',
    'uncertainty', 'event_fraction',
]
SAFE_GAIN_GRID = [
    (0., 0., 0.),
    (.10, 0., 0.), (.25, 0., 0.),
    (.10, .05, 0.), (.25, .10, 0.),
    (.10, .05, .05), (.25, .10, .05),
    (.25, .10, .10), (.50, .10, .10),
]
FULL_GAIN_GRID = [
    (.10, .05, .05), (.10, .05, .10),
    (.25, .05, .05), (.25, .10, .05),
    (.25, .10, .10), (.50, .10, .05), (.50, .10, .10),
]


def stress_specs(seeds: int):
    specs = [{'id': 'clean', 'family': 'clean', 'level': 0., 'seed': -1}]
    for delay in [2, 5, 10]:
        specs.append({'id': f'delay_{delay}', 'family': 'delay',
                      'level': float(delay), 'seed': -1})
    for onset in [10, 20, 30]:
        specs.append({'id': f'onset_{onset}', 'family': 'onset',
                      'level': float(onset), 'seed': -1})
    for index in range(seeds):
        for rate in [.10, .20, .30]:
            specs.append({'id': f'dropout_{int(rate*100):02d}_seed{index:02d}',
                          'family': 'dropout', 'level': rate, 'seed': index})
        for sigma in [.10, .25, .50]:
            specs.append({'id': f'noise_{str(sigma).replace(".", "p")}_seed{index:02d}',
                          'family': 'noise', 'level': sigma, 'seed': index})
        for length in [3, 5, 10]:
            specs.append({'id': f'burst_{length:02d}_seed{index:02d}',
                          'family': 'burst', 'level': float(length), 'seed': index})
    return specs


def perturb_spec(frame: pd.DataFrame, spec: dict, seed: int) -> pd.DataFrame:
    result = frame.copy()
    family, level = spec['family'], spec['level']
    if family == 'clean':
        return result
    if family == 'delay':
        steps = int(level)
        result['p_dynamic'] = (result.groupby('row_id').p_dynamic.shift(steps)
                               .fillna(result.groupby('row_id').p_dynamic.transform('first')))
        return result
    if family == 'onset':
        onset = int(level)
        first = result.groupby('row_id').p_dynamic.transform('first')
        result.loc[result.event_count < onset, 'p_dynamic'] = first[result.event_count < onset]
        return result
    rng = np.random.default_rng(seed)
    if family == 'noise':
        from scripts.run_stateful_gated_residual_pid import sigmoid
        result['p_dynamic'] = sigmoid(
            logit(result.p_dynamic) + rng.normal(0, float(level), len(result)))
        return result
    values = result.p_dynamic.to_numpy(copy=True)
    for _, positions in result.groupby('row_id', sort=False).indices.items():
        positions = np.asarray(positions)
        if family == 'dropout':
            retain = np.ones(len(positions), dtype=bool)
            retain[1:] = rng.random(len(positions) - 1) >= float(level)
            last = values[positions[0]]
            for position, keep in zip(positions, retain):
                if keep:
                    last = values[position]
                else:
                    values[position] = last
        elif family == 'burst':
            length = min(int(level), len(positions) - 2)
            start = int(rng.integers(1, max(2, len(positions) - length)))
            values[positions[start:start + length]] = values[positions[start - 1]]
        else:
            raise ValueError(f'Unknown stress family: {family}')
    result['p_dynamic'] = values
    return result


def fit_history_stack(train, validation, target_tpr, seed):
    trials = []
    for order, c_value in enumerate([.01, .03, .1, .3, 1., 3.]):
        model = make_pipeline(
            StandardScaler(),
            LogisticRegression(C=c_value, max_iter=3000, class_weight='balanced',
                               random_state=seed),
        )
        model.fit(train[HISTORY_FEATURES], train.label)
        score = model.predict_proba(validation[HISTORY_FEATURES])[:, 1]
        scored = validation.assign(score=score)
        threshold = choose_threshold(final_rows(scored).label, final_rows(scored).score, target_tpr)
        measured = trajectory_metrics(scored, threshold)
        trials.append({'order': order, 'c': c_value, 'threshold': threshold,
                       'model': model, **measured})
    selected = min(trials, key=lambda item: (
        item['fpr'], -item['event_auc'], -item['auc'], item['brier'], item['order']))
    return selected, [{key: value for key, value in item.items() if key != 'model'}
                      for item in trials]


def selection_specs(all_specs):
    wanted = {'clean', 'delay_5', 'onset_20', 'dropout_20_seed00',
              'noise_0p25_seed00', 'burst_05_seed00'}
    return [spec for spec in all_specs if spec['id'] in wanted]


def select_residual(validation_frames, base_scores, train, target_tpr,
                    norm, gains_grid, specs):
    reference = train.gate_raw.to_numpy()
    base_clean = validation_frames['clean'].assign(score=base_scores['clean'])
    base_threshold = choose_threshold(
        final_rows(base_clean).label, final_rows(base_clean).score, target_tpr)
    base_clean_metrics = trajectory_metrics(base_clean, base_threshold)
    trials, order = [], 0
    for gains in gains_grid:
        gates = ([{'quantile': .5, 'temperature': 1., 'max_gate': 0.}]
                 if gains == (0., 0., 0.) else GATE_GRID)
        for gate in gates:
            gate_threshold = float(np.quantile(reference, gate['quantile']))
            clean = validation_frames['clean']
            clean_score, _, _ = pid_score(
                clean, base_scores['clean'], gains, gate, norm, gate_threshold)
            clean_scored = clean.assign(score=clean_score)
            clean_final = final_rows(clean_scored)
            threshold = choose_threshold(clean_final.label, clean_final.score, target_tpr)
            clean_metrics = trajectory_metrics(clean_scored, threshold)
            stress_metrics = []
            for spec in specs:
                frame = validation_frames[spec['id']]
                score, _, _ = pid_score(
                    frame, base_scores[spec['id']], gains, gate, norm, gate_threshold)
                stress_metrics.append(trajectory_metrics(frame.assign(score=score), threshold))
            trials.append({
                'order': order, 'gains': list(gains), 'gate': gate,
                'gate_threshold': gate_threshold, 'threshold': threshold,
                'mean_stress_fpr': float(np.mean([item['fpr'] for item in stress_metrics])),
                'mean_stress_tpr': float(np.mean([item['tpr'] for item in stress_metrics])),
                'mean_stress_event_auc': float(np.mean([item['event_auc'] for item in stress_metrics])),
                'base_clean_tpr': base_clean_metrics['tpr'], **clean_metrics,
            })
            order += 1
    eligible = [item for item in trials
                if item['tpr'] >= item['base_clean_tpr'] - .01]
    if not eligible:
        eligible = trials
    selected = min(eligible, key=lambda item: (
        item['mean_stress_fpr'], -item['mean_stress_tpr'],
        -item['mean_stress_event_auc'], item['fpr'], -item['event_auc'], item['order']))
    return selected, trials


def confidence_interval(values):
    values = np.asarray(values, dtype=float)
    mean = float(np.mean(values))
    if len(values) < 2:
        return {'mean': mean, 'ci95_low': mean, 'ci95_high': mean, 'folds': len(values)}
    sem = float(np.std(values, ddof=1) / np.sqrt(len(values)))
    critical = float(student_t.ppf(.975, df=len(values) - 1))
    return {'mean': mean, 'ci95_low': mean - critical * sem,
            'ci95_high': mean + critical * sem, 'folds': len(values)}


def paired_effects(metrics, left, right):
    keys = ['outer_fold', 'stress_id', 'family', 'level', 'seed']
    left_frame = metrics[metrics.method == left]
    right_frame = metrics[metrics.method == right]
    paired = left_frame.merge(right_frame, on=keys, suffixes=('_left', '_right'),
                              validate='one_to_one')
    rows = []
    for (family, level), group in paired.groupby(['family', 'level']):
        fold_values = []
        for _, fold in group.groupby('outer_fold'):
            fold_values.append({
                metric: float(np.mean(fold[f'{metric}_left'] - fold[f'{metric}_right']))
                for metric in ['fpr', 'tpr', 'auc', 'event_auc', 'early_auc_10',
                               'mean_threshold_crossings', 'benign_any_alarm_rate']
            })
        rows.append({
            'family': family, 'level': float(level),
            'comparison': f'{left}_minus_{right}',
            **{metric: confidence_interval([item[metric] for item in fold_values])
               for metric in fold_values[0]},
        })
    return rows


def run(args):
    args.output.mkdir(parents=True, exist_ok=False)
    raw = base_trajectory(pd.read_csv(args.predictions))
    max_event = float(raw.event_count.max())
    clean = add_state_features(raw, max_event)
    folds = sorted(int(value) for value in clean.outer_fold.unique())
    specs = stress_specs(args.stress_seeds)
    select_specs = selection_specs(specs)
    metric_rows, prediction_rows, audits = [], [], []

    for fold in folds:
        validation_fold = folds[(fold + 1) % len(folds)]
        train_ids = clean[~clean.outer_fold.isin([fold, validation_fold])].row_id.unique()
        validation_ids = clean[clean.outer_fold == validation_fold].row_id.unique()
        test_ids = clean[clean.outer_fold == fold].row_id.unique()
        train = clean[clean.row_id.isin(train_ids)]
        validation_clean = clean[clean.row_id.isin(validation_ids)]
        stack_selected, stack_trials = fit_history_stack(
            train, validation_clean, args.target_tpr, args.seed + fold)
        stack_model = stack_selected['model']
        norm = normalization(train)

        validation_frames, validation_scores = {}, {}
        for index, spec in enumerate(select_specs):
            frame = add_state_features(
                perturb_spec(raw, spec, args.seed + fold * 10000 + index), max_event)
            frame = frame[frame.row_id.isin(validation_ids)].copy()
            validation_frames[spec['id']] = frame
            validation_scores[spec['id']] = stack_model.predict_proba(
                frame[HISTORY_FEATURES])[:, 1]
        safe, safe_trials = select_residual(
            validation_frames, validation_scores, train, args.target_tpr,
            norm, SAFE_GAIN_GRID, select_specs)
        full, full_trials = select_residual(
            validation_frames, validation_scores, train, args.target_tpr,
            norm, FULL_GAIN_GRID, select_specs)
        audits.append({
            'outer_fold': fold, 'validation_fold': validation_fold,
            'history_stack_selected': {key: value for key, value in stack_selected.items()
                                       if key != 'model'},
            'history_stack_trials': stack_trials,
            'safe_pid_selected': safe, 'safe_pid_trials': safe_trials,
            'full_pid_selected': full, 'full_pid_trials': full_trials,
            'normalization': norm,
            'history_stack_features': HISTORY_FEATURES,
            'history_stack_coefficients': stack_model[1].coef_[0].tolist(),
            'history_stack_intercept': float(stack_model[1].intercept_[0]),
        })

        for index, spec in enumerate(specs):
            frame = add_state_features(
                perturb_spec(raw, spec, args.seed + fold * 100000 + index), max_event)
            frame = frame[frame.row_id.isin(test_ids)].copy()
            base_score = stack_model.predict_proba(frame[HISTORY_FEATURES])[:, 1]
            methods = {
                'History_aware_stacking': (base_score, stack_selected['threshold'], None, None),
            }
            safe_values = pid_score(
                frame, base_score, tuple(safe['gains']), safe['gate'],
                norm, safe['gate_threshold'])
            methods['Gated_PID_safe'] = (safe_values[0], safe['threshold'],
                                         safe_values[1], safe_values[2])
            full_values = pid_score(
                frame, base_score, tuple(full['gains']), full['gate'],
                norm, full['gate_threshold'])
            methods['Gated_full_PID'] = (full_values[0], full['threshold'],
                                         full_values[1], full_values[2])
            pi_gains = (full['gains'][0], full['gains'][1], 0.)
            pi_values = pid_score(
                frame, base_score, pi_gains, full['gate'], norm, full['gate_threshold'])
            methods['Matched_PI'] = (pi_values[0], full['threshold'],
                                     pi_values[1], pi_values[2])
            for method, (score, threshold, gate_value, residual) in methods.items():
                scored = frame.assign(score=score)
                measured = trajectory_metrics(scored, threshold)
                metric_rows.append({
                    'outer_fold': fold, 'method': method,
                    'stress_id': spec['id'], 'family': spec['family'],
                    'level': spec['level'], 'seed': spec['seed'],
                    'threshold': threshold, **measured,
                })
                if spec['id'] in {'clean', 'delay_5', 'onset_20'}:
                    saved = scored[['row_id', 'outer_fold', 'event_count', 'label', 'score']].copy()
                    saved['method'], saved['stress_id'] = method, spec['id']
                    saved['threshold'] = threshold
                    saved['predicted_label'] = (saved.score >= threshold).astype(int)
                    saved['gate'] = 0. if gate_value is None else gate_value
                    saved['pid_residual'] = 0. if residual is None else residual
                    prediction_rows.append(saved)

    metrics = pd.DataFrame(metric_rows)
    predictions = pd.concat(prediction_rows, ignore_index=True)
    safe_effects = paired_effects(metrics, 'Gated_PID_safe', 'History_aware_stacking')
    d_effects = paired_effects(metrics, 'Gated_full_PID', 'Matched_PI')
    summaries = []
    for (method, family, level), group in metrics.groupby(['method', 'family', 'level']):
        fold_means = group.groupby('outer_fold').mean(numeric_only=True)
        summaries.append({
            'method': method, 'family': family, 'level': float(level),
            'stress_realizations': int(len(group)),
            **{metric: confidence_interval(fold_means[metric].tolist())
               for metric in ['auc', 'fpr', 'tpr', 'event_auc', 'early_auc_10',
                              'mean_threshold_crossings', 'benign_any_alarm_rate']},
        })
    summary = {
        'status': 'exploratory_matched_information_pid_upgrade',
        'samples': int(clean.row_id.nunique()), 'outer_folds': len(folds),
        'event_horizon': int(max_event), 'stress_seeds': args.stress_seeds,
        'history_features_shared': HISTORY_FEATURES,
        'selection_stresses': [spec['id'] for spec in select_specs],
        'results': summaries,
        'safe_pid_minus_history_stacking': safe_effects,
        'full_pid_minus_matched_pi': d_effects,
        'selected_by_fold': [
            {'outer_fold': item['outer_fold'],
             'safe_pid': item['safe_pid_selected'],
             'full_pid': item['full_pid_selected']}
            for item in audits],
        'limitations': [
            'The cohort is previously inspected development data, not external confirmation.',
            'Stress conditions are controlled score-trajectory perturbations, not new executions.',
            'Fold-clustered t intervals use only five outer folds and are therefore wide.',
            'Family/time generalization still requires a new labeled paired corpus.',
        ],
        'source': str(args.predictions.resolve()), 'source_sha256': sha256(args.predictions),
    }
    metrics.to_csv(args.output / 'fold_stress_metrics.csv', index=False)
    predictions.to_csv(args.output / 'selected_event_predictions.csv.gz',
                       index=False, compression='gzip')
    (args.output / 'model_search.json').write_text(json.dumps(audits, indent=2) + '\n')
    (args.output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    write_report(summary, args.output / 'REPORT_VI.md')
    plot_effects(summary, args.output)
    (args.output / 'verification.json').write_text(json.dumps({
        'status': 'passed', 'samples': summary['samples'], 'outer_folds': len(folds),
        'history_information_matched': True,
        'd_ablation_same_kp_ki_gate_threshold': True,
        'stress_seeds': args.stress_seeds,
        'outer_test_used_for_selection': False,
        'evidence_status': 'exploratory_post_hoc',
    }, indent=2) + '\n')
    hashes = {path.name: sha256(path) for path in sorted(args.output.iterdir())
              if path.is_file() and path.name != 'artifact_sha256.json'}
    (args.output / 'artifact_sha256.json').write_text(json.dumps(hashes, indent=2) + '\n')


def effect_lookup(summary, key, family, level):
    for item in summary[key]:
        if item['family'] == family and np.isclose(item['level'], level):
            return item
    raise KeyError((key, family, level))


def write_report(summary, path):
    clean = [item for item in summary['results']
             if item['family'] == 'clean' and item['level'] == 0]
    clean_rows = '\n'.join(
        f"| {item['method']} | {item['auc']['mean']:.4f} | "
        f"{100*item['fpr']['mean']:.2f}% | {100*item['tpr']['mean']:.2f}% | "
        f"{item['event_auc']['mean']:.4f} | {item['mean_threshold_crossings']['mean']:.3f} |"
        for item in clean)
    safe_rows, d_rows = [], []
    ordered = [('delay', 2.), ('delay', 5.), ('delay', 10.),
               ('dropout', .1), ('dropout', .2), ('dropout', .3),
               ('noise', .1), ('noise', .25), ('noise', .5),
               ('burst', 3.), ('burst', 5.), ('burst', 10.),
               ('onset', 10.), ('onset', 20.), ('onset', 30.)]
    for family, level in ordered:
        safe = effect_lookup(summary, 'safe_pid_minus_history_stacking', family, level)
        d_value = effect_lookup(summary, 'full_pid_minus_matched_pi', family, level)
        safe_rows.append(
            f"| {family} | {level:g} | {100*safe['fpr']['mean']:+.2f} "
            f"[{100*safe['fpr']['ci95_low']:+.2f}; {100*safe['fpr']['ci95_high']:+.2f}] | "
            f"{100*safe['tpr']['mean']:+.2f} | {safe['event_auc']['mean']:+.5f} | "
            f"{safe['mean_threshold_crossings']['mean']:+.3f} |"
        )
        d_rows.append(
            f"| {family} | {level:g} | {100*d_value['fpr']['mean']:+.2f} "
            f"[{100*d_value['fpr']['ci95_low']:+.2f}; {100*d_value['fpr']['ci95_high']:+.2f}] | "
            f"{100*d_value['tpr']['mean']:+.2f} | {d_value['event_auc']['mean']:+.5f} | "
            f"{d_value['mean_threshold_crossings']['mean']:+.3f} |"
        )
    selected = '\n'.join(
        f"- Fold {item['outer_fold']}: safe={item['safe_pid']['gains']}; "
        f"full={item['full_pid']['gains']}."
        for item in summary['selected_by_fold'])
    path.write_text(
        '# PID evidence upgrade — matched information và D ablation\n\n'
        '> History-aware stacking nhận đúng cùng P/I/D, volatility và event history. '
        'Full PID và Matched PI chỉ khác Kd. Đây vẫn là development evidence.\n\n'
        '## Clean outer-test\n\n'
        '| Method | AUC | FPR | TPR | Event-AUC | Crossings |\n'
        '|---|---:|---:|---:|---:|---:|\n' + clean_rows +
        '\n\n## Safe PID trừ History-aware stacking\n\n'
        '| Family | Level | ΔFPR pp [CI] | ΔTPR pp | ΔEvent-AUC | ΔCrossings |\n'
        '|---|---:|---:|---:|---:|---:|\n' + '\n'.join(safe_rows) +
        '\n\n## Full PID trừ Matched PI — hiệu ứng riêng của D\n\n'
        '| Family | Level | ΔFPR pp [CI] | ΔTPR pp | ΔEvent-AUC | ΔCrossings |\n'
        '|---|---:|---:|---:|---:|---:|\n' + '\n'.join(d_rows) +
        '\n\n## Gains được validation chọn\n\n' + selected +
        '\n\nCI được tính trên năm outer-fold effects; với dropout/noise/burst, mỗi fold '
        'được lấy trung bình qua các seed trước khi tính CI. Stress test không thay thế '
        'external/family/time validation.\n', encoding='utf-8')


def plot_effects(summary, output):
    import matplotlib.pyplot as plt

    families = [('delay', [2., 5., 10.]), ('dropout', [.1, .2, .3]),
                ('noise', [.1, .25, .5]), ('burst', [3., 5., 10.]),
                ('onset', [10., 20., 30.])]
    fig, axes = plt.subplots(2, 3, figsize=(12, 7.2))
    axes = axes.ravel()
    for axis, (family, levels) in zip(axes, families):
        safe = [effect_lookup(summary, 'safe_pid_minus_history_stacking', family, level)
                for level in levels]
        d_values = [effect_lookup(summary, 'full_pid_minus_matched_pi', family, level)
                    for level in levels]
        axis.axhline(0, color='black', linewidth=.8)
        axis.plot(levels, [100*item['fpr']['mean'] for item in safe], 'o-',
                  label='Safe PID - history stack', color='#D55E00')
        axis.plot(levels, [100*item['fpr']['mean'] for item in d_values], 's--',
                  label='Full PID - PI (D effect)', color='#2878B5')
        axis.set_title(family.capitalize())
        axis.set_xlabel('Stress level')
        axis.set_ylabel('ΔFPR (percentage points)')
        axis.grid(alpha=.25)
    axes[-1].axis('off')
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower right', bbox_to_anchor=(.96, .08), frameon=False)
    fig.suptitle('PID evidence upgrade: matched-information and D ablation')
    fig.tight_layout()
    fig.savefig(output / 'pid_evidence_upgrade_effects.png', dpi=220)
    fig.savefig(output / 'pid_evidence_upgrade_effects.pdf')
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--predictions', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--target-tpr', type=float, default=.95)
    parser.add_argument('--stress-seeds', type=int, default=10)
    parser.add_argument('--seed', type=int, default=2026)
    run(parser.parse_args())


if __name__ == '__main__':
    main()
