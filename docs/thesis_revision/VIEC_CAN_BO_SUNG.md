# Việc cần bổ sung để mở rộng kết luận

Hai phép đo AL và Fidelity đã hoàn tất trong phạm vi thăm dò. Danh sách dưới đây xác định bước tiếp theo theo mức ưu tiên; không yêu cầu thay chúng bằng số liệu đẹp hơn hoặc buộc phương pháp đề xuất phải thắng. Mỗi lần đo mới cần lưu cấu hình và đầu ra riêng, không ghi đè bằng chứng hiện có.

## Ưu tiên 1 — Xác minh dữ liệu và ý nghĩa nhãn

**Liên quan:** Mục 4.1, 4.7 và Phụ lục A.1–A.2, A.5.

- Thu thập nguồn tạo CSV, ý nghĩa nhãn0/1, cách trích đặc trưng và metadata tệp nếu còn: hash PE, nguồn, thời điểm, họ mã độc, căn cứ gán nhãn. Hash của CSV/vector không phải hash tệp PE.
- Kiểm tra overlap với dữ liệu đã dùng huấn luyện, near-duplicate và nhóm nguồn/họ. Phân hoạch không giao nhau theo dòng chưa loại trừ các dạng phụ thuộc này.
- Tạo `dataset_manifest.csv`, `label_definition.md`, `data_audit.json` và `split_manifest.csv`. Nếu không thể bổ sung nguồn gốc, tiếp tục ghi kết quả là pilot nội bộ với nhãn âm/dương; không đổi tên thành benchmark ransomware/zero-day.

**Điều kiện hoàn thành:** tên bài toán, cách chia và phạm vi kết luận có căn cứ từ metadata. Quy mô lớn hơn chỉ hữu ích sau khi nguồn và nhãn đủ rõ.

## Ưu tiên 2 — Đo đóng góp PID trên tín hiệu ghép cặp

**Liên quan:** Mục 3.2 và 4.2.

- Chuẩn bị cùng mẫu có nhãn với xác suất tĩnh, xác suất động thực, phiên bản model, chính sách cổng, thứ tự/phiên xử lý và thời gian từng tầng. Không tạo điểm động từ nhãn thật hoặc xem log minh họa là quan sát thực.
- Khóa split và quy tắc trạng thái/reset; so **fixed-weight, P, PI, PID** trên cùng cặp tín hiệu. Chọn tham số/ngưỡng trên validation; ngưỡng theo cùng TPR mục tiêu rồi khóa khi đánh giá test. Báo TPR thực đạt, FP/FN, FPR, AUC/AP và chênh lệch ghép cặp.
- Kiểm tra ảnh hưởng của thứ tự mẫu, reset, giới hạn tích phân và cách định nghĩa thời gian cập nhật. Chặn trọng số không tự chứng minh ổn định hoặc giảm FPR.

**Đầu ra:** `pid_pairs.csv`, `pid_config.json`, `pid_predictions.csv`, `pid_ablation_summary.csv` và bảng/hình thay cho phần thiết kế khi đủ dữ liệu. **Điều kiện hoàn thành:** tính lại được số liệu từ dự đoán, so sánh cùng phạm vi, test không tham gia chọn cấu hình. Nếu PID không tốt hơn, báo kết quả đó và cân nhắc cấu hình đơn giản.

## Ưu tiên 3 — Chỉ kiểm tra tương tác khi cần kết luận tích hợp

**Liên quan:** cuối Mục 4.2 và phần diễn giải 4.7.

Dùng ma trận **fixed-weight/PID × random sampling/XAI-guided**, cùng initial set, pool, ngân sách nhãn, split và seed. Trong mỗi cấu hình học, hai cách fusion nhận cùng cặp xác suất; giữa random và XAI, model tĩnh thay đổi theo nhãn được truy vấn, còn nguồn điểm động và chính sách xử lý phải nhất quán. Tĩnh đơn lẻ có thể là đối chứng phụ để tách lợi ích có thêm thông tin động.

**Đầu ra:** `fusion_al_cells.csv`, `paired_interaction.csv`, bảng2×2 và đồ thị chênh lệch. **Điều kiện hoàn thành:** đánh giá tương tác bằng chênh lệch ghép cặp trên thang metric được nêu rõ. Cấu hình đầy đủ tốt nhất chưa đủ chứng minh cộng hưởng. Đây là điều kiện cho tuyên bố tích hợp; không phải lý do phủ nhận hai pilot thành phần đã thực hiện.

## Ưu tiên 4 — Đo đúng chi phí trước khi nói về vận hành

**Liên quan:** Mục 4.1, 4.3, 4.6–4.7.

Giữ các thời gian chấm pool/SHAP/huấn luyện đã có, rồi đo thêm phần còn thiếu nếu muốn kết luận chi phí toàn hệ thống: trích đặc trưng, sắp xếp truy vấn, truyền và chờ hàng đợi, khởi tạo/quan sát động, fusion và thời điểm có quyết định cuối. Ghi tải máy, số mẫu, tỷ lệ kích hoạt động và warm/cold run; báo trung vị và phân vị đuôi phù hợp với số lần đo. Không đổi thời gian fusion thành thời gian phát hiện đầu cuối.

Muốn nói tiết kiệm nhãn, đặt trước chất lượng mục tiêu và đo số nhãn cần để đạt đích. Muốn nói tiết kiệm chi phí chuyên gia, ghi thời gian/độ khó gán nhãn thực; 400 nhãn validation cũng là nguồn lực cần công khai.

**Đầu ra:** `timing_protocol.md`, `stage_timings.csv`, `cost_to_target.csv` khi có phép đo tương ứng. **Điều kiện hoàn thành:** nêu rõ điểm bắt đầu/kết thúc và phần được tính; không quy đổi số truy vấn thành tiền hoặc thời gian bằng giả định chưa kiểm chứng.

## Bổ sung theo mục tiêu — Độ ổn định và Fidelity PE-aware

**AL, Mục 4.3/4.7:** ưu tiên dữ liệu có nguồn hoặc split độc lập theo thời gian/nhóm trước khi chỉ tăng seed trên cùng test. Giữ ghép cặp giữa phương pháp, báo FPR cùng TPR; nếu FPR tiếp tục dao động thì giới hạn kết luận ở chất lượng xếp hạng. Năm seed không tự bảo đảm ý nghĩa thống kê. Không xem các vòng học phụ thuộc là quan sát độc lập.

**Fidelity, Mục 3.4/4.4 và A.4:** chuẩn hóa schema nhóm phụ thuộc, miền và kiểu của đặc trưng; định nghĩa masking theo nhóm cùng ngân sách với random. Ghi số chiều thực sự thay đổi và các ràng buộc bị vi phạm. Nếu tuyên bố hợp lệ ở mức PE thực thi, cần kiểm tra trên tệp tương ứng; masking vector đơn thuần không đủ. Thêm seed/model/split khi muốn mở rộng kết luận vượt một model đã fit.

Trước khi dùng OFS, khóa một đặc tả FF/EC/CF, cách xử lý miền giá trị và công thức tổng hợp, rồi tính từ cùng lần chạy. Không ghép harmonic mean với số của tổng trọng số khác. Có thể tiếp tục báo các thành phần và random control nếu OFS chưa đem lại cách diễn giải rõ hơn.

**Đầu ra:** `fidelity_spec.md`, `pe_group_schema.json`, `mask_validity.csv`, `fidelity_summary.json`; thêm `ofs_recalculation.csv` chỉ khi đã thống nhất quy tắc. **Điều kiện hoàn thành:** kết luận tương ứng với phép kiểm tra thực sự đã làm, giữ cả kết quả không thuận lợi.

## Chốt nội dung trước lần bảo vệ tiếp theo

Lập một bảng ngắn `claim_evidence_map.csv`: phát biểu, mục luận văn/slide, lần chạy, tệp bằng chứng, phạm vi và trạng thái. Kiểm tra số liệu khớp artifact, tóm tắt và kết luận. Dùng “đã đo” cho AL/Fidelity trong phạm vi hiện tại, “đề xuất/thiết kế” cho hiệu quả dung hợp chưa kiểm chứng. Không tuyên bố hệ thống đã sẵn sàng vận hành hoặc đã xử lý đầy đủ mọi góp ý khi các điều kiện về dữ liệu và tín hiệu động còn thiếu.
