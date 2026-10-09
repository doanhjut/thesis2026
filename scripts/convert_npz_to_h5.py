
import numpy as np
import h5py
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
npz_path = str(_ROOT / "data" / "archives" / "train-features.npz")
h5_path = str(_ROOT / "data" / "archives" / "train_features.h5")
chunk_size = 10000

print("Converting NPZ to HDF5...")
print("This is ONE-TIME process, next time will be instant!")

with np.load(npz_path, mmap_mode='r') as data:
    X = data['arr_0']
    y = data['arr_1']
    
    total = X.shape[0]
    n_features = X.shape[1]
    
    print(f"Total: {total:,} samples, {n_features} features")
    
    with h5py.File(h5_path, 'w') as hf:
        X_dset = hf.create_dataset('X', shape=X.shape, dtype='float32', 
                                   chunks=(chunk_size, n_features))
        y_dset = hf.create_dataset('y', shape=y.shape, dtype='int8',
                                   chunks=(chunk_size,))
        
        for i in range(0, total, chunk_size):
            end = min(i + chunk_size, total)
            X_dset[i:end] = X[i:end]
            y_dset[i:end] = y[i:end]
            if i % 100000 == 0:
                print(f"  Progress: {i:,}/{total:,}")
        
print("Done! Now you can sample from HDF5 file quickly")
