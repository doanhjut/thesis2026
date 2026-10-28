# Stateful Gated Residual PID — exploratory

> Baseline stacking được giữ nguyên. PID chỉ cộng residual có gate và có cấu hình gain=0 để quay về stacking. Cohort đã tham gia phát triển phương pháp nên chưa phải xác nhận ngoài.

| Phương pháp | Stress | AUC | FPR | TPR | Event-AUC | Early-AUC@10 | Median stable event | Crossings |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Gated_residual_PID | clean | 0.9893 | 3.47% | 94.17% | 0.9866 | 0.9810 | 1.00 | 0.339 |
| Gated_residual_PID | delay_5 | 0.9892 | 2.61% | 94.49% | 0.9848 | 0.9766 | 1.00 | 0.325 |
| Gated_residual_PID | dropout_20 | 0.9893 | 3.47% | 94.17% | 0.9865 | 0.9809 | 1.00 | 0.322 |
| Gated_residual_PID | noise_logit_025 | 0.9892 | 3.63% | 94.00% | 0.9863 | 0.9805 | 1.00 | 0.466 |
| Temporal_stacking | clean | 0.9894 | 4.29% | 94.34% | 0.9869 | 0.9816 | 1.00 | 0.360 |
| Temporal_stacking | delay_5 | 0.9894 | 3.93% | 94.66% | 0.9852 | 0.9773 | 1.00 | 0.353 |
| Temporal_stacking | dropout_20 | 0.9894 | 4.12% | 94.34% | 0.9868 | 0.9814 | 1.00 | 0.338 |
| Temporal_stacking | noise_logit_025 | 0.9893 | 4.62% | 94.17% | 0.9867 | 0.9811 | 1.00 | 0.507 |

## Cấu hình PID được validation chọn

- Fold 0: gains=[0.25, 0.1, 0.0], gate={'quantile': 0.5, 'temperature': 0.5, 'max_gate': 0.5}, validation FPR=3.25%.
- Fold 1: gains=[0.0, 0.0, 0.0], gate={'quantile': 0.5, 'temperature': 1.0, 'max_gate': 0.0}, validation FPR=4.76%.
- Fold 2: gains=[0.0, 0.0, 0.0], gate={'quantile': 0.5, 'temperature': 1.0, 'max_gate': 0.0}, validation FPR=1.64%.
- Fold 3: gains=[0.5, 0.1, 0.1], gate={'quantile': 0.75, 'temperature': 1.0, 'max_gate': 1.0}, validation FPR=4.46%.
- Fold 4: gains=[0.0, 0.0, 0.0], gate={'quantile': 0.5, 'temperature': 1.0, 'max_gate': 0.0}, validation FPR=2.50%.

## Kiểm định quyết định cuối ghép cặp

| Stress | FP của stacking được PID loại | FP chỉ PID tạo | TP của stacking PID làm mất | Exact p | Holm p |
|---|---:|---:|---:|---:|---:|
| clean | 5 | 0 | 1 | 0.0625 | 0.1250 |
| delay_5 | 8 | 0 | 1 | 0.0078 | 0.0312 |
| dropout_20 | 4 | 0 | 1 | 0.1250 | 0.1250 |
| noise_logit_025 | 6 | 0 | 1 | 0.0312 | 0.0938 |

## Phạm vi diễn giải

Delay, missing update và noise là controlled stress tests. Chúng đánh giá cơ chế, không được mô tả như các execution malware mới. Nếu validation chọn gain=0 ở nhiều fold, dữ liệu không hỗ trợ lợi ích PID residual. Nếu gain khác 0 nhưng outer-test không cải thiện, cũng phải báo kết quả âm.
