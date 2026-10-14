# Kết quả Active Learning

Ngân sách cuối: 700 nhãn huấn luyện; thêm 400 nhãn validation.

| Phương pháp | ROC-AUC | AP | FPR (%) | TPR (%) |
|---|---:|---:|---:|---:|
| Random | 0.9634 ± 0.0063 | 0.9194 ± 0.0115 | 21.73 ± 4.59 | 93.80 ± 2.28 |
| Uncertainty | 0.9691 ± 0.0046 | 0.9363 ± 0.0076 | 19.87 ± 4.65 | 95.60 ± 1.14 |
| U+H | 0.9676 ± 0.0031 | 0.9371 ± 0.0015 | 17.20 ± 5.15 | 93.00 ± 2.35 |
| U+V | 0.9692 ± 0.0062 | 0.9392 ± 0.0073 | 28.33 ± 7.23 | 96.40 ± 3.05 |
| XAI_full | 0.9749 ± 0.0040 | 0.9442 ± 0.0057 | 17.53 ± 4.85 | 95.40 ± 1.52 |

XAI_full so với Uncertainty: AUC cao hơn ở 5/5 seed; FPR thấp hơn ở 2/5 seed.
Ngưỡng chọn trên validation theo TPR mục tiêu; TPR test được đo riêng. Các seed dùng chung test.
Không quy đổi chất lượng ở cùng ngân sách thành số nhãn hay giờ công tiết kiệm.

Dự đoán từng mẫu: predictions.csv.gz; lựa chọn truy vấn: queries.csv; run này đã lưu 150 checkpoint model.

The CSV source, original file identities and ransomware-specific label semantics are not verified. Row-disjoint measurements are an internal pilot, not a verified ransomware, family-held-out or zero-day benchmark.
