# Static gate và audit PID — 19/10/2026

Run dùng commit `d831933` và dự đoán AL đã kiểm chứng của gói `measured_20261014`. Validation 400 dòng được chia cố định thành 200 dòng fit Platt calibration và 200 dòng chọn hai gate threshold. Test 400 dòng không tham gia calibration hoặc chọn threshold.

Ràng buộc trên gate-selection validation là early-FNR ≤ 2% tổng positive và early-FPR ≤ 2% tổng negative. Kết quả test là out-of-sample đối với calibration/gate selection:

| Phương pháp | Chuyển dynamic | Early FN / tổng positive | Early FP / tổng negative |
|---|---:|---:|---:|
| Random | 24.35% ± 8.14% | 2.60% ± 2.07% | 4.53% ± 1.61% |
| Uncertainty | 24.05% ± 9.28% | 2.80% ± 1.48% | 3.47% ± 1.52% |
| XAI_full | 29.40% ± 5.64% | 0.40% ± 0.55% | 3.20% ± 0.56% |

Platt calibration giảm Brier test trung bình của `XAI_full` từ `0.059314` xuống `0.050193` và ECE từ `0.079884` xuống `0.026712`.

Đây là bằng chứng cho **static gate**, chưa phải chất lượng hệ thống hoàn chỉnh. Khoảng 29.4% routed rows của XAI_full chưa có final decision vì chưa có dynamic observation thật. Không diễn giải con số này thành mức tiết kiệm latency hoặc tài nguyên end-to-end.

`static_gate/verification.json` xác nhận replay 25 cặp model–gate và 15.000 decision rows. `pid_input_audit/` ghi bốn blocker dữ liệu hiện tại. `temporal_template/` cung cấp 3.200 dòng kế hoạch cho 800 mẫu × bốn cửa sổ 5/15/30/60 giây; mọi trường quan sát vẫn trống và không phải kết quả thực nghiệm.
