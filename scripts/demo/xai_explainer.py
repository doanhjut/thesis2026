"""Shim tuong thich. Ban canonical: dashboard/xai_explainer.py"""
import importlib.util
import sys
from pathlib import Path

_CANONICAL = None
for _parent in Path(__file__).resolve().parents:
    _candidate = _parent / "dashboard" / "xai_explainer.py"
    if _candidate.is_file():
        _CANONICAL = _candidate
        break

if _CANONICAL is None:
    raise ImportError("Khong tim thay dashboard/xai_explainer.py")

_spec = importlib.util.spec_from_file_location("xai_explainer_canonical", _CANONICAL)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Khong nap duoc {_CANONICAL}")
_module = importlib.util.module_from_spec(_spec)
sys.modules["xai_explainer_canonical"] = _module
_spec.loader.exec_module(_module)

for _name in dir(_module):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_module, _name)

if __name__ == "__main__":
    import runpy

    runpy.run_path(str(_CANONICAL), run_name="__main__")
