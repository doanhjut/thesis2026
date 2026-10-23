# Pilot PID theo tiến trình sự kiện

Đã đánh giá 1922 mẫu có đủ hai kênh; coverage metadata tĩnh 99.9%. Mỗi mẫu có các mốc 5, 10, 15 và 20 API call.

| Phương pháp | ROC-AUC | AP | FPR (%) | TPR (%) | Brier |
|---|---:|---:|---:|---:|---:|
| Static_only | 0.9702 ± 0.0140 | 0.9700 ± 0.0130 | 23.58 ± 11.74 | 96.56 ± 2.01 | 0.0567 ± 0.0146 |
| Dynamic_only | 0.9733 ± 0.0076 | 0.9802 ± 0.0055 | 16.40 ± 5.57 | 95.46 ± 2.11 | 0.0584 ± 0.0106 |
| Average_50_50 | 0.9844 ± 0.0088 | 0.9883 ± 0.0059 | 13.40 ± 6.49 | 96.57 ± 0.66 | 0.0455 ± 0.0100 |
| Fixed_weight | 0.9832 ± 0.0086 | 0.9872 ± 0.0060 | 11.69 ± 3.58 | 96.06 ± 0.84 | 0.0481 ± 0.0108 |
| P | 0.9838 ± 0.0088 | 0.9878 ± 0.0058 | 13.29 ± 6.07 | 96.36 ± 0.74 | 0.0476 ± 0.0101 |
| PI | 0.9837 ± 0.0089 | 0.9877 ± 0.0059 | 13.83 ± 6.06 | 96.47 ± 0.71 | 0.0474 ± 0.0102 |
| PID | 0.9838 ± 0.0088 | 0.9877 ± 0.0058 | 13.83 ± 6.06 | 96.47 ± 0.71 | 0.0479 ± 0.0105 |

## So sánh ghép cặp PID với Fixed

Bootstrap dự đoán out-of-fold, PID trừ Fixed: ΔAUC=+0.0004 (95% CI [-0.0009, +0.0018]); ΔAP=+0.0003 (95% CI [-0.0008, +0.0014]).
ΔFPR=+2.16 điểm phần trăm (95% CI [+0.84, +3.50]); ΔTPR=+0.40 điểm phần trăm (95% CI [-0.20, +1.00]).
PID có AUC cao hơn ở 3/5 fold, hòa 0/5; FPR tốt hơn ở 0/5 fold, hòa 0/5.

## Kiểm tra đóng góp riêng của D

Ở mốc cuối, |score PID - score PI| trung bình là 0.001746, tối đa 0.097337; số quyết định phân lớp khác nhau là 0/1922.
Pilot này chưa tách được lợi ích gia tăng của thành phần D. Không dùng nó để tuyên bố PID hoàn chỉnh vượt PI.

## Phạm vi kết luận

Kết quả hỗ trợ tính khả thi của dung hợp tĩnh–động và cho thấy xu hướng cải thiện ranking của nhóm adaptive fusion. Khoảng tin cậy PID–Fixed còn cắt qua 0 và FPR biến thiên lớn, nên chưa đủ bằng chứng xác nhận PID giảm cảnh báo nhầm.
Đây là generic Windows malware với trục số sự kiện, không phải benchmark ransomware hay thời gian thực theo giây.

Tệp nguồn: fusion_metrics.csv, event_predictions.csv.gz, timepoint_metrics.csv, fold_effects_pid_minus_fixed.csv và paired_bootstrap_pid_minus_fixed.json.
