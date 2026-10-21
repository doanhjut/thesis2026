# Confirmatory paper writing plan — 21 October 2026

## Scope

The manuscript focuses on explanation-guided active learning and controlled
TreeSHAP validation for static Windows PE malware detection. PID fusion is not a
headline contribution because the full cohort and integrated system evaluation
are incomplete. The earlier multi-stage manuscript remains unchanged under
`docs/paper/`.

## Evidence hierarchy

1. Main evidence: identity-audited 2,000-row EMBER subset, five outer folds,
   five active-learning seeds per fold, and 25 fidelity models.
2. Context only: 199-sample event-indexed static/dynamic fusion pilot.
3. Excluded: legacy root-level results, simulations, illustrative dashboard
   traces, and unverified ransomware-specific claims.

The numerical source for this revision is
`PAPER_EVIDENCE_AND_READINESS_REPORT_20261021.md`. The experiment commits named
in that report are not present in the current cloud checkout, so this revision
does not claim an independent rerun. Before submission, the named commits and
artifacts must be synchronized, hash-checked, and replayed.

## Research questions

1. Do TreeSHAP-derived mass-balance and dispersion signals improve learning-curve
   performance over random and uncertainty acquisition at equal training-label
   budgets?
2. How do acquisition variants trade ranking quality, labels to a predeclared
   validation target, low-FPR behavior, and computation?
3. Do top-absolute-SHAP coordinates affect fitted-model behavior more than
   equal-budget random coordinates under mean and median replacement, and how
   stable are the rankings across folds and model seeds?

## Submission gates

- Add uncertainty-plus-diversity and a calibrated committee baseline.
- Add weight/normalization sensitivity and batch-redundancy analysis.
- Add used-feature, magnitude-matched, and attribution-permutation deletion
  controls where artifacts permit.
- Synchronize and replay the confirmatory artifacts.
- Verify all bibliography metadata against publisher records.
- Confirm author metadata and journal template requirements.
- Prefer an external or temporal evaluation before targeting a venue with a
  strong generalization requirement.

## Writing order

1. Evidence and claim map.
2. Method and experimental protocol.
3. Results, discussion, and threats to validity.
4. Related work and novelty table.
5. Introduction, abstract, and conclusion.
6. Internal reviewer pass and release build.

