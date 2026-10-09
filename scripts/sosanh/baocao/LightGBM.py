import pandas as pd
import lightgbm as lgb
from pathlib import Path
from sklearn.model_selection import train_test_split

_ROOT = Path(__file__).resolve().parents[3]
df = pd.read_csv(_ROOT / "data" / "processed" / "train_10percent.csv")

X = df.drop(columns=["label"])
y = df["label"]

# Lấy 50k mẫu nhanh
X_sub, _, y_sub, _ = train_test_split(
    X, y, train_size=50_000, random_state=42, stratify=y
)

X_train, X_val, y_train, y_val = train_test_split(
    X_sub, y_sub, test_size=0.2, random_state=42, stratify=y_sub
)

train_data = lgb.Dataset(X_train, label=y_train)
val_data   = lgb.Dataset(X_val,   label=y_val, reference=train_data)  # reference giúp early stopping hoạt động tốt hơn

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
}

model = lgb.train(
    params,
    train_data,
    num_boost_round=1000,   # tăng lên vì có early stopping
    valid_sets=[val_data],
    callbacks=[
        lgb.early_stopping(stopping_rounds=30, verbose=True),
        lgb.log_evaluation(100),  # in log mỗi 100 round
    ]
)

print(f"Best iteration: {model.best_iteration}")