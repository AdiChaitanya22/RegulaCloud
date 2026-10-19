# Phase 6: Threats to Validity

In benchmarking RegulaCloud for the final evaluation, several internal and external threats to validity must be declared.

## 1. Internal Threats (System Design)
- **Regex Remediation**: Auto-remediation relies on idempotent Regex pattern substitution rather than safe AST manipulation (e.g., HCLEDIT). Edge-case HCL formatting may cause syntax invalidation.
- **Synthetic Workloads**: Performance benchmarks are executed against generated or heavily mocked AWS architectures, which may not completely map to the complexity of real-world enterprise IaC.
- **Local Scanner Fallback**: The evaluation compares SonarQube with a simplistic local static RegExp engine (e.g., catching `SELECT * FROM`). The fallback is intentionally primitive, affecting realistic recall scaling for complex application logic.
- **SQLite Database Constraints**: Extrapolated storage metrics rely on SQLite. A production database (PostgreSQL) would handle caching, concurrency, and payload compression differently.

## 2. External Threats (Generalizability)
- **Simulated AWS Deployment**: RegulaCloud does not run `terraform apply`. While plan execution is native, the final deployment phase is simulated. Unforeseen AWS API constraints are not benchmarked.
- **Limited Regulatory Corpus**: Currently, controls map to a constrained subset of DPDP Section 8(5) and CERT-In. Full mapping to PCI-DSS or HIPAA could exponentiate the State/Action dimensionality of the Q-Learning algorithm, potentially degrading convergence stability.
- **Deterministic Offline Provider**: The Native pipeline uses an offline, mocked AWS Provider configuration to bypass STS/Credentials. Unforeseen network requirements for specialized modules might affect live deployments.

## 3. Construct Validity & Provenance Integrity
- **Synthesized vs. Executed Provenance Quarantine**: Early prototyping utilized synthesized baseline result structures. To ensure strict scientific validity, all synthesized runs (e.g. `1791380137-INVALID-SYNTHESIZED`) are quarantined and rejected by the benchmark harness by default. Only measurements produced by active execution of Native Terraform CLI, OPA Evaluator, and production RL agents are accepted as empirical evidence.
