"""Prepare the multi-time-step observation contract required to test PID terms."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .common import require, sha256, write_json
from .fusion import al_final_predictions


TEMPORAL_COLUMNS = [
    'row_id', 'execution_id', 'time_step', 'elapsed_seconds', 'p_dynamic',
    'evidence_status', 'report_path', 'report_sha256',
]


def prepare(al_run, out, windows=(5., 15., 30., 60.)):
    windows = [float(value) for value in windows]
    require(len(windows) >= 2 and all(np.isfinite(windows)) and all(value > 0 for value in windows),
            'At least two finite positive observation windows are required to identify temporal PID terms.')
    require(windows == sorted(set(windows)), 'Observation windows must be unique and increasing.')
    predictions, config = al_final_predictions(al_run)
    mapping = predictions[['row_id', 'split', 'label']].drop_duplicates().sort_values('row_id')
    require(mapping.row_id.is_unique, 'AL row mapping is inconsistent.')
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    rows = []
    for item in mapping.itertuples():
        for step, elapsed in enumerate(windows):
            rows.append({
                'row_id': int(item.row_id), 'execution_id': f'row_{int(item.row_id)}_run_1',
                'time_step': step, 'elapsed_seconds': elapsed, 'p_dynamic': '',
                'evidence_status': '', 'report_path': '', 'report_sha256': '',
            })
    pd.DataFrame(rows, columns=TEMPORAL_COLUMNS).to_csv(out / 'dynamic_time_series.csv', index=False)
    mapping.to_csv(out / 'row_mapping.csv', index=False)
    write_json(out / 'provenance.json', {
        'dataset_sha256': config['dataset']['data_sha256'],
        'measurements_sha256': None,
        'signal_origin': 'not_collected',
        'label_definition': '', 'dynamic_feature_definition': '', 'dynamic_score_definition': '',
        'dynamic_model_training_source': '', 'calibration_method': '', 'sandbox_or_honeypot': '',
        'collection_period': '', 'observation_windows_seconds': windows,
        'no_target_label_in_score': False,
        'notes': 'Template only. Prefilled execution IDs and windows are planned identifiers, not observations.',
    })
    (out / 'README.md').write_text(
        '# Mẫu quan sát động theo thời gian\n\n'
        'Mỗi `row_id` có nhiều time step trong cùng một `execution_id`; trạng thái PID phải reset khi đổi execution. '
        'Các execution ID được điền sẵn chỉ là kế hoạch đặt tên. Thay chúng nếu hệ thống sandbox cung cấp ID thật.\n\n'
        '`p_dynamic` phải do một scorer đóng băng tạo từ hành vi quan sát đến `elapsed_seconds`, không đọc target label. '
        '`evidence_status` dùng một trong: `observed`, `no_behavior`, `sandbox_failure`, `missing`. '
        'Với `observed` hoặc `no_behavior`, điền score và báo cáo/hash. Với failure/missing, lưu failure report nếu có và để score trống; '
        'policy xử lý missing phải được khai báo trước test.\n\n'
        'Báo cáo có thể dùng chung cho nhiều time step của cùng execution nếu score được tái tạo bằng cách cắt event theo timestamp. '
        'Không dùng cùng report cho hai PE khác nhau. `row_mapping.csv` chỉ hỗ trợ ghép dữ liệu; không đưa label vào scorer.\n',
        encoding='utf-8')
    return {'status': 'temporal_template_created', 'samples': len(mapping),
            'time_steps_per_sample': len(windows), 'required_rows': len(rows), 'windows_seconds': windows}


def validate(path, provenance_path, expected_dataset_sha256=None):
    path = Path(path).resolve()
    frame = pd.read_csv(path, dtype={'execution_id': str, 'evidence_status': str,
                                    'report_path': str, 'report_sha256': str})
    require(set(TEMPORAL_COLUMNS) <= set(frame), f'Required columns: {TEMPORAL_COLUMNS}')
    require(not frame[['row_id', 'execution_id', 'time_step', 'elapsed_seconds', 'evidence_status']].isna().any().any(),
            'Temporal identity/status fields are incomplete.')
    require(not frame.duplicated(['row_id', 'execution_id', 'time_step']).any(), 'Duplicate temporal observation key.')
    require(set(frame.evidence_status) <= {'observed', 'no_behavior', 'sandbox_failure', 'missing'}, 'Unknown evidence_status.')
    for _, execution in frame.groupby(['row_id', 'execution_id']):
        ordered = execution.sort_values('time_step')
        require(np.all(np.diff(ordered.time_step) > 0) and np.all(np.diff(ordered.elapsed_seconds) > 0),
                'time_step and elapsed_seconds must increase within each execution.')
    scored = frame.evidence_status.isin(['observed', 'no_behavior'])
    require(frame.loc[scored, 'p_dynamic'].notna().all(), 'Observed/no-behavior rows require p_dynamic.')
    values = pd.to_numeric(frame.loc[scored, 'p_dynamic'])
    require(np.isfinite(values).all() and values.between(0, 1).all(), 'Dynamic scores must be finite values in [0,1].')
    owners = {}
    for row in frame.loc[scored].itertuples():
        require(bool(row.report_path.strip()) and bool(row.report_sha256.strip()), 'Scored rows require report path and hash.')
        report = (path.parent / row.report_path).resolve()
        require(report.is_relative_to(path.parent) and report.is_file(), 'Dynamic report must exist under the observation directory.')
        require(sha256(report) == row.report_sha256, f'Report hash mismatch for row {row.row_id}, step {row.time_step}.')
        owner = (int(row.row_id), row.execution_id)
        require(str(report) not in owners or owners[str(report)] == owner, 'One dynamic report is linked to different PE executions.')
        owners[str(report)] = owner
    meta = json.loads(Path(provenance_path).read_text())
    require(meta.get('signal_origin') == 'observed', 'Temporal data are not declared observed.')
    require(meta.get('no_target_label_in_score') is True, 'Scoring must explicitly exclude target labels.')
    require(meta.get('measurements_sha256') == sha256(path), 'Temporal measurement checksum mismatch.')
    for key in ['label_definition', 'dynamic_feature_definition', 'dynamic_score_definition',
                'dynamic_model_training_source', 'calibration_method', 'sandbox_or_honeypot', 'collection_period']:
        require(isinstance(meta.get(key), str) and bool(meta[key].strip()), f'Missing provenance field: {key}')
    if expected_dataset_sha256:
        require(meta.get('dataset_sha256') == expected_dataset_sha256, 'Dataset checksum mismatch.')
    return {'status': 'valid_schema', 'rows': len(frame), 'samples': frame.row_id.nunique(),
            'executions': frame.execution_id.nunique(), 'scored_rows': int(scored.sum()),
            'missing_or_failed_rows': int((~scored).sum())}
