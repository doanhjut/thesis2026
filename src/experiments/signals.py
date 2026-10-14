"""Native TreeSHAP and acquisition signals specified by the revised thesis."""
from time import perf_counter

import numpy as np

from .common import probabilities, require

METHODS = ['Random', 'Uncertainty', 'U+H', 'U+V', 'XAI_full']
WEIGHTS = {'Uncertainty': {'U': 1.0}, 'U+H': {'U': 3 / 7, 'H': 4 / 7},
           'U+V': {'U': .5, 'V': .5}, 'XAI_full': {'U': .3, 'H': .4, 'V': .3}}


def normalize(a):
    a = np.asarray(a, dtype=float)
    require(a.ndim == 1 and len(a) > 0 and np.isfinite(a).all(), 'Invalid acquisition signal.')
    span = a.max() - a.min()
    return (a - a.min()) / span if span > 0 else np.zeros_like(a)


def shap_signals(phi):
    phi = np.asarray(phi, dtype=float)
    require(phi.ndim == 2 and phi.shape[1] > 0 and np.isfinite(phi).all(), 'Invalid SHAP matrix.')
    positive = np.maximum(phi, 0).sum(axis=1)
    negative = -np.minimum(phi, 0).sum(axis=1)
    total = positive + negative
    q = np.divide(positive, total, out=np.zeros_like(total), where=total > 0)
    entropy = np.zeros(len(phi))
    mixed = (q > 0) & (q < 1)
    entropy[mixed] = -(q[mixed] * np.log2(q[mixed]) + (1 - q[mixed]) * np.log2(1 - q[mixed]))
    return entropy, phi.var(axis=1)


def native_shap(model, X, threads=2):
    booster = getattr(model, 'booster_', model)
    require(booster is not None and hasattr(booster, 'predict'), 'A fitted LightGBM model is required; no SHAP simulation.')
    t0 = perf_counter()
    values = np.asarray(booster.predict(X, pred_contrib=True, num_threads=threads))
    seconds = perf_counter() - t0
    require(values.shape == (len(X), X.shape[1] + 1) and np.isfinite(values).all(), 'Expected binary native TreeSHAP with one bias column.')
    raw = np.asarray(booster.predict(X, raw_score=True, num_threads=threads))
    require(raw.shape == (len(X),) and np.isfinite(raw).all(), 'Expected finite binary raw scores.')
    error = float(np.max(np.abs(values.sum(axis=1) - raw)))
    require(error < 1e-8, f'TreeSHAP additivity check failed: {error}')
    return values[:, :-1], values[:, -1], raw, seconds, error


def acquisition_scores(model, X, method, rng, threads=2):
    require(method in METHODS, f'Unknown strategy: {method}')
    start = perf_counter()
    p = probabilities(model.predict(X, num_threads=threads))
    inference_seconds = perf_counter() - start
    signals = {'U': 1 - 2 * np.abs(p - .5)}
    shap_seconds, error = 0., 0.
    if method in ['U+H', 'U+V', 'XAI_full']:
        phi, _, _, shap_seconds, error = native_shap(model, X, threads)
        h, v = shap_signals(phi)
        signals.update(H=h, V=v)
    scaled = {name: normalize(values) for name, values in signals.items()}
    scores = rng.random(len(X)) if method == 'Random' else sum(w * scaled[k] for k, w in WEIGHTS[method].items())
    timing = {'query_seconds': perf_counter() - start, 'pool_inference_seconds': inference_seconds,
              'tree_shap_seconds': shap_seconds}
    return scores, signals, scaled, timing, error
