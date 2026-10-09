import numpy as np
import pandas as pd
from pathlib import Path

# ============================
# CONFIG
# ============================
NPZ_PATH = Path(__file__).resolve().parents[1] / "data" / "archives" / "train-features.npz"
OUTPUT_CSV = Path(__file__).resolve().parents[1] / "data" / "processed" / "train_small.csv"

TARGET_SAMPLES = 1_000_000
BATCH_SIZE = 50000

def main():
    print("="*80)
    print("📥 LOADING train_features.npz USING MEMMAP")
    print("="*80)

    # mmap_mode='r' → không load toàn file vào RAM
    data = np.load(NPZ_PATH, mmap_mode='r')

    keys = data.files
    print("Keys:", keys)

    X_full = data[keys[0]]  # arr_0
    y_full = data[keys[1]]  # arr_1

    total_rows = X_full.shape[0]
    print(f"Total rows in NPZ: {total_rows:,}")

    # Random index lấy 1M từ 10M
    rng = np.random.default_rng(42)
    chosen_idx = rng.choice(total_rows, TARGET_SAMPLES, replace=False)

    print(f"Sampling {len(chosen_idx):,} rows...")

    # Ghi từng batch để không vỡ RAM
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    if OUTPUT.exists():
        OUTPUT.unlink()

    for i in range(0, len(chosen_idx), BATCH_SIZE):
        batch_idx = chosen_idx[i:i+BATCH_SIZE]

        X_batch = X_full[batch_idx].astype("float32")
        y_batch = y_full[batch_idx].astype("int8")

        df_batch = pd.DataFrame(X_batch)
        df_batch["label"] = y_batch

        df_batch.to_csv(
            OUTPUT,
            mode="a",
            index=False,
            header=(i == 0),
        )

        print(f"  → Saved {i + len(batch_idx):,}/{TARGET_SAMPLES:,} rows")

    print("\n🎉 DONE! Saved:", OUTPUT)

if __name__ == "__main__":
    main()
