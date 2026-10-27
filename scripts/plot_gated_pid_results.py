#!/usr/bin/env python3
"""Plot final operating metrics from a saved uncertainty-gated PID run."""
from pathlib import Path
import argparse

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


LABELS = {
    'Average_50_50': 'Average', 'Fixed_weight': 'Fixed',
    'Logistic_stack': 'Stacking', 'Reliability_P': 'R-P',
    'Reliability_PI': 'R-PI', 'Reliability_PID': 'R-PID family',
    'Reliability_full_PID': 'R-PID (D>0)',
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--error-cap', type=float, default=.01)
    args = parser.parse_args()
    data = pd.read_csv(args.run / 'fold_metrics.csv')
    data = data[(np.isclose(data.error_cap, args.error_cap)) & (data.scope == 'end_to_end')]
    methods = ['Average_50_50', 'Fixed_weight', 'Logistic_stack',
               'Reliability_P', 'Reliability_PI', 'Reliability_PID',
               'Reliability_full_PID']
    summary = data.groupby('method').agg(
        fpr=('fpr', 'mean'), fpr_sd=('fpr', 'std'),
        tpr=('tpr', 'mean'), tpr_sd=('tpr', 'std'),
        routed=('routed_fraction', 'mean')).loc[methods]
    x = np.arange(len(methods)); width = .36
    fig, axis = plt.subplots(figsize=(10, 4.8), constrained_layout=True)
    axis.bar(x - width / 2, summary.fpr * 100, width,
             yerr=summary.fpr_sd * 100, capsize=2, label='FPR')
    axis.bar(x + width / 2, summary.tpr * 100, width,
             yerr=summary.tpr_sd * 100, capsize=2, label='TPR')
    axis.set_ylabel('Rate (%) — mean ± SD across outer folds')
    axis.set_xticks(x, [LABELS[value] for value in methods], rotation=30, ha='right')
    axis.set_ylim(0, 105); axis.grid(axis='y', alpha=.2); axis.legend()
    axis.set_title(
        f'Cross-fitted uncertainty gate (development early-error cap {args.error_cap*100:.1f}%, '
        f'mean routed {summary.routed.mean()*100:.1f}%)')
    fig.savefig(args.run / 'gated_pid_operating_metrics.png', dpi=220)
    fig.savefig(args.run / 'gated_pid_operating_metrics.pdf')


if __name__ == '__main__':
    main()
