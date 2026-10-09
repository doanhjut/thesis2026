#!/usr/bin/env python3
"""
================================================================================
setup_defense_kit.py  -  Dong goi "Defense Kit" mang di bao ve luan van
================================================================================
Muc dich (chay MOT LAN):
    Tao thu muc doc lap 'Live_Demo_Defense/' tren Desktop (neu khong co Desktop
    thi tao ngay tai thu muc du an), sau do COPY tat ca file can thiet vao do
    de co mot bo demo sach se, di dong, chay duoc ngay tren may bao ve.

Cac thanh phan duoc dong goi:
    - real_mini_dataset.csv          (du lieu mini 2000 mau)
    - ransomware_lgbm_1M_final.txt   (mo hinh LightGBM da huan luyen)
    - live_defense_demo.py           (script demo truc tiep)
    - xai_dashboard.py               (giao dien Streamlit - ban moi nhat)
    - raw_logs/                      (toan bo log tho)
  (+ file bo tro neu co: generate_thesis_charts.py, extract_real_mini_data.py, results/)

Chay:   python setup_defense_kit.py
================================================================================
"""

import shutil
import sys
from pathlib import Path
from datetime import datetime

# ============================================================================
# CAU HINH
# ============================================================================
REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_DIR = Path(__file__).resolve().parent
KIT_NAME = "Live_Demo_Defense"

# File BAT BUOC: (duong_dan_nguon, ten_dich)
REQUIRED_ITEMS = [
    (REPO_ROOT / "data" / "processed" / "real_mini_dataset.csv", "real_mini_dataset.csv"),
    (REPO_ROOT / "models" / "ransomware_lgbm_1M_final.txt", "ransomware_lgbm_1M_final.txt"),
    (BASE_DIR / "live_defense_demo.py", "live_defense_demo.py"),
    (REPO_ROOT / "dashboard" / "xai_dashboard.py", "xai_dashboard.py"),
]

# Thu muc BAT BUOC copy (nguon, ten_dich)
REQUIRED_DIRS = [
    (REPO_ROOT / "data" / "dynamic_logs", "raw_logs"),
]

# File / thu muc BO TRO (copy neu ton tai - khong bao loi neu thieu)
OPTIONAL_ITEMS = [
    (BASE_DIR / "generate_thesis_charts.py", "generate_thesis_charts.py"),
    (BASE_DIR / "extract_real_mini_data.py", "extract_real_mini_data.py"),
]
OPTIONAL_DIRS = [
    (REPO_ROOT / "results", "results"),
]


def human_size(num_bytes: int) -> str:
    """Chuyen so byte thanh chuoi de doc (KB/MB/GB)."""
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def resolve_destination() -> Path:
    """
    Xac dinh thu muc dich: uu tien Desktop cua nguoi dung; neu khong co
    thi dung thu muc du an hien tai.
    """
    desktop = Path.home() / "Desktop"
    base = desktop if desktop.exists() and desktop.is_dir() else REPO_ROOT
    return base / KIT_NAME


def copy_file(src: Path, dest_dir: Path, dest_name: str, required: bool) -> bool:
    """Copy 1 file, xu ly loi gon gang. Tra ve True neu copy thanh cong."""
    tag = "REQUIRED" if required else "optional"
    if not src.exists():
        level = "ERROR" if required else "SKIP"
        print(f"  [{level}] ({tag}) Khong tim thay: {src.name}")
        return False
    try:
        target = dest_dir / dest_name
        shutil.copy2(src, target)
        print(f"  [OK]   {dest_name:<32} ({human_size(target.stat().st_size)})")
        return True
    except Exception as e:
        print(f"  [ERROR] Khong the copy {src.name}: {e}")
        return False


def copy_dir(src: Path, dest_dir: Path, dest_name: str, required: bool) -> bool:
    """Copy 1 thu muc (de quy), xu ly loi gon gang. Tra ve True neu OK."""
    tag = "REQUIRED" if required else "optional"
    if not src.exists() or not src.is_dir():
        level = "ERROR" if required else "SKIP"
        print(f"  [{level}] ({tag}) Khong tim thay thu muc: {src.name}/")
        return False
    try:
        target = dest_dir / dest_name
        shutil.copytree(src, target, dirs_exist_ok=True)
        n_files = sum(1 for _ in target.rglob("*") if _.is_file())
        print(f"  [OK]   {dest_name + '/':<32} ({n_files} files)")
        return True
    except Exception as e:
        print(f"  [ERROR] Khong the copy thu muc {src.name}/: {e}")
        return False


def write_readme(dest_dir: Path) -> None:
    """Tao file README huong dan su dung ngay trong kit."""
    readme = dest_dir / "README_DEFENSE.txt"
    content = f"""LIVE DEMO DEFENSE KIT
=====================
Dong goi luc: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

NOI DUNG:
  - real_mini_dataset.csv        : Du lieu mini 2000 mau (1500 benign + 500 ransomware)
  - ransomware_lgbm_1M_final.txt : Mo hinh LightGBM da huan luyen (thuc te)
  - live_defense_demo.py         : Script demo truc tiep (terminal SOC + PID + SHAP)
  - xai_dashboard.py             : Giao dien Streamlit (3 tab)
  - raw_logs/                    : Log tho (PID trace, SHAP values, Active Learning)
  - generate_thesis_charts.py    : (Neu co) Ve bieu do 300 DPI tu raw_logs/
  - results/                     : (Neu co) Cac bieu do da xuat

CACH CHAY:
  1) Demo terminal truc tiep:
        python live_defense_demo.py

  2) Giao dien web (dashboard):
        streamlit run xai_dashboard.py

  3) Ve lai bieu do luan van (neu can):
        python generate_thesis_charts.py

YEU CAU THU VIEN:
  pip install pandas numpy scikit-learn lightgbm shap tqdm matplotlib seaborn streamlit plotly
"""
    try:
        readme.write_text(content, encoding="utf-8")
        print(f"  [OK]   README_DEFENSE.txt")
    except Exception as e:
        print(f"  [WARNING] Khong the tao README: {e}")


def main() -> None:
    print("=" * 72)
    print("  SETUP DEFENSE KIT - Dong goi thu muc demo doc lap")
    print("=" * 72)

    dest_dir = resolve_destination()
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"  [ERROR] Khong the tao thu muc dich {dest_dir}: {e}")
        sys.exit(1)

    print(f"\n  Destination: {dest_dir}\n")

    print("  --- Copying REQUIRED files ---")
    ok_req = all(copy_file(s, dest_dir, n, required=True) for s, n in REQUIRED_ITEMS)
    ok_req_dir = all(copy_dir(s, dest_dir, n, required=True) for s, n in REQUIRED_DIRS)

    print("\n  --- Copying OPTIONAL files (neu co) ---")
    for s, n in OPTIONAL_ITEMS:
        copy_file(s, dest_dir, n, required=False)
    for s, n in OPTIONAL_DIRS:
        copy_dir(s, dest_dir, n, required=False)

    print("\n  --- Writing README ---")
    write_readme(dest_dir)

    # Tong ket
    total_files = sum(1 for _ in dest_dir.rglob("*") if _.is_file())
    print("\n" + "=" * 72)
    if ok_req and ok_req_dir:
        print(f"  [SUCCESS] Defense Kit san sang tai:\n            {dest_dir}")
    else:
        print(f"  [PARTIAL] Kit tao xong nhung THIEU mot so file BAT BUOC (xem [ERROR] tren).")
    print(f"  Tong so file trong kit: {total_files}")
    print("=" * 72)


if __name__ == "__main__":
    main()
