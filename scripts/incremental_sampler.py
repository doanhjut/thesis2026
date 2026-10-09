
import numpy as np
import pandas as pd
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
npz_path = str(_ROOT / "data" / "archives" / "train-features.npz")
output_csv = str(_ROOT / "data" / "processed" / "train_small.csv")
target_samples = 1000000
seed = 42

print("Opening NPZ with mmap...")

# Mở NPZ với memory mapping
data = np.load(npz_path, mmap_mode='r')
X = data['arr_0']
y = data['arr_1']

total = X.shape[0]
print(f"Total: {total:,} samples")

# Random indices
rng = np.random.default_rng(seed)

# Stratified: chia 50 bins
n_bins = 50
bin_size = total // n_bins
samples_per_bin = target_samples // n_bins

all_samples = []

for bin_idx in range(n_bins):
    start = bin_idx * bin_size
    end = min(start + bin_size, total)
    
    # Random chọn trong bin này
    bin_indices = rng.integers(start, end, samples_per_bin)
    bin_indices.sort()
    
    print(f"Bin {bin_idx+1}/{n_bins}: reading {len(bin_indices)} samples...")
    
    # Đọc TỪNG sample để tránh load cả bin
    for idx in bin_indices:
        try:
            x_sample = X[idx:idx+1][0]  # Chỉ đọc 1 row
            y_sample = y[idx]
            all_samples.append((x_sample, y_sample))
        except:
            print(f"  Skip index {idx}")
    
    # Save checkpoint mỗi 10 bins
    if (bin_idx + 1) % 10 == 0:
        print(f"  Checkpoint: {len(all_samples):,} samples collected")

print(f"\nCollected {len(all_samples):,} samples")

# Convert to DataFrame
X_list = [s[0] for s in all_samples]
y_list = [s[1] for s in all_samples]

df = pd.DataFrame(X_list, dtype='float32')
df['label'] = pd.Series(y_list, dtype='int8')

# Adjust distribution
n_malware = (df['label'] == 1).sum()
n_benign = (df['label'] == 0).sum()

print(f"\nDistribution: {n_malware:,} malware, {n_benign:,} benign")

target_malware = int(len(df) * 0.598)
target_benign = len(df) - target_malware

malware_df = df[df['label'] == 1]
benign_df = df[df['label'] == 0]

if len(malware_df) >= target_malware:
    malware_final = malware_df.sample(n=target_malware, random_state=seed)
else:
    malware_final = malware_df

if len(benign_df) >= target_benign:
    benign_final = benign_df.sample(n=target_benign, random_state=seed)
else:
    benign_final = benign_df

df_final = pd.concat([malware_final, benign_final]).sample(frac=1, random_state=seed)

print(f"\nFinal: {len(df_final):,} samples")
df_final.to_csv(output_csv, index=False)
print(f"Saved: {output_csv}")
