"""Exploratory reliability-aware PID fusion for ordered API reports.

This runner is deliberately separate from the locked confirmatory event-PID
benchmark.  It was designed after inspecting that benchmark and therefore
must be described as post-hoc method development until it is evaluated on a
new external or temporal cohort.
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .common import (choose_threshold, evaluate, low_fpr_metrics, require,
                     sha256, source_metadata, stats, write_json)
from .malbehavd_pid import (_bootstrap_difference, _counts, _load_sequences,
                            _platt_fit, _platt_predict, _write_gzip_csv)


METHODS = [
    'Static_only', 'Dynamic_only', 'Average_50_50', 'Max_score',
    'Fixed_weight', 'Logistic_stack', 'Reliability_target',
    'Reliability_P', 'Reliability_PI', 'Reliability_PID',
    'Reliability_full_PID',
]


class CorrectnessModel:
    """Small probability model with a deterministic one-class fallback."""

    def __init__(self, seed=2026):
        self.seed = int(seed)
        self.model = None
        self.constant = None

    def fit(self, features, correct):
        features = np.asarray(features, dtype=float)
        correct = np.asarray(correct, dtype=int)
        require(features.ndim == 2 and len(features) == len(correct),
                'Invalid reliability training data.')
        classes = np.unique(correct)
        if len(classes) == 1:
            self.constant = float(classes[0])
        else:
            self.model = LogisticRegression(max_iter=2000, random_state=self.seed)
            self.model.fit(features, correct)
        return self

    def predict(self, features):
        features = np.asarray(features, dtype=float)
        if self.model is None:
            return np.full(len(features), self.constant, dtype=float)
        return self.model.predict_proba(features)[:, 1]

    def audit(self):
        if self.model is None:
            return {'kind': 'constant', 'probability_correct': self.constant}
        return {
            'kind': 'logistic_correctness',
            'intercept': self.model.intercept_.tolist(),
            'coefficients': self.model.coef_.tolist(),
        }


def _logit(value):
    value = np.clip(np.asarray(value, dtype=float), 1e-6, 1 - 1e-6)
    return np.log(value / (1 - value))


def _sigmoid(value):
    value = np.asarray(value, dtype=float)
    positive = value >= 0
    out = np.empty_like(value, dtype=float)
    out[positive] = 1.0 / (1.0 + np.exp(-value[positive]))
    exp_value = np.exp(value[~positive])
    out[~positive] = exp_value / (1.0 + exp_value)
    return out


def reliability_features(frame, max_window):
    """Return static/dynamic correctness features without using test labels."""
    ordered = frame.sort_values(['row_id', 'event_count', 'time_step']).copy()
    ordered['dynamic_delta'] = ordered.groupby('row_id', sort=False).p_dynamic.diff().fillna(0.)
    static = np.column_stack([
        ordered.probability.to_numpy(),
        2. * np.abs(ordered.probability.to_numpy() - .5),
    ])
    dynamic = np.column_stack([
        ordered.p_dynamic.to_numpy(),
        2. * np.abs(ordered.p_dynamic.to_numpy() - .5),
        ordered.event_count.to_numpy() / float(max_window),
        np.abs(ordered.probability.to_numpy() - ordered.p_dynamic.to_numpy()),
        ordered.dynamic_delta.to_numpy(),
    ])
    return ordered, static, dynamic


def fit_reliability_models(calibration_frame, max_window, seed):
    ordered, static_x, dynamic_x = reliability_features(calibration_frame, max_window)
    static_rows = ~ordered.row_id.duplicated()
    static_correct = ((ordered.loc[static_rows, 'probability'].to_numpy() >= .5) ==
                      ordered.loc[static_rows, 'label'].to_numpy()).astype(int)
    dynamic_correct = ((ordered.p_dynamic.to_numpy() >= .5) ==
                       ordered.label.to_numpy()).astype(int)
    static_model = CorrectnessModel(seed).fit(static_x[static_rows], static_correct)
    dynamic_model = CorrectnessModel(seed + 1).fit(dynamic_x, dynamic_correct)
    return static_model, dynamic_model


def add_reliability(frame, static_model, dynamic_model, max_window):
    ordered, static_x, dynamic_x = reliability_features(frame, max_window)
    ordered['r_static'] = static_model.predict(static_x)
    ordered['r_dynamic'] = dynamic_model.predict(dynamic_x)
    require(ordered[['r_static', 'r_dynamic']].notna().all().all(),
            'Reliability model produced missing values.')
    return ordered


def reliability_pid_trajectory(frame, setting, integral_limits=(-5., 5.),
                               weight_limits=(.05, .95)):
    """Track a reliability-derived weight target with an incremental PID.

    The score at each event uses the weight after observing reliability at that
    event.  Controller state is reset for every independent execution.
    """
    required = {'row_id', 'execution_id', 'event_count', 'time_step',
                'probability', 'p_dynamic', 'r_static', 'r_dynamic'}
    require(required <= set(frame), 'Reliability PID frame is incomplete.')
    keys = {'w0', 'beta', 'kp', 'ki', 'kd', 'alpha'}
    require(keys == set(setting), f'Reliability PID setting must contain {sorted(keys)}.')
    w0, beta = float(setting['w0']), float(setting['beta'])
    kp, ki, kd = float(setting['kp']), float(setting['ki']), float(setting['kd'])
    alpha = float(setting['alpha'])
    require(0 < w0 < 1 and beta >= 0 and kp >= 0 and ki >= 0 and kd >= 0,
            'Invalid nonnegative reliability PID gains.')
    require(0 <= alpha < 1, 'Derivative smoothing alpha must be in [0,1).')

    result = frame.sort_values(['row_id', 'event_count', 'time_step']).copy()
    columns = ['score', 'w_static', 'w_target', 'pid_error', 'pid_integral',
               'pid_derivative', 'pid_control']
    values = {name: np.full(len(result), np.nan) for name in columns}
    positions = {index: position for position, index in enumerate(result.index)}
    base_logit = float(_logit(w0))
    for _, sequence in result.groupby(['row_id', 'execution_id'], sort=False):
        weight, integral = w0, 0.
        previous_error, filtered_derivative, previous_event = None, 0., 0.
        for row in sequence.sort_values(['event_count', 'time_step']).itertuples():
            delta = float(row.event_count) - previous_event
            require(delta > 0, 'Event count must increase inside an execution.')
            target = float(_sigmoid(base_logit + beta * (row.r_static - row.r_dynamic)))
            error = target - weight
            integral = float(np.clip(integral + error * delta, *integral_limits))
            raw_derivative = 0. if previous_error is None else (error - previous_error) / delta
            filtered_derivative = alpha * filtered_derivative + (1. - alpha) * raw_derivative
            control = kp * error + ki * integral + kd * filtered_derivative
            weight = float(np.clip(weight + control, *weight_limits))
            position = positions[row.Index]
            values['w_target'][position] = target
            values['w_static'][position] = weight
            values['pid_error'][position] = error
            values['pid_integral'][position] = integral
            values['pid_derivative'][position] = filtered_derivative
            values['pid_control'][position] = control
            values['score'][position] = weight * row.probability + (1. - weight) * row.p_dynamic
            previous_error, previous_event = error, float(row.event_count)
    for name in columns:
        result[name] = values[name]
    require(result[columns].notna().all().all(), 'Reliability PID trajectory contains missing values.')
    return result


def _algebraic_trajectory(frame, kind, setting=None):
    result = frame.sort_values(['row_id', 'event_count', 'time_step']).copy()
    if kind == 'Static_only':
        result['w_static'], result['score'] = 1., result.probability
    elif kind == 'Dynamic_only':
        result['w_static'], result['score'] = 0., result.p_dynamic
    elif kind == 'Average_50_50':
        result['w_static'] = .5
        result['score'] = .5 * (result.probability + result.p_dynamic)
    elif kind == 'Max_score':
        result['w_static'] = (result.probability >= result.p_dynamic).astype(float)
        result['score'] = np.maximum(result.probability, result.p_dynamic)
    elif kind == 'Fixed_weight':
        result['w_static'] = float(setting)
        result['score'] = result.w_static * result.probability + (1 - result.w_static) * result.p_dynamic
    elif kind == 'Reliability_target':
        beta = float(setting['beta']); w0 = float(setting['w0'])
        result['w_target'] = _sigmoid(float(_logit(w0)) + beta * (result.r_static - result.r_dynamic))
        result['w_static'] = result.w_target
        result['score'] = result.w_static * result.probability + (1 - result.w_static) * result.p_dynamic
    else:
        raise ValueError(f'Unsupported algebraic method: {kind}')
    for column in ['w_target', 'pid_error', 'pid_integral', 'pid_derivative', 'pid_control']:
        if column not in result:
            result[column] = np.nan
    return result


def _stack_features(frame, max_window):
    ordered, _, _ = reliability_features(frame, max_window)
    return ordered, np.column_stack([
        _logit(ordered.probability.to_numpy()),
        _logit(ordered.p_dynamic.to_numpy()),
        ordered.event_count.to_numpy() / float(max_window),
        np.abs(ordered.probability.to_numpy() - ordered.p_dynamic.to_numpy()),
        ordered.dynamic_delta.to_numpy(),
    ])


def _stack_trajectory(frame, model, max_window):
    result, features = _stack_features(frame, max_window)
    result['score'] = model.predict_proba(features)[:, 1]
    result['w_static'] = np.nan
    for column in ['w_target', 'pid_error', 'pid_integral', 'pid_derivative', 'pid_control']:
        result[column] = np.nan
    return result


def _final_rows(frame):
    return (frame.sort_values(['row_id', 'event_count', 'time_step'])
            .groupby('row_id', sort=False).tail(1))


def _trajectory_metrics(frame, threshold):
    event_auc = float(np.mean([
        roc_auc_score(group.label, group.score)
        for _, group in frame.groupby('event_count', sort=True)
    ]))
    final = _final_rows(frame)
    measured = evaluate(final.label, final.score, threshold)
    malware = frame[frame.label == 1].copy()
    benign = frame[frame.label == 0].copy()
    detected = malware[malware.score >= threshold].groupby('row_id').event_count.min()
    all_malware = malware.row_id.drop_duplicates()
    max_event = int(frame.event_count.max())
    first = pd.Series(max_event + 1., index=all_malware.to_numpy())
    first.loc[detected.index] = detected.to_numpy()
    benign_any = (benign.assign(alarm=benign.score >= threshold)
                  .groupby('row_id').alarm.max())
    ordered = frame.sort_values(['row_id', 'event_count'])
    decision = (ordered.score >= threshold).astype(int)
    crossings = decision.groupby(ordered.row_id).apply(lambda values: int(np.abs(np.diff(values)).sum()))
    return {
        **measured,
        'brier': float(brier_score_loss(final.label, final.score)),
        'event_auc': event_auc,
        'median_detection_event': float(np.median(first)),
        'detected_by_5': float(np.mean(first <= 5)),
        'detected_by_10': float(np.mean(first <= 10)),
        'detected_by_15': float(np.mean(first <= 15)),
        'detected_by_final': float(np.mean(first <= max_event)),
        'benign_any_alarm_rate': float(benign_any.mean()),
        'mean_threshold_crossings': float(crossings.mean()),
    }


def _candidate_record(frame, setting, target_tpr):
    final = _final_rows(frame)
    threshold = choose_threshold(final.label, final.score, target_tpr)
    metrics = _trajectory_metrics(frame, threshold)
    return {'setting': setting, 'threshold': threshold, **metrics}


def _selection_key(record):
    """Operational objective declared before exploratory test evaluation."""
    return (-record['fpr'], record['event_auc'], record['auc'], -record['brier'])


def _select(validation, candidates, builder, target_tpr):
    trials = []
    for order, setting in enumerate(candidates):
        record = _candidate_record(builder(validation, setting), setting, target_tpr)
        record['grid_order'] = order
        trials.append(record)
    winner = max(range(len(trials)), key=lambda index: (*_selection_key(trials[index]), -index))
    return trials[winner]['setting'], trials


def _reliability_grids(w0):
    # Fixed fusion can select the endpoints 0/1. The controller uses a logit
    # state and the declared [.05, .95] weight limits, so project an endpoint
    # into that same feasible interval before building PID candidates.
    w0 = float(np.clip(w0, .05, .95))
    betas = [2., 4., 8.]
    kp = [.25, .5, 1.]
    ki = [.005, .02]
    kd = [.1, .25]
    alpha = [.5, .8]

    def setting(beta, p, i=0., d=0., smooth=.5):
        return {'w0': float(w0), 'beta': beta, 'kp': p, 'ki': i, 'kd': d, 'alpha': smooth}

    p_grid = [setting(beta, p) for beta, p in itertools.product(betas, kp)]
    pi_grid = p_grid + [setting(beta, p, i) for beta, p, i in itertools.product(betas, kp, ki)]
    full = [setting(beta, p, i, d, smooth)
            for beta, p, i, d, smooth in itertools.product(betas, kp, ki, kd, alpha)]
    pid_grid = pi_grid + full
    return {
        'Reliability_target': [{'w0': float(w0), 'beta': beta} for beta in betas],
        'Reliability_P': p_grid,
        'Reliability_PI': pi_grid,
        'Reliability_PID': pid_grid,
        'Reliability_full_PID': full,
    }


def _score_prefixes(frame, p_static, vectorizer, dynamic_model, calibrators, windows):
    texts, owners, counts = [], [], []
    identities, hashes, labels = [], [], []
    for position, item in enumerate(frame.itertuples(index=False)):
        for count in windows:
            texts.append(' '.join(item.api_sequence[:count]))
            owners.append(position); counts.append(count)
            identities.append(int(item.row_id)); hashes.append(item.sha256); labels.append(int(item.label))
    raw = dynamic_model.decision_function(vectorizer.transform(texts))
    dynamic = np.empty(len(raw), dtype=float)
    counts_array = np.asarray(counts)
    for count in windows:
        selected = counts_array == count
        dynamic[selected] = _platt_predict(calibrators[int(count)], raw[selected])
    return pd.DataFrame({
        'row_id': identities, 'sha256': hashes,
        'execution_id': [f'public_report_{value}' for value in hashes],
        'time_step': np.tile(np.arange(len(windows)), len(frame)),
        'event_count': counts_array.astype(float), 'label': labels,
        'probability': np.asarray(p_static)[np.asarray(owners)],
        'p_dynamic': dynamic,
    })


def _fit_dynamic(model_train, calibration, windows, seed):
    train_text, train_label = [], []
    for item in model_train.itertuples(index=False):
        for count in windows:
            train_text.append(' '.join(item.api_sequence[:count])); train_label.append(int(item.label))
    vectorizer = TfidfVectorizer(token_pattern=r'[^ ]+', lowercase=False, ngram_range=(1, 2),
                                 min_df=2, max_features=10000, sublinear_tf=True)
    train_x = vectorizer.fit_transform(train_text)
    model = LogisticRegression(max_iter=2000, class_weight='balanced', random_state=seed)
    model.fit(train_x, train_label)
    calibrators = {}
    for count in windows:
        texts = [' '.join(item.api_sequence[:count]) for item in calibration.itertuples(index=False)]
        raw = model.decision_function(vectorizer.transform(texts))
        calibrators[int(count)] = _platt_fit(raw, calibration.label)
    return vectorizer, model, calibrators


def _load_joined(sequences, static_features, selection, min_coverage, windows):
    sequence_frame = _load_sequences(Path(sequences))
    selection_metadata = None
    if selection is not None:
        selection = Path(selection).resolve()
        selected = pd.read_csv(selection, dtype={'sha256': str})
        require({'row_id', 'sha256', 'label'} <= set(selected), 'Selection manifest is incomplete.')
        sequence_frame = sequence_frame.merge(
            selected[['row_id', 'sha256', 'label']], on=['row_id', 'sha256', 'label'],
            how='inner', validate='one_to_one')
        require(len(sequence_frame) == len(selected), 'Selection includes identities without API sequences.')
        selection_metadata = {'path': str(selection), 'sha256': sha256(selection), 'rows': len(selected)}
    static = pd.read_csv(static_features, dtype={'sha256': str})
    static_columns = [column for column in static if column.startswith('s_')]
    require(static_columns, 'No allow-listed static features found.')
    joined = sequence_frame.merge(static, on=['row_id', 'sha256', 'label'],
                                  how='inner', validate='one_to_one')
    coverage = len(joined) / len(sequence_frame)
    require(coverage >= min_coverage, f'Static coverage {coverage:.3f} is below {min_coverage:.3f}.')
    require((joined.api_sequence.map(len) >= max(windows)).all(), 'A sequence is shorter than max window.')
    return joined, static_columns, coverage, selection_metadata


def _diagnostics(predictions):
    static = predictions[predictions.method == 'Static_only'][
        ['row_id', 'event_count', 'label', 'score']].rename(columns={'score': 'p_static'})
    dynamic = predictions[predictions.method == 'Dynamic_only'][
        ['row_id', 'event_count', 'score']].rename(columns={'score': 'p_dynamic'})
    paired = static.merge(dynamic, on=['row_id', 'event_count'])
    paired['static_error'] = (paired.label - paired.p_static) ** 2
    paired['dynamic_error'] = (paired.label - paired.p_dynamic) ** 2
    paired['better'] = np.where(paired.static_error < paired.dynamic_error, 'static', 'dynamic')
    by_event = []
    for event, group in paired.groupby('event_count'):
        by_event.append({
            'event_count': int(event),
            'static_better_fraction': float((group.better == 'static').mean()),
            'dynamic_better_fraction': float((group.better == 'dynamic').mean()),
            'static_brier': float(group.static_error.mean()),
            'dynamic_brier': float(group.dynamic_error.mean()),
        })
    pivot = paired.pivot(index='row_id', columns='event_count', values='better')
    return {
        'samples': int(paired.row_id.nunique()),
        'samples_where_better_channel_changes': int((pivot.nunique(axis=1) > 1).sum()),
        'fraction_where_better_channel_changes': float((pivot.nunique(axis=1) > 1).mean()),
        'by_event': by_event,
    }


def _format_setting(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def run(sequences, static_features, out, selection=None, windows=tuple(range(1, 21)),
        target_tpr=.95, min_coverage=.9, validation_fraction=.2,
        calibration_fraction=.2, bootstrap=1000, seed=2026):
    """Run post-hoc reliability-aware PID development with frozen outer folds."""
    out = Path(out)
    sequences = Path(sequences).resolve()
    static_features = Path(static_features).resolve()
    windows = tuple(int(value) for value in windows)
    require(list(windows) == sorted(set(windows)) and min(windows) > 0 and len(windows) >= 4,
            'Windows must be unique, increasing, positive and contain at least four points.')
    require(windows == tuple(range(min(windows), max(windows) + 1)),
            'This exploratory runner requires a dense contiguous event grid.')
    out.mkdir(parents=True, exist_ok=False)
    joined, static_columns, coverage, selection_metadata = _load_joined(
        sequences, static_features, selection, min_coverage, windows)
    folds = sorted(joined.outer_fold.unique())
    metric_rows, prediction_rows, search_rows, partition_rows, reliability_audits = [], [], [], [], []

    for fold in folds:
        development = joined[joined.outer_fold != fold].copy()
        test = joined[joined.outer_fold == fold].copy()
        train_cal, validation = train_test_split(
            development, test_size=validation_fraction, random_state=seed + int(fold),
            stratify=development.label)
        model_train, calibration = train_test_split(
            train_cal, test_size=calibration_fraction, random_state=seed + 100 + int(fold),
            stratify=train_cal.label)
        for role, subset in [('model_train', model_train), ('calibration', calibration),
                             ('validation', validation), ('outer_test', test)]:
            require(set(subset.label) == {0, 1}, f'Fold {fold}/{role} is single-class.')
            partition_rows.extend({'outer_fold': int(fold), 'row_id': int(row.row_id),
                                   'sha256': row.sha256, 'label': int(row.label), 'role': role}
                                  for row in subset.itertuples())

        static_model = make_pipeline(
            SimpleImputer(strategy='median'), StandardScaler(),
            LogisticRegression(max_iter=2000, class_weight='balanced', random_state=seed + int(fold)))
        static_model.fit(model_train[static_columns], model_train.label)
        static_calibrator = _platt_fit(
            static_model.decision_function(calibration[static_columns]), calibration.label)

        def static_scores(frame):
            return _platt_predict(static_calibrator, static_model.decision_function(frame[static_columns]))

        vectorizer, dynamic_model, dynamic_calibrators = _fit_dynamic(
            model_train, calibration, windows, seed + int(fold))
        frames = {
            'calibration': _score_prefixes(calibration, static_scores(calibration), vectorizer,
                                           dynamic_model, dynamic_calibrators, windows),
            'validation': _score_prefixes(validation, static_scores(validation), vectorizer,
                                          dynamic_model, dynamic_calibrators, windows),
            'test': _score_prefixes(test, static_scores(test), vectorizer,
                                    dynamic_model, dynamic_calibrators, windows),
        }
        static_reliability, dynamic_reliability = fit_reliability_models(
            frames['calibration'], max(windows), seed + 1000 + int(fold))
        for name in frames:
            frames[name] = add_reliability(
                frames[name], static_reliability, dynamic_reliability, max(windows))
        reliability_audits.append({
            'outer_fold': int(fold), 'static': static_reliability.audit(),
            'dynamic': dynamic_reliability.audit(),
        })

        stack_calibration, stack_x = _stack_features(frames['calibration'], max(windows))
        stack_model = LogisticRegression(max_iter=2000, random_state=seed + 2000 + int(fold))
        stack_model.fit(stack_x, stack_calibration.label)

        fixed_setting, fixed_trials = _select(
            frames['validation'], [float(value) for value in np.linspace(0, 1, 11)],
            lambda frame, value: _algebraic_trajectory(frame, 'Fixed_weight', value), target_tpr)
        settings = {'Fixed_weight': fixed_setting}
        search_rows.append({'outer_fold': int(fold), 'method': 'Fixed_weight',
                            'selected': fixed_setting, 'trials': fixed_trials})
        grids = _reliability_grids(fixed_setting)
        for method, candidates in grids.items():
            if method == 'Reliability_target':
                builder = lambda frame, value: _algebraic_trajectory(frame, method, value)
            else:
                builder = reliability_pid_trajectory
            selected_setting, trials = _select(
                frames['validation'], candidates, builder, target_tpr)
            settings[method] = selected_setting
            search_rows.append({'outer_fold': int(fold), 'method': method,
                                'selected': selected_setting, 'trials': trials})

        for method in METHODS:
            if method in {'Static_only', 'Dynamic_only', 'Average_50_50', 'Max_score'}:
                validation_trajectory = _algebraic_trajectory(frames['validation'], method)
                test_trajectory = _algebraic_trajectory(frames['test'], method)
                selected_setting = None
            elif method == 'Fixed_weight':
                validation_trajectory = _algebraic_trajectory(
                    frames['validation'], method, settings[method])
                test_trajectory = _algebraic_trajectory(frames['test'], method, settings[method])
                selected_setting = settings[method]
            elif method == 'Logistic_stack':
                validation_trajectory = _stack_trajectory(
                    frames['validation'], stack_model, max(windows))
                test_trajectory = _stack_trajectory(frames['test'], stack_model, max(windows))
                selected_setting = {'features': ['logit_static', 'logit_dynamic', 'event_fraction',
                                                 'absolute_disagreement', 'dynamic_delta']}
            elif method == 'Reliability_target':
                validation_trajectory = _algebraic_trajectory(
                    frames['validation'], method, settings[method])
                test_trajectory = _algebraic_trajectory(frames['test'], method, settings[method])
                selected_setting = settings[method]
            else:
                validation_trajectory = reliability_pid_trajectory(
                    frames['validation'], settings[method])
                test_trajectory = reliability_pid_trajectory(frames['test'], settings[method])
                selected_setting = settings[method]

            final_validation = _final_rows(validation_trajectory)
            threshold = choose_threshold(final_validation.label, final_validation.score, target_tpr)
            measured = _trajectory_metrics(test_trajectory, threshold)
            final_test = _final_rows(test_trajectory)
            extra = low_fpr_metrics(final_validation.label, final_validation.score,
                                    final_test.label, final_test.score)
            metric_rows.append({
                'outer_fold': int(fold), 'method': method,
                'selected_setting': _format_setting(selected_setting),
                'threshold': threshold, **measured, **extra,
            })
            saved = test_trajectory.copy()
            saved['outer_fold'] = int(fold); saved['method'] = method; saved['threshold'] = threshold
            saved['predicted_label'] = (saved.score >= threshold).astype(int)
            prediction_rows.append(saved)

    metrics = pd.DataFrame(metric_rows)
    predictions = pd.concat(prediction_rows, ignore_index=True)
    final = (predictions.sort_values(['row_id', 'event_count'])
             .groupby(['outer_fold', 'method', 'row_id'], sort=False).tail(1))
    replayed = 0
    for row in metrics.itertuples(index=False):
        selected = final[(final.outer_fold == row.outer_fold) & (final.method == row.method)]
        check = evaluate(selected.label, selected.score, row.threshold)
        for metric in ['auc', 'ap', 'fpr', 'tpr', 'tn', 'fp', 'fn', 'tp']:
            require(np.isclose(check[metric], getattr(row, metric)),
                    f'Replay mismatch fold={row.outer_fold}, method={row.method}, metric={metric}.')
        replayed += len(selected)

    summaries = []
    summary_metrics = ['auc', 'ap', 'fpr', 'tpr', 'brier', 'event_auc',
                       'median_detection_event', 'benign_any_alarm_rate',
                       'mean_threshold_crossings']
    for method, group in metrics.groupby('method'):
        summaries.append({'method': method, **{name: stats(group[name]) for name in summary_metrics}})
    comparisons = {}
    for left, right in [
            ('Reliability_PID', 'Average_50_50'),
            ('Reliability_PID', 'Fixed_weight'),
            ('Reliability_PID', 'Logistic_stack'),
            ('Reliability_P', 'Average_50_50'),
            ('Reliability_P', 'Fixed_weight'),
            ('Reliability_PID', 'Reliability_P'),
            ('Reliability_full_PID', 'Reliability_PI')]:
        comparisons[f'{left}_minus_{right}'] = _bootstrap_difference(
            final.rename(columns={'method': 'fusion'}), left, right, bootstrap, seed)

    # Timepoint pooled ranking/calibration metrics.
    timepoint_rows = []
    for (method, event), group in predictions.groupby(['method', 'event_count']):
        timepoint_rows.append({
            'method': method, 'event_count': int(event), 'samples': int(len(group)),
            'auc': float(roc_auc_score(group.label, group.score)),
            'ap': float(average_precision_score(group.label, group.score)),
            'brier': float(brier_score_loss(group.label, group.score)),
        })

    metrics.to_csv(out / 'fold_metrics.csv', index=False)
    pd.DataFrame(partition_rows).to_csv(out / 'partition_manifest.csv', index=False)
    pd.DataFrame(timepoint_rows).to_csv(out / 'timepoint_oof_metrics.csv', index=False)
    _write_gzip_csv(predictions, out / 'event_predictions.csv.gz')
    write_json(out / 'validation_search.json', search_rows)
    write_json(out / 'reliability_models.json', reliability_audits)
    write_json(out / 'paired_bootstrap.json', comparisons)
    diagnostics = _diagnostics(predictions)
    write_json(out / 'channel_reliability_diagnostics.json', diagnostics)
    summary = {
        'status': 'exploratory_post_hoc_reliability_pid_development',
        'samples': int(len(joined)), 'coverage': float(coverage),
        'class_counts': _counts(joined.label), 'outer_folds': int(len(folds)),
        'event_windows': list(windows), 'selection': selection_metadata,
        'inputs': {
            'sequences': {'path': str(sequences), 'sha256': sha256(sequences)},
            'static_features': {'path': str(static_features), 'sha256': sha256(static_features)},
        },
        'selection_objective': 'minimum validation FPR at threshold achieving target TPR; then event-AUC, final AUC and Brier',
        'target_validation_tpr': target_tpr,
        'results': summaries, 'paired_bootstrap': comparisons,
        'channel_diagnostics': diagnostics,
        'limitations': [
            'This method was designed after inspecting the earlier confirmatory cohort and is exploratory.',
            'A new external or temporal cohort is required before claiming confirmatory superiority.',
            'Labels are generic Windows malware/benign, not verified ransomware labels.',
            'The time axis is ordered API-event count, not measured seconds.',
            'Reliability models use calibration labels only; test labels never update controller state.',
        ],
        **source_metadata(),
    }
    write_json(out / 'summary.json', summary)
    write_json(out / 'verification.json', {
        'status': 'passed', 'metric_rows_replayed': int(len(metrics)),
        'prediction_rows_checked': int(replayed), 'test_labels_used_for_control': False,
        'no_executable_downloaded_or_executed': True,
    })
    (out / 'REPORT.md').write_text(_report(summary), encoding='utf-8')
    return summary


def _report(summary):
    windows = summary['event_windows']
    rows = []
    for result in summary['results']:
        rows.append(
            f"| {result['method']} | {result['auc']['mean']:.4f} | {result['fpr']['mean']*100:.2f}% | "
            f"{result['tpr']['mean']*100:.2f}% | {result['event_auc']['mean']:.4f} | "
            f"{result['brier']['mean']:.4f} |"
        )
    return (
        '# Exploratory reliability-aware PID\n\n'
        '> This algorithm was designed after inspecting the locked confirmatory run. '
        'The results below are exploratory and require a new external/temporal cohort for confirmation.\n\n'
        f"The controller tracks a validation-trained reliability target on dense "
        f"{min(windows)}--{max(windows)} API-event prefixes. "
        'All thresholds and gains are selected without outer-test labels.\n\n'
        '| Method | AUC | FPR | TPR | Event-AUC | Brier |\n'
        '|---|---:|---:|---:|---:|---:|\n' + '\n'.join(rows) + '\n\n'
        'See `paired_bootstrap.json` for paired uncertainty intervals and '
        '`channel_reliability_diagnostics.json` for whether the better channel changes over time.\n'
    )
