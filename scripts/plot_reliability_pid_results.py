#!/usr/bin/env python3
"""Create reproducible figures from a saved reliability-PID exploratory run."""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


LABELS = {
    'Static_only': 'Static', 'Dynamic_only': 'Dynamic',
    'Average_50_50': 'Average', 'Fixed_weight': 'Fixed',
    'Reliability_P': 'R-P', 'Reliability_PI': 'R-PI',
    'Reliability_PID': 'R-PID family',
    'Reliability_full_PID': 'R-PID (D>0)',
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    args = parser.parse_args()
    run = args.run
    metrics = pd.read_csv(run / 'fold_metrics.csv')
    timepoints = pd.read_csv(run / 'timepoint_oof_metrics.csv')

    methods = ['Static_only', 'Dynamic_only', 'Average_50_50', 'Fixed_weight',
               'Reliability_P', 'Reliability_PI', 'Reliability_PID',
               'Reliability_full_PID']
    colors = ['#6b7280', '#9ca3af', '#2563eb', '#0891b2',
              '#16a34a', '#65a30d', '#f59e0b', '#dc2626']
    summary = metrics.groupby('method').agg(
        auc=('auc', 'mean'), auc_sd=('auc', 'std'),
        fpr=('fpr', 'mean'), fpr_sd=('fpr', 'std')).loc[methods]

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3), constrained_layout=True)
    x = np.arange(len(methods))
    axes[0].bar(x, summary.auc, yerr=summary.auc_sd, color=colors, capsize=2)
    axes[0].set_ylabel('ROC-AUC (mean ± SD across folds)')
    axes[0].set_ylim(.94, 1.0)
    axes[0].grid(axis='y', alpha=.2)
    axes[1].bar(x, summary.fpr * 100, yerr=summary.fpr_sd * 100,
                color=colors, capsize=2)
    axes[1].set_ylabel('FPR at validation-selected target TPR (%)')
    axes[1].grid(axis='y', alpha=.2)
    for axis in axes:
        axis.set_xticks(x, [LABELS[value] for value in methods], rotation=35, ha='right')
    fig.suptitle('Exploratory reliability-aware PID: final-window performance')
    fig.savefig(run / 'reliability_pid_final_metrics.png', dpi=220)
    fig.savefig(run / 'reliability_pid_final_metrics.pdf')
    plt.close(fig)

    selected = ['Static_only', 'Dynamic_only', 'Average_50_50',
                'Fixed_weight', 'Reliability_P', 'Reliability_full_PID']
    fig, axis = plt.subplots(figsize=(7.2, 4.5), constrained_layout=True)
    for method, color in zip(selected, ['#6b7280', '#9ca3af', '#2563eb',
                                        '#0891b2', '#16a34a', '#dc2626']):
        group = timepoints[timepoints.method == method].sort_values('event_count')
        axis.plot(group.event_count, group.auc, label=LABELS[method], color=color,
                  linewidth=2, marker='o', markersize=2.5)
    axis.set_xlabel('Ordered API-event count')
    axis.set_ylabel('Pooled out-of-fold ROC-AUC')
    axis.set_xticks([1, 5, 10, 15, 20])
    axis.grid(alpha=.2)
    axis.legend(ncol=2, fontsize=8)
    axis.set_title('Ranking performance over dense event prefixes')
    fig.savefig(run / 'reliability_pid_event_trajectory.png', dpi=220)
    fig.savefig(run / 'reliability_pid_event_trajectory.pdf')
    plt.close(fig)


if __name__ == '__main__':
    main()
