#!/usr/bin/env python3
"""
================================================================================
extract_real_mini_data.py  -  Trich xuat mini dataset THAT tu tap du lieu goc
================================================================================
Muc dich:
    Doc tap du lieu EMBER goc (2381 dac trung) va trich xuat mot tap con
    (subset) 2000 mau de chay demo bao ve luan van.

Ho tro 2 dinh dang nguon:
    (A) File .npz  (vd: test-features.npz)  -> tap test held-out THAT, khop model.
    (B) File .csv  (vd: train_small.csv)    -> phuong an du phong.

Yeu cau lay mau:
    - Giu nguyen ty le bat can bang: 75% Benign (nhan 0) + 25% Ransomware (nhan 1)
    - Lay dung 1500 mau nhan 0 va 500 mau nhan 1
    - Co dinh random_state=42 de tai lap ket qua

KY THUAT TOI UU BO NHO (quan trong):
    Tap du lieu goc rat lon (test-features.npz: 4.2 trieu dong x 2381 cot
    ~ 40GB khi giai nen; CSV co the >1 trieu dong). KHONG THE nap toan bo vao RAM.
    Do do script dung 2 chien luoc doc-mot-luot:
      * NPZ: doc rieng mang NHAN (nhe ~16MB) de xac dinh vi tri tung lop, sau do
             STREAMING (giai nen tuan tu theo khoi) mang dac trung, chi giu lai
             dung 2000 dong da chon -> RAM chi ~vai chuc MB.
      * CSV: LUOT 1 doc rieng cot 'label'; LUOT 2 dung 'skiprows' chi doc 2000 dong.

Chay:   python extract_real_mini_data.py
Dau ra: real_mini_dataset.csv (2000 dong, cot dac trung '0'..'2380' + 'label')
================================================================================
"""

import sys
import time
import zipfile
from pathlib import Path
from datetime import datetime

import numpy as np
import numpy.lib.format as npformat
import pandas as pd

# ============================================================================
# CAU HINH
# ============================================================================
REPO_ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_DIR = REPO_ROOT / "data" / "archives"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
OUTPUT_FILE = PROCESSED_DIR / "real_mini_dataset.csv"

# Danh sach file nguon uu tien.
# KIEM CHUNG THUC TE voi model ransomware_lgbm_1M_final.txt:
#   - test-features.npz            -> KHOP model (AUC ~0.9982), la TEST SET held-out
#                                     => LY TUONG (khong data-leakage). Uu tien so 1.
#   - train_small.csv              -> KHOP model (AUC ~0.9998) nhung la TRAIN data.
#   - validation_dataset_small.csv -> KHONG khop feature-space (AUC ~0.495) => tranh.
CANDIDATE_FILES = [
    "test-features.npz",           # TEST SET that, khop model (uu tien)
    "test_small.csv",
    "test_dataset_small.csv",
    "train_small.csv",             # fallback: khop model nhung la train data
    "validation_dataset_small.csv" # fallback cuoi (co the khong khop model)
]

# Cac ten cot co the la nhan (dung cho nguon CSV)
POSSIBLE_LABEL_NAMES = ["label", "Label", "LABEL", "y", "target", "Target"]

# So mau can lay theo tung lop
N_BENIGN = 1500      # Nhan 0
N_RANSOMWARE = 500   # Nhan 1
RANDOM_STATE = 42

# So dong doc moi khoi khi streaming NPZ (can bang toc do vs bo nho)
NPZ_CHUNK_ROWS = 20_000


# ============================================================================
# TIM FILE NGUON
# ============================================================================

def find_source_file() -> Path:
    """Tim file du lieu nguon dau tien ton tai theo thu tu uu tien."""
    search_dirs = [ARCHIVE_DIR, PROCESSED_DIR, REPO_ROOT]
    for name in CANDIDATE_FILES:
        for folder in search_dirs:
            fpath = folder / name
            if fpath.exists():
                return fpath

    # Du phong: tim file .npz hoac .csv lon nhat
    candidates = []
    for folder in search_dirs:
        candidates.extend(folder.glob("*.npz"))
        candidates.extend(folder.glob("*.csv"))
    candidates = [
        f for f in candidates
        if f.name != OUTPUT_FILE.name and "mini" not in f.name.lower()
    ]
    if candidates:
        return max(candidates, key=lambda f: f.stat().st_size)

    raise FileNotFoundError(
        "Khong tim thay file du lieu nguon nao. "
        f"Hay dat 1 trong cac file sau vao thu muc: {CANDIDATE_FILES}"
    )


# ============================================================================
# LAY MAU PHAN TANG (dung chung cho ca NPZ va CSV)
# ============================================================================

def stratified_positions(labels: np.ndarray) -> set:
    """
    Tu mang nhan, chon vi tri (index 0-based) cho 1500 benign + 500 ransomware
    voi random_state=42. Tra ve set cac vi tri can giu.
    """
    labels = labels.astype(int)
    total = len(labels)
    n0 = int((labels == 0).sum())
    n1 = int((labels == 1).sum())

    print(f"\n  Total rows in source: {total:,}")
    print(f"    Benign (0):     {n0:,} ({n0/total*100:.1f}%)")
    print(f"    Ransomware (1): {n1:,} ({n1/total*100:.1f}%)")

    if n0 < N_BENIGN or n1 < N_RANSOMWARE:
        print(f"\n  [WARNING] Khong du du lieu de lay {N_BENIGN}+{N_RANSOMWARE}. "
              f"Se lay toi da giu ty le 75/25.")

    idx0 = np.where(labels == 0)[0]
    idx1 = np.where(labels == 1)[0]

    rng = np.random.default_rng(RANDOM_STATE)
    take0 = min(N_BENIGN, len(idx0))
    take1 = min(N_RANSOMWARE, len(idx1))
    sampled0 = rng.choice(idx0, size=take0, replace=False)
    sampled1 = rng.choice(idx1, size=take1, replace=False)

    keep = set(int(i) for i in np.concatenate([sampled0, sampled1]))
    print(f"\n  Sampling: {take0} benign + {take1} ransomware (random_state={RANDOM_STATE})")
    print(f"  Selected {len(keep)} rows total")
    return keep


def finalize_and_save(df_subset: pd.DataFrame, label_col: str, t0: float):
    """Shuffle, xac minh phan phoi, luu CSV va in tong ket."""
    df_subset = df_subset.sample(frac=1, random_state=RANDOM_STATE).reset_index(drop=True)

    counts = df_subset[label_col].astype(int).value_counts().sort_index()
    print(f"\n  === FINAL SUBSET DISTRIBUTION ===")
    for lbl, cnt in counts.items():
        name = "Benign" if lbl == 0 else "Ransomware"
        print(f"    Label {lbl} ({name}): {cnt} ({cnt/len(df_subset)*100:.1f}%)")

    df_subset.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    elapsed = time.time() - t0
    out_mb = OUTPUT_FILE.stat().st_size / (1024 * 1024)
    print(f"\n  [OK] Saved: {OUTPUT_FILE.name} ({out_mb:.2f} MB, {len(df_subset)} rows)")
    print(f"  Columns: {df_subset.shape[1]} (features + label)")
    print(f"  Elapsed: {elapsed:.1f}s")
    print(f"  Done: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 72)


# ============================================================================
# NHANH A: TRICH XUAT TU FILE .NPZ (STREAMING - AN TOAN BO NHO)
# ============================================================================

def _read_npy_header(fp):
    """
    Doc header cua stream .npy (da mo tu zip): tra ve (shape, fortran_order, dtype).
    Stream sau khi goi ham nay se nam ngay dau vung du lieu.
    """
    version = npformat.read_magic(fp)
    # Ho tro nhieu phien ban numpy: uu tien API cong khai neu co
    try:
        shape, fortran_order, dtype = npformat._read_array_header(fp, version)
    except AttributeError:
        # Phien ban cu: dung ham theo version
        if version == (1, 0):
            shape, fortran_order, dtype = npformat.read_array_header_1_0(fp)
        else:
            shape, fortran_order, dtype = npformat.read_array_header_2_0(fp)
    return shape, fortran_order, dtype


def _npz_entry_names(npz_path: Path):
    """Liet ke ten cac entry (*.npy) ben trong file .npz."""
    with zipfile.ZipFile(npz_path) as zf:
        return [n for n in zf.namelist() if n.endswith(".npy")]


def _load_labels_from_npz(npz_path: Path):
    """
    Nap RIENG mang nhan tu npz (nhe, ~vai chuc MB). Tra ve (labels, feat_name, label_name).
    Xac dinh: mang 1 chieu = nhan; mang 2 chieu = dac trung (chi doc header, khong nap).
    """
    entries = _npz_entry_names(npz_path)
    if len(entries) < 2:
        raise ValueError(f"NPZ can it nhat 2 mang (features + labels), tim thay: {entries}")

    label_name = None
    feat_name = None
    with zipfile.ZipFile(npz_path) as zf:
        for name in entries:
            with zf.open(name) as fp:
                shape, _, _ = _read_npy_header(fp)
            if len(shape) == 1:
                label_name = name
            elif len(shape) == 2:
                feat_name = name

    if label_name is None or feat_name is None:
        # Du phong: gia dinh arr_0=features, arr_1=labels theo thu tu
        feat_name = feat_name or entries[0]
        label_name = label_name or entries[-1]

    # Nap rieng mang nhan (lazy per-key: chi giai nen entry nay)
    with np.load(npz_path) as data:
        key = label_name[:-4] if label_name.endswith(".npy") else label_name
        labels = np.asarray(data[key]).ravel()

    return labels, feat_name, label_name


def extract_from_npz(source_file: Path, t0: float):
    """
    Trich xuat mini dataset tu .npz bang STREAMING an toan bo nho.
    Doc tuan tu mang dac trung theo khoi, chi giu lai 2000 dong da chon.
    """
    print(f"\n  Format: NPZ (streaming, memory-safe)")

    # --- Buoc 1: Nap rieng mang nhan (nhe) ---
    print(f"\n  [Pass 1/2] Loading labels array only (lightweight)...")
    try:
        labels, feat_name, label_name = _load_labels_from_npz(source_file)
    except Exception as e:
        print(f"  [ERROR] Khong the doc nhan tu NPZ: {e}")
        sys.exit(1)
    print(f"  Feature array: '{feat_name}'  |  Label array: '{label_name}'")

    # --- Buoc 2: Lay mau phan tang ---
    keep = stratified_positions(labels)
    max_idx = max(keep)  # co the dung stream som sau khi qua vi tri lon nhat

    # --- Buoc 3: STREAMING mang dac trung, chi lay dung cac dong da chon ---
    print(f"\n  [Pass 2/2] Streaming feature rows (decompress on-the-fly)...")
    print(f"             (Giai nen ~40GB tuan tu co the mat vai phut, vui long doi...)")

    collected_idx = []
    collected_rows = []

    with zipfile.ZipFile(source_file) as zf:
        with zf.open(feat_name) as fp:
            shape, fortran_order, dtype = _read_npy_header(fp)
            n_rows, n_cols = int(shape[0]), int(shape[1])

            if fortran_order:
                # Column-major khong the doc theo dong -> fallback nap toan bo
                print(f"  [WARNING] Mang luu Fortran-order, chuyen sang nap toan bo (ton RAM).")
                del fp
                _extract_npz_fullload(source_file, feat_name, keep, labels, t0)
                return

            row_bytes = n_cols * dtype.itemsize
            chunk_bytes = row_bytes * NPZ_CHUNK_ROWS

            pos = 0  # vi tri dong hien tai
            report_every = 200_000
            next_report = report_every

            while pos <= max_idx and pos < n_rows:
                raw = fp.read(chunk_bytes)
                if not raw:
                    break
                # So dong doc duoc trong khoi nay
                rows_in_chunk = len(raw) // row_bytes
                if rows_in_chunk == 0:
                    break
                usable = rows_in_chunk * row_bytes
                arr = np.frombuffer(raw[:usable], dtype=dtype).reshape(rows_in_chunk, n_cols)

                # Cac vi tri toan cuc thuoc khoi nay can giu
                chunk_range = range(pos, pos + rows_in_chunk)
                for local_i, global_i in enumerate(chunk_range):
                    if global_i in keep:
                        collected_idx.append(global_i)
                        collected_rows.append(arr[local_i].copy())

                pos += rows_in_chunk
                if pos >= next_report:
                    print(f"    ...scanned {pos:,}/{n_rows:,} rows, "
                          f"collected {len(collected_rows)}/{len(keep)}")
                    next_report += report_every

    print(f"  Collected {len(collected_rows)} feature rows.")

    # --- Buoc 4: Dung DataFrame (cot '0'..'2380' + 'label') va luu ---
    feat_matrix = np.vstack(collected_rows)
    feat_cols = [str(c) for c in range(feat_matrix.shape[1])]
    df_subset = pd.DataFrame(feat_matrix, columns=feat_cols)
    df_subset["label"] = labels[np.asarray(collected_idx)].astype(int)

    finalize_and_save(df_subset, "label", t0)


def _extract_npz_fullload(source_file: Path, feat_name: str, keep: set,
                          labels: np.ndarray, t0: float):
    """Du phong: nap toan bo mang dac trung (khi Fortran-order). Ton RAM."""
    key = feat_name[:-4] if feat_name.endswith(".npy") else feat_name
    with np.load(source_file) as data:
        X = np.asarray(data[key])
    idx = sorted(keep)
    feat_matrix = X[idx]
    del X
    feat_cols = [str(c) for c in range(feat_matrix.shape[1])]
    df_subset = pd.DataFrame(feat_matrix, columns=feat_cols)
    df_subset["label"] = labels[np.asarray(idx)].astype(int)
    finalize_and_save(df_subset, "label", t0)


# ============================================================================
# NHANH B: TRICH XUAT TU FILE .CSV (2 luot, an toan bo nho)
# ============================================================================

def detect_label_column(source_file: Path) -> str:
    """Phat hien cot nhan trong file CSV (ten pho bien / cot cuoi / cot dau)."""
    df_head = pd.read_csv(source_file, nrows=5)
    columns = list(df_head.columns)

    for name in POSSIBLE_LABEL_NAMES:
        if name in columns:
            return name

    last_col = columns[-1]
    if set(df_head[last_col].dropna().unique()).issubset({0, 1, 0.0, 1.0}):
        return last_col

    first_col = columns[0]
    if set(df_head[first_col].dropna().unique()).issubset({0, 1, 0.0, 1.0}):
        return first_col

    print(f"  [WARNING] Khong chac chan cot nhan, mac dinh dung cot cuoi: '{last_col}'")
    return last_col


def extract_from_csv(source_file: Path, t0: float):
    """Trich xuat mini dataset tu CSV bang ky thuat doc 2 luot."""
    print(f"\n  Format: CSV (2-pass, memory-safe)")

    try:
        label_col = detect_label_column(source_file)
        print(f"  Label column detected: '{label_col}'")
    except Exception as e:
        print(f"  [ERROR] Khong the phat hien cot nhan: {e}")
        sys.exit(1)

    # LUOT 1: chi doc cot nhan
    print(f"\n  [Pass 1/2] Reading label column only (memory-safe)...")
    print(f"             (File lon co the mat 30-90 giay, vui long doi...)")
    try:
        labels = pd.read_csv(source_file, usecols=[label_col])[label_col].to_numpy()
    except Exception as e:
        print(f"  [ERROR] Khong the doc cot nhan: {e}")
        sys.exit(1)

    keep = stratified_positions(labels)

    # LUOT 2: skiprows chi doc cac dong da chon
    print(f"\n  [Pass 2/2] Reading only {len(keep)} selected rows...")

    def skip_logic(row_num: int) -> bool:
        if row_num == 0:
            return False  # giu header
        return (row_num - 1) not in keep

    try:
        df_subset = pd.read_csv(source_file, skiprows=skip_logic)
    except Exception as e:
        print(f"  [ERROR] Loi khi doc cac dong da chon: {e}")
        print(f"  [INFO]  Thu phuong an du phong: doc chunk...")
        df_subset = _fallback_chunk_read(source_file, keep)

    finalize_and_save(df_subset, label_col, t0)


def _fallback_chunk_read(source_file: Path, keep_positions: set) -> pd.DataFrame:
    """Du phong: doc CSV theo chunk 100k dong khi skiprows gap loi."""
    collected = []
    current_pos = 0
    for chunk in pd.read_csv(source_file, chunksize=100_000):
        chunk_len = len(chunk)
        global_idx = np.arange(current_pos, current_pos + chunk_len)
        mask = np.array([gi in keep_positions for gi in global_idx])
        if mask.any():
            collected.append(chunk.iloc[mask])
        current_pos += chunk_len
    return pd.concat(collected, ignore_index=True)


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 72)
    print("  EXTRACT REAL MINI DATASET - EMBER Features (2381-dim)")
    print("=" * 72)
    t0 = time.time()

    try:
        source_file = find_source_file()
    except FileNotFoundError as e:
        print(f"  [ERROR] {e}")
        sys.exit(1)

    size_mb = source_file.stat().st_size / (1024 * 1024)
    print(f"\n  Source file: {source_file.name} ({size_mb:.1f} MB)")

    # Dispatch theo dinh dang
    if source_file.suffix.lower() == ".npz":
        extract_from_npz(source_file, t0)
    else:
        extract_from_csv(source_file, t0)


if __name__ == "__main__":
    main()
