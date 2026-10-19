# Phase 6: Benchmark Design

## 1. Detection Benchmark Corpus
The evaluation corpus will contain symmetric pairs of Infrastructure as Code (Terraform) and Application Security (Java) fixtures for every active technical control.
- **Compliant Case**: Known secure configuration, expecting `PASS`.
- **Non-Compliant Case**: Known insecure configuration, expecting `FAIL`.
- **Edge Case**: Variable interpolation, module delegation, or dynamic references designed to stress the parser/engine.

## 2. Native vs. Synthetic Comparison
An experiment isolating the Phase 5B contribution:
- Evaluate 11 complex syntactic patterns (locals, variables, expressions, child modules, conditional logic, etc.) against both the Python Regex parser and the Native Terraform `show -json` pipeline.
- Measure semantic resolution success rate, UNKNOWN/Error rate, and evaluation latency.

## 3. RL Baseline Strategies
The Q-Learning optimizer will be tested against four deterministic algorithms over a subset of the $2^{11}$ possible state representations (spanning single to multi-violation states):
- **Baseline 1 (Fixed Order)**: Remediate controls in arbitrary static sequence.
- **Baseline 2 (Severity First)**: Prioritize highest severity violations.
- **Baseline 3 (Lowest Cost First)**: Prioritize actions with minimum defined remediation cost.
- **Baseline 4 (Random)**: Monte-Carlo random valid action selection across multiple seeds.
- **Experimental (Q-Learning)**: The trained policy derived from the optimal Bellman equation path.

## 4. Security & Isolation Benchmark
Correctness validation isolating adversarial inputs:
- Cross-project leakage (verifying DB scope enforcing).
- Zip bomb / directory traversal tests for application upload constraints.
- Evaluation run tampering (hash chain validation).

## 5. Performance & Scale Benchmark
- Evaluate timing distributions over 1, 10, 25, 50, and 100-resource Terraform payloads.
- Measure Native Plan overhead, OPA latency, and Evidence SQLite storage size.
- Ensure measurement metrics use statistical medians, means, and p95 thresholds with warm-up cycles.
