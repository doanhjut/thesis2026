# Xác nhận PID theo tiến trình sự kiện trên 1.922 mẫu

Run sử dụng 1.922/1.923 mẫu MalBehavD-V1 có metadata tĩnh ghép theo SHA-256 và
chuỗi API động tại 5, 10, 15, 20 sự kiện. Coverage là 99,95%; một SHA-256 trả
HTTP 404 và được giữ là missing thật. `verification.json` replay 35 dòng metric
và 13.454 dự đoán cuối-fold với trạng thái `passed`.

## Kết quả ablation chính

| Phương pháp | ROC-AUC | AP | FPR (%) | TPR (%) | Brier |
|---|---:|---:|---:|---:|---:|
| Static-only | 0,9702 ± 0,0140 | 0,9700 ± 0,0130 | 23,58 ± 11,74 | 96,56 ± 2,01 | 0,0567 ± 0,0146 |
| Dynamic-only | 0,9733 ± 0,0076 | 0,9802 ± 0,0055 | 16,40 ± 5,57 | 95,46 ± 2,11 | 0,0584 ± 0,0106 |
| Average 50/50 | **0,9844 ± 0,0088** | **0,9883 ± 0,0059** | 13,40 ± 6,49 | 96,57 ± 0,66 | **0,0455 ± 0,0100** |
| Fixed-weight | 0,9832 ± 0,0086 | 0,9872 ± 0,0060 | **11,69 ± 3,58** | 96,06 ± 0,84 | 0,0481 ± 0,0108 |
| P | 0,9838 ± 0,0088 | 0,9878 ± 0,0058 | 13,29 ± 6,07 | 96,36 ± 0,74 | 0,0476 ± 0,0101 |
| PI | 0,9837 ± 0,0089 | 0,9877 ± 0,0059 | 13,83 ± 6,06 | 96,47 ± 0,71 | 0,0474 ± 0,0102 |
| PID | 0,9838 ± 0,0088 | 0,9877 ± 0,0058 | 13,83 ± 6,06 | 96,47 ± 0,71 | 0,0479 ± 0,0105 |

Dung hợp hai nguồn cải thiện ranking so với từng kênh. Tuy nhiên Average 50/50
đạt AUC/AP/Brier tốt nhất, còn Fixed-weight đạt FPR thấp nhất. Vì vậy kết quả
không hỗ trợ phát biểu PID là luật dung hợp tốt nhất trên cohort này.

## PID so với Fixed-weight

Bootstrap ghép cặp trên 1.922 dự đoán out-of-fold, PID trừ Fixed:

- ΔAUC = +0,00043; CI 95% [-0,00088; +0,00175].
- ΔAP = +0,00027; CI 95% [-0,00079; +0,00137].
- ΔBrier = -0,00018; CI 95% [-0,00257; +0,00200].
- ΔFPR = **+2,16 điểm phần trăm**; CI 95% [+0,84; +3,50].
- ΔTPR = +0,40 điểm phần trăm; CI 95% [-0,20; +1,00].

AUC/AP/Brier/TPR chưa có khác biệt chắc chắn; FPR của PID cao hơn Fixed ở 5/5
fold. Không được dùng run này để tuyên bố PID giảm cảnh báo nhầm.

## Kiểm tra riêng thành phần D

Hai phép so sánh bổ sung đã được chạy và lưu trong `d_component_ablation.json`.

### 1. PID tối ưu so với PI tối ưu

Mỗi họ chọn gain riêng trên validation. Trên dự đoán out-of-fold:

- PID AUC 0,983674; PI AUC 0,983800; ΔAUC bootstrap = -0,000125,
  CI 95% [-0,000296; +0,000044].
- PID AP 0,987410; PI AP 0,987528; ΔAP = -0,000116,
  CI 95% [-0,000274; +0,000040].
- PID Brier 0,047879; PI Brier 0,047358; ΔBrier = +0,000512,
  CI 95% [+0,000134; +0,000934], bất lợi cho PID.
- FPR, TPR và ma trận nhầm lẫn giống nhau; D làm đổi 0/1.922 quyết định cuối.

### 2. Tắt D với cùng Kp, Ki và threshold của PID

Đây là phép cô lập trực tiếp hơn: giữ cấu hình PID đã chọn và đặt Kd=0.

- ΔAUC = +0,000015; CI 95% [-0,000021; +0,000049].
- ΔAP = +0,000012; CI 95% [-0,000019; +0,000043].
- ΔBrier = -0,000005; CI 95% [-0,000026; +0,000018].
- FPR và TPR không đổi; 0/1.922 quyết định cuối thay đổi.
- |Δscore| trung bình tại mốc cuối là 0,000207; lớn nhất 0,005207.
- Trên cả bốn mốc sự kiện, 6/7.688 dòng dự đoán đổi nhãn, nhưng không còn khác
  biệt tại mốc cuối.

**Kết luận về D:** chưa có bằng chứng cho thấy thành phần vi phân tạo lợi ích thực
tế ở chuỗi 5--20 sự kiện. Kết quả hỗ trợ lựa chọn cấu hình đơn giản hơn (P, PI,
Average hoặc Fixed tùy mục tiêu) thay vì khẳng định PID đầy đủ vượt trội.

## Phạm vi

Trục thời gian là số sự kiện API, không phải giây. Dữ liệu xác nhận generic
Windows malware, không phải ransomware-specific. Metadata tĩnh dùng allow-list
thuộc tính PE của VirusTotal; không tải hoặc thực thi executable trong quá trình thu.
