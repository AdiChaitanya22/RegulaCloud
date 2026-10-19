# Phase 6: Research Questions & Hypotheses

### RQ1: Native Semantic Parsing
**Question**: Does native Terraform planning significantly improve compliance-decision correctness compared to synthetic regex parsing for non-literal Terraform constructs?
**Hypothesis (H1)**: The Native Terraform pipeline will yield a 100% semantic resolution accuracy for variables, locals, and modules, whereas the synthetic parser will exhibit a high error rate (> 40%) due to unresolvable symbolic references.

### RQ2: Reinforcement Learning Efficiency
**Question**: Does Q-learning optimize remediation pathways in terms of cost and steps compared to deterministic heuristic baselines?
**Hypothesis (H2)**: Q-learning will identify terminal compliant states with an average cumulative remediation cost lower than Severity-First and Random baselines.

### RQ3: Detection Efficacy
**Question**: How accurately do RegulaCloud's OPA controls and static application scanners detect explicitly modeled misconfigurations?
**Hypothesis (H3)**: The compliance engine will achieve > 95% Precision and Recall on the benchmark corpus for supported resources, maintaining an Unsupported rate separate from PASS metrics.

### RQ4: Automated Remediation Reliability
**Question**: How reliably does RegulaCloud mutate failing configurations into compliant states without breaking syntactic or semantic validity?
**Hypothesis (H4)**: Idempotent RegEx-based safe remediations will successfully convert 100% of tested vulnerable fixtures to PASS state on re-evaluation without causing `terraform validate` failures.

### RQ5: Performance Overhead
**Question**: What operational overhead is introduced by invoking an isolated, non-credentialed Native Terraform Plan pipeline?
**Hypothesis (H5)**: Native evaluation will introduce an absolute latency penalty (median > 500ms) compared to synthetic parsing, but will scale linearly, remaining within acceptable interactive thresholds (< 5s) for topologies up to 100 resources.

### RQ6: Immutable Audit & Trust
**Question**: How effectively does fail-closed cryptographic artifact binding prevent stale or modified workloads from passing the deployment authorization gate?
**Hypothesis (H6)**: Tampering with authorized Terraform code post-evaluation will instantly trigger a `stale=true` state, deterministically blocking simulated deployment across 100% of adversarial TOCTOU trials.
