"""Command line for measured runs, provenance audit and dynamic-data preparation."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import traceback

from . import active_learning, fidelity, fusion, gating, provenance, recovery, temporal
from .common import DEFAULT_DATA, REPO, finish_manifest, load_dataset, require, write_json
from .verification import verify_al, verify_fidelity, verify_saved_run


def parser():
    p = argparse.ArgumentParser(description='Measured thesis experiments. No fixed results or simulated fallback.')
    sub = p.add_subparsers(dest='command', required=True)
    run = sub.add_parser('run', help='Train and evaluate AL and/or Fidelity from a feature CSV.')
    run.add_argument('--only', choices=['all', 'al', 'fidelity'], default='all')
    run.add_argument('--data', type=Path, default=DEFAULT_DATA)
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
    audit = sub.add_parser('audit-data', help='Inspect the feature data and split without training.')
    audit.add_argument('--data', type=Path, default=DEFAULT_DATA)
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
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == 'audit-data':
            data = load_dataset(args.data, args.split_seed, args.split_file)
            if args.output:
                args.output.mkdir(parents=True, exist_ok=False)
                data.save_split(args.output)
                finish_manifest(args.output)
            print(json.dumps(data.audit, ensure_ascii=False, indent=2))
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

        data = load_dataset(args.data, args.split_seed, args.split_file)
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
            + data.audit['limitations'][0] + '\n', encoding='utf-8')
        finish_manifest(args.output)
        print(json.dumps({'status': status['status'], 'output': str(args.output.resolve()), 'fusion': status['fusion']}, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, FileNotFoundError, FileExistsError) as error:
        print(f'ERROR: {error}', flush=True)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
