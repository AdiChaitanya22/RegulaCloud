# REGULACLOUD — COMPLETE STUDY GUIDE

*This is a read-only reverse-engineering documentation of the current RegulaCloud repository.*

## Table of Contents
1. [Part 1: Current Application Discovery](#part-1-current-application-discovery)
2. [Part 2: Database Architecture](#part-2-database-architecture)
3. [Part 3: API Catalog](#part-3-api-catalog)
4. [Part 4: OPA Integration & Terraform](#part-4-opa-integration--terraform)
5. [Part 5: SonarQube Integration](#part-5-sonarqube-integration)
6. [Part 6: Q-Learning & Remediation Engine](#part-6-q-learning--remediation-engine)
7. [Part 7: AI Assistant & RAG Implementation](#part-7-ai-assistant--rag-implementation)
8. [Part 8: Dashboard & Telemetry](#part-8-dashboard--telemetry)
9. [Part 9: Infrastructure Topology](#part-9-infrastructure-topology)
10. [Part 10: Audit Ledger & Cryptographic Verification](#part-10-audit-ledger--cryptographic-verification)
11. [Part 11: Security Architecture](#part-11-security-architecture)
12. [Part 12: Regulatory Knowledge Base](#part-12-regulatory-knowledge-base)
13. [Part 13: Complete System Flow](#part-13-complete-system-flow)
14. [Part 14: Failure Scenarios](#part-14-failure-scenarios)
15. [Part 15: Reality Matrix](#part-15-reality-matrix)
16. [Part 16: File-by-File Code Map](#part-16-file-by-file-code-map)

---

## Part 1: Current Application Discovery

### Frontend Architecture (React + Vite + TypeScript)
- **Entry Point**: `frontend/src/main.tsx` mounting `<App />` from `App.tsx`.
- **Routing**: Handled by `frontend/src/routes.tsx` using `react-router-dom`. Protected routes check for auth tokens.
- **State Management**: React Context (`AuthContext.tsx`, `ProjectContext.tsx`) and `sessionStorage` (transient).
- **Core Pages**:
  - `Dashboard.tsx`: High-level metrics.
  - `Projects.tsx`: Project selection and creation.
  - `Deploy.tsx`: The primary gating interface showing OPA and SonarQube evaluation results and the RL remediation trigger.
  - `Compliance.tsx`: Traceability matrix.
  - `AIAssistant.tsx`: Chat interface for LLM fallback/Gemini/Ollama.
  - `SecurityScanner.tsx`: Pipeline visualization for SonarQube.
  - `AuditLogs.tsx`: Tamper-evident ledger UI.

### Backend Architecture (FastAPI + SQLAlchemy + SQLite)
- **Entry Point**: `backend/app/main.py`.
- **Database**: SQLite (default `regulacloud.db` fallback). NOT PostgreSQL by default.
- **Core Engines** (`backend/app/engines/`):
  - `compliance_engine.py`: Orchestrates OPA and Sonar evaluation.
  - `terraform_engine.py`: HCL to Plan JSON parsing, S3/RDS template generation, and Terraform remediation.
  - `opa_evaluator.py`: CLI wrapper for OPA. Includes local fallback logic for DPDP/CERT-In rules if OPA binary is absent.
  - `sonarqube_client.py`: Calls SonarQube API, falls back to raw regex scanning (CWE-89, CWE-327) on `.java/.ts/.py` files.
  - `rl_remediator.py`: Implements a hardcoded Q-learning table for finding optimal remediation paths based on cost and complexity.
  - `application_remediator.py`: Modifies physical Java source files to fix CWEs.
  - `llm_client.py` & `guardrails.py`: AI Assistant using Gemini/Ollama with a zero-downtime deterministic grounding fallback.

---

## Part 2: Database Architecture

The application uses **SQLite** natively. 

### Key Models (`backend/app/db/models.py`)
1. **User**: `username`, `hashed_password`, `role` (ADMIN, USER).
2. **Project**: Holds metadata, `compliance_score`, `hcl_content`, `infrastructure_path`, `application_source_path`.
3. **EvaluationRun**: Captures `overall_status`, `compliance_score`, `evidence_hash`, `failed_count`. This is the deterministic record of a scan.
4. **RequirementEvaluation**: Maps an EvaluationRun to specific RegulatoryRequirements (status: PASS/FAIL). Contains JSON `findings`.
5. **TechnicalControl**: Defines expected state (e.g., `CTRL-AWS-S3-ENC`).
6. **AuditLog**: Stores `action`, `severity`, `details`, and `current_hash` (a SHA-256 chain validating history).
7. **Deployment**: Records rollout state (`AWAITING_APPROVAL`, `SUCCESS`, `BLOCKED`).

*Note: Database immutability for the Audit Ledger is software-enforced via hash chaining, not true database-level immutability.*

---

## Part 3: API Catalog

| Method | Endpoint | Purpose | Role |
|--------|----------|---------|------|
| POST | `/api/v1/auth/login` | Authenticates users, returning a JWT. | ALL |
| GET | `/api/v1/projects` | Lists accessible projects. | ALL |
| POST | `/api/v1/projects/{id}/upload/infrastructure` | Extracts ZIP, reads `.tf` to `hcl_content`. | Owner/Admin |
| POST | `/api/v1/projects/{id}/upload/application` | Extracts ZIP to `application_source_path`. | Owner/Admin |
| POST | `/api/v1/projects/{id}/remediate` | Triggers Terraform + App modifications via action IDs. | Owner/Admin |
| POST | `/api/v1/deployments/plan` | Triggers the Compliance Engine evaluation. | ALL |
| POST | `/api/v1/deployments/{id}/apply` | Completes simulated deployment (AWS API not actively called). | **ADMIN** |
| GET | `/api/v1/compliance/summary` | Dashboard compliance aggregation. | ALL |
| GET | `/api/v1/security/findings` | SonarQube fetch/scan. | ALL |
| POST | `/api/v1/ai/chat` | RAG-grounded LLM interaction. | ALL |
| GET | `/api/v1/audit/logs` | Fetches cryptographic audit ledger. | ALL |

---

## Part 4: OPA Integration & Terraform

- **Reality**: HYBRID (Real evaluation, simulated execution).
- **Process**: 
  1. `terraform_engine.py` converts `hcl_content` into a mocked `tfplan_json` structure.
  2. `opa_evaluator.py` attempts to run `opa eval --data opa_policies --input tmp.json data.regulacloud`.
  3. **Fallback**: If `opa` binary isn't present, a native Python evaluation checks `tfplan_json` for missing encryption (`storage_encrypted`), public exposure (`publicly_accessible`), and logging configuration.
- **Deployment**: True AWS rollout is **SIMULATED**. `deployments.py` simply records logs: `[SUCCESS] Terraform state applied cleanly.`

---

## Part 5: SonarQube Integration

- **Reality**: HYBRID (Real API or static regex fallback).
- **Process**:
  1. `sonarqube_client.py` attempts to hit the SonarQube REST API (`/api/issues/search`).
  2. **Fallback**: If unavailable or offline, it traverses the `application_source_path`, manually `re.search`ing for SQL concatenation (CWE-89) and DES encryption (CWE-327) in `.java` / `.ts` files, yielding exact line numbers.

---

## Part 6: Q-Learning & Remediation Engine

- **Reality**: STATIC / RULE-BASED (Offline Q-learning matrix).
- **Implementation**:
  - `rl_remediator.py` uses pre-calculated Q-values mapping state (failed controls) to actions (e.g., `ACT_ENABLE_RDS_ENC`).
  - While framed as reinforcement learning, it behaves deterministically at runtime.
- **Application Remediation**: `application_remediator.py` does **REAL** text replacement in physical source files (e.g., replacing `"DES"` with `"AES/GCM/NoPadding"`).
- **Terraform Remediation**: `terraform_engine.py` applies **REAL** regex injection to the `hcl_content` (e.g., inserting `storage_encrypted = true`).

---

## Part 7: AI Assistant & RAG Implementation

- **Reality**: HYBRID (LLM dependent on API Key, falls back to deterministic text).
- **Implementation**:
  - `rag_engine.py` builds context (Project, Violations, Score).
  - `llm_client.py` calls Gemini / Ollama if configured.
  - **Fallback**: If keys are missing, `guardrails.py` uses hardcoded deterministic string formatting (e.g., "Deployment is Blocked...").

---

## Part 8: Dashboard & Telemetry

- **Reality**: HYBRID (DB-driven, but not real-time).
- **Implementation**:
  - `dashboard.py` queries `EvaluationRun` to get failure counts.
  - The UI does NOT use WebSockets. It relies on standard REST polling or manual refresh.

---

## Part 9: Infrastructure Topology

- **Reality**: STATIC / HYBRID.
- **Implementation**:
  - The `Infrastructure.tsx` page renders React Flow nodes. While it maps dynamically to `cloudProvider` and `region`, the visual diagram is largely predefined and does not deeply introspect the `hcl_content` AST for visualization.

---

## Part 10: Audit Ledger & Cryptographic Verification

- **Reality**: HYBRID (Valid SHA-256 chaining, but standard SQL storage).
- **Implementation**:
  - `models.py (AuditLog.create_entry)` hashes the previous record's hash along with the current payload, forming a true hash chain.
  - It is tamper-evident, but anyone with raw SQLite DB access could theoretically recalculate the entire chain.

---

## Part 11: Security Architecture

- **Authentication**: JWT tokens generated in `security.py`. Uses `HS256`.
- **Authorization**: `require_admin` ensures only `ADMIN` roles can hit `/deployments/{id}/apply`.
- **Gate Enforcement**: `deployments.py` checks `eval_run.overall_status != "PASS"`. This is a hard, fail-closed programmatic gate. AI cannot override it.

---

## Part 12: Regulatory Knowledge Base

- **Reality**: BACKEND-DRIVEN (DB-seeded).
- **Implementation**:
  - Seeded during `database_seeder.py` execution.
  - Maps DPDP Act (2023) Section 8(5) to `CTRL-AWS-RDS-STORAGE-ENC` and CERT-In 2022 to `CTRL-AWS-LOG-180D`.
  - Determines applicability dynamically based on project `jurisdiction` and `sector` in `applicability_engine.py`.

---

## Part 13: Complete System Flow

User (Healthcare-B) → `Login` → `Projects.tsx`
↓ Uploads ZIP & Terraform
`API` → Extracts ZIP to disk, saves HCL to DB
↓ Navigates to Deploy Center
`Deploy.tsx` → `POST /deployments/plan`
↓
`ComplianceEngine` builds DB context
↓
`TerraformEngine` & `OPA Evaluator` process HCL
↓
`SonarQubeClient` scans Application files
↓
Result = **FAIL** (Returns Failed Controls)
↓
`Deploy.tsx` blocks deployment. Trigger Remediation.
↓
`RLRemediator` determines optimal Actions (`ACT_ENABLE_RDS_ENC`, `ACT_UPGRADE_WEAK_CRYPTO`)
↓
`POST /projects/remediate`
↓
`TerraformEngine` mutates HCL. `ApplicationRemediator` mutates Java code.
↓
User Re-evaluates (`POST /deployments/plan`)
↓
Result = **PASS**
↓
Admin User Authorizes `POST /deployments/{id}/apply`
↓
Audit Ledger signs the transaction.

---

## Part 14: Failure Scenarios

1. **Unauthorized Page**: `ProtectedRoute.tsx` bounces user to `/login`.
2. **USER attempts Admin deployment**: `require_admin` throws `403 Forbidden`.
3. **Missing OPA binary**: `opa_evaluator.py` executes native python regex checking.
4. **Missing SonarQube server**: `sonarqube_client.py` executes native python regex checking on source tree.
5. **No LLM API Key**: `llm_client.py` falls back to `guardrails.py` returning DB metrics deterministically.
6. **Mandatory Control Violation**: `Deployment` state is set to `BLOCKED`. Rollout API refuses to execute.

---

## Part 15: Reality Matrix

| Feature | Current Implementation | REAL / SIMULATED / STATIC / HYBRID | Limitation |
|---------|------------------------|-------------------------------------|------------|
| Auth & RBAC | JWT HS256 + Role Checks | **REAL** | No OAuth/SSO integration. |
| Database | SQLite | **REAL** (SQLite) | Not PostgreSQL as some docs might claim. |
| OPA Eval | Subprocess call or Fallback | **HYBRID** | Regex fallback lacks full Rego syntax support. |
| SonarQube | REST API or Regex Fallback | **HYBRID** | Regex fallback only finds exact CWE-89/327 string matches. |
| Remediation Engine | Offline matrix | **STATIC** / RULE-BASED | Pre-computed Q-values; not actively learning online. |
| Remediation Execution | Source/HCL Mutation | **REAL** | Only supports specific regex replacements, not AST parsing. |
| Deployment | Audit Logging | **SIMULATED** | Does not actually hit AWS `boto3`. |
| Audit Ledger | SHA-256 Hash Chaining | **REAL** | Stored in SQLite, vulnerable to DB wiping. |
| Dashboard | DB Aggregation | **HYBRID** | Polled execution, not real-time WebSockets. |
| AI Assistant | Gemini/Ollama or Fallback | **HYBRID** | Deterministic engine overrides if keys missing. |

---

## Part 16: File-by-File Code Map

- **`frontend/src/pages/Deploy.tsx`**: The core gating UI. Prevents rollout if status != PASS.
- **`backend/app/engines/compliance_engine.py`**: The orchestrator. Aggregates Applicability, OPA, and Sonar.
- **`backend/app/engines/rl_remediator.py`**: Houses the Q-learning matrix recommending fixes based on cost.
- **`backend/app/engines/terraform_engine.py`**: Uses `jinja2` to create baseline templates and parses custom HCL for OPA.
- **`backend/app/engines/application_remediator.py`**: Executes raw file writes to fix Java vulnerabilities.
- **`backend/app/api/v1/deployments.py`**: The API gatekeeper. Checks `is_blocked = not eval_result["deployment_allowed"]`.


## Part 17: Complete Page Inventory

*The following inventory maps every reachable route based on the current `frontend/src/routes.tsx` configuration and page source code.*

### 1. Landing Page
1. **Route**: `/`
2. **Purpose**: Public introduction and entry point.
3. **Visible sections**: Hero section, Features.
4. **Every button**: Login / Get Started (Navigates to `/login`).
5. **Every input**: None.
6. **Every API call**: None.
7. **Backend endpoint**: N/A.
8. **Database/engine involved**: N/A.
9. **Real/static/simulated/hybrid status**: STATIC.
10. **Role restrictions**: Public.
11. **Error behavior**: N/A.
12. **What happens after each important action**: Routes user to `/login`.
13. **Demo explanation**: "This is the unauthenticated public landing page."
14. **Likely viva questions**: "How is the landing page served? It's a static React route."

### 2. Login Page
1. **Route**: `/login`
2. **Purpose**: Authenticates users to access the platform.
3. **Visible sections**: Login form.
4. **Every button**: "Sign In", "Show/Hide Password".
5. **Every input**: Username (text), Password (password).
6. **Every API call**: `request('/auth/login', { method: 'POST', body: { username, password } })`.
7. **Backend endpoint**: `POST /api/v1/auth/login`.
8. **Database/engine involved**: `User` table (SQLite).
9. **Real/static/simulated/hybrid status**: REAL.
10. **Role restrictions**: Public (but issues tokens for Admin/User).
11. **Error behavior**: Shows "Invalid credentials" on 401.
12. **What happens after each important action**: Saves token to `sessionStorage`, redirects to `/dashboard`.
13. **Demo explanation**: "We authenticate here to receive a JWT."
14. **Likely viva questions**: "How are passwords stored? PBKDF2 hashing."

### 3. Dashboard Page
1. **Route**: `/dashboard`
2. **Purpose**: High-level telemetry and KPI aggregation.
3. **Visible sections**: KPI Cards, Quick Actions, Trend Charts, Activity Table.
4. **Every button**: "Trigger Scan", "Dismiss".
5. **Every input**: None.
6. **Every API call**: `GET /dashboard/stats`, `POST /compliance/evaluate` (via trigger).
7. **Backend endpoint**: `GET /api/v1/dashboard/stats`.
8. **Database/engine involved**: `EvaluationRun`, `Project`, `Deployment`, `AuditLog`.
9. **Real/static/simulated/hybrid status**: HYBRID (DB-driven stats, but manual refresh/polling, not WebSockets).
10. **Role restrictions**: PROTECTED (User/Admin).
11. **Error behavior**: Fails gracefully if stats fail to load.
12. **What happens after each important action**: Refreshing updates KPIs from the database.
13. **Demo explanation**: "Aggregated telemetry across all managed environments."
14. **Likely viva questions**: "Are these charts real-time? No, they pull from the DB on load or manual scan."

### 4. Projects Page
1. **Route**: `/projects`
2. **Purpose**: Project selection, creation, and source code upload.
3. **Visible sections**: Project List, Create Dialog, Detail Drawer.
4. **Every button**: "Create Project", "Upload Zip", "Delete", "Manage This Project".
5. **Every input**: Name, Organization, Sector, Data Categories, Infrastructure (Zip), Application Source (Zip).
6. **Every API call**: `GET /projects`, `POST /projects`, `POST /projects/{id}/upload/infrastructure`, `POST /projects/{id}/upload/application`, `DELETE /projects/{id}`.
7. **Backend endpoint**: `/api/v1/projects/*`.
8. **Database/engine involved**: `Project` table. File system extraction for ZIPs.
9. **Real/static/simulated/hybrid status**: REAL.
10. **Role restrictions**: PROTECTED. Users see their projects; Admins see all.
11. **Error behavior**: Upload errors show toast notifications.
12. **What happens after each important action**: Sets active `ProjectContext`.
13. **Demo explanation**: "This is where we isolate distinct environments and upload their IaC and app source."
14. **Likely viva questions**: "How is isolation maintained? Projects have UUIDs acting as foreign keys for all downstream data."

### 5. Deploy Center
1. **Route**: `/deploy`
2. **Purpose**: Gating pipeline and remediation trigger.
3. **Visible sections**: Gate Status, Pipeline Steps, OPA Findings, Sonar Findings, RL Optimizer Recommendations.
4. **Every button**: "Evaluate Gate", "Apply RL Remediation", "Authorize & Apply to AWS".
5. **Every input**: None directly (acts on uploaded code).
6. **Every API call**: `POST /deployments/plan`, `POST /projects/{id}/remediate`, `POST /deployments/{id}/apply`.
7. **Backend endpoint**: `/api/v1/deployments/*`, `/api/v1/projects/{id}/remediate`.
8. **Database/engine involved**: `ComplianceEngine`, `TerraformEngine`, `SonarQubeClient`, `RLRemediator`.
9. **Real/static/simulated/hybrid status**: HYBRID (Real evaluation, simulated AWS rollout).
10. **Role restrictions**: PROTECTED. Only ADMIN can click "Authorize & Apply".
11. **Error behavior**: Deployment blocked if scan fails or returns 4xx.
12. **What happens after each important action**: RL Remediation mutates files. Apply marks Deployment as SUCCESS.
13. **Demo explanation**: "The deployment gate enforces strict compliance. AI cannot override this."
14. **Likely viva questions**: "What prevents a user from deploying? The backend validates the EvaluationRun status == PASS."

### 6. Deployments Page
1. **Route**: `/deployments`
2. **Purpose**: Historical log of all deployment attempts.
3. **Visible sections**: Table of deployments (Success/Blocked/Awaiting).
4. **Every button**: "View Logs".
5. **Every input**: None.
6. **Every API call**: `GET /deployments`.
7. **Backend endpoint**: `/api/v1/deployments`.
8. **Database/engine involved**: `Deployment` table.
9. **Real/static/simulated/hybrid status**: REAL (DB log of simulated AWS actions).
10. **Role restrictions**: PROTECTED.
11. **Error behavior**: Standard API failure toasts.
12. **What happens after each important action**: Shows detailed logs of that deployment run.
13. **Demo explanation**: "A ledger of all rollout attempts and their enforcement statuses."
14. **Likely viva questions**: "Do these represent real AWS deployments? No, they represent the execution of the compliance gate."

### 7. Infrastructure Topology
1. **Route**: `/infrastructure`
2. **Purpose**: Visual mapping of the cloud environment.
3. **Visible sections**: React Flow canvas, Node details.
4. **Every button**: "Zoom In/Out", "Fit View".
5. **Every input**: None.
6. **Every API call**: None (relies on Project Context).
7. **Backend endpoint**: N/A.
8. **Database/engine involved**: React Flow (Frontend).
9. **Real/static/simulated/hybrid status**: STATIC / HYBRID (Pre-defined nodes styled by project provider/region).
10. **Role restrictions**: PROTECTED.
11. **Error behavior**: N/A.
12. **What happens after each important action**: Nodes can be clicked for hardcoded/contextual metadata.
13. **Demo explanation**: "A conceptual map of the intended cloud architecture."
14. **Likely viva questions**: "Is this generated dynamically from Terraform? No, it's a structural representation based on project metadata."

### 8. Compliance Matrix
1. **Route**: `/compliance`
2. **Purpose**: Regulatory traceability mapping.
3. **Visible sections**: 5-Layer Matrix, Framework Overview.
4. **Every button**: "Traceability Chain", "Framework Overview".
5. **Every input**: None.
6. **Every API call**: `GET /compliance/summary`.
7. **Backend endpoint**: `/api/v1/compliance/summary`.
8. **Database/engine involved**: `Regulation`, `RegulatoryRequirement`, `RequirementEvaluation`.
9. **Real/static/simulated/hybrid status**: REAL.
10. **Role restrictions**: PROTECTED.
11. **Error behavior**: N/A.
12. **What happens after each important action**: Toggles views between matrix and summary.
13. **Demo explanation**: "Maps statutory laws directly to technical controls."
14. **Likely viva questions**: "Where does this data come from? It aggregates the latest EvaluationRun for the project."

### 9. Policies Page
1. **Route**: `/policies`
2. **Purpose**: Viewing OPA Rego rules.
3. **Visible sections**: List of policies, Policy Inspector drawer.
4. **Every button**: "Inspect", "Close Drawer".
5. **Every input**: Search (text).
6. **Every API call**: None (Hardcoded/Fetched from local state in standard setup, or mock API).
7. **Backend endpoint**: N/A.
8. **Database/engine involved**: Frontend state representing OPA rules.
9. **Real/static/simulated/hybrid status**: STATIC representations of actual backend policies.
10. **Role restrictions**: PROTECTED.
11. **Error behavior**: N/A.
12. **What happens after each important action**: Drawer shows policy details.
13. **Demo explanation**: "These are the declarative OPA rules enforced by the engine."
14. **Likely viva questions**: "Can I edit policies here? No, this is read-only."

### 10. Security Scanner
1. **Route**: `/security`
2. **Purpose**: SonarQube application security pipeline view.
3. **Visible sections**: Pipeline visualization, Findings list, Remediation drawer.
4. **Every button**: "Run security scan", "Remediation", "Close Drawer".
5. **Every input**: None.
6. **Every API call**: `GET /security/findings`, `POST /security/scan`.
7. **Backend endpoint**: `/api/v1/security/*`.
8. **Database/engine involved**: `sonarqube_client.py` (API or Regex fallback).
9. **Real/static/simulated/hybrid status**: HYBRID.
10. **Role restrictions**: PROTECTED.
11. **Error behavior**: Shows "0 findings" if scan fails.
12. **What happens after each important action**: Fetches CWE findings for the active project.
13. **Demo explanation**: "Scanning physical application source code for CWEs."
14. **Likely viva questions**: "Does this scan Terraform? No, it scans the uploaded application ZIP (e.g. Java files)."

### 11. AI Assistant
1. **Route**: `/ai-assistant` (Alias: `/ai`)
2. **Purpose**: Chat interface for regulatory queries.
3. **Visible sections**: Chat history, Input area, Citations toggle.
4. **Every button**: "Send", "Toggle Citations".
5. **Every input**: Chat prompt (textarea/text).
6. **Every API call**: `POST /ai/chat`.
7. **Backend endpoint**: `/api/v1/ai/chat`.
8. **Database/engine involved**: `llm_client.py`, `rag_engine.py`, `guardrails.py`.
9. **Real/static/simulated/hybrid status**: HYBRID (LLM if API keys exist, else deterministic RAG text).
10. **Role restrictions**: PROTECTED.
11. **Error behavior**: Returns fallback string if API fails.
12. **What happens after each important action**: Appends chat message to UI.
13. **Demo explanation**: "A grounded copilot that can only answer based on current project compliance state."
14. **Likely viva questions**: "Can the AI deploy? No, the backend physically isolates deployment execution."

### 12. Audit Logs
1. **Route**: `/audit` (Alias: `/audit-logs`)
2. **Purpose**: Tamper-evident ledger of all actions.
3. **Visible sections**: Log table, Pagination.
4. **Every button**: "Export Logs", Pagination (Next/Prev).
5. **Every input**: Search (text).
6. **Every API call**: `GET /audit/logs`.
7. **Backend endpoint**: `/api/v1/audit/logs`.
8. **Database/engine involved**: `AuditLog` table (SHA-256 hash chaining).
9. **Real/static/simulated/hybrid status**: REAL.
10. **Role restrictions**: PROTECTED.
11. **Error behavior**: N/A.
12. **What happens after each important action**: Changes page or downloads CSV.
13. **Demo explanation**: "An immutable hash chain recording every scan, failure, and deployment."
14. **Likely viva questions**: "How is immutability enforced? Each record hashes the payload + the previous record's hash."

### 13. Reports
1. **Route**: `/reports`
2. **Purpose**: Compliance certification generation.
3. **Visible sections**: Report List.
4. **Every button**: "Download", "Generate new report".
5. **Every input**: None.
6. **Every API call**: Trigger generation logic.
7. **Backend endpoint**: Mocked/Local generation in frontend.
8. **Database/engine involved**: N/A.
9. **Real/static/simulated/hybrid status**: STATIC/MOCKED generation.
10. **Role restrictions**: PROTECTED.
11. **Error behavior**: N/A.
12. **What happens after each important action**: Downloads a CSV/PDF representation.
13. **Demo explanation**: "Generates board-level compliance reports."
14. **Likely viva questions**: "Are these PDFs real? No, they trigger frontend-based CSV/PDF downloads."

### 14. Settings
1. **Route**: `/settings`
2. **Purpose**: System configuration (Read-only UI).
3. **Visible sections**: Cloud Provider, Sonar URL, OPA URL.
4. **Every button**: "Save Configuration".
5. **Every input**: URLs and toggles.
6. **Every API call**: None (Updates local state only).
7. **Backend endpoint**: N/A.
8. **Database/engine involved**: N/A.
9. **Real/static/simulated/hybrid status**: STATIC (UI only).
10. **Role restrictions**: PROTECTED.
11. **Error behavior**: N/A.
12. **What happens after each important action**: Shows success toast, but doesn't mutate backend.
13. **Demo explanation**: "Configuration for integrations."
14. **Likely viva questions**: "Does changing this URL break the app? No, the UI here is static."

### 15. Not Found
1. **Route**: `*`
2. **Purpose**: 404 Catch-all.
3. **Visible sections**: 404 Error message.
4. **Every button**: "Return to Dashboard".
5. **Every input**: None.
6. **Every API call**: None.
7. **Backend endpoint**: N/A.
8. **Database/engine involved**: N/A.
9. **Real/static/simulated/hybrid status**: STATIC.
10. **Role restrictions**: PROTECTED.
11. **Error behavior**: N/A.
12. **What happens after each important action**: Redirects to `/dashboard`.
13. **Demo explanation**: N/A.
14. **Likely viva questions**: N/A.

### App Shell / Global Behaviors
- **Logout**: Located in the sidebar. Clears `sessionStorage` and `AuthContext`, forces route to `/login`.
- **Project Selection**: Dropdown in the sidebar. Changes `activeProject` in `ProjectContext`. Automatically filters data on subsequent API calls (e.g., Deploy, Sonar) by `projectId`.
