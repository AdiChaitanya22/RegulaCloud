# Phase 5 Backlog - Generalized Terraform & Compliance Pipeline

## P0 — CRITICAL
**1. True Fail-Closed Compliance Evaluation**
- **Problem:** Missing policies or unsupported resources default to PASS in `ComplianceEngine`.
- **Why it matters:** Unsupported infrastructure can be deployed silently, violating compliance.
- **Files/Components:** `ComplianceEngine.evaluate_compliance`, `OPAPolicyEvaluator`
- **Risk:** High (False positives for compliance).
- **Complexity:** SMALL
- **Acceptance Criteria:** Any unmapped control or missing policy explicitly results in UNKNOWN or FAIL.

**2. Deployment Gate TOCTOU Vulnerability**
- **Problem:** `/plan` evaluates HCL, but `/apply` uses the stored `EvaluationRun` without re-verifying the current project HCL hash.
- **Why it matters:** Users can swap compliant code for malicious code right before deployment.
- **Files/Components:** `Deployments.py`, `ComplianceEngine`
- **Risk:** Critical.
- **Complexity:** MEDIUM
- **Acceptance Criteria:** Deployment gate re-hashes physical project files and matches against `EvaluationRun.evidence_hash`.

**3. Application Remediation Code Corruption**
- **Problem:** `ApplicationRemediator` uses blind Regex replacement, risking syntax errors.
- **Why it matters:** Can corrupt valid Java files or modify unrelated code.
- **Files/Components:** `ApplicationRemediator`
- **Risk:** High.
- **Complexity:** LARGE
- **Acceptance Criteria:** Use proper AST parser or diff-based patching with backup mechanisms.

**4. Audit Ledger Race Condition**
- **Problem:** Concurrent writes to `AuditLog` can reuse the same `previous_hash`.
- **Why it matters:** Cryptographic chain can fork, breaking audit integrity.
- **Files/Components:** `AuditLog.create_entry`
- **Risk:** Medium.
- **Complexity:** MEDIUM
- **Acceptance Criteria:** Use database transactions or row-level locking to ensure sequential hashing.

## P1 — HIGH
**5. Real Terraform CLI Integration & Plan Generation**
- **Problem:** Terraform engine uses regex to parse and modify HCL instead of using the Terraform CLI.
- **Why it matters:** Cannot support variables, modules, or real-world Terraform files.
- **Files/Components:** `TerraformEngine`
- **Risk:** High (Core functionality gap).
- **Complexity:** LARGE
- **Acceptance Criteria:** Safely invoke `terraform init` and `terraform plan -out=plan.tfplan`, followed by `terraform show -json` in an isolated sandbox.

**6. Expanded AWS Policy Coverage**
- **Problem:** Only a few AWS resources are supported by OPA and the Compliance Engine.
- **Why it matters:** Generalization requires covering KMS, Lambda, ECS, VPCs, etc.
- **Files/Components:** `OPAPolicyEvaluator`, `opa_policies/`
- **Risk:** Medium.
- **Complexity:** LARGE
- **Acceptance Criteria:** Comprehensive Rego policies covering 20+ AWS resources.

## P2 — MEDIUM
**7. Q-Learning Persistence & Generalization**
- **Problem:** Q-table is trained synthetically and wiped on server restart. Only supports 8 hardcoded actions.
- **Why it matters:** Makes the RL engine a static simulation rather than a learning system.
- **Files/Components:** `rl_remediator.py`
- **Risk:** Low.
- **Complexity:** MEDIUM
- **Acceptance Criteria:** Persist Q-table to SQLite/Postgres. Expand action space.

**8. Dynamic Dashboard Telemetry & Infrastructure Topology**
- **Problem:** Dashboard telemetry is partially hardcoded, and the Infrastructure Topology is completely static SVG.
- **Why it matters:** Misleads users into thinking it reflects live AWS/Terraform state.
- **Files/Components:** `Dashboard.py`, `Infrastructure.tsx`
- **Risk:** Low.
- **Complexity:** LARGE
- **Acceptance Criteria:** Topology generated from actual Terraform Plan JSON relationships.

## RESEARCH
**9. RL Experimental Evaluation**
- **Problem:** The Q-learning approach lacks empirical justification against simpler algorithms.
- **Why it matters:** Needed to strengthen the dissertation.
- **Complexity:** MEDIUM
- **Acceptance Criteria:** Benchmark RL vs Greedy/Random ordering on convergence and remediation cost metrics.

## FUTURE
**10. Continuous Post-Deployment Drift Detection**
- **Problem:** Currently fully simulated.
- **Why it matters:** Out-of-band AWS changes are not genuinely detected.
- **Complexity:** LARGE
- **Acceptance Criteria:** Integrate AWS Config or run `terraform plan` on a schedule to detect live drift.
