# MalBehavD-V1 / VirusTotal PID intake — 20/10/2026

Đây là bằng chứng **intake và schema pilot**, chưa phải kết quả hiệu quả PID.
Không có PE executable nào được tải hoặc thực thi.

## Kết quả đã đo

- Nguồn MalBehavD-V1: 2.570 hàng, 1.285 benign và 1.285 malware.
- Sau loại SHA trùng: 2.543 SHA duy nhất. Có 26 SHA xuất hiện lặp, tương ứng
  27 hàng dư; không có xung đột nhãn.
- Sau yêu cầu tối thiểu 20 API call: 1.923 mẫu, gồm 932 benign và 991 malware.
- Năm outer folds đã được khóa trước khi lấy metadata; mỗi fold có 384--385 mẫu.
- SHA-256 của CSV nguồn khớp snapshot đã khai báo.
- Pilot VirusTotal cân bằng 20 mẫu: 19 metadata hợp lệ và một `404`, coverage 95%.
- 19 mẫu hợp lệ gồm 10 benign và 9 malware.
- Bộ trích allow-list tạo 199 feature cấu trúc PE.

Collector chỉ gọi `GET /api/v3/files/{sha256}` và không gọi endpoint tải file.
Feature chỉ đọc `sha256`, `size`, `type_tag` và `pe_info`; AV verdict, detection
count, threat name, sandbox verdict, tag và filename bị loại rõ ràng.

## Ý nghĩa

Coverage pilot vượt ngưỡng tiếp tục 90%, nên có thể mở rộng thu metadata. Pilot
20 mẫu chỉ xác nhận định danh, schema, quota, missingness và cơ chế chống label
leakage. Không dùng các con số này để nói PID tăng AUC hoặc giảm FPR.

## Phần còn lại

Thu metadata cho cohort bằng cache, giới hạn 4 request/phút và quota tài khoản.
Sau khi coverage cuối được đo và kiểm tra theo nhãn/fold, chạy 5-fold ablation
Static, Dynamic, Average, Fixed, P, PI và PID theo các mốc 5/10/15/20 API call.
Giao thức và lệnh nằm tại
[`docs/EVENT_INDEXED_PID_RUNBOOK.md`](../../docs/EVENT_INDEXED_PID_RUNBOOK.md).

Phạm vi kết luận là generic Windows malware benchmark với trục số sự kiện. Dữ
liệu này không hỗ trợ kết luận ransomware-specific hoặc latency theo giây.
