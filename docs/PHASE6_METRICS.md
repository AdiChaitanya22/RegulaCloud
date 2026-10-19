# Phase 6: Detection and RL Metrics

## 1. Classification & Confusion Matrix
For categorical compliance detection, RegulaCloud evaluates its effectiveness using standard binary classification metrics.
- **True Positive (TP)**: System correctly flags an insecure configuration (FAIL).
- **True Negative (TN)**: System correctly accepts a secure configuration (PASS).
- **False Positive (FP)**: System incorrectly flags a secure configuration.
- **False Negative (FN)**: System incorrectly accepts an insecure configuration.

**Formulas**:
- **Precision**: `TP / (TP + FP)`
- **Recall**: `TP / (TP + FN)`
- **Accuracy**: `(TP + TN) / Total Categorized`
- **F1 Score**: `2 * (Precision * Recall) / (Precision + Recall)`

*Note on Unknowns*: `UNKNOWN`, `UNSUPPORTED`, and `NOT_APPLICABLE` outcomes are strictly omitted from the True/False Accuracy denominator to prevent artificial inflation of performance. They are reported separately as `unknown_rate`, `unsupported_rate`, and `coverage_rate`.

## 2. Timing & Performance Statistics
System benchmarks require robust statistical filtering to mitigate single-run anomalies (CPU scheduling, IO blocks).
- **Metric points**: Mean, Median, Standard Deviation, p95 (95th percentile).
- **Process**: Mandatory warm-up runs (uncached/cached) followed by 10+ iterations.

## 3. RL Strategy Metrics
Evaluating Q-Learning against deterministic baselines relies on state traversal efficiency.
- **Remediation Success Rate**: % of states resulting in a 100% PASS compliance score.
- **Cumulative Remediation Cost**: Sum of defined integer penalties associated with each invoked action.
- **Mean Steps to Terminal**: Average number of state transitions required.
- **Actions Attempted vs. Skipped**: Distinguishing between automatic mutation and manual guidance.
