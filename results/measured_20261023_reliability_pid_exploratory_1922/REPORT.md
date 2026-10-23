# Exploratory reliability-aware PID

> This algorithm was designed after inspecting the locked confirmatory run. The results below are exploratory and require a new external/temporal cohort for confirmation.

The controller tracks a validation-trained reliability target on dense 1--20 API-event prefixes. All thresholds and gains are selected without outer-test labels.

| Method | AUC | FPR | TPR | Event-AUC | Brier |
|---|---:|---:|---:|---:|---:|
| Average_50_50 | 0.9837 | 14.69% | 96.77% | 0.9799 | 0.0450 |
| Dynamic_only | 0.9720 | 20.38% | 95.45% | 0.9453 | 0.0589 |
| Fixed_weight | 0.9822 | 12.44% | 96.06% | 0.9736 | 0.0487 |
| Logistic_stack | 0.9826 | 14.90% | 96.56% | 0.9798 | 0.0454 |
| Max_score | 0.9784 | 16.62% | 96.77% | 0.9726 | 0.0604 |
| Reliability_P | 0.9826 | 11.15% | 95.96% | 0.9787 | 0.0456 |
| Reliability_PI | 0.9825 | 11.47% | 95.96% | 0.9786 | 0.0456 |
| Reliability_PID | 0.9825 | 11.47% | 95.96% | 0.9785 | 0.0455 |
| Reliability_full_PID | 0.9825 | 11.58% | 95.96% | 0.9785 | 0.0455 |
| Reliability_target | 0.9815 | 11.26% | 95.96% | 0.9775 | 0.0458 |
| Static_only | 0.9702 | 23.58% | 96.56% | 0.9702 | 0.0567 |

See `paired_bootstrap.json` for paired uncertainty intervals and `channel_reliability_diagnostics.json` for whether the better channel changes over time.
