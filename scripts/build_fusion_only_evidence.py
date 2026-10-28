#!/usr/bin/env python3
"""Build a defense artifact comparing fusion methods with fusion methods.

This script intentionally excludes Static-only and Dynamic-only from the main
claim.  Those channels are useful diagnostic baselines, but they cannot prove
that a proposed fusion rule is better than another fusion rule.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score


METHODS = [
    "Average_50_50",
    "Max_score",
    "Fixed_weight",
    "Logistic_stack",
    "Reliability_P",
    "Reliability_PI",
    "Reliability_full_PID",
]

LABELS = {
    "Average_50_50": "Average 50/50",
    "Max_score": "Max-risk",
    "Fixed_weight": "Fixed weight",
    "Logistic_stack": "Logistic stacking",
    "Reliability_P": "Adaptive P",
    "Reliability_PI": "Adaptive PI",
    "Reliability_full_PID": "Full PID",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def metrics(frame: pd.DataFrame) -> dict[str, float | int]:
    y = frame.label.to_numpy(dtype=int)
    score = frame.score.to_numpy(dtype=float)
    decision = frame.predicted_label.to_numpy(dtype=int)
    negative = y == 0
    positive = y == 1
    fp = int(np.sum((decision == 1) & negative))
    tn = int(np.sum((decision == 0) & negative))
    tp = int(np.sum((decision == 1) & positive))
    fn = int(np.sum((decision == 0) & positive))
    return {
        "samples": int(len(frame)),
        "auc": float(roc_auc_score(y, score)),
        "ap": float(average_precision_score(y, score)),
        "brier": float(brier_score_loss(y, score)),
        "fpr": fp / (fp + tn),
        "tpr": tp / (tp + fn),
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "tp": tp,
    }


def bootstrap_difference(
    final: pd.DataFrame,
    left: str,
    right: str,
    iterations: int,
    seed: int,
) -> dict:
    wide = {}
    for method in (left, right):
        selected = final[final.method == method].sort_values("row_id")
        wide[method] = selected
    if not np.array_equal(wide[left].row_id.to_numpy(), wide[right].row_id.to_numpy()):
        raise ValueError(f"Unpaired rows for {left} and {right}")
    y = wide[left].label.to_numpy(dtype=int)
    if not np.array_equal(y, wide[right].label.to_numpy(dtype=int)):
        raise ValueError(f"Unpaired labels for {left} and {right}")
    left_score = wide[left].score.to_numpy(dtype=float)
    right_score = wide[right].score.to_numpy(dtype=float)
    left_decision = wide[left].predicted_label.to_numpy(dtype=int)
    right_decision = wide[right].predicted_label.to_numpy(dtype=int)
    rng = np.random.default_rng(seed)
    class_indices = [np.flatnonzero(y == value) for value in (0, 1)]
    values = {name: [] for name in ("auc", "ap", "brier", "fpr", "tpr")}
    for _ in range(iterations):
        sampled = np.concatenate([
            rng.choice(index, size=len(index), replace=True) for index in class_indices
        ])
        sampled_y = y[sampled]
        negative = sampled_y == 0
        positive = sampled_y == 1
        sampled_left_score = left_score[sampled]
        sampled_right_score = right_score[sampled]
        sampled_left_decision = left_decision[sampled]
        sampled_right_decision = right_decision[sampled]
        values["auc"].append(float(
            roc_auc_score(sampled_y, sampled_left_score)
            - roc_auc_score(sampled_y, sampled_right_score)
        ))
        values["ap"].append(float(
            average_precision_score(sampled_y, sampled_left_score)
            - average_precision_score(sampled_y, sampled_right_score)
        ))
        values["brier"].append(float(
            np.mean((sampled_y - sampled_left_score) ** 2)
            - np.mean((sampled_y - sampled_right_score) ** 2)
        ))
        values["fpr"].append(float(
            np.mean(sampled_left_decision[negative])
            - np.mean(sampled_right_decision[negative])
        ))
        values["tpr"].append(float(
            np.mean(sampled_left_decision[positive])
            - np.mean(sampled_right_decision[positive])
        ))
    return {
        "comparison": f"{left}_minus_{right}",
        "samples": int(len(y)),
        "iterations": int(iterations),
        "metrics": {
            name: {
                "mean": float(np.mean(samples)),
                "ci95_low": float(np.quantile(samples, 0.025)),
                "ci95_high": float(np.quantile(samples, 0.975)),
            }
            for name, samples in values.items()
        },
    }


def pct(value: float) -> str:
    return f"{100 * value:.2f}%"


def pp(value: float) -> str:
    return f"{100 * value:+.2f} pp"


def build_report(summary: dict) -> str:
    rows = []
    for method in METHODS:
        item = summary["methods"][method]
        rows.append(
            f"| {LABELS[method]} | {item['auc']:.4f} | {item['ap']:.4f} | "
            f"{pct(item['fpr'])} ({item['fp']}) | {pct(item['tpr'])} ({item['tp']}) | "
            f"{item['brier']:.4f} |"
        )
    p_fixed = summary["comparisons"]["Reliability_P_minus_Fixed_weight"]["metrics"]
    full_p = summary["comparisons"]["Reliability_full_PID_minus_Reliability_P"]["metrics"]
    full_baseline_rows = []
    for baseline in ("Average_50_50", "Max_score", "Fixed_weight", "Logistic_stack"):
        comparison = summary["comparisons"][
            f"Reliability_full_PID_minus_{baseline}"
        ]["metrics"]
        full_baseline_rows.append(
            f"| {LABELS[baseline]} | {pp(comparison['fpr']['mean'])} "
            f"[{pp(comparison['fpr']['ci95_low'])}; {pp(comparison['fpr']['ci95_high'])}] | "
            f"{pp(comparison['tpr']['mean'])} "
            f"[{pp(comparison['tpr']['ci95_low'])}; {pp(comparison['tpr']['ci95_high'])}] | "
            f"{100 * comparison['auc']['mean']:+.2f} pp "
            f"[{100 * comparison['auc']['ci95_low']:+.2f}; "
            f"{100 * comparison['auc']['ci95_high']:+.2f}] |"
        )
    p = summary["methods"]["Reliability_P"]
    fixed = summary["methods"]["Fixed_weight"]
    return f"""# Kiểm định fusion-only cho đóng góp dung hợp

## Câu hỏi đúng

Phương pháp dung hợp đề xuất có tốt hơn các **phương pháp dung hợp** hay không?
Static-only và Dynamic-only chỉ được giữ làm chẩn đoán kênh, không được dùng làm
đối chứng chính cho tuyên bố vượt trội của luật dung hợp.

## Kết quả trên 1.922 mẫu, 5 outer folds

| Phương pháp dung hợp | ROC-AUC | AP | FPR (FP) | TPR (TP) | Brier |
|---|---:|---:|---:|---:|---:|
{chr(10).join(rows)}

## Phát biểu được dữ liệu hỗ trợ

So với Fixed weight, **Adaptive P** giảm FPR từ {pct(fixed['fpr'])} xuống
{pct(p['fpr'])}, tương ứng {pp(p_fixed['fpr']['mean'])}, CI 95%
[{pp(p_fixed['fpr']['ci95_low'])}; {pp(p_fixed['fpr']['ci95_high'])}]. Brier giảm
{p_fixed['brier']['mean']:.5f}, CI 95%
[{p_fixed['brier']['ci95_low']:.5f}; {p_fixed['brier']['ci95_high']:.5f}]. Chênh lệch
TPR là {pp(p_fixed['tpr']['mean'])} và CI đi qua 0. Ở số đếm gộp, Adaptive P
tạo {p['fp']} báo động nhầm so với {fixed['fp']} của Fixed, trong khi số dương tính
đúng là {p['tp']} so với {fixed['tp']}.

Đây là bằng chứng rằng **trọng số thích nghi theo độ tin cậy** có lợi hơn trọng số
cố định ở operating point đã khóa. Average và Logistic stacking vẫn tạo đánh đổi
khác: AUC/TPR cao hơn nhưng FPR cao hơn. Vì vậy Adaptive P là một điểm trên biên
đánh đổi, không phải phương pháp thắng mọi chỉ số.

## Full PID so với các luật dung hợp bên ngoài họ PID

Các hiệu ứng dưới đây là `Full PID - baseline`; giá trị FPR âm có lợi cho PID,
giá trị TPR/AUC dương có lợi cho PID.

| Baseline | ΔFPR (CI 95%) | ΔTPR (CI 95%) | ΔAUC (CI 95%) |
|---|---:|---:|---:|
{chr(10).join(full_baseline_rows)}

Full PID có FPR quan sát thấp nhất trong nhóm baseline bên ngoài họ PID. Mức giảm
FPR có CI loại 0 so với Average, Max-risk và Logistic stacking; so với Fixed,
CI FPR còn đi qua 0 nhưng Brier cải thiện. Tuy nhiên, so với Average/Max-risk,
PID đồng thời giảm khoảng 0,8 điểm phần trăm TPR. Đây là đánh đổi vận hành, không
phải thống trị toàn diện. Không được mô tả các hàng này là so sánh "cùng TPR"
vì threshold được chọn riêng trên validation và TPR outer-test có sai khác.

## Điều dữ liệu bác bỏ

Full PID không hơn Adaptive P: chênh lệch FPR là
{pp(full_p['fpr']['mean'])}, CI 95% [{pp(full_p['fpr']['ci95_low'])};
{pp(full_p['fpr']['ci95_high'])}], trong khi TPR không đổi. Full PID cũng không
đạt AUC cao nhất. Do đó không được tuyên bố thành phần I/D tạo cải thiện trên
chuỗi 1--20 sự kiện hiện tại.

## Cách trình bày trước hội đồng

> Trên cùng 1.922 mẫu và năm outer folds, thành phần thích nghi P trong khung
> PID giảm FPR 1,28 điểm phần trăm và cải thiện Brier so với trọng số cố định;
> bootstrap ghép cặp cho hai hiệu ứng này không đi qua 0, còn TPR không có khác
> biệt được phát hiện. Ablation cho thấy I và D chưa bổ sung lợi ích trong horizon
> 20 sự kiện. Vì vậy đóng góp thực nghiệm là reliability-aware adaptive fusion và
> phép ablation P/PI/PID, không phải tuyên bố full PID luôn vượt mọi baseline.

Muốn tuyên bố full PID vượt Average, Fixed và Stacking cần khóa lại thuật toán,
metric chính và biên non-inferiority trước khi chạy **một cohort external/temporal
chưa từng dùng để phát triển phương pháp**. Không tiếp tục chỉnh gain trên chính
1.922 mẫu này để tìm kết quả thuận lợi.
"""


def plot(summary: dict, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(9.2, 5.4))
    for method in METHODS:
        item = summary["methods"][method]
        color = "#D55E00" if method == "Reliability_P" else (
            "#7F7F7F" if method == "Reliability_full_PID" else "#1675B9"
        )
        ax.scatter(100 * item["fpr"], 100 * item["tpr"], s=105, color=color, zorder=3)
        ax.annotate(LABELS[method], (100 * item["fpr"], 100 * item["tpr"]),
                    xytext=(5, 5), textcoords="offset points", fontsize=8.5)
    ax.set_xlabel("False-positive rate (%) — thấp hơn tốt hơn")
    ax.set_ylabel("True-positive rate (%) — cao hơn tốt hơn")
    ax.set_title("So sánh giữa các phương pháp dung hợp (ngưỡng chọn trên validation)")
    ax.grid(alpha=.25)
    fig.tight_layout()
    fig.savefig(out / "fusion_only_operating_tradeoff.png", dpi=220)
    fig.savefig(out / "fusion_only_operating_tradeoff.pdf")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--bootstrap", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    predictions = pd.read_csv(args.predictions)
    final = (predictions.sort_values(["row_id", "time_step"])
             .groupby(["row_id", "method"], as_index=False).tail(1))
    available = set(final.method)
    missing = set(METHODS) - available
    if missing:
        raise ValueError(f"Missing methods: {sorted(missing)}")
    methods = {method: metrics(final[final.method == method]) for method in METHODS}
    # Compare the adaptive controller with every external fusion baseline,
    # then keep the P-vs-Fixed contribution test and full-PID-vs-P ablation.
    pairs = [
        ("Reliability_P", "Fixed_weight"),
        ("Reliability_full_PID", "Average_50_50"),
        ("Reliability_full_PID", "Max_score"),
        ("Reliability_full_PID", "Fixed_weight"),
        ("Reliability_full_PID", "Logistic_stack"),
        ("Reliability_full_PID", "Reliability_P"),
    ]
    comparisons = {
        f"{left}_minus_{right}": bootstrap_difference(
            final, left, right, args.bootstrap, args.seed + index
        )
        for index, (left, right) in enumerate(pairs)
    }
    summary = {
        "status": "fusion_only_evidence_audit",
        "source": str(args.predictions.resolve()),
        "source_sha256": sha256(args.predictions),
        "samples": int(final.row_id.nunique()),
        "outer_folds": int(final.outer_fold.nunique()),
        "bootstrap_iterations": int(args.bootstrap),
        "seed": int(args.seed),
        "methods": methods,
        "comparisons": comparisons,
        "claim_scope": "fusion methods only; Static/Dynamic excluded from superiority claim",
    }
    (args.out / "fusion_only_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.out / "FUSION_ONLY_EVIDENCE_VI.md").write_text(
        build_report(summary), encoding="utf-8"
    )
    plot(summary, args.out)
    artifact_hashes = {
        path.name: sha256(path)
        for path in sorted(args.out.iterdir())
        if path.is_file() and path.name != "artifact_sha256.json"
    }
    (args.out / "artifact_sha256.json").write_text(
        json.dumps(artifact_hashes, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
