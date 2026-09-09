from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.db.models import TechnicalControl, RegulatoryRequirement, EvaluationRun, RequirementEvaluation
from backend.app.core.auth import require_user

router = APIRouter(prefix="/policies", tags=["Policies"])

@router.get("")
def get_policies(current_user=Depends(require_user), db: Session = Depends(get_db)):
    controls = db.query(TechnicalControl).all()
    
    # Query latest evaluation run to determine actual live control status
    latest_run = db.query(EvaluationRun).order_by(EvaluationRun.evaluated_at.desc()).first()
    failed_control_ids = set()
    passed_control_ids = set()
    
    if latest_run:
        req_evals = db.query(RequirementEvaluation).filter(
            RequirementEvaluation.evaluation_run_id == latest_run.id
        ).all()
        for re_item in req_evals:
            if re_item.status == "PASS":
                # Mapped controls passed
                for m in re_item.requirement.control_mappings:
                    passed_control_ids.add(m.control_id)
            elif re_item.status == "FAIL":
                for finding in (re_item.findings or []):
                    if isinstance(finding, dict) and "control_id" in finding:
                        failed_control_ids.add(finding["control_id"])
                        
    output = []
    for c in controls:
        # Determine framework mapping
        req_mapping = c.requirement_mappings[0] if c.requirement_mappings else None
        framework_name = "India DPDP Act 2023" if "DPDP" in (req_mapping.requirement_id if req_mapping else "") else "CERT-In Directions 2022"
        
        remediation_snippet = ""
        if "RDS" in c.id:
            remediation_snippet = 'resource "aws_db_instance" "postgres" {\n-  publicly_accessible = true\n+  publicly_accessible = false\n+  storage_encrypted   = true\n}'
        elif "S3" in c.id:
            remediation_snippet = 'resource "aws_s3_bucket_server_side_encryption_configuration" "enc" {\n+  rule {\n+    apply_server_side_encryption_by_default {\n+      sse_algorithm = "aws:kms"\n+    }\n+  }\n}'
        elif "LOG" in c.id:
            remediation_snippet = 'resource "aws_cloudwatch_log_group" "audit" {\n-  retention_in_days = 30\n+  retention_in_days = 180\n}'
        else:
            remediation_snippet = '// Ensure parameterized queries with PreparedStatement\nPreparedStatement ps = conn.prepareStatement(query);'

        # Compute dynamic status
        if c.id in failed_control_ids:
            status = "FAIL"
        elif c.id in passed_control_ids:
            status = "PASS"
        elif latest_run:
            status = "PASS" if latest_run.overall_status == "PASS" else "UNKNOWN"
        else:
            status = "UNKNOWN"

        output.append({
            "id": c.id,
            "name": c.name,
            "framework": framework_name,
            "severity": "Critical" if "NO-PUBLIC" in c.id or "CRITICAL" in c.id else "High",
            "description": c.description,
            "status": status,
            "lastEvaluation": latest_run.evaluated_at.strftime("%d %b %Y %H:%M") if latest_run and latest_run.evaluated_at else "Not evaluated",
            "remediationCode": remediation_snippet
        })
    return output
