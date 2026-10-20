# Trạng thái kết quả trong thư mục này

`measured_20261019_ember_identity/` là gói mới nhất dùng 2.000 dòng EMBER 2018 có định danh SHA-256 đã đối chiếu. Gói lưu AL, Fidelity, static gate, kết quả replay và phần thẩm định độc lập tái tính từ CSV. Kết quả cho thấy lợi ích AUC nhỏ của `XAI_full`, nhưng chưa chứng minh giảm FPR, tiết kiệm nhãn hoặc PID; xem README trong gói để dùng đúng phạm vi.

`measured_20261014/` là pilot AL/Fidelity trên CSV cũ và `measured_20261019_gate/` là static-gate cùng audit PID của pilot đó. `measured_20261019_source_inspection/` lưu header/phân bố nhãn archive nguồn; `measured_20261019_source_recovery/` lưu phép tái tạo 2.000 source index. Các gói cũ không có sample SHA-256/tag SOREL đã căn chỉnh và không chứng minh nhãn ransomware.

`measured_20261020_malbehavd_pid_intake/` lưu audit cohort report-only và pilot
VirusTotal 20 SHA. Nó xác nhận pipeline không cần executable và coverage schema
95%, nhưng chưa chứa ablation hoặc kết luận hiệu quả PID.

Các file nằm trực tiếp tại `results/` được tạo bởi mã nguyên mẫu trước đây, không có cùng split/provenance/checkpoint để kiểm tra lại; không dùng chúng làm bằng chứng cho luận văn.
