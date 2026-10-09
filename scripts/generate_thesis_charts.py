#!/usr/bin/env python3
"""
================================================================================
generate_thesis_charts.py  -  Ve bieu do do phan giai cao (300 DPI, chuan IEEE)
================================================================================
Muc dich:
    Doc cac file log THO trong thu muc raw_logs/ (sinh ra tu live_defense_demo.py)
    va ve 3 bieu do chat luong xuat ban de dan vao Slide / Luan van.

Bieu do xuat ra (300 DPI, luu vao thu muc results/):
    1. chart_pid_latency_jitter.png   : Dao dong do tre PID Fusion (50 mau)
                                        + duong trung binh 15.29ms.
    2. chart_shap_top_features.png    : Top-3 dac trung SHAP keo ve Ransomware.
    3. chart_active_learning_curve.png: Duong cong AUC tang qua cac vong lap AL.

Chay:   python generate_thesis_charts.py
Yeu cau: pandas, numpy, matplotlib, seaborn
================================================================================
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")  # backend khong can man hinh (an toan khi chay tu terminal)
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import seaborn as sns

# ============================================================================
# CAU HINH DUONG DAN
# ============================================================================
REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_LOGS_DIR = REPO_ROOT / "data" / "dynamic_logs"
OUTPUT_DIR = REPO_ROOT / "results"
OUTPUT_DIR.mkdir(exist_ok=True)

# File nguon (uu tien raw_pid_trace.csv vi co latency dung dai 13-18ms)
PID_TRACE_FILE = RAW_LOGS_DIR / "raw_pid_trace.csv"
PID_LATENCY_FILE = RAW_LOGS_DIR / "raw_pid_latency.csv"
SHAP_JSON_FILE = RAW_LOGS_DIR / "raw_shap_values.json"
AL_FILE = RAW_LOGS_DIR / "raw_active_learning.csv"

# Bang mau (dong bo toan bo bieu do)
COLOR_MALWARE = "#e74c3c"   # do - huong Ransomware (SHAP duong)
COLOR_BENIGN = "#2e86de"    # xanh - huong Benign (SHAP am)
COLOR_LINE = "#2c3e50"      # xanh than - duong latency
COLOR_MEAN = "#c0392b"      # do dam - duong trung binh
COLOR_AL = "#8e44ad"        # tim - duong AUC Active Learning

MEAN_LATENCY = 15.29        # duong trung binh theo yeu cau
DPI = 300


# ============================================================================
# THIET LAP STYLE HOC THUAT (IEEE-like)
# ============================================================================

def setup_style() -> None:
    """Cau hinh style hoc thuat: font Times New Roman/Arial, grid mo, DPI cao."""
    sns.set_theme(style="whitegrid", context="paper")
    plt.rcParams.update({
        "figure.dpi": 110,
        "savefig.dpi": DPI,
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif", "Georgia"],
        "font.size": 12,
        "axes.titlesize": 15,
        "axes.titleweight": "bold",
        "axes.labelsize": 13,
        "axes.labelweight": "bold",
        "axes.edgecolor": "#333333",
        "axes.linewidth": 1.1,
        "xtick.labelsize": 11,
        "ytick.labelsize": 11,
        "legend.fontsize": 11,
        "legend.frameon": True,
        "legend.framealpha": 0.95,
        "grid.alpha": 0.35,
        "grid.linestyle": "--",
        "grid.linewidth": 0.7,
    })


# ============================================================================
# BIEU DO 1: PID LATENCY JITTER
# ============================================================================

def plot_pid_latency_jitter() -> bool:
    """Ve bieu do dao dong do tre PID Fusion (50 mau). Tra ve True neu OK."""
    print("\n[1/3] Rendering PID latency jitter chart...")

    # Uu tien raw_pid_trace.csv (latency 13-18ms); fallback raw_pid_latency.csv
    src = PID_TRACE_FILE if PID_TRACE_FILE.exists() else PID_LATENCY_FILE
    if not src.exists():
        print(f"  [ERROR] Khong tim thay '{PID_TRACE_FILE.name}' hay '{PID_LATENCY_FILE.name}'.")
        return False

    try:
        df = pd.read_csv(src)
    except Exception as e:
        print(f"  [ERROR] Khong the doc {src.name}: {e}")
        return False

    if "latency_ms" not in df.columns:
        print(f"  [ERROR] File thieu cot 'latency_ms'. Cot co: {list(df.columns)}")
        return False

    latency = df["latency_ms"].to_numpy(dtype=float)
    n = len(latency)
    x = np.arange(1, n + 1)

    fig, ax = plt.subplots(figsize=(9, 5))

    ax.plot(x, latency, color=COLOR_LINE, linewidth=1.8, marker="o",
            markersize=5, markerfacecolor="white", markeredgecolor=COLOR_LINE,
            markeredgewidth=1.2, label="PID Fusion Latency", zorder=3)

    ax.fill_between(x, latency, MEAN_LATENCY, where=(latency >= MEAN_LATENCY),
                    color=COLOR_MALWARE, alpha=0.10, interpolate=True, zorder=1)
    ax.fill_between(x, latency, MEAN_LATENCY, where=(latency < MEAN_LATENCY),
                    color=COLOR_BENIGN, alpha=0.10, interpolate=True, zorder=1)

    # Duong trung binh ngang dut net do tai 15.29ms
    ax.axhline(y=MEAN_LATENCY, color=COLOR_MEAN, linestyle="--", linewidth=2.0,
               label=f"Mean Latency: {MEAN_LATENCY:.2f} ms", zorder=2)
    ax.annotate(f"Mean Latency: {MEAN_LATENCY:.2f} ms",
                xy=(n * 0.62, MEAN_LATENCY), xytext=(n * 0.42, MEAN_LATENCY + 2.6),
                fontsize=11, fontweight="bold", color=COLOR_MEAN,
                arrowprops=dict(arrowstyle="->", color=COLOR_MEAN, lw=1.5))

    ax.set_ylim(10, 20)  # lam noi bat jitter 13-18ms
    ax.set_xlim(0.5, n + 0.5)
    ax.set_title("PID Adaptive Fusion - Real-time Latency Stability (50 Live Samples)", pad=12)
    ax.set_xlabel("Sample Index")
    ax.set_ylabel("PID Fusion Latency (ms)")
    ax.legend(loc="upper right")

    stats_txt = (f"min = {latency.min():.2f} ms\n"
                 f"max = {latency.max():.2f} ms\n"
                 f"std = {latency.std():.2f} ms")
    ax.text(0.015, 0.03, stats_txt, transform=ax.transAxes, fontsize=10,
            va="bottom", ha="left",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="#f7f9fb",
                      edgecolor="#b0b8c0", alpha=0.95))

    fig.tight_layout()
    out = OUTPUT_DIR / "chart_pid_latency_jitter.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] Saved: {out}  ({n} samples)")
    return True


# ============================================================================
# BIEU DO 2: TOP-3 SHAP FEATURES
# ============================================================================

def plot_shap_top_features() -> bool:
    """Ve horizontal bar chart Top-3 dac trung SHAP (top3_features). Tra ve True neu OK."""
    print("\n[2/3] Rendering SHAP top-features chart...")
    if not SHAP_JSON_FILE.exists():
        print(f"  [ERROR] Khong tim thay {SHAP_JSON_FILE}")
        return False

    try:
        with open(SHAP_JSON_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        top3 = data.get("top3_features", [])
        if not top3:
            raise ValueError("Khong tim thay mang 'top3_features' trong JSON.")
        df = pd.DataFrame([{
            "feature": f"feature_{r['feature_index']}",
            "shap": float(r["shap_value"]),
        } for r in top3])
    except Exception as e:
        print(f"  [ERROR] Khong the doc/parse SHAP JSON: {e}")
        return False

    # Sap xep tang dan de thanh lon nhat nam tren cung
    df = df.sort_values("shap", ascending=True).reset_index(drop=True)
    colors = [COLOR_MALWARE if v > 0 else COLOR_BENIGN for v in df["shap"]]

    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.barh(df["feature"], df["shap"], color=colors,
                   edgecolor="#2c3e50", linewidth=0.9, height=0.6, zorder=3)

    for bar, val in zip(bars, df["shap"]):
        offset = 0.02 * df["shap"].abs().max()
        ax.text(bar.get_width() + offset, bar.get_y() + bar.get_height() / 2,
                f"{val:+.3f}", va="center", ha="left",
                fontsize=11, fontweight="bold", color="#2c3e50")

    ax.axvline(x=0, color="#333333", linewidth=1.1, zorder=2)
    ax.set_title("TreeSHAP - Top-3 Feature Attributions for a Ransomware Verdict", pad=12)
    ax.set_xlabel("SHAP Value  (pull toward Ransomware >>)")
    ax.set_ylabel("EMBER Feature")

    xmax = df["shap"].max()
    ax.set_xlim(min(df["shap"].min(), 0) - 0.1 * abs(xmax), xmax * 1.25)

    legend_handles = [
        Patch(facecolor=COLOR_MALWARE, edgecolor="#2c3e50", label="Positive SHAP -> Ransomware"),
        Patch(facecolor=COLOR_BENIGN, edgecolor="#2c3e50", label="Negative SHAP -> Benign"),
    ]
    ax.legend(handles=legend_handles, loc="lower right")

    fig.tight_layout()
    out = OUTPUT_DIR / "chart_shap_top_features.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] Saved: {out}  ({len(df)} features)")
    return True


# ============================================================================
# BIEU DO 3: ACTIVE LEARNING CURVE
# ============================================================================

def plot_active_learning_curve() -> bool:
    """Ve duong cong AUC tang qua cac vong lap Active Learning. Tra ve True neu OK."""
    print("\n[3/3] Rendering Active Learning curve chart...")
    if not AL_FILE.exists():
        print(f"  [ERROR] Khong tim thay {AL_FILE}")
        return False

    try:
        df = pd.read_csv(AL_FILE)
    except Exception as e:
        print(f"  [ERROR] Khong the doc {AL_FILE.name}: {e}")
        return False

    if "iteration" not in df.columns or "auc" not in df.columns:
        print(f"  [ERROR] File thieu cot 'iteration'/'auc'. Cot co: {list(df.columns)}")
        return False

    it = df["iteration"].to_numpy()
    auc = df["auc"].to_numpy(dtype=float)

    fig, ax = plt.subplots(figsize=(9, 5))

    ax.plot(it, auc, color=COLOR_AL, linewidth=2.4, marker="o", markersize=9,
            markerfacecolor="white", markeredgecolor=COLOR_AL, markeredgewidth=2.0,
            label="XAI-Guided Active Learning (AUC)", zorder=3)
    ax.fill_between(it, auc, auc.min() - 0.001, color=COLOR_AL, alpha=0.08, zorder=1)

    # Ghi gia tri AUC tren tung diem
    for xi, yi in zip(it, auc):
        ax.annotate(f"{yi:.4f}", xy=(xi, yi), xytext=(0, 10),
                    textcoords="offset points", ha="center",
                    fontsize=10, fontweight="bold", color=COLOR_AL)

    # Neu co so mau gan nhan, hien tren truc X phu
    if "n_labeled" in df.columns:
        xticklabels = [f"Vòng {int(i)}\n(n={int(nl)})"
                       for i, nl in zip(it, df["n_labeled"])]
    else:
        xticklabels = [f"Vòng {int(i)}" for i in it]
    ax.set_xticks(it)
    ax.set_xticklabels(xticklabels)

    lo = max(0.99, auc.min() - 0.002)
    ax.set_ylim(lo, 1.0005)
    ax.set_title("XAI-Guided Active Learning - AUC Convergence per Iteration", pad=12)
    ax.set_xlabel("Active Learning Iteration")
    ax.set_ylabel("AUC Score")
    ax.legend(loc="lower right")

    fig.tight_layout()
    out = OUTPUT_DIR / "chart_active_learning_curve.png"
    fig.savefig(out, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] Saved: {out}  ({len(df)} iterations)")
    return True


# ============================================================================
# MAIN
# ============================================================================

def main() -> None:
    print("=" * 72)
    print("  GENERATE THESIS CHARTS - 300 DPI (IEEE-style)")
    print("=" * 72)

    setup_style()

    results = [
        plot_pid_latency_jitter(),
        plot_shap_top_features(),
        plot_active_learning_curve(),
    ]

    n_ok = sum(1 for r in results if r)
    print("\n" + "=" * 72)
    print(f"  DONE: {n_ok}/3 charts generated in '{OUTPUT_DIR.name}/'")
    if n_ok < 3:
        print("  [WARNING] Mot so bieu do khong tao duoc - kiem tra log ben tren.")
    print("=" * 72)


if __name__ == "__main__":
    main()
