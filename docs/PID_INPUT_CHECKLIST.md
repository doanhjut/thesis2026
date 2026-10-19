# Dữ liệu cần cung cấp để chạy thí nghiệm PID

Audit ngày 19/10/2026 trên workspace hiện tại kết luận `blocked` vì `real_mini_dataset.csv` chỉ có 2.381 feature và `label`; không có SHA-256/ID của PE, archive nguồn, PE binary hay report sandbox theo mẫu. `data/dynamic_logs/raw_pid_trace.csv` được sinh từ demo mô phỏng và không được dùng làm evidence.

## Chọn một trong hai đầu vào nguồn

### Phương án A — Khôi phục dataset hiện tại

Cung cấp:

- Archive gốc đã tạo `real_mini_dataset.csv`, ưu tiên `test-features.npz`.
- Metadata/index đi kèm có `sha256`, label và source row index.
- Các PE được phép phân tích hoặc một sandbox corpus đã chạy đúng các SHA-256 đó.
- Định nghĩa rõ label 1 là generic malware hay ransomware; nguồn xác nhận ransomware/family.

Script sampling dùng `random_state=42`, nhưng CSV cuối đã shuffle và không lưu source index. Chỉ archive feature/label chưa chắc đủ để lấy SHA-256; cần metadata cùng thứ tự hoặc mapping tương ứng.

### Phương án B — Tạo paired dataset mới

Cung cấp một manifest:

```text
sample_sha256,source,collection_date,label,label_source,family,binary_path_or_archive_id
```

Từ các PE này, pipeline sẽ trích lại EMBER feature và thu dynamic report để static/dynamic cùng chỉ một mẫu.

## Dynamic report bắt buộc

Mỗi PE execution cần event có timestamp và ít nhất hai observation window. Template mặc định dùng 5, 15, 30 và 60 giây. Report cần chứa hoặc cho phép suy ra:

- process tree;
- file open/write/rename/delete;
- số file bị tác động và entropy/tốc độ thay đổi;
- registry/API/system-call events nếu collector hỗ trợ;
- network events nếu collector hỗ trợ;
- sandbox start/end, timeout và termination reason;
- SHA-256 của PE và SHA-256 của report.

Không cần đưa PE vào Git. Có thể đặt binary trong kho lưu trữ riêng và chỉ cung cấp manifest/path mà môi trường thực nghiệm được phép đọc. Không gửi credential hoặc khóa truy cập trong manifest.

## Điều kiện chạy

1. `row_id` hoặc sample trong static feature phải ghép đúng `sample_sha256` của report.
2. Dynamic scorer được train trên training samples hoặc là model ngoài đã đóng băng.
3. Validation/test label không tham gia tạo `p_dynamic`.
4. Controller reset theo mỗi `execution_id`.
5. Gain, threshold và policy missing evidence được chọn trên validation rồi khóa trước test.
6. Báo cáo full-traffic, gồm mẫu quyết định sớm, mẫu routed và sandbox failure.
