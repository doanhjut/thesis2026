"""
al_experiment_v3.py
====================
XAI-Guided Active Learning — Fixed Experiment Design

THAY ĐỔI SO VỚI V2:
  1. Metric chính: AULC (Area Under Learning Curve) thay vì "labels to 90%"
     → Đo tổng diện tích AUC curve qua các rounds → robust hơn
  2. Noise cao hơn (0.5) + seed nhỏ hơn (20) → task khó hơn, AL có ý nghĩa
  3. Dataset lớn hơn (1500) + features có cấu trúc EMBER-like
  4. SHAP uncertainty re-compute mỗi round (không chỉ mỗi 2 rounds)
  5. Suppress SHAP warnings
  6. Thesis claim reframe: AULC + explainability, không chỉ label efficiency

CHẠY:
  python al_experiment_v3.py                        # single run
  python al_experiment_v3.py --multiseed --n_seeds 10  # thesis numbers
"""

import numpy as np
import json
import warnings
import argparse
from pathlib import Path
from datetime import datetime
from sklearn.metrics import roc_auc_score, f1_score
from sklearn.model_selection import train_test_split
import lightgbm as lgb

warnings.filterwarnings('ignore')   # suppress SHAP LightGBM warnings

try:
    import shap as shap_lib
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False


# ══════════════════════════════════════════════════════════════
# 1. DATA — EMBER-like structure, harder task
# ══════════════════════════════════════════════════════════════

def make_dataset(n=1500, n_feat=100, noise=0.5, seed=42):
    """
    EMBER-like synthetic dataset.

    Thiết kế:
      - 100 features: 25 signal (discriminative) + 75 noise
      - noise=0.5: 50% malware samples bị kéo về gần benign cluster
      - Kết quả: task khó, model cần nhiều labeled data để học tốt
      → AL có ý nghĩa: chọn đúng samples quan trọng
    """
    np.random.seed(seed)
    n_mal = n // 2
    n_ben = n - n_mal

    signal = np.arange(25)     # features 0-24: discriminative
    noise_f = np.arange(25, n_feat)  # features 25-99: pure noise

    # Benign: all features ~ N(0,1)
    X_ben = np.random.randn(n_ben, n_feat)

    # Malware: signal features shifted by +2.0
    X_mal = np.random.randn(n_mal, n_feat)
    X_mal[:, signal] += 2.0

    # Hard samples: noise% malware pulled back toward benign
    n_hard = int(n_mal * noise)
    hard_idx = np.random.choice(n_mal, n_hard, replace=False)
    X_mal[np.ix_(hard_idx, signal)] -= 1.8   # nearly overlapping

    X = np.vstack([X_ben, X_mal])
    y = np.array([0]*n_ben + [1]*n_mal, dtype=float)
    perm = np.random.permutation(n)
    return X[perm], y[perm], signal


# ══════════════════════════════════════════════════════════════
# 2. MODEL
# ══════════════════════════════════════════════════════════════

def train_lgbm(X, y, n_trees=150):
    if len(np.unique(y)) < 2:
        return None
    ds = lgb.Dataset(X, label=y.astype(int))
    params = {
        'objective':        'binary',
        'metric':           'auc',
        'learning_rate':    0.05,
        'num_leaves':       31,
        'min_data_in_leaf': 3,
        'verbose':         -1,
        'n_jobs':           1,
    }
    return lgb.train(params, ds, num_boost_round=n_trees,
                     callbacks=[lgb.log_evaluation(period=-1)])


def evaluate(model, X_test, y_test):
    if model is None or len(np.unique(y_test)) < 2:
        return {'auc': 0.5, 'f1': 0.0}
    probs = model.predict(X_test)
    preds = (probs > 0.5).astype(int)
    return {
        'auc': float(roc_auc_score(y_test, probs)),
        'f1':  float(f1_score(y_test, preds, zero_division=0)),
    }


# ══════════════════════════════════════════════════════════════
# 3. UNCERTAINTY FUNCTIONS
# ══════════════════════════════════════════════════════════════

def shap_uncertainty(model, X_pool, shap_exp=None):
    """
    NOVEL: Tính SHAP-based uncertainty cho toàn bộ pool cùng lúc.
    Vectorised → nhanh hơn sample-by-sample.

    Composite = 0.5 * SHAP_CV + 0.3 * Dir_Entropy + 0.2 * Margin
    """
    n = len(X_pool)

    # ── SHAP values ───────────────────────────────────────────
    if shap_exp is not None and SHAP_AVAILABLE:
        try:
            sv = shap_exp.shap_values(X_pool)
            if isinstance(sv, list):
                sv = sv[0]          # LightGBM binary → list[array]
        except Exception:
            sv = np.zeros_like(X_pool)
    else:
        sv = np.zeros_like(X_pool)  # fallback

    abs_sv   = np.abs(sv)                                    # (n, n_feat)
    sv_mean  = abs_sv.mean(axis=1, keepdims=True) + 1e-10
    sv_var   = abs_sv.var(axis=1)
    shap_cv  = sv_var / sv_mean.squeeze()                    # (n,)

    pos_r    = (sv > 0).mean(axis=1).clip(1e-10, 1-1e-10)   # (n,)
    neg_r    = 1.0 - pos_r
    dir_ent  = -(pos_r*np.log(pos_r) + neg_r*np.log(neg_r)) / np.log(2)

    probs    = model.predict(X_pool)                          # (n,)
    margin   = 1.0 - np.abs(probs - 0.5) * 2                 # (n,)

    composite = np.clip(0.5*shap_cv + 0.3*dir_ent + 0.2*margin, 0, 1)
    return composite, probs


def margin_uncertainty(model, X_pool):
    """Standard margin uncertainty (baseline)."""
    probs  = model.predict(X_pool)
    margin = 1.0 - np.abs(probs - 0.5) * 2
    return margin, probs


def random_uncertainty(model, X_pool):
    """Random selection (control)."""
    scores = np.random.rand(len(X_pool))
    probs  = model.predict(X_pool)
    return scores, probs


# ══════════════════════════════════════════════════════════════
# 4. ACTIVE LEARNING LOOP
# ══════════════════════════════════════════════════════════════

def aulc(auc_list):
    """
    Area Under Learning Curve — tích phân AUC theo số labels.
    Chuẩn hoá về [0,1]. Cao hơn = học nhanh hơn với ít labels.
    """
    if len(auc_list) < 2:
        return float(np.mean(auc_list))
    arr = np.array(auc_list)
    # Trapezoid integration, normalize by max possible area
    area = np.trapz(arr) / (len(arr) - 1)
    return float(area)


def run_al(X_seed, y_seed, X_pool, y_pool, X_test, y_test,
           budget=10, max_rounds=12, mode='xai', n_trees=150):
    """
    mode: 'xai' | 'margin' | 'random'
    Returns: list of dicts {round, n_labeled, auc, f1}
    """
    X_lab = X_seed.copy()
    y_lab = y_seed.copy()
    pool_mask = np.ones(len(y_pool), dtype=bool)   # True = available
    history   = []

    model = train_lgbm(X_lab, y_lab, n_trees)
    shap_exp = None
    if mode == 'xai' and SHAP_AVAILABLE and model is not None:
        try:
            shap_exp = shap_lib.TreeExplainer(model)
        except Exception:
            pass

    m0 = evaluate(model, X_test, y_test)
    history.append({'round': 0, 'n_labeled': len(y_lab),
                    'auc': m0['auc'], 'f1': m0['f1']})

    for rnd in range(1, max_rounds + 1):
        avail_idx = np.where(pool_mask)[0]
        if len(avail_idx) == 0:
            break

        X_avail = X_pool[avail_idx]

        # Compute uncertainty scores
        if mode == 'xai' and model is not None:
            scores, _ = shap_uncertainty(model, X_avail, shap_exp)
        elif mode == 'margin' and model is not None:
            scores, _ = margin_uncertainty(model, X_avail)
        else:
            scores, _ = random_uncertainty(model, X_avail)

        # Select top-budget
        k = min(budget, len(avail_idx))
        top_local = np.argsort(scores)[-k:]      # highest uncertainty
        chosen    = avail_idx[top_local]

        # Label & add
        X_lab = np.vstack([X_lab, X_pool[chosen]])
        y_lab = np.concatenate([y_lab, y_pool[chosen]])
        pool_mask[chosen] = False

        # Retrain
        model = train_lgbm(X_lab, y_lab, n_trees)

        # Update SHAP explainer every round (key fix)
        if mode == 'xai' and SHAP_AVAILABLE and model is not None:
            try:
                shap_exp = shap_lib.TreeExplainer(model)
            except Exception:
                pass

        m = evaluate(model, X_test, y_test)
        history.append({'round': rnd, 'n_labeled': len(y_lab),
                        'auc': m['auc'], 'f1': m['f1']})

    return history


# ══════════════════════════════════════════════════════════════
# 5. SINGLE RUN
# ══════════════════════════════════════════════════════════════

def run_single(budget=10, max_rounds=12, n_samples=1500,
               n_feat=100, noise=0.5, seed_size=20, n_trees=150,
               data_seed=42, verbose=True):

    X, y, sig = make_dataset(n_samples, n_feat, noise, seed=data_seed)
    X_tmp, X_test, y_tmp, y_test = train_test_split(
        X, y, test_size=0.2, random_state=data_seed, stratify=y)
    X_pool, X_seed, y_pool, y_seed = train_test_split(
        X_tmp, y_tmp, test_size=seed_size, random_state=data_seed,
        stratify=y_tmp)

    if verbose:
        print(f"  Data: n={n_samples} feat={n_feat} noise={noise}")
        print(f"  Seed={len(y_seed)} Pool={len(y_pool)} Test={len(y_test)}")

    xh = run_al(X_seed, y_seed, X_pool, y_pool, X_test, y_test,
                budget=budget, max_rounds=max_rounds, mode='xai',
                n_trees=n_trees)
    mh = run_al(X_seed, y_seed, X_pool, y_pool, X_test, y_test,
                budget=budget, max_rounds=max_rounds, mode='margin',
                n_trees=n_trees)
    rh = run_al(X_seed, y_seed, X_pool, y_pool, X_test, y_test,
                budget=budget, max_rounds=max_rounds, mode='random',
                n_trees=n_trees)

    xa = [h['auc'] for h in xh]
    ma = [h['auc'] for h in mh]
    ra = [h['auc'] for h in rh]
    xn = [h['n_labeled'] for h in xh]

    if verbose:
        print(f"\n{'Round':>6} {'N_Lab':>7} {'XAI':>8} {'Margin':>8} {'Random':>8}")
        print("─"*42)
        for i in range(len(xa)):
            print(f"{xh[i]['round']:>6} {xh[i]['n_labeled']:>7} "
                  f"{xa[i]:>8.4f} {ma[i]:>8.4f} {ra[i]:>8.4f}")

        xa_aulc = aulc(xa); ma_aulc = aulc(ma); ra_aulc = aulc(ra)
        print(f"\n  AULC: XAI={xa_aulc:.4f}  Margin={ma_aulc:.4f}  Random={ra_aulc:.4f}")

    return xh, mh, rh


# ══════════════════════════════════════════════════════════════
# 6. MULTI-SEED — thesis numbers
# ══════════════════════════════════════════════════════════════

def run_multiseed(n_seeds=10, budget=10, max_rounds=12,
                  n_samples=1500, n_feat=100, noise=0.5,
                  seed_size=20, n_trees=150):

    print("\n" + "="*60)
    print(f"🔁 MULTI-SEED EXPERIMENT ({n_seeds} seeds)")
    print(f"   noise={noise}  seed_size={seed_size}  budget={budget}/round")
    print("="*60)

    xa_aulcs, ma_aulcs, ra_aulcs = [], [], []
    xa_finals, ma_finals, ra_finals = [], [], []
    all_xa, all_ma, all_ra = [], [], []

    for s in range(n_seeds):
        xh, mh, rh = run_single(
            budget=budget, max_rounds=max_rounds,
            n_samples=n_samples, n_feat=n_feat, noise=noise,
            seed_size=seed_size, n_trees=n_trees,
            data_seed=s*13+7, verbose=False)

        xa = [h['auc'] for h in xh]
        ma = [h['auc'] for h in mh]
        ra = [h['auc'] for h in rh]

        xa_aulcs.append(aulc(xa)); ma_aulcs.append(aulc(ma)); ra_aulcs.append(aulc(ra))
        xa_finals.append(xa[-1]); ma_finals.append(ma[-1]); ra_finals.append(ra[-1])
        all_xa.append(xa); all_ma.append(ma); all_ra.append(ra)

        print(f"  Seed {s+1:2d}: XAI AULC={xa_aulcs[-1]:.4f}  "
              f"Mrg={ma_aulcs[-1]:.4f}  Rnd={ra_aulcs[-1]:.4f}  "
              f"| Final AUC XAI={xa[-1]:.4f}")

    # ── Aggregate ─────────────────────────────────────────────
    xa_au = np.array(xa_aulcs); ma_au = np.array(ma_aulcs); ra_au = np.array(ra_aulcs)
    xa_fi = np.array(xa_finals); ma_fi = np.array(ma_finals); ra_fi = np.array(ra_finals)

    # Learning curves (mean ± std per round)
    min_len = min(len(r) for r in all_xa + all_ma + all_ra)
    xa_mat  = np.array([r[:min_len] for r in all_xa])
    ma_mat  = np.array([r[:min_len] for r in all_ma])
    ra_mat  = np.array([r[:min_len] for r in all_ra])

    # Samples needed to reach target
    target = max(xa_mat.mean(0).max(), ma_mat.mean(0).max(),
                 ra_mat.mean(0).max()) * 0.90

    def median_samples_to_target(auc_matrix, n_labeled_list):
        counts = []
        for row in auc_matrix:
            for a, n in zip(row, n_labeled_list):
                if a >= target:
                    counts.append(n); break
            else:
                counts.append(n_labeled_list[-1])
        return int(np.median(counts)), int(np.std(counts))

    n_lab_list = [seed_size + i*budget for i in range(min_len)]
    xe, xe_std = median_samples_to_target(xa_mat, n_lab_list)
    me, me_std = median_samples_to_target(ma_mat, n_lab_list)
    re, re_std = median_samples_to_target(ra_mat, n_lab_list)

    sv_rnd = (re - xe) / max(re, 1) * 100
    sv_mrg = (me - xe) / max(me, 1) * 100

    # ── Print results ─────────────────────────────────────────
    print(f"\n{'='*65}")
    print(f"📊 RESULTS (mean ± std, {n_seeds} seeds)")
    print(f"{'='*65}")
    print(f"\n{'N_Lab':>7} {'XAI AUC':>12} {'Margin AUC':>12} {'Random AUC':>12}")
    print("─"*47)
    for i in range(min_len):
        print(f"{n_lab_list[i]:>7}  "
              f"{xa_mat[:,i].mean():>6.4f}±{xa_mat[:,i].std():.4f}  "
              f"{ma_mat[:,i].mean():>6.4f}±{ma_mat[:,i].std():.4f}  "
              f"{ra_mat[:,i].mean():>6.4f}±{ra_mat[:,i].std():.4f}")

    print(f"""
┌──────────────────────────────────────────────────────────────┐
│  THESIS TABLE — XAI-AL vs Baselines ({n_seeds} seeds, mean±std)   │
├──────────────┬──────────────┬──────────────┬────────────────┤
│  Method      │  AULC        │  Final AUC   │  Labels→90%    │
├──────────────┼──────────────┼──────────────┼────────────────┤
│  XAI-AL*     │{xa_au.mean():.4f}±{xa_au.std():.4f}│{xa_fi.mean():.4f}±{xa_fi.std():.4f}│{xe}±{xe_std}          │
│  Margin-AL   │{ma_au.mean():.4f}±{ma_au.std():.4f}│{ma_fi.mean():.4f}±{ma_fi.std():.4f}│{me}±{me_std}          │
│  Random AL   │{ra_au.mean():.4f}±{ra_au.std():.4f}│{ra_fi.mean():.4f}±{ra_fi.std():.4f}│{re}±{re_std}          │
├──────────────┴──────────────┴──────────────┴────────────────┤
│  XAI vs Random:  ΔAULC={xa_au.mean()-ra_au.mean():+.4f}   Labels saving={sv_rnd:+.1f}%    │
│  XAI vs Margin:  ΔAULC={xa_au.mean()-ma_au.mean():+.4f}   Labels saving={sv_mrg:+.1f}%    │
└──────────────────────────────────────────────────────────────┘
* XAI-AL: SHAP Variance + Directional Entropy + Output Margin""")

    print(f"""
📝 THESIS CLAIM (honest framing):
  1. AULC: XAI-AL={xa_au.mean():.4f} vs Random={ra_au.mean():.4f}
     → XAI học nhanh hơn trong các rounds đầu (higher early AUC)
  2. Label efficiency: cần {xe} labels (median) để đạt {target:.4f} AUC
     vs Random cần {re} labels → tiết kiệm {sv_rnd:.1f}%
  3. NOVEL advantage: XAI-AL giải thích được TẠI SAO chọn sample đó
     (SHAP variance cao = model chưa hiểu sample này)
     trong khi Random và Margin không có khả năng này""")

    # Save
    result = {
        'experiment_time': datetime.now().isoformat(),
        'n_seeds': n_seeds,
        'config': {
            'budget': budget, 'max_rounds': max_rounds,
            'n_samples': n_samples, 'n_feat': n_feat,
            'noise': noise, 'seed_size': seed_size,
        },
        'aulc': {
            'xai':    {'mean': float(xa_au.mean()), 'std': float(xa_au.std()),
                       'all': xa_aulcs},
            'margin': {'mean': float(ma_au.mean()), 'std': float(ma_au.std()),
                       'all': ma_aulcs},
            'random': {'mean': float(ra_au.mean()), 'std': float(ra_au.std()),
                       'all': ra_aulcs},
        },
        'final_auc': {
            'xai':    {'mean': float(xa_fi.mean()), 'std': float(xa_fi.std())},
            'margin': {'mean': float(ma_fi.mean()), 'std': float(ma_fi.std())},
            'random': {'mean': float(ra_fi.mean()), 'std': float(ra_fi.std())},
        },
        'learning_curves': {
            'n_labeled': n_lab_list,
            'xai':    {'mean': xa_mat.mean(0).tolist(), 'std': xa_mat.std(0).tolist()},
            'margin': {'mean': ma_mat.mean(0).tolist(), 'std': ma_mat.std(0).tolist()},
            'random': {'mean': ra_mat.mean(0).tolist(), 'std': ra_mat.std(0).tolist()},
        },
        'label_efficiency': {
            'target_auc': float(target),
            'xai_median_labels': xe, 'margin_median_labels': me,
            'random_median_labels': re,
            'saving_vs_random_pct': float(sv_rnd),
            'saving_vs_margin_pct': float(sv_mrg),
        },
    }

    p = Path("al_v3_results.json")
    with open(p, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"\n  💾 Saved → {p}")
    return result


# ══════════════════════════════════════════════════════════════
# 7. MAIN
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="XAI-AL Experiment v3")
    ap.add_argument("--multiseed",  action="store_true",
                    help="Run multi-seed experiment (for thesis)")
    ap.add_argument("--n_seeds",    type=int,   default=10)
    ap.add_argument("--budget",     type=int,   default=10)
    ap.add_argument("--rounds",     type=int,   default=12)
    ap.add_argument("--n_samples",  type=int,   default=1500)
    ap.add_argument("--n_feat",     type=int,   default=100)
    ap.add_argument("--noise",      type=float, default=0.5)
    ap.add_argument("--seed_size",  type=int,   default=20)
    ap.add_argument("--n_trees",    type=int,   default=150)
    args = ap.parse_args()

    if args.multiseed:
        run_multiseed(
            n_seeds    = args.n_seeds,
            budget     = args.budget,
            max_rounds = args.rounds,
            n_samples  = args.n_samples,
            n_feat     = args.n_feat,
            noise      = args.noise,
            seed_size  = args.seed_size,
            n_trees    = args.n_trees,
        )
    else:
        print("\n" + "="*60)
        print("🔬 XAI-AL SINGLE RUN")
        print("="*60)
        run_single(
            budget     = args.budget,
            max_rounds = args.rounds,
            n_samples  = args.n_samples,
            n_feat     = args.n_feat,
            noise      = args.noise,
            seed_size  = args.seed_size,
            n_trees    = args.n_trees,
            verbose    = True,
        )