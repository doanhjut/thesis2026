import pandas as pd
import lightgbm as lgb
from pathlib import Path
import gc
import psutil
import numpy as np

# ============================
# CONFIG
# ============================
REPO_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = REPO_ROOT / "data" / "processed" / "validation_dataset_small.csv"
MODEL_PATH = REPO_ROOT / "models" / "model_lightgbm.pkl"
REPORT_PATH = REPO_ROOT / "docs" / "model_report.txt"

def print_memory_usage():
    """In ra mức sử dụng RAM hiện tại"""
    process = psutil.Process()
    mem_info = process.memory_info()
    mem_gb = mem_info.rss / 1024**3
    print(f"💾 RAM usage: {mem_gb:.2f} GB")

def train_lightgbm_memory_efficient():
    """
    CHIẾN LƯỢC TỐI ƯU:
    1. Đọc data theo chunks nhưng GIỮ TOÀN BỘ trong memory (vì 32GB đủ)
    2. Train 1 lần duy nhất trên toàn bộ dataset
    3. Sử dụng các tính năng của LightGBM để tiết kiệm RAM
    """
    print("=" * 80)
    print("LIGHTGBM TRAINING - TỐI ƯU CHO RAM 32GB")
    print("=" * 80)
    
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {CSV_PATH}")
    
    print_memory_usage()
    
    # ============================================
    # BƯỚC 1: ĐỌC DATA THEO CHUNKS (TIẾT KIỆM RAM)
    # ============================================
    print("\n[BƯỚC 1] Đọc data theo chunks...")
    
    chunks = []
    chunk_size = 100_000  # Đọc mỗi lần 100k rows
    total_rows = 0
    
    for i, chunk in enumerate(pd.read_csv(CSV_PATH, chunksize=chunk_size), 1):
        # Xóa cột sha256 ngay (tiết kiệm RAM)
        if "sha256" in chunk.columns:
            chunk = chunk.drop(columns=["sha256"])
        
        # Convert sang int8/int16 để tiết kiệm RAM (nếu có thể)
        for col in chunk.select_dtypes(include=['int64', 'float64']).columns:
            if col != 'label':
                col_min, col_max = chunk[col].min(), chunk[col].max()
                if col_min >= 0 and col_max <= 255:
                    chunk[col] = chunk[col].astype('int8')
                elif col_min >= -128 and col_max <= 127:
                    chunk[col] = chunk[col].astype('int8')
                elif col_min >= 0 and col_max <= 65535:
                    chunk[col] = chunk[col].astype('int16')
        
        chunks.append(chunk)
        total_rows += len(chunk)
        
        if i % 5 == 0:
            print(f"  → Đã đọc {total_rows:,} rows...")
            print_memory_usage()
    
    print(f"\n✅ Đã đọc xong {total_rows:,} rows")
    print_memory_usage()
    
    # ============================================
    # BƯỚC 2: GỘP DATA VÀ CHIA TRAIN/VALID
    # ============================================
    print("\n[BƯỚC 2] Gộp data và chia train/valid...")
    
    df = pd.concat(chunks, ignore_index=True)
    del chunks
    gc.collect()
    
    print(f"  → DataFrame shape: {df.shape}")
    print_memory_usage()
    
    # Shuffle data trước khi chia (QUAN TRỌNG!)
    print("\n  → Đang shuffle data...")
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    
    # Chia train/valid
    train_size = int(len(df) * 0.8)
    df_train = df.iloc[:train_size]
    df_valid = df.iloc[train_size:]
    
    print(f"\n  → Train: {len(df_train):,} rows ({len(df_train[df_train['label']==1]):,} malware)")
    print(f"  → Valid: {len(df_valid):,} rows ({len(df_valid[df_valid['label']==1]):,} malware)")
    
    del df
    gc.collect()
    print_memory_usage()
    
    # ============================================
    # BƯỚC 3: CHUẨN BỊ DATASET
    # ============================================
    print("\n[BƯỚC 3] Tạo LightGBM Dataset...")
    
    X_train = df_train.drop(columns=['label'])
    y_train = df_train['label']
    X_valid = df_valid.drop(columns=['label'])
    y_valid = df_valid['label']
    
    del df_train, df_valid
    gc.collect()
    
    # Tạo Dataset với các tùy chọn tiết kiệm RAM
    train_data = lgb.Dataset(
        X_train, 
        label=y_train,
        free_raw_data=False  # Giữ data để có thể sử dụng lại
    )
    
    valid_data = lgb.Dataset(
        X_valid, 
        label=y_valid,
        reference=train_data,
        free_raw_data=False
    )
    
    print("✅ Dataset đã sẵn sàng")
    print_memory_usage()
    
    # ============================================
    # BƯỚC 4: TRAINING
    # ============================================
    print("\n[BƯỚC 4] Bắt đầu training...")
    print("=" * 80)
    
    params = {
        "objective": "binary",
        "metric": ["auc", "binary_logloss"],
        "boosting_type": "gbdt",
        "learning_rate": 0.05,
        "num_leaves": 255,
        "max_depth": -1,
        "min_data_in_leaf": 100,
        "feature_fraction": 0.8,
        "bagging_fraction": 0.8,
        "bagging_freq": 5,
        "lambda_l1": 0.1,
        "lambda_l2": 0.1,
        "min_gain_to_split": 0.01,
        "verbose": -1,
        "seed": 42,
        "n_jobs": -1,
        "max_bin": 255,  # Giảm để tiết kiệm RAM
    }
    
    # Callbacks
    callbacks = [
        lgb.early_stopping(stopping_rounds=100, verbose=True),
        lgb.log_evaluation(period=50)
    ]
    
    # Train model
    model = lgb.train(
        params,
        train_data,
        num_boost_round=5000,
        valid_sets=[train_data, valid_data],
        valid_names=['train', 'valid'],
        callbacks=callbacks
    )
    
    print("\n" + "=" * 80)
    print("✅ TRAINING HOÀN TẤT!")
    print("=" * 80)
    
    # ============================================
    # BƯỚC 5: ĐÁNH GIÁ VÀ LƯU MODEL
    # ============================================
    print("\n[BƯỚC 5] Đánh giá model...")
    
    best_iter = model.best_iteration
    train_auc = model.best_score['train']['auc']
    valid_auc = model.best_score['valid']['auc']
    train_logloss = model.best_score['train']['binary_logloss']
    valid_logloss = model.best_score['valid']['binary_logloss']
    
    print(f"\n📊 KẾT QUẢ:")
    print(f"  Best iteration: {best_iter}")
    print(f"  Train AUC     : {train_auc:.6f}")
    print(f"  Valid AUC     : {valid_auc:.6f}")
    print(f"  Train LogLoss : {train_logloss:.6f}")
    print(f"  Valid LogLoss : {valid_logloss:.6f}")
    
    # Dự đoán trên validation để kiểm tra
    y_pred = model.predict(X_valid, num_iteration=best_iter)
    
    print(f"\n📈 Phân bố dự đoán:")
    print(f"  Min  : {y_pred.min():.6f}")
    print(f"  Max  : {y_pred.max():.6f}")
    print(f"  Mean : {y_pred.mean():.6f}")
    print(f"  Std  : {y_pred.std():.6f}")
    
    # Feature importance
    print(f"\n🔝 Top 20 features quan trọng nhất:")
    importance = model.feature_importance(importance_type='gain')
    feature_names = model.feature_name()
    
    feat_imp = pd.DataFrame({
        'feature': feature_names,
        'importance': importance
    }).sort_values('importance', ascending=False)
    
    for i, row in feat_imp.head(20).iterrows():
        print(f"  {row.name+1:2d}. {row['feature']:30s}: {row['importance']:,.0f}")
    
    # Lưu model
    print(f"\n💾 Đang lưu model...")
    model.save_model(str(MODEL_PATH))
    print(f"✅ Đã lưu model → {MODEL_PATH}")
    
    # Ghi report
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("LIGHTGBM MALWARE DETECTION - TRAINING REPORT\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Dataset         : {CSV_PATH.name}\n")
        f.write(f"Total samples   : {total_rows:,}\n")
        f.write(f"Train samples   : {train_size:,} (80%)\n")
        f.write(f"Valid samples   : {total_rows - train_size:,} (20%)\n")
        f.write(f"Best iteration  : {best_iter}\n")
        f.write(f"Train AUC       : {train_auc:.6f}\n")
        f.write(f"Valid AUC       : {valid_auc:.6f}\n")
        f.write(f"Train LogLoss   : {train_logloss:.6f}\n")
        f.write(f"Valid LogLoss   : {valid_logloss:.6f}\n")
        f.write(f"\nTop 20 Important Features:\n")
        f.write("-" * 80 + "\n")
        for i, row in feat_imp.head(20).iterrows():
            f.write(f"{row.name+1:3d}. {row['feature']:30s}: {row['importance']:,.0f}\n")
        f.write(f"\nModel saved at  : {MODEL_PATH}\n")
    
    print(f"✅ Đã ghi report → {REPORT_PATH}")
    print_memory_usage()
    
    print("\n" + "=" * 80)
    print("🎉 HOÀN TẤT! MODEL ĐÃ SẴN SÀNG!")
    print("=" * 80)
    
    return model

if __name__ == "__main__":
    model = train_lightgbm_memory_efficient()
