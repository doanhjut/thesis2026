# Kịch bản demo ba đóng góp của luận văn

## 1. Mục tiêu và nguyên tắc

Demo được thiết kế cho tình huống hội đồng yêu cầu xem cơ chế và bằng chứng trực tiếp. Đây là **artifact replay offline**:

- không tải lên, tải xuống hoặc thực thi tệp PE;
- không gọi VirusTotal, sandbox hoặc dịch vụ mạng;
- không huấn luyện lại mô hình tại phòng bảo vệ;
- không sinh số liệu ngẫu nhiên hoặc thay thế số liệu đã đo;
- mọi bảng và vết mẫu đều được rút từ artifact thực nghiệm, kèm SHA-256 nguồn.

Dashboard gồm sáu màn hình: tổng quan, ba đóng góp, kịch bản trình bày và nguồn/hash. Ba đóng góp dùng cùng màu với slide: đỏ cho dung hợp, cam cho Active Learning và xanh cho Fidelity.

## 2. Các tệp được bổ sung

| Tệp | Vai trò |
|---|---|
| `dashboard/defense_contributions_demo.py` | Dashboard Streamlit |
| `src/defense_demo.py` | Tạo, đọc và xác minh bundle đo lường |
| `scripts/build_defense_demo_bundle.py` | Tái tạo bundle từ artifact gốc |
| `scripts/run_defense_demo.py` | Kiểm tra hoặc khởi động demo |
| `results/defense_demo_bundle/demo_bundle.json` | Bundle nhỏ dùng khi demo offline |

Các script nguyên mẫu cũ `scripts/defense_demo.py` và `scripts/live_defense_demo.py` không được dùng vì có đường sinh tín hiệu mô phỏng.

## 3. Chuẩn bị một lần

Từ thư mục gốc repository:

### Linux/macOS

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/run_defense_demo.py --check
```

### Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts\run_defense_demo.py --check
```

Kết quả đúng phải có `"ok": true`, `source_count: 9` và `pid_scenarios: 4`. Lệnh kiểm tra đối chiếu hash của bundle với chín artifact nguồn, nên nên chạy sau khi clone/pull hoặc trước buổi bảo vệ.

Nếu artifact nguồn được chạy lại có chủ đích, tạo lại bundle rồi kiểm tra:

```bash
python scripts/run_defense_demo.py --rebuild --check
```

Không dùng `--rebuild` ngay trước khi trình bày nếu chưa kiểm tra số liệu mới với slide và luận văn.

## 4. Khởi động demo

```bash
python scripts/run_defense_demo.py
```

Mở `http://127.0.0.1:8501`. Để dùng cổng khác:

```bash
python scripts/run_defense_demo.py --port 8510
```

Trên máy trình chiếu, nên khởi động demo trước khi vào phòng, mở toàn màn hình trình duyệt và giữ cửa sổ terminal ở phía sau. Nhấn `Ctrl+C` để dừng.

## 5. Kịch bản chính trong 4–5 phút

### 0:00–0:20 — Xác lập tính hợp lệ

Mở **Tổng quan** và nói:

> Em không chạy lại mô hình và không đưa mã độc vào máy trình chiếu. Demo này phát lại các artifact đã đo, có hash và cùng nguồn với số liệu trong luận văn. Ba màn hình tiếp theo tương ứng với ra quyết định, cập nhật mô hình và kiểm chứng căn cứ của quyết định.

Không đi sâu vào kiến trúc tại màn hình này; kiến trúc đã có trên slide.

### 0:20–1:50 — Đóng góp 1: dung hợp thích nghi

1. Chọn **1 · Dung hợp thích nghi**.
2. Chỉ biểu đồ FPR và đọc ba số: Fixed `12,45%`, Adaptive P `11,16%`, Full PID `11,59%`.
3. Nói:

> Trên 1.922 mẫu và năm outer folds, Adaptive P giảm 1,28 điểm phần trăm FPR so với trọng số cố định; bootstrap ghép cặp cho hiệu ứng này có khoảng tin cậy không đi qua 0. Brier cũng giảm, còn TPR không phát hiện khác biệt.

4. Giữ tình huống mặc định **“Giảm một báo động nhầm do kênh động xung đột”**. Chỉ lần lượt điểm tĩnh, điểm động và đường Adaptive P.
5. Chỉ biểu đồ trọng số và nói:

> Điểm khác của luật đề xuất nằm ở đây: trọng số kênh tĩnh không cố định cho mọi mẫu mà được cập nhật theo lịch sử bất đồng giữa hai kênh.

6. Chốt giới hạn:

> Ablation cho thấy thành phần P tạo phần cải thiện rõ nhất; I và D chưa tạo lợi ích bổ sung ổn định trong horizon hiện tại. Vì vậy em phát biểu đóng góp là dung hợp thích nghi có trạng thái và phép ablation P/PI/PID, không nói full PID thắng mọi chỉ số.

Nếu cần thêm một tình huống dương, chọn **“Khôi phục một mẫu malware bị luật cố định bỏ sót”**. Nếu hội đồng hỏi điểm yếu, chọn **“Phản ví dụ…”** để chỉ ra mẫu mà họ PID thất bại.

### 1:50–3:00 — Đóng góp 2: XAI-Guided Active Learning

1. Chọn **2 · XAI-Guided AL**.
2. Giữ bốn đường `Random`, `Uncertainty`, `U+H`, `XAI_full`.
3. Chỉ trục hoành là số mẫu đã gán nhãn và nói:

> Các phương pháp dùng cùng tập khởi tạo, ngân sách và outer-test. Khác biệt nằm ở thứ tự mẫu được hỏi. XAI-full đạt mục tiêu với trung bình 492 nhãn, trong khi Random cần 584, tức giảm 92 nhãn hay 15,8 phần trăm.

4. Chỉ bảng và nói:

> U cộng H có ROC-AULC và AP-AULC cao nhất; U cộng V cần ít nhãn nhất. Vì vậy cấu hình đầy đủ không đứng đầu mọi tiêu chí. Lợi ích so với Uncertainty nhỏ hơn so với Random và query overhead của XAI-full là khoảng 5,42 phần trăm thời gian train cộng query.

5. Chốt:

> Đóng góp ở đây không phải phát minh Active Learning hay SHAP, mà là acquisition function kết hợp bất định đầu ra với xung đột và phân tán của giải thích, kèm ablation từng tín hiệu.

### 3:00–4:00 — Đóng góp 3: kiểm chứng Fidelity

1. Chọn **3 · Fidelity**, giữ baseline `mean`.
2. Chỉ cặp cột tại `k=50` và nói:

> Nếu thứ hạng SHAP không mang thông tin, che top-k và che ngẫu nhiên cùng k phải gây tác động gần nhau. Thực tế, che top-50 làm AUC giảm 0,3067, còn che ngẫu nhiên chỉ giảm 0,0010.

3. Chỉ biểu đồ stability:

> Spearman của global importance là 0,614 trong cùng fold và 0,551 giữa các fold. Như vậy giải thích có độ ổn định trung bình, và thay đổi phân hoạch dữ liệu ảnh hưởng nhiều hơn thay đổi seed.

4. Chốt giới hạn:

> Kết quả hỗ trợ model fidelity của TreeSHAP. Nó không chứng minh quan hệ nhân quả và cũng không khẳng định vector sau masking tương ứng với một PE thực thi hợp lệ.

### 4:00–4:30 — Tổng kết

> Ba màn hình tạo thành một chuỗi bằng chứng: dung hợp thích nghi cải thiện operating point, XAI-Guided AL giảm ngân sách nhãn, và Fidelity cung cấp đối chứng định lượng cho lời giải thích. Đây là bằng chứng theo từng thành phần trên hai benchmark malware Windows, chưa phải đánh giá end-to-end dành riêng cho ransomware trong môi trường sản xuất.

## 6. Phiên bản rút gọn 90 giây

Nếu chủ tọa chỉ cho demo nhanh:

1. Đóng góp 1: chỉ biểu đồ FPR, đọc `11,16%` so với `12,45%`.
2. Đóng góp 2: chỉ ba thẻ `92 nhãn`, `−15,8%`, `5,42% overhead`.
3. Đóng góp 3: chỉ cặp cột top-50 `0,3067` và random `0,0010`.
4. Kết thúc bằng câu giới hạn component-wise.

Không mở vết mẫu trong phiên bản 90 giây.

## 7. Câu hỏi dự kiến khi demo

### “Đây có phải kết quả chạy trực tiếp không?”

> Đây là phát lại artifact đo trước, không phải chạy lại thí nghiệm. Chạy lại toàn bộ AL/Fidelity mất thời gian và có rủi ro kỹ thuật không cần thiết tại buổi bảo vệ. Trang Nguồn và hash cho phép đối chiếu bundle với artifact gốc.

### “Tại sao gọi PID khi P đang tốt hơn?”

> PID là khung thiết kế và ablation. Kết quả hiện tại cho thấy P là thành phần tạo lợi ích chính; I/D chưa bổ sung ổn định. Luận văn giữ kết quả này thay vì gán toàn bộ cải thiện cho full PID.

### “Mẫu được chọn trong vết PID có phải cherry-pick?”

> Vết mẫu chỉ minh họa cơ chế và dashboard có cả phản ví dụ. Kết luận hiệu quả dựa trên toàn bộ 1.922 mẫu cùng paired bootstrap, không dựa vào mẫu minh họa.

### “Fidelity có chứng minh SHAP đúng về mặt nhân quả không?”

> Không. Deletion và stability kiểm tra độ bám vào fitted model. Luận văn không chuyển kết quả này thành giải thích nhân quả.

## 8. Phương án dự phòng

Trước buổi bảo vệ:

- chạy `python scripts/run_defense_demo.py --check`;
- ngắt Wi-Fi và mở lại dashboard để xác nhận chạy offline;
- mở sẵn ba trang đóng góp trong một cửa sổ trình duyệt;
- lưu bản PDF slide và ảnh kết quả trong `results/` làm phương án dự phòng;
- không thay môi trường Python hoặc cập nhật package trong ngày bảo vệ.

Nếu Streamlit không khởi động, dùng trực tiếp các hình:

- `results/measured_20261028_fusion_only_evidence_1922/fusion_only_operating_tradeoff.png`;
- `results/confirmatory_20261019_ember_identity/al/aulc_and_label_budget.png`;
- `results/confirmatory_20261019_ember_identity/fidelity/deletion_effect.png`;
- `results/confirmatory_20261019_ember_identity/fidelity/shap_stability.png`.

Các hình này sử dụng cùng artifact với dashboard.
