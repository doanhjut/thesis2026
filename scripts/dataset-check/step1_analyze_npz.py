import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
import pandas as pd

df = pd.read_csv(r"D:\Code\WoDT\Digital-Twin-in-python\train_small.csv")
X = df.drop(columns=["label"])
y = df["label"]

X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

train_data = lgb.Dataset(X_train, label=y_train)
valid_data = lgb.Dataset(X_val, label=y_val, reference=train_data)

params = {
    'objective': 'binary',
    'metric': 'auc',
    'learning_rate': 0.05,
    'num_leaves': 128,
    'max_bin': 63,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    
    'device': 'gpu',           # đổi thành 'gpu' nếu muốn chạy card
    'gpu_platform_id': 0,
    'gpu_device_id': 0,
    'tree_learner': 'data',
    'histogram_pool_size': 1024,
    
    'verbose': 10
}

model = lgb.train(
    params,
    train_data,
    num_boost_round=1000,
    valid_sets=[valid_data],
    callbacks=[
        lgb.early_stopping(stopping_rounds=50),
        lgb.log_evaluation(period=20)
    ]
)

# Dự đoán
y_prob = model.predict(X_val)
y_pred = (y_prob > 0.5).astype(int)

print("Acc:", accuracy_score(y_val, y_pred))
print("F1 :", f1_score(y_val, y_pred))
print("AUC:", roc_auc_score(y_val, y_prob))