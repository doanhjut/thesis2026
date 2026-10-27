# Gói bằng chứng PID dùng cho bảo vệ

## Thông điệp có thể bảo vệ

Full reliability-aware PID cải thiện rõ so với hai kênh độc lập. Trên 1.922 dự
đoán out-of-fold, AUC tăng từ 0.9702 (Static) và
0.9720 (Dynamic) lên 0.9825; FPR giảm từ
23.58% và 20.38% xuống
11.58%.

| Phương pháp | AUC | AP | FPR | TPR | Brier |
|---|---:|---:|---:|---:|---:|
| Static | 0.9702 | 0.9700 | 23.58% | 96.56% | 0.0567 |
| Dynamic | 0.9720 | 0.9794 | 20.38% | 95.45% | 0.0589 |
| Full PID | **0.9825** | **0.9864** | **11.58%** | 95.96% | **0.0455** |

## Effect size và khoảng tin cậy

- Full PID − Static: ΔAUC **+1.34 điểm phần trăm**,
  CI 95% `[+0.78; +1.94]`;
  ΔFPR **-12.06 điểm phần trăm**,
  CI `[-14.60; -9.57]`.
- Full PID − Dynamic: ΔAUC **+1.14 điểm phần trăm**,
  CI `[+0.68; +1.61]`;
  ΔFPR **-8.87 điểm phần trăm**,
  CI `[-11.16; -6.59]`.
- Adaptive P − Fixed: ΔFPR **-1.33 điểm phần trăm**,
  CI `[-2.45; -0.21]`;
  ΔBrier `-0.00308`, CI
  `[-0.00560; -0.00071]`.

Mức giảm FPR tương đối của full PID là
**50.9% so với Static** và
**43.2% so với Dynamic**.
Adaptive P giảm FPR tương đối
**10.4% so với Fixed**.

## Giới hạn phải nói cùng kết quả

Full PID chưa hơn Average/P/PI trên mọi tiêu chí. Full PID − PI có ΔAUC
`+0.007` điểm phần trăm với CI đi qua 0 và ΔFPR
`+0.11` điểm phần trăm. Vì vậy bằng chứng hỗ trợ
**PID-family fusion so với phân tích đơn kênh** và hỗ trợ **adaptive P so với
Fixed**, nhưng không hỗ trợ phát biểu thành phần D tạo lợi ích gia tăng.

## Câu trình bày đề xuất

> Trên 1.922 mẫu và năm outer folds, full PID fusion tăng AUC khoảng 1,34 điểm
> phần trăm và giảm FPR 12,06 điểm phần trăm so với Static; so với Dynamic, AUC
> tăng 1,14 điểm và FPR giảm 8,87 điểm. Bootstrap ghép cặp cho các hiệu ứng này
> có CI 95% không đi qua 0. Ablation cho thấy phần lớn lợi ích đến từ khâu P;
> I và D chưa tạo thêm khác biệt trong horizon 1–20 sự kiện.
