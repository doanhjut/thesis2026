
from __future__ import annotations

import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle


# ============================================================
# CẤU HÌNH CHUNG
# ============================================================

OUTPUT_DIR = Path("thesis_figures")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DPI = 300

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.unicode_minus": False,
    }
)


# ============================================================
# HÀM HỖ TRỢ
# ============================================================

def wrap_text(text: str, width: int = 28) -> str:
    """
    Tự động xuống dòng từng đoạn.
    Giữ nguyên các dòng chủ động xuống dòng bằng ký tự \\n.
    """
    lines: list[str] = []

    for paragraph in text.split("\n"):
        paragraph = paragraph.strip()

        if not paragraph:
            lines.append("")
            continue

        wrapped = textwrap.wrap(
            paragraph,
            width=width,
            break_long_words=False,
            break_on_hyphens=False,
        )

        lines.extend(wrapped if wrapped else [paragraph])

    return "\n".join(lines)


def draw_box(
    ax,
    x: float,
    y: float,
    width: float,
    height: float,
    text: str,
    *,
    facecolor: str = "#FFFFFF",
    edgecolor: str = "#222222",
    fontsize: float = 10,
    linewidth: float = 1.2,
    rounded: bool = False,
    wrap_width: int = 28,
    fontweight: str = "normal",
    zorder: int = 3,
):
    """
    Vẽ một hộp có chữ căn giữa.

    x, y là tọa độ góc trái dưới.
    """

    if rounded:
        patch = FancyBboxPatch(
            (x, y),
            width,
            height,
            boxstyle="round,pad=0.25,rounding_size=1.2",
            linewidth=linewidth,
            edgecolor=edgecolor,
            facecolor=facecolor,
            zorder=zorder,
        )
    else:
        patch = Rectangle(
            (x, y),
            width,
            height,
            linewidth=linewidth,
            edgecolor=edgecolor,
            facecolor=facecolor,
            zorder=zorder,
        )

    ax.add_patch(patch)

    ax.text(
        x + width / 2,
        y + height / 2,
        wrap_text(text, wrap_width),
        ha="center",
        va="center",
        fontsize=fontsize,
        fontweight=fontweight,
        linespacing=1.25,
        zorder=zorder + 1,
    )

    return patch


def draw_arrow(
    ax,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    connectionstyle: str = "arc3",
    linewidth: float = 1.5,
):
    """
    Vẽ mũi tên.
    """

    ax.annotate(
        "",
        xy=end,
        xytext=start,
        arrowprops={
            "arrowstyle": "-|>",
            "linewidth": linewidth,
            "color": "#333333",
            "shrinkA": 2,
            "shrinkB": 2,
            "mutation_scale": 14,
            "connectionstyle": connectionstyle,
        },
        zorder=2,
    )


def save_figure(fig, filename: str):
    """
    Xuất đồng thời PNG, PDF và SVG.
    """

    for extension in ("png", "pdf", "svg"):
        path = OUTPUT_DIR / f"{filename}.{extension}"

        kwargs = {
            "bbox_inches": "tight",
            "pad_inches": 0.15,
        }

        if extension == "png":
            kwargs["dpi"] = DPI

        fig.savefig(path, **kwargs)

    plt.close(fig)


# ============================================================
# HÌNH 1
# CẤU TRÚC WINDOWS PE
# ============================================================

def draw_pe_structure():
    fig, ax = plt.subplots(
        figsize=(10, 11),
        constrained_layout=True,
    )

    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # --------------------------------------------------------
    # Tiêu đề
    # --------------------------------------------------------

    ax.text(
        50,
        97,
        "CẤU TRÚC CƠ BẢN CỦA TỆP THỰC THI WINDOWS PE",
        ha="center",
        va="top",
        fontsize=15,
        fontweight="bold",
    )

    # --------------------------------------------------------
    # Khối PE chính
    # --------------------------------------------------------

    pe_x = 8
    pe_width = 48
    top_y = 91

    blocks = [
        (
            "DOS Header",
            "Magic number MZ; e_lfanew trỏ tới PE Header",
            8,
            "#D9EAF7",
        ),
        (
            "DOS Stub",
            "Mã tương thích MS-DOS",
            6,
            "#EAF3F8",
        ),
        (
            "PE Signature",
            r"Chữ ký PE\0\0",
            5,
            "#DDF1E3",
        ),
        (
            "COFF File Header",
            "Machine, NumberOfSections, TimeDateStamp",
            8,
            "#E7F3E9",
        ),
        (
            "Optional Header",
            "AddressOfEntryPoint, ImageBase, SectionAlignment và Data Directories",
            12,
            "#FFF2CC",
        ),
        (
            "Section Table",
            "Mô tả tên, kích thước, RVA và thuộc tính của các section",
            8,
            "#FCE5CD",
        ),
        (
            ".text",
            "Mã lệnh thực thi",
            6,
            "#F4CCCC",
        ),
        (
            ".rdata",
            "Dữ liệu chỉ đọc và thông tin import",
            6,
            "#FCE8E6",
        ),
        (
            ".data",
            "Dữ liệu đã khởi tạo",
            6,
            "#EADCF8",
        ),
        (
            ".rsrc",
            "Tài nguyên: biểu tượng, chuỗi và hộp thoại",
            7,
            "#E5D5F1",
        ),
        (
            ".reloc",
            "Thông tin tái định vị",
            6,
            "#DDD9F3",
        ),
    ]

    current_y = top_y

    block_centers: dict[str, tuple[float, float]] = {}

    for title, description, height, color in blocks:
        current_y -= height

        text = f"{title}\n{description}"

        draw_box(
            ax,
            pe_x,
            current_y,
            pe_width,
            height,
            text,
            facecolor=color,
            fontsize=9.2,
            wrap_width=45,
            fontweight="normal",
        )

        block_centers[title] = (
            pe_x + pe_width,
            current_y + height / 2,
        )

    total_height = top_y - current_y

    # Viền ngoài
    ax.add_patch(
        Rectangle(
            (pe_x, current_y),
            pe_width,
            total_height,
            fill=False,
            linewidth=2.0,
            edgecolor="#111111",
            zorder=4,
        )
    )

    # --------------------------------------------------------
    # Offset
    # --------------------------------------------------------

    ax.annotate(
        "",
        xy=(61, current_y),
        xytext=(61, top_y),
        arrowprops={
            "arrowstyle": "-|>",
            "linewidth": 1.5,
            "color": "#333333",
        },
    )

    ax.text(
        64,
        (top_y + current_y) / 2,
        "Offset tăng dần\ntrong tệp",
        ha="center",
        va="center",
        rotation=90,
        fontsize=10,
    )

    # --------------------------------------------------------
    # Ghi chú bên phải
    # --------------------------------------------------------

    note_x = 70
    note_width = 27

    notes = [
        (
            78,
            11,
            "DOS Header",
            "Trường e_lfanew xác định vị trí bắt đầu của PE Header.",
            "#F8FBFD",
        ),
        (
            57,
            14,
            "Optional Header",
            "Chứa các tham số quan trọng phục vụ quá trình nạp ảnh PE vào bộ nhớ.",
            "#FFFDF5",
        ),
        (
            27,
            19,
            ".data",
            "Các section là nguồn đặc trưng quan trọng trong phân tích mã độc, "
            "bao gồm entropy, kích thước và thuộc tính truy cập.",
            "#FBF8FD",
        ),
    ]

    for note_y, note_height, target, note_text, color in notes:
        draw_box(
            ax,
            note_x,
            note_y,
            note_width,
            note_height,
            note_text,
            facecolor=color,
            fontsize=9,
            rounded=True,
            wrap_width=30,
        )

        target_x, target_y = block_centers[target]

        draw_arrow(
            ax,
            (target_x + 0.5, target_y),
            (note_x - 0.5, note_y + note_height / 2),
        )

    save_figure(fig, "pe_structure")


# ============================================================
# HÌNH 2
# RANSOMWARE KILL CHAIN
# ============================================================

def draw_ransomware_kill_chain():
    fig, ax = plt.subplots(
        figsize=(14, 8),
        constrained_layout=True,
    )

    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    ax.text(
        50,
        96,
        "VÒNG ĐỜI TẤN CÔNG ĐIỂN HÌNH CỦA MÃ ĐỘC TỐNG TIỀN",
        ha="center",
        va="top",
        fontsize=15,
        fontweight="bold",
    )

    # --------------------------------------------------------
    # Bố cục snake-flow 2 hàng
    #
    # 1 -> 2 -> 3 -> 4
    #                |
    # 7 <- 6 <- 5 <--
    # --------------------------------------------------------

    box_width = 20
    box_height = 17

    steps = [
        {
            "number": "1",
            "title": "INITIAL ACCESS",
            "detail": "Phishing, khai thác lỗ hổng hoặc truy cập RDP",
            "x": 2,
            "y": 62,
            "color": "#D9EAF7",
        },
        {
            "number": "2",
            "title": "EXECUTION",
            "detail": "Tải và thực thi payload hoặc dropper",
            "x": 27,
            "y": 62,
            "color": "#DDF1E3",
        },
        {
            "number": "3",
            "title": "PERSISTENCE & EVASION",
            "detail": "Duy trì hiện diện, làm rối mã và vô hiệu hóa phòng vệ",
            "x": 52,
            "y": 62,
            "color": "#FFF2CC",
        },
        {
            "number": "4",
            "title": "DISCOVERY & PRIVILEGE",
            "detail": "Khảo sát hệ thống và nâng cao đặc quyền",
            "x": 77,
            "y": 62,
            "color": "#FCE5CD",
        },
        {
            "number": "5",
            "title": "LATERAL MOVEMENT & C2",
            "detail": "Lan truyền nội bộ và liên lạc máy chủ điều khiển",
            "x": 77,
            "y": 29,
            "color": "#F4CCCC",
        },
        {
            "number": "6",
            "title": "DATA PREPARATION",
            "detail": "Thu thập dữ liệu, chọn tệp và xóa bản sao lưu",
            "x": 52,
            "y": 29,
            "color": "#EADCF8",
        },
        {
            "number": "7",
            "title": "ENCRYPTION & EXTORTION",
            "detail": "Mã hóa dữ liệu và phát thông báo đòi tiền chuộc",
            "x": 27,
            "y": 29,
            "color": "#E5D5F1",
        },
    ]

    for step in steps:
        text = (
            f"{step['number']}. {step['title']}\n\n"
            f"{step['detail']}"
        )

        draw_box(
            ax,
            step["x"],
            step["y"],
            box_width,
            box_height,
            text,
            facecolor=step["color"],
            fontsize=9.2,
            rounded=True,
            wrap_width=27,
        )

    # --------------------------------------------------------
    # Mũi tên hàng trên
    # --------------------------------------------------------

    draw_arrow(ax, (22, 70.5), (27, 70.5))
    draw_arrow(ax, (47, 70.5), (52, 70.5))
    draw_arrow(ax, (72, 70.5), (77, 70.5))

    # --------------------------------------------------------
    # 4 -> 5
    # --------------------------------------------------------

    draw_arrow(
        ax,
        (87, 62),
        (87, 46),
    )

    # --------------------------------------------------------
    # Hàng dưới đi từ phải sang trái
    # --------------------------------------------------------

    draw_arrow(ax, (77, 37.5), (72, 37.5))
    draw_arrow(ax, (52, 37.5), (47, 37.5))

    # --------------------------------------------------------
    # Phân chia ba pha
    # --------------------------------------------------------

    phase_y = 12

    phase_data = [
        (
            3,
            27,
            "PHA XÂM NHẬP",
            "Thiết lập điểm vào và thực thi mã độc",
        ),
        (
            37,
            30,
            "PHA MỞ RỘNG",
            "Duy trì hiện diện, khám phá và lan truyền",
        ),
        (
            72,
            25,
            "PHA TÁC ĐỘNG",
            "Chuẩn bị dữ liệu, mã hóa và tống tiền",
        ),
    ]

    for x, width, title, detail in phase_data:
        draw_box(
            ax,
            x,
            phase_y,
            width,
            9,
            f"{title}\n{detail}",
            facecolor="#FAFAFA",
            edgecolor="#777777",
            fontsize=8.5,
            rounded=True,
            wrap_width=38,
        )

    save_figure(fig, "ransomware_kill_chain")


# ============================================================
# MAIN
# ============================================================

def main():
    draw_pe_structure()
    draw_ransomware_kill_chain()

    print("Đã tạo hình thành công.")
    print(f"Thư mục đầu ra: {OUTPUT_DIR.resolve()}")
    print()
    print("Các file:")
    print("  - pe_structure.png")
    print("  - pe_structure.pdf")
    print("  - pe_structure.svg")
    print("  - ransomware_kill_chain.png")
    print("  - ransomware_kill_chain.pdf")
    print("  - ransomware_kill_chain.svg")


if __name__ == "__main__":
    main()

