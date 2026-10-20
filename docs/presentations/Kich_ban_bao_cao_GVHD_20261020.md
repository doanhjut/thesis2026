# Kịch bản báo cáo với giảng viên hướng dẫn

Thời lượng mục tiêu: **10–12 phút**, không demo. Bộ slide dùng kết quả đã đo trong
repository; PID được trình bày đúng là pilot, còn AL và Fidelity là thực nghiệm
xác nhận.

## Trang 1 — Mục tiêu buổi làm việc (45 giây)

“Hôm nay em xin trình bày bằng chứng thực nghiệm cho ba đóng góp đã chốt. Hai
đóng góp XAI-Guided Active Learning và đánh giá Fidelity đã hoàn tất thực nghiệm
xác nhận. PID đã chạy end-to-end trên pilot 199 mẫu; em đang mở rộng lên cohort
1.923 mẫu để chốt kết luận trước buổi bảo vệ sau 20 ngày. Em xin thầy thống nhất
phạm vi kết luận và ưu tiên hoàn thiện.”

## Trang 2 — Điểm khác với nghiên cứu trước (70 giây)

“Đề tài không coi mô hình phân loại đơn lẻ là đóng góp. Ba khoảng trống em xử lý
là: trọng số tĩnh–động thường được cố định; Active Learning thường chỉ dùng độ
bất định; SHAP thường chỉ được dùng để minh họa. Tương ứng, luận văn bổ sung PID
cho dung hợp, H/V cho lựa chọn mẫu, và deletion/stability để kiểm tra giải thích.
Mỗi phần có đối chứng và đại lượng đo riêng.”

## Trang 3 — Kiến trúc và ranh giới ba đóng góp (60 giây)

“Luồng phát hiện gồm mô hình tĩnh, cổng bất định, phân tích động và dung hợp.
PID chỉ giải quyết luật dung hợp. Active Learning dùng giải thích để chọn dữ liệu
gán nhãn và cập nhật mô hình tĩnh. Fidelity kiểm tra xem thứ hạng SHAP có thật sự
gắn với dự đoán hay không. Việc tách này giúp em trả lời rõ thành phần nào tạo ra
hiệu quả nào.”

## Trang 4 — PID Fusion (100 giây)

“Pilot dùng 199 mẫu có hai kênh ghép cặp và năm outer folds. Dung hợp giúp AUC
tăng từ 0,9254 ở tĩnh và 0,9345 ở động lên khoảng 0,958–0,959. PID cao hơn fixed
weight trung bình 0,013 AUC và tăng TPR 4,10 điểm phần trăm. Tuy nhiên khoảng tin
cậy của AUC còn cắt 0, FPR tăng 5,06 điểm phần trăm, và PI/PID không làm thay đổi
quyết định nào. Vì vậy bằng chứng hiện tại xác nhận lợi ích của dung hợp thích
nghi, chưa xác nhận lợi ích riêng của D hoặc giảm FPR. Em đang chạy cohort đầy đủ
để trả lời đúng hai câu hỏi này.”

Nếu thầy hỏi vì sao vẫn giữ PID: “PID là giả thuyết cơ chế cần kiểm định. Pilot
cho thấy P đã phản ứng đủ nhanh, nên thực nghiệm mở rộng có thể dẫn tới một trong
hai kết luận đều có giá trị: D hữu ích khi chuỗi dài và nhiễu, hoặc P/PI là cấu
hình tối giản phù hợp hơn. Em không chọn lại số để ép PID thắng.”

## Trang 5 — XAI-Guided Active Learning (100 giây)

“Thực nghiệm dùng 2.000 mẫu EMBER có định danh, năm folds và năm seed trong mỗi
fold. XAI-full cần trung bình 492 nhãn để đạt mục tiêu validation, thấp hơn 92
nhãn so với Random và 28 nhãn so với Uncertainty. Về chất lượng toàn đường học,
U+H tăng ROC-AULC 0,00425 và AP-AULC 0,01498 so với Random, thắng ở cả năm folds.
Chi phí tính query của XAI-full chiếm 5,42% tổng train cộng query. Kết quả cho
thấy H giúp đường học, còn V/full score hỗ trợ đạt mục tiêu với ít nhãn hơn.”

## Trang 6 — Fidelity và độ phù hợp của chỉ số (90 giây)

“Em không dùng điểm OFS tổng hợp khi các thành phần chưa có cùng thang đo. Thay
vào đó em kiểm tra từng thuộc tính. Khi che 25 đặc trưng top-SHAP, AUC giảm
0,1359; che ngẫu nhiên cùng số đặc trưng chỉ giảm 0,0005. Xu hướng tăng theo k=10,
25, 50 và lặp lại với mean/median baseline trên 25 mô hình. Độ tương quan thứ hạng
SHAP là 0,614 trong cùng fold và 0,551 giữa các fold. Kết luận đúng là SHAP bám
vào hành vi mô hình trong không gian đặc trưng EMBER; chưa phải bằng chứng nhân
quả trên file PE thực thi.”

## Trang 7 — Tiếp thu góp ý Seminar (75 giây)

“Các góp ý đã được chuyển thành phép đo: ablation P/PI/PID; random control và ba
mức masking; 25 cặp fold–seed cho Active Learning; báo AULC, ngân sách nhãn,
overhead, FPR/TPR và khoảng tin cậy. Vì vậy phần sửa không chỉ thêm diễn giải mà
đã bổ sung các đối chứng để truy nguyên đóng góp.”

## Trang 8 — Việc còn lại trong 20 ngày (60 giây)

“Cohort PID đã khóa 1.923 mẫu và hiện thu được 493 mẫu, tương đương 25,64%. Em sẽ
chạy khi coverage đạt ít nhất 90%, sau đó dùng đúng năm fold và protocol đã khóa.
Các ngày còn lại dành cho cập nhật bảng/hình, đối soát claim–evidence và luyện
hỏi đáp. Nếu kết quả full-cohort không cho thấy D cải thiện, luận văn sẽ báo kết
quả âm và thu hẹp phát biểu, không thay đổi dữ liệu hay split.”

## Trang 9 — Đề nghị thầy thống nhất (45 giây)

“Với hai đóng góp đã có confirmatory evidence, một đóng góp PID đã có pilot tái
lập và quy trình mở rộng rõ ràng, em đề nghị giữ ba đóng góp và tiếp tục mục tiêu
bảo vệ trong đợt này. Trọng tâm 20 ngày là hoàn tất PID và khóa mọi phát biểu theo
artifact. Thông điệp cuối của luận văn là hiệu quả vận hành: dung hợp thích nghi,
giảm chi phí nhãn và giải thích có thể kiểm chứng.”

## Ba câu trả lời cần giữ nhất quán

1. **PID đã tốt hơn chưa?** Đã có xu hướng tăng ranking so với fixed; chưa chứng
   minh D hoặc giảm FPR. Kết luận xác nhận chờ cohort đầy đủ.
2. **AUC tăng nhỏ có ý nghĩa gì?** Không diễn giải riêng AUC; dùng chênh lệch ghép
   cặp, CI, low-FPR, TPR/FPR, ngân sách nhãn và overhead.
3. **OFS ở đâu?** Chưa tổng hợp vì thiếu chuẩn hóa chung đã được xác nhận. Báo
   Faithfulness/deletion, stability và contrastive evidence riêng để tránh một
   điểm số đẹp nhưng khó giải thích.
