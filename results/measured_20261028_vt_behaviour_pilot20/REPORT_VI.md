# Pilot dữ liệu động có timestamp từ VirusTotal

## Mục tiêu

Pilot kiểm tra liệu behavior report ghép theo SHA-256 có cung cấp timestamp gắn
với API call để đánh giá thành phần vi phân `D` theo wall-clock time hay không.
Toàn bộ quy trình chỉ tải metadata và behavior report; không tải hoặc thực thi
PE binary.

## Cohort và thu thập ban đầu

- Cohort nguồn: 1.923 mẫu MalBehavD đã khóa, SHA-256 manifest
  `9540b88b0da2463f63b4e983f5ecc277e3845b7badebbb79695e35f2c3b1a669`.
- Pilot: 20 mẫu, chọn cố định hai mẫu cho mỗi cặp `5 outer folds × 2 labels`.
- Cân bằng: 10 benign, 10 malware.
- Tốc độ: 4 VirusTotal request/phút.
- Kết quả: 20/20 mẫu có HTML behavior report tải thành công; không gặp HTTP
  429; không tải binary.
- GitHub Actions run: `40642154122`, thời lượng 10 phút 18 giây.

Trong 20 report được chọn ban đầu, 14 có token timestamp và 20 có token API.
Kiểm tra cấu trúc cho thấy lựa chọn provider ban đầu không cân bằng cho event
timeline: chỉ 2/20 có tín hiệu mạnh và cả hai đều là benign.

## Audit provider

Hai mươi listing chứa 111 behavior objects. Coverage đáng chú ý:

| Provider | Mẫu có HTML | Benign | Malware | EVTX |
|---|---:|---:|---:|---:|
| CAPE Sandbox | 9 | 9 | 0 | 8 |
| VirusTotal Cuckoofork | 9 | 2 | 7 | 0 |
| VirusTotal Jujubox | 15 | 9 | 6 | 0 |
| Tencent HABO | 14 | 5 | 9 | 0 |
| VenusEye Sandbox | 4 | 0 | 4 | 0 |
| Zenbox | 3 HTML / 8 EVTX | 2 HTML | 1 HTML | 8 |

EVTX hiện không cân bằng: 9 benign và 1 malware. Vì vậy EVTX pilot chưa phù
hợp làm bằng chứng hai lớp. VirusTotal Cuckoofork được chọn để kiểm tra tiếp vì
có report cho cả hai lớp và report chứa các khóa `api`/`timestamp` lặp theo
event.

## Kết quả Cuckoofork

- Tải 9 report: 2 benign, 7 malware.
- 9/9 tải thành công.
- 8/9 đạt kiểm tra chuỗi event: 2 benign, 6 malware.
- 1 malware bị loại vì chỉ có hai timestamp phân biệt.
- Tổng số event trích được: 4.697.
- Số event mỗi execution: 13–1.658.
- Số API phân biệt: 10–25.
- Tỷ lệ ghép cục bộ `api–timestamp`: 100% ở cả chín report.
- Tỷ lệ timestamp không giảm: 99,77–100%.

Timestamp Cuckoofork có dạng:

```text
YYYYMMDDhhmmss.fraction
```

Ví dụ `20210415144055.258`. Parser chuyển timestamp bằng `datetime`; không trừ
trực tiếp giá trị thập phân qua ranh giới phút. Sau sửa parser, thời lượng quan
sát của tám chuỗi usable nằm trong khoảng 0,02–60,816 giây.

## Kết luận học thuật hiện tại

Pilot chứng minh **nguồn và parser khả thi** để xây dữ liệu event có timestamp
thật. Kết quả này chưa chứng minh PID hoặc thành phần `D` cải thiện hiệu năng.
Chưa chạy confirmatory PID vì:

1. chỉ có tám execution usable;
2. phân bố lớp còn lệch 2 benign / 6 malware;
3. nhiều execution ngắn hơn 5 giây;
4. API và timestamp hiện được ghép theo thứ tự xuất hiện trong report; cần khóa
   parser provider-specific và kiểm tra thêm trước khi mở rộng;
5. process ID chưa được ánh xạ tới từng API call.

## Điều kiện để mở rộng

Collector toàn cohort cần:

1. thu behavior listing cho SHA-256 đã khóa;
2. ưu tiên Cuckoofork report có HTML;
3. parse `api`, `timestamp` và chuẩn hóa thời gian tương đối;
4. loại execution có dưới ba timestamp phân biệt hoặc thứ tự thời gian không
   đạt 95%;
5. báo coverage theo label/fold và phân bố thời lượng trước khi huấn luyện;
6. chỉ chạy PID sau khi có coverage hai lớp đủ cho outer-fold evaluation;
7. giữ raw report trong artifact riêng, lưu hash và provenance; không commit raw
   HTML vào Git.

## Artifact chính

- `coverage_audit.json`: coverage thu report pilot.
- `provider_availability_audit.json`: availability HTML/EVTX theo provider.
- `provider_html_structure_audit.json`: kiểm tra cấu trúc Cuckoofork.
- `event_extraction_summary.json`: tổng số event và chuỗi usable.
- `event_sequence_audit.csv`: audit từng execution.
- `artifact_sha256.txt`: hash các artifact đã commit.

Raw report và event-level CSV được giữ trong GitHub Actions artifacts có thời
hạn; repository chỉ lưu audit và hash, không lưu raw behavior content.
