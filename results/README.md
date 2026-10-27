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
metadata cho confirmatory trên toàn cohort 1.923 mẫu. Collection cuối có 1.922
mẫu usable (99,95%); một SHA trả HTTP 404.

`measured_20261023_malbehavd_pid_confirmatory_1922/` là run PID xác nhận trên
1.922 mẫu, 5 outer folds và 1.000 bootstrap. Gói chứa prediction từng mẫu,
ablation Static/Dynamic/Average/Fixed/P/PI/PID và phép tắt riêng thành phần D
với cùng Kp/Ki/threshold. Kết quả cho thấy dung hợp có lợi nhưng Average đạt AUC
tốt nhất, Fixed có FPR thấp nhất và D không đổi quyết định cuối.

Các file nằm trực tiếp tại `results/` được tạo bởi mã nguyên mẫu trước đây, không có cùng split/provenance/checkpoint để kiểm tra lại; không dùng chúng làm bằng chứng cho luận văn.

`measured_20261023_reliability_pid_exploratory_1922/` là thí nghiệm phát triển
sau confirmatory: dùng 20 tiền tố API, ước lượng độ tin cậy trên calibration và
PID theo dõi trọng số mục tiêu quanh Fixed baseline. Reliability-P giảm FPR
1,33 điểm phần trăm và cải thiện Brier so với Fixed với CI 95% loại trừ 0,
nhưng P vẫn tốt hơn PI/PID; full PID không chứng minh được lợi ích của D. Vì
phương pháp được thiết kế sau khi xem cohort này, kết quả chỉ là exploratory và
cần cohort external/temporal mới để xác nhận.

`measured_20261027_gated_pid_exploratory_1922/` đánh giá uncertainty gate bằng
cross-fitting: gate của mỗi outer fold chỉ được chọn từ OOF static predictions
của các folds còn lại. Với giới hạn early-FN/FP 1% trên development, trung bình
52,67% mẫu được chuyển sang dynamic. Reliability-P đạt FPR thấp nhất 9,97%;
full PID đạt 10,40% và không hơn PI/P. Kết quả tiếp tục hỗ trợ adaptive P, không
hỗ trợ phát biểu full PID vượt trội.

`measured_20261027_pid_defense_evidence_1922/` tổng hợp effect size dùng cho
trình bày: full PID so với Static/Dynamic và adaptive P so với Fixed, kèm
bootstrap ghép cặp 1.000 lần. Full PID tăng AUC 1,34/1,14 điểm phần trăm và
giảm FPR 12,06/8,87 điểm so với Static/Dynamic; các CI 95% loại trừ 0. Gói
cũng giữ rõ kết quả full PID chưa hơn Average/PI để tránh diễn giải quá mức.
