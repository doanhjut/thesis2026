# PID v2 meta-fusion — kết quả exploratory

> Cohort này đã được dùng để phát triển phương pháp. Các số dưới đây không phải xác nhận độc lập.

PID v2 học các hệ số của bất đồng logit hiện tại (P), trung bình bất đồng tích lũy (I), biến thiên bước cuối (D) và độ nhiễu của chuỗi. Meta-train, validation và outer-test được tách theo fold; outer-test không chọn C, threshold hoặc hệ số.

| Phương pháp | AUC | AP | FPR | TPR | Brier | FP | FN |
|---|---:|---:|---:|---:|---:|---:|---:|
| Average_50_50 | 0.9891 | 0.9909 | 4.30% | 94.35% | 0.0388 | 26 | 33 |
| Fixed_weight | 0.9891 | 0.9910 | 4.47% | 94.35% | 0.0387 | 27 | 33 |
| Logistic_final | 0.9890 | 0.9909 | 3.46% | 94.50% | 0.0747 | 21 | 32 |
| Logistic_stack | 0.9895 | 0.9911 | 3.68% | 94.84% | 0.0506 | 22 | 30 |
| Max_score | 0.9865 | 0.9883 | 6.94% | 95.07% | 0.0502 | 42 | 29 |
| PID_PI_v2 | 0.9880 | 0.9902 | 3.29% | 94.16% | 0.0502 | 20 | 34 |
| PID_P_v2 | 0.9881 | 0.9903 | 2.79% | 93.99% | 0.0479 | 17 | 35 |
| PID_full_v2 | 0.9893 | 0.9909 | 4.68% | 94.66% | 0.0400 | 28 | 31 |
| PID_robust_v2 | 0.9895 | 0.9911 | 3.35% | 94.32% | 0.0408 | 20 | 33 |

## Hiệu ứng ghép cặp của Robust PID v2

- So với Average: ΔAUC +0.0003 [-0.0015; +0.0021]; ΔFPR -0.9873 [-2.1677; +0.2106] pp; ΔTPR -0.0371 [-1.2786; +1.1491] pp. Các CI còn đi qua 0.
- So với Max-risk: ΔAUC +0.0029 [+0.0001; +0.0058]; ΔFPR -3.5615 [-5.4238; -1.7437] pp; cả hai CI loại 0.
- So với Logistic stacking: ΔAUC -0.0000 [-0.0008; +0.0008]; ΔFPR -0.3222 [-1.2977; +0.5557] pp; chưa có khác biệt rõ.
- So với PID full v2 không có thống kê nhiễu: ΔFPR -1.3316 [-2.6625; -0.1451] pp; CI loại 0, TPR không khác biệt rõ.

## Kết luận sử dụng

Robust PID v2 sửa được hạn chế của controller cũ: các hệ số D dương ở cả năm folds, và biến thể robust giảm FPR so với PID full v2. Trên cohort phát triển, nó có AUC/AP nhỉnh hơn Average và FPR thấp hơn khoảng một điểm phần trăm, nhưng CI vẫn đi qua 0; Logistic stacking vẫn tương đương. Vì vậy đây là ứng viên thuật toán đã cải tiến, chưa phải bằng chứng PID vượt tất cả phương pháp.

Xem `summary.json` để đọc toàn bộ bootstrap và `model_coefficients.json` để kiểm tra hệ số theo từng outer fold. Mọi tuyên bố vượt trội cần cohort external/temporal mới.
