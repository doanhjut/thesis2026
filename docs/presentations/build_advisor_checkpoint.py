#!/usr/bin/env python3
"""Build the 9-slide advisor checkpoint deck from measured repository artifacts."""

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE, MSO_CONNECTOR
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt


OUT = Path(__file__).resolve().parent
PPTX = OUT / "Bao_cao_GVHD_truoc_bao_ve_20261020.pptx"

W, H = Inches(13.333), Inches(7.5)

BG = RGBColor(10, 18, 34)
PANEL = RGBColor(20, 32, 54)
PANEL_2 = RGBColor(26, 42, 68)
WHITE = RGBColor(245, 248, 252)
MUTED = RGBColor(172, 187, 207)
CYAN = RGBColor(64, 208, 255)
BLUE = RGBColor(96, 137, 255)
GREEN = RGBColor(66, 211, 146)
AMBER = RGBColor(255, 190, 82)
RED = RGBColor(255, 105, 120)
GRID = RGBColor(57, 75, 104)

FONT = "Noto Sans"
FONT_MONO = "DejaVu Sans Mono"


def fill(shape, color, transparency=0):
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.fill.transparency = transparency
    shape.line.fill.background()


def text_box(slide, x, y, w, h, text, size=18, color=WHITE, bold=False,
             align=PP_ALIGN.LEFT, font=FONT, margin=0.05, valign=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.clear()
    tf.margin_left = Inches(margin)
    tf.margin_right = Inches(margin)
    tf.margin_top = Inches(margin)
    tf.margin_bottom = Inches(margin)
    tf.vertical_anchor = valign
    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = text
    r.font.name = font
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.color.rgb = color
    return box


def rich_text(slide, x, y, w, h, lines, size=17, leading=1.08, margin=0.08):
    """lines: list[(text, color, bold, level)]"""
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.clear()
    tf.margin_left = Inches(margin)
    tf.margin_right = Inches(margin)
    tf.margin_top = Inches(margin)
    tf.margin_bottom = Inches(margin)
    for i, (value, color, bold, level) in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.level = level
        p.space_after = Pt(6)
        p.line_spacing = leading
        r = p.add_run()
        r.text = value
        r.font.name = FONT
        r.font.size = Pt(size - level)
        r.font.bold = bold
        r.font.color.rgb = color
    return box


def rect(slide, x, y, w, h, color=PANEL, radius=True, line=None):
    kind = MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE if radius else MSO_AUTO_SHAPE_TYPE.RECTANGLE
    s = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    fill(s, color)
    if line:
        s.line.color.rgb = line
        s.line.width = Pt(1)
    return s


def pill(slide, x, y, w, text, color=CYAN, text_color=BG):
    s = rect(slide, x, y, w, 0.34, color)
    text_box(slide, x, y + 0.01, w, 0.29, text, 10.5, text_color, True, PP_ALIGN.CENTER)
    return s


def header(slide, section, title, subtitle, num):
    text_box(slide, 0.62, 0.36, 3.3, 0.28, section.upper(), 11, CYAN, True)
    text_box(slide, 0.62, 0.72, 12.0, 0.55, title, 25, WHITE, True)
    text_box(slide, 0.62, 1.29, 12.0, 0.42, subtitle, 12.5, MUTED)
    text_box(slide, 12.25, 0.40, 0.48, 0.27, f"{num:02d}", 11, MUTED, True, PP_ALIGN.RIGHT)
    line = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.RECTANGLE, Inches(0.62), Inches(1.76), Inches(12.08), Inches(0.02))
    fill(line, GRID)


def footer(slide, source):
    text_box(slide, 0.62, 7.13, 11.8, 0.20, source, 8.5, MUTED)


def add_card(slide, x, y, w, h, title, value, note="", accent=CYAN):
    rect(slide, x, y, w, h, PANEL)
    text_box(slide, x + 0.18, y + 0.15, w - 0.36, 0.28, title.upper(), 10, accent, True)
    text_box(slide, x + 0.18, y + 0.50, w - 0.36, 0.52, value, 23, WHITE, True)
    if note:
        text_box(slide, x + 0.18, y + h - 0.48, w - 0.36, 0.32, note, 10, MUTED)


def bar_chart(slide, x, y, w, h, labels, values, colors, vmin=0.0, vmax=1.0,
              value_fmt=lambda v: f"{v:.3f}", label_w=1.45, value_w=0.7):
    n = len(labels)
    row_h = h / n
    bar_x = x + label_w
    bar_w = w - label_w - value_w
    for i, (lab, val, col) in enumerate(zip(labels, values, colors)):
        yy = y + i * row_h
        text_box(slide, x, yy + 0.02, label_w - 0.08, row_h - 0.04, lab, 11.2, WHITE,
                 bold=(col == CYAN or col == GREEN), valign=MSO_ANCHOR.MIDDLE)
        rect(slide, bar_x, yy + row_h * 0.29, bar_w, row_h * 0.36, GRID, radius=False)
        frac = max(0.012, min(1.0, (val - vmin) / (vmax - vmin)))
        rect(slide, bar_x, yy + row_h * 0.29, bar_w * frac, row_h * 0.36, col, radius=False)
        text_box(slide, bar_x + bar_w + 0.08, yy + 0.02, value_w - 0.08, row_h - 0.04,
                 value_fmt(val), 11.2, col, True, PP_ALIGN.RIGHT, valign=MSO_ANCHOR.MIDDLE)


def add_chevron(slide, x, y, w, h, title, note, accent):
    s = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.CHEVRON, Inches(x), Inches(y), Inches(w), Inches(h))
    fill(s, PANEL_2)
    s.line.color.rgb = accent
    s.line.width = Pt(1.2)
    text_box(slide, x + 0.12, y + 0.16, w - 0.42, 0.30, title, 13.5, accent, True)
    text_box(slide, x + 0.12, y + 0.52, w - 0.44, h - 0.62, note, 10.4, MUTED)


def new_slide(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = slide.background.fill
    bg.solid()
    bg.fore_color.rgb = BG
    return slide


def build():
    prs = Presentation()
    prs.slide_width = W
    prs.slide_height = H
    prs.core_properties.title = "Báo cáo GVHD trước bảo vệ — bằng chứng cho ba đóng góp"
    prs.core_properties.subject = "Kết quả thực nghiệm đo thật và kế hoạch hoàn tất trong 20 ngày"
    prs.core_properties.author = "Lưu Văn Doanh"

    # 1 — Cover
    s = new_slide(prs)
    rect(s, 0, 0, 0.22, 7.5, CYAN, radius=False)
    pill(s, 0.72, 0.58, 2.35, "BÁO CÁO VỚI GVHD", CYAN)
    text_box(s, 0.72, 1.30, 11.6, 1.18, "Bằng chứng thực nghiệm cho\nba đóng góp của luận văn", 34, WHITE, True)
    text_box(s, 0.75, 2.73, 10.8, 0.60,
             "Phát hiện mã độc đa tầng • PID Fusion • XAI-Guided Active Learning • Fidelity",
             16, MUTED)
    add_card(s, 0.75, 4.05, 3.65, 1.53, "Đã xác nhận", "2 đóng góp", "AL và Fidelity • 5-fold", GREEN)
    add_card(s, 4.63, 4.05, 3.65, 1.53, "Đã chạy pilot", "PID • n = 199", "Pipeline end-to-end • 5-fold", AMBER)
    add_card(s, 8.51, 4.05, 3.65, 1.53, "Thời gian còn lại", "20 ngày", "Hoàn tất PID và khóa luận văn", CYAN)
    text_box(s, 0.75, 6.35, 11.6, 0.37,
             "Học viên: Lưu Văn Doanh   |   GVHD: PGS.TS. Trương Ninh Thuận   |   20/10/2026",
             12, WHITE)
    text_box(s, 0.75, 6.84, 11.6, 0.25,
             "Mục tiêu buổi làm việc: thống nhất phạm vi kết luận và kế hoạch chốt bản bảo vệ.",
             10, MUTED)

    # 2 — Novelty
    s = new_slide(prs)
    header(s, "01 / Định vị nghiên cứu", "Điểm mới nằm ở ba khoảng trống có thể đo được",
           "So sánh trực tiếp cách làm phổ biến với cơ chế đề xuất và bằng chứng tương ứng.", 2)
    cols = [
        ("Cách làm phổ biến", "Trọng số tĩnh–động cố định", "Lấy mẫu theo bất định", "SHAP chỉ để minh họa"),
        ("Đóng góp của luận văn", "PID điều chỉnh trọng số theo tiến trình", "Thêm H và V từ cấu trúc SHAP", "Deletion + stability theo đối chứng"),
        ("Đại lượng chứng minh", "P / PI / PID • AUC, AP, FPR, TPR", "AULC • nhãn để đạt mục tiêu • overhead", "Top-SHAP vs random • nhiều k / baseline"),
    ]
    xs = [0.68, 4.46, 8.24]
    accents = [MUTED, CYAN, GREEN]
    for x, data, ac in zip(xs, cols, accents):
        rect(s, x, 2.08, 3.43, 4.30, PANEL)
        text_box(s, x + 0.22, 2.31, 3.0, 0.40, data[0], 15, ac, True)
        for j, val in enumerate(data[1:]):
            yy = 2.95 + j * 1.03
            text_box(s, x + 0.22, yy, 0.32, 0.32, str(j + 1).zfill(2), 11, ac, True)
            text_box(s, x + 0.66, yy - 0.02, 2.50, 0.64, val, 12.5, WHITE, j == 0 and x == 4.46)
    footer(s, "Phạm vi đo: mã độc Windows/EMBER; các phát biểu ransomware-specific chỉ dùng khi nhãn nguồn hỗ trợ.")

    # 3 — Architecture
    s = new_slide(prs)
    header(s, "02 / Kiến trúc", "Một hệ thống, ba câu hỏi nghiên cứu tách biệt",
           "Mỗi đóng góp có đối chứng và tiêu chí đánh giá riêng để tránh gộp hiệu quả.", 3)
    add_chevron(s, 0.68, 2.20, 2.25, 1.18, "Tĩnh", "Đặc trưng PE → pₛ", BLUE)
    add_chevron(s, 3.12, 2.20, 2.25, 1.18, "Cổng", "Bất định quyết định chạy động", AMBER)
    add_chevron(s, 5.56, 2.20, 2.25, 1.18, "Động", "Chuỗi API → p_d", GREEN)
    add_chevron(s, 8.00, 2.20, 2.25, 1.18, "PID Fusion", "pₛ + p_d → quyết định", CYAN)
    add_chevron(s, 10.44, 2.20, 2.25, 1.18, "Đầu ra", "Score + giải thích", WHITE)
    # Support lanes
    rect(s, 0.68, 4.05, 5.82, 1.55, PANEL)
    pill(s, 0.91, 4.26, 1.23, "ĐÓNG GÓP 2", BLUE, WHITE)
    text_box(s, 0.91, 4.75, 5.20, 0.34, "XAI-Guided AL", 18, WHITE, True)
    text_box(s, 0.91, 5.15, 5.25, 0.27, "Chọn mẫu cần nhãn → cập nhật mô hình tĩnh", 11.5, MUTED)
    rect(s, 6.72, 4.05, 5.95, 1.55, PANEL)
    pill(s, 6.95, 4.26, 1.23, "ĐÓNG GÓP 3", GREEN, BG)
    text_box(s, 6.95, 4.75, 5.20, 0.34, "Fidelity & Stability", 18, WHITE, True)
    text_box(s, 6.95, 5.15, 5.25, 0.27, "Kiểm tra giải thích bằng tác động và độ lặp lại", 11.5, MUTED)
    text_box(s, 0.80, 6.24, 11.70, 0.43,
             "Luận điểm trung tâm: hiệu quả được đánh giá bằng vận hành, chi phí nhãn và độ tin cậy — không chỉ một giá trị Accuracy.",
             14, CYAN, True, PP_ALIGN.CENTER)
    footer(s, "Nguồn thiết kế: src/pid_fusion.py • src/xai_active_learning.py • src/fidelity_framework.py")

    # 4 — PID measured pilot
    s = new_slide(prs)
    header(s, "03 / Đóng góp 1 — PID Fusion", "Pilot xác nhận dung hợp; thành phần D chưa tạo hiệu ứng riêng",
           "199 mẫu ghép cặp tĩnh–động • 5 outer folds • tham số và ngưỡng chọn ngoài test.", 4)
    rect(s, 0.68, 2.03, 6.25, 4.45, PANEL)
    text_box(s, 0.94, 2.25, 5.75, 0.34, "ROC-AUC cuối chuỗi sự kiện", 14, WHITE, True)
    bar_chart(s, 0.94, 2.78, 5.70, 3.20,
              ["Static", "Dynamic", "Fixed", "P", "PI", "PID"],
              [0.9254, 0.9345, 0.9415, 0.9592, 0.9583, 0.9583],
              [BLUE, GREEN, MUTED, CYAN, AMBER, AMBER],
              vmin=0.90, vmax=0.97, value_fmt=lambda v: f"{v:.4f}", label_w=1.12, value_w=0.78)
    text_box(s, 0.94, 6.10, 5.75, 0.20, "Trung bình 5 fold; thanh bắt đầu tại AUC = 0,90.", 8.8, MUTED)
    add_card(s, 7.20, 2.03, 2.50, 1.28, "PID − Fixed", "+0,0130 AUC", "95% CI: −0,0086 → +0,0409", CYAN)
    add_card(s, 9.93, 2.03, 2.73, 1.28, "Đánh đổi", "+4,10 pp TPR", "95% CI: +0,94 → +8,26", GREEN)
    add_card(s, 7.20, 3.54, 2.50, 1.28, "FPR", "+5,06 pp", "PID cao hơn Fixed trong pilot", RED)
    add_card(s, 9.93, 3.54, 2.73, 1.28, "P so với PID", "P: 0,9592", "PID: 0,9583 • gần như trùng", AMBER)
    rect(s, 7.20, 5.05, 5.46, 1.43, PANEL_2)
    text_box(s, 7.44, 5.28, 4.98, 0.30, "KẾT LUẬN ĐÚNG MỨC", 10, AMBER, True)
    text_box(s, 7.44, 5.68, 4.98, 0.58,
             "Dung hợp thích nghi cải thiện khả năng xếp hạng; PI và PID không đổi quyết định nào. Cần cohort lớn để kiểm định D và FPR.",
             12.3, WHITE)
    footer(s, "Nguồn: measured_20261020_malbehavd_pid_pilot200 • bootstrap ghép cặp 1.000 lần.")

    # 5 — AL
    s = new_slide(prs)
    header(s, "04 / Đóng góp 2 — XAI-Guided AL", "Tín hiệu XAI giảm số nhãn cần thiết và cải thiện đường học",
           "2.000 mẫu EMBER có định danh • 5 folds × 5 seeds • cùng split, pool và ngân sách.", 5)
    rect(s, 0.68, 2.03, 6.15, 4.47, PANEL)
    text_box(s, 0.94, 2.25, 5.62, 0.33, "Số nhãn huấn luyện để đạt AUC validation mục tiêu", 13.5, WHITE, True)
    bar_chart(s, 0.94, 2.87, 5.60, 2.82,
              ["Random", "Uncertainty", "U + H", "U + V", "XAI full"],
              [584, 520, 508, 488, 492],
              [MUTED, BLUE, AMBER, GREEN, CYAN],
              vmin=250, vmax=650, value_fmt=lambda v: f"{int(v)}", label_w=1.40, value_w=0.56)
    text_box(s, 0.94, 5.88, 5.62, 0.42,
             "XAI full tiết kiệm 92 nhãn (15,8%) so với Random\nvà 28 nhãn (5,4%) so với Uncertainty.",
             11.5, CYAN, True)
    add_card(s, 7.10, 2.03, 2.62, 1.38, "U+H − Random", "+0,00425", "ROC-AULC • thắng 5/5 folds", GREEN)
    add_card(s, 9.96, 2.03, 2.70, 1.38, "U+H − Random", "+0,01498", "AP-AULC • thắng 5/5 folds", GREEN)
    add_card(s, 7.10, 3.67, 2.62, 1.38, "XAI full", "492 nhãn", "Random cần 584 nhãn", CYAN)
    add_card(s, 9.96, 3.67, 2.70, 1.38, "Overhead truy vấn", "5,42%", "Tỷ trọng query/(train+query)", AMBER)
    rect(s, 7.10, 5.31, 5.56, 1.19, PANEL_2)
    text_box(s, 7.36, 5.55, 5.06, 0.57,
             "H giúp chất lượng đường học; V/full score giúp đạt mục tiêu với ít nhãn hơn. Đóng góp được chứng minh theo từng thành phần.",
             12.2, WHITE, True)
    footer(s, "Nguồn: confirmatory_20261019_ember_identity/al • 25 cặp fold–seed; nhãn là oracle query.")

    # 6 — Fidelity
    s = new_slide(prs)
    header(s, "05 / Đóng góp 3 — Đánh giá giải thích", "Top-SHAP ảnh hưởng dự đoán mạnh hơn đối chứng ngẫu nhiên",
           "25 mô hình • mean/median masking • k = 10, 25, 50 • kiểm tra thêm độ ổn định thứ hạng.", 6)
    rect(s, 0.68, 2.03, 7.18, 4.46, PANEL)
    text_box(s, 0.94, 2.25, 6.60, 0.33, "AUC drop sau masking — baseline = mean", 14, WHITE, True)
    # Custom grouped horizontal bars
    ks = [10, 25, 50]
    top = [0.047817, 0.135853, 0.306729]
    rnd = [0.000200, 0.000530, 0.000979]
    for i, k in enumerate(ks):
        yy = 2.98 + i * 0.94
        text_box(s, 0.94, yy, 0.58, 0.32, f"k={k}", 11.5, WHITE, True)
        rect(s, 1.60, yy + 0.02, 4.95, 0.20, GRID, radius=False)
        rect(s, 1.60, yy + 0.02, 4.95 * top[i] / 0.33, 0.20, CYAN, radius=False)
        text_box(s, 6.61, yy - 0.04, 0.92, 0.27, f"{top[i]:.4f}", 10.5, CYAN, True, PP_ALIGN.RIGHT)
        rect(s, 1.60, yy + 0.36, 4.95, 0.12, GRID, radius=False)
        rect(s, 1.60, yy + 0.36, max(0.025, 4.95 * rnd[i] / 0.33), 0.12, MUTED, radius=False)
        text_box(s, 6.61, yy + 0.29, 0.92, 0.27, f"{rnd[i]:.4f}", 10.2, MUTED, True, PP_ALIGN.RIGHT)
    pill(s, 1.60, 5.92, 1.28, "TOP-SHAP", CYAN)
    pill(s, 3.04, 5.92, 1.25, "RANDOM", MUTED, BG)
    add_card(s, 8.12, 2.03, 2.11, 1.40, "Spearman", "0,614", "within-fold • 50 cặp", GREEN)
    add_card(s, 10.48, 2.03, 2.18, 1.40, "Spearman", "0,551", "across-fold • 250 cặp", AMBER)
    add_card(s, 8.12, 3.70, 2.11, 1.40, "Top-25 drop", "0,1359", "random: 0,0005", CYAN)
    add_card(s, 10.48, 3.70, 2.18, 1.40, "Mô hình", "25", "5 folds × 5 seeds", BLUE)
    rect(s, 8.12, 5.37, 4.54, 1.12, PANEL_2)
    text_box(s, 8.36, 5.59, 4.05, 0.57,
             "Không gộp OFS khi chưa có chuẩn hóa chung; báo riêng fidelity, contrast và stability.",
             11.8, WHITE, True)
    footer(s, "Nguồn: confirmatory_20261019_ember_identity/fidelity • masking trong không gian đặc trưng EMBER.")

    # 7 — Seminar response
    s = new_slide(prs)
    header(s, "06 / Tiếp thu Seminar", "Mỗi nhận xét đã được chuyển thành một phép kiểm chứng cụ thể",
           "Tách rõ điều đã đo, kết luận được phép nói và phần đang hoàn tất.", 7)
    rows = [
        ("PID có cần thiết? P/PI/PID khác gì?", "Ablation 7 cấu hình + bootstrap ghép cặp", "PILOT", AMBER),
        ("Chỉ số XAI có phù hợp với mã độc?", "Mean/median masking + random control + 3 mức k", "ĐÃ ĐO", GREEN),
        ("Kết quả gán nhãn chưa thuyết phục", "5 folds × 5 seeds; AULC + budget-to-target", "ĐÃ ĐO", GREEN),
        ("AUC tăng ít có ý nghĩa gì?", "Báo CI, AP, FPR/TPR, low-FPR và chi phí nhãn", "ĐÃ SỬA", CYAN),
        ("Tĩnh / động / kết hợp đóng góp gì?", "Static, Dynamic, Fixed, P, PI, PID cùng protocol", "PILOT", AMBER),
        ("Toàn hệ thống được gì?", "Claim–evidence map; không cộng chéo metric khác run", "ĐÃ SỬA", CYAN),
    ]
    y0 = 2.04
    for i, (feedback, action, status, ac) in enumerate(rows):
        yy = y0 + i * 0.72
        rect(s, 0.68, yy, 12.00, 0.61, PANEL if i % 2 == 0 else PANEL_2)
        text_box(s, 0.92, yy + 0.11, 4.18, 0.34, feedback, 11.3, WHITE, True)
        text_box(s, 5.17, yy + 0.11, 5.72, 0.34, action, 11.1, MUTED)
        pill(s, 11.07, yy + 0.135, 1.32, status, ac, BG if ac != MUTED else WHITE)
    footer(s, "Nguyên tắc khóa luận: mọi con số trên slide truy về một artifact; kết quả âm vẫn được giữ.")

    # 8 — Readiness and 20-day plan
    s = new_slide(prs)
    header(s, "07 / Mức sẵn sàng", "Phần còn lại tập trung vào xác nhận PID trên cohort đầy đủ",
           "Pipeline, split, audit và artifact schema đã khóa; không cần thiết kế lại nghiên cứu.", 8)
    add_card(s, 0.68, 2.03, 2.80, 1.38, "Cohort PID", "1.923 mẫu", "932 benign • 991 malware", BLUE)
    add_card(s, 3.72, 2.03, 2.80, 1.38, "Đã thu", "493 mẫu", "25,64% • cân bằng theo fold", AMBER)
    add_card(s, 6.76, 2.03, 2.80, 1.38, "Ngưỡng chạy", "≥ 90%", "1.731 mẫu usable", CYAN)
    add_card(s, 9.80, 2.03, 2.88, 1.38, "Cần thêm tối thiểu", "1.238 mẫu", "Sau đó chạy đúng protocol", GREEN)
    phases = [
        ("D−20 → D−16", "Thu đủ metadata", "Audit coverage ≥90%; khóa manifest"),
        ("D−15 → D−12", "Chạy PID confirmatory", "5-fold; P/PI/PID; CI và sensitivity"),
        ("D−11 → D−7", "Cập nhật luận văn", "Bảng, hình, phạm vi kết luận"),
        ("D−6 → D−3", "Khóa slide", "Đối soát số và nguồn artifact"),
        ("D−2 → D−0", "Luyện bảo vệ", "Q&A PID, overhead, OFS"),
    ]
    x = 0.68
    widths = [2.32, 2.32, 2.32, 2.32, 2.32]
    accents = [AMBER, CYAN, GREEN, BLUE, WHITE]
    for (period, title, note), ww, ac in zip(phases, widths, accents):
        rect(s, x, 3.78, ww, 2.20, PANEL)
        text_box(s, x + 0.18, 4.00, ww - 0.36, 0.28, period, 10.2, ac, True)
        text_box(s, x + 0.18, 4.43, ww - 0.36, 0.52, title, 14.2, WHITE, True)
        text_box(s, x + 0.18, 5.14, ww - 0.36, 0.58, note, 10.3, MUTED)
        x += ww + 0.10
    text_box(s, 0.82, 6.34, 11.72, 0.40,
             "Điều kiện chốt: chỉ thay bảng PID pilot bằng kết quả full-cohort sau khi verification và hash artifact đều đạt.",
             12.5, CYAN, True, PP_ALIGN.CENTER)
    footer(s, "Tiến độ đo tại 20/10/2026: measured_20261020_malbehavd_pid_full_collection_progress.")

    # 9 — Decision
    s = new_slide(prs)
    header(s, "08 / Đề xuất chốt phạm vi", "Có cơ sở để tiếp tục bảo vệ trong đợt này",
           "Hai đóng góp đã có confirmatory evidence; PID có pilot tái lập và kế hoạch xác nhận trong 20 ngày.", 9)
    statuses = [
        ("01", "PID Fusion", "PILOT ĐÃ ĐO", "AUC +0,013 so với Fixed; cần cohort lớn để chốt D/FPR", AMBER),
        ("02", "XAI-Guided AL", "ĐÃ XÁC NHẬN", "−15,8% nhãn so với Random; AULC cải thiện 5/5 folds", GREEN),
        ("03", "Fidelity", "ĐÃ XÁC NHẬN", "Top-SHAP deletion >> random; stability đo trên 25 model", GREEN),
    ]
    xs = [0.68, 4.48, 8.28]
    for x, (n, title, status, note, ac) in zip(xs, statuses):
        rect(s, x, 2.10, 3.52, 2.80, PANEL)
        text_box(s, x + 0.24, 2.33, 0.52, 0.40, n, 13, ac, True)
        text_box(s, x + 0.24, 2.83, 3.02, 0.45, title, 17, WHITE, True)
        pill(s, x + 0.24, 3.47, 1.55, status, ac, BG)
        text_box(s, x + 0.24, 4.00, 3.02, 0.62, note, 11.2, MUTED)
    rect(s, 0.68, 5.27, 11.12, 1.20, PANEL_2)
    text_box(s, 0.95, 5.48, 7.52, 0.30, "ĐỀ NGHỊ THẦY HƯỚNG DẪN THỐNG NHẤT", 11, CYAN, True)
    text_box(s, 0.95, 5.91, 7.52, 0.32,
             "Giữ ba đóng góp; ưu tiên hoàn tất PID; khóa phát biểu theo đúng bằng chứng đo được.",
             14.2, WHITE, True)
    pill(s, 9.03, 5.65, 2.42, "20 NGÀY ĐỂ CHỐT", CYAN)
    text_box(s, 0.82, 6.72, 11.62, 0.28,
             "Thông điệp bảo vệ: giá trị của hệ thống nằm ở dung hợp thích nghi, tiết kiệm nhãn và giải thích có thể kiểm chứng.",
             12.6, WHITE, True, PP_ALIGN.CENTER)
    footer(s, "Tất cả số liệu trong deck lấy từ artifact đã đo; không dùng bảng giả lập hoặc số bản thảo chưa xác minh.")

    PPTX.parent.mkdir(parents=True, exist_ok=True)
    prs.save(PPTX)
    print(PPTX)


if __name__ == "__main__":
    build()
