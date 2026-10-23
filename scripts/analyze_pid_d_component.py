#!/usr/bin/env python3
"""Measure the derivative contribution in an event-indexed PID run.

Two paired comparisons are reported:

1. validation-selected PID versus validation-selected PI;
2. the selected PID versus a counterfactual replay with the same Kp, Ki and
   decision threshold but Kd set to zero.

The second comparison isolates the derivative term for the deployed PID
configuration.  It does not retune the no-D counterfactual on outer-test data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sigmoid_clipped(values: np.ndarray) -> np.ndarray:
    positive = values >= 0
    result = np.empty_like(values, dtype=float)
    result[positive] = 1.0 / (1.0 + np.exp(-values[positive]))
    exp_value = np.exp(values[~positive])
    result[~positive] = exp_value / (1.0 + exp_value)
    return np.clip(result, 0.1, 0.9)


def metrics(labels: np.ndarray, scores: np.ndarray, predictions: np.ndarray) -> dict:
    negative, positive = labels == 0, labels == 1
    return {
        "auc": float(roc_auc_score(labels, scores)),
        "ap": float(average_precision_score(labels, scores)),
        "brier": float(brier_score_loss(labels, scores)),
        "fpr": float(predictions[negative].mean()),
        "tpr": float(predictions[positive].mean()),
        "tn": int((predictions[negative] == 0).sum()),
        "fp": int((predictions[negative] == 1).sum()),
        "fn": int((predictions[positive] == 0).sum()),
        "tp": int((predictions[positive] == 1).sum()),
    }


def paired_bootstrap(
    labels: np.ndarray,
    left_scores: np.ndarray,
    right_scores: np.ndarray,
    left_predictions: np.ndarray,
    right_predictions: np.ndarray,
    iterations: int,
    seed: int,
) -> dict:
    rng = np.random.default_rng(seed)
    values = {name: [] for name in ["auc", "ap", "brier", "fpr", "tpr"]}
    for _ in range(iterations):
        indices = rng.integers(0, len(labels), len(labels))
        sampled = labels[indices]
        if len(np.unique(sampled)) < 2:
            continue
        negative, positive = sampled == 0, sampled == 1
        values["auc"].append(
            roc_auc_score(sampled, left_scores[indices])
            - roc_auc_score(sampled, right_scores[indices])
        )
        values["ap"].append(
            average_precision_score(sampled, left_scores[indices])
            - average_precision_score(sampled, right_scores[indices])
        )
        values["brier"].append(
            brier_score_loss(sampled, left_scores[indices])
            - brier_score_loss(sampled, right_scores[indices])
        )
        values["fpr"].append(
            left_predictions[indices][negative].mean()
            - right_predictions[indices][negative].mean()
        )
        values["tpr"].append(
            left_predictions[indices][positive].mean()
            - right_predictions[indices][positive].mean()
        )
    return {
        name: {
            "mean": float(np.mean(samples)),
            "ci95_low": float(np.quantile(samples, 0.025)),
            "ci95_high": float(np.quantile(samples, 0.975)),
            "iterations": len(samples),
        }
        for name, samples in values.items()
    }


def final_rows(frame: pd.DataFrame) -> pd.DataFrame:
    return (
        frame.sort_values(["outer_fold", "fusion", "row_id", "event_count", "time_step"])
        .groupby(["outer_fold", "fusion", "row_id"], sort=False)
        .tail(1)
        .sort_values(["outer_fold", "row_id"])
        .reset_index(drop=True)
    )


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bootstrap", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()

    run = args.run.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    prediction_path = run / "event_predictions.csv.gz"
    search_path = run / "validation_search.json"
    verification_path = run / "verification.json"
    if json.loads(verification_path.read_text(encoding="utf-8")).get("status") != "passed":
        raise RuntimeError("The source PID run has not passed replay verification.")

    predictions = pd.read_csv(prediction_path)
    search = json.loads(search_path.read_text(encoding="utf-8"))
    gains = {
        int(item["outer_fold"]): tuple(float(value) for value in item["selected"])
        for item in search
        if item["fusion"] == "PID"
    }
    pid = predictions[predictions.fusion == "PID"].copy()
    if set(pid.outer_fold.unique()) != set(gains):
        raise RuntimeError("PID gain selection does not cover every outer fold.")
    pid["kp"] = pid.outer_fold.map(lambda fold: gains[int(fold)][0])
    pid["ki"] = pid.outer_fold.map(lambda fold: gains[int(fold)][1])
    pid["kd"] = pid.outer_fold.map(lambda fold: gains[int(fold)][2])
    control_no_d = pid.kp.to_numpy() * pid.pid_error.to_numpy() + pid.ki.to_numpy() * pid.pid_integral.to_numpy()
    pid["w_static_no_d"] = sigmoid_clipped(control_no_d)
    pid["score_no_d"] = (
        pid.w_static_no_d * pid.probability + (1.0 - pid.w_static_no_d) * pid.p_dynamic
    )
    pid["predicted_label_no_d"] = (pid.score_no_d >= pid.threshold).astype(int)
    replay_error = float(
        np.max(
            np.abs(
                pid.score.to_numpy()
                - (pid.w_static * pid.probability + (1.0 - pid.w_static) * pid.p_dynamic).to_numpy()
            )
        )
    )
    if replay_error > 1e-12:
        raise RuntimeError(f"Saved PID score replay failed: {replay_error}")

    pid_final = final_rows(pid)
    no_d_fold_rows = []
    for fold, group in pid_final.groupby("outer_fold", sort=True):
        labels = group.label.to_numpy(dtype=int)
        full = metrics(labels, group.score.to_numpy(), group.predicted_label.to_numpy(dtype=int))
        no_d = metrics(labels, group.score_no_d.to_numpy(), group.predicted_label_no_d.to_numpy(dtype=int))
        for name in ["auc", "ap", "brier", "fpr", "tpr"]:
            no_d_fold_rows.append(
                {
                    "outer_fold": int(fold),
                    "metric": name,
                    "pid_value": full[name],
                    "same_kp_ki_kd_zero_value": no_d[name],
                    "difference_pid_minus_no_d": full[name] - no_d[name],
                    "lower_is_better": name in {"brier", "fpr"},
                }
            )
    fold_frame = pd.DataFrame(no_d_fold_rows)
    fold_frame.to_csv(output / "same_gain_d_toggle_fold_effects.csv", index=False)

    labels = pid_final.label.to_numpy(dtype=int)
    full_scores = pid_final.score.to_numpy()
    no_d_scores = pid_final.score_no_d.to_numpy()
    full_predictions = pid_final.predicted_label.to_numpy(dtype=int)
    no_d_predictions = pid_final.predicted_label_no_d.to_numpy(dtype=int)
    same_gain_bootstrap = paired_bootstrap(
        labels,
        full_scores,
        no_d_scores,
        full_predictions,
        no_d_predictions,
        args.bootstrap,
        args.seed,
    )

    optimized = final_rows(predictions[predictions.fusion.isin(["PI", "PID"])])
    pid_optimized = optimized[optimized.fusion == "PID"].sort_values("row_id")
    pi_optimized = optimized[optimized.fusion == "PI"].sort_values("row_id")
    if not np.array_equal(pid_optimized.row_id.to_numpy(), pi_optimized.row_id.to_numpy()):
        raise RuntimeError("Optimized PID and PI rows are not aligned.")
    optimized_bootstrap = paired_bootstrap(
        pid_optimized.label.to_numpy(dtype=int),
        pid_optimized.score.to_numpy(),
        pi_optimized.score.to_numpy(),
        pid_optimized.predicted_label.to_numpy(dtype=int),
        pi_optimized.predicted_label.to_numpy(dtype=int),
        args.bootstrap,
        args.seed,
    )

    all_abs = np.abs(pid.score.to_numpy() - pid.score_no_d.to_numpy())
    final_abs = np.abs(full_scores - no_d_scores)
    same_gain_metrics = {
        "pid": metrics(labels, full_scores, full_predictions),
        "same_kp_ki_kd_zero": metrics(labels, no_d_scores, no_d_predictions),
        "bootstrap_pid_minus_no_d": same_gain_bootstrap,
        "mean_absolute_score_change_all_events": float(all_abs.mean()),
        "max_absolute_score_change_all_events": float(all_abs.max()),
        "mean_absolute_score_change_final_event": float(final_abs.mean()),
        "max_absolute_score_change_final_event": float(final_abs.max()),
        "decision_changes_all_events": int(
            (pid.predicted_label.to_numpy(dtype=int) != pid.predicted_label_no_d.to_numpy(dtype=int)).sum()
        ),
        "decision_changes_final_event": int((full_predictions != no_d_predictions).sum()),
    }
    optimized_metrics = {
        "pid": metrics(
            pid_optimized.label.to_numpy(dtype=int),
            pid_optimized.score.to_numpy(),
            pid_optimized.predicted_label.to_numpy(dtype=int),
        ),
        "pi": metrics(
            pi_optimized.label.to_numpy(dtype=int),
            pi_optimized.score.to_numpy(),
            pi_optimized.predicted_label.to_numpy(dtype=int),
        ),
        "bootstrap_pid_minus_pi": optimized_bootstrap,
        "mean_absolute_score_difference": float(
            np.abs(pid_optimized.score.to_numpy() - pi_optimized.score.to_numpy()).mean()
        ),
        "max_absolute_score_difference": float(
            np.abs(pid_optimized.score.to_numpy() - pi_optimized.score.to_numpy()).max()
        ),
        "decision_changes": int(
            (
                pid_optimized.predicted_label.to_numpy(dtype=int)
                != pi_optimized.predicted_label.to_numpy(dtype=int)
            ).sum()
        ),
    }

    selected_gains = [
        {"outer_fold": fold, "kp": values[0], "ki": values[1], "kd": values[2]}
        for fold, values in sorted(gains.items())
    ]
    result = {
        "status": "passed",
        "samples": int(len(pid_final)),
        "event_rows": int(len(pid)),
        "comparison_1": "validation_selected_PID_minus_validation_selected_PI",
        "optimized_pid_vs_pi": optimized_metrics,
        "comparison_2": "selected_PID_minus_same_Kp_Ki_threshold_with_Kd_zero",
        "same_gain_derivative_toggle": same_gain_metrics,
        "selected_pid_gains": selected_gains,
        "interpretation": {
            "auc": "positive_favors_PID",
            "ap": "positive_favors_PID",
            "brier": "negative_favors_PID",
            "fpr": "negative_favors_PID",
            "tpr": "positive_favors_PID",
        },
        "limitations": [
            "The optimized PID-versus-PI comparison allows each family to select Kp and Ki on validation.",
            "The same-gain toggle isolates the deployed derivative term but deliberately does not retune the no-D counterfactual.",
            "Event count is an observation axis, not wall-clock latency.",
        ],
        "source": {
            "run": str(run),
            "event_predictions_sha256": sha256(prediction_path),
            "validation_search_sha256": sha256(search_path),
        },
    }
    write_json(output / "d_component_ablation.json", result)
    pid[
        [
            "row_id",
            "sha256",
            "outer_fold",
            "event_count",
            "label",
            "threshold",
            "kp",
            "ki",
            "kd",
            "pid_derivative",
            "score",
            "score_no_d",
            "predicted_label",
            "predicted_label_no_d",
        ]
    ].to_csv(output / "same_gain_d_toggle_predictions.csv.gz", index=False, compression="gzip")
    write_json(
        output / "verification.json",
        {
            "status": "passed",
            "source_run_verification": "passed",
            "pid_score_replay_max_abs_error": replay_error,
            "samples_checked": int(len(pid_final)),
            "event_rows_checked": int(len(pid)),
        },
    )
    artifact_names = [
        "d_component_ablation.json",
        "same_gain_d_toggle_fold_effects.csv",
        "same_gain_d_toggle_predictions.csv.gz",
        "verification.json",
    ]
    write_json(output / "artifact_sha256.json", {name: sha256(output / name) for name in artifact_names})
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
