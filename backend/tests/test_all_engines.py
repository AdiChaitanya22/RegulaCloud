import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.core.database import Base
from backend.app.db.init_db import init_database
from backend.app.engines.applicability_engine import ApplicabilityEngine
from backend.app.engines.opa_evaluator import OPAPolicyEvaluator
from backend.app.engines.compliance_engine import ComplianceEngine
from backend.app.engines.rl_remediator import QLearningRemediationAgent
from backend.app.core.database import SessionLocal

@pytest.fixture(scope="module")
def db_session():
    init_database()
    db = SessionLocal()
    yield db
    db.close()

def test_applicability_engine(db_session):
    profile = {
        "jurisdiction": "India",
        "sector": "Healthcare",
        "data_categories": ["personal_data", "health_data"],
        "environment": "production",
        "cloud_provider": "AWS"
    }
    results = ApplicabilityEngine.evaluate_applicability(profile, db_session)
    assert len(results) >= 3
    req_ids = [r["requirement_id"] for r in results]
    assert "DPDP-2023-SEC8.5" in req_ids
    assert "CERTIN-2022-LOG-RETENTION" in req_ids

def test_opa_evaluator_catches_public_db():
    plan_with_public_db = {
        "resource_changes": [
            {
                "type": "aws_db_instance",
                "address": "aws_db_instance.rds_postgres",
                "change": {
                    "after": {
                        "publicly_accessible": True,
                        "storage_encrypted": False
                    }
                }
            }
        ]
    }
    violations = OPAPolicyEvaluator.evaluate_terraform_plan(plan_with_public_db)
    assert len(violations) >= 2
    controls_violated = [v["control_id"] for v in violations]
    assert "CTRL-AWS-RDS-NO-PUBLIC" in controls_violated
    assert "CTRL-AWS-RDS-STORAGE-ENC" in controls_violated

def test_deterministic_compliance_gating(db_session):
    # Non-compliant plan (publicly accessible database)
    bad_hcl = """
    resource "aws_db_instance" "vulnerable" {
      publicly_accessible = true
      storage_encrypted = false
    }
    """
    eval_result = ComplianceEngine.evaluate_compliance(
        db=db_session,
        project_id="proj-healthcare-india",
        hcl_code=bad_hcl
    )
    # Must fail and block deployment
    assert eval_result["overall_status"] == "FAIL"
    assert eval_result["deployment_allowed"] is False
    assert eval_result["failed_count"] > 0
    assert len(eval_result["evidence_hash"]) == 64

def test_rl_remediation_optimizer():
    agent = QLearningRemediationAgent()
    agent.train_simulator(episodes=100)
    
    recommendations = agent.recommend_remediations([
        "CTRL-AWS-RDS-NO-PUBLIC",
        "CTRL-AWS-S3-ENC"
    ])
    assert len(recommendations) == 2
    actions = [r["target_control"] for r in recommendations]
    assert "CTRL-AWS-RDS-NO-PUBLIC" in actions
    assert "CTRL-AWS-S3-ENC" in actions
