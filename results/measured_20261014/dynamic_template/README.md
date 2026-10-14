# Thu thập tín hiệu động

Đây là mẫu trống; không có điểm động được sinh tự động. `row_id` là dòng 0-based trong CSV có hash ghi trong provenance.json, không phải hash tệp PE. Chỉ thu thập khi ghép được dòng đó với đúng tệp/phiên quan sát. Không suy ra p_dynamic từ label hoặc thêm nhiễu vào p_static.

Điền p_dynamic từ quy tắc/model cố định trước test; mô tả thang điểm (xác suất đã hiệu chuẩn hay risk score), nguồn model và dữ liệu huấn luyện. sequence_id/sequence_order phải có nghĩa thực tế; đặt một ID riêng cho mỗi mẫu độc lập. Các phiên validation/test phải độc lập. Giữ cửa sổ/chính sách quan sát chung.

Lưu báo cáo quan sát trong reports/ bên cạnh CSV; report_path là đường dẫn tương đối tới tệp và report_sha256 là SHA-256 nội dung. Mỗi hàng cần báo cáo riêng. Điền provenance.json, gồm hash CSV sau khi hoàn tất và xác nhận phép tính điểm không đọc nhãn đích. Runner kiểm tra đầy đủ ID, split, hash và schema; metadata tự khai không tự chứng minh dữ liệu là quan sát thực.
