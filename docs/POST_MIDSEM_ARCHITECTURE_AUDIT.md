# RegulaCloud - Post-Midsem Phase 5 Architecture Audit

## A. Baseline Information
- **Git Branch:** `main`
- **Git Commit:** `10cb6f1` (HEAD -> main, origin/main) feat: Implement Healthcare-B RL application source code remediation
- **Git Tag:** `v1.0.0`
- **Backend Tests:** Passed (82 tests passed, 4 warnings in ~30s).
- **Frontend Build:** Assumed healthy.
- **Repository Cleanliness:** Clean besides modified frontend files and untracked `uploads/` and `docs/` folders.

## B. Architecture Inventory Classification

| Component | Classification | Evidence / Rationale |
|-----------|----------------|----------------------|
| **API Services & Routers** | REAL | FastAPI fully operational in `app/api/v1/`. |
| **Authentication (JWT)** | REAL | Implemented manually using PBKDF2 in `security.py`. |
| **Project Model/Context** | REAL | Backed by SQLite/SQLAlchemy. |
| **Artifact Storage** | REAL | Local file system (`uploads/projects/`). |
| **Regulatory Knowledge / Applicability** | REAL | Stored in DB (`ApplicabilityEngine`). |
| **Compliance Engine** | REAL | Deterministic, merges OPA + Sonar evidence. |
| **Terraform Engine** | **SIMULATED** | Relies on Regex parsing. **No real Terraform CLI invocation.** Synthesizes JSON manually. |
| **OPA / Rego Engine** | **HYBRID** | Tries to invoke local `opa` CLI, falls back to Python-based hardcoded rules (`OPAPolicyEvaluator`). |
| **SonarQube / Code Scan** | **HYBRID** | Tries live REST API, falls back to primitive Regex-based local static scanning. |
| **Application Remediation** | **SIMULATED** | Uses blind Regex string replacement (`ApplicationRemediator`). |
| **Q-Learning Engine** | **SIMULATED** | Offline synthetic training, forgets Q-table on server restart, no real environment feedback. |
| **Deployment Gate** | REAL | Functioning gate logic, but vulnerable to TOCTOU. |
| **Deployment Execution** | **SIMULATED** | Does not actually deploy to AWS, just marks status as SUCCESS. |
| **Audit Ledger** | REAL | Uses SHA-256 hash chaining, but vulnerable to concurrent write race conditions. |
| **Dashboard** | HYBRID | DB-backed but uses hardcoded logic for Severity Distribution calculations. |
| **Infrastructure Topology** | **STATIC** | Hardcoded initial array of nodes in `Infrastructure.tsx`. |
| **AI / RAG Copilot** | REAL | Integrates with Gemini / Ollama with a deterministic fallback. Properly guardrailed. |

## C. Terraform Pipeline Audit
**Verdict:** The Terraform pipeline is purely synthetic.
- `terraform init`, `validate`, `plan`, `show` are **NOT** used anywhere.
- HCL code is parsed via naive Regex.
- Terraform Plan JSON is synthesized internally by matching Regex groups.

## D. Current AWS Resource Coverage
Currently hardcoded in the Terraform regex parser and OPA fallback:
- `aws_db_instance` (RDS)
- `aws_s3_bucket` (S3)
- `aws_s3_bucket_server_side_encryption_configuration`
- `aws_s3_bucket_public_access_block`
- `aws_cloudwatch_log_group`
- `aws_cloudtrail`
*Anything else is completely ignored and silently passes compliance.*

## E. OPA / Rego Audit
- Expects synthetic Plan JSON.
- **Fail-Closed Risk:** If a resource is not parsed, or no policy exists for a control, the engine defaults to `PASS`! This is a critical flaw.

## F. Application Security & Remediation
- **SonarQube Fallback:** Uses `re.search` for basic CWE-89 and CWE-327.
- **ApplicationRemediator:** Blindly runs `re.sub` across all `.java` files. Extremely brittle. Can corrupt unrelated files.

## G. Q-Learning Audit
- **Action Space:** 8 hardcoded static actions.
- **Persistence:** None. Q-table is lost on restart.
- **Environment:** Simulated synthetic environment without real feedback.

## H. Compliance & Deployment Audit
- **TOCTOU Flaw:** `EvaluationRun` hashes the HCL payload at `/plan` time. However, `/apply` does not re-hash the project directory.

## I. Audit Ledger Audit
- Under concurrent API requests, a race condition will cause a chain fork (same `previous_hash` for two different logs).

## J. Project / Tenant Isolation
- Checks for `current_user.role == "ADMIN"` or `project.owner == current_user.username`. Susceptible to IDOR if artifacts are fetched incorrectly.

## K. AI / RAG Audit
- Safe execution. It reads RAG context from the deterministic engine. Zero authorization override privileges.

## L. Continuous Compliance / Drift
- **Status:** **NOT IMPLEMENTED / SIMULATED**.
