# ==================== predict.py ====================
# Dự đoán siêu nhanh bằng model đã train (1M rows)
import lightgbm as lgb
import pandas as pd
import time
import os
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = str(_ROOT / "models" / "ransomware_lgbm_1M_final.txt")

# Load model (chỉ mất ~0.5 giây)
print("Đang load model thần thánh...")
model = lgb.Booster(model_file=MODEL_PATH)
print(f"Load thành công! Số cây: {model.num_trees()}")

# Đọc file cần dự đoán (có thể là test set, hoặc dữ liệu real-time)
TEST_PATH = str(_ROOT / "data" / "processed" / "validation_dataset_small.csv")

print("Đang đọc dữ liệu mới...")
start = time.time()
df = pd.read_csv(TEST_PATH)

X_test = df.drop(columns=["label"], errors="ignore")   # nếu có label thì bỏ, không thì ignore

print(f"Đang dự đoán {len(X_test):,} mẫu...")
y_prob = model.predict(X_test)        # Siêu nhanh: ~100k–500k mẫu/giây
y_pred = (y_prob >= 0.5).astype(int)

# Lưu kết quả
result = pd.DataFrame({
    "probability_ransomware": y_prob.round(6),
    "prediction": y_pred
})

output_file = "FINAL_PREDICTION_RESULT.csv"
result.to_csv(output_file, index=False)

print(f"\nHOÀN TẤT!")
print(f"Thời gian dự đoán: {time.time()-start:.2f} giây")
print(f"Kết quả lưu tại: {os.path.abspath(output_file)}")
print(f"Số mẫu bị phát hiện ransomware: {y_pred.sum():,} / {len(y_pred):,}")
print(f"Tỷ lệ nhiễm: {y_pred.mean()*100:.3f}%")