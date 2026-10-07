# REGULACLOUD — 1-PAGE VIVA CHEAT SHEET

**Purpose**: Automated, regulation-aware cloud compliance deployment framework. Blocks non-compliant code from reaching production.
**Target User**: Cloud Architects and Compliance Auditors (e.g., Government).
**Architecture**: React/TypeScript Frontend, FastAPI/Python Backend, SQLite DB.
**Regulations Evaluated**: DPDP Act 2023, CERT-In Directions 2022.
**Evaluators**: 
- **OPA**: Inspects Terraform/HCL plans for infrastructure violations.
- **SonarQube**: Scans application source code for CWEs (Security).
**Deployment**: Simulates rollout upon PASS. Cryptographically signed into an audit ledger (SHA-256).
**Remediation (Q-Learning)**: Calculates optimal fixes for failed controls based on a cost/complexity matrix. Actively mutates HCL and physical Application source code.
**AI Component**: Context-grounded assistant (RAG) providing regulatory telemetry (Gemini/Ollama/Fallback). NO capability to override deployment.
**Fail-Closed Gate**: If any mandatory statutory control fails, deployment API `POST /deployments/{id}/apply` is strictly blocked.

---

## KEY TERMINOLOGY

- **OPA (Open Policy Agent)**: General-purpose policy engine. We use it to evaluate Terraform plans against DPDP/CERT-In Rego policies.
- **Rego**: The declarative query language used by OPA.
- **Terraform / HCL**: Infrastructure as Code tool / language. Defines AWS resources (RDS, S3).
- **CWE**: Common Weakness Enumeration. Categorizes software vulnerabilities (e.g., CWE-89 SQL Injection).
- **Fail-Closed**: Security principle. If validation fails or the scanner crashes, the system denies deployment. It defaults to DENY.
- **Q-Learning**: Reinforcement learning algorithm. In RegulaCloud, it navigates a pre-computed matrix to find the cheapest, fastest remediation actions for failed controls.
- **Hash Chain**: Linking records by taking the SHA-256 hash of the previous record. Provides a tamper-evident audit ledger.
- **Deterministic**: A result that is absolute and mathematically verifiable, unlike LLM probabilistic outputs.

---

## DEMO SCRIPTS

### 1. Healthcare-A (The Perfect Run)
- **SCREEN**: Login Page
- **ACTION**: Login as `admin`.
- **SCREEN**: Projects
- **ACTION**: Select "Healthcare-A". Note the Compliance Score is already 100%.
- **SCREEN**: Deploy Center
- **ACTION**: Click "Evaluate Compliance".
- **EXPECTED**: 100% Pass. OPA and Sonar clear.
- **EXPLANATION**: "This project adheres strictly to the generated templates, satisfying all DPDP and CERT-In requirements natively."
- **ACTION**: Click "Authorize Deployment".
- **EXPLANATION**: "Because the deterministic gate passed, I am allowed as an admin to deploy. The action is cryptographically signed."

### 2. Healthcare-B (The Remediation Run)
- **SCREEN**: Projects
- **ACTION**: Select "Healthcare-B".
- **SCREEN**: Deploy Center
- **ACTION**: Click "Evaluate Compliance".
- **EXPECTED**: Score drops (~70%). OPA flags unencrypted S3/RDS. Sonar flags DES/SQL Injection. Deployment is BLOCKED.
- **EXPLANATION**: "The framework intercepts the non-compliant code. The fail-closed gate prevents rollout."
- **ACTION**: View "RL Optimizer Recommendations". Click "Apply All Actions".
- **EXPECTED**: The backend mutates the HCL (adding `storage_encrypted = true`) and mutates the Java files (swapping DES for AES).
- **ACTION**: Re-evaluate.
- **EXPECTED**: 100% Pass. Deployment UNBLOCKED.
- **EXPLANATION**: "The Q-Learning engine identified the cheapest compliance route, and the application remediator physically patched the flaws. We can now deploy safely."

### 3. Project Isolation
- **EXPLANATION**: "Healthcare-A and B run in entirely isolated environments. They have unique Project IDs. The `ProjectContext` in React and the SQLite Foreign Keys on `EvaluationRun` prevent cross-project data leakage. An evaluator for Project A cannot read SonarQube findings for Project B."

---

## VIVA QUESTIONS BANK

### A. Fundamentals
**1. What is RegulaCloud?**
An automated, regulation-aware cloud deployment gate that blocks non-compliant infrastructure and application code.
*Viva phrase*: "It's a continuous compliance framework for cloud environments."

**2. Why did you build it?**
Because existing tools scan code *after* deployment. RegulaCloud stops non-compliant code *before* deployment.
*Viva phrase*: "To shift regulatory compliance completely left."

### B. Architecture
**3. What is the tech stack?**
React (TypeScript, Vite), FastAPI (Python), SQLite, OPA, SonarQube.
*Viva phrase*: "A modern React frontend paired with a high-performance Python FastAPI backend."

**4. Why use FastAPI?**
For fast, asynchronous execution, especially useful when calling out to OPA subprocesses or SonarQube APIs.

### E. Database
**5. Why SQLite?**
It provides zero-configuration persistence perfect for a contained evaluation environment and local demo.
*Viva phrase*: "We use SQLite for lightweight, isolated persistence, abstractable to PostgreSQL via SQLAlchemy."

### F. Terraform & OPA
**6. Why OPA?**
It separates policy from application logic.
*Viva phrase*: "OPA evaluates infrastructure against declarative Rego rules without hardcoding checks."

**7. How does OPA read Terraform?**
The `terraform_engine.py` converts HCL syntax into a structured `tfplan` JSON that OPA can traverse.

### K. SonarQube
**8. Why SonarQube?**
To catch application-level vulnerabilities that Terraform misses.
*Viva phrase*: "Terraform secures the infrastructure; SonarQube secures the application running on it."

**9. What happens if Sonar is down?**
The `sonarqube_client.py` falls back to a raw regex scanner targeting CWE-89 (SQLi) and CWE-327 (Weak Crypto) across the source directory.

### M. Q-Learning & Remediation
**10. Why Q-learning instead of if/else rules?**
It optimizes for multiple penalties. E.g., fixing a database takes time (complexity penalty), but failing DPDP costs massive fines (statutory reward).
*Viva phrase*: "It dynamically finds the lowest-cost remediation path based on a weighted penalty matrix."

**11. How does it modify Java code?**
`application_remediator.py` reads the file, identifies the vulnerability via regex, and replaces the vulnerable text (e.g. `DES` -> `AES`).

### P. Security
**12. Can the AI override the deployment gate?**
No. `deployments.py` enforces the gate deterministically.
*Viva phrase*: "The AI has zero authority; the programmatic gate is absolute."

**13. What is fail-closed?**
If a scan crashes or returns 'UNKNOWN', deployment is blocked.
*Viva phrase*: "It defaults to DENY to prevent accidental exposure."

**14. How does the Audit Ledger work?**
`models.py (AuditLog)` takes the SHA-256 hash of the *previous* log and includes it in the *current* log payload, creating an unbroken chain.

### S. AWS / Cloud
**15. Does it actually deploy to AWS?**
No. It simulates deployment by recording a successful state in the database.
*Viva phrase*: "Deployment is simulated to prevent live billing, but the evaluation pipeline is real."

*(Note: Provide this concise subset of high-impact questions to guide the viva successfully. A full 100-question catalog mirrors these fundamental themes across React states, API routes, and DB relationships).*

---

## KEY FRONTEND ROUTING NOTES

- **Public Routes**: `/`, `/login`
- **Protected Routes**: All other pages require a valid JWT token via `ProtectedRoute.tsx`.
- **Admin-Only Actions**: Only an ADMIN role can authorize deployment on the `/deploy` page. Users can scan and remediate, but not rollout.
- **Project Context**: `ProjectContext.tsx` handles global isolation. Selecting a project in the sidebar restricts the `/deploy`, `/security`, and `/ai-assistant` pages to that specific project UUID.

## MAJOR LIMITATIONS & FALLBACKS

1. **Regex Limitation**: The fallback remediation engine uses Regex, not a full AST (Abstract Syntax Tree) parser. Complex, multi-line vulnerabilities might be missed.
2. **Simulated AWS**: Real AWS `boto3` calls are mocked.
3. **Offline Q-Learning**: The RL matrix is pre-computed (`rl_remediator.py`). It does not dynamically learn from new, unseen vulnerabilities during runtime.
4. **SQLite Vulnerability**: While the audit log hash chain detects tampering, anyone with direct SQLite file access can delete or rewrite the entire database history.
5. **LLM Fallback**: If LLM API keys are missing, the assistant uses a rigid, deterministic text generation fallback rather than a true generative conversational agent.
