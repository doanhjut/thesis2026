#!/usr/bin/env python3
"""
================================================================================
generate_mini_dataset.py  -  Sinh mini dataset PE features cho demo bao ve
================================================================================
Muc dich: Tao file mini_sorel_features.csv chua 2000 mau (1500 Benign + 500 Ransomware)
dua tren phan phoi chuan cua PE file thuc te tu SOREL-20M.

Phan phoi dac trung:
  - Benign:   SectionMaxEntropy ~ 4.5-6.0, SuspiciousAPI_Count thap (0-3)
  - Ransomware: SectionMaxEntropy ~ 7.5-7.9, SuspiciousAPI_Count cao (8-20)

Chay: python generate_mini_dataset.py
Dau ra: mini_sorel_features.csv (2000 dong)
================================================================================
"""

import hashlib
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime

# Seed de tai lap ket qua
np.random.seed(42)

# ============================================================================
# CAU HINH
# ============================================================================
OUTPUT_FILE = Path(__file__).resolve().parents[1] / "data" / "processed" / "mini_sorel_features.csv"
N_BENIGN = 1500
N_RANSOMWARE = 500
N_TOTAL = N_BENIGN + N_RANSOMWARE


def generate_md5_hash(index: int, label: int) -> str:
    """Tao md5 hash gia lap dua tren index va label."""
    seed_str = f"sample_{index}_label_{label}_defense_demo"
    return hashlib.md5(seed_str.encode()).hexdigest()


def generate_benign_features(n: int) -> pd.DataFrame:
    """
    Sinh dac trung PE cho mau Benign.
    Phan phoi dua tren thong ke thuc te tu SOREL-20M:
    - SizeOfCode: PE hop le thuong co code section lon (50KB - 500KB)
    - SectionMaxEntropy: Entropy thap (4.5 - 6.0) do code khong bi pack/encrypt
    - SizeOfUninitializedData: Thap (BSS section nho)
    - SuspiciousAPI_Count: Rat thap (0-3), it goi API dang ngo
    """
    rng = np.random.default_rng(42)

    # SizeOfCode: phan phoi lognormal, median ~100KB
    size_of_code = rng.lognormal(mean=11.5, sigma=0.8, size=n)
    size_of_code = np.clip(size_of_code, 1024, 2_000_000).astype(int)

    # SectionMaxEntropy: 4.5 - 6.0 (entropy thap, code binh thuong)
    section_max_entropy = rng.normal(loc=5.2, scale=0.4, size=n)
    section_max_entropy = np.clip(section_max_entropy, 3.5, 6.5)

    # SizeOfUninitializedData: thap (BSS section nho)
    size_uninit = rng.lognormal(mean=7.0, sigma=1.0, size=n)
    size_uninit = np.clip(size_uninit, 0, 100_000).astype(int)

    # SuspiciousAPI_Count: 0-3 (it API dang ngo)
    suspicious_api = rng.poisson(lam=1.2, size=n)
    suspicious_api = np.clip(suspicious_api, 0, 5)

    return pd.DataFrame({
        "SizeOfCode": size_of_code,
        "SectionMaxEntropy": np.round(section_max_entropy, 4),
        "SizeOfUninitializedData": size_uninit,
        "SuspiciousAPI_Count": suspicious_api,
    })


def generate_ransomware_features(n: int) -> pd.DataFrame:
    """
    Sinh dac trung PE cho mau Ransomware.
    Phan phoi dua tren thong ke thuc te:
    - SizeOfCode: Thuong nho hon (packed, 10KB - 200KB)
    - SectionMaxEntropy: CAO (7.5 - 7.9) do code bi encrypt/pack
    - SizeOfUninitializedData: Trung binh
    - SuspiciousAPI_Count: CAO (8-20) do goi nhieu API doc hai
      (CryptEncrypt, WriteFile, DeleteFileA, vssadmin, bcdedit...)
    """
    rng = np.random.default_rng(123)

    # SizeOfCode: phan phoi nho hon (packed binary)
    size_of_code = rng.lognormal(mean=10.2, sigma=0.9, size=n)
    size_of_code = np.clip(size_of_code, 2048, 500_000).astype(int)

    # SectionMaxEntropy: 7.5 - 7.9 (entropy CAO, dac trung cua packed/encrypted code)
    section_max_entropy = rng.normal(loc=7.72, scale=0.12, size=n)
    section_max_entropy = np.clip(section_max_entropy, 7.2, 7.99)

    # SizeOfUninitializedData: trung binh
    size_uninit = rng.lognormal(mean=8.5, sigma=1.2, size=n)
    size_uninit = np.clip(size_uninit, 0, 200_000).astype(int)

    # SuspiciousAPI_Count: 8-20 (goi nhieu API doc hai)
    suspicious_api = rng.poisson(lam=12, size=n)
    suspicious_api = np.clip(suspicious_api, 6, 25)

    return pd.DataFrame({
        "SizeOfCode": size_of_code,
        "SectionMaxEntropy": np.round(section_max_entropy, 4),
        "SizeOfUninitializedData": size_uninit,
        "SuspiciousAPI_Count": suspicious_api,
    })


def main():
    print("=" * 70)
    print("  GENERATE MINI DATASET - SOREL-20M PE Features")
    print("=" * 70)
    print(f"\n  Benign samples:     {N_BENIGN}")
    print(f"  Ransomware samples: {N_RANSOMWARE}")
    print(f"  Total:              {N_TOTAL}")
    print(f"  Output:             {OUTPUT_FILE}\n")

    # Sinh du lieu Benign
    print("  [1/3] Generating Benign PE features...")
    df_benign = generate_benign_features(N_BENIGN)
    df_benign["Label"] = 0

    # Sinh du lieu Ransomware
    print("  [2/3] Generating Ransomware PE features...")
    df_ransomware = generate_ransomware_features(N_RANSOMWARE)
    df_ransomware["Label"] = 1

    # Gop va shuffle
    print("  [3/3] Merging and shuffling...")
    df_all = pd.concat([df_benign, df_ransomware], ignore_index=True)

    # Tao md5_hash cho tung mau
    df_all["md5_hash"] = [
        generate_md5_hash(i, int(df_all.iloc[i]["Label"]))
        for i in range(len(df_all))
    ]

    # Sap xep lai cot theo yeu cau
    df_all = df_all[["md5_hash", "SizeOfCode", "SectionMaxEntropy",
                      "SizeOfUninitializedData", "SuspiciousAPI_Count", "Label"]]

    # Shuffle ngau nhien
    df_all = df_all.sample(frac=1, random_state=42).reset_index(drop=True)

    # Xuat CSV
    df_all.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    # Thong ke
    print("\n  === DATASET STATISTICS ===")
    print(f"  {'Feature':<28} {'Benign (mean)':>15} {'Ransomware (mean)':>18}")
    print(f"  {'-'*63}")
    for col in ["SizeOfCode", "SectionMaxEntropy", "SizeOfUninitializedData", "SuspiciousAPI_Count"]:
        b_mean = df_benign[col].mean()
        r_mean = df_ransomware[col].mean()
        print(f"  {col:<28} {b_mean:>15.2f} {r_mean:>18.2f}")

    print(f"\n  [OK] Saved: {OUTPUT_FILE} ({OUTPUT_FILE.stat().st_size / 1024:.1f} KB)")
    print(f"  Done: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


if __name__ == "__main__":
    main()
