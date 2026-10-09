import numpy as np
import pandas as pd
from pathlib import Path

# ============================
# CONFIG — ĐƯỜNG DẪN
# ============================
NPZ_PATH = Path(__file__).resolve().parents[1] / "data" / "archives" / "train-features.npz"
OUTPUT_CSV = Path(__file__).resolve().parents[1] / "data" / "processed" / "train_dataset_2M.csv"

MAX_ROWS = 2_000_000        # huấn luyện tốt, nhanh, không quá nặng
USE_FLOAT32 = True          # giảm 50% RAM


def main():
    print("=" * 80)
    print("📥 LOADING train.npz (features + labels)")
    print("=" * 80)

    # Load file
    data = np.load(NPZ_PATH)
    print("Keys:", data.files)

    arr0 = data[data.files[0]]
    arr1 = data[data.files[1]]

    # Xác định feature và label
    if arr0.ndim == 2 and arr1.ndim == 1:
        X = arr0
        y = arr1
    elif arr1.ndim == 2 and arr0.ndim == 1:
        X = arr1
        y = arr0
    else:
        raise ValueError("Không phân biệt được features / labels!")

    print(f"Features shape: {X.shape}")
    print(f"Labels shape  : {y.shape}")

    # Cắt nhỏ để train nhanh
    n = min(MAX_ROWS, X.shape[0])
    X = X[:n]
    y = y[:n]

    # Đưa về float32 để giảm RAM 50%
    if USE_FLOAT32:
        X = X.astype("float32")

    df = pd.DataFrame(X)
    df["label"] = y.astype("int8")

    print(f"\n📄 Final DataFrame shape: {df.shape}")

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_CSV, index=False)

    print(f"💾 Dataset saved → {OUTPUT_CSV}")


if __name__ == "__main__":
    main()

