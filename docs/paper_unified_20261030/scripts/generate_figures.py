#!/usr/bin/env python3
"""Regenerate aggregate manuscript figures from the locked readiness report.

These plots intentionally omit uncertainty bars because this writing checkout
contains aggregate report values rather than the named fold-level artifacts.
Submission figures must be regenerated from synchronized source artifacts.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "figures"
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.size": 9,
        "axes.labelsize": 9,
        "axes.titlesize": 10,
        "legend.fontsize": 8,
        "figure.dpi": 180,
        "savefig.bbox": "tight",
    }
)


def save(fig, stem):
    fig.savefig(OUT / f"{stem}.pdf")
    fig.savefig(OUT / f"{stem}.png", dpi=220)
    plt.close(fig)


def fusion_summary():
    methods = ["Average", "Max-risk", "Fixed", "Stacking", "P", "PI", "PID"]
    auc = np.array([0.9840, 0.9779, 0.9821, 0.9819, 0.9827, 0.9827, 0.9828])
    fpr = np.array([14.70, 16.63, 12.45, 14.91, 11.16, 11.48, 11.59])
    brier = np.array([0.0450, 0.0604, 0.0487, 0.0454, 0.0456, 0.0456, 0.0455])
    colors = ["#718096", "#a0aec0", "#4a5568", "#805ad5", "#2b6cb0", "#3182ce", "#63b3ed"]
    x = np.arange(len(methods))
    fig, axes = plt.subplots(1, 3, figsize=(10.2, 3.0))
    for ax, values, title, ylim in [
        (axes[0], auc, "ROC--AUC (higher is better)", (0.976, 0.985)),
        (axes[1], fpr, "FPR, % (lower is better)", (10, 17.5)),
        (axes[2], brier, "Brier (lower is better)", (0.043, 0.062)),
    ]:
        ax.bar(x, values, color=colors, edgecolor="black", linewidth=0.35)
        ax.set_title(title)
        ax.set_ylim(*ylim)
        ax.set_xticks(x)
        ax.set_xticklabels(methods, rotation=42, ha="right")
        ax.grid(axis="y", alpha=0.25, linewidth=0.5)
    fig.tight_layout(w_pad=1.4)
    save(fig, "fusion_summary")


def al_summary():
    policies = ["Random", "Uncertainty", "U+H", "U+V", "XAI-full"]
    roc = [0.928777, 0.931272, 0.933026, 0.930377, 0.932202]
    ap = [0.868350, 0.881934, 0.883336, 0.880164, 0.881638]
    labels = [584, 520, 508, 488, 492]
    x = np.arange(len(policies))
    width = 0.36
    fig, axes = plt.subplots(1, 2, figsize=(8.7, 3.15))
    axes[0].bar(x - width / 2, roc, width, label="ROC-AULC", color="#2b6cb0")
    axes[0].bar(x + width / 2, ap, width, label="AP-AULC", color="#68d391")
    axes[0].set_ylim(0.84, 0.94)
    axes[0].set_ylabel("Normalized AULC")
    axes[0].legend(frameon=False, ncol=2)
    axes[1].bar(x, labels, color=["#a0aec0", "#718096", "#2b6cb0", "#38a169", "#805ad5"])
    axes[1].set_ylim(450, 610)
    axes[1].set_ylabel("Training labels to target")
    for ax in axes:
        ax.set_xticks(x)
        ax.set_xticklabels(policies, rotation=25, ha="right")
        ax.grid(axis="y", alpha=0.25, linewidth=0.5)
    fig.tight_layout()
    save(fig, "al_summary")


def deletion_summary():
    k = np.array([10, 25, 50])
    mean_top = [0.047817, 0.135853, 0.306729]
    mean_random = [0.000200, 0.000530, 0.000979]
    median_top = [0.053483, 0.125180, 0.300777]
    median_random = [0.000094, 0.000326, 0.000658]
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.0), sharey=True)
    for ax, top, random, title in [
        (axes[0], mean_top, mean_random, "Training-mean replacement"),
        (axes[1], median_top, median_random, "Training-median replacement"),
    ]:
        ax.plot(k, top, marker="o", linewidth=2, color="#c53030", label="Top-|SHAP|")
        ax.plot(k, random, marker="s", linewidth=2, color="#2b6cb0", label="Random")
        ax.set_title(title)
        ax.set_xlabel("Coordinates replaced (k)")
        ax.set_xticks(k)
        ax.grid(alpha=0.25, linewidth=0.5)
    axes[0].set_ylabel("ROC--AUC decrease")
    axes[0].legend(frameon=False)
    fig.tight_layout()
    save(fig, "fidelity_deletion_confirmatory")


def stability_summary():
    metrics = ["Spearman", "Jaccard-10", "Jaccard-25", "Jaccard-50"]
    within = [0.6144, 0.6221, 0.5398, 0.4901]
    across = [0.5512, 0.4416, 0.3073, 0.3020]
    x = np.arange(len(metrics))
    width = 0.36
    fig, ax = plt.subplots(figsize=(5.8, 3.1))
    ax.bar(x - width / 2, within, width, color="#2b6cb0", label="Seeds, same fold")
    ax.bar(x + width / 2, across, width, color="#ed8936", label="Different folds")
    ax.set_ylim(0, 0.7)
    ax.set_ylabel("Agreement")
    ax.set_xticks(x)
    ax.set_xticklabels(metrics, rotation=18, ha="right")
    ax.grid(axis="y", alpha=0.25, linewidth=0.5)
    ax.legend(frameon=False)
    fig.tight_layout()
    save(fig, "shap_stability_confirmatory")


if __name__ == "__main__":
    fusion_summary()
    al_summary()
    deletion_summary()
    stability_summary()
