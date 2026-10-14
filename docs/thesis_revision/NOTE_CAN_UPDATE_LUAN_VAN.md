# Ghi chú rà soát LaTeX luận văn — 14/10/2026

Đã đọc nguồn trong `Luan_van_Luu_Van_Doanh_UET.zip`, đối chiếu thêm PDF mới `thesis (2).pdf` (80 trang vật lý), mã triển khai và các artifact AL/Fidelity đã lưu. PDF mới vẫn chứa các bảng số liệu đang được rà soát; khác biệt với PDF trong ZIP chủ yếu ở dàn trang và bỏ trang danh mục công trình. Các nhận xét dưới đây phân biệt **vấn đề của bản gửi**, **việc đã sửa trong bản nháp** và **việc còn cần bằng chứng**. Không coi việc sửa câu chữ là đã hoàn tất thực nghiệm.

Lưu ý vị trí: `chapters/c1/` tương ứng **Chương 2**; `chapters/c2/` là **Chương 3**; `chapters/c3/` là **Chương 4**. Số bảng có thể thay đổi sau biên dịch, nên dùng tên file và mục để sửa.

## Nhận định chính

Ba đóng góp nên giữ làm trục trình bày, nhưng phải trả lời riêng ba câu hỏi: **PID cải thiện gì so với cách dung hợp đơn giản? XAI giúp chọn mẫu tốt hơn uncertainty thế nào? Phép đo nào chứng minh giải thích phản ánh hành vi mô hình?** Điểm yếu cần xử lý trước là sự nhất quán và khả năng truy vết của bằng chứng, không phải số lượng trang.

| Ưu tiên | Phần cần cập nhật | Trạng thái bản nháp |
|---|---|---|
| Bắt buộc | Dữ liệu, số chiều, cách chia và nguồn nhãn — 4.1 | Đã mô tả đúng phép đo hiện có; vẫn cần xác minh nguồn |
| Bắt buộc | Công thức, mã và đối chứng PID — 3.2, 4.2 | Đã đồng bộ đặc tả; chưa có kết quả PID ghép cặp thực |
| Bắt buộc | Tách lợi ích AL khỏi việc có thêm nhãn — 3.3, 4.3 | Đã bổ sung năm chiến lược, năm seed |
| Bắt buộc | Miền giá trị FF/EC/CF, OFS và masking — 3.4, 4.4 | Đã sửa công thức/diễn giải và bổ sung đối chứng; chưa kiểm chứng PE sau che |
| Bắt buộc | Mâu thuẫn số liệu và phạm vi latency — 4.2–4.6 | Đã thay bằng số có artifact; còn thiếu đo đầu cuối |
| Quan trọng | Đối chiếu công trình gần nhất — 2.4 | Vẫn cần bổ sung bảng công trình cụ thể |
| Quan trọng | Hiệu quả kết hợp PID + AL — 4.2 | Đã đặc tả thiết kế 2×2; chưa có kết quả |
| Đồng bộ | Minh họa, tóm tắt, kết luận, phụ lục | Đã sửa theo phạm vi bằng chứng; tác giả cần duyệt |

## 1. Dữ liệu thực nghiệm: cần chốt trước các bảng kết quả

**Vị trí:** `chapters/c3/c3_1.tex` — Mục 4.1; đồng bộ `chapters/c2/c2_1.tex`, `c2_2.tex` và `chapters/appendices.tex`.

**Bản gửi:** mô tả 20.000 tệp, 1.024 đặc trưng, chia 70/10/20, có các họ WannaCry/LockBit/Ryuk và tỷ lệ packed. Các mô tả này cần manifest hoặc dữ liệu tương ứng; CSV đang được dùng cho phép đo bổ sung có 2.000 dòng, 2.381 đặc trưng và chưa xác minh metadata họ.

**Cần cập nhật:** ghi đúng nguồn, ý nghĩa nhãn, đơn vị mẫu, schema, split, seed và kiểm tra trùng của từng thí nghiệm. Không gọi số dòng CSV là số tệp độc lập đã xác minh. Không coi “chưa xuất hiện trong tập khởi tạo” là bằng chứng zero-day.

**Đã sửa trong nháp:** phép đo 1.200 train/pool, 400 validation, 400 test; nhãn âm/dương và SHA-256 đầu vào. **Còn cần:** nguồn tạo CSV, căn cứ nhãn ransomware, hash tệp/metadata nếu muốn kết luận đặc thù cho ransomware. Nếu bộ 20.000 tệp có thật, cần cung cấp artifact của bộ đó và báo thành thí nghiệm riêng, không ghép số từ hai bộ.

## 2. PID: phải thống nhất công thức và lý do hiệu quả

**Vị trí:** `chapters/c2/c2_2.tex` — Mục 3.2; `chapters/c3/c3_2.tex` — Mục 4.2.

**Bản gửi:** trình bày PID liên tục, rời rạc hóa theo Δt, chống tích lũy và trọng số động. Triển khai tham chiếu dùng tổng sai lệch và sai phân theo bước, với phép chặn trọng số; không tự đồng nghĩa đã có anti-windup cho tích phân. Cần đối chiếu cặp quy ước dấu sai lệch và nguồn nhận trọng số: đổi cả hai có thể tương đương, nhưng đổi một bên thì đổi hành vi.

**Cần cập nhật:** chỉ rõ e, trạng thái tích lũy, bước cập nhật, reset theo phiên, trọng số của nguồn nào, hệ số được chọn bằng cách nào. Tách **chứng minh điểm dung hợp nằm giữa hai đầu vào** khỏi **bằng chứng AUC/FPR tốt hơn**. O(1) chỉ nói về bước fusion khi đã có hai điểm.

**Đã sửa trong nháp:** đặc tả rời rạc khớp triển khai và phân tích thành phần P. Với hệ số P không âm, cơ chế riêng P có thể thiên về điểm lớp dương lớn hơn; đây không phải bảo đảm giảm cảnh báo nhầm. **Còn cần:** cùng mẫu có điểm tĩnh và điểm động thực; so Static-only, Dynamic-only, trung bình 50/50, fixed-weight đã chọn trên validation, P/PI/PID. Giữ chung nguồn tín hiệu, cửa sổ quan sát, cổng và quy tắc trạng thái.

## 3. AL: chứng minh giá trị của XAI ở cùng ngân sách

**Vị trí:** `chapters/c2/c2_3.tex` — Mục 3.3; `chapters/c3/c3_3.tex` — Mục 4.3.

**Bản gửi:** đường học từ 2.000 lên 2.500 nhãn chưa tách được tác động của thêm dữ liệu và tiêu chí chọn mẫu. Các baseline cần chung initial set, ngân sách, mô hình và ngưỡng. Nếu “entropy sampling” là entropy nhị phân của cùng xác suất p, nó có cùng thứ hạng bất định với margin sampling; phải định nghĩa rõ trước khi coi đó là đối chứng khác.

**Cần cập nhật:** Random, Uncertainty, U+H, U+V, cấu hình đầy đủ; báo theo seed ghép cặp. Nêu H là entropy khối lượng SHAP dương/âm, V là phương sai SHAP có dấu; V không phải bất định dự đoán giữa các cây. Không nói đã sàng lọc ứng viên/giới hạn họ nếu runner chấm toàn pool.

**Đã sửa trong nháp:** năm seed, 200 nhãn khởi tạo + 5×100 truy vấn, cùng ngân sách 700 nhãn. AUC trung bình XAI đầy đủ **0,974873**, Uncertainty **0,969087**; chênh lệch dương ở **5/5 seed**. FPR thấp hơn chỉ ở **2/5 seed**, nên không kết luận giảm FPR ổn định. 400 nhãn validation là chi phí bổ sung, không nằm trong 700 nhãn huấn luyện.

**Còn cần nếu muốn nói tiết kiệm nhãn:** đặt trước chất lượng mục tiêu trên validation rồi đo ngân sách để đạt đích. Muốn nói tiết kiệm thời gian chuyên gia thì cần đo thao tác gán nhãn thực; oracle lấy nhãn có sẵn chưa cung cấp bằng chứng này.

## 4. Fidelity/OFS: sửa định nghĩa trước khi diễn giải điểm

**Vị trí:** `chapters/c2/c2_4.tex` — Mục 3.4; `chapters/c3/c3_4.tex` — Mục 4.4; phụ lục.

**Cần cập nhật về toán:** FF dạng thay đổi xác suất tương đối có thể vượt 1; EC dạng Pearson thuộc [-1,1]; CF theo chuẩn mẫu lớn nhất có thể tới 2. Vì vậy chưa thể trực tiếp gộp các số thô thành một thang chất lượng chung. Trung bình điều hòa nhấn mạnh thành phần thấp, nhưng tự nó không chứng minh độ đo phù hợp bài toán mã độc.

**Lỗi số cần đối chiếu trong bản gửi:** FF = 0,3328, EC = 0,3008, CF = 0,5230 cho trung bình điều hòa khoảng **0,364019**, không phải **0,3612**. Cần kiểm tra công thức triển khai, phép biến đổi và lần chạy nguồn; không chỉnh tay một ô cho khớp.

**Cần cập nhật về thực nghiệm:** nêu rõ model được giải thích, top-k, baseline lấy từ train, cách tính tương đồng, xử lý vector 0, thang raw score của SHAP và thang xác suất của phép đo. So top-SHAP với random cùng k; nếu kết luận tốt hơn bộ giải thích khác thì cần thêm bộ giải thích đó làm đối chứng.

**Đã sửa trong nháp:** k = 10/25/50, 20 lần random; ở k=25, AUC trước che **0,980167**, sau top-SHAP **0,818533**, random trung bình **0,979910**. Đây là model riêng, không phải model AL vòng cuối. Báo riêng FF/EC/CF, không xuất OFS khi chưa chốt phép tổng hợp.

## 5. Chuyển độ đo từ ảnh sang PE: phải nói rõ giới hạn phép che

**Vị trí:** cuối Mục 3.4; Mục 4.4, 4.7; `chapters/appendices.tex`.

Pixel ảnh và các trường PE không có cùng cấu trúc. Đặc trưng PE gồm số đếm, cờ, kích thước, bucket băm và các trường phụ thuộc; thay riêng từng chiều bằng trung bình có thể tạo vector không tương ứng với tệp hợp lệ. Bucket băm cũng không nhất thiết xác định duy nhất một API.

**Bản gửi:** mô tả masking theo nhóm, trung vị làm tròn và ràng buộc PE như đã áp dụng. **Đã sửa trong nháp:** ghi đúng phép thử đang chạy là thay từng cột bằng trung bình train; nêu rõ kết quả đánh giá phản ứng của model trước biến đổi vector. **Còn cần:** schema nhóm phụ thuộc, kiểm tra miền và đối chứng cùng ngân sách biến đổi; chỉ tuyên bố hợp lệ ở mức tệp khi có kiểm tra tệp PE tương ứng.

## 6. Bảng phân loại và overhead: tránh so khác cấu hình/phạm vi

**Vị trí:** `chapters/c3/c3_2.tex`, `c3_3.tex`, `c3_6.tex` — Mục 4.2, 4.3, 4.6.

**Điểm cần giải thích:** ma trận cuối trong bản gửi có FP=48 và TN=2.952, tức **FPR=1,6%**; bảng PID ghi **0,8%**. Hai số có thể thuộc cấu hình/ngưỡng khác nhau, nhưng phải chỉ rõ và truy vết từ dự đoán. Không tự xem chúng là cùng kết quả.

Độ trễ Static-only, Dynamic-only và fusion trong bảng cũ có phạm vi khác nhau. Không thể dùng riêng 15,2 ms của fusion để kết luận nhanh hơn 1.205,4 ms quan sát động theo nghĩa đầu cuối. Ghi rõ thiết bị đã dùng, mốc bắt đầu/kết thúc, số lần đo, trung vị/p95 khi đủ mẫu và tỷ lệ kích hoạt động.

**Đã sửa trong nháp:** bảng cấu hình đúng runner và thời gian có phạm vi đo. Ví dụ chấm pool XAI đầy đủ khoảng 31,65 ms/lượt so với 2,71 ms của Uncertainty; đây không phải độ trễ phát hiện từng tệp. **Còn cần:** log timing từng tầng và đầu cuối nếu muốn kết luận về chi phí vận hành.

## 7. Kết hợp toàn hệ thống: cần ma trận bốn cấu hình

**Vị trí:** cuối `chapters/c3/c3_2.tex` — Mục 4.2.

Thiết kế tối thiểu: **fixed-weight + Random; PID + Random; fixed-weight + XAI-AL; PID + XAI-AL**. Giữ cùng dữ liệu, ngân sách, initial set, split và seed. Uncertainty là đối chứng bổ sung để tách lợi ích của XAI khỏi AL thông thường.

So từng cặp để xác định tác động PID và AL; nếu muốn nói “cộng hưởng”, phải xét chênh lệch giữa các tác động trên cùng thang chỉ số. Cấu hình đầy đủ đứng đầu chưa đủ chứng minh tương tác. **Bản nháp đã có thiết kế, chưa có kết quả đo bốn cấu hình.**

## 8. Nghiên cứu liên quan: cần chỉ ra khác bài nào, ở điểm nào

**Vị trí:** `chapters/c1/c1_4.tex` — Mục 2.4; `chapters/introduction.tex` — Mục 1.2.

Bảng hiện tại chủ yếu so các nhóm phương pháp. Cần thêm khoảng **3–5 công trình gần nhất** có trích dẫn cụ thể, đối chiếu đầu vào, cách dung hợp, tiêu chí AL, cách đánh giá XAI và điểm khác của luận văn. Các câu “ít nghiên cứu”, “chưa có” cần phạm vi tài liệu rõ; không gán nhược điểm cho một bài chỉ vì bài đó có mục tiêu khác.

Không so trực tiếp AUC từ các bài dùng bộ dữ liệu/cách chia khác nhau để khẳng định vượt trội. Tính mới nằm ở phần phương pháp đã xác định và kiểm chứng, không phải ở việc dùng các thành phần phổ biến. **Phần này vẫn cần cập nhật trong nháp; chưa bổ sung tài liệu mới chưa được kiểm tra.**

## 9. Minh họa, khả năng triển khai và tuyên bố cuối

**Vị trí:** `chapters/c2/c2_1.tex`; `chapters/c3/c3_5.tex`, `c3_6.tex`; `chapters/abtract_vi.tex`, `abtract_en.tex`, `introduction.tex`, `conclusion.tex`.

- Watchdog theo dõi hệ thống tệp không tự cung cấp API hooking. Các mô tả CryptEncrypt/process injection cần nguồn quan sát tương ứng nếu viết là tính năng đã triển khai.
- TreeSHAP của LightGBM tĩnh giải thích đầu ra model đó; chưa tự giải thích quyết định PID kết hợp động. Hình SHAP phải gắn đúng model và thang đầu ra.
- Kịch bản LockBit giả lập không dùng làm kết quả mẫu thật. Bản nháp thay bằng một hàng test Fidelity có dự đoán và SHAP lưu kèm.
- Bảng tham số cố định không được gọi là “kết quả tối ưu” nếu chưa có lịch sử tìm kiếm. Bản nháp đã sửa cách gọi.
- Tóm tắt/kết luận phải cùng mức khẳng định với Chương 4: AL và Fidelity có phép đo thăm dò; PID còn thiếu đối chứng động thực; không kết luận đã triệt tiêu cảnh báo rác hoặc sẵn sàng triển khai SOC.

## 10. Việc trình bày cuối cùng

**Vị trí:** `thesis.tex`, `references.bib`, phụ lục và hai trang lời cảm ơn/cam đoan.

Đồng bộ tên/đơn vị chỉ số, AP khác với các cách tính diện tích PR bằng hình thang, số chiều, seed, ngưỡng, phạm vi SHAP và artifact. Giữ cùng số liệu trong bảng, biểu đồ, tóm tắt và slide. Các cảnh báo về nguồn dữ liệu chi tiết có thể tập trung ở giao thức và hạn chế, nhưng không bỏ điều kiện cần để hiểu đúng kết quả.

Bản nháp đã biên dịch 78 trang; PDF hiện dùng Liberation Serif dự phòng, nên cần biên dịch lại với font theo quy định trường trước khi nộp. Ngày tháng và nội dung cam đoan vẫn cần tác giả rà soát; không tự thêm xác nhận/chữ ký.

## Thứ tự xử lý đề xuất

1. Chốt nguồn dữ liệu và khóa định nghĩa/cấu hình dùng cho các kết quả.
2. Hoàn thiện các mục AL/Fidelity từ artifact hiện có; kiểm tra lại bảng, hình và công thức.
3. Ưu tiên thu thập cặp tín hiệu tĩnh–động để làm ablation PID; sau đó mới đo ma trận kết hợp.
4. Bổ sung bảng công trình gần nhất và phát biểu ba đóng góp đúng phạm vi.
5. Đồng bộ tóm tắt, kết luận, phụ lục và slide.

Các đầu ra thực nghiệm cụ thể nằm trong `VIEC_CAN_BO_SUNG.md`; nội dung đã chỉnh sửa được liệt kê tại `THAY_DOI_THUC_NGHIEM.md`.
