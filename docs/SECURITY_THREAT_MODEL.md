# RegulaCloud Security Threat Model

| Threat | Attack Scenario | Current Mitigation | Residual Risk | Recommended Mitigation | Priority |
|--------|-----------------|--------------------|---------------|------------------------|----------|
| **Malicious Terraform Execution** | Attacker uploads Terraform code that executes local shell scripts or modifies the host. | Engine only parses HCL text natively using regex. No CLI is executed. | Low | Run real Terraform in an isolated sandbox with restricted privileges. | P1 |
| **Malicious ZIP / Path Traversal** | Attacker uploads ZIP with path traversal (`../`) to overwrite system files. | `extract_safe_zip` checks for `/` and `../`. | Medium (ZIP bombs, nested ZIPs, symlinks are not checked). | Implement strict size limits, file count limits, and symlink validation. | P2 |
| **Cross-Project Access (IDOR)** | User swaps `project_id` in API payload to view/modify other tenant's artifacts. | API routes check `project.owner == current_user.username`. | Medium (Some routes might miss proper artifact isolation). | Enforce standard RBAC middleware for all resource access. | P1 |
| **Weak JWT Secret** | Attacker brute forces weak HMAC secret to forge admin tokens. | `security.py` checks for `JWT_SECRET_KEY` env var. | Medium (If default/fallback is used in production). | Enforce high-entropy keys and regular rotation. | P0 |
| **Audit Ledger Tampering** | Attacker modifies DB records directly, breaking the hash chain. | SHA-256 chaining on previous hash. | High (Race conditions in `create_entry` can fork the chain). | Use DB transactions/locks to serialize ledger writes. | P0 |
| **Artifact Modification (TOCTOU)** | User uploads compliant HCL, gets PASS `/plan`, then uploads malicious HCL and calls `/apply`. | None. `/apply` blindly trusts the `EvaluationRun` status. | **Critical** (Bypasses the entire compliance gate). | Cryptographically bind `/apply` to the exact HCL payload hash evaluated in `/plan`. | P0 |
| **Application Remediation Corruption** | Attacker uploads crafted Java files to exploit regex remediator. | None. Uses blind `re.sub`. | High (Can cause syntax errors or unintended code execution). | Use a proper AST-based patcher with backup files. | P0 |
| **Missing OPA Policy Bypass** | User provisions unmonitored AWS resources or removes policy files. | None. Engine defaults to `PASS` if no policy output matches. | **Critical** | Fail-closed design: unmapped resources or missing policies must result in UNKNOWN/FAIL. | P0 |

## Residual Risk Summary
The most critical vulnerabilities involve the **Deployment Gate TOCTOU** bypass and the **Fail-Closed** logic flaw in the Compliance Engine.
