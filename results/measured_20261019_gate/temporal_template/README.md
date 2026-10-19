# Mẫu quan sát động theo thời gian

Mỗi `row_id` có nhiều time step trong cùng một `execution_id`; trạng thái PID phải reset khi đổi execution. Các execution ID được điền sẵn chỉ là kế hoạch đặt tên. Thay chúng nếu hệ thống sandbox cung cấp ID thật.

`p_dynamic` phải do một scorer đóng băng tạo từ hành vi quan sát đến `elapsed_seconds`, không đọc target label. `evidence_status` dùng một trong: `observed`, `no_behavior`, `sandbox_failure`, `missing`. Với `observed` hoặc `no_behavior`, điền score và báo cáo/hash. Với failure/missing, lưu failure report nếu có và để score trống; policy xử lý missing phải được khai báo trước test.

Báo cáo có thể dùng chung cho nhiều time step của cùng execution nếu score được tái tạo bằng cách cắt event theo timestamp. Không dùng cùng report cho hai PE khác nhau. `row_mapping.csv` chỉ hỗ trợ ghép dữ liệu; không đưa label vào scorer.
