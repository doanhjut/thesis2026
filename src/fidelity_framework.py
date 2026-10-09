"""
xai_fidelity.py
================
XAI Fidelity Evaluation Framework
NOVEL CONTRIBUTION #3 — Master's Thesis

ĐỊNH NGHĨA:
  Fidelity = mức độ explanation phản ánh đúng lý do thật sự
             mà model dùng để ra quyết định.

  Câu hỏi: "SHAP explanation của chúng ta có đáng tin không?"

3 METRICS CHÍNH:

  1. Feature Faithfulness (FF)
     Xóa top-K features SHAP claim là quan trọng → AUC phải giảm
     FF cao = xóa features đó thực sự hurt model → SHAP đúng

  2. Explanation Consistency (EC)
     Thêm nhỏ nhiễu vào input → SHAP explanation có ổn định không?
     EC cao = explanation robust, không bị flip bởi noise nhỏ

  3. Contrastive Fidelity (CF)
     Sample malware vs sample benign gần nhất →
     SHAP phải highlight đúng features phân biệt 2 sample
     CF cao = explanation discriminative, không explain noise

  OVERALL FIDELITY = weighted average(FF, EC, CF)

NOVEL ASPECTS:
  - Lần đầu tiên áp dụng fidelity evaluation cho PE binary features
  - PE-aware: handle correlated features (không naive removal)
  - Multi-stage: evaluate fidelity cho từng stage riêng biệt
  - Security-aware: weight recall cao hơn precision (miss malware = costly)

CHẠY:
  python xai_fidelity.py --quick        # test nhanh ~3 phút
  python xai_fidelity.py --full         # full evaluation ~15 phút
  python xai_fidelity.py --multistage   # evaluate từng stage
"""

import numpy as np
import json
import warnings
import argparse
from pathlib import Path
from datetime import datetime
from sklearn.metrics import roc_auc_score, f1_score
from sklearn.neighbors import NearestNeighbors
import lightgbm as lgb

warnings.filterwarnings('ignore')

try:
    import shap as shap_lib
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    print("⚠️  shap not available")

MODEL_PATH    = Path("../ransomware_lgbm_1M_final.txt")
EMBER_DIR     = Path("../../ember2018")
N_FEATURES    = 2381


# ══════════════════════════════════════════════════════════════
# 1. DATA LOADER
# ══════════════════════════════════════════════════════════════

def load_ember_sample(n: int = 5000, seed: int = 42) -> tuple:
    """Load n samples từ EMBER test set."""
    print(f"📂 Loading {n} EMBER samples...")
    Xp = EMBER_DIR / "X_test.dat"
    yp = EMBER_DIR / "y_test.dat"
    if not Xp.exists():
        Xp = EMBER_DIR / "X_train.dat"
        yp = EMBER_DIR / "y_train.dat"

    y_full = np.fromfile(str(yp), dtype=np.float32)
    X_full = np.fromfile(str(Xp), dtype=np.float32).reshape(-1, N_FEATURES)

    mask = y_full != -1
    X_full, y_full = X_full[mask], y_full[mask]

    rng = np.random.RandomState(seed)
    idx = rng.choice(len(y_full), min(n, len(y_full)), replace=False)
    X, y = X_full[idx], y_full[idx]
    print(f"   ✅ {len(y)} samples | {int(y.sum())} mal / {int((1-y).sum())} ben")
    return X.astype(np.float64), y


# ══════════════════════════════════════════════════════════════
# 2. SHAP COMPUTER
# ══════════════════════════════════════════════════════════════

class SHAPComputer:
    """Wrapper để compute SHAP values hiệu quả."""

    def __init__(self, model: lgb.Booster):
        self.model = model
        self.explainer = None
        if SHAP_AVAILABLE:
            print("   🔧 Initializing SHAP TreeExplainer...")
            self.explainer = shap_lib.TreeExplainer(model)
            print("   ✅ SHAP ready")

    def compute(self, X: np.ndarray) -> np.ndarray:
        """
        Compute SHAP values cho batch X.
        Returns: array (n_samples, n_features)
        """
        if self.explainer is None:
            return np.zeros_like(X)
        sv = self.explainer.shap_values(X)
        if isinstance(sv, list):
            sv = sv[0]
        return np.array(sv)

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict(X)


# ══════════════════════════════════════════════════════════════
# 3. METRIC 1 — FEATURE FAITHFULNESS
# ══════════════════════════════════════════════════════════════

def compute_feature_faithfulness(shap_computer: SHAPComputer,
                                  X: np.ndarray, y: np.ndarray,
                                  k_values: list = [10, 25, 50, 100],
                                  n_samples: int = 500) -> dict:
    """
    Feature Faithfulness (FF):

    Logic:
      1. Tính SHAP values → biết top-K features quan trọng nhất
      2. Tạo X_masked: set top-K features = mean (như thể không có)
      3. Đo AUC drop: AUC_original - AUC_masked
      4. FF = normalized AUC drop (cao = SHAP đúng)

    PE-aware trick:
      Thay vì set = 0 (naive), set = feature mean của training data
      Vì nhiều PE features có 0 là giá trị có nghĩa (feature absent)
      Set = mean là neutral hơn và không tạo out-of-distribution samples.
    """
    print("\n📐 Computing Feature Faithfulness...")

    # Sample subset để nhanh
    rng  = np.random.RandomState(42)
    idx  = rng.choice(len(y), min(n_samples, len(y)), replace=False)
    X_s  = X[idx];  y_s = y[idx]

    # Feature means (dùng để mask)
    feat_means = X.mean(axis=0)

    # SHAP values
    print(f"   Computing SHAP for {len(X_s)} samples...")
    sv = shap_computer.compute(X_s)       # (n, 2381)

    # Baseline AUC
    probs_orig = shap_computer.predict(X_s)
    auc_orig   = roc_auc_score(y_s, probs_orig)
    print(f"   Baseline AUC: {auc_orig:.4f}")

    results = {}
    for k in k_values:
        # Top-K features per sample (by |SHAP|)
        top_k_per_sample = np.argsort(np.abs(sv), axis=1)[:, -k:]

        # Mask: replace top-K với mean
        X_masked = X_s.copy()
        for i in range(len(X_s)):
            X_masked[i, top_k_per_sample[i]] = feat_means[top_k_per_sample[i]]

        probs_masked = shap_computer.predict(X_masked)
        auc_masked   = roc_auc_score(y_s, probs_masked)
        auc_drop     = auc_orig - auc_masked

        # FIX: Normalize bằng max possible drop = auc_orig - 0.5
        # random classifier AUC = 0.5, nên max drop có thể = auc_orig - 0.5
        # Công thức cũ drop/auc_orig → underestimate khi auc_orig ~ 0.97
        max_possible_drop = max(auc_orig - 0.5, 1e-10)
        ff_score = float(np.clip(auc_drop / max_possible_drop, 0, 1))

        results[k] = {
            'auc_original': float(auc_orig),
            'auc_masked':   float(auc_masked),
            'auc_drop':     float(auc_drop),
            'ff_score':     ff_score,
        }
        print(f"   k={k:3d}: AUC {auc_orig:.4f} → {auc_masked:.4f} "
              f"(drop={auc_drop:+.4f}, FF={ff_score:.4f})")

    # Also test RANDOM features (control)
    random_feat_idx = rng.choice(N_FEATURES, k_values[-1], replace=False)
    X_random_masked = X_s.copy()
    X_random_masked[:, random_feat_idx] = feat_means[random_feat_idx]
    auc_random = roc_auc_score(y_s, shap_computer.predict(X_random_masked))
    auc_drop_random = auc_orig - auc_random

    results['random_control'] = {
        'auc_drop':  float(auc_drop_random),
        'ff_score':  float(np.clip(auc_drop_random / max(auc_orig - 0.5, 1e-10), 0, 1)),
    }
    print(f"   Random control (k={k_values[-1]}): "
          f"drop={auc_drop_random:+.4f} "
          f"(SHAP should be higher than this)")

    # Overall FF = weighted average, ưu tiên k lớn hơn
    # Lý do: PE features có redundancy cao (2381 features, nhiều correlated)
    # k nhỏ → model dùng correlated features thay thế → underestimate FF
    # k lớn → phá redundancy → phản ánh đúng hơn
    weights_k = np.array([k for k in k_values], dtype=float)
    weights_k = weights_k / weights_k.sum()   # normalize
    ff_scores = np.array([results[k]['ff_score'] for k in k_values])
    ff_overall = float(np.dot(ff_scores, weights_k))
    results['overall'] = ff_overall

    # Redundancy score: đặc tính của PE features
    # Cao = features redundant, cần xóa nhiều mới thấy effect
    if len(k_values) >= 2:
        drop_small = results[k_values[0]]['auc_drop']
        drop_large = results[k_values[-1]]['auc_drop']
        redundancy = 1.0 - (drop_small / max(drop_large, 1e-10))
        results['redundancy_score'] = float(redundancy)
        print(f"   PE Feature Redundancy: {redundancy:.4f} "
              f"(high = many correlated features, expected for PE)")

    # Faithfulness ratio: SHAP/Random (>1 = SHAP better than random)
    shap_drop   = results[k_values[-1]]['auc_drop']
    random_drop = results['random_control']['auc_drop']
    results['faithfulness_ratio'] = float(shap_drop / max(abs(random_drop), 1e-6))

    print(f"   ✅ Feature Faithfulness (overall): {ff_overall:.4f}")
    print(f"   ✅ Faithfulness Ratio (SHAP/Random): "
          f"{results['faithfulness_ratio']:.2f}x")

    return results


# ══════════════════════════════════════════════════════════════
# 4. METRIC 2 — EXPLANATION CONSISTENCY
# ══════════════════════════════════════════════════════════════

def compute_explanation_consistency(shap_computer: SHAPComputer,
                                     X: np.ndarray,
                                     noise_levels: list = [0.01, 0.05, 0.1],
                                     n_samples: int = 200,
                                     n_perturb: int = 5) -> dict:
    """
    Explanation Consistency (EC):

    Logic:
      1. Lấy sample X_i, compute SHAP → explanation E_i
      2. Tạo n_perturb versions với Gaussian noise nhỏ
      3. Compute SHAP cho mỗi version → E_i_1, ..., E_i_n
      4. EC = mean cosine similarity giữa E_i và các E_i_j
      5. EC cao = explanation ổn định dù input hơi thay đổi

    PE-aware:
      Noise chỉ thêm vào non-zero features (zero = feature absent,
      thêm noise vào zero tạo ra artifact không thực tế)
    """
    print("\n📐 Computing Explanation Consistency...")

    rng = np.random.RandomState(42)
    idx = rng.choice(len(X), min(n_samples, len(X)), replace=False)
    X_s = X[idx]

    # Original SHAP
    print(f"   Computing original SHAP for {len(X_s)} samples...")
    sv_orig = shap_computer.compute(X_s)   # (n, 2381)

    results = {}
    for noise_std in noise_levels:
        similarities = []

        for _ in range(n_perturb):
            # PE-aware noise: only perturb non-zero features
            noise = np.zeros_like(X_s)
            nonzero_mask = X_s != 0
            noise[nonzero_mask] = (
                rng.randn(nonzero_mask.sum()) *
                noise_std * np.abs(X_s[nonzero_mask])
            )
            X_perturbed = X_s + noise

            sv_perturbed = shap_computer.compute(X_perturbed)

            # Cosine similarity per sample
            for i in range(len(X_s)):
                a = sv_orig[i];      b = sv_perturbed[i]
                norm_a = np.linalg.norm(a); norm_b = np.linalg.norm(b)
                if norm_a > 1e-10 and norm_b > 1e-10:
                    sim = float(np.dot(a, b) / (norm_a * norm_b))
                    similarities.append(sim)

        ec_score = float(np.mean(similarities)) if similarities else 0.0
        results[noise_std] = {
            'ec_score':  ec_score,
            'ec_std':    float(np.std(similarities)),
            'n_pairs':   len(similarities),
        }
        print(f"   noise={noise_std:.2f}: EC={ec_score:.4f} ± "
              f"{results[noise_std]['ec_std']:.4f}")

    # Overall EC = weighted average (lower noise = more important)
    weights = [1.0 / s for s in noise_levels]
    total_w = sum(weights)
    ec_overall = float(sum(results[s]['ec_score'] * w / total_w
                           for s, w in zip(noise_levels, weights)))
    results['overall'] = ec_overall

    print(f"   ✅ Explanation Consistency (overall): {ec_overall:.4f}")
    return results


# ══════════════════════════════════════════════════════════════
# 5. METRIC 3 — CONTRASTIVE FIDELITY
# ══════════════════════════════════════════════════════════════

def compute_contrastive_fidelity(shap_computer: SHAPComputer,
                                  X: np.ndarray, y: np.ndarray,
                                  top_k: int = 20,
                                  n_pairs: int = 200) -> dict:
    """
    Contrastive Fidelity (CF):

    Logic:
      1. Lấy sample malware M_i, tìm benign sample gần nhất B_i
         (dùng KNN trong feature space)
      2. Tính diff features: features thực sự phân biệt M_i vs B_i
         diff_feat = |M_i - B_i| > threshold
      3. Tính SHAP top-K features của M_i
      4. CF = overlap(SHAP_top_K, diff_features)
         → SHAP phải highlight features phân biệt M vs B

    Ý nghĩa:
      Nếu CF cao: SHAP chỉ đúng features làm M khác B
      Nếu CF thấp: SHAP đang explain shared features (không discriminative)
    """
    print("\n📐 Computing Contrastive Fidelity...")

    mal_idx = np.where(y == 1)[0]
    ben_idx = np.where(y == 0)[0]

    # Sample pairs
    rng      = np.random.RandomState(42)
    n_pairs  = min(n_pairs, len(mal_idx))
    sel_mal  = rng.choice(mal_idx, n_pairs, replace=False)

    X_mal = X[sel_mal]
    X_ben = X[ben_idx]

    # KNN: tìm benign gần nhất cho mỗi malware
    print(f"   Finding nearest benign neighbor for {n_pairs} malware samples...")
    knn = NearestNeighbors(n_neighbors=1, metric='euclidean', n_jobs=-1)
    knn.fit(X_ben)
    _, nn_idx = knn.kneighbors(X_mal)
    X_nearest_ben = X_ben[nn_idx.squeeze()]

    # SHAP values cho malware samples
    print(f"   Computing SHAP for malware samples...")
    sv_mal = shap_computer.compute(X_mal)   # (n_pairs, 2381)

    # Tính overlap
    overlaps        = []
    diff_sizes      = []
    shap_in_diff    = []

    for i in range(n_pairs):
        # Features thực sự khác nhau giữa M và B
        feat_diff = np.abs(X_mal[i] - X_nearest_ben[i])
        # Threshold: top-K% features có diff lớn nhất
        diff_threshold  = np.percentile(feat_diff, 100 - top_k/N_FEATURES*100*5)
        diff_feat_idx   = set(np.where(feat_diff > diff_threshold)[0])

        # SHAP top-K features của malware sample
        shap_top_k_idx  = set(np.argsort(np.abs(sv_mal[i]))[-top_k:])

        # Overlap
        if len(diff_feat_idx) > 0 and len(shap_top_k_idx) > 0:
            overlap = len(diff_feat_idx & shap_top_k_idx)
            overlap_pct = overlap / len(shap_top_k_idx)
            overlaps.append(overlap_pct)
            diff_sizes.append(len(diff_feat_idx))
            shap_in_diff.append(overlap)

    cf_score = float(np.mean(overlaps)) if overlaps else 0.0
    results = {
        'cf_score':          cf_score,
        'cf_std':            float(np.std(overlaps)),
        'mean_diff_features': float(np.mean(diff_sizes)),
        'mean_shap_in_diff': float(np.mean(shap_in_diff)),
        'n_pairs':           len(overlaps),
        'top_k':             top_k,
        'overall':           cf_score,
    }
    print(f"   ✅ Contrastive Fidelity: {cf_score:.4f} ± {results['cf_std']:.4f}")
    print(f"      Mean diff features: {results['mean_diff_features']:.1f}")
    print(f"      SHAP features in diff set: {results['mean_shap_in_diff']:.1f}/{top_k}")
    return results


# ══════════════════════════════════════════════════════════════
# 6. OVERALL FIDELITY SCORE
# ══════════════════════════════════════════════════════════════

def compute_overall_fidelity(ff_results: dict,
                              ec_results: dict,
                              cf_results: dict) -> dict:
    """
    Overall Fidelity Score (OFS):

    Weights:
      FF: 0.5 → most important, directly measures explanation accuracy
      EC: 0.3 → stability under noise
      CF: 0.2 → discriminative quality

    Security-aware: FF weighted higher vì false explanation về
    malware features có thể dẫn đến wrong security decision.
    """
    ff = ff_results['overall']
    ec = ec_results['overall']
    cf = cf_results['overall']

    weights     = {'ff': 0.5, 'ec': 0.3, 'cf': 0.2}
    ofs         = weights['ff']*ff + weights['ec']*ec + weights['cf']*cf

    # Grade
    if ofs >= 0.60:   grade = "HIGH ✅ (Trustworthy)"
    elif ofs >= 0.40: grade = "MEDIUM ⚠️  (Acceptable)"
    else:             grade = "LOW ❌ (Needs improvement)"

    return {
        'feature_faithfulness':     ff,
        'explanation_consistency':  ec,
        'contrastive_fidelity':     cf,
        'weights':                  weights,
        'overall_fidelity_score':   float(ofs),
        'grade':                    grade,
        'faithfulness_ratio':       ff_results.get('faithfulness_ratio', 0),
    }


# ══════════════════════════════════════════════════════════════
# 7. MULTI-STAGE FIDELITY
# ══════════════════════════════════════════════════════════════

def compute_multistage_fidelity(shap_computer: SHAPComputer,
                                 X: np.ndarray, y: np.ndarray,
                                 n_samples: int = 300) -> dict:
    """
    Đánh giá fidelity theo từng nhóm feature của EMBER:

    EMBER 2381 features gồm:
      - ByteHistogram    [0:256]      → byte distribution
      - ByteEntropyHist  [256:512]    → entropy features
      - StringFeatures   [512:616]    → string analysis
      - GeneralFileInfo  [616:622]    → file metadata
      - HeaderFeatures   [622:738]    → PE header
      - SectionFeatures  [738:1018]   → PE sections
      - ImportsFeatures  [1018:1306]  → imported functions
      - ExportsFeatures  [1306:1338]  → exported functions
      - DataDirectories  [1338:2381]  → data directories

    Ý nghĩa: SHAP có fidelity cao hơn ở nhóm feature nào?
    → Biết group nào đáng tin để explain hơn
    """
    print("\n📐 Computing Multi-Stage Feature Group Fidelity...")

    FEATURE_GROUPS = {
        'ByteHistogram':   (0,    256),
        'ByteEntropy':     (256,  512),
        'StringFeatures':  (512,  616),
        'GeneralFileInfo': (616,  622),
        'PEHeader':        (622,  738),
        'PESections':      (738,  1018),
        'Imports':         (1018, 1306),
        'Exports':         (1306, 1338),
        'DataDirectories': (1338, 2381),
    }

    rng = np.random.RandomState(42)
    idx = rng.choice(len(y), min(n_samples, len(y)), replace=False)
    X_s = X[idx];  y_s = y[idx]

    feat_means   = X.mean(axis=0)
    sv           = shap_computer.compute(X_s)
    probs_orig   = shap_computer.predict(X_s)
    auc_orig     = roc_auc_score(y_s, probs_orig)

    group_results = {}
    for group_name, (start, end) in FEATURE_GROUPS.items():
        # Mask toàn bộ feature group
        X_masked = X_s.copy()
        X_masked[:, start:end] = feat_means[start:end]

        probs_masked = shap_computer.predict(X_masked)
        try:
            auc_masked = roc_auc_score(y_s, probs_masked)
        except Exception:
            auc_masked = auc_orig

        auc_drop  = auc_orig - auc_masked
        group_size = end - start

        # SHAP concentration in this group
        shap_in_group   = np.abs(sv[:, start:end]).sum(axis=1).mean()
        shap_total      = np.abs(sv).sum(axis=1).mean()
        shap_pct        = float(shap_in_group / max(shap_total, 1e-10))

        # Fidelity for this group:
        # SHAP should allocate more importance to groups that hurt more when removed
        expected_shap_pct = float(auc_drop / max(auc_orig, 1e-10))
        alignment = float(1.0 - abs(shap_pct - expected_shap_pct))

        group_results[group_name] = {
            'feature_range':     f"[{start}:{end}]",
            'n_features':        group_size,
            'auc_drop':          float(auc_drop),
            'shap_concentration': shap_pct,
            'alignment_score':   alignment,
        }
        print(f"   {group_name:<18}: AUC drop={auc_drop:+.4f}  "
              f"SHAP%={shap_pct:.3f}  Align={alignment:.3f}")

    # Best and worst groups
    best  = max(group_results, key=lambda g: group_results[g]['alignment_score'])
    worst = min(group_results, key=lambda g: group_results[g]['alignment_score'])
    mean_align = float(np.mean([v['alignment_score']
                                for v in group_results.values()]))

    print(f"\n   Best  aligned group: {best} "
          f"({group_results[best]['alignment_score']:.3f})")
    print(f"   Worst aligned group: {worst} "
          f"({group_results[worst]['alignment_score']:.3f})")
    print(f"   Mean alignment: {mean_align:.3f}")

    return {
        'groups':        group_results,
        'best_group':    best,
        'worst_group':   worst,
        'mean_alignment': mean_align,
        'baseline_auc':  float(auc_orig),
    }


# ══════════════════════════════════════════════════════════════
# 8. REPORT
# ══════════════════════════════════════════════════════════════

def print_fidelity_report(ofs: dict, ff: dict, ec: dict,
                           cf: dict, ms: dict = None):
    """In báo cáo fidelity đầy đủ."""

    print(f"\n{'='*65}")
    print(f"📋 XAI FIDELITY EVALUATION REPORT")
    print(f"{'='*65}")
    print(f"""
┌─────────────────────────────────────────────────────────────┐
│  OVERALL FIDELITY SCORE: {ofs['overall_fidelity_score']:.4f}                          │
│  Grade: {ofs['grade']:<52}│
├──────────────────────┬──────────┬────────┬──────────────────┤
│  Metric              │  Score   │ Weight │  Interpretation  │
├──────────────────────┼──────────┼────────┼──────────────────┤
│  Feature Faithfulness│  {ofs['feature_faithfulness']:.4f}  │  0.50  │ {"High ✅" if ofs['feature_faithfulness']>0.45 else "Medium ⚠️ " if ofs['feature_faithfulness']>0.3 else "Low ❌ ":16}│
│  Explanation Consist.│  {ofs['explanation_consistency']:.4f}  │  0.30  │ {"High ✅" if ofs['explanation_consistency']>0.8 else "Medium ⚠️ " if ofs['explanation_consistency']>0.6 else "Low ❌ ":16}│
│  Contrastive Fidelity│  {ofs['contrastive_fidelity']:.4f}  │  0.20  │ {"High ✅" if ofs['contrastive_fidelity']>0.4 else "Medium ⚠️ " if ofs['contrastive_fidelity']>0.2 else "Low ❌ ":16}│
├──────────────────────┼──────────┼────────┼──────────────────┤
│  Faithfulness Ratio  │  {ofs['faithfulness_ratio']:5.2f}x  │   -    │ {"SHAP > Random ✅" if ofs['faithfulness_ratio']>1 else "SHAP ≤ Random ⚠️":16}│
└──────────────────────┴──────────┴────────┴──────────────────┘""")

    # FF detail
    print(f"\n  Feature Faithfulness Detail:")
    for k, v in ff.items():
        if isinstance(k, int):
            print(f"    k={k:3d}: AUC drop={v['auc_drop']:+.4f}  "
                  f"FF={v['ff_score']:.4f}")
    rc = ff.get('random_control', {})
    print(f"    Random: AUC drop={rc.get('auc_drop',0):+.4f}  "
          f"FF={rc.get('ff_score',0):.4f}  ← baseline")

    # EC detail
    print(f"\n  Explanation Consistency Detail:")
    for noise, v in ec.items():
        if isinstance(noise, float):
            print(f"    noise={noise:.2f}: EC={v['ec_score']:.4f} ± {v['ec_std']:.4f}")

    # CF detail
    print(f"\n  Contrastive Fidelity:")
    print(f"    Score={cf['cf_score']:.4f} ± {cf['cf_std']:.4f}")
    print(f"    Mean SHAP features overlapping diff: "
          f"{cf['mean_shap_in_diff']:.1f}/{cf['top_k']}")

    # Multi-stage
    if ms:
        print(f"\n  Multi-Stage Feature Group Analysis:")
        print(f"  {'Group':<18} {'AUC Drop':>10} {'SHAP%':>8} {'Align':>8}")
        print("  " + "─"*48)
        for g, v in sorted(ms['groups'].items(),
                            key=lambda x: x[1]['auc_drop'], reverse=True):
            print(f"  {g:<18} {v['auc_drop']:>+10.4f} "
                  f"{v['shap_concentration']:>8.3f} "
                  f"{v['alignment_score']:>8.3f}")
        print(f"\n  Best group : {ms['best_group']}")
        print(f"  Worst group: {ms['worst_group']}")

    # Thesis interpretation
    ofs_score = ofs['overall_fidelity_score']
    fr        = ofs['faithfulness_ratio']
    print(f"""
{'='*65}
📝 THESIS INTERPRETATION:

  Overall Fidelity = {ofs_score:.4f} → {ofs['grade']}

  1. Feature Faithfulness = {ofs['feature_faithfulness']:.4f}
     Xóa top SHAP features → AUC giảm {ff.get(50,{}).get('auc_drop',0):+.4f}
     vs Random features → AUC giảm {ff.get('random_control',{}).get('auc_drop',0):+.4f}
     → SHAP {fr:.1f}x tốt hơn Random selection ({'✅ significant' if fr > 1.2 else '⚠️ marginal'})

  2. Explanation Consistency = {ofs['explanation_consistency']:.4f}
     SHAP explanation stable under small input perturbations
     → {"Analyst có thể trust explanation ✅" if ofs['explanation_consistency'] > 0.8 else "Explanation có thể flip với noise nhỏ ⚠️"}

  3. Contrastive Fidelity = {ofs['contrastive_fidelity']:.4f}
     SHAP highlights features phân biệt malware vs benign neighbor
     → {"Discriminative explanation ✅" if ofs['contrastive_fidelity'] > 0.3 else "Explanation không đủ discriminative ⚠️"}

  CONCLUSION: SHAP explanations trong hệ thống ransomware detection
  này có fidelity {"cao, đáng tin cậy cho security analysts" if ofs_score > 0.60
  else "trung bình, cần thận trọng khi interpret" if ofs_score > 0.40
  else "thấp, cần cải thiện explanation method"}.
{'='*65}""")


# ══════════════════════════════════════════════════════════════
# 9. SAVE RESULTS
# ══════════════════════════════════════════════════════════════

def save_results(ofs, ff, ec, cf, ms, output_path="xai_fidelity_results.json"):
    result = {
        'experiment_time':      datetime.now().isoformat(),
        'model':                str(MODEL_PATH),
        'overall_fidelity':     ofs,
        'feature_faithfulness': {str(k): v for k, v in ff.items()},
        'explanation_consistency': {str(k): v for k, v in ec.items()},
        'contrastive_fidelity': cf,
        'multistage_analysis':  ms,
    }
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n💾 Results saved → {output_path}")
    return result


# ══════════════════════════════════════════════════════════════
# 10. MAIN
# ══════════════════════════════════════════════════════════════

def main():
    ap = argparse.ArgumentParser(description="XAI Fidelity Evaluation")
    ap.add_argument("--quick",      action="store_true",
                    help="Quick test: 500 samples, basic metrics")
    ap.add_argument("--full",       action="store_true",
                    help="Full evaluation: 5000 samples, all metrics")
    ap.add_argument("--multistage", action="store_true",
                    help="Include multi-stage feature group analysis")
    ap.add_argument("--n_samples",  type=int, default=2000)
    args = ap.parse_args()

    print("\n" + "="*65)
    print("🔬 XAI FIDELITY EVALUATION FRAMEWORK")
    print("   Novel Contribution #3 — Ransomware Detection Thesis")
    print("="*65)

    # Config
    if args.quick:
        n_samples   = 500
        n_ff        = 200
        n_ec        = 100
        n_cf        = 100
        n_ms        = 200
        k_values    = [10, 50]
        noise_lvls  = [0.05, 0.1]
        print("⚡ QUICK MODE")
    elif args.full:
        n_samples   = 5000
        n_ff        = 1000
        n_ec        = 500
        n_cf        = 300
        n_ms        = 500
        k_values    = [10, 25, 50, 100]
        noise_lvls  = [0.01, 0.05, 0.1]
        print("🔬 FULL MODE")
    else:
        n_samples   = args.n_samples
        n_ff        = min(500, n_samples)
        n_ec        = min(200, n_samples)
        n_cf        = min(200, n_samples)
        n_ms        = min(300, n_samples)
        k_values    = [10, 25, 50]
        noise_lvls  = [0.05, 0.1]

    # Load
    X, y = load_ember_sample(n=n_samples)

    # Model + SHAP
    print(f"\n🔧 Loading model: {MODEL_PATH}")
    model  = lgb.Booster(model_file=str(MODEL_PATH))
    shap_c = SHAPComputer(model)

    # Compute metrics
    ff = compute_feature_faithfulness(shap_c, X, y,
                                       k_values=k_values, n_samples=n_ff)
    ec = compute_explanation_consistency(shap_c, X,
                                          noise_levels=noise_lvls,
                                          n_samples=n_ec)
    cf = compute_contrastive_fidelity(shap_c, X, y, n_pairs=n_cf)

    ms = None
    if args.multistage or not args.quick:
        ms = compute_multistage_fidelity(shap_c, X, y, n_samples=n_ms)

    # Overall score
    ofs = compute_overall_fidelity(ff, ec, cf)

    # Report
    print_fidelity_report(ofs, ff, ec, cf, ms)

    # Save
    save_results(ofs, ff, ec, cf, ms)


if __name__ == "__main__":
    main()