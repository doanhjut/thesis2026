# Exploratory uncertainty-gated PID

> Gate của mỗi outer fold được chọn từ OOF predictions thuộc các folds còn lại. Phương pháp vẫn là exploratory vì fusion đã được phát triển sau khi xem cohort này.

Gate chính giới hạn early-FNR và early-FPR trên development ở 1.0%.

| Phương pháp | Chuyển dynamic | AUC | FPR | TPR | Brier |
|---|---:|---:|---:|---:|---:|
| Average_50_50 | 52.67% | 0.9762 | 13.08% | 96.46% | 0.0465 |
| Fixed_weight | 52.67% | 0.9756 | 10.62% | 95.65% | 0.0484 |
| Logistic_stack | 52.67% | 0.9773 | 14.58% | 96.46% | 0.0459 |
| Reliability_P | 52.67% | 0.9761 | 9.97% | 95.76% | 0.0466 |
| Reliability_PI | 52.67% | 0.9761 | 10.29% | 95.76% | 0.0466 |
| Reliability_PID | 52.67% | 0.9760 | 10.29% | 95.76% | 0.0466 |
| Reliability_full_PID | 52.67% | 0.9760 | 10.40% | 95.76% | 0.0466 |

## Bootstrap ghép cặp

- Reliability-P trừ Fixed: ΔFPR -0.66 điểm phần trăm, CI 95% [-1.53; +0.21]; ΔTPR +0.10 điểm phần trăm.
- Full PID trừ PI: ΔFPR +0.11 điểm phần trăm, CI 95% [+0.00; +0.33]; ΔTPR +0.00 điểm phần trăm.
- Full PID trừ Average: ΔFPR -2.72 điểm phần trăm, CI 95% [-3.99; -1.50]; ΔTPR -0.71 điểm phần trăm, CI [-1.40; -0.10].

## Kết luận

Gate làm rõ giá trị của adaptive fusion trên nhóm static bất định, nhưng không đảo ngược ablation: P vẫn có FPR tốt nhất, còn full PID không hơn PI/P. Full PID giảm FPR so với Average nhưng đánh đổi TPR. Vì vậy run này chưa chứng minh full PID vượt trội.
