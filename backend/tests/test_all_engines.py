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

def test_act_block_s3_public_a_to_f():
    from backend.app.engines.terraform_engine import TerraformEngine
    from backend.app.engines.opa_evaluator import OPAPolicyEvaluator
    import tempfile
    import os
    import shutil
    from backend.app.engines.terraform_cli import TerraformCLI

    # Test A: Failing public S3 -> remediation -> terraform validate -> native plan -> OPA PASS
    failing_hcl = '''
resource "aws_s3_bucket" "b" {
  bucket = "test-bucket"
}
resource "aws_s3_bucket_public_access_block" "pab" {
  bucket = aws_s3_bucket.b.id
  block_public_acls = false
  block_public_policy = false
  ignore_public_acls = false
  restrict_public_buckets = false
}
'''
    # Initial plan fails
    initial_plan = TerraformEngine.hcl_to_plan_json(failing_hcl)
    initial_violations = OPAPolicyEvaluator.evaluate_terraform_plan(initial_plan)
    assert any(v["control_id"] == "CTRL-AWS-S3-NO-PUBLIC" for v in initial_violations)

    # Remediation applied
    remediated_hcl, applied, skipped = TerraformEngine.apply_rl_actions(failing_hcl, ["ACT_BLOCK_S3_PUBLIC"])
    assert "ACT_BLOCK_S3_PUBLIC" in applied
    assert len(skipped) == 0

    # Remediated plan passes
    remediated_plan = TerraformEngine.hcl_to_plan_json(remediated_hcl)
    remediated_violations = OPAPolicyEvaluator.evaluate_terraform_plan(remediated_plan)
    assert not any(v["control_id"] == "CTRL-AWS-S3-NO-PUBLIC" for v in remediated_violations)

    # Test Native Terraform validation and plan generation of remediated HCL via CLI
    from backend.app.engines.terraform_plan_adapter import TerraformPlanAdapter
    tmp = tempfile.mkdtemp()
    try:
        with open(os.path.join(tmp, "main.tf"), "w") as f:
            f.write(remediated_hcl)
        cli_res = TerraformCLI.generate_plan_json(tmp)
        assert cli_res.success is True
        assert cli_res.validation_status == "PASS"
        native_plan_adapted = TerraformPlanAdapter.adapt(cli_res.plan_json)
        native_violations = OPAPolicyEvaluator.evaluate_terraform_plan(native_plan_adapted)
        assert not any(v["control_id"] == "CTRL-AWS-S3-NO-PUBLIC" for v in native_violations)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # Test B: Already compliant -> unchanged / idempotent
    compliant_hcl = '''
resource "aws_s3_bucket_public_access_block" "pab" {
  block_public_acls = true
  block_public_policy = true
  ignore_public_acls = true
  restrict_public_buckets = true
}
'''
    hcl_b, applied_b, _ = TerraformEngine.apply_rl_actions(compliant_hcl, ["ACT_BLOCK_S3_PUBLIC"])
    assert "ACT_BLOCK_S3_PUBLIC" in applied_b
    assert hcl_b.strip() == compliant_hcl.strip()

    # Second run on remediated_hcl is idempotent
    hcl_re_remediated, _, _ = TerraformEngine.apply_rl_actions(remediated_hcl, ["ACT_BLOCK_S3_PUBLIC"])
    assert hcl_re_remediated == remediated_hcl

    # Test C: Partial public-access block -> completed safely
    partial_hcl = '''
resource "aws_s3_bucket_public_access_block" "partial_pab" {
  block_public_acls = true
  block_public_policy = false
}
'''
    hcl_c, applied_c, _ = TerraformEngine.apply_rl_actions(partial_hcl, ["ACT_BLOCK_S3_PUBLIC"])
    assert "block_public_acls = true" in hcl_c
    assert "block_public_policy = true" in hcl_c
    assert "ignore_public_acls = true" in hcl_c
    assert "restrict_public_buckets = true" in hcl_c

    # Test D: Multiple buckets -> all protected
    multi_bucket_hcl = '''
resource "aws_s3_bucket" "bucket_one" {
  bucket = "b1"
}
resource "aws_s3_bucket" "bucket_two" {
  bucket = "b2"
}
'''
    hcl_d, applied_d, _ = TerraformEngine.apply_rl_actions(multi_bucket_hcl, ["ACT_BLOCK_S3_PUBLIC"])
    assert "aws_s3_bucket_public_access_block" in hcl_d
    assert "bucket_one_pab" in hcl_d
    assert "bucket_two_pab" in hcl_d
    assert "aws_s3_bucket.bucket_one.id" in hcl_d
    assert "aws_s3_bucket.bucket_two.id" in hcl_d

    # Test E: Unrelated HCL preserved byte-for-byte
    unrelated_hcl = '''
resource "aws_db_instance" "rds" {
  allocated_storage = 20
  engine = "postgres"
}
'''
    hcl_e, applied_e, _ = TerraformEngine.apply_rl_actions(unrelated_hcl, ["ACT_BLOCK_S3_PUBLIC"])
    assert hcl_e.strip() == unrelated_hcl.strip()

    # Test F: Downstream RL execution
    agent = QLearningRemediationAgent()
    recs = agent.recommend_remediations(["CTRL-AWS-S3-NO-PUBLIC"])
    assert any(r["action_id"] == "ACT_BLOCK_S3_PUBLIC" for r in recs)
    target_action = next(r["action_id"] for r in recs if r["action_id"] == "ACT_BLOCK_S3_PUBLIC")
    hcl_f, applied_f, _ = TerraformEngine.apply_rl_actions(failing_hcl, [target_action])
    assert target_action in applied_f
