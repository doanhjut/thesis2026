from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from lightgbm import LGBMClassifier
from pathlib import Path
import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
df = pd.read_csv(_ROOT / "data" / "processed" / "train_small.csv")
X = df.drop(columns=["label"]).values
y = df["label"].values

X_train, X_val, y_train, y_val = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

model = LGBMClassifier(
    n_estimators=500,
    max_depth=-1,
    learning_rate=0.05,
    n_jobs=-1
)
model.fit(X_train, y_train)

y_pred = model.predict(X_val)
y_prob = model.predict_proba(X_val)[:, 1]

print("Acc:", accuracy_score(y_val, y_pred))
print("F1 :", f1_score(y_val, y_pred))
print("AUC:", roc_auc_score(y_val, y_prob))
