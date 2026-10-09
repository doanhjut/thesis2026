# ============================================================================
# HƯỚNG DẪN: ĐÁNH GIÁ CROSS-DATASET (SOREL → EMBER)
# ============================================================================

## 🎯 MỤC ĐÍCH
Đánh giá khả năng generalization của model LightGBM được train trên SOREL-20M 
khi test trên EMBER 2018 dataset (cross-dataset evaluation)

## 📋 CÁC BƯỚC ĐÃ HOÀN THÀNH

### ✅ Bước 1: Sửa lỗi compatibility
- **Vấn đề**: Lỗi sklearn FeatureHasher với phiên bản mới
- **Giải pháp**: Đã sửa file `ember/features.py` dòng 192
- **File đã sửa**: `d:\Code\Luanvan\ember_test\ember\ember\features.py`

### ✅ Bước 2: Vectorize EMBER test data
- **Script**: `vectorize_test_data.py`
- **Kết quả**: Đã tạo `X_test.dat` và `y_test.dat` trong `ember2018/`
- **Thời gian**: ~6 phút (800k train + 200k test samples)

### ✅ Bước 3: Hoàn thiện script đánh giá
- **Script**: `ember_comparison.py`
- **Chức năng**: 
  - Load model SOREL và data EMBER
  - Prediction và evaluation
  - Phân tích generalization
  - Tạo báo cáo chi tiết

## 🚀 CHẠY ĐÁNH GIÁ

### Bước tiếp theo - Chạy script đánh giá:

```powershell
python ember_test\ember\ember_comparison.py
```

### Script này sẽ:
1. ✅ Load model SOREL (`ransomware_lgbm_1M_final.txt`)
2. ✅ Load EMBER 2018 test set (200k samples)
3. ✅ Kiểm tra feature compatibility (2381 features)
4. ✅ Dự đoán trên EMBER test set
5. ✅ Tính toán metrics:
   - Accuracy, F1-Score, AUC
   - Confusion Matrix (TP, TN, FP, FN)
   - True Positive Rate, False Positive Rate, Precision
6. ✅ Phân tích generalization:
   - So sánh SOREL validation AUC vs EMBER test AUC
   - Tính Generalization Score
7. ✅ Phân tích chi tiết:
   - False Positive Analysis
   - False Negative Analysis
8. ✅ Lưu báo cáo: `cross_dataset_evaluation.txt`

## 📊 KẾT QUẢ MONG ĐỢI

### Metrics quan trọng:
- **AUC**: Càng gần 0.99 càng tốt
- **Generalization Score**: 
  - ≥98%: EXCELLENT
  - ≥95%: GOOD
  - ≥90%: ACCEPTABLE
  - <90%: POOR (overfitting)
- **False Positive Rate**: <5% là tốt
- **False Negative Rate**: <5% là tốt

### Ví dụ output:
```
📊 CROSS-DATASET EVALUATION RESULTS
================================================================================
1️⃣ Overall Performance:
   Accuracy: 0.985432 (98.54%)
   F1-Score: 0.987123
   AUC:      0.992345

2️⃣ Confusion Matrix:
   True Negatives:  95,234
   False Positives: 1,234
   False Negatives: 876
   True Positives:  102,656

🎯 Generalization Score: 99.35%
   ✅ EXCELLENT generalization!
```

## 📁 CẤU TRÚC FILE

```
d:\Code\Luanvan\
├── ransomware_lgbm_1M_final.txt          # Model SOREL
├── ember_test\
│   ├── ember\
│   │   ├── ember_comparison.py           # Script đánh giá chính ⭐
│   │   ├── vectorize_test_data.py        # Script vectorize (đã chạy)
│   │   └── ember\
│   │       └── features.py               # Đã sửa lỗi sklearn
│   └── ember2018\
│       ├── X_test.dat                    # ✅ Đã tạo
│       ├── y_test.dat                    # ✅ Đã tạo
│       ├── X_train.dat
│       ├── y_train.dat
│       └── test_features.jsonl
└── cross_dataset_evaluation.txt          # Báo cáo kết quả (sẽ tạo)
```

## 🔧 TROUBLESHOOTING

### Nếu gặp lỗi "File not found":
- Kiểm tra file model: `ransomware_lgbm_1M_final.txt` có trong `d:\Code\Luanvan\`
- Kiểm tra đường dẫn EMBER_DATA_DIR trong `ember_comparison.py`

### Nếu gặp lỗi "Feature mismatch":
- SOREL model cần 2381 features (EMBER-v2)
- EMBER dataset cũng có 2381 features
- Nếu khác → kiểm tra lại model

### Nếu gặp lỗi Memory:
- EMBER test set có 200k samples × 2381 features
- Cần ~4GB RAM
- Nếu không đủ → giảm số samples trong script

## 📝 GHI CHÚ

### Về SOREL validation AUC:
- Trong script có dòng: `sorel_val_auc = 0.998867`
- Đây là giá trị từ kết quả training của bạn
- **Nếu khác**, hãy sửa lại cho đúng với kết quả training thực tế

### Về threshold:
- Hiện tại dùng threshold = 0.5
- Có thể điều chỉnh để tối ưu FPR/FNR
- Ví dụ: threshold = 0.7 → giảm FP nhưng tăng FN

## 🎓 Ý NGHĨA CROSS-DATASET EVALUATION

### Tại sao quan trọng?
1. **Kiểm tra overfitting**: Model có học "quá khớp" với SOREL không?
2. **Đánh giá generalization**: Model có hoạt động tốt trên data khác không?
3. **Độ tin cậy**: Model có thể dùng trong thực tế không?

### Kết quả tốt nghĩa là gì?
- Model học được **đặc trưng chung** của malware
- Không phụ thuộc vào đặc điểm riêng của SOREL dataset
- Có thể áp dụng cho nhiều loại malware khác nhau

### Nếu kết quả kém?
- Model có thể đang overfitting
- Cần retrain với data đa dạng hơn
- Hoặc cần feature engineering tốt hơn

## ✅ CHECKLIST

- [x] Sửa lỗi sklearn FeatureHasher
- [x] Vectorize EMBER test data
- [x] Hoàn thiện script ember_comparison.py
- [ ] **Chạy ember_comparison.py** ← BẠN Ở ĐÂY
- [ ] Xem kết quả và phân tích
- [ ] Đọc báo cáo chi tiết trong `cross_dataset_evaluation.txt`

## 🚀 LỆNH CHẠY

```powershell
# Chạy từ thư mục d:\Code\Luanvan
python ember_test\ember\ember_comparison.py
```

Chúc may mắn! 🍀
