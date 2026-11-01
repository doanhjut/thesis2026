#!/usr/bin/env python3
"""Build a generic two-column preview when IEEEtran.cls is unavailable."""

from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / ".build"
BUILD.mkdir(exist_ok=True)

source = (ROOT / "main.tex").read_text()
source = source.replace(
    r"\documentclass[journal]{IEEEtran}",
    r"\documentclass[10pt,twocolumn]{article}",
)
source = source.replace(
    r"\usepackage[hidelinks]{hyperref}",
    r"\usepackage[hidelinks]{hyperref}"
    "\n"
    r"\newenvironment{IEEEkeywords}{\par\small\noindent\textbf{Index Terms---}}{\par\normalsize}",
)
source = source.replace(r"\appendices", r"\appendix")
source = source.replace(r"\bibliographystyle{IEEEtran}", r"\bibliographystyle{plain}")
(BUILD / "preview.tex").write_text(source)

subprocess.run(
    [
        "latexmk",
        "-pdf",
        "-interaction=nonstopmode",
        "-halt-on-error",
        f"-outdir={BUILD}",
        str(BUILD / "preview.tex"),
    ],
    cwd=ROOT,
    check=True,
)

shutil.copy2(BUILD / "preview.pdf", ROOT / "PREVIEW_TWO_COLUMN_NOT_IEEE.pdf")
