# ==================== test_on_ember_pre.py ====================
# Test model ransomware của bạn trên EMBER 2018 pre-vectorized features
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score, confusion_matrix
import lightgbm as lgb
import os

# Đường dẫn model ransomware của bạn
MODEL_PATH = r"D:\Code\Luanvan\ransomware_lgbm_1M_final.txt"  # THAY NẾU KHÁC

# Đường dẫn pre-vectorized EMBER (thay nếu bạn đặt chỗ khác)
EMBER_DIR = r"D:\Code\Luanvan\ember_test\ember_pre_vectorized"

# Load model
print("Đang load model ransomware...")
model = lgb.Booster(model_file=MODEL_PATH)
print(f"Model có {model.num_trees()} cây")

# Load test set EMBER (200k mẫu)
print("Đang load EMBER test set (200k mẫu)...")
X_test = np.load(os.path.join(EMBER_DIR, "X_test.npy"))
y_test = np.load(os.path.join(EMBER_DIR, "y_test.npy"))

print(f"Shape: {X_test.shape} | Số malware: {y_test.sum()} / {len(y_test)}")

# Dự đoán (EMBER có 2351 features, model bạn có ~2381 → sẽ lỗi nếu số cột không khớp)
# Nếu lỗi "number of features" → bỏ qua bước này và đọc phần dưới
try:
    y_prob = model.predict(X_test)
    y_pred = (y_prob >= 0.5).astype(int)

    acc = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_prob)
    cm = confusion_matrix(y_test, y_pred)

    print("\n🎉 KẾT QUẢ TEST TRÊN EMBER 2018 TEST SET")
    print(f"   Accuracy: {acc:.4f}")
    print(f"   F1-Score: {f1:.4f}")
    print(f"   AUC     : {auc:.4f}")
    print(f"   Confusion Matrix:\n{cm}")

except Exception as e:
    print(f"\n❌ Lỗi khi predict: {e}")
    print("   Nguyên nhân phổ biến: Số features không khớp (EMBER 2351 vs bạn ~2381)")
    print("   Giải pháp: Chỉ test trên subset features chung hoặc dùng bộ dữ liệu behavioral khác.")

# Nếu muốn test chỉ 10k mẫu đầu để nhanh
# X_test_sample = X_test[:10000]
# y_test_sample = y_test[:10000]