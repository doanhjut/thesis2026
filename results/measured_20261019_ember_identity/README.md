# Bằng chứng EMBER identity-aligned — 19/10/2026

Gói này lưu nguyên trạng các artifact người dùng cung cấp từ lần chạy outputs\\ember_measured_run, sau đó tái tính các bảng tóm tắt trực tiếp từ metrics.csv, mask_metrics.csv và split_manifest.csv. SOURCE_FILES.json ghi hash của từng tệp nhập; SHA256SUMS khóa toàn bộ gói sau khi tạo.

## Phạm vi và kiểm tra

- Nguồn được khai báo là EMBER 2018 static: 2.000 dòng, split thành train pool 1.200, validation 400 và test 400; mỗi split giữ tỷ lệ 3:1 benign/malware.
- AL replay đã qua: 150 checkpoint, 120.000 prediction record, 12.500 query record.
- Fidelity replay đã qua: 63 mask batch, 25.200 prediction record.
- Static-gate replay được báo qua: 25 model–gate pair, 15.000 decision row. Gói upload không chứa decision-level CSV, nên bản thẩm định này không tự tái tính được gate từ từng dòng.
- run_status.json không ghi Git commit hay hash của toàn bộ run directory. Gói này khóa đúng các tệp đã nhận, không suy diễn code version ngoài artifact.

## Active Learning

Tại 700 nhãn train, XAI_full đạt ROC-AUC test **0.9549 ± 0.0098** và AP **0.9244**.

So với Uncertainty, chênh lệch AUC cuối trung bình là **+0.0049**, tốt hơn ở **4/5 seed**. Chênh lệch AP chỉ **+0.0012** và FPR tăng trung bình **+3.33 điểm phần trăm**; FPR chỉ tốt hơn ở **2/5 seed**. Dữ liệu ủng hộ lợi ích AUC nhỏ, chưa ủng hộ phát biểu giảm cảnh báo nhầm.

Mục tiêu validation AUC được khai báo trước là **0.95**, nhưng **0/25** cặp method–seed đạt mục tiêu. Tất cả phương pháp đều dùng 700 nhãn train, nên lần chạy này **không chứng minh tiết kiệm nhãn**. Normalized AULC test-AUC của XAI_full là 0.9272, cao hơn Uncertainty +0.0037; đây là mô tả hiệu quả theo ngân sách, chưa phải số nhãn tiết kiệm.

Tổng thời gian query trung bình qua năm vòng của XAI_full là 0.423s, gấp 17.2 lần Uncertainty, và bằng 17.0% thời gian train của chính nó trên tập nhỏ này. Đây là overhead tính toán, không phải latency production.

## Fidelity

Model cố định có ROC-AUC 0.9688. Che top-|SHAP| làm giảm AUC lần lượt 0.0655, 0.1309, 0.3647 tại k=10/25/50; random control cùng kích thước chỉ giảm trung bình 0.0002, 0.0008, 0.0015. Kết quả cho thấy TreeSHAP xếp hạng đúng các tọa độ mà model nhạy dưới phép masking đã định nghĩa.

EC=0.4092, CF=0.4304. OFS để trống vì chưa có quy tắc chuẩn hóa/trọng số chung được kiểm định. Masking vector EMBER không tạo ra PE thực thi hợp lệ, nên không diễn giải thành quan hệ nhân quả hoặc fidelity ở mức chương trình.

## Static gate và PID

XAI_full chuyển trung bình 49.3% test row sang dynamic, so với 53.5% của Uncertainty. Early-FN/tổng positive là 1.4% và early-FP/tổng negative là 1.53%. Đây là bằng chứng cho static gate; các row được route chưa có quyết định cuối.

PID/fusion không chạy vì chưa có dynamic report thật ghép với ID. Gói này không cung cấp bằng chứng cho PID, static+dynamic, latency end-to-end, ransomware-specific, family-held-out hay temporal/zero-day generalization.
