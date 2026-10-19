# Runbook hoàn thiện ba đóng góp

Tài liệu này mô tả đầu vào thật, lệnh chạy và điều kiện hoàn tất. Không dùng
artifact legacy trong `data/dynamic_logs/` làm bằng chứng.

## 1. Gói dữ liệu static cần có

Hai tệp đã được tạo trên máy Windows:

- `outputs/ember_identity_dataset/ember_mini_dataset.csv`
- `outputs/ember_identity_dataset/ember_row_manifest.csv`

Manifest phải có `row_id,label,sha256`; pipeline kiểm tra lại nhãn, SHA-256 duy
nhất và feature hash nếu cột `source_feature_float32_sha256` có mặt. Không commit
CSV này lên Git.

## 2. XAI-Guided Active Learning confirmatory

Chạy từ repository root trên PowerShell:

```powershell
python scripts/run_experiments.py confirmatory-al `
  --data outputs\ember_identity_dataset\ember_mini_dataset.csv `
  --row-manifest outputs\ember_identity_dataset\ember_row_manifest.csv `
  --output outputs\ember_confirmatory_al `
  --folds 5 `
  --seeds 11 22 33 44 55 `
  --initial-labels 200 `
  --rounds 10 `
  --batch-size 100 `
  --target-excess-auc-fraction 0.95
```

Mỗi outer fold dùng test fold riêng. Validation được tách trong phần develop.
Full-pool model của từng fold xác định trước target:

```text
target = 0.5 + 0.95 * (full_pool_validation_auc - 0.5)
```

Kết quả chính:

- `method_summary.csv`: AUC/AP/FPR/TPR và partial AUC.
- `aulc_summary.csv`: hiệu quả dọc theo ngân sách nhãn.
- `target_reach_summary.csv`: số lần và số nhãn đạt target.
- `paired_xai_differences.csv`: hiệu số XAI_full theo đúng fold/seed.
- `verification.json`: replay toàn bộ checkpoint.

## 3. Fidelity confirmatory

Dùng đúng outer folds của AL:

```powershell
python scripts/run_experiments.py confirmatory-fidelity `
  --data outputs\ember_identity_dataset\ember_mini_dataset.csv `
  --row-manifest outputs\ember_identity_dataset\ember_row_manifest.csv `
  --split-dir outputs\ember_confirmatory_al\fold_manifests `
  --output outputs\ember_confirmatory_fidelity `
  --seeds 41 42 43 44 45 `
  --baselines mean median `
  --k 10 25 50 `
  --random-masks 20 `
  --bootstrap 500
```

LightGBM dùng row/feature subsampling có seed để tạo các model khác nhau nhưng
tái lập được. Deletion test dùng cả training mean và median; random masks có cùng
k với top-|SHAP|. `deletion_summary.csv` là bằng chứng faithfulness và
`shap_rank_stability.csv` là bằng chứng consistency. Không tổng hợp OFS.

## 4. Gói dữ liệu thật cần cho PID

EMBER static không chứa executable hay behavior trace. PID cần một paired corpus
riêng. Khoảng 200 PE chỉ phù hợp smoke/pilot; nên có ít nhất 500 PE để phần
validation và test còn đủ mẫu sau khi chia dữ liệu.
Mỗi PE cần:

- Tệp PE được phép phân tích và SHA-256.
- Nhãn độc lập với dynamic scorer.
- Vector static trích từ chính PE đó.
- Một sandbox execution ID.
- Báo cáo sự kiện đến các mốc 5, 15, 30 và 60 giây.
- `p_dynamic` do một scorer đóng băng tạo ra mà không đọc target label.
- Đường dẫn và SHA-256 của report.
- Thời gian thu thập, sandbox/tool version và chính sách timeout.

Không dùng điểm tạo từ label, `p_static`, RNG hoặc log demo. Không đưa PE độc hại
vào Git; chỉ lưu report đã xử lý và hash theo chính sách của đơn vị.

Sau khi chạy AL trên paired corpus, tạo template:

```powershell
python scripts/run_experiments.py prepare-temporal `
  --al-run outputs\paired_pid_al\al `
  --output outputs\paired_pid_temporal `
  --windows 5 15 30 60
```

Điền `dynamic_time_series.csv`, lưu report dưới cùng thư mục, cập nhật
`provenance.json` và `measurements_sha256`, rồi kiểm tra:

```powershell
python scripts/run_experiments.py validate-temporal `
  --data outputs\paired_pid_temporal\dynamic_time_series.csv `
  --provenance outputs\paired_pid_temporal\provenance.json
```

Chạy ablation cuối:

```powershell
python scripts/run_experiments.py temporal-fusion `
  --al-run outputs\paired_pid_al\al `
  --temporal-data outputs\paired_pid_temporal\dynamic_time_series.csv `
  --provenance outputs\paired_pid_temporal\provenance.json `
  --output outputs\paired_pid_fusion `
  --target-tpr 0.95 `
  --integral-limits -5 5
```

Runner dùng thời gian thật:

```text
I[k] = clip(I[k-1] + e[k] * delta_t[k], I_min, I_max)
D[k] = (e[k] - e[k-1]) / delta_t[k], D[0] = 0
u[k] = Kp*e[k] + Ki*I[k] + Kd*D[k]
```

Gain, fixed weight và threshold được chọn trên validation. Test chỉ được đánh giá
sau khi khóa lựa chọn. `factorial_2x2.csv` tách hiệu ứng
`Random/XAI_full × Fixed/PID`.

## 5. Tệp cần gửi lại để đưa vào luận văn

Nén và gửi ba thư mục output sau; không cần gửi checkpoint nếu dung lượng quá lớn:

1. `ember_confirmatory_al`: config, summary, các CSV tổng hợp, verification và
   artifact hash; giữ checkpoint tại máy để có thể replay.
2. `ember_confirmatory_fidelity`: config, summary, deletion/stability CSV,
   verification và artifact hash.
3. `paired_pid_fusion`: config, summary, fusion/timepoint/factorial CSV,
   verification và artifact hash; kèm provenance/report hash của dynamic corpus.

Không đưa số vào luận văn trước khi `verification.json` báo `passed` và
`artifact_sha256.json` đã được tạo cho đúng run.
