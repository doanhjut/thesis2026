# Hướng dẫn đầy đủ: những việc tác giả cần chuẩn bị để hoàn thiện PID và bảo vệ luận văn

**Cập nhật:** 20/10/2026  
**Nhánh Git đang sử dụng:** `feat/reproducible-thesis-experiments`  
**Mục tiêu:** hoàn thiện bằng chứng cho đóng góp PID tĩnh--động, sau đó đồng bộ luận văn và slide bảo vệ.

---

## 1. Trạng thái hiện tại và việc còn thiếu

Hai phần sau đã hoàn thành và không cần tác giả chạy lại:

- **XAI-Guided Active Learning:** 5 outer folds × 5 seed, có Random, Uncertainty, `U+H`, `U+V`, XAI đầy đủ; đã báo AULC, ngân sách nhãn, vùng FPR thấp và overhead.
- **Fidelity/độ ổn định TreeSHAP:** 25 mô hình, hai masking baseline, random control, ba mức `k` và kiểm tra stability.

Phần còn thiếu để nói rằng **cả ba đóng góp đều có thực nghiệm** là PID. Bộ EMBER hiện tại có feature tĩnh và SHA-256 nhưng không có executable hoặc behavior trace. Vì vậy, việc tác giả cần làm là cung cấp một **paired corpus**: mỗi mẫu phải có cùng định danh SHA-256 ở dữ liệu tĩnh, nhãn và báo cáo động.

Nếu không thu thập được paired corpus trước hạn bảo vệ, giữ PID ở mức thiết kế, phân tích công thức và giao thức kiểm chứng. Không sử dụng log demo, điểm mô phỏng hoặc số liệu cũ chưa truy vết làm bằng chứng.

---

## 2. Việc cần làm ngay: kiểm tra nguồn dữ liệu đang có

Tác giả đang có các thư mục tương tự:

```text
D:\Code\Luanvan\data\archives\
    test-features.npz
    train-features.npz
    validation-features.npz
    train_small.zip

D:\Code\Luanvan\data\ember2018\
    X_test.dat
    y_test.dat
    test_features.jsonl
    ...
```

Ba tệp `*.npz` và các tệp `X_*.dat/y_*.dat` thông thường chỉ chứa feature/nhãn. Chúng không đủ để chạy sandbox. Cần kiểm tra `train_small.zip` xem bên trong là PE binary, feature hay metadata.

### 2.1. Chỉ kiểm kê archive, chưa giải nén hoặc thực thi

Mở PowerShell trong thư mục repository và chạy:

```powershell
git switch feat/reproducible-thesis-experiments
git pull

$Archive = "D:\Code\Luanvan\data\archives\train_small.zip"
$Out = "D:\Code\Luanvan\outputs\pid_intake"
New-Item -ItemType Directory -Force -Path $Out | Out-Null

Get-Item $Archive |
  Select-Object FullName, Length, LastWriteTimeUtc |
  Format-List | Out-File "$Out\archive_info.txt" -Encoding utf8

Get-FileHash $Archive -Algorithm SHA256 |
  Format-List | Out-File "$Out\archive_sha256.txt" -Encoding utf8

tar -tf $Archive | Select-Object -First 5000 |
  Out-File "$Out\archive_listing_first5000.txt" -Encoding utf8
```

Nếu `tar` không đọc được ZIP nhưng máy có 7-Zip:

```powershell
& "C:\Program Files\7-Zip\7z.exe" l -slt $Archive |
  Out-File "$Out\archive_listing_7zip.txt" -Encoding utf8
```

Không mở hoặc chạy file `.exe/.dll/.sys/.scr` trên máy làm việc. Bước này chỉ đọc danh sách tệp và hash archive.

### 2.2. Gửi lại trước tiên các tệp nhỏ

Nén và gửi:

```text
outputs\pid_intake\archive_info.txt
outputs\pid_intake\archive_sha256.txt
outputs\pid_intake\archive_listing_first5000.txt
hoặc archive_listing_7zip.txt
```

Không cần gửi `train_small.zip` ở bước đầu. Từ danh sách này có thể xác định archive có binary, metadata hay chỉ có feature.

### 2.3. Quyết định sau kiểm kê

| Kết quả kiểm kê | Hành động tiếp theo |
|---|---|
| Có PE binary và có nhãn/SHA-256 | Tạo manifest rồi thu report động trong sandbox. |
| Có PE binary nhưng không có nhãn tin cậy | Bổ sung nguồn nhãn; chưa dùng cho kết luận ransomware. |
| Chỉ có feature/NPZ/DAT/JSONL | Không thể chạy động; cần paired corpus khác. |
| Chỉ có report sandbox và SHA-256 | Có thể ghép nếu tìm được feature tĩnh của đúng SHA-256. |
| Không có timestamp hoặc chỉ một điểm động | Chỉ so static/dynamic/fixed fusion; chưa tách được I và D của PID. |

---

## 3. Paired corpus cần có những gì

### 3.1. Tệp manifest mẫu

Tạo `sample_manifest.csv` với một hàng cho mỗi PE:

```csv
row_id,sample_sha256,label,label_name,label_source,family,collection_date,source,archive_id
0,0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef,0,benign,Microsoft-signed catalog,,2024-01-15,internal-clean-set,archive_01
1,abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789,1,malware,analyst-confirmed,ExampleFamily,2024-01-16,authorized-malware-set,archive_02
```

Yêu cầu:

- `row_id`: số nguyên liên tiếp từ 0; về sau phải khớp hàng của `static_features.csv`.
- `sample_sha256`: 64 ký tự hex, duy nhất.
- `label`: 0 hoặc 1.
- `label_name`: ghi rõ `benign`, `malware` hoặc định nghĩa đã khóa.
- `label_source`: nguồn xác nhận; không ghi chung chung “Internet”.
- `family`: để trống nếu không có ground truth đáng tin cậy.
- `collection_date`: ngày thu thập nếu có.
- `source/archive_id`: đủ để truy lại mẫu nhưng không chứa credential.

Nếu mục tiêu là tuyên bố **ransomware**, nhãn dương cần nguồn xác nhận ransomware. Nhãn malware chung hoặc `avclass` yếu không đủ để đổi tên thành ransomware ground truth.

### 3.2. Feature tĩnh

Tạo `static_features.csv`:

```text
feature_0,feature_1,...,feature_2380,label
```

Tạo `row_manifest.csv` tối thiểu:

```csv
row_id,label,sha256
0,0,0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
1,1,abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789
```

Ba điều phải đúng tuyệt đối:

1. Hàng `row_id=17` trong manifest phải là hàng thứ 17 theo chỉ số 0 của CSV feature.
2. Nhãn giữa hai tệp phải giống nhau.
3. SHA-256 phải thuộc đúng PE đã dùng để trích feature và chạy sandbox.

Nếu tác giả chỉ cung cấp binary + manifest, phần trích EMBER feature có thể được thực hiện sau; không cần tự tạo CSV bằng cách thủ công.

### 3.3. Split có kiểm soát

Tạo `split_manifest.csv`:

```csv
row_id,split
0,train_pool
1,validation
2,test
```

Mỗi `row_id` xuất hiện đúng một lần và `split` chỉ nhận `train_pool`, `validation`, `test`. Nếu có family/source/time, ưu tiên tách theo nhóm hoặc thời gian để biến thể gần nhau không rơi vào cả train và test.

Không chọn PID gain, fixed weight, calibration hoặc threshold trên test.

---

## 4. Quy mô dữ liệu nên chuẩn bị

| Mức | Quy mô gợi ý | Có thể dùng để làm gì |
|---|---:|---|
| Kiểm tra pipeline | 20--50 mẫu | Kiểm tra schema, hash, parser và sandbox; không dùng làm kết quả luận văn. |
| Pilot | Khoảng 200 mẫu | Phát hiện lỗi thiết kế và ước lượng thời gian chạy. |
| Mức tối thiểu thực tế | 500--1.000 mẫu ghép cặp | So sánh AUC/AP và ablation có kiểm soát, nhưng FPR thấp còn nhiễu. |
| Đánh giá FPR khoảng 1% | Test có ít nhất khoảng 1.000 benign | Một FP tương ứng 0,1 điểm phần trăm; phù hợp hơn để nói về vùng FPR thấp. |

Nếu nguồn lực hạn chế, ưu tiên **định danh đúng, nhãn có nguồn và báo cáo động đầy đủ** hơn số lượng lớn nhưng không truy vết được. Với test chỉ có 300 benign, một FP làm FPR thay đổi 0,333 điểm phần trăm; phải nêu giới hạn này khi bảo vệ.

---

## 5. Thu thập báo cáo động

### 5.1. Môi trường an toàn

Chỉ phân tích mẫu được phép sử dụng trong sandbox/VM cô lập do đơn vị quản lý. Không chạy PE đáng ngờ trên máy cá nhân hoặc máy chứa tài khoản/dữ liệu thật.

Thiết lập tối thiểu:

- snapshot có thể khôi phục;
- mạng host-only hoặc mạng mô phỏng/sinkhole theo chính sách đơn vị;
- không gắn thư mục cá nhân hoặc ổ đĩa dùng chung;
- không lưu credential trong image;
- ghi phiên bản OS, sandbox, collector và cấu hình timeout;
- mỗi execution có ID riêng và report riêng;
- khôi phục trạng thái sạch theo chính sách đã khóa.

### 5.2. Cửa sổ quan sát

Dùng cùng các mốc cho mọi mẫu:

```text
5 giây, 15 giây, 30 giây, 60 giây
```

Ít nhất phải có hai mốc tăng dần để thành phần tích phân và vi phân có ý nghĩa. Không lấy bốn lần chạy độc lập làm bốn time step của một execution. Các time step phải là trạng thái tích lũy của cùng một execution hoặc được tái tạo bằng cách cắt cùng event log theo timestamp.

### 5.3. Nội dung report cần lưu

Mỗi report nên có:

- SHA-256 của mẫu;
- execution ID, thời điểm bắt đầu/kết thúc và termination reason;
- process tree;
- file create/open/write/rename/delete;
- số file và số byte bị tác động;
- thay đổi extension và entropy nếu collector hỗ trợ;
- registry, API/system call nếu có;
- network event nếu có;
- timeout, crash hoặc sandbox failure;
- phiên bản sandbox/collector;
- SHA-256 của chính report.

JSON, JSONL hoặc CSV đều dùng được nếu có timestamp và sample SHA-256. Giữ raw report bất biến; nếu cần chuẩn hóa, tạo tệp mới và lưu hash cả hai.

### 5.4. Phân biệt `no_behavior` và lỗi sandbox

- `observed`: collector hoạt động và thấy hành vi.
- `no_behavior`: collector hoạt động đủ cửa sổ nhưng không thấy tín hiệu đáng kể; vẫn phải có report và điểm động.
- `sandbox_failure`: sandbox/collector lỗi.
- `missing`: chưa thu được report.

Không đổi `sandbox_failure` thành `no_behavior`. Runner cuối hiện chỉ chấp nhận `observed` hoặc `no_behavior`; nếu còn failure/missing cần chạy lại hoặc bổ sung một chính sách missing-evidence được khóa và kiểm thử trước khi đánh giá test.

---

## 6. Tạo điểm động đúng cách

Tác giả có thể gửi raw report để pipeline xây dynamic scorer. Nếu tự tạo `p_dynamic`, phải đáp ứng:

- giá trị hữu hạn trong `[0,1]`;
- được tính chỉ từ event quan sát đến mốc thời gian đang xét;
- không đọc nhãn thật của chính mẫu;
- không tạo bằng `p_static + noise`;
- không dùng demo trace;
- feature/scorer/calibration được fit trên train, lựa chọn trên validation và khóa trước test;
- ghi rõ đây là xác suất đã hiệu chỉnh hay risk score.

Các feature động thực tế có thể gồm số process con, số file ghi/đổi tên/xóa, byte ghi, tốc độ tác động file, số extension mới, event persistence, registry và network counts. Công thức hoặc model biến các feature này thành điểm phải được lưu trong provenance.

---

## 7. Cấu trúc thư mục cần tạo

```text
paired_pid_corpus/
├── sample_manifest.csv
├── static_features.csv
├── row_manifest.csv
├── split_manifest.csv
├── collection_environment.md
├── reports/
│   ├── <sha256_01>/report.json
│   ├── <sha256_02>/report.json
│   └── ...
└── hashes/
    ├── source_archives_sha256.txt
    └── reports_sha256.txt
```

Không đưa binary PE vào Git. Binary có thể nằm trong kho riêng và được tham chiếu bằng `archive_id`. Không ghi mật khẩu, token, API key hoặc đường dẫn chứa credential.

---

## 8. Lệnh chạy sau khi đã có paired corpus

### 8.1. Kiểm tra feature, manifest và split

```powershell
python scripts/run_experiments.py audit-data `
  --data "D:\Code\Luanvan\paired_pid_corpus\static_features.csv" `
  --row-manifest "D:\Code\Luanvan\paired_pid_corpus\row_manifest.csv" `
  --split-file "D:\Code\Luanvan\paired_pid_corpus\split_manifest.csv" `
  --output "outputs\paired_pid_audit"
```

Thư mục output phải là thư mục mới. Nếu đã tồn tại, đặt tên run khác; không xóa run cũ đã khóa.

### 8.2. Chạy AL nền trên paired corpus

```powershell
python scripts/run_experiments.py run `
  --only al `
  --data "D:\Code\Luanvan\paired_pid_corpus\static_features.csv" `
  --row-manifest "D:\Code\Luanvan\paired_pid_corpus\row_manifest.csv" `
  --split-file "D:\Code\Luanvan\paired_pid_corpus\split_manifest.csv" `
  --output "outputs\paired_pid_base" `
  --seeds 11 22 33 44 55 `
  --initial-labels 200 `
  --rounds 5 `
  --batch-size 100 `
  --target-tpr 0.95
```

Điều chỉnh `initial-labels`, `rounds` và `batch-size` nếu train pool nhỏ hơn 700, nhưng phải khóa cùng một cấu hình cho mọi phương pháp.

### 8.3. Sinh template các mốc thời gian

```powershell
python scripts/run_experiments.py prepare-temporal `
  --al-run "outputs\paired_pid_base\al" `
  --output "outputs\paired_pid_temporal" `
  --windows 5 15 30 60
```

Lệnh tạo:

- `dynamic_time_series.csv`;
- `row_mapping.csv`;
- `provenance.json`;
- `README.md`.

### 8.4. Điền `dynamic_time_series.csv`

Schema bắt buộc:

```csv
row_id,execution_id,time_step,elapsed_seconds,p_dynamic,evidence_status,report_path,report_sha256
10,exec_10_001,0,5,0.12,observed,reports/sha10/report.json,<report_sha256>
10,exec_10_001,1,15,0.36,observed,reports/sha10/report.json,<report_sha256>
10,exec_10_001,2,30,0.71,observed,reports/sha10/report.json,<report_sha256>
10,exec_10_001,3,60,0.93,observed,reports/sha10/report.json,<report_sha256>
```

Quy tắc:

- cùng mẫu dùng cùng `execution_id`;
- `time_step` và `elapsed_seconds` tăng nghiêm ngặt;
- mọi mẫu dùng cùng bộ cửa sổ;
- report phải nằm dưới thư mục `outputs\paired_pid_temporal`;
- một report có thể được dùng cho nhiều time step của cùng execution nếu có timestamp đầy đủ;
- không dùng một report cho hai mẫu khác nhau.

### 8.5. Điền `provenance.json`

Các trường phải hoàn chỉnh:

```json
{
  "dataset_sha256": "GIU_NGUYEN_GIA_TRI_DA_TAO",
  "measurements_sha256": "SHA256_CUA_DYNAMIC_TIME_SERIES_CSV",
  "signal_origin": "observed",
  "label_definition": "Mo ta label va nguon xac nhan",
  "dynamic_feature_definition": "Mo ta feature dong o tung cua so",
  "dynamic_score_definition": "Mo ta model/cong thuc tao p_dynamic",
  "dynamic_model_training_source": "Train split hoac model dong bang",
  "calibration_method": "Platt/isotonic/none va ly do",
  "sandbox_or_honeypot": "Ten, version, image va collector",
  "collection_period": "YYYY-MM-DD den YYYY-MM-DD",
  "observation_windows_seconds": [5.0, 15.0, 30.0, 60.0],
  "no_target_label_in_score": true,
  "notes": "Ghi chu them"
}
```

Tính hash measurements bằng PowerShell:

```powershell
(Get-FileHash "outputs\paired_pid_temporal\dynamic_time_series.csv" -Algorithm SHA256).Hash.ToLower()
```

### 8.6. Kiểm tra dữ liệu động

```powershell
python scripts/run_experiments.py validate-temporal `
  --data "outputs\paired_pid_temporal\dynamic_time_series.csv" `
  --provenance "outputs\paired_pid_temporal\provenance.json"
```

Chỉ chuyển sang chạy PID khi kết quả là `valid_schema` và không còn report/hash sai.

### 8.7. Chạy ablation PID

```powershell
python scripts/run_experiments.py temporal-fusion `
  --al-run "outputs\paired_pid_base\al" `
  --temporal-data "outputs\paired_pid_temporal\dynamic_time_series.csv" `
  --provenance "outputs\paired_pid_temporal\provenance.json" `
  --output "outputs\paired_pid_fusion" `
  --target-tpr 0.95 `
  --integral-limits -5 5
```

Runner sẽ so sánh:

- Static-only;
- Dynamic-only;
- Average 50/50;
- Fixed-weight;
- P;
- PI;
- PID.

Fixed weight, PID gain và threshold được chọn trên validation. Test chỉ được đọc sau khi khóa lựa chọn. Đầu ra gồm `fusion_metrics.csv`, `temporal_predictions.csv.gz`, `timepoint_metrics.csv`, `factorial_2x2.csv`, `verification.json`, `summary.json` và hash artifacts.

### 8.8. Lặp theo nhiều outer folds

Lệnh trên chạy một phân hoạch train/validation/test. Để có bằng chứng tương xứng với phần AL/Fidelity, nên chuẩn bị 5 `split_manifest_fold_<n>.csv` và lặp toàn bộ chuỗi `run → prepare-temporal → validate-temporal → temporal-fusion` cho mỗi fold.

Nguyên tắc:

- cùng một mẫu chỉ thuộc một test fold;
- family/source/time group không bị tách nếu đã chọn grouped/temporal split;
- dynamic scorer được fit lại bằng train của fold hoặc là model ngoài đã đóng băng;
- raw report không thay đổi, nhưng `p_dynamic` phải được tạo theo scorer hợp lệ của fold;
- lấy trung bình seed trong từng fold trước khi tính hiệu ứng PID trừ Fixed/PI;
- báo trung bình, SD, min/max và số fold PID thắng;
- không gộp mọi seed thành các bộ dữ liệu độc lập.

Nếu thời gian chỉ cho phép một split, phải gọi kết quả là xác nhận nội bộ và không trình bày độ lệch chuẩn giữa seed như độ bất định giữa các tập dữ liệu.

---

## 9. Những gì cần gửi lại

### Gói 1 — kiểm kê ban đầu

```text
archive_info.txt
archive_sha256.txt
archive_listing_first5000.txt hoặc archive_listing_7zip.txt
```

### Gói 2 — paired corpus đã chuẩn bị

```text
sample_manifest.csv
row_manifest.csv
split_manifest.csv
collection_environment.md
reports_sha256.txt
3--5 report mẫu đại diện đã loại thông tin nhạy cảm
```

Nếu report có dữ liệu nhạy cảm, có thể gửi schema, danh sách trường, hash và một số report đã ẩn danh trước. Không gửi binary, credential hoặc dữ liệu nội bộ bị cấm chia sẻ.

### Gói 3 — sau khi chạy

```text
outputs\paired_pid_audit\
outputs\paired_pid_base\al\config.json
outputs\paired_pid_base\al\summary.json
outputs\paired_pid_temporal\dynamic_time_series.csv
outputs\paired_pid_temporal\provenance.json
outputs\paired_pid_fusion\
```

Có thể bỏ checkpoint/model lớn khi chuyển file, nhưng phải giữ lại trên máy để replay khi cần.

---

## 10. Những việc tuyệt đối không làm

- Không tạo `p_dynamic` từ nhãn thật.
- Không cộng nhiễu vào `p_static` để giả làm tín hiệu động.
- Không sử dụng `raw_pid_trace.csv` từ demo làm bằng chứng.
- Không gán SHA-256 bằng suy đoán theo thứ tự khi mapping không khớp.
- Không gọi nhãn EMBER malware chung là ransomware ground truth.
- Không điều chỉnh gain hoặc threshold sau khi xem test.
- Không xóa hoặc ghi đè run cũ; luôn tạo thư mục output mới.
- Không sửa CSV kết quả để làm số đẹp hơn.
- Không đưa executable đáng ngờ hoặc credential lên Git.
- Không coi thời gian tính phép fusion là latency phát hiện đầu cuối.

---

## 11. Checklist tác giả

### Kiểm kê

- [ ] Pull nhánh `feat/reproducible-thesis-experiments`.
- [ ] Tạo hash và listing của `train_small.zip`.
- [ ] Gửi gói kiểm kê nhỏ để xác định loại dữ liệu.

### Dữ liệu

- [ ] Có manifest SHA-256 và nhãn có nguồn.
- [ ] Xác định nhãn là benign/malware hay ransomware-specific.
- [ ] Feature tĩnh và report động thuộc đúng cùng mẫu.
- [ ] Split không làm rò rỉ family/source/time.

### Sandbox

- [ ] Môi trường được phép, cô lập và có snapshot.
- [ ] Cùng chính sách quan sát cho mọi mẫu.
- [ ] Có timestamp và ít nhất hai cửa sổ; ưu tiên 5/15/30/60 giây.
- [ ] Lưu execution ID, report, report hash và failure status.

### Điểm động

- [ ] Scorer không đọc target label.
- [ ] Train/calibration chỉ dùng train/validation.
- [ ] `p_dynamic` hữu hạn trong `[0,1]`.
- [ ] Provenance mô tả feature, scorer, calibration và collection period.

### Trước khi đưa vào luận văn

- [ ] `validate-temporal` trả `valid_schema`.
- [ ] `verification.json` của run PID báo `passed`.
- [ ] Metric tính lại được từ prediction từng mẫu.
- [ ] Báo cả FP/FN, TPR/FPR và số split/seed thắng.
- [ ] Báo riêng latency tĩnh, thu tín hiệu động, suy luận động, fusion và end-to-end.
- [ ] Nếu PID không hơn Fixed/PI, giữ kết quả và thu hẹp kết luận.

---

## 12. Phân công rõ ràng

### Tác giả cần thực hiện

1. Kiểm kê `train_small.zip` bằng các lệnh ở Mục 2.
2. Xác nhận quyền sử dụng mẫu và nguồn nhãn.
3. Nếu có binary, chuẩn bị manifest và chạy sandbox an toàn; nếu đã có report, cung cấp mapping SHA-256.
4. Gửi các gói nhỏ được liệt kê ở Mục 9.
5. Duyệt lại cách gọi nhãn trong luận văn với thầy hướng dẫn.

### Phần pipeline có thể thực hiện sau khi nhận dữ liệu

1. Kiểm tra hash, mapping, nhãn, duplicate và split leakage.
2. Trích feature tĩnh hoặc kiểm tra feature hiện có.
3. Xây/khóa dynamic scorer và calibration mà không đọc test label.
4. Sinh template thời gian và kiểm tra report.
5. Chạy Static/Dynamic/Average/Fixed/P/PI/PID.
6. Sinh bảng, biểu đồ, ablation, overhead và verification.
7. Cập nhật Chương 4, tóm tắt, kết luận và slide bảo vệ.

---

## 13. Phương án khi không kịp dữ liệu động

Nếu không có paired corpus đúng hạn:

- giữ nguyên kết quả AL và Fidelity đã xác nhận;
- trình bày PID là đóng góp thiết kế có phân tích toán học và giao thức kiểm chứng;
- bỏ mọi số PID không truy được về prediction thật;
- nói rõ EMBER chỉ xác nhận malware tĩnh;
- không tuyên bố PID đã giảm FPR hoặc hệ thống đã sẵn sàng vận hành;
- tập trung bảo vệ giá trị của AULC, tiết kiệm nhãn, low-FPR evaluation và deletion/stability.

Phương án này yếu hơn về số lượng đóng góp đã kiểm chứng nhưng vẫn nhất quán về học thuật và tránh một điểm phản biện có thể làm mất độ tin cậy của toàn bộ luận văn.
