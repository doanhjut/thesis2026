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

## Đánh giá học thuật

Nguồn này chưa đủ cho PID vì không có behavior trace theo thời gian. CSV vẫn có thể hữu ích cho dữ liệu tĩnh hoặc mapping nếu header chứa SHA-256 và metadata. Bước tiếp theo là kiểm tra header và một số dòng đầu bằng `scripts/inspect_zip_csv.py`:

```powershell
python scripts\inspect_zip_csv.py `
  --archive "D:\Code\Luanvan\data\archives\train_small.zip" `
  --output "D:\Code\Luanvan\outputs\pid_intake\train_small_schema.json" `
  --sample-rows 20
```

Script không ghi CSV 14 GB ra đĩa. Sau bước này:

- nếu có SHA-256: tìm binary hoặc report sandbox khớp SHA-256;
- nếu không có SHA-256: CSV không thể tự cung cấp mapping tĩnh--động đáng tin cậy;
- dù có SHA-256, vẫn cần binary được phép phân tích hoặc report động đã tồn tại.
