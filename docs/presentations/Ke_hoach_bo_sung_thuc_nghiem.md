# Phiếu bổ sung thực nghiệm và thay hình cho bộ slide 9 trang

**Mục đích:** giữ bộ slide tập trung vào đề tài và kết quả; dùng phiếu này để quản lý phần cần kiểm chứng, dữ liệu cần bổ sung và hình sẽ thay. Tên tệp dưới đây là artifact trong gói bằng chứng đã giao hoặc tên đầu ra đề nghị; không phải đường dẫn máy cục bộ.

## Cách dùng số hiện tại

- **Slide 4 — PID:** số của Bảng 4.5, tr.53 trong `luuvan.pdf` là số bản thảo, **chưa được xác minh từ dự đoán tĩnh–động ghép cặp**. Bảng có script xuất giá trị định sẵn. Không diễn giải việc xuất lại bảng là chạy lại thí nghiệm. Khoảng 15,2 ms là thời gian dung hợp được báo cáo, không phải đầu cuối. Trước khi thay bằng phép đo mới, người trình bày cần nhận diện đây là kết quả bản thảo đang đối soát.
- **Slide 6 — AL:** dùng phép đo trong `pilot_al/summary.json`, `REPORT.md` và `learning_curves.png`. Đây là pilot đã huấn luyện mới trên CSV cục bộ, có split, query và dự đoán. Nguồn upstream và ý nghĩa nhãn riêng cho ransomware chưa xác minh; dùng nhãn âm/dương. Năm seed dùng chung test, không phải năm bộ dữ liệu độc lập.
- **Slide 7 — Fidelity:** dùng `pilot_fidelity/run_seed42/summary.json`. Đây là phép đo thực trên một model mới và phép masking vector, chưa xác nhận vector sau che là một PE hợp lệ. Không gộp số này với OFS của bảng cũ.
- **Slide 8 — Tiếp thu seminar:** có thể nói đã bổ sung đối chứng AL và phép đo masking; không nói đã hoàn tất kiểm chứng PID, tính hợp lệ PE-aware hoặc hiệu quả vận hành toàn hệ thống. Tệp này chứa phần việc còn lại để người trình bày nắm rõ dù không đưa toàn bộ lên slide.

## 1. Slide 4: tách đóng góp thực của PID

**Hình/bảng hiện tại:** Bảng 4.5 của bản thảo: PID AUC 0,9818, FPR 0,8%; fixed-weight AUC 0,9720, FPR 1,1%. Đặt tên bản sao lưu `slide04_pid_table_draft.svg`; giữ nguyên số và nguồn, không đổi tên thành kết quả đã tái lập.

**Đầu vào còn cần:** manifest có ID/hash mẫu, nhãn có nguồn, split, xác suất tĩnh và động của cùng mẫu; ID/phiên bản model, chính sách cổng, thứ tự dòng/phiên, trạng thái/reset PID, thời gian của từng tầng. Tín hiệu động phải lấy từ log quan sát thực đủ truy nguyên; không dựng điểm động từ nhãn thật hoặc từ điểm tĩnh cộng nhiễu. Xác định thời gian cập nhật có nghĩa theo luồng nào, tránh coi hai tệp bất kỳ là hai thời điểm của cùng đối tượng điều khiển.

**Thí nghiệm tối thiểu:**

1. Khóa train/validation/test và dữ liệu đầu vào; huấn luyện, chọn tham số và ngưỡng bằng train/validation. Trên cùng các cặp xác suất, so **fixed-weight, P, PI, PID**; ghi rõ clip integral, quy tắc thời gian và reset. Giữ cùng cổng trong mỗi phép đối chiếu. Tĩnh đơn lẻ và động đơn lẻ là hai mốc bổ sung để phân biệt lợi ích của nguồn thông tin với lợi ích của luật dung hợp.
2. Chọn ngưỡng cho cùng TPR mục tiêu trên validation; khóa ngưỡng và đo cả TPR/FPR thật trên test. Kiểm tra độ nhạy với thứ tự mẫu/reset và báo chênh lệch ghép cặp. Ghi riêng latency tĩnh, động, fusion và đầu cuối; không lấy các thời gian khác phạm vi chia nhau thành hệ số tăng tốc.
3. Nếu muốn kết luận tương tác PID–AL, dùng ma trận **fixed-weight/PID × random sampling/XAI-guided**, cùng initial set, pool, ngân sách, split và seed. Trong mỗi cấu hình học, hai cách fusion nhận cùng cặp xác suất. Giữa random và XAI, model tĩnh được cập nhật từ nhãn tương ứng, còn dữ liệu động và chính sách xử lý được giữ nhất quán. Cấu hình không cập nhật model chỉ cần cho câu hỏi riêng về lợi ích cập nhật dữ liệu.

**Đầu ra/thay hình:** `pid_pair_manifest.csv`, `pid_config.json`, `pid_test_predictions.csv`, `pid_ablation_summary.csv`, `pid_interaction_summary.csv`, `pid_latency.csv`, `slide04_pid_ablation.svg`. Thay bảng kết quả tại slide 4; hình tương tác có thể ở phụ lục, chỉ đưa thông điệp chính lên slide.

**Tiêu chí chấp nhận:** tính lại được metric từ dự đoán; mọi hàng so sánh có cùng phạm vi và nguồn dữ liệu; không tối ưu trên test; có số FP/FN, TPR, FPR và độ biến thiên. **PID không bắt buộc phải thắng.** Nếu không có cải thiện ổn định hoặc I/D không có ích, kết luận đúng mức và cân nhắc cấu hình đơn giản hơn.

**Trạng thái:** chưa có bộ tín hiệu động thực ghép cặp đủ để xác nhận hiệu quả bảng cũ. Phần thiết kế có thể trình bày; phần hiệu quả định lượng còn chờ phép đo này.

## 2. Slide 6: giữ AL pilot, bổ sung xuất xứ và kiểm tra FPR

**Hình/bảng hiện tại:** `pilot_al/learning_curves.png`, bảng cuối trong `final_summary.csv`. Năm phương pháp: random, uncertainty, U+H, U+V, XAI đầy đủ. XAI đầy đủ đạt AUC trung bình 0,9749; cao hơn uncertainty ở 5/5 seed với chênh lệch trung bình 0,005787. FPR thấp hơn chỉ ở 2/5 seed, dù trung bình giảm 2,333 điểm phần trăm. Ngân sách huấn luyện 200+500=700 nhãn; thêm 400 nhãn validation.

**Đầu vào còn cần:** nguồn tạo CSV, nghĩa nhãn, nguồn/họ/thời gian mẫu nếu có, quy trình trích đặc trưng và danh sách kiểm tra overlap/near-duplicate. Cần một test có nguồn gốc xác minh trước khi tuyên bố phát hiện ransomware hoặc zero-day. Muốn quy đổi chi phí chuyên gia, cần thời gian/chi phí gán nhãn thực, không chỉ số truy vấn.

**Thí nghiệm tối thiểu:** giữ nguyên năm đối chứng và công thức pilot; áp dụng trên dữ liệu đã xác minh. Dùng split và initial set ghép cặp; loại trùng và mọi tiền xử lý công bằng giữa phương pháp. Báo AUC/AP, FPR và TPR theo số nhãn. Tối ưu ngưỡng theo cùng TPR mục tiêu trên validation, không ép test có cùng TPR. Xác định test có đủ mẫu âm cho mức FPR muốn đo; luôn kèm số FP và mẫu số. Nếu kiểm tra tiết kiệm nhãn, đo ngân sách để đạt mục tiêu chất lượng đã định trước; kết quả tại cùng ngân sách chưa trả lời câu hỏi này.

**Đầu ra/thay hình:** giữ nguyên thư mục pilot làm mốc; ghi lần chạy mới vào `al_verified_run/` với `data_manifest.csv`, `config.json`, `queries.csv`, `predictions.csv.gz`, `paired_differences.csv`, `summary.json`, `slide06_al_learning_curves.svg`, `slide06_al_final_table.csv`. Thay đồ thị và bảng tại slide 6 sau khi đối chiếu nguồn; không ghi đè pilot.

**Tiêu chí chấp nhận:** xuất xứ và nghĩa nhãn đủ rõ cho tên bài toán; metric tính lại từ dự đoán; nhãn pool chỉ mở sau chọn; test độc lập với điều chỉnh thiết lập. Chênh lệch được báo theo cặp và đúng đơn vị bất định; số seed không phải chứng nhận tự động về ý nghĩa thống kê. Nếu FPR vẫn dao động, giữ kết luận cải thiện xếp hạng và báo riêng đánh đổi tại ngưỡng.

**Trạng thái:** AL pilot và ablation U/H/V đã hoàn tất, có artifact. Chưa xác nhận FPR giảm ổn định, chưa đo tiết kiệm thời gian chuyên gia, chưa xác minh nhãn ransomware-specific.

## 3. Slide 7: củng cố PE-aware và thống nhất OFS

**Hình/bảng hiện tại:** từ `pilot_fidelity/run_seed42/summary.json`: k=25, AUC trước che 0,980167; sau che top-SHAP 0,818533; sau che random trung bình 0,979910. AUC drop tương ứng 0,161633 và 0,000257. FF thô theo PDF là 2,004518; EC tương quan cấu trúc tương đồng là 0,304373; CF phân tách tâm cụm là 0,587352. Pilot không xuất OFS.

**Đầu vào còn cần:** schema các nhóm PE và quan hệ phụ thuộc, miền/kiểu hợp lệ, baseline train, quy tắc masking theo nhóm, dữ liệu hoặc phép kiểm tra tính hợp lệ của PE sau biến đổi nếu muốn tuyên bố ở mức tệp thực thi. Chọn một đặc tả FF/EC/CF/OFS thống nhất giữa công thức, code và bảng; công khai cách xử lý FF>1, EC âm và mẫu số gần0.

**Thí nghiệm tối thiểu:** giữ model và test của một lần chạy, so masking top-SHAP với random cùng ngân sách trên các nhóm được xác định trước. Khóa k/nhóm, baseline và cách chuẩn hóa trước đánh giá; thống kê số tọa độ thật sự thay đổi và mức vi phạm ràng buộc. So thêm vài mức k đã quy định để tránh kết luận từ một điểm thuận lợi. Báo AUC drop, độ đổi xác suất, EC/CF theo đúng định nghĩa; không gọi EC này là ổn định trước Gaussian noise.

Nếu dùng OFS, tính lại từ các thành phần của **cùng lần chạy** bằng một công thức đã khóa; không gộp harmonic mean trong PDF với tổng trọng số 0,5/0,3/0,2 ở code cũ. Chỉ số chưa có ngưỡng chuẩn “đáng tin”, nên ưu tiên diễn giải thành phần và đối chứng. Có thể tiếp tục bỏ OFS nếu chưa giải quyết các quy ước; điều đó không làm mất giá trị phép thử masking đã có.

**Đầu ra/thay hình:** `fidelity_spec.md`, `pe_group_schema.json`, `mask_validity_report.csv`, `mask_predictions.csv`, `mask_metrics.csv`, `fidelity_summary.json`, `slide07_fidelity_masking.svg`. Nếu có OFS đã thống nhất, thêm `ofs_recalculation.csv`; đặt chi tiết ở phụ lục kỹ thuật. Thay hình masking ở slide 7, không cần tăng số slide chính.

**Tiêu chí chấp nhận:** baseline từ train; cùng mẫu, ngân sách và quy tắc cho mọi đối chứng; kiểm tra metric từ dữ liệu lưu; công khai phép biến đổi có bảo đảm vector hay tệp PE hợp lệ đến mức nào. Bootstrap trên test chỉ phản ánh bất định có điều kiện của model đã fit; không gọi là biến thiên toàn bộ quá trình huấn luyện. Kết quả âm hoặc hạn chế cũng được giữ.

**Trạng thái:** pilot masking top-k/random, EC/CF và FF thô đã hoàn tất. Tính hợp lệ PE theo nhóm/tệp và quy tắc OFS còn cần xử lý; chưa thể dùng điểm tổng hợp để tuyên bố giải thích hoàn toàn trung thực.

## 4. Slide 8 và bước chốt phát biểu khoa học

**Nội dung hiện tại:** bảng “góp ý seminar → thay đổi → bằng chứng”. AL đã có năm cấu hình và phép so sánh cùng ngân sách; fidelity có random control và dữ liệu masking. PID còn ở thiết kế/bảng bản thảo chờ xác minh. Không đánh dấu cả ba là hoàn tất thực nghiệm.

**Đầu vào:** các artifact nêu trên cùng một danh sách phát biểu muốn nói. **Thao tác tối thiểu:** lập `claim_evidence_map.csv` với các cột `slide`, `claim`, `run_id`, `artifact`, `metric_definition`, `scope`, `status`. Mỗi số trên slide phải truy về đúng một nguồn; phân biệt bản thảo cũ, pilot và lần chạy đã xác minh. Xuất `slide08_response_matrix.csv` để thay bảng tiếp thu.

**Tiêu chí chấp nhận:** câu “đã bổ sung” mô tả đúng việc đã làm; câu “đã chứng minh” chỉ dùng trong phạm vi có đối chứng và dữ liệu hỗ trợ. Không nối AUC của AL với AUC của fidelity để tạo cải thiện giả vì hai pilot khác model/ngân sách. Không gọi tăng TP là tăng phát hiện zero-day hoặc gọi giảm FPR trung bình là giảm ổn định.

**Chốt thủ công trước mỗi lần trình bày:** đọc lại từng headline với số và phạm vi ngay cạnh; giữ ba đóng góp làm trục, thay hình từ artifact mới khi đủ điều kiện. Khi phép đo chưa hỗ trợ giả thuyết, sửa phát biểu thay vì sửa số. Dùng phiếu này để phối hợp công việc; không cần đưa toàn bộ ghi chú lên bộ slide chính.
