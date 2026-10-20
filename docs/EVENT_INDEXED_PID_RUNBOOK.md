# Giao thức PID theo tiến trình sự kiện, không cần giữ executable

## Phạm vi

Giao thức này dùng MalBehavD-V1, một bộ CSV công khai gồm SHA-256, nhãn nhị
phân và chuỗi API call do Cuckoo Sandbox thu thập. Không có PE executable nào
được tải hoặc thực thi. Metadata tĩnh được truy vấn theo cùng SHA-256 qua
VirusTotal API và chỉ các thuộc tính cấu trúc PE trong allow-list mới đi vào
mô hình.

Kết quả trả lời câu hỏi về dung hợp tĩnh--động cho **generic Windows malware**.
Trục quan sát là số API call đã thấy, không phải số giây. Vì vậy, luận văn phải
gọi cấu hình này là `event-indexed PID` và không suy ra độ trễ sandbox hay tuyên
bố riêng cho ransomware.

Nguồn dữ liệu: <https://github.com/mpasco/MalbehavD-V1>. Khi sử dụng cần trích
dẫn Maniriho et al., “API-MalDetect”, *Journal of Network and Computer
Applications*, 2023.

Snapshot đang dùng là commit `6aac5027635ac3d2832d323a873fccd7cdd89a5e`; file
CSV phải có SHA-256
`1e39c43a014e9b4ee56766ad6bb367ffe8ec4316eb0be75eb182c3b2d15f6364`.

## 1. Chuẩn bị secret

Thêm `VT_API_KEY` vào Network secrets của môi trường và cho phép domain
`www.virustotal.com`. Không ghi key vào tệp, lệnh shell, log hoặc Git.

## 2. Khóa cohort trước khi lấy metadata

```bash
git clone https://github.com/mpasco/MalbehavD-V1.git /tmp/MalbehavD-V1
git -C /tmp/MalbehavD-V1 checkout 6aac5027635ac3d2832d323a873fccd7cdd89a5e
```

```bash
.venv/bin/python scripts/run_experiments.py prepare-malbehavd \
  --source /tmp/MalbehavD-V1/MalBehavD-V1-dataset.csv \
  --output outputs/malbehavd_pid_prepared \
  --min-events 20 --folds 5 --seed 2026
```

Lệnh kiểm tra SHA-256, nhãn, xung đột, chọn trace dài nhất cho SHA trùng, giữ
các mẫu có ít nhất 20 API call và khóa năm outer folds phân tầng. Split không
được thay đổi sau khi xem kết quả.

## 3. Pilot metadata

```bash
.venv/bin/python scripts/run_experiments.py collect-vt-static \
  --cohort outputs/malbehavd_pid_prepared/cohort_manifest.csv \
  --output outputs/malbehavd_pid_vt \
  --limit 200 --seed 2026 --requests-per-minute 4
```

Collector chỉ gọi `GET /api/v3/files/{sha256}`. Nó không gọi endpoint download.
Raw response được giữ để audit, nhưng bộ trích feature chỉ có thể đọc `size`,
`type_tag` và `pe_info`. AV verdict, detection count, threat name, tag và filename
đều bị loại. Cache theo SHA-256 cho phép chạy tiếp sau khi hết quota.

Quy tắc quyết định đã khóa:

- coverage từ 90%: tiếp tục confirmatory;
- 80--90%: phân tích missingness theo nhãn/fold trước;
- dưới 80%: không dùng làm bằng chứng PID chính.

## 4. Thu metadata cho toàn cohort

Bỏ `--limit` và dùng lại đúng thư mục output của pilot để tái sử dụng cache.
Không tăng tốc độ cao hơn quota của tài khoản.

```bash
.venv/bin/python scripts/run_experiments.py collect-vt-static \
  --cohort outputs/malbehavd_pid_prepared/cohort_manifest.csv \
  --output outputs/malbehavd_pid_vt \
  --seed 2026 --requests-per-minute 4 --max-new 500
```

Nếu tài khoản có quota 500 request/ngày, chạy lại đúng lệnh này vào ngày tiếp
theo. Các SHA đã có cache không tiêu tốn request mới; `--max-new` giới hạn phần
chưa cache trong mỗi lần gọi. Không dùng nhiều key để né quota.

## 5. Chạy ablation

```bash
.venv/bin/python scripts/run_experiments.py event-pid \
  --sequences outputs/malbehavd_pid_prepared/api_sequences.csv.gz \
  --static-features outputs/malbehavd_pid_vt/static_features.csv.gz \
  --output outputs/malbehavd_pid_confirmatory \
  --windows 5 10 15 20 \
  --target-tpr 0.95 --min-coverage 0.80 \
  --bootstrap 1000 --seed 2026
```

Trong mỗi outer fold, base training, calibration và fusion validation là ba
phân vùng rời nhau. Gain PID, fixed weight và threshold chỉ được chọn trên
fusion validation. Outer test không tham gia lựa chọn. Các đối chứng gồm
Static, Dynamic, Average 50/50, Fixed, P, PI và PID.

## 6. Điều kiện đưa vào luận văn

- `verification.json` có `status=passed`;
- coverage đạt ngưỡng đã khóa và missingness không lệch nghiêm trọng theo nhãn;
- metric tính lại được từ `event_predictions.csv.gz`;
- báo cả FP/TN/FN/TP, confidence interval và biến thiên giữa folds;
- kết luận theo kết quả đo, kể cả khi PID không hơn Fixed hoặc PI;
- ghi rõ source bias: benign và malware của bộ gốc đến từ hai nguồn thu thập;
- không dùng kết quả để tuyên bố latency theo giây, ransomware-specific hoặc
  production readiness.

Các tệp chính gồm `fusion_metrics.csv`, `event_predictions.csv.gz`,
`validation_search.json`, `paired_bootstrap_pid_minus_fixed.json`,
`summary.json`, `verification.json` và `artifact_sha256.json`.
