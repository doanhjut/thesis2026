"""Build and validate the offline defense-demo evidence bundle.

The demo is an artifact replay.  It never downloads or executes PE files and it
does not generate replacement measurements.  Every value shown by the dashboard
is copied or aggregated from the measured experiment artifacts in ``results``.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score


SCHEMA_VERSION = 1
DEFAULT_BUNDLE = Path("results/defense_demo_bundle/demo_bundle.json")

FUSION_SUMMARY = Path(
    "results/measured_20261028_fusion_only_evidence_1922/fusion_only_summary.json"
)
FUSION_EVENTS = Path(
    "results/measured_20261023_reliability_pid_exploratory_1922/"
    "event_predictions.csv.gz"
)
AL_DIR = Path("results/confirmatory_20261019_ember_identity/al")
FIDELITY_DIR = Path("results/confirmatory_20261019_ember_identity/fidelity")

TRACE_METHODS = [
    "Static_only",
    "Dynamic_only",
    "Fixed_weight",
    "Logistic_stack",
    "Reliability_P",
    "Reliability_full_PID",
]

# The descriptions are presentation aids.  The rows and every score displayed
# are measured rows from FUSION_EVENTS and are checked below before packaging.
PID_SCENARIOS = [
    {
        "row_id": 1171,
        "title": "Giảm một báo động nhầm do kênh động xung đột",
        "summary": (
            "Mẫu lành; Fixed và Logistic stacking cảnh báo nhầm, trong khi "
            "Adaptive P và Full PID giữ quyết định lành."
        ),
        "expected": {"label": 0, "Fixed_weight": 1, "Reliability_P": 0},
    },
    {
        "row_id": 1505,
        "title": "Khôi phục một mẫu malware bị luật cố định bỏ sót",
        "summary": (
            "Mẫu malware; Fixed và Logistic stacking bỏ sót, trong khi "
            "Adaptive P và Full PID dự đoán đúng."
        ),
        "expected": {"label": 1, "Fixed_weight": 0, "Reliability_P": 1},
    },
    {
        "row_id": 723,
        "title": "Giảm ảnh hưởng của tín hiệu động nhiễu",
        "summary": (
            "Mẫu lành có điểm động cao; Adaptive P sửa cảnh báo nhầm của "
            "Fixed weight."
        ),
        "expected": {"label": 0, "Fixed_weight": 1, "Reliability_P": 0},
    },
    {
        "row_id": 621,
        "title": "Phản ví dụ: dung hợp thích nghi không thắng mọi mẫu",
        "summary": (
            "Mẫu malware mà Fixed/Logistic dự đoán đúng nhưng họ PID bỏ sót; "
            "dùng để trình bày trung thực giới hạn của phương pháp."
        ),
        "expected": {"label": 1, "Fixed_weight": 1, "Reliability_P": 0},
    },
]


PORTABLE_TEXT_SUFFIXES = {".csv", ".json", ".md", ".txt"}


def sha256_file(path: Path) -> str:
    """Hash an artifact consistently across LF and CRLF Git checkouts.

    Git may materialize tracked text files with CRLF on Windows.  The measured
    values are unchanged, so text artifacts are hashed after canonicalizing line
    endings to LF.  Compressed and other binary artifacts keep byte-exact hashes.
    """

    if path.suffix.lower() in PORTABLE_TEXT_SUFFIXES:
        content = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        return hashlib.sha256(content).hexdigest()

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert a DataFrame to strict JSON records (NaN becomes null)."""

    return json.loads(frame.to_json(orient="records", double_precision=12))


def _source(root: Path, relative: Path) -> dict[str, Any]:
    path = root / relative
    if not path.is_file():
        raise FileNotFoundError(f"Missing measured demo source: {path}")
    return {
        "path": relative.as_posix(),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def _build_pid(root: Path) -> dict[str, Any]:
    summary = json.loads((root / FUSION_SUMMARY).read_text(encoding="utf-8"))

    usecols = [
        "row_id",
        "sha256",
        "time_step",
        "event_count",
        "label",
        "probability",
        "p_dynamic",
        "w_static",
        "score",
        "outer_fold",
        "method",
        "threshold",
        "predicted_label",
        "pid_error",
        "pid_integral",
        "pid_derivative",
    ]
    rows = {item["row_id"] for item in PID_SCENARIOS}
    events = pd.read_csv(root / FUSION_EVENTS, usecols=usecols)
    events = events[
        events["row_id"].isin(rows) & events["method"].isin(TRACE_METHODS)
    ].copy()
    events = events.sort_values(["row_id", "method", "time_step"])

    scenarios: list[dict[str, Any]] = []
    for definition in PID_SCENARIOS:
        sample = events[events["row_id"] == definition["row_id"]].copy()
        if sample.empty:
            raise ValueError(f"PID demo row not found: {definition['row_id']}")
        final = sample.groupby("method", as_index=False).tail(1).set_index("method")
        label = int(sample["label"].iloc[0])
        expected = definition["expected"]
        if label != expected["label"]:
            raise ValueError(f"Unexpected label for PID row {definition['row_id']}")
        for method in ("Fixed_weight", "Reliability_P"):
            actual = int(final.loc[method, "predicted_label"])
            if actual != expected[method]:
                raise ValueError(
                    f"Unexpected {method} decision for PID row "
                    f"{definition['row_id']}: {actual}"
                )
        scenarios.append(
            {
                "row_id": definition["row_id"],
                "title": definition["title"],
                "summary": definition["summary"],
                "sha256": str(sample["sha256"].iloc[0]),
                "label": label,
                "outer_fold": int(sample["outer_fold"].iloc[0]),
                "trace": _records(sample),
            }
        )

    methods = []
    for name, values in summary["methods"].items():
        methods.append({"method": name, **values})

    comparison_names = [
        "Reliability_P_minus_Fixed_weight",
        "Reliability_full_PID_minus_Logistic_stack",
        "Reliability_full_PID_minus_Reliability_P",
    ]
    comparisons = {
        key: summary["comparisons"][key] for key in comparison_names
    }
    return {
        "samples": int(summary["samples"]),
        "outer_folds": int(summary["outer_folds"]),
        "methods": methods,
        "comparisons": comparisons,
        "scenarios": scenarios,
        "scope": summary["claim_scope"],
        "notice": (
            "Development evidence trên cùng cohort 1.922 mẫu. Adaptive P cải "
            "thiện Fixed tại operating point đã khóa; I/D chưa tạo lợi ích "
            "bổ sung ổn định."
        ),
    }


def _build_al(root: Path) -> dict[str, Any]:
    aulc = pd.read_csv(root / AL_DIR / "aulc_summary.csv")
    target = pd.read_csv(root / AL_DIR / "target_reach_summary.csv")
    overhead = pd.read_csv(root / AL_DIR / "overhead_by_fold.csv")
    metrics = pd.read_csv(root / AL_DIR / "metrics_all_folds.csv")

    curves = (
        metrics.groupby(["method", "n_labeled"], as_index=False)
        .agg(
            test_auc_mean=("test_auc", "mean"),
            test_auc_sd=("test_auc", "std"),
            test_ap_mean=("test_ap", "mean"),
            test_ap_sd=("test_ap", "std"),
            observations=("test_auc", "size"),
        )
        .sort_values(["method", "n_labeled"])
    )
    summary = aulc.merge(target, on="method", how="inner").merge(
        overhead[["method", "query_share_percent"]], on="method", how="left"
    )
    return {
        "fold_seed_pairs": int(aulc["n_fold_seed_pairs"].iloc[0]),
        "summary": _records(summary),
        "learning_curves": _records(curves),
        "notice": (
            "Kết quả trên 5 folds × 5 seeds của EMBER. Số nhãn là số truy vấn "
            "oracle, không phải thời gian lao động thực tế của chuyên gia."
        ),
    }


def _build_fidelity(root: Path) -> dict[str, Any]:
    deletion = pd.read_csv(root / FIDELITY_DIR / "deletion_summary.csv")
    stability = pd.read_csv(
        root / FIDELITY_DIR / "shap_stability_summary.csv"
    )
    model_metrics = pd.read_csv(root / FIDELITY_DIR / "model_metrics.csv")
    additivity_max = float(model_metrics["max_shap_additivity_error"].max())
    return {
        "models": int(deletion["models"].max()),
        "deletion": _records(deletion),
        "stability": _records(stability),
        "max_shap_additivity_error": additivity_max,
        "notice": (
            "Deletion và stability đo độ bám của TreeSHAP vào fitted model; "
            "không chứng minh quan hệ nhân quả hoặc PE vẫn hợp lệ sau masking."
        ),
    }


def build_demo_bundle(root: Path, output: Path | None = None) -> Path:
    root = root.resolve()
    output = output or DEFAULT_BUNDLE
    output = output if output.is_absolute() else root / output

    source_paths = [
        FUSION_SUMMARY,
        FUSION_EVENTS,
        AL_DIR / "aulc_summary.csv",
        AL_DIR / "target_reach_summary.csv",
        AL_DIR / "overhead_by_fold.csv",
        AL_DIR / "metrics_all_folds.csv",
        AL_DIR / "full_pool_references.csv",
        AL_DIR / "verification.json",
        FIDELITY_DIR / "deletion_summary.csv",
        FIDELITY_DIR / "mask_metrics_all_models.csv",
        FIDELITY_DIR / "shap_stability_summary.csv",
        FIDELITY_DIR / "shap_rank_stability.csv",
        FIDELITY_DIR / "model_metrics.csv",
        FIDELITY_DIR / "verification.json",
    ]
    bundle = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "measured_artifact_replay",
        "safety": (
            "Offline artifact replay only; no PE download, upload, execution, "
            "sandbox call, model training, or network request."
        ),
        "sources": [_source(root, item) for item in source_paths],
        "pid": _build_pid(root),
        "active_learning": _build_al(root),
        "fidelity": _build_fidelity(root),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return output


def load_demo_bundle(path: Path) -> dict[str, Any]:
    bundle = json.loads(path.read_text(encoding="utf-8"))
    if bundle.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported demo bundle schema: {bundle.get('schema_version')}"
        )
    if bundle.get("mode") != "measured_artifact_replay":
        raise ValueError("Demo bundle is not a measured artifact replay")
    return bundle


def validate_demo_bundle(
    root: Path, path: Path, *, verify_source_hashes: bool = True
) -> dict[str, Any]:
    root = root.resolve()
    path = path if path.is_absolute() else root / path
    bundle = load_demo_bundle(path)
    errors: list[str] = []

    if verify_source_hashes:
        for source in bundle["sources"]:
            candidate = root / source["path"]
            if not candidate.is_file():
                errors.append(f"missing source: {source['path']}")
                continue
            actual = sha256_file(candidate)
            if actual != source["sha256"]:
                errors.append(f"hash mismatch: {source['path']}")

    pid_methods = {item["method"] for item in bundle["pid"]["methods"]}
    required_pid = {"Fixed_weight", "Reliability_P", "Reliability_full_PID"}
    if not required_pid.issubset(pid_methods):
        errors.append("PID summary is missing required methods")
    al_methods = {
        item["method"] for item in bundle["active_learning"]["summary"]
    }
    if {"Random", "Uncertainty", "XAI_full"} - al_methods:
        errors.append("AL summary is missing required methods")
    if not bundle["fidelity"]["deletion"]:
        errors.append("Fidelity deletion summary is empty")

    return {
        "ok": not errors,
        "errors": errors,
        "bundle": path.as_posix(),
        "schema_version": bundle["schema_version"],
        "source_count": len(bundle["sources"]),
        "pid_scenarios": len(bundle["pid"]["scenarios"]),
    }


def audit_demo_evidence(root: Path, path: Path) -> dict[str, Any]:
    """Recompute the headline demo claims from lower-level measured artifacts."""

    root = root.resolve()
    path = path if path.is_absolute() else root / path
    hash_report = validate_demo_bundle(root, path, verify_source_hashes=True)
    bundle = load_demo_bundle(path)
    checks: list[dict[str, Any]] = []

    def check(name: str, computed: float, displayed: float, tolerance: float = 1e-9):
        difference = abs(float(computed) - float(displayed))
        checks.append(
            {
                "name": name,
                "computed": float(computed),
                "displayed": float(displayed),
                "absolute_difference": difference,
                "passed": difference <= tolerance,
            }
        )

    event_columns = [
        "row_id", "time_step", "label", "method", "score", "predicted_label"
    ]
    events = pd.read_csv(root / FUSION_EVENTS, usecols=event_columns)
    final = (
        events.sort_values(["row_id", "time_step"])
        .groupby(["row_id", "method"], as_index=False)
        .tail(1)
    )
    displayed_pid = {item["method"]: item for item in bundle["pid"]["methods"]}
    for method in ("Fixed_weight", "Reliability_P", "Reliability_full_PID"):
        frame = final[final["method"] == method]
        y = frame["label"].to_numpy(dtype=int)
        decision = frame["predicted_label"].to_numpy(dtype=int)
        negative = y == 0
        fpr = float(np.mean(decision[negative]))
        auc = float(roc_auc_score(y, frame["score"].to_numpy(dtype=float)))
        check(f"PID/{method}/fpr", fpr, displayed_pid[method]["fpr"])
        check(f"PID/{method}/auc", auc, displayed_pid[method]["auc"])

    al_metrics = pd.read_csv(root / AL_DIR / "metrics_all_folds.csv")
    references = pd.read_csv(root / AL_DIR / "full_pool_references.csv")
    areas, costs, timings = [], [], []
    for (fold, seed, method), group in al_metrics.groupby(["fold", "seed", "method"]):
        group = group.sort_values("n_labeled")
        width = float(group["n_labeled"].max() - group["n_labeled"].min())
        areas.append(
            {
                "method": method,
                "auc": float(np.trapezoid(group["test_auc"], group["n_labeled"]) / width),
                "ap": float(np.trapezoid(group["test_ap"], group["n_labeled"]) / width),
            }
        )
        target = float(
            references.loc[references["fold"] == fold, "target_validation_auc"].iloc[0]
        )
        reached = group[group["val_auc"] >= target]
        costs.append(
            {
                "method": method,
                "labels": float(reached.iloc[0]["n_labeled"]) if len(reached) else np.nan,
            }
        )
        timings.append(
            {
                "method": method,
                "train": float(group["train_seconds"].sum()),
                "query": float(group["query_seconds"].sum()),
            }
        )
    area_summary = pd.DataFrame(areas).groupby("method").mean()
    cost_summary = pd.DataFrame(costs).groupby("method").mean()
    timing_summary = pd.DataFrame(timings).groupby("method").mean()
    displayed_al = {
        item["method"]: item for item in bundle["active_learning"]["summary"]
    }
    for method in displayed_al:
        check(f"AL/{method}/roc_aulc", area_summary.loc[method, "auc"], displayed_al[method]["auc_aulc_mean"])
        check(f"AL/{method}/ap_aulc", area_summary.loc[method, "ap"], displayed_al[method]["ap_aulc_mean"])
        check(f"AL/{method}/labels_to_target", cost_summary.loc[method, "labels"], displayed_al[method]["mean_labels_reached"])
        query_share = 100 * timing_summary.loc[method, "query"] / (
            timing_summary.loc[method, "train"] + timing_summary.loc[method, "query"]
        )
        check(f"AL/{method}/query_share_percent", query_share, displayed_al[method]["query_share_percent"])

    masks = pd.read_csv(root / FIDELITY_DIR / "mask_metrics_all_models.csv")
    comparisons = []
    for (_, _, baseline, k), group in masks.groupby(
        ["fold", "seed", "mask_baseline", "k"]
    ):
        top = group[group["method"] == "top_abs_treeshap"].iloc[0]
        random = group[group["method"] == "uniform_random"]
        comparisons.append(
            {
                "mask_baseline": baseline,
                "k": int(k),
                "top": float(top["auc_drop"]),
                "random": float(random["auc_drop"].mean()),
            }
        )
    deletion = pd.DataFrame(comparisons).groupby(["mask_baseline", "k"]).mean()
    displayed_deletion = {
        (item["mask_baseline"], int(item["k"])): item
        for item in bundle["fidelity"]["deletion"]
    }
    for key, displayed in displayed_deletion.items():
        check(f"Fidelity/{key[0]}/k{key[1]}/top_drop", deletion.loc[key, "top"], displayed["top_shap_auc_drop_mean"])
        check(f"Fidelity/{key[0]}/k{key[1]}/random_drop", deletion.loc[key, "random"], displayed["random_auc_drop_mean"])

    ranks = pd.read_csv(root / FIDELITY_DIR / "shap_rank_stability.csv")
    displayed_stability = {
        (item["scope"], item["metric"]): item
        for item in bundle["fidelity"]["stability"]
    }
    for same_fold, scope in ((True, "within_fold"), (False, "across_fold")):
        computed = float(
            ranks.loc[
                ranks["same_fold"] == same_fold, "spearman_global_importance"
            ].mean()
        )
        check(
            f"Fidelity/{scope}/spearman",
            computed,
            displayed_stability[(scope, "spearman_global_importance")]["mean"],
        )

    al_verification = json.loads(
        (root / AL_DIR / "verification.json").read_text(encoding="utf-8")
    )
    fidelity_verification = json.loads(
        (root / FIDELITY_DIR / "verification.json").read_text(encoding="utf-8")
    )
    replay = {
        "al_status": al_verification["status"],
        "al_checkpoints_replayed": int(
            sum(item["checkpoints_replayed"] for item in al_verification["folds"])
        ),
        "al_prediction_records": int(
            sum(item["prediction_records"] for item in al_verification["folds"])
        ),
        "fidelity_status": fidelity_verification["status"],
        "fidelity_mask_batches_replayed": int(
            sum(item["mask_batches_replayed"] for item in fidelity_verification["runs"])
        ),
        "fidelity_prediction_records": int(
            sum(item["prediction_records"] for item in fidelity_verification["runs"])
        ),
    }
    return {
        "ok": hash_report["ok"] and all(item["passed"] for item in checks),
        "mode": "recomputed_from_lower_level_artifacts",
        "hash_validation": hash_report,
        "metric_checks_passed": sum(item["passed"] for item in checks),
        "metric_checks_total": len(checks),
        "replay_verification": replay,
        "checks": checks,
    }
