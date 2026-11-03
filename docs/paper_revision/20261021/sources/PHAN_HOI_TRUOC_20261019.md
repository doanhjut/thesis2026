## Đánh giá tổng thể

Bản [MULTI_STAGE_RESEARCH_PLAN.md](/workspace/attachments/e5fee33f-4a4d-4966-a983-eca71145d3d2/MULTI_STAGE_RESEARCH_PLAN.md) đánh giá đúng phần lớn các điểm yếu hiện tại. Đây là một **research roadmap theo chuẩn bài báo/tạp chí**, không phải kết luận rằng luận văn hoàn toàn không có đóng góp.

Hai phần hiện đã có bằng chứng thực nghiệm thực sự là:

- XAI-Guided Active Learning.
- Fidelity của TreeSHAP trên mô hình tĩnh.

Các phần chưa có đủ bằng chứng là:

- Uncertainty gate.
- Dynamic detector.
- PID fusion.
- End-to-end latency.
- Quan hệ tích hợp giữa gate, fusion và Active Learning.

## Những nhận xét hoàn toàn đúng

### 1. Dataset hiện chỉ đủ làm pilot

Pipeline đã tự ghi `provenance_status: unverified`. CSV có 2.000 dòng và 2.381 đặc trưng, nhưng không có SHA-256 của PE, family, thời điểm, nguồn và cách xác nhận nhãn.

Nhận định tại [mục Dataset](/workspace/attachments/e5fee33f-4a4d-4966-a983-eca71145d3d2/MULTI_STAGE_RESEARCH_PLAN.md:43) là đúng: chưa nên dùng kết quả này để tuyên bố khả năng phát hiện ransomware mới, zero-day hoặc family-disjoint.

Tuy nhiên, yêu cầu provenance từng PE không phải con đường duy nhất. Một benchmark công khai có tài liệu nguồn, phiên bản, label policy và split chính thức cũng có thể được chấp nhận. Vấn đề là CSV hiện tại không còn đủ ID để truy ngược về benchmark đó.

### 2. PID hiện chưa được chứng minh

Nhận xét quan trọng nhất nằm tại [dòng 141](/workspace/attachments/e5fee33f-4a4d-4966-a983-eca71145d3d2/MULTI_STAGE_RESEARCH_PLAN.md:141):

\[
e_k=p_{s,k}-p_{d,k}
\]

đo sự bất đồng giữa hai detector, không phải prediction error hay reliability feedback.

Với thành phần P và \(K_p>0\):

- Nếu \(p_s>p_d\), trọng số static tăng, kết quả dịch về score lớn hơn.
- Nếu \(p_d>p_s\), trọng số static giảm, kết quả lại dịch về score lớn hơn.

Vì vậy PID hiện tại có hành vi gần một phiên bản làm trơn của **max-risk fusion**. Max-risk là baseline bắt buộc nếu muốn chứng minh PID có giá trị riêng.

### 3. Schema PID hiện tại chưa kiểm chứng được I và D

Đây là điểm kế hoạch nhận xét đúng nhưng còn nghiêm trọng hơn đối với implementation hiện tại.

Template đang yêu cầu đúng một `p_dynamic` cho mỗi `row_id`. Nếu reset controller cho từng PE và mỗi PE chỉ có một quan sát:

\[
u_1=(K_p+K_i+K_d)e_1
\]

Khi đó PI và PID không thể phân biệt về mặt thực nghiệm với một P-controller có gain khác.

Nếu giữ state qua nhiều PE không liên quan, kết quả lại phụ thuộc vào thứ tự xử lý các binary, không có ý nghĩa rõ ràng về mặt phát hiện malware.

Muốn kiểm chứng PID, schema phải đổi thành nhiều dòng trên một PE:

```text
sample_sha256
execution_id
time_step
elapsed_seconds
p_static
p_dynamic
evidence_status
report_path
report_sha256
```

Controller nên reset cho mỗi execution, còn \(p_d(t)\) thay đổi theo thời gian quan sát.

### 4. Gate hiện chưa tồn tại trong thí nghiệm

Fusion runner hiện ghi rõ:

```text
All supplied pairs evaluated. No early-exit gate or deployment coverage claim.
```

Do đó chuỗi `static → gate → dynamic → fusion` trong tài liệu chưa phải hệ thống đã được đánh giá.

Nhận xét ở [mục Uncertainty gate](/workspace/attachments/e5fee33f-4a4d-4966-a983-eca71145d3d2/MULTI_STAGE_RESEARCH_PLAN.md:110) là đúng: phải đánh giá trên toàn bộ traffic, gồm cả những mẫu gate quyết định sớm. Nếu chỉ đánh giá các mẫu được chuyển sang dynamic, ta bỏ qua confident false negatives.

Ngoài ra, trước khi gọi khoảng quanh 0.5 là “uncertain”, \(p_s\) cần được hiệu chuẩn. LightGBM score hiện chưa được kiểm tra calibration.

### 5. Claim về latency chưa hợp lệ

Code hiện chỉ đo thời gian replay phép tính fusion. Nó không đo sandbox startup, observation window, dynamic scoring hoặc queue.

Vì vậy đánh giá tại [mục Latency](/workspace/attachments/e5fee33f-4a4d-4966-a983-eca71145d3d2/MULTI_STAGE_RESEARCH_PLAN.md:232) là chính xác. Không thể dùng thời gian vài millisecond của phép tính PID để tuyên bố end-to-end detection latency.

## Những gì dự án đã chứng minh được

### Active Learning

Ở cùng ngân sách 700 nhãn train:

| So sánh XAI_full − Uncertainty | Trung bình | Kết luận |
|---|---:|---|
| ROC-AUC | +0.005787 | Dương ở 5/5 seed |
| AP | +0.007915 | Dương ở 5/5 seed |
| FPR | −0.023333 | Chỉ tốt hơn ở 2/5 seed |
| TPR | −0.002000 | Gần như không đổi |

Đây là bằng chứng tốt cho nhận định:

> XAI-guided acquisition cải thiện ranking quality dưới cùng ngân sách nhãn trong pilot hiện tại.

Chưa đủ bằng chứng cho:

- Luôn giảm FPR.
- Tiết kiệm một số lượng nhãn cụ thể.
- Tiết kiệm thời gian chuyên gia.
- Tổng quát sang họ ransomware hoặc nguồn mới.

Kế hoạch đúng khi yêu cầu thêm diversity/core-set, query-by-committee, full-data reference và sensitivity. Tuy nhiên không cần chạy mọi baseline trong danh sách để bảo vệ luận văn. Một baseline `uncertainty + diversity`, một full-data reference và sensitivity của \(U,H,V\) đã tạo ra cải thiện đáng kể về sức thuyết phục.

### Fidelity

Kết quả hiện tại khá rõ:

| k | AUC sau top-SHAP | AUC sau random | AUC giảm do top-SHAP |
|---:|---:|---:|---:|
| 10 | 0.913933 | 0.979867 | 0.066233 |
| 25 | 0.818533 | 0.979910 | 0.161633 |
| 50 | 0.671200 | 0.979263 | 0.308967 |

Điều này chứng minh những đặc trưng có \(|SHAP|\) lớn ảnh hưởng mạnh hơn random mask cùng kích thước trên model cố định.

Kế hoạch vẫn đúng khi yêu cầu mở rộng sang nhiều model/checkpoint. Hiện Fidelity mới được chạy trên một model riêng, nên chưa chứng minh explanation quality ổn định trong quá trình Active Learning.

Việc không tổng hợp OFS là quyết định đúng. EC và CF nên được gọi là geometry diagnostics.

## Điểm kế hoạch còn thiếu hoặc cần sửa

### 1. Dynamic scorer cũng cần training evidence

Tài liệu yêu cầu report cho validation/test nhưng đồng thời yêu cầu:

\[
p_d=f_d(z)
\]

được huấn luyện trên training data. Như vậy cũng cần dynamic reports cho training/calibration, trừ khi sử dụng một dynamic detector bên ngoài đã huấn luyện và đóng băng.

### 2. Active Learning không nên vẽ như một stage inference

Sơ đồ đầu tài liệu đặt:

```text
Final decision → Explanation-guided active-learning update
```

Điều này dễ khiến hội đồng hiểu rằng hệ thống retrain ngay sau mỗi quyết định. Nên tách thành hai vòng:

```text
Inference:
Static → Gate → Dynamic → Fusion → Decision

Development/adaptation:
Unlabeled pool → Query → Analyst label → Retrain → Validate → Deploy
```

Hai vòng có thể tương tác, nhưng không phải cùng một latency path.

### 3. Low-FPR chưa thể đo bằng test hiện tại

Test hiện có 300 benign samples. Độ phân giải FPR nhỏ nhất là:

\[
\frac{1}{300}=0.00333
\]

Do đó:

- FPR \(10^{-3}\) chưa đo được.
- FPR \(10^{-4}\) hoàn toàn chưa đo được.
- Ngay cả FPR \(10^{-2}\) cũng chỉ tương ứng ba false positives, rất nhiễu.

Theo quy tắc xấp xỉ \(3/n\), cần khoảng 3.000 benign không có false positive để upper bound 95% xuống dưới \(10^{-3}\), và khoảng 30.000 cho \(10^{-4}\).

### 4. “Independent verification” cần đổi tên

Verifier hiện do cùng dự án triển khai, nhưng dùng đường tái tính riêng. Tên phù hợp là:

- `separate replay verification`, hoặc
- `independent recomputation path`.

Chưa nên gọi là independent verification bởi một bên độc lập.

### 5. Commit `e1d4e7a` không tồn tại trong repository hiện tại

Dòng 417 yêu cầu giữ commit này làm baseline, nhưng object đó không có ở local history hiện tại. Nên tạo một tag có thật, chẳng hạn:

```text
pre-multistage-revision
```

trên commit được chọn, và ghi full commit SHA trong kế hoạch.

## Ma trận trạng thái hiện tại

| Thành phần | Trạng thái | Đánh giá |
|---|---|---|
| Static LightGBM | Có implementation và kết quả | Pilot, thiếu provenance |
| XAI-Guided AL | Đã đo, 5 seed, cùng budget | Đóng góp mạnh nhất hiện tại |
| Fidelity deletion | Đã đo và có random control | Tốt nhưng mới trên một model |
| OFS tổng hợp | Đã bỏ | Quyết định đúng |
| Dynamic detector | Chưa có | Blocker |
| Uncertainty gate | Chưa có | Blocker |
| PID implementation | Có prototype | Chưa có bằng chứng |
| P/PI/PID ablation | Code có khung | Chưa chạy được hợp lệ |
| End-to-end latency | Chưa đo | Không được claim |
| Integrated experiment | Chưa có | Không được claim synergy |
| Reproducibility | Khá tốt | Thiếu environment lock và full public artifacts |

## Khuyến nghị chiến lược

Nếu mục tiêu gần nhất là **bảo vệ luận văn**, không nên cố hoàn thành toàn bộ roadmap này. Nên định vị ba đóng góp như sau:

1. **Đóng góp đã chứng minh:** XAI-Guided Active Learning cải thiện AUC/AP dưới cùng label budget.
2. **Đóng góp đã chứng minh có giới hạn:** framework Fidelity và deletion controls cho TreeSHAP.
3. **Đóng góp phương pháp/nguyên mẫu:** kiến trúc multi-stage và PID fusion, đang chờ dynamic evidence để xác nhận thực nghiệm.

Nếu luận văn đang viết rằng PID đã giảm FPR hoặc đạt latency khoảng 15 ms, phải sửa lại.

Nếu mục tiêu là **nộp bài báo multi-stage**, kế hoạch này hợp lý và các cổng A–D thực sự cần thiết. Tôi khuyến nghị ưu tiên:

1. Khôi phục hoặc xây dựng dataset manifest.
2. Tách inference loop và adaptation loop.
3. Thiết kế lại schema dynamic theo time step.
4. Xây dựng/calibrate dynamic scorer.
5. Cài gate và đánh giá quality–cost trên toàn traffic.
6. So sánh fixed, max-risk, stacking, P, PI và PID.
7. Sau đó mới chạy ma trận PID × Active Learning.

Nếu không có khả năng thu thập dynamic reports thật, hướng bài báo khả thi hơn là tập trung vào **XAI-Guided Active Learning và Fidelity cho static PE detection**, còn multi-stage/PID chuyển thành hướng nghiên cứu tiếp theo.
