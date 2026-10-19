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

Nếu có archive NPZ lớn trên máy khác, `inspect-source` đọc header mà không nạp ma trận feature; `recover-manifest` tái tạo source index từ sampling/shuffle cũ. Với NPZ SOREL, dùng tiếp `recover-sorel-metadata` cùng `meta.db` và danh sách missing-feature chính thức để lấy SHA-256/tag; không ghép JSONL EMBER 2018 vào SOREL. Xem `docs/PID_INPUT_CHECKLIST.md` để lấy lệnh PowerShell cụ thể.

Phần static uncertainty gate có thể đo trước khi có sandbox data. Runner tách validation thành hai phần rời nhau: một phần fit Platt calibration, phần còn lại chọn threshold; test chỉ dùng đánh giá:

```bash
python scripts/run_experiments.py gate \
  --al-run outputs/thesis_run/al \
  --output outputs/static_gate \
  --max-early-fnr 0.02 \
  --max-early-fpr 0.02
```

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
e[k]        = P_static[k] - P_dynamic[k]
u[k]        = Kp e[k] + Ki Σ(i=0..k)e[i] + Kd(e[k] - e[k-1])
w_static[k] = clip(sigmoid(u[k]), 0.1, 0.9)
P_fused[k]  = w_static[k] P_static[k] + (1-w_static[k]) P_dynamic[k]
```

Các hệ số mặc định `Kp=0.85`, `Ki=0.12`, `Kd=0.35` chỉ là cấu hình cần đối chứng. Pipeline chọn cấu hình trên validation và đánh giá một lần trên test. Công thức hiện là PID theo bước quan sát, chưa có `Δt` hay anti-windup; không tự tạo cam kết độ trễ.

Active Learning dùng `U = 1 - 2|p-0.5|`. Từ SHAP có dấu `φ`, đặt tổng phần dương `A+`, độ lớn phần âm `A-`, `q=A+/(A++A-)`, rồi tính entropy nhị phân `H(q)` và `V=Var_j(φ_j)`. Từng tín hiệu được min-max trên pool tại vòng hiện tại trước khi ghép theo trọng số khai báo trong `src/experiments/signals.py`.

## Kết quả đã đo

Gói báo cáo gọn của lần chạy mặc định ngày 2026-10-14 nằm tại [`results/measured_20261014`](results/measured_20261014/README.md). Gói này chứa bảng, biểu đồ, config, tóm tắt và kết quả verification. Checkpoint và dự đoán từng mẫu không được commit vì toàn bộ run có kích thước khoảng 28 MB; có thể tái tạo bằng lệnh mặc định ở trên.

Kết quả calibration/static gate và audit đầu vào PID ngày 19/10/2026 nằm tại [`results/measured_20261019_gate`](results/measured_20261019_gate/README.md).

## Mã legacy và demo

`scripts/live_defense_demo.py`, `scripts/defense_demo.py`, `src/xai_active_learning.py` và `src/fidelity_framework.py` là mã nguyên mẫu cũ. Một số đường chạy trong đó sinh tín hiệu bằng RNG hoặc dùng công thức đánh giá cũ; không dùng các tệp này để tạo số liệu luận văn. Lệnh thực nghiệm chuẩn là `scripts/run_experiments.py`.

Các file PE thô, archive lớn và EMBER raw được `.gitignore` loại khỏi Git. Trình trích đặc trưng riêng lẻ vẫn có thể chạy qua `src/feature_extraction.py` khi đã cài `lief` và đặt mẫu được phép phân tích trong `data/sample_pe/`.
