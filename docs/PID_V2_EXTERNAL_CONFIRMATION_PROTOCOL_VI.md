# Protocol xác nhận ngoài cho PID v2

## Mục tiêu

Kiểm tra liệu Robust PID v2 có giảm báo động nhầm so với các luật dung hợp mạnh
trong khi không làm giảm đáng kể khả năng phát hiện. Tập MalBehavD 1.922/1.186
mẫu hiện tại được coi là **development** vì đã tham gia thiết kế thuật toán; nó
không được dùng lại làm confirmatory test.

## Dữ liệu cần bổ sung

- Một corpus Windows malware/benign độc lập hoặc lát cắt theo thời gian/họ mã
  độc chưa xuất hiện trong development.
- Tối thiểu mục tiêu 1.600--2.000 mẫu ghép cặp; nên có ít nhất 800 benign và
  800 malware để FPR chênh 1--2 điểm phần trăm có số đếm đủ diễn giải.
- Mỗi mẫu có SHA-256, nhãn có nguồn, metadata tĩnh và chuỗi ít nhất 40 API
  events theo đúng thứ tự.
- Có thể dùng báo cáo sandbox đã công bố; không cần tải hoặc thực thi PE trong
  môi trường làm luận văn.
- Loại trùng SHA-256 và nhóm biến thể gần nhau trước khi chia train/test. Nếu có
  family hoặc thời gian thu thập, chia theo family/time thay vì chia ngẫu nhiên.

## Thuật toán được khóa trước khi đọc test

Robust PID v2 dùng:

\[
e_t=\operatorname{logit}(p_d(t))-\operatorname{logit}(p_s),
\quad I_t=\frac{1}{t}\sum_{\tau=1}^{t}e_\tau,
\quad D_t=e_t-e_{t-1}.
\]

Điểm meta-fusion là logistic model của logit tĩnh, logit động, \(I_t\), \(D_t\),
độ lệch chuẩn của \(e_{1:t}\) và độ lệch chuẩn của \(D_{1:t}\). Grid regularization,
quy tắc chọn threshold, seed và fold phải giữ đúng như
`scripts/run_pid_v2_meta_fusion.py`; chỉ được sửa trước khi đọc nhãn test và mọi
sửa đổi phải tạo phiên bản protocol mới.

## Baseline bắt buộc

1. Average 50/50.
2. Max-risk.
3. Fixed weight chọn trên validation.
4. Logistic fusion chỉ dùng hai điểm cuối.
5. Temporal Logistic stacking.
6. P, PI và full PID v2 để ablation.

Mọi phương pháp dùng cùng outer folds, cùng base predictions và cùng quy tắc
chọn threshold. Không chọn riêng test subset cho từng phương pháp.

## Endpoint và điều kiện kết luận

Endpoint chính là FPR outer-test tại threshold được chọn trên validation để
hướng tới TPR 95%. Robust PID v2 chỉ được gọi là tốt hơn một baseline khi CI 95%
ghép cặp của \(\Delta FPR\) nằm hoàn toàn dưới 0. Đồng thời phải báo \(\Delta TPR\);
biên non-inferiority, nếu sử dụng, phải được chốt và có lý do nghiệp vụ trước
khi chạy test.

AUC, AP, Brier, pAUC ở FPR thấp, FP/FN tuyệt đối và overhead là endpoint phụ.
Không yêu cầu một phương pháp thắng mọi endpoint; mọi đánh đổi phải được trình
bày. Muốn tuyên bố “vượt tất cả phương pháp dung hợp”, điều kiện FPR phải đạt với
từng baseline bắt buộc và điều kiện TPR đã khóa cũng phải đạt.

## Quy tắc dừng

- Chạy confirmatory đúng một lần sau khi artifact dữ liệu, split, code commit và
  protocol đã được hash.
- Không thay gain, feature, threshold rule hoặc loại mẫu sau khi xem test.
- Nếu tiêu chí không đạt, báo kết quả âm và quay lại development bằng phiên bản
  thuật toán mới; không ghi đè run đã khóa.
