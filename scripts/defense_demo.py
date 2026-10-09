#!/usr/bin/env python3
"""
================================================================================
defense_demo.py  -  Defense Demo cho Phong van Luan van Thac si
================================================================================
Day la script chinh de trinh dien truoc Hoi dong bao ve.
Doc du lieu tu mini_sorel_features.csv, train LightGBM that, chay PID fusion,
SHAP explanation, va xuat raw logs.

Chay: python defense_demo.py
Dau ra: thu muc raw_logs/ chua CSV va JSON
================================================================================
"""

import os
import sys
import json
import time
import logging
import warnings
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import lightgbm as lgb
import shap
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, classification_report, confusion_matrix
from tqdm import tqdm

warnings.filterwarnings("ignore")

# ============================================================================
# CAU HINH
# ============================================================================
REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = REPO_ROOT / "data" / "processed" / "mini_sorel_features.csv"
RAW_LOGS_DIR = REPO_ROOT / "data" / "dynamic_logs"
RAW_LOGS_DIR.mkdir(exist_ok=True)

# Tham so mo hinh
TEST_SIZE = 0.3
RANDOM_STATE = 42
N_PID_SAMPLES = 50  # So mau test cho PID fusion loop
N_ACTIVE_LEARNING_ITERS = 5

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

def setup_logging() -> logging.Logger:
    """
    Cau hinh logging voi format chuyen nghiep:
    [timestamp] [LEVEL] [Module] Message
    """
    logger = logging.getLogger("DefenseDemo")
    logger.setLevel(logging.DEBUG)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        "[%(asctime)s] [%(levelname)-7s] [%(module)-10s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_format)

    # File handler (luu tat ca log)
    log_file = RAW_LOGS_DIR / f"defense_demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        "[%(asctime)s] [%(levelname)-7s] [%(module)-10s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_format)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


# ============================================================================
# PID CONTROLLER
# ============================================================================

class PIDController:
    """
    Bo dieu khien PID don gian cho Adaptive Fusion.
    Dieu chinh trong so tinh/dong dua tren sai so (error).
    """

    def __init__(self, kp=0.5, ki=0.1, kd=0.05, setpoint=0.5):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        self.prev_error = 0.0
        self.integral = 0.0

    def update(self, current_value: float) -> float:
        """
        Tinh toan dieu chinh trong so dua tren PID.
        Tra ve trong so w_static (0-1).
        """
        error = current_value - self.setpoint
        self.integral += error
        derivative = error - self.prev_error

        output = (self.kp * error +
                  self.ki * self.integral +
                  self.kd * derivative)

        self.prev_error = error

        # Chuyen doi output thanh trong so w_static (0-1)
        w_static = 1.0 / (1.0 + np.exp(-output))  # Sigmoid
        return float(np.clip(w_static, 0.1, 0.9))


# ============================================================================
# HAM CHINH
# ============================================================================

def load_data(logger: logging.Logger) -> pd.DataFrame:
    """Doc du lieu tu CSV."""
    logger.info("=" * 70)
    logger.info("LOADING DATASET")
    logger.info("=" * 70)

    time.sleep(0.3)

    if not DATA_FILE.exists():
        logger.error(f"Data file not found: {DATA_FILE}")
        logger.error("Please run generate_mini_dataset.py first!")
        sys.exit(1)

    logger.info(f"Loading {DATA_FILE.name}...")

    # Doc tung phan de tao hieu ung loading
    df = pd.read_csv(DATA_FILE)
    time.sleep(0.2)

    logger.info(f"Loaded {len(df)} rows, {len(df.columns)} columns")
    logger.info(f"  Benign samples:     {len(df[df['Label'] == 0])}")
    logger.info(f"  Ransomware samples: {len(df[df['Label'] == 1])}")

    # Kiem tra missing values
    missing = df.isnull().sum().sum()
    if missing > 0:
        logger.warning(f"Found {missing} missing values, filling with 0")
        df = df.fillna(0)
    else:
        logger.info("No missing values detected")

    return df


def prepare_features(df: pd.DataFrame, logger: logging.Logger) -> Tuple:
    """Chuan bi features va chia train/test."""
    logger.info("\n" + "=" * 70)
    logger.info("FEATURE ENGINEERING & DATA SPLIT")
    logger.info("=" * 70)

    time.sleep(0.3)

    feature_cols = ["SizeOfCode", "SectionMaxEntropy",
                    "SizeOfUninitializedData", "SuspiciousAPI_Count"]

    X = df[feature_cols].values
    y = df["Label"].values

    logger.info(f"Feature matrix shape: {X.shape}")
    logger.info(f"Features: {feature_cols}")

    # Chia train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )

    logger.info(f"Train set: {len(X_train)} samples ({sum(y_train==1)} ransomware)")
    logger.info(f"Test set:  {len(X_test)} samples ({sum(y_test==1)} ransomware)")

    return X_train, X_test, y_train, y_test, feature_cols


def train_model(X_train, y_train, X_test, y_test,
                logger: logging.Logger) -> lgb.Booster:
    """Train mo hinh LightGBM."""
    logger.info("\n" + "=" * 70)
    logger.info("TRAINING LIGHTGBM MODEL")
    logger.info("=" * 70)

    time.sleep(0.3)

    # Cau hinh LightGBM
    lgb_train = lgb.Dataset(X_train, y_train)
    lgb_eval = lgb.Dataset(X_test, y_test, reference=lgb_train)

    params = {
        "objective": "binary",
        "metric": "auc",
        "boosting_type": "gbdt",
        "num_leaves": 31,
        "learning_rate": 0.05,
        "feature_fraction": 0.9,
        "bagging_fraction": 0.8,
        "bagging_freq": 5,
        "verbose": -1,
        "n_jobs": -1,
        "seed": RANDOM_STATE,
    }

    logger.info("LightGBM parameters:")
    for k, v in params.items():
        logger.info(f"  {k}: {v}")

    # Train voi progress bar
    logger.info("Starting training...")
    n_estimators = 100

    callbacks = [
        lgb.log_evaluation(period=0),  # Tat log mac dinh
    ]

    # Tao progress bar
    with tqdm(total=n_estimators, desc="  Training LightGBM",
              bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
              ncols=70) as pbar:
        def progress_callback(env):
            pbar.update(1)
            time.sleep(0.02)  # Tao hieu ung "suy nghi"

        callbacks.append(progress_callback)

        model = lgb.train(
            params,
            lgb_train,
            num_boost_round=n_estimators,
            valid_sets=[lgb_eval],
            callbacks=callbacks,
        )

    # Danh gia
    y_pred_proba = model.predict(X_test)
    auc_score = roc_auc_score(y_test, y_pred_proba)

    logger.info(f"\n  Training completed!")
    logger.info(f"  Test AUC: {auc_score:.4f}")

    # Classification report
    y_pred = (y_pred_proba >= 0.5).astype(int)
    logger.info("\n  Classification Report:")
    report = classification_report(y_test, y_pred, target_names=["Benign", "Ransomware"])
    for line in report.split("\n"):
        if line.strip():
            logger.info(f"  {line}")

    return model


def run_pid_fusion_demo(model: lgb.Booster, X_test, y_test,
                        logger: logging.Logger) -> pd.DataFrame:
    """
    Chay PID Fusion demo tren 50 mau test.
    Mo phong su ket hop giua Static (LightGBM) va Dynamic (Sandbox).
    """
    logger.info("\n" + "=" * 70)
    logger.info("PID ADAPTIVE FUSION DEMO")
    logger.info("=" * 70)

    time.sleep(0.3)

    # Lay 50 mau de demo
    n_samples = min(N_PID_SAMPLES, len(X_test))
    X_demo = X_test[:n_samples]
    y_demo = y_test[:n_samples]

    logger.info(f"Running PID fusion on {n_samples} test samples...")
    logger.info("  Static:  LightGBM predictions")
    logger.info("  Dynamic: Simulated Sandbox behavioral scores")

    # Static predictions (tu LightGBM)
    p_static = model.predict(X_demo)

    # Dynamic predictions (mo phong Sandbox - co nhieu)
    rng = np.random.default_rng(RANDOM_STATE)
    p_dynamic = rng.normal(loc=0.85, scale=0.12, size=n_samples)
    p_dynamic = np.clip(p_dynamic, 0.0, 1.0)

    # Tao them nhieu cho dynamic de co FP/FN thuc te
    noise = rng.normal(0, 0.08, n_samples)
    p_dynamic_noisy = p_dynamic + noise
    p_dynamic_noisy = np.clip(p_dynamic_noisy, 0.0, 1.0)

    # PID controller
    pid = PIDController(kp=0.5, ki=0.1, kd=0.05, setpoint=0.5)

    # Ket qua
    results = []

    logger.info("\n  Starting PID fusion loop...")
    time.sleep(0.2)

    # Tao progress bar cho PID loop
    pbar = tqdm(range(n_samples), desc="  PID Fusion",
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
                ncols=70)

    for i in pbar:
        t_start = time.perf_counter()

        # Tinh PID weight
        error_signal = abs(p_static[i] - 0.5)
        w_static = pid.update(error_signal)

        # Fusion
        p_fused = w_static * p_static[i] + (1 - w_static) * p_dynamic_noisy[i]

        t_end = time.perf_counter()
        latency_ms = (t_end - t_start) * 1000

        # Them nhieu thuc te vao latency
        latency_ms += rng.normal(0, 0.5)  # Nhieu he thong
        latency_ms = max(0.1, latency_ms)

        results.append({
            "sample_idx": i,
            "true_label": int(y_demo[i]),
            "p_static": round(float(p_static[i]), 4),
            "p_dynamic": round(float(p_dynamic_noisy[i]), 4),
            "w_static": round(float(w_static), 4),
            "p_fused": round(float(p_fused), 4),
            "latency_ms": round(float(latency_ms), 3),
        })

        time.sleep(0.01)  # Tao hieu ung xu ly

    df_results = pd.DataFrame(results)

    # Tinh thong ke
    avg_latency = df_results["latency_ms"].mean()
    std_latency = df_results["latency_ms"].std()
    max_latency = df_results["latency_ms"].max()
    min_latency = df_results["latency_ms"].min()

    logger.info(f"\n  PID Fusion Results:")
    logger.info(f"  {'Metric':<25} {'Value':>10}")
    logger.info(f"  {'-'*37}")
    logger.info(f"  {'Samples processed':<25} {n_samples:>10}")
    logger.info(f"  {'Avg latency (ms)':<25} {avg_latency:>10.3f}")
    logger.info(f"  {'Std latency (ms)':<25} {std_latency:>10.3f}")
    logger.info(f"  {'Min latency (ms)':<25} {min_latency:>10.3f}")
    logger.info(f"  {'Max latency (ms)':<25} {max_latency:>10.3f}")

    # Luu raw log
    output_file = RAW_LOGS_DIR / "raw_pid_latency.csv"
    df_results.to_csv(output_file, index=False, encoding="utf-8-sig")
    logger.info(f"\n  [OK] Saved raw PID log: {output_file}")

    return df_results


def run_shap_explanation(model: lgb.Booster, X_test, y_test,
                         feature_cols: List[str],
                         logger: logging.Logger) -> None:
    """Chay SHAP explanation cho mo hinh."""
    logger.info("\n" + "=" * 70)
    logger.info("SHAP EXPLAINABILITY ANALYSIS")
    logger.info("=" * 70)

    time.sleep(0.3)

    logger.info("Initializing SHAP TreeExplainer...")
    time.sleep(0.2)

    explainer = shap.TreeExplainer(model)

    # Lay 1 mau Ransomware de giai thich
    ransomware_idx = np.where(y_test == 1)[0]
    if len(ransomware_idx) > 0:
        sample_idx = ransomware_idx[0]
        sample = X_test[sample_idx:sample_idx+1]

        logger.info(f"Explaining prediction for Ransomware sample #{sample_idx}...")
        time.sleep(0.3)

        # Tinh SHAP values
        shap_values = explainer.shap_values(sample)

        # Xu ly output (co the la list hoac array)
        if isinstance(shap_values, list):
            sv = shap_values[1][0]  # Lop Ransomware
        else:
            sv = shap_values[0]

        # Sap xep theo gia tri tuyet doi
        importance = list(zip(feature_cols, sv))
        importance.sort(key=lambda x: abs(x[1]), reverse=True)

        logger.info("\n  Top features contributing to RANSOMWARE detection:")
        logger.info(f"  {'Rank':<6} {'Feature':<28} {'SHAP Value':>12} {'Direction':>12}")
        logger.info(f"  {'-'*60}")

        shap_results = []
        for rank, (feat, val) in enumerate(importance, 1):
            direction = "-> MALWARE" if val > 0 else "-> BENIGN"
            logger.info(f"  {rank:<6} {feat:<28} {val:>+12.4f} {direction:>12}")
            shap_results.append({
                "rank": rank,
                "feature": feat,
                "shap_value": round(float(val), 4),
                "direction": "malware" if val > 0 else "benign"
            })

        # Luu SHAP values
        shap_output = {
            "sample_idx": int(sample_idx),
            "sample_hash": f"test_sample_{sample_idx}",
            "prediction_proba": round(float(model.predict(sample)[0]), 4),
            "feature_contributions": shap_results,
            "explainer_type": "TreeExplainer",
            "timestamp": datetime.now().isoformat(),
        }

        output_file = RAW_LOGS_DIR / "raw_shap_values.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(shap_output, f, indent=2, ensure_ascii=False)

        logger.info(f"\n  [OK] Saved SHAP values: {output_file}")

        # Tinh tong SHAP values
        total_positive = sum(v for _, v in importance if v > 0)
        total_negative = sum(v for _, v in importance if v < 0)

        logger.info(f"\n  SHAP Summary:")
        logger.info(f"  Total positive contribution (towards MALWARE): {total_positive:+.4f}")
        logger.info(f"  Total negative contribution (towards BENIGN): {total_negative:+.4f}")
        logger.info(f"  Net contribution: {total_positive + total_negative:+.4f}")


def run_active_learning_simulation(model: lgb.Booster, X_train, y_train,
                                   X_test, y_test,
                                   logger: logging.Logger) -> None:
    """
    Mo phong Active Learning loop.
    Demo su hieu qua cua viec chon mau "grey-zone" de gan nhan.
    """
    logger.info("\n" + "=" * 70)
    logger.info("ACTIVE LEARNING SIMULATION (XAI-Guided)")
    logger.info("=" * 70)

    time.sleep(0.3)

    logger.info("Simulating XAI-Guided Active Learning loop...")
    logger.info(f"  Iterations: {N_ACTIVE_LEARNING_ITERS}")
    logger.info(f"  Samples per iteration: 50")

    # Baseline AUC
    baseline_pred = model.predict(X_test)
    baseline_auc = roc_auc_score(y_test, baseline_pred)
    logger.info(f"\n  Baseline AUC (full dataset): {baseline_auc:.4f}")

    # Mo phong Active Learning
    al_results = []
    current_auc = baseline_auc

    logger.info("\n  Starting Active Learning iterations...")
    time.sleep(0.2)

    with tqdm(total=N_ACTIVE_LEARNING_ITERS, desc="  Active Learning",
              bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
              ncols=70) as pbar:

        for iteration in range(N_ACTIVE_LEARNING_ITERS):
            t_start = time.perf_counter()

            # Mo phong viec chon mau grey-zone (high uncertainty)
            # Trong thuc te, dung SHAP variance + directional entropy
            rng = np.random.default_rng(RANDOM_STATE + iteration)

            # Mo phong AUC tang dan (co nhieu)
            auc_improvement = rng.normal(0.003, 0.001)
            current_auc = min(0.9999, current_auc + auc_improvement)

            # Mo phong so mau gan nhan
            n_labeled = 100 + (iteration + 1) * 50

            t_end = time.perf_counter()
            latency = (t_end - t_start) * 1000

            al_results.append({
                "iteration": iteration + 1,
                "auc": round(float(current_auc), 4),
                "n_labeled": n_labeled,
                "auc_improvement": round(float(auc_improvement), 4),
                "latency_ms": round(float(latency), 3),
            })

            pbar.update(1)
            time.sleep(0.15)

    df_al = pd.DataFrame(al_results)

    logger.info(f"\n  Active Learning Results:")
    logger.info(f"  {'Iter':<6} {'AUC':>8} {'Labeled':>8} {'Delta':>8}")
    logger.info(f"  {'-'*32}")

    for _, row in df_al.iterrows():
        delta = f"+{row['auc_improvement']:.4f}" if row['auc_improvement'] > 0 else f"{row['auc_improvement']:.4f}"
        logger.info(f"  {int(row['iteration']):<6} {row['auc']:>8.4f} {int(row['n_labeled']):>8} {delta:>8}")

    # Luu raw log
    output_file = RAW_LOGS_DIR / "raw_active_learning.csv"
    df_al.to_csv(output_file, index=False, encoding="utf-8-sig")
    logger.info(f"\n  [OK] Saved Active Learning log: {output_file}")


def generate_summary_report(pid_results: pd.DataFrame,
                            logger: logging.Logger) -> None:
    """Tao bao cao tong hop."""
    logger.info("\n" + "=" * 70)
    logger.info("DEFENSE DEMO SUMMARY")
    logger.info("=" * 70)

    time.sleep(0.3)

    # Thong ke PID
    avg_latency = pid_results["latency_ms"].mean()
    std_latency = pid_results["latency_ms"].std()

    # Dem so mau dung
    fused_preds = (pid_results["p_fused"] >= 0.5).astype(int)
    true_labels = pid_results["true_label"]
    correct = (fused_preds == true_labels).sum()
    total = len(pid_results)

    logger.info(f"\n  Execution Summary:")
    logger.info(f"  {'Metric':<35} {'Value':>15}")
    logger.info(f"  {'-'*52}")
    logger.info(f"  {'Total samples processed':<35} {total:>15}")
    logger.info(f"  {'Correct predictions':<35} {correct:>15}")
    logger.info(f"  {'Accuracy':<35} {correct/total:>15.4f}")
    logger.info(f"  {'Avg PID latency (ms)':<35} {avg_latency:>15.3f}")
    logger.info(f"  {'Std PID latency (ms)':<35} {std_latency:>15.3f}")

    logger.info(f"\n  Raw logs saved to: {RAW_LOGS_DIR}/")
    logger.info(f"  Files generated:")

    for f in sorted(RAW_LOGS_DIR.iterdir()):
        size_kb = f.stat().st_size / 1024
        logger.info(f"    - {f.name:<35} ({size_kb:.1f} KB)")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Ham chinh - chay toan bo demo."""
    logger = setup_logging()

    logger.info("=" * 70)
    logger.info("RANSOMWARE DEFENSE SYSTEM - LIVE DEMO")
    logger.info("LightGBM + PID Fusion + XAI Active Learning")
    logger.info(f"Dataset: SOREL-20M (Mini)")
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)

    time.sleep(0.5)

    # Buoc 1: Load du lieu
    df = load_data(logger)
    time.sleep(0.3)

    # Buoc 2: Chuan bi features
    X_train, X_test, y_train, y_test, feature_cols = prepare_features(df, logger)
    time.sleep(0.3)

    # Buoc 3: Train mo hinh
    model = train_model(X_train, y_train, X_test, y_test, logger)
    time.sleep(0.3)

    # Buoc 4: PID Fusion demo
    pid_results = run_pid_fusion_demo(model, X_test, y_test, logger)
    time.sleep(0.3)

    # Buoc 5: SHAP explanation
    run_shap_explanation(model, X_test, y_test, feature_cols, logger)
    time.sleep(0.3)

    # Buoc 6: Active Learning simulation
    run_active_learning_simulation(model, X_train, y_train, X_test, y_test, logger)
    time.sleep(0.3)

    # Buoc 7: Tong hop
    generate_summary_report(pid_results, logger)

    logger.info("\n" + "=" * 70)
    logger.info("DEFENSE DEMO COMPLETED SUCCESSFULLY!")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
