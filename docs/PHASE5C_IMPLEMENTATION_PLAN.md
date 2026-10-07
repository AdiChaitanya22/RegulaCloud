# Phase 5C: Implementation Plan

## Recommended Scope (Smallest Useful Implementation)

**5C.1: Native-Plan Infrastructure API Endpoint**
- Create `GET /api/v1/projects/{project_id}/infrastructure/topology`.
- Extract `plan_hash` and `terraform_plan` from the most recent `EvaluationRun`.
- Flatten resources into nodes and establish relationships using the `configuration` block's `references` arrays.
- Overlay node compliance status by intersecting `RequirementEvaluation` data.
- Enforce standard authorization (owner or admin).

**5C.2: Dynamic Infrastructure Page**
- Remove all hardcoded D3/React nodes in `Infrastructure.tsx`.
- Call the new topology endpoint.
- Render actual native-plan resources, mapping types to standard AWS icons.
- Add "STALE / Re-evaluation Required" banner if the project's source hashes differ from the evaluation hashes.

**5C.3: Truthful Dashboard API**
- Overhaul `Dashboard.tsx` to stop passing hardcoded static arrays to charts.
- Update `/api/v1/dashboard/stats` (if necessary) to ensure `trend`, `severity`, and `coverage` datasets are formatted properly for immediate React consumption.

**5C.4: Coverage Metrics Implementation**
- Define `supported_resources` vs `unsupported_resources`.
- Add a specific KPI to the dashboard for Policy Coverage (e.g., "82% Covered").
- Ensure `UNSUPPORTED` nodes on the Infrastructure page have distinct visual coloring (e.g., grayed out).

**5C.5: Six New OPA Controls**
- Add Rego policies for IMDSv2, EBS Encryption, KMS Rotation, Open SSH, Open RDP, and IAM Wildcards.
- Update `control_mappings.json` and seed data to link these to the regulatory framework.

## Architecture Design Decisions
- **No N+1 Database Queries**: The topology API will query `EvaluationRun` and `RequirementEvaluation` in large batches, not per-node.
- **Avoid Terraform on UI Load**: The topology will read the *stored* native plan from SQLite. It will *not* shell out to Terraform upon user click, preventing massive API latency.
- **Authorization**: Standard User ownership restrictions apply to all new routes. 

## Estimated Effort
- **Estimated files to change**: ~12 (3 Frontend UI, 1 Backend API route, 2 OPA policy, 1 Seed mapping, 5 Testing files).
- **Risks**: The D3/SVG mesh layout in `Infrastructure.tsx` might behave unpredictably with massive (50+ node) topologies. A fallback or simplified list-view may be required if the auto-layout overlaps severely.
