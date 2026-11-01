# Hồ sơ bằng chứng mới nhất và yêu cầu viết lại bài báo

**Ngày cập nhật:** 30/10/2026
**Nhánh:** feat/reproducible-thesis-experiments
**Commit tham chiếu tại thời điểm cập nhật:** 8bfa06b65b93
**Mục đích:** làm nguồn sự thật duy nhất khi viết lại paper từ kết quả hiện có. Tài liệu này thay thế nội dung đánh giá ngày 23/10/2026 trong chính file này.

---

## 1. Kết luận điều hành

Nghiên cứu hiện có đủ bằng chứng để viết lại một bài báo nghiêm túc về **phát hiện malware Windows có khả năng thích nghi và kiểm chứng**, nhưng chưa đủ để tuyên bố một hệ thống ransomware end-to-end đã được xác nhận.

Ba kết quả mạnh nhất hiện nay là:

1. **Adaptive fusion:** trên 1.922 mẫu MalBehavD-V1 ghép cặp, Adaptive P giảm FPR từ 12,45% xuống 11,16% so với Fixed weight, tương ứng −1,28 điểm phần trăm với CI 95% [−2,47; −0,11]. Brier giảm 0,00306 với CI loại 0; TPR không phát hiện khác biệt. Full PID có AUC tương đương Logistic stacking và FPR thấp hơn tại operating point đã khóa, nhưng TPR thấp hơn nhẹ.
2. **XAI-Guided Active Learning:** trên 2.000 mẫu EMBER, U+H đạt ROC/AP-AULC cao nhất; XAI-full cần 492 nhãn so với 584 của Random, giảm 92 nhãn hay 15,8%. So với Uncertainty, lợi ích nhỏ hơn và phụ thuộc chỉ số.
3. **TreeSHAP Fidelity:** deletion top-|SHAP| làm giảm AUC lớn hơn random mask cùng số chiều dưới cả mean và median replacement. Với mean và k=50, độ sụt là 0,306729 so với 0,000979 của random. Spearman thứ hạng là 0,6144 trong cùng fold và 0,5512 giữa các fold.

Các kết quả mới đã thay đổi cách phải viết phần PID:

- Không còn đúng nếu chỉ nói Fixed luôn tốt nhất về FPR. Bằng chứng fusion-only mới cho thấy Adaptive P cải thiện Fixed về FPR và Brier.
- Không được viết full PID thắng mọi phương pháp. Adaptive P tốt hơn full PID về FPR trên horizon 1–20 sự kiện; I và D chưa tạo lợi ích bổ sung ổn định.
- Robust PID v2 trên horizon 40 đạt AUC/AP tương đương Logistic stacking và FPR quan sát thấp hơn, nhưng đây là development evidence trên cohort đã dùng để phát triển phương pháp; CI so với stacking vẫn đi qua 0.
- Pilot timestamp chứng minh pipeline lấy chuỗi API–timestamp thật là khả thi, chưa chứng minh thành phần D cải thiện hiệu năng.

### Phạm vi paper khuyến nghị

Nếu giữ đủ ba đóng góp, paper phải được viết như:

> **Component-wise evaluation of an auditable Windows-malware analysis framework: reliability-aware static–dynamic fusion, explanation-guided sample acquisition, and quantitative TreeSHAP validation.**

Không được mô tả hai benchmark như một thí nghiệm end-to-end duy nhất. EMBER đánh giá AL/Fidelity; MalBehavD-V1 đánh giá fusion. Mối liên hệ giữa ba phần là một kiến trúc nghiên cứu và ba research questions, không phải một kết quả tích hợp trên cùng cohort.

### Tên bài báo đề xuất

**Auditable Adaptive Learning for Windows Malware Detection: Reliability-Aware Fusion, Explanation-Guided Sampling, and SHAP Validation**

Tên ngắn hơn nếu muốn tập trung vào phần có bằng chứng xác nhận mạnh nhất:

**Explanation-Guided Active Learning with Robust TreeSHAP Validation for Static Windows Malware Detection**

Phương án đầu giữ đủ ba đóng góp nhưng cần discussion/threats-to-validity chặt chẽ. Phương án thứ hai dễ bảo vệ hơn ở venue học máy ứng dụng vì dùng một benchmark và một mạch thực nghiệm thống nhất.

---

## 2. Thứ bậc bằng chứng

| Mức bằng chứng | Gói kết quả | Cách dùng |
|---|---|---|
| **Confirmatory, verification pass** | results/confirmatory_20261019_ember_identity | Kết quả chính cho AL và Fidelity |
| **Confirmatory theo protocol ban đầu** | results/measured_20261023_malbehavd_pid_confirmatory_1922 | Chứng minh hai kênh bổ sung; Average/Fixed mạnh; D không có lợi ích |
| **Measured development evidence trên outer-test rows** | results/measured_20261028_fusion_only_evidence_1922 | Dùng cho Adaptive P vs Fixed và Full PID vs stacking; phải ghi rõ phương pháp được phát triển sau confirmatory trên cùng cohort |
| **Exploratory method development** | results/exploratory_20261028_pid_v2_meta_fusion_horizon40 | Trình bày Robust PID v2 như phương án cải tiến, không phải external confirmation |
| **Exploratory stress evidence** | results/exploratory_20261028_stateful_gated_residual_pid_horizon40 và results/exploratory_20261028_pid_evidence_upgrade_horizon40 | Dùng trong robustness/discussion; không dùng làm claim superiority tổng quát |
| **Measured feasibility pilot** | results/measured_20261028_vt_behaviour_pilot20 | Chứng minh khả năng thu chuỗi có timestamp; không dùng làm kết quả hiệu năng PID |
| **Không dùng làm bằng chứng** | File legacy trực tiếp trong results, demo, số mô phỏng, dashboard giả định | Không đưa vào abstract, results hoặc conclusion |

Quy tắc ưu tiên:

1. Kết quả confirmatory quyết định claim chính.
2. Kết quả development/exploratory chỉ giải thích hướng cải tiến và tạo hypothesis cho external validation.
3. Không gộp số từ các cohort hoặc protocol khác nhau vào cùng một hàng so sánh.
4. Không gọi một kết quả là statistically significant nếu CI hoặc phép kiểm định tương ứng chưa loại 0.

---

## 3. Kiểm kê dữ liệu

### 3.1. EMBER 2018 có định danh

| Thuộc tính | Giá trị |
|---|---:|
| Số mẫu | 2.000 |
| Benign / malware | 1.500 / 500 |
| Số đặc trưng | 2.381 |
| SHA-256 mẫu duy nhất | 2.000 |
| row_id duy nhất | 2.000 |
| source_index duy nhất | 2.000 |
| Vector đặc trưng trùng hoàn toàn | 0 |
| Khoảng appeared | 11/2018–12/2018 |
| Có AVClass yếu | 498 |

Hash khóa:

- Dataset SHA-256: 69f0ae680846edd95458d1e7aaabe36f8866f4f22a6d11488b126ed026b28963
- Manifest SHA-256: a2ca16402653e6cc51fdd7a4857d007faf86807b044d78654f180409c73565bb

Nhãn 1 có nghĩa là malware tổng quát. AVClass không phải ransomware ground truth. Random row folds không chứng minh family-held-out, temporal, zero-day hoặc cross-dataset generalization.

Nguồn chuẩn: results/confirmatory_20261019_ember_identity.

### 3.2. MalBehavD-V1 event-indexed

| Thuộc tính | Giá trị |
|---|---:|
| Dòng nguồn | 2.570 |
| Benign / malware nguồn | 1.285 / 1.285 |
| SHA-256 duy nhất | 2.543 |
| SHA trùng / xung đột nhãn | 26 / 0 |
| Cohort tối thiểu 20 API events | 1.923 |
| Metadata usable | 1.922 |
| Benign / malware usable | 932 / 990 |
| Coverage | 99,95% |
| Outer folds | 5, seed 2026 |

Manifest SHA-256: 9540b88b0da2463f63b4e983f5ecc277e3845b7badebbb79695e35f2c3b1a669.

Tín hiệu động là chuỗi API có thứ tự tại các prefix sự kiện. Trục sự kiện không phải thời gian theo giây. Tín hiệu tĩnh gồm 199 thuộc tính cấu trúc từ metadata; allow-list loại verdict, detection count, threat name, tag và filename.

Collector chỉ gọi metadata/report API theo SHA-256; không tải hoặc thực thi PE.

Giới hạn:

- Nhãn benign/malware tổng quát, không phải ransomware.
- Nguy cơ source bias giữa benign và malware.
- Event-indexed không đo latency wall-clock.
- Cohort 1.922 đã được dùng cho phát triển phương pháp sau confirmatory; cần external/temporal cohort để xác nhận thuật toán mới.

### 3.3. Horizon-40 development subset

Robust PID v2 dùng 1.186 mẫu có ít nhất 40 API events, 5 outer folds. Đây là subset được chọn sau khi đã quan sát hạn chế của horizon 20, nên chỉ là exploratory development set.

### 3.4. Timestamp pilot

| Thuộc tính | Giá trị |
|---|---:|
| Pilot cân bằng ban đầu | 20 mẫu, 10 benign / 10 malware |
| Behavior HTML tải thành công | 20/20 |
| Cuckoofork reports | 9 |
| Chuỗi event usable | 8, gồm 2 benign / 6 malware |
| Tổng API–timestamp pairs | 4.697 |
| Event mỗi execution | 13–1.658 |
| Thời lượng usable | 0,02–60,816 giây |

Pilot chỉ chứng minh nguồn dữ liệu và parser khả thi. Quy mô và cân bằng lớp chưa đủ cho outer-fold evaluation hoặc kết luận về D.

---

## 4. Research questions và đóng góp

### RQ1 — Adaptive static–dynamic fusion

Khi tín hiệu tĩnh và động xuất hiện theo chuỗi, reliability-aware adaptive fusion có cải thiện so với từng kênh và các baseline kết hợp không?

Đóng góp phù hợp:

- Công thức cập nhật trọng số theo bất đồng giữa hai detector.
- Ablation P, PI và PID.
- So sánh với Average, Max-risk, Fixed weight và Logistic stacking.
- Báo cả discrimination, calibration và operating-point trade-off.

### RQ2 — Explanation-guided sample acquisition

Trong ngân sách nhãn hữu hạn, Directional Entropy và SHAP Variance có bổ sung giá trị cho uncertainty sampling không?

Đóng góp phù hợp:

- Năm acquisition strategies dùng cùng initial set và budget.
- AULC, label-to-target, low-FPR metrics và overhead.
- Ablation U+H, U+V và XAI-full.

### RQ3 — Quantitative TreeSHAP validation

Thứ hạng TreeSHAP có bám vào fitted model và ổn định qua seed/fold trên dữ liệu PE dạng bảng không?

Đóng góp phù hợp:

- Top-|SHAP| deletion so với equal-budget random masking.
- Mean/median train-derived baselines.
- Rank stability trong fold và giữa fold.
- Không tổng hợp OFS khi chưa có scale/trọng số được kiểm định.

---

## 5. Kết quả mới nhất cho RQ1

### 5.1. Fusion-only comparison trên 1.922 mẫu

| Phương pháp | ROC-AUC | AP | FPR | TPR | Brier |
|---|---:|---:|---:|---:|---:|
| Average 50/50 | 0,9840 | 0,9880 | 14,70% | 96,77% | 0,0450 |
| Max-risk | 0,9779 | 0,9794 | 16,63% | 96,77% | 0,0604 |
| Fixed weight | 0,9821 | 0,9862 | 12,45% | 96,06% | 0,0487 |
| Logistic stacking | 0,9819 | 0,9867 | 14,91% | 96,57% | 0,0454 |
| **Adaptive P** | 0,9827 | 0,9867 | **11,16%** | 95,96% | 0,0456 |
| Adaptive PI | 0,9827 | 0,9867 | 11,48% | 95,96% | 0,0456 |
| Full PID | 0,9828 | 0,9868 | 11,59% | 95,96% | 0,0455 |

Nguồn: results/measured_20261028_fusion_only_evidence_1922.

### 5.2. So sánh ghép cặp quan trọng

**Adaptive P so với Fixed weight**

- ΔFPR = −1,28 pp; CI 95% [−2,47; −0,11].
- ΔBrier = −0,00306; CI 95% [−0,00585; −0,00030].
- ΔTPR = −0,10 pp; CI đi qua 0.
- Số FP: 104 so với 116; TP: 950 so với 951.

Kết luận được phép: adaptive P cải thiện operating-point FPR và calibration so với trọng số cố định, không phát hiện mất TPR có ý nghĩa.

**Full PID so với Logistic stacking**

- ΔFPR = −3,32 pp; CI 95% [−4,94; −1,72].
- ΔAUC = +0,08 pp; CI 95% [−0,19; +0,37].
- ΔTPR = −0,62 pp; CI 95% [−1,21; 0,00].

Kết luận được phép: full PID có AUC tương đương stacking và FPR thấp hơn tại operating point riêng đã khóa, với đánh đổi TPR nhỏ. Không mô tả là so sánh tại cùng TPR.

**Full PID so với Adaptive P**

- ΔFPR = +0,43 pp; CI 95% [+0,11; +0,86].
- TPR không đổi.

Kết luận: I/D không bổ sung lợi ích trong horizon 1–20; full PID không phải biến thể tốt nhất trong họ PID.

### 5.3. Confirmatory component ablation ban đầu

Run confirmatory ngày 23/10 cho thấy:

- Average có mean AUC/AP/Brier tốt nhất trong protocol ban đầu.
- Fixed có mean FPR thấp nhất trong protocol đó.
- PID − PI có ΔAUC −0,000125 với CI đi qua 0.
- Khi giữ Kp, Ki, threshold và tắt Kd, 0/1.922 quyết định cuối thay đổi.
- D chỉ làm đổi 6/7.688 quyết định ở các prefix trung gian và khác biệt mất tại mốc cuối.

Ý nghĩa: bằng chứng xác nhận ban đầu hỗ trợ sự bổ sung của hai kênh và bác bỏ việc coi D là nguồn cải thiện tự động.

### 5.4. Robust PID v2 trên horizon 40 — exploratory

| Phương pháp | AUC | AP | FPR | TPR | Brier |
|---|---:|---:|---:|---:|---:|
| Average | 0,9891 | 0,9909 | 4,30% | 94,35% | 0,0388 |
| Fixed | 0,9891 | 0,9910 | 4,47% | 94,35% | 0,0387 |
| Logistic stacking | **0,9895** | 0,9911 | 3,68% | **94,84%** | 0,0506 |
| PID P v2 | 0,9881 | 0,9903 | **2,79%** | 93,99% | 0,0479 |
| PID full v2 | 0,9893 | 0,9909 | 4,68% | 94,66% | 0,0400 |
| **Robust PID v2** | **0,9895** | **0,9911** | 3,35% | 94,32% | 0,0408 |

Robust PID v2 so với:

- Average: ΔAUC +0,0003 và ΔFPR −0,99 pp; cả hai CI đi qua 0.
- Logistic stacking: ΔAUC xấp xỉ 0, CI [−0,0008; +0,0008]; ΔFPR −0,32 pp, CI đi qua 0.
- Max-risk: ΔAUC +0,0029 và ΔFPR −3,56 pp; CI loại 0.
- PID full v2: ΔFPR −1,33 pp; CI [−2,66; −0,15].

Diễn giải đúng: Robust PID v2 là ứng viên thuật toán cạnh tranh với stacking và cải thiện controller v2 cũ, chưa phải external confirmation.

### 5.5. Stateful residual PID dưới controlled stress — exploratory

So với Temporal stacking:

- Clean: FPR 3,47% so với 4,29%; TPR 94,17% so với 94,34%.
- Delay 5 events: FPR 2,61% so với 3,93%; TPR 94,49% so với 94,66%.
- Dưới delay, PID loại 8 FP, tạo 0 FP mới và mất 1 TP; Holm-adjusted p=0,0312.
- Ba trong năm folds chọn gain=0.
- Event-AULC và Early-AUC không cải thiện.

Chỉ dùng kết quả này để nói residual PID có thể giảm FP dưới một stress được kiểm soát. Không được suy rộng thành robustness ngoài đời hoặc superiority toàn diện.

### 5.6. Claim cuối cho RQ1

Phát biểu nên dùng:

> Reliability-aware adaptive P improved FPR and Brier over fixed weighting on the development cohort, while retaining comparable TPR. Full PID achieved ranking performance comparable to logistic stacking and a lower FPR at its validation-selected operating point, but the I and D components did not provide consistent incremental benefit over P within the examined event horizon.

Không dùng:

- Full PID significantly outperforms all fusion methods.
- D improves early detection.
- PID handles sleep evasion.
- PID reduces wall-clock detection latency.
- PID has been externally validated.

---

## 6. Kết quả xác nhận cho RQ2

Thiết kế: 5 outer folds × 5 AL seeds; 200 nhãn ban đầu; 10 vòng × 100 nhãn; cùng initial set theo fold/seed; validation/test không vào query pool; target xác định trên validation.

| Phương pháp | ROC-AULC | AP-AULC | Nhãn tới target | Query/10 vòng | Model + query |
|---|---:|---:|---:|---:|---:|
| Random | 0,928777 | 0,868350 | 584 | 0,0194 s | 4,1947 s |
| Uncertainty | 0,931272 | 0,881934 | 520 | 0,0191 s | 4,1454 s |
| **U+H** | **0,933026** | **0,883336** | 508 | 0,2459 s | 4,4741 s |
| U+V | 0,930377 | 0,880164 | **488** | 0,2298 s | 4,3826 s |
| XAI-full | 0,932202 | 0,881638 | 492 | 0,2358 s | 4,3471 s |

Hiệu ứng ghép cặp:

- U+H vs Random: ΔROC-AULC +0,004249; ΔAP-AULC +0,014985; thắng 5/5 folds; giảm 76 nhãn hay 13,0%.
- U+H vs Uncertainty: ΔROC-AULC +0,001754; ΔAP-AULC +0,001401; thắng 4/5 folds; hiệu ứng nhỏ.
- XAI-full vs Random: ΔROC-AULC +0,003425; ΔAP-AULC +0,013287; thắng 5/5 folds; giảm 92 nhãn hay 15,8%.
- XAI-full vs Uncertainty: ΔROC-AULC +0,000931; ΔAP-AULC −0,000297; giảm trung bình 28 nhãn nhưng không thắng nhất quán.

Vùng FPR thấp:

| Phương pháp | pAUC FPR≤5% | TPR-AULC cap 1% | TPR-AULC cap 5% |
|---|---:|---:|---:|
| Random | 0,804096 | 0,580620 | 0,731980 |
| Uncertainty | **0,826300** | **0,638180** | 0,769260 |
| U+H | 0,824774 | 0,636780 | 0,770620 |
| U+V | 0,825194 | 0,626260 | 0,768140 |
| XAI-full | 0,823525 | 0,631860 | **0,771460** |

Overhead:

- U+H tổng model+query cao hơn Uncertainty khoảng 7,93%.
- XAI-full cao hơn Uncertainty khoảng 4,86%.
- Query của XAI-full chiếm khoảng 5,42% model+query.

Claim cuối cho RQ2:

> Explanation-derived signals improved learning-curve quality and label efficiency over random sampling. Directional Entropy produced the strongest AULC, whereas the variance-based variant reached the validation target with the fewest labels. Gains over uncertainty sampling were smaller and metric-dependent.

Không quy đổi label savings thành analyst hours nếu chưa đo thời gian gán nhãn thật.

---

## 7. Kết quả xác nhận cho RQ3

Thiết kế: 5 folds × 5 model seeds × 2 baselines; k ∈ {10,25,50}; 20 random masks cho mỗi k và fitted model; 50/50 verification pass.

| Baseline | k | AUC drop top-SHAP | AUC drop random | Top − random |
|---|---:|---:|---:|---:|
| Mean | 10 | 0,047817 | 0,000200 | 0,047617 |
| Mean | 25 | 0,135853 | 0,000530 | 0,135323 |
| Mean | 50 | **0,306729** | 0,000979 | **0,305750** |
| Median | 10 | 0,053483 | 0,000094 | 0,053388 |
| Median | 25 | 0,125180 | 0,000326 | 0,124854 |
| Median | 50 | **0,300777** | 0,000658 | **0,300119** |

Stability:

| Phạm vi | Spearman | Jaccard top-10 | top-25 | top-50 |
|---|---:|---:|---:|---:|
| Khác seed, cùng fold | 0,6144 | 0,6221 | 0,5398 | 0,4901 |
| Khác fold | 0,5512 | 0,4416 | 0,3073 | 0,3020 |

Max SHAP additivity error xấp xỉ 6×10⁻¹⁵. OFS không được tổng hợp vì các thành phần không có cùng scale và chưa có trọng số validation.

Claim cuối cho RQ3:

> Features ranked highly by TreeSHAP caused substantially larger model-performance degradation than equal-budget random features under both mean and median replacement. Ranking stability was moderate and decreased across data folds, supporting model faithfulness while exposing sensitivity to data partitioning.

Không được viết:

- SHAP proves causal malware features.
- Masked vectors correspond to valid executable PE files.
- OFS proves explanation correctness.
- 307× là universal effect size; nếu dùng tỷ lệ này phải ghi rõ mẫu số random gần 0. Trong paper nên ưu tiên chênh lệch tuyệt đối 0,305750.

---

## 8. Cách thống nhất ba đóng góp trong paper

Mạch học thuật nên dùng:

1. **Decision stage:** bằng chứng tĩnh và động có ưu/nhược khác nhau; adaptive fusion xử lý bất đồng theo chuỗi.
2. **Adaptation stage:** không thể gán nhãn toàn bộ pool; explanation-guided acquisition ưu tiên mẫu có giá trị.
3. **Audit stage:** explanation dùng cho lựa chọn và hỗ trợ chuyên gia phải được kiểm chứng bằng deletion/stability.

Đây là ba thành phần của một vòng phân tích có khả năng audit. Tuy nhiên:

- Fusion và AL/Fidelity được đo trên hai benchmark khác nhau.
- Chưa có thí nghiệm AL × fusion.
- Chưa có latency/cost end-to-end.
- Không được dùng cụm complete integrated pipeline outperforms baselines.

Trong Introduction, câu chuyện doanh nghiệp không nên trở thành case study. Nếu giữ, chỉ dùng một câu motivation và không gán nguyên nhân sự cố cho việc thiếu PID/AL/Fidelity.

---

## 9. Ma trận claim cho manuscript

### 9.1. Có thể đặt trong abstract và conclusion

- On an identity-verified EMBER subset, explanation-guided sampling improved ROC/AP learning-curve area over random acquisition.
- XAI-full reduced the mean label budget by 92 samples relative to random at the predeclared validation target.
- Top-|SHAP| deletion produced substantially larger AUC degradation than equal-budget random deletion under mean and median baselines.
- On a paired MalBehavD-V1 cohort, adaptive P reduced FPR and Brier relative to fixed weighting with paired-bootstrap intervals excluding zero.
- Full PID obtained AUC comparable to logistic stacking, while component ablation found no consistent incremental benefit from I/D over P.

### 9.2. Chỉ đặt trong Results/Discussion với nhãn development hoặc exploratory

- Robust PID v2 matched Logistic stacking in AUC/AP on the horizon-40 development cohort.
- Gated residual PID reduced false positives under controlled delay stress.
- Real timestamp extraction is feasible from a small Cuckoofork pilot.

### 9.3. Không được viết như kết luận

- The method detects ransomware or zero-day ransomware.
- Full PID is superior to all fusion baselines.
- The D term improves detection.
- The method handles sleep evasion.
- The framework is production-ready.
- The complete three-stage system was evaluated end-to-end.
- XAI-full is universally the best acquisition method.
- Label reduction equals analyst-time reduction.
- SHAP explanations are causal.

---

## 10. Cấu trúc bài báo cần viết lại

### 10.1. Abstract

Abstract cần có:

1. Bài toán: kết hợp bằng chứng, ngân sách nhãn và độ tin cậy explanation.
2. Ba research questions, mô tả ngắn gọn.
3. Hai benchmark và ghi rõ component-wise evaluation.
4. Ba kết quả chính:
   - Adaptive P vs Fixed: −1,28 pp FPR, CI loại 0.
   - XAI-full vs Random: −92 nhãn, −15,8%; U+H AULC tốt nhất.
   - Mean top-50 SHAP deletion: 0,306729 vs 0,000979 random.
5. Giới hạn: generic Windows malware, không phải ransomware-specific; chưa external/end-to-end.

Không đưa Robust PID v2 vào abstract như kết quả xác nhận.

### 10.2. Introduction

Đề xuất bốn đoạn:

1. Malware detection cần ra quyết định từ bằng chứng không đồng nhất và cập nhật dưới ngân sách chuyên gia hữu hạn.
2. Fixed fusion, uncertainty-only acquisition và explanation visualization để lại ba khoảng trống.
3. Nêu RQ1–RQ3 và vì sao chúng tạo thành một vòng auditable adaptation.
4. Liệt kê đóng góp với đúng phạm vi bằng chứng.

### 10.3. Related Work

- Static/dynamic Windows malware detection.
- Score-level fusion và learned stacking.
- Active learning cho malware/tabular security.
- SHAP-guided sampling.
- Feature-attribution faithfulness/stability trên tabular data.

Related Work phải trả lời rõ PID đã được dùng ở đâu trong control/fusion và phần nào là ánh xạ mới của nghiên cứu.

### 10.4. Method

Tách ba module:

1. Reliability-aware adaptive fusion, công thức P/I/D và clip.
2. U, Directional Entropy H, SHAP Variance V và acquisition scores.
3. Deletion controls, train-derived baselines và rank stability.

Không mô tả PID như một controller có plant vật lý hoặc có bảo đảm ổn định nếu chưa chứng minh.

### 10.5. Experimental Protocol

Tách rõ hai benchmark:

- EMBER: AL/Fidelity.
- MalBehavD-V1: fusion.

Báo provenance, label semantics, split, seed, validation-only selection, threshold objective, paired bootstrap và artifact verification.

### 10.6. Results

Thứ tự:

1. RQ1 fusion-only baselines và P/PI/PID ablation.
2. RQ2 AULC, label budget, low-FPR và overhead.
3. RQ3 deletion, baseline sensitivity và stability.
4. Exploratory robustness/PID v2 ở subsection riêng, có nhãn rõ.

### 10.7. Discussion và Threats to Validity

Bắt buộc bàn:

- Hai benchmark không tạo thành end-to-end evaluation.
- Generic malware labels.
- Same-cohort method development cho fusion mới.
- Source bias và metadata availability.
- Random-row EMBER split.
- Masking có thể tạo vector ngoài phân phối.
- Label savings chưa phải analyst-hour savings.
- D chưa có bằng chứng độc lập.

---

## 11. Bảng và hình bắt buộc

### Main paper

1. Bảng dataset/provenance/label semantics.
2. Bảng fusion-only gồm Average, Max-risk, Fixed, Logistic stacking, P, PI, PID.
3. Forest plot hoặc bảng paired effects Adaptive P−Fixed và PID−Stacking.
4. Learning curves theo label budget.
5. Bảng AULC, labels-to-target và overhead.
6. Deletion plot top-SHAP vs random cho mean/median.
7. Rank-stability plot trong fold và giữa fold.

### Supplementary

1. Confirmatory P/PI/PID component ablation.
2. Robust PID v2 horizon-40 table.
3. Controlled stress table.
4. Timestamp pilot coverage.
5. Full configuration, hash và verification map.

Không dùng dashboard hoặc case study giả định làm bằng chứng.

---

## 12. Artifact map

### Dữ liệu và identity

- results/confirmatory_20261019_ember_identity/static_identity_audit.json
- results/confirmatory_20261019_ember_identity/SHA256SUMS
- results/measured_20261023_malbehavd_pid_confirmatory_1922/selected_cohort.csv
- results/measured_20261023_malbehavd_pid_confirmatory_1922/SOURCE_FILES.json

### Active Learning

- results/confirmatory_20261019_ember_identity/al/aulc_summary.csv
- results/confirmatory_20261019_ember_identity/al/target_reach_summary.csv
- results/confirmatory_20261019_ember_identity/al/fold_level_effects.csv
- results/confirmatory_20261019_ember_identity/al/low_fpr_aulc_by_fold.csv
- results/confirmatory_20261019_ember_identity/al/overhead_by_fold.csv
- results/confirmatory_20261019_ember_identity/al/learning_curves.png
- results/confirmatory_20261019_ember_identity/al/verification.json

### Fidelity

- results/confirmatory_20261019_ember_identity/fidelity/deletion_summary.csv
- results/confirmatory_20261019_ember_identity/fidelity/shap_stability_summary.csv
- results/confirmatory_20261019_ember_identity/fidelity/model_deletion_comparisons.csv
- results/confirmatory_20261019_ember_identity/fidelity/deletion_effect.png
- results/confirmatory_20261019_ember_identity/fidelity/shap_stability.png
- results/confirmatory_20261019_ember_identity/fidelity/verification.json

### Fusion confirmatory

- results/measured_20261023_malbehavd_pid_confirmatory_1922/fusion_summary.csv
- results/measured_20261023_malbehavd_pid_confirmatory_1922/paired_bootstrap_pid_minus_fixed.json
- results/measured_20261023_malbehavd_pid_confirmatory_1922/d_component_ablation.json
- results/measured_20261023_malbehavd_pid_confirmatory_1922/d_component_verification.json
- results/measured_20261023_malbehavd_pid_confirmatory_1922/verification.json

### Fusion mới

- results/measured_20261028_fusion_only_evidence_1922/FUSION_ONLY_EVIDENCE_VI.md
- results/measured_20261028_fusion_only_evidence_1922/fusion_only_summary.json
- results/exploratory_20261028_pid_v2_meta_fusion_horizon40/REPORT_VI.md
- results/exploratory_20261028_pid_v2_meta_fusion_horizon40/summary.json
- results/exploratory_20261028_stateful_gated_residual_pid_horizon40/REPORT_VI.md
- results/exploratory_20261028_pid_evidence_upgrade_horizon40/REPORT_VI.md

### Timestamp pilot

- results/measured_20261028_vt_behaviour_pilot20/REPORT_VI.md
- results/measured_20261028_vt_behaviour_pilot20/event_extraction_summary.json
- results/measured_20261028_vt_behaviour_pilot20/event_sequence_audit.csv

---

## 13. Việc còn thiếu trước khi gửi paper

### Bắt buộc nếu muốn claim PID mạnh

1. Khóa Robust PID v2 trước khi lấy dữ liệu mới.
2. Chạy external hoặc temporal cohort chưa dùng để phát triển.
3. Đăng ký metric chính và non-inferiority/superiority margin trước khi chạy.
4. Báo cùng operating target khi so sánh FPR/TPR.

### Nên làm cho AL/Fidelity

1. Thêm uncertainty + diversity/k-center hoặc query-by-committee.
2. Sensitivity theo trọng số U/H/V và normalization.
3. Family-disjoint hoặc temporal split nếu dữ liệu cho phép.
4. Group-aware hoặc conditional masking theo nhóm PE.
5. So sánh ít nhất một explainer khác nếu venue yêu cầu.

### Bắt buộc về viết

1. Không dùng ransomware trong title/abstract nếu không có ransomware ground truth.
2. Phân biệt confirmatory, development và exploratory ở caption/table.
3. Không gọi two-dataset component evaluation là end-to-end.
4. Công bố negative result của D; không giấu ablation bất lợi.
5. Giữ toàn bộ con số nhất quán với artifact map.

---

## 14. Yêu cầu dành cho thread viết lại paper

Sử dụng nguyên văn yêu cầu dưới đây khi chuyển sang thread viết paper:

> Hãy viết lại toàn bộ bài báo dựa trên file PAPER_EVIDENCE_AND_READINESS_REPORT_20261021.md cập nhật ngày 30/10/2026 và các artifact được liệt kê trong mục Artifact map.
>
> Bài báo phải trình bày ba research questions: reliability-aware static–dynamic fusion, explanation-guided active learning và quantitative TreeSHAP validation. Hãy thống nhất chúng dưới chủ đề auditable adaptive learning for Windows malware detection.
>
> Phải mô tả đây là component-wise evaluation trên hai benchmark bổ sung cho nhau: EMBER cho AL/Fidelity và MalBehavD-V1 cho fusion. Không được viết như một end-to-end experiment trên cùng cohort.
>
> Với PID, dùng kết quả fusion-only 1.922 mẫu làm bảng so sánh chính, nhưng ghi rõ đây là development evidence sau confirmatory trên cùng cohort. Claim chính là Adaptive P cải thiện Fixed về FPR/Brier; Full PID có AUC tương đương Logistic stacking và FPR thấp hơn tại operating point đã chọn, có đánh đổi TPR. Báo rõ I/D chưa tạo lợi ích ổn định. Robust PID v2 và stress tests chỉ đặt trong exploratory subsection hoặc supplementary.
>
> Với Active Learning, dùng kết quả confirmatory 5 folds × 5 seeds. U+H là cấu hình có AULC tốt nhất; U+V cần ít nhãn nhất; XAI-full giảm 92 nhãn hay 15,8% so với Random. Không nói XAI-full tốt nhất mọi chỉ số và không quy đổi nhãn thành analyst hours.
>
> Với Fidelity, dùng deletion top-|SHAP| so với equal-budget random dưới mean/median và rank stability. Ưu tiên báo chênh lệch tuyệt đối thay vì nhấn mạnh tỷ lệ 307×. Không khẳng định quan hệ nhân quả hoặc PE validity của masked vectors. Không dùng OFS.
>
> Abstract, Results và Conclusion chỉ được dùng claim trong mục Ma trận claim. Phải có riêng Threats to Validity, Data/Label Semantics và Confirmatory-versus-Exploratory Status.
>
> Không dùng từ ransomware hoặc zero-day như kết quả đã chứng minh. Không dùng câu full PID outperforms all baselines. Không dùng sự cố doanh nghiệp như bằng chứng; nếu nhắc thì chỉ một câu motivation không có chi tiết nhận dạng.
>
> Trước khi viết prose, hãy tạo: (1) title và abstract mới; (2) outline chi tiết; (3) bảng mapping từng claim tới artifact; (4) danh sách bảng/hình cần sinh. Sau đó viết paper theo thứ tự Introduction, Related Work, Method, Experimental Protocol, Results by RQ, Discussion, Threats to Validity, Conclusion.

---

## 15. Checklist kiểm tra bản thảo sau khi viết

- [ ] Title không tuyên bố ransomware-specific.
- [ ] Abstract ghi component-wise evaluation.
- [ ] RQ1/RQ2/RQ3 xuất hiện rõ.
- [ ] EMBER và MalBehavD-V1 có label semantics riêng.
- [ ] Adaptive P−Fixed có CI chính xác.
- [ ] PID−Stacking có cả FPR, AUC và TPR trade-off.
- [ ] D negative result được báo.
- [ ] AL báo cả Random và Uncertainty.
- [ ] AL không chọn một phương pháp thắng mọi metric.
- [ ] Fidelity có mean/median, random control và stability.
- [ ] OFS không xuất hiện như composite score.
- [ ] Robust PID v2 được gắn nhãn exploratory.
- [ ] Timestamp pilot không bị diễn giải thành performance evidence.
- [ ] Không có claim end-to-end.
- [ ] Không có claim ransomware/zero-day/production-ready.
- [ ] Mọi bảng/hình truy ngược được tới artifact.
