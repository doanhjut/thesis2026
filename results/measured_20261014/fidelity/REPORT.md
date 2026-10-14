# Kết quả Fidelity

AUC trước che: 0.980167.

| k | AUC sau top-SHAP | AUC sau random (TB) | AUC giảm top-SHAP | FF thô |
|---:|---:|---:|---:|---:|
| 10 | 0.913933 | 0.979867 | 0.066233 | 1.039404 |
| 25 | 0.818533 | 0.979910 | 0.161633 | 2.004518 |
| 50 | 0.671200 | 0.979263 | 0.308967 | 2.148306 |

EC = 0.304372514036267; CF = 0.587352. OFS không tổng hợp.
Mô hình này huấn luyện riêng, khác model AL. Khoảng bootstrap có điều kiện trên model cố định.
Che vector không chứng minh tệp PE sau biến đổi hợp lệ; số chiều được chọn bằng nhau không bảo đảm cùng độ lớn biến đổi.

The CSV source, original file identities and ransomware-specific label semantics are not verified. Row-disjoint measurements are an internal pilot, not a verified ransomware, family-held-out or zero-day benchmark.
One fitted model; test bootstrap is conditional on that model.
Masking is not a validated transformation of executable PE files.
EC pairs share samples; no naive independent-pair p-value.
CF describes class separation, not causality or explanation correctness.
