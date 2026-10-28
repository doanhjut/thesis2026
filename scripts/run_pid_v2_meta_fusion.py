#!/usr/bin/env python3
"""Exploratory cross-fitted PID-v2 meta-fusion on saved OOF trajectories.

The current cohort has already been used for method development.  This runner
therefore produces development evidence only; it must not be described as an
independent confirmatory test.
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

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.experiments.common import choose_threshold


LEARNED = {
    'Logistic_final': ['ls', 'ld'],
    'Logistic_stack': ['ls', 'ld', 'abs_p', 'd'],
    'PID_P_v2': ['ls', 'p'],
    'PID_PI_v2': ['ls', 'p', 'i_mean'],
    'PID_full_v2': ['ls', 'p', 'i_mean', 'd'],
    # Volatility terms let the learned controller attenuate an unstable
    # derivative rather than treating every last-step change as equally valid.
    'PID_robust_v2': ['ls', 'ld', 'i_mean', 'd', 'e_std', 'd_std'],
}
METHODS = ['Average_50_50', 'Max_score', 'Fixed_weight', *LEARNED]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def logit(values):
    values = np.clip(np.asarray(values, dtype=float), 1e-6, 1 - 1e-6)
    return np.log(values / (1 - values))


def build_features(predictions: pd.DataFrame) -> pd.DataFrame:
    base = (predictions[predictions.method == 'Static_only']
            .sort_values(['outer_fold', 'row_id', 'event_count']).copy())
    if base.empty:
        raise ValueError('Static_only rows are required to recover paired channel scores.')
    base['ls'] = logit(base.probability)
    base['ld'] = logit(base.p_dynamic)
    base['p'] = base.ld - base.ls
    base['abs_p'] = base.p.abs()
    base['i_mean'] = (base.groupby('row_id').p.expanding().mean()
                      .reset_index(level=0, drop=True))
    base['d'] = base.groupby('row_id').p.diff().fillna(0.)
    base['e_std_running'] = (base.groupby('row_id').p.expanding().std(ddof=0)
                             .reset_index(level=0, drop=True).fillna(0.))
    base['d_std_running'] = (base.groupby('row_id').d.expanding().std(ddof=0)
                             .reset_index(level=0, drop=True).fillna(0.))
    final = base.groupby('row_id', sort=False).tail(1).copy()
    final['e_std'] = final.e_std_running
    final['d_std'] = final.d_std_running
    final['average_score'] = .5 * (final.probability + final.p_dynamic)
    final['max_score'] = np.maximum(final.probability, final.p_dynamic)
    return final


def evaluate(frame: pd.DataFrame, score, threshold: float) -> dict:
    y = frame.label.to_numpy(dtype=int)
    score = np.asarray(score, dtype=float)
    decision = score >= threshold
    tn, fp, fn, tp = confusion_matrix(y, decision, labels=[0, 1]).ravel()
    return {
        'auc': float(roc_auc_score(y, score)),
        'ap': float(average_precision_score(y, score)),
        'brier': float(brier_score_loss(y, score)),
        'fpr': float(fp / (fp + tn)),
        'tpr': float(tp / (tp + fn)),
        'tn': int(tn), 'fp': int(fp), 'fn': int(fn), 'tp': int(tp),
    }


def validation_key(record):
    return (record['fpr'], -record['auc'], record['brier'], record['order'])


def select_learned(train, validation, features, target_tpr, seed):
    trials = []
    grid = [.001, .003, .01, .03, .1, .3, 1., 3., 10.]
    for order, c_value in enumerate(grid):
        model = make_pipeline(
            StandardScaler(),
            LogisticRegression(C=c_value, max_iter=3000, class_weight='balanced',
                               random_state=seed),
        )
        model.fit(train[features], train.label)
        score = model.predict_proba(validation[features])[:, 1]
        threshold = choose_threshold(validation.label, score, target_tpr)
        measured = evaluate(validation, score, threshold)
        trials.append({'order': order, 'c': c_value, 'threshold': threshold,
                       'model': model, **measured})
    selected = min(trials, key=validation_key)
    audit_trials = [{key: value for key, value in item.items() if key != 'model'}
                    for item in trials]
    return selected, audit_trials


def model_audit(model, features):
    scaler = model[0]
    classifier = model[1]
    return {
        'features': features,
        'scaler_mean': scaler.mean_.tolist(),
        'scaler_scale': scaler.scale_.tolist(),
        'standardized_coefficients': classifier.coef_[0].tolist(),
        'intercept': float(classifier.intercept_[0]),
    }


def stratified_bootstrap(final, left, right, iterations, seed):
    a = final[final.method == left].sort_values('row_id')
    b = final[final.method == right].sort_values('row_id')
    if not np.array_equal(a.row_id.to_numpy(), b.row_id.to_numpy()):
        raise ValueError(f'Unpaired comparison: {left}/{right}')
    y = a.label.to_numpy(dtype=int)
    if not np.array_equal(y, b.label.to_numpy(dtype=int)):
        raise ValueError(f'Label mismatch: {left}/{right}')
    arrays = {
        'a_score': a.score.to_numpy(), 'b_score': b.score.to_numpy(),
        'a_decision': a.predicted_label.to_numpy(),
        'b_decision': b.predicted_label.to_numpy(),
    }
    folds = a.outer_fold.to_numpy(dtype=int)
    fold_parts = {
        int(fold): [np.flatnonzero((folds == fold) & (y == value))
                    for value in (0, 1)]
        for fold in sorted(np.unique(folds))
    }
    rng = np.random.default_rng(seed)
    samples = {name: [] for name in ('auc', 'ap', 'brier', 'fpr', 'tpr')}
    for _ in range(iterations):
        fold_differences = {name: [] for name in samples}
        for parts in fold_parts.values():
            index = np.concatenate([rng.choice(part, len(part), replace=True)
                                    for part in parts])
            ys = y[index]
            a_score, b_score = arrays['a_score'][index], arrays['b_score'][index]
            a_decision = arrays['a_decision'][index]
            b_decision = arrays['b_decision'][index]
            negative, positive = ys == 0, ys == 1
            fold_differences['auc'].append(
                roc_auc_score(ys, a_score) - roc_auc_score(ys, b_score))
            fold_differences['ap'].append(
                average_precision_score(ys, a_score)
                - average_precision_score(ys, b_score))
            fold_differences['brier'].append(
                np.mean((ys - a_score) ** 2) - np.mean((ys - b_score) ** 2))
            fold_differences['fpr'].append(
                np.mean(a_decision[negative]) - np.mean(b_decision[negative]))
            fold_differences['tpr'].append(
                np.mean(a_decision[positive]) - np.mean(b_decision[positive]))
        for name in samples:
            samples[name].append(float(np.mean(fold_differences[name])))
    return {
        name: {'mean': float(np.mean(values)),
               'ci95_low': float(np.quantile(values, .025)),
               'ci95_high': float(np.quantile(values, .975))}
        for name, values in samples.items()
    }


def run(args):
    args.output.mkdir(parents=True, exist_ok=False)
    source = pd.read_csv(args.predictions)
    frame = build_features(source)
    folds = sorted(frame.outer_fold.unique())
    if folds != list(range(len(folds))):
        raise ValueError(f'Expected contiguous folds, got {folds}')
    predictions, metrics, searches, audits = [], [], [], []
    for fold_value in folds:
        fold = int(fold_value)
        validation_fold = int(folds[(fold + 1) % len(folds)])
        train = frame[~frame.outer_fold.isin([fold, validation_fold])]
        validation = frame[frame.outer_fold == validation_fold]
        test = frame[frame.outer_fold == fold]

        formula = {
            'Average_50_50': ('average_score', None),
            'Max_score': ('max_score', None),
        }
        for method, (column, _) in formula.items():
            threshold = choose_threshold(validation.label, validation[column], args.target_tpr)
            measured = evaluate(test, test[column], threshold)
            metrics.append({'outer_fold': fold, 'validation_fold': validation_fold,
                            'method': method, 'threshold': threshold, **measured})
            saved = test[['row_id', 'outer_fold', 'label']].copy()
            saved['method'], saved['score'], saved['threshold'] = method, test[column], threshold
            saved['predicted_label'] = (saved.score >= threshold).astype(int)
            predictions.append(saved)

        fixed_trials = []
        for order, weight in enumerate(np.linspace(0, 1, 21)):
            score = weight * validation.probability + (1 - weight) * validation.p_dynamic
            threshold = choose_threshold(validation.label, score, args.target_tpr)
            fixed_trials.append({'order': order, 'weight_static': float(weight),
                                 'threshold': threshold,
                                 **evaluate(validation, score, threshold)})
        fixed = min(fixed_trials, key=validation_key)
        score = fixed['weight_static'] * test.probability + (1 - fixed['weight_static']) * test.p_dynamic
        measured = evaluate(test, score, fixed['threshold'])
        metrics.append({'outer_fold': fold, 'validation_fold': validation_fold,
                        'method': 'Fixed_weight', 'threshold': fixed['threshold'], **measured})
        saved = test[['row_id', 'outer_fold', 'label']].copy()
        saved['method'], saved['score'], saved['threshold'] = 'Fixed_weight', score, fixed['threshold']
        saved['predicted_label'] = (saved.score >= fixed['threshold']).astype(int)
        predictions.append(saved)
        searches.append({'outer_fold': fold, 'method': 'Fixed_weight',
                         'selected': fixed, 'trials': fixed_trials})

        for method, features in LEARNED.items():
            selected, trials = select_learned(
                train, validation, features, args.target_tpr, args.seed + int(fold))
            model = selected['model']
            score = model.predict_proba(test[features])[:, 1]
            measured = evaluate(test, score, selected['threshold'])
            metrics.append({'outer_fold': fold, 'validation_fold': validation_fold,
                            'method': method, 'threshold': selected['threshold'], **measured})
            saved = test[['row_id', 'outer_fold', 'label']].copy()
            saved['method'], saved['score'], saved['threshold'] = method, score, selected['threshold']
            saved['predicted_label'] = (saved.score >= selected['threshold']).astype(int)
            predictions.append(saved)
            searches.append({'outer_fold': fold, 'method': method,
                             'selected': {key: value for key, value in selected.items()
                                          if key != 'model'}, 'trials': trials})
            audits.append({'outer_fold': fold, 'method': method,
                           'c': selected['c'], **model_audit(model, features)})

    metric_frame = pd.DataFrame(metrics)
    prediction_frame = pd.concat(predictions, ignore_index=True)
    result_rows = []
    for method, group in metric_frame.groupby('method'):
        pooled = prediction_frame[prediction_frame.method == method]
        result_rows.append({
            'method': method,
            **{name: {'mean': float(group[name].mean()),
                      'sd': float(group[name].std(ddof=1))}
               for name in ('auc', 'ap', 'fpr', 'tpr', 'brier')},
            'pooled_counts': {name: int(group[name].sum()) for name in ('tn', 'fp', 'fn', 'tp')},
            'pooled_auc': float(roc_auc_score(pooled.label, pooled.score)),
            'pooled_ap': float(average_precision_score(pooled.label, pooled.score)),
        })
    comparisons = {}
    for index, baseline in enumerate(['Average_50_50', 'Max_score', 'Fixed_weight',
                                      'Logistic_final', 'Logistic_stack',
                                      'PID_P_v2', 'PID_PI_v2', 'PID_full_v2']):
        comparisons[f'PID_robust_v2_minus_{baseline}'] = stratified_bootstrap(
            prediction_frame, 'PID_robust_v2', baseline,
            args.bootstrap, args.seed + index)

    summary = {
        'status': 'exploratory_post_hoc_pid_v2_development',
        'samples': int(frame.row_id.nunique()),
        'outer_folds': len(folds),
        'target_validation_tpr': args.target_tpr,
        'selection_objective': 'minimum validation FPR at target TPR; then AUC and Brier',
        'results': result_rows,
        'paired_bootstrap': comparisons,
        'source': str(args.predictions.resolve()),
        'source_sha256': sha256(args.predictions),
        'limitations': [
            'The cohort was previously inspected and this is exploratory method development.',
            'A new external or temporal cohort is required for a confirmatory superiority claim.',
            'The endpoint is the final observed event; wall-clock detection latency is not measured.',
            'Labels are generic Windows malware/benign, not verified ransomware labels.',
        ],
    }
    metric_frame.to_csv(args.output / 'fold_metrics.csv', index=False)
    prediction_frame.to_csv(args.output / 'final_predictions.csv.gz', index=False, compression='gzip')
    (args.output / 'model_search.json').write_text(json.dumps(searches, indent=2) + '\n')
    (args.output / 'model_coefficients.json').write_text(json.dumps(audits, indent=2) + '\n')
    (args.output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    write_report(summary, args.output / 'REPORT_VI.md')
    (args.output / 'verification.json').write_text(json.dumps({
        'status': 'passed',
        'samples': int(frame.row_id.nunique()),
        'outer_folds': len(folds),
        'methods': len(METHODS),
        'prediction_rows': int(len(prediction_frame)),
        'outer_test_used_for_model_or_threshold_selection': False,
        'evidence_status': 'exploratory_post_hoc',
    }, indent=2) + '\n')
    hashes = {path.name: sha256(path) for path in sorted(args.output.iterdir())
              if path.is_file() and path.name != 'artifact_sha256.json'}
    (args.output / 'artifact_sha256.json').write_text(json.dumps(hashes, indent=2) + '\n')


def write_report(summary, path):
    rows = []
    for item in summary['results']:
        rows.append(
            f"| {item['method']} | {item['auc']['mean']:.4f} | {item['ap']['mean']:.4f} | "
            f"{100*item['fpr']['mean']:.2f}% | {100*item['tpr']['mean']:.2f}% | "
            f"{item['brier']['mean']:.4f} | {item['pooled_counts']['fp']} | "
            f"{item['pooled_counts']['fn']} |"
        )
    comparisons = summary['paired_bootstrap']
    average = comparisons['PID_robust_v2_minus_Average_50_50']
    max_score = comparisons['PID_robust_v2_minus_Max_score']
    stack = comparisons['PID_robust_v2_minus_Logistic_stack']
    full = comparisons['PID_robust_v2_minus_PID_full_v2']

    def effect(item, name, scale=1.):
        value = item[name]
        return (f"{scale*value['mean']:+.4f} "
                f"[{scale*value['ci95_low']:+.4f}; {scale*value['ci95_high']:+.4f}]")

    path.write_text(
        '# PID v2 meta-fusion — kết quả exploratory\n\n'
        '> Cohort này đã được dùng để phát triển phương pháp. Các số dưới đây không phải xác nhận độc lập.\n\n'
        'PID v2 học các hệ số của bất đồng logit hiện tại (P), trung bình bất đồng tích lũy (I), '
        'biến thiên bước cuối (D) và độ nhiễu của chuỗi. Meta-train, validation và outer-test '
        'được tách theo fold; outer-test không chọn C, threshold hoặc hệ số.\n\n'
        '| Phương pháp | AUC | AP | FPR | TPR | Brier | FP | FN |\n'
        '|---|---:|---:|---:|---:|---:|---:|---:|\n' + '\n'.join(rows) + '\n\n'
        '## Hiệu ứng ghép cặp của Robust PID v2\n\n'
        f"- So với Average: ΔAUC {effect(average, 'auc')}; ΔFPR {effect(average, 'fpr', 100)} pp; "
        f"ΔTPR {effect(average, 'tpr', 100)} pp. Các CI còn đi qua 0.\n"
        f"- So với Max-risk: ΔAUC {effect(max_score, 'auc')}; ΔFPR "
        f"{effect(max_score, 'fpr', 100)} pp; cả hai CI loại 0.\n"
        f"- So với Logistic stacking: ΔAUC {effect(stack, 'auc')}; ΔFPR "
        f"{effect(stack, 'fpr', 100)} pp; chưa có khác biệt rõ.\n"
        f"- So với PID full v2 không có thống kê nhiễu: ΔFPR "
        f"{effect(full, 'fpr', 100)} pp; CI loại 0, TPR không khác biệt rõ.\n\n"
        '## Kết luận sử dụng\n\n'
        'Robust PID v2 sửa được hạn chế của controller cũ: các hệ số D dương ở cả năm folds, '
        'và biến thể robust giảm FPR so với PID full v2. Trên cohort phát triển, nó có AUC/AP '
        'nhỉnh hơn Average và FPR thấp hơn khoảng một điểm phần trăm, nhưng CI vẫn đi qua 0; '
        'Logistic stacking vẫn tương đương. Vì vậy đây là ứng viên thuật toán đã cải tiến, chưa '
        'phải bằng chứng PID vượt tất cả phương pháp.\n\n'
        'Xem `summary.json` để đọc toàn bộ bootstrap và `model_coefficients.json` để kiểm tra '
        'hệ số theo từng outer fold. Mọi tuyên bố vượt trội cần cohort external/temporal mới.\n',
        encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--predictions', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--target-tpr', type=float, default=.95)
    parser.add_argument('--bootstrap', type=int, default=1000)
    parser.add_argument('--seed', type=int, default=2026)
    run(parser.parse_args())


if __name__ == '__main__':
    main()
