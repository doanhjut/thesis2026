"""
run_active_learning.py
======================
Integration: XAI-Guided Active Learning + Real LightGBM Model

Kết nối active_learner.py với:
  - ransomware_lgbm_1M_final.txt  (model thật)
  - xai_explainer.RansomwareExplainer  (SHAP thật)
  - pe_feature_extractor  (features thật từ PE files)

Chạy:
    # Mode 1: Experiment với EMBER features có sẵn (KHUYÊN DÙNG cho thesis)
    python run_active_learning.py --mode ember --data_dir ./ember_features

    # Mode 2: Experiment synthetic (không cần data, chạy ngay)
    python run_active_learning.py --mode synthetic

    # Mode 3: Scan thư mục PE files thật
    python run_active_learning.py --mode pe_files --pe_dir C:/Windows/System32
"""

import numpy as np
import json
import argparse
from pathlib import Path
from datetime import datetime

# ── Import các module trong cùng thư mục ──────────────────────
import lightgbm as lgb

from xai_explainer import RansomwareExplainer
from active_learner import (
    SHAPUncertaintyEstimator,
    UncertaintyPriorityQueue,
    SampleRecord,
    XAIActiveLearner,
    IncrementalRetrainer,
    ALExperimentRunner,
)

MODEL_PATH = "ransomware_lgbm_1M_final.txt"


# ══════════════════════════════════════════════════════════════
# 1.  REAL SHAP UNCERTAINTY — dùng RansomwareExplainer
# ══════════════════════════════════════════════════════════════

class RealSHAPUncertaintyEstimator(SHAPUncertaintyEstimator):
    """
    Override SHAPUncertaintyEstimator để dùng model + SHAP thật.
    Kế thừa toàn bộ logic tính uncertainty, chỉ thay _compute_real_shap.
    """

    def __init__(self, explainer: RansomwareExplainer):
        super().__init__(model=explainer.model)
        self.explainer = explainer
        print("⚡ RealSHAP Uncertainty Estimator — using actual LightGBM + SHAP")

    def _compute_uncertainty(self, features: np.ndarray) -> dict:
        """Dùng SHAP thật từ RansomwareExplainer."""
        try:
            result = self.explainer.explain_features(features, top_n=20)
            shap_values = np.array(result['shap_values'])
            return self._build_result(features, shap_values)
        except Exception as e:
            # Fallback về simulation nếu SHAP lỗi
            print(f"   ⚠️  Real SHAP error: {e} → fallback")
            return self._compute_simulated_shap(features)


# ══════════════════════════════════════════════════════════════
# 2.  LOAD EMBER FEATURES từ file .npz / .npy
# ══════════════════════════════════════════════════════════════

def load_ember_features(data_dir: str, max_samples: int = 2000):
    """
    Load EMBER feature vectors đã được vectorize sẵn.
    
    Hỗ trợ format:
      - X_train.dat / y_train.dat  (EMBER binary format)
      - features.npy + labels.npy
      - features.npz
    
    Nếu không tìm thấy → tự generate synthetic giống EMBER statistics.
    """
    data_path = Path(data_dir)
    print(f"\n📂 Loading EMBER features from: {data_path}")

    # Option A: EMBER binary format (từ ember.utils)
    try:
        import ember
        X_train, y_train, X_test, y_test = ember.read_vectorized_features(str(data_path))
        # Lọc bỏ unlabeled (y = -1)
        mask_train = y_train != -1
        mask_test  = y_test  != -1
        X = np.vstack([X_train[mask_train], X_test[mask_test]])
        y = np.concatenate([y_train[mask_train], y_test[mask_test]])
        X = X[:max_samples]
        y = y[:max_samples]
        print(f"   ✅ EMBER format: {X.shape}, malware={int(y.sum())}")
        return X, y
    except Exception:
        pass

    # Option B: numpy files
    npy_X = data_path / "features.npy"
    npy_y = data_path / "labels.npy"
    if npy_X.exists() and npy_y.exists():
        X = np.load(str(npy_X))[:max_samples]
        y = np.load(str(npy_y))[:max_samples]
        print(f"   ✅ NPY format: {X.shape}, malware={int(y.sum())}")
        return X, y

    # Option C: npz
    npz_path = data_path / "features.npz"
    if npz_path.exists():
        data = np.load(str(npz_path))
        X = data['X'][:max_samples]
        y = data['y'][:max_samples]
        print(f"   ✅ NPZ format: {X.shape}, malware={int(y.sum())}")
        return X, y

    # Fallback: synthetic với EMBER-like statistics
    print("   ⚠️  No feature files found → generating synthetic EMBER-like data")
    return generate_ember_like_synthetic(max_samples)


def generate_ember_like_synthetic(n: int = 2000, n_features: int = 2381):
    """
    Synthetic data bắt chước thống kê của EMBER:
      - Sparse features (nhiều zeros)
      - ~50% malware
      - Cluster structure
    """
    print(f"   🔧 Generating {n} synthetic samples ({n_features} features)…")
    np.random.seed(42)

    n_mal = n // 2
    n_ben = n - n_mal

    # Benign: mostly zeros, small positive values
    X_ben = np.zeros((n_ben, n_features))
    nonzero_ben = np.random.choice(n_features, 200, replace=False)
    X_ben[:, nonzero_ben] = np.random.exponential(0.1, (n_ben, 200))

    # Malware: elevated values in specific feature subsets
    X_mal = np.zeros((n_mal, n_features))
    nonzero_mal = np.random.choice(n_features, 200, replace=False)
    X_mal[:, nonzero_mal] = np.random.exponential(0.1, (n_mal, 200))
    # Distinctive malware features
    mal_signal = np.random.choice(n_features, 50, replace=False)
    X_mal[:, mal_signal] += np.random.exponential(0.8, (n_mal, 50))

    X = np.vstack([X_ben, X_mal])
    y = np.array([0] * n_ben + [1] * n_mal, dtype=float)

    perm = np.random.permutation(n)
    return X[perm], y[perm]


# ══════════════════════════════════════════════════════════════
# 3.  LOAD PE FILES từ thư mục
# ══════════════════════════════════════════════════════════════

def load_pe_features(pe_dir: str, explainer: RansomwareExplainer,
                     max_files: int = 200):
    """
    Extract features từ PE files thật trong thư mục.
    Dùng pe_feature_extractor qua RansomwareExplainer.
    """
    pe_path = Path(pe_dir)
    exe_files = list(pe_path.glob("*.exe"))[:max_files]

    if not exe_files:
        print(f"   ⚠️  No .exe files in {pe_dir}")
        return None, None

    print(f"   Found {len(exe_files)} .exe files, extracting features…")
    features_list = []
    valid_files   = []

    for f in exe_files:
        try:
            result = explainer.explain_file(str(f), top_n=1)
            if result['success']:
                features_list.append(np.array(result['features']))
                valid_files.append(str(f))
        except Exception as e:
            pass

    if not features_list:
        return None, None

    X = np.vstack(features_list)
    # PE files từ System32 → label = benign (0)
    # Cho experiment: để oracle giả định
    y = np.zeros(len(features_list))

    print(f"   ✅ Extracted {X.shape[0]} samples")
    return X, y


# ══════════════════════════════════════════════════════════════
# 4.  MAIN EXPERIMENT với model thật
# ══════════════════════════════════════════════════════════════

def run_real_experiment(X: np.ndarray, y: np.ndarray,
                        explainer: RansomwareExplainer,
                        budget: int = 20, rounds: int = 8):
    """
    Chạy XAI-AL experiment với model + SHAP thật.
    """
    print("\n" + "="*60)
    print("🔬 XAI-GUIDED AL — REAL MODEL EXPERIMENT")
    print("="*60)
    print(f"   Total samples  : {len(y)}")
    print(f"   Malware        : {int(y.sum())} ({y.mean()*100:.1f}%)")
    print(f"   Features       : {X.shape[1]}")
    print(f"   Budget/round   : {budget}")
    print(f"   Max rounds     : {rounds}")

    # Split: 10% seed, 70% pool, 20% test
    n = len(y)
    n_seed = max(20, int(n * 0.10))
    n_test = int(n * 0.20)

    idx   = np.random.permutation(n)
    X, y  = X[idx], y[idx]

    X_seed, y_seed = X[:n_seed],       y[:n_seed]
    X_pool, y_pool = X[n_seed:-n_test], y[n_seed:-n_test]
    X_test, y_test = X[-n_test:],       y[-n_test:]

    print(f"\n   Seed: {len(y_seed)}  Pool: {len(y_pool)}  Test: {len(y_test)}")

    # ── XAI-AL với SHAP thật ──────────────────────────────────
    learner = XAIActiveLearner(
        model_path       = MODEL_PATH,
        budget_per_round = budget,
        max_rounds       = rounds,
    )
    # Override uncertainty estimator với real SHAP
    learner.uncertainty_estimator = RealSHAPUncertaintyEstimator(explainer)

    learner.initialize_pool(X_pool, X_seed, y_seed)
    xai_history = learner.run_al_loop(X_test, y_test, oracle_labels=y_pool)

    # ── Random sampling baseline ──────────────────────────────
    print("\n" + "="*60)
    print("🎲 RANDOM SAMPLING BASELINE")
    print("="*60)
    runner = ALExperimentRunner(budget_per_round=budget, max_rounds=rounds)
    random_history = runner.run_random_al(
        X_seed, y_seed, X_pool, y_pool, X_test, y_test)

    # ── So sánh ───────────────────────────────────────────────
    comparison = runner.compare_and_report(xai_history, random_history)

    # ── Lưu kết quả ───────────────────────────────────────────
    output = {
        'experiment_time': datetime.now().isoformat(),
        'data_info': {
            'n_total':    n,
            'n_seed':     n_seed,
            'n_pool':     len(y_pool),
            'n_test':     n_test,
            'malware_pct': float(y.mean() * 100),
        },
        'config': {
            'budget_per_round': budget,
            'max_rounds':       rounds,
            'model':            MODEL_PATH,
        },
        'xai_history': [
            {'round': r.round_number, 'n_labeled': r.n_labeled,
             'auc': r.auc_score, 'f1': r.f1_score}
            for r in xai_history
        ],
        'random_history': random_history,
        'comparison': comparison,
    }

    out_path = Path("al_real_experiment_results.json")
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\n💾 Results saved → {out_path}")

    # ── In thesis summary ─────────────────────────────────────
    print_thesis_summary(output)

    return output


def print_thesis_summary(output: dict):
    """In bảng số liệu sẵn sàng cho thesis."""
    print("\n" + "="*60)
    print("📝 THESIS NUMBERS (copy vào Chương 4)")
    print("="*60)

    c = output['comparison']
    print(f"""
┌─────────────────────────────────────────────────────┐
│  Metric                  XAI-AL        Random       │
├─────────────────────────────────────────────────────┤
│  Final AUC           {c['xai_final_auc']:.4f}          {c['random_final_auc']:.4f}       │
│  Labels to 90% AUC   {c['xai_efficiency']:<14}  {c['random_efficiency']:<14} │
│  Label saving        {c['label_saving_pct']:.1f}%                             │
└─────────────────────────────────────────────────────┘

AUC per round:""")

    xai_h = output['xai_history']
    rnd_h = output['random_history']
    mn = min(len(xai_h), len(rnd_h))
    print(f"  {'Round':>5}  {'N_Labeled':>10}  {'XAI-AUC':>9}  {'Rnd-AUC':>9}  {'Δ':>7}")
    print("  " + "─"*46)
    for i in range(mn):
        x  = xai_h[i]
        r  = rnd_h[i]
        d  = x['auc'] - r['auc']
        print(f"  {x['round']:>5}  {x['n_labeled']:>10}  "
              f"{x['auc']:>9.4f}  {r['auc']:>9.4f}  {d:>+7.4f}")


# ══════════════════════════════════════════════════════════════
# 5.  CLI
# ══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="XAI-Guided Active Learning — Integration Runner")
    parser.add_argument("--mode", choices=["synthetic", "ember", "pe_files"],
                        default="synthetic",
                        help="Data source mode")
    parser.add_argument("--data_dir", default=".",
                        help="[ember mode] Directory with EMBER feature files")
    parser.add_argument("--pe_dir",
                        default="C:/Windows/System32",
                        help="[pe_files mode] Directory with .exe files")
    parser.add_argument("--budget", type=int, default=20,
                        help="Samples to label per round")
    parser.add_argument("--rounds", type=int, default=8,
                        help="Max AL rounds")
    parser.add_argument("--max_samples", type=int, default=2000,
                        help="Max samples to load")
    args = parser.parse_args()

    # ── Load model + explainer ────────────────────────────────
    print(f"\n🔧 Loading model: {MODEL_PATH}")
    try:
        explainer = RansomwareExplainer(MODEL_PATH)
    except Exception as e:
        print(f"❌ Could not load model: {e}")
        print("   Make sure ransomware_lgbm_1M_final.txt is in current directory")
        return

    # ── Load data ─────────────────────────────────────────────
    if args.mode == "synthetic":
        print("\n📊 Mode: SYNTHETIC (EMBER-like)")
        X, y = generate_ember_like_synthetic(args.max_samples)

    elif args.mode == "ember":
        X, y = load_ember_features(args.data_dir, args.max_samples)
        if X is None:
            print("❌ Failed to load EMBER features")
            return

    elif args.mode == "pe_files":
        print(f"\n📂 Mode: PE_FILES from {args.pe_dir}")
        X, y = load_pe_features(args.pe_dir, explainer, args.max_samples)
        if X is None:
            print("❌ No PE files found or extraction failed")
            return

    # ── Run experiment ────────────────────────────────────────
    run_real_experiment(X, y, explainer,
                        budget=args.budget,
                        rounds=args.rounds)


if __name__ == "__main__":
    main()