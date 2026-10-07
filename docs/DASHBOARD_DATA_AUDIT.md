# Phase 5C: Dashboard Data Audit

## Current State Verdict
The `/dashboard/stats` backend API provides **REAL, TRUTHFUL** data for top-level metrics, but the frontend React components (`ComplianceTrend`, `SecuritySeverity`, `DeploymentActivity`, `ResourceDistribution`) currently ignore this data and render **HARDCODED FAKE DATA**.

## Detailed Element Source Matrix

| Dashboard Element | Current Value | Source | DB-backed? | Truthful? | Recommended Action |
| --- | --- | --- | --- | --- | --- |
| Compliance Score | Varies | `api/v1/dashboard.py` | Yes | Yes | Retain |
| Security Findings | Varies | `api/v1/dashboard.py` | Yes | Yes | Retain |
| Total Deployments | Varies | `api/v1/dashboard.py` | Yes | Yes | Retain |
| Recent Activity | Varies | `AuditLog` table | Yes | Yes | Retain |
| Compliance Trend Chart | FAKE | Hardcoded React | No | **NO** | Feed real `stats.trend` |
| Security Severity Chart | FAKE | Hardcoded React | No | **NO** | Feed real `stats.critical/highFindings` |
| Deployment Chart | FAKE | Hardcoded React | No | **NO** | Replace with real historical data or remove |
| Resource Distribution | FAKE | Hardcoded React | No | **NO** | Extract from latest native plan JSON |

## Truthful Metric Recommendations

**1. Projects Evaluated**
- Source: `Project` table

**2. Open OPA Violations**
- Source: Count of `RequirementEvaluation.findings` from the latest `EvaluationRun`

**3. Coverage Model**
- Distinguish Compliance Status (PASS/FAIL) from Policy Coverage (Supported/Unsupported).
- **Resource Coverage Percent** = (Resources matching a `TechnicalControl` / Total Native Resources) * 100
- This ensures that a workspace containing 10 AWS resources where only 2 are understood by OPA is visibly flagged as having low coverage, preventing a false sense of security.

## Chart Feasibility
- **Compliance Trend**: The DB has `EvaluationRun` history, which is already aggregated in `stats.trend`. The React component must be updated to accept this data.
- **Severity Distribution**: The OPA rules currently embed severity implicitly. The dashboard infers it loosely. True severity should be formalized or mapped directly from `TechnicalControl` records to be scientifically rigorous.
- **Recent Activity**: The `AuditLog` is effectively queried and provided by the backend. The frontend table currently binds correctly to `stats.recentActivities`.
