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

import pandas as pd


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


def sha256_file(path: Path) -> str:
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
        FIDELITY_DIR / "deletion_summary.csv",
        FIDELITY_DIR / "shap_stability_summary.csv",
        FIDELITY_DIR / "model_metrics.csv",
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
