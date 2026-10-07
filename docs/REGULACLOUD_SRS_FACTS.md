# RegulaCloud - Software Requirements Specification (SRS) Factsheet

This document provides a factual technical snapshot of the RegulaCloud implementation for use in generating the academic Mid-Sem Software Requirements Specification (SRS).

==================================================
## 1. PROJECT OVERVIEW
==================================================
**1. Exact current project name/title:**
RegulaCloud — Regulation-Aware Cloud Deployment and Compliance Verification Platform (India DPDP Act 2023 & CERT-In 2022).

**2. One-paragraph problem statement:**
Modern cloud deployments often occur without rigorous, automated verification against statutory regulations, leading to data breaches and non-compliance penalties. There is a disconnect between legal compliance frameworks (like the DPDP Act 2023) and technical infrastructure-as-code (IaC) implementation, requiring a system that enforces mandatory security controls before cloud resources are provisioned.

**3. Motivation:**
To shift compliance "left" by embedding legal and regulatory requirements directly into the continuous integration and deployment (CI/CD) or infrastructure provisioning lifecycle.

**4. Primary objective:**
To provide an automated, deterministic compliance verification platform that acts as a deployment gate, preventing non-compliant infrastructure from being provisioned.

**5. Secondary objectives:**
- Automate the mapping of legal texts to technical controls.
- Provide intelligent, ordered remediation recommendations for non-compliant states.
- Maintain a tamper-evident audit ledger for all deployment and evaluation activities.

**6. Target beneficiaries/users:**
DevOps Engineers, Cloud Architects, Security Auditors, Compliance Officers, and Administrators.

**7. Application/domain/sector:**
Cloud Infrastructure Governance, Cybersecurity, Regulatory Tech (RegTech).

**8. Current project scope:**
The system handles project isolation, dynamic regulatory applicability evaluation, compliance checking of Terraform (HCL) and Application code against Indian regulations (DPDP 2023, DPDP Rules 2025, CERT-In 2022) targeting AWS environments.

**9. Features actually implemented:**
- JWT Authentication and Role-Based Access Control (RBAC).
- Regulatory Applicability Engine (matching jurisdiction, data categories, etc.).
- Compliance Engine (parsing Terraform JSON and SonarQube findings).
- Remediation Recommendations (via a simulated Q-learning model).
- Simulated AWS Deployment Gate (blocks non-compliant rollouts).
- Tamper-Evident SHA-256 Audit Log.
- AI Assistant fallback mechanism (Gemini/Ollama/Deterministic).

**10. Features that are planned but not implemented:**
- Real AWS Infrastructure Provisioning (deployments are currently strictly simulated).
- Dynamic, Online Reinforcement Learning (currently relies on a pre-computed/static Q-table training simulation).
- Integration with external SSO/OIDC providers.
- PostgreSQL database integration (currently relies exclusively on SQLite).

**11. Major limitations of the current implementation:**
- Uses SQLite instead of a production-ready database like PostgreSQL.
- Deployment to AWS is fully simulated; no actual boto3 calls or terraform applies occur against live cloud environments.
- If a local OPA binary is missing, the evaluator falls back to a brittle python-based JSON dictionary parsing method.
- The local application security scanner is a regex-based fallback (AST simulation) if a real SonarQube server is unreachable.

==================================================
## 2. CURRENT TECHNOLOGY STACK
==================================================
**Frontend:**
- **Framework:** React 19 (via Vite)
- **Language:** TypeScript
- **Build tool:** Vite
- **Routing:** React Router DOM (v7)
- **Major libraries:** TailwindCSS, Radix UI, Framer Motion, Recharts, Lucide-React
- **State/context management:** React Context API (`AuthContext`)

**Backend:**
- **Framework:** FastAPI
- **Language:** Python 3
- **API architecture:** REST
- **ORM:** SQLAlchemy
- **Database:** SQLite (`regulacloud.db`)
- **Authentication mechanism:** JWT (JSON Web Tokens) with Passlib/Bcrypt password hashing

**Cloud/IaC:**
- **Terraform:** HCL parsing/generation via Jinja2 templates.
- **AWS-related components:** Target provider for generated code (S3, RDS, CloudWatch, CloudTrail, IAM).
- **OPA/Rego:** Hybrid implementation. Attempts to run a local OPA binary to evaluate policies; if unavailable, falls back to native Python dictionary parsing of the `terraform plan` JSON.
- **Terraform parsing/evaluation approach:** Regex-based HCL to JSON converter natively implemented in Python (`TerraformEngine.hcl_to_plan_json`).

**Security:**
- **SonarQube:** Hybrid. Tries SonarQube REST API; falls back to local regex-based AST scanning for CWE-89, CWE-327.
- **Application-code scanning:** Yes, local fallback available for Java/Python/TS.
- **Authentication:** JWT Bearer tokens.
- **Authorization/RBAC:** Custom dependency injection decorators (`require_user`, `require_admin`).
- **Password hashing:** Bcrypt.
- **Audit mechanism:** Tamper-evident SHA-256 hash chaining on the `audit_logs` table.

**AI:**
- **LLM provider(s):** Google Gemini API, local Ollama.
- **Knowledge retrieval / RAG:** Implemented via `RAGContext` feeding into the prompt.
- **Guardrails / Fallback:** A deterministic grounded fallback engine activates if the LLM provider is unavailable or fails.

**RL (Reinforcement Learning):**
- **Q-learning implementation:** Yes, in `rl_remediator.py`.
- **State:** Binary tuple representing active violations (e.g., `(1, 0, 1, 0)`).
- **Actions:** 8 hardcoded approved remediation actions (e.g., `ACT_ENABLE_RDS_ENC`).
- **Reward/cost/complexity:** Actions have predefined cost and complexity penalties. Reward formula: `50 - (cost + complexity)`.
- **Q-table:** Maintained in memory as a Python dictionary mapping states to Numpy arrays.
- **Whether learning is online/offline:** Offline / Pre-computed. The agent is trained inside a loop on a simulated environment state before returning recommendations; it does NOT learn online from actual user feedback.
- **Remediation mechanism:** Returns an ordered list of suggested HCL modifications.

==================================================
## 3. SYSTEM ARCHITECTURE
==================================================
**Current Architecture Flow:**
User → React Frontend → FastAPI (REST API) → Authentication/RBAC Gate → Route Handler
→ Project Context Retrieval
→ **Applicability Engine**: Determines which rules apply based on project metadata.
→ **Compliance Engine**:
   → **Terraform Engine**: Converts HCL to Plan JSON.
   → **OPA Evaluator**: Evaluates Plan JSON against Rego policies (or native Python fallback).
   → **SonarQube Client**: Scans app code via API or local regex fallback.
→ Compliance Engine aggregates PASS/FAIL/UNKNOWN statuses.
→ **Q-Learning Remediator**: (If violations exist) Suggests sequence of remediation actions.
→ **Deployment Gate**: Blocks if `failed_count > 0` or `unknown_count > 0` for mandatory controls.
→ **Simulated Deployment**: If approved and passing, marks status as SUCCESS and logs to DB (no real AWS deployment).
→ **Audit Ledger**: Hashes the evaluation/deployment payload and chains it to the previous hash.

**Component Reality Status:**
- **REAL**: React Frontend, FastAPI Backend, SQLite DB, JWT Auth, Applicability Engine, Tamper-evident audit chain.
- **HYBRID / FALLBACK**: OPA Evaluation (real binary OR simulated python parsing), SonarQube (real API OR simulated local regex scan), AI Assistant (Gemini OR deterministic fallback).
- **SIMULATED**: AWS Deployment (mocked success, no actual provisioning).
- **STATIC / PRE-COMPUTED**: Q-Learning Remediation (trains on a static internal model, not online user behavior).

==================================================
## 4. REGULATORY KNOWLEDGE BASE
==================================================
The application implements exact structured regulatory JSON seeds located in `backend/app/db/seeds/`:

1. **CERT-In Directions under Section 70B(6) of IT Act, 2000**
   - Requirements: `CERTIN-2022-LOG-RETENTION` (180-day logs), `CERTIN-2022-NTP-SYNC` (NPL NTP), `CERTIN-2022-INCIDENT-LOGS` (6-hour readiness).
2. **Digital Personal Data Protection Act, 2023 (DPDP-ACT-2023)**
   - Requirements: `DPDP-2023-SEC8.5` (Security Safeguards/Encryption), `DPDP-2023-SEC8.6` (Breach Logging), `DPDP-2023-SEC8.1` (Purpose Isolation), `DPDP-2023-SEC9.1` (Children's data).
3. **Digital Personal Data Protection Rules, 2025 (Draft)**
   - Requirements: `DPDPR-2025-R4.2` (Data erasure), `DPDPR-2025-R6.1` (IAM MFA), `DPDPR-2025-R8.3` (AppSec baseline).

**Technical Controls (Control IDs):**
`CTRL-AWS-S3-ENC`, `CTRL-AWS-S3-NO-PUBLIC`, `CTRL-AWS-RDS-NO-PUBLIC`, `CTRL-AWS-RDS-STORAGE-ENC`, `CTRL-AWS-LOG-180D`, `CTRL-AWS-CLOUDTRAIL-MULTI`, `CTRL-AWS-S3-LIFECYCLE`, `CTRL-AWS-IAM-MFA`, `CTRL-AWS-NTP-SYNC`, `CTRL-SONAR-ZERO-CRITICAL`, `CTRL-SONAR-INJECTION-FREE`.

**Data Storage & Loading:**
Regulations, Requirements, Controls, and Mappings are stored in the SQLite database and are seeded via `init_db.py` reading the JSON files.

**Applicability Engine:**
Checks `project_profile` (jurisdiction, data categories, sector, environment) against the `applicability_conditions` JSON field in `RegulatoryRequirement`.

**Compliance Engine:**
Looks up mappings in `RequirementControlMapping`. Calls OPA/Terraform or SonarQube based on the control's `verification_source` field, aggregating results to determine compliance.

==================================================
## 5. FUNCTIONAL REQUIREMENTS
==================================================
**FR-01: User Authentication:**
The system shall authenticate users via username and password and issue a JWT token. (API: `/api/v1/auth/login`)

**FR-02: Role-Based Access Control (RBAC):**
The system shall restrict specific endpoints (like deployment application) to users with the 'ADMIN' role.

**FR-03: Project Management:**
The system shall allow users to create, retrieve, update, and isolate cloud infrastructure projects containing specific compliance metadata. (API: `/api/v1/projects`)

**FR-04: Infrastructure Upload (HCL):**
The system shall allow users to upload or paste Terraform HCL configurations for evaluation.

**FR-05: Regulatory Applicability Determination:**
The system shall dynamically filter and select applicable regulatory requirements based on the project's sector, data categories, and environment.

**FR-06: Terraform/OPA Compliance Evaluation:**
The system shall evaluate Terraform HCL state against defined OPA control expected states, outputting PASS/FAIL findings.

**FR-07: Application Security Scanning:**
The system shall evaluate application source code via SonarQube API or local AST fallback to detect critical vulnerabilities (e.g., CWE-89).

**FR-08: Remediation Recommendation Generation:**
The system shall utilize a Q-learning agent to recommend an optimized, ordered sequence of Terraform HCL modifications for identified compliance failures.

**FR-09: Deployment Gating:**
The system shall block the generation of a simulated deployment plan if any mandatory regulatory requirement is evaluated as FAIL or UNKNOWN.

**FR-10: Simulated Cloud Deployment:**
The system shall simulate an AWS resource deployment for compliant projects upon administrator approval, logging the execution.

**FR-11: Tamper-Evident Audit Logging:**
The system shall compute a SHA-256 hash for every system action, cryptographically chaining it to the previous action's hash.

**FR-12: AI Copilot Assistance:**
The system shall provide an AI chat interface utilizing context-aware RAG to answer regulatory and compliance questions, with deterministic fallback capabilities.

==================================================
## 6. NON-FUNCTIONAL REQUIREMENTS
==================================================
- **Security:** Passwords shall be hashed using Bcrypt. All API endpoints except login must require a valid JWT Bearer token.
- **Reliability (Graceful Degradation):** The system shall fallback to local native processing if external dependencies (SonarQube server, OPA binary, external LLM provider) are unreachable.
- **Maintainability:** The regulatory knowledge base shall be decoupled from application logic via JSON seed files and database mappings.
- **Performance:** Cryptographic audit verification must execute efficiently; simulated deployments must respond synchronously.
- **Correctness:** The deployment gate must act deterministically; failure in evidence gathering must result in a fail-closed (UNKNOWN -> BLOCKED) state.

==================================================
## 7. USER CLASSES AND RBAC
==================================================
**Roles Implemented:**
- **USER (Operator):** Can view dashboard, create projects, upload code, run evaluations, generate remediation plans, and initiate deployment plans (which enter `AWAITING_APPROVAL`). Cannot apply deployments.
- **ADMIN:** Can do everything a USER can, plus authorize and execute the actual deployment application (`/{deployment_id}/apply`), and access global system settings.

**Security Flows:**
- **Login Flow:** User posts credentials to `/api/v1/auth/login`, receives JWT.
- **JWT Flow:** Token passed in `Authorization: Bearer <token>` header. FastApi `Depends(get_current_user)` decodes and validates token.
- **Password Hashing:** Passlib with Bcrypt.
- **Deployment Authorization:** The `/apply` endpoint is protected by `Depends(require_admin)`.

==================================================
## 8. DATABASE / DATA STRUCTURES
==================================================
**Database Type:** SQLite (File: `backend/regulacloud.db`)

**Key Models / Tables:**
- `users`: id, username, email, hashed_password, role.
- `regulations`: id, name, jurisdiction.
- `regulatory_requirements`: id, regulation_id, mandatory, applicability_conditions (JSON).
- `technical_controls`: id, name, verification_source, expected_state (JSON).
- `requirement_control_mappings`: Maps requirements to controls.
- `projects`: id, name, sector, data_categories (JSON), environment, compliance_score, hcl_content, status.
- `evaluation_runs`: id, project_id, overall_status, compliance_score, passed_count, failed_count, evidence_hash.
- `requirement_evaluations`: Links evaluation runs to specific requirements, storing PASS/FAIL and findings JSON.
- `deployments`: id, project_id, evaluation_run_id, status (BLOCKED, AWAITING_APPROVAL, SUCCESS), logs.
- `audit_logs`: id, actor, action, previous_hash, current_hash, timestamp. (Crucial for tamper-evidence).
- `system_settings`: Key-value JSON storage for app configuration.

==================================================
## 9. DATA / DATA CHARACTERISTICS
==================================================
- **A. Regulatory data:** Static JSON dictionaries mapped into SQLite. Highly structured.
- **B. Infrastructure/IaC data:** Terraform HCL strings (user-provided or generated) and Terraform Plan JSON (generated dynamically).
- **C. Application source code:** Read from local filesystem paths (e.g. `test_apps/`).
- **D. Compliance/evaluation data:** Deterministic structured JSON containing finding counts, reasons, and arrays of violations.
- **E. Security findings:** Array of dictionaries detailing file, line number, and CWE identifier.
- **F. RL state/action data:** Transient in-memory Numpy arrays and binary tuples; not stored persistently across server restarts. NO conventional ML dataset exists; training is done synthetically on-the-fly.
- **G. Audit/evidence data:** Highly sensitive JSON payloads hashed with SHA-256 and persisted immutably in SQLite.

==================================================
## 10. ALGORITHMS
==================================================
**A. Regulatory Applicability Engine:** Set-intersection and string matching logic comparing a project's JSON metadata against requirement condition dictionaries.
**B. Compliance Evaluation:** Deterministic aggregation. If any control linked to a mandatory requirement fails or errors, the requirement FAILS.
**C. OPA/Rego Policy Evaluation:** Hybrid. If `opa` binary exists, runs a subprocess. Otherwise, executes a custom Python native fallback that iterates through Terraform Plan JSON dictionary keys using regex and conditional logic.
**D. SonarQube Application Scanning:** Hybrid. Requests findings from Sonar API, falls back to Python regex matching (`re.search`) over source code lines to detect CWE-89 (SQLi) and CWE-327 (Weak Crypto).
**E. Q-Learning Remediation Optimizer:**
  - **State Representation:** Binary tuple representing active violations (e.g., `(1,0,0)`).
  - **Actions:** Hardcoded list of 8 predefined actions with cost/complexity penalties.
  - **Reward Model:** `50 - (cost + complexity)`. Redundant actions yield `-10`. Full compliance yields `+100`.
  - **Q-table:** Trained synthetically. Epsilon-greedy action selection.
  - **Learning Status:** Pre-computed / Static simulation. It trains in memory for a few hundred synthetic episodes upon request, then extracts the highest Q-value path. It does NOT learn from actual live deployment success/failure.
**H. SHA-256 Audit Hash Chaining:** Iteratively calculates `SHA-256(current_payload + previous_hash)`. Verification brute-forces microsecond timestamp offsets to account for serialization jitter.

==================================================
## 11. API CATALOG
==================================================
| Method | Endpoint | Purpose | Role |
|---|---|---|---|
| POST | `/api/v1/auth/login` | Authenticate user & get JWT | Public |
| GET | `/api/v1/auth/me` | Get current user profile | USER |
| GET | `/api/v1/projects` | List all projects | USER |
| POST | `/api/v1/projects` | Create a new project | USER |
| POST | `/api/v1/projects/{id}/upload/infrastructure` | Upload HCL | USER |
| POST | `/api/v1/applicability/evaluate` | Determine applicable rules | USER |
| POST | `/api/v1/compliance/evaluate` | Run deterministic evaluation | USER |
| POST | `/api/v1/remediation_rl/optimize` | Generate Q-learning plan | USER |
| POST | `/api/v1/security_sonar/scan` | Trigger app security scan | USER |
| GET | `/api/v1/deployments` | List deployment plans | USER |
| POST | `/api/v1/deployments/plan` | Evaluate and create a deployment plan (Gate) | USER |
| POST | `/api/v1/deployments/{id}/apply` | Execute simulated AWS rollout | ADMIN |
| GET | `/api/v1/audit/logs` | Fetch ledger entries | USER |
| GET | `/api/v1/audit/verify` | Cryptographically verify hash chain | USER |
| POST | `/api/v1/ai_copilot/chat` | Chat with LLM/RAG | USER |

==================================================
## 12. FRONTEND PAGE INVENTORY
==================================================
- **`/` (Landing Page):** Public marketing page.
- **`/login`:** User authentication form. Calls `/api/v1/auth/login`.
- **`/dashboard`:** Protected. Shows system stats.
- **`/projects`:** List and create projects. Calls `/api/v1/projects`.
- **`/deployments`:** Views deployment history.
- **`/infrastructure`:** View project topology and upload Terraform HCL.
- **`/compliance`:** Triggers evaluations and displays PASS/FAIL metrics and Sonar/OPA findings.
- **`/policies`:** Lists regulatory requirements.
- **`/security`:** Detailed view of SonarQube/SAST findings.
- **`/ai-assistant`:** Chat interface to LLM.
- **`/audit`:** View audit logs and trigger cryptographic hash chain verification.
- **`/reports`:** Generate compliance summary PDFs/data.
- **`/settings`:** Admin system settings.
- **`/deploy`:** The Deployment Gate interface. Initiates deployment plan and shows ADMIN apply button.

*Data is generally DB-backed, but AWS deployment status is simulated.*

==================================================
## 13. COMPLETE USER WORKFLOWS
==================================================
**Workflow 4 (Remediation):**
User views OPA violations on frontend → clicks "Generate Remediation Plan" → API `/api/v1/remediation_rl/optimize` → Backend instantiates `QLearningRemediationAgent`, trains synthetically, returns ordered JSON list of HCL modifications → Frontend displays actions.

**Workflow 7 (Deployment Gate):**
User navigates to `/deploy` → clicks "Initiate Deployment Plan" → API `/api/v1/deployments/plan` → Backend runs `ComplianceEngine.evaluate_compliance`. If `failed_count > 0` for mandatory controls, status = BLOCKED. Else, status = AWAITING_APPROVAL. → Admin views plan → clicks "Apply" → API `/api/v1/deployments/{id}/apply` verifies evaluation run matches → DB status updated to SUCCESS (simulated AWS rollout).

**Workflow 8 (Audit Verification):**
User navigates to `/audit` → clicks "Verify Chain" → API `/api/v1/audit/verify` → Backend sequentially hashes all rows and compares `previous_hash` chains → Returns valid/invalid status.

==================================================
## 14. DEPLOYMENT GATE
==================================================
**Implementation:**
The gate is a deterministic backend function (`deployments.py: create_deployment_plan`).
- Evaluates compliance dynamically based on current HCL.
- **FAIL/BLOCKED:** If `failed_count > 0` or `unknown_count > 0` for any requirement flagged as `mandatory = True`.
- **PASS/AWAITING_APPROVAL:** If all mandatory requirements pass.
- **Fail-closed:** If evidence cannot be collected (e.g., Sonar fails entirely without fallback), the control becomes UNKNOWN, which blocks deployment.
- **Simulated AWS:** The deployment is 100% simulated. The `/apply` endpoint merely updates DB state to SUCCESS and appends dummy logs ("Provisioning AWS Cloud resources...").

==================================================
## 15. AUDIT / EVIDENCE
==================================================
The system utilizes a **TAMPER-EVIDENT SHA-256 HASH CHAIN**.
- `AuditLog` fields: actor, action, resource, severity, details, previous_hash, current_hash, timestamp.
- Chain construction: `current_hash = SHA256(payload + previous_hash)`.
- Verification endpoint loops through the table verifying that `row[n].previous_hash == row[n-1].current_hash` and recompiling the payload hash.
- Note: The database itself (SQLite) is NOT immutable. If an attacker gains raw DB access, they can alter data, but the `verify` endpoint will detect the broken hash chain.

==================================================
## 16. SWOT ANALYSIS INPUT
==================================================
- **Strengths:** Excellent hybrid fallback architecture ensuring zero-downtime compliance evaluation. Cryptographic audit trails build strong trust.
- **Weaknesses:** SQLite database limits horizontal scalability. Deployments are currently only simulated.
- **Opportunities:** Integration with real AWS APIs (boto3) and enterprise SSO (Okta/Entra).
- **Threats:** Complex changes in DPDP rules may outpace the static applicability engine mappings.

==================================================
## 17. DESIGN CONSTRAINTS
==================================================
- **Database:** Hard dependency on local filesystem SQLite (`regulacloud.db`).
- **Runtime:** Requires Python 3 and Node.js (Vite).
- **Remediation limitations:** Regex-based HCL remediation is brittle and may fail on complex Terraform modules.
- **Deployment Limitations:** Cloud deployment is simulated; cannot provision actual resources.

==================================================
## 18. ASSUMPTIONS AND DEPENDENCIES
==================================================
- **Assumptions:** Evaluated Terraform configurations are for AWS `ap-south-1`.
- **Dependencies:** FastAPI, SQLAlchemy, React, Vite.
- **Optional Services:** External SonarQube Server, External OPA binary, Google Gemini API (all have internal offline fallbacks).

==================================================
## 19. PROTOCOLS AND INTERFACES
==================================================
- **HTTP/REST:** Communication between React frontend and FastAPI backend.
- **JSON:** Primary payload format for APIs and regulatory configuration seeds.
- **JWT:** Used for secure, stateless session management.
- **SQLite (SQL):** Database communication.

==================================================
## 20. DESIGN DIAGRAM REQUIREMENTS
==================================================
- **Level-2 Use Case Diagram:** Actors (User, Admin). Cases: Authenticate, Manage Projects, Upload IaC, Evaluate Compliance, Generate Remediation, Authorize Deployment.
- **Class Diagram:** `User`, `Project`, `EvaluationRun`, `RegulatoryRequirement`, `TechnicalControl`, `Deployment`, `AuditLog`. (Show composition between `EvaluationRun` and `RequirementEvaluation`).
- **Activity Diagram (Deployment Gate):** Upload HCL -> Run Applicability -> Evaluate OPA/Sonar -> Decision Node (Violations?) -> Yes: Block Deployment -> Generate Remediation. No: Await Admin Approval -> Simulate AWS Deployment.
- **Sequence Diagram (Compliance):** Frontend -> API `/evaluate` -> Applicability Engine -> Terraform Engine (HCL->JSON) -> OPA Evaluator -> Sonar Client -> API aggregates -> Returns JSON.

==================================================
## 21. TESTING / VERIFICATION
==================================================
- Tests exist in the `backend/tests/` directory (e.g. `test_project_artifacts.py`).
- Verification relies primarily on the internal backend engines acting deterministically.

==================================================
## 22. CURRENT DEMO DATA
==================================================
- Pre-loaded configurations are generated by `init_db.py` reading from the `seeds/` directory.
- Regulatory seeds include specific IDs (e.g., `DPDP-2023-SEC8.5`, `CERTIN-2022-LOG-RETENTION`).

==================================================
## 23. REALITY MATRIX
==================================================
| Component | Current Status | Evidence in Code | Limitation |
|---|---|---|---|
| Frontend | REAL | `frontend/src/` React code | None |
| Backend | REAL | `backend/app/main.py` FastAPI | None |
| SQLite | REAL | `backend/app/db/models.py` | Not scalable like PostgreSQL |
| Authentication | REAL | `api/v1/auth.py` JWT logic | No external SSO |
| RBAC | REAL | `@Depends(require_admin)` | Basic Roles |
| Regulatory KB | REAL | `db/seeds/*.json` | Limited to provided JSON |
| Applicability Engine | REAL | `applicability_engine.py` | Rule engine |
| OPA | HYBRID | `opa_evaluator.py` | Falls back to custom python dictionary parsing |
| Terraform | HYBRID | `terraform_engine.py` | Only parses to JSON, no real apply |
| SonarQube | HYBRID | `sonarqube_client.py` | Falls back to local regex AST scanning |
| Q-learning | STATIC | `rl_remediator.py` | Pre-computed/synthetic training, not online |
| App Remediation | SIMULATED | `application_remediator.py` | Uses static text replacement |
| RAG/LLM | HYBRID | `llm_client.py` | Falls back to deterministic rule engine |
| Audit chain | REAL | `AuditLog` current_hash | Tamper-evident, but DB is not immutable |
| AWS deployment | SIMULATED | `deployments.py` | Just updates DB status to SUCCESS |

==================================================
## 24. SRS-READY SUMMARY
==================================================
**A. Project abstract:** RegulaCloud is a continuous compliance verification platform designed to bridge the gap between regulatory mandates (like India's DPDP Act 2023 and CERT-In) and technical cloud infrastructure provisioning.
**B. Problem statement:** Cloud infrastructures are often deployed without automated checks against legal frameworks, leading to non-compliance.
**C. Objectives:** Automate compliance, prevent non-compliant deployments, generate remediation plans, and maintain a tamper-evident audit ledger.
**D. Main technologies:** React, FastAPI, SQLite, OPA (Hybrid), SonarQube (Hybrid).
**E. Main limitations:** Fully simulated deployments, pre-computed Q-learning, reliance on local regex fallbacks for complex tooling.

==================================================
### FACTS THAT MUST NOT BE MISREPRESENTED IN THE SRS
==================================================
1. **Database:** The system uses **SQLite**, NOT PostgreSQL or MySQL.
2. **Deployments:** AWS deployments are **100% SIMULATED**. The backend does not actually provision AWS resources using boto3 or terraform apply.
3. **Machine Learning:** The Q-learning algorithm is a **STATIC/PRE-COMPUTED** simulation. It does not perform "online" learning based on user behavior.
4. **Third-Party Tools:** OPA and SonarQube implementations are **HYBRID**. If the real server/binary is unavailable, they actively fall back to custom Python string/regex parsing.
5. **Audit Logs:** The audit system provides a **TAMPER-EVIDENT SHA-256 HASH CHAIN**, but the underlying database (SQLite) is NOT inherently immutable like a blockchain.
6. **AI:** RAG and LLM functionality will fall back to a deterministic, hardcoded engine if external API keys (Gemini/Ollama) are not provided or fail.
