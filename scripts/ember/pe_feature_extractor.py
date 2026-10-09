"""Shim tuong thich. Ban canonical: src/feature_extraction.py"""
import sys
from pathlib import Path

for _parent in Path(__file__).resolve().parents:
    if (_parent / "src" / "_compat.py").is_file():
        sys.path.insert(0, str(_parent / "src"))
        break
else:
    raise ImportError("Khong tim thay src/_compat.py")

from _compat import export_module, run_as_main

export_module("feature_extraction.py", globals())

if __name__ == "__main__":
    run_as_main("feature_extraction.py")
