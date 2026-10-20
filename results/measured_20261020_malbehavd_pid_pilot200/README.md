# Pilot đo thật: dung hợp tĩnh–động theo tiến trình sự kiện

## Trạng thái bằng chứng

Đây là **pilot đã đo**, không phải số liệu mô phỏng. Pipeline chọn trước 200 mẫu
cân bằng từ MalBehavD-V1, truy vấn metadata PE theo đúng SHA-256 và thu được đủ
hai kênh cho 199 mẫu (coverage 99,5%; 100 benign, 99 malware). Một SHA malware
không có bản ghi VirusTotal và bị loại trước khi huấn luyện. Không tải hoặc thực
thi executable.

Kết quả đủ để chứng minh pipeline tĩnh–động chạy được, split không rò rỉ và
adaptive fusion có xu hướng cải thiện khả năng xếp hạng. Kết quả **chưa đủ** để
kết luận thành phần D của PID tạo lợi ích riêng hoặc PID làm giảm FPR. Khi viết
luận văn, dùng gói này như pilot/ablation feasibility và giữ đúng giới hạn trên.

## Thiết kế thực nghiệm

- Nguồn: MalBehavD-V1 tại commit
  `6aac5027635ac3d2832d323a873fccd7cdd89a5e`; CSV nguồn có SHA-256
  `1e39c43a014e9b4ee56766ad6bb367ffe8ec4316eb0be75eb182c3b2d15f6364`.
- Trục động: chuỗi API call công khai tại các mốc 5, 10, 15 và 20 sự kiện. Đây
  là số sự kiện, không phải số giây.
- Kênh tĩnh: 199 feature cấu trúc từ `size`, `type_tag` và `pe_info`. AV verdict,
  detection count, threat name, tag và filename bị loại bằng allow-list.
- Đánh giá: năm outer fold đã khóa trước khi lấy metadata. Trong mỗi fold, tập
  huấn luyện base model, calibration, fusion validation và outer test tách rời.
- Gain, fixed weight và threshold chỉ chọn trên fusion validation. Test không
  tham gia lựa chọn.
- Đối chứng: Static, Dynamic, Average 50/50, Fixed weight, P, PI và PID.

## Kết quả cuối chuỗi

Các ô là trung bình ± sample SD qua năm outer fold.

| Phương pháp | ROC-AUC | AP | FPR (%) | TPR (%) | Brier |
|---|---:|---:|---:|---:|---:|
| Static | 0,9254 ± 0,0667 | 0,9286 ± 0,0479 | 47,08 ± 28,23 | 96,28 ± 3,44 | 0,0980 ± 0,0654 |
| Dynamic | 0,9345 ± 0,0428 | 0,9437 ± 0,0375 | 47,96 ± 16,69 | 96,95 ± 4,71 | 0,1102 ± 0,0305 |
| Average 50/50 | 0,9582 ± 0,0344 | 0,9663 ± 0,0240 | 34,97 ± 23,46 | 96,28 ± 3,44 | 0,0810 ± 0,0318 |
| Fixed weight | 0,9415 ± 0,0449 | 0,9558 ± 0,0314 | **29,97 ± 15,41** | 93,23 ± 2,39 | 0,0927 ± 0,0381 |
| P | **0,9592 ± 0,0335** | **0,9674 ± 0,0229** | 34,97 ± 23,46 | 96,28 ± 3,44 | 0,0816 ± 0,0326 |
| PI | 0,9583 ± 0,0354 | 0,9660 ± 0,0253 | 34,97 ± 23,46 | 96,28 ± 3,44 | 0,0854 ± 0,0391 |
| PID | 0,9583 ± 0,0354 | 0,9660 ± 0,0253 | 34,97 ± 23,46 | 96,28 ± 3,44 | 0,0854 ± 0,0391 |

PID so với Fixed trên dự đoán out-of-fold:

- ΔAUC = +0,0130; bootstrap 95% CI [-0,0086; +0,0409].
- ΔAP = +0,0080; bootstrap 95% CI [-0,0102; +0,0272].
- ΔFPR = +5,06 điểm phần trăm; bootstrap 95% CI [0,00; +10,58]. Giá trị
  dương nghĩa là PID có FPR cao hơn.
- ΔTPR = +4,10 điểm phần trăm; bootstrap 95% CI [+0,94; +8,26].
- AUC của PID cao hơn Fixed ở 4/5 fold và hòa 1/5. FPR hòa ở 4/5 fold và xấu
  hơn ở 1/5.

PID và PI gần như trùng nhau: sai khác tuyệt đối của score tại mốc cuối trung
bình 0,000109, tối đa 0,001196 và không làm thay đổi quyết định nào trong 199
mẫu. Vì vậy pilot hiện tại chưa chứng minh đóng góp gia tăng của thành phần D.

## Cách dùng trong luận văn

Có thể dùng ngay:

- bảng `event_pid_table.tex` và hai biểu đồ PDF/PNG;
- lập luận rằng hai nguồn bổ sung cho nhau và adaptive fusion cải thiện ranking
  trong pilot so với từng kênh riêng;
- minh họa quy trình ablation P → PI → PID, đồng thời báo trung thực rằng D chưa
  có hiệu ứng nhận diện được trong cấu hình này;
- chứng minh an toàn dữ liệu: chỉ dùng report/metadata, không giữ executable.

Chưa được dùng để khẳng định:

- PID giảm cảnh báo nhầm hoặc vượt PI;
- hiệu quả trên ransomware nói riêng;
- độ trễ theo giây hoặc tính sẵn sàng production;
- cải thiện có ý nghĩa thống kê ở mức xác nhận, vì CI của ΔAUC và ΔAP còn cắt 0.

Để biến thành kết quả xác nhận, tiếp tục thu metadata cho cohort 1.923 mẫu đã
khóa, chạy lại đúng năm fold và giữ nguyên protocol. Nếu D vẫn không hơn PI,
kết luận học thuật đúng là P/PI đủ cho dữ liệu này hoặc cần sửa định nghĩa
error/dynamics; không nên thay số liệu hay chọn lại split.

## Tái lập

Code tương ứng ở commit `44812ad0c9997e47b418db55975d80c9814b9b77`.

```bash
MPLCONFIGDIR=/tmp/mplconfig XDG_CACHE_HOME=/tmp/cache \
.venv/bin/python scripts/run_experiments.py event-pid \
  --sequences outputs/malbehavd_pid_20261020_prepared/api_sequences.csv.gz \
  --static-features outputs/malbehavd_pid_20261020_vt_pilot20/static_features.csv.gz \
  --selection outputs/malbehavd_pid_20261020_vt_pilot20/selected_cohort.csv \
  --output outputs/malbehavd_pid_pilot200_replay \
  --windows 5 10 15 20 --target-tpr 0.95 --min-coverage 0.90 \
  --bootstrap 1000 --seed 2026
```

`verification.json` xác nhận 35 hàng metric và 1.393 dự đoán cuối fold/method
được tái tính thành công. `artifact_sha256.json` khóa hash toàn bộ gói. Raw
VirusTotal response không được commit; `static_features.csv.gz` là bảng dẫn
xuất đã lọc allow-list để có thể tái lập mà không gọi lại API.
