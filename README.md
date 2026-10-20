# Phát hiện ransomware bằng XAI và Active Learning

Kho mã nguồn luận văn dùng LightGBM trên vector đặc trưng EMBER, Active Learning có hướng dẫn bởi TreeSHAP và cơ chế dung hợp điểm tĩnh–động. Pipeline thực nghiệm dùng cho báo cáo nằm trong `src/experiments/`; mọi bảng và biểu đồ của một lần chạy được sinh từ dự đoán từng mẫu đã lưu, không chứa kết quả gán sẵn hay nhánh mô phỏng dự phòng.

## Phạm vi đã kiểm chứng

Ba câu hỏi được tách thành ba thí nghiệm độc lập:

1. **XAI-Guided Active Learning:** so sánh `Random`, `Uncertainty`, `U+H`, `U+V` và `XAI_full` với cùng tập khởi tạo, ngân sách nhãn, validation và test. Mỗi vòng huấn luyện model mới; test không tham gia chọn mẫu, ngưỡng hay tham số.
2. **Fidelity:** tính TreeSHAP gốc của LightGBM, kiểm tra tính cộng, rồi so sánh việc che top-k đặc trưng với nhiều mask ngẫu nhiên cùng kích thước. FF, EC và CF được báo cáo riêng; pipeline không tự tổng hợp OFS vì chưa có quy tắc chuẩn hóa và trọng số được kiểm định cho dữ liệu PE.
3. **PID Fusion:** chỉ chạy khi có điểm động quan sát thật, báo cáo theo từng mẫu và metadata nguồn. Runner từ chối trace demo, dữ liệu khai là mô phỏng, thiếu báo cáo hoặc hash không khớp. So sánh static, dynamic, trung bình, trọng số cố định, P, PI và PID; kèm bảng nhân tố 2×2 giữa `Random/XAI_full` và `Fixed/PID`.

CSV hiện có trong Git cho phép chạy pilot nội bộ theo dòng dữ liệu. Nguồn tệp PE gốc, quan hệ họ malware, thời điểm thu thập và ý nghĩa ransomware cụ thể của nhãn chưa được xác minh trong kho. Vì vậy kết quả này chưa phải bằng chứng family-held-out, temporal/zero-day hoặc benchmark ransomware độc lập.

## Cài đặt

Chạy từ thư mục gốc:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Trên PowerShell, kích hoạt bằng `\.venv\Scripts\Activate.ps1`.

## Chạy và kiểm tra lại

Audit dữ liệu mà không huấn luyện:

```bash
python scripts/run_experiments.py audit-data \
  --data data/processed/real_mini_dataset.csv
```

Chạy cấu hình mặc định gồm AL và Fidelity. Thư mục output phải chưa tồn tại:

```bash
python scripts/run_experiments.py run \
  --data data/processed/real_mini_dataset.csv \
  --output outputs/thesis_run
```

Khi dataset có manifest SHA-256 theo hàng, truyền manifest để runner xác minh
định danh, nhãn và feature hash trước khi huấn luyện:

```bash
python scripts/run_experiments.py run \
  --data outputs/ember_identity_dataset/ember_mini_dataset.csv \
  --row-manifest outputs/ember_identity_dataset/ember_row_manifest.csv \
  --output outputs/ember_measured_run
```

Đầu ra gồm config, split cố định, model/checkpoint, dự đoán từng mẫu, truy vấn AL, mask Fidelity, bảng CSV/LaTeX, biểu đồ PDF/PNG, báo cáo Markdown và SHA-256 của artifact. Đường replay riêng nạp lại model và tái tính dự đoán/chỉ số:

```bash
python scripts/run_experiments.py verify --run outputs/thesis_run
```

Có thể cấp split hoàn chỉnh bằng CSV gồm `row_id,split`, trong đó `split` nhận đúng ba giá trị `train_pool`, `validation`, `test`. Đây là cách nên dùng khi đã có split theo họ, thời gian hoặc nguồn dữ liệu.

## Gate và dữ liệu cần cho PID

Kiểm tra repository có đủ PE, mapping và report động hay chưa. Exit code `3` nghĩa là còn blocker dữ liệu:

```bash
python scripts/run_experiments.py audit-pid-inputs \
  --data data/processed/real_mini_dataset.csv \
  --output outputs/pid_input_audit
```

Nếu có archive NPZ lớn trên máy khác, `inspect-source` đọc header mà không nạp ma trận feature; `recover-manifest` tái tạo source index từ sampling/shuffle cũ. Với NPZ SOREL, `recover-sorel-metadata` chỉ lấy SHA/tag khi thứ tự nhãn được xác minh; không ghép JSONL EMBER 2018 vào SOREL. Khi mapping SOREL không phục hồi được, `recover-ember-dataset` tạo một CSV mới từ bộ ba EMBER `X_test.dat`/`y_test.dat`/`test_features.jsonl` vốn có cùng thứ tự. Xem `docs/PID_INPUT_CHECKLIST.md` để lấy lệnh PowerShell cụ thể.

Phần static uncertainty gate có thể đo trước khi có sandbox data. Runner tách validation thành hai phần rời nhau: một phần fit Platt calibration, phần còn lại chọn threshold; test chỉ dùng đánh giá:

```bash
python scripts/run_experiments.py gate \
  --al-run outputs/thesis_run/al \
  --output outputs/static_gate \
  --max-early-fnr 0.02 \
  --max-early-fpr 0.02
```

Giao thức xác nhận nhiều fold cho AL và Fidelity, cùng hợp đồng dữ liệu PID theo thời gian, được mô tả tại [`docs/CONFIRMATORY_RUNBOOK.md`](docs/CONFIRMATORY_RUNBOOK.md). Các lệnh chính là `confirmatory-al`, `confirmatory-fidelity`, `prepare-temporal`, `validate-temporal` và `temporal-fusion`.

Khi không có hạ tầng giữ/chạy PE, giao thức [`docs/EVENT_INDEXED_PID_RUNBOOK.md`](docs/EVENT_INDEXED_PID_RUNBOOK.md)
dùng MalBehavD-V1 và metadata PE theo cùng SHA-256. Đường chạy này không tải
executable; nó đánh giá PID theo số API call đã quan sát và phải được báo là
generic Windows malware benchmark, không phải latency theo giây hay ransomware-specific.

Để kiểm chứng riêng I và D, tạo mẫu nhiều time step trên mỗi PE:

```bash
python scripts/run_experiments.py prepare-temporal \
  --al-run outputs/thesis_run/al \
  --output outputs/pid_temporal_input \
  --windows 5 15 30 60
```

Sau khi thu thập, hoàn thiện `dynamic_time_series.csv` và `provenance.json`, cập nhật SHA-256 rồi kiểm tra:

```bash
python scripts/run_experiments.py validate-temporal \
  --data outputs/pid_temporal_input/dynamic_time_series.csv \
  --provenance outputs/pid_temporal_input/provenance.json
```

Lệnh `prepare-dynamic`/`fusion` cũ chỉ xử lý một dynamic score trên mỗi mẫu. Nó có thể so sánh weighting tĩnh–động nhưng không đủ để quy lợi ích riêng cho I và D. Thí nghiệm PID chính phải dùng nhiều time step, reset theo từng PE execution và report có hash hợp lệ.

## Công thức được cài đặt

Ở bước quan sát rời rạc `k`:

```text
e[k]        = P_static - P_dynamic[k]
Δt[k]       = elapsed[k] - elapsed[k-1]
I[k]        = clip(I[k-1] + e[k] Δt[k], I_min, I_max)
D[k]        = (e[k] - e[k-1]) / Δt[k], với D[0] = 0
u[k]        = Kp e[k] + Ki I[k] + Kd D[k]
w_static[k] = clip(sigmoid(u[k]), 0.1, 0.9)
P_fused[k]  = w_static[k] P_static[k] + (1-w_static[k]) P_dynamic[k]
```

Các hệ số mặc định `Kp=0.85`, `Ki=0.12`, `Kd=0.35` chỉ là cấu hình tham chiếu. Runner temporal chọn gain trên validation và đánh giá một lần trên test. Integral clipping là chính sách anti-windup; trạng thái reset theo từng PE execution. Đây là heuristic điều chỉnh trọng số theo lịch sử bất đồng giữa hai điểm, không phải định lý ổn định của một plant vật lý và không tự tạo cam kết độ trễ.

Active Learning dùng `U = 1 - 2|p-0.5|`. Từ SHAP có dấu `φ`, đặt tổng phần dương `A+`, độ lớn phần âm `A-`, `q=A+/(A++A-)`, rồi tính entropy nhị phân `H(q)` và `V=Var_j(φ_j)`. Từng tín hiệu được min-max trên pool tại vòng hiện tại trước khi ghép theo trọng số khai báo trong `src/experiments/signals.py`.

## Kết quả đã đo

Gói mới nhất dùng dữ liệu EMBER 2018 có định danh hàng đã kiểm tra nằm tại [`results/measured_20261019_ember_identity`](results/measured_20261019_ember_identity/README.md). Gói chứa artifact được tải lên, bảng tái tính độc lập, biểu đồ và hash. Đây là nguồn số liệu nên ưu tiên cho phần AL/Fidelity/static gate; báo cáo trong gói ghi rõ các kết luận chưa được dữ liệu ủng hộ.

Gói báo cáo gọn của lần chạy mặc định ngày 2026-10-14 nằm tại [`results/measured_20261014`](results/measured_20261014/README.md). Gói này chứa bảng, biểu đồ, config, tóm tắt và kết quả verification. Checkpoint và dự đoán từng mẫu không được commit vì toàn bộ run có kích thước khoảng 28 MB; có thể tái tạo bằng lệnh mặc định ở trên.

Kết quả calibration/static gate và audit đầu vào PID ngày 19/10/2026 nằm tại [`results/measured_20261019_gate`](results/measured_20261019_gate/README.md).

Audit MalBehavD-V1 và pilot 20 truy vấn metadata PE an toàn ngày 20/10/2026 nằm
tại [`results/measured_20261020_malbehavd_pid_intake`](results/measured_20261020_malbehavd_pid_intake/README.md).
Coverage pilot là 19/20; đây là bằng chứng intake/schema, chưa phải kết quả hiệu
quả PID.

## Mã legacy và demo

`scripts/live_defense_demo.py`, `scripts/defense_demo.py`, `src/xai_active_learning.py` và `src/fidelity_framework.py` là mã nguyên mẫu cũ. Một số đường chạy trong đó sinh tín hiệu bằng RNG hoặc dùng công thức đánh giá cũ; không dùng các tệp này để tạo số liệu luận văn. Lệnh thực nghiệm chuẩn là `scripts/run_experiments.py`.

Các file PE thô, archive lớn và EMBER raw được `.gitignore` loại khỏi Git. Trình trích đặc trưng riêng lẻ vẫn có thể chạy qua `src/feature_extraction.py` khi đã cài `lief` và đặt mẫu được phép phân tích trong `data/sample_pe/`.
