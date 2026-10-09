# train_and_shap.py
# Chạy 1 lần → xong hết: train + 3 hình SHAP cho luận văn

import os
import pandas as pd
import numpy as np
import lightgbm as lgb
import shap
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.model_selection import train_test_split

_ROOT = Path(__file__).resolve().parents[3]

# ------------------------------------------------------------------
# 0. Tạo thư mục figures nếu chưa có
# ------------------------------------------------------------------
os.makedirs(_ROOT / "figures", exist_ok=True)

# ------------------------------------------------------------------
# 1. Đọc dữ liệu (thay đường dẫn nếu cần)
# ------------------------------------------------------------------
print("Đang đọc dữ liệu...")
df = pd.read_csv(_ROOT / "data" / "processed" / "train_10percent.csv")

X = df.drop(columns=["label"])
y = df["label"]

print(f"Dataset: {X.shape[0]:,} mẫu, {X.shape[1]} đặc trưng")

# ------------------------------------------------------------------
# 2. Lấy 50k mẫu để train nhanh
# ------------------------------------------------------------------
X_sub, _, y_sub, _ = train_test_split(
    X, y, train_size=50_000, random_state=42, stratify=y
)

X_train, X_val, y_train, y_val = train_test_split(
    X_sub, y_sub, test_size=0.2, random_state=42, stratify=y_sub
)

print(f"Train: {X_train.shape[0]:,} | Val: {X_val.shape[0]:,}")

# ------------------------------------------------------------------
# 3. Tạo LightGBM Dataset
# ------------------------------------------------------------------
train_data = lgb.Dataset(X_train, label=y_train)
val_data   = lgb.Dataset(X_val,   label=y_val, reference=train_data)

# ------------------------------------------------------------------
# 4. Thiết lập tham số + train (tương thích LightGBM >=4.0)
# ------------------------------------------------------------------
params = {
    "objective": "binary",
    "metric": "auc",
    "learning_rate": 0.05,
    "num_leaves": 128,
    "max_depth": -1,
    "feature_fraction": 0.9,
    "bagging_fraction": 0.8,
    "bagging_freq": 5,
    "verbosity": -1,
    "seed": 42,
}

print("Đang train LightGBM...")
model = lgb.train(
    params,
    train_data,
    num_boost_round=2000,
    valid_sets=[train_data, val_data],
    valid_names=["train", "valid"],
    callbacks=[
        lgb.early_stopping(stopping_rounds=50, verbose=True),
        lgb.log_evaluation(period=100),
    ]
)

print(f"Best iteration: {model.best_iteration}")
print(f"Best AUC: {model.best_score['valid']['auc']:.5f}")

# ------------------------------------------------------------------
# 5. Tính SHAP values (dùng 5000 mẫu để nhanh)
# ------------------------------------------------------------------
print("Tính SHAP values...")
explainer = shap.TreeExplainer(model)

# Lấy 5000 mẫu từ validation để tính SHAP
X_shap = X_val.sample(n=min(5000, len(X_val)), random_state=42)
shap_values = explainer.shap_values(X_shap)

# Với binary classification, shap_values là list [class0, class1] → lấy class 1
if isinstance(shap_values, list):
    shap_class1 = shap_values[1]
else:
    shap_class1 = shap_values

# ------------------------------------------------------------------
# 6. SHAP Summary Plot – 20 đặc trưng (Hình 3.1 chương 3)
# ------------------------------------------------------------------
print("Vẽ shap_summary_plot.png (20 đặc trưng)...")
plt.figure(figsize=(10, 8))
shap.summary_plot(
    shap_class1,
    X_shap,
    max_display=20,
    show=False
)
plt.tight_layout()
plt.savefig(_ROOT / "figures" / "shap_summary_plot.png", dpi=300, bbox_inches="tight")
plt.close()
print("→ Đã lưu: figures/shap_summary_plot.png")

# ------------------------------------------------------------------
# 7. SHAP Summary Plot – 15 đặc trưng (dùng cho chương 5)
# ------------------------------------------------------------------
print("Vẽ shap_summary.png (15 đặc trưng)...")
plt.figure(figsize=(10, 7))
shap.summary_plot(
    shap_class1,
    X_shap,
    max_display=15,
    show=False
)
plt.tight_layout()
plt.savefig(_ROOT / "figures" / "shap_summary.png", dpi=300, bbox_inches="tight")
plt.close()
print("→ Đã lưu: figures/shap_summary.png")

# ------------------------------------------------------------------
# 8. SHAP Force Plot – 1 mẫu malware (tạm gọi là LockBit)
# ------------------------------------------------------------------
print("Vẽ shap_force_lockbit.png...")
# Chọn ngẫu nhiên 1 mẫu malware (label == 1)
malware_idx = df[df["label"] == 1].sample(1, random_state=42).index[0]
x_one = X.loc[[malware_idx]]  # giữ dạng DataFrame để tên cột hiện đẹp

shap_one = explainer.shap_values(x_one)
shap_one_class1 = shap_one[1] if isinstance(shap_one, list) else shap_one

shap.initjs()
plt.figure(figsize=(12, 4))
shap.force_plot(
    explainer.expected_value[1] if isinstance(explainer.expected_value, list) else explainer.expected_value,
    shap_one_class1,
    x_one,
    matplotlib=True,
    show=False,
    contribution_threshold=0.05
)
plt.tight_layout()
plt.savefig(_ROOT / "figures" / "shap_force_lockbit.png", dpi=300, bbox_inches="tight")
plt.close()
print("→ Đã lưu: figures/shap_force_lockbit.png")

print("\nHOÀN TẤT! Tất cả file đã sẵn sàng cho LaTeX:")
print("   figures/shap_summary_plot.png   → Hình 3.1 (20 đặc trưng)")
print("   figures/shap_summary.png        → Chương 5 (15 đặc trưng)")
print("   figures/shap_force_lockbit.png  → Force plot mẫu ransomware")