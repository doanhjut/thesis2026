# Unified auditable malware-learning paper

This directory contains the new full journal manuscript written from the
30 October 2026 evidence report. Earlier manuscripts under `docs/paper/` and
`docs/paper_confirmatory_20261021/` remain unchanged.

## Scientific scope

The paper unifies three contributions as **auditable evidence allocation under
partial observability**:

1. reliability-aware static--dynamic fusion on MalBehavD-V1;
2. explanation-guided active learning on an identity-audited EMBER subset;
3. quantitative TreeSHAP deletion and rank-stability validation on EMBER.

The evaluations are component-wise. The manuscript does not claim one
end-to-end experiment, ransomware-specific detection, full-PID superiority,
sleep-evasion resistance, causal explanations, or production readiness.

## Main files

- `main.tex`: IEEEtran manuscript entry point.
- `sections/`: complete paper and reproducibility appendices.
- `references.bib`: bibliography.
- `PAPER_DESIGN.md`: title, locked abstract, unified problem, detailed outline,
  tables/figures, and writing constraints created before prose.
- `CLAIM_EVIDENCE_MAP.csv`: machine-readable claim-to-artifact map.
- `EVIDENCE_REPORT_20261030.md`: immutable copy of the user-supplied source of
  truth.
- `figures/`: PDF and PNG summary figures.
- `scripts/generate_figures.py`: reproduces aggregate figures from locked report
  values.
- `PREVIEW_TWO_COLUMN_NOT_IEEE.pdf`: 27-page syntax/layout preview compiled with
  the generic two-column `article` class because IEEEtran is unavailable in the
  current environment. It is not the submission rendering.

## Evidence status

The source report identifies branch `feat/reproducible-thesis-experiments` and
commit `8bfa06b65b93`. The remote branch visible during this writing pass ends at
an older commit, so the named result directories could not be replayed here.
Numerical values are transcribed from the locked report and tracked to its
artifact map. Before submission, synchronize the named commit and artifacts,
verify hashes, replay the experiments, and regenerate figures from fold-level
records.

## Build

In an IEEEtran-enabled LaTeX environment:

```sh
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

To regenerate the generic two-column preview:

```sh
python3 scripts/generate_figures.py
python3 scripts/build_preview.py
```

Before submission, confirm author order, corresponding author, institutional
emails, ORCID identifiers, funding/conflicts, data rights, bibliography metadata,
and the current target-journal template.
