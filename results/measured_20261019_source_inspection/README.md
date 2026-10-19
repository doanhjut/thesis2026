# Kiểm tra nguồn archive cho `real_mini_dataset.csv`

Thư mục này lưu kết quả `inspect-source` do chủ sở hữu dữ liệu chạy trên
`D:\Code\Luanvan\data\archives\test-features.npz`. Checksum trong
`artifact_sha256.json` khớp với `source_inspection.json`.

Kết quả quan sát được:

- ma trận đặc trưng `arr_0.npy`: 4.195.042 dòng, 2.381 đặc trưng `float32`;
- vector nhãn `arr_1.npy`: 4.195.042 nhãn `int64`;
- nhãn 0: 2.834.428; nhãn 1: 1.360.614;
- số chiều và phân vùng này phù hợp với nguồn SOREL-20M được mô tả trong
  repository và đủ để tái tạo phép lấy mẫu 1.500/500 với seed 42;
- SHA-256 của archive 39 GB chưa được tính ở lần kiểm tra này.

`data/ember2018/test_features.jsonl` không được ghép vào archive trên: đó là
metadata của EMBER 2018, trong khi archive đang kiểm tra thuộc pipeline SOREL.
Trùng số chiều EMBER-v2 không chứng minh hai nguồn có cùng thứ tự mẫu.

Bước tiếp theo là chạy `recover-manifest` **không có** `--metadata-jsonl` để
tái tạo source index và so khớp đủ 2.381 đặc trưng cùng nhãn với CSV mini.
Sau khi phép kiểm tra này đạt, cần metadata SOREL cùng thứ tự dòng để bổ sung
SHA-256 của PE. Nhãn 1 chỉ được gọi là malware; muốn kết luận ransomware cần
nhãn họ/tag có nguồn và tiêu chí ánh xạ được công bố.
