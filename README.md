# Phát hiện Ransomware bằng XAI và Active Learning

Luận văn thạc sĩ. Hệ thống phân loại PE ransomware bằng LightGBM trên đặc trưng EMBER (2381 chiều), rồi giải thích quyết định bằng SHAP và chọn mẫu gắn nhãn theo độ bất định của lời giải thích.

Ba đóng góp lõi nằm ở `src/`.

## Đóng góp

### 1. PID Fusion

`src/pid_fusion.py` dung hợp xác suất tĩnh `P_static` (LightGBM) và xác suất động `P_dynamic` (honeypot / sandbox).

Sai số `e(t) = P_static - P_dynamic` đi qua bộ điều khiển PID với hệ số thực nghiệm `Kp = 0.85`, `Ki = 0.12`, `Kd = 0.35`. Trọng số tĩnh là sigmoid của tín hiệu điều khiển, được kẹp trong `(0.1, 0.9)`:

```text
P_fused = w_static * P_static + (1 - w_static) * P_dynamic
```

Mục tiêu là giữ độ trễ quyết định quanh 15 ms thay vì chờ toàn bộ quan sát động.

### 2. XAI-Guided Active Learning

`src/xai_active_learning.py` chọn mẫu cần gắn nhãn theo phương sai SHAP giữa các cây, không chỉ theo entropy hay margin của xác suất đầu ra. Mẫu mà lời giải thích không ổn định được ưu tiên, vì đó là vùng mô hình chưa giải thích được hành vi.

### 3. Fidelity OFS

`src/fidelity_framework.py` chấm độ trung thực của giải thích SHAP trên đặc trưng PE bằng Overall Fidelity Score (OFS). OFS là trung bình có trọng số của ba thước đo:

- **Feature Faithfulness (FF):** xóa top-K đặc trưng mà SHAP cho là quan trọng thì AUC phải giảm.
- **Explanation Consistency (EC):** nhiễu nhỏ trên đầu vào không được lật lời giải thích.
- **Contrastive Fidelity (CF):** cặp malware và benign gần nhau phải được tách bằng đúng các đặc trưng phân biệt.

Khung này xử lý đặc trưng PE tương quan với nhau, không xóa ngây thơ từng cột độc lập.

## Cấu trúc

```text
data/sample_pe/       PE mẫu để trích đặc trưng (file .exe không được commit)
data/processed/       CSV đặc trưng đã trích xuất
data/dynamic_logs/    JSON, CSV và log honeypot
data/archives/        NPZ / ZIP gốc, chỉ giữ trên máy local
data/ember2018/       EMBER 2018 raw, chỉ giữ trên máy local
models/               Trọng số LightGBM (.pkl và booster .txt)
src/                  feature_extraction.py, pid_fusion.py,
                      xai_active_learning.py, fidelity_framework.py
scripts/              pipeline huấn luyện, thực nghiệm, mã EMBER kèm theo
notebooks/            notebook EMBER
dashboard/            giao diện Streamlit và honeypot monitor
figures/              hình luận văn
results/              số liệu và biểu đồ thực nghiệm
```

`scripts/ember/` là bản EMBER kèm các thí nghiệm của luận văn. Các file `pe_feature_extractor.py`, `active_learner.py` và `xai_fidelity.py` trong đó là lớp tương thích, trỏ về module canonical trong `src/`.

Thư mục `doanh-trang/` không thuộc luận văn và được `.gitignore` loại khỏi remote.

## Cài đặt

Chạy mọi lệnh từ thư mục gốc của repo.

```bash
python -m venv .venv
```

Windows (PowerShell):

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e scripts/ember
```

Bash:

```bash
source .venv/bin/activate
pip install -r requirements.txt
pip install -e scripts/ember
```

`pip install -e scripts/ember` cần cho `src/feature_extraction.py`, vì trình trích đặc trưng gọi gói `ember` và LIEF.

## Chạy

Ablation ba bài toán (PID fusion, active learning, fidelity) và ghi kết quả vào `results/`:

```bash
python scripts/run_experiments.py
```

Demo trực tiếp: nạp `models/ransomware_lgbm_1M_final.txt`, chấm `data/processed/real_mini_dataset.csv`, chạy PID fusion và TreeSHAP, ghi log vào `data/dynamic_logs/`:

```bash
python scripts/live_defense_demo.py
```

Vẽ lại biểu đồ từ log thô:

```bash
python scripts/generate_thesis_charts.py
```

Active learning (demo ngắn) và fidelity:

```bash
python src/xai_active_learning.py --mode demo
python src/fidelity_framework.py --quick
```

Trích đặc trưng một file PE (file mẫu đặt trong `data/sample_pe/`, không commit):

```bash
python src/feature_extraction.py data/sample_pe/sample.exe
```

Giao diện giải thích:

```bash
streamlit run dashboard/xai_dashboard.py
```

Huấn luyện lại LightGBM trên CSV đã xử lý (file lớn, chỉ có local):

```bash
python scripts/train_lightgbm_optimized.py
```

## Dữ liệu không nằm trên Git

Các file sau vượt giới hạn GitHub hoặc là bộ dữ liệu thô. Chúng vẫn ở trên máy, và `.gitignore` đã loại chúng:

| Đường dẫn | Vai trò |
| --- | --- |
| `data/archives/train-features.npz` | Đặc trưng train gốc |
| `data/archives/test-features.npz` | Tập test held-out |
| `data/archives/validation-features.npz` | Tập validation |
| `data/processed/train_small.csv` | Mẫu rút từ NPZ train |
| `data/processed/validation_dataset_small.csv` | CSV validation |
| `data/processed/train_10percent.csv` | 10% dùng cho thí nghiệm nhanh |
| `data/ember2018/` | EMBER 2018 (JSONL và ma trận `.dat`) |

Được commit: `data/processed/mini_sorel_features.csv`, `data/processed/real_mini_dataset.csv`, và trọng số trong `models/`.

Đặt PE cần phân tích vào `data/sample_pe/`. Mọi `*.exe` và `*.dll` bị bỏ qua khi `git add`.
