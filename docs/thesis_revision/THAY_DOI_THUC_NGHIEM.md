# Những thay đổi về thực nghiệm và phạm vi kết luận

Tài liệu này tóm tắt phần đã cập nhật trong luận văn. Số mục được đối chiếu với bản nguồn và mục lục biên dịch; số trang có thể thay đổi khi dàn trang lại. Hai thực nghiệm bổ sung là phép đo đã thực hiện, có mô hình, cấu hình, split và dự đoán lưu kèm. Chúng không xác nhận hồi tố toàn bộ các bảng của bản trước.

## 1. Phần đã bổ sung bằng phép đo thực

**Học tích cực — Mục 3.3 và 4.3.** Đã chạy năm chiến lược: random, uncertainty, U+H, U+V và XAI đầy đủ, qua năm seed ghép cặp. Các phương pháp dùng cùng split, cùng 200 nhãn khởi tạo theo seed và năm vòng truy vấn thêm 100 mẫu; kết thúc ở 700 nhãn huấn luyện. Có thêm 400 nhãn validation để chọn ngưỡng, không tính vào ngân sách huấn luyện.

Ở ngân sách cuối, XAI đầy đủ đạt ROC-AUC trung bình **0,974873**, so với **0,969087** của uncertainty. AUC cao hơn ở **5/5 seed**, nhưng FPR thấp hơn chỉ ở **2/5 seed**. Luận văn báo cáo AUC, AP, FPR/TPR, đường học, chênh lệch ghép cặp và thời gian tính toán; không đổi kết quả AUC thành tuyên bố giảm cảnh báo nhầm ổn định hoặc tiết kiệm thời gian chuyên gia. Năm seed cùng một test, không phải năm bộ dữ liệu độc lập.

**Fidelity — Mục 3.4 và 4.4.** Đã huấn luyện model riêng trên 1.200 mẫu, tính TreeSHAP và so masking top-k với 20 lần random cùng k ở các mức 10/25/50. Baseline chỉ lấy từ train. Ở k=25, AUC trước che **0,980167**, sau che top-SHAP **0,818533**, còn sau che random trung bình **0,979910**. Có dự đoán trước/sau, chỉ số chiều bị che và bootstrap lưu kèm để kiểm tra.

Các thành phần được báo riêng: **FF thô 2,004518**, **EC 0,304373**, **CF 0,587352** ở thiết lập được mô tả. FF có thể vượt1; EC là tương quan cấu trúc tương đồng, không phải độ ổn định trước nhiễu; CF là mức tách lớp trong không gian SHAP. Kết quả hỗ trợ vai trò của thứ hạng SHAP dưới phép thử masking hiện tại, chưa chứng minh vector sau che là PE hợp lệ hoặc là nguyên nhân hành vi ransomware.

Hai thí nghiệm có cấu hình và ngân sách khác nhau; không lấy chênh lệch AUC giữa chúng để quy cho một thành phần hệ thống.

## 2. Phần đã điều chỉnh để khớp bằng chứng

| Nội dung bản trước | Cách trình bày trong bản chỉnh sửa | Vị trí |
|---|---|---|
| Quy mô 20.000 tệp và mô tả họ ransomware chưa có manifest tương ứng đủ hỗ trợ | Dùng đúng dữ liệu đo: CSV cục bộ 2.000 dòng, 2.381 đặc trưng; công khai chưa xác minh upstream và nghĩa nhãn ransomware-specific | 4.1; A.1–A.2 |
| Bảng PID và độ trễ chưa có dự đoán tĩnh–động thực ghép cặp đủ để tái tính | Trình bày thiết kế, tính chất toán học, giới hạn và đối chứng cần thực hiện; không dùng các con số cũ như kết quả đã xác nhận | 3.2; 4.2 |
| OFS có khác biệt giữa công thức và triển khai | Giải thích điều kiện tổng hợp; không xuất OFS trong kết quả mới, báo thành phần và phép thử có đối chứng | 3.4; 4.4; A.4 |
| Minh họa chưa gắn với một mẫu của phép đo mới | Dùng giải thích SHAP của một hàng kiểm thử có thể truy vết; không suy ra nhãn họ ransomware từ hình | 4.5 |
| Cấu hình tìm kiếm và nhật ký chưa gắn với lần chạy được báo cáo | Liệt kê đúng cấu hình cố định, artifact và phạm vi thời gian của hai lần đo | 4.6; A.1–A.3 |

Tóm tắt Việt/Anh, phần giới thiệu và kết luận cũng đã được điều chỉnh theo cùng phạm vi. Luận văn giữ ba đóng góp làm trục: **thiết kế dung hợp**, **lựa chọn mẫu có đối chứng**, **đánh giá giải thích có phép đo**; không gộp ba mức bằng chứng thành xác nhận toàn hệ thống.

## 3. Đối chiếu với góp ý seminar

| Góp ý cần xử lý | Nội dung đã bổ sung | Phần chưa kết luận |
|---|---|---|
| Tách đóng góp tĩnh/động và PID | Phân biệt cổng với fusion, phân tích PID và thiết kế đối chứng | Chưa đo ưu thế PID trên tín hiệu động thực; xem 3.2, 4.2 |
| Tách đóng góp từng tín hiệu AL | Năm cấu hình, cùng ngân sách, chênh lệch theo seed | Chưa khẳng định từng tín hiệu tự cải thiện ổn định; xem 3.3, 4.3 |
| Mức cải thiện còn nhỏ | Báo AUC/AP kèm FPR, TPR, ngân sách và phạm vi chi phí | Chưa đo tiết kiệm thời gian gán nhãn hoặc lợi ích SOC; xem 4.1, 4.3, 4.7 |
| Độ đo XAI từ dữ liệu khác có phù hợp PE | Định nghĩa rõ masking, EC/CF, random control và giới hạn của vector perturbation | Chưa bảo đảm PE sau che hợp lệ; xem 3.4, 4.4, A.4 |
| Tính tái lập và thực tiễn | Dữ liệu, cấu hình, mẫu giải thích, artifact, độ bất định | Nguồn nhãn và tín hiệu động thực còn cần xác minh; xem 4.1, 4.5–4.7, A.1–A.5 |

**Phát biểu phù hợp khi bảo vệ:** “Em đã bổ sung đối chứng cùng ngân sách và phân tách tín hiệu AL, đồng thời thực hiện phép thử masking có random control. Kết quả hỗ trợ khả năng xếp hạng và đánh giá hành vi mô hình trên dữ liệu hiện có. Phần PID được trình bày ở mức thiết kế và điều kiện kiểm chứng; em chưa khẳng định hiệu quả vận hành của toàn hệ thống.”

Nguồn đối soát: thư mục thí nghiệm AL với `summary.json`, `paired_differences.csv`, `predictions.csv.gz`, `queries.csv`, `config.json`; thư mục Fidelity `run_seed42` với `summary.json`, `mask_metrics.csv`, `mask_predictions.csv`, split và model. Chi tiết việc cần bổ sung nằm trong `VIEC_CAN_BO_SUNG.md`.
