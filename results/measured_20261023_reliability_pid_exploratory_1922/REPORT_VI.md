# Báo cáo exploratory: PID hướng theo độ tin cậy trên 1.922 mẫu

> Phương pháp này được thiết kế sau khi xem run confirmatory trước đó. Kết quả là bằng chứng exploratory, không phải xác nhận độc lập. Muốn tuyên bố vượt trội trong paper cần một cohort external/temporal mới.

## Thiết kế đã thực hiện

- Giữ nguyên 5 outer folds và cohort 1.922 mẫu có metadata tĩnh ghép đúng SHA-256.
- Mở rộng chuỗi từ 4 mốc lên 20 tiền tố API liên tiếp, từ 1 đến 20 sự kiện.
- Hiệu chỉnh static và dynamic riêng trong từng outer fold; dynamic được hiệu chỉnh theo từng mốc sự kiện.
- Học xác suất đúng của mỗi kênh chỉ trên partition calibration.
- Dùng trọng số Fixed đã chọn trên validation làm `w0`; PID theo dõi trọng số mục tiêu sinh từ chênh lệch độ tin cậy.
- Cho phép `Ki=0` và `Kd=0`; báo riêng PID family và full PID bắt buộc `Kd>0`.
- Chọn cấu hình bằng FPR thấp nhất tại threshold đạt TPR validation 95%, sau đó dùng event-AUC, final AUC và Brier để phá hòa.
- Outer-test label không tham gia calibration, chọn gain, chọn threshold hoặc cập nhật controller.

## Kết quả chính

| Phương pháp | AUC | FPR | TPR | Event-AUC | Brier |
|---|---:|---:|---:|---:|---:|
| Static | 0,9702 | 23,58% | 96,56% | 0,9702 | 0,0567 |
| Dynamic | 0,9720 | 20,38% | 95,45% | 0,9453 | 0,0589 |
| Average | **0,9837** | 14,69% | **96,77%** | **0,9799** | **0,0450** |
| Fixed | 0,9822 | 12,44% | 96,06% | 0,9736 | 0,0487 |
| Reliability-P | 0,9826 | **11,15%** | 95,96% | 0,9787 | 0,0456 |
| Reliability-PI | 0,9825 | 11,47% | 95,96% | 0,9786 | 0,0456 |
| Reliability-PID family | 0,9825 | 11,47% | 95,96% | 0,9785 | 0,0455 |
| Full reliability-PID (`Kd>0`) | 0,9825 | 11,58% | 95,96% | 0,9785 | 0,0455 |

## Hiệu ứng ghép cặp quan trọng

### Reliability-P so với Fixed

- ΔFPR = **-1,33 điểm phần trăm**, bootstrap CI 95% `[-2,45; -0,21]`.
- ΔBrier = **-0,00308**, CI 95% `[-0,00560; -0,00071]`.
- ΔAUC = `+0,00060`, CI đi qua 0.
- ΔTPR = `-0,11 điểm phần trăm`, CI đi qua 0.

Kết quả hỗ trợ lợi ích của trọng số thích nghi hướng theo độ tin cậy, nhưng thành phần tạo kết quả tốt nhất là P.

### Reliability-PID family so với Average

- ΔFPR = `-3,27 điểm phần trăm`, CI 95% `[-4,67; -1,93]`.
- ΔTPR = `-0,81 điểm phần trăm`, CI 95% `[-1,51; -0,20]`.
- ΔAP = `-0,00129`, CI hoàn toàn âm.
- ΔAUC có CI đi qua 0.

PID giảm FPR ở operating point đã chọn nhưng đồng thời giảm TPR/AP. Vì vậy không thể gọi đây là vượt trội toàn diện.

### Full PID so với PI và P

- Full PID trừ PI: ΔAUC `+0,00007`, CI đi qua 0; ΔFPR `+0,11 điểm phần trăm`, CI `[0; +0,33]`; TPR không đổi.
- PID family trừ P: ΔAUC `+0,00008`, CI đi qua 0; ΔFPR `+0,32 điểm phần trăm`, CI đi qua 0; TPR không đổi.
- Một trong năm folds của PID family tự chọn `Kd=0`.

Không có bằng chứng rằng D tạo lợi ích. Việc bắt buộc `Kd>0` còn làm FPR xấu nhẹ so với PI.

## Chẩn đoán dữ liệu

Kênh tốt hơn thay đổi theo chuỗi ở 1.119/1.922 mẫu (58,2%). Static tốt hơn ở 87,8% mẫu tại sự kiện đầu; dynamic tăng dần và tốt hơn ở 54,7% mẫu tại sự kiện 20. Điều này xác nhận dữ liệu có chuyển dịch độ tin cậy theo thời gian và giải thích vì sao reliability-aware P có thể tốt hơn Fixed.

Tuy nhiên, median detection event của tất cả phương pháp là 1 vì static đã mạnh và threshold cuối chuỗi được áp dụng từ mốc đầu. Chỉ số detection delay hiện không phân biệt được các luật. Cần cohort có hành vi xuất hiện muộn hơn hoặc protocol gate chỉ kích hoạt dynamic cho mẫu bất định để đánh giá lợi ích phát hiện sớm.

## Kết luận được phép sử dụng

1. Dung hợp hướng theo độ tin cậy đã cải thiện FPR và Brier so với Fixed trong run exploratory.
2. Cấu hình Reliability-P đạt kết quả vận hành tốt nhất; I và D không tạo lợi ích tăng thêm.
3. Average vẫn tốt hơn về AUC/AP/event-AUC và có TPR cao hơn.
4. Full PID chưa được chứng minh vượt P, PI hoặc Average.
5. Nếu giữ đóng góp trong luận văn, nên gọi là **reliability-aware adaptive fusion with PID component ablation**; chưa nên tuyên bố full PID vượt trội.
