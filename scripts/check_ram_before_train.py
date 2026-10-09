import psutil
import pandas as pd
from pathlib import Path

CSV_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "validation_dataset_small.csv"

def check_system_resources():
    """Kiểm tra RAM và ước lượng khả năng train"""
    print("=" * 80)
    print("KIỂM TRA HỆ THỐNG TRƯỚC KHI TRAIN")
    print("=" * 80)
    
    # Thông tin RAM
    mem = psutil.virtual_memory()
    print(f"\n📊 THÔNG TIN RAM:")
    print(f"  Tổng RAM      : {mem.total / 1024**3:.2f} GB")
    print(f"  Đang dùng     : {mem.used / 1024**3:.2f} GB ({mem.percent:.1f}%)")
    print(f"  Còn trống     : {mem.available / 1024**3:.2f} GB")
    
    # Thông tin CPU
    print(f"\n💻 THÔNG TIN CPU:")
    print(f"  CPU cores     : {psutil.cpu_count(logical=False)} physical")
    print(f"  CPU threads   : {psutil.cpu_count(logical=True)} logical")
    
    # Phân tích file CSV
    if CSV_PATH.exists():
        print(f"\n📁 PHÂN TÍCH FILE DATA:")
        print(f"  File path     : {CSV_PATH}")
        
        # Đọc sample để ước lượng
        print("  Đang đọc sample...")
        df_sample = pd.read_csv(CSV_PATH, nrows=1000)
        
        # Đếm tổng rows
        total_rows = sum(1 for _ in open(CSV_PATH, "r", encoding="utf-8")) - 1
        
        # Ước lượng kích thước
        n_features = len(df_sample.columns) - 1  # Trừ cột label/sha256
        
        print(f"  Số rows       : {total_rows:,}")
        print(f"  Số features   : {n_features:,}")
        
        # Ước lượng RAM cần thiết
        bytes_per_value = 4  # int32 default
        raw_size_gb = (total_rows * n_features * bytes_per_value) / 1024**3
        
        print(f"\n🧮 ƯỚC LƯỢNG RAM CẦN THIẾT:")
        print(f"  Raw data (int32)           : ~{raw_size_gb:.2f} GB")
        print(f"  Sau optimize dtype (int8)  : ~{raw_size_gb/3:.2f} GB")
        print(f"  LightGBM Dataset overhead  : ~{raw_size_gb/3 * 0.5:.2f} GB")
        print(f"  Python overhead            : ~{2:.2f} GB")
        print(f"  {'─' * 50}")
        
        estimated_total = (raw_size_gb/3) + (raw_size_gb/3 * 0.5) + 2
        print(f"  TỔNG ƯỚC LƯỢNG            : ~{estimated_total:.2f} GB")
        
        # Đưa ra khuyến nghị
        print(f"\n💡 KHUYẾN NGHỊ:")
        
        available_for_train = mem.available / 1024**3 - 2  # Giữ lại 2GB cho OS
        
        if available_for_train >= estimated_total * 1.5:
            print(f"  ✅ RAM còn trống ({available_for_train:.1f} GB) >> RAM cần ({estimated_total:.1f} GB)")
            print(f"  ✅ HOÀN TOÀN ĐỦ! Sử dụng PHƯƠNG ÁN 1 (train_lightgbm_optimized.py)")
            print(f"  ✅ Dự kiến AUC: 0.95-0.99")
            return "PA1"
            
        elif available_for_train >= estimated_total:
            print(f"  ⚠️  RAM còn trống ({available_for_train:.1f} GB) ≈ RAM cần ({estimated_total:.1f} GB)")
            print(f"  ⚠️  CÓ THỂ ĐỦ nhưng hơi sát. Đóng các app khác trước khi train")
            print(f"  ✅ Thử PHƯƠNG ÁN 1 trước")
            print(f"  ✅ Nếu bị Out of Memory → Dùng PHƯƠNG ÁN 2")
            return "PA1_RISKY"
            
        elif available_for_train >= estimated_total * 0.5:
            print(f"  ❌ RAM còn trống ({available_for_train:.1f} GB) < RAM cần ({estimated_total:.1f} GB)")
            print(f"  ❌ KHÔNG ĐỦ cho load toàn bộ data")
            print(f"  ✅ SỬ DỤNG PHƯƠNG ÁN 2 (train_lightgbm_ultra_low_ram.py)")
            print(f"  ✅ Stratified sampling 500k rows → RAM cần ~{estimated_total/2:.1f} GB")
            print(f"  ✅ Dự kiến AUC: 0.92-0.96")
            return "PA2"
            
        else:
            print(f"  ❌❌ RAM còn trống ({available_for_train:.1f} GB) << RAM cần ({estimated_total:.1f} GB)")
            print(f"  ❌ RAM QUÁ THẤP")
            print(f"  ⚠️  CẦN NÂNG CẤP RAM hoặc dùng cloud (Colab, Kaggle)")
            print(f"  ⚠️  Hoặc giảm dataset xuống còn 500k rows")
            return "INSUFFICIENT"
    
    else:
        print(f"\n❌ Không tìm thấy file: {CSV_PATH}")
        return "NO_FILE"
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    recommendation = check_system_resources()
    
    print(f"\n\n{'=' * 80}")
    print("HƯỚNG DẪN TIẾP THEO:")
    print("=" * 80)
    
    if recommendation == "PA1":
        print("""
✅ CHẠY PHƯƠNG ÁN 1:

1. Đóng tất cả ứng dụng đang chạy (Chrome, etc.)
2. Chạy: python train_lightgbm_optimized.py
3. Đợi ~10-15 phút
4. Kiểm tra kết quả: Valid AUC phải > 0.90
        """)
    
    elif recommendation == "PA1_RISKY":
        print("""
⚠️  THỬ PHƯƠNG ÁN 1, DỰ PHÒNG PHƯƠNG ÁN 2:

1. Đóng TẤT CẢ ứng dụng khác
2. Restart máy để clear RAM
3. Chạy: python train_lightgbm_optimized.py
4. Nếu bị "MemoryError" → Dùng train_lightgbm_ultra_low_ram.py
        """)
    
    elif recommendation == "PA2":
        print("""
✅ CHẠY PHƯƠNG ÁN 2:

1. Đóng các ứng dụng tốn RAM
2. Chạy: python train_lightgbm_ultra_low_ram.py
3. Đợi ~15-20 phút
4. Kiểm tra kết quả: Valid AUC phải > 0.85
        """)
    
    elif recommendation == "INSUFFICIENT":
        print("""
❌ RAM KHÔNG ĐỦ - GIẢI PHÁP:

1. Nâng cấp RAM lên 32GB hoặc 64GB
2. Sử dụng Google Colab (FREE 12GB RAM):
   - Upload file lên Google Drive
   - Chạy code trên Colab
3. Sử dụng Kaggle Notebooks (FREE 16GB RAM)
4. Giảm dataset xuống 500k rows
        """)
    
    print("=" * 80)
