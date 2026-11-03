# Kịch bản trình bày luận văn trong 15 phút

**Người trình bày:** Lưu Văn Doanh  
**Người nghe:** Giảng viên hướng dẫn  
**Bám theo:** 15 slide trong `Luan_van_Luu_Van_Doanh_UET_format_pdflatex.tex`  
**Thời lượng dự kiến:** 14 phút 30 giây, dành 30 giây dự phòng. Chưa tính phần hỏi đáp.

Mạch kể xuyên suốt: **một tệp có điểm rủi ro chưa rõ cần thêm bằng chứng, một lời giải thích hữu ích và một cách học từ lần xem xét đó.** Mẫu M-001 là tình huống giả định, không phải một ca phát hiện đã xảy ra.

## Cách sử dụng

- Phần trong khối trích dẫn là lời nói có thể luyện trực tiếp. Chữ **đậm** là chỗ nên nhấn giọng.
- Phần *in nghiêng* là chỉ dẫn trình bày, không đọc thành lời. Mốc giờ tính từ lúc bắt đầu nói ở bìa.
- Nói như đang trao đổi với Thầy. Dùng slide để chỉ vào sơ đồ và ví dụ, hạn chế nhìn màn hình đọc lại chữ.
- Mốc thời gian là kế hoạch luyện tập. Hãy bấm giờ một lượt với nhịp nói thật, bao gồm các khoảng dừng, rồi điều chỉnh theo hướng dẫn cuối file.

## Bảng phân bổ thời gian

| Slide | Nội dung | Thời lượng | Mốc kết thúc |
|---|---|---:|---:|
| 1 | Bìa và tình huống mở đầu | 45 giây | 00:45 |
| 2 | Tổng quan nội dung | 25 giây | 01:10 |
| 3 | Bài toán và mục tiêu | 55 giây | 02:05 |
| 4 | Nền tảng kế thừa và phần đề xuất | 55 giây | 03:00 |
| 5 | LightGBM và TreeSHAP | 55 giây | 03:55 |
| 6 | Kiến trúc tổng thể | 80 giây | 05:15 |
| 7 | Hình thành điểm động | 50 giây | 06:05 |
| 8 | Trực giác về PID | 65 giây | 07:10 |
| 9 | XAI-Guided Active Learning | 65 giây | 08:15 |
| 10 | Kiểm chứng giải thích | 55 giây | 09:10 |
| 11 | Thiết kế đánh giá | 40 giây | 09:50 |
| 12 | Kết quả chính | 70 giây | 11:00 |
| 13 | Báo cáo minh họa M-001 | 90 giây | 12:30 |
| 14 | Tiến độ và điều kiện hoàn thiện | 65 giây | 13:35 |
| 15 | Kết luận và xin góp ý | 55 giây | 14:30 |

---

## Slide 1 — Bìa và tình huống mở đầu

**00:00–00:45.** Mục tiêu: tạo một tình huống để người nghe muốn theo dõi cách giải quyết.

*Nhìn Thầy, nói chậm ở hai câu đầu. Không đọc toàn bộ tên đề tài trên bìa.*

> Em kính chào Thầy. Em là Lưu Văn Doanh. Hôm nay em xin báo cáo hướng tiếp cận và tiến độ luận văn.
>
> Trước khi vào nội dung, em xin mời Thầy hình dung một tình huống giả định: một tệp thực thi được đưa vào phân tích và mô hình trả về điểm rủi ro **0,55**.
>
> Với một điểm như vậy, chuyên gia nên kết luận ngay, hay yêu cầu thêm bằng chứng? Và nếu cần xem xét thêm, hệ thống sẽ giải thích điều gì để hỗ trợ chuyên gia?

*Dừng khoảng 2 giây. Đây là câu hỏi dẫn dắt, không cần chờ câu trả lời.*

> Luận văn của em đi từ tình huống đó. Em sẽ quay lại mẫu này ở phần minh họa để cho thấy các thành phần kết nối với nhau như thế nào.

*Chuyển slide.*

## Slide 2 — Tổng quan nội dung

**00:45–01:10.** Mục tiêu: cho người nghe biết đích đến của bài nói.

> Trong khoảng mười lăm phút, em sẽ đi theo mạch trên màn hình: từ bài toán và đóng góp, đến kiến trúc, các cơ chế đề xuất và kết quả chính.
>
> Phần cuối là một báo cáo minh họa và kế hoạch hoàn thiện. Em xin tập trung vào **vì sao cần từng thành phần và chúng bổ sung cho nhau ra sao**; các chi tiết thực nghiệm em sẽ trao đổi thêm khi Thầy cần.

*Chuyển ngay sang slide 3, không đọc năm mục trong danh sách.*

## Slide 3 — Bài toán và mục tiêu nghiên cứu

**01:10–02:05.** Mục tiêu: làm rõ khó khăn của người sử dụng hệ thống.

> Bài toán em xét là phân tích tệp thực thi Windows PE, với định hướng ứng dụng vào phát hiện ransomware.
>
> Khi xây dựng quy trình này, có một đánh đổi: phân tích tĩnh cho điểm ban đầu tương đối nhanh, nhưng một số mẫu vẫn chưa đủ rõ để kết luận. Quan sát hành vi có thể bổ sung thông tin, nhưng cần thời gian và tài nguyên thu thập.
>
> Với chuyên gia, một cảnh báo còn đặt ra việc phải kiểm tra: mô hình dựa vào đặc trưng nào, bằng chứng đã đủ chưa và mẫu này có đáng dành công sức gán nhãn hay không.
>
> Vì vậy, mục tiêu của em là xây dựng một quy trình **biết khi nào cần thêm bằng chứng và hỗ trợ người phân tích xem xét quyết định**. Hướng ứng dụng là ransomware; phần đã kiểm chứng hiện tại nằm trên dữ liệu malware tĩnh.

*Nhấn câu chuyển, rồi chuyển slide.*

> Từ bài toán đó, em xác định phần kế thừa và phần cần triển khai, đánh giá trong luận văn.

## Slide 4 — Nền tảng kế thừa và phần đề xuất của luận văn

**02:05–03:00.** Mục tiêu: giúp Thầy nhận ra giá trị riêng của đề tài.

*Chỉ vào cột giữa của bảng, không đọc lần lượt từng ô.*

> EMBER, LightGBM, TreeSHAP và vòng học tích cực là các nền tảng em kế thừa. Phần em tập trung triển khai và khảo sát nằm ở cột giữa.
>
> Thứ nhất là cách kết hợp điểm tĩnh và động theo **lịch sử bất đồng** giữa hai nguồn. Thứ hai là dùng thêm thông tin từ SHAP để lựa chọn mẫu gán nhãn. Thứ ba là xây dựng quy trình kiểm tra giải thích bằng đối chứng và đánh giá độ ổn định.
>
> Mỗi hướng đều đi kèm một câu hỏi kiểm chứng: PID có thêm giá trị so với trọng số cố định không? SHAP có giúp chọn mẫu tốt hơn chỉ dùng xác suất không? Và các đặc trưng được giải thích là quan trọng có thực sự ảnh hưởng đến mô hình không?
>
> Em muốn làm rõ giá trị của những lựa chọn này qua đối chứng, thay vì chỉ mô tả việc ghép các công cụ.

*Chuyển slide.*

## Slide 5 — Nền tảng tĩnh: LightGBM và TreeSHAP

**03:00–03:55.** Mục tiêu: giải thích vai trò công cụ bằng ngôn ngữ dễ theo dõi.

> Quy trình bắt đầu bằng việc biểu diễn tệp PE thành vector đặc trưng EMBER. Các nhóm đầu vào mô tả những thuộc tính như thống kê byte, entropy, header, section và import.
>
> LightGBM đọc vector đó và tạo điểm phân loại ban đầu. TreeSHAP bổ sung cách nhìn vào dự đoán: những đặc trưng nào kéo điểm về phía malware, những đặc trưng nào kéo theo hướng ngược lại.
>
> Một điểm em muốn nhấn mạnh là **các mẫu có điểm dự đoán gần nhau vẫn có thể có cấu trúc giải thích khác nhau**. Chính sự khác nhau này là thông tin em tiếp tục khai thác cho Active Learning.
>
> Khi diễn giải, em giữ SHAP trong phạm vi giải thích hành vi của mô hình. Muốn nói một tọa độ liên quan đến API hay section nào, cần có ánh xạ đặc trưng tương ứng.

*Chuyển slide.*

> Hai đầu ra là điểm tĩnh và giải thích sẽ đi vào kiến trúc tổng thể sau đây.

## Slide 6 — Kiến trúc phát hiện, cập nhật và kiểm chứng

**03:55–05:15.** Mục tiêu: giúp người nghe nhìn được toàn bộ hệ thống mà không lạc trong sơ đồ.

*Di con trỏ theo nhánh trên trước. Chỉ chuyển xuống nhánh nét đứt sau khi nói xong đường quyết định.*

> Em xin đi theo hai phần của sơ đồ. Phần nét liền là đường ra quyết định cho từng tệp; phần nét đứt là vòng cập nhật và đánh giá.
>
> Ở nhánh trên, tệp đi qua LightGBM và TreeSHAP. Cổng chuyển tuyến xem xét mức chắc chắn. Mẫu đủ chắc chắn có thể nhận quyết định tĩnh sớm; mẫu chưa rõ được chuyển sang quan sát động.
>
> Khi đã có điểm tĩnh và điểm động của đúng mẫu, cơ chế dung hợp mới tạo điểm kết hợp. Như vậy, **cổng chuyển tuyến quyết định có cần thêm quan sát; PID thực hiện dung hợp sau khi có hai điểm**.

*Chỉ xuống nhánh nét đứt.*

> Các đầu ra được lưu cùng định danh model, dữ liệu và report. Từ những mẫu trong pool, Active Learning lựa chọn mẫu để chuyên gia gán nhãn, rồi mô hình được huấn luyện lại và lưu phiên bản.
>
> Ở nhánh còn lại, Fidelity kiểm tra giải thích với đúng model và dữ liệu liên quan. Phần này phục vụ đánh giá, không bắt buộc chặn đường cảnh báo của mỗi tệp.
>
> Kiến trúc vì vậy nối việc ra quyết định hiện tại với việc cải thiện và kiểm tra mô hình về sau.

*Dừng ngắn để người nghe nhìn sơ đồ, rồi chuyển slide.*

## Slide 7 — Từ sự kiện quan sát đến điểm động

**05:15–06:05.** Mục tiêu: giải thích điểm động có nguồn gốc như thế nào.

> Để kết hợp được hai nguồn, em cần làm rõ nguồn gốc của điểm động.
>
> Theo thiết kế, các sự kiện được gom trong cùng một lần thực thi, chẳng hạn số tệp bị ghi, đổi tên hoặc xóa, tại các mốc quan sát trên màn hình. Những thống kê này tạo thành đầu vào cho một bộ chấm điểm động.
>
> Bộ chấm điểm chỉ được sử dụng thông tin đã xuất hiện đến thời điểm đang xét. Nó cần được huấn luyện từ train, lựa chọn trên validation và khóa trước test.
>
> Đây là phần còn cần dữ liệu động để hoàn thiện. Điều kiện quan trọng là **feature tĩnh và report động phải thuộc cùng một mẫu**, được ghép bằng định danh, chứ không ghép hai nguồn có điểm số trông giống nhau.

*Chuyển slide.*

## Slide 8 — Vì sao khảo sát PID thay cho trọng số cố định?

**06:05–07:10.** Mục tiêu: trình bày động cơ phương pháp, không giảng lại lý thuyết điều khiển.

*Chỉ công thức phía trên một lần, sau đó hướng sự chú ý sang hai cột.*

> Khi có hai điểm, cách kết hợp dễ hiểu nhất là dùng một trọng số cố định. Đây là baseline quan trọng vì đơn giản và dễ kiểm tra.
>
> Tuy nhiên, qua các cửa sổ quan sát, mức bất đồng giữa điểm tĩnh và động có thể thay đổi. Một chênh lệch chỉ xuất hiện ở một thời điểm và một chênh lệch kéo dài có lịch sử khác nhau, dù đôi lúc chúng cho cùng giá trị hiện tại.
>
> Từ đó, em khảo sát một quy tắc lấy ý tưởng từ PID: P phản ánh bất đồng hiện tại, I tích lũy bất đồng theo thời gian và D phản ánh tốc độ thay đổi. Các thông tin này dùng để cập nhật trọng số dung hợp.
>
> **Giả thuyết là lịch sử có thể bổ sung giá trị cho quyết định.** Để kết luận, em cần so với Fixed, P và PI trên cùng đầu vào. Nếu lợi ích không đủ rõ, sự đơn giản của trọng số cố định vẫn là một ưu điểm cần giữ trong đánh giá.

*Chuyển slide.*

## Slide 9 — XAI-Guided Active Learning

**07:10–08:15.** Mục tiêu: nối giải thích với một lợi ích cụ thể trong công việc gán nhãn.

> Sau việc kết hợp bằng chứng, câu hỏi tiếp theo là mô hình nên học thêm từ mẫu nào.
>
> Giả sử chuyên gia chỉ có thể gán nhãn một số lượng mẫu nhất định. Uncertainty ưu tiên mẫu mà mô hình đang phân vân. Em khảo sát thêm thông tin từ cấu trúc giải thích SHAP.
>
> Hai mẫu có điểm dự đoán tương tự nhau, nhưng ở một mẫu, các đóng góp có thể kéo mạnh theo hai hướng trái ngược. Sự khác biệt đó gợi ý rằng chỉ nhìn xác suất chưa mô tả hết những gì mô hình đang sử dụng.
>
> Vì vậy, điểm chọn mẫu kết hợp bất định, entropy hướng đóng góp và phương sai SHAP. Từng tín hiệu được chuẩn hóa trên pool trước khi ghép.
>
> Sau bước chọn, **chuyên gia vẫn là người phân tích và cung cấp nhãn**. Trong đánh giá offline, em mô phỏng bước truy vấn bằng việc mở nhãn sẵn có theo cùng ngân sách. Lợi ích cần đo là chọn mẫu có hiệu quả hơn các baseline hay không.

*Chuyển slide.*

## Slide 10 — Kiểm chứng giải thích TreeSHAP

**08:15–09:10.** Mục tiêu: thể hiện tư duy kiểm chứng thay vì chỉ trình diễn hình SHAP.

> Khi đã dùng SHAP để hỗ trợ quyết định và chọn mẫu, em cần kiểm tra chính lời giải thích đó.
>
> Bước đầu là kiểm tra tính cộng: tổng đóng góp và bias phải tái tạo raw score của đúng mô hình đã lưu.
>
> Sau đó, em thay thế giá trị của các đặc trưng được xếp quan trọng và so với việc thay thế ngẫu nhiên cùng số lượng. Nếu thứ hạng phản ánh những gì model sử dụng, tác động của hai cách che cần thể hiện khác biệt.
>
> Cuối cùng, em xem giải thích thay đổi đến đâu khi đổi seed hoặc cách chia dữ liệu. Một kết quả hữu ích cần cho biết cả mức ảnh hưởng và mức ổn định.
>
> Các kiểm tra này được báo riêng. Phép che diễn ra trong không gian feature, nên kết luận cũng được giữ trong phạm vi đó.

*Chuyển slide.*

## Slide 11 — Thiết kế đánh giá và phạm vi dữ liệu

**09:10–09:50.** Mục tiêu: cung cấp đủ bối cảnh để đọc kết quả, tránh sa vào mô tả dataset.

> Để đọc đúng kết quả, em xin giữ lại những thông tin thiết yếu trên slide này.
>
> Phần static dùng hai nghìn mẫu EMBER có định danh. Nhãn dương ở đây là malware nói chung. Các phương pháp AL được so ở cùng ngân sách và cùng tập khởi tạo tương ứng, qua nhiều phân hoạch và seed.
>
> Nguyên tắc em giữ là tách bước lựa chọn cấu hình khỏi bước đánh giá test. Model, dự đoán và các đầu ra được lưu để kiểm tra lại.
>
> Nhờ đó, các thông điệp ở bảng tiếp theo có thể truy về cùng một giao thức so sánh.

*Chuyển ngay sang kết quả.*

## Slide 12 — Kết quả chính: Active Learning và Fidelity

**09:50–11:00.** Mục tiêu: người nghe nhớ được kết quả và đánh đổi, không phải nhớ các số thập phân.

*Chỉ bảng AL bên trái. Chỉ đọc số phục vụ thông điệp, không đọc toàn bộ bảng.*

> Ở phần Active Learning, các biến thể dùng thông tin SHAP cải thiện so với Random trong đánh giá này. U cộng H tốt nhất về ROC-AULC, tức hiệu năng được tổng hợp dọc theo ngân sách nhãn.
>
> Nhưng phương pháp tốt nhất về đường học và phương pháp cần ít nhãn nhất lại khác nhau. U cộng V đạt target với trung bình **488 nhãn**, trong khi Random là **584 nhãn**.
>
> Đồng thời, lợi ích so với Uncertainty nhỏ và tùy chỉ số. Em giữ kết quả này để thể hiện đúng đánh đổi: cấu hình đầy đủ không mặc nhiên đứng đầu mọi tiêu chí.

*Chuyển con trỏ sang bảng Fidelity.*

> Với Fidelity, dưới cả hai baseline, che top-SHAP làm AUC giảm mạnh hơn che ngẫu nhiên cùng số lượng. Kết quả hỗ trợ giá trị của thứ hạng giải thích với model.
>
> Như vậy, em có bằng chứng cho việc khai thác và kiểm tra giải thích trên phần static. Phần tiếp theo minh họa các đầu ra ấy có thể được trình bày cho chuyên gia như thế nào.

## Slide 13 — Minh họa một báo cáo hỗ trợ chuyên gia

**11:00–12:30.** Mục tiêu: kết nối các thành phần bằng một tình huống cụ thể, dễ nhớ.

*Nhìn người nghe trước, rồi mới chỉ biểu đồ. Nói rõ tính giả định ngay đầu.*

> Bây giờ em quay lại tệp M-001 ở đầu bài, với điểm tĩnh **0,55**. Toàn bộ điểm và đóng góp SHAP trong ví dụ này đều là giả định để giải thích cơ chế.
>
> Ở biểu đồ bên trái, điểm tĩnh giữ nguyên. Điểm động thay đổi khi có thêm quan sát, và điểm dung hợp được cập nhật theo quy tắc đã trình bày. Tại mốc giả định ba mươi giây, điểm dung hợp vượt ngưỡng minh họa 0,65.
>
> Điều chuyên gia nhận được còn có phần bên phải. Hai nhóm đặc trưng đang đóng góp theo hướng tăng điểm malware, trong khi nhóm header đóng góp theo hướng ngược lại. Các giá trị SHAP ở đây là đóng góp trên thang log-odds, không phải phần trăm rủi ro.

*Dừng khoảng 2 giây, chỉ vào các dấu cộng và trừ.*

> Phần báo cáo giúp chuyên gia xác định nơi cần xem lại và đối chiếu với report hành vi. Nếu đưa vào quy trình cập nhật, mẫu có thể được chuyển đến hàng đợi duyệt nhãn để chuyên gia xem xét.
>
> **Từ một điểm 0,55, quy trình đã bổ sung diễn biến bằng chứng và lý do để người phân tích kiểm tra.** Ví dụ chỉ minh họa cách tính và cách trình bày, chưa xác nhận thời gian phát hiện hoặc hiệu quả thực tế của PID.

*Chuyển slide.*

## Slide 14 — Tiến độ và điều kiện hoàn thiện luận văn

**12:30–13:35.** Mục tiêu: để Thầy thấy rõ sản phẩm hiện có và công việc tiếp theo.

> Với tiến độ hiện tại, em đã có phần kiểm chứng static cho AL và Fidelity, cùng pipeline lưu kết quả và replay.
>
> Để hoàn thiện phần tĩnh–động, em chia công việc thành các đầu ra có điều kiện hoàn tất.
>
> Mốc thứ nhất là dữ liệu ghép cặp: feature tĩnh và report động phải thuộc đúng mẫu, có thời gian quan sát và định danh kiểm tra được.
>
> Mốc thứ hai là scorer động và đối chứng dung hợp. Cấu hình được chọn trên validation, khóa trước test và kết quả phải kiểm tra lại được.
>
> Mốc thứ ba là đồng bộ bản thảo và slide, để kiến trúc, bảng biểu và kết luận cùng dựa trên một nguồn bằng chứng.
>
> Nếu dữ liệu động chưa đáp ứng trước hạn, phương án em đề xuất là **giữ PID ở mức thiết kế và minh họa**, đồng thời chốt đầy đủ hai phần đã được kiểm chứng. Em mong Thầy góp ý mức ưu tiên phù hợp cho giai đoạn tiếp theo.

*Chuyển slide kết luận.*

## Slide 15 — Kết luận và nội dung xin góp ý

**13:35–14:30.** Mục tiêu: khép lại câu chuyện và mở đúng nội dung cần trao đổi.

*Ngừng di con trỏ. Nhìn Thầy, nói chậm hơn ở đoạn cuối.*

> Em xin kết lại bằng tình huống ban đầu. Khi mô hình đưa ra một điểm rủi ro chưa rõ, hệ thống cần hỗ trợ xác định bằng chứng nào còn thiếu, dự đoán đang dựa vào điều gì và mẫu nào nên được ưu tiên xem xét.
>
> Luận văn của em tiếp cận những việc đó bằng kiến trúc đa tầng, Active Learning sử dụng thông tin XAI và quy trình kiểm tra giải thích. Phần AL và Fidelity đã có kết quả static; PID có thiết kế và cần tiếp tục kiểm chứng trên dữ liệu động ghép cặp.
>
> Sau buổi báo cáo, em mong Thầy chốt giúp hai điểm: **phạm vi kết luận của luận văn với bằng chứng hiện có**, và **mức hoàn thiện cần thiết cho PID trước bảo vệ**.
>
> Em xin trân trọng cảm ơn Thầy. Em sẵn sàng trao đổi thêm về những phần Thầy quan tâm.

*Dừng nói, giữ slide 15 để trao đổi. Không mở thêm nội dung cho đầy thời gian.*

---

## Luyện để bài nói hấp dẫn hơn

### Những chỗ nên tạo nhịp

- **Mở bài:** dừng sau câu hỏi về điểm 0,55. Đừng giải thích toàn bộ hệ thống ngay tại bìa.
- **Slide 6:** dẫn con trỏ theo một nhánh tại một thời điểm. Nói xong luồng quyết định mới chỉ vòng cập nhật.
- **Slide 8:** nói rõ động cơ dùng lịch sử bất đồng, giữ công thức chi tiết để trao đổi khi được hỏi.
- **Slide 12:** thay đổi nhịp khi chuyển từ kết quả thuận lợi sang đánh đổi với Uncertainty. Điều này cho thấy bạn hiểu và đánh giá kết quả của mình.
- **Slide 13:** quay lại đúng mẫu đã giới thiệu ở mở bài, dừng ở các đóng góp trái chiều. Đây là đoạn minh họa trọng tâm.
- **Kết bài:** nhìn người nghe, nhấn hai nội dung xin góp ý và kết thúc dứt khoát.

### Khi sắp hết giờ

Nếu luyện tập cho thấy bạn nói chậm hơn kế hoạch, ưu tiên giữ mở bài, kiến trúc và ví dụ M-001. Rút các phần sau:

| Phần | Cách rút |
|---|---|
| Slide 4 | Chỉ nói một câu cho mỗi phần đề xuất, không đọc cột đối chứng. |
| Slide 5 | Gói lại thành: feature biểu diễn tệp, LightGBM cho điểm, TreeSHAP cho đóng góp. |
| Slide 11 | Chỉ giữ quy mô hai nghìn mẫu và nguyên tắc validation/test. |
| Slide 12 | Giữ hai thông điệp: đánh đổi giữa chiến lược AL và top-SHAP ảnh hưởng mạnh hơn random mask. |

**Mốc tự kiểm:** đến slide 6 khoảng phút 4, đến slide 12 trước phút 10 và bắt đầu kết luận khoảng phút 13 phút 35 giây. Nếu trễ hơn, rút câu ở các phần phía trên, tránh tăng tốc đọc toàn bộ bài.

### Nếu Thầy hỏi giữa bài

Trả lời thẳng câu hỏi trước. Nếu phần trao đổi kéo dài, cập nhật thời gian còn lại và rút một đoạn giải thích phía sau; không cố đọc đủ mọi câu trong script.

Nếu cần quay lại mạch trình bày, có thể nói:

> Dạ, em xin giữ điểm Thầy vừa góp ý để điều chỉnh phần này. Em tiếp tục sang phần kế tiếp để làm rõ mối liên hệ với kết quả và hướng hoàn thiện.

Chỉ dùng câu này sau khi đã trả lời hoặc ghi nhận cụ thể câu hỏi, không dùng để né nội dung cần giải thích.

## Thẻ nhắc nhanh trước khi trình bày

1. Tình huống M-001 là giả định, điểm tĩnh 0,55.
2. Cổng chuyển tuyến chọn mẫu cần thêm quan sát; PID dung hợp khi đủ hai điểm.
3. AL cần nhãn do chuyên gia cung cấp; mô phỏng offline dùng nhãn sẵn có theo ngân sách.
4. Đọc SHAP như đóng góp của model, không đổi thành xác suất hoặc khẳng định nguyên nhân hành vi.
5. Kết quả AL/Fidelity đã đo và ví dụ giả định là hai phần riêng.
6. Hai câu hỏi cuối buổi: phạm vi kết luận và mức hoàn thiện PID.

Nguồn nội dung: tệp LaTeX hiện tại và gói `results/confirmatory_20261019_ember_identity/`. Kịch bản giữ đúng phạm vi nhãn malware tĩnh, không mở rộng thành bằng chứng ransomware-specific hoặc hiệu quả PID thực tế.
