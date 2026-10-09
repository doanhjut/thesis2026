import pandas as pd
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
df = pd.read_csv(_ROOT / "data" / "processed" / "train_small.csv")

# Lấy ngẫu nhiên 10% (giữ nguyên tỷ lệ label)
df_sample = df.sample(frac=0.1, random_state=42)

# Hoặc lấy 1/10 đầu tiên (nhanh hơn nếu file đã shuffle)
# df_sample = df.iloc[:len(df)//10]

df_sample.to_csv(_ROOT / "data" / "processed" / "train_10percent.csv", index=False)
print(f"Đã lưu file 10%: {len(df_sample):,} dòng")