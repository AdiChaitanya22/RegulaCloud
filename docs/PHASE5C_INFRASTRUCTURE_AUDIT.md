# Phase 5C: Infrastructure Page Audit

## Current State Verdict
The current `/infrastructure` page (frontend/src/pages/Infrastructure.tsx) is entirely **STATIC / HARDCODED FAKE DEMO DATA**. 
All visible elements, including nodes, resource names, types, relationships, badges, and attributes are hardcoded into an `initialNodes` array. This is misleading for a production environment.

## Topology Feasibility
**Analysis of Native Plan JSON vs. `terraform graph`:**
- **Option A (Plan JSON only):** The `terraform show -json` output contains both a `planned_values` block (yielding exact resource types, addresses, and final attributes) and a `configuration` block (yielding exact `references` arrays showing dependencies). 
- **Option B (Plan JSON + `terraform graph`):** `terraform graph` produces raw Graphviz DOT format, which includes noisy meta-nodes (providers, variables, outputs) and requires a separate parser.

**Recommendation:** **Option A**. The JSON plan alone is fully sufficient to extract clean, resource-to-resource edge relationships by parsing the `references` arrays within the `configuration` block.

## Canonical Infrastructure Model
A proposed backend-neutral API schema:
```json
{
  "project_id": "proj-xyz",
  "plan_hash": "a1b2c3...",
  "evaluation_run_id": "eval-run-123",
  "resources": [
    {
      "id": "aws_db_instance.patient_db",
      "type": "aws_db_instance",
      "category": "DATABASE",
      "attributes": { "publicly_accessible": false },
      "status": "PASS",
      "supported": true
    }
  ],
  "edges": [
    { "source": "aws_db_instance.patient_db", "target": "aws_security_group.db_sg", "type": "REFERENCES" }
  ]
}
```

## Resource Classification
- **DATABASE**: aws_db_instance, aws_dynamodb_table
- **STORAGE**: aws_s3_bucket, aws_ebs_volume
- **COMPUTE**: aws_instance, aws_lambda_function
- **NETWORK**: aws_vpc, aws_subnet, aws_security_group, aws_lb
- **SECURITY**: aws_kms_key, aws_waf, aws_secretsmanager_secret
- **IDENTITY**: aws_iam_role, aws_iam_policy
- **OBSERVABILITY**: aws_cloudwatch_log_group, aws_cloudtrail

## Compliance Overlay Rules
Status mapping precedence per node:
`FAIL` > `UNKNOWN` > `PASS` > `NOT_APPLICABLE`
Nodes with no applicable controls in the mapping database will be distinctly marked `UNSUPPORTED`.

## API Design Recommendation
Rather than querying the database repeatedly and re-running Terraform, the backend should expose:
`GET /api/v1/projects/{id}/infrastructure/topology`
This endpoint will parse the exact `native_plan_json` saved within the most recent `EvaluationRun.evidence_payload`, ensuring absolute correspondence with the OPA evaluation. If the `infrastructure_hash` of the project differs from the `EvaluationRun`, the endpoint will flag `is_stale: true`.
