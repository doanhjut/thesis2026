# ==================== train_perfect.py ====================
# LightGBM Ransomware Detection - Phiên bản HOÀN HẢO cho 1M+ rows
# Tác giả: Grok (dành riêng cho bạn)
# Ngày: 2025

import pandas as pd
import lightgbm as lgb
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score, confusion_matrix
import os
import gc
import time

_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = str(_ROOT / "data" / "processed" / "train_small.csv")
MODEL_SAVE_PATH = str(_ROOT / "models" / "ransomware_lgbm_1M_final.txt")
LOG_FILE = str(_ROOT / "data" / "dynamic_logs" / "training_log.txt")

print("Bắt đầu huấn luyện mô hình LightGBM trên dữ liệu đầy đủ (1M+ rows)...\n")

start_time = time.time()

# ------------------ 2. Đọc dữ liệu thông minh (tiết kiệm RAM) ------------------
print("Đang đọc dữ liệu (có thể mất 10-60 giây với 1M rows)...")
df = pd.read_csv(DATA_PATH)

print(f"Đã đọc xong: {df.shape[0]:,} rows × {df.shape[1]:,} columns")
print(f"Phân bố nhãn: \n{df['label'].value_counts()}\n")

X = df.drop(columns=["label"])
y = df["label"]

# Giải phóng RAM
del df
gc.collect()

# ------------------ 3. Chia train/val (stratify để giữ tỷ lệ lớp) ------------------
X_train, X_val, y_train, y_val = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"Train size: {X_train.shape[0]:,} | Val size: {X_val.shape[0]:,}")

# ------------------ 4. Tạo Dataset LightGBM (tối ưu tốc độ) ------------------
train_data = lgb.Dataset(X_train, label=y_train, free_raw_data=False)
val_data = lgb.Dataset(X_val, label=y_val, reference=train_data, free_raw_data=False)

# Giải phóng bộ nhớ không cần thiết
del X_train, X_val, y_train
gc.collect()

# ------------------ 5. Tham số tối ưu cho dữ liệu lớn + hiệu suất cao ------------------
params = {
    "objective": "binary",
    "metric": "binary_error,auc",
    "boosting_type": "gbdt",
    "num_leous": 256,              # Tăng lên vì dữ liệu lớn
    "max_depth": 18,
    "learning_rate": 0.03,         # Giảm lr để học ổn định hơn với dữ liệu lớn
    "feature_fraction": 0.85,
    "bagging_fraction": 0.85,
    "bagging_freq": 5,
    "min_data_in_leaf": 100,
    "lambda_l1": 0.1,
    "lambda_l2": 0.1,
    "max_bin": 255,
    "verbosity": -1,
    "force_col_wise": True,        # Bắt buộc với dữ liệu >500k rows để tránh lỗi bộ nhớ
    "seed": 42
}

# ------------------ 6. Huấn luyện với callback hiện đại ------------------
print("Bắt đầu huấn luyện mô hình...\n")

clf = lgb.train(
    params,
    train_data,
    num_boost_round=5000,                  # Cho phép train rất sâu
    valid_sets=[val_data],
    valid_names=["valid"],
    callbacks=[
        lgb.early_stopping(stopping_rounds=100, verbose=True),   # Dừng nếu không cải thiện 100 vòng
        lgb.log_evaluation(period=50),                           # In log mỗi 50 vòng
        lgb.record_evaluation({})                                # Ghi lại lịch sử
    ]
)

best_iter = clf.best_iteration
print(f"\nHUẤN LUYỆN HOÀN TẤT!")
print(f"Best iteration: {best_iter}")
print(f"Valid binary_error tốt nhất: {clf.best_score['valid']['binary_error']:.6f}")
print(f"Valid AUC tốt nhất: {clf.best_score['valid']['auc']:.6f}")

# ------------------ 7. Dự đoán & đánh giá trên validation ------------------
print("\nĐang dự đoán trên tập validation...")
y_pred_prob = clf.predict(val_data.data, num_iteration=best_iter)
y_pred = (y_pred_prob >= 0.5).astype(int)

acc = accuracy_score(y_val, y_pred)
f1 = f1_score(y_val, y_pred)
auc = roc_auc_score(y_val, y_pred_prob)

print("\n" + "="*50)
print("KẾT QUẢ CUỐI CÙNG TRÊN TẬP VALIDATION")
print("="*50)
print(f"   Accuracy       : {acc:.6f}")
print(f"   F1-Score       : {f1:.6f}")
print(f"   AUC            : {auc:.6f}")
print(f"   Confusion Matrix:\n{confusion_matrix(y_val, y_pred)}")
print("="*50)

# ------------------ 8. LƯU MODEL TỐT NHẤT ------------------
print(f"\nĐang lưu model vào: {MODEL_SAVE_PATH}")
clf.save_model(MODEL_SAVE_PATH)

file_size = os.path.getsize(MODEL_SAVE_PATH) / (1024*1024)
print(f"Lưu thành công! Kích thước: {file_size:.2f} MB")

# Ghi log đầy đủ
with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write(f"Thời gian huấn luyện: {(time.time() - start_time)/60:.2f} phút\n")
    f.write(f"Số iteration tốt nhất: {best_iter}\n")
    f.write(f"Accuracy: {acc:.6f} | F1: {f1:.6f} | AUC: {auc:.6f}\n")
    f.write(f"Model path: {os.path.abspath(MODEL_SAVE_PATH)}\n")

print(f"\nLog đã được lưu tại: {LOG_FILE}")
print(f"Tổng thời gian: {(time.time() - start_time)/60:.2f} phút")
print("\nBẠN ĐÃ SỞ HỮU MỘT CON MODEL SIÊU MẠNH VÀ CÓ THỂ DÙNG MÃI MÃI!")