# Kế hoạch phát triển bài báo khoa học hoàn chỉnh

> **Trạng thái 2026-10-19:** Master manuscript Track B đã hoàn thành tại
> `docs/paper/main.tex`, gồm khoảng 10.400 từ và 22 trang trong bản dựng kiểm tra
> hai cột. Các mục còn lại trước khi nộp là xác nhận metadata/tư cách tác giả,
> kiểm tra thư mục tài liệu tham khảo bằng DOI/publisher record, build bằng
> template chính thức của tạp chí đích, và bổ sung dữ liệu động thật nếu muốn
> nâng PID từ protocol thành đóng góp thực nghiệm.

## 1. Mục tiêu và chiến lược xuất bản

Mục tiêu là xây dựng một **master manuscript 20–26 trang** từ luận văn, đủ chi
tiết để phản biện kỹ thuật có thể truy vết phát biểu, công thức, cấu hình và bằng
chứng. Bản master dùng `IEEEtran`; trước khi nộp phải tạo một bản submission
riêng tuân thủ đúng giới hạn trang và template mới nhất của tạp chí đích.

Định hướng tạp chí:

1. **IEEE Transactions on Information Forensics and Security (TIFS)** là lựa
   chọn ưu tiên nếu hoàn tất provenance của dữ liệu, thực nghiệm PID trên tín
   hiệu động thật và đánh giá ngoài miền. Bản 20–26 trang không nên được nộp
   nguyên trạng nếu vượt giới hạn hiện hành của tạp chí.
2. **Computers & Security** là lựa chọn dự phòng phù hợp với một bài thiên về
   hệ thống và đánh giá thực nghiệm. Khi chọn tạp chí này phải chuyển từ
   `IEEEtran` sang template Elsevier; nội dung khoa học và claim–evidence map
   được giữ nguyên.

Không thể bảo đảm bài được nhận. Kế hoạch này tập trung loại bỏ các lý do từ
chối dễ dự đoán: claim vượt bằng chứng, dữ liệu không truy nguyên, thiếu baseline,
đánh giá PID bằng tín hiệu mô phỏng, Related Work hời hợt, và thiếu threats to
validity.

## 2. Tác giả

Thứ tự tác giả dự kiến:

1. **Luu Van Doanh** — first author.
2. **Truong Ninh Thuan** — supervisor/co-author.

Trước khi nộp cần xác nhận bằng văn bản với thầy hướng dẫn:

- đồng ý làm đồng tác giả và thứ tự tác giả;
- tên tiếng Anh chính thức;
- affiliation tiếng Anh;
- institutional email;
- ORCID;
- CRediT author contributions;
- corresponding author.

Không ghi `PGS.TS.` hoặc `Assoc. Prof. Dr.` trong dòng tên tác giả. Học hàm có
thể xuất hiện trong hồ sơ tác giả nếu tạp chí yêu cầu, không đặt trong byline.

## 3. Quyết định phạm vi trước khi viết toàn văn

### Track A — Bài đầy đủ ba đóng góp

Giữ tiêu đề hiện tại và trình bày PID, Active Learning, Fidelity như ba đóng góp
thực nghiệm. Track này chỉ đủ điều kiện khi có:

- cặp `p_static`–`p_dynamic` truy nguyên tới cùng mẫu/phiên quan sát;
- báo cáo động thật và SHA-256 cho từng quan sát;
- ablation Static, Dynamic, Average, Fixed, P, PI, PID trên cùng test;
- gain, trọng số và threshold chọn trên validation;
- latency tách thành signal collection, feature extraction, inference, fusion và
  end-to-end;
- ma trận 2×2 `Random/XAI_full × Fixed/PID` nếu tuyên bố hiệu ứng kết hợp;
- provenance và ý nghĩa nhãn ransomware được xác minh.

### Track B — Bài trung thực với bằng chứng hiện có

Trọng tâm là **XAI-guided Active Learning và controlled fidelity verification**;
PID chỉ là kiến trúc đề xuất và protocol đánh giá. Track này cần đổi tiêu đề để
không khiến phản biện hiểu rằng hiệu quả PID đã được chứng minh, ví dụ:

> Explanation-Guided Active Learning and Controlled Fidelity Evaluation for
> Static PE Malware Detection

Track B có thể hoàn thiện từ artifact hiện tại nhưng vẫn cần mô tả dataset đúng
phạm vi: pilot 2.000 dòng, 2.381 đặc trưng, provenance upstream và ý nghĩa nhãn
ransomware-specific chưa được xác minh. Không gọi kết quả là benchmark SOREL,
family-held-out, temporal hoặc zero-day nếu chưa có manifest hỗ trợ.

## 4. Cấu trúc và ngân sách trang

Ngân sách dưới đây dành cho master manuscript hai cột, mục tiêu khoảng 22–26
trang gồm tài liệu tham khảo. Appendix dài và artifact manifest có thể tách sang
supplementary material khi nộp.

| Phần | Nội dung chính | Ngân sách |
|---|---|---:|
| Front matter | Title, authors, abstract, keywords | 0.5 trang |
| I. Introduction | Bối cảnh, vấn đề, research gap, contributions, cấu trúc bài | 1.5–2 trang |
| II. Related Work | Static/dynamic, hybrid fusion, AL, XAI security, fidelity | 2.5–3 trang |
| III. Problem Formulation and Threat Model | Ký hiệu, assumptions, attacker, scope, research questions | 1–1.5 trang |
| IV. Proposed Methodology | Architecture, gate, PID, AL query, fidelity metrics | 4–5 trang |
| V. Experimental Methodology | Data audit, split, baselines, metrics, implementation, verification | 2.5–3 trang |
| VI. Results | AL, fidelity và PID chỉ khi đủ dữ liệu | 4–5 trang |
| VII. Discussion | Cơ chế, ý nghĩa thực tế, failure cases, cost | 1.5–2 trang |
| VIII. Threats to Validity | Internal, construct, external, statistical validity | 1–1.5 trang |
| IX. Conclusion | Kết luận đúng phạm vi và hướng tiếp theo | 0.5–0.75 trang |
| References | 45–70 nguồn được kiểm tra | 2–3 trang |
| Appendix/Supplement | Pseudocode, hyperparameters, extra tables, artifact map | 2–4 trang |

## 5. Đặc tả từng phần

### I. Introduction

- Mở bằng trade-off giữa quyết định sớm và bằng chứng hành vi đến muộn.
- Giải thích ba vấn đề độc lập: fusion, chi phí nhãn, fidelity của lời giải thích.
- Không đồng nhất malware detection với ransomware detection khi nhãn chưa xác
  minh.
- Kết thúc bằng research questions có thể kiểm định:
  - **RQ1:** tín hiệu explanation có cải thiện query selection so với uncertainty?
  - **RQ2:** top-SHAP deletion có ảnh hưởng model lớn hơn random control cùng
    ngân sách?
  - **RQ3:** PID có cải thiện fusion trên cặp tín hiệu động thật so với baseline
    đơn giản? Chỉ trả lời nếu Track A hoàn tất.
- Contributions phải nêu rõ cái gì là phương pháp, cái gì đã đo và phạm vi dữ
  liệu.

### II. Related Work

Tổ chức theo vấn đề thay vì liệt kê từng bài:

1. Static PE malware/ransomware detection.
2. Dynamic analysis, sandbox evasion và delayed execution.
3. Hybrid/static–dynamic fusion và adaptive decision mechanisms.
4. Active learning cho malware và query-by-uncertainty/diversity.
5. XAI cho cybersecurity và các phê bình về explanation robustness.
6. Fidelity metrics, perturbation tests và vấn đề input validity.

Cần một bảng so sánh 10–15 công trình gần nhất theo các cột: data provenance,
static/dynamic, AL, explanation method, quantitative fidelity, random control,
external validation, artifact availability. Mỗi phát biểu novelty phải dựa trên
bảng này, không dùng câu “first” nếu chưa có systematic search hỗ trợ.

### III. Problem Formulation and Threat Model

- Định nghĩa vector PE, static score, dynamic score, pool AL, SHAP vector và
  label budget.
- Phân biệt model output, calibrated probability và risk score.
- Nêu attacker capabilities: packing, obfuscation, delayed/sleep execution,
  environment awareness; không tuyên bố chống mọi adaptive attacker.
- Nêu defender assumptions: Windows PE scope, availability of static features,
  conditional dynamic analysis, oracle labels.
- Định nghĩa rõ các research hypotheses và metric tương ứng.

### IV. Proposed Methodology

#### IV-A. Overall architecture and uncertainty gate

- Vẽ luồng từ PE → static LightGBM → uncertainty gate → dynamic observation →
  fusion → decision → explanation/AL loop.
- Phân biệt latency của gate, dynamic observation và fusion update.
- Có pseudocode tổng thể và phân tích độ phức tạp.

#### IV-B. Adaptive PID fusion

- Thống nhất dấu của sai lệch với implementation.
- Định nghĩa P, I, D, state reset, clipping và mapping sang `w_static`.
- Giải thích khi nào I/D có ý nghĩa; một quan sát độc lập cho mỗi session không
  chứng minh lợi ích lịch sử.
- Không dùng số AUC/FPR/latency cũ trong Results cho đến khi có artifact hợp lệ.

#### IV-C. XAI-guided Active Learning

- Định nghĩa `U`, Directional Entropy và SHAP Variance đúng với code.
- Nêu min–max normalization trên pool của từng vòng.
- Khóa trọng số full policy: `U=0.3`, `H=0.4`, `V=0.3` nếu tiếp tục dùng cấu
  hình đã đo.
- Thêm Algorithm 1 cho query–label–retrain cycle.

#### IV-D. Controlled fidelity framework

- Baseline hiện tại là **training-column arithmetic mean**, không phải median.
- Giải thích top-`|SHAP|` mask và 20 random masks cùng `k`.
- Báo FF, EC và CF riêng; không tổng hợp OFS khi chưa có normalization/weights
  được kiểm định.
- Nêu rõ deletion diễn ra trong feature space và chưa chứng minh có PE hợp lệ
  tương ứng.

### V. Experimental Methodology

- Dataset card: nguồn, license, collection period, class meaning, extraction
  version, hashes, duplicates, family/time metadata.
- Split card: train pool 1.200, validation 400, test 400 cho pilot hiện tại;
  class counts và seed.
- AL: 200 initial labels, 5 rounds × 100 queries, final budget 700, five paired
  seeds, fixed test, threshold chosen on validation for target TPR 0.95.
- Fidelity: model riêng, 400 test rows, `k={10,25,50}`, 20 random masks,
  bootstrap 500.
- Baselines và ablations phải dùng chung split, budget và evaluation policy.
- Ghi software versions, hardware, CPU threads, runtime scope và artifact hashes.
- Trình bày verifier replay: 150 checkpoints, 120.000 AL predictions, 12.500
  queries, 63 mask batches và 25.200 Fidelity predictions.

### VI. Results

#### VI-A. Active Learning

- Bảng mean ± SD cho AUC, AP, FPR và TPR.
- Learning curves và area under learning curve.
- Paired differences theo seed; nhấn mạnh AUC của `XAI_full` cao hơn
  `Uncertainty` ở 5/5 seed.
- Không tuyên bố FPR giảm ổn định: chỉ tốt hơn ở 2/5 seed.
- Không quy đổi sang số giờ/chi phí chuyên gia nếu chưa đo.

#### VI-B. Fidelity

- Baseline AUC 0.980167.
- Top-SHAP AUC sau che: 0.913933, 0.818533, 0.671200 tại k=10,25,50.
- Random control tương ứng xấp xỉ 0.98.
- Ở k=25, AUC drop 0.161633 so với random mean 0.000257, khoảng 630 lần.
- Báo bootstrap interval, probability change, actual changed coordinates, EC và
  CF cùng giới hạn diễn giải.

#### VI-C. PID fusion

- Track A: báo full ablation, achieved TPR cạnh FPR, paired differences và
  latency decomposition.
- Track B: không tạo bảng kết quả; chỉ mô tả protocol và lý do chưa đánh giá.

### VII. Discussion

- Tại sao H và V có thể bổ sung cho U.
- Khi nào explanation conflict hữu ích, khi nào chỉ phản ánh correlation/noise.
- Tách statistical improvement khỏi operational benefit.
- Phân tích failure cases và negative results.
- Nêu chi phí SHAP/query scoring, khả năng triển khai và attack surface.

### VIII. Threats to Validity

- **Construct validity:** nhãn ransomware chưa xác minh; SHAP fidelity không
  tương đương causal explanation.
- **Internal validity:** model Fidelity khác model AL; threshold và split policy;
  feature-space masking.
- **External validity:** chỉ một bảng dữ liệu cục bộ; thiếu family-held-out,
  temporal và cross-dataset evaluation được truy nguyên.
- **Statistical conclusion validity:** năm seed dùng chung test; SD không phải
  population confidence interval; EC pairs không độc lập.
- **Operational validity:** chưa có end-to-end PID latency trên động thật.

## 6. Danh mục hình và bảng tối thiểu

### Hình

1. Overall multi-stage architecture and data flow.
2. Uncertainty gate and static–dynamic timing diagram.
3. XAI-guided AL loop.
4. Learning curves by method.
5. Paired AUC/FPR differences across seeds.
6. Fidelity deletion curves: top-SHAP vs random.
7. Traceable local SHAP example.
8. PID ablation/latency figure, chỉ khi Track A có dữ liệu hợp lệ.

### Bảng

1. Related-work comparison and research gap.
2. Dataset/split/class distribution and provenance status.
3. Model and experiment hyperparameters.
4. Final AL results at 700 labels.
5. Paired AL comparison and win counts.
6. Fidelity results for k=10/25/50.
7. Component definitions, ranges and interpretation limits.
8. PID ablation and latency decomposition, chỉ cho Track A.
9. Claim–evidence map trong appendix/supplement.

Không lặp lại cùng số liệu trong cả bảng và hình nếu không phục vụ hai câu hỏi
khác nhau.

## 7. Chiến lược tài liệu tham khảo

- Mục tiêu 45–70 nguồn, ưu tiên 2019–2026 và các nguồn nền tảng bắt buộc.
- Ít nhất 60% nguồn từ journal/conference peer-reviewed; hạn chế arXiv khi đã có
  bản xuất bản.
- Bao phủ: ransomware behavior, PE malware detection, EMBER/SOREL, hybrid
  analysis, sandbox evasion, Active Learning, SHAP/TreeSHAP, security XAI
  evaluation, fidelity/perturbation validity và reproducible ML security.
- Xác minh từng DOI, venue, year, volume/pages và tránh citation không đọc.
- Related Work phải có nguồn gần đây từ chính tạp chí đích.

## 8. Quy trình triển khai

### Milestone 0 — Chốt scope và authorship

- Chọn Track A hoặc Track B.
- Chọn tạp chí ưu tiên.
- Xác nhận metadata của hai tác giả.
- Khóa claim–evidence map.

### Milestone 1 — Evidence readiness

- Hoàn thiện dataset provenance/label definition hoặc chấp nhận scope pilot.
- Với Track A, hoàn tất dynamic observations và PID ablation.
- Xác minh mọi bảng/hình từ artifact, không nhập số thủ công.

### Milestone 2 — Methodology and protocol

- Viết Sections III–V.
- Đồng bộ công thức với code.
- Hoàn thiện architecture figure, algorithms và hyperparameter tables.

### Milestone 3 — Results and discussion

- Viết Section VI từ artifact chuẩn.
- Thêm effect sizes, paired comparisons, intervals và negative results.
- Viết Discussion và Threats to Validity trước khi sửa Abstract.

### Milestone 4 — Literature and positioning

- Systematic search log.
- Related-work matrix.
- Hoàn thiện BibTeX và kiểm tra citation coverage.

### Milestone 5 — Submission-quality revision

- Kiểm tra consistency của title/abstract/contributions/results/conclusion.
- Language edit theo academic English, bỏ marketing claims.
- Kiểm tra figure fonts, grayscale, caption self-containment và table width.
- Chạy plagiarism/self-overlap review và kiểm tra quyền sử dụng hình.
- Chuẩn bị cover letter, highlights, graphical abstract hoặc supplementary theo
  yêu cầu tạp chí.

### Milestone 6 — Internal review

- Vòng 1: technical correctness.
- Vòng 2: adversarial reviewer review.
- Vòng 3: supervisor approval và authorship sign-off.
- Vòng 4: journal compliance checklist và final PDF inspection.

## 9. Quality gates trước khi nộp

Bài chỉ được đánh dấu submission-ready khi tất cả mục áp dụng đều đạt:

- [ ] Tiêu đề không hứa nhiều hơn bằng chứng.
- [ ] Tên, affiliation, email, ORCID và author order đã xác nhận.
- [ ] Mỗi claim định lượng trỏ tới artifact và script tái tính.
- [ ] Dataset provenance/label scope được mô tả trung thực.
- [ ] Không dùng 20.000 mẫu khi run được xác minh chỉ có 2.000 dòng.
- [ ] Không dùng PID AUC/FPR/latency cũ nếu chưa có dynamic evidence.
- [ ] Không gọi training-mean masking là median masking.
- [ ] Không báo OFS khi chưa có aggregation rule hợp lệ.
- [ ] AL so sánh paired trên cùng seed/split/budget.
- [ ] FPR luôn đi cùng achieved TPR và threshold-selection policy.
- [ ] Fidelity có random control cùng k và nêu feature-space limitation.
- [ ] Có Threats to Validity độc lập.
- [ ] Reference metadata được xác minh.
- [ ] Figures/tables có thể đọc ở kích thước hai cột.
- [ ] LaTeX build sạch, không undefined references/citations.
- [ ] Template và page limit khớp hướng dẫn mới nhất của journal.
- [ ] Thầy hướng dẫn duyệt bản cuối trước submission.

## 10. Đầu ra cuối cùng

Repository nên có:

```text
docs/paper/
├── main.tex
├── sections/
│   ├── 01_introduction.tex
│   ├── 02_related_work.tex
│   ├── 03_problem_threat_model.tex
│   ├── 04_methodology.tex
│   ├── 05_experimental_methodology.tex
│   ├── 06_results.tex
│   ├── 07_discussion.tex
│   ├── 08_threats_to_validity.tex
│   └── 09_conclusion.tex
├── figures/
├── tables/
├── references.bib
├── supplementary.tex
├── CLAIM_EVIDENCE_MAP.csv
├── COVER_LETTER.md
└── releases/
    ├── manuscript.pdf
    ├── source.zip
    └── SHA256SUMS
```

Phase 1 hiện có sẽ được tách sang cấu trúc này khi bắt đầu triển khai toàn văn.
