# Pilot PID theo tiến trình sự kiện

Đã đánh giá 199 mẫu có đủ hai kênh; coverage metadata tĩnh 99.5%. Mỗi mẫu có các mốc 5, 10, 15 và 20 API call.

| Phương pháp | ROC-AUC | AP | FPR (%) | TPR (%) | Brier |
|---|---:|---:|---:|---:|---:|
| Static_only | 0.9254 ± 0.0667 | 0.9286 ± 0.0479 | 47.08 ± 28.23 | 96.28 ± 3.44 | 0.0980 ± 0.0654 |
| Dynamic_only | 0.9345 ± 0.0428 | 0.9437 ± 0.0375 | 47.96 ± 16.69 | 96.95 ± 4.71 | 0.1102 ± 0.0305 |
| Average_50_50 | 0.9582 ± 0.0344 | 0.9663 ± 0.0240 | 34.97 ± 23.46 | 96.28 ± 3.44 | 0.0810 ± 0.0318 |
| Fixed_weight | 0.9415 ± 0.0449 | 0.9558 ± 0.0314 | 29.97 ± 15.41 | 93.23 ± 2.39 | 0.0927 ± 0.0381 |
| P | 0.9592 ± 0.0335 | 0.9674 ± 0.0229 | 34.97 ± 23.46 | 96.28 ± 3.44 | 0.0816 ± 0.0326 |
| PI | 0.9583 ± 0.0354 | 0.9660 ± 0.0253 | 34.97 ± 23.46 | 96.28 ± 3.44 | 0.0854 ± 0.0391 |
| PID | 0.9583 ± 0.0354 | 0.9660 ± 0.0253 | 34.97 ± 23.46 | 96.28 ± 3.44 | 0.0854 ± 0.0391 |

## So sánh ghép cặp PID với Fixed

Bootstrap dự đoán out-of-fold, PID trừ Fixed: ΔAUC=+0.0130 (95% CI [-0.0086, +0.0409]); ΔAP=+0.0080 (95% CI [-0.0102, +0.0272]).
ΔFPR=+5.06 điểm phần trăm (95% CI [+0.00, +10.58]); ΔTPR=+4.10 điểm phần trăm (95% CI [+0.94, +8.26]).
PID có AUC cao hơn ở 4/5 fold, hòa 1/5; FPR tốt hơn ở 0/5 fold, hòa 4/5.

## Kiểm tra đóng góp riêng của D

Ở mốc cuối, |score PID - score PI| trung bình là 0.000109, tối đa 0.001196; số quyết định phân lớp khác nhau là 0/199.
Pilot này chưa tách được lợi ích gia tăng của thành phần D. Không dùng nó để tuyên bố PID hoàn chỉnh vượt PI.

## Phạm vi kết luận

Kết quả hỗ trợ tính khả thi của dung hợp tĩnh–động và cho thấy xu hướng cải thiện ranking của nhóm adaptive fusion. Khoảng tin cậy PID–Fixed còn cắt qua 0 và FPR biến thiên lớn, nên chưa đủ bằng chứng xác nhận PID giảm cảnh báo nhầm.
Đây là generic Windows malware với trục số sự kiện, không phải benchmark ransomware hay thời gian thực theo giây.

Tệp nguồn: fusion_metrics.csv, event_predictions.csv.gz, timepoint_metrics.csv, fold_effects_pid_minus_fixed.csv và paired_bootstrap_pid_minus_fixed.json.
