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

### Lệnh khôi phục trên máy Windows

Sau khi pull nhánh `feat/reproducible-thesis-experiments`, chạy kiểm tra header của nguồn nhiều khả năng đã được chọn. Lệnh này không nạp ma trận feature vào RAM và mặc định chưa hash toàn bộ file 39 GB:

```powershell
python scripts/run_experiments.py inspect-source `
  --source "D:\Code\Luanvan\data\archives\test-features.npz" `
  --output outputs\source_inspection_test
```

Gửi lại file nhỏ `outputs\source_inspection_test\source_inspection.json`. Nếu shape và class counts phù hợp, khôi phục mapping và thử ghép JSONL:

```powershell
python scripts/run_experiments.py recover-manifest `
  --source "D:\Code\Luanvan\data\archives\test-features.npz" `
  --mini "D:\Code\Luanvan\data\processed\real_mini_dataset.csv" `
  --metadata-jsonl "D:\Code\Luanvan\data\ember2018\test_features.jsonl" `
  --output outputs\recovered_manifest_test
```

Runner tái tạo sampling và shuffle cũ, stream đúng 2.000 source rows, rồi so từng vector/label với CSV hiện tại. JSONL chỉ được ghép khi đủ dòng, SHA-256 hợp lệ và label cùng thứ tự; mismatch sẽ dừng thay vì tạo manifest sai.

Lần đóng băng cuối nên thêm `--hash-source`. Hash file hàng chục GB sẽ mất nhiều thời gian nên chưa cần dùng ở bước inspect đầu tiên.

### Ánh xạ SOREL source index sang SHA-256 và tag

Khi `recover-manifest` đã đạt, không dùng `ember2018/test_features.jsonl`: JSONL
đó thuộc EMBER 2018 và không cùng thứ tự mẫu với SOREL. NPZ LightGBM chính thức
chỉ chứa feature và nhãn malware nhị phân. Cần hai artifact đúng bản SOREL:

- `processed-data/meta.db` (khoảng 3,5 GB), chứa SHA-256, timestamp, nhãn và tag;
- `shas_missing_ember_features.json` từ repository SOREL-20M chính thức.

Chạy:

```powershell
python scripts/run_experiments.py recover-sorel-metadata `
  --manifest "outputs\recovered_manifest_sorel_test\row_manifest.csv" `
  --source-inspection "outputs\recovered_manifest_sorel_test\source_inspection.json" `
  --meta-db "D:\Code\Luanvan\data\sorel20m\meta.db" `
  --missing-shas "D:\Code\Luanvan\data\sorel20m\shas_missing_ember_features.json" `
  --output "outputs\recovered_sorel_metadata"
```

Công cụ phát lại truy vấn test và bộ lọc missing-feature của mã SOREL chính thức,
kiểm tra tổng số dòng sau lọc bằng số dòng NPZ, rồi kiểm tra nhãn tại đủ 2.000
source index trước khi xuất `sorel_row_manifest.csv`. `tag_ransomware` là weak
multi-label tag của SOREL, không được mô tả như family ground truth. Lần đóng
băng cuối có thể thêm `--hash-meta-db`.

Nếu metadata dùng điều kiện biên `rl_fs_t >= 1547279640` nhiều hơn NPZ đúng bằng
số mẫu nằm tại timestamp biên, runner thử chính sách `>` trong cùng một lượt đọc.
Nó chỉ chấp nhận chính sách này khi tổng số dòng khớp NPZ và nhãn khớp tại cả
2.000 source index; quyết định được lưu trong `sorel_alignment_audit.json` và
`selected_split_policy` của báo cáo. Không được tự trừ số dòng hoặc bỏ qua lỗi.

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
