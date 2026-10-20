# Kết quả xác nhận trên EMBER có định danh tĩnh

Gói này lưu kết quả đo ngày 19/10/2026 cho XAI-Guided Active Learning và đánh giá Fidelity/độ ổn định của TreeSHAP. Dữ liệu và manifest đã qua kiểm tra nhãn, SHA-256, định danh hàng và hash vector đặc trưng. Tất cả lượt replay đều `passed`.

## Dữ liệu và phạm vi kết luận

- Dataset: 2.000 mẫu, 2.381 đặc trưng; 1.500 benign và 500 malware.
- SHA-256 dataset: `69f0ae680846edd95458d1e7aaabe36f8866f4f22a6d11488b126ed026b28963`.
- SHA-256 manifest: `a2ca16402653e6cc51fdd7a4857d007faf86807b044d78654f180409c73565bb`.
- 2.000 `row_id`, `source_index` và SHA-256 mẫu đều duy nhất; không có vector đặc trưng trùng hoàn toàn.
- Thời gian `appeared` từ 11/2018 đến 12/2018; `avclass` có ở 498 mẫu.

Nhãn 1 của EMBER có nghĩa là malware nói chung. `avclass` là metadata họ yếu, không phải nhãn ransomware đã xác minh. Vì vậy gói này hỗ trợ kết luận về phân loại malware tĩnh trên mẫu EMBER đã định danh; không tự hỗ trợ kết luận ransomware-specific, family-held-out, temporal/zero-day hoặc PID.

## XAI-Guided Active Learning

Thiết kế gồm 5 outer folds, validation tách trong phần develop, 5 AL seeds, 200 nhãn ban đầu và 10 vòng × 100 nhãn. Mỗi phương pháp dùng cùng initial set theo fold/seed. Test không tham gia chọn mẫu, đặt target, chọn threshold hoặc dừng. Năm seed trong cùng fold được lấy trung bình trước khi tính hiệu ứng và độ bất định.

Pipeline đã replay đủ 1.375 checkpoint, 1.100.000 bản ghi dự đoán và 125.000 bản ghi truy vấn; 5/5 fold qua kiểm chứng.

| Phương pháp | ROC-AULC | AP-AULC | Nhãn đạt target | Query (giây/10 vòng) | Model + query (giây) |
|---|---:|---:|---:|---:|---:|
| Random | 0,928777 | 0,868350 | 584 | 0,0194 | 4,1947 |
| Uncertainty | 0,931272 | 0,881934 | 520 | 0,0191 | 4,1454 |
| **U+H** | **0,933026** | **0,883336** | 508 | 0,2459 | 4,4741 |
| U+V | 0,930377 | 0,880164 | **488** | 0,2298 | 4,3826 |
| XAI_full | 0,932202 | 0,881638 | 492 | 0,2358 | 4,3471 |

Kết quả ghép cặp theo outer fold:

- `U+H` so với Random: ROC-AULC `+0,004249`, AP-AULC `+0,014985`, thắng 5/5 fold; giảm trung bình 76 nhãn (13,0%).
- `U+H` so với Uncertainty: ROC-AULC `+0,001754`, AP-AULC `+0,001401`, thắng 4/5 fold; giảm trung bình 12 nhãn nhưng chỉ ít nhãn hơn ở 2/5 fold. Hiệu ứng nhỏ và ngân sách không ổn định giữa fold.
- `XAI_full` so với Random: ROC-AULC `+0,003425`, AP-AULC `+0,013287`, thắng 5/5 fold; giảm trung bình 92 nhãn (15,8%).
- `XAI_full` so với Uncertainty: ROC-AULC `+0,000931` và thắng 3/5 fold; AP-AULC `−0,000297`. Cấu hình đầy đủ không vượt baseline mạnh một cách nhất quán.

`U+H` là biến thể tốt nhất về ROC/AP-AULC; `U+V` cần ít nhãn nhất để đạt target; `XAI_full` đứng giữa hai mục tiêu. Đây là một đánh đổi quan sát được, không phải bằng chứng rằng thêm mọi tín hiệu XAI luôn tốt hơn.

Ở 1.200 nhãn, các phương pháp gặp cùng full-pool model nên điểm cuối giống nhau. Hiệu quả AL phải được đọc từ AULC, đường học và ngân sách đạt target.

### Điểm vận hành FPR thấp

Normalized AULC dọc theo ngân sách:

| Phương pháp | pAUC tại FPR≤5% | TPR tại cap FPR 1% | TPR tại cap FPR 5% |
|---|---:|---:|---:|
| Random | 0,804096 | 0,580620 | 0,731980 |
| Uncertainty | **0,826300** | **0,638180** | 0,769260 |
| U+H | 0,824774 | 0,636780 | 0,770620 |
| U+V | 0,825194 | 0,626260 | 0,768140 |
| XAI_full | 0,823525 | 0,631860 | **0,771460** |

So với Random, `U+H` tăng TPR-AULC `+0,05616` tại cap 1% và `+0,03864` tại cap 5%, cùng chiều ở 5/5 fold. So với Uncertainty, chênh lệch tương ứng là `−0,00140` và `+0,00136`; chưa có bằng chứng XAI giảm cảnh báo nhầm tốt hơn Uncertainty một cách ổn định.

Query của `U+H` tăng khoảng 0,227 giây cho 10 vòng so với Uncertainty; tổng model + query tăng khoảng 7,93%. Với `XAI_full`, tổng overhead tương ứng khoảng 4,86%. Đây là thời gian chấm pool/huấn luyện ở quy mô 2.000 mẫu, không phải latency phát hiện đầu cuối hoặc thời gian chuyên gia gán nhãn.

## Fidelity và độ ổn định TreeSHAP

Thiết kế gồm 5 folds × 5 model seeds × 2 masking baselines (mean/median), với 20 random masks cho mỗi `k = 10, 25, 50`. Có 50/50 lượt replay qua kiểm chứng; mỗi lượt đối chiếu 63 nhóm mask và 25.200 bản ghi dự đoán.

| Baseline | k | Giảm AUC top-SHAP | Giảm AUC random | Top-SHAP trừ random |
|---|---:|---:|---:|---:|
| Mean | 10 | 0,047817 | 0,000200 | 0,047617 |
| Mean | 25 | 0,135853 | 0,000530 | 0,135323 |
| Mean | 50 | 0,306729 | 0,000979 | 0,305750 |
| Median | 10 | 0,053483 | 0,000094 | 0,053388 |
| Median | 25 | 0,125180 | 0,000326 | 0,124854 |
| Median | 50 | 0,300777 | 0,000658 | 0,300119 |

Khi chỉ đổi model seed trong cùng fold, Spearman thứ hạng SHAP trung bình là `0,6144`, Jaccard top-10 `0,6221`, top-25 `0,5398` và top-50 `0,4901`. Khi đổi cả fold, các giá trị giảm còn `0,5512`, `0,4416`, `0,3073` và `0,3020`. Kết quả hỗ trợ faithfulness tương đối của thứ hạng TreeSHAP với model và cho thấy giải thích nhạy với phân hoạch dữ liệu.

OFS không được tổng hợp vì chưa có quy tắc chuẩn hóa và trọng số chung được kiểm định. Faithfulness, stability/consistency và contrastive separation cần được báo riêng.

Deletion được thực hiện trong không gian đặc trưng EMBER. Mean/median replacement có thể tạo vector ngoài phân phối và không chứng minh quan hệ nhân quả hoặc tính hợp lệ ở mức tệp PE thực thi.

## Kết luận được hỗ trợ

- Trên EMBER có định danh tĩnh, các chiến lược XAI-guided vượt Random về ROC/AP-AULC và hiệu quả vùng FPR thấp.
- `U+H` cho ROC/AP-AULC tốt nhất; lợi ích so với Uncertainty nhỏ và không đồng nhất trên mọi chỉ số.
- `XAI_full` giảm ngân sách trung bình so với Random và Uncertainty, nhưng không tốt nhất trên mọi metric.
- Top-SHAP gây suy giảm AUC lớn hơn random mask cùng ngân sách dưới cả baseline mean và median.
- Giải thích ổn định hơn trước thay đổi seed trong cùng fold so với thay đổi phân hoạch dữ liệu.

Chưa được dùng gói này để kết luận PID làm giảm FPR, hệ thống phát hiện ransomware/zero-day, hoặc toàn hệ thống đã sẵn sàng vận hành. PID vẫn cần behavior traces thực ghép cặp theo SHA-256.

## Lệnh đã chạy

```bash
.venv/bin/python scripts/run_experiments.py confirmatory-al \
  --data outputs/ember_identity_dataset/ember_mini_dataset.csv \
  --row-manifest outputs/ember_identity_dataset/ember_row_manifest.csv \
  --output outputs/ember_confirmatory_al_20261019 \
  --folds 5 --seeds 11 22 33 44 55 \
  --initial-labels 200 --rounds 10 --batch-size 100 \
  --trees 60 --threads 2 --target-tpr 0.95 \
  --target-excess-auc-fraction 0.95

.venv/bin/python scripts/run_experiments.py confirmatory-fidelity \
  --data outputs/ember_identity_dataset/ember_mini_dataset.csv \
  --row-manifest outputs/ember_identity_dataset/ember_row_manifest.csv \
  --split-dir outputs/ember_confirmatory_al_20261019/fold_manifests \
  --output outputs/ember_confirmatory_fidelity_20261019 \
  --seeds 41 42 43 44 45 --baselines mean median \
  --k 10 25 50 --random-masks 20 --bootstrap 500 \
  --trees 100 --threads 2 --max-test-rows 1000 \
  --feature-fraction 0.8 --bagging-fraction 0.8
```

Các run được tạo từ commit `fed4322f58f5bb55ec47833e857370d076592a32` với working tree sạch. Dữ liệu/manifest và checkpoint lớn được giữ ngoài Git; gói này lưu hash, audit, cấu hình, bảng đủ để tái tính kết luận và file verification.

Để kiểm tra tính toàn vẹn, chạy `sha256sum -c SHA256SUMS` ngay trong thư mục này. Các đường dẫn trong `SHA256SUMS` được tính tương đối theo gốc của gói kết quả.
