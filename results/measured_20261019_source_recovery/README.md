# Khôi phục source index của tập mini

Gói này là đầu ra `recover-manifest` chạy trên archive SOREL có 4.195.042 dòng.
Checksum của ba artifact gốc đều khớp. Kiểm tra độc lập trong
`independent_verification.json` xác nhận:

- 2.000 `row_id` liên tục và 2.000 `source_index` duy nhất, nằm trong archive;
- phân bố nhãn đúng 1.500 nhãn 0 và 500 nhãn 1;
- nhãn và 2.000 feature hash khớp CSV trong repository;
- SHA-256 khác nhau của CSV Windows và CSV trong Git được giải thích hoàn toàn
  bởi CRLF so với LF; dữ liệu sau khi parse giống nhau;
- phép so nguồn–CSV báo 2.000/2.000 hàng đạt `rtol=1e-6`, `atol=1e-8`.

Giới hạn còn lại:

- archive 39 GB chưa được hash;
- sai số tuyệt đối lớn nhất được báo là 120, do đó đây là đối sánh số theo dung
  sai chứ chưa phải đối sánh byte của ma trận nguồn;
- manifest chưa có SHA-256 PE hoặc tag SOREL; nhãn 1 vẫn là malware tổng quát.

Bước tiếp theo dùng `recover-sorel-metadata` với `meta.db` và
`shas_missing_ember_features.json` của đúng bản SOREL. Công cụ chỉ xuất SHA/tag
khi toàn bộ số dòng sau lọc và cả 2.000 nhãn tại source index đều khớp.
