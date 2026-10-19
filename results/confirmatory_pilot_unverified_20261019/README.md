# Confirmatory pilot trên bộ dữ liệu chưa xác minh định danh

Gói này lưu kết quả đo ngày 19/10/2026 cho hai phần có thể chạy bằng dữ liệu hiện có: XAI-Guided Active Learning và đánh giá Fidelity/độ ổn định của TreeSHAP. Tất cả lượt kiểm chứng độc lập đều đã `passed`.

> **Phạm vi sử dụng:** đây là kết quả pilot nội bộ. File nguồn `data/processed/real_mini_dataset.csv` có SHA-256 `c733cc0c3e0950fa1d05d57d34c69d0a034383e0c1a2fde0e6878b9e2e8c3668`, gồm 2.000 hàng, 2.381 đặc trưng và nhãn 1.500/500. Môi trường này không có row-manifest nối từng hàng với SHA-256 tệp gốc. Vì vậy chưa được mô tả các số liệu dưới đây là bằng chứng cuối cùng trên ransomware, zero-day, family-held-out hoặc temporal holdout.

## 1. XAI-Guided Active Learning

Thiết kế gồm 5 outer folds; trong phần develop của mỗi fold tách riêng validation; 5 seed AL; 200 nhãn ban đầu; 10 vòng, mỗi vòng 100 nhãn. Mỗi phương pháp dùng cùng initial set theo cặp fold/seed. Test không tham gia chọn mẫu, đặt mục tiêu, chọn ngưỡng hoặc dừng. Đơn vị lặp độc lập khi tổng hợp là outer fold: năm seed trong một fold được lấy trung bình trước.

Pipeline đã replay đủ 1.375 checkpoint, 1.100.000 bản ghi dự đoán và 125.000 bản ghi truy vấn. Cả 5/5 fold đều qua kiểm chứng.

| Phương pháp | ROC-AULC | AP-AULC | Nhãn đạt mục tiêu | Query (giây/10 vòng) | Model + query (giây) |
|---|---:|---:|---:|---:|---:|
| Random | 0,95600 | 0,91799 | 392 | 0,0197 | 4,3175 |
| Uncertainty | 0,96417 | 0,93318 | 324 | 0,0197 | 4,3217 |
| **U+H** | **0,96526** | **0,93544** | **316** | 0,2305 | 4,5050 |
| U+V | 0,96195 | 0,93111 | 328 | 0,2248 | 4,5176 |
| XAI_full | 0,96454 | 0,93432 | 340 | 0,2227 | 4,5386 |

`U+H` là biến thể có bằng chứng tốt nhất trong ablation này:

- So với Random, ROC-AULC tăng `+0,00926` và thắng 5/5 fold; cần ít hơn trung bình 76 nhãn (19,4%).
- So với Uncertainty, ROC-AULC tăng `+0,00109` và thắng 5/5 fold; cần ít hơn trung bình 8 nhãn. Mức tăng nhỏ, cần được trình bày cùng biến thiên fold.
- Query tăng khoảng 0,211 giây cho 10 vòng so với Uncertainty. Tổng thời gian model + query tăng khoảng 4,24%.
- `XAI_full` vượt Random (`+0,00854` ROC-AULC; ít hơn 52 nhãn), nhưng thấp hơn `U+H` `0,00072` ROC-AULC và dùng nhiều hơn 24 nhãn. Kết quả không hỗ trợ tuyên bố rằng ghép cả U, H và V với trọng số hiện tại là cấu hình tối ưu.

Điểm cuối tại 1.200 nhãn giống nhau giữa các phương pháp vì ngân sách này đã dùng hết train pool. Do đó hiệu quả AL phải được đọc từ AULC, đường học và ngân sách đạt mục tiêu, không đọc từ AUC cuối.

## 2. Fidelity và độ ổn định của TreeSHAP

Thiết kế gồm 5 folds × 5 model seeds × 2 baseline che đặc trưng (mean/median), với 20 random masks cho mỗi `k = 10, 25, 50`. Có 50/50 lượt replay qua kiểm chứng, mỗi lượt đối chiếu 63 nhóm mask và 25.200 bản ghi dự đoán.

| Baseline | k | Giảm AUC khi che top-SHAP | Giảm AUC với random mask | Chênh lệch |
|---|---:|---:|---:|---:|
| Mean | 10 | 0,04777 | 0,00017 | 0,04760 |
| Mean | 25 | 0,11261 | 0,00044 | 0,11217 |
| Mean | 50 | 0,20971 | 0,00099 | 0,20872 |
| Median | 10 | 0,04032 | 0,00004 | 0,04029 |
| Median | 25 | 0,12299 | 0,00019 | 0,12280 |
| Median | 50 | 0,26834 | 0,00043 | 0,26791 |

Thứ hạng SHAP ổn định hơn khi chỉ đổi seed trong cùng fold: Spearman toàn cục `0,614`, Jaccard top-10 `0,681`. Khi đổi cả fold, hai giá trị giảm còn `0,540` và `0,414`. Kết quả hỗ trợ faithfulness tương đối của thứ hạng TreeSHAP đối với model và cho thấy giải thích nhạy với mẫu dữ liệu.

OFS không được tổng hợp (`null`) vì chưa có quy tắc chuẩn hóa và trọng số trên cùng thang đo được kiểm định. Các thành phần Faithfulness/Consistency/Contrastive được giữ riêng để tránh tạo một điểm tổng hợp tùy ý.

## 3. Kết luận được phép sử dụng

- Trên pilot row-stratified này, các chiến lược có định hướng vượt Random ở vùng ngân sách thấp và trung bình.
- Thành phần entropy SHAP `H` bổ sung cho Uncertainty trong biến thể `U+H`, với hiệu ứng ROC-AULC nhỏ nhưng cùng chiều ở 5/5 fold.
- TreeSHAP xếp hạng các đặc trưng có ảnh hưởng dự đoán lớn hơn rõ rệt so với random mask, với cả baseline mean và median.
- Chi phí TreeSHAP trong thí nghiệm AL nhỏ so với thời gian huấn luyện model ở quy mô 2.000 mẫu, nhưng con số này chưa đại diện cho corpus lớn hoặc chi phí analyst.

Các kết luận sau chưa được phép rút ra từ gói này:

- Không xác nhận hiệu quả trên ransomware, zero-day, family-held-out hoặc temporal holdout.
- Không xác nhận PID/fusion làm giảm FPR, vì chưa có chuỗi hành vi động thực được nối với cùng mẫu tĩnh.
- Không xác nhận `XAI_full` là cấu hình AL tốt nhất.
- Deletion trong không gian đặc trưng EMBER không chứng minh quan hệ nhân quả và có thể tạo tổ hợp đặc trưng ngoài phân phối.

## 4. Lệnh đã chạy

```bash
.venv/bin/python scripts/run_experiments.py confirmatory-al \
  --data data/processed/real_mini_dataset.csv \
  --output outputs/confirmatory_pilot_unverified_al_20261019 \
  --folds 5 --seeds 11 22 33 44 55 \
  --initial-labels 200 --rounds 10 --batch-size 100 \
  --trees 60 --threads 2 --target-tpr 0.95 \
  --target-excess-auc-fraction 0.95

.venv/bin/python scripts/run_experiments.py confirmatory-fidelity \
  --data data/processed/real_mini_dataset.csv \
  --split-dir outputs/confirmatory_pilot_unverified_al_20261019/fold_manifests \
  --output outputs/confirmatory_pilot_unverified_fidelity_20261019 \
  --seeds 41 42 43 44 45 --baselines mean median \
  --k 10 25 50 --random-masks 20 --bootstrap 500 \
  --trees 100 --threads 2 --max-test-rows 1000 \
  --feature-fraction 0.8 --bagging-fraction 0.8
```

Các run được tạo từ commit `dbcdb471e15a3b631c916ad389b1beb371a33afc` với working tree sạch. Bảng gốc đủ để tái tính kết luận nằm trong `al/` và `fidelity/`; checkpoint/model lớn được giữ ngoài Git tại `outputs/`.
