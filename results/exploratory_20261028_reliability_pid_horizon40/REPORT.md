# Exploratory reliability-aware PID

> This algorithm was designed after inspecting the locked confirmatory run. The results below are exploratory and require a new external/temporal cohort for confirmation.

The controller tracks a validation-trained reliability target on dense 1--40 API-event prefixes. All thresholds and gains are selected without outer-test labels.

| Method | AUC | FPR | TPR | Event-AUC | Brier |
|---|---:|---:|---:|---:|---:|
| Average_50_50 | 0.9891 | 9.89% | 96.23% | 0.9863 | 0.0388 |
| Dynamic_only | 0.9815 | 14.64% | 95.62% | 0.9615 | 0.0474 |
| Fixed_weight | 0.9871 | 7.62% | 94.85% | 0.9803 | 0.0437 |
| Logistic_stack | 0.9872 | 6.39% | 95.25% | 0.9845 | 0.0379 |
| Max_score | 0.9865 | 11.93% | 96.76% | 0.9815 | 0.0502 |
| Reliability_P | 0.9866 | 10.00% | 95.73% | 0.9838 | 0.0413 |
| Reliability_PI | 0.9866 | 9.82% | 95.73% | 0.9837 | 0.0413 |
| Reliability_PID | 0.9866 | 9.82% | 95.73% | 0.9837 | 0.0413 |
| Reliability_full_PID | 0.9864 | 10.00% | 95.73% | 0.9837 | 0.0413 |
| Reliability_target | 0.9864 | 10.00% | 95.73% | 0.9837 | 0.0413 |
| Static_only | 0.9740 | 15.15% | 95.40% | 0.9740 | 0.0545 |

See `paired_bootstrap.json` for paired uncertainty intervals and `channel_reliability_diagnostics.json` for whether the better channel changes over time.
