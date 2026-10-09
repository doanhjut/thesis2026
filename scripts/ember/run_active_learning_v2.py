"""
run_active_learning_v2.py
=========================
Fixes so với v1:
  FIX 1: Retrain dùng TOÀN BỘ _X_labeled (không chỉ batch mới 20 samples)
  FIX 2: Oracle mapping dùng dict {sample_id -> pool_index} (tránh shuffle bug)
  FIX 3: Plateau check chỉ sau round 4 (không dừng sớm khi AUC=0)
  FIX 4: Baseline dùng model gốc predict trực tiếp (không qua retrainer stub)

Chạy:
    python run_active_learning_v2.py --mode synthetic
    python run_active_learning_v2.py --mode ember --data_dir .
"""

import numpy as np
import json
import time
import heapq
import argparse
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional
from sklearn.metrics import roc_auc_score, f1_score, precision_score, recall_score
import lightgbm as lgb

from xai_explainer import RansomwareExplainer

MODEL_PATH = "ransomware_lgbm_1M_final.txt"


# ══════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ══════════════════════════════════════════════════════════════

@dataclass
class SampleRecord:
    sample_id:     str
    features:      np.ndarray
    uncertainty:   float = 0.0
    shap_variance: float = 0.0
    margin_score:  float = 0.0
    is_labeled:    bool  = False
    true_label:    Optional[int] = None
    labeled_at_round: Optional[int] = None

    def __lt__(self, other):
        return self.uncertainty > other.uncertainty


@dataclass
class ALRound:
    round_number:    int
    n_labeled:       int
    auc_score:       float
    f1_score:        float
    precision:       float
    recall:          float
    samples_queried: list
    uncertainty_scores: list
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# ══════════════════════════════════════════════════════════════
# SHAP UNCERTAINTY (real model)
# ══════════════════════════════════════════════════════════════

class SHAPUncertaintyEstimator:
    """
    NOVEL: Uncertainty từ SHAP variance, không phải output entropy.
    """

    def __init__(self, explainer: RansomwareExplainer):
        self.explainer = explainer
        self._cache    = {}
        print("   SHAP Uncertainty Estimator (real LightGBM+SHAP) ready")

    def compute(self, features: np.ndarray, sample_id: str = None) -> dict:
        if sample_id and sample_id in self._cache:
            return self._cache[sample_id]
        result = self._compute(features)
        if sample_id:
            self._cache[sample_id] = result
        return result

    def _compute(self, features: np.ndarray) -> dict:
        try:
            r           = self.explainer.explain_features(features, top_n=50)
            shap_values = np.array(r['shap_values'])
        except Exception:
            shap_values = np.zeros(len(features))

        abs_shap  = np.abs(shap_values)
        shap_mean = abs_shap.mean() + 1e-10
        shap_var  = float(abs_shap.var())
        shap_cv   = shap_var / shap_mean

        pos_ratio = float((shap_values > 0).mean())
        neg_ratio = 1.0 - pos_ratio
        eps       = 1e-10
        dir_ent   = float(-(pos_ratio * np.log(pos_ratio + eps) +
                             neg_ratio * np.log(neg_ratio + eps)) / np.log(2))

        prob   = float(self.explainer.predict_from_features(features))
        margin = float(1.0 - abs(prob - 0.5) * 2)

        composite = float(np.clip(0.5 * shap_cv + 0.3 * dir_ent + 0.2 * margin, 0, 1))

        return {
            'shap_variance':         shap_var,
            'shap_cv':               float(shap_cv),
            'directional_entropy':   dir_ent,
            'output_margin':         margin,
            'probability':           prob,
            'composite_uncertainty': composite,
        }


# ══════════════════════════════════════════════════════════════
# PRIORITY QUEUE
# ══════════════════════════════════════════════════════════════

class UncertaintyPQ:
    def __init__(self):
        self._heap    = []
        self._samples = {}
        self._labeled = set()

    def add(self, rec: SampleRecord):
        self._samples[rec.sample_id] = rec
        heapq.heappush(self._heap, (-rec.uncertainty, rec.sample_id))

    def pop_top(self, n: int) -> list:
        out = []
        while self._heap and len(out) < n:
            _, sid = heapq.heappop(self._heap)
            if sid in self._labeled:
                continue
            rec = self._samples.get(sid)
            if rec and not rec.is_labeled:
                out.append(rec)
        return out

    def mark_labeled(self, sid: str, label: int, rnd: int):
        if sid in self._samples:
            r = self._samples[sid]
            r.is_labeled = True
            r.true_label = label
            r.labeled_at_round = rnd
            self._labeled.add(sid)

    @property
    def n_unlabeled(self): return len(self._samples) - len(self._labeled)
    @property
    def n_labeled(self):   return len(self._labeled)


# ══════════════════════════════════════════════════════════════
# RETRAINER — FIX 1: train trên FULL labeled set
# ══════════════════════════════════════════════════════════════

class Retrainer:
    """
    FIX 1: Mỗi round train trên TOÀN BỘ X_labeled (seed + tất cả labeled mới).
    init_model = base_model: fine-tune từ model 1M-sample gốc.
    """

    def __init__(self, base_model: lgb.Booster, n_trees: int = 30):
        self.base_model    = base_model
        self.current_model = base_model
        self.n_trees       = n_trees
        print(f"   Retrainer: fine-tune {n_trees} trees trên full labeled set mỗi round")

    def retrain(self, X_all: np.ndarray, y_all: np.ndarray, rnd: int) -> bool:
        if len(np.unique(y_all)) < 2:
            print(f"   ⚠️  Round {rnd}: cần cả 2 class để train (hiện tại chỉ có 1)")
            return False
        try:
            ds = lgb.Dataset(X_all, label=y_all.astype(int))
            params = {
                'objective':        'binary',
                'metric':           'auc',
                'learning_rate':    0.05,
                'num_leaves':       31,
                'min_data_in_leaf': 5,
                'verbose':         -1,
            }
            self.current_model = lgb.train(
                params, ds,
                num_boost_round       = self.n_trees,
                init_model            = self.base_model,
                keep_training_booster = True,
            )
            return True
        except Exception as e:
            print(f"   ⚠️  Retrain error: {e}")
            return False

    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> dict:
        if len(np.unique(y_test)) < 2:
            return {'auc': 0.0, 'f1': 0.0, 'precision': 0.0, 'recall': 0.0}
        try:
            probs = self.current_model.predict(X_test)
            preds = (probs > 0.5).astype(int)
            return {
                'auc':       float(roc_auc_score(y_test, probs)),
                'f1':        float(f1_score(y_test, preds, zero_division=0)),
                'precision': float(precision_score(y_test, preds, zero_division=0)),
                'recall':    float(recall_score(y_test, preds, zero_division=0)),
            }
        except Exception as e:
            print(f"   ⚠️  Evaluate error: {e}")
            return {'auc': 0.0, 'f1': 0.0, 'precision': 0.0, 'recall': 0.0}


# ══════════════════════════════════════════════════════════════
# XAI ACTIVE LEARNER (fixed)
# ══════════════════════════════════════════════════════════════

class XAIActiveLearner:

    def __init__(self, estimator: SHAPUncertaintyEstimator,
                 retrainer: Retrainer,
                 budget: int = 20, max_rounds: int = 8, plateau: float = 0.002):
        self.estimator  = estimator
        self.retrainer  = retrainer
        self.budget     = budget
        self.max_rounds = max_rounds
        self.plateau    = plateau
        self.pq         = UncertaintyPQ()
        self.history: list = []
        self._X_labeled = None
        self._y_labeled = None
        self._id_to_idx = {}   # FIX 2: sample_id -> pool index

        print(f"\n{'='*60}")
        print(f"🎓 XAI-GUIDED ACTIVE LEARNER (v2 — fixed)")
        print(f"   budget={budget}  max_rounds={max_rounds}  plateau={plateau}")

    def initialize(self, X_pool, y_pool_oracle, X_seed, y_seed):
        self._X_labeled    = X_seed.copy()
        self._y_labeled    = y_seed.copy()
        self._y_pool_oracle = y_pool_oracle

        print(f"\n📦 Pool={len(X_pool)}  Seed={len(y_seed)} "
              f"({int(y_seed.sum())} mal / {int((1-y_seed).sum())} ben)")
        print("   Computing SHAP uncertainty (~2min for 1400 samples)...")
        t0 = time.time()

        for i, feat in enumerate(X_pool):
            sid = f"s_{i:05d}"
            self._id_to_idx[sid] = i    # FIX 2
            unc = self.estimator.compute(feat, sid)
            self.pq.add(SampleRecord(
                sample_id    = sid,
                features     = feat,
                uncertainty  = unc['composite_uncertainty'],
                shap_variance = unc['shap_variance'],
                margin_score  = unc['output_margin'],
            ))
            if (i+1) % 200 == 0:
                ela = time.time() - t0
                eta = ela/(i+1)*(len(X_pool)-i-1)
                print(f"   {i+1}/{len(X_pool)} | {ela:.0f}s elapsed | ETA {eta:.0f}s")

        print(f"   Done in {time.time()-t0:.1f}s")

    def run(self, X_test, y_test) -> list:
        print(f"\n🚀 AL loop (max {self.max_rounds} rounds)")

        # FIX 4: baseline từ model gốc trực tiếp
        baseline = self.retrainer.evaluate(X_test, y_test)
        print(f"📊 BASELINE (model gốc): AUC={baseline['auc']:.4f}  F1={baseline['f1']:.4f}")
        prev_auc = baseline['auc']

        for rnd in range(1, self.max_rounds + 1):
            print(f"\n{'─'*55}")
            print(f"ROUND {rnd}/{self.max_rounds} | labeled={self.pq.n_labeled} | unlabeled={self.pq.n_unlabeled}")

            selected = self.pq.pop_top(self.budget)
            if not selected:
                print("   Pool exhausted")
                break

            unc_sc = [s.uncertainty for s in selected]
            print(f"   Selected {len(selected)} | unc mean={np.mean(unc_sc):.3f} max={np.max(unc_sc):.3f}")

            # FIX 2: oracle dùng dict mapping
            new_X    = np.vstack([s.features for s in selected])
            pool_idx = [self._id_to_idx[s.sample_id] for s in selected]
            new_y    = self._y_pool_oracle[pool_idx]
            print(f"   Oracle: {int(new_y.sum())} malware / {int((1-new_y).sum())} benign")

            for s, lbl in zip(selected, new_y):
                self.pq.mark_labeled(s.sample_id, int(lbl), rnd)

            # FIX 1: accumulate full labeled set
            self._X_labeled = np.vstack([self._X_labeled, new_X])
            self._y_labeled = np.concatenate([self._y_labeled, new_y])

            ok = self.retrainer.retrain(self._X_labeled, self._y_labeled, rnd)
            m  = self.retrainer.evaluate(X_test, y_test)
            print(f"   AUC={m['auc']:.4f}  F1={m['f1']:.4f}  "
                  f"Prec={m['precision']:.4f}  Rec={m['recall']:.4f}")

            self.history.append(ALRound(
                round_number=rnd, n_labeled=self.pq.n_labeled,
                auc_score=m['auc'], f1_score=m['f1'],
                precision=m['precision'], recall=m['recall'],
                samples_queried=[s.sample_id for s in selected],
                uncertainty_scores=unc_sc,
            ))

            # FIX 3: plateau chỉ check sau round 4
            delta = m['auc'] - prev_auc
            if rnd >= 4 and abs(delta) < self.plateau:
                print(f"   Plateau ΔAUC={delta:.5f} → early stop")
                break
            prev_auc = m['auc']

        print(f"\n{'='*55}")
        print(f"XAI-AL DONE: {len(self.history)} rounds")
        print(f"{'Round':>6} {'N_Lab':>7} {'AUC':>8} {'F1':>8}")
        print("─"*32)
        for r in self.history:
            print(f"{r.round_number:>6} {r.n_labeled:>7} {r.auc_score:>8.4f} {r.f1_score:>8.4f}")
        return self.history


# ══════════════════════════════════════════════════════════════
# RANDOM BASELINE
# ══════════════════════════════════════════════════════════════

def run_random_baseline(base_model, X_seed, y_seed, X_pool, y_pool,
                        X_test, y_test, budget=20, max_rounds=8):
    print(f"\n{'='*55}")
    print(f"RANDOM SAMPLING BASELINE")
    retrainer = Retrainer(base_model)
    X_lab = X_seed.copy();  y_lab = y_seed.copy()
    perm  = np.random.permutation(len(y_pool));  ptr = 0
    hist  = []

    for rnd in range(1, max_rounds+1):
        chosen = perm[ptr:ptr+budget];  ptr += budget
        if len(chosen) == 0:
            break
        X_lab = np.vstack([X_lab, X_pool[chosen]])
        y_lab = np.concatenate([y_lab, y_pool[chosen]])
        retrainer.retrain(X_lab, y_lab, rnd)
        m = retrainer.evaluate(X_test, y_test)
        print(f"   Round {rnd}: n={len(y_lab):4d}  AUC={m['auc']:.4f}  F1={m['f1']:.4f}")
        hist.append({'round': rnd, 'n_labeled': len(y_lab),
                     'auc': m['auc'], 'f1': m['f1']})
    return hist


# ══════════════════════════════════════════════════════════════
# COMPARE + SAVE
# ══════════════════════════════════════════════════════════════

def compare_and_save(xai_hist, rnd_hist, data_info, config):
    xa = [r.auc_score  for r in xai_hist];  xn = [r.n_labeled   for r in xai_hist]
    ra = [h['auc']     for h in rnd_hist];  rn = [h['n_labeled'] for h in rnd_hist]
    mn = min(len(xa), len(ra))

    print(f"\n{'='*55}")
    print(f"COMPARISON: XAI-AL vs Random")
    print(f"{'Round':>6} {'XAI-AUC':>9} {'Rnd-AUC':>9} {'Δ':>8}")
    print("─"*34)
    for i in range(mn):
        print(f"{i+1:>6} {xa[i]:>9.4f} {ra[i]:>9.4f} {xa[i]-ra[i]:>+8.4f}")

    max_auc = max(max(xa, default=0), max(ra, default=0))
    target  = max_auc * 0.90

    def eff(aucs, ns):
        for a, n in zip(aucs, ns):
            if a >= target: return n
        return ns[-1] if ns else 9999

    xe = eff(xa, xn);  re = eff(ra, rn)
    sv = (re - xe) / max(re, 1) * 100

    print(f"\n  90% AUC target ({target:.4f}): XAI={xe}  Random={re}  Saving={sv:.1f}%")

    print(f"""
╔══════════════════════════════════════════════════════╗
║  THESIS TABLE                                        ║
╠══════════════════════════════════════════════════════╣
║  Metric              XAI-AL        Random            ║
║  Final AUC       {xa[-1] if xa else 0:.4f}          {ra[-1] if ra else 0:.4f}            ║
║  Labels to 90%   {xe:<14}{re:<14}  ║
║  Label saving    {sv:.1f}%                               ║
╚══════════════════════════════════════════════════════╝""")

    out = {
        'experiment_time': datetime.now().isoformat(),
        'data_info': data_info, 'config': config,
        'xai_history':    [{'round': r.round_number, 'n_labeled': r.n_labeled,
                             'auc': r.auc_score, 'f1': r.f1_score} for r in xai_hist],
        'random_history': rnd_hist,
        'comparison': {'xai_final_auc': xa[-1] if xa else 0,
                       'random_final_auc': ra[-1] if ra else 0,
                       'xai_efficiency': xe, 'random_efficiency': re,
                       'label_saving_pct': sv},
    }
    p = Path("al_results_v2.json")
    with open(p, 'w') as f: json.dump(out, f, indent=2)
    print(f"\n  Saved → {p}")
    return out


# ══════════════════════════════════════════════════════════════
# DATA HELPERS
# ══════════════════════════════════════════════════════════════

def generate_synthetic(n=2000, n_feat=2381):
    print(f"\n  Synthetic: {n} samples x {n_feat} features")
    np.random.seed(42)
    n_mal = n//2;  n_ben = n-n_mal
    idx = np.random.choice(n_feat, min(200, n_feat), replace=False)
    sig = np.random.choice(n_feat, min(50, n_feat),  replace=False)

    X_ben = np.zeros((n_ben, n_feat))
    X_ben[:, idx] = np.random.exponential(0.1, (n_ben, len(idx)))

    X_mal = np.zeros((n_mal, n_feat))
    X_mal[:, idx] = np.random.exponential(0.1, (n_mal, len(idx)))
    X_mal[:, sig] += np.random.exponential(0.8, (n_mal, len(sig)))

    X = np.vstack([X_ben, X_mal])
    y = np.array([0]*n_ben + [1]*n_mal, dtype=float)
    p = np.random.permutation(n)
    return X[p], y[p]


def load_ember(data_dir, max_samples=2000):
    dp = Path(data_dir)
    try:
        import ember
        Xt, yt, Xe, ye = ember.read_vectorized_features(str(dp))
        mt = yt != -1;  me = ye != -1
        X = np.vstack([Xt[mt], Xe[me]])[:max_samples]
        y = np.concatenate([yt[mt], ye[me]])[:max_samples]
        print(f"  EMBER binary: {X.shape}"); return X, y
    except Exception: pass
    for fn in ["features.npy", "features.npz"]:
        p = dp/fn
        if p.exists():
            if fn.endswith('.npz'):
                d = np.load(str(p)); X,y = d['X'][:max_samples], d['y'][:max_samples]
            else:
                X = np.load(str(p))[:max_samples]
                y = np.load(str(dp/"labels.npy"))[:max_samples]
            print(f"  {fn}: {X.shape}"); return X, y
    print("  No EMBER files → synthetic")
    return generate_synthetic(max_samples)


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode",        choices=["synthetic","ember"], default="synthetic")
    ap.add_argument("--data_dir",    default=".")
    ap.add_argument("--budget",      type=int, default=20)
    ap.add_argument("--rounds",      type=int, default=8)
    ap.add_argument("--max_samples", type=int, default=2000)
    ap.add_argument("--n_trees",     type=int, default=30)
    args = ap.parse_args()

    print(f"\n{'='*55}")
    print(f"XAI-GUIDED ACTIVE LEARNING v2")
    print(f"{'='*55}")

    explainer  = RansomwareExplainer(MODEL_PATH)
    base_model = lgb.Booster(model_file=MODEL_PATH)

    X, y = generate_synthetic(args.max_samples) if args.mode=="synthetic" \
           else load_ember(args.data_dir, args.max_samples)

    n = len(y)
    np.random.seed(0)
    perm = np.random.permutation(n)
    X, y = X[perm], y[perm]

    n_seed = max(30, int(n*0.10));  n_test = int(n*0.20)
    X_seed, y_seed = X[:n_seed],        y[:n_seed]
    X_pool, y_pool = X[n_seed:-n_test], y[n_seed:-n_test]
    X_test, y_test = X[-n_test:],       y[-n_test:]

    print(f"  Seed={len(y_seed)} Pool={len(y_pool)} Test={len(y_test)}")
    print(f"  Test: {int(y_test.sum())} mal / {int((1-y_test).sum())} ben")

    # Base model baseline
    p0 = base_model.predict(X_test)
    if len(np.unique(y_test)) > 1:
        print(f"  Base model AUC={roc_auc_score(y_test,p0):.4f}")

    estimator = SHAPUncertaintyEstimator(explainer)
    retrainer = Retrainer(base_model, args.n_trees)
    learner   = XAIActiveLearner(estimator, retrainer,
                                  args.budget, args.rounds)

    learner.initialize(X_pool, y_pool, X_seed, y_seed)
    xai_hist = learner.run(X_test, y_test)

    rnd_hist = run_random_baseline(
        base_model, X_seed, y_seed, X_pool, y_pool,
        X_test, y_test, args.budget, args.rounds)

    compare_and_save(
        xai_hist, rnd_hist,
        data_info={'n': n, 'n_seed': n_seed, 'malware_pct': float(y.mean()*100)},
        config={'budget': args.budget, 'rounds': args.rounds, 'n_trees': args.n_trees},
    )


if __name__ == "__main__":
    main()