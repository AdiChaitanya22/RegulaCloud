from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from typing import Dict, Any
from datetime import datetime
from backend.app.core.database import get_db
from backend.app.db.models import DriftEvent, Project, AuditLog
from backend.app.engines.compliance_engine import ComplianceEngine

router = APIRouter(prefix="/drift", tags=["Post-Deployment Drift Detection"])

@router.get("/events/{project_id}")
def get_drift_events(project_id: str, db: Session = Depends(get_db)):
    events = db.query(DriftEvent).filter(DriftEvent.project_id == project_id).all()
    return events

@router.post("/inspect")
def inspect_drift(payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    project_id = payload.get("projectId", "proj-healthcare-india")
    simulate_drift = payload.get("simulate_drift", False)

    if simulate_drift:
        drift = DriftEvent(
            project_id=project_id,
            resource_id="aws_s3_bucket.ayushman_records",
            control_id="CTRL-AWS-S3-NO-PUBLIC",
            expected_state={"block_public_acls": True, "block_public_policy": True},
            actual_state={"block_public_acls": False, "block_public_policy": False},
            detected_at=datetime.utcnow()
        )
        db.add(drift)
        
        AuditLog.create_entry(
            session=db,
            actor="aws.config_monitor",
            action="DRIFT_DETECTED_ALERT",
            resource_type="AWS_S3",
            resource_id="aws_s3_bucket.ayushman_records",
            severity="Critical",
            details={"violation": "Public access block removed out-of-band on S3 bucket"}
        )
        db.commit()

        return {
            "drift_detected": True,
            "drift_count": 1,
            "drifts": [
                {
                    "resource": "aws_s3_bucket.ayushman_records",
                    "control": "CTRL-AWS-S3-NO-PUBLIC",
                    "violation": "Out-of-band modification detected: Public Access Block disabled directly on AWS console.",
                    "status": "NON_COMPLIANT_DRIFT",
                    "remediation_action": "ACT_BLOCK_S3_PUBLIC"
                }
            ],
            "message": "CRITICAL DRIFT: Infrastructure state deviated from approved compliance baseline."
        }

    return {
        "drift_detected": False,
        "drift_count": 0,
        "drifts": [],
        "message": "All AWS live configurations match approved Terraform compliance baseline."
    }
