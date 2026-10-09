
import h5py
import pandas as pd
import numpy as np
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
h5_path = str(_ROOT / "data" / "archives" / "train_features.h5")
output_csv = str(_ROOT / "data" / "processed" / "train_small.csv")
target_samples = 1000000
seed = 42

print("Sampling from HDF5...")

rng = np.random.default_rng(seed)

with h5py.File(h5_path, 'r') as hf:
    X = hf['X']
    y = hf['y']
    total = X.shape[0]
    
    # Stratified sampling
    n_bins = 50
    bin_size = total // n_bins
    samples_per_bin = target_samples // n_bins
    
    indices = []
    for i in range(n_bins):
        start = i * bin_size
        end = min(start + bin_size, total)
        bin_indices = rng.integers(start, end, samples_per_bin)
        indices.extend(bin_indices)
    
    indices = np.array(indices[:target_samples])
    indices.sort()
    
    print(f"Reading {len(indices):,} samples...")
    
    X_sample = X[indices]
    y_sample = y[indices]
    
    df = pd.DataFrame(X_sample, dtype='float32')
    df['label'] = y_sample
    
    # Adjust ratio
    n_malware = (df['label'] == 1).sum()
    ratio = n_malware / len(df)
    
    print(f"Malware ratio: {ratio:.1%}")
    
    df.to_csv(output_csv, index=False)
    print(f"Saved: {output_csv}")
