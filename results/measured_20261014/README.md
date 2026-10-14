# Gói kết quả đo ngày 2026-10-14

Lần chạy này dùng commit `4bd07c6`, dataset SHA-256 `c733cc0c3e0950fa1d05d57d34c69d0a034383e0c1a2fde0e6878b9e2e8c3668` và cấu hình mặc định của `scripts/run_experiments.py run`.

Verifier đã nạp lại 150 checkpoint AL và 63 batch mask Fidelity, rồi tái tính 120.000 dự đoán AL, 12.500 truy vấn và 25.200 dự đoán mask. Trạng thái chi tiết nằm trong `verification.json`.

## Kết quả chính

- Ở ngân sách cuối 700 nhãn train, `XAI_full` đạt ROC-AUC `0.9749 ± 0.0040`; `Uncertainty` đạt `0.9691 ± 0.0046`. Hiệu số AUC dương ở 5/5 seed.
- FPR test của `XAI_full` là `17.53% ± 4.85`, so với `19.87% ± 4.65` của `Uncertainty`, nhưng hiệu số theo seed chỉ tốt hơn ở 2/5 seed. Không kết luận XAI_full luôn giảm FPR.
- Fidelity trên model cố định có AUC gốc `0.980167`. Che top-|SHAP| làm AUC còn `0.913933`, `0.818533`, `0.671200` lần lượt tại k=10, 25, 50; random control tương ứng gần `0.98`.
- EC=`0.304373`, CF=`0.587352`. OFS không được tổng hợp vì chưa có chuẩn hóa/trọng số được kiểm định cho miền PE.
- PID chưa có kết quả trong gói này vì kho chưa chứa quan sát động thật ghép theo mẫu. Template yêu cầu 800 quan sát đã được runner tạo cục bộ; trace demo bị từ chối.

`al/` và `fidelity/` chứa báo cáo Markdown, bảng LaTeX/CSV và biểu đồ PDF/PNG. Đây là gói gọn phục vụ review. Checkpoint, dự đoán từng mẫu và mask indices của run đầy đủ không được commit; chạy lại lệnh trong README gốc để tái tạo và dùng `verify` để kiểm tra.

Nguồn tệp PE gốc, quan hệ họ, thời gian và ý nghĩa ransomware cụ thể của nhãn CSV chưa được xác minh. Các con số trên là pilot row-disjoint nội bộ, không phải benchmark family-held-out hoặc zero-day.
