# Báo cáo trạng thái bằng chứng và mức sẵn sàng viết bài báo

**Ngày cập nhật:** 23/10/2026
**Nhánh mã nguồn:** `feat/reproducible-thesis-experiments`  
**Mục đích:** tổng hợp dữ liệu, thực nghiệm, nội dung đã khắc phục, nội dung chưa đáp ứng và phạm vi phát biểu phù hợp để chuyển sang viết paper.

---

## 1. Kết luận điều hành

Tới thời điểm hiện tại, nghiên cứu đã tiến xa hơn đáng kể so với bản được nhận xét ở seminar:

1. **Dữ liệu tĩnh EMBER đã được khôi phục định danh và kiểm tra provenance ở mức hàng.** Bộ dùng cho Active Learning và Fidelity có 2.000 mẫu, 2.381 đặc trưng, SHA-256 và manifest khóa bằng hash.
2. **XAI-Guided Active Learning đã có thực nghiệm xác nhận** trên 5 outer folds × 5 seeds, có Random và Uncertainty làm baseline, có ablation `U+H`, `U+V`, `XAI_full`, có AULC, ngân sách nhãn, low-FPR metrics và overhead.
3. **Fidelity đã được nâng từ một điểm OFS khó bảo vệ thành một giao thức có đối chứng:** deletion top-SHAP so với random cùng số chiều, hai baseline mean/median, nhiều fold/seed và kiểm tra độ ổn định thứ hạng.
4. **PID đã có run xác nhận trên MalBehavD-V1:** 1.922/1.923 mẫu có đủ metadata tĩnh và chuỗi API động; có bảy cấu hình Static, Dynamic, Average, Fixed, P, PI và PID, 5 outer folds, bootstrap ghép cặp và phép tắt riêng thành phần D.
5. **Pipeline và artifact đã có khả năng replay/verification.** Các bảng chính có thể truy ngược về cấu hình, prediction và hash.

Tuy nhiên, bằng chứng hiện tại **chưa đủ để viết một paper khẳng định hoàn chỉnh “multi-stage ransomware detection with PID”** vì:

- EMBER và MalBehavD-V1 đều có nhãn malware tổng quát, không phải ransomware ground truth đã xác minh.
- AL/Fidelity chạy trên EMBER, PID chạy trên MalBehavD-V1; chưa có một thí nghiệm end-to-end trên cùng cohort.
- Run xác nhận cho thấy Average đạt AUC/AP/Brier tốt nhất, Fixed đạt FPR thấp nhất; full PID không phải cấu hình tốt nhất.
- Thành phần D không làm thay đổi quyết định cuối trên 1.922 mẫu và không tạo hiệu ứng AUC/AP có khoảng tin cậy loại trừ 0.
- Chưa có gate + fusion + AL tích hợp, external/temporal validation và đo latency đầu cuối.

### Khuyến nghị phạm vi paper

**Phương án có thể viết ngay và bảo vệ tốt hơn:**

> **Explanation-Guided Active Learning with Robust TreeSHAP Validation for Static Windows Malware Detection**

Paper này dùng EMBER làm bằng chứng chính. Hai trục phương pháp là XAI-guided acquisition và đánh giá Fidelity/stability. PID chỉ xuất hiện ở phần thảo luận hoặc pilot bổ sung, không phải claim trung tâm.

**Phương án giữ đủ ba đóng góp và kiến trúc multi-stage:** run confirmatory PID đã hoàn tất, nhưng vẫn cần baseline learned-fusion, gate end-to-end và thí nghiệm tích hợp trước khi chốt manuscript mạnh. Vì D không tạo lợi ích đo được, nên đổi đóng góp từ “PID Fusion vượt trội” thành **event-indexed static–dynamic fusion with component ablation**, trong đó kết quả khoa học là luật đơn giản hơn đủ trong horizon hiện tại.

---

## 2. Thứ bậc bằng chứng cần dùng khi viết

| Mức | Nội dung | Cách dùng trong paper |
|---|---|---|
| **Xác nhận** | AL và Fidelity trên EMBER 2.000 mẫu; verification pass | Có thể dùng làm kết quả chính |
| **Xác nhận** | PID/fusion trên 1.922/1.923 mẫu MalBehavD-V1; verification pass | Dùng làm kết quả ablation chính, báo CI và giới hạn |
| **Pilot đo thật** | PID trên 199/200 mẫu MalBehavD-V1 | Chỉ dùng đối chiếu feasibility; đã được thay bởi run xác nhận |
| **Bằng chứng phụ** | Static gate đã đo trên dữ liệu tĩnh nhưng chưa có quyết định động cuối | Dùng mô tả thiết kế hoặc limitation |
| **Không dùng** | Artifact legacy nằm trực tiếp trong `results/`, pilot cũ không có identity, số demo/mô phỏng | Không đưa vào bảng, abstract hoặc kết luận |

Không trộn số giữa các mức trên. Một con số chỉ được gọi là “measured result” khi có đầu vào phù hợp, cấu hình, prediction và verification tương ứng.

---

## 3. Kiểm kê dữ liệu

### 3.1. EMBER 2018 có định danh — dùng cho AL và Fidelity

| Thuộc tính | Giá trị |
|---|---:|
| Số mẫu | 2.000 |
| Số đặc trưng | 2.381 |
| Benign | 1.500 |
| Malware | 500 |
| `row_id` duy nhất | 2.000 |
| `source_index` duy nhất | 2.000 |
| SHA-256 mẫu duy nhất | 2.000 |
| Vector đặc trưng trùng hoàn toàn | 0 |
| Khoảng thời gian `appeared` | 11/2018–12/2018 |
| Có `avclass` | 498 mẫu |

**Hash khóa dữ liệu:**

- Dataset SHA-256: `69f0ae680846edd95458d1e7aaabe36f8866f4f22a6d11488b126ed026b28963`
- Manifest SHA-256: `a2ca16402653e6cc51fdd7a4857d007faf86807b044d78654f180409c73565bb`

**Ý nghĩa nhãn:** `0 = EMBER benign`, `1 = EMBER malware`. `avclass` chỉ là metadata họ yếu; không phải nhãn ransomware đã xác minh.

**Điểm đã khắc phục:**

- Đã đối chiếu nhãn giữa dataset và manifest.
- Đã xác minh SHA-256 của vector float32 theo hàng.
- Đã loại nghi vấn trùng hàng chính xác.
- Test được tách khỏi query selection, target, threshold và model selection.
- Các split, seed và artifact được khóa.

**Giới hạn còn lại:**

- Random row folds không chứng minh family-held-out, temporal, zero-day hoặc cross-dataset generalization.
- Khoảng thời gian mẫu hẹp.
- Không có behavior trace nên EMBER không thể kiểm chứng PID.
- Không được dùng từ “ransomware detection” cho kết quả này nếu không bổ sung ground truth tương ứng.

Nguồn chuẩn: `results/confirmatory_20261019_ember_identity/`.

### 3.2. MalBehavD-V1 — dùng cho PID event-indexed

**Nguồn:** MalBehavD-V1, commit `6aac5027635ac3d2832d323a873fccd7cdd89a5e`.  
**CSV SHA-256:** `1e39c43a014e9b4ee56766ad6bb367ffe8ec4316eb0be75eb182c3b2d15f6364`.

| Thuộc tính | Giá trị |
|---|---:|
| Số dòng nguồn | 2.570 |
| Benign / malware nguồn | 1.285 / 1.285 |
| SHA-256 duy nhất | 2.543 |
| SHA-256 trùng | 26 |
| Xung đột nhãn trong SHA trùng | 0 |
| Điều kiện đủ cohort | Tối thiểu 20 API events |
| Cohort đủ điều kiện | 1.923 |
| Benign / malware trong cohort | 932 / 991 |
| Outer folds | 5, seed 2026 |

**Tín hiệu động:** chuỗi API call có thứ tự do benchmark công bố. Các mốc đánh giá là 5, 10, 15 và 20 sự kiện. Đây là **event count**, không phải thời gian theo giây.

**Tín hiệu tĩnh:** 199 thuộc tính cấu trúc từ `size`, `type_tag` và `pe_info` của metadata VirusTotal. Allow-list loại AV verdict, số detection, threat name, tag và filename để tránh dùng trực tiếp tín hiệu nhãn.

**An toàn dữ liệu:** collector chỉ gọi metadata `GET /api/v3/files/{sha256}`; không tải và không thực thi PE executable.

**Giới hạn dữ liệu:**

- Nhãn là benign/malware tổng quát.
- Benign và malware của bộ gốc đến từ các nguồn thu thập khác nhau, có nguy cơ source bias.
- Chuỗi có thứ tự nhưng không có wall-clock timestamp.
- Metadata VirusTotal có thể tạo missingness theo khả năng tồn tại bản ghi.

### 3.3. Pilot PID 200 mẫu

| Thuộc tính | Giá trị |
|---|---:|
| Cohort chọn trước | 200 |
| Có đủ hai kênh | 199 |
| Coverage | 99,5% |
| Benign / malware usable | 100 / 99 |
| Mẫu thiếu metadata | 1 malware |
| Event windows | 5 / 10 / 15 / 20 |

Pilot có verification pass và đủ dùng để chứng minh pipeline/ablation hoạt động. Quy mô này chưa đủ để xác nhận full PID hoặc ước lượng low-FPR đáng tin cậy.

### 3.4. Cohort confirmatory PID 1.923 mẫu — đã hoàn tất

| Thuộc tính | Giá trị |
|---|---:|
| Cohort đã khóa | 1.923 |
| Manifest SHA-256 | `9540b88b0da2463f63b4e983f5ecc277e3845b7badebbb79695e35f2c3b1a669` |
| Metadata usable | 1.922 |
| Coverage | 99,95% |
| Benign usable | 932/932 = 100% |
| Malware usable | 990/991 = 99,90% |
| Ngưỡng tối thiểu đã khóa | 90% = 1.731 mẫu |
| Mẫu thiếu thực | 1 malware, HTTP 404 |
| Deferred do rate limit | 0 |

**Quyết định hiện tại:** run confirmatory đã chạy trên 1.922 mẫu usable sau khi collection kết thúc. Mẫu HTTP 404 được giữ là missing thật, không thay thế hoặc tạo metadata. Verification replay pass.

Nguồn xác nhận: `results/measured_20261023_malbehavd_pid_confirmatory_1922/`.

---

## 4. Đóng góp 1 — Adaptive static–dynamic fusion/PID

### 4.1. Cơ chế đã cài đặt

Với mỗi mốc sự kiện (k):

\[
e_k=p_{static}-p_{dynamic,k}
\]

\[
I_k=\operatorname{clip}(I_{k-1}+e_k\Delta t_k), \qquad
D_k=\frac{e_k-e_{k-1}}{\Delta t_k}
\]

\[
u_k=K_pe_k+K_iI_k+K_dD_k
\]

\[
w_k=\operatorname{clip}(\sigma(u_k),0.1,0.9)
\]

\[
p_{fused,k}=w_kp_{static}+(1-w_k)p_{dynamic,k}.
\]

Trạng thái được reset theo execution; (D_0=0); integral có giới hạn anti-windup. Đây là heuristic thích nghi theo lịch sử bất đồng giữa hai detector, không phải PID điều khiển một plant vật lý và không có bảo đảm lý thuyết tự động về giảm FPR.

### 4.2. Thiết kế thực nghiệm đã khắc phục

- Static scorer: median imputation, standardization và balanced logistic regression trên 199 structural features; score được Platt-calibrate trên calibration partition.
- Dynamic scorer: TF-IDF API unigram/bigram trên từng prefix, tối đa 10.000 chiều, balanced logistic regression và Platt calibration.
- Static và dynamic được ghép đúng SHA-256.
- Base training, calibration, fusion validation và outer test tách rời trong mỗi fold.
- Gain, fixed weight và threshold được chọn trên validation, không chọn trên test.
- So sánh cùng đầu vào và cùng test rows: Static, Dynamic, Average 50/50, Fixed, P, PI, PID.
- Có AUC, AP, FPR, TPR, Brier, fold variation và paired bootstrap.
- Có trajectory theo 5/10/15/20 sự kiện.
- Có kiểm tra riêng `PID − PI` để xác định đóng góp D.

### 4.3. Kết quả confirmatory cuối chuỗi

Các ô là mean ± sample SD qua 5 outer folds.

| Phương pháp | ROC-AUC | AP | FPR (%) | TPR (%) | Brier |
|---|---:|---:|---:|---:|---:|
| Static | 0,9702 ± 0,0140 | 0,9700 ± 0,0130 | 23,58 ± 11,74 | 96,56 ± 2,01 | 0,0567 ± 0,0146 |
| Dynamic | 0,9733 ± 0,0076 | 0,9802 ± 0,0055 | 16,40 ± 5,57 | 95,46 ± 2,11 | 0,0584 ± 0,0106 |
| **Average 50/50** | **0,9844 ± 0,0088** | **0,9883 ± 0,0059** | 13,40 ± 6,49 | 96,57 ± 0,66 | **0,0455 ± 0,0100** |
| Fixed weight | 0,9832 ± 0,0086 | 0,9872 ± 0,0060 | **11,69 ± 3,58** | 96,06 ± 0,84 | 0,0481 ± 0,0108 |
| P | 0,9838 ± 0,0088 | 0,9878 ± 0,0058 | 13,29 ± 6,07 | 96,36 ± 0,74 | 0,0476 ± 0,0101 |
| PI | 0,9837 ± 0,0089 | 0,9877 ± 0,0059 | 13,83 ± 6,06 | 96,47 ± 0,71 | 0,0474 ± 0,0102 |
| PID | 0,9838 ± 0,0088 | 0,9877 ± 0,0058 | 13,83 ± 6,06 | 96,47 ± 0,71 | 0,0479 ± 0,0105 |

**Hiệu ứng mô tả nổi bật:**

- Average cao hơn Static khoảng 1,42 điểm phần trăm ROC-AUC.
- Average cao hơn Dynamic khoảng 1,12 điểm phần trăm ROC-AUC.
- Average cao hơn PID khoảng 0,064 điểm phần trăm ROC-AUC.
- Fixed đạt FPR thấp nhất; không có một luật tốt nhất trên mọi tiêu chí.

**PID so với Fixed trên dự đoán out-of-fold:**

- ΔAUC = `+0,00043`, bootstrap 95% CI `[-0,00088; +0,00175]`.
- ΔAP = `+0,00027`, bootstrap 95% CI `[-0,00079; +0,00137]`.
- ΔTPR = `+0,40` điểm phần trăm, CI `[-0,20; +1,00]`.
- ΔFPR = `+2,16` điểm phần trăm, CI `[+0,84; +3,50]`; dấu dương nghĩa là PID có FPR cao hơn.

### 4.4. Kết quả riêng của thành phần D

- PID tối ưu so với PI tối ưu: ΔAUC `-0,000125`, CI 95% `[-0,000296; +0,000044]`; ΔBrier `+0,000512`, CI `[+0,000134; +0,000934]`, bất lợi cho PID.
- Khi giữ cùng Kp, Ki, threshold và đặt Kd=0: ΔAUC `+0,000015`, CI 95% `[-0,000021; +0,000049]`.
- Trung bình `|Δscore|` tại mốc cuối = `0,000207`; lớn nhất = `0,005207`.
- Quyết định phân lớp khác nhau tại mốc cuối = `0/1.922`.
- Trên cả bốn mốc, D làm đổi 6/7.688 dòng quyết định nhưng khác biệt biến mất ở mốc cuối.

**Diễn giải phù hợp:** ở horizon 5–20 sự kiện, D chưa mang thêm lợi ích nhận diện có thể đo được. Kết quả ủng hộ luật dung hợp đơn giản hơn, thay vì ủng hộ full PID.

### 4.5. Phát biểu được phép

- Hai kênh tĩnh và động có tính bổ sung trong cohort xác nhận.
- Nhóm fusion cải thiện ranking so với từng kênh riêng.
- Average đạt AUC/AP/Brier trung bình tốt nhất; Fixed đạt FPR thấp nhất.
- Ablation phát hiện I/D chưa tạo lợi ích gia tăng rõ trong horizon hiện tại.
- Pipeline event-indexed có thể chạy an toàn chỉ từ report/metadata công khai.

### 4.6. Phát biểu chưa được phép

- “Full PID vượt trội Average, P hoặc PI.”
- “PID giảm báo động nhầm.”
- “PID xử lý sleep evasion.”
- “PID cải thiện latency phát hiện theo giây.”
- “Kết quả xác nhận hiệu quả trên ransomware.”
- “Cải thiện AUC/AP có ý nghĩa xác nhận”; CI hiện còn đi qua 0.

### 4.7. Phần còn thiếu cho paper mạnh

1. Bổ sung `max-risk`, calibrated logistic stacking và ít nhất một learned-fusion baseline.
2. Báo pAUC/TPR tại FPR thấp và phân tích calibration theo mục tiêu vận hành.
3. Phân tích sensitivity của gain và weight trajectory.
4. Nếu muốn giữ D, cần chuỗi dài hơn hoặc định nghĩa reliability/error có ý nghĩa hơn; không chọn lại split để tìm kết quả thuận lợi.
5. Đổi paper framing sang event-indexed fusion/component selection; không tuyên bố full PID vượt trội.

---

## 4.8. Exploratory reliability-aware PID sau confirmatory

Một runner mới được phát triển sau khi phân tích run xác nhận, dùng 20 tiền tố API,
trọng số cơ sở `w0`, mô hình độ tin cậy học trên calibration và lưới gain cho phép
`Ki=0`, `Kd=0`. Đây là kết quả post-hoc/exploratory, không thay thế bằng chứng
confirmatory và cần cohort external/temporal mới.

- Reliability-P đạt AUC 0,9826, FPR 11,15%, TPR 95,96%, Brier 0,0456.
- So với Fixed, Reliability-P giảm FPR 1,33 điểm phần trăm, CI 95%
  `[-2,45; -0,21]`, và giảm Brier 0,00308, CI `[-0,00560; -0,00071]`.
- Full reliability-PID đạt AUC 0,9825 và FPR 11,58%; không hơn PI/P.
- Full PID trừ PI có ΔAUC +0,00007 với CI đi qua 0; FPR tăng 0,11 điểm phần
  trăm, CI `[0; +0,33]`; TPR không đổi.
- Average vẫn tốt nhất về AUC/AP/event-AUC; do đó chưa được tuyên bố full PID
  vượt các baseline dung hợp.

Kết quả củng cố framing **reliability-aware adaptive fusion with PID component
ablation**, trong đó thành phần P tạo lợi ích vận hành và D chưa có bằng chứng hỗ
trợ. Nguồn: `results/measured_20261023_reliability_pid_exploratory_1922/`.


## 4.9. Exploratory uncertainty-gated PID

Gate được chọn bằng cross-fitting: với outer fold đang kiểm thử, ngưỡng thấp/cao
chỉ dùng OOF static predictions của các folds còn lại. Ở gate chính, early-FNR và
early-FPR bị giới hạn 1% trên development; 52,67% outer-test được chuyển sang
phân tích động.

| Phương pháp end-to-end | AUC | FPR | TPR | Brier |
|---|---:|---:|---:|---:|
| Average | 0,9762 | 13,08% | 96,46% | 0,0465 |
| Fixed | 0,9756 | 10,62% | 95,65% | 0,0484 |
| Reliability-P | 0,9761 | **9,97%** | 95,76% | 0,0466 |
| Reliability-PI | 0,9761 | 10,29% | 95,76% | 0,0466 |
| Reliability-PID family | 0,9760 | 10,29% | 95,76% | 0,0466 |
| Full PID (`Kd>0`) | 0,9760 | 10,40% | 95,76% | 0,0466 |

Bootstrap end-to-end cho thấy Reliability-P giảm FPR 0,66 điểm phần trăm so với
Fixed nhưng CI 95% `[-1,53; +0,21]` còn đi qua 0. Full PID so với PI tăng FPR
0,11 điểm phần trăm, CI `[0; +0,33]`, TPR không đổi. So với Average, full PID
giảm FPR 2,72 điểm phần trăm nhưng đồng thời giảm TPR 0,71 điểm, cả hai CI loại
trừ 0. Gate vì vậy làm rõ đánh đổi vận hành nhưng không tạo bằng chứng full PID
vượt P/PI.

Nguồn: `results/measured_20261027_gated_pid_exploratory_1922/`.


## 4.10. Effect size phù hợp cho trình bày bảo vệ

Khi câu hỏi là lợi ích của full PID fusion so với từng kênh độc lập, hiệu ứng
đủ lớn và bootstrap ghép cặp loại trừ 0:

- Full PID so với Static: ΔAUC +1,34 điểm phần trăm, CI 95%
  `[+0,78; +1,94]`; ΔFPR -12,06 điểm, CI `[-14,60; -9,57]`.
- Full PID so với Dynamic: ΔAUC +1,14 điểm phần trăm, CI
  `[+0,68; +1,61]`; ΔFPR -8,87 điểm, CI `[-11,16; -6,59]`.
- FPR tương đối giảm 50,9% so với Static và 43,2% so với Dynamic.
- Adaptive P so với Fixed giảm FPR 1,33 điểm, CI `[-2,45; -0,21]`, và giảm
  Brier 0,00308, CI `[-0,00560; -0,00071]`.

Các effect size này hỗ trợ phát biểu **PID-family fusion cải thiện so với phân
tích đơn kênh** và **adaptive P cải thiện so với Fixed**. Chúng không thay đổi
kết luận ablation rằng D chưa tạo lợi ích gia tăng so với PI/P.

Nguồn: `results/measured_20261027_pid_defense_evidence_1922/`.

## 5. Đóng góp 2 — XAI-Guided Active Learning

### 5.1. Cơ chế

Tín hiệu bất định:

\[
U(x)=1-2|p(x)-0.5|.
\]

Với vector SHAP có dấu \(\phi\), Directional Entropy (H) được tính từ tỷ lệ tổng khối lượng SHAP dương so với tổng khối lượng dương + âm. (H) cao khi lời giải thích có các lực kéo đáng kể theo cả hai hướng. (V) là phương sai của các giá trị SHAP có dấu trên các chiều đặc trưng.

Các score đều được min–max normalize trên pool trước khi kết hợp:

| Phương pháp | Điểm truy vấn |
|---|---|
| Random | Ngẫu nhiên |
| Uncertainty | \(U\) |
| U+H | \(3U/7 + 4H/7\) |
| U+V | \(0,5U + 0,5V\) |
| XAI_full | \(0,3U + 0,4H + 0,3V\) |

AL chỉ chọn mẫu để hỏi oracle/chuyên gia. Nó không tự sinh pseudo-label.

### 5.2. Thiết kế đã khắc phục

- 5 outer folds × 5 seeds.
- AL seeds: 11, 22, 33, 44 và 55.
- 200 nhãn ban đầu, 10 vòng × 100 nhãn; tối đa 1.200 training labels.
- LightGBM: 60 trees, learning rate 0,05, `num_leaves=15`, `max_depth=4`; cấu hình deterministic theo seed.
- Năm phương pháp dùng cùng initial set trong từng fold/seed.
- Validation/test không đi vào pool truy vấn.
- Target được xác định trên validation từ full-pool reference; test không quyết định thời điểm dừng.
- Có ROC-AULC, AP-AULC, số nhãn tới target, paired fold effects, low-FPR metrics và query overhead.
- TreeSHAP có additivity check trên raw score.
- Replay đủ 1.375 checkpoint, 1.100.000 prediction records và 125.000 query records; 5/5 fold pass.

### 5.3. Kết quả chính

| Phương pháp | ROC-AULC | AP-AULC | Nhãn đạt target | Query/10 vòng (s) | Model + query (s) |
|---|---:|---:|---:|---:|---:|
| Random | 0,928777 | 0,868350 | 584 | 0,0194 | 4,1947 |
| Uncertainty | 0,931272 | 0,881934 | 520 | 0,0191 | 4,1454 |
| **U+H** | **0,933026** | **0,883336** | 508 | 0,2459 | 4,4741 |
| U+V | 0,930377 | 0,880164 | **488** | 0,2298 | 4,3826 |
| XAI_full | 0,932202 | 0,881638 | 492 | 0,2358 | 4,3471 |

“Nhãn đạt target” là số training labels trung bình khi lần đầu đạt target validation. Nhãn validation là chi phí bổ sung và không được tính vào cột này; các con số cũng là oracle queries từ ground truth có sẵn, chưa phải thời gian gán nhãn của con người.

**So sánh ghép cặp theo outer fold:**

- U+H so với Random: ΔROC-AULC `+0,004249`, ΔAP-AULC `+0,014985`, thắng 5/5 folds; giảm 76 nhãn, tương đương 13,0%.
- U+H so với Uncertainty: ΔROC-AULC `+0,001754`, ΔAP-AULC `+0,001401`, thắng 4/5 folds; lợi ích nhỏ.
- XAI_full so với Random: ΔROC-AULC `+0,003425`, ΔAP-AULC `+0,013287`, thắng 5/5 folds; giảm 92 nhãn, tương đương 15,8%.
- XAI_full so với Uncertainty: ΔROC-AULC `+0,000931`, thắng 3/5 folds; ΔAP-AULC `−0,000297`; giảm trung bình 28 nhãn nhưng không vượt baseline mạnh nhất quán.

**Đánh đổi quan trọng:**

- U+H tốt nhất về chất lượng toàn bộ đường học.
- U+V cần ít nhãn nhất để đạt target.
- XAI_full cân bằng hai mục tiêu nhưng không đứng đầu mọi chỉ số.
- Ở 1.200 nhãn, các phương pháp gặp cùng full-pool model, nên giá trị AL phải đọc từ đường học/AULC và label budget, không đọc riêng điểm cuối.

### 5.4. Vùng FPR thấp

| Phương pháp | pAUC tại FPR≤5% | TPR-AULC tại cap FPR 1% | TPR-AULC tại cap FPR 5% |
|---|---:|---:|---:|
| Random | 0,804096 | 0,580620 | 0,731980 |
| Uncertainty | **0,826300** | **0,638180** | 0,769260 |
| U+H | 0,824774 | 0,636780 | 0,770620 |
| U+V | 0,825194 | 0,626260 | 0,768140 |
| XAI_full | 0,823525 | 0,631860 | **0,771460** |

So với Random, các biến thể XAI cải thiện rõ. So với Uncertainty, chênh lệch nhỏ và tùy chỉ số. Không dùng kết quả này để tuyên bố XAI giảm false alert ổn định hơn Uncertainty.

### 5.5. Overhead

- U+H tăng khoảng 0,227 giây query trong 10 vòng so với Uncertainty; tổng model + query tăng khoảng 7,93%.
- XAI_full có tổng overhead khoảng 4,86% so với Uncertainty; query chiếm khoảng 5,42% tổng model + query.
- Đây là thời gian tính score/query ở quy mô 2.000 mẫu, không phải thời gian chuyên gia gán nhãn và không phải latency phát hiện một PE.

### 5.6. Phát biểu được phép

- Tín hiệu SHAP giúp vượt Random về AULC trong thiết lập này.
- Directional Entropy là thành phần tạo bằng chứng rõ nhất về chất lượng đường học.
- XAI_full giảm label budget trung bình so với Random và Uncertainty tại target đã định.
- Không có một cấu hình tốt nhất trên mọi tiêu chí.

### 5.7. Phần còn thiếu

- Strong baselines: uncertainty + diversity/k-center, query-by-committee.
- Sensitivity theo trọng số 0,3/0,4/0,3 và cách normalize.
- Batch redundancy/diversity và positive-label yield theo vòng.
- External/temporal/family-disjoint evaluation.
- Đo thời gian gán nhãn thật nếu muốn quy đổi label savings thành chi phí chuyên gia.
- Interaction `AL × fusion` chưa được chạy.

---

## 6. Đóng góp 3 — Fidelity và độ ổn định TreeSHAP

### 6.1. Vấn đề cũ đã được khắc phục

Bản cũ dựa vào Faithfulness, Consistency, Contrastive và OFS nhưng chưa chứng minh thang đo từ miền khác phù hợp với đặc trưng PE. Bản hiện tại thay cách trình bày bằng các phép đo tách biệt:

1. **Faithfulness tương đối:** deletion top-|SHAP| so với uniform random mask cùng (k).
2. **Độ nhạy baseline:** thay bằng mean và median tính chỉ từ training data.
3. **Độ ổn định:** Spearman toàn cục và Jaccard top-k giữa fitted models.
4. **Additivity:** tổng SHAP + bias tái tạo raw log-odds của LightGBM.
5. **Geometry diagnostics:** EC/CF báo riêng; không coi là bằng chứng nhân quả.
6. **OFS:** không tổng hợp vì chưa có chuẩn hóa và trọng số chung đã kiểm định.

### 6.2. Thiết kế

- 5 folds × 5 model seeds × 2 masking baselines = 50 runs.
- Model seeds: 41, 42, 43, 44 và 45.
- LightGBM: 100 trees, learning rate 0,1, `feature_fraction=0,8`, `bagging_fraction=0,8` để tạo các fitted models khác nhau có kiểm soát.
- (k \in \{10,25,50\}).
- 20 uniform random masks cho mỗi (k) và mỗi fitted model.
- LightGBM dùng row/feature subsampling để fitted model khác nhau có kiểm soát theo seed.
- Top-k được xếp theo \,\(|SHAP|\); SHAP có dấu được dùng cho EC/CF.
- 50/50 lượt verification pass; 3.150 mask batches và 1.260.000 prediction records được replay.

### 6.3. Kết quả deletion

| Baseline | k | AUC drop top-SHAP | AUC drop random | Chênh top − random |
|---|---:|---:|---:|---:|
| Mean | 10 | 0,047817 | 0,000200 | 0,047617 |
| Mean | 25 | 0,135853 | 0,000530 | 0,135323 |
| Mean | 50 | **0,306729** | 0,000979 | **0,305750** |
| Median | 10 | 0,053483 | 0,000094 | 0,053388 |
| Median | 25 | 0,125180 | 0,000326 | 0,124854 |
| Median | 50 | **0,300777** | 0,000658 | **0,300119** |

Ở (k=50), tác động top-SHAP lớn hơn random khoảng 300 lần theo tỷ lệ thô. Cách phát biểu an toàn hơn trong paper là báo chênh lệch tuyệt đối và không nhấn mạnh tỷ lệ khi mẫu số random gần 0.

### 6.4. Độ ổn định thứ hạng

| Phạm vi so sánh | Spearman | Jaccard top-10 | top-25 | top-50 |
|---|---:|---:|---:|---:|
| Khác seed, cùng fold | 0,6144 | 0,6221 | 0,5398 | 0,4901 |
| Khác fold | 0,5512 | 0,4416 | 0,3073 | 0,3020 |

Kết quả cho thấy giải thích ổn định trung bình và nhạy hơn với thay đổi phân hoạch dữ liệu so với thay đổi seed trong cùng fold.

### 6.5. EC/CF và OFS

Trên 25 fitted models, thống kê mô tả trung bình:

- EC ≈ `0,4268 ± 0,0363`.
- CF ≈ `0,4680 ± 0,0465`.
- Max SHAP additivity error trung bình ≈ `6,0×10⁻¹⁵`.

EC là tương quan giữa geometry của feature space chuẩn hóa và geometry của SHAP; CF là khoảng cách centroid lớp trong không gian SHAP đã chuẩn hóa theo norm mẫu lớn nhất. Đây là diagnostics, không phải chuẩn “đúng/sai” của explanation.

Không tính OFS vì FF, EC và CF không cùng miền giá trị, không có trọng số đã validation và chưa có căn cứ cho một composite score trong miền PE.

### 6.6. Phát biểu được phép

- Các feature được TreeSHAP xếp hạng cao ảnh hưởng tới prediction mạnh hơn random features cùng ngân sách masking.
- Kết quả giữ dưới cả mean và median replacement.
- Rank stability ở mức trung bình; thay đổi fold ảnh hưởng nhiều hơn thay đổi seed.
- TreeSHAP giải thích đúng fitted static model ở nghĩa additivity và model faithfulness tương đối.

### 6.7. Phát biểu chưa được phép và phần còn thiếu

- Masking trong feature space không chứng minh tồn tại PE hợp lệ tương ứng.
- Không chứng minh quan hệ nhân quả hoặc “đặc trưng gây ra malware”.
- Chưa có group-aware/conditional intervention cho Header, Section, Import, ByteHistogram.
- Chưa có magnitude-matched, used-feature-only hoặc attribution-permutation negative control.
- Chưa so với một explainer khác.
- Fidelity chưa chạy trên dynamic model, fusion model hoặc các checkpoint AL đại diện.

---

## 7. Đối chiếu kế hoạch Multi-Stage: đã khắc phục và còn thiếu

| Yêu cầu trong kế hoạch | Trạng thái | Bằng chứng hiện có | Việc còn làm |
|---|---|---|---|
| Provenance dữ liệu | **Một phần** | EMBER identity/hashes; MalBehavD source hash/cohort manifest | Ransomware ground truth, license/provenance đầy đủ, external source |
| Dynamic evidence thật | **Đạt ở pilot** | API sequences công khai ghép SHA-256, không tạo từ label | Confirmatory coverage; timestamp/behavior richer nếu claim temporal |
| Static–dynamic baselines | **Khá đầy đủ ở pilot** | Static, Dynamic, Average, Fixed, P, PI, PID | Max-risk, stacking, learned fusion |
| P/PI/PID ablation | **Đạt ở pilot** | D không đổi 0/199 quyết định | Lặp trên confirmatory cohort; quyết định giữ/bỏ D |
| Uncertainty gate | **Một phần** | Static gate phụ: route khoảng 49,3%; early-FN 1,4% positive; early-FP 1,53% negative | Quyết định cuối cho routed rows, quality–cost curve, missing dynamic policy |
| Sleep evasion | **Chưa đạt** | Chỉ có event windows | Cần delayed behavior xác minh, time-to-detection và wall-clock time |
| Latency decomposition | **Chưa đạt** | Chỉ có query/model computation | Queue, static extraction, sandbox startup, observation, dynamic scoring, fusion, p95/p99 |
| AL baseline/ablation | **Đạt mức khá** | 5 strategies, 5 folds × 5 seeds, AULC/label budget | Diversity/QBC, weight sensitivity, external split |
| AL × fusion interaction | **Chưa đạt** | Chưa có ma trận 2×2 | Fixed/PID × baseline/XAI trên cùng data |
| Fidelity controls | **Đạt mức khá** | Mean/median, random, k, folds/seeds, stability | Group-aware/conditional và explainer baselines |
| Low-FPR evaluation | **Một phần** | Có cho AL | PID/system cần nhiều benign hơn và CI phù hợp |
| Reproducibility | **Đạt tốt** | Hash, split, prediction, verification, source commit | Đóng gói environment lock/release và data-access instructions |
| External/temporal validation | **Chưa đạt** | Không có | Bắt buộc cho journal claim mạnh |
| Integrated multi-stage result | **Chưa đạt** | Các đóng góp chạy trên hai dataset khác nhau | Cùng cohort, cùng split, gate → dynamic → fusion → AL |

Các số liệu gate trong bảng là bằng chứng phụ từ `results/measured_20261019_ember_identity/static_gate/`; chúng chưa nằm trong gói confirmatory AL/Fidelity và chưa có quyết định động cho routed rows.

---

## 8. Những góp ý seminar đã xử lý

### 8.1. “Cần tách đóng góp của từng thành phần”

**Đã xử lý:**

- PID: Static, Dynamic, Average, Fixed, P, PI, PID.
- AL: Random, Uncertainty, U+H, U+V, XAI_full.
- Fidelity: top-SHAP/random, mean/median, nhiều k, stability.

**Còn thiếu:** ma trận tích hợp giữa PID và AL; learned-fusion baseline.

### 8.2. “Công thức PID có đúng và vì sao cần?”

**Đã xử lý:** công thức rời rạc đã đồng bộ với code; có reset, \(\Delta t\), anti-windup, clip và validation-selected gain. Lý do sử dụng là mô hình hóa bất đồng hiện tại, tích lũy và biến thiên theo chuỗi.

**Kết quả thực nghiệm:** P tạo phần cải thiện chính; I/D chưa tạo giá trị gia tăng rõ. Do đó công thức được kiểm chứng bằng ablation, không được “chứng minh hiệu quả” chỉ từ hình thức toán học.

### 8.3. “Chuẩn Fidelity từ miền khác có phù hợp mã độc?”

**Đã xử lý:** không bê nguyên một composite score; dùng deletion trong feature space với random control, hai train-derived baselines và stability. Giới hạn PE validity được ghi rõ.

**Còn thiếu:** group-aware/conditional intervention để phù hợp cấu trúc phụ thuộc của PE.

### 8.4. “Kết quả gán nhãn chưa thuyết phục”

**Đã xử lý:** có target validation khai báo trước, AULC, label-to-target, paired folds và overhead. XAI_full giảm 92 nhãn so với Random; U+V là cấu hình ít nhãn nhất.

**Còn thiếu:** thời gian chuyên gia thật và strong AL baselines.

### 8.5. “AUC chỉ tăng ít, có ý nghĩa không?”

**Đã xử lý:** không chỉ báo endpoint AUC; báo AULC, AP-AULC, label savings, low-FPR metrics, CI/paired effects và operational trade-off.

**Diễn giải:** lợi ích chính của AL là sample efficiency; lợi ích chính của fusion pilot là tính bổ sung hai kênh. Không phóng đại chênh lệch nhỏ thành superiority tuyệt đối.

### 8.6. “Tĩnh, động, kết hợp và AL đóng góp gì?”

**Đã xử lý một phần:** PID pilot tách static/dynamic/fusion; AL tách các query strategy.

**Còn thiếu:** chưa có một experiment end-to-end kết nối tất cả thành phần trên cùng dataset.

---

## 9. Ma trận claim cho manuscript

### 9.1. Có thể viết trong abstract/conclusion

- “On a 2,000-sample identity-verified EMBER subset, explanation-guided acquisition improved ROC/AP learning-curve area over random sampling.”
- “The U+H variant achieved the strongest AULC, while U+V required the fewest labels to reach the predeclared validation target.”
- “Top-|SHAP| deletion caused substantially larger AUC degradation than equal-budget random deletion under mean and median baselines.”
- “A 199-sample paired pilot showed that static and dynamic signals were complementary; the proportional fusion variant achieved the highest mean ROC-AUC.”
- “The derivative term did not alter any final decision in the pilot, motivating a simpler controller for the examined event horizon.”

### 9.2. Chỉ nên viết ở discussion/limitations

- PID có xu hướng hơn Fixed về AUC nhưng CI còn qua 0.
- XAI_full tiết kiệm nhãn trung bình nhưng không tốt nhất trên mọi metric.
- Rank stability ở mức trung bình và giảm giữa folds.
- Dữ liệu là generic Windows malware, chưa phải ransomware-specific.
- Ba đóng góp hiện được xác nhận trên hai dataset khác nhau.

### 9.3. Không được viết như kết luận đã chứng minh

- “The method detects ransomware/zero-day families.”
- “PID significantly outperforms all fusion baselines.”
- “PID reduces false positives.”
- “The system handles sleep evasion.”
- “The complete pipeline is production-ready.”
- “XAI_full is the best acquisition method.”
- “OFS proves that the explanations are correct.”
- “Label savings equal analyst-hour savings.”

---

## 10. Cấu trúc paper đề xuất

### 10.1. Paper có thể viết ngay: AL + Fidelity

1. **Introduction**
   - Chi phí nhãn trong malware detection.
   - Uncertainty không khai thác cấu trúc explanation.
   - Explanation cần được kiểm tra chứ không chỉ minh họa.
2. **Related Work**
   - Static PE malware detection.
   - Active learning cho malware/tabular data.
   - SHAP-guided sampling.
   - Fidelity/stability của feature attribution.
3. **Method**
   - LightGBM/TreeSHAP.
   - (U,H,V) và năm acquisition strategies.
   - Deletion controls và rank stability.
4. **Experimental Protocol**
   - EMBER identity, splits, target, seeds, leakage controls.
5. **Results**
   - AULC/label budget.
   - Low-FPR trade-off.
   - Overhead.
   - Deletion/stability.
6. **Discussion**
   - Không có universal winner.
   - Masking/OOD và generic malware scope.
7. **Threats to Validity and Conclusion**.

### 10.2. Paper ba đóng góp sau khi hoàn tất PID

1. Introduction và ba research questions.
2. Related work về multi-stage detection, fusion, AL và XAI validation.
3. Data/provenance của một cohort chung.
4. Conditional gate và dynamic scorer.
5. Event-indexed adaptive fusion.
6. Explanation-guided adaptation.
7. Fidelity/diagnostics.
8. Thực nghiệm riêng từng contribution.
9. Thực nghiệm tích hợp và cost/latency.
10. Threats to validity.

Không nên ghép hai dataset thành một “end-to-end pipeline result”. Nếu vẫn dùng cả EMBER và MalBehavD, paper phải gọi đây là **component-wise evaluation on complementary benchmarks**.

---

## 11. Bảng và hình nên đưa vào paper

### Bảng bắt buộc

1. Dataset/provenance và label semantics.
2. AL AULC + label-to-target + overhead.
3. Paired fold effects U+H/XAI_full so với Random và Uncertainty.
4. Fidelity deletion mean/median tại k=10/25/50.
5. SHAP rank stability.
6. Nếu giữ PID: bảy cấu hình fusion và bootstrap PID−Fixed.
7. Claim/limitation hoặc threats-to-validity summary.

### Hình bắt buộc

1. Learning curves theo label budget, có mean và variability qua folds.
2. AULC và label budget summary.
3. Deletion effect top-SHAP vs random cho hai baselines.
4. Rank stability trong fold/giữa fold.
5. Nếu giữ PID: final AUC/AP/FPR/TPR và event trajectory 5/10/15/20.

### Hình không dùng như bằng chứng

- Dashboard demo.
- Case study giả định không gắn row ID.
- Latency figure cũ không có log đo đầu cuối.
- Bảng/biểu đồ legacy ở thư mục gốc `results/`.

---

## 12. Artifact map dùng khi viết

### AL

- `results/confirmatory_20261019_ember_identity/al/aulc_summary.csv`
- `results/confirmatory_20261019_ember_identity/al/target_reach_summary.csv`
- `results/confirmatory_20261019_ember_identity/al/fold_level_effects.csv`
- `results/confirmatory_20261019_ember_identity/al/low_fpr_aulc_by_fold.csv`
- `results/confirmatory_20261019_ember_identity/al/overhead_by_fold.csv`
- `results/confirmatory_20261019_ember_identity/al/learning_curves.pdf`
- `results/confirmatory_20261019_ember_identity/al/verification.json`

### Fidelity

- `results/confirmatory_20261019_ember_identity/fidelity/deletion_summary.csv`
- `results/confirmatory_20261019_ember_identity/fidelity/model_deletion_comparisons.csv`
- `results/confirmatory_20261019_ember_identity/fidelity/shap_stability_summary.csv`
- `results/confirmatory_20261019_ember_identity/fidelity/model_metrics.csv`
- `results/confirmatory_20261019_ember_identity/fidelity/deletion_effect.pdf`
- `results/confirmatory_20261019_ember_identity/fidelity/shap_stability.pdf`
- `results/confirmatory_20261019_ember_identity/fidelity/verification.json`

### PID pilot

- `results/measured_20261020_malbehavd_pid_pilot200/fusion_summary.csv`
- `results/measured_20261020_malbehavd_pid_pilot200/timepoint_oof_metrics.csv`
- `results/measured_20261020_malbehavd_pid_pilot200/fold_effects_pid_minus_fixed.csv`
- `results/measured_20261020_malbehavd_pid_pilot200/paired_bootstrap_pid_minus_fixed.json`
- `results/measured_20261020_malbehavd_pid_pilot200/event_predictions.csv.gz`
- `results/measured_20261020_malbehavd_pid_pilot200/event_pid_final_metrics.pdf`
- `results/measured_20261020_malbehavd_pid_pilot200/event_pid_trajectory.pdf`
- `results/measured_20261020_malbehavd_pid_pilot200/verification.json`

### Provenance và trạng thái

- `results/confirmatory_20261019_ember_identity/static_identity_audit.json`
- `results/confirmatory_20261019_ember_identity/SHA256SUMS`
- `results/measured_20261020_malbehavd_pid_pilot200/dataset_audit.json`
- `results/measured_20261020_malbehavd_pid_pilot200/artifact_sha256.json`
- `results/measured_20261020_malbehavd_pid_full_collection_progress/coverage_audit.json`

---

## 13. Việc cần hoàn thành theo ưu tiên

### P0 — Chốt phạm vi paper

- Chọn paper AL/Fidelity có thể viết ngay, hoặc paper multi-stage ba đóng góp cần thêm thực nghiệm.
- Nếu deadline gần, dùng phương án AL/Fidelity. Không để PID pilot làm claim trung tâm.

### P1 — Hoàn tất PID confirmatory nếu giữ đóng góp 1

1. Tiếp tục đúng cohort/cache đến ít nhất 1.731 usable.
2. Audit coverage/missingness theo label và fold.
3. Chạy `event-pid` đúng một lần với split/gain grid đã khóa.
4. Bổ sung max-risk và learned/calibrated fusion baseline.
5. Quyết định giữ P/PI/PID dựa trên kết quả, kể cả khi D âm.

### P2 — Thí nghiệm tích hợp

- Dùng cùng cohort và cùng folds.
- Tối thiểu: `Fixed + baseline AL`, `P/PID + baseline AL`, `Fixed + XAI AL`, `P/PID + XAI AL`.
- Tính difference-in-differences; chỉ nói “synergy” khi interaction được đo.
- Đánh giá gate trên toàn traffic, gồm cả early decisions và routed rows.

### P3 — Generalization và operating point

- Family/source-disjoint split.
- Temporal split hoặc external dataset.
- TPR tại FPR 1%/5% với CI; muốn FPR thấp hơn cần tăng mạnh số benign.
- Precision theo prevalence giả định công khai.

### P4 — Operational evaluation

- Đo queue, static feature extraction, static inference, sandbox startup, observation, dynamic scoring, fusion.
- Báo median/p95/p99, throughput, phần cứng và traffic routed fraction.
- Đo analyst labeling time riêng nếu muốn quy đổi label savings thành chi phí.

### P5 — Mở rộng Fidelity/AL

- Group-aware/conditional masking.
- Used-feature/magnitude-matched/attribution-permutation controls.
- Diversity/k-center và query-by-committee.
- Weight/normalization sensitivity cho (U,H,V).
- Fidelity trên checkpoint AL và fusion model phù hợp.

---

## 14. Cổng sẵn sàng nộp bài

| Cổng | Điều kiện | Hiện tại |
|---|---|---|
| Dataset gate | Provenance và semantics phù hợp claim | **Đạt cho generic malware; không đạt cho ransomware** |
| AL gate | Baseline, folds/seeds, label budget, verification | **Đạt mức paper component** |
| Fidelity gate | Controls, repeated models, limitations | **Đạt mức paper component** |
| Dynamic/PID gate | Paired real signals và confirmatory coverage | **Đạt pilot; chưa đạt confirmatory** |
| PID value gate | Hơn baseline đơn giản/learned hoặc có negative-result framing | **P tốt nhất; full PID chưa được ủng hộ** |
| Integration gate | Gate + fusion + AL trên cùng protocol | **Chưa đạt** |
| Generalization gate | Temporal/family/external test | **Chưa đạt** |
| Operational gate | End-to-end cost/latency | **Chưa đạt** |
| Reproducibility gate | Hash, predictions, config, replay | **Đạt tốt cho run hiện có** |

---

## 15. Mẫu phát biểu đóng góp phù hợp

### Nếu viết paper AL/Fidelity ngay

1. Đề xuất acquisition score kết hợp prediction uncertainty với Directional Entropy và SHAP Variance cho static Windows malware detection.
2. Thực hiện đánh giá paired, multi-fold/multi-seed theo toàn bộ label budget, gồm label-to-target, low-FPR behavior và overhead.
3. Đề xuất protocol kiểm tra TreeSHAP trên đặc trưng PE bằng deletion có random control, hai training-derived baselines và rank stability, đồng thời tránh composite OFS chưa được validation.

### Nếu viết paper multi-stage sau confirmatory

1. Thiết kế event-indexed adaptive static–dynamic fusion và ablation xác định thành phần controller thực sự cần thiết.
2. Thiết kế explanation-guided adaptation để sử dụng hiệu quả ngân sách nhãn.
3. Thiết kế evaluation framework kiểm tra prediction quality, explanation faithfulness/stability và cost trong một protocol có thể replay.

Nếu confirmatory tiếp tục cho thấy P vượt hoặc bằng PI/PID, đóng góp 1 nên mô tả **evidence-driven simplification of temporal fusion**, không mô tả “full PID superiority”.

---

## 16. Những nội dung cần bổ sung trong Related Work

Trước khi viết Introduction/Related Work cuối, cần lập bảng 3–5 công trình gần nhất cho từng nhóm:

1. Static PE malware detection bằng gradient boosting/EMBER.
2. Static–dynamic malware fusion và conditional analysis.
3. Active learning cho malware/security, đặc biệt uncertainty + diversity.
4. XAI-guided acquisition hoặc explanation disagreement.
5. SHAP faithfulness/stability trên tabular/security data.

Mỗi công trình cần đối chiếu: dataset, label semantics, input modality, split, baseline, metric, availability của code/data và khác biệt phương pháp. Không so trực tiếp AUC giữa các paper dùng dataset/split khác nhau để tuyên bố vượt trội.

---

## 17. Nguồn chuẩn và commit tái lập

- AL/Fidelity confirmatory được tạo từ commit `fed4322f58f5bb55ec47833e857370d076592a32` với working tree sạch.
- PID pilot tương ứng commit `44812ad0c9997e47b418db55975d80c9814b9b77`.
- Audit collection full PID tương ứng commit `62e8a657454b5257a9e6a57308e4ed988d8068c3`.
- Mỗi gói kết quả có `artifact_sha256.json` hoặc `SHA256SUMS`; nên kiểm tra hash trước khi đóng gói submission artifact.

Tài liệu giao thức cần dùng cùng report này:

- `docs/EXPERIMENT_PROTOCOL.md`
- `docs/CONFIRMATORY_RUNBOOK.md`
- `docs/EVENT_INDEXED_PID_RUNBOOK.md`
- `results/confirmatory_20261019_ember_identity/README.md`
- `results/measured_20261020_malbehavd_pid_pilot200/README.md`
- `results/measured_20261020_malbehavd_pid_full_collection_progress/README.md`

---

## 18. Quyết định khuyến nghị tại thời điểm 21/10/2026

1. **Bắt đầu viết ngay** phần Data, XAI-Guided AL, Fidelity, Experimental Protocol, Results và Threats to Validity từ artifact confirmatory EMBER.
2. **Viết PID như pilot có kết quả âm của D**, không biến pilot thành confirmatory và không đổi quy mô thành 2.000 mẫu.
3. **Không dùng “ransomware” trong claim thực nghiệm chính** cho tới khi có nhãn ransomware xác minh; có thể giữ ransomware là bối cảnh/định hướng ứng dụng nếu diễn đạt rõ.
4. **Không tuyên bố hệ thống end-to-end** vì AL/Fidelity và PID đang chạy trên hai dataset khác nhau.
5. Nếu deadline paper gần, chọn paper AL/Fidelity. Nếu mục tiêu là journal multi-stage, hoàn thành P1–P4 trước khi chốt abstract và title.

