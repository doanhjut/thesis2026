# Bàn giao cho thread tài liệu

Ngày cập nhật: 19/10/2026.

## Phân chia phạm vi

- **Thread tài liệu:** báo cáo, slide, bài báo, luận văn, kịch bản trình bày và hỏi đáp hội đồng.
- **Thread code hiện tại:** triển khai, kiểm thử, tái lập thực nghiệm và giải thích chi tiết mô hình/công thức.

## Nguồn được phép dùng làm số liệu

Nhánh mã nguồn: `feat/reproducible-thesis-experiments`.

Gói kết quả chuẩn: `results/measured_20261019_ember_identity/`.

- `README.md`: diễn giải học thuật và giới hạn được phép kết luận.
- `al/final_summary_recomputed.csv`: bảng Active Learning cuối.
- `al/paired_differences_recomputed.csv`: hiệu số ghép cặp theo seed.
- `al/aulc_recomputed.csv`: hiệu quả dọc theo ngân sách nhãn.
- `al/al_learning_curve_recomputed.pdf`: learning curve.
- `fidelity/deletion_summary_recomputed.csv`: đối chứng top-SHAP và random mask.
- `fidelity/deletion_recomputed.pdf`: biểu đồ deletion test.
- `static_gate/summary_recomputed.csv`: tỷ lệ route và lỗi quyết định sớm.
- `evidence_assessment.json`: kết luận đã/ chưa được bằng chứng ủng hộ.
- `verification.json`: bằng chứng replay verification.
- `independent_checks.json`: kiểm tra độc lập từ artifact đã tải lên.

`results/measured_20261014/` và `results/measured_20261019_gate/` là pilot cũ trên CSV chưa có sample identity. Không trộn các số đó với gói EMBER mới. Các file nằm trực tiếp trong `results/` là artifact legacy; không dùng làm số liệu cho luận văn, bài báo hoặc slide.

## Kết quả đã kiểm chứng

Ở ngân sách cuối 700 nhãn huấn luyện và 400 nhãn validation:

| Phương pháp | ROC-AUC | AP | FPR | TPR |
|---|---:|---:|---:|---:|
| Random | 0.9376 ± 0.0137 | 0.8847 ± 0.0146 | 50.87% ± 9.97 | 97.40% ± 2.70 |
| Uncertainty | 0.9500 ± 0.0072 | 0.9232 ± 0.0120 | 50.07% ± 6.83 | 97.40% ± 1.34 |
| U+H | 0.9524 ± 0.0054 | 0.9227 ± 0.0111 | 46.33% ± 10.46 | 96.80% ± 2.28 |
| U+V | 0.9530 ± 0.0065 | 0.9216 ± 0.0118 | 52.20% ± 3.97 | 98.40% ± 1.14 |
| XAI_full | 0.9549 ± 0.0098 | 0.9244 ± 0.0169 | 53.40% ± 11.02 | 98.20% ± 1.30 |

`XAI_full` có AUC cao hơn `Uncertainty` trung bình 0,00487 và tốt hơn ở 4/5 seed. AP chỉ tăng trung bình 0,00124. FPR tăng trung bình 3,33 điểm phần trăm và chỉ tốt hơn ở 2/5 seed, nên không trình bày rằng phương pháp giảm cảnh báo nhầm.

Mục tiêu validation AUC khai báo trước là 0,95, nhưng 0/25 cặp phương pháp–seed đạt ngưỡng. Tất cả đều dùng 700 nhãn train. Lần chạy này không chứng minh tiết kiệm nhãn. Normalized test-AUC AULC của `XAI_full` là 0,92722, cao hơn `Uncertainty` 0,00370; chỉ dùng như thước đo mô tả hiệu quả theo ngân sách.

Fidelity trên model cố định:

| k | AUC gốc | AUC sau che top-|SHAP| | AUC sau random mask |
|---:|---:|---:|---:|
| 10 | 0.968800 | 0.903333 | 0.968570 |
| 25 | 0.968800 | 0.837933 | 0.968010 |
| 50 | 0.968800 | 0.604100 | 0.967268 |

EC = 0.409222 và CF = 0.430404. Không tổng hợp OFS vì chưa có chuẩn hóa và trọng số được kiểm định cho miền đặc trưng PE.

Static gate của `XAI_full` route 49,3% test row sang dynamic; early-FN/tổng positive là 1,4% và early-FP/tổng negative là 1,53%. Đây chưa phải kết quả hệ thống hoàn chỉnh vì các row được route chưa có quyết định động cuối.

Verification đã pass 150 checkpoint AL, 120.000 dự đoán AL, 12.500 truy vấn, 63 batch mask, 25.200 dự đoán Fidelity, 25 model–gate pair và 15.000 decision row. Gói tải lên không chứa decision-level CSV của gate nên phần gate chưa được bản thẩm định tái tính từng dòng.

## Giới hạn phải trình bày rõ

1. Định danh SHA-256 và nhãn binary của 2.000 dòng đã được đối chiếu với EMBER 2018. Nhãn 1 là malware nói chung; không được gọi là ransomware. Split ngẫu nhiên theo dòng chưa chứng minh family-held-out, temporal/zero-day hoặc cross-dataset generalization.
2. Chưa có kết quả PID hợp lệ vì chưa có quan sát động thật ghép theo từng mẫu. Không dùng trace demo hoặc số mô phỏng để điền bảng PID.
3. FPR phụ thuộc ngưỡng chọn trên validation theo TPR mục tiêu; luôn báo TPR test bên cạnh FPR.
4. Deletion test diễn ra trong không gian đặc trưng, chưa chứng minh vector sau che tương ứng với một PE hợp lệ.
5. Năm seed dùng chung một test set; SD giữa seed không phải khoảng tin cậy quần thể.
6. `run_status.json` tải lên không ghi Git commit hoặc hash toàn bộ run directory. `SOURCE_FILES.json` và `SHA256SUMS` chỉ khóa chính xác tập artifact đã nhận.

## Thứ tự tài liệu nên hoàn thiện

1. Chốt bảng và hình trong luận văn từ gói kết quả chuẩn.
2. Viết lại phần đóng góp và giới hạn theo đúng bằng chứng.
3. Dựng slide 8–9 trang từ cùng một nguồn số liệu.
4. Tạo bản thảo bài báo sau khi có mô tả dataset/provenance đầy đủ hơn.
5. Bổ sung phần PID sau khi hoàn tất thu thập quan sát động và chạy ablation.

## Prompt mở thread mới

> Hãy đóng vai cố vấn học thuật về Khoa học Máy tính và An toàn Thông tin. Thread này chỉ tập trung hoàn thiện tài liệu gồm luận văn, báo cáo, slide, bài báo và kịch bản bảo vệ. Hãy đọc `docs/DOCUMENTATION_THREAD_HANDOFF.md`, `docs/EXPERIMENT_PROTOCOL.md` và `results/measured_20261019_ember_identity/` trên nhánh `feat/reproducible-thesis-experiments`. Chỉ dùng số liệu đã kiểm chứng trong gói này; không trộn pilot cũ, artifact legacy hoặc tạo số liệu mới. Khi viết, phân biệt rõ kết quả đã chứng minh, kết quả còn yếu và thí nghiệm PID chưa có dữ liệu động thật. Trước tiên hãy kiểm tra cấu trúc tài liệu hiện tại và lập danh sách phần cần cập nhật theo mức ưu tiên.
