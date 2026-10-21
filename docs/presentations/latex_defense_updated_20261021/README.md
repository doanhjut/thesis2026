# Slide LaTeX cập nhật — 21/10/2026

Bộ slide gồm 15 trang, tập trung vào ba đóng góp và bằng chứng thực nghiệm:

1. PID Fusion trên 199 mẫu ghép cặp MalBehavD-V1 (100 benign, 99 malware), 5 outer folds, trục động 5/10/15/20 sự kiện API.
2. XAI-Guided Active Learning trên EMBER 2018, 5 folds × 5 seeds.
3. Deletion và rank stability để kiểm tra TreeSHAP trên đặc trưng PE dạng bảng.

Các con số trong slide được lấy từ artifact hiện có. PID được trình bày đúng phạm vi thăm dò của cohort 199 mẫu; deck không tuyên bố đã hoàn thành cohort 1.923 mẫu, không tuyên bố thành phần D làm giảm FPR và không gộp các phép đo Fidelity thành OFS.

## Biên dịch

Slide dùng XeLaTeX để hiển thị tiếng Việt ổn định:

```bash
xelatex -interaction=nonstopmode -halt-on-error Luan_van_Luu_Van_Doanh_UET_updated.tex
xelatex -interaction=nonstopmode -halt-on-error Luan_van_Luu_Van_Doanh_UET_updated.tex
```

Giữ thư mục `assets/` cạnh tệp `.tex`.

## Artifact nguồn

- `results/measured_20261020_malbehavd_pid_pilot200/`
- `results/confirmatory_20261019_ember_identity/al/`
- `results/confirmatory_20261019_ember_identity/fidelity/`

