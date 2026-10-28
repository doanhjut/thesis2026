# Kiểm định fusion-only cho đóng góp dung hợp

## Câu hỏi đúng

Phương pháp dung hợp đề xuất có tốt hơn các **phương pháp dung hợp** hay không?
Static-only và Dynamic-only chỉ được giữ làm chẩn đoán kênh, không được dùng làm
đối chứng chính cho tuyên bố vượt trội của luật dung hợp.

## Kết quả trên 1.922 mẫu, 5 outer folds

| Phương pháp dung hợp | ROC-AUC | AP | FPR (FP) | TPR (TP) | Brier |
|---|---:|---:|---:|---:|---:|
| Average 50/50 | 0.9840 | 0.9880 | 14.70% (137) | 96.77% (958) | 0.0450 |
| Max-risk | 0.9779 | 0.9794 | 16.63% (155) | 96.77% (958) | 0.0604 |
| Fixed weight | 0.9821 | 0.9862 | 12.45% (116) | 96.06% (951) | 0.0487 |
| Logistic stacking | 0.9819 | 0.9867 | 14.91% (139) | 96.57% (956) | 0.0454 |
| Adaptive P | 0.9827 | 0.9867 | 11.16% (104) | 95.96% (950) | 0.0456 |
| Adaptive PI | 0.9827 | 0.9867 | 11.48% (107) | 95.96% (950) | 0.0456 |
| Full PID | 0.9828 | 0.9868 | 11.59% (108) | 95.96% (950) | 0.0455 |

## Phát biểu được dữ liệu hỗ trợ

So với Fixed weight, **Adaptive P** giảm FPR từ 12.45% xuống
11.16%, tương ứng -1.28 pp, CI 95%
[-2.47 pp; -0.11 pp]. Brier giảm
-0.00306, CI 95%
[-0.00585; -0.00030]. Chênh lệch
TPR là -0.10 pp và CI đi qua 0. Ở số đếm gộp, Adaptive P
tạo 104 báo động nhầm so với 116 của Fixed, trong khi số dương tính
đúng là 950 so với 951.

Đây là bằng chứng rằng **trọng số thích nghi theo độ tin cậy** có lợi hơn trọng số
cố định ở operating point đã khóa. Average và Logistic stacking vẫn tạo đánh đổi
khác: AUC/TPR cao hơn nhưng FPR cao hơn. Vì vậy Adaptive P là một điểm trên biên
đánh đổi, không phải phương pháp thắng mọi chỉ số.

## Full PID so với các luật dung hợp bên ngoài họ PID

Các hiệu ứng dưới đây là `Full PID - baseline`; giá trị FPR âm có lợi cho PID,
giá trị TPR/AUC dương có lợi cho PID.

| Baseline | ΔFPR (CI 95%) | ΔTPR (CI 95%) | ΔAUC (CI 95%) |
|---|---:|---:|---:|
| Average 50/50 | -3.13 pp [-4.40 pp; -1.82 pp] | -0.80 pp [-1.41 pp; -0.20 pp] | -0.12 pp [-0.29; +0.03] |
| Max-risk | -5.04 pp [-6.55 pp; -3.43 pp] | -0.83 pp [-1.62 pp; -0.10 pp] | +0.49 pp [+0.16; +0.84] |
| Fixed weight | -0.87 pp [-1.93 pp; +0.21 pp] | -0.09 pp [-0.81 pp; +0.61 pp] | +0.07 pp [-0.08; +0.21] |
| Logistic stacking | -3.32 pp [-4.94 pp; -1.72 pp] | -0.62 pp [-1.21 pp; +0.00 pp] | +0.08 pp [-0.19; +0.37] |

Full PID có FPR quan sát thấp nhất trong nhóm baseline bên ngoài họ PID. Mức giảm
FPR có CI loại 0 so với Average, Max-risk và Logistic stacking; so với Fixed,
CI FPR còn đi qua 0 nhưng Brier cải thiện. Tuy nhiên, so với Average/Max-risk,
PID đồng thời giảm khoảng 0,8 điểm phần trăm TPR. Đây là đánh đổi vận hành, không
phải thống trị toàn diện. Không được mô tả các hàng này là so sánh "cùng TPR"
vì threshold được chọn riêng trên validation và TPR outer-test có sai khác.

## Điều dữ liệu bác bỏ

Full PID không hơn Adaptive P: chênh lệch FPR là
+0.43 pp, CI 95% [+0.11 pp;
+0.86 pp], trong khi TPR không đổi. Full PID cũng không
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
