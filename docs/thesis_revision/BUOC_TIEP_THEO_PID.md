# Bước tiếp theo để xác nhận đóng góp PID

Hai phần XAI-Guided Active Learning và Fidelity đã có kết quả xác nhận. Khoảng trống còn lại là dữ liệu động ghép với điểm tĩnh theo cùng mẫu.

## Dữ liệu cần chuẩn bị

Mỗi mẫu cần tối thiểu:

| Cột | Ý nghĩa |
|---|---|
| `sha256` | Định danh tệp, duy nhất và dùng để ghép tĩnh–động |
| `label` | 0/1 với nguồn nhãn được ghi rõ |
| `split_group` | Họ, nguồn hoặc thời gian để tránh rò rỉ khi chia tập |
| `static_score` | Xác suất đã hiệu chỉnh từ mô hình tĩnh đã khóa |
| `dynamic_score_t0...tn` hoặc `event_time,event_type,value` | Chuỗi điểm/hành vi động theo thời gian |
| `sandbox_status` | Thành công, timeout, lỗi hoặc không quan sát được |
| `dynamic_latency_ms` | Thời gian từ kích hoạt đến khi có điểm động |

Không cần gửi executable lên Git. Có thể giữ mẫu trong kho an toàn và chỉ xuất feature/report cùng SHA-256.

## Ablation bắt buộc

Chạy trên cùng split, scorer nguồn và threshold protocol:

1. Static-only.
2. Dynamic-only.
3. Fixed-weight fusion.
4. P fusion.
5. PI fusion.
6. PID fusion.

Metric chính: ROC-AUC, AP, calibration, FPR tại TPR mục tiêu, số mẫu qua sandbox, latency động và latency đầu cuối. Với PID cần khóa `Kp`, `Ki`, `Kd`, bước thời gian, giới hạn tích phân, clipping trọng số, reset state và thứ tự mẫu trước khi đọc test.

## Tiêu chí hoàn thành

- tất cả biến thể chạy trên ít nhất 5 folds hoặc các split theo thời gian/họ phù hợp;
- chênh lệch được ghép cặp theo split, báo trung bình, độ lệch chuẩn và số split thắng;
- chứng minh PID tốt hơn fixed/PI trên ít nhất một mục tiêu vận hành mà không làm suy giảm nghiêm trọng mục tiêu còn lại;
- lưu cấu hình, dự đoán từng mẫu, log trạng thái, manifest, hash và verification;
- nếu PID không vượt đối chứng, luận văn giữ PID là thiết kế và báo trung thực kết quả âm.

## Việc người dùng cần làm

Chuẩn bị một thư mục chứa dynamic reports hoặc bảng sự kiện có SHA-256 trùng với manifest mẫu tĩnh. Khi có dữ liệu này, runner hiện tại có thể được nối với pipeline ablation mà không cần chạy lại AL/Fidelity.
