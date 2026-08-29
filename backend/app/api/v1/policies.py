from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.db.models import TechnicalControl, RegulatoryRequirement

router = APIRouter(prefix="/policies", tags=["Policies"])

@router.get("")
def get_policies(db: Session = Depends(get_db)):
    controls = db.query(TechnicalControl).all()
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

        output.append({
            "id": c.id,
            "name": c.name,
            "framework": framework_name,
            "severity": "Critical" if "NO-PUBLIC" in c.id or "CRITICAL" in c.id else "High",
            "description": c.description,
            "status": "PASS",
            "lastEvaluation": "Just now",
            "remediationCode": remediation_snippet
        })
    return output
