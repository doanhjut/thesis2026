# Báo cáo cập nhật bằng chứng và phản hồi cho paper

**Tác giả nghiên cứu:** Lưu Văn Doanh  
**Ngày cập nhật:** 21/10/2026  
**Mốc đối chiếu:** kế hoạch MULTI_STAGE_RESEARCH_PLAN và bản IEEE master ngày 19/10/2026  
**Mục tiêu sử dụng:** cập nhật phản hồi học thuật, xác định phạm vi bài báo và bàn giao các bước thực nghiệm tiếp theo.

## 1 Kết luận điều hành

Nghiên cứu đã tiến bộ đáng kể so với lần đánh giá trước. Dữ liệu tĩnh EMBER đã có định danh kiểm chứng; Active Learning và Fidelity đã được đánh giá qua nhiều fold và model seed; PID đã chuyển từ thiết kế chưa có dữ liệu sang pilot tĩnh–động đo thật. Tuy nhiên, bằng chứng hiện tại chưa đủ để khẳng định một hệ thống multi-stage phát hiện ransomware đã được xác nhận trọn vẹn.

Hướng có thể viết ngay là bài về **explanation-guided Active Learning và controlled fidelity evaluation cho static PE malware detection**. Hướng multi-stage cần tiếp tục hoàn thiện cohort tĩnh–động, đối chứng fusion mạnh, gate trên toàn traffic và thí nghiệm tích hợp. Giữ ba hướng đóng góp không có nghĩa là cả ba đã có cùng mức bằng chứng.

| Hạng mục | Mức hiện tại | Kết luận sử dụng cho paper |
|---|---|---|
| EMBER và định danh tĩnh | Đã kiểm chứng 2.000 mẫu | Dùng làm benchmark tĩnh có provenance trong phạm vi tập con |
| XAI Guided Active Learning | Đã có confirmatory theo giao thức dự án | Có lợi so với Random; lợi ích so với Uncertainty nhỏ và tùy chỉ số |
| Fidelity và rank stability | Đã có 25 model và hai masking baseline | Hỗ trợ ảnh hưởng của thứ hạng SHAP trong không gian feature |
| Event indexed PID | Đã có pilot 199 mẫu | Chứng minh tính khả thi; chưa chứng minh D có lợi hoặc giảm FPR |
| Collection toàn cohort PID | Mốc đã xác nhận 693 trên 1.923 | Chưa đủ điều kiện chạy confirmatory theo ngưỡng đã khóa |
| Hệ thống tích hợp và vận hành | Chưa xác nhận | Chưa claim synergy, sleep evasion hoặc latency đầu cuối |

Từ “confirmatory” trong báo cáo chỉ giao thức xác nhận đã khóa trong dự án, không phải xác nhận bởi một nhóm nghiên cứu độc lập hay bằng chứng khái quát ra môi trường vận hành. Báo cáo không gán xác suất được nhận bài hoặc coi các kết quả trên là bằng chứng về chất lượng tạp chí đích.

## 2 Những nhận xét cũ đã thay đổi

Bản đánh giá trước nêu đúng các khoảng trống tại thời điểm đó, nhưng một số trạng thái cần cập nhật. CSV không rõ provenance đã được thay bằng tập EMBER có định danh; một test chia cố định và năm seed đã được bổ sung bằng năm outer fold; Fidelity một model đã được mở rộng thành 25 model; thiếu dynamic scorer đã được xử lý ở pilot bằng chuỗi API công khai và mô hình động huấn luyện trong từng fold. [E01–E04]

Những yêu cầu vẫn còn nguyên giá trị là nhãn ransomware phải có căn cứ, PID phải so với fusion đơn giản và learned fusion, gate phải đánh giá trên toàn traffic, thời gian theo sự kiện không được đổi thành giây, và kết quả ba thành phần trên hai corpus không tự chứng minh hiệu quả tích hợp. Kế hoạch 17 mục gốc được cập nhật theo từng mục trong RESPONSE_MATRIX.csv đi kèm; các mục là yêu cầu của roadmap, không được trình bày như trích nguyên văn một thư phản biện của tạp chí.

| Nhận xét trước | Bằng chứng mới | Đánh giá cập nhật |
|---|---|---|
| Dataset tĩnh thiếu sample identity | SHA và hash feature của 2.000 hàng EMBER khớp | Đã giải quyết cho tập con EMBER; chưa giải quyết ransomware labels |
| PID không có dynamic evidence | Pilot 199 mẫu có API sequence và metadata cùng SHA | Đã giải quyết ở mức pilot theo sự kiện |
| Một điểm động không tách được I và D | Bốn prefix 5 10 15 20 API calls của cùng trace | Schema đã cải thiện; lợi ích D vẫn chưa được chứng minh |
| AL chỉ có năm seed trên một test | Năm outer fold và năm AL seed mỗi fold | Bằng chứng ổn định hơn; chưa có external validation |
| Fidelity chỉ trên một model | 25 model và mean cùng median masking | Đã mở rộng; chưa đánh giá các checkpoint AL liên quan |
| Gate và hệ thống chưa được đo | Có pilot static gate riêng | Chưa có final decision trên toàn traffic của cùng paired corpus |

## 3 Dữ liệu đã có và giới hạn sử dụng

### 3 1 EMBER có định danh

Tập chính cho AL và Fidelity gồm **2.000 mẫu, 2.381 đặc trưng, 1.500 benign và 500 malware**. Manifest có row_id, source_index, nhãn, SHA-256, appeared, avclass và hash vector float32. Tất cả định danh hàng, source index và sample SHA đều duy nhất; không có vector feature trùng hoàn toàn. appeared nằm trong tháng 11–12/2018; avclass có ở 498 mẫu nhưng không phải ransomware ground truth. [E01]

Nguồn mini này được khôi phục từ phần test EMBER đang có trên máy rồi dùng làm benchmark nội bộ với outer folds riêng. Vì thế cần công khai cách lấy tập con; không gọi đây là kết quả theo official train/test protocol đầy đủ của EMBER. Không có family-held-out, temporal-held-out hay external test trong gói confirmatory hiện tại. Metadata định danh được dùng cho audit, không được đưa làm feature lộ nhãn.

### 3 2 Những archive không giải quyết được PID

train_small.zip chỉ có train_small.csv: 2.381 feature và label, không có SHA, family, timestamp hay report động. ZIP khoảng 2,82 GB; member CSV khoảng 14,41 GB. Việc kiểm kê và đọc schema đã hoàn tất; không cần giải nén lại để tìm behavior trace. [E05]

Nguồn NPZ SOREL và meta.db chưa đạt kiểm tra alignment theo hàng; việc khớp số dòng hoặc cấu trúc feature không đủ chứng minh cùng danh tính. Không dùng mapping suy đoán để tạo nhãn family, ransomware hoặc paired corpus. Đây là nhánh phục hồi chưa được chấp nhận, không phải một benchmark đã xác minh cho paper. [E06]

### 3 3 MalBehavD và metadata VirusTotal

Nguồn CSV công khai có nhãn benign/malware, SHA-256 và chuỗi API call. Cohort khóa sau xử lý trùng và yêu cầu ít nhất 20 API calls gồm **1.923 SHA duy nhất: 932 benign và 991 malware**, chia năm outer fold trước khi truy vấn metadata. Snapshot nguồn và manifest đều có SHA-256 cố định. [E03]

Metadata tĩnh chỉ lấy cấu trúc nội tại qua GET /api/v3/files/{sha256}. Bộ trích feature dùng allow-list size, type_tag và pe_info, tạo 199 feature số; không dùng AV verdict, detection count, threat name, tags hoặc filename làm đầu vào mô hình. Chuỗi API là quan sát công khai đã được upstream thu thập, không phải trace thực thi mới do dự án tự đo. Không tải hoặc chạy PE.

Hai corpus hiện trả lời hai nhóm câu hỏi khác nhau. Không ghép hàng EMBER với MalBehavD bằng vị trí, không so trực tiếp AUC của hai corpus để quy công cho một thành phần, và không coi static metadata VirusTotal là tương đương vector EMBER của LightGBM.

## 4 Kết quả Active Learning có thể dùng ngay

Thiết kế mới gồm năm outer folds, năm seed mỗi fold, năm chiến lược, 200 nhãn khởi tạo và 10 vòng thêm 100 nhãn. Các phương pháp trong cùng fold và seed dùng cùng initial set. Validation nằm trong develop; test không dùng chọn mẫu, target hay threshold. Full-pool reference được dùng để đặt target trên validation theo công thức 0,5 + 0,95 × (AUC_full_validation − 0,5). [E02]

| Phương pháp | ROC AULC | AP AULC | Nhãn tới target | Model và query giây |
| --- | --- | --- | --- | --- |
| Random | 0,928777 | 0,868350 | 584 | 4,1947 |
| Uncertainty | 0,931272 | 0,881934 | 520 | 4,1454 |
| U+H | 0,933026 | 0,883336 | 508 | 4,4741 |
| U+V | 0,930377 | 0,880164 | 488 | 4,3826 |
| XAI_full | 0,932202 | 0,881638 | 492 | 4,3471 |

Các số AULC là trung bình dọc theo ngân sách của giao thức; số nhãn là ngân sách train để đạt target validation, không phải tổng nhãn của toàn quá trình nghiên cứu. Cần công khai nhãn validation và chi phí tạo full-pool reference. Đến 1.200 nhãn, các phương pháp dùng cùng full pool nên điểm cuối giống nhau; bảng final AUC không phải bằng chứng chính cho hiệu quả lựa chọn mẫu.

**Kết quả đã đạt.** U+H tăng ROC-AULC 0,004249 và AP-AULC 0,014985 so với Random, cùng chiều ở 5/5 outer fold; trung bình giảm 76 nhãn, tương đương 13,0%. XAI_full giảm 92 nhãn, tương đương 15,8%, so với Random. U+V cần ít nhãn nhất để đạt target, còn U+H tốt nhất về ROC/AP-AULC. Đây là đánh đổi giữa hai mục tiêu, không phải lý do chỉ báo biến thể thắng một bảng.

**So với baseline mạnh.** U+H hơn Uncertainty 0,001754 ROC-AULC và 0,001401 AP-AULC, thắng 4/5 fold về hai AULC; nhưng ngân sách ít hơn chỉ ở 2/5 fold. XAI_full hơn 0,000931 ROC-AULC ở 3/5 fold, trong khi AP-AULC thấp hơn 0,000297. Vì vậy phải thay claim “full policy luôn tối ưu” bằng kết luận có điều kiện về từng biến thể.

**Vùng FPR thấp và chi phí.** TPR-AULC tại cap FPR 1% của Uncertainty là 0,638180, U+H là 0,636780; tại cap 5% tương ứng 0,769260 và 0,770620. Chưa có lợi ích ổn định vượt Uncertainty ở cả hai điểm. U+H tăng khoảng 0,227 giây query cho 10 vòng và khoảng 7,93% tổng model cộng query; XAI_full tăng tổng khoảng 4,86%. Đây là runtime nhỏ trên corpus 2.000 mẫu, không phải thời gian chuyên gia gán nhãn hoặc latency phát hiện đầu cuối.

**Để tiếp tục paper.** Bổ sung Uncertainty cộng diversity và calibrated query-by-committee nếu giữ claim vượt strong acquisition baselines; phân tích weight và normalization sensitivity, batch redundancy, positive-label yield. Khóa các biến thể trước lần đánh giá mới. Năm seed trong một fold được lấy trung bình trước so sánh theo outer fold; không dùng 25 cặp fold–seed như 25 test độc lập. Chưa có bằng chứng về family hoặc time generalization.

## 5 Kết quả Fidelity và độ ổn định

Đã chạy năm folds × năm model seeds, hai masking baseline lấy từ train là mean và median, ba mức k bằng 10 25 50, mỗi mức có 20 random masks. Có 25 model, 50 tổ hợp model–baseline và 50/50 lượt replay đạt. Đây là mở rộng thực chất so với phép thử trên một model riêng trong paper cũ. [E02]

| Baseline | k | Giảm AUC top SHAP | Giảm AUC random | Chênh lệch |
| --- | --- | --- | --- | --- |
| mean | 10 | 0,047817 | 0,000200 | 0,047617 |
| mean | 25 | 0,135853 | 0,000530 | 0,135323 |
| mean | 50 | 0,306729 | 0,000979 | 0,305750 |
| median | 10 | 0,053483 | 0,000094 | 0,053388 |
| median | 25 | 0,125180 | 0,000326 | 0,124854 |
| median | 50 | 0,300777 | 0,000658 | 0,300119 |

Top SHAP trừ random luôn phải được đọc là chênh lệch mức giảm AUC dưới cùng ngân sách masking. Không dùng tỷ số lớn do random drop gần 0 làm headline. Cần báo trị tuyệt đối và biến thiên, thay vì tiếp tục sử dụng claim khoảng 630 lần từ pilot cũ.

| Chỉ số | Đổi seed cùng fold | Đổi fold |
| --- | --- | --- |
| Spearman | 0,6144 | 0,5512 |
| Jaccard top 10 | 0,6221 | 0,4416 |
| Jaccard top 25 | 0,5398 | 0,3073 |
| Jaccard top 50 | 0,4901 | 0,3020 |

Mức giảm khi đổi fold cho thấy giải thích phụ thuộc phân hoạch dữ liệu. Các cặp model dùng chung dữ liệu hoặc model thành phần; không coi số cặp trong bảng stability là số quan sát độc lập để suy ra ý nghĩa thống kê.

**Phạm vi đạt được.** Có bằng chứng rằng tọa độ top |SHAP| ảnh hưởng đến mô hình mạnh hơn uniform random mask trong feature space, dưới hai baseline đã đo. Có mô tả rank stability qua model seed và fold.

**Khoảng trống cho paper.** Chưa bảo đảm vector sau mean hoặc median replacement tương ứng PE hợp lệ; chưa có group-aware hoặc conditional intervention, model-used-feature random, magnitude-matched control, gain/permutation ranking và attribution-permutation negative control. Fidelity chưa được xác nhận trên checkpoint AL cuối tương ứng hoặc dynamic scorer. Chưa có OFS tổng hợp được chuẩn hóa và kiểm định; EC/CF nếu giữ chỉ được gọi là geometry diagnostics. Độ trung thực với model không đồng nghĩa causal explanation hay xác nhận hành vi ransomware.

## 6 Pilot PID đã thực hiện như thế nào

Pilot chọn trước 200 mẫu, 100 mỗi lớp; 199 mẫu có metadata dùng được, gồm 100 benign và 99 malware. Một mẫu malware không có bản ghi VirusTotal. Coverage 99,5% chỉ tính trên selection pilot 200, không phải trên cohort 1.923. [E04]

Kênh tĩnh pilot là mô hình logistic regression trên metadata PE allow-list, với imputation và scaling trong train. Kênh động dùng TF IDF unigram và bigram API calls cùng logistic regression. Hai kênh có Platt calibration trên partition calibration riêng. Đây chưa phải cấu hình LightGBM cùng TreeSHAP của nhánh EMBER. Mọi prefix của một SHA nằm cùng partition; không chia prefix như các mẫu độc lập. [E10]

Năm outer test folds được giữ nguyên. Trong mỗi develop fold tách model training, calibration và fusion validation. Gain, fixed weight, threshold chỉ chọn trên fusion validation. p_static của cùng mẫu được giữ cố định, p_dynamic thay đổi qua prefix 5 10 15 20 API calls. Controller reset cho mỗi mẫu; bước cập nhật là số sự kiện, không phải số giây.

| Phương pháp | AUC và SD | AP | FPR phần trăm | TPR phần trăm | Brier |
| --- | --- | --- | --- | --- | --- |
| Static only | 0,9254 ± 0,0667 | 0,9286 | 47,08 | 96,28 | 0,0980 |
| Dynamic only | 0,9345 ± 0,0428 | 0,9437 | 47,96 | 96,95 | 0,1102 |
| Average 50 50 | 0,9582 ± 0,0344 | 0,9663 | 34,97 | 96,28 | 0,0810 |
| Fixed weight | 0,9415 ± 0,0449 | 0,9558 | 29,97 | 93,23 | 0,0927 |
| P | 0,9592 ± 0,0335 | 0,9674 | 34,97 | 96,28 | 0,0816 |
| PI | 0,9583 ± 0,0354 | 0,9660 | 34,97 | 96,28 | 0,0854 |
| PID | 0,9583 ± 0,0354 | 0,9660 | 34,97 | 96,28 | 0,0854 |

Các giá trị là trung bình theo năm fold tại prefix cuối, không phải metric tính từ pooled out-of-fold scores. FPR và TPR phải báo cùng nhau vì ngưỡng được chọn trên validation để hướng tới TPR 0,95, còn TPR test thực đạt khác nhau. Brier thấp hơn tốt hơn; AUC/AP cao hơn tốt hơn. SD giữa folds không được gọi là khoảng tin cậy 95%.

### 6 1 Những gì pilot chứng minh và chưa chứng minh

Pipeline có thể xây hai scorer từ evidence cùng SHA, hiệu chuẩn riêng, chọn fusion trên validation và tính lại prediction. P có mean AUC/AP cao nhất trong pilot; PID và PI có cùng AUC/AP, FPR/TPR ở mức báo cáo. Average 50/50 gần tương đương PID về AUC và có Brier trung bình thấp hơn. Vì vậy ưu thế so với Fixed một mình không đủ chứng minh cần controller phức tạp.

Bootstrap ghép cặp trên 199 dự đoán out-of-fold cho PID trừ Fixed có ΔAUC trung bình 0,012953 và CI 95% [−0,008599; 0,040939]; ΔAP 0,008039, CI [−0,010166; 0,027223]. Các interval này cắt 0. Đây là bootstrap của prediction từ model đã fit, chưa phản ánh việc refit toàn pipeline qua nhiều lần lấy mẫu. Không thay nó bằng hiệu số hai fold mean vì hai phép tổng hợp khác nhau.

ΔFPR bootstrap bằng +5,0607 điểm phần trăm, CI [0,0000; 10,5785]; ΔTPR bằng +4,0996 điểm phần trăm, CI [0,9434; 8,2610]. PID tăng TPR cùng với FPR ở operating point đã đo, không chứng minh giảm false alarms. PID hơn Fixed về AUC ở 4 fold và hòa 1; về FPR hòa 4 và xấu hơn 1. [E04]

PI và PID không đổi quyết định nào trên 199 mẫu ở mốc cuối. Sai khác score tuyệt đối trung bình khoảng 0,000109, tối đa 0,001196. Chưa có bằng chứng thành phần D mang lại lợi ích riêng. Sai lệch e = p_static − p_dynamic là bất đồng hai detector, chưa phải feedback về reliability hoặc nhãn đúng. Nhận xét max-risk trong roadmap vì thế vẫn cần đối chứng trực tiếp; không kết luận PID tương đương max-risk chỉ từ lập luận định tính.

### 6 2 Phần còn thiếu để bảo vệ đóng góp phương pháp

Ngoài bảy đối chứng đã có, cần Max-risk và calibrated stacking hoặc learned fusion trên cùng samples và observations. Cần giải thích mapping u sang trọng số, dấu sai lệch, clipping, initial state, reset, độ dài prefix, gain search và tỷ lệ trọng số chạm biên. Sensitivity của Kp Ki Kd và integral bounds chưa phải kết quả hoàn tất chỉ vì code có grid search. Nếu thiết kế lại reliability signal sau pilot, đánh dấu protocol revision và giữ nguyên kết quả phiên cũ.

Không có timestamp thực, delayed execution xác nhận hay observation duration trong CSV đang dùng. Bốn prefix không được gọi là 5 10 15 20 giây. Chưa thể đo time to detection, sandbox sleep evasion hoặc thời gian trước khi file bị phá hoại. Event indexed PID là một câu hỏi nghiên cứu hẹp hơn PID theo thời gian thực trong roadmap.

## 7 Tiến độ collection và trạng thái vận hành

Mốc collector hoàn tất mới nhất đọc được từ chat Linux là **693 usable trên 1.923 mẫu, coverage 36,0374%**. Đây là kết quả của lệnh collect-vt-static trả exit code 0; tăng 200 mẫu so với checkpoint 493. Không thay các file snapshot Git ngày 20/10 ghi 493 bằng cách sửa tay; cần xuất một snapshot mới từ cache Linux khi tiếp tục. [E07]

| Đại lượng | Giá trị tại mốc đã xác nhận |
|---|---:|
| Cohort cố định | 1.923 |
| Metadata usable đã thu | 693 |
| Tăng so với snapshot trước | 200 |
| Ngưỡng 90 phần trăm | 1.731 |
| Còn thiếu tối thiểu để đạt ngưỡng | 1.038 usable |
| Còn chưa có usable nếu so với toàn cohort | 1.230 |

1.230 là phần bù số usable, không phải số HTTP 404 hoặc số request chắc chắn còn cần. Không có bảng class/fold mới ở mốc 693 để kết luận missingness. Một request không bảo đảm tạo ra một mẫu usable. Cần thử hết cohort theo chính sách đã khóa và hết deferred trước khi mô hình hóa, ngay cả khi đã chạm 90%, để tránh bias do dừng ở giữa thứ tự manifest.

Đầu phiên 21/10 có lỗi mạng Operation not permitted, sau đó được xử lý và các request fetched đã thành công. Collector lần thứ hai hoàn tất ở 693. Turn điều phối Linux tiếp đó kết thúc với thông báo **giới hạn sử dụng Codex**, khác quota API VirusTotal. Không có bằng chứng từ lần kết thúc này để kết luận VT đã hết quota; cũng không báo đang thu nền khi chưa có kiểm tra tiến trình mới. Chưa xác nhận checkpoint mới hơn 693 khi lập báo cáo.

Việc tiếp tục phải kiểm tra collector còn sống, cache, request_history và schema đầy đủ trước. Nếu không có tiến trình thu, chạy tuần tự 4 request/phút trên cùng output; dừng HTTP 429 và lưu retry information nếu có. Dừng để xử lý lỗi permission, authentication hoặc transport thay vì ghi hàng loạt lỗi giống nhau. Không biến lỗi hạ tầng thành missing sample. Secret ở biến môi trường; không đưa key, raw response hoặc binary vào báo cáo/Git.

## 8 Phản hồi cập nhật theo các nhóm yêu cầu paper

### 8 1 Provenance và định vị bài toán

**Phản hồi:** Đã thay nguồn tĩnh không rõ identity bằng EMBER có SHA và feature hash; đã thêm MalBehavD có API sequence cho fusion pilot. Phần provenance tĩnh và ghép cặp pilot đã tiến bộ. Tuy nhiên, cả hai nguồn chỉ hỗ trợ benign/malware tổng quát. Không có nhãn ransomware đã xác minh, dữ liệu thời gian/family đủ cho held-out evaluation hoặc external validation. **Trạng thái: đạt một phần.** Phải đổi title, abstract và kết luận về generic PE malware, hoặc bổ sung corpus có nhãn ransomware trước khi giữ định vị cũ.

### 8 2 Conditional multi stage và uncertainty gate

**Phản hồi:** Đã có code và pilot static gate riêng; kết quả cũ route 49,3% test rows, early FN trên toàn positive 1,4%, early FP trên toàn negative 1,53%. Đây là XAI_full trên giao thức EMBER cũ, không phải gate của confirmatory mới hay MalBehavD paired corpus. Chưa có final prediction cho mọi traffic sau gate và dynamic path, quality–cost curve hoặc missing-evidence policy đã đánh giá. **Trạng thái: chưa đạt yêu cầu hệ thống.** [E08]

Cần đóng băng tau_low và tau_high trên validation; báo early decisions, routed cases, confident false negatives và final decisions trên toàn test. Baseline luôn chạy dynamic và baseline static-only phải dùng cùng traffic. Tách đường inference khỏi vòng query–analyst–retrain; không vẽ AL như bước bắt buộc trong latency của mỗi tệp.

### 8 3 Fusion PID và dynamic scorer

**Phản hồi:** Đã có observed API evidence, calibration và nhiều prefix, nên nhận xét “chưa có dynamic detector” không còn đúng cho pilot hiện tại. Nhưng thiếu Max-risk, stacking, sensitivity và full cohort confirmatory; không có lợi ích riêng của D, không có giảm FPR. **Trạng thái: đạt pilot, chưa đủ làm claim PID vượt trội.** Chọn phương pháp theo kết quả; nếu P hoặc PI bằng hay tốt hơn PID, báo đầy đủ và cân nhắc đóng góp adaptive fusion thay vì chỉ PID.

### 8 4 Active Learning và chi phí

**Phản hồi:** Đã có full-pool reference, label-to-target, nhiều folds/seeds, low-FPR metrics và query overhead. Không tiếp tục nói “chưa đo tiết kiệm nhãn” một cách tuyệt đối; đã đo giảm ngân sách oracle-query theo target, nổi bật so với Random. Nhưng chưa đo annotation time, diversity/QBC mạnh, tổng development-label cost, cross-source transfer hoặc sensitivity đầy đủ. **Trạng thái: bằng chứng thành phần tốt, còn thiếu cho claim mạnh về acquisition và vận hành.**

### 8 5 Fidelity và OFS

**Phản hồi:** Đã mở rộng từ một model sang 25 model, hai baseline và stability. Chưa có PE-aware validity, alternative rankings/negative controls hay fidelity trên AL checkpoints và dynamic model liên quan. Không gộp EC/CF với deletion để tạo OFS khi chưa có quy tắc đã kiểm định. **Trạng thái: đạt controlled feature-space evaluation; chưa đạt kiểm chứng giải thích toàn hệ thống.**

### 8 6 Latency sleep evasion và operating region

**Phản hồi:** AL đã có một số đo vùng FPR 1%/5%, nhưng không có bằng chứng low-FPR thực tế ở 10⁻³ hoặc 10⁻⁴. Mỗi outer test EMBER có khoảng 300 benign, một FP tương đương 0,333 điểm phần trăm. Pooled OOF của nhiều model không được gọi là một deployment test lớn của một model cố định. Chưa có latency queue, trích feature, sandbox startup/observation, dynamic inference và final decision. **Trạng thái: mới đạt một phần operating-region analysis; latency và sleep evasion chưa đạt.**

Nếu không thu timestamp và delayed behavior, loại claim sleep evasion/time-to-detection khỏi paper này. Các thời gian model/query hoặc arithmetic fusion chỉ được ghi với phạm vi đo tương ứng. Chỉ mô tả low-FPR rất thấp khi benign test đủ lớn và có khoảng bất định phù hợp.

### 8 7 Tích hợp và reproducibility

**Phản hồi:** Đã có replay verification, artifact hashes, stored predictions và truy vết model cho các gói kết quả. Cụm từ independent verification trong tên tệp không có nghĩa một nhóm bên ngoài đã tái lập nghiên cứu. Chưa có release đầy đủ đóng băng environment cho toàn bộ chuỗi tích hợp; raw/checkpoints lớn còn ở các môi trường khác nhau. **Trạng thái: tái lập nội bộ tốt theo từng thành phần, chưa phải system release hoàn chỉnh.**

Ma trận Random/Uncertainty hoặc XAI × Fixed/PID cần chạy trên cùng paired corpus, cùng outer folds và initial label sets, model tĩnh được cập nhật theo policy AL. Không lấy AULC EMBER và AUC PID MalBehavD ghép thành ma trận 2×2. Chỉ dùng từ “interaction” khi đã tính difference in differences ghép cặp trên metric được định trước, kèm bất định; không gọi hệ thống đầy đủ có điểm cao nhất là synergy.

## 9 Những câu có thể và chưa thể viết

| Phát biểu | Quyết định |
|---|---|
| Explanation guided policies cải thiện AULC so với Random trên tập con EMBER đã kiểm chứng | Được dùng kèm thiết kế và số liệu |
| U cộng H luôn vượt Uncertainty trên mọi tiêu chí | Không dùng |
| Giảm 15,8 phần trăm ngân sách train tới target so với Random | Dùng cho XAI_full trong protocol này; công khai validation và reference cost |
| SHAP top k quan trọng hơn random dưới mean và median feature masking | Được dùng trong feature space |
| SHAP xác định nguyên nhân hành vi ransomware hoặc PE sửa hợp lệ | Không dùng |
| Có pilot tĩnh động cùng SHA và calibration tách biệt | Được dùng |
| PID giảm FPR hoặc thành phần D vượt PI | Không dùng từ kết quả hiện tại |
| PID có xu hướng tăng ranking so với Fixed trong pilot | Dùng kèm CI cắt 0 và kết quả P Average PI |
| Đã chứng minh hệ thống multi stage hoặc PID cộng AL có synergy | Không dùng |
| Đã phát hiện ransomware zero day hoặc sleep evasion | Không dùng |

Tình huống M-001, điểm 0,55 và các đường dung hợp minh họa trên slide là dữ liệu giả định để giải thích cơ chế. Chúng không thuộc tập test, không phải report malware đã quan sát và không được đưa vào bảng kết quả paper. Kết quả định lượng chính phải lấy từ prediction và artifact đã nêu ở trên.

**Đoạn tiếng Anh cho phần tiến độ bằng chứng:**

> We replaced the unverified static pilot with a SHA-256-identified subset of EMBER and evaluated acquisition policies across five outer folds and five seeds per fold. Explanation-guided policies improved learning-curve performance relative to random sampling, whereas gains over uncertainty sampling were smaller and metric dependent. The full policy was not uniformly optimal.

> Controlled TreeSHAP deletion was expanded to 25 fitted models, two training-derived replacement baselines, and equal-budget random controls. The results support model faithfulness under the tested feature-space interventions; they do not establish executable validity or causal ransomware explanations.

> We additionally completed a 199-sample paired static–dynamic pilot using structural PE metadata and published ordered API traces. PID did not outperform PI in final decisions, and its AUC advantage over fixed weighting remained uncertain. Full-cohort collection and integrated gate–fusion–adaptation evaluation are still incomplete. Event counts are not interpreted as wall-clock detection time.

## 10 Quyết định phạm vi và cấu trúc manuscript

**Track B có thể triển khai ngay:** tập trung AL và Fidelity cho generic static PE malware, bổ sung dynamic pilot như feasibility study nếu cần, với phạm vi riêng và giới hạn rõ. Tiêu đề gợi ý: “Explanation Guided Active Learning and Controlled Fidelity Evaluation for Static PE Malware Detection”. Đây là hướng ít phụ thuộc collection, nhưng vẫn phải bổ sung baseline và phân tích novelty cho mục tiêu paper đã chọn.

**Track A cần thêm bằng chứng:** nghiên cứu conditional multi-stage generic malware detection với paired corpus đủ coverage, Max-risk/stacking, gate trên toàn traffic và AL × fusion cùng corpus. Chỉ thêm “ransomware” khi có nhãn và phép đánh giá phù hợp. Có thể giữ ba đóng góp dạng kiến trúc cùng adaptive fusion, acquisition policy và controlled diagnostics; không đặt trước kết luận PID phải là phương pháp thắng.

Chưa có cơ sở đánh dấu submission-ready cho multi-stage từ checkpoint hiện tại. Tên tạp chí và template trong kế hoạch cũ là định hướng lịch sử; chưa được rà lại quy định hiện hành trong lần cập nhật này. Chốt venue và xác minh author guidance sau khi chốt scope, không dùng số trang master làm bằng chứng tuân thủ template tạp chí.

| Phần | Tệp cần cập nhật | Thay đổi cần làm |
| --- | --- | --- |
| Title Abstract Keywords | main.tex | Giới hạn generic PE malware; thay pilot AUC cũ bằng kết quả confirmatory; PID là pilot riêng |
| Introduction và RQs | sections/01_introduction.tex | Tách acquisition fidelity fusion và hệ thống; không hứa ransomware hoặc synergy chưa đo |
| Related Work | sections/02_related_work.tex | Cập nhật đối chứng AL fusion fidelity; kiểm chứng metadata reference và bảng novelty |
| Problem và threat model | sections/03_problem_threat_model.tex | Tách event index khỏi giây; định nghĩa missing evidence và inference adaptation loops |
| Methodology | sections/04_methodology.tex | Thống nhất code U H V PID reset calibration; ghi khác biệt hai corpus và hai static scorer |
| Experimental methodology | sections/05_experimental_methodology.tex | Thay nguồn unverified bằng EMBER có identity; 5 folds 5 seeds; thêm paired pilot protocol |
| Results | sections/06_results.tex | Dùng AULC labels low FPR và 25 model Fidelity; thêm pilot PID với negative findings |
| Discussion | sections/07_discussion.tex | Giải thích U H và U V tradeoff; P Average PI cạnh tranh với PID; bỏ diễn giải quá mức |
| Threats to validity | sections/08_threats_to_validity.tex | Source bias hai corpus missingness event axis feature validity và phụ thuộc folds |
| Conclusion | sections/09_conclusion.tex | Chỉ kết luận các RQ đã có evidence; ghi rõ phần hệ thống còn chưa đánh giá |
| Appendix và claim map | sections/10_appendices.tex | Cập nhật hashes protocol verifier artifact map và code commit; tách lịch sử pilot |

Toàn bộ title, abstract, introduction, results và conclusion phải dùng cùng mức bằng chứng. Không chỉ thay bảng số rồi giữ câu “XAI_full tốt nhất” hoặc “không có bất kỳ dynamic evidence nào” của bản cũ. Không trộn số pilot 20261014, EMBER single-split 20261019, confirmatory EMBER và MalBehavD pilot trong một hàng kết quả.

## 11 Công việc tiếp theo và điều kiện nghiệm thu

| Mã | Ưu tiên | Công việc | Phụ thuộc |
| --- | --- | --- | --- |
| T01 | P0 | Kiểm tra môi trường Linux và cache | Không |
| T02 | P0 | Thu nốt cohort đã khóa | T01 |
| T03 | P0 | Audit coverage missingness | T02 |
| T04 | P1 | Chạy fusion confirmatory hiện có | T03 |
| T05 | P1 | Max risk stacking và sensitivity | Khóa trước run mở rộng |
| T06 | P1 | Gate trên toàn traffic | T03 T05 |
| T07 | P1 | Strong AL baselines và sensitivity | Có thể làm song song |
| T08 | P1 | Ma trận AL và fusion | T06 T07 |
| T09 | P1 | Fidelity trên model liên quan và controls | T07 |
| T10 | Theo claim | External temporal hoặc ransomware labels | Corpus bổ sung nếu có |
| T11 | Theo claim | Latency và sleep evasion | Môi trường timestamp thật |
| T12 | P1 | Cập nhật manuscript và release | T04 T05 và scope đã chốt |

**M1 hoàn tất dữ liệu:** không còn deferred, coverage tối thiểu 90%, bảng missingness theo class/fold và file hash được lưu. Nếu thấp ngưỡng, báo coverage thực và hạ phạm vi kết luận; không đổi cohort để đạt số mong muốn.

**M2 hoàn tất fusion:** cùng test samples cho tất cả baseline; chọn cấu hình/threshold trên validation, lưu prediction, controller state và verification. Báo P I D kể cả kết quả âm. Protocol mới thêm Max-risk, stacking và sensitivity phải có version riêng vì đã xem pilot; không gọi các lựa chọn sau pilot là pre-registered từ đầu.

**M3 hoàn tất hệ thống:** gate có final decisions toàn traffic và quality–cost analysis; AL × fusion trên paired corpus, giải thích trên model tương ứng, thiếu evidence có policy đã khóa. Nếu chưa thực hiện M3, paper chỉ được mô tả là các đánh giá thành phần và feasibility, không phải system validation.

**M4 hoàn tất manuscript:** tables/figures sinh từ artifact cuối, claim map không có claim vượt evidence, source citations kiểm chứng, author metadata được xác nhận, template build sạch và thầy hướng dẫn duyệt. Environment lock và replay cần được kiểm thử trong môi trường sạch; chỉ tăng số test unit không thay thế được đánh giá khoa học.

Về thủ tục bài báo, cần xác nhận author order, affiliation, institutional email, ORCID, corresponding author, đóng góp CRediT và đồng thuận của đồng tác giả. Danh sách tài liệu tham khảo của master chưa được rà lại DOI và publisher record trong lần cập nhật này; việc có BibTeX và không lỗi citation khi build không thay thế kiểm chứng reference. Quyền sử dụng và chia sẻ bảng feature/report dẫn xuất cũng cần được ghi trong data availability statement trước release.

Các việc có thể làm song song khi chờ quota là viết lại dataset card và scope, cập nhật bảng AL/Fidelity, thiết kế strong baselines, lập sensitivity protocol và kiểm tra references. Không cần chạy lại nguyên hai gói confirmatory đã đạt nếu chưa có thay đổi phương pháp hoặc lỗi cần sửa.

## 12 Hướng dẫn tiếp tục từ checkpoint

**Môi trường dữ liệu chính:** Linux /workspace/thesis2026. Cohort đã khóa ở outputs/malbehavd_pid_20261020_prepared, cache ở outputs/malbehavd_pid_20261020_vt_full. Mẫu tái tạo Windows ở outputs/malbehavd_pid_20261021_prepared có manifest hash khớp sau chuẩn hóa LF, nhưng không chứa cache Linux hay secret; không khởi động collection mới từ đầu ở Windows.

Kiểm tra tiến trình hiện tại trước, rồi audit không gọi mạng:

```bash
.venv/bin/python scripts/run_experiments.py audit-vt-collection \
  --cohort outputs/malbehavd_pid_20261020_prepared/cohort_manifest.csv \
  --collection outputs/malbehavd_pid_20261020_vt_full --min-coverage 0.90
```

Exit code 3 có thể là collection incomplete dự kiến; kiểm tra JSON để phân biệt với lỗi schema. Nếu request_log bị ngắt giữa cohort, giữ history và phục hồi log từ identity/cache/history, đánh dấu phần chưa gọi là deferred; không giả lập kết quả mạng. Chỉ resume sau khi xác nhận không có collector khác:

```bash
.venv/bin/python scripts/run_experiments.py collect-vt-static \
  --cohort outputs/malbehavd_pid_20261020_prepared/cohort_manifest.csv \
  --output outputs/malbehavd_pid_20261020_vt_full \
  --seed 2026 --requests-per-minute 4 --max-new 100
```

Sau mỗi lô hoàn tất, lưu summary và audit mới. Chỉ khi M1 đạt mới chạy event-pid trên output directory mới:

```bash
.venv/bin/python scripts/run_experiments.py event-pid \
  --sequences outputs/malbehavd_pid_20261020_prepared/api_sequences.csv.gz \
  --static-features outputs/malbehavd_pid_20261020_vt_full/static_features.csv.gz \
  --selection outputs/malbehavd_pid_20261020_vt_full/selected_cohort.csv \
  --output outputs/malbehavd_pid_confirmatory_NEW_RUN_ID \
  --windows 5 10 15 20 --target-tpr 0.95 --min-coverage 0.90 \
  --bootstrap 1000 --seed 2026
```

Lệnh trên tái sử dụng runner bảy baseline đang có, chưa bao gồm Max-risk hoặc stacking đề xuất cho paper. Không coi việc chạy lệnh này là hoàn tất M2 mở rộng. Đóng băng protocol bổ sung trước run mới, giữ pilot cũ nguyên trạng. Mọi bảng chênh lệch phải nêu dùng mean theo fold hay pooled OOF, và báo FP FN TPR FPR cùng policy threshold.

**Prompt bàn giao:** “Đọc báo cáo cập nhật paper 21/10/2026, RESPONSE_MATRIX.csv, NEXT_ACTIONS.csv và EVIDENCE_SNAPSHOT.json. Giữ scope generic PE malware, cohort/folds đã khóa và checkpoint cuối đã xác nhận. Kiểm tra trạng thái thật trước khi báo đang chạy. Không tải hoặc thực thi PE, không lộ secret, không sửa số đo. Ưu tiên M1 rồi M2; chỉ claim multi-stage integration khi M3 có artifact.”

## 13 Danh mục nguồn và khóa bằng chứng

| Mã | Bằng chứng | Đường dẫn hoặc vị trí |
| --- | --- | --- |
| E01 | Định danh EMBER và trạng thái run | results/confirmatory_20261019_ember_identity/static_identity_audit.json; run_status.json |
| E02 | AL Fidelity confirmatory và replay | results/confirmatory_20261019_ember_identity/README.md; al/; fidelity/ |
| E03 | Cohort và giao thức event indexed | docs/EVENT_INDEXED_PID_RUNBOOK.md; outputs/malbehavd_pid_20261021_prepared/ |
| E04 | PID pilot đo thật và bootstrap | results/measured_20261020_malbehavd_pid_pilot200/ |
| E05 | Kiểm kê train small | results/pid_intake_20261020/ |
| E06 | SOREL recovery chưa đạt mapping | results/measured_20261019_source_recovery/ |
| E07 | Log collector Linux hoàn tất ở 693 | sources/COLLECTION_CHECKPOINT_693.json trong gói báo cáo |
| E08 | Static gate theo protocol cũ | results/measured_20261019_ember_identity/static_gate/summary_recomputed.csv |
| E09 | Bài master và roadmap đã đối chiếu | sources/MANUSCRIPT_20261019_main.txt; MULTI_STAGE_RESEARCH_PLAN_ORIGINAL.md; PHAN_HOI_TRUOC_20261019.md |
| E10 | Implementation model và fusion | src/experiments/malbehavd_pid.py; temporal_fusion.py; src/pid_fusion.py |

Các mã E trong báo cáo là nguồn nội bộ hoặc hồ sơ nguồn công khai đã lưu tại repository, không phải đánh số tài liệu tham khảo đã xuất bản. EVIDENCE_SNAPSHOT.json ghi full path, SHA-256 của các tệp đầu vào và trích đoạn log checkpoint 693. Trạng thái thu thập Linux là mốc đã xác nhận qua log của chat “Thiết lập thesis2026”, không phải một cache được tải về và audit lại trên Windows.

Đối soát Git hiện tại đã tìm thấy commit e1d4e7a6ea168b53d248d5f4fa778c49d25d53a7 với tiêu đề “docs: complete full journal manuscript”. Vì thế nhận xét cũ rằng commit này không có ở local history không còn áp dụng cho checkout hiện tại. Đây là commit manuscript; vẫn phải dùng commit nguồn thực nghiệm riêng cho từng run và hash ZIP manuscript làm mốc đối chiếu, không đồng nhất chúng thành một baseline thực nghiệm duy nhất.

Đối soát lại 67 tệp theo manifest hash của hai gói đầu vào: 14 tệp khớp byte, 53 tệp văn bản khớp sau chuẩn hóa CRLF thành LF, 0 mismatch và 0 thiếu. Khác biệt newline được báo riêng, không gọi là byte equality. Đây là kiểm tra tính toàn vẹn bản sao đầu vào và đối chiếu artifact, không phải một lần huấn luyện lại hay replication bởi nhóm bên ngoài.

RESPONSE_MATRIX.csv giữ từng yêu cầu của 17 mục roadmap cùng trạng thái, bằng chứng, phần thiếu và điều kiện hoàn thành. CLAIM_EVIDENCE_MAP.csv khóa các phát biểu quan trọng; NEXT_ACTIONS.csv ghi thứ tự, dependency, artifact và acceptance criteria. Các tệp này cần được cập nhật khi có snapshot hoặc run mới, trước khi sửa headline và kết luận paper.
