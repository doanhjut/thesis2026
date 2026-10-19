# Kết quả static uncertainty gate

Calibration dùng 50% validation; phần còn lại chọn gate với giới hạn early-FNR=2.00%, early-FPR=2.00%.

| Phương pháp | Test chuyển dynamic | Early FN / tổng positive | Early FP / tổng negative |
|---|---:|---:|---:|
| Random | 24.35% ± 8.14% | 2.60% ± 2.07% | 4.53% ± 1.61% |
| U+H | 24.65% ± 11.31% | 3.60% ± 2.61% | 3.47% ± 0.51% |
| U+V | 32.25% ± 11.03% | 2.00% ± 2.92% | 3.60% ± 0.55% |
| Uncertainty | 24.05% ± 9.28% | 2.80% ± 1.48% | 3.47% ± 1.52% |
| XAI_full | 29.40% ± 5.64% | 0.40% ± 0.55% | 3.20% ± 0.56% |

Đây mới là gate tĩnh: các dòng được chuyển dynamic chưa có final decision. Không diễn giải routed fraction thành mức tiết kiệm end-to-end trước khi đo sandbox và full-traffic quality.

Static gate only. Routed rows have no final decision until real dynamic evidence is supplied.
Threshold feasibility is estimated from half of a 400-row validation split and is therefore coarse.
The same test split is shared across seeds; seed SD is not a population confidence interval.
Calibration/gating does not establish ransomware-specific validity without source provenance.
