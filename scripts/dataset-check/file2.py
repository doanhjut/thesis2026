"""
SEQUENTIAL STREAMING SAMPLER WITH RESERVOIR SAMPLING
Thời gian: 20-40 phút (đọc tuần tự toàn bộ file)
Chất lượng: Tốt nhất (representative sampling)
"""

import numpy as np
import pandas as pd
from pathlib import Path
import zipfile
import struct

NPZ_PATH = Path(r"D:\Code\WoDT\Digital-Twin-in-python\train-features.npz")
OUTPUT_CSV = Path(r"D:\Code\WoDT\Digital-Twin-in-python\train_small.csv")

TARGET_SAMPLES = 1_000_000
MALWARE_RATIO = 0.598
SEED = 42

# Sequential reading config
STREAM_BATCH_SIZE = 10_000  # Đọc 10K samples mỗi lần


def read_npy_header(file_obj):
    """Đọc header"""
    magic = file_obj.read(6)
    if magic != b'\x93NUMPY':
        raise ValueError("Not a valid .npy file")
    
    major, minor = struct.unpack('BB', file_obj.read(2))
    
    if major == 1:
        header_len = struct.unpack('<H', file_obj.read(2))[0]
    else:
        header_len = struct.unpack('<I', file_obj.read(4))[0]
    
    header = file_obj.read(header_len)
    header_dict = eval(header.decode('latin1'))
    
    return header_dict['shape'], np.dtype(header_dict['descr']), file_obj.tell()


def reservoir_sample_streaming(npz_path, target_samples, seed=42):
    """
    Reservoir sampling: đọc tuần tự, giữ lại target_samples ngẫu nhiên
    """
    print(f"\n🌊 Sequential Streaming with Reservoir Sampling...")
    print(f"   Target: {target_samples:,} samples")
    print(f"   ⏱️ This will take 20-40 minutes (reading entire dataset)")
    
    rng = np.random.default_rng(seed)
    
    with zipfile.ZipFile(npz_path, 'r') as z:
        # Get shapes
        with z.open('arr_0.npy') as f:
            X_shape, X_dtype, X_offset = read_npy_header(f)
        
        with z.open('arr_1.npy') as f:
            y_shape, y_dtype, y_offset = read_npy_header(f)
        
        total_samples = X_shape[0]
        n_features = X_shape[1]
        
        print(f"   Total samples: {total_samples:,}")
        print(f"   Features: {n_features}")
        
        # Initialize reservoir
        reservoir_X = np.zeros((target_samples, n_features), dtype='float32')
        reservoir_y = np.zeros(target_samples, dtype='int8')
        
        samples_seen = 0
        
        # Stream through dataset
        with z.open('arr_0.npy') as f_X, z.open('arr_1.npy') as f_y:
            # Skip headers
            f_X.seek(X_offset)
            f_y.seek(y_offset)
            
            sample_size_X = n_features * X_dtype.itemsize
            sample_size_y = y_dtype.itemsize
            
            while samples_seen < total_samples:
                # Đọc batch
                batch_size = min(STREAM_BATCH_SIZE, total_samples - samples_seen)
                
                X_bytes = f_X.read(batch_size * sample_size_X)
                y_bytes = f_y.read(batch_size * sample_size_y)
                
                X_batch = np.frombuffer(X_bytes, dtype=X_dtype).reshape(batch_size, n_features)
                y_batch = np.frombuffer(y_bytes, dtype=y_dtype)
                
                # Reservoir sampling logic
                for i in range(batch_size):
                    sample_idx = samples_seen + i
                    
                    if sample_idx < target_samples:
                        # Fill reservoir
                        reservoir_X[sample_idx] = X_batch[i]
                        reservoir_y[sample_idx] = y_batch[i]
                    else:
                        # Random replacement
                        j = rng.integers(0, sample_idx + 1)
                        if j < target_samples:
                            reservoir_X[j] = X_batch[i]
                            reservoir_y[j] = y_batch[i]
                
                samples_seen += batch_size
                
                # Progress
                if samples_seen % 100_000 == 0:
                    pct = samples_seen / total_samples * 100
                    print(f"   [{pct:5.1f}%] Processed {samples_seen:,}/{total_samples:,} samples")
        
        print(f"   ✅ Completed streaming through {total_samples:,} samples")
        print(f"   ✅ Reservoir contains {len(reservoir_X):,} samples")
        
        return reservoir_X, reservoir_y


def balance_distribution(X, y, target_ratio, seed=42):
    """Cân bằng distribution"""
    print(f"\n⚖️ Balancing distribution to {target_ratio:.3f}...")
    
    current_malware = (y == 1).sum()
    current_ratio = current_malware / len(y)
    
    print(f"   Current: {current_ratio:.3f}")
    print(f"   Target: {target_ratio:.3f}")
    
    target_malware = int(len(y) * target_ratio)
    target_benign = len(y) - target_malware
    
    malware_idx = np.where(y == 1)[0]
    benign_idx = np.where(y == 0)[0]
    
    rng = np.random.default_rng(seed)
    
    if len(malware_idx) > target_malware:
        selected_malware = rng.choice(malware_idx, size=target_malware, replace=False)
    else:
        selected_malware = malware_idx
    
    if len(benign_idx) > target_benign:
        selected_benign = rng.choice(benign_idx, size=target_benign, replace=False)
    else:
        selected_benign = benign_idx
    
    selected = np.concatenate([selected_malware, selected_benign])
    rng.shuffle(selected)
    
    X_balanced = X[selected]
    y_balanced = y[selected]
    
    final_ratio = (y_balanced == 1).sum() / len(y_balanced)
    print(f"   ✅ Final: {final_ratio:.3f} (diff: {abs(final_ratio - target_ratio):.4f})")
    
    return X_balanced, y_balanced


def main():
    print("="*80)
    print("🐌 SEQUENTIAL STREAMING SOREL-20M SAMPLER")
    print("="*80)
    print("⚠️ This method is SLOW but GUARANTEED to work")
    print("⏱️ Expected time: 20-40 minutes")
    print("="*80)
    
    import time
    start = time.time()
    
    # 1. Reservoir sampling
    X, y = reservoir_sample_streaming(NPZ_PATH, TARGET_SAMPLES, SEED)
    
    # 2. Balance distribution
    X_final, y_final = balance_distribution(X, y, MALWARE_RATIO, SEED)
    
    # 3. Save
    print(f"\n💾 Saving to CSV...")
    df = pd.DataFrame(X_final)
    df['label'] = y_final
    df.to_csv(OUTPUT_CSV, index=False)
    
    print(f"   ✅ Saved: {OUTPUT_CSV}")
    print(f"   📊 Shape: {df.shape}")
    
    # Report
    malware_count = (y_final == 1).sum()
    ratio = malware_count / len(y_final)
    
    print(f"\n📊 Final Dataset:")
    print(f"   Total: {len(df):,} samples")
    print(f"   Malware: {malware_count:,} ({ratio:.4f})")
    print(f"   Benign: {len(df) - malware_count:,} ({1-ratio:.4f})")
    
    elapsed = time.time() - start
    print(f"\n⏱️ Total time: {elapsed/60:.1f} minutes")
    print(f"🎉 SUCCESS!")


if __name__ == "__main__":
    main()
