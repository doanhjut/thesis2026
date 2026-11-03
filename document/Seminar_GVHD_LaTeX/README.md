# Nguồn LaTeX slide trao đổi với GVHD

Tệp chính: `Luan_van_Luu_Van_Doanh_UET_format_pdflatex.tex`.

Đây là bản chỉnh sửa theo nguồn Beamer chuẩn trong `Slide_Baove_Luu_Van_Doanh.zip`, giữ theme Madrid 10pt, màu UET, bìa trắng căn giữa, logo, tên học viên và GVHD. Nội dung gồm **đúng 15 khung, tính cả bìa**, cho buổi trình bày khoảng 15 phút. Không có phụ lục hoặc hiệu ứng xuất hiện từng bước sinh thêm trang.

## Cách sửa và biên dịch

1. Mở tệp `.tex` trong thư mục này. Sửa nội dung trực tiếp tại các `\begin{frame}...\end{frame}`.
2. Giữ thư mục `assets` cạnh tệp chính để hiển thị hai logo gốc.
3. Chọn **pdfLaTeX** làm compiler. Trên Overleaf, tải cả nội dung thư mục này lên, chọn tệp `.tex` làm Main document và compiler pdfLaTeX.
4. Nếu biên dịch cục bộ, chạy hai lần từ thư mục chứa tệp chính:

```powershell
pdflatex -interaction=nonstopmode -halt-on-error Luan_van_Luu_Van_Doanh_UET_format_pdflatex.tex
pdflatex -interaction=nonstopmode -halt-on-error Luan_van_Luu_Van_Doanh_UET_format_pdflatex.tex
```

Nguồn dùng các gói Beamer, hỗ trợ tiếng Việt T5/babel, Latin Modern, TikZ và PGFPlots. Không cần shell-escape hoặc chương trình ngoài để vẽ sơ đồ/biểu đồ.

## Cấu trúc 15 trang và lời dẫn

1. Bìa báo cáo.
2. Tổng quan nội dung.
3. Bài toán và mục tiêu nghiên cứu.
4. Nền tảng kế thừa và phần đề xuất của luận văn.
5. Nền tảng tĩnh: LightGBM và TreeSHAP.
6. Kiến trúc phát hiện, cập nhật và kiểm chứng.
7. Từ sự kiện quan sát đến điểm động.
8. Vì sao khảo sát PID thay cho trọng số cố định?.
9. XAI-Guided Active Learning.
10. Kiểm chứng giải thích TreeSHAP.
11. Thiết kế đánh giá và phạm vi dữ liệu.
12. Kết quả chính: Active Learning và Fidelity.
13. Minh họa một báo cáo hỗ trợ chuyên gia.
14. Tiến độ và điều kiện hoàn thiện luận văn.
15. Kết luận và nội dung xin góp ý.

- Lời dẫn nằm trong `\note{...}` của mỗi slide và mặc định ẩn. Muốn hiện trang ghi chú, đổi `\setbeameroption{hide notes}` thành `\setbeameroption{show notes}`. Muốn dùng chế độ hai màn hình, dùng `\setbeameroption{show notes on second screen=right}`.
- Để giữ đúng giới hạn 15 trang, giữ `hide notes` và không thêm frame, overlay hoặc `allowframebreaks`.

## Các thay đổi nội dung

- Giữ một bìa báo cáo tiến độ, hướng lời trình bày đến GVHD.
- Gộp 32 khung trong nguồn chuẩn thành 15 khung, bỏ bìa trùng và backup slide.
- Phân biệt nền tảng kế thừa và phần đề xuất/triển khai, bổ sung ba tham chiếu nền tảng trực tiếp trong nguồn.
- Rút phần lý thuyết và số liệu, giữ mỗi phần một thông điệp chính. Slide PID trình bày trực giác so với trọng số cố định, công thức chi tiết chuyển vào lời dẫn.
- Sửa sơ đồ: cổng chuyển tuyến đưa mẫu chưa rõ sang quan sát động, PID chỉ dung hợp khi có cả hai điểm của đúng mẫu. Vòng ngoài thể hiện chọn mẫu AL, chuyên gia gán nhãn, huấn luyện lại và Fidelity theo phiên bản model.
- Sơ đồ ở slide 6 dùng TikZ; biểu đồ slide 13 dùng PGFPlots. Tất cả có thể sửa trong nguồn, không phải ảnh chụp slide PowerPoint.
- Nêu cách hình thành feature động và scorer đề xuất. Các thành phần này còn cần dữ liệu động để huấn luyện và xác nhận.
- Ghi rõ mức bằng chứng của từng đóng góp. Bỏ AUC/latency PID, dữ liệu 20.000 ransomware và điểm OFS chưa có nguồn kiểm chứng tương ứng.
- Số liệu giả định chỉ nằm ở tình huống minh họa slide 13. Các bảng số liệu thật ở slide 12 lấy từ gói kết quả EMBER đã xác minh.

## Ví dụ PID giả định

Đầu vào minh họa: điểm tĩnh 0,55; điểm động 0,20 / 0,40 / 0,75 / 0,90 tại 5 / 15 / 30 / 60 giây. Dùng Kp=0,85, Ki=0,02, Kd=0,35, integral clipping [-5,5], đạo hàm đầu tiên bằng 0 và ngưỡng minh họa 0,65. Điểm dung hợp đã được đối chiếu với `src/pid_fusion.py` và làm tròn 6 chữ số cho biểu đồ. Khi đổi đầu vào hoặc gain, cần tính lại các tọa độ dung hợp.

Ví dụ không có PE, sandbox report hoặc nhãn thật. Không dùng ví dụ để suy ra AUC, FPR, cải thiện PID hoặc thời gian phát hiện thực tế.

## Báo cáo XAI giả định của M-001

Ba đóng góp theo nhóm ở slide 13 là giả định: Import/API +0,55, Section/entropy +0,35 và Header -0,40, theo đơn vị log-odds. Cộng bias giả định -0,2993293 được raw score khoảng 0,2006707, tương ứng sigmoid khoảng 0,55. Tên nhóm chỉ minh họa, không gán một feature index cụ thể của model EMBER. Không suy ra thứ hạng AL cao nhất nếu chưa có pool và bước chuẩn hóa.

## Tham chiếu nền tảng

- Anderson & Roth (2018), [EMBER: An Open Dataset for Training Static PE Malware Machine Learning Models](https://arxiv.org/abs/1804.04637).
- Lundberg et al. (2020), [From local explanations to global understanding with explainable AI for trees](https://doi.org/10.1038/s42256-019-0138-9).
- Settles (2009), [Active Learning Literature Survey](https://research.cs.wisc.edu/techreports/2009/TR1648.pdf).

Các tài liệu này làm rõ nền tảng kế thừa, không phải bằng chứng rằng toàn bộ khung tích hợp là đầu tiên trong nghiên cứu.

## Nguồn số liệu thật

- `results/confirmatory_20261019_ember_identity/README.md`
- `results/confirmatory_20261019_ember_identity/al/aulc_summary.csv`
- `results/confirmatory_20261019_ember_identity/al/target_reach_summary.csv`
- `results/confirmatory_20261019_ember_identity/fidelity/deletion_summary.csv`
- Công thức: `src/pid_fusion.py`, `src/experiments/temporal_fusion.py`, `src/experiments/signals.py`.

Nhãn EMBER là benign/malware chung. Mục tiêu ứng dụng ransomware cần được phân biệt với phạm vi đã đo. Không đưa PE binary vào gói nguồn này.
