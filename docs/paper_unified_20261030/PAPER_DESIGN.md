# Manuscript design before prose

## Proposed title

**Auditable Adaptive Learning for Windows Malware Detection: Reliability-Aware Fusion, Explanation-Guided Sampling, and TreeSHAP Validation**

The title retains all three contributions while avoiding ransomware-specific,
zero-day, production-readiness, and end-to-end claims that the available labels
and component-wise experiments do not support.

## Abstract locked for drafting

Windows malware detection is a problem of allocating incomplete evidence under
two constraints: behavioral evidence arrives sequentially, and expert labels
are scarce. Static scores provide early coverage, whereas dynamic API prefixes
offer complementary observations after execution; the resulting models also
require explanations that can be audited before they guide data acquisition.
We formulate these requirements as an auditable adaptive-learning framework
with three component-level research questions. First, a control-inspired fusion
rule maps disagreement between static and dynamic scores to an adaptive weight,
and ablates proportional, integral, and derivative terms. Second, a pool-based
policy combines predictive uncertainty with TreeSHAP directional entropy and
attribution variance. Third, controlled deletion and rank-stability tests assess
whether TreeSHAP rankings track fitted-model behavior. The components are
evaluated on complementary, non-integrated benchmarks: 1,922 paired MalBehavD-V1
samples for fusion and an identity-audited 2,000-sample, 2,381-feature EMBER
subset for active learning and fidelity. On the fusion development cohort,
Adaptive P reduced false-positive rate from 12.45% to 11.16% relative to fixed
weighting (difference -1.28 percentage points; 95% CI [-2.47, -0.11]) and
improved Brier score, while integral and derivative terms supplied no consistent
incremental benefit. Across five outer folds and five seeds, uncertainty plus
directional entropy achieved the best ROC/AP learning-curve areas; the full
three-signal policy reached a predeclared validation target with 492 labels, 92
(15.8%) fewer than random acquisition. Replacing the top 50 TreeSHAP-ranked
features by training means reduced AUC by 0.306729, versus 0.000979 for
equal-budget random replacement, with moderate ranking stability. These results
support component-wise evidence allocation and model auditing for generic
Windows malware; they do not constitute ransomware-specific, external, or
end-to-end validation.

## Unified scientific problem

The manuscript is organized around **auditable evidence allocation under
partial observability**:

1. **Decision:** a static score is available early, while behavioral evidence
   arrives as ordered API-event prefixes. A control-inspired update uses current
   detector disagreement to adapt their relative weight.
2. **Adaptation:** the detector cannot obtain labels for the complete incoming
   pool. Predictive ambiguity and explanation structure prioritize candidate
   labels under a fixed budget.
3. **Audit:** because TreeSHAP affects acquisition and analyst-facing evidence,
   its fitted-model reliance and stability are tested rather than assumed.

The formulation is unified; the empirical estimands remain separate. EMBER
evaluates adaptation and audit, whereas MalBehavD-V1 evaluates decision fusion.
No result is presented as a complete pipeline evaluation.

## Research questions

- **RQ1:** On paired event-indexed static and dynamic evidence, how do adaptive
  P/PI/PID fusion rules compare with average, max-risk, fixed weighting, and
  learned logistic stacking in discrimination, calibration, and operating-point
  trade-offs?
- **RQ2:** Under matched training-label budgets, do directional entropy and SHAP
  variance add useful acquisition information beyond random and
  uncertainty-only selection?
- **RQ3:** Under training-derived mean and median replacement, do
  top-|TreeSHAP| coordinates affect fitted-model ranking more than equal-budget
  random coordinates, and how stable are the rankings across seeds and folds?

## Detailed outline and target length

| Section | Purpose | Target two-column pages |
|---|---|---:|
| Abstract and Introduction | Problem, unified flow, RQs, scoped contributions | 2.0 |
| Related Work | Static/dynamic detection, fusion/control, AL, XAI validation | 2.5--3.0 |
| Problem Formulation | Partial observability, label budget, audit objects, scope | 1.5--2.0 |
| Methodology | P/PI/PID fusion, U/H/V acquisition, deletion/stability | 4.0--5.0 |
| Experimental Protocol | Two datasets, provenance, splits, metrics, evidence tiers | 3.0--4.0 |
| Results | RQ1--RQ3 plus clearly labeled exploratory evidence | 4.5--5.5 |
| Discussion | Evidence-driven PID simplification, integration boundary, use cases | 2.0--2.5 |
| Threats to Validity | Construct, internal, statistical, external, reproducibility | 1.5--2.0 |
| Conclusion | Findings and evidence gates | 0.5--1.0 |
| Appendices | Configuration, interpretation, artifact and claim maps | 3.0--5.0 |

Expected complete length: approximately 22--27 two-column pages, depending on
the final IEEE template, bibliography flow, and figure placement.

## Required main-paper tables and figures

1. **Fig. 1:** Unified decision--adaptation--audit architecture, with the two
   benchmark boundaries marked explicitly.
2. **Table I:** Dataset provenance, label semantics, observation unit, and
   evaluation role.
3. **Table II:** Fusion comparison on 1,922 paired samples.
4. **Fig. 2:** Fusion discrimination, FPR, and Brier summaries.
5. **Table III:** Paired fusion effects and confidence intervals.
6. **Table IV/Fig. 3:** AL AULC, label-to-target, timing, and summary plot.
7. **Table V:** Low-FPR AL results.
8. **Table VI/Fig. 4:** TreeSHAP deletion under mean/median baselines.
9. **Table VII/Fig. 5:** Within-fold and across-fold rank stability.
10. **Table VIII:** Confirmatory, development, exploratory, and feasibility
    evidence status.

## Writing constraints

- Use “generic Windows malware,” never ransomware or zero-day as a demonstrated
  result.
- Call the study component-wise and state that the two benchmarks are not an
  end-to-end experiment.
- Describe PID as control-inspired. Detector disagreement is not a physical
  tracking error, and no closed-loop stability guarantee is claimed.
- Treat Adaptive P versus Fixed as development evidence on a cohort observed
  during method development.
- Report the negative I/D result prominently.
- Put robust PID v2, controlled stress, and timestamp extraction only in an
  exploratory subsection or appendix.
- Do not construct an Overall Fidelity Score or claim executable-valid/causal
  interventions.
- Do not convert labels saved into analyst hours.
