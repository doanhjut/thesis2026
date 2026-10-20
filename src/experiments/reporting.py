"""Generate figures and thesis tables exclusively from saved measured artifacts."""
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .signals import METHODS

COLORS = ['#747474', '#276DA8', '#AD7B23', '#91619F', '#18846C']


def setup():
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9, 'pdf.fonttype': 42,
                         'axes.spines.top': False, 'axes.spines.right': False})


def save(fig, out, name):
    fig.savefig(out / f'{name}.pdf', bbox_inches='tight')
    fig.savefig(out / f'{name}.png', dpi=180, bbox_inches='tight')
    plt.close(fig)


def tex_escape(text):
    return str(text).replace('_', r'\_').replace('%', r'\%').replace('&', r'\&')


def tex_table(headers, rows, caption):
    columns = 'l' + 'r' * (len(headers) - 1)
    return ('% Generated from measured artifacts; requires booktabs.\n'
            '\\begin{table}[htbp]\n\\centering\n\\small\n'
            f'\\caption{{{tex_escape(caption)}}}\n\\begin{{tabular}}{{{columns}}}\n\\toprule\n' +
            ' & '.join(headers) + r' \\' + '\n\\midrule\n' +
            '\n'.join(' & '.join(map(str, row)) + r' \\' for row in rows) +
            '\n\\bottomrule\n\\end{tabular}\n\\end{table}\n')


def pm(values, scale=1, digits=4):
    a = np.asarray(values) * scale
    return f'{a.mean():.{digits}f}' + (f' $\\pm$ {a.std(ddof=1):.{digits}f}' if len(a) > 1 else ' (n=1)')


def al_report(out):
    setup()
    metrics = pd.read_csv(out / 'metrics.csv')
    config = json.loads((out / 'config.json').read_text())
    summary = json.loads((out / 'summary.json').read_text())
    final = metrics[metrics['round'] == config['rounds']]
    final.groupby('method')[['test_auc', 'test_ap', 'test_fpr', 'test_tpr']].agg(['mean', 'std']).to_csv(out / 'final_summary.csv')
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.5), layout='constrained')
    for ax, metric, title in zip(axes, ['auc', 'ap'], ['ROC-AUC', 'Average precision']):
        for method, color in zip(METHODS, COLORS):
            g = metrics[metrics.method == method].groupby('n_labeled')[f'test_{metric}'].agg(['mean', 'std'])
            x, mean, sd = g.index.to_numpy(), g['mean'].to_numpy(), g['std'].fillna(0).to_numpy()
            ax.plot(x, mean, '.-', label=method, color=color)
            if method in ['Uncertainty', 'XAI_full']:
                ax.fill_between(x, mean - sd, mean + sd, color=color, alpha=.12)
        ax.set(xlabel='Training labels (validation extra)', ylabel=title)
        ax.grid(alpha=.15)
    axes[0].legend(fontsize=7)
    fig.suptitle('Same fixed test; mean ± seed SD (not confidence intervals)')
    save(fig, out, 'al_learning_curves')
    paired = pd.read_csv(out / 'paired_differences.csv')
    selected = paired[(paired.method == 'XAI_full') & (paired.baseline == 'Uncertainty')]
    fig, axes = plt.subplots(1, 2, figsize=(8, 3), layout='constrained')
    for ax, metric, scale, title in zip(axes, ['auc', 'fpr'], [1, 100], ['AUC difference', 'FPR difference (percentage points)']):
        g = selected[selected.metric == metric].sort_values('seed')
        values = g.difference.to_numpy() * scale
        good = values > 0 if metric == 'auc' else values < 0
        ax.bar(g.seed.astype(str), values, color=np.where(good, '#18846C', '#B77253'))
        ax.axhline(0, color='black', lw=.7)
        ax.set(title=title, xlabel='Paired seed')
    save(fig, out, 'al_paired_differences')
    rows = []
    for method in METHODS:
        g = final[final.method == method]
        rows.append([tex_escape(method), pm(g.test_auc), pm(g.test_ap), pm(g.test_fpr, 100, 2), pm(g.test_tpr, 100, 2)])
    (out / 'al_table.tex').write_text(tex_table(['Strategy', 'ROC-AUC', 'AP', r'FPR (\%)', r'TPR (\%)'], rows,
        f'Equal training budget: {summary["final_training_labels"]} labels; mean and seed sample SD.'), encoding='utf-8')
    improvements = {k: int((selected[selected.metric == k].difference * (1 if k != 'fpr' else -1) > 0).sum())
                    for k in ['auc', 'ap', 'fpr']}
    lines = ['# Kết quả Active Learning', '',
             f'Ngân sách cuối: {summary["final_training_labels"]} nhãn huấn luyện; thêm {summary["additional_validation_labels"]} nhãn validation.', '',
             '| Phương pháp | ROC-AUC | AP | FPR (%) | TPR (%) |', '|---|---:|---:|---:|---:|']
    for method in METHODS:
        g = final[final.method == method]
        lines.append('| ' + ' | '.join([method, pm(g.test_auc), pm(g.test_ap), pm(g.test_fpr, 100, 2), pm(g.test_tpr, 100, 2)]) .replace('$\\pm$', '±') + ' |')
    n_models = len(metrics)
    lines += ['', f'XAI_full so với Uncertainty: AUC cao hơn ở {improvements["auc"]}/{summary["n_seeds"]} seed; FPR thấp hơn ở {improvements["fpr"]}/{summary["n_seeds"]} seed.',
              'Ngưỡng chọn trên validation theo TPR mục tiêu; TPR test được đo riêng. Các seed dùng chung test.',
              'Không quy đổi chất lượng ở cùng ngân sách thành số nhãn hay giờ công tiết kiệm.', '',
              f'Dự đoán từng mẫu: predictions.csv.gz; lựa chọn truy vấn: queries.csv; run này đã lưu {n_models} checkpoint model.', '',
              *config['dataset']['limitations']]
    (out / 'REPORT.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def fidelity_report(out):
    setup()
    summary = json.loads((out / 'summary.json').read_text())
    rows = summary['deletion_comparisons']
    pd.DataFrame(rows).to_csv(out / 'deletion_summary.csv', index=False)
    x = np.array([r['k'] for r in rows])
    top = np.array([r['top_shap_auc_drop'] for r in rows])
    ci = np.array([r['top_shap_auc_drop_bootstrap_test_ci95'] for r in rows])
    fig, ax = plt.subplots(figsize=(7, 3.5), layout='constrained')
    # CI bounds need not contain the point estimate for very small bootstrap samples.
    ax.plot(x, top, 'o-', color='#245B97', label='Top-|SHAP|')
    ax.vlines(x, ci[:, 0], ci[:, 1], color='#245B97', lw=1.5, label='95% paired test bootstrap')
    ax.plot(x, [r['random_auc_drop_mean'] for r in rows], 's--', color='#B17A23', label='Random: mean across masks')
    ax.set(xlabel='Selected feature count k', ylabel='ROC-AUC decrease', xticks=x)
    ax.grid(alpha=.15)
    ax.legend(fontsize=8)
    save(fig, out, 'fidelity_deletion')
    table = [[r['k'], f'{r["auc_before"]:.6f}', f'{r["top_shap_auc_after"]:.6f}',
              f'{r["random_auc_after_mean"]:.6f}', f'{r["top_shap_auc_drop"]:.6f}'] for r in rows]
    (out / 'fidelity_table.tex').write_text(tex_table(['k', 'AUC before', 'AUC top-SHAP', 'AUC random', 'Top-SHAP drop'], table,
        'Feature deletion on a fixed model; random control uses the same selected feature count.'), encoding='utf-8')
    attributions = np.load(out / 'shap_values.npz')
    predictions = pd.read_csv(out / 'test_predictions.csv')
    phi = attributions['phi'][0]
    top_ids = np.argsort(np.abs(phi))[-10:][::-1]
    values = np.r_[phi[top_ids], phi.sum() - phi[top_ids].sum()]
    labels = [f'Feature {i}' for i in top_ids] + ['Remaining features']
    fig, ax = plt.subplots(figsize=(7, 4), layout='constrained')
    ax.barh(labels, values, color=np.where(values >= 0, '#087F8C', '#BD5A38'))
    ax.invert_yaxis()
    ax.axvline(0, color='gray', lw=.6)
    ax.set(xlabel='TreeSHAP contribution (raw log-odds)',
           title=f'First saved test row {int(predictions.iloc[0].row_id)}; p={predictions.iloc[0].p_original:.6f}\nBias + contributions = {attributions["raw_scores"][0]:.6f}')
    save(fig, out, 'local_shap_example')
    text = ['# Kết quả Fidelity', '', f'AUC trước che: {summary["baseline_test_roc_auc"]:.6f}.', '',
            '| k | AUC sau top-SHAP | AUC sau random (TB) | AUC giảm top-SHAP | FF thô |', '|---:|---:|---:|---:|---:|']
    for r in rows:
        text.append(f'| {r["k"]} | {r["top_shap_auc_after"]:.6f} | {r["random_auc_after_mean"]:.6f} | {r["top_shap_auc_drop"]:.6f} | {r["top_shap_ff_raw"]:.6f} |')
    text += ['', f'EC = {summary["ec"]}; CF = {summary["cf"]:.6f}. OFS không tổng hợp.',
             'Mô hình này huấn luyện riêng, khác model AL. Khoảng bootstrap có điều kiện trên model cố định.',
             'Che vector không chứng minh tệp PE sau biến đổi hợp lệ; số chiều được chọn bằng nhau không bảo đảm cùng độ lớn biến đổi.', '',
             *summary['limitations']]
    (out / 'REPORT.md').write_text('\n'.join(text) + '\n', encoding='utf-8')


def fusion_report(out):
    setup()
    metrics = pd.read_csv(out / 'fusion_metrics.csv')
    metrics.groupby(['strategy', 'fusion'])[['auc', 'ap', 'fpr', 'tpr', 'test_replay_ms_per_row']].agg(['mean', 'std']).to_csv(out / 'fusion_summary.csv')
    cells = metrics[(metrics.strategy.isin(['Random', 'XAI_full'])) & metrics.fusion.isin(['Fixed_weight', 'PID'])].copy()
    cells['configuration'] = cells.strategy + ' + ' + cells.fusion
    fig, axes = plt.subplots(1, 2, figsize=(9, 4), layout='constrained')
    for ax, metric, scale in zip(axes, ['auc', 'fpr'], [1, 100]):
        g = cells.groupby('configuration')[metric].agg(['mean', 'std'])
        ax.bar(g.index, g['mean'] * scale, yerr=g['std'].fillna(0) * scale, color='#287F85')
        ax.tick_params(axis='x', rotation=25)
        ax.set_ylabel('ROC-AUC' if metric == 'auc' else 'FPR (%)')
    save(fig, out, 'fusion_factorial')
    rows = []
    for (strategy, fusion), g in cells.groupby(['strategy', 'fusion']):
        rows.append([tex_escape(strategy + ' + ' + fusion), pm(g.auc), pm(g.ap), pm(g.fpr, 100, 2), pm(g.tpr, 100, 2)])
    (out / 'fusion_table.tex').write_text(tex_table(['Configuration', 'AUC', 'AP', r'FPR (\%)', r'TPR (\%)'], rows,
        'Paired 2x2 fusion and AL comparison; thresholds selected on validation.'), encoding='utf-8')
    (out / 'REPORT.md').write_text('# Fusion ablation\n\nSee fusion_summary.csv, fusion_table.tex and factorial_2x2.csv. '
        'All rows come from supplied paired observations. See config.json for report provenance, reset and selection rules. '
        'Latency measures offline replay only; all input pairs already have both scores.\n', encoding='utf-8')


def event_pid_report(out):
    """Create thesis-ready tables/figures from the saved event-indexed pilot."""
    setup()
    metrics = pd.read_csv(out / 'fusion_metrics.csv')
    timepoints = pd.read_csv(out / 'timepoint_metrics.csv')
    predictions = pd.read_csv(out / 'event_predictions.csv.gz')
    summary = json.loads((out / 'summary.json').read_text())
    bootstrap = json.loads((out / 'paired_bootstrap_pid_minus_fixed.json').read_text())
    order = ['Static_only', 'Dynamic_only', 'Average_50_50', 'Fixed_weight', 'P', 'PI', 'PID']
    colors = ['#747474', '#276DA8', '#AD7B23', '#91619F', '#18846C', '#B75D69', '#1B4332']

    aggregates = (metrics.groupby('fusion')[['auc', 'ap', 'fpr', 'tpr', 'brier']]
                  .agg(['mean', 'std']).reindex(order))
    aggregates.to_csv(out / 'fusion_summary.csv')
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.5), layout='constrained')
    for ax, metric, title in zip(axes, ['auc', 'ap'], ['ROC-AUC theo số API call', 'Average precision theo số API call']):
        for fusion, color in zip(order, colors):
            group = timepoints[timepoints.fusion == fusion].groupby('event_count')[metric].agg(['mean', 'std'])
            x, mean = group.index.to_numpy(), group['mean'].to_numpy()
            sd = group['std'].fillna(0).to_numpy()
            ax.plot(x, mean, '.-', label=fusion, color=color, lw=1.3)
            if fusion in {'Fixed_weight', 'PID'}:
                ax.fill_between(x, mean - sd, mean + sd, color=color, alpha=.10)
        ax.set(xlabel='Số API call đã quan sát', ylabel=metric.upper(), xticks=sorted(timepoints.event_count.unique()))
        ax.grid(alpha=.15)
    axes[0].legend(fontsize=6.5, ncol=2)
    fig.suptitle('Pilot event-indexed; đường là trung bình 5 outer fold, vùng là ± SD')
    save(fig, out, 'event_pid_trajectory')

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.6), layout='constrained')
    x = np.arange(len(order))
    display_names = ['Static\nonly', 'Dynamic\nonly', 'Average\n50/50',
                     'Fixed\nweight', 'P', 'PI', 'PID']
    for ax, metric, scale, title in zip(
            axes, ['auc', 'fpr'], [1, 100], ['ROC-AUC cuối chuỗi', 'FPR tại ngưỡng validation (%)']):
        means = np.array([metrics.loc[metrics.fusion == fusion, metric].mean() for fusion in order]) * scale
        errors = np.array([metrics.loc[metrics.fusion == fusion, metric].std(ddof=1) for fusion in order]) * scale
        ax.bar(x, means, yerr=errors, color=colors, capsize=2)
        ax.set_xticks(x, display_names, rotation=0)
        ax.tick_params(axis='x', labelsize=8)
        ax.set(title=title, ylabel=metric.upper())
        ax.grid(axis='y', alpha=.15)
    axes[0].set_ylim(.82, 1.02)
    fig.suptitle('Trung bình ± sample SD qua 5 outer fold')
    save(fig, out, 'event_pid_final_metrics')

    rows = []
    for fusion in order:
        group = metrics[metrics.fusion == fusion]
        rows.append([tex_escape(fusion), pm(group.auc), pm(group.ap),
                     pm(group.fpr, 100, 2), pm(group.tpr, 100, 2), pm(group.brier)])
    (out / 'event_pid_table.tex').write_text(tex_table(
        ['Phương pháp', 'ROC-AUC', 'AP', r'FPR (\%)', r'TPR (\%)', 'Brier'], rows,
        'Pilot event-indexed trên các mẫu có metadata tĩnh; trung bình và sample SD qua 5 outer fold.'),
        encoding='utf-8')

    final = (predictions.sort_values(['row_id', 'event_count'])
             .groupby(['fusion', 'row_id'], sort=False).tail(1))
    pid = final[final.fusion == 'PID'].set_index('row_id')
    pi = final[final.fusion == 'PI'].set_index('row_id').loc[pid.index]
    mean_pid_pi = float(np.mean(np.abs(pid.score - pi.score)))
    max_pid_pi = float(np.max(np.abs(pid.score - pi.score)))
    decision_pid_pi = int(np.sum(pid.predicted_label.to_numpy() != pi.predicted_label.to_numpy()))
    effect = bootstrap['metrics']
    win_loss = summary['fold_win_tie_loss_pid_vs_fixed']
    lines = [
        '# Pilot PID theo tiến trình sự kiện', '',
        f"Đã đánh giá {summary['samples']} mẫu có đủ hai kênh; coverage metadata tĩnh "
        f"{summary['static_metadata_coverage'] * 100:.1f}%. Mỗi mẫu có các mốc 5, 10, 15 và 20 API call.", '',
        '| Phương pháp | ROC-AUC | AP | FPR (%) | TPR (%) | Brier |',
        '|---|---:|---:|---:|---:|---:|',
    ]
    for fusion in order:
        group = metrics[metrics.fusion == fusion]
        lines.append('| ' + ' | '.join([
            fusion, pm(group.auc).replace('$\\pm$', '±'), pm(group.ap).replace('$\\pm$', '±'),
            pm(group.fpr, 100, 2).replace('$\\pm$', '±'),
            pm(group.tpr, 100, 2).replace('$\\pm$', '±'),
            pm(group.brier).replace('$\\pm$', '±')]) + ' |')
    lines += [
        '', '## So sánh ghép cặp PID với Fixed', '',
        f"Bootstrap dự đoán out-of-fold, PID trừ Fixed: ΔAUC={effect['auc']['mean']:+.4f} "
        f"(95% CI [{effect['auc']['ci95_low']:+.4f}, {effect['auc']['ci95_high']:+.4f}]); "
        f"ΔAP={effect['ap']['mean']:+.4f} "
        f"(95% CI [{effect['ap']['ci95_low']:+.4f}, {effect['ap']['ci95_high']:+.4f}]).",
        f"ΔFPR={effect['fpr']['mean'] * 100:+.2f} điểm phần trăm "
        f"(95% CI [{effect['fpr']['ci95_low'] * 100:+.2f}, {effect['fpr']['ci95_high'] * 100:+.2f}]); "
        f"ΔTPR={effect['tpr']['mean'] * 100:+.2f} điểm phần trăm "
        f"(95% CI [{effect['tpr']['ci95_low'] * 100:+.2f}, {effect['tpr']['ci95_high'] * 100:+.2f}]).",
        f"PID có AUC cao hơn ở {win_loss['auc']['pid_better_folds']}/5 fold, "
        f"hòa {win_loss['auc']['tied_folds']}/5; FPR tốt hơn ở "
        f"{win_loss['fpr']['pid_better_folds']}/5 fold, hòa {win_loss['fpr']['tied_folds']}/5.",
        '', '## Kiểm tra đóng góp riêng của D', '',
        f"Ở mốc cuối, |score PID - score PI| trung bình là {mean_pid_pi:.6f}, tối đa {max_pid_pi:.6f}; "
        f"số quyết định phân lớp khác nhau là {decision_pid_pi}/{len(pid)}.",
        'Pilot này chưa tách được lợi ích gia tăng của thành phần D. Không dùng nó để tuyên bố PID hoàn chỉnh vượt PI.',
        '', '## Phạm vi kết luận', '',
        'Kết quả hỗ trợ tính khả thi của dung hợp tĩnh–động và cho thấy xu hướng cải thiện ranking của nhóm adaptive fusion. '
        'Khoảng tin cậy PID–Fixed còn cắt qua 0 và FPR biến thiên lớn, nên chưa đủ bằng chứng xác nhận PID giảm cảnh báo nhầm.',
        'Đây là generic Windows malware với trục số sự kiện, không phải benchmark ransomware hay thời gian thực theo giây.',
        '', 'Tệp nguồn: fusion_metrics.csv, event_predictions.csv.gz, timepoint_metrics.csv, '
        'fold_effects_pid_minus_fixed.csv và paired_bootstrap_pid_minus_fixed.json.',
    ]
    (out / 'REPORT.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
