# VirusTotal behaviour pilot: 20 reports with timestamps

Mục tiêu của pilot là kiểm tra xem behavior report của VirusTotal có chứa
timeline/timestamp đủ để xây dựng thành phần vi phân `D` theo thời gian thực hay
không. Workflow chỉ truy vấn behavior metadata và tải HTML report. Workflow
không gọi endpoint tải PE hoặc executable.

## 1. Tạo GitHub Actions secret

Trong repository `doanhjut/thesis2026`:

1. Mở **Settings**.
2. Chọn **Secrets and variables** → **Actions**.
3. Chọn **New repository secret**.
4. Đặt tên `VT_API_KEY` và nhập VirusTotal API key.

Không ghi API key vào file, commit, workflow input hoặc Actions log.

## 2. Chạy pilot

1. Mở tab **Actions**.
2. Chọn **VirusTotal behaviour pilot (report only)**.
3. Chọn **Run workflow** trên branch chứa workflow.

Workflow chọn cố định 20 mẫu: hai mẫu cho mỗi cặp `outer_fold × label`, giới
hạn bốn VirusTotal request mỗi phút và dừng khi gặp HTTP 429.

## 3. Lấy artifact

Khi job kết thúc, mở job summary và tải artifact:

```text
vt-behaviour-pilot20
```

Artifact có:

```text
coverage_audit.json
coverage_by_sample.csv
pilot_manifest.csv
request_history.csv
raw_listings/*.json.gz
raw_html_reports/*.html.gz
```

## 4. Điều kiện tiếp tục thu toàn cohort

Chỉ triển khai thu toàn cohort nếu raw report thực sự chứa timestamp gắn với
event/API call. Các cờ `contains_timestamp_token` và `contains_api_token` chỉ
dùng để sàng lọc schema; chúng không tự chứng minh report có timeline sử dụng
được. Sau pilot cần parse ít nhất một report và xác minh:

- timestamp tăng theo cùng một execution;
- event có API/category/process tương ứng;
- có đủ ít nhất ba cửa sổ thời gian;
- SHA-256 của report khớp manifest;
- timestamp không được suy diễn từ `event_index`.

Nếu report chỉ chứa behavior summary, dữ liệu đó có thể dùng cho dynamic score
tổng hợp nhưng không đủ để tuyên bố đã kiểm chứng thành phần `D` theo wall-clock
time.
