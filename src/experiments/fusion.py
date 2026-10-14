"""Fusion ablation on AL predictions joined to supplied, traceable dynamic observations.

The runner does not execute PE files, manufacture dynamic scores or authenticate
the truth of a report. Provenance checks establish integrity and ID alignment.
"""
import itertools
import json
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd

from ..pid_fusion import PIDController
from .common import choose_threshold, evaluate, probabilities, require, sha256, source_metadata, stats, write_json

DYNAMIC_COLUMNS = ['row_id', 'p_dynamic', 'sequence_id', 'sequence_order', 'report_path', 'report_sha256']


def al_final_predictions(al_run):
    al_run = Path(al_run)
    config = json.loads((al_run / 'config.json').read_text())
    require(config.get('kind') == 'active_learning', 'Expected output of the measured AL runner.')
    frame = pd.read_csv(al_run / 'predictions.csv.gz', float_precision='round_trip')
    final = frame[frame['round'] == config['rounds']].copy()
    require(len(final) > 0 and not final.duplicated(['seed', 'method', 'split', 'row_id']).any(), 'Invalid AL prediction keys.')
    require(set(final.split) == {'validation', 'test'}, 'Validation and test predictions are required.')
    for _, g in final.groupby(['seed', 'method']):
        require(g.row_id.is_unique, 'One sample crosses AL validation/test partitions.')
    return final, config


def prepare_dynamic_template(al_run, out):
    predictions, config = al_final_predictions(al_run)
    out.mkdir(parents=True, exist_ok=False)
    ids = sorted(predictions.row_id.unique())
    frame = pd.DataFrame({'row_id': ids})
    for name in DYNAMIC_COLUMNS[1:]:
        frame[name] = ''
    frame.to_csv(out / 'dynamic_measurements.csv', index=False)
    write_json(out / 'provenance.json', {
        'dataset_sha256': config['dataset']['data_sha256'],
        'measurements_sha256': None, 'signal_origin': 'not_collected',
        'label_definition': 'Fill from independently documented source; current CSV semantics are unverified.',
        'dynamic_score_definition': '', 'observation_policy': '', 'collection_tool': '',
        'collection_period': '', 'no_target_label_in_score': False,
        'notes': 'Fill with actual observations. Set signal_origin=observed only for measured reports. Hashes verify integrity, not factual authenticity.'})
    split_rows = predictions[['row_id', 'split', 'label']].drop_duplicates().sort_values('row_id')
    split_rows.to_csv(out / 'row_mapping.csv', index=False)
    (out / 'README.md').write_text(
        '# Thu thập tín hiệu động\n\n'
        'Đây là mẫu trống; không có điểm động được sinh tự động. `row_id` là dòng 0-based trong CSV có hash ghi trong provenance.json, không phải hash tệp PE. '
        'Chỉ thu thập khi ghép được dòng đó với đúng tệp/phiên quan sát. Không suy ra p_dynamic từ label hoặc thêm nhiễu vào p_static.\n\n'
        'Điền p_dynamic từ quy tắc/model cố định trước test; mô tả thang điểm (xác suất đã hiệu chuẩn hay risk score), nguồn model và dữ liệu huấn luyện. '
        'sequence_id/sequence_order phải có nghĩa thực tế; đặt một ID riêng cho mỗi mẫu độc lập. '
        'Các phiên validation/test phải độc lập. Giữ cửa sổ/chính sách quan sát chung.\n\n'
        'Lưu báo cáo quan sát trong reports/ bên cạnh CSV; report_path là đường dẫn tương đối tới tệp và report_sha256 là SHA-256 nội dung. '
        'Mỗi hàng cần báo cáo riêng. Điền provenance.json, gồm hash CSV sau khi hoàn tất và xác nhận phép tính điểm không đọc nhãn đích. '
        'Runner kiểm tra đầy đủ ID, split, hash và schema; metadata tự khai không tự chứng minh dữ liệu là quan sát thực.\n', encoding='utf-8')
    return {'status': 'template_created', 'required_observations': len(ids), 'data_sha256': config['dataset']['data_sha256']}


def load_dynamic(path, provenance_path, predictions, al_config):
    path = Path(path).resolve()
    meta = json.loads(Path(provenance_path).read_text())
    require(meta.get('signal_origin') == 'observed', 'Dynamic observations are missing or declared simulated. Demo traces cannot validate PID.')
    require(meta.get('no_target_label_in_score') is True, 'Document a dynamic scoring rule that does not use the target label.')
    for key in ['dynamic_score_definition', 'observation_policy', 'collection_tool', 'collection_period', 'label_definition']:
        require(isinstance(meta.get(key), str) and bool(meta[key].strip()), f'Missing provenance field: {key}')
    require(meta.get('dataset_sha256') == al_config['dataset']['data_sha256'], 'Dynamic row IDs refer to a different dataset.')
    require(meta.get('measurements_sha256') == sha256(path), 'Dynamic measurement checksum mismatch.')
    frame = pd.read_csv(path, dtype={'sequence_id': str, 'report_path': str, 'report_sha256': str})
    require(set(DYNAMIC_COLUMNS) <= set(frame), f'Required dynamic columns: {DYNAMIC_COLUMNS}')
    require(not frame[DYNAMIC_COLUMNS].isna().any().any(), 'Dynamic template is incomplete.')
    require(frame.row_id.is_unique and set(frame.row_id) == set(predictions.row_id), 'Need exactly one observation for every validation/test row ID.')
    probabilities(frame.p_dynamic)
    orders = pd.to_numeric(frame.sequence_order)
    frame['sequence_order'] = orders
    require(np.isfinite(orders).all() and not frame.duplicated(['sequence_id', 'sequence_order']).any(), 'Sequence order must be finite and unique within a session.')
    require(frame.sequence_id.str.strip().ne('').all(), 'Empty sequence ID.')
    partition = predictions[['row_id', 'split']].drop_duplicates()
    require(partition.row_id.is_unique, 'Inconsistent AL splits across seeds/methods.')
    joined = frame.merge(partition, on='row_id', validate='one_to_one')
    require(joined.groupby('sequence_id').split.nunique().max() == 1, 'A dynamic session spans validation and test; define independent sessions/splits.')
    reports = []
    for row in frame.itertuples():
        report = (path.parent / row.report_path).resolve()
        require(report.is_relative_to(path.parent) and report.is_file(), 'Report must exist under the measurement directory.')
        require(sha256(report) == row.report_sha256, f'Report hash mismatch for row {row.row_id}.')
        reports.append(str(report))
    require(len(set(reports)) == len(reports), 'Expected a distinct per-observation report; export per-sample reports before evaluation.')
    return frame, meta


def sequence_scores(frame, gains):
    """Reset at each independent session; never carry validation state into test."""
    scores = pd.Series(index=frame.index, dtype=float)
    weights = pd.Series(index=frame.index, dtype=float)
    for _, sequence in frame.groupby('sequence_id', sort=True):
        controller = PIDController(*gains)
        for row in sequence.sort_values('sequence_order').itertuples():
            w = controller.update(float(row.probability - row.p_dynamic))
            weights.loc[row.Index] = w
            scores.loc[row.Index] = w * row.probability + (1 - w) * row.p_dynamic
    # Preserve the caller's row order even when the frame carries a filtered,
    # non-contiguous index.  This keeps each score aligned with its label.
    return scores.loc[frame.index].to_numpy(), weights.loc[frame.index].to_numpy()


def candidate_grids():
    kp = [.425, .85, 1.7]
    return {'P': [(v, 0., 0.) for v in [0., *kp]],
            'PI': list(itertools.product(kp, [0., .06, .12], [0.])),
            'PID': list(itertools.product(kp, [0., .06, .12], [0., .175, .35]))}


def select_on_validation(validation, kind, target_tpr=.95):
    candidates = list(np.linspace(0, 1, 11)) if kind == 'Fixed_weight' else candidate_grids()[kind]
    trials = []
    for setting in candidates:
        p = (setting * validation.probability.to_numpy() + (1 - setting) * validation.p_dynamic.to_numpy()
             if kind == 'Fixed_weight' else sequence_scores(validation, setting)[0])
        threshold = choose_threshold(validation.label, p, target_tpr)
        metrics = evaluate(validation.label, p, threshold)
        trials.append({'setting': float(setting) if kind == 'Fixed_weight' else list(setting),
                       'threshold': threshold, **metrics})
    # Declared tie policy: max validation AUC, then lower validation FPR, then grid order.
    winner = max(range(len(trials)), key=lambda i: (trials[i]['auc'], -trials[i]['fpr'], -i))
    return trials[winner]['setting'], trials


def run(al_run, dynamic_path, provenance_path, out, target_tpr=.95):
    require(0 < target_tpr <= 1, 'Invalid validation TPR target.')
    predictions, al_config = al_final_predictions(al_run)
    dynamic, provenance = load_dynamic(dynamic_path, provenance_path, predictions, al_config)
    out.mkdir(parents=True, exist_ok=False)
    joined = predictions.merge(dynamic, on='row_id', validate='many_to_one')
    require(not joined.duplicated(['seed', 'method', 'row_id']).any(), 'Unexpected joined duplicates.')
    joined.to_csv(out / 'paired_inputs.csv.gz', index=False)
    config = {'kind': 'fusion', 'al_config': al_config, 'al_predictions_sha256': sha256(Path(al_run) / 'predictions.csv.gz'),
              'dynamic_provenance': provenance, 'dynamic_provenance_sha256': sha256(provenance_path),
              'target_validation_tpr': target_tpr, 'grids': candidate_grids(),
              'selection': 'Maximum validation AUC, lower validation FPR on tie, then candidate order.',
              'state_policy': 'Reset for every sequence_id, split, seed and AL method; sort by sequence_order.',
              'gate_policy': 'All supplied pairs evaluated. No early-exit gate or deployment coverage claim.',
              'timing_scope': 'Offline fusion score replay, including Python/session traversal; excludes signal collection, model inference and I/O.',
              'provenance_scope': 'Report existence/hash and declared origin checked; factual authenticity is not automatically established.',
              **source_metadata()}
    write_json(out / 'config.json', config)
    rows, outputs, tuning = [], [], []
    for (seed, strategy), g in joined.groupby(['seed', 'method']):
        validation, test = [g[g.split == split].copy() for split in ['validation', 'test']]
        settings = {'Static_only': 1., 'Dynamic_only': 0., 'Average_50_50': .5,
                    'PID_default': [.85, .12, .35]}
        for kind in ['Fixed_weight', 'P', 'PI', 'PID']:
            settings[kind], trials = select_on_validation(validation, kind, target_tpr)
            tuning.append({'seed': int(seed), 'strategy': strategy, 'fusion': kind, 'selected': settings[kind], 'trials': trials})
        for kind, setting in settings.items():
            scores, timings = {}, {}
            for split, subset in [('validation', validation), ('test', test)]:
                t0 = perf_counter()
                if isinstance(setting, (int, float)):
                    p = setting * subset.probability.to_numpy() + (1 - setting) * subset.p_dynamic.to_numpy()
                    weights = np.full(len(subset), setting)
                else:
                    p, weights = sequence_scores(subset, setting)
                timings[split] = (perf_counter() - t0) * 1000 / len(subset)
                scores[split] = p
                output = subset[['row_id', 'label', 'split', 'sequence_id', 'sequence_order']].copy()
                output['seed'], output['strategy'], output['fusion'] = seed, strategy, kind
                output['score'], output['w_static'] = p, weights
                outputs.append(output)
            threshold = choose_threshold(validation.label, scores['validation'], target_tpr)
            metric = evaluate(test.label, scores['test'], threshold)
            rows.append({'seed': int(seed), 'strategy': strategy, 'fusion': kind, 'threshold': threshold,
                         'test_replay_ms_per_row': timings['test'], **metric})
    metrics = pd.DataFrame(rows)
    metrics.to_csv(out / 'fusion_metrics.csv', index=False)
    pd.concat(outputs, ignore_index=True).to_csv(out / 'fusion_predictions.csv.gz', index=False)
    write_json(out / 'validation_search.json', tuning)
    interaction = []
    for seed, g in metrics.groupby('seed'):
        for metric in ['auc', 'ap', 'fpr', 'tpr']:
            at = {(r.strategy, r.fusion): getattr(r, metric) for r in g.itertuples()}
            required = [('Random', 'Fixed_weight'), ('Random', 'PID'), ('XAI_full', 'Fixed_weight'), ('XAI_full', 'PID')]
            if all(k in at for k in required):
                a, b, c, d = [at[k] for k in required]
                interaction.append({'seed': int(seed), 'metric': metric, 'fixed_random': a, 'pid_random': b,
                                    'fixed_xai': c, 'pid_xai': d, 'difference_of_differences': (d - c) - (b - a)})
    pd.DataFrame(interaction).to_csv(out / 'factorial_2x2.csv', index=False)
    summary = {'status': 'measured_from_supplied_observations',
               'results': [{'strategy': strategy, 'fusion': fusion,
                            **{metric: stats(g[metric]) for metric in ['auc', 'ap', 'fpr', 'tpr']}}
                           for (strategy, fusion), g in metrics.groupby(['strategy', 'fusion'])],
               'factorial_rows': len(interaction),
               'limitations': [config['provenance_scope'], config['gate_policy'],
                               'One observation per independent sequence cannot identify separate historical I/D benefits.',
                               'FPR is reported with achieved test TPR; fusion compute time is not end-to-end latency.']}
    write_json(out / 'summary.json', summary)
    return summary
