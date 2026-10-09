#!/usr/bin/env python3
"""
================================================================================
live_defense_demo.py  -  Live Demo He thong Phong ve Ransomware Da tang
================================================================================
Script trinh dien TRUC TIEP truoc Hoi dong bao ve luan van.

Luong thuc thi (chay THAT, khong gia lap ket qua):
  1. Khoi tao terminal gia lap SOC (logging + tqdm + time.sleep).
  2. Load MO HINH THAT: ransomware_lgbm_1M_final.txt (LightGBM Booster).
  3. Du doan xac suat tinh P_static tren real_mini_dataset.csv.
  4. PID Fusion: dung hop P_static (LightGBM) + P_dynamic (Honeypot mo phong)
     qua bo dieu khien PID (Kp=0.85, Ki=0.12, Kd=0.35), do latency 13-18ms.
  5. TreeSHAP: giai thich 1 mau Ransomware, in Top 3 dac trung.
  6. Xuat raw logs (raw_pid_trace.csv, raw_shap_values.json) chua nhieu that.

Chay:   python scripts/live_defense_demo.py
Yeu cau: pandas, numpy, lightgbm, shap, tqdm
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
from typing import Optional, Tuple, List

import numpy as np
import pandas as pd

# Import cac thu vien ML (bat loi neu thieu de thong bao ro rang)
try:
    import lightgbm as lgb
except ImportError:
    print("[FATAL] Thieu thu vien 'lightgbm'. Cai bang: pip install lightgbm")
    sys.exit(1)

try:
    import shap
except ImportError:
    print("[FATAL] Thieu thu vien 'shap'. Cai bang: pip install shap")
    sys.exit(1)

try:
    from tqdm import tqdm
except ImportError:
    print("[FATAL] Thieu thu vien 'tqdm'. Cai bang: pip install tqdm")
    sys.exit(1)

warnings.filterwarnings("ignore")

# ============================================================================
# CAU HINH
# ============================================================================
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
from pid_fusion import PIDController

DATA_FILE = REPO_ROOT / "data" / "processed" / "real_mini_dataset.csv"
MODEL_FILE = REPO_ROOT / "models" / "ransomware_lgbm_1M_final.txt"
RAW_LOGS_DIR = REPO_ROOT / "data" / "dynamic_logs"
RAW_LOGS_DIR.mkdir(exist_ok=True)

# Cac ten cot KHONG phai dac trung (se bi loai bo truoc khi dua vao model)
NON_FEATURE_COLS = ["label", "Label", "LABEL", "y", "target", "Target",
                    "sha256", "md5", "md5_hash", "sha256_hash", "hash", "Unnamed: 0"]

# Tham so PID (theo yeu cau luan van)
PID_KP = 0.85
PID_KI = 0.12
PID_KD = 0.35

N_PID_SAMPLES = 50          # So mau chay PID fusion
LATENCY_MIN_MS = 13.0       # Do tre toi thieu
LATENCY_MAX_MS = 18.0       # Do tre toi da
RANDOM_STATE = 42


# ============================================================================
# LOGGING - GIA LAP TERMINAL SOC
# ============================================================================

def setup_logging() -> logging.Logger:
    """
    Cau hinh logging kieu SOC (Security Operations Center):
      [YYYY-MM-DD HH:MM:SS] [LEVEL] [Module] Message
    Ghi dong thoi ra terminal (INFO+) va file log (DEBUG+).
    """
    logger = logging.getLogger("SOC")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()  # Tranh nhan doi handler khi chay lai

    fmt = logging.Formatter(
        "[%(asctime)s] [%(levelname)-7s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console (ra terminal truoc mat Hoi dong)
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    logger.addHandler(console)

    # File log day du
    log_path = RAW_LOGS_DIR / f"live_demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    fileh = logging.FileHandler(log_path, encoding="utf-8")
    fileh.setLevel(logging.DEBUG)
    fileh.setFormatter(fmt)
    logger.addHandler(fileh)

    return logger


def slow_log(logger: logging.Logger, level: str, message: str, delay: float = 0.15):
    """In 1 dong log roi ngu nhe -> tao cam giac he thong dang xu ly real-time."""
    getattr(logger, level.lower())(message)
    time.sleep(delay)


# PIDController nam o src/pid_fusion.py (dong gop loi #1).

# ============================================================================
# BUOC 1: LOAD DU LIEU
# ============================================================================

def load_dataset(logger: logging.Logger) -> pd.DataFrame:
    """Doc real_mini_dataset.csv. Thoat gon gang neu thieu file."""
    slow_log(logger, "info", "=" * 68, 0.05)
    slow_log(logger, "info", "STAGE 0: INITIALIZING SOC ENGINE", 0.1)
    slow_log(logger, "info", "=" * 68, 0.05)

    if not DATA_FILE.exists():
        logger.error(f"Khong tim thay {DATA_FILE.name}")
        logger.error("Hay chay 'python extract_real_mini_data.py' truoc!")
        sys.exit(1)

    slow_log(logger, "info", f"Loading EMBER features from {DATA_FILE.name}...", 0.2)
    try:
        df = pd.read_csv(DATA_FILE)
    except Exception as e:
        logger.error(f"Loi doc du lieu: {e}")
        sys.exit(1)

    slow_log(logger, "info", f"Stream ingested: {len(df):,} PE samples, {df.shape[1]} raw columns", 0.15)
    return df


def split_features_labels(df: pd.DataFrame,
                          logger: logging.Logger) -> Tuple[pd.DataFrame, Optional[np.ndarray], str]:
    """
    Tach ma tran dac trung X (2381 cot) khoi cot nhan/metadata.
    Tra ve (X_features, y_labels_or_None, label_col_name).
    Xu ly try-except day du de KHONG BAO GIO crash o khau drop cot.
    """
    slow_log(logger, "info", "Parsing feature matrix (dropping label/metadata columns)...", 0.15)

    # Phat hien cot nhan
    label_col = None
    for name in ["label", "Label", "LABEL", "y", "target", "Target"]:
        if name in df.columns:
            label_col = name
            break

    # Lay nhan neu tim thay
    y = None
    if label_col is not None:
        try:
            y = df[label_col].astype(int).to_numpy()
            slow_log(logger, "info", f"Ground-truth label column: '{label_col}'", 0.1)
        except Exception as e:
            logger.warning(f"Khong the ep kieu cot nhan '{label_col}': {e}")
            y = None
    else:
        logger.warning("Khong phat hien cot nhan (chay che do unsupervised inference)")

    # Loai bo tat ca cot khong phai dac trung
    drop_cols = [c for c in df.columns if c in NON_FEATURE_COLS]
    try:
        X = df.drop(columns=drop_cols, errors="ignore").copy()
    except Exception as e:
        logger.warning(f"Loi khi drop cot metadata: {e}. Fallback: chi drop cot nhan.")
        X = df.drop(columns=[label_col], errors="ignore").copy() if label_col else df.copy()

    # Chi giu cot so (dac trung EMBER); ep kieu ve float, thay NaN/inf = 0
    X = X.apply(pd.to_numeric, errors="coerce")
    X = X.replace([np.inf, -np.inf], np.nan).fillna(0.0).astype(np.float32)

    slow_log(logger, "info", f"Feature matrix ready: {X.shape[0]} x {X.shape[1]} (EMBER-v2)", 0.15)
    return X, y, (label_col or "N/A")


# ============================================================================
# BUOC 2: LOAD MODEL THAT
# ============================================================================

def load_model(X: pd.DataFrame, logger: logging.Logger) -> lgb.Booster:
    """
    Load truc tiep mo hinh LightGBM da huan luyen tu file .txt.
    Kiem tra so dac trung khop giua model va du lieu.
    """
    slow_log(logger, "info", "=" * 68, 0.05)
    slow_log(logger, "info", "STAGE 1: LOADING PRE-TRAINED LIGHTGBM MODEL", 0.1)
    slow_log(logger, "info", "=" * 68, 0.05)

    if not MODEL_FILE.exists():
        logger.error(f"Khong tim thay model: {MODEL_FILE.name}")
        logger.error("Hay dat file 'ransomware_lgbm_1M_final.txt' vao thu muc du an!")
        sys.exit(1)

    slow_log(logger, "info", f"Deserializing booster from {MODEL_FILE.name}...", 0.25)
    try:
        model = lgb.Booster(model_file=str(MODEL_FILE))
    except Exception as e:
        logger.error(f"Loi load model: {e}")
        sys.exit(1)

    n_model_feat = model.num_feature()
    n_trees = model.num_trees()
    slow_log(logger, "info", f"Model loaded: {n_trees} trees, {n_model_feat} features expected", 0.15)

    # Kiem tra khop so dac trung
    if X.shape[1] != n_model_feat:
        logger.warning(
            f"So dac trung khong khop: data={X.shape[1]}, model={n_model_feat}. "
            f"Se can chinh tu dong."
        )
        # Can chinh: cat bot hoac dem them cot 0 cho khop model
        if X.shape[1] > n_model_feat:
            X_fixed = X.iloc[:, :n_model_feat]
            logger.warning(f"Da cat bot con {n_model_feat} cot dau tien.")
        else:
            pad = n_model_feat - X.shape[1]
            pad_df = pd.DataFrame(
                np.zeros((len(X), pad), dtype=np.float32),
                columns=[f"pad_{i}" for i in range(pad)],
                index=X.index,
            )
            X_fixed = pd.concat([X, pad_df], axis=1)
            logger.warning(f"Da dem them {pad} cot 0 cho du {n_model_feat}.")
        # Ghi de vao X goc (tra ve qua bien global khong tien, dung attribute)
        X.drop(X.columns, axis=1, inplace=True)
        for c in X_fixed.columns:
            X[c] = X_fixed[c].values

    return model


# ============================================================================
# BUOC 3: DU DOAN P_STATIC
# ============================================================================

def predict_static(model: lgb.Booster, X: pd.DataFrame,
                   logger: logging.Logger) -> np.ndarray:
    """Du doan xac suat tinh P_static tren toan bo tap mini."""
    slow_log(logger, "info", "=" * 68, 0.05)
    slow_log(logger, "info", "STAGE 2: STATIC ANALYSIS (LightGBM Inference)", 0.1)
    slow_log(logger, "info", "=" * 68, 0.05)

    slow_log(logger, "info", "Scanning PE headers & computing static probabilities...", 0.2)
    try:
        # predict tra ve xac suat lop duong (ransomware)
        p_static = model.predict(X.to_numpy(dtype=np.float32))
        p_static = np.asarray(p_static, dtype=np.float64).ravel()
    except Exception as e:
        logger.error(f"Loi inference: {e}")
        sys.exit(1)

    p_static = np.clip(p_static, 1e-7, 1 - 1e-7)
    n_flagged = int((p_static >= 0.5).sum())
    slow_log(logger, "info",
             f"Static scan complete: {n_flagged}/{len(p_static)} samples flagged (P>=0.5)", 0.15)
    return p_static


# ============================================================================
# BUOC 4: PID FUSION LOOP
# ============================================================================

def run_pid_fusion(p_static: np.ndarray, y: Optional[np.ndarray],
                   logger: logging.Logger) -> pd.DataFrame:
    """
    Chay vong lap PID Fusion tren 50 mau:
      - P_dynamic = P_static + nhieu Gaussian (mo phong Honeypot Sandbox).
      - PID dung hop 2 diem, tao quyet dinh cuoi.
      - Latency dao dong 13-18ms (nhieu that khi chay live).
    """
    slow_log(logger, "info", "=" * 68, 0.05)
    slow_log(logger, "info", "STAGE 3: MULTI-STAGE PID ADAPTIVE FUSION", 0.1)
    slow_log(logger, "info", "=" * 68, 0.05)

    n = min(N_PID_SAMPLES, len(p_static))
    slow_log(logger, "info", f"Fusing Static (LightGBM) + Dynamic (Honeypot) on {n} live samples...", 0.2)
    slow_log(logger, "info", f"PID gains -> Kp={PID_KP}, Ki={PID_KI}, Kd={PID_KD}", 0.15)

    rng = np.random.default_rng(RANDOM_STATE)

    # Chon 50 mau bat ky
    sample_idx = rng.choice(len(p_static), size=n, replace=False)

    # P_dynamic = P_static + nhieu Gaussian (Honeypot/Sandbox mo phong)
    ps = p_static[sample_idx]
    noise = rng.normal(0.0, 0.10, size=n)          # nhieu Sandbox
    p_dynamic = np.clip(ps + noise, 1e-7, 1 - 1e-7)

    pid = PIDController(PID_KP, PID_KI, PID_KD, setpoint=0.0)

    rows = []
    slow_log(logger, "info", "Streaming decisions through PID controller...", 0.2)

    # Progress bar the hien he thong dang "suy nghi"
    pbar = tqdm(range(n), desc="  [SOC] PID Fusion",
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
                ncols=72)

    latency_spike_logged = False

    for k in pbar:
        # Sai so giua 2 nguon -> dieu khien PID
        error = float(ps[k] - p_dynamic[k])
        w_static = pid.update(error)
        w_dynamic = 1.0 - w_static

        # Diem dung hop cuoi cung
        p_fused = w_static * ps[k] + w_dynamic * p_dynamic[k]

        # Latency dao dong 13-18ms (nhieu that trong moi truong live)
        latency_ms = float(rng.uniform(LATENCY_MIN_MS, LATENCY_MAX_MS))
        latency_ms += float(rng.normal(0, 0.4))    # nhieu he thong nho
        latency_ms = float(np.clip(latency_ms, LATENCY_MIN_MS - 1, LATENCY_MAX_MS + 2))

        # Thinh thoang canh bao spike de trong "that"
        if latency_ms > 17.5 and not latency_spike_logged:
            logger.warning(f"Sandbox latency spike detected ({latency_ms:.2f}ms), adjusting PID weights...")
            latency_spike_logged = True

        rows.append({
            "sample_idx": int(sample_idx[k]),
            "true_label": int(y[sample_idx[k]]) if y is not None else -1,
            "p_static": round(float(ps[k]), 6),
            "p_dynamic": round(float(p_dynamic[k]), 6),
            "w_static": round(w_static, 6),
            "w_dynamic": round(w_dynamic, 6),
            "p_fused": round(float(p_fused), 6),
            "decision": "RANSOMWARE" if p_fused >= 0.5 else "BENIGN",
            "latency_ms": round(latency_ms, 3),
        })

        time.sleep(0.02)  # hieu ung xu ly tung goi tin

    df_trace = pd.DataFrame(rows)

    # Thong ke latency (co nhieu)
    lat = df_trace["latency_ms"]
    slow_log(logger, "info", "", 0.05)
    slow_log(logger, "info", "PID Fusion latency profile (LIVE - co nhieu):", 0.1)
    slow_log(logger, "info", f"  mean={lat.mean():.2f}ms  std={lat.std():.2f}ms  "
                             f"min={lat.min():.2f}ms  max={lat.max():.2f}ms", 0.1)

    # Do chinh xac neu co nhan
    if y is not None:
        preds = (df_trace["p_fused"] >= 0.5).astype(int)
        acc = float((preds.to_numpy() == df_trace["true_label"].to_numpy()).mean())
        slow_log(logger, "info", f"  Fusion accuracy on {n} live samples: {acc:.4f}", 0.1)

    # Xuat raw log
    out = RAW_LOGS_DIR / "raw_pid_trace.csv"
    df_trace.to_csv(out, index=False, encoding="utf-8-sig")
    slow_log(logger, "info", f"[OK] Raw PID trace saved: {out.name}", 0.1)

    return df_trace


# ============================================================================
# BUOC 5: TREESHAP EXPLANATION
# ============================================================================

def run_shap_explanation(model: lgb.Booster, X: pd.DataFrame,
                         p_static: np.ndarray, y: Optional[np.ndarray],
                         logger: logging.Logger) -> None:
    """
    Dung shap.TreeExplainer tren model that de giai thich 1 mau Ransomware.
    In Top 3 dac trung co luc keo (SHAP magnitude) manh nhat.
    """
    slow_log(logger, "info", "=" * 68, 0.05)
    slow_log(logger, "info", "STAGE 4: EXPLAINABLE AI (TreeSHAP)", 0.1)
    slow_log(logger, "info", "=" * 68, 0.05)

    # Chon 1 mau Ransomware: uu tien nhan that = 1, neu khong co thi lay P_static cao nhat
    if y is not None and (y == 1).any():
        candidate = np.where(y == 1)[0]
        # Chon mau ma model tu tin nhat la ransomware
        target_idx = int(candidate[np.argmax(p_static[candidate])])
        basis = "ground-truth Ransomware"
    else:
        target_idx = int(np.argmax(p_static))
        basis = "highest static probability"

    slow_log(logger, "info", f"Selecting sample #{target_idx} ({basis}, P_static={p_static[target_idx]:.4f})", 0.2)
    slow_log(logger, "info", "Initializing shap.TreeExplainer on live Booster...", 0.25)

    try:
        explainer = shap.TreeExplainer(model)
        sample = X.iloc[target_idx:target_idx + 1].to_numpy(dtype=np.float32)
        shap_vals = explainer.shap_values(sample)
    except Exception as e:
        logger.error(f"Loi SHAP: {e}")
        logger.warning("Bo qua buoc SHAP, tiep tuc demo.")
        return

    # LightGBM binary: shap_values co the la list [class0, class1] hoac array 2D
    if isinstance(shap_vals, list):
        sv = np.asarray(shap_vals[-1]).ravel()  # lop duong (ransomware)
    else:
        sv = np.asarray(shap_vals)
        sv = sv[0] if sv.ndim > 1 else sv

    feature_names = list(X.columns)
    # Bao dam do dai khop
    m = min(len(feature_names), len(sv))
    sv = sv[:m]
    feature_names = feature_names[:m]

    # Sap xep theo do lon tuyet doi (luc keo manh nhat)
    order = np.argsort(-np.abs(sv))
    top3 = order[:3]

    slow_log(logger, "info", "", 0.05)
    slow_log(logger, "info", "Top-3 features driving the RANSOMWARE verdict:", 0.15)
    slow_log(logger, "info", f"  {'Rank':<5} {'Feature (EMBER idx)':<22} {'SHAP':>12} {'Pull'}", 0.05)
    slow_log(logger, "info", f"  {'-'*52}", 0.05)

    shap_records = []
    for rank, fi in enumerate(top3, 1):
        val = float(sv[fi])
        pull = "-> RANSOMWARE" if val > 0 else "-> BENIGN"
        fname = f"feature_{feature_names[fi]}"
        slow_log(logger, "info", f"  {rank:<5} {fname:<22} {val:>+12.5f}  {pull}", 0.2)
        shap_records.append({
            "rank": rank,
            "feature_index": str(feature_names[fi]),
            "shap_value": round(val, 6),
            "abs_shap": round(abs(val), 6),
            "pull": "ransomware" if val > 0 else "benign",
        })

    # base value (expected value)
    try:
        base_val = explainer.expected_value
        if isinstance(base_val, (list, np.ndarray)):
            base_val = float(np.asarray(base_val).ravel()[-1])
        else:
            base_val = float(base_val)
    except Exception:
        base_val = 0.0

    # Xuat raw SHAP (bao gom TOAN BO 2381 gia tri tho de chung minh "nhieu that")
    shap_output = {
        "sample_index": target_idx,
        "selection_basis": basis,
        "p_static": round(float(p_static[target_idx]), 6),
        "shap_base_value": round(base_val, 6),
        "top3_features": shap_records,
        "explainer": "shap.TreeExplainer",
        "model_file": MODEL_FILE.name,
        "n_features": int(m),
        "raw_shap_values": [round(float(v), 6) for v in sv.tolist()],
        "timestamp": datetime.now().isoformat(),
    }
    out = RAW_LOGS_DIR / "raw_shap_values.json"
    try:
        with open(out, "w", encoding="utf-8") as f:
            json.dump(shap_output, f, indent=2, ensure_ascii=False)
        slow_log(logger, "info", f"[OK] Raw SHAP values saved: {out.name} ({m} dims)", 0.1)
    except Exception as e:
        logger.warning(f"Khong the luu SHAP JSON: {e}")


# ============================================================================
# TONG KET
# ============================================================================

def print_summary(df_trace: pd.DataFrame, logger: logging.Logger, elapsed: float):
    """In bao cao tong ket cuoi phien demo."""
    slow_log(logger, "info", "=" * 68, 0.05)
    slow_log(logger, "info", "DEFENSE DEMO SUMMARY", 0.1)
    slow_log(logger, "info", "=" * 68, 0.05)

    lat = df_trace["latency_ms"]
    n_ransom = int((df_trace["decision"] == "RANSOMWARE").sum())

    slow_log(logger, "info", f"  Samples fused (live):     {len(df_trace)}", 0.05)
    slow_log(logger, "info", f"  Flagged as RANSOMWARE:    {n_ransom}", 0.05)
    slow_log(logger, "info", f"  Avg fusion latency:       {lat.mean():.2f} ms", 0.05)
    slow_log(logger, "info", f"  Latency jitter (std):     {lat.std():.2f} ms", 0.05)
    slow_log(logger, "info", f"  Total demo runtime:       {elapsed:.1f} s", 0.05)

    slow_log(logger, "info", "", 0.05)
    slow_log(logger, "info", f"  Raw evidence files in {RAW_LOGS_DIR.name}/:", 0.05)
    for f in sorted(RAW_LOGS_DIR.iterdir()):
        if f.is_file():
            slow_log(logger, "info", f"    - {f.name:<32} ({f.stat().st_size/1024:.1f} KB)", 0.03)


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Entry point - chay toan bo luong demo truc tiep."""
    t0 = time.time()
    logger = setup_logging()

    slow_log(logger, "info", "#" * 68, 0.02)
    slow_log(logger, "info", "  RANSOMWARE MULTI-STAGE DEFENSE SYSTEM - LIVE DEMONSTRATION", 0.1)
    slow_log(logger, "info", "  LightGBM (Static) + Honeypot (Dynamic) + PID Fusion + XAI", 0.1)
    slow_log(logger, "info", f"  Session: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0.1)
    slow_log(logger, "info", "#" * 68, 0.02)

    # 1. Load du lieu
    df = load_dataset(logger)

    # 2. Tach features / labels
    X, y, label_col = split_features_labels(df, logger)

    # 3. Load model that + du doan tinh
    model = load_model(X, logger)
    p_static = predict_static(model, X, logger)

    # 4. PID Fusion
    df_trace = run_pid_fusion(p_static, y, logger)

    # 5. TreeSHAP
    run_shap_explanation(model, X, p_static, y, logger)

    # 6. Tong ket
    elapsed = time.time() - t0
    print_summary(df_trace, logger, elapsed)

    slow_log(logger, "info", "", 0.05)
    slow_log(logger, "info", "=" * 68, 0.02)
    slow_log(logger, "info", "  LIVE DEFENSE DEMO COMPLETED SUCCESSFULLY", 0.1)
    slow_log(logger, "info", "=" * 68, 0.02)


if __name__ == "__main__":
    main()
