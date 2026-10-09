"""Nap module canonical trong src/ tu mot file shim o thu muc khac."""

from __future__ import annotations

import sys
from pathlib import Path


def repo_root(marker: str) -> Path:
    """Tim goc repo bang cach di len den khi thay src/<marker>."""
    for parent in Path(__file__).resolve().parents:
        if (parent / "src" / marker).is_file():
            return parent
    raise ImportError(f"Khong tim thay src/{marker}")


def export_module(canonical_name: str, target_globals: dict) -> None:
    """Import src/<canonical_name> va do ten public vao shim."""
    src = repo_root(canonical_name) / "src"
    src_str = str(src)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)
    module_name = Path(canonical_name).stem
    module = __import__(module_name)
    for name in dir(module):
        if not name.startswith("_"):
            target_globals[name] = getattr(module, name)


def run_as_main(canonical_name: str) -> None:
    import runpy

    canonical = repo_root(canonical_name) / "src" / canonical_name
    runpy.run_path(str(canonical), run_name="__main__")
