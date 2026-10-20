"""Time-aware static/dynamic fusion with validation-selected P, PI and PID."""
from __future__ import annotations

import itertools
import json
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

from ..pid_fusion import PIDController
from .common import (choose_threshold, evaluate, low_fpr_metrics, require,
                     sha256, source_metadata, stats, write_json)
from .fusion import al_final_predictions
from .temporal import validate as validate_temporal


def candidate_grids():
    """Predeclared compact grids; all choices are made on validation only."""
    kp = [.25, .5, 1., 2.]
    ki = [.005, .01, .02]
    kd = [.25, .5, 1.]
    return {
        'Fixed_weight': [float(x) for x in np.linspace(0, 1, 11)],
        'P': [(p, 0., 0.) for p in kp],
        'PI': [(p, i, 0.) for p, i in itertools.product(kp, ki)],
        'PID': list(itertools.product(kp, ki, kd)),
    }


def _observation_axis(frame):
    """Return the declared discrete axis without conflating events with seconds."""
    if 'event_count' in frame:
        return 'event_count'
    require('elapsed_seconds' in frame, 'Temporal fusion requires event_count or elapsed_seconds.')
    return 'elapsed_seconds'


def pid_trajectory(frame, gains, integral_limits=(-5., 5.)):
    """Replay one independent controller per execution using the observed delta."""
    require({'row_id', 'execution_id', 'probability', 'p_dynamic'} <= set(frame),
            'Temporal fusion frame is missing required columns.')
    axis = _observation_axis(frame)
    result = frame.copy()
    columns = ['score', 'w_static', 'pid_error', 'pid_integral', 'pid_derivative', 'pid_control']
    values = {name: np.full(len(result), np.nan) for name in columns}
    positions = {index: position for position, index in enumerate(result.index)}
    for _, sequence in result.groupby(['row_id', 'execution_id'], sort=False):
        controller = PIDController(*gains, integral_limits=integral_limits)
        previous_time = 0.
        for row in sequence.sort_values([axis, 'time_step']).itertuples():
            observed = float(getattr(row, axis))
            delta_t = observed - previous_time
            require(delta_t > 0, 'The observation axis must increase within every execution.')
            error = float(row.probability - row.p_dynamic)
            weight = controller.update(error, delta_t=delta_t)
            position = positions[row.Index]
            values['score'][position] = weight * row.probability + (1 - weight) * row.p_dynamic
            values['w_static'][position] = weight
            for name, value in controller.last_terms.items():
                values[f'pid_{name}'][position] = value
            previous_time = observed
    for name in columns:
        result[name] = values[name]
    require(result[['score', 'w_static', 'pid_error', 'pid_integral',
                    'pid_derivative', 'pid_control']].notna().all().all(),
            'PID trajectory contains missing values.')
    return result


def _algebraic_trajectory(frame, weight):
    result = frame.copy()
    result['w_static'] = float(weight)
    result['score'] = weight * result.probability + (1 - weight) * result.p_dynamic
    for name in ['pid_error', 'pid_integral', 'pid_derivative', 'pid_control']:
        result[name] = np.nan
    return result


def score_trajectory(frame, kind, setting, integral_limits=(-5., 5.)):
    if kind in {'Static_only', 'Dynamic_only', 'Average_50_50', 'Fixed_weight'}:
        weight = {'Static_only': 1., 'Dynamic_only': 0., 'Average_50_50': .5}.get(kind, setting)
        return _algebraic_trajectory(frame, float(weight))
    require(kind in {'P', 'PI', 'PID'}, f'Unknown temporal fusion method: {kind}')
    return pid_trajectory(frame, tuple(setting), integral_limits)


def _final_rows(trajectory):
    ordered = trajectory.sort_values(['row_id', _observation_axis(trajectory), 'time_step'])
    return ordered.groupby('row_id', sort=False).tail(1).sort_values('row_id')


def select_on_validation(validation, kind, target_tpr=.95, integral_limits=(-5., 5.)):
    trials = []
    for order, setting in enumerate(candidate_grids()[kind]):
        trajectory = score_trajectory(validation, kind, setting, integral_limits)
        final = _final_rows(trajectory)
        threshold = choose_threshold(final.label, final.score, target_tpr)
        measured = evaluate(final.label, final.score, threshold)
        trials.append({
            'setting': setting if isinstance(setting, float) else list(setting),
            'grid_order': order, 'threshold': threshold, **measured,
        })
    winner = max(range(len(trials)), key=lambda i: (trials[i]['auc'], -trials[i]['fpr'], -i))
    return trials[winner]['setting'], trials


def _load_temporal(path, provenance_path, predictions, al_config):
    validation = validate_temporal(path, provenance_path, al_config['dataset']['data_sha256'])
    frame = pd.read_csv(path, dtype={'execution_id': str, 'evidence_status': str,
                                    'report_path': str, 'report_sha256': str})
    require(set(frame.evidence_status) <= {'observed', 'no_behavior'},
            'Confirmatory PID requires a score for every planned observation; resolve missing/failure rows first.')
    expected = set(predictions.row_id.unique())
    require(set(frame.row_id.unique()) == expected,
            'Temporal data must cover every AL validation/test row exactly.')
    require(frame.groupby('row_id').execution_id.nunique().max() == 1,
            'Primary confirmatory run requires exactly one execution per row_id.')
    require(frame.groupby('row_id').size().min() >= 2,
            'At least two time points per sample are required for PI/PID history.')
    windows = frame.groupby('row_id').elapsed_seconds.apply(lambda x: tuple(sorted(x))).unique()
    require(len(windows) == 1, 'All samples must use the same observation windows.')
    provenance = json.loads(Path(provenance_path).read_text())
    declared = provenance.get('observation_windows_seconds')
    require(isinstance(declared, list) and len(declared) == len(windows[0]) and
            np.allclose(np.asarray(declared, dtype=float), np.asarray(windows[0], dtype=float)),
            'Observed windows differ from the predeclared provenance windows.')
    return frame, validation, list(windows[0])


def _verify_outputs(metrics, outputs, target_tpr):
    require(not outputs.duplicated(['seed', 'strategy', 'fusion', 'split',
                                    'row_id', 'execution_id', 'time_step']).any(),
            'Duplicate temporal fusion prediction key.')
    require(np.allclose(outputs.score,
                        outputs.w_static * outputs.probability +
                        (1 - outputs.w_static) * outputs.p_dynamic),
            'Saved fused scores do not match saved weights and inputs.')
    checked = 0
    for row in metrics.itertuples():
        selected = outputs[(outputs.seed == row.seed) &
                           (outputs.strategy == row.strategy) &
                           (outputs.fusion == row.fusion)]
        validation = _final_rows(selected[selected.split == 'validation'])
        test = _final_rows(selected[selected.split == 'test'])
        threshold = choose_threshold(validation.label, validation.score, target_tpr)
        require(np.isclose(threshold, row.threshold), 'Temporal threshold replay mismatch.')
        measured = evaluate(test.label, test.score, threshold)
        for name, value in measured.items():
            require(np.isclose(value, getattr(row, name)), f'Temporal metric replay mismatch: {name}')
        checked += len(selected)
    return {'status': 'passed', 'metric_rows_replayed': int(len(metrics)),
            'prediction_rows_checked': int(checked)}


def run(al_run, temporal_path, provenance_path, out, target_tpr=.95,
        integral_limits=(-5., 5.)):
    require(0 < target_tpr <= 1, 'Invalid target TPR.')
    require(len(integral_limits) == 2 and integral_limits[0] < integral_limits[1],
            'Invalid anti-windup integral limits.')
    predictions, al_config = al_final_predictions(al_run)
    temporal, temporal_validation, windows = _load_temporal(
        temporal_path, provenance_path, predictions, al_config)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    started = perf_counter()
    joined = predictions.merge(temporal, on='row_id', validate='many_to_many')
    require(not joined.duplicated(['seed', 'method', 'split', 'row_id',
                                   'execution_id', 'time_step']).any(),
            'Unexpected duplicate after static/dynamic temporal join.')
    provenance = json.loads(Path(provenance_path).read_text())
    config = {
        'kind': 'temporal_pid_fusion',
        'al_run': str(Path(al_run).resolve()),
        'al_predictions_sha256': sha256(Path(al_run) / 'predictions.csv.gz'),
        'temporal_data_sha256': sha256(temporal_path),
        'temporal_provenance_sha256': sha256(provenance_path),
        'temporal_validation': temporal_validation,
        'observation_windows_seconds': windows,
        'target_validation_tpr': target_tpr,
        'error_definition': 'e_k = p_static - p_dynamic,k',
        'interpretation': (
            'A positive discrepancy increases static weight and a negative discrepancy '
            'increases dynamic weight; this is a conservative score-disagreement heuristic, '
            'not a plant-stability theorem.'
        ),
        'integral': 'I_k = clip(I_(k-1) + e_k * delta_t_k, limits)',
        'derivative': 'D_k = (e_k - e_(k-1)) / delta_t_k; D_0 = 0',
        'integral_limits': list(integral_limits),
        'grids': candidate_grids(),
        'selection': 'Maximum final-window validation AUC, then lower FPR, then grid order.',
        'test_policy': 'Test is evaluated once after validation-only gain, weight and threshold selection.',
        'dynamic_provenance': provenance,
        **source_metadata(),
    }
    write_json(out / 'config.json', config)
    joined.to_csv(out / 'paired_temporal_inputs.csv.gz', index=False)

    metric_rows, prediction_rows, tuning_rows, trajectory_rows = [], [], [], []
    kinds = ['Static_only', 'Dynamic_only', 'Average_50_50',
             'Fixed_weight', 'P', 'PI', 'PID']
    for (seed, strategy), group in joined.groupby(['seed', 'method']):
        validation = group[group.split == 'validation'].copy()
        test = group[group.split == 'test'].copy()
        settings = {'Static_only': 1., 'Dynamic_only': 0., 'Average_50_50': .5}
        for kind in ['Fixed_weight', 'P', 'PI', 'PID']:
            setting, trials = select_on_validation(validation, kind, target_tpr, integral_limits)
            settings[kind] = setting
            tuning_rows.append({'seed': int(seed), 'strategy': strategy,
                                'fusion': kind, 'selected': setting, 'trials': trials})
        for kind in kinds:
            trajectories = {}
            for split, subset in [('validation', validation), ('test', test)]:
                trajectory = score_trajectory(subset, kind, settings[kind], integral_limits)
                trajectory['seed'] = int(seed)
                trajectory['strategy'] = strategy
                trajectory['fusion'] = kind
                trajectories[split] = trajectory
                prediction_rows.append(trajectory)
            final_validation = _final_rows(trajectories['validation'])
            final_test = _final_rows(trajectories['test'])
            threshold = choose_threshold(final_validation.label, final_validation.score, target_tpr)
            measured = evaluate(final_test.label, final_test.score, threshold)
            low_fpr = low_fpr_metrics(final_validation.label, final_validation.score,
                                      final_test.label, final_test.score)
            metric_rows.append({
                'seed': int(seed), 'strategy': strategy, 'fusion': kind,
                'selected_setting': json.dumps(settings[kind]),
                'threshold': threshold, **measured, **low_fpr,
            })
            for elapsed, at_time in trajectories['test'].groupby('elapsed_seconds'):
                trajectory_rows.append({
                    'seed': int(seed), 'strategy': strategy, 'fusion': kind,
                    'elapsed_seconds': float(elapsed),
                    'auc': float(roc_auc_score(at_time.label, at_time.score)),
                    'ap': float(average_precision_score(at_time.label, at_time.score)),
                })

    metrics = pd.DataFrame(metric_rows)
    outputs = pd.concat(prediction_rows, ignore_index=True)
    trajectory_metrics = pd.DataFrame(trajectory_rows)
    metrics.to_csv(out / 'fusion_metrics.csv', index=False)
    outputs.to_csv(out / 'temporal_predictions.csv.gz', index=False)
    trajectory_metrics.to_csv(out / 'timepoint_metrics.csv', index=False)
    write_json(out / 'validation_search.json', tuning_rows)
    write_json(out / 'verification.json', _verify_outputs(metrics, outputs, target_tpr))

    interaction = []
    for seed, group in metrics.groupby('seed'):
        for metric in ['auc', 'ap', 'fpr', 'tpr']:
            values = {(row.strategy, row.fusion): getattr(row, metric) for row in group.itertuples()}
            cells = [('Random', 'Fixed_weight'), ('Random', 'PID'),
                     ('XAI_full', 'Fixed_weight'), ('XAI_full', 'PID')]
            if all(cell in values for cell in cells):
                a, b, c, d = [values[cell] for cell in cells]
                interaction.append({
                    'seed': int(seed), 'metric': metric,
                    'fixed_random': a, 'pid_random': b,
                    'fixed_xai': c, 'pid_xai': d,
                    'difference_of_differences': (d - c) - (b - a),
                })
    pd.DataFrame(interaction).to_csv(out / 'factorial_2x2.csv', index=False)

    summary = {
        'status': 'measured_from_observed_temporal_reports',
        'samples': int(temporal.row_id.nunique()),
        'time_steps_per_sample': int(temporal.groupby('row_id').size().iloc[0]),
        'observation_windows_seconds': windows,
        'results': [
            {'strategy': strategy, 'fusion': kind,
             **{metric: stats(group[metric]) for metric in
                ['auc', 'ap', 'fpr', 'tpr', 'test_standardized_pauc_fpr_05',
                 'test_tpr_at_val_fpr_01', 'test_tpr_at_val_fpr_05']}}
            for (strategy, kind), group in metrics.groupby(['strategy', 'fusion'])
        ],
        'factorial_rows': len(interaction),
        'elapsed_seconds': perf_counter() - started,
        'limitations': [
            'PID is an adaptive score-fusion heuristic; bounded weights and anti-windup do not prove classifier optimality.',
            'Dynamic collection latency is external to this offline replay and must be reported separately.',
            'Gain grids have different cardinalities; all selection is isolated to validation but model-selection variance remains.',
            'The same observed dynamic reports are paired with each AL seed/method to isolate fusion effects.',
        ],
    }
    write_json(out / 'summary.json', summary)
    (out / 'REPORT.md').write_text(
        '# Temporal PID fusion\n\n'
        'So sánh Static, Dynamic, Average, Fixed, P, PI và PID bằng cùng báo cáo '
        'động nhiều mốc thời gian. Gain, fixed weight và threshold chỉ được chọn '
        'trên validation; test không tham gia lựa chọn. Xem fusion_metrics.csv, '
        'timepoint_metrics.csv và factorial_2x2.csv.\n',
        encoding='utf-8',
    )
    return summary
