# PID input intake — `train_small.zip`

Đánh giá từ bộ kiểm kê do tác giả tạo ngày 20/10/2026, tại commit nguồn `2af3015f840a57741a00f2bf96aae3a035e77b7d`.

## Kết quả

- Archive: `D:\Code\Luanvan\data\archives\train_small.zip`.
- Kích thước ZIP: 2.821.784.137 byte.
- SHA-256: `7aa786b5523bf9c5386b231962a60ea322cd00b8a10f32019ad36d105e20c37e`.
- ZIP không thay đổi trong quá trình đọc.
- Có đúng một member: `train_small.csv`.
- Kích thước member sau giải nén: 14.414.686.875 byte.
- Không có PE binary hoặc sandbox report được liệt kê riêng.
- Kiểm kê chỉ đọc central directory và hash archive; không giải nén member, không chạy PE.

## Kết quả kiểm tra schema

`train_small_schema.json` được tạo bằng cách đọc header và 20 dòng đầu trực tiếp trong ZIP:

- 2.382 cột: `0` đến `2380` và `label`;
- 2.381 chiều đặc trưng số theo cấu trúc EMBER;
- không có SHA-256, `row_id`, sample ID, family, timestamp, source hoặc split;
- 20/20 dòng mẫu có đúng 2.382 trường;
- nhãn mẫu nhận giá trị 0/1;
- SHA-256 của báo cáo schema: `9e7ab9c8efb64ba1178d7d56edfd9c688d2c1ef0c8ed8a90aed451fafb74a3e9`.

## Đánh giá học thuật

Nguồn này có thể dùng để huấn luyện mô hình tĩnh quy mô lớn, nhưng không thể dùng để khôi phục mapping tĩnh--động: CSV không chứa định danh mẫu và archive không chứa PE/report. Thứ tự hàng đơn thuần không phải bằng chứng để gán SHA-256 từ một nguồn khác.

Lệnh đã dùng để kiểm tra:

```powershell
python scripts\inspect_zip_csv.py `
  --archive "D:\Code\Luanvan\data\archives\train_small.zip" `
  --output "D:\Code\Luanvan\outputs\pid_intake\train_small_schema.json" `
  --sample-rows 20
```

Script không ghi CSV 14 GB ra đĩa. Kết luận cuối cho nguồn này là `static_only_without_identity`. Để chạy PID cần một corpus khác có binary hoặc report động và manifest SHA-256, hoặc metadata gốc chứng minh được mapping tới chính các hàng trong CSV. Không tiếp tục suy đoán mapping từ `train_small.csv`.
