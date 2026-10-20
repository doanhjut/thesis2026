# Tiến độ thu metadata cho confirmatory PID

Snapshot này ghi trạng thái thu thập toàn cohort MalBehavD-V1 đã khóa. Đây là
bằng chứng tiến độ, chưa phải kết quả mô hình.

## Trạng thái hiện tại

- Cohort: 1.923 SHA-256; 932 benign và 991 malware.
- Metadata tĩnh usable: 424 mẫu; coverage 22,05%.
- Còn 1.499 mẫu được đánh dấu `deferred_quota`. Đây là mẫu chưa gọi API, không
  phải mẫu thiếu trên VirusTotal.
- Ngưỡng confirmatory đã khóa: coverage tối thiểu 90%, tương ứng 1.731 mẫu
  usable. Snapshot hiện cần thêm tối thiểu 1.307 mẫu usable.
- 200 request có audit history của hai lô gần nhất đều `fetched`; không có 404,
  429 hay lỗi mạng. Ngoài ra có 199 cache usable từ pilot và 25 mẫu của lô kiểm
  tra trước khi tính năng history được thêm vào.
- Không tải hoặc thực thi executable. Raw VirusTotal response chỉ nằm trong
  `outputs/` bị Git bỏ qua.

Coverage hiện tại theo lớp là 19,53% benign và 24,42% malware. Mức chênh này
phản ánh snapshot thu dở theo thứ tự manifest; không được dùng để phân tích
missingness hoặc huấn luyện confirmatory. `coverage_by_fold_label.csv` cho thấy
cả 10 ô fold×class đã có dữ liệu, nhưng chưa cân bằng đủ để đánh giá cuối.

## Quyết định thực nghiệm

Không chạy confirmatory trên 424 mẫu. Tiếp tục dùng đúng cohort, cache và outer
fold hiện tại cho đến khi hết `deferred_quota`. Sau đó:

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

Collector bỏ qua cache, dừng gửi request mới khi gặp HTTP 429 và ghi từng lần
gọi mạng vào `request_history.csv`.

Kiểm tra không gọi mạng:

```bash
.venv/bin/python scripts/run_experiments.py audit-vt-collection \
  --cohort outputs/malbehavd_pid_20261020_prepared/cohort_manifest.csv \
  --collection outputs/malbehavd_pid_20261020_vt_full \
  --min-coverage 0.90
```

Exit code `3` là trạng thái dự kiến khi collection còn dở. Code audit tương ứng
commit `a93d4181b6feff9370d3b2420dfdc856e55f7267`.
