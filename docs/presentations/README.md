# Slide báo cáo với GVHD — đóng góp và bằng chứng thực nghiệm

Bản cập nhật 12/10/2026: **12 slide chính + 5 slide phụ lục**, có lời dẫn cho từng slide. Nội dung tập trung vào điểm khác biệt của ba đóng góp, số liệu đo và việc tiếp thu góp ý Seminar.

- [Xem PDF trên GitHub](Dong_gop_va_bang_chung_thuc_nghiem_GVHD.pdf)
- [Tải PowerPoint chỉnh sửa được](Dong_gop_va_bang_chung_thuc_nghiem_GVHD.pptx?raw=true)
- [Tải ZIP đầy đủ — khoảng 16 MB](Bo_slide_GVHD.zip?raw=true)

ZIP có PowerPoint, PDF, lời dẫn, đánh giá các bảng cũ, kết quả bổ sung, mã chạy, cấu hình, split, seed, 150 checkpoint AL, dự đoán và log kiểm tra. Mã ứng dụng của repository không bị thay đổi.

## Kết quả mới đã đo

AL dùng 1.200 mẫu train/pool, 400 validation, 400 test; 5 seed ghép cặp. Từ 200 nhãn ban đầu, thêm 5 vòng × 100 nhãn. Bảng tại **700 nhãn huấn luyện**, trung bình ± SD qua seed:

| Phương pháp | ROC-AUC | AP | FPR | TPR |
|---|---:|---:|---:|---:|
| Random | 0,9634 ± 0,0063 | 0,9194 | 21,73% | 93,80% |
| Uncertainty | 0,9691 ± 0,0046 | 0,9363 | 19,87% | 95,60% |
| U + H | 0,9676 ± 0,0031 | 0,9371 | 17,20% | 93,00% |
| U + V | 0,9692 ± 0,0062 | 0,9392 | 28,33% | 96,40% |
| XAI đầy đủ | 0,9749 ± 0,0040 | 0,9442 | 17,53% | 95,40% |

AUC của XAI cao hơn Uncertainty ở **5/5 seed**; chênh lệch ghép cặp **+0,005787 ± 0,003904**. FPR thấp hơn chỉ ở **2/5 seed**, chưa thể kết luận giảm FPR ổn định. Ngưỡng chọn trên validation với TPR ≥ 95%; TPR test thực đạt được báo trong bảng. 400 nhãn validation là tài nguyên bổ sung, chưa tính trong ngân sách huấn luyện.

Fidelity dùng **mô hình riêng**, huấn luyện trên toàn bộ 1.200 mẫu, cùng test 400 mẫu. AUC trước che là **0,9802**. Tại k = 25, che top-SHAP cho **0,8185**, còn che ngẫu nhiên cùng k cho trung bình **0,9799** qua 20 lần lặp. Đây là kiểm tra tác động dưới phép masking đã chọn; không lấy AUC của hai pilot trừ nhau để suy ra hiệu quả AL.

## Phạm vi kết luận

- CSV trong repo có 2.000 mẫu và 2.381 đặc trưng; nguồn upstream, họ/thời gian và ý nghĩa nhãn riêng ransomware chưa xác minh. Pilot mới không xác nhận hồi tố các Bảng 4.5–4.9 của luận văn.
- AL chưa chứng minh số nhãn hoặc thời gian chuyên gia tiết kiệm để đạt cùng mục tiêu. Năm seed dùng chung một tập test, không phải năm bộ dữ liệu độc lập.
- Fidelity chỉ che vector đặc trưng bằng baseline train; chưa xác nhận tệp PE hợp lệ hay tính nhân quả. Chưa tổng hợp OFS vì định nghĩa và miền giá trị cần thống nhất.
- PID chưa có điểm động thật ghép theo mẫu đủ để kiểm chứng mức cải thiện. Số cũ chỉ nằm trong phụ lục đối soát. Kế hoạch đo Fixed/P/PI/PID và bảng 2×2 PID × AL nằm trong ZIP; chưa điền số giả lập.

PowerPoint/PDF đã được kiểm tra 17 trang, lời dẫn đầy đủ và số liệu khớp artifacts; ZIP đã kiểm tra giải nén và SHA-256 từng tệp. Bộ báo cáo dùng cho trao đổi khoa học với GVHD, không tự kết luận toàn bộ luận văn đủ điều kiện bảo vệ.
