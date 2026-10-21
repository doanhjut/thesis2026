# Confirmatory AL/Fidelity paper revision

This directory contains the focused journal manuscript prepared from
`PAPER_EVIDENCE_AND_READINESS_REPORT_20261021.md`.

## Scope

The paper studies explanation-guided active learning and controlled TreeSHAP
validation for static Windows PE malware detection. It does not claim ransomware
detection, end-to-end multi-stage validation, PID superiority, sleep-evasion
resistance, or deployment latency.

The earlier multi-stage manuscript remains under `docs/paper/` and is not
overwritten.

## Files

- `main.tex`: IEEEtran manuscript entry point.
- `sections/`: complete paper and reproducibility appendices.
- `figures/`: aggregate plots generated from values locked in the readiness
  report.
- `references.bib`: bibliography used by this revision.
- `PREVIEW_TWO_COLUMN_NOT_IEEE.pdf`: readable 19-page surrogate build used for
  syntax and layout review; it is not the final IEEEtran rendering.
- `CLAIM_EVIDENCE_MAP.csv`: allowed, bounded, and rejected central claims.
- `PAPER_WRITING_PLAN.md`: writing scope and submission gates.
- `EVIDENCE_SOURCE.md`: evidence provenance and pre-submission replay warning.

## Evidence status

The readiness report identifies confirmatory source commit
`fed4322f58f5bb55ec47833e857370d076592a32` and the artifact directory
`results/confirmatory_20261019_ember_identity/`. They are not present in the
current cloud checkout. Numerical values in this revision are therefore
attributed to that report. Before submission, synchronize the exact commit and
artifacts, verify the dataset/manifest hashes, rerun the verifier, and regenerate
tables and figures from fold-level files.

## Build

Compile in an IEEEtran-enabled LaTeX environment:

```sh
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

Author order, institutional emails, ORCID identifiers, corresponding-author
designation, data rights, bibliography metadata, and target-journal instructions
must be confirmed before submission.

