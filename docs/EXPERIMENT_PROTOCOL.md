# Giao thức thực nghiệm và điều kiện kết luận

Tài liệu này là checklist trước khi đưa số liệu vào luận văn hoặc slide. Mỗi bảng phải trỏ được về một thư mục run có `artifact_sha256.json` và lệnh `verify` đã pass.

## Active Learning

- Thực nghiệm xác nhận dùng outer test folds. Trong mỗi fold, validation được tách khỏi develop và không đổi trong mọi chiến lược/seed.
- Target label-efficiency được xác định trên validation từ full-pool reference: `0.5 + q(AUC_full - 0.5)` với `q` khai báo trước. Test không tham gia tạo target.
- Khóa dataset hash và split trước khi chạy. Nếu có metadata họ, thời gian hoặc nguồn, tạo split ngoài pipeline rồi truyền `--split-file`.
- Dùng cùng tập khởi tạo cho năm chiến lược trong mỗi seed; dùng cùng ngân sách truy vấn và test cố định.
- Chọn ngưỡng từ validation theo TPR mục tiêu. Báo cả TPR test bên cạnh FPR; không so FPR ở các điểm vận hành không tương đương.
- Báo mean, SD giữa seed, hiệu số paired theo seed và learning curve. SD của năm seed trên cùng test không phải khoảng tin cậy quần thể.
- Chỉ tuyên bố tiết kiệm nhãn nếu đã khai báo trước target validation và nhiều chiến lược thật sự đạt target. Số giờ chuyên gia phải được đo riêng.
- Ngoài AUC/AP, báo standardized partial AUC đến FPR 5% và TPR test tại threshold được chọn trên validation dưới FPR 1%/5%.

## Fidelity

- Lặp trên nhiều outer fold và model seed. Model seed phải tạo fitted model khác nhau theo một cấu hình stochastic đã khóa, không chỉ đổi tên seed trên một thuật toán hoàn toàn deterministic.
- Dùng ít nhất hai training-derived replacement baseline (mean và median) để kiểm tra độ nhạy với phép masking.
- SHAP dùng đúng model đã lưu; tổng bias và contribution phải tái tạo raw log-odds trong sai số số học.
- Baseline che đặc trưng được tính chỉ trên train. Top-k và random control có cùng số tọa độ được chọn.
- Báo AUC trước/sau, AUC drop, thay đổi xác suất, bootstrap theo mẫu test và phân bố qua random mask.
- FF, EC và CF mô tả ba thuộc tính khác nhau, có miền giá trị và giả định khác nhau. Không cộng thành OFS nếu chưa có chuẩn hóa, trọng số và đánh giá độ nhạy được biện minh.
- Che vector đặc trưng chưa chứng minh có một PE hợp lệ tương ứng; mô tả đây là deletion test trong không gian đặc trưng.

## PID và dung hợp tĩnh–động

- Một `row_id` phải ghép được với đúng PE/SHA-256. Mỗi `execution_id` có nhiều time step và báo cáo có SHA-256; không suy ra điểm động từ label, điểm tĩnh hoặc nhiễu ngẫu nhiên.
- Quy tắc biến log thành `p_dynamic` phải được khóa trước test và ghi rõ đó là xác suất đã hiệu chuẩn hay risk score.
- Execution validation và test không giao nhau. Reset PID theo PE execution; nếu mỗi execution chỉ có một quan sát thì P/PI/PID không định danh được lợi ích lịch sử riêng của I và D.
- Khi cửa sổ quan sát không đều, dùng `I_k=clip(I_{k-1}+e_kΔt_k)` và `D_k=(e_k-e_{k-1})/Δt_k`; đặt `D_0=0` và khai báo giới hạn anti-windup.
- Chọn gain, trọng số cố định và threshold chỉ trên validation. So sánh `Static`, `Dynamic`, `Average`, `Fixed`, `P`, `PI`, `PID` trên cùng test.
- Bảng 2×2 `Random/XAI_full × Fixed/PID` trả lời hiệu ứng riêng và tương tác của hai đóng góp. Difference-in-differences phải được báo, kể cả bằng không hoặc trái giả thuyết.
- Đo riêng thời gian thu tín hiệu động, trích đặc trưng, suy luận static/dynamic, dung hợp và end-to-end. Không suy thời gian từ công thức PID.

## Diễn giải

Kết quả chỉ được gọi là “đã đo” khi runner đã chạy trên đầu vào có provenance phù hợp và verification pass. Nếu một giả thuyết không được dữ liệu ủng hộ, giữ nguyên kết quả và thu hẹp kết luận; không điều chỉnh output thủ công.
