# Cập nhật phản hồi và bằng chứng cho paper ngày 21 tháng 10 năm 2026

Gói bàn giao cho Lưu Văn Doanh và giảng viên hướng dẫn, đối chiếu bản đánh giá trước với dữ liệu và thực nghiệm đã hoàn thành. Báo cáo chính có bản Word để đọc/chỉnh sửa và bản Markdown để cập nhật bằng Git.

## Đọc theo thứ tự

1. `BAO_CAO_CAP_NHAT_PAPER_20261021.docx` hoặc `.md`: báo cáo đầy đủ, 13 mục.
2. `RESPONSE_MATRIX.csv`: 17 yêu cầu theo đúng thứ tự roadmap gốc, trạng thái mới, nguồn bằng chứng, phần thiếu, bước tiếp và tiêu chí nghiệm thu.
3. `CLAIM_EVIDENCE_MAP.csv`: 13 phát biểu cùng phạm vi và cách dùng trong paper.
4. `NEXT_ACTIONS.csv`: 12 công việc theo dependency, đơn vị thực hiện, output và acceptance criteria.
5. `EVIDENCE_SNAPSHOT.json`: nguồn đầu vào, hash, commit, checkpoint collection và giới hạn xác nhận.
6. `SOURCE_INTEGRITY_CHECKS.json`: đối soát 67 file của hai gói thực nghiệm, tách khớp byte và khớp sau chuẩn hóa LF.

`sources/` chứa bản roadmap, phản hồi trước, phần front matter/kế hoạch/claim map manuscript cũ và trích log collector để đối chiếu lịch sử. Các nội dung đó là tài liệu nguồn; trạng thái cập nhật nằm trong báo cáo và các CSV ở thư mục chính.

## Trạng thái khóa khi lập báo cáo

- EMBER: 2.000 mẫu có identity; AL và Fidelity đã có gói confirmatory theo giao thức dự án.
- PID: pilot 199 mẫu đo thật; không chứng minh D vượt PI hoặc giảm FPR.
- Toàn cohort MalBehavD: checkpoint collector hoàn tất mới nhất được xác nhận là 693/1.923 usable, không phải số live.
- Collection cần đạt ít nhất 1.731 usable, thử hết cohort và không còn deferred trước confirmatory; còn thiếu tối thiểu 1.038 usable tại checkpoint này.
- Lần điều phối Linux cuối kết thúc do giới hạn sử dụng Codex sau khi lô collector hoàn tất; không đồng nghĩa quota VirusTotal hết.
- Không có executable trong gói này; không tải hoặc thực thi PE trong công việc cập nhật báo cáo.

## Phạm vi tiếp tục

Không lấy kết quả EMBER và PID MalBehavD ghép thành một thí nghiệm hệ thống. Tiếp tục M1 collection/audit, M2 fusion/strong baselines, M3 integration và M4 manuscript/release theo báo cáo. Giữ mọi pilot và run đã khóa; output run mới phải dùng tên mới. Tình huống giả định trên slide không phải bằng chứng cho paper.

Báo cáo chưa sửa trực tiếp source manuscript gốc trong Downloads, chưa kiểm chứng lại DOI hoặc hướng dẫn tạp chí hiện hành và chưa chạy lại huấn luyện các gói thực nghiệm cũ. Tên, DOI, template, authorship và data-sharing rights cần được chốt trước submission.
