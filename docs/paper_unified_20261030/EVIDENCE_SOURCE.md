# Evidence source and limits

## Primary source

- File copied into this package: `EVIDENCE_REPORT_20261030.md`
- Source filename: `PAPER_EVIDENCE_AND_READINESS_REPORT_20261021.md`
- Report update date: 30 October 2026
- Reported branch: `feat/reproducible-thesis-experiments`
- Reported commit: `8bfa06b65b93`
- EMBER dataset SHA-256:
  `69f0ae680846edd95458d1e7aaabe36f8866f4f22a6d11488b126ed026b28963`
- EMBER manifest SHA-256:
  `a2ca16402653e6cc51fdd7a4857d007faf86807b044d78654f180409c73565bb`
- MalBehavD-V1 manifest SHA-256:
  `9540b88b0da2463f63b4e983f5ecc277e3845b7badebbb79695e35f2c3b1a669`

## Evidence hierarchy applied

- Confirmatory verification: EMBER active learning and TreeSHAP fidelity.
- Original confirmatory: MalBehavD-V1 channel complementarity and component
  ablation.
- Measured development: fusion-only Adaptive P/PI/PID comparison on the same
  1,922-sample cohort.
- Exploratory: horizon-40 Robust PID v2 and controlled stress tests.
- Feasibility only: 20-sample report download and eight usable timestamped
  sequences.

## Checked in this writing environment

- The full supplied report, including Section 14, was read.
- Every central numerical claim was mapped to a named artifact family.
- Tables and figures were checked against report values.
- LaTeX syntax, citations, references, and a 27-page two-column surrogate build
  were validated.
- The manuscript explicitly separates the two benchmarks and evidence tiers.

## Not checked here

- Commit `8bfa06b65b93` and the named result directories are absent from the
  remote checkout available to this environment.
- Models were not retrained and predictions were not independently replayed.
- Fold-level vectors were unavailable, so aggregate figures omit uncertainty
  bars.
- Bibliography metadata has not been verified against current publisher pages.

These limits remain visible in the paper's protocol and threats-to-validity
sections until the exact artifacts are synchronized and replayed.
