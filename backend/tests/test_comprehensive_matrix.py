import pytest
import hashlib
import json
from datetime import datetime
from backend.app.core.database import SessionLocal
from backend.app.db.init_db import init_database
from backend.app.db.models import (
    Project,
    RegulatoryRequirement,
    RequirementControlMapping,
    TechnicalControl,
    AuditLog,
    DriftEvent,
    EvaluationRun
)
from backend.app.engines.applicability_engine import ApplicabilityEngine
from backend.app.engines.compliance_engine import ComplianceEngine
from backend.app.engines.opa_evaluator import OPAPolicyEvaluator
from backend.app.engines.terraform_engine import TerraformEngine
from backend.app.engines.rl_remediator import QLearningRemediationAgent

@pytest.fixture(scope="module")
def db_session():
    init_database()
    db = SessionLocal()
    yield db
    db.close()

# 1. Test PASS Condition
def test_deterministic_pass(db_session):
    compliant_hcl = TerraformEngine.generate_compliant_hcl({
        "aws_region": "ap-south-1",
        "s3_bucket_name": "pass-bucket",
        "rds_identifier": "pass-db",
        "rds_public": False,
        "rds_encrypted": True,
        "include_logging": True,
        "log_retention_days": 180,
        "environment": "production"
    })
    
    result = ComplianceEngine.evaluate_compliance(
        db=db_session,
        project_id="proj-healthcare-india",
        hcl_code=compliant_hcl,
        sonar_project_key="clean-build"
    )
    assert result["overall_status"] == "PASS"
    assert result["compliance_score"] == 100.0
    assert result["deployment_allowed"] is True
    assert result["failed_count"] == 0

# 2. Test FAIL Condition (Mandatory Violation)
def test_deterministic_fail_blocks_deployment(db_session):
    vulnerable_hcl = """
    resource "aws_db_instance" "vuln_db" {
      publicly_accessible = true
      storage_encrypted = false
    }
    """
    result = ComplianceEngine.evaluate_compliance(
        db=db_session,
        project_id="proj-healthcare-india",
        hcl_code=vulnerable_hcl
    )
    assert result["overall_status"] == "FAIL"
    assert result["deployment_allowed"] is False
    assert result["failed_count"] > 0
    assert any(v["control_id"] == "CTRL-AWS-RDS-NO-PUBLIC" for v in result["opa_violations"])

# 3. Test UNKNOWN Condition (Unmapped Mandatory Requirement Blocks Deployment)
def test_unknown_mandatory_blocks_deployment(db_session):
    # Temporarily insert an unmapped mandatory requirement
    unmapped_req = RegulatoryRequirement(
        id="REQ-UNMAPPED-TEST",
        regulation_id="DPDP-ACT-2023",
        title="Unmapped Mandatory Statutory Obligation",
        requirement_text="Mandatory obligation with no technical control mapping yet approved.",
        version="1.0",
        mandatory=True,
        applicability_conditions={"jurisdiction": "India"},
        status="APPROVED"
    )
    db_session.add(unmapped_req)
    db_session.commit()

    try:
        result = ComplianceEngine.evaluate_compliance(
            db=db_session,
            project_id="proj-healthcare-india",
            sonar_project_key="clean-build"
        )
        assert result["unknown_count"] >= 1
        assert result["deployment_allowed"] is False  # Fail-closed rule!
    finally:
        db_session.delete(unmapped_req)
        db_session.commit()

# 4. Test NOT_APPLICABLE Condition (Sector/Jurisdiction mismatch)
def test_not_applicable_evaluation(db_session):
    # Foreign profile not subject to India-specific rules
    us_profile = {
        "jurisdiction": "USA",
        "sector": "Retail",
        "data_categories": ["general_inventory"],
        "environment": "staging",
        "cloud_provider": "AWS"
    }
    results = ApplicabilityEngine.evaluate_applicability(us_profile, db_session)
    # India DPDPA and CERT-In must not apply
    assert len(results) == 0

# 5. Test Q-Learning Remediation
def test_q_learning_remediation_optimization():
    agent = QLearningRemediationAgent()
    agent.train_simulator(episodes=200)
    recs = agent.recommend_remediations([
        "CTRL-AWS-RDS-NO-PUBLIC",
        "CTRL-AWS-S3-ENC",
        "CTRL-AWS-LOG-180D"
    ])
    assert len(recs) == 3
    # Step 1 should address high penalty violation
    step_controls = [r["target_control"] for r in recs]
    assert "CTRL-AWS-RDS-NO-PUBLIC" in step_controls
    assert "CTRL-AWS-S3-ENC" in step_controls

# 6. Test Evidence Hash Validity (SHA-256)
def test_evidence_hash_cryptographic_integrity(db_session):
    result = ComplianceEngine.evaluate_compliance(
        db=db_session,
        project_id="proj-healthcare-india"
    )
    h = result["evidence_hash"]
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)

# 7. Test Cryptographic Audit Hash Chaining
def test_audit_log_hash_chain(db_session):
    log1 = AuditLog.create_entry(
        session=db_session,
        actor="tester.1",
        action="TEST_ACTION_1",
        resource_type="TEST",
        resource_id="1",
        severity="Low",
        details={"step": 1}
    )
    log2 = AuditLog.create_entry(
        session=db_session,
        actor="tester.2",
        action="TEST_ACTION_2",
        resource_type="TEST",
        resource_id="2",
        severity="Low",
        details={"step": 2}
    )
    # Child's previous_hash must match parent's current_hash
    assert log2.previous_hash == log1.current_hash
    assert len(log2.current_hash) == 64

# 8. Test Drift Detection Event Recording
def test_drift_detection_flow(db_session):
    drift = DriftEvent(
        project_id="proj-healthcare-india",
        resource_id="aws_s3_bucket.secure_records",
        control_id="CTRL-AWS-S3-NO-PUBLIC",
        expected_state={"block_public_acls": True},
        actual_state={"block_public_acls": False},
        detected_at=datetime.utcnow()
    )
    db_session.add(drift)
    db_session.commit()
    
    saved_drift = db_session.query(DriftEvent).filter(
        DriftEvent.resource_id == "aws_s3_bucket.secure_records"
    ).first()
    assert saved_drift is not None
    assert saved_drift.actual_state["block_public_acls"] is False
