# Bàn giao cho thread tài liệu

Ngày cập nhật: 16/10/2026.

## Phân chia phạm vi

- **Thread tài liệu:** báo cáo, slide, bài báo, luận văn, kịch bản trình bày và hỏi đáp hội đồng.
- **Thread code hiện tại:** triển khai, kiểm thử, tái lập thực nghiệm và giải thích chi tiết mô hình/công thức.

## Nguồn được phép dùng làm số liệu

Nhánh mã nguồn: `feat/reproducible-thesis-experiments`.

Gói kết quả chuẩn: `results/measured_20261014/`.

- `al/REPORT.md`: bảng Active Learning.
- `al/paired_differences.csv`: hiệu số paired theo seed.
- `al/al_learning_curves.pdf`: learning curve.
- `al/al_paired_differences.pdf`: độ ổn định theo seed.
- `fidelity/REPORT.md`: kết quả Fidelity.
- `fidelity/fidelity_deletion.pdf`: đối chứng top-SHAP và random mask.
- `verification.json`: bằng chứng replay verification.
- `dynamic_template/`: mẫu thu thập dữ liệu PID; đây chưa phải kết quả.

Các file nằm trực tiếp trong `results/` là artifact legacy, không có đủ provenance và checkpoint để kiểm tra độc lập. Không dùng chúng làm số liệu cho luận văn, bài báo hoặc slide.

## Kết quả đã kiểm chứng

Ở ngân sách cuối 700 nhãn huấn luyện và 400 nhãn validation:

| Phương pháp | ROC-AUC | AP | FPR | TPR |
|---|---:|---:|---:|---:|
| Random | 0.9634 ± 0.0063 | 0.9194 ± 0.0115 | 21.73% ± 4.59 | 93.80% ± 2.28 |
| Uncertainty | 0.9691 ± 0.0046 | 0.9363 ± 0.0076 | 19.87% ± 4.65 | 95.60% ± 1.14 |
| XAI_full | 0.9749 ± 0.0040 | 0.9442 ± 0.0057 | 17.53% ± 4.85 | 95.40% ± 1.52 |

`XAI_full` có AUC cao hơn `Uncertainty` ở 5/5 seed. FPR chỉ thấp hơn ở 2/5 seed, nên không trình bày rằng phương pháp luôn giảm FPR.

Fidelity trên model cố định:

| k | AUC gốc | AUC sau che top-|SHAP| | AUC sau random mask |
|---:|---:|---:|---:|
| 10 | 0.980167 | 0.913933 | 0.979867 |
| 25 | 0.980167 | 0.818533 | 0.979910 |
| 50 | 0.980167 | 0.671200 | 0.979263 |

EC = 0.304373 và CF = 0.587352. Không tổng hợp OFS vì chưa có chuẩn hóa và trọng số được kiểm định cho miền đặc trưng PE.

Verification đã pass 150 checkpoint AL, 120.000 dự đoán AL, 12.500 truy vấn, 63 batch mask và 25.200 dự đoán Fidelity.

## Giới hạn phải trình bày rõ

1. Nguồn PE gốc, họ malware, mốc thời gian và ý nghĩa ransomware cụ thể của nhãn CSV chưa được xác minh. Kết quả hiện là pilot row-disjoint nội bộ.
2. Chưa có kết quả PID hợp lệ vì chưa có quan sát động thật ghép theo từng mẫu. Không dùng trace demo hoặc số mô phỏng để điền bảng PID.
3. FPR phụ thuộc ngưỡng chọn trên validation theo TPR mục tiêu; luôn báo TPR test bên cạnh FPR.
4. Deletion test diễn ra trong không gian đặc trưng, chưa chứng minh vector sau che tương ứng với một PE hợp lệ.
5. Năm seed dùng chung một test set; SD giữa seed không phải khoảng tin cậy quần thể.

## Thứ tự tài liệu nên hoàn thiện

1. Chốt bảng và hình trong luận văn từ gói kết quả chuẩn.
2. Viết lại phần đóng góp và giới hạn theo đúng bằng chứng.
3. Dựng slide 8–9 trang từ cùng một nguồn số liệu.
4. Tạo bản thảo bài báo sau khi có mô tả dataset/provenance đầy đủ hơn.
5. Bổ sung phần PID sau khi hoàn tất thu thập quan sát động và chạy ablation.

## Prompt mở thread mới

> Hãy đóng vai cố vấn học thuật về Khoa học Máy tính và An toàn Thông tin. Thread này chỉ tập trung hoàn thiện tài liệu gồm luận văn, báo cáo, slide, bài báo và kịch bản bảo vệ. Hãy đọc `docs/DOCUMENTATION_THREAD_HANDOFF.md`, `docs/EXPERIMENT_PROTOCOL.md` và `results/measured_20261014/` trên nhánh `feat/reproducible-thesis-experiments`. Chỉ dùng số liệu đã kiểm chứng trong gói này; không dùng artifact legacy hoặc tạo số liệu mới. Khi viết, phân biệt rõ kết quả đã chứng minh, kết quả còn yếu và thí nghiệm PID chưa có dữ liệu động thật. Trước tiên hãy kiểm tra cấu trúc tài liệu hiện tại và lập danh sách phần cần cập nhật theo mức ưu tiên.
