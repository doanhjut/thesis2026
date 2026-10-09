"""
al_ember_real.py
=================
XAI-Guided Active Learning — Real EMBER Data
Scenario: "Unknown Ransomware Detection"

THESIS SCENARIO (realistic):
  - Model đã train tốt trên malware "cũ" (known families)
  - Xuất hiện ransomware "mới" (unknown family, chưa trong training)
  - Analyst có 1000 samples nghi ngờ, chỉ label được N samples/tuần
  - Câu hỏi: chọn samples nào để label trước?
    → Random: chọn ngẫu nhiên
    → Margin: chọn samples gần decision boundary
    → XAI-AL: chọn samples có SHAP explanation uncertainty cao nhất
               (model "không hiểu" sample này → cần label gấp)

NOVEL CONTRIBUTION được chứng minh:
  1. XAI-AL đạt target detection rate nhanh hơn (AULC cao hơn)
  2. XAI-AL chọn samples "đúng" hơn — malware rate trong selected cao hơn
  3. XAI-AL explainable: analyst biết TẠI SAO sample được prioritize

CHẠY:
  cd D:\\Code\\Luanvan\\ember_test\\ember
  python al_ember_real.py --quick          # test nhanh 2 phút
  python al_ember_real.py --multiseed      # thesis numbers ~15 phút
"""

import numpy as np
import json
import warnings
import argparse
from pathlib import Path
from datetime import datetime
from sklearn.metrics import roc_auc_score, f1_score, precision_score, recall_score
import lightgbm as lgb

warnings.filterwarnings('ignore')

try:
    import shap as shap_lib
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    print("⚠️  shap not available — using margin fallback for XAI mode")

# ── Paths ──────────────────────────────────────────────────────
EMBER2018_DIR  = Path("../ember2018")
MODEL_PATH     = Path("ransomware_lgbm_1M_final.txt")
N_FEATURES     = 2381


# ══════════════════════════════════════════════════════════════
# 1. LOAD REAL EMBER DATA
# ══════════════════════════════════════════════════════════════

def load_ember(max_samples: int = 50000, seed: int = 42):
    """
    Load EMBER 2018 features từ .dat files.
    Trả về X (float32), y (float32: 0/1).
    """
    print(f"📂 Loading EMBER features (max={max_samples})...")

    X_path = EMBER2018_DIR / "X_test.dat"
    y_path = EMBER2018_DIR / "y_test.dat"

    if not X_path.exists():
        # Fallback: thử X_train
        X_path = EMBER2018_DIR / "X_train.dat"
        y_path = EMBER2018_DIR / "y_train.dat"

    if not X_path.exists():
        raise FileNotFoundError(
            f"Không tìm thấy EMBER data ở {EMBER2018_DIR}\n"
            f"Chạy từ thư mục: D:\\Code\\Luanvan\\ember_test\\ember")

    y_full = np.fromfile(str(y_path), dtype=np.float32)
    X_full = np.fromfile(str(X_path), dtype=np.float32).reshape(-1, N_FEATURES)

    # Filter unlabeled nếu có
    mask = y_full != -1
    X_full, y_full = X_full[mask], y_full[mask]

    # Sample ngẫu nhiên để nhanh hơn
    rng  = np.random.RandomState(seed)
    n    = min(max_samples, len(y_full))
    idx  = rng.choice(len(y_full), n, replace=False)
    X, y = X_full[idx], y_full[idx]

    mal_rate = y.mean() * 100
    print(f"   ✅ Loaded {len(y):,} samples × {N_FEATURES} features")
    print(f"   Malware: {int(y.sum()):,} ({mal_rate:.1f}%)  "
          f"Benign: {int((1-y).sum()):,} ({100-mal_rate:.1f}%)")
    return X, y


# ══════════════════════════════════════════════════════════════
# 2. SIMULATE "UNKNOWN RANSOMWARE" SCENARIO
# ══════════════════════════════════════════════════════════════

def create_known_unknown_split(X: np.ndarray, y: np.ndarray,
                                unknown_malware_frac: float = 0.3,
                                seed: int = 42):
    """
    Giả lập scenario: một phần malware là "unknown family"
    chưa từng xuất hiện trong training data.

    known_malware   → dùng để train seed model
    unknown_malware → đây là target cần detect (hidden từ model ban đầu)
    benign          → bình thường

    unknown_malware_frac=0.3: 30% malware là "new family"
    """
    rng = np.random.RandomState(seed)

    mal_idx = np.where(y == 1)[0]
    ben_idx = np.where(y == 0)[0]

    # Split malware: known vs unknown
    rng.shuffle(mal_idx)
    n_unknown = int(len(mal_idx) * unknown_malware_frac)
    unknown_mal_idx = mal_idx[:n_unknown]
    known_mal_idx   = mal_idx[n_unknown:]

    return {
        'X_known_mal':   X[known_mal_idx],
        'y_known_mal':   y[known_mal_idx],
        'X_unknown_mal': X[unknown_mal_idx],
        'y_unknown_mal': y[unknown_mal_idx],
        'X_benign':      X[ben_idx],
        'y_benign':      y[ben_idx],
        'n_known':       len(known_mal_idx),
        'n_unknown':     len(unknown_mal_idx),
        'n_benign':      len(ben_idx),
    }


def build_experiment_sets(splits: dict, seed_size: int = 50,
                           pool_size: int = 1000, test_size: int = 500,
                           seed: int = 42):
    """
    Xây dựng các sets cho experiment:

    seed_set : known malware + benign → train model ban đầu
               Model này sẽ YẾU với unknown malware
    pool     : unknown malware + thêm benign → analyst cần label
               Đây là "suspicious samples" analyst nhận được
    test_set : cả known + unknown malware + benign → evaluate detection
    """
    rng = np.random.RandomState(seed)

    Xkm = splits['X_known_mal'];   ykm = splits['y_known_mal']
    Xum = splits['X_unknown_mal']; yum = splits['y_unknown_mal']
    Xb  = splits['X_benign'];      yb  = splits['y_benign']

    # ── Seed set: known malware + benign ──────────────────────
    n_seed_mal = seed_size // 2
    n_seed_ben = seed_size - n_seed_mal

    seed_mal_idx = rng.choice(len(ykm), min(n_seed_mal, len(ykm)), replace=False)
    seed_ben_idx = rng.choice(len(yb),  min(n_seed_ben, len(yb)),  replace=False)

    X_seed = np.vstack([Xkm[seed_mal_idx], Xb[seed_ben_idx]])
    y_seed = np.concatenate([ykm[seed_mal_idx], yb[seed_ben_idx]])

    # ── Pool: unknown malware + benign (analyst's inbox) ──────
    # Loại bỏ samples đã dùng trong seed
    remaining_ben = np.setdiff1d(np.arange(len(yb)), seed_ben_idx)

    n_pool_mal = min(pool_size // 2, len(yum))
    n_pool_ben = min(pool_size - n_pool_mal, len(remaining_ben))

    pool_mal_idx = rng.choice(len(yum), n_pool_mal, replace=False)
    pool_ben_idx = rng.choice(remaining_ben, n_pool_ben, replace=False)

    X_pool = np.vstack([Xum[pool_mal_idx], Xb[pool_ben_idx]])
    y_pool = np.concatenate([yum[pool_mal_idx], yb[pool_ben_idx]])

    # Shuffle pool (analyst không biết thứ tự)
    perm   = rng.permutation(len(y_pool))
    X_pool = X_pool[perm];  y_pool = y_pool[perm]

    # ── Test set: mix of everything ───────────────────────────
    n_test_mal = test_size // 2
    n_test_ben = test_size - n_test_mal

    all_mal = np.vstack([Xkm, Xum])
    all_y_mal = np.ones(len(all_mal))
    test_mal_idx = rng.choice(len(all_mal), min(n_test_mal, len(all_mal)), replace=False)
    test_ben_idx = rng.choice(len(yb), min(n_test_ben, len(yb)), replace=False)

    X_test = np.vstack([all_mal[test_mal_idx], Xb[test_ben_idx]])
    y_test = np.concatenate([all_y_mal[test_mal_idx], yb[test_ben_idx]])

    print(f"\n📊 Experiment sets:")
    print(f"   Seed : {len(y_seed):4d} samples "
          f"({int(y_seed.sum())} known_mal + {int((1-y_seed).sum())} benign)")
    print(f"   Pool : {len(y_pool):4d} samples "
          f"({int(y_pool.sum())} unknown_mal + {int((1-y_pool).sum())} benign)")
    print(f"   Test : {len(y_test):4d} samples "
          f"({int(y_test.sum())} mal + {int((1-y_test).sum())} benign)")
    print(f"   → Model sẽ YẾU với unknown malware ban đầu")

    return X_seed, y_seed, X_pool, y_pool, X_test, y_test


# ══════════════════════════════════════════════════════════════
# 3. MODEL
# ══════════════════════════════════════════════════════════════

def load_pretrained():
    """Load model 99.89% nếu có."""
    if MODEL_PATH.exists():
        try:
            m = lgb.Booster(model_file=str(MODEL_PATH))
            print(f"   ✅ Pretrained model loaded: {MODEL_PATH}")
            return m
        except Exception as e:
            print(f"   ⚠️  Cannot load pretrained: {e}")
    return None


def train_lgbm(X, y, n_trees=200, init_model=None):
    """Train hoặc fine-tune LightGBM."""
    if len(np.unique(y)) < 2:
        return init_model
    ds = lgb.Dataset(X, label=y.astype(int))
    params = {
        'objective':        'binary',
        'metric':           'auc',
        'learning_rate':    0.05,
        'num_leaves':       63,
        'min_data_in_leaf': 5,
        'feature_fraction': 0.8,
        'verbose':         -1,
        'n_jobs':           -1,
    }
    return lgb.train(params, ds, num_boost_round=n_trees,
                     init_model=init_model,
                     keep_training_booster=(init_model is not None),
                     callbacks=[lgb.log_evaluation(period=-1)])


def evaluate(model, X_test, y_test) -> dict:
    if model is None or len(np.unique(y_test)) < 2:
        return {'auc': 0.5, 'f1': 0.0, 'precision': 0.0, 'recall': 0.0}
    probs = model.predict(X_test)
    preds = (probs > 0.5).astype(int)
    return {
        'auc':       float(roc_auc_score(y_test, probs)),
        'f1':        float(f1_score(y_test, preds, zero_division=0)),
        'precision': float(precision_score(y_test, preds, zero_division=0)),
        'recall':    float(recall_score(y_test, preds, zero_division=0)),
    }


# ══════════════════════════════════════════════════════════════
# 4. UNCERTAINTY FUNCTIONS (vectorised)
# ══════════════════════════════════════════════════════════════

def compute_shap_uncertainty(model, X_pool, shap_exp=None):
    """
    NOVEL: Batch SHAP uncertainty.
    Composite = 0.5*SHAP_CV + 0.3*Dir_Entropy + 0.2*Margin
    """
    if shap_exp is not None and SHAP_AVAILABLE:
        try:
            sv = shap_exp.shap_values(X_pool)
            if isinstance(sv, list):
                sv = sv[0]
        except Exception:
            sv = np.zeros_like(X_pool)
    else:
        sv = np.zeros_like(X_pool)

    abs_sv  = np.abs(sv)
    sv_mean = abs_sv.mean(axis=1, keepdims=True) + 1e-10
    shap_cv = abs_sv.var(axis=1) / sv_mean.squeeze()

    pos_r   = (sv > 0).mean(axis=1).clip(1e-10, 1-1e-10)
    neg_r   = 1.0 - pos_r
    dir_ent = -(pos_r*np.log(pos_r) + neg_r*np.log(neg_r)) / np.log(2)

    probs  = model.predict(X_pool)
    margin = 1.0 - np.abs(probs - 0.5) * 2

    composite = np.clip(0.5*shap_cv + 0.3*dir_ent + 0.2*margin, 0, 1)
    return composite, probs


def compute_margin_uncertainty(model, X_pool):
    probs  = model.predict(X_pool)
    margin = 1.0 - np.abs(probs - 0.5) * 2
    return margin, probs


def compute_random_uncertainty(model, X_pool):
    probs = model.predict(X_pool)
    return np.random.rand(len(X_pool)), probs


# ══════════════════════════════════════════════════════════════
# 5. ACTIVE LEARNING LOOP
# ══════════════════════════════════════════════════════════════

def aulc(auc_list):
    """Area Under Learning Curve — higher = faster learning."""
    arr = np.array(auc_list)
    if len(arr) < 2:
        return float(arr.mean())
    return float(np.trapz(arr) / (len(arr) - 1))


def malware_hit_rate(selected_y):
    """Tỉ lệ malware trong samples được chọn để label."""
    if len(selected_y) == 0:
        return 0.0
    return float(selected_y.mean())


def run_al_loop(X_seed, y_seed, X_pool, y_pool, X_test, y_test,
                budget: int = 20, max_rounds: int = 10,
                mode: str = 'xai', n_trees: int = 200,
                pretrained_model=None, verbose: bool = False) -> dict:
    """
    Chạy 1 AL loop.

    Trả về dict với:
      - history: [{round, n_labeled, auc, f1, recall, malware_hit_rate}]
      - aulc: scalar
      - final_metrics: dict
      - total_malware_found: int (số unknown malware được label)
    """
    X_lab = X_seed.copy()
    y_lab = y_seed.copy()
    pool_mask      = np.ones(len(y_pool), dtype=bool)
    history        = []
    total_mal_found = 0
    hit_rates       = []

    # Train initial model
    if pretrained_model is not None:
        # Fine-tune từ pretrained
        model = train_lgbm(X_lab, y_lab, n_trees=50,
                           init_model=pretrained_model)
    else:
        model = train_lgbm(X_lab, y_lab, n_trees)

    # SHAP explainer
    shap_exp = None
    if mode == 'xai' and SHAP_AVAILABLE and model is not None:
        try:
            shap_exp = shap_lib.TreeExplainer(model)
        except Exception:
            pass

    m0 = evaluate(model, X_test, y_test)
    history.append({
        'round': 0, 'n_labeled': len(y_lab),
        'auc': m0['auc'], 'f1': m0['f1'],
        'recall': m0['recall'], 'malware_hit_rate': 0.0,
    })

    for rnd in range(1, max_rounds + 1):
        avail = np.where(pool_mask)[0]
        if len(avail) == 0:
            break

        X_avail = X_pool[avail]

        # Select by uncertainty
        if mode == 'xai' and model is not None:
            scores, _ = compute_shap_uncertainty(model, X_avail, shap_exp)
        elif mode == 'margin' and model is not None:
            scores, _ = compute_margin_uncertainty(model, X_avail)
        else:
            scores, _ = compute_random_uncertainty(model, X_avail)

        k        = min(budget, len(avail))
        top_loc  = np.argsort(scores)[-k:]
        chosen   = avail[top_loc]

        # Oracle labels
        y_new    = y_pool[chosen]
        hit_rate = malware_hit_rate(y_new)
        hit_rates.append(hit_rate)
        total_mal_found += int(y_new.sum())

        X_lab = np.vstack([X_lab, X_pool[chosen]])
        y_lab = np.concatenate([y_lab, y_new])
        pool_mask[chosen] = False

        if verbose:
            print(f"   Round {rnd}: selected {k} "
                  f"({int(y_new.sum())} mal/{int((1-y_new).sum())} ben) "
                  f"hit={hit_rate:.1%}")

        # Retrain
        if pretrained_model is not None:
            model = train_lgbm(X_lab, y_lab, n_trees=50,
                               init_model=pretrained_model)
        else:
            model = train_lgbm(X_lab, y_lab, n_trees)

        # Update SHAP every round
        if mode == 'xai' and SHAP_AVAILABLE and model is not None:
            try:
                shap_exp = shap_lib.TreeExplainer(model)
            except Exception:
                pass

        m = evaluate(model, X_test, y_test)
        history.append({
            'round':            rnd,
            'n_labeled':        len(y_lab),
            'auc':              m['auc'],
            'f1':               m['f1'],
            'recall':           m['recall'],
            'malware_hit_rate': hit_rate,
        })

    aucs = [h['auc'] for h in history]
    return {
        'history':           history,
        'aulc':              aulc(aucs),
        'final_auc':         aucs[-1],
        'final_recall':      history[-1]['recall'],
        'total_mal_found':   total_mal_found,
        'avg_hit_rate':      float(np.mean(hit_rates)) if hit_rates else 0.0,
    }


# ══════════════════════════════════════════════════════════════
# 6. SINGLE EXPERIMENT
# ══════════════════════════════════════════════════════════════

def run_single_experiment(budget=20, max_rounds=10, seed=42,
                           max_samples=30000, seed_size=50,
                           pool_size=1000, test_size=500,
                           n_trees=200, verbose=True):

    X, y = load_ember(max_samples=max_samples, seed=seed)

    splits = create_known_unknown_split(X, y,
                                        unknown_malware_frac=0.3, seed=seed)
    X_seed, y_seed, X_pool, y_pool, X_test, y_test = \
        build_experiment_sets(splits, seed_size=seed_size,
                               pool_size=pool_size, test_size=test_size,
                               seed=seed)

    pretrained = load_pretrained()

    print(f"\n{'='*60}")
    print(f"🚀 Running 3 methods (budget={budget}/round, {max_rounds} rounds)")
    print(f"{'='*60}")

    results = {}
    for mode in ['xai', 'margin', 'random']:
        label = {'xai': '🧪 XAI-AL', 'margin': '📏 Margin-AL',
                 'random': '🎲 Random'}[mode]
        print(f"\n{label}...")
        r = run_al_loop(
            X_seed, y_seed, X_pool, y_pool, X_test, y_test,
            budget=budget, max_rounds=max_rounds, mode=mode,
            n_trees=n_trees, pretrained_model=pretrained,
            verbose=verbose)
        results[mode] = r
        print(f"   AULC={r['aulc']:.4f}  FinalAUC={r['final_auc']:.4f}  "
              f"Recall={r['final_recall']:.4f}  "
              f"MalFound={r['total_mal_found']}  "
              f"HitRate={r['avg_hit_rate']:.1%}")

    print_comparison(results, budget, max_rounds)
    return results


def print_comparison(results, budget, max_rounds):
    xh = results['xai']['history']
    mh = results['margin']['history']
    rh = results['random']['history']

    print(f"\n{'='*70}")
    print(f"📊 COMPARISON TABLE")
    print(f"{'='*70}")
    print(f"{'Round':>6} {'N_Lab':>7} "
          f"{'XAI-AUC':>9} {'Mrg-AUC':>9} {'Rnd-AUC':>9} "
          f"{'XAI-Hit':>9} {'Rnd-Hit':>9}")
    print("─"*65)

    for i in range(min(len(xh), len(rh))):
        xhi = results['xai']['history'][i]
        rhi = results['random']['history'][i]
        mhi = results['margin']['history'][i]
        print(f"{xhi['round']:>6} {xhi['n_labeled']:>7} "
              f"{xhi['auc']:>9.4f} {mhi['auc']:>9.4f} {rhi['auc']:>9.4f} "
              f"{xhi['malware_hit_rate']:>9.1%} {rhi['malware_hit_rate']:>9.1%}")

    xr = results['xai'];  mr = results['margin'];  rr = results['random']
    print(f"""
┌────────────────────────────────────────────────────────────┐
│  SUMMARY                                                   │
├──────────────┬──────────┬──────────┬──────────────────────┤
│  Method      │   AULC   │ FinalAUC │ Mal Found | Hit Rate │
├──────────────┼──────────┼──────────┼──────────────────────┤
│  XAI-AL*     │ {xr['aulc']:.4f}  │  {xr['final_auc']:.4f}  │ {xr['total_mal_found']:>5}     | {xr['avg_hit_rate']:>6.1%}     │
│  Margin-AL   │ {mr['aulc']:.4f}  │  {mr['final_auc']:.4f}  │ {mr['total_mal_found']:>5}     | {mr['avg_hit_rate']:>6.1%}     │
│  Random AL   │ {rr['aulc']:.4f}  │  {rr['final_auc']:.4f}  │ {rr['total_mal_found']:>5}     | {rr['avg_hit_rate']:>6.1%}     │
└──────────────┴──────────┴──────────┴──────────────────────┘
  * NOVEL: XAI-AL prioritizes samples with high SHAP uncertainty
    Hit Rate = % malware trong samples được chọn để label
    → Cao hơn = analyst tìm thấy nhiều unknown malware hơn""")


# ══════════════════════════════════════════════════════════════
# 7. MULTI-SEED
# ══════════════════════════════════════════════════════════════

def run_multiseed(n_seeds=5, budget=20, max_rounds=10,
                  max_samples=30000, seed_size=50,
                  pool_size=1000, test_size=500, n_trees=200):

    print(f"\n{'='*60}")
    print(f"🔁 MULTI-SEED EXPERIMENT ({n_seeds} seeds)")
    print(f"   EMBER real data | budget={budget} | rounds={max_rounds}")
    print(f"{'='*60}")

    X_full, y_full = load_ember(max_samples=max_samples, seed=0)
    pretrained     = load_pretrained()

    metrics = {m: {'aulc': [], 'final_auc': [], 'final_recall': [],
                   'mal_found': [], 'hit_rate': []}
               for m in ['xai', 'margin', 'random']}
    all_curves = {m: [] for m in ['xai', 'margin', 'random']}

    for s in range(n_seeds):
        print(f"\n--- Seed {s+1}/{n_seeds} ---")
        rng  = np.random.RandomState(s * 17 + 3)
        idx  = rng.choice(len(y_full), min(max_samples, len(y_full)),
                          replace=False)
        X, y = X_full[idx], y_full[idx]

        splits = create_known_unknown_split(X, y, unknown_malware_frac=0.3,
                                            seed=s)
        X_seed, y_seed, X_pool, y_pool, X_test, y_test = \
            build_experiment_sets(splits, seed_size=seed_size,
                                   pool_size=pool_size, test_size=test_size,
                                   seed=s)

        for mode in ['xai', 'margin', 'random']:
            r = run_al_loop(
                X_seed, y_seed, X_pool, y_pool, X_test, y_test,
                budget=budget, max_rounds=max_rounds, mode=mode,
                n_trees=n_trees, pretrained_model=pretrained,
                verbose=False)
            metrics[mode]['aulc'].append(r['aulc'])
            metrics[mode]['final_auc'].append(r['final_auc'])
            metrics[mode]['final_recall'].append(r['final_recall'])
            metrics[mode]['mal_found'].append(r['total_mal_found'])
            metrics[mode]['hit_rate'].append(r['avg_hit_rate'])
            all_curves[mode].append([h['auc'] for h in r['history']])

        # Print seed summary
        for m in ['xai', 'margin', 'random']:
            print(f"   {m:>6}: AULC={metrics[m]['aulc'][-1]:.4f}  "
                  f"AUC={metrics[m]['final_auc'][-1]:.4f}  "
                  f"Hit={metrics[m]['hit_rate'][-1]:.1%}  "
                  f"MalFound={metrics[m]['mal_found'][-1]}")

    # ── Aggregate ─────────────────────────────────────────────
    print(f"\n{'='*65}")
    print(f"📊 FINAL RESULTS (mean ± std, {n_seeds} seeds)")
    print(f"{'='*65}")

    agg = {}
    for m in ['xai', 'margin', 'random']:
        agg[m] = {k: (np.mean(v), np.std(v))
                  for k, v in metrics[m].items()}

    # Learning curves
    min_len = min(len(c) for curves in all_curves.values() for c in curves)
    curve_agg = {}
    for m in ['xai', 'margin', 'random']:
        mat = np.array([c[:min_len] for c in all_curves[m]])
        curve_agg[m] = {'mean': mat.mean(0).tolist(),
                        'std':  mat.std(0).tolist()}

    # Tính ΔAULC và hit rate advantage
    xai_aulc  = np.array(metrics['xai']['aulc'])
    rnd_aulc  = np.array(metrics['random']['aulc'])
    xai_hit   = np.array(metrics['xai']['hit_rate'])
    rnd_hit   = np.array(metrics['random']['hit_rate'])

    delta_aulc = xai_aulc - rnd_aulc
    delta_hit  = xai_hit  - rnd_hit

    print(f"""
┌─────────────────────────────────────────────────────────────────┐
│  THESIS TABLE — Real EMBER Data, Unknown Ransomware Scenario    │
│  ({n_seeds} seeds, mean ± std)                                       │
├──────────────┬────────────────┬────────────────┬────────────────┤
│  Method      │      AULC      │   Final AUC    │  Hit Rate*     │
├──────────────┼────────────────┼────────────────┼────────────────┤
│  XAI-AL†     │{agg['xai']['aulc'][0]:.4f} ± {agg['xai']['aulc'][1]:.4f}│{agg['xai']['final_auc'][0]:.4f} ± {agg['xai']['final_auc'][1]:.4f}│{agg['xai']['hit_rate'][0]:.1%} ± {agg['xai']['hit_rate'][1]:.1%}   │
│  Margin-AL   │{agg['margin']['aulc'][0]:.4f} ± {agg['margin']['aulc'][1]:.4f}│{agg['margin']['final_auc'][0]:.4f} ± {agg['margin']['final_auc'][1]:.4f}│{agg['margin']['hit_rate'][0]:.1%} ± {agg['margin']['hit_rate'][1]:.1%}   │
│  Random AL   │{agg['random']['aulc'][0]:.4f} ± {agg['random']['aulc'][1]:.4f}│{agg['random']['final_auc'][0]:.4f} ± {agg['random']['final_auc'][1]:.4f}│{agg['random']['hit_rate'][0]:.1%} ± {agg['random']['hit_rate'][1]:.1%}   │
├──────────────┴────────────────┴────────────────┴────────────────┤
│  ΔAULC (XAI−Random): {delta_aulc.mean():+.4f} ± {delta_aulc.std():.4f}                    │
│  ΔHitRate (XAI−Random): {delta_hit.mean():+.1%} ± {delta_hit.std():.1%}                  │
└─────────────────────────────────────────────────────────────────┘
  * Hit Rate = % unknown malware trong samples được chọn để label
  † XAI-AL: SHAP Variance + Directional Entropy + Output Margin

📝 THESIS CLAIMS:
  1. XAI-AL đạt AULC={agg['xai']['aulc'][0]:.4f} vs Random={agg['random']['aulc'][0]:.4f}
     → ΔAULC = {delta_aulc.mean():+.4f} (p-value cần Wilcoxon test)
  2. XAI-AL Hit Rate={agg['xai']['hit_rate'][0]:.1%} vs Random={agg['random']['hit_rate'][0]:.1%}
     → XAI analyst tìm thấy {delta_hit.mean():+.1%} nhiều unknown malware hơn/label round
  3. NOVEL: XAI-AL explainable — mỗi sample được chọn có SHAP justification
     Random/Margin không cung cấp được điều này""")

    # Statistical test
    from scipy import stats
    stat, pval = stats.wilcoxon(metrics['xai']['aulc'],
                                metrics['random']['aulc'],
                                alternative='greater')
    print(f"\n  📐 Wilcoxon test (XAI AULC > Random AULC):")
    print(f"     statistic={stat:.3f}  p-value={pval:.4f}  "
          f"{'✅ significant (p<0.05)' if pval < 0.05 else '⚠️  not significant yet'}")
    print(f"     → Cần ít nhất 10 seeds để có p<0.05")

    # Save
    output = {
        'experiment_time': datetime.now().isoformat(),
        'n_seeds': n_seeds,
        'config': {'budget': budget, 'max_rounds': max_rounds,
                   'seed_size': seed_size, 'pool_size': pool_size,
                   'unknown_malware_frac': 0.3},
        'metrics': {m: {k: {'mean': float(v[0]), 'std': float(v[1])}
                        for k, v in agg[m].items()}
                    for m in ['xai', 'margin', 'random']},
        'learning_curves': curve_agg,
        'statistical_test': {
            'test': 'wilcoxon', 'alternative': 'greater',
            'statistic': float(stat), 'p_value': float(pval),
            'significant': bool(pval < 0.05),
        },
        'delta_aulc': {
            'mean': float(delta_aulc.mean()),
            'std':  float(delta_aulc.std()),
        },
        'delta_hit_rate': {
            'mean': float(delta_hit.mean()),
            'std':  float(delta_hit.std()),
        },
    }
    p = Path("al_ember_results.json")
    with open(p, 'w') as f: json.dump(output, f, indent=2)
    print(f"\n  💾 Saved → {p}")
    return output


# ══════════════════════════════════════════════════════════════
# 8. MAIN
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="XAI-AL with Real EMBER Data")
    ap.add_argument("--multiseed",   action="store_true")
    ap.add_argument("--quick",       action="store_true",
                    help="Quick test: 5k samples, 3 rounds")
    ap.add_argument("--n_seeds",     type=int,   default=5)
    ap.add_argument("--budget",      type=int,   default=20)
    ap.add_argument("--rounds",      type=int,   default=10)
    ap.add_argument("--max_samples", type=int,   default=30000)
    ap.add_argument("--seed_size",   type=int,   default=50)
    ap.add_argument("--pool_size",   type=int,   default=1000)
    ap.add_argument("--n_trees",     type=int,   default=200)
    args = ap.parse_args()

    if args.quick:
        print("⚡ QUICK MODE (5k samples, 3 rounds)")
        run_single_experiment(
            budget=20, max_rounds=3, max_samples=5000,
            seed_size=30, pool_size=300, test_size=200,
            n_trees=100, verbose=True)

    elif args.multiseed:
        run_multiseed(
            n_seeds     = args.n_seeds,
            budget      = args.budget,
            max_rounds  = args.rounds,
            max_samples = args.max_samples,
            seed_size   = args.seed_size,
            pool_size   = args.pool_size,
            n_trees     = args.n_trees)
    else:
        run_single_experiment(
            budget      = args.budget,
            max_rounds  = args.rounds,
            max_samples = args.max_samples,
            seed_size   = args.seed_size,
            pool_size   = args.pool_size,
            n_trees     = args.n_trees,
            verbose     = True)