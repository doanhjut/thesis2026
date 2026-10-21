# Trạng thái kết quả trong thư mục này

`measured_20261019_ember_identity/` là gói mới nhất dùng 2.000 dòng EMBER 2018 có định danh SHA-256 đã đối chiếu. Gói lưu AL, Fidelity, static gate, kết quả replay và phần thẩm định độc lập tái tính từ CSV. Kết quả cho thấy lợi ích AUC nhỏ của `XAI_full`, nhưng chưa chứng minh giảm FPR, tiết kiệm nhãn hoặc PID; xem README trong gói để dùng đúng phạm vi.

`measured_20261014/` là pilot AL/Fidelity trên CSV cũ và `measured_20261019_gate/` là static-gate cùng audit PID của pilot đó. `measured_20261019_source_inspection/` lưu header/phân bố nhãn archive nguồn; `measured_20261019_source_recovery/` lưu phép tái tạo 2.000 source index. Các gói cũ không có sample SHA-256/tag SOREL đã căn chỉnh và không chứng minh nhãn ransomware.

`measured_20261020_malbehavd_pid_intake/` lưu audit cohort report-only và pilot
VirusTotal 20 SHA. Nó xác nhận pipeline không cần executable và coverage schema
95%, nhưng chưa chứa ablation hoặc kết luận hiệu quả PID.

`measured_20261020_malbehavd_pid_pilot200/` là pilot đo thật trên 200 SHA đã
chọn trước, trong đó 199 mẫu có đủ hai kênh. Gói có dự đoán từng mẫu, ablation
Static/Dynamic/Average/Fixed/P/PI/PID, bootstrap ghép cặp, bảng LaTeX và biểu đồ.
Kết quả hỗ trợ tính khả thi của adaptive fusion, nhưng chưa chứng minh PID giảm
FPR hoặc thành phần D vượt PI; xem README trong gói trước khi trích dẫn.

`measured_20261020_malbehavd_pid_full_collection_progress/` lưu snapshot thu
metadata cho confirmatory trên toàn cohort 1.923 mẫu. Hiện có 993 mẫu usable
(51,64%); 929 mẫu còn lại được hoãn sau khi API trả HTTP 429, nên chưa chạy
mô hình và chưa phân tích missingness cuối cùng.

Các file nằm trực tiếp tại `results/` được tạo bởi mã nguyên mẫu trước đây, không có cùng split/provenance/checkpoint để kiểm tra lại; không dùng chúng làm bằng chứng cho luận văn.
