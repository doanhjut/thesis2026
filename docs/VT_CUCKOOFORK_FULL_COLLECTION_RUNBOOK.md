# Thu Cuckoofork timestamp toàn cohort

Workflow `Daily VirusTotal Cuckoofork collection` thu behavior listing và HTML
report theo SHA-256 đã khóa. Workflow không tải hoặc thực thi PE.

## Điều kiện kích hoạt lịch chạy

GitHub chỉ chạy `schedule` cho workflow tồn tại trên default branch. Vì vậy cần
merge workflow và collector vào `main`. Dữ liệu trạng thái vẫn được commit vào
branch `feat/reproducible-thesis-experiments`.

## Chính sách thu thập

- 4 VirusTotal request/phút;
- tối đa 350 API request mỗi lần chạy;
- cron `00:30 UTC` mỗi ngày (`07:30` giờ Việt Nam/Thái Lan);
- chọn mẫu pending theo round-robin trên `outer_fold × label`;
- dừng sạch khi gặp HTTP 429, 401 hoặc 403;
- `no_cuckoofork`, `report_collected` và `not_found` là trạng thái terminal;
- raw listing/report nằm trong GitHub Actions artifact 30 ngày;
- Git chỉ lưu state, request history, summary và hash.

## Ước lượng

Với coverage Cuckoofork pilot khoảng 45%, toàn cohort cần xấp xỉ 2.800 API
request (listing cộng report). Ở ngân sách 350 request/ngày, thời gian dự kiến
khoảng 8 ngày nếu quota ổn định. Đây chỉ là ước lượng; workflow báo số thực sau
mỗi batch.

## Điều kiện chạy PID sau thu thập

Không chạy confirmatory PID chỉ vì collection hoàn tất. Trước tiên cần tổng hợp
artifact, parse timestamp, audit coverage theo fold/label, thời lượng execution
và số timestamp phân biệt. Chỉ dùng execution qua các điều kiện parser đã khóa.
