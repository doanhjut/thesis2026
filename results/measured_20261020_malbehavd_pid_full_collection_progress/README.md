# Tiến độ thu metadata cho confirmatory PID

Snapshot này ghi trạng thái thu thập toàn cohort MalBehavD-V1 đã khóa. Đây là
bằng chứng tiến độ, chưa phải kết quả mô hình.

## Trạng thái hiện tại

- Cohort: 1.923 SHA-256; 932 benign và 991 malware.
- Metadata tĩnh usable: 993 mẫu; coverage 51,64%.
- Còn 929 mẫu được đánh dấu `deferred_rate_limit`. Đây là mẫu chưa gọi API, không
  phải mẫu thiếu trên VirusTotal.
- Ngưỡng confirmatory đã khóa: coverage tối thiểu 90%, tương ứng 1.731 mẫu
  usable. Snapshot hiện cần thêm tối thiểu 738 mẫu usable.
- Audit history ghi 769 request `fetched` thành công, 23 lỗi mạng
  `Operation not permitted` ở phiên bị chặn quyền và bốn HTTP 429. Các lỗi mạng
  không được coi là mẫu thiếu; collector tiếp tục từ cache sau khi mạng được cấp.
- Phiên ngày 21/10 thu thêm 273 mẫu rồi dừng ngay tại HTTP 429 lúc
  14:47:49 UTC (21:47:49 giờ Việt Nam).
- Lần thử resume ngày 22/10 gửi đúng một yêu cầu metadata và tiếp tục nhận HTTP
  429 lúc 23:38:43 UTC ngày 21/10 (06:38:43 giờ Việt Nam ngày 22/10); collector
  dừng ngay và không làm thay đổi coverage.
- Không tải hoặc thực thi executable. Raw VirusTotal response chỉ nằm trong
  `outputs/` bị Git bỏ qua.

Coverage hiện tại theo lớp là 50,00% benign và 53,18% malware. Mức chênh này
phản ánh snapshot thu dở theo thứ tự manifest; không được dùng để phân tích
missingness hoặc huấn luyện confirmatory. `coverage_by_fold_label.csv` cho thấy
cả 10 ô fold×class đã có dữ liệu, nhưng chưa cân bằng đủ để đánh giá cuối.

## Quyết định thực nghiệm

Không chạy confirmatory trên 993 mẫu. Tiếp tục dùng đúng cohort, cache và outer
fold hiện tại cho đến khi hết trạng thái `deferred_rate_limit`. Sau đó:

1. Chạy `audit-vt-collection` với ngưỡng 0,90.
2. Nếu coverage đạt ít nhất 90%, kiểm tra missingness thực theo nhãn/fold.
3. Chạy `event-pid` đúng một lần trên cohort usable cuối cùng.
4. Báo Static, Dynamic, Average, Fixed, P, PI, PID; bootstrap ghép cặp và hiệu
   ứng riêng của P/I/D, kể cả khi PID không vượt PI.

## Lệnh resume

```bash
.venv/bin/python scripts/run_experiments.py collect-vt-static \
  --cohort outputs/malbehavd_pid_20261020_prepared/cohort_manifest.csv \
  --output outputs/malbehavd_pid_20261020_vt_full \
  --seed 2026 --requests-per-minute 4 --max-new 100
```

Chỉ chạy lại lệnh sau khi quota được reset. Collector bỏ qua cache, dừng gửi
request mới khi gặp HTTP 429 và ghi từng lần gọi mạng vào `request_history.csv`.

Kiểm tra không gọi mạng:

```bash
.venv/bin/python scripts/run_experiments.py audit-vt-collection \
  --cohort outputs/malbehavd_pid_20261020_prepared/cohort_manifest.csv \
  --collection outputs/malbehavd_pid_20261020_vt_full \
  --min-coverage 0.90
```

Exit code `3` là trạng thái dự kiến khi collection còn dở. Code audit tương ứng
commit `62e8a657454b5257a9e6a57308e4ed988d8068c3`.
