"""Command line for measured runs, provenance audit and dynamic-data preparation."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import traceback

from . import (active_learning, confirmatory, fidelity, fusion, gating,
               malbehavd_pid, provenance, recovery, robust_fidelity, temporal,
               temporal_fusion)
from .common import DEFAULT_DATA, REPO, finish_manifest, load_dataset, require, write_json
from .verification import verify_al, verify_fidelity, verify_saved_run


def parser():
    p = argparse.ArgumentParser(description='Measured thesis experiments. No fixed results or simulated fallback.')
    sub = p.add_subparsers(dest='command', required=True)
    run = sub.add_parser('run', help='Train and evaluate AL and/or Fidelity from a feature CSV.')
    run.add_argument('--only', choices=['all', 'al', 'fidelity'], default='all')
    run.add_argument('--data', type=Path, default=DEFAULT_DATA)
    run.add_argument('--row-manifest', type=Path, help='Optional row_id/label/SHA-256 manifest for verified static provenance.')
    run.add_argument('--output', type=Path, required=True, help='A NEW output directory; never overwrites an old run.')
    run.add_argument('--split-file', type=Path, help='Optional complete row_id,split CSV; groups/time splits must be defined upstream.')
    run.add_argument('--split-seed', type=int, default=42)
    run.add_argument('--seeds', nargs='+', type=int, default=[11, 22, 33, 44, 55])
    run.add_argument('--initial-labels', type=int, default=200)
    run.add_argument('--rounds', type=int, default=5)
    run.add_argument('--batch-size', type=int, default=100)
    run.add_argument('--al-trees', type=int, default=60)
    run.add_argument('--fidelity-trees', type=int, default=100)
    run.add_argument('--fidelity-seed', type=int, default=42)
    run.add_argument('--k', nargs='+', type=int, default=[10, 25, 50])
    run.add_argument('--random-masks', type=int, default=20)
    run.add_argument('--bootstrap', type=int, default=500)
    run.add_argument('--max-fidelity-test-rows', type=int, default=1000)
    run.add_argument('--threads', type=int, default=2)
    run.add_argument('--target-tpr', type=float, default=.95)
    run.add_argument('--target-val-auc', type=float, help='Optional predeclared target for label-budget-to-quality analysis.')
    confirm = sub.add_parser('confirmatory-al', help='Run cross-fold AL with a full-pool-relative label-efficiency target.')
    confirm.add_argument('--data', type=Path, default=DEFAULT_DATA)
    confirm.add_argument('--row-manifest', type=Path)
    confirm.add_argument('--output', type=Path, required=True)
    confirm.add_argument('--folds', type=int, default=5)
    confirm.add_argument('--fold-seed', type=int, default=2026)
    confirm.add_argument('--seeds', nargs='+', type=int, default=[11, 22, 33, 44, 55])
    confirm.add_argument('--initial-labels', type=int, default=200)
    confirm.add_argument('--rounds', type=int, default=10)
    confirm.add_argument('--batch-size', type=int, default=100)
    confirm.add_argument('--trees', type=int, default=60)
    confirm.add_argument('--threads', type=int, default=2)
    confirm.add_argument('--target-tpr', type=float, default=.95)
    confirm.add_argument('--target-excess-auc-fraction', type=float, default=.95)
    confirm_fidelity = sub.add_parser(
        'confirmatory-fidelity',
        help='Repeat Fidelity across folds, stochastic model seeds and mean/median masking baselines.')
    confirm_fidelity.add_argument('--data', type=Path, default=DEFAULT_DATA)
    confirm_fidelity.add_argument('--row-manifest', type=Path)
    confirm_fidelity.add_argument('--split-dir', type=Path,
                                  help='Directory containing fold_*.csv from confirmatory-al.')
    confirm_fidelity.add_argument('--output', type=Path, required=True)
    confirm_fidelity.add_argument('--seeds', nargs='+', type=int, default=[41, 42, 43, 44, 45])
    confirm_fidelity.add_argument('--baselines', nargs='+', choices=['mean', 'median'],
                                  default=['mean', 'median'])
    confirm_fidelity.add_argument('--k', nargs='+', type=int, default=[10, 25, 50])
    confirm_fidelity.add_argument('--random-masks', type=int, default=20)
    confirm_fidelity.add_argument('--bootstrap', type=int, default=500)
    confirm_fidelity.add_argument('--trees', type=int, default=100)
    confirm_fidelity.add_argument('--threads', type=int, default=2)
    confirm_fidelity.add_argument('--max-test-rows', type=int, default=1000)
    confirm_fidelity.add_argument('--feature-fraction', type=float, default=.8)
    confirm_fidelity.add_argument('--bagging-fraction', type=float, default=.8)
    audit = sub.add_parser('audit-data', help='Inspect the feature data and split without training.')
    audit.add_argument('--data', type=Path, default=DEFAULT_DATA)
    audit.add_argument('--row-manifest', type=Path)
    audit.add_argument('--split-file', type=Path)
    audit.add_argument('--split-seed', type=int, default=42)
    audit.add_argument('--output', type=Path)
    verify = sub.add_parser('verify', help='Recompute metrics and predictions from saved models/masks.')
    verify.add_argument('--run', type=Path, required=True)
    verify.add_argument('--data', type=Path, help='Override original CSV location; hash must still match.')
    prepare = sub.add_parser('prepare-dynamic', help='Write a blank observation template aligned to AL validation/test IDs.')
    prepare.add_argument('--al-run', type=Path, required=True)
    prepare.add_argument('--output', type=Path, required=True)
    pid = sub.add_parser('fusion', help='Run PID ablations and the 2x2 study with actual supplied dynamic observations.')
    pid.add_argument('--al-run', type=Path, required=True)
    pid.add_argument('--dynamic-data', type=Path, required=True)
    pid.add_argument('--provenance', type=Path, required=True)
    pid.add_argument('--output', type=Path, required=True)
    pid.add_argument('--target-tpr', type=float, default=.95)
    pid_audit = sub.add_parser('audit-pid-inputs', help='Check whether paired PE and dynamic evidence exist for PID experiments.')
    pid_audit.add_argument('--data', type=Path, default=DEFAULT_DATA)
    pid_audit.add_argument('--output', type=Path)
    gate = sub.add_parser('gate', help='Calibrate saved final AL probabilities and evaluate a validation-selected static uncertainty gate.')
    gate.add_argument('--al-run', type=Path, required=True)
    gate.add_argument('--output', type=Path, required=True)
    gate.add_argument('--calibration-fraction', type=float, default=.5)
    gate.add_argument('--partition-seed', type=int, default=2026)
    gate.add_argument('--max-early-fnr', type=float, default=.02)
    gate.add_argument('--max-early-fpr', type=float, default=.02)
    temporal_template = sub.add_parser('prepare-temporal', help='Create a multi-time-step dynamic observation template for PID.')
    temporal_template.add_argument('--al-run', type=Path, required=True)
    temporal_template.add_argument('--output', type=Path, required=True)
    temporal_template.add_argument('--windows', nargs='+', type=float, default=[5, 15, 30, 60])
    temporal_validate = sub.add_parser('validate-temporal', help='Validate collected temporal dynamic observations before PID evaluation.')
    temporal_validate.add_argument('--data', type=Path, required=True)
    temporal_validate.add_argument('--provenance', type=Path, required=True)
    temporal_validate.add_argument('--dataset-sha256')
    temporal_pid = sub.add_parser(
        'temporal-fusion',
        help='Run Static/Dynamic/Average/Fixed/P/PI/PID on validated multi-time-step reports.')
    temporal_pid.add_argument('--al-run', type=Path, required=True)
    temporal_pid.add_argument('--temporal-data', type=Path, required=True)
    temporal_pid.add_argument('--provenance', type=Path, required=True)
    temporal_pid.add_argument('--output', type=Path, required=True)
    temporal_pid.add_argument('--target-tpr', type=float, default=.95)
    temporal_pid.add_argument('--integral-limits', nargs=2, type=float, default=[-5., 5.])
    inspect_source = sub.add_parser('inspect-source', help='Inspect a large NPZ without loading its feature matrix into memory.')
    inspect_source.add_argument('--source', type=Path, required=True)
    inspect_source.add_argument('--output', type=Path)
    inspect_source.add_argument('--hash-source', action='store_true', help='Hash the entire archive; slow for tens of GB.')
    recover = sub.add_parser('recover-manifest', help='Recreate mini-dataset source indices and optionally join aligned JSONL metadata.')
    recover.add_argument('--source', type=Path, required=True)
    recover.add_argument('--mini', type=Path, default=DEFAULT_DATA)
    recover.add_argument('--output', type=Path, required=True)
    recover.add_argument('--metadata-jsonl', nargs='+', type=Path)
    recover.add_argument('--n-negative', type=int, default=1500)
    recover.add_argument('--n-positive', type=int, default=500)
    recover.add_argument('--seed', type=int, default=42)
    recover.add_argument('--hash-source', action='store_true')
    sorel = sub.add_parser('recover-sorel-metadata', help='Map recovered SOREL NPZ row indices to meta.db SHA-256 and tags.')
    sorel.add_argument('--manifest', type=Path, required=True)
    sorel.add_argument('--source-inspection', type=Path, required=True)
    sorel.add_argument('--source', type=Path, help='Original SOREL NPZ; loads only its label vector for full-order verification.')
    sorel.add_argument('--meta-db', type=Path, required=True)
    sorel.add_argument('--missing-shas', type=Path, required=True)
    sorel.add_argument('--output', type=Path, required=True)
    sorel.add_argument('--test-split', type=float, default=recovery.SOREL_TEST_SPLIT)
    sorel.add_argument('--hash-meta-db', action='store_true', help='Hash the multi-GB SQLite file; slow but useful for a frozen run.')
    ember = sub.add_parser('recover-ember-dataset', help='Build a SHA-aligned mini CSV from EMBER 2018 X/y/JSONL test files.')
    ember.add_argument('--data-dir', type=Path, required=True)
    ember.add_argument('--output', type=Path, required=True)
    ember.add_argument('--n-negative', type=int, default=1500)
    ember.add_argument('--n-positive', type=int, default=500)
    ember.add_argument('--seed', type=int, default=42)
    ember.add_argument('--features', type=int, default=2381)
    ember.add_argument('--hash-source-files', action='store_true')
    malbehavd = sub.add_parser(
        'prepare-malbehavd',
        help='Audit and freeze a report-only MalBehavD-V1 cohort for event-indexed PID.')
    malbehavd.add_argument('--source', type=Path, required=True)
    malbehavd.add_argument('--output', type=Path, required=True)
    malbehavd.add_argument('--min-events', type=int, default=20)
    malbehavd.add_argument('--folds', type=int, default=5)
    malbehavd.add_argument('--seed', type=int, default=2026)
    vt = sub.add_parser(
        'collect-vt-static',
        help='Fetch intrinsic PE metadata by SHA-256; never downloads executable content.')
    vt.add_argument('--cohort', type=Path, required=True)
    vt.add_argument('--output', type=Path, required=True)
    vt.add_argument('--limit', type=int, help='Balanced pilot size; omit for the entire cohort.')
    vt.add_argument('--seed', type=int, default=2026)
    vt.add_argument('--requests-per-minute', type=float, default=4.0)
    vt.add_argument('--api-key-env', default='VT_API_KEY')
    vt.add_argument('--max-new', type=int,
                    help='Maximum uncached API requests in this invocation; useful for daily quota.')
    event_pid = sub.add_parser(
        'event-pid',
        help='Run Static/Dynamic/Average/Fixed/P/PI/PID on ordered public API-call reports.')
    event_pid.add_argument('--sequences', type=Path, required=True)
    event_pid.add_argument('--static-features', type=Path, required=True)
    event_pid.add_argument('--selection', type=Path,
                           help='Optional predeclared pilot/full cohort manifest used as coverage denominator.')
    event_pid.add_argument('--output', type=Path, required=True)
    event_pid.add_argument('--windows', nargs='+', type=int, default=[5, 10, 15, 20])
    event_pid.add_argument('--target-tpr', type=float, default=.95)
    event_pid.add_argument('--min-coverage', type=float, default=.8)
    event_pid.add_argument('--validation-fraction', type=float, default=.2)
    event_pid.add_argument('--calibration-fraction', type=float, default=.2)
    event_pid.add_argument('--bootstrap', type=int, default=1000)
    event_pid.add_argument('--seed', type=int, default=2026)
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == 'audit-data':
            data = load_dataset(args.data, args.split_seed, args.split_file, args.row_manifest)
            if args.output:
                args.output.mkdir(parents=True, exist_ok=False)
                data.save_split(args.output)
                finish_manifest(args.output)
            print(json.dumps(data.audit, ensure_ascii=False, indent=2))
            return 0
        if args.command == 'confirmatory-al':
            result = confirmatory.run(
                args.data, args.row_manifest, args.output, args.folds, args.fold_seed,
                args.seeds, args.initial_labels, args.rounds, args.batch_size,
                args.trees, args.threads, args.target_tpr,
                args.target_excess_auc_fraction,
            )
            finish_manifest(args.output)
            print(json.dumps({'status': result['status'], 'output': str(args.output.resolve())},
                             ensure_ascii=False, indent=2))
            return 0
        if args.command == 'confirmatory-fidelity':
            result = robust_fidelity.run(
                args.data, args.row_manifest, args.output, args.split_dir,
                args.seeds, args.baselines, args.k, args.random_masks,
                args.bootstrap, args.trees, args.threads, args.max_test_rows,
                args.feature_fraction, args.bagging_fraction,
            )
            finish_manifest(args.output)
            print(json.dumps({'status': result['status'], 'output': str(args.output.resolve())},
                             ensure_ascii=False, indent=2))
            return 0
        if args.command == 'verify':
            print(json.dumps(verify_saved_run(args.run, args.data), ensure_ascii=False, indent=2))
            return 0
        if args.command == 'audit-pid-inputs':
            result = provenance.audit(args.data, output=args.output)
            if args.output:
                finish_manifest(args.output)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result['status'] == 'ready' else 3
        if args.command == 'gate':
            result = gating.run(args.al_run, args.output, args.calibration_fraction, args.partition_seed,
                                args.max_early_fnr, args.max_early_fpr)
            finish_manifest(args.output)
            print(json.dumps({'status': result['status'], 'output': str(args.output.resolve())}, ensure_ascii=False, indent=2))
            return 0
        if args.command == 'prepare-temporal':
            result = temporal.prepare(args.al_run, args.output, args.windows)
            finish_manifest(args.output)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == 'validate-temporal':
            print(json.dumps(temporal.validate(args.data, args.provenance, args.dataset_sha256), ensure_ascii=False, indent=2))
            return 0
        if args.command == 'temporal-fusion':
            result = temporal_fusion.run(
                args.al_run, args.temporal_data, args.provenance, args.output,
                args.target_tpr, tuple(args.integral_limits),
            )
            finish_manifest(args.output)
            print(json.dumps({'status': result['status'], 'output': str(args.output.resolve())},
                             ensure_ascii=False, indent=2))
            return 0
        if args.command == 'inspect-source':
            result = recovery.inspect_npz(args.source, args.hash_source)
            if args.output:
                args.output.mkdir(parents=True, exist_ok=False)
                write_json(args.output / 'source_inspection.json', result)
                finish_manifest(args.output)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == 'recover-manifest':
            result = recovery.recover(args.source, args.mini, args.output, args.metadata_jsonl,
                                      args.n_negative, args.n_positive, args.seed, args.hash_source)
            finish_manifest(args.output)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == 'recover-sorel-metadata':
            result = recovery.recover_sorel_metadata(
                args.manifest, args.source_inspection, args.meta_db, args.missing_shas,
                args.output, args.test_split, args.hash_meta_db, args.source)
            finish_manifest(args.output)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == 'recover-ember-dataset':
            result = recovery.recover_ember_dataset(
                args.data_dir, args.output, args.n_negative, args.n_positive,
                args.seed, args.features, args.hash_source_files)
            finish_manifest(args.output)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == 'prepare-malbehavd':
            result = malbehavd_pid.prepare(
                args.source, args.output, args.min_events, args.folds, args.seed)
            finish_manifest(args.output)
            print(json.dumps({'status': result['status'], 'output': str(args.output.resolve()),
                              'eligible_rows': result['eligible_rows']}, ensure_ascii=False, indent=2))
            return 0
        if args.command == 'collect-vt-static':
            result = malbehavd_pid.collect_vt(
                args.cohort, args.output, args.limit, args.seed,
                args.requests_per_minute, args.api_key_env, args.max_new)
            finish_manifest(args.output)
            print(json.dumps({'status': result['status'], 'output': str(args.output.resolve()),
                              'usable_rows': result['usable_rows'], 'coverage': result['coverage']},
                             ensure_ascii=False, indent=2))
            return 0
        if args.command == 'event-pid':
            result = malbehavd_pid.run_event_pid(
                args.sequences, args.static_features, args.output, tuple(args.windows),
                args.target_tpr, args.min_coverage, args.validation_fraction,
                args.calibration_fraction, args.bootstrap, args.seed, args.selection)
            finish_manifest(args.output)
            print(json.dumps({'status': result['status'], 'output': str(args.output.resolve()),
                              'samples': result['samples']}, ensure_ascii=False, indent=2))
            return 0
        if args.command == 'prepare-dynamic':
            result = fusion.prepare_dynamic_template(args.al_run, args.output)
            finish_manifest(args.output)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == 'fusion':
            result = fusion.run(args.al_run, args.dynamic_data, args.provenance, args.output, args.target_tpr)
            from . import reporting
            reporting.fusion_report(args.output)
            finish_manifest(args.output)
            print(json.dumps({'status': result['status'], 'output': str(args.output)}, ensure_ascii=False))
            return 0

        data = load_dataset(args.data, args.split_seed, args.split_file, args.row_manifest)
        args.output.mkdir(parents=True, exist_ok=False)
        status = {'started_at_utc': datetime.now(timezone.utc).isoformat(), 'command': vars(args).copy(),
                  'status': 'running', 'experiments': {},
                  'fusion': {'status': 'not_run', 'reason': 'Requires actual dynamic reports aligned to validation/test IDs; use prepare-dynamic then fusion.'}}
        status['command'] = {k: str(v) if isinstance(v, Path) else v for k, v in status['command'].items()}
        write_json(args.output / 'run_status.json', status)
        try:
            from . import reporting
            checks = {}
            if args.only in ['all', 'al']:
                folder = args.output / 'al'
                result = active_learning.run(data, folder, args.seeds, args.initial_labels, args.rounds,
                    args.batch_size, args.al_trees, args.threads, args.target_tpr, args.target_val_auc)
                reporting.al_report(folder)
                checks['al'] = verify_al(folder, data)
                status['experiments']['al'] = {'status': result['status'], 'models': result['counts']['models']}
            if args.only in ['all', 'fidelity']:
                folder = args.output / 'fidelity'
                result = fidelity.run(data, folder, args.fidelity_seed, args.k, args.random_masks, args.bootstrap,
                                      args.fidelity_trees, args.threads, args.max_fidelity_test_rows)
                reporting.fidelity_report(folder)
                checks['fidelity'] = verify_fidelity(folder, data)
                status['experiments']['fidelity'] = {'status': result['status'], 'evaluation_rows': result['evaluation_rows']}
            write_json(args.output / 'verification.json', checks)
            status['status'] = 'completed_selected_experiments'
            status['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
        except Exception as error:
            status['status'] = 'failed'
            status['error'] = f'{type(error).__name__}: {error}'
            write_json(args.output / 'run_status.json', status)
            raise
        write_json(args.output / 'run_status.json', status)
        (args.output / 'README.md').write_text(
            '# Kết quả thực nghiệm đã đo\n\n'
            'Xem al/REPORT.md, fidelity/REPORT.md (nếu đã chọn chạy), run_status.json và verification.json. '
            'Các bảng .tex, CSV và biểu đồ PDF/PNG được sinh từ dự đoán đã lưu. '
            'Bộ mặc định không chạy PID khi chưa có tín hiệu động thật. '
            'Không dùng các log demo hay bảng cũ trong results/ làm bằng chứng của lần chạy này.\n\n'
            + '\n'.join(f'- {item}' for item in data.audit['limitations']) + '\n', encoding='utf-8')
        finish_manifest(args.output)
        print(json.dumps({'status': status['status'], 'output': str(args.output.resolve()), 'fusion': status['fusion']}, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, FileNotFoundError, FileExistsError) as error:
        print(f'ERROR: {error}', flush=True)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
