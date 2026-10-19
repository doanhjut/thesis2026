# Kế hoạch hoàn thiện bài báo Multi-Stage

## 1. Mục tiêu

Mục tiêu là phát triển bài báo thành một nghiên cứu hệ thống nhiều giai đoạn có
bằng chứng thực nghiệm đầy đủ cho chuỗi:

```text
Static detector
    → Uncertainty gate
    → Dynamic observation
    → Static–dynamic fusion
    → Final decision
    → Explanation-guided active-learning update
```

Bài báo chỉ nên tiếp tục sử dụng định vị **multi-stage ransomware detection** khi
có dữ liệu và thí nghiệm xác nhận từng giai đoạn. Chỉnh sửa câu chữ không thể thay
thế bằng chứng còn thiếu cho gate, dynamic detector và PID fusion.

## 2. Ba đóng góp cần được chứng minh

### 2.1. Conditional multi-stage detection

Uncertainty gate phải giảm số mẫu cần dynamic analysis trong khi vẫn duy trì
detection coverage. Cần đo cả chất lượng quyết định và chi phí quan sát động.

### 2.2. Adaptive static–dynamic fusion

PID hoặc cơ chế fusion thay thế phải được so sánh với các baseline đơn giản và
fusion model học được. Mọi phương pháp phải nhận cùng static/dynamic inputs và
cùng test samples.

### 2.3. Explanation-guided adaptation and diagnostics

Active Learning phải cải thiện detector dưới cùng label budget và vượt qua các
baseline mạnh. Fidelity phải được đánh giá trên các model/checkpoint có liên quan
đến hệ thống, không chỉ trên một mô hình tách biệt.

Ngoài các thí nghiệm riêng, cần ít nhất một thí nghiệm tích hợp chứng minh quan hệ
giữa các stage.

## 3. Xây dựng dataset có provenance

Đây là điều kiện bắt buộc nếu bài báo tiếp tục sử dụng thuật ngữ
``ransomware detection``.

Mỗi PE cần có:

- SHA-256 của binary;
- nguồn và quy trình thu thập;
- thời điểm thu thập;
- nhãn benign, malware hoặc ransomware;
- nguồn xác nhận nhãn;
- ransomware family/campaign khi có;
- phiên bản static feature extractor;
- SHA-256 của feature vector;
- chính sách loại duplicate và near-duplicate;
- giấy phép hoặc quyền sử dụng dữ liệu.

Các partition tối thiểu:

- training;
- validation;
- temporal test;
- family- hoặc source-disjoint test;
- external test nếu có thể.

Nếu không khôi phục được provenance của CSV hiện tại, tập này chỉ được giữ làm
pilot. Kết luận chính phải dựa trên một tập mới có manifest kiểm chứng được.

## 4. Thu thập dynamic evidence thật

Mỗi mẫu validation/test cần có báo cáo hành vi liên kết bằng SHA-256, bao gồm:

- process creation;
- file access, write, rename và deletion;
- entropy hoặc tốc độ thay đổi file;
- registry activity;
- API/system calls;
- network activity;
- timestamp của sự kiện;
- cấu hình sandbox/honeypot;
- observation duration;
- reason for termination;
- SHA-256 của report.

Dynamic score phải được tạo từ hành vi quan sát được:

\[
p_d=f_d(z).
\]

Hàm \(f_d\) phải được huấn luyện hoặc hiệu chỉnh trên training data. Không được
dùng target label của validation/test sample để tạo \(p_d\).

Các trường hợp cần có trong protocol:

- execution bình thường;
- delayed/sleep execution;
- không quan sát được hành vi;
- sandbox failure;
- missing dynamic evidence;
- hành vi xuất hiện qua nhiều time steps.

Muốn kiểm chứng thành phần I và D, một session phải có chuỗi thời gian có ý nghĩa.
Nếu mỗi PE chỉ có một dynamic score, PID gần như suy biến thành một phép weighting
đơn giản.

## 5. Đánh giá uncertainty gate

Gate sử dụng hai threshold chọn trên validation:

\[
p_s < \tau_{\mathrm{low}},\qquad
\tau_{\mathrm{low}}\le p_s\le\tau_{\mathrm{high}},\qquad
p_s > \tau_{\mathrm{high}}.
\]

Cần báo cáo:

- tỷ lệ traffic được chuyển sang dynamic analysis;
- TPR/FPR của nhánh quyết định sớm;
- số confident false negatives không được chuyển;
- chất lượng trên toàn bộ traffic;
- quality–cost curve theo gate coverage;
- latency và tài nguyên tiết kiệm được;
- kết quả khi dynamic evidence bị thiếu.

Không chỉ đánh giá trên các mẫu đã được gate chọn. Cách đánh giá đó sẽ bỏ qua lỗi
định tuyến của gate.

## 6. Sửa hoặc bảo vệ thiết kế PID

Thiết kế hiện tại sử dụng:

\[
e_k=p_{s,k}-p_{d,k}.
\]

Đại lượng này đo mức bất đồng giữa hai detector, chưa phải prediction error hoặc
reliability feedback. Có hai hướng phát triển.

### 6.1. Hướng A — Giữ PID hiện tại

Phải chứng minh PID tốt hơn:

- average fusion;
- validation-selected fixed weighting;
- max-risk fusion;
- proportional-only fusion;
- PI fusion;
- calibrated stacking/logistic regression;
- một fusion model học được.

Đồng thời phải xử lý hoặc phân tích:

- state reset;
- ý nghĩa của sequence;
- \(\Delta t\);
- integral windup;
- missing dynamic score;
- calibration của hai score;
- sensitivity theo \(K_p,K_i,K_d\);
- stability của fusion weight;
- ảnh hưởng đến FPR.

### 6.2. Hướng B — Thiết kế lại theo reliability

Trọng số có thể dựa trên reliability được ước lượng từ validation, chẳng hạn
calibration error, uncertainty hoặc chất lượng theo observation stage. PID khi đó
điều chỉnh một reliability signal thay vì chỉ phản ứng với detector disagreement.

Hướng B có cơ sở phương pháp tốt hơn nhưng yêu cầu thay đổi implementation và
chạy lại toàn bộ fusion experiment.

## 7. Full fusion ablation

Mọi baseline phải dùng cùng static/dynamic observations và cùng test rows.

| Baseline | Vai trò |
|---|---|
| Static-only | Giá trị của nhánh tĩnh |
| Dynamic-only | Giá trị của nhánh động |
| Average 50/50 | Fusion đơn giản |
| Max-risk | Kiểm tra hiệu ứng ưu tiên score lớn |
| Fixed validation weight | Baseline mạnh nhưng đơn giản |
| P | Giá trị của proportional term |
| PI | Giá trị bổ sung của integral term |
| PID | Giá trị bổ sung của derivative term |
| Calibrated stacking | Fusion học được |
| Oracle analysis | Cận trên phân tích, không phải deployment method |

Cần báo cáo:

- ROC-AUC và AP;
- TPR tại các FPR cố định;
- partial AUC trong vùng low FPR;
- calibration và Brier score;
- FPR cùng achieved TPR;
- bootstrap confidence intervals;
- paired differences trên cùng samples;
- failure cases theo family và observation stage.

Gain, threshold và model selection phải được thực hiện trên validation, sau đó
đóng băng trước test.

## 8. Thí nghiệm sleep evasion

Nếu giữ claim ``handles sleep evasion``, protocol phải có:

- nhiều observation windows \(t_1,t_2,\ldots,t_m\);
- delayed behavior đã được xác minh;
- static score trước execution;
- dynamic score tại từng time step;
- time-to-detection;
- tỷ lệ phát hiện trước khi hành vi phá hoại xảy ra;
- false alarms theo thời gian;
- PID weight/state trace.

So sánh tối thiểu:

- fixed fusion;
- P;
- PI;
- PID;
- adaptive observation kết hợp fixed fusion.

Thiết kế này tách lợi ích của observation window dài hơn khỏi lợi ích của PID.
PID không thể phát hiện hành vi mà sandbox chưa quan sát được.

## 9. Đo latency đúng phạm vi

End-to-end latency cần được phân rã:

\[
T_{\mathrm{total}}=
T_{\mathrm{queue}}+
T_{\mathrm{static\ feature}}+
T_{\mathrm{static\ inference}}+
T_{\mathrm{sandbox\ startup}}+
T_{\mathrm{observation}}+
T_{\mathrm{dynamic\ scoring}}+
T_{\mathrm{fusion}}.
\]

Cần báo cáo:

- median;
- mean và standard deviation;
- p95 và p99;
- warm/cold start;
- phần cứng và số threads;
- batch size;
- observation policy;
- throughput;
- tỷ lệ traffic qua dynamic path.

Fusion arithmetic time không được gọi là end-to-end detection latency.

## 10. Nâng Active Learning

Các baseline và phân tích cần bổ sung:

- uncertainty plus diversity/k-center;
- query-by-committee;
- attribution \(L_1\) và \(L_2\);
- các ablation cần thiết của \(U,H,V\);
- full-data supervised reference;
- weight sensitivity;
- normalization sensitivity;
- nhiều data splits;
- batch redundancy;
- positive-label yield theo round;
- tổng development-label budget.

Cần chạy ma trận tích hợp:

| Fusion / Acquisition | Random hoặc Uncertainty | XAI-guided AL |
|---|---:|---:|
| Fixed fusion | Đo | Đo |
| PID fusion | Đo | Đo |

Sau đó phân tích difference-in-differences:

\[
(\mathrm{PID+XAI}-\mathrm{Fixed+XAI})
-(\mathrm{PID+Baseline}-\mathrm{Fixed+Baseline}).
\]

Nếu interaction không tồn tại, không tuyên bố PID và AL tăng cường lẫn nhau.

## 11. Nâng fidelity thành đánh giá của hệ thống

Fidelity nên được chạy trên:

- static model;
- dynamic model nếu có explanation hợp lệ;
- final Active Learning checkpoints;
- fusion/meta-model nếu dùng learned fusion.

Controls cần có:

- uniform random masking;
- random masking trên model-used features;
- magnitude-matched masking;
- group-aware hoặc conditional intervention;
- global gain/permutation-importance ranking;
- attribution-column permutation negative control;
- nhiều fitted models.

EC và CF chỉ nên được gọi là geometry diagnostics. Không dùng OFS nếu chưa có
normalization, weighting và external validation.

## 12. Đánh giá operating region

Endpoint detection cần được đánh giá trong vùng FPR phù hợp. Cần bổ sung:

- TPR tại các FPR mục tiêu, chẳng hạn \(10^{-2},10^{-3},10^{-4}\), nếu dữ liệu
  đủ lớn;
- partial ROC trong vùng quan tâm;
- precision dưới các prevalence assumptions công khai;
- số false alerts trên 10.000 hoặc 100.000 benign files;
- confidence intervals;
- threshold transfer qua thời gian hoặc nguồn dữ liệu.

Test set benign phải đủ lớn cho FPR cần ước lượng. Một test set có vài trăm benign
samples không thể xác nhận đáng tin cậy vùng FPR rất thấp.

## 13. Artifact và reproducibility

Release cố định cần chứa:

- source commit hoặc tag;
- environment lock;
- dataset manifest;
- split manifests;
- static predictions;
- dynamic reports và hashes;
- dynamic scores theo time step;
- gate decisions;
- controller traces;
- fused predictions;
- Active Learning queries và checkpoints;
- fidelity masks và predictions;
- lệnh train, evaluate và verify;
- expected summaries và numerical tolerances.

Thuật ngữ ``independent verification`` chỉ dùng khi có bên độc lập thực sự chạy
artifact. Nếu verifier chỉ độc lập với plotting code, dùng ``independent replay
path`` hoặc ``separate verification implementation``.

## 14. Trình tự thực hiện

1. Xác minh dataset và ransomware-specific labels.
2. Khóa static train/validation/test splits.
3. Thu thập dynamic reports trên cùng samples.
4. Xây dựng và calibrate dynamic scorer.
5. Đánh giá uncertainty gate trên toàn bộ traffic.
6. Chạy fusion baselines và ablations.
7. Quyết định giữ, sửa hoặc bỏ PID dựa trên kết quả.
8. Chạy Active Learning strong baselines.
9. Chạy ma trận Active Learning × fusion.
10. Mở rộng fidelity controls.
11. Đánh giá low-FPR region và latency decomposition.
12. Đóng băng artifact và chạy replay verification.
13. Viết lại manuscript và response-to-reviewers.

## 15. Cổng quyết định

### Gate A — Dataset

Chỉ tiếp tục claim ransomware khi provenance và label semantics đã được xác minh.

### Gate B — Dynamic evidence

Chỉ đánh giá PID khi dynamic score đến từ hành vi quan sát thật, được ghép đúng
mẫu và không sử dụng target label.

### Gate C — PID value

Nếu PID không tốt hơn fixed weighting hoặc calibrated stacking, chuyển PID thành
negative result hoặc bỏ khỏi đóng góp chính.

### Gate D — Integrated contribution

Chỉ tuyên bố framework tích hợp khi có thí nghiệm cho thấy quan hệ đo được giữa
gate, fusion và adaptation.

### Gate E — Submission readiness

Chỉ nộp tạp chí khi kết quả chính có external/temporal validation, operating-point
evaluation, uncertainty phù hợp và artifact tái lập được.

## 16. Điều kiện tối thiểu để giữ tiêu đề multi-stage

- Provenance và ransomware labels được xác minh.
- Dynamic score đến từ hành vi thật.
- Gate được đánh giá trên toàn bộ traffic.
- PID được so sánh với fixed và learned fusion.
- Có P/PI/PID ablation.
- Latency được phân rã đầy đủ.
- Active Learning có strong baselines.
- Fidelity chạy trên các model liên quan.
- Có ít nhất một thí nghiệm tích hợp giữa các stage.

Nếu PID không thắng phương pháp đơn giản hơn, bài báo vẫn có thể giữ kiến trúc
multi-stage nhưng phải bỏ PID khỏi tiêu đề và đóng góp chính. Một kết quả âm được
báo cáo trung thực thuyết phục hơn một controller không có lợi ích đo được.

## 17. Nguyên tắc cập nhật manuscript

- Không sửa các kết quả cũ thành kết quả mới nếu chưa có artifact tương ứng.
- Không dùng số liệu demonstration làm bằng chứng thực nghiệm.
- Không chọn gain, weights hoặc threshold sau khi xem test results.
- Mỗi claim định lượng phải truy ngược được tới predictions và configuration.
- Giữ bản hiện tại tại commit `e1d4e7a` làm baseline trước revision.
- Chỉ sửa manuscript sau khi phạm vi thí nghiệm và các evidence gates được duyệt.
